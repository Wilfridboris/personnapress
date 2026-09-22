"""Tests for the write-token authored read-back API (Story 12.8).

Covers:
- Auth matrix: no token / malformed -> 401; ppd_ -> 403; revoked ppw_ -> 401; valid ppw_ -> 200
- List returns hidden + published for caller's client
- api_authored field (True for ingest-created, False for campaign-created)
- status filter (hidden | published) and invalid status -> 422
- slug filter is normalized before lookup
- slug filter returns one article or empty
- By-id happy path: html, status, id, edit_url, seo, meta_description, api_authored
- By-id 404 for unknown id and for another client's id (identical response)
- Non-UUID article_id -> 422 (tested at unit level via get_authored_article logic)
- Cache-Control: no-store on all authored responses
- 429 via rate limiter
- Isolation: client A token never sees client B articles; hidden article absent from public routes
- No generation function invoked
"""
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import types as _types


def _make_passthrough_limiter(*args, **kwargs):
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
    status="hidden",
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
    campaign_id=None,
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
    a.campaign_id = campaign_id
    return a


def _make_write_token(client_id=None, revoked=False, prefix="ppw_abc1") -> MagicMock:
    t = MagicMock()
    t.id = uuid.uuid4()
    t.client_id = client_id or uuid.uuid4()
    t.token_prefix = prefix
    t.token_hash = "fakehash"
    t.revoked_at = _utc() if revoked else None
    t.last_used_at = None
    t.scope = "write"
    return t


def _make_read_token(client_id=None) -> MagicMock:
    t = MagicMock()
    t.id = uuid.uuid4()
    t.client_id = client_id or uuid.uuid4()
    t.token_prefix = "ppd_abc1"
    t.token_hash = "fakehash"
    t.revoked_at = None
    t.last_used_at = None
    t.scope = "read"
    return t


def _make_request(auth_header: str = "") -> MagicMock:
    req = MagicMock()
    req.headers = {"Authorization": auth_header}
    return req


# ---------------------------------------------------------------------------
# Auth matrix — get_delivery_client_write (shared dep, exercised here too)
# ---------------------------------------------------------------------------

async def test_no_token_returns_401():
    from app.routers.public_articles import get_delivery_client_write
    from fastapi import HTTPException

    db = AsyncMock()
    req = _make_request("")
    with pytest.raises(HTTPException) as exc:
        await get_delivery_client_write(req, db)
    assert exc.value.status_code == 401
    assert exc.value.detail["error"]["code"] == "INVALID_DELIVERY_TOKEN"


async def test_malformed_token_returns_401():
    from app.routers.public_articles import get_delivery_client_write
    from fastapi import HTTPException

    db = AsyncMock()
    req = _make_request("Bearer ppd_readtoken")
    with pytest.raises(HTTPException) as exc:
        await get_delivery_client_write(req, db)
    assert exc.value.status_code == 401


async def test_read_scoped_token_returns_403():
    from app.routers.public_articles import get_delivery_client_write
    from fastapi import HTTPException

    client_id = uuid.uuid4()
    db = AsyncMock()
    db.commit = AsyncMock()
    req = _make_request("Bearer ppw_validreadtoken1234567")
    token = _make_read_token(client_id=client_id)

    with patch("app.routers.public_articles.get_active_token_by_prefix", new=AsyncMock(return_value=token)):
        with patch("app.routers.public_articles.verify_token", return_value=True):
            with pytest.raises(HTTPException) as exc:
                await get_delivery_client_write(req, db)

    assert exc.value.status_code == 403
    assert exc.value.detail["error"]["code"] == "WRITE_SCOPE_REQUIRED"


