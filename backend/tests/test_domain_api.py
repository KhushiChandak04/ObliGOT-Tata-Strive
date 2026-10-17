from fastapi.testclient import TestClient
from app.main import app
from app import repository


def reset_projects():
    repository._COLLECTIONS["projects"].clear()
    repository._firestore_client = None
    repository._firestore_attempted = True


def test_project_crud():
    reset_projects()
    client = TestClient(app)
    created = client.post("/api/projects", json={"name": "Sample Project", "status": "active", "amount": 1250})
    assert created.status_code == 201, created.text
    record = created.json()
    assert record["name"] == "Sample Project"
    project_id = record["id"]
    fetched = client.get(f"/api/projects/{project_id}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["name"] == "Sample Project"
    updated = client.patch(f"/api/projects/{project_id}", json={"status": "completed"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["status"] == "completed"
    assert client.delete(f"/api/projects/{project_id}").status_code == 204
    assert client.get(f"/api/projects/{project_id}").status_code == 404


def test_import_preview_validation():
    client = TestClient(app)
    result = client.post("/api/import/preview", json={"entity_type": "finance-records", "rows": [{"name": "Invoice", "amount": "bad"}, {"amount": 20}]})
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["total_rows"] == 2
    assert data["valid_count"] == 0
    assert data["invalid_count"] == 2
    assert data["committed"] is False


def test_openapi_has_expected_routes():
    paths = app.openapi()["paths"]
    assert "/api/health" in paths
    assert "/api/projects" in paths
    assert {"get", "post"}.issubset(paths["/api/projects"].keys())
    assert {"get", "patch", "delete"}.issubset(paths["/api/projects/{project_id}"].keys())
    assert "post" in paths["/api/import/preview"]
    expected_detail_methods = {
        "/api/agreements/{agreement_id}": {"get", "patch", "delete"},
        "/api/projects/{project_id}": {"get", "patch", "delete"},
        "/api/finance/{finance_id}": {"get", "patch", "delete"},
        "/api/reports/{report_id}": {"get", "patch", "delete"},
        "/api/actions/{action_id}": {"get", "patch", "delete"},
        "/api/followups/{followup_id}": {"get", "patch", "delete"},
    }
    for path, methods in expected_detail_methods.items():
        assert path in paths, f"Missing route: {path}"
        assert methods.issubset(paths[path]), f"Missing methods for {path}: {methods - set(paths[path])}"


def test_agreement_finance_report_detail_routes():
    for name in ("agreements", "finance", "reports"):
        repository._COLLECTIONS[name].clear()
    repository._firestore_client = None
    repository._firestore_attempted = True
    client = TestClient(app)
    partner_id = "demo-001"

    agreement = client.post("/api/agreements", json={"partner_id": partner_id, "title": "Sample agreement"})
    assert agreement.status_code == 201, agreement.text
    agreement_id = agreement.json()["id"]
    assert client.get(f"/api/agreements/{agreement_id}").status_code == 200
    updated_agreement = client.patch(f"/api/agreements/{agreement_id}", json={"status": "active"})
    assert updated_agreement.status_code == 200, updated_agreement.text
    assert updated_agreement.json()["status"] == "active"
    assert client.delete(f"/api/agreements/{agreement_id}").status_code == 204

    finance = client.post("/api/finance", json={"partner_id": partner_id, "record_type": "invoice", "title": "Sample invoice", "amount": 1250})
    assert finance.status_code == 201, finance.text
    finance_id = finance.json()["id"]
    assert client.get(f"/api/finance/{finance_id}").status_code == 200
    updated_finance = client.patch(f"/api/finance/{finance_id}", json={"status": "paid"})
    assert updated_finance.status_code == 200, updated_finance.text
    assert updated_finance.json()["status"] == "paid"
    assert client.delete(f"/api/finance/{finance_id}").status_code == 204

    report = client.post("/api/reports", json={"partner_id": partner_id, "title": "Sample quarterly report", "report_type": "quarterly"})
    assert report.status_code == 201, report.text
    report_id = report.json()["id"]
    assert client.get(f"/api/reports/{report_id}").status_code == 200
    updated_report = client.patch(f"/api/reports/{report_id}", json={"status": "submitted"})
    assert updated_report.status_code == 200, updated_report.text
    assert updated_report.json()["status"] == "submitted"
    assert client.delete(f"/api/reports/{report_id}").status_code == 204


def test_csv_import_preview_is_non_destructive():
    client = TestClient(app)
    response = client.post("/api/import/preview", files={"file": ("rows.csv", "name,amount\nInvoice A,100\nInvoice B,bad\n", "text/csv")})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total_rows"] == 2
    assert data["committed"] is False
    assert data["valid_count"] == 1
    assert data["invalid_count"] == 1


def test_dashboard_findings_clear_when_report_is_submitted():
    from datetime import timedelta
    from app.rules import business_today
    for name in ("agreements", "finance", "reports"):
        repository._COLLECTIONS[name].clear()
    repository._firestore_client = None
    repository._firestore_attempted = True
    client = TestClient(app)
    past = (business_today() - timedelta(days=5)).isoformat()
    report_id = client.post("/api/reports", json={"partner_id": "demo-001", "title": "Overdue sample report", "due_date": past, "status": "due"}).json()["id"]
    client.post("/api/finance", json={"partner_id": "demo-001", "record_type": "fund_received", "title": "Sample receipt"})

    dashboard = client.get("/api/dashboard").json()
    assert dashboard["as_of"] == business_today().isoformat()
    finding_ids = {f["record_id"]: f for f in dashboard["findings"]}
    assert set(finding_ids) == {report_id}
    assert finding_ids[report_id]["issue"] == "Overdue: Overdue sample report"

    assert client.patch(f"/api/reports/{report_id}", json={"status": "submitted"}).status_code == 200
    assert client.get("/api/dashboard").json()["findings"] == []
