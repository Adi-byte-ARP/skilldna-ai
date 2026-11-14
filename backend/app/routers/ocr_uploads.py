import os
import shutil

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import ExtractedSkill, Submission, User
from app.models.schemas import SubmissionOut
from app.routers.auth import authorize_user
from app.services.identity import detect_name, identity_status
from app.services.ocr_service import parse_certificate, parse_linkedin_screenshot
from app.utils.files import stored_filename
from app.services.submissions import DUPLICATE_MESSAGE, find_counted_duplicate, sha256_of, supersede_previous

router = APIRouter(prefix="/ocr", tags=["ocr"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXT = (".png", ".jpg", ".jpeg", ".webp", ".pdf")
SOURCE_LABEL = {"linkedin": "LinkedIn upload", "certificate": "certificate", "resume": "resume"}


def _save_upload(file: UploadFile, data: bytes) -> str:
    saved_path = os.path.join(UPLOAD_DIR, stored_filename(file.filename))
    with open(saved_path, "wb") as f:
        f.write(data)
    return saved_path


def apply_identity(submission: Submission, user: User, source_type: str, raw_text: str) -> bool:
    """Compare the name on the document with the account name. Returns True if verified.

    Only verified documents are counted. Mismatched or unnamed documents keep their text
    for reference but are marked, so the score and the user's dashboard both explain why.
    """
    detected = detect_name(source_type, raw_text)
    status, _ = identity_status(detected, user.name)
    submission.detected_name = detected
    label = SOURCE_LABEL.get(source_type, "document")
    if status == "verified":
        submission.status = "processed"
        submission.error_message = None
        return True
    if status == "mismatch":
        submission.status = "name_mismatch"
        submission.error_message = (
            f"The name on this {label} is '{detected}', but your account name is '{user.name}'. "
            "It was not counted. Upload a document with your own name."
        )
    else:
        submission.status = "name_unverified"
        if source_type == "linkedin":
            submission.error_message = (
                "We could not find your name on this LinkedIn upload, so it was not counted. "
                "Upload your LinkedIn profile PDF, or a screenshot showing both your name "
                "and Skills section."
            )
        else:
            submission.error_message = (
                f"We could not find a name on this {label}, so it was not counted. "
                "Upload a file that shows your name."
            )
    return False


def _store_skills(db: Session, submission: Submission, skills: list[dict]) -> None:
    for skill in skills:
        db.add(ExtractedSkill(
            submission_id=submission.id,
            skill_name=skill["skill_name"],
            category=skill["category"],
            confidence=skill["confidence"],
            evidence=skill["evidence"],
        ))


def _process_one(user: User, file: UploadFile, source_type: str, parser_fn, db: Session) -> Submission:
    """Handle one file completely. A problem with this file never stops the rest of a batch."""
    name = file.filename or "upload"
    if not name.lower().endswith(ALLOWED_EXT):
        submission = Submission(user_id=user.id, source_type=source_type, original_filename=name,
                                status="failed",
                                error_message=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXT)}")
        db.add(submission)
        db.commit()
        db.refresh(submission)
        return submission

    data = file.file.read()
    digest = sha256_of(data)
    if find_counted_duplicate(db, user.id, source_type, digest):
        duplicate = Submission(user_id=user.id, source_type=source_type, original_filename=name,
                               status="duplicate", error_message=DUPLICATE_MESSAGE, content_hash=digest)
        db.add(duplicate)
        db.commit()
        db.refresh(duplicate)
        return duplicate

    saved_path = _save_upload(file, data)
    submission = Submission(user_id=user.id, source_type=source_type, original_filename=name,
                            status="pending", content_hash=digest)
    db.add(submission)
    db.commit()
    db.refresh(submission)

    try:
        parsed = parser_fn(saved_path, name)
        submission.raw_text = parsed["raw_text"]
        if apply_identity(submission, user, source_type, parsed["raw_text"]):
            db.flush()
            supersede_previous(db, user.id, source_type, keep_id=submission.id)
            _store_skills(db, submission, parsed["skills"])
    except ValueError as e:
        submission.status = "failed"
        submission.error_message = str(e)
    except Exception as e:  # keep the batch going whatever one file does
        submission.status = "failed"
        submission.error_message = f"Unexpected error: {e}"
    db.commit()
    db.refresh(submission)
    return submission


def _load_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/linkedin/{user_id}", response_model=SubmissionOut)
def upload_linkedin(user_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), _=Depends(authorize_user)):
    """A screenshot (PNG/JPG/WEBP, needs Tesseract installed) or LinkedIn's 'Save to PDF' export."""
    user = _load_user(db, user_id)
    return _process_one(user, file, "linkedin", parse_linkedin_screenshot, db)


@router.post("/certificate/{user_id}", response_model=list[SubmissionOut])
def upload_certificates(user_id: int, files: list[UploadFile] = File(...), db: Session = Depends(get_db), _=Depends(authorize_user)):
    """Every file in the batch is scanned, one by one. A bad file gets its own error and the rest still run."""
    user = _load_user(db, user_id)
    return [_process_one(user, f, "certificate", parse_certificate, db) for f in files]
