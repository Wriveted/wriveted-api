"""CSRF protection dependencies for FastAPI endpoints."""

import os
from fastapi import Depends, HTTPException, Request
from structlog import get_logger

from app.security.csrf import validate_csrf_token

logger = get_logger()


async def require_csrf_token(request: Request):
    """Dependency that validates CSRF token for protected endpoints."""
    try:
        validate_csrf_token(request)
        return True
    except HTTPException:
        # Re-raise the HTTPException from validate_csrf_token
        raise
    except Exception as e:
        logger.error("Unexpected error during CSRF validation", error=str(e))
        raise HTTPException(status_code=500, detail="CSRF validation error")


async def require_csrf_token_always(request: Request):
    """Dependency that always validates CSRF token, ignoring test environment settings."""
    try:
        validate_csrf_token(request)
        return True
    except HTTPException:
        # Re-raise the HTTPException from validate_csrf_token
        raise
    except Exception as e:
        logger.error("Unexpected error during CSRF validation", error=str(e))
        raise HTTPException(status_code=500, detail="CSRF validation error")


# Dependency for endpoints that need CSRF protection
CSRFProtected = Depends(require_csrf_token)

# Dependency for endpoints that always need CSRF protection (for testing)
CSRFProtectedAlways = Depends(require_csrf_token_always)
