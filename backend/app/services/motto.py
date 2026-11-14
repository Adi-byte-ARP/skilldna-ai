"""One honest thought a day, shown on the dashboard, the profile and in the assistant."""
from datetime import date

MOTTOS = [
    "Be honest with yourself: a skill counts when you can show it.",
    "Claims are cheap. Evidence is what gets you hired.",
    "Practise what you cannot do yet, not only what you already do well.",
    "If you cannot explain it without notes, you do not know it yet.",
    "Small honest steps beat a perfect plan you never start.",
    "Ask what you would do if the tool disappeared. That is the skill.",
    "Your score should surprise you a little. If it never does, you are not looking closely.",
]


def daily_motto(day: date | None = None) -> str:
    day = day or date.today()
    return MOTTOS[day.toordinal() % len(MOTTOS)]
