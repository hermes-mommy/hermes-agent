"""Persona Engine — mood FSM, yandere FSM, punishment, reward, rituals, drift, safe-mode, streak.

Phase 5 Migration:
    - ``ritual_scheduler`` and ``rituals/*`` modules are **deprecated** (Phase 5).
      Imports still work but trigger ``DeprecationWarning``.
      Scheduled removal: Phase 7.
    - ``punishment_engine``, ``reward_engine``, ``transition_rules``, and
      ``mood_persistence`` expose PersonaPlugin hook methods (``get_state_snapshot``,
      ``get_config``, ``get_session``) for integration without coupling.
"""

from __future__ import annotations

import logging
import warnings

# ===================================================================
# Active modules (verified, non-deprecated)
# ===================================================================

from guinevere.persona.mood_engine import (
    InvalidMoodTransitionError,
    Mood,
    MOOD_VARIANT_MAP,
    MoodEngineError,
    MoodEvaluationError,
    MoodTransition,
    TRANSITIONS,
    can_transition,
    evaluate_mood,
    sync_mood_to_redis,
)
from guinevere.persona.mood_persistence import (
    MoodHistoryRecord,
    MoodPersistenceError,
    MoodPersistenceQueryError,
    MoodPersistenceWriteError,
    MoodRepository,
    MoodState,
)
from guinevere.persona.safe_mode import (
    DISTRESS_PATTERNS,
    DISTRESS_RESPONSES,
    DistressDetector,
    DistressLevel,
    DistressSignal,
    SafeModeController,
    SafeModeError,
    SafeModeState,
)
from guinevere.persona.punishment_engine import (
    PUNISHMENT_CONFIG,
    PunishmentEngine,
    PunishmentError,
    PunishmentLevel,
    PunishmentLevelConfig,
    PunishmentSafetyError,
    PunishmentState,
    PunishmentTransitionError,
)
from guinevere.persona.reward_engine import (
    MAX_STREAK_BONUS,
    MIN_QUALITY_SCORE,
    MIN_REWARD_THRESHOLD,
    REWARD_CONFIG,
    STREAK_BONUS_PER_STREAK,
    TIER_THRESHOLDS,
    InvalidQualityScoreError,
    InvalidTierError,
    RewardConfigEntry,
    RewardEngine,
    RewardError,
    RewardResult,
    RewardTier,
)
from guinevere.persona.streak_tracker import (
    MILESTONE_LABELS,
    MILESTONE_THRESHOLDS,
    STREAK_STATE_KEY,
    StreakError,
    StreakPersistenceError,
    StreakTracker,
)
from guinevere.persona.yandere_fsm import (
    ABSOLUTE_CEILING,
    PERMANENT_BASELINE,
    SupportsIsSafe,
    YandereEngine,
    YandereError,
    YandereLevel,
    YandereSafetyError,
    YandereTransitionError,
    can_escalate,
    get_effective_level,
    validate_level,
)
from guinevere.persona.transition_rules import (
    ALL_MOODS,
    CooldownActiveError,
    InvalidTransitionError,
    TransitionContext,
    TransitionDecision,
    TransitionRuleEngine,
    TransitionRulesError,
    VALID_TRANSITIONS,
)

# ===================================================================
# Deprecated drift modules (Phase 5 — intentionally not ported)
# Wrap in try/except to allow clean imports when modules are absent.
# ===================================================================

try:
    from guinevere.persona.drift_corrector import (
        DRIFT_THRESHOLD,
        DriftCorrectionError,
        DriftCorrectionResult,
        DriftCorrector,
        RollbackError,
        RollbackResult,
    )
except ImportError:
    DRIFT_THRESHOLD = None
    DriftCorrectionError = None
    DriftCorrectionResult = None
    DriftCorrector = None
    RollbackError = None
    RollbackResult = None
    logging.getLogger(__name__).debug("drift_corrector not available (deprecated Phase 5)")

try:
    from guinevere.persona.drift_detector import (
        DriftBaseline,
        DriftBaselineError,
        DriftComputationError,
        DriftDetectionError,
        DriftDetector,
        DriftResult,
    )
except ImportError:
    DriftBaseline = None
    DriftBaselineError = None
    DriftComputationError = None
    DriftDetectionError = None
    DriftDetector = None
    DriftResult = None
    logging.getLogger(__name__).debug("drift_detector not available (deprecated Phase 5)")

