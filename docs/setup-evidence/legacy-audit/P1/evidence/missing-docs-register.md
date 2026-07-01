# P1 Missing / Stale / Superseded Documentation Register

**Date:** 2026-06-25
**Scope:** All documentation, evidence, config, and index defects identified across Round-1 (D1-D4) and Round-2 (D1-verify, D2-verify, D3-verify, D4-verify, completeness-critic) audits.
**Constraint:** READ-ONLY consolidation. No source code or documents modified.
**Audit Trail:** 8 reports consolidated.

---

## Register Summary

| Category | Total | Critical | High | Medium | Low | Cosmetic |
|----------|-------|----------|------|--------|-----|----------|
| Missing STEP directories | 7 | 0 | 1 | 0 | 6 | 0 |
| Stale evidence snapshots | 4 | 0 | 0 | 2 | 2 | 0 |
| Encoding defects | 3 | 0 | 0 | 0 | 3 | 0 |
| Missing doc index entries | 2 | 0 | 0 | 1 | 1 | 0 |
| Missing attribution / cross-references | 2 | 0 | 0 | 0 | 1 | 1 |
| Stale config references | 3 | 0 | 0 | 1 | 1 | 1 |
| Inconsistent claims between documents | 3 | 0 | 1 | 2 | 0 | 0 |
| Audit plan scaffold defects | 1 | 0 | 0 | 1 | 0 | 0 |
| **TOTAL** | **25** | **0** | **2** | **7** | **14** | **2** |

**Verdict impact:** 2 High items weaken the audit verdict. Neither is a code defect or secret leak. Both are documentation / test coverage gaps that affect audit confidence, not runtime safety.

---

## 1. Missing STEP Directories

### REG-MISS-01: STEP-P1-008 through STEP-P1-011 (4 directories)

| Field | Value |
|-------|-------|
| **What's missing** | STEP directories for P1-008 (GPT-5.5 provider setup), P1-009 (GPT-5.5 connectivity), P1-010 (DeepSeek V4 Flash setup), P1-011 (DeepSeek connectivity) |
| **Where they should be** | `docs/setup-evidence/P1/STEP-P1-008/` through `STEP-P1-011/` |
| **Evidence source** | `docs/setup-evidence/P1/migration-9router/evidence.md` lines 56-60 (GPT-5.5 REAL RESPONSE) and section 3 (provider list). Evidence IS present but in a different file/directory structure. |
| **Severity** | **High** |
| **Auditor source** | D2 (round-1), D2-verify (round-2), completeness-critic Q1/Q3 |
| **Affects verdict?** | Yes -- weakens evidence completeness. 33% of claimed 21-step structure has no standalone evidence directory. CHECKLIST.md claims "21/21 verified" but only 14/21 have dedicated STEP dirs. |
| **Resolution** | Create bridging STEP directories with a note file pointing to `migration-9router/evidence.md` and the relevant section/line range, OR update CHECKLIST to acknowledge non-standard evidence location. |

### REG-MISS-02: STEP-P1-012 through STEP-P1-014 (3 directories)

| Field | Value |
|-------|-------|
| **What's missing** | STEP directories for P1-012 (Ollama install), P1-013 (Ollama model pull), P1-014 (Ollama fallback test) |
| **Where they should be** | `docs/setup-evidence/P1/STEP-P1-012/` through `STEP-P1-014/` |
| **Justification** | SKIPPED per Faiz directive 2026-06-01, documented in `docs/setup-evidence/P1/adr-028-skip-ollama.md`. ADR-028 is thorough: 10 validation checks, auditor gate with 3 findings fixed, rollback safety documented. |
| **Severity** | Low |
| **Auditor source** | D2 (round-1), D2-verify (round-2), completeness-critic Q2 |
| **Affects verdict?** | No -- properly justified via ADR-028. |
| **Resolution** | None required. Consider adding a placeholder `README.md` in each missing STEP dir stating "SKIPPED -- see adr-028-skip-ollama.md" for discoverability. |

---

## 2. Stale Evidence Snapshots

### REG-STALE-01: P1-015 llm_router.py snapshot (90 lines vs 253 live)

| Field | Value |
|-------|-------|
| **What's stale** | `docs/setup-evidence/P1/STEP-P1-015/llm_router.py` is a 90-line P1 snapshot. Live `src/core/services/llm_router.py` is 253 lines (rewritten in Phase 6). |
| **Evidence** | D1 (round-1) Section 8: model comparison table. Primary model changed from gpt-5.5 to ds/deepseek-v4-flash. Temperature 0.7->0.5, max_tokens 16384->8192. CostTracker added, metrics added, SSE stripping added. |
| **Severity** | Medium |
| **Auditor source** | D1 (round-1) |
| **Affects verdict?** | No -- the P1 architecture (TaskType enum, fallback chain, 9Router routing) is preserved. The drift is documented enhancement, not regression. |
| **Resolution** | Add a note in the evidence directory: "Snapshot accurate for P1 epoch. Source was enhanced in Phase 6 (253 lines). See `src/core/services/llm_router.py` for current." |

