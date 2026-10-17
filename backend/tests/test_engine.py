from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.engine import RULES, RuleConfig, evaluate, rule_catalog
from app.main import app

TODAY = date(2026, 6, 1)
d = lambda n: (TODAY + timedelta(days=n)).isoformat()


def run(config=None, **records):
    return evaluate(records, TODAY, config)


def rules_fired(alerts):
    return sorted(a["rule_id"] for a in alerts)


def evidence(alert):
    return {e["label"]: e["value"] for e in alert["evidence"]}


# ---- Agreements -------------------------------------------------------------------------------

def agreement(**kw):
    return {"id": "a1", "partner_id": "p1", "title": "MOU", "status": "active", "signed_copy": "received", "renewal_status": "none", **kw}


@pytest.mark.parametrize("days,expected", [(0, ["MOU_EXPIRING"]), (60, ["MOU_EXPIRING"]), (61, []), (-1, ["MOU_EXPIRED_NO_RENEWAL"])])
def test_mou_expiry_window_boundaries(days, expected):
    assert rules_fired(run(agreements=[agreement(expiry_date=d(days))])) == expected


@pytest.mark.parametrize("renewal", ["renewed", "not_renewing"])
def test_final_renewal_status_suppresses_expiry_rules(renewal):
    assert run(agreements=[agreement(expiry_date=d(10), renewal_status=renewal)]) == []
    assert run(agreements=[agreement(expiry_date=d(-10), renewal_status=renewal)]) == []


def test_renewal_in_progress_still_alerts_with_lower_priority():
    plain = run(agreements=[agreement(expiry_date=d(10))])[0]["priority"]
    in_progress = run(agreements=[agreement(expiry_date=d(10), renewal_status="in_progress")])[0]["priority"]
    assert in_progress["score"] == plain["score"] - 10
    assert {"label": "Renewal already in progress", "points": -10} in in_progress["factors"]


@pytest.mark.parametrize("status", ["draft", "under_review", "closed"])
def test_non_active_agreements_do_not_alert(status):
    assert run(agreements=[agreement(status=status, expiry_date=d(5), signed_copy="unknown")]) == []


def test_expired_status_past_expiry_alerts_but_future_does_not():
    assert rules_fired(run(agreements=[agreement(status="expired", expiry_date=d(-3))])) == ["MOU_EXPIRED_NO_RENEWAL"]
    assert run(agreements=[agreement(status="expired", expiry_date=d(3))]) == []


def test_signed_copy_and_missing_expiry():
    alerts = run(agreements=[agreement(signed_copy="pending")])
    assert rules_fired(alerts) == ["AGREEMENT_EXPIRY_MISSING", "MOU_SIGNED_COPY_MISSING"]
    signed = next(a for a in alerts if a["rule_id"] == "MOU_SIGNED_COPY_MISSING")
    assert evidence(signed)["Signed copy"] == "pending"


def test_mou_window_is_configurable():
    config = RuleConfig(mou_expiry_warning_days=90)
    assert rules_fired(run(config, agreements=[agreement(expiry_date=d(75))])) == ["MOU_EXPIRING"]


# ---- Pipeline ---------------------------------------------------------------------------------

def opportunity(**kw):
    return {"id": "o1", "partner_id": "p1", "title": "Opp", "stage": "proposal", "owner": "Ops", "updated_at": d(-1), **kw}


@pytest.mark.parametrize("stage,fires", [("approval", True), ("agreement", True), ("proposal", False), ("active", False)])
def test_approved_without_agreement(stage, fires):
    assert ("APPROVED_NO_AGREEMENT" in rules_fired(run(opportunities=[opportunity(stage=stage, next_step_date=d(5))]))) is fires


def test_linked_agreement_clears_approved_without_agreement():
    alerts = run(opportunities=[opportunity(stage="approval", next_step_date=d(5))],
                 agreements=[agreement(status="draft", opportunity_id="o1")])
    assert "APPROVED_NO_AGREEMENT" not in rules_fired(alerts)


