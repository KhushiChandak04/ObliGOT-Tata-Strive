"""Single lazily initialized Firebase Admin app shared by Firestore access and token verification."""
from pathlib import Path

from app.config import settings

_app = None

class FirebaseUnavailable(RuntimeError):
    """Firebase Admin cannot be used (not installed, not configured, or failed to initialize)."""

def _credentials_path(value: str) -> str:
    """Relative paths resolve inside backend/, so the app works from any working directory."""
    path = Path(value)
    return str(path if path.is_absolute() else Path(__file__).resolve().parent.parent / path)

def get_firebase_app():
    global _app
    if _app is not None:
        return _app
    try:
        import firebase_admin
    except ImportError as exc:
        raise FirebaseUnavailable("firebase-admin is not installed") from exc
    try:
        _app = firebase_admin.get_app()
    except ValueError:
        options = {"projectId": settings.firebase_project_id} if settings.firebase_project_id else None
        try:
            # A service-account file named in settings (.env) is used directly; otherwise Application Default
            # Credentials (the GOOGLE_APPLICATION_CREDENTIALS environment variable or the Cloud Run identity).
            credential = None
            if settings.firebase_credentials_file:
                from firebase_admin import credentials
                credential = credentials.Certificate(_credentials_path(settings.firebase_credentials_file))
            _app = firebase_admin.initialize_app(credential, options=options)
        except Exception as exc:
            raise FirebaseUnavailable(f"Firebase Admin initialization failed: {type(exc).__name__}") from exc
    return _app
