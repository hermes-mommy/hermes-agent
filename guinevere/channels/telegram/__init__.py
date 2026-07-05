"""Telegram channel adapter — httpx Bot API client (rewrite).

Synthesized from guinevere/life_integrations/adapters/telegram_adapter.py +
Hermes gateway/platforms/telegram.py patterns. Uses httpx for the Bot
API (token embedded in URL path).  Supports send/edit/delete/get_updates
plus media (photo/document).  Per-chat throttle (1.05s minimum) and
429 retry_after respect.

CONFIG_MISSING markers for sec-telegram-bot-token when not
provisioned (D2 pattern).
"""

from .adapter import TelegramAdapter

__all__ = ["TelegramAdapter"]
