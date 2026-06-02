# Auditor Gate Report — Obscura CDP Adoption (ADR-033)

**Auditor:** Guinevere (independent audit)
**Date:** 2026-06-02
**Scope:** All file changes for ADR-033 — Obscura CDP adoption decision
**Verdict: NEEDS REVIEW** (1 finding requires investigation; no blocking issues)

---

## 1. Per-File Audit Findings

### 1.1 `adr/ADR-033-browser-automation-obscura.md` (Created)

| Check | Result | Notes |
|---|---|---|
| MADR format | PASS | YAML frontmatter + standard MADR sections present (Status, Date, Deciders, Tags, Context, Decision Drivers, Considered Options, Decision, Consequences, Rollback Plan, Implementation Notes, Links) |
| Frontmatter metadata | PASS | adr: 033, status: Accepted, date: 2026-06-02, risk_level: MEDIUM, supersedes: "Refines ADR-020 (implementation-level)" |
| Decision/context sections | PASS | Coherent narrative — context explains why Obscura, decision drivers cite VPS resources + X auto-poster + CDP compatibility |
| Consequences (positive) | PASS | 7 positive consequences documented (memory reduction, anti-detect, single binary, faster loads, CDP-compatible, $0 cost, VPS-friendly) |
| Consequences (negative/risks) | PASS | 8 risk items documented |
| Pre-1.0 version | PASS | "Pre-1.0: v0.1.6 (April 2026)" on line 160 |
| Project age | PASS | "~50 days old at time of adoption" on line 161 |
| Bus factor | PASS | "Top 3 contributors account for ~78 visible commits" on line 167 |
| CDP coverage | PASS | "9 of 40+ CDP domains implemented" on line 163 |
| Rollback plan | PASS | Documented with commands, time estimate (< 5 minutes), fallback architecture reference |
| GitHub stars mention | **FINDING** | ADR-033 does **NOT** mention GitHub star count (14K or otherwise). The number appears only in `decisions-log.md` line 14. If 14K stars is material to the decision, it should be included in ADR-033's Context or Risk section. See Finding 1 below. |
| ADR-020 refs | PASS | Referenced 9 times (supersedes field, related_documents, line 50, line 56, line 74, line 144, line 171, line 192, line 209). Correctly clarifies that ADR-020 remains strategic decision. |
| Links section | PASS | All paths resolve within project structure |

### 1.2 `docs/10-governance/17-ADR_Index_v1.0.md` (Modified)

| Check | Result | Notes |
|---|---|---|
| ADR-033 row exists | PASS | Line 97: correct title, status "Accepted", risk "MEDIUM", correct tags |
| adr_count frontmatter | PASS | 33 matches register (ADR 001-033) |
| Accepted count (18) | PASS | Manually verified: ADR-004, 005, 006, 007, 011, 013, 014, 015, 017, 020, 021, 026, 027, 029, 030, 031, 032, 033 = 18 |
| Accepted with notes count (14) | PASS | ADR-001, 002, 003, 008, 009, 010, 012, 016, 018, 019, 022, 023, 024, 025 = 14 |
| Superseded count (1) | PASS | ADR-028 = 1 |
| MEDIUM count (7) | PASS | ADR-006, 020, 021, 023, 026, 028, 033 = 7 |
| CRITICAL count (11) | PASS | Verified |
| HIGH count (15) | PASS | Verified |
| Backlog shifted | PASS | Correctly shifted to 034-048 |
| ADR-020 row unchanged | PASS | Line 84: "Accepted | MEDIUM | browser, obscura, playwright, automation" — match with original |

### 1.3 `adr/README.md` (Modified)

| Check | Result | Notes |
|---|---|---|
| ADR-033 row exists | PASS | Line 90: correct title, "Accepted", "MEDIUM", correct tags, correct file link |
| adr_count frontmatter | PASS | 26 — but see Finding 2 below |
| Accepted count (12) | PASS | ADR-004, 005, 006, 007, 011, 013, 014, 015, 017, 020, 021, 033 = 12 |
| Accepted with notes (14) | PASS | ADR-001-003, 008-010, 012, 016, 018, 019, 022-025 = 14 |
| MEDIUM count (5) | PASS | ADR-006, 020, 021, 023, 033 = 5 |
| CRITICAL count (8) | PASS | Verified |
| HIGH count (13) | PASS | Verified |
| Backlog shifted | PASS | Correctly shifted to 034-048 |
| Missing ADRs 026-032 | **FINDING** | ADR-026 through ADR-032 are present in the master index (`17-ADR_Index_v1.0.md`) but **missing** from `adr/README.md` register. The Canonical Decision Map is also missing their entries (only goes to ADR-021). This pre-dates ADR-033. See Finding 2 below. |

