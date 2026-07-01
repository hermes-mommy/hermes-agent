# P19 Research: P21/P22/P17 Integration Dependency Map

**Status:** ✅ COMPLETE
**Date:** 2026-06-25
**Author:** Guinevere (parent-authored from scout reports + direct reads)
**Scope:** How P19 integrates with P21 Voice, P22 Life Integration Hub, and P17 Cross-Device Sync.

> **HISTORICAL / SUPERSEDED BY P20 WAIVER (2026-06-25):** This research was authored when P20 was in "PRODUCTION PASS HOLD (soak)". References below to "P20 PRODUCTION PASS", "after P20 PRODUCTION PASS", and "BLOCKED until P20 pass" are **historical context**. P20's final status is `P20 EARLY PRODUCTION ACCEPTANCE — OPERATOR WAIVED 24H SOAK — PASS WITH ACCEPTED RISK`; the P20 axis is **satisfied by operator waiver**, not by a soak. P19 lands by operator approval (not after a P20 soak). See `docs/setup-evidence/P19/evidence/p20-waiver-gate-sync.md`. The body is retained unchanged for traceability.

---

## 1. Executive Summary

P19 is the **foundation** that P21 (Voice), P22 (Life Integration Hub), and P17 (Cross-Device Sync) build upon for project-aware behavior. P19 owns the project registry (`projects.project_registry`); P21/P22/P17 read it and tag their data with `project_id`. Dependency ordering: P19 lands **after** P20 PRODUCTION PASS (don't disturb the soak) and **before** P21/P22 implementation (so they're project-aware from day one). P17 can land independently but references `project_id` once P19 exists.

---

## 2. P21 Voice Dependency

From P21 plan §P19 forward-compat:
- P21 voice episodes carry a nullable `project_id` (forward-compat seam) so P19 can partition later without a backfill.
- P21 code is namespace-agnostic (`project_id=None` default).

**P19 must provide:**
- Accept `project_id` in voice episodes (P21 already writes nullable; P19 makes it meaningful).
- Partition voice memory by `project_id` (voice episodes in `memory.episodes` with `source='voice'` + `project_id`).
- `/voice project <name>` switcher OR voice channel per project.

**P21 does NOT depend on P19 landing first** — nullable `project_id` works without P19. But once P19 lands, voice memory is properly partitioned.

---

## 3. P22 Life Integration Dependency

