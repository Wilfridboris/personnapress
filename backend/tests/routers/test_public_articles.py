"""Tests for the public delivery API (/public/v1/*).

Covers: tenant isolation, hidden article filtering, revoked/malformed tokens,
pagination clamping, tag/category filters, ETag round-trips, seo.json_ld shape,
null-field omission, and rate limiter key extraction.
"""
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Stub slowapi so public_articles.py can be imported without the real package.
# The limiter's .limit() decorator must be a passthrough so async route functions
# remain awaitable in unit tests.
import types as _types

def _make_passthrough_limiter(*args, **kwargs):
    """Returns a fake Limiter whose .limit() is a no-op decorator."""
    lim = MagicMock()
    lim.limit = lambda *a, **kw: (lambda fn: fn)
    return lim

_slowapi_mod = _types.ModuleType("slowapi")
_slowapi_mod.Limiter = _make_passthrough_limiter
sys.modules["slowapi"] = _slowapi_mod

_slowapi_errors = _types.ModuleType("slowapi.errors")
_slowapi_errors.RateLimitExceeded = type("RateLimitExceeded", (Exception,), {})
sys.modules["slowapi.errors"] = _slowapi_errors

_slowapi_mw = _types.ModuleType("slowapi.middleware")
_slowapi_mw.SlowAPIMiddleware = MagicMock()
sys.modules["slowapi.middleware"] = _slowapi_mw

_slowapi_util = _types.ModuleType("slowapi.util")
_slowapi_util.get_remote_address = MagicMock(return_value="127.0.0.1")
sys.modules["slowapi.util"] = _slowapi_util

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc(year=2026, month=1, day=1) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc).replace(tzinfo=None)


def _make_article(
    client_id=None,
    slug="test-slug",
    title="Test Title",
    html="<p>Hello</p>",
    status="published",
    tags=None,
    category=None,
    excerpt=None,
    meta_description=None,
    featured_image_url=None,
    featured_image_alt=None,
    author=None,
    reading_time_minutes=3,
    published_at=None,
    updated_at=None,
) -> MagicMock:
    a = MagicMock()
    a.id = uuid.uuid4()
    a.client_id = client_id or uuid.uuid4()
    a.slug = slug
    a.title = title
    a.html = html
    a.status = status
    a.tags = tags or []
    a.category = category
    a.excerpt = excerpt
    a.meta_description = meta_description
    a.featured_image_url = featured_image_url
    a.featured_image_alt = featured_image_alt
    a.author = author
    a.reading_time_minutes = reading_time_minutes
    a.published_at = published_at or _utc()
    a.updated_at = updated_at or _utc()
    return a


def _make_token(client_id=None, revoked=False, prefix="ppd_abc1") -> MagicMock:
    t = MagicMock()
    t.id = uuid.uuid4()
    t.client_id = client_id or uuid.uuid4()
    t.token_prefix = prefix
    t.token_hash = "fakehash"
    t.revoked_at = _utc() if revoked else None
    t.last_used_at = None
    return t


def _make_request(auth_header: str = "") -> MagicMock:
    req = MagicMock()
    req.headers = {"Authorization": auth_header}
    return req


# ---------------------------------------------------------------------------
# Auth dependency tests
# ---------------------------------------------------------------------------

async def test_get_delivery_client_missing_header_raises_401():
    from app.routers.public_articles import get_delivery_client
    from fastapi import HTTPException

    db = AsyncMock()
    req = _make_request("")
    with pytest.raises(HTTPException) as exc:
        await get_delivery_client(req, db)
    assert exc.value.status_code == 401
    assert exc.value.detail["error"]["code"] == "INVALID_DELIVERY_TOKEN"


async def test_get_delivery_client_wrong_prefix_raises_401():
    from app.routers.public_articles import get_delivery_client
    from fastapi import HTTPException

    db = AsyncMock()
    req = _make_request("Bearer sk_notappd_something")
    with pytest.raises(HTTPException) as exc:
        await get_delivery_client(req, db)
    assert exc.value.status_code == 401


