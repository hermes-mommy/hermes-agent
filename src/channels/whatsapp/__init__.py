"""WhatsApp channel integration package for P11."""

from .adapter import WhatsAppIngressEgressAdapter
from .bridge import (
    HermesBridgeError,
    HermesInternalError,
    HermesResult,
    HermesSafetyRefusal,
    HermesTimeout,
    HermesToolFailure,
    HermesUnavailable,
    WhatsAppHermesBridge,
)
from .consent_manager import ConsentDecision, ConsentState, WhatsAppConsentManager
from .envelope import WhatsAppDeliveryEnvelope, WhatsAppMessageEnvelope
from .formatter import ChunkingConfig, WhatsAppFormatter
from .hard_stop import HardStopDecision, WhatsAppHardStopGate, get_shared_hard_stop_handler
from .ops_commands import OpsCommandResult, WhatsAppOpsCommandHandler
from .policy import PolicyDecision, WhatsAppPolicyGate
from .presence import TypingIndicator
from .rate_limiter import DedupDecision, RateLimitDecision, WhatsAppRateLimiter
from .router import RouterDecision, WhatsAppRouter
from .whitelist import WhitelistDecision, WhitelistManager

__all__ = [
    "ChunkingConfig",
    "ConsentDecision",
    "ConsentState",
    "DedupDecision",
    "HardStopDecision",
    "HermesBridgeError",
    "HermesInternalError",
    "HermesResult",
    "HermesSafetyRefusal",
    "HermesTimeout",
    "HermesToolFailure",
    "HermesUnavailable",
    "OpsCommandResult",
    "PolicyDecision",
    "RateLimitDecision",
    "RouterDecision",
    "TypingIndicator",
    "WhatsAppConsentManager",
    "WhatsAppDeliveryEnvelope",
    "WhatsAppFormatter",
    "WhatsAppHardStopGate",
    "WhatsAppHermesBridge",
    "WhatsAppIngressEgressAdapter",
    "WhatsAppMessageEnvelope",
    "WhatsAppOpsCommandHandler",
    "WhatsAppPolicyGate",
    "WhatsAppRateLimiter",
    "WhatsAppRouter",
    "WhitelistDecision",
    "WhitelistManager",
    "get_shared_hard_stop_handler",
]
