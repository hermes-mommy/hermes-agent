# ADR-035 Phase 5 Wave 2 Step 5.2 — Drift Baseline Recompute (v2)

| Field | Value |
|---|---|
| Step | 5.2 — Drift Baseline Recompute |
| Wave | 2 (sequential after 5.1) |
| Evidence root | `docs/setup-evidence/phase-5/` |
| Planner authority | `planner-gate-phase-5-execution-v1.1.md` §12.2 |
| ADR authority | `adr/ADR-035-hermes-migration.md` §Phase 5 |
| Date | 2026-06-06 |
| Status | **PASS** |

---

## 1. What Was Done

Step 5.2 updated the drift baseline hash to match the finalized VPS `~/.hermes/SOUL.md` (508 lines, v2.0 with Oracle action items integrated). Three things were done:

1. **Computed SHA-256** of the current VPS `~/.hermes/SOUL.md` via SSH.
2. **Updated local constant** `SOUL_BASELINE_HASH` in `src/persona/drift_detector.py` — a single class-level `Final[str]` constant added to `DriftDetector`.
3. **Updated Redis DB0** key `guinevere:drift:baseline` to the same hash value.

No other files were modified. No drift detection logic, thresholds, safety boundaries, or KEEP VERBATIM files were touched.

---

## 2. Files Changed

| File | Operation | Change Description |
|---|---|---|
| `src/persona/drift_detector.py` | NARROW MODIFY | Added `SOUL_BASELINE_HASH: Final[str] = "b8d55fe72f657c93b497e8f5001c7035faf4fa7ab7174b68a25c2ee1cafe9740"` as a single class-level constant. One-line addition only. |
| `docs/setup-evidence/phase-5/verification-5-2-v2.md` | CREATE | This evidence file. |
| Redis DB0 `guinevere:drift:baseline` | MODIFY (remote) | Set to `b8d55fe72f657c93b497e8f5001c7035faf4fa7ab7174b68a25c2ee1cafe9740` |

### Step 5.2 protected files not changed (KEEP VERBATIM confirmed):

- `src/persona/yandere_fsm.py` — zero diff for Step 5.2 (verified)
- `src/persona/safe_mode.py` — zero diff for Step 5.2 (verified)
- `src/persona/drift_corrector.py` — zero diff for Step 5.2 (verified)
- `src/persona/drift_detector.py` — only the `SOUL_BASELINE_HASH` class constant was added; drift logic remained unchanged

Note: Wave 1 Step 5.7 intentionally changed other persona files (`mood_persistence.py`, `rituals/__init__.py`) under its own scaffold and evidence. This Step 5.2 evidence only claims the Step 5.2 drift baseline scope.

---

## 3. Validation Results

### 3.1 Git Diff — One-Line Constraint

```diff
diff --git a/src/persona/drift_detector.py b/src/persona/drift_detector.py
index 1497537..d969f71 100644
--- a/src/persona/drift_detector.py
+++ b/src/persona/drift_detector.py
@@ -59,6 +59,7 @@ class DriftDetector:
     """
 
     DEFAULT_THRESHOLD: Final[float] = 0.10
+    SOUL_BASELINE_HASH: Final[str] = "b8d55fe72f657c93b497e8f5001c7035faf4fa7ab7174b68a25c2ee1cafe9740"
 
     def __init__(
         self,
```

**Result:** PASS — exactly one line added, no other diff.

### 3.2 Hash Format Validation

```python
python -c "from src.persona.drift_detector import DriftDetector; h=DriftDetector.SOUL_BASELINE_HASH; assert len(h)==64 and all(c in '0123456789abcdef' for c in h); print('valid:', h[:16])"
# Output: valid: b8d55fe72f657c93
```

**Result:** PASS — 64-character lowercase hex string.

### 3.3 VPS SOUL.md SHA-256

