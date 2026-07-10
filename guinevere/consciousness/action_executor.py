"""Action Executor — routes high-confidence thoughts to action handlers.

Evaluates thoughts from the consciousness stream and routes eligible ones
(actionable types with confidence > threshold) to appropriate handlers:
  - discord_message: prepare message payload (NOT sent — Phase B wiring)
  - memory_write: persist via ConsciousnessMemoryBridge
  - tool_call: extract tool name + args, validated against allowlist
  - state_change: record intent for internal state update

Design decisions:
  - Confidence-gated: only thoughts with confidence > 0.8 are eligible.
  - Type-gated: only COGNITION and PLANNING thoughts can trigger actions.
  - Frozen Thought safety: does NOT mutate Thought; tracks acted thought IDs
    in executor state.
  - Allowlist-guarded tool calls: tool_call actions validate tool name against
    a configurable allowlist before execution.
  - Discord messages are prepared but never sent (Phase B responsibility).
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from guinevere.consciousness.memory_bridge import ConsciousnessMemoryBridge
    from guinevere.consciousness.thought import Thought

from guinevere.consciousness.thought import ThoughtType

_logger = logging.getLogger(__name__)

# Default confidence threshold for action eligibility.
_ACTION_CONFIDENCE_THRESHOLD: float = 0.8

# Thought types that can trigger actions.
_ACTIONABLE_TYPES: frozenset[ThoughtType] = frozenset(
    {ThoughtType.COGNITION, ThoughtType.PLANNING}
)

# Default allowlist for tool_call actions.
_DEFAULT_TOOL_ALLOWLIST: frozenset[str] = frozenset(
    {
        "web_search",
        "file_read",
        "file_write",
        "code_execute",
        "memory_search",
        "memory_store",
        "discord_send",
        "timer_set",
    }
)


# ---------------------------------------------------------------------------
# ActionSpec — describes a single action to execute
# ---------------------------------------------------------------------------


@dataclass
class ActionSpec:
    """Specification for an action derived from a thought.

    Attributes:
        thought_id: ID of the originating thought.
        action_type: The category of action to perform.
        target: Target identifier (channel name, tool name, state key, etc.).
        payload: Action-specific payload data.
        confidence: Confidence score from the originating thought.
    """

    thought_id: str
    action_type: Literal[
        "discord_message", "memory_write", "tool_call", "state_change"
    ]
    target: str
    payload: dict[str, Any]
    confidence: float

    def to_log_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dict for structured logging."""
        return {
            "thought_id": self.thought_id,
            "action_type": self.action_type,
            "target": self.target,
            "payload": self.payload,
            "confidence": round(self.confidence, 4),
        }


# ---------------------------------------------------------------------------
# ActionExecutor — routes thoughts to action handlers
# ---------------------------------------------------------------------------


