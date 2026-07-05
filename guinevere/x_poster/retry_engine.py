"""P13 X Auto Poster — Failed post rescheduling engine."""

from __future__ import annotations

from uuid import UUID

import structlog

from .exceptions import SessionExpiredError, XPosterError
from .metrics import record_post
from .queue_manager import QueueManager
from .schedule_manager import ScheduleManager

_logger = structlog.get_logger(__name__)


class RetryEngine:
    """Handles failed post rescheduling to the next available schedule slot."""

    _queue: QueueManager
    _schedule: ScheduleManager
    _max_attempts: int

    def __init__(
        self,
        queue: QueueManager,
        schedule: ScheduleManager,
        max_attempts: int = 3,
    ) -> None:
        self._queue = queue
        self._schedule = schedule
        self._max_attempts = max_attempts

    async def handle_failure(self, post_id: UUID, error: Exception) -> str:
        """Handle a post failure by determining the next action.

        Args:
            post_id: The UUID of the failed post.
            error: The exception that caused the failure.

        Returns:
            'failed' if max attempts reached, 'held' if session expired, 'retried' otherwise.
        """
        try:
            post = await self._queue.get_post(post_id)
            if not post:
                _logger.warning("retry_engine.post_not_found", post_id=str(post_id))
                return "failed"

            attempts = post.get("attempts", 0) + 1

            if attempts >= self._max_attempts:
                await self._queue.update_state(post_id, "failed")
                _logger.error(
                    "retry_engine.max_attempts_reached",
                    post_id=str(post_id),
                    attempts=attempts,
                    error=str(error),
                )
                record_post("failed")
                return "failed"

            if isinstance(error, SessionExpiredError):
                await self._queue.update_state(post_id, "held")
                _logger.warning(
                    "retry_engine.session_expired_held",
                    post_id=str(post_id),
                    attempts=attempts,
                )
                record_post("held")
                return "held"

            await self._queue.increment_attempts(post_id)
            
            media_type = str(post.get("media_type", "photo"))
            new_slot = await self._schedule.assign_next_slot(post_id)
            
            await self._queue.update_state(post_id, "scheduled")
            _logger.info(
                "retry_engine.rescheduled",
                post_id=str(post_id),
                attempts=attempts,
                new_slot=str(new_slot),
                error=str(error),
            )
            record_post("retried")
            return "retried"

        except XPosterError:
            raise
        except Exception as e:
            _logger.error(
                "retry_engine.handle_failure_error",
                post_id=str(post_id),
                error=str(e),
                exc_info=True,
            )
            raise XPosterError(f"Failed to handle post failure: {e}") from e

    async def retry_held_posts(self) -> int:
        """Find all 'held' posts and attempt to reschedule them.

        Returns:
            The number of posts successfully rescheduled.
        """
        try:
            held_posts = await self._queue.list_posts(state="held")
            rescheduled_count = 0

            for post in held_posts:
                post_id = post["id"]
                try:
                    media_type = str(post.get("media_type", "photo"))
                    new_slot = await self._schedule.assign_next_slot(post_id)
                    await self._queue.update_state(post_id, "scheduled")
                    _logger.info(
                        "retry_engine.held_post_rescheduled",
                        post_id=str(post_id),
                        new_slot=str(new_slot),
                    )
                    rescheduled_count += 1
                except Exception as e:
                    _logger.warning(
                        "retry_engine.held_post_retry_failed",
                        post_id=str(post_id),
                        error=str(e),
                    )

            _logger.info(
                "retry_engine.retry_held_completed",
                rescheduled_count=rescheduled_count,
                total_held=len(held_posts),
            )
            return rescheduled_count

        except XPosterError:
            raise
        except Exception as e:
            _logger.error(
                "retry_engine.retry_held_error",
                error=str(e),
                exc_info=True,
            )
            raise XPosterError(f"Failed to retry held posts: {e}") from e
