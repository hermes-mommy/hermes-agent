# Evidence: ADR-022 Revision (Baileys → Neonize)

**Date:** 2026-06-03
**Operator:** Faiz
**Executor:** Guinevere (Sisyphus orchestrator)
**Status:** Implementation complete, parent-verified, pending auditor gate

---

## 1. What Was Done

Revised ADR-022 (Communication Channel Strategy) to replace Baileys (Node.js, WhatsApp Web MD protocol) with Neonize (pure Python, wraps whatsmeow via CGo) for the WhatsApp integration channel. Updated ADR-Index, adr/README.md, and decisions-log to reflect the revision. Fixed 1 cosmetic "Baileys/Neonize" reference in StepPrompts.md P11-020.

## 2. Files Changed

| File | Task | Changes |
|---|---|---|
| `adr/ADR-022-communication-channel-strategy.md` | T1 | 7 edits: YAML status, body status, Context wearable note, Review Record WhatsApp bullet, Review Record caveats bullet, Implementation Notes exception, Revision History section (v1.0 + v1.1) |
| `docs/10-governance/17-ADR_Index_v1.0.md` | T2 | ADR-022 row: status → "Accepted with notes (Revised 2026-06-03)", tags +neonize |
| `adr/README.md` | T3 | Mirror of T2: ADR-022 row updated identically |
| `docs/10-governance/decisions-log.md` | T4 | Row #002 added, last-updated → 2026-06-03 |
| `stepprompts/StepPrompts.md` | T4 | 1x "Baileys/Neonize" → "Neonize" (line 24386, P11-020 section) |

## 3. Validation Results

### Parent Grep Verification (5 checks)

| Check | Expected | Actual | Status |
|---|---|---|---|
| ADR-022 Baileys active refs | 0 (historical in Rev History OK) | 2 (both in Revision History table lines 146-147) | ✅ PASS |
| ADR-022 Neonize refs | 3+ | 3 (lines 131, 138, 147) | ✅ PASS |
| ADR-Index "Revised 2026-06-03" | 1 match | 1 (line 86) | ✅ PASS |
| adr/README.md "Revised 2026-06-03" | 1 match | 1 (line 89) | ✅ PASS |
| decisions-log row #002 | 1 match | 1 (line 15) | ✅ PASS |
| StepPrompts "Baileys/Neonize" | 0 | 0 | ✅ PASS |
| ADR-022 PostgreSQL session | present | 4 matches (lines 71, 131, 138, 147) | ✅ PASS |

## 4. Evidence Artifacts

| Artifact | Path |
|---|---|
| Research impact map | `research-reports/adr-022-revision/impact-map.md` |
| Neonize library research | `research-reports/whatsapp-integration-research-2026-06-03.md` |
| Ban risk research | `research-reports/whatsapp-unofficial-api-production-risks.md` |
| P11 requirements | `research-reports/p11-expansion/requirements-p11-whatsapp.md` |
| This evidence file | `docs/setup-evidence/adr-022-revision/evidence-adr-022-revision.md` |

## 5. Doc-Sync Impact

- ADR-022 status now includes revision note; no other ADR affected
- ADR-Index and adr/README.md remain synchronized
- decisions-log.md grew from 1 to 2 entries
- 15 other docs still contain Baileys references as active implementation guidance (OUT OF SCOPE — flagged as follow-up)

## 6. Boundary Compliance

| Boundary | Status |
|---|---|
| Persona drift | N/A — governance doc change |
| Consent | N/A — no runtime change |
| Surveillance | N/A — no runtime change |
| HARD STOP | Preserved (ADR-002 cross-channel mandate unchanged) |
| Secret exposure | None |
| ADR governance | Exception noted: in-place revision per Faiz explicit instruction, with full revision history appended |

## 7. Rollback / Re-run Safety

- ADR-022 git history preserves pre-revision state
- Baileys/Evolution API remains viable fallback (documented in Revision History v1.1)
- No runtime code changes; purely documentation

## 8. Design Decisions / Caveats

1. **In-place revision vs superseding ADR:** ADR-022 convention says "create a superseding ADR instead." Faiz explicitly requested in-place revision with revision history. Exception documented in Implementation Notes.
2. **Neonize session = PostgreSQL, NOT Redis:** Librarian discovered Neonize has no Redis backend. Requirements doc (`requirements-p11-whatsapp.md`) incorrectly stated Redis. This ADR revision corrects it to PostgreSQL. Requirements doc should be updated in a follow-up.
3. **15 stale docs with Baileys refs:** 42 files total reference Baileys, 15 still prescribe it as current implementation. Highest risk: `docs/40-operations/44-DeploymentGuide_v1.0.md` §3.7 has full Baileys systemd unit file with npm install. OUT OF SCOPE for this revision.
4. **P11-020 cosmetic fix:** Only 1 of 2 expected "Baileys/Neonize" occurrences found (line 24386). Second occurrence may have been cleaned in a prior session. Zero remain after this fix.

## 9. Auditor Gate

| Auditor | Verdict | Report Path |
|---|---|---|
| Completeness (bg_e4587ccc) | ✅ PASS (10/10) | `audit-reports/auditor-adr022-completeness.md` |
| Cross-File Consistency (bg_93fb99b5) | ✅ PASS (33/33) | `audit-reports/auditor-adr022-consistency.md` |
| Scope + Baileys Check (bg_788bee38) | ✅ PASS | `audit-reports/auditor-adr022-scope.md` |

**Pre-existing deviations noted (out of scope, low severity):**
1. ADR-021 wording in Canonical Decision Map differs between ADR-Index ("Expansion") and adr/README.md ("Stabilization/Expansion")
2. `last_modified` YAML field still shows 2026-05-30 in both ADR-Index and adr/README.md despite ADR-022 revision on 2026-06-03

## 10. Security Scan

No security-sensitive changes. No secrets, credentials, tokens, or personal data exposed.

## 11. Acceptance Criteria Mapping

| Criterion | Status |
|---|---|
| ADR-022 WhatsApp section references Neonize, not Baileys | ✅ |
| Revision History with v1.0 and v1.1 entries | ✅ |
| ADR-Index reflects revision | ✅ |
| adr/README.md mirrors ADR-Index | ✅ |
| decisions-log has entry #002 | ✅ |
| Session storage = PostgreSQL (not Redis) | ✅ |

## 12. Footer

| Field | Value |
|---|---|
| Evidence version | 1.0 |
| Evidence date | 2026-06-03 |
| Evidence author | Guinevere (Sisyphus) |
| Approved by | Pending auditor gate |
