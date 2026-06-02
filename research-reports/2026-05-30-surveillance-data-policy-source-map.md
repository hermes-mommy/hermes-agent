# Surveillance Data Policy — Foundation Source Map

**Report ID:** 2026-05-30-surveillance-data-policy-source-map
**Status:** Complete
**Date:** 2026-05-30
**Author:** Guinevere de Baroque
**Purpose:** Map all surveillance-policy-relevant requirements from foundation docs into a structured source map for authoring `Guinevere_SurveillanceDataPolicy_v1.0.md`.

---

## Source Documents Read

| # | Document | Version | Status | Lines |
|---|---|---|---|---|
| 1 | `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | 1.0 | Accepted | 778 |
| 2 | `Guinevere_PersonaSafetyPolicy_v1.0.md` | 1.0 | Accepted | 666 |
| 3 | `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` | 1.0 | Accepted | 550 |
| 4 | `Guinevere_MemorySchema_v2.0.md` | 2.0 | (seed) | 746 |
| 5 | `adr/ADR-010-surveillance-data-retention-policy.md` | — | Accepted with notes | 131 |
| 6 | `adr/ADR-019-access-control-vpn-mesh-strategy.md` | — | Accepted with notes | 142 |
| 7 | `adr/ADR-024-data-governance-classification-policy.md` | — | Accepted with notes | 132 |
| 8 | `Guinevere_TechnicalArchitecture_v2.0.md` | 2.0 | (seed) | 724 |
| 9 | `Guinevere_PRD_v2.2.md` | 2.2 | (seed) | 553 |

Additional cross-reference sources consulted:
- `Guinevere_AcceptanceCriteriaCatalog_v1.0.md`
- `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md`
- `Guinevere_EncryptionKeyManagementStandard_v1.0.md`
- `Guinevere_SecretsRotationRunbook_v1.0.md`
- `Guinevere_Observability_AlertingSpec_v1.0.md`
- `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md`
- `Guinevere_APIIntegration_v2.0.md`
- `Guinevere_ADR_Index_v1.0.md`
- `adr/ADR-018-security-architecture-defense-in-depth.md`
- `adr/ADR-008-memory-encryption-key-management.md`
- `adr/ADR-001-persona-safety-ethical-boundary.md`
- `adr/ADR-002-user-autonomy-safe-word-enforcement.md`
- `adr/ADR-003-persona-drift-control-validation.md`
- `adr/ADR-021-wearable-integration-post-mvp.md`

---

## 1. Authority Requirements

### 1.1 Normative Parents

| Source | Citation | Requirement for Surveillance Policy |
|---|---|---|
| DataGovernance §2.1 | Authority order: ADRs > PersonaSafety > DataGovernance > Samm instruction > product docs | Surveillance policy must assert its place as normative child under ADR-010/ADR-024, with cross-boundary enforcement against PersonaSafetyPolicy. |
| DataGovernance §2.2 | Supersession of blanket retention language | Policy must explicitly supersede "data forever" language from PRD v2.2 §3.5 and TechnicalArchitecture v2.0 §5.2. |
| DataGovernance §2.3 | Full consent boundary | Policy must assert that Samm's full consent is necessary but not sufficient. |
| DataGovernance §15 (backlog) | Formal surveillance retention specification is tracked backlog | The surveillance policy itself resolves this item. |
| ADR-024 Decision | Create explicit multi-class governance | Surveillance data must map to explicit classification tiers. |
| ADR-010 Decision | Retain by data class with minimization | Policy must implement tiered retention per data class. |

### 1.2 User Constraints (Must Preserve)

| Constraint | Source | Policy Requirement |
|---|---|---|
| Full owner consent necessary but not sufficient | DataGovernance §2.3, PersonaSafety §6.1 | Consent does not waive minimization, retention, incident, or safe-mode controls. |
| Persona never outranks controls | PersonaSafety §2.1, §5 | Safety/consent/privacy/security always win. |
| Blackmail/humiliation/punitive leverage/jealousy escalation/dependency/safe-word invalidation prohibited | PersonaSafety §11 (F-03, F-06, F-13), §12.2 | Explicit prohibited-use list and runtime gate required. |
| Confrontation blocked in safe-mode/distress/crisis/incident | PersonaSafety §7.2, §8; AccessControl §7 | Surveillance confrontation denied in restricted states. |
| Clipboard secrets: dropped and incident-logged | AccessControl §11, DataGovernance §9.2, §11.1 | Secret scanner mandatory on clipboard ingestion. |
| Camera/screenshots: disabled by default Critical short retention | DataGovernance §5, AccessControl §11 | Default Critical with minimum retention. |
| Wearable: post-MVP fresh activation checklist | TechnicalArchitecture §6.1, ADR-021, PRD §3.3 | Pre-activation checklist required. |
| All controls must, zero should | AGENTS.md §3, DataGovernance Review Record | Use "must" throughout. |
| Status Accepted + Samm Review Record | All foundation docs | Required boilerplate. |
| Normative child docs | DataGovernance, PersonaSafety, AccessControl, ADR-010, ADR-019, ADR-024 | List as normative parents.


---

## 18. Recommended Appendices

| Appendix | Content | Source Material |
|---|---|---|
| A — Collection Source Matrix | Per-source: Android (6), Windows (7), Wearable (5) with purpose, classification, retention, access, processing, deletion | DataGovernance §9.1, TechnicalArchitecture §6.2, PRD v2.2 §3.1-3.3 |
| B — Retention Matrix | Raw→Derived retention rules with expiry actions | DataGovernance §6.2, Appendix B |
| C — Access Matrix | Principal vs data type table with safe-mode column | AccessControl §5, §7, §8, §9, §10, §11; DataGovernance Appendix C |
| D — Prohibited Use Matrix | Forbidden pattern, detection method, runtime response | PersonaSafety §11, §12.2; Appendix B |
| E — Audit Checklist | Per-control audit items for surveillance | DataGovernance Appendix F, AccessControl Appendix C |
| F — Incident Checklist | Surveillance-specific triage and containment | DataGovernance §11, Appendix E |
| G — Wearable Activation Checklist | Consent reaffirmation, retention limits, health-data classification, persona boundary mapping | ADR-021, PRD v2.2 §3.3, TechnicalArchitecture §6.1 |
| H — Review Record | Samm acceptance record | All foundation docs |

---

## 19. Pending Items / Gaps Identified

| Gap | Impact | Source |
|---|---|---|
| No existing Surveillance Data Policy to update | Policy is net-new | Glob scan found no *Surveillance* files |
| TechnicalArchitecture v2.0 §5.2 says 'selamanya' | Must be explicitly superseded | TA §5.2 |
| PRD v2.2 §3.5 says 'selamanya — tidak ada yang dihapus' | Must be explicitly superseded | PRD §3.5 |
| Clipboard secret scanner mandatory but no exact retention beyond 'shortest feasible' | Needs concrete default (e.g., 7 days) | DataGovernance §6.2, AccessControl §11 |
| Camera screenshots: 'default Critical short retention' without exact duration | Needs concrete default (e.g., 7-30 days) | DataGovernance §6.2, AccessControl §11 |
| Wearable activation checklist not yet defined anywhere | Policy must define it fresh | Cross-doc gap |
| No existing Consent & Revocation Policy for revocation hooks | Policy must define provisional hooks | DataGovernance §15 backlog |
| No explicit Real-Time vs Batch classification per source type | Should define in policy | Gap |
| Anonymization procedure not defined for derived surveillance data | Should define in policy | Gap |

---

## 20. Verification Log

| Check | Result |
|---|---|
| All 9 foundation docs read | PASS |
| Cross-reference documents consulted | PASS (14 additional sources) |
| All 20+ required policy sections mapped | PASS |
| User constraints preserved | PASS (all prohibitions, safe-mode rules, revocation hooks) |
| All controls use 'must' not 'should' | MAPPED (normative requirement for target policy) |
| Status Accepted + Samm Review Record noted | PASS |
| Normative child docs identified | PASS (DataGovernance, PersonaSafety, AccessControl, ADR-010, ADR-019, ADR-024) |
| Recommended structure provided | PASS (20 sections + 8 appendices) |
| Gaps documented | PASS (9 gaps) |
| Output file exists and non-empty | VERIFIED |

---

**End of Source Map Report — 2026-05-30-surveillance-data-policy-source-map.md**
