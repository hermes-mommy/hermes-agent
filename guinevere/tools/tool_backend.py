"""M8 Unified Tool Backend ABC — convergence of P22 adapters + P23 executors.

Single interface for all 9 backends. Risk labels are L1-L3 only (L4 deleted
per ADR-062 — no consent gate, no HARD STOP in the executor layer).

UUID v7 + SHA-256 hash-chain audit on every dispatch. Durable queue is
PG + Redis DB6 (fail-soft D2 — no live PG/Redis means no crash).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Risk labels — L1-L3 only.  L4 DELETED per ADR-062.
# ---------------------------------------------------------------------------


class ActionTier(Enum):
    """Risk tiers for tool actions.  L4 does not exist."""

    L1_READ = "L1"
    L2_WRITE = "L2"
    L3_DESTRUCTIVE = "L3"


# ---------------------------------------------------------------------------
# Action descriptor
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Action:
    """Immutable descriptor of a single backend action."""

    name: str
    label: ActionTier
    schema: dict[str, Any] = field(default_factory=dict)
    handler: str = ""  # method name on the backend, default = action name
    description: str = ""


# ---------------------------------------------------------------------------
# Audit record
# ---------------------------------------------------------------------------


@dataclass
class AuditRecord:
    """Audit entry produced on every dispatch.  UUID v7 + SHA-256 chain."""

    action_id: str  # UUID v7 hex
    timestamp: str  # ISO-8601 UTC
    backend: str
    action: str
    label: str  # L1/L2/L3
    ok: bool
    duration_ms: float
    hash_chain: str  # SHA-256 of this record, chained to previous
    error: str | None = None
    output: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Hash-chain helper
# ---------------------------------------------------------------------------

_prev_hash: str = hashlib.sha256(b"genesis").hexdigest()


def _compute_chain_hash(record_payload: str) -> str:
    """Compute SHA-256 of *record_payload* chained to the previous hash."""
    global _prev_hash
    combined = f"{_prev_hash}|{record_payload}"
    h = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    _prev_hash = h
    return h


# ---------------------------------------------------------------------------
# Durable queue (fail-soft D2)
# ---------------------------------------------------------------------------


class _DurableQueue:
    """Best-effort durable queue backed by PG + Redis DB6.

    D2: if neither PG nor Redis is reachable the queue silently drops (no
    crash, no raise).  Callers always get an ``ok`` acknowledgment.
    """

    def __init__(self) -> None:
        self._pg_conn: Any | None = None
        self._redis: Any | None = None

    async def enqueue(self, record: AuditRecord) -> bool:
        """Best-effort enqueue.  Returns True if persisted."""
        # Try Redis first (fast path)
        try:
            import redis.asyncio as aioredis

            if self._redis is None:
                self._redis = aioredis.from_url(
                    "redis://localhost:6379/6", decode_responses=True
                )
            await self._redis.lpush(
                "tool_audit_queue", json.dumps(record.__dict__, default=str)
            )
            return True
        except Exception:
            self._redis = None

        # Try PG (slow path)
        try:
            import asyncpg

            if self._pg_conn is None:
                self._pg_conn = await asyncpg.connect(
                    dsn="postgresql://localhost:5432/guinevere"
                )
            await self._pg_conn.execute(
                """
                INSERT INTO tool_audit_queue
                    (action_id, timestamp, backend, action, label, ok,
                     duration_ms, hash_chain, error, output)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                """,
                record.action_id,
                record.timestamp,
                record.backend,
                record.action,
                record.label,
                record.ok,
                record.duration_ms,
                record.hash_chain,
                record.error,
                json.dumps(record.output, default=str) if record.output else None,
            )
            return True
        except Exception:
            self._pg_conn = None

        # Fail-soft: neither available — logged, not raised.
        logger.debug("durable_queue.fail_soft action_id=%s", record.action_id)
        return False


_queue = _DurableQueue()


# ---------------------------------------------------------------------------
# ToolBackend ABC
# ---------------------------------------------------------------------------


class ToolBackend(ABC):
    """Abstract base class for every M8 tool backend.

    Subclasses MUST implement:
    - ``name`` property
    - ``actions()`` returning the full action catalogue
    - ``dispatch(action, args)`` executing an action
    - ``is_available()`` for liveness probing

    The backend does NOT:
    - Make policy decisions (Hermes owns all policy)
    - Gate by consent (ADR-062: no consent gate)
    - Hold a HARD STOP (removed per Q34)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend identifier: 'browser', 'github', 'filesystem', etc."""
        ...

    @abstractmethod
    def actions(self) -> list[Action]:
        """Return the full catalogue of actions this backend supports."""
        ...

    @abstractmethod
    async def dispatch(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute an action.  MUST return a dict; never raise to caller."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the backend's dependencies are configured."""
        ...

    def find_action(self, action: str) -> Action | None:
        """Look up an action by name in the catalogue."""
        for a in self.actions():
            if a.name == action:
                return a
        return None


