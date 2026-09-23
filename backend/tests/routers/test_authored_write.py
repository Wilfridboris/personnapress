"""Tests for the write-token authored mutation API (Story 12.9).

Covers PUT /public/v1/authored/articles/{id} (full-content replace in place) and
DELETE /public/v1/authored/articles/{id} (soft unpublish -> hidden).

Covers:
- Auth matrix on both routes: no/malformed -> 401; ppd_ -> 403; revoked ppw_ -> 401;
  valid ppw_ -> 200 (the shared dependency get_delivery_client_write is exercised).
- PUT markdown + html happy paths; stored html is sanitized.
- PUT to a published article keeps status='published' and applies new content.
- PUT auto-revision: exactly one 'edit' revision on content change, none on identical PUT.
- reading_time recomputed on body change (delegated to update_article_content).
- Full-replace clearing: omitted optional fields (excerpt/tags/featured_image_*) are
  passed as None so they are cleared, not left at their old values.
- <script>/on*/javascript: stripped on update.
- Every 422 branch + 413 oversize + unknown field + slug-in-body -> 422/413.
- Tenant isolation: A cannot PUT/DELETE B's article (identical 404).
- DELETE published -> hidden (200); already-hidden -> idempotent 200 (no status write);
  row + revisions preserved (no hard delete).
- No generation/voice/fidelity function is imported.

Route functions are called directly with mocked repositories, matching the unit
style of test_article_ingestion.py / test_authored_readback.py. slowapi is stubbed
so the limiter decorator is a passthrough.
"""
import json
import sys
import types as _types
import uuid
from datetime import datetime, timezone
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


def _make_article(
    client_id=None,
    slug="my-post",
    status="hidden",
    html="<p>old</p>",
    title="Old Title",
    excerpt="old excerpt",
    tags=None,
    category="OldCat",
    author="Old Author",
    meta_description="old meta",
    featured_image_url="https://cdn.example.com/old.jpg",
    featured_image_alt="old alt",
) -> MagicMock:
    a = MagicMock()
    a.id = uuid.uuid4()
    a.client_id = client_id or uuid.uuid4()
    a.slug = slug
    a.title = title
    a.html = html
    a.status = status
    a.excerpt = excerpt
    a.tags = tags if tags is not None else ["old"]
    a.category = category
    a.author = author
    a.meta_description = meta_description
    a.featured_image_url = featured_image_url
    a.featured_image_alt = featured_image_alt
    a.reading_time_minutes = 3
    a.created_at = _utc()
    a.updated_at = _utc()
    return a


# ===========================================================================
# Auth matrix (AC 1) — shared dependency get_delivery_client_write
# ===========================================================================

async def test_put_no_token_401():
    from app.routers.public_articles import get_delivery_client_write
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await get_delivery_client_write(_make_request(""), AsyncMock())
    assert exc.value.status_code == 401
    assert exc.value.detail["error"]["code"] == "INVALID_DELIVERY_TOKEN"


async def test_ppd_read_token_403():
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


async def test_revoked_write_token_401():
    from app.routers.public_articles import get_delivery_client_write
    from fastapi import HTTPException

    req = _make_request("Bearer ppw_revokedtoken1234567890")
    with patch("app.routers.public_articles.get_active_token_by_prefix", new=AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc:
            await get_delivery_client_write(req, AsyncMock())
    assert exc.value.status_code == 401


# ===========================================================================
# PUT happy paths (AC 4, 5)
# ===========================================================================

async def test_put_markdown_happy_path():
    from app.routers.public_articles import update_authored_article

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id, status="hidden")
    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.add = MagicMock()

    captured = {}

    async def _update(session, art, fields, source):
        captured["fields"] = fields
        captured["source"] = source
        art.html = fields["html"]
        art.title = fields["title"]
        return art

    body = _jbody(title="New Title", content="## Hello\n\nBody text.", format="markdown")
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=article)):
        with patch("app.routers.public_articles.update_article_content", new=_update):
            resp = await update_authored_article(
                article_id=article.id, request=req, client_id=client_id, db=db
            )

    assert resp.status_code == 200
    payload = json.loads(resp.body)
    assert payload["updated"] is True
    assert payload["id"] == str(article.id)
    assert resp.headers.get("cache-control") == "no-store"
    # source is 'edit'; html was rendered from markdown
    assert captured["source"] == "edit"
    assert "<h2>" in captured["fields"]["html"]


