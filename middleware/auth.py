"""
API Key Authentication Middleware

Provides simple API key authentication for securing the Graphiti API
when exposed to external services like n8n.
"""
import logging
import os
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

# API Key header configuration
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key() -> Optional[str]:
    """Get the configured API key from environment"""
    return os.getenv("API_KEY")


async def verify_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> str:
    """
    Verify the API key from request header.

    If API_KEY environment variable is not set, authentication is disabled
    (useful for local development).

    Parameters
    ----------
    api_key : str, optional
        API key from X-API-Key header

    Returns
    -------
    str
        The verified API key

    Raises
    ------
    HTTPException
        If API key is invalid or missing (when auth is enabled)
    """
    configured_key = get_api_key()

    # If no API key is configured, skip authentication (dev mode)
    if not configured_key:
        logger.warning("API_KEY not configured - authentication disabled")
        return "dev-mode"

    # Validate the provided key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if api_key != configured_key:
        logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key


def require_api_key(api_key: str = Security(verify_api_key)) -> str:
    """Dependency for routes that require authentication"""
    return api_key
