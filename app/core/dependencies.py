import uuid
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.company import CompanyMember, RoleEnum

from sqlalchemy.orm import selectinload

bearer_scheme = HTTPBearer()

ROLE_HIERARCHY = {
    RoleEnum.owner:  4,
    RoleEnum.admin:  3,
    RoleEnum.member: 2,
    RoleEnum.viewer: 1,
}


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_redis() -> aioredis.Redis:
    client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield client
    finally:
        await client.close()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except ValueError:
        raise credentials_exception

    jti: str = payload.get("jti")
    if jti and await redis.get(f"blocklist:{jti}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please log in again.",
        )

    user_id: str = payload.get("sub")
    if not user_id:
        raise credentials_exception

    # Eager load memberships and their associated companies
    result = await db.execute(
        select(User)
        .where(User.id == uuid.UUID(user_id))
        .options(
            selectinload(User.memberships).selectinload(CompanyMember.company)
        )
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise credentials_exception

    return user


async def get_tenant_context(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> uuid.UUID:
    try:
        payload = decode_access_token(credentials.credentials)
        company_id = payload.get("company_id")
        if not company_id:
            raise ValueError("No company_id in token")
        return uuid.UUID(company_id)
    except (ValueError, Exception):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not determine tenant context",
        )


def require_role(minimum_role: RoleEnum):
    async def role_checker(
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_user)],
        tenant_id: Annotated[uuid.UUID, Depends(get_tenant_context)],
    ) -> bool:
        result = await db.execute(
            select(CompanyMember).where(
                CompanyMember.user_id == current_user.id,
                CompanyMember.company_id == tenant_id,
            )
        )
        membership = result.scalar_one_or_none()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this company.",
            )

        if ROLE_HIERARCHY[membership.role] < ROLE_HIERARCHY[minimum_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {minimum_role.value}",
            )
        return True

    return role_checker