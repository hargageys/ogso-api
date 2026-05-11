from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.submission import SubmissionStatus


class SubmissionCreate(BaseModel):
    title: str
    abstract: str | None = None
    authors: list[str] | None = None
    year: int | None = None
    doi: str | None = None
    file_url: str | None = None


class SubmissionUpdate(SubmissionCreate):
    pass


class SubmissionOut(BaseModel):
    id: uuid.UUID
    submitted_by: uuid.UUID
    paper_id: str | None
    title: str | None
    abstract: str | None
    authors: list | dict | None
    year: str | None
    doi: str | None
    file_url: str | None
    status: SubmissionStatus
    reviewer_notes: str | None
    submitted_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedSubmissions(BaseModel):
    items: list[SubmissionOut]
    total: int
    page: int
    limit: int
    pages: int
