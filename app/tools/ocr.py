"""
app/tools/ocr.py — pytesseract OCR on uploaded PDF/image files.

Reads the actual bytes from uploads/{app_id}/{filename} and extracts
text using pytesseract (Tesseract-OCR wrapper).

For PDFs: uses pdf2image to convert each page to a PIL Image, then
runs pytesseract on each page and joins the results.

For images (PNG/JPG/TIFF): runs pytesseract directly.

Returns (text, confidence) where confidence is the mean word-level
confidence from pytesseract (0.0–1.0), or None if pytesseract is
unavailable or the file cannot be read.

All content returned is UNTRUSTED INPUT — callers must treat it as
applicant-supplied data and wrap it in <applicant_data> tags before
passing to any LLM.
"""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

_UPLOAD_ROOT = Path("uploads")


def ocr_file(app_id: str, filename: str) -> tuple[str, float | None]:
    """
    OCR a single uploaded file and return (text, confidence).

    Parameters
    ----------
    app_id    : application ID, used to locate uploads/{app_id}/{filename}
    filename  : the filename as stored under the upload directory

    Returns
    -------
    (text, confidence)
        text       — extracted text, or "" on failure
        confidence — mean word confidence 0.0–1.0, or None if unavailable
    """
    file_path = _UPLOAD_ROOT / app_id / Path(filename).name

    if not file_path.exists():
        log.warning("ocr: file not found: %s", file_path)
        return "", None

    suffix = file_path.suffix.lower()

    try:
        if suffix == ".pdf":
            return _ocr_pdf(file_path)
        else:
            return _ocr_image(file_path)
    except Exception as exc:  # noqa: BLE001
        log.warning("ocr: failed on %s — %s", file_path, exc)
        return "", None


def _ocr_image(path: Path) -> tuple[str, float | None]:
    """OCR a single image file."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        log.warning("ocr: pytesseract or Pillow not installed — skipping OCR")
        return "", None

    image = Image.open(path)
    # Get both text and confidence data
    try:
        data = pytesseract.image_to_data(
            image, output_type=pytesseract.Output.DICT, lang="eng"
        )
        # Filter words with confidence > 0
        confidences = [int(c) for c in data["conf"] if int(c) > 0]
        mean_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else None

        text = pytesseract.image_to_string(image, lang="eng").strip()
        log.info("ocr: %s — %d chars, confidence=%.2f",
                 path.name, len(text), mean_conf if mean_conf is not None else 0)
        return text, mean_conf
    except Exception as exc:
        log.warning("ocr: pytesseract error on %s — %s", path.name, exc)
        return "", None


def _ocr_pdf(path: Path) -> tuple[str, float | None]:
    """OCR a PDF by converting each page to an image first."""
    try:
        from pdf2image import convert_from_path
    except ImportError:
        log.warning("ocr: pdf2image not installed — attempting direct pytesseract on PDF")
        # Fallback: try pytesseract directly (works if Tesseract has PDF support)
        return _ocr_image(path)

    try:
        pages = convert_from_path(str(path), dpi=200)
    except Exception as exc:
        log.warning("ocr: pdf2image failed on %s — %s", path.name, exc)
        # pdf2image needs poppler; fall back gracefully
        return _ocr_direct_pdf(path)

    all_text: list[str] = []
    all_conf: list[float] = []

    for i, page_image in enumerate(pages):
        text, conf = _ocr_image_obj(page_image, f"{path.name} p{i+1}")
        if text:
            all_text.append(text)
        if conf is not None:
            all_conf.append(conf)

    combined_text = "\n\n".join(all_text).strip()
    mean_conf = (sum(all_conf) / len(all_conf)) if all_conf else None
    return combined_text, mean_conf


def _ocr_image_obj(image, label: str) -> tuple[str, float | None]:
    """OCR a PIL Image object (used by _ocr_pdf)."""
    try:
        import pytesseract
    except ImportError:
        return "", None

    try:
        data = pytesseract.image_to_data(
            image, output_type=pytesseract.Output.DICT, lang="eng"
        )
        confidences = [int(c) for c in data["conf"] if int(c) > 0]
        mean_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else None
        text = pytesseract.image_to_string(image, lang="eng").strip()
        return text, mean_conf
    except Exception as exc:
        log.warning("ocr: error on %s — %s", label, exc)
        return "", None


def _ocr_direct_pdf(path: Path) -> tuple[str, float | None]:
    """Last-resort: try pytesseract directly on the PDF (requires Tesseract PDF support)."""
    try:
        import pytesseract
        from PIL import Image
        image = Image.open(path)
        text = pytesseract.image_to_string(image, lang="eng").strip()
        return text, None
    except Exception as exc:
        log.warning("ocr: direct PDF OCR failed on %s — %s", path.name, exc)
        return "", None


def ocr_application_documents(app_id: str, documents: list) -> list:
    """
    OCR all uploaded documents for an application, replacing any
    placeholder extracted_text with real OCR output.

    Parameters
    ----------
    app_id    : application ID
    documents : list of UploadedDocument objects

    Returns
    -------
    Updated list of UploadedDocument objects with ocr'd extracted_text
    and updated ocr_confidence. Documents with no uploaded file are
    returned unchanged.
    """
    updated = []
    for doc in documents:
        filename = Path(doc.file_path).name if doc.file_path else None
        if not filename:
            updated.append(doc)
            continue

        file_path = _UPLOAD_ROOT / app_id / filename
        if not file_path.exists():
            # No real file uploaded — keep whatever extracted_text was provided
            log.info("ocr: no file found for %s/%s — using submitted text", app_id, filename)
            updated.append(doc)
            continue

        log.info("ocr: running OCR on %s/%s", app_id, filename)
        text, confidence = ocr_file(app_id, filename)

        if text:
            # Replace applicant-supplied text with real OCR output
            updated_doc = doc.model_copy(update={
                "extracted_text": text,
                "ocr_confidence": round(confidence, 3) if confidence is not None else doc.ocr_confidence,
            })
            log.info("ocr: %s — extracted %d chars (confidence=%.2f)",
                     filename, len(text), confidence if confidence else 0)
        else:
            # OCR failed or returned nothing — keep submitted text but flag low confidence
            log.warning("ocr: empty result for %s — keeping submitted text", filename)
            updated_doc = doc.model_copy(update={
                "ocr_confidence": 0.0,  # signals to VERIFY that this needs manual review
            })

        updated.append(updated_doc)

    return updated
