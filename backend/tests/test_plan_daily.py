"""Skill-gap plan and daily challenge: content, progress, one answer per day, streaks."""
import io
import os
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DATABASE_URL", f"sqlite:////tmp/skilldna_plan_test_{uuid.uuid4().hex}.db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.services.daily_bank import DAILY_BANK  # noqa: E402
from app.services.daily_engine import current_streak, pick_challenge  # noqa: E402
from app.services.mock_content import ROLE_SKILLS  # noqa: E402
from app.services.roadmap import PLAYBOOK, _gaps_for_role  # noqa: E402

client = TestClient(app)


def _user():
    email = f"plan{uuid.uuid4().hex[:12]}@gmail.com"
    r = client.post("/auth/register", json={"name": "Plan Tester", "email": email, "password": "TestPass123!"})
    body = r.json()
    return body["user"]["id"], {"Authorization": f"Bearer {body['token']}"}


def _bank(cid):
    return next(c for c in DAILY_BANK if c["id"] == cid)


def _correct_payload(today):
    """A correct answer for today's question, whatever its kind."""
    cid = today["challenge"]["id"]
    bank = _bank(cid)
    if bank.get("kind") == "text":
        return {"challenge_id": cid, "answer_text": ", ".join(bank["keywords"][: bank["min_hits"]])}
    return {"challenge_id": cid, "answer_index": bank["answer"]}


def _wrong_payload(today):
    cid = today["challenge"]["id"]
    bank = _bank(cid)
    if bank.get("kind") == "text":
        return {"challenge_id": cid, "answer_text": "something unrelated entirely"}
    return {"challenge_id": cid, "answer_index": (bank["answer"] + 1) % len(bank["options"])}


def _resume_pdf(text: str) -> bytes:
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for line in text.split("\n"):  # one line per row, as a real resume has
        c.drawString(50, y, line)
        y -= 20
    c.save()
    return buf.getvalue()


# ---------- plan ----------

def test_plan_for_new_user_lists_every_role_skill_as_missing():
    _, h = _user()
    plan = client.get("/plan", params={"role": "Backend Engineer"}, headers=h).json()
    assert plan["gap_count"] == len(ROLE_SKILLS["Backend Engineer"])
    assert all(item["status"] == "missing" for item in plan["items"])
    # every gap appears in exactly one learning phase, and the last phase is the proof step
    placed = [key for ph in plan["phases"] for key in ph["items"]]
    assert sorted(placed) == sorted(it["key"] for it in plan["items"])
    assert plan["phases"][-1]["name"].split("·")[1].strip().startswith("Prove it")
    assert all("weeks" in ph["name"] for ph in plan["phases"][:-1])
    assert plan["total_hours_estimate"] > 0
    assert plan["summary"]


def test_plan_items_are_detailed():
    _, h = _user()
    plan = client.get("/plan", params={"role": "Backend Engineer"}, headers=h).json()
    for item in plan["items"]:
        assert len(item["objectives"]) == 3
        assert len(item["tasks"]) == 3
        assert item["project"]
        assert item["resources"] and item["resources"][0]["url"].startswith("https://")
        assert item["hours_estimate"] > 0
        assert item["check"]


def test_every_playbook_entry_is_complete():
    for skill, book in PLAYBOOK.items():
        assert len(book["objectives"]) == 3, skill
        assert len(book["tasks"]) == 3, skill
        assert book["resources"] and all(u.startswith("https://") for _, u in book["resources"]), skill
        assert book["hours"] > 0 and book["project"] and book["why"], skill


def test_resume_skill_counts_as_weak_until_a_second_source_confirms_it():
    uid, h = _user()
    pdf = _resume_pdf("Plan Tester\nBackend engineer. Skills: Python, FastAPI, SQL, Docker, Git.")
    r = client.post(f"/resume/upload/{uid}", headers=h, files={"file": ("cv.pdf", pdf, "application/pdf")})
    assert r.status_code == 200
    plan = client.get("/plan", params={"role": "Backend Engineer"}, headers=h).json()
    python = next((it for it in plan["items"] if it["skill"] == "Python"), None)
    assert python is not None and python["status"] == "weak"
    assert 40 <= python["current_score"] < 60  # resume-only: claimed, not verified


def test_task_toggle_updates_progress_and_persists():
    _, h = _user()
    r = client.post("/plan/tasks/python:task0", params={"role": "Backend Engineer"}, json={"done": True}, headers=h)
    assert r.status_code == 200 and r.json()["done"] is True
    plan = client.get("/plan", params={"role": "Backend Engineer"}, headers=h).json()
    python = next(it for it in plan["items"] if it["skill"] == "Python")
    assert python["tasks"][0]["done"] is True
    assert plan["progress"]["done"] == 1
    client.post("/plan/tasks/python:task0", params={"role": "Backend Engineer"}, json={"done": False}, headers=h)
    assert client.get("/plan", params={"role": "Backend Engineer"}, headers=h).json()["progress"]["done"] == 0


def test_invalid_task_key_and_unknown_role_are_rejected():
    _, h = _user()
    assert client.post("/plan/tasks/DROP TABLE;--", json={"done": True}, headers=h).status_code == 400
    assert client.get("/plan", params={"role": "Astronaut"}, headers=h).status_code == 400


