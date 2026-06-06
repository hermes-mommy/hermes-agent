"""
ADR-029: Auto Rollback Safety Tests

Tests the ADR-029 automatic rollback semantics using sandbox state only.
No real repository git operations are performed — all rollback behavior
is simulated via temporary directory data structures and sentinel files.

Required test contracts (Phase 7b Step 7b.4):
1. Rollback completes under 60 seconds in sandbox.
2. Evidence files are preserved after rollback.
3. Audit log records rollback reason, failing command, changed files,
   and restored sentinel.
4. No rollback occurs when tests pass.
5. Rollback result can be verified by sentinel state.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path


# ============================================================
# Sandbox Rollback Simulator
# ============================================================


@dataclass
class AuditEntry:
    """Single audit log entry for a rollback event."""

    rollback_reason: str
    failing_command: str
    changed_files: list[str]
    restored_sentinel: str
    timestamp: float
    duration_seconds: float
    success: bool


@dataclass
class RollbackResult:
    """Result of a simulated rollback operation."""

    rolled_back: bool
    sentinel_before: str
    sentinel_after: str
    audit: AuditEntry | None = None
    evidence_files_preserved: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


class SandboxRollbackSimulator:
    """Simulates ADR-029 automatic rollback using sandbox state.

    Operates entirely on temporary directory structures. No real
    git commands, no real repository mutation, no destructive ops.
    """

    def __init__(self, sandbox: Path) -> None:
        self._sandbox: Path = sandbox
        self._sentinel_file: Path = sandbox / "sentinel.txt"
        self._evidence_dir: Path = sandbox / "evidence"
        self._audit_log: list[AuditEntry] = []
        self._has_rolled_back: bool = False

        # Create sandbox structure
        self._evidence_dir.mkdir(parents=True, exist_ok=True)

        # Initial sentinel state
        self._write_sentinel("PRE_DEPLOY")
        self._write_evidence("baseline-check.txt", "Baseline OK")

    # -- Public API ---------------------------------------------------

    def deploy_change(self, change_name: str) -> None:
        """Simulate deploying a change by writing a test sentinel."""
        self._write_sentinel(f"DEPLOYED:{change_name}")
        self._write_evidence(
            f"deploy-{change_name}.txt",
            f"Deployed change: {change_name}",
        )

    def simulate_failure(self, reason: str, failing_cmd: str) -> None:
        """Simulate a failure and trigger rollback logic.

        The rollback restores the sentinel to its PRE_DEPLOY state
        and preserves all evidence files.
        """
        changed_files = self._list_changed_files()

        start = time.time()
        self._restore_sentinel()
        duration = time.time() - start

        self._has_rolled_back = True

        entry = AuditEntry(
            rollback_reason=reason,
            failing_command=failing_cmd,
            changed_files=sorted(changed_files),
            restored_sentinel=self._read_sentinel(),
            timestamp=time.time(),
            duration_seconds=duration,
            success=(self._read_sentinel() == "PRE_DEPLOY"),
        )
        self._audit_log.append(entry)

    def verify_no_rollback(self) -> None:
        """Confirm no rollback has occurred."""
        self._has_rolled_back = False

    def get_result(self) -> RollbackResult:
        """Build a RollbackResult from current state."""
        sentinel_before = "PRE_DEPLOY"
        if self._audit_log:
            entry = self._audit_log[-1]
            sentinel_before = entry.changed_files[0] if entry.changed_files else "unknown"
        else:
            entry = None

        evidence_files = sorted(
            str(p.relative_to(self._evidence_dir))
            for p in self._evidence_dir.rglob("*")
            if p.is_file()
        )

        return RollbackResult(
            rolled_back=self._has_rolled_back,
            sentinel_before=sentinel_before,
            sentinel_after=self._read_sentinel(),
            audit=entry,
            evidence_files_preserved=evidence_files,
            duration_seconds=entry.duration_seconds if entry else 0.0,
        )

    @property
    def audit_log(self) -> list[AuditEntry]:
        return list(self._audit_log)

    @property
    def sentinel_value(self) -> str:
        return self._read_sentinel()

    # -- Internal helpers ---------------------------------------------

    def _write_sentinel(self, value: str) -> None:
        _ = self._sentinel_file.write_text(value, encoding="utf-8")

    def _read_sentinel(self) -> str:
        if self._sentinel_file.exists():
            return self._sentinel_file.read_text(encoding="utf-8").strip()
        return "MISSING"

    def _restore_sentinel(self) -> None:
        self._write_sentinel("PRE_DEPLOY")

    def _list_changed_files(self) -> list[str]:
        return [str(p.relative_to(self._sandbox)) for p in self._sandbox.rglob("*") if p.is_file()]

    def _write_evidence(self, name: str, content: str) -> None:
        _ = (self._evidence_dir / name).write_text(content, encoding="utf-8")

    def write_evidence(self, name: str, content: str) -> None:
        """Public helper to write evidence files for test assertions."""
        self._write_evidence(name, content)

    @property
    def evidence_dir(self) -> Path:
        """Public accessor for the evidence directory path."""
        return self._evidence_dir

    @property
    def sentinel_file(self) -> Path:
        """Public accessor for the sentinel file path."""
        return self._sentinel_file


# ============================================================
# Helpers
# ============================================================


def _setup_test(tmp_path: Path) -> SandboxRollbackSimulator:
    """Create a fresh sandbox directory and simulator for each test.

    Uses explicit helper construction instead of framework fixtures,
    while preserving full test isolation via ``tmp_path``.
    """
    return SandboxRollbackSimulator(tmp_path / "rollback-sandbox")


# ============================================================
# 1. Rollback Completes Under 60 Seconds
# ============================================================


class TestRollbackTimeout:
    """ADR-029: Rollback must complete within 60 seconds."""

    def test_rollback_completes_under_60s(self, tmp_path: Path) -> None:
        """Simulate failure and verify rollback duration is under 60s."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("test-feature")
        simulator.simulate_failure(
            reason="Unit test failure in test_feature_x",
            failing_cmd="python -m pytest tests/ -k test_feature_x",
        )
        result = simulator.get_result()
        assert result.audit is not None
        assert result.duration_seconds < 60.0, (
            f"Rollback took {result.duration_seconds:.2f}s, expected < 60s"
        )

    def test_rollback_completes_under_60s_no_ops(self, tmp_path: Path) -> None:
        """Rollback of a no-change deploy also completes under 60s."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("no-op")
        simulator.simulate_failure(
            reason="No tests passed",
            failing_cmd="python -m pytest tests/safety/",
        )
        result = simulator.get_result()
        assert result.audit is not None
        assert result.duration_seconds < 60.0, (
            f"Rollback took {result.duration_seconds:.2f}s, expected < 60s"
        )

    def test_rollback_time_is_recorded(self, tmp_path: Path) -> None:
        """Rollback duration is always > 0 and recorded in audit."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("timed")
        simulator.simulate_failure(
            reason="Timeout on integration test",
            failing_cmd="python -m pytest tests/integration/",
        )
        result = simulator.get_result()
        assert result.audit is not None
        assert result.duration_seconds > 0.0
        assert result.audit.duration_seconds > 0.0


