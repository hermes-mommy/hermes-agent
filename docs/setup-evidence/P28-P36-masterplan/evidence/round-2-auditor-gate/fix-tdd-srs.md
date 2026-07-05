# Fix Report: TDD + SRS Paradigm Shift Alignment (Auditor 05)

| Field | Value |
|---|---|
| Task | Fix TDD and SRS documents for P28-P36 paradigm shift alignment |
| Source | Auditor 05 FAIL/NEEDS-REVIEW findings |
| Date | 2026-06-28 |
| Executor | Guinevere (Sisyphus-Junior) |
| Files Modified | `docs/tdd-technical-design-document.md`, `docs/srs-software-requirements-specification.md` |

---

## TDD Fixes (7 issues — auditor FAIL)

### Fix 1: HARD STOP ADR-062 disclaimers (6 sections)

Added `> **ADR-062 Disclaimer**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime (P24 fork) can bypass per ADR-062.` after first HARD STOP mention in each section:

| Section | Line (post-edit) | Context |
|---|---|---|
| §1.2 Scope | ~40 | In Scope table row |
| §1.3 References | ~55 | PersonaSafetyPolicy reference row |
| §1.4 Glossary | ~70 | HARD STOP glossary entry |
| §3.6 Observability | ~138 | Alert routing paragraph |
| §8 Security | ~418 | Threat mitigation table row |
| §10 ADR Table | ~469 | ADR-057 (HARD STOP semantics) row |

**Line ~494 boundary statement**: Handled by Fix 2 (triple violation) — HARD STOP text replaced with "HARD STOP (dev-workflow only, see ADR-062)" which covers the disclaimer inline.

**Post-edit verification**: 6 ADR-062 disclaimers found via grep ✅

### Fix 2: Line ~494 Triple Violation (boundary statement)

**Before:**
```
| Boundary Statement | HARD STOP absolute; consent revocation absolute; relationship memory encrypted; founder-only spawn; 2/2 agreement; wallet max ~$10; female-dominant policy; all Hermeses visible; P24 fork-agnostic for P28 (per ADR-054 + PersonaSafetyPolicy) |
```

**After:**
```
| Boundary Statement | HARD STOP (dev-workflow only, see ADR-062); consent revocation (dev-workflow only, see ADR-066); relationship memory encrypted; founder-only spawn; 2/2 agreement; wallet max ~$10; female-dominant policy; all Hermeses visible; P24 native fork (hard dependency) |
```

Changes:
- `HARD STOP absolute` → `HARD STOP (dev-workflow only, see ADR-062)` ✅
- `consent revocation absolute` → `consent revocation (dev-workflow only, see ADR-066)` ✅
- `P24 fork-agnostic for P28 (per ADR-054 + PersonaSafetyPolicy)` → `P24 native fork (hard dependency)` ✅

### Fix 3: P32 Section Rename (line ~453→471)

**Before:** `| ADR-058 | P32 P24 Fork Integration Boundary | DRAFT | Defers P24 dependency |`
**After:** `| ADR-058 | P32 External Presence & Tools Boundary | DRAFT | Defers P24 dependency |`

### Fix 4: ADR-056 Stale Reference (line ~451→466)

**Before:** `| ADR-056 | P30 Shared World Model | DRAFT | World model + private memory split |`
**After:** `| ADR-056 (DELETED — superseded by ADR-062 + P24 v2.0) | P30 Shared World Model | DELETED | World model + private memory split |`

### Fix 5: Consent Endpoint Annotation (line ~341→353)

**Before:** `| `/api/hermes/<name>`, `/api/consent/revoke` | Hermes status / revocation | founder / operator |`
**After:** `| `/api/hermes/<name>`, `/api/consent/revoke` (dev workflow only) | Hermes status / revocation | founder / operator |`

### Fix 6: Y-Level ADR-067 Disclaimers — N/A

Grep for `Y4`, `Y5`, `Y6`, `yandere` in TDD returned **0 matches**. The TDD does not contain yandere level references. No fix needed.

### Fix 7: fork-agnostic Replacement (3 occurrences)

| Line (original) | Original | Replacement |
|---|---|---|
| 32 | `P24 Hermes fork (deferred to P32 — fork-agnostic)` | `P24 Hermes fork (deferred to P32 — P24 native fork)` |
| 468 | `P28 fork-agnostic` | `P28 P24 native fork` |
| 494 | `P24 fork-agnostic for P28` | `P24 native fork (hard dependency)` |

**Post-edit verification**: 0 fork-agnostic occurrences found via grep ✅

---

## SRS Fixes (2 issues — auditor NEEDS-REVIEW)

### Fix 1: Y-Level ADR-067 Disclaimers (6 sections, 7 original refs)

Added `> **ADR-067**: Y-level caps apply to dev-workflow agent ONLY. Hermes runtime has no Y-level cap.` after first Y4/Y5/Y6 mention in each section:

| Section | Line (post-edit) | Context |
|---|---|---|
| §1.4 References | ~77 | PersonaSafetyPolicy v1.0 (Y4 baseline, Y5 ceiling) |
| §1.5 Overview | ~85 | After "HARD STOP and consent revocation carved out" paragraph |
| REQ-010 §3.2 | ~214 | After "Y4 baseline + Y5 ceiling via PersonaSafetyPolicy" in self-modification |
| §3.4 Guardrails | ~270 | After "1 confirmed Y5 excursion" in auto-rollback thresholds |
| §5.B Acronyms | ~357 | After "Y4/Y5/Y6 (yandere levels)" acronym entry |
| §5.F CF-06 | ~382 | After "reading Y4/Y5 as advisory from outside, hard from inside" |

**Post-edit verification**: 6 ADR-067 disclaimers found via grep ✅

### Fix 2: fork-agnostic Replacement (line ~32)

**Before:** `"P24 is NOT a hard dependency (fork-agnostic per ADR-054)"`
**After:** `"P24 is a hard dependency (P24 native fork per ADR-054)"`

**Post-edit verification**: 0 fork-agnostic occurrences found via grep ✅

---

## Verification Summary

| Check | TDD | SRS |
|---|---|---|
| 0 fork-agnostic remaining | ✅ 0 found | ✅ 0 found |
| ADR-062 disclaimers on HARD STOP | ✅ 6 sections | N/A |
| ADR-067 disclaimers on Y-level | N/A (0 refs) | ✅ 6 sections |
| ADR-056 annotated DELETED | ✅ line 466 | N/A |
| P32 section renamed | ✅ line 471 | N/A |
| Consent endpoint annotated | ✅ line 353 | N/A |
| Boundary triple violation fixed | ✅ line 512 | N/A |

## Exit Status

**PASS** — All 9 applicable fixes applied and verified. TDD: 7 issues resolved (6 applied + 1 N/A). SRS: 2 issues resolved. Zero remaining `fork-agnostic`, zero unannotated HARD STOP, zero stale ADR-056, zero unannotated Y-level refs.
