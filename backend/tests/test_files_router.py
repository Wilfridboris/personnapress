"""Unit tests for routers/files.py."""
import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_client(user_id: uuid.UUID | None = None):
    c = MagicMock()
    c.id = uuid.uuid4()
    c.user_id = user_id or uuid.uuid4()
    c.name = "Acme"
    c.website_url = "https://acme.com"
    return c


def _make_upload_file(filename: str, content: bytes) -> MagicMock:
    uf = AsyncMock()
    uf.filename = filename
    uf.read = AsyncMock(return_value=content)
    return uf


# ── upload_files ──────────────────────────────────────────────────────────────

@patch("app.routers.files.supabase_storage.upload_file", new_callable=AsyncMock)
@patch("app.routers.files.supabase_storage.list_files", new_callable=AsyncMock)
@patch("app.routers.files._get_owned_client", new_callable=AsyncMock)
async def test_upload_valid_txt_file(mock_get_client, mock_list, mock_upload):
    from app.routers.files import upload_files

    client_id = uuid.uuid4()
    user_id = uuid.uuid4()
    client = _make_client(user_id=user_id)
    mock_get_client.return_value = client
    mock_list.return_value = []  # no existing files
    mock_upload.return_value = None

    uf = _make_upload_file("post.txt", b"Hello there!")
    result = await upload_files(
        client_id=client_id,
        files=[uf],
        current_user={"user_id": str(user_id)},
        db=AsyncMock(),
    )

    assert len(result.uploaded) == 1
    assert result.uploaded[0].filename == "post.txt"
    assert len(result.errors) == 0
    mock_upload.assert_called_once()


@patch("app.routers.files._get_owned_client", new_callable=AsyncMock)
async def test_upload_rejects_invalid_extension(mock_get_client):
    from app.routers.files import upload_files

    mock_get_client.return_value = _make_client()
    uf = _make_upload_file("image.png", b"data")

    with patch("app.routers.files.supabase_storage.list_files", new_callable=AsyncMock, return_value=[]):
        result = await upload_files(
            client_id=uuid.uuid4(),
            files=[uf],
            current_user={"user_id": str(uuid.uuid4())},
            db=AsyncMock(),
        )

    assert len(result.uploaded) == 0
    assert len(result.errors) == 1
    assert "supported" in result.errors[0].error.lower()


@patch("app.routers.files._get_owned_client", new_callable=AsyncMock)
async def test_upload_rejects_oversized_file(mock_get_client):
    from app.routers.files import upload_files, MAX_FILE_SIZE

    mock_get_client.return_value = _make_client()
    big_content = b"x" * (MAX_FILE_SIZE + 1)
    uf = _make_upload_file("big.txt", big_content)

    with patch("app.routers.files.supabase_storage.list_files", new_callable=AsyncMock, return_value=[]):
        result = await upload_files(
            client_id=uuid.uuid4(),
            files=[uf],
            current_user={"user_id": str(uuid.uuid4())},
            db=AsyncMock(),
        )

    assert len(result.uploaded) == 0
    assert len(result.errors) == 1
    assert "5 MB" in result.errors[0].error


@patch("app.routers.files._get_owned_client", new_callable=AsyncMock)
async def test_upload_rejects_when_limit_reached(mock_get_client):
    from app.routers.files import upload_files, FILE_LIMIT

    mock_get_client.return_value = _make_client()
    uf = _make_upload_file("new.txt", b"content")

    # Simulate existing files at limit
    existing = [{"name": f"file{i}.txt", "metadata": {"size": 100}} for i in range(FILE_LIMIT)]

    with patch("app.routers.files.supabase_storage.list_files", new_callable=AsyncMock, return_value=existing):
        result = await upload_files(
            client_id=uuid.uuid4(),
            files=[uf],
            current_user={"user_id": str(uuid.uuid4())},
            db=AsyncMock(),
        )

    assert len(result.uploaded) == 0
    assert len(result.errors) == 1
    assert "10-file limit" in result.errors[0].error


# ── list_client_files ─────────────────────────────────────────────────────────

@patch("app.routers.files.supabase_storage.list_files", new_callable=AsyncMock)
@patch("app.routers.files._get_owned_client", new_callable=AsyncMock)
async def test_list_files_returns_file_items(mock_get_client, mock_list):
    from app.routers.files import list_client_files

    mock_get_client.return_value = _make_client()
    mock_list.return_value = [
        {"name": "post.txt", "metadata": {"size": 1024}},
        {"name": "readme.md", "metadata": {"size": 512}},
    ]

    result = await list_client_files(
        client_id=uuid.uuid4(),
        current_user={"user_id": str(uuid.uuid4())},
        db=AsyncMock(),
    )

    assert result.count == 2
    assert result.limit == 10
    filenames = {f.filename for f in result.files}
    assert "post.txt" in filenames
    assert "readme.md" in filenames


