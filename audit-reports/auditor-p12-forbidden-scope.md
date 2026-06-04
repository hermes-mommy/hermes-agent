# Auditor Report: P12 Forbidden Patterns & Scope Violations

| Field | Value |
|---|---|
| **Auditor** | Guinevere (automated forbidden-pattern + scope audit) |
| **Date** | 2026-06-03 |
| **Scope** | P12-001.md through P12-029.md (29 files) |
| **Location** | `research-reports/p12-expansion/` |
| **Verdict** | **FAIL** — 3 forbidden pattern violations, 1 terminology violation |

---

## §1 File Inventory

| Check | Result |
|---|---|
| Files present | 29/29 |
| Expected range | P12-001.md — P12-029.md |
| Missing files | None |

All 29 step files exist and are non-empty.

---

## §2 Forbidden Pattern Scan

### 2.1 Type Safety Bypass: `as any` / `@ts-ignore` / `@ts-expect-error`

| Metric | Value |
|---|---|
| Raw regex matches | 12 across 12 files |
| Actual violations (in code) | **0** |
| Meta-references (checklists/rules) | 12 |
| **Verdict** | **PASS** |

**Analysis:** All 12 matches are checklist items of the form `"No as any, @ts-ignore, or type suppression patterns in any new file"`. These are meta-references prescribing what implementers must NOT do — not actual usage of the forbidden patterns.

**Files with meta-references:** P12-006, P12-007, P12-016, P12-020, P12-021, P12-022, P12-023, P12-024, P12-025, P12-027, P12-028, P12-029.

---

### 2.2 Python Type Safety Bypass: `# type: ignore`

| Metric | Value |
|---|---|
| Raw regex matches | 9 across 8 files |
| Actual violations (in code) | **2** |
| Meta-references (checklists/justifications) | 7 |
| **Verdict** | **FAIL** |

**Actual violations:**

| File | Line | Code | Severity |
|---|---|---|---|
| P12-002.md | 221 | `return self._creds  # type: ignore[return-value]` | HIGH |
| P12-004.md | 94 | `return self._svc  # type: ignore[return-value]` | HIGH |

**Context for P12-002 line 221:** `TokenManager.get_credentials()` method. `_creds` is typed `Credentials | None`. The `# type: ignore[return-value]` suppresses mypy's narrowing complaint after the `if self._creds is None: self._load()` guard. **Fix:** Add explicit `assert self._creds is not None` before the return, or restructure to `return cast(Credentials, self._creds)` after the guard.

**Context for P12-004 line 94:** `GmailClient.service` property. `_svc` is typed `Resource | None`. Same pattern — lazy init followed by return with `# type: ignore[return-value]`. P12-004 line 321 contains a justification paragraph for this suppression, but justification does not exempt it from the BLOCKING rule. **Fix:** Same pattern — add `assert self._svc is not None` or use `cast()`.

**Meta-references (not violations):**

| File | Line | Type |
|---|---|---|
| P12-004.md | 321 | Justification paragraph explaining the suppression |
| P12-007.md | 190 | Checklist item |
| P12-016.md | 113 | Checklist item |
| P12-025.md | 330 | Checklist item |
| P12-027.md | 273 | Checklist item |
| P12-028.md | 294 | Checklist item |
| P12-029.md | 334 | Checklist item |

---

### 2.3 Error Swallowing: `except:` / `except Exception:` with empty body

| Metric | Value |
|---|---|
| Raw regex matches | 2 in 1 file (P12-011.md) |
| Actual violations (empty body) | **1** |
| Legitimate fallbacks | 1 |
| **Verdict** | **FAIL** |

**Violation:**

| File | Lines | Code | Severity |
|---|---|---|---|
| P12-011.md | 229-230 | `except Exception:` → `pass` | HIGH |

**Context:** Inside `_scan_injection()` method, base64 decode attempt:
```python
try:
    decoded = base64.b64decode(b64).decode("utf-8", errors="ignore")
    if any(kw in decoded.lower() for kw in [...]):
        result.base64_segments_found += 1
        result.injection_patterns_matched.append("base64_decoded_instruction")
except Exception:
    pass  # ← VIOLATION: silent failure
```
**Fix:** Replace `pass` with `logger.debug("base64_decode_failed", segment_length=len(b64))` to at least log the failure, or narrow the exception to `except (ValueError, UnicodeDecodeError):` with a debug log.

