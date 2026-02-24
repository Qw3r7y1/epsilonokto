from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.invoice import UploadResponse
from app.services.ingestion.router import IngestionRouter
from app.core.logging import get_logger

logger = get_logger("api.upload")
router = APIRouter(prefix="/upload", tags=["Upload"])

ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/tiff"}


@router.post("/", response_model=UploadResponse)
async def upload_invoice(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Accepted: PDF, PNG, JPEG, TIFF.",
        )
    logger.info(f"Received upload: {file.filename} ({file.content_type})")
    ingestion = IngestionRouter()
    result = await ingestion.process(file=file, db=db)
    return result
