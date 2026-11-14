"""Send the daily-challenge reminder email to users who opted in and have not answered today.

Safe by default: without --send it only prints who would be emailed. Sending needs SMTP settings
(SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM) and APP_URL.

Schedule it with cron or a task scheduler, for example once an evening:
    python backend/scripts/send_reminders.py --send
"""
import argparse
import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from app.database import SessionLocal  # noqa: E402
from datetime import date  # noqa: E402

from app.models.db_models import DailyAttempt  # noqa: E402
from app.services.daily_engine import current_streak  # noqa: E402
from app.services.reminders import build_reminder_email, today_utc_iso, users_to_email  # noqa: E402


def streak_for(db, user_id: int, today_iso: str) -> int:
    rows = db.query(DailyAttempt.day).filter(DailyAttempt.user_id == user_id).all()
    days = {date.fromisoformat(r[0]) for r in rows}
    return current_streak(days, date.fromisoformat(today_iso))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true", help="actually send the emails (default: dry run)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        today = today_utc_iso()
        recipients = users_to_email(db, today)
        if not recipients:
            print("No opted-in users still need a reminder today.")
            return 0
        app_url = os.getenv("APP_URL", "http://localhost:5173")
        print(f"{len(recipients)} user(s) to remind for {today}:")
        if not args.send:
            for u in recipients:
                print(f"  would email {u.email}")
            print("Dry run. Re-run with --send to deliver.")
            return 0

        host = os.getenv("SMTP_HOST")
        if not host:
            print("SMTP_HOST is not set, so nothing was sent.", file=sys.stderr)
            return 2
        sender = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", ""))
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=30) as smtp:
            smtp.starttls()
            if os.getenv("SMTP_USER"):
                smtp.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD", ""))
            for u in recipients:
                subject, body = build_reminder_email(u.name, streak_for(db, u.id, today), app_url)
                msg = EmailMessage()
                msg["From"], msg["To"], msg["Subject"] = sender, u.email, subject
                msg.set_content(body)
                smtp.send_message(msg)
                print(f"  sent to {u.email}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
