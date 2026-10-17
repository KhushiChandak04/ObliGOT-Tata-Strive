"""Optional Firebase ID-token verification for API routes.

Keep REQUIRE_FIREBASE_AUTH=false only for local development. Enable it for a
public deployment after the frontend sends Firebase ID tokens in Authorization.
"""
from fastapi import Header, HTTPException
from app.config import settings

def verify_bearer_token(authorization: str | None = Header(default=None)) -> dict | None:
    if not settings.require_firebase_auth:
        return None
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Firebase ID token required")
    token = authorization.split(" ", 1)[1].strip()
    try:
        from firebase_admin import auth
        return auth.verify_id_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired Firebase ID token") from exc