### REG-STALE-02: P1-018 guinevere-core.service evidence vs live (5 divergences)

| Field | Value |
|-------|-------|
| **What's stale** | `docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service` has 5 divergences from `vps-mirror/systemd-live/guinevere-core.service`: (1) EnvironmentFile added in live, (2) NoNewPrivileges=true removed from live, (3) ProtectSystem changed strict->full, (4) ProtectHome=read-only removed, (5) ReadWritePaths expanded with .hermes path. |
| **Evidence** | D3 (round-1) check D3-05, D3-verify (round-2) confirmed all 5 divergences. |
| **Severity** | Medium |
| **Auditor source** | D3 (round-1), D3-verify (round-2) |
| **Affects verdict?** | Yes -- security hardening regression in live unit. NoNewPrivileges and ProtectHome removed, ProtectSystem relaxed. This is a runtime security concern, not a documentation concern per se, but the evidence snapshot no longer represents the deployed state. |
| **Resolution** | Either (a) update evidence snapshot to match live, or (b) add a note in evidence directory documenting the divergences and rationale. Also flag the security regression separately for operator review. |

### REG-STALE-03: P1-020 Redis key count (11 keys vs 13+ in live code)

| Field | Value |
|-------|-------|
| **What's stale** | `docs/setup-evidence/P1/STEP-P1-020/redis-db5-keys.txt` shows 11 Redis keys. Current `cost_tracker.py` lines 34-49 write ~13 unique key patterns (5 cost + 8 token) plus dynamically-created daily/monthly keys. |
| **Evidence** | D3 (round-1) check D3-09, completeness-critic Q4/Q6. |
| **Severity** | Low |
| **Auditor source** | D3 (round-1), completeness-critic Q4 |
| **Affects verdict?** | No -- point-in-time snapshot was accurate at P1 epoch. Drift is documented. |
| **Resolution** | Add note: "Snapshot accurate for P1 epoch. cost_tracker.py now writes 13+ key patterns. See `src/core/services/cost_tracker.py:34-49`." |

### REG-STALE-04: P1-005 config.yaml Prometheus port (9091 vs 9191)

| Field | Value |
|-------|-------|
| **What's stale** | `docs/setup-evidence/P1/STEP-P1-005/config.yaml:77` declares `port: 9091` for Prometheus metrics. Live `hermes-config/config.yaml` uses `metrics_port: 9191`. `llm_metrics.py:88` binds to `9191`. |
| **Evidence** | D3-verify (round-2) NEW-01. |
| **Severity** | Low |
| **Auditor source** | D3-verify (round-2) |
| **Affects verdict?** | No -- evidence-reality mismatch only. Live code and live config agree on 9191. |
| **Resolution** | Add note in evidence directory documenting the port change. |

---

## 3. Encoding Defects

### REG-ENC-01: UTF-16LE encoding on 3 evidence .txt files

| Field | Value |
|-------|-------|
| **Affected files** | `STEP-P1-015/import-test.txt` (496 bytes), `STEP-P1-016/system-prompt-loaded.txt` (1206 bytes), `STEP-P1-019/health-check.txt` (962 bytes) |
| **What's wrong** | All 3 files are UTF-16 little-endian with BOM (`ff fe`). Should be UTF-8. Caused by SSH client capturing VPS output with wrong encoding. |
| **Content recoverable?** | Yes -- Perl UTF-16LE decode produces valid content. Verified by Round-1 D2. |
| **Severity** | Low (all 3) |
| **Auditor source** | D2 (round-1) check D2-05, D2-verify (round-2) confirmed. |
| **Affects verdict?** | No -- content is genuine, not fabricated. All decoded content verified against VPS output expectations. |
| **Resolution** | Re-capture with explicit encoding control: `script -c "command" -q output.txt` or `command > output.txt` with `LANG=en_US.UTF-8`. |

---

## 4. Missing Doc Index Entries

### REG-INDEX-01: docs/README.md has no P1 entry

| Field | Value |
|-------|-------|
| **What's missing** | `docs/README.md` (333 lines) has entries for P12 (line 138), P13 (lines 139-140), P16 (lines 141-142) but zero entries for P1. |
| **Where it should be** | Row in the `docs/README.md` table, under the governance/setup-evidence section. |
| **Severity** | Low |
| **Auditor source** | D2 (round-1) bug D2-B05, completeness-critic Q9. |
| **Affects verdict?** | No -- docs index is a navigation aid, not an evidence artifact. |
| **Resolution** | Add a row: `| XX | [P1 LLM + Hermes Foundation](setup-evidence/P1/) | v1.0 | Diterima | ~36 files |` |

