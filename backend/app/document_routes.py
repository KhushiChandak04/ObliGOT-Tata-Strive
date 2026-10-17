"""Document intake and extraction: upload private MOU/addendum PDFs and export document-scoped results."""
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, Response
from fastapi.concurrency import run_in_threadpool

from app import deterministic, document_storage, ocr
from app.config import settings
from app.documents import DocumentStatus, ExtractionRun, PageReading, SourceDocument
from app.document_workbook import build_document_workbook
from app.extraction import ExtractionFailed, Generate, build_prompt, build_proposals, chunk_pages, groq_generate, parse_chunk
from app.page_reading import batches, groq_read_pages, parse_batch, render_page
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
             responses={413: {"description": "File too large"},
                        415: {"description": "Not a PDF"}})
async def upload_document(request: Request) -> dict:
    """Upload and inspect a PDF; every accepted upload gets a new document record."""
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
        if low and (settings.groq_available or ocr.ocr_available()):
            # Scanned pages are read from page images during extraction (AI transcription, reviewed by a person).
            record["status"] = "uploaded"
            scope = "All pages are" if len(low) == inspection.page_count else f"Page{'s' if len(low) > 1 else ''} {', '.join(map(str, low))} {'are' if len(low) > 1 else 'is'}"
            record["warnings"].append(
                f"{scope} scanned images without a text layer. During extraction "
                + ("Groq reads them from the page images (an AI transcription)" if settings.groq_available else "local OCR reads them (plain text)")
                + ", so compare extracted values with the page images.")
        elif len(low) == inspection.page_count:
            record["status"] = "blocked"
            record["warnings"].append(
                "No page has embedded text (likely a scanned PDF). Configure Groq vision or install Tesseract OCR to extract text from the page images.")
        else:
            record["status"] = "uploaded"
            if low:
                many = len(low) > 1
                record["warnings"].append(
                    f"Page{'s' if many else ''} {', '.join(map(str, low))} {'have' if many else 'has'} little or no embedded "
                    f"text (scanned, blank, or image-only). Review {'them' if many else 'it'} manually; "
                    f"{'they are' if many else 'it is'} not extracted.")
        if kind == "addendum" and not agreement_id:
            record["warnings"].append("Choose the agreement this addendum amends before comparing its changes.")
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

PROPOSAL_COLLECTIONS = ("extracted_fields", "clauses", "financial_terms", "obligations", "programme_scope", "tables", "review_issues")
# Bump when the extraction prompt/schema changes, so cached parts and page readings are not reused across versions.
EXTRACTION_SCHEMA_VERSION = "s2.1"
# Errors where the model's output for one part was unusable; that part is retried, then skipped.
BAD_OUTPUT_CODES = {"malformed_response", "invalid_json", "empty_response"}
PAGE_READING_VERSION = "1"
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
    if all(p["text_status"] == "low_text" for p in document.get("pages", [])) and not settings.groq_available \
            and not ocr.ocr_available() and not _pages_for(document["id"]):
        raise HTTPException(status_code=409, detail="No page has embedded text, Groq is not configured, and OCR (Tesseract) is not installed; enter the values manually or configure one of them")
    proposals = _proposals_for(document["id"])
    if any(r.get("review_state") in ("approved", "rejected") for c, rows in proposals.items() if c != "review_issues" for r in rows):
        raise HTTPException(status_code=409, detail="Legacy reviewed values exist; re-extracting would replace them")


def _page_id(document_id: str, number: int) -> str:
    return f"{document_id}-p{number:04d}"


def _pages_for(document_id: str) -> dict[int, dict]:
    """Stored page readings of the current version (older versions are read again)."""
    return {p["page_number"]: p for p in list_records("document_pages")
            if p.get("document_id") == document_id and p.get("version", PAGE_READING_VERSION) == PAGE_READING_VERSION}


