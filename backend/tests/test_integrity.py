"""Cheating signals end a test or interview automatically. Each signal is recorded and explained."""
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DATABASE_URL", f"sqlite:////tmp/skilldna_integrity_test_{uuid.uuid4().hex}.db")
os.environ.pop("ANTHROPIC_API_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.services import integrity  # noqa: E402
from app.services.mock_content import ROLE_SKILLS  # noqa: E402

client = TestClient(app)
ROLE = "Backend Engineer"
LONG = ("I built a payments service in Python. For example it cut latency by forty percent after we added "
        "a Redis cache, and I measured the result on production traffic for two weeks before the release.")


def _unique(text=LONG):
    """Each test gets its own answer text, so the duplicate check only fires where a test wants it."""
    return text + " " + uuid.uuid4().hex


def _account():
    email = f"integ{uuid.uuid4().hex[:12]}@gmail.com"
    r = client.post("/auth/register", json={"name": "Integ Tester", "email": email, "password": "TestPass123!"})
    body = r.json()
    return body["user"]["id"], {"Authorization": f"Bearer {body['token']}"}


# ---------- the engine ----------

def test_a_tab_switch_with_one_copy_attempt_is_enough_to_auto_submit():
    flags, points = integrity.add_flag([], 0, "tab_hidden")
    assert not integrity.should_auto_submit(points)
    flags, points = integrity.add_flag(flags, points, "copy")
    assert integrity.should_auto_submit(points)


def test_a_fast_long_answer_is_flagged_as_a_burst():
    kinds = [k for k, _ in integrity.analyse_answer("word " * 120, seconds_spent=5)]
    assert "answer_burst" in kinds


def test_a_normal_answer_is_not_flagged():
    assert integrity.analyse_answer(LONG, seconds_spent=180) == []


def test_answers_are_compared_ignoring_case_and_punctuation():
    assert integrity.answer_fingerprint(LONG) == integrity.answer_fingerprint(LONG.upper().replace(".", "!"))
    assert integrity.answer_fingerprint("too short") is None


# ---------- the mock test ----------

def _start_test(h):
    r = client.post("/mock/sessions", json={"kind": "test", "role": ROLE}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def test_a_mock_test_auto_submits_on_a_tab_switch_plus_a_copy_attempt():
    _, h = _account()
    s = _start_test(h)
    state = client.post(f"/mock/sessions/{s['id']}/events", json={"type": "tab_hidden"}, headers=h).json()
    assert state["status"] == "active"
    state = client.post(f"/mock/sessions/{s['id']}/events", json={"type": "copy"}, headers=h).json()
    assert state["status"] == "terminated"
    assert state["end_reason"] == "integrity"
    assert state["result"]["end_reason"] == "integrity"
    assert state["integrity"]["points"] >= integrity.AUTO_SUBMIT_AT
    assert {f["label"] for f in state["integrity"]["flags"]} >= {"Switched to another tab", "Tried to copy"}


def test_the_mock_test_records_why_it_ended_when_violations_run_out():
    _, h = _account()
    s = _start_test(h)
    client.post(f"/mock/sessions/{s['id']}/events", json={"type": "window_blur"}, headers=h)
    state = client.post(f"/mock/sessions/{s['id']}/events", json={"type": "fullscreen_exit"}, headers=h).json()
    assert state["status"] == "terminated"
    assert state["end_reason"] in ("violations", "integrity")


# ---------- the AI interview ----------

def _start_interview(h):
    return client.post("/interview/sessions", json={"role": ROLE}, headers=h).json()["id"]


def test_pasting_a_long_answer_within_seconds_auto_submits_the_interview():
    _, h = _account()
    sid = _start_interview(h)
    body = client.post(f"/interview/sessions/{sid}/answer", json={"answer": _unique(), "seconds_spent": 3}, headers=h).json()
    assert body["auto_submitted"] is True
    assert body["status"] == "finished" and body["end_reason"] == "integrity"
    assert body["report"]["overall"] >= 0
    assert "answer_burst" in {f["type"] for f in body["integrity"]["flags"]}


def test_a_paste_attempt_during_the_interview_is_recorded_and_can_end_it():
    _, h = _account()
    sid = _start_interview(h)
    client.post(f"/interview/sessions/{sid}/event", json={"type": "tab_hidden"}, headers=h)
    body = client.post(f"/interview/sessions/{sid}/event", json={"type": "paste"}, headers=h).json()
    assert body["auto_submitted"] is True
    assert body["status"] == "finished"


def test_the_same_answer_given_by_someone_else_is_flagged_as_a_duplicate():
    _, first = _account()
    _, second = _account()
    sid1 = _start_interview(first)
    shared = _unique()
    client.post(f"/interview/sessions/{sid1}/answer", json={"answer": shared, "seconds_spent": 200}, headers=first)
    sid2 = _start_interview(second)
    body = client.post(f"/interview/sessions/{sid2}/answer", json={"answer": shared, "seconds_spent": 200}, headers=second).json()
    assert "answer_duplicate" in {f["type"] for f in body["integrity"]["flags"]}
    assert body["auto_submitted"] is True


def test_an_honest_interview_is_not_interrupted():
    _, h = _account()
    sid = _start_interview(h)
    body = client.post(f"/interview/sessions/{sid}/answer", json={"answer": _unique(), "seconds_spent": 150}, headers=h).json()
    assert body["auto_submitted"] is False and body["status"] == "active"
    assert body["integrity"]["points"] == 0


def test_an_unknown_browser_signal_is_refused():
    _, h = _account()
    sid = _start_interview(h)
    assert client.post(f"/interview/sessions/{sid}/event", json={"type": "telepathy"}, headers=h).status_code == 400


def test_a_signal_that_ends_the_interview_returns_the_report_with_it():
    _, h = _account()
    sid = _start_interview(h)
    client.post(f"/interview/sessions/{sid}/event", json={"type": "tab_hidden"}, headers=h)
    body = client.post(f"/interview/sessions/{sid}/event", json={"type": "paste"}, headers=h).json()
    assert body["auto_submitted"] is True
    assert body["report"] is not None and "overall" in body["report"]
    assert body["status"] == "finished" and body["end_reason"] == "integrity"