@patch("app.routers.files.supabase_storage.list_files", new_callable=AsyncMock)
@patch("app.routers.files._get_owned_client", new_callable=AsyncMock)
async def test_list_files_handles_storage_error(mock_get_client, mock_list):
    from app.routers.files import list_client_files

    mock_get_client.return_value = _make_client()
    mock_list.side_effect = Exception("Storage unavailable")

    result = await list_client_files(
        client_id=uuid.uuid4(),
        current_user={"user_id": str(uuid.uuid4())},
        db=AsyncMock(),
    )

    # Should gracefully return empty list instead of crashing
    assert result.count == 0
    assert result.files == []


# ── delete_client_file ────────────────────────────────────────────────────────

@patch("app.routers.files.supabase_storage.delete_file", new_callable=AsyncMock)
@patch("app.routers.files._get_owned_client", new_callable=AsyncMock)
async def test_delete_file_returns_204(mock_get_client, mock_delete):
    from app.routers.files import delete_client_file

    mock_get_client.return_value = _make_client()
    mock_delete.return_value = None

    response = await delete_client_file(
        client_id=uuid.uuid4(),
        filename="post.txt",
        current_user={"user_id": str(uuid.uuid4())},
        db=AsyncMock(),
    )

    assert response.status_code == 204
    mock_delete.assert_called_once()


@patch("app.routers.files.supabase_storage.delete_file", new_callable=AsyncMock)
@patch("app.routers.files._get_owned_client", new_callable=AsyncMock)
async def test_delete_file_storage_error_returns_500(mock_get_client, mock_delete):
    from app.routers.files import delete_client_file

    mock_get_client.return_value = _make_client()
    mock_delete.side_effect = Exception("Storage error")

    with pytest.raises(HTTPException) as exc_info:
        await delete_client_file(
            client_id=uuid.uuid4(),
            filename="post.txt",
            current_user={"user_id": str(uuid.uuid4())},
            db=AsyncMock(),
        )

    assert exc_info.value.status_code == 500


# ── _get_owned_client ─────────────────────────────────────────────────────────

async def test_get_owned_client_raises_401_on_bad_session():
    from app.routers.files import _get_owned_client

    with pytest.raises(HTTPException) as exc_info:
        await _get_owned_client(uuid.uuid4(), {}, AsyncMock())

    assert exc_info.value.status_code == 401


async def test_get_owned_client_raises_404_when_not_found():
    from app.routers.files import _get_owned_client

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    user_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc_info:
        await _get_owned_client(uuid.uuid4(), {"user_id": str(user_id)}, db)

    assert exc_info.value.status_code == 404


async def test_get_owned_client_raises_403_wrong_owner():
    from app.routers.files import _get_owned_client

    owner_id = uuid.uuid4()
    requester_id = uuid.uuid4()
    client = _make_client(user_id=owner_id)

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = client
    db.execute = AsyncMock(return_value=result_mock)

    with pytest.raises(HTTPException) as exc_info:
        await _get_owned_client(client.id, {"user_id": str(requester_id)}, db)

    assert exc_info.value.status_code == 403


# ── upload_files: valid .md and .docx extensions ─────────────────────────────

@patch("app.routers.files.supabase_storage.upload_file", new_callable=AsyncMock)
@patch("app.routers.files.supabase_storage.list_files", new_callable=AsyncMock)
@patch("app.routers.files._get_owned_client", new_callable=AsyncMock)
async def test_upload_valid_md_file(mock_get_client, mock_list, mock_upload):
    from app.routers.files import upload_files

    mock_get_client.return_value = _make_client()
    mock_list.return_value = []
    mock_upload.return_value = None

    uf = _make_upload_file("notes.md", b"# My Notes\n\nSome text.")
    result = await upload_files(
        client_id=uuid.uuid4(),
        files=[uf],
        current_user={"user_id": str(uuid.uuid4())},
        db=AsyncMock(),
    )

    assert len(result.uploaded) == 1
    assert result.uploaded[0].filename == "notes.md"
    assert len(result.errors) == 0


