"""Public delivery API — unauthenticated read surface for client articles.

This is a FastAPI sub-application mounted at /public in main.py.
It has its own CORS (allow_origins=["*"], GET/HEAD/OPTIONS only),
its own exception handler, and its own rate limiter.
It does NOT share middleware or exception handlers with the main app.
"""

import hashlib
import uuid
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_session
from app.db.repositories.articles import get_article_by_slug, list_articles
from app.db.repositories.delivery_tokens import (
    get_active_token_by_prefix,
    touch_last_used,
    verify_token,
)
from app.db.repositories.models import Article, ArticleStatus

# ---------------------------------------------------------------------------
# Rate limiter keyed on token prefix, falling back to IP
# ---------------------------------------------------------------------------

def _token_or_ip(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ppd_"):
        raw = auth[len("Bearer "):]
        return raw[:8]  # prefix
    from slowapi.util import get_remote_address
    return get_remote_address(request)


public_limiter = Limiter(key_func=_token_or_ip)

# ---------------------------------------------------------------------------
# Sub-application
# ---------------------------------------------------------------------------

public_app = FastAPI(openapi_url=None, title="PersonnaPress Public Delivery API")

public_app.state.limiter = public_limiter
public_app.add_middleware(SlowAPIMiddleware)

public_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["Authorization"],
)

_INVALID_TOKEN = {
    "detail": {
        "error": {
            "code": "INVALID_DELIVERY_TOKEN",
            "message": "Missing or invalid delivery token.",
        }
    }
}
_ARTICLE_NOT_FOUND = {
    "detail": {
        "error": {
            "code": "ARTICLE_NOT_FOUND",
            "message": "Article not found.",
        }
    }
}


from fastapi.exception_handlers import http_exception_handler as _default_http_handler
from starlette.exceptions import HTTPException as StarletteHTTPException


@public_app.exception_handler(StarletteHTTPException)
async def _http_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # Explicit handler ensures HTTPException is never swallowed by the generic Exception handler below.
    return await _default_http_handler(request, exc)


@public_app.exception_handler(Exception)
async def _generic_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": {"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}}},
    )


@public_app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": {"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests"}}},
        headers={"Cache-Control": "no-store"},
    )


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

