"""Run independent platform integrations concurrently; isolate each failure."""
from __future__ import annotations

import asyncio
import httpx

from app.config import Settings
from app.platforms import bluesky, discord, mastodon, telegram, wordpress
from app.platforms.base import PlatformError, failed
from app.schemas import PostingRequest, PostingResponse, PostingResult

PLATFORMS = (mastodon, bluesky, telegram, discord, wordpress)


async def publish_to_one(platform, message: str, client: httpx.AsyncClient, settings: Settings) -> PostingResult:
    if not settings.posting_enabled:
        return failed(platform.NAME, "Publishing disabled: set POSTING_ENABLED=true after configuring authorized accounts")
    try:
        return await platform.publish(message, client, settings)
    except PlatformError as exc:
        return failed(platform.NAME, str(exc))
    except httpx.TimeoutException:
        return failed(platform.NAME, "Provider request timed out")
    except httpx.HTTPError:
        return failed(platform.NAME, "Network error contacting provider")
    except Exception:
        # Maintain per-platform independence without exposing credentials/tracebacks.
        return failed(platform.NAME, "Unexpected integration error (check server logs)")


async def publish_all(request: PostingRequest, client: httpx.AsyncClient, settings: Settings) -> PostingResponse:
    results = await asyncio.gather(*(publish_to_one(p, request.message, client, settings) for p in PLATFORMS))
    return PostingResponse(success=all(p.status == "success" for p in results), results=list(results))
