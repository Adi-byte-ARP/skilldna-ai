"""The profile: identity, target role, skill summary, achievements, a merged history, and an export.

The history combines every feature's record into one timeline: uploads, plan snapshots, daily
answers, phase tests, mock tests and AI interviews. The export contains the user's records but
never the raw text of their documents.
"""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.db_models import (
    DailyAttempt, InterviewSession, MockSession, PhaseAttempt, PlanSnapshot, Submission, User,
)
from app.services.motto import daily_motto
from app.services.mock_content import ROLE_SKILLS
from app.services.roles import recommend_roles
from app.services.roadmap import _pretty
from app.services.scoring_engine import build_report

HISTORY_LIMIT = 80


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc).isoformat() if value.tzinfo is None else value.isoformat()
    return str(value)


def _streak(days: set[date], today: date) -> int:
    cursor = today if today in days else today - timedelta(days=1)
    count = 0
    while cursor in days:
        count += 1
        cursor -= timedelta(days=1)
    return count


DEFAULT_ROLE = "Full-Stack Developer"  # used until there is evidence to rank roles by


def recommended_role(db: Session, user: User) -> str:
    report = build_report(db, user.id)
    ranked = recommend_roles(report.get("all_scores", []))
    # With no evidence every role scores 0, so ranking would be arbitrary. Use the default instead.
    if not ranked or ranked[0]["fit"] <= 0:
        return DEFAULT_ROLE
    return ranked[0]["role"]


def effective_role(db: Session, user: User) -> str:
    if user.target_role in ROLE_SKILLS:
        return user.target_role
    return recommended_role(db, user)


def _history(db: Session, user: User) -> list[dict]:
    items = []
    for row in db.query(Submission).filter(Submission.user_id == user.id).order_by(Submission.id.desc()).limit(30):
        status_text = {"processed": "counted", "duplicate": "already on your profile, not counted",
                       "name_mismatch": "name does not match, not counted",
                       "name_unverified": "no name found, not counted",
                       "superseded": "replaced by a newer upload", "failed": "could not be read"}.get(row.status, row.status)
        items.append({"at": _iso(row.created_at) if hasattr(row, "created_at") else None,
                      "kind": "upload", "title": f"{row.source_type.capitalize()} · {row.original_filename or 'upload'}",
                      "detail": status_text, "tone": "teal" if row.status == "processed" else "coral"})
    for row in db.query(PlanSnapshot).filter(PlanSnapshot.user_id == user.id).order_by(PlanSnapshot.day.desc()).limit(30):
        items.append({"at": row.day, "kind": "plan", "title": f"Plan · {row.role}",
                      "detail": f"{round(row.progress_percent)}% of tasks ticked · {round(row.overall_score)}/100 score",
                      "tone": "violet"})
    for row in db.query(DailyAttempt).filter(DailyAttempt.user_id == user.id).order_by(DailyAttempt.day.desc()).limit(30):
        items.append({"at": row.day, "kind": "daily", "title": f"Daily challenge · {row.skill}",
                      "detail": f"{'correct' if row.correct else 'missed'} · +{row.points} points",
                      "tone": "teal" if row.correct else "coral"})
    for row in db.query(PhaseAttempt).filter(PhaseAttempt.user_id == user.id).order_by(PhaseAttempt.id.desc()).limit(20):
        items.append({"at": _iso(row.created_at), "kind": "phase", "title": f"Phase {row.phase_index + 1} test · {row.role}",
                      "detail": f"{round(row.score)}% · {'passed' if row.passed else 'not passed'}",
                      "tone": "teal" if row.passed else "coral"})
    for row in db.query(MockSession).filter(MockSession.user_id == user.id).order_by(MockSession.id.desc()).limit(20):
        score = (row.result or {}).get("score")
        ended = {"integrity": "auto-submitted: cheating signals", "violations": "ended: too many violations",
                 "submitted": "submitted"}.get(row.end_reason or "", row.status)
        items.append({"at": _iso(row.started_at), "kind": "mock",
                      "title": f"{'Mock test' if row.kind == 'test' else 'Mock interview'} · {row.role}",
                      "detail": f"{round(score) if score is not None else '–'}/100 · {ended}",
                      "tone": "coral" if row.end_reason in ("integrity", "violations") else "violet"})
    for row in db.query(InterviewSession).filter(InterviewSession.user_id == user.id).order_by(InterviewSession.id.desc()).limit(20):
        ended = {"integrity": "auto-submitted: integrity", "completed": "completed"}.get(row.end_reason or "", "in progress")
        items.append({"at": _iso(row.started_at), "kind": "interview", "title": f"AI interview · {row.role}",
                      "detail": f"{round(row.overall) if row.overall is not None else '–'}/100 · {ended}",
                      "tone": "coral" if row.end_reason == "integrity" else "violet"})

    def sort_key(item):
        return str(item.get("at") or "")

    items.sort(key=sort_key, reverse=True)
    return items[:HISTORY_LIMIT]


