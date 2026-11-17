"""One user REST endpoint: POST /posting (FastAPI serves /docs automatically)."""
from __future__ import annotations

from collections.abc import AsyncIterator
import httpx
from fastapi import Depends, FastAPI

from app.config import Settings, get_settings
from app.schemas import PostingRequest, PostingResponse
from app.services.posting_service import publish_all
from app.wordpress_oauth import router as wordpress_oauth_router

app = FastAPI(
    title="Automated Multi-Platform Posting System",
    description="Publish a validated message through five independently configured platform APIs.",
    version="1.0.0",
)


app.include_router(wordpress_oauth_router)


async def get_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
        yield client


@app.post("/posting", response_model=PostingResponse)
async def posting(
    payload: PostingRequest,
    client: httpx.AsyncClient = Depends(get_client),
    settings: Settings = Depends(get_settings),
) -> PostingResponse:
    return await publish_all(payload, client, settings)
