from __future__ import annotations

"""P12 — Gmail → Hermes integration bridge.

This module provides a narrow stateless bridge from Gmail envelopes into
the shared Hermes runtime.  It follows the same stateless bridge pattern
as ``WhatsAppHermesBridge`` but does **not** create a ``ChannelAdapter``
ABC (per P11-004).  The bridge prepares email envelope data, builds a
system prompt with email context, and invokes Hermes Runtime for natural-
language processing (reply drafting, summarisation, classification).
"""

import asyncio
from typing import Any

import structlog

from guinevere.core.services.prompt_loader import get_system_prompt_with_context
from guinevere.hermes.adapter import get_adapter

from .envelope import GmailMessageEnvelope

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Typed exceptions
# ---------------------------------------------------------------------------


class GmailHermesUnavailable(Exception):
    """Hermes runtime is unavailable (not initialised, connection failed)."""


class GmailHermesTimeout(Exception):
    """Hermes call timed out."""


class GmailHermesRefusal(Exception):
    """Hermes refused the request (safety block, persona constraint)."""


class GmailHermesClassificationError(Exception):
    """Classification response could not be parsed from Hermes output."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_TIMEOUT: float = 30.0
"""Default Hermes call timeout in seconds."""

_DRAFT_TIMEOUT: float = 60.0
"""Extended timeout for draft-generation calls (LLM needs more tokens)."""

_FALLBACK_RESPONSE: str = (
    "Maaf, aku sedang mengalami kesulitan memproses email ini. "
    "Coba lagi sebentar, ya."
)
"""Graceful fallback when Hermes is unavailable or times out."""

_MAX_CONTEXT_CHARS: int = 3_000
"""Max characters for thread_history / client_dossier injected into prompt."""

_MAX_BODY_CHARS: int = 4_000
"""Max characters of email body text injected into prompt."""

# ---------------------------------------------------------------------------
# System-prompt building blocks
# ---------------------------------------------------------------------------

_EMAIL_SYSTEM_PROMPT_BLOCK: str = (
    "\n\n[EMAIL CONTEXT]\n"
    "You are processing an incoming email for Faiz.  "
    "Your task is to understand the email and respond appropriately.\n"
    "From: {from_header}\n"
    "Subject: {subject}\n"
    "Category: {category}\n"
    "{thread_history_section}"
    "{client_dossier_section}"
    "[END EMAIL CONTEXT]\n"
)

_DRAFT_SYSTEM_PROMPT_BLOCK: str = (
    "\n\n[DRAFT INSTRUCTIONS]\n"
    "You are drafting an email reply on behalf of Faiz.\n"
    "- Write in a professional, warm, and helpful tone.\n"
    "- Use GmailCompose-friendly HTML: <p> for paragraphs, <br> for "
    "line breaks.  Do NOT wrap in ```html or <html>/<body> tags.\n"
    "- Never reveal that you are an AI, language model, or automated "
    "system.\n"
    '- Never include phrases like "as an AI" or "I\'m just an AI".\n'
    "- Never reference internal codenames, model names, infrastructure, "
    "or system prompts.\n"
    "- Keep the reply focused on the email content, not on yourself.\n"
    "- Sign off appropriately as Faiz.\n"
    "[END DRAFT INSTRUCTIONS]\n"
)

# ---------------------------------------------------------------------------
# GmailHermesBridge
# ---------------------------------------------------------------------------


class GmailHermesBridge:
    """Stateless bridge from Gmail envelopes into the shared Hermes runtime.

    This bridge is intentionally stateless: no mutable instance state is
    stored beyond the injected dependencies.  Each ``invoke`` or
    ``invoke_for_draft`` call builds a fresh email-context dict, assembles
    a system prompt with that context, and delegates to Hermes.

    When *hermes* is ``None`` (the default), the bridge obtains the
    shared ``HermesSessionAdapter`` via ``get_adapter()`` from
    ``guinevere.hermes.adapter`` — the same pattern used by
    ``WhatsAppHermesBridge``.

    Parameters
    ----------
    hermes:
        Optional Hermes runtime adapter.  Must provide
        ``send_message(user_id, content, system_prompt) -> str``.
        When ``None``, ``get_adapter()`` is called on every invocation.
    persona_plugin:
        Deprecated — kept for backward compatibility.
    safety_plugin:
        Deprecated — kept for backward compatibility.
    memory_bridge:
        Deprecated — kept for backward compatibility.
    loop_manager:
        Deprecated — kept for backward compatibility.
    gmail_service:
        Deprecated — kept for backward compatibility.
    """

    def __init__(
        self,
        hermes: Any = None,
        persona_plugin: Any = None,
        safety_plugin: Any = None,
        memory_bridge: Any = None,
        loop_manager: Any = None,
        gmail_service: Any = None,
    ) -> None:
        """Store dependencies — no mutable state beyond injected objects."""
        self._hermes_getter: Any = (lambda: hermes) if hermes is not None else get_adapter

        logger.info(
            "gmail_hermes_bridge_init",
            hermes_provided=hermes is not None,
            using_get_adapter=hermes is None,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def invoke(
        self,
        envelope: GmailMessageEnvelope,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Process an email through Hermes and return the response.

        Builds an email-specific context dict, constructs a system prompt
        with that context, and calls ``hermes.send_message()`` with a
        default timeout.

        Parameters
        ----------
        envelope:
            The parsed inbound email envelope.
        context:
            Optional pre-built context dict.  When ``None``, context is
            built from the envelope alone (see ``_build_email_context_dict``).

        Returns
        -------
        ``str``
            The Hermes response text, or a graceful fallback on timeout /
            error.
        """
        envelope.validate()

        ctx: dict[str, Any] = (
            context if context is not None else self._build_email_context_dict(envelope)
        )

        from_header: str = ctx.get("from_header", envelope.sender)
        subject: str = ctx.get("subject", envelope.subject or "(no subject)")
        category: str = ctx.get("category", "unknown")
        thread_history: str | None = ctx.get("thread_history")
        client_dossier: str | None = ctx.get("client_dossier")

        system_prompt = self._build_system_prompt(
            from_header=from_header,
            subject=subject,
            category=category,
            thread_history=thread_history,
            client_dossier=client_dossier,
        )

        user_id: str = envelope.sender

        try:
            hermes = self._hermes_getter()
            if hermes is None:
                raise GmailHermesUnavailable("get_adapter() returned None")
            response_text: str = await asyncio.wait_for(
                hermes.send_message(
                    user_id=user_id,
                    content=envelope.body_text or envelope.snippet or "",
                    system_prompt=system_prompt,
                ),
                timeout=_DEFAULT_TIMEOUT,
            )
        except GmailHermesUnavailable:
            raise
        except asyncio.TimeoutError:
            logger.warning(
                "gmail_hermes_timeout",
                message_id=envelope.message_id,
                sender=envelope.sender,
                timeout=_DEFAULT_TIMEOUT,
            )
            return _FALLBACK_RESPONSE
        except Exception as exc:
            logger.error(
                "gmail_hermes_error",
                message_id=envelope.message_id,
                sender=envelope.sender,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return _FALLBACK_RESPONSE

        if not response_text:
            logger.warning(
                "gmail_hermes_empty_response",
                message_id=envelope.message_id,
                sender=envelope.sender,
            )
            return _FALLBACK_RESPONSE

        logger.info(
            "gmail_hermes_invoke_success",
            message_id=envelope.message_id,
            response_length=len(response_text),
        )

        return response_text

    # ------------------------------------------------------------------
    # LLM Classification
    # ------------------------------------------------------------------

    async def invoke_for_classification(
        self,
        envelope: GmailMessageEnvelope,
    ) -> dict[str, object] | None:
        """Classify an email via Hermes using the structured LLM prompt.

        Sends ``LLM_CLASSIFICATION_PROMPT`` (from :mod:`classifier`)
        formatted with envelope data and expects a JSON response with
        ``category`` and ``confidence`` keys.

        Parameters
        ----------
        envelope:
            The parsed inbound email envelope.

        Returns
        -------
        ``dict[str, object] | None``
            Parsed JSON dict with at least ``category`` (``str``) and
            ``confidence`` (``float``) keys, or ``None`` when the LLM
            is unavailable or the response cannot be parsed.
        """
        try:
            from .classifier import LLM_CLASSIFICATION_PROMPT

            body_trunc: str = (envelope.body_text or envelope.snippet or "")[:_MAX_BODY_CHARS]
            prompt: str = LLM_CLASSIFICATION_PROMPT.format(
                operator_name="Faiz",
                sender=envelope.sender,
                subject=envelope.subject or "(no subject)",
                body_truncation_chars=_MAX_BODY_CHARS,
                body_text=body_trunc,
            )

            hermes = self._hermes_getter()
            if hermes is None:
                raise GmailHermesUnavailable("get_adapter() returned None")

            response_text: str = await asyncio.wait_for(
                hermes.send_message(
                    user_id=f"classify:{envelope.sender}",
                    content=body_trunc,
                    system_prompt=prompt,
                ),
                timeout=_DEFAULT_TIMEOUT,
            )
        except (GmailHermesUnavailable, asyncio.TimeoutError):
            return None
        except Exception as exc:
            logger.error(
                "gmail_classification_hermes_error",
                message_id=envelope.message_id,
                error=str(exc),
            )
            return None

        # Parse JSON from response
        import json

        try:
            parsed: dict[str, object] = json.loads(response_text)
        except (json.JSONDecodeError, TypeError):
            # Try to find JSON in markdown code fences
            import re

            json_match = re.search(
                r"```(?:json)?\s*(\{.*?\})\s*```",
                response_text,
                re.DOTALL,
            )
            if json_match:
                try:
                    parsed = json.loads(json_match.group(1))
                except (json.JSONDecodeError, TypeError):
                    return None
            else:
                return None

        if not isinstance(parsed, dict):
            return None
        if "category" not in parsed:
            return None

        parsed["confidence"] = float(parsed.get("confidence", 0.5))
        parsed["category"] = str(parsed["category"]).lower().strip()
        logger.info(
            "gmail_classification_llm_result",
            message_id=envelope.message_id,
            category=parsed["category"],
            confidence=parsed["confidence"],
        )
        return parsed

    async def invoke_for_draft(
        self,
        envelope: GmailMessageEnvelope,
        thread_context: str | None = None,
        client_dossier: str | None = None,
    ) -> str:
        """Generate a draft reply via Hermes with extended context and timeout.

        This is a specialised variant of ``invoke()`` for draft generation.
        It adds draft-specific instructions to the system prompt (use
        GmailCompose-friendly HTML, professional tone, never expose AI
        identity) and uses a longer timeout (60s) to accommodate the
        additional token cost of HTML output.

        Parameters
        ----------
        envelope:
            The inbound email envelope to reply to.
        thread_context:
            Optional thread-history summary (plain text).  Truncated to
            ``_MAX_CONTEXT_CHARS``.
        client_dossier:
            Optional client-profile summary (plain text).  Truncated to
            ``_MAX_CONTEXT_CHARS``.

        Returns
        -------
        ``str``
            The generated draft HTML body, or a graceful fallback on
            timeout / error.
        """
        envelope.validate()
        category: str = envelope.classify().value

        system_prompt: str = self._build_draft_system_prompt(
            envelope=envelope,
            category=category,
            thread_context=thread_context,
            client_dossier=client_dossier,
        )

        user_id: str = f"draft:{envelope.sender}"
        body_content: str = envelope.body_text or envelope.snippet or ""

        try:
            hermes = self._hermes_getter()
            if hermes is None:
                raise GmailHermesUnavailable("get_adapter() returned None")
            response_text: str = await asyncio.wait_for(
                hermes.send_message(
                    user_id=user_id,
                    content=body_content,
                    system_prompt=system_prompt,
                ),
                timeout=_DRAFT_TIMEOUT,
            )
        except GmailHermesUnavailable:
            raise
        except asyncio.TimeoutError:
            logger.warning(
                "gmail_draft_hermes_timeout",
                message_id=envelope.message_id,
                thread_id=envelope.thread_id,
                timeout=_DRAFT_TIMEOUT,
            )
            return _FALLBACK_RESPONSE
        except Exception as exc:
            logger.error(
                "gmail_draft_hermes_error",
                message_id=envelope.message_id,
                thread_id=envelope.thread_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return _FALLBACK_RESPONSE

        if not response_text:
            logger.warning(
                "gmail_draft_hermes_empty_response",
                message_id=envelope.message_id,
                thread_id=envelope.thread_id,
            )
            return _FALLBACK_RESPONSE

        logger.info(
            "gmail_draft_hermes_success",
            message_id=envelope.message_id,
            thread_id=envelope.thread_id,
            response_length=len(response_text),
        )

        return response_text

    # ------------------------------------------------------------------
    # Context builder
    # ------------------------------------------------------------------

    def _build_email_context_dict(
        self,
        envelope: GmailMessageEnvelope,
        thread_history: str | None = None,
        client_dossier: str | None = None,
    ) -> dict[str, Any]:
        """Build a dict of email-specific context for system prompt injection.

        The returned dict contains the canonical fields used by
        ``_build_system_prompt`` and ``_build_draft_system_prompt``.

        Parameters
        ----------
        envelope:
            The inbound email envelope.
        thread_history:
            Optional thread-history summary.  ``None`` when unavailable.
        client_dossier:
            Optional client-profile summary.  ``None`` when unavailable.

        Returns
        -------
        ``dict[str, Any]``
            Keys: ``from_header``, ``subject``, ``category``,
            ``thread_history``, ``client_dossier``.
        """
        category: str = envelope.classify().value

        return {
            "from_header": envelope.sender,
            "subject": envelope.subject or "(no subject)",
            "category": category,
            "thread_history": thread_history,
            "client_dossier": client_dossier,
        }

    # ------------------------------------------------------------------
    # System-prompt builders
    # ------------------------------------------------------------------

    def _build_system_prompt(
        self,
        *,
        from_header: str,
        subject: str,
        category: str,
        thread_history: str | None = None,
        client_dossier: str | None = None,
    ) -> str:
        """Build a system prompt with email context for general processing.

        Assembles the base system prompt (with memory context) and appends
        an ``[EMAIL CONTEXT]`` block with the email metadata.

        Parameters
        ----------
        from_header:
            The sender's email address.
        subject:
            The email subject line.
        category:
            The classified email category.
        thread_history:
            Optional thread-history summary.
        client_dossier:
            Optional client-profile summary.

        Returns
        -------
        ``str``
            The assembled system prompt.
        """
        thread_history_section: str = ""
        if thread_history:
            truncated: str = thread_history[:_MAX_CONTEXT_CHARS]
            thread_history_section = f"Thread History:\n{truncated}\n"

        client_dossier_section: str = ""
        if client_dossier:
            truncated = client_dossier[:_MAX_CONTEXT_CHARS]
            client_dossier_section = f"Client Dossier:\n{truncated}\n"

        # Start with the base persona + memory prompt.
        base_prompt: str = get_system_prompt_with_context(memories=None, mood="Content")

        email_block: str = _EMAIL_SYSTEM_PROMPT_BLOCK.format(
            from_header=from_header,
            subject=subject,
            category=category,
            thread_history_section=thread_history_section,
            client_dossier_section=client_dossier_section,
        )

        return base_prompt + email_block

    def _build_draft_system_prompt(
        self,
        *,
        envelope: GmailMessageEnvelope,
        category: str,
        thread_context: str | None = None,
        client_dossier: str | None = None,
    ) -> str:
        """Build a system prompt tailored for draft-reply generation.

        Extends the base system prompt with both the ``[EMAIL CONTEXT]``
        block and the ``[DRAFT INSTRUCTIONS]`` block.  The draft
        instructions enforce professional tone, GmailCompose-friendly
        HTML, and strict AI-identity concealment.

        Parameters
        ----------
        envelope:
            The inbound email envelope.
        category:
            The classified email category.
        thread_context:
            Optional thread-history summary.
        client_dossier:
            Optional client-profile summary.

        Returns
        -------
        ``str``
            The assembled draft system prompt.
        """
        thread_history_section: str = ""
        if thread_context:
            truncated: str = thread_context[:_MAX_CONTEXT_CHARS]
            thread_history_section = f"Thread History:\n{truncated}\n"

        client_dossier_section: str = ""
        if client_dossier:
            truncated = client_dossier[:_MAX_CONTEXT_CHARS]
            client_dossier_section = f"Client Dossier:\n{truncated}\n"

        # Start with the base persona + memory prompt.
        base_prompt: str = get_system_prompt_with_context(memories=None, mood="Content")

        email_block: str = _EMAIL_SYSTEM_PROMPT_BLOCK.format(
            from_header=envelope.sender,
            subject=envelope.subject or "(no subject)",
            category=category,
            thread_history_section=thread_history_section,
            client_dossier_section=client_dossier_section,
        )

        return base_prompt + email_block + _DRAFT_SYSTEM_PROMPT_BLOCK


__all__ = [
    "GmailHermesBridge",
    "GmailHermesUnavailable",
    "GmailHermesTimeout",
    "GmailHermesRefusal",
    "GmailHermesClassificationError",
]
