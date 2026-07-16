"""Article management endpoints — create, read, update, revisions."""

import logging
import uuid

from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.connection import get_session
from app.db.repositories.articles import (
    get_article,
    get_article_by_slug,
    get_revision,
    list_articles,
    list_revisions,
    set_article_status,
    update_article_content,
)
from app.db.repositories.models import utcnow
from app.db.repositories.clients import get_client
from app.core.html_sanitize import is_allowed_image_src
from app.schemas.article import (
    ArticleListResponse,
    ArticleResponse,
    ArticlePatch,
    RevisionDetail,
    RevisionListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["articles"])

# ---------------------------------------------------------------------------
# HTML allowlist — mirrors frontend DOMPurify config in BlogEditor.tsx
# ---------------------------------------------------------------------------
_ALLOWED_TAGS = {
    "h1", "h2", "h3", "h4",
    "p", "ul", "ol", "li",
    "strong", "em",
    "a", "br",
    "blockquote",
    "code", "pre",
    "img", "figure", "figcaption",
}
_ALLOWED_ATTRS: dict[str, list[str]] = {
    "a": ["href", "title", "rel"],
    "img": ["src", "alt", "width", "height"],
}
_BLOCK_TAGS = {
    "script", "style", "iframe", "object", "embed",
    # Dangerous structural/scripting tags that must be decomposed rather than unwrapped
    "template", "svg", "math", "use", "noscript",
}

_SAFE_HREF_SCHEMES = ("http://", "https://", "mailto:", "/", "#", "./", "../")


def _sanitize_html(raw: str) -> str:
    """Strip disallowed tags and attributes from HTML using BeautifulSoup.

    Preserves only the tags in _ALLOWED_TAGS with the attributes in _ALLOWED_ATTRS.
    Removes any <img> whose src is missing or not from our own storage buckets.
    Strips javascript:/data:/vbscript: schemes from <a> hrefs.
    """
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup.find_all(True):
        # After decompose() the tag is detached; skip orphaned nodes from block-tag children.
        if tag.parent is None:
            continue
        if tag.name in _BLOCK_TAGS:
            tag.decompose()
        elif tag.name not in _ALLOWED_TAGS:
            tag.unwrap()
        else:
            allowed = _ALLOWED_ATTRS.get(tag.name, [])
            attrs_to_remove = [a for a in list(tag.attrs) if a not in allowed]
            for a in attrs_to_remove:
                del tag[a]
            # Strip event attributes unconditionally
            for a in [k for k in list(tag.attrs) if k.startswith("on")]:
                del tag[a]
    # Strip dangerous href schemes (javascript:, data:, vbscript:) from <a> tags
    for a_tag in soup.find_all("a"):
        href = a_tag.get("href", "")
        if href:
            lower = href.strip().lower()
            if not any(lower.startswith(s) for s in _SAFE_HREF_SCHEMES):
                del a_tag["href"]
    # Remove any <img> with missing or disallowed src (done after attribute strip)
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src or not is_allowed_image_src(src):
            img.decompose()
    return str(soup)


def _parse_user_id(current_user: dict) -> uuid.UUID:
    try:
        return uuid.UUID(str(current_user["user_id"]))
    except (KeyError, ValueError) as e:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Invalid session.", "detail": {}}},
        ) from e


async def _get_owned_article(article_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession):
    """Return the article, verifying it belongs to the current user via its client."""
    article = await get_article(db, article_id)
    if not article:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "ARTICLE_NOT_FOUND", "message": "Article not found.", "detail": {}}},
        )
    client = await get_client(db, article.client_id)
    if not client or client.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "ARTICLE_NOT_FOUND", "message": "Article not found.", "detail": {}}},
        )
    return article


# ---------------------------------------------------------------------------
# GET /api/v1/articles?client_id=&status=&page=&page_size=
# ---------------------------------------------------------------------------

@router.get("/articles")
async def list_articles_endpoint(
    client_id: uuid.UUID,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)

    client = await get_client(db, client_id)
    if not client or client.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Client not found.", "detail": {}}},
        )

    items, total = await list_articles(db, client_id, status=status, page=page, page_size=page_size)
    from app.schemas.article import ArticleListItem
    return {
        "items": [ArticleListItem.model_validate(a).model_dump() for a in items],
        "total": total,
    }


# ---------------------------------------------------------------------------
# GET /api/v1/articles/{id}
# ---------------------------------------------------------------------------

