"""Article creation service — converts published campaigns into first-class articles."""

import logging
from typing import Optional

from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.repositories.models import Article, ArticleRevision, ArticleStatus, utcnow
from app.integrations.github import slug_from_title
from app.services.publishing import _extract_meta_description

logger = logging.getLogger(__name__)

_WORDS_PER_MINUTE = 225


def _reading_time(html: str) -> int:
    text = BeautifulSoup(html, "html.parser").get_text(separator=" ")
    word_count = len(text.split())
    return max(1, round(word_count / _WORDS_PER_MINUTE))


def _extract_title(campaign) -> str:
    soup = BeautifulSoup(campaign.blog_html or "", "html.parser")
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return (campaign.brain_dump or "")[:80].strip() or "Untitled"


async def _unique_slug(session: AsyncSession, client_id, base_slug: str) -> str:
    """Return base_slug or base_slug-N where N makes it unique for client."""
    result = await session.execute(
        select(Article.slug).where(
            Article.client_id == client_id,
            Article.slug.like(f"{base_slug}%"),
        )
    )
    existing = {row[0] for row in result.all()}
    if base_slug not in existing:
        return base_slug
    n = 2
    while f"{base_slug}-{n}" in existing:
        n += 1
    return f"{base_slug}-{n}"


async def create_or_update_article_from_campaign(
    session: AsyncSession,
    campaign,
    status_override: Optional[str] = None,
) -> Optional[Article]:
    """Create an article from a published campaign, or return the existing one.

    Idempotent: if an article already exists for this campaign, returns it unchanged.
    status_override lets the backfill script set status=hidden for existing campaigns.
    """
    if not campaign.blog_html:
        return None

    # Idempotency check — multi-platform publishes and re-publishes must be no-ops
    result = await session.execute(
        select(Article).where(Article.campaign_id == campaign.id)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    title = _extract_title(campaign)
    base_slug = slug_from_title(title)
    slug = await _unique_slug(session, campaign.client_id, base_slug)

    meta_description = _extract_meta_description(campaign.blog_html)
    excerpt = meta_description
    tags = campaign.voice_score.get("tags") if isinstance(campaign.voice_score, dict) else None
    reading_time = _reading_time(campaign.blog_html)
    article_status = status_override if status_override else ArticleStatus.published

    article = Article(
        client_id=campaign.client_id,
        campaign_id=campaign.id,
        slug=slug,
        title=title,
        html=campaign.blog_html,
        excerpt=excerpt,
        meta_description=meta_description,
        featured_image_url=campaign.image_url,
        author=None,
        tags=tags,
        category=None,
        status=article_status,
        reading_time_minutes=reading_time,
        published_at=utcnow(),
    )
    session.add(article)
    await session.flush()
    await session.refresh(article)

    revision = ArticleRevision(
        article_id=article.id,
        revision_number=1,
        title=title,
        html=campaign.blog_html,
        excerpt=excerpt,
        meta_description=meta_description,
        tags=tags,
        category=None,
        author=None,
        source="initial",
    )
    session.add(revision)
    await session.flush()

    return article
