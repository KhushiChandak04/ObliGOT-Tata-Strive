import pytest

from app import repository
from app.config import settings


@pytest.fixture(autouse=True)
def local_settings_do_not_apply(monkeypatch):
    """Tests must not depend on a developer's backend/.env (auth, Firebase credentials, Gemini key)."""
    monkeypatch.setattr(settings, "require_firebase_auth", False)
    monkeypatch.setattr(settings, "firebase_credentials_file", "")
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "gemini_backoff_base_seconds", 0.0)  # no real waiting on retries in tests
    monkeypatch.setattr(settings, "gemini_max_retry_wait_seconds", 0.0)
    monkeypatch.setattr(settings, "gemini_fallback_models", [])
    monkeypatch.setattr(settings, "ocr_enabled", False)  # OCR tests switch it on with a fake; results never depend on the machine


@pytest.fixture(autouse=True)
def no_real_gemini(monkeypatch):
    """Tests must never send anything to Google. Tests that exercise the client install their own fake."""
    from google import genai

    class Blocked:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("A test tried to call the real Gemini API; install a fake instead")
    monkeypatch.setattr(genai, "Client", Blocked)


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
