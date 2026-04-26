import os
import time
import logging
import logging.config
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.routers.facebook import auth, ads, pages
from app.routers.instagram import auth as instagram_auth
from app.routers.instagram import accounts as instagram_accounts
from app.routers.instagram import content as instagram_content
from app.routers.instagram import insights as instagram_insights
from app.routers.tiktok import auth as tiktok_auth
from app.routers.tiktok import content as tiktok_content
from app.routers.brands import auth as brands_auth
from app.routers.subscriptions import router as subscriptions_router
from app.routers.content import feed as content_feed
from app.routers.admin import router as admin_router
from app.routers.organizations import router as organizations_router
from app.routers.competitors import router as competitors_router
from app.routers.usage import router as usage_router
from app.config import get_settings

settings = get_settings()

# ── Logging setup ─────────────────────────────────────────────────────────────

logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
    "loggers": {
        "app": {"level": "DEBUG", "propagate": True},
        "uvicorn.access": {"level": "WARNING", "propagate": False},  # suppress noisy uvicorn access log
    },
})

logger = logging.getLogger("app")

# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Social Media Sync API",
    description="API for syncing and analyzing social media data (Facebook, Instagram, TikTok) with OAuth authentication",
    version="2.0.0"
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s → %s  (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all exceptions and return JSON"""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal server error: {str(exc)}",
            "type": type(exc).__name__
        }
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(auth.router)
app.include_router(ads.router)
app.include_router(pages.router)
app.include_router(instagram_auth.router)
app.include_router(instagram_accounts.router)
app.include_router(instagram_content.router)
app.include_router(instagram_insights.router)
app.include_router(tiktok_auth.router)
app.include_router(tiktok_content.router)
app.include_router(brands_auth.router)
app.include_router(subscriptions_router.router)
app.include_router(content_feed.router)
app.include_router(admin_router.router)
app.include_router(organizations_router.router)
app.include_router(competitors_router.router)
app.include_router(usage_router.router)


@app.on_event("startup")
async def on_startup():
    """Run Alembic migrations and seed default subscription plans."""
    from alembic.config import Config
    from alembic import command
    from app.database import get_session_local, get_engine, Base
    from app.repositories.subscription import SubscriptionRepository
    import app.models.organization           # noqa: ensure ORM model is registered
    import app.models.organization_membership  # noqa: ensure ORM model is registered
    import app.models.brand              # noqa: ensure ORM model is registered
    import app.models.subscription       # noqa: ensure ORM model is registered
    import app.models.user               # noqa: ensure ORM model is registered
    import app.models.user_brand         # noqa: ensure ORM model is registered
    import app.models.invitation         # noqa: ensure ORM model is registered
    import app.models.instagram_session  # noqa: ensure ORM model is registered
    import app.models.tiktok_session     # noqa: ensure ORM model is registered
    import app.models.competitor                    # noqa: ensure ORM model is registered
    import app.models.competitor_analysis_job       # noqa: ensure ORM model is registered
    import app.models.competitor_analysis_result    # noqa: ensure ORM model is registered
    import app.models.competitor_target              # noqa: ensure ORM model is registered
    import app.models.apify_run                       # noqa: ensure ORM model is registered

    # Safety net: create any missing tables
    # Retry a few times to handle Neon free-tier cold-start (DB suspends when idle)
    import asyncio as _asyncio
    engine = get_engine()
    for _attempt in range(5):
        try:
            Base.metadata.create_all(bind=engine)
            break
        except Exception as exc:
            if _attempt < 4:
                logger.warning("DB not ready (attempt %d/5): %s — retrying in 3s…", _attempt + 1, exc)
                await _asyncio.sleep(3)
            else:
                logger.error("Could not connect to database after 5 attempts: %s", exc)
                logger.error("Check DATABASE_URL in .env and ensure the database is reachable.")
                raise

    # Run Alembic migrations - DISABLED (run manually with: alembic upgrade head)
    # try:
    #     logger.info("Running Alembic migrations…")
    #     alembic_cfg = Config("alembic.ini")
    #     alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
    #     command.upgrade(alembic_cfg, "head")
    #     logger.info("Migrations complete")
    # except Exception as exc:
    #     logger.warning("Migration step failed or timed out: %s", exc)
    #     logger.warning("Continuing server startup anyway...")
    logger.info("Skipping automatic migrations - run 'alembic upgrade head' manually if needed")

    # Seed subscription plans
    try:
        db = get_session_local()()
        try:
            SubscriptionRepository(db).seed_defaults()
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Subscription seed skipped: %s", exc)

    # One-time cleanup: remove stale state entries left by the old session_storage design
    try:
        from sqlalchemy import text as _text
        _db = get_session_local()()
        _db.execute(_text(
            "DELETE FROM facebook_sessions WHERE session_id LIKE 'state_%' OR access_token = ''"
        ))
        _db.commit()
        _db.close()
    except Exception as exc:
        logger.warning("Could not clean up stale state entries: %s", exc)

    # Recover orphaned competitor-analysis jobs left running by a previous worker
    # (uvicorn reload kills BackgroundTasks; this lets the user retry them via Refresh).
    try:
        from datetime import datetime, timedelta
        from app.models.competitor_analysis_job import (
            CompetitorAnalysisJobModel,
            JOB_STATUS_FAILED,
            JOB_STATUS_PENDING,
            JOB_STATUS_RUNNING,
        )
        cutoff = datetime.utcnow() - timedelta(seconds=30)
        db = get_session_local()()
        try:
            stuck = (
                db.query(CompetitorAnalysisJobModel)
                .filter(
                    CompetitorAnalysisJobModel.deleted_at.is_(None),
                    CompetitorAnalysisJobModel.status.in_(
                        [JOB_STATUS_PENDING, JOB_STATUS_RUNNING]
                    ),
                    CompetitorAnalysisJobModel.created_at < cutoff,
                )
                .all()
            )
            now = datetime.utcnow()
            for job in stuck:
                job.status = JOB_STATUS_FAILED
                job.error_message = (
                    "Server restarted before this scrape completed. "
                    "Run the scraper again to retry."
                )
                job.finished_at = now
                job.updated_at = now
            if stuck:
                db.commit()
                logger.info("Recovered %d orphaned competitor-analysis job(s)", len(stuck))
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Orphan-job recovery skipped: %s", exc)

    logger.info("Server ready")


@app.get("/")
def dashboard():
    """Serve the main dashboard"""
    dashboard_file = os.path.join(static_dir, "dashboard.html")
    if os.path.exists(dashboard_file):
        return FileResponse(dashboard_file)
    return {"message": "Dashboard not found"}


@app.get("/api")
def api_info():
    """API information"""
    return {
        "message": "Social Media Sync API",
        "version": "2.0.0",
        "platforms": ["Facebook", "Instagram", "TikTok"],
        "endpoints": {
            "docs": "/docs",
            "dashboard": "/",
            "facebook_auth": "/facebook/auth/login"
        },
        "status": "running",
        "session_storage": settings.session_storage
    }


@app.get("/health")
async def health_check():
    db_status = "not_used"
    if settings.session_storage == "postgresql":
        try:
            from app.database import get_engine
            from sqlalchemy import text
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "version": "2.0.0",
        "session_storage": settings.session_storage,
        "database_status": db_status,
        "facebook_configured": bool(settings.facebook_app_id and settings.facebook_app_secret)
    }


@app.get("/config/check")
async def config_check():
    """Check if application is properly configured"""
    return {
        "facebook": {
            "app_id_set": bool(settings.facebook_app_id),
            "app_secret_set": bool(settings.facebook_app_secret),
            "redirect_uri": settings.facebook_redirect_uri,
            "api_version": settings.facebook_api_version
        },
        "deployment": {
            "deployed_url": settings.deployed_url,
            "app_url": settings.app_url,
            "base_url": settings.base_url
        },
        "session_storage": settings.session_storage,
        "ready": bool(settings.facebook_app_id and settings.facebook_app_secret)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    