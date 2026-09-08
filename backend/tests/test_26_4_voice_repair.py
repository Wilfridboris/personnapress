"""Tests for Story 26.4: Fidelity repair loop and per-mode voice differentiation.

Coverage:
- repair triggered on each failing dimension independently
- does not fire on passing scores
- better-score-wins selection (both directions)
- single-call bound (mock call counts)
- repair exception falls back cleanly
- repaired flag and initial/final persisted
- flat keys hold final values
- per-surface prompt differentiation (pairwise inequality)
- X punchier line present
- LinkedIn compressed brief is exactly 2 sentences
- template voice lines present/absent per template
- assist-mode invariance (no repair, voice_score stays None)
"""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.generation_prompts import (
    _build_template_voice_line,
    _build_voice_injection,
    build_voice_for_surface,
)


# ── Shared fixtures ───────────────────────────────────────────────────────────

_BVP = {
    "voice_brief": "Direct, data-driven writer who opens with a bold claim. Second sentence context here.",
    "tone": ["authoritative", "direct"],
    "cadence": {"avg_sentence_length": 14, "variation_pattern": "", "paragraph_structure": ""},
    "banned_jargon": ["leverage", "synergy"],
    "opening_pattern": "bold_claim",
    "closing_pattern": "question",
    "post_structure_template": "hook -- pain -- insight -- CTA",
    "casing_style": "lowercase_leaning",
}

_BLOG_HTML = "<h1>Test Title</h1><p>Body text here.</p>"

_PASSING_SCORE = {
    "tone_score": 9,
    "cadence_score": 8,
    "jargon_violations": 0,
    "seo_bluf_present": True,
    "seo_h2_count": 3,
    "seo_faq_present": True,
    "seo_fluff_detected": False,
    "authored_passages_preserved": True,
    "tags": ["content"],
}

_FAILING_TONE_SCORE = {
    **_PASSING_SCORE,
    "tone_score": 5,
}

_FAILING_CADENCE_SCORE = {
    **_PASSING_SCORE,
    "cadence_score": 4,
}

_FAILING_JARGON_SCORE = {
    **_PASSING_SCORE,
    "jargon_violations": 2,
}

_SOCIAL = {
    "x_post": "Tweet!",
    "linkedin_post": "LinkedIn post " * 40,
    "instagram_caption": "Instagram caption with hashtags #test #social",
    "facebook_post": "Facebook post content for the campaign",
    "threads_post": "Threads hot take right here.",
}


def _make_job(campaign_id=None):
    job = MagicMock()
    job.id = uuid.uuid4()
    job.campaign_id = campaign_id or uuid.uuid4()
    job.status = "pending"
    job.started_at = None
    job.error_details = None
    return job


def _make_campaign(client_id=None, generation_mode=None):
    campaign = MagicMock()
    campaign.id = uuid.uuid4()
    campaign.client_id = client_id or uuid.uuid4()
    campaign.brain_dump = "Raw brain dump text"
    campaign.blog_html = None
    campaign.voice_score = None
    campaign.x_post = None
    campaign.linkedin_post = None
    campaign.instagram_caption = None
    campaign.facebook_post = None
    campaign.threads_post = None
    campaign.target_keyword = None
    campaign.target_audience = None
    campaign.secondary_keywords = None
    campaign.target_word_count = None
    campaign.article_template = None
    campaign.generation_mode = generation_mode
    return campaign


def _make_client(user_id=None, bvp=None, voice_samples=None):
    client = MagicMock()
    client.id = uuid.uuid4()
    client.user_id = user_id or uuid.uuid4()
    client.brand_voice_profile = bvp
    client.voice_samples = voice_samples
    return client


def _make_db(job, campaign, client):
    db = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    async def mock_execute(stmt):
        result = MagicMock()
        stmt_str = str(stmt)
        if "jobs" in stmt_str:
            result.scalar_one_or_none = MagicMock(return_value=job)
        elif "campaigns" in stmt_str:
            result.scalar_one_or_none = MagicMock(return_value=campaign)
        elif "clients" in stmt_str:
            result.scalar_one_or_none = MagicMock(return_value=client)
        else:
            result.scalar_one_or_none = MagicMock(return_value=None)
        return result

    db.execute = AsyncMock(side_effect=mock_execute)
    return db


