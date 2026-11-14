"""Skill-gap plan and learning roadmaps for the logged-in user.

Two modes, kept apart so their progress and tests never mix:
  mode=gap      (default) the plan for the target role, built from the user's evidence:
                only the skills they do not yet show, ranked by priority.
  mode=scratch  a full roadmap for a role from zero, ignoring existing evidence.

GET   /plan?role=&mode=                     the plan, with phase statuses and the ranked improve list
POST  /plan/tasks/{key}?role=&mode=         tick a task. Refused (423) while its phase is locked.
GET   /plan/phases/{index}/test?role=&mode= the questions, once every task in the phase is ticked
POST  /plan/phases/{index}/test?role=&mode= submit answers. 60% or more unlocks the next phase.
GET   /plan/history                         one snapshot per role per day (gap mode only)
"""
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import DailyAttempt, PhaseAttempt, PlanBaseline, PlanSnapshot, PlanTask, User
from app.routers.auth import get_current_user
from app.services.learning import PHASE_PASS_SCORE, grade_phase_test, phase_test_questions
from app.services.mock_content import ROLE_SKILLS
from app.services.phase_gate import apply_phase_gates, phase_is_open_for_task
from app.services.roadmap import _gaps_for_role, build_plan
from app.services.scoring_engine import build_report

router = APIRouter(prefix="/plan", tags=["plan"])

TASK_KEY_RE = re.compile(r"^[a-z0-9-]+:task\d+$")
MODES = ("gap", "scratch")


class TaskToggle(BaseModel):
    done: bool


class PhaseTestSubmit(BaseModel):
    answers: dict[str, int]


def _check_role(role: str) -> None:
    if role not in ROLE_SKILLS:
        raise HTTPException(status_code=400, detail="Unknown role")


def _check_mode(mode: str) -> str:
    if mode not in MODES:
        raise HTTPException(status_code=400, detail="mode must be 'gap' or 'scratch'")
    return mode


def _role_key(role: str, mode: str) -> str:
    """Attempts and phase results are stored per role and mode, so a scratch roadmap never unlocks a gap plan."""
    return role if mode == "gap" else f"scratch:{role}"


def _full_plan(db: Session, user: User, role: str, record_baselines: bool = True, mode: str = "gap") -> dict:
    report = build_report(db, user.id)
    scores = report.get("all_scores", [])
    # A scratch roadmap ignores existing evidence: every skill for the role is a step to learn.
    all_scores = scores if mode == "gap" else []
    done_keys = {row.task_key for row in
                 db.query(PlanTask).filter(PlanTask.user_id == user.id, PlanTask.done.is_(True)).all()}

    baselines: dict[str, float] = {}
    if mode == "gap":
        current = {}
        for item in scores:
            name = item.skill_name if hasattr(item, "skill_name") else item["skill_name"]
            score = item.score if hasattr(item, "score") else item["score"]
            current[name.lower()] = float(score)
        baselines = {row.skill_key: row.baseline_score for row in
                     db.query(PlanBaseline).filter(PlanBaseline.user_id == user.id).all()}
        if record_baselines:
            for g in _gaps_for_role(role, scores):
                key = g["skill"].lower()
                if key not in baselines:
                    baselines[key] = current.get(key, 0.0)
                    db.add(PlanBaseline(user_id=user.id, skill_key=key, baseline_score=baselines[key]))
            db.commit()

    since = (datetime.now(timezone.utc).date() - timedelta(days=30)).isoformat()
    daily_stats: dict[str, dict] = {}
    for row in db.query(DailyAttempt).filter(DailyAttempt.user_id == user.id, DailyAttempt.day >= since).all():
        stats = daily_stats.setdefault(row.skill.lower(), {"attempts": 0, "correct": 0})
        stats["attempts"] += 1
        stats["correct"] += 1 if row.correct else 0

    plan = build_plan(
        role=role,
        all_scores=all_scores,
        overall_score=report.get("overall_score", 0.0),
        tier=report.get("tier", "No data yet"),
        done_keys=done_keys,
        baselines=baselines,
        daily_stats=daily_stats,
    )
    plan["mode"] = mode

    key = _role_key(role, mode)
    passed: dict[int, float] = {}
    counts: dict[int, int] = {}
    for attempt in db.query(PhaseAttempt).filter(PhaseAttempt.user_id == user.id, PhaseAttempt.role == key).all():
        counts[attempt.phase_index] = counts.get(attempt.phase_index, 0) + 1
        if attempt.passed:
            passed[attempt.phase_index] = max(passed.get(attempt.phase_index, 0.0), attempt.score)
    return apply_phase_gates(plan, passed, counts)


def _phase_skills(plan: dict, index: int) -> list[str]:
    keys = set(plan["phases"][index]["items"])
    return [it["skill"] for it in plan["items"] if it["key"] in keys]


