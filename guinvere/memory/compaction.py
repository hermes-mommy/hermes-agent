"""Context compaction pipeline — P5-024.

Implements AutoGPT 5-step cascade with pinned safety messages.
Compacts long conversation histories before they exceed model context limits.

Safety constraints:
- NEVER compact messages containing pinned safety tags
- ALWAYS use proper error handling (no bare except)
- NEVER use type-safety suppression
- Tiktoken fallback is graceful, not silent
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, cast

import structlog

from guinvere.core.services.llm_router import LLMRouter, TaskType

_logger = structlog.get_logger()

# Pinned safety tags that must NEVER be compacted away
_PINNED_TAGS = frozenset({
    "safe_word",
    "hard_stop",
    "distress",
    "consent_revocation",
    "do_not_recall",
})

# Token budget: 100k (leave 28k buffer for 128k context window)
_MAX_TOKENS = 100000

# Preserve first 3 and last 3 regular messages (recency + primacy bias)
_PRIME_RECENCY_COUNT = 3


@dataclass(frozen=True)
class CompactionResult:
    """Result of a compaction operation."""

    original_message_count: int
    compacted_message_count: int
    tokens_saved: int
    summary: str
    pinned_count: int


class ContextCompactor:
    """Compacts conversation histories before they exceed model context limits.

    Implements AutoGPT 5-step cascade:
    1. Separate pinned messages (safety tags) — NEVER compact these
    2. Count tokens (tiktoken or len//4 fallback)
    3. If under budget, return as-is
    4. Summarize middle messages via LLM (first 3 + last 3)
    5. Re-assemble: pinned + first_3 + summary + last_3
    """

    def __init__(
        self,
        max_tokens: int = _MAX_TOKENS,
        summary_model: str = "deepseek-v4-flash",
    ) -> None:
        """Initialize the context compactor.

        Parameters
        ----------
        max_tokens:
            Maximum allowed tokens before compaction is triggered.
            Default 100k (128k context - 28k buffer).
        summary_model:
            Model name to use for summarization. Defaults to DeepSeek V4 Flash.
        """
        self.max_tokens = max_tokens
        self.summary_model = summary_model
        self.llm_router = LLMRouter()

    async def compact(self, messages: list[dict]) -> CompactionResult:
        """Compact conversation history before it exceeds model limits.

        Parameters
        ----------
        messages:
            List of message dictionaries, each with at least a ``content`` key.
            Example: [{"role": "user", "content": "..."}, ...]

        Returns
        -------
        CompactionResult
            Details about the compaction operation.

        Raises
        ------
        ValueError
            If messages is empty or malformed.
        """
        if not messages:
            raise ValueError("messages list must contain at least one message")

        # Step 1: Separate pinned messages (safety tags)
        pinned_messages, regular_messages = self._extract_pinned(messages)

        if not regular_messages:
            # Only pinned messages — nothing to compact
            return CompactionResult(
                original_message_count=len(messages),
                compacted_message_count=len(messages),
                tokens_saved=0,
                summary="",
                pinned_count=len(pinned_messages),
            )

        # Step 2: Count tokens
        total_tokens = sum(
            self._count_tokens(msg.get("content", "")) for msg in messages
        )

        # Step 3: If under budget, return as-is
        if total_tokens <= self.max_tokens:
            return CompactionResult(
                original_message_count=len(messages),
                compacted_message_count=len(messages),
                tokens_saved=0,
                summary="",
                pinned_count=len(pinned_messages),
            )

        # Step 4: Summarize middle messages (first 3 + last 3 preserved)
        first_preserved = regular_messages[:_PRIME_RECENCY_COUNT]
        last_preserved = regular_messages[-_PRIME_RECENCY_COUNT:]

        middle_messages = regular_messages[_PRIME_RECENCY_COUNT:-_PRIME_RECENCY_COUNT]
        if len(middle_messages) == 0:
            # All regular messages are in first/last 3 — nothing to summarize
            return CompactionResult(
                original_message_count=len(messages),
                compacted_message_count=len(messages),
                tokens_saved=0,
                summary="",
                pinned_count=len(pinned_messages),
            )

        summary = await self._summarize(middle_messages)

        # Step 5: Re-assemble
        compacted_messages = (
            pinned_messages +
            first_preserved +
            [{"role": "system", "content": f"Summary: {summary}"}] +
            last_preserved
        )

        saved_tokens = total_tokens - sum(
            self._count_tokens(msg.get("content", ""))
            for msg in compacted_messages
        )

        _logger.info(
            "context_compacted",
            original_count=len(messages),
            compacted_count=len(compacted_messages),
            tokens_saved=saved_tokens,
            pinned_count=len(pinned_messages),
        )

        return CompactionResult(
            original_message_count=len(messages),
            compacted_message_count=len(compacted_messages),
            tokens_saved=saved_tokens,
            summary=summary,
            pinned_count=len(pinned_messages),
        )

    def _extract_pinned(self, messages: list[dict]) -> tuple[list[dict], list[dict]]:
        """Separate pinned safety messages from regular messages.

        Parameters
        ----------
        messages:
            List of message dictionaries.

        Returns
        -------
        tuple[list[dict], list[dict]]
            (pinned_messages, regular_messages)
        """
        pinned_messages: list[dict] = []
        regular_messages: list[dict] = []

        for msg in messages:
            content = msg.get("content", "")
            if not isinstance(content, str):
                # Non-string content is treated as regular (cannot contain tags)
                regular_messages.append(msg)
                continue

            # Check if any pinned tag appears in content
            content_lower = content.lower()
            is_pinned = any(tag in content_lower for tag in _PINNED_TAGS)

            if is_pinned:
                pinned_messages.append(msg)
            else:
                regular_messages.append(msg)

        return pinned_messages, regular_messages

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text with tiktoken fallback.

        Parameters
        ----------
        text:
            Text to count tokens for.

        Returns
        -------
        int
            Estimated token count.
        """
        try:
            # Try tiktoken encoding_for_model (DeepSeek V4 Flash compatible)
            import tiktoken

            encoding = tiktoken.encoding_for_model("gpt-4")
            return len(encoding.encode(text))
        except ImportError:
            # Tiktoken not available — fallback to len//4
            _logger.warning("tiktoken_not_available_fallback_to_char_div4")
            tokens = len(text) // 4
            return max(0, tokens)
        except Exception as exc:
            # Unexpected error — log and use fallback
            _logger.warning(
                "tiktoken_count_error_fallback",
                error=str(exc),
                text_length=len(text),
            )
            tokens = len(text) // 4
            return max(0, tokens)

    async def _summarize(self, messages: list[dict]) -> str:
        """Summarize middle messages via LLM.

        Parameters
        ----------
        messages:
            Messages to summarize (middle section of conversation).

        Returns
        -------
        str
            Summary of the conversation.
        """
        # Build summary prompt
        prompt_parts = [
            "Summarize this conversation history. Preserve key facts, decisions, and context.",
            "Never remove mentions of: safe words, hard stops, distress signals,",
            "consent changes, or do-not-recall requests.",
            "",
            "Conversation:",
        ]

        for idx, msg in enumerate(messages, start=1):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            prompt_parts.append(f"{idx}. [{role}]: {content}")

        prompt_parts.append("")
        prompt_parts.append("Summary:")

        prompt = "\n".join(prompt_parts)

        # Call LLMRouter with FALLBACK task type
        try:
            result = await self.llm_router.chat(
                messages=[{"role": "user", "content": prompt}],
                task_type=TaskType.FALLBACK,
            )

            summary = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return summary.strip()
        except Exception as exc:
            _logger.error(
                "llm_summarization_failed",
                error=str(exc),
            )
            # Fallback: return empty summary on error
            return ""

    async def close(self) -> None:
        """Close the LLM router client."""
        await self.llm_router.close()