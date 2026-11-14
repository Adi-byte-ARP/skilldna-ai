"""Integrity checks for mock tests and AI interviews.

Honest scope: a browser cannot prove that someone is cheating. These are signals that
commonly accompany cheating. Each signal adds points; when the total reaches AUTO_SUBMIT_AT
the session is submitted automatically, and the user sees exactly which signals fired.
A person reviews anything that matters, and the signals are described, never called proof.

Signals and what they catch:
  tab_hidden, window_blur      switching to another tab or window (notes, a chatbot, a second device)
  fullscreen_exit              leaving the exam screen
  copy, cut, paste             trying to move text in or out of the test
  context_menu, shortcut_blocked  looking for a way around the rules
  camera_lost                  covering or turning off the camera
  answer_burst                 a long answer arrived far faster than anyone types (pasted or generated)
  answer_duplicate             an answer word-for-word identical to one given by someone else
  answer_instant               a long answer given within seconds of the question appearing
"""
import hashlib
import re
from datetime import datetime, timezone

AUTO_SUBMIT_AT = 5.0  # points: one tab switch with one copy, paste or blur attempt ends the session

WEIGHTS = {
    "tab_hidden": 3.0,
    "window_blur": 2.0,
    "fullscreen_exit": 2.0,
    "copy": 2.0,
    "cut": 2.0,
    "paste": 2.0,
    "context_menu": 1.0,
    "shortcut_blocked": 2.0,
    "camera_lost": 3.0,
    "answer_burst": 5.0,   # a long answer in seconds is pasted or generated: enough on its own
    "answer_duplicate": 5.0,
    "answer_instant": 2.0,
    "speech": 2.0,         # talking during a test; two incidents plus one blur ends it
    "mobile_device": 5.0,  # on its own, enough to end the test
}

LABELS = {
    "tab_hidden": "Switched to another tab",
    "window_blur": "Clicked outside the window",
    "fullscreen_exit": "Left fullscreen",
    "copy": "Tried to copy",
    "cut": "Tried to cut",
    "paste": "Tried to paste",
    "context_menu": "Opened the right-click menu",
    "shortcut_blocked": "Used a blocked shortcut",
    "camera_lost": "Camera went off",
    "answer_burst": "Answer arrived too fast to be typed",
    "answer_duplicate": "Answer matches one given by someone else",
    "answer_instant": "Long answer given within seconds of the question",
    "speech": "Talking or reading aloud during the test",
    "mobile_device": "Phone or tablet used to take the test",
}

MIN_CHARS_FOR_BURST = 80
BURST_CHARS_PER_SECOND = 12.0   # faster than any human typist sustains
INSTANT_SECONDS = 4.0
INSTANT_MIN_CHARS = 40
MIN_CHARS_FOR_DUPLICATE = 60


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_flag(flags: list[dict], points: float, kind: str, detail: str | None = None) -> tuple[list[dict], float]:
    """Record one signal. Returns (new flags, new total)."""
    weight = WEIGHTS.get(kind, 1.0)
    updated = list(flags) + [{"type": kind, "label": LABELS.get(kind, kind), "points": weight,
                              "detail": detail, "at": now_iso()}]
    return updated, round(points + weight, 2)


def total_points(flags: list[dict]) -> float:
    return round(sum(f.get("points", 0) for f in flags), 2)


def should_auto_submit(points: float) -> bool:
    return points >= AUTO_SUBMIT_AT


def is_valid(points: float) -> bool:
    """Return True if the session integrity is still within the allowed threshold."""
    return points < AUTO_SUBMIT_AT


def integrity_snapshot(flags: list[dict], points: float) -> dict:
    """Build the integrity object returned to the frontend."""
    return {
        "points": points,
        "auto_submit_at": AUTO_SUBMIT_AT,
        "flags": flags,
        "is_valid": is_valid(points),
    }


def normalise_answer(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower()).split())


def answer_fingerprint(text: str) -> str | None:
    """A stable hash of the normalised answer, or None if the answer is too short to compare."""
    normalised = normalise_answer(text)
    if len(normalised) < MIN_CHARS_FOR_DUPLICATE:
        return None
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def analyse_answer(text: str, seconds_spent: float | None) -> list[tuple[str, str]]:
    """Signals from one answer alone: (kind, detail) pairs. Duplicates are checked against the database elsewhere."""
    signals = []
    chars = len(text or "")
    if seconds_spent is not None and seconds_spent >= 0:
        if chars >= MIN_CHARS_FOR_BURST and seconds_spent > 0 and chars / max(seconds_spent, 0.5) > BURST_CHARS_PER_SECOND:
            signals.append(("answer_burst", f"{chars} characters in {seconds_spent:.0f} seconds"))
        elif chars >= INSTANT_MIN_CHARS and seconds_spent < INSTANT_SECONDS:
            signals.append(("answer_instant", f"{chars} characters in {seconds_spent:.1f} seconds"))
    return signals
