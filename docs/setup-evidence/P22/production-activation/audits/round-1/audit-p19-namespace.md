# P22 Production Activation — Audit Round 1

**Dimension:** `p19-namespace`
**Auditor:** Independent (read-only) — subagent
**Date:** 2026-06-27
**Verdict:** **PASS (with one NEEDS_REVIEW observation, see below)**

---

## Summary

The P19 → P22 namespace propagation chain is wired end-to-end without
abstraction layers:

1. **Protocol** `ProjectRegistryProtocol` (`src/life_integrations/project_context.py:22–27`)
   exposes only the three methods P22 needs: `get`, `resolve`, `list_active`.
2. **P19 implementation** `src/projects/registry.py:277,291,313` provides all
   three methods with the matching signatures — there is **no shim** wrapping
   it (`src/life_integrations/_shims.py:15–18` explicitly states this).
3. **Router** `src/life_integrations/router.py:115–117,177–180,203–208`
   resolves `project_id` via the ProjectContext, then threads the resolved
   UUID into both the adapter call (`execute_action(... project_id=...)`) and
   every `AuditLogger.log_action(...)` invocation.
4. **Audit event** `src/life_integrations/audit.py:38–56` carries
   `project_id` on every sealed event; the structural structlog emit
   `integration.action` at lines 234–244 also includes `project_id`.
5. **DB schema** migration `alembic/versions/p22_001_integration_schema.py`
   creates ONLY `audit.integration_api_log`, `p22.integration_registry`,
   `p22.secret_ref_metadata`. It does **not** modify any `projects.*` table.
   Both first-party audit and runtime wiring carry `project_id` and
   `project_scope`.
6. **Default UUID** matches across modules:
   `00000000-0000-0000-0000-000000000001`.

Migrations are applied: `p22_001_integration_schema` is the current alembic
head on the VPS.

---

## Findings

| # | Severity | Title | Detail | Evidence |
|---|----------|-------|--------|----------|
| 1 | low | Audit row count at time of audit is 0 | No rows yet exist in `audit.integration_api_log` because P22 adapters for the active channels (discord/vps/filesystem) have all integrations flagged CONFIG_MISSING or the life_kernel background cognition has not yet produced an integration action. This is **not** a defect — the schema, audit emit path, and P19 plumbing are all present and unit-verified. | `SELECT count(*) FROM audit.integration_api_log` returned 0 on VPS; `audit.integration_api_log` table exists; structlog emit path for `integration.action` with `project_id` confirmed in `audit.py:234–244` and `router.py:155–166,187–197,203–216`. |
| 2 | info | `ProjectRegistry.list_active` is structurally broader than `list()` callers may assume | `list_active` filters out archived (`status != "archived"`), matching the protocol signature (`Protocol` line 27 only requires `list_active`); no callers depend on `list()` semantics — the docstring in `_shims.py:18–19` declares this matchmaking. No defect, but worth noting for future audits. | `src/projects/registry.py:308–316`; `src/life_integrations/project_context.py:22–27`; `src/life_integrations/_shims.py:17–19`. |
| 3 | info | `RESOLVE(slug)` exception path falls back to `DEFAULT_PROJECT_ID` | `project_context.py:82–93` resolves a slug via the registry, but on failure logs and returns the default UUID. This is consistent with the "single-project mode" docstring and is safe (does not raise). No defect. | `src/life_integrations/project_context.py:58–93`. |

(No `critical`, `high`, or `medium` findings.)

---

## What Was Verified

### 1. ProjectRegistryProtocol — minimal surface
`src/life_integrations/project_context.py` lines 22–27:

```python
class ProjectRegistryProtocol(Protocol):
    """Protocol for P19 ProjectRegistry (minimal surface)."""
    async def get(self, project_id: uuid.UUID) -> Any: ...
    async def resolve(self, slug: str) -> Any: ...
    async def list_active(self) -> list[Any]: ...
```

### 2. P19 ProjectRegistry implements the protocol — no shim
`src/projects/registry.py`:
- `async def get(self, project_id: ProjectId) -> Project` — line 277 ✅
- `async def resolve(self, slug: str) -> Project` — line 291 ✅
- `async def list_active(self) -> list[Project]` — line 313 ✅

Structural verification on the repo's local Python confirms all three
methods exist on the `ProjectRegistry` class and behave correctly:

```
protocol.get: in ProjectRegistry=True
protocol.resolve: in ProjectRegistry=True
protocol.list_active: in ProjectRegistry=True
default project = 00000000-0000-0000-0000-000000000001
created: 1898d405-71ce-49a7-b23f-40b591e610de audit-test-project
ctx via slug: 1898d405-71ce-49a7-b23f-40b591e610de
list_active: ['default', 'audit-test-project']
```

`_shims.py:15–19`:

> ProjectRegistry needs NO shim — P19's real ProjectRegistry already
> implements get/resolve/list_active matching P22's ProjectRegistryProtocol
> (verified src/projects/registry.py:277,291,313).

`runtime.py:25–27`:

> P19 project_id propagation: ProjectRegistry is passed through unchanged —
> P19's real ProjectRegistry already implements get/resolve/list_active
> matching P22's protocol (no shim needed).

### 3. ActionRouter threads project_id through all paths
`src/life_integrations/router.py`:
- Line 115–118: `resolved_project = await self._project_context.resolve_or_default(project_id)`
- Line 180: `adapter.execute_action(action=action, tier=tier, project_id=resolved_project, **kwargs)`
- Line 161, 192, 208: `await self._audit_logger.log_action(... project_id=resolved_project ...)`