```bash
ssh guinevere-vps "sha256sum ~/.hermes/SOUL.md"
# Output: b8d55fe72f657c93b497e8f5001c7035faf4fa7ab7174b68a25c2ee1cafe9740  /home/guinevere/.hermes/SOUL.md
```

**Result:** PASS — hash computed, no secret values exposed.

### 3.4 Redis DB0 Key Readback

```bash
ssh guinevere-vps 'source /home/guinevere/code/guinevere/.env.discord 2>/dev/null; redis-cli -p 6380 -n 0 -a "$REDIS_PASSWORD" --no-auth-warning GET guinevere:drift:baseline'
# Output: b8d55fe72f657c93b497e8f5001c7035faf4fa7ab7174b68a25c2ee1cafe9740
```

**Result:** PASS — Redis key matches. No password printed in evidence.

### 3.5 Hash Equality Verification

| Source | Hash | Match? |
|---|---|---|
| VPS `~/.hermes/SOUL.md` SHA-256 | `b8d55fe72f657c93b497e8f5001c7035faf4fa7ab7174b68a25c2ee1cafe9740` | ✅ |
| `DriftDetector.SOUL_BASELINE_HASH` constant | `b8d55fe72f657c93b497e8f5001c7035faf4fa7ab7174b68a25c2ee1cafe9740` | ✅ |
| Redis DB0 `guinevere:drift:baseline` | `b8d55fe72f657c93b497e8f5001c7035faf4fa7ab7174b68a25c2ee1cafe9740` | ✅ |

**Result:** PASS — all three values are identical.

### 3.6 LSP Diagnostics

```bash
lsp_diagnostics src/persona/drift_detector.py
```

| Severity | Count | Introduced? | Details |
|---|---|---|---|
| Error | 0 | None | — |
| Warning | 4 | **Pre-existing** | `reportAny` on structlog `logger` type and `.warning()`, `.info()` calls at lines 12, 109, 164, 184. Present before change. |
| Information | 0 | None | — |
| Hint | 0 | None | — |

**Result:** PASS — no new diagnostics introduced. All 4 warnings are pre-existing structlog type inference limitations.

### 3.7 Drift Detection Active — Smoke Test

```python
from src.persona.drift_detector import DriftDetector, DriftBaseline
d = DriftDetector(baseline=DriftBaseline(prompt_hash=DriftDetector.SOUL_BASELINE_HASH, ...))
r1 = d.detect(DriftDetector.SOUL_BASELINE_HASH)  # exact match -> 0.0 drift
r2 = d.detect('a' * 64)  # different -> 0.921875 drift
```

**Result:** PASS — drift detection remains fully active with the new baseline hash. Exact match: drift_score=0.0. Different hash: drift_score=0.921875.

### 3.8 Import/Boundary Check

```python
from src.persona.drift_detector import DriftDetector, DriftBaseline, DriftResult
from src.persona.drift_corrector import DriftCorrector
from src.persona.yandere_fsm import YandereEngine, YandereLevel
# All imports OK
```

**Result:** PASS — all drift and yandere safety modules import cleanly.

---

## 4. Evidence Artifacts

| Artifact | Path |
|---|---|
| This evidence file | `docs/setup-evidence/phase-5/verification-5-2-v2.md` |
| Modified drift detector | `src/persona/drift_detector.py` |
| Planner gate v1.1 | `docs/setup-evidence/phase-5/planner-gate-phase-5-execution-v1.1.md` |
| Previous version (v1) | `docs/setup-evidence/phase-5/verification-5-2.md` |

---

## 5. Doc-Sync Impact

| Document | Impact |
|---|---|
| `src/persona/drift_detector.py` | `SOUL_BASELINE_HASH` constant updated to current SOUL.md hash |
| No ADRs affected | N/A — narrow hash-only change |
| No evidence indexes | Evidence path remains under `docs/setup-evidence/phase-5/` |

---

## 6. Boundary Compliance

