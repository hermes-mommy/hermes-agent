# P19 Round-1 Audit — Architecture

**Auditor:** architecture
**Date:** 2026-06-25
**Scope:** Namespace flow, wrapper correctness, thread_id strategy, additive-only design, integration-not-sidecar.

## Verdict: PASS (with conditions)

## Findings

### ARCH-01 [HIGH] ADR number collision
**Finding:** Plan §Wave P19-001 proposes `adr/ADR-039-multi-project-context.md`. ADR-039 is the reserved backlog slot for "Consent & Revocation Policy" (`docs/10-governance/17-ADR_Index_v1.0.md:127`). Using it for multi-project context violates ADR maintenance rules ("Do not reuse ADR numbers") and collides with the planned consent ADR.
**Impact:** ADR index inconsistency; future consent ADR blocked.
**Fix:** Use the next free number. Implemented ADRs go to ADR-050 (KG). Backlog ADR-039..051 are reserved. Next free: **ADR-052** (ADR-051 = Compliance & Data Residency). P19 ADR = `ADR-052-multi-project-context.md`.
**Wave:** P19-001.

### ARCH-02 [MEDIUM] `_ADAPTERS` global in graph.py
**Finding:** `src/life_kernel/graph.py:33` has `_ADAPTERS: dict[str, Any] = {"kg": None, "memory": None, "journal": None}` as module-level global. Plan P19-005 threads `project_id` into graph state but does not address how per-project adapter instances coexist with this global.
**Impact:** If two projects' graphs share the global `_ADAPTERS`, recall could leak (adapter returns wrong project's data).
**Fix:** P19-005 scaffold must specify: either (a) per-project adapter instances injected at `create_life_mind_graph(..., project_id)` (no shared global), or (b) adapter `recall(context)` reads `project_id` from context (already planned). Document the chosen approach explicitly.
**Wave:** P19-005.

### ARCH-03 [LOW] Dashboard top-N bound unspecified
**Finding:** Plan §Dashboard/Log Model says "bounded to top-N active projects" but does not specify N or eviction policy.
**Fix:** P19-007 scaffold: specify N=3 (matches log channel top-3), LRU eviction for dashboards beyond N.
**Wave:** P19-007.

### ARCH-04 [LOW] Cross-project recall API consent scope undefined
**Finding:** Plan mentions `recall_across_projects(query, project_ids=[...])` requiring `consent.memory.cross_project` scope but this scope is not in the ConsentRevocationPolicy §4 taxonomy.
**Fix:** P19-009 scaffold: add `consent.memory.cross_project` to the taxonomy as a new global scope (Faiz-approved, audited), or reuse `consent.autonomy.high_blast` for cross-project recall. Document decision.
**Wave:** P19-009.

## Summary
Architecture is sound: namespace flows everywhere via `project_id`; LangGraph thread_id reuse is correct; additive-only design is correct; integration-not-sidecar (threads through core, not a sidecar). The ADR collision (ARCH-01) is the only HIGH finding and is easily fixed. Conditions are documentation/specification gaps, not design flaws.

## Hard Rejection Check
- Namespace flows to memory/KG/audit/agenda/dashboard/sensors/actions: ✅ (every wave threads project_id)
- Integration not sidecar: ✅ (threads through core memory/loop/life_kernel)
- Additive-only: ✅ (NotRequired fields, nullable columns, feature flag)
