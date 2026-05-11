"""
Migrate papers from an existing ogso.db (SQLite) into Postgres.

Usage:
    python scripts/migrate_sqlite.py --db ogso.db
    python scripts/migrate_sqlite.py --db ogso.db --limit 100
    python scripts/migrate_sqlite.py --db ogso.db --dry-run
    python scripts/migrate_sqlite.py --db ogso.db --status published
    python scripts/migrate_sqlite.py --db ogso.db --table research_papers
"""
import argparse
import asyncio
import json
import re
import sqlite3
import sys
import uuid
from pathlib import Path

# Make sure the project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import AsyncSessionLocal, init_db
from app.models.paper import Paper, PaperStatus, OgsoType

# Map SQLite column names → Paper model field names
COLUMN_MAP = {
    "id": "id",
    "title": "title",
    "abstract": "abstract",
    "year": "year",
    "source": "source",
    "url": "url",
    "doi": "doi",
    "institution": "institution",
    "category": "category",
    "doc_type": "doc_type",
    "language": "language",
    "citations": "citations",
    "full_text": "full_text",
    # common scraper variants
    "somali_author": "somali_authored",
    "somali_authored": "somali_authored",
    "is_somali_author": "somali_authored",
    "authors": "authors",
    "author": "authors",
    "scraped_at": "scraped_at",
}

BATCH_SIZE = 500


def fingerprint(title: str) -> str:
    return re.sub(r"[^a-z0-9]", "", title.lower())


def parse_authors(raw) -> list | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        return raw
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [str(parsed)]
    except (json.JSONDecodeError, TypeError):
        # Comma-separated string
        return [a.strip() for a in str(raw).split(",") if a.strip()]


async def migrate(db_path: str, limit: int | None, dry_run: bool, status: str, table: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Detect schema
    cur = conn.execute(f"PRAGMA table_info({table})")
    columns = [row["name"] for row in cur.fetchall()]

    if not columns:
        print(f"ERROR: Table '{table}' not found in {db_path}")
        print("Available tables:")
        for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            print(f"  {t}")
        sys.exit(1)

    print(f"\nDetected columns in '{table}':")
    mapped = {}
    unmapped = []
    for col in columns:
        if col in COLUMN_MAP:
            mapped[col] = COLUMN_MAP[col]
            print(f"  ✓ {col} → {COLUMN_MAP[col]}")
        else:
            unmapped.append(col)
            print(f"  ✗ {col} (skipped — no mapping)")

    if not mapped.get("title") and "title" not in [COLUMN_MAP.get(c) for c in columns]:
        print("\nERROR: No 'title' column found — cannot migrate without titles.")
        sys.exit(1)

    print()

    sql = f"SELECT * FROM {table}"
    if limit:
        sql += f" LIMIT {limit}"

    rows = conn.execute(sql).fetchall()
    total = len(rows)
    print(f"Found {total} rows to process{' (dry run)' if dry_run else ''}.\n")

    if dry_run:
        conn.close()
        return

    # Pre-load existing DOIs and fingerprints for deduplication
    async with AsyncSessionLocal() as db:
        existing_dois = set((await db.execute(text("SELECT doi FROM papers WHERE doi IS NOT NULL"))).scalars().all())
        existing_fps = set(
            fingerprint(t) for (t,) in (await db.execute(text("SELECT title FROM papers"))).fetchall()
        )

    target_status = PaperStatus(status)
    imported = skipped = errors = 0

    for batch_start in range(0, total, BATCH_SIZE):
        batch = rows[batch_start: batch_start + BATCH_SIZE]
        papers_to_add = []

        for row in batch:
            try:
                # Build field dict from mapped columns
                fields: dict = {}
                for sqlite_col, model_field in mapped.items():
                    val = row[sqlite_col]
                    if val is not None:
                        fields[model_field] = val

                title = fields.get("title")
                if not title:
                    skipped += 1
                    continue

                # Deduplication
                doi = fields.get("doi")
                if doi and doi in existing_dois:
                    skipped += 1
                    continue
                fp = fingerprint(title)
                if fp in existing_fps:
                    skipped += 1
                    continue

                # Build Paper
                paper_id = fields.get("id") or f"sqlite_{uuid.uuid4().hex[:12]}"
                year_raw = fields.get("year")
                try:
                    year = int(year_raw) if year_raw else None
                except (ValueError, TypeError):
                    year = None

                paper = Paper(
                    id=str(paper_id),
                    title=title,
                    authors=parse_authors(fields.get("authors")),
                    year=year,
                    abstract=fields.get("abstract"),
                    full_text=fields.get("full_text"),
                    source=fields.get("source"),
                    url=fields.get("url"),
                    doi=doi,
                    institution=fields.get("institution"),
                    category=fields.get("category"),
                    doc_type=fields.get("doc_type"),
                    language=fields.get("language", "en"),
                    citations=int(fields.get("citations") or 0),
                    somali_authored=bool(fields.get("somali_authored", False)),
                    status=target_status,
                    ogso_type=OgsoType.archive,
                )
                papers_to_add.append(paper)
                existing_dois.add(doi)
                existing_fps.add(fp)

            except Exception as e:
                errors += 1
                print(f"  Row error: {e}")

        if papers_to_add:
            async with AsyncSessionLocal() as db:
                db.add_all(papers_to_add)
                await db.commit()
            imported += len(papers_to_add)

        done = min(batch_start + BATCH_SIZE, total)
        print(f"  Progress: {done}/{total} processed — imported {imported}, skipped {skipped}", end="\r")

    conn.close()
    print(f"\n\nDone — imported {imported}, skipped {skipped} (duplicates), errors {errors}")
    print(f"Papers inserted with status='{status}'.")
    if status == "pending_embed":
        print("Run POST /admin/papers/trigger-embed (or python -m app.workers.runner) to generate embeddings.")


async def main():
    parser = argparse.ArgumentParser(description="Migrate ogso.db SQLite papers → Postgres")
    parser.add_argument("--db", required=True, help="Path to ogso.db SQLite file")
    parser.add_argument("--table", default="papers", help="SQLite table name (default: papers)")
    parser.add_argument("--limit", type=int, default=None, help="Max rows to process (for testing)")
    parser.add_argument("--dry-run", action="store_true", help="Print schema and row count without inserting")
    parser.add_argument("--status", default="pending_embed",
                        choices=["pending_embed", "embedded", "published"],
                        help="Status to assign imported papers (default: pending_embed)")
    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"ERROR: File not found: {args.db}")
        sys.exit(1)

    if not args.dry_run:
        await init_db()
    await migrate(args.db, args.limit, args.dry_run, args.status, args.table)


if __name__ == "__main__":
    asyncio.run(main())
