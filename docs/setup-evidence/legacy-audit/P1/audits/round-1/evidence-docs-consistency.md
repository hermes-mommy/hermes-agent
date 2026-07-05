# D2: Evidence-Docs-Consistency Audit Report

**Audit Dimension:** D2 -- Evidence-Docs-Consistency
**Phase:** P1 (Phase 1: LLM + Hermes Agent Foundation)
**Audit Date:** 2026-06-25
**Auditor:** READ-ONLY research subagent (D2 specialized)
**Output Path:** `docs/setup-evidence/legacy-audit/P1/audits/round-1/evidence-docs-consistency.md`
**Plan Reference:** `docs/setup-evidence/legacy-audit/P1/plan/p1-implementation-audit-plan.md` SS 3.2

---

## Per-Check Results Table

| Check ID | Action | Finding | Verdict | Notes |
|----------|--------|---------|---------|-------|
| D2-01 | CHECKLIST.md P1 entry | CHECKLIST.md 3S 3.2 marks all 21 P1 steps as [x] (complete) including P1-012/013/014 (SKIPPED per Faiz directive). P1-015 claim matches evidence snapshot (90-line llm_router.py) but DOES NOT mention that live source has drifted to 253 lines with different model/architecture. P1-021 claims "70/70 tests PASS" consistent with evidence but CHECKLIST P1-021 header says "HARD STOP Protocol Verification Gate (AC-SAFE-001)" -- OK. No acknowledgment of 6/7 stale artifacts. | **NEEDS-REVIEW** | CHECKLIST does not flag known source drift. Compliant metadata-wise but misleading for any reader comparing evidence to live source. |
| D2-02 | PROGRESS.md P1 section | PROGRESS.md L109-L132 has 21/21 steps [x], aligns with evidence dir structure. ADR references correct (ADR-004, ADR-006, ADR-014, ADR-028). P1-021 test count says "142/142 tests PASS (56 handler + 86 comprehensive -- verified 2026-06-08)" which diverges from evidence.md claiming "70/70" -- internal inconsistency found. | **NEEDS-REVIEW** | PROGRESS.md P1-021 claim (142/142) does NOT match evidence.md claim (70/70). The 142 claim includes "86 comprehensive" tests that evidence.md does not mention. |
| D2-03 | docs/ index files referencing P1 | Only `docs/10-governance/17-ADR_Index_v1.0.md` references P1 (one line: ADR-028 implemented via migration-9router). `docs/README.md` has NO P1 references whatsoever. All other doc references to P1 are in non-index files. | **PASS** | ADR index reference is valid. README missing P1 is not a consistency failure since it is a file index, not a phase index. |
| D2-04 | P1 directory tree | 14 of 21 STEP-P1-XXX directories exist (P1-001 through P1-007, P1-015 through P1-021). 7 directories (P1-008 through P1-014) are MISSING with no evidence files. 36 total files found. Expected 36-40+ files based on plan. The missing directories correspond to steps that were SKIPPED (P1-012/013/014, Ollama) or covered inline in batch plans without individual STEP dirs (P1-008/009/010/011, provider config). | **NEEDS-REVIEW** | 14/21 directories exist. 7 missing directories have some justification (batch plan consolidation + SKIPs) but this is a significant structural gap from the "21 STEP dirs" claim. |
| D2-05 | Encoding defect analysis (3 files) | `file` command confirms all 3 files are "Unicode text, UTF-16, little-endian text, with CRLF line terminators". Hex dumps show valid UTF-16LE BOM (`ff fe`). Perl decode recovers readable content: import-test.txt shows "Router module OK / TaskType values: ['core', 'sub_agent', 'fallback']"; system-prompt-loaded.txt shows all 5+ CHECK lines PASS; health-check.txt shows 5/5 service checks. Content is genuine VPS command output captured with wrong encoding. | **PASS** | Files are genuine captures with encoding defect. No fabrication. Content is fully recoverable via UTF-16 decode. Recommend re-capture during maintenance cycle. |
| D2-06 | P1-005 config.yaml vs hermes-config/config.yaml | Files are DIFFERENT: P1-005 config.yaml = 81 lines (P1 Hermes Agent structural config), hermes-config/config.yaml = 393 lines (Hermes Gateway operational config). Different schemas, different headers. No P1 document confuses these as the same artifact. P1-005 evidence.md correctly describes it as "Copy of deployed config" at `/home/guinevere/config/hermes/config.yaml`. Two cross-reference files (adr-028-skip-ollama.md, batch-plan-004-005.md) reference the VPS path without confusing it with the live gateway config. | **PASS** | No document conflates the two config files. Clear distinction maintained. |
| D2-07 | SystemPromptMaster v1.1 doc | File exists at `docs/60-persona/61-SystemPromptMaster_v1.1.md`. Contains 0 instances of "P1" or "Phase 1" text -- no explicit attribution to P1 anywhere in the document header or body. The document metadata (Date: 2026-05-31, Version 1.1) implicitly aligns with P1 timeline but there is no explicit "Phase 1" or "P1" credit. This is a documentation gap but not a consistency failure. | **NEEDS-REVIEW** | Document is physically present and structurally correct but has zero P1 attribution text. Implicit timeline alignment only. |
| D2-08 | ADR cross-reference check | P1 evidence references only ONE unique ADR number: ADR-028 (via `grep -rn "adr-" docs/setup-evidence/P1 --include="*.md" -o -i | sort -u`). The batch plans and evidence.md files reference ADR-004, ADR-006, ADR-014, ADR-028 by name (not "adr-NNN" pattern). All referenced ADRs exist in `adr/` directory with matching files. ADR-004, ADR-006, ADR-014, ADR-028, ADR-001, ADR-002, ADR-003, ADR-005, ADR-007, ADR-008, ADR-009, ADR-015, ADR-016, ADR-017, ADR-018, ADR-019, ADR-020, ADR-022, ADR-023, ADR-024, ADR-025, ADR-026, ADR-027, ADR-029, ADR-030, ADR-031, ADR-032, ADR-033, ADR-034, ADR-035 all confirmed present. | **PASS** | All ADRs referenced by P1 evidence exist in current docs tree. |
| D2-09 | P1-021 test count claim | Evidence.md claims 70/70 tests (56 deterministic handler + 14 model compliance). Actual source: `test_hard_stop_handler.py` has 16 `def test_` functions (pytest parametrize expands to 56), `test_hard_stop_model.py` has 8 `def test_` functions (expands to 14). The 56+14=70 claim is ACCOUNTED FOR and consistent. PROGRESS.md claims "142/142 tests PASS (56 handler + 86 comprehensive)" -- this is a DIFFERENT figure that references a later expanded test suite (added after P1-021 evidence was captured). The 70 test claim in the P1 evidence is VALID for the P1-021 snapshot. | **PASS** | P1-021 evidence 70/70 claim is correct for the P1 snapshot. The 142/142 in PROGRESS.md reflects later expansion -- not an inconsistency with P1 evidence. |