def test_plan_requires_login():
    assert client.get("/plan").status_code == 401


def test_gap_helper_orders_missing_before_weak():
    scores = [{"skill_name": "python", "score": 55.0}]
    gaps = _gaps_for_role("Backend Engineer", scores)
    statuses = [g["status"] for g in gaps]
    assert statuses == sorted(statuses, key=lambda s: 0 if s == "missing" else 1)


# ---------- daily challenge ----------

def test_daily_question_hides_answer_until_answered():
    _, h = _user()
    body = client.get("/daily/today", headers=h).json()
    assert body["answered"] is False and body["result"] is None
    assert "answer" not in body["challenge"] and "keywords" not in body["challenge"]
    if body["challenge"]["kind"] == "mcq":
        assert len(body["challenge"]["options"]) >= 2
    else:
        assert body["challenge"]["min_hits"] >= 1


def test_one_answer_per_day_and_result_is_revealed():
    _, h = _user()
    today = client.get("/daily/today", headers=h).json()
    r = client.post("/daily/answer", json=_correct_payload(today), headers=h)
    assert r.status_code == 200
    assert r.json()["correct"] is True and r.json()["points"] == 10
    assert r.json()["explanation"]
    again = client.post("/daily/answer", json=_correct_payload(today), headers=h)
    assert again.status_code == 409
    after = client.get("/daily/today", headers=h).json()
    assert after["answered"] is True and after["result"]["correct"] is True


def test_wrong_answer_scores_zero():
    _, h = _user()
    today = client.get("/daily/today", headers=h).json()
    r = client.post("/daily/answer", json=_wrong_payload(today), headers=h).json()
    assert r["correct"] is False and r["points"] == 0


def test_cannot_answer_a_different_challenge():
    _, h = _user()
    r = client.post("/daily/answer", json={"challenge_id": "d-not-today", "answer_index": 0}, headers=h)
    assert r.status_code == 400


def test_free_text_grading_counts_keywords():
    text_q = next(c for c in DAILY_BANK if c["kind"] == "text" and c["min_hits"] == 2)
    from app.services.daily_engine import grade
    good = grade(text_q, answer_text=f"I would use {text_q['keywords'][0]} and {text_q['keywords'][1]}.")
    one = grade(text_q, answer_text=text_q["keywords"][0])
    assert good["correct"] is True and good["points"] == 10
    assert one["correct"] is False and one["points"] == 0
    assert grade(text_q, answer_text=text_q["keywords"][0].upper() + " " + text_q["keywords"][1].upper())["correct"]


def test_free_text_endpoint_validates_and_grades_once(monkeypatch):
    """Fix today's question to a free-text one, so the endpoint's text path always runs."""
    import app.routers.daily as daily_router
    text_q = next(c for c in DAILY_BANK if c["kind"] == "text" and c["min_hits"] == 1)
    monkeypatch.setattr(daily_router, "_todays_challenge", lambda db, user, role: text_q)
    _, h = _user()
    assert client.post("/daily/answer", json={"challenge_id": text_q["id"], "answer_text": "   "},
                       headers=h).status_code == 400
    ok = client.post("/daily/answer", json={"challenge_id": text_q["id"], "answer_text": text_q["keywords"][0]},
                     headers=h)
    assert ok.status_code == 200 and ok.json()["correct"] is True
    assert client.post("/daily/answer", json={"challenge_id": text_q["id"], "answer_text": "again"},
                       headers=h).status_code == 409


def test_history_reports_points_and_streak():
    _, h = _user()
    today = client.get("/daily/today", headers=h).json()
    client.post("/daily/answer", json=_correct_payload(today), headers=h)
    hist = client.get("/daily/history", headers=h).json()
    assert hist["streak"] == 1 and hist["total_points"] == 10 and len(hist["days"]) == 1


def test_daily_challenge_is_stable_within_a_day():
    day = date(2026, 10, 12)
    a = pick_challenge(5, day, ["sql"], [])
    b = pick_challenge(5, day, ["sql"], [])
    assert a["id"] == b["id"]


def test_challenges_follow_gaps_and_explore_every_third_day():
    base = date(2026, 10, 12)
    focus_days = [pick_challenge(3, base + timedelta(i), ["sql"], []) for i in range(6)]
    explore_flags = [c["explore"] for c in focus_days]
    expected = [((base + timedelta(i)).toordinal() % 3 == 0) for i in range(6)]
    assert explore_flags == expected
    for c in focus_days:
        if not c["explore"]:
            assert c["skill"] == "sql"


def test_streak_counts_back_from_today_or_yesterday():
    today = date(2026, 10, 12)
    assert current_streak({today - timedelta(1), today}, today) == 2
    assert current_streak({today - timedelta(2), today - timedelta(1)}, today) == 2  # today not answered yet
    assert current_streak({today - timedelta(3)}, today) == 0


def test_question_bank_is_large_and_valid():
    assert len(DAILY_BANK) >= 100
    assert len({c["id"] for c in DAILY_BANK}) == len(DAILY_BANK)
    for c in DAILY_BANK:
        assert c["explanation"]
        if c["kind"] == "mcq":
            assert 0 <= c["answer"] < len(c["options"])
        else:
            assert c["keywords"] and 1 <= c["min_hits"] <= len(c["keywords"])