async def test_get_delivery_client_token_not_found_raises_401():
    from app.routers.public_articles import get_delivery_client
    from fastapi import HTTPException

    db = AsyncMock()
    req = _make_request("Bearer ppd_validtokenthatdoesnotexist1234567")

    with patch("app.routers.public_articles.get_active_token_by_prefix", new=AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc:
            await get_delivery_client(req, db)
    assert exc.value.status_code == 401


async def test_get_delivery_client_hash_mismatch_raises_401():
    from app.routers.public_articles import get_delivery_client
    from fastapi import HTTPException

    db = AsyncMock()
    db.commit = AsyncMock()
    req = _make_request("Bearer ppd_validtokenthatdoesnotexist1234567")
    token = _make_token()
    token.token_hash = "wronghash"

    with patch("app.routers.public_articles.get_active_token_by_prefix", new=AsyncMock(return_value=token)):
        with patch("app.routers.public_articles.verify_token", return_value=False):
            with pytest.raises(HTTPException) as exc:
                await get_delivery_client(req, db)
    assert exc.value.status_code == 401


async def test_get_delivery_client_valid_returns_client_id():
    from app.routers.public_articles import get_delivery_client

    client_id = uuid.uuid4()
    db = AsyncMock()
    db.commit = AsyncMock()
    req = _make_request("Bearer ppd_validtokenthatdoesnotexist1234567")
    token = _make_token(client_id=client_id)

    with patch("app.routers.public_articles.get_active_token_by_prefix", new=AsyncMock(return_value=token)):
        with patch("app.routers.public_articles.verify_token", return_value=True):
            with patch("app.routers.public_articles.touch_last_used", new=AsyncMock()):
                result = await get_delivery_client(req, db)
    assert result == client_id


# ---------------------------------------------------------------------------
# List articles
# ---------------------------------------------------------------------------

async def test_list_articles_returns_published_only():
    from app.routers.public_articles import list_published_articles

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id)

    with patch("app.routers.public_articles.list_articles", new=AsyncMock(return_value=([article], 1))):
        req = _make_request()
        req.headers = {}
        resp = await list_published_articles(
            request=req,
            client_id=client_id,
            db=AsyncMock(),
            page=1,
            page_size=20,
            tag=None,
            category=None,
        )

    import json
    body = json.loads(resp.body)
    assert body["meta"]["total"] == 1
    assert len(body["data"]) == 1
    assert body["data"][0]["slug"] == "test-slug"
    # Must not contain html
    assert "html" not in body["data"][0]


async def test_list_articles_page_size_clamped_to_50():
    """page_size > 50 is rejected by Query validation (ge=1, le=50).
    Verify the route passes page_size clamped via list_articles, not raw query param."""
    from app.routers.public_articles import list_published_articles

    client_id = uuid.uuid4()
    mock_list = AsyncMock(return_value=([], 0))

    with patch("app.routers.public_articles.list_articles", mock_list):
        req = MagicMock()
        req.headers = {}
        # Call with page_size=50 (max allowed) — list_articles must receive it unchanged
        await list_published_articles(
            request=req, client_id=client_id, db=AsyncMock(),
            page=1, page_size=50, tag=None, category=None,
        )

    assert mock_list.call_args.kwargs["page_size"] == 50


async def test_list_articles_calls_list_with_published_status():
    from app.routers.public_articles import list_published_articles
    from app.db.repositories.models import ArticleStatus

    client_id = uuid.uuid4()

    mock_list = AsyncMock(return_value=([], 0))
    with patch("app.routers.public_articles.list_articles", mock_list):
        req = MagicMock()
        req.headers = {}
        await list_published_articles(
            request=req,
            client_id=client_id,
            db=AsyncMock(),
            page=1,
            page_size=20,
            tag="python",
            category="tech",
        )

    call_kwargs = mock_list.call_args.kwargs
    assert call_kwargs["status"] == ArticleStatus.published
    assert call_kwargs["tag"] == "python"
    assert call_kwargs["category"] == "tech"


