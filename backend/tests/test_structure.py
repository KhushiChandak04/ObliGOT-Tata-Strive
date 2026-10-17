"""Tables, relative deadlines, sections, templates (Step S2).

Synthetic fixtures modelled on the team's descriptions of the three sample MOUs (no real content):
- "MoU 1-like": schedules with course rows and grant instalments on the last page, after the signature page.
- "MoU 2-like": a quarterly budget table that continues across a page break.
- "MoU 3-like": a receipt-format annexure, utilization deadlines of 15 and 20 days after year end, monthly and
  quarterly reporting, and a deadline relative to receiving an instalment.
Groq is faked: these tests check how the application keeps, verifies, and flags what the model returns,
not the model's reading accuracy on the real documents."""
import json

import pytest
from fastapi.testclient import TestClient

from app import document_routes
from app.config import settings
from app.extraction import ChunkExtraction, build_proposals, chunk_pages
from app.main import app
from app.repository import list_records
from test_page_reading import install, reading, scanned_pdf, upload

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "document_storage_dir", str(tmp_path / "store"))
    monkeypatch.setattr(settings, "groq_api_key", "test-key")


DOC = {"id": "doc-0000000000aa", "kind": "mou", "partner_id": "demo-003", "agreement_id": None}


def build(output, texts, meta=None):
    return build_proposals(DOC, [ChunkExtraction.model_validate(output)], texts, ["ai_transcript"] * len(texts), [], meta or {})


def ob(**kw):
    return {"obligation_type": "utilization_certificate", "title": "UC", "page": 1, "quote": "x", **kw}


# ---- MoU 1-like: schedules after the signature page ----

MOU1 = [
    "SYNTHETIC CSR AGREEMENT (fictional). 6. The Implementing Agency shall submit a utilization certificate for each instalment.",
    "IN WITNESS WHEREOF the parties have signed (fictional signatures).",
    "SCHEDULE A\nCourse | Students | Cost per student (Rs.) | Total (Rs.)\nRetail Associate | 60 | 15,000 | 9,00,000\n"
    "Field Technician | 40 | 18,000 | 7,20,000\nTotal | 100 | | 16,20,000\n"
    "SCHEDULE B\nInstalment | Timing | Amount (Rs.)\nFirst | On signing | 8,10,000\nSecond | After mid-term report | 8,10,000",
]


def test_schedules_after_the_signature_page_are_extracted_as_tables(monkeypatch):
    pages = {1: reading(1, MOU1[0], printed_page_number="1"), 2: reading(2, MOU1[1], "signature"),
             3: reading(3, MOU1[2], "schedule", section_labels=["Schedule A", "Schedule B"], has_table=True, printed_page_number="8")}
    output = {
        "tables": [
            {"title": "Schedule A", "kind": "budget", "section": "Schedule A", "pages": [3],
             "headers": ["Course", "Students", "Cost per student (Rs.)", "Total (Rs.)"],
             "rows": [{"page": 3, "cells": ["Retail Associate", "60", "15,000", "9,00,000"]},
                      {"page": 3, "cells": ["Field Technician", "40", "18,000", "7,20,000"]},
                      {"page": 3, "cells": ["Total", "100", "", "16,20,000"]}]},
            {"title": "Schedule B", "kind": "tranches", "section": "Schedule B", "pages": [3],
             "headers": ["Instalment", "Timing", "Amount (Rs.)"],
             "rows": [{"page": 3, "cells": ["First", "On signing", "8,10,000"]},
                      {"page": 3, "cells": ["Second", "After mid-term report", "8,10,000"]}]},
        ],
        "obligations": [ob(title="UC for each instalment", section="Clause 6", quote="submit a utilization certificate for each instalment",
                           deadline_type="unspecified")],
    }
    _, prompts = install(monkeypatch, pages, output)
    doc = upload(scanned_pdf(MOU1))
    client.post(f"/api/documents/{doc['id']}/extract")
    final = client.get(f"/api/documents/{doc['id']}").json()
    assert final["status"] == "extracted" and final["extraction"]["pages_sent"] == [1, 2, 3]
    data = client.get(f"/api/documents/{doc['id']}/extraction").json()
    budget, tranches = data["tables"]
    assert (budget["section"], budget["kind"], budget["pages"]) == ("Schedule A", "budget", [3])
    assert budget["rows"][1]["cells"] == ["Field Technician", "40", "18,000", "7,20,000"]  # row stays together
    assert all(r["verified"] for r in budget["rows"] + tranches["rows"])
    assert budget["evidence"]["verified"] and budget["evidence"]["printed_page"] == "8" and budget["evidence"]["basis"] == "ai_transcript"
    assert budget["review_state"] == "proposed" and tranches["kind"] == "tranches"
    uc = data["obligations"][0]
    assert uc["evidence"]["section"] == "Clause 6" and uc["evidence"]["printed_page"] == "1"  # separately identifiable
    assert client.post(f"/api/documents/{doc['id']}/approve", json={}).status_code == 404


