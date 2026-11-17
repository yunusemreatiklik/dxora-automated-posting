"""Discord test suite: mock only, never publishes to Discord."""
import json
import httpx
import pytest
from app.config import Settings
from app.platforms import discord
from tools.verify_existing_discord import parse_message_link,verify_existing

@pytest.mark.asyncio
async def test_post_without_guild_id_falls_back_to_get_webhook():
    calls=[]
    def fake(req):
        calls.append(req)
        if req.method=="POST":
            assert req.url.params.get("wait")=="true"
            return httpx.Response(200,json={"id":"101","channel_id":"202"})
        return httpx.Response(200,json={"guild_id":"303","channel_id":"202"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(fake)) as client:
        out=await discord.publish("hi",client,Settings(discord_webhook_url="https://discord.com/api/webhooks/11/secret"))
    assert out.status=="success"
    assert out.posted_url=="https://discord.com/channels/303/202/101"
    assert out.public_access is False
    assert [r.method for r in calls]==["POST","GET"]

@pytest.mark.asyncio
async def test_post_without_guild_id_or_metadata_still_success_without_fake_link():
    def fake(req):
        if req.method=="POST":return httpx.Response(200,json={"id":"101","channel_id":"202"})
        return httpx.Response(403)
    async with httpx.AsyncClient(transport=httpx.MockTransport(fake)) as client:
        out=await discord.publish("hi",client,Settings(discord_webhook_url="https://discord.com/api/webhooks/11/secret"))
    assert out.status=="success" and out.posted_url is None

@pytest.mark.asyncio
async def test_missing_message_id_is_not_silent_success():
    from app.platforms.base import PlatformError
    def fake(req):return httpx.Response(200,json={"channel_id":"202"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(fake)) as client:
        with pytest.raises(PlatformError,match="check channel"):
            await discord.publish("hi",client,Settings(discord_webhook_url="https://discord.com/api/webhooks/11/secret"))


def test_parse_existing_message_link():
    guild,channel,msg=parse_message_link("https://discord.com/channels/1572184900696674354/1572186549238632519/1572199999999999999")
    assert guild=="1572184900696674354" and msg=="1572199999999999999"
    with pytest.raises(ValueError):parse_message_link("https://discord.com/channels/1572184900696674354/1572186549238632519")


def test_read_only_existing_discord_message_confirmation():
    calls=[]
    def fake(request):
        calls.append(request)
        return httpx.Response(200,json={
            "id":"1572199999999999999", "channel_id":"1572186549238632519",
            "webhook_id":"1572186666439807086", "timestamp":"2026-11-17T18:01:00.000Z",
            "content":"Dxora Python integration verification on Discord: https://github.com/yunusemreatiklik",
        })
    data=verify_existing("https://discord.com/channels/1572184900696674354/1572186549238632519/1572199999999999999",
        "https://discord.com/api/webhooks/1572186666439807086/secret",transport=httpx.MockTransport(fake))
    assert len(calls)==1 and calls[0].method=="GET"
    assert data["status"]=="success" and data["date"]=="2026-11-17"
    assert data["posted_url"].endswith("/1572199999999999999")
