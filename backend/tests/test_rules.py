from datetime import date, timedelta
from app.rules import build_deadline_finding, days_until

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
