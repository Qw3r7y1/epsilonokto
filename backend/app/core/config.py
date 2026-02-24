from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "change-me"
    api_prefix: str = "/api/v1"

    # Database
    postgres_user: str = "maillard"
    postgres_password: str = "changeme"
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "maillard_db"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """Sync URL for Alembic migrations."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # File storage
    upload_dir: str = "./data/raw_uploads"
    processed_dir: str = "./data/processed_text"
    max_upload_size_mb: int = 20

    # OCR
    tesseract_cmd: str = "/usr/bin/tesseract"
    ocr_language: str = "eng"

    # Dropbox
    dropbox_access_token: str = ""
    dropbox_folder: str = "/invoices"          # folder to watch inside Dropbox
    dropbox_poll_interval_seconds: int = 300   # how often to check for new files

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
