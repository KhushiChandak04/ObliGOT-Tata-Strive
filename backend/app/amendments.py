"""Addenda: link to the right agreement, compare proposed changes with current values, review, apply, keep history.

- An addendum is linked to an agreement by a person; candidates are only suggested, never chosen automatically.
- Changes are built from the addendum's extracted values against the agreement's *current* values (prior → proposed).
- A change is applied only after approval, with verified evidence and a known effective date. Changes whose
  effective date is in the future are applied when that date arrives (checked whenever alerts or agreements are read).
- Several approved changes to one field are applied in effective-date order; two different values for the same
  field and effective date are a conflict and stay `unresolved` — they never affect alerts.
- Original values and every change are kept (`agreement_changes`); nothing is overwritten in the history.
"""
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError

from app.document_routes import _proposals_for
from app.documents import AgreementChange, ScalarValue
from app.repository import delete_record, get_record, list_records, patch_record, put_record
from app.reviews import actor, log_activity, now_iso
from app.rules import business_today

router = APIRouter(tags=["documents"])

# Agreement terms an addendum may change. "record" fields live on the agreement record and drive alerts;
# "term" fields are part of the effective view and the workbook only.
CHANGEABLE: dict[str, Literal["record", "term"]] = {
    "expiry_date": "record", "start_date": "record", "renewal_terms": "term", "termination_terms": "term",
    "duration": "term", "scope_summary": "term", "programme_name": "term",
}
DATE_FIELDS = {"expiry_date", "start_date"}
# The addendum's own dates: execution_date = amendment date; effective_date = when its changes take effect.
ADD_TARGETS = {"obligations": ("obligation", "title"), "financial_terms": ("financial_term", "description"),
               "clauses": ("clause", "summary")}


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return value.isoformat() if isinstance(value, date) else str(value)


def _single(fields: list[dict], name: str) -> Any:
    values = {_iso(f.get("proposed_value")) for f in fields if f["field"] == name and f.get("proposed_value") is not None}
    return values.pop() if len(values) == 1 else None


