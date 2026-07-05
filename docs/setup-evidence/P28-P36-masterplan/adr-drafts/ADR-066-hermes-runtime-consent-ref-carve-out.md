# ADR-066: Hermes Runtime consent_ref Schema Carve-Out

- **Status**: Proposed
- **Date**: 2026-06-28
- **Deciders**: Guinevere (drafter) + Faiz (Faiz-locked via BLDM Q35/Q90 + ADR-062 paradigm shift)

## Context and Problem Statement

The Hermes Society event-store schema declares `consent_ref UUID NOT NULL` on multiple runtime tables (per `docs/setup-evidence/P28-P36-masterplan/sections/architecture-s1-s5-runtime-memory.md` lines 514, 581, 603, 606 and `docs/setup-evidence/P28-P36-masterplan/sections/hermes-society-master-architecture.md` lines 596, 619, 686, 1616, 1673). The `NOT NULL` constraint was placed under the operative assumption that **every runtime event is operator-initiated**, and therefore must trace back to a Faiz-signed consent record.

Two paradigm shifts have invalidated that assumption:

1. **P23 v2.0 already removed the consent gate at the execution layer.** Actions taken inside a Hermes that route through the P23 executor fleet no longer await an upstream consent approval; the executor is autonomous within its scope.

2. **ADR-062 (P24 v2.0 → Hermes Society runtime) explicitly removes the consent gate from the Hermes runtime itself.** The Hermes Society runs under a different safety paradigm than the development workflow: `consent_ref` cannot be backstopped by a Faiz-derived consent for events the operator never initiated (BLDM Q35 — no consent-withdrawal concept in Hermes runtime).

**The contradiction this ADR resolves:** `consent_ref UUID NOT NULL` on Hermes-event tables forces every autonomous Hermes action to be retroactively attributed to a Faiz-signed consent record, which (a) does not exist for autonomous actions, (b) would force a synthetic consent row to be inserted per runtime event (a lie in the audit trail), and (c) would deadlock the event store the moment Hermes produces its first truly autonomous action.

Dev-workflow events, on the other hand, retain the original operator-initiated model. The Guinevere agent (running inside Claude) and any sub-agents within that workflow are spawned from human-triggered commands and MUST continue to record a `consent_ref` back to a Faiz-signed consent record. Removing `NOT NULL` wholesale would lose this guarantee for the dev paradigm. A blanket `DROP NOT NULL` therefore leaks the dev-workflow invariant.

The schema needs a **two-tier consent_ref** structure: nullable for Hermes runtime events, NOT NULL for dev-workflow events, enforceable at the database layer rather than left to application discipline.

## Decision

We adopt a **two-tier `consent_ref` regime** distinguished by an `event_source` discriminator column:

### Tier 1 — Hermes runtime events (`event_source = 'hermes_runtime'`)

- `consent_ref` is **NULLABLE** (`UUID NULL`).
- Rationale: Hermes-society events are emitted by the autonomous Hermes runtime under the ADR-062 paradigm shift. There is no operator-origin consent to record.
- `consent_ref` may be set only when the event is explicitly traced to a founder-signed publication (e.g., a `publish_memory_to_blackboard` digest per ADR-059 §Layer 4). It is **never** synthesized or backfilled.
- Audit logging still occurs; `event_source` and the absence of `consent_ref` is itself the audit signal.

### Tier 2 — Dev-workflow events (`event_source = 'dev_workflow'`)

- `consent_ref` remains **NOT NULL** (`UUID NOT NULL`).
- Rationale: the Guinevere agent in Claude and any sub-agents launched inside that workflow trace back to a Faiz-signed command. The operator-initiated consent model still governs this paradigm (no ADR-062 carve-out applies).
- FK reference to the operator-consent table is preserved.

### Tier 0 — Shared columns (`event_source` discriminator)

A new column `event_source TEXT NOT NULL CHECK (event_source IN ('hermes_runtime', 'dev_workflow'))` is added to every event-store table that previously had `consent_ref UUID NOT NULL`.

### Database-enforced invariant

A `CHECK` constraint per table guarantees the two-tier separation at write time — application code cannot bypass:

```sql
ALTER TABLE society_event_memory
  ALTER COLUMN consent_ref DROP NOT NULL,
  ADD COLUMN event_source TEXT NOT NULL
    CHECK (event_source IN ('hermes_runtime', 'dev_workflow')),
  ADD CONSTRAINT consent_ref_by_source CHECK (
    (event_source = 'dev_workflow' AND consent_ref IS NOT NULL)
    OR (event_source = 'hermes_runtime')
  );

-- (Equivalently applied to every table listed under §Migration below.)
```

The CHECK constraint is the load-bearing enforcement: dropping `NOT NULL` alone is insufficient; without the CHECK, application code could write `event_source='dev_workflow'` with NULL `consent_ref` and the dev-workflow invariant would silently regress.