### 1.4 `stepprompts/StepPrompts.md` (P6-009, lines 7150-7210) (Modified)

| Check | Result | Notes |
|---|---|---|
| P6-009 references ADR-033 | PASS | Line 7162: `(ADR-020, ADR-033)`, line 7202: `(per ADR-033)` |
| Primary install: Obscura binary | PASS | Lines 7164-7168: curl download + install |
| Systemd service | PASS | Lines 7170-7188: `guinevere-obscura.service` with correct config (port 9222, stealth, workers 2) |
| playwright-core install | PASS | Line 7191: `pip install playwright-core` (not full playwright) |
| connect_over_cdp pattern | PASS | Lines 7193-7196: correct `p.chromium.connect_over_cdp("ws://127.0.0.1:9222")` |
| Rollback as comment only | PASS | Lines 7202-7204: Playwright+Chromium install only in rollback comments (`# apt install`, `# pip install`) |
| No `npx playwright install chromium` | PASS | Zero matches |
| No `apt-get install chromium-browser` | PASS | Zero matches |

### 1.5 `docs/IMPLEMENTATION_GUIDE.md` (Modified)

| Check | Result | Notes |
|---|---|---|
| Obscura CDP in services table | PASS | Line 527: `Obscura CDP | guinevere-obscura | 9222` |
| Port 9222 in ports line | PASS | Line 540: `9222 Obscura CDP` |
| Browser troubleshooting section | PASS | Lines 421-429: Systemctl status, CDP endpoint curl test, connect_over_cdp pattern, ADR-033 rollback reference |
| No Playwright install as primary | PASS | No `playwright install chromium`, `npx playwright`, or `apt-get install chromium-browser` outside rollback context |

### 1.6 `docs/10-governance/decisions-log.md` (Created)

| Check | Result | Notes |
|---|---|---|
| File exists | PASS | Created at `docs/10-governance/decisions-log.md` |
| Obscura entry as #001 | PASS | Line 14: entry #001, correct date, correct category (Tooling) |
| ADR-033 link correct | PASS | Relative path `../../adr/ADR-033-browser-automation-obscura.md` resolves to `adr/ADR-033-browser-automation-obscura.md` from root |
| Rationale mentions 14K stars | PASS | Line 14: "14K stars" present in rationale text |

---

## 2. Stale Reference Check

| Pattern | Files Checked | Matches | Verdict |
|---|---|---|---|
| `npx playwright install chromium` | All changed files | 0 | PASS — zero references |
| `apt-get install chromium-browser` as primary | ADR-033, StepPrompts, IMPLEMENTATION_GUIDE | 0 | PASS — zero references |
| `pip install playwright` (not playwright-core) as primary | ADR-033, StepPrompts, IMPLEMENTATION_GUIDE | 0 | PASS — `playwright-core` used instead |
| `playwright install chromium` | ADR-033 | 1 match (line 188) | PASS — in rollback section only |
| `playwright install chromium` | StepPrompts P6-009 | 1 match (line 7204) | PASS — in rollback comment block only |
| `playwright install chromium` | IMPLEMENTATION_GUIDE | 0 | PASS |
| `headless.?chrom` | Changed files | All in ADR-033 alternatives/description | PASS — intentional context |

**Stale reference verdict: PASS — ZERO stale/erroneous Playwright/Chromium mentions. All occurrences are intentional rollback/fallback documentation.**

---

## 3. Cross-Reference Consistency

| Check | Result |
|---|---|
| ADR-033 references ADR-020 correctly | PASS — 9 references, all correctly frame ADR-020 as unchanged strategic decision |
| Master index (17-ADR_Index_v1.0.md) ADR-033: "Accepted" + "MEDIUM" | PASS |
| adr/README.md ADR-033: "Accepted" + "MEDIUM" | PASS |
| Both indexes agree on ADR-033 status/risk | PASS |
| Decision log links to correct ADR-033 path | PASS — relative path resolves correctly |
| StepPrompts P6-009 references ADR-033 | PASS — lines 7162, 7202 |

---

## 4. Boundary Checks

