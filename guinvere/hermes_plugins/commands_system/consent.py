"""Hermes command plugin — /consent. Show or update consent boundaries.

Reads and writes consent grants from Redis DB0 key ``consent:grants``
as a JSON set. Requires explicit Faiz action for grant/revoke.

SAFETY: No consent change without explicit operator action.
Surveillance consent requires explicit grant — never auto-granted.

Usage:
    /consent [action: view|grant|revoke] [category: str]
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis

logger = logging.getLogger(__name__)

VALID_ACTIONS: frozenset[str] = frozenset({"view", "grant", "revoke"})
DEFAULT_ACTION: str = "view"

REDIS_HOST: str = "localhost"
REDIS_PORT: int = 6380
REDIS_DB: int = 0
REDIS_KEY: str = "consent:grants"


def _redis() -> redis.Redis:
    """Return a Redis client for DB0 (consent state)."""
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)


def _get_grants(r: redis.Redis) -> set[str]:
    """Read current consent grants from Redis."""
    raw = r.get(REDIS_KEY)
    if raw is None:
        return set()
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return set(data)
        return set()
    except (json.JSONDecodeError, TypeError):
        return set()


def _save_grants(r: redis.Redis, grants: set[str]) -> None:
    """Persist consent grants to Redis."""
    r.set(REDIS_KEY, json.dumps(sorted(grants)))


def register(ctx: Any) -> None:
    """Register the /consent command with Hermes."""

    @ctx.register_command("consent", description="Show or update consent boundaries.")
    async def handle(context: Any) -> str:
        try:
            args: list[str] = getattr(context, "args", [])
            action = args[0] if args and args[0] in VALID_ACTIONS else DEFAULT_ACTION

            r = _redis()
            grants = _get_grants(r)

            if action == "view":
                grants_list = sorted(grants) if grants else ["(none)"]
                grant_lines = "\n".join(f"• {g}" for g in grants_list)

                return (
                    "# 🔒 Consent Manager\n\n"
                    "Ini consent grants saat ini, Darling.\n\n"
                    "---\n\n"
                    f"## 📋 Current Grants\n\n"
                    f"{grant_lines}\n\n"
                    "---\n\n"
                    f"🛡️ Safety • {len(grants)} grants active\n"
                )

            if len(args) < 2:
                return f"⚠️ Parameter `category` diperlukan untuk {action}, Darling."

            category = args[1]

            if action == "grant":
                grants.add(category)
                _save_grants(r, grants)
                logger.info("consent_granted", extra={"category": category})

                return (
                    "# 🔒 Consent Manager\n\n"
                    f"Consent `{category}` sudah di-grant, Darling.\n\n"
                    "---\n\n"
                    f"| Field | Value |\n|---|---|\n"
                    f"| 📋 Category | `{category}` |\n"
                    f"| ✅ Status | Granted |\n"
                )

            if action == "revoke":
                grants.discard(category)
                _save_grants(r, grants)
                logger.info("consent_revoked", extra={"category": category})

                return (
                    "# 🔒 Consent Manager\n\n"
                    f"Consent `{category}` sudah di-revoke, Darling.\n\n"
                    "---\n\n"
                    f"| Field | Value |\n|---|---|\n"
                    f"| 📋 Category | `{category}` |\n"
                    f"| ❌ Status | Revoked |\n"
                )

            return "# 🔒 Consent Manager\n\nAction tidak dikenali, Darling."

        except Exception:
            logger.exception("consent_command_failed")
            return "⚠️ Consent manager is temporarily unavailable."


__all__ = ["register"]