async def _read_pages(document: dict, raw: bytes, inspection, run: dict, use_vision: bool) -> tuple[dict[int, dict], ExtractionFailed | None]:
    """Every page gets a PageReading: text-layer pages from the PDF; scanned pages from Groq vision when
    available. Readings are saved per batch and reused, so a retry never re-reads (or re-sends) finished pages.
    Returns the readings and, if Groq failed part-way, that failure (completed batches are kept)."""
    readings = _pages_for(document["id"])
    for page in inspection.pages:
        n = page.page_number
        if page.text_status == "text" and n not in readings:
            readings[n] = put_record("document_pages", PageReading(
                id=_page_id(document["id"], n), document_id=document["id"], page_number=n, method="text_layer",
                transcript=inspection.page_texts[n - 1], legibility="good", read_at=now_iso()).model_dump(mode="json"), _page_id(document["id"], n))
    if not use_vision:
        return readings, None
    to_read = [p.page_number for p in inspection.pages if p.text_status == "low_text"
               and (p.page_number not in readings or readings[p.page_number].get("method") == "ocr")]
    for batch in batches(to_read, min(3, max(1, settings.vision_batch_pages))):
        try:
            images = [(n, await run_in_threadpool(render_page, raw, n)) for n in batch]
            items = parse_batch(await groq_read_pages(images), batch)
        except ExtractionFailed as exc:
            return readings, exc
        for item in items:
            record = PageReading(
                id=_page_id(document["id"], item.page), document_id=document["id"], page_number=item.page,
                method="groq_vision", model=settings.groq_vision_model, read_at=now_iso(),
                **item.model_dump(exclude={"page"})).model_dump(mode="json")
            readings[item.page] = put_record("document_pages", record, record["id"])
        run["pages_read"] += len(batch)
        run["ai_used"] = True
        patch_record("documents", document["id"], {"extraction": run})
    return readings, None


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


def _chunk_key(document_id: str, prompt: str) -> str:
    digest = hashlib.sha256(f"{EXTRACTION_SCHEMA_VERSION}\n{prompt}".encode("utf-8")).hexdigest()[:20]
    return f"{document_id}-x{digest}"


def _ranges(pages: list[int]) -> str:
    out, start = [], None
    for i, n in enumerate(pages):
        if start is None:
            start = n
        if i + 1 == len(pages) or pages[i + 1] != n + 1:
            out.append(str(start) if start == n else f"{start}–{n}")
            start = None
    return ", ".join(out)


