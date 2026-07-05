"""Decision context builder for the Living Autonomy Kernel.

Combines P16 Knowledge Graph signals and P18 Memory signals into a single
enriched decision context dictionary.  The builder is intentionally passive:
it returns a context dict for ``observe_node`` (or any other graph node) to
merge into ``LifeMindState.decision_context``; it does not mutate state itself.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

from guinevere.life_kernel.p16_adapter import KGRecallAdapter
from guinevere.life_kernel.p18_adapter import MemoryRecallAdapter
from guinevere.life_kernel.state import LifeMindState

logger = structlog.get_logger(__name__)


class DecisionContextBuilder:
    """Build an enriched decision context from KG and Memory recall signals.

    Attributes:
        kg_adapter: Adapter used to recall Knowledge Graph concepts.  If
            ``None``, a default :class:`KGRecallAdapter` is created.
        memory_adapter: Adapter used to recall past memories.  If ``None``, a
            default :class:`MemoryRecallAdapter` is created.
    """

    def __init__(
        self,
        kg_adapter: KGRecallAdapter | None = None,
        memory_adapter: MemoryRecallAdapter | None = None,
    ) -> None:
        """Initialize the builder with optional adapters.

        Args:
            kg_adapter: Optional KG recall adapter.
            memory_adapter: Optional memory recall adapter.
        """
        self.kg_adapter = kg_adapter or KGRecallAdapter()
        self.memory_adapter = memory_adapter or MemoryRecallAdapter()

    async def build(self, state: LifeMindState) -> dict[str, Any]:
        """Return an enriched decision context for the supplied state.

        The method reads the latest observation (if any) from the state's
        ``observations`` list and uses it as the recall seed.  Both adapters are
        invoked concurrently.

        Args:
            state: Current life-mind state.  Read-only; never modified.

        Returns:
            Dict with keys ``kg_concepts``, ``memory_signals``,
            ``enriched_context`` and ``source_timestamp``.
        """
        observations = state.get("observations", [])
        latest_observation = observations[0] if observations else {}
        seed_context: dict[str, Any]
        if isinstance(latest_observation, dict):
            seed_context = latest_observation
        else:
            seed_context = {"raw": latest_observation}

        kg_result = await self.kg_adapter.recall(seed_context)
        memory_result = await self.memory_adapter.recall(seed_context)

        kg_concepts = kg_result.get("concepts", [])
        memory_signals = memory_result.get("memories", [])

        enriched_context = {
            "seed": seed_context,
            "kg_summary": {
                "top_concepts": [c.get("name") for c in kg_concepts],
                "count": len(kg_concepts),
            },
            "memory_summary": {
                "top_memories": [m.get("content") for m in memory_signals],
                "count": len(memory_signals),
            },
        }

        logger.debug(
            "decision_context_built",
            kg_count=len(kg_concepts),
            memory_count=len(memory_signals),
            seed_keys=list(seed_context.keys()),
        )

        return {
            "kg_concepts": kg_concepts,
            "memory_signals": memory_signals,
            "enriched_context": enriched_context,
            "source_timestamp": datetime.now().isoformat(),
        }
