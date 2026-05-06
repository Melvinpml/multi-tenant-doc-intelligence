import os
import uuid
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import magic
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.models.document import Document, DocumentStatus
from app.models.folder import Folder

ALLOWED_MIME_TYPES = {
    "pdf":  "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt":  "text/plain",
    "md":   "text/plain",
}


def sanitize_filename(filename: str) -> str:
    name = Path(filename).name
    name = "".join(c for c in name if c.isalnum() or c in "._- ")
    name = name.strip(". ")
    return name or "unnamed_file"


async def validate_and_save_file(
    file: UploadFile,
    company_id: uuid.UUID,
) -> tuple[str, str, int, str]:
    extension = Path(file.filename or "").suffix.lstrip(".").lower()
    if extension not in settings.ALLOWED_EXTENSIONS_LIST:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Only {', '.join(settings.ALLOWED_EXTENSIONS_LIST).upper()} allowed.",
        )

    content = await file.read()
    file_size = len(content)

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit.",
        )

    detected_mime = magic.from_buffer(content[:2048], mime=True)
    expected_mime = ALLOWED_MIME_TYPES.get(extension)
    if expected_mime and detected_mime not in (expected_mime, "text/plain"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File content does not match its extension.",
        )

    safe_name = sanitize_filename(file.filename or "upload")
    unique_name = f"{uuid.uuid4()}_{safe_name}"
    company_dir = Path(settings.UPLOAD_DIR) / str(company_id)
    company_dir.mkdir(parents=True, exist_ok=True)
    file_path = company_dir / unique_name

    with open(file_path, "wb") as f:
        f.write(content)

    return str(file_path), extension.upper(), file_size, safe_name


async def get_document_or_404(
    document_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> Document:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.company_id == tenant_id,
            Document.deleted_at.is_(None),
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied.",
        )
    return doc


async def list_documents(
    company_id: uuid.UUID,
    db: AsyncSession,
    folder_id: Optional[uuid.UUID] = None,
    status_filter: Optional[DocumentStatus] = None,
    page: int = 1,
    limit: int = 20,
) -> dict:
    query = select(Document).where(
        Document.company_id == company_id,
        Document.deleted_at.is_(None),
    )
    if folder_id is not None:
        query = query.where(Document.folder_id == folder_id)
    if status_filter is not None:
        query = query.where(Document.status == status_filter)

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    documents = result.scalars().all()

    return {"total": total, "items": documents}


async def move_document(
    document_id: uuid.UUID,
    target_folder_id: Optional[uuid.UUID],
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> Document:
    doc = await get_document_or_404(document_id, tenant_id, db)

    if target_folder_id is not None:
        folder_result = await db.execute(
            select(Folder).where(
                Folder.id == target_folder_id,
                Folder.company_id == tenant_id,
                Folder.deleted_at.is_(None),
            )
        )
        if not folder_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target folder not found.",
            )

    doc.folder_id = target_folder_id
    await db.flush()
    await db.refresh(doc)
    return doc


async def soft_delete_document(
    document_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    doc = await get_document_or_404(document_id, tenant_id, db)
    doc.deleted_at = datetime.now(timezone.utc)
    await db.flush()
