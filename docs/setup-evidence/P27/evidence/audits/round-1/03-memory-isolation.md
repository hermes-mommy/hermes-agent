# P27 Memory Isolation Audit — Round 1

| Field | Value |
|---|---|
| Audit target | P27 Hermes Society Foundation plan — Memory Architecture (3-scope) |
| Plan section reviewed | `p27-hermes-society-foundation-plan.md` §6 (L1142–1643) |
| Companion doc | `p28-dual-autonomous-hermes-blueprint.md` §7 (L2338–2391) |
| Research grounding | `p27-private-shared-memory-research.md` (first 200 lines) |
| Auditor | Guinevere (parent) |
| Date | 2026-06-28 |
| Audit scope | Memory isolation correctness — separate namespaces, RLS enforcement, no cross-agent private memory access |

---

## Verdict: **NEEDS REVIEW**

The 3-scope memory architecture is **fundamentally sound** and aligns with the 2026 PostgreSQL multi-tenant consensus (research F3, F8, F9), but **two schema-level gaps** exist around provenance columns. Plan is acceptably close to PASS once the two items below are reconciled. No safety or privacy boundary is breached in the current draft, but the gaps MUST be addressed before P28 implementation begins.

---

## Checklist — Item-by-Item Findings

### ✅ PASS — 3 distinct scopes

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Three scopes: private_agents, shared_world, relationship_pairs | **PASS** | Plan §6.1 L1148–1152 explicitly defines all three scopes with table names; P28 §7.1 L2342–2349 confirms deployment. |

### ✅ PASS — Per-scope access control

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 2a | `private` = agent owner only | **PASS** | §6.1 L1150: "Agent owner ONLY (default). Faiz on audit + explicit consent-gated exception." |
| 2b | `shared` = all agents (read), any agent (write) | **PASS** | §6.1 L1151: "All Society agents read; any agent write (with audit); Faiz for governance." |
| 2c | `relationship_private` = pair members only | **PASS** | §6.1 L1152: "Pair members ONLY (e.g., Guinevere + Pharsa). Faiz on audit." |

### ✅ PASS — RLS FORCE specified on every memory table

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 3a | `memory.private_agents` FORCE RLS | **PASS** | §6.2.1 L1191–1193: `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY`. |
| 3b | `memory.relationship_pairs` FORCE RLS | **PASS** | §6.2.2 L1251–1252: both statements. |
| 3c | `memory.shared_world` FORCE RLS | **PASS** | §6.2.3 L1306–1307: both statements. |
| 3d | `memory.intimacy_bridge_pending` FORCE RLS | **PASS** | §6.2.4 L1342–1343: both statements. |

### ✅ PASS — Non-owner application role

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 4 | Dedicated non-owner role `agent_memory_app` | **PASS** | §6.2.5 L1358: `CREATE ROLE agent_memory_app LOGIN PASSWORD '…'`; explicit comment L1357 names the PCMI-consensus trigger ("FORCES bypass-block"). Section also grants SELECT/INSERT/UPDATE/DELETE — NOT table ownership — confirming non-owner posture. |
| 4a | Role is not superuser | **PASS (implicit)** | `CREATE ROLE … LOGIN PASSWORD …` defaults to NOSUPERUSER. Plan does not promote to superuser. |

### ⚠️ NEEDS REVIEW — agent_id NOT NULL on all memory tables

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 5a | `private_agents.agent_id` NOT NULL | **PASS** | §6.2.1 L1170: `agent_id TEXT NOT NULL CHECK (agent_id IN ('guinevere','pharsa'))`. |
| 5b | `relationship_pairs` identity NOT NULL | **PASS (substitute)** | §6.2.2 L1213–1220: `pair_id UUID NOT NULL` + `pair_member_a/b` both NOT NULL with CHECK constraint enforcing lexicographic ordering and unique pair. Pair identity is the substitute for per-agent `agent_id`. |
| 5c | `shared_world.agent_id` NOT NULL | **FINDING F-1: column absent** | §6.2.3 L1277–1308: no `agent_id` column. Plan uses `created_by_agent TEXT NOT NULL` (L1296) as provenance — different column with different semantics. By design (shared world is owner-less), but inconsistent with checklist phrasing "agent_id NOT NULL on all memory tables." |
| 5d | `intimacy_bridge_pending.agent_id` NOT NULL | **PASS** | §6.2.4 L1331: `agent_id TEXT NOT NULL …`. This names the proposer. |
| 5e | `kg_edges` agent_id | **PASS (substitute)** | §6.2.6 L1388–1390: index `kg_edges_private_agent_idx` references `kg_edges.agent_id` — column must already exist from ADR-050. ADR-050 ownership not validated in this audit; see F-4 below. |

