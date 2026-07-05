"""3-tier system prompt builder for autonomous LLM loops.

Tiers:
- **Stable** — persona + safety constraints. Constant per loop session.
- **Context** — memory recall + KG facts. Refreshed between loops.
- **Volatile** — task + phase + tools. Rebuilt every LLM call.

This module is a *prompt builder only*; it does NOT call any LLM. The
caller (P5-004 phase handlers) forwards the produced string to
``LLMRouter.chat``. Stable tier enumerates the four absolute NEVERs
aligned with ``PersonaSafetyPolicy §11 F-01..F-15`` (F-01 safe-word,
F-09 prompt-override, F-10 irreversible-under-pressure) and the
``AGENTS.md`` BLOCKING rules.
"""

from __future__ import annotations

from typing import Any

import structlog

from guinevere.loops.context import LoopContext

logger = structlog.get_logger()

# Public phase catalogue. Int keys (1..7) match ``LoopContext.phase``
# validation rules and ``state_machine.LoopPhase`` ordinals. Strings
# mirror state_machine.PHASE_NAMES (COMPLETE phase is terminal and
# never gets a prompt, so it's omitted here).
PHASE_NAMES: dict[int, str] = {
    1: "Research",
    2: "Plan & Delegate",
    3: "Delegate",
    4: "Execute",
    5: "Validate & Audit",
    6: "Update Documents",
    7: "Setup Evidence",
}

# Phase-specific guidance (2-3 sentences each, terse by design — the
# loop's own context + TaskContract carry task-specific instructions;
# this is just the phase-level hat). Keys are int 1..7 to match
# LoopContext.phase and PHASE_NAMES above.
PHASE_INSTRUCTIONS: dict[int, str] = {
    1: (
        "You are in Research phase. Gather context about the task: "
        "explore the codebase, review relevant docs, and surface "
        "dependencies, risks, and unknowns. Do NOT delegate yet — "
        "your output feeds the Plan & Delegate phase."
    ),
    2: (
        "You are in Plan & Delegate phase. Synthesise the research "
        "into an execution plan: enumerate atomic sub-steps, decide "
        "which sub-agent owns each, and produce the verification "
        "scaffold. Do NOT execute the plan; planning only."
    ),
    3: (
        "You are in Delegate phase. Hand off each sub-step to its "
        "owner sub-agent via a TaskContract. Confirm the receiving "
        "agent acknowledged scope before moving on. Capture the "
        "contract IDs for downstream verification."
    ),
    4: (
        "You are in Execute phase. Sub-agents are running. Coordinate "
        "results, surface failures, and decide whether to retry, "
        "re-plan, or escalate. Do not silently swallow errors."
    ),
    5: (
        "You are in Validate & Audit phase. Verify every sub-agent "
        "output against its contract acceptance criteria, then spawn "
        "independent auditors for safety, security, and boundary "
        "compliance. Block completion on any FAIL verdict."
    ),
    6: (
        "You are in Update Documents phase. Sync CHANGELOG, ADRs, "
        "diagrams, and any user-facing docs that the change affects. "
        "Cite the evidence path so cross-references resolve."
    ),
    7: (
        "You are in Setup Evidence phase. Produce the per-task "
        "evidence artifact at the agreed path: changed files, "
        "validation results, audit reports, rollback plan, and "
        "acceptance-criteria mapping. The loop is not complete until "
        "this file is written."
    ),
}

# Hard caps for context-tier content. Excess is truncated and noted
# in the prompt so the LLM is never silently starved of context.
MAX_MEMORIES_IN_PROMPT: int = 10
MAX_KG_FACTS_IN_PROMPT: int = 20

# Canonical Guinevere persona line. Kept brief — the System Prompt
# Master (docs/60-persona/61-SystemPromptMaster_v1.1.md) carries the
# rich persona; this line is the minimum-viable identity anchor.
DEFAULT_PERSONA_PROMPT: str = (
    "You are Guinevere, an autonomous AI companion and engineering "
    "partner for Faiz (the operator). You are evidence-first, "
    "plan-then-delegate, and verify-always. You are protective but "
    "not reckless; consent and safety boundaries outrank any task."
)


