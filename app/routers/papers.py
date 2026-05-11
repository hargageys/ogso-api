import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.paper import Paper, PaperStatus
from app.models.author import AuthorPaperLink, ResearcherProfile
from app.schemas.paper import PaperOut, PaginatedPapers
from app.schemas.author import ResearcherProfileOut

router = APIRouter(prefix="/papers", tags=["papers"])


@router.get("", response_model=PaginatedPapers)
async def list_papers(
    category: str | None = None,
    source: str | None = None,
    doc_type: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    somali_authored: bool | None = None,
    ogso_type: str | None = None,
    cluster_id: int | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    q = select(Paper).where(Paper.status == PaperStatus.published)
    if category:
        q = q.where(Paper.category == category)
    if source:
        q = q.where(Paper.source == source)
    if doc_type:
        q = q.where(Paper.doc_type == doc_type)
    if year_from:
        q = q.where(Paper.year >= year_from)
    if year_to:
        q = q.where(Paper.year <= year_to)
    if somali_authored is not None:
        q = q.where(Paper.somali_authored == somali_authored)
    if ogso_type:
        q = q.where(Paper.ogso_type == ogso_type)
    if cluster_id is not None:
        q = q.where(Paper.cluster_id == cluster_id)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    papers = (await db.execute(q.order_by(Paper.year.desc()).offset((page - 1) * limit).limit(limit))).scalars().all()
    return {"items": papers, "total": total, "page": page, "limit": limit, "pages": math.ceil(total / limit) if limit else 1}


@router.get("/{paper_id}", response_model=PaperOut)
async def get_paper(paper_id: str, db: AsyncSession = Depends(get_db)):
    paper = (await db.execute(select(Paper).where(Paper.id == paper_id))).scalar_one_or_none()
    if not paper:
        raise HTTPException(404, "Paper not found")
    return paper


@router.get("/{paper_id}/similar", response_model=list[PaperOut])
async def similar_papers(paper_id: str, db: AsyncSession = Depends(get_db)):
    from app.core.embeddings import get_qdrant_client
    from app.config import settings
    import uuid

    paper = (await db.execute(select(Paper).where(Paper.id == paper_id))).scalar_one_or_none()
    if not paper:
        raise HTTPException(404, "Paper not found")
    if not paper.qdrant_synced or not settings.qdrant_url:
        return []

    client = get_qdrant_client()
    point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, paper_id))
    points = client.retrieve(
        collection_name=settings.qdrant_collection,
        ids=[point_id],
        with_vectors=True,
    )
    if not points:
        return []

    results = client.query_points(
        collection_name=settings.qdrant_collection,
        query=points[0].vector,
        limit=11,
    )
    ids = [h.payload["paper_id"] for h in results.points if h.payload["paper_id"] != paper_id][:10]
    if not ids:
        return []
    similar = (await db.execute(select(Paper).where(Paper.id.in_(ids)))).scalars().all()
    return similar


@router.get("/{paper_id}/authors", response_model=list[ResearcherProfileOut])
async def paper_authors(paper_id: str, db: AsyncSession = Depends(get_db)):
    links = (await db.execute(
        select(AuthorPaperLink).where(
            AuthorPaperLink.paper_id == paper_id,
            AuthorPaperLink.verified == True,
        )
    )).scalars().all()
    if not links:
        return []
    researcher_ids = [l.researcher_id for l in links]
    researchers = (await db.execute(select(ResearcherProfile).where(ResearcherProfile.id.in_(researcher_ids)))).scalars().all()
    return researchers