### REG-INDEX-02: PROGRESS.md P1-021 test count inflation (142 vs 70)

| Field | Value |
|-------|-------|
| **What's wrong** | `PROGRESS.md:132` claims "142/142 tests PASS (56 handler + 86 comprehensive)". P1-021 `evidence.md` claims "70/70 tests PASS (56 handler + 14 model compliance)". The 86 "comprehensive" tests were added post-P1 in Phase 4/6. |
| **Severity** | Medium |
| **Auditor source** | D2 (round-1) bug D2-B01, D2-verify (round-2) confirmed, completeness-critic NEW-07. |
| **Affects verdict?** | Yes -- inflates P1 test coverage claim by 103%. A reader comparing PROGRESS.md to evidence.md would find contradictory numbers with no reconciliation note. |
| **Resolution** | Change PROGRESS.md line 132 to: "70/70 tests PASS (56 handler + 14 model compliance; 86 comprehensive added post-P1 in Phase 4/6)" |

---

## 5. Missing Attribution / Cross-References

### REG-ATTRIB-01: migration-9router doc-sync omits P1-009

| Field | Value |
|-------|-------|
| **What's missing** | `docs/setup-evidence/P1/migration-9router/evidence.md:92` claims "P1-008 + P1-010 + P1-011 effectively satisfied" but omits P1-009. The GPT-5.5 connectivity evidence (P1-009) IS present at lines 56-60 but is not listed in the doc-sync claim line. |
| **Severity** | Low |
| **Auditor source** | completeness-critic Q3, NEW-03. |
| **Affects verdict?** | No -- evidence content is present, only the labeling line is incomplete. |
| **Resolution** | Edit line 92 to include P1-009 in the list. |

### REG-ATTRIB-02: P1-006 / P1-007 evidence thinner than batch-plan planned

| Field | Value |
|-------|-------|
| **What's missing** | `batch-plan-006-007.md` Section 5 planned 9 evidence files for P1-006 and P1-007 combined. Actual: P1-006 has 2 files (evidence.md, 9router-install.txt) and P1-007 has 1 file (evidence.md). 5 of 9 planned files were not created. |
| **Severity** | Cosmetic |
| **Auditor source** | completeness-critic NEW-05. |
| **Affects verdict?** | No -- evidence.md files in both directories are present and contain substantive content. |
| **Resolution** | No action required. Batch plan was more ambitious than execution delivered. Optionally update batch plan to match actual. |

---

## 6. Stale Config References

### REG-CONFIG-01: CHECKLIST P1 Section 3.6 "20 steps" (should be 21)

| Field | Value |
|-------|-------|
| **What's wrong** | `CHECKLIST.md:233` P1 Phase Complete Criteria says "All 20 steps verified" but P1 has 21 steps (P1-001 through P1-021). |
| **Severity** | Cosmetic |
| **Auditor source** | D2-verify (round-2) bug D2-R2-B01. |
| **Affects verdict?** | No -- off-by-one in completion criteria text only. |
| **Resolution** | Change "20" to "21" at CHECKLIST.md line 233. |

### REG-CONFIG-02: CHECKLIST P1 Phase Complete Criteria items unchecked

| Field | Value |
|-------|-------|
| **What's wrong** | `CHECKLIST.md:231-238` P1 Phase Complete Criteria has 5 unchecked items (`- [ ]`) despite P1 being marked 21/21 complete. This is a systemic pattern across all phases. |
| **Severity** | Low |
| **Auditor source** | D2-verify (round-2) bug D2-R2-B02. |
| **Affects verdict?** | No -- systemic across all phases, not P1-specific. Creates a false impression that phase exit criteria were not met. |
| **Resolution** | Check the P1 Phase Complete Criteria items, or add a note explaining they are template items for future phases. |

### REG-CONFIG-03: Round-1 D3 report phantom typo in VPS path

| Field | Value |
|-------|-------|
| **What's wrong** | D3 (round-1) report D3-08 notes section transcribes `SOPS_AGE_KEY_FILE=/home/guinevera/secrets/age-key.txt` (missing trailing 'e'). Actual file `scripts/health-check-p1.sh:36` reads `SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt`. The round-1 auditor introduced a phantom typo into their report. |
| **Severity** | Cosmetic |
| **Auditor source** | D3-verify (round-2) NEW-03. |
| **Affects verdict?** | No -- the PASS verdict for D3-08 is correct. The typo exists only in the audit report, not in the source code. |
| **Resolution** | Correct the typo in the round-1 D3 report. |

---

## 7. Inconsistent Claims Between Documents

