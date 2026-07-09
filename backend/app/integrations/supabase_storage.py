"""Supabase Storage integration via REST API.

Uses httpx to call the Supabase Storage REST API directly.
Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in config.
"""

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

def _content_type_for_path(path: str) -> str:
    """Return the correct MIME type for a storage path based on its extension."""
    lower = path.lower()
    if lower.endswith(".txt"):
        return "text/plain"
    if lower.endswith(".md"):
        return "text/markdown"
    if lower.endswith(".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "application/octet-stream"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
    }


def _storage_url(path: str) -> str:
    base = settings.SUPABASE_URL.rstrip("/")
    return f"{base}/storage/v1{path}"


async def _ensure_bucket(client: httpx.AsyncClient, bucket: str, public: bool = False) -> None:
    """Create bucket if it does not already exist (409 = already exists, ignored)."""
    url = _storage_url("/bucket")
    resp = await client.post(
        url,
        json={"id": bucket, "name": bucket, "public": public},
        headers=_headers(),
    )
    if resp.status_code not in (200, 201, 409):
        logger.warning("_ensure_bucket: %s → %d %s", bucket, resp.status_code, resp.text)


async def upload_file(bucket: str, path: str, file_bytes: bytes) -> None:
    """Upload file_bytes to Supabase Storage at bucket/path.

    Auto-creates the bucket on first use if it doesn't exist.
    Raises httpx.HTTPStatusError on failure.
    """
    url = _storage_url(f"/object/{bucket}/{path}")
    content_type = _content_type_for_path(path)
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            url,
            content=file_bytes,
            headers={
                **_headers(),
                "Content-Type": content_type,
                "x-upsert": "true",  # overwrite if exists
            },
        )
        if resp.status_code == 400 and "Bucket not found" in resp.text:
            logger.info("upload_file: bucket %r not found — creating it", bucket)
            await _ensure_bucket(client, bucket, public=False)
            resp = await client.post(
                url,
                content=file_bytes,
                headers={
                    **_headers(),
                    "Content-Type": content_type,
                    "x-upsert": "true",
                },
            )
        if not resp.is_success:
            logger.error(
                "upload_file: Supabase Storage %d for %s/%s — %s",
                resp.status_code,
                bucket,
                path,
                resp.text,
            )
        resp.raise_for_status()


async def list_files(bucket: str, prefix: str) -> list[dict[str, Any]]:
    """List files in bucket under prefix.

    Returns list of dicts with at least {"name": str, "metadata": {"size": int}}.
    Returns empty list if storage is not configured.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("Supabase storage not configured — returning empty file list")
        return []

    url = _storage_url(f"/object/list/{bucket}")
    payload = {"prefix": prefix, "limit": 100, "offset": 0}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=_headers())
        resp.raise_for_status()
        return resp.json()  # type: ignore[return-value]


async def download_file(bucket: str, path: str) -> bytes:
    """Download a file from Supabase Storage.

    Returns raw bytes. Raises httpx.HTTPStatusError on failure.
    """
    url = _storage_url(f"/object/{bucket}/{path}")
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(url, headers=_headers())
        resp.raise_for_status()
        return resp.content


async def upload_image_from_url(replicate_url: str, storage_path: str) -> str:
    """Download an image from a Replicate URL and upload it to Supabase Storage.

    Args:
        replicate_url: Temporary Replicate CDN URL to download from.
        storage_path: Supabase Storage path (e.g. generated-images/{id}/featured.png).

    Returns:
        Public CDN URL of the uploaded image, or the Replicate URL if Supabase is not configured.

    Raises:
        httpx.HTTPStatusError: On download or upload failure.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        logger.warning(
            "Supabase storage not configured — storing Replicate URL directly (temporary URL, will expire)"
        )
        return replicate_url

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(replicate_url)
        response.raise_for_status()
        image_bytes = response.content

    bucket = "generated-images"
    prefix = f"{bucket}/"
    if not storage_path.startswith(prefix):
        raise ValueError(f"storage_path must start with '{prefix}', got: {storage_path!r}")
    object_path = storage_path[len(prefix):]

    await upload_file(bucket, object_path, image_bytes)

    base = settings.SUPABASE_URL.rstrip("/")
    public_url = f"{base}/storage/v1/object/public/{bucket}/{object_path}"
    return public_url


async def delete_file(bucket: str, path: str) -> None:
    """Delete a file from Supabase Storage."""
    url = _storage_url(f"/object/{bucket}/{path}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.delete(url, headers=_headers())
        resp.raise_for_status()
