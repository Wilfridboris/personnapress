"""Tests for article management endpoints (routers/articles.py).

Covers:
  - GET /articles  — ownership (404 on wrong owner), empty list
  - GET /articles/{id}  — 404 not found, 404 wrong owner, success
  - PATCH /articles/{id}  — content change triggers update_content, status-only skips
    it, slug conflict 409, slug/status format validation, HTML sanitization
  - GET /articles/{id}/revisions  — list, ownership
  - GET /articles/{id}/revisions/{n}  — detail, 404
  - POST /articles/{id}/revisions/{n}/restore  — calls update_content with source=restore,
    no-op on identical content, 404 revision not found
  - _sanitize_html helper  — strips <script>, <style>, event attrs
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now():
    return datetime(2026, 7, 13, 10, 0, 0, tzinfo=timezone.utc)


def _make_client(user_id=None, client_id=None):
    c = MagicMock()
    c.id = client_id or uuid.uuid4()
    c.user_id = user_id or uuid.uuid4()
    return c


def _make_article(client_id=None, article_id=None, slug="test-article", status="published"):
    a = MagicMock()
    a.id = article_id or uuid.uuid4()
    a.client_id = client_id or uuid.uuid4()
    a.campaign_id = None
    a.slug = slug
    a.title = "Test Article"
    a.html = "<p>Hello world</p>"
    a.excerpt = "A short excerpt."
    a.meta_description = "Meta description"
    a.featured_image_url = None
    a.author = "Boris"
    a.tags = ["python"]
    a.category = "Tech"
    a.status = status
    a.reading_time_minutes = 1
    a.published_at = _now()
    a.created_at = _now()
    a.updated_at = _now()
    return a


def _make_revision(article_id=None, revision_number=1, source="edit"):
    r = MagicMock()
    r.article_id = article_id or uuid.uuid4()
    r.revision_number = revision_number
    r.title = "Test Article"
    r.html = "<p>Hello world</p>"
    r.excerpt = "A short excerpt."
    r.meta_description = "Meta description"
    r.tags = ["python"]
    r.category = "Tech"
    r.author = "Boris"
    r.source = source
    r.created_at = _now()
    return r


def _make_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# _sanitize_html unit tests
# ---------------------------------------------------------------------------


def test_sanitize_html_strips_script():
    """_sanitize_html removes <script> blocks and their content."""
    from app.routers.articles import _sanitize_html

    result = _sanitize_html('<p>Good content</p><script>alert("xss")</script>')
    assert "script" not in result
    assert "Good content" in result


def test_sanitize_html_strips_style():
    """_sanitize_html removes <style> tags."""
    from app.routers.articles import _sanitize_html

    result = _sanitize_html("<p>Text</p><style>body { display: none; }</style>")
    assert "style" not in result
    assert "Text" in result


def test_sanitize_html_strips_event_attributes():
    """_sanitize_html removes on* event attributes from allowed tags."""
    from app.routers.articles import _sanitize_html

    result = _sanitize_html('<p onclick="evil()">Safe text</p>')
    assert "onclick" not in result
    assert "Safe text" in result


def test_sanitize_html_preserves_allowed_tags():
    """_sanitize_html keeps h1-h4, p, ul/ol/li, strong, em, a, br, blockquote, code, pre."""
    from app.routers.articles import _sanitize_html

    safe = "<h2>Title</h2><p><strong>Bold</strong> and <em>italic</em></p>"
    result = _sanitize_html(safe)
    assert "<h2>" in result
    assert "<strong>" in result
    assert "<em>" in result


def test_sanitize_html_strips_iframe():
    """_sanitize_html removes <iframe> (block tag)."""
    from app.routers.articles import _sanitize_html

    result = _sanitize_html('<p>Text</p><iframe src="evil.com"></iframe>')
    assert "iframe" not in result
    assert "Text" in result


# ---------------------------------------------------------------------------
# GET /articles
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_articles_success():
    """User A can list their own client's articles."""
    from app.routers.articles import list_articles_endpoint

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    article = _make_article(client_id=client.id)
    db = _make_db()

    with (
        patch("app.routers.articles.get_client", AsyncMock(return_value=client)),
        patch("app.routers.articles.list_articles", AsyncMock(return_value=([article], 1))),
    ):
        result = await list_articles_endpoint(
            client_id=client.id,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["slug"] == "test-article"


@pytest.mark.asyncio
async def test_list_articles_empty():
    """Returns total=0 and empty items when the client has no articles."""
    from app.routers.articles import list_articles_endpoint

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = _make_db()

    with (
        patch("app.routers.articles.get_client", AsyncMock(return_value=client)),
        patch("app.routers.articles.list_articles", AsyncMock(return_value=([], 0))),
    ):
        result = await list_articles_endpoint(
            client_id=client.id,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result["total"] == 0
    assert result["items"] == []


@pytest.mark.asyncio
async def test_list_articles_404_wrong_owner():
    """User B cannot list user A's client's articles."""
    from app.routers.articles import list_articles_endpoint

    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    client = _make_client(user_id=other_user_id)
    db = _make_db()

    with patch("app.routers.articles.get_client", AsyncMock(return_value=client)):
        with pytest.raises(HTTPException) as exc_info:
            await list_articles_endpoint(
                client_id=client.id,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_list_articles_404_client_not_found():
    """Returns 404 when the client doesn't exist."""
    from app.routers.articles import list_articles_endpoint

    user_id = uuid.uuid4()
    db = _make_db()

    with patch("app.routers.articles.get_client", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc_info:
            await list_articles_endpoint(
                client_id=uuid.uuid4(),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# GET /articles/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_article_success():
    """Returns the article when caller is the owner."""
    from app.routers.articles import get_article_endpoint

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    article = _make_article(client_id=client.id)
    db = _make_db()

    with (
        patch("app.routers.articles.get_article", AsyncMock(return_value=article)),
        patch("app.routers.articles.get_client", AsyncMock(return_value=client)),
    ):
        result = await get_article_endpoint(
            article_id=article.id,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result["slug"] == "test-article"
    assert result["title"] == "Test Article"


@pytest.mark.asyncio
async def test_get_article_404_not_found():
    """Returns 404 ARTICLE_NOT_FOUND when the article doesn't exist."""
    from app.routers.articles import get_article_endpoint

    user_id = uuid.uuid4()
    db = _make_db()

    with patch("app.routers.articles.get_article", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc_info:
            await get_article_endpoint(
                article_id=uuid.uuid4(),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error"]["code"] == "ARTICLE_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_article_404_wrong_owner():
    """User B gets 404 when accessing user A's article (ownership verified via client)."""
    from app.routers.articles import get_article_endpoint

    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    client = _make_client(user_id=other_user_id)
    article = _make_article(client_id=client.id)
    db = _make_db()

    with (
        patch("app.routers.articles.get_article", AsyncMock(return_value=article)),
        patch("app.routers.articles.get_client", AsyncMock(return_value=client)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_article_endpoint(
                article_id=article.id,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error"]["code"] == "ARTICLE_NOT_FOUND"


# ---------------------------------------------------------------------------
# PATCH /articles/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_article_content_change_calls_update_content():
    """PATCH with a title change routes through update_article_content (creates revision)."""
    from app.routers.articles import patch_article_endpoint
    from app.schemas.article import ArticlePatch

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    article = _make_article(client_id=client.id)
    updated = _make_article(client_id=client.id, article_id=article.id)
    updated.title = "Updated Title"
    db = _make_db()

    update_mock = AsyncMock(return_value=updated)

    with (
        patch("app.routers.articles._get_owned_article", AsyncMock(return_value=article)),
        patch("app.routers.articles.update_article_content", update_mock),
        patch("app.routers.articles.set_article_status", AsyncMock(return_value=updated)),
    ):
        result = await patch_article_endpoint(
            article_id=article.id,
            body=ArticlePatch(title="Updated Title"),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    update_mock.assert_called_once()
    _db_arg, _art_arg, fields_arg = update_mock.call_args.args
    source_arg = update_mock.call_args.kwargs.get("source", update_mock.call_args.args[3] if len(update_mock.call_args.args) > 3 else None)
    assert fields_arg.get("title") == "Updated Title"
    assert source_arg == "edit"
    assert result["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_patch_article_status_only_no_revision():
    """PATCH with status only calls set_article_status; update_article_content is NOT called."""
    from app.routers.articles import patch_article_endpoint
    from app.schemas.article import ArticlePatch

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    article = _make_article(client_id=client.id, status="published")
    hidden = _make_article(client_id=client.id, article_id=article.id, status="hidden")
    db = _make_db()

    set_status_mock = AsyncMock(return_value=hidden)
    update_mock = AsyncMock()

    with (
        patch("app.routers.articles._get_owned_article", AsyncMock(return_value=article)),
        patch("app.routers.articles.update_article_content", update_mock),
        patch("app.routers.articles.set_article_status", set_status_mock),
    ):
        result = await patch_article_endpoint(
            article_id=article.id,
            body=ArticlePatch(status="hidden"),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    update_mock.assert_not_called()
    set_status_mock.assert_called_once()
    assert result["status"] == "hidden"


@pytest.mark.asyncio
async def test_patch_article_slug_conflict_409():
    """PATCH with a slug already owned by another article returns 409 SLUG_TAKEN."""
    from app.routers.articles import patch_article_endpoint
    from app.schemas.article import ArticlePatch

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    article = _make_article(client_id=client.id, slug="my-article")
    conflicting = _make_article(client_id=client.id, slug="taken-slug")  # different id
    db = _make_db()

    with (
        patch("app.routers.articles._get_owned_article", AsyncMock(return_value=article)),
        patch("app.routers.articles.get_article_by_slug", AsyncMock(return_value=conflicting)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await patch_article_endpoint(
                article_id=article.id,
                body=ArticlePatch(slug="taken-slug"),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error"]["code"] == "SLUG_TAKEN"


@pytest.mark.asyncio
async def test_patch_article_slug_same_as_current_no_conflict_check():
    """PATCH with the same slug (no change) skips the conflict check and succeeds."""
    from app.routers.articles import patch_article_endpoint
    from app.schemas.article import ArticlePatch

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    article = _make_article(client_id=client.id, slug="my-article")
    db = _make_db()

    slug_lookup_mock = AsyncMock()

    with (
        patch("app.routers.articles._get_owned_article", AsyncMock(return_value=article)),
        patch("app.routers.articles.get_article_by_slug", slug_lookup_mock),
        patch("app.routers.articles.update_article_content", AsyncMock(return_value=article)),
    ):
        await patch_article_endpoint(
            article_id=article.id,
            body=ArticlePatch(slug="my-article"),  # same slug
            current_user={"user_id": str(user_id)},
            db=db,
        )

    slug_lookup_mock.assert_not_called()


def test_article_patch_invalid_slug_format_rejected():
    """ArticlePatch validates slug against ^[a-z0-9]+(?:-[a-z0-9]+)*$."""
    from pydantic import ValidationError
    from app.schemas.article import ArticlePatch

    for bad_slug in ("Invalid Slug!", "-leading-hyphen", "trailing-hyphen-", "UPPER", "double--hyphen"):
        with pytest.raises(ValidationError):
            ArticlePatch(slug=bad_slug)


def test_article_patch_valid_slugs_accepted():
    """ArticlePatch accepts correctly formatted slugs."""
    from app.schemas.article import ArticlePatch

    for good_slug in ("hello", "hello-world", "my-article-123", "a1"):
        body = ArticlePatch(slug=good_slug)
        assert body.slug == good_slug


def test_article_patch_invalid_status_rejected():
    """ArticlePatch rejects status values other than 'published' or 'hidden'."""
    from pydantic import ValidationError
    from app.schemas.article import ArticlePatch

    for bad_status in ("approved", "pending", "draft", "active"):
        with pytest.raises(ValidationError):
            ArticlePatch(status=bad_status)


@pytest.mark.asyncio
async def test_patch_article_html_sanitization_strips_script():
    """Server-side sanitization removes <script> tags before calling update_article_content."""
    from app.routers.articles import patch_article_endpoint
    from app.schemas.article import ArticlePatch

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    article = _make_article(client_id=client.id)
    db = _make_db()

    captured: dict = {}

    async def _capture(db, article, fields, source):
        captured.update(fields)
        return article

    with (
        patch("app.routers.articles._get_owned_article", AsyncMock(return_value=article)),
        patch("app.routers.articles.update_article_content", AsyncMock(side_effect=_capture)),
    ):
        await patch_article_endpoint(
            article_id=article.id,
            body=ArticlePatch(html='<p>Good</p><script>alert("xss")</script>'),
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert "script" not in captured.get("html", "")
    assert "<p>Good</p>" in captured.get("html", "")


# ---------------------------------------------------------------------------
# GET /articles/{id}/revisions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_revisions_success():
    """Returns revisions newest-first for an owned article."""
    from app.routers.articles import list_revisions_endpoint

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    article = _make_article(client_id=client.id)
    rev2 = _make_revision(article_id=article.id, revision_number=2, source="edit")
    rev1 = _make_revision(article_id=article.id, revision_number=1, source="initial")
    db = _make_db()

    with (
        patch("app.routers.articles._get_owned_article", AsyncMock(return_value=article)),
        patch("app.routers.articles.list_revisions", AsyncMock(return_value=[rev2, rev1])),
    ):
        result = await list_revisions_endpoint(
            article_id=article.id,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert len(result["items"]) == 2
    assert result["items"][0]["revision_number"] == 2
    assert result["items"][0]["source"] == "edit"
    assert result["items"][1]["revision_number"] == 1
    assert result["items"][1]["source"] == "initial"


@pytest.mark.asyncio
async def test_list_revisions_404_wrong_owner():
    """_get_owned_article raises 404 when article belongs to another user."""
    from app.routers.articles import list_revisions_endpoint

    user_id = uuid.uuid4()
    db = _make_db()

    with patch(
        "app.routers.articles._get_owned_article",
        AsyncMock(side_effect=HTTPException(
            status_code=404,
            detail={"error": {"code": "ARTICLE_NOT_FOUND", "message": "Not found.", "detail": {}}},
        )),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await list_revisions_endpoint(
                article_id=uuid.uuid4(),
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error"]["code"] == "ARTICLE_NOT_FOUND"


# ---------------------------------------------------------------------------
# GET /articles/{id}/revisions/{n}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_revision_success():
    """Returns full revision detail for an owned article."""
    from app.routers.articles import get_revision_endpoint

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    article = _make_article(client_id=client.id)
    revision = _make_revision(article_id=article.id, revision_number=1, source="initial")
    db = _make_db()

    with (
        patch("app.routers.articles._get_owned_article", AsyncMock(return_value=article)),
        patch("app.routers.articles.get_revision", AsyncMock(return_value=revision)),
    ):
        result = await get_revision_endpoint(
            article_id=article.id,
            revision_number=1,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result["revision_number"] == 1
    assert result["source"] == "initial"
    assert result["html"] == "<p>Hello world</p>"
    assert result["title"] == "Test Article"


@pytest.mark.asyncio
async def test_get_revision_404():
    """Returns 404 REVISION_NOT_FOUND when the revision doesn't exist."""
    from app.routers.articles import get_revision_endpoint

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    article = _make_article(client_id=client.id)
    db = _make_db()

    with (
        patch("app.routers.articles._get_owned_article", AsyncMock(return_value=article)),
        patch("app.routers.articles.get_revision", AsyncMock(return_value=None)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_revision_endpoint(
                article_id=article.id,
                revision_number=99,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error"]["code"] == "REVISION_NOT_FOUND"


# ---------------------------------------------------------------------------
# POST /articles/{id}/revisions/{n}/restore
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_restore_revision_calls_update_content_with_correct_args():
    """Restore calls update_article_content with source='restore' and the revision's content."""
    from app.routers.articles import restore_revision_endpoint

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    article = _make_article(client_id=client.id)
    revision = _make_revision(article_id=article.id, revision_number=1, source="initial")
    revision.title = "Original Title"
    revision.html = "<p>Original content</p>"
    db = _make_db()

    update_mock = AsyncMock(return_value=article)

    with (
        patch("app.routers.articles._get_owned_article", AsyncMock(return_value=article)),
        patch("app.routers.articles.get_revision", AsyncMock(return_value=revision)),
        patch("app.routers.articles.update_article_content", update_mock),
    ):
        result = await restore_revision_endpoint(
            article_id=article.id,
            revision_number=1,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    update_mock.assert_called_once()
    _db_arg, _art_arg, fields_arg = update_mock.call_args.args
    source_arg = update_mock.call_args.kwargs.get("source", update_mock.call_args.args[3] if len(update_mock.call_args.args) > 3 else None)
    assert fields_arg["title"] == "Original Title"
    assert fields_arg["html"] == "<p>Original content</p>"
    assert source_arg == "restore"
    assert "slug" in result  # article returned


@pytest.mark.asyncio
async def test_restore_revision_identical_content_still_calls_update():
    """Restore with content identical to current article still calls update_article_content.

    The repository layer decides whether to create a revision; the endpoint always
    delegates — this tests that the endpoint wires through correctly (repo no-op is
    a separate concern tested in the repository layer).
    """
    from app.routers.articles import restore_revision_endpoint

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    article = _make_article(client_id=client.id)
    revision = _make_revision(article_id=article.id, revision_number=1, source="initial")
    # Make revision content match current article
    revision.title = article.title
    revision.html = article.html
    db = _make_db()

    update_mock = AsyncMock(return_value=article)  # repo returns article unchanged

    with (
        patch("app.routers.articles._get_owned_article", AsyncMock(return_value=article)),
        patch("app.routers.articles.get_revision", AsyncMock(return_value=revision)),
        patch("app.routers.articles.update_article_content", update_mock),
    ):
        result = await restore_revision_endpoint(
            article_id=article.id,
            revision_number=1,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    update_mock.assert_called_once()
    assert result["slug"] == "test-article"


@pytest.mark.asyncio
async def test_restore_revision_404_revision_not_found():
    """Returns 404 REVISION_NOT_FOUND when the specified revision doesn't exist."""
    from app.routers.articles import restore_revision_endpoint

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    article = _make_article(client_id=client.id)
    db = _make_db()

    with (
        patch("app.routers.articles._get_owned_article", AsyncMock(return_value=article)),
        patch("app.routers.articles.get_revision", AsyncMock(return_value=None)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await restore_revision_endpoint(
                article_id=article.id,
                revision_number=99,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error"]["code"] == "REVISION_NOT_FOUND"


@pytest.mark.asyncio
async def test_restore_revision_404_wrong_owner():
    """Returns 404 when the caller does not own the article."""
    from app.routers.articles import restore_revision_endpoint

    user_id = uuid.uuid4()
    db = _make_db()

    with patch(
        "app.routers.articles._get_owned_article",
        AsyncMock(side_effect=HTTPException(
            status_code=404,
            detail={"error": {"code": "ARTICLE_NOT_FOUND", "message": "Not found.", "detail": {}}},
        )),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await restore_revision_endpoint(
                article_id=uuid.uuid4(),
                revision_number=1,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# _sanitize_html — image tag handling
# ---------------------------------------------------------------------------


def test_sanitize_html_keeps_own_bucket_img():
    """_sanitize_html preserves <img> whose src starts with the configured Supabase URL."""
    from app.routers.articles import _sanitize_html
    from app.core.config import settings

    original_url = settings.SUPABASE_URL
    settings.SUPABASE_URL = "https://test.supabase.co"
    try:
        src = "https://test.supabase.co/storage/v1/object/public/article-images/abc.png"
        result = _sanitize_html(f'<p>text</p><img src="{src}" alt="Chart">')
        assert "img" in result
        assert src in result
    finally:
        settings.SUPABASE_URL = original_url


def test_sanitize_html_strips_foreign_img_src():
    """_sanitize_html removes <img> whose src is a foreign URL."""
    from app.routers.articles import _sanitize_html
    from app.core.config import settings

    original_url = settings.SUPABASE_URL
    settings.SUPABASE_URL = "https://test.supabase.co"
    try:
        result = _sanitize_html('<p>text</p><img src="https://evil.com/tracker.png" alt="x">')
        assert "evil.com" not in result
    finally:
        settings.SUPABASE_URL = original_url


def test_sanitize_html_strips_img_onerror_and_srcset():
    """_sanitize_html removes onerror, srcset and style attrs from img tags."""
    from app.routers.articles import _sanitize_html
    from app.core.config import settings

    original_url = settings.SUPABASE_URL
    settings.SUPABASE_URL = "https://test.supabase.co"
    try:
        src = "https://test.supabase.co/storage/v1/object/public/article-images/ok.png"
        result = _sanitize_html(
            f'<img src="{src}" alt="x" onerror="alert(1)" srcset="x.png 2x" style="width:100%">'
        )
        assert "onerror" not in result
        assert "srcset" not in result
        assert "style" not in result
        # src and alt should be preserved
        assert src in result
    finally:
        settings.SUPABASE_URL = original_url


def test_sanitize_html_keeps_figure_and_figcaption():
    """_sanitize_html preserves <figure> and <figcaption> as allowed tags."""
    from app.routers.articles import _sanitize_html
    from app.core.config import settings

    original_url = settings.SUPABASE_URL
    settings.SUPABASE_URL = "https://test.supabase.co"
    try:
        src = "https://test.supabase.co/storage/v1/object/public/article-images/fig.png"
        html = f'<figure><img src="{src}" alt="Chart"><figcaption>Caption here</figcaption></figure>'
        result = _sanitize_html(html)
        assert "figure" in result
        assert "figcaption" in result
        assert "Caption here" in result
    finally:
        settings.SUPABASE_URL = original_url


# ---------------------------------------------------------------------------
# PATCH /articles/{id} — featured_image_url
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_article_featured_image_url_success_no_revision():
    """PATCH featured_image_url updates the field without creating a revision."""
    from app.routers.articles import patch_article_endpoint
    from app.schemas.article import ArticlePatch
    from app.core.config import settings

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    article = _make_article(client_id=client.id)
    db = _make_db()

    original_url = settings.SUPABASE_URL
    settings.SUPABASE_URL = "https://test.supabase.co"
    try:
        own_url = "https://test.supabase.co/storage/v1/object/public/article-images/abc.png"
        update_mock = AsyncMock()

        with (
            patch("app.routers.articles._get_owned_article", AsyncMock(return_value=article)),
            patch("app.routers.articles.update_article_content", update_mock),
        ):
            await patch_article_endpoint(
                article_id=article.id,
                body=ArticlePatch(featured_image_url=own_url),
                current_user={"user_id": str(user_id)},
                db=db,
            )

        # featured_image_url is not a content field — update_article_content must not be called
        update_mock.assert_not_called()
        # The field should be set directly on the article mock
        assert article.featured_image_url == own_url
        db.commit.assert_awaited()
    finally:
        settings.SUPABASE_URL = original_url


def test_patch_article_featured_image_url_foreign_url_rejected():
    """ArticlePatch rejects featured_image_url pointing to a foreign host."""
    from pydantic import ValidationError
    from app.schemas.article import ArticlePatch
    from app.core.config import settings

    original_url = settings.SUPABASE_URL
    settings.SUPABASE_URL = "https://test.supabase.co"
    try:
        with pytest.raises(ValidationError):
            ArticlePatch(featured_image_url="https://evil.com/image.png")
    finally:
        settings.SUPABASE_URL = original_url
