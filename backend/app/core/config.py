from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    APP_SECRET_KEY: str = "change-this-to-a-random-string"
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://maillard:changeme@db:5432/maillard_db"

    # Storage
    UPLOAD_DIR: Path = Path("./data/raw_uploads")
    PROCESSED_DIR: Path = Path("./data/processed_text")
    MAX_UPLOAD_SIZE_MB: int = 20

    # S3 (prod)
    AWS_S3_BUCKET: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # OCR
    TESSERACT_CMD: str = "/usr/bin/tesseract"
    OCR_LANGUAGE: str = "eng"
    OCR_DPI: int = 300

    # LLM (optional / future)
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    @property
    def database_url_sync(self) -> str:
        """Synchronous URL for Alembic (strips +asyncpg driver prefix)."""
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
