"""Daily challenge: one question per day, a streak and points.

GET  /daily/today?role=...     today's challenge (answer hidden until answered)
POST /daily/answer             answer today's challenge once
GET  /daily/history            last 30 days, streak and total points
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import DailyAttempt, User
from app.routers.auth import get_current_user
from app.services.daily_engine import current_streak, grade, pick_challenge
from app.services.mock_content import ROLE_SKILLS
from app.services.roadmap import _gaps_for_role
from app.services.scoring_engine import build_report

router = APIRouter(prefix="/daily", tags=["daily"])


class AnswerRequest(BaseModel):
    challenge_id: str
    answer_index: int | None = None  # multiple choice
    answer_text: str | None = None  # free-text challenges
    role: str = "Full-Stack Developer"


MAX_TEXT_ANSWER_CHARS = 500


def _today() -> datetime.date:
    return datetime.now(timezone.utc).date()


def public_challenge(challenge: dict) -> dict:
    """What the client may see before answering: never the answer or keywords."""
    base = {"id": challenge["id"], "skill": challenge["skill"], "question": challenge["question"],
            "kind": challenge.get("kind", "mcq")}
    if base["kind"] == "mcq":
        base["options"] = challenge["options"]
    else:
        base["min_hits"] = challenge["min_hits"]
    return base


def _todays_challenge(db: Session, user: User, role: str) -> dict:
    if role not in ROLE_SKILLS:
        raise HTTPException(status_code=400, detail="Unknown role")
    report = build_report(db, user.id)
    gap_skills = [g["skill"] for g in _gaps_for_role(role, report.get("all_scores", []))]
    return pick_challenge(user.id, _today(), gap_skills, ROLE_SKILLS[role])


def _answered_days(db: Session, user: User) -> set:
    rows = db.query(DailyAttempt.day).filter(DailyAttempt.user_id == user.id).all()
    return {datetime.strptime(r[0], "%Y-%m-%d").date() for r in rows}


@router.get("/today")
def get_today(role: str = "Full-Stack Developer", local_hour: int | None = None,
              user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Today's question, with the reminder state folded in so the page makes one request."""
    from app.models.db_models import ReminderSetting
    from app.services.reminders import should_remind_now
    if local_hour is not None and not 0 <= local_hour <= 23:
        raise HTTPException(status_code=400, detail="local_hour must be 0-23")
    today = _today()
    challenge = _todays_challenge(db, user, role)
    attempt = db.query(DailyAttempt).filter(
        DailyAttempt.user_id == user.id, DailyAttempt.day == today.isoformat()).first()
    streak = current_streak(_answered_days(db, user), today)
    total_points = sum(r[0] for r in db.query(DailyAttempt.points).filter(DailyAttempt.user_id == user.id).all())

    body = {
        "date": today.isoformat(),
        "role": role,
        "streak": streak,
        "total_points": total_points,
        "explore": challenge["explore"],
        "challenge": public_challenge(challenge),
        "answered": attempt is not None,
        "result": None,
    }
    reminder = db.query(ReminderSetting).filter(ReminderSetting.user_id == user.id).first()
    body["email_opt_in"] = bool(reminder and reminder.email_opt_in)
    body["remind_now"] = should_remind_now(attempt is not None, local_hour)
    if attempt is not None:
        body["result"] = {
            "correct": attempt.correct,
            "your_index": attempt.answer_index if attempt.answer_index >= 0 else None,
            "correct_index": challenge.get("answer"),
            "accepted": challenge.get("keywords"),
            "explanation": challenge["explanation"],
            "points": attempt.points,
        }
    return body


@router.post("/answer")
def answer_today(payload: AnswerRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = _today()
    challenge = _todays_challenge(db, user, payload.role)
    if payload.challenge_id != challenge["id"]:
        raise HTTPException(status_code=400, detail="That is not today's challenge")
    is_text = challenge.get("kind") == "text"
    if is_text:
        text = (payload.answer_text or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="Type an answer first")
        if len(text) > MAX_TEXT_ANSWER_CHARS:
            raise HTTPException(status_code=400, detail="Answer is too long")
        stored_index = -1  # free-text answers are graded once and not kept
    else:
        if payload.answer_index is None or not 0 <= payload.answer_index < len(challenge["options"]):
            raise HTTPException(status_code=400, detail="Choose one option")
        stored_index = payload.answer_index
    if db.query(DailyAttempt).filter(DailyAttempt.user_id == user.id,
                                     DailyAttempt.day == today.isoformat()).first():
        raise HTTPException(status_code=409, detail="You already answered today's challenge")

    result = grade(challenge, answer_index=payload.answer_index, answer_text=payload.answer_text)
    db.add(DailyAttempt(
        user_id=user.id, day=today.isoformat(), challenge_id=challenge["id"], skill=challenge["skill"],
        answer_index=stored_index, correct=result["correct"], points=result["points"],
    ))
    db.commit()
    streak = current_streak(_answered_days(db, user), today)
    return {**result, "streak": streak}


@router.get("/status")
def status(local_hour: int | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """What the page needs to decide on an in-app reminder. local_hour is the user's own hour (0-23)."""
    from app.models.db_models import ReminderSetting
    from app.services.reminders import should_remind_now
    today = _today()
    answered = db.query(DailyAttempt).filter(
        DailyAttempt.user_id == user.id, DailyAttempt.day == today.isoformat()).first() is not None
    if local_hour is not None and not 0 <= local_hour <= 23:
        raise HTTPException(status_code=400, detail="local_hour must be 0-23")
    row = db.query(ReminderSetting).filter(ReminderSetting.user_id == user.id).first()
    return {
        "answered_today": answered,
        "remind_now": should_remind_now(answered, local_hour),
        "streak": current_streak(_answered_days(db, user), today),
        "email_opt_in": bool(row and row.email_opt_in),
    }


@router.get("/history")
def history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    since = (_today() - timedelta(days=30)).isoformat()
    rows = (db.query(DailyAttempt)
            .filter(DailyAttempt.user_id == user.id, DailyAttempt.day >= since)
            .order_by(DailyAttempt.day.desc()).all())
    total = sum(r.points for r in db.query(DailyAttempt).filter(DailyAttempt.user_id == user.id).all())
    return {
        "streak": current_streak(_answered_days(db, user), _today()),
        "total_points": total,
        "days": [{"day": r.day, "skill": r.skill, "correct": r.correct, "points": r.points} for r in rows],
    }
