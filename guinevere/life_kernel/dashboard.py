"""Dashboard renderer for the Living Autonomy Kernel.

Renders a ``LifeMindState`` into a markdown dashboard suitable for a Discord
channel or web UI.  The renderer coalesces updates by checksumming the state
and sanitizes any text that may contain secrets or credentials.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

from guinevere.life_kernel.log_channel import LogChannel
from guinevere.life_kernel.state import LifeMindPhase, LifeMindState, Priority


class DashboardRenderer:
    """Render kernel state as markdown dashboard or compact log line.

    The renderer caches the last rendered output and only re-renders when the
    state changes (detected via a SHA-256 checksum).  All rendered text is run
    through a sanitiser that redacts common secret patterns.
    """

    _API_KEY_PATTERN = re.compile(r"sk-[A-Za-z0-9]{20,}")
    _BEARER_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9\-_\.]+")
    _CREDENTIAL_PATTERN = re.compile(r"(?i)(password|passwd|pwd|secret|token|key)\s*[:=]\s*\S+")

    _SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
        (_API_KEY_PATTERN, "[API_KEY_REDACTED]"),
        (_BEARER_PATTERN, "[TOKEN_REDACTED]"),
        (_CREDENTIAL_PATTERN, "[CREDENTIAL_REDACTED]"),
    )

    def __init__(self) -> None:
        self._last_full_checksum: str | None = None
        self._last_full_render: str = ""
        self._last_minimal_checksum: str | None = None
        self._last_minimal_render: str = ""

    @staticmethod
    def _state_checksum(state: LifeMindState) -> str:
        """Compute a stable checksum for ``state``.

        Args:
            state: Current kernel state.

        Returns:
            Hex digest of the state checksum.
        """
        data = dict(state)
        serialized = json.dumps(data, sort_keys=True, default=str, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _sanitize(text: str) -> str:
        """Redact API keys, tokens, passwords, and credential pairs.

        Args:
            text: Raw text to sanitise.

        Returns:
            Sanitised text with secrets replaced by placeholders labels.
        """
        for pattern, replacement in DashboardRenderer._SECRET_PATTERNS:
            text = pattern.sub(replacement, text)
        return text

    @staticmethod
    def _fmt_timestamp() -> str:
        """Return current UTC timestamp as ISO string."""
        return datetime.now(timezone.utc).isoformat()

    def _heartbeat_section(self, state: LifeMindState) -> str:
        phase = state.get("current_phase", LifeMindPhase.IDLE)
        return (
            "## HEARTBEAT\n\n"
            f"- **Phase**: {phase}\n"
            f"- **Last heartbeat**: {state.get('last_heartbeat', 'n/a')}\n"
            f"- **Active**: {'yes' if state.get('is_active', False) else 'no'}\n"
        )

    def _state_section(self, state: LifeMindState) -> str:
        observations = state.get("observations", [])
        errors = state.get("errors", [])
        goals = state.get("goals", [])
        commitments = state.get("commitments", [])
        pending_tasks = len(goals) + len(commitments)
        return (
            "## STATE\n\n"
            f"- **Observations**: {len(observations)}\n"
            f"- **Actions (act_count)**: {state.get('act_count', 0)}\n"
            f"- **Cycles (cycle_count)**: {state.get('cycle_count', 0)}\n"
            f"- **Errors**: {len(errors)}\n"
            f"- **Pending tasks**: {pending_tasks}\n"
        )

    def _goals_section(self, state: LifeMindState) -> str:
        goals = state.get("goals", [])
        priority_order = {p: i for i, p in enumerate(Priority)}

        def _priority_key(goal: dict[str, object]) -> int:
            priority = goal.get("priority")
            if isinstance(priority, Priority):
                return priority_order.get(priority, -1)
            if isinstance(priority, str):
                try:
                    return priority_order.get(Priority(priority), -1)
                except ValueError:
                    return -1
            return -1

        sorted_goals = sorted(goals, key=_priority_key, reverse=True)

        lines = ["## GOALS", ""]
        for goal in sorted_goals[:5]:
            gid = goal.get("goal_id", "unknown")
            priority = goal.get("priority", "unknown")
            desc = goal.get("description", "")
            lines.append(f"- **{gid}** [{priority}]: {desc}")
        if not sorted_goals:
            lines.append("_No active goals_")
        lines.append("")
        return "\n".join(lines)

    def _commitments_section(self, state: LifeMindState) -> str:
        commitments = state.get("commitments", [])
        lines = ["## COMMITMENTS", ""]
        for commitment in commitments:
            cid = commitment.get("commitment_id", commitment.get("id", "unknown"))
            desc = commitment.get("description", "")
            due = commitment.get("due_at", "n/a")
            lines.append(f"- **{cid}** (due {due}): {desc}")
        if not commitments:
            lines.append("_No active commitments_")
        lines.append("")
        return "\n".join(lines)

    def _concerns_section(self, state: LifeMindState) -> str:
        concerns = state.get("concerns", [])
        lines = ["## CONCERNS", ""]
        for concern in concerns:
            cid = concern.get("concern_id", concern.get("id", "unknown"))
            level = concern.get("level", concern.get("severity", "medium"))
            desc = concern.get("description", "")
            lines.append(f"- **{cid}** [{level}]: {desc}")
        if not concerns:
            lines.append("_No active concerns_")
        lines.append("")
        return "\n".join(lines)

    def _sessions_section(self, state: LifeMindState) -> str:
        session_count = state.get("session_count", 0)
        return (
            "## SESSIONS\n\n"
            f"- **Count**: {session_count}\n"
            f"- **Active**: {session_count}\n"
        )

    def _audit_section(self, state: LifeMindState) -> str:
        audit_entries = state.get("audit_entries", [])
        lines = ["## AUDIT", ""]
        if not audit_entries:
            lines.append("_No audit entries_")
        else:
            for entry in audit_entries[-3:]:
                phase = entry.get("phase", "unknown")
                ts = entry.get("timestamp", "n/a")
                cycle = entry.get("cycle", "n/a")
                lines.append(f"- **{phase}** @ {ts} (cycle {cycle})")
        lines.append("")
        return "\n".join(lines)

    def _autonomy_section(self, state: LifeMindState) -> str:
        """Render autonomy fields section for markdown dashboard."""
        lines = ["## AUTONOMY", ""]
        lines.append(f"- Last Decision: {self._sanitize(str(state.get('last_autonomous_decision', '—')))}")
        lines.append(f"- Last Action Result: {self._sanitize(str(state.get('last_action_result', '—')))}")
        lines.append(f"- Next Planned Action: {self._sanitize(str(state.get('next_planned_action', '—')))}")
        lines.append(f"- HARD STOP: {'ACTIVE' if state.get('hard_stop_requested', False) else 'CLEAR'}")
        lines.append(f"- Memory: {self._sanitize(str(state.get('memory_status', '—')))}")
        lines.append(f"- Uptime Start: {self._sanitize(str(state.get('uptime_start', '—')))}")
        lines.append("")
        return "\n".join(lines)

    def _format_agenda(self, state: LifeMindState) -> str:
        """Format goals/commitments as agenda string for embed."""
        goals = state.get("goals", [])
        if not goals:
            return "No active agenda"
        lines: list[str] = []
        for g in goals[:5]:
            priority = g.get("priority", "?")
            desc = self._sanitize(str(g.get("description", "—")))
            status = g.get("status", "pending")
            lines.append(f"[{priority}] {desc} ({status})")
        return "\n".join(lines) if lines else "No active agenda"

    def _render_full(self, state: LifeMindState) -> str:
        """Build the full markdown dashboard."""
        sections = [
            f"# Living Autonomy Kernel Dashboard\n\n*Rendered at {self._fmt_timestamp()}*\n",
            self._heartbeat_section(state),
            self._state_section(state),
            self._goals_section(state),
            self._commitments_section(state),
            self._concerns_section(state),
            self._sessions_section(state),
            self._audit_section(state),
            self._autonomy_section(state),
        ]
        return "\n".join(sections)

    def render(self, graph_state: LifeMindState) -> str:
        """Render ``graph_state`` as a markdown dashboard.

        Re-renders only when the state has changed since the last call.

        Args:
            graph_state: Current kernel state.

        Returns:
            Markdown dashboard string with secrets redacted.
        """
        checksum = self._state_checksum(graph_state)
        if checksum != self._last_full_checksum:
            self._last_full_render = self._sanitize(self._render_full(graph_state))
            self._last_full_checksum = checksum
        return self._last_full_render

    def render_minimal(self, graph_state: LifeMindState) -> str:
        """Render a compact single-line status for log channel.

        Args:
            graph_state: Current kernel state.

        Returns:
            Compact status string with secrets redacted.
        """
        checksum = self._state_checksum(graph_state)
        if checksum != self._last_minimal_checksum:
            phase = graph_state.get("current_phase", "unknown")
            obs = len(graph_state.get("observations", []))
            acts = graph_state.get("act_count", 0)
            cycles = graph_state.get("cycle_count", 0)
            sessions = graph_state.get("session_count", 0)
            goals = len(graph_state.get("goals", []))
            commitments = len(graph_state.get("commitments", []))
            concerns = len(graph_state.get("concerns", []))
            minimal = (
                f"[LK] phase={phase} obs={obs} acts={acts} cycles={cycles} "
                f"sessions={sessions} goals={goals} commitments={commitments} concerns={concerns}"
            )
            self._last_minimal_render = self._sanitize(minimal)
            self._last_minimal_checksum = checksum
        return self._last_minimal_render

    async def render_to_channel(self, state: LifeMindState, channel: LogChannel) -> None:
        """Render the full dashboard and write it to ``channel``.

        Args:
            state: Current kernel state.
            channel: Target log channel.
        """
        await channel.write(self.render(state))

    async def render_minimal_to_channel(self, state: LifeMindState, channel: LogChannel) -> None:
        """Render the minimal status and write it to ``channel``.

        Args:
            state: Current kernel state.
            channel: Target log channel.
        """
        await channel.write(self.render_minimal(state))

    @staticmethod
    def _truncate_field(value: str, limit: int = 1024) -> str:
        """Truncate a string to ``limit`` characters, appending ellipsis if cut."""
        if len(value) <= limit:
            return value
        return value[: limit - 3] + "..."

    def render_embed(self, state: LifeMindState) -> dict[str, object]:
        """Render state as a Discord embed JSON dict.

        Returns embed dict compatible with Discord REST API.
        Uses _sanitize() on all string values to prevent secret leakage.

        Args:
            state: Current kernel state.

        Returns:
            Discord embed JSON dict with title, description, color, timestamp,
            fields, and footer keys.
        """
        hard_stop = state.get("hard_stop_requested", False)
        color = 0xED4245 if hard_stop else 0x5865F2

        status_emoji = (
            "HARD STOPPED" if hard_stop
            else ("ALIVE" if state.get("is_active", False) else "INACTIVE")
        )
        status_display = (
            f"{'🔴' if hard_stop else ('🟢' if state.get('is_active', False) else '⚪')} {status_emoji}"
        )

        fields: list[dict[str, object]] = [
            {
                "name": "Status",
                "value": self._truncate_field(status_display),
                "inline": True,
            },
            {
                "name": "Mode",
                "value": self._truncate_field(self._sanitize(str(state.get("current_phase", "UNKNOWN")))),
                "inline": True,
            },
            {
                "name": "Current Focus",
                "value": self._truncate_field(self._sanitize(str(state.get("current_focus", "—")))),
                "inline": True,
            },
            {
                "name": "Last Decision",
                "value": self._truncate_field(self._sanitize(str(state.get("last_autonomous_decision", "—")))),
                "inline": False,
            },
            {
                "name": "Last Action Result",
                "value": self._truncate_field(self._sanitize(str(state.get("last_action_result", "—")))),
                "inline": False,
            },
            {
                "name": "Next Planned Action",
                "value": self._truncate_field(self._sanitize(str(state.get("next_planned_action", "—")))),
                "inline": False,
            },
            {
                "name": "Current Agenda",
                "value": self._truncate_field(self._format_agenda(state)),
                "inline": False,
            },
            {
                "name": "HARD STOP",
                "value": "🔴 ACTIVE" if hard_stop else "✅ CLEAR",
                "inline": True,
            },
            {
                "name": "Memory",
                "value": self._truncate_field(self._sanitize(str(state.get("memory_status", "—")))),
                "inline": True,
            },
            {
                "name": "Uptime",
                "value": self._truncate_field(self._sanitize(str(state.get("uptime_start", "—")))),
                "inline": True,
            },
        ]

        fields.append({
            "name": "Heartbeat",
            "value": self._truncate_field(self._sanitize(str(state.get("last_heartbeat", "—")))),
            "inline": True,
        })

        fields.append({
            "name": "Cycles",
            "value": (
                f"act={state.get('act_count', 0)} "
                f"cycle={state.get('cycle_count', 0)} "
                f"session={state.get('session_count', 0)}"
            ),
            "inline": True,
        })

        embed: dict[str, object] = {
            "title": "Guinevere — Living Autonomy Dashboard",
            "description": "P20 Life Kernel real-time status",
            "color": color,
            "timestamp": self._fmt_timestamp(),
            "fields": fields,
            "footer": {"text": "Guinevere P20 — Living Autonomy Kernel"},
        }
        return embed
