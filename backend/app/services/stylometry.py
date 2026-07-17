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

    # ── 5. low_confidence flag ────────────────────────────────────────────────
    if textstat.lexicon_count(text[:50_000], removepunct=True) < 300:
        result["low_confidence"] = True

    return result
