"""Signed, short-lived administrator browser sessions (stdlib only)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import HTTPException, Request, status

from app.core.config import settings

COOKIE_NAME = "rti_admin_session"
SESSION_TTL_SECONDS = 8 * 60 * 60


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_session() -> tuple[str, str]:
    secret = settings.admin_session_secret
    if not secret or len(secret.encode("utf-8")) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin session signing secret is not configured (minimum 32 bytes)",
        )
    csrf = secrets.token_urlsafe(32)
    payload = json.dumps(
        {"sub": settings.admin_id, "exp": int(time.time()) + SESSION_TTL_SECONDS, "csrf": csrf,\n         "auth": hmac.new(secret.encode("utf-8"), (settings.admin_pass or "").encode("utf-8"), hashlib.sha256).hexdigest()},
        separators=(",", ":"),
    ).encode("utf-8")
    body = _b64encode(payload)
    signature = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return body + "." + _b64encode(signature), csrf


def read_session(request: Request) -> dict[str, str]:
    secret = settings.admin_session_secret
    token = request.cookies.get(COOKIE_NAME, "")
    try:
        body, supplied_signature = token.split(".", 1)
        expected = hmac.new(
            (secret or "").encode("utf-8"), body.encode("ascii"), hashlib.sha256
        ).digest()
        if not secret or not hmac.compare_digest(_b64decode(supplied_signature), expected):
            raise ValueError("invalid signature")
        payload = json.loads(_b64decode(body))
        if (
            payload.get("sub") != settings.admin_id
            or int(payload.get("exp", 0)) <= int(time.time())
            or not isinstance(payload.get("csrf"), str)\n            or not hmac.compare_digest(\n                str(payload.get("auth", "")),\n                hmac.new(\n                    (secret or "").encode("utf-8"),\n                    (settings.admin_pass or "").encode("utf-8"),\n                    hashlib.sha256,\n                ).hexdigest(),\n            )
        ):
            raise ValueError("expired or invalid session")
        return payload
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrator login required",
        ) from None


def require_admin(request: Request, csrf_token: str | None = None) -> dict[str, str]:
    session = read_session(request)
    if request.method not in {"GET", "HEAD", "OPTIONS"} and (
        not csrf_token or not hmac.compare_digest(csrf_token, session["csrf"])
    ):
        raise HTTPException(status_code=403, detail="Invalid or missing CSRF token")
    return session
