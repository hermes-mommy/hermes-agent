# ADR-035 Compliance Re-Audit — Phase 4 Batch Plan v1.1

| Field | Value |
|-------|-------|
| Auditor | Oracle (ADR-035 Compliance) |
| Target | `docs/setup-evidence/phase-4/batch-plan-phase-4.md` v1.1 (1034 lines) |
| Previous Verdict | NEEDS REVIEW (7 findings, 0 FAIL) |
| Re-Audit Verdict | **PASS** |
| Date | 2026-06-05 |

## Previous Findings Resolution

| ID | Severity | Original Finding | Resolution | Verified |
|----|----------|-----------------|------------|----------|
| F-004 | CONDITIONAL | Phase 3 hard dependency not in ADR-035 | Preamble changed: "Phase 2 must PASS. Phase 3 recommended but not hard gate per ADR-035." §16 checklist updated. | ✓ RESOLVED |
| F-002 | ADVISORY | Tool-list inflation 24 vs 16 | P4-005 annotation maps 24 MCP operations to 7 canonical tools with explicit breakdown. | ✓ RESOLVED |
| F-003 | ADVISORY | Auth matrix granularity mismatch | BD-006 changed to single-source Python auth_matrix.py import. YAML auth_matrix marked reference-only. | ✓ RESOLVED |
| F-005 | ADVISORY | NFR-P05 latency baseline missing | P4-007 check #15 added. P4-008 latency regression test category added. | ✓ RESOLVED |
| F-006 | ADVISORY | Rollback missing hermes gateway stop | Universal kill-switch row added to §14. All 7 rollback procedures prefixed with `sudo systemctl stop hermes-gateway`. | ✓ RESOLVED |
| F-007 | ADVISORY | Runtime watchdog not in Phase 4 | Caveat #10 explicitly defers to Phase 7. Phase 4 compensates with startup gate + fail-closed hooks. | ✓ RESOLVED |
| F-001 | ADVISORY | Phase 2 shadow mode | Unchanged, still valid approach. | N/A |

## New Issues Check

| ID | Severity | Finding | Status |
|----|----------|---------|--------|
| N-001 | ADVISORY | manifest.yaml naming was inconsistent across P4-002 plugin structure (said plugin.yaml) and P4-006 startup gate (checked manifest.yaml). | Fixed in v1.1 post-audit patch — all references unified to manifest.yaml. |

No new BLOCKING or FAIL findings introduced.

## Cross-Reference Consistency

| Check | Result |
|-------|--------|
| ADR-035 Phase 4 dependency matches plan §0 | ✓ Both say Phase 2 required, Phase 3 recommended |
| ADR-035 16 tools matches plan tool count | ✓ 16 canonical tools, 24 operations annotated |
| ADR-035 rollback procedure matches plan §14 | ✓ Plan extends ADR-035 with hermes gateway stop prefix |
| ADR-035 auth matrix design matches plan BD-006 | ✓ Single-source Python import eliminates drift |
| NFR-P05 referenced in plan | ✓ P4-007 check #15 + P4-008 latency test |

## Recommendation

**PASS.** All 7 previous findings resolved. 1 new ADVISORY finding (manifest.yaml naming) was fixed in post-audit patch. Plan v1.1 is compliant with ADR-035 Phase 4 requirements.

## Footer

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-05 | Oracle | Initial re-audit analysis |