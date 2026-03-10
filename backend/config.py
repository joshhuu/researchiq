from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # ── Core settings ──────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./paperiq.db"
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 20
    api_secret_key: str = "dev_secret"

    # ── NLP model settings ────────────────────────────────────────────────────
    # Sentence-transformer model used for semantic similarity tasks.
    # Cached locally after first download.
    sentence_transformer_model: str = "all-MiniLM-L6-v2"

    # ── Optional legacy / external API (not used by NLP pipeline) ─────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemma-3-27b-it"

    class Config:
        env_file = ".env"


settings = Settings()
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
