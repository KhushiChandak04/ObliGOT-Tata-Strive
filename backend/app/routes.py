from collections.abc import Callable
from datetime import date, timedelta
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import ValidationError

from app.config import settings
from app.intelligence import analyze_context
from app.models import (
    ActionCreate, ActionItem, ActionUpdate, Agreement, AgreementCreate,
    AnalyzeRequest, AnalyzeResponse, FinanceCreate, FinanceRecord,
    FollowupCreate, FollowupUpdate, Milestone, MilestoneCreate, Opportunity, OpportunityCreate, Partner, PartnerCreate, PartnerUpdate,
    Project, ProjectCreate, ReportCreate, ReportRecord,
)
from app.repository import (
    firestore_enabled, get_record, list_records, patch_record, put_record, delete_record,
)
from app.engine import RuleConfig, evaluate, rule_catalog
from app.reviews import ReviewCreate, TaskFromAlert, actor, attach_reviews, fingerprint, log_activity, now_iso
from app.rules import build_deadline_finding, business_today, scan_deadlines

router = APIRouter()

IMPORT_ENTITY_TYPES = {"agreements", "projects", "finance", "finance-records", "reports", "partners"}

@router.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "app": "ObliGOT API", "environment": settings.environment,
            "database": "firestore" if firestore_enabled() else "demo-memory-fallback",
            "ai_configured": bool(settings.gemini_api_key), "auth_required": settings.require_firebase_auth}

@router.get("/dashboard", tags=["dashboard"])
def dashboard() -> dict:
    partners = list_records("partners")
    actions = list_records("actions")
    agreements = list_records("agreements")
    projects = list_records("projects")
    finance = list_records("finance")
    reports = list_records("reports")
    return {
        "metrics": {
            "partners_total": len(partners),
            "partners_active": sum(p.get("status") == "active" for p in partners),
            "actions_open": sum(a.get("status", "open") not in {"done", "deferred"} for a in actions),
            "agreements_active": sum(a.get("status") == "active" for a in agreements),
            "projects_active": sum(p.get("status") == "active" for p in projects),
            "reports_pending": sum(r.get("status") not in {"submitted", "accepted"} for r in reports),
            "finance_records": len(finance),
        },
        "findings": scan_deadlines({"agreements": agreements, "projects": projects, "finance": finance, "reports": reports}),
        "as_of": business_today().isoformat(),
        "storage_mode": "firestore" if firestore_enabled() else "demo-memory-fallback",
        "demo_data_notice": "Any record marked source_label=demo is illustrative, not verified.",
    }

@router.get("/partners", response_model=list[Partner], tags=["partners"])
def list_partners(q: str | None = Query(default=None, max_length=160)) -> list[Partner]:
    records = list_records("partners")
    if q:
        needle = q.casefold()
        records = [p for p in records if needle in p.get("name", "").casefold() or needle in p.get("category", "").casefold() or needle in p.get("owner", "").casefold()]
    return records

@router.post("/partners", response_model=Partner, status_code=201, tags=["partners"])
def create_partner(payload: PartnerCreate) -> dict:
    data = payload.model_dump(mode="json")
    data.update({"updated_at": business_today().isoformat(), "source_label": "user"})
    return put_record("partners", data)

@router.get("/partners/{partner_id}", response_model=Partner, tags=["partners"])
def get_partner(partner_id: str) -> dict:
    record = get_record("partners", partner_id)
    if not record:
        raise HTTPException(status_code=404, detail="Partner not found")
    return record

def _patch_validated(collection: str, record_id: str, changes: dict, model, label: str) -> dict:
    """Apply explicit changes, including nulls that clear optional fields, and validate the merged record."""
    current = get_record(collection, record_id)
    if not current:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    merged = {**current, **changes}
    try:
        model.model_validate(merged)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return put_record(collection, merged, record_id)

@router.patch("/partners/{partner_id}", response_model=Partner, tags=["partners"])
def update_partner(partner_id: str, payload: PartnerUpdate) -> dict:
    changes = payload.model_dump(exclude_unset=True, mode="json")
    changes["updated_at"] = business_today().isoformat()
    return _patch_validated("partners", partner_id, changes, Partner, "Partner")

