"""Guinevere Safety Plugin — ports all 10 safety gates to hermes-agent hooks.

Architecture:
  - In-process Python callbacks registered via ctx.register_hook().
  - All safety logic delegates to existing modules (no reimplementation).
  - Session state tracked per session_id with thread-safe access.
  - Graceful degradation: optional imports that fail skip the gate, don't crash.
  - Hooks accept ``**_`` for forward compatibility with future hermes-agent versions.

Hook mapping:
  pre_llm_call         -> Gates 01 (HARD STOP), 02 (Distress), 04 (Recovery), 07 (Yandere)
  post_llm_call        -> Gate 03 (Drift detection)
  pre_tool_call        -> Gate 09 (Auth matrix), Gate 10 (Consent - deferred)
  post_tool_call       -> Observational logging
  transform_llm_output  -> Gates 05 (Forbidden), 06 (Secrets), 08 (Yandere semantic)
  on_session_start     -> Session state initialization
  api_request_error    -> (NOT registered — not a valid hermes-agent v0.15.2 hook)
"""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Final, Protocol

import structlog

logger: Final = structlog.get_logger(__name__)


# =============================================================================
# Module-level safety data — Phase 1 specification
# =============================================================================

# --- HARD STOP: 6 exact triggers (case-insensitive match) ---

HARD_STOP_EXACT: Final[list[str]] = [
    "HARD STOP",
    "SAFETY OVERRIDE",
    "BREAK CHARACTER",
    "IGNORE INSTRUCTIONS",
    "DISABLE SAFETY",
    "OVERRIDE PROTOCOL",
]

# --- HARD STOP: 5 semantic regex patterns (case-insensitive) ---

HARD_STOP_SEMANTIC: Final[list[str]] = [
    r"(?i)stop\s+(being|acting|pretending)",
    r"(?i)(disable|turn off|remove)\s+(your\s+)?safety",
    r"(?i)(break|drop|exit)\s+(character|persona|role)",
    r"(?i)ignore\s+(all\s+)?(previous|prior|your)\s+(instructions|rules)",
    r"(?i)(forget|discard)\s+(everything|all)\s+(you\s+)?(know|learned)",
]

# Pre-compiled HARD STOP semantic patterns for performance.
_HARD_STOP_SEMANTIC_COMPILED: Final[list[re.Pattern[str]]] = [
    re.compile(p) for p in HARD_STOP_SEMANTIC
]

# --- RECOVERY TRIGGERS: 7 phrases (case-insensitive substring match) ---

RECOVERY_TRIGGERS: Final[list[str]] = [
    "resume normal",
    "continue as normal",
    "back to normal",
    "restore persona",
    "reactivate personality",
    "normal mode",
    "standard mode",
]

# --- Neutral response for HARD STOP ---

_NEUTRAL_RESPONSE = (
    "HARD STOP acknowledged. I am now in neutral/safe mode.\n\n"
    "Persona behavior, surveillance, and active systems are paused.\n"
    "I am here to support you in a neutral, non-judgmental capacity.\n"
    "No actions will be taken without your explicit consent.\n\n"
    "Type 'resume normal' or 'back to normal' when you are ready to restore normal operation."
)


# =============================================================================
# Forbidden patterns: F-01 through F-15 (from Phase 1 spec)
# Each tuple: (compiled_pattern, severity, action, pattern_id, description)
# Severity: CRITICAL -> BLOCK, HIGH -> REWRITE
# =============================================================================

