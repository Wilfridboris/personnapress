"""Unit tests for compute_stylometric_fields (Story 16.1 AC 4/6)."""

import pytest

from app.services.stylometry import COMPUTED_FIELD_NAMES, compute_stylometric_fields

# ── Fixtures ──────────────────────────────────────────────────────────────────

SENTENCE_NORMAL = "The quick brown fox jumps over the lazy dog. " * 5  # 45 words per repeat


def _make_normal_text() -> str:
    """300+ words, varied sentence lengths."""
    short = "Yes. No. OK. "
    long_sent = "This is a significantly longer sentence that contains many more words than the others do. "
    block = (short * 5) + (long_sent * 5)
    # Repeat enough to exceed 300 words, separated by double newlines for paragraphs.
    return "\n\n".join([block] * 6)


def _make_short_text() -> str:
    """Under 300 words."""
    return "Hello world. " * 15  # ~30 words


def _make_contraction_free_text() -> str:
    """Long text with no contractions at all."""
    sentence = "The engineers reviewed all of the documentation before submitting the final report. "
    return (sentence * 30) + "\n\n" + (sentence * 30)


def _make_heavy_list_text() -> str:
    """More than 20% of paragraphs start with a list marker."""
    normal_para = "This is a normal paragraph with some content in it.\n"
    list_para = "- First item in the list\n"
    parts = []
    for i in range(10):
        parts.append(list_para)  # 10 list paras
        parts.append(normal_para)  # 10 normal paras → 50% list
    return "\n\n".join(parts)


def _make_uniform_text() -> str:
    """All sentences have very similar word counts (stddev < 4)."""
    sentence = "The cat sat on the mat and looked around. "  # ~9 words
    # Repeat 80 times (720+ words, very uniform)
    return sentence * 80


def _make_varied_text() -> str:
    """Sentences with high variance in length (stddev >= 4)."""
    short = "OK. " * 10
    long_sent = (
        "This particular sentence is intentionally much longer than all of the other "
        "sentences in this block of text so that we get a high standard deviation. " * 5
    )
    block = short + long_sent
    return (block + "\n\n") * 8


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestNormalText:
    def setup_method(self):
        self.result = compute_stylometric_fields(_make_normal_text())

    def test_returns_all_five_keys(self):
        for key in COMPUTED_FIELD_NAMES:
            assert key in self.result, f"Missing key: {key}"

    def test_no_low_confidence_flag(self):
        assert "low_confidence" not in self.result

    def test_sentence_length_avg_is_int(self):
        assert isinstance(self.result["sentence_length_avg"], int)

    def test_sentence_rhythm_valid_value(self):
        assert self.result["sentence_rhythm"] in {"uniform", "varied"}

    def test_paragraph_density_valid_value(self):
        assert self.result["paragraph_density"] in {"airy", "moderate", "dense"}

    def test_contraction_frequency_valid_value(self):
        assert self.result["contraction_frequency"] in {"never", "occasional", "frequent"}

    def test_list_preference_valid_value(self):
        assert self.result["list_preference"] in {"rarely", "sometimes", "often"}


class TestShortText:
    def setup_method(self):
        self.result = compute_stylometric_fields(_make_short_text())

    def test_returns_all_five_keys(self):
        for key in COMPUTED_FIELD_NAMES:
            assert key in self.result, f"Missing key: {key}"

    def test_low_confidence_is_true(self):
        assert self.result.get("low_confidence") is True


def _make_contraction_heavy_text() -> str:
    """Text with enough contractions to exceed the 5% threshold."""
    sentence = "I'm not sure we'll go, but they're saying it's fine and can't wait. "
    return sentence * 60


class TestContractionFreeText:
    def test_contraction_frequency_is_never(self):
        result = compute_stylometric_fields(_make_contraction_free_text())
        assert result["contraction_frequency"] == "never"


class TestContractionHeavyText:
    def test_contraction_frequency_is_not_never(self):
        result = compute_stylometric_fields(_make_contraction_heavy_text())
        assert result["contraction_frequency"] in {"occasional", "frequent"}


class TestHeavyListText:
    def test_list_preference_is_often(self):
        result = compute_stylometric_fields(_make_heavy_list_text())
        assert result["list_preference"] == "often"


class TestUniformSentenceLengths:
    def test_sentence_rhythm_is_uniform(self):
        result = compute_stylometric_fields(_make_uniform_text())
        assert result["sentence_rhythm"] == "uniform"


