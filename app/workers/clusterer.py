import logging
import json
from datetime import datetime, timezone
from collections import Counter
from sqlalchemy import select, text
from app.database import AsyncSessionLocal
from app.models.paper import Paper
from app.models.cluster import Cluster

logger = logging.getLogger(__name__)

N_CLUSTERS = 25


async def run_clusterer():
    logger.info("Clusterer: starting run")

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            text("SELECT id, title, abstract, year, somali_authored, citations, cluster_id FROM papers WHERE embedding IS NOT NULL")
        )).fetchall()

        if len(rows) < N_CLUSTERS:
            logger.info(f"Clusterer: only {len(rows)} papers, skipping")
            return

        emb_rows = (await db.execute(
            text("SELECT id, embedding::text FROM papers WHERE embedding IS NOT NULL")
        )).fetchall()

    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer

    paper_map = {r[0]: r for r in rows}
    ids = [r[0] for r in emb_rows]

    def parse_vec(s):
        return [float(x) for x in s.strip("[]").split(",")]

    X = np.array([parse_vec(r[1]) for r in emb_rows])

    km = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init="auto")
    labels = km.fit_predict(X)

    id_to_cluster = {ids[i]: int(labels[i]) for i in range(len(ids))}

    # Build cluster stats
    clusters: dict[int, dict] = {i: {"ids": [], "years": [], "citations": [], "somali": []} for i in range(N_CLUSTERS)}
    for paper_id, cid in id_to_cluster.items():
        r = paper_map.get(paper_id)
        if r:
            clusters[cid]["ids"].append(paper_id)
            if r[3]:
                clusters[cid]["years"].append(r[3])
            clusters[cid]["citations"].append(r[5] or 0)
            clusters[cid]["somali"].append(1 if r[4] else 0)

    # TF-IDF per cluster for top terms
    cluster_texts = {}
    for paper_id, cid in id_to_cluster.items():
        r = paper_map.get(paper_id)
        if r:
            cluster_texts.setdefault(cid, []).append(f"{r[1] or ''} {r[2] or ''}")

    tfidf = TfidfVectorizer(max_features=1000, stop_words="english")
    all_texts = [" ".join(cluster_texts.get(i, [""])) for i in range(N_CLUSTERS)]
    try:
        tfidf_matrix = tfidf.fit_transform(all_texts)
        feature_names = tfidf.get_feature_names_out()
    except Exception:
        feature_names = []
        tfidf_matrix = None

    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        # Update paper cluster assignments
        for paper_id, cid in id_to_cluster.items():
            await db.execute(
                text("UPDATE papers SET cluster_id = :cid WHERE id = :id"),
                {"cid": cid + 1, "id": paper_id},  # 1-indexed
            )

        # Upsert clusters
        for i in range(N_CLUSTERS):
            cid = i + 1
            c = clusters[i]
            paper_count = len(c["ids"])
            total_citations = sum(c["citations"])
            somali_ratio = sum(c["somali"]) / paper_count if paper_count else 0
            recent_count = sum(1 for y in c["years"] if y and y >= 2022)
            gap_score = 0
            if paper_count < 5:
                gap_score += 2
            elif paper_count < 20:
                gap_score += 1
            if recent_count == 0:
                gap_score += 1

            # Decade trend
            decade_trend = {}
            for y in c["years"]:
                decade = (y // 10) * 10
                decade_trend[str(decade)] = decade_trend.get(str(decade), 0) + 1

            # Top terms from TF-IDF
            top_terms = []
            if tfidf_matrix is not None and len(feature_names):
                row = tfidf_matrix[i].toarray()[0]
                top_idx = row.argsort()[-5:][::-1]
                top_terms = [feature_names[j] for j in top_idx if row[j] > 0]

            label = " / ".join(top_terms[:3]) if top_terms else f"Cluster {cid}"

            existing = (await db.execute(select(Cluster).where(Cluster.id == cid))).scalar_one_or_none()
            if existing:
                existing.label = label
                existing.top_terms = top_terms
                existing.paper_count = paper_count
                existing.total_citations = total_citations
                existing.somali_author_ratio = somali_ratio
                existing.recent_count = recent_count
                existing.gap_score = gap_score
                existing.decade_trend = decade_trend
                existing.last_computed = now
            else:
                db.add(Cluster(
                    id=cid,
                    label=label,
                    top_terms=top_terms,
                    paper_count=paper_count,
                    total_citations=total_citations,
                    somali_author_ratio=somali_ratio,
                    recent_count=recent_count,
                    gap_score=gap_score,
                    decade_trend=decade_trend,
                    last_computed=now,
                ))

        await db.commit()

    logger.info(f"Clusterer: complete — {N_CLUSTERS} clusters updated")
