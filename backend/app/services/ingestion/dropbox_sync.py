"""
Dropbox background sync — polls Dropbox every N seconds and feeds
newly found files into the existing ingestion pipeline.

Start it once from the FastAPI lifespan:

    asyncio.create_task(dropbox_sync_loop())
"""

import asyncio
import hashlib
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import Invoice
from app.db.session import async_session
from app.services.ingestion.dropbox_source import DropboxSource
from app.services.ingestion.pipeline import process_invoice_async

log = get_logger("services.ingestion.dropbox_sync")
settings = get_settings()


async def _ingest_file(filename: str, file_bytes: bytes) -> None:
    """Save a Dropbox file to disk and kick off the ingestion pipeline."""
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    invoice_id = uuid.uuid4()
    suffix = Path(filename).suffix
    dest = upload_dir / f"{invoice_id}{suffix}"
    dest.write_bytes(file_bytes)

    file_type = suffix.lstrip(".").lower() or "unknown"

    async with async_session() as session:
        invoice = Invoice(
            id=invoice_id,
            original_filename=filename,
            stored_path=str(dest),
            file_hash=file_hash,
            file_type=file_type,
            status="pending",
        )
        session.add(invoice)
        await session.commit()

    log.info("Queuing Dropbox file for processing: %s → invoice %s", filename, invoice_id)
    asyncio.create_task(process_invoice_async(invoice_id=invoice_id))


async def run_dropbox_sync() -> int:
    """
    Run a single sync pass: check Dropbox for new files and ingest them.
    Returns the number of new files found.
    """
    loop = asyncio.get_event_loop()
    source = DropboxSource()

    # Dropbox SDK is blocking — run in thread executor to avoid blocking the event loop
    new_files: list[tuple[str, bytes]] = await loop.run_in_executor(None, source.new_files)

    for filename, file_bytes in new_files:
        await _ingest_file(filename, file_bytes)

    if new_files:
        log.info("Dropbox sync: ingested %d new file(s)", len(new_files))
    else:
        log.debug("Dropbox sync: no new files found")

    return len(new_files)


async def dropbox_sync_loop() -> None:
    """
    Long-running background task that polls Dropbox at the configured interval.
    Designed to run for the lifetime of the application.
    """
    if not settings.dropbox_access_token:
        log.info(
            "DROPBOX_ACCESS_TOKEN not configured — Dropbox sync disabled. "
            "Set it in .env to enable automatic ingestion from Dropbox."
        )
        return

    interval = settings.dropbox_poll_interval_seconds
    log.info(
        "Dropbox sync started — watching '%s' every %ds",
        settings.dropbox_folder,
        interval,
    )

    while True:
        try:
            await run_dropbox_sync()
        except Exception:
            log.exception("Dropbox sync pass failed — will retry next interval")
        await asyncio.sleep(interval)
