import uuid
import math
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.dependencies import get_active_user
from app.models.user import User
from app.models.submission import Submission, SubmissionStatus
from app.schemas.submission import SubmissionCreate, SubmissionUpdate, SubmissionOut, PaginatedSubmissions

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.post("", response_model=SubmissionOut, status_code=201)
async def create_submission(
    body: SubmissionCreate,
    user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_db),
):
    sub = Submission(
        id=uuid.uuid4(),
        submitted_by=user.id,
        title=body.title,
        abstract=body.abstract,
        authors=body.authors,
        year=str(body.year) if body.year else None,
        doi=body.doi,
        file_url=body.file_url,
        status=SubmissionStatus.draft,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


@router.post("/{submission_id}/submit")
async def submit_submission(
    submission_id: uuid.UUID,
    user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_db),
):
    sub = (await db.execute(select(Submission).where(Submission.id == submission_id))).scalar_one_or_none()
    if not sub:
        raise HTTPException(404, "Submission not found")
    if sub.submitted_by != user.id:
        raise HTTPException(403, "Not your submission")
    if sub.status != SubmissionStatus.draft:
        raise HTTPException(400, "Can only submit a draft")
    sub.status = SubmissionStatus.submitted
    sub.submitted_at = datetime.now(timezone.utc)
    await db.commit()
    import logging
    logging.getLogger(__name__).info(f"[STUB] Admin notified of submission {submission_id}")
    return {"message": "Submission received. Admin will review shortly."}


@router.get("/mine", response_model=PaginatedSubmissions)
async def my_submissions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Submission).where(Submission.submitted_by == user.id)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    subs = (await db.execute(q.order_by(Submission.created_at.desc()).offset((page - 1) * limit).limit(limit))).scalars().all()
    return {"items": subs, "total": total, "page": page, "limit": limit, "pages": math.ceil(total / limit) if limit else 1}


@router.get("/{submission_id}", response_model=SubmissionOut)
async def get_submission(
    submission_id: uuid.UUID,
    user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import UserRole
    sub = (await db.execute(select(Submission).where(Submission.id == submission_id))).scalar_one_or_none()
    if not sub:
        raise HTTPException(404, "Submission not found")
    if sub.submitted_by != user.id and user.role != UserRole.admin:
        raise HTTPException(403, "Access denied")
    return sub


@router.put("/{submission_id}", response_model=SubmissionOut)
async def update_submission(
    submission_id: uuid.UUID,
    body: SubmissionUpdate,
    user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_db),
):
    sub = (await db.execute(select(Submission).where(Submission.id == submission_id))).scalar_one_or_none()
    if not sub:
        raise HTTPException(404, "Submission not found")
    if sub.submitted_by != user.id:
        raise HTTPException(403, "Not your submission")
    if sub.status not in (SubmissionStatus.draft, SubmissionStatus.revision_requested):
        raise HTTPException(400, "Can only edit draft or revision_requested submissions")
    for k, v in body.model_dump(exclude_unset=True).items():
        if k == "year":
            setattr(sub, k, str(v) if v else None)
        else:
            setattr(sub, k, v)
    await db.commit()
    await db.refresh(sub)
    return sub
