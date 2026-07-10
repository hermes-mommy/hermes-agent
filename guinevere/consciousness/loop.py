"""Consciousness Loop — unified thought-stream architecture.

Replaces the 7-substrate pattern (ADR-063) with a single ThoughtStream
that generates thoughts sequentially.  The loop provides lifecycle hooks
(on_session_start / on_session_end) and delegates all thought generation
to ThoughtStream.

Design decisions:
  - Single asyncio.Task for the ThoughtStream (not 7 tasks).
  - Shutdown via asyncio.Event (same pattern as before).
  - ConsciousnessState shared between loop and stream.
  - AffectVector from state.py influences thought type selection.
  - HARD STOP check at start of each thought cycle.
  - No asyncio.sleep in thought generation — natural flow.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from guinevere.consciousness.state import ConsciousnessState
from guinevere.consciousness.thought import Thought, ThoughtType
from guinevere.consciousness.thought_stream import ThoughtStream

import structlog

logger = structlog.get_logger("guinevere.consciousness")

# Thought type names — the 6 consciousness modes.
THOUGHT_TYPE_NAMES: list[str] = [t.value for t in ThoughtType]


class ConsciousnessLoop:
    """Unified consciousness loop delegating to ThoughtStream.

    Lifecycle:
      1. Construct with ``llm_router`` (a real Hermes AIAgent via 9router)
         and optional ``settings`` (fail-soft if ``None``).
      2. Call ``on_session_start()`` to initialise state.
      3. Call ``run()`` — spawns the ThoughtStream task and blocks until shutdown.
      4. Call ``on_session_end()`` to flush journals and persist state.
    """

    def __init__(
        self,
        llm_router: Any | None = None,
        settings: Any | None = None,
        redis_client: Any | None = None,
    ) -> None:
        self._llm_router = llm_router
        self._settings = settings
        self._redis_client = redis_client
        self._state = ConsciousnessState()
        self._shutdown_event = asyncio.Event()
        self._stream_task: asyncio.Task[None] | None = None
        self._session_active = False

        # Read config from settings (fail-soft).
        self._config: dict[str, Any] = {}
        if settings is not None:
            consciousness_cfg = getattr(settings, "consciousness", None)
            if consciousness_cfg is not None:
                if isinstance(consciousness_cfg, dict):
                    self._config = consciousness_cfg
                else:
                    # Pydantic model — try .model_dump() then fall back.
                    dump = getattr(consciousness_cfg, "model_dump", None)
                    if callable(dump):
                        self._config = dump()
                    else:
                        self._config = vars(consciousness_cfg)

        # Build the ThoughtStream.
        self._stream = ThoughtStream(
            llm_router=self._llm_router,
            state=self._state,
            shutdown_event=self._shutdown_event,
            config=self._config,
            redis_client=self._redis_client,
        )

        logger.info(
            "consciousness_loop.initialized",
            has_llm_router=llm_router is not None,
            has_settings=settings is not None,
        )

    # ── public properties ───────────────────────────────────

    @property
    def state(self) -> ConsciousnessState:
        """Return the mutable consciousness state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Return True if the loop is actively running."""
        return self._session_active and not self._shutdown_event.is_set()

    @property
    def thought_stream(self) -> ThoughtStream:
        """Return the ThoughtStream instance."""
        return self._stream

    # ── lifecycle hooks ─────────────────────────────────────

    def on_session_start(self, session_id: str | None = None) -> None:
        """Called when a new session begins.

        Initialises the affect vector, loads self_story, resets state.
        """
        self._state.started_at = datetime.now(timezone.utc)
        self._state.session_id = session_id or uuid.uuid4().hex[:12]
        self._session_active = True
        self._shutdown_event.clear()

        logger.info(
            "consciousness.session_started",
            session_id=self._state.session_id,
        )

    def on_session_end(self) -> None:
        """Called when the session ends.

        Flushes dream journal, persists affect state, checkpoints
        consciousness state.  Signals the thought stream to stop.
        """
        self._shutdown_event.set()
        self._session_active = False

        logger.info(
            "consciousness.session_ended",
            session_id=self._state.session_id,
            dream_count=len(self._state.dream_journal),
            thought_count=len(self._state._thoughts),
        )

    # ── main run loop ───────────────────────────────────────

    async def run(self) -> None:
        """Run the ThoughtStream and block until shutdown.

        Delegates to ThoughtStream.run() in a single asyncio.Task.
        This method itself runs inside the W4 lifespan TaskGroup —
        when cancelled, it signals the stream to stop and awaits
        completion.
        """
        if not self._session_active:
            self.on_session_start()

        logger.info("consciousness.run_starting")

        # Spawn the ThoughtStream as a single task.
        self._stream_task = asyncio.create_task(
            self._stream.run(),
            name="thought-stream",
        )

        logger.info("consciousness.thought_stream_spawned")

        try:
            # Wait for either shutdown signal or stream completion.
            shutdown_waiter = asyncio.create_task(self._shutdown_event.wait())
            await asyncio.wait(
                [shutdown_waiter, self._stream_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel the waiter if stream finished first.
            if not shutdown_waiter.done():
                shutdown_waiter.cancel()

        except asyncio.CancelledError:
            logger.info("consciousness.run_cancelled")
            self._shutdown_event.set()
            if self._stream_task and not self._stream_task.done():
                self._stream_task.cancel()
            if self._stream_task:
                await asyncio.gather(self._stream_task, return_exceptions=True)
            raise

        finally:
            self._stream_task = None
            logger.info("consciousness.run_exited")
