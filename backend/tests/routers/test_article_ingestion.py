"""Tests for the public article ingestion API (POST /public/v1/articles) — Story 12.7.

Covers the write-scope auth matrix, the markdown/html content pipeline (with a
security assertion that <script>/on*/javascript: are stripped), body validation
(413 oversize + 422 branches + unknown field), slug auto-generation, hidden-slug
upsert (200, revision only on change), published-slug 409, tenant isolation, the
absence of ingested articles from every read endpoint, and a hard assertion that
no generation/voice function is ever imported or called during ingest.

Route functions are called directly with mocked repositories, matching the unit
style of test_public_articles.py. slowapi is stubbed so the limiter decorator is
a passthrough.
"""
import json
import sys
import types as _types
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub slowapi (passthrough limiter) — must run before importing public_articles
# ---------------------------------------------------------------------------

def _make_passthrough_limiter(*args, **kwargs):
    lim = MagicMock()
    lim.limit = lambda *a, **kw: (lambda fn: fn)
    return lim

if "slowapi" not in sys.modules or not hasattr(sys.modules.get("slowapi"), "Limiter"):
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


def _make_token(client_id=None, revoked=False, scope="write", prefix="ppw_abc1") -> MagicMock:
    t = MagicMock()
    t.id = uuid.uuid4()
    t.client_id = client_id or uuid.uuid4()
    t.token_prefix = prefix
    t.token_hash = "fakehash"
    t.scope = scope
    t.revoked_at = _utc() if revoked else None
    t.last_used_at = None
    return t


def _make_request(auth_header: str = "", body: bytes = b"{}") -> MagicMock:
    req = MagicMock()
    req.headers = {"Authorization": auth_header} if auth_header else {}
    req.body = AsyncMock(return_value=body)
    return req


def _jbody(**fields) -> bytes:
    return json.dumps(fields).encode()


def _make_article(client_id=None, slug="my-post", status="hidden", html="<p>x</p>") -> MagicMock:
    a = MagicMock()
    a.id = uuid.uuid4()
    a.client_id = client_id or uuid.uuid4()
    a.slug = slug
    a.title = "My Post"
    a.html = html
    a.status = status
    a.created_at = _utc()
    a.updated_at = _utc()
    return a


# A valid write token dependency is normally resolved by get_delivery_client_write.
# For endpoint-body tests we call ingest_article directly and pass client_id, so the
# dependency is bypassed. The auth matrix tests exercise the dependency itself.


# ---------------------------------------------------------------------------
# Auth matrix — get_delivery_client_write
# ---------------------------------------------------------------------------

async def test_write_auth_missing_header_401():
    from app.routers.public_articles import get_delivery_client_write
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await get_delivery_client_write(_make_request(""), AsyncMock())
    assert exc.value.status_code == 401
    assert exc.value.detail["error"]["code"] == "INVALID_DELIVERY_TOKEN"


async def test_write_auth_ppd_prefix_rejected_401_early():
    """A ppd_ (read) token on the write route fails the ppw_ prefix check -> 401."""
    from app.routers.public_articles import get_delivery_client_write
    from fastapi import HTTPException

    req = _make_request("Bearer ppd_somereadtoken1234567890123456789")
    with pytest.raises(HTTPException) as exc:
        await get_delivery_client_write(req, AsyncMock())
    assert exc.value.status_code == 401


async def test_write_auth_read_scope_token_403():
    """A ppw_-prefixed token whose stored scope is 'read' -> 403 WRITE_SCOPE_REQUIRED."""
    from app.routers.public_articles import get_delivery_client_write
    from fastapi import HTTPException

    req = _make_request("Bearer ppw_validlookingtoken12345678901234567")
    token = _make_token(scope="read", prefix="ppw_abc1")

    with patch("app.routers.public_articles.get_active_token_by_prefix", new=AsyncMock(return_value=token)):
        with patch("app.routers.public_articles.verify_token", return_value=True):
            with pytest.raises(HTTPException) as exc:
                await get_delivery_client_write(req, AsyncMock())
    assert exc.value.status_code == 403
    assert exc.value.detail["error"]["code"] == "WRITE_SCOPE_REQUIRED"


