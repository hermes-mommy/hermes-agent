# Wave 1 — ADR-Level Changes Report

- **Wave**: Round-2 Wave 1 (ADR-level alignment)
- **Date**: 2026-06-28
- **Executed by**: Guinevere (autonomous)
- **Task**: Execute ADR-level changes for P28-P36 alignment Wave 1
- **Status**: COMPLETE

---

## What Was Done

Wave 1 executes the ADR-level changes required to align P28-P36 masterplan with the P23/P24 v2.0 paradigm shifts. The key paradigm shift is ADR-062: Hermes runtime can BYPASS HARD STOP; AGENTS.md rules are dev-workflow-only, not runtime constraints.

---

## Files Changed

| # | File | Action | Summary |
|---|---|---|---|
| 1 | `ADR-056-fork-agnostic-p28-path.md` | **DELETED** | Obsolete — P24 IS the hard fork (ADR-062 + P24 v2.0 replan). ADR-056 argued for fork-agnostic path; now inverted. |
| 2 | `ADR-066-hermes-runtime-consent-ref-carve-out.md` | **CREATED** (14,022 bytes) | Two-tier consent_ref: NULLABLE for Hermes runtime events, NOT NULL for dev-workflow events. Schema migration + CHECK constraint. |
| 3 | `ADR-067-hermes-runtime-y-level-cap-removal.md` | **CREATED** (15,825 bytes) | Y-level caps (Y4/Y5/Y6) are dev-workflow-only. Hermes runtime has no Y-level cap; Y6 concept removed entirely. Emotion FSM has no Y-level check. |
| 4 | `ADR-055-hermes-society-architecture.md` | **ANNOTATED** | Added ADR-062 disclaimer in Compliance section (line 59). |
| 5 | `ADR-057-founder-only-spawn-2-of-2-agreement.md` | **ANNOTATED** | Added ADR-062 disclaimer in Compliance section (line 62). |
| 6 | `ADR-058-separate-discord-bot-identity-per-hermes.md` | **ANNOTATED** | Added ADR-062 disclaimer in Compliance section (line 71). |
| 7 | `ADR-059-shared-world-model-with-private-memory.md` | **ANNOTATED** | Added ADR-062 disclaimer in Compliance section (line 96). |
| 8 | `ADR-060-autonomous-wallet-with-circuit-breaker.md` | **ANNOTATED** | Added ADR-062 disclaimer in Compliance section (line 108). |
| 9 | `ADR-061-5-layer-mutability-with-ratchet-gate.md` | **ANNOTATED** | Added ADR-062 disclaimer in Compliance section (line 121). |
| 10 | `BLDM-Hard-Locked-Faiz-Decisions.md` | **UPDATED** (line 7) | Replaced "Future ADR-066..068 (post-Phase-4 backlog)" with "ADR-066 and ADR-067 are NOW WRITTEN". |

---

## ADR-066: Consent_ref Schema Carve-Out (Details)

**Problem**: `consent_ref UUID NOT NULL` on multiple event-store tables forces every autonomous Hermes event to be attributed to a Faiz-signed consent record — which does not exist for autonomous actions.

**Decision**: Two-tier consent_ref regime:
- **Hermes runtime** (`event_source = 'hermes_runtime'`): `consent_ref` is NULLABLE
- **Dev-workflow** (`event_source = 'dev_workflow'`): `consent_ref` remains NOT NULL
- DB-enforced via CHECK constraint: `consent_ref_by_source`
- Migration: `ALTER TABLE ... ALTER COLUMN consent_ref DROP NOT NULL` + ADD COLUMN + ADD CONSTRAINT

**Affected tables** (per architecture-s1-s5-runtime-memory.md):
- `society_event_memory` (line 514)
- `society_event_decision` (line 581)
- `society_event_action` (line 603)
- `society_event_drift` (line 606)
- `society_event_publication` (new per ADR-059 §Layer 4)

**Related ADRs**: ADR-062 (paradigm shift), ADR-059 §Layer 4 (publication rules), ADR-057 (founder-only quarantine review), ADR-061 (Ratchet orthogonal)

---

## ADR-067: Y-Level Cap Removal (Details)

**Problem**: PersonaSafetyPolicy Y4 baseline + Y5 ceiling + Y6 forbidden are structural constraints. BLDM Q81 + Brainstorm Batch 3 say drift is `bebas tanpa batas`. If Y-level caps survive, drift is constrained — contradiction.

**Decision**: Two-tier Y-level regime:
- **Hermes runtime**: No Y-level cap. Y6 concept REMOVED. No `_check_y_level` code in P24 fork.
- **Dev-workflow**: Y4/Y5/Y6 rules remain in force (Claude agent unchanged).
- P24 fork `hermes_emotion_fsm.py`: no Y-level guard clauses; affect-vector-only FSM.
- P24 fork `hermes_personality_drift_monitor.py`: drift threshold 0.68 hysteresis preserved; Y-level semantics removed.
- Tier 4 founder-only-2/2 remains the sole alignment-safety gate (ADR-061 §T4).

