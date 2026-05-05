import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.dependencies import (
    get_db, get_current_user, get_tenant_context, require_role
)
from app.models.company import Company, CompanyMember, RoleEnum
from app.models.user import User
from app.schemas.company import (
    CompanyResponse, MemberInviteRequest,
    MemberRoleUpdateRequest, MemberResponse
)

router = APIRouter(prefix="/api/v1/companies", tags=["Companies"])


@router.get("/me", response_model=CompanyResponse)
async def get_my_company(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_context)],
):
    result = await db.execute(
        select(Company).where(Company.id == tenant_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    membership_result = await db.execute(
        select(CompanyMember).where(
            CompanyMember.user_id == current_user.id,
            CompanyMember.company_id == tenant_id,
        )
    )
    membership = membership_result.scalar_one_or_none()

    return CompanyResponse(id=company.id, name=company.name, role=membership.role)


@router.get("/{company_id}/members", response_model=list[MemberResponse])
async def list_members(
    company_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_context)],
    _: Annotated[bool, Depends(require_role(RoleEnum.viewer))],
):
    if company_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    result = await db.execute(
        select(CompanyMember, User)
        .join(User, CompanyMember.user_id == User.id)
        .where(CompanyMember.company_id == tenant_id)
    )
    rows = result.all()

    return [
        MemberResponse(
            user_id=member.user_id,
            company_id=member.company_id,
            email=user.email,
            role=member.role,
        )
        for member, user in rows
    ]


@router.post(
    "/{company_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_member(
    company_id: uuid.UUID,
    payload: MemberInviteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_context)],
    _: Annotated[bool, Depends(require_role(RoleEnum.admin))],
):
    if company_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    user_result = await db.execute(
        select(User).where(User.email == payload.email)
    )
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    existing = await db.execute(
        select(CompanyMember).where(
            CompanyMember.user_id == target_user.id,
            CompanyMember.company_id == tenant_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User already a member.")

    if payload.role == RoleEnum.owner:
        raise HTTPException(
            status_code=400, detail="Cannot assign Owner role via invite."
        )

    membership = CompanyMember(
        user_id=target_user.id,
        company_id=tenant_id,
        role=payload.role,
    )
    db.add(membership)
    await db.flush()

    return MemberResponse(
        user_id=target_user.id,
        company_id=tenant_id,
        email=target_user.email,
        role=payload.role,
    )


@router.patch("/{company_id}/members/{user_id}", response_model=MemberResponse)
async def change_member_role(
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: MemberRoleUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_context)],
    _: Annotated[bool, Depends(require_role(RoleEnum.owner))],
):
    if company_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role.")

    result = await db.execute(
        select(CompanyMember, User)
        .join(User, CompanyMember.user_id == User.id)
        .where(
            CompanyMember.user_id == user_id,
            CompanyMember.company_id == tenant_id,
        )
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Member not found.")

    membership, user = row
    membership.role = payload.role
    await db.flush()

    return MemberResponse(
        user_id=user.id,
        company_id=tenant_id,
        email=user.email,
        role=membership.role,
    )


@router.delete("/{company_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_context)],
    _: Annotated[bool, Depends(require_role(RoleEnum.admin))],
):
    if company_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    result = await db.execute(
        select(CompanyMember).where(
            CompanyMember.user_id == user_id,
            CompanyMember.company_id == tenant_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="Member not found.")

    if membership.role == RoleEnum.owner:
        raise HTTPException(status_code=400, detail="Cannot remove the company Owner.")

    await db.delete(membership)