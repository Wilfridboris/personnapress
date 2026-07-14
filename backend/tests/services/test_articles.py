"""Tests for services/articles.py — article creation from campaigns."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


_DEFAULT_HTML = "<h1>My Title</h1><p>Body content here.</p>"


def _make_campaign(blog_html=_DEFAULT_HTML, brain_dump="Default brain dump text", voice_score=None, image_url=None):
    c = MagicMock()
    c.id = uuid.uuid4()
    c.client_id = uuid.uuid4()
    c.blog_html = blog_html
    c.brain_dump = brain_dump
    c.voice_score = voice_score
    c.image_url = image_url
    return c


async def _run_create(campaign, existing_article=None, existing_slugs=None):
    """Helper: runs create_or_update_article_from_campaign with session mocked."""
    from app.services.articles import create_or_update_article_from_campaign

    session = AsyncMock()

    # Mock the campaign_id existence check
    existing_check = MagicMock()
    existing_check.scalar_one_or_none.return_value = existing_article

    # Mock slug query (returns empty by default, or provided slugs)
    slug_result = MagicMock()
    slug_result.all.return_value = [(s,) for s in (existing_slugs or [])]

    # Max revision query not called on create — but session.execute needs to handle multiple calls
    call_count = 0

    async def mock_execute(query):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return existing_check
        return slug_result

    session.execute = mock_execute
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock(side_effect=lambda obj: None)

    result = await create_or_update_article_from_campaign(session, campaign)
    return result, session


async def test_title_extracted_from_h1():
    from app.services.articles import _extract_title
    campaign = _make_campaign(blog_html="<h1>Hello World</h1><p>Body</p>")
    assert _extract_title(campaign) == "Hello World"


async def test_title_fallback_to_brain_dump():
    from app.services.articles import _extract_title
    campaign = _make_campaign(blog_html="<p>No heading here</p>", brain_dump="My Brain Dump Content")
    assert _extract_title(campaign) == "My Brain Dump Content"


async def test_title_brain_dump_truncated_at_80():
    from app.services.articles import _extract_title
    long_dump = "x" * 100
    campaign = _make_campaign(blog_html="<p>no h1</p>", brain_dump=long_dump)
    assert len(_extract_title(campaign)) == 80


async def test_reading_time_minimum_one():
    from app.services.articles import _reading_time
    assert _reading_time("<p>Short</p>") == 1


async def test_reading_time_rounds_correctly():
    from app.services.articles import _reading_time
    # 450 words / 225 wpm = 2 minutes
    words = " ".join(["word"] * 450)
    html = f"<p>{words}</p>"
    assert _reading_time(html) == 2


async def test_create_returns_existing_article_without_changes():
    """If article already exists for campaign, return it unchanged — no add/flush."""
    from app.services.articles import create_or_update_article_from_campaign

    existing = MagicMock()
    campaign = _make_campaign()
    session = AsyncMock()
    existing_check = MagicMock()
    existing_check.scalar_one_or_none.return_value = existing
    session.execute = AsyncMock(return_value=existing_check)

    result = await create_or_update_article_from_campaign(session, campaign)

    assert result is existing
    session.add.assert_not_called()
    session.flush.assert_not_called()


async def test_create_returns_none_for_empty_blog_html():
    from app.services.articles import create_or_update_article_from_campaign

    campaign = _make_campaign(blog_html=None)
    session = AsyncMock()
    result = await create_or_update_article_from_campaign(session, campaign)
    assert result is None


async def test_slug_collision_appends_suffix():
    from app.services.articles import _unique_slug
    from app.db.repositories.models import Article

    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.all.return_value = [("my-title",), ("my-title-2",)]
    session.execute = AsyncMock(return_value=result_mock)

    client_id = uuid.uuid4()
    slug = await _unique_slug(session, client_id, "my-title")
    assert slug == "my-title-3"


async def test_slug_no_collision_returns_base():
    from app.services.articles import _unique_slug

    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.all.return_value = []
    session.execute = AsyncMock(return_value=result_mock)

    slug = await _unique_slug(session, uuid.uuid4(), "clean-slug")
    assert slug == "clean-slug"


async def test_tags_extracted_from_voice_score():
    from app.services.articles import create_or_update_article_from_campaign

    campaign = _make_campaign(
        blog_html="<h1>Title</h1><p>Body</p>",
        voice_score={"tags": ["python", "ai", "blog"]},
    )
    session = AsyncMock()

    # First call: no existing article; second call: slug query empty
    no_existing = MagicMock()
    no_existing.scalar_one_or_none.return_value = None
    slug_result = MagicMock()
    slug_result.all.return_value = []

    captured_article = {}

    def capture_add(obj):
        if hasattr(obj, "tags"):
            captured_article["tags"] = obj.tags

    session.add = capture_add
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    call_count = 0

    async def mock_execute(q):
        nonlocal call_count
        call_count += 1
        return no_existing if call_count == 1 else slug_result

    session.execute = mock_execute
    await create_or_update_article_from_campaign(session, campaign)
    assert captured_article.get("tags") == ["python", "ai", "blog"]


async def test_tags_none_when_voice_score_missing():
    from app.services.articles import create_or_update_article_from_campaign

    campaign = _make_campaign(blog_html="<h1>Title</h1><p>Body</p>", voice_score=None)
    session = AsyncMock()

    no_existing = MagicMock()
    no_existing.scalar_one_or_none.return_value = None
    slug_result = MagicMock()
    slug_result.all.return_value = []
    captured = {}

    def capture_add(obj):
        if hasattr(obj, "tags"):
            captured["tags"] = obj.tags

    session.add = capture_add
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    call_count = 0

    async def mock_execute(q):
        nonlocal call_count
        call_count += 1
        return no_existing if call_count == 1 else slug_result

    session.execute = mock_execute
    await create_or_update_article_from_campaign(session, campaign)
    assert captured.get("tags") is None


async def test_idempotency_second_call_no_revision():
    """Second call with same campaign must return existing article, revision count stays 1."""
    from app.services.articles import create_or_update_article_from_campaign

    existing = MagicMock()
    existing.id = uuid.uuid4()
    campaign = _make_campaign()
    session = AsyncMock()

    existing_check = MagicMock()
    existing_check.scalar_one_or_none.return_value = existing
    session.execute = AsyncMock(return_value=existing_check)

    result1 = await create_or_update_article_from_campaign(session, campaign)
    result2 = await create_or_update_article_from_campaign(session, campaign)

    assert result1 is existing
    assert result2 is existing
    # No new rows created on idempotent calls
    session.add.assert_not_called()