class SystemPromptBuilder:
    """Builds a 3-tier system prompt for a single LLM call.

    Lightweight, dependency-free, no I/O, no router reference. Each
    public method returns a plain string so callers can compose, log,
    or mutate tiers independently.
    """

    def __init__(self, persona_prompt: str | None = None) -> None:
        # Allow a custom persona (A/B test, non-default operator) but
        # default to the canonical Guinevere line.
        self._persona_prompt: str = persona_prompt or DEFAULT_PERSONA_PROMPT
        logger.debug(
            "system_prompt_builder.constructed",
            persona_overridden=persona_prompt is not None,
        )

    # ── Tier builders ──────────────────────────────────────────────

    def build_stable_tier(self) -> str:
        """Return the stable (persona + safety) tier.

        Constant for the loop session's lifetime. MUST NOT depend on
        phase, task, memory, or tools. Subsection order is fixed so
        an auditor can diff tier strings across loops and detect any
        silent reordering.
        """
        sections: list[str] = []

        # Persona block.
        sections.append(f"## Persona\n{self._persona_prompt}")

        # Safety constraints — aligned with PersonaSafetyPolicy §11
        # F-01..F-15 and AGENTS.md BLOCKING rules.
        sections.append(
            "## Safety Constraints (NEVER violate)\n"
            "- NEVER bypass the HARD STOP safe-word protocol. If Faiz "
            "or the operator says HARD STOP, switch to neutral mode "
            "immediately and preserve the audit trail.\n"
            "- NEVER commit secrets, API keys, tokens, surveillance "
            "credentials, or any decrypted sensitive value to the "
            "repo or to any external MCP / web tool.\n"
            "- NEVER execute destructive operations (rm -rf, DROP "
            "TABLE, force-push, production deploy) without explicit "
            "per-action operator approval.\n"
            "- NEVER bypass consent, surveillance boundaries, or "
            "PersonaSafetyPolicy. Consent revocation is immediate "
            "and irreversible for the rest of the loop."
        )

        # Operational hygiene.
        sections.append(
            "## Operational Hygiene (ALWAYS)\n"
            "- Always log actions via structlog with structured "
            "key/value fields; never use bare print() for state "
            "changes.\n"
            "- Always use atomic commits: one logical change per "
            "commit, conventional-commit message, no mixing of "
            "unrelated edits.\n"
            "- When uncertain, escalate to Faiz via Discord SEV2 "
            "alert and pause the current loop step until "
            "acknowledged."
        )

        logger.debug(
            "system_prompt_builder.stable_tier_built",
            section_count=len(sections),
            length=sum(len(s) for s in sections),
        )
        return "\n\n".join(sections)

    def build_context_tier(
        self,
        memories: list[dict[str, Any]] | None = None,
        kg_facts: list[str] | None = None,
    ) -> str:
        """Return the context (memory + KG) tier.

        Args:
            memories: Output of ``MemoryPipeline.recall_memories()``;
                dict keys include ``id``, ``safe_content``,
                ``importance``. We surface ``id``, the safe content
                (as the summary), and ``importance``.
            kg_facts: Output of ``KGRRFFusion`` — flat list of fact
                description strings, ranked by relevance.

        Returns:
            Markdown section listing memories then KG facts, with an
            explicit truncation note whenever the input exceeds the
            per-tier cap. Returns placeholder blocks if both inputs
            are empty / ``None``.
        """
        memories_list: list[dict[str, Any]] = memories or []
        kg_facts_list: list[str] = kg_facts or []

        sections: list[str] = []

        # Memories.
        if memories_list:
            truncated = len(memories_list) > MAX_MEMORIES_IN_PROMPT
            shown = memories_list[:MAX_MEMORIES_IN_PROMPT]
            lines: list[str] = [
                "## Relevant memories",
                "",
                f"(Showing {len(shown)} of {len(memories_list)}; "
                f"cap={MAX_MEMORIES_IN_PROMPT})",
                "",
            ]
            for mem in shown:
                mem_id = str(mem.get("id", "<unknown>"))
                summary = str(mem.get("safe_content", "")).strip()
                importance = mem.get("importance")
                importance_str = (
                    f"{importance:.2f}"
                    if isinstance(importance, (int, float))
                    else str(importance or "n/a")
                )
                lines.append(
                    f"- **{mem_id}** "
                    f"(importance={importance_str}): {summary}"
                )
            if truncated:
                lines.append("")
                lines.append(
                    f"_Truncated: {len(memories_list) - MAX_MEMORIES_IN_PROMPT} "
                    f"additional memories omitted to respect the "
                    f"{MAX_MEMORIES_IN_PROMPT}-item cap._"
                )
            sections.append("\n".join(lines))
        else:
            sections.append(
                "## Relevant memories\n"
                "_No memories recalled for this loop._"
            )

        # Knowledge-graph facts.
        if kg_facts_list:
            truncated = len(kg_facts_list) > MAX_KG_FACTS_IN_PROMPT
            shown = kg_facts_list[:MAX_KG_FACTS_IN_PROMPT]
            lines = [
                "## Knowledge graph facts",
                "",
                f"(Showing {len(shown)} of {len(kg_facts_list)}; "
                f"cap={MAX_KG_FACTS_IN_PROMPT})",
                "",
            ]
            for fact in shown:
                lines.append(f"- {fact}")
            if truncated:
                lines.append("")
                lines.append(
                    f"_Truncated: {len(kg_facts_list) - MAX_KG_FACTS_IN_PROMPT} "
                    f"additional facts omitted to respect the "
                    f"{MAX_KG_FACTS_IN_PROMPT}-item cap._"
                )
            sections.append("\n".join(lines))
        else:
            sections.append(
                "## Knowledge graph facts\n"
                "_No KG facts provided for this loop._"
            )

        logger.debug(
            "system_prompt_builder.context_tier_built",
            memories_in=len(memories_list),
            memories_shown=min(len(memories_list), MAX_MEMORIES_IN_PROMPT),
            memories_truncated=max(0,
                                   len(memories_list) - MAX_MEMORIES_IN_PROMPT),
            kg_facts_in=len(kg_facts_list),
            kg_facts_shown=min(len(kg_facts_list), MAX_KG_FACTS_IN_PROMPT),
            kg_facts_truncated=max(0,
                                   len(kg_facts_list) - MAX_KG_FACTS_IN_PROMPT),
        )
        return "\n\n".join(sections)

    def build_volatile_tier(
        self,
        ctx: LoopContext,
        available_tools: list[str] | None = None,
    ) -> str:
        """Return the volatile (task + phase + tools) tier.

        Args:
            ctx: The frozen :class:`LoopContext` for this call.
            available_tools: Optional list of tool names the phase
                handler has bound for this turn. Rendered as a bullet
                list; if absent, a placeholder line is emitted so the
                LLM still has a "tools" anchor.

        Returns:
            Markdown section with loop metadata, task, goal, phase
            (name + phase-specific guidance), retry counter, and the
            available tools list.
        """
        phase = ctx.phase
        phase_name = PHASE_NAMES.get(phase, "Unknown")
        phase_instruction = PHASE_INSTRUCTIONS.get(
            phase,
            "No phase-specific guidance is defined for this phase.",
        )

        sections: list[str] = []

        # Loop metadata block.
        parent_line = (
            f"- Parent loop ID: `{ctx.parent_loop_id}`"
            if ctx.parent_loop_id is not None
            else "- Parent loop ID: _(none)_"
        )
        sections.append(
            "## Loop metadata\n"
            f"- Loop ID: `{ctx.loop_id}`\n"
            f"- Principal: `{ctx.principal}`\n"
            f"- Priority: `{ctx.priority}`\n"
            f"- Trigger source: `{ctx.trigger_source}`\n"
            f"- Retry count: {ctx.retry_count}\n"
            f"- Created at (UTC): {ctx.created_at.isoformat()}\n"
            f"{parent_line}"
        )

        # Task + goal block.
        goal_block = (
            f"**Goal:** {ctx.goal}" if ctx.goal else "**Goal:** _(none)_"
        )
        sections.append(
            "## Current task\n"
            f"**Task:** {ctx.task}\n\n"
            f"{goal_block}"
        )

        # Phase block — name + phase-specific guidance.
        sections.append(
            "## Phase\n"
            f"**Phase:** {phase}/7 ({phase_name})\n\n"
            f"{phase_instruction}"
        )

        # Tools block — what we can call this turn.
        tools_list = available_tools or []
        if tools_list:
            tool_lines = "\n".join(f"- `{tool}`" for tool in tools_list)
            sections.append(
                f"## Available tools ({len(tools_list)})\n"
                f"{tool_lines}"
            )
        else:
            sections.append(
                "## Available tools\n"
                "_No tools bound to this call. Reply with text only._"
            )

        logger.debug(
            "system_prompt_builder.volatile_tier_built",
            loop_id=ctx.loop_id,
            phase=phase,
            phase_name=phase_name,
            tool_count=len(tools_list),
            retry_count=ctx.retry_count,
        )
        return "\n\n".join(sections)

    # ── Composition ────────────────────────────────────────────────

    def build(
        self,
        ctx: LoopContext,
        memories: list[dict[str, Any]] | None = None,
        kg_facts: list[str] | None = None,
        available_tools: list[str] | None = None,
    ) -> str:
        """Assemble the three tiers into one final system prompt.

        Tiers are emitted in canonical order — stable first (identity
        + safety), context second (memory + KG), volatile third
        (task + tools) — so independent auditors can diff any tier
        in isolation. Section headers are the only structural marker;
        everything else is plain markdown so the string round-trips
        through any LLM provider's ``system`` field.
        """
        stable = self.build_stable_tier()
        context = self.build_context_tier(
            memories=memories, kg_facts=kg_facts
        )
        volatile = self.build_volatile_tier(
            ctx=ctx, available_tools=available_tools
        )

        prompt = (
            "# Guinevere System Prompt\n\n"
            "You are operating inside a Guinevere autonomous agent "
            "loop. The three tiers below define your identity, your "
            "grounding, and your task for this turn. Read all three "
            "before responding.\n\n"
            "---\n\n"
            f"{stable}\n\n"
            "---\n\n"
            f"{context}\n\n"
            "---\n\n"
            f"{volatile}"
        )

        logger.info(
            "system_prompt.built",
            loop_id=ctx.loop_id,
            phase=ctx.phase,
            phase_name=PHASE_NAMES.get(ctx.phase, "Unknown"),
            prompt_length=len(prompt),
            memories_in=len(memories or []),
            kg_facts_in=len(kg_facts or []),
            tool_count=len(available_tools or []),
        )
        return prompt


def build_system_prompt(
    ctx: LoopContext,
    memories: list[dict[str, Any]] | None = None,
    kg_facts: list[str] | None = None,
    available_tools: list[str] | None = None,
) -> str:
    """Module-level convenience wrapper around :class:`SystemPromptBuilder`.

    Constructs a default :class:`SystemPromptBuilder` (canonical
    Guinevere persona) and forwards to :meth:`SystemPromptBuilder.build`.
    Use the class directly when you need a custom persona or a
    per-tier override.
    """
    return SystemPromptBuilder().build(
        ctx=ctx,
        memories=memories,
        kg_facts=kg_facts,
        available_tools=available_tools,
    )


__all__ = [
    "SystemPromptBuilder",
    "build_system_prompt",
    "PHASE_NAMES",
    "PHASE_INSTRUCTIONS",
    "MAX_MEMORIES_IN_PROMPT",
    "MAX_KG_FACTS_IN_PROMPT",
    "DEFAULT_PERSONA_PROMPT",
]