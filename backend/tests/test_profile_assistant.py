"""Profile, role recommendations, the daily honest note, the assistant's context, and the export."""
import io
import os
import sys
import uuid
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DATABASE_URL", f"sqlite:////tmp/skilldna_profile_test_{uuid.uuid4().hex}.db")
os.environ.pop("ANTHROPIC_API_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.services.mock_content import ROLE_SKILLS  # noqa: E402
from app.services.motto import MOTTOS, daily_motto  # noqa: E402
from app.services.roles import recommend_roles  # noqa: E402
from app.services.assistant_context import intent_for, week_schedule  # noqa: E402

client = TestClient(app)


def _account(name="Priya Nair"):
    email = f"prof{uuid.uuid4().hex[:12]}@gmail.com"
    r = client.post("/auth/register", json={"name": name, "email": email, "password": "TestPass123!"})
    body = r.json()
    return body["user"]["id"], {"Authorization": f"Bearer {body['token']}"}


def _resume(lines):
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for line in lines:
        c.drawString(50, y, line)
        y -= 20
    c.save()
    return buf.getvalue()


# ---------- roles and the honest note ----------

def test_roles_are_ranked_by_how_much_of_the_role_the_user_already_shows():
    scores = [{"skill_name": s.lower(), "score": 80.0} for s in ROLE_SKILLS["Data Analyst"]]
    ranked = recommend_roles(scores)
    assert ranked[0]["role"] == "Data Analyst"
    assert ranked[0]["fit"] >= 79
    assert ranked[0]["missing"] == []


def test_a_role_recommendation_names_the_gap_not_just_a_percentage():
    ranked = recommend_roles([{"skill_name": "python", "score": 70.0}])
    top = ranked[0]
    assert "Not yet shown" in top["reason"] or top["reason"].startswith("You have no evidence")
    assert all(role["fit"] >= 0 for role in ranked)


def test_the_daily_note_is_one_of_the_honest_thoughts():
    assert daily_motto(date(2026, 10, 12)) in MOTTOS
    assert any("honest" in m.lower() for m in MOTTOS)


# ---------- the profile ----------

def test_a_new_profile_has_the_identity_summary_and_achievements():
    _, h = _account("Priya Nair")
    body = client.get("/profile", headers=h).json()
    assert body["name"] == "Priya Nair" and body["email"].endswith("@gmail.com")
    assert body["motto"] in MOTTOS
    assert len(body["recommendations"]) == 3
    assert {a["id"] for a in body["achievements"]} >= {"first-evidence", "streak-3", "phase-cleared"}
    assert all(a["earned"] is False for a in body["achievements"] if a["id"] == "first-evidence")


def test_the_history_shows_what_happened_across_features():
    uid, h = _account()
    client.get("/plan", params={"role": "Backend Engineer"}, headers=h)
    client.post("/resume/upload/%d" % uid, headers=h, files={"file": ("cv.pdf", _resume(["Priya Nair", "Skills: Python"]), "application/pdf")})
    client.post("/interview/sessions", json={"role": "Backend Engineer"}, headers=h)
    history = client.get("/profile", headers=h).json()["history"]
    kinds = {item["kind"] for item in history}
    assert {"plan", "upload", "interview"} <= kinds
    assert all("title" in item and "detail" in item for item in history)


def test_an_earned_achievement_shows_once_evidence_is_counted():
    uid, h = _account()
    client.post("/resume/upload/%d" % uid, headers=h, files={"file": ("cv.pdf", _resume(["Priya Nair", "Skills: Python"]), "application/pdf")})
    achievements = {a["id"]: a["earned"] for a in client.get("/profile", headers=h).json()["achievements"]}
    assert achievements["first-evidence"] is True


def test_the_target_role_can_be_chosen_and_cleared():
    _, h = _account()
    r = client.put("/profile/target-role", json={"role": "Cloud Engineer"}, headers=h).json()
    assert r["target_role"] == "Cloud Engineer"
    assert client.get("/profile", headers=h).json()["effective_role"] == "Cloud Engineer"
    assert client.put("/profile/target-role", json={"role": "Astronaut"}, headers=h).status_code == 400
    cleared = client.put("/profile/target-role", json={"role": None}, headers=h).json()
    assert cleared["target_role"] is None and cleared["effective_role"] in ROLE_SKILLS


def test_the_assistant_setting_can_be_switched_off():
    _, h = _account()
    assert client.put("/profile/settings", json={"assistant_context": False}, headers=h).json() == {"assistant_context": False}
    assert client.get("/profile", headers=h).json()["assistant_context"] is False


def test_recommendations_are_available_from_the_profile():
    _, h = _account()
    ranked = client.get("/profile/recommendations", headers=h).json()
    assert len(ranked) == len(ROLE_SKILLS)


def test_the_export_contains_the_records_but_not_document_text():
    uid, h = _account()
    client.post("/resume/upload/%d" % uid, headers=h, files={"file": ("cv.pdf", _resume(["Priya Nair", "Skills: Python"]), "application/pdf")})
    r = client.get("/profile/export", headers=h)
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    data = r.json()
    assert {"skills", "uploads", "interviews", "mock_sessions"} <= set(data)
    assert "raw_text" not in str(data)


def test_the_profile_needs_a_signed_in_user():
    assert client.get("/profile").status_code == 401


# ---------- the personal assistant ----------

def test_intents_are_recognised():
    assert intent_for("What should I do next?") == "next"
    assert intent_for("Plan my week") == "week"
    assert intent_for("How am I doing?") == "progress"
    assert intent_for("Which role fits me?") == "roles"
    assert intent_for("How do uploads work?") is None


def test_the_assistant_gives_a_personal_next_step_when_signed_in():
    _, h = _account()
    r = client.post("/assistant/chat", json={"message": "What should I do next?", "history": []}, headers=h).json()
    assert r["personalised"] is True
    assert r["source"] == "plan" and r["reply"]


def test_the_assistant_works_without_signing_in_and_uses_no_personal_data():
    r = client.post("/assistant/chat", json={"message": "What should I do next?", "history": []}).json()
    assert r["personalised"] is False
    assert r["source"] == "faq"


def test_the_week_plan_covers_seven_days_in_plan_order():
    _, h = _account()
    schedule = client.post("/assistant/action", json={"action": "week"}, headers=h).json()["data"]["schedule"]
    assert len(schedule) == 7
    assert schedule[0]["tasks"]


def test_actions_need_a_signed_in_user_who_allows_it():
    _, h = _account()
    client.put("/profile/settings", json={"assistant_context": False}, headers=h)
    assert client.post("/assistant/action", json={"action": "next"}, headers=h).status_code == 403
    assert client.post("/assistant/action", json={"action": "next"}).status_code == 401


def test_the_week_schedule_spreads_tasks_without_losing_any():
    plan = {"items": [{"locked": False, "skill": "Python", "tasks": [
        {"text": f"t{i}", "done": False, "videos": []} for i in range(10)]}], "phases": []}
    schedule = week_schedule(plan, today=date(2026, 10, 12))
    assert sum(len(d["tasks"]) for d in schedule) == 10
    assert len(schedule) == 7


def test_a_new_user_with_no_evidence_gets_the_default_role_not_an_arbitrary_one():
    _, h = _account("Nina Rao")
    body = client.get("/profile", headers=h).json()
    assert body["effective_role"] == "Full-Stack Developer"


def test_the_profile_lists_each_document_with_the_name_read_and_whether_it_was_counted():
    uid, h = _account("Priya Nair")
    client.post(f"/resume/upload/{uid}", headers=h, files={"file": ("cv.pdf", _resume(["Priya Nair", "Skills: Python"]), "application/pdf")})
    client.post(f"/resume/upload/{uid}", headers=h, files={"file": ("other.pdf", _resume(["Rahul Patel", "Skills: Java"]), "application/pdf")})
    docs = client.get("/profile", headers=h).json()["documents"]
    statuses = {d["name_read"]: d["status"] for d in docs if d["source"] == "resume"}
    assert statuses.get("Priya Nair") == "processed" or statuses.get("Priya Nair") == "superseded"
    assert statuses.get("Rahul Patel") == "name_mismatch"
    assert all("raw_text" not in d for d in docs)
