"""Human review of extracted proposals and the approval gate into operational records.

Only approved values cross the gate. Approving an MOU creates (or fills in) the agreement and turns approved
obligations into milestones, reports, or UC records, which the deterministic rules engine then evaluates.
Rejected and deferred values never reach operational records.
"""
from datetime import date
from pathlib import PurePath
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError

from app.amendments import addendum_blockers, approve_addendum
from app.document_routes import PROPOSAL_COLLECTIONS, _proposals_for
from app.documents import (
    Clause, ExtractedField, ExtractedTable, FinancialTerm, Obligation, ProgrammeScope, ReviewIssue, ScalarValue,
)
from app.extraction import AGREEMENT_FIELDS
from app.models import AgreementCreate, FinanceCreate, MilestoneCreate, PartnerCreate, ProjectCreate, ReportCreate
from app.repository import get_record, patch_record, put_record
from app.reviews import actor, log_activity, now_iso
from app.rules import business_today

router = APIRouter(tags=["documents"])

REVIEWABLE = {
    "extracted_fields": ExtractedField, "clauses": Clause, "financial_terms": FinancialTerm,
    "obligations": Obligation, "programme_scope": ProgrammeScope, "tables": ExtractedTable,
}
# Fields a reviewer may correct when approving (extracted fields are corrected through `value`).
EDITABLE = {
    "clauses": {"clause_type", "heading", "summary", "needs_legal_review"},
    "financial_terms": {"term_type", "description", "amount", "currency", "basis", "financial_year", "payer", "due_date", "condition"},
    "obligations": {"obligation_type", "title", "frequency", "due_date", "owner"},
    "programme_scope": {"dimension", "value", "target_value", "target_unit", "location", "period"},
    "tables": {"title", "kind", "section", "currency", "unit_notes", "notes"},  # cells are corrected against the page in S3
}
DECISION_STATE = {"approve": "approved", "reject": "rejected", "defer": "deferred", "reset": "needs_review"}
PAST = {"approve": "Approved", "reject": "Rejected", "defer": "Deferred", "reset": "Reopened"}
PENDING = ("proposed", "needs_review")


class ProposalDecision(BaseModel):
    decision: Literal["approve", "reject", "defer", "reset"]
    value: ScalarValue = None  # extracted fields: corrected value (defaults to the proposed value)
    changes: dict[str, Any] = Field(default_factory=dict)  # other proposals: corrected fields
    note: str | None = Field(default=None, max_length=1000)


class IssueDecision(BaseModel):
    status: Literal["resolved", "deferred", "open"]
    resolution: str | None = Field(default=None, max_length=1000)


class DocumentApproval(BaseModel):
    partner_id: str | None = None
    create_partner: bool = False  # create the partner from the approved partner name
    owner: str | None = Field(default=None, min_length=2, max_length=120)
    overwrite_existing: bool = False  # replace differing values on an already linked agreement