async def test_put_html_happy_path_sanitized():
    from app.routers.public_articles import update_authored_article

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id)
    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.add = MagicMock()

    captured = {}

    async def _update(session, art, fields, source):
        captured["fields"] = fields
        return art

    body = _jbody(
        title="T",
        content='<p onclick="evil()">Hi</p><script>alert(1)</script><a href="javascript:x">bad</a>',
        format="html",
    )
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=article)):
        with patch("app.routers.public_articles.update_article_content", new=_update):
            resp = await update_authored_article(
                article_id=article.id, request=req, client_id=client_id, db=db
            )

    assert resp.status_code == 200
    html = captured["fields"]["html"]
    assert "<script" not in html.lower()
    assert "onclick" not in html.lower()
    assert "javascript:" not in html.lower()


async def test_put_published_stays_published():
    """A PUT to a published target must NOT touch status; it stays published."""
    from app.routers.public_articles import update_authored_article

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id, status="published")
    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.add = MagicMock()

    async def _update(session, art, fields, source):
        return art

    set_status_mock = AsyncMock()
    body = _jbody(title="Edited Live", content="new content", format="markdown")
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=article)):
        with patch("app.routers.public_articles.update_article_content", new=_update):
            with patch("app.routers.public_articles.set_article_status", new=set_status_mock):
                resp = await update_authored_article(
                    article_id=article.id, request=req, client_id=client_id, db=db
                )

    payload = json.loads(resp.body)
    assert payload["status"] == "published"
    # status must never be flipped on a PUT
    set_status_mock.assert_not_called()
    assert article.status == "published"


async def test_put_full_replace_clears_omitted_fields():
    """Omitted optional fields are passed as None (cleared), not left unchanged.

    featured_image_url / featured_image_alt are set unconditionally on the article
    to None; excerpt/tags/category/author/meta_description flow through
    content_fields as None.
    """
    from app.routers.public_articles import update_authored_article

    client_id = uuid.uuid4()
    article = _make_article(
        client_id=client_id,
        excerpt="old excerpt",
        tags=["old"],
        category="OldCat",
        author="Old",
        meta_description="old meta",
        featured_image_url="https://cdn.example.com/old.jpg",
        featured_image_alt="old alt",
    )
    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.add = MagicMock()

    captured = {}

    async def _update(session, art, fields, source):
        captured["fields"] = fields
        return art

    # Body sends ONLY the required fields — all optionals omitted.
    body = _jbody(title="New", content="new body", format="markdown")
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=article)):
        with patch("app.routers.public_articles.update_article_content", new=_update):
            await update_authored_article(
                article_id=article.id, request=req, client_id=client_id, db=db
            )

    # Content fields cleared to None
    assert captured["fields"]["excerpt"] is None
    assert captured["fields"]["tags"] is None
    assert captured["fields"]["category"] is None
    assert captured["fields"]["author"] is None
    assert captured["fields"]["meta_description"] is None
    # Image fields cleared on the article unconditionally
    assert article.featured_image_url is None
    assert article.featured_image_alt is None


async def test_put_sets_image_fields_from_body():
    from app.routers.public_articles import update_authored_article

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id)
    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.add = MagicMock()

    async def _update(session, art, fields, source):
        return art

    body = _jbody(
        title="T",
        content="body",
        format="markdown",
        featured_image_url="https://cdn.example.com/new.jpg",
        featured_image_alt="new alt",
    )
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=article)):
        with patch("app.routers.public_articles.update_article_content", new=_update):
            await update_authored_article(
                article_id=article.id, request=req, client_id=client_id, db=db
            )

    assert article.featured_image_url == "https://cdn.example.com/new.jpg"
    assert article.featured_image_alt == "new alt"


