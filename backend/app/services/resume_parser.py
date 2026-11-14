"""
Resume parser.

Pipeline: PDF -> raw text (pdfplumber) -> skill matches against the
taxonomy, with a lightweight confidence boost when the skill appears
near signal words like "years", "proficient", "expert" (crude but
effective proxy for depth vs. a passing mention).

This module only depends on pdfplumber + the taxonomy, so it's easy to
unit test in isolation (see tests/test_resume_parser.py).
"""
import re
import pdfplumber
from app.utils.skills_taxonomy import ALIAS_LOOKUP, SKILLS_TAXONOMY

STRONG_SIGNAL_WORDS = [
    "expert", "proficient", "advanced", "years of experience",
    "extensive experience", "specialist", "certified",
]
YEARS_PATTERN = re.compile(r"(\d+)\+?\s*years?", re.IGNORECASE)

# Short, common-word-shaped aliases are prone to false positives: "js" matches
# inside "React.js" or "Node.js" (which are already caught by their own,
# more specific aliases), "r" and "c" and "go" can match inside ordinary
# words or abbreviations ("R&D", "a.c.", "let's go") once you strip word
# boundaries down to punctuation. These require a stricter, list-context
# match: only count them when they appear as their own item in an
# obviously delimited skills list (comma/semicolon/pipe/bullet/newline on
# both sides), not floating in prose.
AMBIGUOUS_SHORT_ALIASES = {"js", "r", "c", "go"}
LIST_BOUNDARY = r"(?:^|[,;:|•\n\t]|\s-\s)"


def _pattern_for_alias(alias: str) -> re.Pattern:
    escaped = re.escape(alias)
    if alias in AMBIGUOUS_SHORT_ALIASES:
        return re.compile(
            LIST_BOUNDARY + r"\s*" + escaped + r"\s*(?:$|[,;|•\n\t])",
            re.IGNORECASE,
        )
    return re.compile(r"(?<![a-zA-Z0-9])" + escaped + r"(?![a-zA-Z0-9])", re.IGNORECASE)


def extract_text_from_pdf(file_path: str) -> str:
    text_chunks = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_chunks.append(page_text)
    return "\n".join(text_chunks)


def count_pdf_pages(file_path: str) -> int:
    with pdfplumber.open(file_path) as pdf:
        return len(pdf.pages)


def _find_skill_mentions(text: str, alias: str) -> list[str]:
    """Return the sentence(s) containing this alias, for use as evidence."""
    pattern = re.compile(r"([^.\n]*\b" + re.escape(alias) + r"\b[^.\n]*)", re.IGNORECASE)
    return [m.strip() for m in pattern.findall(text)]


ACTION_VERBS = re.compile(
    r"\b(built|developed|designed|implemented|deployed|created|led|architected|shipped|engineered|"
    r"optimi[sz]ed|automated|trained|analy[sz]ed|maintained|migrated|integrated|launched|delivered)\b",
    re.IGNORECASE,
)
SKILLS_LINE = re.compile(r"^\s*(technical\s+)?skills\b|\b(languages|frameworks|tools|technologies)\s*:", re.IGNORECASE)


def confidence_from_evidence(lines: list[str], years_text: str) -> tuple[float, str]:
    """Confidence from HOW a skill is used in the resume, not just that it appears.

    A resume alone is a claim, so the range is deliberately narrow: 0.40 to 0.58.
    That keeps every resume-only skill below 60 ("claimed until verified") while still
    letting well-used skills rank above passing mentions:
      - base 0.40 for any mention
      - in a skills list                 +0.04
      - next to an action verb           +0.06   (built, deployed, developed...)
      - a depth word (expert, certified) +0.04
      - each extra line that mentions it +0.02 (max +0.04)
      - years of experience near it      +0.01 per year (max +0.03)
    """
    score = 0.40
    lines_hit = len(lines)
    if any(SKILLS_LINE.search(line) for line in lines):
        score += 0.04
    if any(ACTION_VERBS.search(line) for line in lines):
        score += 0.06
    if any(sig in " ".join(lines) for sig in STRONG_SIGNAL_WORDS):
        score += 0.04
    score += min(max(lines_hit - 1, 0), 2) * 0.02
    years_match = YEARS_PATTERN.search(years_text)
    if years_match:
        score += min(int(years_match.group(1)), 3) * 0.01
    return min(score, 0.58), " / ".join(lines[:2])


def _aliases_by_skill() -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for alias, canonical in ALIAS_LOOKUP.items():
        grouped.setdefault(canonical, []).append(alias)
    return grouped


_ALIASES = None


def extract_skills_from_text(text: str) -> list[dict]:
    """
    Match taxonomy skills against resume text.
    Returns a list of dicts: skill_name, category, confidence, evidence.

    All aliases of a skill are searched together, so "Git" in a skills list and
    "version control" in a sentence are both evidence for the same skill.
    Confidence reflects how the skill is used (see confidence_from_evidence).
    """
    global _ALIASES
    if not text:
        return []
    if _ALIASES is None:
        _ALIASES = _aliases_by_skill()

    text_lower = text.lower()
    lines = [line.strip() for line in text_lower.splitlines() if line.strip()]
    results = []
    for canonical, aliases in _ALIASES.items():
        patterns = [_pattern_for_alias(a) for a in aliases]
        mention_lines = [line for line in lines if any(p.search(line) for p in patterns)]
        if not mention_lines:
            if not any(p.search(text_lower) for p in patterns):
                continue
            mention_lines = [m for a in aliases for m in _find_skill_mentions(text_lower, a)][:5]
        years_text = " ".join(mention_lines)
        confidence, evidence = confidence_from_evidence(mention_lines, years_text)
        results.append({
            "skill_name": canonical,
            "category": SKILLS_TAXONOMY[canonical]["category"],
            "confidence": round(confidence, 2),
            "evidence": evidence or None,
        })
    return results


def parse_resume(file_path: str) -> dict:
    """Full pipeline: returns raw_text and extracted skills for a resume PDF."""
    raw_text = extract_text_from_pdf(file_path)
    skills = extract_skills_from_text(raw_text)
    return {"raw_text": raw_text, "skills": skills}
