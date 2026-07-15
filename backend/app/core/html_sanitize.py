"""Shared HTML sanitization helpers.

The allowed-image-src check is the server-side security boundary for image tags.
Only our own Supabase public-object URLs pass. No external URLs, no base64.
"""

import posixpath
from urllib.parse import urlparse

from app.core.config import settings

_ALLOWED_BUCKETS = ("article-images", "generated-images")


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