From P22 plan §P19 Project-Namespace Dependency Map:
- Default namespace `default` (matches P19's `default` project).
- Template `p22:<domain>:<provider>:<resource-id>`.
- Project-qualified `<project>:p22:<domain>:<provider>:<resource-id>`.
- **P19 owns the project registry; P22 reads it read-only.**
- Collision-resolution policy documented (composite key `(namespace, provider, resource_id)`).
- No P22 code may create/rename/delete P19 namespaces.

**P19 must provide:**
- `projects.project_registry` table (the registry P22 reads).
- Namespace resolution API: `resolve_project(slug) -> project_id`.
- `project_id` on all P22 tables (`audit.integration_api_log`, P22 world-model tables).
- Migration path: P22 Phase 0 (all `default`) → Phase 1 (optional `project_id` column) → Phase 2 (backfill `default`) → Phase 3 (explicit namespace required).

P22's documented migration path aligns with P19's backfill-to-`default` strategy.

---

## 4. P17 Cross-Device Sync Dependency

From PROGRESS.md: P17 Cross-Device Sync is ⏳ TBD.
- P17 syncs state across devices (VPS, Android, Windows, wearable).
- `project_id` must be part of the sync key so a device's project context syncs correctly.
- P19 must provide: `project_id` in sync messages; project registry as the source of truth for project identity.

P17 can land independently of P19, but should reference `project_id` once P19 exists (otherwise it syncs only global state).

---

## 5. P20 Life-Kernel Dependency

(Covered in `p19-p20-life-kernel-dependency-map.md` — summarized here.)
- P19 makes life_kernel project-aware (thread_id, state, models, journal, dashboard).
- BLOCKED on P20 PRODUCTION PASS for life_kernel file changes.
- Additive-only changes; HARD STOP stays global.

---

## 6. Dependency Ordering

```text
P20 PRODUCTION PASS (LK-017 soak complete)
        │
        ▼
P19-001..004 (governance, registry, schema, memory/KG partition)  ← can start, NEW files + additive migrations
        │
        ▼
P19-005 (life-kernel project context)  ← BLOCKED until P20 pass (touches P20 files)
        │
        ▼
P19-006..012 (sensors, Discord, agent-loop, consent, observability, migration, deploy)
        │
        ▼
P19 DEFINITION/IMPLEMENTATION COMPLETE
        │
        ▼
P21 implementation (project-aware from day 1)
P22 implementation (project-aware from day 1, reads P19 registry)
P17 implementation (references project_id)
```

**P19 should land AFTER P20 PRODUCTION PASS and BEFORE P21/P22 implementation.**

---

## 7. Voice + Project Switcher

- P21 voice turns: Faiz selects project mid-conversation via `/voice project <name>` OR voice channel per project (`#guinevere-voice-work`).
- Voice episodes tagged with active `project_id`.
- Proactive voice brief (morning brief) is per-project: "Good morning — for project work, you have 3 calendar events today...".

---

## 8. P22 + Voice + Project

- P22 integration data surfaced via voice must label with `project_id`.
- "Guinevere, what's on my calendar?" → resolves to active project's calendar (P22 `p22:calendar:google:{resource}` scoped to project).
- Sensitive content (`sensitivity=confidential/intimate`) always `require_confirm=true` (P22 voice-consent gating).

---

## 9. Cross-Project Integration Rules

- By default, project A's calendar event does NOT trigger project B's work.
- Cross-project triggers require an explicit cross-project rule + `consent.autonomy.cross_project` scope (Faiz-approved, audited).
- Example: "When project work has a deploy failure, notify project personal" — explicit rule, audited.

---

## 10. Hard Rejection: P21/P22 Ignored

- Plan must explicitly address P21 integration (voice episodes `project_id`, `/voice project` switcher). ✅ (P19-006, P19-008)
- Plan must explicitly address P22 integration (registry read-only, `project_id` on P22 tables, namespace resolution). ✅ (P19-002, P19-006, P19-009)

---

## 11. Hard Rejection: P20 Disturbance

- P19 plan must NOT schedule changes to P20 life_kernel until P20 PRODUCTION PASS. ✅ (P19-005 explicitly BLOCKED on P20 pass; P19-001..004 are NEW files + additive migrations that don't touch life_kernel runtime.)

---

## 12. Collision Scan Across Phases

Files shared between P19 and P21/P22:
- `src/life_kernel/state.py` — P19 adds `project_id` NotRequired field; P21 adds voice fields. Both additive. **Resolve: P19 goes first; P21 rebases.**
- `src/memory/models.py` — P19 adds `project_id` column; P21 adds nullable `project_id` on Episodes (same column!). **Resolve: P19 owns the `project_id` column; P21's nullable seam is satisfied by P19's column.**
- `docs/10-governance/17-ADR_Index_v1.0.md` — P19 ADR + P21 ADR + P22 ADR. **Resolve: parent-only single-owner edit; P19 pointer added in P19-001, P21/P22 pointers already exist.**
- `alembic/versions/` — P19 `p19_001`, P21 `p21_001` (down_revision `p20_001`), P22 `p22_001`. **Resolve: migration chain P19 → P21 → P22 (P21/P22 rebased onto P19 head).**

---

## 13. Parallelism Map

- P19-001..004 can parallel with P21 wave 1 (NEW files only, no LOCKED P20 files).
- P19-005..008 must wait for P20 pass (touch life_kernel / shared files).
- P21/P22 implementation waits for P19 to land (for project-aware schema).
- P19-009..012 (consent, observability, migration, deploy) depend on P19-005..008.

---

## 14. Migration Ordering

```text
p20_001_life_kernel_schema (current head)
        │
        ▼
p19_001_project_namespaces  (P19: projects.project_registry + project_id columns)
        │
        ▼
p21_001_voice_stream  (P21: nullable project_id → now references P19 projects table)
        │
        ▼
p22_001_integrations  (P22: project_id NOT NULL default 'default', references P19 projects)
```

P21's nullable `project_id` seam becomes a real FK to `projects.project_registry` after P19 lands.

---

## 15. Rollback Interaction

- Rollback P19 (`alembic downgrade p20_001`) → P21/P22 base rows are preserved but lose their `project_id` partitioning data (the column is dropped). P19's own `project_id`/`project_scope` data is lost on downgrade; only base (non-P19) row data is preserved. Re-running P19 re-adds + re-backfills.
- P21/P22 code degrades gracefully (project_id=None → default behavior).
- No data loss on P19 rollback.

---

## 16. Evidence Interaction

- P19 evidence root: `docs/setup-evidence/P19/`.
- P21 evidence root: `docs/setup-evidence/P21/`.
- P22 evidence root: `docs/setup-evidence/P22/`.
- Independent; no collision.

---

## 17. Hard Rejection Checks

1. **P21 dependency ignored:** ✅ MITIGATED — voice episodes `project_id`, `/voice project` switcher, P21 migration rebased onto P19.
2. **P22 dependency ignored:** ✅ MITIGATED — P22 reads P19 registry read-only, `project_id` on P22 tables, namespace resolution API, migration chain.
3. **P20 disturbance:** ✅ MITIGATED — P19-005 BLOCKED on P20 pass; P19-001..004 additive only.
4. **Migration chain breaks P21/P22:** ✅ MITIGATED — P19 → P21 → P22 ordering; nullable columns preserve data on rollback.

---

## 18. Conclusion

P19 is the foundation for P21/P22/P17 project-awareness. P19 owns the project registry; P21/P22/P17 read it and tag data with `project_id`. P19 lands after P20 PRODUCTION PASS and before P21/P22 implementation. Migration chain: P19 → P21 → P22. Collision resolution: P19 owns shared schema additions (project_id column, state.py field); P21/P22 rebase onto P19. Rollback is non-destructive (nullable columns).
