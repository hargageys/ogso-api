import uuid
import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.dependencies import get_active_user
from app.models.user import User, UserRole
from app.models.organisation import OrganisationProfile
from app.models.author import ResearcherProfile
from app.schemas.organisation import (
    OrganisationProfileCreate, OrganisationProfileUpdate,
    OrganisationProfileOut, PaginatedOrganisations,
)
from app.schemas.author import ResearcherProfileOut

router = APIRouter(prefix="/organisations", tags=["organisations"])

ORG_ROLES = {UserRole.organisation, UserRole.university, UserRole.ministry}


@router.get("", response_model=PaginatedOrganisations)
async def list_organisations(
    org_type: str | None = None,
    country: str | None = None,
    somali_entity: bool | None = None,
    partner: bool | None = None,
    verified: bool | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    q = select(OrganisationProfile)
    if org_type:
        q = q.where(OrganisationProfile.org_type == org_type)
    if country:
        q = q.where(OrganisationProfile.country == country)
    if somali_entity is not None:
        q = q.where(OrganisationProfile.somali_entity == somali_entity)
    if partner is not None:
        q = q.where(OrganisationProfile.partner == partner)
    if verified is not None:
        q = q.where(OrganisationProfile.verified == verified)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    orgs = (await db.execute(q.offset((page - 1) * limit).limit(limit))).scalars().all()
    return {"items": orgs, "total": total, "page": page, "limit": limit, "pages": math.ceil(total / limit) if limit else 1}


@router.get("/{org_id}", response_model=OrganisationProfileOut)
async def get_organisation(org_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    org = (await db.execute(select(OrganisationProfile).where(OrganisationProfile.id == org_id))).scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organisation not found")
    return org


@router.get("/{org_id}/members", response_model=list[ResearcherProfileOut])
async def org_members(org_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    org = (await db.execute(select(OrganisationProfile).where(OrganisationProfile.id == org_id))).scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organisation not found")
    # Members = researchers whose institution matches org name
    members = (await db.execute(
        select(ResearcherProfile).where(ResearcherProfile.institution == org.name)
    )).scalars().all()
    return members


@router.post("/profile", response_model=OrganisationProfileOut, status_code=201)
async def create_profile(
    body: OrganisationProfileCreate,
    user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role not in ORG_ROLES:
        raise HTTPException(403, "Only organisation/university/ministry accounts can create an org profile")

    existing = (await db.execute(select(OrganisationProfile).where(OrganisationProfile.user_id == user.id))).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "Profile already exists")

    org = OrganisationProfile(id=uuid.uuid4(), user_id=user.id, **body.model_dump())
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@router.put("/profile", response_model=OrganisationProfileOut)
async def update_profile(
    body: OrganisationProfileUpdate,
    user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_db),
):
    org = (await db.execute(select(OrganisationProfile).where(OrganisationProfile.user_id == user.id))).scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Profile not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(org, k, v)
    await db.commit()
    await db.refresh(org)
    return org


@router.post("/{org_id}/join-request")
async def join_request(
    org_id: uuid.UUID,
    user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != UserRole.researcher:
        raise HTTPException(403, "Only researchers can request to join an organisation")
    org = (await db.execute(select(OrganisationProfile).where(OrganisationProfile.id == org_id))).scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organisation not found")
    # Stub: log the join request (full implementation would create a join_requests table)
    import logging
    logging.getLogger(__name__).info(f"Join request: user {user.id} → org {org_id}")
    return {"message": "Join request submitted. Awaiting admin approval."}
