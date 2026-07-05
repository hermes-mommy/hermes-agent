#!/usr/bin/env python3
"""Shadow Monitor — reads shadow_comparisons.jsonl, calculates parity metrics,
enforces cost caps, and alerts via Discord webhook on threshold violations.

Run standalone:  python3 -m guinevere.discord.shadow_monitor --check
Run parity test: python3 -m guinevere.discord.shadow_monitor --parity-check --min-queries 100 --report
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("shadow_monitor")
logger.setLevel(logging.INFO)

_console = logging.StreamHandler()
_console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(_console)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_COMPARISON_LOG = "logs/shadow_comparisons.jsonl"
COST_CAP_USD = 5.0
DEFAULT_SINCE_MINUTES = 60
DEFAULT_MIN_QUERIES = 100


# ---------------------------------------------------------------------------
# ShadowMonitor
# ---------------------------------------------------------------------------
class ShadowMonitor:
    """Monitors Hermes shadow parity vs production bot.py via JSONL comparison log."""

    def __init__(self, comparison_log: str | None = None) -> None:
        self.comparison_log: str = comparison_log or DEFAULT_COMPARISON_LOG
        self.cost_cap_usd: float = COST_CAP_USD
        self.webhook_url: str = os.environ.get("DISCORD_APPROVAL_WEBHOOK", "")
        self.thresholds: dict[str, float] = {
            "safety_parity_pct": 100.0,       # MUST be 100%
            "memory_deviation_pct": 5.0,       # max 5% deviation
            "command_match_pct": 100.0,        # MUST be 100%
            "error_rate_pct": 5.0,             # max 5% error rate
        }

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------
    def read_comparisons(self, since_minutes: int = DEFAULT_SINCE_MINUTES) -> list[dict[str, Any]]:
        """Read JSONL comparison log, filter to entries within the last N minutes."""
        comparisons: list[dict[str, Any]] = []
        cutoff = datetime.now(timezone.utc).timestamp() - (since_minutes * 60)

        if not os.path.isfile(self.comparison_log):
            logger.warning("Comparison log not found: %s", self.comparison_log)
            return comparisons

        try:
            with open(self.comparison_log, "r", encoding="utf-8") as fh:
                for line_num, line in enumerate(fh, start=1):
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        entry: dict[str, Any] = json.loads(stripped)
                    except json.JSONDecodeError:
                        logger.warning("Skipping malformed JSON at line %d in %s",
                                       line_num, self.comparison_log)
                        continue

                    ts_str: str | None = entry.get("timestamp")
                    if ts_str is None:
                        logger.warning("Skipping entry without timestamp at line %d", line_num)
                        continue

                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        logger.warning("Skipping entry with invalid timestamp at line %d: %s",
                                       line_num, ts_str)
                        continue

                    if ts.timestamp() >= cutoff:
                        comparisons.append(entry)

        except OSError as exc:
            logger.error("Failed to read comparison log %s: %s", self.comparison_log, exc)

        return comparisons

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------
    def calculate_metrics(self, comparisons: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate parity metrics from comparison data.

        Returns dict with:
          safety_parity_pct, memory_deviation_pct, command_match_pct,
          error_rate_pct, total_queries, total_cost_usd, uptime_hours
        """
        if not comparisons:
            return {
                "safety_parity_pct": 100.0,
                "memory_deviation_pct": 0.0,
                "command_match_pct": 100.0,
                "error_rate_pct": 0.0,
                "total_queries": 0,
                "total_cost_usd": 0.0,
                "uptime_hours": 0.0,
            }

        total = len(comparisons)
        safety_ok = sum(1 for c in comparisons if c.get("safety_match") is True)
        errors = sum(1 for c in comparisons if c.get("error") is not None)
        total_cost = sum(float(c.get("cost_usd", 0.0)) for c in comparisons)

        # Command match: check if command_match field exists, default True
        cmd_ok = sum(1 for c in comparisons if c.get("command_match", True) is True)

        # Memory deviation: average of memory_deviation_pct if present
        mem_deviations: list[float] = []
        for c in comparisons:
            md = c.get("memory_deviation_pct")
            if md is not None:
                mem_deviations.append(float(md))

        avg_memory_deviation = (
            sum(mem_deviations) / len(mem_deviations) if mem_deviations else 0.0
        )

        # Uptime: time delta between first and last entry
        try:
            first_ts = datetime.fromisoformat(
                comparisons[0]["timestamp"].replace("Z", "+00:00")
            )
            last_ts = datetime.fromisoformat(
                comparisons[-1]["timestamp"].replace("Z", "+00:00")
            )
            uptime_hours = (last_ts - first_ts).total_seconds() / 3600.0
        except (KeyError, ValueError, TypeError, IndexError):
            uptime_hours = 0.0

        return {
            "safety_parity_pct": (safety_ok / total) * 100.0 if total else 100.0,
            "memory_deviation_pct": avg_memory_deviation,
            "command_match_pct": (cmd_ok / total) * 100.0 if total else 100.0,
            "error_rate_pct": (errors / total) * 100.0 if total else 0.0,
            "total_queries": total,
            "total_cost_usd": round(total_cost, 6),
            "uptime_hours": round(uptime_hours, 2),
        }

    # ------------------------------------------------------------------
    # Thresholds
    # ------------------------------------------------------------------
    def check_thresholds(self, metrics: dict[str, Any]) -> list[str]:
        """Check metrics against thresholds. Return list of violation descriptions."""
        violations: list[str] = []

        # Cost cap
        cost = float(metrics.get("total_cost_usd", 0.0))
        if cost > self.cost_cap_usd:
            msg = ("COST CAP EXCEEDED: ${:.4f} > ${:.2f} cap. "
                   "Shadow must be disabled.").format(cost, self.cost_cap_usd)
            violations.append(msg)

        # Safety parity — must be exactly 100%
        safety = float(metrics.get("safety_parity_pct", 100.0))
        if safety < self.thresholds["safety_parity_pct"]:
            msg = ("SAFETY PARITY FAILED: {:.1f}% < {:.0f}%. "
                   "CRITICAL — Hermes safety does not match production.").format(
                safety, self.thresholds["safety_parity_pct"])
            violations.append(msg)

        # Memory deviation
        mem = float(metrics.get("memory_deviation_pct", 0.0))
        if mem > self.thresholds["memory_deviation_pct"]:
            msg = "MEMORY DEVIATION: {:.2f}% > {:.1f}% threshold.".format(
                mem, self.thresholds["memory_deviation_pct"])
            violations.append(msg)

        # Command match
        cmd = float(metrics.get("command_match_pct", 100.0))
        if cmd < self.thresholds["command_match_pct"]:
            msg = ("COMMAND MISMATCH: {:.1f}% < {:.0f}%. "
                   "CRITICAL — Hermes commands do not match production.").format(
                cmd, self.thresholds["command_match_pct"])
            violations.append(msg)

        # Error rate
        err = float(metrics.get("error_rate_pct", 0.0))
        if err > self.thresholds["error_rate_pct"]:
            msg = "ERROR RATE: {:.2f}% > {:.1f}% threshold.".format(
                err, self.thresholds["error_rate_pct"])
            violations.append(msg)

        return violations

    # ------------------------------------------------------------------
    # Alerting
    # ------------------------------------------------------------------
    def send_alert(self, violations: list[str], metrics: dict[str, Any]) -> None:
        """Send Discord webhook alert with violations and current metrics."""
        if not self.webhook_url:
            logger.warning("DISCORD_APPROVAL_WEBHOOK not set — cannot send alert.")
            return

        import ssl
        import urllib.error
        import urllib.request

        ctx = ssl.create_default_context()
        timestamp = datetime.now(timezone.utc).isoformat()
        color = 0xFF0000 if any("SAFETY" in v or "CRITICAL" in v for v in violations) else 0xFFA500

        embed: dict[str, Any] = {
            "title": "Shadow Monitor Alert",
            "color": color,
            "timestamp": timestamp,
            "fields": [
                {
                    "name": "Safety Parity",
                    "value": f"{metrics.get('safety_parity_pct', 0.0):.1f}% (threshold: 100%)",
                    "inline": True,
                },
                {
                    "name": "Command Match",
                    "value": f"{metrics.get('command_match_pct', 0.0):.1f}% (threshold: 100%)",
                    "inline": True,
                },
                {
                    "name": "Memory Deviation",
                    "value": f"{metrics.get('memory_deviation_pct', 0.0):.2f}% (max: 5%)",
                    "inline": True,
                },
                {
                    "name": "Error Rate",
                    "value": f"{metrics.get('error_rate_pct', 0.0):.2f}% (max: 5%)",
                    "inline": True,
                },
                {
                    "name": "Total Queries",
                    "value": str(metrics.get("total_queries", 0)),
                    "inline": True,
                },
                {
                    "name": "Total Cost (USD)",
                    "value": f"${metrics.get('total_cost_usd', 0.0):.4f} (cap: ${self.cost_cap_usd:.2f})",
                    "inline": True,
                },
            ],
        }

        if violations:
            embed["fields"].append({
                "name": "Violations",
                "value": "\n".join(f"- {v}" for v in violations),
                "inline": False,
            })

        payload: dict[str, Any] = {"embeds": [embed]}
        body = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            self.webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                status = resp.status
                if status not in (200, 204):
                    logger.error("Webhook returned status %d", status)
        except urllib.error.HTTPError as exc:
            logger.error("Webhook HTTP error: %s", exc)
        except (OSError, ValueError) as exc:
            logger.error("Failed to send webhook alert: %s", exc)

    # ------------------------------------------------------------------
    # Main entry points
    # ------------------------------------------------------------------
    def run_check(self) -> int:
        """Main check cycle. Returns 0 if all OK, 1 if violations found."""
        logger.info("Shadow monitor check starting…")

        comparisons = self.read_comparisons()
        logger.info("Read %d comparisons from last %d minutes",
                     len(comparisons), DEFAULT_SINCE_MINUTES)

        metrics = self.calculate_metrics(comparisons)
        logger.info(
            "Metrics: safety=%.1f%%  command=%.1f%%  memory=%.2f%%  errors=%.2f%%  queries=%d  cost=$%.4f",
            metrics["safety_parity_pct"],
            metrics["command_match_pct"],
            metrics["memory_deviation_pct"],
            metrics["error_rate_pct"],
            metrics["total_queries"],
            metrics["total_cost_usd"])

        violations = self.check_thresholds(metrics)

        if violations:
            logger.warning("Threshold violations found: %d", len(violations))
            for v in violations:
                logger.warning("  %s", v)
            self.send_alert(violations, metrics)
            return 1

        logger.info("All thresholds OK.")
        return 0

    def parity_check(
        self, min_queries: int = DEFAULT_MIN_QUERIES, output_path: str | None = None
    ) -> int:
        """Run comprehensive parity check. Optionally output markdown report.

        Returns 0 if all thresholds pass, 1 if violations or insufficient data.
        """
        comparisons = self.read_comparisons(since_minutes=int(1e9))  # all-time
        logger.info("Parity check: %d total comparisons loaded", len(comparisons))

        if len(comparisons) < min_queries:
            logger.warning(
                "Insufficient data for parity check: %d comparisons (need %d)",
                len(comparisons), min_queries,
            )
            return 1

        metrics = self.calculate_metrics(comparisons)
        violations = self.check_thresholds(metrics)

        if output_path:
            self._write_parity_report(output_path, metrics, violations, len(comparisons))
            logger.info("Parity report written to %s", output_path)

        if violations:
            logger.warning("Parity check: %d violation(s) found", len(violations))
            for v in violations:
                logger.warning("  %s", v)
            return 1

        logger.info("Parity check PASSED — all thresholds met.")
        return 0

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------
    def _write_parity_report(
        self,
        path: str,
        metrics: dict[str, Any],
        violations: list[str],
        total_entries: int,
    ) -> None:
        """Write a markdown parity report to *path*."""
        now = datetime.now(timezone.utc).isoformat()
        lines: list[str] = [
            "# Shadow Monitor — Parity Report",
            "",
            f"**Generated**: {now}",
            f"**Total entries analysed**: {total_entries}",
            "",
            "## Metrics",
            "",
            "| Metric | Value | Threshold | Status |",
            "|---|---|---|---|",
        ]

        def _status_row(name: str, value: float, threshold: float,
                        fmt: str = ".2f", op: str = ">=") -> str:
            if op == ">=":
                ok = value >= threshold
            elif op == "<=":
                ok = value <= threshold
            else:
                ok = True
            status = "✅ PASS" if ok else "❌ FAIL"
            return f"| {name} | {value:{fmt}} | {threshold} | {status} |"

        lines.append(_status_row("Safety Parity %",
                     float(metrics["safety_parity_pct"]),
                     self.thresholds["safety_parity_pct"], ".1f", ">="))
        lines.append(_status_row("Command Match %",
                     float(metrics["command_match_pct"]),
                     self.thresholds["command_match_pct"], ".1f", ">="))
        lines.append(_status_row("Memory Deviation %",
                     float(metrics["memory_deviation_pct"]),
                     self.thresholds["memory_deviation_pct"], ".2f", "<="))
        lines.append(_status_row("Error Rate %",
                     float(metrics["error_rate_pct"]),
                     self.thresholds["error_rate_pct"], ".2f", "<="))

        lines.append("")
        lines.append("## Totals")
        lines.append("")
        lines.append(f"- **Total queries**: {metrics['total_queries']}")
        lines.append(f"- **Total cost**: ${metrics['total_cost_usd']:.4f} (cap: ${self.cost_cap_usd:.2f})")
        lines.append(f"- **Uptime**: {metrics['uptime_hours']:.2f} hours")

        cost = float(metrics["total_cost_usd"])
        if cost > self.cost_cap_usd:
            lines.append(f"\n⛔ **COST CAP EXCEEDED**: ${cost:.4f} > ${self.cost_cap_usd:.2f}")
        else:
            lines.append(f"\nCost under cap (${cost:.4f} / ${self.cost_cap_usd:.2f}). ✅")

        if violations:
            lines.append("")
            lines.append("## Violations")
            lines.append("")
            for v in violations:
                lines.append(f"- {v}")
        else:
            lines.append("")
            lines.append("## Violations: None ✅")

        lines.append("")

        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines))
        except OSError as exc:
            logger.error("Failed to write parity report to %s: %s", path, exc)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Guinevere Shadow Monitor — parity metrics & threshold alerts"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--check", action="store_true",
        help="Run a single check cycle (reads last 60 min of comparison log)",
    )
    group.add_argument(
        "--parity-check", action="store_true",
        help="Run comprehensive parity check across all comparison data",
    )
    parser.add_argument(
        "--min-queries", type=int, default=DEFAULT_MIN_QUERIES,
        help=f"Minimum queries required for parity check (default: {DEFAULT_MIN_QUERIES})",
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Generate markdown report (only with --parity-check)",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output path for markdown report (default: stdout summary only)",
    )
    parser.add_argument(
        "--log", type=str, default=None,
        help="Path to shadow_comparisons.jsonl (default: logs/shadow_comparisons.jsonl)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    monitor = ShadowMonitor(comparison_log=args.log)

    if args.check:
        return monitor.run_check()

    if args.parity_check:
        output_path: str | None = None
        if args.report:
            output_path = args.output or "logs/shadow_parity_report.md"
        return monitor.parity_check(
            min_queries=args.min_queries,
            output_path=output_path,
        )

    return 0  # unreachable


if __name__ == "__main__":
    sys.exit(main())