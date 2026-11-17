"""Network-free tests. MockTransport responses are NOT evidence of live publication."""
from __future__ import annotations

import json
import httpx
import pytest
from pydantic import ValidationError

from app.config import Settings
from app.main import app, get_client, get_settings
from app.platforms.bluesky import link_facet
from app.schemas import PostingRequest, extract_cta_url

MESSAGE = "Explore our business platform: https://example.com"


@pytest.mark.parametrize("message", [
    "No link here",
    "Too many links https://example.com and https://another.com",
    "Bad localhost https://localhost:1234/",
    "Bad private IP http://192.168.1.10/path",
    "Bad scheme ftp://example.com",
    "x" * 201 + " https://example.com",
])
def test_invalid_messages(message):
    with pytest.raises((ValidationError, ValueError)):
        PostingRequest(message=message)


def test_url_with_punctuation_and_multibyte_facet():
    msg = "Hello 🌍 https://example.com/x)."
    assert extract_cta_url(msg) == "https://example.com/x"
    facet = link_facet(msg)
    start = facet["index"]["byteStart"]
    end = facet["index"]["byteEnd"]
    assert msg.encode("utf-8")[start:end].decode() == "https://example.com/x"


@pytest.mark.asyncio
async def test_publishing_is_disabled_by_default():
    app.dependency_overrides[get_settings] = lambda: Settings(posting_enabled=False)
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as api:
            res = await api.post("/posting", json={"message": MESSAGE})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is False
        assert len(data["results"]) == 5
        assert all(result["status"] == "failed" for result in data["results"])
        assert all(result["posted_url"] is None for result in data["results"])
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_validation_returns_422_before_any_publication():
    app.dependency_overrides[get_settings] = lambda: Settings(posting_enabled=True)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as api:
            res = await api.post("/posting", json={"message": "https://one.com https://two.com"})
        assert res.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_five_real_api_adapters_against_simulated_provider_responses():
    """Simulate 6 API calls for 5 connectors; NO outside internet calls."""
    calls: list[httpx.Request] = []

    def provider(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.host == "mastodon.social":
            assert request.headers["Authorization"] == "Bearer m-test"
            assert "visibility=public" in request.content.decode()
            return httpx.Response(200, json={"id": "55", "url": "https://mastodon.social/@demo/55", "visibility": "public"})
        if request.url.path.endswith("createSession"):
            body = json.loads(request.content)
            assert body["identifier"] == "example.bsky.social"
            return httpx.Response(200, json={"accessJwt": "test-access-jwt", "did": "did:plc:example"})
        if request.url.path.endswith("createRecord"):
            assert request.headers["Authorization"] == "Bearer test-access-jwt"
            body = json.loads(request.content)
            assert body["record"]["text"] == MESSAGE
            assert body["record"]["facets"][0]["features"][0]["uri"] == "https://example.com"
            return httpx.Response(200, json={"uri": "at://did:plc:example/app.bsky.feed.post/xyz123", "cid": "bafy-test"})
        if request.url.host == "api.telegram.org":
            assert json.loads(request.content)["chat_id"] == "@mypublicchannel"
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 99}})
        if request.url.host == "discord.com":
            assert request.url.params["wait"] == "true"
            assert json.loads(request.content)["allowed_mentions"] == {"parse": []}
            return httpx.Response(200, json={"id": "3", "channel_id": "2", "guild_id": "1"})
        if request.url.host == "myblog.example":
            assert request.headers["Authorization"].startswith("Basic ")
            body = json.loads(request.content)
            assert body["status"] == "publish"
            return httpx.Response(201, json={"id": 70, "status": "publish", "link": "https://myblog.example/hello/"})
        raise AssertionError(f"Unexpected provider endpoint: {request.url}")

    settings = Settings(
        posting_enabled=True,
        mastodon_base_url="https://mastodon.social", mastodon_token="m-test",
        bluesky_handle="example.bsky.social", bluesky_app_password="app-password-test",
        telegram_bot_token="123456789:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        telegram_public_channel="@mypublicchannel",
        discord_webhook_url="https://discord.com/api/webhooks/22/secret",
        wordpress_base_url="https://myblog.example", wordpress_username="test-user",
        wordpress_app_password="test-app-password",
    )

    async def fake_client():
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as client:
            yield client

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_client] = fake_client
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as api:
            res = await api.post("/posting", json={"message": MESSAGE})
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert len(calls) == 6
        assert [x["platform"] for x in body["results"]] == ["Mastodon", "Bluesky", "Telegram", "Discord", "WordPress"]
        assert all(x["status"] == "success" and x["posted_url"] for x in body["results"])
        assert next(x for x in body["results"] if x["platform"] == "Discord")["public_access"] is False
        assert all(x["date"] and x["time"] for x in body["results"])
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_platform_failure_does_not_stop_other_adapters():
    from app.services.posting_service import publish_all
    from app.schemas import PostingRequest

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.host == "mastodon.social":
            return httpx.Response(401, json={"error": "unauthorized"})
        if request.url.path.endswith("createSession"):
            return httpx.Response(200, json={"accessJwt": "xyz", "did": "did:plc:example"})
        if request.url.path.endswith("createRecord"):
            return httpx.Response(200, json={"uri": "at://did:plc:example/app.bsky.feed.post/rkey", "cid": "c"})
        if request.url.host == "api.telegram.org":
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 5}})
        if request.url.host == "discord.com":
            return httpx.Response(200, json={"id": "3", "channel_id": "2", "guild_id": "1"})
        return httpx.Response(201, json={"id": 1, "status": "publish", "link": "https://myblog.example/1"})

    settings = Settings(posting_enabled=True, mastodon_base_url="https://mastodon.social", mastodon_token="wrong",
        bluesky_handle="test.bsky.social", bluesky_app_password="test", telegram_bot_token="123456789:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        telegram_public_channel="@mypublicchannel", discord_webhook_url="https://discord.com/api/webhooks/2/secret",
        wordpress_base_url="https://myblog.example", wordpress_username="u", wordpress_app_password="p")
    async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as c:
        outcome = await publish_all(PostingRequest(message=MESSAGE), c, settings)
    assert not outcome.success
    assert outcome.results[0].status == "failed"
    assert "HTTP 401" in outcome.results[0].error
    assert all(x.status == "success" for x in outcome.results[1:])


@pytest.mark.asyncio
async def test_config_missing_does_not_claim_success():
    from app.services.posting_service import publish_all
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail("Should not call outside APIs"))) as c:
        outcome = await publish_all(PostingRequest(message=MESSAGE), c, Settings(posting_enabled=True))
    assert not outcome.success
    assert len(outcome.results) == 5
    assert all(x.status == "failed" and not x.posted_url for x in outcome.results)
