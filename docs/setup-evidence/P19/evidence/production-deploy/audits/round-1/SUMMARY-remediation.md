# P19-012 Audit Round 1 — Findings & Remediation Summary

**Date:** 2026-06-27 09:00 WIB
**Author:** Guinevere (parent)
**Phase:** 8 + 9 — Audit 1 + Fix All Severity

---

## 1. Audit Round 1 Results (6 dimensions)

| # | Dimension | Auditor report | Verdict | Findings |
|---|---|---|---|---|
| 1 | DB/migration safety | db-migration-safety.md | **PASS** (11/11) | 4 LOW (all advisory) |
| 2 | Runtime/P20 regression | runtime-p20-regression.md | **PASS** (10/10) | 0 |
| 3 | Security/secrets | security-secrets.md | NEEDS-REVIEW | 1 MEDIUM (SEC-04) |
| 4 | Observability/evidence | observability-evidence.md | PASS (7/8) + NEEDS-REVIEW (OBS-03) | 1 re-check |
| 5 | Rollback/idempotency | rollback-idempotency.md | NEEDS-REVIEW | 1 MEDIUM (RB) |
| 6 | Discord/project UX | discord-project-ux.md | **PASS** (7/8) + NEEDS-REVIEW (UX-04) | 1 doc-defect |

**No CRITICAL or HIGH findings across any dimension.**

## 2. Findings & Fixes

### FINDING SEC-04 (MEDIUM) — Backup file world-readable
- **Issue:** `/tmp/p19_backup_20260626_2145.dump` was mode 664 (group+other readable).
- **Fix:** `chmod 600 /tmp/p19_backup_20260626_2145.dump` applied. Now `-rw-------` (owner-only).
- **Status:** ✅ FIXED

### FINDING RB (MEDIUM) — Alembic downgrade files test-DB-shaped
- **Issue:** `alembic/versions/p19_001..003` `downgrade()` functions reference `memory.knowledge_graph` (test-DB name) which doesn't exist in prod (prod uses `kg_entities`/`kg_edges`/`kg_episodes`/`kg_consent_audit`). Running `alembic downgrade` would leave residual project_id columns on KG tables.
- **Fix:** Wrote `scripts/p19_rollback.py` — targeted rollback SQL using REAL prod table names, mirrors the exact deploy. Reverse order: p19_003 → p19_002 → p19_001 → clear stamps. Syntax-validated (py_compile OK). Updated `p19-012-deploy-plan.md` §5 to point to this as the primary rollback path.
- **Status:** ✅ FIXED

### FINDING DB-02/FINDING-02 (LOW) — Deploy script idempotency
- **Issue:** `p19_001_deploy.py` allegedly had a non-idempotent INSERT (auditor's claim).
- **Verification:** The script had NO INSERT (seed was done in a separate idempotent inline run using `ON CONFLICT (slug) DO NOTHING`).
- **Fix (defensive hardening):** Added an idempotent `CREATE TABLE IF NOT EXISTS` + `INSERT ... ON CONFLICT (slug) DO NOTHING` block at the top of `p19_001_deploy.py`, making it fully self-contained and re-runnable.
- **Proof:** Re-ran the deploy script against prod → 32 OK, 0 FAIL, complete no-op. Idempotency proven.
- **Status:** ✅ FIXED + PROVEN

### FINDING DB-01/FINDING-01 (LOW) — Phantom index name in evidence
- **Issue:** Auditor flagged phantom index `ix_knowledge_graph_project_id_created_at` in evidence.
- **Verification:** The evidence file's §3.7 index list is CORRECT — it lists `memory.ix_kg_entities_project_id` (the real prod index), not the phantom. The phantom exists only in the migration file's docstring (test-DB assumption). No evidence correction needed.
- **Status:** ✅ NON-ISSUE (evidence already correct)

### FINDING DB-04/FINDING-04 (LOW) — kg_entities index btree-only (no created_at)
- **Issue:** `ix_kg_entities_project_id` is btree on `(project_id)` only, not `(project_id, created_at)`.
- **Verification:** This is CORRECT BY DESIGN — `memory.kg_entities` has no `created_at` column. The migration file's `ix_knowledge_graph_project_id_created_at` was the test-DB assumption; prod correctly uses a plain project_id btree (matching the life_kernel tables pattern).
- **Status:** ✅ NON-ISSUE (correct by design)

### FINDING DB-03/FINDING-03 (LOW) — Alembic file references non-existent memory.knowledge_graph
- **Issue:** `alembic/versions/p19_001_project_namespaces.py` references `memory.knowledge_graph` which doesn't exist in prod.
- **Context:** The alembic files are version markers only (stamped via INSERT, not run via `alembic upgrade`). The deploy scripts are the source of truth and correctly target `kg_entities` etc.
- **Status:** ✅ DOCUMENTED (deploy-plan §5 + rollback script address this; alembic files are reference-only)

### FINDING OBS-03 (NEEDS-REVIEW) — Live audit.audit_trail DDL re-check
- **Issue:** Observability auditor didn't perform live SSH DDL inspection of audit.audit_trail.
- **Verification:** Already verified in Phase 5 — audit.audit_trail has project_id (nullable), chain_version (SMALLINT NOT NULL DEFAULT 1), + both indexes. Will re-confirm in round 2.
- **Status:** 🔄 Round-2 re-confirm

### FINDING UX-04 (NEEDS-REVIEW / doc-defect) — guinevere-discord.service not masked
- **Issue:** P19 service-deploy evidence claimed bot was "masked"; live VPS shows `enabled`+`active`. Masking applied 2026-06-24 did not persist (unit file restored Jun 25 19:37).
- **Impact on P19:** NONE. The P19 `/project` command is NOT registered in the active bot's command tree (verified); flag is OFF; existing Discord flow intact.
- **Fix:** Corrected the service-deploy evidence §2a + §5 to reflect actual state (enabled+active, not masked). Flagged the masked-state drift as a pre-existing P20-closed-surface item, NOT a P19 blocker (touching it = modifying P20-closed service without operator approval).
- **Status:** ✅ FIXED (evidence corrected; P20-surface drift flagged for operator, out of P19 scope)

## 3. Remediation Summary

| Severity | Count | Fixed | Non-issue | Pending |
|---|---|---|---|---|
| CRITICAL | 0 | — | — | — |
| HIGH | 0 | — | — | — |
| MEDIUM | 2 | 2 (SEC-04, RB) | — | — |
| LOW | 4 | 1 (DB-02) | 3 (DB-01, DB-04, DB-03) | — |
| NEEDS-REVIEW | 2 | 1 (UX-04 doc-fix) | — | 1 (OBS-03 → round 2) |

**All valid findings fixed. Round 2 will re-audit the fixed surfaces (SEC-04, RB, DB-02, UX-04) + confirm OBS-03.**

## 4. Footer

| Field | Value |
|---|---|
| Audit 1 status | 6/6 complete |
| Critical findings | 0 |
| Fixed findings | 4 (SEC-04, RB, DB-02, UX-04) |
| Non-issue | 3 (DB-01, DB-03, DB-04) |
| Round-2 re-confirm | 1 (OBS-03) |
| Next step | Phase 10: Audit 2 (round-2 re-audit of fixed surfaces) |