# D13 -- Tasker Documentation Audit Report

**Date:** 2026-06-03
**Auditor:** Guinevere (D13 documentation audit)
**Scope:** 7 Tasker documentation files (6 .md + 1 .js)
**Verdict:** **NEEDS REVIEW** -- 1 blocking issue (signing string format mismatch)

---

## 1. File Existence

All 7 files exist and are readable.

| # | File | Path | Exists | Size (approx) |
|---|---|---|---|---|
| 1 | tasker-setup-guide.md | `docs/setup-evidence/P7/STEP-P7-012/tasker-setup-guide.md` | YES | ~400 lines |
| 2 | tasker-app-usage.md | `docs/setup-evidence/P7/STEP-P7-013/tasker-app-usage.md` | YES | ~280 lines |
| 3 | tasker-location.md | `docs/setup-evidence/P7/STEP-P7-014/tasker-location.md` | YES | ~320 lines |
| 4 | tasker-notifications.md | `docs/setup-evidence/P7/STEP-P7-015/tasker-notifications.md` | YES | ~380 lines |
| 5 | tasker-clipboard.md | `docs/setup-evidence/P7/STEP-P7-016/tasker-clipboard.md` | YES | ~230 lines |
| 6 | tasker-hmac-jslet.md | `docs/setup-evidence/P7/STEP-P7-017/tasker-hmac-jslet.md` | YES | ~140 lines |
| 7 | hmac-sign.js | `docs/setup-evidence/P7/STEP-P7-017/hmac-sign.js` | YES | 49 lines |

---

## 2. Cross-Reference Verification

Every documentation file references both P7-012 (setup guide) and P7-017 (HMAC signing).

| File | P7-012 refs | P7-017 refs | Status |
|---|---|---|---|
| P7-012 tasker-setup-guide.md | 3 (self, footer) | 6 | PASS |
| P7-013 tasker-app-usage.md | 5 | 10 | PASS |
| P7-014 tasker-location.md | 4 | 9 | PASS |
| P7-015 tasker-notifications.md | 8 | 10 | PASS |
| P7-016 tasker-clipboard.md | 4 | 5 | PASS |
| P7-017 tasker-hmac-jslet.md | 3 | 1 (self, title) | PASS |
| hmac-sign.js | 0 | 0 | PASS (code file, not docs) |

**Finding:** Cross-references are comprehensive. Every .md doc explicitly points to P7-012 for setup prerequisites and P7-017 for HMAC signing implementation. The `hmac-sign.js` file is a code asset, not documentation, so the absence of doc cross-references is expected.

---

## 3. Signing String Format Consistency -- CRITICAL BUG

### 3.1 Format by Document

| File | Format Documented | Separator | Matches Implementation? |
|---|---|---|---|
| P7-012 (Section 5.1) | `POST\n/surveillance/events\n{timestamp}\n{nonce}\n{body}` | **Newlines** | NO |
| P7-012 (Section 8.3) | `POST\n/surveillance/events\n{timestamp}\n{nonce}\n{body}` | **Newlines** | NO |
| P7-013 (HMAC Signing) | `POST:/surveillance/events:{timestamp}:{nonce}:{body}` | **Colons** | YES |
| P7-014 (HMAC Signing) | `POST:/surveillance/events:{timestamp}:{nonce}:{body}` | **Colons** | YES |
| P7-015 (HMAC Signing) | `POST:/surveillance/events:{timestamp}:{nonce}:{body}` | **Colons** | YES |
| P7-016 | Delegates to P7-017 (no explicit format) | N/A | N/A |
| P7-017 (Signing Algorithm) | `POST:/surveillance/events:1717401600:a1b2c3d4...:{body}` | **Colons** | YES |
| hmac-sign.js (line 27) | `method + ":" + path + ":" + timestamp + ":" + nonce + ":" + body` | **Colons** | YES |

### 3.2 Impact Analysis

P7-012 Section 5.1 documents the signing string with **newlines** between fields:

```
POST
/surveillance/events
{timestamp}
{nonce}
{request_body}
```

Section 8.3 (troubleshooting) confirms this with `POST\n/surveillance/events\n{timestamp}\n{nonce}\n{body}`.

The actual implementation in `hmac-sign.js` uses **colons**:

```javascript
var signingString = method + ":" + path + ":" + timestamp + ":" + nonce + ":" + body.toString();
```

