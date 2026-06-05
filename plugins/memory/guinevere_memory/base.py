"""Local MemoryProvider stub for development when Hermes Agent is not installed.

This stub mirrors the ``agent.memory_provider.MemoryProvider`` abstract base
class interface. The ``__init__.py`` entry point imports conditionally:
the real ``agent.memory_provider.MemoryProvider`` when available, otherwise
this local stub.

All method signatures match the Hermes Agent v0.2.0+ MemoryProvider ABC.
Subclasses MUST override every abstract method.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MemoryProvider(ABC):
    """Abstract base class for Hermes Agent external memory plugins.

    Provides the full interface expected by ``agent.memory_manager.MemoryManager``.
    Concrete plugins inherit from this class (or the canonical upstream version)
    and register via ``ctx.register_memory_provider()``.
    """

    # ------------------------------------------------------------------
    # Required methods
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier. Must be unique across all memory providers.

        Example: ``"guinevere-memory"``
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the provider can activate.

        MUST NOT make network calls, query databases, or perform file I/O.
        Use environment-variable existence checks or local file existence.
        """
        ...

    @abstractmethod
    def initialize(self, session_id: str, **kwargs: Any) -> None:
        """Called once at agent start. Store configuration.

        ``kwargs`` always includes ``hermes_home`` (str) for profile-isolated
        storage paths.
        """
        ...

    @abstractmethod
    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI function-calling format schemas for tools exposed to the LLM.

        Return empty list if the provider has no tools.
        """
        ...

    @abstractmethod
    def handle_tool_call(
        self, name: str, args: dict[str, Any], **kwargs: Any
    ) -> str:
        """Dispatch and handle tool calls. Must return a JSON-formatted result string.

        Return a JSON error object if no tools are registered.
        """
        ...

    @abstractmethod
    def get_config_schema(self) -> list[dict[str, Any]]:
        """Declare config fields for the ``hermes memory setup`` wizard.

        Each dict may contain: key, description, secret, required, env_var, default, choices.
        """
        ...

    @abstractmethod
    def save_config(self, values: dict[str, Any], hermes_home: str) -> None:
        """Write non-secret config to native location.

        Secret fields are handled separately (written to ``$HERMES_HOME/.env``).
        This method receives only non-secret fields.
        """
        ...

    # ------------------------------------------------------------------
    # Optional lifecycle hooks (default no-op implementations)
    # ------------------------------------------------------------------

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Called before each API call. Return context string to inject into user message.

        Default: no-op, returns empty string.
        """
        _ = (query, session_id)
        return ""

    def queue_prefetch(self, query: str) -> None:
        """Called after each turn to pre-warm background recall.

        Default: no-op.
        """
        _ = query

    def sync_turn(
        self, user: str, assistant: str, *, session_id: str = ""
    ) -> None:
        """Called after each completed turn to persist conversation.

        MUST be non-blocking (use daemon threads for I/O). Default: no-op.
        """
        _ = (user, assistant, session_id)

    def on_session_end(self, messages: list[Any]) -> None:
        """Called when the conversation ends. Final flush, summary retention.

        Default: no-op.
        """
        _ = messages

    def on_pre_compress(self, messages: list[Any]) -> str:
        """Called before context compression. Save insights before they are discarded.

        Returns a summary string. Default: no-op.
        """
        _ = messages
        return ""

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Mirror built-in MEMORY.md/USER.md writes to external backend.

        Default: no-op.
        """
        _ = (action, target, content, metadata)

    def system_prompt_block(self) -> str:
        """Return a short description of provider capabilities for the system prompt.

        Default: empty string.
        """
        return ""

    def shutdown(self) -> None:
        """Called at process exit. Clean up connections, close DBs, flush buffers.

        Default: no-op.
        """