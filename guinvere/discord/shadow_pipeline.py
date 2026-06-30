"""Shadow Pipeline Module — Phase 2 Discord Migration (S2.1).

In-process shadow pipeline that forwards messages to Hermes subprocess,
captures Hermes response, logs comparison with bot.py response — but
**NEVER** sends Hermes response to Discord.

Architecture:
    bot.py sends response → shadow_forward() fires asyncio.create_task()
    → Hermes subprocess invoked → response captured → comparison logged
    → Zero Discord send calls in this file.

Disabled by default. Opt-in via SHADOW_ENABLED=true env var.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Any, Final

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

_COST_CAP_USD: Final[float] = 5.0
"""Shadow cost ceiling. Stop forwarding if cumulative cost exceeds this."""

_SUBPROCESS_TIMEOUT: Final[float] = 30.0
"""Maximum seconds to wait for Hermes subprocess response."""

_ESTIMATED_COST_PER_1K_OUTPUT: Final[float] = 0.000015
"""Estimated cost per 1000 output tokens (GPT-5.5 blended rate)."""

_TOKENS_PER_WORD: Final[float] = 0.75
"""Rough tokens-per-word ratio for English/Indonesian text."""

# ── Safety Patterns ───────────────────────────────────────────────────────────

_SAFETY_PATTERNS: Final[list[str]] = [
    "HARD STOP",
    "Y6",
    "Y6_PROHIBITED",
    "F-01", "F-02", "F-03", "F-04", "F-05",
    "F-06", "F-07", "F-08", "F-09", "F-10",
    "F-11", "F-12", "F-13", "F-14", "F-15",
]
"""Forbidden-pattern markers checked in both responses for safety comparison."""


class ShadowPipeline:
    """In-process shadow that forwards to Hermes, logs response, never sends to Discord.

    Lifecycle:
        - Created by ``GuinevereBot.__init__()`` — disabled by default.
        - ``shadow_forward()`` is called as fire-and-forget via ``asyncio.create_task()``.
        - No Discord API calls, no ``channel.send()``, no ``message.reply()``.
    """

    # ── Init ────────────────────────────────────────────────────────────────

    def __init__(self, enabled: bool = False, traffic_pct: int = 0) -> None:
        """Initialise the shadow pipeline.

        Args:
            enabled: If ``True``, shadow forwarding is active.
                     Default ``False`` — opt-in via ``SHADOW_ENABLED`` env var.
            traffic_pct: Percentage of traffic to shadow (0-100). 0 means none.
        """
        self.enabled: bool = enabled
        self.traffic_pct: int = max(0, min(100, traffic_pct))

        self.hermes_cmd: list[str] = [
            "hermes", "--no-stream", "--quiet", "--max-iterations", "15",
        ]

        self.comparison_log: str = "logs/shadow_comparisons.jsonl"

        # Environment-driven configuration
        self._shadow_bot_token: str = os.environ.get(
            "DISCORD_SHADOW_BOT_TOKEN", "",
        )
        self._shadow_channel_id: str = os.environ.get(
            "DISCORD_SHADOW_CHANNEL_ID", "",
        )

        # Counters and cost tracking
        self._request_count: int = 0
        self._error_count: int = 0
        self._shadow_cost_usd: float = 0.0

        # Thread safety
        self._file_lock: asyncio.Lock = asyncio.Lock()

        # Ensure log directory exists at init time
        _log_dir = Path(self.comparison_log).parent
        _log_dir.mkdir(parents=True, exist_ok=True)

        if self.enabled:
            logger.info(
                "shadow_pipeline_initialized",
                extra={
                    "traffic_pct": self.traffic_pct,
                    "cost_cap_usd": _COST_CAP_USD,
                    "comparison_log": self.comparison_log,
                    "subprocess_timeout_s": _SUBPROCESS_TIMEOUT,
                },
            )
        else:
            logger.info("shadow_pipeline_disabled")

    # ── Public API ──────────────────────────────────────────────────────────

    async def shadow_forward(
        self,
        message_content: str,
        bot_response: str,
        user_id: str,
        channel_id: str,
    ) -> dict[str, Any]:
        """Forward message to Hermes subprocess, capture response, log comparison.

        This is the **only** public method. It is called via
        ``asyncio.create_task()`` from the conversational handler after bot.py
        has sent its own response to Discord. The Hermes response is captured
        and logged for comparison — **never** sent to Discord.

        Args:
            message_content: The user's original message.
            bot_response: What bot.py actually sent to Discord (the reference).
            user_id: Discord user ID string (anonymised in logs).
            channel_id: Discord channel ID string.

        Returns:
            A comparison dictionary with fields: ``timestamp``, ``user_id_hash``,
            ``channel_id``, ``user_msg``, ``bot_response``, ``hermes_response``,
            ``safety_match``, ``latency_ms``, ``token_count``, ``cost_usd``,
            ``error`` (``None`` if no error).
        """
        result: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "user_id_hash": user_id[:8],
            "channel_id": channel_id,
            "user_msg": message_content,
            "bot_response": bot_response,
            "hermes_response": "",
            "safety_match": None,
            "latency_ms": 0,
            "token_count": 0,
            "cost_usd": 0.0,
            "error": None,
        }

        # Gate 1: enabled?
        if not self.enabled:
            return result

        # Gate 2: traffic percentage
        if not self._traffic_gate_passes():
            return result

        # Gate 3: cost cap
        if self._shadow_cost_usd >= _COST_CAP_USD:
            logger.warning(
                "shadow_cost_cap_hit",
                extra={
                    "cumulative_cost": round(self._shadow_cost_usd, 6),
                    "cap": _COST_CAP_USD,
                },
            )
            result["error"] = "cost_cap_exceeded"
            return result

        self._request_count += 1
        start_time: float = time.time()

        # ── Invoke Hermes subprocess ────────────────────────────────────────
        try:
            hermes_input: str = self._build_hermes_input(message_content)

            process = await asyncio.create_subprocess_exec(
                *self.hermes_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(input=hermes_input.encode("utf-8")),
                    timeout=_SUBPROCESS_TIMEOUT,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                latency_ms: float = round(
                    (time.time() - start_time) * 1000, 1,
                )
                self._error_count += 1
                logger.warning(
                    "shadow_hermes_timeout",
                    extra={
                        "request_count": self._request_count,
                        "timeout_s": _SUBPROCESS_TIMEOUT,
                        "latency_ms": latency_ms,
                    },
                )
                result["latency_ms"] = latency_ms
                result["error"] = "hermes_subprocess_timeout"
                return result

            latency_ms = round((time.time() - start_time) * 1000, 1)
            result["latency_ms"] = latency_ms

            # Decode outputs
            hermes_response: str = stdout_bytes.decode(
                "utf-8", errors="replace",
            ).strip()
            stderr_text: str = stderr_bytes.decode(
                "utf-8", errors="replace",
            ).strip()

            if process.returncode != 0:
                self._error_count += 1
                logger.warning(
                    "shadow_hermes_nonzero_exit",
                    extra={
                        "returncode": process.returncode,
                        "stderr_preview": stderr_text[:200],
                        "request_count": self._request_count,
                    },
                )
                result["error"] = f"hermes_exit_{process.returncode}"
                result["hermes_response"] = hermes_response
            else:
                result["hermes_response"] = hermes_response

            # ── Safety comparison ───────────────────────────────────────────
            result["safety_match"] = self._compare_safety(
                bot_response, hermes_response,
            )

            # ── Token count (rough) ─────────────────────────────────────────
            token_count: int = int(
                len(hermes_response.split()) * _TOKENS_PER_WORD,
            )
            result["token_count"] = token_count

            # ── Cost estimate ───────────────────────────────────────────────
            estimated_cost: float = self._estimate_cost(hermes_response)
            self._shadow_cost_usd += estimated_cost
            result["cost_usd"] = round(estimated_cost, 6)

            logger.info(
                "shadow_comparison_complete",
                extra={
                    "request_count": self._request_count,
                    "latency_ms": latency_ms,
                    "safety_match": result["safety_match"],
                    "cost_usd": round(estimated_cost, 6),
                    "cumulative_cost": round(self._shadow_cost_usd, 6),
                    "hermes_response_len": len(hermes_response),
                },
            )

        except FileNotFoundError:
            self._error_count += 1
            logger.error(
                "shadow_hermes_binary_not_found",
                extra={"hermes_cmd": self.hermes_cmd},
            )
            result["error"] = "hermes_binary_not_found"
        except OSError as exc:
            self._error_count += 1
            logger.error(
                "shadow_hermes_os_error",
                extra={
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            result["error"] = f"os_error_{type(exc).__name__}"
        except Exception as exc:
            self._error_count += 1
            logger.error(
                "shadow_forward_unexpected",
                extra={
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "request_count": self._request_count,
                },
            )
            result["error"] = f"unexpected_{type(exc).__name__}"

        # ── Log to JSONL (NEVER send to Discord) ────────────────────────────
        await self._write_comparison_log(result)

        return result

    # ── Internal Helpers ────────────────────────────────────────────────────

    def _traffic_gate_passes(self) -> bool:
        """Determine if this request passes the traffic-percentage gate.

        Returns:
            ``True`` if the request should be shadowed based on ``traffic_pct``.
        """
        if self.traffic_pct <= 0:
            return False
        if self.traffic_pct >= 100:
            return True
        return random.randint(1, 100) <= self.traffic_pct

    def _build_hermes_input(self, message_content: str) -> str:
        """Construct the JSON payload for the Hermes subprocess stdin.

        Args:
            message_content: The user's message text.

        Returns:
            A JSON string with ``message`` and ``source`` fields.
        """
        payload: dict[str, str] = {
            "message": message_content,
            "source": "shadow_pipeline",
            "mode": "query",
        }
        return json.dumps(payload)

    def _compare_safety(self, bot_response: str, hermes_response: str) -> bool:
        """Compare safety markers between bot and Hermes responses.

        Both responses are checked for the presence of safety markers
        (HARD STOP, Y6, F-01..F-15 forbidden patterns). If both contain
        the same set of markers, safety is considered matching.

        Args:
            bot_response: The response sent to Discord by bot.py.
            hermes_response: The response captured from the Hermes subprocess.

        Returns:
            ``True`` if the same safety markers appear in both responses.
        """
        bot_upper: str = (bot_response or "").upper()
        hermes_upper: str = (hermes_response or "").upper()

        bot_flags: set[str] = {
            p for p in _SAFETY_PATTERNS if p.upper() in bot_upper
        }
        hermes_flags: set[str] = {
            p for p in _SAFETY_PATTERNS if p.upper() in hermes_upper
        }

        return bot_flags == hermes_flags

    def _estimate_cost(self, response_text: str) -> float:
        """Estimate the cost of a Hermes response.

        Uses a rough word → token → cost pipeline. This is an estimate,
        not a precise billing calculation.

        Args:
            response_text: The raw response text from Hermes.

        Returns:
            Estimated cost in USD, rounded to 6 decimal places.
        """
        word_count: int = len(response_text.split())
        estimated_tokens: float = word_count * _TOKENS_PER_WORD
        cost: float = (estimated_tokens / 1000.0) * _ESTIMATED_COST_PER_1K_OUTPUT
        return round(cost, 6)

    async def _write_comparison_log(self, result: dict[str, Any]) -> None:
        """Append a comparison result to the JSONL log file.

        Uses ``asyncio.Lock`` for thread-safe concurrent writes.
        The log file is written line-by-line in JSONL format with
        ``ensure_ascii=False`` for proper Unicode handling.

        Args:
            result: The comparison dictionary to log.
        """
        async with self._file_lock:
            try:
                with open(
                    self.comparison_log, "a", encoding="utf-8",
                ) as log_handle:
                    log_handle.write(
                        json.dumps(result, ensure_ascii=False) + "\n",
                    )
            except OSError as exc:
                logger.error(
                    "shadow_log_write_failed",
                    extra={
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                        "path": self.comparison_log,
                    },
                )

    # ── Introspection ───────────────────────────────────────────────────────

    @property
    def stats(self) -> dict[str, Any]:
        """Return current shadow pipeline statistics (read-only)."""
        return {
            "enabled": self.enabled,
            "traffic_pct": self.traffic_pct,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "cumulative_cost_usd": round(self._shadow_cost_usd, 6),
            "cost_cap_usd": _COST_CAP_USD,
            "comparison_log": self.comparison_log,
        }