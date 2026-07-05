"""Async file log writer with 60-second coalesced flushing.

Buffers log entries in memory and flushes them to disk either on demand or
automatically every 60 seconds.  When the log file grows beyond ``max_lines``
the file is rotated, keeping up to three numbered backups.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Sequence
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


class LogWriter:
    """Coalesced async file log writer.

    Entries are buffered in memory and flushed to ``output_path`` either when
    :meth:`flush` is called or automatically every ``flush_interval_seconds``
    seconds.  Multiple entries written within the same flush window are
    batched into a single disk write.

    Args:
        output_path: File path where log entries are written.
        max_lines: Maximum number of lines to keep in the active log file
            before rotating.  Defaults to ``10000``.
        flush_interval_seconds: Interval between automatic flushes in
            seconds.  Defaults to ``60.0``.
    """

    def __init__(
        self,
        output_path: str | os.PathLike[str],
        max_lines: int = 10000,
        *,
        flush_interval_seconds: float = 60.0,
    ) -> None:
        self.output_path = Path(output_path)
        self.max_lines = max_lines
        self.flush_interval_seconds = flush_interval_seconds
        self._buffer: list[str] = []
        self._lock = asyncio.Lock()
        self._flush_task: asyncio.Task[None] | None = None
        self._stopped = False

    async def write(self, entry: str) -> None:
        """Buffer a log entry for the next flush.

        Args:
            entry: Log entry to buffer.

        Raises:
            RuntimeError: If :meth:`stop` has already been called.
        """
        if self._stopped:
            raise RuntimeError("LogWriter is stopped")
        async with self._lock:
            self._buffer.append(entry)
        await self._ensure_flush_task()

    async def _ensure_flush_task(self) -> None:
        """Start the periodic flush task if it is not already running."""
        if self._flush_task is not None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self._flush_task = loop.create_task(self._flush_loop())

    async def _flush_loop(self) -> None:
        """Periodically flush buffered entries to disk."""
        while True:
            await asyncio.sleep(self.flush_interval_seconds)
            try:
                await self.flush()
            except Exception as exc:
                # Keep the flush loop alive even if an individual flush fails.
                # Errors are surfaced to callers that invoke flush() directly.
                logger.warning("log_writer_auto_flush_failed", error=str(exc))
                continue

    async def flush(self) -> None:
        """Write all buffered entries to disk immediately."""
        async with self._lock:
            if not self._buffer:
                return
            entries = self._buffer
            self._buffer = []
        await self._write_entries(entries)

    async def _write_entries(self, entries: Sequence[str]) -> None:
        """Persist ``entries`` to ``output_path``, rotating if necessary."""
        lines = [entry.strip() for entry in entries if entry.strip()]
        if not lines:
            return

        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        existing_lines: list[str] = []
        if self.output_path.exists():
            existing_text = self.output_path.read_text(encoding="utf-8")
            existing_lines = existing_text.splitlines()

        total_lines = existing_lines + lines
        if len(total_lines) > self.max_lines:
            if self.output_path.exists():
                self._rotate_files()
            total_lines = lines

        self.output_path.write_text("\n".join(total_lines) + "\n", encoding="utf-8")

    def _rotate_files(self) -> None:
        """Rotate the active log file, keeping up to three backups."""
        def rotated(i: int) -> Path:
            return self.output_path.with_name(f"{self.output_path.name}.{i}")

        oldest = rotated(3)
        if oldest.exists():
            oldest.unlink()

        for i in range(2, 0, -1):
            older = rotated(i)
            newer = rotated(i + 1)
            if older.exists():
                older.rename(newer)

        rotated_one = rotated(1)
        self.output_path.rename(rotated_one)

    async def stop(self) -> None:
        """Stop the periodic flush task and flush any remaining entries."""
        self._stopped = True
        if self._flush_task is not None:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None
        await self.flush()
