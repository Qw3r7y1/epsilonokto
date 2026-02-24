"""
Dropbox sync endpoints.

POST /api/v1/dropbox/sync  — manually trigger an immediate sync pass
GET  /api/v1/dropbox/status — check whether Dropbox integration is configured
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.ingestion.dropbox_sync import run_dropbox_sync

router = APIRouter(prefix="/dropbox", tags=["dropbox"])
log = get_logger("api.routes.dropbox")
settings = get_settings()


class SyncResponse(BaseModel):
    new_files: int
    message: str


class StatusResponse(BaseModel):
    configured: bool
    folder: str
    poll_interval_seconds: int


@router.get("/status", response_model=StatusResponse)
async def dropbox_status() -> StatusResponse:
    """Return whether Dropbox integration is active and its configuration."""
    return StatusResponse(
        configured=bool(settings.dropbox_access_token),
        folder=settings.dropbox_folder,
        poll_interval_seconds=settings.dropbox_poll_interval_seconds,
    )


@router.post("/sync", response_model=SyncResponse)
async def dropbox_sync() -> SyncResponse:
    """
    Trigger an immediate Dropbox sync pass outside the normal poll interval.
    Useful for testing or forcing a re-check after uploading files.
    """
    if not settings.dropbox_access_token:
        raise HTTPException(
            status_code=503,
            detail=(
                "Dropbox is not configured. "
                "Set DROPBOX_ACCESS_TOKEN in your .env file."
            ),
        )

    try:
        count = await run_dropbox_sync()
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SyncResponse(
        new_files=count,
        message=f"Sync complete. {count} new file(s) queued for processing.",
    )
