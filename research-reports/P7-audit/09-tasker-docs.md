# P7 Tasker Documentation Audit — 2026-06-03

**Audit scope**: 6 Tasker documentation files + `hmac-sign.js` for P7 Surveillance phase  
**Auditor**: Guinevere (parent verification)  
**Output path**: `research-reports/P7-audit/09-tasker-docs.md`

---

## 1. File Existence — ALL FOUND

| # | File | Size | Exists |
|---|---|---|---|
| 1 | `docs/setup-evidence/P7/STEP-P7-012/tasker-setup-guide.md` | 486 lines | ✅ |
| 2 | `docs/setup-evidence/P7/STEP-P7-013/tasker-app-usage.md` | 395 lines | ✅ |
| 3 | `docs/setup-evidence/P7/STEP-P7-014/tasker-location.md` | 386 lines | ✅ |
| 4 | `docs/setup-evidence/P7/STEP-P7-015/tasker-notifications.md` | 448 lines | ✅ |
| 5 | `docs/setup-evidence/P7/STEP-P7-016/tasker-clipboard.md` | 215 lines | ✅ |
| 6 | `docs/setup-evidence/P7/STEP-P7-017/tasker-hmac-jslet.md` | 144 lines | ✅ |
| 7 | `docs/setup-evidence/P7/STEP-P7-017/hmac-sign.js` | 69 lines | ✅ |

---

## 2. Cross-Reference Matrix — ALL PASS

### 2.1 P7-012 Setup Guide References

| Doc | References P7-012? | Evidence |
|---|---|---|
| P7-013 tasker-app-usage.md | ✅ YES | Prerequisites table (line 25), Battery Optimization (line 322), References table (line 377), Footer dependencies (line 394) |
| P7-014 tasker-location.md | ✅ YES | Prerequisites section (line 16), Prerequisites table (line 25), References table (line 367), Footer (line 385) |
| P7-015 tasker-notifications.md | ✅ YES | Prerequisites (line 17), table items (lines 24, 26), Battery (line 344), References (line 427), Footer (line 447) |
| P7-016 tasker-clipboard.md | ✅ YES | Prerequisites (line 15), event format (line 76), Consent (line 130), References (line 214) |
| P7-017 tasker-hmac-jslet.md | ✅ YES | Prerequisites (line 14), Variable Setup table (line 20), References (line 142) |

### 2.2 P7-017 HMAC Signing References

| Doc | References P7-017? | Evidence |
|---|---|---|
| P7-012 tasker-setup-guide.md | ✅ YES | Section 5.1 (line 219), Section 5.4 (lines 265-273), Testing (line 419), References (line 469), Footer (line 485) |
| P7-013 tasker-app-usage.md | ✅ YES | Prerequisites (line 28), Action 4 (line 100), Exit Action 3 (line 175), HMAC Signing section (lines 241-262), References (line 378), Footer (line 394) |
| P7-014 tasker-location.md | ✅ YES | Overview (line 12), GPS/Actions (line 49), Geofence entries (lines 103, 115), HMAC section (lines 206-214), Troubleshooting (line 358), References (line 368), Footer (line 385) |
| P7-015 tasker-notifications.md | ✅ YES | Action 4 (line 108), HMAC Signing section (lines 254-266), References (line 428), Footer (line 447) |
| P7-016 tasker-clipboard.md | ✅ YES | Prerequisites (line 16), Action 4 (line 50), HMAC Signing section (lines 116-124), References (line 215) |

### 2.3 P7-009 Secret Scanner Reference (P7-016 only)

| Doc | References P7-009? | Evidence |
|---|---|---|
| P7-016 tasker-clipboard.md | ✅ YES | Overview (line 5), Secret Scanning Integration (lines 81-113), References (line 213) |

---

## 3. Consent Scope Coverage — ALL PASS

| Doc | Consent Scope | Mentioned? | Section |
|---|---|---|---|
| P7-012 tasker-setup-guide.md | All 4 scopes table | ✅ YES | Section 6.1 Consent Scopes (lines 282-290), Section 6 (lines 277-317) |
| P7-013 tasker-app-usage.md | `surveillance.app_usage` | ✅ YES | Prerequisites (line 29), Consent section (lines 266-290) |
| P7-014 tasker-location.md | `surveillance.location` | ✅ YES | Consent section (lines 216-244) |
| P7-015 tasker-notifications.md | `surveillance.notifications` | ✅ YES | Consent section (lines 268-287) |
| P7-016 tasker-clipboard.md | `surveillance.clipboard` | ✅ YES | Consent Requirements (lines 126-133) |
| P7-017 tasker-hmac-jslet.md | All 4 scopes | ✅ YES | Prerequisites (line 28), Security Notes (line 138) |

---

## 4. Secret & Data Hygiene — PASS (1 em dashes issue)

### 4.1 Hardcoded Secrets