async def test_write_auth_revoked_token_401():
    from app.routers.public_articles import get_delivery_client_write
    from fastapi import HTTPException

    req = _make_request("Bearer ppw_validlookingtoken12345678901234567")
    # revoked tokens are filtered out by get_active_token_by_prefix -> None
    with patch("app.routers.public_articles.get_active_token_by_prefix", new=AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc:
            await get_delivery_client_write(req, AsyncMock())
    assert exc.value.status_code == 401


async def test_write_auth_hash_mismatch_401():
    from app.routers.public_articles import get_delivery_client_write
    from fastapi import HTTPException

    req = _make_request("Bearer ppw_validlookingtoken12345678901234567")
    token = _make_token(scope="write")
    with patch("app.routers.public_articles.get_active_token_by_prefix", new=AsyncMock(return_value=token)):
        with patch("app.routers.public_articles.verify_token", return_value=False):
            with pytest.raises(HTTPException) as exc:
                await get_delivery_client_write(req, AsyncMock())
    assert exc.value.status_code == 401


async def test_write_auth_valid_write_token_returns_client_id():
    from app.routers.public_articles import get_delivery_client_write

    client_id = uuid.uuid4()
    db = AsyncMock()
    db.commit = AsyncMock()
    req = _make_request("Bearer ppw_validlookingtoken12345678901234567")
    token = _make_token(client_id=client_id, scope="write")

    with patch("app.routers.public_articles.get_active_token_by_prefix", new=AsyncMock(return_value=token)):
        with patch("app.routers.public_articles.verify_token", return_value=True):
            with patch("app.routers.public_articles.touch_last_used", new=AsyncMock()):
                result = await get_delivery_client_write(req, db)
    assert result == client_id


# ---------------------------------------------------------------------------
# Happy paths — markdown + html create (201)
# ---------------------------------------------------------------------------

def _patch_create(created_article):
    """Context managers that stub the create path repos for ingest_article."""
    return (
        patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=None)),
        patch("app.routers.public_articles._unique_slug", new=AsyncMock(return_value="my-post")),
        patch("app.routers.public_articles.create_article", new=AsyncMock(return_value=created_article)),
    )


async def test_ingest_markdown_creates_hidden_article_201():
    from app.routers.public_articles import ingest_article

    client_id = uuid.uuid4()
    created = _make_article(client_id=client_id, slug="my-post", status="hidden")
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()

    body = _jbody(title="My Post", content="# Hello\n\nSome **bold** text.", format="markdown")
    req = _make_request("Bearer ppw_x", body=body)

    p1, p2, p3 = _patch_create(created)
    with p1, p2, p3:
        resp = await ingest_article(request=req, client_id=client_id, db=db)

    assert resp.status_code == 201
    payload = json.loads(resp.body)
    assert payload["status"] == "hidden"
    assert payload["updated"] is False
    assert payload["slug"] == "my-post"
    assert payload["edit_url"].endswith(f"/articles/{created.id}")
    # An explicit initial revision was added (revision_number=1, source=initial)
    added = [c.args[0] for c in db.add.call_args_list]
    from app.db.repositories.models import ArticleRevision
    revs = [o for o in added if isinstance(o, ArticleRevision)]
    assert len(revs) == 1
    assert revs[0].revision_number == 1
    assert revs[0].source == "initial"


async def test_ingest_html_creates_article_201():
    from app.routers.public_articles import ingest_article

    client_id = uuid.uuid4()
    created = _make_article(client_id=client_id)
    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.flush = AsyncMock()

    body = _jbody(title="My Post", content="<h2>Title</h2><p>Body</p>", format="html")
    req = _make_request("Bearer ppw_x", body=body)

    p1, p2, p3 = _patch_create(created)
    with p1, p2, p3:
        resp = await ingest_article(request=req, client_id=client_id, db=db)
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Sanitization — <script>, on*, javascript: are stripped (security)
# ---------------------------------------------------------------------------

