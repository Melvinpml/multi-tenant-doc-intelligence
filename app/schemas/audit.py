import uuid
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    action: str
    ip_address: Optional[str]
    details: Optional[dict[str, Any]]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)