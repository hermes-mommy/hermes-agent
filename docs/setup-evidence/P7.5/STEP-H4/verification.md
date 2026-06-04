# STEP-H4 Verification: Crash-Loop Protection for guinevere-surveillance.service

## What Was Done
Added `StartLimitBurst=5` and `StartLimitIntervalSec=300` to the `[Service]` section of `systemd/guinevere-surveillance.service`, immediately after `RestartSec=10`. This prevents infinite crash-loop behavior by instructing systemd to stop restarting the service after 5 restarts within a 300-second (5-minute) window.

## Files Changed
- `systemd/guinevere-surveillance.service` -- lines 20-21 inserted

## Validation Results

### File Content Check
- `StartLimitBurst=5` present at line 20: PASS
- `StartLimitIntervalSec=300` present at line 21: PASS
- `Restart=always` unchanged at line 18: PASS
- `RestartSec=10` unchanged at line 19: PASS

### Grep Verification
- `StartLimitBurst` count: 1 -- PASS
- `StartLimitIntervalSec` count: 1 -- PASS

## Evidence Artifacts
- Modified file: `systemd/guinevere-surveillance.service` (38 lines, was 36)
- Diff: inserted `StartLimitBurst=5` and `StartLimitIntervalSec=300` after `RestartSec=10`

## Doc-Sync Impact
None -- this is a service unit file modification only.

## Boundary Compliance
- No persona/safety/surveillance/consent boundary affected
- No secrets or credentials exposed
- Purely operational hardening

## Rollback/Re-run Safety
- Re-run safe: both directives are idempotent (setting same values again is a no-op)
- Rollback: remove lines 20-21 to restore original behavior

## Design Decisions/Caveats
- 5 bursts in 5 minutes is conservative -- allows legitimate transient failures while capping resource waste from persistent bugs
- `StartLimitIntervalSec=300` aligns with systemd defaults for reasonable restart windows
- `Restart=always` is preserved so systemd still attempts restart within the limit window

## Auditor Gate
See `auditor-gate.md` in same directory.

## Security Scan
No security impact -- purely operational service management hardening.

## Acceptance Criteria Mapping
| Criterion | Status |
|---|---|
| StartLimitBurst added | PASS |
| StartLimitIntervalSec added | PASS |
| No other unit files modified | PASS |
| Restart=always preserved | PASS |
| RestartSec=10 preserved | PASS |
| Grep count = 1 for both directives | PASS |

## Footer
- **Step**: STEP-H4
- **Batch**: P7.5
- **Date**: 2026-06-03
- **Verifier**: Guinevere (parent)