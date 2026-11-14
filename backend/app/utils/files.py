"""Filename handling for uploads.

Client-supplied filenames are untrusted. They can contain path separators
("../", "/") or be very long. The stored name is always a random id plus a
cleaned copy of the original, and the original's directory parts are dropped.
"""
import os
import re
import uuid

_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")
MAX_NAME_LENGTH = 80


def clean_filename(filename: str | None) -> str:
    base = os.path.basename((filename or "").replace("\\", "/")) or "upload"
    cleaned = _SAFE_CHARS.sub("_", base)[:MAX_NAME_LENGTH]
    return cleaned.lstrip(".") or "upload"


def stored_filename(filename: str | None) -> str:
    return f"{uuid.uuid4().hex}_{clean_filename(filename)}"
