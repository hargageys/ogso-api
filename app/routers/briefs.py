import uuid
import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.dependencies import get_active_user, get_admin_user
from app.models.user import User, UserRole
from app.models.brief import PolicyBrief
from app.schemas.brief import BriefOut, PaginatedBriefs

router = APIRouter(prefix="/briefs", tags=["briefs"])


@router.get("/mine", response_model=PaginatedBriefs)
async def my_briefs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(PolicyBrief).where(PolicyBrief.requested_by == user.id)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    briefs = (await db.execute(q.order_by(PolicyBrief.created_at.desc()).offset((page - 1) * limit).limit(limit))).scalars().all()
    return {"items": briefs, "total": total, "page": page, "limit": limit, "pages": math.ceil(total / limit) if limit else 1}


@router.get("", response_model=PaginatedBriefs)
async def all_briefs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(PolicyBrief)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    briefs = (await db.execute(q.order_by(PolicyBrief.created_at.desc()).offset((page - 1) * limit).limit(limit))).scalars().all()
    return {"items": briefs, "total": total, "page": page, "limit": limit, "pages": math.ceil(total / limit) if limit else 1}


@router.get("/{brief_id}", response_model=BriefOut)
async def get_brief(
    brief_id: uuid.UUID,
    user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_db),
):
    brief = (await db.execute(select(PolicyBrief).where(PolicyBrief.id == brief_id))).scalar_one_or_none()
    if not brief:
        raise HTTPException(404, "Brief not found")
    if brief.requested_by != user.id and user.role != UserRole.admin:
        raise HTTPException(403, "Access denied")
    return brief
