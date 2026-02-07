from __future__ import annotations

from typing import Dict, Optional

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.config import get_settings
from app.security.csrf import generate_csrf_token, validate_csrf_token


def _make_request(
    *,
    headers: Optional[Dict[str, str]] = None,
    cookies: Optional[Dict[str, str]] = None,
    path: str = "/v1/chat/sessions/test/interact",
    method: str = "POST",
) -> Request:
    header_list = []
    if headers:
        header_list.extend(
            [(key.lower().encode(), value.encode()) for key, value in headers.items()]
        )
    if cookies:
        cookie_value = "; ".join(f"{key}={value}" for key, value in cookies.items())
        header_list.append((b"cookie", cookie_value.encode()))

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": header_list,
    }
    return Request(scope)


def _set_csrf_skip(monkeypatch, value: bool) -> None:
    monkeypatch.setenv("CSRF_SKIP_COOKIE_VALIDATION", "true" if value else "false")
    get_settings.cache_clear()


def test_generate_csrf_token_unique():
    token_a = generate_csrf_token()
    token_b = generate_csrf_token()
    assert token_a
    assert token_b
    assert token_a != token_b


def test_validate_csrf_token_missing_header(monkeypatch):
    _set_csrf_skip(monkeypatch, False)
    request = _make_request(headers={}, cookies={"csrf_token": "abc"})

    with pytest.raises(HTTPException) as exc:
        validate_csrf_token(request)

    assert exc.value.status_code == 403
    assert "header" in exc.value.detail


def test_validate_csrf_token_missing_cookie_accepts_header_only(monkeypatch):
    """When cookie is absent (cross-origin), header-only validation succeeds."""
    _set_csrf_skip(monkeypatch, False)
    request = _make_request(headers={"X-CSRF-Token": "abc"})

    # Should not raise — header-only is accepted for cross-origin scenarios
    validate_csrf_token(request)


def test_validate_csrf_token_mismatch(monkeypatch):
    _set_csrf_skip(monkeypatch, False)
    request = _make_request(
        headers={"X-CSRF-Token": "abc"}, cookies={"csrf_token": "different"}
    )

    with pytest.raises(HTTPException) as exc:
        validate_csrf_token(request)

    assert exc.value.status_code == 403
    assert "mismatch" in exc.value.detail


def test_validate_csrf_token_success(monkeypatch):
    _set_csrf_skip(monkeypatch, False)
    request = _make_request(
        headers={"X-CSRF-Token": "abc"}, cookies={"csrf_token": "abc"}
    )

    validate_csrf_token(request)


def test_validate_csrf_token_header_only_mode(monkeypatch):
    _set_csrf_skip(monkeypatch, True)
    request = _make_request(headers={"X-CSRF-Token": "abc"})

    validate_csrf_token(request)
