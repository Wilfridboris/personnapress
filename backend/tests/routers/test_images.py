"""Tests for image upload endpoint (routers/images.py).

Covers:
  - Happy path: valid PNG upload → upload_file called with correct args, URL returned
  - Ownership: 403 when client belongs to another user, 404 when client not found
  - 401 on invalid session
  - 400 on oversize file
  - 400 on unsupported extension
  - 400 on magic-byte mismatch (e.g., .png named but exe bytes inside)
"""

import uuid
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_client(user_id=None, client_id=None):
    c = MagicMock()
    c.id = client_id or uuid.uuid4()
    c.user_id = user_id or uuid.uuid4()
    return c


def _make_upload_file(filename="photo.png", content=b"\x89PNG\r\n\x1a\ndata"):
    f = MagicMock()
    f.filename = filename
    f.read = AsyncMock(return_value=content)
    return f


def _make_db():
    db = AsyncMock()
    return db


# PNG magic bytes (minimal valid header)
_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
# JPEG magic bytes
_JPG = b"\xff\xd8\xff" + b"\x00" * 100
# WEBP magic bytes
_WEBP = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 100
# EXE magic bytes
_EXE = b"MZ" + b"\x00" * 100


# ── Happy path ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_image_success_png():
    """Valid PNG upload stores to article-images bucket with public=True and returns URL."""
    from app.routers.images import upload_image

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = _make_db()
    upload_file = _make_upload_file("photo.png", _PNG)

    with (
        patch("app.routers.images._get_owned_client", AsyncMock(return_value=client)),
        patch("app.routers.images.supabase_storage.upload_file", AsyncMock()) as mock_upload,
        patch("app.routers.images.supabase_storage.public_object_url", return_value="https://supabase.io/storage/v1/object/public/article-images/some/path.png"),
    ):
        result = await upload_image(
            client_id=client.id,
            file=upload_file,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert result.url == "https://supabase.io/storage/v1/object/public/article-images/some/path.png"
    mock_upload.assert_awaited_once()
    call_args = mock_upload.call_args
    bucket, path, file_bytes, *rest = call_args.args
    public_kwarg = call_args.kwargs.get("public", rest[0] if rest else None)
    assert bucket == "article-images"
    assert path.startswith(str(client.id))
    assert path.endswith(".png")
    assert public_kwarg is True


@pytest.mark.asyncio
async def test_upload_image_success_webp():
    """WEBP upload is accepted and stored correctly."""
    from app.routers.images import upload_image

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = _make_db()
    upload_file = _make_upload_file("banner.webp", _WEBP)

    with (
        patch("app.routers.images._get_owned_client", AsyncMock(return_value=client)),
        patch("app.routers.images.supabase_storage.upload_file", AsyncMock()),
        patch("app.routers.images.supabase_storage.public_object_url", return_value="https://example.com/banner.webp"),
    ):
        result = await upload_image(
            client_id=client.id,
            file=upload_file,
            current_user={"user_id": str(user_id)},
            db=db,
        )

    assert "webp" in result.url


# ── 401 no session ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_image_401_invalid_session():
    """An invalid session token (non-UUID user_id) is rejected with 401.

    Spec Task 7.1 listed this test explicitly.  The 401 is raised inside
    _get_owned_client when uuid.UUID(user_id) fails.
    """
    from app.routers.images import upload_image

    db = _make_db()
    upload_file = _make_upload_file("photo.png", _PNG)

    with pytest.raises(HTTPException) as exc_info:
        await upload_image(
            client_id=uuid.uuid4(),
            file=upload_file,
            current_user={"user_id": "not-a-valid-uuid"},
            db=db,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error"]["code"] == "INVALID_SESSION"


# ── Ownership ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_image_403_wrong_owner():
    """User B cannot upload to user A's client."""
    from app.routers.images import upload_image

    user_id = uuid.uuid4()
    db = _make_db()
    upload_file = _make_upload_file("photo.png", _PNG)

    with patch(
        "app.routers.images._get_owned_client",
        AsyncMock(side_effect=HTTPException(
            status_code=403,
            detail={"error": {"code": "FORBIDDEN", "message": "Access denied.", "detail": {}}},
        )),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await upload_image(
                client_id=uuid.uuid4(),
                file=upload_file,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_upload_image_404_client_not_found():
    """Returns 404 when the client does not exist."""
    from app.routers.images import upload_image

    user_id = uuid.uuid4()
    db = _make_db()
    upload_file = _make_upload_file("photo.png", _PNG)

    with patch(
        "app.routers.images._get_owned_client",
        AsyncMock(side_effect=HTTPException(
            status_code=404,
            detail={"error": {"code": "CLIENT_NOT_FOUND", "message": "Client not found.", "detail": {}}},
        )),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await upload_image(
                client_id=uuid.uuid4(),
                file=upload_file,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 404


# ── Validation rejections ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_image_400_oversize():
    """Files over 5 MB are rejected with FILE_TOO_LARGE."""
    from app.routers.images import upload_image

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = _make_db()
    big_content = _PNG + b"\x00" * (5 * 1024 * 1024 + 1)
    upload_file = _make_upload_file("photo.png", big_content)

    with patch("app.routers.images._get_owned_client", AsyncMock(return_value=client)):
        with pytest.raises(HTTPException) as exc_info:
            await upload_image(
                client_id=client.id,
                file=upload_file,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_upload_image_400_bad_extension():
    """Files with unsupported extensions (e.g. .gif) are rejected with INVALID_IMAGE_TYPE."""
    from app.routers.images import upload_image

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = _make_db()
    upload_file = _make_upload_file("animation.gif", b"GIF89a")

    with patch("app.routers.images._get_owned_client", AsyncMock(return_value=client)):
        with pytest.raises(HTTPException) as exc_info:
            await upload_image(
                client_id=client.id,
                file=upload_file,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "INVALID_IMAGE_TYPE"


@pytest.mark.asyncio
async def test_upload_image_400_magic_byte_mismatch():
    """A .png-named file with EXE magic bytes is rejected as INVALID_IMAGE."""
    from app.routers.images import upload_image

    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    db = _make_db()
    upload_file = _make_upload_file("notreally.png", _EXE)

    with patch("app.routers.images._get_owned_client", AsyncMock(return_value=client)):
        with pytest.raises(HTTPException) as exc_info:
            await upload_image(
                client_id=client.id,
                file=upload_file,
                current_user={"user_id": str(user_id)},
                db=db,
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"]["code"] == "INVALID_IMAGE"
