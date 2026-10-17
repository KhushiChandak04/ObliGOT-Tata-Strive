from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.config import settings

# Statuses that mean the obligation is resolved and must not raise a deadline finding.
RESOLVED_STATUSES = {
    "agreements": {"closed"},
    "reports": {"submitted", "accepted"},
    "finance": {"paid", "received", "submitted", "accepted", "completed", "closed", "cancelled"},
}
# Only these agreement statuses carry an operational expiry date.
EVALUATED_AGREEMENT_STATUSES = {"active", "expired"}
# Budgets and fund receipts have no due date by nature; only obligations are evaluated.
EVALUATED_FINANCE_TYPES = {"invoice", "utilization_certificate"}

def business_today() -> date:
    """Current date in the business timezone (default IST, UTC+05:30, which has no DST)."""
    offset = timezone(timedelta(minutes=settings.business_utc_offset_minutes))
    return datetime.now(offset).date()

def days_until(target_date: date, today: date | None = None) -> int:
    return (target_date - (today or business_today())).days

def build_deadline_finding(*, record_id: str, record_type: str, label: str, due_date: date | None, warning_days: int = 30, today: date | None = None, date_label: str = "due date") -> dict[str, Any] | None:
    is_expiry = date_label == "expiry date"
    if due_date is None:
        return {"id": f"missing-date:{record_type}:{record_id}", "record_id": record_id, "record_type": record_type, "issue": f"Missing {date_label}: {label}", "priority": "medium", "evidence": [f"The source record does not contain a {date_label}."], "recommended_action": f"Confirm the {date_label} with the record owner and update the source record."}
    remaining = days_until(due_date, today)
    if remaining < 0:
        priority, issue = "high", f"{'Expired' if is_expiry else 'Overdue'}: {label}"
    elif remaining <= warning_days:
        priority, issue = "medium", f"{'Expiring soon' if is_expiry else 'Due soon'}: {label}"
    else:
        return None
    return {"id": f"deadline:{record_type}:{record_id}", "record_id": record_id, "record_type": record_type, "issue": issue, "priority": priority, "due_date": due_date.isoformat(), "days_remaining": remaining, "evidence": [f"Recorded {date_label}: {due_date.isoformat()}", f"Days remaining: {remaining}"], "recommended_action": "Confirm the owner and next step; update the record after follow-up."}

def _parse_date(raw_date: Any) -> date | None:
    if isinstance(raw_date, date):
        return raw_date
    if isinstance(raw_date, str) and raw_date:
        try:
            return date.fromisoformat(raw_date[:10])
        except ValueError:
            return None
    return None

def _is_evaluated(collection_name: str, record: dict) -> bool:
    status = str(record.get("status") or "").strip().lower()
    if status in RESOLVED_STATUSES.get(collection_name, set()):
        return False
    if collection_name == "agreements":
        return status in EVALUATED_AGREEMENT_STATUSES
    if collection_name == "finance":
        return record.get("record_type") in EVALUATED_FINANCE_TYPES
    return collection_name == "reports"

def scan_deadlines(collections: dict[str, list[dict]], today: date | None = None) -> list[dict[str, Any]]:
    """Inspect known due-date fields of unresolved obligations without inferring missing dates."""
    today = today or business_today()
    findings = []
    for collection_name, records in collections.items():
        for record in records:
            if not _is_evaluated(collection_name, record):
                continue
            date_label = "expiry date" if collection_name == "agreements" else "due date"
            result = build_deadline_finding(record_id=record.get("id", "unknown"), record_type=collection_name, label=record.get("title", record.get("name", collection_name)), due_date=_parse_date(record.get(date_label.replace(" ", "_"))), today=today, date_label=date_label)
            if result:
                if record.get("status"):
                    result["evidence"].append(f"Recorded status: {record['status']}")
                result["partner_id"] = record.get("partner_id")
                findings.append(result)
    return findings
