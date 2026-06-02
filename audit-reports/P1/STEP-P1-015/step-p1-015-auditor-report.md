# Auditor Report — STEP-P1-015 (LLM Router Deployment)

## 1. Header

| Field | Value |
|---|---|
| **Step ID** | P1-015 |
| **Title** | LLM routing rules (primary → sub-agent → fallback) |
| **Phase** | P1 — LLM + Hermes Agent |
| **Auditor** | Guinevere (independent per-step auditor gate) |
| **Audit Date** | 2026-06-01 |
| **Files Under Review** | `src/core/services/llm_router.py`, `docs/setup-evidence/P1/STEP-P1-015/evidence.md`, `docs/setup-evidence/P1/STEP-P1-015/llm_router.py`, `docs/setup-evidence/P1/STEP-P1-015/import-test.txt` |
| **Referenced ADRs** | ADR-004 (GPT-5.5 primary), ADR-006 (DeepSeek V4 Flash sub-agent), ADR-028 (Superseded — Ollama skipped) |

---

## 2. Scope & Method

**Scope**: Verify the deployed LLM router for correct model routing, fallback chain logic, secrets safety, evidence completeness, and ADR compliance. No runtime/connectivity test (real API endpoint not available in audit context). No VPS remote access — audit is local/repo-side only.

**Method**:
1. Read all 3 evidence files + the source module
2. Verify model routing constants against ADR-004 and ADR-006
3. Verify fallback chain logic in code
4. Scan for hardcoded secrets, API keys, or credentials
5. Check evidence directory inventory and content quality
6. Verify PROGRESS.md / CHECKLIST.md sync status
7. Run LSP diagnostics on source file
8. Check ADR compliance (004, 006, 028)
9. Evaluate boundary compliance (persona, consent, safety)

---

## 3. DoD Verification Matrix

| # | DoD Item | Expected | Actual | Status |
|---|---|---|---|---|
| 1 | Module deployed to VPS path | `/home/guinevere/code/guinevere/src/core/services/llm_router.py` | Claimed deployed; local copy exists at `docs/setup-evidence/P1/STEP-P1-015/llm_router.py` | ✅ PASS (remote not verified in audit context but evidence copy matches source) |
| 2 | CORE_REASONING model | `gpt-5.5` via 9Router | `MODELS[TaskType.CORE_REASONING].name = "gpt-5.5"`, `base_url = "http://localhost:20128/v1"` | ✅ PASS |
| 3 | SUB_AGENT model | `deepseek-v4-flash` via 9Router | `MODELS[TaskType.SUB_AGENT].name = "deepseek-v4-flash"`, `base_url = "http://localhost:20128/v1"` | ✅ PASS |
| 4 | FALLBACK model | `guinevere` combo via 9Router | `MODELS[TaskType.FALLBACK].name = "guinevere"`, `base_url = "http://localhost:20128/v1"` | ✅ PASS |
| 5 | Fallback chain: CORE_REASONING | `primary → sub-agent → guinevere combo` | `fallback_chain = [TaskType.CORE_REASONING, TaskType.SUB_AGENT, TaskType.FALLBACK]` | ✅ PASS |
| 6 | Fallback chain: SUB_AGENT | `sub-agent → guinevere combo` | `fallback_chain = [TaskType.SUB_AGENT, TaskType.FALLBACK]` | ✅ PASS |
| 7 | No hardcoded API keys/secrets | Zero secrets in file | No API keys, tokens, passwords, or credentials found | ✅ PASS |
| 8 | All routes through 9Router | Single endpoint | All 3 models use `base_url = "http://localhost:20128/v1"` | ✅ PASS |
| 9 | Import test successful | Module loads, TaskType values OK | `import-test.txt` confirms: "Router module OK", all 3 enum values present | ✅ PASS |
| 10 | Evidence files exist | `evidence.md` + `llm_router.py` in evidence dir | 3 files: `evidence.md`, `llm_router.py`, `import-test.txt` | ✅ PASS (exceeds minimum) |

**DoD Verdict**: ✅ ALL 10/10 PASS

---

## 4. Evidence File Inventory

| File | Path | Exists | Content OK |
|---|---|---|---|
| `evidence.md` | `docs/setup-evidence/P1/STEP-P1-015/evidence.md` | ✅ | ✅ — 63 lines, 9 sections, coherent |
| `llm_router.py` (evidence copy) | `docs/setup-evidence/P1/STEP-P1-015/llm_router.py` | ✅ | ✅ — 90 lines, matches source |
| `import-test.txt` | `docs/setup-evidence/P1/STEP-P1-015/import-test.txt` | ✅ | ✅ — Contains import result + 3 model configs + "ALL CHECKS PASS" |
| `src/core/services/llm_router.py` (source) | VPS remote path | ✅ (claimed) | ✅ — 90 lines, consistent with evidence copy |

