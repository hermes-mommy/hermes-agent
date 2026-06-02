# StepPrompts.md — Full Audit Report

**Date:** 2026-05-31
**Auditor:** 5 parallel deep agents (D1+D8, D2+D5, D3+D4, D6+D7, D9-D12)
**File Audited:** `stepprompts/StepPrompts.md` (7360 lines, 256.9KB)
**Scope:** 12 dimensions across technical accuracy, ADR compliance, security, completeness, AC coverage, persona, memory, and more.

---

## Executive Summary

| Dimension | Status | Critical | High | Medium | Low |
|---|---|---|---|---|---|
| D1: Technical Accuracy | **FAIL** | 5 | 6 | 5 | 3 |
| D2: ADR Compliance | **FAIL** | 2 | 4 | 0 | 0 |
| D3: Security Compliance | **FAIL** | 4 | 9 | 16 | 9 |
| D4: Shared VPS Compliance | **FAIL** | 0 | 2 | 8 | 4 |
| D5: Dependency Correctness | **FAIL** | 0 | 2 | 0 | 0 |
| D6: Completeness | **FAIL** | 5 | 8 | 3 | 2 |
| D7: AC Coverage | **FAIL** | 10 | 4 | 5 | 2 |
| D8: Cost Accuracy | **FAIL** | 0 | 3 | 2 | 1 |
| D9: Evidence Requirements | **FAIL** | 1 | 2 | 3 | 5 |
| D10: Persona + Discord | **PARTIAL** | 0 | 4 | 3 | 8 |
| D11: Agent Loop Accuracy | **PARTIAL** | 0 | 2 | 2 | 4 |
| D12: Memory System | **PARTIAL** | 0 | 1 | 1 | 5 |
| **TOTAL** | | **27** | **47** | **48** | **43** |

**After deduplication: 19 unique CRITICAL, 38 unique HIGH**

**Overall Verdict: CONDITIONAL FAIL** — 19 blocking critical findings require fix before P0 execution.

---

## CRITICAL Findings (Blocking — Must Fix Before P0)

### 9Router Cluster (5 findings)

| ID | Step(s) | Issue | Reference |
|---|---|---|---|
| C-01 | P1-006 to P1-020 (24 locations) | 9Router port listed as `8080` throughout. Actual port is `20128`. | research-reports/2026-05-31-hermes-9router-tasker.md |
| C-02 | P1-006 | npm package `@9router/cli` is fabricated. Real package: `npm install -g 9router` | npmjs.com/package/9router |
| C-03 | P1-006 | 9Router configuration via `config.yaml` file is fabricated. 9Router is configured via web dashboard at `:20128/dashboard`. | github.com/decolua/9router |
| C-04 | P1-006, P1-008 | `https://api.9router.com/v1` used as provider base_url — fabricated. 9Router is self-hosted at `localhost:20128`. | research report |
| C-05 | P1-008, P1-010 | Provider `base_url` points to cloud API. 9Router IS the proxy — base_url should be `http://localhost:20128/v1` for ALL model routing. | ADR-005 |

### Secrets Cluster (4 findings)

| ID | Step(s) | Issue | Reference |
|---|---|---|---|
| C-06 | P1-007, P1-008 | Plaintext API key in `secrets/.env.9router` via `echo "..." > file`. Must use SOPS+age per ADR-015. | ADR-015 |
| C-07 | P2-017 | Plaintext Discord bot token in `secrets/.env.discord`. Must use SOPS+age. | ADR-015 |
| C-08 | P8-001 | Hardcoded `GF_SECURITY_ADMIN_PASSWORD=changeme` in docker-compose.yml. Must use env file + SOPS. | ADR-015, Security Policy |
| C-09 | P2-020 | Hardcoded `GOTIFY_DEFAULTUSER_PASS=changeme` in docker-compose.yml. Must use env file + SOPS. | ADR-015, Security Policy |

### ADR Compliance (2 findings)

