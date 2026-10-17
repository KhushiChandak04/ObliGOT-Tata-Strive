"""Document intake (Step P2a): upload validation, page-by-page inspection, low-text detection, private storage.

All PDFs are synthetic, generated in the test; none is a real agreement.
"""
import pymupdf
import pytest
from fastapi.testclient import TestClient

from app import document_storage
from app.config import settings
from app.main import app
from app.repository import list_records

client = TestClient(app)


@pytest.fixture(autouse=True)
def private_store(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "document_storage_dir", str(tmp_path / "store"))
    return tmp_path / "store"


def make_pdf(pages: list[str], password: str | None = None) -> bytes:
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        if text:
            page.insert_textbox(pymupdf.Rect(50, 50, 550, 800), text, fontsize=10)
    if password:
        data = doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw=password, user_pw=password)
    else:
        data = doc.tobytes()
    doc.close()
    return data


def clause(n: int) -> str:
    return f"SYNTHETIC TEST AGREEMENT - page {n}. Clause {n}.1: the implementing partner shall report quarterly (fictional)."


def upload(data: bytes, filename: str = "synthetic-mou.pdf", **fields):
    form = {"kind": "mou", **fields}
    return client.post("/api/documents", data=form, files={"file": (filename, data, "application/pdf")})


def test_text_pdf_is_inspected_page_by_page_and_stored_privately(private_store):
    response = upload(make_pdf([clause(1), clause(2), clause(3)]), partner_id="demo-001")
    assert response.status_code == 201, response.text
    doc = response.json()
    assert doc["status"] == "uploaded" and doc["page_count"] == 3 and doc["warnings"] == []
    assert [p["page_number"] for p in doc["pages"]] == [1, 2, 3]
    assert all(p["text_status"] == "text" and p["char_count"] > 40 for p in doc["pages"])
    assert doc["storage_ref"] == f"local:{doc['id']}.pdf"
    assert (private_store / f"{doc['id']}.pdf").read_bytes()[:5] == b"%PDF-"
    assert doc["partner_id"] == "demo-001" and doc["source_label"] == "user" and doc["uploaded_by"] == "Demo user"
    assert client.get(f"/api/documents/{doc['id']}").json() == doc


def test_upload_does_not_extract_or_approve_anything():
    doc = upload(make_pdf([clause(1)])).json()
    assert doc["status"] != "approved" and doc["approved_by"] is None
    for collection in ("agreements", "projects", "milestones", "reports", "finance"):
        assert not any(r.get("source_label") == "user" for r in list_records(collection))


def test_long_document_is_not_truncated():
    pages = [clause(n) for n in range(1, 61)]
    doc = upload(make_pdf(pages)).json()
    assert doc["page_count"] == 60 and len(doc["pages"]) == 60
    stored = document_storage.load_pdf(doc["storage_ref"])
    with pymupdf.open(stream=stored, filetype="pdf") as reopened:
        assert "page 60" in reopened[59].get_text()


def test_blank_or_scanned_pages_are_flagged_not_treated_as_extracted():
    doc = upload(make_pdf([clause(1), "", clause(3)])).json()
    assert doc["status"] == "uploaded"
    assert [p["text_status"] for p in doc["pages"]] == ["text", "low_text", "text"]
    assert doc["warnings"] and "Page 2 has little or no embedded text" in doc["warnings"][0]


def test_pdf_without_any_text_is_blocked_with_extraction_guidance():
    doc = upload(make_pdf(["", ""])).json()
    assert doc["status"] == "blocked"
    assert "Configure Groq vision or install Tesseract OCR to extract text" in doc["warnings"][0]


def test_non_pdf_empty_and_oversized_files_are_rejected(monkeypatch):
    assert upload(b"Name,Amount\nX,1\n", "data.csv").status_code == 415
    assert upload(b"MZ\x90\x00 not a pdf", "renamed.pdf").status_code == 415
    assert upload(b"", "empty.pdf").status_code == 422
    monkeypatch.setattr(settings, "max_document_mb", 0)
    assert upload(make_pdf([clause(1)])).status_code == 413
    assert list_records("documents") == []


