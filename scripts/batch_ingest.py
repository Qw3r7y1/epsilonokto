"""Batch ingest all files from a directory.

Usage: python scripts/batch_ingest.py ./data/raw_uploads/
"""
import asyncio
import sys
from pathlib import Path

from app.db.session import async_session
from app.services.ingestion.router import IngestionRouter
from app.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger("batch_ingest")


class FakeUploadFile:
    """Mimic FastAPI UploadFile for batch processing."""

    def __init__(self, path: Path):
        self.filename = path.name
        self._path = path
        suffix = path.suffix.lower()
        self.content_type = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".tiff": "image/tiff",
        }.get(suffix, "application/octet-stream")

    async def read(self) -> bytes:
        return self._path.read_bytes()


async def main(directory: str):
    folder = Path(directory)
    if not folder.is_dir():
        print(f"Error: {directory} is not a directory")
        sys.exit(1)

    files = [
        f for f in folder.iterdir()
        if f.suffix.lower() in (".pdf", ".png", ".jpg", ".jpeg", ".tiff")
    ]

    logger.info(f"Found {len(files)} files to ingest")

    router = IngestionRouter()

    async with async_session() as db:
        for f in files:
            try:
                upload = FakeUploadFile(f)
                result = await router.process(file=upload, db=db)
                logger.info(f"✓ {f.name} → {result.status}")
            except Exception as e:
                logger.error(f"✗ {f.name} → {e}")
        await db.commit()

    logger.info("Batch ingestion complete")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/batch_ingest.py <directory>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
