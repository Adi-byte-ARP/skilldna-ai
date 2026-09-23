"""
Scoring engine.

Aggregates ExtractedSkill rows across ALL of a user's submissions
(resume, GitHub, LinkedIn, certificates) into one SkillScore per skill,
then rolls those up into an overall SkillDNA score and recommendations.

Aggregation rule (deliberately simple and explainable, not a black box):
  - each source contributes confidence (0-1) for a skill it mentions
  - a skill validated by MULTIPLE independent sources scores higher than
    the same confidence from a single source (this is the whole point of
    "consolidating resume, coding-profile, LinkedIn, and certificate data
    into one composite assessment" instead of just parsing one document)
  - final per-skill score = 100 * (1 - product(1 - confidence_i))
    i.e. treat each source as independent evidence and combine via
    "noisy-OR" so 2-3 medium-confidence sources compound meaningfully
"""
from collections import defaultdict
from sqlalchemy.orm import Session
from app.models.db_models import Submission, ExtractedSkill, SkillScore


def _noisy_or(confidences: list[float]) -> float:
    prob_none = 1.0
    for c in confidences:
        prob_none *= (1 - c)
    return 1 - prob_none


def compute_scores_for_user(db: Session, user_id: int) -> list[SkillScore]:
    submissions = (
        db.query(Submission)
        .filter(Submission.user_id == user_id, Submission.status == "processed")
        .all()
    )

    # skill_name -> list of (confidence, source_type)
    evidence_map: dict[str, list[tuple[float, str]]] = defaultdict(list)
    category_map: dict[str, str] = {}

    for sub in submissions:
        for skill in sub.extracted_skills:
            evidence_map[skill.skill_name].append((skill.confidence, sub.source_type))
            category_map[skill.skill_name] = skill.category

    # clear old scores and recompute fresh (simplest correct approach for a v1)
    db.query(SkillScore).filter(SkillScore.user_id == user_id).delete()

    new_scores = []
    for skill_name, evidence in evidence_map.items():
        confidences = [c for c, _ in evidence]
        sources = sorted(set(s for _, s in evidence))
        score = round(_noisy_or(confidences) * 100, 1)
        skill_score = SkillScore(
            user_id=user_id,
            skill_name=skill_name,
            category=category_map.get(skill_name),
            score=score,
            sources=sources,
        )
        db.add(skill_score)
        new_scores.append(skill_score)

    db.commit()
    for s in new_scores:
        db.refresh(s)
    return new_scores


TIER_THRESHOLDS = [
    (90, "Expert-verified"),
    (75, "Strong"),
    (60, "Solid"),
    (40, "Developing"),
    (0, "Early-stage"),
]

# Concrete, skill-category-specific next actions. Generic advice like
# "add more evidence" is true of every gap and therefore useless — these
# templates give a different, doable next step depending on what kind of
# skill is weak, since "prove you know Python" and "prove you have
# leadership experience" don't call for the same fix.
GAP_ACTION_BY_CATEGORY = {
    "Programming Language": (
        "ship a small project in {skill} and link the repo — working code is the "
        "fastest way to turn a language claim into verified evidence"
    ),
    "Framework": (
        "build something real with {skill}, even a small one, and put it on GitHub — "
        "frameworks are proven by usage, not by naming them"
    ),
    "Database": (
        "add a project README or portfolio note describing actual schema/query work "
        "you've done with {skill}, not just that you've used it"
    ),
    "Cloud/DevOps": (
        "a certification (e.g. an associate-level {skill} cert) is the fastest way to "
        "convert this from a resume line into third-party-verified evidence"
    ),
    "Data/ML": (
        "publish a notebook, Kaggle entry, or writeup that actually uses {skill} — "
        "ML claims are especially easy to inflate and easy to verify with one link"
    ),
    "Soft Skill": (
        "these are hard to verify with documents alone — ask a manager or professor "
        "for a LinkedIn recommendation that specifically mentions your {skill}"
    ),
}

# A few skills need their own phrasing because the category default
# doesn't quite fit them (e.g. suggesting a "certification" for Git is
# an odd recommendation — consistent public contribution history is the
# real evidence for that one).
SKILL_SPECIFIC_GAP_ACTIONS = {
    "git": "keep a steady public commit history across a few repos — consistent activity is the evidence here, not a certificate",
    "linux": "document specific sysadmin/scripting work (a dotfiles repo, a homelab writeup) rather than just listing it",
}

# Rough role-fit mapping by dominant category cluster among strengths.
# Not exhaustive career advice — just a starting point to point the
# person toward roles where their strongest, best-verified skills matter.
ROLE_FIT_BY_CATEGORY = {
    "Programming Language": ["Software Engineer", "Backend Developer"],
    "Framework": ["Full-stack Developer", "Frontend Engineer"],
    "Database": ["Backend Engineer", "Data Engineer"],
    "Cloud/DevOps": ["DevOps Engineer", "Site Reliability Engineer"],
    "Data/ML": ["ML Engineer", "Data Scientist"],
    "Soft Skill": ["Team Lead", "Technical Project Manager"],
}


