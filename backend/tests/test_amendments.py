"""Addenda (Step P4a): linking, change building, review, effective-date application, history, conflicts.
All documents are synthetic; Gemini is faked; "today" is fixed at 17 Oct 2026."""
import io
from datetime import date

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app import amendments, document_review, routes
from app.config import settings
from app.main import app
from app.repository import get_record, list_records
from test_document_review import OUTPUT, PAGES, approve_all, extracted, item, proposals

client = TestClient(app)
TODAY = date(2026, 10, 17)


@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "document_storage_dir", str(tmp_path / "store"))
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    set_today(monkeypatch, TODAY)


def set_today(monkeypatch, day):
    for module in (amendments, document_review, routes):
        monkeypatch.setattr(module, "business_today", lambda: day)


def mou(monkeypatch, ref="SYN-REV-002") -> dict:
    pages = [p.replace("SYN-REV-002", ref) for p in PAGES]
    output = {k: [{**i, "quote": i["quote"].replace("SYN-REV-002", ref),
                   "value_as_written": i.get("value_as_written", "").replace("SYN-REV-002", ref)} if "value_as_written" in i
                  else {**i} for i in v] for k, v in OUTPUT.items()}
    doc = extracted(monkeypatch, output=output, pages=pages, partner_id="demo-003")
    approve_all(doc["id"])
    body = client.post(f"/api/documents/{doc['id']}/approve", json={}).json()
    return get_record("agreements", body["agreement_id"])


def addendum_pages(n, expiry_text, effective_text="This addendum is effective from 1 October 2026.", extra=""):
    return [f"ADDENDUM No. {n} to MOU SYN-REV-002 between the parties (fictional). Signed on 1 October 2026.",
            f"The term of the MOU is extended until {expiry_text}. {effective_text} {extra}".strip()]


def addendum_output(expiry_iso, expiry_text, effective_iso="2026-10-01", effective=True, obligations=()):
    fields = [
        item(field="reference_number", value_as_written="SYN-REV-002", page=1, quote="MOU SYN-REV-002"),
        item(field="execution_date", value_as_written="1 October 2026", normalized_value="2026-10-01", page=1, quote="Signed on 1 October 2026"),
        item(field="expiry_date", value_as_written=expiry_text, normalized_value=expiry_iso, page=2, quote=f"extended until {expiry_text}"),
    ]
    if effective:
        fields.append(item(field="effective_date", value_as_written="1 October 2026", normalized_value=effective_iso, page=2,
                           quote="effective from 1 October 2026"))
    return {"fields": fields, "obligations": list(obligations)}


def addendum(monkeypatch, n, expiry_iso, expiry_text, link_to=None, build=True, **kw) -> dict:
    extra = kw.pop("extra", "")
    effective_text = kw.pop("effective_text", "This addendum is effective from 1 October 2026.")
    doc = extracted(monkeypatch, output=addendum_output(expiry_iso, expiry_text, **kw),
                    pages=addendum_pages(n, expiry_text, effective_text, extra), kind="addendum", partner_id="demo-003")
    if link_to:
        assert client.patch(f"/api/documents/{doc['id']}/link", json={"agreement_id": link_to}).status_code == 200
        if build:
            assert client.post(f"/api/documents/{doc['id']}/changes").status_code == 200
    return doc


def changes(doc_id):
    return client.get(f"/api/documents/{doc_id}/changes").json()


def decide(change_id, decision="approve", **body):
    return client.patch(f"/api/agreement-changes/{change_id}", json={"decision": decision, **body})


def approve(doc_id):
    return client.post(f"/api/documents/{doc_id}/approve", json={})


def rules_for(record_id):
    return {a["rule_id"] for a in client.get("/api/alerts").json()["alerts"] if a["record_id"] == record_id}


def test_one_partner_keeps_independent_mous_and_candidates_are_only_suggested(monkeypatch):
    first, second = mou(monkeypatch, "SYN-REV-002"), mou(monkeypatch, "SYN-REV-003")
    assert first["id"] != second["id"] and {first["reference_number"], second["reference_number"]} == {"SYN-REV-002", "SYN-REV-003"}
    doc = addendum(monkeypatch, 1, "2027-03-31", "31 March 2027")
    candidates = client.get(f"/api/documents/{doc['id']}/agreement-candidates").json()
    assert candidates[0]["agreement_id"] == first["id"] and "reference number appears in the addendum" in candidates[0]["reasons"]
    assert get_record("documents", doc["id"])["agreement_id"] is None  # nothing linked automatically


def test_linking_rules(monkeypatch):
    agreement = mou(monkeypatch)
    doc = addendum(monkeypatch, 1, "2027-03-31", "31 March 2027")
    assert client.post(f"/api/documents/{doc['id']}/changes").status_code == 409  # not linked yet
    assert client.patch(f"/api/documents/{doc['id']}/link", json={"agreement_id": "nope"}).status_code == 404
    other = next(a for a in list_records("agreements") if a["partner_id"] == "demo-001")
    assert client.patch(f"/api/documents/{doc['id']}/link", json={"agreement_id": other["id"]}).status_code == 422
    mou_doc = agreement["source_document_id"]
    assert client.patch(f"/api/documents/{mou_doc}/link", json={"agreement_id": agreement["id"]}).status_code == 422
    linked = client.patch(f"/api/documents/{doc['id']}/link", json={"agreement_id": agreement["id"]}).json()
    assert linked["agreement_id"] == agreement["id"] and not any("Choose the agreement" in w for w in linked["warnings"])


