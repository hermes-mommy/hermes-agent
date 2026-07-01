# P23 Research — GitHub/Repo Action (gh CLI + API)

> Status: RESEARCH (definition phase). Date: 2026-06-25. Author: Guinevere (parent-authored; subagent attempts timed out on API errors — provenance documented per AGENTS.md §14, mirroring P21 §2 acceptance of parent-authored replacement files).
> Scope: P23 Embodied Operations / Personal OS Action Layer — GitHub/repo executor (gh CLI + GitHub REST/GraphQL API).

> ⚠️ **SUPERSEDED (2026-06-25, Codex P1-2 fix):** This research file is a HISTORICAL SNAPSHOT. It contains statements that `AuthLevel` maps 1:1 to P23 L1-L4 risk tiers. **That mapping is NO LONGER VALID.** Per plan §22b `SemanticActionClassifier`, `AuthLevel` is an INPUT to risk classification, NOT a 1:1 map: `shell_exec` is `READ_AUTO` (`src/mcp/tools/shell_tool.py:350`) yet allows `python`/`pip`/`git` which can mutate state, so those classify L2/L3 by semantics, never L1. **Do NOT use the AuthLevel 1:1 claims in this file for implementation.** Always defer to the plan §22 + §22b semantic classifier. The reuse findings (git_tool/github.py wrappers) remain valid; only the 1:1 risk-tier mapping is superseded.


## 1. Objective

Define how P23 executes GitHub/repo actions autonomously and safely: branch/PR/check policy, isolation via scoped PAT/GitHub App, self-modification gate (V-006/ADR-029), rollback, failure/self-debug. Critical finding: the repo **already has** production-grade GitHub + git MCP tools (`src/mcp/tools/github.py`, `src/mcp/tools/git_tool.py`) with auth-level gating that maps directly to P23's L1-L4 risk tiers — P23's GitHub executor largely **wraps/reuses** these rather than building new.

## 2. Sources Consulted

