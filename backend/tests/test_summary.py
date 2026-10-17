"""Backend-computed dashboard summary and options (Phase R3): values come from current records only."""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app import repository
from app.main import app
from app.models import FINANCE_STATUSES
from app.repository import put_record

client = TestClient(app)


def summary():
    return client.get("/api/dashboard/summary").json()


def test_summary_matches_the_alerts_api():
    s, alerts = summary(), client.get("/api/alerts").json()
    assert s["alerts"]["open"] == alerts["counts"]["total"]
    assert s["alerts"]["by_level"] == alerts["counts"]["by_level"]
    assert sum(s["alerts"]["by_category"].values()) == s["alerts"]["open"]
    assert s["alerts"]["overdue"] == sum(1 for a in alerts["alerts"] if a["days_remaining"] is not None and a["days_remaining"] < 0)


def test_summary_changes_when_records_change():
    before = summary()
    milestone = next(m for m in repository.list_records("milestones") if m["status"] == "in_progress")
    client.patch(f"/api/milestones/{milestone['id']}", json={"status": "completed", "completed_date": date.today().isoformat()})
    after = summary()
    assert after["alerts"]["open"] == before["alerts"]["open"] - 1


def test_empty_store_gives_zeros_not_sample_numbers():
    for records in repository._COLLECTIONS.values():
        records.clear()
    s = summary()
    assert s["alerts"]["open"] == 0 and s["partners"] == {"total": 0, "active": 0}
    assert s["finance"]["unpaid_invoices"] == [] and all(v == [] for v in s["coverage"].values())


def test_amounts_are_summed_per_currency_and_concept_only():
    repository._COLLECTIONS["finance"].clear()
    base = {"partner_id": "demo-001", "record_type": "invoice", "status": "sent", "source_label": "user", "title": "I"}
    put_record("finance", {**base, "amount": 100, "currency": "INR"}, "i1")
    put_record("finance", {**base, "amount": 50, "currency": "INR"}, "i2")
    put_record("finance", {**base, "amount": 10, "currency": "USD"}, "i3")
    put_record("finance", {**base, "record_type": "budget", "status": "approved", "amount": 999, "currency": "INR"}, "b1")
    assert summary()["finance"]["unpaid_invoices"] == [{"currency": "INR", "amount": 150, "count": 2}, {"currency": "USD", "amount": 10, "count": 1}]


def test_overdue_fund_release_is_counted_from_approved_terms_without_receipts():
    put_record("financial_terms", {"agreement_id": "a", "partner_id": "demo-001", "term_type": "tranche", "description": "T2",
                                   "amount": 500, "currency": "INR", "due_date": (date.today() - timedelta(days=2)).isoformat(),
                                   "review_state": "approved"}, "t1")
    put_record("financial_terms", {"term_type": "tranche", "description": "T3", "amount": 700, "currency": "INR",
                                   "due_date": (date.today() - timedelta(days=2)).isoformat(), "review_state": "proposed"}, "t2")
    assert summary()["finance"]["fund_releases_overdue"] == [{"currency": "INR", "amount": 500, "count": 1}]


def test_options_come_from_the_schema_and_current_records():
    put_record("programme_scope", {"dimension": "state", "value": "State A (synthetic)", "review_state": "approved"}, "s1")
    put_record("programme_scope", {"dimension": "state", "value": "State B (synthetic)", "review_state": "proposed"}, "s2")
    o = client.get("/api/options").json()
    assert o["enums"]["finance_status"] == {k: list(v) for k, v in FINANCE_STATUSES.items()}
    assert [p["id"] for p in o["partners"]] and {p["id"] for p in o["partners"]} == {p["id"] for p in repository.list_records("partners")}
    assert o["states"] == ["State A (synthetic)"]  # only approved data
