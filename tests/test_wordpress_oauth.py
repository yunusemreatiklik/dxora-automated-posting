"""Offline WordPress.com OAuth and posting contract tests; no live posts."""
from __future__ import annotations

import json
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from app.config import Settings, get_settings
from app.main import app
from app.wordpress_oauth import get_oauth_client, _pending
from app.platforms import wordpress
from app.schemas import PostingRequest


@pytest.mark.asyncio
async def test_oauth_authorization_callback_and_wordpress_posting(tmp_path, monkeypatch):
    token_file = tmp_path / ".wordpress_oauth_token.json"
    monkeypatch.setattr(wordpress, "TOKEN_FILE", token_file)
    import app.wordpress_oauth as oauth
    monkeypatch.setattr(oauth, "TOKEN_FILE", token_file)

    settings = Settings(
        posting_enabled=True,
        wordpress_base_url="https://userblog.wordpress.com",
        wordpress_client_id="test-client-id",
        wordpress_client_secret="test-client-secret",
    )
    calls = []

    def provider(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path == "/oauth2/token":
            assert request.method == "POST"
            assert b"client_secret=test-client-secret" in request.content
            assert b"grant_type=authorization_code" in request.content
            return httpx.Response(200, json={
                "access_token": "oauth-token-for-test",
                "blog_id": "12345",
                "blog_url": "https://userblog.wordpress.com",
                "token_type": "bearer",
            })
        if request.url.path == "/rest/v1.2/sites/12345/posts/new":
            assert request.headers["Authorization"] == "Bearer oauth-token-for-test"
            assert json.loads(request.content)["status"] == "publish"
            return httpx.Response(201, json={
                "ID": 86,
                "status": "publish",
                "URL": "https://userblog.wordpress.com/2026/11/hello/",
            })
        raise AssertionError(f"Unexpected request: {request.url}")

    async def fake_client():
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as c:
            yield c

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_oauth_client] = fake_client
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:4000") as api:
            r = await api.get("/wordpress/connect", follow_redirects=False)
            assert r.status_code == 302
            params = parse_qs(urlsplit(r.headers["location"]).query)
            assert params["client_id"] == ["test-client-id"]
            assert params["blog"] == ["userblog.wordpress.com"]
            assert params["scope"] == ["posts"]
            assert params["redirect_uri"] == ["http://localhost:4000/wordpress/callback"]
            state = params["state"][0]

            # State is not guessable; state is single use.
            denied = await api.get("/wordpress/callback?code=x&state=wrong")
            assert denied.status_code == 400
            success = await api.get("/wordpress/callback", params={"code": "auth-code-test", "state": state})
            assert success.status_code == 200
            assert "connection successful" in success.text
            assert "oauth-token-for-test" not in success.text
            replay = await api.get("/wordpress/callback", params={"code": "auth-code-test", "state": state})
            assert replay.status_code == 400

        assert json.loads(token_file.read_text())["blog_id"] == "12345"
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as provider_client:
            result = await wordpress.publish("Check https://example.com", provider_client, settings)
        assert result.status == "success"
        assert result.posted_url.startswith("https://userblog.wordpress.com/")
        assert len(calls) == 2
    finally:
        app.dependency_overrides.clear()
        _pending.clear()


@pytest.mark.asyncio
async def test_oauth_without_credentials_is_clear_error():
    app.dependency_overrides[get_settings] = lambda: Settings(
        wordpress_base_url="https://userblog.wordpress.com"
    )
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as api:
            r = await api.get("/wordpress/connect")
        assert r.status_code == 400
        assert "WORDPRESS_CLIENT_ID" in r.text
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_wordpress_does_not_publish_with_wrong_blog_token(tmp_path, monkeypatch):
    token_file = tmp_path / ".wordpress_oauth_token.json"
    token_file.write_text(json.dumps({
        "access_token": "wrong-site-token", "blog_id": "4321", "blog_url": "https://wrong.wordpress.com"
    }))
    monkeypatch.setattr(wordpress, "TOKEN_FILE", token_file)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail("Should not POST"))) as client:
        from app.platforms.base import PlatformError
        with pytest.raises(PlatformError, match="different site"):
            await wordpress.publish("Check https://example.com", client, Settings(
                wordpress_base_url="https://userblog.wordpress.com"
            ))
