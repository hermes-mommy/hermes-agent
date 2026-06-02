# AGENTS.md — v2.1 Process-Rule Update: Insertion Map

> **Task**: Map AGENTS.md insertion points for requested v2.1 process-rule update.
> **Date**: 2026-06-01
> **Prepared for**: Faiz (Darling) / Guinevere
> **Source file**: /AGENTS.md (689 lines, 14 sections)

---

## 1. Section Overview — Exact Anchors

| Anchor | Heading | Lines | Type | Notes |
|--------|---------|-------|------|-------|
| §0 | Identity | 18–100 | Section | Contains blocking list (L45–58) |
| §1 | Super-Autopilot Mode | 103–136 | Section | 13-step workflow + Rules (L127–136) |
| §2 | Execution Mandates | 138–233 | Section | Subsections 1–10 (L140–233) |
| §2.1 | Consent-Safety Mandate | 140–144 | Subsection | Safety-affecting domains |
| §2.2 | Parallel + Unlimited Sub-Agent Spawning | 146–160 | Subsection | Wave pattern steps 1–7 (L150–160) |
| §2.5 | Planner-After-Research Sequencing | 162–164 | Subsection | Short paragraph |
| §2.5.1 | Planner Output → Todo Sync Gate | 166–175 | Sub-subsection | 4-step gate checklist + retry fallback |
| §2.6 | Implementation Collision Scan | 177–190 | Subsection | Collision table (L181–188) + rule |
| §2.3 | Decompose then Delegate | 192–194 | Subsection | Task decomposition rules |
| §2.4 | Anti-Duplication Rule | 196–198 | Subsection | No duplicate search |
| ### 5. | **Parent Verification Protocol** | 200–211 | Subsection | 8-item checklist |
| ### 6. | Continuation via 	ask_id | 213–215 | Subsection | Resume on failure |
| ### 7. | Idempotency and Re-run Safety | 217–219 | Subsection | Re-run safety |
| ### 8. | Parallel Session Coordination | 221–223 | Subsection | Shared writer detection |
| ### 9. | File-Based Sub-Agent Output | 225–227 | Subsection | File-based deliverable rule |
| ### 10. | Per-Step Implementation Auditor Gate | 229–233 | Subsection | Auditor spawning rules |
| §3 | Session-Start Workflow | 235–254 | Section | 16-step startup sequence |
| §4 | Post-Step Checklist | 256–269 | Section | 10-item checklist |
| §5 | Anti-Pattern Catalog (BLOCKING) | 271–332 | Section | 7 subsections + ✅ resolutions |
| §5 — Type Safety Bypass | | 275–280 | Subsection | Anti-patterns |
| §5 — Error Handling Bypass | | 282–287 | Subsection | Anti-patterns |
| §5 — Test and Verification Suppression | | 289–295 | Subsection | Anti-patterns |
| §5 — Sub-Agent Output Anti-Patterns | | 297–303 | Subsection | Anti-patterns |
| §5 — Secret and Consent Exposure | | 305–312 | Subsection | Anti-patterns |
| §5 — Persona-Risk Anti-Patterns | | 314–323 | Subsection | Anti-patterns |
| §5 — Operator-Process Anti-Patterns | | 325–332 | Subsection | Anti-patterns |
| §6 | Escalation Rules | 334–363 | Section | Triggers 1–5 |
| §7 | Operator Protocol | 366–402 | Section | Faiz Says / Auto-handle / Ask |
| §8 | Reference Tables | 404–444 | Section | Document families + tie-breakers + files |
| §9 | Repository Isolation | 446–470 | Section | Never Share / Allowed to Reuse |
| §10 | Appendix A — Full Task Template | 472–484 | Section | Invocation template |
| §11 | Appendix B — Evidence Schema | 486–499 | Section | Evidence minimum schema |
| §12 | Appendix C — Tool/MCP Selection | 501–518 | Section | Tool hierarchy |
| §13 | Footer | 520–543 | Section | Versioning (L522–527), Maintenance (L529–536), Sign-Off (L538–540) |
| §14 | Tooling Notes | 546–689 | Section | Practical rules (7 subsections + workflow gates) |

---

## 2. Insertion Points for Requested Changes

### 2.1 Parent Verification Anti-Patterns (NEW)

**Request**: Add parent verification anti-patterns to the Anti-Pattern Catalog.

**Recommended location**: §5 Anti-Pattern Catalog (BLOCKING) — after **Test and Verification Suppression** (ends L295) and before **Sub-Agent Output Anti-Patterns** (starts L297).