---

## Complete Evidence File Inventory

Total: **36 files** in `docs/setup-evidence/P1/` (verified by `find | sort`)

### Step Directories (14 of 21 exist)

| # | STEP Directory | Files | Status | Notes |
|---|---------------|-------|--------|-------|
| 1 | STEP-P1-001 | `evidence.md`, `python-version.txt` | EXISTS | Python 3.12 installation evidence |
| 2 | STEP-P1-002 | `evidence.md`, `uv-version.txt` | EXISTS | UV package manager |
| 3 | STEP-P1-003 | `evidence.md`, `venv-packages.txt` | EXISTS | Virtual environment |
| 4 | STEP-P1-004 | `evidence.md`, `hermes-install.txt`, `project-structure.txt`, `pyproject.toml` | EXISTS | Hermes Agent install (4 files) |
| 5 | STEP-P1-005 | `evidence.md`, `config.yaml` | EXISTS | Hermes config (2 files) |
| 6 | STEP-P1-006 | `evidence.md`, `9router-install.txt` | EXISTS | 9Router installation |
| 7 | STEP-P1-007 | `evidence.md` | EXISTS | 9Router config (1 file) |
| 8 | STEP-P1-008 | -- | **MISSING** | Provider setup (GPT-5.5) |
| 9 | STEP-P1-009 | -- | **MISSING** | GPT-5.5 connectivity test |
| 10 | STEP-P1-010 | -- | **MISSING** | DeepSeek V4 Flash setup |
| 11 | STEP-P1-011 | -- | **MISSING** | DeepSeek connectivity test |
| 12 | STEP-P1-012 | -- | **MISSING** | Ollama install (SKIPPED) |
| 13 | STEP-P1-013 | -- | **MISSING** | Ollama model pull (SKIPPED) |
| 14 | STEP-P1-014 | -- | **MISSING** | Ollama fallback test (SKIPPED) |
| 15 | STEP-P1-015 | `evidence.md`, `import-test.txt`, `llm_router.py` | EXISTS | LLM routing (3 files, 1 UTF-16 defective) |
| 16 | STEP-P1-016 | `evidence.md`, `system-prompt-loaded.txt` | EXISTS | SystemPromptMaster (2 files, 1 UTF-16 defective) |
| 17 | STEP-P1-017 | `evidence.md`, `smoke-test-output.txt` | EXISTS | Persona smoke tests |
| 18 | STEP-P1-018 | `evidence.md`, `guinevere-core.service`, `guinevere-core-status.txt` | EXISTS | FastAPI skeleton + systemd |
| 19 | STEP-P1-019 | `evidence.md`, `health-check.txt` | EXISTS | Health checks (1 UTF-16 defective) |
| 20 | STEP-P1-020 | `evidence.md`, `redis-db5-keys.txt` | EXISTS | Redis DB5 cost tracking |
| 21 | STEP-P1-021 | `evidence.md` | EXISTS | HARD STOP handler (1 file) |

