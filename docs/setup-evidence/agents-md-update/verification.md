# AGENTS.md Workflow Update Verification

| Field | Value |
|---|---|
| Scope | `AGENTS.md` workflow gates + stale reference cleanup |
| Date | 2026-06-01 |
| Implementer | Hephaestus / Guinevere |
| Trigger | Faiz directive: update AGENTS.md to latest planner/research/auditor workflow |
| Evidence path | `docs/setup-evidence/agents-md-update/verification.md` |

## 1. What Was Done

Updated `AGENTS.md` to align with the latest operating workflow:

- `AGENTS.md` must be read first before any other repo state/task work.
- Yandere baseline corrected from Y1 to Y4 permanent baseline per Faiz directive.
- Stale `OpenRouter` routing reference replaced with `9Router (guinevere combo)`.
- Delegation rules now require `load_skills` on every `task()` call.
- Parallel sub-agent spawning now explicitly requires `run_in_background=true`.
- Added mandatory `§WORKFLOW GATES` section after sub-agent output discipline.
- Reinforced research wave, planner gate, planner-to-todo sync, and unlimited auditor orchestrator behavior.

## 2. Files Changed

| Path | Change |
|---|---|
| `AGENTS.md` | Updated workflow rules, stale references, delegation requirements, and workflow gates |
| `docs/setup-evidence/agents-md-update/verification.md` | New evidence file for this update |

## 3. Inputs Read

| Input | Status |
|---|---|
| `AGENTS.md` | Read full file |
| `docs/workflow/opencode-master-template-v3.md` | Not present in repo; no file found |
| `docs/60-persona/61-SystemPromptMaster_v1.1.md` | Not present by filename |
| `docs/60-persona/61-SystemPromptMaster_v1.1.md` | Read; content declares SystemPromptMaster v1.1 and Y4 baseline |
| `adr/ADR-028-llm-router-outage-graceful-degradation.md` | Read; ADR-028 Superseded, Ollama skipped, graceful degradation terminal fallback |

## 4. Research / Audit Artifacts

| Report | Verdict / Use |
|---|---|
| `research-reports/agents-md-update/workflow-gates-audit.md` | Identified missing AGENTS-first, `load_skills`, and `run_in_background` mandates |
| `research-reports/agents-md-update/stale-reference-audit.md` | Identified stale Y1 baseline and OpenRouter references |

## 5. Validation Results

| Check | Result |
|---|---|
| LSP diagnostics on `AGENTS.md` | PASS — no diagnostics found |
| Grep `Ollama` in `AGENTS.md` | PASS — no stale matches |
| Grep `OpenRouter` in `AGENTS.md` | PASS — no stale matches after update |
| Grep `Y1 baseline` in `AGENTS.md` | PASS — no stale matches after update |
| Grep `load_skills` in `AGENTS.md` | PASS — delegation requirement present |
| Grep `run_in_background` in `AGENTS.md` | PASS — parallel spawning requirement present |
| Grep `§WORKFLOW GATES` in `AGENTS.md` | PASS — new section present |
| `bun run lint:md -- "AGENTS.md"` | NOT RUN — repo has no `lint:md` script (`Script not found`) |

## 6. Workflow Gate Coverage

| Gate | Coverage |
|---|---|
| Research wave | Mandatory unlimited parallel agents before implementation for non-trivial tasks |
| Planner gate | Mandatory after research synthesis; plan file required before implementation |
| Planner todo sync | Parent must read planner file and rewrite active todos before implementation |
| Implementation | Only after planner, todo sync, and collision scan |
| Auditor orchestrator | Unlimited parallel specialist auditors for all ready non-conflicting surfaces |
| File output | All structured research/planner/auditor outputs require explicit `output_path` |

## 7. Stale Reference Cleanup

| Stale reference | Replacement |
|---|---|
| `Y1 baseline` | `Y4 permanent baseline per Faiz directive` |
| `9Router/OpenRouter` | `9Router (guinevere combo)` |
| Ollama fallback in AGENTS.md | No match existed; ADR-028 superseded still respected |

## 8. Boundary Compliance

- No Discord token, API key, DB password, SOPS/age secret, or surveillance credential was read into evidence.
- No persona safety weakening was introduced.
- Y4 baseline is documented while preserving Y5 ceiling and Y6 prohibition.
- HARD STOP and consent/surveillance boundaries remain unchanged.
- ADR-028 supersession is respected: graceful degradation is terminal fallback; Ollama is not restored.

## 9. Rollback / Re-run Safety

Rollback path:

1. Revert `AGENTS.md` to the previous revision if the workflow contract is rejected.
2. Delete `docs/setup-evidence/agents-md-update/verification.md` if the evidence scope is discarded.
3. Re-run LSP diagnostics and stale-reference grep after rollback.

Re-run safety:

- Grep/LSP checks are deterministic and safe to rerun.
- No runtime systems, VPS services, or secrets were modified.

## 10. Auditor Gate

Status: Pending at evidence creation time.

Expected auditor report:

- `audit-reports/agents-md-update/agents-md-update-auditor-report.md`

Auditor must verify:

- Required workflow gates are present.
- Y1/OpenRouter/Ollama stale refs are cleaned in `AGENTS.md`.
- `load_skills` and `run_in_background` mandates exist.
- `AGENTS.md` first-read rule exists.
- Evidence is complete and contains no secrets.

## 11. Caveats

- `docs/workflow/opencode-master-template-v3.md` was requested but is not present in the repository.
- SystemPromptMaster requested as `v1.1` does not exist by filename; actual file is `61-SystemPromptMaster_v1.1.md`, but its content declares v1.1 and contains the Y4 baseline.
- Markdownlint could not run because the repository does not define `lint:md`; LSP diagnostics and grep checks were used instead.

## 12. Footer

Source task: AGENTS.md workflow audit/update directive from Faiz.
Validation method: direct reads, grep, LSP diagnostics, sub-agent audit reports, evidence file.