| Check | Result |
|---|---|
| HMAC secret in code/docs | **PASS** — All use `%HMAC_SECRET` Tasker variable, never plaintext |
| hmac-sign.js line 22 | **PASS** — `java.lang.String("%HMAC_SECRET")` reads from Tasker variable |
| API keys, tokens, passwords | **PASS** — None found in any doc |
| SOPS decryption command in P7-012 | **PASS** — Uses placeholder path `secrets/surveillance/tasker-hmac.enc.yaml` |
| No `BEGIN PRIVATE KEY` | **PASS** — None in any file |

### 4.2 Real Data

| Check | Result |
|---|---|
| GPS coordinates in P7-014 | **PASS** — All use `0.0` placeholder values (lines 133-134, 149-150) |
| Device ID examples | **PASS** — Use synthetic UUIDs and placeholder names like `pixel-7-faiz-001` |
| App package names | **PASS** — All use `com.example.*` synthetic namespace |
| Zone names | **PASS** — Use generic labels like `"office"`, `"home"`, `"gym"` |
| Notification text | **PASS** — Synthetic examples only (e.g., "Hey, are you free for lunch today?") |
| Clipboard content | **PASS** — Uses `"example clipboard content"` |

### 4.3 Em Dashes

| Doc | Em dashes found | Status |
|---|---|---|
| P7-012 tasker-setup-guide.md | **6 found** (lines 1, 171, 182, 193, 204) | ❌ NEEDS FIX |
| P7-013 tasker-app-usage.md | 0 | ✅ PASS |
| P7-014 tasker-location.md | 0 | ✅ PASS |
| P7-015 tasker-notifications.md | 0 | ✅ PASS |
| P7-016 tasker-clipboard.md | 0 | ✅ PASS |
| P7-017 tasker-hmac-jslet.md | 0 | ✅ PASS |
| hmac-sign.js | 0 | ✅ PASS |

**Details for P7-012 em dashes:**
- Line 1: `# STEP-P7-012 *** Android Tasker Setup Guide for Guinevere Surveillance`
- Line 171: `### 4.1 P7-013 *** App Usage Profile`
- Line 182: `### 4.2 P7-014 *** Location Profile`
- Line 193: `### 4.3 P7-015 *** Notification Profile`
- Line 204: `### 4.4 P7-016 *** Clipboard Profile`

---

## 5. hmac-sign.js Verification — ALL PASS

| Criterion | Status | Evidence |
|---|---|---|
| Uses `javax.crypto.Mac` | ✅ PASS | Line 37: `java.lang.Class.forName("javax.crypto.Mac")` |
| Signing string format | ✅ PASS | Line 34: `method + ":" + path + ":" + timestamp + ":" + nonce + ":" + body` |
| Uses `%HMAC_SECRET` variable | ✅ PASS | Line 22: `java.lang.String("%HMAC_SECRET")` |
| UUID nonce generation | ✅ PASS | Line 29: `java.util.UUID.randomUUID().toString()` |
| No CryptoJS / external library | ✅ PASS | Pure Java bridge — no CDN imports, no crypto-js |
| Hex-encoded output | ✅ PASS | Line 54: `java.lang.String.format("%02x", rawHmac[i])` |
| Error handling | ✅ PASS | Try/catch with `hmac_error` flag (lines 63-68) |
| Build helper function | ✅ PASS | `buildEventPayload()` at lines 8-17 |
| No hardcoded secrets | ✅ PASS | Only `%HMAC_SECRET` variable reference |

---

## 6. Event Format vs Pydantic Model — PASS

The Pydantic `SurveillanceEventRequest` model (`src/surveillance/models.py`) requires:

```python
device_id: str (min_length=1, max_length=128)
event_type: Literal["app_usage", "screen_state", "notification", "location", "clipboard", ...]
occurred_at: datetime (ISO 8601, timezone-aware)
payload: dict[str, Any]
metadata: dict[str, Any] | None = None  # optional
```

| Doc | Matches model? | Notes |
|---|---|---|
| P7-012 | ✅ YES | Section 5.3 body structure includes all fields, `metadata` absent (correct — optional) |
| P7-013 | ✅ YES | Entry/exit event examples include `event_type`, `device_id`, `occurred_at`, `payload`, no `metadata` |
| P7-014 | ✅ YES | GPS and geofence examples include all required fields, `metadata` absent |
| P7-015 | ✅ YES | Notification event examples match schema exactly |
| P7-016 | ✅ YES | Clipboard event has `event_type`, `device_id`, `occurred_at`, `payload` (with `text`, `length`) |

All docs produce JSON bodies that will pass `SurveillanceEventRequest(**body)` validation. The `metadata` field is correctly treated as optional.

---

## 7. Header Verification — PASS (with BUG below)

Server expects (from `src/surveillance/auth.py`, lines 38-40):

| Header | Server alias | Expected Value |
|---|---|---|
| `X-Signature` | `Header(..., alias="X-Signature")` | Hex-encoded HMAC-SHA256 |
| `X-Timestamp` | `Header(..., alias="X-Timestamp")` | Unix epoch seconds |
| `X-Nonce` | `Header(..., alias="X-Nonce")` | UUID v4 |
| `Content-Type` | (FastAPI default) | `application/json` |

### Docs Coverage:

