"""ProjectSecretsVault — in-memory secrets vault keyed by project_id.

The vault is a pure in-memory isolation mechanism for per-project secrets.
It does **not** load secrets from environment variables, decrypt files, or
persist anything to disk.  Callers (or deploy-time wiring) are responsible
for decryption and providing the secret dict to :meth:`load`.

Typical usage::

    vault = ProjectSecretsVault()
    vault.load(project_a, {"gmail": "token-gmail-a", "discord": "token-discord-a"})
    vault.load(project_b, {"gmail": "token-gmail-b"})

    vault.get(project_a, "gmail")   # "token-gmail-a"
    vault.get(project_b, "gmail")   # "token-gmail-b"
    vault.get(project_a, "discord") # "token-discord-a"
    vault.get(project_b, "discord") # None  (not loaded)

Thread-safe via ``threading.RLock``.
"""

from __future__ import annotations

import threading

from guinevere.projects.types import ProjectId


class ProjectSecretsVault:
    """In-memory secrets vault that isolates secrets by project_id.

    The vault stores a ``dict[ProjectId, dict[str, str]]`` in memory.
    All public methods are guarded by a :class:`threading.RLock` so they
    are safe to call from async adapters and sync background workers alike.
    """

    def __init__(self) -> None:
        self._store: dict[ProjectId, dict[str, str]] = {}
        self._lock = threading.RLock()

    # ── Public API ─────────────────────────────────────────────────────

    def load(self, project_id: ProjectId, secrets: dict[str, str]) -> None:
        """Load or replace a project's secret mapping.

        Idempotent — calling load again with the same ``project_id``
        replaces the previous secrets atomically.

        Parameters
        ----------
        project_id:
            The project whose secrets to load.
        secrets:
            Domain-to-secret mapping
            (e.g. ``{"gmail": "...", "discord": "..."}``).
        """
        with self._lock:
            self._store[project_id] = dict(secrets)  # defensive copy

    def get(self, project_id: ProjectId, domain: str) -> str | None:
        """Return the secret for ``(project_id, domain)``, or ``None``.

        The lookup is strictly keyed by ``project_id``, so project A can
        **never** read project B's secrets through this API — it is
        structurally impossible to leak across projects.
        """
        with self._lock:
            domains = self._store.get(project_id)
            if domains is None:
                return None
            return domains.get(domain)

    def unload(self, project_id: ProjectId) -> None:
        """Remove all secrets for ``project_id`` from memory."""
        with self._lock:
            self._store.pop(project_id, None)

    def domains(self, project_id: ProjectId) -> list[str]:
        """Return the list of loaded domain keys for ``project_id``.

        Useful for audit and debugging.  Returns an empty list if the
        project has no loaded secrets.
        """
        with self._lock:
            domains = self._store.get(project_id)
            if domains is None:
                return []
            return list(domains.keys())
