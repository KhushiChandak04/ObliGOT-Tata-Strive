"""Document intake: upload MOU/addendum PDFs, inspect them page by page, and track their status.

Upload never extracts or approves anything. A document becomes operational only after review (later phases).
"""
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, Response
from fastapi.concurrency import run_in_threadpool

from app import document_storage
from app.config import settings
from app.documents import DocumentStatus, ExtractionRun, PageReading, SourceDocument
from app.extraction import ExtractionFailed, Generate, build_prompt, build_proposals, chunk_pages, gemini_generate, parse_chunk
from app.page_reading import batches, gemini_read_pages, parse_batch, render_page
from app.pdf_inspect import PdfInspectionError, inspect_pdf, looks_like_pdf
from app.repository import delete_record, get_record, list_records, patch_record, put_record
from app.reviews import actor, log_activity, now_iso

router = APIRouter(tags=["documents"])
logger = logging.getLogger("obligot.documents")

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
        if low and settings.gemini_api_key:
            # Scanned pages are read from page images during extraction (AI transcription, reviewed by a person).
            record["status"] = "uploaded"
            scope = "All pages are" if len(low) == inspection.page_count else f"Page{'s' if len(low) > 1 else ''} {', '.join(map(str, low))} {'are' if len(low) > 1 else 'is'}"
            record["warnings"].append(
                f"{scope} scanned images without a text layer. During extraction Gemini reads them from the page images; "
                "that reading is an AI transcription, so compare extracted values with the page images when reviewing.")
        elif len(low) == inspection.page_count:
            record["status"] = "blocked"
            record["warnings"].append(
                "No page has embedded text (likely a scanned PDF). Gemini is not configured to read page images; the document needs manual review.")
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


# ---- extraction ----

PROPOSAL_COLLECTIONS = ("extracted_fields", "clauses", "financial_terms", "obligations", "programme_scope", "review_issues")
# An extraction still "running" after this long is assumed to have died with the process and may be restarted.
STALE_EXTRACTION = timedelta(minutes=15)


def _proposals_for(document_id: str) -> dict[str, list[dict]]:
    return {c: sorted((r for r in list_records(c) if r.get("document_id") == document_id), key=lambda r: r["id"])
            for c in PROPOSAL_COLLECTIONS}


def _check_can_extract(document: dict) -> None:
    status = document["status"]
    if status == "extracting":
        started = (document.get("extraction") or {}).get("started_at")
        if started and datetime.now(timezone.utc) - datetime.fromisoformat(started) < STALE_EXTRACTION:
            raise HTTPException(status_code=409, detail="Extraction is already running for this document")
    if status == "approved":
        raise HTTPException(status_code=409, detail="The document is approved; its values can no longer be re-extracted")
    if not document.get("storage_ref"):
        raise HTTPException(status_code=409, detail="The file could not be read when uploaded; upload a readable copy")
    if all(p["text_status"] == "low_text" for p in document.get("pages", [])) and not settings.gemini_api_key:
        raise HTTPException(status_code=409, detail="No page has embedded text and Gemini is not configured to read page images; enter the values manually")
    proposals = _proposals_for(document["id"])
    if any(r.get("review_state") in ("approved", "rejected") for c, rows in proposals.items() if c != "review_issues" for r in rows):
        raise HTTPException(status_code=409, detail="Some extracted values were already reviewed; re-extracting would discard that review")


def _page_id(document_id: str, number: int) -> str:
    return f"{document_id}-p{number:04d}"


def _pages_for(document_id: str) -> dict[int, dict]:
    return {p["page_number"]: p for p in list_records("document_pages") if p.get("document_id") == document_id}