| Doc | Content-Type | X-Signature | X-Timestamp | X-Nonce |
|---|---|---|---|---|
| P7-012 | ✅ (line 244) | ✅ (line 245) | ✅ (line 246) | ✅ (line 247) |
| P7-013 | ✅ (line 112) | ✅ (line 113) | ✅ (line 114) | ✅ (line 115) |
| P7-014 | ✅ (line 61) | ✅ (line 61) | ✅ (line 61) | ✅ (line 61) |
| P7-015 | ✅ (line 137) | ✅ (line 138) | ✅ (line 139) | ✅ (line 140) |
| P7-016 | ✅ (implied via P7-017 ref) | ✅ | ✅ | ✅ |
| P7-017 | ✅ (line 86) | ✅ (line 87) | ✅ (line 88) | ✅ (line 89) |

All headers match the server-expected names. 

---

## 8. CRITICAL BUG: P7-012 Signing String Format Mismatch

### The Bug

**P7-012** (`tasker-setup-guide.md`) documents the signing string as **newline-separated**:

```
Line 224-231:
POST
/surveillance/events
{timestamp}
{nonce}
{request_body}

Line 389 (troubleshooting):
POST\n/surveillance/events\n{timestamp}\n{nonce}\n{body}
```

**However**, the actual signing string uses **colon separators**, confirmed by both:
- **Server** (`src/surveillance/auth.py`, line 70-73):
  ```python
  f"{request.method}:{request.url.path}:{x_timestamp}:{x_nonce}:{body_str}"
  ```
- **JavaScriptlet** (`hmac-sign.js`, line 34):
  ```javascript
  method + ":" + path + ":" + timestamp + ":" + nonce + ":" + body.toString()
  ```

**All other docs correctly document colon format:**
- P7-013 line 248: `POST:/surveillance/events:{timestamp}:{nonce}:{body}` ✅
- P7-014 line 209: `POST:/surveillance/events:{timestamp}:{nonce}:{body}` ✅
- P7-015 line 260: `POST:/surveillance/events:{timestamp}:{nonce}:{body}` ✅
- P7-017 lines 47-51: `method:path:timestamp:nonce:body` ✅

### Impact

If an operator configures Tasker using P7-012 Section 5.1 as the canonical signing string reference, the HMAC signatures will never match, and **all events will be rejected with HTTP 401**.

### Fix Required

In `docs/setup-evidence/P7/STEP-P7-012/tasker-setup-guide.md`:

1. **Section 5.1** (lines 224-237): Replace newline-separated diagram with colon-separated format:
   ```
   Instead of:
   POST
   /surveillance/events
   {timestamp}
   {nonce}
   {request_body}
   
   Should be:
   POST:/surveillance/events:{timestamp}:{nonce}:{request_body}
   ```

2. **Troubleshooting line 389**: Replace:
   `POST\n/surveillance/events\n{timestamp}\n{nonce}\n{body}`
   with:
   `POST:/surveillance/events:{timestamp}:{nonce}:{body}`

---

## 9. Summary — VERDICT

| Criterion | Result |
|---|---|
| All 7 files exist | ✅ PASS |
| P7-012 cross-references | ✅ PASS (all 5 docs reference it) |
| P7-017 cross-references | ✅ PASS (all 5 docs reference it) |
| P7-009 reference (P7-016) | ✅ PASS |
| Consent scopes mentioned | ✅ PASS (all 6 docs) |
| No hardcoded secrets | ✅ PASS |
| No real data | ✅ PASS |
| hmac-sign.js correctness | ✅ PASS |
| Event format vs Pydantic model | ✅ PASS |
| Headers vs server expectations | ✅ PASS |
| **Em dashes in P7-012** | ❌ **NEEDS FIX** (6 occurrences) |
| **Signing string format in P7-012** | ❌ **CRITICAL BUG** (newlines instead of colons) |

### Overall Verdict: NEEDS REVIEW

**PASS items**: 10 of 12 criteria pass.

**BLOCKING items**: 2 findings require remediation:
1. **CRITICAL**: P7-012 signing string format uses newlines but server/JS use colons — will cause 100% HMAC signature rejection if followed literally
2. **Minor**: 6 em dashes in P7-012 title and subsection headers — replace with standard hyphens

**P7-016 completeness note**: At 215 lines (vs 386-486 for other profiles), the clipboard doc is shorter. Cross-references and event format are present, but the HMAC header table is inferred via P7-017 reference rather than explicit. Acceptable but could be strengthened with a brief header table like P7-013/P7-015 use.

---

## 10. Remediation Actions

### REQUIRED (blocks PASS verdict):
1. **Fix P7-012 Section 5.1** — Change signing string diagram from newline-separated to colon-separated to match `hmac-sign.js` and `auth.py`
2. **Fix P7-012 line 389** — Change troubleshooting canonical string from `POST\n/surveillance/events\n...` to `POST:/surveillance/events:...`

### RECOMMENDED (cosmetic):
3. **Replace 6 em dashes in P7-012** — Change `—` to `-` in title (line 1) and subsection headers (lines 171, 182, 193, 204)

---

*Audit completed 2026-06-03. Guinevere (parent verification).*
