import uuid
import math
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, and_
from app.database import get_db
from app.dependencies import get_admin_user
from app.models.user import User, UserStatus, UserRole
from app.models.paper import Paper, PaperStatus
from app.models.submission import Submission, SubmissionStatus
from app.models.author import ResearcherProfile, AuthorPaperLink
from app.models.organisation import OrganisationProfile
from app.models.brief import PolicyBrief
from app.models.audit import AuditLog
from app.schemas.user import UserOut, UserDetail, PaginatedUsers
from app.schemas.paper import PaperOut, PaperImportItem, PaperImportResponse, PaginatedPapers
from app.schemas.submission import SubmissionOut, PaginatedSubmissions
from app.schemas.author import ResearcherProfileOut, PaginatedResearchers
from app.schemas.organisation import OrganisationProfileOut, PaginatedOrganisations
from app.schemas.brief import BriefOut, PaginatedBriefs
from app.core.email import send_approval_email, send_rejection_email
from pydantic import BaseModel
import re

router = APIRouter(prefix="/admin", tags=["admin"])


class ReasonBody(BaseModel):
    reason: str = ""


class ReviewBody(BaseModel):
    reviewer_notes: str = ""


async def _log(db: AsyncSession, admin: User, action: str, target_type: str, target_id: str, notes: str = ""):
    db.add(AuditLog(
        id=uuid.uuid4(),
        admin_id=admin.id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        notes=notes,
    ))


def _paginate(query_result, page, limit, total):
    return {
        "items": query_result,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": math.ceil(total / limit) if limit else 1,
    }


# ── USER MANAGEMENT ──────────────────────────────────────────

