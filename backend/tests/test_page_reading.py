"""Groq scan-aware page reading. Synthetic scanned PDFs; provider calls are faked in tests."""
import asyncio
import json
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app import document_routes
from app.config import settings
from app.extraction import ExtractionFailed
from app.groq_client import structured_completion
from app.main import app
from app.page_reading import BatchReading, groq_read_pages, parse_batch, render_page
from app.repository import list_records, patch_record

client = TestClient(app)
SAMPLES = Path(__file__).resolve().parents[2] / "samples"

# Synthetic scanned agreement: main text, signature page, then a schedule after the signatures (as described for MoU 1).
SCANNED = [
    "SYNTHETIC GRANT AGREEMENT (fictional). Clause 4: The grantee shall submit a utilization certificate within 15 days after year end.",
    "Clause 9: Signed for and on behalf of the parties (fictional signatures).",
    "SCHEDULE A - Project budget (fictional). Course | Students | Cost per student (INR) | Total (INR)",
]


@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "document_storage_dir", str(tmp_path / "store"))
    monkeypatch.setattr(settings, "groq_api_key", "test-key")


def scanned_pdf(texts: list[str], with_text_layer: set[int] = frozenset()) -> bytes:
    """Each page is an image of its text (like a scan); pages in `with_text_layer` (1-based) keep real text."""
    out = pymupdf.open()
    for n, text in enumerate(texts, 1):
        src = pymupdf.open()
        src.new_page().insert_textbox(pymupdf.Rect(40, 40, 555, 800), text, fontsize=11)
        page = out.new_page()
        if n in with_text_layer:
            page.insert_textbox(pymupdf.Rect(40, 40, 555, 800), text, fontsize=11)
        else:
            page.insert_image(page.rect, stream=src[0].get_pixmap(dpi=90).tobytes("png"))
        src.close()
    data = out.tobytes()
    out.close()
    return data


def upload(data: bytes, **form) -> dict:
    response = client.post("/api/documents", data={"kind": "mou", "partner_id": "demo-003", **form},
                           files={"file": ("synthetic-scan.pdf", data, "application/pdf")})
    assert response.status_code == 201, response.text
    return response.json()


def reading(n, text, page_type="main_agreement", **extra):
    return {"page": n, "page_type": page_type, "transcript": text, "legibility": "good", **extra}


def install(monkeypatch, pages: dict[int, dict], extraction=None):
    """Fake page reader returning `pages[n]` for each requested page, and a fake extractor."""
    calls, prompts = [], []

    async def reader(images):
        calls.append([(n, image[:2]) for n, image in images])
        return json.dumps({"pages": [pages[n] for n, _ in images]})

    async def extractor(prompt):
        prompts.append(prompt)
        return json.dumps(extraction or {})
    monkeypatch.setattr(document_routes, "groq_read_pages", reader)
    monkeypatch.setattr(document_routes, "groq_generate", extractor)
    return calls, prompts


def test_scanned_upload_is_not_blocked_when_groq_can_read_images():
    doc = upload(scanned_pdf(SCANNED))
    assert doc["status"] == "uploaded" and all(p["text_status"] == "low_text" for p in doc["pages"])
    assert "All pages are scanned images" in doc["warnings"][0] and "AI transcription" in doc["warnings"][0]


def test_legacy_gemini_blocked_scan_can_be_retried_with_groq(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "")
    monkeypatch.setattr(document_routes.ocr, "ocr_available", lambda: False)
    doc = upload(scanned_pdf(SCANNED))
    assert doc["status"] == "blocked"
    patch_record("documents", doc["id"], {
        "warnings": [
            "No page has embedded text (likely a scanned PDF). Configure Gemini or OCR to extract text from the page images."
        ]
    })
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    pages = {n: reading(n, text) for n, text in enumerate(SCANNED, 1)}
    install(monkeypatch, pages)

    response = client.post(f"/api/documents/{doc['id']}/extract")

    assert response.status_code == 202
    final = client.get(f"/api/documents/{doc['id']}").json()
    assert final["status"] == "extracted", final["error"]
    assert final["extraction"]["mode"] == "groq"
    assert not any("Configure Gemini" in warning or "Configure Groq" in warning for warning in final["warnings"])
    assert len(client.get(f"/api/documents/{doc['id']}/pages").json()) == len(SCANNED)


