"""Consent management module for Guinevere.

Provides centralized consent state management and revocation coordination
across persona, surveillance, and tool-call consumers.
"""

from guinevere.consent.revocation_handler import (
    ConsentRevocationHandler,
    ConsentState,
    get_consent_handler,
)

__all__ = [
    "ConsentRevocationHandler",
    "ConsentState",
    "get_consent_handler",
]
