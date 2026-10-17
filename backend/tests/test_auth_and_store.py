import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import auth, repository
from app.config import settings


@pytest.fixture
def memory_store():
    repository._firestore_client = None
    repository._firestore_attempted = True
    yield


@pytest.fixture
def auth_required(monkeypatch, memory_store):
    monkeypatch.setattr(settings, "require_firebase_auth", True)


def test_partner_delete_blocked_while_linked_records_exist(memory_store):
    c = TestClient(app)
    partner_id = c.post("/api/partners", json={"name": "Linked Partner", "category": "Other", "owner": "Ops"}).json()["id"]
    agreement_id = c.post("/api/agreements", json={"partner_id": partner_id, "title": "Linked MOU"}).json()["id"]
    c.post("/api/actions", json={"title": "Linked action", "related_partner_id": partner_id})

    blocked = c.delete(f"/api/partners/{partner_id}")
    assert blocked.status_code == 409
    assert "agreements: 1" in blocked.json()["detail"] and "actions: 1" in blocked.json()["detail"]
    assert c.get(f"/api/partners/{partner_id}").status_code == 200


def test_partner_delete_succeeds_without_links_and_404_when_missing(memory_store):
    c = TestClient(app)
    partner_id = c.post("/api/partners", json={"name": "Unlinked Partner", "category": "Other", "owner": "Ops"}).json()["id"]
    assert c.delete(f"/api/partners/{partner_id}").status_code == 204
    assert c.delete(f"/api/partners/{partner_id}").status_code == 404


class BrokenFirestore:
    def collection(self, name):
        raise ConnectionError("simulated network failure")


def test_firestore_failure_returns_503_not_500(monkeypatch):
    monkeypatch.setattr(repository, "_TEST_MEMORY_STORE", False)
    monkeypatch.setattr(repository, "_firestore_client", BrokenFirestore())
    monkeypatch.setattr(repository, "_firestore_attempted", True)
    c = TestClient(app, raise_server_exceptions=False)
    for response in (c.get("/api/partners"), c.get("/api/partners/demo-001"),
                     c.post("/api/partners", json={"name": "New Partner", "category": "Other", "owner": "Ops"}),
                     c.get("/api/dashboard")):
        assert response.status_code == 503, response.text
        assert "data store is unavailable" in response.json()["detail"]


def test_auth_missing_token_is_401(auth_required):
    assert TestClient(app).get("/api/partners").status_code == 401


def test_auth_health_and_docs_stay_public(auth_required):
    c = TestClient(app)
    assert c.get("/api/health").status_code == 200
    assert c.get("/openapi.json").status_code == 200


def test_auth_invalid_token_is_401(auth_required, monkeypatch):
    def reject(token):
        raise auth.InvalidToken("bad")
    monkeypatch.setattr(auth, "verify_token", reject)
    response = TestClient(app).get("/api/partners", headers={"Authorization": "Bearer bad"})
    assert response.status_code == 401


def test_auth_unavailable_is_503_not_401(auth_required, monkeypatch):
    def unavailable(token):
        raise auth.AuthUnavailable("not configured")
    monkeypatch.setattr(auth, "verify_token", unavailable)
    response = TestClient(app).get("/api/partners", headers={"Authorization": "Bearer something"})
    assert response.status_code == 503


def test_auth_valid_token_passes(auth_required, monkeypatch):
    monkeypatch.setattr(auth, "verify_token", lambda token: {"uid": "user-1"})
    response = TestClient(app).get("/api/partners", headers={"Authorization": "Bearer good"})
    assert response.status_code == 200


def test_verify_token_reports_unavailable_without_firebase_admin(monkeypatch):
    from app import firebase_app
    def missing():
        raise firebase_app.FirebaseUnavailable("firebase-admin is not installed")
    monkeypatch.setattr(auth, "get_firebase_app", missing)
    with pytest.raises(auth.AuthUnavailable):
        auth.verify_token("anything")


def test_credentials_file_setting_is_used_and_resolved_inside_backend(monkeypatch):
    """FIREBASE_CREDENTIALS_FILE in .env must reach the Admin SDK (pydantic settings do not set os.environ)."""
    import firebase_admin
    from firebase_admin import credentials
    from app import firebase_app
    seen = {}
    monkeypatch.setattr(firebase_app, "_app", None)
    monkeypatch.setattr(firebase_admin, "get_app", lambda: (_ for _ in ()).throw(ValueError("no app")))
    monkeypatch.setattr(credentials, "Certificate", lambda path: seen.setdefault("path", path))
    monkeypatch.setattr(firebase_admin, "initialize_app", lambda credential, options=None: seen.update(credential=credential, options=options) or "app")
    monkeypatch.setattr(settings, "firebase_credentials_file", "service-account.json")
    monkeypatch.setattr(settings, "firebase_project_id", "demo-project")
    assert firebase_app.get_firebase_app() == "app"
    assert seen["path"].replace("\\", "/").endswith("backend/service-account.json")
    assert seen["credential"] == seen["path"] and seen["options"] == {"projectId": "demo-project"}