# ── Task 1 + 2: Repair pass orchestration ────────────────────────────────────


@pytest.mark.asyncio
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation._llm")
async def test_repair_fired_on_failing_tone(mock_llm, mock_logs):
    """repair_blog_voice is called when tone_score < 7."""
    from app.services.generation import run_generation_pipeline

    campaign = _make_campaign()
    client = _make_client(bvp=_BVP)
    job = _make_job(campaign_id=campaign.id)

    repaired_html = "<h1>Repaired</h1><p>Better body.</p>"

    mock_llm.generate_blog = AsyncMock(return_value=_BLOG_HTML)
    mock_llm.check_fidelity = AsyncMock(side_effect=[_FAILING_TONE_SCORE, _PASSING_SCORE])
    mock_llm.generate_social = AsyncMock(return_value=_SOCIAL)
    mock_llm.repair_blog_voice = AsyncMock(return_value=repaired_html)
    mock_logs.create_generation_log = AsyncMock()

    db = _make_db(job, campaign, client)
    await run_generation_pipeline(job.id, db)

    mock_llm.repair_blog_voice.assert_called_once()
    assert campaign.voice_score["repaired"] is True
    assert campaign.voice_score["initial"]["tone_score"] == 5
    assert campaign.voice_score["final"]["tone_score"] == _PASSING_SCORE["tone_score"]


@pytest.mark.asyncio
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation._llm")
async def test_repair_fired_on_failing_cadence(mock_llm, mock_logs):
    """repair_blog_voice is called when cadence_score < 6."""
    from app.services.generation import run_generation_pipeline

    campaign = _make_campaign()
    client = _make_client(bvp=_BVP)
    job = _make_job(campaign_id=campaign.id)

    mock_llm.generate_blog = AsyncMock(return_value=_BLOG_HTML)
    mock_llm.check_fidelity = AsyncMock(side_effect=[_FAILING_CADENCE_SCORE, _PASSING_SCORE])
    mock_llm.generate_social = AsyncMock(return_value=_SOCIAL)
    mock_llm.repair_blog_voice = AsyncMock(return_value="<h1>Repaired</h1><p>text</p>")
    mock_logs.create_generation_log = AsyncMock()

    db = _make_db(job, campaign, client)
    await run_generation_pipeline(job.id, db)

    mock_llm.repair_blog_voice.assert_called_once()
    assert campaign.voice_score["repaired"] is True


@pytest.mark.asyncio
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation._llm")
async def test_repair_fired_on_failing_jargon(mock_llm, mock_logs):
    """repair_blog_voice is called when jargon_violations > 0."""
    from app.services.generation import run_generation_pipeline

    campaign = _make_campaign()
    client = _make_client(bvp=_BVP)
    job = _make_job(campaign_id=campaign.id)

    mock_llm.generate_blog = AsyncMock(return_value=_BLOG_HTML)
    mock_llm.check_fidelity = AsyncMock(side_effect=[_FAILING_JARGON_SCORE, _PASSING_SCORE])
    mock_llm.generate_social = AsyncMock(return_value=_SOCIAL)
    mock_llm.repair_blog_voice = AsyncMock(return_value="<h1>Repaired</h1><p>text</p>")
    mock_logs.create_generation_log = AsyncMock()

    db = _make_db(job, campaign, client)
    await run_generation_pipeline(job.id, db)

    mock_llm.repair_blog_voice.assert_called_once()
    assert campaign.voice_score["repaired"] is True