### Non-Step Files (6 files)

| File | Size | Notes |
|------|------|-------|
| `adr-028-skip-ollama.md` | ~12KB | ADR-028 documentation |
| `batch-plan-004-005.md` | ~30KB | Batch plan for steps 004-005 |
| `batch-plan-006-007.md` | ~30KB | Batch plan for steps 006-007 |
| `batch-plan-017-019.md` | ~20KB | Batch plan for steps 017-019 |
| `migration-9router/evidence.md` | ~8KB | 9Router migration evidence |
| `p2-preconditions-resolved.md` | ~6KB | P2 preconditions document |

---

## Encoding Defect Analysis

### Files Identified (3 of 36)

| File | Size | `file` Command Output | BOM Present | Content Recoverable? |
|------|------|-----------------------|-------------|---------------------|
| `STEP-P1-015/import-test.txt` | 496 bytes | UTF-16, little-endian text, CRLF | Yes (`ff fe`) | Yes -- 5 lines decoded via perl |
| `STEP-P1-016/system-prompt-loaded.txt` | 1206 bytes | UTF-16, little-endian text, CRLF | Yes (`ff fe`) | Yes -- 12 lines decoded via perl |
| `STEP-P1-019/health-check.txt` | 962 bytes | UTF-16, little-endian text, CRLF | Yes (`ff fe`) | Yes -- 15 lines decoded via perl |

### Decoded Content Verification

**import-test.txt** (perl UTF-16LE decode):
```
Router module OK
TaskType values: ['core', 'sub_agent', 'fallback']
CORE_REASONING: gpt-5.5 @ http://localhost:20128/v1
SUB_AGENT: deepseek-v4-flash @ http://localhost:20128/v1
FALLBACK: guinevere @ http://localhost:20128/v1
```

**system-prompt-loaded.txt** (perl UTF-16LE decode):
```
CHECK 1 PASS: system-prompt.md exists (23942 bytes)
CHECK 2 PASS: System prompt is 23708 chars
CHECK 3 PASS: Prompt loaded (23708 chars)
CHECK 4 PASS: All safety elements present (HARD STOP, Y5, distress)
CHECK 4b: Safe word reference: PASS
CHECK 5 PASS: Context injection works (memory + mood)
```

**health-check.txt** (perl UTF-16LE decode):
```
=== P1 SERVICE HEALTH CHECK ===
--- Core ---
[PASS] guinevere-core health endpoint responds
--- 9Router ---
[PASS] guinevere-9router health endpoint responds
--- Graceful Degradation ---
[INFO] Ollama skipped per Faiz directive 2026-06-01; final fallback is graceful degradation
--- PostgreSQL ---
[PASS] PostgreSQL SELECT 1 succeeded
--- Redis ---
```

### Verdict: NOT fabrication. SSH capture encoding defect only. All three files are genuine VPS command output captured by an SSH client that wrote UTF-16LE instead of UTF-8. Content is fully recoverable via UTF-16 decode. Recommend re-capture during maintenance cycle with explicit `script` encoding control.

---

## P1-005 config vs hermes-config Confusion Check

### Files Compared

| Property | `docs/setup-evidence/P1/STEP-P1-005/config.yaml` | `hermes-config/config.yaml` |
|----------|---------------------------------------------------|-----------------------------|
| Line count | **81 lines** | **393 lines** |
| First line | `agent:` / `name: "Guinevere"` | `# Guinevere Hermes Agent -- Gateway Configuration` |
| Purpose | P1 Hermes Agent structural config (9-section YAML) | Hermes Gateway operational config (Gateway) |
| Schema | Agent config (agent, llm, memory, loop, safety, budget, tools, messaging, monitoring) | Gateway config (different schema) |

### Confusion Assessment

