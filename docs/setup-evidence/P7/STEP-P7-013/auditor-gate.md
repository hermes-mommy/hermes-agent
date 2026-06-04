# STEP-P7-013 - Tasker App Usage Profile - Auditor Gate

## Verdict

**PENDING**, awaiting independent auditor review.

---

## Audit Scope

The auditor should verify the following:

| # | Check | Expected |
|---|---|---|
| 1 | Title matches | "P7-013: Tasker App Usage Profile" as first heading |
| 2 | All required sections present | Overview, Prerequisites, Profile Setup, Event Format, HMAC Signing, Consent, Battery Optimization, Troubleshooting, References |
| 3 | No hardcoded HMAC secrets | Zero literal secret values in any example or code block |
| 4 | No real app usage data | Only `com.example.app`, `com.example.browser`, or similar placeholder package names |
| 5 | No real API endpoints or device IDs | Only `%API_URL` and `%DEVICE_ID` variable references |
| 6 | References P7-012 setup guide | Prerequisites section and References table point to `docs/setup-evidence/P7/STEP-P7-012/` |
| 7 | References P7-017 HMAC JavaScriptlet | HMAC Signing section and References table point to `docs/setup-evidence/P7/STEP-P7-017/` |
| 8 | Event format matches Pydantic model | `event_type="app_usage"`, `device_id` string, `occurred_at` ISO 8601, `payload` dict with `app_name`, `action`, `duration_seconds` |
| 9 | Consent scope `surveillance.app_usage` mentioned | Appears in Prerequisites, Consent section, and/or HTTP error table |
| 10 | No em dashes | Text uses standard hyphens, commas, periods; no em dash characters |
| 11 | Entry and exit events both documented | Separate task definitions for app enter and app exit |
| 12 | Battery optimization strategy documented | Exponential backoff retry, event batching, or similar approach |
| 13 | Troubleshooting covers common issues | At minimum: profile not triggering, permissions, battery optimization |
| 14 | Verification accuracy | Claims in verification.md match the actual guide content |

---

## Findings Table

| # | Check | Result | Detail |
|---|---|---|---|
| 1 | Title matches | PENDING | To be verified by auditor |
| 2 | Required sections | PENDING | To be verified by auditor |
| 3 | No hardcoded secrets | PENDING | To be verified by auditor |
| 4 | No real app data | PENDING | To be verified by auditor |
| 5 | No real endpoints | PENDING | To be verified by auditor |
| 6 | P7-012 reference | PENDING | To be verified by auditor |
| 7 | P7-017 reference | PENDING | To be verified by auditor |
| 8 | Event format valid | PENDING | To be verified by auditor |
| 9 | Consent scope | PENDING | To be verified by auditor |
| 10 | No em dashes | PENDING | To be verified by auditor |
| 11 | Entry/exit events | PENDING | To be verified by auditor |
| 12 | Battery optimization | PENDING | To be verified by auditor |
| 13 | Troubleshooting | PENDING | To be verified by auditor |
| 14 | Verification accuracy | PENDING | To be verified by auditor |

---

## Footer

| Field | Value |
|---|---|
| **Step** | STEP-P7-013 |
| **Date** | 2026-06-03 |
| **Verdict** | **PENDING** |
| **Evidence path** | `docs/setup-evidence/P7/STEP-P7-013/verification.md` |
| **Guide path** | `docs/setup-evidence/P7/STEP-P7-013/tasker-app-usage.md` |
| **Auditor** | To be assigned |
| **Next** | Independent auditor review |
