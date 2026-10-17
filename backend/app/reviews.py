"""Human review state for computed alerts, and the activity (audit) log.

Alerts are recomputed on every request; only people's decisions are stored, keyed by alert id. A review records a
fingerprint of the alert's stored evidence values. If those facts change (for example a new due date), the
review no longer applies and the alert is shown as unreviewed again.
"""
import hashlib
import itertools
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

from fastapi import Request
from pydantic import BaseModel, Field, model_validator

from app.config import settings
from app.repository import put_record

ReviewDecision = Literal["acknowledged", "deferred", "dismissed"]
DEMO_ACTOR = "Demo user"
# Tie-breaker for activities logged within the same clock tick by this process.
_sequence = itertools.count()


class ReviewCreate(BaseModel):
    decision: ReviewDecision
    deferred_until: date | None = None
    reason: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def decision_details(self):
        if self.decision == "deferred" and self.deferred_until is None:
            raise ValueError("deferred_until is required when deferring")
        if self.decision != "deferred" and self.deferred_until is not None:
            raise ValueError("deferred_until is only allowed when deferring")
        if self.decision == "dismissed" and len((self.reason or "").strip()) < 5:
            raise ValueError("A reason of at least 5 characters is required to dismiss an alert")
        return self


class TaskFromAlert(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=240)
    owner: str | None = Field(default=None, min_length=2, max_length=120)
    due_date: date | None = None
    priority: Literal["high", "medium", "low"] | None = None


def now_iso() -> str:
    offset = timezone(timedelta(minutes=settings.business_utc_offset_minutes))
    return datetime.now(offset).isoformat(timespec="microseconds")


def actor(request: Request) -> str:
    """Signed-in user's email when Firebase auth is enforced; a labelled demo identity otherwise."""
    user = getattr(request.state, "firebase_user", None) or {}
    return user.get("email") or user.get("uid") or DEMO_ACTOR


def fingerprint(alert: dict[str, Any]) -> str:
    """Hash of the alert's stored facts. Computed values (e.g. days overdue) are excluded because they change daily."""
    facts = [[e["label"], e["value"]] for e in alert["evidence"] if e["source"] == "record"]
    payload = json.dumps({"rule": alert["rule_id"], "due": alert["due_date"], "facts": facts}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def attach_reviews(alerts: list[dict], reviews: dict[str, dict], today: date) -> tuple[list[dict], int]:
    """Annotate alerts with their current review. Returns (active alerts, number hidden by a current review).

    Hidden: dismissed (while facts are unchanged) and deferred until a date after today.
    Acknowledged and task_created alerts stay active so they remain visible until the record is fixed.
    """
    active, hidden = [], 0
    for alert in alerts:
        review = reviews.get(alert["id"])
        if review and review.get("fingerprint") != fingerprint(alert):
            alert["review"] = None
            alert["previous_review"] = {**review, "stale_reason": "The underlying record changed after this review."}
        else:
            alert["review"] = review
        current = alert["review"]
        is_hidden = bool(current) and (
            current["decision"] == "dismissed"
            or (current["decision"] == "deferred" and current.get("deferred_until") and current["deferred_until"] > today.isoformat())
        )
        alert["hidden_by_review"] = is_hidden
        if is_hidden:
            hidden += 1
        else:
            active.append(alert)
    return active, hidden


def log_activity(*, actor_name: str, event: str, summary: str, entity_type: str, entity_id: str,
                 partner_id: str | None, details: dict[str, Any] | None = None) -> dict:
    return put_record("activities", {
        "at": now_iso(), "actor": actor_name, "event": event, "summary": summary,
        "entity_type": entity_type, "entity_id": entity_id, "partner_id": partner_id, "details": details or {},
        "seq": next(_sequence),
    }, f"activity-{uuid4().hex[:12]}")
