import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import User, Submission, ExtractedSkill
from app.models.schemas import SubmissionOut
from app.services.resume_parser import parse_resume

router = APIRouter(prefix="/resume", tags=["resume"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload/{user_id}", response_model=SubmissionOut)
def upload_resume(user_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF resumes are supported right now")

    saved_name = f"{uuid.uuid4().hex}_{file.filename}"
    saved_path = os.path.join(UPLOAD_DIR, saved_name)
    with open(saved_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    submission = Submission(
        user_id=user_id,
        source_type="resume",
        original_filename=file.filename,
        status="pending",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    try:
        parsed = parse_resume(saved_path)
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
