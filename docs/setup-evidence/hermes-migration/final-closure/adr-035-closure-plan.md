# ADR-035 Final Closure Plan

> Date: 2026-06-07
> Scope: Resolve B10/B11/B12 governance posture, determine ADR-035 IMPLEMENTED status, and update supporting project records.
> Oracle gate: `bg_38533336` — **IMPLEMENTED with accepted-risk note**
> Status: PLANNED

---

## 1. Executive Gate

Oracle verdict: **ADR-035 can be marked IMPLEMENTED now, with one accepted-risk note and two documentation-resolved blockers.**

### Binding closure decisions

| Item | Decision | Rationale |
|---|---|---|
| **B10** | **Accepted Risk** | Missing `secrets/backup/` SOPS credential set is a DR operational gap, not a migration architecture invalidator. Verified fallback backups exist: Hermes zip, PostgreSQL dump, Redis BGSAVE. |
| **B11** | **Resolved (docs update)** | Backup sentinel exists at `/home/guinevere/.backup/last-success`; original register path `/var/log/guinevere/last-backup-success` is stale and must be updated to the operational path. |
| **B12** | **Resolved (docs update)** | Hermes-native metrics now exist (`hermes_safety_blocks_total`, `hermes_session_count`, `hermes_message_count_total`); `hermes_gateway_up` is intentionally blocked, not missing by oversight. |
| **ADR-035** | **IMPLEMENTED** | The Hybrid Hermes Migration architecture is live. Remaining DR caveat is documented as accepted operational risk, not as an architecture blocker. |
| **Commit + tag** | **Allowed after doc updates + validation** | User explicitly requested final status flip, commit, and tag. |

### Must not overclaim

- Do **not** claim cloud restore readiness for encrypted S3/R2 backups without restored age key / `secrets/backup/` material.
- Do **not** claim `/var/log/guinevere/last-backup-success` exists; only `/home/guinevere/.backup/last-success` is verified.
- Do **not** claim `hermes_gateway_up` exists; document that it is intentionally not emitted from core/FastAPI metrics.
- Do **not** reopen resolved B3/B8/B1/B5/B6/B7 work unless needed for wording accuracy.

---

## 2. Research Inputs and Evidence

### Primary records

- `AGENTS.md`
- `docs/20-security/hermes-phase-7-blocker-register.md`
- `adr/ADR-035-hermes-migration.md`
- `PROGRESS.md`
- `docs/IMPLEMENTATION_GUIDE.md`
- `CHECKLIST.md`
- `docs/10-governance/decisions-log.md`

### Supporting evidence

- `docs/setup-evidence/hermes-migration/phase-7c-b1/mcp-service-fix-verification.md`
- `docs/setup-evidence/hermes-migration/phase-7c-b3-b8/AUDIT-metrics-completeness.md`
- `docs/setup-evidence/hermes-migration/phase-7c-b3-archive/AUDIT-import-migration-final.md`
- `B6-B7/01-backup-state.md`

### Oracle decision

- `bg_38533336` — structured verdict: IMPLEMENTED with accepted-risk note; B10 accepted risk; B11 resolved via docs; B12 resolved via docs; commit+tag justified.

---

## 3. Files to Update

### 3.1 Blocker register

**Path:** `docs/20-security/hermes-phase-7-blocker-register.md`

**Required changes:**
1. Summary row: update Resolved count.
2. Replace line-16 style blanket rule (`All 12 blockers...`) with current governance truth:
   - ADR-035 is implemented as of 2026-06-07.
   - B10 is accepted operational DR risk.
   - Remaining items tracked as operational caveats/follow-ups, not architecture blockers.
3. Update B10 entry:
   - Status → `Accepted Risk — documented at ADR-035 implementation closure`
   - Description/Impact remain accurate.
   - Replace remediation language with accepted-risk note + offline age-key recovery requirement.
