import json
import httpx
import pytest
from app.config import Settings
from app.platforms import wordpress
from app.platforms.base import PlatformError

@pytest.mark.asyncio
async def test_wordpress_com_rest_v12_publishes_and_parses_uppercase(monkeypatch, tmp_path):
    tok=tmp_path/"token.json"
    tok.write_text(json.dumps({"access_token":"fake", "blog_id":"123", "blog_url":"https://demo.wordpress.com"}))
    monkeypatch.setattr(wordpress,"TOKEN_FILE",tok)
    async def mock_handler(request):
        assert request.url.path=="/rest/v1.2/sites/123/posts/new"
        assert request.headers["Authorization"]=="Bearer fake"
        assert json.loads(request.content)["status"]=="publish"
        return httpx.Response(200,json={"ID":90,"URL":"https://demo.wordpress.com/hello/","status":"publish"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_handler)) as cli:
        out=await wordpress.publish("Hello https://example.com",cli,Settings(wordpress_base_url="https://demo.wordpress.com"))
    assert out.status=="success"
    assert out.posted_url=="https://demo.wordpress.com/hello/"

@pytest.mark.asyncio
async def test_wordpress_rest_v12_403_reported_not_fake_success(monkeypatch, tmp_path):
    tok=tmp_path/"token.json"
    tok.write_text(json.dumps({"access_token":"fake", "blog_id":"123", "blog_url":"https://demo.wordpress.com"}))
    monkeypatch.setattr(wordpress,"TOKEN_FILE",tok)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(403,json={"error":"unauthorized"}))) as cli:
        with pytest.raises(PlatformError,match="403"):
            await wordpress.publish("Hello https://example.com",cli,Settings(wordpress_base_url="https://demo.wordpress.com"))
