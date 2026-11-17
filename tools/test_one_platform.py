"""Explicitly publish to exactly ONE selected provider, never all five."""
from __future__ import annotations
import asyncio
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import httpx
from app.config import get_settings
from app.platforms import wordpress, discord
from app.services.posting_service import publish_to_one

ROOT = Path(__file__).resolve().parents[1]
OPTIONS = {"1": wordpress, "2": discord}


def main() -> None:
    print("DXORA - SINGLE-PLATFORM LIVE PUBLISHING TEST")
    print("1 - WordPress")
    print("2 - Discord")
    print("0 - Cancel")
    choice = input("Select an option [1/2/0]: ").strip()
    if choice not in OPTIONS:
        print("Cancelled. No message was published.")
        return
    platform = OPTIONS[choice]
    message = f"Dxora Python integration verification on {platform.NAME}: https://github.com/yunusemreatiklik"
    print("\nMessage to publish:", message)
    print(f"This will publish a REAL message to {platform.NAME} ONLY.")
    print("Mastodon, Bluesky, and Telegram will NOT be contacted.")
    confirmation = input("Type PUBLISH to confirm (anything else cancels): ").strip()
    if confirmation != "PUBLISH":
        print("Cancelled. No message was published.")
        return
    settings = replace(get_settings(), posting_enabled=True)

    async def run():
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
            return await publish_to_one(platform, message, client, settings)

    result = asyncio.run(run())
    data = result.model_dump()
    print("\nRESULT:")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    output = ROOT / "evidence" / (
        "LIVE_" + platform.NAME.lower() + "_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + ".json"
    )
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\nEvidence saved to:", output)
    print("NOTICE: Check the provider for an existing post before attempting another publish.")


if __name__ == "__main__":
    main()
