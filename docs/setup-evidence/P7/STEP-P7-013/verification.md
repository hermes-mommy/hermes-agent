# STEP-P7-013 - Tasker App Usage Profile - Verification

## 1. What Was Done

Created documentation for the Tasker app usage profile that tracks foreground app name and duration via entry/exit events. The guide covers profile setup, event format, HMAC signing, consent requirements, battery optimization, and troubleshooting.

**File created:**

| File | Action | Purpose |
|---|---|---|
| `docs/setup-evidence/P7/STEP-P7-013/tasker-app-usage.md` | **CREATE** | Complete app usage profile documentation |

## 2. Files Changed

| File | Action | Purpose |
|---|---|---|
| `docs/setup-evidence/P7/STEP-P7-013/tasker-app-usage.md` | **CREATE** | App usage profile guide with all required sections |
| `docs/setup-evidence/P7/STEP-P7-013/verification.md` | **CREATE** | This verification file |
| `docs/setup-evidence/P7/STEP-P7-013/auditor-gate.md` | **CREATE** | Auditor gate file (PENDING) |

## 3. Validation Results

### 3.1 Required Sections Checklist

| Section | Present | Notes |
|---|---|---|
| Overview | YES | Describes foreground app tracking via entry/exit events |
| Prerequisites | YES | Tasker 5.8+, AutoTools (optional), HMAC config from P7-012, Usage Access, battery optimization, consent |
| Profile Setup: Trigger | YES | Application context type for app enter/exit |
| Profile Setup: Entry Task | YES | Captures app name, timestamp, builds payload, HMAC signs, POSTs |
| Profile Setup: Exit Task | YES | Captures duration, builds payload, HMAC signs, POSTs |
| Event Format | YES | JSON payload with entry and exit examples, field reference table |
| HMAC Signing | YES | References P7-017 for JavaScriptlet, describes headers and process |
| Consent | YES | Scope `surveillance.app_usage`, grant/revoke flow, optional client-side check |
| Battery Optimization | YES | Exponential backoff retry, event batching, Android battery settings |
| Troubleshooting | YES | Profile not triggering, HTTP errors, data issues, HMAC mismatch |

### 3.2 Security Constraints Checklist

| Constraint | Status | Notes |
|---|---|---|
| No hardcoded HMAC secrets | PASS | All references use `%HMAC_SECRET` variable |
| No real app usage data | PASS | Uses `com.example.app` and `com.example.browser` only |
| No real API endpoints | PASS | Uses `%API_URL` variable reference |
| No real device IDs | PASS | Uses `%DEVICE_ID` variable reference |
| No em dashes | PASS | Verified by text scan; uses commas, periods, and standard hyphens only |
| No files outside specified paths | PASS | All files under `docs/setup-evidence/P7/STEP-P7-013/` |
| No source code modifications | PASS | Documentation-only step |

### 3.3 Reference Checks

| Reference | Status | Notes |
|---|---|---|
| P7-012 setup guide | PASS | Referenced in Prerequisites table, Battery Optimization, and References section |
| P7-017 HMAC JavaScriptlet | PASS | Referenced in Profile Setup actions, HMAC Signing section, and References section |
| SurveillanceEventRequest model | PASS | Event format matches Pydantic model fields: `event_type`, `device_id`, `occurred_at`, `payload` |
| Consent scope `surveillance.app_usage` | PASS | Mentioned in Prerequisites, Consent section, and HTTP error table |

### 3.4 Event Format Validation

| Field | Expected | Actual | Match |
|---|---|---|---|
| `event_type` | `"app_usage"` (Literal) | `"app_usage"` | PASS |
| `device_id` | string (min 1, max 128) | `"%DEVICE_ID"` variable | PASS |
| `occurred_at` | ISO 8601 with timezone | `"2026-01-01T12:00:00Z"` | PASS |
| `payload` | dict | JSON object with `app_name`, `action`, `duration_seconds` | PASS |
| No extra top-level fields | forbidden | None present | PASS |

### 3.5 Content Quality Checks

| Check | Status | Notes |
|---|---|---|
| Entry event example present | PASS | JSON block with `action: "enter"`, `duration_seconds: null` |
| Exit event example present | PASS | JSON block with `action: "exit"`, `duration_seconds: 330` |
| Field reference table present | PASS | All six fields documented with types and descriptions |
| HMAC headers documented | PASS | Content-Type, X-Signature, X-Timestamp, X-Nonce with values |
| Retry strategy documented | PASS | Exponential backoff (30s, 60s, 120s) with batch fallback |
| Troubleshooting covers common issues | PASS | Four categories: profile not triggering, HTTP errors, data issues, HMAC mismatch |

## 4. Evidence Artifacts

| Artifact | Path |
|---|---|
| App usage guide | `docs/setup-evidence/P7/STEP-P7-013/tasker-app-usage.md` |
| This verification | `docs/setup-evidence/P7/STEP-P7-013/verification.md` |
| Auditor gate (PENDING) | `docs/setup-evidence/P7/STEP-P7-013/auditor-gate.md` |

## 5. Doc-Sync Impact