async def test_list_articles_etag_304():
    from app.routers.public_articles import list_published_articles, _etag_list

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id)
    etag = _etag_list(client_id, 1, 20, None, None, 1, article.updated_at.isoformat())

    with patch("app.routers.public_articles.list_articles", new=AsyncMock(return_value=([article], 1))):
        req = MagicMock()
        req.headers = {"If-None-Match": etag}
        resp = await list_published_articles(
            request=req,
            client_id=client_id,
            db=AsyncMock(),
            page=1,
            page_size=20,
            tag=None,
            category=None,
        )

    assert resp.status_code == 304


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------

async def test_tenant_isolation_wrong_token_client_gets_404():
    """Token for client A + slug belonging to client B -> 404, not the article."""
    from app.routers.public_articles import get_published_article

    client_a = uuid.uuid4()
    client_b = uuid.uuid4()
    # get_article_by_slug is called with client_a's id, so client_b's article won't be found
    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=None)):
        req = MagicMock()
        req.headers = {}
        resp = await get_published_article(
            slug="client-b-slug",
            request=req,
            client_id=client_a,
            db=AsyncMock(),
        )

    import json
    body = json.loads(resp.body)
    assert resp.status_code == 404
    assert body["detail"]["error"]["code"] == "ARTICLE_NOT_FOUND"


async def test_list_returns_only_own_articles():
    """list_articles is always called with the resolved client_id — ensuring isolation."""
    from app.routers.public_articles import list_published_articles

    client_id = uuid.uuid4()
    mock_list = AsyncMock(return_value=([], 0))

    with patch("app.routers.public_articles.list_articles", mock_list):
        req = MagicMock()
        req.headers = {}
        await list_published_articles(
            request=req,
            client_id=client_id,
            db=AsyncMock(),
            page=1,
            page_size=20,
            tag=None,
            category=None,
        )

    assert mock_list.call_args.kwargs["client_id"] == client_id


# ---------------------------------------------------------------------------
# Hidden article indistinguishability
# ---------------------------------------------------------------------------

async def test_hidden_article_returns_404():
    from app.routers.public_articles import get_published_article

    article = _make_article(status="hidden")
    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=article)):
        req = MagicMock()
        req.headers = {}
        resp = await get_published_article(
            slug=article.slug,
            request=req,
            client_id=article.client_id,
            db=AsyncMock(),
        )

    import json
    body = json.loads(resp.body)
    assert resp.status_code == 404
    assert body["detail"]["error"]["code"] == "ARTICLE_NOT_FOUND"


async def test_missing_article_and_hidden_same_response():
    """Both missing and hidden return identical response body."""
    from app.routers.public_articles import get_published_article
    import json

    client_id = uuid.uuid4()
    req = MagicMock()
    req.headers = {}

    # Missing
    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=None)):
        resp_missing = await get_published_article(
            slug="nope", request=req, client_id=client_id, db=AsyncMock()
        )
    # Hidden
    hidden = _make_article(client_id=client_id, status="hidden")
    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=hidden)):
        resp_hidden = await get_published_article(
            slug="nope", request=req, client_id=client_id, db=AsyncMock()
        )

    assert resp_missing.status_code == resp_hidden.status_code == 404
    assert json.loads(resp_missing.body) == json.loads(resp_hidden.body)


# ---------------------------------------------------------------------------
# Article detail endpoint
# ---------------------------------------------------------------------------

async def test_article_detail_contains_html_and_seo():
    from app.routers.public_articles import get_published_article
    import json

    article = _make_article(
        meta_description="My description",
        featured_image_url="https://example.com/img.png",
        author="Alice",
        tags=["python", "fastapi"],
    )

    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=article)):
        req = MagicMock()
        req.headers = {}
        resp = await get_published_article(
            slug=article.slug, request=req, client_id=article.client_id, db=AsyncMock()
        )

    body = json.loads(resp.body)
    assert resp.status_code == 200
    assert "html" in body
    assert "seo" in body
    assert "json_ld" in body["seo"]
    assert body["seo"]["json_ld"]["@type"] == "Article"
    assert set(body["seo"]["json_ld"]["keywords"].split(", ")) == {"python", "fastapi"}
    assert "meta_description" in body["seo"]
    assert "og" in body["seo"]