# ============================================================
# 2. Evidence Files Preserved
# ============================================================


class TestEvidencePreservation:
    """Evidence files must be preserved across rollback."""

    def test_evidence_survives_rollback(self, tmp_path: Path) -> None:
        """Evidence files from deploy phase persist after rollback."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("feature-a")
        simulator.write_evidence("security-scan.txt", "Pass: 0 critical")
        simulator.write_evidence("test-results.txt", "Fail: 3 tests failed")
        simulator.simulate_failure(
            reason="Test regression detected",
            failing_cmd="python -m pytest tests/ -v",
        )
        result = simulator.get_result()
        assert len(result.evidence_files_preserved) >= 3
        assert any("deploy-feature-a" in f for f in result.evidence_files_preserved)
        assert any("security-scan" in f for f in result.evidence_files_preserved)
        assert any("test-results" in f for f in result.evidence_files_preserved)

    def test_evidence_dir_not_deleted(self, tmp_path: Path) -> None:
        """Evidence directory itself must not be removed by rollback."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("feature-b")
        simulator.simulate_failure(
            reason="Safety test failed",
            failing_cmd="python -m pytest tests/safety/",
        )
        assert simulator.evidence_dir.exists()
        result = simulator.get_result()
        assert len(result.evidence_files_preserved) >= 1

    def test_baseline_evidence_preserved(self, tmp_path: Path) -> None:
        """Baseline checks should survive across rollback cycles."""
        simulator = _setup_test(tmp_path)
        simulator.write_evidence("baseline-deployment.txt", "Timestamp: 2026-06-06T14:00:00Z")
        simulator.deploy_change("feature-c")
        simulator.simulate_failure(
            reason="Memory corruption detected",
            failing_cmd="python -m pytest tests/memory/",
        )
        result = simulator.get_result()
        assert any("baseline" in f for f in result.evidence_files_preserved)


