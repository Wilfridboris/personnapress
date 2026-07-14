"""Article and ArticleRevision repository — plain async functions over AsyncSession."""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.models import Article, ArticleRevision, utcnow

_CONTENT_FIELDS = ("title", "html", "excerpt", "meta_description", "tags", "category", "author")


async def create_article(session: AsyncSession, **fields) -> Article:
    article = Article(**fields)
    session.add(article)
    await session.flush()
    await session.refresh(article)
    return article


async def get_article(session: AsyncSession, article_id: uuid.UUID) -> Optional[Article]:
    result = await session.execute(select(Article).where(Article.id == article_id))
    return result.scalar_one_or_none()


async def get_article_by_slug(
    session: AsyncSession, client_id: uuid.UUID, slug: str
) -> Optional[Article]:
    result = await session.execute(
        select(Article).where(Article.client_id == client_id, Article.slug == slug)
    )
    return result.scalar_one_or_none()


async def list_articles(
    session: AsyncSession,
    client_id: uuid.UUID,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    category: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Article], int]:
    query = select(Article).where(Article.client_id == client_id)
    if status is not None:
        query = query.where(Article.status == status)
    if tag is not None:
        query = query.where(Article.tags.contains([tag]))
    if category is not None:
        query = query.where(Article.category == category)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    items_query = (
        query.order_by(Article.published_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items_result = await session.execute(items_query)
    items = list(items_result.scalars().all())
    return items, total


async def update_article_content(
    session: AsyncSession,
    article: Article,
    fields: dict,
    source: str,
) -> Article:
    """Update content fields and create a revision only if content actually changed."""
    changed = False
    for field in _CONTENT_FIELDS:
        if field in fields and getattr(article, field) != fields[field]:
            setattr(article, field, fields[field])
            changed = True

    if not changed:
        return article

    article.updated_at = utcnow()
    session.add(article)
    await session.flush()
    await session.refresh(article)

    max_rev_result = await session.execute(
        select(func.max(ArticleRevision.revision_number)).where(
            ArticleRevision.article_id == article.id
        )
    )
    max_rev = max_rev_result.scalar_one_or_none() or 0

    revision = ArticleRevision(
        article_id=article.id,
        revision_number=max_rev + 1,
        title=article.title,
        html=article.html,
        excerpt=article.excerpt,
        meta_description=article.meta_description,
        tags=article.tags,
        category=article.category,
        author=article.author,
        source=source,
    )
    session.add(revision)
    await session.flush()
    return article


async def set_article_status(
    session: AsyncSession, article: Article, status: str
) -> Article:
    """Change article status without creating a revision."""
    article.status = status
    article.updated_at = utcnow()
    session.add(article)
    await session.flush()
    await session.refresh(article)
    return article


async def list_revisions(
    session: AsyncSession, article_id: uuid.UUID
) -> list[ArticleRevision]:
    result = await session.execute(
        select(ArticleRevision)
        .where(ArticleRevision.article_id == article_id)
        .order_by(ArticleRevision.revision_number.desc())
    )
    return list(result.scalars().all())


async def get_revision(
    session: AsyncSession, article_id: uuid.UUID, revision_number: int
) -> Optional[ArticleRevision]:
    result = await session.execute(
        select(ArticleRevision).where(
            ArticleRevision.article_id == article_id,
            ArticleRevision.revision_number == revision_number,
        )
    )
    return result.scalar_one_or_none()
