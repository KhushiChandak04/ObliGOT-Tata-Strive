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
    # Gemini resilience. Retryable errors (rate limit, overload, timeout) are retried with exponential backoff;
    # Google's suggested retry delay is used when given. Permanent errors are never retried.
    gemini_max_retries: int = 3
    gemini_backoff_base_seconds: float = 4.0
    gemini_max_retry_wait_seconds: float = 60.0
    gemini_max_concurrency: int = 2
    # Tried in order when the main model is overloaded, rate-limited, out of daily quota, or not available to the key.
    gemini_fallback_models: list[str] = ["gemini-flash-latest"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

settings = Settings()
