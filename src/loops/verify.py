"""Output verification — scaffold and post-implementation checks.

Provides the ``OutputVerifier`` class for verifying implementation
outputs: file existence, markdown structure, forbidden patterns,
and command execution results.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


class OutputVerifier:
    """Verifies implementation outputs against scaffold criteria.

    Accumulates verification results and produces a summary
    of passed/failed checks.
    """

    def __init__(self) -> None:
        self.results: list[dict[str, Any]] = []
        logger.info("output_verifier_initialized")

    def verify_file_exists(self, path: str) -> bool:
        """Check whether a file exists at the given path.

        Args:
            path: Filesystem path to check.

        Returns:
            True if the file exists, False otherwise.
        """
        exists = Path(path).is_file()
        self.record(
            check_name=f"file_exists:{path}",
            passed=exists,
            details=f"File {'exists' if exists else 'not found'}: {path}",
        )
        return exists

    def verify_markdown(self, content: str) -> bool:
        """Check whether content looks like valid markdown.

        Validates that the content starts with ``#`` (heading) or
        contains at least one markdown heading (``##``, ``###``, etc.).

        Args:
            content: Text content to validate.

        Returns:
            True if content appears to be valid markdown.
        """
        stripped = content.strip()
        has_heading = stripped.startswith("#") or bool(
            re.search(r"^#{1,6}\s+", stripped, re.MULTILINE)
        )
        self.record(
            check_name="markdown_structure",
            passed=has_heading,
            details="Markdown heading found" if has_heading else "No markdown heading found",
        )
        return has_heading

    def verify_no_forbidden(self, content: str, patterns: list[str]) -> list[str]:
        """Check that content does not contain any forbidden patterns.

        Args:
            content: Text content to scan.
            patterns: List of regex patterns that must NOT appear.

        Returns:
            List of forbidden patterns that were found (empty = all clear).
        """
        found: list[str] = []
        for pattern in patterns:
            if re.search(pattern, content):
                found.append(pattern)

        self.record(
            check_name="no_forbidden_patterns",
            passed=len(found) == 0,
            details=(
                f"Found {len(found)} forbidden pattern(s): {found}"
                if found
                else "No forbidden patterns found"
            ),
        )
        return found

    def verify_command(self, command: str, expected_exit: int = 0) -> dict[str, Any]:
        """Run a shell command and verify its exit code.

        Args:
            command: Shell command to execute.
            expected_exit: Expected exit code (default 0).

        Returns:
            Dict with keys: exit_code, stdout, stderr, passed.
        """
        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            result: dict[str, Any] = {
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "passed": proc.returncode == expected_exit,
            }
        except subprocess.TimeoutExpired:
            result = {
                "exit_code": -1,
                "stdout": "",
                "stderr": "Command timed out after 30 seconds",
                "passed": False,
            }
            logger.error("command_timeout", command=command)
        except OSError as exc:
            result = {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(exc),
                "passed": False,
            }
            logger.error("command_error", command=command, error=str(exc))

        self.record(
            check_name=f"command:{command}",
            passed=result["passed"],
            details=f"exit_code={result['exit_code']}, expected={expected_exit}",
        )
        return result

    def record(self, check_name: str, passed: bool, details: str) -> None:
        """Record a single verification result.

        Args:
            check_name: Name/identifier of the check.
            passed: Whether the check passed.
            details: Human-readable details.
        """
        self.results.append({
            "check_name": check_name,
            "passed": passed,
            "details": details,
        })
        log_fn = logger.info if passed else logger.warning
        log_fn("verification_recorded",
               check_name=check_name,
               passed=passed,
               details=details)

    def summary(self) -> dict[str, Any]:
        """Return a summary of all verification results.

        Returns:
            Dict with keys: total, passed, failed, results.
        """
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        summary_data: dict[str, Any] = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "results": list(self.results),
        }
        logger.info("verification_summary",
                     total=total,
                     passed=passed,
                     failed=failed)
        return summary_data
