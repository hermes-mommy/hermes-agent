"""Consciousness Loop — ADR-063 composite 7-substrate architecture.

Owns one asyncio.Task per substrate, runs them concurrently, and
provides lifecycle hooks (on_session_start / on_session_end) for
the W4 server lifespan to call.

Design decisions:
  - Per-substrate try/except (r04 §7: TaskGroup propagates CancelledError).
  - Each substrate runs in its own asyncio.Task (not inside the TaskGroup
    directly) so that one substrate crashing does not kill siblings.
  - MockLLMRouter for all self-prompting (D3).
  - Config from agent._guinevere_settings.consciousness (fail-soft).
  - Pydantic v2 / async/await throughout.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

import guinevere.consciousness.prompts as _prompts_module
from guinevere.consciousness.state import ConsciousnessState, SubstrateStatus
from guinevere.consciousness.substrates import (
    substrate_active_cognition,
    substrate_dreaming,
    substrate_emotion_driven,
    substrate_heartbeat,
    substrate_metacognition,
    substrate_reflection,
    substrate_strategic_planning,
)
from guinevere.consciousness.substrate_registry import build_registry

import structlog

logger = structlog.get_logger("guinevere.consciousness")

# Default substrate names — must be exactly 7 (ADR-063).
SUBSTRATE_NAMES: list[str] = [
    "heartbeat",
    "active_cognition",
    "reflection",
    "strategic_planning",
    "dreaming",
    "metacognition",
    "emotion_driven",
]


class ConsciousnessLoop:
    """7-substrate consciousness loop per ADR-063.

    Lifecycle:
      1. Construct with ``llm_router`` (MockLLMRouter for D3) and optional
         ``settings`` (fail-soft if ``None``).
      2. Call ``on_session_start()`` to initialise state.
      3. Call ``run()`` — spawns 7 substrate tasks and blocks until shutdown.
      4. Call ``on_session_end()`` to flush journals and persist state.
    """

    def __init__(
        self,
        llm_router: Any | None = None,
        settings: Any | None = None,
    ) -> None:
        self._llm_router = llm_router
        self._settings = settings
        self._state = ConsciousnessState()
        self._shutdown_event = asyncio.Event()
        self._tasks: list[asyncio.Task[None]] = []
        self._session_active = False

        # Expose for substrates.py (which accesses self._prompts).
        self._prompts = _prompts_module

        # Expose SubstrateStatus enum for substrates.
        self._SubstrateStatus = SubstrateStatus

        # Build the substrate registry.
        self._registry = build_registry(self)

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

        logger.info(
            "consciousness_loop.initialized",
            substrate_count=len(self._registry),
            has_llm_router=llm_router is not None,
            has_settings=settings is not None,
        )

    # ── public properties ───────────────────────────────────

    @property
    def substrate_names(self) -> list[str]:
        """Return the list of substrate names (always 7)."""
        return list(self._registry.keys())

    @property
    def state(self) -> ConsciousnessState:
        """Return the mutable consciousness state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Return True if the loop is actively running."""
        return self._session_active and not self._shutdown_event.is_set()

    # ── lifecycle hooks ─────────────────────────────────────

    def on_session_start(self, session_id: str | None = None) -> None:
        """Called when a new session begins.

        Initialises the affect vector, loads self_story, resets state.
        """
        self._state.started_at = datetime.now(timezone.utc)
        self._state.session_id = session_id or uuid.uuid4().hex[:12]
        self._session_active = True
        self._shutdown_event.clear()

        # Reset substrate statuses.
        for name in SUBSTRATE_NAMES:
            self._state.set_substrate_status(name, SubstrateStatus.IDLE)

        logger.info(
            "consciousness.session_started",
            session_id=self._state.session_id,
        )

    def on_session_end(self) -> None:
        """Called when the session ends.

        Flushes dream journal, persists affect state, checkpoints
        consciousness state.  Signals all substrates to stop.
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
        """Spawn all 7 substrate tasks and block until shutdown.

        Each substrate runs in its own asyncio.Task with per-substrate
        failure isolation (try/except).  This method itself runs inside
        the W4 lifespan TaskGroup — when cancelled, it signals all
        substrates to stop and awaits their completion.
        """
        if not self._session_active:
            self.on_session_start()

        logger.info("consciousness.run_starting", substrates=list(self._registry.keys()))

        # Spawn one task per substrate.
        for name, coroutine_fn in self._registry.items():
            task = asyncio.create_task(
                self._run_substrate(name, coroutine_fn),
                name=f"substrate-{name}",
            )
            self._tasks.append(task)

        logger.info("consciousness.all_substrates_spawned", count=len(self._tasks))

        # Block until shutdown signal or cancellation.
        try:
            # Wait for the shutdown event or for all tasks to complete.
            # Using asyncio.Event.wait() ensures we block until the
            # lifespan cancels us or on_session_end() sets the event.
            done_event = asyncio.Event()

            # Watch for all tasks finishing (should not happen normally).
            async def _watch_tasks() -> None:
                if self._tasks:
                    await asyncio.gather(*self._tasks, return_exceptions=True)
                done_event.set()

            watcher = asyncio.create_task(_watch_tasks())

            # Wait for either shutdown signal or all tasks completing.
            shutdown_waiter = asyncio.create_task(self._shutdown_event.wait())
            await asyncio.wait(
                [shutdown_waiter, watcher],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel the watcher if shutdown was signalled.
            if not watcher.done():
                watcher.cancel()
            if not shutdown_waiter.done():
                shutdown_waiter.cancel()

        except asyncio.CancelledError:
            logger.info("consciousness.run_cancelled")
            self._shutdown_event.set()
            # Cancel all substrate tasks.
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            # Wait for them to finish cleanup.
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            raise

        finally:
            self._tasks.clear()
            logger.info("consciousness.run_exited")

    # ── substrate runner (failure isolation) ────────────────

    async def _run_substrate(
        self,
        name: str,
        coroutine_fn: Any,
    ) -> None:
        """Run a single substrate with per-substrate failure isolation.

        If the substrate raises (non-CancelledError), it is logged and
        the substrate is marked FAILED — but siblings continue running.

        Note: coroutine_fn is a functools.partial-bound callable that
        already has the loop instance bound — call with no arguments.
        """
        logger.debug("substrate.starting", name=name)
        try:
            await coroutine_fn()
        except asyncio.CancelledError:
            logger.debug("substrate.cancelled", name=name)
            raise
        except Exception as e:
            logger.exception("substrate.failed", name=name, error=str(e))
            self._state.set_substrate_status(name, SubstrateStatus.FAILED)
        finally:
            logger.debug("substrate.exited", name=name)
