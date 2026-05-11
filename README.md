# Ogso API — Somali Research Intelligence Platform

FastAPI backend for Ogso: semantic research discovery, researcher profiles, organisation profiles, and AI-generated policy briefs.

## Stack

- **FastAPI** + **uvicorn** (async ASGI)
- **PostgreSQL 16** + **pgvector** (vector similarity search)
- **SQLAlchemy** (async ORM) + **Alembic** (migrations)
- **sentence-transformers** (`all-MiniLM-L6-v2`, 384-dim embeddings)
- **APScheduler** (hourly embedder, weekly clusterer)
- **Anthropic Claude** *(optional — only for AI policy brief generation)*

## Local Setup

### 1. Install PostgreSQL with pgvector

**Ubuntu / Debian:**
```bash
sudo apt install postgresql-16 postgresql-16-pgvector
sudo -u postgres createuser -s $USER
createdb ogso
```

**Mac (Homebrew):**
```bash
brew install postgresql@16 pgvector
createdb ogso
```

### 2. Install Python dependencies

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` — at minimum set:
- `SECRET_KEY` — generate with `python -c "import secrets; print(secrets.token_hex(32))"`
- `ADMIN_EMAIL` and `ADMIN_PASSWORD` — your admin login
- `DATABASE_URL` — defaults to `postgresql+asyncpg://ogso:ogso@localhost:5432/ogso`

### 4. Run migrations

```bash
alembic upgrade head
```

This creates all tables and enables the `pgvector` extension automatically.

### 5. Start the API

```bash
uvicorn app.main:app --reload
```

The admin user is seeded automatically on first startup.

API: `http://localhost:8000`  
Docs: `http://localhost:8000/docs`

### 6. (Optional) Start the background worker

In a separate terminal:

```bash
python -m app.workers.runner
```

This runs the **embedder** (hourly) and **clusterer** (weekly) on a schedule.

---

## Importing Your Existing Papers (ogso.db)

If you have a SQLite database from the ogso4.py scraper, import it directly:

```bash
# Dry run — detects schema and shows row count without inserting
python scripts/migrate_sqlite.py --db ogso.db --dry-run

# Test with first 10 rows
python scripts/migrate_sqlite.py --db ogso.db --limit 10

# Full import (papers land as 'pending_embed')
python scripts/migrate_sqlite.py --db ogso.db

# Import and mark as published immediately (skips embed step)
python scripts/migrate_sqlite.py --db ogso.db --status published

# If your papers table has a different name
python scripts/migrate_sqlite.py --db ogso.db --table research_papers
```

After importing, trigger embedding:
```bash
# Via API (requires admin login first)
curl -X POST http://localhost:8000/admin/papers/trigger-embed \
  -H "Authorization: Bearer <your-token>"

# Or run the worker directly
python -c "import asyncio; from app.workers.embedder import run_embedder; asyncio.run(run_embedder())"
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | asyncpg connection string |
| `SECRET_KEY` | Yes | JWT signing secret |
| `ADMIN_EMAIL` | Yes | Seeded admin email |
| `ADMIN_PASSWORD` | Yes | Seeded admin password |
| `ALLOWED_ORIGINS` | No | Comma-separated CORS origins (default: localhost:3000) |
| `ANTHROPIC_API_KEY` | No | Only for `POST /search/policy` brief generation |
| `ENVIRONMENT` | No | `development` or `production` |
| `VERSION` | No | App version string |

---

## Key Endpoints

### Auth
| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | — | Register (status=pending, awaits admin approval) |
| `POST` | `/auth/login` | — | Login → access token + refresh cookie |
| `POST` | `/auth/refresh` | Cookie | Refresh access token |
| `POST` | `/auth/logout` | — | Clear refresh cookie |
| `GET` | `/auth/me` | Token | Current user |

### Admin (`role=admin` required)
| Method | Path | Description |
|---|---|---|
| `GET` | `/admin/users/pending` | Users awaiting approval |
| `POST` | `/admin/users/{id}/approve` | Approve user |
| `POST` | `/admin/papers/import` | Bulk import from scraper JSON |
| `POST` | `/admin/papers/trigger-embed` | Run embedder in background |
| `POST` | `/admin/papers/trigger-cluster` | Run clusterer in background |
| `POST` | `/admin/submissions/{id}/approve` | Approve submission → creates paper |
| `GET` | `/admin/stats` | Platform statistics |
| `GET` | `/admin/audit` | Audit log |

### Papers (public)
| Method | Path | Description |
|---|---|---|
| `GET` | `/papers` | List with filters (category, year, source, etc.) |
| `GET` | `/papers/{id}` | Paper detail |
| `GET` | `/papers/{id}/similar` | pgvector cosine similarity (top 10) |

### Search
| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/search?q=...` | — | Full-text keyword search |
| `POST` | `/search/semantic` | — | Semantic vector search |
| `POST` | `/search/policy` | Token | Queue AI policy brief (needs ANTHROPIC_API_KEY) |

All other endpoints documented at `/docs`.

---

## Scraper Import Format

`POST /admin/papers/import` accepts the `ogso4.py` scraper output format:

```json
[
  {
    "id": "openalex_W123",
    "title": "Paper title",
    "authors": ["Author One", "Author Two"],
    "year": "2023",
    "abstract": "Abstract text...",
    "source": "OpenAlex",
    "url": "https://doi.org/...",
    "institution": "University name",
    "category": "Health",
    "doc_type": "article",
    "somali_author": true,
    "citations": 45
  }
]
```

Deduplication by DOI and title fingerprint. Returns `{"imported": N, "skipped": N, "total": N}`.

---

## Project Structure

```
app/
  main.py          # FastAPI app, middleware, lifespan, admin seed
  config.py        # Settings (pydantic-settings, reads .env)
  database.py      # SQLAlchemy async engine + Base
  dependencies.py  # JWT auth dependencies
  models/          # SQLAlchemy ORM models (8 models)
  schemas/         # Pydantic v2 schemas
  routers/         # FastAPI routers (10 routers)
  workers/         # Background jobs (embedder, clusterer, brief_generator, runner)
  core/            # Security, embeddings, email stubs
alembic/           # Database migrations
scripts/
  migrate_sqlite.py  # Import from ogso.db → Postgres
```
