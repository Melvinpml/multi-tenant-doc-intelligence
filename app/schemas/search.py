import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict


class SearchResultItem(BaseModel):
    doc_id: uuid.UUID
    filename: str
    folder_id: Optional[uuid.UUID]
    chunk: str
    score: float
    search_mode: str

    model_config = ConfigDict(from_attributes=True)


class SearchResponse(BaseModel):
    query: str
    mode: str
    total: int
    results: list[SearchResultItem]