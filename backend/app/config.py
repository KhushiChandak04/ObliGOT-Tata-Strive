from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "ObliGOT API"
    environment: str = "development"
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    firebase_project_id: str = ""
    require_firebase_auth: bool = False
    # Business timezone offset used for "today" in deadline rules (IST = +330 minutes).
    business_utc_offset_minutes: int = 330

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

settings = Settings()
