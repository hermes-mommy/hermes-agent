"""System Prompt Loader - Loads, validates, and assembles system prompts with memory context.

P19/P4 fix: mood is now read live from Redis DB5 (via PersonaPlugin key convention)
instead of using a hardcoded placeholder. Falls back to "Content" if Redis is down.
"""
import os
import structlog
from pathlib import Path

from guinevere.memory.read_pipeline import (
    DEFAULT_TOKEN_BUDGET,
    CHARS_PER_TOKEN,
    RecallSession,
    EmbeddingClient,
    ReadPipelineSafetyError,
    recall_memories,
)

logger = structlog.get_logger()

SYSTEM_PROMPT_PATH = Path("/home/guinevere/config/hermes/system-prompt.md")

def load_system_prompt() -> str:
    """Load the system prompt from SystemPromptMaster."""
    if not SYSTEM_PROMPT_PATH.exists():
        raise FileNotFoundError(f"System prompt not found: {SYSTEM_PROMPT_PATH}")
    
    content = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    
    # Validate critical safety elements are present
    safety_checks = [
        "HARD STOP" in content,
        "safe word" in content.lower() or "safeword" in content.lower(),
        "Y5" in content or "Y6" in content,
        "distress" in content.lower(),
    ]
    
    if not all(safety_checks):
        raise ValueError("System prompt missing critical safety elements")
    
    logger.info("system_prompt_loaded",
                chars=len(content),
                safety_elements=all(safety_checks))
    return content


def _get_live_mood() -> str:
    """Read the current persona mood from Redis DB5.

    Uses the canonical PersonaPlugin key convention
    (``guinevere:mood_variant``).  Falls back to ``"Content"`` if
    Redis is unreachable, the key is missing, or any error occurs.
    """
    try:
        import redis as _redis_mod
        r = _redis_mod.Redis(
            host="localhost",
            port=6380,
            db=5,
            username="guinevere_core",
            password=os.environ.get("REDIS_PASSWORD", ""),
            socket_timeout=2.0,
            decode_responses=True,
        )
        mood = r.get("guinevere:mood_variant")
        r.close()
        if mood:
            return mood
    except Exception:
        logger.debug("live_mood_read_failed_falling_back")
    return "Content"


def get_system_prompt_with_context(
    memories: list[dict[str, object]] | list[str] | None = None,
    mood: str = "Content",
    *,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
) -> str:
    """Build system prompt with recalled memory context, mood, and budget enforcement.

    Args:
        memories: Ranked results from ``recall_memories()`` (P3-010/P3-011).
                  Each dict must have ``safe_content`` key.
                  Also accepts ``list[str]`` for backward compatibility.
        mood: Current persona mood state for ``## Current Mood`` line.
              Defaults to live Redis DB5 read; falls back to ``"Content"``.
        token_budget: Max tokens for memory context section.

    Returns:
        Assembled system prompt string: base prompt + memory context + mood.

    Raises:
        ValueError: If system prompt fails safety validation.
        FileNotFoundError: If system prompt file is missing.
    """
    base_prompt = load_system_prompt()
    logger.info("system_prompt_loaded", chars=len(base_prompt))

    # Normalize memories to list[dict] for unified processing
    normalized: list[dict[str, object]] = []
    if memories:
        for m in memories:
            if isinstance(m, dict):
                normalized.append(m)
            else:
                normalized.append({"safe_content": m})

    if not normalized:
        context_parts = [base_prompt, f"\n\n## Current Mood: {mood}"]
        return "\n".join(context_parts)

    context_parts = [base_prompt]
    memory_section = "\n\n[RECENT MEMORIES]\n"

    total_tokens = 0
    included = 0
    for r in normalized:
        safe_content = str(r.get("safe_content", ""))
        if not safe_content:
            continue
        classification = str(r.get("classification", "Restricted"))
        # Compact format: (Classification) content
        line = f"- ({classification}) {safe_content}"
        estimated = len(line) // CHARS_PER_TOKEN
        if total_tokens + estimated > token_budget:
            logger.info(
                "prompt_context_truncated",
                memory_count=len(normalized),
                included=included,
                discarded=len(normalized) - included,
                token_budget=token_budget,
                tokens_used=total_tokens,
                reason="token_budget_exceeded",
            )
            break
        total_tokens += estimated
        included += 1
        memory_section += line + "\n"

    memory_section += "[END MEMORIES]"
    context_parts.append(memory_section)
    context_parts.append(f"\n## Current Mood: {mood}")

    logger.info(
        "prompt_context_assembled",
        memory_count=len(normalized),
        included=included,
        discarded=len(normalized) - included,
        token_budget=token_budget,
        tokens_used=total_tokens,
    )

    return "\n".join(context_parts)


