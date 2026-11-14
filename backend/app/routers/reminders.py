"""Reminder settings. Email reminders are off until the user turns them on."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import ReminderSetting, User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/reminders", tags=["reminders"])


class ReminderUpdate(BaseModel):
    email_opt_in: bool


@router.get("/settings")
def get_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(ReminderSetting).filter(ReminderSetting.user_id == user.id).first()
    return {"email_opt_in": bool(row and row.email_opt_in)}


@router.put("/settings")
def update_settings(payload: ReminderUpdate, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    row = db.query(ReminderSetting).filter(ReminderSetting.user_id == user.id).first()
    if row is None:
        row = ReminderSetting(user_id=user.id, email_opt_in=payload.email_opt_in)
        db.add(row)
    else:
        row.email_opt_in = payload.email_opt_in
    db.commit()
    return {"email_opt_in": row.email_opt_in}
