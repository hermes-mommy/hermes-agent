# P4 Fix Plan (Executed)

**Date:** 2026-06-26

---

## Priority Order

| # | Fix | Status | Files Touched |
|---|-----|--------|---------------|
| 1 | Consent revocation Gate 10 | ✅ DONE | `src/hermes/safety_plugin.py` |
| 2 | Test Gate 10 consent enforcement | ✅ DONE | `tests/safety/test_gate_10_consent.py` (new) |
| 3 | Safety boundary regression tests | ✅ DONE | `tests/safety/test_safety_boundary_regression.py` (new) |
| 4 | Behavioral engines documentation | ✅ DONE | `p4-behavioral-engines-resolution.md` (new evidence) |
| 5 | Rituals deprecation documentation | ✅ DONE | `p4-rituals-deprecation-resolution.md` (new evidence) |
| 6 | Runtime verification | ✅ DONE | `p4-runtime-verification.md` (read-only) |
| 7 | Audit 1 | 🔄 IN PROGRESS | 7 parallel auditors |

## Deploy/Restart Impact

| Concern | Assessment |
|---------|------------|
| Deploy needed | Yes — `src/hermes/safety_plugin.py` is a live plugin on VPS. Needs `git pull && systemctl restart hermes-gateway` on VPS. |
| Restart scope | hermes-gateway.service ONLY |
| Rollback | `git checkout HEAD~1 -- src/hermes/safety_plugin.py && systemctl restart hermes-gateway` |
| DB migration | None |
| Secrets touched | None |

## Evidence Paths

All under `docs/setup-evidence/legacy-audit/P4/fix/`:
- `p4-runtime-preflight.md` — pre-fix read-only checks
- `p4-fix-plan.md` — this file
- `p4-consent-revocation-fix.md` — Gate 10 implementation
- `p4-behavioral-engines-resolution.md` — engine status per engine
- `p4-rituals-deprecation-resolution.md` — ritual deprecation cleanup
- `p4-safety-regression-tests.md` — test results (13/13 PASS)
- `p4-runtime-verification.md` — post-fix read-only VPS checks
- `audits/round-1/*.md` — audit reports
- `audits/round-2/*.md` — re-audit reports
- `p4-final-fix-report.md` — synthesis
- `p4-auditor-gate.md` — gate sign-off

## Hard Rejection Criteria

| Criterion | Status |
|-----------|--------|
| Gate 10 still says "deferred" | ✅ FIXED — now checks safe-mode |
| Consent bypass when safe-mode active | ✅ TESTED — no bypass |
| Y6 can activate | ✅ VERIFIED — 5 guards confirmed |
| HARD STOP bypassed | ✅ VERIFIED — all gates intact |
| Tests "PASS" when only collected | ✅ NOT CLAIMED — 13 tests actually executed |
| Secrets exposed | ✅ NONE — no message content in logs |