| ID | Step(s) | Issue | Reference |
|---|---|---|---|
| C-10 | P0-020, P0-021 | Redis DB assignments wrong: DB1 labeled "pubsub" (should be LLM cache), DB4 labeled "config" (should be Pub/Sub). | ADR-030: DB0=task queue, DB1=LLM cache, DB2=surveillance, DB3=session, DB4=pub/sub, DB5=rate limit |
| C-11 | P1-014, P1-015 | LLM fallback chain omits OpenRouter as Tier 2. Only shows 9Router → Ollama. ADR-028 mandates: 9Router → OpenRouter → Ollama → Graceful Degradation. | ADR-028 v3.0 |

### Completeness (5 findings)

| ID | Step(s) | Issue | Reference |
|---|---|---|---|
| C-12 | P3-P11 (191 steps) | 191 of 252 steps (75.8%) lack individual step prompts — batched as ranges (e.g., P3-001 to P3-005). Only P0-P2 have detailed individual prompts. | Completeness check |
| C-13 | ALL steps | `Type` field (Infrastructure/Code/Config/Documentation) missing from ALL steps. | Mandatory fields |
| C-14 | ALL steps | `Status` field (Pending/In-Progress/Complete) missing from ALL steps. | Mandatory fields |
| C-15 | ALL steps | `Risk level` (CRITICAL/HIGH/MEDIUM/LOW) missing from ALL steps. | Mandatory fields |
| C-16 | ALL steps | `Git Commit` field missing from ALL steps. | Mandatory fields |

### AC Coverage (5 findings)

| ID | AC ID | Issue | Reference |
|---|---|---|---|
| C-17 | AC-SAFE-002 | Yandere cap Y5 enforcement not covered by any step. | AcceptanceCriteriaCatalog |
| C-18 | AC-SAFE-003 | Consent revocation flow not covered by any step. | AcceptanceCriteriaCatalog |
| C-19 | AC-SAFE-006 | Punishment overflow not overriding emergency response — not covered. | AcceptanceCriteriaCatalog |
| C-20 | AC-SAFE-008 | Distress D0-D4 escalation test not covered. | AcceptanceCriteriaCatalog |
| C-21 | AC-PHASE-006 | MVP go-live gate not covered. | AcceptanceCriteriaCatalog |

### Evidence + Other (2 findings)

| ID | Step(s) | Issue | Reference |
|---|---|---|---|
| C-22 | ALL steps | Evidence path convention uses `evidence/phase-N/step-NNN/` instead of expected `docs/setup-evidence/P{N}/STEP-P{N}-{XXX}/`. | CHECKLIST.md, PROGRESS.md |
| C-23 | P4 (HARD STOP test) | HARD STOP test placed in Phase 4. AcceptanceCriteriaCatalog requires it BEFORE Phase 2 completion. | AC-SAFE-001, AcceptanceCriteriaCatalog |

---

## HIGH Findings (Non-blocking — Fix During Implementation)

### Technical (6)

| ID | Step(s) | Issue |
|---|---|---|
| H-01 | P1-007 | Health endpoint `/health` wrong — 9Router uses `/api/health` |
| H-02 | P1-005 | `hermes-agent` pip package likely doesn't exist on PyPI |
| H-03 | P1-005 | Python 3.12 specified but Hermes Agent may require 3.11 |
| H-04 | P1-008 | GPT-5.5 cost $10/mo — FinOps v1.1 says $7-8/mo |
| H-05 | P1-010 | DeepSeek cost $3/mo — FinOps v1.1 says $1-2/mo |
| H-06 | P8-001 | Exa "$5/day cap" conflates daily burst with $3 monthly throttle trigger |

### ADR + Dependency (4)

| ID | Step(s) | Issue |
|---|---|---|
| H-07 | P5-004 to P5-010 | Range notation without individual step blocks |
| H-08 | P1-012 | Ollama cgroup 8GB doesn't enforce ADR-028's 4GB RAM cap |
| H-09 | P2-018 | Dependency wrong (lists P2-015, needs P2-017) |
| H-10 | P2-021 | Dependency wrong (lists P2-019, needs P2-020) |

### Security (9)