def test_scanned_pages_are_read_in_batches_and_extraction_continues_past_the_signature(monkeypatch):
    monkeypatch.setattr(settings, "vision_batch_pages", 2)
    pages = {1: reading(1, SCANNED[0], printed_page_number="2"), 2: reading(2, SCANNED[1], "signature"),
             3: reading(3, SCANNED[2], "schedule", section_labels=["Schedule A"], has_table=True)}
    output = {"obligations": [{"obligation_type": "utilization_certificate", "title": "Annual UC", "page": 1,
                               "quote": "submit a utilization certificate within 15 days after year end"}]}
    calls, prompts = install(monkeypatch, pages, output)
    doc = upload(scanned_pdf(SCANNED))
    assert client.post(f"/api/documents/{doc['id']}/extract").status_code == 202
    final = client.get(f"/api/documents/{doc['id']}").json()
    assert final["status"] == "extracted", final["error"]
    assert [[n for n, _ in c] for c in calls] == [[1, 2], [3]]
    assert all(magic == b"\xff\xd8" for c in calls for _, magic in c)  # JPEG page images
    run = final["extraction"]
    assert run["pages_to_read"] == 3 and run["pages_read"] == 3 and run["pages_sent"] == [1, 2, 3]
    assert "<<<PAGE 3>>> [read from a scanned image (AI transcription); page type: schedule; sections: Schedule A]" in prompts[0]
    assert "printed page number: 2" in prompts[0]
    stored = client.get(f"/api/documents/{doc['id']}/pages").json()
    assert [(p["page_number"], p["method"], p["page_type"]) for p in stored] == \
        [(1, "groq_vision", "main_agreement"), (2, "groq_vision", "signature"), (3, "groq_vision", "schedule")]
    assert stored[0]["printed_page_number"] == "2" and stored[0]["page_number"] == 1  # printed ≠ physical
    evidence = client.get(f"/api/documents/{doc['id']}/extraction").json()["obligations"][0]["evidence"]
    assert evidence["verified"] and evidence["basis"] == "ai_transcript"


def test_unreadable_scan_without_any_text_asks_for_a_retry_and_saves_nothing_wrong(monkeypatch):
    async def reader(images):
        return json.dumps({"pages": [reading(9, "text")]})  # wrong pages: rejected
    install(monkeypatch, {})
    monkeypatch.setattr(document_routes, "groq_read_pages", reader)
    doc = upload(scanned_pdf(SCANNED))
    client.post(f"/api/documents/{doc['id']}/extract")
    final = client.get(f"/api/documents/{doc['id']}").json()
    assert final["status"] == "retry_required" and final["extraction"]["ai_error"] == "malformed_response"
    assert "was sent pages [1, 2, 3]" in final["error"] and final["extraction"]["retryable"]
    assert client.get(f"/api/documents/{doc['id']}/pages").json() == []
    assert not [r for r in list_records("review_issues") if r["document_id"] == doc["id"]]
    assert client.post(f"/api/documents/{doc['id']}/extract").status_code == 202  # retry allowed


