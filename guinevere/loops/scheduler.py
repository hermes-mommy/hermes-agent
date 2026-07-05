"""Loop Scheduler — cron-based scheduling for daily rituals and maintenance.

Uses APScheduler v3 AsyncIOScheduler to trigger loops at configured times.
"""

from __future__ import annotations

import asyncio

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from guinevere.loops.manager import LoopManager

logger = structlog.get_logger()

_DEFAULT_TIMEZONE = "Asia/Bangkok"


class LoopScheduler:
    """Cron-based loop scheduler for daily rituals and maintenance."""

    def __init__(self, manager: LoopManager | None = None) -> None:
        self.scheduler = AsyncIOScheduler(timezone=_DEFAULT_TIMEZONE)
        self.manager = manager if manager is not None else LoopManager()
        self._job_counter: int = 0

        logger.info(
            "loop_scheduler.initialized",
            timezone=_DEFAULT_TIMEZONE,
            external_manager=manager is not None,
        )

    def add_daily_ritual(
        self, hour: int, minute: int, task: str, goal: str
    ) -> str:
        """Schedule a daily loop at the given time.

        Args:
            hour: Hour of day (0-23) in configured timezone.
            minute: Minute of hour (0-59).
            task: Task description for the loop.
            goal: Goal the loop should achieve.

        Returns:
            The generated job_id.
        """
        self._job_counter += 1
        job_id = f"ritual-{self._job_counter:04d}"

        self.scheduler.add_job(
            func=self._trigger_loop,
            trigger="cron",
            hour=hour,
            minute=minute,
            args=[task, goal],
            id=job_id,
            name=f"Daily Ritual: {task}",
            replace_existing=True,
        )

        logger.info(
            "loop_scheduler.ritual_added",
            job_id=job_id,
            hour=hour,
            minute=minute,
            task=task,
            goal=goal,
        )

        return job_id

    def remove_job(self, job_id: str) -> None:
        """Remove a scheduled job.

        Args:
            job_id: The job to remove.
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info("loop_scheduler.job_removed", job_id=job_id)
        except Exception as exc:
            logger.warning(
                "loop_scheduler.job_remove_failed",
                job_id=job_id,
                error=str(exc),
            )
            raise

    def list_jobs(self) -> list[dict[str, object]]:
        """List all scheduled jobs.

        Returns:
            List of dicts with job_id, name, next_run_time, and trigger info.
        """
        jobs = self.scheduler.get_jobs()
        result = []

        for job in jobs:
            result.append(
                {
                    "job_id": job.id,
                    "name": job.name,
                    "next_run_time": (
                        job.next_run_time.isoformat()
                        if job.next_run_time
                        else None
                    ),
                    "trigger": str(job.trigger),
                }
            )

        logger.debug(
            "loop_scheduler.jobs_listed",
            count=len(result),
        )

        return result

    def start(self) -> None:
        """Start the scheduler."""
        self.scheduler.start()
        logger.info("loop_scheduler.started")

    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        self.scheduler.shutdown(wait=False)
        logger.info("loop_scheduler.stopped")

    async def _trigger_loop(self, task: str, goal: str) -> None:
        """Internal: trigger a new loop from a scheduled job.

        Args:
            task: Task description for the loop.
            goal: Goal the loop should achieve.
        """
        logger.info(
            "loop_scheduler.triggering_loop",
            task=task,
            goal=goal,
        )

        try:
            loop_id = await self.manager.start_loop(task=task, goal=goal)
            logger.info(
                "loop_scheduler.loop_triggered",
                loop_id=loop_id,
                task=task,
            )
        except Exception as exc:
            logger.error(
                "loop_scheduler.trigger_failed",
                task=task,
                error=str(exc),
            )


async def main() -> None:
    """Entry point for running the scheduler as a standalone service."""
    scheduler = LoopScheduler()
    scheduler.start()

    logger.info("loop_scheduler.service_started")

    try:
        # Keep the service running until interrupted.
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("loop_scheduler.service_stopping")
    finally:
        scheduler.stop()
        logger.info("loop_scheduler.service_stopped")


if __name__ == "__main__":
    asyncio.run(main())
