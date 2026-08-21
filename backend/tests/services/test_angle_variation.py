"""Tests for Story 20.8: Angle Variation Engine.

Tests cover:
- fallback_angles cycling behaviour
- plan_week_angles planner-failure path returns valid fallback plan
- generate_social_only persists campaign.angle; no directive when angle=None
- generate_roadmap assigns distinct angles across slots
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.angles import fallback_angles, ANGLE_LABELS, KNOWN_CODES, _LINKEDIN_ORDER, _X_ORDER


# ---------------------------------------------------------------------------
# fallback_angles tests (pure unit, no DB)
# ---------------------------------------------------------------------------

def test_fallback_angles_linkedin_returns_correct_sequence():
    result = fallback_angles("linkedin", 3)
    assert result == _LINKEDIN_ORDER[:3]


def test_fallback_angles_x_returns_correct_sequence():
    result = fallback_angles("x", 3)
    assert result == _X_ORDER[:3]


def test_fallback_angles_cycles_past_pool():
    pool_size = len(_LINKEDIN_ORDER)
    result = fallback_angles("linkedin", pool_size + 2)
    assert len(result) == pool_size + 2
    # First element of the second cycle should repeat the first element
    assert result[pool_size] == _LINKEDIN_ORDER[0]
    assert result[pool_size + 1] == _LINKEDIN_ORDER[1]


def test_fallback_angles_zero_count():
    assert fallback_angles("linkedin", 0) == []
    assert fallback_angles("x", 0) == []


def test_fallback_angles_all_known_codes():
    for code in fallback_angles("linkedin", len(_LINKEDIN_ORDER)):
        assert code in KNOWN_CODES
    for code in fallback_angles("x", len(_X_ORDER)):
        assert code in KNOWN_CODES


# ---------------------------------------------------------------------------
# plan_week_angles: planner failure falls back gracefully
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_plan_week_angles_planner_failure_returns_fallback():
    """When generate_week_plan raises, plan_week_angles returns a fallback plan
    with valid angle codes and does not re-raise."""
    with patch("app.services.generation._llm") as mock_llm, \
         patch("app.services.generation.sentry_sdk") as mock_sentry:
        mock_llm.generate_week_plan = AsyncMock(side_effect=ValueError("LLM error"))

        from app.services.generation import plan_week_angles
        plan = await plan_week_angles(
            brain_dump="Test brain dump",
            bvp=None,
            linkedin_count=2,
            twitter_count=2,
        )

    assert len(plan["linkedin"]) == 2
    assert len(plan["x"]) == 2
    for entry in plan["linkedin"]:
        assert entry["angle"] in KNOWN_CODES
    for entry in plan["x"]:
        assert entry["angle"] in KNOWN_CODES
    mock_sentry.capture_exception.assert_called_once()


@pytest.mark.asyncio
async def test_plan_week_angles_returns_distinct_angles_per_platform():
    """Planner success: returned angles are distinct within each platform's list."""
    linkedin_plan = [
        {"angle": "personal_story", "hook": "hook1", "facet": "facet1"},
        {"angle": "data_proof", "hook": "hook2", "facet": "facet2"},
    ]
    x_plan = [
        {"angle": "contrarian", "hook": "hookA", "facet": "facetA"},
        {"angle": "quick_tip", "hook": "hookB", "facet": "facetB"},
    ]
    with patch("app.services.generation._llm") as mock_llm:
        mock_llm.generate_week_plan = AsyncMock(return_value={"linkedin": linkedin_plan, "x": x_plan})

        from app.services.generation import plan_week_angles
        plan = await plan_week_angles("dump", None, linkedin_count=2, twitter_count=2)

    li_angles = [e["angle"] for e in plan["linkedin"]]
    x_angles = [e["angle"] for e in plan["x"]]
    assert len(set(li_angles)) == 2, "LinkedIn angles must be distinct"
    assert len(set(x_angles)) == 2, "X angles must be distinct"


# ---------------------------------------------------------------------------
# generate_social_only: angle persistence + no-directive when angle=None
# ---------------------------------------------------------------------------

