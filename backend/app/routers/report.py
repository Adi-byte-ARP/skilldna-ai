from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import User
from app.models.schemas import SkillDNAReport
from app.services.scoring_engine import build_report

router = APIRouter(prefix="/report", tags=["report"])


@router.get("/{user_id}", response_model=SkillDNAReport)
def get_skilldna_report(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return build_report(db, user_id)
