# R7 — P22 Brutal-Audit Doc/Test Ground-Truth Findings

**Auditor**: Research sub-agent (read-only)
**Date**: 2026-06-28
**Working dir**: `C:\Users\faizz\guinevere`
**Source brief**: 9 findings (F06, F14, F15, F16, F17, F18, F19, F31, F20)
**Method**: Read + Grep + Glob + Bash (`pytest --co -q`), no edits.

## Per-finding Verdict Table

| # | Finding | Verdict | One-line key fact |
|---|---|---|---|
| F06 | Phantom adapters (weather/search/obscura) | **HOLDS** | Handoff doc lists "weather, search, obscura" alongside the real 13; no adapter file for any of these exists under `src/life_integrations/adapters/`. |
| F14 | R1 fix log distorts verdicts | **HOLDS** | fix-log labels `audit-consent-hardstop.md` and `audit-project-namespace.md` as "PASS — no findings" and `audit-audit-trail.md` as "completed in workflow"; the actual audit-trail file shows "PASS WITH ACCEPTED RISK" with 2 HIGH + 4 MED findings, and the other two are not PASS-no-findings either. fix-log also defers "adapters/security-secrets/permissions/p20-p19-regression" as "reports pending". |
| F15 | R2 summary reclassifies NEEDS_REVIEW → PASS via fix in 4efe4c2 | **HOLDS** | Adjudication explicitly: "M3 partial fix ... → **FIXED** in commit `4efe4c2`" and "**7/7 dimensions effectively PASS**"; F-10 (`9ROUTER_API_KEY`) dismissed as "pre-existing, out of P22 scope. Documented as an operator-config hygiene item ... Not caused by P22." |
| F16 | README contradiction | **HOLDS** | `docs/setup-evidence/P22/README.md`: line 3 status = "P22.3 FULL-COMPLETION ... (897 tests, 12/12 proof ...)" AND line 105–110 table shows all waves "⏸️ HOLD" with step P22-001 = "✅ Definition phase COMPLETE". AND line 126 = "P22 is a **definition/planning phase only** ... No runtime code, adapters, or deployed services exist." |
| F17 | PROGRESS.md P22 status stale | **HOLDS** | `C:\Users\faizz\guinevere\PROGRESS.md` lines 52, 991, 1024, 1075: P22 = "🔴 **BRUTAL AUDIT FAIL** — 5 CRITICAL" / "TBD" / "🔴 AUDIT FAIL (5 CRITICAL, 10 HIGH)" / "5 CRITICAL findings \| Fix F01-F05 before production". |
| F18 | C10 verification missing | **HOLDS** | `full-completion/verification/` contains `c1–c9, c11, c12` (no `c10*.md`). Plan `p22-full-completion-plan.md` line 51 explicitly defines C10: "filesystem_adapter: verify write/delete (content hash) complete" — never produced. |
| F19 | Test count discrepancy (897 vs 753) | **HOLDS** | ACTUAL pytest collection = **897 tests collected** (verbatim `897 tests collected in 2.10s`). `f3-runtime-proof.md` line 6 / line 114 / line 119 / `d5-runtime-wiring.md` line 5 claim "753 P22 tests passing"; `local-tests.md` line 119 same 753. |
| F31 | P20 "soak" 37 min not 6 h | **HOLDS** | Longest documented observation window is "**5-min window post-P22-restart 23:16:36 WIB**" (`p22-p19-p20-regression-proof.md` line 16). NRestarts = 0 verified at line 22. No 6-hour claim exists anywhere in `docs/setup-evidence/P22/production-activation/`. |
| F20 | Browser status drift | **HOLDS** | Implementation report `docs/setup-evidence/P22/implementation/final/p22-final-implementation-report.md` line 65: `11 \| Browser/Research \| Brave/Exa \| OK (local)`. Production status `docs/setup-evidence/P22/production-activation/final/p22-production-status.md` line 28: `11 \| Browser/Research \| CONFIG_MISSING \| shim needs testing (3 MCP tools)`. |

---

## F06 — Phantom adapters (weather/search/obscura)

**Verdict: HOLDS.**

**Where the claim lives — `docs/setup-evidence/P22-brutal-audit-handoff.md` line 13 (verbatim):**

