"""Centralised settings loaded from environment / .env file."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # LLM
    anthropic_api_key: str = Field(..., description="Anthropic API key")
    google_api_key: str | None = Field(None, description="Google Gemini API key (cross-validation)")
    openai_api_key: str | None = None
    primary_llm_model: str = "claude-sonnet-4-6"
    fast_llm_model: str = "claude-haiku-4-5-20251001"
    gemini_model: str = "gemini-2.0-flash"

    # PDF / OCR
    ocr_quality_threshold: int = 100  # chars/page below which OCR is triggered
    tesseract_cmd: str = ""

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # Storage
    upload_dir: Path = Path("/tmp/docu-flow/uploads")
    results_dir: Path = Path("/tmp/docu-flow/results")

    # Logging
    log_level: str = "INFO"

    def ensure_dirs(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()  # type: ignore[call-arg]
