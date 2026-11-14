"""Scorecard dimensions for an AI interview, computed from the candidate's own answers.

Each dimension is 0 to 100 and comes with one plain sentence on what to do next when it is low.
These measure how an answer is built and delivered, plus the keyword match from scoring. They do
not judge personality or claim to predict hiring decisions.
"""
import re

HEDGES = re.compile(r"\b(maybe|i think|i guess|i'm not sure|i am not sure|probably|kind of|sort of|i believe)\b", re.I)
STRUCTURE = re.compile(r"\b(first|then|after that|because|as a result|for example|for instance|finally|so that|which means)\b", re.I)
IDEAL_WORDS = (40, 140)  # answers this long read as complete without rambling


def _words(text: str) -> int:
    return len((text or "").split())


def compute(turns: list[dict]) -> list[dict]:
    if not turns:
        return []
    answers = [t.get("answer") or "" for t in turns]
    scores = [float(t.get("score") or 0) for t in turns]
    n = len(answers)

    lengths = [_words(a) for a in answers]
    low, high = IDEAL_WORDS
    length_ok = sum(1 for w in lengths if low <= w <= high) / n
    avg_len = sum(lengths) / n
    communication = round(max(0.0, min(100.0, 100 * (0.5 * length_ok + 0.5 * (1 if avg_len >= 20 else avg_len / 20)))), 1)

    structured = sum(1 for a in answers if STRUCTURE.search(a)) / n
    structure = round(100 * structured, 1)

    hedges = sum(len(HEDGES.findall(a)) for a in answers) / n
    confidence = round(max(0.0, 100 - 25 * hedges), 1)

    relevant = sum(1 for s in scores if s >= 50) / n
    relevance = round(100 * relevant, 1)

    technical = round(sum(scores) / n, 1)

    return [
        {"name": "Technical depth", "score": technical,
         "advice": "Name the tools you used and the exact problem each one solved." if technical < 60 else None},
        {"name": "Relevance", "score": relevance,
         "advice": "Answer the question asked before adding background." if relevance < 60 else None},
        {"name": "Communication", "score": communication,
         "advice": "Aim for two to four sentences, about 40 to 140 words, per answer." if communication < 60 else None},
        {"name": "Structure", "score": structure,
         "advice": "Use a simple order: the situation, what you did, and the result." if structure < 60 else None},
        {"name": "Confidence", "score": confidence,
         "advice": "Replace hedges such as 'I think' and 'maybe' with what you did and why." if confidence < 60 else None},
    ]
