import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import User, Submission, ExtractedSkill
from app.models.schemas import SubmissionOut
from app.services.ocr_service import parse_linkedin_screenshot, parse_certificate

router = APIRouter(prefix="/ocr", tags=["ocr"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXT = (".png", ".jpg", ".jpeg", ".webp", ".pdf")


def _save_upload(file: UploadFile) -> str:
    saved_name = f"{uuid.uuid4().hex}_{file.filename}"
    saved_path = os.path.join(UPLOAD_DIR, saved_name)
    with open(saved_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return saved_path


def _process_one(user_id: int, file: UploadFile, source_type: str, parser_fn, db: Session) -> Submission:
    if not file.filename.lower().endswith(ALLOWED_EXT):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type for '{file.filename}'. Allowed: {ALLOWED_EXT}",
        )

    saved_path = _save_upload(file)

    submission = Submission(
        user_id=user_id,
        source_type=source_type,
        original_filename=file.filename,
        status="pending",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    try:
        parsed = parser_fn(saved_path, file.filename)
        submission.raw_text = parsed["raw_text"]
        submission.status = "processed"
        for skill in parsed["skills"]:
            db.add(ExtractedSkill(
                submission_id=submission.id,
                skill_name=skill["skill_name"],
                category=skill["category"],
                confidence=skill["confidence"],
                evidence=skill["evidence"],
            ))
        db.commit()
        db.refresh(submission)
    except ValueError as e:
        submission.status = "failed"
        submission.error_message = str(e)
        db.commit()
        db.refresh(submission)
    except Exception as e:
        submission.status = "failed"
        submission.error_message = f"Unexpected error: {e}"
        db.commit()
        db.refresh(submission)

    return submission


@router.post("/linkedin/{user_id}", response_model=SubmissionOut)
def upload_linkedin(user_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Accepts a screenshot (PNG/JPG/WEBP, needs Tesseract installed) or
    LinkedIn's own 'Save to PDF' profile export (no OCR needed)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _process_one(user_id, file, "linkedin", parse_linkedin_screenshot, db)


@router.post("/certificate/{user_id}", response_model=list[SubmissionOut])
def upload_certificates(user_id: int, files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    """Accepts one or more certificates at once (images or PDFs)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return [_process_one(user_id, f, "certificate", parse_certificate, db) for f in files]
