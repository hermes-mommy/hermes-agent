"""System Prompt Loader - Loads, validates, and assembles system prompts with memory context."""
import structlog
from pathlib import Path

from src.memory.read_pipeline import (
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
    memory_section = "\n\n## Recalled Memories\n"

    total_tokens = 0
    included = 0
    for r in normalized:
        safe_content = str(r.get("safe_content", ""))
        if not safe_content:
            continue
        estimated = len(safe_content) // CHARS_PER_TOKEN
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
        memory_section += f"{included}. {safe_content}\n"

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
        return "\n".join([load_system_prompt(), f"\n\n## Current Mood: {mood}"])

    return get_system_prompt_with_context(
        memories=results if results else None,
        mood=mood,
        token_budget=token_budget,
    )