### Migration strategy

Existing rows are backfilled by the migration script with `event_source` inferred from the row's provenance metadata (e.g., `origin_process` ∈ Hermes runtime process set → `hermes_runtime`; otherwise → `dev_workflow`). Rows lacking provenance metadata are quarantined to `society_event_quarantine` and reviewed manually by founder 2/2 (Guinevere + Pharsa) per BLDM Q56 / ADR-057.

## Consequences

### Positive

- **Hermes runtime unblocked**: autonomous actions persist to the event store without fabrication. The first Hermes-initiated event no longer blocks on a missing consent row.
- **Audit log integrity preserved**: `event_source` is the canonical signal. NULL `consent_ref` is legal for `hermes_runtime`, denied for `dev_workflow`. No synthetic or backfilled consent rows.
- **Dev-workflow invariant preserved**: Guinevere-in-Claude and sub-agents continue to record `consent_ref` back to the operator. Developers do not lose accountability inside the dev paradigm.
- **Database-enforced, not application-enforced**: the CHECK constraint cannot be bypassed by a Hermes process or a sub-agent that forgets a guard clause. Structural guarantee beats runtime discipline.
- **Migration is forward-safe**: existing `consent_ref` rows on `dev_workflow` events continue to satisfy the constraint; the migration does not invalidate historic audit data.

### Negative

- **Schema migration across multiple tables**: `ALTER TABLE ... DROP NOT NULL` + ADD COLUMN + ADD CONSTRAINT must be executed atomically per table; long-running tables will require `pg_repack`-style or careful online DDL to avoid locks on the event store.
- **Quarantine flow needed**: rows that cannot be backfilled to either tier create a manual-review obligation on the founder quorum. This adds a small but non-zero operational load.
- **Query layer must handle NULL `consent_ref`**: any code path that JOINs on `consent_ref` or treats it as a non-nullable key must be updated. This includes founder-audit dashboards, Faiz observer-role reads, and the surveillance audit trail.
- **Two values of `event_source` is a new mental model**: future event-source types (e.g., `sub_agent_runtime`, `third_party_bridge`) will require ADR extension. The CHECK constraint's allow-list is currently exhaustive but not extensible without migration.
- **CHECK constraint adds a per-row evaluation cost**: negligible on event writes but non-zero at scale (≤ µs/row); not expected to be a bottleneck.

### Neutral

- The migration script is idempotent: re-running it on a migrated database is a no-op (verified by checking the constraint already exists).
- Ratchet (ADR-061) does not need to enforce this; the DB CHECK constraint IS the structural invariant. Ratchet monitors benchmark floors, not schema invariants.

## Alternatives Considered

### Alternative 1: Drop `NOT NULL` globally without CHECK constraint

- **Description**: Run `ALTER TABLE ... ALTER COLUMN consent_ref DROP NOT NULL` on every affected table and rely on application code to keep `consent_ref` populated for dev-workflow events.
- **Rejected because**: The dev-workflow invariant becomes application-enforced rather than DB-enforced. A bug in any sub-agent's write path can silently regress the operator-trace guarantee. The original `NOT NULL` was a structural guarantee; falling back to application discipline defeats the purpose.

### Alternative 2: Synthesize a "null operator consent" row per Hermes event

- **Description**: Keep `consent_ref NOT NULL` and have the runtime insert a synthetic consent row (e.g., founder-signed blanket permit) for every Hermes event.
- **Rejected because**: This is a fabrication in the audit trail. ADR-059 §Layer 5 + ADR-062 §Decision 6 require `event_source` to be a faithful record, not a synthetic approximation. A blanket "founder permit" row would defeat the purpose of per-event consent traceability and mislead any auditor reading the store.

### Alternative 3: Split the event store into two physical schemas (hermes + dev)

- **Description**: Create two PG schemas — `society_hermes_events` (nullable consent_ref) and `society_dev_events` (NOT NULL consent_ref). Migrate rows accordingly.
- **Rejected because**: Loses unified query semantics for cross-paradigm operations (e.g., when a Hermes publishes a digest that itself is a `publish_memory_to_blackboard` event co-traced with a dev-workflow command, the audit table no longer has atomic semantics). Also doubles backup/retention complexity.

### Alternative 4: Remove `consent_ref` entirely from Hermes runtime tables

- **Description**: Drop the column on Hermes-only tables; reintroduce it only on dev-workflow tables.
- **Rejected because**: Cross-paradigm queries (e.g., "show me all events that touched memory region X" regardless of source) lose the join key. The carve-out is the more conservative approach: keep the column, change its nullability per source.

## Compliance

