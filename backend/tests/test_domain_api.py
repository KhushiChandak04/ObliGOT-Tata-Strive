from fastapi.testclient import TestClient
from app.main import app
from app import domain_store

def test_domain_crud(tmp_path, monkeypatch):
    monkeypatch.setattr(domain_store, "DB_PATH", tmp_path / "test.db")
    client = TestClient(app)
    created = client.post("/api/projects", json={"name": "Sample Project", "status": "active", "amount": 1250})
    assert created.status_code == 201
    record = created.json()
    assert record["name"] == "Sample Project"
    assert client.get(f"/api/projects/{record['id']}").status_code == 200
    assert client.patch(f"/api/projects/{record['id']}", json={"status": "completed"}).json()["status"] == "completed"
    assert client.delete(f"/api/projects/{record['id']}").status_code == 204

def test_import_preview_validation():
    client = TestClient(app)
    result = client.post("/api/import/preview", json={"entity_type": "finance-records", "rows": [{"name": "Invoice", "amount": "bad"}, {"amount": 20}]})
    assert result.status_code == 200
    assert result.json()["invalid_count"] == 2