@pytest.mark.asyncio
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation._llm")
async def test_repair_not_fired_on_passing_score(mock_llm, mock_logs):
    """repair_blog_voice is NOT called when all dimensions pass."""
    from app.services.generation import run_generation_pipeline

    campaign = _make_campaign()
    client = _make_client(bvp=_BVP)
    job = _make_job(campaign_id=campaign.id)

    mock_llm.generate_blog = AsyncMock(return_value=_BLOG_HTML)
    mock_llm.check_fidelity = AsyncMock(return_value=_PASSING_SCORE)
    mock_llm.generate_social = AsyncMock(return_value=_SOCIAL)
    mock_llm.repair_blog_voice = AsyncMock(return_value="<h1>Irrelevant</h1>")
    mock_logs.create_generation_log = AsyncMock()

    db = _make_db(job, campaign, client)
    await run_generation_pipeline(job.id, db)

    mock_llm.repair_blog_voice.assert_not_called()
    assert campaign.voice_score["repaired"] is False


@pytest.mark.asyncio
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation._llm")
async def test_repair_single_call_bound(mock_llm, mock_logs):
    """repair_blog_voice is called at most once per campaign regardless of re-score result."""
    from app.services.generation import run_generation_pipeline

    campaign = _make_campaign()
    client = _make_client(bvp=_BVP)
    job = _make_job(campaign_id=campaign.id)

    # Both initial and re-score fail -- but repair must not be called again
    still_failing = {**_FAILING_TONE_SCORE, "tone_score": 4}

    mock_llm.generate_blog = AsyncMock(return_value=_BLOG_HTML)
    mock_llm.check_fidelity = AsyncMock(side_effect=[_FAILING_TONE_SCORE, still_failing])
    mock_llm.generate_social = AsyncMock(return_value=_SOCIAL)
    mock_llm.repair_blog_voice = AsyncMock(return_value="<h1>Repaired</h1><p>text</p>")
    mock_logs.create_generation_log = AsyncMock()

    db = _make_db(job, campaign, client)
    await run_generation_pipeline(job.id, db)

    # Exactly one repair call -- no recursion
    assert mock_llm.repair_blog_voice.call_count == 1


@pytest.mark.asyncio
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation._llm")
async def test_better_score_wins_repaired_is_better(mock_llm, mock_logs):
    """When repaired score is higher, repaired HTML and score are used."""
    from app.services.generation import run_generation_pipeline

    campaign = _make_campaign()
    client = _make_client(bvp=_BVP)
    job = _make_job(campaign_id=campaign.id)

    repaired_html = "<h1>Repaired</h1><p>Better.</p>"
    repaired_score = {**_PASSING_SCORE, "tone_score": 9, "cadence_score": 9, "jargon_violations": 0}

    mock_llm.generate_blog = AsyncMock(return_value=_BLOG_HTML)
    mock_llm.check_fidelity = AsyncMock(side_effect=[_FAILING_TONE_SCORE, repaired_score])
    mock_llm.generate_social = AsyncMock(return_value=_SOCIAL)
    mock_llm.repair_blog_voice = AsyncMock(return_value=repaired_html)
    mock_logs.create_generation_log = AsyncMock()

    db = _make_db(job, campaign, client)
    await run_generation_pipeline(job.id, db)

    # Repaired HTML should be used
    assert campaign.blog_html == repaired_html
    # Flat keys hold final (repaired) values
    assert campaign.voice_score["tone_score"] == 9
    assert campaign.voice_score["repaired"] is True


@pytest.mark.asyncio
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation._llm")
async def test_better_score_wins_original_is_better(mock_llm, mock_logs):
    """When original score is higher than repaired, original HTML is kept."""
    from app.services.generation import run_generation_pipeline

    campaign = _make_campaign()
    client = _make_client(bvp=_BVP)
    job = _make_job(campaign_id=campaign.id)

    # Repaired is worse than initial (which itself was failing)
    worse_repaired = {**_FAILING_TONE_SCORE, "tone_score": 3, "cadence_score": 3}

    mock_llm.generate_blog = AsyncMock(return_value=_BLOG_HTML)
    mock_llm.check_fidelity = AsyncMock(side_effect=[_FAILING_TONE_SCORE, worse_repaired])
    mock_llm.generate_social = AsyncMock(return_value=_SOCIAL)
    mock_llm.repair_blog_voice = AsyncMock(return_value="<h1>Worse Repair</h1><p>text</p>")
    mock_logs.create_generation_log = AsyncMock()

    db = _make_db(job, campaign, client)
    await run_generation_pipeline(job.id, db)

    # Original HTML kept (campaign.blog_html was set to _BLOG_HTML by generate_blog path)
    assert campaign.blog_html == _BLOG_HTML
    # Flat keys hold final values (original initial score since it won)
    assert campaign.voice_score["tone_score"] == _FAILING_TONE_SCORE["tone_score"]
    assert campaign.voice_score["repaired"] is True