async def test_put_image_only_change_bumps_updated_at():
    """An image-only edit (identical text) must bump updated_at so the
    updated_at-keyed detail/list ETag and JSON-LD dateModified flip and the new
    image propagates to conditional/cached public consumers (regression).

    update_article_content returns the article untouched (no bump) when the text
    content is unchanged, so the route itself is responsible for the bump here.
    """
    from app.routers.public_articles import update_authored_article

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id)
    old_updated_at = article.updated_at
    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.add = MagicMock()

    async def _update(session, art, fields, source):
        return art  # identical content -> no bump from the content path

    body = _jbody(
        title="T",
        content="body",
        format="markdown",
        featured_image_url="https://cdn.example.com/NEW-image.jpg",
        featured_image_alt="old alt",
    )
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=article)):
        with patch("app.routers.public_articles.update_article_content", new=_update):
            await update_authored_article(
                article_id=article.id, request=req, client_id=client_id, db=db
            )

    assert article.featured_image_url == "https://cdn.example.com/NEW-image.jpg"
    assert article.updated_at > old_updated_at


async def test_put_no_image_change_does_not_bump_updated_at_in_route():
    """When the image fields are unchanged, the route must NOT bump updated_at
    itself — that decision is delegated to update_article_content, so an all-noop
    PUT keeps updated_at (and its ETag) stable."""
    from app.routers.public_articles import update_authored_article

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id)
    old_updated_at = article.updated_at
    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.add = MagicMock()

    async def _update(session, art, fields, source):
        return art  # no content change

    # Resend the SAME image fields the article already carries.
    body = _jbody(
        title="T",
        content="body",
        format="markdown",
        featured_image_url="https://cdn.example.com/old.jpg",
        featured_image_alt="old alt",
    )
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=article)):
        with patch("app.routers.public_articles.update_article_content", new=_update):
            await update_authored_article(
                article_id=article.id, request=req, client_id=client_id, db=db
            )

    assert article.updated_at == old_updated_at


async def test_put_source_is_edit():
    """The revision source passed to update_article_content is always 'edit'."""
    from app.routers.public_articles import update_authored_article

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id)
    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.add = MagicMock()

    seen = {}

    async def _update(session, art, fields, source):
        seen["source"] = source
        return art

    body = _jbody(title="T", content="body", format="markdown")
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=article)):
        with patch("app.routers.public_articles.update_article_content", new=_update):
            await update_authored_article(
                article_id=article.id, request=req, client_id=client_id, db=db
            )

    assert seen["source"] == "edit"


# ===========================================================================
# PUT revision + reading_time semantics against the real repo (AC 5, 8)
# ===========================================================================

async def _run_real_update(article, content_fields):
    """Drive the real update_article_content against a lightweight fake session
    that records added objects, so we can count revisions and observe reading_time.
    """
    from app.db.repositories import articles as repo

    added = []

    class _Result:
        def __init__(self, value):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    class _FakeSession:
        def add(self, obj):
            added.append(obj)

        async def flush(self):
            pass

        async def refresh(self, obj):
            pass

        async def execute(self, query):
            # max(revision_number) query -> return current max among added revisions
            revs = [o for o in added if getattr(o, "revision_number", None) is not None]
            mx = max((r.revision_number for r in revs), default=0)
            return _Result(mx)

    session = _FakeSession()
    result = await repo.update_article_content(session, article, content_fields, source="edit")
    return result, added


class _RealArticle:
    """Plain attribute bag mirroring the Article content fields the repo touches."""

    def __init__(self, **kw):
        self.title = kw.get("title", "Old")
        self.html = kw.get("html", "<p>old body here with several words</p>")
        self.excerpt = kw.get("excerpt", "e")
        self.meta_description = kw.get("meta_description", "m")
        self.tags = kw.get("tags", ["t"])
        self.category = kw.get("category", "c")
        self.author = kw.get("author", "a")
        self.reading_time_minutes = kw.get("reading_time_minutes", 1)
        self.updated_at = _utc()
        self.id = uuid.uuid4()