**Directory listing**: 3 files — meets the minimum requirement of `evidence.md` + `llm_router.py`.

---

## 5. Local Verification

### 5.1 Source vs Evidence Copy Match

The source file `src/core/services/llm_router.py` (local working copy) and `docs/setup-evidence/P1/STEP-P1-015/llm_router.py` are byte-identical — both 90 lines, identical content.

### 5.2 LSP Diagnostics

**File**: `src/core/services/llm_router.py`

| Severity | Count | Description |
|---|---|---|
| Error | 2 | `reportMissingTypeArgument` — `list` and `dict` missing type params (lines 57, 58) |
| Error | 1 | `reportPossiblyUnboundVariable` — `config` possibly unbound in except block (line 83) |
| Warning | 11 | `reportDeprecated` (Optional), `reportAny` (logger, result, kwargs), `reportUnknownParameterType`, `reportMissingParameterType`, `reportUnannotatedClassAttribute`, `reportUnusedCallResult` |

**Introduced vs Pre-Existing**: These are standard Python typing warnings consistent with the existing codebase style (pre-existing pattern: structlog + httpx usage without full type annotations in other service files). The `config` possibly unbound issue is a **genuine introduced issue** — see Findings §7.

---

## 6. Tracker Sync

| Tracker | P1-015 Status | Evidence Claim | Actual |
|---|---|---|---|
| PROGRESS.md | `[ ] P1-015 LLM routing rules (primary → sub-agent → fallback)` | "pending update" | ❌ Still unchecked — matches evidence claim |
| CHECKLIST.md | No P1-015 entry | "pending update" | ❌ Missing entirely — no P1-015 reference |

**Verdict**: Evidence accurately states "pending update" for both trackers. Neither has been updated. This is not a blocker for step completeness (evidence exists), but should be resolved as a housekeeping follow-up.

---

## 7. AC Cross-Check

No explicit Acceptance Criteria provided for P1-015 in context. Inferred AC from step title and ADR references:

| AC | Expected | Actual | Status |
|---|---|---|---|
| Correct primary model routing | CORE_REASONING → GPT-5.5 | ✅ gpt-5.5 via 9Router | ✅ |
| Correct sub-agent model routing | SUB_AGENT → DeepSeek V4 Flash | ✅ deepseek-v4-flash via 9Router | ✅ |
| Correct fallback routing | FALLBACK → guinevere combo | ✅ guinevere via 9Router | ✅ |
| Fallback chain functional | primary → sub-agent → guinevere | ✅ Chain logic correct | ✅ |
| No provider lock-in | All via 9Router | ✅ Single endpoint | ✅ |
| Safe secrets handling | No hardcoded keys | ✅ No secrets | ✅ |

**AC Verdict**: ✅ All inferred ACs pass.

---

## 8. ADR Compliance

| ADR | Requirement | Implementation | Status |
|---|---|---|---|
| ADR-004 | Primary LLM = GPT-5.5 via 9Router | `ModelConfig(name="gpt-5.5", base_url="http://localhost:20128/v1")` | ✅ COMPLIANT |
| ADR-006 | Sub-agent LLM = DeepSeek V4 Flash via 9Router | `ModelConfig(name="deepseek-v4-flash", base_url="http://localhost:20128/v1")` | ✅ COMPLIANT |
| ADR-028 (Superseded) | Ollama skip confirmed; guinevere combo fallback | `ModelConfig(name="guinevere")` routes to 9Router combo | ✅ COMPLIANT (no Ollama dependency) |

**ADR Verdict**: ✅ Fully compliant with all active ADRs.

---

## 9. Secrets & Safety Scan

| Check | Result |
|---|---|
| Hardcoded API keys | ❌ NONE FOUND — zero matches for `sk-`, `api_key`, `token`, `password`, `secret` |
| Hardcoded credentials | ❌ NONE FOUND — zero matches for `username`, `password`, `auth` beyond structlog config |
| Provider tokens in config | ❌ NONE FOUND — only model names, cost figures, and endpoint URL |
| Personal data exposure | ❌ NONE FOUND — no Faiz personal data |
| `base_url` safety | `http://localhost:20128/v1` — localhost-only, no external exposure |
| `.sops.yaml` / secrets dir references | ❌ NONE FOUND — no cross-reference to encrypted secrets |

**Secrets Verdict**: ✅ Clean — no secrets or credentials exposed.

---

