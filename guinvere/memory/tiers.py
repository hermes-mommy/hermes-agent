"""Memory tier management for P18 Advanced Memory."""
from enum import Enum
from datetime import datetime, timedelta


class MemoryTier(str, Enum):
    WORKING = "working"      # Short-term, high-access
    EPISODIC = "episodic"    # Medium-term, event-based
    SEMANTIC = "semantic"    # Long-term, distilled facts


TIER_DECAY_RATES = {
    MemoryTier.WORKING: 0.3,    # 30% per day
    MemoryTier.EPISODIC: 0.05,  # 5% per day
    MemoryTier.SEMANTIC: 0.01,  # 1% per day
}


class TierManager:
    """Manages memory tier transitions and tier-aware operations."""

    @staticmethod
    def should_promote(episode, current_tier: MemoryTier) -> MemoryTier | None:
        """Determine if episode should be promoted to next tier."""
        if current_tier == MemoryTier.WORKING:
            # Promote to episodic if importance >= 7 and age > 7 days
            if episode.importance and episode.importance >= 7:
                if episode.started_at < datetime.now() - timedelta(days=7):
                    return MemoryTier.EPISODIC
        elif current_tier == MemoryTier.EPISODIC:
            # Promote to semantic if verified_count >= 3
            if hasattr(episode, 'verified_count') and episode.verified_count and episode.verified_count >= 3:
                return MemoryTier.SEMANTIC
        return None

    @staticmethod
    def get_tier_decay_rate(tier: str | MemoryTier) -> float:
        """Get decay rate for tier (higher = faster decay)."""
        if isinstance(tier, str):
            tier = MemoryTier(tier.lower())
        return TIER_DECAY_RATES.get(tier, 0.05)