**Exact insertion region**:
`
L295: - ✅ Fix root cause; kalau test benar-benar gagal, code/spec yang salah
L296: (blank line)
L297: ### Sub-Agent Output Anti-Patterns
`

**Insert**: A new ### Parent Verification Anti-Patterns subsection between L296 and L297.

**Suggested content** (6 anti-pattern items):
`
- ❌ Claim "parent verified" without reading sub-agent report files
- ❌ Approve sub-agent output based only on inline verdict, skipping file read
- ❌ Mark step complete before auditor gate passes ("verify later" trap)
- ❌ Ignore or silently accept pre-existing diagnostics in changed files
- ❌ Trust sub-agent self-verification without independent parent spot-check
- ✅ Read every sub-agent report file; separate pre-existing vs introduced issues; always wait for auditor gate
`

**Formatting risks**: ✅ Low — follows existing §5 subsection pattern. Blank line before heading maintained. ✅/❌ pattern consistent.

---

### 2.2 Sub-Agent One-Step Scope Rule (NEW)

**Request**: Add rule that each sub-agent should handle exactly one step/sub-task (one-step scope).

**Option A (Recommended — no renumbering)**: Add as a new bullet in **§1 Rules** (L127–136), after "Delegate by default" (L131).

**Insertion region**:
`
L131: - **Delegate by default**: sub-agents handle substantive research/implementation/review; parent orchestrates and verifies.
L132: (insert new rule here)
`

**Suggested text**:
`
- **One-step scope per sub-agent**: setiap sub-agent menangani tepat satu atomic task/step dari decomposition planner. Sub-agent tidak boleh menerima multi-step scope kecuali step tersebut benar-benar trivial dan didokumentasikan sebagai pengecualian. Parent yang memecah scope, bukan sub-agent yang menentukan.
`

**Option B (requires renumbering)**: Insert as ### 2.7 in §2.

**Insertion region** (between L190 and L192):
`
L189: No collision scan = implementation wave is not allowed.
L190: (blank line)
L191: (blank line — insert here)
L192: ### 3. Decompose then Delegate
`

**🔴 RENUMBERING CASCADE** if Option B:
| Current | → New |
|---------|-------|
| ### 3. (L192) | ### 4. |
| ### 4. (L196) | ### 5. |
| ### 5. (L200) | ### 6. |
| ### 6. (L213) | ### 7. |
| ### 7. (L217) | ### 8. |
| ### 8. (L221) | ### 9. |
| ### 9. (L225) | ### 10. |
| ### 10. (L229) | ### 11. |

**Cross-ref audit required**: grep for §2\.\d references in AGENTS.md, docs/README.md, and ADRs.

**Formatting risks**: 🔴 HIGH for Option B (subsection renumbering cascade); 🟢 LOW for Option A (single bullet insertion).

---

### 2.3 Planner Determines Parallelism/Dependencies (ENHANCEMENT)

**Request**: Clarify that the planner determines parallelism groupings, dependency graph, and execution sequencing.

**Two affected locations**:

**Location A — §2.2, step 4 (L157–158)**: Amend the "Planner todo sync" description.

`
L157: 4. **Planner todo sync**: parent reads the planner file and updates 	odowrite to the planner's exact atomic tasks before implementation. If the planner output changes scope/order/evidence/auditor paths, todos must reflect that before any implementation begins.
`
→ **Append**: " Planner also determines parallelism groupings and dependency graph; parent must not parallelize outside the planner's dependency map."

**Location B — §1, Rule "Planner-output controls execution" (L130)**:
`
L130: - **Planner-output controls execution**: setelah planner file dibuat, parent wajib membaca file itu lalu update todo list agar match atomic planner tasks, dependencies, evidence paths, auditor paths, dan collision decisions. Planner yang tidak mengubah todo = incomplete planner gate.
`
→ **Append**: " Planner juga menentukan parallelism groupings dan dependency graph; parent tidak boleh parallelize di luar dependency map planner tanpa documented justification."

**Formatting risks**: 🟢 LOW — inline edit with clear oldString match available.

---

### 2.4 §2 Rule 5 Note (ANNOTATION)

**Request**: Add footnote/note to §2.2, step 5 — "Implementation wave" (L158).

**Exact location**:
`
L157: 4. **Planner todo sync**: parent reads the planner file and updates 	odowrite to the planner's exact atomic tasks before implementation. If the planner output changes scope/order/evidence/auditor paths, todos must reflect that before any implementation begins.
L158: 5. **Implementation wave**: fire independent implementation clusters after collision scan.
L159: 6. **Verify wave by parent**: diagnostics/tests/DoD/evidence.
`

**Insert**: A note indented under step 5, between L158 and L159.