def _document(document_id: str) -> dict:
    document = get_record("documents", document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


def _changes_for(*, agreement_id: str | None = None, document_id: str | None = None) -> list[dict]:
    rows = [c for c in list_records("agreement_changes")
            if (agreement_id is None or c["agreement_id"] == agreement_id)
            and (document_id is None or c["addendum_document_id"] == document_id)]
    return sorted(rows, key=lambda c: (c.get("effective_date") or "9999", c.get("created_at") or "", c["id"]))


def current_terms(agreement: dict) -> dict[str, Any]:
    """The agreement's current values: record fields as stored; terms from the latest applied change, else the
    approved value from the agreement's source MOU."""
    values: dict[str, Any] = {f: _iso(agreement.get(f)) for f, kind in CHANGEABLE.items() if kind == "record"}
    source = agreement.get("source_document_id")
    if source:
        for f in list_records("extracted_fields"):
            if f["document_id"] == source and f["review_state"] == "approved" and CHANGEABLE.get(f["field"]) == "term":
                values[f["field"]] = f.get("approved_value")
    for change in _changes_for(agreement_id=agreement["id"]):
        if change["status"] == "approved" and change.get("applied_at") and change["kind"] == "modify" \
                and CHANGEABLE.get(change["field"]) == "term":
            values[change["field"]] = change["proposed_value"]
    return values


# ---- linking ----

class LinkRequest(BaseModel):
    agreement_id: str


@router.get("/documents/{document_id}/agreement-candidates")
def agreement_candidates(document_id: str) -> list[dict]:
    """Agreements this addendum might amend, with reasons. A suggestion only: a person must choose."""
    document = _document(document_id)
    fields = _proposals_for(document_id)["extracted_fields"]
    refs = {str(f.get("proposed_value") or "").strip().casefold() for f in fields if f["field"] == "reference_number"} - {""}
    candidates = []
    for agreement in list_records("agreements"):
        if document.get("partner_id") and agreement.get("partner_id") != document["partner_id"]:
            continue
        reasons = []
        reference = str(agreement.get("reference_number") or "").strip().casefold()
        if reference and any(reference in r or r in reference for r in refs):
            reasons.append("reference number appears in the addendum")
        if document.get("partner_id"):
            reasons.append("same partner")
        candidates.append({"agreement_id": agreement["id"], "title": agreement["title"], "reference_number": agreement.get("reference_number"),
                           "status": agreement.get("status"), "expiry_date": agreement.get("expiry_date"), "reasons": reasons})
    return sorted(candidates, key=lambda c: (-len(c["reasons"]), c["title"]))


@router.patch("/documents/{document_id}/link")
def link_addendum(document_id: str, payload: LinkRequest, request: Request) -> dict:
    """Choose the agreement an addendum amends. Discards undecided changes built against a previous choice."""
    document = _document(document_id)
    if document["kind"] != "addendum":
        raise HTTPException(status_code=422, detail="Only addenda are linked here; an MOU becomes its own agreement on approval")
    if document["status"] not in ("uploaded", "needs_review", "failed"):
        raise HTTPException(status_code=409, detail=f"The document is {document['status'].replace('_', ' ')}; its agreement can no longer change")
    agreement = get_record("agreements", payload.agreement_id)
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    if document.get("partner_id") and agreement.get("partner_id") != document["partner_id"]:
        raise HTTPException(status_code=422, detail="Agreement belongs to a different partner")
    existing = _changes_for(document_id=document_id)
    if any(c["status"] != "proposed" for c in existing) and document.get("agreement_id") != payload.agreement_id:
        raise HTTPException(status_code=409, detail="Some changes were already decided; reset them before choosing another agreement")
    if document.get("agreement_id") != payload.agreement_id:
        for change in existing:
            delete_record("agreement_changes", change["id"])
    warnings = [w for w in document.get("warnings", []) if not w.startswith("Choose the agreement this addendum amends")]
    updated = patch_record("documents", document_id, {"agreement_id": payload.agreement_id, "partner_id": agreement.get("partner_id"),
                                                      "warnings": warnings, "changes_built_at": None if existing else document.get("changes_built_at")})
    log_activity(actor_name=actor(request), event="addendum_linked",
                 summary=f"Linked addendum “{document['filename']}” to “{agreement['title']}”",
                 entity_type="document", entity_id=document_id, partner_id=agreement.get("partner_id"),
                 details={"agreement_id": payload.agreement_id})
    return updated


# ---- building changes ----

@router.post("/documents/{document_id}/changes")
def build_changes(document_id: str, request: Request) -> dict:
    """Compare the addendum's extracted values with the agreement's current values and propose changes."""
    document = _document(document_id)
    if document["kind"] != "addendum":
        raise HTTPException(status_code=422, detail="Changes are built for addenda only")
    if document["status"] != "needs_review":
        raise HTTPException(status_code=409, detail="Extract the addendum first; changes are built while it needs review")
    if not document.get("agreement_id"):
        raise HTTPException(status_code=409, detail="Choose the agreement this addendum amends first")
    existing = _changes_for(document_id=document_id)
    if any(c["status"] not in ("proposed", "unresolved") or c.get("reviewed_by") for c in existing):
        raise HTTPException(status_code=409, detail="Some changes were already decided; rebuilding would discard that review")
    for change in existing:
        delete_record("agreement_changes", change["id"])

    agreement = get_record("agreements", document["agreement_id"])
    proposals = _proposals_for(document_id)
    fields = proposals["extracted_fields"]
    amendment_date, effective_date = _single(fields, "execution_date"), _single(fields, "effective_date")
    prior = current_terms(agreement)
    others = [c for c in _changes_for(agreement_id=agreement["id"]) if c["addendum_document_id"] != document_id
              and c["status"] in ("proposed", "approved")]
    created, unchanged, skipped, n = [], [], [], 0
    when = now_iso()

    def add(**data) -> None:
        nonlocal n
        n += 1
        record = {"id": f"{document_id}-x{n:03d}", "agreement_id": agreement["id"], "addendum_document_id": document_id,
                  "created_at": when, "amendment_date": amendment_date, "effective_date": effective_date, "status": "proposed",
                  "reviewed_by": None, "reviewed_at": None, "applied_at": None, "note": None, **data}
        record = AgreementChange(**record).model_dump(mode="json")
        created.append(put_record("agreement_changes", record, record["id"]))

    for name, kind in CHANGEABLE.items():
        items = [f for f in fields if f["field"] == name and f.get("proposed_value") is not None]
        if not items:
            continue
        values = {_iso(f["proposed_value"]) for f in items}
        for f in items:
            if not f.get("evidence"):
                skipped.append({"field": name, "reason": "no source quote"})
                continue
            proposed = _iso(f["proposed_value"])
            if len(values) == 1 and proposed == _iso(prior.get(name)):
                unchanged.append(name)
                break
            note, status = None, "proposed"
            if len(values) > 1:
                note, status = "The addendum states different values for this term; decide which one governs.", "unresolved"
            clash = [c for c in others if c["field"] == name and c["kind"] == "modify"
                     and c.get("effective_date") == effective_date and _iso(c["proposed_value"]) != proposed]
            if clash:
                note, status = (f"Another addendum sets a different value with the same effective date ({clash[0]['addendum_document_id']}); "
                                "decide which one governs."), "unresolved"
            add(kind="modify", target="agreement", target_id=agreement["id"], field=name, prior_value=prior.get(name),
                proposed_value=proposed, evidence=f["evidence"], status=status, note=note)
            if len(values) == 1:
                break  # one change per field when the addendum is consistent
    for collection, (target, label) in ADD_TARGETS.items():
        for item in proposals[collection]:
            if not item.get("evidence"):
                skipped.append({"field": f"{target}: {item.get(label)}", "reason": "no source quote"})
                continue
            add(kind="add", target=target, target_id=item["id"], field="added", prior_value=None,
                proposed_value=str(item.get(label) or item.get("clause_type"))[:500], evidence=item["evidence"])
    patch_record("documents", document_id, {"changes_built_at": when})
    log_activity(actor_name=actor(request), event="changes_built",
                 summary=f"Compared “{document['filename']}” with “{agreement['title']}”: {len(created)} proposed changes",
                 entity_type="document", entity_id=document_id, partner_id=document.get("partner_id"),
                 details={"changes": len(created), "unchanged": unchanged})
    return {"changes": created, "unchanged": unchanged, "skipped": skipped,
            "amendment_date": amendment_date, "effective_date": effective_date}


@router.get("/documents/{document_id}/changes")
def document_changes(document_id: str) -> list[dict]:
    _document(document_id)
    return _changes_for(document_id=document_id)


# ---- deciding changes ----

class ChangeDecision(BaseModel):
    decision: Literal["approve", "reject", "unresolved", "reset"]
    proposed_value: ScalarValue = None  # correction; requires a note
    effective_date: date | None = None
    amendment_date: date | None = None
    note: str | None = Field(default=None, max_length=1000)


@router.patch("/agreement-changes/{change_id}")
def decide_change(change_id: str, payload: ChangeDecision, request: Request) -> dict:
    change = get_record("agreement_changes", change_id)
    if not change:
        raise HTTPException(status_code=404, detail="Change not found")
    document = _document(change["addendum_document_id"])
    if document["status"] != "needs_review":
        raise HTTPException(status_code=409, detail="The addendum is no longer under review; its changes are locked")
    updated = dict(change)
    note = (payload.note or "").strip() or None
    if payload.effective_date:
        updated["effective_date"] = payload.effective_date.isoformat()
    if payload.amendment_date:
        updated["amendment_date"] = payload.amendment_date.isoformat()
    if payload.proposed_value is not None:
        if change["kind"] != "modify" or payload.decision != "approve":
            raise HTTPException(status_code=422, detail="Only a modified term can be corrected, and only when approving")
        if not note:
            raise HTTPException(status_code=422, detail="Explain the correction in a note")
        value = payload.proposed_value
        if change["field"] in DATE_FIELDS:
            try:
                value = date.fromisoformat(str(value)).isoformat()
            except ValueError:
                raise HTTPException(status_code=422, detail=f"{change['field']} must be a date in YYYY-MM-DD format") from None
        updated["proposed_value"] = value
    if payload.decision == "reset":
        updated.update(status="proposed", reviewed_by=None, reviewed_at=None, note=note)
    else:
        if payload.decision == "unresolved" and not note:
            raise HTTPException(status_code=422, detail="Explain what is unresolved")
        if payload.decision == "approve":
            if not updated.get("effective_date"):
                raise HTTPException(status_code=422, detail="The effective date is not stated; enter it from the addendum before approving")
            if change["kind"] == "modify" and change["field"] in DATE_FIELDS:
                try:
                    date.fromisoformat(str(updated["proposed_value"]))
                except ValueError:
                    raise HTTPException(status_code=422, detail="The new value is not a date; correct it before approving") from None
            clash = [c for c in _changes_for(agreement_id=change["agreement_id"]) if c["id"] != change_id and c["status"] == "approved"
                     and c["kind"] == "modify" and c["field"] == change["field"] and c.get("effective_date") == updated["effective_date"]
                     and _iso(c["proposed_value"]) != _iso(updated["proposed_value"])]
            if clash:
                raise HTTPException(status_code=409, detail="A different value for this term with the same effective date is already approved; mark this change unresolved or reject it")
        updated.update(status={"approve": "approved", "reject": "rejected", "unresolved": "unresolved"}[payload.decision],
                       reviewed_by=actor(request), reviewed_at=now_iso(), note=note or updated.get("note"))
    try:
        validated = AgreementChange(**updated).model_dump(mode="json")
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=[e["msg"] for e in exc.errors()]) from None
    saved = put_record("agreement_changes", validated, change_id)
    log_activity(actor_name=actor(request), event=f"change_{payload.decision}",
                 summary=f"{ {'approve': 'Approved', 'reject': 'Rejected', 'unresolved': 'Marked unresolved', 'reset': 'Reopened'}[payload.decision]} "
                         f"change to {change['field'] if change['kind'] == 'modify' else change['target']} "
                         f"({_iso(change.get('prior_value')) or '—'} → {_iso(saved['proposed_value'])})",
                 entity_type="agreement", entity_id=change["agreement_id"], partner_id=document.get("partner_id"),
                 details={"change_id": change_id, "document_id": document["id"], "note": note})
    return saved