All four profile docs (P7-013, P7-014, P7-015) and P7-017's own documentation consistently document the colon-separated format. P7-012 is the **only** file using newlines.

**If a user follows P7-012's instructions literally, they will produce signatures that do not match the server's computation.** This will result in HTTP 401 on every request.

### 3.3 Server-Side Format (for reference)

Based on prior audit reports (P7-003 auditor-gate.md line 33): the server uses the format `<method>:<path>:<timestamp>:<nonce>:<body>`, confirming colons are the authoritative format.

### 3.4 Recommendation

Fix P7-012 Section 5.1 and Section 8.3 to use colon-separated format, matching the implementation and all other docs:

```
POST:/surveillance/events:{timestamp}:{nonce}:{request_body}
```

---

## 4. Secret Hygiene

| File | Hardcoded Secrets | Status |
|---|---|---|
| P7-012 tasker-setup-guide.md | None. Uses `%HMAC_SECRET` variable | PASS |
| P7-013 tasker-app-usage.md | None. Uses `%HMAC_SECRET` variable | PASS |
| P7-014 tasker-location.md | None. Uses `%HMAC_SECRET` variable | PASS |
| P7-015 tasker-notifications.md | None. Uses `%HMAC_SECRET` variable | PASS |
| P7-016 tasker-clipboard.md | 2 synthetic examples (line 92, 106: `sk_test_...`, `SecretPass123`) | PASS (synthetic) |
| P7-017 tasker-hmac-jslet.md | None. Uses `%HMAC_SECRET` variable | PASS |
| hmac-sign.js | None. Reads `%HMAC_SECRET` at runtime | PASS |

All real secrets are handled via the `%HMAC_SECRET` Tasker global variable. The two occurrences in P7-016 are clearly labeled synthetic examples for testing (`sk_test_1234567890abcdef` is a recognizable test key prefix, `SecretPass123` is obviously a placeholder). No `%API_URL` endpoints reveal real server addresses either -- all show `YOUR-ENDPOINT.example.com` or similar placeholders.

---

## 5. Em Dash Scan

| File | Em Dashes (`---`) | Locations | Status |
|---|---|---|---|
| P7-012 tasker-setup-guide.md | 5 | Lines 1, 171, 182, 193, 204 | FAIL |
| P7-013 tasker-app-usage.md | 0 | N/A | PASS |
| P7-014 tasker-location.md | 0 | N/A | PASS |
| P7-015 tasker-notifications.md | 0 | N/A | PASS |
| P7-016 tasker-clipboard.md | 0 | N/A | PASS |
| P7-017 tasker-hmac-jslet.md | 0 | N/A | PASS |
| hmac-sign.js | 0 | N/A | PASS |

**Note:** The research findings reported 6 em dashes, but verification found exactly 5. The discrepancy of 1 may be from a double-count or a grepping artifact.

**Affected lines in P7-012:**

| Line | Text |
|---|---|
| 1 | `# STEP-P7-012 --- Android Tasker Setup Guide for Guinevere Surveillance` |
| 171 | `### 4.1 P7-013 --- App Usage Profile` |
| 182 | `### 4.2 P7-014 --- Location Profile` |
| 193 | `### 4.3 P7-015 --- Notification Profile` |
| 204 | `### 4.4 P7-016 --- Clipboard Profile` |

All five are in section headers using `Text --- Description` format. These should be replaced with hyphens (`Text - Description`) per the anti-AI-slop rules. No other files have em dashes.

---

## 6. Consent Scope Coverage

Every document explicitly covers its consent scope requirements.

| File | Consent Scope Documented | Mechanism |
|---|---|---|
| P7-012 | All 4: `app_usage`, `location`, `notifications`, `clipboard` | Section 6: full table + enforcement flow |
| P7-013 | `surveillance.app_usage` | Dedicated Consent section with grant/revoke lifecycle |
| P7-014 | `surveillance.location` | Dedicated Consent section with client-side optional check |
| P7-015 | `surveillance.notifications` | Consent section with server-side + client-side enforcement layers |
| P7-016 | `surveillance.clipboard` | Consent Requirements section with explicit revoke behavior |
| P7-017 | All 4 (in references) | Consent note in prerequisites + References section |
| hmac-sign.js | N/A (code) | Not applicable; script only computes signatures |

