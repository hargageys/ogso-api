import uuid
import math
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.dependencies import get_active_user
from app.models.user import User, UserRole
from app.models.author import ResearcherProfile, AuthorPaperLink
from app.models.paper import Paper, PaperStatus
from app.schemas.author import (
    ResearcherProfileCreate, ResearcherProfileUpdate,
    ResearcherProfileOut, ClaimPaperRequest, PaginatedResearchers,
)
from app.schemas.paper import PaperOut

router = APIRouter(prefix="/authors", tags=["authors"])


@router.get("", response_model=PaginatedResearchers)
async def list_authors(
    country: str | None = None,
    field: str | None = None,
    inside_somalia: bool | None = None,
    somali_diaspora: bool | None = None,
    verified: bool | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    q = select(ResearcherProfile)
    if country:
        q = q.where(ResearcherProfile.country == country)
    if inside_somalia is not None:
        q = q.where(ResearcherProfile.inside_somalia == inside_somalia)
    if somali_diaspora is not None:
        q = q.where(ResearcherProfile.somali_diaspora == somali_diaspora)
    if verified is not None:
        q = q.where(ResearcherProfile.verified == verified)
    if field:
        q = q.where(ResearcherProfile.fields.any(field))

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    researchers = (await db.execute(q.offset((page - 1) * limit).limit(limit))).scalars().all()
    return {"items": researchers, "total": total, "page": page, "limit": limit, "pages": math.ceil(total / limit) if limit else 1}


@router.get("/{researcher_id}", response_model=ResearcherProfileOut)
async def get_author(researcher_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    r = (await db.execute(select(ResearcherProfile).where(ResearcherProfile.id == researcher_id))).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Researcher not found")
    return r


@router.get("/{researcher_id}/papers", response_model=list[PaperOut])
async def author_papers(researcher_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    links = (await db.execute(
        select(AuthorPaperLink).where(
            AuthorPaperLink.researcher_id == researcher_id,
            AuthorPaperLink.claimed == True,
        )
    )).scalars().all()
    if not links:
        return []
    paper_ids = [l.paper_id for l in links]
    papers = (await db.execute(select(Paper).where(Paper.id.in_(paper_ids)))).scalars().all()
    return papers


@router.post("/profile", response_model=ResearcherProfileOut, status_code=201)
async def create_profile(
    body: ResearcherProfileCreate,
    user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != UserRole.researcher:
        raise HTTPException(403, "Only researchers can create a researcher profile")

    existing = (await db.execute(select(ResearcherProfile).where(ResearcherProfile.user_id == user.id))).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "Profile already exists")

    profile = ResearcherProfile(id=uuid.uuid4(), user_id=user.id, **body.model_dump())
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.put("/profile", response_model=ResearcherProfileOut)
async def update_profile(
    body: ResearcherProfileUpdate,
    user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_db),
):
    profile = (await db.execute(select(ResearcherProfile).where(ResearcherProfile.user_id == user.id))).scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Profile not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(profile, k, v)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.post("/claim-paper")
async def claim_paper(
    body: ClaimPaperRequest,
    user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_db),
):
    profile = (await db.execute(select(ResearcherProfile).where(ResearcherProfile.user_id == user.id))).scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Create a researcher profile first")

    paper = (await db.execute(select(Paper).where(Paper.id == body.paper_id))).scalar_one_or_none()
    if not paper:
        raise HTTPException(404, "Paper not found")

    existing = (await db.execute(
        select(AuthorPaperLink).where(
            AuthorPaperLink.researcher_id == profile.id,
            AuthorPaperLink.paper_id == body.paper_id,
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "Already claimed")

    link = AuthorPaperLink(
        id=uuid.uuid4(),
        researcher_id=profile.id,
        paper_id=body.paper_id,
        claimed=True,
        claimed_at=datetime.now(timezone.utc),
    )
    db.add(link)
    await db.commit()
    return {"message": "Claim submitted. Awaiting admin verification.", "link_id": str(link.id)}