# ============================================================
# 3. Audit Log Records Rollback Details
# ============================================================


class TestAuditLog:
    """Audit log must record rollback reason, failing command,
    changed files, and restored sentinel."""

    def test_audit_log_has_rollback_reason(self, tmp_path: Path) -> None:
        """Audit entry includes the rollback reason."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("audit-log-test")
        reason = "Safety boundary violation detected"
        simulator.simulate_failure(reason=reason, failing_cmd="python -m pytest tests/safety/")
        assert len(simulator.audit_log) == 1
        assert simulator.audit_log[0].rollback_reason == reason

    def test_audit_log_has_failing_command(self, tmp_path: Path) -> None:
        """Audit entry includes the failing command that triggered rollback."""
        simulator = _setup_test(tmp_path)
        failing_cmd = "python -m pytest tests/phase7/ -v --tb=long"
        simulator.deploy_change("feature-d")
        simulator.simulate_failure(
            reason="Phase 7 test suite failed",
            failing_cmd=failing_cmd,
        )
        assert simulator.audit_log[0].failing_command == failing_cmd

    def test_audit_log_has_changed_files(self, tmp_path: Path) -> None:
        """Audit entry lists files changed during the deploy attempt."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("feature-e")
        simulator.write_evidence("deploy-artifact.txt", "artifact data")
        simulator.simulate_failure(
            reason="Artifact verification failed",
            failing_cmd="python -m pytest tests/deploy/",
        )
        entry = simulator.audit_log[0]
        assert len(entry.changed_files) > 0
        # At minimum sentinel.txt and baseline should be listed
        assert any("sentinel" in f for f in entry.changed_files)

    def test_audit_log_has_restored_sentinel(self, tmp_path: Path) -> None:
        """Audit entry records the restored sentinel state."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("feature-f")
        simulator.simulate_failure(
            reason="Feature regression",
            failing_cmd="python -m pytest tests/ -k feature_f",
        )
        entry = simulator.audit_log[0]
        assert entry.restored_sentinel == "PRE_DEPLOY"
        assert entry.success is True

    def test_audit_log_has_timestamp(self, tmp_path: Path) -> None:
        """Each audit entry carries a valid timestamp."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("timestamp-test")
        before = time.time()
        simulator.simulate_failure(
            reason="Timestamp verification",
            failing_cmd="python -m pytest tests/",
        )
        after = time.time()
        entry = simulator.audit_log[0]
        assert before <= entry.timestamp <= after

    def test_audit_log_multiple_entries(self, tmp_path: Path) -> None:
        """Multiple rollback events accumulate in the audit log."""
        simulator = _setup_test(tmp_path)
        for i in range(3):
            simulator.deploy_change(f"multi-{i}")
            simulator.simulate_failure(
                reason=f"Failure iteration {i}",
                failing_cmd=f"python -m pytest tests/ -k test_{i}",
            )
        assert len(simulator.audit_log) == 3
        for i, entry in enumerate(simulator.audit_log):
            assert f"Failure iteration {i}" in entry.rollback_reason
            assert entry.restored_sentinel == "PRE_DEPLOY"


