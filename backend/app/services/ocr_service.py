"""
Document ingestion for LinkedIn screenshots and certificates.

Handles two input shapes:
  - Images (png/jpg/jpeg/webp): preprocessed (upscaled, grayscale,
    contrast-boosted) then run through Tesseract OCR. Real screenshots
    are lower-resolution and more compressed than test images, so the
    preprocessing step matters a lot for accuracy.
  - PDFs: text is extracted directly first (no OCR needed at all — this
    is the path for LinkedIn's own "Save to PDF" profile export, or any
    text-based certificate PDF). If a PDF turns out to be a scanned
    image with no extractable text, we fall back to rasterizing each
    page and OCRing it.

LinkedIn is special-cased: only the Skills section counts.
  A LinkedIn screenshot also shows a right-hand sidebar ("Who your
  viewers also viewed", other people's headlines). Matching the whole
  screenshot picked up other people's skills and produced false,
  heavily weighted LinkedIn evidence. So for LinkedIn uploads we:
    1. If the screenshot visibly has a sidebar, OCR only the main
       (left) column, by word position, so sidebar text is dropped.
    2. Match skills only inside the block that starts at a "Skills"
       heading and ends at the next profile section heading.
  If there is no Skills section at all, the upload is rejected with a
  clear message instead of guessing from the rest of the page.

Certificates are parsed as before: the whole document is matched.

Tesseract is a system binary, not a Python package — pytesseract just
wraps it. If it isn't installed, every OCR call raises
TesseractNotFoundError. We catch that everywhere and turn it into a
clear, actionable message rather than a stack trace, and PDF text
extraction works either way since it doesn't touch Tesseract at all.
"""
import io
import os
import re
import warnings
from PIL import Image, ImageOps
import pytesseract
from pytesseract import Output

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    import pymupdf as fitz  # PyMuPDF; new import name, old one is deprecated

from app.services.resume_parser import extract_skills_from_text, extract_text_from_pdf

MIN_TEXT_LENGTH_FOR_DIRECT_PDF = 40  # below this, assume the PDF is a scanned image
PDF_RENDER_DPI = 200

# On Linux/Mac, `tesseract` is usually on PATH once installed and pytesseract
# finds it automatically. On Windows it's frequently NOT on PATH even after
# installing — set TESSERACT_CMD to the full path to tesseract.exe and we'll
# point pytesseract at it directly instead of relying on PATH.
_tesseract_cmd = os.getenv("TESSERACT_CMD")
if _tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd

TESSERACT_MISSING_MESSAGE = (
    "Tesseract OCR isn't installed (or isn't on PATH) on this machine, so image "
    "uploads (PNG/JPG) can't be read yet. Install it, then restart the backend:\n"
    "  Linux:   sudo apt-get install tesseract-ocr\n"
    "  Mac:     brew install tesseract\n"
    "  Windows: download the installer from "
    "https://github.com/UB-Mannheim/tesseract/wiki, then set TESSERACT_CMD in "
    "backend/.env to the installed tesseract.exe path, e.g. "
    "TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe\n"
    "In the meantime, PDF uploads work without it."
)

# ---------------------------------------------------------------------------
# LinkedIn: sidebar handling and Skills-section extraction
# ---------------------------------------------------------------------------

# The main profile card on LinkedIn's desktop layout ends at roughly 70% of
# the screenshot width; the sidebar starts at roughly 72%. Words that start
# to the right of this fraction are treated as sidebar.
LINKEDIN_MAIN_COLUMN_MAX_X = 0.71

# Phrases that only appear in LinkedIn's sidebar. If one of them is found in
# the OCR text, the screenshot has a sidebar and the column filter is applied.
LINKEDIN_SIDEBAR_MARKERS = (
    "viewers also viewed",
    "people also viewed",
    "also viewed",
    "profile language",
    "public profile",
    "suggested for you",
    "who your viewers",
    "premium",
)

SKILLS_HEADING_RE = re.compile(r"^\s*(top\s+)?skills\W*$", re.IGNORECASE)

# Any of these headings ends the Skills block.
NEXT_SECTION_HEADING_RE = re.compile(
    r"^\s*(experience|education|licenses\s*(&|and)\s*certifications|certifications|"
    r"courses|projects|honors\s*(&|and)\s*awards|honors|awards|"
    r"volunteer(ing)?(\s+experience)?|languages|recommendations|interests|"
    r"publications|activity|about|featured|organizations|patents|test scores|causes)\W*$",
    re.IGNORECASE,
)

