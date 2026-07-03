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

# Stub google.generativeai so the module-level genai.configure() call in
# integrations/gemini.py does not require a real API key during test runs.
import types as _types

if "google" not in sys.modules:
    google_pkg = _types.ModuleType("google")
    google_pkg.__path__ = []  # make it a namespace package
    sys.modules["google"] = google_pkg

if "google.generativeai" not in sys.modules:
    sys.modules["google.generativeai"] = MagicMock()