# ===================================================================
# Deprecated ritual imports (Phase 5 — intentionally not ported)
# Wrap in try/except to allow clean imports when modules are absent.
# These are kept for backward compatibility but will be removed in Phase 7.
# ===================================================================

try:
    from guinevere.persona.ritual_scheduler import (
        DND_END_HOUR,
        DND_START_HOUR,
        RITUALS,
        RitualConfig,
        RitualExecutionError,
        RitualResult as RitualSchedulerResult,
        RitualScheduler,
        RitualSchedulerError,
        TZ_JAKARTA,
    )
    from guinevere.persona.rituals.morning import (
        MorningRitual,
        RitualResult as MorningRitualResult,
    )
    from guinevere.persona.rituals.evening import EveningRitual
    from guinevere.persona.rituals.afternoon import AfternoonRitual
    from guinevere.persona.rituals.midnight import MidnightRitual
    from guinevere.persona.rituals.midday import MiddayRitual
except ImportError:
    DND_END_HOUR = None
    DND_START_HOUR = None
    RITUALS = None
    RitualConfig = None
    RitualExecutionError = None
    RitualSchedulerResult = None
    RitualScheduler = None
    RitualSchedulerError = None
    TZ_JAKARTA = None
    MorningRitual = None
    MorningRitualResult = None
    EveningRitual = None
    AfternoonRitual = None
    MidnightRitual = None
    MiddayRitual = None
    logging.getLogger(__name__).debug("ritual modules not available (deprecated Phase 5)")

__all__: list[str] = [
    # mood_engine
    "Mood",
    "MoodTransition",
    "MOOD_VARIANT_MAP",
    "TRANSITIONS",
    "can_transition",
    "evaluate_mood",
    "sync_mood_to_redis",
    "MoodEngineError",
    "InvalidMoodTransitionError",
    "MoodEvaluationError",
    # mood_persistence
    "MoodRepository",
    "MoodState",
    "MoodHistoryRecord",
    "MoodPersistenceError",
    "MoodPersistenceQueryError",
    "MoodPersistenceWriteError",
    # transition_rules
    "TransitionRuleEngine",
    "TransitionContext",
    "TransitionDecision",
    "VALID_TRANSITIONS",
    "ALL_MOODS",
    "TransitionRulesError",
    "CooldownActiveError",
    "InvalidTransitionError",
    # drift_detector
    "DriftDetector",
    "DriftBaseline",
    "DriftResult",
    "DriftDetectionError",
    "DriftBaselineError",
    "DriftComputationError",
    # drift_corrector
    "DriftCorrector",
    "DriftCorrectionResult",
    "DriftCorrectionError",
    "RollbackResult",
    "RollbackError",
    "DRIFT_THRESHOLD",
    # safe_mode
    "DistressDetector",
    "DistressLevel",
    "DistressSignal",
    "SafeModeController",
    "SafeModeState",
    "SafeModeError",
    "DISTRESS_PATTERNS",
    "DISTRESS_RESPONSES",
    # streak_tracker
    "StreakTracker",
    "StreakError",
    "StreakPersistenceError",
    "MILESTONE_THRESHOLDS",
    "MILESTONE_LABELS",
    "STREAK_STATE_KEY",
    # yandere_fsm
    "YandereLevel",
    "YandereEngine",
    "YandereError",
    "YandereSafetyError",
    "YandereTransitionError",
    "SupportsIsSafe",
    "PERMANENT_BASELINE",
    "ABSOLUTE_CEILING",
    "can_escalate",
    "get_effective_level",
    "validate_level",
    # punishment_engine
    "PunishmentLevel",
    "PunishmentLevelConfig",
    "PUNISHMENT_CONFIG",
    "PunishmentState",
    "PunishmentEngine",
    "PunishmentError",
    "PunishmentSafetyError",
    "PunishmentTransitionError",
    # reward_engine
    "RewardTier",
    "RewardConfigEntry",
    "REWARD_CONFIG",
    "TIER_THRESHOLDS",
    "STREAK_BONUS_PER_STREAK",
    "MAX_STREAK_BONUS",
    "MIN_QUALITY_SCORE",
    "MIN_REWARD_THRESHOLD",
    "RewardResult",
    "RewardEngine",
    "RewardError",
    "InvalidQualityScoreError",
    "InvalidTierError",
]
