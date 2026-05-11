from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel
from app.models.paper import PaperStatus, OgsoType


class PaperOut(BaseModel):
    id: str
    title: str
    authors: list | dict | None
    year: int | None
    abstract: str | None
    source: str | None
    url: str | None
    doi: str | None
    institution: str | None
    category: str | None
    doc_type: str | None
    cluster_id: int | None
    somali_authored: bool
    citations: int
    language: str
    status: PaperStatus
    ogso_type: OgsoType
    created_at: datetime

    model_config = {"from_attributes": True}


class PaperImportItem(BaseModel):
    id: str | None = None
    title: str
    authors: list[str] | None = None
    year: str | int | None = None
    abstract: str | None = None
    source: str | None = None
    url: str | None = None
    institution: str | None = None
    category: str | None = None
    doc_type: str | None = None
    somali_author: bool = False
    citations: int = 0
    doi: str | None = None


class PaperImportResponse(BaseModel):
    imported: int
    skipped: int
    total: int


class PaginatedPapers(BaseModel):
    items: list[PaperOut]
    total: int
    page: int
    limit: int
    pages: int