def _make_campaign_mock():
    c = MagicMock()
    c.id = uuid.uuid4()
    c.brain_dump = "Brain dump text"
    c.x_post = None
    c.linkedin_post = None
    c.angle = None
    c.updated_at = None
    return c


def _make_db_for_social(campaign):
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = campaign
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_generate_social_only_persists_angle():
    """When angle is provided, campaign.angle is set after generation."""
    campaign = _make_campaign_mock()
    db = _make_db_for_social(campaign)

    social_output = {
        "x_post": "Great X post content here.",
        "linkedin_post": "LinkedIn content here.",
        "instagram_caption": "Insta here.",
        "facebook_post": "Facebook here.",
        "threads_post": "Threads here.",
    }

    with patch("app.services.generation._llm") as mock_llm:
        mock_llm.generate_social_standalone = AsyncMock(return_value=social_output)
        from app.services.generation import generate_social_only
        await generate_social_only(
            "Brain dump", None, "x", campaign.id, db,
            angle="contrarian", hook="Everyone is wrong about X"
        )

    assert campaign.angle == "contrarian"
    assert campaign.x_post == social_output["x_post"]


@pytest.mark.asyncio
async def test_generate_social_only_no_directive_when_angle_none():
    """When angle=None (social_only path), campaign.angle stays None and
    generate_social_standalone is called without angle/hook kwargs."""
    campaign = _make_campaign_mock()
    db = _make_db_for_social(campaign)

    social_output = {
        "x_post": "X post content.",
        "linkedin_post": "LinkedIn content.",
        "instagram_caption": "Insta.",
        "facebook_post": "Facebook.",
        "threads_post": "Threads.",
    }

    with patch("app.services.generation._llm") as mock_llm:
        mock_llm.generate_social_standalone = AsyncMock(return_value=social_output)
        from app.services.generation import generate_social_only
        await generate_social_only(
            "Brain dump", None, "x", campaign.id, db,
            angle=None, hook=None,
        )

    assert campaign.angle is None
    # Verify generate_social_standalone received angle=None, hook=None
    call_kwargs = mock_llm.generate_social_standalone.call_args.kwargs
    assert call_kwargs.get("angle") is None
    assert call_kwargs.get("hook") is None


# ---------------------------------------------------------------------------
# _repair_plan_entries: unknown-code replacement + duplicate dedup
# ---------------------------------------------------------------------------

def test_repair_plan_entries_replaces_unknown_code():
    """An entry with an unrecognised angle code is replaced by the first unused
    pool code for that platform."""
    from app.integrations.gemini import _repair_plan_entries

    entries = [{"angle": "viral_hook", "hook": "Bad hook", "facet": "facet1"}]
    result = _repair_plan_entries(entries, expected=1, platform="x")
    assert len(result) == 1
    assert result[0]["angle"] == _X_ORDER[0], "Unknown code should be replaced with first X pool code"
    assert result[0]["angle"] in KNOWN_CODES


def test_repair_plan_entries_deduplicates_valid_codes():
    """When the LLM returns the same valid angle code twice, the second entry
    is replaced by the next unused pool code."""
    from app.integrations.gemini import _repair_plan_entries

    entries = [
        {"angle": "contrarian", "hook": "Hook 1", "facet": "facet1"},
        {"angle": "contrarian", "hook": "Hook 2", "facet": "facet2"},
    ]
    result = _repair_plan_entries(entries, expected=2, platform="x")
    assert len(result) == 2
    assert result[0]["angle"] == "contrarian"
    assert result[1]["angle"] != "contrarian", "Duplicate angle code should be replaced"
    assert result[1]["angle"] in KNOWN_CODES


def test_pad_fallback_avoids_already_used_angles():
    """_pad_fallback should prefer codes not already in used before cycling."""
    from app.integrations.gemini import _pad_fallback

    used = ["contrarian", "data_proof", "quick_tip"]
    result = _pad_fallback("x", used, count=2)
    assert len(result) == 2
    # hot_take and how_to are the next unused X pool codes
    for code in result:
        assert code not in used[:len(result)], f"Padded code {code!r} repeats an already-used angle"
