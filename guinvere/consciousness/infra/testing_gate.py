"""ADR-029 Testing Gate — enforces test pass and coverage before self-modification deployment.

Ported from ``src/loops/testing_gate.py`` — API preserved for M10 (W14).
Runs pytest in an isolated subprocess (never pytest.main in-process).
"""

from __future__ import annotations

import asyncio
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Awaitable, Callable

import structlog

logger = structlog.get_logger(__name__)


# ──────────────────────────────────────────────────────────────
# Data contracts
# ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TestResult:
    """Result of a single test run."""

    passed: bool
    total: int
    failed: int
    errors: list[str]
    duration_s: float
    coverage_pct: float | None = None


@dataclass(frozen=True)
class GateDecision:
    """Decision returned by ``TestingGate.gate()`` or ``.evaluate()``."""

    approved: bool
    reason: str
    test_result: TestResult | None = None


# ──────────────────────────────────────────────────────────────
# Parsing helpers
# ──────────────────────────────────────────────────────────────

_PASSED_SUMMARY_RE = re.compile(
    r"(?P<passed>\d+)\s+passed",
)
_FAILED_SUMMARY_RE = re.compile(
    r"(?P<failed>\d+)\s+failed",
)
_COVERAGE_RE = re.compile(
    r"TOTAL\s+\d+\s+\d+\s+(?P<coverage>\d+)%",
)
_DURATION_RE = re.compile(
    r"in\s+(?P<seconds>[\d.]+)s",
)


def _parse_pytest_output(
    stdout: str,
    stderr: str,
    returncode: int,
    duration_s: float,
) -> TestResult:
    """Parse pytest stdout/stderr into a ``TestResult``."""
    combined = stdout + "\n" + stderr
    passed = returncode == 0

    passed_count = 0
    failed_count = 0
    total_count = 0

    passed_match = _PASSED_SUMMARY_RE.search(combined)
    failed_match = _FAILED_SUMMARY_RE.search(combined)

    if passed_match:
        passed_count = int(passed_match.group("passed"))
    if failed_match:
        failed_count = int(failed_match.group("failed"))

    total_count = passed_count + failed_count

    if total_count == 0:
        if returncode != 0:
            total_count = 1
            failed_count = 1
        else:
            total_count = 1
            passed_count = 1

    errors: list[str] = []
    error_section = False
    for line in combined.splitlines():
        stripped = line.strip()
        if stripped.startswith("FAILED ") or stripped.startswith("ERRORS"):
            error_section = True
        if error_section and stripped:
            errors.append(stripped)
        if error_section and not stripped:
            error_section = False

    errors = errors[:10]

    coverage_pct: float | None = None
    cov_match = _COVERAGE_RE.search(combined)
    if cov_match:
        coverage_pct = float(cov_match.group("coverage"))

    return TestResult(
        passed=passed,
        total=total_count,
        failed=failed_count,
        errors=errors,
        duration_s=duration_s,
        coverage_pct=coverage_pct,
    )


# ──────────────────────────────────────────────────────────────
# TestingGate
# ──────────────────────────────────────────────────────────────


class TestingGate:
    """ADR-029 compliance gate — blocks self-modification unless tests pass.

    Runs pytest in a subprocess (never ``pytest.main()`` in-process) with
    optional coverage measurement.

    Constructor injection:
    - sandbox_runner: Optional callable that runs tests in an isolated environment.
    """

    def __init__(
        self,
        sandbox_runner: Callable[..., Awaitable[TestResult]] | None = None,
        min_coverage_pct: float = 80.0,
    ) -> None:
        self._sandbox_runner = sandbox_runner
        self._min_coverage_pct = min_coverage_pct
        self._log = logger.bind(gate="testing")

    async def run_tests(self, loop_id: str, target_path: str) -> TestResult:
        """Run pytest against *target_path* in an isolated subprocess."""
        self._log.info("run_tests.start", loop_id=loop_id, target_path=target_path)

        if self._sandbox_runner is not None:
            self._log.info("run_tests.sandbox", loop_id=loop_id)
            try:
                return await self._sandbox_runner(loop_id, target_path)
            except Exception as exc:
                self._log.error(
                    "run_tests.sandbox_failed",
                    loop_id=loop_id,
                    error=str(exc),
                )
                return TestResult(
                    passed=False,
                    total=1,
                    failed=1,
                    errors=[f"Sandbox runner raised: {exc}"],
                    duration_s=0.0,
                )

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            target_path,
            "-v",
            "--tb=short",
            "--no-header",
        ]

        self._log.info(
            "run_tests.subprocess",
            loop_id=loop_id,
            cmd=[sys.executable, "-m", "pytest", target_path, "-v", "--tb=short"],
        )

        start = time.monotonic()
        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - start
            self._log.error(
                "run_tests.timeout",
                loop_id=loop_id,
                duration_s=round(elapsed, 2),
            )
            return TestResult(
                passed=False,
                total=1,
                failed=1,
                errors=["pytest timed out after 300s"],
                duration_s=elapsed,
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            self._log.error(
                "run_tests.subprocess_error",
                loop_id=loop_id,
                error=str(exc),
            )
            return TestResult(
                passed=False,
                total=1,
                failed=1,
                errors=[f"Subprocess error: {exc}"],
                duration_s=elapsed,
            )

        elapsed = time.monotonic() - start
        self._log.info(
            "run_tests.done",
            loop_id=loop_id,
            returncode=proc.returncode,
            duration_s=round(elapsed, 2),
        )

        result = _parse_pytest_output(
            stdout=proc.stdout,
            stderr=proc.stderr,
            returncode=proc.returncode,
            duration_s=elapsed,
        )
        return result

    async def evaluate(
        self,
        result: TestResult,
        min_coverage: float | None = None,
    ) -> GateDecision:
        """Evaluate a test result against acceptance criteria."""
        threshold = min_coverage if min_coverage is not None else self._min_coverage_pct

        if not result.passed or result.failed > 0:
            reason = (
                f"Tests failed: {result.failed}/{result.total} failures. "
                f"Errors: {result.errors[:3]}"
            )
            self._log.warning("evaluate.blocked", reason=reason)
            return GateDecision(
                approved=False,
                reason=reason,
                test_result=result,
            )

        if result.coverage_pct is not None and result.coverage_pct < threshold:
            reason = (
                f"Coverage {result.coverage_pct:.1f}% is below "
                f"threshold {threshold:.1f}%"
            )
            self._log.warning("evaluate.coverage_blocked", reason=reason)
            return GateDecision(
                approved=False,
                reason=reason,
                test_result=result,
            )

        self._log.info(
            "evaluate.passed",
            total=result.total,
            coverage=result.coverage_pct,
        )
        return GateDecision(
            approved=True,
            reason="All tests passed with sufficient coverage.",
            test_result=result,
        )

    async def gate(self, loop_id: str, target_path: str) -> GateDecision:
        """Convenience: run tests and evaluate in a single call."""
        result = await self.run_tests(loop_id, target_path)
        return await self.evaluate(result)
