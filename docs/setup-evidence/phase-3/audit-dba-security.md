# DBA/Security Audit Report — Phase 3 Planner Gate

**Auditor**: DBA/Security
**Date**: 2026-06-04
**Document Reviewed**: `docs/setup-evidence/phase-3/batch-plan-phase-3.md` (641 lines)
**Cross-Referenced**:
- `docs/20-security/21-AccessControl_RBAC_ABAC_v1.0.md` (full 550 lines)
- `docs/20-security/20-SecurityPolicy_v1.0.md` (excerpts)
- `docs/20-security/22-EncryptionKeyMgmt_v1.0.md` (excerpts)
- `docs/30-data/30-DataGovernance_Classification_v1.0.md` (excerpts)
- `src/hermes/memory_bridge.py` (full 295 lines)
- `src/memory/embeddings.py` (excerpts)
- `docs/setup-evidence/hermes-migration/batch-plan-migration.md` (Phase 3 section, lines 997–1126)

## Verdict: NEEDS REVIEW

—

## DBA/Security Checklist Results

| # | Check | Verdict | Finding |
|---|---|---|---|
| 1 | PostgreSQL RBAC (P3-004) | **NEEDS REVIEW** | `hermes_memory_bridge` role not defined in governing RBAC matrix (21-AccessControl_RBAC_ABAC_v1.0.md). Granted `SELECT ON ALL TABLES IN SCHEMA memory`, which includes Critical-classified tables (`faiz_profile`, `emotional_events`) — violates ABAC-003 default-deny on Critical. `REVOKE INSERT/UPDATE/DELETE` never explicitly issued (defense-in-depth gap). `ALTER DEFAULT PRIVILEGES` references role `memory_owner` that is never created. `GRANT USAGE ON SCHEMA` missing for `memory` schema on the connection path. |
| 2 | Row-Level Security (P3-004) | **FAIL** | Research summary mentions "RLS with FORCE + SET LOCAL for PgBouncer compatibility" but P3-004 Implementation Design has **zero RLS SQL statements**. No `ALTER TABLE … FORCE ROW LEVEL SECURITY`, no `CREATE POLICY`, no `rls_data_class_ceiling` predicate. All 5 RLS policies defined in RBAC matrix §8.3 (`rls_data_class_ceiling`, `rls_task_scope`, `rls_safe_mode`, `rls_subagent_redaction`, `rls_audit_payload_min`) are absent. The only defense against Critical data exposure is a broad GRANT SELECT — there is no row-level classification filter. |
| 3 | Streaming Replication (P3-004) | **NEEDS REVIEW** | Implementation mentions "streaming replication" and "hot_standby=on" but omits critical configuration: `wal_level=replica` not specified, `max_wal_senders` value not set, no replication user/role, no replication slot management, no `ssl_mode=verify-full` for replication transport encryption. Monitoring via postgres_exporter and lag alerts (30s/300s) is correctly specified. |
| 4 | Zero-Write Enforcement (P3-007) | **NEEDS REVIEW** | Five verification methods sound in principle but incomplete: `log_statement='mod'` appears in prose (line 383) but NOT in the scaffold `Required Commands` (lines 496–503); no network-level verification (e.g., `pg_stat_statements`, tcpdump); the `grep` for INSERT/UPDATE/DELETE in plugin code will miss ORM-based dynamic SQL or multi-line string constructions; the parent plan's `audit.hermes_writes` table concept is absent. Code review and RBAC enforcement are correct. |
| 5 | Secret Handling | **NEEDS REVIEW** | 4 secrets listed but **REDIS_PASSWORD and DISCORD_TOKEN are absent** from the token/secret table — only DB_PASSWORD, 9ROUTER_API_KEY, and (implicit) OpenAI key are tracked. `GUINEVERE_PG_DSN` embeds the password in the connection string itself — if logged, the password leaks. No explicit "must not log connection strings" rule in scaffold. `$HERMES_HOME/.env` is plaintext on disk; Encryption Key Mgmt standard (§22, §2.3) requires SOPS/age encryption for secrets files. Env-var pattern is correctly applied for all listed secrets. Plugin config schema marks `pg_dsn` as `secret: True` — good. |
| 6 | SQLite FTS5 Security (P3-003) | **NEEDS REVIEW** | FTS5 is Hermes-native (`~/.hermes/state.db`), not Guinevere Python code — the plan correctly documents this. Post-recall DNR gate in plugin mitigates DNR content reaching LLM. **Missing**: file permission specification for `~/.hermes/state.db` (should be `0600` for Hermes process user); no FTS5 query injection analysis — while FTS5 MATCH syntax is inherently safer than SQL, Hermes may construct FTS5 queries from user input; no content sanitization before FTS5 indexing (DNR content exists in the index by design, filtered post-recall). |
| 7 | Network Isolation (P3-004) | **NEEDS REVIEW** | No `ssl_mode=verify-full` specified for replication connection. No mention of whether the streaming replica is Tailscale-only (security policy §1.3 requires zero public ports). `pg_hba.conf` mentioned only for Hermes connection (line 297), not for replication user. Replication transport could be plaintext on the internal network — acceptable if VPS-local, but should be documented and verified. |
| 8 | Data Exfiltration Prevention | **FAIL** | `hermes_memory_bridge` has `SELECT ON ALL TABLES IN SCHEMA memory` — includes Critical data (`emotional_events`, `faiz_profile` intimate rows, `inner_journal`). No RLS prevents Hermes from retrieving rows above its classification ceiling. Hermes is an **external framework** — not defined as a principal in the RBAC matrix (21-AccessControl_RBAC_ABAC_v1.0.md has zero matches for "hermes"). Hermes's `~/.hermes/state.db` is outside Guinevere governance: any recall data returned by the plugin can be cached, indexed, or persisted by Hermes — a data exfiltration path from Guinevere PostgreSQL → Hermes SQLite. Post-recall DNR/classification gates exist in the plugin, but they filter AFTER data has already been transferred from PostgreSQL to Hermes's memory space. |
| 9 | Connection String Security | **NEEDS REVIEW** | `GUINEVERE_PG_DSN` in `$HERMES_HOME/.env` — plaintext file on disk, contains embedded password. Encryption standard requires SOPS/age for secrets at rest. No explicit scaffold rule against logging connection strings. Redis connection string security not mentioned. Memory bridge code (`memory_bridge.py` lines 142–149, 244–249) correctly logs only metadata (query_length, results_count, content_length) — good existing pattern. |
| 10 | Rollback Data Safety | **PASS** | All 7 rollback procedures are reversible and non-destructive: P3-001 reverts plugin files, P3-002/P3-003 disable features via config, P3-004 drops role + removes replication config (no data deletion), P3-006 reverts features, full rollback restores `skip_memory=True`. No scenario causes PostgreSQL data loss or corruption. Minor note: no verification step to confirm PostgreSQL primary operates correctly after replica removal (replication slot cleanup). |

