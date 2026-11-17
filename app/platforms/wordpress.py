"""WordPress.com OAuth2 posting, or self-hosted WordPress Application Password posting."""
from __future__ import annotations

import html
import json
from pathlib import Path
from urllib.parse import quote, urlsplit

import httpx

from app.config import Settings
from app.platforms.base import PlatformError, expect_json, require_https_base, successful
from app.schemas import PostingResult, extract_cta_url

NAME = "WordPress"
# Saved on the user's computer ONLY. Never include in submitted project or GitHub.
TOKEN_FILE = Path(__file__).resolve().parents[2] / ".wordpress_oauth_token.json"


def _payload(message: str) -> dict[str, str]:
    link = extract_cta_url(message)
    description = message.replace(link, "").strip(" -:;,.\n")
    title = description[:70].strip() or "New announcement"
    body_html = (
        f"<p>{html.escape(description)} "
        f'<a href="{html.escape(link, quote=True)}">{html.escape(link)}</a></p>'
    )
    return {"title": title, "content": body_html, "status": "publish"}


def _wordpress_com_token(base: str) -> tuple[str, str]:
    try:
        data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise PlatformError("WordPress.com not connected; open http://localhost:4000/wordpress/connect") from None
    access_token = data.get("access_token")
    blog_id = str(data.get("blog_id", ""))
    blog_url = data.get("blog_url", "")
    if not isinstance(access_token, str) or not access_token or not blog_id.isdigit():
        raise PlatformError("WordPress.com OAuth token invalid; reconnect at /wordpress/connect")
    if not isinstance(blog_url, str) or blog_url.rstrip("/").lower() != base.lower():
        raise PlatformError("WordPress.com OAuth token belongs to a different site; reconnect")
    return access_token, blog_id


async def publish(message: str, client: httpx.AsyncClient, settings: Settings) -> PostingResult:
    if not settings.wordpress_base_url:
        raise PlatformError("Missing WORDPRESS_BASE_URL")
    base = require_https_base(settings.wordpress_base_url)
    host = urlsplit(base).hostname or ""
    payload = _payload(message)
    if host.endswith(".wordpress.com"):
        access_token, site_id = _wordpress_com_token(base)
        # WordPress.com legacy REST API natively accepts OAuth2 scoped to posts.
        # The v1.2 endpoint is documented for free WordPress.com sites.
        response = await client.post(
            f"https://public-api.wordpress.com/rest/v1.2/sites/{quote(site_id)}/posts/new",
            headers={"Authorization": f"Bearer {access_token}"},
            json=payload,
        )
    else:
        # Legacy self-hosted mode is retained for separately hosted sites.
        if not (settings.wordpress_username and settings.wordpress_app_password):
            raise PlatformError("Missing WORDPRESS_USERNAME or WORDPRESS_APP_PASSWORD")
        response = await client.post(
            f"{base}/wp-json/wp/v2/posts",
            auth=httpx.BasicAuth(settings.wordpress_username, settings.wordpress_app_password),
            json={**payload, "comment_status": "closed"},
        )
    data = await expect_json(response)
    # WordPress.com REST v1.2 uses uppercase ID and URL; self-hosted wp/v2
    # uses lowercase id and link. Both confirm status=publish.
    post_id = data.get("ID") if host.endswith(".wordpress.com") else data.get("id")
    link = data.get("URL") if host.endswith(".wordpress.com") else data.get("link")
    if data.get("status") != "publish" or not post_id or not link:
        raise PlatformError("WordPress did not confirm published post and URL")
    if not isinstance(link, str) or urlsplit(link).scheme != "https":
        raise PlatformError("WordPress returned an invalid public post URL")
    if host.endswith(".wordpress.com") and urlsplit(link).hostname != host:
        raise PlatformError("WordPress post URL does not match configured site")
    return successful(NAME, link, True)
