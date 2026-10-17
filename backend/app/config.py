from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "ObliGOT API"
    environment: str = "development"
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_seconds: float = 20.0
    firebase_project_id: str = ""
    require_firebase_auth: bool = False
    # Business timezone offset used for "today" in deadline rules (IST = +330 minutes).
    business_utc_offset_minutes: int = 330
    # Private folder for uploaded PDFs (relative paths resolve inside backend/; git-ignored).
    document_storage_dir: str = ".document_store"
    max_document_mb: int = 20
    max_document_pages: int = 500

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

settings = Settings()
