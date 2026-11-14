"""Reminder rules for the daily challenge.

Two kinds of reminder, both opt-in:
  - In the app: a notice on the daily page after REMIND_AFTER_LOCAL_HOUR, while today's question is open.
  - By email: only for users who turned on email reminders. Sent by scripts/send_reminders.py.
The email uses the UTC date, the same date the daily challenge uses.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.db_models import DailyAttempt, ReminderSetting, User

REMIND_AFTER_LOCAL_HOUR = 18  # 6 pm in the user's own clock


def today_utc_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def should_remind_now(answered_today: bool, local_hour: int | None) -> bool:
    """True when today's question is still open and it is evening for the user."""
    if answered_today or local_hour is None:
        return False
    return local_hour >= REMIND_AFTER_LOCAL_HOUR


def users_to_email(db: Session, day_iso: str) -> list[User]:
    """Opted-in users with an email address who have not answered for `day_iso`."""
    opted_in = (
        db.query(User)
        .join(ReminderSetting, ReminderSetting.user_id == User.id)
        .filter(ReminderSetting.email_opt_in.is_(True), User.email.isnot(None))
        .all()
    )
    answered = {row[0] for row in db.query(DailyAttempt.user_id).filter(DailyAttempt.day == day_iso).all()}
    return [u for u in opted_in if u.id not in answered]


def build_reminder_email(name: str, streak: int, app_url: str) -> tuple[str, str]:
    subject = "Today's SkillDNA challenge is still open"
    streak_line = (f"You are on a {streak}-day streak. Keep it going." if streak
                   else "One question takes about a minute.")
    body = (
        f"Hi {name or 'there'},\n\n"
        "You have not answered today's SkillDNA daily challenge yet.\n"
        f"{streak_line}\n\n"
        f"Open it here: {app_url}/app/daily\n\n"
        "You get this email because you turned on reminders. Turn them off in the app any time."
    )
    return subject, body
