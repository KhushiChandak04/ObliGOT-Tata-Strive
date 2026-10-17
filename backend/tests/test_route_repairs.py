from fastapi.testclient import TestClient
from app.main import app
from app import repository


def client():
    repository._firestore_client = None
    repository._firestore_attempted = True
    return TestClient(app)


def test_action_patch_null_clears_optional_field():
    c = client()
    action_id = c.post("/api/actions", json={"title": "Clearable action", "due_date": "2026-11-01"}).json()["id"]
    response = c.patch(f"/api/actions/{action_id}", json={"due_date": None})
    assert response.status_code == 200, response.text
    assert response.json()["due_date"] is None
    assert c.get(f"/api/actions/{action_id}").json()["due_date"] is None


def test_action_patch_omitted_fields_are_unchanged():
    c = client()
    action_id = c.post("/api/actions", json={"title": "Partial update", "due_date": "2026-11-01", "owner": "Ops"}).json()["id"]
    response = c.patch(f"/api/actions/{action_id}", json={"status": "in_review"})
    assert response.status_code == 200, response.text
    assert response.json()["due_date"] == "2026-11-01" and response.json()["owner"] == "Ops"


def test_partner_patch_null_clears_optional_but_rejects_required():
    c = client()
    partner_id = c.post("/api/partners", json={"name": "Patchable Partner", "category": "Other", "owner": "Ops", "contact_name": "A Person"}).json()["id"]
    cleared = c.patch(f"/api/partners/{partner_id}", json={"contact_name": None})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["contact_name"] is None
    assert c.patch(f"/api/partners/{partner_id}", json={"name": None}).status_code == 422
    assert c.get(f"/api/partners/{partner_id}").json()["name"] == "Patchable Partner"


def test_patch_missing_record_returns_404():
    c = client()
    assert c.patch("/api/actions/does-not-exist", json={"status": "done"}).status_code == 404
    assert c.patch("/api/partners/does-not-exist", json={"owner": "Ops"}).status_code == 404


def test_agreement_expiry_before_start_rejected_on_create_and_patch():
    c = client()
    bad = c.post("/api/agreements", json={"partner_id": "demo-001", "title": "Bad MOU", "start_date": "2026-05-01", "expiry_date": "2026-01-01"})
    assert bad.status_code == 422
    agreement_id = c.post("/api/agreements", json={"partner_id": "demo-001", "title": "Good MOU", "start_date": "2026-05-01", "expiry_date": "2027-04-30"}).json()["id"]
    assert c.patch(f"/api/agreements/{agreement_id}", json={"expiry_date": "2026-04-01"}).status_code == 422
    assert c.get(f"/api/agreements/{agreement_id}").json()["expiry_date"] == "2027-04-30"
    assert c.patch(f"/api/agreements/{agreement_id}", json={"expiry_date": "2026-05-01"}).status_code == 200


def test_project_end_before_start_rejected_on_create_and_patch():
    c = client()
    assert c.post("/api/projects", json={"name": "Bad project", "start_date": "2026-05-01", "end_date": "2026-04-30"}).status_code == 422
    project_id = c.post("/api/projects", json={"name": "Good project", "start_date": "2026-05-01"}).json()["id"]
    assert c.patch(f"/api/projects/{project_id}", json={"end_date": "2026-04-01"}).status_code == 422


def test_multipart_import_rejects_unknown_entity_type():
    c = client()
    bad = c.post("/api/import/preview", data={"entity_type": "bogus"}, files={"file": ("a.csv", "name\nX\n", "text/csv")})
    assert bad.status_code == 422
    good = c.post("/api/import/preview", data={"entity_type": "agreements"}, files={"file": ("a.csv", "name\nX\n", "text/csv")})
    assert good.status_code == 200 and good.json()["entity_type"] == "agreements"
    default = c.post("/api/import/preview", files={"file": ("a.csv", "name\nX\n", "text/csv")})
    assert default.status_code == 200 and default.json()["entity_type"] == "projects"


def test_followups_list_with_filters():
    repository._COLLECTIONS["followups"].clear()
    c = client()
    first = c.post("/api/followups", json={"title": "Call partner", "owner": "Ops", "related_partner_id": "demo-001"}).json()["id"]
    second = c.post("/api/followups", json={"title": "Email partner", "owner": "Ops", "related_partner_id": "demo-002"}).json()["id"]
    c.patch(f"/api/followups/{second}", json={"status": "done"})
    assert {r["id"] for r in c.get("/api/followups").json()} == {first, second}
    assert [r["id"] for r in c.get("/api/followups", params={"status": "open"}).json()] == [first]
    assert [r["id"] for r in c.get("/api/followups", params={"related_partner_id": "demo-002"}).json()] == [second]
