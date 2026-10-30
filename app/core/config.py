from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    APP_ENV: str = "development"
    DEMO_MODE: bool = False
    DEMO_PASSWORD: str = ""
    COOKIE_SECURE: bool = False
    SESSION_HOURS: int = 8
    S3_ENDPOINT: str = "http://127.0.0.1:9002"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "docentra-private"
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
    MAX_SESSION_PAGES: int = 30
    OCR_LANGUAGES: str = "vie+eng"
    WORKER_LEASE_SECONDS: int = 180
    FRONTEND_DIR: Path = ROOT / "frontend" / "dist"


@lru_cache
def get_settings() -> Settings:
    return Settings()
