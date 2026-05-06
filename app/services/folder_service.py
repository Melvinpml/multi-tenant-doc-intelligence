import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.models.folder import Folder
# from app.models.document import Document



async def get_folder_or_404(
    folder_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> Folder:
    result = await db.execute(
        select(Folder).where(
            Folder.id == folder_id,
            Folder.company_id == tenant_id,
            Folder.deleted_at.is_(None),
        )
    )
    folder = result.scalar_one_or_none()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found or access denied.",
        )
    return folder


async def create_folder(
    name: str,
    company_id: uuid.UUID,
    created_by: uuid.UUID,
    db: AsyncSession,
    parent_id: Optional[uuid.UUID] = None,
) -> Folder:
    if parent_id:
        await get_folder_or_404(parent_id, company_id, db)

    existing = await db.execute(
        select(Folder).where(
            Folder.company_id == company_id,
            Folder.parent_id == parent_id,
            Folder.name == name,
            Folder.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A folder with this name already exists at this level.",
        )

    folder = Folder(
        name=name,
        company_id=company_id,
        parent_id=parent_id,
        created_by=created_by,
    )
    db.add(folder)
    await db.flush()
    await db.refresh(folder)
    return folder


async def list_folders(
    company_id: uuid.UUID,
    db: AsyncSession,
    parent_id: Optional[uuid.UUID] = None,
) -> list[dict]:
    doc_count_result = await db.execute(
        text("""
            SELECT folder_id, COUNT(id) AS doc_count
            FROM documents
            WHERE company_id = :company_id
              AND deleted_at IS NULL
              AND folder_id IS NOT NULL
            GROUP BY folder_id
        """),
        {"company_id": str(company_id)},
    )
    doc_counts: dict[str, int] = {
        str(row.folder_id): row.doc_count
        for row in doc_count_result.mappings().all()
    }

    folder_result = await db.execute(
        select(Folder).where(
            Folder.company_id == company_id,
            Folder.parent_id == parent_id,
            Folder.deleted_at.is_(None),
        )
    )
    folders = folder_result.scalars().all()

    return [
        {"folder": f, "document_count": doc_counts.get(str(f.id), 0)}
        for f in folders
    ]


async def rename_folder(
    folder_id: uuid.UUID,
    new_name: str,
    company_id: uuid.UUID,
    db: AsyncSession,
) -> Folder:
    folder = await get_folder_or_404(folder_id, company_id, db)

    existing = await db.execute(
        select(Folder).where(
            Folder.company_id == company_id,
            Folder.parent_id == folder.parent_id,
            Folder.name == new_name,
            Folder.id != folder_id,
            Folder.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A folder with this name already exists.",
        )

    folder.name = new_name
    await db.flush()
    await db.refresh(folder)
    return folder


async def soft_delete_folder(
    folder_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    folder = await get_folder_or_404(folder_id, company_id, db)

    doc_count_result = await db.execute(
        text("""
            SELECT COUNT(id) AS doc_count
            FROM documents
            WHERE folder_id = :folder_id
              AND deleted_at IS NULL
        """),
        {"folder_id": str(folder_id)},
    )
    doc_count = doc_count_result.scalar() or 0

    if doc_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Folder contains {doc_count} document(s). Delete documents first.",
        )

    folder.deleted_at = datetime.now(timezone.utc)
    await db.flush()




