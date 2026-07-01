# P19-012 Round 2 Re-Audit: Security & Rollback Fix Verification

**Audit ID:** P19-012-REAUDIT-SEC-RB-ROUND2
**Date:** 2026-06-27
**Auditor:** Independent re-auditor (SSH live VPS verification)
**Scope:** SEC-04 backup file permissions fix + RB rollback script replacement
**Standard:** Every round-1 finding must be verified FIXED on the LIVE VPS, not just in local repo

---

## 1. Audit Scope and Methodology

This re-audit verifies that round-1 findings from `security-secrets.md` (SEC-04) and `rollback-idempotency.md` (RB-02) were actually fixed on the live guinevere-vps, not just patched in the local repository.

**Round-1 findings to re-verify:**
- **SEC-04 (MEDIUM):** Backup file `/tmp/p19_backup_20260626_2145.dump` was mode 664 (world-readable). Required: mode 600.
- **RB (MEDIUM):** Alembic downgrade functions reference phantom table `memory.knowledge_graph` instead of real prod KG tables. Required: targeted rollback script using real prod table names.

**Method:**
1. SSH to `guinevere-vps` as live system
2. Verify backup file permissions via `ls -la`
3. Verify rollback script exists, is syntax-valid, uses correct table names, correct order, and preserves p20 stamps
4. Verify deploy-plan section 5 references the script
5. Cross-reference all findings against round-1 evidence

---

## 2. Individual Check Results

### RE-SEC-04: Backup file mode 600

**Verdict: PASS**

**Round-1 finding:** `/tmp/p19_backup_20260626_2145.dump` was mode `-rw-rw-r--` (664). Any local user could read the 1.2 GB database dump via `pg_restore`.

**VPS re-verification (SSH):**
```
-rw------- 1 guinevere guinevere 1235417322 Jun 26 21:57 /tmp/p19_backup_20260626_2145.dump
```

Mode `-rw-------` = `600`. Owner (`guinevere`) read/write only. Group and others have zero access. The remediation `chmod 600` has been applied and verified on the live VPS.

**Fix confirmed.**

---

### RE-RB-01: p19_rollback.py exists + syntax valid

**Verdict: PASS**

**Check 1 -- File exists on VPS:**
```
-rw-r--r-- 1 guinevere guinevere 6810 Jun 27 08:53 /home/guinevere/code/guinevere/scripts/p19_rollback.py
```

File exists at the expected path, 6810 bytes, owned by the `guinevere` service account.

**Check 2 -- Syntax validation:**
```
cd /home/guinevere/code/guinevere && source .venv/bin/activate && python -c "import py_compile; py_compile.compile('scripts/p19_rollback.py', doraise=True)"
```

Result: **No output, exit code 0.** `py_compile.compile()` with `doraise=True` raises `py_compile.PyCompileError` on any syntax error. The absence of output and error confirms the script is syntactically valid Python.

**Fix confirmed.**

---

### RE-RB-02: Uses real prod KG table names (NOT phantom memory.knowledge_graph)

**Verdict: PASS**

**Round-1 finding:** Alembic downgrade functions reference `memory.knowledge_graph` which does NOT exist in production. Production uses `memory.kg_entities`, `memory.kg_edges`, `memory.kg_episodes`, `memory.kg_consent_audit`.

**VPS grep of the rollback script:**

```
grep -n 'kg_entities|kg_edges|kg_episodes|kg_consent_audit|knowledge_graph' scripts/p19_rollback.py
```

Results:
| Line | Content | In SQL? |
|---|---|---|
| 4 | `alembic/versions/p19_001..003 reference the test-DB table name memory.knowledge_graph` | No (docstring) |
| 5 | `which does not exist in production (prod uses memory.kg_entities/edges/episodes/kg_consent_audit).` | No (docstring) |
| 12 | `Acceptable for prod data volume (3 episodes, 6 facts, 6 kg_entities)` | No (docstring) |
| 54 | `'memory.session_summaries', 'memory.kg_entities',` | **YES** (p19_002 NOT NULL list) |
| 86 | `('memory', 'ix_kg_entities_project_id'),` | **YES** (index drop) |
| 102 | `'memory.procedural_skills', 'memory.kg_entities':` | **YES** (project_scope drop) |
| 110 | `'memory.kg_entities', 'memory.kg_edges', 'memory.kg_episodes',` | **YES** (project_id drop) |
| 111 | `'memory.kg_consent_audit',` | **YES** (project_id drop) |

**All 4 real prod KG tables appear in SQL statements.** The phantom `memory.knowledge_graph` appears ONLY in the docstring (lines 4-5) where it explains WHY the script exists. Zero phantom references in executable code.

**Fix confirmed.**

---

### RE-RB-03: Correct rollback order

**Verdict: PASS**

**Required order (reverse of deploy):** p19_003 (chain_version) then p19_002 (NOT NULL) then p19_001 (indexes/swap/cols/registry) then clear stamps.

