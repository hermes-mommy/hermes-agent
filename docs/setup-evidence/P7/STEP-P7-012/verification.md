# STEP-P7-012 — Android Tasker Setup Guide — Verification

## 1. What Was Done

Created a comprehensive Android Tasker setup guide for Guinevere surveillance data collection. The guide covers prerequisites, installation, configuration, profile overview, HMAC signing reference, consent requirements, security considerations, troubleshooting, and testing.

**File created:**

| File | Action | Purpose |
|---|---|---|
| `docs/setup-evidence/P7/STEP-P7-012/tasker-setup-guide.md` | **CREATE** | Complete Tasker setup guide |

## 2. Files Changed

| File | Action | Purpose |
|---|---|---|
| `docs/setup-evidence/P7/STEP-P7-012/tasker-setup-guide.md` | **CREATE** | Tasker setup guide with 10 sections |
| `docs/setup-evidence/P7/STEP-P7-012/verification.md` | **CREATE** | This verification file |
| `docs/setup-evidence/P7/STEP-P7-012/auditor-gate.md` | **CREATE** | Auditor gate file (PENDING) |

## 3. Validation Results

### 3.1 Required Sections Checklist

| Section | Present | Notes |
|---|---|---|
| Prerequisites | ✅ YES | Android version, Tasker, plugins, permissions, battery optimization |
| Installation | ✅ YES | Step-by-step Play Store install, plugin setup, system settings |
| Configuration: %API_URL | ✅ YES | HTTPS endpoint setup, Cloudflare Tunnel and Tailscale options |
| Configuration: %HMAC_SECRET | ✅ YES | SOPS-decrypted value, runtime loading, never hardcoded in guide |
| Configuration: %DEVICE_ID | ✅ YES | UUID generation and setup |
| Profile Overview (P7-013 to P7-016) | ✅ YES | All four profiles described with event type, trigger, data, consent scope |
| HMAC Signing | ✅ YES | Signature computation, headers, body structure, P7-017 reference |
| Consent Requirements | ✅ YES | Consent scopes, grant/revoke flow, optional client-side check, safe mode |
| Security Considerations | ✅ YES | TLS only, HMAC signing, replay protection, secret storage, data minimization |
| Troubleshooting | ✅ YES | API errors, battery issues, HMAC mismatch, plugin issues |
| Testing | ✅ YES | Connectivity test, event submission test, per-profile test, HMAC verification, consent enforcement test |

### 3.2 Security Constraints Checklist

| Constraint | Status | Notes |
|---|---|---|
| No hardcoded HMAC secrets | ✅ PASS | All examples use `%HMAC_SECRET` variable reference; SOPS loading described |
| No plaintext HTTP URLs | ✅ PASS | All URLs use `https://`; placeholder uses `YOUR-ENDPOINT.example.com` |
| No consent bypass instructions | ✅ PASS | Guide describes consent enforcement, not circumvention |
| No real data in examples | ✅ PASS | Uses `com.test.example`, placeholder UUIDs, fake package names |
| No real API endpoints | ✅ PASS | Uses `https://YOUR-ENDPOINT.example.com` and `YOUR-TUNNEL-NAME.example.com` |
| No files outside specified paths | ✅ PASS | All files under `docs/setup-evidence/P7/STEP-P7-012/` |
| No source code modifications | ✅ PASS | Documentation-only step; no source files touched |

### 3.3 Content Quality Checks

| Check | Status | Notes |
|---|---|---|
| TLS referenced | ✅ PASS | Section 7.1 explicitly states HTTPS only, no plaintext HTTP |
| Consent covered | ✅ PASS | Section 6 covers all four consent scopes, grant/revoke, safe mode |
| HMAC reference to P7-017 | ✅ PASS | Section 5.4 references STEP-P7-017 JavaScriptlet |
| All four profiles covered | ✅ PASS | Sections 4.1 through 4.4 cover P7-013, P7-014, P7-015, P7-016 |
| Event flow described | ✅ PASS | Overview section includes full event flow diagram |
| Dependencies listed | ✅ PASS | Section 10 references all dependent steps |

## 4. Evidence Artifacts

| Artifact | Path |
|---|---|
| Setup guide | `docs/setup-evidence/P7/STEP-P7-012/tasker-setup-guide.md` |
| This verification | `docs/setup-evidence/P7/STEP-P7-012/verification.md` |
| Auditor gate (PENDING) | `docs/setup-evidence/P7/STEP-P7-012/auditor-gate.md` |

## 5. Doc-Sync Impact