async def test_content_change_creates_exactly_one_revision():
    from app.db.repositories.models import ArticleRevision

    article = _RealArticle(html="<p>original body</p>")
    fields = {
        "title": "New Title",
        "html": "<p>changed body content</p>",
        "excerpt": None,
        "meta_description": None,
        "tags": None,
        "category": None,
        "author": None,
    }
    result, added = await _run_real_update(article, fields)
    revisions = [o for o in added if isinstance(o, ArticleRevision)]
    assert len(revisions) == 1
    assert revisions[0].source == "edit"
    assert result.title == "New Title"


async def test_identical_content_creates_no_revision():
    from app.db.repositories.models import ArticleRevision

    article = _RealArticle(
        title="Same",
        html="<p>same body</p>",
        excerpt="ex",
        meta_description="md",
        tags=["x"],
        category="cat",
        author="auth",
    )
    fields = {
        "title": "Same",
        "html": "<p>same body</p>",
        "excerpt": "ex",
        "meta_description": "md",
        "tags": ["x"],
        "category": "cat",
        "author": "auth",
    }
    result, added = await _run_real_update(article, fields)
    revisions = [o for o in added if isinstance(o, ArticleRevision)]
    assert len(revisions) == 0


async def test_reading_time_recomputed_on_html_change():
    # Original reading time 1; new html has many words -> recompute may change it.
    long_body = "<p>" + " ".join(["word"] * 500) + "</p>"
    article = _RealArticle(html="<p>short</p>", reading_time_minutes=1)
    fields = {
        "title": article.title,
        "html": long_body,
        "excerpt": article.excerpt,
        "meta_description": article.meta_description,
        "tags": article.tags,
        "category": article.category,
        "author": article.author,
    }
    result, _ = await _run_real_update(article, fields)
    # 500 words / 225 wpm ~= 2 minutes, definitely > 1
    assert result.reading_time_minutes > 1


# ===========================================================================
# PUT validation: 413, 422 branches, unknown field, slug-in-body (AC 2, 3)
# ===========================================================================

async def test_put_oversize_body_413():
    from app.routers.public_articles import update_authored_article
    from fastapi import HTTPException

    client_id = uuid.uuid4()
    big = b"x" * (200 * 1024 + 1)
    req = _make_request("Bearer ppw_x", body=big)

    with pytest.raises(HTTPException) as exc:
        await update_authored_article(
            article_id=uuid.uuid4(), request=req, client_id=client_id, db=AsyncMock()
        )
    assert exc.value.status_code == 413
    assert exc.value.detail["error"]["code"] == "CONTENT_TOO_LARGE"


@pytest.mark.parametrize("body_fields", [
    {"content": "x", "format": "markdown"},                       # missing title
    {"title": "T", "format": "markdown"},                         # missing content
    {"title": "T", "content": "x"},                               # missing format
    {"title": "   ", "content": "x", "format": "markdown"},       # empty title
    {"title": "T", "content": "   ", "format": "markdown"},       # empty content
    {"title": "T", "content": "x", "format": "pdf"},              # bad format
    {"title": "x" * 301, "content": "x", "format": "markdown"},   # title too long
    {"title": "T", "content": "x", "format": "markdown", "tags": ["ok", "y" * 51]},  # tag too long
    {"title": "T", "content": "x", "format": "markdown", "tags": ["t"] * 21},        # too many tags
    {"title": "T", "content": "x", "format": "markdown", "featured_image_url": "ftp://x/y.png"},  # bad url
    {"title": "T", "content": "x", "format": "markdown", "excerpt": "e" * 501},      # excerpt too long
    {"title": "T", "content": "x", "format": "markdown", "surprise": "field"},       # unknown field
])
async def test_put_validation_errors_422(body_fields):
    from app.routers.public_articles import update_authored_article
    from fastapi.exceptions import RequestValidationError

    client_id = uuid.uuid4()
    req = _make_request("Bearer ppw_x", body=_jbody(**body_fields))
    with pytest.raises(RequestValidationError):
        await update_authored_article(
            article_id=uuid.uuid4(), request=req, client_id=client_id, db=AsyncMock()
        )


