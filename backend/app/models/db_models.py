"""
Core data model.

Design: every input source (resume, GitHub, LinkedIn screenshot, certificate)
produces a set of ExtractedSkill rows tagged with its source and a confidence
score. The scoring engine reads across all sources for a user to build one
composite SkillDNA score. This is what lets us "consolidate resume,
coding-profile, LinkedIn, and certificate data into one composite
assessment" per the synopsis, without hardcoding per-source logic into
the scorer.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # nullable for pre-auth rows created before this column existed
    created_at = Column(DateTime, default=datetime.utcnow)

    submissions = relationship("Submission", back_populates="user", cascade="all, delete-orphan")
    scores = relationship("SkillScore", back_populates="user", cascade="all, delete-orphan")


class Submission(Base):
    """One uploaded artifact: a resume PDF, a LinkedIn screenshot, a
    certificate image, or a GitHub username lookup."""
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source_type = Column(String, nullable=False)  # resume | github | linkedin | certificate
    original_filename = Column(String, nullable=True)
    raw_text = Column(Text, nullable=True)  # extracted text (OCR/pdf/API dump)
    status = Column(String, default="pending")  # pending | processed | failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="submissions")
    extracted_skills = relationship("ExtractedSkill", back_populates="submission", cascade="all, delete-orphan")


class ExtractedSkill(Base):
    """A single skill found in a submission, with a confidence and
    optional evidence snippet (e.g. the sentence it was found in, or
    'contributed 40 commits in last year' for GitHub)."""
    __tablename__ = "extracted_skills"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    skill_name = Column(String, nullable=False, index=True)
    category = Column(String, nullable=True)  # e.g. "Programming Language", "Framework", "Soft Skill"
    confidence = Column(Float, default=0.5)  # 0-1
    evidence = Column(Text, nullable=True)

    submission = relationship("Submission", back_populates="extracted_skills")


class SkillScore(Base):
    """Composite per-skill score for a user, aggregated across all their
    submissions. This is what the frontend renders as the SkillDNA
    profile / radar chart."""
    __tablename__ = "skill_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    skill_name = Column(String, nullable=False, index=True)
    category = Column(String, nullable=True)
    score = Column(Float, nullable=False)  # 0-100
    sources = Column(JSON, nullable=True)  # list of source_types that contributed
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="scores")
