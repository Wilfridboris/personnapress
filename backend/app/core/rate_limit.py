from slowapi import Limiter
from slowapi.util import get_remote_address

# Default covers all routes; sensitive auth endpoints override this with explicit decorators.
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