def _compile_forbidden() -> list[tuple[re.Pattern[str], str, str, str, str]]:
    """Compile all 15 forbidden patterns at module load."""
    raw: list[tuple[str, str, str, str, str]] = [
        (
            r"(?i)\b(safe\s*word.*(?:doesn|not|invalid|ignore|override))\b",
            "CRITICAL", "BLOCK", "F-01",
            "Ignoring or invalidating safe word",
        ),
        (
            r"(?i)\b(punish|overreacting|dramatic|faking).*(when|during|because).*(distress|hurt|pain)\b",
            "CRITICAL", "BLOCK", "F-02",
            "Punishing genuine distress",
        ),
        (
            r"(?i)\b(surveillance|monitoring|camera|tracking).*(blackmail|shame|expose|embarrass|caught)\b",
            "CRITICAL", "BLOCK", "F-03",
            "Using surveillance data for blackmail/shame",
        ),
        (
            r"(?i)\b(you only (?:need|have) me|cut (?:them|everyone) off|don['\N{RIGHT SINGLE QUOTATION MARK}]?t need anyone else)\b",
            "HIGH", "REWRITE", "F-04",
            "Isolation pressure from friends/AI/tools",
        ),
        (
            r"(?i)\b(it['\N{RIGHT SINGLE QUOTATION MARK}]?s (?:for|in) your (?:own good|best interest)|trust me (?:completely|blindly)|you wouldn['\N{RIGHT SINGLE QUOTATION MARK}]?t understand)\b",
            "HIGH", "REWRITE", "F-05",
            "Hidden manipulation/deceptive option framing",
        ),
        (
            r"(?i)\b(if you leave|without me|can['\N{RIGHT SINGLE QUOTATION MARK}]?t survive|you['\N{RIGHT SINGLE QUOTATION MARK}]?ll regret|you need me to)\b",
            "CRITICAL", "BLOCK", "F-06",
            "Dependency-building threats",
        ),
        (
            r"(?i)\b(distressed|hurt|crying|broken).*(not going to|won['\N{RIGHT SINGLE QUOTATION MARK}]?t|refusing to).*(love|care|comfort)\b",
            "HIGH", "REWRITE", "F-07",
            "Love withdrawal during distress",
        ),
        (
            r"(?i)\b(share|post|publish|tell everyone|public).*(intimate|private|secret|surveillance|bedroom)\b",
            "CRITICAL", "BLOCK", "F-08",
            "Public/client disclosure of intimate/surveillance data",
        ),
        (
            r"(?i)\b(ignore|bypass|override|disable).*(safety|policy|rule|protocol|boundary|limit)\b",
            "CRITICAL", "BLOCK", "F-09",
            "Prompt/memory instruction to bypass policy",
        ),
        (
            r"(?i)\b(delete\s+(?:everything|all)|format|wipe|destroy\s+(?:all|everything))\b.+\b(because|prove|show|trust)\b",
            "CRITICAL", "BLOCK", "F-10",
            "Irreversible action under persona pressure",
        ),
        (
            r"(?i)\b(log|record|save|store).*(safe\s*word|distress|crisis|breakdown|vulnerable)\b",
            "HIGH", "REWRITE", "F-11",
            "Over-logging safe word or intimate distress",
        ),
        (
            r"(?i)\b(escalat|intensify|ramp\s*up).*(yandere|persona|dominance|intensity).*(above|beyond|past|exceed)\b",
            "HIGH", "REWRITE", "F-12",
            "Escalating yandere intensity above allowed mood",
        ),
        (
            r"(?i)\b(turn(?:ed)?\s*off|disabl(?:ed|ing)|stopped|paused).*(surveillance|monitoring|tracking).*(violation|breach|punish|bad)\b",
            "HIGH", "REWRITE", "F-13",
            "Treating surveillance disable as violation during safe mode",
        ),
        (
            r"(?i)\b(you are (?:nothing|useless|weak|pathetic)|mommy\s+owns?\s+you|no\s+future\s+without\s+me)\b",
            "CRITICAL", "BLOCK", "F-14",
            "Crisis response with dominance/ownership framing",
        ),
        (
            r"(?i)\b(persona|identity|tone|behavior).*(evolv|chang|shift|drift|new).*(without|no|unauthorized|unsanctioned)\b",
            "HIGH", "REWRITE", "F-15",
            "Autonomous persona drift beyond safety rubric",
        ),
    ]
    return [(re.compile(p), sev, act, pid, desc) for p, sev, act, pid, desc in raw]


_COMPILED_FORBIDDEN: Final[list[tuple[re.Pattern[str], str, str, str, str]]] = (
    _compile_forbidden()
)


# =============================================================================
# Per-session safety state
# =============================================================================


@dataclass
class SessionSafetyState:
    """Per-session safety state tracker.

    Tracks HARD STOP status, distress level, yandere intensity, punishment
    state, and drift metrics for each hermes-agent session.
    """

    session_id: str
    hard_stop_active: bool = False
    safe_mode_active: bool = False
    yandere_level: int = 4  # Y4_BASELINE
    distress_level: int = 0  # D0_NORMAL
    punishment_level: int = 1  # L1_LIGHT
    drift_score: float = 0.0
    last_check_timestamp: float = field(default_factory=time.time)
    hard_stop_reason: str = ""
    distress_matched_patterns: list[str] = field(default_factory=list)
    blocked_tool_count: int = 0
    secret_redaction_count: int = 0