def _achievements(db: Session, user: User, streak: int) -> list[dict]:
    processed_sources = {r.source_type for r in db.query(Submission.source_type).filter(
        Submission.user_id == user.id, Submission.status == "processed").all()}
    phases_passed = db.query(PhaseAttempt).filter(PhaseAttempt.user_id == user.id, PhaseAttempt.passed.is_(True)).count()
    clean_mock = db.query(MockSession).filter(MockSession.user_id == user.id, MockSession.status == "submitted").count()
    honest_interview = db.query(InterviewSession).filter(
        InterviewSession.user_id == user.id, InterviewSession.end_reason == "completed",
        InterviewSession.overall >= 60).count()
    items = [
        ("first-evidence", "First evidence", "Your first counted upload.", bool(processed_sources)),
        ("two-sources", "Cross-checked", "Two different sources agree on your skills.", len(processed_sources) >= 2),
        ("all-sources", "Full picture", "Resume, GitHub, LinkedIn and certificates all counted.", len(processed_sources) >= 4),
        ("streak-3", "Three-day streak", "Answered the daily challenge three days in a row.", streak >= 3),
        ("phase-cleared", "Phase cleared", "Passed a phase test and unlocked the next phase.", phases_passed >= 1),
        ("clean-test", "Clean test", "Finished a mock test without any violation.", clean_mock >= 1),
        ("honest-interview", "Honest interview", "Completed an AI interview with a score of 60 or more.", honest_interview >= 1),
    ]
    return [{"id": i, "title": t, "detail": d, "earned": e} for i, t, d, e in items]


def _documents(db: Session, user: User) -> list[dict]:
    """Every uploaded document, the name read from it, and whether it was counted. No document text."""
    rows = (db.query(Submission).filter(Submission.user_id == user.id)
            .order_by(Submission.id.desc()).limit(30).all())
    return [{
        "id": r.id,
        "source": r.source_type,
        "file": r.original_filename,
        "status": r.status,
        "name_read": r.detected_name,
        "message": r.error_message,
        "uploaded_at": _iso(r.created_at),
    } for r in rows]


def build_profile(db: Session, user: User) -> dict:
    report = build_report(db, user.id)
    scores = report.get("all_scores", [])
    ranked = sorted(scores, key=lambda s: -(s["score"] if isinstance(s, dict) else s.score))
    names = [(s["skill_name"], s["score"]) if isinstance(s, dict) else (s.skill_name, s.score) for s in ranked]
    today = date.today()
    days = {r.day for r in db.query(DailyAttempt.day).filter(DailyAttempt.user_id == user.id).all()}
    days = {date.fromisoformat(d) for d in days}
    streak = _streak(days, today)
    points = sum(r[0] for r in db.query(DailyAttempt.points).filter(DailyAttempt.user_id == user.id).all())
    recommendations = recommend_roles(scores)[:3]
    return {
        "name": user.name,
        "email": user.email,
        "target_role": user.target_role,
        "effective_role": effective_role(db, user),
        "assistant_context": bool(user.assistant_context),
        "motto": daily_motto(today),
        "summary": {
            "overall": report.get("overall_score", 0),
            "tier": report.get("tier"),
            "skills": len(scores),
            "strengths": [_pretty(n) for n, s in names if s >= 60][:5],
            "gaps": [_pretty(n) for n, s in reversed(names) if s < 60][:5],
        },
        "recommendations": recommendations,
        "stats": {
            "streak": streak,
            "daily_points": points,
            "plan_snapshots": db.query(PlanSnapshot).filter(PlanSnapshot.user_id == user.id).count(),
            "mock_sessions": db.query(MockSession).filter(MockSession.user_id == user.id).count(),
            "interviews_finished": db.query(InterviewSession).filter(
                InterviewSession.user_id == user.id, InterviewSession.status == "finished").count(),
            "phases_passed": db.query(PhaseAttempt).filter(PhaseAttempt.user_id == user.id, PhaseAttempt.passed.is_(True)).count(),
        },
        "achievements": _achievements(db, user, streak),
        "history": _history(db, user),
        "documents": _documents(db, user),
    }


def export_profile(db: Session, user: User) -> dict:
    """Everything the account holds, without the raw text of documents."""
    report = build_report(db, user.id)
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "account": {"name": user.name, "email": user.email, "target_role": user.target_role,
                    "assistant_context": bool(user.assistant_context)},
        "skills": [{"skill": s["skill_name"], "score": s["score"], "sources": s["sources"]}
                   if isinstance(s, dict) else {"skill": s.skill_name, "score": s.score, "sources": s.sources}
                   for s in report.get("all_scores", [])],
        "uploads": [{"source": r.source_type, "file": r.original_filename, "status": r.status,
                     "name_read": r.detected_name} for r in db.query(Submission).filter(Submission.user_id == user.id).all()],
        "plan_snapshots": [{"day": r.day, "role": r.role, "score": r.overall_score, "progress": r.progress_percent}
                           for r in db.query(PlanSnapshot).filter(PlanSnapshot.user_id == user.id).all()],
        "daily_answers": [{"day": r.day, "skill": r.skill, "correct": r.correct, "points": r.points}
                          for r in db.query(DailyAttempt).filter(DailyAttempt.user_id == user.id).all()],
        "phase_tests": [{"role": r.role, "phase": r.phase_index + 1, "score": r.score, "passed": r.passed}
                        for r in db.query(PhaseAttempt).filter(PhaseAttempt.user_id == user.id).all()],
        "mock_sessions": [{"role": r.role, "kind": r.kind, "status": r.status, "end_reason": r.end_reason,
                           "violations": len(r.violations or []), "integrity_points": r.integrity_points}
                          for r in db.query(MockSession).filter(MockSession.user_id == user.id).all()],
        "interviews": [{"role": r.role, "status": r.status, "overall": r.overall, "end_reason": r.end_reason,
                        "turns": (r.state or {}).get("turns", [])}
                       for r in db.query(InterviewSession).filter(InterviewSession.user_id == user.id).all()],
    }