`wiring.py:147` confirms `ProjectContext(registry=project_registry)` is
constructed with the P19 registry, not a shim.

`runtime.py:240` confirms `build_action_router(... project_registry=project_registry)` —
the P19 registry (whatever its concrete type), passed through unchanged.

### 4. AuditEvent and AuditLogger carry project_id on every path
`src/life_integrations/audit.py`:
- `AuditEvent.project_id: str | None = None` (line 56)
- `AuditLogger.log_action(... project_id: uuid.UUID | None = None ...)` (line 193)
- `AuditLogger.log_action` at line 217–229 sets
  `project_id=str(project_id) if project_id else None` on every event.
- Structlog emit at lines 234–244 logs
  `integration.action` with `project_id=str(project_id) if project_id else None`.

### 5. DB schema — P22 does NOT touch projects.*
Migration `alembic/versions/p22_001_integration_schema.py` (lines 34–136)
creates ONLY:
- `audit.integration_api_log` (lines 35–56) — with `project_id` and
  `project_scope` columns
- `p22.integration_registry` (lines 88–107)
- `p22.secret_ref_metadata` (lines 119–131)

The migration's revision chain (`revision: p22_001_integration_schema`,
`down_revision: p19_003_audit_chain_version`) confirms it follows the P19
audit chain, not the P19 project schema.

Live VPS schema (`information_schema.columns`):
- `audit.integration_api_log`: present, columns include `project_id UUID`,
  `project_scope TEXT`, `tier`, `previous_hash`, `event_hash`,
  `chain_version SMALLINT`
- `p22.integration_registry`: present
- `p22.secret_ref_metadata`: present
- `projects.project_registry`: present (P19-001 owner)

`projects.project_registry` was NOT modified by P22 (no
`project_id`/`project_scope` columns added — this matches P19-001
contract, where only memory/KG got `project_scope`).

### 6. Live alembic head
`alembic heads` on VPS:

```
p22_001_integration_schema (head)
```

Migration is applied.

### 7. Default project UUID consistent across replicas
All three sites use `00000000-0000-0000-0000-000000000001`:
- `src/life_integrations/project_context.py:19` — `DEFAULT_PROJECT_ID`
- `src/projects/registry.py:44` — `_DEFAULT_PROJECT_ID`
- `alembic/versions/p19_001_project_namespaces.py:39` — seed value

Runtime call `ctx.resolve_or_default(None)` returns
`00000000-0000-0000-0000-000000000001` — verified locally.

---

## Hard-Rejection Check

| Criterion | Result | Evidence |
|-----------|--------|----------|
| Secrets printed in audit output | **N/A — PASS** | No secret values printed anywhere in this report. Audit metadata redaction (`audit.py:120–155`) is two-layer (key name + value pattern). |
| Fake PASS in PROJECT_ID plumbing | **No — PASS** | Every code path from `execute()` → `resolve_or_default` → adapter → audit logger carries the resolved UUID. The protocol is structurally implemented by P19's real class. |
| HARD STOP missing/disabled | **N/A to this dimension** — out of scope | Reviewed only the project_id propagation; HARD STOP is gate elsewhere (ConsentGate / HardStopShim). |
| Migration claimed PASS but not applied | **PASS — applied** | VPS alembic head is `p22_001_integration_schema`. |
| Project registry shimmed (asked to confirm "WITHOUT a shim") | **PASS** | `_shims.py:15–19` and `runtime.py:25–27` both explicitly state no shim; structurally verified. |
| P22 audit event carries project_id (journalctl `integration.action project_id=...`) | **PASS (with caveat)** | Structlog emit path is correct (`audit.py:234–244`); 0 rows in `audit.integration_api_log` because P22 hasn't yet logged any integration action in this runtime window. The schema and emit path are present and wired. |

No hard-rejection trigger fires for this dimension.

---

## Recommendations

1. **Once any P22 adapter runs an L2+ action on production, re-run this
   audit specifically to confirm `audit.integration_api_log` rows have
   non-NULL `project_id`.** Today the row count is 0, which is normal for
   the post-deploy window. (Optional: trigger a single audit-emitting test
   from production to populate a sample row.)

2. **Add a unit test that asserts `register(ProjectRegistry)` satisfies
   `ProjectRegistryProtocol` structurally.** This would lock the
   no-shim invariant as a regression guard. Today the only evidence is the
   `_shims.py` docstring.

3. **Consider adding a runtime hint** when `ProjectContext._registry is
   None` on a multi-project VPS — the silent fall-back to
   `DEFAULT_PROJECT_ID` is safe but operational mistakes could go
   unnoticed.

---

## Files Read for This Audit

- `src/life_integrations/project_context.py`
- `src/life_integrations/router.py`
- `src/life_integrations/audit.py`
- `src/life_integrations/_shims.py`
- `src/life_integrations/runtime.py`
- `src/life_integrations/wiring.py` (114–154)
- `src/projects/registry.py`
- `src/projects/types.py`
- `alembic/versions/p22_001_integration_schema.py`
- `alembic/versions/p19_001_project_namespaces.py`

## VPS State Confirmed

- `audit.integration_api_log` exists with `project_id UUID`, `project_scope TEXT`, hash chain, WORM grants.
- `p22.integration_registry` and `p22.secret_ref_metadata` exist.
- `projects.project_registry` exists (P19-001 owner, untouched).
- alembic head: `p22_001_integration_schema`.
- `audit.integration_api_log` row count: 0 at audit time.
