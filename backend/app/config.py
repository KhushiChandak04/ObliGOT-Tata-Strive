from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "ObliGOT API"
    environment: str = "development"
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    gemini_api_key: str = ""
    # gemini-2.5-flash is no longer available to new API projects (404 on 17 Oct 2026); 3.5 Flash reads images and PDFs.
    gemini_model: str = "gemini-3.5-flash"
    gemini_timeout_seconds: float = 20.0
    firebase_project_id: str = ""
    # Path to a service-account JSON (git-ignored; relative paths resolve inside backend/). Empty = default credentials.
    firebase_credentials_file: str = ""
    require_firebase_auth: bool = False
    # Business timezone offset used for "today" in deadline rules (IST = +330 minutes).
    business_utc_offset_minutes: int = 330
    # Private folder for uploaded PDFs (relative paths resolve inside backend/; git-ignored).
    document_storage_dir: str = ".document_store"
    max_document_mb: int = 20
    max_document_pages: int = 500
    # Extraction: pages are sent in chunks of whole pages up to this many characters; one Gemini call per chunk.
    extraction_chunk_chars: int = 40000
    gemini_extraction_timeout_seconds: float = 120.0
    # Scanned pages: rendered to images and read by Gemini in small batches (AI transcription, reviewed by a person).
    vision_batch_pages: int = 4
    page_render_dpi: int = 150
    # Waits (seconds) before retrying a Gemini call that hit a rate limit; one retry per entry.
    gemini_retry_delays: list[float] = [20.0, 40.0]
    # Tried in order when the main model answers "overloaded" (503) or its quota is used up (429).
    gemini_fallback_models: list[str] = ["gemini-flash-latest"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

settings = Settings()
