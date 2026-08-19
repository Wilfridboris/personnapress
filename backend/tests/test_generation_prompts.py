"""Unit tests for generation_prompts.py -- Story 16.6: Voice signal injection."""
import pytest

from app.integrations.generation_prompts import (
    _BLOG_ASSIST_PROMPT,
    _BLOG_PROMPT,
    _FIDELITY_PROMPT,
    _SOCIAL_PROMPT,
    _SOCIAL_STANDALONE_PROMPT,
    _build_social_universal_rules,
    _build_standalone_voice_injection,
    _build_template_structure,
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
        assert "test, phrase" in result
        assert "test—phrase" not in result

    def test_em_dash_in_voice_anchor_replaced(self):
        bvp = {**_BASE_BVP, "voice_anchor_sentences": ["sentence—with dash"]}
        result = _build_voice_injection(bvp)
        assert "sentence, with dash" in result
        assert "sentence—with dash" not in result

    def test_em_dash_in_anti_pattern_replaced(self):
        bvp = {**_BASE_BVP, "anti_pattern_example": "example—bad sentence"}
        result = _build_voice_injection(bvp)
        assert "example, bad sentence" in result
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
        assert "test, phrase" in result
        assert "test—phrase" not in result

    def test_em_dash_in_anti_pattern_replaced(self):
        bvp = {"anti_pattern_example": "bad—example"}
        result = _build_standalone_voice_injection(bvp)
        assert "bad, example" in result
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

    def test_strips_trailer_containing_gt_character(self):
        html = "<p>Done.</p>\n--- keyword density > 2%"
        assert _strip_blog_trailer(html) == "<p>Done.</p>"


# ── TestWordCountPrompt -- Story 3.23: Blog target length selector ─────────────

class TestWordCountPrompt:
    """Tests for {word_count_range} and {length_override_section} placeholders.

    These tests verify the prompt building logic in gemini.py / anthropic_client.py
    by inspecting the format parameters passed to _BLOG_PROMPT. All tests use only
    the prompt template and the word-count formatting logic -- no LLM calls made.
    """

    def _build_prompt(self, target_word_count=None):
        """Build the blog prompt with the same logic used in generate_blog."""
        from app.integrations.generation_prompts import _BLOG_PROMPT, _DEFAULT_VOICE

        _WORD_COUNT_MAP = {
            "300-500": "300-500 words",
            "600-1000": "600-1,000 words",
            "1500-2500": "1,500-2,500 words",
        }
        word_count_range = _WORD_COUNT_MAP.get(target_word_count or "", "900-1,500 words")

        if target_word_count == "300-500":
            length_override_section = (
                "QUICK READ MODE (300-500 words):\n"
                "- Strict word limit: 300-500 words total including all headings and HTML.\n"
                '- OMIT the <div class="tldr"> block entirely. Do not output it.\n'
                "- OMIT the <h2>Frequently Asked Questions</h2> and <dl class=\"faq\"> block entirely.\n"
                "- Write 1-2 H2 body sections only (not 3-4).\n"
                "- The BLUF intro paragraph and conclusion are still required.\n"
                "- Every sentence must earn its place. Cut anything that does not give the reader\n"
                "  a new fact or a specific action."
            )
        else:
            length_override_section = ""

        return _BLOG_PROMPT.format(
            voice_section=_DEFAULT_VOICE,
            meta_voice_note="",
            brain_dump="test brain dump",
            tone_list="professional",
            cadence_instruction="avg sentence length 15 words",
            banned_jargon_list="none",
            seo_target_section="",
            audience_section="",
            word_count_range=word_count_range,
            template_structure_override="",
            length_override_section=length_override_section,
        )

    def test_word_count_standard_default(self):
        """None target_word_count maps to 900-1,500 words with no QUICK READ block."""
        prompt = self._build_prompt(target_word_count=None)
        assert "900-1,500 words" in prompt
        assert "QUICK READ MODE" not in prompt

    def test_word_count_quick_read(self):
        """300-500 target maps to 300-500 words range and includes QUICK READ block."""
        prompt = self._build_prompt(target_word_count="300-500")
        assert "300-500 words" in prompt
        assert "QUICK READ MODE" in prompt
        assert 'OMIT the <div class="tldr">' in prompt

    def test_word_count_in_depth(self):
        """1500-2500 target maps to 1,500-2,500 words with no QUICK READ block."""
        prompt = self._build_prompt(target_word_count="1500-2500")
        assert "1,500-2,500 words" in prompt
        assert "QUICK READ MODE" not in prompt


# ── _build_template_structure tests: Story 3.24 ───────────────────────────────

class TestBuildTemplateStructure:
    def test_template_standard_no_override(self):
        """_build_template_structure("standard", "") returns empty string."""
        result = _build_template_structure("standard", "")
        assert result == ""

    def test_template_none_no_override(self):
        """_build_template_structure(None, "") returns empty string."""
        result = _build_template_structure(None, "")
        assert result == ""

    def test_template_how_to_structure(self):
        """_build_template_structure("how-to", "") contains expected markers."""
        result = _build_template_structure("how-to", "")
        assert "HOW-TO GUIDE" in result
        assert "What You Will Need" in result
        assert "Step 1:" in result
        assert "Frequently Asked Questions" in result

    def test_template_listicle_structure(self):
        """_build_template_structure("listicle", "") contains expected markers."""
        result = _build_template_structure("listicle", "")
        assert "LISTICLE" in result
        assert "<ol>" in result
        assert "<h3>" in result
        assert "Do NOT add a FAQ section" in result

    def test_template_thought_leadership_structure(self):
        """_build_template_structure("thought-leadership", "") contains expected markers."""
        result = _build_template_structure("thought-leadership", "")
        assert "THOUGHT LEADERSHIP" in result
        assert "counter-argument" in result
        assert "Do NOT add a FAQ section" in result


# ── _build_social_universal_rules tests: Story 3.26 ──────────────────────────

class TestBuildSocialUniversalRules:
    def test_returns_banned_jargon_when_present(self):
        bvp = {"banned_jargon": ["leverage", "synergy"]}
        result = _build_social_universal_rules(bvp, "professional", "avg sentence length 15 words")
        assert "BANNED WORDS" in result
        assert "leverage" in result
        assert "synergy" in result

    def test_omits_banned_jargon_when_empty(self):
        bvp = {"banned_jargon": []}
        result = _build_social_universal_rules(bvp, "professional", "avg sentence length 15 words")
        assert "BANNED WORDS" not in result

    def test_omits_banned_jargon_when_absent(self):
        result = _build_social_universal_rules({}, "professional", "avg sentence length 15 words")
        assert "BANNED WORDS" not in result

    def test_professional_tone_avoids_contractions(self):
        result = _build_social_universal_rules({}, "professional, authoritative", "avg sentence length 15 words")
        assert "avoid" in result.lower()
        assert "Contractions" in result

    def test_casual_tone_uses_contractions(self):
        result = _build_social_universal_rules({}, "casual, friendly", "avg sentence length 15 words")
        assert "use naturally" in result.lower() or "use contractions" in result.lower() or "use naturally throughout" in result

    def test_neutral_tone_omits_contractions_rule(self):
        result = _build_social_universal_rules({}, "clear, direct", "avg sentence length 15 words")
        assert "Contractions" not in result

    def test_always_includes_dash_ban(self):
        result = _build_social_universal_rules({}, "professional", "avg sentence length 15 words")
        assert "em-dash" in result
        assert "double-dash" in result
        assert "flows naturally" in result

    def test_always_includes_banned_openers(self):
        result = _build_social_universal_rules({}, "professional", "avg sentence length 15 words")
        assert "In today's fast-paced world" in result
        assert "As we all know" in result

    def test_always_includes_passive_voice_rule(self):
        result = _build_social_universal_rules({}, "professional", "avg sentence length 15 words")
        assert "passive voice" in result.lower()

    def test_specificity_rule_injected_when_concrete_numbers(self):
        bvp = {"specificity_preference": "concrete_numbers"}
        result = _build_social_universal_rules(bvp, "professional", "avg sentence length 15 words")
        assert "specific numbers" in result

    def test_specificity_rule_omitted_when_not_concrete_numbers(self):
        bvp = {"specificity_preference": "general"}
        result = _build_social_universal_rules(bvp, "professional", "avg sentence length 15 words")
        assert "specific numbers" not in result

    def test_tone_and_cadence_appear_in_output(self):
        result = _build_social_universal_rules({}, "direct, authoritative", "avg sentence length 12 words")
        assert "direct, authoritative" in result
        assert "avg sentence length 12 words" in result


# ── Anti-pattern scope test: Story 3.26 AC 11 ────────────────────────────────

class TestStandaloneVoiceInjectionAntiPatternScope:
    def test_anti_pattern_appears_before_linkedin_section(self):
        bvp = {
            "opening_pattern": "bold_claim",
            "anti_pattern_example": "The paradigm shift enables us to leverage synergies.",
        }
        result = _build_standalone_voice_injection(bvp)
        assert "ANTI-PATTERN" in result
        assert "apply to all posts" in result
        anti_pos = result.index("ANTI-PATTERN")
        linkedin_pos = result.index("apply to linkedin_post only")
        assert anti_pos < linkedin_pos

    def test_anti_pattern_without_other_hints_returns_just_anti_block(self):
        bvp = {"anti_pattern_example": "Plain corporate sentence here."}
        result = _build_standalone_voice_injection(bvp)
        assert "ANTI-PATTERN" in result
        assert "apply to all posts" in result
        assert "BRAND STRUCTURE HINTS" not in result


# ── TestAssistPrompt -- Story 3.28: Assist mode ───────────────────────────────

class TestAssistPrompt:
    """_BLOG_ASSIST_PROMPT contains correct directives and omits default-mode scaffolding."""

    def _render(self, brain_dump: str = "test brain dump") -> str:
        return _BLOG_ASSIST_PROMPT.format(brain_dump=brain_dump)

    def test_prompt_formats_without_error(self):
        result = self._render("My writing goes here.")
        assert "My writing goes here." in result

    def test_preserve_directive_present(self):
        result = self._render()
        lower = result.lower()
        assert "reproduce" in lower or "faithfully" in lower or "preserve" in lower

    def test_no_restructure_directive(self):
        result = self._render()
        lower = result.lower()
        assert "do not restructure" in lower or "not restructure" in lower

    def test_no_vocabulary_substitution_directive(self):
        result = self._render()
        lower = result.lower()
        assert "synonym" in lower or "substitute vocabulary" in lower or "word choices" in lower

    def test_no_brand_voice_profile_application(self):
        result = self._render()
        lower = result.lower()
        assert "do not apply" in lower or "not apply" in lower

    def test_no_tldr_added(self):
        result = self._render()
        lower = result.lower()
        assert "tldr" in lower or "tl;dr" in lower

    def test_no_faq_added(self):
        result = self._render()
        lower = result.lower()
        assert "faq" in lower

    def test_html_only_output_rule(self):
        result = self._render()
        lower = result.lower()
        assert "valid html" in lower

    def test_em_dash_ban_in_assist_prompt(self):
        result = self._render()
        assert "em-dash" in result

    def test_double_hyphen_ban_in_assist_prompt(self):
        result = self._render()
        lower = result.lower()
        assert "double-hyphen" in lower or "double hyphen" in lower

    def test_no_mandatory_structure_scaffolding(self):
        result = self._render()
        assert "MANDATORY STRUCTURE" not in result
        assert "BLUF" not in result


# ── TestDefaultPromptSoftenedPreservation -- Story 3.28 AC 5 ─────────────────

class TestDefaultPromptSoftenedPreservation:
    """Verify _BLOG_PROMPT authored-passage definition is broadened per AC 5."""

    def test_single_strong_sentence_treated_as_authored(self):
        lower = _BLOG_PROMPT.lower()
        assert "single strong" in lower or "single" in lower

    def test_finished_prose_classification_expanded(self):
        assert "finished prose" in _BLOG_PROMPT.lower()

    def test_authored_passage_corrections_only_language_strong(self):
        lower = _BLOG_PROMPT.lower()
        assert "corrections only" in lower or "grammar and punctuation corrections only" in lower

    def test_authored_passage_any_voice(self):
        lower = _BLOG_PROMPT.lower()
        assert "any voice" in lower or "non-first-person" in lower