# ---- approving an addendum and applying changes ----

def addendum_blockers(document: dict) -> list[str]:
    blockers = []
    if not document.get("agreement_id"):
        blockers.append("Choose the agreement this addendum amends.")
    if not document.get("changes_built_at"):
        blockers.append("Compare the addendum with the agreement (build the proposed changes) first.")
    changes = _changes_for(document_id=document["id"])
    pending = sum(1 for c in changes if c["status"] == "proposed")
    if pending:
        blockers.append(f"{pending} proposed change{'s' if pending != 1 else ''} still need{'s' if pending == 1 else ''} a decision.")
    open_issues = sum(1 for i in _proposals_for(document["id"])["review_issues"] if i["status"] == "open")
    if open_issues:
        blockers.append(f"{open_issues} review issue{'s are' if open_issues != 1 else ' is'} still open (resolve or defer with a note).")
    return blockers


def approve_addendum(document: dict, who: str, owner: str) -> dict:
    """Apply the addendum's approved changes. Called by POST /documents/{id}/approve after the blockers pass."""
    from app.document_review import create_operational, ensure_project
    agreement = get_record("agreements", document["agreement_id"])
    partner_id = agreement["partner_id"]
    changes = _changes_for(document_id=document["id"])
    added = {"milestones": 0, "reports": 0, "finance": 0, "register_only": 0}
    collections = {"obligation": "obligations", "financial_term": "financial_terms", "clause": "clauses"}
    for change in changes:
        if change["kind"] != "add" or change["target"] not in collections:
            continue
        collection = collections[change["target"]]
        item = get_record(collection, change["target_id"])
        decision = {"approved": "approved", "rejected": "rejected"}.get(change["status"], "deferred")
        update: dict[str, Any] = {"review_state": decision, "reviewed_by": change.get("reviewed_by") or who,
                                  "reviewed_at": change.get("reviewed_at") or now_iso(), "agreement_id": agreement["id"]}
        if collection in ("financial_terms", "obligations"):
            update["partner_id"] = partner_id
        if collection == "obligations" and decision == "approved":
            project_id = ensure_project(agreement, item, owner)
            ref = create_operational(item, partner_id, project_id, owner)
            update.update(project_id=project_id, operational_ref=ref)
            added[ref["collection"] if ref else "register_only"] += 1
        patch_record(collection, item["id"], update)
    applied = apply_due_changes(who=who, agreement_ids={agreement["id"]}, approving=document["id"])
    return {"agreement_id": agreement["id"], "applied": applied, "added": added,
            "scheduled": [c["id"] for c in _changes_for(document_id=document["id"])
                          if c["status"] == "approved" and c["kind"] == "modify" and not c.get("applied_at")]}