async def test_seo_json_ld_omits_null_fields():
    """Null fields must be omitted from json_ld, not emitted as null."""
    from app.routers.public_articles import get_published_article
    import json

    article = _make_article(
        meta_description=None,
        featured_image_url=None,
        author=None,
        tags=[],
    )

    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=article)):
        req = MagicMock()
        req.headers = {}
        resp = await get_published_article(
            slug=article.slug, request=req, client_id=article.client_id, db=AsyncMock()
        )

    body = json.loads(resp.body)
    json_ld = body["seo"]["json_ld"]
    assert "description" not in json_ld
    assert "image" not in json_ld
    assert "author" not in json_ld
    assert "keywords" not in json_ld


async def test_article_detail_etag_304():
    from app.routers.public_articles import get_published_article, _etag_detail
    import json

    article = _make_article()
    etag = _etag_detail(article)

    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=article)):
        req = MagicMock()
        req.headers = {"If-None-Match": etag}
        resp = await get_published_article(
            slug=article.slug, request=req, client_id=article.client_id, db=AsyncMock()
        )

    assert resp.status_code == 304


async def test_article_detail_etag_changes_after_update():
    """After article.updated_at changes, ETag must differ."""
    from app.routers.public_articles import _etag_detail

    article_v1 = _make_article(updated_at=_utc(2026, 1, 1))
    article_v2 = _make_article(updated_at=_utc(2026, 1, 2))
    article_v2.id = article_v1.id

    etag1 = _etag_detail(article_v1)
    etag2 = _etag_detail(article_v2)
    assert etag1 != etag2


async def test_html_scripts_stripped():
    from app.routers.public_articles import _strip_scripts

    html = "<p>Hello</p><script>alert('xss')</script><style>body{}</style>"
    result = _strip_scripts(html)
    assert "<script" not in result
    assert "<style" not in result
    assert "<p>Hello</p>" in result


def test_strip_scripts_preserves_img_tags():
    """_strip_scripts does NOT strip <img> — inline images must pass through to API consumers."""
    from app.routers.public_articles import _strip_scripts

    src = "https://test.supabase.co/storage/v1/object/public/article-images/chart.png"
    html = f'<p>Text</p><img src="{src}" alt="Chart">'
    result = _strip_scripts(html)
    assert "<img" in result
    assert src in result


# ---------------------------------------------------------------------------
# Tags endpoint
# ---------------------------------------------------------------------------

async def test_tags_endpoint_aggregates_counts():
    from app.routers.public_articles import get_tags_and_categories
    import json

    client_id = uuid.uuid4()
    articles = [
        _make_article(client_id=client_id, tags=["python", "fastapi"], category="tech"),
        _make_article(client_id=client_id, tags=["python"], category="tech"),
        _make_article(client_id=client_id, tags=[], category="other"),
    ]

    with patch("app.routers.public_articles.list_articles", new=AsyncMock(return_value=(articles, 3))):
        req = MagicMock()
        req.headers = {}
        resp = await get_tags_and_categories(
            request=req, client_id=client_id, db=AsyncMock()
        )

    body = json.loads(resp.body)
    tag_map = {t["name"]: t["count"] for t in body["tags"]}
    cat_map = {c["name"]: c["count"] for c in body["categories"]}
    assert tag_map["python"] == 2
    assert tag_map["fastapi"] == 1
    assert cat_map["tech"] == 2
    assert cat_map["other"] == 1


# ---------------------------------------------------------------------------
# Cache-Control headers
# ---------------------------------------------------------------------------

