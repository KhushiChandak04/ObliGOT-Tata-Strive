"""Deterministic validators and new alert rules (Phase R2). Generic synthetic figures only."""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.engine import RuleConfig, evaluate
from app.main import app
from app.repository import put_record
from app.validators import parse_number, remove_duplicates, table_checks, tranche_checks

client = TestClient(app)
TODAY = date(2026, 10, 17)


def d(days):
    return (TODAY + timedelta(days=days)).isoformat()


def table(headers, rows, title="T"):
    return {"title": title, "headers": headers, "rows": [{"row_index": i, "page": 1, "cells": r, "verified": True} for i, r in enumerate(rows, 1)]}


def test_number_parsing_never_mixes_percentages_or_text():
    assert parse_number("₹23,80,000") == 2380000 and parse_number("18,04,000/-") == 1804000 and parse_number("Rs. 1,000.50") == 1000.5
    assert parse_number("10%") is None and parse_number("Total") is None and parse_number("") is None and parse_number("1-2") is None


def test_total_rows_are_checked_and_grand_totals_include_the_previous_total():
    ok = table(["Item", "Amount"], [["A", "100"], ["B", "250"], ["Total", "350"], ["Admin", "35"], ["Grand total", "385"]])
    assert table_checks(ok) == []
    bad = table(["Item", "Amount", "Share"], [["A", "100", "40%"], ["B", "250", "60%"], ["Total", "360", "100%"]])
    (code, message, field), = table_checks(bad)
    assert code == "ARITHMETIC_MISMATCH" and field == "Amount" and "stated 360" in message and "add up to 350" in message


def test_rows_with_unreadable_components_are_not_compared():
    assert table_checks(table(["Item", "Amount"], [["A", "100"], ["B", "[unreadable]"], ["Total", "999"]])) == []


def test_quarterly_amounts_against_the_total_column():
    t = table(["Location", "Q1", "Q2", "Q3", "Q4", "Total"], [["City A", "10", "10", "10", "10", "40"], ["City B", "5", "5", "5", "5", "25"]])
    issues = table_checks(t)
    assert len(issues) == 1 and "City B" in issues[0][1] and "add up to 20" in issues[0][1]


def test_quantity_times_unit_cost_against_line_total():
    t = table(["Course", "Students", "Cost per student", "Total"], [["Course 1", "40", "1,000", "40,000"], ["Course 2", "20", "500", "11,000"]])
    issues = table_checks(t)
    assert len(issues) == 1 and "20 × Cost per student 500 = 10,000" in issues[0][1]


def test_tranches_against_commitment_in_the_same_currency_only():
    terms = [{"term_type": "total_commitment", "amount": 1000, "currency": "INR"},
             {"term_type": "tranche", "amount": 400, "currency": "INR"}, {"term_type": "tranche", "amount": 500, "currency": "INR"},
             {"term_type": "tranche", "amount": 100, "currency": "USD"}, {"term_type": "tranche", "amount": 200, "currency": "USD"}]
    (code, message, _), = tranche_checks(terms)  # USD has no commitment to compare with
    assert code == "TRANCHE_TOTAL_MISMATCH" and "INR 900" in message and "INR 1,000" in message
    terms[2]["amount"] = 600
    assert tranche_checks(terms) == []


def test_exact_duplicates_are_removed_and_reported_without_blocking():
    clause = {"clause_type": "termination", "evidence": {"quote": "Either party may terminate"}}
    out = {"clauses": [dict(clause), dict(clause)], "financial_terms": [], "obligations": [], "programme_scope": []}
    assert remove_duplicates(out) == 1 and len(out["clauses"]) == 1


# ---- alert rules ----

AGREEMENT = {"id": "ag1", "partner_id": "p1", "title": "Synthetic MOU", "status": "active", "expiry_date": d(300),
             "signed_copy": "received", "owner": "Programme team"}


def tranche(**kw):
    return {"id": "t1", "agreement_id": "ag1", "partner_id": "p1", "term_type": "tranche", "description": "Second tranche",
            "amount": 1_804_000, "currency": "INR", "basis": "confirmed", "due_date": d(-10), "review_state": "approved", **kw}


