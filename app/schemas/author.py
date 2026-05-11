from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel


class ResearcherProfileCreate(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    photo_url: str | None = None
    orcid: str | None = None
    title: str | None = None
    position: str | None = None
    institution: str | None = None
    country: str | None = None
    city: str | None = None
    website: str | None = None
    twitter: str | None = None
    linkedin: str | None = None
    research_interests: list[str] | None = None
    fields: list[str] | None = None
    inside_somalia: bool = False
    somali_diaspora: bool = False


class ResearcherProfileUpdate(ResearcherProfileCreate):
    pass


class ResearcherProfileOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str | None
    bio: str | None
    photo_url: str | None
    orcid: str | None
    title: str | None
    position: str | None
    institution: str | None
    country: str | None
    city: str | None
    website: str | None
    twitter: str | None
    linkedin: str | None
    research_interests: list[str] | None
    fields: list[str] | None
    inside_somalia: bool
    somali_diaspora: bool
    verified: bool
    paper_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ClaimPaperRequest(BaseModel):
    paper_id: str


class PaginatedResearchers(BaseModel):
    items: list[ResearcherProfileOut]
    total: int
    page: int
    limit: int
    pages: int
