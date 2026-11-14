"""Skill-level progress on the plan, daily reminders, and the reminder email selection."""
import io
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DATABASE_URL", f"sqlite:////tmp/skilldna_progress_test_{uuid.uuid4().hex}.db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.db_models import DailyAttempt  # noqa: E402
from app.services.daily_bank import DAILY_BANK  # noqa: E402
from app.services.reminders import build_reminder_email, should_remind_now, users_to_email  # noqa: E402

client = TestClient(app)


def _user():
    email = f"prog{uuid.uuid4().hex[:12]}@gmail.com"
    r = client.post("/auth/register", json={"name": "Prog Tester", "email": email, "password": "TestPass123!"})
    body = r.json()
    return body["user"]["id"], body["user"]["email"], {"Authorization": f"Bearer {body['token']}"}


def _pdf(text):
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for line in text.split("\n"):  # one line per row, as a real resume has
        c.drawString(50, y, line)
        y -= 20
    c.save()
    return buf.getvalue()


def _item(plan, skill):
    return next(it for it in plan["items"] if it["skill"] == skill)


# ---------- skill-level progress ----------

def test_first_view_records_baseline_and_reports_it():
    _, _, h = _user()
    plan = client.get("/plan", params={"role": "Backend Engineer"}, headers=h).json()
    py = _item(plan, "Python")
    assert py["progress"]["baseline_score"] == 0.0
    assert py["progress"]["score_change"] is None or py["progress"]["score_change"] == 0.0


def test_new_evidence_shows_a_score_change_against_the_baseline():
    uid, _, h = _user()
    client.get("/plan", params={"role": "Backend Engineer"}, headers=h)  # baseline: Python at 0
    client.post(f"/resume/upload/{uid}", headers=h,
                files={"file": ("cv.pdf", _pdf("Prog Tester\nSkills: Python, FastAPI"), "application/pdf")})
    plan = client.get("/plan", params={"role": "Backend Engineer"}, headers=h).json()
    py = _item(plan, "Python")
    assert py["progress"]["baseline_score"] == 0.0
    assert 40 <= py["progress"]["current_score"] < 60
    assert py["progress"]["score_change"] == py["progress"]["current_score"]  # measured from the 0 baseline
    assert "Up " in py["progress"]["message"]


def test_ticked_tasks_without_a_score_change_say_so():
    _, _, h = _user()
    client.get("/plan", params={"role": "Backend Engineer"}, headers=h)
    client.post("/plan/tasks/python:task0", params={"role": "Backend Engineer"}, json={"done": True}, headers=h)
    plan = client.get("/plan", params={"role": "Backend Engineer"}, headers=h).json()
    py = _item(plan, "Python")
    assert py["progress"]["tasks_done"] == 1
    assert "score has not moved yet" in py["progress"]["message"]


def test_daily_accuracy_per_skill_is_on_the_plan():
    uid, _, h = _user()
    client.get("/plan", params={"role": "Backend Engineer"}, headers=h)
    db = SessionLocal()
    try:
        db.add(DailyAttempt(user_id=uid, day="2000-01-01", challenge_id="x", skill="python",
                            answer_index=0, correct=True, points=10))
        db.commit()
    finally:
        db.close()
    plan = client.get("/plan", params={"role": "Backend Engineer"}, headers=h).json()
    # the old attempt is outside the 30-day window, so it must not count
    assert _item(plan, "Python")["progress"]["daily_attempts"] == 0


# ---------- reminders ----------

def test_reminder_rule_is_evening_and_unanswered_only():
    assert should_remind_now(answered_today=False, local_hour=18) is True
    assert should_remind_now(answered_today=False, local_hour=23) is True
    assert should_remind_now(answered_today=False, local_hour=9) is False
    assert should_remind_now(answered_today=True, local_hour=20) is False
    assert should_remind_now(answered_today=False, local_hour=None) is False


def test_status_endpoint_reflects_time_and_answers():
    _, _, h = _user()
    evening = client.get("/daily/status", params={"local_hour": 20}, headers=h).json()
    assert evening["remind_now"] is True and evening["answered_today"] is False
    morning = client.get("/daily/status", params={"local_hour": 8}, headers=h).json()
    assert morning["remind_now"] is False
    assert client.get("/daily/status", params={"local_hour": 30}, headers=h).status_code == 400


def test_reminder_settings_default_off_and_can_be_changed():
    _, _, h = _user()
    assert client.get("/reminders/settings", headers=h).json() == {"email_opt_in": False}
    assert client.put("/reminders/settings", json={"email_opt_in": True}, headers=h).json() == {"email_opt_in": True}
    assert client.get("/reminders/settings", headers=h).json() == {"email_opt_in": True}


def test_only_opted_in_users_who_have_not_answered_get_email():
    uid_in, _, h_in = _user()
    uid_out, _, _ = _user()
    uid_done, _, h_done = _user()
    client.put("/reminders/settings", json={"email_opt_in": True}, headers=h_in)
    client.put("/reminders/settings", json={"email_opt_in": True}, headers=h_done)
    db = SessionLocal()
    try:
        from app.services.reminders import today_utc_iso
        today = today_utc_iso()
        db.add(DailyAttempt(user_id=uid_done, day=today, challenge_id="x", skill="python",
                            answer_index=0, correct=True, points=10))
        db.commit()
        ids = {u.id for u in users_to_email(db, today)}
    finally:
        db.close()
    assert uid_in in ids
    assert uid_out not in ids  # never opted in
    assert uid_done not in ids  # already answered today


def test_reminder_email_mentions_streak_and_link_and_opt_out():
    subject, body = build_reminder_email("Asha", 4, "https://skilldna.example")
    assert "streak" in body and "4-day" in body
    assert "https://skilldna.example/app/daily" in body
    assert "turned on reminders" in body
    assert subject
    _, plain = build_reminder_email("", 0, "https://x")
    assert plain.startswith("Hi there")
