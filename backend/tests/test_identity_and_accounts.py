"""Name checks across documents, Gmail and password rules, and batch uploads."""
import io
import os
import shutil
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DATABASE_URL", f"sqlite:////tmp/skilldna_identity_test_{uuid.uuid4().hex}.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.services.account_rules import canonical_email, normalise_gmail, password_problems, validate_full_name  # noqa: E402
from app.services.identity import (  # noqa: E402
    detect_certificate_name, detect_linkedin_name, detect_resume_name, names_match,
)

client = TestClient(app)
GOOD_PASSWORD = "TestPass123!"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
needs_tesseract = pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")


def _account(name="Aditya Pattar"):
    email = f"id{uuid.uuid4().hex[:12]}@gmail.com"
    r = client.post("/auth/register", json={"name": name, "email": email, "password": GOOD_PASSWORD})
    assert r.status_code == 200, r.text
    body = r.json()
    return body["user"]["id"], {"Authorization": f"Bearer {body['token']}"}, email


def _pdf(lines):
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for line in lines:
        c.drawString(50, y, line)
        y -= 22
    c.save()
    return buf.getvalue()


def _png(lines, path):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(FONT, 34)
    img = Image.new("RGB", (1000, 120 + 60 * len(lines)), "white")
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        draw.text((40, 30 + i * 60), line, fill="black", font=font)
    img.save(path)
    return str(path)


# ---------- name matching ----------

@pytest.mark.parametrize("document_name, account, expected", [
    ("ADITYA R PATTAR", "Aditya R Pattar", True),
    ("ADITYA R P", "Aditya R Pattar", True),          # LinkedIn shows an initial
    ("ADITYA PATTAR", "Aditya R Pattar", True),       # certificate omits the middle initial
    ("Aditya Kumar", "Aditya R Pattar", False),       # different surname
    ("Rahul Pattar", "Aditya R Pattar", False),       # different first name
    ("Pattar Aditya", "Aditya R Pattar", False),      # order matters
    ("Adi Pattar", "Aditya R Pattar", False),         # different first name
    ("Jose Munoz", "José Muñoz", True),               # accents ignored
])
def test_names_match_rules(document_name, account, expected):
    assert names_match(document_name, account) is expected


def test_names_are_read_from_each_document_type():
    assert detect_resume_name("ADITYA R PATTAR\nadityapattar204@gmail.com\nSUMMARY") == "ADITYA R PATTAR"
    assert detect_linkedin_name("ADITYA R P@\nStudent at Basaveshwara Engineering College") == "ADITYA R P"
    assert detect_certificate_name("The certificate is awarded to\nADITYA PATTAR\nfor successfully completing") == "ADITYA PATTAR"


def test_resume_without_a_name_is_not_read_as_one():
    assert detect_resume_name("Full Stack Developer\nSUMMARY\nBuilt things") is None
    assert detect_certificate_name("Certificate of Completion\nMachine Learning") is None


# ---------- Gmail and password rules ----------

@pytest.mark.parametrize("address", [
    "a.b@gmail.com", "x@gmail.com", ".abc.def@gmail.com", "ab..cdef@gmail.com",
    "abc@yahoo.com", "adityapattar@gmail.co", "aditya_pattar@gmail.com",
])
def test_non_gmail_or_malformed_addresses_are_refused(address):
    with pytest.raises(ValueError):
        normalise_gmail(address)


def test_gmail_is_normalised_and_dots_are_the_same_mailbox():
    assert normalise_gmail("  ADITYA.PATTAR@Gmail.com ") == "aditya.pattar@gmail.com"
    assert canonical_email("aditya.pattar@gmail.com") == canonical_email("adityapattar@gmail.com")


def test_password_rules_list_what_is_missing():
    problems = password_problems("weak")
    assert "at least 8 characters" in problems and "a symbol such as ! @ # $ %" in problems
    assert password_problems(GOOD_PASSWORD, "someone@gmail.com") == []
    assert "no part of your Gmail name" in password_problems("Pattar2026!Xy", "pattar2026@gmail.com")
    assert "no part of your Gmail name" not in password_problems(GOOD_PASSWORD, "pattar2026@gmail.com")


def test_full_name_needs_first_and_last_name():
    assert validate_full_name("Aditya Pattar") == "Aditya Pattar"
    with pytest.raises(ValueError):
        validate_full_name("Aditya")
    with pytest.raises(ValueError):
        validate_full_name("Aditya123 Pattar")


def test_register_rejects_bad_input_with_a_clear_message():
    r = client.post("/auth/register", json={"name": "Aditya Pattar", "email": "someone@yahoo.com", "password": GOOD_PASSWORD})
    assert r.status_code == 400 and "Gmail" in r.json()["detail"]
    r = client.post("/auth/register", json={"name": "Aditya Pattar", "email": "weakpass1@gmail.com", "password": "short"})
    assert r.status_code == 400 and "Password needs" in r.json()["detail"]
    r = client.post("/auth/register", json={"name": "Aditya", "email": "onename1@gmail.com", "password": GOOD_PASSWORD})
    assert r.status_code == 400


