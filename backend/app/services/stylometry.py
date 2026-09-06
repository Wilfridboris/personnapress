"""Stylometric metrics pre-processing (Story 16.1).

Computes five objective writing-style metrics from raw text using spaCy and
textstat.  All computation is local — no external API calls are made.
"""

import re
import statistics
from typing import Any

import spacy
import textstat

try:
    _nlp = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])
except OSError:
    raise RuntimeError(
        "spaCy model 'en_core_web_sm' is not installed. "
        "Run: python -m spacy download en_core_web_sm"
    ) from None
_LIST_MARKER_RE = re.compile(r"^(\s*[-*]|\s*\d+\.)[\s]")

# Computed-only field names — callers should discard these from PATCH payloads.
COMPUTED_FIELD_NAMES = frozenset(
    {
        "sentence_length_avg",
        "sentence_rhythm",
        "paragraph_density",
        "contraction_frequency",
        "list_preference",
        # Story 26.2: micro-style fields
        "casing_style",
        "comma_density",
        "exclamation_frequency",
        "ellipsis_usage",
        "parenthetical_usage",
        "sentence_length_stdev",
    }
)


def compute_stylometric_fields(text: str) -> dict[str, Any]:
    """Return a dict of five stylometric metrics computed from *text*.

    Never raises; never calls any external API.  Adds ``low_confidence: True``
    when the word count is below 300.
    """
    result: dict[str, Any] = {}

    # Cap input at 50 k chars to match the existing Gemini cap.
    doc = _nlp(text[:50_000])

    # ── 1. sentence_length_avg & sentence_rhythm ──────────────────────────────
    lengths = [
        len([t for t in sent if not t.is_punct and not t.is_space])
        for sent in doc.sents
    ]
    if lengths:
        result["sentence_length_avg"] = round(statistics.mean(lengths))
        if len(lengths) >= 2:
            result["sentence_rhythm"] = (
                "uniform" if statistics.stdev(lengths) < 4 else "varied"
            )
        else:
            result["sentence_rhythm"] = "varied"
    else:
        result["sentence_length_avg"] = 0
        result["sentence_rhythm"] = "varied"

    # ── 2. paragraph_density ─────────────────────────────────────────────────
    paragraphs = [p for p in text[:50_000].split("\n\n") if p.strip()]
    if paragraphs:
        sents_per_para = [len(list(_nlp(p).sents)) for p in paragraphs]
        avg_spp = statistics.mean(sents_per_para)
        if avg_spp <= 2:
            result["paragraph_density"] = "airy"
        elif avg_spp <= 4:
            result["paragraph_density"] = "moderate"
        else:
            result["paragraph_density"] = "dense"
    else:
        result["paragraph_density"] = "airy"

    # ── 3. contraction_frequency ─────────────────────────────────────────────
    non_space_tokens = [t for t in doc if not t.is_space]
    total_tokens = len(non_space_tokens)
    contractions = sum(1 for t in non_space_tokens if "'" in t.text)
    if contractions == 0:
        result["contraction_frequency"] = "never"
    elif total_tokens > 0 and (contractions / total_tokens) >= 0.05:
        result["contraction_frequency"] = "frequent"
    else:
        result["contraction_frequency"] = "occasional"

    # ── 4. list_preference ───────────────────────────────────────────────────
    if paragraphs:
        list_paras = sum(
            1 for p in paragraphs if _LIST_MARKER_RE.match(p)
        )
        pct = list_paras / len(paragraphs)
        if pct > 0.20:
            result["list_preference"] = "often"
        elif pct >= 0.05:
            result["list_preference"] = "sometimes"
        else:
            result["list_preference"] = "rarely"
    else:
        result["list_preference"] = "rarely"

    # ── 5. casing_style ──────────────────────────────────────────────────────
    sentences_list = list(doc.sents)
    if sentences_list:
        lowercase_starters = sum(
            1 for sent in sentences_list
            if sent.text.strip() and sent.text.strip()[0].islower()
        )
        pct_lower = lowercase_starters / len(sentences_list)
        if pct_lower > 0.30:
            result["casing_style"] = "lowercase_leaning"
        elif pct_lower >= 0.10:
            result["casing_style"] = "mixed"
        else:
            result["casing_style"] = "standard"
    else:
        result["casing_style"] = "standard"

    # ── 6. comma_density ─────────────────────────────────────────────────────
    # Reuse non_space_tokens (already computed above for contraction_frequency)
    word_count_for_density = total_tokens if total_tokens > 0 else 1
    comma_count = sum(1 for t in doc if t.text == ",")
    commas_per_100 = (comma_count / word_count_for_density) * 100
    if commas_per_100 < 4:
        result["comma_density"] = "light"
    elif commas_per_100 <= 8:
        result["comma_density"] = "moderate"
    else:
        result["comma_density"] = "heavy"

    # ── 7. exclamation_frequency ─────────────────────────────────────────────
    excl_count = sum(1 for t in doc if t.text == "!")
    excl_per_100 = (excl_count / word_count_for_density) * 100
    if excl_count == 0:
        result["exclamation_frequency"] = "never"
    elif excl_per_100 < 0.5:
        result["exclamation_frequency"] = "rare"
    else:
        result["exclamation_frequency"] = "frequent"

    # ── 8. ellipsis_usage ────────────────────────────────────────────────────
    capped_text = text[:50_000]
    result["ellipsis_usage"] = (capped_text.count("...") + capped_text.count("…")) > 1

    # ── 9. parenthetical_usage ───────────────────────────────────────────────
    paren_count = sum(1 for t in doc if t.text == "(")
    if word_count_for_density < 10:
        # Too few words to produce a meaningful signal; avoid spurious "frequent" from
        # the zero-guard (word_count_for_density=1 makes words_per_1000=0.001, so a
        # single "(" would yield parens_per_1000=1000).
        result["parenthetical_usage"] = "rare"
    else:
        words_per_1000 = word_count_for_density / 1000
        parens_per_1000 = paren_count / words_per_1000
        if parens_per_1000 < 1:
            result["parenthetical_usage"] = "rare"
        elif parens_per_1000 <= 3:
            result["parenthetical_usage"] = "occasional"
        else:
            result["parenthetical_usage"] = "frequent"

    # ── 10. sentence_length_stdev ─────────────────────────────────────────────
    if len(lengths) >= 2:
        result["sentence_length_stdev"] = round(statistics.stdev(lengths))
    else:
        result["sentence_length_stdev"] = 0

    # ── 11. low_confidence flag ───────────────────────────────────────────────
    if textstat.lexicon_count(text[:50_000], removepunct=True) < 300:
        result["low_confidence"] = True

    return result
