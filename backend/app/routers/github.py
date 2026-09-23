from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import User, Submission, ExtractedSkill
from app.models.schemas import SubmissionOut
from app.services.github_analyzer import fetch_github_profile, extract_skills_from_github

router = APIRouter(prefix="/github", tags=["github"])


@router.post("/analyze/{user_id}", response_model=SubmissionOut)
def analyze_github(user_id: int, username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    submission = Submission(
        user_id=user_id,
        source_type="github",
        original_filename=username,
        status="pending",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    try:
        github_data = fetch_github_profile(username)
        skills = extract_skills_from_github(github_data)
        submission.raw_text = f"GitHub user: {username}, {len(github_data['repos'])} repos"
        submission.status = "processed"
        for skill in skills:
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
