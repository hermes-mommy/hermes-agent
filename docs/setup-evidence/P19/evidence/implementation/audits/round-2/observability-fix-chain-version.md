# OBS-02 Fix: Audit Hash Chain Versioning (chain_version)

**Finding:** OBS-02 [MEDIUM] -- Audit hash chain versioning field missing from schema
**Date:** 2026-06-26
**Verdict:** IMPLEMENTED

---

## 1. Root Cause

The P19 plan (P19-010) specified a `chain_version` field on `audit.audit_trail` to distinguish legacy hash chain rows (v1) from P19+ rows (v2, which include `project_id` in the canonical payload). The field was documented in:
- `docs/setup-evidence/P19/plan/p19-multi-project-context-enterprise-plan.md` L693-701, L831
- `docs/setup-evidence/P19/evidence/audits/round-1/observability-evidence.md` L19

The round-2 evidence tracker (`audits/round-2/observability-evidence.md` L14) prematurely marked OBS-02 as "RESOLVED" based solely on the plan documentation. The round-2 implementation audit (`implementation/audits/round-2/observability.md` L70-74, L109) actually checked the code and confirmed FAIL: no `chain_version` field existed in the model, dataclass, or any migration.

---

## 2. Changes Made

### 2a. Migration: `alembic/versions/p19_003_audit_chain_version.py` (NEW)

- Adds `chain_version SMALLINT NOT NULL DEFAULT 1` to `audit.audit_trail`
- Creates `ix_audit_trail_chain_version` btree index
- All existing rows backfilled to `chain_version=1` (legacy) via server default
- No hash recomputation -- existing hashes preserved
- Revision chain: `p19_002_project_id_not_null` -> `p19_003_audit_chain_version`

### 2b. Model: `src/memory/models.py` (AuditTrail, L1098-1101)

- Added `chain_version: Mapped[int] = mapped_column(SmallInteger, ...)` after `occurred_at`
- `server_default=text("1")`, `default=1` -- legacy rows default to v1
- `SmallInteger` added to sqlalchemy import block (L16)

### 2c. Dataclass: `src/loops/audit_writer.py` (AuditEvent, L32)

- Added `chain_version: int = 2` field (default 2 for new P19+ events)

### 2d. Writer: `src/loops/audit_writer.py` (AuditWriter.write_event, L100, L112)

- `AuditEvent` construction sets `chain_version=2`
- `AuditTrail` DB row construction sets `chain_version=2`

### 2e. Verifier: `src/loops/audit_writer.py` (AuditWriter.verify_chain, L127-168)

- Updated docstring to document chain-version-aware verification
- Added `chain_version` to `audit.chain_broken` error log for diagnostics
- Hash recomputation uses `event_payload` as-is (v1 rows have no project_id; v2 rows do) -- both verify correctly without cross-contamination

---

## 3. Chain Version Semantics

| Version | Meaning | Canonical Payload | Hash Algorithm | Created By |
|---------|---------|-------------------|---------------|-----------|
| 1 (legacy) | Pre-P19 rows | No project_id field | Original (unchanged) | Migration backfill / pre-P19 code |
| 2 (P19+) | New P19+ rows | MAY include project_id (NULL = global) | Same function, same input format | AuditWriter.write_event |

The `compute_hash` function is NOT changed. Both versions use the same SHA-256 computation over `event_type:loop_id:timestamp:data_json:previous_hash`. The difference is in what `data_json` contains:
- V1: `{"loop_id": "...", ...}` -- no project_id
- V2: `{"loop_id": "...", "project_id": "...", ...}` -- project_id present when non-null

This means legacy hashes remain valid and are not re-verified against the new format, exactly as the plan specified.

---

## 4. Verification Query

Post-deployment:
```sql
-- Confirm column exists
SELECT chain_version, count(*)
FROM audit.audit_trail
GROUP BY chain_version;
-- Expected: chain_version=1 for all pre-existing rows

-- Confirm index exists
SELECT indexname FROM pg_indexes
WHERE schemaname = 'audit' AND tablename = 'audit_trail'
AND indexname = 'ix_audit_trail_chain_version';

-- Confirm new rows use v2 (after write_event is called)
SELECT chain_version, event_type, occurred_at
FROM audit.audit_trail
WHERE chain_version = 2
ORDER BY occurred_at DESC
LIMIT 5;
```

---

## 5. Files Modified

| File | Change |
|------|--------|
| `alembic/versions/p19_003_audit_chain_version.py` | NEW -- migration |
| `src/memory/models.py` | AuditTrail.chain_version column + SmallInteger import |
| `src/loops/audit_writer.py` | AuditEvent.chain_version field + write_event/verify_chain updates |

---

## 6. Previous Claim vs Reality

The round-2 evidence tracker claimed "OBS-02 RESOLVED" based on the plan document. The implementation audit correctly identified this as FAIL. This fix closes the gap between plan documentation and actual code.