### REG-INCON-01: D1 vs D4 contradiction on .chat() caller classification

| Field | Value |
|-------|-------|
| **What's inconsistent** | D1 (round-1) classified all 6 `.chat()` callers as "HERMESBRAIN-WIRED" (PASS). D4 (round-1) classified the same 6 callers as "UNGATED" (NEEDS-REVIEW). These are mutually exclusive assessments of the same code paths. |
| **Resolution** | D4's classification is correct. Callers use loop infrastructure (DI, CostTracker, 9Router) but bypass P20 safety kernel. D1's PASS on D1-02 should be revised to NEEDS-REVIEW. Completeness-critic NEW-01 adjudicated this. |
| **Severity** | **High** |
| **Auditor source** | completeness-critic Q6, NEW-01. |
| **Affects verdict?** | Yes -- weakens D1's overall PASS verdict. D1-02 should be NEEDS-REVIEW, not PASS. |

### REG-INCON-02: CHECKLIST claims 21/21 but only 14 STEP directories exist

| Field | Value |
|-------|-------|
| **What's inconsistent** | CHECKLIST.md marks all 21 P1 steps as `[x]` (complete). Only 14 of 21 STEP directories exist in the evidence tree. 4 directories (P1-008/009/010/011) have no standalone evidence -- only inline content in `migration-9router/evidence.md`. |
| **Severity** | Medium |
| **Auditor source** | D2 (round-1), D2-verify (round-2), completeness-critic Q1/Q3. |
| **Affects verdict?** | Not a runtime concern but weakens evidence auditability. A future auditor would expect 21 STEP directories and find only 14. |
| **Resolution** | Either create 4 bridging STEP directories with pointer files, or add a note in CHECKLIST acknowledging the non-standard evidence locations. |

### REG-INCON-03: CHECKLIST P1-021 says 70/70 but PROGRESS.md says 142/142

| Field | Value |
|-------|-------|
| **What's inconsistent** | `CHECKLIST.md:218` says "70/70 PASS" (consistent with evidence.md). `PROGRESS.md:132` says "142/142 PASS (56 handler + 86 comprehensive)". The 86 "comprehensive" tests were added after the P1 evidence snapshot. |
| **Severity** | Medium |
| **Auditor source** | D2 (round-1) bug D2-B01, D2-verify (round-2) confirmed, completeness-critic NEW-07. |
| **Affects verdict?** | Inflates P1 test coverage claim. PROGRESS.md and CHECKLIST.md disagree on the same metric. |
| **Resolution** | Reconcile: update PROGRESS.md to note the 142 figure includes post-P1 test additions. |

---

## 8. Audit Plan Scaffold Defects

### REG-SCAFFOLD-01: D3-03 scaffold command references non-existent REGISTRY export

| Field | Value |
|-------|-------|
| **What's wrong** | Audit plan D3-03 scaffold command `python -c "from src.core.services.llm_metrics import REGISTRY; print('Import OK')"` fails with `ImportError`. Module exports individual metric objects (LLM_CALLS_TOTAL, etc.) that auto-register with Prometheus default REGISTRY. No named REGISTRY export exists. |
| **Severity** | Medium |
| **Auditor source** | D3 (round-1), D3-verify (round-2) confirmed. |
| **Affects verdict?** | No -- the module itself is fine. The scaffold command was wrong, not the code. But it indicates the plan author did not verify the command against actual module exports. |
| **Resolution** | Correct the audit plan to use `python -c "import src.core.services.llm_metrics; print('Import OK')"`. |

---

## Appendix: Source Report Index

All paths relative to `docs/setup-evidence/legacy-audit/P1/audits/`:

| Report | Path |
|--------|------|
| D1 Round-1 | `round-1/architecture-implementation.md` |
| D2 Round-1 | `round-1/evidence-docs-consistency.md` |
| D3 Round-1 | `round-1/runtime-config-readiness.md` |
| D4 Round-1 | `round-1/d4-security-secrets-safety.md` |
| D1 Round-2 | `round-2/d1-architecture-verify.md` |
| D2 Round-2 | `round-2/d2-evidence-docs-verify.md` |
| D3 Round-2 | `round-2/d3-runtime-config-verify.md` |
| D4 Round-2 | `round-2/d4-security-verify.md` |
| Completeness Critic | `round-2/completeness-critic.md` |

---

## Appendix: Cross-Reference to Implementation Gap Register

The companion register at `docs/setup-evidence/legacy-audit/P1/evidence/implementation-gap-register.md` covers code-level defects (latent bugs N1/N2, missing tests, security architectural debt). This document covers documentation/evidence-level defects only. There is intentional separation between code gaps and doc gaps.

---

*End of register. READ-ONLY consolidation -- no files modified except this output.*