def test_next_step_overdue_and_stale():
    assert rules_fired(run(opportunities=[opportunity(next_step_date=d(-2))])) == ["OPPORTUNITY_NEXT_STEP_OVERDUE"]
    assert run(opportunities=[opportunity(next_step_date=d(0))]) == []
    assert run(opportunities=[opportunity(updated_at=d(-30))]) == []  # exactly the window: not stale
    assert rules_fired(run(opportunities=[opportunity(updated_at=d(-31))])) == ["OPPORTUNITY_STALE"]
    assert run(opportunities=[opportunity(stage="closed", next_step_date=d(-9), updated_at=d(-400))]) == []


# ---- Milestones, reports, finance, tasks -----------------------------------------------------

@pytest.mark.parametrize("status,days,expected", [
    ("in_progress", -1, ["MILESTONE_OVERDUE"]), ("planned", 30, ["MILESTONE_DUE_SOON"]), ("planned", 31, []),
    ("completed", -5, []), ("cancelled", -5, []), ("missed", -5, []),
])
def test_milestones(status, days, expected):
    assert rules_fired(run(milestones=[{"id": "m1", "project_id": "x", "partner_id": "p1", "title": "M", "status": status, "due_date": d(days)}])) == expected


@pytest.mark.parametrize("status,due,expected", [
    ("due", d(-1), ["REPORT_OVERDUE"]), ("planned", d(10), ["REPORT_DUE_SOON"]), ("overdue", None, ["REPORT_DUE_DATE_MISSING"]),
    ("submitted", d(-10), []), ("accepted", None, []),
])
def test_reports(status, due, expected):
    assert rules_fired(run(reports=[{"id": "r1", "partner_id": "p1", "title": "R", "status": status, "due_date": due}])) == expected


@pytest.mark.parametrize("kind,status,due,expected", [
    ("utilization_certificate", "pending", d(-1), ["UC_OVERDUE"]),
    ("utilization_certificate", "rejected", d(5), ["UC_DUE_SOON"]),
    ("utilization_certificate", "pending", None, ["UC_DUE_DATE_MISSING"]),
    ("utilization_certificate", "accepted", d(-1), []),
    ("invoice", "sent", d(-1), ["INVOICE_OVERDUE"]),
    ("invoice", "raised", d(3), ["INVOICE_DUE_SOON"]),
    ("invoice", "raised", None, ["INVOICE_DUE_DATE_MISSING"]),
    ("invoice", "paid", d(-30), []),
    ("invoice", "draft", d(-30), []),
    ("budget", "approved", None, []),
    ("fund_received", "expected", d(-5), []),
])
def test_finance(kind, status, due, expected):
    record = {"id": "f1", "partner_id": "p1", "title": "F", "record_type": kind, "status": status, "due_date": due, "amount": 100.0, "currency": "INR"}
    assert rules_fired(run(finance=[record])) == expected


def test_invoice_without_due_date_is_never_called_overdue():
    alert = run(finance=[{"id": "f1", "partner_id": "p1", "title": "Old invoice", "record_type": "invoice", "status": "raised", "amount": 5.0}])[0]
    assert alert["rule_id"] == "INVOICE_DUE_DATE_MISSING" and alert["days_remaining"] is None and alert["severity"] == "missing_data"


@pytest.mark.parametrize("status,days,expected", [("open", -1, ["TASK_OVERDUE"]), ("in_review", -1, ["TASK_OVERDUE"]), ("open", 0, []), ("done", -5, []), ("deferred", -5, [])])
def test_tasks(status, days, expected):
    assert rules_fired(run(actions=[{"id": "t1", "title": "T", "status": status, "due_date": d(days)}])) == expected


# ---- Priority, evidence, determinism ---------------------------------------------------------

def test_priority_breakdown_sums_to_score_and_levels():
    alert = run(reports=[{"id": "r1", "partner_id": "p1", "title": "R", "status": "due", "due_date": d(-45)}])[0]
    assert alert["priority"]["factors"] == [{"label": "Base: overdue", "points": 50}, {"label": "45 days overdue (max 30)", "points": 30}]
    assert alert["priority"]["score"] == 80 and alert["priority"]["level"] == "high"
    soon = run(reports=[{"id": "r1", "partner_id": "p1", "title": "R", "status": "due", "due_date": d(5)}])[0]["priority"]
    assert soon["score"] == 45 and soon["level"] == "medium"
    for a in run(reports=[{"id": "r1", "partner_id": "p1", "title": "R", "status": "due", "due_date": d(25)}]):
        assert a["priority"]["score"] == sum(f["points"] for f in a["priority"]["factors"]) and a["priority"]["level"] == "low"


