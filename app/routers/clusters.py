import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.cluster import Cluster
from app.models.paper import Paper, PaperStatus
from app.schemas.cluster import ClusterOut
from app.schemas.paper import PaperOut, PaginatedPapers

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.get("", response_model=list[ClusterOut])
async def list_clusters(db: AsyncSession = Depends(get_db)):
    clusters = (await db.execute(select(Cluster).order_by(Cluster.paper_count.desc()))).scalars().all()
    return clusters


@router.get("/gaps", response_model=list[ClusterOut])
async def research_gaps(db: AsyncSession = Depends(get_db)):
    clusters = (await db.execute(select(Cluster).where(Cluster.gap_score >= 2).order_by(Cluster.gap_score.desc()))).scalars().all()
    return clusters


@router.get("/trends")
async def cluster_trends(db: AsyncSession = Depends(get_db)):
    clusters = (await db.execute(select(Cluster.id, Cluster.label, Cluster.decade_trend))).all()
    return [{"id": c.id, "label": c.label, "decade_trend": c.decade_trend} for c in clusters]


@router.get("/{cluster_id}", response_model=ClusterOut)
async def get_cluster(cluster_id: int, db: AsyncSession = Depends(get_db)):
    cluster = (await db.execute(select(Cluster).where(Cluster.id == cluster_id))).scalar_one_or_none()
    if not cluster:
        raise HTTPException(404, "Cluster not found")
    return cluster


@router.get("/{cluster_id}/papers", response_model=PaginatedPapers)
async def cluster_papers(
    cluster_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    q = select(Paper).where(Paper.cluster_id == cluster_id, Paper.status == PaperStatus.published)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    papers = (await db.execute(q.offset((page - 1) * limit).limit(limit))).scalars().all()
    return {"items": papers, "total": total, "page": page, "limit": limit, "pages": math.ceil(total / limit) if limit else 1}
