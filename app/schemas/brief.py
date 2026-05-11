from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.brief import BriefStatus


class BriefOut(BaseModel):
    id: uuid.UUID
    requested_by: uuid.UUID
    query: str
    source_paper_ids: list[str] | None
    status: BriefStatus
    content_english: str | None
    content_somali: str | None
    video_script: str | None
    paper_count: int
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class PaginatedBriefs(BaseModel):
    items: list[BriefOut]
    total: int
    page: int
    limit: int
    pages: int