**Finding F-1.** Plan §6.2.3 does not declare `agent_id` on `memory.shared_world`. The audit checklist explicitly requires `agent_id NOT NULL` on every memory table. This is a **legitimate design choice** (shared world has no owner) but should be acknowledged: either (a) document the deliberate omission in §6.2.3 with rationale, or (b) add `agent_id TEXT` as NULLABLE for completeness and add scope-aware RLS policy that filters NULL `agent_id` rows only into `scope='shared'`.

### ✅ PASS — pair_id UUID NULL where scope allows non-pair rows

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 6a | `relationship_pairs.pair_id` | PASS | §6.2.2 L1213: `pair_id UUID NOT NULL` — correct semantics (every row in this table IS a pair row). |
| 6b | `kg_edges.pair_id` UUID NULL | **PASS** | §6.2.6 L1383: `ALTER TABLE memory.kg_edges ADD COLUMN pair_id UUID NULL` — explicit NULLABLE, only populated for `scope='relationship_private'` edges. |
| 6c | `intimacy_bridge_pending.intended_pair_id` NULL | **PASS (substitute)** | §6.2.4 L1333: `intended_pair_id UUID` — nullable because `intended_scope='shared'` proposals don't carry a pair. |

### ✅ PASS — scope NOT NULL CHECK constraint

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 7a | `private_agents.scope` NOT NULL CHECK | **PASS** | §6.2.1 L1171: `scope TEXT NOT NULL DEFAULT 'private' CHECK (scope = 'private')`. |
| 7b | `relationship_pairs.scope` NOT NULL CHECK | **PASS** | §6.2.2 L1221: `scope TEXT NOT NULL DEFAULT 'relationship_private' CHECK (scope = 'relationship_private')`. |
| 7c | `shared_world.scope` NOT NULL CHECK | **PASS** | §6.2.3 L1279: `scope TEXT NOT NULL DEFAULT 'shared' CHECK (scope = 'shared')`. |
| 7d | `kg_entities.scope` NOT NULL CHECK (3 values) | **PASS** | §6.2.6 L1376–1377: `scope TEXT NOT NULL DEFAULT 'shared' CHECK (scope IN ('private','shared','relationship_private'))`. |
| 7e | `kg_edges.scope` NOT NULL CHECK (3 values) | **PASS** | §6.2.6 L1381–1382: identical pattern. |

### ⚠️ NEEDS REVIEW — created_by_agent NOT NULL for provenance

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 8a | `private_agents.created_by_agent` NOT NULL | **PASS** | §6.2.1 L1184: `created_by_agent TEXT NOT NULL CHECK (created_by_agent IN ('guinevere','pharsa'))`. |
| 8b | `relationship_pairs.created_by_agent` NOT NULL | **PASS** | §6.2.2 L1241: `created_by_agent TEXT NOT NULL` (no CHECK; permitted because promotion chain may add new agents). |
| 8c | `shared_world.created_by_agent` NOT NULL | **PASS** | §6.2.3 L1296: `created_by_agent TEXT NOT NULL`. |
| 8d | `kg_edges.created_by_agent` NOT NULL | **PASS** | §6.2.6 L1384–1385: `ADD COLUMN created_by_agent TEXT NOT NULL CHECK (created_by_agent IN ('guinevere','pharsa'))`. |
| 8e | `kg_entities.created_by_agent` NOT NULL | **FINDING F-2: column added as NULLABLE** | §6.2.6 L1378–1379: `ADD COLUMN created_by_agent TEXT CHECK (created_by_agent IN ('guinevere','pharsa'))` — **missing `NOT NULL`**. Inconsistent with kg_edges and other memory tables. Existing rows from ADR-050 may not have provenance. |

**Finding F-2.** §6.2.6 L1378 declares `memory.kg_entities.created_by_agent` as TEXT without `NOT NULL`. This is a provenance hole: a `kg_entities` row in `scope='private'` could lack an author. Mitigation path: (a) add NOT NULL with `UPDATE memory.kg_entities SET created_by_agent = 'system' WHERE created_by_agent IS NULL` as a backfill before ALTER, or (b) document why only edges carry NOT NULL provenance (e.g., entities pre-date the Society). Worth flagging to Faiz — Silent provenance gaps create audit-trail blind spots.