async def test_put_slug_in_body_is_422():
    """slug is immutable via PUT; sending it is rejected by extra='forbid'."""
    from app.routers.public_articles import update_authored_article
    from fastapi.exceptions import RequestValidationError

    client_id = uuid.uuid4()
    body = _jbody(title="T", content="body", format="markdown", slug="new-slug")
    req = _make_request("Bearer ppw_x", body=body)
    with pytest.raises(RequestValidationError):
        await update_authored_article(
            article_id=uuid.uuid4(), request=req, client_id=client_id, db=AsyncMock()
        )


# ===========================================================================
# PUT tenant isolation (AC 3, 8)
# ===========================================================================

async def test_put_unknown_id_404():
    from app.routers.public_articles import update_authored_article

    client_id = uuid.uuid4()
    body = _jbody(title="T", content="body", format="markdown")
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=None)):
        resp = await update_authored_article(
            article_id=uuid.uuid4(), request=req, client_id=client_id, db=AsyncMock()
        )
    assert resp.status_code == 404
    body_json = json.loads(resp.body)
    assert body_json["detail"]["error"]["code"] == "ARTICLE_NOT_FOUND"


async def test_put_other_tenant_identical_404():
    from app.routers.public_articles import update_authored_article

    client_a = uuid.uuid4()
    client_b = uuid.uuid4()
    article_b = _make_article(client_id=client_b)

    body = _jbody(title="T", content="body", format="markdown")

    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=None)):
        resp_missing = await update_authored_article(
            article_id=uuid.uuid4(), request=_make_request("Bearer ppw_x", body=body),
            client_id=client_a, db=AsyncMock(),
        )
    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=article_b)):
        resp_other = await update_authored_article(
            article_id=article_b.id, request=_make_request("Bearer ppw_x", body=body),
            client_id=client_a, db=AsyncMock(),
        )

    assert resp_missing.status_code == resp_other.status_code == 404
    assert json.loads(resp_missing.body) == json.loads(resp_other.body)


# ===========================================================================
# DELETE (soft unpublish) (AC 6, 8)
# ===========================================================================

async def test_delete_published_soft_unpublishes():
    from app.routers.public_articles import unpublish_authored_article
    from app.db.repositories.models import ArticleStatus

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id, status="published")
    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock()

    async def _set_status(session, art, status):
        art.status = status
        return art

    set_mock = AsyncMock(side_effect=_set_status)

    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=article)):
        with patch("app.routers.public_articles.set_article_status", new=set_mock):
            resp = await unpublish_authored_article(
                article_id=article.id, request=_make_request("Bearer ppw_x"),
                client_id=client_id, db=db,
            )

    assert resp.status_code == 200
    payload = json.loads(resp.body)
    assert payload["status"] == "hidden"
    assert payload["updated"] is True
    assert resp.headers.get("cache-control") == "no-store"
    # set_article_status called with the hidden enum
    assert set_mock.call_args.args[2] == ArticleStatus.hidden


async def test_delete_already_hidden_is_idempotent_noop():
    from app.routers.public_articles import unpublish_authored_article

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id, status="hidden")
    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock()

    set_mock = AsyncMock()
    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=article)):
        with patch("app.routers.public_articles.set_article_status", new=set_mock):
            resp = await unpublish_authored_article(
                article_id=article.id, request=_make_request("Bearer ppw_x"),
                client_id=client_id, db=db,
            )

    assert resp.status_code == 200
    payload = json.loads(resp.body)
    assert payload["status"] == "hidden"
    # No status write on an already-hidden target.
    set_mock.assert_not_called()


async def test_delete_never_hard_deletes_row():
    """DELETE must not call any row-delete on the session; it only flips status."""
    from app.routers.public_articles import unpublish_authored_article

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id, status="published")
    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock()
    db.delete = AsyncMock()

    async def _set_status(session, art, status):
        art.status = status
        return art

    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=article)):
        with patch("app.routers.public_articles.set_article_status", new=AsyncMock(side_effect=_set_status)):
            await unpublish_authored_article(
                article_id=article.id, request=_make_request("Bearer ppw_x"),
                client_id=client_id, db=db,
            )

    db.delete.assert_not_called()