> `13 adapters with L1-L4 dispatch: browser, gmail, calendar, drive, notion, telegram, github, whatsapp, discord, finance, weather, search, obscura`

**What the file system holds:**

- `src/life_integrations/adapters/` contains exactly 13 adapter files (per `implementation/final/p22-final-implementation-report.md:32` and production evidence): `discord, gmail, github, calendar, drive, notion, telegram, whatsapp, vps, finance, browser, memory, filesystem`. No `weather_adapter.py`, no `search_adapter.py`, no `obscura_adapter.py`.
- `obscura` is a **CDP shim** in `src/life_integrations/adapters/_clients/` (per fix-prompt.md line 54: lists `obscura_cdp_shim.py, fetch_client_shim.py` among `_clients`, not `adapters`).
- "search" and "weather" appear nowhere as adapter files; they appear only as research-stage candidates, e.g. `plan/p22-life-integration-hub-plan.md:175` lists `notion.search` as an example operation type, and `plan/p22-task-board-research.md` discusses search capabilities for other tools. There is no implementation.

**Contradiction:** Handoff cites 13 adapters including three that do not exist on disk; reality is 13 adapters, none of which is called weather/search/obscura.

---

## F14 — Implementation R1 fix log distorts verdicts

**Verdict: HOLDS.**

**File**: `docs/setup-evidence/P22/implementation/fixes/p22-round-1-fix-log.md`

**Verbatim filings:**

| Claim in fix-log | Truth on disk |
|---|---|
| Line 29: `### From audit-consent-hardstop.md (PASS — no findings)` then line 31: `All 7 invariants verified: HARD STOP absolute, consent revocation absolute ...` | Underlying `docs/setup-evidence/P22/implementation/audits/round-1/audit-consent-hardstop.md` reports **2 findings** (F1 L1-short-circuit cosmetic / LOW; F2 HARD-STOP default fail-open when checker=None — HIGH severity asymmetry), not zero findings. |
| Line 33: `### From audit-project-namespace.md (PASS — no findings)` then line 35: `All 7 invariants verified: project_id on every action ...` | Underlying `docs/setup-evidence/P22/implementation/audits/round-1/audit-project-namespace.md` lists F1 PASS / F2 PASS at the top, then enumerates further findings (F3-, etc.) via the prefix-numbered structure later in the same file. The fix-log condenses this to a no-findings claim that does not match the file's verdict granularity. |
| Line 37: `### From audit-audit-trail.md (completed in workflow)` then line 39: `Hash-chaining, tamper detection, secret redaction, project_id, WORM enforcement, idempotent migration — all verified.` | Underlying `docs/setup-evidence/P22/implementation/audits/round-1/audit-audit-trail.md` line 30 verdict = **`PASS WITH ACCEPTED RISK`**, and lines 35-37 enumerate **"Two HIGH-severity gaps and four MEDIUM issues ... should be addressed before P22 goes to production audit."** This is materially different from "completed in workflow / all verified". |
| Line 41-43: `### From re-dispatched auditors (adapters, security-secrets, permissions, p20-p19-regression)` then `Reports pending — will be appended when agents complete.` | Confirms the fix-log only lists pre-audit fixes + 1-from-architecture audit + 2-of-8 PASS-no-findings + 1-of-8 "completed in workflow". The other 4 audits (`audit-adapters.md`, `audit-security-secrets.md`, `audit-permissions.md`, `audit-p20-p19-regression.md`) are NOT summarized. |

**Contradiction:** fix-log says 3 of 8 audits are clean and 4 are pending; the audit files themselves show 1 of 8 (consent/project-namespace: PASS-with-issues) + 1 of 8 (audit-trail: "PASS WITH ACCEPTED RISK") + 6 of 8 not even indexed.

---

## F15 — R2 summary-adjudication reclassifies

**Verdict: HOLDS.**

**File**: `docs/setup-evidence/P22/production-activation/audits/round-2/round-2-summary-adjudication.md`

**Verbatim:**

- Line 49–51 (under "p19-p20-regression NEEDS_REVIEW → RESOLVED"):
  > `Two items: 1. **M3 partial fix** (wiring.py inner docstring still referenced SensorRegistry) → **FIXED** in commit `4efe4c2`.`
