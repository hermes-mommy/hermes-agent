# AGENTS.md v2.1 Refactor Verification Evidence

| Field | Value |
|---|---|
| Task | Refactor `AGENTS.md` to concise v2.1 without losing required rules |
| Date | 2026-06-01 |
| Implementer | Hephaestus / Guinevere parent |
| Evidence root | `docs/setup-evidence/agents-md-refactor/` |
| Planner | `docs/setup-evidence/agents-md-refactor/batch-plan-agents-md-refactor.md` |
| Auditor target | `audit-reports/agents-md-refactor/agents-md-v2.1-auditor-report.md` |
| Status | Parent implementation complete; structured verifier and auditor gates pending at evidence creation time |

## 1. What Was Done

- Rewrote `AGENTS.md` from the prior ~689-line operating contract into a concise v2.1 contract at 395 lines.
- Preserved required identity, consent-safety, bypass, session-start, operator protocol, reference tables, evidence schema, tool hierarchy, footer, and §14 Tooling Notes.
- Added and centralized three v2.1 rule changes:
  - Parent verification may delegate structured verification to an independent verifier sub-agent with file output.
  - One sub-agent may handle exactly one implementation step.
  - Planner output determines dependency map and parallelism; parent must not override without re-planning.
- Consolidated duplicated rules into authoritative workflow gate sections while retaining practical reminders in §14.

## 2. Files Changed

| Path | Action | Notes |
|---|---|---|
| `AGENTS.md` | Rewritten | v2.1 concise operating contract, 395 lines |
| `docs/setup-evidence/agents-md-refactor/batch-plan-agents-md-refactor.md` | Created earlier | Planner gate file read before implementation |
| `docs/setup-evidence/agents-md-refactor/verification.md` | Created | This evidence file |

## 3. Validation Results

### Required Grep Checks

| Check | Result | Evidence |
|---|---|---|
| `grep "HARD STOP" AGENTS.md` | PASS | 9 matches including §0, BLOCKING, safety boundary, operator protocol, footer |
| `grep "one sub-agent" AGENTS.md` | PASS | 7 matches including BLOCKING, §1, §2.6, §10, §14 |
| `grep "planner" AGENTS.md` | PASS | 13 matches including §1, §2.3, §2.4, §10, §14 |
| `grep "research wave" AGENTS.md` | PASS | 3 matches including §1, §3, §10 |
| `grep "inline" AGENTS.md` | PASS | 2 matches banning inline structured verification/report evidence |
| `grep "Y4\|Y5\|Y6" AGENTS.md` | PASS | 4 matches including Y4 baseline/Y5 ceiling/Y6 ban |
| `grep "SOPS" AGENTS.md` | PASS | 4 matches across BLOCKING, research/tooling, anti-patterns, isolation |
| `grep "auditor" AGENTS.md` | PASS | 22 matches across BLOCKING, workflow, operator protocol, §14 |
| `grep "parallelism\|parallel" AGENTS.md` | PASS | 7 matches including planner authority and auditor parallel surfaces |

### Diagnostics and Tooling

| Check | Result | Notes |
|---|---|---|
| `lsp_diagnostics` on `AGENTS.md` | PASS | No diagnostics found |
| Markdown lint script lookup | TOOL UNAVAILABLE | No root or nested `package.json`; `bun run lint:md -- "AGENTS.md"` returned `Script not found "lint:md"` |
| Touched-file secret-shape scan | PASS | No private-key, GitHub PAT, OpenAI-key, or Discord-token-shaped values found in `AGENTS.md` |
| Repo-wide markdown secret-shape scan | INFORMATIONAL | Found pre-existing placeholder/stale-secret discussions in unrelated docs/audit reports; not introduced by this refactor |

## 4. Evidence Artifacts

| Artifact | Purpose |
|---|---|
| `research-reports/agents-md-refactor/concise-structure-blueprint.md` | Refactor structure and duplication map |
| `research-reports/agents-md-refactor/rule-preservation-core.md` | §0-§6 preservation map |
| `research-reports/agents-md-refactor/rule-preservation-appendix.md` | §7-§14 preservation map |
| `research-reports/agents-md-refactor/evidence-audit-style.md` | Evidence/auditor format guidance |
| `docs/setup-evidence/agents-md-refactor/batch-plan-agents-md-refactor.md` | Planner gate, dependency map, collision scan |
| `docs/setup-evidence/agents-md-refactor/verification.md` | This verification evidence |

