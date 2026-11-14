"""The profile: summary, history, achievements, target role, settings, data export, role recommendations."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import User
from app.routers.auth import get_current_user
from app.services.mock_content import ROLE_SKILLS
from app.services.profile import build_profile, export_profile, recommended_role
from app.services.roles import recommend_roles
from app.services.scoring_engine import build_report

router = APIRouter(prefix="/profile", tags=["profile"])


class TargetRole(BaseModel):
    role: str | None = None  # None clears the choice and the recommended role is used


class Settings(BaseModel):
    assistant_context: bool


@router.get("")
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_profile(db, user)


@router.put("/target-role")
def set_target_role(payload: TargetRole, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.role is not None and payload.role not in ROLE_SKILLS:
        raise HTTPException(status_code=400, detail="Unknown role")
    user.target_role = payload.role
    db.commit()
    return {"target_role": user.target_role, "effective_role": payload.role or recommended_role(db, user)}


@router.put("/settings")
def update_settings(payload: Settings, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.assistant_context = payload.assistant_context
    db.commit()
    return {"assistant_context": user.assistant_context}


@router.get("/recommendations")
def recommendations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return recommend_roles(build_report(db, user.id).get("all_scores", []))


@router.get("/export")
def export(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return JSONResponse(export_profile(db, user), headers={
        "Content-Disposition": f'attachment; filename="skilldna-export-{user.id}.json"'})
