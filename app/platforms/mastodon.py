"""Mastodon: POST /api/v1/statuses (user token, write:statuses scope)."""
from __future__ import annotations

from uuid import uuid4
import httpx

from app.config import Settings
from app.platforms.base import PlatformError, expect_json, require_https_base, successful
from app.schemas import PostingResult

NAME = "Mastodon"


async def publish(message: str, client: httpx.AsyncClient, settings: Settings) -> PostingResult:
    if not (settings.mastodon_base_url and settings.mastodon_token):
        raise PlatformError("Missing MASTODON_BASE_URL or MASTODON_TOKEN")
    base = require_https_base(settings.mastodon_base_url)
    response = await client.post(
        f"{base}/api/v1/statuses",
        headers={"Authorization": f"Bearer {settings.mastodon_token}", "Idempotency-Key": str(uuid4())},
        data={"status": message, "visibility": "public"},
    )
    payload = await expect_json(response)
    post_url = payload.get("url") or payload.get("uri")
    if not post_url or not payload.get("id"):
        raise PlatformError("Mastodon returned no post identifier/URL")
    return successful(NAME, post_url, payload.get("visibility") == "public")