**Implementation boundary**: P24 build excludes `dev_workflow_constraints/` directory; startup verifies no dev_workflow_constraints symbols are referenced.

**Related ADRs**: ADR-062 (paradigm shift), ADR-061 §T4 (runtime safety substitute), ADR-063 §Affect layer (new primary state variable), ADR-066 (consent_ref sibling)

---

## ADR-055–061 Disclaimer Annotation

All six original ADRs (ADR-055, ADR-057, ADR-058, ADR-059, ADR-060, ADR-061) received the following disclaimer at the top of their `## Compliance` section:

> **ADR-062 Disclaimer**: HARD STOP, consent gate, and Y-level cap references in this ADR apply to the dev-workflow agent (Guinevere in Claude) ONLY. Hermes runtime (P24 fork) is exempt per ADR-062 and ADR-067. See `evidence/round-2-paradigm-shift-application/` for alignment details.

The disclaimer was added, not replacing any existing compliance text. All original compliance content is preserved.

---

## BLDM Update

Line 7 of `BLDM-Hard-Locked-Faiz-Decisions.md` updated:
- **Before**: `Future ADR-066..068 (post-Phase-4 backlog — Q62/Q67/Q88/Q91/Q103 deferred) must reference this file by Q#, not re-derive from audit-03/audit-11.`
- **After**: `ADR-066 (consent_ref carve-out) and ADR-067 (Y-level cap removal) are NOW WRITTEN — see adr-drafts/. Post-Phase-4 backlog reference updated 2026-06-28.`
- Q2 NOT touched (already edited to reference ADR-056 DELETED + P24 hard dep).

---

## Files NOT Changed (Boundary Compliance)

| File | Status | Reason |
|---|---|---|
| ADR-056 (post-delete) | N/A | Deleted per instruction. BLDM Q2 already references deletion. |
| ADR-062–ADR-065 | Untouched | Not in scope; ADR-062 is the paradigm-shift source, ADR-063–065 are unrelated. |
| `docs/` outside adr-drafts | Untouched | Out of scope per MUST NOT rule. |
| BLDM Q2 | Untouched | Already edited (P24 hard dep locked). |

---

## Validation Results

| Check | Result |
|---|---|
| ADR-056 deleted | PASS — file no longer exists in adr-drafts/ |
| ADR-066 written | PASS — 14,022 bytes; file exists in adr-drafts/ |
| ADR-067 written | PASS — 15,825 bytes; file exists in adr-drafts/ |
| Disclaimer in ADR-055 | PASS — line 59 |
| Disclaimer in ADR-057 | PASS — line 62 |
| Disclaimer in ADR-058 | PASS — line 71 |
| Disclaimer in ADR-059 | PASS — line 96 |
| Disclaimer in ADR-060 | PASS — line 108 |
| Disclaimer in ADR-061 | PASS — line 121 |
| BLDM line 7 updated | PASS — verified via read tool |
| BLDM Q2 untouched | PASS — not modified |
| No files outside scope changed | PASS |

---

## Design Decisions / Caveats

1. **ADR-056 remains in BLDM Authority list (line 7)**: The task only asked to update the ADR-066..068 backlog reference. ADR-056 §Compliance is still referenced in the Authority line of BLDM line 7. This is a historical reference; the deleted file is clearly marked in Q2 as "ADR-056 DELETED". Cleaning the Authority list was not requested and is a potential follow-up.

2. **ADR-062 Disclaimer uses `>` blockquote syntax**: The disclaimers are formatted as markdown blockquotes for visual emphasis. This matches the intent of calling out the paradigm-shift boundary explicitly.

3. **ADR-066 migration script is described but not executed**: The ADR specifies the SQL DDL but does not execute it (this is an ADR, not a migration). Migration execution belongs to P28-P36 implementation waves.

4. **ADR-067 references brainstorm Batch 3 and Batch 5 decisions**: The Y-level removal is grounded in the brainstorm decisions from the same session. Cross-references point to `brainstorm-decisions-2026-06-28.md` and P24 v2.0 plan §4.4/§4.12.

5. **evidence/round-2-paradigm-shift-application/ directory exists**: The disclaimer references this path for further alignment details. The directory exists (verified before execution).

---

## Next Steps

- **Wave 2**: BRD/PRD/SRS/FSD/TDD/RTM/Acceptance/Risk Register HARD STOP annotation wave (17+ doc-level assertions per ADR-062 §Supersedes line 121)
- **Wave 3**: P24 plan v2.0 finalization incorporating ADR-066 + ADR-067 implementation requirements
- **Follow-up**: Clean ADR-056 reference from BLDM line 7 Authority list (optional, low priority)

---

## Footer

Version 1.0 | 2026-06-28 | Author: Guinevere | Scope: Round-2 Wave 1 ADR-level changes
