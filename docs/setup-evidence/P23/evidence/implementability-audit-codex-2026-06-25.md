# P23 Implementability Audit - Codex Parent Audit - 2026-06-25

## Verdict

**P23 is implementable in staged waves, but the current P23 definition is not yet clean enough to treat as "100% implementation-ready".**

The architecture is real enough to build: P20 life-kernel exists, `HermesBrain.think()` exists, sensor-adapter patterns exist, MCP tools exist, `AuthLevel` exists, Alembic has a single P20 head, and the baseline test suites are healthy. The blockers are not "this is just a plan"; the blockers are two concrete correctness gaps that must be fixed before implementation starts.

## Findings

### P1 - P23 doc-gate evidence line counts are false from filesystem ground truth

P23 docs and trackers claim `45 files / 9,622 lines`, for example:

- `docs/setup-evidence/P23/README.md:81`
- `docs/setup-evidence/P23/evidence/final-p23-planning-report.md:34`
- `docs/setup-evidence/P23/evidence/final-p23-planning-report.md:111`
- `docs/setup-evidence/P23/evidence/p23-doc-gate-cleanup.md:22`
- `PROGRESS.md:53`
- `CHECKLIST.md:1607`
- `docs/IMPLEMENTATION_GUIDE.md:383`

Direct filesystem recount gives:

```text
FileCount=45
MarkdownCount=45
NonMarkdown=0
LineCount=7226
```

That recount was taken before this Codex audit file was added. This audit file intentionally adds one more markdown artifact under the P23 evidence root, so any final cleanup must recompute the count fresh instead of copying either the old `45 / 9,622` claim or this audit snapshot.

The helper scripts also show count drift history:

- `scripts/p23_doc_gate_cleanup.py:5` still describes an older `40 files / 9,072 / 9,513 -> 44 files / 9,514` cleanup.
- `scripts/p23_doc_gate_recount.py:2` then describes `44/9,514 -> 45/9,611`.
- Current docs claim `45/9,622`, but the measured count is `45/7,226`.

**Why this matters:** the P23 cleanup says counts were independently reconciled, but that claim does not reproduce. This does not invalidate the architecture, but it does invalidate the doc-gate cleanliness claim.

**Required fix before implementation:** create a fresh parent-owned recount evidence file, update P23 README/final report/verification/auditor gate/trackers to the measured count, and add a guard script that computes counts from filesystem instead of string-replacing old totals.

### P1 - AuthLevel cannot be mapped 1:1 to P23 action risk tiers yet

The P23 plan says existing MCP `AuthLevel` maps 1:1 to P23 L1-L4 risk tiers and P23 "aliases rather than reinvents":

- `docs/setup-evidence/P23/README.md:13`
- `docs/setup-evidence/P23/evidence/final-p23-planning-report.md:14`
- `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:7`
- `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:1032`
- `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:1069`

That is unsafe for the shell surface. Ground truth:

- `src/mcp/auth.py:7` defines `READ_AUTO` as no side effects.
- `src/mcp/tools/shell_tool.py:3-4` registers `shell_exec` as `AuthLevel.READ_AUTO`.
- `src/mcp/tools/shell_tool.py:43-45` allows `python`, `pip`, and `git` command bases.
- `src/mcp/tools/shell_tool.py:350-351` decorates `shell_exec` with `AuthLevel.READ_AUTO`.
- `src/mcp/auth_matrix.py:150` maps shell `exec` to `AuthLevel.READ_AUTO`.

Even with metacharacter and destructive-pattern filtering, generic `python`, `pip`, and `git` are not inherently read-only. `python -c`, `pip install`, and some `git` subcommands can mutate local state under a `READ_AUTO` label. P23 cannot safely turn "MCP AuthLevel says READ_AUTO" into "P23 L1 safe autonomous action".

**Required fix before implementation:** add a P23 semantic action classifier above MCP tools. For shell/desktop/VPS actions, classify by parsed intent and subcommand, not only by tool auth level. L1 should permit only proven read-only shell verbs and read-only git subcommands. Mutating Python, pip, git, systemctl, service, filesystem, Docker, Redis, and Postgres operations must be L2/L3/L4 by semantics.

