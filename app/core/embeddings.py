from __future__ import annotations
import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

JINA_MODEL = "jina-embeddings-v2-base-en"
VECTOR_DIM = 768

_qdrant_client = None


async def embed_texts(texts: list[str]) -> list[list[float]]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.jina.ai/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.jina_api_key}"},
            json={"model": JINA_MODEL, "input": texts},
        )
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]


async def embed_query(text: str) -> list[float]:
    return (await embed_texts([text]))[0]


def get_qdrant_client():
    global _qdrant_client
    if _qdrant_client is None:
        from qdrant_client import QdrantClient
        _qdrant_client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
    return _qdrant_client


def ensure_collection() -> None:
    from qdrant_client.models import Distance, VectorParams
    client = get_qdrant_client()
    existing = [c.name for c in client.get_collections().collections]
    if settings.qdrant_collection not in existing:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )
        logger.info(f"Created Qdrant collection '{settings.qdrant_collection}' ({VECTOR_DIM}-dim)")
