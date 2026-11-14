from app.utils.files import stored_filename
from app.routers.auth import authorize_user
import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import User, Submission, ExtractedSkill
from app.models.schemas import SubmissionOut
from app.services.resume_parser import parse_resume
from app.routers.ocr_uploads import apply_identity
from app.services.submissions import DUPLICATE_MESSAGE, find_counted_duplicate, sha256_of, supersede_previous

router = APIRouter(prefix="/resume", tags=["resume"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload/{user_id}", response_model=SubmissionOut)
def upload_resume(user_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), _=Depends(authorize_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF resumes are supported right now")

    data = file.file.read()
    digest = sha256_of(data)
    if find_counted_duplicate(db, user.id, "resume", digest):
        duplicate = Submission(user_id=user_id, source_type="resume", original_filename=file.filename,
                               status="duplicate", error_message=DUPLICATE_MESSAGE, content_hash=digest)
        db.add(duplicate)
        db.commit()
        db.refresh(duplicate)
        return duplicate

    saved_name = stored_filename(file.filename)
    saved_path = os.path.join(UPLOAD_DIR, saved_name)
    with open(saved_path, "wb") as f:
        f.write(data)

    submission = Submission(
        user_id=user_id,
        source_type="resume",
        original_filename=file.filename,
        status="pending",
        content_hash=digest,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    try:
        parsed = parse_resume(saved_path)
        submission.raw_text = parsed["raw_text"]
        if apply_identity(submission, user, "resume", parsed["raw_text"]):
            db.flush()
            supersede_previous(db, user.id, "resume", keep_id=submission.id)
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
    except Exception as e:
        submission.status = "failed"
        submission.error_message = str(e)
        db.commit()
        db.refresh(submission)
    finally:
        # keep uploaded file for now (useful for debugging); in prod, delete
        # or move to object storage instead
        pass

    return submission
