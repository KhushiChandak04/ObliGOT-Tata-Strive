from datetime import date
from typing import Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from app.domain_store import ENTITY_TYPES, create_record, delete_record, get_record, list_records, update_record

router = APIRouter()

class RecordCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=200)
    partner_id: str | None = None
    status: str = Field(default="planned", min_length=2, max_length=50)
    owner: str | None = Field(default=None, max_length=120)
    due_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    amount: float | None = Field(default=None, ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    description: str = Field(default="", max_length=3000)
    reference: str | None = None

class RecordPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=2, max_length=200)
    partner_id: str | None = None
    status: str | None = None
    owner: str | None = None
    due_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    amount: float | None = Field(default=None, ge=0)
    currency: str | None = None
    description: str | None = None
    reference: str | None = None

class ImportPreview(BaseModel):
    entity_type: str
    rows: list[dict[str, Any]] = Field(min_length=1, max_length=500)

def check_type(entity_type: str):
    if entity_type not in ENTITY_TYPES:
        raise HTTPException(status_code=404, detail="Unknown record type")

@router.get("/dashboard/summary", tags=["dashboard"])
def dashboard_summary():
    return {"as_of": date.today().isoformat(), "counts": {kind: len(list_records(kind)) for kind in sorted(ENTITY_TYPES)}, "note": "Counts include persistent domain records only."}

@router.get("/import/preview", tags=["import"])
def import_help():
    return {"supported_entity_types": sorted(ENTITY_TYPES), "max_rows": 500, "required_field": "name", "commits_data": False}

@router.post("/import/preview", tags=["import"])
def preview_import(payload: ImportPreview):
    check_type(payload.entity_type)
    seen, valid, issues = set(), [], []
    for idx, row in enumerate(payload.rows, 1):
        name = str(row.get("name", "")).strip()
        errors = []
        if not name:
            errors.append("Missing required field: name")
        elif name.casefold() in seen:
            errors.append("Duplicate name in this batch")
        if name:
            seen.add(name.casefold())
        amount = row.get("amount")
        if amount not in (None, ""):
            try:
                if float(amount) < 0: errors.append("Amount cannot be negative")
            except (TypeError, ValueError):
                errors.append("Amount must be numeric")
        entry = {"row": idx, "name": name or None, "valid": not errors, "issues": errors}
        (valid if not errors else issues).append(entry)
    return {"entity_type": payload.entity_type, "total_rows": len(payload.rows), "valid_count": len(valid), "invalid_count": len(issues), "valid_rows": valid, "issues": issues, "committed": False}

@router.get("/{entity_type}", tags=["domain records"])
def list_domain(entity_type: str, q: str | None = Query(default=None, max_length=160)):
    check_type(entity_type)
    rows = list_records(entity_type)
    if q:
        needle = q.casefold()
        rows = [r for r in rows if needle in str(r.get("name", "")).casefold() or needle in str(r.get("partner_id", "")).casefold()]
    return rows

@router.post("/{entity_type}", status_code=201, tags=["domain records"])
def create_domain(entity_type: str, payload: RecordCreate):
    check_type(entity_type)
    data = payload.model_dump(exclude_none=True, mode="json")
    if data.get("start_date") and data.get("end_date") and data["end_date"] < data["start_date"]:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    return create_record(entity_type, data)

@router.get("/{entity_type}/{record_id}", tags=["domain records"])
def get_domain(entity_type: str, record_id: str):
    check_type(entity_type)
    result = get_record(entity_type, record_id)
    if result is None: raise HTTPException(status_code=404, detail="Record not found")
    return result

@router.patch("/{entity_type}/{record_id}", tags=["domain records"])
def patch_domain(entity_type: str, record_id: str, payload: RecordPatch):
    check_type(entity_type)
    changes = payload.model_dump(exclude_unset=True, mode="json")
    result = update_record(entity_type, record_id, changes)
    if result is None: raise HTTPException(status_code=404, detail="Record not found")
    return result

@router.delete("/{entity_type}/{record_id}", status_code=204, tags=["domain records"])
def remove_domain(entity_type: str, record_id: str):
    check_type(entity_type)
    if not delete_record(entity_type, record_id): raise HTTPException(status_code=404, detail="Record not found")
    return None