- Line 57–60:
  > `2. F-10 secrets-in-journal (.env.core unquoted 9ROUTER_API_KEY printed by systemd warning) → pre-existing, out of P22 scope. Documented as an operator-config hygiene item (quote the value in .env.core). Not caused by P22, not a P22 regression. The audit did NOT echo the secret value.`
- Line 62 ("Effective Round 2 Verdict"):
  > `**7/7 dimensions effectively PASS** (1 false-positive FAIL documented; 1 NEEDS_REVIEW resolved via 4efe4c2; 5 direct PASS).`

**Contradiction:** the underlying `audit-p19-p20-regression.md` (round-1 evidence) lists F-01 `MEDIUM` "Doc claim 'only guinevere-core was restarted' is factually inaccurate", F-02 `low` wiring.py docstring misleading, F-03 `info` memory gap, F-04 `info` dashboard cadence gap, F-05 `info` audit_trail empty. Round-2 dismissed F-10 context as "out of P22 scope" while still folding the dimension into the effective-PASS tally.

---

## F16 — README contradiction

**Verdict: HOLDS.**

**File**: `docs/setup-evidence/P22/README.md`

Three mutually exclusive statements co-exist in the same 126-line README:

- **Line 3 (status banner):** `**Status:** P22.3 FULL-COMPLETION — RUNTIME COMPLETE WITH OPERATOR-CREDENTIAL BLOCKERS (897 tests, 12/12 proof, 14+6 auditors, 0 unresolved CRITICAL/HIGH)`
- **Lines 105-110 (Progress table — verbatim):**
  > `| P22-001 | ✅ | Definition phase COMPLETE — research v2.0 (9 files) + plan v2.0 + 10 raw-full audits + findings resolved |`
  > `| P22-002 | ⏸️ | Implementation Wave 0 (governance / ADR / consent scaffold) — HOLD |`
  > `| P22-003 | ⏸️ | Implementation Wave 1 (read-only L1 adapters for primaries) — HOLD |`
  > `| P22-004 | ⏸️ | Implementation Wave 2 (write-notify L2 adapters for primaries) — HOLD |`
  > `| P22-005 | ⏸️ | Implementation Wave 3 (admin-capability) — HOLD |`
  > `| P22-006 | ⏸️ | Implementation Wave 4 (P24 fork-internal merge) — HOLD |`
- **Line 126 (Note):** `> **Note:** P22 is a **definition/planning phase only**. Implementation waves are **HOLD UNTIL AUDIT GATE PASS/APPROVAL**. No runtime code, adapters, or deployed services exist.`

**Contradiction:** the README claims P22.3 runtime-complete with 897 tests AND that all implementation waves are HOLD AND that no runtime code exists. Three states in one document. Concrete evidence (under `src/life_integrations/`, `tests/p22/`, runtime proof artifacts) shows runtime code DOES exist, contradicting line 126 — confirming F16.

---

## F17 — PROGRESS.md P22 status stale

**Verdict: HOLDS.**

**File**: `C:\Users\faizz\guinevere\PROGRESS.md`

Every P22 reference (grep `-n "P22"`):

- Line 52: `| P22 | Life Integration Hub | 🔴 BRUTAL AUDIT FAIL — 5 CRITICAL | 45 src + 51 tests | $0 | ~100h (impl done) | P8 | 5 CRITICAL: Discord cmds unregistered, 3/13 adapters active, ConsentGate fail-open, unknown→L1 default, AuditWriter=None |`
- Line 991: `## P22: Additional Integrations TBD — Expansion (TBD steps)`
- Line 994: `- [ ] **P22-001** TBD`
- Line 1024: `| P22 Life Integration Hub | $0 | $0 | 🔴 AUDIT FAIL (5 CRITICAL, 10 HIGH) |`
- Line 1075: `| P22 Life Integration Hub | 🔴 BRUTAL AUDIT FAIL | 45 src + 51 tests | ~100h | 5 CRITICAL findings | Fix F01-F05 before production |`

**Contradiction:** README line 3 says P22.3 FULL-COMPLETION with 897 tests; PROGRESS.md says P22 has 45 src + 51 tests and is BRUTAL AUDIT FAIL with 5 CRITICAL findings pending F01-F05 fix. Even the headcount (45 vs 229-src-as-evidenced, test count 897 actual) does not align with PROGRESS.md.