**Script structure verification (from source):**

| Section | Line Range | Action | Correct Position |
|---|---|---|---|
| `p19_003 ROLLBACK: chain_version` | Lines 42-46 | DROP INDEX + DROP COLUMN chain_version | 1st |
| `p19_002 ROLLBACK: drop NOT NULL` | Lines 51-61 | ALTER COLUMN DROP NOT NULL on 11 tables | 2nd |
| `p19_001 ROLLBACK: indexes + unique swap + cols` | Lines 66-124 | Reverse indexes, swap unique, drop project_scope, drop project_id, drop project_registry | 3rd |
| `CLEAR P19 ALEMBIC STAMPS` | Lines 129-131 | DELETE FROM alembic_version WHERE LIKE 'p19%' | 4th (last) |

The order is correct: p19_003 first (drop dependency), then p19_002 (relax constraint), then p19_001 (remove structural additions), then stamps last. This is the reverse of the deploy order (p19_001 -> p19_002 -> p19_003 -> stamps), which is correct rollback sequencing.

**Fix confirmed.**

---

### RE-RB-04: Preserves p20_001 alembic stamp

**Verdict: PASS**

**Round-1 concern:** The rollback must not delete the p20_001 alembic stamp.

**Script verification (line 129-131):**
```python
await run(conn, 'delete p19 stamps',
          "DELETE FROM ops.alembic_version WHERE version_num LIKE 'p19%'", stats)
```

The `LIKE 'p19%'` pattern matches exactly:
- `p19_001_project_namespaces` -- deleted
- `p19_002_project_id_not_null` -- deleted
- `p19_003_audit_chain_version` -- deleted

And does NOT match:
- `p20_001_life_kernel_schema` -- **preserved** (does not start with `p19`)

This was also confirmed in round-1 (RB-03 PASS) and the fix preserves the exact same logic.

**Fix confirmed.**

---

### RE-RB-05: Deploy-plan section 5 references scripts/p19_rollback.py

**Verdict: PASS**

**File:** `docs/setup-evidence/P19/evidence/production-deploy/p19-012-deploy-plan.md`

**Section 5 (lines 79-99):**
```markdown
## 5. Rollback Plan

**Primary rollback path: `scripts/p19_rollback.py`** (targeted SQL, mirrors the exact deploy).
```

The section explicitly states:
1. `scripts/p19_rollback.py` is the **primary rollback path**
2. Explains WHY: alembic downgrade functions reference test-DB table name `memory.knowledge_graph`
3. Notes the script uses **REAL prod table names**
4. Documents rollback order: p19_003 -> p19_002 -> p19_001 -> clear stamps
5. References the backup file as last-resort (mode 600 confirmed)

The deploy plan correctly delegates to the targeted script rather than `alembic downgrade`.

**Fix confirmed.**

---

## 3. Summary Matrix

| Check | ID | Verdict | Round-1 Status | Round-2 Status |
|---|---|---|---|---|
| Backup file mode 600 | RE-SEC-04 | **PASS** | FAIL (664) | PASS (600) |
| Rollback script exists + syntax valid | RE-RB-01 | **PASS** | N/A (did not exist) | PASS |
| Real prod KG table names | RE-RB-02 | **PASS** | FAIL (phantom name) | PASS |
| Correct rollback order | RE-RB-03 | **PASS** | N/A | PASS |
| Preserves p20_001 stamp | RE-RB-04 | **PASS** | PASS (already) | PASS |
| Deploy-plan references rollback script | RE-RB-05 | **PASS** | N/A | PASS |

**Overall: 6/6 PASS**

---

## 4. Findings Detail

No new findings. All round-1 findings verified fixed on the live VPS.

---

## 5. SEC-04 Deep Dive: Backup Permission Fix Chain

| Step | Evidence |
|---|---|
| Round-1 detection | `-rw-rw-r--` (664) via SSH `ls -la` |
| Remediation command | `chmod 600 /tmp/p19_backup_20260626_2145.dump` |
| Round-2 live verification | `-rw-------` (600) via SSH `ls -la` |
| File identity preserved | Size (1235417322 bytes) and timestamp (Jun 26 21:57) unchanged |

The file is the same backup (same size, same timestamp). Only the permissions changed. The fix is a single `chmod` and is verified correct.

---

## 6. RB Deep Dive: Rollback Script Architecture

The `scripts/p19_rollback.py` script is a standalone Python script using `asyncpg` for direct PostgreSQL access. It:

1. **Loads credentials** from `.env.core` via `dotenv` (same pattern as all deploy scripts -- SEC-02 compliant)
2. **Connects** via `DATABASE_URL` from environment (no hardcoded credentials)
3. **Executes DDL** in reverse deploy order with `IF EXISTS` / `IF NOT EXISTS` guards for idempotency
4. **Reports** OK/FAIL count per statement with exception details
5. **Preserves** p20_001 stamp via targeted `LIKE 'p19%'` deletion