def test_reading_stops_part_way_keeps_finished_pages_and_flags_the_rest(monkeypatch):
    monkeypatch.setattr(settings, "vision_batch_pages", 2)
    calls = {"n": 0}

    async def reader(images):
        calls["n"] += 1
        if calls["n"] == 2:
            raise ExtractionFailed("rate_limited", "Groq rate limit reached", retryable=True)
        return json.dumps({"pages": [reading(n, SCANNED[n - 1]) for n, _ in images]})
    install(monkeypatch, {})
    monkeypatch.setattr(document_routes, "groq_read_pages", reader)
    doc = upload(scanned_pdf(SCANNED))
    client.post(f"/api/documents/{doc['id']}/extract")
    final = client.get(f"/api/documents/{doc['id']}").json()
    assert final["status"] == "extracted" and final["extraction"]["ai_error"] == "rate_limited"
    assert [p["page_number"] for p in client.get(f"/api/documents/{doc['id']}/pages").json()] == [1, 2]  # kept
    issues = {i["code"]: i for i in client.get(f"/api/documents/{doc['id']}/extraction").json()["review_issues"]}
    assert issues["PAGES_NOT_READ"]["severity"] == "error" and "Pages 3 have no text" in issues["PAGES_NOT_READ"]["message"]
    assert "Pages 1–2 were processed by pattern matching only" in issues["SEMANTIC_EXTRACTION_PENDING"]["message"]


def test_unreadable_spots_templates_and_poor_pages_become_review_issues(monkeypatch):
    pages = {1: reading(1, "Grant of INR [unreadable] for the project", unreadable_regions=["amount in clause 3 under a stamp"]),
             2: reading(2, "RECEIPT FORMAT  Received the sum of Rs ______", "receipt_template", section_labels=["Annexure C"]),
             3: reading(3, "faint text", legibility="poor")}
    install(monkeypatch, pages)
    doc = upload(scanned_pdf(SCANNED))
    client.post(f"/api/documents/{doc['id']}/extract")
    issues = {i["code"]: i["message"] for i in client.get(f"/api/documents/{doc['id']}/extraction").json()["review_issues"]}
    assert "amount in clause 3 under a stamp" in issues["UNREADABLE"] and "nothing was guessed" in issues["UNREADABLE"]
    assert "not evidence of a payment" in issues["TEMPLATE_PAGE"]
    assert "Page 3 is hard to read" in issues["POOR_LEGIBILITY"]


def test_rerun_reuses_page_readings(monkeypatch):
    pages = {n: reading(n, t) for n, t in enumerate(SCANNED, 1)}
    calls, _ = install(monkeypatch, pages)
    doc = upload(scanned_pdf(SCANNED))
    client.post(f"/api/documents/{doc['id']}/extract")
    client.post(f"/api/documents/{doc['id']}/extract")
    assert len(calls) == 1  # pages were not read (or sent) again
    assert len([p for p in list_records("document_pages") if p["document_id"] == doc["id"]]) == 3


def test_mixed_pdf_reads_only_pages_without_a_text_layer(monkeypatch):
    pages = {2: reading(2, SCANNED[1], "signature")}
    calls, prompts = install(monkeypatch, pages)
    doc = upload(scanned_pdf(SCANNED, with_text_layer={1, 3}))
    client.post(f"/api/documents/{doc['id']}/extract")
    assert [[n for n, _ in c] for c in calls] == [[2]]
    methods = {p["page_number"]: p["method"] for p in client.get(f"/api/documents/{doc['id']}/pages").json()}
    assert methods == {1: "text_layer", 2: "groq_vision", 3: "text_layer"}
    assert "<<<PAGE 1>>> [read from the PDF text layer]" in prompts[0]


def test_page_image_endpoint(monkeypatch):
    doc = upload(scanned_pdf(SCANNED))
    image = client.get(f"/api/documents/{doc['id']}/pages/3/image")
    assert image.status_code == 200 and image.headers["content-type"] == "image/jpeg" and image.content[:2] == b"\xff\xd8"
    assert image.headers["cache-control"] == "private, no-store"
    assert client.get(f"/api/documents/{doc['id']}/pages/4/image").status_code == 404
    assert client.get(f"/api/documents/{doc['id']}/pages/1/image", params={"dpi": 999}).status_code == 422
    monkeypatch.setattr(settings, "require_firebase_auth", True)
    assert client.get(f"/api/documents/{doc['id']}/pages/1/image").status_code == 401  # never public