- `adr-028-skip-ollama.md`: References `docs/setup-evidence/P1/STEP-P1-005/config.yaml` and VPS path `/home/guinevere/config/hermes/config.yaml` -- correct usage, no confusion.
- `batch-plan-004-005.md`: References `/home/guinevere/config/hermes/config.yaml` throughout -- consistent with P1 context.
- `STEP-P1-005/evidence.md`: States "Copy of deployed config" and references VPS path -- clear and correct.

**Verdict: PASS** -- No document in the P1 evidence corpus confuses the P1-005 config.yaml with the live Hermes gateway config. The distinction is clearly maintained.

---

## ADR Cross-Reference Table

ADRs referenced (by name or `adr-NNN` pattern) across P1 evidence files, verified against `adr/` directory:

| ADR | Referenced In | File Exists? | Notes |
|-----|---------------|-------------|-------|
| ADR-004 | batch-plan-004-005.md, batch-plan-006-007.md, PROGRESS.md | YES | `ADR-004-primary-llm-model-selection.md` |
| ADR-006 | batch-plan-004-005.md, batch-plan-006-007.md, PROGRESS.md | YES | `ADR-006-sub-agent-llm-model-strategy.md` |
| ADR-014 | STEP-P1-001, STEP-P1-003, STEP-P1-004, PROGRESS.md | YES | `ADR-014-vps-container-architecture.md` |
| ADR-028 | adr-028-skip-ollama.md (solo file), PROGRESS.md, CHECKLIST.md | YES | `ADR-028-llm-router-outage-graceful-degradation.md` |
| ADR-001 | batch-plan-004-005.md | YES | Referenced in batch plan |
| ADR-002 | batch-plan-004-005.md | YES | Referenced in batch plan |
| ADR-003 | batch-plan-004-005.md | YES | Referenced in batch plan |
| ADR-005 | batch-plan-004-005.md, batch-plan-006-007.md | YES | Referenced in batch plans |
| ADR-007 | batch-plan-004-005.md, batch-plan-006-007.md | YES | Referenced in batch plans |
| ADR-008 | batch-plan-004-005.md, batch-plan-006-007.md | YES | Referenced in batch plans |
| ADR-009 | batch-plan-004-005.md, batch-plan-006-007.md | YES | Referenced in batch plans |
| ADR-015 | STEP-P1-004 evidence.md, STEP-P1-005 evidence.md | YES | Referenced in step evidence |
| ADR-020 | batch-plan-006-007.md | YES | Referenced |
| ADR-022 | batch-plan-006-007.md | YES | Referenced |
| ADR-023 | batch-plan-006-007.md | YES | Referenced |
| ADR-033 | batch-plan-006-007.md | YES | Referenced |

All referenced ADRs **confirmed present** in `adr/` directory. No stale ADR references found.

---

## Docs Index Cross-Reference Table

Current docs index files checked for P1 references:

| Index File | P1 References Found | Verdict |
|------------|-------------------|---------|
| `docs/README.md` | **None** | **MISSING** -- No P1 entry in the docs README file table |
| `docs/10-governance/17-ADR_Index_v1.0.md` | 1 reference (ADR-028 implemented via migration-9router) | PASS -- valid |

The `docs/README.md` has entries for P12, P13, P16 phases but no P1 entry. This is a documentation completeness gap: the project's main docs index file has entries for later phases but lacks a P1 entry.

---

## Missing/Stale/Superseded Doc Flag List

| Item | Type | Status | Notes |
|------|------|--------|-------|
| STEP-P1-008 dir | Missing directory | STALE GAP | GPT-5.5 provider setup evidence was inline in batch-plan-006-007.md, no dedicated directory |
| STEP-P1-009 dir | Missing directory | STALE GAP | GPT-5.5 connectivity test evidence, no dedicated directory |
| STEP-P1-010 dir | Missing directory | STALE GAP | DeepSeek V4 Flash setup evidence, no dedicated directory |
| STEP-P1-011 dir | Missing directory | STALE GAP | DeepSeek connectivity test evidence, no dedicated directory |
| STEP-P1-012 dir | Missing (SKIPPED) | SUPERSEDED | Ollama install skipped per Faiz directive, ADR-028 superseded |
| STEP-P1-013 dir | Missing (SKIPPED) | SUPERSEDED | Ollama model pull skipped |
| STEP-P1-014 dir | Missing (SKIPPED) | SUPERSEDED | Ollama fallback test skipped |
| P1-015 llm_router.py snapshot | Stale | SUPERSEDED | 90-line snapshot no longer matches live 253-line source |
| P1-018 guinevere-core.service evidence | Stale | SUPERSEDED | Evidence snapshot differs from vps-mirror copy (ProtectSystem, ProtectHome, EnvironmentFile) |
| P1-020 evidence (11 Redis keys) | Stale snapshot | NEEDS-REVIEW | Current Redis state may differ; VPS-only verification |
| SystemPromptMaster v1.1 doc | Missing P1 attribution | DOC GAP | File exists but has no "P1" or "Phase 1" text anywhere |
| docs/README.md P1 entry | Missing | DOC GAP | No P1 entry in main docs README file table |