4. Update B11 entry:
   - Status → `Resolved — sentinel path updated to /home/guinevere/.backup/last-success`
   - Description reflects operational sentinel path.
5. Update B12 entry:
   - Status → `Resolved — metrics exported; gateway_up intentionally blocked`
   - Description references actual exported metrics and design decision.
6. Appendix summary gates:
   - Remove B10/B11 from backup gate blockers if posture changes to accepted risk / resolved.
   - Remove B12 from monitoring-completeness blockers.
   - Replace `ADR-035 IMPLEMENTED | All (B1-B12) | 7c` with a closed-state note or remove the blocker-row framing.

### 3.2 ADR-035

**Path:** `adr/ADR-035-hermes-migration.md`

**Required changes:**
1. Frontmatter `status: "Accepted"` → `status: "Implemented"`.
2. Status section body `Accepted` → `Implemented`.
3. Add an **Implementation Note** section near the top or footer addendum:
   - Date: 2026-06-07
   - State that migration architecture is implemented.
   - B10 accepted risk caveat.
   - B11 operational sentinel path.
   - B12 exported metrics + intentional `hermes_gateway_up` omission.
4. Preserve original ADR decision content; do not rewrite history.

### 3.3 PROGRESS tracker

**Path:** `PROGRESS.md`

**Required changes:**
1. Header/status line currently stale at Phase 6 latest.
2. Update top-level status to reflect:
   - P0-P10 or equivalent current completion framing as appropriate for this repo’s terminology.
   - ADR-035 IMPLEMENTED on 2026-06-07.
   - Mention accepted DR caveat if needed briefly.
3. Add/refresh a Hermes migration closure summary section or latest-update note with:
   - B1 MCP service fixed.
   - B3 archive completed.
   - B5 9Router loopback.
   - B6/B7 fallback backup artifacts.
   - B8 Hermes metrics safe subset.
   - B10 accepted risk, B11/B12 docs resolved.
4. Avoid a full rewrite of all historical sections; perform minimal honest update.

### 3.4 Implementation guide

**Path:** `docs/IMPLEMENTATION_GUIDE.md`

**Required changes:**
1. Update top metadata (`Last updated`).
2. Add a concise note near intro or relevant migration section that ADR-035 is implemented as of 2026-06-07.
3. If backup/DR is mentioned, reference fallback backups and accepted-risk caveat rather than overstating restic restore readiness.

### 3.5 Checklist

**Path:** `CHECKLIST.md`

**Required changes:**
1. Update high-level readiness/status metadata if it still says READY FOR EXECUTION in a way that conflicts with implemented migration state.
2. Add a short note or checked item reflecting ADR-035 implementation closure if appropriate.
3. Keep edits minimal; this file is broad and should not be rewritten end-to-end.

### 3.6 Decisions log

**Path:** `docs/10-governance/decisions-log.md`

**Required changes:**
1. Add a new entry `005` dated `2026-06-07`.
2. Decision: ADR-035 implementation closure with accepted DR caveat.
3. Category: Governance / Architecture.
4. ADR column points to ADR-035.
5. Rationale mentions:
   - Hybrid Hermes Migration implemented.
   - B10 accepted operational DR risk pending age-key recovery.
   - B11/B12 resolved through operational/documentation updates.

---

## 4. Evidence to Create/Update

### Required evidence files

| Path | Purpose |
|---|---|
| `docs/setup-evidence/hermes-migration/final-closure/adr-035-closure-plan.md` | This planner/scaffold file |
| `docs/setup-evidence/hermes-migration/final-closure/adr-035-closure-verification.md` | Parent verification of doc updates and status truth |
| `docs/setup-evidence/hermes-migration/final-closure/adr-035-closure-summary.md` | Human-readable closure summary and caveats |

Optional if useful:
- `docs/setup-evidence/hermes-migration/final-closure/git-tag-verification.md`

---

## 5. Verification Scaffold

