# STEP-H2 - P7-012 Signing String Format Fix - Verification

## What Was Done

Fixed the HMAC signing string format in `docs/setup-evidence/P7/STEP-P7-012/tasker-setup-guide.md` to use colon separators instead of newlines, matching the actual implementation in both server (auth.py) and client (hmac-sign.js).

## Files Changed

| File | Change |
|---|---|
| `docs/setup-evidence/P7/STEP-P7-012/tasker-setup-guide.md` | Section 5.1: replaced multi-line signing string with colon-separated format + explanation. Section 8.3: replaced `\n`-separated string with colon-separated format. All em dashes replaced with hyphens. |

## Validation Results

| Check | Command | Result |
|---|---|---|
| Zero em dashes | `grep -c "—"` | 0 matches - PASS |
| Colon format present | `grep "POST:/surveillance/events:"` | 2 matches (Section 5.1, Section 8.3) - PASS |
| Section 5.1 correct | Read lines 221-238 | `POST:/surveillance/events:{timestamp}:{nonce}:{request_body}` with explanation - PASS |
| Section 8.3 correct | Read lines 383-389 | `POST:/surveillance/events:{timestamp}:{nonce}:{body}` - PASS |

## Evidence Artifacts

- Grep output confirming 0 em dashes and 2 colon-format occurrences
- Read output confirming both sections display correct format

## Doc-Sync Impact

None. Only the tasker-setup-guide.md was modified; no cross-references or indexes affected.

## Boundary Compliance

- No secrets exposed
- No persona/safety boundary changes
- No consent/surveillance boundary changes
- Documentation-only fix

## Rollback/Re-run Safety

N/A. Documentation-only change, no code or database modifications.

The signing string format now matches both:
- Server: `f"{method}:{path}:{timestamp}:{nonce}:{body_str}"` (auth.py)
- Client: `method + ":" + path + ":" + timestamp + ":" + nonce + ":" + body.toString()` (hmac-sign.js)

## Design Decisions/Caveats

Replaced em dashes with hyphens per ANTI-AI-SLOP rules (zero tolerance for em dashes).

## Auditor Gate

See `docs/setup-evidence/P7.5/STEP-H2/auditor-gate.md`.

## Security Scan

No security impact. Documentation-only change.

## Acceptance Criteria Mapping

| Criterion | Status |
|---|---|
| Section 5.1 shows colon-separated format with explanation | PASS |
| Section 8.3 shows colon-separated format | PASS |
| Zero em dashes in file | PASS |
| No modification to hmac-sign.js | PASS (unchanged) |
| No modification to auth.py | PASS (unchanged) |
| No hardcoded secrets | PASS |

## Footer

| Field | Value |
|---|---|
| Step | STEP-H2 |
| Date | 2026-06-03 |
| Author | Guinevere (Sisyphus-Junior) |
| Scope | Fix P7-012 signing string format (HIGH priority) |
| Changed file | `docs/setup-evidence/P7/STEP-P7-012/tasker-setup-guide.md` |
| Evidence path | `docs/setup-evidence/P7.5/STEP-H2/` |