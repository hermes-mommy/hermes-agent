"""WhatsApp channel adapter — Neonize-based WhatsApp Web client.

Port of src/channels/whatsapp/ (22 files, ~3368 lines) condensed into
a single adapter module. Safety modules moved to governance.
consent/ops command handlers.  CONFIG_MISSING when WHATSAPP_PHONE_NUMBER
or Redis is not provisioned.
"""

from .adapter import WhatsAppAdapter

__all__ = ["WhatsAppAdapter"]
