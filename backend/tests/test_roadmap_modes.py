"""Gap plan versus scratch roadmap, and the ranked list of skills to improve."""
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DATABASE_URL", f"sqlite:////tmp/skilldna_roadmap_modes_{uuid.uuid4().hex}.db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.services.mock_content import ROLE_SKILLS  # noqa: E402

client = TestClient(app)
ROLE = "Backend Engineer"


def _account():
    email = f"rm{uuid.uuid4().hex[:12]}@gmail.com"
    r = client.post("/auth/register", json={"name": "Road Map", "email": email, "password": "TestPass123!"})
    body = r.json()
    return body["user"]["id"], {"Authorization": f"Bearer {body['token']}"}


def _plan(h, mode="gap", role=ROLE):
    return client.get("/plan", params={"role": role, "mode": mode}, headers=h).json()


def test_a_scratch_roadmap_lists_every_skill_for_the_role_even_with_evidence():
    uid, h = _account()
    # give the user real evidence for Python
    from reportlab.pdfgen import canvas
    import io
    buf = io.BytesIO(); c = canvas.Canvas(buf); c.drawString(50, 800, "Road Map"); c.drawString(50, 780, "Skills: Python, FastAPI, Docker"); c.save()
    client.post(f"/resume/upload/{uid}", headers=h, files={"file": ("cv.pdf", buf.getvalue(), "application/pdf")})
    gap = _plan(h, "gap")
    scratch = _plan(h, "scratch")
    assert scratch["mode"] == "scratch" and gap["mode"] == "gap"
    assert len(scratch["items"]) == len(ROLE_SKILLS[ROLE])
    assert all(item["status"] == "missing" for item in scratch["items"])
    assert "Python" not in [it["skill"] for it in gap["items"] if it["status"] == "missing"]


def test_the_gap_plan_lists_only_what_the_user_does_not_show():
    _, h = _account()
    gap = _plan(h, "gap")
    assert gap["gap_count"] == len(ROLE_SKILLS[ROLE])  # no evidence yet, so every skill is a gap


def test_the_improve_list_puts_high_priority_first_and_names_the_next_task():
    _, h = _account()
    improve = _plan(h, "gap")["improve"]
    assert improve and all(item["priority"] in ("High", "Medium") for item in improve)
    priorities = [0 if item["priority"] == "High" else 1 for item in improve]
    assert priorities == sorted(priorities)
    assert all(item["reason"] and item["next_task"] for item in improve)


def test_a_scratch_roadmap_locks_its_phases_like_the_gap_plan():
    _, h = _account()
    plan = _plan(h, "scratch")
    assert plan["phases"][0]["status"] == "in_progress"
    assert plan["phases"][1]["status"] == "locked"
    locked_task = plan["items"][-1]["tasks"][0]["key"] if plan["items"][-1]["locked"] else None
    if locked_task:
        r = client.post(f"/plan/tasks/{locked_task}", params={"role": ROLE, "mode": "scratch"}, json={"done": True}, headers=h)
        assert r.status_code == 423


def test_passing_a_gap_phase_test_does_not_unlock_the_scratch_roadmap():
    uid, h = _account()
    gap = _plan(h, "gap")
    for item in [it for it in gap["items"] if it["phase_index"] == 0]:
        for task in item["tasks"]:
            client.post(f"/plan/tasks/{task['key']}", params={"role": ROLE, "mode": "gap"}, json={"done": True}, headers=h)
    from app.services.learning import phase_test_questions
    skills = [it["skill"] for it in gap["items"] if it["phase_index"] == 0]
    key = {q["id"]: q["answer"] for q in phase_test_questions(skills, seed=uid * 31 + 0)}
    assert client.post("/plan/phases/0/test", params={"role": ROLE, "mode": "gap"}, json={"answers": key}, headers=h).json()["passed"]
    assert _plan(h, "gap")["phases"][1]["status"] == "in_progress"
    assert _plan(h, "scratch")["phases"][1]["status"] == "locked"


def test_an_unknown_mode_is_refused():
    _, h = _account()
    assert client.get("/plan", params={"role": ROLE, "mode": "magic"}, headers=h).status_code == 400


def test_scratch_roadmaps_do_not_write_history_snapshots():
    _, h = _account()
    _plan(h, "scratch")
    assert client.get("/plan/history", headers=h).json() == []