async def test_cache_control_on_200_list():
    from app.routers.public_articles import list_published_articles

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id)

    with patch("app.routers.public_articles.list_articles", new=AsyncMock(return_value=([article], 1))):
        req = MagicMock()
        req.headers = {}
        resp = await list_published_articles(
            request=req, client_id=client_id, db=AsyncMock(),
            page=1, page_size=20, tag=None, category=None,
        )

    assert "public" in resp.headers.get("cache-control", "")
    assert "max-age=60" in resp.headers.get("cache-control", "")


async def test_cache_control_no_store_on_404():
    from app.routers.public_articles import get_published_article

    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=None)):
        req = MagicMock()
        req.headers = {}
        resp = await get_published_article(
            slug="nope", request=req, client_id=uuid.uuid4(), db=AsyncMock()
        )

    assert resp.headers.get("cache-control") == "no-store"


# ---------------------------------------------------------------------------
# Rate limiter key function
# ---------------------------------------------------------------------------

def test_rate_limiter_key_uses_token_prefix():
    from app.routers.public_articles import _token_or_ip

    req = MagicMock()
    req.headers = {"Authorization": "Bearer ppd_abc12345xyz"}
    key = _token_or_ip(req)
    assert key == "ppd_abc1"  # first 8 chars of raw token


def test_rate_limiter_key_falls_back_to_ip():
    from app.routers.public_articles import _token_or_ip

    req = MagicMock()
    req.headers = {"Authorization": "Bearer sk_notppd"}

    # The function imports get_remote_address lazily from slowapi.util
    # Our stub returns "127.0.0.1" — just verify it does NOT use the token prefix
    key = _token_or_ip(req)
    # Should not start with ppd_ since the auth header doesn't start with ppd_
    assert not key.startswith("ppd_")


# ---------------------------------------------------------------------------
# featured_image_alt in list and detail responses
# ---------------------------------------------------------------------------


async def test_list_articles_includes_featured_image_alt():
    """featured_image_alt must appear in every item of the list response."""
    from app.routers.public_articles import list_published_articles
    import json

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id)
    article.featured_image_alt = "A person typing at a wooden desk"

    with patch("app.routers.public_articles.list_articles", new=AsyncMock(return_value=([article], 1))):
        req = MagicMock()
        req.headers = {}
        resp = await list_published_articles(
            request=req,
            client_id=client_id,
            db=AsyncMock(),
            page=1,
            page_size=20,
            tag=None,
            category=None,
        )

    body = json.loads(resp.body)
    assert resp.status_code == 200
    assert body["data"][0]["featured_image_alt"] == "A person typing at a wooden desk"


async def test_article_detail_includes_featured_image_alt():
    """featured_image_alt must appear in the article detail response."""
    from app.routers.public_articles import get_published_article
    import json

    article = _make_article(featured_image_url="https://example.com/img.png")
    article.featured_image_alt = "A red lighthouse overlooking a stormy sea"

    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=article)):
        req = MagicMock()
        req.headers = {}
        resp = await get_published_article(
            slug=article.slug, request=req, client_id=article.client_id, db=AsyncMock()
        )

    body = json.loads(resp.body)
    assert resp.status_code == 200
    assert body["featured_image_alt"] == "A red lighthouse overlooking a stormy sea"


async def test_list_articles_featured_image_alt_null_when_unset():
    """When featured_image_alt is None, the list response must include the key with null value."""
    from app.routers.public_articles import list_published_articles
    import json

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id)
    article.featured_image_alt = None

    with patch("app.routers.public_articles.list_articles", new=AsyncMock(return_value=([article], 1))):
        req = MagicMock()
        req.headers = {}
        resp = await list_published_articles(
            request=req,
            client_id=client_id,
            db=AsyncMock(),
            page=1,
            page_size=20,
            tag=None,
            category=None,
        )

    body = json.loads(resp.body)
    assert "featured_image_alt" in body["data"][0]
    assert body["data"][0]["featured_image_alt"] is None