| Document | Impact |
|---|---|
| P7-012 Setup Guide | No edit needed. Guide is referenced as prerequisite. |
| P7-017 HMAC JavaScriptlet | No edit needed. Guide is referenced for signing implementation. |
| P7 Planner | No edit needed. Guide implements what the planner describes for P7-013. |
| SurveillanceDataPolicy | Consistent. Profile collects app usage data within the defined scope. |
| ConsentRevocationPolicy | Consistent. Guide describes consent scope and revocation behavior. |

## 6. Boundary Compliance

| Boundary | Status | Evidence |
|---|---|---|
| No secret exposure | PASS | HMAC secret referenced via `%HMAC_SECRET` variable only |
| No consent bypass | PASS | Guide explains consent enforcement, not circumvention |
| No intimate data exposure | PASS | No real app names, usage data, or device identifiers in examples |
| HTTPS only | PASS | `%API_URL` references HTTPS endpoint per P7-012 configuration |
| Consent scope enforced | PASS | `surveillance.app_usage` scope documented; API rejection behavior explained |

## 7. Rollback / Re-run Safety

| Operation | Safety |
|---|---|
| Delete guide | Safe. Documentation-only; no code dependencies. |
| Re-create guide | Idempotent. File overwrite with identical content. |

## 8. Design Decisions / Caveats

| Decision | Rationale | Caveat |
|---|---|---|
| Entry and exit events as separate requests | Matches Tasker's native Application context behavior; simpler to implement | Two HTTP requests per app switch instead of one combined event |
| `%APP` as primary package source | Built-in Tasker variable; no plugin dependency | May require shell fallback on some Android versions; alternative documented |
| Exponential backoff for retries | Prevents battery drain on poor connections | Events may arrive late; ordering by `occurred_at` handles this server-side |
| Optional client-side consent check | Saves bandwidth; API enforces regardless | Adds complexity to profile; users may skip it |
| Batch storage in Tasker array | Simple fallback for offline events | Array limited by Tasker memory; cap at 50 events recommended |

## 9. Auditor Gate

Auditor gate file: `docs/setup-evidence/P7/STEP-P7-013/auditor-gate.md`

Status: **PENDING**, awaiting independent auditor review.

## 10. Security Scan

| Check | Result | Notes |
|---|---|---|
| Hardcoded secrets | None | All secrets reference `%HMAC_SECRET` variable |
| Real endpoints | None | Uses `%API_URL` placeholder |
| Real user data | None | Examples use `com.example.app`, `com.example.browser`, synthetic timestamps |
| Plaintext HTTP | None | HTTPS only via `%API_URL` configuration from P7-012 |
| Consent bypass | None | No instructions to circumvent consent |
| Em dashes | None | Text uses standard hyphens and punctuation only |

## 11. Acceptance Criteria Mapping

| AC | Status | Verification |
|---|---|---|
| Title: "P7-013: Tasker App Usage Profile" | PASS | First heading matches exactly |
| Overview section with entry/exit events | PASS | Describes both event types and flow |
| Prerequisites: Tasker 5.8+, AutoTools optional, HMAC from P7-012 | PASS | Table with all three items |
| Profile Setup with step-by-step instructions | PASS | Four steps: create profile, entry task, exit task, activate |
| Trigger: Application context | PASS | Step 1 selects Application context type |
| Entry Task: capture, sign, POST | PASS | Five actions covering the full flow |
| Exit Task: capture, sign, POST | PASS | Four actions covering the full flow |
| Event Format: JSON matching SurveillanceEventRequest | PASS | Two examples plus field reference table |
| HMAC Signing: reference P7-017 | PASS | Dedicated section with signing process and header table |
| Consent: scope `surveillance.app_usage` | PASS | Dedicated section with grant/revoke flow |
| Battery Optimization: batch + exponential backoff | PASS | Retry strategy and batching documented |
| Troubleshooting: common issues | PASS | Four categories with symptoms, causes, fixes |
| No real data in examples | PASS | Only `com.example.app`, `com.example.browser`, synthetic UUIDs |
| No hardcoded secrets | PASS | All references use Tasker variables |
| No em dashes | PASS | Verified by text scan |
| References P7-012 | PASS | Prerequisites, Battery Optimization, References section |
| References P7-017 | PASS | HMAC Signing section, Profile Setup actions, References section |

## 12. Footer

| Field | Value |
|---|---|
| **Step** | STEP-P7-013 |
| **Date** | 2026-06-03 |
| **Implementation** | Direct parent execution (documentation-only step) |
| **Evidence path** | `docs/setup-evidence/P7/STEP-P7-013/verification.md` |
| **Auditor path** | `docs/setup-evidence/P7/STEP-P7-013/auditor-gate.md` (PENDING) |
| **Changed files** | 3 (all CREATE, all documentation) |
| **Source code changes** | 0 |
| **Anti-pattern scan** | No hardcoded secrets, no real data, no em dashes, no consent bypass |
| **Rollback** | Delete the three files under STEP-P7-013/ |
| **Boundary compliance** | All 5 boundaries verified PASS |