async def run_extraction(document_id: str, who: str, generate: Generate | None = None) -> None:
    """Background job. Stages: read pages (text layer; Groq vision for scanned pages) → extract with Groq in
    page-aware parts (each finished part cached) → deterministic fallback for whatever Groq could not do →
    validate → save document-scoped extraction output."""
    generate = generate or groq_generate
    document = get_record("documents", document_id)
    run = dict(document["extraction"])
    use_groq = run.get("mode") in {"groq", "gemini"}
    try:
        raw = await run_in_threadpool(document_storage.load_pdf, document["storage_ref"])
        inspection = await run_in_threadpool(inspect_pdf, raw, settings.max_document_pages)
        readings, failure = await _read_pages(document, raw, inspection, run, use_vision=use_groq)
        # Optional local OCR for scanned pages still without text (Groq unavailable or stopped).
        unread = [p.page_number for p in inspection.pages if p.text_status == "low_text" and p.page_number not in readings]
        ocr_note = None
        if unread and ocr.ocr_available():
            done = 0
            for n in unread:
                try:
                    text = await run_in_threadpool(ocr.ocr_page, raw, n)
                except ocr.OcrFailed as exc:
                    ocr_note = f"OCR stopped at page {n}: {exc}"
                    break
                record = PageReading(id=_page_id(document_id, n), document_id=document_id, page_number=n, method="ocr",
                                     model="tesseract", transcript=text, read_at=now_iso()).model_dump(mode="json")
                readings[n] = put_record("document_pages", record, record["id"])
                done += 1
            ocr_note = ocr_note or f"OCR read {done} scanned page{'s' if done != 1 else ''} (plain text; tables may be flattened)."
        total = inspection.page_count
        texts = [readings[n]["transcript"] if n in readings else "" for n in range(1, total + 1)]
        bases = [{"groq_vision": "ai_transcript", "gemini_vision": "ai_transcript", "ocr": "ocr_text"}.get(readings.get(n, {}).get("method"), "text_layer")
                 for n in range(1, total + 1)]
        lengths = {n: len(texts[n - 1]) for n in range(1, total + 1) if texts[n - 1].strip()}
        no_text = [n for n in range(1, total + 1) if n not in lengths]
        run.update(pages_sent=sorted(lengths), pages_skipped_low_text=no_text)
        results, covered = [], set()
        if use_groq and failure is None:
            continuing = {n for n, r in readings.items() if r.get("table_continues_from_previous")} | \
                         {n + 1 for n, r in readings.items() if r.get("table_continues_to_next")}
            plan = chunk_pages(lengths, settings.extraction_chunk_chars, continuing)
            run["chunks_total"] = len(plan)
            for pages in plan:
                prompt = build_prompt(document["kind"], texts, pages, total, readings)
                key = _chunk_key(document_id, prompt)
                cached = get_record("extraction_chunks", key)
                output, bad_output, stop = None, None, None
                for _ in range(1 if cached else 3):
                    try:
                        output = cached["output"] if cached else await generate(prompt)
                        results.append(parse_chunk(output))
                        bad_output = None
                        break
                    except ExtractionFailed as exc:
                        if exc.code not in BAD_OUTPUT_CODES:
                            stop = exc
                            break
                        bad_output = exc
                if stop is not None:  # quota, auth, or outage: later parts would fail the same way
                    failure = stop
                    break
                if bad_output is not None:
                    # This part's output was unusable after retries; later parts are still extracted.
                    failure = bad_output
                    continue
                if not cached:  # finished parts are cached, so a retry resumes after them
                    put_record("extraction_chunks", {"document_id": document_id, "pages": pages, "output": output,
                                                     "schema_version": EXTRACTION_SCHEMA_VERSION, "created_at": now_iso()}, key)
                covered.update(pages)
                run["chunks_done"] += 1
                run["ai_used"] = True
                patch_record("documents", document_id, {"extraction": run})
        remaining = [n for n in sorted(lengths) if n not in covered]
        notes = _page_notes(readings)
        if remaining:
            # Deterministic fallback: explicit dates, references, and amounts from the text that exists.
            fallback_texts = [texts[n - 1] if n in remaining else "" for n in range(1, total + 1)]
            results.append(deterministic.extract(fallback_texts))
            notes.append(("warning", "SEMANTIC_EXTRACTION_PENDING",
                          f"Pages {_ranges(remaining)} were processed by pattern matching only (dates, references, amounts with a "
                          "currency). Clauses, obligations, deadlines, and tables on them were not extracted — re-run extraction "
                          "when Groq is available, or use the source pages to enter missing values in the workbook."))
        if no_text:
            why = ("Groq could not read them" if use_groq else "Groq is not configured") + (
                " and OCR could not read them" if ocr.ocr_available() else " and OCR (Tesseract) is not installed")
            notes.append(("error", "PAGES_NOT_READ",
                          f"Pages {_ranges(no_text)} have no text available ({why}); nothing on them was extracted. "
                          "Re-run extraction later or use the page images to check the exported workbook."))
        if not lengths:
            # Nothing usable at all: keep what finished (page readings) and ask for a retry.
            code = failure.code if failure else "no_text"
            run.update(finished_at=now_iso(), ai_error=code, retryable=True, mode="groq" if use_groq else "deterministic",
                       note=f"No page has text yet ({len(readings)} of {total} pages read). Re-run extraction later.")
            patch_record("documents", document_id, {"status": "retry_required", "error": f"Extraction incomplete: {failure or 'no readable text'}",
                                                    "extraction": run})
            log_activity(actor_name=who, event="extraction_retry_required", summary=f"Extraction of “{document['filename']}” needs a retry ({code})",
                         entity_type="document", entity_id=document_id, partner_id=document.get("partner_id"), details={"error": code})
            return
        proposals = build_proposals(document, results, texts, bases, notes, readings)
    except Exception as exc:  # unexpected or permanent failure: a visible failed state, never a silent "extracting"
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
    for collection in PROPOSAL_COLLECTIONS:
        for old in _proposals_for(document_id)[collection]:
            delete_record(collection, old["id"])
        for record in proposals[collection]:
            put_record(collection, record, record["id"])
    groq_part = f"Groq read {run['pages_read']} scanned pages and extracted {run['chunks_done']} of {run['chunks_total']} parts" if use_groq else "Groq not used"
    if ocr_note:
        groq_part = f"{groq_part}. {ocr_note}"
    if failure is not None:
        stage = f"{groq_part}; then stopped ({failure.code}: {failure}). Pattern matching covered the rest."
    elif remaining:
        stage = f"{groq_part}. Pattern matching only (no Groq)."
    else:
        stage = f"{groq_part}."
    run.update(finished_at=now_iso(), counts={c: len(rows) for c, rows in proposals.items()},
               mode="groq" if use_groq and not remaining else ("partial" if covered else "deterministic"),
               ai_error=failure.code if failure else None,
               retryable=bool(remaining or no_text) and (failure is None or failure.retryable or not use_groq),
               note=stage)
    patch_record("documents", document_id, {"status": "extracted", "error": None, "extraction": run})
    found = sum(n for c, n in run["counts"].items() if c != "review_issues")
    log_activity(actor_name=who, event="extraction_completed",
                 summary=f"Extracted {found} values from “{document['filename']}” — {run['counts']['review_issues']} extraction notes"
                         + ("" if run["mode"] in {"groq", "gemini"} else f" ({run['mode']} extraction)"),
                 entity_type="document", entity_id=document_id, partner_id=document.get("partner_id"), details=run["counts"])


