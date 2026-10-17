from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "ObliGOT API"
    environment: str = "development"
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    groq_vision_model: str = "qwen/qwen3.8-27b"
    groq_timeout_seconds: float = 20.0
    groq_document_timeout_seconds: float = 120.0
    groq_max_retries: int = 2
    groq_backoff_base_seconds: float = 2.0
    groq_max_retry_wait_seconds: float = 30.0
    groq_max_concurrency: int = 2
    firebase_project_id: str = ""
    # Path to a service-account JSON (git-ignored; relative paths resolve inside backend/). Empty = default credentials.
    firebase_credentials_file: str = ""
    require_firebase_auth: bool = False
    # Explicit local-only synthetic dataset. Live Firestore remains the default.
    obligot_demo_mode: bool = False
    # When opted in for local demos, switch to the synthetic store after any Firestore init/read/write error.
    obligot_auto_demo_fallback: bool = False
    # Business timezone offset used for "today" in deadline rules (IST = +330 minutes).
    business_utc_offset_minutes: int = 330
    # Regional defaults for Tata STRIVE's Indian agreements (settings, not values in the code).
    default_currency: str = "INR"  # pre-filled on manual finance entries; extracted amounts never get it implicitly
    number_decimal_separator: str = "."  # Indian documents: "." is the decimal point ("1.5 lakh"); "auto" or "," also supported
    date_order: str = "dmy"  # Indian documents write numeric dates day-first; "auto" (unambiguous only) or "mdy" also supported
    # Private folder for uploaded PDFs (relative paths resolve inside backend/; git-ignored).
    document_storage_dir: str = ".document_store"
    max_document_mb: int = 20
    max_document_pages: int = 500
    # Extraction: pages are sent in chunks of whole pages up to this many characters; one Groq call per chunk.
    extraction_chunk_chars: int = 40000
    # Scanned pages: Groq vision currently supports at most three images per request.
    vision_batch_pages: int = 3
    page_render_dpi: int = 150
    # Optional OCR fallback (Tesseract must be installed). Languages as Tesseract codes, e.g. "eng" or "eng+hin".
    ocr_enabled: bool = True
    tesseract_cmd: str = "tesseract"
    ocr_languages: str = "eng"
    ocr_dpi: int = 300
    ocr_timeout_seconds: float = 60.0
    @property
    def groq_available(self) -> bool:
        return bool(self.groq_api_key)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

settings = Settings()