async def _read_pages(document: dict, raw: bytes, inspection, run: dict) -> dict[int, dict]:
    """Make sure every page has a PageReading: text-layer pages from the PDF, scanned pages from Gemini vision.
    Readings already stored are reused, so re-running extraction does not re-read (or re-send) pages."""
    readings = _pages_for(document["id"])
    for page in inspection.pages:
        n = page.page_number
        if page.text_status == "text" and n not in readings:
            readings[n] = put_record("document_pages", PageReading(
                id=_page_id(document["id"], n), document_id=document["id"], page_number=n, method="text_layer",
                transcript=inspection.page_texts[n - 1], legibility="good", read_at=now_iso()).model_dump(mode="json"), _page_id(document["id"], n))
    to_read = [p.page_number for p in inspection.pages if p.text_status == "low_text" and p.page_number not in readings]
    for batch in batches(to_read, max(1, settings.vision_batch_pages)):
        images = [(n, await run_in_threadpool(render_page, raw, n)) for n in batch]
        for item in parse_batch(await gemini_read_pages(images), batch):
            record = PageReading(
                id=_page_id(document["id"], item.page), document_id=document["id"], page_number=item.page,
                method="gemini_vision", model=settings.gemini_model, read_at=now_iso(),
                **item.model_dump(exclude={"page"})).model_dump(mode="json")
            readings[item.page] = record  # saved together with the proposals, after the whole run succeeds
        run["pages_read"] += len(batch)
        run["ai_used"] = True
        patch_record("documents", document["id"], {"extraction": run})
    return readings


def _page_notes(readings: dict[int, dict]) -> list[tuple[str, str, str]]:
    """Review issues from the page readings: unreadable spots, poor legibility, templates."""
    notes = []
    for n, page in sorted(readings.items()):
        label = f"Page {n}" + (f" (printed {page['printed_page_number']})" if page.get("printed_page_number") else "")
        for region in page.get("unreadable_regions") or []:
            notes.append(("warning", "UNREADABLE", f"{label}: {region[:400]} — check the page image; nothing was guessed."))
        if page.get("legibility") == "poor":
            notes.append(("warning", "POOR_LEGIBILITY", f"{label} is hard to read; values from it need a careful check against the image."))
        if page.get("page_type") == "receipt_template":
            notes.append(("warning", "TEMPLATE_PAGE", f"{label} is a blank receipt format (a template), not evidence of a payment."))
    return notes


async def run_extraction(document_id: str, who: str, generate: Generate | None = None) -> None:
    """Background job: read scanned pages, extract every page with text in chunks, then save page readings and
    all proposals at once (or nothing on failure)."""
    generate = generate or gemini_generate
    document = get_record("documents", document_id)
    run = dict(document["extraction"])
    try:
        raw = await run_in_threadpool(document_storage.load_pdf, document["storage_ref"])
        inspection = await run_in_threadpool(inspect_pdf, raw, settings.max_document_pages)
        readings = await _read_pages(document, raw, inspection, run)
        texts = [readings[n]["transcript"] if n in readings else "" for n in range(1, inspection.page_count + 1)]
        bases = ["ai_transcript" if readings.get(n, {}).get("method") == "gemini_vision" else "text_layer"
                 for n in range(1, inspection.page_count + 1)]
        labels = {n: r for n, r in readings.items()}
        lengths = {n: len(texts[n - 1]) for n in range(1, inspection.page_count + 1) if texts[n - 1].strip()}
        plan = chunk_pages(lengths, settings.extraction_chunk_chars)
        run.update(chunks_total=len(plan), pages_sent=sorted(lengths),
                   pages_skipped_low_text=[n for n in range(1, inspection.page_count + 1) if n not in lengths])
        results = []
        for pages in plan:
            results.append(parse_chunk(await generate(build_prompt(document["kind"], texts, pages, inspection.page_count, labels))))
            run["chunks_done"] += 1
            run["ai_used"] = True
            patch_record("documents", document_id, {"extraction": run})
        proposals = build_proposals(document, results, texts, bases, _page_notes(readings))
    except Exception as exc:  # any failure must end in a visible failed state, never a silent "extracting"
        code = exc.code if isinstance(exc, (ExtractionFailed, PdfInspectionError)) else f"error:{type(exc).__name__}"
        if not isinstance(exc, ExtractionFailed):
            logger.warning("Extraction of %s failed: %s", document_id, code)
        run.update(finished_at=now_iso(), ai_error=code)
        # Only our own messages are shown; other exception texts may echo document content.
        reason = str(exc) if isinstance(exc, (ExtractionFailed, PdfInspectionError)) else f"unexpected error ({code})"
        patch_record("documents", document_id, {"status": "failed", "error": f"Extraction failed: {reason}", "extraction": run})
        log_activity(actor_name=who, event="extraction_failed", summary=f"Extraction of “{document['filename']}” failed ({code})",
                     entity_type="document", entity_id=document_id, partner_id=document.get("partner_id"), details={"error": code})
        return
    stored = _pages_for(document_id)
    for number, reading in readings.items():
        if number not in stored:
            put_record("document_pages", reading, reading["id"])
    for collection in PROPOSAL_COLLECTIONS:
        for old in _proposals_for(document_id)[collection]:
            delete_record(collection, old["id"])
        for record in proposals[collection]:
            put_record(collection, record, record["id"])
    run.update(finished_at=now_iso(), counts={c: len(rows) for c, rows in proposals.items()})
    patch_record("documents", document_id, {"status": "needs_review", "error": None, "extraction": run})
    found = sum(n for c, n in run["counts"].items() if c != "review_issues")
    log_activity(actor_name=who, event="extraction_completed",
                 summary=f"Extracted {found} proposed values from “{document['filename']}” — {run['counts']['review_issues']} issues to review",
                 entity_type="document", entity_id=document_id, partner_id=document.get("partner_id"), details=run["counts"])


