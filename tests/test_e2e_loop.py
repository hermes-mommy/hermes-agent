"""P5-022: E2E Agent Loop Test — Full 7-phase SDLC cycle.

Standalone async test that exercises LoopManager through all 7 phases:
  1. Research → 2. Plan & Delegate → 3. Delegate → 4. Execute →
  5. Validate & Audit → 6. Update Documents → 7. Setup Evidence → COMPLETE

Verifies: status transitions, phase progression, artifact creation, final report.

# Server-based E2E test (requires running guinevere-core on port 8000):
# curl -X POST http://localhost:8000/api/v1/loops \
#   -H "Content-Type: application/json" \
#   -H "X-Guinevere-API-Key: guinevere-dev-key" \
#   -d '{"task": "Create README for memory module", "priority": "normal"}'
# Expected: loop spawns, executes 7 phases, creates evidence files
"""

from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path

# Ensure project root is on sys.path for `from src.loops.*` imports.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Phase slugs matching _PHASE_SLUGS in src/loops/evidence.py.
_PHASE_SLUGS: list[str] = [
    "research",
    "plan-delegate",
    "delegate",
    "execute",
    "validate-audit",
    "update-documents",
    "setup-evidence",
]

_TOTAL_PHASES = 7
_COMPLETE_PHASE_VALUE = 8
_POLL_INTERVAL = 0.2  # seconds between status polls
_TIMEOUT = 30  # max seconds to wait for loop completion


async def test_full_loop_cycle() -> bool:
    """Run a complete 7-phase SDLC loop and verify all outputs."""
    from src.loops.manager import LoopManager
    from src.loops.artifacts import artifact_exists, evidence_dir

    results: list[tuple[str, bool]] = []
    evidence_dirs_to_clean: list[Path] = []

    try:
        # ── 1. Create manager and start loop ──────────────────────────
        manager = LoopManager()

        loop_id = await manager.start_loop(
            task="Create README for memory module",
            goal="Create comprehensive README with usage examples",
            priority="normal",
        )

        results.append(("start_loop returns loop_id", isinstance(loop_id, str) and len(loop_id) > 0))

        # Track evidence dir for cleanup.
        ev_dir = evidence_dir(loop_id)
        evidence_dirs_to_clean.append(ev_dir)

        # ── 2. Wait for completion with timeout ───────────────────────
        elapsed = 0.0
        terminal_statuses = frozenset({"complete", "failed", "cancelled"})
        final_status: dict[str, str | int | dict[str, str]] | None = None

        while elapsed < _TIMEOUT:
            status_dict = await manager.get_loop_status(loop_id)
            if status_dict is not None and status_dict.get("status") in terminal_statuses:
                final_status = status_dict
                break
            await asyncio.sleep(_POLL_INTERVAL)
            elapsed += _POLL_INTERVAL

        results.append((
            f"Loop reached terminal status within {_TIMEOUT}s",
            final_status is not None,
        ))

        if final_status is None:
            # Cannot proceed without a terminal status.
            results.append(("Loop status is 'complete'", False))
            _print_results(results)
            return False

        # ── 3. Verify final status is COMPLETE ────────────────────────
        status_value = str(final_status.get("status", ""))
        results.append(("Final status is 'complete'", status_value == "complete"))

        # ── 4. Verify all 7 phases were traversed ─────────────────────
        current_phase_raw = final_status.get("current_phase", 0)
        current_phase = current_phase_raw if isinstance(current_phase_raw, int) else 0
        results.append((
            f"Reached COMPLETE phase (value={_COMPLETE_PHASE_VALUE})",
            current_phase == _COMPLETE_PHASE_VALUE,
        ))

        # ── 5. Verify phase name in status dict ───────────────────────
        phase_name = str(final_status.get("current_phase_name", ""))
        results.append(("Final phase name is 'Complete'", phase_name == "Complete"))

        # ── 6. Verify artifacts exist for each phase ──────────────────
        for slug in _PHASE_SLUGS:
            exists = artifact_exists(loop_id, slug)
            results.append((f"Artifact exists: {slug}.md", exists))

        # ── 7. Verify final evidence report exists ────────────────────
        final_exists = artifact_exists(loop_id, "evidence-final")
        results.append(("Final evidence report (evidence-final.md)", final_exists))

        # ── 8. Verify error_count is 0 ────────────────────────────────
        error_count_raw = final_status.get("error_count", -1)
        error_count = error_count_raw if isinstance(error_count_raw, int) else -1
        results.append(("error_count is 0", error_count == 0))

        # ── 9. Verify artifacts dict in status is non-empty ───────────
        artifacts_dict = final_status.get("artifacts", {})
        results.append((
            f"Status artifacts dict has {_TOTAL_PHASES} entries",
            isinstance(artifacts_dict, dict) and len(artifacts_dict) == _TOTAL_PHASES,
        ))

        # ── 10. Verify task and goal preserved ────────────────────────
        results.append(("Task preserved in status", final_status.get("task") == "Create README for memory module"))
        results.append(("Goal preserved in status", final_status.get("goal") == "Create comprehensive README with usage examples"))

    except ImportError as exc:
        results.append((f"Import failed: {exc}", False))
    except OSError as exc:
        # Evidence directory creation may fail on systems without /home/ path.
        results.append((f"Filesystem error (expected on some dev machines): {exc}", False))
    except Exception as exc:
        results.append((f"Unexpected error: {type(exc).__name__}: {exc}", False))
    finally:
        # ── Cleanup evidence directories ──────────────────────────────
        for d in evidence_dirs_to_clean:
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
        # Clean up parent dirs if empty (e.g., /home/guinevere/evidence/loops/date-id/).
        for d in evidence_dirs_to_clean:
            parent = d.parent
            while parent.exists() and parent != Path("/"):
                try:
                    if any(parent.iterdir()):
                        break
                    parent.rmdir()
                    parent = parent.parent
                except OSError:
                    break

    _print_results(results)
    return all(passed for _, passed in results)


def _print_results(results: list[tuple[str, bool]]) -> None:
    """Print formatted test results table."""
    print("\n" + "=" * 60)
    print("  P5-022: E2E Agent Loop Test — 7-Phase SDLC Cycle")
    print("=" * 60 + "\n")

    pass_count = 0
    fail_count = 0

    for name, passed in results:
        icon = "PASS" if passed else "FAIL"
        print(f"  [{icon}] {name}")
        if passed:
            pass_count += 1
        else:
            fail_count += 1

    total = pass_count + fail_count
    print(f"\n  {'─' * 50}")
    print(f"  Total: {total}  |  Passed: {pass_count}  |  Failed: {fail_count}")

    if fail_count == 0:
        print("\n  ALL TESTS PASSED")
    else:
        print("\n  SOME TESTS FAILED")

    print()


if __name__ == "__main__":
    success = asyncio.run(test_full_loop_cycle())
    sys.exit(0 if success else 1)
