"""Bluesky AT Protocol: createSession -> createRecord, with a clickable link facet."""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote
import httpx

from app.config import Settings
from app.platforms.base import PlatformError, expect_json, successful
from app.schemas import PostingResult, extract_cta_url

NAME = "Bluesky"
SERVER = "https://bsky.social/xrpc"


def link_facet(message: str) -> dict:
    url = extract_cta_url(message)
    start = message.index(url)
    return {
        "index": {
            "byteStart": len(message[:start].encode("utf-8")),
            "byteEnd": len(message[: start + len(url)].encode("utf-8")),
        },
        "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}],
    }


async def publish(message: str, client: httpx.AsyncClient, settings: Settings) -> PostingResult:
    if not (settings.bluesky_handle and settings.bluesky_app_password):
        raise PlatformError("Missing BLUESKY_HANDLE or BLUESKY_APP_PASSWORD")
    session_r = await client.post(
        f"{SERVER}/com.atproto.server.createSession",
        json={"identifier": settings.bluesky_handle, "password": settings.bluesky_app_password},
    )
    session = await expect_json(session_r)
    jwt, did = session.get("accessJwt"), session.get("did")
    if not jwt or not did:
        raise PlatformError("Bluesky session response missing access token or DID")
    record = {
        "$type": "app.bsky.feed.post", "text": message,
        "createdAt": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "facets": [link_facet(message)],
    }
    post_r = await client.post(
        f"{SERVER}/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {jwt}"},
        json={"repo": did, "collection": "app.bsky.feed.post", "record": record},
    )
    post = await expect_json(post_r)
    at_uri = post.get("uri", "")
    prefix = f"at://{did}/app.bsky.feed.post/"
    if not at_uri.startswith(prefix) or not post.get("cid"):
        raise PlatformError("Bluesky returned no valid post URI/CID")
    rkey = at_uri[len(prefix):]
    if not rkey or "/" in rkey:
        raise PlatformError("Bluesky returned malformed record key")
    return successful(NAME, f"https://bsky.app/profile/{quote(did, safe=':')}/post/{quote(rkey)}", True)