| Document | Impact |
|---|---|
| P7 Planner | No edit needed. Guide implements what the planner describes for P7-012. |
| SurveillanceDataPolicy | Consistent. Guide covers the four Android source types within the 15-family scope. |
| ConsentRevocationPolicy | Consistent. Guide describes consent scopes and revocation via Discord. |
| Security Policy | Consistent. TLS-only, HMAC signing, no plaintext secrets. |

## 6. Boundary Compliance

| Boundary | Status | Evidence |
|---|---|---|
| No secret exposure | ✅ PASS | HMAC secret loaded from SOPS at runtime; never hardcoded or shown in examples |
| No consent bypass | ✅ PASS | Guide explains consent enforcement; client-side check is optional, API always enforces |
| Safe mode preserved | ✅ PASS | Section 6.4 explains safe mode pauses confrontation but preserves ingestion |
| No intimate data exposure | ✅ PASS | No real GPS, notification, or clipboard content in any example |
| HTTPS only | ✅ PASS | All URL examples use HTTPS; Section 7.1 explicitly forbids plaintext |

## 7. Rollback / Re-run Safety

| Operation | Safety |
|---|---|
| Delete guide | ✅ Safe. Documentation-only; no code dependencies. |
| Re-create guide | ✅ Idempotent. File overwrite with identical content. |

## 8. Design Decisions / Caveats

| Decision | Rationale | Caveat |
|---|---|---|
| Placeholder URLs instead of real endpoints | Prevent accidental leakage of real infrastructure | Users must replace placeholders with their actual endpoint |
| SOPS decryption described but not automated | Secret loading is a manual step on the device | Future: consider an encrypted push mechanism for secret rotation |
| Client-side consent check is optional | API enforces consent regardless; client check is bandwidth optimization | Users may skip this and rely on server-side enforcement |
| Profile details deferred to P7-013..016 | Each profile has its own dedicated step with full implementation | This guide provides overview only; detailed task actions live in profile-specific steps |

## 9. Auditor Gate

Auditor gate file: `docs/setup-evidence/P7/STEP-P7-012/auditor-gate.md`

Status: **PENDING**, awaiting independent auditor review.

## 10. Security Scan

| Check | Result | Notes |
|---|---|---|
| Hardcoded secrets | ✅ None | All secrets reference `%HMAC_SECRET` variable |
| Real endpoints | ✅ None | Placeholder URLs only |
| Real user data | ✅ None | Example payloads use fake package names and synthetic UUIDs |
| Plaintext HTTP | ✅ None | All URLs are HTTPS |
| Consent bypass | ✅ None | No instructions to circumvent consent |

## 11. Acceptance Criteria Mapping

| AC | Status | Verification |
|---|---|---|
| Prerequisites section with Android version, permissions | ✅ PASS | Section 1 covers device requirements, apps, permissions, battery |
| Step-by-step installation | ✅ PASS | Section 2 covers Play Store install and system settings |
| Configuration with API_URL, HMAC_SECRET, DEVICE_ID | ✅ PASS | Section 3 with three variables, SOPS loading for HMAC |
| Profile overview for P7-013 to P7-016 | ✅ PASS | Section 4 with four subsections |
| HMAC signing reference to P7-017 | ✅ PASS | Section 5 with canonical string, headers, body, and P7-017 reference |
| Consent requirements with scopes and revocation | ✅ PASS | Section 6 with four scopes, grant/revoke, safe mode |
| Security considerations with TLS and HMAC | ✅ PASS | Section 7 with five subsections |
| Troubleshooting section | ✅ PASS | Section 8 with four tables covering common issues |
| Testing section | ✅ PASS | Section 9 with five test procedures |
| No hardcoded secrets anywhere | ✅ PASS | Grep confirms zero hardcoded keys or tokens |
| No plaintext HTTP URLs | ✅ PASS | All URLs use https:// scheme |
| No real data in examples | ✅ PASS | All examples use synthetic placeholders |

## 12. Footer

| Field | Value |
|---|---|
| **Step** | STEP-P7-012 |
| **Date** | 2026-06-02 |
| **Implementation** | Direct parent execution (documentation-only step, no sub-agent delegation needed) |
| **Evidence path** | `docs/setup-evidence/P7/STEP-P7-012/verification.md` |
| **Auditor path** | `docs/setup-evidence/P7/STEP-P7-012/auditor-gate.md` (PENDING) |
| **Changed files** | 3 (all CREATE, all documentation) |
| **Source code changes** | 0 |
| **Anti-pattern scan** | No hardcoded secrets, no plaintext HTTP, no consent bypass, no real data |
| **Rollback** | Delete the three files under STEP-P7-012/ |
| **Boundary compliance** | All 5 boundaries verified PASS |
