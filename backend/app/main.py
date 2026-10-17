import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app import auth
from app.config import settings
from app.repository import DataStoreUnavailable
from app.routes import router
from app.document_routes import router as document_router

logger = logging.getLogger("obligot")

app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description="ObliGOT partnership management API. Firebase/Firestore is the intended persistent store.",
)
class FirebaseAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Keep health and API docs public for uptime checks and schema discovery.
        path = request.url.path
        if not settings.require_firebase_auth or path in {"/", "/api/health", "/docs", "/openapi.json", "/redoc"}:
            return await call_next(request)
        header = request.headers.get("Authorization", "")
        if not header.lower().startswith("bearer "):
            return JSONResponse(status_code=401, content={"detail": "Firebase ID token required"})
        try:
            request.state.firebase_user = auth.verify_token(header.split(" ", 1)[1].strip())
        except auth.AuthUnavailable as exc:
            logger.error("Token verification unavailable: %s", exc)
            return JSONResponse(status_code=503, content={"detail": "Authentication service unavailable. Check the backend Firebase configuration."})
        except auth.InvalidToken:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired Firebase ID token"})
        return await call_next(request)

app.add_middleware(FirebaseAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(router, prefix="/api")
app.include_router(document_router, prefix="/api")

@app.exception_handler(DataStoreUnavailable)
async def data_store_unavailable(request, exc: DataStoreUnavailable) -> JSONResponse:
    logger.error("Data store failure: %s", exc, exc_info=exc.__cause__)
    return JSONResponse(status_code=503, content={"detail": "The data store is unavailable. No changes were confirmed; try again shortly."})

@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"app": "ObliGOT", "docs": "/docs", "health": "/api/health"}
