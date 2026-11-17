"""Read-only network connectivity check; no secrets and no publishing."""
import asyncio
from urllib.parse import urlsplit
import httpx
from app.config import get_settings


async def main() -> None:
    site_host = urlsplit(get_settings().wordpress_base_url).hostname or "example.wordpress.com"
    endpoints = [
        ("Discord", "https://discord.com/api/v10/gateway"),
        ("WordPress", f"https://public-api.wordpress.com/rest/v1.1/sites/{site_host}/posts/"),
    ]
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, url in endpoints:
            try:
                response = await client.get(url)
                print(f"{name}: HTTP {response.status_code} (reachable; posting not tested)")
            except httpx.TimeoutException:
                print(f"{name}: TIMEOUT (check VPN, DNS, firewall, and connectivity)")
            except httpx.HTTPError as exc:
                print(f"{name}: NETWORK ERROR ({type(exc).__name__})")


if __name__ == "__main__":
    asyncio.run(main())
