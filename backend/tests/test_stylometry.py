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
        assert len(COMPUTED_FIELD_NAMES) == 5