# Collections that reference a partner, and the field holding the reference.
PARTNER_LINKS = {
    "agreements": "partner_id", "projects": "partner_id", "finance": "partner_id",
    "reports": "partner_id", "opportunities": "partner_id", "milestones": "partner_id",
    "actions": "related_partner_id", "followups": "related_partner_id",
}

@router.delete("/partners/{partner_id}", status_code=204, tags=["partners"],
               responses={409: {"description": "Partner still has linked records"}})
def remove_partner(partner_id: str):
    if not get_record("partners", partner_id):
        raise HTTPException(status_code=404, detail="Partner not found")
    linked = {collection: count for collection, field in PARTNER_LINKS.items()
              if (count := sum(r.get(field) == partner_id for r in list_records(collection)))}
    if linked:
        summary = ", ".join(f"{collection}: {count}" for collection, count in linked.items())
        raise HTTPException(status_code=409, detail=f"Partner has linked records ({summary}). Reassign or delete them first.")
    if not delete_record("partners", partner_id):
        raise HTTPException(status_code=404, detail="Partner not found")
    return None

@router.get("/actions", response_model=list[ActionItem], tags=["actions"])
def list_actions(status: str | None = None, related_partner_id: str | None = None) -> list[dict]:
    records = list_records("actions")
    return [r for r in records
            if (not status or r.get("status", "open") == status)
            and (not related_partner_id or r.get("related_partner_id") == related_partner_id)]

@router.post("/actions", response_model=ActionItem, status_code=201, tags=["actions"])
def create_action(payload: ActionCreate, request: Request) -> dict:
    data = payload.model_dump(mode="json")
    if data.get("related_partner_id") and not get_record("partners", data["related_partner_id"]):
        raise HTTPException(status_code=404, detail="Related partner not found")
    data.update({"status": "open", "source_label": "user"})
    saved = put_record("actions", data)
    log_activity(actor_name=actor(request), event="task_created", summary=f"Created task “{saved['title']}”",
                 entity_type="actions", entity_id=saved["id"], partner_id=saved.get("related_partner_id"))
    return saved

@router.get("/actions/{action_id}", response_model=ActionItem, tags=["actions"])
def get_action(action_id: str) -> dict:
    record = get_record("actions", action_id)
    if not record:
        raise HTTPException(status_code=404, detail="Action not found")
    return record

@router.patch("/actions/{action_id}", response_model=ActionItem, tags=["actions"])
def update_action(action_id: str, payload: ActionUpdate, request: Request) -> dict:
    before = get_record("actions", action_id) or {}
    saved = _patch_validated("actions", action_id, payload.model_dump(exclude_unset=True, mode="json"), ActionItem, "Action")
    for field, event, verb in (("status", "task_status_changed", "status"), ("owner", "task_reassigned", "owner")):
        if before.get(field) != saved.get(field):
            log_activity(actor_name=actor(request), event=event,
                         summary=f"Changed {verb} of “{saved['title']}” from {before.get(field) or 'none'} to {saved.get(field) or 'none'}",
                         entity_type="actions", entity_id=action_id, partner_id=saved.get("related_partner_id"),
                         details={"field": field, "from": before.get(field), "to": saved.get(field)})
    return saved

@router.delete("/actions/{action_id}", status_code=204, tags=["actions"])
def delete_action(action_id: str):
    if not delete_record("actions", action_id):
        raise HTTPException(status_code=404, detail="Action not found")
    return None

@router.get("/agreements", response_model=list[Agreement], tags=["agreements"])
def list_agreements(partner_id: str | None = None,
                    expiring_within_days: int | None = Query(default=None, ge=0, le=3650)) -> list[dict]:
    """`expiring_within_days`: active agreements whose expiry falls between today (IST) and today + N days, inclusive."""
    records = [r for r in list_records("agreements") if not partner_id or r.get("partner_id") == partner_id]
    if expiring_within_days is not None:
        today = business_today()
        horizon = today + timedelta(days=expiring_within_days)
        records = [r for r in records if r.get("status") == "active" and r.get("expiry_date")
                   and today.isoformat() <= str(r["expiry_date"])[:10] <= horizon.isoformat()]
    return records

LINKS = {"project_id": ("projects", "Project"), "opportunity_id": ("opportunities", "Opportunity")}