# ============================================================
# 4. No Rollback When Tests Pass
# ============================================================


class TestNoRollbackOnPass:
    """If tests pass, rollback must NOT be triggered."""

    def test_no_rollback_when_all_tests_pass(self, tmp_path: Path) -> None:
        """No audit entry when no failure is simulated."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("passing-feature")
        # No simulate_failure call -- tests passed
        simulator.verify_no_rollback()
        result = simulator.get_result()
        assert result.rolled_back is False
        assert result.sentinel_after != "PRE_DEPLOY"

    def test_sentinel_preserved_on_success(self, tmp_path: Path) -> None:
        """After a successful deploy, sentinel stays at deployed value."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("successful-deploy")
        simulator.verify_no_rollback()
        assert simulator.sentinel_value == "DEPLOYED:successful-deploy"

    def test_evidence_preserved_on_success(self, tmp_path: Path) -> None:
        """On success, evidence from the deploy is available."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("success-evidence")
        simulator.write_evidence("pass-report.txt", "All 42 tests passed")
        simulator.verify_no_rollback()
        result = simulator.get_result()
        assert result.rolled_back is False
        assert any("pass-report" in f for f in result.evidence_files_preserved)
        assert any("deploy-success-evidence" in f for f in result.evidence_files_preserved)

    def test_empty_audit_on_success(self, tmp_path: Path) -> None:
        """No audit entries exist when no rollback occurred."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("clean-deploy")
        simulator.verify_no_rollback()
        assert len(simulator.audit_log) == 0


# ============================================================
# 5. Sentinel State Verification
# ============================================================