# ---- MoU 2-like: a table continuing across pages ----

def test_chunks_keep_a_continuing_table_together():
    lengths = {1: 900, 2: 900, 3: 900, 4: 900}
    assert chunk_pages(lengths, 1000) == [[1], [2], [3], [4]]
    assert chunk_pages(lengths, 1000, {3}) == [[1], [2, 3], [4]]
    assert chunk_pages(lengths, 1000, {3, 4}) == [[1], [2, 3, 4]]


def test_budget_table_across_a_page_break_is_one_table_with_its_headers(monkeypatch):
    texts = ["SYNTHETIC PROJECT AGREEMENT (fictional) - project summary and objectives. " * 6,
             "ANNEXURE 3 - BUDGET\nLocation | Cost head | Q1 | Q2 | Q3 | Q4 | Total\nCity A | Trainer salaries | 1,00,000 | 1,00,000 | 1,00,000 | 1,00,000 | 4,00,000",
             "City B | Trainer salaries | 50,000 | 50,000 | 50,000 | 50,000 | 2,00,000\nGrand total | | | | | | 6,00,000\nNote: amounts in INR."]
    pages = {1: reading(1, texts[0]), 2: reading(2, texts[1], "budget_table", has_table=True, table_continues_to_next=True),
             3: reading(3, texts[2], "budget_table", has_table=True, table_continues_from_previous=True)}
    headers = ["Location", "Cost head", "Q1", "Q2", "Q3", "Q4", "Total"]
    output = {"tables": [{"title": "Budget", "kind": "budget", "section": "Annexure 3", "pages": [2, 3], "headers": headers, "currency": "INR",
                          "notes": ["Note: amounts in INR."],
                          "rows": [{"page": 2, "cells": ["City A", "Trainer salaries", "1,00,000", "1,00,000", "1,00,000", "1,00,000", "4,00,000"]},
                                   {"page": 3, "cells": ["City B", "Trainer salaries", "50,000", "50,000", "50,000", "50,000", "2,00,000"]},
                                   {"page": 3, "cells": ["Grand total", "", "", "", "", "", "6,00,000"]}]}]}
    monkeypatch.setattr(settings, "extraction_chunk_chars", 200)  # each page alone would exceed the budget
    _, prompts = install(monkeypatch, pages, output)
    doc = upload(scanned_pdf(texts))
    client.post(f"/api/documents/{doc['id']}/extract")
    assert any("<<<PAGE 2>>>" in p and "<<<PAGE 3>>>" in p for p in prompts)  # sent together
    table = client.get(f"/api/documents/{doc['id']}/extraction").json()["tables"][0]
    assert table["pages"] == [2, 3] and table["continues_across_pages"] and table["headers"] == headers
    assert [r["page"] for r in table["rows"]] == [2, 3, 3] and all(r["verified"] for r in table["rows"])
    assert table["rows"][1]["cells"][0:2] == ["City B", "Trainer salaries"] and table["currency"] == "INR"


# ---- MoU 3-like: templates, conflicting deadlines, recurring and event-based reporting ----

def test_receipt_template_values_are_flagged_not_treated_as_payments():
    texts = ["Clause 5: funds are released in two instalments (fictional).", "ANNEXURE C - FORMAT OF RECEIPT\nReceived Rs. ______ from ______"]
    meta = {2: {"page_type": "receipt_template", "printed_page_number": None}}
    output = {"financial_terms": [{"term_type": "tranche", "description": "Receipt amount", "amount": 0, "currency": "INR",
                                   "page": 2, "quote": "Received Rs. ______ from ______"}],
              "tables": [{"title": "Format of receipt", "kind": "other", "pages": [2], "headers": ["Received Rs."], "rows": []}]}
    out = build(output, texts, meta)
    assert out["financial_terms"][0]["review_state"] == "needs_review"
    assert any("blank template" in w for w in out["financial_terms"][0]["warnings"])
    assert [i["code"] for i in out["review_issues"]].count("TEMPLATE_VALUE") == 2


