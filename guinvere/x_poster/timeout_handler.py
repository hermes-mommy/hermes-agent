"""P13 X Auto Poster — Per-action timeout handler with graceful degradation."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import TypeVar

import structlog

from .exceptions import XApiConnectionError, XPosterError

_logger = structlog.get_logger(__name__)

T = TypeVar("T")


@dataclass
class TimeoutConfig:
    """Timeout configuration for various async operations."""

    x_api_connect: float = 30.0
    x_api_upload: float = 120.0
    x_api_post: float = 60.0
    caption_generation: float = 45.0
    moderation_check: float = 30.0
    db_operation: float = 10.0


class TimeoutHandler:
    """Wraps async operations with configurable timeouts and graceful degradation."""

    _config: TimeoutConfig

    def __init__(self, config: TimeoutConfig | None = None) -> None:
        self._config = config or TimeoutConfig()

    async def with_timeout(
        self,
        coro: Awaitable[T],
        timeout_seconds: float,
        action_name: str,
    ) -> T:
        """Wrap a coroutine with a timeout."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout_seconds)
        except asyncio.TimeoutError as exc:
            _logger.warning(
                "timeout_handler.timeout",
                action=action_name,
                timeout_seconds=timeout_seconds,
            )
            if action_name.startswith("x_api_"):
                raise XApiConnectionError(
                    f"{action_name} timed out after {timeout_seconds}s"
                ) from exc
            raise XPosterError(f"{action_name} timed out after {timeout_seconds}s") from exc
        except asyncio.CancelledError:
            _logger.warning("timeout_handler.cancelled", action=action_name)
            raise
        except Exception:
            _logger.error("timeout_handler.error", action=action_name, exc_info=True)
            raise

    async def timeout_x_api_connect(self, coro: Awaitable[T]) -> T:
        """Timeout wrapper for X API connection."""
        return await self.with_timeout(coro, self._config.x_api_connect, "x_api_connect")

    async def timeout_x_api_upload(self, coro: Awaitable[T]) -> T:
        """Timeout wrapper for X API media upload."""
        return await self.with_timeout(coro, self._config.x_api_upload, "x_api_upload")

    async def timeout_x_api_post(self, coro: Awaitable[T]) -> T:
        """Timeout wrapper for X API post action."""
        return await self.with_timeout(coro, self._config.x_api_post, "x_api_post")

    async def timeout_caption_generation(self, coro: Awaitable[T]) -> T:
        """Timeout wrapper for caption generation."""
        return await self.with_timeout(coro, self._config.caption_generation, "caption_generation")

    async def timeout_moderation(self, coro: Awaitable[T]) -> T:
        """Timeout wrapper for content moderation."""
        return await self.with_timeout(coro, self._config.moderation_check, "moderation_check")

    async def timeout_db(self, coro: Awaitable[T]) -> T:
        """Timeout wrapper for database operations."""
        return await self.with_timeout(coro, self._config.db_operation, "db_operation")
