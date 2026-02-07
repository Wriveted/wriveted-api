"""CSRF protection for chat endpoints using double-submit cookie pattern."""

import secrets
from typing import Optional

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from structlog import get_logger

from app.config import get_settings

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
                    httponly=False,  # Must be readable by JavaScript for double-submit pattern
                    samesite="none",  # Allow cross-origin cookie sending
                    secure=True,  # Required with SameSite=none
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
    """Validate CSRF token using double-submit cookie pattern with cross-origin fallback.

    The X-CSRF-Token header is always required. When the csrf_token cookie is
    also present (same-origin), both must match. When the cookie is absent
    (cross-origin — SameSite prevents it), the header alone is accepted.

    This is secure because CORS restricts which origins can read the token
    from the /chat/start response, so only authorized frontends can obtain it.
    """
    settings = get_settings()

    # Get token from header (always required)
    header_token = request.headers.get("X-CSRF-Token")
    if not header_token:
        logger.warning(
            "CSRF validation failed: No token in header", path=request.url.path
        )
        raise HTTPException(status_code=403, detail="CSRF token missing in header")

    # In development mode, skip cookie validation entirely
    if settings.CSRF_SKIP_COOKIE_VALIDATION:
        logger.debug(
            "CSRF validation (header-only mode) successful", path=request.url.path
        )
        return

    # When cookie is present (same-origin), verify it matches the header
    cookie_token = request.cookies.get("csrf_token")
    if cookie_token:
        if not secrets.compare_digest(cookie_token, header_token):
            logger.warning(
                "CSRF validation failed: Token mismatch",
                path=request.url.path,
            )
            raise HTTPException(status_code=403, detail="CSRF token mismatch")
        logger.debug(
            "CSRF validation successful (double-submit)", path=request.url.path
        )
    else:
        # Cross-origin: cookie absent due to SameSite restrictions.
        # Header-only is sufficient — CORS prevents unauthorized origins
        # from reading the token returned by /chat/start.
        logger.debug(
            "CSRF validation successful (header-only, cross-origin)",
            path=request.url.path,
        )


def set_secure_session_cookie(
    response: Response, name: str, value: str, max_age: int = 3600, debug: bool = False
):
    """Set a secure session cookie with proper security attributes.

    Production: SameSite=none allows cross-origin cookie sending (requires Secure).
    Debug: SameSite=lax for cross-port local development without HTTPS.
    """
    response.set_cookie(
        name,
        value,
        httponly=True,
        samesite="lax" if debug else "none",
        secure=not debug,
        max_age=max_age,
    )
