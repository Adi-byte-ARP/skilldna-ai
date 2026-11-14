"""Help assistant endpoint. Public on purpose: it can be used before sign-in. It never reads user data."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import User
from app.routers.auth import get_current_user, get_optional_user
from app.services.assistant import answer
from app.services.assistant_context import action_reply, assistant_context, week_schedule

router = APIRouter(prefix="/assistant", tags=["assistant"])


class Turn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = ""
    history: list[Turn] = []


@router.post("/chat")
def chat(payload: ChatRequest, user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    """Anyone can ask. A signed-in user who allows it gets answers about their own progress."""
    context = assistant_context(db, user) if user else None
    result = answer(payload.message, [t.model_dump() for t in payload.history], context=context)
    result["personalised"] = context is not None
    return result


class ActionRequest(BaseModel):
    action: str  # next | week | progress | roles


@router.post("/action")
def action(payload: ActionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """One-tap actions: the next step, this week's schedule, progress, and role fit."""
    context = assistant_context(db, user)
    if context is None:
        raise HTTPException(status_code=403, detail="Turn on 'let the assistant use my progress' in your profile to use this.")
    if payload.action not in ("next", "week", "progress", "roles"):
        raise HTTPException(status_code=400, detail="Unknown action")
    return action_reply(payload.action, context)