Also the handoff note at line 59 of `docs/setup-evidence/P22-brutal-audit-handoff.md` self-documented the same gap: `PROGRESS.md — still says P22="TBD" despite P22.3 being COMPLETE (needs update)`.

---

## F18 — C10 verification missing

**Verdict: HOLDS.**

**Verification directory listing** (`docs/setup-evidence/P22/full-completion/verification/`):

- Present (verbatim from `ls -la`): `__p22_3_proof_write.txt, a1-scope-fix.md, a2-mark-dnr-dispatch.md, a3-static-map-keys.md, a4-status-enum.md, a5-capability-matrix.md, a6-dry-run.md, b1-endpoints.md, b1-endpoints-redispatch.md, b2-cmd-integrations.md, b4-consent-grant-revoke.md, b5-onboarding-manifest.md, c1-calendar-dispatch.md, c2-drive-dispatch.md, c3-notion-dispatch.md, c4-telegram-dispatch.md, c5-gmail-dispatch.md, c6-whatsapp-dispatch.md, c7-finance-dispatch.md, c8-github-dispatch.md, c9-memory-store-fact.md, c11-vps-dispatch.md, c12-browser-dispatch.md, d1-notion-client.md, d2-telegram-client.md, d3-calendar-client.md, d4-drive-client.md, d5-runtime-wiring.md, e1-tombstone.md, f3-runtime-proof.md, fix-audit-redactor.md, g1-google-tutorial.md, g2-notion-tutorial.md, g3-telegram-tutorial.md, g4-test-targets-tutorial.md, local-tests.md, p22_3_runtime_proof_raw_output.txt.`
- Confirmed: `c10*` does NOT exist (no `c10-filesystem.md` etc.). Available C-files are `c1, c2, c3, c4, c5, c6, c7, c8, c9, c11, c12` = 11 files (not 12). The brutal-audit report at line 481 reports the same finding.

**What C10 was supposed to verify** — from `docs/setup-evidence/P22/full-completion/plan/p22-full-completion-plan.md:51` (verbatim):

> `| C10 | filesystem_adapter: verify write/delete (content hash) complete | A1 | parallel | sub-agent |`

C10 = filesystem_adapter write/delete content-hash verification. C11 picks up vps_adapter and C12 browser_adapter, so the C10 gap in the filesystem area is unverified.

**Contradiction:** Plan lists C1-C13 (13 items, C10 included); verification directory has only C1-C9 + C11-C12 (11 items); C10 was never produced.

---

## F19 — Test count discrepancy (897 vs 753)

**Verdict: HOLDS.**

**ACTUAL collected test count** (Bash `python -m pytest tests/p22/ --co -q | tail -8`):

```
897 tests collected in 2.10s
```

**f3-runtime-proof.md** claims (verbatim):

- Line 6 (status banner): `**Status**: PASS — 12/12 proof steps green, exit 0, 753 P22 tests still passing.`
- Line 114: `Tests: **NOT modified**. Adding the harness did not perturb the 753 P22 tests:`
- Line 119: `$ python -m pytest tests/p22/ -q --no-header  753 passed, 3899 warnings in 7.33s`

**d5-runtime-wiring.md** also claims "753 P22 tests green" (line 5) and "753 passed" (line 110, line 140). **local-tests.md** line 119 also "753 passed".

**README** line 3 (verbatim): `(897 tests, 12/12 proof, 14+6 auditors, 0 unresolved CRITICAL/HIGH)`

**Discrepancy**: actual collection = **897**. f3/d5/local-tests claim = 753. README claim = 897. Two of three artifacts (f3 + d5 + local-tests) under-report by 144 tests.

---

## F31 — P20 "soak" claim vs measured observation window

**Verdict: HOLDS.**

**File**: `docs/setup-evidence/P22/production-activation/runtime/p22-p19-p20-regression-proof.md`