async def test_ingest_strips_script_onclick_and_javascript_href():
    from app.routers.public_articles import ingest_article

    client_id = uuid.uuid4()
    created = _make_article(client_id=client_id)
    captured = {}

    async def _capture_create(session, **fields):
        captured.update(fields)
        return created

    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.flush = AsyncMock()

    dangerous = (
        '<p onclick="steal()">hi</p>'
        '<script>alert(1)</script>'
        '<a href="javascript:alert(2)">bad link</a>'
    )
    body = _jbody(title="XSS Test", content=dangerous, format="html")
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=None)):
        with patch("app.routers.public_articles._unique_slug", new=AsyncMock(return_value="xss-test")):
            with patch("app.routers.public_articles.create_article", new=_capture_create):
                resp = await ingest_article(request=req, client_id=client_id, db=db)

    assert resp.status_code == 201
    stored = captured["html"]
    assert "<script" not in stored.lower()
    assert "onclick" not in stored.lower()
    assert "javascript:" not in stored.lower()


async def test_markdown_raw_html_passthrough_disabled():
    """Raw HTML embedded in Markdown must not be injected verbatim (html=False)."""
    from app.routers.public_articles import ingest_article

    client_id = uuid.uuid4()
    created = _make_article(client_id=client_id)
    captured = {}

    async def _capture_create(session, **fields):
        captured.update(fields)
        return created

    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.flush = AsyncMock()

    body = _jbody(
        title="MD raw html",
        content="Normal <strong>raw</strong> and <script>alert(1)</script>\n",
        format="markdown",
    )
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=None)):
        with patch("app.routers.public_articles._unique_slug", new=AsyncMock(return_value="md-raw-html")):
            with patch("app.routers.public_articles.create_article", new=_capture_create):
                await ingest_article(request=req, client_id=client_id, db=db)

    html = captured["html"]
    assert "<script" not in html.lower()
    # Distinguish html=False from html=True: <strong> IS an allowed tag, so the
    # sanitizer would NOT strip it if the renderer had injected it live. With
    # raw-HTML passthrough disabled, the source tag is emitted as escaped text.
    # If this test only checked <script>, the sanitizer's unconditional
    # script-decompose would let a passthrough regression slip through.
    assert "<strong>raw</strong>" not in html
    assert "&lt;strong&gt;raw&lt;/strong&gt;" in html


# ---------------------------------------------------------------------------
# Validation — 413 oversize, 422 branches, unknown field
# ---------------------------------------------------------------------------

async def test_ingest_oversize_body_413():
    from app.routers.public_articles import ingest_article
    from fastapi import HTTPException

    client_id = uuid.uuid4()
    big = b"x" * (200 * 1024 + 1)
    req = _make_request("Bearer ppw_x", body=big)

    with pytest.raises(HTTPException) as exc:
        await ingest_article(request=req, client_id=client_id, db=AsyncMock())
    assert exc.value.status_code == 413
    assert exc.value.detail["error"]["code"] == "CONTENT_TOO_LARGE"


