"""
Government Scheme Eligibility API

FastAPI application entry point with lifespan management,
middleware configuration, and router registration.
"""

import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.config import get_settings
from app.core.api_key import require_private_api_key
from app.core.rate_limit import limiter
from app.database import engine
from app.routers import auth as auth_router
from app.routers import eligibility as eligibility_router
from app.routers import admin as admin_router
from app.routers import profile as profile_router
from app.services.memory_redis import MemoryRedis

settings = get_settings()

# Configure loguru — use default for request_id so non-request logs don't crash
logger.configure(extra={"request_id": "system"})

try:
    Path("logs").mkdir(exist_ok=True)
    logger.add(
        "logs/api_{time}.log",
        rotation="10 MB",
        retention="7 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {extra[request_id]} | {message}",
    )
except OSError as exc:
    logger.warning(f"File logging disabled: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events for DB and cache connections.
    """
    # Startup
    if settings.REDIS_URL.startswith("memory://"):
        app.state.redis = MemoryRedis()
        logger.info("Using in-memory cache")
    else:
        import redis.asyncio as aioredis

        app.state.redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    logger.info("Application started")

    yield

    # Shutdown
    await app.state.redis.close()
    await engine.dispose()
    logger.info("Application stopped")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "A developer-friendly API that takes user profile inputs "
        "(age, income, caste, state, gender, occupation, disability status) "
        "and returns all government schemes they qualify for — with application "
        "links, deadlines, and benefit details.\n\n"
        "**Base URL:** `/api/v1`\n\n"
        "**Authentication:** Bearer JWT token in Authorization header"
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    contact={
        "name": "API Support",
        "email": "support@schemesapi.gov.in",
    },
    license_info={
        "name": "MIT",
    },
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """
    Middleware that adds a unique request ID to every request and logs
    request/response details including timing.
    """
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id

    start_time = time.time()

    with logger.contextualize(request_id=request_id):
        logger.info(f"{request.method} {request.url.path}")

        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(f"Unhandled error: {exc}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Internal server error",
                    "request_id": request_id,
                },
            )

        duration_ms = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(f"{response.status_code} in {duration_ms}ms")

    return response


# Global exception handler for structured error responses
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return structured JSON for any unhandled exception."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
        },
    )


# Register routers under /api/v1
private_api_dependencies = [Depends(require_private_api_key)]
app.include_router(
    auth_router.router,
    prefix=settings.API_V1_PREFIX,
    dependencies=private_api_dependencies,
)
app.include_router(
    eligibility_router.router,
    prefix=settings.API_V1_PREFIX,
    dependencies=private_api_dependencies,
)
app.include_router(
    profile_router.router,
    prefix=settings.API_V1_PREFIX,
    dependencies=private_api_dependencies,
)
app.include_router(
    admin_router.router,
    prefix=settings.API_V1_PREFIX,
    dependencies=private_api_dependencies,
)


@app.get("/health", tags=["Health"])
async def health_check(request: Request):
    """
    Health check endpoint.
    Verifies API, database, and cache connectivity.
    """
    from app.services.cache_service import CacheService

    cache_ok = False
    try:
        cache = CacheService(request.app.state.redis)
        cache_ok = await cache.health_check()
    except Exception:
        pass

    db_ok = False
    try:
        from sqlalchemy import text
        from app.database import async_session
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass

    overall = "ok" if (cache_ok and db_ok) else "degraded"
    cache_backend = "memory" if settings.REDIS_URL.startswith("memory://") else "redis"

    return {
        "status": overall,
        "database": "connected" if db_ok else "disconnected",
        "cache": "connected" if cache_ok else "disconnected",
        "cache_backend": cache_backend,
    }