**Legitimate (not a violation):**

| File | Lines | Code | Status |
|---|---|---|---|
| P12-011.md | 240-241 | `except Exception:` → `return BeautifulSoup(content, ...).get_text(...)` | OK — proper fallback to HTML-to-text conversion |

---

### 2.4 Dangerous Commands: `rm -rf /`

| Metric | Value |
|---|---|
| Matches | 0 |
| **Verdict** | **PASS** |

---

### 2.5 Secret Exposure: API keys / tokens / passwords

| Metric | Value |
|---|---|
| Raw regex matches | 1 in 1 file |
| Actual secret exposure | **0** |
| **Verdict** | **PASS** |

**Match analysis:**

| File | Line | Content | Assessment |
|---|---|---|---|
| P12-002.md | 201 | `encrypted_token="secrets/gmail-oauth-token.enc"` | File path parameter default pointing to a SOPS-encrypted file. NOT an actual secret value. |

The code references encrypted file paths (`secrets/gmail-oauth-token.enc`, `secrets/gmail-oauth-client.enc`) and uses `sops -d` for decryption at runtime. No plaintext secrets, API keys, tokens, or passwords are hardcoded.

---

### 2.6 Stale Terminology: `post-MVP`

| Metric | Value |
|---|---|
| Matches | 6 across 3 files |
| **Verdict** | **FAIL** |

**All occurrences:**

| File | Line | Context |
|---|---|---|
| P12-010.md | 8 | "fixed weights for MVP with **post-MVP** tunability via Discord" |
| P12-010.md | 48 | "Weights stored in Redis for runtime tuning (**post-MVP**)" |
| P12-010.md | 120 | `"""Runtime-tunable scoring weights (**post-MVP** via Discord).` |
| P12-010.md | 242 | "if Faiz requests it **post-MVP**" |
| P12-019.md | 201 | "If a weekly summary is desired **post-MVP**, it can be added..." |
| P12-028.md | 197 | "**post-MVP**. For MVP, these are hardcoded." |

**Required fix:** Replace all instances of `post-MVP` with the correct terminology: `Stabilization` (for near-term follow-up) or `Expansion` (for future phase features). Context-dependent:
- P12-010.md lines 8, 48, 120: Replace with "Stabilization" (tunable weights are near-term)
- P12-010.md line 242: Replace with "Expansion" (domain hierarchy matching is a future feature)
- P12-019.md line 201: Replace with "Expansion" (weekly summary is a future feature)
- P12-028.md line 197: Replace with "Stabilization" (hardcoded config is near-term)

---

## §3 Scope Checks

### 3.1 General Scope: All Steps Gmail/Email Related

| Metric | Value |
|---|---|
| Files checked | 29 |
| Files with Gmail/email references | 29 (769 total matches) |
| Out-of-scope files | 0 |
| **Verdict** | **PASS** |

**Step title verification (all 29):**

| Step | Title | Scope |
|---|---|---|
| P12-001 | GCP Project + API Enablement | Gmail API setup |
| P12-002 | OAuth2 Token Management + !email-reauth | Gmail auth |
| P12-003 | Resend Client Setup | Email sending |
| P12-004 | Gmail API Client Wrapper | Gmail API |
| P12-005 | Incremental Sync Engine | Gmail sync |
| P12-006 | Pub/Sub StreamingPull + Watch Renewal | Gmail push |
| P12-007 | GmailAdapter (ChannelAdapter) | Gmail channel |
| P12-008 | Channel Context Manager | Email context |
| P12-009 | Email Classifier (Cascade Pattern) | Email classification |
| P12-010 | Importance Scorer | Email scoring |
| P12-011 | Content Sanitizer + Injection Defense | Email security |
| P12-012 | Secret Scanner + PII Redactor | Email content |
| P12-013 | Memory Store Integration | Email memory |
| P12-014 | Financial Email → P9 Bridge | Email → finance |
| P12-015 | Draft Generator (LLM) | Email drafts |
| P12-016 | Discord Draft UX | Email draft UX |
| P12-017 | Gmail Draft Sync + Send | Gmail send |
| P12-018 | Real-Time Email Notifications | Email alerts |
| P12-019 | Morning Briefing + On-Demand Digest | Email briefing |
| P12-020 | !email-digest Command | Email digest |
| P12-021 | !email-consent + !email-reauth | Email commands |
| P12-022 | Cross-Channel HARD STOP | Email safety |
| P12-023 | Surveillance Classification | Email surveillance |
| P12-024 | Watch Renewal + Health Check | Gmail health |
| P12-025 | Grafana Dashboard + Metrics | Email metrics |
| P12-026 | Systemd Service + Runbook | Email ops |
| P12-027 | E2E Integration Test (P12 GATE) | Email testing |
| P12-028 | Agent Loop Trigger Detector | Email triggers |
| P12-029 | TaskContract Email Context | Email contracts |

