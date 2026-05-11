from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.organisation import OrgType


class OrganisationProfileCreate(BaseModel):
    name: str
    org_type: OrgType
    description: str | None = None
    logo_url: str | None = None
    website: str | None = None
    country: str | None = None
    city: str | None = None
    founded_year: int | None = None
    somali_entity: bool = False
    focus_areas: list[str] | None = None
    email_public: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    twitter: str | None = None


class OrganisationProfileUpdate(OrganisationProfileCreate):
    pass


class OrganisationProfileOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    org_type: OrgType | None
    description: str | None
    logo_url: str | None
    website: str | None
    country: str | None
    city: str | None
    founded_year: int | None
    somali_entity: bool
    focus_areas: list[str] | None
    email_public: str | None
    phone: str | None
    linkedin: str | None
    twitter: str | None
    partner: bool
    verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedOrganisations(BaseModel):
    items: list[OrganisationProfileOut]
    total: int
    page: int
    limit: int
    pages: int
