"""Multi-source signal aggregation for autonomous task discovery.

Defines a generic ``TaskSignal``, a ``SignalCollector`` ABC, concrete collectors
for surveillance, Alertmanager, GitHub, TODO/FIXME markers, runbooks, Gmail, and
Discord, and a ``DiscoveryEngine`` that deduplicates and pushes signals into a
``Backlog``.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from guinevere.loops.dedup import DeduplicationFilter

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from guinevere.loops.backlog import Backlog

logger = logging.getLogger(__name__)

SignalType = Literal[
    "surveillance",
    "alertmanager",
    "github",
    "todo",
    "runbook",
    "gmail",
    "discord",
]


@dataclass(frozen=True)
class TaskSignal:
    """A single task signal discovered from an external source."""

    source: str
    signal_type: SignalType
    title: str
    description: str
    priority_hint: float = 0.5
    metadata: dict = field(default_factory=dict)
    raw_event: str | None = None
    content_hash: str = field(default="")
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.content_hash:
            hash_value = DeduplicationFilter.compute_hash(
                self.title, self.description, self.source
            )
            object.__setattr__(self, "content_hash", hash_value)


class SignalCollector(ABC):
    """Abstract base class for task-signal collectors."""

    @abstractmethod
    async def collect(self) -> list[TaskSignal]:
        """Collect zero or more task signals from the source."""


# ---------------------------------------------------------------------------
# Surveillance collector
# ---------------------------------------------------------------------------


class SurveillanceCollector(SignalCollector):
    """Reads high-severity events from ``surveillance.events``."""

    _HIGH_SEVERITY_TYPES: tuple[str, ...] = (
        "health",
        "screenshot",
        "camera",
        "clipboard",
        "notification",
    )

    def __init__(
        self,
        session_factory: Callable[[], "AbstractAsyncContextManager[object]"]
        | None = None,
        *,
        lookback_hours: int = 24,
    ) -> None:
        self._session_factory = session_factory
        self._lookback_hours = lookback_hours

    async def collect(self) -> list[TaskSignal]:
        if self._session_factory is None:
            return []

        from sqlalchemy import text

        cutoff = datetime.now(timezone.utc) - timedelta(hours=self._lookback_hours)
        sql = text(
            """
            SELECT event_type, extracted_facts, summary, occurred_at, source
            FROM surveillance.events
            WHERE occurred_at >= :cutoff
              AND (
                  event_type = ANY(:high_types)
                  OR extracted_facts ->> 'severity' IN ('high', 'critical')
              )
            ORDER BY occurred_at DESC
            LIMIT 50
            """
        )
        params = {
            "cutoff": cutoff,
            "high_types": list(self._HIGH_SEVERITY_TYPES),
        }

        signals: list[TaskSignal] = []
        try:
            async with self._session_factory() as session:
                result = await session.execute(sql, params)
                rows = result.mappings().all()
        except Exception as exc:
            logger.warning("surveillance_collect_failed", exc_info=exc)
            return []

        for row in rows:
            facts = row.get("extracted_facts") or {}
            if isinstance(facts, str):
                try:
                    facts = {}  # ignore malformed JSON for safety
                except Exception:
                    logger.debug("malformed_extracted_facts", facts_type=type(facts).__name__)
                    facts = {}
            summary = row.get("summary") or f"surveillance {row.get('event_type')}"
            occurred_at = row.get("occurred_at")
            occurred_str = ""
            if isinstance(occurred_at, datetime):
                occurred_str = occurred_at.isoformat()
            signals.append(
                TaskSignal(
                    source="surveillance",
                    signal_type="surveillance",
                    title=f"Surveillance {row.get('event_type')}",
                    description=str(summary),
                    priority_hint=0.8,
                    metadata={
                        "event_type": row.get("event_type"),
                        "severity": facts.get("severity", "high"),
                        "occurred_at": occurred_str,
                        "source_event": row.get("source"),
                    },
                    raw_event=str(dict(row)),
                )
            )
        return signals


# ---------------------------------------------------------------------------
# Alertmanager collector
# ---------------------------------------------------------------------------


class AlertmanagerCollector(SignalCollector):
    """Receives and stores pending Alertmanager alerts as task signals."""

    def __init__(self) -> None:
        self._pending: list[dict] = []

    def receive_alert(self, alert: dict) -> None:
        """Accept a raw Alertmanager alert payload."""
        self._pending.append(alert)

    async def collect(self) -> list[TaskSignal]:
        alerts = self._pending
        self._pending = []
        signals: list[TaskSignal] = []
        for alert in alerts:
            labels = alert.get("labels") or {}
            annotations = alert.get("annotations") or {}
            title = str(labels.get("alertname", "Alertmanager alert"))
            description = str(
                annotations.get("summary") or annotations.get("description") or ""
            )
            signals.append(
                TaskSignal(
                    source="alertmanager",
                    signal_type="alertmanager",
                    title=title,
                    description=description,
                    priority_hint=_severity_to_priority(labels.get("severity", "warning")),
                    metadata={
                        "labels": labels,
                        "annotations": annotations,
                        "status": alert.get("status"),
                    },
                    raw_event=str(alert),
                )
            )
        return signals


# ---------------------------------------------------------------------------
# GitHub collector
# ---------------------------------------------------------------------------


class GitHubCollector(SignalCollector):
    """Discovers failed CI runs and open PRs needing attention."""

    def __init__(
        self,
        owner: str | None = None,
        repo: str | None = None,
        token: str | None = None,
    ) -> None:
        self._owner = owner
        self._repo = repo
        self._token = token or os.environ.get("GITHUB_TOKEN")

    async def collect(self) -> list[TaskSignal]:
        if not self._owner or not self._repo:
            return []

        try:
            import httpx
        except ImportError:
            logger.warning("github_collector_missing_httpx")
            return []

        signals: list[TaskSignal] = []
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            signals.extend(await self._collect_failed_ci(client))
            signals.extend(await self._collect_open_prs(client))
        return signals

    async def _collect_failed_ci(self, client: object) -> list[TaskSignal]:
        import httpx

        url = (
            f"https://api.github.com/repos/{self._owner}/{self._repo}"
            "/actions/runs?per_page=20"
        )
        signals: list[TaskSignal] = []
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            logger.warning("github_failed_ci_fetch_error", exc_info=exc)
            return signals

        for run in data.get("workflow_runs", []):
            if run.get("conclusion") == "failure":
                signals.append(
                    TaskSignal(
                        source="github",
                        signal_type="github",
                        title=f"Failed CI: {run.get('name')}",
                        description=f"Workflow run failed: {run.get('html_url')}",
                        priority_hint=0.7,
                        metadata={
                            "run_id": run.get("id"),
                            "url": run.get("html_url"),
                            "branch": run.get("head_branch"),
                        },
                        raw_event=str(run),
                    )
                )
        return signals

    async def _collect_open_prs(self, client: object) -> list[TaskSignal]:
        import httpx

        url = (
            f"https://api.github.com/repos/{self._owner}/{self._repo}"
            "/pulls?state=open&per_page=20"
        )
        signals: list[TaskSignal] = []
        try:
            response = await client.get(url)
            response.raise_for_status()
            prs = response.json()
        except httpx.HTTPError as exc:
            logger.warning("github_open_prs_fetch_error", exc_info=exc)
            return signals

        now = datetime.now(timezone.utc)
        for pr in prs:
            updated_at = _parse_iso(pr.get("updated_at"))
            age_days = (
                (now - updated_at).total_seconds() / 86400.0
                if updated_at
                else 0.0
            )
            if age_days >= 1.0:
                signals.append(
                    TaskSignal(
                        source="github",
                        signal_type="github",
                        title=f"PR needs attention: {pr.get('title')}",
                        description=f"Open PR last updated {age_days:.1f} days ago: {pr.get('html_url')}",
                        priority_hint=min(0.5 + age_days * 0.05, 0.9),
                        metadata={
                            "pr_number": pr.get("number"),
                            "url": pr.get("html_url"),
                            "author": pr.get("user", {}).get("login"),
                            "updated_at": pr.get("updated_at"),
                        },
                        raw_event=str(pr),
                    )
                )
        return signals


# ---------------------------------------------------------------------------
# TODO / FIXME scanner
# ---------------------------------------------------------------------------


class TodoScanner(SignalCollector):
    """Scans ``guinevere/`` for TODO and FIXME markers."""

    _PATTERN = re.compile(r"#\s*(TODO|FIXME)\b(?::\s*|\s+)(.+)", re.IGNORECASE)

    def __init__(self, root: str | Path = "src", max_files: int = 200) -> None:
        self._root = Path(root)
        self._max_files = max_files

    async def collect(self) -> list[TaskSignal]:
        signals: list[TaskSignal] = []
        files = list(self._root.rglob("*.py"))
        for path in files[: self._max_files]:
            try:
                text = await asyncio.to_thread(path.read_text, encoding="utf-8")
            except OSError as exc:
                logger.debug("todo_scan_read_error", path=str(path), error=str(exc))
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                match = self._PATTERN.search(line)
                if match:
                    signals.append(
                        TaskSignal(
                            source="todo",
                            signal_type="todo",
                            title=f"{match.group(1).upper()} at {path.as_posix()}:{lineno}",
                            description=match.group(2).strip(),
                            priority_hint=0.5,
                            metadata={
                                "file": path.as_posix(),
                                "line": lineno,
                                "kind": match.group(1).upper(),
                            },
                            raw_event=line.strip(),
                        )
                    )
        return signals


# ---------------------------------------------------------------------------
# Runbook scanner
# ---------------------------------------------------------------------------


class RunbookScanner(SignalCollector):
    """Scans runbook directories for actionable operational guides."""

    _ACTIONABLE_KEYWORDS = (
        "incident",
        "recovery",
        "alert",
        "emergency",
        "response",
        "action",
        "sev-1",
        "rollback",
        "drill",
        "escalation",
    )

    def __init__(self, roots: Sequence[str | Path] | None = None) -> None:
        self._roots = [Path(r) for r in (roots or ["runbooks", "docs/40-operations/runbooks"])]

    async def collect(self) -> list[TaskSignal]:
        signals: list[TaskSignal] = []
        seen: set[Path] = set()
        for root in self._roots:
            if not root.exists():
                continue
            for path in root.rglob("*.md"):
                if path in seen:
                    continue
                seen.add(path)
                try:
                    text = await asyncio.to_thread(path.read_text, encoding="utf-8")
                except OSError as exc:
                    logger.debug("runbook_read_error", path=str(path), error=str(exc))
                    continue
                if self._is_actionable(text):
                    title = _extract_title(text) or path.stem
                    signals.append(
                        TaskSignal(
                            source="runbook",
                            signal_type="runbook",
                            title=f"Runbook actionable: {title}",
                            description=f"Actionable runbook detected at {path.as_posix()}",
                            priority_hint=0.6,
                            metadata={
                                "path": path.as_posix(),
                                "keywords": [kw for kw in self._ACTIONABLE_KEYWORDS if kw in text.lower()],
                            },
                            raw_event=text[:500],
                        )
                    )
        return signals

    def _is_actionable(self, text: str) -> bool:
        lower = text.lower()
        if "status:" in lower and "deprecated" in lower:
            return False
        return any(kw in lower for kw in self._ACTIONABLE_KEYWORDS)


# ---------------------------------------------------------------------------
# Gmail collector
# ---------------------------------------------------------------------------


class GmailSignalCollector(SignalCollector):
    """Detects task-signal vocabulary (urgency keywords) from Gmail messages."""

    _URGENCY_TERMS = (
        "urgent",
        "asap",
        "segera",
        "darurat",
        "deadline",
        "action required",
        "please review",
        "mohon",
        "tolong",
    )

    def __init__(self, messages: list[dict] | None = None) -> None:
        self._messages = messages or []

    def set_messages(self, messages: list[dict]) -> None:
        """Replace the internal message buffer."""
        self._messages = messages

    async def collect(self) -> list[TaskSignal]:
        signals: list[TaskSignal] = []
        for message in self._messages:
            subject = str(message.get("subject") or "")
            body = str(message.get("body") or "")
            combined = f"{subject} {body}".lower()
            if any(term in combined for term in self._URGENCY_TERMS):
                signals.append(
                    TaskSignal(
                        source="gmail",
                        signal_type="gmail",
                        title=f"Gmail urgency: {subject}" if subject else "Gmail urgency signal",
                        description=f"Urgent email from {message.get('sender', 'unknown')}",
                        priority_hint=0.7,
                        metadata={
                            "sender": message.get("sender"),
                            "matched_terms": [
                                term for term in self._URGENCY_TERMS if term in combined
                            ],
                        },
                        raw_event=str(message),
                    )
                )
        return signals


# ---------------------------------------------------------------------------
# Discord listener collector
# ---------------------------------------------------------------------------


class DiscordListener(SignalCollector):
    """Collects trigger keywords from Discord on_message events."""

    # HARD STOP is handled by HardStopHandler in main.py — do NOT capture as backlog signal
    _DEFAULT_TRIGGERS = (
        "bug",
        "error",
        "failure",
        "incident",
        "urgent",
        "deploy failed",
    )

    def __init__(self, trigger_words: Sequence[str] | None = None) -> None:
        self._trigger_words = set(trigger_words or self._DEFAULT_TRIGGERS)
        self._buffer: list[dict] = []

    async def on_message(self, message: dict) -> None:
        """Feed a Discord message into the collector buffer.

        This is a standalone collector and does NOT modify the Discord bot.
        """
        content = str(message.get("content") or "").lower()
        if "hard stop" in content:
            return
        if any(word.lower() in content for word in self._trigger_words):
            self._buffer.append(message)

    async def collect(self) -> list[TaskSignal]:
        buffer = self._buffer
        self._buffer = []
        signals: list[TaskSignal] = []
        for message in buffer:
            content = message.get("content", "")
            signals.append(
                TaskSignal(
                    source="discord",
                    signal_type="discord",
                    title=f"Discord trigger: {content[:60]}",
                    description=str(content),
                    priority_hint=0.6,
                    metadata={
                        "author": message.get("author"),
                        "channel": message.get("channel"),
                    },
                    raw_event=str(message),
                )
            )
        return signals


# ---------------------------------------------------------------------------
# Discovery engine
# ---------------------------------------------------------------------------


class DiscoveryEngine:
    """Runs collectors, deduplicates signals, and pushes them to a backlog."""

    def __init__(
        self,
        collectors: Sequence[SignalCollector],
        backlog: "Backlog",
        dedup_filter: DeduplicationFilter | None = None,
    ) -> None:
        self._collectors = list(collectors)
        self._backlog = backlog
        self._dedup_filter = dedup_filter or DeduplicationFilter()

    async def discover(self) -> list[TaskSignal]:
        """Run all collectors, deduplicate, push to backlog, return new signals."""
        tasks = [collector.collect() for collector in self._collectors]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_signals: list[TaskSignal] = []
        for result in results:
            if isinstance(result, BaseException):
                logger.warning("collector_failed", exc_info=result)
                continue
            all_signals.extend(result)

        new_signals: list[TaskSignal] = []
        for signal in all_signals:
            if await self._dedup_filter.is_duplicate(signal.content_hash):
                continue
            item = await self._backlog.add(signal)
            if item is not None:
                await self._dedup_filter.record(signal.content_hash, item.item_id)
                new_signals.append(signal)

        logger.info(
            "discovery_run",
            discovered=len(all_signals),
            unique=len(new_signals),
        )
        return new_signals

    async def run_periodic(self, interval_seconds: int = 3600) -> None:
        """Start an APScheduler periodic discovery job."""
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            self._discover_job,
            "interval",
            seconds=interval_seconds,
            id="discovery_periodic",
            replace_existing=True,
        )
        scheduler.start()

    async def _discover_job(self) -> None:
        await self.discover()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _severity_to_priority(severity: object) -> float:
    mapping = {
        "critical": 1.0,
        "high": 0.8,
        "warning": 0.5,
        "info": 0.2,
    }
    return mapping.get(str(severity).lower(), 0.5)


def _parse_iso(value: object) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _extract_title(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped.lstrip("# ").strip()
    return None


__all__ = [
    "TaskSignal",
    "SignalCollector",
    "SurveillanceCollector",
    "AlertmanagerCollector",
    "GitHubCollector",
    "TodoScanner",
    "RunbookScanner",
    "GmailSignalCollector",
    "DiscordListener",
    "DiscoveryEngine",
]