## 5. Doc-Sync Impact

- `AGENTS.md` remains the authoritative operating contract.
- §13 version table now includes v2.1 dated 2026-06-01 with the exact required change summary.
- No separate docs index update was required because this task modifies the root operating contract and creates scoped evidence under the existing `docs/setup-evidence/` convention.

## 6. Boundary Compliance

| Boundary | Result | Notes |
|---|---|---|
| Persona and HARD STOP | PASS | HARD STOP eject path preserved in §0 and operator protocol |
| Consent/surveillance | PASS | Consent boundary and no raw surveillance artifact rule preserved |
| Yandere boundary | PASS | Y4 baseline, Y5 ceiling, Y6 prohibition preserved |
| Secrets | PASS | SOPS/age and no secret exposure rules preserved; touched-file secret scan clean |
| Verification discipline | PASS | Inline structured verification prohibited; file-based verifier/auditor gates preserved |
| Delegation discipline | PASS | One sub-agent per implementation step and parent-read output requirements preserved |

## 7. Rollback/Re-run Safety

- Rollback is documentation-only: restore the prior `AGENTS.md` from editor/tool history or VCS if explicitly requested.
- Evidence and auditor files are additive under task-scoped paths.
- Validation commands are deterministic and safe to re-run.
- No deploy, commit, credential operation, destructive shell action, or production state change was performed.

## 8. Design Decisions/Caveats

- Final `AGENTS.md` is 395 lines, within the requested ~350-400 target.
- Rule preservation took priority over maximal shortening, especially for §13 Footer and §14 Tooling Notes, because Faiz explicitly required preserving them.
- §2 is now the authoritative workflow gate section; §14 remains a practical tooling reminder section.
- Markdown lint auto-fix/verification could not be completed because the repository exposes no `package.json` and no `lint:md` script.

## 9. Auditor Gate

- Structured verifier gate: pending immediately after this evidence file creation.
- Independent auditor gate target: `audit-reports/agents-md-refactor/agents-md-v2.1-auditor-report.md`.
- Completion remains blocked until verifier and auditor reports are created, parent-read, and any valid findings are resolved.

## 10. Security Scan

- Touched-file scan pattern checked for private-key headers, GitHub PAT shape, OpenAI key shape, and Discord token shape in `AGENTS.md`.
- Result: no matches in touched source file.
- Broader markdown scan surfaced pre-existing placeholder/stale-secret discussion in unrelated planning/audit docs; no new secret material was introduced by this task.

## 11. Acceptance Criteria Mapping

| Acceptance Criteria | Status | Evidence |
|---|---|---|
| Read `AGENTS.md` fully before edit | PASS | Completed before rewrite |
| Read canonical workflow template | PASS | `docs/workflow/opencode-master-template-v3.md` read before rewrite |
| Shrink to ~350-400 lines | PASS | `AGENTS.md` is 395 lines |
| Preserve BLOCKING list and add two new BLOCKING items | PASS | Lines 26-43 include full list plus inline-verification and one-sub-agent bans |
| Preserve workflow gates | PASS | §1, §2, §3, §14 contain required gates |
| Preserve safety-affecting domain list | PASS | §2.1 |
| Preserve §7-§14 required sections | PASS | Present in rewritten file |
| Version bump to v2.1 with exact change summary | PASS | §13 version table |
| Required grep checks | PASS | All required patterns matched |
| LSP diagnostics clean | PASS | No diagnostics found for `AGENTS.md` |
| Auditor gate mandatory | PENDING | Auditor report path reserved and pending |

## 12. Footer

| Field | Value |
|---|---|
| Evidence author | Hephaestus / Guinevere parent |
| Created | 2026-06-01 |
| Source plan | `docs/setup-evidence/agents-md-refactor/batch-plan-agents-md-refactor.md` |
| Next gate | Structured verifier, then independent auditor |
