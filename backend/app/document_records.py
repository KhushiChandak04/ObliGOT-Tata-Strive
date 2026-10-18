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

from app.document_routes import _proposals_for
from app.models import AgreementCreate, FinanceCreate, MilestoneCreate, PartnerCreate, ProjectCreate, ReportCreate
from app.repository import get_record, list_records, patch_record, put_record
from app.reviews import actor, log_activity, now_iso
from app.rules import business_today

router = APIRouter(tags=["documents"])


class CreateRecords(BaseModel):
    partner_id: str | None = None  # an existing partner; otherwise one is created from the extracted partner name
    partner_name: str | None = Field(default=None, max_length=160)  # overrides the extracted name (e.g. redacted scans)
    owner: str | None = Field(default=None, max_length=120)


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

    # ---- partner ----
    partner_id = payload.partner_id
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
                           project_id=project_id, signed_copy="received")
    agreement_id = put_record("agreements", {**agreement, "source_label": "user", "source_document_id": document_id})["id"]

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
                              title=label, due_date=due)
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

    document = patch_record("documents", document_id, {"partner_id": partner_id, "agreement_id": agreement_id,
                                                      "records_created_at": now_iso(), "records_created_by": who})
    log_activity(actor_name=who, event="document_records_created",
                 summary=f"Created records from “{document['filename']}”: agreement, project, {created['reports']} reports, "
                         f"{created['utilization_certificates']} UCs, {created['milestones']} milestones",
                 entity_type="document", entity_id=document_id, partner_id=partner_id,
                 details={"agreement_id": agreement_id, "project_id": project_id, **created})
    return {"document": document, "partner_id": partner_id, "partner_created": partner_created, "agreement_id": agreement_id,
            "project_id": project_id, "created": created}
