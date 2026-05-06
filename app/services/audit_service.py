import uuid
from typing import Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


# ── Audit Action Constants ─────────────────────────────────────────────────────

class AuditAction:
    LOGIN          = "LOGIN"
    LOGOUT         = "LOGOUT"
    REGISTER       = "REGISTER"
    DOC_UPLOAD     = "DOC_UPLOAD"
    DOC_DELETE     = "DOC_DELETE"
    DOC_MOVE       = "DOC_MOVE"
    DOC_VIEW       = "DOC_VIEW"
    FOLDER_CREATE  = "FOLDER_CREATE"
    FOLDER_RENAME  = "FOLDER_RENAME"
    FOLDER_DELETE  = "FOLDER_DELETE"
    SEARCH         = "SEARCH"
    MEMBER_INVITE  = "MEMBER_INVITE"
    MEMBER_REMOVE  = "MEMBER_REMOVE"
    MEMBER_ROLE_CHANGE = "MEMBER_ROLE_CHANGE"


# ── IP Address Extractor ───────────────────────────────────────────────────────

def get_client_ip(request: Request) -> Optional[str]:
    """
    Extracts the real client IP address from the HTTP request.
    Handles proxy headers (X-Forwarded-For, X-Real-IP) for production deployments.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    if request.client:
        return request.client.host

    return None


# ── Audit Logger ──────────────────────────────────────────────────────────────

async def log_action(
    db: AsyncSession,
    action: str,
    company_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = None,
    ip_address: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """
    Creates an audit log entry. Called from route handlers after
    successful operations. Does NOT commit — relies on the
    get_db dependency to commit at the end of the request.
    """
    log = AuditLog(
        company_id=company_id,
        user_id=user_id,
        action=action,
        ip_address=ip_address,
        details=details,
    )
    db.add(log)
    await db.flush()