async def get_delivery_client(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> uuid.UUID:
    """Resolve a delivery token to a client_id; 401 on any failure."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ppd_"):
        raise _token_401()

    raw = auth[len("Bearer "):]
    if len(raw) < 8:
        raise _token_401()

    prefix = raw[:8]
    token = await get_active_token_by_prefix(db, prefix)
    if token is None:
        raise _token_401()

    if not verify_token(raw, token.token_hash):
        raise _token_401()

    await touch_last_used(db, token)
    # Commit the last_used_at update; errors here are non-fatal
    try:
        await db.commit()
    except Exception:
        import logging as _logging
        _logging.getLogger(__name__).warning("touch_last_used commit failed", exc_info=True)
        await db.rollback()

    return token.client_id


def _token_401():
    from fastapi import HTTPException
    return HTTPException(
        status_code=401,
        detail=_INVALID_TOKEN["detail"],
        headers={"Cache-Control": "no-store"},
    )


# ---------------------------------------------------------------------------
# Caching helpers
# ---------------------------------------------------------------------------

def _etag_list(
    client_id: uuid.UUID,
    page: int,
    page_size: int,
    tag: Optional[str],
    category: Optional[str],
    total: int,
    max_updated: Optional[str],
) -> str:
    key = f"{client_id}:{page}:{page_size}:{tag}:{category}:{total}:{max_updated}"
    digest = hashlib.sha256(key.encode()).hexdigest()[:16]
    return f'W/"{digest}"'


def _etag_detail(article: Article) -> str:
    key = f"{article.id}{article.updated_at.isoformat()}"
    digest = hashlib.sha256(key.encode()).hexdigest()[:16]
    return f'W/"{digest}"'


_CACHE_PUBLIC = "public, max-age=60, stale-while-revalidate=300"
_CACHE_PRIVATE = "no-store"


def _check_etag(request: Request, etag: str) -> Optional[Response]:
    if_none_match = request.headers.get("If-None-Match")
    if if_none_match and if_none_match == etag:
        return Response(
            status_code=304,
            headers={"ETag": etag, "Cache-Control": _CACHE_PUBLIC},
        )
    return None


# ---------------------------------------------------------------------------
# Article serialisation helpers
# ---------------------------------------------------------------------------

def _article_list_item(article: Article) -> dict:
    return {
        "slug": article.slug,
        "title": article.title,
        "excerpt": article.excerpt,
        "featured_image_url": article.featured_image_url,
        "author": article.author,
        "tags": article.tags or [],
        "category": article.category,
        "published_at": article.published_at.isoformat(),
        "updated_at": article.updated_at.isoformat(),
        "reading_time_minutes": article.reading_time_minutes,
    }


def _build_seo(article: Article, client_name: Optional[str] = None) -> dict:
    author_name = article.author or client_name or ""
    json_ld: dict = {
        "@context": "https://schema.org",
        "@type": "Article",
    }
    if article.title:
        json_ld["headline"] = article.title
    if article.meta_description:
        json_ld["description"] = article.meta_description
    if article.featured_image_url:
        json_ld["image"] = article.featured_image_url
    json_ld["datePublished"] = article.published_at.isoformat()
    json_ld["dateModified"] = article.updated_at.isoformat()
    if author_name:
        json_ld["author"] = {"@type": "Person", "name": author_name}
    if article.tags:
        json_ld["keywords"] = ", ".join(article.tags)

    seo: dict = {
        "reading_time_minutes": article.reading_time_minutes,
        "json_ld": json_ld,
    }
    if article.meta_description:
        seo["meta_description"] = article.meta_description
    if article.title or article.meta_description or article.featured_image_url:
        og: dict = {}
        if article.title:
            og["title"] = article.title
        if article.meta_description:
            og["description"] = article.meta_description
        if article.featured_image_url:
            og["image"] = article.featured_image_url
        if og:
            seo["og"] = og
    return seo


def _strip_scripts(html: str) -> str:
    # Defense-in-depth strip of active content tags. HTML is sanitized at write time;
    # this catches anything that slips through.
    import re
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<iframe[^>]*>.*?</iframe>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<object[^>]*>.*?</object>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<embed[^>]*/?>", "", html, flags=re.IGNORECASE)
    return html


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@public_app.get("/v1/articles")
@public_limiter.limit("120/minute")
async def list_published_articles(
    request: Request,
    client_id: uuid.UUID = Depends(get_delivery_client),
    db: AsyncSession = Depends(get_session),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    tag: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
) -> Response:
    articles, total = await list_articles(
        db,
        client_id=client_id,
        status=ArticleStatus.published,
        tag=tag,
        category=category,
        page=page,
        page_size=page_size,
    )

    max_updated = max((a.updated_at.isoformat() for a in articles), default=None)
    etag = _etag_list(client_id, page, page_size, tag, category, total, max_updated)

    if (resp := _check_etag(request, etag)):
        return resp

    body = {
        "data": [_article_list_item(a) for a in articles],
        "meta": {"page": page, "page_size": page_size, "total": total},
    }
    return JSONResponse(
        content=body,
        headers={"ETag": etag, "Cache-Control": _CACHE_PUBLIC},
    )


@public_app.get("/v1/articles/{slug}")
@public_limiter.limit("120/minute")
async def get_published_article(
    slug: str,
    request: Request,
    client_id: uuid.UUID = Depends(get_delivery_client),
    db: AsyncSession = Depends(get_session),
) -> Response:
    article = await get_article_by_slug(db, client_id, slug)

    # Hidden, missing, or other-tenant all return identical 404
    if article is None or article.status != ArticleStatus.published:
        return JSONResponse(
            status_code=404,
            content=_ARTICLE_NOT_FOUND,
            headers={"Cache-Control": _CACHE_PRIVATE},
        )

    etag = _etag_detail(article)
    if (resp := _check_etag(request, etag)):
        return resp

    seo = _build_seo(article)
    body = {
        **_article_list_item(article),
        "html": _strip_scripts(article.html or ""),
        "seo": seo,
    }
    return JSONResponse(
        content=body,
        headers={"ETag": etag, "Cache-Control": _CACHE_PUBLIC},
    )


@public_app.get("/v1/tags")
@public_limiter.limit("120/minute")
async def get_tags_and_categories(
    request: Request,
    client_id: uuid.UUID = Depends(get_delivery_client),
    db: AsyncSession = Depends(get_session),
) -> Response:
    articles, _ = await list_articles(
        db,
        client_id=client_id,
        status=ArticleStatus.published,
        page=1,
        page_size=10_000,
    )

    tag_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    max_updated: Optional[str] = None

    for article in articles:
        for tag in (article.tags or []):
            if tag:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        if article.category:
            category_counts[article.category] = category_counts.get(article.category, 0) + 1
        ts = article.updated_at.isoformat()
        if max_updated is None or ts > max_updated:
            max_updated = ts

    etag = _etag_list(client_id, 1, 10_000, None, None, len(articles), max_updated)
    if (resp := _check_etag(request, etag)):
        return resp

    body = {
        "tags": [{"name": k, "count": v} for k, v in sorted(tag_counts.items())],
        "categories": [{"name": k, "count": v} for k, v in sorted(category_counts.items())],
    }
    return JSONResponse(
        content=body,
        headers={"ETag": etag, "Cache-Control": _CACHE_PUBLIC},
    )