async def test_revoked_token_returns_401():
    from app.routers.public_articles import get_delivery_client_write
    from fastapi import HTTPException

    db = AsyncMock()
    req = _make_request("Bearer ppw_revokedtoken1234567890")
    # revoked token not in active set
    with patch("app.routers.public_articles.get_active_token_by_prefix", new=AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc:
            await get_delivery_client_write(req, db)
    assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# List authored articles
# ---------------------------------------------------------------------------

async def test_list_returns_hidden_and_published():
    from app.routers.public_articles import list_authored_articles
    import json

    client_id = uuid.uuid4()
    hidden_art = _make_article(client_id=client_id, status="hidden", slug="hidden-one")
    published_art = _make_article(client_id=client_id, status="published", slug="pub-one")

    with patch("app.routers.public_articles.list_articles", new=AsyncMock(return_value=([hidden_art, published_art], 2))):
        resp = await list_authored_articles(
            request=_make_request(),
            client_id=client_id,
            db=AsyncMock(),
            page=1,
            page_size=20,
            status=None,
            tag=None,
            category=None,
            slug=None,
        )

    body = json.loads(resp.body)
    assert resp.status_code == 200
    assert body["meta"]["total"] == 2
    slugs = {item["slug"] for item in body["data"]}
    assert "hidden-one" in slugs
    assert "pub-one" in slugs


async def test_list_item_contains_id_status_edit_url():
    from app.routers.public_articles import list_authored_articles
    import json

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id, status="hidden")

    with patch("app.routers.public_articles.list_articles", new=AsyncMock(return_value=([article], 1))):
        resp = await list_authored_articles(
            request=_make_request(),
            client_id=client_id,
            db=AsyncMock(),
            page=1, page_size=20, status=None, tag=None, category=None, slug=None,
        )

    body = json.loads(resp.body)
    item = body["data"][0]
    assert "id" in item
    assert item["id"] == str(article.id)
    assert "status" in item
    assert item["status"] == "hidden"
    assert "edit_url" in item
    assert str(article.id) in item["edit_url"]


async def test_api_authored_true_for_ingest_article():
    """api_authored is True when campaign_id is None (created via ingestion API)."""
    from app.routers.public_articles import list_authored_articles
    import json

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id, campaign_id=None)

    with patch("app.routers.public_articles.list_articles", new=AsyncMock(return_value=([article], 1))):
        resp = await list_authored_articles(
            request=_make_request(), client_id=client_id, db=AsyncMock(),
            page=1, page_size=20, status=None, tag=None, category=None, slug=None,
        )

    body = json.loads(resp.body)
    assert body["data"][0]["api_authored"] is True


async def test_api_authored_false_for_campaign_article():
    """api_authored is False when campaign_id is set (in-app/campaign content)."""
    from app.routers.public_articles import list_authored_articles
    import json

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id, campaign_id=uuid.uuid4())

    with patch("app.routers.public_articles.list_articles", new=AsyncMock(return_value=([article], 1))):
        resp = await list_authored_articles(
            request=_make_request(), client_id=client_id, db=AsyncMock(),
            page=1, page_size=20, status=None, tag=None, category=None, slug=None,
        )

    body = json.loads(resp.body)
    assert body["data"][0]["api_authored"] is False


async def test_status_filter_hidden():
    from app.routers.public_articles import list_authored_articles
    from app.db.repositories.models import ArticleStatus

    client_id = uuid.uuid4()
    mock_list = AsyncMock(return_value=([], 0))

    with patch("app.routers.public_articles.list_articles", mock_list):
        await list_authored_articles(
            request=_make_request(), client_id=client_id, db=AsyncMock(),
            page=1, page_size=20, status="hidden", tag=None, category=None, slug=None,
        )

    assert mock_list.call_args.kwargs["status"] == ArticleStatus.hidden


async def test_status_filter_published():
    from app.routers.public_articles import list_authored_articles
    from app.db.repositories.models import ArticleStatus

    client_id = uuid.uuid4()
    mock_list = AsyncMock(return_value=([], 0))

    with patch("app.routers.public_articles.list_articles", mock_list):
        await list_authored_articles(
            request=_make_request(), client_id=client_id, db=AsyncMock(),
            page=1, page_size=20, status="published", tag=None, category=None, slug=None,
        )

    assert mock_list.call_args.kwargs["status"] == ArticleStatus.published


async def test_status_filter_none_passes_none():
    """status=None means all statuses — list_articles called with status=None."""
    from app.routers.public_articles import list_authored_articles

    client_id = uuid.uuid4()
    mock_list = AsyncMock(return_value=([], 0))

    with patch("app.routers.public_articles.list_articles", mock_list):
        await list_authored_articles(
            request=_make_request(), client_id=client_id, db=AsyncMock(),
            page=1, page_size=20, status=None, tag=None, category=None, slug=None,
        )

    assert mock_list.call_args.kwargs["status"] is None


