"""Role recommendations, derived from the user's skill scores and the role skill lists.

A role's fit is the average strength across that role's skills (a skill with no evidence counts as 0).
The recommendation lists what the user already shows, what is weak, and what is missing, so the
gap to the role is visible rather than a bare percentage.
"""
from app.services.mock_content import ROLE_SKILLS
from app.services.roadmap import _as_pair

STRONG = 60  # a skill scored at or above this counts as shown


def recommend_roles(all_scores: list) -> list[dict]:
    by_name = {}
    for item in all_scores:
        name, score = _as_pair(item)
        by_name[name.lower()] = score
    results = []
    for role, skills in ROLE_SKILLS.items():
        strength = [min(by_name.get(s.lower(), 0.0), 100.0) for s in skills]
        fit = round(sum(strength) / (100.0 * len(skills)) * 100, 1)
        strong = [s for s in skills if by_name.get(s.lower(), 0) >= STRONG]
        weak = [s for s in skills if 0 < by_name.get(s.lower(), 0) < STRONG]
        missing = [s for s in skills if by_name.get(s.lower(), 0) <= 0]
        results.append({
            "role": role,
            "fit": fit,
            "strong": strong,
            "weak": weak,
            "missing": missing,
            "gap_count": len(weak) + len(missing),
            "reason": _reason(role, strong, weak, missing),
        })
    results.sort(key=lambda r: (-r["fit"], r["gap_count"]))
    return results


def _reason(role: str, strong: list[str], weak: list[str], missing: list[str]) -> str:
    total = len(strong) + len(weak) + len(missing)
    if not strong and not weak:
        return f"You have no evidence yet for the {total} skills {role} expects. Upload a resume or certificates to start."
    parts = [f"You already show {len(strong)} of {total} skills for {role}."]
    if missing:
        parts.append("Not yet shown: " + ", ".join(missing[:3]) + ".")
    if weak:
        parts.append("Shown but weak: " + ", ".join(weak[:3]) + ".")
    return " ".join(parts)
