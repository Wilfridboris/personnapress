"""Angle taxonomy for roadmap post variety (Story 20.8).

Single source of truth for angle codes, display labels, and per-platform
preference order used by the week planner and the fallback rotation.
"""

from __future__ import annotations

# Ordered preference list per platform (planner + fallback draw in this order)
_LINKEDIN_ORDER: list[str] = [
    "personal_story",
    "data_proof",
    "how_to",
    "contrarian",
    "lesson_learned",
    "myth_bust",
    "prediction",
    "engagement_q",
]

_X_ORDER: list[str] = [
    "contrarian",
    "data_proof",
    "quick_tip",
    "hot_take",
    "how_to",
    "myth_bust",
    "engagement_q",
]

ANGLE_LABELS: dict[str, str] = {
    "personal_story": "Personal story",
    "lesson_learned": "Lesson learned",
    "how_to": "How-to",
    "data_proof": "Data proof",
    "contrarian": "Contrarian take",
    "myth_bust": "Myth-buster",
    "prediction": "Prediction",
    "engagement_q": "Question",
    "quick_tip": "Quick tip",
    "hot_take": "Hot take",
}

KNOWN_CODES: frozenset[str] = frozenset(ANGLE_LABELS)

_PLATFORM_ORDER: dict[str, list[str]] = {
    "linkedin": _LINKEDIN_ORDER,
    "x": _X_ORDER,
}


def fallback_angles(platform: str, count: int) -> list[str]:
    """Return `count` angle codes for `platform` drawn in preference order, cycling.

    Blog slots should never call this (they have no angle). Unknown platforms
    fall back to the X order. Cycles through the pool once exhausted.
    """
    if count <= 0:
        return []
    pool = _PLATFORM_ORDER.get(platform, _X_ORDER)
    return [pool[i % len(pool)] for i in range(count)]
