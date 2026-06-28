"""P22 Tombstone — standardized post-deletion record for L3 destructive actions.

Per consent-audit §5, every L3 destructive action (delete_message, delete_event,
delete_file, merge_pr, delete_branch, remove_container, etc.) MUST emit a
standardized tombstone record into ``audit.integration_api_log.metadata`` so
that:

- The deletion is forensically reconstructable (content_hash + restore_instr).
- No plaintext content leaks into the audit JSONB (content_hash only).
- The operator can audit ``restore_possible`` / ``irreversible_warning`` to
  judge blast radius.
- Pre-delete exports follow the same shape regardless of provider.

Tombstones are written by calling
``Tombstone.to_audit_metadata()`` and embedding the returned dict into the
audit event's ``metadata`` field.  The WORM audit log + ``_redact_metadata``
ensures secrets / plaintext content never reach disk.

Adapters currently return ad-hoc tombstone-shaped dicts inline.  This module
normalises those into ``Tombstone`` so router / audit code has a single
contract: ``from_action_result(adapter_result, provider, resource_type)``.

The dataclass is ``frozen=True`` so a sealed tombstone can never be mutated
after sealing (sealing happens via :meth:`to_audit_metadata`, which freezes
the dict that lands in WORM storage).
"""

from __future__ import annotations

import hashlib
import re as _re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog

from src.life_integrations.audit import _redact_metadata, _VALUE_SECRET_PATTERNS

logger = structlog.get_logger(__name__)


# Allowed resource_type values — kept narrow so mis-classified adapter
# results can't smuggle an unexpected shape into audit metadata.
ALLOWED_RESOURCE_TYPES: frozenset[str] = frozenset({
    "message",
    "event",
    "file",
    "branch",
    "container",
    "pr",
})


# Secret-shaped keys that should be redacted when scanning nested
# tombstone sub-dicts.  Kept in sync with ``audit._redact_metadata``'s
# own key-name pattern list so the redaction behaviour is consistent
# whether the WORM audit writer sees the dict at the top level or
# nested inside ``tombstone``.
_SECRET_KEY_PATTERNS = ("token", "password", "secret", "key", "credential", "auth")


def _deep_redact(value: Any) -> Any:
    """Recursively redact secret-shaped strings and key names.

    Used by :meth:`Tombstone.to_audit_metadata` to scrub nested tombstone
    fields (``restore_instructions``, ``pre_delete_export.object_path``,
    etc.) before they reach WORM storage.  ``_redact_metadata`` in
    ``audit.py`` only inspects top-level keys; this helper handles the
    nested case.
    """
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for k, v in value.items():
            if any(p in k.lower() for p in _SECRET_KEY_PATTERNS):
                redacted[k] = "<redacted>"
                continue
            redacted[k] = _deep_redact(v)
        return redacted
    if isinstance(value, list):
        return [_deep_redact(item) for item in value]
    if isinstance(value, str):
        if _VALUE_SECRET_PATTERNS.search(value):
            return "<redacted:secret_in_value>"
        if len(value) > 100:
            return f"<long:{len(value)}>"
    return value


