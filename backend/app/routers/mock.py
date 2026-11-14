"""Mock tests and mock interviews.

Rules the server enforces (the browser cannot change them):
  - One active session per user at a time.
  - The deadline is fixed when the session starts. Answers after it are rejected
    and the session is submitted with whatever was answered.
  - Each reported violation is recorded. On the MAX_VIOLATIONS-th violation the
    session is terminated and scored immediately.
  - Answer keys and expected keywords never leave the server until the session ends.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import MockSession, User
from app.routers.auth import get_current_user
from app.services import integrity
from app.services import mock_engine as eng
from app.services.mock_content import ROLE_SKILLS, INTERVIEW_BANK

router = APIRouter(prefix="/mock", tags=["mock"])

MAX_OPEN_ANSWER_CHARS = 5000


class StartRequest(BaseModel):
    kind: str  # "test" | "interview"
    role: str


class EventRequest(BaseModel):
    type: str


class AnswerRequest(BaseModel):
    question_id: str
    answer: str | int | None = None


def _now() -> datetime:
    """Naive UTC, matching how the columns are stored."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _iso(dt: datetime) -> str:
    return dt.replace(tzinfo=timezone.utc).isoformat()


def _owned_session(db: Session, user: User, session_id: int) -> MockSession:
    session = (
        db.query(MockSession)
        .filter(MockSession.id == session_id, MockSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def _finish(db: Session, session: MockSession, status: str, reason: str | None = None) -> None:
    session.status = status
    session.ended_at = _now()
    session.end_reason = reason or ("submitted" if status == "submitted" else session.end_reason)
    result = eng.score_session(session.kind, session.questions, session.answers)
    result["violation_count"] = len(session.violations)
    result["terminated"] = status == "terminated"
    result["end_reason"] = session.end_reason
    result["integrity_points"] = float(session.integrity_points or 0)
    result["integrity_flags"] = session.integrity_flags or []
    session.result = result
    db.commit()


def _enforce_deadline(db: Session, session: MockSession) -> None:
    if session.status == "active" and _now() > session.deadline_at:
        _finish(db, session, "submitted")


def _state(session: MockSession) -> dict:
    remaining = 0
    if session.status == "active":
        remaining = max(0, int((session.deadline_at - _now()).total_seconds()))
    body = {
        "id": session.id,
        "kind": session.kind,
        "role": session.role,
        "status": session.status,
        "time_limit_seconds": session.time_limit_seconds,
        "remaining_seconds": remaining,
        "deadline_at": _iso(session.deadline_at),
        "max_violations": eng.MAX_VIOLATIONS,
        "violations": [
            {"type": v["type"], "label": eng.VIOLATION_TYPES.get(v["type"], v["type"]), "at": v["at"]}
            for v in session.violations
        ],
        "questions": [eng.public_question(q) for q in session.questions],
        "answered_ids": list(session.answers.keys()),
        "end_reason": session.end_reason,
        "integrity": {
            "points": float(session.integrity_points or 0),
            "auto_submit_at": integrity.AUTO_SUBMIT_AT,
            "is_valid": integrity.is_valid(float(session.integrity_points or 0)),
            "flags": [{"type": f.get("type"), "label": f.get("label"), "at": f.get("at")} for f in (session.integrity_flags or [])],
        },
    }
    if session.status != "active":
        body["result"] = session.result
    return body


@router.get("/roles")
def list_roles():
    return {
        "roles": list(ROLE_SKILLS.keys()),
        "kinds": ["test", "interview"],
        "max_violations": eng.MAX_VIOLATIONS,
        "violation_types": eng.VIOLATION_TYPES,
        "interview_roles": list(INTERVIEW_BANK.keys()),
    }


@router.post("/sessions")
def start_session(
    payload: StartRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.kind not in ("test", "interview"):
        raise HTTPException(status_code=400, detail="kind must be 'test' or 'interview'")
    if payload.role not in ROLE_SKILLS:
        raise HTTPException(status_code=400, detail="Unknown role")

    active = (
        db.query(MockSession)
        .filter(MockSession.user_id == user.id, MockSession.status == "active")
        .first()
    )
    if active:
        if _now() > active.deadline_at:
            _finish(db, active, "submitted")
        else:
            raise HTTPException(
                status_code=409,
                detail=f"You already have an active session (#{active.id}). Finish it first.",
            )

    built = eng.build_test(payload.role) if payload.kind == "test" else eng.build_interview(payload.role)
    now = _now()
    session = MockSession(
        user_id=user.id,
        kind=payload.kind,
        role=payload.role,
        status="active",
        questions=built["questions"],
        answers={},
        violations=[],
        time_limit_seconds=built["time_limit_seconds"],
        started_at=now,
        deadline_at=now + timedelta(seconds=built["time_limit_seconds"]),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _state(session)


@router.get("/sessions")
def list_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(MockSession)
        .filter(MockSession.user_id == user.id)
        .order_by(MockSession.started_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": r.id,
            "kind": r.kind,
            "role": r.role,
            "status": r.status,
            "started_at": _iso(r.started_at),
            "score": (r.result or {}).get("score"),
            "violation_count": len(r.violations or []),
        }
        for r in rows
    ]


@router.get("/sessions/{session_id}")
def get_session(session_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = _owned_session(db, user, session_id)
    _enforce_deadline(db, session)
    return _state(session)


@router.post("/sessions/{session_id}/events")
def report_event(
    session_id: int,
    payload: EventRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.type not in eng.VIOLATION_TYPES and payload.type not in eng.SIGNAL_TYPES:
        raise HTTPException(status_code=400, detail="Unknown event type")
    session = _owned_session(db, user, session_id)
    _enforce_deadline(db, session)
    if session.status != "active":
        return _state(session)

    # Every signal adds integrity points. Reaching the threshold ends the test automatically.
    flags, points = integrity.add_flag(list(session.integrity_flags or []),
                                       float(session.integrity_points or 0), payload.type)
    session.integrity_flags = flags
    session.integrity_points = points
    terminate = False
    if payload.type in eng.VIOLATION_TYPES:
        session.violations, terminate = eng.apply_violation(
            list(session.violations or []), payload.type, _iso(_now())
        )
    db.commit()
    if integrity.should_auto_submit(points):
        _finish(db, session, "terminated", reason="integrity")
    elif terminate:
        _finish(db, session, "terminated", reason="violations")
    return _state(session)


@router.post("/sessions/{session_id}/answers")
def save_answer(
    session_id: int,
    payload: AnswerRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _owned_session(db, user, session_id)
    _enforce_deadline(db, session)
    if session.status != "active":
        raise HTTPException(status_code=409, detail="This session is no longer active")

    question = next((q for q in session.questions if q["id"] == payload.question_id), None)
    if question is None:
        raise HTTPException(status_code=400, detail="Unknown question")

    if question["kind"] == "mcq":
        if payload.answer is None:
            raise HTTPException(status_code=400, detail="Choose an option")
        try:
            value = int(payload.answer)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Option must be a number")
        if not 0 <= value < len(question["options"]):
            raise HTTPException(status_code=400, detail="Option out of range")
    else:
        value = str(payload.answer or "").strip()[:MAX_OPEN_ANSWER_CHARS]

    session.answers = {**(session.answers or {}), payload.question_id: value}
    db.commit()
    return _state(session)


@router.post("/sessions/{session_id}/submit")
def submit_session(session_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = _owned_session(db, user, session_id)
    if session.status == "active":
        _finish(db, session, "submitted")
    return _state(session)
