"""Firebase ID-token verification used by the API auth middleware.

Keep REQUIRE_FIREBASE_AUTH=false only for local development. Enable it for a
public deployment after the frontend sends Firebase ID tokens in Authorization.
"""
import logging

from app.firebase_app import FirebaseUnavailable, get_firebase_app

logger = logging.getLogger("obligot.auth")

class AuthUnavailable(RuntimeError):
    """Tokens cannot be verified right now (Firebase not configured or unreachable)."""

class InvalidToken(ValueError):
    """The supplied token is malformed, expired, revoked, or for another project."""

def verify_token(token: str) -> dict:
    try:
        firebase_app = get_firebase_app()
    except FirebaseUnavailable as exc:
        raise AuthUnavailable(str(exc)) from exc
    from firebase_admin import auth
    try:
        return auth.verify_id_token(token, app=firebase_app)
    except auth.CertificateFetchError as exc:
        raise AuthUnavailable("Could not fetch Firebase token certificates") from exc
    except Exception as exc:
        logger.warning("Firebase ID token rejected (%s)", type(exc).__name__)
        raise InvalidToken("Invalid or expired Firebase ID token") from exc