def test_cross_record_bump_needs_two_other_alerts_for_same_partner():
    reports = lambda n, partner="p1": [{"id": f"r{i}", "partner_id": partner, "title": "R", "status": "due", "due_date": d(-1)} for i in range(n)]
    two = run(reports=reports(2))
    assert all(len(a["related_alert_ids"]) == 1 and a["priority"]["score"] == 51 for a in two)
    three = run(reports=reports(3))
    assert all(len(a["related_alert_ids"]) == 2 and a["priority"]["score"] == 61 for a in three)
    unrelated = run(reports=[{"id": f"r{i}", "partner_id": f"p{i}", "title": "R", "status": "due", "due_date": d(-1)} for i in range(3)])
    assert all(a["related_alert_ids"] == [] for a in unrelated)


def test_evidence_uses_record_values_and_marks_computed_values():
    alert = run(reports=[{"id": "r1", "partner_id": "p1", "title": "R", "report_type": "monthly", "status": "due", "due_date": d(-6)}])[0]
    assert alert["evidence"] == [
        {"label": "Report type", "value": "monthly", "source": "record"},
        {"label": "Status", "value": "due", "source": "record"},
        {"label": "Due date", "value": d(-6), "source": "record"},
        {"label": "Days overdue", "value": 6, "source": "computed"},
    ]
    assert alert["id"] == "REPORT_OVERDUE:reports:r1"


def test_same_input_gives_identical_output():
    records = {"reports": [{"id": f"r{i}", "partner_id": "p1", "title": "R", "status": "due", "due_date": d(-i)} for i in range(5)],
               "agreements": [agreement(expiry_date=d(4), signed_copy="unknown")]}
    assert evaluate(records, TODAY) == evaluate(records, TODAY)
    scores = [a["priority"]["score"] for a in evaluate(records, TODAY)]
    assert scores == sorted(scores, reverse=True)


def test_catalog_covers_every_rule():
    assert {r["rule_id"] for r in rule_catalog()} == set(RULES)


# ---- API --------------------------------------------------------------------------------------

client = TestClient(app)


def test_alerts_endpoint_with_demo_data_and_filters():
    body = client.get("/api/alerts").json()
    assert body["counts"]["total"] == len(body["alerts"]) > 0
    rule_ids = {a["rule_id"] for a in body["alerts"]}
    assert {"MILESTONE_OVERDUE", "REPORT_OVERDUE", "UC_DUE_SOON", "MOU_EXPIRING", "MOU_SIGNED_COPY_MISSING"} <= rule_ids
    assert all(a["source_label"] == "demo" for a in body["alerts"])
    high = client.get("/api/alerts", params={"level": "high"}).json()["alerts"]
    assert high and all(a["priority"]["level"] == "high" for a in high)
    assert client.get("/api/alerts", params={"partner_id": "demo-003"}).json()["alerts"] == []
    assert client.get("/api/alerts", params={"level": "urgent"}).status_code == 422


def test_resolving_a_record_clears_its_alert():
    alert_ids = lambda: {a["id"] for a in client.get("/api/alerts").json()["alerts"]}
    assert "REPORT_OVERDUE:reports:demo-report-001" in alert_ids()
    client.patch("/api/reports/demo-report-001", json={"status": "submitted"})
    assert "REPORT_OVERDUE:reports:demo-report-001" not in alert_ids()


def test_rule_config_get_patch_and_validation():
    assert client.get("/api/rules/config").json() == RuleConfig().model_dump()
    assert client.patch("/api/rules/config", json={"mou_expiry_warning_days": 0}).status_code == 422
    assert client.patch("/api/rules/config", json={"unknown": 5}).status_code == 422
    assert client.get("/api/alerts", params={"category": "agreements"}).json()["counts"]["total"] == 2
    updated = client.patch("/api/rules/config", json={"mou_expiry_warning_days": 14})
    assert updated.status_code == 200 and updated.json()["mou_expiry_warning_days"] == 14
    # The demo MOU expires in 21 days, so it drops out of a 14-day window.
    assert "MOU_EXPIRING" not in {a["rule_id"] for a in client.get("/api/alerts").json()["alerts"]}
    assert client.get("/api/rules").status_code == 200