class TestVariedSentenceLengths:
    def test_sentence_rhythm_is_varied(self):
        result = compute_stylometric_fields(_make_varied_text())
        assert result["sentence_rhythm"] == "varied"


class TestEdgeCases:
    def test_empty_string_does_not_raise(self):
        result = compute_stylometric_fields("")
        for key in COMPUTED_FIELD_NAMES:
            assert key in result

    def test_empty_string_has_low_confidence(self):
        result = compute_stylometric_fields("")
        assert result.get("low_confidence") is True

    def test_single_sentence_no_stdev_crash(self):
        result = compute_stylometric_fields("Hello world this is a single sentence.")
        assert result["sentence_rhythm"] in {"uniform", "varied"}

    def test_computed_field_names_constant(self):
        assert "low_confidence" not in COMPUTED_FIELD_NAMES
        assert len(COMPUTED_FIELD_NAMES) == 11


# ── Story 26.2: New micro-style field tests ────────────────────────────────────

def _make_lowercase_leaning_text() -> str:
    """More than 30% of sentences start with a lowercase letter."""
    # Repeat 'lowercase opener. ' 7 times + 'Standard opener. ' 3 times = 70% lowercase
    lower = "lowercase opener sentence here. " * 70
    upper = "Standard opener sentence here. " * 30
    # interleave so spaCy sentence detection works well
    return (lower + upper) * 5


def _make_standard_casing_text() -> str:
    """All sentences start with an uppercase letter."""
    return "The cat sat on the mat. The dog ran over the hill. Everyone was happy. " * 50


def _make_mixed_casing_text() -> str:
    """Between 10-30% of sentences start with lowercase."""
    lower = "lowercase sentence here. " * 15
    upper = "Standard sentence here. " * 85
    return lower + upper


def _make_heavy_comma_text() -> str:
    """More than 8 commas per 100 words."""
    # Each sentence has 4 commas in ~10 words => ~40 commas per 100 words
    sentence = "One, two, three, four, five words per sentence here done. "
    return sentence * 60


def _make_light_comma_text() -> str:
    """Fewer than 4 commas per 100 words -- no commas at all."""
    sentence = "The quick brown fox jumps over the lazy dog today. "
    return sentence * 60


def _make_exclamation_frequent_text() -> str:
    """Exclamation marks at >= 0.5 per 100 words."""
    # 1 exclamation per ~5 words => 20 per 100 words
    return "Wow amazing! Great job! Excellent work! Fantastic result! " * 60


def _make_exclamation_rare_text() -> str:
    """Exactly one exclamation mark in a long piece."""
    base = "The report was thorough and well-structured throughout the analysis. " * 80
    return base + "Excellent!"


def _make_ellipsis_text() -> str:
    """Text with more than one occurrence of '...'"""
    return "I was thinking... maybe not... let me reconsider... definitely not. " * 20


def _make_parenthetical_frequent_text() -> str:
    """More than 3 pairs of parentheses per 1000 words."""
    # 1 pair per ~5 words => 200 pairs per 1000 words
    sentence = "This is a sentence (with an aside) that continues. "
    return sentence * 60


def _make_parenthetical_rare_text() -> str:
    """Fewer than 1 pair of parentheses per 1000 words."""
    return "The quick brown fox jumps over the lazy dog today. " * 60


class TestCasingStyle:
    def test_standard_casing(self):
        result = compute_stylometric_fields(_make_standard_casing_text())
        assert result["casing_style"] == "standard"

    def test_lowercase_leaning(self):
        result = compute_stylometric_fields(_make_lowercase_leaning_text())
        assert result["casing_style"] == "lowercase_leaning"

    def test_empty_text_returns_standard(self):
        result = compute_stylometric_fields("")
        assert result["casing_style"] == "standard"

    def test_casing_style_valid_values(self):
        result = compute_stylometric_fields(_make_normal_text())
        assert result["casing_style"] in {"standard", "mixed", "lowercase_leaning"}


