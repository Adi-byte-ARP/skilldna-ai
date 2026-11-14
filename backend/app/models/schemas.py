from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    name: str
    email: EmailStr


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class RegisterRequest(BaseModel):
    # Validated in the route, so the message the user sees is ours and specific.
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: UserOut


class ExtractedSkillOut(BaseModel):
    skill_name: str
    category: Optional[str] = None
    confidence: float
    evidence: Optional[str] = None

    class Config:
        from_attributes = True


class SubmissionOut(BaseModel):
    id: int
    source_type: str
    original_filename: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    detected_name: Optional[str] = None
    extracted_skills: list[ExtractedSkillOut] = []

    class Config:
        from_attributes = True


class SkillScoreOut(BaseModel):
    skill_name: str
    category: Optional[str] = None
    score: float
    sources: Optional[list[str]] = None

    class Config:
        from_attributes = True


class SkillDNAReport(BaseModel):
    user_id: int
    overall_score: float
    tier: str
    source_scores: dict[str, float] = {}
    strengths: list[SkillScoreOut]
    gaps: list[SkillScoreOut]
    all_scores: list[SkillScoreOut]
    recommendations: list[str]
