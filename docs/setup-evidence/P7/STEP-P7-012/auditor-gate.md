# STEP-P7-012 — Android Tasker Setup Guide — Auditor Gate

## Verdict

**PENDING**, awaiting independent auditor review.

---

## Audit Scope

The auditor should verify the following:

| # | Check | Expected |
|---|---|---|
| 1 | All required sections present in guide | Prerequisites, Installation, Configuration, Profile Overview, HMAC Signing, Consent, Security, Troubleshooting, Testing |
| 2 | No hardcoded HMAC secrets | Zero literal secret values in any example or code block |
| 3 | No plaintext HTTP URLs | All URLs use `https://` scheme |
| 4 | No consent bypass instructions | Guide does not describe circumventing consent enforcement |
| 5 | No real data in examples | No real GPS coordinates, notification content, clipboard data, API endpoints, or domain names |
| 6 | Consent requirements covered | Four consent scopes described, revocation explained, safe mode noted |
| 7 | HMAC signing references P7-017 | Section 5 points to STEP-P7-017 for JavaScriptlet implementation |
| 8 | All four profiles covered | P7-013 (app usage), P7-014 (location), P7-015 (notifications), P7-016 (clipboard) |
| 9 | Security considerations complete | TLS-only, HMAC signing, replay protection, secret storage, data minimization |
| 10 | Verification accuracy | Claims in verification.md match the actual guide content |

---

## Findings Table

| # | Check | Result | Detail |
|---|---|---|---|
| 1 | Required sections | ⏳ PENDING | To be verified by auditor |
| 2 | No hardcoded secrets | ⏳ PENDING | To be verified by auditor |
| 3 | No plaintext HTTP | ⏳ PENDING | To be verified by auditor |
| 4 | No consent bypass | ⏳ PENDING | To be verified by auditor |
| 5 | No real data | ⏳ PENDING | To be verified by auditor |
| 6 | Consent coverage | ⏳ PENDING | To be verified by auditor |
| 7 | HMAC P7-017 reference | ⏳ PENDING | To be verified by auditor |
| 8 | Four profiles | ⏳ PENDING | To be verified by auditor |
| 9 | Security considerations | ⏳ PENDING | To be verified by auditor |
| 10 | Verification accuracy | ⏳ PENDING | To be verified by auditor |

---

## Footer

| Field | Value |
|---|---|
| **Step** | STEP-P7-012 |
| **Date** | 2026-06-02 |
| **Verdict** | **PENDING** |
| **Evidence path** | `docs/setup-evidence/P7/STEP-P7-012/verification.md` |
| **Guide path** | `docs/setup-evidence/P7/STEP-P7-012/tasker-setup-guide.md` |
| **Auditor** | To be assigned |
| **Next** | Independent auditor review |