def test_changes_compare_with_current_values(monkeypatch):
    agreement = mou(monkeypatch)
    report = item(obligation_type="impact_report", title="Mid-term impact report", due_date="2027-01-31", page=2,
                  quote="submit a mid-term impact report by 31 January 2027")
    doc = addendum(monkeypatch, 1, "2027-03-31", "31 March 2027", link_to=agreement["id"], build=False,
                   extra="The partner shall submit a mid-term impact report by 31 January 2027.", obligations=[report])
    built = client.post(f"/api/documents/{doc['id']}/changes").json()
    assert built["amendment_date"] == "2026-10-01" and built["effective_date"] == "2026-10-01"
    by_field = {c["field"]: c for c in built["changes"]}
    expiry = by_field["expiry_date"]
    assert (expiry["prior_value"], expiry["proposed_value"], expiry["status"], expiry["kind"]) == ("2026-11-30", "2027-03-31", "proposed", "modify")
    assert expiry["evidence"]["verified"] and expiry["evidence"]["page"] == 2
    assert by_field["added"]["target"] == "obligation" and by_field["added"]["proposed_value"] == "Mid-term impact report"
    assert get_record("agreements", agreement["id"])["expiry_date"] == "2026-11-30"  # nothing applied by building


def test_restated_value_is_not_a_change(monkeypatch):
    agreement = mou(monkeypatch)
    doc = addendum(monkeypatch, 1, "2026-11-30", "30 November 2026", link_to=agreement["id"], build=False)
    built = client.post(f"/api/documents/{doc['id']}/changes").json()
    assert built["changes"] == [] and built["unchanged"] == ["expiry_date"]


def test_approved_change_applies_on_addendum_approval_and_keeps_history(monkeypatch):
    agreement = mou(monkeypatch)
    assert "MOU_EXPIRING" in rules_for(agreement["id"])
    report = item(obligation_type="impact_report", title="Mid-term impact report", due_date="2027-01-31", page=2,
                  quote="submit a mid-term impact report by 31 January 2027")
    doc = addendum(monkeypatch, 1, "2027-03-31", "31 March 2027", link_to=agreement["id"],
                   extra="The partner shall submit a mid-term impact report by 31 January 2027.", obligations=[report])
    for change in changes(doc["id"]):
        assert decide(change["id"], note="Checked against the addendum").status_code == 200
    assert "MOU_EXPIRING" in rules_for(agreement["id"])  # approved change, addendum not yet approved: not applied
    result = approve(doc["id"])
    assert result.status_code == 200, result.text
    body = result.json()
    assert len(body["applied_changes"]) == 1 and body["scheduled_changes"] == [] and body["created"]["reports"] == 1
    current = get_record("agreements", agreement["id"])
    assert current["expiry_date"] == "2027-03-31" and current["status"] == "active"
    assert "MOU_EXPIRING" not in rules_for(agreement["id"])
    history = client.get(f"/api/agreements/{agreement['id']}/history").json()
    assert history["original"]["expiry_date"] == "2026-11-30" and history["effective"]["expiry_date"] == "2027-03-31"
    assert history["counts"]["applied"] == 1 and history["changes"][0]["reviewed_by"] == "Demo user"
    assert any(r["title"] == "Mid-term impact report" and r["report_type"] == "impact" for r in list_records("reports"))
    events = [a["event"] for a in client.get("/api/activities", params={"limit": 3}).json()]
    assert events[:2] == ["document_approved", "amendment_applied"]
    wb = load_workbook(io.BytesIO(client.get("/api/export/workbook").content))
    rows = list(wb["Addenda_Change_History"].iter_rows(min_row=2, values_only=True))
    assert any(r[5] == "expiry_date" and r[6] == "2026-11-30" and r[7] == "2027-03-31" and r[12] == "approved" for r in rows)
    header = [c.value for c in wb["Agreements"][1]]
    row = next(r for r in wb["Agreements"].iter_rows(min_row=2, values_only=True) if r[0] == agreement["id"])
    assert row[header.index("amended")] is True and row[header.index("expiry_date")].date() == date(2027, 3, 31)


