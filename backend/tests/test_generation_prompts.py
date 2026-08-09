"""Unit tests for generation_prompts.py -- Story 16.6: Voice signal injection."""
import pytest

from app.integrations.generation_prompts import (
    _BLOG_PROMPT,
    _FIDELITY_PROMPT,
    _SOCIAL_PROMPT,
    _SOCIAL_STANDALONE_PROMPT,
    _build_standalone_voice_injection,
    _build_voice_injection,
    _strip_blog_trailer,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

_VOICE_BRIEF = "Direct, data-driven voice with short declarative sentences."

_BASE_BVP = {
    "voice_brief": _VOICE_BRIEF,
    "tone": ["authoritative", "direct"],
    "cadence": {"avg_sentence_length": 14},
    "banned_jargon": ["leverage"],
}

_FULL_BVP = {
    **_BASE_BVP,
    "signature_phrases": ["Let me be blunt", "the data says otherwise", "here is what I know"],
    "voice_anchor_sentences": [
        "Here is what the numbers actually show.",
        "Most advice ignores the base rate.",
    ],
    "anti_pattern_example": "In today's rapidly evolving landscape, it is important to note...",
}


# ── _build_voice_injection tests ──────────────────────────────────────────────

class TestBuildVoiceInjection:
    def test_all_three_new_fields_appear(self):
        result = _build_voice_injection(_FULL_BVP)
        assert "SIGNATURE PHRASES" in result
        assert "VOICE ANCHORS" in result
        assert "ANTI-PATTERN" in result
        assert "Let me be blunt" in result
        assert "Here is what the numbers actually show." in result
        assert "In today's rapidly evolving landscape" in result

    def test_only_voice_brief_no_new_blocks(self):
        bvp = {**_BASE_BVP}
        result = _build_voice_injection(bvp)
        assert "SIGNATURE PHRASES" not in result
        assert "VOICE ANCHORS" not in result
        assert "ANTI-PATTERN" not in result
        assert _VOICE_BRIEF in result

    def test_empty_lists_no_new_blocks(self):
        bvp = {**_BASE_BVP, "signature_phrases": [], "voice_anchor_sentences": [], "anti_pattern_example": ""}
        result = _build_voice_injection(bvp)
        assert "SIGNATURE PHRASES" not in result
        assert "VOICE ANCHORS" not in result
        assert "ANTI-PATTERN" not in result

    def test_no_voice_brief_returns_empty(self):
        bvp = {
            "tone": ["formal"],
            "signature_phrases": ["Let me be blunt"],
            "voice_anchor_sentences": ["Here is what I found."],
            "anti_pattern_example": "As we all know...",
        }
        assert _build_voice_injection(bvp) == ""

    def test_em_dash_in_signature_phrase_replaced(self):
        bvp = {**_BASE_BVP, "signature_phrases": ["test—phrase"]}
        result = _build_voice_injection(bvp)
        assert "test--phrase" in result
        assert "test—phrase" not in result

    def test_em_dash_in_voice_anchor_replaced(self):
        bvp = {**_BASE_BVP, "voice_anchor_sentences": ["sentence—with dash"]}
        result = _build_voice_injection(bvp)
        assert "sentence--with dash" in result
        assert "sentence—with dash" not in result

    def test_em_dash_in_anti_pattern_replaced(self):
        bvp = {**_BASE_BVP, "anti_pattern_example": "example—bad sentence"}
        result = _build_voice_injection(bvp)
        assert "example--bad sentence" in result
        assert "example—bad sentence" not in result

    def test_signature_phrases_capped_at_10(self):
        phrases = [f"phrase {i}" for i in range(15)]
        bvp = {**_BASE_BVP, "signature_phrases": phrases}
        result = _build_voice_injection(bvp)
        for i in range(10):
            assert f"phrase {i}" in result
        for i in range(10, 15):
            assert f"phrase {i}" not in result

    def test_voice_anchors_capped_at_5(self):
        sentences = [f"Sentence {i}." for i in range(8)]
        bvp = {**_BASE_BVP, "voice_anchor_sentences": sentences}
        result = _build_voice_injection(bvp)
        for i in range(5):
            assert f"Sentence {i}." in result
        for i in range(5, 8):
            assert f"Sentence {i}." not in result

    def test_existing_voice_application_rules_preserved(self):
        result = _build_voice_injection(_FULL_BVP)
        assert "VOICE APPLICATION RULES" in result
        assert _VOICE_BRIEF in result

    def test_block_order_sig_then_anchors_then_anti(self):
        result = _build_voice_injection(_FULL_BVP)
        sig_pos = result.index("SIGNATURE PHRASES")
        anchor_pos = result.index("VOICE ANCHORS")
        anti_pos = result.index("ANTI-PATTERN")
        assert sig_pos < anchor_pos < anti_pos

    def test_whitespace_only_phrases_excluded(self):
        bvp = {**_BASE_BVP, "signature_phrases": ["   ", "", "real phrase"]}
        result = _build_voice_injection(bvp)
        assert "real phrase" in result
        # Only one bullet should appear
        assert result.count("- real phrase") == 1

    def test_none_values_in_lists_excluded(self):
        bvp = {**_BASE_BVP, "signature_phrases": [None, "valid phrase"]}  # type: ignore[list-item]
        result = _build_voice_injection(bvp)
        assert "valid phrase" in result

    def test_signature_phrases_non_list_does_not_iterate_chars(self):
        bvp = {**_BASE_BVP, "signature_phrases": "not a list"}  # type: ignore[arg-type]
        result = _build_voice_injection(bvp)
        assert "SIGNATURE PHRASES" not in result

    def test_voice_anchors_non_list_does_not_iterate_chars(self):
        bvp = {**_BASE_BVP, "voice_anchor_sentences": "not a list"}  # type: ignore[arg-type]
        result = _build_voice_injection(bvp)
        assert "VOICE ANCHORS" not in result

    def test_anti_pattern_non_string_does_not_crash(self):
        bvp = {**_BASE_BVP, "anti_pattern_example": 42}  # type: ignore[arg-type]
        result = _build_voice_injection(bvp)
        assert "ANTI-PATTERN" not in result

    def test_embedded_newline_in_phrase_flattened(self):
        bvp = {**_BASE_BVP, "signature_phrases": ["line one\nline two"]}
        result = _build_voice_injection(bvp)
        assert "line one line two" in result
        assert "line one\nline two" not in result

    def test_double_quote_in_anti_pattern_replaced_with_single(self):
        bvp = {**_BASE_BVP, "anti_pattern_example": 'she said "hello" like that'}
        result = _build_voice_injection(bvp)
        assert "she said 'hello' like that" in result


# ── _build_standalone_voice_injection tests ────────────────────────────────────

class TestBuildStandaloneVoiceInjection:
    def test_signature_phrases_and_anti_pattern_appear(self):
        bvp = {
            "signature_phrases": ["Let me be blunt", "the data says otherwise"],
            "anti_pattern_example": "As we all know, the landscape is evolving...",
        }
        result = _build_standalone_voice_injection(bvp)
        assert "BRAND STRUCTURE HINTS" in result
        assert "Let me be blunt" in result
        assert "the data says otherwise" in result
        assert "ANTI-PATTERN" in result
        assert "As we all know" in result

    def test_opening_pattern_preserved_alongside_new_hints(self):
        bvp = {
            "opening_pattern": "bold_claim",
            "signature_phrases": ["Let me be blunt"],
        }
        result = _build_standalone_voice_injection(bvp)
        assert "bold claim" in result
        assert "Let me be blunt" in result

    def test_no_signature_phrases_no_phrase_hint(self):
        bvp = {"opening_pattern": "bold_claim"}
        result = _build_standalone_voice_injection(bvp)
        assert "Writer's signature phrases" not in result
        assert "ANTI-PATTERN" not in result
        assert "bold claim" in result

    def test_empty_signature_phrases_no_phrase_hint(self):
        bvp = {"opening_pattern": "question", "signature_phrases": []}
        result = _build_standalone_voice_injection(bvp)
        assert "Writer's signature phrases" not in result

    def test_no_relevant_fields_returns_empty(self):
        bvp = {"tone": ["formal"], "banned_jargon": ["leverage"]}
        assert _build_standalone_voice_injection(bvp) == ""

    def test_empty_bvp_returns_empty(self):
        assert _build_standalone_voice_injection({}) == ""

    def test_signature_phrases_capped_at_5(self):
        phrases = [f"phrase {i}" for i in range(8)]
        bvp = {"signature_phrases": phrases}
        result = _build_standalone_voice_injection(bvp)
        for i in range(5):
            assert f"phrase {i}" in result
        for i in range(5, 8):
            assert f"phrase {i}" not in result

    def test_em_dash_in_signature_phrase_replaced(self):
        bvp = {"signature_phrases": ["test—phrase"]}
        result = _build_standalone_voice_injection(bvp)
        assert "test--phrase" in result
        assert "test—phrase" not in result

    def test_em_dash_in_anti_pattern_replaced(self):
        bvp = {"anti_pattern_example": "bad—example"}
        result = _build_standalone_voice_injection(bvp)
        assert "bad--example" in result
        assert "bad—example" not in result

    def test_anti_pattern_without_signature_phrases(self):
        bvp = {"anti_pattern_example": "Bland sentence like this."}
        result = _build_standalone_voice_injection(bvp)
        assert "ANTI-PATTERN" in result
        assert "Bland sentence like this." in result

    def test_signature_phrases_non_list_does_not_iterate_chars(self):
        bvp = {"signature_phrases": "not a list"}  # type: ignore[arg-type]
        result = _build_standalone_voice_injection(bvp)
        assert "Writer's signature phrases" not in result

    def test_anti_pattern_non_string_does_not_crash(self):
        bvp = {"anti_pattern_example": 99}  # type: ignore[arg-type]
        result = _build_standalone_voice_injection(bvp)
        assert "ANTI-PATTERN" not in result

    def test_embedded_newline_in_phrase_flattened(self):
        bvp = {"signature_phrases": ["first\nsecond"]}
        result = _build_standalone_voice_injection(bvp)
        assert "first second" in result
        assert "first\nsecond" not in result

    def test_double_quote_in_anti_pattern_replaced_with_single(self):
        bvp = {"anti_pattern_example": 'he said "yes"'}
        result = _build_standalone_voice_injection(bvp)
        assert "he said 'yes'" in result


# ── TestPromptStructure -- Story 3.19: Personal voice preservation ─────────────

class TestPromptStructure:
    def test_blog_prompt_contains_authored_passage_classification(self):
        assert "AUTHORED PASSAGE" in _BLOG_PROMPT
        assert "FRAGMENT/NOTE" in _BLOG_PROMPT
        assert "DIRECTIVE" in _BLOG_PROMPT

    def test_blog_prompt_directive_markers_listed(self):
        assert "Note:" in _BLOG_PROMPT
        assert "Final note:" in _BLOG_PROMPT
        assert "PS:" in _BLOG_PROMPT

    def test_blog_prompt_passive_voice_rule_present(self):
        assert "passive voice" in _BLOG_PROMPT.lower()

    def test_fidelity_prompt_contains_authored_passages_preserved_field(self):
        assert "authored_passages_preserved" in _FIDELITY_PROMPT
        assert "brain_dump_sample" in _FIDELITY_PROMPT

    def test_social_prompts_contain_authored_passage_instruction(self):
        assert "AUTHORED PASSAGE" in _SOCIAL_PROMPT or "authored passage" in _SOCIAL_PROMPT.lower()
        assert "AUTHORED PASSAGE" in _SOCIAL_STANDALONE_PROMPT or "authored passage" in _SOCIAL_STANDALONE_PROMPT.lower()


# ── _strip_blog_trailer tests ─────────────────────────────────────────────────

class TestStripBlogTrailer:
    def test_strips_compliance_report_after_last_tag(self):
        html = "<h2>Conclusion</h2>\n<p>Final paragraph.</p>\n\n--- Word count: 1,147 words Primary keyword placement: H1 ✓"
        assert _strip_blog_trailer(html) == "<h2>Conclusion</h2>\n<p>Final paragraph.</p>"

    def test_no_trailer_unchanged(self):
        html = "<h1>Title</h1><p>Body.</p>"
        assert _strip_blog_trailer(html) == html

    def test_empty_string_unchanged(self):
        assert _strip_blog_trailer("") == ""

    def test_no_html_tags_unchanged(self):
        assert _strip_blog_trailer("plain text") == "plain text"

    def test_strips_whitespace_after_last_tag(self):
        html = "<p>Done.</p>   \n"
        assert _strip_blog_trailer(html) == "<p>Done.</p>"
