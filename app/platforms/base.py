"""Shared connector response mapping and safe error formatting."""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx

from app.schemas import PostingResult


class PlatformError(Exception):
    pass


def safe_api_error(response: httpx.Response) -> str:
    # Never echo arbitrary response bodies: they can contain auth data or PII.
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        code = payload.get("code") or payload.get("error")
        if isinstance(code, str) and len(code) < 75 and all(c.isalnum() or c in "_- ." for c in code):
            return f"HTTP {response.status_code}: {code}"
    return f"HTTP {response.status_code} from provider"


def require_https_base(url: str) -> str:
    """Only administrator-configured HTTPS URLs may receive credentials."""
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        raise PlatformError("Invalid configured service URL: HTTPS host required")
    return url.rstrip("/")


def successful(name: str, url: str | None, public_access: bool) -> PostingResult:
    now = datetime.now(timezone.utc)
    return PostingResult(
        platform=name, status="success", posted_url=url,
        public_access=public_access,
        date=now.date().isoformat(), time=now.time().replace(microsecond=0).isoformat() + "Z",
        error=None,
    )


def failed(name: str, reason: str) -> PostingResult:
    return PostingResult(platform=name, status="failed", error=reason[:180])


async def expect_json(response: httpx.Response) -> dict:
    if not (200 <= response.status_code < 300):
        raise PlatformError(safe_api_error(response))
    try:
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("not an object")
        return data
    except ValueError as exc:
        raise PlatformError("Provider returned invalid JSON") from exc
