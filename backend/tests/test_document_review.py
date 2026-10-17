"""Review and approval gate (Step P3b). Synthetic documents; Gemini replaced by a fake.

Proves: unapproved extraction creates no operational records or alerts; only approved values cross the gate;
approval creates the agreement and obligations, and the deterministic rules engine then raises alerts.
"""
import json
import re

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app import document_routes
from app.config import settings
from app.main import app
from app.repository import get_record, list_records

client = TestClient(app)

# Dates are relative to the fixed seed only through the text; business "today" is the real IST date, so the
# inception report (30 Sep 2026) is overdue and the expiry (30 Nov 2026) is inside the 60-day MOU window when
# these tests run in Oct 2026. Tests that depend on it compute expectations from the API, not hard-coded counts.
PAGES = [
    "SYNTHETIC MEMORANDUM OF UNDERSTANDING with Sample Learning Collective (fictional). Reference: SYN-REV-002.",
    "This MOU is effective from 1 December 2025 and remains valid until 30 November 2026.",
    "The partner shall submit an inception report by 30 September 2026. A utilization certificate is due by "
    "31 December 2026. Milestone: first cohort of 50 learners enrolled by 15 January 2027. The first tranche "
    "will be released on signing. Either party may terminate with 30 days written notice.",
]


def item(**kw):
    return kw


OUTPUT = {
    "fields": [
        item(field="partner_name", value_as_written="Sample Learning Collective (fictional)", page=1, quote="Sample Learning Collective (fictional)"),
        item(field="reference_number", value_as_written="SYN-REV-002", page=1, quote="Reference: SYN-REV-002"),
        item(field="effective_date", value_as_written="1 December 2025", normalized_value="2025-12-01", page=2, quote="effective from 1 December 2025"),
        item(field="expiry_date", value_as_written="30 November 2026", normalized_value="2026-11-30", page=2, quote="valid until 30 November 2026"),
    ],
    "obligations": [
        item(obligation_type="progress_report", title="Inception report", frequency="once", due_date="2026-09-30", page=3,
             quote="submit an inception report by 30 September 2026"),
        item(obligation_type="utilization_certificate", title="Utilization certificate", due_date="2026-12-31", page=3,
             quote="A utilization certificate is due by 31 December 2026"),
        item(obligation_type="milestone", title="First cohort of 50 learners enrolled", due_date="2027-01-15", page=3,
             quote="first cohort of 50 learners enrolled by 15 January 2027"),
        item(obligation_type="fund_release", title="First tranche on signing", page=3, quote="The first tranche will be released on signing"),
    ],
    "clauses": [item(clause_type="termination", summary="30 days' notice", page=3, quote="Either party may terminate with 30 days written notice.")],
}


@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "document_storage_dir", str(tmp_path / "store"))
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")


