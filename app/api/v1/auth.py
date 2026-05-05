import uuid
from datetime import timedelta
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.dependencies import get_db, get_redis, get_current_user
from app.core.security import (
    hash_password, verify_password, create_access_token, decode_access_token
)
from app.models.user import User
from app.models.company import Company, CompanyMember, RoleEnum
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserMeResponse, RegisterUserOnlyRequest, UserOnlyResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
bearer_scheme = HTTPBearer()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered.")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.flush()

    company = Company(name=payload.company_name)
    db.add(company)
    await db.flush()

    membership = CompanyMember(
        user_id=user.id,
        company_id=company.id,
        role=RoleEnum.owner,
    )
    db.add(membership)
    await db.flush()

    token = create_access_token(
        subject=str(user.id),
        company_id=str(company.id),
        role=RoleEnum.owner.value,
    )
    return TokenResponse(access_token=token)


@router.post("/register-user", response_model=UserOnlyResponse, status_code=status.HTTP_201_CREATED)
async def register_user_only(
    payload: RegisterUserOnlyRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Register a user WITHOUT creating a company.
    
    Use this endpoint to:
    - Create team members before inviting them to an existing company
    - Register users who will be invited later via the multi-tenancy flow
    """
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered."
        )
    
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        is_active=True
    )
    db.add(user)
    await db.flush()
    
    return UserOnlyResponse(
        id=user.id,
        email=user.email,
        message="User created successfully. They can now be invited to a company."
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is deactivated.")

    membership_result = await db.execute(
        select(CompanyMember).where(CompanyMember.user_id == user.id)
    )
    memberships = membership_result.scalars().all()
    if not memberships:
        raise HTTPException(status_code=400, detail="User has no company membership.")

    primary = memberships[0]
    token = create_access_token(
        subject=str(user.id),
        company_id=str(primary.company_id),
        role=primary.role.value,
    )
    return TokenResponse(access_token=token)


@router.post("/logout")
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            import time
            ttl = int(exp - time.time())
            if ttl > 0:
                await redis.setex(f"blocklist:{jti}", ttl, "revoked")
    except Exception:
        pass
    return {"message": "Successfully logged out."}


@router.get("/me", response_model=UserMeResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    """Get current authenticated user with their company memberships"""
    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        companies=[
            {
                "company_id": str(m.company_id),
                "company_name": m.company.name,
                "role": m.role.value,
            }
            for m in current_user.memberships
        ],
    )