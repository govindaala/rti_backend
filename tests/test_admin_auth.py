# Repository path: rti_backend/tests/test_admin_auth.py
"""Security regression tests for administrator browser sessions."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core import admin_auth


def configured_settings():
    return SimpleNamespace(
        admin_id="test-admin",
        admin_pass="correct horse battery staple",
        admin_session_secret="test-only-signing-secret-with-more-than-32-bytes",
    )


def request_with_cookie(token: str, method: str = "GET") -> Request:
    headers = [(b"cookie", f"{admin_auth.COOKIE_NAME}={token}".encode("ascii"))]
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "https",
        "path": "/api/v1/admin/dashboard",
        "raw_path": b"/api/v1/admin/dashboard",
        "query_string": b"",
        "headers": headers,
        "server": ("testserver", 443),
        "client": ("testclient", 12345),
    }
    return Request(scope)


def test_signed_session_round_trip(monkeypatch):
    monkeypatch.setattr(admin_auth, "settings", configured_settings())
    token, csrf = admin_auth.create_session()

    session = admin_auth.read_session(request_with_cookie(token))

    assert session["sub"] == "test-admin"
    assert session["csrf"] == csrf


def test_tampered_cookie_is_rejected(monkeypatch):
    monkeypatch.setattr(admin_auth, "settings", configured_settings())
    token, _ = admin_auth.create_session()
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")

    with pytest.raises(HTTPException) as error:
        admin_auth.read_session(request_with_cookie(tampered))

    assert error.value.status_code == 401


def test_password_rotation_invalidates_existing_session(monkeypatch):
    config = configured_settings()
    monkeypatch.setattr(admin_auth, "settings", config)
    token, _ = admin_auth.create_session()
    config.admin_pass = "new-password-after-rotation"

    with pytest.raises(HTTPException) as error:
        admin_auth.read_session(request_with_cookie(token))

    assert error.value.status_code == 401


def test_state_changing_request_requires_matching_csrf(monkeypatch):
    monkeypatch.setattr(admin_auth, "settings", configured_settings())
    token, csrf = admin_auth.create_session()
    request = request_with_cookie(token, method="POST")

    with pytest.raises(HTTPException) as error:
        admin_auth.require_admin(request, "wrong-csrf-token")
    assert error.value.status_code == 403

    assert admin_auth.require_admin(request, csrf)["sub"] == "test-admin"


def test_short_signing_secret_fails_closed(monkeypatch):
    config = configured_settings()
    config.admin_session_secret = "too-short"
    monkeypatch.setattr(admin_auth, "settings", config)

    with pytest.raises(HTTPException) as error:
        admin_auth.create_session()

    assert error.value.status_code == 503
