"""Keeps the score honest across repeated uploads.

Rules:
  - An identical file that is already counted is recorded as a duplicate and adds nothing.
  - A new resume or LinkedIn file that is counted replaces the previous one, so the same
    source never adds its evidence twice. Replaced rows are kept, marked 'superseded'.
  - Certificates are independent: each distinct certificate counts once, and several
    different certificates all count.
  - GitHub analyses replace the previous analysis, because repositories change over time.
"""
import hashlib

from sqlalchemy.orm import Session

from app.models.db_models import Submission

ONE_ACTIVE_PER_SOURCE = {"resume", "linkedin", "github"}
DUPLICATE_MESSAGE = (
    "This file is already on your profile, so it was not counted again. "
    "Upload an updated file to change your results."
)


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_counted_duplicate(db: Session, user_id: int, source_type: str, digest: str) -> Submission | None:
    return (
        db.query(Submission)
        .filter(
            Submission.user_id == user_id,
            Submission.source_type == source_type,
            Submission.content_hash == digest,
            Submission.status == "processed",
        )
        .first()
    )


def supersede_previous(db: Session, user_id: int, source_type: str, keep_id: int) -> int:
    """Mark earlier counted submissions of a single-source type as replaced. Returns how many."""
    if source_type not in ONE_ACTIVE_PER_SOURCE:
        return 0
    rows = (
        db.query(Submission)
        .filter(
            Submission.user_id == user_id,
            Submission.source_type == source_type,
            Submission.status == "processed",
            Submission.id != keep_id,
        )
        .all()
    )
    for row in rows:
        row.status = "superseded"
        row.error_message = "Replaced by a newer upload."
    return len(rows)
