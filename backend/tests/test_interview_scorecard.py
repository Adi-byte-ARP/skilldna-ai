"""The interview scorecard, and the mock test's speech and device signals."""
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DATABASE_URL", f"sqlite:////tmp/skilldna_scorecard_{uuid.uuid4().hex}.db")
os.environ.pop("ANTHROPIC_API_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.services.interview_dimensions import compute  # noqa: E402

client = TestClient(app)
LONG = ("For example I built a payments service in Python. First I added a Redis cache, then I measured "
        "latency for two weeks, because the database was the bottleneck, and as a result p95 fell by forty percent. "
        "Finally I wrote the runbook so the team could repeat it on other services without help from me.")


def test_scorecard_has_five_dimensions_each_between_zero_and_a_hundred():
    turns = [{"answer": LONG, "score": 80}, {"answer": LONG, "score": 70}]
    dims = compute(turns)
    assert [d["name"] for d in dims] == ["Technical depth", "Relevance", "Communication", "Structure", "Confidence"]
    assert all(0 <= d["score"] <= 100 for d in dims)


def test_hedging_lowers_confidence():
    confident = compute([{"answer": LONG, "score": 70}])
    hedged = compute([{"answer": "maybe I think I guess probably I am not sure " + LONG, "score": 70}])
    c1 = next(d["score"] for d in confident if d["name"] == "Confidence")
    c2 = next(d["score"] for d in hedged if d["name"] == "Confidence")
    assert c2 < c1


def test_low_dimensions_come_with_advice_and_high_ones_do_not():
    dims = compute([{"answer": "ok", "score": 20}])
    assert all(d["advice"] for d in dims if d["score"] < 60)
    strong = compute([{"answer": LONG, "score": 90}])
    assert all(d["advice"] is None for d in strong if d["score"] >= 60)


def test_the_report_returns_the_scorecard():
    email = f"sc{uuid.uuid4().hex[:10]}@gmail.com"
    r = client.post("/auth/register", json={"name": "Score Card", "email": email, "password": "TestPass123!"}).json()
    h = {"Authorization": f"Bearer {r['token']}"}
    sid = client.post("/interview/sessions", json={"role": "Backend Engineer"}, headers=h).json()["id"]
    body = client.post(f"/interview/sessions/{sid}/answer", json={"answer": LONG, "seconds_spent": 150}, headers=h).json()
    assert body["done"] is False
    # the scorecard appears once the interview finishes
    for _ in range(6):
        body = client.post(f"/interview/sessions/{sid}/answer", json={"answer": LONG, "seconds_spent": 150}, headers=h).json()
        if body["done"]:
            break
    assert body["done"] is True
    assert len(body["report"]["dimensions"]) == 5


def _mock_test(h):
    return client.post("/mock/sessions", json={"kind": "test", "role": "Backend Engineer"}, headers=h).json()


def _account():
    email = f"sp{uuid.uuid4().hex[:10]}@gmail.com"
    r = client.post("/auth/register", json={"name": "Speech Test", "email": email, "password": "TestPass123!"}).json()
    return {"Authorization": f"Bearer {r['token']}"}


def test_speech_adds_integrity_points_but_is_not_a_violation():
    h = _account()
    s = _mock_test(h)
    state = client.post(f"/mock/sessions/{s['id']}/events", json={"type": "speech"}, headers=h).json()
    assert state["status"] == "active"
    assert len(state["violations"]) == 0
    assert state["integrity"]["points"] == 2.0


def test_two_speech_incidents_and_a_blur_end_the_test_automatically():
    h = _account()
    s = _mock_test(h)
    client.post(f"/mock/sessions/{s['id']}/events", json={"type": "speech"}, headers=h)
    client.post(f"/mock/sessions/{s['id']}/events", json={"type": "speech"}, headers=h)
    state = client.post(f"/mock/sessions/{s['id']}/events", json={"type": "window_blur"}, headers=h).json()
    assert state["status"] == "terminated"
    assert state["end_reason"] == "integrity"


def test_a_mobile_device_signal_ends_the_test_on_its_own():
    h = _account()
    s = _mock_test(h)
    state = client.post(f"/mock/sessions/{s['id']}/events", json={"type": "mobile_device"}, headers=h).json()
    assert state["status"] == "terminated" and state["end_reason"] == "integrity"


def test_an_unknown_mock_signal_is_still_refused():
    h = _account()
    s = _mock_test(h)
    assert client.post(f"/mock/sessions/{s['id']}/events", json={"type": "telepathy"}, headers=h).status_code == 400
