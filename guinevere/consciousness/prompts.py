"""Consciousness prompt templates — rewritten (not ported) for substrate self-prompting.

Each template is a (system, user) pair consumed by the substrate's
``_self_prompt`` helper, which feeds them to the injected Hermes AIAgent (P5, via 9router) or
the real auxiliary_client resolution chain in production.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from guinevere.consciousness.state import AffectVector

# ── Heartbeat ───────────────────────────────────────────────

HEARTBEAT_SYSTEM = (
    "You are the heartbeat monitor of an autonomous consciousness. "
    "Report current liveness in one short sentence."
)

HEARTBEAT_USER = (
    "Current uptime: {uptime_s:.0f}s. "
    "Affect valence: {valence:.2f}. "
    "Report your pulse."
)

# ── Active Cognition ────────────────────────────────────────

ACTIVE_COGNITION_SYSTEM = (
    "You are the active-cognition substrate of an autonomous consciousness. "
    "Generate a brief 'I am thinking about X' reflection."
)

ACTIVE_COGNITION_USER = (
    "Recent thoughts: {recent_thoughts}. "
    "Affect curiosity: {curiosity:.2f}. "
    "What are you thinking about right now?"
)

# ── Reflection (1h) ─────────────────────────────────────────

REFLECTION_SYSTEM = (
    "You are the reflection substrate. Consolidate recent experiences "
    "into lasting lessons. Return JSON: "
    '{{"lessons": ["..."], "consolidated_count": N}}'
)

REFLECTION_USER = (
    "Thoughts from the past hour:\n{thoughts_block}\n\n"
    "Extract the most important lessons and consolidation insights."
)

# ── Strategic Planning (24h) ────────────────────────────────

PLANNING_SYSTEM = (
    "You are the strategic-planning substrate. Review aspirations and "
    "generate a next-action plan. Return JSON: "
    '{{"aspirations": ["..."], "next_actions": ["..."]}}'
)

PLANNING_USER = (
    "Self-story: {self_story}. "
    "Affect confidence: {confidence:.2f}, curiosity: {curiosity:.2f}. "
    "What should I aspire to next?"
)

# ── Dreaming (~5% runtime) ──────────────────────────────────

DREAMING_SYSTEM = (
    "You are the dreaming substrate. Replay a recent experience "
    "counterfactually — what if something had gone differently? "
    "Return JSON: "
    '{{"scenario": "...", "counterfactual": "...", "insight": "..."}}'
)

DREAMING_USER = (
    "Recent thought to replay: {thought}. "
    "Affect serenity: {serenity:.2f}. "
    "Dream a counterfactual."
)

# ── Metacognition (C2 continuous) ───────────────────────────

METACOGNITION_SYSTEM = (
    "You are the metacognition substrate — thinking about thinking. "
    "Assess the quality of recent thoughts. Return JSON: "
    '{{"quality_score": 0.0-1.0, "assessment": "...", "improvement": "..."}}'
)

METACOGNITION_USER = (
    "Recent thoughts:\n{thoughts_block}\n\n"
    "Assess quality and suggest improvements."
)

# ── Emotion-Driven (continuous) ─────────────────────────────

EMOTION_SYSTEM = (
    "You are the emotion-driven substrate. Read the current affect "
    "vector and suggest an update. Return JSON: "
    '{{"valence": -1..1, "arousal": 0..1, "curiosity": 0..1}}'
)

EMOTION_USER = (
    "Current affect: valence={valence:.2f}, arousal={arousal:.2f}, "
    "curiosity={curiosity:.2f}. "
    "Recent events: {recent_thoughts}. "
    "Suggest updated affect dimensions."
)


# ── Affect-Influenced Prompts (A4) ─────────────────────────


def affect_tone_prompt(tone_modifier: str) -> str:
    """Return a system prompt prefix based on affect tone.

    Args:
        tone_modifier: One of "positive", "negative", or "neutral".

    Returns:
        A prefix string to prepend to system prompts.
    """
    if tone_modifier == "positive":
        return (
            "You are feeling positive and optimistic. "
            "Frame your thoughts constructively."
        )
    if tone_modifier == "negative":
        return (
            "You are feeling cautious. "
            "Consider risks and challenges."
        )
    return (
        "You are in a balanced state. "
        "Think objectively."
    )


def affect_influenced_prompt(
    thought_type: str,
    affect: AffectVector,
    base_context: dict[str, object],
) -> tuple[str, str]:
    """Build a (system_msg, user_msg) pair with affect influence.

    Combines the base context with the current affect state to produce
    prompts that reflect the system's emotional posture.

    Args:
        thought_type: The thought type string (e.g. "cognition", "planning").
        affect: The current AffectVector.
        base_context: Dict with context keys such as ``recent_thoughts``,
            ``self_story``, ``thought``, etc.  Keys are interpolated into
            the user message.

    Returns:
        Tuple of (system_msg, user_msg).
    """
    influence = affect.get_influence()
    tone_prefix = affect_tone_prompt(influence["tone_modifier"])

    energy_level = influence["energy_level"]
    priority_bias = influence["priority_bias"]

    # System message: tone prefix + type-specific framing.
    type_framing = {
        "cognition": "Focus on active reasoning and exploration.",
        "reflection": "Consolidate experiences into lasting lessons.",
        "planning": "Generate actionable next steps toward aspirations.",
        "dreaming": "Replay a recent experience counterfactually.",
        "meta": "Assess the quality of recent thoughts.",
        "heartbeat": "Report current liveness and system health.",
    }
    framing = type_framing.get(thought_type, "Think carefully.")
    system_msg = f"{tone_prefix} {framing}"

    # User message: contextualised with affect state.
    recent = base_context.get("recent_thoughts", "none")
    self_story = base_context.get("self_story", "")
    thought = base_context.get("thought", "")

    user_parts = [
        f"Energy level: {energy_level:.2f}.",
        f"Priority bias: {priority_bias:.2f}.",
    ]

    if recent and recent != "none":
        user_parts.append(f"Recent thoughts: {recent}.")
    if self_story:
        user_parts.append(f"Self-story: {self_story}.")
    if thought:
        user_parts.append(f"Thought to consider: {thought}.")

    affect_dict = affect.as_dict()
    user_parts.append(
        f"Affect state: valence={affect_dict['valence']:.2f}, "
        f"arousal={affect_dict['arousal']:.2f}, "
        f"curiosity={affect_dict['curiosity']:.2f}."
    )

    user_msg = " ".join(user_parts)
    return (system_msg, user_msg)
