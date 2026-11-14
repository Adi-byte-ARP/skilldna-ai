from app.routers.auth import authorize_user
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import User
from app.models.schemas import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.post("")
def create_user_disabled():
    """Removed: it returned an existing account's name and email to anyone who
    submitted that address. Use POST /auth/register instead."""
    raise HTTPException(status_code=410, detail="Use POST /auth/register instead")


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), _=Depends(authorize_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
