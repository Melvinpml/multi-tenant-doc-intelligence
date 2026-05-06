import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.document import DocumentStatus


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    file_type: str
    file_size: int
    status: DocumentStatus
    folder_id: Optional[uuid.UUID]
    company_id: uuid.UUID
    uploaded_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    status: DocumentStatus
    msg: str


class DocumentMoveRequest(BaseModel):
    folder_id: Optional[uuid.UUID] = None

class DocumentListResponse(BaseModel):
    total: int
    items: list[DocumentResponse]