### 5.1 Expected files modified

- `docs/20-security/hermes-phase-7-blocker-register.md`
- `adr/ADR-035-hermes-migration.md`
- `PROGRESS.md`
- `docs/IMPLEMENTATION_GUIDE.md`
- `CHECKLIST.md`
- `docs/10-governance/decisions-log.md`
- `docs/setup-evidence/hermes-migration/final-closure/adr-035-closure-verification.md`
- `docs/setup-evidence/hermes-migration/final-closure/adr-035-closure-summary.md`

### 5.2 Forbidden patterns

Must return zero matches in modified docs (except where clearly negated/quoted in evidence):
- `All 12 blockers must be resolved before ADR-035 can transition to IMPLEMENTED status`
- `ADR-035 IMPLEMENTED | All \(B1-B12\)`
- false claims that `/var/log/guinevere/last-backup-success` exists
- false claims that `hermes_gateway_up` is exported
- false claims that encrypted S3/R2 restore is currently tested/ready
- any secret values / tokens / passwords / keys

### 5.3 Required commands

Run after edits:
1. `grep` for stale blocker statements in `docs/20-security/hermes-phase-7-blocker-register.md` → zero stale matches.
2. `grep` for `status: "Implemented"` and `## Status` body in `adr/ADR-035-hermes-migration.md` → present.
3. `lsp_diagnostics` on touched markdown files where supported → no errors.
4. Optional markdown lint if available; if unavailable, document tooling gap.
5. `git status` before commit to confirm intended file set only.
6. Before tag: `git status`, `git log -1 --oneline`, and post-tag verification.

### 5.4 Hard rejection criteria

Fail/stop if any are true:
- Oracle verdict contradicted or ignored.
- Docs claim restore readiness without age-key recovery.
- Docs claim `hermes_gateway_up` exists.
- Docs leave blanket blocker rule while also flipping ADR-035 to IMPLEMENTED.
- Tag/commit attempted before documentation is internally consistent.

---

## 6. Commit and Tag Strategy

### Commit

One focused docs/governance commit is acceptable here because all modified files are one atomic closure unit:
- blocker register
- ADR-035
- progress/checklist/implementation guide
- decisions log
- final closure evidence

Suggested commit message (subject only; final wording can follow repo semantic style):
- `docs: mark ADR-035 implemented with accepted DR caveat`

### Tag

Oracle suggested tag forms like `adr-035-implemented` or a milestone tag. Use the user-requested release-style finalization only if it does not conflict with repo conventions. Since no explicit tag name is yet specified in this turn, choose a conservative architecture milestone tag if user does not override during execution, e.g.:
- `adr-035-implemented`

If repo already uses `v*` release tags for broader releases, note that this is an architecture milestone, not necessarily a product release.

---

## 7. Caveats to Preserve

- B10 remains an **accepted operational DR risk**, not silently erased.
- B11 is resolved by path correction, not by claiming the old sentinel path exists.
- B12 is resolved by actual exported metrics **except** `hermes_gateway_up`, which remains intentionally blocked.
- ADR-035 implementation status does not mean every future hardening task is done; it means the architecture decision is live and residual risks are documented.

---

## 8. Execution Order

1. Update blocker register.
2. Update ADR-035 frontmatter/status + implementation note.
3. Update PROGRESS.md top-level status.
4. Update `docs/IMPLEMENTATION_GUIDE.md` and `CHECKLIST.md` minimally.
5. Add decisions-log entry #005.
6. Write final closure evidence files.
7. Validate greps/diagnostics.
8. If clean, commit.
9. If commit succeeds, create tag.
10. Report final status and caveats.

---

## 9. Final Closure Question

This plan assumes Oracle’s verdict stands: **IMPLEMENTED with accepted-risk note**. If any validation contradicts that (for example, another still-active blocker statement elsewhere materially conflicts), stop and resolve the documentation inconsistency before committing/tagging.
