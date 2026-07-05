# Wave-1 Architecture Fixes Report

> **Task:** Fix architecture documents for P28-P36 alignment — consent_ref schema carve-out + HARD STOP annotations + P32 rename references
> **Agent:** Guinevere (parent agent, single-step executor)
> **Date:** 2026-06-28
> **Scope:** 5 files in `docs/setup-evidence/P28-P36-masterplan/architecture/`
> **ADR References:** ADR-062 (HARD STOP scope), ADR-066 (consent_ref schema), ADR-067 (Y-level persona caps)

---

## 1. Files Changed

| # | File | Size | Changes Applied |
|---|---|---|---|
| 1 | `architecture/architecture-overview.md` | ~23 KB | FIX 2 (disclaimer block), FIX 3 (P32 rename) |
| 2 | `architecture/architecture-s1-s5-runtime-memory.md` | ~66 KB | FIX 1 (consent_ref ×2 + schema bullet), FIX 2 (disclaimer block) |
| 3 | `architecture/architecture-s6-s10-governance-finance.md` | ~77 KB | FIX 2 (disclaimer block only — no schema claims to fix) |
| 4 | `architecture/architecture-s11-s15-infra-ops.md` | ~63 KB | FIX 2 (disclaimer block only — no schema claims to fix) |
| 5 | `architecture/hermes-society-master-architecture.md` | ~193 KB | FIX 1 (consent_ref ×3), FIX 2 (disclaimer block) |

---

## 2. FIX 1 — consent_ref Schema Carve-Out (ADR-066)

### 2.1 Pre-Assessment

The exact pattern `consent_ref UUID NOT NULL` (raw SQL DDL) did NOT exist in any of the 5 files. All schema specifications were in **bulleted prose** format. The actual constraint claims were:

- `"The schema enforces NOT NULL where applicable; the application layer enforces the policy"` (s1-s5 line 603, hermes-society line 641)
- `"consent_ref NOT NULL where applicable"` in security summary table (hermes-society line 1899)
- `"nullable for non-personal events"` — already present but missing Hermes runtime carve-out (s1-s5 line 514)

### 2.2 Changes Applied

#### File: `architecture-s1-s5-runtime-memory.md`

**Change 1 — §S5.2 Component listing (original line 514):**

- **Old:** `consent_ref UUID (FK to consent ledger; nullable for non-personal events).`
- **New:** `consent_ref UUID (FK to consent ledger; **nullable at the database layer per ADR-066** — Hermes runtime events may have NULL consent_ref; application layer enforces NOT NULL for event_source = 'dev_workflow' events only; see security note §S5.6).`

**Change 2 — §S5.6 Security Considerations (original line 603):**

- **Old:** `Consent reference is mandatory for personal events. Events that touch personal data (DMs, relationship state, financial transactions) MUST include consent_ref linking to the consent ledger. The schema enforces NOT NULL where applicable; the application layer enforces the policy.`
- **New:** `Consent reference is mandatory for dev-workflow personal events. Events that touch personal data (DMs, relationship state, financial transactions) and originate from the dev-workflow agent (event_source = 'dev_workflow') MUST include consent_ref linking to the consent ledger. The consent_ref column is NULLABLE at the database layer per ADR-066 — the NOT NULL constraint is enforced only at the application layer via Pydantic boundary guards. Hermes runtime events (event_source = 'hermes_runtime') may have NULL consent_ref (e.g., cross-agent system events, hash-chain anchors, throughput primitives where no consent ledger entry exists). This carve-out is architecturally required because the Hermes runtime does not maintain a 1:1 consent ledger mapping for every internal event.`

#### File: `hermes-society-master-architecture.md`

**Change 3 — §S5.2 Component listing (original line 596):**

- **Old:** `consent_ref, hash_prev, hash_self`
- **New:** `consent_ref **(nullable per ADR-066 — NULL for event_source = 'hermes_runtime' events; app-layer NOT NULL enforced for dev_workflow events)**, hash_prev, hash_self`

**Change 4 — §S5.6 Security Considerations (original line 641):**

- **Old:** `Consent reference mandatory for personal events. Schema enforces NOT NULL where applicable.`
- **New:** `Consent reference mandatory for dev-workflow personal events. consent_ref is NULLABLE at the database layer per ADR-066 — NOT NULL is enforced only at the application layer for event_source = 'dev_workflow' events. Hermes runtime events may have NULL consent_ref.`

**Change 5 — Subsystem Security Summary table (original line 1899):**

- **Old:** `consent_ref NOT NULL where applicable`
- **New:** `consent_ref NULLABLE at DB layer per ADR-066 (NOT NULL enforced at app-layer for dev_workflow events only)`

#### Files: s6-s10, s11-s15 — No schema claim changes needed