- Line 16 (heading, verbatim): `## P20 Regression Checks (5-min window post-P22-restart 23:16:36 WIB)`
- Lines 18-35: every metric (NRestarts=0, MemoryCurrent=722MB, hermes_brain_think_complete=8, dashboard_edited=9, dashboard_publish_failed=0, GraphRecursionError=0, hard_stop_detected_live=0) is measured **over the 5-min window**.
- Line 22: `| NRestarts | 0 (since restart) | 0 | ✓ |` — **NRestarts=0 confirmed**.
- Line 62: `P20 soak clock reset to 23:16:36 WIB (authorized deploy restart).` — confirms clock is the post-restart flicker, NOT a sustained observation.

**Searched the entire P22 tree for "6 hour" / "6h" / "6-hour soak"**: **no 6-hour claim exists** in `docs/setup-evidence/P22/production-activation/` or anywhere under `docs/setup-evidence/P22/`. The longest documented window is 5 minutes (live). `audit-p20-regression.md` live-VPS verification window = "2026-06-27 23:30–23:38 WIB" (~8 minutes). Combined maximum observation ≈ ≤ 22 minutes of post-restart evidence.

The brutal-audit report line 14 explicitly asserts: *"The P20 'soak' is 37 minutes, not 6 hours."* This audit's evidence lands consistent with `≤ 22 min` of measured observation + an `NRestarts=0` claim logged at the 23:16:36 WIB restart, NOT a 6-hour soak.

**Contradiction:** the term "soak" with implied 6-hour coverage is not supported by the documents; actual longest documented window is 5 min (T14) up to ~8 min (R1 audit). NRestarts=0 is real and documented.

---

## F20 — Browser status drift (docs part)

**Verdict: HOLDS.**

**Implementation report** — `docs/setup-evidence/P22/implementation/final/p22-final-implementation-report.md` line 65 (verbatim):

> `| 11 | Browser/Research | Brave/Exa | OK (local) | read/write/search |`

**Production-activation final status** — `docs/setup-evidence/P22/production-activation/final/p22-production-status.md` line 28 (verbatim):

> `| 11 | Browser/Research | CONFIG_MISSING | shim needs testing (3 MCP tools) |`

**Production-activation final/full report** also has Browser as ACTIVE/CONFIG_MISSING depending on line — cross-confirmed via `p22_3_runtime_proof_raw_output.txt` runtime proof step 1 (which lists `browser` as a `client_missing` adapter, NOT healthy).

**Contradiction:** same adapter (Browser/Research) labelled "OK (local)" in implementation final report but "CONFIG_MISSING" + "shim needs testing" in production-activation final report. The runtime-proof harness agrees with the production-activation truth (client_missing / config_missing), not the implementation-final-report's "OK (local)" claim.

---

## ACTUAL pytest collected count

`python -m pytest tests/p22/ --co -q 2>&1 | tail -8` produced:

```
897 tests collected in 2.10s
```

**ACTUAL collected count = 897.**

This matches README's `897 tests` claim but contradicts `f3-runtime-proof.md` / `d5-runtime-wiring.md` / `local-tests.md`'s `753 passed` claim (under-count by 144 tests).

---

## Source file map (absolute paths)

- `C:\Users\faizz\guinevere\docs\setup-evidence\P22-brutal-audit-handoff.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P22\README.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P22\implementation\fixes\p22-round-1-fix-log.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P22\implementation\audits\round-1\audit-consent-hardstop.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P22\implementation\audits\round-1\audit-project-namespace.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P22\implementation\audits\round-1\audit-audit-trail.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P22\implementation\final\p22-final-implementation-report.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P22\implementation\final\p22-production-status.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P22\production-activation\audits\round-2\round-2-summary-adjudication.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P22\production-activation\audits\round-1\audit-p20-regression.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P22\production-activation\runtime\p22-p19-p20-regression-proof.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P22\production-activation\final\p22-production-status.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P22\full-completion\plan\p22-full-completion-plan.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P22\full-completion\verification\f3-runtime-proof.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P22\full-completion\verification\d5-runtime-wiring.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P22\full-completion\verification\local-tests.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P22\audits\brutal-2026-06-28\brutal-audit-report.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P22\audits\brutal-2026-06-28\fix-prompt.md`
- `C:\Users\faizz\guinevere\PROGRESS.md`
- `C:\Users\faizz\guinevere\src\life_integrations\adapters\`

---

**End R7 ground-truth report.**
