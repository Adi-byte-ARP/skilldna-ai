from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import User
from app.models.schemas import RegisterRequest, LoginRequest, AuthResponse, UserOut
from app.services.account_rules import (
    canonical_email, normalise_gmail, password_problems, validate_full_name,
)
from app.utils.security import hash_password, verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Dependency that resolves the bearer token to a real User row, or 401s.

    Use this on any route that should trust `user_id` from the token instead
    of an unauthenticated path/query parameter.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return user


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    try:
        name = validate_full_name(payload.name)
        email = normalise_gmail(payload.email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    problems = password_problems(payload.password, email)
    if problems:
        raise HTTPException(
            status_code=400,
            detail="Password needs " + ", ".join(problems) + ".",
        )

    canonical = canonical_email(email)
    existing = db.query(User).filter(User.email_canonical == canonical).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this Gmail address already exists. Try logging in instead.")

    user = User(
        name=name,
        email=email,
        email_canonical=canonical,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.email)
    return {"token": token, "user": user}


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    try:
        email = normalise_gmail(payload.email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    user = db.query(User).filter(User.email_canonical == canonical_email(email)).first()
    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = create_access_token(user.id, user.email)
    return {"token": token, "user": user}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


def authorize_user(user_id: int, current_user: User = Depends(get_current_user)) -> User:
    """Dependency for routes whose path contains a user_id: the caller must be
    logged in AND must be that user. Without this, anyone who knew a numeric id
    could read or write another person's data."""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only access your own data")
    return current_user


def get_optional_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User | None:
    """The signed-in user if the request carries a valid token, otherwise None. Never raises."""
    if not authorization:
        return None
    try:
        return get_current_user(authorization=authorization, db=db)
    except HTTPException:
        return None