@pytest.mark.parametrize("body_fields", [
    {"content": "x", "format": "markdown"},                       # missing title
    {"title": "T", "format": "markdown"},                         # missing content
    {"title": "T", "content": "x"},                               # missing format
    {"title": "   ", "content": "x", "format": "markdown"},       # empty title
    {"title": "T", "content": "   ", "format": "markdown"},       # empty content
    {"title": "T", "content": "x", "format": "pdf"},              # bad format
    {"title": "T", "content": "x", "format": "markdown", "slug": "s" * 201},   # slug too long
    {"title": "x" * 301, "content": "x", "format": "markdown"},   # title too long
    {"title": "T", "content": "x", "format": "markdown", "tags": ["ok", "y" * 51]},  # tag too long
    {"title": "T", "content": "x", "format": "markdown", "tags": ["t"] * 21},   # too many tags
    {"title": "T", "content": "x", "format": "markdown", "featured_image_url": "ftp://x/y.png"},  # bad url
    {"title": "T", "content": "x", "format": "markdown", "surprise": "field"},  # unknown field
])
async def test_ingest_validation_errors_422(body_fields):
    """Every validation branch raises RequestValidationError (mapped to 422 VALIDATION_ERROR)."""
    from app.routers.public_articles import ingest_article
    from fastapi.exceptions import RequestValidationError

    client_id = uuid.uuid4()
    req = _make_request("Bearer ppw_x", body=_jbody(**body_fields))

    with pytest.raises(RequestValidationError):
        await ingest_article(request=req, client_id=client_id, db=AsyncMock())


def test_validation_handler_returns_nested_shape():
    """The app-level handler wraps validation errors into the nested VALIDATION_ERROR body."""
    import asyncio
    from fastapi.exceptions import RequestValidationError
    from app.routers.public_articles import _validation_handler

    exc = RequestValidationError([{"loc": ("body", "title"), "msg": "field required", "type": "missing"}])
    resp = asyncio.get_event_loop().run_until_complete(_validation_handler(_make_request(), exc))
    assert resp.status_code == 422
    body = json.loads(resp.body)
    assert body["detail"]["error"]["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# Slug behaviour — auto-generate, hidden upsert (200), published conflict (409)
# ---------------------------------------------------------------------------

async def test_ingest_no_slug_autogenerates_and_creates():
    from app.routers.public_articles import ingest_article

    client_id = uuid.uuid4()
    created = _make_article(client_id=client_id, slug="the-title-2")
    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.flush = AsyncMock()
    unique = AsyncMock(return_value="the-title-2")

    body = _jbody(title="The Title", content="body text", format="markdown")
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles._unique_slug", new=unique):
        with patch("app.routers.public_articles.create_article", new=AsyncMock(return_value=created)):
            resp = await ingest_article(request=req, client_id=client_id, db=db)

    assert resp.status_code == 201
    # _unique_slug was consulted with the base slug derived from the title
    assert unique.await_args.args[2] == "the-title"


async def test_ingest_slug_hidden_upserts_200_with_revision_on_change():
    from app.routers.public_articles import ingest_article

    client_id = uuid.uuid4()
    existing = _make_article(client_id=client_id, slug="existing", status="hidden")
    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.flush = AsyncMock()

    async def _update(session, article, fields, source):
        assert source == "edit"
        return article

    body = _jbody(title="Existing", content="new body", format="markdown", slug="existing")
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=existing)):
        with patch("app.routers.public_articles.update_article_content", new=_update):
            resp = await ingest_article(request=req, client_id=client_id, db=db)

    assert resp.status_code == 200
    payload = json.loads(resp.body)
    assert payload["updated"] is True
    assert payload["status"] == "hidden"


async def test_ingest_slug_hidden_upsert_no_change_returns_200():
    """Re-POSTing identical content to a hidden slug still returns 200 updated=True.

    update_article_content returns the article untouched (no new revision) when
    nothing changed; the endpoint must not crash serialising the response.
    """
    from app.routers.public_articles import ingest_article

    client_id = uuid.uuid4()
    existing = _make_article(client_id=client_id, slug="existing", status="hidden")
    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.flush = AsyncMock()

    async def _update_noop(session, article, fields, source):
        # Simulate the "content identical -> no revision, article returned as-is" path.
        return article

    body = _jbody(title="Existing", content="same body", format="markdown", slug="existing")
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=existing)):
        with patch("app.routers.public_articles.update_article_content", new=_update_noop):
            resp = await ingest_article(request=req, client_id=client_id, db=db)

    assert resp.status_code == 200
    payload = json.loads(resp.body)
    assert payload["updated"] is True