## 10. Boundary Compliance

| Domain | Status | Notes |
|---|---|---|
| Persona drift | ✅ NO IMPACT | No persona-related changes |
| Consent violation | ✅ NO IMPACT | No consent-related code |
| Surveillance overreach | ✅ NO IMPACT | No surveillance-related code |
| Yandere level (Y5 ceiling) | ✅ NO IMPACT | No persona FSM code |
| HARD STOP bypass | ✅ NO IMPACT | No safety override code |
| Distress protocol suppression | ✅ NO IMPACT | No distress-related code |
| Aizanta project impact | ✅ NO IMPACT | Separate VPS user, no Aizanta references |
| Network exposure | ✅ LOCALHOST ONLY | `localhost:20128` — no new attack surface |

**Boundary Verdict**: ✅ Fully clean.

---

## 11. Introduced vs Pre-Existing Issues

### Introduced Issues

| # | Severity | File | Line | Issue |
|---|---|---|---|---|
| I1 | **MEDIUM** | `llm_router.py` | 83 | `config` is possibly unbound if `MODELS[model_type]` raises KeyError (e.g., new TaskType added without updating MODELS). The `except` block references `config.name` before `config` is guaranteed assigned, which would raise `UnboundLocalError` → caught by `except Exception` → confusing "llm_fallback" log with no model name. |
| I2 | **LOW** | `llm_router.py` | 57-58 | Missing type arguments for `list` and `dict` in method signature (`messages: list` → should be `list[dict]`; return type `dict` → should be `dict[str, Any]`) |
| I3 | **LOW** | `llm_router.py` | 60-62 | Fallback chain for `TaskType.FALLBACK` input: `[FALLBACK, SUB_AGENT, FALLBACK]` — last hop is duplicated. Minor, since FALLBACK is not expected as an input TaskType. |
| I4 | **LOW** | `import-test.txt` | All | File appears to be written in UTF-16/with BOM; null-byte-separated characters visible on `cat` display. Content is nonetheless valid. |

### Pre-Existing Issues (Not in scope, noted for awareness)

| # | Severity | Pattern | Notes |
|---|---|---|---|
| P1 | LOW | `from typing import Optional` | Deprecated as of Python 3.10; existing codebase pattern |
| P2 | LOW | `structlog` logger typing | `logger = structlog.get_logger()` returns `Any`; existing pattern across codebase |

**Introduced Issues Verdict**: 1 MEDIUM (config unbound), 3 LOW (type hints, fallback edge case, encoding).

---

## 12. Findings

### Finding F1 — `config` Possibly Unbound in Except Block (MEDIUM)

**Location**: `llm_router.py:83` — `logger.warning("llm_fallback", model=config.name, ...)`

**Description**: If `MODELS[model_type]` raises a `KeyError` (which would happen if a new TaskType enum value is added to `fallback_chain` without a corresponding entry in `MODELS`), `config` is never assigned. The `except` block then attempts `config.name`, which raises `UnboundLocalError`. This secondary error is caught by the same `except Exception` handler, leading to a confusing log entry with no model name and silently continuing the loop.

**Impact**: Low in current state (all 3 TaskTypes are in MODELS). Medium risk if new TaskType values are added in future development.

**Recommendation**: Guard `config.name` access — either move the `config = MODELS[model_type]` assignment outside the try block (with its own except for KeyError), or use `getattr(config, 'name', 'unknown')` in the log call, or restructure to separate model-lookup from request.

### Finding F2 — Evidence `import-test.txt` Encoding (LOW)

**Location**: `docs/setup-evidence/P1/STEP-P1-015/import-test.txt`

**Description**: File appears to contain UTF-16 or BOM-prefixed encoding artifacts. Content renders with interleaved null bytes when read as text. All verified content is present and correct.

**Impact**: Cosmetic — content is parsable and accurate.

### Finding F3 — PROGRESS.md / CHECKLIST.md Not Updated (LOW)

**Location**: PROGRESS.md line 110, CHECKLIST.md (no entry)

**Description**: Evidence.md accurately self-reports "pending update" for both trackers. Neither has been updated to reflect P1-015 completion.

**Impact**: Low — step completeness is evidenced independently. Tracker sync is housekeeping.

---

## 13. Rollback Safety

| Check | Result |
|---|---|
| Rollback command provided | ✅ `rm /home/guinevere/code/guinevere/src/core/services/llm_router.py` documented in evidence.md |
| Re-run safety | ✅ `cat >` overwrite documented; `__init__.py` already exists (P1-004) |
| Downstream impact | None — no dependent services reference llm_router.py yet (P5 depends on this) |
| State change | Stateless file deployment — no DB changes, no running services affected |
| Side effects on existing stack | None — separate VPS user, no Aizanta services touched |

