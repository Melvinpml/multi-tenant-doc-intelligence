import uuid
from typing import Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from sqlalchemy.orm import aliased

from app.core.config import settings
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk


# ── Embedding Generator ────────────────────────────────────────────────────────

async def generate_embedding(query: str) -> list[float]:
    """
    Calls the Gemini AI API to convert a text query into a vector embedding.
    Returns a list of 768 floats representing the semantic meaning of the query.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/{settings.AI_EMBEDDING_MODEL}:embedContent",
            headers={"Content-Type": "application/json"},
            params={"key": settings.AI_PROVIDER_API_KEY},
            json={
                "model": settings.AI_EMBEDDING_MODEL,
                "content": {
                    "parts": [{"text": query}]
                },
                "outputDimensionality": settings.AI_EMBEDDING_DIMENSION,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["embedding"]["values"]


# ── Keyword Search ─────────────────────────────────────────────────────────────

async def keyword_search(
    query: str,
    tenant_id: uuid.UUID,
    db: AsyncSession,
    limit: int = 10,
) -> list[dict]:
    """
    Uses PostgreSQL full-text search (to_tsvector / to_tsquery) for
    exact phrase and keyword matching across document chunks.
    Scoped strictly to the authenticated tenant.
    """
    sql = text("""
        SELECT
            dc.id            AS chunk_id,
            dc.document_id   AS doc_id,
            dc.chunk_text    AS chunk,
            dc.company_id,
            d.filename,
            d.folder_id,
            ts_rank(
                to_tsvector('english', dc.chunk_text),
                plainto_tsquery('english', :query)
            ) AS score
        FROM document_chunks dc
        JOIN documents d
            ON dc.document_id = d.id
        WHERE
            dc.company_id = :tenant_id
            AND d.company_id = :tenant_id
            AND d.status = 'completed'
            AND d.deleted_at IS NULL
            AND to_tsvector('english', dc.chunk_text)
                @@ plainto_tsquery('english', :query)
        ORDER BY score DESC
        LIMIT :limit
    """)

    result = await db.execute(
        sql,
        {
            "query": query,
            "tenant_id": str(tenant_id),
            "limit": limit,
        },
    )
    rows = result.mappings().all()

    return [
        {
            "doc_id": row["doc_id"],
            "filename": row["filename"],
            "folder_id": row["folder_id"],
            "chunk": row["chunk"],
            "score": round(float(row["score"]), 4),
            "search_mode": "keyword",
        }
        for row in rows
    ]


# ── Semantic Search ────────────────────────────────────────────────────────────

async def semantic_search(
    query: str,
    tenant_id: uuid.UUID,
    db: AsyncSession,
    limit: int = 10,
) -> list[dict]:
    """
    Converts the query to a vector embedding using the AI API,
    then uses pgvector cosine distance operator (<=>) to find the
    most semantically similar document chunks — strictly within this tenant.
    """
    embedding = await generate_embedding(query)
    embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

    sql = text("""
        SELECT
            dc.id            AS chunk_id,
            dc.document_id   AS doc_id,
            dc.chunk_text    AS chunk,
            dc.company_id,
            d.filename,
            d.folder_id,
            1 - (dc.embedding <=> CAST(:embedding AS vector)) AS score
        FROM document_chunks dc
        JOIN documents d
            ON dc.document_id = d.id
        WHERE
            dc.company_id  = :tenant_id
            AND d.company_id   = :tenant_id
            AND d.status       = 'completed'
            AND d.deleted_at   IS NULL
            AND dc.embedding   IS NOT NULL
        ORDER BY dc.embedding <=> CAST(:embedding AS vector)
        LIMIT :limit
    """)

    result = await db.execute(
        sql,
        {
            "embedding": embedding_str,
            "tenant_id": str(tenant_id),
            "limit": limit,
        },
    )
    rows = result.mappings().all()

    return [
        {
            "doc_id": row["doc_id"],
            "filename": row["filename"],
            "folder_id": row["folder_id"],
            "chunk": row["chunk"],
            "score": round(float(row["score"]), 4),
            "search_mode": "semantic",
        }
        for row in rows
    ]
