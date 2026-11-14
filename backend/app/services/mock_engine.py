"""Pure logic for mock tests and mock interviews. No HTTP, no DB here.

Scoring is deliberately simple and explainable:
  - Test: share of correct answers, plus a per-skill breakdown.
  - Interview: keyword coverage of the expected points (70%) and answer length
    (30%). This is a rubric check, not a human assessment, and the feedback says so.
"""
from app.services.mock_content import MCQ_BANK, INTERVIEW_BANK, GENERAL_INTERVIEW, ROLE_SKILLS

MAX_VIOLATIONS = 2  # strict: the session ends on the second violation
TEST_SECONDS_PER_QUESTION = 90
INTERVIEW_GRACE_SECONDS = 30  # server deadline allows a little slack past the question timers
MCQ_PER_TEST = 8

VIOLATION_TYPES = {
    "tab_hidden": "Switched to another tab or minimized the window",
    "window_blur": "Clicked outside the exam window",
    "fullscreen_exit": "Left fullscreen mode",
    "copy": "Tried to copy exam content",
    "paste": "Tried to paste into the exam",
    "cut": "Tried to cut exam content",
    "context_menu": "Opened the right-click menu",
    "shortcut_blocked": "Used a blocked keyboard shortcut",
    "camera_lost": "Camera was turned off or disconnected",
}

# Signals that add integrity points without counting as one of the two violations.
# speech: sustained talking during the test (reading the questions aloud, someone helping).
# mobile_device: the test was started or continued on a phone or tablet.
SIGNAL_TYPES = {
    "speech": "Talking or reading aloud during the test",
    "mobile_device": "Phone or tablet used to take the test",
}

LENGTH_TARGET_WORDS = 60  # answers near this length get full length credit


def build_test(role: str) -> dict:
    """Pick MCQs that match the role's skills, falling back to the whole bank."""
    role_skills = {s.lower() for s in ROLE_SKILLS.get(role, [])}
    matched = [q for q in MCQ_BANK if q["skill"] in role_skills]
    pool = matched or MCQ_BANK
    questions = pool[:MCQ_PER_TEST]
    return {
        "questions": [dict(q, kind="mcq") for q in questions],
        "time_limit_seconds": TEST_SECONDS_PER_QUESTION * len(questions),
    }


def build_interview(role: str) -> dict:
    """Three role questions plus two general ones, each with its own answer timer."""
    role_questions = INTERVIEW_BANK.get(role, [])
    questions = [dict(q, kind="open") for q in role_questions + GENERAL_INTERVIEW]
    total = sum(q["seconds"] for q in questions)
    return {
        "questions": questions,
        "time_limit_seconds": total + INTERVIEW_GRACE_SECONDS,
    }


def public_question(question: dict) -> dict:
    """What the client may see: never the answer key or the expected keywords."""
    if question["kind"] == "mcq":
        return {"id": question["id"], "kind": "mcq", "skill": question["skill"],
                "question": question["question"], "options": question["options"]}
    return {"id": question["id"], "kind": "open", "question": question["question"],
            "seconds": question["seconds"]}


def score_mcq_answer(question: dict, answer) -> bool:
    return answer is not None and int(answer) == question["answer"]


def score_open_answer(question: dict, answer: str) -> dict:
    """Keyword coverage plus length. Returns the score and the expected points
    the answer did not mention, so the feedback can name them."""
    text = (answer or "").lower()
    words = len(text.split())
    keywords = question["keywords"]
    matched = [k for k in keywords if k in text]
    missing = [k for k in keywords if k not in text]
    coverage = len(matched) / len(keywords) if keywords else 0.0
    length_factor = min(1.0, words / LENGTH_TARGET_WORDS)
    score = round(100 * (0.7 * coverage + 0.3 * length_factor), 1)
    return {"score": score, "words": words, "missing_points": missing}


def score_session(session_kind: str, questions: list[dict], answers: dict) -> dict:
    """Score a finished (or terminated) session from its stored answers."""
    per_question = []
    if session_kind == "test":
        correct = 0
        by_skill: dict[str, list[bool]] = {}
        for q in questions:
            ok = score_mcq_answer(q, answers.get(q["id"]))
            correct += ok
            by_skill.setdefault(q["skill"], []).append(ok)
            per_question.append({"id": q["id"], "correct": ok})
        total = len(questions) or 1
        return {
            "score": round(100 * correct / total, 1),
            "correct": correct,
            "total": len(questions),
            "by_skill": {s: round(100 * sum(v) / len(v), 1) for s, v in by_skill.items()},
            "per_question": per_question,
            "feedback": _test_feedback(correct, len(questions), by_skill),
        }

    scores = []
    for q in questions:
        answer = answers.get(q["id"], "")
        detail = score_open_answer(q, answer)
        scores.append(detail["score"])
        per_question.append({"id": q["id"], "question": q["question"], **detail})
    overall = round(sum(scores) / len(scores), 1) if scores else 0.0
    return {
        "score": overall,
        "per_question": per_question,
        "feedback": _interview_feedback(per_question),
        "note": "Keyword-coverage rubric. It checks whether expected points were covered, not how well you spoke.",
    }


def _test_feedback(correct: int, total: int, by_skill: dict) -> list[str]:
    tips = [f"You answered {correct} of {total} correctly."]
    weak = [s for s, v in by_skill.items() if sum(v) / len(v) < 0.5]
    if weak:
        tips.append("Review: " + ", ".join(sorted(weak)) + ".")
    return tips


def _interview_feedback(per_question: list[dict]) -> list[str]:
    tips = []
    for item in per_question:
        if item["words"] < 20:
            tips.append(f"'{item['question'][:50]}...' was very short. Aim for 3 to 5 sentences with an example.")
        elif item["missing_points"]:
            tips.append(
                f"'{item['question'][:50]}...' did not mention: {', '.join(item['missing_points'][:3])}."
            )
    return tips or ["Good coverage of the expected points across your answers."]


def apply_violation(violations: list[dict], event_type: str, now_iso: str) -> tuple[list[dict], bool]:
    """Record one violation. Returns (new_list, terminate) where terminate is
    True once the limit is reached."""
    updated = violations + [{"type": event_type, "at": now_iso}]
    return updated, len(updated) >= MAX_VIOLATIONS
