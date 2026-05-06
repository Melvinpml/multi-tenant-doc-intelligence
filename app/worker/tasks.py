import asyncio
import uuid
from pathlib import Path

import fitz
import httpx
from docx import Document as DocxDocument
from sqlalchemy import delete, select

import app.models
from app.db.session import AsyncSessionLocal, engine
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.services.search_service import generate_embedding
from app.worker.celery_app import celery_app


CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200


def extract_text(file_path: str) -> str:
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension == ".pdf":
        with fitz.open(path) as pdf:
            return "\n".join(page.get_text("text") for page in pdf)

    if extension == ".docx":
        document = DocxDocument(path)
        return "\n".join(paragraph.text for paragraph in document.paragraphs)

    if extension in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")

    raise ValueError(f"Unsupported file type: {extension}")


def split_text(text: str) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(normalized):
        end = min(start + CHUNK_SIZE, len(normalized))
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(normalized):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)

    return chunks


async def generate_chunk_embeddings(chunks: list[str]) -> list[list[float] | None]:
    embeddings: list[list[float] | None] = []

    for chunk in chunks:
        try:
            embeddings.append(await generate_embedding(chunk))
        except httpx.HTTPError:
            embeddings.append(None)

    return embeddings


async def set_document_status(
    document_id: uuid.UUID,
    tenant_id: uuid.UUID,
    status: DocumentStatus,
) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.company_id == tenant_id,
                Document.deleted_at.is_(None),
            )
        )
        doc = result.scalar_one_or_none()
        if doc:
            doc.status = status
            await db.commit()


async def process_document_async(
    document_id: str,
    tenant_id: str,
    file_path: str,
) -> bool:
    document_uuid = uuid.UUID(document_id)
    tenant_uuid = uuid.UUID(tenant_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Document).where(
                Document.id == document_uuid,
                Document.company_id == tenant_uuid,
                Document.deleted_at.is_(None),
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return False

        doc.status = DocumentStatus.processing
        await db.commit()

    try:
        text = extract_text(file_path)
        chunks = split_text(text)
        if not chunks:
            raise ValueError("No extractable text found in document.")

        embeddings = await generate_chunk_embeddings(chunks)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Document).where(
                    Document.id == document_uuid,
                    Document.company_id == tenant_uuid,
                    Document.deleted_at.is_(None),
                )
            )
            doc = result.scalar_one_or_none()
            if not doc:
                return False

            await db.execute(
                delete(DocumentChunk).where(
                    DocumentChunk.document_id == document_uuid,
                    DocumentChunk.company_id == tenant_uuid,
                )
            )

            for index, chunk in enumerate(chunks):
                db.add(
                    DocumentChunk(
                        company_id=tenant_uuid,
                        document_id=document_uuid,
                        chunk_index=index,
                        chunk_text=chunk,
                        embedding=embeddings[index],
                    )
                )

            doc.status = DocumentStatus.completed
            await db.commit()
            return True

    except (OSError, ValueError):
        await set_document_status(document_uuid, tenant_uuid, DocumentStatus.failed)
        raise


@celery_app.task(
    bind=True,
    name="app.worker.tasks.process_document",
    autoretry_for=(httpx.TimeoutException, httpx.HTTPStatusError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_document(self, document_id: str, tenant_id: str, file_path: str) -> str:
    async def run_task() -> bool:
        try:
            return await process_document_async(document_id, tenant_id, file_path)
        finally:
            await engine.dispose()

    processed = asyncio.run(run_task())
    if not processed:
        raise self.retry(countdown=2, max_retries=5)
    return f"processed document {document_id}"