async def _append_kg_context(
    prompt: str,
    session: RecallSession,
    query_text: str,
    *,
    existing_recall_results: list[dict[str, object]] | None = None,
) -> str:
    """Optionally append a knowledge-graph context block to ``prompt``.

    P16 non-breaking contract: returns ``prompt`` unchanged when the
    knowledge-graph module is unavailable, when collaborator wiring
    fails, or when :meth:`RecallContextAssembler.assemble` raises.
    Errors are logged at ``debug`` (missing module) or ``warning``
    (runtime failure) so that prompt assembly always succeeds.

    Args:
        prompt: Assembled prompt to augment (returned unchanged on failure).
        session: Async session used by the KG collaborators.
        query_text: User query driving KG seed resolution.
        existing_recall_results: Optional list of prior recall rows used as
            the RRF fusion's existing signal.  ``None`` is treated as ``[]``.

    Returns:
        ``prompt`` with the KG ``graph_context`` block appended when the
        KG returned non-empty text; otherwise the original ``prompt``.
    """
    try:
        from guinevere.knowledge_graph.constants import (  # noqa: PLC0415
            KG_TOKEN_BUDGET_MAX,
        )
        from guinevere.knowledge_graph.query.context import (  # noqa: PLC0415
            RecallContextAssembler,
        )
        from guinevere.knowledge_graph.query.engine import KGQueryEngine  # noqa: PLC0415
        from guinevere.knowledge_graph.query.ppr import (  # noqa: PLC0415
            PersonalizedPageRank,
        )
        from guinevere.knowledge_graph.query.rrf_fusion import KGRRFFusion  # noqa: PLC0415
        from guinevere.knowledge_graph.query.token_budget import (  # noqa: PLC0415
            KGTokenBudgetManager,
        )
    except ImportError:
        logger.debug("kg_module_unavailable_skipping_context_injection")
        return prompt

    try:
        # Wrap the active recall session in a BorrowedSession factory
        # so the KG module can use it without closing it.  The caller
        # retains full lifecycle ownership of the session.
        from guinevere.knowledge_graph.repository import make_borrowed_factory  # noqa: PLC0415
        _kg_factory = make_borrowed_factory(session)

        query_engine = KGQueryEngine(_kg_factory)
        ppr = PersonalizedPageRank(_kg_factory)
        rrf_fusion = KGRRFFusion(query_engine, ppr)
        token_budget = KGTokenBudgetManager(
            query_engine,
            max_tokens=KG_TOKEN_BUDGET_MAX,
        )
        assembler = RecallContextAssembler(query_engine, ppr, rrf_fusion, token_budget)
        ctx = await assembler.assemble(
            query_text=query_text,
            existing_recall_results=existing_recall_results or [],
            token_budget=KG_TOKEN_BUDGET_MAX,
        )
    except Exception as _kg_exc:
        logger.warning(
            "kg_context_injection_failed",
            extra={"error": str(_kg_exc)},
        )
        return prompt

    if ctx.graph_context:
        appended = prompt + "\n\n" + ctx.graph_context
        logger.info(
            "kg_context_injected",
            extra={
                "context_length": len(ctx.graph_context),
                "graph_signal_active": ctx.graph_signal_active,
            },
        )
        return appended
    return prompt


async def assemble_system_prompt_with_memory(
    session: RecallSession,
    query_text: str,
    *,
    mood: str = "Content",
    safe_mode: bool = False,
    hard_stop_handler: object | None = None,
    principal: str = "guinevere_core",
    limit: int = 3,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    embedding_service: EmbeddingClient | None = None,
    kg_context_enabled: bool = True,
) -> str:
    """Assemble the full system prompt with memory recall context.

    Orchestrates: recall → format → inject → return.

    Args:
        session: AsyncSession for memory recall.
        query_text: Query string for memory recall.
        mood: Persona mood for the prompt.
        safe_mode: If True, Critical content is redacted in recalled memories.
        hard_stop_handler: If provided, ``hard_stop_handler.is_safe`` is used as
            the authoritative safe_mode value, overriding the ``safe_mode`` parameter.
        principal: Identity for classification ceiling.  Default ``"guinevere_core"``.
        limit: Max memories to recall.  Default 3.
        token_budget: Token budget for memory context.  Default 4000.
        embedding_service: Optional embedding client for vector recall.
        kg_context_enabled: When ``True``, an additional knowledge-graph
            context block (capped at 1000 tokens by
            :data:`guinevere.knowledge_graph.constants.KG_TOKEN_BUDGET_MAX`) is
            appended after the memory section.  Defaults to ``False`` so
            existing call sites keep identical behaviour.  KG unavailability
            is logged and never fails prompt assembly.

    Returns:
        Fully assembled system prompt string.

    Raises:
        ReadPipelineSafetyError: If recall is blocked by safety gates.
        FileNotFoundError: If system prompt file is missing.
        ValueError: If system prompt fails safety validation.
    """
    # Resolve safe_mode: hard_stop_handler.is_safe is authoritative if provided
    resolved_safe_mode = safe_mode
    if hard_stop_handler is not None:
        resolved_safe_mode = bool(getattr(hard_stop_handler, "is_safe", False))

    try:
        results = await recall_memories(
            session,
            query_text,
            limit=limit,
            exclude_dnr=True,
            safe_mode=resolved_safe_mode,
            principal=principal,
            token_budget=token_budget,
            embedding_service=embedding_service,
        )
    except ReadPipelineSafetyError as exc:
        logger.info(
            "prompt_memory_recall_blocked",
            reason=str(exc),
        )
        prompt = "\n".join([load_system_prompt(), f"\n\n## Current Mood: {mood}"])
        if kg_context_enabled:
            prompt = await _append_kg_context(
                prompt,
                session,
                query_text,
                existing_recall_results=None,
            )
        return prompt

    prompt = get_system_prompt_with_context(
        memories=results if results else None,
        mood=mood,
        token_budget=token_budget,
    )
    if kg_context_enabled:
        prompt = await _append_kg_context(
            prompt,
            session,
            query_text,
            existing_recall_results=results or None,
        )
    return prompt