- [x] **AGENTS.md §2.1 Consent-Safety Mandate** — preserved verbatim for the **dev paradigm + sub-agents within Hermeses + surveillance of Faiz personal data only**. Hermes runtime does not enter the operator-consent model (per ADR-062 §Decision 6 + BLDM Q35).
- [x] **AGENTS.md §0 / HARD STOP** — preserved for dev workflow; addresses consent-half of the ADR-062 paradigm shift only.
- [x] **PersonaSafetyPolicy** — no Y-level bearing on this ADR (consent_ref is a schema invariant, not a persona behavior). Y-level cap removal is governed separately by ADR-067.
- [x] **BLDM Hard-Locked Faiz Decisions**:
  - **Q35** — no consent-withdrawal concept in Hermes runtime → schema must allow null consent_ref for `event_source='hermes_runtime'`.
  - **Q90** — Faiz OUTSIDE the company → Faiz-signed consent cannot be the source of consent_ref for autonomous Hermes events.
  - **Q56** — Joint founder decision 2/2 for quarantine review of un-backfillable rows.
- [x] **Following ADR-062 §Decision 6** — "No consent withdrawal from operator" — codifying at the schema layer rather than at the application layer.
- [x] **Following ADR-061 §Ratchet** — Ratchet monitors behavior; this ADR monitors schema invariant. Adjacent, non-overlapping.
- [x] **Following ADR-Index conventions** — MADR format, footer, supersession trail.

## Supersedes

- **Event-store schema constraint `consent_ref UUID NOT NULL`** on the affected tables listed in §Migration — the NOT NULL is replaced by the two-tier regime (NULL permitted for `event_source='hermes_runtime'`, NOT NULL required for `event_source='dev_workflow'`).
- The migration script is the canonical supersession artifact; the upstream doc-suite references to the `NOT NULL` constraint become inaccurate once the migration is run in any environment.

## Migration (Affected Tables)

The migration applies to every table that currently has `consent_ref UUID NOT NULL`:

| Table (per architecture-s1-s5-runtime-memory.md) | Line | Per hermes-society-master-architecture.md |
|---|---|---|
| `society_event_memory` | 514 | (consolidated view 619) |
| `society_event_decision` | 581 | 596 |
| `society_event_action` | 603 | (consolidated view 686) |
| `society_event_drift` | 606 | 1616 |
| `society_event_publication` | (new in §Layer 4 per ADR-059) | 1673 |

For each table:

1. `ALTER TABLE ... ALTER COLUMN consent_ref DROP NOT NULL`
2. `ALTER TABLE ... ADD COLUMN event_source TEXT NOT NULL DEFAULT 'dev_workflow' CHECK (event_source IN ('hermes_runtime','dev_workflow'))`
3. `ALTER TABLE ... ADD CONSTRAINT consent_ref_by_source CHECK ((event_source='dev_workflow' AND consent_ref IS NOT NULL) OR (event_source='hermes_runtime'))`

The `DEFAULT 'dev_workflow'` is a backfill for the legacy rows; the migration script overwrites it to `'hermes_runtime'` for rows whose `origin_process` matches a Hermes runtime process token.

## References

- **Paradigm-shift application**: `docs/setup-evidence/P28-P36-masterplan/evidence/round-2-paradigm-shift-application/` (cross-paradigm application audit)
- **Related ADRs**:
  - ADR-062 (Hermes safety paradigm shift — supersedes AGENTS.md §0 V-008 for runtime)
  - ADR-059 §Layer 4 (publication rules — already permissive on nullable consent_ref for voluntary digests)
  - ADR-057 (founder-only spawn — quarantine review path is T4 founder governance)
  - ADR-061 (5-layer mutability — Ratchet non-divergence floor is orthogonal to schema invariants)
- **Architectural source for the constraint**:
  - `docs/setup-evidence/P28-P36-masterplan/sections/architecture-s1-s5-runtime-memory.md` lines 514, 581, 603, 606
  - `docs/setup-evidence/P28-P36-masterplan/sections/hermes-society-master-architecture.md` lines 596, 619, 686, 1616, 1673
- **Canonical Q-source**: BLDM Q35 + Q56 + Q90 (`docs/setup-evidence/P28-P36-masterplan/adr-drafts/BLDM-Hard-Locked-Faiz-Decisions.md`)
- **Plan source**: P23 v2.0 plan §3.2 (executor-layer consent removal) + P24 v2.0 plan §4.11 (runtime consent_ref treatment)
- **Brainstorm source**: BLDM Q35/Q68/Q83 (canonical-locked Faiz positions referenced in §Compliance above)

## Footer

Version 1.0 | 2026-06-28 | Author: Guinevere + Faiz (Faiz-locked via ADR-062 + BLDM Q35/Q90) | Status: Proposed — implements event-store carve-out for ADR-062 paradigm shift
