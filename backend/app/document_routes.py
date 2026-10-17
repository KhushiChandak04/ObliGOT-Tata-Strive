"""Document intake: upload MOU/addendum PDFs, inspect them page by page, and track their status.

Upload never extracts or approves anything. A document becomes operational only after review (later phases).
"""
import hashlib
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from app import document_storage
from app.config import settings
from app.documents import DocumentStatus, SourceDocument
from app.pdf_inspect import PdfInspectionError, inspect_pdf, looks_like_pdf
from app.repository import get_record, list_records, put_record
from app.reviews import actor, log_activity, now_iso

router = APIRouter(tags=["documents"])

DOCUMENT_KINDS = ("mou", "addendum")


def _form_text(form, name: str) -> str | None:
    value = form.get(name)
    if value is None or hasattr(value, "read"):
        return None
    return str(value).strip() or None


def _resolve_links(partner_id: str | None, agreement_id: str | None) -> tuple[str | None, str | None]:
    """Linked records must exist; an agreement must belong to the given partner (or supplies the partner)."""
    if agreement_id:
        agreement = get_record("agreements", agreement_id)
        if not agreement:
            raise HTTPException(status_code=404, detail="Agreement not found")
        if partner_id and agreement.get("partner_id") != partner_id:
            raise HTTPException(status_code=422, detail="Agreement belongs to a different partner")
        partner_id = partner_id or agreement.get("partner_id")
    if partner_id and not get_record("partners", partner_id):
        raise HTTPException(status_code=404, detail="Partner not found")
    return partner_id, agreement_id


@router.post("/documents", response_model=SourceDocument, status_code=201,
             responses={409: {"description": "The same file was already uploaded"},
                        413: {"description": "File too large"},
                        415: {"description": "Not a PDF"}})
async def upload_document(request: Request) -> dict:
    """Upload a PDF (multipart: file, kind = mou | addendum, optional partner_id, agreement_id) and inspect it."""
    if "multipart/form-data" not in request.headers.get("content-type", "").lower():
        raise HTTPException(status_code=415, detail="Send the PDF as multipart/form-data")
    form = await request.form()
    kind = _form_text(form, "kind")
    if kind not in DOCUMENT_KINDS:
        raise HTTPException(status_code=422, detail="kind must be mou or addendum")
    partner_id, agreement_id = _resolve_links(_form_text(form, "partner_id"), _form_text(form, "agreement_id"))
    upload = form.get("file")
    if upload is None or not hasattr(upload, "read"):
        raise HTTPException(status_code=422, detail="A file field is required")
    limit = settings.max_document_mb * 1024 * 1024
    raw = await upload.read(limit + 1)
    if not raw:
        raise HTTPException(status_code=422, detail="The file is empty")
    if len(raw) > limit:
        raise HTTPException(status_code=413, detail=f"The file is larger than the {settings.max_document_mb} MB limit")
    if not looks_like_pdf(raw):
        raise HTTPException(status_code=415, detail="Only PDF files are accepted")

    digest = hashlib.sha256(raw).hexdigest()
    duplicate = next((d for d in list_records("documents")
                      if d.get("sha256") == digest and d.get("status") != "failed"), None)
    if duplicate:
        raise HTTPException(status_code=409, detail={
            "message": "This file was already uploaded", "document_id": duplicate["id"]})

    document_id = f"doc-{uuid4().hex[:12]}"
    who = actor(request)
    record = {
        "filename": document_storage.safe_display_name(getattr(upload, "filename", None)),
        "kind": kind, "partner_id": partner_id, "agreement_id": agreement_id,
        "uploaded_at": now_iso(), "uploaded_by": who, "size_bytes": len(raw), "sha256": digest,
        "pages": [], "warnings": [], "error": None, "storage_ref": None, "source_label": "user",
    }
    try:
        inspection = await run_in_threadpool(inspect_pdf, raw, settings.max_document_pages)
    except PdfInspectionError as exc:
        # Kept as a failed record so the reason is visible; the unreadable file itself is not stored.
        record.update(status="failed", error=str(exc))
    else:
        record["storage_ref"] = await run_in_threadpool(document_storage.save_pdf, document_id, raw)
        record.update(page_count=inspection.page_count, pages=[p.model_dump() for p in inspection.pages])
        low = inspection.low_text_pages
        if len(low) == inspection.page_count:
            record["status"] = "blocked"
            record["warnings"].append(
                "No page has embedded text (likely a scanned PDF). OCR is not available yet; the document needs manual review.")
        else:
            record["status"] = "uploaded"
            if low:
                many = len(low) > 1
                record["warnings"].append(
                    f"Page{'s' if many else ''} {', '.join(map(str, low))} {'have' if many else 'has'} little or no embedded "
                    f"text (scanned, blank, or image-only). Review {'them' if many else 'it'} manually; "
                    f"{'they are' if many else 'it is'} not extracted.")
        if kind == "addendum" and not agreement_id:
            record["warnings"].append("Choose the agreement this addendum amends before its changes can be reviewed.")
    SourceDocument(id=document_id, **record)  # validate before saving
    saved = put_record("documents", record, document_id)
    outcome = "could not be read" if record["status"] == "failed" else f"inspected ({record.get('page_count')} pages)"
    log_activity(actor_name=who, event="document_uploaded", summary=f"Uploaded “{record['filename']}” — {outcome}",
                 entity_type="document", entity_id=document_id, partner_id=partner_id,
                 details={"kind": kind, "status": record["status"]})
    return saved


@router.get("/documents", response_model=list[SourceDocument])
def list_documents(partner_id: str | None = None, agreement_id: str | None = None,
                   status: DocumentStatus | None = None, kind: Literal["mou", "addendum"] | None = None) -> list[dict]:
    documents = list_records("documents")
    filters = {"partner_id": partner_id, "agreement_id": agreement_id, "status": status, "kind": kind}
    for field, value in filters.items():
        if value:
            documents = [d for d in documents if d.get(field) == value]
    return sorted(documents, key=lambda d: (d.get("uploaded_at") or "", d["id"]), reverse=True)


@router.get("/documents/{document_id}", response_model=SourceDocument)
def get_document(document_id: str) -> dict:
    document = get_record("documents", document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document
