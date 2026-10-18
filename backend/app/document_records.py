"""Create operational records from one extracted MOU, on an explicit user action.

Extraction stays document-scoped (the workbook is unchanged). When a person clicks "Create records", the extracted
values become a partner (or an existing one), an agreement, a project, reports, UCs, milestones, and a budget, so the
deterministic rules engine raises alerts from real MOU data. Nothing here runs automatically, nothing is inferred:
missing dates stay missing, and amounts keep their own currency.
"""
from datetime import date
from pathlib import PurePath
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError

from app import document_storage
from app.document_routes import PROPOSAL_COLLECTIONS, _proposals_for
from app.config import settings
from app.models import AgreementCreate, FinanceCreate, MilestoneCreate, OpportunityCreate, PartnerCreate, ProjectCreate, ReportCreate
from app.repository import delete_record, get_record, list_records, patch_record, put_record
from app.reviews import actor, log_activity, now_iso
from app.rules import business_today

router = APIRouter(tags=["documents"])


class CreateRecords(BaseModel):
    partner_id: str | None = None  # an existing partner; otherwise one is created from the extracted partner name
    partner_name: str | None = Field(default=None, max_length=160)  # overrides the extracted name (e.g. redacted scans)
    owner: str | None = Field(default=None, max_length=120)
    opportunity_id: str | None = None  # the pipeline deal this MOU closes; it must be approved in the pipeline first


# Pipeline stages at which a deal counts as approved, so its MOU can become an operational agreement.
APPROVED_STAGES = ("approval", "agreement", "active", "renewal")


def _validated(model, **data) -> dict:
    try:
        return model(**data).model_dump(mode="json")
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=[f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()]) from None


def _as_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def _fields(proposals: dict[str, list[dict]]) -> dict[str, Any]:
    """First non-rejected value per agreement field."""
    values: dict[str, Any] = {}
    for row in proposals["extracted_fields"]:
        value = row.get("approved_value") if row.get("approved_value") is not None else row.get("proposed_value")
        if row.get("review_state") != "rejected" and value not in (None, "") and row["field"] not in values:
            values[row["field"]] = value
    return values


def _deal_from_mou(document: dict, proposals: dict[str, list[dict]], partner_id: str | None, owner: str, today: date) -> dict:
    """The pipeline deal an MOU represents, from its extracted values only: no probability or follow-up is invented."""
    values = _fields(proposals)
    title = str(values.get("title") or values.get("programme_name") or PurePath(document["filename"]).stem)[:200]
    start = _as_date(values.get("effective_date") or values.get("start_date") or values.get("execution_date"))
    expiry = _as_date(values.get("expiry_date"))
    total = next((t for t in proposals["financial_terms"] if t.get("review_state") != "rejected"
                  and t.get("term_type") == "total_commitment" and t.get("amount") is not None and t.get("currency")), None)
    places = [s.get("value") or s.get("location") for s in proposals["programme_scope"]
              if s.get("review_state") != "rejected" and (s.get("dimension") in ("state", "region") or s.get("location"))]
    location = ", ".join(dict.fromkeys(str(p) for p in places if p))[:120] or None
    return {"partner_id": partner_id, "title": title, "stage": "closed" if expiry and expiry < today else "active",
            "owner": owner, "amount": total["amount"] if total else None,
            "currency": total["currency"] if total else settings.default_currency, "started_on": start, "location": location}


def _save_deal(document_id: str, deal: dict, agreement_id: str, today: date) -> dict:
    data = _validated(OpportunityCreate, **deal)
    saved = put_record("opportunities", {**data, "updated_at": today.isoformat(), "source_label": "user",
                                         "source_document_id": document_id})
    patch_record("agreements", agreement_id, {"opportunity_id": saved["id"]})
    return saved


def _deal_for(document: dict) -> dict | None:
    """The pipeline deal of this MOU: the one created from it, or the one its agreement was linked to."""
    deal = next((o for o in list_records("opportunities") if o.get("source_document_id") == document["id"]), None)
    agreement = get_record("agreements", document["agreement_id"]) if document.get("agreement_id") else None
    if not deal and agreement and agreement.get("opportunity_id"):
        deal = get_record("opportunities", agreement["opportunity_id"])
    return deal


