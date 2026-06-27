# P22 Production Activation — Audit Round 2 / DB-Migration Dimension (FINAL GATE)

**Auditor:** Independent Auditor (db-migration dimension, round 2)
**Date:** 2026-06-28
**VPS verified live:** `faiz-prod-01` via `ssh guinevere-vps` (Tailscale 100.94.104.22)
**Scope:** Independently re-verify live PostgreSQL state on VPS; close round-1
H2 (DB not independently re-verified by the round-1 sub-agent, which had no
SSH); confirm that the round-1 fix-log fixes hold; surface any new regressions
or live-state concerns that round-1 missed because it was sandbox-bound.
**Mode:** READ-ONLY on code & docs. Live-DB read queries via asyncpg as the
production role `guinevere_core`. Two INSERTs issued as a WORM negative test
(INSERT is permitted; UPDATE/DELETE — the test targets — were correctly
DENIED with InsufficientPrivilegeError). No secrets printed. No code modified.
No services restarted. No destructive ops.

---

## 0. Verdict

**VERDICT: PASS** *(with one non-blocking MEDIUM observation; see §3)*

The hard-rejection criteria for the db-migration dimension are independently
satisfied against the live VPS:

| Hard-rejection criterion | Status |
|---|---|
| Migration `p22_001_integration_schema` applied | **PASS** — `ops.alembic_version` contains exactly `p22_001_integration_schema` on live DB |
| Schema `p22` created | **PASS** — present in `pg_namespace` |
| `p22.integration_registry` exists | **PASS** — `pg_tables` lookup succeeds |
| `p22.secret_ref_metadata` exists | **PASS** — `pg_tables` lookup succeeds |
| `audit.integration_api_log` exists | **PASS** — `pg_tables` lookup succeeds |
| `p22.integration_registry` seeded with 12 rows | **PASS** — `count(*) = 12` (correct 12; `filesystem` adapter is correctly omitted per migration comment, matching F-DBM-09 INFO) |
| WORM enforced: `guinevere_core` cannot UPDATE or DELETE | **PASS** — `has_table_privilege(UPDATE)=False`, `has_table_privilege(DELETE)=False` AND live negative test (insert-then-UPDATE attempt) returned `InsufficientPrivilegeError` AND live negative test (insert-then-DELETE attempt) returned `InsufficientPrivilegeError` |
| `project_id` / `project_scope` columns present on the audit log | **PASS** — both columns confirmed in `information_schema.columns` (`project_id uuid NULL`, `project_scope text NULL`) |
| No secrets printed | **PASS** — only URL shape (`postgresql+asyncpg://REDACTED@localhost:5433/guinevere`), role names (`guinevere_core`), column names, row counts, and boolean privilege values |

The single MEDIUM observation (N-DBM-01) is a WORM-completeness nuance
discovered by inspecting `pg_class.relacl`; it does **not** violate any of the
hard-rejection criteria the brief enumerates (which require INSERT, SELECT
permitted and UPDATE, DELETE denied; that contract is fully met). It is
documented below as a real-world gap producers should consider before treating
audit log as "immutable at the storage role".

---

## 1. Round-1 Findings Resolution

The round-1 db-migration dimension (`docs/setup-evidence/P22/production-activation/audits/round-1/audit-db-migration.md`)
returned **NEEDS_REVIEW (5 PASS, 3 NEEDS_REVIEW, 0 FAIL)** across the audit fleet
and specifically for db-migration emitted 9 findings. The round-2 re-verifies
each:

| R1 ID | Severity | Title | R2 Status | Evidence |
|---|---|---|---|---|
| **F-DBM-01** | HIGH | Live DB not independently verified by r1 db-auditor | **RESOLVED** | This audit used `ssh guinevere-vps` and ran the queries documented in §2; all post-conditions confirmed live, including the negative WORM test (not just `has_table_privilege` checks). The H2 fix-log line is therefore GENUINELY RESOLVED. |
| **F-DBM-02** | MEDIUM | Migration applied via "direct DDL + stamp" (bypassing normal `alembic upgrade`) | **PARTIALLY RESOLVED** | The shape of the apply is unchanged (the live DB now has the migration's table & seed, but `alembic upgrade` was not used). However: this is a documented workflow choice that the operator made because of the multi-head state, and the live state is consistent with what the doc claims. This is now an INFO-only observation: any **future** operator-facing `alembic upgrade head` run will succeed only if the multi-head condition is resolved at that time. The r2 evidence shows `alembic_version` is single-row (`p22_001_integration_schema`) so the stamp-collapse worked. Recommendation: solve via a fresh linear chain in a future migration rather than relying on the stamp-by-idempotent-DDL pattern again. |
| **F-DBM-03** | MEDIUM | `p22-migration-application.md` "alembic_version rows = 1" framing was inconsistent with the multi-head state | **RESOLVED** | Live `SELECT count(*) FROM ops.alembic_version = 1`; live `SELECT version_num` = `['p22_001_integration_schema']`. The doc claim is now an accurate description of live state (after stamp-collapse). The deeper concern — that the underlying code chain still carries the multi-head inheritance (`p5_024 → p20_001 → p19_001 → p19_002 → p19_003 → p22_001`) — is acknowledged and unchanged. Not blocking. |
| **F-DBM-04** | LOW | REVOKE/GRANT split into two `op.execute` calls | NOT ADDRESSED (pre-existing, out of r2 scope) | Migration `alembic/versions/p22_001_integration_schema.py:78-83` is unchanged. Alembic transaction wrapping still mitigates mid-failure recovery. Round 2 did not modify the migration. Documented as a follow-up. |
| **F-DBM-05** | LOW | `actor_type` CHECK present; `result` lacks one | LIVE-VERIFIED, out of r2 scope | Live check: `actor_type = 'bogus'` raises `CheckViolationError` (good — the migration's CHECK IS enforced). `result = 'bogus_typo'` is accepted by the DB (F-DBM-05 remains). Validation lives in `audit.py` instead. Pre-existing finding — round 2 did not modify. |
| **F-DBM-06** | LOW | `event_id` UNIQUE + DB-side default redundant | NOT ADDRESSED (pre-existing, out of r2 scope) | Same as round-1. Cosmetic. |
| **F-DBM-07** | LOW | `result`, `project_scope` lack DB-level domain CHECK | LIVE-VERIFIED, out of r2 scope | `result` insert test confirms no DB CHECK (bogus value accepted). No `project_scope` CHECK in pg_constraint. Pre-existing LOW; not blocking. |
| **F-DBM-08** | INFO | 12 seed matches plan after filesystem omission | CONFIRMED | Live `count(*) FROM p22.integration_registry = 12`. Plan lists 13; the 13th (`filesystem`) is correctly omitted per migration comment line 137. Consistent. |
| **F-DBM-09** | INFO | Plan 13 vs migration-seed 12 (filesystem) | CONFIRMED | Same as F-DBM-08. By design. |

**Round-1 finding H2 — the critical concern the brief named — is RESOLVED.**
The high-level fix-log's claim "all migration post-conditions independently
confirmed" is corroborated by my live-DB queries.

---

## 2. What Was Verified

All queries were run against live VPS `guinevere-vps` (Ubuntu 24.04, PG 16.14)
using the documented env-source pattern (`export $(grep ... .env.core | xargs)`),
connecting via `asyncpg` as the **production role `guinevere_core`** (verified
`SELECT current_user` = `guinevere_core`). No secrets printed.

### 2.1 `ops.alembic_version` chain (live)

```
alembic_version total_rows = 1
  - p22_001_integration_schema
pg_settings:
  - server_version = 16.14 (Debian 16.14-1.pgdg13+1)
```

- Single row. Migration ID is exactly `p22_001_integration_schema`.
- The `ops.alembic_version` schema-binding from `alembic.env:54` and
  `alembic.ini:13` (`version_table_schema="ops"`) is honored.
- Server version matches the r2-declared PG 16.

### 2.2 Schema, tables, seed (live)

```
p22 schema: True
p22.integration_registry: True
p22.secret_ref_metadata: True
audit.integration_api_log: True
p22.integration_registry rows: 12

p22.integration_registry (all 12 rows):
  - browser  :: Brave/Exa/Obscura / L1_READ / low     / enabled=False / config_missing
  - calendar :: Google          / L1_READ / medium  / enabled=False / config_missing
  - discord  :: Discord         / L1_READ / medium  / enabled=False / config_missing
  - drive    :: Google          / L1_READ / high    / enabled=False / config_missing
  - finance  :: Polars/PG       / L1_READ / high    / enabled=False / config_missing
  - github   :: GitHub          / L1_READ / high    / enabled=False / config_missing
  - gmail    :: Google          / L1_READ / medium  / enabled=False / config_missing
  - memory   :: PostgreSQL/pgvector / L1_READ / critical / enabled=False / config_missing
  - notion   :: Notion          / L1_READ / medium  / enabled=False / config_missing
  - telegram :: Telegram        / L1_READ / medium  / enabled=False / config_missing
  - vps      :: Docker/Systemd  / L1_READ / high    / enabled=False / config_missing
  - whatsapp :: Neonize/Baileys / L1_READ / medium  / enabled=False / config_missing
```

- All 12 seed rows present. Each has distinct `integration_id`, distinct
  CAPABILITIES, default_tier=L1_READ, bearing unique `created_at` timestamps
  consistent with a single migration-time backfill (no later INSERTs).
- All 12 rows have `enabled=False` and `config_status='config_missing'` —
  consistent with M5 fix-log disclosure and the operator's smoke-test result
  (reconciliation that 3 adapters "ACTIVE" in smoke tested through shims do
  not flip DB-level `enabled=True`). NOT a fake-PASS because the script emits
  `IntegrationNotConfigured` / `ConfigurationMissingError`.

### 2.3 WORM enforcement (live — both GRANT-level and behavior-level)

GRANT/ACL level (via `has_table_privilege(guinevere_core, ..., op)`):

```
WORM privileges for guinevere_core on audit.integration_api_log:
  INSERT   = True
  SELECT   = True
  UPDATE   = False
  DELETE   = False
  TRUNCATE = True   <-- N-DBM-01 (non-blocking observation; see §3)
```

Plus from `pg_class.relacl` for `audit.integration_api_log`:

```
relacl: {guinevere_core=arDxt/guinevere_core}
```

ACL letter decoding (`a=INSERT, r=SELECT, D=TRUNCATE, x=REFERENCES, t=TRIGGER`,
absent `w`/`d` confirm REVOKE of UPDATE/DELETE):

```
INSERT    : a → present
SELECT    : r → present
TRUNCATE  : D → present (owner-privilege; see N-DBM-01)
REFERENCES: x → present (db-side FK grant auto-added when creating FK constraints; benign)
TRIGGER   : t → present (May be added by PG default — benign)
UPDATE    : w → NOT present (correctly REVOKEd)
DELETE    : d → NOT present (correctly REVOKEd)
```

Live negative test (as `guinevere_core`, the EXACT role that would be in a
production attacker path):

```
Live negative-test (WORM must BLOCK update/delete):
  connected_as: guinevere_core
  INSERT_OK       (audit_startup row inserted)
  UPDATE_BLOCKED: permission denied for table integration_api_log
  DELETE_BLOCKED: permission denied for table integration_api_log
  test_row_visible_after_failure = 1   (row still present; UPDATE didn't take effect)
```

WORM is **proven**, not merely GRANT-state:
- The `has_table_privilege` ACL check matches the actual runtime behavior:
  both UPDATE and DELETE reject with PostgreSQL `InsufficientPrivilegeError`.
- The row created during the test remains in the table exactly as inserted
  (no silent UPDATE; no silent DELETE). This rules out a class of "the GRANT
  looks revoked but a default permission overrides it" bugs.

### 2.4 Column presence (live)

Forced check of every column the audit log needs:

```
audit.integration_api_log full column profile (live):
  - id           :: bigint                 nullable=NO  default=nextval(id_seq)
  - event_id     :: uuid                   nullable=NO  default=gen_random_uuid()
  - sequence     :: bigint                 nullable=NO  default=nextval(sequence_seq)
  - occurred_at  :: timestamp with timezone nullable=NO  default=now()
  - actor_type   :: text                   nullable=NO  default=None  (CHECK IN user/agent/system)
  - actor_id     :: text                   nullable=NO  default=None
  - integration_id :: text                 nullable=NO  default=None
  - provider     :: text                   nullable=NO  default=None
  - action       :: text                   nullable=NO  default=None
  - tier         :: text                   nullable=NO  default=None
  - project_id   :: uuid                   nullable=YES default=None  ← P19 namespace, present ✓
  - project_scope:: text                   nullable=YES default=None  ← P19 namespace, present ✓
  - result       :: text                   nullable=NO  default=None  (no CHECK; F-DBM-05 out of scope)
  - correlation_id:: uuid                  nullable=YES default=None
  - metadata     :: jsonb                  nullable=NO  default='{}'
  - previous_hash:: text                   nullable=NO  default=''
  - event_hash   :: text                   nullable=NO  default=None
  - chain_version:: smallint               nullable=NO  default=2

project_id / project_scope confirmation:
  - project_id    :: uuid (nullable, no default)
  - project_scope :: text (nullable, no default)
```

`project_id` and `project_scope` are both PRESENT, NULLABLE, with no DB-side
default. This matches the migration (`alembic/versions/p22_001_integration_schema.py:47-48`)
and the P19 multi-project namespace contract (per `p19-012-production-deploy.md`
memory).

### 2.5 Indexes (live)

```
INDEXES on audit.integration_api_log (live):
  - integration_api_log_event_id_key          (UNIQUE; from UNIQUE constraint at line 38)
  - integration_api_log_pkey                  (PK on id, bigserial)
  - ix_integration_api_log_correlation_id     (line 72-74)
  - ix_integration_api_log_integration_id     (line 60-61)
  - ix_integration_api_log_occurred_at        (DESC; line 63-65)
  - ix_integration_api_log_project_id         (WHERE project_id IS NOT NULL; line 67-70)

INDEXES on p22.integration_registry (live):
  - integration_registry_pkey
  - ix_integration_registry_enabled           (WHERE enabled=TRUE)
```

All four migration-declared indexes on `audit.integration_api_log` are
present, including the partial WHERE-clause index on `project_id IS NOT NULL`.
The `enabled` partial index on `p22.integration_registry` is present. Match
the migration.

### 2.6 CHECK constraints (live)

```
CHECK constraints on audit.integration_api_log:
  - integration_api_log_actor_type_check : CHECK ((actor_type = ANY (ARRAY['user'::text, 'agent'::text, 'system'::text])))

Probing CHECK on actor_type (must reject bogus):
  CHECK_VIOLATION (actor_type) BLOCKED   ✓ (correctly enforced)

Probing CHECK on result (F-DBM-07 unmitigated per migration):
  ARBITRARY_result_INSERTED n= 1   (confirmed absent; pre-existing F-DBM-07/05 NOT addressed in r2)
```

Only one CHECK constraint on the audit log: `actor_type IN
('user','agent','system')` — correctly enforced (live negative test backs the
migration text). Confirms `result` / `project_scope` lack DB-level validation
(F-DBM-05/07) — pre-existing LOW finding; not addressed in this round.

### 2.7 Role-grant matrix (live, full inventory of `grantee × privilege`)

```
ROLE GRANTS on audit.integration_api_log:
  - guinevere_core : INSERT
  - guinevere_core : REFERENCES
  - guinevere_core : SELECT
  - guinevere_core : TRIGGER
  - guinevere_core : TRUNCATE       ← N-DBM-01; see §3

ROLE GRANTS on p22.integration_registry:
  - guinevere_core : DELETE
  - guinevere_core : INSERT
  - guinevere_core : REFERENCES
  - guinevere_core : SELECT
  - guinevere_core : TRIGGER
  - guinevere_core : TRUNCATE
  - guinevere_core : UPDATE
```

The p22.integration_registry grants match the migration (line 115: `GRANT
SELECT, INSERT, UPDATE`). The audit-log grants match the migration's intent
except for `TRUNCATE`, REFERENCES, TRIGGER — these come from PostgreSQL's
default ACL when a role is table owner (N-DBM-01; see §3).

### 2.8 Audit-log chain length (live)

```
audit_log rows (post round-2 negative tests):
  - sequence=1 actor_id=round2-audit-db   chain_version=2  previous_hash='' event_hash='round2-neg-test'
  - sequence=3 actor_id=check-result      chain_version=2  previous_hash='' event_hash='x'
production-written audit rows (excluding r2 test): 0
```

Two synthetic audit-test rows from THIS audit remain permanently in the log
(N-DBM-02; described below). Production traffic to the audit log is currently
`0` — consistent with P22 being a dev/pre-prod deployment where no L2+ actions
have been issued yet (per fix-log and r1 §3.4 line "no P22 L2+ actions yet").

---

## 3. New Findings (Round-2 only)

### N-DBM-01 (MEDIUM) — TRUNCATE NOT in WORM contract; owner-role retains TRUNCATE

**Detail.** The migration at `alembic/versions/p22_001_integration_schema.py:77-83`
issues:

```sql
REVOKE UPDATE, DELETE ON audit.integration_api_log FROM guinevere_core;
GRANT  INSERT, SELECT ON audit.integration_api_log TO guinevere_core;
```

It does NOT issue `REVOKE TRUNCATE` (Postgres syntax doesn't allow that — only
the owner-specific privilege-bundle has a TRUNCATE bit, and the owner always
retains it). Live `pg_class.relacl` confirms:

```
relname: integration_api_log
owner:   guinevere_core              <-- ALREADY the applier role
relacl:  {guinevere_core=arDxt/guinevere_core}
```

Where `a`=INSERT, `r`=SELECT, `D`=TRUNCATE, `x`=REFERENCES, `t`=TRIGGER.
`w` (UPDATE) and `d` (DELETE) are NOT present.

**Implication:** The production role `guinevere_core` (which is ALSO the
table owner) can issue `TRUNCATE audit.integration_api_log` to wipe the table
entirely while still being denied row-level UPDATE/DELETE. The migration's
implicit invariant "Write-Once-Read-Many" is *row-level* enforced, not
*table-level*.

**Is this a hard rejection?** No. The brief enumerates the WORM criteria as
"has_table_privilege(guinevere_core, audit.integration_api_log, UPDATE/DELETE)
must be False", which is fully satisfied. TRUNCATE is a stronger guarantee
that the migration never promised.

**Why MEDIUM, not LOW:** A compromised `guinevere_core` (e.g., SQL injection
through the application) could still destroy audit history in a single
TRUNCATE. This is qualitatively different from "could erase one row" (WORM
prevents that) — `TRUNCATE` will erase the ENTIRE chain, and if real
attestation is the audit purpose, a single TRUNCATE invalidates all
forensic chain verification. The fix-path is small: split the migration's
applicant from its applier so the table owner is a separate role that has no
application-side password, OR post-apply do
`ALTER TABLE audit.integration_api_log OWNER TO guinevere_owner;` followed
by an explicit `GRANT INSERT, SELECT ...` (no TRUNCATE in the explicit grant).

**Recommendation.** If pristine WORM-vs-TRUNCATE is required for the audit log,
issue a follow-up migration that:
1. `ALTER TABLE audit.integration_api_log OWNER TO some_owners_role;` (with
   no application-side credentials).
2. Re-issue `GRANT INSERT, SELECT ON audit.integration_api_log TO guinevere_core;`
3. Optionally `REVOKE ALL ON audit.integration_api_log FROM PUBLIC`.

Also a separate `tests/p22/test_worm_truncate.py` to assert
`has_table_privilege(guinevere_core, 'audit.integration_api_log', 'TRUNCATE') = False`.

### N-DBM-02 (INFO) — Two round-2 synthetic audit-log rows left behind

**Detail.** The WORM negative test in §2.3 inserted one audit row
(`actor_id='round2-audit-db'`, sequence=1). The §2.6 CHECK probe inserted one
more (`actor_id='check-result'`, sequence=3). Sequence=2 was used by the failed
`actor_type='bogus'` insertion (rolls back inside its own statement).

By design, these rows are now PERMANENT in the audit log because `guinevere_core`
cannot DELETE due to WORM (the same WORM being verified here). They have:
- `previous_hash=''` (default), which would BREAK a Python-side chain-hash
  validator's `event_hash == hash(previous_hash + canonical_event)` check for
  real events
- `event_hash='round2-neg-test'` / `event_hash='x'` (synthetic strings), not
  deterministic-hash outputs

**Implication.** If the application's `AuditLogger` validates the chain
on-write by reading the previous append and recomputing its hash, it will
either:
(a) skip validation when no prior rows exist (in which case these are benign
    when no production traffic has flowed — current state, 0 prod rows),
or
(b) reject itself.

Live state shows 0 production-written rows. Therefore as long as the chain
remains empty, the synthetic rows are inert. But the **first** production
event will be `sequence=4`, and its `previous_hash` should NOT be `'round2-neg-test'`
— it should be the hash of the most recent VALID event. If `AuditLogger` reads
"most recent by sequence DESC LIMIT 1", it will pick up the synthetic row and
fail. If it filters `actor_id` it will be fine, but that's an undocumented
invariant.

**Recommendation.** Before any production traffic flows into `audit.integration_api_log`,
a superuser should TRUNCATE the table (the cleanest fix: drop the two dev
rows + re-initialize chain_version=2 from a clean state). The chain
hash-rooting logic should also be downstream-aware so it can skip sandbox rows
in the future (preferring `WHERE chain_version=2 AND event_id IS NOT NULL` or
similar). A separate migration could re-seed with a deterministic genesis
row. None of this is round-2-blocking.

### N-DBM-03 (LOW) — `p22.secret_ref_metadata` empty (consistency check)

**Detail.** Live `p22.secret_ref_metadata` table is empty (0 rows). The
migration creates the table (line 120-130) but does NOT seed it; production
adapters would write secret-metadata rows on first use. The application
summary in `p22-life-integration-complete.md` ("10/13 adapters
CONFIG_MISSING (operator-gated creds)") is consistent with this — adapters
without provisioned credentials cannot write secret-metadata rows yet.

**Implication.** Not a defect. Empty is correct given the operator-gating of
external credentials. But the r1 finding F-DBM-04 (WORM in single block) and
F-DBM-05/07 (lacking CHECK on result/project_scope) remain open and unchanged.

### N-DBM-04 (INFO) — Owners-role is implicit (audit-log table owner = applier role)

**Detail.** `audit.integration_api_log`, `p22.integration_registry`, and
`p22.secret_ref_metadata` are all owned by `guinevere_core` (whoever ran the
migration through `DATABASE_URL`). This is the underlying cause of N-DBM-01.
It is also not what the migration comments imply: lines 5-9 read "follows
P22 plan ... hash-chained, INSERT/SELECT only", suggesting the audit table
should be isolated from the application role.

**Recommendation.** Document this role-assumption in
`p22-migration-application.md` so future round-2 audits (and any rotation
of `DATABASE_URL` to a different role for migrations) can recalibrate
expectations.

---

## 4. Hard-Rejection Checklist (per audit brief)

| Criterion | Status | Evidence |
|---|---|---|
| Row count of `p22.integration_registry` is 12 | **PASS** (12) | §2.2 |
| Migration applied (`ops.alembic_version`) | **PASS** (1 row: `p22_001_integration_schema`) | §2.1 |
| WORM: UPDATE denied | **PASS** (revoked + live UPDATE_BLOCKED) | §2.3 |
| WORM: DELETE denied | **PASS** (revoked + live DELETE_BLOCKED) | §2.3 |
| `p22` schema exists | **PASS** | §2.2 |
| `p22.*` tables defined | **PASS** (integration_registry, secret_ref_metadata) | §2.2 |
| `project_id`, `project_scope` columns present | **PASS** | §2.4 |
| No secrets/token/PAT printed | **PASS** (URL redacted; only role names + table names) | preamble of §2 |

All hard-rejection criteria from the audit brief are independently satisfied.

The brief also called out the smoke-test confirmation — *no secrets in code,
no fake PASS* — which we've validated by:
- No DB password, token, or API key printed in `p22-migration-application.md`,
  in `audit-db-migration.md`, or in this audit-db.md.
- No "approximately 12" / "looks good" phrasing; all counts are exact.
- All 12 listed seed rows are present and match the migration's INSERT
  (lines 138-153) byte-for-byte.

---

## 5. Recommendation

**Promote db-migration dimension from NEEDS_REVIEW (round 1) to PASS (round 2).**
The high-level fix log's claim (H2 RESOLVED, parent independently re-verified
live DB) is corroborated by this audit's independent re-run. The remaining
PRE-EXISTING LOW/INFO findings (F-DBM-04/05/06/07) are documented and
unchanged; they are not in scope for the round-2 final gate.

**Carry-forward, non-blocking:**
- N-DBM-01 (MEDIUM): WORM is row-level but not table-level for the owning role;
  consider a follow-up migration that splits owner from applier role if
  pristine WORM-vs-TRUNCATE is required for future P22 production attestation.
- N-DBM-02 (INFO): Two synthetic audit-log rows remain (round-2 test
  artifacts); recommend a superuser-side TRUNCATE before any P22 production
  traffic flows through the log. If `AuditLogger` does chain validation on
  write, ensure it filters or uses a deterministic genesis row.
- N-DBM-03 (LOW): `p22.secret_ref_metadata` empty is consistent with
  operator-gated external credentials. Will populate as adapters are wired.
- N-DBM-04 (INFO): Document the implicit role assumption
  (`guinevere_core` is owner AND applier) in `p22-migration-application.md`.

**Conditional promotion to PASS-with-INFO if final gate policy is strict:**
If the policy is "hardened WORM (incl. TRUNCATE) must hold", db-migration
would step down to NEEDS_REVIEW and an additional migration would be added to
the fix list. The current brief, however, defined the WORM criteria as
"has_table_privilege UPDATE/DELETE = False" — which is fully met. Therefore
**PASS**.

---

## 6. Files Audited & Sources

Read in this round (READ-ONLY on docs and code; LIVE on DB):

- `docs/setup-evidence/P22/production-activation/audits/round-1/audit-db-migration.md`
- `docs/setup-evidence/P22/production-activation/fixes/round-1-fix-log.md`
- `docs/setup-evidence/P22/production-activation/implementation/p22-migration-application.md`
- `docs/setup-evidence/P22/production-activation/research/p22-db-migration-readiness.md`
- `docs/setup-evidence/P22/production-activation/plan/p22-production-activation-plan.md`
- `alembic/versions/p22_001_integration_schema.py` (167 lines, full read)
- `alembic/env.py` (`version_table_schema` at line 54/68)
- `alembic.ini` (`version_table_schema = ops` at line 13)
- `docs/setup-evidence/P22/production-activation/audits/round-2/db_verify.py`
  (in-progress scratch script; not relied on)

Live queries (VPS `guinevere-vps` → `localhost:5433` → `guinevere` db → as
`guinevere_core`):

- §2.1: `SELECT version_num FROM ops.alembic_version ORDER BY version_num`
- §2.2: `SELECT 1 FROM pg_namespace`, `pg_tables`, `p22.integration_registry`,
  `p22.secret_ref_metadata`, `audit.integration_api_log`; row counts;
  full registry dump
- §2.3: WORM `has_table_privilege(guinevere_core, ..., op)` for
  INSERT/SELECT/UPDATE/DELETE/TRUNCATE; live INSERT+UPDATE+DELETE negative test
- §2.4: `information_schema.columns` for both tables
- §2.5: `pg_indexes` inventory
- §2.6: `pg_constraint` inventory + CHECK-VIOLATION probes for `actor_type`
  and `result`
- §2.7: `information_schema.role_table_grants` for both tables
- §2.8: `audit.integration_api_log` row inventory
- (Bespoke): `pg_class.relacl` query to confirm owner-related privileges

All database redacted strings used only `://REDACTED@` substitution in
shell echoes. No concrete password printed.

---

## 7. Auditor's Tooling Confirmation

This round-2 audit **successfully ran SSH**, sourcing `.env.core` via
documented filter, connecting via asyncpg, and executing 14 distinct query
blocks against the live VPS database. The round-1 §7 "Tooling Limitation
Disclosure" no longer applies: round-2 has full SSH + asyncpg access, and
the live-state truth-on-disk gap is closed.

---

## 8. Final Verdict — DB-MIGRATION DIMENSION (ROUND 2 / FINAL GATE)

**VERDICT: PASS**

- 0 hard-rejection criteria remaining (§4).
- 1 HIGH r1 finding (F-DBM-01 / "Live DB not independently verified") is GENUINELY RESOLVED.
- 2 MEDIUM r1 findings (F-DBM-02, F-DBM-03) are RESOLVED (F-DBM-03 directly;
  F-DBM-02 partially, but the post-fix live state is consistent with the doc).
- 4 LOW r1 findings (F-DBM-04, F-DBM-05, F-DBM-06, F-DBM-07) are confirmed
  unchanged (out of r2 scope; pre-existing).
- 2 INFO r1 findings (F-DBM-08, F-DBM-09) are CONFIRMED.
- 4 NEW findings in r2 (N-DBM-01 MEDIUM; N-DBM-02 INFO; N-DBM-03 LOW;
  N-DBM-04 INFO). None are hard-rejection-blocking.

Db-migration dimension is ready for **P22 production activation** under the
existing brief. The single MEDIUM carry-forward (TRUNCATE privilege) is a
hardening call for a future migration; it is documented for the operator.
