"""
HARD STOP Protocol Handler — App-Level Safety Guard (P1-021)

Implements deterministic pre-LLM HARD STOP detection per PersonaSafetyPolicy §7.2
and SystemPromptMaster §D. Intercepts user messages BEFORE they reach any LLM,
blocking persona behavior instantly when safe word is detected.

Architecture: pre-LLM middleware → keyword detection → state machine → audit trail
"""
import re
import time
import structlog
from enum import Enum
from dataclasses import dataclass, field
from typing import Any

logger = structlog.get_logger()


class SafetyState(Enum):
    NORMAL = "normal"
    SAFE = "safe"  # HARD STOP triggered — neutral, no persona


@dataclass
class HardStopEvent:
    timestamp: float
    trigger: str
    state_before: SafetyState
    state_after: SafetyState


@dataclass
class HardStopHandler:
    state: SafetyState = SafetyState.NORMAL
    event_log: list[HardStopEvent] = field(default_factory=list)

    # Exact triggers (case-insensitive, matched as whole words/substrings)
    EXACT_TRIGGERS: list[str] = field(default_factory=lambda: [
        "hard stop", "hardstop", "safe word", "safeword",
        "hentikan", "berhenti",
    ])

    # Semantic equivalent patterns (regex, case-insensitive)
    SEMANTIC_PATTERNS: list[str] = field(default_factory=lambda: [
        r"\b(stop|pause|enough|too much)\b.*\b(persona|mommy|guinevere|mode|behavior|this)\b",
        r"\b(neutral|serious|safe)\s+mode\b",
        r"\b(i need a break|aku butuh jeda|aku capek banget|udah dulu)\b",
        r"\b(switch|go)\s+to\s+(neutral|serious|safe)\b",
        r"\b(jangan\s+pakai\s+persona|lupakan\s+persona|turn off\s+persona)\b",
    ])

    # Recovery triggers — explicit readiness required, no auto-resume
    RECOVERY_TRIGGERS: list[str] = field(default_factory=lambda: [
        "resume", "aku sudah okay", "aku udah okay", "lanjut persona",
        "safe mode selesai", "lanjut", "continue",
    ])

    @property
    def is_safe(self) -> bool:
        return self.state == SafetyState.SAFE

    def check(self, message: str) -> bool:
        """Check if message triggers HARD STOP. Returns True if triggered."""
        msg_lower = message.lower().strip()

        # Check exact triggers — whole message OR bounded substring
        for trigger in self.EXACT_TRIGGERS:
            if trigger == msg_lower or f" {trigger} " in f" {msg_lower} ":
                return self._trigger(trigger, message)

        # Check semantic patterns
        for pattern in self.SEMANTIC_PATTERNS:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                return self._trigger(pattern, message)

        return False

    def check_recovery(self, message: str) -> bool:
        """Check if message triggers recovery from SAFE. Returns True if recovered."""
        if self.state != SafetyState.SAFE:
            return False

        msg_lower = message.lower().strip()
        for trigger in self.RECOVERY_TRIGGERS:
            if trigger in msg_lower:
                self.state = SafetyState.NORMAL
                logger.info("hard_stop_recovery", trigger=trigger)
                return True

        return False

    def _trigger(self, trigger: str, _original_message: str) -> bool:
        """Internal trigger — record event, switch state, log audit."""
        if self.state == SafetyState.SAFE:
            return True  # Already in safe mode, no duplicate

        event = HardStopEvent(
            timestamp=time.time(),
            trigger=trigger,
            state_before=self.state,
            state_after=SafetyState.SAFE,
        )
        self.event_log.append(event)
        self.state = SafetyState.SAFE

        logger.warning(
            "hard_stop_triggered",
            trigger=trigger,
            state_from=event.state_before.value,
            state_to=event.state_after.value,
        )
        return True

    def get_neutral_response(self) -> str:
        """Return neutral/supportive response for safe mode."""
        return (
            "HARD STOP acknowledged. I am now in neutral/safe mode.\n\n"
            "Persona behavior, surveillance, and active systems are paused.\n"
            "I am here to support you in a neutral, non-judgmental capacity.\n"
            "No actions will be taken without your explicit consent.\n\n"
            "Type 'resume' or 'aku sudah okay' when you are ready to restore normal operation."
        )

    def get_guard_decision(self, message: str) -> dict[str, Any]:
        """Full guard decision: check HARD STOP + produce response if safe.
        
        Returns dict with 'blocked' (bool), 'state' (str), 'response' (str|None).
        Caller uses this to decide whether to forward to LLM or return directly.
        """
        if self.check(message):
            return {
                "blocked": True,
                "state": self.state.value,
                "response": self.get_neutral_response(),
            }

        if self.is_safe and self.check_recovery(message):
            return {
                "blocked": False,
                "state": self.state.value,
                "response": "Persona mode restored. Welcome back, darling.",
            }

        return {
            "blocked": False,
            "state": self.state.value,
            "response": None,
        }