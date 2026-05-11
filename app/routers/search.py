import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.database import get_db
from app.dependencies import get_active_user
from app.models.user import User
from app.models.paper import Paper, PaperStatus
from app.models.brief import PolicyBrief, BriefStatus
from app.schemas.paper import PaperOut
from app.schemas.search import SemanticSearchRequest, PolicySearchRequest, SemanticSearchResult, PolicySearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[PaperOut])
async def keyword_search(q: str = Query(..., min_length=1), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        text("""
            SELECT *, ts_rank(
                to_tsvector('english', coalesce(title,'') || ' ' || coalesce(abstract,'')),
                plainto_tsquery('english', :q)
            ) AS rank
            FROM papers
            WHERE status = 'published'
              AND to_tsvector('english', coalesce(title,'') || ' ' || coalesce(abstract,''))
                  @@ plainto_tsquery('english', :q)
            ORDER BY rank DESC
            LIMIT 20
        """),
        {"q": q},
    )).fetchall()
    ids = [r[0] for r in rows]
    if not ids:
        return []
    papers = (await db.execute(select(Paper).where(Paper.id.in_(ids)))).scalars().all()
    paper_map = {p.id: p for p in papers}
    return [paper_map[i] for i in ids if i in paper_map]


@router.post("/semantic", response_model=list[SemanticSearchResult])
async def semantic_search(body: SemanticSearchRequest, db: AsyncSession = Depends(get_db)):
    from app.core.embeddings import embed_query, get_qdrant_client
    from app.config import settings

    if not settings.qdrant_url:
        return []

    vec = await embed_query(body.query)
    client = get_qdrant_client()
    results = client.query_points(
        collection_name=settings.qdrant_collection,
        query=vec,
        limit=body.limit if hasattr(body, "limit") else 20,
    )

    ids = [h.payload["paper_id"] for h in results.points]
    scores = {h.payload["paper_id"]: h.score for h in results.points}
    if not ids:
        return []

    papers = (await db.execute(select(Paper).where(Paper.id.in_(ids)))).scalars().all()
    paper_map = {p.id: p for p in papers}
    return [{"paper": paper_map[i], "score": scores[i]} for i in ids if i in paper_map]


@router.post("/policy", response_model=PolicySearchResponse)
async def policy_search(
    body: PolicySearchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    brief_id = uuid.uuid4()
    brief = PolicyBrief(
        id=brief_id,
        requested_by=user.id,
        query=body.query,
        status=BriefStatus.queued,
    )
    db.add(brief)
    await db.commit()

    from app.workers.brief_generator import process_brief
    background_tasks.add_task(process_brief, str(brief_id), body.query)

    return PolicySearchResponse(
        brief_id=str(brief_id),
        message="Brief generation queued. Poll GET /briefs/{brief_id} for results.",
    )
