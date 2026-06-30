"""Gmail channel integration package for P12.

This package provides the foundational DTO layer for the Gmail integration
within the Guinevere autonomous AI companion system.  It defines:

- **Email taxonomy** (categories, priorities, action mappings) for classifying
  inbound email at the transport boundary.
- **Inbound envelope** (``GmailMessageEnvelope``) — the narrow normalized shape
  consumed by classifier, policy, and routing stages.
- **Outbound envelope** (``GmailDeliveryEnvelope``) — the normalized payload
  used by reply-draft and notification stages to construct Gmail API requests.

Adapters, bridges, and policy gates will be added in later implementation waves.
"""

from .categories import (
    CATEGORY_ACTIONS,
    CATEGORY_PRIORITY,
    EmailCategory,
    EmailPriority,
)
from .envelope import GmailDeliveryEnvelope, GmailMessageEnvelope

__all__ = [
    "CATEGORY_ACTIONS",
    "CATEGORY_PRIORITY",
    "EmailCategory",
    "EmailPriority",
    "GmailDeliveryEnvelope",
    "GmailMessageEnvelope",
]
