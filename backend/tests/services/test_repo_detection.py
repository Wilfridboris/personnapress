"""Tests for services/repo_detection.py — framework detection engine."""
from unittest.mock import AsyncMock, patch

import pytest


def _root(*names: str) -> list[dict]:
    """Build a mock root listing from file/dir names."""
    items = []
    for name in names:
        item_type = "dir" if name.endswith("/") else "file"
        clean = name.rstrip("/")
        items.append({"name": clean, "type": item_type, "path": clean})
    return items


def _dir_contents(*names: str) -> list[dict]:
    """Build a non-empty directory listing (content doesn't matter for detection)."""
    return [{"name": n, "type": "file", "path": n} for n in names]


@pytest.mark.anyio
async def test_jekyll_detection_high_confidence():
    from app.services.repo_detection import detect_framework

    with (
        patch("app.services.repo_detection.get_repo_root_contents", AsyncMock(return_value=_root("_config.yml", "index.html"))),
        patch("app.services.repo_detection.get_directory_contents", AsyncMock(return_value=_dir_contents("2024-01-01-post.md"))),
    ):
        result = await detect_framework("token", "owner/repo")

    assert result["detected_framework"] == "jekyll"
    assert result["publish_path"] == "_posts/"
    assert result["confidence"] == "high"
    assert "_config.yml" in result["signals"]
    assert "_posts/" in result["signals"]
    assert result["candidates"] == []


@pytest.mark.anyio
async def test_astro_detection_high_confidence():
    from app.services.repo_detection import detect_framework

    dir_call_results = {
        "_posts": [],            # Jekyll secondary check — no _posts dir
        "src/content": _dir_contents("index.md"),
    }

    async def mock_dir(token, repo, path):
        return dir_call_results.get(path, [])

    with (
        patch("app.services.repo_detection.get_repo_root_contents", AsyncMock(return_value=_root("astro.config.ts"))),
        patch("app.services.repo_detection.get_directory_contents", AsyncMock(side_effect=mock_dir)),
    ):
        result = await detect_framework("token", "owner/repo")

    assert result["detected_framework"] == "astro"
    assert result["publish_path"] == "src/content/blog/"
    assert result["confidence"] == "high"
    assert "astro.config.ts" in result["signals"]
    assert "src/content/" in result["signals"]


@pytest.mark.anyio
async def test_jekyll_ambiguous_no_posts_dir():
    """_config.yml present but no _posts/ → Jekyll is a candidate, not a confident match."""
    from app.services.repo_detection import detect_framework

    with (
        patch("app.services.repo_detection.get_repo_root_contents", AsyncMock(return_value=_root("_config.yml"))),
        patch("app.services.repo_detection.get_directory_contents", AsyncMock(return_value=[])),
    ):
        result = await detect_framework("token", "owner/repo")

    # Single candidate → medium confidence, not unknown
    assert result["detected_framework"] == "jekyll"
    assert result["confidence"] == "medium"
    assert result["candidates"] == []
    assert "_config.yml" in result["signals"]


@pytest.mark.anyio
async def test_unknown_empty_root():
    """Empty root listing → unknown framework."""
    from app.services.repo_detection import detect_framework

    with (
        patch("app.services.repo_detection.get_repo_root_contents", AsyncMock(return_value=[])),
        patch("app.services.repo_detection.get_directory_contents", AsyncMock(return_value=[])),
    ):
        result = await detect_framework("token", "owner/repo")

    assert result["detected_framework"] == "unknown"
    assert result["publish_path"] == ""
    assert result["confidence"] == "low"
    assert result["candidates"] == []


@pytest.mark.anyio
async def test_priority_jekyll_wins_over_astro():
    """When Jekyll has full signals AND Astro has full signals, Jekyll wins (higher priority)."""
    from app.services.repo_detection import detect_framework

    dir_call_results = {
        "_posts": _dir_contents("2024-01-01-post.md"),
        "src/content": _dir_contents("index.md"),
    }

    async def mock_dir(token, repo, path):
        return dir_call_results.get(path, [])

    with (
        patch("app.services.repo_detection.get_repo_root_contents", AsyncMock(
            return_value=_root("_config.yml", "astro.config.ts")
        )),
        patch("app.services.repo_detection.get_directory_contents", AsyncMock(side_effect=mock_dir)),
    ):
        result = await detect_framework("token", "owner/repo")

    assert result["detected_framework"] == "jekyll"
    assert result["confidence"] == "high"


@pytest.mark.anyio
async def test_ambiguous_two_candidates():
    """Multiple partial matches → ambiguous result with candidates list."""
    from app.services.repo_detection import detect_framework

    with (
        patch("app.services.repo_detection.get_repo_root_contents", AsyncMock(
            return_value=_root("_config.yml", "astro.config.ts")
        )),
        patch("app.services.repo_detection.get_directory_contents", AsyncMock(return_value=[])),
    ):
        result = await detect_framework("token", "owner/repo")

    assert result["confidence"] == "low"
    assert len(result["candidates"]) == 2
    assert result["candidates"][0]["framework"] == "jekyll"
    assert result["candidates"][1]["framework"] == "astro"


@pytest.mark.anyio
async def test_eleventy_single_signal_high_confidence():
    """Eleventy .eleventy.js alone is enough for high confidence."""
    from app.services.repo_detection import detect_framework

    with (
        patch("app.services.repo_detection.get_repo_root_contents", AsyncMock(return_value=_root(".eleventy.js"))),
        patch("app.services.repo_detection.get_directory_contents", AsyncMock(return_value=[])),
    ):
        result = await detect_framework("token", "owner/repo")

    assert result["detected_framework"] == "eleventy"
    assert result["confidence"] == "high"
    assert result["publish_path"] == "src/posts/"


@pytest.mark.anyio
async def test_hugo_detection():
    from app.services.repo_detection import detect_framework

    dir_call_results = {"_posts": [], "content": _dir_contents("posts")}

    async def mock_dir(token, repo, path):
        return dir_call_results.get(path, [])

    with (
        patch("app.services.repo_detection.get_repo_root_contents", AsyncMock(return_value=_root("hugo.toml"))),
        patch("app.services.repo_detection.get_directory_contents", AsyncMock(side_effect=mock_dir)),
    ):
        result = await detect_framework("token", "owner/repo")

    assert result["detected_framework"] == "hugo"
    assert result["confidence"] == "high"
    assert result["publish_path"] == "content/posts/"


@pytest.mark.anyio
async def test_plain_static_detection():
    from app.services.repo_detection import detect_framework

    with (
        patch("app.services.repo_detection.get_repo_root_contents", AsyncMock(return_value=_root("index.html", ".nojekyll"))),
        patch("app.services.repo_detection.get_directory_contents", AsyncMock(return_value=[])),
    ):
        result = await detect_framework("token", "owner/repo")

    assert result["detected_framework"] == "plain_static"
    assert result["confidence"] == "high"
    assert result["publish_path"] == "/"
