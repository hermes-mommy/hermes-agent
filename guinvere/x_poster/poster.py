"""P13 X Auto Poster — Post executor using Official X API v2 client."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog

from .metrics import observe_post_duration, record_post

if TYPE_CHECKING:
    from .queue_manager import QueueManager
    from .x_api_client import XApiClient

_logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PostResult:
    """Result of post execution pipeline."""

    success: bool
    tweet_id: str | None = None
    tweet_url: str | None = None
    post_url: str | None = None
    error: str | None = None
    duration_seconds: float = 0.0


class XPoster:
    """Thin post executor around XApiClient with DB state updates."""

    def __init__(self, x_api: XApiClient | Any, queue_mgr: QueueManager, db: Any | None = None) -> None:
        self._x_api = x_api
        self._queue_mgr = queue_mgr
        self._db = db

    async def execute_post_batch(self, post_batch: list[tuple[UUID, str]], caption: str) -> PostResult:
        """Publish a batch of posts (up to 4 media) as a single tweet."""
        start_time = time.monotonic()
        post_ids = [p[0] for p in post_batch]
        media_paths = [p[1] for p in post_batch if p[1]]

        try:
            for post_id in post_ids:
                await self._queue_mgr.update_state(post_id, "in_progress")

            result = await self._x_api.post_media(media_paths, None)
            duration = time.monotonic() - start_time
            tweet_id = str(result.get("tweet_id") or "")
            tweet_url = str(result.get("tweet_url") or "")

            for post_id in post_ids:
                await self._queue_mgr.update_state(post_id, "completed", post_url=tweet_url)
                if tweet_id and self._db is not None:
                    try:
                        await self._db.execute(
                            "UPDATE p13_posts SET tweet_id = $1 WHERE id = $2",
                            tweet_id,
                            post_id,
                        )
                    except Exception as exc:
                        _logger.warning(
                            "x_poster.poster.tweet_id_store_failed",
                            post_id=str(post_id),
                            tweet_id=tweet_id,
                            error=str(exc),
                        )

            record_post("success")
            observe_post_duration(duration)
            _logger.info(
                "x_poster.poster.post_completed",
                post_ids=[str(pid) for pid in post_ids],
                tweet_id=tweet_id,
                tweet_url=tweet_url,
                media_count=len(media_paths),
                duration_seconds=round(duration, 2),
            )
            return PostResult(
                success=True,
                tweet_id=tweet_id,
                tweet_url=tweet_url,
                post_url=tweet_url,
                duration_seconds=duration,
            )
        except Exception as exc:
            duration = time.monotonic() - start_time
            for post_id in post_ids:
                await self._queue_mgr.update_state(post_id, "failed", last_error=str(exc))
            record_post("failed")
            observe_post_duration(duration)
            _logger.error(
                "x_poster.poster.post_failed",
                post_ids=[str(pid) for pid in post_ids],
                error=str(exc),
                duration_seconds=round(duration, 2),
            )
            return PostResult(success=False, error=str(exc), duration_seconds=duration)

    async def execute_post(self, post_id: UUID, caption: str, media_paths: list[str]) -> PostResult:
        """Publish a single post (backward compatibility)."""
        return await self.execute_post_batch([(post_id, media_paths[0] if media_paths else "")], caption)


async def execute_post(
    post_id: UUID,
    media_path: str,
    caption: str | None,
    x_api: XApiClient,
    queue_mgr: QueueManager,
) -> dict[str, Any]:
    """Simple async function wrapper for one-shot post execution."""
    poster = XPoster(x_api, queue_mgr)
    result = await poster.execute_post(post_id, caption or "", [media_path] if media_path else [])
    return {
        "ok": result.success,
        "tweet_id": result.tweet_id or "",
        "tweet_url": result.tweet_url or "",
        "error": result.error or "",
    }


__all__ = ["PostResult", "XPoster", "execute_post"]