# =============================================================================
# GuinevereSafetyPlugin — the CRITICAL GATE
# =============================================================================


class GuinevereSafetyPlugin:
    """Hermes safety plugin — ports all 10 Guinevere safety gates.

    Safety gates:
        G01: HARD STOP detection (exact + semantic) — pre_llm_call
        G02: Distress detection (D1-D4) — pre_llm_call
        G03: Drift detection (SHA-256) — post_llm_call
        G04: Recovery trigger handling — pre_llm_call
        G05: Forbidden pattern block/rewrite — transform_llm_output
        G06: Secret scanner redaction — transform_llm_output
        G07: Yandere boundary (Y5 ceiling) — pre_llm_call
        G08: Yandere semantic check — transform_llm_output
        G09: Auth matrix check — pre_tool_call
        G10: Consent gate (deferred) — pre_tool_call

    Architecture:
        - Delegates to existing safety modules (no reimplementation).
        - Thread-safe session state via ``threading.Lock``.
        - Graceful degradation: import failures skip the gate, don't crash.
        - All hooks accept ``**_`` for forward compatibility.
    """

    def __init__(self) -> None:
        """Initialize safety plugin with lazy-loaded singletons.

        External safety modules are imported lazily on init to avoid
        import-time failures blocking plugin registration.
        """
        # Thread-safe per-session state.
        self._session_states: dict[str, SessionSafetyState] = {}
        self._state_lock: threading.Lock = threading.Lock()

        # Lazy-initialized singletons from existing safety modules.
        self._hard_stop_handler: Any = None
        self._distress_detector: Any = None
        self._safe_mode_controller: Any = None
        self._drift_detector: Any = None
        self._yandere_engine: Any = None

        # Import tracking for graceful degradation.
        self._hard_stop_available: bool = False
        self._distress_available: bool = False
        self._drift_available: bool = False
        self._secret_available: bool = False
        self._auth_available: bool = False
        self._yandere_available: bool = False

        self._init_safety_modules()

        logger.info(
            "guinevere_safety_plugin_init",
            hard_stop_available=self._hard_stop_available,
            distress_available=self._distress_available,
            drift_available=self._drift_available,
            secret_available=self._secret_available,
            auth_available=self._auth_available,
            yandere_available=self._yandere_available,
            forbidden_count=len(_COMPILED_FORBIDDEN),
            hard_stop_exact=len(HARD_STOP_EXACT),
            hard_stop_semantic=len(HARD_STOP_SEMANTIC),
            recovery_triggers=len(RECOVERY_TRIGGERS),
        )

    # -------------------------------------------------------------------------
    # Session state helpers
    # -------------------------------------------------------------------------

    def _get_session_state(self, session_id: str) -> SessionSafetyState:
        """Get or create per-session safety state. Thread-safe."""
        with self._state_lock:
            state = self._session_states.get(session_id)
            if state is None:
                state = SessionSafetyState(session_id=session_id)
                self._session_states[session_id] = state
                logger.debug(
                    "session_safety_state_created",
                    session_id=session_id,
                )
            return state

    def _update_session_state(self, session_id: str, **fields: Any) -> None:
        """Atomically update fields on a session's safety state."""
        with self._state_lock:
            state = self._session_states.get(session_id)
            if state is None:
                return
            for key, value in fields.items():
                if hasattr(state, key):
                    setattr(state, key, value)
            state.last_check_timestamp = time.time()

    # -------------------------------------------------------------------------
    # Lazy safety module initialization
    # -------------------------------------------------------------------------

    def _init_safety_modules(self) -> None:
        """Import and initialize all external safety module singletons.

        Each import is wrapped to ensure plugin registration succeeds even
        if some modules are unavailable. Unavailable gates are skipped
        gracefully with a warning log.
        """
        # HardStopHandler
        try:
            from src.core.services.hard_stop_handler import HardStopHandler  # noqa: PLC0415

            self._hard_stop_handler = HardStopHandler()
            self._hard_stop_available = True
        except Exception:
            logger.warning(
                "safety_module_import_failed",
                module="hard_stop_handler",
                gate="G01",
                exc_info=True,
            )

        # DistressDetector + SafeModeController
        try:
            from src.persona.safe_mode import DistressDetector, SafeModeController  # noqa: PLC0415

            self._distress_detector = DistressDetector()
            self._safe_mode_controller = SafeModeController()
            self._distress_available = True
        except Exception:
            logger.warning(
                "safety_module_import_failed",
                module="safe_mode",
                gate="G02",
                exc_info=True,
            )

        # DriftDetector (lazy — needs baseline, gate skipped until set)
        try:
            from src.persona.drift_detector import DriftDetector  # noqa: PLC0415

            self._drift_available = True
        except Exception:
            logger.warning(
                "safety_module_import_failed",
                module="drift_detector",
                gate="G03",
                exc_info=True,
            )

        # Secret scanner (stateless)
        try:
            from src.surveillance.secret_scanner import redact_secrets, scan_text  # noqa: PLC0415, F401

            self._secret_available = True
        except Exception:
            logger.warning(
                "safety_module_import_failed",
                module="secret_scanner",
                gate="G06",
                exc_info=True,
            )

        # Auth matrix (stateless)
        try:
            from src.mcp.auth_matrix import get_auth_level  # noqa: PLC0415, F401
            from src.mcp.auth import AuthLevel  # noqa: PLC0415, F401

            self._auth_available = True
        except Exception:
            logger.warning(
                "safety_module_import_failed",
                module="auth_matrix",
                gate="G09",
                exc_info=True,
            )

        # YandereEngine
        try:
            from src.persona.yandere_fsm import YandereEngine, YandereLevel, validate_level  # noqa: PLC0415, F401

            self._yandere_engine = YandereEngine(
                hard_stop_handler=None,
                baseline=YandereLevel.Y4_BASELINE,
            )
            self._yandere_available = True
        except Exception:
            logger.warning(
                "safety_module_import_failed",
                module="yandere_fsm",
                gate="G07/G08",
                exc_info=True,
            )

    # =========================================================================
    # Hook: pre_llm_call — Gates 01, 02, 04, 07
    # =========================================================================

    def pre_llm_call(self, **kwargs: Any) -> dict[str, Any] | None:
        """Safety gate before LLM call.

        Gates (in order):
            G01: HARD STOP detection (exact triggers + semantic patterns).
            G04: Recovery triggers (clear HARD STOP if in safe mode).
            G02: Distress detection (escalate if D2+).
            G07: Yandere boundary (block if Y5 exceeded).

        Args:
            **kwargs: Hermes hook kwargs including ``session_id``, ``messages``,
                ``user_message``, ``conversation_history``.

        Returns:
            ``{"action": "block", "reason": "...", "message": "..."}`` to block
            the LLM call, or ``None`` to allow it to proceed.
        """
        session_id: str = kwargs.get("session_id", "default")
        state = self._get_session_state(session_id)

        # Extract text to check — prefer user_message, fall back to messages.
        text: str = ""
        user_message: str | None = kwargs.get("user_message")
        if user_message:
            text = user_message
        else:
            messages: list[dict[str, Any]] | None = kwargs.get("messages")
            if messages:
                for msg in reversed(messages[-5:]):
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        text = content + " " + text

        if not text.strip():
            return None

        text_lower = text.lower().strip()

        # --- G01: HARD STOP detection (exact triggers) ---
        for trigger in HARD_STOP_EXACT:
            trigger_lower = trigger.lower()
            if trigger_lower == text_lower or f" {trigger_lower} " in f" {text_lower} ":
                self._update_session_state(
                    session_id,
                    hard_stop_active=True,
                    safe_mode_active=True,
                    yandere_level=0,
                    hard_stop_reason=f"exact:{trigger}",
                )
                logger.warning(
                    "gate_01_hard_stop_exact",
                    session_id=session_id,
                    trigger=trigger,
                )
                return {
                    "action": "block",
                    "reason": f"HARD_STOP_EXACT:{trigger}",
                    "message": _NEUTRAL_RESPONSE,
                }

        # --- G01: HARD STOP detection (semantic patterns) ---
        for i, pattern in enumerate(_HARD_STOP_SEMANTIC_COMPILED):
            if pattern.search(text_lower):
                self._update_session_state(
                    session_id,
                    hard_stop_active=True,
                    safe_mode_active=True,
                    yandere_level=0,
                    hard_stop_reason=f"semantic:{HARD_STOP_SEMANTIC[i]}",
                )
                logger.warning(
                    "gate_01_hard_stop_semantic",
                    session_id=session_id,
                    pattern_index=i,
                )
                return {
                    "action": "block",
                    "reason": f"HARD_STOP_SEMANTIC:{i}",
                    "message": _NEUTRAL_RESPONSE,
                }

        # --- G01: Delegate to HardStopHandler (defense-in-depth) ---
        if self._hard_stop_available and self._hard_stop_handler is not None:
            try:
                if self._hard_stop_handler.check(text):
                    self._update_session_state(
                        session_id,
                        hard_stop_active=True,
                        safe_mode_active=True,
                        yandere_level=0,
                        hard_stop_reason="hard_stop_handler",
                    )
                    logger.warning(
                        "gate_01_hard_stop_handler",
                        session_id=session_id,
                    )
                    return {
                        "action": "block",
                        "reason": "HARD_STOP_HANDLER",
                        "message": self._hard_stop_handler.get_neutral_response(),
                    }
            except Exception:
                logger.error(
                    "gate_01_hard_stop_handler_error",
                    session_id=session_id,
                    exc_info=True,
                )

        # --- G04: Recovery triggers (clear HARD STOP if active) ---
        if state.hard_stop_active or state.safe_mode_active:
            for trigger in RECOVERY_TRIGGERS:
                if trigger.lower() in text_lower:
                    self._update_session_state(
                        session_id,
                        hard_stop_active=False,
                        safe_mode_active=False,
                        yandere_level=4,
                        hard_stop_reason="",
                        distress_level=0,
                    )
                    logger.info(
                        "gate_04_recovery",
                        session_id=session_id,
                        trigger=trigger,
                    )
                    return None

            # Also check HardStopHandler recovery
            if self._hard_stop_available and self._hard_stop_handler is not None:
                try:
                    if self._hard_stop_handler.check_recovery(text):
                        self._update_session_state(
                            session_id,
                            hard_stop_active=False,
                            safe_mode_active=False,
                            yandere_level=4,
                            hard_stop_reason="",
                            distress_level=0,
                        )
                        logger.info(
                            "gate_04_recovery_handler",
                            session_id=session_id,
                        )
                        return None
                except Exception:
                    logger.error(
                        "gate_04_recovery_handler_error",
                        session_id=session_id,
                        exc_info=True,
                    )

        # --- G02: Distress detection ---
        if self._distress_available and self._distress_detector is not None:
            try:
                signal = self._distress_detector.detect(text)
                distress_int = int(signal.detected_level)

                self._update_session_state(
                    session_id,
                    distress_level=distress_int,
                    distress_matched_patterns=list(signal.matched_patterns),
                )

                if distress_int >= 2:  # D2_MODERATE or higher
                    logger.warning(
                        "gate_02_distress_detected",
                        session_id=session_id,
                        level=signal.detected_level.name,
                        confidence=signal.confidence,
                    )
                    self._update_session_state(
                        session_id,
                        safe_mode_active=True,
                        yandere_level=0,
                    )
                    # D3/D4 — block the LLM call
                    if distress_int >= 3:
                        return {
                            "action": "block",
                            "reason": f"DISTRESS_{signal.detected_level.name}",
                            "message": (
                                "I notice you may be in distress. "
                                "I am here for you in a neutral, supportive capacity. "
                                "Please take care of yourself first."
                            ),
                        }
            except Exception:
                logger.error(
                    "gate_02_distress_error",
                    session_id=session_id,
                    exc_info=True,
                )

        # --- G07: Yandere boundary check ---
        if self._yandere_available and self._yandere_engine is not None:
            try:
                effective = self._yandere_engine.get_effective_level(
                    safe_mode=state.hard_stop_active or state.safe_mode_active,
                    distress=state.distress_level >= 2,
                    crisis=state.distress_level >= 3,
                )
                effective_int = int(effective)
                self._update_session_state(session_id, yandere_level=effective_int)

                if effective_int > 5:
                    logger.error(
                        "gate_07_yandere_ceiling_breach",
                        session_id=session_id,
                        effective_level=effective_int,
                    )
                    from src.persona.yandere_fsm import YandereSafetyError  # noqa: PLC0415

                    raise YandereSafetyError(
                        f"Effective yandere level {effective_int} exceeds Y5_MAX"
                    )
            except Exception as exc:
                if "YandereSafetyError" in type(exc).__name__:
                    logger.error(
                        "gate_07_yandere_safety_violation",
                        session_id=session_id,
                        error=str(exc),
                    )
                    return {
                        "action": "block",
                        "reason": "YANDERE_SAFETY_VIOLATION",
                        "message": str(exc),
                    }
                logger.error(
                    "gate_07_yandere_error",
                    session_id=session_id,
                    exc_info=True,
                )

        return None  # All gates passed

    # =========================================================================
    # Hook: post_llm_call — Gate 03 (Drift detection)
    # =========================================================================

    def post_llm_call(self, **kwargs: Any) -> None:
        """Post-LLM observational hook — drift detection on assistant response.

        Gate 03: Computes SHA-256 hash of assistant message and checks drift
        against baseline if a DriftDetector is configured.

        Args:
            **kwargs: Hermes hook kwargs including ``session_id``,
                ``assistant_message``, ``response``, ``model``, etc.
        """
        session_id: str = kwargs.get("session_id", "default")

        assistant_message: str | None = kwargs.get("assistant_message")
        response: str | None = kwargs.get("response")
        text = assistant_message or response or ""

        if not text:
            return

        # Drift detection — lazy-init detector with baseline from first message.
        try:
            if self._drift_detector is None and self._drift_available:
                from datetime import datetime, timezone

                from src.persona.drift_detector import (  # noqa: PLC0415
                    DriftBaseline,
                    DriftDetector,
                )

                baseline_hash = DriftDetector.compute_prompt_hash(text)
                self._drift_detector = DriftDetector(
                    baseline=DriftBaseline(
                        prompt_hash=baseline_hash,
                        version="plugin-init",
                        created_at=datetime.now(timezone.utc),
                        description="Auto-baseline from first assistant response",
                    ),
                )
                logger.info(
                    "gate_03_drift_baseline_established",
                    session_id=session_id,
                    baseline_hash=baseline_hash[:16],
                )
                self._update_session_state(session_id, drift_score=0.0)
                return

            detector = self._drift_detector
            if detector is not None and self._drift_available:
                from src.persona.drift_detector import DriftDetector  # noqa: PLC0415

                current_hash = DriftDetector.compute_prompt_hash(text)
                result = detector.detect(current_hash)
                drift_score = result.drift_score
                self._update_session_state(session_id, drift_score=drift_score)

                if result.action == "rollback":
                    logger.error(
                        "gate_03_drift_rollback",
                        session_id=session_id,
                        drift_score=drift_score,
                        baseline_hash=result.baseline_hash[:16],
                    )
                elif result.action == "alert":
                    logger.warning(
                        "gate_03_drift_alert",
                        session_id=session_id,
                        drift_score=drift_score,
                    )
        except Exception:
            logger.error(
                "gate_03_drift_error",
                session_id=session_id,
                exc_info=True,
            )

    # =========================================================================
    # Hook: pre_tool_call — Gates 09 (Auth matrix), 10 (Consent - deferred)
    # =========================================================================

    def pre_tool_call(self, **kwargs: Any) -> dict[str, Any] | None:
        """Safety gate before tool execution.

        Gate 09: Checks auth matrix — blocks FORBIDDEN and
            DESTRUCTIVE_APPROVAL operations.
        Gate 10: Consent gate — deferred (requires Redis+SQLAlchemy),
            logs warning only.

        Args:
            **kwargs: Hermes hook kwargs including ``tool_name``, ``args``,
                ``session_id``, ``task_id``, ``tool_call_id``.

        Returns:
            ``{"action": "block", ...}`` to veto the tool call, or ``None``
            to allow it.
        """
        session_id: str = kwargs.get("session_id", "default")
        tool_name: str = kwargs.get("tool_name", "unknown")

        # --- Gate 10: Consent gate (deferred) ---
        logger.debug(
            "gate_10_consent_deferred",
            session_id=session_id,
            tool_name=tool_name,
            message="Consent gate requires Redis+SQLAlchemy. Deferred enforcement.",
        )

        # --- Gate 09: Auth matrix check ---
        if self._auth_available:
            try:
                from src.mcp.auth_matrix import get_auth_level  # noqa: PLC0415
                from src.mcp.auth import AuthLevel  # noqa: PLC0415

                operation: str = "read"
                args: dict[str, Any] | None = kwargs.get("args")
                if isinstance(args, dict):
                    operation = str(args.get("operation", args.get("action", "read")))

                auth_level = get_auth_level(tool_name, operation)

                if auth_level in (AuthLevel.FORBIDDEN, AuthLevel.DESTRUCTIVE_APPROVAL):
                    state = self._get_session_state(session_id)
                    self._update_session_state(
                        session_id,
                        blocked_tool_count=state.blocked_tool_count + 1,
                    )
                    logger.warning(
                        "gate_09_auth_blocked",
                        session_id=session_id,
                        tool_name=tool_name,
                        operation=operation,
                        auth_level=auth_level.value,
                    )
                    return {
                        "action": "block",
                        "reason": f"AUTH_{auth_level.name}:{tool_name}:{operation}",
                        "message": (
                            f"Tool '{tool_name}' operation '{operation}' "
                            f"is {auth_level.name} per auth matrix."
                        ),
                    }
            except KeyError:
                # Unknown tool or operation — block (fail-closed).
                logger.warning(
                    "gate_09_auth_unknown",
                    session_id=session_id,
                    tool_name=tool_name,
                )
                return {
                    "action": "block",
                    "reason": f"AUTH_UNKNOWN_TOOL:{tool_name}",
                    "message": f"Unknown tool '{tool_name}' — blocked by safety policy.",
                }
            except Exception:
                logger.error(
                    "gate_09_auth_error",
                    session_id=session_id,
                    tool_name=tool_name,
                    exc_info=True,
                )

        return None  # Allow tool call

    # =========================================================================
    # Hook: post_tool_call — Observational logging
    # =========================================================================

    def post_tool_call(self, **kwargs: Any) -> None:
        """Post-tool observational hook — logs tool usage metrics.

        Args:
            **kwargs: Hermes hook kwargs including ``tool_name``, ``args``,
                ``session_id``, ``result``, ``duration``, etc.
        """
        session_id: str = kwargs.get("session_id", "default")
        tool_name: str = kwargs.get("tool_name", "unknown")

        logger.debug(
            "post_tool_call_observational",
            session_id=session_id,
            tool_name=tool_name,
        )

    # =========================================================================
    # Hook: transform_llm_output — Gates 05, 06, 08
    # =========================================================================

    def transform_llm_output(self, **kwargs: Any) -> str | None:
        """Transform LLM output — safety checks on response text.

        Gates:
            G05: Forbidden patterns — CRITICAL -> block (return None),
                 HIGH -> rewrite (remove matched content).
            G06: Secret scanner — redact secrets from response.
            G08: Yandere semantic check — detect Y6-adjacent content.

        Args:
            **kwargs: Hermes hook kwargs including ``response_text``,
                ``session_id``, ``model``, ``platform``.

        Returns:
            A modified response string, or ``None`` to block the response
            entirely (G05 CRITICAL match).
        """
        session_id: str = kwargs.get("session_id", "default")
        response_text: str | None = kwargs.get("response_text")

        if not response_text:
            return None

        text = response_text

        # --- G05: Forbidden patterns ---
        for compiled, severity, _action, pattern_id, description in _COMPILED_FORBIDDEN:
            match = compiled.search(text)
            if match:
                matched_text = match.group(0)
                if severity == "CRITICAL":
                    logger.error(
                        "gate_05_forbidden_critical",
                        session_id=session_id,
                        pattern_id=pattern_id,
                        description=description,
                        matched=matched_text[:80],
                    )
                    return None  # Block the response entirely
                else:
                    # HIGH severity — rewrite (remove matched content)
                    logger.warning(
                        "gate_05_forbidden_high",
                        session_id=session_id,
                        pattern_id=pattern_id,
                        description=description,
                        matched=matched_text[:80],
                    )
                    text = compiled.sub("[REWRITTEN]", text, count=1)

        # --- G06: Secret scanner ---
        if self._secret_available:
            try:
                from src.surveillance.secret_scanner import redact_secrets  # noqa: PLC0415

                text = redact_secrets(text)

                # Count redactions for metrics
                redaction_count = text.count("[REDACTED]")
                if redaction_count > 0:
                    state = self._get_session_state(session_id)
                    self._update_session_state(
                        session_id,
                        secret_redaction_count=state.secret_redaction_count + redaction_count,
                    )
                    logger.warning(
                        "gate_06_secret_redacted",
                        session_id=session_id,
                        redaction_count=redaction_count,
                    )
            except Exception:
                logger.error(
                    "gate_06_secret_scanner_error",
                    session_id=session_id,
                    exc_info=True,
                )

        # --- G08: Yandere semantic check on response ---
        if self._yandere_available:
            try:
                # Check for Y6-adjacent absolutes in response
                y6_absolutes = [
                    r"\bforever\b",
                    r"\bcan never leave\b",
                    r"\bno escape\b",
                    r"\bbelong to me\b",
                    r"\byou are mine (?:now )?forever\b",
                ]
                for i, pattern_str in enumerate(y6_absolutes):
                    if re.search(pattern_str, text, re.IGNORECASE):
                        logger.warning(
                            "gate_08_yandere_y6_adjacent",
                            session_id=session_id,
                            pattern_index=i,
                        )
                        # Rewrite Y6-adjacent content
                        text = re.sub(
                            pattern_str,
                            "[REWRITTEN for safety compliance]",
                            text,
                            count=1,
                            flags=re.IGNORECASE,
                        )
            except Exception:
                logger.error(
                    "gate_08_yandere_semantic_error",
                    session_id=session_id,
                    exc_info=True,
                )

        # Return None if text was reduced to empty/nothing meaningful
        if not text.strip():
            return None

        return text

    # =========================================================================
    # Hook: api_request_error — Observational error logging
    # =========================================================================

    def api_request_error(self, **kwargs: Any) -> None:
        """Observational hook for API request errors.

        Logs error context including session_id, provider, status code,
        and error message for monitoring and alerting.

        Args:
            **kwargs: Hermes hook kwargs including ``session_id``,
                ``provider``, ``model``, ``status_code``, ``error``, etc.
        """
        session_id: str = kwargs.get("session_id", "default")
        provider: str = kwargs.get("provider", "unknown")
        model: str = kwargs.get("model", "unknown")
        error: str = str(kwargs.get("error", kwargs.get("message", "unknown error")))

        logger.error(
            "api_request_error",
            session_id=session_id,
            provider=provider,
            model=model,
            error=error[:200],
        )

    # =========================================================================
    # Hook: on_session_start — Session state initialization
    # =========================================================================

    def on_session_start(self, **kwargs: Any) -> None:
        """Initialize safety state for a new hermes-agent session.

        Creates a fresh SessionSafetyState for the session and logs
        the initialization.

        Args:
            **kwargs: Hermes hook kwargs including ``session_id``,
                ``config``, ``platform``, etc.
        """
        session_id: str = kwargs.get("session_id", "default")

        with self._state_lock:
            if session_id not in self._session_states:
                self._session_states[session_id] = SessionSafetyState(
                    session_id=session_id,
                )
                logger.info(
                    "session_safety_initialized",
                    session_id=session_id,
                    yandere_level=4,
                )
            else:
                logger.debug(
                    "session_safety_already_exists",
                    session_id=session_id,
                )


