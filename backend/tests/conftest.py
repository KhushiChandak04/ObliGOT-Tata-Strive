import pytest

from app import repository
from app.config import settings


@pytest.fixture(autouse=True)
def local_settings_do_not_apply(monkeypatch):
    """Tests must not depend on a developer's backend/.env (auth, Firebase credentials, Gemini key)."""
    monkeypatch.setattr(settings, "require_firebase_auth", False)
    monkeypatch.setattr(settings, "firebase_credentials_file", "")
    monkeypatch.setattr(settings, "gemini_api_key", "")


@pytest.fixture(autouse=True)
def isolated_memory_store():
    """Run every test against the in-memory store and restore it afterwards, so tests cannot leak records."""
    saved = {name: dict(records) for name, records in repository._COLLECTIONS.items()}
    repository._firestore_client = None
    repository._firestore_attempted = True
    yield
    for name, records in repository._COLLECTIONS.items():
        records.clear()
        records.update(saved[name])
