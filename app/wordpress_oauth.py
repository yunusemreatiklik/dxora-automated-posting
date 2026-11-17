"""WordPress.com authorization-code OAuth2 flow (local development only).

Only the authorization URL is sent to the browser. Client secret and token stay
on the local machine. State is single-use and is checked before token exchange.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
import os
import secrets
import time
from pathlib import Path
from urllib.parse import urlsplit, quote

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import Settings, get_settings
from app.platforms.wordpress import TOKEN_FILE

router = APIRouter()


async def get_oauth_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
        yield client

REDIRECT_URI = "http://localhost:4000/wordpress/callback"
AUTH_BASE = "https://public-api.wordpress.com/oauth2/authorize"
TOKEN_ENDPOINT = "https://public-api.wordpress.com/oauth2/token"

# Local single-process development. Restarting the server invalidates pending
# authorization attempts, but does not erase an already stored access token.
_pending: dict[str, float] = {}


def _validated_settings(settings: Settings) -> str:
    if not settings.wordpress_client_id or not settings.wordpress_client_secret:
        raise HTTPException(400, "Fill WORDPRESS_CLIENT_ID and WORDPRESS_CLIENT_SECRET in .env, then restart the server")
    parts = urlsplit(settings.wordpress_base_url)
    host = parts.hostname
    if parts.scheme != "https" or not host or not host.endswith(".wordpress.com") or parts.username or parts.password or parts.path not in ("", "/") or parts.query or parts.fragment:
        raise HTTPException(400, "WORDPRESS_BASE_URL must be your https://yourblog.wordpress.com site")
    return host


@router.get("/wordpress/connect", include_in_schema=True)
async def wordpress_connect(settings: Settings = Depends(get_settings)):
    host = _validated_settings(settings)
    state = secrets.token_urlsafe(32)
    now = time.monotonic()
    _pending.clear()  # one active local login attempt at a time
    _pending[state] = now + 600
    return RedirectResponse(
        str(httpx.URL(AUTH_BASE, params={
            "client_id": settings.wordpress_client_id,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": "posts",
            "blog": host,
            "state": state,
        })),
        status_code=302,
    )


@router.get("/wordpress/callback", response_class=HTMLResponse, include_in_schema=True)
async def wordpress_callback(
    code: str = "",
    state: str = "",
    error: str = "",
    settings: Settings = Depends(get_settings),
    client: httpx.AsyncClient = Depends(get_oauth_client),
):
    _validated_settings(settings)
    expires = _pending.pop(state, None)
    if not state or expires is None or time.monotonic() > expires:
        raise HTTPException(400, "Invalid/expired OAuth state. Start again at /wordpress/connect")
    if error:
        raise HTTPException(400, "WordPress.com authorization was denied")
    if not code:
        raise HTTPException(400, "WordPress.com did not supply an authorization code")
    try:
        response = await client.post(TOKEN_ENDPOINT, data={
            "client_id": settings.wordpress_client_id,
            "client_secret": settings.wordpress_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        })
    except httpx.HTTPError:
        raise HTTPException(502, "WordPress.com token exchange network error")
    if response.status_code != 200:
        raise HTTPException(502, f"WordPress.com token exchange failed (HTTP {response.status_code})")
    # WordPress.com may return slightly different site metadata depending on
    # account, domain and OAuth scope. Never reject a genuine access token
    # just because its blog_url is http:// or it omitted blog_id: resolve the
    # target site with the official public API and compare numeric site IDs.
    try:
        payload = response.json()
    except ValueError:
        raise HTTPException(502, "WordPress.com returned non-JSON token data")
    if not isinstance(payload, dict):
        raise HTTPException(502, "WordPress.com returned unexpected token data")
    token = payload.get("access_token")
    if not isinstance(token, str) or not token.strip():
        # Never echo complete provider responses, authorization codes or tokens.
        err = payload.get("error") or payload.get("code")
        safe_error = (str(err)[:55] if isinstance(err, str)
                      and all(c.isalnum() or c in "_- ." for c in err[:55]) else "unspecified")
        raise HTTPException(502, f"WordPress.com did not provide access_token (OAuth error: {safe_error})")

    expected_host = urlsplit(settings.wordpress_base_url).hostname
    raw_blog_url = payload.get("blog_url")
    response_host = urlsplit(raw_blog_url).hostname if isinstance(raw_blog_url, str) else None
    raw_id = payload.get("blog_id") or payload.get("site_id")
    response_id = str(raw_id) if raw_id is not None else ""
    if not response_id.isdigit() or response_id == "0":
        response_id = ""

    # Fast path: WordPress returned a real blog ID and the intended blog host.
    # Ignore harmless http-vs-https and trailing slash differences.
    if response_id and response_host == expected_host:
        blog_id = response_id
    else:
        # The public endpoint is safe to query. It returns the canonical ID of
        # the configured blog and allows us to reject a token for another site.
        try:
            site_response = await client.get(
                f"https://public-api.wordpress.com/rest/v1.1/sites/{quote(expected_host, safe='')}"
            )
            site_data = site_response.json() if site_response.status_code == 200 else None
        except (httpx.HTTPError, ValueError):
            site_data = None
        if not isinstance(site_data, dict):
            raise HTTPException(502, "Cannot verify WordPress site ID using WordPress.com public API")
        public_id = str(site_data.get("ID", ""))
        public_url = site_data.get("URL")
        public_host = urlsplit(public_url).hostname if isinstance(public_url, str) else None
        if not public_id.isdigit() or public_host != expected_host:
            raise HTTPException(502, "Configured WordPress site could not be verified")
        if response_id and response_id != public_id:
            raise HTTPException(502, "OAuth token belongs to a different WordPress site (blog ID mismatch)")
        if response_host and response_host not in (expected_host, "public-api.wordpress.com") and not response_id:
            raise HTTPException(502, "OAuth token belongs to a different WordPress site (URL mismatch)")
        if not response_id and response_host != expected_host:
            # WordPress sometimes gives a global token with blog_id=0. Check
            # its actual delegated blog and 'posts' scope before accepting it.
            try:
                info_response = await client.get(
                    "https://public-api.wordpress.com/oauth2/token-info",
                    params={"client_id": settings.wordpress_client_id, "token": token},
                )
                token_info = info_response.json() if info_response.status_code == 200 else None
            except (httpx.HTTPError, ValueError):
                token_info = None
            if not isinstance(token_info, dict):
                raise HTTPException(502, "Cannot verify WordPress OAuth scope for this site")
            info_blog_id = str(token_info.get("blog_id", ""))
            scope = str(token_info.get("scope", ""))
            if info_blog_id != public_id or "posts" not in scope.split(","):
                raise HTTPException(502, "WordPress OAuth token lacks verified posting access for this site")
        blog_id = public_id
    blog_url = settings.wordpress_base_url.rstrip("/")

    # Atomic write, no secrets printed or returned. This is a localhost-only
    # demo setup; use an OS credential store for production workloads.
    tmp_path = TOKEN_FILE.with_name(TOKEN_FILE.name + ".tmp")
    try:
        fd = os.open(str(tmp_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"access_token": token, "blog_id": blog_id, "blog_url": blog_url}, stream)
        os.replace(tmp_path, TOKEN_FILE)
        if os.name == "posix":
            os.chmod(TOKEN_FILE, 0o600)
    except OSError:
        raise HTTPException(500, "Unable to save local token file; check project folder write permissions")

    return HTMLResponse(
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<title>WordPress.com connection successful</title><body>"
        "<h2>WordPress.com connection successful!</h2>"
        "<p>Your OAuth access token was saved to a private file on this computer. "
        "The token is not displayed on this page.</p>"
        "<p>You can now use <a href='http://localhost:4000/docs'>FastAPI /docs</a> "
        "to test POST /posting. Set POSTING_ENABLED=true only when you intend "
        "to publish live messages.</p>"
        "</body></html>",
        headers={"Cache-Control": "no-store"},
    )
