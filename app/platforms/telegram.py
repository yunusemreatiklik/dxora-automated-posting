"""Telegram Bot API sendMessage to an administrator-authorized PUBLIC channel."""
from __future__ import annotations

import re
import httpx

from app.config import Settings
from app.platforms.base import PlatformError, expect_json, successful
from app.schemas import PostingResult

NAME = "Telegram"


async def publish(message: str, client: httpx.AsyncClient, settings: Settings) -> PostingResult:
    token = settings.telegram_bot_token
    target = settings.telegram_public_channel
    if not (token and target):
        raise PlatformError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_PUBLIC_CHANNEL")
    if not re.fullmatch(r"@[A-Za-z0-9_]{5,32}", target):
        raise PlatformError("Use a public channel username, e.g. @mypublicchannel")
    # Restrict token to BotFather's expected shape, avoiding malformed API URLs.
    if not re.fullmatch(r"\d{5,16}:[A-Za-z0-9_-]{25,}", token):
        raise PlatformError("TELEGRAM_BOT_TOKEN has an invalid format")
    response = await client.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": target, "text": message, "disable_notification": True},
    )
    data = await expect_json(response)
    if data.get("ok") is not True or not isinstance(data.get("result"), dict):
        raise PlatformError("Telegram did not confirm the message")
    mid = data["result"].get("message_id")
    if not isinstance(mid, int):
        raise PlatformError("Telegram returned no message ID")
    return successful(NAME, f"https://t.me/{target[1:]}/{mid}", True)
