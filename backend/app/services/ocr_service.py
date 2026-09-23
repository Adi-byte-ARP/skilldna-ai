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

Tesseract is a system binary, not a Python package — pytesseract just
wraps it. If it isn't installed, every OCR call raises
TesseractNotFoundError. We catch that everywhere and turn it into a
clear, actionable message rather than a stack trace, and PDF text
extraction works either way since it doesn't touch Tesseract at all.
"""
import io
import os
import warnings
from PIL import Image, ImageOps
import pytesseract

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


def parse_document(file_path: str, filename: str, boost_confidence: bool = False) -> dict:
    """Unified entry point for LinkedIn screenshots and certificates —
    routes to PDF or image handling based on the filename, extracts
    text, then matches skills against the taxonomy."""
    if _is_pdf(filename):
        raw_text = extract_text_from_pdf_with_ocr_fallback(file_path)
    else:
        raw_text = extract_text_from_image(file_path)

    skills = extract_skills_from_text(raw_text)

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
    return parse_document(file_path, filename or file_path, boost_confidence=False)


def parse_certificate(file_path: str, filename: str = "") -> dict:
    return parse_document(file_path, filename or file_path, boost_confidence=True)