def make_pdf(pages):
    doc = pymupdf.open()
    for text in pages:
        doc.new_page().insert_textbox(pymupdf.Rect(50, 50, 550, 800), text, fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data


def extracted(monkeypatch, output=OUTPUT, pages=PAGES, **form) -> dict:
    async def generate(prompt):
        present = {int(n) for n in re.findall(r"<<<PAGE (\d+)>>>", prompt)}
        return json.dumps({k: [i for i in v if i["page"] in present] for k, v in output.items()})
    monkeypatch.setattr(document_routes, "gemini_generate", generate)
    doc = client.post("/api/documents", data={"kind": "mou", **form},
                      files={"file": ("synthetic-review.pdf", make_pdf(pages), "application/pdf")}).json()
    client.post(f"/api/documents/{doc['id']}/extract")
    assert client.get(f"/api/documents/{doc['id']}").json()["status"] == "needs_review"
    return doc


def proposals(doc_id):
    return client.get(f"/api/documents/{doc_id}/extraction").json()


def decide(doc_id, collection, item_id, decision="approve", **body):
    return client.patch(f"/api/documents/{doc_id}/proposals/{collection}/{item_id}", json={"decision": decision, **body})


def approve_all(doc_id, skip=()):
    data = proposals(doc_id)
    for collection in ("extracted_fields", "clauses", "financial_terms", "obligations", "programme_scope"):
        for row in data[collection]:
            if row["id"] not in skip and row["review_state"] in ("proposed", "needs_review"):
                assert decide(doc_id, collection, row["id"], note="Checked against the PDF").status_code == 200
    for issue in data["review_issues"]:
        client.patch(f"/api/documents/{doc_id}/issues/{issue['id']}", json={"status": "resolved", "resolution": "Checked"})


def alerts_for(record_ids):
    return [a for a in client.get("/api/alerts").json()["alerts"] if a["record_id"] in record_ids]


def test_unapproved_extraction_creates_nothing_operational(monkeypatch):
    counts = {c: len(list_records(c)) for c in ("partners", "agreements", "projects", "milestones", "reports", "finance")}
    alerts = client.get("/api/alerts").json()["counts"]["total"]
    doc = extracted(monkeypatch, partner_id="demo-003")
    check = client.get(f"/api/documents/{doc['id']}/approval-check").json()
    assert check["ready"] is False and any("still need" in b for b in check["blockers"])
    assert {c: len(list_records(c)) for c in counts} == counts
    assert client.get("/api/alerts").json()["counts"]["total"] == alerts
    response = client.post(f"/api/documents/{doc['id']}/approve", json={})
    assert response.status_code == 409 and response.json()["detail"]["blockers"]


def test_field_decisions_corrections_and_validation(monkeypatch):
    doc = extracted(monkeypatch, partner_id="demo-003")
    fields = {f["field"]: f for f in proposals(doc["id"])["extracted_fields"]}
    expiry = fields["expiry_date"]
    assert decide(doc["id"], "extracted_fields", expiry["id"], value="30/11/2026").status_code == 422
    corrected = decide(doc["id"], "extracted_fields", expiry["id"], value="2026-11-29").json()
    assert corrected["approved_value"] == "2026-11-29" and corrected["proposed_value"] == "2026-11-30"
    assert corrected["review_state"] == "approved" and corrected["reviewed_by"] == "Demo user" and corrected["reviewed_at"]
    reset = decide(doc["id"], "extracted_fields", expiry["id"], "reset").json()
    assert reset["review_state"] == "needs_review" and reset["approved_value"] is None and reset["reviewed_by"] is None
    assert decide(doc["id"], "extracted_fields", expiry["id"], "defer").status_code == 422  # defer needs a reason
    deferred = decide(doc["id"], "extracted_fields", expiry["id"], "defer", note="Waiting for the signed copy").json()
    assert deferred["review_state"] == "deferred" and deferred["approved_value"] is None
    rejected = decide(doc["id"], "extracted_fields", fields["reference_number"]["id"], "reject").json()
    assert rejected["review_state"] == "rejected" and rejected["approved_value"] is None
    assert decide(doc["id"], "nonsense", "x").status_code == 404
    assert decide(doc["id"], "extracted_fields", "doc-x-f001").status_code == 404
    events = [a["summary"] for a in client.get("/api/activities", params={"limit": 4}).json()]
    assert events[0].startswith("Rejected “reference_number”") and events[1].startswith("Deferred “expiry_date”")


def test_unverified_evidence_needs_a_note_to_approve(monkeypatch):
    output = {"fields": [item(field="partner_name", value_as_written="Sample Learning Collective (fictional)", page=2,
                              quote="Sample Learning Collective (fictional)")]}  # quote is on page 1, not 2
    doc = extracted(monkeypatch, output=output, partner_id="demo-003")
    field = proposals(doc["id"])["extracted_fields"][0]
    assert field["evidence"]["verified"] is False
    response = decide(doc["id"], "extracted_fields", field["id"])
    assert response.status_code == 422 and "not verified" in response.json()["detail"]
    assert decide(doc["id"], "extracted_fields", field["id"], note="Name checked on page 1").status_code == 200


def test_corrections_on_other_proposals(monkeypatch):
    doc = extracted(monkeypatch, partner_id="demo-003")
    report = next(o for o in proposals(doc["id"])["obligations"] if o["title"] == "Inception report")
    assert decide(doc["id"], "obligations", report["id"], changes={"partner_id": "demo-001"}).status_code == 422
    assert decide(doc["id"], "obligations", report["id"], "reject", changes={"title": "x"}).status_code == 422
    assert decide(doc["id"], "obligations", report["id"], changes={"due_date": "not a date"}).status_code == 422
    saved = decide(doc["id"], "obligations", report["id"], changes={"owner": "Programme Team (fictional)"}).json()
    assert saved["owner"] == "Programme Team (fictional)" and saved["review_state"] == "approved"


def test_issue_resolution_requires_a_note(monkeypatch):
    output = {**OUTPUT, "fields": OUTPUT["fields"][:3]}  # no expiry → MISSING_FIELD issue
    doc = extracted(monkeypatch, output=output, partner_id="demo-003")
    issue = proposals(doc["id"])["review_issues"][0]
    url = f"/api/documents/{doc['id']}/issues/{issue['id']}"
    assert client.patch(url, json={"status": "resolved"}).status_code == 422
    assert client.patch(url, json={"status": "deferred", "resolution": "Expiry not stated; ask the partner"}).json()["status"] == "deferred"


def test_approval_creates_agreement_and_obligations_and_alerts_follow(monkeypatch):
    doc = extracted(monkeypatch, partner_id="demo-003")
    data = proposals(doc["id"])
    milestone = next(o for o in data["obligations"] if o["obligation_type"] == "milestone")
    decide(doc["id"], "obligations", milestone["id"], "reject", note="Target belongs to a different programme")
    approve_all(doc["id"])
    assert client.get(f"/api/documents/{doc['id']}/approval-check").json() == {"ready": True, "blockers": []}
    result = client.post(f"/api/documents/{doc['id']}/approve", json={"owner": "Partnership Team (fictional)"})
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["created"] == {"milestones": 0, "reports": 1, "finance": 1, "register_only": 1}
    assert body["project_created"] is False  # the only milestone was rejected and no programme/scope was approved
    agreement = get_record("agreements", body["agreement_id"])
    assert (agreement["partner_id"], agreement["reference_number"], agreement["start_date"], agreement["expiry_date"]) == \
        ("demo-003", "SYN-REV-002", "2025-12-01", "2026-11-30")
    assert agreement["source_document_id"] == doc["id"] and agreement["source_label"] == "user"
    assert agreement["owner"] == "Partnership Team (fictional)"
    obligations = {o["title"]: o for o in proposals(doc["id"])["obligations"]}
    report = get_record("reports", obligations["Inception report"]["operational_ref"]["id"])
    assert report["due_date"] == "2026-09-30" and report["report_type"] == "other" and report["status"] == "planned"
    uc = get_record("finance", obligations["Utilization certificate"]["operational_ref"]["id"])
    assert uc["record_type"] == "utilization_certificate" and uc["amount"] is None and uc["status"] == "pending"
    assert obligations["First tranche on signing"]["operational_ref"] is None  # no money record invented
    assert obligations["First cohort of 50 learners enrolled"]["operational_ref"] is None  # rejected
    rules = {a["rule_id"] for a in alerts_for({report["id"], uc["id"], agreement["id"]})}
    assert "REPORT_OVERDUE" in rules  # the deterministic engine evaluates the approved record
    final = client.get(f"/api/documents/{doc['id']}").json()
    assert final["status"] == "approved" and final["approved_by"] == "Demo user" and final["agreement_id"] == agreement["id"]
    assert client.get("/api/activities", params={"limit": 1}).json()[0]["event"] == "document_approved"


def test_approved_document_is_locked(monkeypatch):
    doc = extracted(monkeypatch, partner_id="demo-003")
    approve_all(doc["id"])
    assert client.post(f"/api/documents/{doc['id']}/approve", json={}).status_code == 200
    field = proposals(doc["id"])["extracted_fields"][0]
    assert decide(doc["id"], "extracted_fields", field["id"], "reset").status_code == 409
    assert client.post(f"/api/documents/{doc['id']}/approve", json={}).status_code == 409
    assert client.post(f"/api/documents/{doc['id']}/extract").status_code == 409


def test_milestones_create_a_project_and_deferred_values_are_left_out(monkeypatch):
    doc = extracted(monkeypatch, partner_id="demo-003")
    data = proposals(doc["id"])
    uc = next(o for o in data["obligations"] if o["obligation_type"] == "utilization_certificate")
    decide(doc["id"], "obligations", uc["id"], "defer", note="Confirm UC format with finance")
    approve_all(doc["id"])
    body = client.post(f"/api/documents/{doc['id']}/approve", json={}).json()
    assert body["project_created"] and body["created"]["milestones"] == 1 and body["created"]["finance"] == 0
    project = get_record("projects", body["project_id"])
    assert project["partner_id"] == "demo-003" and get_record("agreements", body["agreement_id"])["project_id"] == project["id"]
    milestone = next(m for m in list_records("milestones") if m["project_id"] == project["id"])
    assert milestone["due_date"] == "2027-01-15" and milestone["partner_id"] == "demo-003"


def test_partner_is_created_from_the_approved_name_only_when_asked(monkeypatch):
    doc = extracted(monkeypatch)
    approve_all(doc["id"])
    check = client.get(f"/api/documents/{doc['id']}/approval-check").json()
    assert any("Choose the partner" in b for b in check["blockers"])
    assert client.post(f"/api/documents/{doc['id']}/approve", json={"partner_id": "nope"}).status_code == 404
    body = client.post(f"/api/documents/{doc['id']}/approve", json={"create_partner": True}).json()
    partner = get_record("partners", body["partner_id"])
    assert body["partner_created"] and partner["name"] == "Sample Learning Collective (fictional)" and partner["source_label"] == "user"


def test_linked_agreement_conflicts_need_explicit_overwrite(monkeypatch):
    agreement = client.post("/api/agreements", json={"partner_id": "demo-003", "title": "Existing MOU (fictional)",
                                                     "status": "active", "start_date": "2025-12-01", "expiry_date": "2026-12-31"}).json()
    doc = extracted(monkeypatch, partner_id="demo-003", agreement_id=agreement["id"])
    approve_all(doc["id"])
    conflict = client.post(f"/api/documents/{doc['id']}/approve", json={})
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["conflicts"] == [{"field": "expiry_date", "current": "2026-12-31", "approved": "2026-11-30"}]
    assert get_record("agreements", agreement["id"])["expiry_date"] == "2026-12-31"  # nothing written
    body = client.post(f"/api/documents/{doc['id']}/approve", json={"overwrite_existing": True}).json()
    updated = get_record("agreements", body["agreement_id"])
    assert body["agreement_id"] == agreement["id"] and updated["expiry_date"] == "2026-11-30"
    assert updated["reference_number"] == "SYN-REV-002"  # empty field filled
    assert updated["title"] == "Existing MOU (fictional)"


def test_unlinked_addendum_cannot_be_approved(monkeypatch):
    doc = extracted(monkeypatch, partner_id="demo-003", kind="addendum")
    approve_all(doc["id"])
    response = client.post(f"/api/documents/{doc['id']}/approve", json={})
    assert response.status_code == 409
    blockers = response.json()["detail"]["blockers"]
    assert blockers[0] == "Choose the agreement this addendum amends." and "Compare the addendum" in blockers[1]


def test_conflicting_approved_values_block_approval(monkeypatch):
    output = {"fields": OUTPUT["fields"] + [item(field="expiry_date", value_as_written="30 November 2026",
                                                 normalized_value="2026-11-30", page=2, quote="valid until 30 November 2026")]}
    doc = extracted(monkeypatch, output=output, partner_id="demo-003")
    expiries = [f for f in proposals(doc["id"])["extracted_fields"] if f["field"] == "expiry_date"]
    approve_all(doc["id"], skip={expiries[1]["id"]})
    decide(doc["id"], "extracted_fields", expiries[1]["id"], value="2026-12-31", note="Typed from page 2")
    blockers = client.get(f"/api/documents/{doc['id']}/approval-check").json()["blockers"]
    assert blockers == ["Different values were approved for expiry_date; keep only one."]