### P2 - Full P23 cannot be completed end-to-end until dependency phases expose runtime contracts

The plan correctly marks P23-012/P23-013/P23-014 as blocked:

- P23-012 is blocked on P19 namespace contract readiness: `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:893-904`
- P23-013 is blocked on P21 implementation: `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:906-917`
- P23-014 is blocked on P22 implementation: `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:919-930`
- P23-020 is blocked on final integration/deploy prerequisites: `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:997-1005`

But some wording is too optimistic:

- `docs/setup-evidence/P23/evidence/final-p23-planning-report.md:102` says P23-012 is gated on P19 namespace contract readiness, not P19 implementation.
- `docs/setup-evidence/P23/research/p23-p19-project-namespace-dependency-map.md:335` says implementation is held until P19 reaches definition pass.

For a real "Personal OS action layer", default namespace is enough for early MVP, not enough for final multi-project isolation. P23 can start new-file waves, but it cannot honestly complete P23-012, P23-014, or P23-020 production proof until P19/P21/P22 runtime contracts exist or those surfaces are explicitly feature-flagged out of the acceptance criteria.

**Required fix before implementation:** split acceptance into `P23A core action runtime` and `P23B full integration`. P23A may run with `default` namespace and disabled voice/external adapters. P23B requires P19 runtime namespace registry, P21 voice event contract, and P22 integration adapters.

## Positive Ground Truth

These checks support that P23 is genuinely buildable, not just fantasy planning:

```text
python -m pytest tests/life_kernel/ -q
420 passed, 7 skipped

python -m pytest tests/mcp/ -q
814 passed, 3 skipped

python -m alembic heads
p20_001_life_kernel_schema (head)
```

Existing implementation anchors found:

- `src/life_kernel/hermes_brain.py:258` has `HermesBrain.think`.
- `src/life_kernel/hermes_brain.py:372` has `HermesBrain.think_with_tools`.
- `src/life_kernel/sensor_adapters/base.py:17` has `BaseSensorAdapter`.
- `src/life_kernel/sensors.py:45` has `SensorRegistry`.
- `src/mcp/auth.py:42-48` has `AuthLevel`.
- `src/mcp/tools/git_tool.py:222-308` has read/write/destructive git gating.
- `src/mcp/tools/filesystem.py` exists and has read/write/delete separation.
- `src/mcp/tools/obscura_cdp.py` exists and exposes browser automation primitives.
- `systemd/` exists and already contains Guinevere service units, so a future `guinevere-actions.service` is feasible.

## Implementation Readiness Split

Ready after the two P1 fixes:

- P23-001 governance/scaffold.
- P23-002 typed action model.
- P23-003 durable queue and migration, with DB role/WORM verification.
- P23-004 executor interface and registry.
- P23-005 through P23-010 executor wrappers, provided P1 semantic risk classification is implemented first.
- P23-016 through P23-019 audit/dashboard/metrics/E2E scaffolding.

Not ready for final production acceptance yet:

- P23-011 life-kernel planner wiring: requires fresh P20 runtime preflight before touching locked files.
- P23-012 namespace integration: requires P19 runtime contract or feature-flagged default-only mode.
- P23-013 voice bridge: requires P21 implementation.
- P23-014 external integrations: requires P22 implementation.
- P23-020 production deploy/soak/final gate: requires all dependency contracts and runtime proof.

## Hard-Rejection Gate Result

Current result: **NEEDS FIX BEFORE IMPLEMENTATION START**.

Reason:

1. P23 doc-gate evidence contains a non-reproducible line-count claim.
2. P23 risk-tier mapping would be unsafe if implemented exactly as written against the current shell MCP tool.
3. P23 final acceptance depends on runtime contracts that are not all present yet.

After the two P1 fixes, P23 can begin staged implementation as `P23A core action runtime`; final `P23B full integration` must wait for P19/P21/P22 runtime contracts or explicitly scoped feature flags.