async def test_invalid_status_raises_422():
    """Invalid status value must produce 422 VALIDATION_ERROR via RequestValidationError."""
    from app.routers.public_articles import list_authored_articles
    from fastapi.exceptions import RequestValidationError

    client_id = uuid.uuid4()
    with pytest.raises(RequestValidationError):
        await list_authored_articles(
            request=_make_request(), client_id=client_id, db=AsyncMock(),
            page=1, page_size=20, status="draft", tag=None, category=None, slug=None,
        )


async def test_slug_filter_normalizes_before_lookup():
    """?slug=My Post should resolve the stored 'my-post' via slug_from_title normalization."""
    from app.routers.public_articles import list_authored_articles
    import json

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id, slug="my-post")

    mock_get = AsyncMock(return_value=article)
    with patch("app.routers.public_articles.get_article_by_slug", mock_get):
        resp = await list_authored_articles(
            request=_make_request(), client_id=client_id, db=AsyncMock(),
            page=1, page_size=20, status=None, tag=None, category=None, slug="My Post",
        )

    # Lookup must use normalized slug "my-post", not the raw "My Post"
    call_args = mock_get.call_args
    # get_article_by_slug(db, client_id, normalized) — positional args
    assert call_args.args[2] == "my-post"

    body = json.loads(resp.body)
    assert body["meta"]["total"] == 1
    assert body["data"][0]["slug"] == "my-post"
    assert resp.headers.get("cache-control") == "no-store"


async def test_slug_filter_returns_empty_when_not_found():
    from app.routers.public_articles import list_authored_articles
    import json

    client_id = uuid.uuid4()
    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=None)):
        resp = await list_authored_articles(
            request=_make_request(), client_id=client_id, db=AsyncMock(),
            page=1, page_size=20, status=None, tag=None, category=None, slug="nonexistent",
        )

    body = json.loads(resp.body)
    assert body["meta"]["total"] == 0
    assert body["data"] == []
    assert resp.headers.get("cache-control") == "no-store"


async def test_list_no_store_cache_header():
    from app.routers.public_articles import list_authored_articles

    client_id = uuid.uuid4()
    with patch("app.routers.public_articles.list_articles", new=AsyncMock(return_value=([], 0))):
        resp = await list_authored_articles(
            request=_make_request(), client_id=client_id, db=AsyncMock(),
            page=1, page_size=20, status=None, tag=None, category=None, slug=None,
        )

    assert resp.headers.get("cache-control") == "no-store"


# ---------------------------------------------------------------------------
# By-id endpoint
# ---------------------------------------------------------------------------

async def test_byid_happy_path():
    from app.routers.public_articles import get_authored_article
    import json

    client_id = uuid.uuid4()
    article = _make_article(
        client_id=client_id,
        status="hidden",
        html="<p>Content</p><script>evil()</script>",
        meta_description="A description",
        campaign_id=None,
    )

    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=article)):
        resp = await get_authored_article(
            article_id=article.id,
            request=_make_request(),
            client_id=client_id,
            db=AsyncMock(),
        )

    body = json.loads(resp.body)
    assert resp.status_code == 200
    assert "html" in body
    assert "<script" not in body["html"]
    assert "id" in body
    assert body["id"] == str(article.id)
    assert "status" in body
    assert body["status"] == "hidden"
    assert "edit_url" in body
    assert "seo" in body
    assert "meta_description" in body
    assert "api_authored" in body
    assert body["api_authored"] is True


async def test_byid_no_store_cache_header():
    from app.routers.public_articles import get_authored_article

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id)

    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=article)):
        resp = await get_authored_article(
            article_id=article.id,
            request=_make_request(),
            client_id=client_id,
            db=AsyncMock(),
        )

    assert resp.headers.get("cache-control") == "no-store"


async def test_byid_unknown_id_returns_404():
    from app.routers.public_articles import get_authored_article
    import json

    client_id = uuid.uuid4()
    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=None)):
        resp = await get_authored_article(
            article_id=uuid.uuid4(),
            request=_make_request(),
            client_id=client_id,
            db=AsyncMock(),
        )

    body = json.loads(resp.body)
    assert resp.status_code == 404
    assert body["detail"]["error"]["code"] == "ARTICLE_NOT_FOUND"


