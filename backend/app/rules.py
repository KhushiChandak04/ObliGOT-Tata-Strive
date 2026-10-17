from datetime import date
from typing import Any

def days_until(target_date: date, today: date | None = None) -> int:
    return (target_date - (today or date.today())).days

def build_deadline_finding(*, record_id: str, record_type: str, label: str, due_date: date | None, warning_days: int = 30, today: date | None = None) -> dict[str, Any] | None:
    if due_date is None:
        return {"id": f"missing-date:{record_type}:{record_id}", "record_id": record_id, "record_type": record_type, "issue": f"Missing due date: {label}", "priority": "medium", "evidence": ["The source record does not contain a due date."], "recommended_action": "Confirm the due date with the record owner and update the source record."}
    remaining = days_until(due_date, today)
    if remaining < 0:
        priority, issue = "high", f"Overdue: {label}"
    elif remaining <= warning_days:
        priority, issue = "medium", f"Due soon: {label}"
    else:
        return None
    return {"id": f"deadline:{record_type}:{record_id}", "record_id": record_id, "record_type": record_type, "issue": issue, "priority": priority, "due_date": due_date.isoformat(), "days_remaining": remaining, "evidence": [f"Recorded due date: {due_date.isoformat()}", f"Days remaining: {remaining}"], "recommended_action": "Confirm the owner and next step; update the record after follow-up."}

def scan_deadlines(collections: dict[str, list[dict]], today: date | None = None) -> list[dict[str, Any]]:
    """Inspect known due-date fields without inferring missing dates."""
    today = today or date.today()
    findings = []
    for collection_name, records in collections.items():
        for record in records:
            field = "expiry_date" if collection_name == "agreements" else "due_date"
            raw_date = record.get(field)
            parsed = None
            if isinstance(raw_date, date):
                parsed = raw_date
            elif isinstance(raw_date, str) and raw_date:
                try:
                    parsed = date.fromisoformat(raw_date[:10])
                except ValueError:
                    parsed = None
            if collection_name in {"agreements", "reports", "finance"}:
                result = build_deadline_finding(record_id=record.get("id", "unknown"), record_type=collection_name, label=record.get("title", record.get("name", collection_name)), due_date=parsed, today=today)
                if result:
                    result["partner_id"] = record.get("partner_id")
                    findings.append(result)
    return findings
