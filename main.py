import os
import time
import logging
import logging.config
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.routers.facebook import auth, ads, pages
from app.routers.brands import auth as brands_auth
from app.routers.subscriptions import router as subscriptions_router
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
app.include_router(brands_auth.router)
app.include_router(subscriptions_router.router)


@app.on_event("startup")
async def on_startup():
    """Run Alembic migrations and seed default subscription plans."""
    from alembic.config import Config
    from alembic import command
    from app.database import get_session_local, get_engine, Base
    from app.repositories.subscription import SubscriptionRepository
    import app.models.brand         # noqa: ensure ORM model is registered
    import app.models.subscription  # noqa: ensure ORM model is registered

    # Safety net: create any missing tables (handles fresh DBs and migration gaps)
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    # Run Alembic migrations (idempotent — won't re-apply already-applied revisions)
    try:
        logger.info("Running Alembic migrations…")
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations complete")
    except Exception as exc:
        logger.warning("Migration step skipped (schema may already be up to date): %s", exc)

    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        logger.info("Seeding default subscription plans…")
        SubscriptionRepository(db).seed_defaults()
        logger.info("Subscription seed complete")
    finally:
        db.close()

    logger.info("Server ready — session_storage=%s", settings.session_storage)


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
        "platforms": ["Facebook", "Instagram (coming soon)", "TikTok (coming soon)"],
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
    