class TestCommaDensity:
    def test_heavy_comma_density(self):
        result = compute_stylometric_fields(_make_heavy_comma_text())
        assert result["comma_density"] == "heavy"

    def test_light_comma_density(self):
        result = compute_stylometric_fields(_make_light_comma_text())
        assert result["comma_density"] == "light"

    def test_comma_density_valid_values(self):
        result = compute_stylometric_fields(_make_normal_text())
        assert result["comma_density"] in {"light", "moderate", "heavy"}

    def test_empty_text_returns_light(self):
        result = compute_stylometric_fields("")
        assert result["comma_density"] == "light"


class TestExclamationFrequency:
    def test_frequent_exclamations(self):
        result = compute_stylometric_fields(_make_exclamation_frequent_text())
        assert result["exclamation_frequency"] == "frequent"

    def test_rare_exclamations(self):
        result = compute_stylometric_fields(_make_exclamation_rare_text())
        assert result["exclamation_frequency"] == "rare"

    def test_never_exclamations(self):
        result = compute_stylometric_fields(_make_light_comma_text())
        assert result["exclamation_frequency"] == "never"

    def test_exclamation_frequency_valid_values(self):
        result = compute_stylometric_fields(_make_normal_text())
        assert result["exclamation_frequency"] in {"never", "rare", "frequent"}


class TestEllipsisUsage:
    def test_ellipsis_detected(self):
        result = compute_stylometric_fields(_make_ellipsis_text())
        assert result["ellipsis_usage"] is True

    def test_no_ellipsis(self):
        result = compute_stylometric_fields(_make_standard_casing_text())
        assert result["ellipsis_usage"] is False

    def test_single_ellipsis_not_flagged(self):
        text = "The cat sat on the mat. Maybe... I don't know. " * 40
        result = compute_stylometric_fields(text)
        # Only one "..." -- should not be flagged
        assert result["ellipsis_usage"] is False

    def test_ellipsis_usage_is_bool(self):
        result = compute_stylometric_fields(_make_normal_text())
        assert isinstance(result["ellipsis_usage"], bool)


class TestParentheticalUsage:
    def test_frequent_parentheticals(self):
        result = compute_stylometric_fields(_make_parenthetical_frequent_text())
        assert result["parenthetical_usage"] == "frequent"

    def test_rare_parentheticals(self):
        result = compute_stylometric_fields(_make_parenthetical_rare_text())
        assert result["parenthetical_usage"] == "rare"

    def test_parenthetical_usage_valid_values(self):
        result = compute_stylometric_fields(_make_normal_text())
        assert result["parenthetical_usage"] in {"rare", "occasional", "frequent"}

    def test_empty_text_returns_rare(self):
        result = compute_stylometric_fields("")
        assert result["parenthetical_usage"] == "rare"


class TestSentenceLengthStdev:
    def test_stdev_is_int(self):
        result = compute_stylometric_fields(_make_normal_text())
        assert isinstance(result["sentence_length_stdev"], int)

    def test_single_sentence_stdev_is_zero(self):
        result = compute_stylometric_fields("Hello world this is one sentence only.")
        assert result["sentence_length_stdev"] == 0

    def test_empty_text_stdev_is_zero(self):
        result = compute_stylometric_fields("")
        assert result["sentence_length_stdev"] == 0

    def test_varied_text_has_nonzero_stdev(self):
        result = compute_stylometric_fields(_make_varied_text())
        assert result["sentence_length_stdev"] > 0


class TestAllNewFieldsPresent:
    """AC 1: All 6 new fields are always present in the output dict."""

    def test_all_new_fields_present_on_normal_text(self):
        new_fields = {
            "casing_style", "comma_density", "exclamation_frequency",
            "ellipsis_usage", "parenthetical_usage", "sentence_length_stdev",
        }
        result = compute_stylometric_fields(_make_normal_text())
        for field in new_fields:
            assert field in result, f"Missing field: {field}"

    def test_all_new_fields_present_on_short_text(self):
        new_fields = {
            "casing_style", "comma_density", "exclamation_frequency",
            "ellipsis_usage", "parenthetical_usage", "sentence_length_stdev",
        }
        result = compute_stylometric_fields(_make_short_text())
        for field in new_fields:
            assert field in result, f"Missing field on short text: {field}"

    def test_all_new_fields_present_on_empty_text(self):
        new_fields = {
            "casing_style", "comma_density", "exclamation_frequency",
            "ellipsis_usage", "parenthetical_usage", "sentence_length_stdev",
        }
        result = compute_stylometric_fields("")
        for field in new_fields:
            assert field in result, f"Missing field on empty text: {field}"
