import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Invoice, InvoiceStatus
from app.db.session import get_db
from app.schemas.upload import UploadResponse
from app.services.ingestion.pipeline import process_invoice_async

settings = get_settings()
router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff",
}


@router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_invoice(
    file: UploadFile = File(...),
    vendor_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}. "
            f"Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    contents = await file.read()
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB} MB",
        )

    # Save raw upload
    upload_dir: Path = settings.LOCAL_UPLOAD_DIR
    upload_dir.mkdir(parents=True, exist_ok=True)
    invoice_id = uuid.uuid4()
    suffix = Path(file.filename or "upload").suffix
    dest = upload_dir / f"{invoice_id}{suffix}"
    dest.write_bytes(contents)

    # Create invoice record
    invoice = Invoice(
        id=invoice_id,
        vendor_id=vendor_id,
        filename=file.filename or dest.name,
        file_path=str(dest),
        status=InvoiceStatus.pending,
    )
    db.add(invoice)
    db.commit()

    # Kick off background processing (fire-and-forget via asyncio)
    import asyncio

    asyncio.create_task(process_invoice_async(invoice_id=invoice_id))

    return UploadResponse(
        invoice_id=invoice_id,
        filename=file.filename or dest.name,
        message="Invoice uploaded and queued for processing.",
    )