@pytest.mark.asyncio
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation._llm")
async def test_repair_exception_falls_back_cleanly(mock_llm, mock_logs):
    """If repair_blog_voice raises, the pipeline continues with original score."""
    from app.services.generation import run_generation_pipeline

    campaign = _make_campaign()
    client = _make_client(bvp=_BVP)
    job = _make_job(campaign_id=campaign.id)

    mock_llm.generate_blog = AsyncMock(return_value=_BLOG_HTML)
    mock_llm.check_fidelity = AsyncMock(return_value=_FAILING_TONE_SCORE)
    mock_llm.generate_social = AsyncMock(return_value=_SOCIAL)
    mock_llm.repair_blog_voice = AsyncMock(side_effect=RuntimeError("LLM failure"))
    mock_logs.create_generation_log = AsyncMock()

    db = _make_db(job, campaign, client)
    await run_generation_pipeline(job.id, db)

    # Pipeline should not fail -- job still in_progress
    assert job.status == "in_progress"
    # Voice score preserved with repaired=False
    assert campaign.voice_score["repaired"] is False
    assert campaign.voice_score["tone_score"] == _FAILING_TONE_SCORE["tone_score"]


@pytest.mark.asyncio
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation._llm")
async def test_flat_keys_hold_final_values(mock_llm, mock_logs):
    """Top-level flat keys (tone_score etc.) always reflect the FINAL chosen score."""
    from app.services.generation import run_generation_pipeline

    campaign = _make_campaign()
    client = _make_client(bvp=_BVP)
    job = _make_job(campaign_id=campaign.id)

    final_score = {**_PASSING_SCORE, "tone_score": 9, "cadence_score": 9, "jargon_violations": 0}

    mock_llm.generate_blog = AsyncMock(return_value=_BLOG_HTML)
    mock_llm.check_fidelity = AsyncMock(side_effect=[_FAILING_TONE_SCORE, final_score])
    mock_llm.generate_social = AsyncMock(return_value=_SOCIAL)
    mock_llm.repair_blog_voice = AsyncMock(return_value="<h1>Repaired</h1><p>text</p>")
    mock_logs.create_generation_log = AsyncMock()

    db = _make_db(job, campaign, client)
    await run_generation_pipeline(job.id, db)

    vs = campaign.voice_score
    # Flat keys hold final values
    assert vs["tone_score"] == 9
    assert vs["cadence_score"] == 9
    assert vs["jargon_violations"] == 0
    # Additive keys present
    assert "initial" in vs
    assert "final" in vs
    assert vs["initial"]["tone_score"] == 5  # original failing score
    assert vs["final"]["tone_score"] == 9


@pytest.mark.asyncio
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation._llm")
async def test_assist_mode_no_repair_voice_score_null(mock_llm, mock_logs):
    """Assist mode: repair is not called, voice_score stays None."""
    from app.services.generation import run_generation_pipeline

    campaign = _make_campaign(generation_mode="assist")
    client = _make_client(bvp=_BVP)
    job = _make_job(campaign_id=campaign.id)

    mock_llm.generate_blog = AsyncMock(return_value=_BLOG_HTML)
    mock_llm.check_fidelity = AsyncMock(return_value=_FAILING_TONE_SCORE)
    mock_llm.generate_social = AsyncMock(return_value=_SOCIAL)
    mock_llm.repair_blog_voice = AsyncMock(return_value="<h1>Repair</h1>")
    mock_logs.create_generation_log = AsyncMock()

    db = _make_db(job, campaign, client)
    await run_generation_pipeline(job.id, db)

    mock_llm.repair_blog_voice.assert_not_called()
    mock_llm.check_fidelity.assert_not_called()
    assert campaign.voice_score is None


