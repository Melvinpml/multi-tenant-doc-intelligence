import uuid
from typing import Annotated, Optional
from enum import Enum

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user, get_tenant_context
from app.models.user import User
from app.schemas.search import SearchResponse, SearchResultItem
from app.services.search_service import keyword_search, semantic_search

# NEW: Imported Audit services
from app.services.audit_service import log_action, get_client_ip, AuditAction

router = APIRouter(prefix="/api/v1/search", tags=["Search"])


class SearchMode(str, Enum):
    keyword  = "keyword"
    semantic = "semantic"


@router.get(
    "",
    response_model=SearchResponse,
    dependencies=[Depends(RateLimiter(times=60, seconds=60))],
)
async def search_documents(
    request: Request, # NEW: Added request to capture IP for audit logs
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_context)],
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    mode: SearchMode = Query(SearchMode.keyword, description="Search mode: keyword or semantic"),
    limit: int = Query(10, ge=1, le=50, description="Number of results to return"),
):
    """
    Search across documents in the authenticated tenant.

    - **keyword**: PostgreSQL full-text search using to_tsvector / plainto_tsquery.
      Fast, exact phrase matching.
    - **semantic**: AI-powered vector similarity using pgvector cosine distance.
      Finds conceptually related content even without exact keyword match.

    Results are strictly scoped to the authenticated user's active company.
    """
    q = q.strip()
    if not q:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Search query cannot be empty.",
        )

    try:
        if mode == SearchMode.keyword:
            results = await keyword_search(
                query=q,
                tenant_id=tenant_id,
                db=db,
                limit=limit,
            )
        else:
            results = await semantic_search(
                query=q,
                tenant_id=tenant_id,
                db=db,
                limit=limit,
            )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI Service Timeout. Please try again later.",
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI Service error: {e.response.status_code}",
        )

    items = [
        SearchResultItem(
            doc_id=r["doc_id"],
            filename=r["filename"],
            folder_id=r["folder_id"],
            chunk=r["chunk"],
            score=r["score"],
            search_mode=r["search_mode"],
        )
        for r in results
    ]

    # NEW: Log the search event
    await log_action(
        db=db,
        action=AuditAction.SEARCH,
        company_id=tenant_id,
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        details={
            "query": q,
            "mode": mode.value,
            "results_count": len(items),
        },
    )

    return SearchResponse(
        query=q,
        mode=mode.value,
        total=len(items),
        results=items,
    )