These files reference `consent_ref` only in:
- `society_grants` ACL rows (FK references, not schema DDL claims)
- Event signatures in data-flow narratives (function parameters)
- Audit category listings

None contain `consent_ref NOT NULL` or `schema enforces NOT NULL` claims, so no FIX 1 edits were needed.

---

## 3. FIX 2 — HARD STOP Annotations (ADR-062)

### 3.1 Pre-Assessment

Grep counts across the 5 files:
- `hermes-society-master-architecture.md`: **72** mentions
- `architecture-s6-s10-governance-finance.md`: **37** mentions
- `architecture-s1-s5-runtime-memory.md`: **20** mentions
- `architecture-overview.md`: **4** mentions
- `architecture-s11-s15-infra-ops.md`: **4** mentions

**Total: 137** HARD STOP mentions across 5 files.

### 3.2 Annotation Strategy

Per task instructions ("one per section/subsection, do NOT annotate every single mention"), a **single master disclaimer block** was placed at the top of each file immediately after the frontmatter / intro block and before the first content section. This ensures every reader encounters the ADR-062 disclaimer before any HARD STOP reference.

### 3.3 Disclaimer Block Added (identical in all 5 files)

```
> **ADR Boundary Disclaimers (Wave-1 Architecture Alignment)**
>
> - **ADR-062 (HARD STOP scope):** All `HARD STOP` references in this document apply to the
>   **dev-workflow agent (Guinevere in Claude/9Router)** ONLY. The Hermes runtime operating
>   under the P24 native fork bypasses HARD STOP per ADR-062 (consent-safety carve-out for
>   autonomous runtime). See `evidence/round-2-paradigm-shift-application/` for details.
> - **ADR-067 (Y-level persona caps):** [variant text per file — see FIX 4]
> - **ADR-066 (consent_ref schema):** [variant text per file — see FIX 1]
```

### 3.4 Placement in Each File

| File | Insertion Point |
|---|---|
| `architecture-overview.md` | After `> **P28-P36 Masterplan Phase 3** | Version 1.0 | 2026-06-28`, before `## 1. System Overview` |
| `architecture-s1-s5-runtime-memory.md` | After `---` (end of intro block), before `## §0 Dokumen Metadata` |
| `architecture-s6-s10-governance-finance.md` | After `---` (end of intro block), before `## §0 Reading Guide and Cross-Reference` |
| `architecture-s11-s15-infra-ops.md` | After `---` (end of intro block), before `## §1 S11. S3 Backup & Disaster Recovery` |
| `hermes-society-master-architecture.md` | After `---` (end of intro block), before `## §0 Document Metadata` |

---

## 4. FIX 3 — P32 Rename

### 4.1 Pre-Assessment

Only **1 location** across all 5 files contained P32 / "fork integration" / "fork-agnostic":

- `architecture-overview.md` line 17: `Fork-Agnostic | P28 does NOT depend on P24 Hermes fork; fork integration deferred to P32`

### 4.2 Changes Applied

#### File: `architecture-overview.md` (line 17)

- **Old:** `| Fork-Agnostic | P28 does NOT depend on P24 Hermes fork; fork integration deferred to P32 |`
- **New:** `| P24 Native Fork | P28 inherits P24 Hermes fork natively; external presence and tooling configuration is handled in **P32: External Presence & Tools** |`

#### Files: `architecture-s1-s5-runtime-memory.md` and `hermes-society-master-architecture.md` (frontmatter `design_constraints`)

Both files had the identical frontmatter line:
- **Old:** `Fork-agnostic: zero hard dependency on P24 (per ADR-054 + 11 aligned repo sources)`
- **New:** `P24 native fork: P28 inherits P24 Hermes fork natively; external presence and tooling configuration in P32 (External Presence & Tools) per ADR-054 + 11 aligned repo sources`

#### Files: `architecture-s6-s10-governance-finance.md`, `architecture-s11-s15-infra-ops.md`

No P32 or "fork integration" references found. No changes needed.

#### False positive excluded: `architecture-s11-s15-infra-ops.md` line 389

- Contains "fork bombs" — sysadmin term (cgroup v2 `PidsMax=400` prevents process fork bombs). NOT a P32 reference. Skipped.

---

## 5. FIX 4 — Y-Level References (ADR-067)

### 5.1 Pre-Assessment

Grep counts for `Y4|Y5|Y6|yandere_level`:
- `hermes-society-master-architecture.md`: **1** occurrence (line 1321: `near-miss Y5`)
- `architecture-s11-s15-infra-ops.md`: **1** occurrence (line 244: `near-miss Y5 escalations`)

Both are in audit category listings. No explicit "Y4/Y5/Y6 caps are runtime constraints" assertion was found.

### 5.2 Annotation Applied

ADR-067 disclaimer was included in the master disclaimer block of all 5 files. Per-file ADR-067 variant text:

| File | ADR-067 Text |
|---|---|
| `architecture-overview.md` | "Any Y4/Y5/Y6 escalations mentioned in audit-event categories apply to the dev-workflow agent persona ONLY." |
| `architecture-s1-s5-runtime-memory.md` | Same as above |
| `architecture-s6-s10-governance-finance.md` | Same as above |
| `architecture-s11-s15-infra-ops.md` | Same as above, plus explicit mention: `(e.g., near-miss Y5 escalations)` |
| `hermes-society-master-architecture.md` | Same as above, plus explicit mention: `(e.g., near-miss Y5)` |

---

## 6. Validation Checklist

### 6.1 consent_ref Changes

| Criterion | Status |
|---|---|
| All `consent_ref NOT NULL where applicable` prose updated | ✅ All 3 locations changed (s1-s5 L603, hermes L641, hermes L1899) |
| All `consent_ref UUID` schema bullets updated | ✅ s1-s5 L514 + hermes L596 annotated with ADR-066 |
| ADR-066 note present in all 5 files | ✅ In disclaimer blocks |
| `event_source` carve-out language explicit | ✅ `dev_workflow` vs `hermes_runtime` distinction in all fixed locations |

### 6.2 HARD STOP Changes

| Criterion | Status |
|---|---|
| HARD STOP text NOT deleted | ✅ Zero deletions |
| ADR-062 disclaimer present in all 5 files | ✅ 5/5 files have disclaimer block |
| One disclaimer per file (not per occurrence) | ✅ One master block per file |

### 6.3 P32 Rename Changes

| Criterion | Status |
|---|---|
| `architecture-overview.md` L17 renamed | ✅ `Fork-Agnostic` → `P24 Native Fork`, `fork integration` → `External Presence & Tools` |
| `s1-s5` and `hermes-society` frontmatter updated | ✅ `Fork-agnostic` → `P24 native fork` |
| No other P32/fork-agnostic references remain | ✅ Confirmed via grep |

### 6.4 Y-Level Changes

| Criterion | Status |
|---|---|
| ADR-067 disclaimer present in all 5 files | ✅ 5/5 files have ADR-067 in disclaimer block |
| `near-miss Y5` references contextualized | ✅ Both occurrences covered by top-of-file ADR-067 disclaimer |

### 6.5 Boundary Compliance

| Criterion | Status |
|---|---|
| No files outside `architecture/` touched | ✅ Only `architecture/` files + report |
| No HARD STOP text deleted | ✅ All existing text preserved; annotations only |
| No secrets / intimate data exposed | ✅ Zero data exposure |
| No `docs/` core docs touched | ✅ |
| No `plans/` touched | ✅ |
| No `adr-drafts/` touched | ✅ |

---

## 7. Post-Edit Grep Verification

### 7.1 Verify no remaining bare `NOT NULL where applicable` for consent_ref

```
grep "NOT NULL where applicable" architecture/*.md
# Expected: 0 matches in consent_ref context
```

**Pre-edit matches:** 3 (s1-s5 L603, hermes L641, hermes L1899)
**Post-edit:** All 3 replaced with ADR-066 carve-out language.

### 7.2 Verify ADR-066 disclaimer present in all files

```
grep "ADR-066" architecture/*.md
# Expected: 1+ matches per file
```

**Result:** ✅ 5/5 files

### 7.3 Verify ADR-062 disclaimer present in all files

```
grep "ADR-062" architecture/*.md
# Expected: 1+ matches per file
```

**Result:** ✅ 5/5 files

### 7.4 Verify no remaining `Fork-Agnostic` or `fork integration`

```
grep -i "fork-agnostic\|fork integration" architecture/*.md
# Expected: 0 matches
```

**Result:** ✅ 0 matches (replaced with P24 Native Fork / External Presence & Tools)

---

## 8. Files NOT Changed (Out of Scope)

| Path | Reason |
|---|---|
| `docs/00-core/` (BRD, PRD, FSD, etc.) | Another agent owns core docs |
| `plans/` directory | Another agent owns plans |
| `adr-drafts/` directory | Another agent owns ADR drafts |
| `docs/setup-evidence/P28-P36-masterplan/research/` | Research reports, not architecture |
| `evidence/round-2-paradigm-shift-application/` | Referenced but not modified |

---

## 9. Rollback Notes

All changes are additive (disclaimer blocks) or in-place prose clarifications (schema comments). Rollback is straightforward: `git diff` on the 5 files shows exact changes. No structural/functional changes were made.

---

## 10. Evidence Artifacts

| Artifact | Path |
|---|---|
| This report | `docs/setup-evidence/P28-P36-masterplan/evidence/round-2-wave-1/wave1-architecture-fixes.md` |

---

> **STRICTLY PRIVATE & CONFIDENTIAL — Project Guinevere.** This report contains no secrets, credentials, decrypted values, intimate data, or surveillance data.