---

### 3.2 Specific Scope Checks

| # | Check | File | Evidence | Verdict |
|---|---|---|---|---|
| 1 | P12-027 references P12 GATE with 10 scenarios | P12-027.md | 15 matches: "P12 GATE", "10 scenarios", "ALL 10 scenarios must PASS", explicit gate contract section | **PASS** |
| 2 | P12-022 references cross-channel shared Redis flag | P12-022.md | 13 matches: "cross-channel HARD STOP", "shared Redis flag", `guinevere:hard_stop`, JSON value structure | **PASS** |
| 3 | P12-028 references LoopManager from src/loops/ | P12-028.md | References `LoopManager`, `src.loops.manager`, import verification command | **PASS** |
| 4 | P12-029 references src/loops/contract.py build_contract() | P12-029.md | 19 matches: `src/loops/contract.py`, `build_contract()`, `TaskContract`, `contract_to_prompt()` | **PASS** |
| 5 | P12-007 references ChannelAdapter interface from P11-004 | P12-007.md | 19 matches: `ChannelAdapter` ABC, `P11-004`, `UnifiedMessage`, 5 abstract + 2 concrete methods | **PASS** |

---

## §4 Summary

### Forbidden Patterns

| # | Pattern | Match Count (Actual) | Verdict |
|---|---|---|---|
| 1 | `as any` / `@ts-ignore` / `@ts-expect-error` | 0 (12 meta-only) | PASS |
| 2 | `# type: ignore` | 2 (P12-002:221, P12-004:94) | **FAIL** |
| 3 | `except Exception:` with empty body | 1 (P12-011:229-230) | **FAIL** |
| 4 | `rm -rf /` | 0 | PASS |
| 5 | API keys / tokens / passwords | 0 (1 false positive — encrypted file path) | PASS |
| 6 | `post-MVP` (stale terminology) | 6 (P12-010: 4, P12-019: 1, P12-028: 1) | **FAIL** |

### Scope Checks

| # | Check | Verdict |
|---|---|---|
| 1 | All 29 steps Gmail/Email related | PASS |
| 2 | P12-027 → P12 GATE + 10 scenarios | PASS |
| 3 | P12-022 → cross-channel shared Redis flag | PASS |
| 4 | P12-028 → LoopManager from src/loops/ | PASS |
| 5 | P12-029 → src/loops/contract.py build_contract() | PASS |
| 6 | P12-007 → ChannelAdapter from P11-004 | PASS |

---

## §5 Final Verdict

| Category | Status |
|---|---|
| Forbidden Patterns | **FAIL** (3 violations) |
| Scope Checks | PASS (all 6 checks pass) |
| **Overall** | **FAIL** |

### Required Fixes (3 items)

| # | File | Issue | Fix |
|---|---|---|---|
| 1 | P12-002.md:221 | `# type: ignore[return-value]` in code | Replace with `assert self._creds is not None` before return |
| 2 | P12-004.md:94 | `# type: ignore[return-value]` in code | Replace with `assert self._svc is not None` before return |
| 3 | P12-011.md:229-230 | `except Exception: pass` (empty body) | Add `logger.debug()` or narrow to specific exception types |
| 4 | P12-010.md (4×), P12-019.md (1×), P12-028.md (1×) | `post-MVP` stale terminology | Replace with `Stabilization` or `Expansion` per context |

---

## §6 Footer

| Field | Value |
|---|---|
| Audit method | Automated regex scan + contextual verification |
| Tool | grep + manual context review |
| False positive handling | Meta-references (checklists, justifications) distinguished from actual code violations |
| Reproducible | Yes — all patterns and file paths are deterministic |