def _document(document_id: str) -> dict:
    document = get_record("documents", document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


def _require_reviewable(document: dict) -> None:
    if document["status"] != "needs_review":
        raise HTTPException(status_code=409, detail=f"The document is {document['status'].replace('_', ' ')}; decisions can only be changed while it needs review")


def _approved_field_value(field: str, value: ScalarValue, proposed: ScalarValue) -> ScalarValue:
    chosen = proposed if value is None else value
    if chosen is None or (isinstance(chosen, str) and not chosen.strip()):
        raise HTTPException(status_code=422, detail="No value to approve: enter the value from the document, or reject the field")
    if AGREEMENT_FIELDS[field] == "date":
        try:
            return chosen if isinstance(chosen, date) else date.fromisoformat(str(chosen).strip())
        except ValueError:
            raise HTTPException(status_code=422, detail=f"{field} must be a date in YYYY-MM-DD format") from None
    text = str(chosen).strip()
    if len(text) > 1000:
        raise HTTPException(status_code=422, detail="Value is longer than 1000 characters")
    return text


@router.patch("/documents/{document_id}/proposals/{collection}/{item_id}")
def decide_proposal(document_id: str, collection: str, item_id: str, payload: ProposalDecision, request: Request) -> dict:
    """Approve (optionally corrected), reject, defer, or reset one proposed value."""
    if collection not in REVIEWABLE:
        raise HTTPException(status_code=404, detail="Unknown proposal type")
    document = _document(document_id)
    _require_reviewable(document)
    item = get_record(collection, item_id)
    if not item or item.get("document_id") != document_id:
        raise HTTPException(status_code=404, detail="Proposal not found for this document")
    evidence = item.get("evidence") or {}
    if payload.decision in ("approve", "defer") and not (payload.note or "").strip() and (
            payload.decision == "defer" or not evidence.get("verified")):
        reason = "Explain why this is deferred" if payload.decision == "defer" else \
            "The source quote was not verified; add a note confirming you checked the document"
        raise HTTPException(status_code=422, detail=reason)
    who, when = actor(request), now_iso()
    updated = dict(item)
    if payload.decision == "reset":
        updated.update(review_state="needs_review", reviewed_by=None, reviewed_at=None)
        if collection == "extracted_fields":
            updated["approved_value"] = None
    else:
        updated.update(review_state=DECISION_STATE[payload.decision], reviewed_by=who, reviewed_at=when)
        if collection == "extracted_fields":
            updated["approved_value"] = (_approved_field_value(item["field"], payload.value, item.get("proposed_value"))
                                         if payload.decision == "approve" else None)
            updated["review_note"] = payload.note
        elif payload.changes:
            if payload.decision != "approve":
                raise HTTPException(status_code=422, detail="Corrections can only be made when approving")
            unknown = set(payload.changes) - EDITABLE[collection]
            if unknown:
                raise HTTPException(status_code=422, detail=f"These fields cannot be changed here: {', '.join(sorted(unknown))}")
            updated.update(payload.changes)
    try:
        validated = REVIEWABLE[collection](**updated).model_dump(mode="json")
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=[e["msg"] for e in exc.errors()]) from None
    saved = put_record(collection, validated, item_id)
    corrected = collection == "extracted_fields" and payload.decision == "approve" and \
        str(validated["approved_value"]) != str(item.get("proposed_value"))
    label = item.get("field") or item.get("title") or item.get("description") or item.get("value") or item.get("clause_type")
    log_activity(actor_name=who, event=f"proposal_{payload.decision}",
                 summary=f"{PAST[payload.decision]} “{label}”"
                         f"{' (corrected)' if corrected or (payload.decision == 'approve' and payload.changes) else ''} in “{document['filename']}”",
                 entity_type="document", entity_id=document_id, partner_id=document.get("partner_id"),
                 details={"collection": collection, "item_id": item_id, "note": payload.note})
    return saved


@router.patch("/documents/{document_id}/issues/{issue_id}", response_model=ReviewIssue)
def decide_issue(document_id: str, issue_id: str, payload: IssueDecision, request: Request) -> dict:
    document = _document(document_id)
    _require_reviewable(document)
    issue = get_record("review_issues", issue_id)
    if not issue or issue.get("document_id") != document_id:
        raise HTTPException(status_code=404, detail="Issue not found for this document")
    updated = {**issue, "status": payload.status, "resolution": payload.resolution if payload.status != "open" else None}
    try:
        validated = ReviewIssue(**updated).model_dump(mode="json")
    except ValidationError:
        raise HTTPException(status_code=422, detail=f"A {payload.status} issue needs a resolution note") from None
    saved = put_record("review_issues", validated, issue_id)
    log_activity(actor_name=actor(request), event=f"issue_{payload.status}",
                 summary=f"Issue {issue['code']} {payload.status} in “{document['filename']}”",
                 entity_type="document", entity_id=document_id, partner_id=document.get("partner_id"),
                 details={"issue_id": issue_id, "resolution": payload.resolution})
    return saved


