"""Configuration is loaded only from the environment / local .env file."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True, slots=True)
class Settings:
    posting_enabled: bool = False
    mastodon_base_url: str = ""
    mastodon_token: str = ""
    bluesky_handle: str = ""
    bluesky_app_password: str = ""
    telegram_bot_token: str = ""
    telegram_public_channel: str = ""
    discord_webhook_url: str = ""
    wordpress_base_url: str = ""
    wordpress_username: str = ""
    wordpress_app_password: str = ""
    wordpress_client_id: str = ""
    wordpress_client_secret: str = ""


def get_settings() -> Settings:
    return Settings(
        posting_enabled=os.getenv("POSTING_ENABLED", "false").lower() == "true",
        mastodon_base_url=os.getenv("MASTODON_BASE_URL", ""),
        mastodon_token=os.getenv("MASTODON_TOKEN", ""),
        bluesky_handle=os.getenv("BLUESKY_HANDLE", ""),
        bluesky_app_password=os.getenv("BLUESKY_APP_PASSWORD", ""),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_public_channel=os.getenv("TELEGRAM_PUBLIC_CHANNEL", ""),
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL", ""),
        wordpress_base_url=os.getenv("WORDPRESS_BASE_URL", ""),
        wordpress_username=os.getenv("WORDPRESS_USERNAME", ""),
        wordpress_app_password=os.getenv("WORDPRESS_APP_PASSWORD", ""),
        wordpress_client_id=os.getenv("WORDPRESS_CLIENT_ID", ""),
        wordpress_client_secret=os.getenv("WORDPRESS_CLIENT_SECRET", ""),
    )
