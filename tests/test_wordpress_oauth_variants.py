"""Regression tests for WordPress.com token metadata variations.
All provider HTTP calls are mocked: never publish to real platforms.
"""
import json
from urllib.parse import parse_qs, urlsplit
import httpx
import pytest
from app.main import app
from app.config import Settings, get_settings
from app.wordpress_oauth import get_oauth_client, _pending
from app.platforms import wordpress

@pytest.mark.asyncio
@pytest.mark.parametrize('token_meta', [
    {"blog_id": 0, "blog_url": "http://userblog.wordpress.com/"},
    {"blog_id": "12345", "blog_url": "https://userblog.wordpress.com/"},
    {"blog_id": "12345", "blog_url": "https://custom-domain.example"},
    {"site_id": "12345", "blog_url": None},
])
async def test_oauth_handles_site_metadata_variations(tmp_path, monkeypatch, token_meta):
    import app.wordpress_oauth as oauth
    tokenfile = tmp_path / '.wordpress_oauth_token.json'
    monkeypatch.setattr(oauth, 'TOKEN_FILE', tokenfile)
    monkeypatch.setattr(wordpress, 'TOKEN_FILE', tokenfile)
    settings = Settings(wordpress_base_url='https://userblog.wordpress.com',wordpress_client_id='123',wordpress_client_secret='secret')
    events=[]
    def provider(req):
        events.append((req.method,req.url.path))
        if req.url.path=='/oauth2/token':
            return httpx.Response(200,json={"access_token":"a-local-test-value",**token_meta})
        if req.url.path=='/rest/v1.1/sites/userblog.wordpress.com':
            return httpx.Response(200,json={"ID":12345,"URL":"https://userblog.wordpress.com"})
        pytest.fail('Unexpected provider request')
    async def cl():
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as client:
            yield client
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_oauth_client] = cl
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://localhost:4000') as c:
            start=await c.get('/wordpress/connect',follow_redirects=False)
            state=parse_qs(urlsplit(start.headers['location']).query)['state'][0]
            res=await c.get('/wordpress/callback',params={'state':state,'code':'dummy'})
        assert res.status_code==200, res.text
        assert json.loads(tokenfile.read_text())['blog_id']=='12345'
        assert json.loads(tokenfile.read_text())['blog_url']=='https://userblog.wordpress.com'
        assert len(events) in (1,2)
    finally:
        app.dependency_overrides.clear()
        _pending.clear()

@pytest.mark.asyncio
async def test_oauth_rejects_other_site_even_with_valid_token(tmp_path,monkeypatch):
    import app.wordpress_oauth as oauth
    tokenfile=tmp_path/'.wordpress_oauth_token.json'
    monkeypatch.setattr(oauth,'TOKEN_FILE',tokenfile)
    settings=Settings(wordpress_base_url='https://userblog.wordpress.com',wordpress_client_id='123',wordpress_client_secret='secret')
    def provider(req):
        if req.url.path=='/oauth2/token':
            return httpx.Response(200,json={'access_token':'private-example','blog_id':'9000','blog_url':'https://other.wordpress.com'})
        return httpx.Response(200,json={'ID':12345,'URL':'https://userblog.wordpress.com'})
    async def cl():
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as client:
            yield client
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_oauth_client] = cl
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://localhost:4000') as c:
            start=await c.get('/wordpress/connect',follow_redirects=False)
            state=parse_qs(urlsplit(start.headers['location']).query)['state'][0]
            res=await c.get('/wordpress/callback',params={'state':state,'code':'dummy'})
        assert res.status_code==502
        assert 'different WordPress site' in res.text
        assert not tokenfile.exists()
    finally:
        app.dependency_overrides.clear()
        _pending.clear()

@pytest.mark.asyncio
async def test_oauth_reports_missing_access_token_safely(tmp_path,monkeypatch):
    import app.wordpress_oauth as oauth
    tokenfile=tmp_path/'.wordpress_oauth_token.json'
    monkeypatch.setattr(oauth,'TOKEN_FILE',tokenfile)
    settings=Settings(wordpress_base_url='https://userblog.wordpress.com',wordpress_client_id='123',wordpress_client_secret='secret')
    async def cl():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200,json={'error':'invalid_grant','error_description':'contains sensitive text'}))) as client:
            yield client
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_oauth_client] = cl
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://localhost:4000') as c:
            start=await c.get('/wordpress/connect',follow_redirects=False)
            state=parse_qs(urlsplit(start.headers['location']).query)['state'][0]
            res=await c.get('/wordpress/callback',params={'state':state,'code':'dummy'})
        assert res.status_code==502
        assert 'invalid_grant' in res.text
        assert 'sensitive text' not in res.text
        assert not tokenfile.exists()
    finally:
        app.dependency_overrides.clear()
        _pending.clear()