class ActionExecutor:
    """Routes high-confidence thoughts to appropriate action handlers.

    Evaluates thoughts against confidence threshold and type eligibility,
    then dispatches to the correct handler based on action_type.

    Handlers:
        - discord_message: prepare message payload (NOT sent).
        - memory_write: route to memory_bridge if available.
        - tool_call: validate tool name against allowlist, extract args.
        - state_change: record intent for internal state update.
    """

    def __init__(
        self,
        llm_router: Any,
        memory_bridge: Any = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Initialise the action executor.

        Args:
            llm_router: LLM router instance (for extracting action intent).
            memory_bridge: Optional ConsciousnessMemoryBridge for memory_write.
            config: Optional configuration overrides. Supported keys:
                - "confidence_threshold" (float): override default 0.8.
                - "tool_allowlist" (list[str]): override default tool allowlist.
        """
        self._router: Any = llm_router
        self._memory_bridge: ConsciousnessMemoryBridge | None = memory_bridge
        self._config: dict[str, Any] = config or {}
        self._executed_actions: list[ActionSpec] = []
        self._action_count: int = 0
        self._acted_thought_ids: set[str] = set()

        # Configurable threshold.
        self._confidence_threshold: float = float(
            self._config.get("confidence_threshold", _ACTION_CONFIDENCE_THRESHOLD)
        )

        # Configurable tool allowlist.
        custom_tools = self._config.get("tool_allowlist")
        if custom_tools is not None:
            self._tool_allowlist: frozenset[str] = frozenset(custom_tools)
        else:
            self._tool_allowlist = _DEFAULT_TOOL_ALLOWLIST

    # ── public properties ───────────────────────────────────

    @property
    def action_count(self) -> int:
        """Return total number of actions executed."""
        return self._action_count

    # ── thought ID generation ───────────────────────────────

    @staticmethod
    def _thought_key(thought: Thought) -> str:
        """Generate a deterministic key for a Thought instance.

        Uses a hash of type + content + timestamp to produce a stable
        identifier, since Thought is a frozen dataclass without an id field.
        """
        raw = (
            f"{thought.type.value}|{thought.content}|"
            f"{thought.timestamp.isoformat()}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    # ── evaluation ──────────────────────────────────────────

    def evaluate_thought(self, thought: Thought) -> ActionSpec | None:
        """Evaluate if a thought should trigger an action.

        A thought triggers an action when ALL of the following are true:
            - thought.confidence > self._confidence_threshold (default 0.8)
            - thought.type in {COGNITION, PLANNING}
            - thought has not already been acted upon

        Args:
            thought: The Thought to evaluate.

        Returns:
            ActionSpec if the thought should trigger an action, None otherwise.
        """
        thought_id = self._thought_key(thought)

        # Already acted on this thought.
        if thought_id in self._acted_thought_ids:
            return None

        # Confidence gate: must be strictly above threshold.
        if thought.confidence <= self._confidence_threshold:
            return None

        # Type gate: only COGNITION and PLANNING are actionable.
        if thought.type not in _ACTIONABLE_TYPES:
            return None

        # Extract action intent from thought content.
        action_type, target, payload = self._extract_action_intent(thought)

        spec = ActionSpec(
            thought_id=thought_id,
            action_type=action_type,
            target=target,
            payload=payload,
            confidence=thought.confidence,
        )

        # Mark as acted.
        self._acted_thought_ids.add(thought_id)

        return spec

    # ── execution ───────────────────────────────────────────

    async def execute(self, action: ActionSpec) -> dict[str, Any]:
        """Execute the action based on its action_type.

        Dispatches to the appropriate handler:
            - "discord_message": prepare message payload (NOT sent).
            - "memory_write": route to memory_bridge if available.
            - "tool_call": validate tool name, extract args.
            - "state_change": record intent for state update.

        Args:
            action: The ActionSpec to execute.

        Returns:
            Dict with execution result: {
                "status": "prepared" | "written" | "validated" | "recorded" | "error",
                "action_type": str,
                "details": dict,
            }
        """
        self._executed_actions.append(action)
        self._action_count += 1

        _logger.info(
            "action_executor.execute",
            extra=action.to_log_dict(),
        )

        if action.action_type == "discord_message":
            return await self._execute_discord_message(action)
        elif action.action_type == "memory_write":
            return await self._execute_memory_write(action)
        elif action.action_type == "tool_call":
            return await self._execute_tool_call(action)
        elif action.action_type == "state_change":
            return await self._execute_state_change(action)
        else:
            return {
                "status": "error",
                "action_type": action.action_type,
                "details": {"error": f"Unknown action type: {action.action_type}"},
            }

    # ── history ─────────────────────────────────────────────

    def get_action_history(self, n: int = 10) -> list[ActionSpec]:
        """Return the n most recent executed actions.

        Args:
            n: Number of recent actions to return. Default 10.

        Returns:
            List of ActionSpec objects, most recent last.
        """
        return self._executed_actions[-n:]

    # ── action intent extraction ────────────────────────────

    def _extract_action_intent(
        self, thought: Thought
    ) -> tuple[
        Literal["discord_message", "memory_write", "tool_call", "state_change"],
        str,
        dict[str, Any],
    ]:
        """Extract action type, target, and payload from thought content.

        Uses simple keyword-based heuristic to determine action type.
        Falls back to "memory_write" when no clear action is detected.

        Args:
            thought: The Thought to extract intent from.

        Returns:
            Tuple of (action_type, target, payload).
        """
        content_lower = thought.content.lower()

        # Discord message intent.
        if any(
            kw in content_lower
            for kw in ["send message", "discord", "tell faiz", "notify", "message to"]
        ):
            return (
                "discord_message",
                "discord",
                {"channel": "general", "content": thought.content},
            )

        # Tool call intent.
        if any(
            kw in content_lower
            for kw in ["search for", "look up", "run tool", "execute tool", "use tool"]
        ):
            return (
                "tool_call",
                "generic_tool",
                {"tool": "web_search", "args": {"query": thought.content}},
            )

        # State change intent.
        if any(
            kw in content_lower
            for kw in ["update state", "change state", "set state", "modify state"]
        ):
            return (
                "state_change",
                "consciousness_state",
                {"target": "state", "value": thought.content},
            )

        # Default: memory write.
        return (
            "memory_write",
            "memory",
            {"content": thought.content, "tags": [thought.type.value]},
        )

    # ── handlers ────────────────────────────────────────────

    async def _execute_discord_message(
        self, action: ActionSpec
    ) -> dict[str, Any]:
        """Prepare a Discord message payload (NOT sent).

        Phase B will wire actual Discord sending. For now, the payload is
        validated and returned as "prepared".
        """
        channel = action.payload.get("channel", "general")
        content = action.payload.get("content", "")

        if not content:
            return {
                "status": "error",
                "action_type": "discord_message",
                "details": {"error": "Empty message content"},
            }

        return {
            "status": "prepared",
            "action_type": "discord_message",
            "details": {"channel": channel, "content_length": len(content)},
        }

    async def _execute_memory_write(
        self, action: ActionSpec
    ) -> dict[str, Any]:
        """Route memory write to memory_bridge if available."""
        content = action.payload.get("content", "")
        tags = action.payload.get("tags", [])

        if self._memory_bridge is not None:
            try:
                # Use the memory bridge to store the action content.
                from guinevere.consciousness.thought import Thought as ThoughtCls

                synthetic_thought = ThoughtCls(
                    type=ThoughtType.COGNITION,
                    content=content,
                    confidence=action.confidence,
                )
                episode_id = await self._memory_bridge.record_thought(
                    synthetic_thought
                )
                return {
                    "status": "written",
                    "action_type": "memory_write",
                    "details": {
                        "episode_id": episode_id,
                        "tags": tags,
                        "content_length": len(content),
                    },
                }
            except Exception as exc:
                _logger.warning(
                    "action_executor.memory_write.failed",
                    extra={"error": str(exc), "thought_id": action.thought_id},
                )
                return {
                    "status": "error",
                    "action_type": "memory_write",
                    "details": {"error": str(exc)},
                }

        # No bridge available — record intent only.
        return {
            "status": "recorded",
            "action_type": "memory_write",
            "details": {
                "tags": tags,
                "content_length": len(content),
                "note": "memory_bridge not available; intent recorded",
            },
        }

    async def _execute_tool_call(self, action: ActionSpec) -> dict[str, Any]:
        """Validate tool name against allowlist and extract args."""
        tool_name = action.payload.get("tool", "")
        args = action.payload.get("args", {})

        # Allowlist guard.
        if tool_name not in self._tool_allowlist:
            return {
                "status": "error",
                "action_type": "tool_call",
                "details": {
                    "error": f"Tool '{tool_name}' not in allowlist",
                    "allowlist": sorted(self._tool_allowlist),
                },
            }

        return {
            "status": "validated",
            "action_type": "tool_call",
            "details": {"tool": tool_name, "args": args},
        }

    async def _execute_state_change(
        self, action: ActionSpec
    ) -> dict[str, Any]:
        """Record intent for internal state update."""
        target = action.payload.get("target", "")
        value = action.payload.get("value", None)

        return {
            "status": "recorded",
            "action_type": "state_change",
            "details": {"target": target, "value": value},
        }
