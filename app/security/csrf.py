"""CSRF protection for chat endpoints using double-submit cookie pattern."""

import secrets
from typing import Optional

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from structlog import get_logger

logger = get_logger()


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """Double-submit cookie CSRF protection middleware."""

    def __init__(self, app, exempt_paths: Optional[list] = None):
        super().__init__(app)
        self.exempt_paths = exempt_paths or []

    async def dispatch(self, request: Request, call_next):
        # Skip CSRF protection for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)

        # Skip for safe methods (GET, HEAD, OPTIONS)
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            response = await call_next(request)
            # Set CSRF token for future requests if not present
            if not request.cookies.get("csrf_token"):
                csrf_token = generate_csrf_token()
                response.set_cookie(
                    "csrf_token",
                    csrf_token,
                    httponly=True,
                    samesite="strict",
                    secure=True,  # Requires HTTPS in production
                    max_age=3600 * 24,  # 24 hours
                )
            return response

        # For state-changing methods, validate CSRF token
        if request.url.path.endswith("/interact"):
            validate_csrf_token(request)

        return await call_next(request)


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(32)


def validate_csrf_token(request: Request):
    """Validate CSRF token using double-submit cookie pattern."""

    # Get token from cookie
    cookie_token = request.cookies.get("csrf_token")
    if not cookie_token:
        logger.warning(
            "CSRF validation failed: No token in cookie", path=request.url.path
        )
        raise HTTPException(status_code=403, detail="CSRF token missing in cookie")

    # Get token from header
    header_token = request.headers.get("X-CSRF-Token")
    if not header_token:
        logger.warning(
            "CSRF validation failed: No token in header", path=request.url.path
        )
        raise HTTPException(status_code=403, detail="CSRF token missing in header")

    # Compare tokens
    if not secrets.compare_digest(cookie_token, header_token):
        logger.warning(
            "CSRF validation failed: Token mismatch",
            path=request.url.path,
            has_cookie=bool(cookie_token),
            has_header=bool(header_token),
        )
        raise HTTPException(status_code=403, detail="CSRF token mismatch")

    logger.debug("CSRF validation successful", path=request.url.path)


def set_secure_session_cookie(
    response: Response, name: str, value: str, max_age: int = 3600, debug: bool = False
):
    """Set a secure session cookie with proper security attributes."""
    response.set_cookie(
        name,
        value,
        httponly=True,
        samesite="strict",
        secure=not debug,  # Only secure in production (non-debug)
        max_age=max_age,
    )
