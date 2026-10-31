# Repository path: rti_backend/app/core/admin_auth.py
"""Signed, short-lived administrator browser sessions (stdlib only)."""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from fastapi import HTTPException, Request, status

from app.core.config import settings

COOKIE_NAME = "rti_admin_session"
SESSION_TTL_SECONDS = 8 * 60 * 60
MINIMUM_SIGNING_SECRET_BYTES = 32


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.b64decode(padded, altchars=b"-_", validate=True)


def _password_fingerprint(secret: str, password: str) -> str:
    return hmac.new(secret.encode("utf-8"), password.encode("utf-8"), hashlib.sha256).hexdigest()


def create_session() -> tuple[str, str]:
    """Create a signed cookie and its separate CSRF token."""
    secret = settings.admin_session_secret
    if not secret or len(secret.encode("utf-8")) < MINIMUM_SIGNING_SECRET_BYTES:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin session signing secret is not configured (minimum 32 bytes)",
        )
    if not settings.admin_id or not settings.admin_pass:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin credentials are not configured",
        )

    csrf = secrets.token_urlsafe(32)
    payload = {
        "sub": settings.admin_id,
        "exp": int(time.time()) + SESSION_TTL_SECONDS,
        "csrf": csrf,
        "auth": _password_fingerprint(secret, settings.admin_pass),
    }
    body = _b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return body + "." + _b64encode(signature), csrf


def read_session(request: Request) -> dict[str, Any]:
    """Validate signature, expiry, configured identity and password version."""
    secret = settings.admin_session_secret
    token = request.cookies.get(COOKIE_NAME, "")
    try:
        if not secret or len(secret.encode("utf-8")) < MINIMUM_SIGNING_SECRET_BYTES:
            raise ValueError("signing secret unavailable")
        body, supplied_signature = token.split(".", 1)
        expected = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64decode(supplied_signature), expected):
            raise ValueError("invalid signature")

        payload = json.loads(_b64decode(body))
        if not isinstance(payload, dict):
            raise TypeError("invalid payload")
        if (
            payload.get("sub") != settings.admin_id
            or int(payload.get("exp", 0)) <= int(time.time())
            or not isinstance(payload.get("csrf"), str)
            or not hmac.compare_digest(
                str(payload.get("auth", "")),
                _password_fingerprint(secret, settings.admin_pass or ""),
            )
        ):
            raise ValueError("expired or invalid session")
        return payload
    except (
        ValueError,
        TypeError,
        KeyError,
        UnicodeError,
        binascii.Error,
        json.JSONDecodeError,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrator login required",
        ) from None


def require_admin(request: Request, csrf_token: str | None = None) -> dict[str, Any]:
    """Require a valid session and CSRF token for every state-changing request."""
    session = read_session(request)
    if request.method not in {"GET", "HEAD", "OPTIONS"} and (
        not csrf_token
        or not hmac.compare_digest(csrf_token, session["csrf"])
    ):
        raise HTTPException(status_code=403, detail="Invalid or missing CSRF token")
    return session
