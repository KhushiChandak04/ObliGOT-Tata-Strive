"""Optional Tesseract OCR fallback. Tesseract is faked unless it is really installed (last test)."""
import json
import shutil

import pytest
from fastapi.testclient import TestClient

from app import document_routes, ocr
from app.config import settings
from app.extraction import ExtractionFailed
from app.main import app
from test_page_reading import reading, scanned_pdf, upload

client = TestClient(app)
PAGES = ["SYNTHETIC GRANT AGREEMENT (fictional). This agreement is effective from 1 April 2026.",
         "It shall remain in force until 31 March 2027. The grant is INR 12,00,000."]


@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "document_storage_dir", str(tmp_path / "store"))


def fake_ocr(monkeypatch, fail_at=None):
    calls = []

    def page(raw, n):
        calls.append(n)
        if n == fail_at:
            raise ocr.OcrFailed("simulated OCR failure")
        return PAGES[n - 1]
    monkeypatch.setattr(ocr, "ocr_available", lambda: True)
    monkeypatch.setattr(ocr, "ocr_page", page)
    return calls


def test_detection_requires_the_program_not_just_a_setting(monkeypatch):
    monkeypatch.setattr(settings, "ocr_enabled", True)
    monkeypatch.setattr(shutil, "which", lambda cmd: None)
    assert ocr.ocr_available() is False
    with pytest.raises(ocr.OcrFailed):
        ocr.ocr_page(b"%PDF", 1)
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/tesseract")
    monkeypatch.setattr(settings, "ocr_enabled", False)
    assert ocr.ocr_available() is False
    assert client.get("/api/health").json()["ocr_available"] is False


def test_without_gemini_scanned_pages_are_read_by_ocr_and_labelled(monkeypatch):
    calls = fake_ocr(monkeypatch)
    doc = upload(scanned_pdf(PAGES))
    assert doc["status"] == "uploaded" and "local OCR reads them" in doc["warnings"][0]
    client.post(f"/api/documents/{doc['id']}/extract")
    final = client.get(f"/api/documents/{doc['id']}").json()
    assert final["status"] == "needs_review" and final["extraction"]["mode"] == "deterministic"
    assert "OCR read 2 scanned pages" in final["extraction"]["note"] and calls == [1, 2]
    pages = client.get(f"/api/documents/{doc['id']}/pages").json()
    assert [p["method"] for p in pages] == ["ocr", "ocr"]
    fields = {f["field"]: f for f in client.get(f"/api/documents/{doc['id']}/extraction").json()["extracted_fields"]}
    assert fields["expiry_date"]["proposed_value"] == "2027-03-31"
    assert fields["expiry_date"]["evidence"]["basis"] == "ocr_text" and fields["expiry_date"]["evidence"]["verified"]


def test_ocr_fills_pages_gemini_could_not_read(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(settings, "vision_batch_pages", 1)
    calls = fake_ocr(monkeypatch)
    state = {"n": 0}

    async def reader(images):
        state["n"] += 1
        if state["n"] == 2:
            raise ExtractionFailed("quota_exhausted", "Today's Gemini quota is used up")
        return json.dumps({"pages": [reading(n, PAGES[n - 1]) for n, _ in images]})

    async def generate(prompt):
        raise ExtractionFailed("quota_exhausted", "Today's Gemini quota is used up")
    monkeypatch.setattr(document_routes, "gemini_read_pages", reader)
    monkeypatch.setattr(document_routes, "gemini_generate", generate)
    doc = upload(scanned_pdf(PAGES))
    client.post(f"/api/documents/{doc['id']}/extract")
    methods = {p["page_number"]: p["method"] for p in client.get(f"/api/documents/{doc['id']}/pages").json()}
    assert methods == {1: "gemini_vision", 2: "ocr"} and calls == [2]
    issues = {i["code"] for i in client.get(f"/api/documents/{doc['id']}/extraction").json()["review_issues"]}
    assert "PAGES_NOT_READ" not in issues and "SEMANTIC_EXTRACTION_PENDING" in issues


def test_a_later_gemini_run_replaces_ocr_text(monkeypatch):
    fake_ocr(monkeypatch)
    doc = upload(scanned_pdf(PAGES))
    client.post(f"/api/documents/{doc['id']}/extract")  # no Gemini: OCR
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    async def reader(images):
        return json.dumps({"pages": [reading(n, PAGES[n - 1]) for n, _ in images]})

    async def generate(prompt):
        return "{}"
    monkeypatch.setattr(document_routes, "gemini_read_pages", reader)
    monkeypatch.setattr(document_routes, "gemini_generate", generate)
    client.post(f"/api/documents/{doc['id']}/extract")
    assert [p["method"] for p in client.get(f"/api/documents/{doc['id']}/pages").json()] == ["gemini_vision", "gemini_vision"]


def test_ocr_failure_is_reported_and_unread_pages_are_flagged(monkeypatch):
    fake_ocr(monkeypatch, fail_at=2)
    doc = upload(scanned_pdf(PAGES))
    client.post(f"/api/documents/{doc['id']}/extract")
    final = client.get(f"/api/documents/{doc['id']}").json()
    assert "OCR stopped at page 2: simulated OCR failure" in final["extraction"]["note"]
    issue = next(i for i in client.get(f"/api/documents/{doc['id']}/extraction").json()["review_issues"] if i["code"] == "PAGES_NOT_READ")
    assert "Pages 2 have no text" in issue["message"] and "OCR could not read them" in issue["message"]


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract is not installed on this machine")
def test_real_tesseract_reads_a_synthetic_scan(monkeypatch):
    monkeypatch.setattr(settings, "ocr_enabled", True)
    text = ocr.ocr_page(scanned_pdf(["SYNTHETIC AGREEMENT effective from 1 April 2026"]), 1)
    assert "AGREEMENT" in text.upper()
