"""Private API key dependency."""

import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import get_settings

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="Private API key from your local .env file.",
)


async def require_private_api_key(api_key: str | None = Security(api_key_header)) -> None:
    """Require the private API key for all versioned API endpoints."""
    settings = get_settings()

    if not settings.PRIVATE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PRIVATE_API_KEY is not configured",
        )

    if not api_key or not secrets.compare_digest(api_key, settings.PRIVATE_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
