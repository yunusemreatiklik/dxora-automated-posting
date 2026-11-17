"""Discord webhook adapter. Guild IDs are optional on message responses.

Discord's Message object has an id and channel_id; guild_id is NOT guaranteed.
The webhook metadata endpoint provides guild_id if omitted from the response.
"""
from __future__ import annotations

from urllib.parse import urlsplit
import httpx

from app.config import Settings
from app.platforms.base import PlatformError, expect_json, successful
from app.schemas import PostingResult

NAME = "Discord"


async def publish(message: str, client: httpx.AsyncClient, settings: Settings) -> PostingResult:
    url = settings.discord_webhook_url
    if not url:
        raise PlatformError("Missing DISCORD_WEBHOOK_URL")
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ("discord.com", "discordapp.com") or not parts.path.startswith("/api/webhooks/"):
        raise PlatformError("Webhook must be a valid HTTPS Discord webhook URL")

    # wait=true requests a created-message body instead of a bare 204 response.
    response = await client.post(url, params={"wait": "true"}, json={"content": message, "allowed_mentions": {"parse": []}})
    data = await expect_json(response)
    message_id = data.get("id")
    channel_id = data.get("channel_id")
    if not message_id or not channel_id:
        raise PlatformError("Discord accepted request but returned no message ID; check channel before any retry")

    # guild_id is not part of the mandatory Discord Message object fields.
    guild_id = data.get("guild_id")
    if not guild_id:
        try:
            # Read-only metadata query. NEVER republish to find the guild ID.
            webhook_r = await client.get(url)
            if webhook_r.status_code == 200:
                webhook_info = webhook_r.json()
                if isinstance(webhook_info, dict):
                    guild_id = webhook_info.get("guild_id")
        except (httpx.HTTPError, ValueError):
            pass

    # A valid message ID confirms a successful publish. If guild ID is
    # unavailable, do not invent a link; a user can copy it from Discord.
    permalink = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}" if guild_id else None
    return successful(NAME, permalink, False)
