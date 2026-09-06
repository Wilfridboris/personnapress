"""Canonical platform character limits for PersonnaPress.

This is the single source of truth for all platform hard limits and target ranges.
All code that needs a platform character limit reads from this module only.

NOTE: X (Twitter) URL weighting is partial -- URLs count as 23 chars, but
emoji weighting and Unicode range weighting are NOT implemented per story 26.1 spec.
Full twitter-text weighting is out of scope.
"""

import re

# Hard limits enforced at generation, approval, and publish time.
# These are the actual platform API limits.
HARD_LIMITS: dict[str, int] = {
    "x": 280,
    "linkedin": 3000,
    "instagram": 2200,
    "facebook_page": 63206,
    "threads": 500,
}

# Target ranges used only in prompt guidance (not enforced).
# These remain stricter than hard limits to produce better content.
TARGET_RANGES: dict[str, tuple[int, int]] = {
    "x": (70, 280),
    "linkedin_linked": (300, 1300),   # blog-linked posts
    "linkedin_standalone": (1200, 2500),  # standalone posts (Plan My Week)
    "instagram": (150, 600),
    "facebook_page": (200, 800),
    "threads": (0, 500),
}

# Regex for URL detection matching X's t.co wrapping behavior.
# Same pattern used by the onboarding link detector.
_URL_PATTERN = re.compile(r"https?://[^\s]+")

# X counts every URL as 23 characters regardless of actual length.
_X_URL_WEIGHT = 23


def count_chars(platform: str, text: str) -> int:
    """Return the character count for a platform post.

    For X, URLs are replaced by a 23-char token before counting
    (matching X's weighted count behavior for URLs).
    For all other platforms, returns the Unicode code point count.

    NOTE: This implements URL weighting only. Emoji weighting and
    Unicode range weighting are not implemented (out of scope per story 26.1).
    """
    if not text:
        return 0
    if platform == "x":
        weighted = _URL_PATTERN.sub("x" * _X_URL_WEIGHT, text)
        return len(weighted)
    return len(text)


def over_limit(platform: str, text: str) -> int:
    """Return how many characters the text exceeds the hard limit.

    Returns 0 if within or at the limit.
    Returns a positive integer indicating overage if over the limit.
    """
    limit = HARD_LIMITS.get(platform)
    if limit is None:
        return 0
    count = count_chars(platform, text)
    return max(0, count - limit)


def sentence_boundary_truncate(text: str, limit: int, platform: str | None = None) -> str:
    """Truncate text at the last sentence boundary at or below limit.

    Splits on '.', '!', '?', or newline. Takes the longest prefix
    that fits within the limit. Never cuts mid-word. No ellipsis appended.
    If no sentence boundary found, truncates at the last word boundary.

    When platform is provided, the final result is re-checked with
    over_limit(platform, result) to account for weighted character counting
    (e.g. X URL weighting). If still over, trims further to the last word
    boundary within the weighted limit.
    """
    if len(text) <= limit:
        return text

    prefix = text[:limit]
    # Find the last sentence-ending punctuation in the prefix
    last_boundary = -1
    for i in range(len(prefix) - 1, -1, -1):
        if prefix[i] in ".!?\n":
            last_boundary = i
            break

    if last_boundary > 0:
        result = text[:last_boundary + 1].rstrip()
    else:
        # Fall back to last word boundary
        last_space = prefix.rfind(" ")
        if last_space > 0:
            result = text[:last_space].rstrip()
        else:
            result = prefix

    # Re-check with weighted counting when platform is provided
    if platform is not None and over_limit(platform, result) > 0:
        # Trim further: walk back from current result's length
        trimmed = result
        for i in range(len(result) - 1, -1, -1):
            if result[i] in " \t\n.!?":
                candidate = result[:i].rstrip()
                if over_limit(platform, candidate) == 0:
                    return candidate
        # No boundary found; return as-is (edge case)
        return trimmed

    return result
