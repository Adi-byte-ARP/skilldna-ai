"""Phase locking: the next phase opens only after every task and a passing phase test."""
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DATABASE_URL", f"sqlite:////tmp/skilldna_gate_test_{uuid.uuid4().hex}.db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.services.learning import phase_test_questions  # noqa: E402
from app.services.mock_content import ROLE_SKILLS  # noqa: E402

client = TestClient(app)
ROLE = "Backend Engineer"


def _account():
    email = f"gate{uuid.uuid4().hex[:12]}@gmail.com"
    r = client.post("/auth/register", json={"name": "Gate Tester", "email": email, "password": "TestPass123!"})
    body = r.json()
    return body["user"]["id"], {"Authorization": f"Bearer {body['token']}"}


def _plan(h):
    return client.get("/plan", params={"role": ROLE}, headers=h).json()


def _tick(h, key, done=True):
    return client.post(f"/plan/tasks/{key}", params={"role": ROLE}, json={"done": done}, headers=h)


def _phase_items(plan, index):
    keys = set(plan["phases"][index]["items"])
    return [it for it in plan["items"] if it["key"] in keys]


def test_only_the_first_phase_is_open_at_the_start():
    _, h = _account()
    plan = _plan(h)
    assert plan["phases"][0]["status"] == "in_progress"
    assert plan["phases"][1]["status"] == "locked"
    locked_item = _phase_items(plan, 1)[0]
    r = _tick(h, locked_item["tasks"][0]["key"])
    assert r.status_code == 423
    assert "locked" in r.json()["detail"]


def test_the_phase_test_is_closed_until_every_task_is_ticked():
    _, h = _account()
    plan = _plan(h)
    assert client.get("/plan/phases/0/test", params={"role": ROLE}, headers=h).status_code == 409
    items = _phase_items(plan, 0)
    for item in items[:-1]:
        for task in item["tasks"]:
            assert _tick(h, task["key"]).status_code == 200
    assert client.get("/plan/phases/0/test", params={"role": ROLE}, headers=h).status_code == 409


def test_passing_the_phase_test_unlocks_the_next_phase():
    uid, h = _account()
    plan = _plan(h)
    for item in _phase_items(plan, 0):
        for task in item["tasks"]:
            _tick(h, task["key"])
    test = client.get("/plan/phases/0/test", params={"role": ROLE}, headers=h).json()
    assert len(test["questions"]) == 5 and "answer" not in test["questions"][0]
    # the server's answer key (same seed the server uses), answered perfectly
    skills = [it["skill"] for it in _phase_items(plan, 0)]
    key = {q["id"]: q["answer"] for q in phase_test_questions(skills, seed=uid * 31 + 0)}
    result = client.post(f"/plan/phases/0/test", params={"role": ROLE},
                         json={"answers": key}, headers=h).json()
    assert result["passed"] is True and result["unlocked_next"] is True
    after = _plan(h)
    assert after["phases"][1]["status"] == "in_progress"
    assert _tick(h, _phase_items(after, 1)[0]["tasks"][0]["key"]).status_code == 200


def test_a_failed_phase_test_keeps_the_next_phase_locked():
    _, h = _account()
    plan = _plan(h)
    for item in _phase_items(plan, 0):
        for task in item["tasks"]:
            _tick(h, task["key"])
    result = client.post("/plan/phases/0/test", params={"role": ROLE}, json={"answers": {}}, headers=h).json()
    assert result["passed"] is False
    assert _plan(h)["phases"][1]["status"] == "locked"


def test_the_final_proof_phase_waits_for_every_learning_phase():
    _, h = _account()
    plan = _plan(h)
    assert plan["phases"][-1]["status"] == "locked"
    assert plan["phases"][-1]["items"] == []


def test_every_task_has_notes_and_video_links():
    _, h = _account()
    plan = _plan(h)
    for item in plan["items"]:
        assert len(item["notes"]) >= 2, item["skill"]
        for task in item["tasks"]:
            assert len(task["videos"]) >= 2
            assert all(v["url"].startswith("https://www.youtube.com/results?search_query=") for v in task["videos"])


def test_learning_phases_are_numbered_without_gaps():
    _, h = _account()
    plan = _plan(h)
    learning = [ph for ph in plan["phases"] if ph["items"]]
    for number, phase in enumerate(learning):
        assert all(it["phase_index"] == number for it in _phase_items(plan, number))


def test_there_are_at_least_ten_roles_each_with_real_skills():
    assert len(ROLE_SKILLS) >= 10
    assert all(len(skills) >= 6 for skills in ROLE_SKILLS.values())