@router.post("/documents/{document_id}/extract", response_model=SourceDocument, status_code=202,
             responses={409: {"description": "Extraction not possible in the document's current state"},
                        503: {"description": "Gemini is not configured"}})
async def start_extraction(document_id: str, request: Request, background: BackgroundTasks) -> dict:
    """Start extraction in the background; poll GET /documents/{id} for `status` and `extraction.chunks_done`."""
    document = get_record("documents", document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    _check_can_extract(document)
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="Gemini is not configured on the server, so automatic extraction is unavailable. Values can still be entered manually.")
    text_pages = [p["page_number"] for p in document["pages"] if p["text_status"] == "text"]
    already_read = _pages_for(document_id)
    run = ExtractionRun(
        started_at=now_iso(), model=settings.gemini_model,
        pages_to_read=sum(1 for p in document["pages"] if p["text_status"] == "low_text" and p["page_number"] not in already_read),
    ).model_dump(mode="json")
    who = actor(request)
    updated = patch_record("documents", document_id, {"status": "extracting", "error": None, "extraction": run})
    log_activity(actor_name=who, event="extraction_started", summary=f"Started extraction of “{document['filename']}”",
                 entity_type="document", entity_id=document_id, partner_id=document.get("partner_id"),
                 details={"pages": len(text_pages)})
    background.add_task(run_extraction, document_id, who)
    return updated


@router.get("/documents/{document_id}/extraction")
def get_extraction(document_id: str) -> dict:
    """Proposed values, clauses, terms, obligations, scope and review issues for one document (none are approved)."""
    document = get_record("documents", document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"document": SourceDocument(**document).model_dump(mode="json"), **_proposals_for(document_id)}


@router.get("/documents/{document_id}/pages", response_model=list[PageReading])
def list_pages(document_id: str) -> list[dict]:
    """The document map: per physical page, how it was read, its type, printed number, and transcript."""
    if not get_record("documents", document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return [page for _, page in sorted(_pages_for(document_id).items())]


@router.get("/documents/{document_id}/pages/{page_number}/image", response_class=Response,
            responses={200: {"content": {"image/jpeg": {}}, "description": "Page image for side-by-side review"}})
async def page_image(document_id: str, page_number: int, dpi: int = Query(default=110, ge=50, le=200)) -> Response:
    """One page as an image, for reviewers. Same authentication as every other route; never cached publicly."""
    document = get_record("documents", document_id)
    if not document or not document.get("storage_ref"):
        raise HTTPException(status_code=404, detail="Document not found")
    if not 1 <= page_number <= (document.get("page_count") or 0):
        raise HTTPException(status_code=404, detail="Page not found")
    raw = await run_in_threadpool(document_storage.load_pdf, document["storage_ref"])
    image = await run_in_threadpool(render_page, raw, page_number, dpi)
    return Response(content=image, media_type="image/jpeg", headers={"Cache-Control": "private, no-store"})
