# P19 Round-1 Audit — Observability & Evidence

**Auditor:** observability-evidence
**Date:** 2026-06-25
**Scope:** project_id labels, audit project_id, hash chain, evidence roots.

## Verdict: PASS (with conditions)

## Findings

### OBS-01 [MEDIUM] Prometheus label cardinality on consent scope
**Finding:** Plan adds `project_id` label to metrics. But consent/surveillance metrics already have `scope`/`event_type` labels. Adding `project_id` multiplies cardinality by N projects. For bounded N (≤5 active), fine, but unbounded projects would explode.
**Fix:** P19-010 scaffold: cap metric cardinality — `project_id` label only for metrics where project is meaningful AND cap to active projects (paused/archived projects' metrics use `project_id="archived"` bucket or stop emitting). Document cardinality budget.
**Wave:** P19-010.

### OBS-02 [MEDIUM] Audit hash chain includes project_id — verify canonical payload
**Finding:** Plan says `event_hash = SHA256(canonical_payload_including_project_id + previous_hash)`. But the existing `audit.audit_trail` hash chain may not include `project_id` in its canonical payload today. Changing the canonical payload format breaks the existing chain.
**Impact:** Hash-chain verification failure for existing rows.
**Fix:** P19-010 scaffold: the canonical payload for NEW rows includes `project_id` (nullable → "global" string for global events). Existing rows' hashes are NOT re-verified against the new format (they keep their old hash). A chain-version field (`chain_version=1` for legacy, `=2` for P19) distinguishes. Document the versioning.
**Wave:** P19-010.

### OBS-03 [LOW] Per-project evidence root path
**Finding:** Plan says runtime projects get `evidence/projects/{project_id}/`. But no wave creates this convention.
**Fix:** P19-001 ADR: document the evidence root convention (`docs/setup-evidence/` for Guinevere-core phases, `evidence/projects/{project_id}/` for runtime projects). No code change needed (convention).
**Wave:** P19-001.

### OBS-04 [LOW] Soak metrics list
**Finding:** Plan lists soak metrics (`p19_projects_active`, etc.) but doesn't specify which Grafana dashboard renders them.
**Fix:** P19-010: add a `guinevere-p19-projects.json` Grafana dashboard (or add a panel to `guinevere-agent-loop.json`).
**Wave:** P19-010.

## Summary
Observability design is sound: `project_id` labels (bounded cardinality), audit `project_id` column, global hash chain, per-project evidence roots. The MEDIUM findings (OBS-01 cardinality cap, OBS-02 chain versioning) need documentation to avoid metric explosion and hash-chain breakage. Evidence root convention (OBS-03) is a doc-only addition.

## Hard Rejection Check
- Audit without project_id: ✅ MITIGATED (project_id on all audit sinks, nullable for global)
- Hash chain broken: ✅ MITIGATED after OBS-02 fix (chain versioning)
- Evidence roots undefined: ✅ MITIGATED (OBS-03 convention documented)
