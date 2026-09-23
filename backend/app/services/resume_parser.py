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


def extract_skills_from_text(text: str) -> list[dict]:
    """
    Match taxonomy skills/aliases against resume text.
    Returns a list of dicts: skill_name, category, confidence, evidence.
    """
    if not text:
        return []

    text_lower = text.lower()
    results = []
    seen_canonical = set()

    # Check longer aliases before shorter ones so a compound match like
    # "react.js" (-> react) is found on its own terms rather than only
    # ever being reached through the ambiguous bare "js" alias.
    for alias, canonical in sorted(ALIAS_LOOKUP.items(), key=lambda kv: -len(kv[0])):
        if canonical in seen_canonical:
            continue
        pattern = _pattern_for_alias(alias)
        if not pattern.search(text_lower):
            continue

        mentions = _find_skill_mentions(text_lower, alias)
        evidence = mentions[0] if mentions else None

        confidence = 0.55  # base confidence for a plain mention
        combined_evidence = " ".join(mentions)
        if any(sig in combined_evidence for sig in STRONG_SIGNAL_WORDS):
            confidence = 0.85
        years_match = YEARS_PATTERN.search(combined_evidence)
        if years_match:
            years = int(years_match.group(1))
            confidence = min(0.95, confidence + min(years, 5) * 0.03)

        results.append({
            "skill_name": canonical,
            "category": SKILLS_TAXONOMY[canonical]["category"],
            "confidence": round(confidence, 2),
            "evidence": evidence,
        })
        seen_canonical.add(canonical)

    return results


def parse_resume(file_path: str) -> dict:
    """Full pipeline: returns raw_text and extracted skills for a resume PDF."""
    raw_text = extract_text_from_pdf(file_path)
    skills = extract_skills_from_text(raw_text)
    return {"raw_text": raw_text, "skills": skills}