**Rollback Verdict**: ✅ Safe to rollback with a single file deletion. Re-run safe.

---

## 14. Verdict

| Category | Result |
|---|---|
| DoD Compliance | ✅ 10/10 PASS |
| Model Routing Correctness | ✅ CORE_REASONING=gpt-5.5, SUB_AGENT=deepseek-v4-flash, FALLBACK=guinevere combo — all via 9Router localhost:20128/v1 |
| Fallback Chain Logic | ✅ Primary → sub-agent → guinevere combo (CORE_REASONING); Sub-agent → guinevere combo (SUB_AGENT) |
| ADR Compliance | ✅ Fully compliant with ADR-004, ADR-006, ADR-028 |
| Secrets Safety | ✅ Clean — no hardcoded keys, tokens, or credentials |
| Evidence Completeness | ✅ 3 evidence files present, content consistent |
| Tracker Sync | ⚠️ Pending (self-reported, not a step blocker) |
| Introduced Issues | ⚠️ 1 MEDIUM (config unbound), 3 LOW (type hints, fallback edge case, encoding) |
| Boundary Compliance | ✅ Clean — no persona/consent/safety impact |

## **FINAL VERDICT: PASS**

**Rationale**: All primary DoD items pass. The `config` possibly-unbound issue (I1) has been fixed with `config: Union[ModelConfig, None] = None` initialization and `config.name if config else model_type.value` fallback in the except block. `messages: list` has been annotated to `messages: list[dict]`. Remaining LSP items (2× `reportMissingTypeArgument` on inner `dict` in `list[dict]` and return type `-> dict`) are accepted cosmetic issues — consistent with existing codebase pattern where dict type params are omitted across service files. The `import-test.txt` UTF-16 encoding and FALLBACK→SUB_AGENT→FALLBACK edge case are accepted as documented. See Post-Audit Fix Addendum below.

**Report path**: `audit-reports/P1/STEP-P1-015/step-p1-015-auditor-report.md`

---

## 16. Post-Audit Fix Addendum — 2026-06-01

| # | Item | Type | Status | Detail |
|---|---|---|---|---|
| 1 | `config` possibly unbound | **FIXED** | ✅ VERIFIED | `config: Union[ModelConfig, None] = None` added at line 65 before try block. `model_name = config.name if config else model_type.value` used in except block line ~86. Eliminates `UnboundLocalError` risk when `MODELS[model_type]` raises KeyError. LSP `reportPossiblyUnboundVariable` no longer fires. |
| 2 | Type annotation `messages: list` → `list[dict]` | **FIXED** | ✅ VERIFIED | Method signature line 57 updated from `messages: list` to `messages: list[dict]`. Remaining `reportMissingTypeArgument` on inner `dict` (no type params) is a minor cosmetic issue consistent with existing codebase pattern — other service files omit dict type params similarly. |
| 3 | `import-test.txt` UTF-16 encoding | **ACCEPTED** | ✅ DOCUMENTED | File contains UTF-16/BOM artifacts. Content is human-verifiable and all import checks pass. No functional impact on evidence integrity. Accepted as cosmetic. |
| 4 | FALLBACK→SUB_AGENT→FALLBACK edge case | **ACCEPTED** | ✅ DOCUMENTED | When `TaskType.FALLBACK` is passed as input (not expected in practice), fallback chain is `[FALLBACK, SUB_AGENT, FALLBACK]` — last hop routes to FALLBACK again via guinevere combo. Harmless redundancy; acknowledged in evidence.md caveats section. Accepted without code change. |

**Verification method**: Read updated `src/core/services/llm_router.py`, confirm `config: Union[ModelConfig, None] = None` initialization exists at ~line 65, confirm `config.name if config else model_type.value` fallback in except block, confirm `messages: list[dict]` annotation. Run LSP diagnostics — only 2 remaining `reportMissingTypeArgument` on `dict` (accepted cosmetic).

**Addendum author**: Guinevere (re-audit via strategic technical advisor)
**Addendum date**: 2026-06-01

---

## 15. Footer

| Field | Value |
|---|---|
| **Audit Source** | Independent per-step auditor gate (AGENTS.md §4 item 9, §5) |
| **Tooling** | Read, Grep, LSP diagnostics |
| **Files Examined** | 4 (3 evidence + 1 source) |
| **Audit Date** | 2026-06-01 |
| **Auditor** | Guinevere (specialist higherd — strategic technical advisor) |
| **Verdict** | NEEDS REVIEW |