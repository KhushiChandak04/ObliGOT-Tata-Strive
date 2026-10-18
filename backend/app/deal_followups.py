"""Follow-ups on pipeline deals and on projects: schedule one ("follow-up needed in N days") and mark it completed.

Dates are set by the server on the IST business date, so the alert that fires when a follow-up is overdue
(OPPORTUNITY_NEXT_STEP_OVERDUE for deals, PROJECT_FOLLOWUP_OVERDUE/_DUE_SOON for projects) and the tracker on the
Pipeline page work from the same deterministic values. Every follow-up stays in the record's `followup_log`.
"""
from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.models import Opportunity, Project
from app.repository import get_record, put_record
from app.reviews import actor, log_activity
from app.rules import business_today

router = APIRouter(tags=["pipeline"])


class ScheduleFollowup(BaseModel):
    in_days: int = Field(ge=0, le=365)


KINDS = {"opportunities": (Opportunity, "Opportunity", "title"), "projects": (Project, "Project", "name")}


def _record(record_id: str, collection: str) -> dict:
    record = get_record(collection, record_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"{KINDS[collection][1]} not found")
    return record


def _save(record: dict, collection: str) -> dict:
    model = KINDS[collection][0]
    return put_record(collection, model.model_validate(record).model_dump(mode="json")
                      | {k: v for k, v in record.items() if k not in model.model_fields}, record["id"])


def _schedule(collection: str, record_id: str, in_days: int, request: Request) -> dict:
    record, today = _record(record_id, collection), business_today()
    due = today + timedelta(days=in_days)
    log = list(record.get("followup_log") or [])
    open_entry = next((e for e in reversed(log) if not e.get("done_on")), None)
    if open_entry:
        open_entry["due_date"] = due.isoformat()
    else:
        log.append({"scheduled_on": today.isoformat(), "due_date": due.isoformat(), "done_on": None})
    changes = {"followup_log": log}
    if collection == "opportunities":
        changes |= {"next_step_date": due.isoformat(), "updated_at": today.isoformat()}
    saved = _save({**record, **changes}, collection)
    name = record.get(KINDS[collection][2])
    log_activity(actor_name=actor(request), event="followup_scheduled", summary=f"Follow-up on “{name}” due {due.isoformat()}",
                 entity_type=collection[:-1], entity_id=record_id, partner_id=record.get("partner_id"))
    return saved


def _complete(collection: str, record_id: str, request: Request) -> dict:
    record, today = _record(record_id, collection), business_today()
    log = list(record.get("followup_log") or [])
    open_entry = next((e for e in reversed(log) if not e.get("done_on")), None)
    if open_entry:
        open_entry["done_on"] = today.isoformat()
    else:
        log.append({"scheduled_on": today.isoformat(), "due_date": today.isoformat(), "done_on": today.isoformat()})
    changes = {"followup_log": log}
    if collection == "opportunities":
        changes |= {"next_step_date": None, "last_followup_date": today.isoformat(), "updated_at": today.isoformat()}
    saved = _save({**record, **changes}, collection)
    log_activity(actor_name=actor(request), event="followup_completed", summary=f"Follow-up on “{record.get(KINDS[collection][2])}” completed",
                 entity_type=collection[:-1], entity_id=record_id, partner_id=record.get("partner_id"))
    return saved


@router.post("/projects/{project_id}/followup")
def schedule_project_followup(project_id: str, payload: ScheduleFollowup, request: Request) -> dict:
    """Follow-up on this project's status needed in N days."""
    return _schedule("projects", project_id, payload.in_days, request)


@router.post("/projects/{project_id}/followup/complete")
def complete_project_followup(project_id: str, request: Request) -> dict:
    return _complete("projects", project_id, request)


@router.post("/opportunities/{opportunity_id}/followup")
def schedule_followup(opportunity_id: str, payload: ScheduleFollowup, request: Request) -> dict:
    """Follow-up needed in N days. An open follow-up is rescheduled rather than duplicated."""
    return _schedule("opportunities", opportunity_id, payload.in_days, request)


@router.post("/opportunities/{opportunity_id}/followup/complete")
def complete_followup(opportunity_id: str, request: Request) -> dict:
    """Mark the open follow-up done today; this records the contact and clears the overdue alert."""
    return _complete("opportunities", opportunity_id, request)
