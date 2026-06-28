"""Stub missing optional dependencies so unit tests run without full install."""
import sys
from types import ModuleType
from unittest.mock import MagicMock

for _mod in ("resend",):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()