# ── Task 3: Per-surface voice application ────────────────────────────────────


class TestBuildVoiceForSurface:
    """Verify that each surface produces a verifiably different voice section."""

    def test_all_surfaces_differ_from_each_other(self):
        """Each surface's voice section must be pairwise distinct."""
        surfaces = ["blog", "linkedin", "x", "instagram", "facebook", "threads"]
        results = {s: build_voice_for_surface(_BVP, s) for s in surfaces}

        # Pairwise inequality
        surface_list = list(surfaces)
        for i in range(len(surface_list)):
            for j in range(i + 1, len(surface_list)):
                s1, s2 = surface_list[i], surface_list[j]
                assert results[s1] != results[s2], (
                    f"Surfaces '{s1}' and '{s2}' produced identical voice sections"
                )

    def test_blog_returns_full_voice_injection(self):
        result = build_voice_for_surface(_BVP, "blog")
        full = _build_voice_injection(_BVP)
        assert result == full

    def test_x_contains_punchier_line(self):
        result = build_voice_for_surface(_BVP, "x")
        assert "Punchier and more compressed than the blog voice" in result

    def test_x_does_not_contain_full_voice_brief(self):
        result = build_voice_for_surface(_BVP, "x")
        # X must not receive the full voice brief prose
        assert _BVP["voice_brief"] not in result

    def test_linkedin_contains_exactly_two_sentence_brief(self):
        """LinkedIn brief is exactly the first 2 sentences of voice_brief."""
        result = build_voice_for_surface(_BVP, "linkedin")
        # voice_brief has 2 sentences separated by ". "
        sentences = [s.strip() for s in _BVP["voice_brief"].split(". ") if s.strip()]
        two_sentence_brief = ". ".join(sentences[:2])
        if not two_sentence_brief.endswith("."):
            two_sentence_brief += "."
        assert two_sentence_brief in result

    def test_linkedin_does_not_contain_full_brief(self):
        """LinkedIn must not receive all sentences if voice_brief has more than 2."""
        long_bvp = {
            **_BVP,
            "voice_brief": "Sentence one. Sentence two. Sentence three. Sentence four.",
        }
        result = build_voice_for_surface(long_bvp, "linkedin")
        assert "Sentence three" not in result
        assert "Sentence four" not in result

    def test_instagram_facebook_contain_warm_brief(self):
        for surface in ("instagram", "facebook"):
            result = build_voice_for_surface(_BVP, surface)
            # Should contain compressed brief (first 2 sentences)
            sentences = [s.strip() for s in _BVP["voice_brief"].split(". ") if s.strip()]
            assert sentences[0] in result, f"{surface} should contain voice brief excerpt"
            # Should contain contraction encouragement
            assert "contractions" in result.lower()

    def test_threads_no_full_brief_but_has_register_rule(self):
        result = build_voice_for_surface(_BVP, "threads")
        assert "THREADS VOICE" in result
        # Should not inject the full voice brief (only 2 sentences max)
        sentences = _BVP["voice_brief"].split(". ")
        if len(sentences) > 2:
            assert sentences[2] not in result

    def test_x_surface_empty_when_no_voice_brief(self):
        bvp_no_brief = {k: v for k, v in _BVP.items() if k != "voice_brief"}
        # X surface should still return something (cadence + banned words + punchier line)
        result = build_voice_for_surface(bvp_no_brief, "x")
        assert "Punchier" in result

    def test_linkedin_empty_when_no_voice_brief(self):
        bvp_no_brief = {k: v for k, v in _BVP.items() if k != "voice_brief"}
        result = build_voice_for_surface(bvp_no_brief, "linkedin")
        assert result == ""

    def test_instagram_empty_when_no_voice_brief(self):
        bvp_no_brief = {k: v for k, v in _BVP.items() if k != "voice_brief"}
        result = build_voice_for_surface(bvp_no_brief, "instagram")
        assert result == ""

    def test_empty_bvp_returns_empty(self):
        for surface in ("blog", "linkedin", "x", "instagram", "facebook", "threads"):
            result = build_voice_for_surface({}, surface)
            assert result == "", f"Expected empty for surface '{surface}' with empty BVP"


