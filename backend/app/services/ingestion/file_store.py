import os
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("ingestion.file_store")
settings = get_settings()


class FileStore:
    """Save uploaded files to local disk (swap for S3 in prod)."""

    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or settings.upload_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, contents: bytes, filename: str, file_hash: str) -> str:
        """Save file using hash-based naming to avoid collisions."""
        ext = Path(filename).suffix
        safe_name = f"{file_hash[:16]}_{filename}"
        dest = self.base_dir / safe_name

        if dest.exists():
            logger.info(f"File already exists (dedup): {safe_name}")
            return str(dest)

        dest.write_bytes(contents)
        logger.info(f"Saved file: {dest} ({len(contents)} bytes)")
        return str(dest)

    async def read(self, path: str) -> bytes:
        return Path(path).read_bytes()
