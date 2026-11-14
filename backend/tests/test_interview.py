"""AI interview: a conversation that follows up on weak answers and ends with a report."""
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DATABASE_URL", f"sqlite:////tmp/skilldna_interview_test_{uuid.uuid4().hex}.db")
os.environ.pop("ANTHROPIC_API_KEY", None)  # tests use the rule-based engine

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.services.interviewer import TARGET_TURNS, score_answer  # noqa: E402

client = TestClient(app)


def _h():
    email = f"ivw{uuid.uuid4().hex[:12]}@gmail.com"
    r = client.post("/auth/register", json={"name": "Ivy Tester", "email": email, "password": "TestPass123!"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_an_interview_starts_with_an_opening_question():
    h = _h()
    r = client.post("/interview/sessions", json={"role": "Backend Engineer"}, headers=h).json()
    assert r["status"] == "active" and r["current_question"]["kind"] == "opening"
    assert r["target_turns"] == TARGET_TURNS


def test_strong_answers_move_on_and_weak_ones_get_a_follow_up():
    h = _h()
    sid = client.post("/interview/sessions", json={"role": "Backend Engineer"}, headers=h).json()["id"]
    strong = ("I built a payments API in Python with FastAPI. For example, I added caching with Redis, "
              "which reduced latency by 40% and the result was measured on production traffic.")
    r = client.post(f"/interview/sessions/{sid}/answer", json={"answer": strong}, headers=h).json()
    assert r["current_question"]["kind"] == "question"
    weak = client.post(f"/interview/sessions/{sid}/answer", json={"answer": "it is fine i think"}, headers=h).json()
    assert weak["current_question"]["kind"] == "follow_up"
    assert "did not cover" in weak["current_question"]["question"]


def test_the_interview_ends_with_a_report_after_the_target_turns():
    h = _h()
    sid = client.post("/interview/sessions", json={"role": "Data / ML Engineer"}, headers=h).json()["id"]
    last = None
    for _ in range(TARGET_TURNS):
        last = client.post(f"/interview/sessions/{sid}/answer",
                           json={"answer": "For example I trained a model, measured it on a test set, and the result improved by 12%."},
                           headers=h).json()
    assert last["done"] is True and last["status"] == "finished"
    report = last["report"]
    assert 0 <= report["overall"] <= 100 and report["turns"] == TARGET_TURNS
    assert report["engine"] in ("rule-based", "language model")
    assert client.post(f"/interview/sessions/{sid}/answer", json={"answer": "more"}, headers=h).status_code == 409


def test_empty_answers_are_refused_and_interviews_are_private():
    h = _h()
    other = _h()
    sid = client.post("/interview/sessions", json={"role": "Backend Engineer"}, headers=h).json()["id"]
    assert client.post(f"/interview/sessions/{sid}/answer", json={"answer": "   "}, headers=h).status_code == 400
    assert client.get(f"/interview/sessions/{sid}", headers=other).status_code == 404


def test_an_unknown_role_is_refused():
    h = _h()
    assert client.post("/interview/sessions", json={"role": "Astronaut"}, headers=h).status_code == 400


def test_the_scorer_rewards_coverage_and_concrete_examples():
    keywords = ["cache", "latency", "redis"]
    vague = score_answer("it was good", keywords)
    concrete = score_answer("For example I added Redis cache and latency dropped 40%", keywords)
    assert concrete["score"] > vague["score"]
    assert concrete["missing"] == []
