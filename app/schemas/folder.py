import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator


class FolderCreateRequest(BaseModel):
    name: str
    parent_id: Optional[uuid.UUID] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Folder name cannot be empty.")
        if len(v) > 255:
            raise ValueError("Folder name too long (max 255 chars).")
        if any(char in v for char in ['/', '\\', '\x00']):
            raise ValueError("Folder name contains invalid characters.")
        return v

    model_config = ConfigDict(str_strip_whitespace=True)


class FolderUpdateRequest(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Folder name cannot be empty.")
        return v


class FolderResponse(BaseModel):
    id: uuid.UUID
    name: str
    parent_id: Optional[uuid.UUID]
    company_id: uuid.UUID
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
    document_count: int = 0

    model_config = ConfigDict(from_attributes=True)