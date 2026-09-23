"""Public delivery API — unauthenticated read surface for client articles.

This is a FastAPI sub-application mounted at /public in main.py.
It has its own CORS (allow_origins=["*"], GET/HEAD/OPTIONS only),
its own exception handler, and its own rate limiter.
It does NOT share middleware or exception handlers with the main app.
"""

import hashlib
import logging
import uuid
from typing import Annotated, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.html_sanitize import _sanitize_html
from app.db.connection import get_session
from app.db.repositories.articles import (
    create_article,
    get_article,
    get_article_by_slug,
    list_articles,
    set_article_status,
    update_article_content,
)
from app.db.repositories.delivery_tokens import (
    get_active_token_by_prefix,
    touch_last_used,
    verify_token,
)
from app.db.repositories.models import (
    Article,
    ArticleRevision,
    ArticleStatus,
    utcnow,
)
from app.integrations.github import slug_from_title
from app.services.articles import _reading_time, _unique_slug

logger = logging.getLogger(__name__)

# Cap the raw request body at 200 KB before parsing/rendering (AC 4).
_MAX_BODY_BYTES = 200 * 1024
_WRITE_RATE_LIMIT = "60/minute"

# ---------------------------------------------------------------------------
# Rate limiter keyed on token prefix, falling back to IP
# ---------------------------------------------------------------------------

