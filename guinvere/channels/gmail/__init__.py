"""Gmail channel adapter — OAuth2-based email integration.

Port of guinvere/gmail/ (36 files, ~12723 lines) condensed into a single
adapter module. Preserves: OAuth2 token management, Gmail API client
with quota tracking, sync engine, draft pipeline, email classification
taxonomy, and envelope DTOs.  Safety modules moved to governance.

CONFIG_MISSING markers for GmailSettings (credentials, client_id, etc.)
when not provisioned (D2 pattern).
"""

from .adapter import GmailAdapter

__all__ = ["GmailAdapter"]