def test_effective_date_is_required_and_future_changes_wait(monkeypatch):
    agreement = mou(monkeypatch)
    doc = addendum(monkeypatch, 1, "2027-03-31", "31 March 2027", link_to=agreement["id"], effective=False,
                   effective_text="The parties will agree the date of effect later.")
    change = changes(doc["id"])[0]
    assert change["effective_date"] is None
    response = decide(change["id"])
    assert response.status_code == 422 and "effective date is not stated" in response.json()["detail"]
    assert decide(change["id"], effective_date="2026-12-01", note="Date confirmed in the cover letter (fictional)").status_code == 200
    body = approve(doc["id"]).json()
    assert body["applied_changes"] == [] and body["scheduled_changes"] == [change["id"]]
    assert get_record("agreements", agreement["id"])["expiry_date"] == "2026-11-30"
    set_today(monkeypatch, date(2026, 12, 2))
    client.get("/api/alerts")
    assert get_record("agreements", agreement["id"])["expiry_date"] == "2027-03-31"
    latest = client.get("/api/activities", params={"limit": 5}).json()
    assert any(a["event"] == "amendment_applied" and a["actor"] == "System (effective date reached)" for a in latest)


def test_two_addenda_apply_in_effective_date_order(monkeypatch):
    agreement = mou(monkeypatch)
    first = addendum(monkeypatch, 1, "2027-03-31", "31 March 2027", link_to=agreement["id"])
    second = addendum(monkeypatch, 2, "2027-06-30", "30 June 2027", link_to=agreement["id"], effective_iso="2026-10-10")
    for doc in (second, first):  # approve the later-effective addendum first
        for change in changes(doc["id"]):
            decide(change["id"], note="Checked")
        assert approve(doc["id"]).status_code == 200
    assert get_record("agreements", agreement["id"])["expiry_date"] == "2027-06-30"  # latest effective date wins
    history = client.get(f"/api/agreements/{agreement['id']}/history").json()
    assert [c["effective_date"] for c in history["changes"]] == ["2026-10-01", "2026-10-10"]
    assert history["counts"]["applied"] == 2 and history["original"]["expiry_date"] == "2026-11-30"


def test_conflicting_addenda_stay_unresolved_and_do_not_apply(monkeypatch):
    agreement = mou(monkeypatch)
    first = addendum(monkeypatch, 1, "2027-03-31", "31 March 2027", link_to=agreement["id"])
    second = addendum(monkeypatch, 2, "2027-02-28", "28 February 2027", link_to=agreement["id"])  # same effective date
    clash = changes(second["id"])[0]
    assert clash["status"] == "unresolved" and "Another addendum sets a different value" in clash["note"]
    decide(changes(first["id"])[0]["id"], note="Checked")
    assert decide(clash["id"], note="Checked").status_code == 409  # cannot approve over an approved conflicting value
    assert decide(clash["id"], "unresolved").status_code == 422  # must explain
    decide(clash["id"], "unresolved", note="Ask the partner which date governs")
    assert approve(second["id"]).status_code == 200  # reviewed; the unresolved change stays visible, not applied
    assert get_record("agreements", agreement["id"])["expiry_date"] == "2026-11-30"
    history = client.get(f"/api/agreements/{agreement['id']}/history").json()
    assert history["counts"]["unresolved"] == 1 and history["counts"]["applied"] == 0
    wb = load_workbook(io.BytesIO(client.get("/api/export/workbook").content))
    header = [c.value for c in wb["Agreements"][1]]
    row = next(r for r in wb["Agreements"].iter_rows(min_row=2, values_only=True) if r[0] == agreement["id"])
    assert row[header.index("unresolved_changes")] == 1 and row[header.index("amended")] is False


def test_addendum_with_two_values_for_one_term_is_unresolved(monkeypatch):
    agreement = mou(monkeypatch)
    output = addendum_output("2027-03-31", "31 March 2027")
    output["fields"].append(item(field="expiry_date", value_as_written="30 April 2027", normalized_value="2027-04-30", page=2,
                                 quote="or 30 April 2027"))
    doc = extracted(monkeypatch, output=output, kind="addendum", partner_id="demo-003",
                    pages=addendum_pages(1, "31 March 2027", extra="Annex B says the term ends on or 30 April 2027."))
    client.patch(f"/api/documents/{doc['id']}/link", json={"agreement_id": agreement["id"]})
    built = client.post(f"/api/documents/{doc['id']}/changes").json()["changes"]
    assert [c["status"] for c in built] == ["unresolved", "unresolved"]


def test_unverified_evidence_cannot_be_approved_and_decided_changes_lock_the_link(monkeypatch):
    agreement = mou(monkeypatch)
    output = addendum_output("2027-03-31", "31 March 2027")
    output["fields"][2]["quote"] = "extended until 31 March 2028"  # not on the page
    doc = extracted(monkeypatch, output=output, kind="addendum", partner_id="demo-003", pages=addendum_pages(1, "31 March 2027"))
    client.patch(f"/api/documents/{doc['id']}/link", json={"agreement_id": agreement["id"]})
    change = client.post(f"/api/documents/{doc['id']}/changes").json()["changes"][0]
    assert change["evidence"]["verified"] is False
    response = decide(change["id"], note="Looks right")
    assert response.status_code == 422 and "verified evidence" in str(response.json()["detail"])
    decide(change["id"], "reject", note="Quote not in the addendum")
    second = mou(monkeypatch, "SYN-REV-009")
    assert client.patch(f"/api/documents/{doc['id']}/link", json={"agreement_id": second["id"]}).status_code == 409