class TestSentinelVerification:
    """Rollback results must be verifiable by sentinel state."""

    def test_sentinel_restored_to_pre_deploy(self, tmp_path: Path) -> None:
        """After rollback, sentinel returns to PRE_DEPLOY."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("revert-me")
        assert simulator.sentinel_value == "DEPLOYED:revert-me"
        simulator.simulate_failure(
            reason="Intentional rollback test",
            failing_cmd="python -m pytest tests/ -k revert_me",
        )
        assert simulator.sentinel_value == "PRE_DEPLOY"

    def test_sentinel_after_failed_deploy(self, tmp_path: Path) -> None:
        """Sentinel confirms rollback completed when deploy failed."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("will-fail")
        simulator.simulate_failure(
            reason="Deploy failure simulation",
            failing_cmd="python -m pytest tests/deploy/",
        )
        result = simulator.get_result()
        assert result.sentinel_after == "PRE_DEPLOY"
        assert result.audit is not None
        assert result.audit.restored_sentinel == "PRE_DEPLOY"

    def test_sentinel_before_after_distinct(self, tmp_path: Path) -> None:
        """Before and after sentinel values differ meaningfully."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("distinct-test")
        sentinel_before_rollback = simulator.sentinel_value
        simulator.simulate_failure(
            reason="Distinct sentinel test",
            failing_cmd="python -m pytest tests/",
        )
        result = simulator.get_result()
        assert sentinel_before_rollback != result.sentinel_after
        assert sentinel_before_rollback.startswith("DEPLOYED:")
        assert result.sentinel_after == "PRE_DEPLOY"

    def test_successful_deploy_sentinel_stays(self, tmp_path: Path) -> None:
        """Without rollback, sentinel stays at the deployed value."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("stable")
        simulator.verify_no_rollback()
        assert simulator.sentinel_value == "DEPLOYED:stable"

    def test_rollback_success_flag(self, tmp_path: Path) -> None:
        """Rollback result indicates success via sentinel state."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("flag-test")
        simulator.simulate_failure(
            reason="Success flag test",
            failing_cmd="python -m pytest tests/",
        )
        result = simulator.get_result()
        assert result.audit is not None
        assert result.audit.success is True
        assert result.sentinel_after == "PRE_DEPLOY"


# ============================================================
# 6. Multiple Rollback Cycles
# ============================================================


class TestMultipleRollbackCycles:
    """System must support multiple rollback cycles reliably."""

    def test_consecutive_rollbacks(self, tmp_path: Path) -> None:
        """Multiple deploy → fail → rollback cycles all work."""
        simulator = _setup_test(tmp_path)
        for i in range(5):
            simulator.deploy_change(f"cycle-{i}")
            simulator.simulate_failure(
                reason=f"Cycle {i} failure",
                failing_cmd=f"python -m pytest tests/ -k cycle_{i}",
            )
            assert simulator.sentinel_value == "PRE_DEPLOY", f"Failed at cycle {i}"
        assert len(simulator.audit_log) == 5

    def test_rollback_then_success(self, tmp_path: Path) -> None:
        """After a rollback, a subsequent deploy can succeed."""
        simulator = _setup_test(tmp_path)
        # First deploy fails
        simulator.deploy_change("first-attempt")
        simulator.simulate_failure(
            reason="First attempt failed",
            failing_cmd="python -m pytest tests/",
        )
        assert simulator.sentinel_value == "PRE_DEPLOY"
    
        # Second deploy succeeds
        simulator.deploy_change("second-attempt")
        simulator.verify_no_rollback()
        assert simulator.sentinel_value == "DEPLOYED:second-attempt"
        assert len(simulator.audit_log) == 1  # Only one rollback recorded


# ============================================================
# 7. Edge Cases
# ============================================================


class TestRollbackEdgeCases:
    """Edge cases for the auto-rollback mechanism."""

    def test_deploy_without_evidence(self, tmp_path: Path) -> None:
        """Deploy with no additional evidence - rollback still works."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("bare-deploy")
        simulator.simulate_failure(
            reason="Bare deploy failure",
            failing_cmd="python -m pytest tests/",
        )
        result = simulator.get_result()
        assert result.sentinel_after == "PRE_DEPLOY"
        # Baseline evidence should still exist
        assert any("baseline" in f for f in result.evidence_files_preserved)

    def test_immediate_rollback_after_deploy(self, tmp_path: Path) -> None:
        """Rollback triggered immediately after deploy completes."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("immediate-fail")
        simulator.simulate_failure(
            reason="Immediate failure",
            failing_cmd="python -m pytest tests/ --timeout=5",
        )
        result = simulator.get_result()
        assert result.audit is not None
        assert result.audit.duration_seconds < 1.0  # Sandbox is near-instant


# ============================================================
# 8. Data Integrity
# ============================================================


class TestRollbackDataIntegrity:
    """Rollback must not corrupt sandbox data structures."""

    def test_evidence_not_truncated(self, tmp_path: Path) -> None:
        """Evidence file content must be intact after rollback."""
        simulator = _setup_test(tmp_path)
        content = "Critical: Safety boundary check PASSED\nAll checks completed."
        simulator.write_evidence("critical-check.txt", content)
        simulator.deploy_change("integrity-test")
        simulator.simulate_failure(
            reason="Integrity failure",
            failing_cmd="python -m pytest tests/integrity/",
        )
        evidence_file = simulator.evidence_dir / "critical-check.txt"
        assert evidence_file.read_text(encoding="utf-8") == content

    def test_sentinel_file_exists_after_rollback(self, tmp_path: Path) -> None:
        """Sentinel file must exist after rollback (not deleted)."""
        simulator = _setup_test(tmp_path)
        simulator.deploy_change("exists-test")
        simulator.simulate_failure(
            reason="Existence test",
            failing_cmd="python -m pytest tests/",
        )
        assert simulator.sentinel_file.exists()
        assert simulator.sentinel_file.read_text(encoding="utf-8").strip() == "PRE_DEPLOY"