@router.get("/users", response_model=PaginatedUsers)
async def list_users(
    status: str | None = None,
    role: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    q = select(User)
    if status:
        q = q.where(User.status == status)
    if role:
        q = q.where(User.role == role)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    users = (await db.execute(q.offset((page - 1) * limit).limit(limit))).scalars().all()
    return _paginate(users, page, limit, total)


@router.get("/users/pending", response_model=PaginatedUsers)
async def list_pending_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    q = select(User).where(User.status == UserStatus.pending)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    users = (await db.execute(q.offset((page - 1) * limit).limit(limit))).scalars().all()
    return _paginate(users, page, limit, total)


@router.get("/users/{user_id}", response_model=UserDetail)
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.post("/users/{user_id}/approve")
async def approve_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    user.status = UserStatus.active
    user.approved_by = admin.id
    user.approved_at = datetime.now(timezone.utc)
    await _log(db, admin, "approve_user", "user", str(user_id))
    await db.commit()
    send_approval_email(user.email, user.full_name or "")
    return {"message": "User approved"}


@router.post("/users/{user_id}/reject")
async def reject_user(user_id: uuid.UUID, body: ReasonBody, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    user.status = UserStatus.suspended
    await _log(db, admin, "reject_user", "user", str(user_id), body.reason)
    await db.commit()
    send_rejection_email(user.email, body.reason)
    return {"message": "User rejected"}


@router.post("/users/{user_id}/suspend")
async def suspend_user(user_id: uuid.UUID, body: ReasonBody, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    user.status = UserStatus.suspended
    await _log(db, admin, "suspend_user", "user", str(user_id), body.reason)
    await db.commit()
    return {"message": "User suspended"}


@router.post("/users/{user_id}/reinstate")
async def reinstate_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    user.status = UserStatus.active
    await _log(db, admin, "reinstate_user", "user", str(user_id))
    await db.commit()
    return {"message": "User reinstated"}


# ── PAPER MANAGEMENT ─────────────────────────────────────────

@router.get("/papers", response_model=PaginatedPapers)
async def list_papers(
    status: str | None = None,
    source: str | None = None,
    category: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    q = select(Paper)
    if status:
        q = q.where(Paper.status == status)
    if source:
        q = q.where(Paper.source == source)
    if category:
        q = q.where(Paper.category == category)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    papers = (await db.execute(q.offset((page - 1) * limit).limit(limit))).scalars().all()
    return _paginate(papers, page, limit, total)


@router.post("/papers/{paper_id}/publish")
async def publish_paper(paper_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    paper = (await db.execute(select(Paper).where(Paper.id == paper_id))).scalar_one_or_none()
    if not paper:
        raise HTTPException(404, "Paper not found")
    paper.status = PaperStatus.published
    await _log(db, admin, "publish_paper", "paper", paper_id)
    await db.commit()
    return {"message": "Paper published"}


@router.post("/papers/{paper_id}/reject")
async def reject_paper(paper_id: str, body: ReasonBody, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    paper = (await db.execute(select(Paper).where(Paper.id == paper_id))).scalar_one_or_none()
    if not paper:
        raise HTTPException(404, "Paper not found")
    paper.status = PaperStatus.rejected
    await _log(db, admin, "reject_paper", "paper", paper_id, body.reason)
    await db.commit()
    return {"message": "Paper rejected"}


@router.post("/papers/import", response_model=PaperImportResponse)
async def import_papers(
    papers: list[PaperImportItem],
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    def _fingerprint(title: str) -> str:
        return re.sub(r"[^a-z0-9]", "", title.lower())

    existing_dois = set()
    existing_fps = set()

    doi_rows = (await db.execute(select(Paper.doi).where(Paper.doi.isnot(None)))).scalars().all()
    existing_dois = set(doi_rows)

    title_rows = (await db.execute(select(Paper.title))).scalars().all()
    existing_fps = {_fingerprint(t) for t in title_rows}

    imported = skipped = 0
    for item in papers:
        if item.doi and item.doi in existing_dois:
            skipped += 1
            continue
        fp = _fingerprint(item.title)
        if fp in existing_fps:
            skipped += 1
            continue

        paper_id = item.id or f"import_{uuid.uuid4().hex[:12]}"
        year = int(item.year) if item.year else None
        db.add(Paper(
            id=paper_id,
            title=item.title,
            authors=item.authors,
            year=year,
            abstract=item.abstract,
            source=item.source,
            url=item.url,
            doi=item.doi,
            institution=item.institution,
            category=item.category,
            doc_type=item.doc_type,
            somali_authored=item.somali_author,
            citations=item.citations,
            status=PaperStatus.pending_embed,
        ))
        existing_dois.add(item.doi)
        existing_fps.add(fp)
        imported += 1

    await db.commit()
    return PaperImportResponse(imported=imported, skipped=skipped, total=len(papers))


@router.post("/papers/trigger-embed")
async def trigger_embed(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    from app.workers.embedder import run_embedder
    job_id = uuid.uuid4().hex
    background_tasks.add_task(run_embedder)
    return {"job_id": job_id, "message": "Embedding job started in background"}


@router.post("/papers/trigger-cluster")
async def trigger_cluster(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    from app.workers.clusterer import run_clusterer
    job_id = uuid.uuid4().hex
    background_tasks.add_task(run_clusterer)
    return {"job_id": job_id, "message": "Clustering job started in background"}


# ── SUBMISSION MANAGEMENT ─────────────────────────────────────

@router.get("/submissions", response_model=PaginatedSubmissions)
async def list_submissions(
    status: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    q = select(Submission)
    if status:
        q = q.where(Submission.status == status)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    subs = (await db.execute(q.offset((page - 1) * limit).limit(limit))).scalars().all()
    return _paginate(subs, page, limit, total)


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
async def get_submission(submission_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    sub = (await db.execute(select(Submission).where(Submission.id == submission_id))).scalar_one_or_none()
    if not sub:
        raise HTTPException(404, "Submission not found")
    return sub


@router.post("/submissions/{submission_id}/approve")
async def approve_submission(submission_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    sub = (await db.execute(select(Submission).where(Submission.id == submission_id))).scalar_one_or_none()
    if not sub:
        raise HTTPException(404, "Submission not found")

    paper_id = f"ogso_{uuid.uuid4().hex[:12]}"
    year = int(sub.year) if sub.year else None
    db.add(Paper(
        id=paper_id,
        title=sub.title,
        authors=sub.authors,
        year=year,
        abstract=sub.abstract,
        doi=sub.doi,
        status=PaperStatus.pending_embed,
        ogso_type="original",
    ))
    sub.status = SubmissionStatus.approved
    sub.paper_id = paper_id
    sub.reviewed_by = admin.id
    sub.reviewed_at = datetime.now(timezone.utc)
    await _log(db, admin, "approve_submission", "submission", str(submission_id))
    await db.commit()
    return {"message": "Submission approved", "paper_id": paper_id}


@router.post("/submissions/{submission_id}/reject")
async def reject_submission(submission_id: uuid.UUID, body: ReviewBody, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    sub = (await db.execute(select(Submission).where(Submission.id == submission_id))).scalar_one_or_none()
    if not sub:
        raise HTTPException(404, "Submission not found")
    sub.status = SubmissionStatus.rejected
    sub.reviewer_notes = body.reviewer_notes
    sub.reviewed_by = admin.id
    sub.reviewed_at = datetime.now(timezone.utc)
    await _log(db, admin, "reject_submission", "submission", str(submission_id))
    await db.commit()
    return {"message": "Submission rejected"}


@router.post("/submissions/{submission_id}/request-revision")
async def request_revision(submission_id: uuid.UUID, body: ReviewBody, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    sub = (await db.execute(select(Submission).where(Submission.id == submission_id))).scalar_one_or_none()
    if not sub:
        raise HTTPException(404, "Submission not found")
    sub.status = SubmissionStatus.revision_requested
    sub.reviewer_notes = body.reviewer_notes
    sub.reviewed_by = admin.id
    sub.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Revision requested"}


# ── ORGANISATION MANAGEMENT ───────────────────────────────────

@router.get("/organisations", response_model=PaginatedOrganisations)
async def list_organisations(
    verified: bool | None = None,
    org_type: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    q = select(OrganisationProfile)
    if verified is not None:
        q = q.where(OrganisationProfile.verified == verified)
    if org_type:
        q = q.where(OrganisationProfile.org_type == org_type)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    orgs = (await db.execute(q.offset((page - 1) * limit).limit(limit))).scalars().all()
    return _paginate(orgs, page, limit, total)


@router.post("/organisations/{org_id}/verify")
async def verify_org(org_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    org = (await db.execute(select(OrganisationProfile).where(OrganisationProfile.id == org_id))).scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organisation not found")
    org.verified = True
    await _log(db, admin, "verify_organisation", "organisation", str(org_id))
    await db.commit()
    return {"message": "Organisation verified"}


@router.post("/organisations/{org_id}/partner")
async def set_partner(org_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    org = (await db.execute(select(OrganisationProfile).where(OrganisationProfile.id == org_id))).scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organisation not found")
    org.partner = True
    await _log(db, admin, "set_partner", "organisation", str(org_id))
    await db.commit()
    return {"message": "Organisation marked as partner"}


# ── RESEARCHER MANAGEMENT ─────────────────────────────────────

@router.get("/researchers", response_model=PaginatedResearchers)
async def list_researchers(
    verified: bool | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    q = select(ResearcherProfile)
    if verified is not None:
        q = q.where(ResearcherProfile.verified == verified)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    researchers = (await db.execute(q.offset((page - 1) * limit).limit(limit))).scalars().all()
    return _paginate(researchers, page, limit, total)


@router.post("/researchers/{researcher_id}/verify")
async def verify_researcher(researcher_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    r = (await db.execute(select(ResearcherProfile).where(ResearcherProfile.id == researcher_id))).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Researcher not found")
    r.verified = True
    await _log(db, admin, "verify_researcher", "researcher", str(researcher_id))
    await db.commit()
    return {"message": "Researcher verified"}


@router.post("/researchers/{researcher_id}/verify-paper-claim")
async def verify_paper_claim(researcher_id: uuid.UUID, link_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    link = (await db.execute(select(AuthorPaperLink).where(AuthorPaperLink.id == link_id))).scalar_one_or_none()
    if not link:
        raise HTTPException(404, "Link not found")
    link.verified = True
    await _log(db, admin, "verify_paper_claim", "author_paper_link", str(link_id))
    await db.commit()
    return {"message": "Paper claim verified"}


# ── POLICY BRIEFS ─────────────────────────────────────────────

@router.get("/briefs", response_model=PaginatedBriefs)
async def list_briefs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    q = select(PolicyBrief)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    briefs = (await db.execute(q.offset((page - 1) * limit).limit(limit))).scalars().all()
    return _paginate(briefs, page, limit, total)


@router.get("/briefs/{brief_id}", response_model=BriefOut)
async def get_brief(brief_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    brief = (await db.execute(select(PolicyBrief).where(PolicyBrief.id == brief_id))).scalar_one_or_none()
    if not brief:
        raise HTTPException(404, "Brief not found")
    return brief


# ── AUDIT LOG ─────────────────────────────────────────────────

@router.get("/audit")
async def get_audit(
    admin_id: uuid.UUID | None = None,
    action: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    q = select(AuditLog).order_by(AuditLog.created_at.desc())
    if admin_id:
        q = q.where(AuditLog.admin_id == admin_id)
    if action:
        q = q.where(AuditLog.action == action)
    if date_from:
        q = q.where(AuditLog.created_at >= date_from)
    if date_to:
        q = q.where(AuditLog.created_at <= date_to)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    logs = (await db.execute(q.offset((page - 1) * limit).limit(limit))).scalars().all()
    return _paginate(
        [{"id": str(l.id), "admin_id": str(l.admin_id), "action": l.action, "target_type": l.target_type, "target_id": l.target_id, "notes": l.notes, "created_at": l.created_at} for l in logs],
        page, limit, total
    )


# ── STATS ─────────────────────────────────────────────────────

@router.get("/stats")
async def admin_stats(db: AsyncSession = Depends(get_db), admin: User = Depends(get_admin_user)):
    from sqlalchemy import case, cast, Date
    from datetime import date, timedelta

    users_by_role = {}
    for role in UserRole:
        count = (await db.execute(select(func.count(User.id)).where(User.role == role))).scalar_one()
        users_by_role[role.value] = count

    users_by_status = {}
    for st in UserStatus:
        count = (await db.execute(select(func.count(User.id)).where(User.status == st))).scalar_one()
        users_by_status[st.value] = count

    total_papers = (await db.execute(select(func.count(Paper.id)))).scalar_one()
    total_submissions = (await db.execute(select(func.count(Submission.id)))).scalar_one()
    total_orgs = (await db.execute(select(func.count(OrganisationProfile.id)))).scalar_one()
    total_researchers = (await db.execute(select(func.count(ResearcherProfile.id)))).scalar_one()

    pending_users = (await db.execute(select(func.count(User.id)).where(User.status == UserStatus.pending))).scalar_one()
    pending_subs = (await db.execute(select(func.count(Submission.id)).where(Submission.status == SubmissionStatus.submitted))).scalar_one()

    return {
        "total_users": {"by_role": users_by_role, "by_status": users_by_status},
        "total_papers": total_papers,
        "total_submissions": total_submissions,
        "total_organisations": total_orgs,
        "total_researchers": total_researchers,
        "pending_actions": {"pending_users": pending_users, "pending_submissions": pending_subs},
    }