def run(**records):
    return evaluate({"agreements": [AGREEMENT], **records}, TODAY, RuleConfig())


def test_missed_fund_release_alert_with_impact_separate_from_urgency():
    alert = next(a for a in run(financial_terms=[tranche()]) if a["rule_id"] == "FUND_RELEASE_OVERDUE")
    assert alert["days_remaining"] == -10 and alert["record_type"] == "financial_terms"
    evidence = {e["label"]: e["value"] for e in alert["evidence"]}
    assert evidence["Amount"] == "1,804,000.00 INR" and evidence["Receipts recorded against this term"] == 0
    p = alert["priority"]
    assert p["impact"] == 15 and p["urgency"] == 60  # 5 recorded amount + 10 material; 50 base + 10 days overdue
    assert any(f["kind"] == "impact" and f["label"].startswith("Material amount") for f in p["factors"])


def test_fund_release_rules_respect_receipts_review_and_currency():
    receipt = {"id": "f1", "record_type": "fund_received", "status": "received", "financial_term_id": "t1", "partner_id": "p1"}
    assert not [a for a in run(financial_terms=[tranche()], finance=[receipt]) if a["rule_id"].startswith("FUND_RELEASE")]
    assert not [a for a in run(financial_terms=[tranche(review_state="proposed")]) if a["rule_id"].startswith("FUND_RELEASE")]
    soon = next(a for a in run(financial_terms=[tranche(due_date=d(5))]) if a["rule_id"] == "FUND_RELEASE_DUE_SOON")
    assert soon["days_remaining"] == 5
    usd = next(a for a in run(financial_terms=[tranche(currency="USD")]) if a["rule_id"] == "FUND_RELEASE_OVERDUE")
    assert not any(f["label"].startswith("Material amount") for f in usd["priority"]["factors"])  # never converted
    no_date = run(financial_terms=[tranche(due_date=None)])
    assert not [a for a in no_date if a["rule_id"].startswith("FUND_RELEASE")]  # no invented deadline


def test_unresolved_amendment_raises_an_alert():
    change = {"id": "c1", "agreement_id": "ag1", "field": "expiry_date", "prior_value": "2026-11-30", "proposed_value": "2027-02-28",
              "effective_date": "2026-10-01", "status": "unresolved", "note": "Two addenda disagree"}
    alert = next(a for a in run(agreement_changes=[change]) if a["rule_id"] == "AMENDMENT_UNRESOLVED")
    assert alert["partner_id"] == "p1" and {e["label"]: e["value"] for e in alert["evidence"]}["Proposed value"] == "2027-02-28"
    assert not [a for a in run(agreement_changes=[{**change, "status": "approved"}]) if a["rule_id"] == "AMENDMENT_UNRESOLVED"]


def test_new_rules_reach_the_alerts_api():
    put_record("agreements", {**AGREEMENT, "source_label": "user"}, "ag1")
    put_record("financial_terms", tranche(due_date=(date.today() - timedelta(days=3)).isoformat()), "t1")
    rules = {a["rule_id"] for a in client.get("/api/alerts").json()["alerts"] if a["record_id"] in ("t1", "ag1")}
    assert "FUND_RELEASE_OVERDUE" in rules


def test_receipt_can_be_linked_only_to_an_approved_term_of_the_same_partner():
    put_record("financial_terms", tranche(partner_id="demo-001"), "t9")
    base = {"partner_id": "demo-001", "record_type": "fund_received", "title": "Tranche 2 receipt", "amount": 1804000, "status": "received"}
    assert client.post("/api/finance", json={**base, "financial_term_id": "nope"}).status_code == 404
    assert client.post("/api/finance", json={**base, "partner_id": "demo-002", "financial_term_id": "t9"}).status_code == 422
    created = client.post("/api/finance", json={**base, "financial_term_id": "t9"})
    assert created.status_code == 201 and created.json()["financial_term_id"] == "t9"