@router.get("/documents/{document_id}/pipeline-deal")
def get_pipeline_deal(document_id: str, request: Request) -> dict:
    """This MOU's pipeline deal if it exists, and the values one would be created with."""
    document = get_record("documents", document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    proposed = _deal_from_mou(document, _proposals_for(document_id), document.get("partner_id"), actor(request), business_today())
    return {"deal": _deal_for(document), "proposed": {k: (v.isoformat() if isinstance(v, date) else v) for k, v in proposed.items()}}


@router.post("/documents/{document_id}/pipeline-deal", status_code=201)
def add_pipeline_deal(document_id: str, request: Request) -> dict:
    """Add an MOU that already has records (e.g. created before deals were automatic) to the pipeline."""
    document = get_record("documents", document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.get("agreement_id"):
        raise HTTPException(status_code=409, detail="Create records from this MOU first; its deal is added then")
    if _deal_for(document):
        raise HTTPException(status_code=409, detail="This MOU already has a pipeline deal")
    today = business_today()
    deal = _save_deal(document_id, _deal_from_mou(document, _proposals_for(document_id), document.get("partner_id"),
                                                  actor(request), today), document["agreement_id"], today)
    log_activity(actor_name=actor(request), event="pipeline_deal_created", summary=f"Added “{deal['title']}” to the pipeline from its MOU",
                 entity_type="opportunity", entity_id=deal["id"], partner_id=deal.get("partner_id"))
    return deal


@router.post("/documents/{document_id}/create-records")
def create_records(document_id: str, payload: CreateRecords, request: Request) -> dict:
    document = get_record("documents", document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.get("agreement_id"):
        raise HTTPException(status_code=409, detail="Records were already created from this document")
    if document.get("status") not in ("extracted", "needs_review"):
        raise HTTPException(status_code=409, detail="Extract the document before creating records")
    proposals = _proposals_for(document_id)
    values = _fields(proposals)
    who, today = actor(request), business_today()
    owner = payload.owner or who
    start = _as_date(values.get("effective_date") or values.get("start_date") or values.get("execution_date"))
    expiry = _as_date(values.get("expiry_date"))
    title = str(values.get("title") or values.get("programme_name") or PurePath(document["filename"]).stem)[:200]

    # ---- pipeline deal: an MOU becomes operational only once its deal is approved in the pipeline ----
    opportunity = get_record("opportunities", payload.opportunity_id) if payload.opportunity_id else None
    if payload.opportunity_id and not opportunity:
        raise HTTPException(status_code=404, detail="Pipeline deal not found")
    if opportunity and opportunity.get("stage") not in APPROVED_STAGES:
        raise HTTPException(status_code=409, detail=f"The pipeline deal “{opportunity['title']}” is at stage "
                                                    f"“{opportunity.get('stage')}”; approve it in the pipeline first")
    if opportunity and payload.partner_id and opportunity["partner_id"] != payload.partner_id:
        raise HTTPException(status_code=422, detail="The pipeline deal belongs to a different partner")

    # ---- partner ----
    partner_id = payload.partner_id or (opportunity or {}).get("partner_id")
    if partner_id and not get_record("partners", partner_id):
        raise HTTPException(status_code=404, detail="Partner not found")
    partner_created = False
    if not partner_id:
        name = (payload.partner_name or values.get("partner_name") or values.get("legal_entity_name") or "").strip()
        if len(name) < 2:
            raise HTTPException(status_code=422, detail="No partner name was extracted; choose a partner or enter its name")
        existing = next((p for p in list_records("partners") if p.get("name", "").strip().lower() == name.lower()), None)
        if existing:
            partner_id = existing["id"]
        else:
            data = _validated(PartnerCreate, name=name[:160], category="CSR funder", status="active", owner=owner,
                              summary=f"Created from the MOU “{document['filename']}”.")
            partner_id = put_record("partners", {**data, "updated_at": today.isoformat(), "source_label": "user"})["id"]
            partner_created = True

    # ---- project and agreement ----
    ended = bool(expiry and expiry < today)
    project = _validated(ProjectCreate, partner_id=partner_id, name=str(values.get("programme_name") or title)[:200],
                         status="completed" if ended else "active", owner=owner, start_date=start, end_date=expiry)
    project_id = put_record("projects", {**project, "source_label": "user", "source_document_id": document_id})["id"]
    agreement = _validated(AgreementCreate, partner_id=partner_id, title=title, reference_number=values.get("reference_number"),
                           status="expired" if ended else "active", start_date=start, expiry_date=expiry, owner=owner,
                           project_id=project_id, signed_copy="received", opportunity_id=(opportunity or {}).get("id"))
    agreement_id = put_record("agreements", {**agreement, "source_label": "user", "source_document_id": document_id})["id"]

    if opportunity and opportunity.get("stage") == "approval":
        patch_record("opportunities", opportunity["id"], {"stage": "agreement", "updated_at": today.isoformat()})

    # ---- obligations → reports / UCs / milestones ----
    created = {"reports": 0, "utilization_certificates": 0, "milestones": 0, "budgets": 0, "fund_release_terms": 0, "register_only": 0}
    for ob in proposals["obligations"]:
        if ob.get("review_state") == "rejected":
            continue
        due, kind, label = _as_date(ob.get("due_date")), ob.get("obligation_type"), str(ob.get("title") or "Obligation")[:200]
        ref = None
        if kind in ("progress_report", "impact_report"):
            report_type = "impact" if kind == "impact_report" else {"monthly": "monthly", "quarterly": "quarterly"}.get(ob.get("frequency"), "other")
            data = _validated(ReportCreate, partner_id=partner_id, project_id=project_id, title=label, report_type=report_type,
                              due_date=due, owner=ob.get("owner") or owner)
            ref, created["reports"] = {"collection": "reports", "id": put_record("reports", {**data, "source_label": "user"})["id"]}, created["reports"] + 1
        elif kind == "utilization_certificate":
            data = _validated(FinanceCreate, partner_id=partner_id, project_id=project_id, record_type="utilization_certificate",
                              title=label, due_date=due, owner=ob.get("owner") or owner)
            ref = {"collection": "finance", "id": put_record("finance", {**data, "source_label": "user"})["id"]}
            created["utilization_certificates"] += 1
        elif kind in ("milestone", "deliverable"):
            data = _validated(MilestoneCreate, project_id=project_id, title=label, due_date=due, owner=ob.get("owner") or owner)
            ref = {"collection": "milestones", "id": put_record("milestones", {**data, "partner_id": partner_id, "source_label": "user"})["id"]}
            created["milestones"] += 1
        else:
            created["register_only"] += 1
        patch_record("obligations", ob["id"], {"review_state": "approved", "agreement_id": agreement_id, "partner_id": partner_id,
                                               "project_id": project_id, "operational_ref": ref})

    # ---- money: the commitment as a budget (own currency); tranches feed the fund-release rules ----
    for term in proposals["financial_terms"]:
        if term.get("review_state") == "rejected":
            continue
        if term.get("term_type") == "total_commitment" and term.get("amount") is not None and term.get("currency"):
            data = _validated(FinanceCreate, partner_id=partner_id, project_id=project_id, record_type="budget",
                              title=str(term.get("description") or "Total commitment")[:200], amount=term["amount"],
                              currency=term["currency"], financial_term_id=term["id"])
            put_record("finance", {**data, "source_label": "user"})
            created["budgets"] += 1
        if term.get("term_type") in ("tranche", "payment_term"):
            created["fund_release_terms"] += 1
        patch_record("financial_terms", term["id"], {"review_state": "approved", "agreement_id": agreement_id, "partner_id": partner_id})

    # ---- pipeline: an MOU in use is a signed deal, so it appears on the pipeline even if nobody entered it there ----
    if not opportunity:
        _save_deal(document_id, _deal_from_mou(document, proposals, partner_id, owner, today), agreement_id, today)

    document = patch_record("documents", document_id, {"partner_id": partner_id, "agreement_id": agreement_id,
                                                      "records_created_at": now_iso(), "records_created_by": who})
    log_activity(actor_name=who, event="document_records_created",
                 summary=f"Created records from “{document['filename']}”: agreement, project, {created['reports']} reports, "
                         f"{created['utilization_certificates']} UCs, {created['milestones']} milestones",
                 entity_type="document", entity_id=document_id, partner_id=partner_id,
                 details={"agreement_id": agreement_id, "project_id": project_id, **created})
    return {"document": document, "partner_id": partner_id, "partner_created": partner_created, "agreement_id": agreement_id,
            "project_id": project_id, "created": created}


# ---- archive / restore / remove ----
# MOUs are contracts kept for audit: once records exist, a document can only be archived (hidden, restorable).
# Only an upload that never produced records can be removed outright, e.g. a mistaken or duplicate upload.

class ArchiveRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


def _linked_records(document: dict) -> list[tuple[str, dict]]:
    """Every record created from this document (archived or not)."""
    doc_id, agreement_id = document["id"], document.get("agreement_id")
    projects = [p for p in list_records("projects", include_archived=True) if p.get("source_document_id") == doc_id]
    project_ids = {p["id"] for p in projects}
    linked: list[tuple[str, dict]] = [("projects", p) for p in projects]
    linked += [("opportunities", o) for o in list_records("opportunities", include_archived=True)
               if o.get("source_document_id") == doc_id]
    linked += [("agreements", a) for a in list_records("agreements", include_archived=True)
               if a.get("source_document_id") == doc_id or (agreement_id and a["id"] == agreement_id)]
    for collection in ("reports", "finance", "milestones"):
        linked += [(collection, r) for r in list_records(collection, include_archived=True) if r.get("project_id") in project_ids]
    for collection in PROPOSAL_COLLECTIONS:
        linked += [(collection, r) for r in list_records(collection, include_archived=True) if r.get("document_id") == doc_id]
    return linked


def _set_archived(document_id: str, archived: bool, request: Request, reason: str | None = None) -> dict:
    document = get_record("documents", document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if archived and not document.get("agreement_id"):
        raise HTTPException(status_code=409, detail="No records were created from this document; remove the upload instead")
    if bool(document.get("archived")) == archived:
        raise HTTPException(status_code=409, detail="Document is already archived" if archived else "Document is not archived")
    linked = _linked_records(document)
    for collection, record in linked:
        patch_record(collection, record["id"], {"archived": archived})
    who = actor(request)
    stamp = {"archived": archived, "archived_at": now_iso() if archived else None,
             "archived_by": who if archived else None, "archived_reason": reason}
    document = put_record("documents", {**document, **stamp}, document_id)
    verb = "Archived" if archived else "Restored"
    log_activity(actor_name=who, event="document_archived" if archived else "document_restored",
                 summary=f"{verb} “{document['filename']}” and {len(linked)} linked records" + (f": {reason}" if reason else ""),
                 entity_type="document", entity_id=document_id, partner_id=document.get("partner_id"),
                 details={"records": len(linked), "reason": reason})
    return {"document": document, "records": len(linked)}


@router.post("/documents/{document_id}/archive")
def archive_document(document_id: str, payload: ArchiveRequest, request: Request) -> dict:
    return _set_archived(document_id, True, request, payload.reason.strip())


@router.post("/documents/{document_id}/restore")
def restore_document(document_id: str, request: Request) -> dict:
    return _set_archived(document_id, False, request)


@router.delete("/documents/{document_id}", status_code=204)
def remove_document(document_id: str, request: Request) -> None:
    """Remove a mistaken upload that never produced records: its PDF, page readings, and extraction."""
    document = get_record("documents", document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.get("agreement_id"):
        raise HTTPException(status_code=409, detail="Records were created from this document; archive it instead")
    if document.get("status") == "extracting":
        raise HTTPException(status_code=409, detail="Extraction is running; wait for it to finish")
    for collection in (*PROPOSAL_COLLECTIONS, "document_pages", "extraction_chunks"):
        for record in list_records(collection, include_archived=True):
            if record.get("document_id") == document_id:
                delete_record(collection, record["id"])
    if document.get("storage_ref"):
        document_storage.delete_pdf(document["storage_ref"])
    delete_record("documents", document_id)
    log_activity(actor_name=actor(request), event="document_removed", summary=f"Removed the upload “{document['filename']}”",
                 entity_type="document", entity_id=document_id, partner_id=document.get("partner_id"))
