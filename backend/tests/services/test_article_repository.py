"""Tests for db/repositories/articles.py — revision logic and status toggle."""
import uuid
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest


def _make_article(**kwargs):
    a = MagicMock()
    a.id = uuid.uuid4()
    a.title = kwargs.get("title", "Original Title")
    a.html = kwargs.get("html", "<p>Original</p>")
    a.excerpt = kwargs.get("excerpt", "Original excerpt")
    a.meta_description = kwargs.get("meta_description", "Original meta")
    a.tags = kwargs.get("tags", None)
    a.category = kwargs.get("category", None)
    a.author = kwargs.get("author", None)
    a.status = kwargs.get("status", "published")
    a.updated_at = None
    return a


async def test_update_article_content_creates_revision_on_change():
    from app.db.repositories.articles import update_article_content

    article = _make_article(title="Old Title")
    session = AsyncMock()

    max_rev_result = MagicMock()
    max_rev_result.scalar_one_or_none.return_value = 1
    session.execute = AsyncMock(return_value=max_rev_result)

    added = []
    session.add = lambda obj: added.append(obj)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    await update_article_content(session, article, {"title": "New Title"}, source="edit")

    assert article.title == "New Title"
    # One ArticleRevision should be added
    from app.db.repositories.models import ArticleRevision
    revisions = [obj for obj in added if isinstance(obj, ArticleRevision)]
    assert len(revisions) == 1
    assert revisions[0].revision_number == 2
    assert revisions[0].source == "edit"


async def test_update_article_content_no_revision_when_unchanged():
    from app.db.repositories.articles import update_article_content

    article = _make_article(title="Same Title")
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    result = await update_article_content(session, article, {"title": "Same Title"}, source="edit")

    # No execute call for max revision since no change occurred
    session.execute.assert_not_called()
    session.add.assert_not_called()
    assert result is article


async def test_revision_numbers_increment():
    from app.db.repositories.articles import update_article_content
    from app.db.repositories.models import ArticleRevision

    article = _make_article()
    session = AsyncMock()

    max_rev_result = MagicMock()
    max_rev_result.scalar_one_or_none.return_value = 3
    session.execute = AsyncMock(return_value=max_rev_result)

    added = []
    session.add = lambda obj: added.append(obj)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    await update_article_content(session, article, {"title": "Updated"}, source="edit")

    revisions = [obj for obj in added if isinstance(obj, ArticleRevision)]
    assert revisions[0].revision_number == 4


async def test_set_article_status_creates_no_revision():
    from app.db.repositories.articles import set_article_status

    article = _make_article(status="published")
    session = AsyncMock()
    added = []
    session.add = lambda obj: added.append(obj)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    await set_article_status(session, article, "hidden")

    assert article.status == "hidden"
    from app.db.repositories.models import ArticleRevision
    revisions = [obj for obj in added if isinstance(obj, ArticleRevision)]
    assert len(revisions) == 0
    # execute must NOT be called (no revision logic)
    session.execute.assert_not_called()
