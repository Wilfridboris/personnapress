"""Shared HTML sanitization helpers.

The allowed-image-src check is the server-side security boundary for image tags.
Only our own Supabase public-object URLs pass. No external URLs, no base64.

``_sanitize_html`` is the single HTML allowlist used by both the in-app article
editor (``routers/articles.py``) and the public ingestion API
(``routers/public_articles.py``). It lives here so neither router has to import
the other.
"""

import posixpath
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.core.config import settings

_ALLOWED_BUCKETS = ("article-images", "generated-images")

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
    "a": ["href", "title", "rel", "target"],
    "img": ["src", "alt", "width", "height"],
}
_BLOCK_TAGS = {
    "script", "style", "iframe", "object", "embed",
    # Dangerous structural/scripting tags that must be decomposed rather than unwrapped
    "template", "svg", "math", "use", "noscript",
}

_SAFE_HREF_SCHEMES = ("http://", "https://", "mailto:", "/", "#", "./", "../")


def is_allowed_image_src(src: str) -> bool:
    """Return True only for own-bucket public-object URLs.

    Fails closed when SUPABASE_URL is not set (local dev without storage):
    all img src values are rejected to prevent accidental storage bypass.

    Path traversal (e.g. .../article-images/../other/x.png) is blocked by
    normalising the URL path component before the prefix check.
    """
    if not settings.SUPABASE_URL:
        return False
    try:
        parsed = urlparse(src)
        base_parsed = urlparse(settings.SUPABASE_URL)
        if parsed.scheme != base_parsed.scheme or parsed.netloc != base_parsed.netloc:
            return False
        normalized_path = posixpath.normpath(parsed.path)
    except Exception:
        return False
    return any(
        normalized_path.startswith(f"/storage/v1/object/public/{bucket}/")
        for bucket in _ALLOWED_BUCKETS
    )


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
    # Restrict target to _blank only; remove any other value
    for a_tag in soup.find_all("a"):
        if a_tag.get("target") not in ("_blank", None):
            del a_tag["target"]
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
