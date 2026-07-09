"""Stub missing optional dependencies so unit tests run without full install."""
import sys
from unittest.mock import MagicMock

for _mod in ("resend", "sentry_sdk", "stripe", "replicate", "psycopg2"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# Stub app.scheduler.scheduler so importing it doesn't require a live
# PostgreSQL connection (APScheduler's SQLAlchemyJobStore needs psycopg2).
import types as _types

_scheduler_mod = _types.ModuleType("app.scheduler.scheduler")
_scheduler_mod.scheduler = MagicMock()
sys.modules["app.scheduler.scheduler"] = _scheduler_mod

# Also stub the jobstores module so direct imports don't fail.
_sqlalchemy_js = _types.ModuleType("apscheduler.jobstores.sqlalchemy")
_sqlalchemy_js.SQLAlchemyJobStore = MagicMock
sys.modules.setdefault("apscheduler.jobstores.sqlalchemy", _sqlalchemy_js)

# Stub google SDK modules so integrations/gemini.py is importable without a
# real API key or network access during test runs.
import types as _types

if "google" not in sys.modules:
    google_pkg = _types.ModuleType("google")
    google_pkg.__path__ = []  # make it a namespace package
    sys.modules["google"] = google_pkg

if "google.generativeai" not in sys.modules:
    sys.modules["google.generativeai"] = MagicMock()

# Stub the new google-genai SDK (google.genai) used by integrations/gemini.py.
# Without this, 'from google import genai' fails when google.genai hasn't been
# imported before conftest creates the fake google package.
if "google.genai" not in sys.modules:
    _genai_stub = MagicMock()
    sys.modules["google.genai"] = _genai_stub
    # Expose as attribute so 'from google import genai' resolves correctly.
    sys.modules["google"].genai = _genai_stub  # type: ignore[attr-defined]

if "google.genai.types" not in sys.modules:
    sys.modules["google.genai.types"] = MagicMock()

# Pre-import the real gemini module now that google.genai is stubbed.
# Some test files use sys.modules.setdefault("app.integrations.gemini", MagicMock())
# to stub heavy transitive deps; pre-importing here ensures the real module wins
# and those setdefault calls become no-ops.
import importlib as _importlib
_importlib.import_module("app.integrations.gemini")
_importlib.import_module("app.services.generation")
