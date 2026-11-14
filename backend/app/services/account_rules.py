"""Rules for sign-up: a real Gmail address, a strong password, and a full name.

Gmail rules (as Gmail itself enforces them for new accounts):
  - the domain is exactly gmail.com
  - the part before @ is 6 to 30 characters: letters, digits and single dots
  - it cannot start or end with a dot, and cannot contain two dots in a row

Gmail ignores dots, so a.dith.ya@gmail.com is the same mailbox as adityapattar@gmail.com.
We store the address as typed and keep a canonical form (no dots) to stop duplicate accounts.
"""
import re

GMAIL_DOMAIN = "gmail.com"
GMAIL_LOCAL_RE = re.compile(r"^[a-z0-9]+(?:\.[a-z0-9]+)*$")

PASSWORD_MIN = 8
PASSWORD_MAX = 72
SYMBOLS = set("!@#$%^&*()_+-=[]{};:'\",.<>/?\\|`~")
COMMON_PASSWORDS = {
    "password", "password1", "password123", "12345678", "123456789", "qwerty123", "qwertyuiop",
    "letmein123", "welcome123", "iloveyou1", "abc12345", "admin1234", "passw0rd", "p@ssw0rd",
}


def normalise_gmail(email: str) -> str:
    """Return the trimmed, lowercased address, or raise ValueError with a clear message."""
    address = (email or "").strip().lower()
    if address.count("@") != 1:
        raise ValueError("Enter a Gmail address, for example yourname@gmail.com.")
    local, domain = address.split("@")
    if domain != GMAIL_DOMAIN:
        raise ValueError("Only Gmail addresses are accepted (name@gmail.com).")
    if not 6 <= len(local) <= 30:
        raise ValueError("A Gmail name is 6 to 30 characters long.")
    if not re.match(r"^[a-z0-9.]+$", local):
        raise ValueError("A Gmail name can only use letters, numbers and dots.")
    if not GMAIL_LOCAL_RE.match(local):
        raise ValueError("A Gmail name cannot start or end with a dot, and cannot have two dots in a row.")
    return f"{local}@{GMAIL_DOMAIN}"


def canonical_email(email: str) -> str:
    """Gmail ignores dots in the name part, so this is the key for 'same mailbox'."""
    address = (email or "").strip().lower()
    if address.endswith("@" + GMAIL_DOMAIN):
        local = address.split("@")[0].replace(".", "")
        return f"{local}@{GMAIL_DOMAIN}"
    return address


def password_problems(password: str, email: str = "") -> list[str]:
    """Every rule the password breaks. An empty list means it is acceptable."""
    problems = []
    if len(password) < PASSWORD_MIN:
        problems.append(f"at least {PASSWORD_MIN} characters")
    if len(password) > PASSWORD_MAX:
        problems.append(f"no more than {PASSWORD_MAX} characters")
    if not any(c.isupper() for c in password):
        problems.append("an uppercase letter")
    if not any(c.islower() for c in password):
        problems.append("a lowercase letter")
    if not any(c.isdigit() for c in password):
        problems.append("a number")
    if not any(c in SYMBOLS for c in password):
        problems.append("a symbol such as ! @ # $ %")
    if any(c.isspace() for c in password):
        problems.append("no spaces")
    local = (email or "").split("@")[0].lower()
    if len(local) >= 4 and local in password.lower():
        problems.append("no part of your Gmail name")
    if password.lower() in COMMON_PASSWORDS:
        problems.append("a password that is not on the common-password list")
    return problems


def validate_full_name(name: str) -> str:
    """Two or more words, each a real name part. Used so documents can be matched to it."""
    cleaned = re.sub(r"\s+", " ", (name or "").strip())
    if not cleaned:
        raise ValueError("Enter your full name.")
    if len(cleaned) > 60:
        raise ValueError("Name is too long (60 characters at most).")
    if not re.match(r"^[A-Za-z][A-Za-z.'\- ]*$", cleaned):
        raise ValueError("Name can only use letters, spaces, dots, apostrophes and hyphens.")
    parts = [p for p in cleaned.split(" ") if len(p.strip(".'-")) >= 1]
    full_parts = [p for p in parts if len(p.strip(".'-")) >= 2]
    if len(full_parts) < 2:
        raise ValueError("Enter your first and last name, for example Aditya Pattar.")
    return cleaned
