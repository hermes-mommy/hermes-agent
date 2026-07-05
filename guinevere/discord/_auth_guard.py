"""Auth guard for Discord interactions — Faiz-only gate.

Extracted from ``guinevere.discord.commands`` (deprecated) into an independent
non-deprecated module so that the 32 command callback modules can import
it without referencing the deprecated ``commands.py`` module.
"""

from __future__ import annotations


def is_faiz_interaction(interaction: object) -> bool:
    """Fail closed unless the interaction user is the Discord guild owner.

    P2-010 must not hardcode Faiz's user ID. Discord already exposes the guild
    owner at runtime, and previous P2 steps discover the same owner ID via REST.
    """

    guild = getattr(interaction, "guild", None)
    user = getattr(interaction, "user", None)
    owner_id = getattr(guild, "owner_id", None)
    user_id = getattr(user, "id", None)
    return isinstance(owner_id, int) and isinstance(user_id, int) and owner_id == user_id
