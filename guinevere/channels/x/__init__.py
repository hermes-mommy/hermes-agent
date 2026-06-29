"""X/Twitter channel adapter — X API v2 OAuth 2.0 client.

Port of src/x_poster/ (26 files, ~5201 lines) condensed into a single
adapter module. Preserves: X API v2 client with OAuth 2.0 Bearer + auto-refresh,
poster, circuit breaker, queue manager, retry engine, and media upload.  Strips:
safety/governance (not applicable).

CONFIG_MISSING markers for x_access_token / x_refresh_token / x_client_id
when not provisioned (D2 pattern).
"""

from .adapter import XAdapter

__all__ = ["XAdapter"]