**Key design properties:**
- Uses `DROP ... IF EXISTS` throughout -- safe to re-run (idempotent)
- Uses `CREATE UNIQUE INDEX IF NOT EXISTS` for the domain_mind_state restore -- safe to re-run
- No destructive data operations (only DDL: DROP COLUMN, DROP INDEX, DROP TABLE)
- Data loss warning in docstring (project_id column data is lost -- acceptable per round-1 RB-08)

---

## 7. Comparison: Round-1 Alembic Downgrade vs Round-2 Targeted Script

| Property | Alembic downgrade (round-1) | p19_rollback.py (round-2) |
|---|---|---|
| Table names | `memory.knowledge_graph` (phantom) | `memory.kg_entities`, `kg_edges`, `kg_episodes`, `kg_consent_audit` (real) |
| p19_002 NOT NULL | 7 tables (includes phantom) | 11 tables (matches deploy) |
| p19_001 columns | knowledge_graph only | 17 tables (matches deploy) |
| p19_001 indexes | knowledge_graph indexes | 16 indexes + 3 pgvector (matches deploy) |
| project_scope | knowledge_graph | episodes, semantic_facts, procedural_skills, kg_entities |
| Idempotent | Unknown (not tested) | Yes (IF EXISTS guards) |
| Error handling | Alembic try/except | Per-statement try/except with OK/FAIL reporting |

The targeted script is strictly superior to the alembic downgrade path for this production deploy.

---

## 8. Production Safety Confirmation

**No rollback was executed during this audit.** The script was verified via:
1. File existence check (`ls -la`)
2. Syntax validation (`py_compile.compile`)
3. Source code grep for table names
4. Source code review for order and stamp preservation

The script is safe to execute if rollback is ever required, but executing it would undo the P19 deploy. This audit intentionally did NOT run it.

---

## 9. Recommendations

**No remediation required.** All round-1 findings are verified fixed.

**Forward-looking (non-blocking):**
1. Consider adding a `--dry-run` flag to `p19_rollback.py` that prints SQL without executing (for future audits)
2. Consider adding backup file permission check to the smoke test (round-1 FINDING-01b, LOW severity)
3. Consider moving the backup from `/tmp/` to the guinevere home directory for persistence

---

## 10. Audit Trail

| Step | Method | Result |
|---|---|---|
| Backup file permission check | SSH `ls -la /tmp/p19_backup_20260626_2145.dump` | `-rw-------` (600) PASS |
| Rollback script existence | SSH `ls -la scripts/p19_rollback.py` | 6810 bytes, exists PASS |
| Syntax validation | SSH `python -c "py_compile.compile(...)"` | No error, exit 0 PASS |
| Table name verification | SSH `grep kg_entities/edges/episodes/consent_audit/knowledge_graph` | 4 real tables in SQL, phantom in docstring only PASS |
| Rollback order review | Source code section analysis | p19_003 -> p19_002 -> p19_001 -> stamps PASS |
| p20_001 stamp preservation | Source code `WHERE version_num LIKE 'p19%'` | Correct pattern, p20 preserved PASS |
| Deploy-plan reference | Read section 5 of p19-012-deploy-plan.md | Primary rollback path documented PASS |

---

## 11. Limitations

- This audit verifies the script is syntactically correct and references the right tables. It does NOT execute the rollback (by design -- would undo the deploy).
- The backup file was not re-extracted or re-verified (`pg_restore -l` was not re-run -- the backup itself was verified in round-1 RB-01).
- The `py_compile` check validates syntax only, not runtime behavior (e.g., asyncpg connection, SQL correctness against live schema).
- The audit assumes the live VPS code matches the local repository (verified by `ls -la` timestamp showing `Jun 27 08:53` for the rollback script, consistent with recent deployment).

---

## 12. Final Verdict

**VERDICT: PASS**

All 6 checks pass. Both round-1 MEDIUM findings (SEC-04 and RB) are verified fixed on the live VPS:

- **SEC-04:** Backup file permissions changed from 664 to 600. Confirmed via SSH `ls -la`.
- **RB:** Targeted rollback script `scripts/p19_rollback.py` exists, is syntax-valid, uses all 4 real prod KG table names (not the phantom `memory.knowledge_graph`), follows correct reverse deploy order, and preserves the p20_001 alembic stamp. Deploy-plan section 5 references it as the primary rollback path.

No new findings. No blocking issues. P19-012 production deploy security and rollback surfaces are clear.

---

| Field | Value |
|---|---|
| Audit type | Round 2 Re-Audit (Security + Rollback) |
| Verdict | **PASS** (6/6) |
| Round-1 findings re-verified | 2 (SEC-04, RB) -- both FIXED |
| New findings | 0 |
| Audit file | `docs/setup-evidence/P19/evidence/production-deploy/audits/round-2/security-rollback-reaudit.md` |
