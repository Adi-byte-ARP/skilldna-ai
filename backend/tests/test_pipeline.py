"""
End-to-end smoke test: generate a fake resume PDF, parse it, run it
through the scoring engine via the DB, and check we get sane output.
Run with: python -m pytest tests/test_pipeline.py -v
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from reportlab.pdfgen import canvas
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.db_models import User, Submission, ExtractedSkill
from app.services.github_analyzer import normalize_username
from app.services.resume_parser import extract_skills_from_text, parse_resume
from app.services.scoring_engine import build_report

SAMPLE_TEXT = """
John Doe - Software Engineer

Summary: Backend engineer with 4 years of experience in Python and FastAPI.
Proficient in PostgreSQL and Docker. Built CI/CD pipelines using GitHub Actions.

Skills: Python, JavaScript, React, FastAPI, PostgreSQL, Docker, AWS, Git

Experience:
- Developed REST APIs using FastAPI and PostgreSQL.
- Led a team of 3 engineers, strong leadership and communication skills.
- Deployed services on AWS using Docker and Kubernetes.
"""


def make_sample_pdf(path):
    c = canvas.Canvas(path)
    y = 800
    for line in SAMPLE_TEXT.split("\n"):
        c.drawString(50, y, line)
        y -= 15
    c.save()


def test_extract_skills_from_text():
    skills = extract_skills_from_text(SAMPLE_TEXT)
    names = {s["skill_name"] for s in skills}
    assert "python" in names
    assert "fastapi" in names
    assert "postgresql" in names
    assert "leadership" in names
    print(f"\nExtracted {len(skills)} skills: {sorted(names)}")


def test_parse_resume_pdf(tmp_path):
    pdf_path = os.path.join(tmp_path, "sample_resume.pdf")
    make_sample_pdf(pdf_path)
    result = parse_resume(pdf_path)
    assert len(result["raw_text"]) > 0
    assert len(result["skills"]) > 0
    print(f"\nPDF parse found {len(result['skills'])} skills")


def test_normalize_username_accepts_url_variants():
    assert normalize_username("adi-byte-arp") == "adi-byte-arp"
    assert normalize_username("@adi-byte-arp") == "adi-byte-arp"
    assert normalize_username("https://github.com/Adi-byte-ARP") == "Adi-byte-ARP"
    assert normalize_username("github.com/Adi-byte-ARP/") == "Adi-byte-ARP"
    assert normalize_username("https://github.com/Adi-byte-ARP?tab=repositories") == "Adi-byte-ARP"


def test_full_pipeline_with_db(tmp_path):
    # in-memory SQLite for an isolated test DB
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    user = User(name="Test User", email="test@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)

    pdf_path = os.path.join(tmp_path, "sample_resume.pdf")
    make_sample_pdf(pdf_path)
    parsed = parse_resume(pdf_path)

    submission = Submission(user_id=user.id, source_type="resume",
                             original_filename="sample_resume.pdf",
                             raw_text=parsed["raw_text"], status="processed")
    db.add(submission)
    db.commit()
    db.refresh(submission)

    for skill in parsed["skills"]:
        db.add(ExtractedSkill(
            submission_id=submission.id,
            skill_name=skill["skill_name"],
            category=skill["category"],
            confidence=skill["confidence"],
            evidence=skill["evidence"],
        ))
    db.commit()

    report = build_report(db, user.id)
    assert report["overall_score"] > 0
    assert len(report["all_scores"]) > 0
    assert len(report["recommendations"]) > 0

    print(f"\nOverall score: {report['overall_score']}")
    print(f"Top strengths: {[(s.skill_name, s.score) for s in report['strengths']]}")
    print(f"Recommendations: {report['recommendations']}")

    db.close()


def test_weighted_source_scores_total_to_100():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    user = User(name="Weighted User", email="weighted@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)

    source_map = {
        "resume": 100.0,
        "github": 100.0,
        "linkedin": 100.0,
        "certificate": 100.0,
    }

    for source_type, score in source_map.items():
        submission = Submission(
            user_id=user.id,
            source_type=source_type,
            original_filename=f"{source_type}.pdf",
            status="processed",
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)

        db.add(ExtractedSkill(
            submission_id=submission.id,
            skill_name=f"{source_type} skill",
            category="Programming Language",
            confidence=score / 100,
            evidence=f"Evidence from {source_type}",
        ))
        db.commit()

    report = build_report(db, user.id)
    assert report["source_scores"]["resume"] == 30.0
    assert report["source_scores"]["github"] == 30.0
    assert report["source_scores"]["linkedin"] == 25.0
    assert report["source_scores"]["certificate"] == 15.0
    assert report["overall_score"] == 100.0

    db.close()
