"""Sandboxed test execution for loop output verification.

Provides the ``SandboxVerifier`` class for running tests in isolated
environments using git worktree (default) or Docker (optional).
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass(frozen=True)
class SandboxResult:
    """Result of sandboxed test execution.

    Attributes:
        passed: Whether all tests passed.
        test_count: Total number of tests run.
        failures: List of failed test names.
        duration_seconds: Execution time in seconds.
        worktree_path: Path to git worktree (None if Docker used).
        docker_used: Whether Docker was used for execution.
    """

    passed: bool
    test_count: int
    failures: list[str]
    duration_seconds: float
    worktree_path: str | None
    docker_used: bool


class SandboxVerifier:
    """Sandboxed test execution for loop output verification.

    Creates isolated environments using git worktree (fast, lightweight)
    or Docker (isolated, for untrusted code). Uses subprocess.run
    exclusively - NEVER pytest.main() or shell=True.

    Bounded retry with exponential backoff on transient failures:
    - Exit code 2 (pytest collection error) → retry
    - Timeout → retry
    - Exit code 1 (test failure) → no retry (permanent)
    """

    # Retry configuration
    MAX_RETRIES = 5
    BACKOFF_SECONDS = 2

    def __init__(self, repo_root: Path, use_docker: bool = False, max_retries: int = 5) -> None:
        """Initialize sandbox verifier.

        Args:
            repo_root: Root of the git repository.
            use_docker: Whether to use Docker for isolation (slower, but more isolated).
            max_retries: Maximum number of retry attempts (default 5).
        """
        self.repo_root = repo_root
        self.use_docker = use_docker
        self.max_retries = max_retries

    async def verify_changes(self, changed_files: list[str], test_paths: list[str]) -> SandboxResult:
        """Run tests in isolated environment.

        Creates git worktree, copies changed files, runs pytest via
        subprocess.run (NEVER pytest.main), parses output, and cleans up.

        Args:
            changed_files: List of changed file paths relative to repo_root.
            test_paths: List of test paths to run (relative to worktree).

        Returns:
            SandboxResult with pass/fail status and details.

        Raises:
            RuntimeError: If worktree creation or cleanup fails.
        """
        worktree_path: Path | None = None
        docker_used = self.use_docker

        try:
            if docker_used:
                worktree_path = None
                result = await self._run_docker(test_paths)
            else:
                worktree_path = await self._create_worktree()
                try:
                    await self._copy_changed_files(changed_files, worktree_path)
                    result = await self._run_pytest(worktree_path, test_paths)
                finally:
                    await self._cleanup_worktree(worktree_path)

            return result
        except Exception as exc:
            logger.error("sandbox_verification_failed", error=str(exc))
            raise RuntimeError(f"Sandbox verification failed: {exc}") from exc

    async def _create_worktree(self) -> Path:
        """Create temporary git worktree.

        Returns:
            Path to the newly created worktree.

        Raises:
            RuntimeError: If worktree creation fails.
        """
        tmpdir = self.repo_root / ".git" / "worktrees" / f"tmp_{asyncio.get_event_loop().time():.0f}"
        tmpdir.mkdir(parents=True, exist_ok=True)

        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                ["git", "worktree", "add", str(tmpdir), "HEAD"],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            logger.info("worktree_created", worktree_path=str(tmpdir))
            return tmpdir
        except subprocess.CalledProcessError as exc:
            logger.error("worktree_creation_failed", error=exc.stderr)
            raise RuntimeError(f"Failed to create worktree: {exc.stderr}") from exc
        except subprocess.TimeoutExpired:
            raise RuntimeError("Worktree creation timed out") from None

    async def _cleanup_worktree(self, worktree_path: Path) -> None:
        """Remove git worktree.

        Args:
            worktree_path: Path to worktree to remove.

        Raises:
            RuntimeError: If cleanup fails.
        """
        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                ["git", "worktree", "remove", "--force", str(worktree_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode != 0:
                logger.warning("worktree_cleanup_failed", stderr=proc.stderr)
                raise RuntimeError(f"Failed to cleanup worktree: {proc.stderr}")
            logger.info("worktree_removed", worktree_path=str(worktree_path))
        except subprocess.TimeoutExpired:
            logger.error("worktree_cleanup_timeout", worktree_path=str(worktree_path))
            raise RuntimeError("Worktree cleanup timed out") from None
        except Exception as exc:
            logger.error("worktree_cleanup_error", error=str(exc))
            raise RuntimeError(f"Worktree cleanup failed: {exc}") from exc

    async def _run_pytest(self, worktree_path: Path, test_paths: list[str]) -> SandboxResult:
        """Execute pytest in worktree via subprocess.

        Args:
            worktree_path: Path to worktree directory.
            test_paths: List of test paths to run.

        Returns:
            SandboxResult with test results.

        Raises:
            RuntimeError: If pytest execution fails after all retries.
        """
        cmd = [sys.executable, "-m", "pytest", "-x", "--tb=short", "-q"] + test_paths

        for attempt in range(self.max_retries):
            try:
                start_time = asyncio.get_event_loop().time()
                proc = await asyncio.to_thread(
                    subprocess.run,
                    cmd,
                    cwd=worktree_path,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                )
                duration = asyncio.get_event_loop().time() - start_time

                # Parse pytest output
                test_count, failures = self._parse_pytest_output(proc.stdout)

                # Exit code 1 = test failures (permanent), exit code 2 = collection error (transient)
                if proc.returncode == 1:
                    # Test failures are permanent - no retry
                    result = SandboxResult(
                        passed=False,
                        test_count=test_count,
                        failures=failures,
                        duration_seconds=duration,
                        worktree_path=str(worktree_path),
                        docker_used=False,
                    )
                    logger.warning(
                        "pytest_failed_permanent",
                        test_count=test_count,
                        failures=failures,
                        duration_seconds=duration,
                    )
                    return result
                elif proc.returncode == 2:
                    # Collection error - transient, retry
                    logger.warning(
                        "pytest_collection_error_retry",
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.BACKOFF_SECONDS * (2 ** attempt))
                        continue
                    else:
                        raise RuntimeError(
                            f"Pytest collection failed after {self.max_retries} attempts"
                        )
                else:
                    # Success or other exit code
                    result = SandboxResult(
                        passed=(proc.returncode == 0),
                        test_count=test_count,
                        failures=failures,
                        duration_seconds=duration,
                        worktree_path=str(worktree_path),
                        docker_used=False,
                    )
                    logger.info(
                        "pytest_completed",
                        passed=result.passed,
                        test_count=test_count,
                        failures=failures,
                        duration_seconds=duration,
                    )
                    return result

            except subprocess.TimeoutExpired:
                logger.warning(
                    "pytest_timeout_retry",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.BACKOFF_SECONDS * (2 ** attempt))
                    continue
                else:
                    raise RuntimeError("Pytest execution timed out") from None
            except Exception as exc:
                logger.error("pytest_execution_error", error=str(exc))
                raise RuntimeError(f"Pytest execution failed: {exc}") from exc

        # Should never reach here due to retry logic
        raise RuntimeError("Unexpected error in pytest execution")

    async def _run_docker(self, test_paths: list[str]) -> SandboxResult:
        """Execute tests in Docker container (for untrusted code).

        Uses minimal Python sandbox with no network access, dropped caps,
        memory limit, and PID limit. Runs as non-root user.

        Args:
            test_paths: List of test paths to run.

        Returns:
            SandboxResult with test results.

        Raises:
            RuntimeError: If Docker execution fails.
        """
        worktree_path = self.repo_root
        docker_image = "guinevere-sandbox:latest"

        cmd = [
            "docker",
            "run",
            "--rm",
            "--network", "none",
            "--cap-drop", "ALL",
            "--memory", "1g",
            "--pids-limit", "256",
            "-v", f"{worktree_path}:/workspace",
            "-w", "/workspace",
            docker_image,
            "python", "-m", "pytest", "-x", "--tb=short", "-q",
        ] + test_paths

        start_time = asyncio.get_event_loop().time()
        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            duration = asyncio.get_event_loop().time() - start_time

            # Parse pytest output
            test_count, failures = self._parse_pytest_output(proc.stdout)

            result = SandboxResult(
                passed=(proc.returncode == 0),
                test_count=test_count,
                failures=failures,
                duration_seconds=duration,
                worktree_path=None,
                docker_used=True,
            )
            logger.info(
                "docker_pytest_completed",
                passed=result.passed,
                test_count=test_count,
                failures=failures,
                duration_seconds=duration,
            )
            return result
        except subprocess.TimeoutExpired:
            raise RuntimeError("Docker pytest execution timed out") from None
        except Exception as exc:
            logger.error("docker_pytest_error", error=str(exc))
            raise RuntimeError(f"Docker pytest execution failed: {exc}") from exc

    def _parse_pytest_output(self, stdout: str) -> tuple[int, list[str]]:
        """Parse pytest output for test count and failures.

        Args:
            stdout: Standard output from pytest.

        Returns:
            Tuple of (test_count, failures_list).
        """
        test_count = 0
        failures = []

        # Parse "X passed, Y failed" pattern
        match = re.search(r"(\d+) passed", stdout)
        if match:
            test_count = int(match.group(1))

        # Parse failure messages
        # Pattern: "FAILED tests/test_something.py::test_function"
        failure_matches = re.finditer(r"FAILED ([^\s:]+)", stdout)
        for match in failure_matches:
            failures.append(match.group(1))

        return test_count, failures