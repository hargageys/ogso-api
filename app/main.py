import time
import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db, AsyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)


async def seed_admin():
    from sqlalchemy import select
    from app.models.user import User, UserRole, UserStatus
    from app.core.security import hash_password

    async with AsyncSessionLocal() as db:
        existing = (await db.execute(select(User).where(User.role == UserRole.admin))).scalar_one_or_none()
        if existing:
            return
        admin = User(
            id=uuid.uuid4(),
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            role=UserRole.admin,
            status=UserStatus.active,
            full_name="Ogso Admin",
            email_verified=True,
        )
        db.add(admin)
        await db.commit()
        logger.info(f"Admin user seeded: {settings.admin_email}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_admin()
    logger.info("Ogso backend ready")
    yield


app = FastAPI(
    title="Ogso API",
    version=settings.version,
    description="Somali Research Intelligence Platform",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REQUEST LOGGING ───────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start) * 1000
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({duration:.1f}ms)")
    return response


# ── GLOBAL EXCEPTION HANDLER ──────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred", "code": "INTERNAL_ERROR"},
    )


# ── HEALTH CHECK ──────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health():
    from sqlalchemy import text
    from app.database import engine

    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    return {
        "status": "ok" if db_ok else "degraded",
        "db": "ok" if db_ok else "error",
        "version": settings.version,
    }


# ── ROUTERS ───────────────────────────────────────────────────
from app.routers import auth, admin, papers, search, authors, organisations, clusters, submissions, briefs, stats  # noqa: E402

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(papers.router)
app.include_router(search.router)
app.include_router(authors.router)
app.include_router(organisations.router)
app.include_router(clusters.router)
app.include_router(submissions.router)
app.include_router(briefs.router)
app.include_router(stats.router)
