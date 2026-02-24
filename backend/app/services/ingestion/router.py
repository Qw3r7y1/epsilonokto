"""IngestionRouter — handles file persistence and kicks off background processing."""

import asyncio
import hashlib
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import Invoice
from app.schemas.invoice import UploadResponse
from app.services.ingestion.pipeline import process_invoice_async

log = get_logger("services.ingestion.router")
settings = get_settings()


class IngestionRouter:
    async def process(self, file: UploadFile, db: AsyncSession) -> UploadResponse:
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        contents = await file.read()
        if len(contents) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size: {settings.max_upload_size_mb} MB",
            )

        file_hash = hashlib.sha256(contents).hexdigest()

        # ── Deduplication check ─────────────────────────────────────────────
        existing = await db.execute(
            select(Invoice).where(Invoice.file_hash == file_hash)
        )
        duplicate = existing.scalar_one_or_none()
        if duplicate:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Duplicate file detected. This document was already uploaded "
                    f"(invoice_id={duplicate.id}, status={duplicate.status})."
                ),
            )

        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        invoice_id = uuid.uuid4()
        original_filename = file.filename or "upload"
        suffix = Path(original_filename).suffix
        dest = upload_dir / f"{invoice_id}{suffix}"
        dest.write_bytes(contents)

        file_type = suffix.lstrip(".").lower() or "unknown"

        invoice = Invoice(
            id=invoice_id,
            original_filename=original_filename,
            stored_path=str(dest),
            file_hash=file_hash,
            file_type=file_type,
            status="pending",
        )
        db.add(invoice)
        await db.commit()

        asyncio.create_task(process_invoice_async(invoice_id=invoice_id))
        log.info("Invoice %s queued for processing", invoice_id)

        return UploadResponse(
            invoice_id=invoice_id,
            filename=original_filename,
            status="pending",
            message="Invoice uploaded and queued for processing.",
        )