### ✅ PASS — Ebbinghaus decay fields

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 9a | `importance_score REAL` with CHECK [0,1] | **PASS** | §6.2.1 L1173, 1225, 1283: all three tables declare `importance_score REAL NOT NULL` with `CHECK (importance_score BETWEEN 0 AND 1)` (private table) or default. |
| 9b | `last_accessed_at TIMESTAMPTZ` | **PASS** | §6.2.1 L1178, 1230, 1288: `last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` on all three tables. |
| 9c | `retrievability` STORED GENERATED | **PASS** | §6.2.1 L1174–1177, 1226–1229, 1284–1287: identical Ebbinghaus formula `exp(-Δt/stability_days) × importance_score` STORED on all three tables. |
| 9d | Sweep spec | **PASS** | §6.3 L1393–1428: complete decay sweep with formula (§6.3 L1397–1408), nightly cron (L1410–1414), at-access reinforcement (L1418), bilateral review sweep (L1420–1422), evergreen semantics (L1424–1427). |

### ✅ PASS — Intimacy bridge staging table

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 10a | `memory.intimacy_bridge_pending` declared | **PASS** | §6.2.4 L1326–1352: full table spec with RLS, FORCE RLS, and pair-review policy. |
| 10b | Bilateral consent flow documented | **PASS** | §6.5 L1440–1468: full mechanism — propose → review → approve → atomic promotion — with bilateral atomicity and trust gradient gating. |
| 10c | Edge case — P28 implementation status | **PASS (with caveat)** | P28 §7.3 L2361: "P28 ships stub only. No rows inserted during P28 acceptance. Full bilateral consent flow = P30." The staging table is created but enforcement deferred. This is **acceptable** because P27 plan owns the full design and P28 owns minimum-viable implementation; the staging table is materially scoped via RLS already. **Caveat C-1** below. |

### ✅ PASS — Last-write-wins with audit chain

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 11a | New row wins via `supersedes_id` | **PASS** | §6.4 L1433: "Every write creates a new row with `supersedes_id=<old_row_id>`." |
| 11b | Old row preserved (`superseded_by_id` chain) | **PASS** | §6.4 L1434–1435; explicit columns in §6.2.3 L1292–1293. |
| 11c | Curator sweep consolidates deep chains | **PASS** | §6.4 L1436–1437: nightly curator sweep, chains >5 levels → single latest-row + archived chain in `memory.shared_world_history`. |
| 11d | Voting explicitly rejected | **PASS** | §6.4 L1438: "Why last-write-wins and NOT consensus voting: Voting consensus … is overkill … AutoGen research supports versioning + provenance." P28 §7.6 L2373–2380 reaffirms. |

### ✅ PASS — No path for cross-private-memory read

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 12a | RLS USING clause restricts to owner | **PASS** | §6.2.1 L1199–1205: policy `agent_owns_private USING (agent_id = current_setting('app.current_agent_id') OR 'faiz' = …)`. |
| 12b | FORCE blocks owner bypass | **PASS** | §6.2.1 L1191–1193, §6.13 L1615: "No FORCE-less RLS (allows owner bypass — PCMI consensus warns)." |
| 12c | Non-owner role prevents QUIET bypass | **PASS** | §6.2.5 L1358–1365: `agent_memory_app` is granted CRUD only; it does not own any table. Combined with FORCE RLS, both bypass paths closed. |
| 12d | Application sets per-session agent_id | **PASS** | §6.2.5 L1367–1369: `set_config('app.current_agent_id', …)` per session or transaction. P28 §7.4 L2365: transaction-scoped pattern `set_config(..., true)`. |
| 12e | Defensive WHERE-clause discipline | **PASS** | §6.13 L1620–1621: "No cross-scope reads via missed WHERE clause (RLS blocks; defense-in-depth). No `select *` writes without scope filter (always specify scope)." |
| 12f | Faiz governance exception | **PASS (intentional)** | Plan grants Faiz governance access via RLS policy. This is **explicitly documented** (§6.1 L1150, L1152) and aligns with operator-level audit rights. No silent bypass. |

