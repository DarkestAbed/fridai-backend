# app/main.py

import os
import platform
import time

from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from json import JSONEncoder
from loguru import logger
from pendulum import DateTime
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, DatabaseError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from app.db import init_models, enable_sqlite_wal
from app.dependencies import get_db
from app.exceptions import DatabaseExceptionHandler
from app.limiter import limiter
from app.routers import (
    tasks,
    categories,
    tags,
    relationships,
    attachments,
    views,
    notifications,
    config,
)
from app.settings import settings_cache


class CustomJSONEncoder(JSONEncoder):
    """Custom JSON encoder to handle Pendulum DateTime objects."""
    def default(self, o):
        if isinstance(o, DateTime):
            return o.isoformat()
        return super().default(o)


# ── Middleware classes ────────────────────────────────────────────────────────

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "{method} {path} {status} {ms:.0f}ms",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            ms=duration_ms,
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if os.getenv("ENFORCE_HTTPS", "0") == "1":
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains"
            )
        return response


# ── Logging setup ────────────────────────────────────────────────────────────

def _setup_app_logging():
    """Wire loguru into the app (called from lifespan)."""
    try:
        from main import setup_logging
        setup_logging()
    except ImportError:
        pass  # running under tests or without root main.py


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    _setup_app_logging()
    await enable_sqlite_wal()
    await init_models()
    await settings_cache.load()
    logger.info("Application startup complete")
    yield
    logger.info("Application shutdown")


app = FastAPI(
    title="Tasks Platform API",
    version="2.0.0-vibe",
    lifespan=lifespan,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Database exception handlers
app.add_exception_handler(IntegrityError, DatabaseExceptionHandler.integrity_error_handler)     # type: ignore
app.add_exception_handler(DatabaseError, DatabaseExceptionHandler.database_error_handler)       # type: ignore

# ── Middleware stack (last added = outermost = runs first) ────────────────────

# 1. HTTPS redirect (outermost)
if os.getenv("ENFORCE_HTTPS", "0") == "1":
    app.add_middleware(HTTPSRedirectMiddleware)

# 2. Trusted hosts
_allowed_hosts = os.getenv("ALLOWED_HOSTS", "")
if _allowed_hosts:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[h.strip() for h in _allowed_hosts.split(",")],
    )

# 3. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # single-user demo; tighten if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 5. Request logging (innermost)
app.add_middleware(RequestLoggingMiddleware)


# Routers
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(categories.router, prefix="/api/categories", tags=["categories"])
app.include_router(tags.router, prefix="/api/tags", tags=["tags"])
app.include_router(relationships.router, prefix="/api/relationships", tags=["relationships"])
app.include_router(attachments.router, prefix="/api/tasks", tags=["attachments"])
app.include_router(views.router, prefix="/api/views", tags=["views"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(config.router, prefix="/api/config", tags=["config"])


# ── Health endpoints ─────────────────────────────────────────────────────────

@app.get("/")
async def hello():
    return {"msg": "Hello, friend. Hello, friend?"}


@app.get("/health/live")
async def health_live():
    """Liveness probe — is the process alive?"""
    return {"status": "alive"}


@app.get("/health/ready")
async def health_ready(db: AsyncSession = Depends(get_db)):
    """Readiness probe — can it serve requests?"""
    try:
        await db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected",
            "settings_loaded": settings_cache.timezone != "",
        }
    except Exception as e:
        logger.error("Readiness check failed: {err}", err=str(e))
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "error": str(e)},
        )


@app.get("/healthz")
async def healthz(db: AsyncSession = Depends(get_db)):
    """Full health check with system info."""
    checks: dict = {
        "status": "healthy",
        "version": "2.0.0-vibe",
        "checks": {},
    }
    # Database
    try:
        await db.execute(text("SELECT 1"))
        checks["checks"]["database"] = {"status": "up"}
    except Exception as e:
        checks["status"] = "degraded"
        checks["checks"]["database"] = {"status": "down", "error": str(e)}

    # Settings cache
    checks["checks"]["settings"] = {
        "status": "loaded" if settings_cache.timezone else "empty",
        "timezone": settings_cache.timezone,
        "notifications_enabled": settings_cache.notifications_enabled,
    }

    # Platform
    checks["checks"]["platform"] = {
        "python": platform.python_version(),
        "system": platform.system(),
        "machine": platform.machine(),
    }

    if checks["status"] != "healthy":
        return JSONResponse(status_code=503, content=checks)
    return checks
