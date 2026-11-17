"""READ ONLY: Verify a previously sent Discord message using its message link.

Does not POST, PATCH or DELETE. Does not print webhook tokens.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

import httpx
from app.config import get_settings

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"^/channels/(?P<guild>\d{15,22})/(?P<channel>\d{15,22})/(?P<message>\d{15,22})/?$")


def parse_message_link(url: str) -> tuple[str,str,str]:
    parts = urlsplit(url.strip())
    if parts.scheme != "https" or parts.hostname not in ("discord.com", "discordapp.com", "canary.discord.com", "ptb.discord.com"):
        raise ValueError("Expected: https://discord.com/channels/SERVER/CHANNEL/MESSAGE")
    match = LINK.fullmatch(parts.path)
    if not match:
        raise ValueError("A message link is required, not a channel link. Right-click the message and select Copy Message Link.")
    return match.group("guild"),match.group("channel"),match.group("message")


def verify_existing(link: str, webhook_url: str, transport: httpx.BaseTransport | None = None) -> dict:
    guild,channel,msg = parse_message_link(link)
    hook = urlsplit(webhook_url)
    if hook.scheme != "https" or hook.hostname not in ("discord.com", "discordapp.com") or not re.fullmatch(r"/api/webhooks/\d{15,22}/[^/]+/?",hook.path):
        raise ValueError("DISCORD_WEBHOOK_URL in .env is missing or invalid")
    url = webhook_url.rstrip("/") + "/messages/" + msg
    with httpx.Client(timeout=20.0, follow_redirects=False, transport=transport) as client:
        response=client.get(url)
    if response.status_code != 200:
        raise ValueError(f"Discord message verification failed (HTTP {response.status_code}); check the message link")
    data=response.json()
    if str(data.get("id")) != msg or str(data.get("channel_id")) != channel:
        raise ValueError("Discord API response does not match the message link")
    if str(data.get("webhook_id")) != hook.path.split("/")[3]:
        raise ValueError("The message was not sent by the configured project webhook")
    content=data.get("content","")
    if "Dxora Python integration verification on Discord:" not in content or "https://github.com/yunusemreatiklik" not in content:
        raise ValueError("Message content does not match the expected Dxora test message")
    timestamp=data.get("timestamp")
    if isinstance(timestamp,str):
        dt=datetime.fromisoformat(timestamp.replace("Z","+00:00")).astimezone(timezone.utc)
    else:
        dt=datetime.now(timezone.utc)
    return {
        "platform":"Discord", "status":"success", "posted_url":f"https://discord.com/channels/{guild}/{channel}/{msg}",
        "public_access":False,"date":dt.date().isoformat(),"time":dt.strftime("%H:%M:%SZ"),"error":None,
        "verification_method":"Discord GET Webhook Message - existing message, no new publication",
        "verified_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main() -> None:
    print("DXORA - VERIFY AN EXISTING DISCORD MESSAGE (READ-ONLY)")
    print("This tool NEVER publishes a new message to any platform.")
    print("In Discord #dxora-posting, right-click the existing DxoraPosting message and select Copy Message Link.")
    link=input("Paste the existing Discord message URL: ").strip()
    webhook_url=get_settings().discord_webhook_url
    try:
        result=verify_existing(link,webhook_url)
    except (ValueError,httpx.HTTPError) as exc:
        print("VERIFICATION FAILED:",str(exc))
        return
    output=ROOT/"evidence"/"LIVE_discord_verified_existing_message.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("\nEXISTING MESSAGE VERIFIED:")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    print("\nEvidence file:",output)


if __name__=="__main__":
    main()
