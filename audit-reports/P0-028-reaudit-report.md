# P0-028 Re-Audit: Port Isolation Fix (scripts/preflight-check.sh)

**Date**: 2026-05-31
**Auditor**: Guinevere (parent)
**Scope**: Lines 238-259 of `scripts/preflight-check.sh`
**Change**: Port 5432 and 6379 checks changed from `log_fail` → `log_warn`
**Audit Type**: Re-audit after fix

---

## Verdict: PASS ✅

All 5 verification points confirmed. No findings.

---

## Verification Matrix

| # | Check | Expected | Actual (line) | Result |
|---|---|---|---|---|
| 1 | 5432 uses `log_warn` | `log_warn` | `log_warn` (line 246) | ✅ PASS |
| 1 | 6379 uses `log_warn` | `log_warn` | `log_warn` (line 254) | ✅ PASS |
| 2 | 5432 increments WARN | `((WARN++))` | `((WARN++))` (line 247) | ✅ PASS |
| 2 | 6379 increments WARN | `((WARN++))` | `((WARN++))` (line 255) | ✅ PASS |
| 3 | 5432 does NOT set OVERALL_EXIT=1 | absent | absent | ✅ PASS |
| 3 | 6379 does NOT set OVERALL_EXIT=1 | absent | absent | ✅ PASS |
| 4 | Inline comments explain Aizanta co-location | present | Lines 238-244 | ✅ PASS |
| 5 | 5432 WARN references Section 2 | "Section 2" | Line 246 | ✅ PASS |
| 5 | 6379 WARN references Section 3 | "Section 3" | Line 254 | ✅ PASS |

---

## Detailed Verification

### 1. Both checks use `log_warn` (not `log_fail`)

- Line 246: `log_warn "Port 5432 in use — may be Aizanta PostgreSQL (expected if Aizanta running). Guinevere confirmed on :5433 in Section 2."`
- Line 254: `log_warn "Port 6379 in use — may be Aizanta Redis (expected if Aizanta running). Guinevere confirmed on :6380 in Section 3."`
- Confirmed: no `log_fail` calls in the 238-259 region.

### 2. Both checks increment WARN counter

- Line 247: `((WARN++))` follows the 5432 warning.
- Line 255: `((WARN++))` follows the 6379 warning.
- The `FAIL` counter is not incremented in this block.

### 3. OVERALL_EXIT is not set to 1

- `log_warn` function (line 39): `log_warn() { echo "  [WARN] $*"; }` — echo only, no variable assignment.
- `OVERALL_EXIT=1` is only set in `log_fail` callers (`check_cmd` lines 48-50, `check_cmd_output` lines 62-64, `check_systemctl` lines 80-82, `check_systemctl_state` lines 107-109).
- Confirmed: neither the 5432 nor 6379 block touches `OVERALL_EXIT`.

### 4. Inline comments explain Aizanta co-location

Lines 238-244:
```
# Port isolation: check that Aizanta ports (5432, 6379) are not consumed by Guinevere.
# NOTE: ss -tlnp shows ALL system ports including Aizanta Docker containers.
# Aizanta's own services WILL appear on 5432/6379 — that is expected.
# The actual Guinevere-specific verification: Section 2 confirms pg_isready :5433,
# Section 3 confirms redis-cli PING :6380. Those already prove correct port binding.
# Here we flag unexpected usage as WARN only (not FAIL) since Aizanta co-location
# naturally occupies those ports.
```

Clear rationale: `ss -tlnp -n` scans all system ports → Aizanta Docker containers show on 5432/6379 → expected behavior → downgrade to WARN → actual Guinevere verification in Section 2/3.

### 5. WARN messages reference Section 2 and Section 3

- Line 246: `"...Guinevere confirmed on :5433 in Section 2."`
- Line 254: `"...Guinevere confirmed on :6380 in Section 3."`
- Section 2 in the script: PostgreSQL `pg_isready` check on port 5433.
- Section 3 in the script: Redis `redis-cli PING` check on port 6380.

---

## Script-Level Impact

The script's exit behavior is unchanged: `OVERALL_EXIT` is set to 0 at line 34 and only incremented by `log_fail` callers. Since these two checks now use `log_warn`, they only increment the `WARN` counter (logged in summary) and do not affect the final exit code via `exit "$OVERALL_EXIT"` (line 467).

**Before fix**: Aizanta co-location caused spurious FAIL → `OVERALL_EXIT=1`.
**After fix**: Aizanta co-location produces WARN only → `OVERALL_EXIT` stays 0 unless real failures exist.

---

## Cross-Reference: No Stale References

- Line 412: `# Aizanta port conflict: already checked in Section 5 port scan (5432, 6379)` — comment in Section 7, not a check. Consistent with the fix.
- No other `log_fail` references to 5432 or 6379 exist in the file.

---

## Summary

| Aspect | Result |
|---|---|
| Verification points passed | 5/5 |
| Findings | 0 |
| Blockers | None |
| Verdict | PASS |

**The port isolation fix is correct, complete, and safe.** The change from `log_fail` to `log_warn` correctly handles Aizanta co-location without suppressing real issues — actual Guinevere port binding is still verified in Section 2 (pg_isready :5433) and Section 3 (redis-cli PING :6380).