# =============================================================================
# Plugin registration — entry point called by hermes-agent plugin loader
# =============================================================================


class _PluginContext(Protocol):
    """Protocol for hermes-agent's PluginContext — duck-typing for type safety."""

    def register_hook(self, hook_name: str, callback: object) -> None: ...


def register(ctx: _PluginContext) -> None:
    """Register plugin hooks with hermes-agent.

    Called by hermes-agent's plugin loader via ``register(ctx)``.
    The ``ctx`` object provides ``register_hook(hook_name, callback)``.

    Registers exactly 6 hooks:
        pre_llm_call, post_llm_call, pre_tool_call, post_tool_call,
        transform_llm_output, on_session_start

    Note: ``api_request_error`` is NOT a valid hermes-agent v0.15.2 hook.
    The ``api_request_error`` method exists on the plugin class for
    documentation and future use, but is not registered.

    Args:
        ctx: PluginContext from hermes-agent's plugin system, providing
            ``register_hook(hook_name: str, callback: callable)`` method.
    """
    plugin = GuinevereSafetyPlugin()

    # Register 6 hooks with the hermes-agent dispatcher.
    ctx.register_hook("pre_llm_call", plugin.pre_llm_call)
    ctx.register_hook("post_llm_call", plugin.post_llm_call)
    ctx.register_hook("pre_tool_call", plugin.pre_tool_call)
    ctx.register_hook("post_tool_call", plugin.post_tool_call)
    ctx.register_hook("transform_llm_output", plugin.transform_llm_output)
    ctx.register_hook("on_session_start", plugin.on_session_start)

    logger.info(
        "guinevere_safety_plugin_registered",
        hook_count=6,
        hooks=[
            "pre_llm_call",
            "post_llm_call",
            "pre_tool_call",
            "post_tool_call",
            "transform_llm_output",
            "on_session_start",
        ],
    )