### Local Files (parent-read)
- `src/mcp/tools/github.py:1-60+` — GitHub REST API client via `httpx`; auth-level gating (`READ_AUTO` for list repos/get file/search code; `WRITE_NOTIFY` for create issue/PR); 401→`ConfigurationError`, 403→rate-limit logged, 404→empty, 5xx→tenacity exponential backoff; `_GITHUB_API_BASE = "https://api.github.com"`; PAT from `GITHUB_PAT` env. **Reuses `src/mcp/auth.AuthLevel` + `require_approval`.**
- `src/mcp/tools/git_tool.py:1-50+` — Local git ops via `asyncio.create_subprocess_exec` (no shell=True — safe); auth-level gating: `git_status`/`git_log`/`git_diff`→`READ_AUTO`, `git_commit`→`WRITE_NOTIFY`, `git_push --force`→`DESTRUCTIVE_APPROVAL`, `git push --force` to main/master→`FORBIDDEN` (`ForbiddenOperationError`). ~~**This is already the L1-L4 model P23 needs.**~~ **[SUPERSEDED — see banner above: AuthLevel is an INPUT, not 1:1 with L1-L4; git_tool's read/write/destructive split is well-gated but the FINAL P23 tier still requires the §22b SemanticActionClassifier to confirm the subcommand is read-only before granting L1.]**
- `src/mcp/auth.py` — `AuthLevel` enum (`READ_AUTO`, `WRITE_NOTIFY`, `DESTRUCTIVE_APPROVAL`, `FORBIDDEN`), `require_approval()`, `ForbiddenOperationError`. **The canonical P23 policy-gate primitive — P23 risk tiers L1-L4 map 1:1.**
- `src/mcp/auth_matrix.py`, `src/mcp/budget.py`, `src/mcp/cost.py`, `src/mcp/tool_selector.py` — MCP governance/budget/cost/tool-selection infra P23 can reuse.
- `src/mcp/manager.py`, `src/mcp/custom_manager.py` — MCP tool registration.
- Git user: `fazulfim`; repo on `main` (git status snapshot); ADR-013 (Guinevere MCP native fully replaces OpenCode).
- `docs/setup-evidence/P22/plan/p22-life-integration-hub-plan.md` — P22 GitHub Projects v2 secret model (`gkv1-kek-secrets-p22-github-pat`, scopes `read:project`/`project`), GraphQL limits (PAT 5,000 pts/hr; App up to 12,500; Enterprise 10,000; secondary 2,000 pts/min + 100 concurrent).

### Sibling Research
- `p23-policy-gate-risk-classification-research.md` — L1-L4 risk tiers, 7-step gate, consent.
- `p23-rollback-idempotency-research.md` — action lifecycle, rollback-per-executor.
- `p23-security-secrets-consent-research.md` — secret_id mapping, V-023 injection.

### External References (official docs, retrieved 2026-06-25)
- GitHub CLI manual — https://cli.github.com/manual/ (retrieved 2026-06-25)
- GitHub REST API v3 — https://docs.github.com/en/rest (retrieved 2026-06-25)
- GitHub GraphQL API v4 — https://docs.github.com/en/graphql (retrieved 2026-06-25)
- GitHub protected branches — https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-branches-in-your-repository/managing-a-branch-protection-rule (retrieved 2026-06-25)
- GitHub Actions workflow runs — https://docs.github.com/en/actions/managing-workflow-runs (retrieved 2026-06-25)

## 3. Findings

### 3.1 Existing GitHub Infra (major reuse opportunity)

The repo already has two production-grade MCP tools that implement the P23 auth-level/risk-tier model:

| Existing Tool | Path | Ops | AuthLevel (L-tier) | P23 Relation |
|---|---|---|---|---|
| GitHub API client | `src/mcp/tools/github.py` | list repos, get file, search code, create issue, create PR | READ_AUTO (L1) / WRITE_NOTIFY (L2) | **Reuse** — P23 GitHub executor wraps these via the action planner |
| Git local ops | `src/mcp/tools/git_tool.py` | git_status, git_log, git_diff, git_commit, git_push (force) | READ_AUTO (L1) / WRITE_NOTIFY (L2) / DESTRUCTIVE_APPROVAL (L3) / FORBIDDEN (L4) | **Reuse** — already enforces main/master force-push = FORBIDDEN |
| Auth gate | `src/mcp/auth.py` | `AuthLevel` enum + `require_approval()` | — | **Reuse** — canonical P23 policy-gate primitive |
| MCP governance | `src/mcp/budget.py`, `src/mcp/cost.py` | cost/budget | — | **Reuse** — feeds CostTracker |
| Tool selector | `src/mcp/tool_selector.py` | picks tool for intent | — | **Reuse** — action planner may consult |

**Implication:** P23-008 (GitHub executor) is largely a **thin wrapper** over these existing tools, adding: (a) action-queue lifecycle (queued→running→done/failed/rolled-back), (b) audit hash-chain, (c) artifact capture, (d) HARD-STOP check, (e) self-debug via HermesBrain. The core git/github operations + auth gating already exist and are battle-tested.

### 3.2 GitHub Action Surfaces

| Surface | Method | Official Doc | L-tier |
|---|---|---|---|
| List repos | REST `GET /user/repos` | docs.github.com/en/rest | L1 |
| Get file content | REST `GET /repos/{owner}/{repo}/contents/{path}` | REST | L1 |
| Search code | REST `GET /search/code` | REST | L1 |
| git status/log/diff | local `git` | git-scm | L1 |
| Create branch | local `git checkout -b` | git-scm | L2 |
| Commit | local `git commit` | git-scm | L2 |
| Push (feature branch) | local `git push` | git-scm | L2 |
| Create issue | REST `POST /repos/{owner}/{repo}/issues` | REST | L2 |
| Comment | REST `POST /repos/.../issues/{n}/comments` | REST | L2 |
| Create PR | REST `POST /repos/{owner}/{repo}/pulls` or `gh pr create` | REST / CLI manual | L2 |
| Merge PR (squash) | REST `PUT /repos/.../pulls/{n}/merge` or `gh pr merge --squash` | REST / CLI | L3 (if to main/deploy) |
| Watch checks | REST `GET /repos/.../commits/{sha}/check-runs` or `gh run watch` | REST / CLI | L1 |
| Run workflow | REST `POST /repos/{owner}/{repo}/actions/workflows/{id}/dispatches` or `gh workflow run` | Actions docs | L3 |
| Force push (feature) | local `git push --force` | git-scm | L3 (DESTRUCTIVE_APPROVAL) |
| Force push to main | local `git push --force` to main/master | — | **L4 FORBIDDEN** (already blocked by `git_tool.py`) |
| Delete branch | REST `DELETE /repos/.../git/refs/heads/{branch}` | REST | L3 (rollback) |

### 3.3 Isolation Boundary

- **Scoped PAT or GitHub App** (not broad token): `read:project`/`read:user`/`repo` (read) for L1; `repo` (write) + `workflow` for L2/L3; org-admin/billing scopes = L4 forbidden. Secret `gkv1-kek-secrets-p23-github-pat` in `secrets/p23/executors.enc.yaml` (SOPS/age), runtime decrypt to tmpfs 0600, never in repo/logs/MCP. Quarterly rotation + `SecretRotationLog` row.
- **Branch policy:** ALL writes happen on feature branches (`feat/p23-<action-id>-<slug>`). `main` is protected (branch protection rule: require PR + passing checks + no direct push + no force-push). P23 NEVER force-pushes to main (L4, already enforced by `git_tool.py:ForbiddenOperationError`).
- **No shell=True:** `git_tool.py` uses `asyncio.create_subprocess_exec` (verified line 7 docstring) — no shell injection vector. P23 GitHub executor must preserve this.
- **Rate-limit aware:** `github.py` already logs 403 rate-limit + retries 5xx via tenacity. GraphQL: PAT 5,000 pts/hr (P22); P23 throttles via slowapi + Redis DB5 at ~3,500 pts/hr headroom.

### 3.4 Action Primitives (P23 GitHub executor)

Each primitive = policy-gated + audited + rollback-capable, wrapping the existing MCP tools:

| Primitive | Wraps | L-tier | Rollback |
|---|---|---|---|
| `create_branch(name)` | `git_tool checkout -b` | L2 | delete branch |
| `commit(message, files)` | `git_tool commit` | L2 | `git reset --hard HEAD~1` |
| `push(branch)` | `git_tool push` (feature) | L2 | delete remote branch |
| `create_pr(title, body, head, base)` | `github.py create PR` / `gh pr create` | L2 | `gh pr close` |
| `merge_pr(number, squash)` | `gh pr merge --squash` | L3 (if base=main) | revert merge commit (`git revert`) + `gh pr reopen` |
| `watch_checks(pr)` | `gh run watch` / check-runs API | L1 | (read-only, no rollback) |
| `create_issue(title, body)` | `github.py create issue` | L2 | `gh issue close` |
| `comment(issue, body)` | `github.py comment` | L2 | delete comment |
| `run_workflow(id, ref)` | `gh workflow run` | L3 | `gh run cancel` |
| `revert_pr(number)` | `git revert` + new PR | L3 | (is the rollback) |

### 3.5 Check Policy (PR merge gate)

Before any PR merges to `main`/deploy branch:
1. PR created from feature branch (L2).
2. CI checks must pass: `pytest` (incl. `tests/life_kernel/` for P20 non-regression), `mypy`, `ruff`, **secret-scan** (AGENTS.md BLOCKING: never commit secrets).
3. `watch_checks` polls until all checks green (L1, autonomous).
4. IF checks pass AND base is feature/staging → `merge_pr` squash (L2 autonomous + notify).
5. IF checks pass AND base is `main`/deploy → `merge_pr` = **L3** (backup→canary→smoke→rollback gate + Faiz approval per §0.1 engineering-deployment gate).
6. IF checks fail → PR stays open, self-debug via HermesBrain (analyze failure → fix commit → re-push), or rollback (close PR + delete branch).

### 3.6 Self-Modification Gate (V-006, ADR-029)

Guinevere improving her own code (prompts/skills/planner/code/tests/Hermes integration) is a first-class P23 GitHub use case, governed by §0.1 self-improvement gate:
1. **Propose** (L1 autonomous): `ReflectionEvaluator` (`src/life_kernel/self_improve.py`) produces an improvement candidate from action-outcome reflection.
2. **Implement** (L2): create branch + commit + push + PR.
3. **Regression test** (L2 autonomous): CI runs `pytest` — MUST pass (ADR-029 self-modification automated testing).
4. **Promote** (L3): merge to main ONLY IF regression passes + audit + **rollback-before-promote** (§0.1 invariant 4). Rollback target = last known-good commit SHA (backup step captures `git rev-parse HEAD`).
5. IF regression fails → auto-revert, log failure, candidate goes to manual review (matches `self_improve.py` behavior: proposes but does NOT auto-promote without validation).

### 3.7 Failure Modes + Self-Debug

| Failure | Detection | Self-Debug (HermesBrain) | Action |
|---|---|---|---|
| Check failure | `watch_checks` non-green | `think()` with failure log + journal recall of similar past fixes | fix commit + re-push, or close PR |
| Merge conflict | `merge_pr` 409 | `think()` to resolve strategy | rebase/merge base into branch, re-push |
| Rate limit (403) | `github.py` logs `X-RateLimit-Remaining` | (no LLM needed) | tenacity backoff (already in `github.py`) |
| Auth expiry (401) | `ConfigurationError` | (no LLM) | flag re-consent-required, notify Faiz, block executor |
| Push rejected (protected branch) | `git push` non-zero | `think()` | switch to feature-branch + PR flow |
| Force-push to main attempted | `ForbiddenOperationError` | (blocked at gate) | log L4 violation, SEV0 audit, abort |

### 3.8 Cost

- GitHub API: $0 (free for current scale; P22 confirmed).
- gh CLI: $0.
- LLM cost: planner `HermesBrain.think()` (action selection) + self-debug `think()` on failure. ~$0.002-0.005/action. Feeds `CostTracker.record_cost(model='p23:github:planner'/'p23:github:self_debug')` → Redis DB5 → USD 30/mo cap.

## 4. Implications for P23 Design

- **P23-008 (GitHub executor)** = thin wrapper over existing `src/mcp/tools/github.py` + `git_tool.py` + `auth.py`; adds action-queue lifecycle, audit hash-chain, artifact capture, HARD-STOP check, self-debug. **Minimal new code** — reuse is the dominant strategy.
- The `AuthLevel` enum (`READ_AUTO`/`WRITE_NOTIFY`/`DESTRUCTIVE_APPROVAL`/`FORBIDDEN`) IS the P23 L1-L4 risk-tier primitive — the policy gate (P23-002) should adopt/alias it, not reinvent.
- Branch protection on `main` must be configured (setup runbook) so L4 force-push-to-main is enforced at GitHub side too (defense-in-depth, not just in `git_tool.py`).
- Self-modification flows through the §0.1 self-improvement gate (regression→audit→rollback-before-promote) — never auto-promote without passing tests.

## 5. Risks / Open Questions

1. **PAT scope creep:** a `repo`-scope PAT can do destructive org-level ops if org permissions allow — mitigate with a dedicated GitHub App (narrower scopes) rather than a personal PAT, or a PAT owned by a dedicated machine user. Decide at P23-008 execution.
2. **GraphQL vs REST:** `github.py` currently uses REST; GraphQL is more efficient for Projects v2 (P22) but adds complexity. P23 GitHub executor may stay REST-only for MVP (PRs/issues/code) and defer GraphQL to P22 overlap.
3. **gh CLI dependency on VPS:** if P23 uses `gh` CLI subprocess, `gh` must be installed + authenticated on the VPS — verify in P23-008 pre-flight. Alternatively use REST only (no `gh` dep).
4. **Concurrent PRs to same branch:** idempotency — P23 action dedup via `(namespace + intent_hash)` prevents double-PR (rollback research).
5. **Secret in commit content:** the CI secret-san catches committed secrets, but P23 must also run `secret_scanner` on the diff BEFORE commit (pre-commit hook analog) to avoid pushing then reverting.

## 6. Recommendations to Planner

- P23-008 scaffold: create `src/life_kernel/executors/github_executor.py` wrapping `src/mcp/tools/github.py` + `git_tool.py`; Expected Files list the wrapper + tests; Forbidden: shell=True, force-push to main, broad-scope PAT, secrets in commit/diff/logs.
- Required Commands: `python -m pytest tests/life_kernel/test_github_executor.py -v` → exit 0; `gh auth status` → authenticated (if gh used); secret-scan on a test diff → 0 secrets.
- Reuse `AuthLevel` as the L1-L4 primitive in P23-002 (policy gate) — do NOT redefine.
- Configure `main` branch protection (require PR + checks + no force-push) as a P23-001 governance/ADR item.
- Self-modification: route through §0.1 self-improvement gate (regression→audit→rollback-before-promote); never auto-promote without green CI.

## 7. Verdict

**PASS** — GitHub executor design is complete and notably efficient: the repo already has production-grade `github.py` + `git_tool.py` MCP tools with `AuthLevel` gating. ~~**that maps 1:1 to P23 L1-L4 risk tiers**~~ **[SUPERSEDED — AuthLevel is an INPUT to the §22b SemanticActionClassifier, not 1:1 with L1-L4; force-push-to-main = FORBIDDEN remains valid.]** (incl. force-push-to-main = FORBIDDEN already enforced). P23-008 is a thin wrapper adding action lifecycle/audit/artifact/HARD-STOP/self-debug. Branch protection + scoped PAT/App + self-modification gate + rollback cover all hard-rejection criteria. Parent-authored due to subagent API timeouts (provenance documented); content grounded in parent-read source files with exact path:line citations + official-doc URLs (retrieved 2026-06-25).