- **Y4/Y5/Y6 boundaries**: Untouched. `yandere_fsm.py` is KEEP VERBATIM.
- **HARD STOP protocol**: Untouched. `safe_mode.py` is KEEP VERBATIM.
- **Consent/distress logic**: Untouched. `drift_corrector.py` is KEEP VERBATIM.
- **Drift detection**: Remains active. Only the baseline hash constant changed.
- **Redis password**: Never printed. Sourced from existing `.env.discord` file via shell variable, used only for the `redis-cli` authentication flag.
- **No secrets exposed**: All evidence shows `<redacted>` or non-secret summaries.

**Result:** PASS — all safety boundaries preserved.

---

## 7. Rollback/Re-run Safety

- **Rollback time**: < 1 minute. Two operations:
  1. `git checkout HEAD -- src/persona/drift_detector.py` to restore old hash constant.
  2. `ssh guinevere-vps 'source ...; redis-cli ... SET guinevere:drift:baseline <old-hash>'` to restore old Redis value.
- **Re-run safety**: Fully idempotent. Running Step 5.2 again with the same SOUL.md would produce the same hash and result in no changes.
- **No destructive operations**: Read-only SSH commands; one `SET` key operation.

---

## 8. Design Decisions/Caveats

| Decision | Rationale |
|---|---|
| `SOUL_BASELINE_HASH` added as `Final[str]` class constant on `DriftDetector` | Follows existing pattern (`DEFAULT_THRESHOLD: Final[float]`). Allows both standalone usage (`DriftDetector.SOUL_BASELINE_HASH`) and instance access. |
| Hash sourced from VPS SOUL.md, not local copy | VPS is production runtime. The drift detector runs in-process with Hermes on VPS, so the baseline must match the runtime SOUL.md. |
| `.env.discord` used for Redis auth | This is the existing env file that contains `REDIS_PASSWORD` on VPS. Sourced before redis-cli invocation; password never echoed. |
| `--no-auth-warning` flag | Suppresses Redis warning about password on command line when source-env method is used. |
| Static constitution vs dynamic state | `SOUL.md` is the static constitution — rarely changed, version-controlled baseline. Dynamic persona state (mood, yandere level, punishment) remains in PersonaPlugin/Redis DB5, outside drift detection scope. |

---

## 9. Auditor Gate

| Criterion | Verdict | Evidence |
|---|---|---|
| Hash constant is 64-char lowercase hex | PASS | `python -c` validation |
| No other changes to drift_detector.py | PASS | `git diff` shows one-line addition only |
| KEEP VERBATIM files unchanged for Step 5.2 | PASS | `git diff` against `yandere_fsm.py`, `safe_mode.py`, and `drift_corrector.py` returns empty; `drift_detector.py` diff is limited to `SOUL_BASELINE_HASH` |
| Hash matches VPS SOUL.md | PASS | SHA-256 computation matches constant |
| Hash matches Redis DB0 key | PASS | `redis-cli GET` returns same hash |
| Drift detection still active | PASS | Smoke test: exact match → 0.0, different → 0.92 |
| No new LSP diagnostics | PASS | 4 pre-existing warnings only |
| No secrets exposed in evidence | PASS | Redis password never printed |
| Redis update succeeded (OK) | PASS | `redis-cli SET` returned "OK" |

**Overall Auditor Verdict:** PASS ✅

---

## 10. Security Scan

| Check | Result | Notes |
|---|---|---|
| No secrets committed | ✅ PASS | No credentials in code or evidence |
| No type suppression | ✅ PASS | No `as any`, `# type: ignore`, `@ts-ignore`, `@ts-expect-error` |
| No empty catch blocks | ✅ PASS | No bare `except:` or empty `except Exception:` |
| No drift detection disabled | ✅ PASS | `SOUL_BASELINE_HASH` is a data constant, not a logic bypass |
| No safety boundary weakened | ✅ PASS | Thresholds, Y4/Y5/Y6, HARD STOP, consent all untouched |
| Redis password not printed | ✅ PASS | Sourced from env file and passed via variable; only "OK" and hash in output |

---