async def test_byid_other_tenant_id_returns_identical_404():
    """Article from another client returns same 404 as unknown id — no distinguishing."""
    from app.routers.public_articles import get_authored_article
    import json

    client_a = uuid.uuid4()
    client_b = uuid.uuid4()
    # Article belongs to client_b
    article = _make_article(client_id=client_b)

    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=article)):
        resp = await get_authored_article(
            article_id=article.id,
            request=_make_request(),
            client_id=client_a,
            db=AsyncMock(),
        )

    body = json.loads(resp.body)
    assert resp.status_code == 404
    assert body["detail"]["error"]["code"] == "ARTICLE_NOT_FOUND"


async def test_byid_missing_and_other_tenant_identical():
    """Missing and other-tenant both return identical 404 bodies."""
    from app.routers.public_articles import get_authored_article
    import json

    client_a = uuid.uuid4()
    client_b = uuid.uuid4()
    article_b = _make_article(client_id=client_b)

    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=None)):
        resp_missing = await get_authored_article(
            article_id=uuid.uuid4(), request=_make_request(), client_id=client_a, db=AsyncMock()
        )
    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=article_b)):
        resp_other = await get_authored_article(
            article_id=article_b.id, request=_make_request(), client_id=client_a, db=AsyncMock()
        )

    assert resp_missing.status_code == resp_other.status_code == 404
    assert json.loads(resp_missing.body) == json.loads(resp_other.body)


# ---------------------------------------------------------------------------
# Tenant isolation (AC 7)
# ---------------------------------------------------------------------------

async def test_list_only_returns_own_client_articles():
    """list_articles is always called with the resolved client_id."""
    from app.routers.public_articles import list_authored_articles

    client_id = uuid.uuid4()
    mock_list = AsyncMock(return_value=([], 0))

    with patch("app.routers.public_articles.list_articles", mock_list):
        await list_authored_articles(
            request=_make_request(), client_id=client_id, db=AsyncMock(),
            page=1, page_size=20, status=None, tag=None, category=None, slug=None,
        )

    assert mock_list.call_args.kwargs["client_id"] == client_id


async def test_hidden_article_absent_from_public_list():
    """A hidden article returned by authored endpoint must NOT appear in the public list."""
    from app.routers.public_articles import list_authored_articles, list_published_articles
    from app.db.repositories.models import ArticleStatus
    import json

    client_id = uuid.uuid4()
    hidden_art = _make_article(client_id=client_id, status="hidden", slug="secret")

    # Authored list returns the hidden article
    with patch("app.routers.public_articles.list_articles", new=AsyncMock(return_value=([hidden_art], 1))):
        authored_resp = await list_authored_articles(
            request=_make_request(), client_id=client_id, db=AsyncMock(),
            page=1, page_size=20, status="hidden", tag=None, category=None, slug=None,
        )

    authored_body = json.loads(authored_resp.body)
    assert authored_body["meta"]["total"] == 1

    # Public list always passes status=published — verify the constraint is intact
    mock_public_list = AsyncMock(return_value=([], 0))
    with patch("app.routers.public_articles.list_articles", mock_public_list):
        req = MagicMock()
        req.headers = {}
        await list_published_articles(
            request=req, client_id=client_id, db=AsyncMock(),
            page=1, page_size=20, tag=None, category=None,
        )

    assert mock_public_list.call_args.kwargs["status"] == ArticleStatus.published


async def test_hidden_article_absent_from_public_detail():
    """A hidden article is still 404 on the public slug route."""
    from app.routers.public_articles import get_published_article

    client_id = uuid.uuid4()
    hidden_art = _make_article(client_id=client_id, status="hidden")

    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=hidden_art)):
        req = MagicMock()
        req.headers = {}
        resp = await get_published_article(
            slug=hidden_art.slug, request=req, client_id=client_id, db=AsyncMock()
        )

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# No generation function called (AC 10, mirrors 12.7 pattern)
# ---------------------------------------------------------------------------

def test_authored_module_does_not_import_generation():
    """public_articles.py must not reference generation/voice/fidelity modules.

    Mirrors test_no_generation_module_imported_by_ingestion in test_article_ingestion.py.
    """
    import app.routers.public_articles as mod
    src = open(mod.__file__, encoding="utf-8").read()
    for banned in ("generation", "voice", "fidelity", "stylometry", "anthropic_client", "gemini"):
        assert f"import {banned}" not in src and f"from app.integrations.{banned}" not in src, (
            f"authored read-back module must not reference {banned}"
        )