—

## Secret Handling Assessment

| Secret | Storage Method | Exposure Risk | Status |
|---|---|---|---|
| `HERMES_PG_PASSWORD` | VPS env / 1Password | Low — used only at role creation time (SQL `'${HERMES_PG_PASSWORD}'`). Not in repo. | ✅ OK |
| `GUINEVERE_PG_DSN` | `$HERMES_HOME/.env` (plaintext) | **Medium** — DSN contains embedded password. Plaintext on disk. If logged in error messages or stack traces, password leaks. SOPS/age not applied. | ⚠️ Add SOPS encryption; add "must not log DSN" to scaffold |
| `9ROUTER_API_KEY` | 9Router dashboard | Low — no code change, no repo exposure. | ✅ OK |
| `OPENAI_API_KEY` (fallback) | `$HERMES_HOME/.env` | Low — fallback path only, not primary. | ✅ OK |
| **`REDIS_PASSWORD`** | **NOT LISTED** | **Unknown** — Redis DB0-DB5 is in use but password not tracked in secrets table. | ❌ Add to secrets table |
| **`DISCORD_TOKEN`** | **NOT LISTED** | **Unknown** — Discord bot is primary interface but token not tracked. | ❌ Add to secrets table |

—

## Critical Security Findings

### Finding 1: Hermes Not Defined as Principal — No Data Classification Boundary
**Risk Level**: **HIGH**
**Evidence**: Planner gate §10 (Token/Secret Handling) and §8 (P3-004 Implementation Design). The RBAC matrix (`21-AccessControl_RBAC_ABAC_v1.0.md`, all 550 lines) defines 13 principals — none of them is Hermes. The `hermes_memory_bridge` role grants SELECT on ALL `memory` schema tables including Critical-classified `emotional_events`, `faiz_profile` (Restricted→Critical rows), and survey-related tables.
**Data Exfiltration Vector**: Hermes's session_search and recall results are cached in `~/.hermes/state.db` — PostgreSQL's Critical/Restricted data flows into an ungoverned SQLite file outside Guinevere's control.
**Recommended Fix**:
1. Define Hermes as a new principal in the RBAC matrix with classification ceiling of `Confidential` by default, `Restricted` with task justification.
2. Create RLS policies on memory tables that filter by classification ceiling for `hermes_memory_bridge` role.
3. Add a data minimization rule: plugin must not return raw Critical content to Hermes — only redacted/summarized versions.
4. Document Hermes's `state.db` as a governed data store and add it to the classification scope.

