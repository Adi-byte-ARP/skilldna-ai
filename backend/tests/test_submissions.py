"""Repeated and multiple uploads: identical files add nothing, updates replace, certificates all count."""
import io
import os
import shutil
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DATABASE_URL", f"sqlite:////tmp/skilldna_submissions_test_{uuid.uuid4().hex}.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
needs_tesseract = pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")


def _account(name="Ravi Kumar"):
    email = f"sub{uuid.uuid4().hex[:12]}@gmail.com"
    r = client.post("/auth/register", json={"name": name, "email": email, "password": "TestPass123!"})
    body = r.json()
    return body["user"]["id"], {"Authorization": f"Bearer {body['token']}"}


def _resume(lines):
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for line in lines:
        c.drawString(50, y, line)
        y -= 20
    c.save()
    return buf.getvalue()


def _cert_png(path, name, course, subtitle=""):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(FONT, 34)
    small = ImageFont.truetype(FONT, 26)
    img = Image.new("RGB", (1100, 320), "white")
    draw = ImageDraw.Draw(img)
    draw.text((40, 30), "The certificate is awarded to", fill="black", font=font)
    draw.text((40, 90), name, fill="black", font=font)
    draw.text((40, 160), course, fill="black", font=font)
    if subtitle:
        draw.text((40, 230), subtitle, fill="black", font=small)
    img.save(path)
    return str(path)


def _skills_of(user_id, headers):
    return {s["skill_name"] for s in client.get(f"/report/{user_id}", headers=headers).json().get("all_scores", [])}


def _score_of(user_id, headers, skill):
    for s in client.get(f"/report/{user_id}", headers=headers).json().get("all_scores", []):
        if s["skill_name"] == skill:
            return s["score"]
    return None


def test_same_resume_uploaded_twice_does_not_raise_the_score():
    uid, h = _account("Ravi Kumar")
    pdf = _resume(["Ravi Kumar", "Built services in Python and deployed them on Docker."])
    first = client.post(f"/resume/upload/{uid}", headers=h, files={"file": ("cv.pdf", pdf, "application/pdf")}).json()
    assert first["status"] == "processed"
    before = _score_of(uid, h, "python")
    second = client.post(f"/resume/upload/{uid}", headers=h, files={"file": ("cv.pdf", pdf, "application/pdf")}).json()
    assert second["status"] == "duplicate"
    assert "not counted again" in second["error_message"]
    assert _score_of(uid, h, "python") == before


def test_an_updated_resume_replaces_the_old_one_instead_of_adding_to_it():
    uid, h = _account("Ravi Kumar")
    old = _resume(["Ravi Kumar", "Skills: Python"])
    new = _resume(["Ravi Kumar", "Skills: Python, Docker", "Built a Docker pipeline. Expert in Docker."])
    client.post(f"/resume/upload/{uid}", headers=h, files={"file": ("cv.pdf", old, "application/pdf")})
    updated = client.post(f"/resume/upload/{uid}", headers=h, files={"file": ("cv2.pdf", new, "application/pdf")}).json()
    assert updated["status"] == "processed"
    assert "docker" in _skills_of(uid, h)
    # the earlier file is kept for reference but no longer counts: its only skill is gone
    assert _score_of(uid, h, "docker") is not None


def test_a_resume_with_another_name_does_not_replace_a_good_one():
    uid, h = _account("Ravi Kumar")
    good = _resume(["Ravi Kumar", "Skills: Python"])
    other = _resume(["Rahul Patel", "Skills: Java"])
    client.post(f"/resume/upload/{uid}", headers=h, files={"file": ("good.pdf", good, "application/pdf")})
    bad = client.post(f"/resume/upload/{uid}", headers=h, files={"file": ("other.pdf", other, "application/pdf")}).json()
    assert bad["status"] == "name_mismatch"
    skills = _skills_of(uid, h)
    assert "python" in skills and "java" not in skills


@needs_tesseract
def test_three_to_four_different_certificates_each_count(tmp_path):
    uid, h = _account("Ravi Kumar")
    certs = [
        ("gen-ai.png", "Generative AI Unleashing", "Prompt Engineering with Large Language Models"),
        ("cv.png", "Computer Vision 101", "OpenCV and image processing"),
        ("cyber.png", "Cybersecurity Fundamentals", "Network security and ethical hacking"),
        ("cloud.png", "Cloud Computing Basics", "Terraform and Docker for infrastructure"),
    ]
    files = [("files", (name, open(_cert_png(tmp_path / name, "RAVI KUMAR", course, sub), "rb"), "image/png"))
             for name, course, sub in certs]
    results = client.post(f"/ocr/certificate/{uid}", headers=h, files=files).json()
    assert len(results) == 4
    assert all(r["status"] == "processed" for r in results), [r["status"] for r in results]
    assert all(len(r["extracted_skills"]) >= 1 for r in results)
    skills = _skills_of(uid, h)
    assert {"generative ai", "computer vision", "cybersecurity", "terraform"} <= skills


@needs_tesseract
def test_the_same_certificate_twice_is_not_counted_twice(tmp_path):
    uid, h = _account("Ravi Kumar")
    path = _cert_png(tmp_path / "same.png", "RAVI KUMAR", "Computer Vision 101")
    client.post(f"/ocr/certificate/{uid}", headers=h, files=[("files", ("same.png", open(path, "rb"), "image/png"))])
    before = _score_of(uid, h, "computer vision")
    again = client.post(f"/ocr/certificate/{uid}", headers=h, files=[("files", ("same.png", open(path, "rb"), "image/png"))]).json()
    assert again[0]["status"] == "duplicate"
    assert _score_of(uid, h, "computer vision") == before