# ---------------------------------------------------------------------------
# ToolRegistry singleton
# ---------------------------------------------------------------------------


class ToolRegistry:
    """Singleton registry for all M8 tool backends.

    Auto-discovers backends via ``discover_backends()``.  Each dispatch is
    wrapped with UUID v7 + SHA-256 hash-chain audit and best-effort durable
    queue persistence.
    """

    _instance: ToolRegistry | None = None

    def __init__(self) -> None:
        self._backends: dict[str, ToolBackend] = {}

    @classmethod
    def instance(cls) -> ToolRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for tests)."""
        cls._instance = None

    # -- registration -------------------------------------------------------

    def register(self, backend: ToolBackend) -> None:
        """Register a backend.  Overwrites if same name already present."""
        self._backends[backend.name] = backend
        logger.info(
            "tool_registry.register name=%s actions=%d",
            backend.name,
            len(backend.actions()),
        )

    def get(self, name: str) -> ToolBackend | None:
        return self._backends.get(name)

    def backends(self) -> list[ToolBackend]:
        return list(self._backends.values())

    def all_actions(self) -> list[tuple[str, Action]]:
        """Return (backend_name, action) for every registered action."""
        result: list[tuple[str, Action]] = []
        for b in self._backends.values():
            for a in b.actions():
                result.append((b.name, a))
        return result

    # -- dispatch -----------------------------------------------------------

    async def dispatch(
        self, backend_name: str, action: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Dispatch an action through the registry with full audit.

        UUID v7 + SHA-256 hash-chain on every call.  Durable queue
        best-effort (fail-soft D2).
        """
        action_id = uuid.uuid7().hex if hasattr(uuid, "uuid7") else uuid.uuid4().hex
        ts = datetime.now(timezone.utc).isoformat()

        backend = self._backends.get(backend_name)
        if backend is None:
            return {"ok": False, "error": f"backend not found: {backend_name}"}

        action_spec = backend.find_action(action)
        label = action_spec.label.value if action_spec else "L1"

        t0 = time.monotonic()
        try:
            result = await backend.dispatch(action, args)
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}
        elapsed_ms = (time.monotonic() - t0) * 1000

        ok = result.get("ok", True)

        # Build hash-chain audit record
        payload = json.dumps(
            {
                "action_id": action_id,
                "ts": ts,
                "backend": backend_name,
                "action": action,
                "label": label,
                "ok": ok,
            },
            sort_keys=True,
        )
        chain = _compute_chain_hash(payload)

        record = AuditRecord(
            action_id=action_id,
            timestamp=ts,
            backend=backend_name,
            action=action,
            label=label,
            ok=ok,
            duration_ms=elapsed_ms,
            hash_chain=chain,
            error=result.get("error"),
            output=result,
        )

        # Best-effort durable queue (fail-soft)
        try:
            await _queue.enqueue(record)
        except Exception:
            logger.debug("durable_queue.enqueue failed (fail-soft)")

        result["action_id"] = action_id
        result["audit_hash"] = chain
        return result


# ---------------------------------------------------------------------------
# Discovery helper
# ---------------------------------------------------------------------------


def discover_backends() -> list[ToolBackend]:
    """Import and instantiate all 9 backends.  Returns list (may be empty)."""
    backends: list[ToolBackend] = []
    backend_modules = [
        ("guinevere.tools.backends.browser", "BrowserBackend"),
        ("guinevere.tools.backends.github", "GitHubBackend"),
        ("guinevere.tools.backends.filesystem", "FilesystemBackend"),
        ("guinevere.tools.backends.vps", "VPSBackend"),
        ("guinevere.tools.backends.email", "EmailBackend"),
        ("guinevere.tools.backends.desktop", "DesktopBackend"),
        ("guinevere.tools.backends.freelance", "FreelanceBackend"),
        ("guinevere.tools.backends.social", "SocialBackend"),
        ("guinevere.tools.backends.memory", "MemoryBackend"),
    ]
    for mod_path, cls_name in backend_modules:
        try:
            import importlib

            mod = importlib.import_module(mod_path)
            cls = getattr(mod, cls_name)
            backends.append(cls())
        except Exception as exc:
            logger.warning("discover_backends.failed module=%s error=%s", mod_path, exc)
    return backends
