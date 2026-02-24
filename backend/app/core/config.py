from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Maillard Back Office"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql://maillard:maillard@localhost:5432/maillard"

    # Storage
    STORAGE_BACKEND: str = "local"  # "local" or "s3"
    LOCAL_UPLOAD_DIR: Path = Path("data/raw_uploads")
    LOCAL_PROCESSED_DIR: Path = Path("data/processed_text")
    LOCAL_EXPORT_DIR: Path = Path("data/exports")

    # S3 (prod)
    AWS_BUCKET: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # OCR
    TESSERACT_CMD: str = "tesseract"
    OCR_DPI: int = 300
    OCR_LANG: str = "eng"

    # File upload limits
    MAX_UPLOAD_SIZE_MB: int = 50

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