### Finding 2: Missing RLS Implementation — Row-Level Access Unenforced
**Risk Level**: **HIGH**
**Evidence**: Research summary line 54: "RLS with FORCE + SET LOCAL for PgBouncer." P3-004 Implementation Design lines 290–327: zero RLS SQL. Scaffold lines 466–473: no RLS check in required commands or hard rejection criteria.
**Impact**: Without RLS, the `hermes_memory_bridge` role can SELECT any row in any memory table — including intimate profile rows, emotional events, inner journal entries, and safe-word logs. The GRANT SELECT on ALL TABLES gives table-level access with no row filtering.
**Recommended Fix**:
1. Add explicit RLS creation to P3-004 SQL migration:
   ```sql
   ALTER TABLE memory.episodic_memory FORCE ROW LEVEL SECURITY;
   CREATE POLICY hermes_classification_ceiling ON memory.episodic_memory
     FOR SELECT TO hermes_memory_bridge
     USING (classification_level <= 'Restricted');
   ```
2. Add `FORCE ROW LEVEL SECURITY` and classification-based policies to all memory schema tables.
3. Add RLS policy verification to P3-004 scaffold Required Commands.

### Finding 3: Broad SELECT on Critical Tables — Classification Escape
**Risk Level**: **HIGH**
**Evidence**: Planner gate lines 308–312. `GRANT SELECT ON ALL TABLES IN SCHEMA memory TO hermes_memory_bridge` covers tables with Critical classification per RBAC matrix §8.2: `memory.faiz_profile` (Restricted→Critical by row), `memory.emotional_events` (Critical), `persona.inner_journal` (Critical — though different schema, RLS not specified).
**Impact**: ABAC-003 in the governing policy states "Sub-agent requests Critical data → Deny by default." While Hermes is not technically a sub-agent, the same principle should apply — external frameworks should not have blanket SELECT on Critical data.
**Recommended Fix**:
1. Narrow the GRANT to specific non-Critical tables or views.
2. Create purpose-scoped views for Hermes (e.g., `memory.hermes_recall_view` that excludes Critical columns and applies classification ceiling).
3. If Critical data is legitimately needed (e.g., for safety support), require explicit task justification and audit logging — mirroring ABAC-004.

### Finding 4: Streaming Replication Security Underspecified
**Risk Level**: **MEDIUM**
**Evidence**: P3-004 lines 294–301. Implementation steps list "Set up streaming replication" and "Configure hot_standby = on" but omit `wal_level`, `max_wal_senders`, replication user, `ssl_mode`, and network isolation.
**Impact**: Replication may use unencrypted transport (plaintext WAL streaming), the replica may accept connections from non-Tailscale sources, and replication slots may accumulate without monitoring.
**Recommended Fix**:
1. Add explicit configuration parameters to P3-004 implementation: `wal_level=replica`, `max_wal_senders=5`, `ssl=on`, `ssl_mode=verify-full`.
2. Add replication user creation with `REPLICATION` privilege.
3. Add `pg_hba.conf` entry for replication user restricted to Tailscale/VPS-local IP.
4. Add replication slot cleanup to rollback procedure.

### Finding 5: Incomplete Secrets Inventory
**Risk Level**: **MEDIUM**
**Evidence**: Planner gate §10 token/secret table (lines 518–525) lists 4 secrets. Two critical secrets — `REDIS_PASSWORD` and `DISCORD_TOKEN` — are absent despite the system actively using Redis (DB0–DB5) and Discord (primary interface).
**Impact**: These secrets have no documented storage location, access pattern, or rotation plan within the Phase 3 scope. If they are in `$HERMES_HOME/.env` alongside `GUINEVERE_PG_DSN`, they share the same plaintext-on-disk risk.
**Recommended Fix**:
1. Add `REDIS_PASSWORD` and `DISCORD_TOKEN` to the secrets table with storage method and access pattern.
2. Verify both are stored with `env_var` pattern, not hardcoded.
3. Confirm `$HERMES_HOME/.env` is SOPS-encrypted at rest per Encryption Key Mgmt standard.

### Finding 6: DSN Password-in-Connection-String Exposure
**Risk Level**: **MEDIUM**
**Evidence**: Planner gate line 522: `GUINEVERE_PG_DSN` stored in `$HERMES_HOME/.env`. Plugin config schema (line 208): `"secret": True, "env_var": "GUINEVERE_PG_DSN"`. There is no explicit rule against logging the DSN.
**Impact**: PostgreSQL connection strings embed the password: `postgresql://hermes_memory_bridge:PASSWORD@host:port/db`. If this string appears in any log, stack trace, error message, or debug output, the password is exposed. The existing codebase (`memory_bridge.py`) correctly avoids logging connection details — but the new plugin must maintain this discipline.
**Recommended Fix**:
1. Add to P3-001 scaffold Forbidden Patterns: "logging or printing of pg_dsn, connection string, or any env var marked secret"
2. Split the DSN config into separate `pg_host`, `pg_port`, `pg_user`, `pg_password` env vars — never log the full DSN.
3. Add "DSN must not appear in any log output" to P3-001 Hard Rejection Criteria.

