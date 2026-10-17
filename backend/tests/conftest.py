import pytest

from app import repository
from app.config import settings


@pytest.fixture(autouse=True)
def local_settings_do_not_apply(monkeypatch):
    """Tests must not depend on a developer's backend/.env or credentials."""
    monkeypatch.setattr(settings, "require_firebase_auth", False)
    monkeypatch.setattr(settings, "firebase_credentials_file", "")
    monkeypatch.setattr(settings, "groq_api_key", "")
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "ocr_enabled", False)  # OCR tests switch it on with a fake; results never depend on the machine


@pytest.fixture(autouse=True)
def isolated_memory_store(monkeypatch):
    """Give each test an isolated repository adapter without contacting Firestore."""
    saved = {name: dict(records) for name, records in repository._COLLECTIONS.items()}
    saved_demo = {name: dict(records) for name, records in repository._DEMO_COLLECTIONS.items()}
    repository._firestore_client = None
    repository._firestore_attempted = True
    monkeypatch.setattr(repository, "_DEMO_MODE", False)
    monkeypatch.setattr(repository, "_AUTO_DEMO_FALLBACK", False)
    monkeypatch.setattr(repository, "_TEST_MEMORY_STORE", True)
    yield
    for name, records in repository._COLLECTIONS.items():
        records.clear()
        records.update(saved[name])
    for name, records in repository._DEMO_COLLECTIONS.items():
        records.clear()
        records.update(saved_demo[name])
