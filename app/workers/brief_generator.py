import json
import logging
from datetime import datetime, timezone
from sqlalchemy import select, text
from app.database import AsyncSessionLocal
from app.models.brief import PolicyBrief, BriefStatus
from app.models.paper import Paper
from app.config import settings

logger = logging.getLogger(__name__)


async def process_brief(brief_id: str, query: str):
    logger.info(f"BriefGen: processing {brief_id}")

    if not settings.anthropic_api_key:
        logger.warning("BriefGen: ANTHROPIC_API_KEY not set — cannot generate brief")
        async with AsyncSessionLocal() as db:
            brief = (await db.execute(select(PolicyBrief).where(PolicyBrief.id == brief_id))).scalar_one_or_none()
            if brief:
                brief.status = BriefStatus.failed
                await db.commit()
        return

    async with AsyncSessionLocal() as db:
        brief = (await db.execute(select(PolicyBrief).where(PolicyBrief.id == brief_id))).scalar_one_or_none()
        if not brief:
            logger.error(f"BriefGen: brief {brief_id} not found")
            return
        brief.status = BriefStatus.processing
        await db.commit()

    try:
        from app.core.embeddings import embed_query, get_qdrant_client
        vec = await embed_query(query)

        client = get_qdrant_client()
        results = client.query_points(
            collection_name=settings.qdrant_collection,
            query=vec,
            limit=50,
        )
        paper_ids = [h.payload["paper_id"] for h in results.points]

        async with AsyncSessionLocal() as db:
            papers = (await db.execute(select(Paper).where(Paper.id.in_(paper_ids)))).scalars().all()

        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        findings = []
        for p in papers[:20]:
            if not p.abstract:
                continue
            resp = client.messages.create(
                model="claude-opus-4-7",
                max_tokens=300,
                messages=[{
                    "role": "user",
                    "content": f"Extract from this abstract: main finding, methodology, year, policy recommendation. Be concise.\n\nAbstract: {p.abstract[:1500]}",
                }],
            )
            findings.append(f"[{p.year or 'n.d.'}] {p.title}: {resp.content[0].text}")

        findings_text = "\n\n".join(findings)

        synthesis_resp = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": f"""You are a policy analyst specialising in Somalia. Write a 3-page policy brief answering this question: "{query}"

Based on these research findings:
{findings_text}

Structure: Executive Summary, Key Findings, Policy Recommendations, Conclusion.
Write in clear plain English suitable for government officials.""",
            }],
        )
        content_english = synthesis_resp.content[0].text

        somali_resp = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=2500,
            messages=[{
                "role": "user",
                "content": f"Translate the following policy brief into Somali language:\n\n{content_english}",
            }],
        )
        content_somali = somali_resp.content[0].text

        script_resp = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=800,
            messages=[{
                "role": "user",
                "content": f"Convert this policy brief into a short 2-minute video narration script. Be engaging and accessible:\n\n{content_english}",
            }],
        )
        video_script = script_resp.content[0].text

        async with AsyncSessionLocal() as db:
            brief = (await db.execute(select(PolicyBrief).where(PolicyBrief.id == brief_id))).scalar_one_or_none()
            if brief:
                brief.status = BriefStatus.complete
                brief.content_english = content_english
                brief.content_somali = content_somali
                brief.video_script = video_script
                brief.source_paper_ids = paper_ids
                brief.paper_count = len(papers)
                brief.completed_at = datetime.now(timezone.utc)
                await db.commit()

        logger.info(f"BriefGen: {brief_id} complete")

    except Exception as e:
        logger.error(f"BriefGen: {brief_id} failed — {e}")
        async with AsyncSessionLocal() as db:
            brief = (await db.execute(select(PolicyBrief).where(PolicyBrief.id == brief_id))).scalar_one_or_none()
            if brief:
                brief.status = BriefStatus.failed
                await db.commit()
