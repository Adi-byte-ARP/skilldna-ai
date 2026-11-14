"""Picks each user's challenge for a day, grades answers, and tracks streaks.

The pick is deterministic: the same user gets the same challenge on the same
day, so refreshing or re-opening the page never changes it. Most days cover
the user's skill gaps. Every third day explores a skill outside the gaps.
"""
from datetime import date, timedelta

from app.services.daily_bank import DAILY_BANK

POINTS_PER_CORRECT = 10
EXPLORE_EVERY = 3


def challenge_pool_skills() -> list[str]:
    return sorted({c["skill"] for c in DAILY_BANK})


def pick_challenge(user_id: int, day: date, gap_skills: list[str], role_skills: list[str]) -> dict:
    available = set(challenge_pool_skills())
    gaps = [s.lower() for s in gap_skills if s.lower() in available]
    role = [s.lower() for s in role_skills if s.lower() in available]
    focus = gaps or role or sorted(available)

    explore = day.toordinal() % EXPLORE_EVERY == 0
    if explore:
        outside = sorted(available - set(focus))
        skills = outside or focus
    else:
        skills = focus

    pool = sorted((c for c in DAILY_BANK if c["skill"] in skills), key=lambda c: c["id"])
    chosen = pool[(day.toordinal() + user_id) % len(pool)]
    return {**chosen, "explore": explore and bool(set(skills) - set(focus))}


def normalise_text(text: str) -> str:
    return " ".join((text or "").lower().split())


def text_hits(challenge: dict, answer_text: str) -> list[str]:
    """Accepted keywords found in the answer (case-insensitive, whitespace-normalised)."""
    text = normalise_text(answer_text)
    return [k for k in challenge["keywords"] if k.lower() in text]


def grade(challenge: dict, answer_index: int | None = None, answer_text: str | None = None) -> dict:
    """Grade one answer. Multiple choice compares the option index; free text
    counts accepted keywords and needs `min_hits` of them."""
    if challenge.get("kind") == "text":
        hits = text_hits(challenge, answer_text or "")
        correct = len(hits) >= challenge["min_hits"]
        return {
            "correct": correct,
            "your_index": None,
            "correct_index": None,
            "accepted": challenge["keywords"],
            "hits": hits,
            "needed": challenge["min_hits"],
            "explanation": challenge["explanation"],
            "points": POINTS_PER_CORRECT if correct else 0,
        }
    correct = answer_index == challenge["answer"]
    return {
        "correct": correct,
        "your_index": answer_index,
        "correct_index": challenge["answer"],
        "explanation": challenge["explanation"],
        "points": POINTS_PER_CORRECT if correct else 0,
    }


def current_streak(answered_days: set[date], today: date) -> int:
    """Consecutive days with an answer, counting back from today. If today is
    not answered yet, the streak still counts from yesterday, so it is not lost
    before the user has had a chance to answer."""
    cursor = today if today in answered_days else today - timedelta(days=1)
    streak = 0
    while cursor in answered_days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak
