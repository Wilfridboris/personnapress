"""Unit tests for Story 16.2: Gemini qualitative extraction and voice brief synthesis."""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure modules are in sys.modules so @patch decorators can resolve them
import app.integrations.gemini  # noqa: F401
import app.services.ingestion  # noqa: F401


# ── Shared fixtures ───────────────────────────────────────────────────────────

def _make_response(text: str):
    mock = MagicMock()
    mock.text = text
    return mock


def _aio_generate(response_text: str) -> AsyncMock:
    return AsyncMock(return_value=_make_response(response_text))


_BASE_BVP = {
    "tone": ["authoritative", "direct"],
    "cadence": {
        "avg_sentence_length": 16,
        "variation_pattern": "short punchy sentences",
        "paragraph_structure": "3-4 sentences opening with a claim",
    },
    "banned_jargon": ["leverage", "synergy"],
    "target_audience": "B2B SaaS marketers",
}

_FULL_QUALITATIVE = {
    "pronoun_preference": "first_person",
    "formality_scale": 2,
    "humor_style": "dry",
    "vocabulary_complexity": "mixed",
    "example_style": "data",
    "specificity_preference": "concrete_numbers",
    "opening_pattern": "bold_claim",
    "closing_pattern": "cta",
    "header_style": "statement",
    "post_structure_template": "hook -- pain -- insight -- example -- CTA",
    "signature_phrases": ["Let me be blunt", "the data says otherwise"],
    "voice_anchor_sentences": ["Here is what the numbers actually show."],
    "anti_pattern_example": "In today's rapidly evolving landscape, it is important to note...",
}

_FULL_BVP = {**_BASE_BVP, **_FULL_QUALITATIVE}

_VOICE_BRIEF = (
    "This writer communicates with a candid, first-person voice that wastes no words. "
    "Their formality sits closer to conversational than formal, and they rarely avoid contractions. "
    "Sentences alternate between short declarations and longer evidence-backed statements, "
    "creating a rhythm that feels deliberate rather than uniform. Posts almost always open "
    "with a bold claim that challenges a common assumption, then pivot to data. They close "
    "with a direct call to action rather than a summary, trusting the reader to draw their "
    "own conclusions from the evidence presented. Vocabulary leans mixed: accessible enough "
    "for a broad business audience yet precise enough to signal expertise. Their dry humor "
    "surfaces occasionally in parenthetical asides. The signature move is a short, punchy "
    "sentence after a long analytical paragraph -- a full stop that lands like a period at "
    "the end of an argument. What you will never find is the bloated throat-clearing prose "
    "of committee writing."
)


# ── Tests for extract_brand_voice (gemini.py) ─────────────────────────────────

class TestFullExtraction:
    """AC 1/2/3: All 15 new qualitative fields returned and stored correctly."""

    @pytest.mark.asyncio
    @patch("app.integrations.gemini._client")
    async def test_all_new_fields_stored_correctly(self, mock_client):
        from app.integrations.gemini import extract_brand_voice

        extraction_json = json.dumps(_FULL_BVP)
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=[
                _make_response(extraction_json),
                _make_response(_VOICE_BRIEF),
            ]
        )

        result = await extract_brand_voice("sample text")

        assert result["pronoun_preference"] == "first_person"
        assert result["formality_scale"] == 2
        assert result["humor_style"] == "dry"
        assert result["vocabulary_complexity"] == "mixed"
        assert result["example_style"] == "data"
        assert result["specificity_preference"] == "concrete_numbers"
        assert result["opening_pattern"] == "bold_claim"
        assert result["closing_pattern"] == "cta"
        assert result["header_style"] == "statement"
        assert result["post_structure_template"] == "hook -- pain -- insight -- example -- CTA"
        assert result["signature_phrases"] == ["Let me be blunt", "the data says otherwise"]
        assert result["voice_anchor_sentences"] == ["Here is what the numbers actually show."]
        assert result["anti_pattern_example"].startswith("In today's")

    @pytest.mark.asyncio
    @patch("app.integrations.gemini._client")
    async def test_existing_tone_cadence_banned_jargon_preserved(self, mock_client):
        from app.integrations.gemini import extract_brand_voice

        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=[
                _make_response(json.dumps(_FULL_BVP)),
                _make_response(_VOICE_BRIEF),
            ]
        )

        result = await extract_brand_voice("sample text")

        assert result["tone"] == ["authoritative", "direct"]
        assert isinstance(result["cadence"], dict)
        assert result["banned_jargon"] == ["leverage", "synergy"]


class TestMissingFieldDefaults:
    """AC 3: Missing new fields receive correct silent defaults."""

    @pytest.mark.asyncio
    @patch("app.integrations.gemini._client")
    async def test_three_missing_fields_get_defaults(self, mock_client):
        from app.integrations.gemini import extract_brand_voice

        partial = dict(_FULL_BVP)
        del partial["humor_style"]
        del partial["signature_phrases"]
        del partial["post_structure_template"]

        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=[
                _make_response(json.dumps(partial)),
                _make_response(_VOICE_BRIEF),
            ]
        )

        result = await extract_brand_voice("sample text")

        assert result["humor_style"] == "none"
        assert result["signature_phrases"] == []
        assert result["post_structure_template"] == ""

    @pytest.mark.asyncio
    @patch("app.integrations.gemini._client")
    async def test_null_field_receives_default(self, mock_client):
        from app.integrations.gemini import extract_brand_voice

        with_null = dict(_FULL_BVP)
        with_null["formality_scale"] = None

        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=[
                _make_response(json.dumps(with_null)),
                _make_response(_VOICE_BRIEF),
            ]
        )

        result = await extract_brand_voice("sample text")

        assert result["formality_scale"] == 3  # default

    @pytest.mark.asyncio
    @patch("app.integrations.gemini._client")
    async def test_all_defaults_applied_when_all_new_fields_missing(self, mock_client):
        from app.integrations.gemini import extract_brand_voice

        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=[
                _make_response(json.dumps(_BASE_BVP)),
                _make_response(_VOICE_BRIEF),
            ]
        )

        result = await extract_brand_voice("sample text")

        assert result["pronoun_preference"] == "mixed"
        assert result["formality_scale"] == 3
        assert result["humor_style"] == "none"
        assert result["vocabulary_complexity"] == "plain"
        assert result["example_style"] == "direct"
        assert result["specificity_preference"] == "mixed"
        assert result["opening_pattern"] == "bold_claim"
        assert result["closing_pattern"] == "none"
        assert result["header_style"] == "statement"
        assert result["post_structure_template"] == ""
        assert result["signature_phrases"] == []
        assert result["voice_anchor_sentences"] == []
        assert result["anti_pattern_example"] == ""

    @pytest.mark.asyncio
    @patch("app.integrations.gemini._client")
    async def test_hard_validation_unchanged_for_tone(self, mock_client):
        """AC 4: existing isinstance checks for tone/cadence/banned_jargon still raise."""
        from app.integrations.gemini import extract_brand_voice

        bad = dict(_BASE_BVP)
        bad["tone"] = "not a list"

        mock_client.aio.models.generate_content = AsyncMock(
            return_value=_make_response(json.dumps(bad))
        )

        with pytest.raises(ValueError, match="tone"):
            await extract_brand_voice("sample text")


class TestVoiceBriefSynthesis:
    """AC 5/6/7: synthesize_voice_brief is called and voice_brief stored in BVP."""

    @pytest.mark.asyncio
    @patch("app.integrations.gemini.synthesize_voice_brief", new_callable=AsyncMock)
    @patch("app.integrations.gemini._client")
    async def test_synthesize_voice_brief_called_after_extraction(
        self, mock_client, mock_synthesize
    ):
        from app.integrations.gemini import extract_brand_voice

        mock_client.aio.models.generate_content = _aio_generate(json.dumps(_FULL_BVP))
        mock_synthesize.return_value = _VOICE_BRIEF

        result = await extract_brand_voice("sample text")

        assert mock_synthesize.called
        assert result["voice_brief"] == _VOICE_BRIEF

    @pytest.mark.asyncio
    @patch("app.integrations.gemini.synthesize_voice_brief", new_callable=AsyncMock)
    @patch("app.integrations.gemini._client")
    async def test_synthesize_voice_brief_receives_full_bvp(
        self, mock_client, mock_synthesize
    ):
        from app.integrations.gemini import extract_brand_voice

        mock_client.aio.models.generate_content = _aio_generate(json.dumps(_FULL_BVP))
        mock_synthesize.return_value = _VOICE_BRIEF

        await extract_brand_voice("sample text")

        call_arg = mock_synthesize.call_args[0][0]
        assert "tone" in call_arg
        assert "pronoun_preference" in call_arg

    @pytest.mark.asyncio
    @patch("app.integrations.gemini._client")
    async def test_voice_brief_failure_stores_empty_string(self, mock_client):
        """AC 6: Gemini failure in synthesize_voice_brief returns empty string, no exception."""
        from app.integrations.gemini import extract_brand_voice

        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=[
                _make_response(json.dumps(_FULL_BVP)),  # extraction call succeeds
                Exception("Gemini 503"),                # brief call fails
            ]
        )

        result = await extract_brand_voice("sample text")

        assert result["voice_brief"] == ""
        assert "tone" in result  # rest of BVP still valid

    @pytest.mark.asyncio
    @patch("app.integrations.gemini._client")
    async def test_voice_brief_stored_as_bvp_field(self, mock_client):
        """AC 7: voice_brief key present on returned dict."""
        from app.integrations.gemini import extract_brand_voice

        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=[
                _make_response(json.dumps(_FULL_BVP)),
                _make_response(_VOICE_BRIEF),
            ]
        )

        result = await extract_brand_voice("sample text")

        assert "voice_brief" in result
        assert isinstance(result["voice_brief"], str)

    @pytest.mark.asyncio
    @patch("app.integrations.gemini._client")
    async def test_synthesize_voice_brief_default_thinking_tokens(self, mock_client):
        """AC 5: synthesize_voice_brief uses 256 thinking tokens by default."""
        from app.integrations.gemini import synthesize_voice_brief

        mock_client.aio.models.generate_content = _aio_generate(_VOICE_BRIEF)

        await synthesize_voice_brief(_FULL_BVP)

        call_kwargs = mock_client.aio.models.generate_content.call_args.kwargs
        assert call_kwargs["config"].thinking_config.thinking_budget == 256


# ── Tests for extract_voice_profile merge (ingestion.py) ─────────────────────

_EXISTING_BVP = {
    "tone": ["warm", "casual"],
    "cadence": {"avg_sentence_length": 12, "variation_pattern": "uniform", "paragraph_structure": "short"},
    "banned_jargon": ["synergy", "leverage"],
    "target_audience": "small business owners",
    "signature_phrases": ["keep it simple"],
    "voice_anchor_sentences": ["Simple is always better."],
}

_NEW_BVP_FROM_GEMINI = {
    "tone": ["direct", "clear"],
    "cadence": {"avg_sentence_length": 14, "variation_pattern": "varied", "paragraph_structure": "medium"},
    "banned_jargon": ["leverage", "paradigm"],  # "leverage" duplicated; "paradigm" is new
    "target_audience": "entrepreneurs",
    "pronoun_preference": "first_person",
    "formality_scale": 2,
    "humor_style": "dry",
    "vocabulary_complexity": "plain",
    "example_style": "story",
    "specificity_preference": "concrete_numbers",
    "opening_pattern": "anecdote",
    "closing_pattern": "cta",
    "header_style": "question",
    "post_structure_template": "hook -- story -- lesson -- CTA",
    "signature_phrases": ["let me be real", "the numbers tell the story"],
    "voice_anchor_sentences": ["Real results require real effort."],
    "anti_pattern_example": "It is important to leverage synergies.",
    "voice_brief": _VOICE_BRIEF,
}


def _make_existing_client(bvp: dict | None = None):
    c = MagicMock()
    c.brand_voice_profile = bvp
    return c


class TestRefreshMergeScalars:
    """AC 8/9: Scalar fields are replaced on refresh."""

    @pytest.mark.asyncio
    @patch("app.services.ingestion.update_client", new_callable=AsyncMock)
    @patch("app.services.ingestion.get_client", new_callable=AsyncMock)
    @patch("app.services.ingestion.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.ingestion.gemini")
    async def test_scalar_fields_replaced_on_refresh(
        self, mock_gemini, mock_sleep, mock_get_client, mock_update_client
    ):
        from app.services.ingestion import extract_voice_profile

        mock_get_client.return_value = _make_existing_client(_EXISTING_BVP)
        mock_gemini.extract_brand_voice = AsyncMock(return_value=dict(_NEW_BVP_FROM_GEMINI))
        mock_gemini.synthesize_voice_brief = AsyncMock(return_value=_VOICE_BRIEF)
        session = AsyncMock()
        client_id = uuid.uuid4()

        result = await extract_voice_profile("text", client_id, session=session)

        # Scalar fields replaced by new extraction
        assert result["tone"] == ["direct", "clear"]
        assert result["target_audience"] == "entrepreneurs"
        assert result["formality_scale"] == 2
        assert result["opening_pattern"] == "anecdote"

    @pytest.mark.asyncio
    @patch("app.services.ingestion.update_client", new_callable=AsyncMock)
    @patch("app.services.ingestion.get_client", new_callable=AsyncMock)
    @patch("app.services.ingestion.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.ingestion.gemini")
    async def test_merged_bvp_written_to_db(
        self, mock_gemini, mock_sleep, mock_get_client, mock_update_client
    ):
        from app.services.ingestion import extract_voice_profile

        mock_get_client.return_value = _make_existing_client(_EXISTING_BVP)
        mock_gemini.extract_brand_voice = AsyncMock(return_value=dict(_NEW_BVP_FROM_GEMINI))
        mock_gemini.synthesize_voice_brief = AsyncMock(return_value=_VOICE_BRIEF)
        session = AsyncMock()
        client_id = uuid.uuid4()

        result = await extract_voice_profile("text", client_id, session=session)

        mock_update_client.assert_called_once_with(
            session, client_id, brand_voice_profile=result
        )

    @pytest.mark.asyncio
    @patch("app.services.ingestion.update_client", new_callable=AsyncMock)
    @patch("app.services.ingestion.get_client", new_callable=AsyncMock)
    @patch("app.services.ingestion.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.ingestion.gemini")
    async def test_voice_brief_regenerated_from_merged_bvp(
        self, mock_gemini, mock_sleep, mock_get_client, mock_update_client
    ):
        """AC 8: voice_brief is always regenerated from the merged full BVP, not pre-merge."""
        from app.services.ingestion import extract_voice_profile

        mock_get_client.return_value = _make_existing_client(_EXISTING_BVP)
        mock_gemini.extract_brand_voice = AsyncMock(return_value=dict(_NEW_BVP_FROM_GEMINI))
        refreshed_brief = "Refreshed brief synthesized from merged BVP."
        mock_gemini.synthesize_voice_brief = AsyncMock(return_value=refreshed_brief)
        session = AsyncMock()

        result = await extract_voice_profile("text", uuid.uuid4(), session=session)

        # synthesize_voice_brief must have been called (from ingestion.py after merge)
        assert mock_gemini.synthesize_voice_brief.called
        # The brief stored is the post-merge synthesis, not the one embedded in the extraction fixture
        assert result["voice_brief"] == refreshed_brief


class TestRefreshMergeArrays:
    """AC 8/9: Array fields are unioned and deduplicated on refresh."""

    @pytest.mark.asyncio
    @patch("app.services.ingestion.update_client", new_callable=AsyncMock)
    @patch("app.services.ingestion.get_client", new_callable=AsyncMock)
    @patch("app.services.ingestion.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.ingestion.gemini")
    async def test_banned_jargon_union_dedup(
        self, mock_gemini, mock_sleep, mock_get_client, mock_update_client
    ):
        from app.services.ingestion import extract_voice_profile

        mock_get_client.return_value = _make_existing_client(_EXISTING_BVP)
        mock_gemini.extract_brand_voice = AsyncMock(return_value=dict(_NEW_BVP_FROM_GEMINI))
        mock_gemini.synthesize_voice_brief = AsyncMock(return_value=_VOICE_BRIEF)
        session = AsyncMock()

        result = await extract_voice_profile("text", uuid.uuid4(), session=session)

        # Existing: ["synergy", "leverage"]
        # New: ["leverage", "paradigm"]
        # Expected: ["synergy", "leverage", "paradigm"] (existing first, no dups)
        assert result["banned_jargon"] == ["synergy", "leverage", "paradigm"]

    @pytest.mark.asyncio
    @patch("app.services.ingestion.update_client", new_callable=AsyncMock)
    @patch("app.services.ingestion.get_client", new_callable=AsyncMock)
    @patch("app.services.ingestion.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.ingestion.gemini")
    async def test_signature_phrases_union_dedup(
        self, mock_gemini, mock_sleep, mock_get_client, mock_update_client
    ):
        from app.services.ingestion import extract_voice_profile

        mock_get_client.return_value = _make_existing_client(_EXISTING_BVP)
        mock_gemini.extract_brand_voice = AsyncMock(return_value=dict(_NEW_BVP_FROM_GEMINI))
        mock_gemini.synthesize_voice_brief = AsyncMock(return_value=_VOICE_BRIEF)
        session = AsyncMock()

        result = await extract_voice_profile("text", uuid.uuid4(), session=session)

        # Existing: ["keep it simple"], New: ["let me be real", "the numbers tell the story"]
        assert "keep it simple" in result["signature_phrases"]
        assert "let me be real" in result["signature_phrases"]
        # Existing items come first
        assert result["signature_phrases"].index("keep it simple") == 0

    @pytest.mark.asyncio
    @patch("app.services.ingestion.update_client", new_callable=AsyncMock)
    @patch("app.services.ingestion.get_client", new_callable=AsyncMock)
    @patch("app.services.ingestion.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.ingestion.gemini")
    async def test_no_merge_when_no_existing_bvp(
        self, mock_gemini, mock_sleep, mock_get_client, mock_update_client
    ):
        """Initial ingestion: no existing BVP, new values written directly."""
        from app.services.ingestion import extract_voice_profile

        mock_get_client.return_value = _make_existing_client(None)
        mock_gemini.extract_brand_voice = AsyncMock(return_value=dict(_NEW_BVP_FROM_GEMINI))
        session = AsyncMock()

        result = await extract_voice_profile("text", uuid.uuid4(), session=session)

        assert result["banned_jargon"] == ["leverage", "paradigm"]