### ✅ PASS — ADR-050 kg_* schema extension

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 13a | Extension explicitly named | **PASS** | §6.1 L1158: "memory.kg_entities, memory.kg_edges — extended with scope, pair_id, created_by_agent (ADR-050 family)." |
| 13b | ALTER TABLE statements provided | **PASS** | §6.2.6 L1372–1391: full ALTER TABLE block for `kg_entities` (scope, created_by_agent) and `kg_edges` (scope, pair_id, created_by_agent, derivation_chain). |
| 13c | Composite indexes on extensions | **PASS** | §6.2.6 L1388–1390: `kg_edges_scope_pair_idx`, `kg_edges_private_agent_idx`. |

### ✅ PASS — PostgreSQL schemas / namespaces

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 14a | All memory tables in `memory.*` schema | **PASS** | §6.2.1–6.2.4: every table qualifier uses `memory.<table_name>`. Centralizes namespace, enables `GRANT USAGE ON SCHEMA memory` (L1359). |
| 14b | Schema-level GRANT | **PASS** | §6.2.5 L1359: `GRANT USAGE ON SCHEMA memory TO agent_memory_app` — single grant covers all current and future `memory.*` tables within the role's other grants. |
| 14c | Per-agent SCHEMA not used; RLS is sole separation mechanism | **PASS (matches research consensus)** | Research L113–115 (ITNotes 2026) and L115 (Toolchew 2026) show schema-per-tenant does NOT scale beyond ~1,000 tenants / RLS with FORCE is the chosen pattern. P27 follows that consensus. Plan does not create per-agent schemas like `memory_private_guinevere`, which is consistent and correct. |

### ✅ PASS — Research reconciliation

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 15a | Plan adopts F3 (RLS FORCE + non-owner role) | **PASS** | Research L33: F3 consensus; plan §6.2.1–6.2.5 implement. |
| 15b | Plan adopts F5 (ADR-050 reuse + extension) | **PASS** | Research L35; plan §6.2.6 extends ADR-050 kg_* tables. |
| 15c | Plan adopts F6 (P19 scope taxonomy extension) | **PASS (mentioned)** | Plan §6.9 L1523–1530: "`project_id` (P19 namespace) + `scope` (P27) — orthogonal." |
| 15d | Plan adopts F8 (Ebbinghaus decay) | **PASS** | Research L38; plan §6.3 with formula + sweep spec. |
| 15e | Plan adopts F9 (Mem0 tagging — agent_id/pair_id/scope/created_by_agent) | **PASS with caveats F-1, F-2** | Research L39: F9; plan implements most of F9 but missing NOT NULL on shared_world (no agent_id) and kg_entities.created_by_agent. |

---

## Findings Summary

### F-1 — `memory.shared_world.agent_id` column absent (MINOR / ACCEPTABLE)
- **Location:** §6.2.3 L1277–1308 (`memory.shared_world` schema).
- **Issue:** Plan does not declare `agent_id` column. Audit checklist requires `agent_id NOT NULL on all memory tables`. Shared world has no per-agent owner by design; `created_by_agent` provides provenance.
- **Severity:** Minor. No data-leakage risk; `FORCE RLS` + `agent_memory_app` non-owner role still enforce isolation. WHAT IT HIDES: cross-agent read of provenance attribution requires joining `created_by_agent`, which is acceptable.
- **Resolution path:** Either (a) document explicit rationale in §6.2.3 header: "`memory.shared_world` is owner-less by design; provenance via `created_by_agent NOT NULL`;", or (b) add `agent_id TEXT NULL` with RLS CHECK constraint `agent_id IS NULL OR scope = 'shared'` to satisfy literal checklist phrasing.

### F-2 — `kg_entities.created_by_agent` added NULLABLE (NEEDS FIX)
- **Location:** §6.2.6 L1378–1379.
- **Issue:** `ADD COLUMN created_by_agent TEXT CHECK (created_by_agent IN ('guinevere','pharsa'))` — missing `NOT NULL`. ADR-050 pre-existing rows would have NULL provenance.
- **Severity:** Moderate. Provenance gaps in knowledge graph create audit-trail blind spots; a private-scope KG entity could lack author attribution.
- **Resolution path:** Add backfill step before ALTER:
  ```sql
  UPDATE memory.kg_entities SET created_by_agent = 'system' WHERE created_by_agent IS NULL;
  ALTER TABLE memory.kg_entities ALTER COLUMN created_by_agent SET NOT NULL;
  ```
  OR explicitly document why ADR-050 entities may be author-less (e.g., curator-imported during P16 deployment). Either choice must appear in §6.2.6.

