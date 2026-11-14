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
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    email_canonical = Column(String, index=True, nullable=True)  # Gmail dots removed; one per mailbox
    target_role = Column(String, nullable=True)  # chosen (or recommended) role for the plan
    assistant_context = Column(Boolean, default=True, nullable=False)  # let the assistant use this user's progress
    hashed_password = Column(String, nullable=True)  # nullable for pre-auth rows created before this column existed
    created_at = Column(DateTime, default=utc_now)

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
    detected_name = Column(String, nullable=True)  # name read from this document
    content_hash = Column(String, nullable=True, index=True)  # SHA-256 of the uploaded file
    created_at = Column(DateTime, default=utc_now)

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
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="scores")


class MockSession(Base):
    """One proctored mock test or mock interview.

    `questions` holds the full bank entries INCLUDING answer keys. They never
    leave the server until the session is finished (see routers/mock.py).
    """
    __tablename__ = "mock_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    kind = Column(String, nullable=False)  # test | interview
    role = Column(String, nullable=False)
    status = Column(String, default="active")  # active | submitted | terminated
    questions = Column(JSON, default=list)
    answers = Column(JSON, default=dict)  # question_id -> answer text / option index
    violations = Column(JSON, default=list)  # [{"type": ..., "at": iso8601}]
    time_limit_seconds = Column(Integer, nullable=False)
    started_at = Column(DateTime, nullable=False)  # naive UTC
    deadline_at = Column(DateTime, nullable=False)  # naive UTC, enforced server-side
    ended_at = Column(DateTime, nullable=True)
    result = Column(JSON, nullable=True)
    integrity_points = Column(Float, default=0.0, nullable=False)
    integrity_flags = Column(JSON, default=list)
    end_reason = Column(String, nullable=True)  # violations | integrity | time | submitted


class PlanTask(Base):
    """A roadmap task a user has ticked off. Only completion is stored; the task
    text itself comes from the playbook, so it can be improved without a migration."""
    __tablename__ = "plan_tasks"
    __table_args__ = (UniqueConstraint("user_id", "task_key", name="uq_plan_task_user_key"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_key = Column(String, nullable=False)
    done = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class DailyAttempt(Base):
    """One answer per user per day (UTC date). The unique constraint enforces it."""
    __tablename__ = "daily_attempts"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_daily_user_day"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    day = Column(String, nullable=False)  # YYYY-MM-DD, UTC
    challenge_id = Column(String, nullable=False)
    skill = Column(String, nullable=False)
    answer_index = Column(Integer, nullable=False)
    correct = Column(Boolean, nullable=False)
    points = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utc_now)


class PlanBaseline(Base):
    """The score a user had for a skill when their plan first listed it. Compared with
    the current score to show progress. New table, so existing databases get it on startup."""
    __tablename__ = "plan_baselines"
    __table_args__ = (UniqueConstraint("user_id", "skill_key", name="uq_baseline_user_skill"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    skill_key = Column(String, nullable=False)  # lowercase skill name
    baseline_score = Column(Float, nullable=False, default=0.0)
    captured_at = Column(DateTime, default=utc_now)


class ReminderSetting(Base):
    """Explicit consent to receive a daily-challenge reminder email. Off by default."""
    __tablename__ = "reminder_settings"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    email_opt_in = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class PlanSnapshot(Base):
    """One row per user, role and day: the plan's headline numbers, kept for history."""
    __tablename__ = "plan_snapshots"
    __table_args__ = (UniqueConstraint("user_id", "role", "day", name="uq_plan_snapshot_user_role_day"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)
    day = Column(String, nullable=False)  # YYYY-MM-DD, UTC
    overall_score = Column(Float, default=0.0, nullable=False)
    progress_percent = Column(Float, default=0.0, nullable=False)
    gap_count = Column(Integer, default=0, nullable=False)
    tasks_done = Column(Integer, default=0, nullable=False)
    tasks_total = Column(Integer, default=0, nullable=False)


class PhaseAttempt(Base):
    """One phase test attempt. A phase opens for the next phase only after a passing attempt."""
    __tablename__ = "phase_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, nullable=False)
    phase_index = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    passed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=utc_now)


class InterviewSession(Base):
    """An AI interview: the conversation so far is kept in `state` (JSON)."""
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, nullable=False)
    status = Column(String, default="active", nullable=False)  # active | finished
    state = Column(JSON, default=dict)
    overall = Column(Float, nullable=True)
    started_at = Column(DateTime, default=utc_now)
    finished_at = Column(DateTime, nullable=True)
    integrity_points = Column(Float, default=0.0, nullable=False)
    integrity_flags = Column(JSON, default=list)
    end_reason = Column(String, nullable=True)


class AnswerFingerprint(Base):
    """A hash of each substantial interview answer, so a word-for-word copy from someone else is noticed."""
    __tablename__ = "answer_fingerprints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    fingerprint = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False)  # interview
    created_at = Column(DateTime, default=utc_now)
