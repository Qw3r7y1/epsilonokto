import uuid
from pydantic import BaseModel


class UploadResponse(BaseModel):
    invoice_id: uuid.UUID
    filename: str
    message: str