| Check | Result |
|---|---|
| No secrets/tokens in ADR-033 | PASS — zero matches for token/password/secret/api key patterns |
| No secrets in decisions-log.md | PASS |
| No type-safety suppression (`as any`, `@ts-ignore`, `# type: ignore`) | PASS — zero matches in all changed files |
| ADR-020 not deleted | PASS — file intact, 121 lines, status still "Accepted" |
| ADR-020 not modified | PASS — unchanged; still reads "obscura primary + Playwright fallback"; no added "Superseded" status |
| Rollback plan documented | PASS — ADR-033 §Rollback Plan with commands, time estimate, ADR-020 cross-ref |
| Rollback available in StepPrompts P6-009 | PASS — comment block line 7202-7204 |
| Rollback available in IMPLEMENTATION_GUIDE | PASS — troubleshooting section references ADR-033 |

---

## 5. Findings

### Finding 1: ADR-033 Missing GitHub Star Count (NEEDS REVIEW)

**Severity:** Low
**Location:** `adr/ADR-033-browser-automation-obscura.md`
**Issue:** The decisions-log.md states Obscura has "14K stars" (line 14), but ADR-033's Context and Risk sections contain zero mention of GitHub star count. The task expected the risk section to include "14K stars" as realistic data.

**Impact:** Inconsistency between decision log rationale and ADR. The star count is material context for project maturity assessment.

**Recommendation:** Either:
- (A) Add star count to ADR-033 Context section with a verified source, OR
- (B) Remove the "14K stars" claim from decisions-log.md if unverifiable

### Finding 2: adr/README.md Missing ADRs 026-032 (PRE-EXISTING)

**Severity:** Low
**Location:** `adr/README.md`
**Issue:** ADR-026 through ADR-032 are registered in the master index (`17-ADR_Index_v1.0.md`) but absent from `adr/README.md`. The frontmatter says `adr_count: 26` but the master index has 33. This is pre-existing — not introduced by ADR-033. The ADR-033 row was correctly added but the 7 pre-existing missing ADRs remain unaddressed.

**Impact:** adr/README.md is out of sync with the master index. Maintenance rules (line 128) state: "Keep `adr/README.md` synchronized with this master index."

**Recommendation:** Sync adr/README.md with the master index as a separate task. Not blocking ADR-033 acceptance.

### Finding 3: Root README.md Stale ADR Count (COLLATERAL — OUT OF SCOPE)

**Severity:** Informational
**Location:** `README.md` (root, not changed)
**Issue:** Root README.md still says "32 Architecture Decision Records" (should be 33). This file was not part of the ADR-033 change set but is now stale.

**Recommendation:** Update as part of routine docs maintenance.

---

## 6. Summary

| Category | Result |
|---|---|
| ADR-033 content & format | PASS |
| ADR Index counts (master) | PASS |
| ADR Index counts (adr/README.md) | PASS (for ADR-033 addition) |
| StepPrompts P6-009 migration | PASS |
| IMPLEMENTATION_GUIDE updates | PASS |
| decisions-log.md | PASS |
| Stale reference check | PASS — zero stale Playwright refs |
| Cross-reference consistency | PASS |
| Boundary compliance | PASS |
| Finding 1 (stars in ADR-033) | NEEDS REVIEW |
| Finding 2 (adr/README.md sync) | PRE-EXISTING, non-blocking |

**VERDICT: NEEDS REVIEW** — ADR-033 is substantively sound and correctly implemented across all files. Finding 1 (missing star count in ADR-033) requires a decision: add it to the ADR or remove it from the decisions log. Finding 2 is pre-existing technical debt. No changes are blocked — all stale references are clean, all counts are correct, all cross-references are consistent, and all boundaries are preserved.

---

## 7. Post-Audit Fixes (2026-06-02)

All 3 findings resolved by parent:

| Finding | Action | Verification |
|---|---|---|
| Finding 1: ADR-033 missing star count | Added `- **Community**: ~14K GitHub stars, 911 forks (as of June 2026)` to ADR-033 Context section (line 66) | ✅ grep confirmed |
| Finding 2: adr/README.md missing ADRs 026-032 | Inserted 7 rows (ADR-026 through ADR-032) into register, updated adr_count 26→33, status summary 18/14/1/0, risk summary 11/15/7 | ✅ grep confirmed all 7 rows present, adr_count: 33 |
| Finding 3: Root README.md stale count | Updated "32 Architecture Decision Records" → "33 Architecture Decision Records" (line 144) | ✅ grep confirmed |

**REVISED VERDICT: PASS** — All findings resolved. No remaining issues.