def apply_due_changes(today: date | None = None, who: str = "System (effective date reached)",
                      agreement_ids: set[str] | None = None, approving: str | None = None) -> list[str]:
    """Bring agreements up to date with approved changes whose effective date has arrived. Idempotent.
    Only changes from approved addenda (or the one being approved now) count; the latest effective date wins."""
    today = today or business_today()
    approved_docs = {d["id"] for d in list_records("documents") if d.get("kind") == "addendum" and d.get("status") == "approved"}
    if approving:
        approved_docs.add(approving)
    by_agreement: dict[str, list[dict]] = {}
    for change in list_records("agreement_changes"):
        if change["status"] == "approved" and change["kind"] == "modify" and change["addendum_document_id"] in approved_docs \
                and (agreement_ids is None or change["agreement_id"] in agreement_ids):
            by_agreement.setdefault(change["agreement_id"], []).append(change)
    applied: list[str] = []
    for agreement_id, changes in by_agreement.items():
        due = [c for c in changes if c.get("effective_date") and c["effective_date"] <= today.isoformat()]
        newly = [c for c in due if not c.get("applied_at")]
        if not newly:
            continue
        agreement = get_record("agreements", agreement_id)
        if not agreement:
            continue
        latest: dict[str, dict] = {}
        for c in sorted(due, key=lambda c: (c["effective_date"], c.get("amendment_date") or "", c.get("reviewed_at") or "", c["id"])):
            latest[c["field"]] = c
        update = {f: c["proposed_value"] for f, c in latest.items() if CHANGEABLE.get(f) == "record"
                  and _iso(agreement.get(f)) != _iso(c["proposed_value"])}
        if "expiry_date" in update and agreement.get("status") in ("active", "expired"):
            update["status"] = "expired" if update["expiry_date"] < today.isoformat() else "active"
        if update:
            patch_record("agreements", agreement_id, update)
        stamp = now_iso()
        for c in newly:
            patch_record("agreement_changes", c["id"], {"applied_at": stamp})
            applied.append(c["id"])
        log_activity(actor_name=who, event="amendment_applied",
                     summary=f"Applied {len(newly)} approved change{'s' if len(newly) != 1 else ''} to “{agreement['title']}”"
                             + (f" ({', '.join(f'{k}: {v}' for k, v in update.items())})" if update else ""),
                     entity_type="agreement", entity_id=agreement_id, partner_id=agreement.get("partner_id"),
                     details={"changes": [c["id"] for c in newly], "update": update})
    return applied


@router.get("/agreements/{agreement_id}/history")
def agreement_history(agreement_id: str) -> dict:
    """Original values, every change in effective-date order, and the current effective values."""
    agreement = get_record("agreements", agreement_id)
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    changes = _changes_for(agreement_id=agreement_id)
    original: dict[str, Any] = {}
    for change in sorted(changes, key=lambda c: (c.get("created_at") or "", c["id"])):
        if change["kind"] == "modify":
            original.setdefault(change["field"], change.get("prior_value"))
    effective = current_terms(agreement)
    return {
        "agreement": agreement, "original": original, "effective": effective, "changes": changes,
        "counts": {s: sum(1 for c in changes if c["status"] == s) for s in ("proposed", "approved", "rejected", "unresolved")}
                  | {"applied": sum(1 for c in changes if c.get("applied_at")),
                     "scheduled": sum(1 for c in changes if c["status"] == "approved" and c["kind"] == "modify" and not c.get("applied_at"))},
    }
