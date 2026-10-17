from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rules import business_today

client = TestClient(app)


def create(**overrides):
    return client.post("/api/agreements", json={"partner_id": "demo-001", "title": "Test MOU", **overrides})


def test_new_fields_default_for_create_and_existing_records():
    body = create().json()
    assert body["signed_copy"] == "unknown" and body["renewal_status"] == "none"
    assert body["project_id"] is None and body["opportunity_id"] is None
    legacy = client.get("/api/agreements/demo-agreement-003").json()
    assert legacy["signed_copy"] == "unknown"


def test_enum_fields_are_validated():
    assert create(signed_copy="maybe").status_code == 422
    assert create(renewal_status="later").status_code == 422
    assert client.patch("/api/agreements/demo-agreement-001", json={"signed_copy": "maybe"}).status_code == 422


@pytest.mark.parametrize("url", ["javascript:alert(1)", "data:text/html,<script>x</script>", "ftp://example.org/a.pdf", "example.org/a.pdf"])
def test_document_url_must_be_http(url):
    assert create(document_url=url).status_code == 422


def test_document_url_accepts_https_and_blank_becomes_null():
    assert create(document_url="https://example.org/mou.pdf").json()["document_url"] == "https://example.org/mou.pdf"
    assert create(document_url="   ").json()["document_url"] is None
    cleared = client.patch("/api/agreements/demo-agreement-001", json={"document_url": None})
    assert cleared.status_code == 200 and cleared.json()["document_url"] is None


def test_linked_project_and_opportunity_must_exist_and_match_partner():
    assert create(project_id="demo-project-001", opportunity_id="demo-opportunity-001").status_code == 201
    assert create(project_id="missing-project").status_code == 404
    assert create(opportunity_id="missing-opportunity").status_code == 404
    wrong = create(opportunity_id="demo-opportunity-002")  # belongs to demo-002
    assert wrong.status_code == 422 and "different partner" in wrong.json()["detail"]
    patched = client.patch("/api/agreements/demo-agreement-002", json={"opportunity_id": "demo-opportunity-003"})
    assert patched.status_code == 422
    # Moving an agreement to another partner re-checks existing links.
    assert client.patch("/api/agreements/demo-agreement-001", json={"partner_id": "demo-002"}).status_code == 422


def test_expiring_within_days_filter_uses_business_date_inclusively():
    today = business_today()
    on_today = create(status="active", expiry_date=today.isoformat()).json()["id"]
    on_horizon = create(status="active", expiry_date=(today + timedelta(days=30)).isoformat()).json()["id"]
    beyond = create(status="active", expiry_date=(today + timedelta(days=31)).isoformat()).json()["id"]
    expired = create(status="active", expiry_date=(today - timedelta(days=1)).isoformat()).json()["id"]
    draft = create(status="draft", expiry_date=(today + timedelta(days=5)).isoformat()).json()["id"]
    ids = {r["id"] for r in client.get("/api/agreements", params={"expiring_within_days": 30}).json()}
    assert {on_today, on_horizon, "demo-agreement-001"} <= ids
    assert not ids & {beyond, expired, draft, "demo-agreement-002", "demo-agreement-003"}
    narrow = {r["id"] for r in client.get("/api/agreements", params={"expiring_within_days": 20, "partner_id": "demo-001"}).json()}
    assert "demo-agreement-001" not in narrow  # demo MOU expires in 21 days
    assert client.get("/api/agreements", params={"expiring_within_days": -1}).status_code == 422
