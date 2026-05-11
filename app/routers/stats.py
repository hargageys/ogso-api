from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.database import get_db
from app.models.paper import Paper, PaperStatus
from app.models.author import ResearcherProfile
from app.models.organisation import OrganisationProfile

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
async def stats(db: AsyncSession = Depends(get_db)):
    total_papers = (await db.execute(select(func.count(Paper.id)).where(Paper.status == PaperStatus.published))).scalar_one()
    total_researchers = (await db.execute(select(func.count(ResearcherProfile.id)))).scalar_one()
    total_orgs = (await db.execute(select(func.count(OrganisationProfile.id)))).scalar_one()
    somali_count = (await db.execute(select(func.count(Paper.id)).where(Paper.somali_authored == True, Paper.status == PaperStatus.published))).scalar_one()
    diss_count = (await db.execute(select(func.count(Paper.id)).where(Paper.doc_type == "dissertation", Paper.status == PaperStatus.published))).scalar_one()
    somali_pct = round(somali_count / total_papers * 100, 1) if total_papers else 0

    papers_per_year = (await db.execute(
        text("SELECT year, COUNT(*) as count FROM papers WHERE status='published' AND year IS NOT NULL AND year >= EXTRACT(YEAR FROM NOW()) - 10 GROUP BY year ORDER BY year")
    )).fetchall()
    top_categories = (await db.execute(
        text("SELECT category, COUNT(*) as count FROM papers WHERE status='published' AND category IS NOT NULL GROUP BY category ORDER BY count DESC LIMIT 10")
    )).fetchall()
    top_sources = (await db.execute(
        text("SELECT source, COUNT(*) as count FROM papers WHERE status='published' AND source IS NOT NULL GROUP BY source ORDER BY count DESC LIMIT 10")
    )).fetchall()

    return {
        "total_papers": total_papers,
        "total_researchers": total_researchers,
        "total_organisations": total_orgs,
        "somali_authored_count": somali_count,
        "somali_authored_percent": somali_pct,
        "dissertations_count": diss_count,
        "papers_per_year": [{"year": r[0], "count": r[1]} for r in papers_per_year],
        "top_categories": [{"category": r[0], "count": r[1]} for r in top_categories],
        "top_sources": [{"source": r[0], "count": r[1]} for r in top_sources],
    }


@router.get("/timeline")
async def timeline(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        text("SELECT year, COUNT(*) as count FROM papers WHERE status='published' AND year >= 1980 AND year IS NOT NULL GROUP BY year ORDER BY year")
    )).fetchall()
    return [{"year": r[0], "count": r[1]} for r in rows]


@router.get("/categories")
async def categories(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count(Paper.id)).where(Paper.status == PaperStatus.published))).scalar_one()
    rows = (await db.execute(
        text("SELECT category, COUNT(*) as count FROM papers WHERE status='published' AND category IS NOT NULL GROUP BY category ORDER BY count DESC")
    )).fetchall()
    return [{"category": r[0], "count": r[1], "percent": round(r[1] / total * 100, 1) if total else 0} for r in rows]


@router.get("/sources")
async def sources(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        text("SELECT source, COUNT(*) as count FROM papers WHERE status='published' AND source IS NOT NULL GROUP BY source ORDER BY count DESC")
    )).fetchall()
    return [{"source": r[0], "count": r[1]} for r in rows]


@router.get("/map")
async def map_data(db: AsyncSession = Depends(get_db)):
    researchers = (await db.execute(
        text("SELECT country, COUNT(*) as count FROM researcher_profiles WHERE country IS NOT NULL GROUP BY country")
    )).fetchall()
    orgs = (await db.execute(
        text("SELECT country, COUNT(*) as count FROM organisation_profiles WHERE country IS NOT NULL GROUP BY country")
    )).fetchall()
    return {
        "researchers": [{"country": r[0], "count": r[1]} for r in researchers],
        "organisations": [{"country": r[0], "count": r[1]} for r in orgs],
    }
