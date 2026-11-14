"""AI interview endpoints, with integrity checks.

POST /interview/sessions                 start an interview for a role; returns the opening question
POST /interview/sessions/{id}/answer     answer the current question (optionally with seconds_spent);
                                         returns feedback, the next question, or the final report
POST /interview/sessions/{id}/event      a browser signal (tab switch, paste attempt, ...); may auto-submit
GET  /interview/sessions/{id}            the conversation so far, with integrity status
GET  /interview/sessions                 past interviews, newest first
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import AnswerFingerprint, InterviewSession, User
from app.routers.auth import get_current_user
from app.services import integrity
from app.services.interviewer import answer_turn, first_question, report, start_state

router = APIRouter(prefix="/interview", tags=["interview"])
MAX_ANSWER_CHARS = 2000
BROWSER_SIGNALS = {"tab_hidden", "window_blur", "paste", "copy", "cut", "context_menu", "shortcut_blocked"}


class StartRequest(BaseModel):
    role: str


class AnswerRequest(BaseModel):
    answer: str
    seconds_spent: float | None = None  # time from the question appearing to the answer being sent


class EventRequest(BaseModel):
    type: str


def _owned(db: Session, user: User, session_id: int) -> InterviewSession:
    row = db.query(InterviewSession).filter(InterviewSession.id == session_id,
                                            InterviewSession.user_id == user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Interview not found")
    return row


def _integrity_view(row: InterviewSession) -> dict:
    pts = float(row.integrity_points or 0)
    return {
        "points": pts,
        "auto_submit_at": integrity.AUTO_SUBMIT_AT,
        "is_valid": integrity.is_valid(pts),
        "flags": [{"type": f.get("type"), "label": f.get("label"), "detail": f.get("detail"), "at": f.get("at")}
                  for f in (row.integrity_flags or [])],
    }


def _view(row: InterviewSession) -> dict:
    state = row.state or {}
    return {
        "id": row.id,
        "role": row.role,
        "status": row.status,
        "turns": state.get("turns", []),
        "target_turns": state.get("target_turns"),
        "current_question": state.get("pending_question"),
        "overall": row.overall,
        "end_reason": row.end_reason,
        "integrity": _integrity_view(row),
    }


def _finish(db: Session, row: InterviewSession, reason: str) -> dict:
    state = dict(row.state or {})
    final = report(state)
    row.state = state
    row.status = "finished"
    row.end_reason = reason
    row.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
    row.overall = final["overall"]
    return final


@router.post("/sessions")
def start(payload: StartRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        state = start_state(payload.role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    state["pending_question"] = first_question(state)
    row = InterviewSession(user_id=user.id, role=payload.role, status="active", state=state,
                           integrity_points=0.0, integrity_flags=[])
    db.add(row)
    db.commit()
    db.refresh(row)
    return _view(row)


@router.post("/sessions/{session_id}/answer")
def answer(session_id: int, payload: AnswerRequest, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    row = _owned(db, user, session_id)
    if row.status != "active":
        raise HTTPException(status_code=409, detail="This interview has already finished")
    text = (payload.answer or "").strip()[:MAX_ANSWER_CHARS]
    if not text:
        raise HTTPException(status_code=400, detail="Type or say an answer first")

    # Integrity: timing signals from this answer, and a match against other people's answers.
    flags = list(row.integrity_flags or [])
    points = float(row.integrity_points or 0)
    for kind, detail in integrity.analyse_answer(text, payload.seconds_spent):
        flags, points = integrity.add_flag(flags, points, kind, detail)
    fp = integrity.answer_fingerprint(text)
    if fp:
        copied = (db.query(AnswerFingerprint)
                  .filter(AnswerFingerprint.fingerprint == fp, AnswerFingerprint.user_id != user.id)
                  .first())
        if copied:
            flags, points = integrity.add_flag(flags, points, "answer_duplicate",
                                               "This answer matches one given in another interview.")
        db.add(AnswerFingerprint(user_id=user.id, fingerprint=fp, source="interview"))

    state = dict(row.state or {})
    result = answer_turn(state, text)
    row.state = state
    row.integrity_flags = flags
    row.integrity_points = points

    auto = integrity.should_auto_submit(points)
    if auto:
        final = _finish(db, row, "integrity")
        db.commit()
        db.refresh(row)
        return {**_view(row), "feedback": result["feedback"], "done": True, "auto_submitted": True,
                "report": final}
    if result["done"]:
        final = _finish(db, row, "completed")
        db.commit()
        db.refresh(row)
        return {**_view(row), "feedback": result["feedback"], "done": True, "auto_submitted": False,
                "report": final}
    db.commit()
    db.refresh(row)
    return {**_view(row), "feedback": result["feedback"], "done": False, "auto_submitted": False, "report": None}


@router.post("/sessions/{session_id}/event")
def event(session_id: int, payload: EventRequest, user: User = Depends(get_current_user),
          db: Session = Depends(get_db)):
    if payload.type not in BROWSER_SIGNALS:
        raise HTTPException(status_code=400, detail="Unknown event type")
    row = _owned(db, user, session_id)
    if row.status != "active":
        return {**_view(row), "auto_submitted": False}
    flags, points = integrity.add_flag(list(row.integrity_flags or []), float(row.integrity_points or 0), payload.type)
    row.integrity_flags = flags
    row.integrity_points = points
    auto = integrity.should_auto_submit(points)
    final = _finish(db, row, "integrity") if auto else None
    db.commit()
    db.refresh(row)
    # When the signal ends the interview, the response carries the report, so the page can show it.
    return {**_view(row), "auto_submitted": auto, "report": final}


@router.get("/sessions/{session_id}")
def get_session(session_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _view(_owned(db, user, session_id))


@router.get("/sessions")
def list_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(InterviewSession).filter(InterviewSession.user_id == user.id)
            .order_by(InterviewSession.started_at.desc()).limit(30).all())
    return [{"id": r.id, "role": r.role, "status": r.status, "overall": r.overall,
             "end_reason": r.end_reason,
             "started_at": r.started_at.isoformat() if r.started_at else None,
             "turns": len((r.state or {}).get("turns", []))} for r in rows]
