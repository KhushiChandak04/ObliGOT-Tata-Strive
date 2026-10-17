from datetime import date, datetime, timedelta, timezone
from app import rules
from app.rules import build_deadline_finding, days_until, scan_deadlines

def test_days_until():
    today = date(2026, 1, 1)
    assert days_until(date(2026, 1, 3), today) == 2
    assert days_until(date(2025, 12, 31), today) == -1

def test_overdue_rule():
    result = build_deadline_finding(record_id="r1", record_type="report", label="Monthly report", due_date=date(2026, 1, 9), today=date(2026, 1, 10))
    assert result is not None and result["priority"] == "high" and result["days_remaining"] == -1

def test_missing_date_is_data_quality_finding():
    result = build_deadline_finding(record_id="r2", record_type="agreement", label="MOU", due_date=None)
    assert result is not None and result["priority"] == "medium" and "Missing due date" in result["issue"]

def test_future_outside_warning_window_is_not_flagged():
    assert build_deadline_finding(record_id="r3", record_type="report", label="Annual report", due_date=date(2026, 3, 2), today=date(2026, 1, 1)) is None

TODAY = date(2026, 6, 1)
PAST = (TODAY - timedelta(days=10)).isoformat()
SOON = (TODAY + timedelta(days=10)).isoformat()

def ids(findings):
    return {f["record_id"] for f in findings}

def test_resolved_reports_are_not_flagged():
    reports = [
        {"id": "pending", "title": "Q1", "status": "due", "due_date": PAST},
        {"id": "submitted", "title": "Q2", "status": "submitted", "due_date": PAST},
        {"id": "accepted", "title": "Q3", "status": "accepted", "due_date": PAST},
    ]
    findings = scan_deadlines({"reports": reports}, today=TODAY)
    assert ids(findings) == {"pending"}
    assert findings[0]["issue"] == "Overdue: Q1" and "Recorded status: due" in findings[0]["evidence"]

def test_budgets_and_fund_receipts_are_not_flagged_for_missing_due_date():
    finance = [
        {"id": "budget", "title": "Budget", "record_type": "budget"},
        {"id": "receipt", "title": "Tranche", "record_type": "fund_received"},
        {"id": "invoice", "title": "Invoice", "record_type": "invoice", "status": "pending"},
        {"id": "paid", "title": "Paid invoice", "record_type": "invoice", "status": "Paid", "due_date": PAST},
        {"id": "uc", "title": "UC", "record_type": "utilization_certificate", "status": "pending", "due_date": SOON},
    ]
    findings = {f["record_id"]: f for f in scan_deadlines({"finance": finance}, today=TODAY)}
    assert set(findings) == {"invoice", "uc"}
    assert findings["invoice"]["issue"] == "Missing due date: Invoice"
    assert findings["uc"]["issue"] == "Due soon: UC"

def test_agreements_use_expiry_wording_and_skip_drafts_and_closed():
    agreements = [
        {"id": "active-soon", "title": "MOU A", "status": "active", "expiry_date": SOON},
        {"id": "expired", "title": "MOU B", "status": "expired", "expiry_date": PAST},
        {"id": "active-no-date", "title": "MOU C", "status": "active"},
        {"id": "draft", "title": "MOU D", "status": "draft"},
        {"id": "closed", "title": "MOU E", "status": "closed", "expiry_date": PAST},
    ]
    findings = {f["record_id"]: f for f in scan_deadlines({"agreements": agreements}, today=TODAY)}
    assert set(findings) == {"active-soon", "expired", "active-no-date"}
    assert findings["active-soon"]["issue"] == "Expiring soon: MOU A"
    assert findings["expired"]["issue"] == "Expired: MOU B" and findings["expired"]["priority"] == "high"
    assert findings["active-no-date"]["issue"] == "Missing expiry date: MOU C"

def test_business_today_uses_configured_offset(monkeypatch):
    monkeypatch.setattr(rules.settings, "business_utc_offset_minutes", 330)
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            # 20:00 UTC on 31 May is already 1 June in India.
            return datetime(2026, 5, 31, 20, 0, tzinfo=timezone.utc).astimezone(tz)
    monkeypatch.setattr(rules, "datetime", FrozenDatetime)
    assert rules.business_today() == date(2026, 6, 1)
