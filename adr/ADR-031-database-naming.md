---
adr: 031
title: "Database Naming Convention"
status: "Accepted"
date: "2026-05-31"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - database
  - postgresql
  - naming
  - infrastructure
risk_level: "HIGH"
supersedes: "N/A"
related_documents:
  - Guinevere_TechnicalArchitecture_v2.0.md
  - Guinevere_MemorySchema_v2.0.md
---

# ADR-031: Database Naming Convention

## Status

Accepted

## Date

2026-05-31

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

database, postgresql, naming, infrastructure

## Risk Level

HIGH

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md) | Defines PostgreSQL deployment and database name as `guinevere` |
| [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md) | Schema definitions use database name `guinevere` |

## Context

During cross-reference validation of the Test Plan, DR Plan, and Ops Manual (2026-05-30), a CRITICAL discrepancy was found in the production database name:

| Document | Database Name Used |
|---|---|
| `Guinevere_TestPlan_v1.0.md` | `guinevere_db` |
| `Guinevere_DisasterRecoveryPlan_v1.0.md` | `guinevere` |
| `Guinevere_InternalOpsManual_v1.0.md` | `guinevere` |
| `Guinevere_TechnicalArchitecture_v2.0.md` | `guinevere` |
| `Guinevere_MemorySchema_v2.0.md` | `guinevere` |
| `docs/Guinevere_TDD_Guide_v1.0.md` | `guinevere_db` |

The TestPlan and TDD Guide used `guinevere_db` while all canonical v2.0 architecture documents and the other two operational docs use `guinevere`. This would cause connection string mismatches and failed database connections in production.

## Decision Drivers

- Connection string correctness: a wrong database name in any config or connection string causes immediate connection failure.
- Canonical consistency: TechnicalArchitecture v2.0 and MemorySchema v2.0 both use `guinevere` as the authoritative name.
- Simplicity: `guinevere` is cleaner than `guinevere_db` and avoids redundancy (the `_db` suffix adds no semantic value since the context is already a database).
- DR restore scripts: backup/restore procedures reference the database name and must match across all docs.

## Considered Options

1. Use `guinevere` everywhere (matches TechnicalArchitecture v2.0 and majority of docs)
2. Use `guinevere_db` everywhere (matches TestPlan and TDD Guide)
3. Use `guinevere_prod` for production and `guinevere_test` for test

## Decision Outcome

Chosen option: **Use `guinevere` everywhere**.

| Context | Database Name |
|---|---|
| Production | `guinevere` |
| Test / CI | `guinevere_test` |
| Staging (future) | `guinevere_staging` |

The production database name is `guinevere` without any suffix. Environment-specific variants append an underscore suffix (`_test`, `_staging`) to the base name.

### Connection String Template

```
postgresql+asyncpg://guinevere:***@postgres.internal:5432/guinevere
```

Test environment:

```
postgresql+asyncpg://test:test@localhost:5433/guinevere_test
```

## Consequences

### Positive

- Eliminates connection string mismatch risk across all operational documents.
- Aligns all docs with the canonical TechnicalArchitecture v2.0 reference.
- Simplifies DR restore scripts — single consistent name.

### Negative

- Requires patching TestPlan (1 occurrence at line 532) and TDD Guide (2 occurrences at lines 805, 824).

### Risks

- None material. The fix is a simple string replacement with no architectural impact.

## Implementation Notes

- TestPlan line 532: `guinevere_db` → `guinevere` in DATABASE_URL production example.
- TDD Guide lines 805, 824: `guinevere_db` → `guinevere` in test configuration examples.
- DRPlan and OpsManual already use `guinevere` — no changes needed.
- All future docs must use `guinevere` for the production database name.

## Links

- [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md)
- [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)

## Review Record

- Reviewer: Guinevere (Sisyphus orchestrator)
- Review Date: 2026-05-31
- Decision: Accepted
- Notes: Simple canonicalization to match TechnicalArchitecture v2.0. Low-risk string replacement.

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-31 | Guinevere (Sisyphus) | Initial ADR canonicalizing database name to `guinevere` per TechnicalArchitecture v2.0. |
