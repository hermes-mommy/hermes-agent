"""Guinevere Discord Gateway — Condensed port of src/discord/ (62 files).

Provides 41 slash commands, 3 bot identities, and all infrastructure
needed for the Guinevere Discord gateway. Stale imports from deleted
former persona, loops, and surveillance gating imports have been
cleaned and replaced with guinevere.* equivalents.

D2 compliance: no live Discord tokens; command registration and bot
identity testing only.

Usage::

    from guinevere.discord import GuinevereBot, CommandRegistry
    from guinevere.discord.commands import COMMAND_SPECS
    from guinevere.discord.bots import BOT_IDENTITIES
"""

from guinevere.discord.bots import GuinevereBot, BOT_IDENTITIES, create_bot
from guinevere.discord.commands import CommandRegistry, COMMAND_SPECS

__all__ = [
    "GuinevereBot",
    "CommandRegistry",
    "COMMAND_SPECS",
    "BOT_IDENTITIES",
    "create_bot",
]
