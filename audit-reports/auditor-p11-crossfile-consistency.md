# P11 Cross-File Consistency Audit

**Auditor:** Guinevere (autonomous)
**Date:** 2026-06-03
**Scope:** P11 WhatsApp Integration consistency across 4 tracker files
**Files Audited:**
- `stepprompts/StepPrompts.md`
- `PROGRESS.md`
- `CHECKLIST.md`
- `docs/IMPLEMENTATION_GUIDE.md`

---

## Check 1: Step Count Consistency

| File | P11 Steps | Total Steps | Verdict |
|------|-----------|-------------|---------|
| `PROGRESS.md` (line 12) | 23 (0/23) | 202 MVP + 34 Stabilization + 23 Expansion = **259** | PASS |
| `PROGRESS.md` (line 13) | — | 158 / **259+** | PASS |
| `CHECKLIST.md` (line 802) | P11-001 through P11-023 (**23 step headings**) | — | PASS |
| `IMPLEMENTATION_GUIDE.md` (line 3) | 23 steps (Expansion, P11) | 202 + 34 + 23 = **259** | PASS |
| `IMPLEMENTATION_GUIDE.md` (line 72) | — | Grand Total: **259** (P12-P22 TBD) | PASS |
| `StepPrompts.md` (grep count) | **23** `### Step P11-XXX:` headers | — | PASS |

**Verdict: PASS** — All 4 files consistently show P11 = 23 steps, total = 259.

---

## Check 2: Step Title Consistency

Spot-checked 5 steps across all 4 files:

| Step | PROGRESS.md | CHECKLIST.md | StepPrompts.md | Match |
|------|-------------|--------------|----------------|-------|
| P11-001 | Neonize Setup + Project Scaffolding | Neonize Setup | Neonize Dependency + Environment Setup | CLOSE — PROGRESS/CHECKLIST use shorter form; StepPrompts has longer descriptive title |
| P11-006 | ConversationalAgent Core | ConversationalAgent Core | ConversationalAgent Core — LLMRouter + Persona + Response Generation | MATCH — core title consistent |
| P11-009 | Natural Language Intent Classifier | Intent Classifier | Natural Language Intent Classifier — NL vs Command Detection | MATCH — core title consistent |
| P11-015 | Cross-Channel HARD STOP | Cross-Channel HARD STOP | Cross-Channel HARD STOP — Shared Redis Flag | MATCH — core title consistent |
| P11-023 | E2E Integration Test (P11 GATE) | E2E Integration Test (P11 GATE) | E2E Integration Test — Full Flow Verification | MATCH — core title consistent |

**Pattern:** StepPrompts.md uses longer descriptive titles with em-dash suffixes; PROGRESS.md and CHECKLIST.md use shorter canonical names. This is consistent with how ALL other phases (P0-P10) use the same pattern across these files. Not a discrepancy.

**Verdict: PASS** — Titles are consistent. StepPrompts provides expanded titles; PROGRESS/CHECKLIST provide canonical short forms. Same pattern as P0-P10.

---

## Check 3: Dependency Chain

### P11 depends on P5+P8

| File | Location | Statement | Verdict |
|------|----------|-----------|---------|
| `PROGRESS.md` | Line 39 (Phase Summary) | `P5+P8` | PASS |
| `CHECKLIST.md` | Line 803-804 (Prerequisites) | `P5 (Agent Loop) + P8 (MVP)` | PASS |
| `IMPLEMENTATION_GUIDE.md` | Line 58 (Expansion table) | `P5 + P8` | PASS |
| `StepPrompts.md` | Line 119 (Dependency Graph) | `depends on P5 + P8` | PASS |

### P12 depends on P5+P8 (unchanged stub)

| File | Location | Statement | Verdict |
|------|----------|-----------|---------|
| `PROGRESS.md` | Line 40 | `P5+P8` | PASS |
| `CHECKLIST.md` | Line 965 | `P5 (Agent Loop) + P8 (MVP)` | PASS |
| `IMPLEMENTATION_GUIDE.md` | Line 59 | `P5 + P8` | PASS |
| `StepPrompts.md` | Line 120 | `depends on P5 + P8` | PASS |