async def test_ingest_slug_published_conflict_409():
    from app.routers.public_articles import ingest_article
    from fastapi import HTTPException

    client_id = uuid.uuid4()
    published = _make_article(client_id=client_id, slug="live-post", status="published")
    db = AsyncMock()

    body = _jbody(title="Live Post", content="body", format="markdown", slug="live-post")
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=published)):
        with pytest.raises(HTTPException) as exc:
            await ingest_article(request=req, client_id=client_id, db=db)
    assert exc.value.status_code == 409
    assert exc.value.detail["error"]["code"] == "SLUG_CONFLICT_PUBLISHED"


# ---------------------------------------------------------------------------
# Tenant isolation — the slug lookup is always scoped by the token's client_id
# ---------------------------------------------------------------------------

async def test_ingest_slug_lookup_scoped_to_token_client():
    """Client A's write token can only look up / upsert within client A's articles."""
    from app.routers.public_articles import ingest_article

    client_a = uuid.uuid4()
    created = _make_article(client_id=client_a, slug="post")
    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.flush = AsyncMock()
    lookup = AsyncMock(return_value=None)

    body = _jbody(title="Post", content="body", format="markdown", slug="post")
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article_by_slug", new=lookup):
        with patch("app.routers.public_articles.create_article", new=AsyncMock(return_value=created)):
            await ingest_article(request=req, client_id=client_a, db=db)

    # The client_id used for the slug lookup is the token's client_id, never a caller value.
    assert lookup.await_args.args[1] == client_a


# ---------------------------------------------------------------------------
# Ingested (hidden) articles never surface on the read endpoints
# ---------------------------------------------------------------------------

async def test_hidden_article_absent_from_read_list():
    from app.routers.public_articles import list_published_articles
    from app.db.repositories.models import ArticleStatus

    client_id = uuid.uuid4()
    mock_list = AsyncMock(return_value=([], 0))
    with patch("app.routers.public_articles.list_articles", mock_list):
        req = MagicMock(); req.headers = {}
        await list_published_articles(
            request=req, client_id=client_id, db=AsyncMock(),
            page=1, page_size=20, tag=None, category=None,
        )
    # Read list is hard-filtered to published — a hidden article can never appear.
    assert mock_list.call_args.kwargs["status"] == ArticleStatus.published


async def test_hidden_article_detail_returns_404():
    from app.routers.public_articles import get_published_article

    client_id = uuid.uuid4()
    hidden = _make_article(client_id=client_id, slug="hidden-one", status="hidden")
    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=hidden)):
        req = MagicMock(); req.headers = {}
        resp = await get_published_article(
            slug="hidden-one", request=req, client_id=client_id, db=AsyncMock(),
        )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# The core guarantee — no generation / voice / fidelity code is invoked
# ---------------------------------------------------------------------------

async def test_no_generation_module_imported_by_ingestion():
    """public_articles must not import generation/voice/fidelity modules."""
    import app.routers.public_articles as mod
    src = open(mod.__file__, encoding="utf-8").read()
    for banned in ("generation", "voice", "fidelity", "stylometry", "anthropic_client", "gemini"):
        assert f"import {banned}" not in src and f"from app.integrations.{banned}" not in src, (
            f"ingestion module must not reference {banned}"
        )


