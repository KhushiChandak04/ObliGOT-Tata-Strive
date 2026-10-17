"""Single lazily initialized Firebase Admin app shared by Firestore access and token verification."""
from app.config import settings

_app = None

class FirebaseUnavailable(RuntimeError):
    """Firebase Admin cannot be used (not installed, not configured, or failed to initialize)."""

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
            _app = firebase_admin.initialize_app(options=options)
        except Exception as exc:
            raise FirebaseUnavailable(f"Firebase Admin initialization failed: {type(exc).__name__}") from exc
    return _app
