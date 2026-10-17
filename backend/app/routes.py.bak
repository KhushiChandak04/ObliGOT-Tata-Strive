from datetime import date
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Query, UploadFile, File

from app.config import settings
from app.demo_data import PARTNERS, ACTIONS
from app.intelligence import analyze_context
from app.models import (
    ActionCreate, ActionItem, ActionUpdate, Agreement, AgreementCreate,
    AnalyzeRequest, AnalyzeResponse, FinanceCreate, FinanceRecord,
    FollowupCreate, FollowupUpdate, Partner, PartnerCreate, PartnerUpdate,
    Project, ProjectCreate, ReportCreate, ReportRecord,
)
from app.repository import (
    firestore_enabled, get_record, list_records, patch_record, put_record, delete_record,
)
from app.rules import build_deadline_finding, scan_deadlines

router = APIRouter()

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
    data.update({"updated_at": date.today().isoformat(), "source_label": "user"})
    return put_record("partners", data)

@router.get("/partners/{partner_id}", response_model=Partner, tags=["partners"])
def get_partner(partner_id: str) -> dict:
    record = get_record("partners", partner_id)
    if not record:
        raise HTTPException(status_code=404, detail="Partner not found")
    return record

@router.patch("/partners/{partner_id}", response_model=Partner, tags=["partners"])
def update_partner(partner_id: str, payload: PartnerUpdate) -> dict:
    changes = payload.model_dump(exclude_unset=True, mode="json")
    changes["updated_at"] = date.today().isoformat()
    record = patch_record("partners", partner_id, changes)
    if not record:
        raise HTTPException(status_code=404, detail="Partner not found")
    return record

@router.delete("/partners/{partner_id}", status_code=204, tags=["partners"])
def remove_partner(partner_id: str):
    if not delete_record("partners", partner_id):
        raise HTTPException(status_code=404, detail="Partner not found")
    return None

@router.get("/actions", response_model=list[ActionItem], tags=["actions"])
def list_actions(status: str | None = None) -> list[dict]:
    records = list_records("actions")
    return [r for r in records if r.get("status", "open") == status] if status else records

@router.post("/actions", response_model=ActionItem, status_code=201, tags=["actions"])
def create_action(payload: ActionCreate) -> dict:
    data = payload.model_dump(mode="json")
    if data.get("related_partner_id") and not get_record("partners", data["related_partner_id"]):
        raise HTTPException(status_code=404, detail="Related partner not found")
    data.update({"status": "open", "source_label": "user"})
    return put_record("actions", data)

@router.patch("/actions/{action_id}", response_model=ActionItem, tags=["actions"])
def update_action(action_id: str, payload: ActionUpdate) -> dict:
    record = patch_record("actions", action_id, payload.model_dump(exclude_unset=True, mode="json"))
    if not record:
        raise HTTPException(status_code=404, detail="Action not found")
    return record

@router.get("/agreements", response_model=list[Agreement], tags=["agreements"])
def list_agreements(partner_id: str | None = None) -> list[dict]:
    records = list_records("agreements")
    return [r for r in records if not partner_id or r.get("partner_id") == partner_id]

@router.post("/agreements", response_model=Agreement, status_code=201, tags=["agreements"])
def create_agreement(payload: AgreementCreate) -> dict:
    if not get_record("partners", payload.partner_id):
        raise HTTPException(status_code=404, detail="Partner not found")
    return put_record("agreements", {**payload.model_dump(mode="json"), "source_label": "user"})

@router.get("/projects", response_model=list[Project], tags=["projects"])
def list_projects(partner_id: str | None = None) -> list[dict]:
    records = list_records("projects")
    return [r for r in records if not partner_id or r.get("partner_id") == partner_id]

@router.post("/projects", response_model=Project, status_code=201, tags=["projects"])
def create_project(payload: ProjectCreate) -> dict:
    if not get_record("partners", payload.partner_id):
        raise HTTPException(status_code=404, detail="Partner not found")
    return put_record("projects", {**payload.model_dump(mode="json"), "source_label": "user"})

@router.get("/finance", response_model=list[FinanceRecord], tags=["finance"])
def list_finance(partner_id: str | None = None) -> list[dict]:
    records = list_records("finance")
    return [r for r in records if not partner_id or r.get("partner_id") == partner_id]

@router.post("/finance", response_model=FinanceRecord, status_code=201, tags=["finance"])
def create_finance(payload: FinanceCreate) -> dict:
    if not get_record("partners", payload.partner_id):
        raise HTTPException(status_code=404, detail="Partner not found")
    return put_record("finance", {**payload.model_dump(mode="json"), "source_label": "user"})

@router.get("/reports", response_model=list[ReportRecord], tags=["reports"])
def list_reports(partner_id: str | None = None) -> list[dict]:
    records = list_records("reports")
    return [r for r in records if not partner_id or r.get("partner_id") == partner_id]

@router.post("/reports", response_model=ReportRecord, status_code=201, tags=["reports"])
def create_report(payload: ReportCreate) -> dict:
    if not get_record("partners", payload.partner_id):
        raise HTTPException(status_code=404, detail="Partner not found")
    return put_record("reports", {**payload.model_dump(mode="json"), "source_label": "user"})

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

@router.get("/rules/deadline-preview", tags=["rules"])
def deadline_preview(record_id: str = "demo-record", record_type: str = "report", label: str = "Quarterly report", due_date: date | None = None) -> dict:
    return {"finding": build_deadline_finding(record_id=record_id, record_type=record_type, label=label, due_date=due_date),
            "note": "Preview only; use verified record dates for operational use."}

@router.post("/import/preview", tags=["import"])
async def import_preview(file: UploadFile = File(...)) -> dict:
    """Preview CSV/XLSX rows without writing to Firestore. Import commit needs explicit mapping/review."""
    filename = (file.filename or "").lower()
    raw = await file.read()
    if len(raw) > 5_000_000:
        raise HTTPException(status_code=413, detail="File is larger than the 5 MB preview limit")
    try:
        if filename.endswith(".csv"):
            import csv, io
            text = raw.decode("utf-8-sig")
            rows = list(csv.DictReader(io.StringIO(text)))
            headers = list(rows[0].keys()) if rows else []
        elif filename.endswith((".xlsx", ".xlsm")):
            from openpyxl import load_workbook
            import io
            workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
            sheet = workbook.active
            values = list(sheet.iter_rows(values_only=True))
            headers = [str(v) if v is not None else "" for v in values[0]] if values else []
            rows = [dict(zip(headers, [str(v) if v is not None else "" for v in row])) for row in values[1:101]]
        else:
            raise HTTPException(status_code=415, detail="Upload a .csv or .xlsx file")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded") from exc
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=400, detail="Could not read this file; check its format") from exc
    return {"filename": file.filename, "headers": headers, "preview_rows": rows[:100], "rows_previewed": min(len(rows), 100),
            "total_rows_detected": len(rows), "committed": False,
            "warning": "Preview only. Review column mappings, duplicates, and missing fields before importing."}