@patch("app.routers.files.supabase_storage.upload_file", new_callable=AsyncMock)
@patch("app.routers.files.supabase_storage.list_files", new_callable=AsyncMock)
@patch("app.routers.files._get_owned_client", new_callable=AsyncMock)
async def test_upload_valid_docx_file(mock_get_client, mock_list, mock_upload):
    from app.routers.files import upload_files

    mock_get_client.return_value = _make_client()
    mock_list.return_value = []
    mock_upload.return_value = None

    uf = _make_upload_file("brand.docx", b"PK\x03\x04fake-docx-bytes")
    result = await upload_files(
        client_id=uuid.uuid4(),
        files=[uf],
        current_user={"user_id": str(uuid.uuid4())},
        db=AsyncMock(),
    )

    assert len(result.uploaded) == 1
    assert result.uploaded[0].filename == "brand.docx"
    assert len(result.errors) == 0


# ── upload_files: partial success (mix valid + invalid in one request) ────────

@patch("app.routers.files.supabase_storage.upload_file", new_callable=AsyncMock)
@patch("app.routers.files.supabase_storage.list_files", new_callable=AsyncMock)
@patch("app.routers.files._get_owned_client", new_callable=AsyncMock)
async def test_upload_partial_success_mixed_files(mock_get_client, mock_list, mock_upload):
    from app.routers.files import upload_files

    mock_get_client.return_value = _make_client()
    mock_list.return_value = []
    mock_upload.return_value = None

    valid_file = _make_upload_file("good.txt", b"valid content")
    invalid_file = _make_upload_file("bad.png", b"image data")

    result = await upload_files(
        client_id=uuid.uuid4(),
        files=[valid_file, invalid_file],
        current_user={"user_id": str(uuid.uuid4())},
        db=AsyncMock(),
    )

    assert len(result.uploaded) == 1
    assert result.uploaded[0].filename == "good.txt"
    assert len(result.errors) == 1
    assert result.errors[0].filename == "bad.png"


# ── upload_files: storage exception per-file → error returned, continues ──────

@patch("app.routers.files.supabase_storage.upload_file", new_callable=AsyncMock)
@patch("app.routers.files.supabase_storage.list_files", new_callable=AsyncMock)
@patch("app.routers.files._get_owned_client", new_callable=AsyncMock)
async def test_upload_storage_exception_returns_error_entry(mock_get_client, mock_list, mock_upload):
    from app.routers.files import upload_files

    mock_get_client.return_value = _make_client()
    mock_list.return_value = []
    mock_upload.side_effect = Exception("Storage unavailable")

    uf = _make_upload_file("post.txt", b"content")
    result = await upload_files(
        client_id=uuid.uuid4(),
        files=[uf],
        current_user={"user_id": str(uuid.uuid4())},
        db=AsyncMock(),
    )

    assert len(result.uploaded) == 0
    assert len(result.errors) == 1
    assert "upload failed" in result.errors[0].error.lower()


# ── list_client_files: file entry with None metadata defaults size to 0 ───────

@patch("app.routers.files.supabase_storage.list_files", new_callable=AsyncMock)
@patch("app.routers.files._get_owned_client", new_callable=AsyncMock)
async def test_list_files_none_metadata_defaults_size_zero(mock_get_client, mock_list):
    from app.routers.files import list_client_files

    mock_get_client.return_value = _make_client()
    # Supabase may return entries with null metadata
    mock_list.return_value = [
        {"name": "nosize.txt", "metadata": None},
    ]

    result = await list_client_files(
        client_id=uuid.uuid4(),
        current_user={"user_id": str(uuid.uuid4())},
        db=AsyncMock(),
    )

    assert result.count == 1
    assert result.files[0].size == 0


# ── upload_files: response includes correct path format ───────────────────────

@patch("app.routers.files.supabase_storage.upload_file", new_callable=AsyncMock)
@patch("app.routers.files.supabase_storage.list_files", new_callable=AsyncMock)
@patch("app.routers.files._get_owned_client", new_callable=AsyncMock)
async def test_upload_response_contains_correct_path(mock_get_client, mock_list, mock_upload):
    from app.routers.files import upload_files

    client_id = uuid.uuid4()
    mock_get_client.return_value = _make_client()
    mock_list.return_value = []
    mock_upload.return_value = None

    uf = _make_upload_file("article.txt", b"text content")
    result = await upload_files(
        client_id=client_id,
        files=[uf],
        current_user={"user_id": str(uuid.uuid4())},
        db=AsyncMock(),
    )

    assert len(result.uploaded) == 1
    # Path must follow convention: {client_id}/{filename}
    assert result.uploaded[0].path == f"{client_id}/article.txt"
    assert result.uploaded[0].size == len(b"text content")