class TestLegacyBVPBackwardCompatibility:
    """AC 5/10/11: Legacy BVPs (3-field) work without KeyError, defaults filled in."""

    @pytest.mark.asyncio
    @patch("app.integrations.gemini._client")
    async def test_legacy_bvp_no_key_error(self, mock_client):
        from app.integrations.gemini import extract_brand_voice

        legacy = {
            "tone": ["professional"],
            "cadence": {"avg_sentence_length": 15, "variation_pattern": "x", "paragraph_structure": "y"},
            "banned_jargon": ["jargon"],
        }

        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=[
                _make_response(json.dumps(legacy)),
                _make_response(_VOICE_BRIEF),
            ]
        )

        result = await extract_brand_voice("legacy text")

        assert result["pronoun_preference"] == "mixed"
        assert result["formality_scale"] == 3
        assert result["signature_phrases"] == []
        assert result["voice_anchor_sentences"] == []
        assert result["anti_pattern_example"] == ""
        assert result["voice_brief"] == _VOICE_BRIEF

    @pytest.mark.asyncio
    @patch("app.services.ingestion.update_client", new_callable=AsyncMock)
    @patch("app.services.ingestion.get_client", new_callable=AsyncMock)
    @patch("app.services.ingestion.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.ingestion.gemini")
    async def test_legacy_bvp_refresh_no_existing_field_loss(
        self, mock_gemini, mock_sleep, mock_get_client, mock_update_client
    ):
        """Legacy BVP refresh: existing 3-field data is preserved, new fields added."""
        from app.services.ingestion import extract_voice_profile

        legacy_existing = {
            "tone": ["bold"],
            "cadence": {"avg_sentence_length": 10, "variation_pattern": "u", "paragraph_structure": "s"},
            "banned_jargon": ["leverage"],
        }
        mock_get_client.return_value = _make_existing_client(legacy_existing)

        new_extraction = dict(_NEW_BVP_FROM_GEMINI)
        new_extraction["banned_jargon"] = ["synergy"]
        mock_gemini.extract_brand_voice = AsyncMock(return_value=new_extraction)
        mock_gemini.synthesize_voice_brief = AsyncMock(return_value=_VOICE_BRIEF)
        session = AsyncMock()

        result = await extract_voice_profile("text", uuid.uuid4(), session=session)

        # Existing banned_jargon merged with new
        assert "leverage" in result["banned_jargon"]
        assert "synergy" in result["banned_jargon"]
        # New scalar fields populated
        assert result["pronoun_preference"] == "first_person"

    @pytest.mark.asyncio
    @patch("app.services.ingestion.compute_stylometric_fields")
    @patch("app.services.ingestion.update_client", new_callable=AsyncMock)
    @patch("app.services.ingestion.get_client", new_callable=AsyncMock)
    @patch("app.services.ingestion.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.ingestion.gemini")
    async def test_computed_fields_added_on_legacy_bvp_refresh(
        self, mock_gemini, mock_sleep, mock_get_client, mock_update_client, mock_compute
    ):
        """AC 11: computed stylometric fields are added when refreshing a pre-16.1 legacy BVP."""
        from app.services.ingestion import extract_voice_profile

        legacy_existing = {
            "tone": ["bold"],
            "cadence": {"avg_sentence_length": 10, "variation_pattern": "u", "paragraph_structure": "s"},
            "banned_jargon": ["leverage"],
        }
        mock_get_client.return_value = _make_existing_client(legacy_existing)

        new_extraction = dict(_NEW_BVP_FROM_GEMINI)
        mock_gemini.extract_brand_voice = AsyncMock(return_value=new_extraction)
        mock_gemini.synthesize_voice_brief = AsyncMock(return_value=_VOICE_BRIEF)

        computed_fields = {"avg_sentence_length_mean": 14.5, "lexical_diversity": 0.72}
        mock_compute.return_value = computed_fields

        result = await extract_voice_profile("sample text", uuid.uuid4(), session=AsyncMock())

        assert result["avg_sentence_length_mean"] == 14.5
        assert result["lexical_diversity"] == 0.72