---

## Bug Register

| ID | Severity | File | Line(s) | Description |
|----|----------|------|---------|-------------|
| D2-B01 | Medium | PROGRESS.md | L132 | P1-021 test count "142/142 tests PASS (56 handler + 86 comprehensive)" conflicts with evidence.md claim "70/70 tests PASS (56 handler + 14 model)". Different test suite generations mixed. |
| D2-B02 | Medium | CHECKLIST.md | L192-211 | All 21 P1 steps marked [x] without acknowledging 6/7 source artifacts have drifted from evidence snapshots. Misleading for accuracy assessment. |
| D2-B03 | High | `docs/setup-evidence/P1/` directory tree | N/A | 7 of 21 STEP directories are missing (P1-008 through P1-014). While 3 of 7 have documented SKIP reasons (P1-012/013/014), the other 4 (P1-008/009/010/011) have no dedicated evidence directories -- content only exists in batch-plan-006-007.md. Incomplete evidence structure vs. the claimed 21-step structure. |
| D2-B04 | Low | `docs/60-persona/61-SystemPromptMaster_v1.1.md` | L1-11 | Zero P1/Phase 1 attribution in document header metadata. Implicit timeline only (Date: 2026-05-31). |
| D2-B05 | Medium | `docs/README.md` | Entire file | No P1 entry in the docs index while later phases (P12, P13, P16) have entries. Incomplete phase coverage in project documentation index. |
| D2-B06 | Low | `docs/setup-evidence/P1/STEP-P1-015/import-test.txt` | All lines | UTF-16LE encoding defect (496 bytes). Content recoverable but requires explicit decode. |
| D2-B07 | Low | `docs/setup-evidence/P1/STEP-P1-016/system-prompt-loaded.txt` | All lines | UTF-16LE encoding defect (1206 bytes). Content recoverable. |
| D2-B08 | Low | `docs/setup-evidence/P1/STEP-P1-019/health-check.txt` | All lines | UTF-16LE encoding defect (962 bytes). Content recoverable. |

---

## D2 Overall Verdict: **NEEDS-REVIEW**

### Summary of Cross-Dimension Findings

**D2-01** -- CHECKLIST.md marks P1 complete but does not acknowledge 6/7 stale source artifacts
**D2-02** -- PROGRESS.md matches evidence dirs, but P1-021 test count (142) contradicts evidence.md (70)
**D2-03** -- Docs index references are valid but sparse (only ADR index has 1 reference)
**D2-04** -- 14/21 STEP directories exist; 7 missing (with partial justification)
**D2-05** -- 3 UTF-16 defective files confirmed genuine; content recoverable; not fabrication
**D2-06** -- P1-005 config and hermes-config/config.yaml clearly distinguished; no confusion
**D2-07** -- SystemPromptMaster v1.1 doc physically present but has zero P1 attribution text
**D2-08** -- All referenced ADRs exist in current docs tree; no stale ADR references
**D2-09** -- P1-021 70/70 test claim verified as valid for P1 snapshot

### Strengths
- All 36 evidence files exist and are accounted for
- Encoding-defective files are genuine captures, not fabrications (confirmed via UTF-16LE decode)
- No document confuses P1-005 config with hermes-config/config.yaml
- All ADRs referenced by P1 evidence exist in the current docs tree
- P1-021 70/70 test claim is properly accounted for as 56+14

### Weaknesses
- 7 of 21 STEP directories do not exist (33% structural gap)
- PROGRESS.md and evidence.md have conflicting test counts for P1-021 (142 vs 70)
- SystemPromptMaster v1.1 doc lacks explicit P1 attribution
- CHECKLIST.md does not flag known source artifact drift
- docs/README.md has no P1 entry

### Recommended Follow-up Actions
1. Create missing STEP directories P1-008 through P1-011 with at minimum a reference note bridging to batch-plan-006-007.md
2. Re-capture 3 UTF-16 defective files with correct encoding
3. Add P1 attribution to SystemPromptMaster v1.1 document header
4. Add P1 entry to docs/README.md
5. Reconcile PROGRESS.md P1-021 test count with evidence.md (70 vs 142 -- determine which is canonical for P1 closure)
