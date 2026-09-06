"""Tests for backend/app/services/platform_limits.py.

Covers: weighted X counting with URLs, over_limit boundaries per platform,
sentence_boundary_truncate, and parity between backend and frontend limit constants.
"""
import re

import pytest


# ── Weighted X counting ───────────────────────────────────────────────────────

def test_x_count_no_url():
    from app.services.platform_limits import count_chars
    text = "Hello, world! This is a tweet."
    assert count_chars("x", text) == len(text)


def test_x_count_single_url_counted_as_23():
    from app.services.platform_limits import count_chars
    url = "https://example.com/some/very/long/path?query=value"
    text = f"Check this out {url}"
    # URL should count as 23 regardless of actual length
    expected = len(f"Check this out {'x' * 23}")
    assert count_chars("x", text) == expected


def test_x_count_multiple_urls():
    from app.services.platform_limits import count_chars
    url1 = "https://first.com/path"
    url2 = "https://second.com/another/path"
    text = f"Link 1 {url1} and link 2 {url2}"
    expected = len(f"Link 1 {'x' * 23} and link 2 {'x' * 23}")
    assert count_chars("x", text) == expected


def test_x_count_url_shorter_than_23_still_counts_as_23():
    from app.services.platform_limits import count_chars
    short_url = "https://x.co"  # shorter than 23 chars
    text = f"Hi {short_url}"
    expected = len(f"Hi {'x' * 23}")
    assert count_chars("x", text) == expected


def test_non_x_platform_uses_raw_length():
    from app.services.platform_limits import count_chars
    url = "https://example.com/some/very/long/path?query=value"
    text = f"Check this {url}"
    # linkedin, instagram, etc. use raw length
    assert count_chars("linkedin", text) == len(text)
    assert count_chars("instagram", text) == len(text)
    assert count_chars("threads", text) == len(text)


def test_empty_string_returns_zero():
    from app.services.platform_limits import count_chars
    assert count_chars("x", "") == 0
    assert count_chars("linkedin", "") == 0


# ── over_limit boundaries ─────────────────────────────────────────────────────

def test_over_limit_exactly_at_limit_returns_zero():
    from app.services.platform_limits import over_limit, HARD_LIMITS
    text = "a" * HARD_LIMITS["x"]
    assert over_limit("x", text) == 0


def test_over_limit_one_over_returns_one():
    from app.services.platform_limits import over_limit, HARD_LIMITS
    text = "a" * (HARD_LIMITS["x"] + 1)
    assert over_limit("x", text) == 1


def test_over_limit_under_limit_returns_zero():
    from app.services.platform_limits import over_limit, HARD_LIMITS
    text = "a" * (HARD_LIMITS["linkedin"] - 1)
    assert over_limit("linkedin", text) == 0


def test_over_limit_linkedin():
    from app.services.platform_limits import over_limit, HARD_LIMITS
    text = "a" * (HARD_LIMITS["linkedin"] + 50)
    assert over_limit("linkedin", text) == 50


def test_over_limit_threads():
    from app.services.platform_limits import over_limit, HARD_LIMITS
    text = "a" * (HARD_LIMITS["threads"] + 10)
    assert over_limit("threads", text) == 10


def test_over_limit_instagram():
    from app.services.platform_limits import over_limit, HARD_LIMITS
    text = "a" * (HARD_LIMITS["instagram"] + 5)
    assert over_limit("instagram", text) == 5


def test_over_limit_facebook_page():
    from app.services.platform_limits import over_limit, HARD_LIMITS
    text = "a" * (HARD_LIMITS["facebook_page"] + 1)
    assert over_limit("facebook_page", text) == 1


def test_over_limit_unknown_platform_returns_zero():
    from app.services.platform_limits import over_limit
    assert over_limit("unknown_platform", "a" * 10000) == 0


# ── sentence_boundary_truncate ────────────────────────────────────────────────

def test_truncate_within_limit_returns_unchanged():
    from app.services.platform_limits import sentence_boundary_truncate
    text = "Short text."
    assert sentence_boundary_truncate(text, 100) == text


def test_truncate_at_sentence_boundary():
    from app.services.platform_limits import sentence_boundary_truncate
    text = "First sentence. Second sentence. Third sentence."
    result = sentence_boundary_truncate(text, 32)
    assert result.endswith(".")
    assert len(result) <= 32
    assert "First sentence." in result


def test_truncate_no_ellipsis_appended():
    from app.services.platform_limits import sentence_boundary_truncate
    text = "First sentence. " + "x" * 300
    result = sentence_boundary_truncate(text, 50)
    assert not result.endswith("…")
    assert not result.endswith("...")


def test_truncate_exclamation_mark_boundary():
    from app.services.platform_limits import sentence_boundary_truncate
    text = "Great news! More details follow here and go on."
    result = sentence_boundary_truncate(text, 15)
    assert result.endswith("!")
    assert len(result) <= 15


def test_truncate_question_mark_boundary():
    from app.services.platform_limits import sentence_boundary_truncate
    text = "Did you know? This is interesting information."
    result = sentence_boundary_truncate(text, 14)
    assert result.endswith("?")
    assert len(result) <= 14


def test_truncate_falls_back_to_word_boundary_when_no_sentence():
    from app.services.platform_limits import sentence_boundary_truncate
    text = "one two three four five six seven eight"
    result = sentence_boundary_truncate(text, 15)
    assert len(result) <= 15
    assert not result.endswith(" ")


# ── Parity: backend constants match frontend platformLimits.ts ────────────────

def test_backend_frontend_limits_parity():
    """Parse frontend/lib/platformLimits.ts and confirm HARD_LIMITS match."""
    from app.services.platform_limits import HARD_LIMITS
    import pathlib

    frontend_file = pathlib.Path(__file__).parent.parent.parent / "frontend" / "lib" / "platformLimits.ts"
    assert frontend_file.exists(), f"Frontend limits file not found at {frontend_file}"
    content = frontend_file.read_text(encoding="utf-8")

    # Extract the HARD_LIMITS block values using regex
    # Pattern: matches "key": number inside the HARD_LIMITS object
    limits_block_match = re.search(r"HARD_LIMITS[^{]*\{([^}]+)\}", content, re.DOTALL)
    assert limits_block_match, "Could not find HARD_LIMITS block in frontend file"
    limits_block = limits_block_match.group(1)

    frontend_limits: dict[str, int] = {}
    for line in limits_block.splitlines():
        line = line.strip().strip(",")
        # Match: x: 280, or "facebook_page": 63206
        m = re.match(r'"?([a-z_A-Z0-9]+)"?\s*:\s*(\d+)', line)
        if m:
            frontend_limits[m.group(1)] = int(m.group(2))

    for platform, backend_limit in HARD_LIMITS.items():
        assert platform in frontend_limits, f"Platform {platform!r} missing from frontend HARD_LIMITS"
        assert frontend_limits[platform] == backend_limit, (
            f"Limit mismatch for {platform}: backend={backend_limit}, frontend={frontend_limits[platform]}"
        )