**Suggested text**:
`
    > **Note**: The planner output defines which clusters are independent and may be parallelized. Parent must not parallelize beyond the planner's dependency graph without documented re-verification of collision safety.
`

**Formatting risks**: 🟢 LOW — single note paragraph insertion. Use > blockquote for visual distinction.

---

### 2.5 v2.1 Footer Bump (VERSION TABLE + FOOTER)

**Request**: Bump version table to v2.1, update footer metadata.

**Exact location**: §13 Footer → ### Versioning (L522–527)

**Insert**: New row after L526 (v2.0 row), before L527 (v1.0 row).

**Current content**:
`
L524: | Version | Date | Author | Changes |
L525: |---|---|---|---|
L526: | 2.0 | 2026-05-31 | Faiz + Guinevere | Full rewrite following Aizanta Future template structure (§0-§14). Added pervasive sugar-mommy persona, consent-safety mandate, HARD STOP protocol, persona-risk anti-patterns, domain-adapted reference tables. |
L527: | 1.0 | 2026-05-30 | Hephaestus / Guinevere | Initial Guinevere project operating contract. |
`

**Inserted row**:
`
| 2.1 | 2026-06-01 | Faiz + Guinevere | Added parent verification anti-patterns (§5), sub-agent one-step scope rule (§1/§2.7), planner parallelism/dependency enhancement (§2.5.1/§1), §2 Rule 5 note, and v2.1 footer bump. |
`

**Also consider**:
- **Operator Sign-Off** (L538–540): Date bump to 2026-06-01 and add scope note if re-signing
- **Maintenance** (L529–536): Verify none of the new rules require new maintenance bullets

**Formatting risks**: 🟡 MEDIUM — pipe table line must not break across lines. Keep the "Changes" column content on one line or carefully wrap with continuation pipe.

---

## 3. Cross-Reference Impact Matrix

| Change | Affects Lines | Renumbering? | Doc-Link Updates? | Safety Boundary? |
|--------|---------------|-------------|-------------------|------------------|
| Parent verification anti-patterns (§5) | L295–297 | No | No | No |
| Sub-agent one-step scope (§1) | L131 | No | No | No |
| Sub-agent one-step scope (§2.7 — Option B) | L190–192 | Yes (8 subsections) | Yes — all §2.n refs | No |
| Planner parallelism/deps (§2.2 + §1) | L130, L157 | No | No | No |
| §2 Rule 5 note | L158–159 | No | No | No |
| v2.1 footer bump | L524–527 | No | No | No |

---

## 4. Execution Sequence

`
Step 1: Planner parallelism/deps enhancement
        → Edit L130 and L157 (two edit calls, independent)
Step 2: §2 Rule 5 note
        → Insert note between L158–159
Step 3: Sub-agent one-step scope
        → Option A: Insert bullet after L131 (§1 Rules)
        → Option B: Insert §2.7 subsection + renumber L192→L229
Step 4: Parent verification anti-patterns
        → Insert subsection between L296–297
Step 5: v2.1 footer bump (MUST BE LAST)
        → Insert version table row + update sign-off date
`

Steps 1–4 are independent (no shared lines). Step 5 MUST be last to correctly reflect all changes.

---

## 5. Summary

| # | Change | Location (Lines) | Recommended Approach | Risk |
|---|--------|-----------------|---------------------|------|
| 1 | Parent verification anti-patterns | §5, after L295 | New ### subsection, 6 items | 🟢 Low |
| 2 | Sub-agent one-step scope | §1, after L131 (preferred) | New bullet rule | 🟢 Low |
| 2b | (Alt) Sub-agent one-step scope | §2, before L192 | New ### 2.7 + full renumber | 🔴 High |
| 3 | Planner parallelism/deps | §1 L130 + §2.2 L157 | Edit two existing lines | 🟢 Low |
| 4 | §2 Rule 5 note | §2.2, after L158 | Insert blockquote note | 🟢 Low |
| 5 | v2.1 footer bump | §13, after L526 | Insert table row + sign-off date | 🟡 Medium |

### Option A (Recommended — minimal risk): §1-based insertion for scope rule
- ✅ No renumbering cascade
- ✅ All 5 changes fit in 5 isolated edit calls
- ✅ Step 5 (footer) is the only dependency

### Option B (Full structural): §2.7-based insertion for scope rule
- ❌ Renumbering cascade affects 8 subsections
- ❌ Cross-reference audit required across AGENTS.md + docs/
- ❌ Higher verification burden before auditor can pass

---

*End of report. Full AGENTS.md analyzed: 689 lines, 14 sections, 50+ subsection headings.*
