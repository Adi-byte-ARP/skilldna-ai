"""Mock test / mock interview: lifecycle, violation policy, deadline, scoring, privacy."""
import os
import sys
import uuid
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DATABASE_URL", f"sqlite:////tmp/skilldna_mock_test_{uuid.uuid4().hex}.db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.services import mock_engine as eng  # noqa: E402
from app.services.mock_content import MCQ_BANK  # noqa: E402

client = TestClient(app)


def _user():
    email = f"mock{uuid.uuid4().hex[:12]}@gmail.com"
    r = client.post("/auth/register", json={"name": "Mock Tester", "email": email, "password": "TestPass123!"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _start(headers, kind="test", role="Backend Engineer"):
    r = client.post("/mock/sessions", json={"kind": kind, "role": role}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- pure logic ----------

def test_mcq_score_and_open_score():
    q = {"id": "x", "answer": 2}
    assert eng.score_mcq_answer(q, 2) is True
    assert eng.score_mcq_answer(q, 0) is False
    assert eng.score_mcq_answer(q, None) is False

    open_q = {"keywords": ["api", "database", "cache", "test"]}
    full = eng.score_open_answer(open_q, " ".join(["api database cache test"] + ["word"] * 60))
    empty = eng.score_open_answer(open_q, "")
    assert full["score"] == 100.0
    assert empty["score"] == 0.0
    assert "api" not in full["missing_points"]


def test_violation_policy_terminates_at_the_limit():
    """Strict: the session ends when the violation limit is reached (two violations)."""
    limit = eng.MAX_VIOLATIONS
    assert limit == 2
    v, stop = eng.apply_violation([], "tab_hidden", "t1")
    assert stop is False if limit > 1 else stop is True
    v, stop = eng.apply_violation(v, "window_blur", "t2")
    assert stop is True and len(v) == limit


def test_public_question_never_leaks_answer_keys():
    mcq = eng.public_question(dict(MCQ_BANK[0], kind="mcq"))
    assert "answer" not in mcq
    open_q = eng.public_question({"id": "o", "kind": "open", "question": "q", "keywords": ["a"], "seconds": 60})
    assert "keywords" not in open_q


# ---------- API lifecycle ----------

def test_start_returns_questions_without_answers():
    h = _user()
    s = _start(h, "test", "Backend Engineer")
    assert s["status"] == "active" and s["questions"]
    assert all("answer" not in q for q in s["questions"])
    assert s["remaining_seconds"] > 0


def test_one_active_session_at_a_time():
    h = _user()
    _start(h)
    r = client.post("/mock/sessions", json={"kind": "interview", "role": "Backend Engineer"}, headers=h)
    assert r.status_code == 409


def test_answer_then_submit_scores_and_reveals_result():
    h = _user()
    s = _start(h, "test", "Backend Engineer")
    first = s["questions"][0]
    correct = next(q["answer"] for q in MCQ_BANK if q["id"] == first["id"])
    r = client.post(f"/mock/sessions/{s['id']}/answers",
                    json={"question_id": first["id"], "answer": correct}, headers=h)
    assert r.status_code == 200 and first["id"] in r.json()["answered_ids"]

    done = client.post(f"/mock/sessions/{s['id']}/submit", headers=h).json()
    assert done["status"] == "submitted"
    assert done["result"]["correct"] == 1
    assert done["result"]["score"] > 0


def test_third_violation_terminates_and_scores():
    h = _user()
    s = _start(h)
    body = None
    for event in ["tab_hidden", "window_blur", "copy"]:
        body = client.post(f"/mock/sessions/{s['id']}/events", json={"type": event}, headers=h).json()
    assert body["status"] == "terminated"
    assert body["result"]["terminated"] is True
    assert body["result"]["violation_count"] == eng.MAX_VIOLATIONS
    late = client.post(f"/mock/sessions/{s['id']}/answers",
                       json={"question_id": s["questions"][0]["id"], "answer": 0}, headers=h)
    assert late.status_code == 409


def test_unknown_event_type_rejected():
    h = _user()
    s = _start(h)
    r = client.post(f"/mock/sessions/{s['id']}/events", json={"type": "made_up"}, headers=h)
    assert r.status_code == 400


def test_deadline_is_enforced_on_the_server(monkeypatch):
    h = _user()
    s = _start(h)
    import app.routers.mock as mock_router
    future = mock_router._now() + timedelta(seconds=s["time_limit_seconds"] + 5)
    monkeypatch.setattr(mock_router, "_now", lambda: future)
    r = client.post(f"/mock/sessions/{s['id']}/answers",
                    json={"question_id": s["questions"][0]["id"], "answer": 0}, headers=h)
    assert r.status_code == 409
    state = client.get(f"/mock/sessions/{s['id']}", headers=h).json()
    assert state["status"] == "submitted"


def test_sessions_are_private_to_their_owner():
    owner, other = _user(), _user()
    s = _start(owner)
    assert client.get(f"/mock/sessions/{s['id']}", headers=other).status_code == 404


def test_requires_login():
    assert client.post("/mock/sessions", json={"kind": "test", "role": "Backend Engineer"}).status_code == 401


def test_interview_answer_is_scored_and_feedback_names_missing_points():
    h = _user()
    s = _start(h, "interview", "Backend Engineer")
    first = s["questions"][0]
    text = "I would check the logs, roll back the bad release, and monitor the fix before the incident closes."
    r = client.post(f"/mock/sessions/{s['id']}/answers",
                    json={"question_id": first["id"], "answer": text}, headers=h)
    assert r.status_code == 200
    done = client.post(f"/mock/sessions/{s['id']}/submit", headers=h).json()
    per_q = {item["id"]: item for item in done["result"]["per_question"]}
    assert per_q[first["id"]]["words"] > 10
    assert "note" in done["result"]  # the rubric limits are stated to the user
    assert done["result"]["feedback"]