def test_dotted_gmail_cannot_create_a_second_account_and_login_works_either_way():
    base = f"dotcheck{uuid.uuid4().hex[:8]}"
    first = client.post("/auth/register", json={"name": "Dot Check", "email": f"{base}@gmail.com", "password": GOOD_PASSWORD})
    assert first.status_code == 200
    dotted = f"{base[:4]}.{base[4:]}@gmail.com"
    dup = client.post("/auth/register", json={"name": "Dot Check", "email": dotted, "password": GOOD_PASSWORD})
    assert dup.status_code == 409
    assert client.post("/auth/login", json={"email": dotted, "password": GOOD_PASSWORD}).status_code == 200


# ---------- batches and identity on uploads ----------

def test_resume_with_another_name_is_marked_and_not_counted():
    uid, h, _ = _account("Aditya Pattar")
    pdf = _pdf(["Rahul Pattar", "Skills: Python, FastAPI, Docker"])
    r = client.post(f"/resume/upload/{uid}", headers=h, files={"file": ("cv.pdf", pdf, "application/pdf")}).json()
    assert r["status"] == "name_mismatch"
    assert "Rahul Pattar" in r["error_message"] and r["extracted_skills"] == []
    report = client.get(f"/report/{uid}", headers=h).json()
    assert report["overall_score"] == 0 or not report.get("all_scores")


def test_linkedin_skills_only_pdf_is_not_counted_and_explains_name_requirement():
    uid, h, _ = _account("Aditya Pattar")
    pdf = _pdf(["Skills", "Python", "React"])
    response = client.post(
        f"/ocr/linkedin/{uid}",
        headers=h,
        files={"file": ("skills.pdf", pdf, "application/pdf")},
    )
    result = response.json()

    assert response.status_code == 200
    assert result["status"] == "name_unverified"
    assert result["extracted_skills"] == []
    assert "profile PDF" in result["error_message"]
    assert "both your name and Skills section" in result["error_message"]


def test_linkedin_pdf_with_matching_name_and_skills_is_counted():
    uid, h, _ = _account("Aditya Pattar")
    pdf = _pdf(["ADITYA R PATTAR", "Skills", "Python", "React", "Experience"])
    response = client.post(
        f"/ocr/linkedin/{uid}",
        headers=h,
        files={"file": ("profile.pdf", pdf, "application/pdf")},
    )
    result = response.json()

    assert response.status_code == 200
    assert result["status"] == "processed"
    assert {skill["skill_name"] for skill in result["extracted_skills"]} >= {"python", "react"}


@needs_tesseract
def test_every_certificate_in_a_batch_is_scanned_and_a_bad_file_does_not_stop_the_rest(tmp_path):
    uid, h, _ = _account("Aditya Pattar")
    good1 = _png(["The certificate is awarded to", "ADITYA PATTAR", "Machine Learning Specialization"], tmp_path / "a.png")
    other = _png(["The certificate is awarded to", "RAHUL PATTAR", "Docker Basics"], tmp_path / "b.png")
    good2 = _png(["The certificate is awarded to", "ADITYA R PATTAR", "Computer Vision 101"], tmp_path / "c.png")
    files = [
        ("files", ("first.png", open(good1, "rb"), "image/png")),
        ("files", ("notes.txt", b"not a certificate", "text/plain")),
        ("files", ("other.png", open(other, "rb"), "image/png")),
        ("files", ("third.png", open(good2, "rb"), "image/png")),
    ]
    results = client.post(f"/ocr/certificate/{uid}", headers=h, files=files).json()
    assert len(results) == 4, "every file in the batch must get a result"
    by_name = {r["original_filename"]: r for r in results}
    assert by_name["first.png"]["status"] == "processed"
    assert by_name["notes.txt"]["status"] == "failed"
    assert by_name["other.png"]["status"] == "name_mismatch"
    assert by_name["third.png"]["status"] == "processed"


def test_plan_history_records_one_snapshot_per_day():
    uid, h, _ = _account("Aditya Pattar")
    client.get("/plan", params={"role": "Backend Engineer"}, headers=h)
    client.get("/plan", params={"role": "Backend Engineer"}, headers=h)
    history = client.get("/plan/history", headers=h).json()
    assert len(history) == 1 and history[0]["role"] == "Backend Engineer"


def test_daily_today_includes_the_reminder_state():
    _, h, _ = _account("Aditya Pattar")
    body = client.get("/daily/today", params={"local_hour": 20}, headers=h).json()
    assert body["remind_now"] is True and body["email_opt_in"] is False
    assert client.get("/daily/today", params={"local_hour": 30}, headers=h).status_code == 400