def approved_values(proposals: dict[str, list[dict]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for f in proposals["extracted_fields"]:
        if f["review_state"] == "approved":
            values.setdefault(f["field"], set()).add(f["approved_value"])
    return {k: next(iter(v)) if len(v) == 1 else v for k, v in values.items()}


def approval_blockers(document: dict, proposals: dict[str, list[dict]], partner_id: str | None = None,
                      create_partner: bool = False) -> list[str]:
    """Everything that prevents approval, in plain words. Empty list = ready."""
    blockers = []
    if document["status"] != "needs_review":
        blockers.append(f"The document is {document['status'].replace('_', ' ')}, not awaiting review.")
    if document["kind"] == "addendum":
        return blockers + addendum_blockers(document)  # addenda are reviewed change by change
    pending = sum(1 for c in REVIEWABLE for r in proposals[c] if r["review_state"] in PENDING)
    if pending:
        blockers.append(f"{pending} extracted value{'s' if pending != 1 else ''} still need{'s' if pending == 1 else ''} a decision (approve, reject, or defer).")
    open_issues = sum(1 for i in proposals["review_issues"] if i["status"] == "open" and i.get("blocks_approval", True))
    if open_issues:
        blockers.append(f"{open_issues} review issue{'s are' if open_issues != 1 else ' is'} still open (resolve or defer with a note).")
    values = approved_values(proposals)
    for field, value in values.items():
        if isinstance(value, set):
            blockers.append(f"Different values were approved for {field}; keep only one.")
    start = values.get("effective_date") or values.get("start_date")
    expiry = values.get("expiry_date")
    if isinstance(start, str):
        start = date.fromisoformat(start)
    if isinstance(expiry, str):
        expiry = date.fromisoformat(expiry)
    if isinstance(start, date) and isinstance(expiry, date) and expiry < start:
        blockers.append("The approved expiry date is before the approved start/effective date.")
    if not (document.get("partner_id") or partner_id or (create_partner and isinstance(values.get("partner_name"), str))):
        blockers.append("Choose the partner, or approve the partner name and create the partner.")
    return blockers


@router.get("/documents/{document_id}/approval-check")
def approval_check(document_id: str, partner_id: str | None = None, create_partner: bool = False) -> dict:
    """Whether the document can be approved now, and what is still blocking it."""
    document = _document(document_id)
    blockers = approval_blockers(document, _proposals_for(document_id), partner_id, create_partner)
    return {"ready": not blockers, "blockers": blockers}


def _as_date(value: Any) -> date | None:
    if value is None or isinstance(value, set):
        return None
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def ensure_project(agreement: dict, obligation: dict, owner: str) -> str | None:
    """The agreement's project; created (and linked) only when a milestone needs one."""
    if agreement.get("project_id") or obligation["obligation_type"] not in ("milestone", "deliverable"):
        return agreement.get("project_id")
    expiry = _as_date(agreement.get("expiry_date"))
    data = _validated(ProjectCreate, partner_id=agreement["partner_id"], name=agreement["title"], owner=owner,
                      status="completed" if expiry and expiry < business_today() else "active",
                      start_date=_as_date(agreement.get("start_date")), end_date=expiry)
    project_id = put_record("projects", {**data, "source_label": "user"})["id"]
    patch_record("agreements", agreement["id"], {"project_id": project_id})
    agreement["project_id"] = project_id
    return project_id


def validate_obligation_target(obligation: dict, project_id: str | None) -> None:
    if obligation["obligation_type"] in ("milestone", "deliverable") and not project_id:
        raise HTTPException(status_code=422, detail="A milestone needs a project")


def create_operational(obligation: dict, partner_id: str, project_id: str | None, owner: str) -> dict | None:
    """Turn one approved obligation into the operational record the rules engine evaluates.
    Fund releases and other obligations stay in the obligations register only (no money record is invented)."""
    due = _as_date(obligation.get("due_date"))
    kind = obligation["obligation_type"]
    if kind in ("milestone", "deliverable"):
        validate_obligation_target(obligation, project_id)
        data = _validated(MilestoneCreate, project_id=project_id, title=obligation["title"][:200], due_date=due,
                          owner=obligation.get("owner") or owner)
        return {"collection": "milestones", "id": put_record("milestones", {**data, "partner_id": partner_id, "source_label": "user"})["id"]}
    if kind in ("progress_report", "impact_report"):
        report_type = "impact" if kind == "impact_report" else {"monthly": "monthly", "quarterly": "quarterly"}.get(obligation["frequency"], "other")
        data = _validated(ReportCreate, partner_id=partner_id, project_id=project_id, title=obligation["title"][:200],
                          report_type=report_type, due_date=due, owner=obligation.get("owner") or owner)
        return {"collection": "reports", "id": put_record("reports", {**data, "source_label": "user"})["id"]}
    if kind == "utilization_certificate":
        data = _validated(FinanceCreate, partner_id=partner_id, project_id=project_id, record_type="utilization_certificate",
                          title=obligation["title"][:200], due_date=due)
        return {"collection": "finance", "id": put_record("finance", {**data, "source_label": "user"})["id"]}
    return None


def _validated(model, **data) -> dict:
    try:
        return model(**data).model_dump(mode="json")
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=[e["msg"] for e in exc.errors()]) from None


@router.post("/documents/{document_id}/approve")
def approve_document(document_id: str, payload: DocumentApproval, request: Request) -> dict:
    """Approve a reviewed MOU: approved values become the agreement and its operational obligations."""
    document = _document(document_id)
    proposals = _proposals_for(document_id)
    if payload.partner_id and not get_record("partners", payload.partner_id):
        raise HTTPException(status_code=404, detail="Partner not found")
    if document.get("partner_id") and payload.partner_id and payload.partner_id != document["partner_id"]:
        raise HTTPException(status_code=422, detail="The document is already linked to a different partner")
    blockers = approval_blockers(document, proposals, payload.partner_id, payload.create_partner)
    if blockers:
        raise HTTPException(status_code=409, detail={"message": "The document cannot be approved yet", "blockers": blockers})

    who, today = actor(request), business_today()
    owner = payload.owner or who
    if document["kind"] == "addendum":
        result = approve_addendum(document, who, owner)
        document = patch_record("documents", document_id, {"status": "approved", "approved_by": who, "approved_at": now_iso()})
        log_activity(actor_name=who, event="document_approved",
                     summary=f"Approved addendum “{document['filename']}”: {len(result['applied'])} changes in force, "
                             f"{len(result['scheduled'])} scheduled for their effective date",
                     entity_type="document", entity_id=document_id, partner_id=document.get("partner_id"),
                     details={"agreement_id": result["agreement_id"], "applied": result["applied"], "scheduled": result["scheduled"]})
        return {"document": document, "agreement_id": result["agreement_id"], "partner_id": document.get("partner_id"),
                "applied_changes": result["applied"], "scheduled_changes": result["scheduled"], "created": result["added"]}
    values = approved_values(proposals)
    start, expiry = _as_date(values.get("effective_date") or values.get("start_date")), _as_date(values.get("expiry_date"))
    title = values.get("title") or values.get("programme_name") or PurePath(document["filename"]).stem
    approved = {c: [r for r in proposals[c] if r["review_state"] == "approved"] for c in REVIEWABLE}

    # ---- validate and plan every write before writing anything ----
    partner_id = document.get("partner_id") or payload.partner_id
    new_partner = None
    if not partner_id:
        new_partner = _validated(PartnerCreate, name=values["partner_name"], category="Other", status="active", owner=owner,
                                 summary=f"Created from the approved document “{document['filename']}”.")
    agreement_id = document.get("agreement_id")
    agreement_update: dict[str, Any] = {}
    if agreement_id:
        existing = get_record("agreements", agreement_id)
        if not existing:
            raise HTTPException(status_code=404, detail="The linked agreement no longer exists")
        conflicts = []
        for field, value in (("title", values.get("title")), ("reference_number", values.get("reference_number")),
                             ("start_date", start and start.isoformat()), ("expiry_date", expiry and expiry.isoformat())):
            if value is None:
                continue
            if existing.get(field) in (None, ""):
                agreement_update[field] = value
            elif str(existing[field]) != str(value):
                if payload.overwrite_existing:
                    agreement_update[field] = value
                else:
                    conflicts.append({"field": field, "current": existing[field], "approved": value})
        if conflicts:
            raise HTTPException(status_code=409, detail={
                "message": "Approved values differ from the linked agreement. Correct them, or approve with overwrite_existing.",
                "conflicts": conflicts})
        merged = {k: v for k, v in {**existing, **agreement_update}.items() if k in AgreementCreate.model_fields}
        _validated(AgreementCreate, **merged)
    else:
        status = "expired" if expiry and expiry < today else "active"
        agreement_data = _validated(AgreementCreate, partner_id=partner_id or "pending", title=title,
                                    reference_number=values.get("reference_number"), status=status,
                                    start_date=start, expiry_date=expiry, owner=owner)

    needs_project = any(o["obligation_type"] in ("milestone", "deliverable") for o in approved["obligations"]) \
        or bool(approved["programme_scope"]) or "programme_name" in values
    project_id = (get_record("agreements", agreement_id) or {}).get("project_id") if agreement_id else None
    new_project = None
    if needs_project and not project_id:
        new_project = _validated(ProjectCreate, partner_id=partner_id or "pending", name=values.get("programme_name") or title,
                                 status="active" if not (expiry and expiry < today) else "completed",
                                 owner=owner, start_date=start, end_date=expiry)

    # ---- write ----
    if new_partner:
        partner = put_record("partners", {**new_partner, "updated_at": today.isoformat(), "source_label": "user"})
        partner_id = partner["id"]
    if new_project:
        project_id = put_record("projects", {**new_project, "partner_id": partner_id, "source_label": "user"})["id"]
    if agreement_id:
        if project_id and not get_record("agreements", agreement_id).get("project_id"):
            agreement_update["project_id"] = project_id
        if agreement_update:
            patch_record("agreements", agreement_id, agreement_update)
        agreement_event = "agreement_updated"
    else:
        agreement = put_record("agreements", {**agreement_data, "partner_id": partner_id, "project_id": project_id,
                                              "source_document_id": document_id, "source_label": "user"})
        agreement_id = agreement["id"]
        agreement_event = "agreement_created"

    created = {"milestones": 0, "reports": 0, "finance": 0, "register_only": 0}
    for obligation in approved["obligations"]:
        ref = create_operational(obligation, partner_id, project_id, owner)
        created[ref["collection"] if ref else "register_only"] += 1
        patch_record("obligations", obligation["id"], {"agreement_id": agreement_id, "partner_id": partner_id,
                                                       "project_id": project_id, "operational_ref": ref})
    for term in approved["financial_terms"]:
        patch_record("financial_terms", term["id"], {"agreement_id": agreement_id, "partner_id": partner_id})
    for clause in approved["clauses"]:
        patch_record("clauses", clause["id"], {"agreement_id": agreement_id})
    for table in approved["tables"]:
        patch_record("tables", table["id"], {"agreement_id": agreement_id})
    for scope in approved["programme_scope"]:
        patch_record("programme_scope", scope["id"], {"agreement_id": agreement_id, "project_id": project_id})
    for field in approved["extracted_fields"]:
        patch_record("extracted_fields", field["id"], {"target_id": agreement_id})

    approved_at = now_iso()
    document = patch_record("documents", document_id, {"status": "approved", "approved_by": who, "approved_at": approved_at,
                                                      "partner_id": partner_id, "agreement_id": agreement_id})
    summary = (f"Approved “{document['filename']}”: {agreement_event.replace('_', ' ')}, {created['milestones']} milestones, "
               f"{created['reports']} reports, {created['finance']} UCs, {created['register_only']} register-only obligations")
    log_activity(actor_name=who, event="document_approved", summary=summary, entity_type="document", entity_id=document_id,
                 partner_id=partner_id, details={"agreement_id": agreement_id, "project_id": project_id, **created})
    return {"document": document, "agreement_id": agreement_id, "partner_id": partner_id, "project_id": project_id,
            "created": created, "partner_created": bool(new_partner), "project_created": bool(new_project)}
