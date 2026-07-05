# P19 Runtime Activation Audit — DB/Audit-Chain + Security/Secrets + Rollback/Idempotency

**Date:** 2026-06-27 13:10 WIB
**Auditor:** Independent (Codex)
**Scope:** DB/AUDIT-CHAIN + SECURITY/SECRETS + ROLLBACK/IDEMPOTENCY
**Evidence base:** p19-flag-enable-evidence.md, p19-service-restart-evidence.md, p19-project-runtime-proof.md, p19_audit_project_id_proof.py, durability.py

---

## 1. RA-DB-01: Alembic Stamps

| Stamp | Present | Expected |
|---|---|---|
| `p19_001_project_namespaces` | YES | YES |
| `p19_002_project_id_not_null` | YES | YES |
| `p19_003_audit_chain_version` | YES | YES |
| `p20_001_life_kernel_schema` | YES | YES |

**Total stamps:** 4 (3 P19 + 1 P20)
**PASS.** All expected stamps present, no extras.

---

## 2. RA-DB-02: Project Registry Default Project

| id | name | status |
|---|---|---|
| `00000000-0000-0000-0000-000000000001` | Default Project | active |

**Count:** 1
**PASS.** Default project exists with expected UUID and active status.

---

## 3. RA-DB-03: Audit Trail Columns (project_id + chain_version)

| Column | Type | Nullable | Default |
|---|---|---|---|
| `project_id` | uuid | YES | (none) |
| `chain_version` | smallint | NO | 1 |

**PASS.** Both columns exist. `project_id` is nullable (correct for pre-P19 rows). `chain_version` defaults to 1 with NOT NULL constraint.

---

## 4. RA-DB-04: Audit Journal project_id Gap — Honest Documentation

**Live query result:**
- Total `life_kernel.audit_journal` rows: 5332
- Rows with `project_id` in entry text: **0**
- Newest 5 rows (all post-activation at 05:48-05:51 UTC): **none** carry `project_id`

**Source code confirmation:**
- `durability.py:record()` accepts `project_id` param and stamps it into stored entry (line 116-139) — callee side is P19-ready.
- Caller (`graph.py` reflect_node → `journal_writer.write_entry`) does NOT propagate `project_id` from state to the `record()` call — caller wiring incomplete.

**Evidence file honesty check:**
- `p19-project-runtime-proof.md` section 6 ("Audit Chain — Honest Gap") explicitly states: "The `PostgresAuditJournal.record()` method accepts `project_id`... but the **caller** does not propagate project_id... So new audit journal entries (5 since activation) do NOT contain project_id."
- `p19_audit_project_id_proof.py` is a standalone proof script that queries the DB and reports `has_project_id: False`.
- No false claim of working project_id in audit journal.

**PASS.** Gap is honestly documented. Runtime proof explicitly states this is a partial P19-010 wiring gap, not an activation failure. The script and evidence file are consistent with live DB state.

---

## 5. RA-SEC-01: Secrets in Evidence Files

**Scan targets:** All files under `docs/setup-evidence/P19/evidence/runtime-activation/`
**Patterns scanned:** bot_token, discord token, password, passwd, redis pw, api_key, apikey, secret, Bearer, sk-*, ghp_*, gho_*

**Findings:**

| File | Match | Risk |
|---|---|---|
| p19-flag-enable-evidence.md L19 | `redis://guinevere_core:<pw>@localhost:6380/6` | NONE — `<pw>` is a placeholder, not an actual password |
| p19-flag-enable-evidence.md L46-47 | `redis-cli -p 6380 -a <pw> -n 6 DEL` | NONE — `<pw>` is a placeholder |
| p19-p20-non-regression.md L32 | `'password authentication failed for user "guinevere_core"'` | NONE — error message text, not a password |

**PASS.** No actual secrets found. All password references use `<pw>` placeholder or are error-message strings.

---

## 6. RA-SEC-02: .env.core Permissions

```
-rw------- 1 guinevere guinevere 799 Jun 27 11:26 /home/guinevere/code/guinevere/.env.core
```

**Mode:** 600 (owner read/write only)
**Owner:** guinevere:guinevere

**PASS.** File is properly restricted to owner-only access.

---

## 7. RA-SEC-03: HARD STOP Global (Not Project-Scoped)

**Source code scan for project-scoped HARD STOP:**

1. `src/knowledge_graph/consent/audit.py:127` — `# Global safety events (HARD_STOP, DNR) MUST pass project_id=None.`
   - This is the authoritative safety comment. The `log_consent_event` function accepts `project_id` but HARD_STOP and DNR events explicitly pass `None`.

2. `src/gmail/router.py:248` — `record_injection_detected("hard_stop", project_id=pid_str)`
   - This is a **metrics counter** (Prometheus gauge), not the safety kill-switch. It tags the metric with project context for observability. The actual HARD_STOP safety gate (`_check_hard_stop()`) is global.

3. No source in `src/` attempts to scope the HARD_STOP global key to a project. The safety key remains project-agnostic.