def test_deadlines_15_and_20_days_after_year_end_are_both_kept_and_flagged():
    texts = ["7.1 The utilization certificate shall be submitted within 15 days after the end of the financial year.",
             "9.4 The audited utilization statement shall be submitted within 20 days after the end of the financial year."]
    output = {"obligations": [
        ob(title="Utilization certificate", page=1, quote="within 15 days after the end of the financial year", section="7.1",
           deadline_type="relative", deadline_text="within 15 days after the end of the financial year", offset_value=15,
           offset_unit="calendar_days", trigger="year_end", recurrence="annual"),
        ob(title="Audited utilization statement", page=2, quote="within 20 days after the end of the financial year", section="9.4",
           deadline_type="relative", deadline_text="within 20 days after the end of the financial year", offset_value=20,
           offset_unit="calendar_days", trigger="year_end", recurrence="annual"),
    ]}
    out = build(output, texts)
    first, second = out["obligations"]
    assert (first["deadline"]["offset_value"], second["deadline"]["offset_value"]) == (15, 20)  # neither overwritten
    assert first["due_date"] is None and second["due_date"] is None
    assert first["review_state"] == second["review_state"] == "needs_review"
    conflict = next(i for i in out["review_issues"] if i["code"] == "DEADLINE_CONFLICT")
    assert "within 15 days" in conflict["message"] and "within 20 days" in conflict["message"] and "page 2" in conflict["message"]


def test_recurring_and_event_based_deadlines_keep_their_rule_without_inventing_dates():
    texts = ["The partner shall submit monthly outcome reports and quarterly analytical reports. "
             "A fund utilization report is due within seven working days after receipt of each instalment."]
    output = {"obligations": [
        ob(obligation_type="progress_report", title="Monthly outcome report", quote="monthly outcome reports",
           deadline_type="recurring", recurrence="monthly", frequency="monthly"),
        ob(obligation_type="progress_report", title="Quarterly analytical report", quote="quarterly analytical reports",
           deadline_type="recurring", recurrence="quarterly", frequency="quarterly"),
        ob(title="Fund utilization report", quote="within seven working days after receipt of each instalment",
           deadline_type="relative", deadline_text="within seven working days after receipt of each instalment",
           offset_value=7, offset_unit="working_days", trigger="event", trigger_event="receipt of each instalment",
           due_date="2026-11-07"),
    ]}
    out = build(output, texts)
    monthly, quarterly, event = out["obligations"]
    assert monthly["deadline"]["recurrence"] == "monthly" and quarterly["deadline"]["recurrence"] == "quarterly"
    assert event["due_date"] is None  # the model's proposed date is not kept for a relative deadline
    assert event["deadline"] == {"deadline_type": "relative", "text": "within seven working days after receipt of each instalment",
                                 "offset_value": 7, "offset_unit": "working_days", "trigger": "event",
                                 "trigger_event": "receipt of each instalment", "recurrence": None}
    assert any("set only when that event is recorded" in w for w in event["warnings"])
    assert any("was not kept" in w for w in event["warnings"])
    assert not any(i["code"] == "DEADLINE_CONFLICT" for i in out["review_issues"])  # different deliverables/triggers


# ---- table safeguards ----

def test_table_rows_are_checked_against_the_page():
    texts = ["Location | Target\nCity A | 120\nCity B | 80"]
    output = {"tables": [{"title": "Targets", "kind": "targets", "pages": [1], "headers": ["Location", "Target"],
                          "rows": [{"page": 1, "cells": ["City A", "120"]},
                                   {"page": 1, "cells": ["City B", "800"]},          # 800 is not on the page
                                   {"page": 1, "cells": ["City B"]},                 # one cell short
                                   {"page": 5, "cells": ["City D", "10"]}]}]}        # page outside the document
    table = build(output, texts)["tables"][0]
    assert [r["verified"] for r in table["rows"]] == [True, False, True, False]
    assert table["review_state"] == "needs_review"
    joined = " ".join(table["warnings"])
    assert "2 of 4 rows have cells not found" in joined and "Rows 3 do not have one cell per header" in joined
    assert "Rows 4 cite a page outside the document" in joined


def test_tables_without_headers_are_not_kept():
    out = build({"tables": [{"title": "x", "kind": "other", "pages": [1], "headers": [], "rows": []}]}, ["text"])
    assert out["tables"] == [] and out["review_issues"][0]["code"] == "TABLE_WITHOUT_HEADERS"


def test_rerun_does_not_duplicate_tables(monkeypatch):
    pages = {1: reading(1, MOU1[0]), 2: reading(2, MOU1[1], "signature"), 3: reading(3, MOU1[2], "schedule")}
    output = {"tables": [{"title": "Schedule B", "kind": "tranches", "pages": [3], "headers": ["Instalment", "Timing", "Amount (Rs.)"],
                          "rows": [{"page": 3, "cells": ["First", "On signing", "8,10,000"]}]}]}
    install(monkeypatch, pages, output)
    doc = upload(scanned_pdf(MOU1))
    client.post(f"/api/documents/{doc['id']}/extract")
    client.post(f"/api/documents/{doc['id']}/extract")
    assert len([t for t in list_records("tables") if t["document_id"] == doc["id"]]) == 1