@router.get("/articles/{article_id}")
async def get_article_endpoint(
    article_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)
    article = await _get_owned_article(article_id, user_id, db)
    return ArticleResponse.model_validate(article).model_dump()


# ---------------------------------------------------------------------------
# PATCH /api/v1/articles/{id}
# ---------------------------------------------------------------------------

@router.patch("/articles/{article_id}")
async def patch_article_endpoint(
    article_id: uuid.UUID,
    body: ArticlePatch,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)
    article = await _get_owned_article(article_id, user_id, db)

    # Separate content fields from status and slug
    content_fields: dict = {}
    for field in ("title", "html", "excerpt", "meta_description", "tags", "category", "author"):
        val = getattr(body, field, None)
        if val is not None:
            content_fields[field] = val

    # Server-side sanitize incoming html
    if "html" in content_fields:
        content_fields["html"] = _sanitize_html(content_fields["html"])

    # Handle slug change (not a content/revisioned field — update directly)
    if body.slug is not None and body.slug != article.slug:
        existing = await get_article_by_slug(db, article.client_id, body.slug)
        if existing and existing.id != article_id:
            raise HTTPException(
                status_code=409,
                detail={"error": {"code": "SLUG_TAKEN", "message": "This slug is already used by another article.", "detail": {}}},
            )
        article.slug = body.slug
        article.updated_at = utcnow()
        db.add(article)

    # Apply content changes (creates revision if changed)
    if content_fields:
        article = await update_article_content(db, article, content_fields, source="edit")

    # Handle status change separately (no revision)
    if body.status is not None and body.status != str(article.status.value if hasattr(article.status, "value") else article.status):
        article = await set_article_status(db, article, body.status)

    # Handle featured_image_url separately (no revision; bumps updated_at so ETag changes)
    if body.featured_image_url is not None:
        article.featured_image_url = body.featured_image_url
        article.updated_at = utcnow()
        db.add(article)

    # Handle featured_image_alt separately (no revision)
    if body.featured_image_alt is not None:
        article.featured_image_alt = body.featured_image_alt
        article.updated_at = utcnow()
        db.add(article)

    await db.commit()
    await db.refresh(article)
    return ArticleResponse.model_validate(article).model_dump()


# ---------------------------------------------------------------------------
# GET /api/v1/articles/{id}/revisions
# ---------------------------------------------------------------------------

@router.get("/articles/{article_id}/revisions")
async def list_revisions_endpoint(
    article_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)
    await _get_owned_article(article_id, user_id, db)

    revisions = await list_revisions(db, article_id)
    from app.schemas.article import RevisionListItem
    return {
        "items": [RevisionListItem.model_validate(r).model_dump() for r in revisions],
    }


# ---------------------------------------------------------------------------
# GET /api/v1/articles/{id}/revisions/{n}
# ---------------------------------------------------------------------------

@router.get("/articles/{article_id}/revisions/{revision_number}")
async def get_revision_endpoint(
    article_id: uuid.UUID,
    revision_number: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)
    await _get_owned_article(article_id, user_id, db)

    revision = await get_revision(db, article_id, revision_number)
    if not revision:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "REVISION_NOT_FOUND", "message": "Revision not found.", "detail": {}}},
        )
    return RevisionDetail.model_validate(revision).model_dump()


# ---------------------------------------------------------------------------
# POST /api/v1/articles/{id}/revisions/{n}/restore
# ---------------------------------------------------------------------------

@router.post("/articles/{article_id}/revisions/{revision_number}/restore")
async def restore_revision_endpoint(
    article_id: uuid.UUID,
    revision_number: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user_id = _parse_user_id(current_user)
    article = await _get_owned_article(article_id, user_id, db)

    revision = await get_revision(db, article_id, revision_number)
    if not revision:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "REVISION_NOT_FOUND", "message": "Revision not found.", "detail": {}}},
        )

    # Build the content dict from the revision
    restore_fields = {
        "title": revision.title,
        "html": revision.html,
        "excerpt": revision.excerpt,
        "meta_description": revision.meta_description,
        "tags": revision.tags,
        "category": revision.category,
        "author": revision.author,
    }
    # update_article_content is a no-op if content is identical (AC 6 — restoring identical = no revision)
    article = await update_article_content(db, article, restore_fields, source="restore")

    await db.commit()
    await db.refresh(article)
    return ArticleResponse.model_validate(article).model_dump()
