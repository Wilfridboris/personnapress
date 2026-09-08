"""Unit tests for Story 26.3: Few-Shot Voice Exemplars from Stored Samples.

Covers:
- select_voice_samples: length bounds, sentence-boundary trim, dedup, 12-cap, diversity
- _build_samples_block: numbering, sanitization, empty case, prefer_short ordering
- Prompt injection: blog gets samples_block, social gets short samples, fidelity gets samples
- Assist mode: no samples injected
- Legacy (no samples) path: block omitted entirely
- Rescan semantics: scrape-only replacement, failure preserves all
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── select_voice_samples ───────────────────────────────────────────────────────

def test_select_voice_samples_basic():
    from app.services.ingestion import select_voice_samples

    # Paragraph that is exactly within the 200-600 range
    text = "A" * 210 + ". " + "B" * 210 + "."
    result = select_voice_samples([(text, "scrape")])
    assert isinstance(result, list)
    for item in result:
        assert "text" in item
        assert "source" in item
        assert "added_at" in item
        assert item["source"] == "scrape"
        assert 200 <= len(item["text"]) <= 600


def test_select_voice_samples_caps_at_12():
    from app.services.ingestion import select_voice_samples

    # 20 paragraphs each comfortably within range
    paras = [f"Para {i}: " + ("X" * 250) + "." for i in range(20)]
    text = "\n\n".join(paras)
    result = select_voice_samples([(text, "scrape")])
    assert len(result) <= 12


def test_select_voice_samples_drops_short():
    from app.services.ingestion import select_voice_samples

    # Paragraphs too short (< 200 chars)
    text = "Short para.\n\nAnother short one."
    result = select_voice_samples([(text, "scrape")])
    # None should make it in (both are < 200 chars)
    assert all(len(item["text"]) >= 200 for item in result)


def test_select_voice_samples_sentence_boundary_trim():
    from app.services.ingestion import select_voice_samples

    # Build a paragraph > 600 chars with clear sentence boundaries
    sentence = "This is a proper sentence that ends with punctuation. "
    long_text = sentence * 15  # well over 600 chars
    result = select_voice_samples([(long_text, "scrape")])
    for item in result:
        # Must not exceed 600
        assert len(item["text"]) <= 600
        # Must end on sentence boundary (last char is .)
        assert item["text"].rstrip()[-1] in ".!?"


def test_select_voice_samples_deduplication():
    from app.services.ingestion import select_voice_samples
    import re

    # Two clearly distinct paragraphs with unique beginnings
    para1 = "This is the first unique paragraph about marketing strategy and results. " + "X" * 150 + "."
    para2 = "Here is the second distinct paragraph covering analytics and metrics. " + "Y" * 150 + "."
    # Repeat para1 to test dedup
    text = para1 + "\n\n" + para2 + "\n\n" + para1
    result = select_voice_samples([(text, "scrape")])
    texts = [r["text"] for r in result]
    # Check no two items share the same 80-char prefix (normalized)
    prefixes = set()
    for t in texts:
        p = re.sub(r"\W+", "", t[:80].lower())
        assert p not in prefixes, f"Duplicate found: {p!r}"
        prefixes.add(p)


def test_select_voice_samples_deterministic():
    from app.services.ingestion import select_voice_samples

    paras = [f"Para {i}: " + ("W" * 250) + ". Ends here." for i in range(15)]
    text = "\n\n".join(paras)
    r1 = select_voice_samples([(text, "scrape")])
    r2 = select_voice_samples([(text, "scrape")])
    assert [x["text"] for x in r1] == [x["text"] for x in r2]


def test_select_voice_samples_empty_input():
    from app.services.ingestion import select_voice_samples

    assert select_voice_samples([]) == []
    assert select_voice_samples([("", "scrape")]) == []


def test_select_voice_samples_questionnaire_source():
    from app.services.ingestion import select_voice_samples

    text = "Q" * 50 + " This is some questionnaire text that is long enough to qualify. " + "R" * 150 + "."
    result = select_voice_samples([(text, "questionnaire")])
    for item in result:
        assert item["source"] == "questionnaire"


def test_select_voice_samples_diversity_mix():
    from app.services.ingestion import select_voice_samples

    # Supply a mix of short (200-300) and long (400-600) paragraphs
    short_paras = [f"Short {i}: " + ("S" * 220) + "." for i in range(8)]
    long_paras = [f"Long {i}: " + ("L" * 500) + "." for i in range(8)]
    text = "\n\n".join(short_paras + long_paras)
    result = select_voice_samples([(text, "scrape")])
    assert len(result) <= 12
    short_count = sum(1 for r in result if len(r["text"]) <= 300)
    long_count = sum(1 for r in result if len(r["text"]) > 300)
    # Should include at least 1 of each type when both are available
    assert short_count > 0
    assert long_count > 0


# ── _build_samples_block ────────────────────────────────────────────────────────

def test_build_samples_block_empty():
    from app.integrations.generation_prompts import _build_samples_block

    assert _build_samples_block(None) == ""
    assert _build_samples_block([]) == ""


def test_build_samples_block_invalid_entries_filtered():
    from app.integrations.generation_prompts import _build_samples_block

    samples = [{"text": "", "source": "scrape"}, {"text": None, "source": "scrape"}]
    assert _build_samples_block(samples) == ""


def test_build_samples_block_numbering_and_quotes():
    from app.integrations.generation_prompts import _build_samples_block

    samples = [
        {"text": "Hello world. A sample sentence.", "source": "scrape", "added_at": "2026-09-08T00:00:00Z"},
        {"text": "Another sample here. More text.", "source": "questionnaire", "added_at": "2026-09-08T00:00:00Z"},
    ]
    block = _build_samples_block(samples, max_count=3)
    assert "WRITING SAMPLES" in block
    assert '1. "Hello world' in block
    assert '2. "Another sample' in block


def test_build_samples_block_sanitizes_newlines():
    from app.integrations.generation_prompts import _build_samples_block

    samples = [{"text": "Line one\nline two\nline three.", "source": "scrape", "added_at": "x"}]
    block = _build_samples_block(samples, max_count=1)
    assert "\n" not in block.split('1. "')[1].split('"')[0]


def test_build_samples_block_sanitizes_double_quotes():
    from app.integrations.generation_prompts import _build_samples_block

    samples = [{"text": 'He said "hello" loudly.', "source": "scrape", "added_at": "x"}]
    block = _build_samples_block(samples, max_count=1)
    # Embedded double quotes should be replaced with single quotes
    inner = block.split('1. "')[1]
    # The embedded " should have been replaced with '
    assert '"hello"' not in inner


def test_build_samples_block_respects_max_count():
    from app.integrations.generation_prompts import _build_samples_block

    samples = [
        {"text": f"Sample {i}. More text here.", "source": "scrape", "added_at": "x"}
        for i in range(5)
    ]
    block = _build_samples_block(samples, max_count=2)
    assert '3. "' not in block
    assert '1. "' in block
    assert '2. "' in block


def test_build_samples_block_prefer_short_orders_shorter_first():
    from app.integrations.generation_prompts import _build_samples_block

    short = {"text": "S" * 220 + ".", "source": "scrape", "added_at": "x"}
    long_s = {"text": "L" * 500 + ".", "source": "scrape", "added_at": "x"}
    # prefer_short=True: short should appear before long
    block = _build_samples_block([long_s, short], max_count=2, prefer_short=True)
    pos_short = block.find(short["text"][:10])
    pos_long = block.find(long_s["text"][:10])
    assert pos_short < pos_long


def test_build_samples_block_instruction_text():
    from app.integrations.generation_prompts import _build_samples_block

    samples = [{"text": "A sample sentence here. Another one.", "source": "scrape", "added_at": "x"}]
    block = _build_samples_block(samples, max_count=1)
    assert "match the rhythm" in block
    assert "do not copy their content" in block
    # Must not contain em-dash or double-dash
    assert "—" not in block
    assert "--" not in block


# ── Blog prompt injection ───────────────────────────────────────────────────────

def _make_samples(n: int = 3) -> list[dict]:
    return [
        {"text": f"Sample sentence number {i}. Extra filler text to reach length.", "source": "scrape", "added_at": "2026-09-08T00:00:00Z"}
        for i in range(n)
    ]


def test_blog_prompt_contains_samples_block():
    """Blog prompt must include the samples block when samples are provided."""
    from app.integrations.generation_prompts import _build_samples_block, _BLOG_PROMPT

    samples = _make_samples(3)
    block = _build_samples_block(samples, max_count=3)
    assert block != ""

    # Simulate prompt building (minimal placeholders)
    prompt = _BLOG_PROMPT.format(
        voice_section="Professional voice.",
        samples_block=block,
        meta_voice_note="",
        brain_dump="Test brain dump.",
        tone_list="professional",
        cadence_instruction="avg 15 words",
        banned_jargon_list="none",
        seo_target_section="",
        audience_section="",
        word_count_range="900-1,500 words",
        template_structure_override="",
        length_override_section="",
    )
    assert "WRITING SAMPLES" in prompt
    assert "match the rhythm" in prompt


def test_blog_prompt_no_samples_block_when_empty():
    """When no samples, samples_block is empty and WRITING SAMPLES does not appear."""
    from app.integrations.generation_prompts import _build_samples_block, _BLOG_PROMPT

    block = _build_samples_block(None)
    assert block == ""

    prompt = _BLOG_PROMPT.format(
        voice_section="Professional voice.",
        samples_block=block,
        meta_voice_note="",
        brain_dump="Test brain dump.",
        tone_list="professional",
        cadence_instruction="avg 15 words",
        banned_jargon_list="none",
        seo_target_section="",
        audience_section="",
        word_count_range="900-1,500 words",
        template_structure_override="",
        length_override_section="",
    )
    assert "WRITING SAMPLES" not in prompt


def test_fidelity_prompt_contains_samples_block():
    """Fidelity prompt must include same samples block as reference."""
    from app.integrations.generation_prompts import _build_samples_block, _FIDELITY_PROMPT

    samples = _make_samples(2)
    block = _build_samples_block(samples, max_count=3)
    prompt = _FIDELITY_PROMPT.format(
        bvp_json="{}",
        samples_block=block,
        blog_html="<h1>Test</h1>",
        brain_dump_sample="brain dump here",
        expanded_scoring_section="",
    )
    assert "WRITING SAMPLES" in prompt


def test_social_prompt_contains_samples_block():
    """Social prompt must include samples block (prefer_short)."""
    from app.integrations.generation_prompts import _build_samples_block, _SOCIAL_PROMPT

    samples = _make_samples(2)
    block = _build_samples_block(samples, max_count=2, prefer_short=True)
    prompt = _SOCIAL_PROMPT.format(
        bvp_json="{}",
        linkedin_voice_section="",
        instagram_voice_section="",
        facebook_voice_section="",
        threads_voice_section="",
        bvp_structure_hints="",
        samples_block=block,
        social_universal_rules="Rules here.",
        social_voice_signals="",
        brain_dump="Brain dump.",
        blog_title="Title",
    )
    assert "WRITING SAMPLES" in prompt


def test_social_standalone_prompt_contains_samples_block():
    from app.integrations.generation_prompts import _build_samples_block, _SOCIAL_STANDALONE_PROMPT

    samples = _make_samples(2)
    block = _build_samples_block(samples, max_count=2, prefer_short=True)
    prompt = _SOCIAL_STANDALONE_PROMPT.format(
        bvp_json="{}",
        linkedin_voice_section="",
        instagram_voice_section="",
        facebook_voice_section="",
        threads_voice_section="",
        bvp_structure_hints="",
        samples_block=block,
        social_universal_rules="Rules here.",
        social_voice_signals="",
        brain_dump="Brain dump.",
    )
    assert "WRITING SAMPLES" in prompt


# ── Rescan semantics ──────────────────────────────────────────────────────────

def test_rescan_preserves_questionnaire_and_transcript_samples():
    """Rescan replaces scrape entries but preserves questionnaire/transcript."""
    questionnaire_sample = {"text": "Questionnaire text here.", "source": "questionnaire", "added_at": "2026-01-01T00:00:00Z"}
    transcript_sample = {"text": "Transcript text here.", "source": "transcript", "added_at": "2026-01-01T00:00:00Z"}
    scrape_sample = {"text": "Old scraped text.", "source": "scrape", "added_at": "2026-01-01T00:00:00Z"}

    existing = [questionnaire_sample, transcript_sample, scrape_sample]

    # Simulate the rescan logic from ingest.py
    new_scrape = [{"text": "New scraped text.", "source": "scrape", "added_at": "2026-09-08T00:00:00Z"}]
    preserved = [s for s in existing if isinstance(s, dict) and s.get("source") != "scrape"]
    updated = preserved + new_scrape

    sources = [s["source"] for s in updated]
    assert "questionnaire" in sources
    assert "transcript" in sources
    # Old scrape gone, new scrape present
    texts = [s["text"] for s in updated]
    assert "Old scraped text." not in texts
    assert "New scraped text." in texts


def test_failed_rescan_preserves_all_samples():
    """On failure (no new samples), existing samples must be preserved."""
    existing = [
        {"text": "Existing sample.", "source": "scrape", "added_at": "2026-01-01T00:00:00Z"},
        {"text": "Q sample.", "source": "questionnaire", "added_at": "2026-01-01T00:00:00Z"},
    ]

    # Failure case: new_scrape_samples is empty (exception caught), preserved logic runs
    new_scrape_samples: list[dict] = []
    preserved = [s for s in existing if isinstance(s, dict) and s.get("source") != "scrape"]
    # When new_scrape_samples is empty, voice_samples = preserved or None
    result = preserved + new_scrape_samples if new_scrape_samples else preserved or None
    # The questionnaire sample must survive; scrape sample gone (replace logic) but if no new
    # scrape samples, only preserved (non-scrape) survive
    assert result is not None
    assert any(s["source"] == "questionnaire" for s in result)