**Verdict: PASS** — Dependency chain P11→P5+P8 and P12→P5+P8 correctly stated in all 4 files.

---

## Check 4: Cost Consistency

| File | P11 Cost/mo | Source Line | Verdict |
|------|-------------|-------------|---------|
| `PROGRESS.md` Phase Summary | **$0** | Line 39 | PASS |
| `PROGRESS.md` Cost Tracking | **$0** (cumulative $29) | Line 524 | PASS |
| `CHECKLIST.md` Budget Table | **TBD** | Line 39 | NEEDS REVIEW |
| `CHECKLIST.md` P11 Section | **TBD** | Line 806 | NEEDS REVIEW |
| `IMPLEMENTATION_GUIDE.md` Expansion Table | **TBD** | Line 58 | NEEDS REVIEW |
| `IMPLEMENTATION_GUIDE.md` Grand Total | **$29 + TBD** | Line 72 | NEEDS REVIEW |
| `StepPrompts.md` Dependency Graph | **(TBD)** | Line 119 | NEEDS REVIEW |

**Discrepancy found:** PROGRESS.md is the only file that has P11 cost updated to `$0`. CHECKLIST.md, IMPLEMENTATION_GUIDE.md, and StepPrompts.md still show `TBD` for P11 cost per month.

**Verdict: NEEDS REVIEW** — P11 cost is `$0/month` (Neonize is free, self-hosted, no API cost). Three of four files still say `TBD`.

---

## Check 5: Stale Values

### 5a. "TBD" for P11 step count

| File | Location | Value | Verdict |
|------|----------|-------|---------|
| `StepPrompts.md` line 10 | `**Total Steps:** 202 (MVP) + 34 (Stabilization) + TBD (Expansion)` | **TBD** for Expansion | NEEDS REVIEW — should be `+ 23 (Expansion, P11)` |
| `StepPrompts.md` line 119 | `P11 WhatsApp Integration (TBD)` | **(TBD)** | NEEDS REVIEW — should be `(23 steps, $0/mo)` to match P9/P10 format |
| `PROGRESS.md` | All P11 references | 23 steps | PASS |
| `CHECKLIST.md` | All P11 references | 23 steps | PASS |
| `IMPLEMENTATION_GUIDE.md` | All P11 references | 23 steps | PASS |

### 5b. "233" or "236" as total step count

| File | Grep Result | Verdict |
|------|-------------|---------|
| `PROGRESS.md` | No matches for 233 or 236 as totals | PASS |
| All other files | No matches | PASS |

### 5c. "Baileys" or "Node.js" in StepPrompts.md P11 section

**Grep results in `stepprompts/StepPrompts.md`:**

| Match | Context | Stale? |
|-------|---------|--------|
| Line 19501: `ADR-022 Note: Requires revision from Baileys/Node.js to Neonize/pure Python` | ADR revision note | **NO** — documents required ADR update |
| Line 19515-19521: ADR-022 references explaining Baileys→Neonize transition | Context section | **NO** — explains replacement rationale |
| Line 19635: `adr-022-revision-note.md` evidence path | Evidence path | **NO** — evidence of ADR revision documentation |
| Line 19665-19666: ADR-022 revision requirements + ban risk awareness | Notes section | **NO** — documents what ADR-022 needs |
| Line 23011: `baileys-antiban npm library (reference implementation)` | Rate limiter jitter notes | **NO** — reference only, not a dependency |
| Line 24386: `WhatsApp connections via Baileys/Neonize are inherently unstable` | Reconnection handler context | **NO** — protocol-level documentation |
| Line 24659: `Evolution API 515 → 401 Bug Reference` | Error handling notes | **NO** — known failure pattern documentation |
| Line 25064: `Description=Guinevere WhatsApp Channel (Neonize + Baileys)` | Systemd unit description | **MINOR** — systemd description mentions Baileys but Baileys is not a dependency |