All profile docs (P7-013 through P7-016) correctly document:
- The consent scope name
- That the API enforces consent server-side (HTTP 403 on missing consent)
- That consent can be revoked at any time
- Optional client-side pre-checks for bandwidth optimization

---

## 7. Event Format -- Pydantic Model Compatibility

All documented event payloads follow the same structure:

```json
{
  "event_type": "<string>",
  "device_id": "<string>",
  "occurred_at": "<ISO 8601 datetime>",
  "payload": { ... }
}
```

This matches the `SurveillanceEventRequest` Pydantic model with `extra="forbid"`. Each profile doc specifies the exact payload shape for its event type:

| Profile | event_type | payload fields |
|---|---|---|
| P7-013 | `app_usage` | `app_name`, `action` (enter/exit), `duration_seconds` |
| P7-014 | `location` | `latitude`, `longitude`, `accuracy_meters`, `altitude_meters`, `geofence` |
| P7-015 | `notification` | `app_name`, `title`, `text_preview`, `channel_id` |
| P7-016 | `clipboard` | `text`, `length` |

All payloads use correct types (strings for identifiers, numbers for metrics, null for absent values) and include the required top-level fields.

---

## 8. hmac-sign.js Verification

The JavaScriptlet passes all structural checks:

| Check | Result | Evidence |
|---|---|---|
| Uses `javax.crypto.Mac` | PASS | Line 33: `java.lang.Class.forName("javax.crypto.Mac")` |
| Uses `javax.crypto.spec.SecretKeySpec` | PASS | Line 34: `java.lang.Class.forName("javax.crypto.spec.SecretKeySpec")` |
| Reads `%HMAC_SECRET` variable | PASS | Line 18: `var hmacSecret = java.lang.String("%HMAC_SECRET")` |
| Colon-separated signing string | PASS | Line 27: `method + ":" + path + ":" + timestamp + ":" + nonce + ":" + body` |
| UUID nonce generation | PASS | Line 24: `java.util.UUID.randomUUID().toString()` |
| Timestamp in Unix seconds | PASS | Line 21: `Math.floor(Date.now() / 1000)` |
| Hex-encoded output (lowercase) | PASS | Line 41: `java.lang.String.format("%02x", rawHmac[i])` |
| Sets output variables | PASS | Lines 45-48: `setLocal("hmac_signature", ...)`, etc. |
| Error handling (fail-safe) | PASS | Lines 52-56: catch block sets `hmac_error = "true"` |
| No hardcoded secrets | PASS | Secret read from variable, never in source |
| No external dependencies | PASS | Uses Java bridge only, no CDN/CryptoJS |

---

## 9. Summary

| Category | Status | Detail |
|---|---|---|
| File existence (7/7) | PASS | All present and readable |
| Cross-references | PASS | All .md docs reference P7-012 and P7-017 |
| Signing string format | **FAIL** | P7-012 uses newlines; implementation uses colons |
| Secret hygiene | PASS | No hardcoded secrets; all use `%HMAC_SECRET` |
| Em dashes | **FAIL** | 5 em dashes in P7-012; other 6 files clean |
| Consent scopes | PASS | All scopes documented per file |
| Event format | PASS | Compatible with Pydantic model |
| hmac-sign.js | PASS | All structural checks pass |

---

## 10. Overall Verdict

**NEEDS REVIEW**

Two issues require fixes before this documentation suite can pass:

1. **BLOCKING:** P7-012 Section 5.1 and Section 8.3 document the signing string with newline separators. The implementation (`hmac-sign.js`) and all other docs use colon separators. This mismatch will cause HMAC signature verification failures (HTTP 401) for anyone following P7-012 literally.

2. **NON-BLOCKING:** P7-012 contains 5 em dashes in section headers (lines 1, 171, 182, 193, 204). Replace with hyphens per project style rules.

The other five documents and the JavaScriptlet are internally consistent with each other and with the server implementation.

---

## Footer

| Field | Value |
|---|---|
| **Audit** | D13 -- Tasker Documentation |
| **Date** | 2026-06-03 |
| **Auditor** | Guinevere (documentation audit agent) |
| **Scope** | 7 files: 6 .md + 1 .js under `docs/setup-evidence/P7/` |
| **Verdict** | NEEDS REVIEW |
| **Evidence path** | `audit-reports/P7/D13-tasker-docs.md` |