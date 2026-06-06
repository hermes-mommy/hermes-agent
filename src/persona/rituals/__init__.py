"""Persona Rituals — mood-aware scheduled greeting modules.

.. deprecated:: Phase 5
    The entire ``rituals`` package is **deprecated** in favour of Hermes cron
    (``~/.hermes/crontab.yaml``) and PersonaPlugin
    (``src/hermes/plugins/persona_plugin.py``).  Ritual greeting templates have
    been ported to SOUL.md §H/§J.  Modules remain importable for backward
    compatibility.  Scheduled removal: Phase 7.
"""

import warnings

warnings.warn(
    "rituals/ package is deprecated in Phase 5. Use Hermes cron + PersonaPlugin instead. Scheduled removal: Phase 7.",
    DeprecationWarning,
    stacklevel=2,
)

from src.persona.rituals.morning import (
    DND_END_HOUR,
    DND_START_HOUR,
    MorningRitual,
    RitualResult,
    TZ_JAKARTA,
)

__all__ = [
    "MorningRitual",
    "RitualResult",
    "TZ_JAKARTA",
    "DND_START_HOUR",
    "DND_END_HOUR",
]