# Lines inside the Skills block that are UI text, not skill names.
SKILL_NOISE_RE = re.compile(
    r"endorse|show all|see all|show more|\bpresent\b|\d{4}",
    re.IGNORECASE,
)

NO_SKILLS_SECTION_MESSAGE = (
    "No Skills section found, and no connection count either, in this LinkedIn "
    "upload. Screenshot the Skills section, or screenshot the profile card that "
    "shows your connection count, or export your profile as a PDF from LinkedIn. "
    "The sidebar is ignored on purpose, so other people's names and headlines "
    "are not counted as your skills."
)

# Connection count -> communication evidence. A connection count is a weak
# proxy for communication (it measures networking reach, not how well someone
# communicates), so the confidence is deliberately low and capped.
COMMUNICATION_FROM_CONNECTIONS = [
    (500, 0.70),
    (300, 0.60),
    (100, 0.50),
    (50, 0.40),
    (1, 0.30),
]
CONNECTIONS_RE = re.compile(r"(\d[\d,]*)\s*\+?\s*connections", re.IGNORECASE)


def extract_connection_count(text: str) -> int | None:
    """Find the connection count on the profile card, e.g. '31 connections'
    or '500+ connections'. 'Mutual connections' lines are ignored."""
    for line in text.splitlines():
        if re.search(r"mutual", line, re.IGNORECASE):
            continue
        match = CONNECTIONS_RE.search(line)
        if match:
            return int(match.group(1).replace(",", ""))
    return None


def communication_confidence_from_connections(count: int | None) -> float | None:
    if not count or count < 1:
        return None
    for threshold, confidence in COMMUNICATION_FROM_CONNECTIONS:
        if count >= threshold:
            return confidence
    return None


def extract_skills_section(text: str) -> tuple[bool, str]:
    """Return (found, section_text).

    section_text is the set of lines after the first line that is a Skills
    heading, up to the next profile section heading (or the end of the text).
    UI noise such as "Show all 12 skills" or endorsement counts is dropped.
    """
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if SKILLS_HEADING_RE.match(line):
            start = i + 1
            break
    if start is None:
        return False, ""

    section_lines = []
    for line in lines[start:]:
        if NEXT_SECTION_HEADING_RE.match(line):
            break
        if line.strip() and not SKILL_NOISE_RE.search(line):
            section_lines.append(line)
    return True, "\n".join(section_lines)


def looks_like_linkedin_sidebar(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in LINKEDIN_SIDEBAR_MARKERS)


def parse_linkedin_text(text: str) -> dict:
    """Skills come only from the Skills section. Communication evidence also
    comes from the connection count on the profile card. Raises ValueError if
    the upload has neither, so nothing outside those two places is counted."""
    found, section = extract_skills_section(text)
    skills = extract_skills_from_text(section) if found else []

    connections = extract_connection_count(text)
    comm_confidence = communication_confidence_from_connections(connections)

    if comm_confidence is not None:
        existing = next((s for s in skills if s["skill_name"] == "communication"), None)
        if existing is None:
            skills.append({
                "skill_name": "communication",
                "category": "Soft Skill",
                "confidence": comm_confidence,
                "evidence": f"{connections} LinkedIn connections (weak signal)",
            })
        else:
            existing["confidence"] = max(existing["confidence"], comm_confidence)

    if not found and comm_confidence is None:
        raise ValueError(NO_SKILLS_SECTION_MESSAGE)

    return {
        "raw_text": text,
        "skills": skills,
        "section_text": section,
    }


# ---------------------------------------------------------------------------
# Image preprocessing and OCR
# ---------------------------------------------------------------------------


def _preprocess_image(image: Image.Image) -> Image.Image:
    """Upscale + grayscale + autocontrast. Real screenshots are often
    small and slightly compressed, which tanks raw OCR accuracy —
    Tesseract does noticeably better on larger, higher-contrast input."""
    image = image.convert("L")  # grayscale
    if max(image.size) < 1600:
        scale = 1600 / max(image.size)
        new_size = (int(image.width * scale), int(image.height * scale))
        image = image.resize(new_size, Image.LANCZOS)
    image = ImageOps.autocontrast(image, cutoff=1)
    return image


def _ocr_image(image: Image.Image) -> str:
    try:
        processed = _preprocess_image(image)
        return pytesseract.image_to_string(processed)
    except pytesseract.TesseractNotFoundError:
        raise ValueError(TESSERACT_MISSING_MESSAGE)


