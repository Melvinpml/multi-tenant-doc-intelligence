import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, status, Request # NEW: Added Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_db, get_current_user, get_tenant_context, require_role
)
from app.models.company import RoleEnum
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.schemas.document import (
    DocumentResponse, DocumentUploadResponse, DocumentMoveRequest, DocumentListResponse
)
from app.services.document_service import (
    validate_and_save_file, get_document_or_404,
    list_documents, move_document, soft_delete_document
)
from app.worker.tasks import process_document

# NEW: Imported Audit services
from app.services.audit_service import log_action, get_client_ip, AuditAction


router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_context)],
    _: Annotated[bool, Depends(require_role(RoleEnum.member))],
    request: Request, # NEW: Added request to capture IP
    file: UploadFile = File(...),
    folder_id: Optional[uuid.UUID] = Form(None),
):
    file_path, file_type, file_size, safe_name = await validate_and_save_file(
        file=file, company_id=tenant_id
    )

    doc = Document(
        company_id=tenant_id,
        folder_id=folder_id,
        uploaded_by=current_user.id,
        filename=safe_name,
        file_type=file_type,
        file_path=file_path,
        file_size=file_size,
        status=DocumentStatus.pending,
    )
    db.add(doc)
    await db.flush()

    process_document.delay(str(doc.id), str(tenant_id), file_path)

    # NEW: Log the document upload event
    await log_action(
        db=db,
        action=AuditAction.DOC_UPLOAD,
        company_id=tenant_id,
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        details={
            "document_id": str(doc.id),
            "filename": safe_name,
            "file_type": file_type,
            "file_size": file_size,
        },
    )

    return DocumentUploadResponse(
        id=doc.id,
        status=DocumentStatus.pending,
        msg="Processing started",
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_context)],
    folder_id: Optional[uuid.UUID] = None,
    doc_status: Optional[DocumentStatus] = None,
    page: int = 1,
    limit: int = 20,
):
    # 1. Fetch the raw dictionary containing the total count and ORM models
    result = await list_documents(
        company_id=tenant_id,
        db=db,
        folder_id=folder_id,
        status_filter=doc_status,
        page=page,
        limit=min(limit, 100),
    )
    
    # 2. Convert ORM models to Pydantic schemas using model_validate (Pydantic V2)
    return DocumentListResponse(
        total=result["total"],
        items=[
            DocumentResponse.model_validate(doc)
            for doc in result["items"]
        ],
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_context)],
):
    doc = await get_document_or_404(document_id, tenant_id, db)
    return doc


@router.patch("/{document_id}/move", response_model=DocumentResponse)
async def move_document_endpoint(
    document_id: uuid.UUID,
    payload: DocumentMoveRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_context)],
    _: Annotated[bool, Depends(require_role(RoleEnum.member))],
    request: Request, # NEW: Added request to capture IP
):
    doc = await move_document(
        document_id=document_id,
        target_folder_id=payload.folder_id,
        tenant_id=tenant_id,
        db=db,
    )

    # NEW: Log the document move event
    await log_action(
        db=db,
        action=AuditAction.DOC_MOVE,
        company_id=tenant_id,
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        details={
            "document_id": str(document_id),
            "target_folder_id": str(payload.folder_id),
        },
    )

    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_endpoint(
    document_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_context)],
    _: Annotated[bool, Depends(require_role(RoleEnum.member))],
    request: Request, # NEW: Added request to capture IP
):
    await soft_delete_document(document_id=document_id, tenant_id=tenant_id, db=db)

    # NEW: Log the document delete event
    await log_action(
        db=db,
        action=AuditAction.DOC_DELETE,
        company_id=tenant_id,
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        details={"document_id": str(document_id)},
    )