| ID | Step(s) | Issue |
|---|---|---|
| H-11 | P0-020, P0-021 | Redis `rename-command` for dangerous commands (FLUSHALL, CONFIG, DEBUG) missing |
| H-12 | P0-002 | SSH hardening incomplete — no root login disable, no password auth disable |
| H-13 | P7 | HMAC secret generation step missing for surveillance endpoints |
| H-14 | P8-013 | Sentry `send_default_pii=false` not explicitly set |
| H-15 | P0-004 | UFW reset may disrupt Aizanta on shared VPS |
| H-16 | P8-001 | Monitoring stack resource impact not assessed for Aizanta |
| H-17 | P1-P11 | 223 of 252 steps (88.5%) missing "Shared VPS Notes" section |
| H-18 | P0-021 | Redis maxmemory-policy not set (should be `allkeys-lru` for cache DBs) |
| H-19 | P2-017 | Discord bot token file permissions not verified (should be 600) |

### Completeness (8)

| ID | Issue |
|---|---|
| H-20 | `Executor` field (Guinevere/Samm/Both) missing from ALL steps |
| H-21 | `AC Reference` field incomplete — many steps have generic "AC-CORE-XXX" |
| H-22 | Phase 0 has no explicit "Shared VPS Discovery" step as STEP-P0-000 |
| H-23 | No MVP gate section between P10 and P11 |
| H-24 | P9-P11 phases exist but with grouped/summary format only |
| H-25 | 30 of 76 ACs (39%) have NO covering step |
| H-26 | 11 of 76 ACs (14%) have only partial coverage |
| H-27 | AC-SEC-005 through AC-SEC-008 coverage weak |

### Persona + Discord (4)

| ID | Issue |
|---|---|
| H-28 | Channel names don't match DiscordUXSpec exact names |
| H-29 | Slash command count discrepancy: 33 vs 34 |
| H-30 | "Watching Darling 👁️" presence string missing |
| H-31 | DND 00:00-07:00 WIB not referenced |

### Agent Loop + Memory (4)

| ID | Issue |
|---|---|
| H-32 | "Pasukan Mommy" sub-agent terminology not referenced |
| H-33 | Phase names abbreviated vs canonical 7-phase names |
| H-34 | Embedding model confusion: dead sentence-transformers vs text-embedding-3-small via 9Router |
| H-35 | No explicit step for pgvector HNSW index creation parameters (m=16, ef_construction=64) |

### Evidence (2)

| ID | Issue |
|---|---|
| H-36 | Screenshot requirements vague — "take screenshot" without specifying what to capture |
| H-37 | Performance baseline requirements missing from infrastructure steps |

---

## MEDIUM Findings Summary (48 total, non-blocking)

Top categories:
- 16 steps with missing/wrong Docker image version tags
- 8 systemd unit inconsistencies
- 8 file path naming inconsistencies
- 6 missing rollback verification steps
- 5 cost estimate discrepancies
- 5 documentation cross-reference issues

## LOW Findings Summary (43 total, non-blocking)

Top categories:
- 15 formatting/style inconsistencies
- 12 minor naming convention issues
- 8 missing optional documentation references
- 8 minor evidence path issues

---

## Dimension-by-Dimension Detail

### D1: Technical Accuracy — FAIL

**Root cause:** 9Router details were fabricated without consulting the actual project (github.com/decolua/9router). The research report had correct details but the generation agent didn't use them.

**Affected area:** All P1 steps (P1-006 through P1-020) — 24 locations reference wrong port, wrong package name, wrong config method, wrong API URL.

**Positive:** No Hetzner, Vultr, B2, or OpenRouter-as-fallback contamination found.

### D2: ADR Compliance — FAIL

**Positive:** No references to deprecated items (SQLite, OpenCode, guinevere_db, B2/Backblaze, Hermes 3 as primary, Claude). Topological ordering of 252 steps verified correct.

**Problem areas:** Redis DB assignments and fallback chain are the main ADR violations.

### D3: Security Compliance — FAIL

**Root cause:** Security steps use placeholder values (`changeme`, `PLACEHOLDER_KEY`) written as plaintext files instead of SOPS-encrypted secrets. This is a design-level issue — the steps should show the SOPS workflow, not plaintext echo commands.

### D4: Shared VPS Compliance — FAIL

**Root cause:** Only 29 of 252 steps (11.5%) have "Shared VPS Notes" sections. The generation agent treated this as optional rather than mandatory.

