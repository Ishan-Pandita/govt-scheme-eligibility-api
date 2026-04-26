"""
Government Scheme Eligibility API

FastAPI application entry point with lifespan management.
"""

from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events for DB and Redis connections.
    """
    # Startup
    app.state.redis = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )

    yield

    # Shutdown
    await app.state.redis.close()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "A developer-friendly API that takes user profile inputs "
        "(age, income, caste, state, gender, occupation, disability status) "
        "and returns all government schemes they qualify for — with application "
        "links, deadlines, and benefit details."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Returns API status. Will include DB and Redis checks in Phase 11.
    """
    return {"status": "ok"}