async def test_ingest_does_not_call_generation(monkeypatch):
    """A full markdown create must not touch any LLM/generation call path."""
    from app.routers.public_articles import ingest_article

    client_id = uuid.uuid4()
    created = _make_article(client_id=client_id)
    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.flush = AsyncMock()

    # If any generation service were imported and called, this sentinel would trip.
    import app.services.generation as gen_mod  # noqa: F401  (import to patch if present)

    called = {"hit": False}
    for attr in dir(gen_mod):
        obj = getattr(gen_mod, attr)
        if callable(obj) and not attr.startswith("_"):
            try:
                monkeypatch.setattr(gen_mod, attr, lambda *a, **k: called.__setitem__("hit", True))
            except Exception:
                pass

    body = _jbody(title="Clean", content="# Verbatim\n\nNo transformation.", format="markdown")
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=None)):
        with patch("app.routers.public_articles._unique_slug", new=AsyncMock(return_value="clean")):
            with patch("app.routers.public_articles.create_article", new=AsyncMock(return_value=created)):
                await ingest_article(request=req, client_id=client_id, db=db)

    assert called["hit"] is False


# ---------------------------------------------------------------------------
# House dash rule is NOT applied to ingested content (stored verbatim)
# ---------------------------------------------------------------------------

async def test_ingest_preserves_dashes_verbatim():
    from app.routers.public_articles import ingest_article

    client_id = uuid.uuid4()
    created = _make_article(client_id=client_id)
    captured = {}

    async def _capture_create(session, **fields):
        captured.update(fields)
        return created

    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.flush = AsyncMock()

    body = _jbody(title="Dashes", content="An em-dash — stays and a double dash -- too.", format="html")
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=None)):
        with patch("app.routers.public_articles._unique_slug", new=AsyncMock(return_value="dashes")):
            with patch("app.routers.public_articles.create_article", new=_capture_create):
                await ingest_article(request=req, client_id=client_id, db=db)

    assert "—" in captured["html"]  # em-dash preserved
    assert "--" in captured["html"]      # double dash preserved


# ---------------------------------------------------------------------------
# Story 12.10: Content fidelity — tables, headings, hr, strikethrough (POST)
# ---------------------------------------------------------------------------

async def test_ingest_markdown_pipe_table_produces_table_element():
    """GFM pipe table in markdown -> <table> with thead/tbody/tr/th/td (AC 1)."""
    from app.routers.public_articles import ingest_article

    client_id = uuid.uuid4()
    created = _make_article(client_id=client_id)
    captured = {}

    async def _capture_create(session, **fields):
        captured.update(fields)
        return created

    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.flush = AsyncMock()

    table_md = "| Name | Value |\n| --- | --- |\n| foo | bar |"
    body = _jbody(title="Table", content=table_md, format="markdown")
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=None)):
        with patch("app.routers.public_articles._unique_slug", new=AsyncMock(return_value="table")):
            with patch("app.routers.public_articles.create_article", new=_capture_create):
                await ingest_article(request=req, client_id=client_id, db=db)

    html = captured["html"]
    assert "<table" in html
    assert "<thead" in html
    assert "<tbody" in html
    assert "<tr" in html
    assert "<th" in html
    assert "<td" in html
    # Content is preserved, not flattened to literal text
    assert "Name" in html
    assert "foo" in html


async def test_ingest_markdown_table_alignment_preserved_no_style():
    """Column alignment row -> align attr on cells, no style attr (AC 2)."""
    from app.routers.public_articles import ingest_article

    client_id = uuid.uuid4()
    created = _make_article(client_id=client_id)
    captured = {}

    async def _capture_create(session, **fields):
        captured.update(fields)
        return created

    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.flush = AsyncMock()

    table_md = "| Left | Center | Right |\n| :--- | :---: | ---: |\n| a | b | c |"
    body = _jbody(title="Align", content=table_md, format="markdown")
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=None)):
        with patch("app.routers.public_articles._unique_slug", new=AsyncMock(return_value="align")):
            with patch("app.routers.public_articles.create_article", new=_capture_create):
                await ingest_article(request=req, client_id=client_id, db=db)

    html = captured["html"]
    assert 'align="left"' in html
    assert 'align="center"' in html
    assert 'align="right"' in html
    # style must not survive (it is banned)
    assert "style=" not in html


