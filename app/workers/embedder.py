import uuid
import logging
import asyncio
from sqlalchemy import select, text, func
from app.database import AsyncSessionLocal
from app.models.paper import Paper
from app.config import settings

logger = logging.getLogger(__name__)

JINA_BATCH = 100
DB_CHUNK = 500
MAX_RETRIES = 5


async def run_embedder():
    from app.core.embeddings import embed_texts, get_qdrant_client, ensure_collection
    from qdrant_client.models import PointStruct

    logger.info("Embedder: starting run")
    ensure_collection()
    client = get_qdrant_client()

    async with AsyncSessionLocal() as db:
        total = (await db.execute(
            select(func.count()).where(Paper.qdrant_synced == False)
        )).scalar_one()

    if not total:
        logger.info("Embedder: nothing to embed")
        return

    total_batches = -(-total // JINA_BATCH)
    logger.info(f"Embedder: {total} papers → Jina API ({total_batches} batches)")

    offset = 0
    batch_num = 0

    while True:
        async with AsyncSessionLocal() as db:
            chunk = (await db.execute(
                select(Paper)
                .where(Paper.qdrant_synced == False)
                .order_by(Paper.id)
                .limit(DB_CHUNK)
            )).scalars().all()

        if not chunk:
            break

        for i in range(0, len(chunk), JINA_BATCH):
            batch = chunk[i:i + JINA_BATCH]
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    texts = [f"{p.title or ''} {p.abstract or ''}".strip() for p in batch]
                    embeddings = await embed_texts(texts)

                    points = [
                        PointStruct(
                            id=str(uuid.uuid5(uuid.NAMESPACE_URL, p.id)),
                            vector=emb,
                            payload={"paper_id": p.id},
                        )
                        for p, emb in zip(batch, embeddings)
                    ]
                    client.upsert(collection_name=settings.qdrant_collection, points=points)

                    paper_ids = [p.id for p in batch]
                    async with AsyncSessionLocal() as db:
                        await db.execute(
                            text("UPDATE papers SET qdrant_synced = TRUE WHERE id = ANY(:ids)"),
                            {"ids": paper_ids},
                        )
                        await db.commit()

                    batch_num += 1
                    synced = batch_num * JINA_BATCH
                    logger.info(f"Embedder: batch {batch_num}/{total_batches} done ({min(synced, total)}/{total})")
                    break
                except Exception as e:
                    wait = 10 * attempt
                    logger.warning(f"Embedder: attempt {attempt}/{MAX_RETRIES} failed ({e}) — retrying in {wait}s")
                    if attempt == MAX_RETRIES:
                        logger.error("Embedder: max retries reached, stopping")
                        return
                    await asyncio.sleep(wait)

    logger.info(f"Embedder: completed — all {total} papers synced to Qdrant")