def _tier_for_score(score: float) -> str:
    for threshold, label in TIER_THRESHOLDS:
        if score >= threshold:
            return label
    return "Early-stage"


def build_report(db: Session, user_id: int) -> dict:
    scores = compute_scores_for_user(db, user_id)

    if not scores:
        return {
            "user_id": user_id,
            "overall_score": 0.0,
            "tier": "No data yet",
            "strengths": [],
            "gaps": [],
            "all_scores": [],
            "recommendations": [
                "No skills detected yet — upload a resume, GitHub profile, "
                "LinkedIn screenshot, or certificate to get your SkillDNA score."
            ],
        }

    overall_score = round(sum(s.score for s in scores) / len(scores), 1)
    sorted_scores = sorted(scores, key=lambda s: s.score, reverse=True)
    strengths = sorted_scores[:5]
    gaps = [s for s in sorted_scores if s.score < 60][-5:]
    source_types_used = set(src for s in scores for src in (s.sources or []))

    recommendations = _generate_recommendations(strengths, gaps, sorted_scores, source_types_used)

    return {
        "user_id": user_id,
        "overall_score": overall_score,
        "tier": _tier_for_score(overall_score),
        "strengths": strengths,
        "gaps": gaps,
        "all_scores": sorted_scores,
        "recommendations": recommendations,
    }


def _generate_recommendations(strengths, gaps, all_scores, source_types_used) -> list[str]:
    """Rule-based, but specific: every recommendation names real skills
    from this user's actual data and gives a concrete next action, not a
    generic platitude. (The clean seam to swap in an LLM call for even
    richer natural-language coaching is right here — this function's
    inputs/outputs would stay the same.)"""
    recs = []

    # 1. Source diversity — the single highest-leverage thing a user can
    # do, since the whole scoring model is built on cross-validation.
    if len(source_types_used) <= 1:
        missing = {"resume", "github", "linkedin", "certificate"} - source_types_used
        recs.append(
            f"You've only got evidence from {len(source_types_used)} source so far — "
            f"every score below is a single unconfirmed claim. Add {', '.join(sorted(missing)[:2])} "
            f"next; that alone will move most of your scores more than anything else here."
        )

    # 2. Concrete, per-skill actions for the weakest 2-3 gaps — not a
    # dumped list of names, an actual instruction for the top offenders.
    actionable_gaps = [
        g for g in gaps
        if g.skill_name in SKILL_SPECIFIC_GAP_ACTIONS or g.category in GAP_ACTION_BY_CATEGORY
    ][:3]
    for gap in actionable_gaps:
        if gap.skill_name in SKILL_SPECIFIC_GAP_ACTIONS:
            action = SKILL_SPECIFIC_GAP_ACTIONS[gap.skill_name]
        else:
            action = GAP_ACTION_BY_CATEGORY[gap.category].format(skill=gap.skill_name.title())
        recs.append(f"'{gap.skill_name}' is at {gap.score:.0f}/100 — {action}.")

    # 3. Single-source strengths worth reinforcing (skills that scored
    # well but are still resting on only one source, so they're one
    # source loss away from looking unverified).
    fragile_strengths = [s for s in strengths if s.sources and len(s.sources) == 1]
    if fragile_strengths:
        names = ", ".join(f"'{s.skill_name}'" for s in fragile_strengths[:3])
        recs.append(
            f"{names} score{'s' if len(fragile_strengths) == 1 else ''} well but "
            f"each rest{'s' if len(fragile_strengths) == 1 else ''} on a single source. "
            f"A second confirming source would push these into your most defensible skills."
        )

    # 4. Role fit, based on the dominant category among real strengths —
    # only offered once there's enough signal to say anything specific.
    if strengths:
        category_scores: dict[str, float] = {}
        for s in strengths:
            if s.category:
                category_scores[s.category] = category_scores.get(s.category, 0) + s.score
        if category_scores:
            top_category = max(category_scores, key=category_scores.get)
            roles = ROLE_FIT_BY_CATEGORY.get(top_category)
            if roles:
                recs.append(
                    f"Your best-verified skills cluster around {top_category} — "
                    f"that profile lines up well with roles like {roles[0]} or {roles[1]}."
                )

    if not recs:
        recs.append(
            "Every skill here is currently backed by just one source. Add a second "
            "source (GitHub, a certificate, or LinkedIn) to start generating real "
            "cross-validated confidence scores instead of single-document guesses."
        )

    return recs
