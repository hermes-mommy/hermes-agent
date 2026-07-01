# P19-009 Verification: Consent/Surveillance Scoped Policy Enforcement

**Wave:** P19-009
**Date:** 2026-06-25
**Status:** PASS
**Reviewer:** Guinevere (implementation agent)

---

## 1. Scope

Implement project-scoped consent enforcement for surveillance and non-surveillance consent scopes.  Additive change: `project_id=None` default preserves legacy behaviour.

---

## 2. Files Modified / Created

| # | File | Status |
|---|------|--------|
| 1 | `src/surveillance/consent_gate.py` | MODIFIED |
| 2 | `src/surveillance/consumer.py` | MODIFIED |
| 3 | `src/surveillance/models.py` | NO CHANGE (nullable project_id from P19-003) |
| 4 | `src/discord/cmd_consent.py` | MODIFIED |
| 5 | `tests/projects/test_consent_isolation.py` | CREATED |
| 6 | `docs/setup-evidence/P19/evidence/P19-009/verification.md` | CREATED |
| 7 | `docs/setup-evidence/P19/evidence/P19-009/auditor-gate.md` | CREATED |

---

## 3. Design Decisions

### 3.1 `check_consent(scope, project_id=None)` signature

- Added `project_id: uuid.UUID | None = None` as keyword-only after `scope`.
- When `project_id` is set: project-scoped row wins over global.
- When `project_id` is `None`: legacy behaviour (no project filter).
- `ConsentCheckResult` gained `project_id` field (default `None`).

### 3.2 SAFE-03: `consent.autonomy.high_blast` per-project

- Registered in `VALID_CONSENT_SCOPES`.
- NOT in `_GLOBAL_ONLY_SCOPES` — supports project scoping.
- NOT in `_PROJECT_ONLY_SCOPES` — allows global fallback.
- Project-scoped rows take precedence over global.

### 3.3 SAFE-04: HARD STOP remains global

- HARD STOP is not a consent scope (handled by `safe_mode.py` / `life_kernel`).
- Not in `_ALL_VALID_SCOPES` — cannot be project-scoped via consent_gate.
- `SurveillanceSafeModeGuard` remains project-agnostic.
- Tests verify no bypass via project_id.

### 3.4 ARCH-04: `consent.memory.cross_project` (global-only)

- Registered in `VALID_CONSENT_SCOPES`.
- In `_GLOBAL_ONLY_SCOPES` — `project_id` parameter ignored if passed.
- Logged as warning when project_id is non-None.
- Always queries `project_id IS NULL`.

### 3.5 SEC-04: `consent.emergency.break_glass_project` (project-scoped, time-bound)

- Registered in `VALID_CONSENT_SCOPES`.
- In `_PROJECT_ONLY_SCOPES` — no global fallback.
- In `_TIME_BOUND_SCOPES` with 4-hour max age.
- `_query_ledger` filters `granted_at >= cutoff` for time-bound scopes.

### 3.6 Cache key: project-scoped

- `_build_cache_key(scope, project_id)` returns `consent:surveillance:<scope>:<uuid>` when project_id is set.
- Legacy key `consent:surveillance:<scope>` preserved when project_id is None.
- Cache TTL unchanged (300s).

### 3.7 Consumer: project_id extracted from event

- `process_event` extracts `project_id` from event dict (P19-003 migration column).
- Invalid UUID strings logged as warning, proceed with `project_id=None`.
- `project_id` passed to both `check_consent()` and `_store_event()`.

### 3.8 Discord commands: project arg

- `/consent action:grant/revoke category:<str> project:<str>` optional project param.
- Grant/revoke keys are `category:project` when project is set.
- View filtered by project if set.

---

## 4. Validation Results

### 4.1 Forbidden pattern grep (PASS)

| Pattern | Matches |
|---------|---------|
| `# type: ignore` | 0 |
| `as any` | 0 |
| bare `except:` | 0 |

### 4.2 Test suite

```bash
python -m pytest tests/projects/test_consent_isolation.py -v
```

Result: PASS (all tests)

### 4.3 Hard rejection checks

| Criterion | Status |
|-----------|--------|
| Consent not per-project | PASS — project_id param added, project-scoped query |
| HARD STOP scoped | PASS — not a consent scope, safe_mode remains global |
| Project pause == HARD STOP | PASS — pause only blocks that project |
| Safety scopes project-scoped | PASS — persona.normal/escalated/y5 NOT in consent_gate |
| Autonomy auto-resume paused project | PASS — paused returns allowed=False |
| Project autonomy touches core | PASS — high_blast per-project, no global override |
| `# type: ignore` / `as any` / bare except | PASS — 0 matches |
| Evidence missing | PASS — verification.md + auditor-gate.md |

---

## 5. New Scope Registry

| Scope | Project-scoping | Time-bound | Global-only |
|-------|----------------|------------|-------------|
| `surveillance.app_usage` | project + global fallback | No | No |
| `surveillance.location` | project + global fallback | No | No |
| `surveillance.notifications` | project + global fallback | No | No |
| `surveillance.clipboard` | project + global fallback | No | No |
| `surveillance.email` | project + global fallback | No | No |
| `consent.autonomy.high_blast` | project + global fallback | No | No |
| `consent.memory.cross_project` | global only | No | **Yes** |
| `consent.emergency.break_glass_project` | project only | **4 hours** | No |

---

**P19-009 verdict: PASS.**
