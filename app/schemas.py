"""Request and response models shared by the FastAPI endpoint."""
from __future__ import annotations

import ipaddress
import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

# The URL regex deliberately stops at whitespace and common prose delimiters.
# Trailing sentence punctuation is removed before parsing.
LINK_PATTERN = re.compile(r"https?://[^\s<>\"'`]+", re.IGNORECASE)
TRAILING_PUNCTUATION = ".,;:!?)]}"


def extract_cta_url(message: str) -> str:
    """Require exactly one externally addressable HTTP(S) CTA URL."""
    matches = [m.group(0).rstrip(TRAILING_PUNCTUATION) for m in LINK_PATTERN.finditer(message)]
    if len(matches) != 1:
        raise ValueError("Message must contain exactly one HTTP(S) CTA link")
    url = matches[0]
    parts = urlsplit(url)
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        raise ValueError("CTA link must be a valid HTTP(S) URL")
    if parts.username or parts.password:
        raise ValueError("CTA link cannot include URL credentials")
    hostname = parts.hostname.lower().rstrip(".")
    if hostname in ("localhost", "localhost.localdomain") or hostname.endswith(".local"):
        raise ValueError("CTA link cannot target a local host")
    try:
        addr = ipaddress.ip_address(hostname)
        if not addr.is_global:
            raise ValueError("CTA link must use a publicly routable address")
    except ValueError as exc:
        if "publicly routable" in str(exc):
            raise
        if "." not in hostname or len(hostname) > 253:
            raise ValueError("CTA link must contain a valid public hostname") from exc
        labels = hostname.split(".")
        if any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels):
            raise ValueError("CTA link contains an invalid hostname") from exc
    if any(ch in url for ch in "{}\\"):
        raise ValueError("CTA link contains invalid characters")
    return url


class PostingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=200, description="Message with exactly one CTA URL")

    @field_validator("message")
    @classmethod
    def check_cta(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message cannot be blank")
        extract_cta_url(value)
        return value


class PostingResult(BaseModel):
    platform: str
    status: Literal["success", "failed"]
    posted_url: str | None = None
    public_access: bool = False
    date: str | None = None
    time: str | None = None
    error: str | None = None


class PostingResponse(BaseModel):
    success: bool  # True ONLY when all five platform publications succeed.
    results: list[PostingResult]