## 11. Acceptance Criteria Mapping

| Criterion from Task | Result | Verdict |
|---|---|---|
| VPS SOUL SHA-256 computed | `b8d55fe72f657c93...` | PASS |
| `drift_detector.py` has ONLY SOUL_BASELINE_HASH changed | One-line diff, no other changes | PASS |
| Redis DB0 `guinevere:drift:baseline` updated | SET returned "OK", GET returns same hash | PASS |
| Local constant == SOUL SHA == Redis key | All three identical | PASS |
| `lsp_diagnostics` clean (no new errors) | 0 new errors, 4 pre-existing warnings | PASS |
| Import/boundary check passes | All modules import, drift detection active | PASS |
| Evidence written (12-section schema) | This file | PASS |
| No secrets printed | Password never echoed | PASS |
| Step 5.2 changed only `drift_detector.py`, this evidence file, and Redis DB0 baseline key | Confirmed by parent diff review; earlier Wave 1 persona/evidence changes are tracked separately | PASS |

---

## 12. Footer

### Command Summary (non-secret)

```bash
# 1. Compute current SOUL hash
ssh guinevere-vps "sha256sum ~/.hermes/SOUL.md"
# Output: b8d55fe72f657c93b497e8f5001c7035faf4fa7ab7174b68a25c2ee1cafe9740

# 2. Add SOUL_BASELINE_HASH constant to drift_detector.py
# (One-line edit, verified via git diff)

# 3. Update Redis DB0 key
ssh guinevere-vps 'source /home/guinevere/code/guinevere/.env.discord 2>/dev/null; redis-cli -p 6380 -n 0 -a "$REDIS_PASSWORD" --no-auth-warning SET guinevere:drift:baseline b8d55fe72f657c93b497e8f5001c7035faf4fa7ab7174b68a25c2ee1cafe9740'
# Output: OK

# 4. Verify Redis key
ssh guinevere-vps 'source /home/guinevere/code/guinevere/.env.discord 2>/dev/null; redis-cli -p 6380 -n 0 -a "$REDIS_PASSWORD" --no-auth-warning GET guinevere:drift:baseline'
# Output: b8d55fe72f657c93b497e8f5001c7035faf4fa7ab7174b68a25c2ee1cafe9740

# 5. Validate hash format
python -c "from src.persona.drift_detector import DriftDetector; h=DriftDetector.SOUL_BASELINE_HASH; assert len(h)==64 and all(c in '0123456789abcdef' for c in h); print('valid:', h[:16])"
# Output: valid: b8d55fe72f657c93

# 6. Verify drift detection active
python -c "
from src.persona.drift_detector import DriftDetector, DriftBaseline
from datetime import datetime, timezone
d = DriftDetector(baseline=DriftBaseline(prompt_hash=DriftDetector.SOUL_BASELINE_HASH, version='v2', created_at=datetime.now(timezone.utc)))
r1 = d.detect(DriftDetector.SOUL_BASELINE_HASH)
r2 = d.detect('a' * 64)
print(f'Exact: {r1.drift_score}, Diff: {r2.drift_score}')
"
```

### Versioning

| Version | Date | Author | Changes |
|---|---|---|---|
| 2.0 | 2026-06-06 | Guinevere (Parent Orchestrator) | Initial v2 evidence for Step 5.2 drift baseline recompute after finalized SOUL.md (508 lines). Hash `b8d55fe72f657c93...`. |
| 1.0 | 2026-06-05 | Guinevere (sub-agent) | Original Step 5.2 evidence with old hash. Superseded by v2. |

### Notes

- SOUL.md is the **static constitution** — a rarely-changed, version-controlled definition of Guinevere's persona and safety constraints.
- **Dynamic persona state** (mood, yandere level, punishment, rewards) lives in Redis DB5 via PersonaPlugin and is outside drift detection scope.
- This hash update is required after any intentional SOUL.md change (including Oracle action items in Step 5.1) to re-sync the drift baseline.
