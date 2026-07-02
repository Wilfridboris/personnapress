"""Stub missing optional dependencies so unit tests run without full install."""
import sys
from unittest.mock import MagicMock

for _mod in ("resend", "sentry_sdk", "stripe", "replicate"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# Stub google.generativeai so the module-level genai.configure() call in
# integrations/gemini.py does not require a real API key during test runs.
import types as _types

if "google" not in sys.modules:
    google_pkg = _types.ModuleType("google")
    google_pkg.__path__ = []  # make it a namespace package
    sys.modules["google"] = google_pkg

if "google.generativeai" not in sys.modules:
    sys.modules["google.generativeai"] = MagicMock()