def test_damaged_and_password_protected_pdfs_are_recorded_as_failed(private_store):
    damaged = upload(b"%PDF-1.7\n this is not really a pdf", "damaged.pdf").json()
    assert damaged["status"] == "failed" and "could not be opened" in damaged["error"]
    assert damaged["storage_ref"] is None and not private_store.exists()
    locked = upload(make_pdf([clause(1)], password="synthetic"), "locked.pdf").json()
    assert locked["status"] == "failed" and "password-protected" in locked["error"]


def test_page_limit_rejects_instead_of_truncating(monkeypatch):
    monkeypatch.setattr(settings, "max_document_pages", 2)
    doc = upload(make_pdf([clause(1), clause(2), clause(3)])).json()
    assert doc["status"] == "failed" and "3 pages; the limit is 2" in doc["error"]


def test_same_file_can_be_uploaded_twice_as_separate_documents():
    data = make_pdf([clause(1)])
    first = upload(data).json()
    second = upload(data)
    assert second.status_code == 201
    assert second.json()["id"] != first["id"]
    assert second.json()["sha256"] == first["sha256"]
    assert len(list_records("documents")) == 2


def test_kind_and_links_are_validated():
    data = make_pdf([clause(1)])
    assert upload(data, kind="contract").status_code == 422
    assert upload(data, partner_id="nope").status_code == 404
    assert upload(data, agreement_id="nope").status_code == 404
    agreement = next(a for a in list_records("agreements") if a["partner_id"] == "demo-001")
    assert upload(data, agreement_id=agreement["id"], partner_id="demo-002").status_code == 422
    doc = upload(data, kind="addendum", agreement_id=agreement["id"]).json()
    assert doc["partner_id"] == "demo-001"  # taken from the agreement


def test_addendum_without_target_agreement_asks_for_a_choice():
    doc = upload(make_pdf([clause(1)]), kind="addendum").json()
    assert any("Choose the agreement this addendum amends" in w for w in doc["warnings"])


def test_unsafe_filename_is_kept_for_display_only(private_store):
    doc = upload(make_pdf([clause(1)]), "..\\..\\evil/name.pdf").json()
    assert doc["filename"] == "name.pdf"
    assert document_storage.safe_display_name("a/b\\c\x00\x1fd.pdf") == "cd.pdf"
    assert document_storage.safe_display_name(None) == "document.pdf"
    assert [p.name for p in private_store.iterdir()] == [f"{doc['id']}.pdf"]
    with pytest.raises(ValueError):
        document_storage.load_pdf("local:../../etc/passwd")


def test_list_filters_and_404():
    a = upload(make_pdf([clause(1)]), partner_id="demo-001").json()
    upload(make_pdf([clause(2)]), kind="addendum", partner_id="demo-002")
    assert [d["id"] for d in client.get("/api/documents", params={"partner_id": "demo-001"}).json()] == [a["id"]]
    assert len(client.get("/api/documents", params={"kind": "addendum"}).json()) == 1
    assert client.get("/api/documents", params={"status": "bogus"}).status_code == 422
    assert client.get("/api/documents/doc-000000000000").status_code == 404


def test_upload_is_logged_and_blocks_partner_delete():
    doc = upload(make_pdf([clause(1)]), partner_id="demo-003").json()
    events = client.get("/api/activities", params={"limit": 5}).json()
    assert events[0]["event"] == "document_uploaded" and events[0]["entity_id"] == doc["id"]
    response = client.delete("/api/partners/demo-003")
    assert response.status_code == 409 and "documents" in response.text


def test_json_body_is_rejected():
    assert client.post("/api/documents", json={"kind": "mou"}).status_code == 415