@router.post("/documents/{document_id}/extract", response_model=SourceDocument, status_code=202,
             responses={409: {"description": "Extraction not possible in the document's current state"}})
async def start_extraction(document_id: str, request: Request, background: BackgroundTasks) -> dict:
    """Start extraction in the background; poll GET /documents/{id} for `status` and `extraction` progress.
    With Groq configured: Groq first, pattern matching for anything it cannot finish. Without Groq:
    pattern matching on available text only, clearly marked as such."""
    document = get_record("documents", document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    _check_can_extract(document)
    already_read = _pages_for(document_id)
    use_groq = settings.groq_available
    run = ExtractionRun(
        started_at=now_iso(), model=settings.groq_model if use_groq else "none",
        mode="groq" if use_groq else "deterministic",
        pages_to_read=sum(1 for p in document["pages"] if p["text_status"] == "low_text" and p["page_number"] not in already_read) if use_groq else 0,
    ).model_dump(mode="json")
    who = actor(request)
    warnings = [
        warning for warning in document.get("warnings", [])
        if not warning.startswith("No page has embedded text (likely a scanned PDF). Configure")
    ]
    updated = patch_record("documents", document_id, {
        "status": "extracting", "error": None, "extraction": run, "warnings": warnings,
    })
    log_activity(actor_name=who, event="extraction_started",
                 summary=f"Started extraction of “{document['filename']}”" + ("" if use_groq else " (pattern matching only; Groq not configured)"),
                 entity_type="document", entity_id=document_id, partner_id=document.get("partner_id"),
                 details={"mode": run["mode"]})
    background.add_task(run_extraction, document_id, who)
    return updated


@router.get("/documents/{document_id}/extraction")
def get_extraction(document_id: str) -> dict:
    """Extracted values, clauses, terms, obligations, scope and extraction issues for one document."""
    document = get_record("documents", document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"document": SourceDocument(**document).model_dump(mode="json"), **_proposals_for(document_id)}


@router.get("/documents/{document_id}/export/workbook", response_class=Response)
def export_document_workbook(document_id: str, request: Request) -> Response:
    document = get_record("documents", document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    content = build_document_workbook(document, _proposals_for(document_id))
    log_activity(actor_name=actor(request), event="document_workbook_exported",
                 summary=f"Downloaded extraction workbook for “{document['filename']}”",
                 entity_type="document", entity_id=document_id, partner_id=document.get("partner_id"))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="obligot-{document_id}-extraction.xlsx"',
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/documents/{document_id}/pages", response_model=list[PageReading])
def list_pages(document_id: str) -> list[dict]:
    """The document map: per physical page, how it was read, its type, printed number, and transcript."""
    if not get_record("documents", document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return [page for _, page in sorted(_pages_for(document_id).items())]


@router.get("/documents/{document_id}/pages/{page_number}/image", response_class=Response,
            responses={200: {"content": {"image/jpeg": {}}, "description": "Source page image"}})
async def page_image(document_id: str, page_number: int, dpi: int = Query(default=110, ge=50, le=200)) -> Response:
    """One page as an image for source comparison. Same authentication as every other route; never cached publicly."""
    document = get_record("documents", document_id)
    if not document or not document.get("storage_ref"):
        raise HTTPException(status_code=404, detail="Document not found")
    if not 1 <= page_number <= (document.get("page_count") or 0):
        raise HTTPException(status_code=404, detail="Page not found")
    raw = await run_in_threadpool(document_storage.load_pdf, document["storage_ref"])
    image = await run_in_threadpool(render_page, raw, page_number, dpi)
    return Response(content=image, media_type="image/jpeg", headers={"Cache-Control": "private, no-store"})
