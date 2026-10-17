from datetime import timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.rules import business_today

client = TestClient(app)


def create(**overrides):
    payload = {"partner_id": "demo-002", "title": "New opportunity", "owner": "Regional Partnerships", **overrides}
    return client.post("/api/opportunities", json=payload)


def test_create_defaults_and_labels():
    response = create()
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["stage"] == "identified" and body["source_label"] == "user"
    assert body["updated_at"] == business_today().isoformat()


def test_create_validation():
    assert create(stage="won").status_code == 422
    assert create(title="x").status_code == 422
    assert create(owner="").status_code == 422
    assert create(partner_id="missing-partner").status_code == 404


def test_list_filters_by_partner_and_stage():
    all_rows = client.get("/api/opportunities").json()
    assert {r["id"] for r in all_rows} >= {"demo-opportunity-001", "demo-opportunity-002", "demo-opportunity-003"}
    assert [r["id"] for r in client.get("/api/opportunities", params={"partner_id": "demo-002"}).json()] == ["demo-opportunity-002"]
    assert [r["id"] for r in client.get("/api/opportunities", params={"stage": "renewal"}).json()] == ["demo-opportunity-001"]


def test_patch_advances_stage_refreshes_updated_at_and_keeps_label():
    response = client.patch("/api/opportunities/demo-opportunity-002", json={"stage": "approval", "next_step_date": None})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stage"] == "approval" and body["next_step_date"] is None
    assert body["updated_at"] == business_today().isoformat()
    assert body["source_label"] == "demo"
    assert client.patch("/api/opportunities/demo-opportunity-002", json={"stage": "bogus"}).status_code == 422
    assert client.patch("/api/opportunities/demo-opportunity-002", json={"partner_id": "missing"}).status_code == 404
    assert client.patch("/api/opportunities/missing", json={"stage": "approval"}).status_code == 404


def test_malformed_json_returns_422_not_500():
    for path in ("/api/opportunities/demo-opportunity-001", "/api/agreements/demo-agreement-001", "/api/projects/demo-project-001"):
        response = client.patch(path, content="{not json", headers={"Content-Type": "application/json"})
        assert response.status_code == 422, (path, response.status_code)
    preview = client.post("/api/import/preview", content="{not json", headers={"Content-Type": "application/json"})
    assert preview.status_code == 422


def test_delete_and_partner_delete_counts_opportunities():
    partner_id = client.post("/api/partners", json={"name": "Pipeline Only Partner", "category": "Other", "owner": "Ops"}).json()["id"]
    opportunity_id = create(partner_id=partner_id, next_step_date=(business_today() + timedelta(days=3)).isoformat()).json()["id"]
    blocked = client.delete(f"/api/partners/{partner_id}")
    assert blocked.status_code == 409 and "opportunities: 1" in blocked.json()["detail"]
    assert client.delete(f"/api/opportunities/{opportunity_id}").status_code == 204
    assert client.get(f"/api/opportunities/{opportunity_id}").status_code == 404
    assert client.delete(f"/api/partners/{partner_id}").status_code == 204
