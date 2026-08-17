"""Patch the slowapi limiter to be a no-op pass-through for router unit tests."""
import sys
from unittest.mock import MagicMock


def _noop_limit(*args, **kwargs):
    """Return a decorator that leaves the function unchanged."""
    def _decorator(func):
        return func
    return _decorator


# Build a minimal Limiter stub that produces pass-through decorators.
_limiter_stub = MagicMock()
_limiter_stub.limit = _noop_limit

_slowapi_stub = MagicMock()
_slowapi_stub.Limiter = MagicMock(return_value=_limiter_stub)

_slowapi_util_stub = MagicMock()
_slowapi_util_stub.get_remote_address = MagicMock(return_value="127.0.0.1")

_slowapi_errors_stub = MagicMock()
_slowapi_middleware_stub = MagicMock()

for _mod, _obj in [
    ("slowapi", _slowapi_stub),
    ("slowapi.util", _slowapi_util_stub),
    ("slowapi.errors", _slowapi_errors_stub),
    ("slowapi.middleware", _slowapi_middleware_stub),
]:
    sys.modules[_mod] = _obj