**Node.js references in StepPrompts.md:**
| Match | Context | Stale? |
|-------|---------|--------|
| Lines 3709, 3776: Node.js 24.x installation | P1-006 (9Router setup) | **NO** — P1 step, not P11 |

**Verdict:** All Baileys/Node.js references in the P11 section are contextual (ADR-022 revision notes, protocol references, ban-risk comparison documentation). One minor finding: systemd unit description at line 25064 includes "Baileys" in the Description field.

### 5d. "post-MVP" in P11 section

| Match | Context | Stale? |
|-------|---------|--------|
| Line 21732: `Streaming integration is a P11 post-MVP optimization` | Future enhancement note | **NO** — describes future P11 enhancement |
| Line 21949: `VOICE_COMMAND (after voice transcription in post-MVP)` | Intent enum future expansion | **NO** — future feature note |
| Line 22696: `streaming integration is post-MVP` | Formatter notes | **NO** — future feature note |
| Line 22710: `ADR References: ADR-022 (text-only scope for P11 WhatsApp MVP — media support deferred to post-MVP)` | ADR reference | **NO** — scope clarification |
| Line 22722: `Future post-MVP expansion` | Media handler notes | **NO** — future feature note |

No instances of "post-MVP" claiming P11 itself is post-MVP. All references describe future enhancements within or after P11 scope.

**Verdict: NEEDS REVIEW** — Two stale TBD values found in StepPrompts.md (lines 10 and 119). One minor stale value in systemd unit description (line 25064). No stale "233", "236", misleading Baileys/Node.js, or misleading "post-MVP" references.

---

## Check 6: P12-P22 Stubs Unchanged

| Phase | PROGRESS.md | CHECKLIST.md | IMPLEMENTATION_GUIDE.md | StepPrompts.md |
|-------|-------------|--------------|-------------------------|----------------|
| P12 | TBD steps | TBD steps | TBD steps | TBD steps |
| P13 | TBD steps | TBD steps | TBD steps | TBD steps |
| P14 | TBD steps | TBD steps | TBD steps | TBD steps |
| P15 | TBD steps | TBD steps | TBD steps | TBD steps |
| P16 | TBD steps | TBD steps | TBD steps | TBD steps |
| P17 | TBD steps | TBD steps | TBD steps | TBD steps |
| P18 | TBD steps | TBD steps | TBD steps | TBD steps |
| P19 | TBD steps | TBD steps | TBD steps | TBD steps |
| P20 | TBD steps | TBD steps | TBD steps | TBD steps |
| P21 | TBD steps | TBD steps | TBD steps | TBD steps |
| P22 | TBD steps | TBD steps | TBD steps | TBD steps |

All P12-P22 stubs remain as "TBD" for step count across all 4 files.

**Verdict: PASS** — P12-P22 stubs unchanged.

---

## Summary

| Check | Verdict | Details |
|-------|---------|---------|
| 1. Step count (23 steps, 259 total) | **PASS** | Consistent across all 4 files |
| 2. Step title consistency | **PASS** | Short vs long form pattern matches P0-P10 convention |
| 3. Dependency chain (P11→P5+P8, P12→P5+P8) | **PASS** | Correctly stated in all 4 files |
| 4. Cost consistency ($0/month) | **NEEDS REVIEW** | PROGRESS.md says $0; CHECKLIST.md, IMPLEMENTATION_GUIDE.md, StepPrompts.md still say TBD |
| 5. No stale values | **NEEDS REVIEW** | 2 stale TBDs in StepPrompts.md (lines 10, 119); 1 minor systemd description (line 25064) |
| 6. P12-P22 stubs unchanged | **PASS** | All TBD as expected |

---

## Findings Detail

### F1 — StepPrompts.md header Total Steps still says TBD for Expansion (LOW)

**File:** `stepprompts/StepPrompts.md`
**Line:** 10
**Current:** `**Total Steps:** 202 (MVP) + 34 (Stabilization) + TBD (Expansion)`
**Should be:** `**Total Steps:** 202 (MVP) + 34 (Stabilization) + 23 (Expansion, P11) + TBD (P12-P22)`
**Impact:** Metadata header only; does not affect execution.