def test_parse_batch_and_render_page():
    with pytest.raises(ExtractionFailed) as missing:
        parse_batch(json.dumps({"pages": [reading(1, "x")]}), [1, 2])
    assert missing.value.code == "malformed_response"
    with pytest.raises(ExtractionFailed):
        parse_batch('{"pages": [{"page": 1}]}', [1])
    assert parse_batch(json.dumps({"pages": [reading(2, "b"), reading(1, "a")]}), [1, 2])[0].page == 1
    data = scanned_pdf(SCANNED)
    assert render_page(data, 1)[:2] == b"\xff\xd8"
    with pytest.raises(ValueError):
        render_page(data, 4)


def test_groq_vision_sends_json_and_base64_image(monkeypatch):
    payloads = []

    class Response:
        status_code = 200
        headers = {}

        def json(self):
            return {"choices": [{"message": {"content": json.dumps({"pages": [reading(1, "Fictional text")]})}}]}

    class Client:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers, json):
            payloads.append(json)
            return Response()

    monkeypatch.setattr("app.groq_client.httpx.AsyncClient", Client)
    monkeypatch.setattr(settings, "groq_vision_model", "test-vision")
    result = asyncio.run(groq_read_pages([(1, b"synthetic jpeg")]))
    assert json.loads(result)["pages"][0]["transcript"] == "Fictional text"
    payload = payloads[0]
    assert payload["model"] == "test-vision"
    assert payload["response_format"] == {"type": "json_object"}
    image = payload["messages"][1]["content"][2]["image_url"]["url"]
    assert image.startswith("data:image/jpeg;base64,")
    assert "Return only a valid JSON object" in payload["messages"][0]["content"]


def test_groq_structured_request_retries_rate_limit(monkeypatch):
    payloads = []

    class Response:
        def __init__(self, status_code):
            self.status_code = status_code
            self.headers = {}

        def json(self):
            return {"choices": [{"message": {"content": "{}"}}]}

    class Client:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers, json):
            payloads.append(json)
            return Response(429 if len(payloads) == 1 else 200)

    monkeypatch.setattr("app.groq_client.httpx.AsyncClient", Client)
    monkeypatch.setattr(settings, "groq_max_retries", 2)
    monkeypatch.setattr(settings, "groq_backoff_base_seconds", 0)
    monkeypatch.setattr(settings, "groq_max_retry_wait_seconds", 0)
    assert asyncio.run(structured_completion(
        [{"role": "user", "content": "synthetic prompt"}],
        BatchReading,
        model="test-model",
        timeout=1,
    )) == "{}"
    assert len(payloads) == 2 and payloads[0]["response_format"] == {"type": "json_object"}


def test_groq_vision_rejects_more_than_three_images():
    with pytest.raises(ExtractionFailed) as error:
        asyncio.run(groq_read_pages([(n, b"synthetic") for n in range(1, 5)]))
    assert error.value.code == "invalid_request"


# ---- real sample MOUs: local structure only (no document data is sent to Groq) ----

SAMPLE_PAGES = {"MoU 1.pdf": 9, "MoU 2.pdf": 27, "mou_3.pdf": 28}


@pytest.mark.skipif(not all((SAMPLES / name).exists() for name in SAMPLE_PAGES), reason="sample MOUs not in samples/")
@pytest.mark.parametrize("name, pages", SAMPLE_PAGES.items())
def test_sample_mous_are_detected_as_scanned_and_accepted(name, pages):
    data = (SAMPLES / name).read_bytes()
    doc = upload(data)
    assert doc["page_count"] == pages and all(p["text_status"] == "low_text" for p in doc["pages"])
    assert doc["status"] == "uploaded" and "All pages are scanned images" in doc["warnings"][0]
    assert render_page(data, pages)[:2] == b"\xff\xd8"  # the last page (where schedules may be) renders