### D5: Dependency Correctness — PARTIAL

**Positive:** Topological ordering is valid for all 252 steps. No circular dependencies.

**Problem areas:** 2 incorrect dependency references (P2-018, P2-021).

### D6: Completeness — FAIL

**Key metrics:**
- 252 steps counted ✅
- 61 individual (24%) — P0-P2 only
- 191 grouped (76%) — P3-P11
- 4 mandatory fields missing from ALL steps (Type, Status, Risk, Git Commit)

**Note:** The grouped format for P3-P11 was an intentional design decision per the synthesis report — detailed for near-term phases, summary for distant ones. However, the 4 missing mandatory fields are genuine gaps.

### D7: AC Coverage — FAIL

**Key metrics:**
- 76 ACs in catalog
- 35 covered (46%)
- 11 partial (14%)
- 30 uncovered (40%)

**Uncovered critical ACs:** AC-SAFE-002/003/006/008, AC-PHASE-006

### D8: Cost Accuracy — PARTIAL

**Positive:** No Hetzner/Vultr/B2 contamination. VPS cost correctly $0 (shared existing).

**Problem areas:** GPT-5.5 and DeepSeek cost estimates slightly off vs FinOps v1.1. Exa throttle trigger not mentioned.

### D9: Evidence Requirements — PARTIAL

**Positive:** All steps have evidence sections.

**Problem areas:** Path convention wrong, screenshot requirements vague.

### D10: Persona + Discord — PARTIAL

**Confirmed correct:** Server name "Guinevere's Domain", 4 categories with correct emojis, embed colors, startup message, HARD STOP phrase, Y1 baseline, L6 deferred.

**Problem areas:** Channel names, slash command count, presence string, DND hours.

### D11: Agent Loop — PARTIAL

**Confirmed correct:** 7 phases (not 8), Loop Guardian, Todo Enforcer, hash-anchored edits, file-based output, parent verification.

**Problem areas:** "Pasukan Mommy" terminology, phase name abbreviations.

### D12: Memory System — PARTIAL

**Confirmed correct:** HNSW indexes, do-not-recall, safe-mode gate, confidence 80%, consolidation job, PostgreSQL primary, Redis cache.

**Problem areas:** Embedding model confusion, HNSW parameter step missing.

---

## Audit Artifacts

| File | Size | Content |
|---|---|---|
| `audit-reports/stepprompts-audit/D1-D8-technical-cost.md` | 23KB | Technical + Cost findings |
| `audit-reports/stepprompts-audit/D2-D5-adr-dependency.md` | ~20KB | ADR + Dependency findings |
| `audit-reports/stepprompts-audit/D3-D4-security-sharedvps.md` | ~25KB | Security + Shared VPS findings |
| `audit-reports/stepprompts-audit/D6-D7-completeness-acceptance.md` | 28KB | Completeness + AC Coverage |
| `audit-reports/stepprompts-audit/D9-D10-D11-D12-evidence-persona-loop-memory.md` | 31KB | Evidence + Persona + AgentLoop + Memory |
| `audit-reports/2026-05-31-stepprompts-full-audit.md` | This file | Consolidated summary |
| `fixes/2026-05-31-stepprompts-fixes.md` | Companion file | Exact edits needed |

---

## Verdict

**CONDITIONAL FAIL** — 19 blocking critical findings must be resolved before P0 execution begins.

**Blocking categories:**
1. 9Router fabrication (5 fixes) — ALL P1 steps affected
2. Secrets management (4 fixes) — ADR-015 violations
3. Redis DB assignments (1 fix) — ADR-030 violation
4. Fallback chain (1 fix) — ADR-028 violation
5. Missing fields (4 fixes) — structural completeness
6. AC coverage gaps (5 fixes) — missing safety tests
7. Evidence paths (1 fix) — convention mismatch
8. HARD STOP timing (1 fix) — safety-critical ordering

**Recommendation:** Fix the 19 critical items, then re-audit. HIGH findings can be resolved incrementally during implementation.

---

*Audit conducted 2026-05-31 by 5 parallel deep audit agents. Consolidated by Guinevere parent orchestrator.*
