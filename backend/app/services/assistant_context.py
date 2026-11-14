"""What the personal assistant knows about a user, and the actions it can take.

The assistant reads only a summary: the target role, the score, the next task, the week's plan,
streak and recent results. It never reads documents. Nothing is used when the user has switched
"let the assistant use my progress" off in their profile.
"""
import math
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.db_models import User
from app.services.profile import effective_role, _streak
from app.services.roadmap import _pretty
from app.services.scoring_engine import build_report
from app.models.db_models import DailyAttempt, InterviewSession, MockSession


def _plan(db: Session, user: User, role: str) -> dict:
    from app.routers.plan import _full_plan  # imported here: the plan router depends on services, not the reverse
    return _full_plan(db, user, role, record_baselines=False)


def next_task(plan: dict) -> dict | None:
    for item in plan["items"]:
        if item.get("locked"):
            continue
        for task in item["tasks"]:
            if not task["done"]:
                return {"skill": item["skill"], "task": task["text"], "key": task["key"],
                        "video": task["videos"][0]["url"] if task.get("videos") else None}
    return None


def ready_phase_test(plan: dict) -> int | None:
    for index, phase in enumerate(plan["phases"]):
        if phase.get("test", {}).get("available"):
            return index
    return None


def week_schedule(plan: dict, today: date | None = None, days: int = 7) -> list[dict]:
    """Spread the remaining tasks over the next `days` days, in plan order."""
    today = today or date.today()
    remaining = []
    for item in plan["items"]:
        if item.get("locked"):
            continue
        for task in item["tasks"]:
            if not task["done"]:
                remaining.append({"skill": item["skill"], "task": task["text"],
                                  "video": task["videos"][0]["url"] if task.get("videos") else None})
    per_day = max(1, math.ceil(len(remaining) / days)) if remaining else 0
    schedule = []
    for offset in range(days):
        chunk = remaining[offset * per_day:(offset + 1) * per_day]
        entry = {"day": (today + timedelta(days=offset)).isoformat(), "tasks": chunk}
        if offset == days - 1:
            phase = ready_phase_test(plan)
            if phase is not None:
                entry["phase_test"] = phase + 1
        schedule.append(entry)
    return schedule


def assistant_context(db: Session, user: User) -> dict | None:
    if not user.assistant_context:
        return None
    role = effective_role(db, user)
    plan = _plan(db, user, role)
    report = build_report(db, user.id)
    scores = report.get("all_scores", [])
    names = sorted(((s["skill_name"], s["score"]) if isinstance(s, dict) else (s.skill_name, s.score) for s in scores),
                   key=lambda x: -x[1])
    days = {date.fromisoformat(r.day) for r in db.query(DailyAttempt.day).filter(DailyAttempt.user_id == user.id).all()}
    last_mock = db.query(MockSession).filter(MockSession.user_id == user.id).order_by(MockSession.id.desc()).first()
    last_interview = db.query(InterviewSession).filter(InterviewSession.user_id == user.id,
                                                       InterviewSession.status == "finished").order_by(
        InterviewSession.id.desc()).first()
    return {
        "first_name": (user.name or "").split(" ")[0],
        "role": role,
        "overall": report.get("overall_score", 0),
        "tier": report.get("tier"),
        "strengths": [_pretty(n) for n, s in names if s >= 60][:3],
        "gaps": [_pretty(n) for n, s in reversed(names) if s < 60][:3],
        "next_task": next_task(plan),
        "phase_test": (ready_phase_test(plan) or None) and ready_phase_test(plan) + 1,
        "streak": _streak(days, date.today()),
        "last_mock_score": round((last_mock.result or {}).get("score", 0)) if last_mock and last_mock.result else None,
        "last_interview": round(last_interview.overall) if last_interview and last_interview.overall is not None else None,
        "plan": plan,
    }


def action_reply(action: str, ctx: dict) -> dict:
    if action == "next":
        nxt = ctx["next_task"]
        if ctx.get("phase_test"):
            text = f"Take the Phase {ctx['phase_test']} test. Every task in that phase is ticked, so it is ready."
        elif nxt:
            text = f"Next: {nxt['task']} ({nxt['skill']})."
        else:
            text = "Nothing left in your open phases. Take the next phase test or try a mock interview."
        return {"reply": text, "source": "plan", "data": {"next_task": nxt, "phase_test": ctx.get("phase_test")}}
    if action == "week":
        schedule = week_schedule(ctx["plan"])
        first = [d for d in schedule if d["tasks"]][:3]
        text = "Your next few days: " + "; ".join(
            f"{d['day']}: " + ", ".join(t["skill"] for t in d["tasks"]) for d in first) + "." if first else \
            "There are no open tasks this week."
        return {"reply": text, "source": "plan", "data": {"schedule": schedule}}
    if action == "progress":
        bits = [f"Your score is {round(ctx['overall'])}/100 ({ctx['tier']})."]
        if ctx["streak"]:
            bits.append(f"You are on a {ctx['streak']}-day streak.")
        if ctx["last_mock_score"] is not None:
            bits.append(f"Your last mock test scored {ctx['last_mock_score']}.")
        if ctx["last_interview"] is not None:
            bits.append(f"Your last interview scored {ctx['last_interview']}.")
        if ctx["gaps"]:
            bits.append("Focus next on " + ", ".join(ctx["gaps"]) + ".")
        return {"reply": " ".join(bits), "source": "profile", "data": {}}
    if action == "roles":
        return {"reply": f"Your plan targets {ctx['role']}. Your profile lists the roles that fit your evidence best, with the gaps for each.",
                "source": "profile", "data": {}}
    raise ValueError("unknown action")


def intent_for(question: str) -> str | None:
    q = (question or "").lower()
    if any(p in q for p in ("next step", "what should i do", "what now", "next task", "what next")):
        return "next"
    if any(p in q for p in ("week", "schedule", "plan my", "this week")):
        return "week"
    if any(p in q for p in ("how am i", "progress", "how is my", "how am i doing")):
        return "progress"
    if any(p in q for p in ("which role", "what role", "career", "job for me", "roles fit")):
        return "roles"
    return None
