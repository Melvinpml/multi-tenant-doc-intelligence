import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.dependencies import (
    get_db, get_current_user, get_tenant_context, require_role
)
from app.models.audit_log import AuditLog
from app.models.company import RoleEnum
from app.models.user import User
from app.schemas.audit import AuditLogResponse

router = APIRouter(prefix="/api/v1/audit", tags=["Audit & Compliance"])


@router.get("/logs", response_model=list[AuditLogResponse])
async def get_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_context)],
    _: Annotated[bool, Depends(require_role(RoleEnum.admin))],
    limit: int = Query(10, ge=1, le=100, description="Number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
):
    """
    Returns the most recent audit log entries for the authenticated tenant.
    Strictly scoped to the active company from the JWT.

    Access: Owner and Admin only.
    """
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.company_id == tenant_id)
        .order_by(desc(AuditLog.timestamp))
        .limit(limit)
        .offset(offset)
    )
    logs = result.scalars().all()
    return logs