def _check_links(data: dict, fields: tuple[str, ...]) -> None:
    """Each linked record must exist and must not belong to a different partner."""
    for field in fields:
        collection, label = LINKS[field]
        if not data.get(field):
            continue
        linked = get_record(collection, data[field])
        if not linked:
            raise HTTPException(status_code=404, detail=f"{label} not found")
        if linked.get("partner_id") and linked["partner_id"] != data["partner_id"]:
            raise HTTPException(status_code=422, detail=f"{label} belongs to a different partner")

@router.post("/agreements", response_model=Agreement, status_code=201, tags=["agreements"])
def create_agreement(payload: AgreementCreate) -> dict:
    if not get_record("partners", payload.partner_id):
        raise HTTPException(status_code=404, detail="Partner not found")
    data = payload.model_dump(mode="json")
    _check_agreement_links(data)
    return put_record("agreements", {**data, "source_label": "user"})

def _check_agreement_links(data: dict) -> None:
    _check_links(data, ("project_id", "opportunity_id"))

def _check_finance_links(data: dict) -> None:
    _check_links(data, ("project_id",))

async def _read_json_object(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Request body must be valid JSON") from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="Request body must be a JSON object")
    return body

async def _update_typed_record(collection: str, record_id: str, request: Request, schema, label: str,
                               extra: dict | None = None, check: Callable[[dict], None] | None = None) -> dict:
    changes = await _read_json_object(request)
    if not isinstance(changes, dict):
        raise HTTPException(status_code=422, detail="Request body must be a JSON object")
    current = get_record(collection, record_id)
    if not current:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    merged = {k: v for k, v in current.items() if k not in {"id", "source_label"}}
    merged.update(changes)
    try:
        validated = schema.model_validate(merged)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    data = validated.model_dump(mode="json")
    if data.get("partner_id") and not get_record("partners", data["partner_id"]):
        raise HTTPException(status_code=404, detail="Partner not found")
    if check:
        check(data)
    data["source_label"] = current.get("source_label", "user")
    data.update(extra or {})
    return put_record(collection, data, record_id)

@router.get("/agreements/{agreement_id}", response_model=Agreement, tags=["agreements"])
def get_agreement(agreement_id: str) -> dict:
    record = get_record("agreements", agreement_id)
    if not record:
        raise HTTPException(status_code=404, detail="Agreement not found")
    return record

@router.patch("/agreements/{agreement_id}", response_model=Agreement, tags=["agreements"])
async def update_agreement(agreement_id: str, request: Request) -> dict:
    return await _update_typed_record("agreements", agreement_id, request, AgreementCreate, "Agreement", check=_check_agreement_links)

@router.delete("/agreements/{agreement_id}", status_code=204, tags=["agreements"])
def delete_agreement(agreement_id: str):
    if not delete_record("agreements", agreement_id):
        raise HTTPException(status_code=404, detail="Agreement not found")
    return None

@router.get("/projects", response_model=list[Project], tags=["projects"])
def list_projects(partner_id: str | None = None) -> list[dict]:
    records = list_records("projects")
    return [r for r in records if not partner_id or r.get("partner_id") == partner_id]

# Records that reference a project through project_id.
PROJECT_LINKS = ("milestones", "agreements", "finance", "reports")

def _project_links(project_id: str) -> dict[str, int]:
    return {collection: count for collection in PROJECT_LINKS
            if (count := sum(r.get("project_id") == project_id for r in list_records(collection)))}

def _links_summary(linked: dict[str, int]) -> str:
    return ", ".join(f"{collection}: {count}" for collection, count in linked.items())

@router.post("/projects", response_model=Project, status_code=201, tags=["projects"])
def create_project(payload: ProjectCreate) -> dict:
    if payload.partner_id and not get_record("partners", payload.partner_id):
        raise HTTPException(status_code=404, detail="Partner not found")
    data = payload.model_dump(mode="json")
    data["source_label"] = "user"
    return put_record("projects", data)

@router.get("/projects/{project_id}", response_model=Project, tags=["projects"])
def get_project(project_id: str) -> dict:
    record = get_record("projects", project_id)
    if not record:
        raise HTTPException(status_code=404, detail="Project not found")
    return record

@router.patch("/projects/{project_id}", response_model=Project, tags=["projects"])
async def update_project(project_id: str, request: Request) -> dict:
    changes = await _read_json_object(request)
    allowed = {"partner_id", "name", "status", "owner", "start_date", "end_date", "milestone_summary"}
    unknown = set(changes) - allowed
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unsupported project fields: {', '.join(sorted(unknown))}")
    if "partner_id" in changes and changes["partner_id"] and not get_record("partners", changes["partner_id"]):
        raise HTTPException(status_code=404, detail="Partner not found")
    current = get_record("projects", project_id)
    if not current:
        raise HTTPException(status_code=404, detail="Project not found")
    merged = {k: v for k, v in current.items() if k in allowed}
    merged.update(changes)
    try:
        validated = ProjectCreate.model_validate(merged)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # Linked records carry the project's partner; moving the project would leave them pointing at the old partner.
    if validated.partner_id != current.get("partner_id") and (linked := _project_links(project_id)):
        raise HTTPException(status_code=409, detail=f"Project has linked records ({_links_summary(linked)}); its partner cannot be changed.")
    return put_record("projects", {**validated.model_dump(mode="json"), "source_label": current.get("source_label", "user")}, project_id)

@router.delete("/projects/{project_id}", status_code=204, tags=["projects"],
               responses={409: {"description": "Project still has linked records"}})
def delete_project(project_id: str):
    if not get_record("projects", project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    if linked := _project_links(project_id):
        raise HTTPException(status_code=409, detail=f"Project has linked records ({_links_summary(linked)}). Reassign or delete them first.")
    if not delete_record("projects", project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return None

@router.get("/milestones", response_model=list[Milestone], tags=["projects"])
def list_milestones(project_id: str | None = None, partner_id: str | None = None, status: str | None = None) -> list[dict]:
    records = list_records("milestones")
    return [r for r in records
            if (not project_id or r.get("project_id") == project_id)
            and (not partner_id or r.get("partner_id") == partner_id)
            and (not status or r.get("status") == status)]

def _milestone_record(validated: MilestoneCreate, source_label: str) -> dict:
    project = get_record("projects", validated.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {**validated.model_dump(mode="json"), "partner_id": project.get("partner_id"), "source_label": source_label}

@router.post("/milestones", response_model=Milestone, status_code=201, tags=["projects"])
def create_milestone(payload: MilestoneCreate) -> dict:
    return put_record("milestones", _milestone_record(payload, "user"))

@router.get("/milestones/{milestone_id}", response_model=Milestone, tags=["projects"])
def get_milestone(milestone_id: str) -> dict:
    record = get_record("milestones", milestone_id)
    if not record:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return record

@router.patch("/milestones/{milestone_id}", response_model=Milestone, tags=["projects"])
async def update_milestone(milestone_id: str, request: Request) -> dict:
    changes = await _read_json_object(request)
    changes.pop("partner_id", None)  # always derived from the project
    current = get_record("milestones", milestone_id)
    if not current:
        raise HTTPException(status_code=404, detail="Milestone not found")
    merged = {k: v for k, v in current.items() if k not in {"id", "source_label", "partner_id"}}
    merged.update(changes)
    try:
        validated = MilestoneCreate.model_validate(merged)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return put_record("milestones", _milestone_record(validated, current.get("source_label", "user")), milestone_id)

@router.delete("/milestones/{milestone_id}", status_code=204, tags=["projects"])
def delete_milestone(milestone_id: str):
    if not delete_record("milestones", milestone_id):
        raise HTTPException(status_code=404, detail="Milestone not found")
    return None

@router.get("/finance/{finance_id}", response_model=FinanceRecord, tags=["finance"])
def get_finance_record(finance_id: str) -> dict:
    record = get_record("finance", finance_id)
    if not record:
        raise HTTPException(status_code=404, detail="Finance record not found")
    return record

@router.patch("/finance/{finance_id}", response_model=FinanceRecord, tags=["finance"])
async def update_finance_record(finance_id: str, request: Request) -> dict:
    return await _update_typed_record("finance", finance_id, request, FinanceCreate, "Finance record", check=_check_finance_links)

@router.delete("/finance/{finance_id}", status_code=204, tags=["finance"])
def delete_finance_record(finance_id: str):
    if not delete_record("finance", finance_id):
        raise HTTPException(status_code=404, detail="Finance record not found")
    return None

@router.get("/finance", response_model=list[FinanceRecord], tags=["finance"])
def list_finance(partner_id: str | None = None, record_type: str | None = None) -> list[dict]:
    records = list_records("finance")
    return [r for r in records if (not partner_id or r.get("partner_id") == partner_id)
            and (not record_type or r.get("record_type") == record_type)]

@router.post("/finance", response_model=FinanceRecord, status_code=201, tags=["finance"])
def create_finance(payload: FinanceCreate) -> dict:
    if not get_record("partners", payload.partner_id):
        raise HTTPException(status_code=404, detail="Partner not found")
    data = payload.model_dump(mode="json")
    _check_finance_links(data)
    return put_record("finance", {**data, "source_label": "user"})

@router.get("/reports/{report_id}", response_model=ReportRecord, tags=["reports"])
def get_report(report_id: str) -> dict:
    record = get_record("reports", report_id)
    if not record:
        raise HTTPException(status_code=404, detail="Report not found")
    return record

@router.patch("/reports/{report_id}", response_model=ReportRecord, tags=["reports"])
async def update_report(report_id: str, request: Request) -> dict:
    return await _update_typed_record("reports", report_id, request, ReportCreate, "Report")

@router.delete("/reports/{report_id}", status_code=204, tags=["reports"])
def delete_report(report_id: str):
    if not delete_record("reports", report_id):
        raise HTTPException(status_code=404, detail="Report not found")
    return None

@router.get("/reports", response_model=list[ReportRecord], tags=["reports"])
def list_reports(partner_id: str | None = None) -> list[dict]:
    records = list_records("reports")
    return [r for r in records if not partner_id or r.get("partner_id") == partner_id]

@router.post("/reports", response_model=ReportRecord, status_code=201, tags=["reports"])
def create_report(payload: ReportCreate) -> dict:
    if not get_record("partners", payload.partner_id):
        raise HTTPException(status_code=404, detail="Partner not found")
    return put_record("reports", {**payload.model_dump(mode="json"), "source_label": "user"})

@router.get("/opportunities", response_model=list[Opportunity], tags=["pipeline"])
def list_opportunities(partner_id: str | None = None, stage: str | None = None) -> list[dict]:
    records = list_records("opportunities")
    return [r for r in records
            if (not partner_id or r.get("partner_id") == partner_id)
            and (not stage or r.get("stage") == stage)]

@router.post("/opportunities", response_model=Opportunity, status_code=201, tags=["pipeline"])
def create_opportunity(payload: OpportunityCreate) -> dict:
    if not get_record("partners", payload.partner_id):
        raise HTTPException(status_code=404, detail="Partner not found")
    return put_record("opportunities", {**payload.model_dump(mode="json"), "updated_at": business_today().isoformat(), "source_label": "user"})

@router.get("/opportunities/{opportunity_id}", response_model=Opportunity, tags=["pipeline"])
def get_opportunity(opportunity_id: str) -> dict:
    record = get_record("opportunities", opportunity_id)
    if not record:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return record

@router.patch("/opportunities/{opportunity_id}", response_model=Opportunity, tags=["pipeline"])
async def update_opportunity(opportunity_id: str, request: Request) -> dict:
    return await _update_typed_record("opportunities", opportunity_id, request, OpportunityCreate, "Opportunity",
                                      extra={"updated_at": business_today().isoformat()})

@router.delete("/opportunities/{opportunity_id}", status_code=204, tags=["pipeline"])
def delete_opportunity(opportunity_id: str):
    if not delete_record("opportunities", opportunity_id):
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return None

@router.get("/followups", tags=["follow-ups"])
def list_followups(status: str | None = None, related_partner_id: str | None = None) -> list[dict]:
    records = list_records("followups")
    return [r for r in records
            if (not status or r.get("status", "open") == status)
            and (not related_partner_id or r.get("related_partner_id") == related_partner_id)]

@router.get("/followups/{followup_id}", tags=["follow-ups"])
def get_followup(followup_id: str) -> dict:
    record = get_record("followups", followup_id)
    if not record:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    return record

@router.delete("/followups/{followup_id}", status_code=204, tags=["follow-ups"])
def delete_followup(followup_id: str):
    if not delete_record("followups", followup_id):
        raise HTTPException(status_code=404, detail="Follow-up not found")
    return None

@router.post("/intelligence/analyze", response_model=AnalyzeResponse, tags=["intelligence"])
async def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    partner_name = None
    context = payload.context
    if payload.partner_id:
        partner = get_record("partners", payload.partner_id)
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")
        partner_name = partner.get("name")
        context = f"Partner summary: {partner.get('summary', '')}\nAdditional context: {context}"
    return await analyze_context(context, partner_name)

@router.post("/followups", status_code=201, tags=["follow-ups"])
def create_followup(payload: FollowupCreate) -> dict:
    if payload.related_partner_id and not get_record("partners", payload.related_partner_id):
        raise HTTPException(status_code=404, detail="Related partner not found")
    data = {**payload.model_dump(mode="json"), "status": "open", "source_label": "user"}
    return put_record("followups", data)

@router.patch("/followups/{followup_id}", tags=["follow-ups"])
def update_followup(followup_id: str, payload: FollowupUpdate) -> dict:
    record = patch_record("followups", followup_id, payload.model_dump(mode="json"))
    if not record:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    return record

ALERT_SOURCES = ("agreements", "opportunities", "milestones", "reports", "finance", "actions")

def load_rule_config() -> RuleConfig:
    stored = get_record("config", "rules")
    return RuleConfig.model_validate({k: v for k, v in stored.items() if k != "id"}) if stored else RuleConfig()

def _current_alerts() -> tuple:
    config, today = load_rule_config(), business_today()
    alerts = evaluate({name: list_records(name) for name in ALERT_SOURCES}, today, config)
    reviews = {r["id"]: r for r in list_records("alert_reviews")}
    active, _ = attach_reviews(alerts, reviews, today)
    return today, config, alerts, active

@router.get("/alerts", tags=["rules"])
def list_alerts(partner_id: str | None = None, level: str | None = Query(default=None, pattern="^(high|medium|low)$"),
                category: str | None = None, include_reviewed: bool = False) -> dict:
    """Deterministic alerts computed from current records (nothing is stored). Sorted by priority score.

    By default, alerts dismissed or deferred (while their facts are unchanged) are left out; `include_reviewed=true`
    returns them too, flagged with `hidden_by_review`.
    """
    today, config, alerts, active = _current_alerts()
    matches = lambda a: ((not partner_id or a["partner_id"] == partner_id)
                         and (not level or a["priority"]["level"] == level)
                         and (not category or a["category"] == category))
    shown = [a for a in (alerts if include_reviewed else active) if matches(a)]
    return {
        "as_of": today.isoformat(),
        "config": config.model_dump(),
        "counts": {"total": len(shown), "by_level": {lvl: sum(a["priority"]["level"] == lvl for a in shown) for lvl in ("high", "medium", "low")},
                   "hidden_by_review": sum(a["hidden_by_review"] for a in alerts if matches(a))},
        "alerts": shown,
        "note": "Priority scores are an illustrative, transparent business rule, not a predictive model.",
    }

def _find_alert(alert_id: str) -> dict:
    today, _, alerts, _ = _current_alerts()
    for alert in alerts:
        if alert["id"] == alert_id:
            return alert
    raise HTTPException(status_code=404, detail="Alert is not currently raised; the record may have been resolved or changed.")

@router.post("/alerts/{alert_id}/review", tags=["rules"])
def review_alert(alert_id: str, payload: ReviewCreate, request: Request) -> dict:
    alert = _find_alert(alert_id)
    today = business_today()
    if payload.decision == "deferred" and not (today < payload.deferred_until <= today + timedelta(days=365)):
        raise HTTPException(status_code=422, detail="deferred_until must be after today and within 365 days")
    review = put_record("alert_reviews", {
        "decision": payload.decision, "deferred_until": payload.deferred_until.isoformat() if payload.deferred_until else None,
        "reason": (payload.reason or "").strip() or None, "note": (payload.note or "").strip() or None,
        "reviewer": actor(request), "reviewed_at": now_iso(), "fingerprint": fingerprint(alert), "task_id": None,
        "rule_id": alert["rule_id"], "rule_title": alert["rule_title"], "record_title": alert["record_title"],
        "record_type": alert["record_type"], "record_id": alert["record_id"], "partner_id": alert["partner_id"],
    }, alert_id)
    detail = {"deferred": f" until {review['deferred_until']}", "dismissed": f": {review['reason']}"}.get(payload.decision, "")
    log_activity(actor_name=review["reviewer"], event=f"alert_{payload.decision}",
                 summary=f"{payload.decision.capitalize()} “{alert['rule_title']}” for {alert['record_title']}{detail}",
                 entity_type=alert["record_type"], entity_id=alert["record_id"], partner_id=alert["partner_id"],
                 details={"alert_id": alert_id, "note": review["note"]})
    return {**alert, "review": review, "hidden_by_review": payload.decision in {"dismissed", "deferred"}}

@router.delete("/alerts/{alert_id}/review", status_code=204, tags=["rules"])
def clear_alert_review(alert_id: str, request: Request):
    review = get_record("alert_reviews", alert_id)
    if not review or not delete_record("alert_reviews", alert_id):
        raise HTTPException(status_code=404, detail="No review recorded for this alert")
    log_activity(actor_name=actor(request), event="alert_review_cleared", summary=f"Reopened “{review.get('rule_title', alert_id)}” for {review.get('record_title', review.get('record_id', 'record'))} (previously {review['decision']})",
                 entity_type=review.get("record_type", "alerts"), entity_id=review.get("record_id", alert_id), partner_id=review.get("partner_id"),
                 details={"alert_id": alert_id})
    return None

@router.post("/alerts/{alert_id}/task", status_code=201, tags=["rules"])
def create_task_from_alert(alert_id: str, payload: TaskFromAlert, request: Request) -> dict:
    alert = _find_alert(alert_id)
    open_task = next((a for a in list_records("actions") if a.get("source_alert_id") == alert_id and a.get("status") in {"open", "in_review"}), None)
    if open_task:
        raise HTTPException(status_code=409, detail=f"An open task already exists for this alert ({open_task['id']}).")
    who = actor(request)
    task = put_record("actions", {
        "title": payload.title or f"{alert['rule_title']}: {alert['record_title']}",
        "priority": payload.priority or alert["priority"]["level"], "status": "open",
        "due_date": payload.due_date.isoformat() if payload.due_date else None,
        "evidence": [f"{e['label']}: {e['value']}" for e in alert["evidence"]],
        "recommended_action": alert["recommended_action"], "related_partner_id": alert["partner_id"],
        "owner": payload.owner or alert["owner"], "source_alert_id": alert_id, "source_label": "user",
    })
    review = put_record("alert_reviews", {
        "decision": "task_created", "deferred_until": None, "reason": None, "note": None, "reviewer": who, "reviewed_at": now_iso(),
        "fingerprint": fingerprint(alert), "task_id": task["id"],
        "rule_id": alert["rule_id"], "rule_title": alert["rule_title"], "record_title": alert["record_title"],
        "record_type": alert["record_type"], "record_id": alert["record_id"], "partner_id": alert["partner_id"],
    }, alert_id)
    log_activity(actor_name=who, event="task_created_from_alert",
                 summary=f"Created task “{task['title']}” for {task['owner']} from alert “{alert['rule_title']}”",
                 entity_type="actions", entity_id=task["id"], partner_id=alert["partner_id"], details={"alert_id": alert_id})
    return {"task": task, "alert": {**alert, "review": review, "hidden_by_review": False}}

@router.get("/activities", tags=["activity"])
def list_activities(partner_id: str | None = None, entity_id: str | None = None, limit: int = Query(default=50, ge=1, le=500)) -> list[dict]:
    rows = [r for r in list_records("activities")
            if (not partner_id or r.get("partner_id") == partner_id) and (not entity_id or r.get("entity_id") == entity_id)]
    return sorted(rows, key=lambda r: (r.get("at", ""), r.get("seq", 0)), reverse=True)[:limit]

@router.get("/rules", tags=["rules"])
def list_rules() -> list[dict]:
    return rule_catalog()

@router.get("/rules/config", response_model=RuleConfig, tags=["rules"])
def get_rule_config() -> RuleConfig:
    return load_rule_config()

@router.patch("/rules/config", response_model=RuleConfig, tags=["rules"])
async def update_rule_config(request: Request) -> RuleConfig:
    changes = await _read_json_object(request)
    unknown = set(changes) - set(RuleConfig.model_fields)
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown rule settings: {', '.join(sorted(unknown))}")
    try:
        config = RuleConfig.model_validate({**load_rule_config().model_dump(), **changes})
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    put_record("config", config.model_dump(), "rules")
    return config

@router.get("/rules/deadline-preview", tags=["rules"])
def deadline_preview(record_id: str = "demo-record", record_type: str = "report", label: str = "Quarterly report", due_date: date | None = None) -> dict:
    return {"finding": build_deadline_finding(record_id=record_id, record_type=record_type, label=label, due_date=due_date),
            "note": "Preview only; use verified record dates for operational use."}

@router.post("/import/preview", tags=["import"])
async def import_preview(request: Request) -> dict:
    """Validate JSON row batches or preview CSV/XLSX uploads without writing records."""
    import csv
    import io
    content_type = request.headers.get("content-type", "").lower()
    filename = None
    headers: list[str] = []
    if "application/json" in content_type:
        payload = await _read_json_object(request)
        entity_type = payload.get("entity_type")
        if entity_type not in IMPORT_ENTITY_TYPES:
            raise HTTPException(status_code=422, detail="Unsupported entity_type")
        rows = payload.get("rows")
        if not isinstance(rows, list) or not rows or len(rows) > 500:
            raise HTTPException(status_code=422, detail="rows must contain between 1 and 500 records")
    elif "multipart/form-data" in content_type:
        form = await request.form()
        entity_type = form.get("entity_type", "projects")
        if entity_type not in IMPORT_ENTITY_TYPES:
            raise HTTPException(status_code=422, detail="Unsupported entity_type")
        upload = form.get("file")
        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(status_code=422, detail="A file field is required")
        filename = getattr(upload, "filename", None)
        raw = await upload.read()
        if len(raw) > 5_000_000:
            raise HTTPException(status_code=413, detail="File is larger than the 5 MB preview limit")
        try:
            if (filename or "").lower().endswith(".csv"):
                decoded = raw.decode("utf-8-sig")
                reader = csv.DictReader(io.StringIO(decoded))
                headers = list(reader.fieldnames or [])
                rows = list(reader)[:500]
            elif (filename or "").lower().endswith((".xlsx", ".xlsm")):
                from openpyxl import load_workbook
                workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
                sheet = workbook.active
                iterator = sheet.iter_rows(values_only=True)
                first = next(iterator, None)
                headers = [str(v).strip() if v is not None else "" for v in (first or [])]
                rows = [dict(zip(headers, [str(v) if v is not None else "" for v in row])) for row in iterator]
                rows = rows[:500]
                workbook.close()
            else:
                raise HTTPException(status_code=415, detail="Upload a .csv or .xlsx file")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded") from exc
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Could not read this file; check its format") from exc
    else:
        raise HTTPException(status_code=415, detail="Send JSON rows or upload a CSV/XLSX file")

    seen: set[str] = set()
    valid_rows: list[dict] = []
    issues: list[dict] = []
    for idx, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            row = {}
        name = str(row.get("name", "") or "").strip()
        errors: list[str] = []
        if not name:
            errors.append("Missing required field: name")
        elif name.casefold() in seen:
            errors.append("Duplicate name in this batch")
        if name:
            seen.add(name.casefold())
        amount = row.get("amount")
        if amount not in (None, ""):
            try:
                if float(amount) < 0:
                    errors.append("Amount cannot be negative")
            except (TypeError, ValueError):
                errors.append("Amount must be numeric")
        item = {"row": idx, "name": name or None, "valid": not errors, "issues": errors}
        (valid_rows if not errors else issues).append(item)

    return {
        "entity_type": entity_type,
        "filename": filename,
        "headers": headers,
        "preview_rows": rows[:100],
        "rows_previewed": min(len(rows), 100),
        "total_rows_detected": len(rows),
        "total_rows": len(rows),
        "valid_count": len(valid_rows),
        "invalid_count": len(issues),
        "valid_rows": valid_rows,
        "issues": issues,
        "committed": False,
        "warning": "Preview only. Review mappings and validation issues before importing; no records were written.",
    }