### F-3 — Implicit `kg_edges.agent_id` dependency (LOW / DOCUMENT)
- **Location:** §6.2.6 L1389–1390: `CREATE INDEX kg_edges_private_agent_idx ON memory.kg_edges (agent_id) WHERE scope = 'private';`
- **Issue:** Index references `agent_id` column on `kg_edges`, but §6.2.6 ALTER TABLE does NOT add `agent_id` — only `scope, created_by_agent, pair_id, derivation_chain`. Either (a) `kg_edges.agent_id` exists from ADR-050 and is implicitly relied upon, or (b) the index will fail at migration time.
- **Severity:** Low (likely addressed by ADR-050 inheritance) but deserves explicit confirmation.
- **Resolution path:** Add a one-line note in §6.2.6 stating "`kg_edges.agent_id` is inherited from ADR-050; not re-declared here."

### F-4 — P28 `intimacy_bridge_pending` is STUB ONLY (CAVEAT, NOT FAIL)
- **Location:** P28 §7.3 L2361.
- **Issue:** Plan §6.5 designs full bilateral consent flow; P28 ships only the staging table schema. No rows inserted during P28 acceptance window.
- **Severity:** Caveat, not failure. P27 plan owns full design; P28 owns minimum-viable implementation scope. The staging table is created with FORCE RLS, so even empty rows enforce isolation.
- **Action:** Confirm in P30 implementation plan that bilateral consent flow + first end-to-end promotion is a P30 deliverable, not silently dropped.

---

## Recommendations

1. **Resolve F-1** before P28 implementation begins. Either document the deliberate omission of `shared_world.agent_id` in §6.2.3, or add the column NULLABLE with a CHECK constraint. Recommended: document — shared world genuinely has no per-agent owner.

2. **Resolve F-2** before P28 implementation begins. Add explicit NOT NULL with a documented backfill, OR add explicit ADR-050-inheritance justification in §6.2.6. Recommended: NOT NULL with a migration step.

3. **Resolve F-3** by adding a one-line note in §6.2.6 confirming `kg_edges.agent_id` is inherited from ADR-050.

4. **Confirm P30 scope** for `intimacy_bridge_pending` end-to-end via P30 plan addendum or P28 evidence doc — do not let the stub silently linger across phases.

5. **Post-fix re-audit:** Once F-1, F-2, F-3 are addressed in the plan markdown, re-run this checklist. Likely verdict flips to PASS.

---

## Boundary Compliance

| Boundary | Status |
|---|---|
| Persona drift | PASS — no persona code in plan; memory schema only. |
| Consent violation | PASS — RLS + bilateral consent atomicity honored. |
| Surveillance overreach | N/A — memory section does not include surveillance scope. |
| Y6 escalation | N/A — not persona-related. |
| HARD STOP bypass | N/A — HARD STOP is life-loop, not memory (see P28 §9.1). |
| Distress protocol suppression | N/A. |
| Secret/intimate data exposure | PASS — `consent_token TEXT NOT NULL` on every memory table (L1187, 1244, 1303). `content TEXT` for relationships (L1232) is protected by FORCE RLS + bilateral consent. |
| Intimate plaintext log exposure | N/A — intimate rows in `relationship_pairs` (L1232); access gated by FORCE RLS pair-policy (L1258–1271). |

---

## Acceptance Criteria Mapping

| DoD Item | Result |
|---|---|
| Memory isolation correctly specified | PASS on isolation mechanics; NEEDS REVIEW on audit completeness (F-1, F-2). |
| Separate namespaces | PASS — `memory.*` schema with governance GRANT. |
| RLS-FORCE enforcement | PASS — all four memory tables. |
| No cross-agent private memory access | PASS — verified via per-scope policy audit. |
| Bilateral intimacy flow design | PASS (P27 full design); CAVEAT (P28 stub, P30 owner). |
| Last-write-wins with audit chain | PASS — schema, sweep, history table. |
| ADR-050 extension | PASS — explicit ALTER + index. |
| Ebbinghaus decay | PASS — full formula + sweep + reinforcement. |

---

## Footer

| Version | Date | Author | Notes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere (parent audit) | Round-1 memory isolation review against P27 plan §6, P28 §7, research F1–F9. Four findings: two NEEDS REVIEW (F-1, F-2), one DOCUMENT (F-3), one CAVEAT (F-4). |

> **Auditor recommendation:** Re-delegate to P28 implementer with F-1/F-2 resolutions; do not block P27 plan acceptance but DO require P28 evidence to include explicit F-1/F-2 disposition recorded in `docs/setup-evidence/P28/evidence/`.
