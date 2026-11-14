"""Checks that a document belongs to the account holder.

Every resume, LinkedIn upload and certificate is compared with the name on the account.
A document whose name does not match is not counted toward the score, and the user is told why.

Matching rules (case and accents ignored, single initials ignored):
  - the first name must match, and
  - when both names have a surname, the surname must match too.
So "Aditya R Pattar" matches "ADITYA R PATTAR", "ADITYA R P" (LinkedIn initial) and "ADITYA PATTAR".
"Aditya Kumar" does not match "Aditya Pattar".
"""
import re
import unicodedata

NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z.'\-]*(\s+[A-Za-z][A-Za-z.'\-]*){1,3}$")
NOT_A_NAME_WORDS = {
    "resume", "curriculum", "vitae", "cv", "summary", "objective", "profile", "skills", "experience",
    "education", "projects", "certificate", "certification", "course", "completion", "linkedin",
    "developer", "engineer", "student", "intern", "analyst", "designer", "manager", "scientist",
    "full", "stack", "backend", "frontend", "software", "data", "web", "contact", "email", "phone",
    "github", "bagalkot", "karnataka", "india", "university", "college",
}

# Phrases that introduce the recipient's name on a certificate.
CERTIFICATE_LEAD_IN = re.compile(
    r"(awarded to|presented to|certify that|certifies that|this is to certify that|issued to|"
    r"conferred (?:up)?on|this certifies that)",
    re.IGNORECASE,
)


def _ascii_letters(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def name_tokens(name: str) -> list[str]:
    """Lowercase letter-only tokens, with single initials removed."""
    cleaned = re.sub(r"[^A-Za-z'\-\s]", " ", _ascii_letters(name))
    return [t.lower().strip("'-") for t in cleaned.split() if len(t.strip("'-")) > 1]


def _looks_like_name(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 60 or "@" in line or re.search(r"\d", line):
        return False
    if not NAME_PATTERN.match(_ascii_letters(line).replace("@", "")):
        return False
    raw_words = [w.strip(".'-") for w in line.split()]
    # names are written with each word capitalised ("Aditya R Pattar" or "ADITYA R PATTAR")
    if not all(w[:1].isupper() for w in raw_words):
        return False
    words = [w.lower() for w in raw_words]
    if any(w in NOT_A_NAME_WORDS for w in words):
        return False
    # a name has at least one word longer than an initial
    return sum(1 for w in words if len(w) > 1) >= 1 and len(words) >= 2


def detect_resume_name(text: str) -> str | None:
    """A labelled 'Name:' line wins. Otherwise the first line that looks like a name."""
    for line in (text or "").splitlines():
        match = re.match(r"^\s*name\s*[:\-]\s*(.+)$", line, re.IGNORECASE)
        if match and _looks_like_name(match.group(1)):
            return match.group(1).strip()
    for line in (text or "").splitlines():
        if _looks_like_name(line):
            return re.sub(r"\s+", " ", line.strip())
    return None


def detect_linkedin_name(text: str) -> str | None:
    """LinkedIn cards start with the person's name. Verification badges and symbols after
    the name are stripped first."""
    for line in (text or "").splitlines():
        cleaned = re.sub(r"[^A-Za-z.'\-\s]+", " ", line)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if _looks_like_name(cleaned):
            return cleaned
    return None


def detect_certificate_name(text: str) -> str | None:
    """The name follows 'awarded to' (or similar), on the same line or the next one."""
    lines = (text or "").splitlines()
    for i, line in enumerate(lines):
        match = CERTIFICATE_LEAD_IN.search(line)
        if not match:
            continue
        after = line[match.end():].strip(" :,-")
        if after and _looks_like_name(after):
            return after
        for candidate in lines[i + 1:i + 4]:
            if _looks_like_name(candidate):
                return candidate.strip()
    return None


def detect_name(source_type: str, text: str) -> str | None:
    if source_type == "resume":
        return detect_resume_name(text)
    if source_type == "linkedin":
        return detect_linkedin_name(text)
    if source_type == "certificate":
        return detect_certificate_name(text)
    return None


def names_match(a: str, b: str) -> bool:
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb:
        return False
    if ta[0] != tb[0]:
        return False
    if len(ta) >= 2 and len(tb) >= 2 and ta[-1] != tb[-1]:
        return False
    return True


def identity_status(detected: str | None, account_name: str) -> tuple[str, str | None]:
    """Returns (status, message). status is 'verified', 'mismatch' or 'unverified'."""
    if not detected:
        return "unverified", None
    if names_match(detected, account_name):
        return "verified", None
    return "mismatch", detected
