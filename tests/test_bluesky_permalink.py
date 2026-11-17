"""Regression test for human-readable Bluesky post links.
Network free; does not publish or use actual credentials.
"""
import json
import httpx
import pytest

from app.config import Settings
from app.platforms.bluesky import publish


@pytest.mark.asyncio
async def test_bluesky_post_url_has_unescaped_did_colons():
    did = "did:plc:3645agszzrvhcbqlqnne2cbg"
    rkey = "3n2jj7oov4k2e"

    def fake_provider(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("com.atproto.server.createSession"):
            return httpx.Response(200, json={"accessJwt": "mock-access-jwt", "did": did})
        if request.url.path.endswith("com.atproto.repo.createRecord"):
            body = json.loads(request.content)
            assert body["repo"] == did
            return httpx.Response(200, json={
                "uri": f"at://{did}/app.bsky.feed.post/{rkey}",
                "cid": "bafy-test",
            })
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(fake_provider)) as client:
        result = await publish(
            "Test https://example.com",
            client,
            Settings(bluesky_handle="demo.bsky.social", bluesky_app_password="fake-not-real"),
        )
    assert result.status == "success"
    assert result.posted_url == f"https://bsky.app/profile/{did}/post/{rkey}"
    assert "%3A" not in result.posted_url
