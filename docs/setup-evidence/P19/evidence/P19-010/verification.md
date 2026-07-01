# P19-010 Verification: Observability / Audit / Evidence Integration

**Wave:** P19-010
**Date:** 2026-06-26
**Status:** PASS

---

## 1. Scope

Add `project_id` to audit/observability surfaces across the loop audit writer, life kernel durability backends, and knowledge graph consent auditor. Create Prometheus metrics modules with `project_id` label. Additive change: `project_id=None` default preserves legacy behaviour.

---

## 2. Files Modified / Created

| # | File | Status |
|---|------|--------|
| 1 | `src/loops/audit_writer.py` | MODIFIED -- `project_id` on `AuditEvent` + `write_event` |
| 2 | `src/life_kernel/domain_minds/durability.py` | MODIFIED -- `project_id` on `record()` abstract + 2 impls |
| 3 | `src/knowledge_graph/consent/audit.py` | MODIFIED -- `project_id` on `log_consent_event` |
| 4 | `src/loops/metrics.py` | CREATED -- loop domain Prometheus metrics (3 counters/histograms) |
| 5 | `src/life_kernel/metrics.py` | CREATED -- life kernel domain Prometheus metrics (2 counters + 1 gauge) |
| 6 | `tests/projects/test_audit_project_id.py` | MODIFIED -- 33 tests across 5 test classes |
| 7 | `docs/setup-evidence/P19/evidence/P19-010/verification.md` | This file |
| 8 | `docs/setup-evidence/P19/evidence/P19-010/auditor-gate.md` | Gate checklist |

---

## 3. Design Decisions

### 3.1 `AuditWriter.write_event(... project_id=None)`

- Added `project_id: uuid.UUID | None = None` as keyword-only parameter.
- When set: `project_id` stored as string inside `event_payload` JSONB.
- When `None`: payload has no `project_id` key (legacy compat).
- `AuditEvent` dataclass gained `project_id` field with `None` default.
- Hash computation includes `project_id` in payload when present -- chain integrity preserved.

### 3.2 `DurabilityBackend.record(... project_id=None)`

- Abstract method updated with `project_id: uuid.UUID | None = None`.
- `PostgresAuditJournal.record`: stamps `project_id` into stored JSONB entry.
- `InMemoryJournal.record`: stamps `project_id` into stored dict entry.
- All callers passing `record(entry)` unchanged -- default `None` is backward compat.

### 3.3 `ConsentAuditor.log_consent_event(... project_id=None)`

- Added `project_id: uuid.UUID | None = None` keyword-only parameter.
- When set: `project_id` injected into `metadata_jsonb` before serialization.
- Global safety events (HARD_STOP, DNR) callers MUST pass `project_id=None`.

### 3.4 Prometheus metrics with `project_id="default"` label

- `src/loops/metrics.py`: 3 metric families (counter, counter, histogram) all with `project_id` label.
- `src/life_kernel/metrics.py`: 3 metric families (counter, gauge, counter) all with `project_id` label.
- Default label value `"default"` for legacy/global observability.

---

## 4. Validation Results

### 4.1 Forbidden pattern grep -- PASS

| Pattern | Matches |
|---------|---------|
| `# type: ignore` | 0 |
| `as any` | 0 |
| bare `except:` | 0 |

### 4.2 Test suite -- 33 passed

```
python -m pytest tests/projects/test_audit_project_id.py -v
```

| Test class | Count | Scope |
|------------|-------|-------|
| TestAuditProjectId | 3 | project_id in audit events, NULL for global, chain integrity |
| TestMetricsProjectIdLabel | 10 | all 6 metrics have project_id label, default value, increment |
| TestDurabilityProjectId | 3 | abstract signature, InMemoryJournal store + legacy |
| TestKGConsentAuditProjectId | 2 | signature, safety event types |
| TestForbiddenPatterns | 15 | 5 files x 3 patterns |

### 4.3 Hard rejection checks -- ALL PASS

| Criterion | Status |
|-----------|--------|
| Audit row without project_id (project event) | PASS -- write_event stores project_id in payload |
| Global safety event with non-null project_id | PASS -- default None, test verifies NULL |
| Hash chain broken | PASS -- chain test passes with mixed legacy/new |
| `# type: ignore` / `as any` / bare except | PASS -- 0 matches across 5 files |
| Evidence missing | PASS -- verification.md + auditor-gate.md present |

---

**P19-010 verdict: PASS.**