def _ocr_main_column(image: Image.Image) -> str:
    """OCR only words in the main (left) column, using word positions.
    Words are grouped back into lines in the order Tesseract reads them."""
    try:
        processed = _preprocess_image(image)
        data = pytesseract.image_to_data(processed, output_type=Output.DICT)
    except pytesseract.TesseractNotFoundError:
        raise ValueError(TESSERACT_MISSING_MESSAGE)

    cutoff = processed.width * LINKEDIN_MAIN_COLUMN_MAX_X
    lines: dict[tuple, list[str]] = {}
    for i, word in enumerate(data["text"]):
        if not word.strip() or data["left"][i] > cutoff:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(word)
    return "\n".join(" ".join(words) for words in lines.values())


def _linkedin_image_text(image: Image.Image) -> str:
    full_text = _ocr_image(image)
    if looks_like_linkedin_sidebar(full_text):
        return _ocr_main_column(image)
    return full_text


# ---------------------------------------------------------------------------
# PDFs
# ---------------------------------------------------------------------------


def extract_text_from_image(image_path: str) -> str:
    image = Image.open(image_path)
    return _ocr_image(image)


def extract_text_from_pdf_with_ocr_fallback(file_path: str) -> str:
    """Try direct text extraction first (fast, no OCR needed). If the
    PDF has little to no extractable text — typical of a scanned
    certificate — rasterize each page and OCR it instead."""
    direct_text = extract_text_from_pdf(file_path)
    if len(direct_text.strip()) >= MIN_TEXT_LENGTH_FOR_DIRECT_PDF:
        return direct_text

    # scanned / image-based PDF: render each page and OCR it
    text_chunks = []
    doc = fitz.open(file_path)
    try:
        zoom = PDF_RENDER_DPI / 72
        matrix = fitz.Matrix(zoom, zoom)
        for page in doc:
            pix = page.get_pixmap(matrix=matrix)
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            text_chunks.append(_ocr_image(image))
    finally:
        doc.close()
    return "\n".join(text_chunks)


def _is_pdf(filename: str) -> bool:
    return filename.lower().endswith(".pdf")


# ---------------------------------------------------------------------------
# Public entry points used by the routers
# ---------------------------------------------------------------------------


_OCR_TERM_FIXES = [
    (re.compile(r"\bAl\b"), "AI"),
    (re.compile(r"\bAi\b"), "AI"),
    (re.compile(r"\bGen Al\b", re.IGNORECASE), "Gen AI"),
]


def _fix_ocr_terms(text: str) -> str:
    for pattern, replacement in _OCR_TERM_FIXES:
        text = pattern.sub(replacement, text)
    return text


def parse_document(file_path: str, filename: str, boost_confidence: bool = False) -> dict:
    """Entry point for certificates — routes to PDF or image handling based
    on the filename, extracts text, then matches skills against the taxonomy
    across the whole document."""
    if _is_pdf(filename):
        raw_text = extract_text_from_pdf_with_ocr_fallback(file_path)
    else:
        raw_text = extract_text_from_image(file_path)

    # OCR often reads capital I as lowercase l ("AI" -> "Al"), which hides skills like
    # "Generative AI". Fix only the forms that are unambiguous in a skills context.
    skills = extract_skills_from_text(_fix_ocr_terms(raw_text))

    if boost_confidence:
        # A certificate naming a skill is stronger evidence than a
        # resume bullet point mentioning it in passing.
        for skill in skills:
            skill["confidence"] = min(0.95, skill["confidence"] + 0.2)
            skill["evidence"] = (
                f"Certificate: {skill['evidence']}" if skill["evidence"] else "Listed on certificate"
            )

    return {"raw_text": raw_text, "skills": skills}


def parse_linkedin_screenshot(file_path: str, filename: str = "") -> dict:
    """LinkedIn screenshot or 'Save to PDF' export. Counts only the Skills
    section, and ignores the sidebar. Raises ValueError if there is no
    Skills section."""
    name = filename or file_path
    if _is_pdf(name):
        text = extract_text_from_pdf_with_ocr_fallback(file_path)
    else:
        text = _linkedin_image_text(Image.open(file_path))
    return parse_linkedin_text(text)


def parse_certificate(file_path: str, filename: str = "") -> dict:
    return parse_document(file_path, filename or file_path, boost_confidence=True)