—

## Data Flow Security Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          GUINEVERE VPS                                  │
│                                                                         │
│  ┌──────────────────────┐         ┌──────────────────────────────────┐  │
│  │  PostgreSQL Primary  │◄────────│     hermes_memory_bridge role    │  │
│  │                      │  SELECT │     GRANT SELECT ON ALL TABLES   │  │
│  │  memory schema:      │  only   │     IN SCHEMA memory             │  │
│  │  ├─ episodic_memory  │         │     ⚠ NO RLS → all rows visible  │  │
│  │  ├─ faiz_profile     │         │     ⚠ Critical tables accessible │  │
│  │  ├─ emotional_events │         └──────────────┬───────────────────┘  │
│  │  ├─ inner_journal    │                        │                      │
│  │  └─ ...              │         ┌──────────────▼───────────────────┐  │
│  └──────────────────────┘         │  Guinevere Memory Plugin         │  │
│                                   │  (plugins/memory/guinevere-      │  │
│  ┌──────────────────────┐         │   memory/__init__.py)            │  │
│  │  Streaming Replica   │         │                                  │  │
│  │  (Hot Standby)       │         │  prefetch() → read_pipeline      │  │
│  │  ⚠ ssl_mode=?       │         │  sync_turn() → write_pipeline    │  │
│  │  ⚠ network iso=?    │         │  Post-recall DNR gate ✅         │  │
│  └──────────────────────┘         │  Classification ceiling ✅       │  │
│                                   └──────────────┬───────────────────┘  │
│                                                  │                      │
│                                   ┌──────────────▼───────────────────┐  │
│                                   │  Hermes Agent Framework          │  │
│                                   │  (NousResearch/hermes-agent)     │  │
│                                   │                                  │  │
│                                   │  session_search() → FTS5         │  │
│                                   │  ~/.hermes/state.db              │  │
│                                   │  ⚠ UNGOVERNED data store         │  │
│                                   │  ⚠ Caches recall results         │  │
│                                   │  ⚠ No classification enforcement │  │
│                                   │  ⚠ No DNR enforcement            │  │
│                                   └──────────────┬───────────────────┘  │
│                                                  │                      │
│                                   ┌──────────────▼───────────────────┐  │
│                                   │  LLM Context Injection           │  │
│                                   │  (GPT-5.5 / DeepSeek via         │  │
│                                   │   9Router)                       │  │
│                                   │  ⚠ Memory content sent to       │  │
│                                   │     external LLM provider        │  │
│                                   └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

LEGEND:
  ✅  = Security gate present
  ⚠  = Security gap identified
  ──► = Data flow direction

KEY GAPS:
  1. No RLS between PostgreSQL and plugin → Critical rows reach the plugin
  2. No classification enforcement on hermes_memory_bridge → all tables accessible
  3. Hermes state.db is ungoverned → recall data persists outside Guinevere control
  4. Replication transport security unspecified
  5. LLM provider receives memory content → external data exposure (by design, managed by existing DNR/classification gates in read_pipeline)
```

—

## Summary

The Phase 3 planner gate defines a directionally correct architecture — Hermes memory plugin with post-recall DNR/classification gates, streaming replication for PostgreSQL mirroring, and zero-write enforcement — but has **two HIGH-severity security gaps** that must be resolved before execution. The `hermes_memory_bridge` database role grants `SELECT ON ALL TABLES IN SCHEMA memory` with no row-level security, giving an external framework (Hermes) blanket access to Critical-classified data including emotional events, intimate profile rows, and inner journal entries. RLS policies mentioned in research are entirely absent from the implementation design, creating a classification enforcement gap at the database boundary. Additionally, data retrieved by the plugin flows into Hermes's ungoverned SQLite state database — a data exfiltration path from Guinevere's governed PostgreSQL to an external store with no classification, DNR, or retention controls. Five medium-severity findings cover incomplete secrets inventory (missing REDIS_PASSWORD, DISCORD_TOKEN), plaintext DSN storage, underspecified replication security, and incomplete zero-write verification. All findings have clear, implementable remediations within a single planning revision. **Recommendation: address all HIGH findings (RLS implementation + principal definition) before Wave 1 execution; MEDIUM findings can be resolved before Wave 3 (P3-006/P3-007) when they become blocking.**

—
**End of DBA/Security Audit Report**