# ── Task 4: Template voice lines ──────────────────────────────────────────────

class TestBuildTemplateVoiceLine:
    def test_thought_leadership_contains_opinion_line(self):
        result = _build_template_voice_line("thought-leadership")
        assert "opinion" in result.lower() or "stance" in result.lower()
        assert "TEMPLATE VOICE" in result

    def test_how_to_contains_imperative_line(self):
        result = _build_template_voice_line("how-to")
        assert "imperative" in result.lower() or "steps" in result.lower()
        assert "TEMPLATE VOICE" in result

    def test_standard_returns_empty(self):
        assert _build_template_voice_line("standard") == ""

    def test_listicle_returns_empty(self):
        assert _build_template_voice_line("listicle") == ""

    def test_none_returns_empty(self):
        assert _build_template_voice_line(None) == ""

    def test_thought_leadership_no_em_dash(self):
        result = _build_template_voice_line("thought-leadership")
        assert "—" not in result
        assert "--" not in result

    def test_how_to_no_em_dash(self):
        result = _build_template_voice_line("how-to")
        assert "—" not in result
        assert "--" not in result

    def test_template_lines_differ(self):
        tl = _build_template_voice_line("thought-leadership")
        ht = _build_template_voice_line("how-to")
        assert tl != ht


# ── Task 5: Assist invariance ─────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.services.generation.generation_logs_repo")
@patch("app.services.generation._llm")
async def test_social_only_pipeline_unaffected_by_repair(mock_llm, mock_logs):
    """run_social_only_pipeline has no fidelity check or repair (social-only campaigns)."""
    from app.services.generation import run_social_only_pipeline

    job = _make_job()
    campaign = _make_campaign()
    client = _make_client(bvp=_BVP)

    db = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    call_count = {"n": 0}

    async def mock_execute(stmt):
        result = MagicMock()
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            result.scalar_one_or_none = MagicMock(return_value=job)
        elif n == 1:
            result.scalar_one_or_none = MagicMock(return_value=campaign)
        else:
            result.scalar_one_or_none = MagicMock(return_value=client)
        return result

    db.execute = AsyncMock(side_effect=mock_execute)

    mock_llm.generate_social_standalone = AsyncMock(return_value={
        "x_post": "Tweet!",
        "linkedin_post": "LinkedIn post " * 40,
        "instagram_caption": "IG caption #test",
        "facebook_post": "Facebook post content",
        "threads_post": "Threads take.",
    })
    mock_llm.repair_blog_voice = AsyncMock()
    mock_llm.check_fidelity = AsyncMock()

    await run_social_only_pipeline(job.id, db)

    mock_llm.repair_blog_voice.assert_not_called()
    mock_llm.check_fidelity.assert_not_called()


# ── Repair prompt integrity: no em-dashes ─────────────────────────────────────

def test_repair_prompt_no_em_dash_in_instructions():
    """The repair prompt may reference em-dash by name but must not use it in instructional copy.

    The line 'Never use an em-dash (—)' is a legitimate reference; em-dashes must not
    appear as punctuation in the prose instructions themselves.
    """
    from app.integrations.generation_prompts import _REPAIR_BLOG_VOICE_PROMPT
    # Strip the reference line that names the character, then verify no remaining em-dashes
    lines = _REPAIR_BLOG_VOICE_PROMPT.split("\n")
    non_reference_lines = [
        line for line in lines
        if "em-dash" not in line.lower()
    ]
    cleaned = "\n".join(non_reference_lines)
    assert "—" not in cleaned, "Em-dash used as punctuation in repair prompt instructions"


def test_template_voice_line_no_em_dash():
    for template in ("thought-leadership", "how-to", "standard", "listicle"):
        result = _build_template_voice_line(template)
        assert "—" not in result