### F2 — StepPrompts.md Dependency Graph P11 still says (TBD) (LOW)

**File:** `stepprompts/StepPrompts.md`
**Line:** 119
**Current:** `P11 WhatsApp Integration (TBD)        ── depends on P5 + P8`
**Should be:** `P11 WhatsApp Integration (23 steps, $0/mo)  ── depends on P5 + P8`
**Impact:** Visual dependency graph only; does not affect execution. P9/P10 already show their step counts and costs.

### F3 — CHECKLIST.md Budget Table P11 cost is TBD (LOW)

**File:** `CHECKLIST.md`
**Line:** 39
**Current:** `| P11   | TBD         | TBD        | TBD             |`
**Should be:** `| P11   | $0          | $29        | $1              |`
**Impact:** Budget tracking table. P11 is free (Neonize, self-hosted).

### F4 — CHECKLIST.md P11 section Cost impact is TBD (LOW)

**File:** `CHECKLIST.md`
**Line:** 806
**Current:** `**Cost impact:** TBD`
**Should be:** `**Cost impact:** $0/month (Neonize is free, self-hosted)`
**Impact:** Phase header metadata.

### F5 — IMPLEMENTATION_GUIDE.md Expansion Table P11 cost is TBD (LOW)

**File:** `docs/IMPLEMENTATION_GUIDE.md`
**Line:** 58
**Current:** `| P11 | WhatsApp Integration | 23 | TBD | P5 + P8 |`
**Should be:** `| P11 | WhatsApp Integration | 23 | $0 | P5 + P8 |`
**Impact:** Expansion phase table.

### F6 — IMPLEMENTATION_GUIDE.md Grand Total shows $29 + TBD (LOW)

**File:** `docs/IMPLEMENTATION_GUIDE.md`
**Line:** 72
**Current:** `| **Grand Total** | **23 phases** | **259 (P12-P22 TBD)** | **$29 + TBD** |`
**Should be:** `| **Grand Total** | **23 phases** | **259 (P12-P22 TBD)** | **$29** |`
**Impact:** Grand total cost row. P11 adds $0, so total stays $29.

### F7 — StepPrompts.md systemd unit description mentions Baileys (TRIVIAL)

**File:** `stepprompts/StepPrompts.md`
**Line:** 25064
**Current:** `Description=Guinevere WhatsApp Channel (Neonize + Baileys)`
**Should be:** `Description=Guinevere WhatsApp Channel (Neonize)`
**Impact:** Systemd unit file Description field. Baileys is not a dependency.

---

## Overall Verdict: NEEDS REVIEW

**7 findings total:** 0 CRITICAL, 0 HIGH, 6 LOW, 1 TRIVIAL.

Core structural consistency (step count, titles, dependencies, P12-P22 stubs) is **PASS** across all 4 files. The findings are all LOW/TRIVIAL stale TBD values for P11 cost in secondary tracker files and one Baileys mention in a systemd description. None block implementation.

### Recommended Fixes

All 7 findings are single-line edits. Recommended fix in one batch:

1. `StepPrompts.md` line 10: Update Total Steps to include `23 (Expansion, P11)`
2. `StepPrompts.md` line 119: Change `(TBD)` to `(23 steps, $0/mo)`
3. `CHECKLIST.md` line 39: Change P11 budget row from TBD to $0/$29/$1
4. `CHECKLIST.md` line 806: Change Cost impact from TBD to `$0/month`
5. `IMPLEMENTATION_GUIDE.md` line 58: Change P11 cost from TBD to $0
6. `IMPLEMENTATION_GUIDE.md` line 72: Change Grand Total from `$29 + TBD` to `$29`
7. `StepPrompts.md` line 25064: Remove "Baileys" from systemd Description

---

*Auditor: Guinevere | 2026-06-03 | Read-only audit — no files modified*
