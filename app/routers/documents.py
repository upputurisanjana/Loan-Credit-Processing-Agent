"""
Documents router — file upload, doc-type tagging, verification, and PDF report.

Endpoints
---------
POST   /applications/{id}/documents
    Upload one or more supporting documents (PDF, PNG, JPG, etc.).
    Accepts optional doc_type form fields per file.
    Returns metadata list of the stored files.

GET    /applications/{id}/documents
    List all uploaded documents for an application, with doc_type and
    verification status.

GET    /applications/{id}/documents/{filename}
    Download a specific uploaded file.

PATCH  /applications/{id}/documents/{filename}/verify
    Reviewer marks a document as verified or rejected, with optional note.

GET    /applications/{id}/pdf
    Generate and download a PDF report of the application + document list.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

log = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["documents"])

# ---------------------------------------------------------------------------
# Storage — files are kept under ./uploads/<application_id>/
# Metadata (doc_type, verification) is stored in .metadata.json per app.
# ---------------------------------------------------------------------------
_UPLOAD_ROOT = Path("uploads")
_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff",
    "image/webp",
}
_ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".webp"}
_MAX_FILE_SIZE_MB = 20

VALID_DOC_TYPES = {"id", "pay_stub", "bank_statement", "other"}


def _app_upload_dir(application_id: str) -> Path:
    path = _UPLOAD_ROOT / application_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _metadata_path(application_id: str) -> Path:
    return _UPLOAD_ROOT / application_id / ".metadata.json"


def _load_metadata(application_id: str) -> dict:
    """Load the per-application document metadata dict."""
    mp = _metadata_path(application_id)
    if mp.exists():
        try:
            return json.loads(mp.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_metadata(application_id: str, meta: dict) -> None:
    """Persist the per-application document metadata dict."""
    mp = _metadata_path(application_id)
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _list_documents(application_id: str) -> list[dict]:
    """Return metadata for every uploaded file for this application."""
    upload_dir = _UPLOAD_ROOT / application_id
    if not upload_dir.exists():
        return []

    meta = _load_metadata(application_id)
    docs = []
    for f in sorted(upload_dir.iterdir()):
        if f.is_file() and not f.name.startswith("."):
            stat = f.stat()
            file_meta = meta.get(f.name, {})
            docs.append({
                "filename": f.name,
                "size_bytes": stat.st_size,
                "uploaded_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "url": f"/applications/{application_id}/documents/{f.name}",
                "doc_type": file_meta.get("doc_type", "other"),
                "doc_type_label": _doc_type_label(file_meta.get("doc_type", "other")),
                "verification_status": file_meta.get("verification_status", "pending"),
                "verification_note": file_meta.get("verification_note"),
                "verified_by": file_meta.get("verified_by"),
                "verified_at": file_meta.get("verified_at"),
            })
    return docs


def _doc_type_label(doc_type: str) -> str:
    return {
        "id": "Identity Document",
        "pay_stub": "Pay Stub",
        "bank_statement": "Bank Statement",
        "other": "Other Document",
    }.get(doc_type, doc_type.replace("_", " ").title())


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------

class VerifyDocumentRequest(BaseModel):
    verification_status: str  # "verified" | "rejected"
    verified_by: str
    verification_note: Optional[str] = None


# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/{application_id}/documents",
    status_code=status.HTTP_201_CREATED,
    summary="Upload supporting documents for an application",
)
async def upload_documents(
    application_id: str,
    files: List[UploadFile] = File(..., description="One or more document files"),
    doc_types: Optional[str] = Form(
        None,
        description=(
            "Comma-separated doc_type values matching the order of files. "
            "Valid values: id, pay_stub, bank_statement, other. "
            "Defaults to 'other' for any unspecified file."
        ),
    ),
) -> dict:
    """
    Upload supporting documents (pay stubs, ID, bank statements, etc.).

    Accepted types: PDF, PNG, JPEG, TIFF, WEBP.
    Maximum file size: 20 MB per file.

    Optionally pass doc_types as a comma-separated string matching the
    order of files: e.g. "id,pay_stub,bank_statement"

    Returns metadata for all uploaded documents for this application.
    """
    from app.routers.intake import get_store
    store = get_store()
    if application_id not in store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id!r} not found.",
        )

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided.",
        )

    # Parse doc_types string into a list aligned with files
    type_list: list[str] = []
    if doc_types:
        type_list = [t.strip() for t in doc_types.split(",")]
    # Pad with "other" if not enough types provided
    while len(type_list) < len(files):
        type_list.append("other")

    upload_dir = _app_upload_dir(application_id)
    meta = _load_metadata(application_id)
    saved: list[dict] = []

    for idx, upload in enumerate(files):
        # Validate extension
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in _ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"File {upload.filename!r}: unsupported type '{suffix}'. "
                    f"Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}"
                ),
            )

        content = await upload.read()

        max_bytes = _MAX_FILE_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"File {upload.filename!r} is {len(content) / 1024 / 1024:.1f} MB "
                    f"— exceeds {_MAX_FILE_SIZE_MB} MB limit."
                ),
            )

        safe_name = Path(upload.filename or "upload").name
        dest = upload_dir / safe_name

        if dest.exists():
            stem = dest.stem
            ext  = dest.suffix
            counter = 1
            while dest.exists():
                dest = upload_dir / f"{stem}_{counter}{ext}"
                counter += 1

        dest.write_bytes(content)

        # Resolve doc_type — clamp to valid values
        raw_type = type_list[idx] if idx < len(type_list) else "other"
        doc_type = raw_type if raw_type in VALID_DOC_TYPES else "other"

        # Store metadata for this file
        meta[dest.name] = {
            "doc_type": doc_type,
            "doc_type_label": _doc_type_label(doc_type),
            "verification_status": "pending",
            "verification_note": None,
            "verified_by": None,
            "verified_at": None,
        }

        log.info(
            "documents: saved %s for app_id=%s (%d bytes) doc_type=%s",
            dest.name, application_id, len(content), doc_type,
        )

        saved.append({
            "filename": dest.name,
            "size_bytes": len(content),
            "url": f"/applications/{application_id}/documents/{dest.name}",
            "doc_type": doc_type,
            "doc_type_label": _doc_type_label(doc_type),
        })

    _save_metadata(application_id, meta)

    return {
        "application_id": application_id,
        "uploaded": saved,
        "all_documents": _list_documents(application_id),
    }


# ---------------------------------------------------------------------------
# List documents
# ---------------------------------------------------------------------------

@router.get(
    "/{application_id}/documents",
    summary="List uploaded documents for an application",
)
async def list_documents(application_id: str) -> dict:
    """Return metadata for all documents uploaded for this application."""
    from app.routers.intake import get_store
    store = get_store()
    if application_id not in store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id!r} not found.",
        )

    return {
        "application_id": application_id,
        "documents": _list_documents(application_id),
    }


# ---------------------------------------------------------------------------
# Download a single file
# ---------------------------------------------------------------------------

@router.get(
    "/{application_id}/documents/{filename}",
    summary="Download a specific uploaded document",
)
async def download_document(application_id: str, filename: str) -> FileResponse:
    """Download a previously uploaded document by filename."""
    safe_name = Path(filename).name
    file_path = _UPLOAD_ROOT / application_id / safe_name

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {filename!r} not found for application {application_id!r}.",
        )

    return FileResponse(
        path=str(file_path),
        filename=safe_name,
        media_type="application/octet-stream",
    )


# ---------------------------------------------------------------------------
# Document verification — reviewer marks a document as verified/rejected
# ---------------------------------------------------------------------------

@router.patch(
    "/{application_id}/documents/{filename}/verify",
    summary="Reviewer verifies or rejects an uploaded document",
    status_code=status.HTTP_200_OK,
)
async def verify_document(
    application_id: str,
    filename: str,
    body: VerifyDocumentRequest,
) -> dict:
    """
    Reviewer marks a document as 'verified' (correct document type, legible)
    or 'rejected' (wrong document, unreadable, or suspicious).

    verification_status: 'verified' | 'rejected'
    verified_by: reviewer ID
    verification_note: optional reason (required on rejection)

    Returns updated document metadata.
    """
    from app.routers.intake import get_store
    store = get_store()
    if application_id not in store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id!r} not found.",
        )

    if body.verification_status not in ("verified", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="verification_status must be 'verified' or 'rejected'.",
        )

    if body.verification_status == "rejected" and not body.verification_note:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="verification_note is required when rejecting a document.",
        )

    safe_name = Path(filename).name
    file_path = _UPLOAD_ROOT / application_id / safe_name
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {filename!r} not found for application {application_id!r}.",
        )

    meta = _load_metadata(application_id)
    if safe_name not in meta:
        meta[safe_name] = {"doc_type": "other", "doc_type_label": "Other Document"}

    meta[safe_name].update({
        "verification_status": body.verification_status,
        "verification_note": body.verification_note,
        "verified_by": body.verified_by,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    })
    _save_metadata(application_id, meta)

    log.info(
        "documents: %s verified as %s by %s for app_id=%s",
        safe_name, body.verification_status, body.verified_by, application_id,
    )

    return {
        "application_id": application_id,
        "filename": safe_name,
        **meta[safe_name],
    }


# ---------------------------------------------------------------------------
# PDF report generation
# ---------------------------------------------------------------------------

def _generate_pdf(application_id: str, record) -> bytes:
    """Generate a PDF report for the application and attached documents."""
    try:
        from fpdf import FPDF
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF generation requires fpdf2. Run: pip install fpdf2",
        )

    from app.models.decision import DecisionRecord

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Cover / header ──────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_fill_color(18, 33, 58)
    pdf.set_text_color(255, 255, 255)
    pdf.rect(0, 0, 210, 28, "F")
    pdf.set_xy(10, 8)
    pdf.cell(0, 12, "Credit Application Report", ln=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_y(34)

    def section_header(title: str):
        pdf.set_fill_color(240, 243, 248)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(60, 80, 120)
        pdf.cell(0, 8, f"  {title}", ln=True, fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    def kv(label: str, value: str, indent: int = 10):
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_x(indent)
        pdf.cell(55, 6, label + ":", ln=False)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 6, str(value))

    # ── Application summary ─────────────────────────────────────────────
    section_header("Application Summary")
    kv("Application ID", application_id)

    if isinstance(record, DecisionRecord):
        kv("Policy Version",     record.policy_version)
        kv("Submitted",         record.created_at.strftime("%Y-%m-%d %H:%M UTC"))
        kv("Status",            record.status.replace("_", " ").title())
        kv("Human Decision",    record.human_decision or "Pending")
        if record.human_reviewer:
            kv("Reviewer",      record.human_reviewer)
        if record.decided_at:
            kv("Decided At",    record.decided_at.strftime("%Y-%m-%d %H:%M UTC"))

        # Applicant details
        if record.applicant_name:
            pdf.ln(4)
            section_header("Applicant Details")
            kv("Name",           record.applicant_name)
            kv("Address",        record.applicant_address)
            kv("Loan Requested", f"£{record.loan_amount_requested:,.2f}")
            if record.applicant_notes:
                kv("Notes",      record.applicant_notes)

        pdf.ln(4)
        section_header("Score Breakdown")
        sb = record.score_breakdown
        kv("Composite Score",       f"{sb.composite_score * 100:.1f} / 100")
        kv("Band",                  sb.band.upper())
        kv("DTI Ratio",             f"{sb.dti_ratio * 100:.1f}%")
        kv("DTI Sub-score",         f"{sb.dti_subscore * 100:.1f}")
        kv("Credit History",        f"{sb.credit_history_subscore * 100:.1f}")
        kv("Income Stability",      f"{sb.income_stability_subscore * 100:.1f}")

        pdf.ln(4)
        section_header("Agent Recommendation")
        kv("Recommendation", record.agent_recommendation.upper())
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(10)
        pdf.multi_cell(0, 5, record.rationale or "—")

        # Use approved notice text if available; fall back to draft
        notice_text = record.approved_notice_text or record.adverse_action_draft
        if notice_text:
            pdf.ln(4)
            notice_label = (
                "Adverse Action Notice (Approved by Reviewer)"
                if record.approved_notice_text
                else "Adverse Action Notice (Draft — not yet approved)"
            )
            section_header(notice_label)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_x(10)
            pdf.multi_cell(0, 5, notice_text)

        if sb.clause_citations:
            pdf.ln(4)
            section_header("Policy Clauses Cited")
            for citation in sb.clause_citations:
                kv(citation.clause_id, citation.clause_text)
    else:
        kv("Status", str(record.get("status", "unknown")))
        if record.get("message"):
            kv("Message", str(record.get("message")))

    # ── Uploaded documents list ─────────────────────────────────────────
    docs = _list_documents(application_id)
    pdf.ln(4)
    section_header("Uploaded Documents")
    if docs:
        pdf.set_font("Helvetica", "", 9)
        for i, doc in enumerate(docs, 1):
            size_kb  = doc["size_bytes"] / 1024
            uploaded = doc.get("uploaded_at", "")[:19].replace("T", " ")
            v_status = doc.get("verification_status", "pending")
            v_icon   = "✓" if v_status == "verified" else "✗" if v_status == "rejected" else "?"
            pdf.set_x(10)
            pdf.cell(
                0, 6,
                f"  {i}. [{v_icon}] {doc['doc_type_label']} — {doc['filename']}"
                f"  ({size_kb:.1f} KB)  —  {uploaded} UTC",
                ln=True,
            )
    else:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_x(10)
        pdf.cell(0, 6, "  No documents uploaded.", ln=True)

    # ── Footer ──────────────────────────────────────────────────────────
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(
        0, 5,
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} — "
        "Credit Decisioning Agent — Human-gated pipeline",
        align="C",
    )

    return bytes(pdf.output())


@router.get(
    "/{application_id}/pdf",
    summary="Generate a PDF report of the application and uploaded documents",
    response_class=StreamingResponse,
)
async def generate_pdf(application_id: str) -> StreamingResponse:
    """
    Generate a structured PDF report containing:
    - Application summary and scores
    - Applicant details
    - Agent recommendation and rationale
    - Adverse action notice (approved version if available)
    - Policy clause citations
    - List of uploaded supporting documents with verification status

    Returns the PDF as a downloadable file.
    """
    from app.routers.intake import get_store
    store = get_store()
    record = store.get(application_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id!r} not found.",
        )

    pdf_bytes = _generate_pdf(application_id, record)
    filename  = f"application_{application_id}.pdf"

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