def _token_or_ip(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ppd_") or auth.startswith("Bearer ppw_"):
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


def _error_detail(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


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


@public_app.exception_handler(RequestValidationError)
async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return Pydantic body-validation failures in the nested VALIDATION_ERROR shape.

    A body that exceeds the size cap, an unknown field (extra="forbid"), or any
    field constraint violation lands here. The first error's message is surfaced;
    raw internals are never leaked.
    """
    errors = exc.errors()
    message = "Request body failed validation."
    if errors:
        first = errors[0]
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        detail = first.get("msg", "invalid")
        message = f"{loc}: {detail}" if loc else detail
    return JSONResponse(
        status_code=422,
        content={"detail": _error_detail("VALIDATION_ERROR", message)},
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
    return HTTPException(
        status_code=401,
        detail=_INVALID_TOKEN["detail"],
        headers={"Cache-Control": "no-store"},
    )


def _write_scope_403():
    return HTTPException(
        status_code=403,
        detail=_error_detail(
            "WRITE_SCOPE_REQUIRED",
            "This token is read-only. A write-scoped token is required for this endpoint.",
        ),
        headers={"Cache-Control": "no-store"},
    )


async def get_delivery_client_write(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> uuid.UUID:
    """Resolve a write-scoped delivery token to a client_id.

    401 INVALID_DELIVERY_TOKEN on any identity failure (missing/malformed header,
    non-ppw_ prefix, unknown or revoked token, hash mismatch). 403 WRITE_SCOPE_REQUIRED
    when the token is a valid identity but read-scoped.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ppw_"):
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

    # Valid identity — now enforce scope. Read-scoped tokens are rejected with 403.
    if getattr(token, "scope", "read") != "write":
        raise _write_scope_403()

    await touch_last_used(db, token)
    try:
        await db.commit()
    except Exception:
        logger.warning("touch_last_used commit failed", exc_info=True)
        await db.rollback()

    return token.client_id


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
        "featured_image_alt": article.featured_image_alt,
        "author": article.author,
        "tags": article.tags or [],
        "category": article.category,
        "published_at": article.published_at.isoformat(),
        "updated_at": article.updated_at.isoformat(),
        "reading_time_minutes": article.reading_time_minutes,
    }


def _authored_list_item(article: Article) -> dict:
    """Serialiser for write-token read-back endpoints.

    Extends the public list-item fields with id, status, edit_url, and api_authored.
    The public serialiser intentionally omits these; this one is the authored surface.
    """
    app_url = settings.APP_URL.rstrip("/")
    return {
        **_article_list_item(article),
        "id": str(article.id),
        "status": article.status.value if hasattr(article.status, "value") else str(article.status),
        "edit_url": f"{app_url}/articles/{article.id}",
        "api_authored": article.campaign_id is None,
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


# ---------------------------------------------------------------------------
# Ingestion (write) endpoint — POST /public/v1/articles (Story 12.7)
# ---------------------------------------------------------------------------

# markdown-it-py with raw-HTML passthrough disabled. html=False means any raw
# HTML in the Markdown source is emitted as escaped text, not injected — so the
# only HTML that reaches the sanitizer is what the renderer itself produced.
_md_renderer = None


def _render_markdown(text: str) -> str:
    """Render Markdown to HTML with raw-HTML passthrough disabled."""
    global _md_renderer
    if _md_renderer is None:
        from markdown_it import MarkdownIt

        # Build and configure the renderer locally, then assign the singleton
        # only once fully initialised. This prevents a thread-race window where
        # a concurrent first-request could observe _md_renderer assigned but
        # .enable() not yet called and receive output without the added rules.
        # We deliberately do NOT switch to the full gfm-like preset because that
        # preset also enables task lists, which emit <input type="checkbox"> — an
        # element we do not want in the sanitizer allowlist.
        _md = MarkdownIt("commonmark", {"html": False})
        _md.enable(["table", "strikethrough"])
        _md_renderer = _md
    return _md_renderer.render(text)


class _ArticleContentBase(BaseModel):
    """Shared content fields + validators for the ingest and update bodies.

    ``extra='forbid'`` rejects unknown fields on every subclass. The two concrete
    request models differ only in the presence of ``slug``: ``ArticleIngestRequest``
    adds it (create/upsert path), ``ArticleUpdateRequest`` omits it (slug is
    immutable via PUT, so sending it lands as a 422 unknown-field). Keeping the
    validators here avoids drift between the two contracts.
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., max_length=300)
    content: str = Field(...)
    format: str = Field(...)
    excerpt: Optional[str] = Field(default=None, max_length=500)
    meta_description: Optional[str] = Field(default=None, max_length=320)
    author: Optional[str] = Field(default=None, max_length=200)
    category: Optional[str] = Field(default=None, max_length=100)
    featured_image_alt: Optional[str] = Field(default=None, max_length=300)
    featured_image_url: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)

    @field_validator("title")
    @classmethod
    def _title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must not be empty")
        return v

    @field_validator("content")
    @classmethod
    def _content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("content must not be empty")
        return v

    @field_validator("format")
    @classmethod
    def _format_allowed(cls, v: str) -> str:
        if v not in ("markdown", "html"):
            raise ValueError("format must be 'markdown' or 'html'")
        return v

    @field_validator("tags")
    @classmethod
    def _tags_valid(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        if len(v) > 20:
            raise ValueError("tags must contain at most 20 entries")
        for tag in v:
            if not isinstance(tag, str):
                raise ValueError("each tag must be a string")
            if len(tag) > 50:
                raise ValueError("each tag must be 50 characters or fewer")
        return v

    @field_validator("featured_image_url")
    @classmethod
    def _image_url_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not v.strip():
            return None
        v = v.strip()
        from urllib.parse import urlparse

        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("featured_image_url must be a valid http(s) URL")
        return v


class ArticleIngestRequest(_ArticleContentBase):
    """Body for POST /public/v1/articles. extra='forbid' rejects unknown fields."""

    slug: Optional[str] = Field(default=None, max_length=200)


class ArticleUpdateRequest(_ArticleContentBase):
    """Body for PUT /public/v1/authored/articles/{id}.

    Identical field set and caps as the ingest body **minus slug** (slug is
    immutable via this endpoint). Because ``extra='forbid'`` is inherited, a
    ``slug`` in the body is a 422 VALIDATION_ERROR rather than a silent no-op.
    """


def _ingest_response(article: Article, updated: bool, status_code: int) -> JSONResponse:
    app_url = settings.APP_URL.rstrip("/")
    body = {
        "id": str(article.id),
        "slug": article.slug,
        "status": article.status.value if hasattr(article.status, "value") else article.status,
        "edit_url": f"{app_url}/articles/{article.id}",
        "created_at": article.created_at.isoformat(),
        "updated_at": article.updated_at.isoformat(),
        "updated": updated,
    }
    return JSONResponse(
        status_code=status_code,
        content=body,
        headers={"Cache-Control": "no-store"},
    )


@public_app.post("/v1/articles")
@public_limiter.limit(_WRITE_RATE_LIMIT)
async def ingest_article(
    request: Request,
    client_id: uuid.UUID = Depends(get_delivery_client_write),
    db: AsyncSession = Depends(get_session),
) -> Response:
    """Create (or upsert-if-hidden) an article verbatim from a write-scoped token.

    No generation, fidelity, or voice code is ever invoked. Content is rendered
    (Markdown) and/or sanitized (HTML allowlist) only.
    """
    # 1) Enforce the 200 KB body cap BEFORE parsing/rendering.
    raw_body = await request.body()
    if len(raw_body) > _MAX_BODY_BYTES:
        raise HTTPException(
            status_code=413,
            detail=_error_detail(
                "CONTENT_TOO_LARGE",
                f"Request body exceeds the {_MAX_BODY_BYTES // 1024} KB limit.",
            ),
            headers={"Cache-Control": "no-store"},
        )

    # 2) Parse + validate the body. Validation failures raise RequestValidationError,
    #    handled into the nested VALIDATION_ERROR shape by _validation_handler.
    try:
        payload = ArticleIngestRequest.model_validate_json(raw_body)
    except ValueError as exc:
        raise RequestValidationError(_pydantic_errors(exc)) from exc

    # 3) Content pipeline — render (markdown) then sanitize, or sanitize (html).
    if payload.format == "markdown":
        rendered = _render_markdown(payload.content)
        html = _sanitize_html(rendered)
    else:
        html = _sanitize_html(payload.content)

    content_fields = {
        "title": payload.title,
        "html": html,
        "excerpt": payload.excerpt,
        "meta_description": payload.meta_description,
        "tags": payload.tags,
        "category": payload.category,
        "author": payload.author,
    }

    # 4) Slug resolution + idempotency.
    if payload.slug:
        base = slug_from_title(payload.slug) or slug_from_title(payload.title)
        existing = await get_article_by_slug(db, client_id, base)
        if existing is not None:
            if existing.status == ArticleStatus.published or existing.status == "published":
                raise HTTPException(
                    status_code=409,
                    detail=_error_detail(
                        "SLUG_CONFLICT_PUBLISHED",
                        "An article with this slug is already published and cannot be overwritten via the API.",
                    ),
                    headers={"Cache-Control": "no-store"},
                )
            # Hidden article with this slug -> update content (versions only if changed).
            article = await update_article_content(db, existing, content_fields, source="edit")
            if payload.featured_image_url is not None:
                article.featured_image_url = payload.featured_image_url
            if payload.featured_image_alt is not None:
                article.featured_image_alt = payload.featured_image_alt
            db.add(article)
            await db.commit()
            await db.refresh(article)
            return _ingest_response(article, updated=True, status_code=200)
        slug = base
    else:
        base = slug_from_title(payload.title)
        slug = await _unique_slug(db, client_id, base)

    # 5) Create path — hidden article + explicit initial revision.
    article = await create_article(
        db,
        client_id=client_id,
        campaign_id=None,
        slug=slug,
        title=payload.title,
        html=html,
        excerpt=payload.excerpt,
        meta_description=payload.meta_description,
        featured_image_url=payload.featured_image_url,
        featured_image_alt=payload.featured_image_alt,
        author=payload.author,
        tags=payload.tags,
        category=payload.category,
        status=ArticleStatus.hidden,
        reading_time_minutes=_reading_time(html),
        published_at=utcnow(),
    )
    revision = ArticleRevision(
        article_id=article.id,
        revision_number=1,
        title=payload.title,
        html=html,
        excerpt=payload.excerpt,
        meta_description=payload.meta_description,
        tags=payload.tags,
        category=payload.category,
        author=payload.author,
        source="initial",
    )
    db.add(revision)
    await db.flush()
    await db.commit()
    await db.refresh(article)
    return _ingest_response(article, updated=False, status_code=201)


def _pydantic_errors(exc: ValueError) -> list:
    """Normalize a Pydantic ValidationError into the list RequestValidationError expects."""
    errs = getattr(exc, "errors", None)
    if callable(errs):
        try:
            return exc.errors()  # type: ignore[attr-defined]
        except Exception:
            pass
    return [{"loc": ("body",), "msg": str(exc), "type": "value_error"}]


# ---------------------------------------------------------------------------
# Authored read-back endpoints — write-token required (Story 12.8)
# ---------------------------------------------------------------------------

@public_app.get("/v1/authored/articles")
@public_limiter.limit("120/minute")
async def list_authored_articles(
    request: Request,
    client_id: uuid.UUID = Depends(get_delivery_client_write),
    db: AsyncSession = Depends(get_session),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    status: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    slug: Optional[str] = Query(default=None),
) -> Response:
    """List all articles for the token's client at any status.

    Requires a write-scoped ppw_ token. A ppd_ read token receives 403.
    All responses carry Cache-Control: no-store.
    """
    # Validate status if provided — only "hidden" and "published" are valid.
    mapped_status = None
    if status is not None:
        if status == ArticleStatus.hidden.value:
            mapped_status = ArticleStatus.hidden
        elif status == ArticleStatus.published.value:
            mapped_status = ArticleStatus.published
        else:
            raise RequestValidationError(
                [{"loc": ("query", "status"), "msg": "status must be 'hidden' or 'published'", "type": "value_error"}]
            )

    # Slug exact-match path: normalize first (mirror the write path) then resolve.
    # Empty slug string falls through to the normal list (no filter).
    if slug is not None and slug.strip():
        normalized = slug_from_title(slug)
        article = await get_article_by_slug(db, client_id, normalized)
        # Apply status filter: a match at the wrong status returns empty.
        if article is not None and mapped_status is not None:
            actual_status = article.status.value if hasattr(article.status, "value") else str(article.status)
            if actual_status != mapped_status.value:
                article = None
        if article is None:
            body = {"data": [], "meta": {"page": 1, "page_size": page_size, "total": 0}}
        else:
            body = {"data": [_authored_list_item(article)], "meta": {"page": 1, "page_size": page_size, "total": 1}}
        return JSONResponse(content=body, headers={"Cache-Control": _CACHE_PRIVATE})

    # Normal paginated list.
    articles, total = await list_articles(
        db,
        client_id=client_id,
        status=mapped_status,
        tag=tag,
        category=category,
        page=page,
        page_size=page_size,
    )
    body = {
        "data": [_authored_list_item(a) for a in articles],
        "meta": {"page": page, "page_size": page_size, "total": total},
    }
    return JSONResponse(content=body, headers={"Cache-Control": _CACHE_PRIVATE})


@public_app.get("/v1/authored/articles/{article_id}")
@public_limiter.limit("120/minute")
async def get_authored_article(
    article_id: uuid.UUID,
    request: Request,
    client_id: uuid.UUID = Depends(get_delivery_client_write),
    db: AsyncSession = Depends(get_session),
) -> Response:
    """Return the full article by id for the token's client at any status.

    Requires a write-scoped ppw_ token. 404 for unknown id or another client's id —
    the two cases are indistinguishable by design (mirrors get_published_article).
    """
    article = await get_article(db, article_id)
    if article is None or article.client_id != client_id:
        return JSONResponse(
            status_code=404,
            content=_ARTICLE_NOT_FOUND,
            headers={"Cache-Control": _CACHE_PRIVATE},
        )

    seo = _build_seo(article)
    body = {
        **_authored_list_item(article),
        "html": _strip_scripts(article.html or ""),
        "meta_description": article.meta_description,
        "seo": seo,
    }
    return JSONResponse(content=body, headers={"Cache-Control": _CACHE_PRIVATE})


# ---------------------------------------------------------------------------
# Authored mutation endpoints — write-token required (Story 12.9)
#
# These deliberately cross the "never overwrite a live post" line that the POST
# create path guards with its 409 — but only through an unambiguous, id-targeted
# gesture. The POST create-flow guardrail and the public read routes are
# untouched. PUT is a full-content replace in place (published edits go live
# immediately, status unchanged, slug immutable). DELETE is a soft unpublish
# (status -> hidden), never a hard row delete. No generation/voice/fidelity code
# is ever invoked; content passes only through the render/sanitize pipeline.
# ---------------------------------------------------------------------------

@public_app.put("/v1/authored/articles/{article_id}")
@public_limiter.limit(_WRITE_RATE_LIMIT)
async def update_authored_article(
    article_id: uuid.UUID,
    request: Request,
    client_id: uuid.UUID = Depends(get_delivery_client_write),
    db: AsyncSession = Depends(get_session),
) -> Response:
    """Full-content replace of an existing article in place.

    Works for a hidden or a published target. Editing a published article is
    immediately live and keeps status='published'. The body is the article's
    complete new state: any omitted optional field is cleared to null.
    """
    # 1) Enforce the 200 KB body cap BEFORE parsing/rendering (413).
    raw_body = await request.body()
    if len(raw_body) > _MAX_BODY_BYTES:
        raise HTTPException(
            status_code=413,
            detail=_error_detail(
                "CONTENT_TOO_LARGE",
                f"Request body exceeds the {_MAX_BODY_BYTES // 1024} KB limit.",
            ),
            headers={"Cache-Control": "no-store"},
        )

    # 2) Parse + validate (422 nested shape via _validation_handler). A slug in the
    #    body is rejected here by extra='forbid'.
    try:
        payload = ArticleUpdateRequest.model_validate_json(raw_body)
    except ValueError as exc:
        raise RequestValidationError(_pydantic_errors(exc)) from exc

    # 3) Fetch + tenant check — identical 404 for missing or other-tenant.
    article = await get_article(db, article_id)
    if article is None or article.client_id != client_id:
        return JSONResponse(
            status_code=404,
            content=_ARTICLE_NOT_FOUND,
            headers={"Cache-Control": _CACHE_PRIVATE},
        )

    # 4) Content pipeline — render (markdown) then sanitize, or sanitize (html).
    #    No generation/voice; no house dash rule.
    if payload.format == "markdown":
        rendered = _render_markdown(payload.content)
        html = _sanitize_html(rendered)
    else:
        html = _sanitize_html(payload.content)

    # 5) Full replace. Every content field is passed (omitted -> None) so
    #    update_article_content clears absent fields. It auto-revisions only on a
    #    real change and recomputes reading_time when html changes.
    content_fields = {
        "title": payload.title,
        "html": html,
        "excerpt": payload.excerpt,
        "meta_description": payload.meta_description,
        "tags": payload.tags,
        "category": payload.category,
        "author": payload.author,
    }
    article = await update_article_content(db, article, content_fields, source="edit")
    # featured_image_* are not content-revision fields, so set them unconditionally
    # (None when omitted) — they obey the same full-replace rule as the text fields.
    image_changed = (
        article.featured_image_url != payload.featured_image_url
        or article.featured_image_alt != payload.featured_image_alt
    )
    article.featured_image_url = payload.featured_image_url
    article.featured_image_alt = payload.featured_image_alt
    # An image-only edit (identical text) does not reach update_article_content's
    # updated_at bump, so bump it here when only the image fields change. Otherwise
    # the updated_at-keyed detail/list ETag and the JSON-LD dateModified never flip,
    # and the new image never propagates to conditional or cached public consumers.
    if image_changed:
        article.updated_at = utcnow()
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return _ingest_response(article, updated=True, status_code=200)


@public_app.delete("/v1/authored/articles/{article_id}")
@public_limiter.limit(_WRITE_RATE_LIMIT)
async def unpublish_authored_article(
    article_id: uuid.UUID,
    request: Request,
    client_id: uuid.UUID = Depends(get_delivery_client_write),
    db: AsyncSession = Depends(get_session),
) -> Response:
    """Soft unpublish: take a published article down by flipping status to hidden.

    Reversible — the row, its content, and its revision history are preserved and
    it becomes recoverable via the app or a later PUT. Never a hard row delete.
    Idempotent: an already-hidden target is a 200 no-op with no status write.
    """
    # Tenant check — identical 404 for missing or other-tenant.
    article = await get_article(db, article_id)
    if article is None or article.client_id != client_id:
        return JSONResponse(
            status_code=404,
            content=_ARTICLE_NOT_FOUND,
            headers={"Cache-Control": _CACHE_PRIVATE},
        )

    status_value = article.status.value if hasattr(article.status, "value") else article.status
    if status_value == ArticleStatus.published.value:
        # set_article_status flips status without creating a revision.
        article = await set_article_status(db, article, ArticleStatus.hidden)
        await db.commit()
        await db.refresh(article)
    # Already hidden -> idempotent no-op (no status write, no commit needed).

    return _ingest_response(article, updated=True, status_code=200)