def _check_phase_open(plan: dict, index: int) -> dict:
    if index < 0 or index >= len(plan["phases"]) or not plan["phases"][index]["items"]:
        raise HTTPException(status_code=404, detail="No such learning phase")
    phase = plan["phases"][index]
    if phase["status"] == "locked":
        raise HTTPException(status_code=423, detail=phase["locked_reason"])
    if not phase["test"]["available"] and not phase["test"]["passed"]:
        raise HTTPException(status_code=409, detail="Tick every task in this phase before taking its test.")
    return phase


@router.get("")
def get_plan(role: str = "Full-Stack Developer", mode: str = "gap", user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    _check_role(role)
    _check_mode(mode)
    plan = _full_plan(db, user, role, mode=mode)
    if mode == "gap":
        _record_snapshot(db, user.id, role, plan)
    return plan


def _record_snapshot(db: Session, user_id: int, role: str, plan: dict) -> None:
    """Keep one snapshot per role per day (updated in place as the day goes on)."""
    today = datetime.now(timezone.utc).date().isoformat()
    row = (db.query(PlanSnapshot)
           .filter(PlanSnapshot.user_id == user_id, PlanSnapshot.role == role, PlanSnapshot.day == today)
           .first())
    if row is None:
        row = PlanSnapshot(user_id=user_id, role=role, day=today)
        db.add(row)
    row.overall_score = float(plan["overall_score"])
    row.progress_percent = float(plan["progress"]["percent"])
    row.gap_count = int(plan["gap_count"])
    row.tasks_done = int(plan["progress"]["done"])
    row.tasks_total = int(plan["progress"]["total"])
    db.commit()


@router.get("/history")
def plan_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The last 60 snapshots, newest first. One per role per day."""
    rows = (db.query(PlanSnapshot)
            .filter(PlanSnapshot.user_id == user.id)
            .order_by(PlanSnapshot.day.desc(), PlanSnapshot.role)
            .limit(60).all())
    return [
        {
            "day": r.day,
            "role": r.role,
            "overall_score": round(r.overall_score, 1),
            "progress_percent": round(r.progress_percent, 1),
            "gap_count": r.gap_count,
            "tasks_done": r.tasks_done,
            "tasks_total": r.tasks_total,
        }
        for r in rows
    ]


@router.post("/tasks/{task_key}")
def toggle_task(task_key: str, payload: TaskToggle, role: str = "Full-Stack Developer", mode: str = "gap",
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not TASK_KEY_RE.match(task_key):
        raise HTTPException(status_code=400, detail="Invalid task key")
    _check_role(role)
    _check_mode(mode)
    plan = _full_plan(db, user, role, record_baselines=False, mode=mode)
    item_key = task_key.split(":")[0]
    open_, reason = phase_is_open_for_task(plan, item_key)
    if not open_:
        status = 423 if any(it["key"] == item_key for it in plan["items"]) else 400
        raise HTTPException(status_code=status, detail=reason)

    row = db.query(PlanTask).filter(PlanTask.user_id == user.id, PlanTask.task_key == task_key).first()
    if row is None:
        row = PlanTask(user_id=user.id, task_key=task_key, done=payload.done)
        db.add(row)
    else:
        row.done = payload.done
    db.commit()
    return {"task_key": task_key, "done": row.done, "mode": mode}


@router.get("/phases/{index}/test")
def get_phase_test(index: int, role: str = "Full-Stack Developer", mode: str = "gap",
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_role(role)
    _check_mode(mode)
    plan = _full_plan(db, user, role, record_baselines=False, mode=mode)
    _check_phase_open(plan, index)
    questions = phase_test_questions(_phase_skills(plan, index), seed=user.id * 31 + index)
    return {
        "phase_index": index,
        "pass_score": PHASE_PASS_SCORE,
        "passed_already": plan["phases"][index]["test"]["passed"],
        "questions": [{"id": q["id"], "question": q["question"], "options": q["options"]} for q in questions],
    }


@router.post("/phases/{index}/test")
def submit_phase_test(index: int, payload: PhaseTestSubmit, role: str = "Full-Stack Developer", mode: str = "gap",
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_role(role)
    _check_mode(mode)
    plan = _full_plan(db, user, role, record_baselines=False, mode=mode)
    if plan["phases"][index]["test"]["passed"]:
        raise HTTPException(status_code=409, detail="You already passed this phase test.")
    _check_phase_open(plan, index)
    questions = phase_test_questions(_phase_skills(plan, index), seed=user.id * 31 + index)
    result = grade_phase_test(questions, payload.answers)
    db.add(PhaseAttempt(user_id=user.id, role=_role_key(role, mode), phase_index=index,
                        score=result["score"], passed=result["passed"]))
    db.commit()

    updated = _full_plan(db, user, role, record_baselines=False, mode=mode)
    return {
        **result,
        "phase_index": index,
        "phase_status": updated["phases"][index]["status"],
        "next_phase": updated["next_phase"],
        "unlocked_next": bool(result["passed"] and index + 1 < len(updated["phases"])
                              and updated["phases"][index + 1].get("unlocked")),
        "plan": updated,
    }