@dataclass(frozen=True)
class Tombstone:
    """Standardized post-deletion record.

    Attributes:
        tombstone_id: UUID4 identifying this tombstone record.
        correlation_id: Correlation UUID that links this tombstone to the
            originating audit event / dispatch trace.
        provider: Provider name (e.g., "Discord", "Google", "GitHub").
        resource_type: One of ``ALLOWED_RESOURCE_TYPES``.
        resource_id: Provider-side identifier of the deleted resource.
        deleted_at: ISO-8601 UTC timestamp of the deletion.
        content_hash: SHA-256[:16] fingerprint of the pre-delete content /
            snapshot.  Plaintext MUST NEVER appear here.
        restore_possible: Whether a documented restore path exists.
        restore_instructions: Human-readable restore How-To (e.g.,
            "git push origin <sha>:<branch>").  Empty string when no
            restore is possible.
        pre_delete_export: Dict describing the pre-delete snapshot/export.
            ``performed`` (bool), ``method`` (str), ``object_path``
            (str | None).  Must not contain plaintext body.
        irreversible_warning: True when the tombstone MUST not be treated as
            safely reversible (no snapshot, deletion unconfirmed, etc.).
        audit_event_id: The audit event UUID this tombstone is sealed under.
            ``None`` until :meth:`to_audit_metadata` is called by the
            audit logger.
    """

    tombstone_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    provider: str = ""
    resource_type: str = ""
    resource_id: str = ""
    deleted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    content_hash: str = ""
    restore_possible: bool = False
    restore_instructions: str = ""
    pre_delete_export: dict[str, Any] = field(default_factory=dict)
    irreversible_warning: bool = True
    audit_event_id: str | None = None

    def __post_init__(self) -> None:
        """Validate the tombstone shape.

        Frozen dataclasses can't have ``__init__`` overridden, so this is
        where invariants are enforced.  We log warnings (not raise) because
        the audit layer upstream may have already swallowed a real failure;
        a malformed tombstone should still land in WORM so the operator
        can see what was emitted — but it'll be flagged for review.
        """
        if self.resource_type and self.resource_type not in ALLOWED_RESOURCE_TYPES:
            logger.warning(
                "tombstone.unknown_resource_type",
                tombstone_id=self.tombstone_id,
                resource_type=self.resource_type,
                allowed=sorted(ALLOWED_RESOURCE_TYPES),
            )

        # Forbidden plaintext-content fingerprints
        if self.content_hash and len(self.content_hash) != 16:
            # SHA-256[:16] is the documented contract.  Anything else is
            # either mis-formed (e.g., wrong slice) or possibly plaintext.
            logger.warning(
                "tombstone.content_hash_wrong_length",
                tombstone_id=self.tombstone_id,
                got_len=len(self.content_hash),
                expected_len=16,
            )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Convert the tombstone to a plain dict (JSON-safe).

        The output preserves every field including ``audit_event_id`` so
        :meth:`from_dict` can faithfully round-trip.  Plaintext content
        must not appear here — only :attr:`content_hash`.
        """
        return {
            "tombstone_id": self.tombstone_id,
            "correlation_id": self.correlation_id,
            "provider": self.provider,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "deleted_at": self.deleted_at,
            "content_hash": self.content_hash,
            "restore_possible": self.restore_possible,
            "restore_instructions": self.restore_instructions,
            "pre_delete_export": dict(self.pre_delete_export),
            "irreversible_warning": self.irreversible_warning,
            "audit_event_id": self.audit_event_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Tombstone":
        """Reconstruct a Tombstone from :meth:`to_dict` output."""
        return cls(
            tombstone_id=str(data.get("tombstone_id", uuid.uuid4())),
            correlation_id=str(data.get("correlation_id", uuid.uuid4())),
            provider=str(data.get("provider", "")),
            resource_type=str(data.get("resource_type", "")),
            resource_id=str(data.get("resource_id", "")),
            deleted_at=str(
                data.get(
                    "deleted_at",
                    datetime.now(timezone.utc).isoformat(),
                )
            ),
            content_hash=str(data.get("content_hash", "")),
            restore_possible=bool(data.get("restore_possible", False)),
            restore_instructions=str(data.get("restore_instructions", "")),
            pre_delete_export=dict(data.get("pre_delete_export") or {}),
            irreversible_warning=bool(
                data.get("irreversible_warning", True)
            ),
            audit_event_id=(
                str(data["audit_event_id"])
                if data.get("audit_event_id") is not None
                else None
            ),
        )

    # ------------------------------------------------------------------
    # Audit metadata
    # ------------------------------------------------------------------

    def to_audit_metadata(self) -> dict[str, Any]:
        """Return a dict safe for ``audit.integration_api_log.metadata``.

        Wraps the tombstone under the ``tombstone`` key and removes any
        raw content (keeping only :attr:`content_hash`).

        Redaction strategy:
        ``_redact_metadata`` only inspects top-level dict keys, so we
        recursively walk the tombstone sub-dict, rewrite any string
        that matches a token pattern (``_VALUE_SECRET_PATTERNS``) or
        any secret-shaped key name (``token`` / ``password`` /
        ``secret`` / ``key`` / ``credential`` / ``auth``), and produce a
        copy that is safe to write to ``audit.integration_api_log``.

        This is a defence-in-depth measure: the Tombstone contract
        already forbids plaintext content, but an upstream bug or an
        attacker that smuggles a token into ``restore_instructions``
        must still be scrubbed before reaching WORM.
        """
        redacted_tombstone = _deep_redact(self.to_dict())
        return {
            "tombstone": redacted_tombstone,
            "tombstone_version": "1.0",
        }

    def with_audit_event_id(self, audit_event_id: str) -> "Tombstone":
        """Return a copy with the audit_event_id stamped (frozen-safe)."""
        return Tombstone(
            tombstone_id=self.tombstone_id,
            correlation_id=self.correlation_id,
            provider=self.provider,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            deleted_at=self.deleted_at,
            content_hash=self.content_hash,
            restore_possible=self.restore_possible,
            restore_instructions=self.restore_instructions,
            pre_delete_export=dict(self.pre_delete_export),
            irreversible_warning=self.irreversible_warning,
            audit_event_id=str(audit_event_id),
        )

    # ------------------------------------------------------------------
    # Adapter integration
    # ------------------------------------------------------------------

    @classmethod
    def from_action_result(
        cls,
        adapter_result: dict[str, Any],
        provider: str,
        resource_type: str,
        correlation_id: str | None = None,
    ) -> "Tombstone":
        """Build a Tombstone from an adapter delete result dict.

        Adapter delete methods return varying shapes; this normalises to
        ``Tombstone``.  If the adapter already provides a nested
        ``tombstone`` sub-dict (e.g., discord), we honour it.  Otherwise
        we extract top-level ``content_hash`` / ``restore_possible``
        fields which drive /calendar, /drive, /github, /vps, /telegram
        adapters today.

        Args:
            adapter_result: Adapter delete return dict.  Must contain
                ``success=True`` (else a tombstone shouldn't be emitted).
            provider: Provider name for the tombstone record.
            resource_type: One of :data:`ALLOWED_RESOURCE_TYPES`.
            correlation_id: Optional correlation UUID; auto-generated if
                omitted.

        Returns:
            A sealed :class:`Tombstone` ready for
            :meth:`to_audit_metadata`.
        """
        if not isinstance(adapter_result, dict):
            raise TypeError(
                f"adapter_result must be dict, got {type(adapter_result).__name__}"
            )
        if resource_type not in ALLOWED_RESOURCE_TYPES:
            logger.warning(
                "tombstone.from_action_result.unknown_resource_type",
                resource_type=resource_type,
                allowed=sorted(ALLOWED_RESOURCE_TYPES),
            )

        # Honour an existing nested "tombstone" sub-dict if present.
        embedded = adapter_result.get("tombstone")
        if isinstance(embedded, dict):
            return cls._from_embedded(
                embedded=embedded,
                provider=provider,
                resource_type=resource_type,
                adapter_result=adapter_result,
                correlation_id=correlation_id,
            )

        # Inline (top-level) shape — most adapters today.
        resource_id = cls._extract_resource_id(adapter_result, resource_type)
        content_hash = str(adapter_result.get("content_hash", "") or "")
        deleted_at = str(
            adapter_result.get("deleted_at")
            or datetime.now(timezone.utc).isoformat()
        )
        restore_possible = bool(adapter_result.get("restore_possible", False))
        restore_instructions = str(
            adapter_result.get("restore_method")
            or adapter_result.get("restore_instructions")
            or ""
        )
        irreversible_warning = bool(
            adapter_result.get("irreversible_warning", not restore_possible)
        )

        # Many adapters also emit a pre_delete_export / pre_delete_snapshot
        # sub-dict.  Normalise that to the documented shape.
        pre_delete_export = cls._normalise_pre_delete_export(
            adapter_result, resource_type
        )

        return cls(
            correlation_id=correlation_id or str(uuid.uuid4()),
            provider=provider,
            resource_type=resource_type,
            resource_id=resource_id,
            deleted_at=deleted_at,
            content_hash=content_hash,
            restore_possible=restore_possible,
            restore_instructions=restore_instructions,
            pre_delete_export=pre_delete_export,
            irreversible_warning=irreversible_warning,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @classmethod
    def _from_embedded(
        cls,
        *,
        embedded: dict[str, Any],
        provider: str,
        resource_type: str,
        adapter_result: dict[str, Any],
        correlation_id: str | None,
    ) -> "Tombstone":
        """Honour a nested ``tombstone`` sub-dict (e.g., discord adapter)."""
        tom = cls(
            correlation_id=correlation_id or str(uuid.uuid4()),
            provider=provider,
            resource_type=resource_type,
            resource_id=cls._extract_resource_id(adapter_result, resource_type),
            deleted_at=str(
                embedded.get("deleted_at")
                or datetime.now(timezone.utc).isoformat()
            ),
            content_hash=str(embedded.get("content_hash", "") or ""),
            restore_possible=bool(embedded.get("restore_possible", False)),
            restore_instructions=str(
                embedded.get("restore_method")
                or embedded.get("restore_instructions")
                or ""
            ),
            pre_delete_export=cls._normalise_pre_delete_export(
                adapter_result, resource_type
            ),
            irreversible_warning=bool(
                embedded.get(
                    "irreversible_warning",
                    not bool(embedded.get("restore_possible", False)),
                )
            ),
        )
        return tom

    @staticmethod
    def _extract_resource_id(
        adapter_result: dict[str, Any], resource_type: str
    ) -> str:
        """Pull the canonical resource identifier from the adapter result."""
        # Adapter return shape: a lot of variance.  We try the obvious keys
        # first, then fall back to whatever the resource_type schema says.
        for key in (
            "resource_id",
            f"{resource_type}_id",
            "message_id",
            "event_id",
            "file_id",
            "branch",
            "container_id",
            "calendar_id",
            "chat_id",
            "pr_number",
        ):
            v = adapter_result.get(key)
            if v is not None and v != "":
                return str(v)
        # Discord-style adapters stash the id inside the nested
        # ``tombstone`` sub-dict.  Walk that if the top-level has no
        # recognised resource id.
        embedded = adapter_result.get("tombstone")
        if isinstance(embedded, dict):
            for key in (
                f"{resource_type}_id",
                "message_id",
                "event_id",
                "file_id",
                "branch",
                "container_id",
                "chat_id",
            ):
                v = embedded.get(key)
                if v is not None and v != "":
                    return str(v)
        return ""

    @staticmethod
    def _normalise_pre_delete_export(
        adapter_result: dict[str, Any], resource_type: str
    ) -> dict[str, Any]:
        """Reduce a pre_delete_snapshot / pre_delete_export dict to the
        documented ``{performed, method, object_path}`` shape.

        Adapters may include ``snapshot`` / ``content_hash`` / ``metadata``
        sub-fields — those are intentionally NOT carried into audit metadata
        (the snapshot lives in the adapter's own storage, not WORM).
        """
        for key in ("pre_delete_export", "pre_delete_snapshot", "snapshot"):
            v = adapter_result.get(key)
            if isinstance(v, dict):
                performed = bool(v.get("performed", True))
                method = str(v.get("method") or v.get("snapshot_method") or "")
                object_path_raw = v.get("object_path")
                if object_path_raw is None:
                    # Sometimes the adapter emits a path under another key.
                    object_path_raw = (
                        v.get("path")
                        or v.get("snapshot_path")
                        or v.get("archive_chat_id")
                        or v.get("snapshot_message_id")
                    )
                object_path = (
                    str(object_path_raw) if object_path_raw is not None else None
                )
                return {
                    "performed": performed,
                    "method": method,
                    "object_path": object_path,
                }
        return {"performed": False, "method": "", "object_path": None}


def hash_content(content: str) -> str:
    """SHA-256[:16] of ``content``.  Mirrors the helper used inline by
    the discord, calendar, drive, telegram, github, vps adapters so
    test fixtures / new adapters can reuse the same fingerprint.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
