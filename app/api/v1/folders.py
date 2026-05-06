import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_db, get_current_user, get_tenant_context, require_role
)
from app.models.company import RoleEnum
from app.models.user import User
from app.schemas.folder import FolderCreateRequest, FolderUpdateRequest, FolderResponse
from app.services.folder_service import (
    create_folder, list_folders, rename_folder, soft_delete_folder
)

router = APIRouter(prefix="/api/v1/folders", tags=["Folders"])


@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder_endpoint(
    payload: FolderCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_context)],
    _: Annotated[bool, Depends(require_role(RoleEnum.member))],
):
    folder = await create_folder(
        name=payload.name,
        company_id=tenant_id,
        created_by=current_user.id,
        db=db,
        parent_id=payload.parent_id,
    )
    return FolderResponse(
        id=folder.id,
        name=folder.name,
        parent_id=folder.parent_id,
        company_id=folder.company_id,
        created_by=folder.created_by,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
        document_count=0,
    )


@router.get("", response_model=list[FolderResponse])
async def list_folders_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_context)],
    parent_id: Optional[uuid.UUID] = None,
):
    rows = await list_folders(company_id=tenant_id, db=db, parent_id=parent_id)
    return [
        FolderResponse(
            id=row["folder"].id,
            name=row["folder"].name,
            parent_id=row["folder"].parent_id,
            company_id=row["folder"].company_id,
            created_by=row["folder"].created_by,
            created_at=row["folder"].created_at,
            updated_at=row["folder"].updated_at,
            document_count=row["document_count"],
        )
        for row in rows
    ]


@router.patch("/{folder_id}", response_model=FolderResponse)
async def rename_folder_endpoint(
    folder_id: uuid.UUID,
    payload: FolderUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_context)],
    _: Annotated[bool, Depends(require_role(RoleEnum.member))],
):
    folder = await rename_folder(
        folder_id=folder_id,
        new_name=payload.name,
        company_id=tenant_id,
        db=db,
    )
    return FolderResponse(
        id=folder.id,
        name=folder.name,
        parent_id=folder.parent_id,
        company_id=folder.company_id,
        created_by=folder.created_by,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
    )


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder_endpoint(
    folder_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_context)],
    _: Annotated[bool, Depends(require_role(RoleEnum.admin))],
):
    await soft_delete_folder(folder_id=folder_id, company_id=tenant_id, db=db)