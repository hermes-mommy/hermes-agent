# Auditor Report — ADR-022 Baileys Scope & StepPrompts Cosmetic Fix

| Field | Value |
|---|---|
| **Auditor** | Guinevere (parent) |
| **Date** | 2026-06-03 |
| **Scope** | Verify no active Baileys implementation references in ADR-022; verify StepPrompts.md has zero "Baileys/Neonize" compound references |
| **Type** | Read-only audit |

---

## §1 ADR-022 — Baileys Reference Audit

### Grep Command

```
grep -c "Baileys" adr/ADR-022-communication-channel-strategy.md
```

### Result: **2 matches** (EXPECTED: exactly 2) ✅

| Line | Content | Section | Acceptable? |
|---|---|---|---|
| 146 | `Initial ADR — WhatsApp via Baileys (Node.js, WhatsApp Web MD protocol)...` | Revision History (v1.0 row) | ✅ Historical record |
| 147 | `Revised WhatsApp implementation from Baileys (Node.js) to Neonize...Rollback: Baileys remains viable fallback...` | Revision History (v1.1 row) | ✅ Historical record + rollback note |

### Active Section Verification (Lines 128–141)

Read lines 128–141 of ADR-022. **Zero Baileys references found.**

| Line | Key Content | Baileys Present? |
|---|---|---|
| 131 | WhatsApp via **Neonize** (pure Python, wraps whatsmeow via CGo) | ❌ No |
| 138 | **Neonize caveats:** v0.3.18.post0... | ❌ No |
| 128–141 (all) | Review Record / Implementation Notes active sections | ❌ None |

### ADR-022 Verdict: **PASS** ✅

All Baileys references are confined to the Revision History table (lines 146–147), which is the correct and expected location for historical decision records. All active governance sections (Context, Decision Drivers, Considered Options, Decision Outcome, Consequences, Implementation Notes, Review Record) use "Neonize" exclusively.

---

## §2 StepPrompts.md — Compound Reference Audit

### Grep Command

```
grep -c "Baileys/Neonize" stepprompts/StepPrompts.md
```

### Result: **0 matches** (EXPECTED: 0) ✅

No compound "Baileys/Neonize" references exist in StepPrompts.md.

### Standalone "Baileys" References (10 matches)

All 10 remaining "Baileys" references were inspected for context acceptability:

| Line | Context Summary | Category | Acceptable? |
|---|---|---|---|
| 19501 | "Requires revision from Baileys/Node.js to Neonize/pure Python" | ADR revision note | ✅ Migration context |
| 19515 | "requires formal revision from Baileys/Node.js to Neonize/Python" | ADR reference note | ✅ Migration context |
| 19521 | "ADR-022 currently mandates 'WhatsApp via Baileys'" | Describing current ADR state for revision | ✅ Migration context |
| 19635 | "requirement to revise ADR-022 from Baileys to Neonize" | Evidence reference | ✅ Migration context |
| 19665 | "replace 'Baileys' with 'Neonize' throughout" | Revision instruction | ✅ Migration context |
| 19666 | "same unofficial WhatsApp Multi-Device protocol as Baileys" | Technical comparison | ✅ Historical/comparison |
| 23011 | "baileys-antiban npm library (reference implementation for Baileys-based bots)" | Anti-ban reference impl | ✅ Reference only, not dependency |
| 23174 | "baileys-antiban Reference: used by Baileys-based WhatsApp bots" | Jitter pattern reference | ✅ Reference only, not dependency |
| 24478 | `NEONIZE_INTERNAL = ... # Neonize/Baileys internal error` | Code comment (error enum) | ✅ Technical classification |
| 24659 | "known failure pattern in Baileys-based libraries" | Bug reference context | ✅ Historical/comparison |

### StepPrompts.md Verdict: **PASS** ✅

Zero compound "Baileys/Neonize" references. All 10 standalone "Baileys" references are in acceptable contexts: migration documentation (5), technical comparison/reference (4), or code classification comments (1). None represent active implementation directives.

---

## §3 Summary

| Check | Expected | Actual | Status |
|---|---|---|---|
| ADR-022 Baileys count | 2 | 2 | ✅ PASS |
| ADR-022 Baileys in active sections | 0 | 0 | ✅ PASS |
| ADR-022 line 131 says Neonize | Yes | Yes | ✅ PASS |
| ADR-022 line 138 says Neonize | Yes | Yes | ✅ PASS |
| StepPrompts "Baileys/Neonize" compound | 0 | 0 | ✅ PASS |
| StepPrompts standalone Baileys acceptable | All | All (10/10) | ✅ PASS |

## Overall Verdict: **PASS** ✅

### Scope Assessment

All remaining Baileys references are acceptable:
- **ADR-022**: Confined to Revision History table — correct for ADR format (historical record of decisions).
- **StepPrompts.md**: All in migration instructions, technical comparisons, reference implementations, or code classification — none represent active Baileys implementation directives.

### Recommendation

No action required. Both files are in expected state. The Baileys→Neonize migration in ADR-022 is complete and correctly reflected in all active governance sections. StepPrompts.md retains Baileys references only where contextually appropriate (migration notes, historical comparisons, reference implementations).

---

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-03 | Guinevere | Initial read-only audit report. |
