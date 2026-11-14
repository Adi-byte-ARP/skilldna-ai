"""Regression tests: LinkedIn uploads count only the Skills section.

Background: a LinkedIn screenshot also shows a right-hand sidebar with other
people's headlines. Earlier, OCR of the whole screenshot picked up "Java" from
someone else's headline and gave the user a false, heavily weighted score.
"""
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import ocr_service as ocr  # noqa: E402

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
needs_tesseract = pytest.mark.skipif(
    shutil.which("tesseract") is None, reason="tesseract not installed"
)


# ---------- pure text tests (no OCR needed) ----------

def test_skills_are_counted_only_inside_skills_block():
    text = "\n".join([
        "Experience",
        "Built services in Java and Python",
        "Skills",
        "React",
        "Docker",
        "Experience",  # next section ends the Skills block
        "Java",
    ])
    found, section = ocr.extract_skills_section(text)
    assert found is True
    assert "React" in section and "Docker" in section
    assert "Java" not in section  # outside the Skills block


def test_no_skills_heading_means_nothing_is_counted():
    text = "Student at Basaveshwara Engineering College\nJava & Next.js\nPython"
    found, section = ocr.extract_skills_section(text)
    assert found is False
    with pytest.raises(ValueError, match="No Skills section found"):
        ocr.parse_linkedin_text(text)


def test_ui_noise_inside_skills_block_is_ignored():
    text = "\n".join([
        "Skills",
        "Python",
        "Show all 12 skills",
        "5 endorsements",
        "Git",
    ])
    _, section = ocr.extract_skills_section(text)
    assert "Show all" not in section
    assert "endorsements" not in section
    assert "Python" in section and "Git" in section


def test_sidebar_marker_detection():
    assert ocr.looks_like_linkedin_sidebar("Who your viewers also viewed")
    assert ocr.looks_like_linkedin_sidebar("Premium\nSamarth Sugandhi")
    assert not ocr.looks_like_linkedin_sidebar("Student at BEC\nPython, React")


# ---------- image tests (real Tesseract OCR) ----------

def _render(main_lines, sidebar_lines, path):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(FONT_PATH, 34)
    img = Image.new("RGB", (1400, 900), "white")
    draw = ImageDraw.Draw(img)
    for i, text in enumerate(main_lines):
        draw.text((60, 60 + i * 70), text, fill="black", font=font)
    for i, text in enumerate(sidebar_lines):
        draw.text((1060, 60 + i * 70), text, fill="black", font=font)
    img.save(path)
    return str(path)


@needs_tesseract
def test_skills_screenshot_counts_main_column_and_ignores_sidebar(tmp_path):
    if not Path(FONT_PATH).exists():
        pytest.skip("DejaVu font not available for rendering the test image")
    path = _render(
        main_lines=["Skills", "Python", "React", "Docker", "Show all 3 skills"],
        sidebar_lines=["Who your viewers also viewed", "Vikas Kannur", "Java & Next.js"],
        path=tmp_path / "skills.png",
    )
    result = ocr.parse_linkedin_screenshot(path, "skills.png")
    names = {s["skill_name"] for s in result["skills"]}
    assert {"python", "react", "docker"} <= names
    assert "java" not in names


@needs_tesseract
def test_profile_without_skills_section_is_rejected(tmp_path):
    if not Path(FONT_PATH).exists():
        pytest.skip("DejaVu font not available for rendering the test image")
    path = _render(
        main_lines=["ADITYA R P", "Student at Basaveshwara Engineering College"],
        sidebar_lines=["Who your viewers also viewed", "Vikas Kannur", "Java & Next.js"],
        path=tmp_path / "profile.png",
    )
    with pytest.raises(ValueError, match="No Skills section found"):
        ocr.parse_linkedin_screenshot(path, "profile.png")


# ---------- connection count -> communication evidence ----------

def test_connection_count_parsed_from_profile_card():
    assert ocr.extract_connection_count("31 connections") == 31
    assert ocr.extract_connection_count("500+ connections") == 500
    assert ocr.extract_connection_count("1,234 connections") == 1234


def test_mutual_connections_are_ignored():
    assert ocr.extract_connection_count("12 mutual connections") is None


def test_connection_confidence_is_weak_and_capped():
    assert ocr.communication_confidence_from_connections(None) is None
    assert ocr.communication_confidence_from_connections(0) is None
    assert ocr.communication_confidence_from_connections(31) == 0.30
    assert ocr.communication_confidence_from_connections(120) == 0.50
    assert ocr.communication_confidence_from_connections(5000) == 0.70


def test_connections_alone_give_communication_without_skills_section():
    result = ocr.parse_linkedin_text("ADITYA R P\n31 connections\nStudent at BEC")
    names = {s["skill_name"]: s for s in result["skills"]}
    assert names["communication"]["confidence"] == 0.30
    assert "31 LinkedIn connections" in names["communication"]["evidence"]


def test_connections_do_not_override_stronger_skills_section_evidence():
    text = "31 connections\nSkills\nCommunication\nTeamwork"
    result = ocr.parse_linkedin_text(text)
    comm = [s for s in result["skills"] if s["skill_name"] == "communication"]
    assert len(comm) == 1
    assert comm[0]["confidence"] > 0.30  # stated skill beats the weak connection signal (0.30)