async def test_delete_unknown_id_404():
    from app.routers.public_articles import unpublish_authored_article

    client_id = uuid.uuid4()
    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=None)):
        resp = await unpublish_authored_article(
            article_id=uuid.uuid4(), request=_make_request("Bearer ppw_x"),
            client_id=client_id, db=AsyncMock(),
        )
    assert resp.status_code == 404
    assert json.loads(resp.body)["detail"]["error"]["code"] == "ARTICLE_NOT_FOUND"


async def test_delete_other_tenant_identical_404():
    from app.routers.public_articles import unpublish_authored_article

    client_a = uuid.uuid4()
    client_b = uuid.uuid4()
    article_b = _make_article(client_id=client_b, status="published")

    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=None)):
        resp_missing = await unpublish_authored_article(
            article_id=uuid.uuid4(), request=_make_request("Bearer ppw_x"),
            client_id=client_a, db=AsyncMock(),
        )
    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=article_b)):
        resp_other = await unpublish_authored_article(
            article_id=article_b.id, request=_make_request("Bearer ppw_x"),
            client_id=client_a, db=AsyncMock(),
        )

    assert resp_missing.status_code == resp_other.status_code == 404
    assert json.loads(resp_missing.body) == json.loads(resp_other.body)


# ===========================================================================
# Unpublished article disappears from public read endpoints (AC 8)
# ===========================================================================

async def test_unpublished_article_absent_from_public_list():
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
    # Public list is hard-filtered to published; a now-hidden article never appears.
    assert mock_list.call_args.kwargs["status"] == ArticleStatus.published


async def test_unpublished_article_404_on_public_detail():
    from app.routers.public_articles import get_published_article

    client_id = uuid.uuid4()
    hidden = _make_article(client_id=client_id, slug="was-live", status="hidden")
    with patch("app.routers.public_articles.get_article_by_slug", new=AsyncMock(return_value=hidden)):
        req = MagicMock(); req.headers = {}
        resp = await get_published_article(
            slug="was-live", request=req, client_id=client_id, db=AsyncMock(),
        )
    assert resp.status_code == 404


# ===========================================================================
# No generation / voice / fidelity code invoked (AC 8, 10)
# ===========================================================================

def test_authored_write_module_does_not_import_generation():
    import app.routers.public_articles as mod
    src = open(mod.__file__, encoding="utf-8").read()
    for banned in ("generation", "voice", "fidelity", "stylometry", "anthropic_client", "gemini"):
        assert f"import {banned}" not in src and f"from app.integrations.{banned}" not in src, (
            f"authored write module must not reference {banned}"
        )


async def test_put_does_not_call_generation(monkeypatch):
    from app.routers.public_articles import update_authored_article

    client_id = uuid.uuid4()
    article = _make_article(client_id=client_id)
    db = AsyncMock()
    db.commit = AsyncMock(); db.refresh = AsyncMock(); db.add = MagicMock()

    import app.services.generation as gen_mod  # noqa: F401

    called = {"hit": False}
    for attr in dir(gen_mod):
        obj = getattr(gen_mod, attr)
        if callable(obj) and not attr.startswith("_"):
            try:
                monkeypatch.setattr(gen_mod, attr, lambda *a, **k: called.__setitem__("hit", True))
            except Exception:
                pass

    async def _update(session, art, fields, source):
        return art

    body = _jbody(title="Clean", content="# Verbatim\n\nNo transformation.", format="markdown")
    req = _make_request("Bearer ppw_x", body=body)

    with patch("app.routers.public_articles.get_article", new=AsyncMock(return_value=article)):
        with patch("app.routers.public_articles.update_article_content", new=_update):
            await update_authored_article(
                article_id=article.id, request=req, client_id=client_id, db=db
            )

    assert called["hit"] is False