async def test_ingest_markdown_strikethrough_produces_s_element():
    """~~text~~ in markdown -> <s>text</s> (AC 3)."""
    from app.routers.public_articles import ingest_article

    client_id = uuid.uuid4()
    created = _make_article(client_id=client_id)
    captured = {}

    async def _capture_create(session, **fields):
        captured.update(fields)
        return created

    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.flush = AsyncMock()

    body = _jbody(title="Strike", content="This is ~~crossed out~~ text.", format="markdown")
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=None)):
        with patch("app.routers.public_articles._unique_slug", new=AsyncMock(return_value="strike")):
            with patch("app.routers.public_articles.create_article", new=_capture_create):
                await ingest_article(request=req, client_id=client_id, db=db)

    html = captured["html"]
    assert "<s>" in html
    assert "crossed out" in html


async def test_ingest_html_table_h5_h6_hr_s_del_preserved():
    """format:html with new elements -> all survive sanitization (AC 4)."""
    from app.routers.public_articles import ingest_article

    client_id = uuid.uuid4()
    created = _make_article(client_id=client_id)
    captured = {}

    async def _capture_create(session, **fields):
        captured.update(fields)
        return created

    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.flush = AsyncMock()

    content = (
        "<table><thead><tr><th>A</th></tr></thead>"
        "<tbody><tr><td>B</td></tr></tbody></table>"
        "<h5>Sub-sub heading</h5>"
        "<h6>Deepest heading</h6>"
        "<hr>"
        "<s>struck</s>"
        "<del>deleted</del>"
    )
    body = _jbody(title="All new tags", content=content, format="html")
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=None)):
        with patch("app.routers.public_articles._unique_slug", new=AsyncMock(return_value="new-tags")):
            with patch("app.routers.public_articles.create_article", new=_capture_create):
                await ingest_article(request=req, client_id=client_id, db=db)

    html = captured["html"]
    assert "<table" in html
    assert "<th>" in html
    assert "<td>" in html
    assert "<h5>" in html
    assert "<h6>" in html
    assert "<hr" in html
    assert "<s>" in html
    assert "<del>" in html


async def test_ingest_table_security_style_and_event_stripped():
    """style and event attrs on table cells are stripped; script inside td is decomposed (AC 5)."""
    from app.routers.public_articles import ingest_article

    client_id = uuid.uuid4()
    created = _make_article(client_id=client_id)
    captured = {}

    async def _capture_create(session, **fields):
        captured.update(fields)
        return created

    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.flush = AsyncMock()

    content = (
        '<table><tbody>'
        '<tr><td style="color:red" onmouseover="evil()">A</td></tr>'
        '<tr><td><script>alert(1)</script>safe</td></tr>'
        '</tbody></table>'
    )
    body = _jbody(title="Security", content=content, format="html")
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=None)):
        with patch("app.routers.public_articles._unique_slug", new=AsyncMock(return_value="security")):
            with patch("app.routers.public_articles.create_article", new=_capture_create):
                await ingest_article(request=req, client_id=client_id, db=db)

    html = captured["html"]
    assert "style=" not in html
    assert "onmouseover" not in html
    assert "<script" not in html.lower()
    # The table itself and its text content survive
    assert "<table" in html
    assert "safe" in html


async def test_ingest_markdown_task_list_no_input_element():
    """Task-list Markdown must not produce <input> elements (AC 6 narrowly)."""
    from app.routers.public_articles import ingest_article

    client_id = uuid.uuid4()
    created = _make_article(client_id=client_id)
    captured = {}

    async def _capture_create(session, **fields):
        captured.update(fields)
        return created

    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.flush = AsyncMock()

    body = _jbody(title="Tasks", content="- [ ] todo item\n- [x] done item", format="markdown")
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=None)):
        with patch("app.routers.public_articles._unique_slug", new=AsyncMock(return_value="tasks")):
            with patch("app.routers.public_articles.create_article", new=_capture_create):
                await ingest_article(request=req, client_id=client_id, db=db)

    html = captured["html"]
    assert "<input" not in html.lower()
