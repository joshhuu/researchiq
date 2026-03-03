from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    gemini_api_key: str = "set_in_env"
    database_url: str = "sqlite+aiosqlite:///./paperiq.db"
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 20
    gemini_model: str = "gemma-3-27b-it"
    api_secret_key: str = "dev_secret"

    class Config:
        env_file = ".env"


settings = Settings()
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