**PASS.** HARD STOP is global-scoped. The consent/audit layer enforces `project_id=None` for safety events. The gmail metrics counter is an observability tag, not a safety mechanism.

---

## 8. RA-SEC-04: LIFE_KERNEL_PROJECT_ID Is Safe

**Value in .env.core:** `LIFE_KERNEL_PROJECT_ID=00000000-0000-0000-0000-000000000001`

**Type:** UUID (default project identifier)
**Secret?** No. This is a deterministic, non-sensitive project identifier (the default project UUID). It is not a token, password, or API key.
**Usage:** `src/core/main.py:410` reads it via `os.environ.get("LIFE_KERNEL_PROJECT_ID") or None` and passes it to the heartbeat/cognition pipeline.

**PASS.** LIFE_KERNEL_PROJECT_ID is a safe, non-secret UUID value.

---

## 9. RA-RB-01: Flag Rollback Path

**Evidence documentation (p19-flag-enable-evidence.md section 5):**

```bash
# Rollback flag to OFF:
redis-cli -p 6380 -a <pw> -n 6 DEL feature:projects:enabled
redis-cli -p 6380 -a <pw> -n 0 DEL feature:projects:enabled
# (runtime re-reads flag each heartbeat cycle → P19 transparent, P20 byte-identical)
```

**Current flag state (verified live):**
- db6: `true`
- db0: `true`

**Rollback characteristics:**
- Instant: `DEL` command takes effect immediately
- No restart required: runtime re-reads flag each heartbeat cycle
- Effect: P19 code paths become transparent, P20 behavior byte-identical to pre-P19

**PASS.** Flag rollback is documented, instant (no restart), and the DEL command targets both db6 and db0.

---

## 10. RA-RB-02: Service Rollback Path

**Evidence documentation (p19-flag-enable-evidence.md section 5, second paragraph):**

> "For full rollback to legacy thread_id: also remove/comment `LIFE_KERNEL_PROJECT_ID` from `.env.core` + restart core."

**Additional context from p19-service-restart-evidence.md:**
- Only `guinevere-core` was restarted. All other services (discord, mcp, 9router, monitoring, obscura, whatsapp, x-poster) were untouched.
- Restart is controlled via systemd: `systemctl restart guinevere-core`
- Pre-restart state is documented (ActiveEnter, NRestarts, service health).

**Rollback sequence:**
1. Remove/comment `LIFE_KERNEL_PROJECT_ID` from `.env.core`
2. `systemctl restart guinevere-core`
3. Core reloads without project context → legacy `thread_id="heartbeat"`

**PASS.** Service rollback path is documented. Only guinevere-core needs restart.

---

## 11. RA-RB-03: Flag Set/Reset Idempotency

**Set idempotency:** `redis SET feature:projects:enabled true` — idempotent by design. Setting the same key to the same value is a no-op.

**Reset idempotency:** `redis DEL feature:projects:enabled` — idempotent by design. Deleting a non-existent key returns 0 without error.

**Service restart idempotency:** `systemctl restart guinevere-core` — idempotent. Restarting an already-running service restarts it cleanly (documented: NRestarts=0 after activation restart).

**Flag + env interaction:** Flag ON + project_id None = byte-identical P20 behavior (documented in flag-enable evidence section 3). Flag OFF + project_id set = flag OFF wins, project_id ignored. Both combinations are safe defaults.

**PASS.** Flag set/reset and service restart are all idempotent operations.

---

## 12. Audit Summary

| Check | ID | Verdict | Notes |
|---|---|---|---|
| Alembic stamps (3 P19 + p20_001) | RA-DB-01 | **PASS** | 4 stamps, all expected |
| Project registry default project | RA-DB-02 | **PASS** | Default Project, UUID 0001, active |
| audit_trail project_id + chain_version | RA-DB-03 | **PASS** | project_id nullable UUID, chain_version NOT NULL DEFAULT 1 |
| audit_journal project_id gap honest | RA-DB-04 | **PASS** | 0/5332 rows have project_id; gap honestly documented, not falsely claimed |
| No secrets in evidence files | RA-SEC-01 | **PASS** | All `<pw>` placeholders, no actual secrets |
| .env.core mode 600 | RA-SEC-02 | **PASS** | -rw------- guinevere:guinevere |
| HARD STOP global (not project-scoped) | RA-SEC-03 | **PASS** | consent/audit.py enforces project_id=None for safety events |
| LIFE_KERNEL_PROJECT_ID safe | RA-SEC-04 | **PASS** | UUID 0001, not a secret |
| Flag rollback documented + instant | RA-RB-01 | **PASS** | DEL db6+db0, no restart, documented in section 5 |
| Service rollback documented | RA-RB-02 | **PASS** | Remove env + restart core, documented |
| Flag set/reset idempotent | RA-RB-03 | **PASS** | Redis SET/DEL + systemctl restart all idempotent |

**Overall verdict: 11/11 PASS, 0 FAIL, 0 CONDITIONAL.**

---

*Auditor: Codex | Duration: ~15 min | VPS live queries via asyncpg + redis-cli*
