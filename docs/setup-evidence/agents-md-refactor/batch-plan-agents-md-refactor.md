# AGENTS.md v2.1 Refactor Batch Plan

| Field | Value |
|---|---|
| Scope | `AGENTS.md` v2.1 simplification/refactor |
| Date | 2026-06-01 |
| Planner | Hephaestus / Guinevere parent |
| Research inputs | `research-reports/agents-md-refactor/concise-structure-blueprint.md`; `rule-preservation-core.md`; `rule-preservation-appendix.md`; `evidence-audit-style.md`; `docs/workflow/opencode-master-template-v3.md` |
| Evidence root | `docs/setup-evidence/agents-md-refactor/` |
| Auditor path | `audit-reports/agents-md-refactor/agents-md-v2.1-auditor-report.md` |

## 1. Master Todo List

1. Rewrite `AGENTS.md` as v2.1, targeting ~350-400 lines while preserving required rules.
2. Preserve §13 Footer and §14 Tooling Notes; §14 may receive only minimal wording de-duplication, not removal of practical rules.
3. Add v2.1 rules: parent verify delegates via verifier sub-agent, one sub-agent per implementation step, planner determines parallelism/dependency map.
4. Create `docs/setup-evidence/agents-md-refactor/verification.md` using the 12-section schema.
5. Run grep/LSP/markdown validation and record results in evidence.
6. Delegate structured verification to an independent verifier sub-agent before auditor gate.
7. Run auditor gate at `audit-reports/agents-md-refactor/agents-md-v2.1-auditor-report.md`; fix findings and re-audit if needed.

## 2. Dependency Map

| Step | Depends On | Parallelism |
|---|---|---|
| AGENTS rewrite | Research reports read + this plan | Sequential; parent-only shared writer |
| Evidence creation | AGENTS rewrite + initial validation | Sequential |
| Structured verifier | Evidence draft + validation commands | Sequential after evidence |
| Auditor gate | Parent verification + verifier result | Sequential after verifier |

Planner decision: this is a single implementation step because only `AGENTS.md` is the material source writer. One sub-agent must not be assigned more than one implementation step; sub-agents here are used for verification/audit, not source edits.

## 3. Collision Scan

| File | Writer | Decision |
|---|---|---|
| `AGENTS.md` | Parent only | Shared operating contract; no implementation sub-agent edits |
| `docs/setup-evidence/agents-md-refactor/verification.md` | Parent only | Evidence generated after validation |
| `audit-reports/agents-md-refactor/agents-md-v2.1-auditor-report.md` | Auditor sub-agent | Report-only output |
| `research-reports/agents-md-refactor/*` | Completed explore agents | Read-only inputs now |

No parallel implementation wave is allowed for `AGENTS.md` because it is one shared writer.

## 4. Files to Modify/Create

| Path | Action |
|---|---|
| `AGENTS.md` | Replace with concise v2.1 contract |
| `docs/setup-evidence/agents-md-refactor/verification.md` | Create evidence after validation |
| `docs/setup-evidence/agents-md-refactor/batch-plan-agents-md-refactor.md` | This planner file |
| `audit-reports/agents-md-refactor/agents-md-v2.1-auditor-report.md` | Created by auditor gate |

## 5. Implementation Design

- Keep project metadata and authority boundary.
- Condense §0 persona while preserving strong identity, bypass mode, eject modes, and full BLOCKING list with the two new items.
- Make §2 the authoritative workflow gate section: AGENTS-first, research wave, planner gate, planner-determined dependency map/parallelism, collision scan, implementation one-step-one-sub-agent, parent verifier delegation, file-based output, auditor orchestrator.
- Keep §3, §4, §5, §6 concise but complete.
- Preserve §7 table, §8 tables, §9 isolation, §10 template, §11 schema, §12 tool hierarchy, §13 footer with v2.1 row, and §14 Tooling Notes.

## 6. Verification Commands

Required exact grep checks from Faiz:

- `grep "HARD STOP" AGENTS.md`
- `grep "one sub-agent" AGENTS.md`
- `grep "planner" AGENTS.md`
- `grep "research wave" AGENTS.md`
- `grep "inline" AGENTS.md`
- `grep "Y4\|Y5\|Y6" AGENTS.md`
- `grep "SOPS" AGENTS.md`
- `grep "auditor" AGENTS.md`
- `grep "parallelism\|parallel" AGENTS.md`

Additional validation:

- `lsp_diagnostics` on `AGENTS.md` and generated evidence/audit markdown files.
- Markdown lint if repo scripts are available; otherwise document unavailability.
- Token/secret shape scan on changed markdown.

## 7. Auditor Matrix

| Gate | Output | Focus |
|---|---|---|
| Structured verifier | file-based verification report or task summary plus evidence update | Rule preservation, exact grep list, line target, footer version, no secret exposure |
| Independent auditor | `audit-reports/agents-md-refactor/agents-md-v2.1-auditor-report.md` | Acceptance criteria, evidence inventory, boundary compliance, stale references, markdown structure |

## 8. Rollback Plan

`AGENTS.md` is a documentation rewrite. Rollback is restoring the prior file content from editor/tool history or VCS if available. Evidence/audit files are additive and can be deleted only with explicit operator approval if rollback is requested.

## 9. Caveats

- Blueprint suggested removing §14 workflow-gate duplicates, but Faiz explicitly required preserving §14 Tooling Notes. This plan follows Faiz: preserve §14 practical section, allowing only minimal wording compression.
- `AGENTS.md` target is ~350-400 lines. If preserving §14 fully makes the target impossible without rule loss, rule preservation wins over exact line count.

## 10. Footer

| Field | Value |
|---|---|
| Source task | AGENTS.md v2.1 refactor planner gate |
| Date | 2026-06-01 |
| Implementer | Hephaestus / Guinevere parent |
| Validation method | Parent synthesis of file-based research reports |
