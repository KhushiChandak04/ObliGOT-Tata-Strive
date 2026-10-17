from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.engine import RuleConfig, evaluate
from app.main import app

client = TestClient(app)


def create(**overrides):
    return client.post("/api/finance", json={"partner_id": "demo-001", "record_type": "invoice", "title": "Test invoice", **overrides})


@pytest.mark.parametrize("currency,ok", [("INR", True), ("USD", True), ("inr", False), ("RUPEES", False), ("", False)])
def test_currency_must_be_three_letter_code(currency, ok):
    assert (create(currency=currency).status_code == 201) is ok


def test_date_order_rules():
    assert create(issue_date="2026-06-10", due_date="2026-06-01").status_code == 422
    assert create(issue_date="2026-06-10", received_date="2026-06-09").status_code == 422
    body = create(issue_date="2026-06-01", due_date="2026-07-01").json()
    assert body["issue_date"] == "2026-06-01" and body["received_date"] is None
    receipt = client.post("/api/finance", json={"partner_id": "demo-001", "record_type": "fund_received", "title": "Tranche", "received_date": "2026-05-01", "status": "received"})
    assert receipt.status_code == 201 and receipt.json()["received_date"] == "2026-05-01"


def test_project_link_must_exist_and_match_partner():
    assert create(project_id="demo-project-001").status_code == 201
    assert create(project_id="missing").status_code == 404
    other = client.post("/api/projects", json={"name": "Other partner project", "partner_id": "demo-002"}).json()["id"]
    wrong = create(project_id=other)
    assert wrong.status_code == 422 and "different partner" in wrong.json()["detail"]
    assert client.patch("/api/finance/demo-finance-003", json={"project_id": other}).status_code == 422
    assert client.patch("/api/finance/demo-finance-003", json={"project_id": "missing"}).status_code == 404


def test_list_filters_by_record_type():
    types = {r["record_type"] for r in client.get("/api/finance", params={"record_type": "invoice"}).json()}
    assert types == {"invoice"}
    assert len(client.get("/api/finance", params={"partner_id": "demo-001", "record_type": "budget"}).json()) == 1


# ---- Invoice ageing rule ----------------------------------------------------------------------

TODAY = date(2026, 6, 1)


def invoice(**kw):
    return {"id": "i1", "partner_id": "p1", "title": "Invoice", "record_type": "invoice", "status": "raised", "amount": 100.0, "currency": "INR", **kw}


def fired(*records, config=None):
    return [a["rule_id"] for a in evaluate({"finance": list(records)}, TODAY, config)]


@pytest.mark.parametrize("age,expected", [(30, []), (31, ["INVOICE_AGING"]), (5, [])])
def test_ageing_window_boundary(age, expected):
    assert fired(invoice(issue_date=(TODAY - timedelta(days=age)).isoformat())) == expected


def test_ageing_alert_describes_age_not_overdue():
    alert = evaluate({"finance": [invoice(issue_date=(TODAY - timedelta(days=50)).isoformat())]}, TODAY)[0]
    assert alert["severity"] == "risk" and alert["days_remaining"] is None and alert["due_date"] is None
    computed = {e["label"]: e["value"] for e in alert["evidence"] if e["source"] == "computed"}
    assert computed == {"Days since issue": 50, "Ageing window (days)": 30}
    assert "not called overdue" in alert["rule_description"]


def test_due_date_takes_precedence_and_paid_invoices_never_age():
    old = (TODAY - timedelta(days=200)).isoformat()
    assert fired(invoice(issue_date=old, due_date=(TODAY - timedelta(days=3)).isoformat())) == ["INVOICE_OVERDUE"]
    assert fired(invoice(issue_date=old, status="paid")) == []
    assert fired(invoice(issue_date=old, status="draft")) == []
    assert fired(invoice()) == ["INVOICE_DUE_DATE_MISSING"]


def test_ageing_window_is_configurable():
    issued = (TODAY - timedelta(days=50)).isoformat()
    assert fired(invoice(issue_date=issued), config=RuleConfig(invoice_aging_days=60)) == []


def test_demo_invoice_now_reports_ageing():
    alerts = {a["record_id"]: a for a in client.get("/api/alerts").json()["alerts"]}
    assert alerts["demo-finance-003"]["rule_id"] == "INVOICE_AGING"
    assert client.patch("/api/rules/config", json={"invoice_aging_days": 2}).status_code == 422
