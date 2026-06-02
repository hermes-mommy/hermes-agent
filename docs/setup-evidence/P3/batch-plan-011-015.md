# P3 Batch Planner Gate - STEP-P3-011 through STEP-P3-015

## Planner Status

| Field | Value |
|---|---|
| Batch | P3 memory safety implementation, STEP-P3-011..STEP-P3-015 |
| Plan path | `docs/setup-evidence/P3/batch-plan-011-015.md` |
| Planner gate | READY FOR PARENT READ |
| Implementation status | NOT STARTED |
| Safety domain | Memory recall, do-not-recall, safe-mode memory filtering, consolidation |
| Binding sequence | `P3-011 -> P3-012 -> P3-013 -> P3-014 -> P3-015` |
| Parallel implementation | Not allowed; serialized by dependency and shared-writer collisions |
| Evidence root | `docs/setup-evidence/P3/` |

## Research Inputs Incorporated

### Binding repository and governance inputs

- `AGENTS.md`: file-based planner gate, one implementation sub-agent per step, parent verification, auditor gate, no type suppression, no raw private data in artifacts.
- `PROGRESS.md`: P3-001..P3-010 complete; P3-011..P3-015 pending.
- `CHECKLIST.md`: pending P3-011..P3-015 acceptance rows plus phase-level checks.
- `stepprompts/StepPrompts.md` P3-011..P3-015: step DoD and target behavior.
- `docs/IMPLEMENTATION_GUIDE.md`: evidence workflow, shared VPS isolation, never touch Aizanta, canonical Guinevere ports.
- `docs/10-governance/17-ADR_Index_v1.0.md`: ADR-009 accepted, high risk.
- `adr/ADR-009-memory-recall-semantic-search-strategy.md`: layered recall, pgvector/FTS, bounded injection, privacy/safety filters.
- `docs/00-core/04-MemorySchema_v2.0.md`: memory hierarchy, episode/semantic fact schemas, consolidation expectations.
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`: safe-word/safe-mode authority; memory recall cannot override policy.
- `src/core/services/hard_stop_handler.py`: authoritative safe-mode runtime state; `HardStopHandler.is_safe == True` means SAFE.
- `src/memory/read_pipeline.py`: current RRF, DNR filters, safe-mode flag, token budget, recall result schema.
- `src/memory/write_pipeline.py`: store episode pipeline and DNR API insertion point.
- `src/memory/embeddings.py`: actual classification order and embedding policy.
- `src/memory/models.py`: Episodes, SemanticFacts, consent/audit-related models.
- `src/core/services/prompt_loader.py`: current prompt assembly surface.

### Parent-verified research reports

- `docs/setup-evidence/P3/research/local-memory-code-readiness-011-015.md`
- `docs/setup-evidence/P3/research/safety-governance-constraints-011-015.md`
- `docs/setup-evidence/P3/research/prompt-context-injection-readiness-011-015.md`
- `docs/setup-evidence/P3/research/external-hybrid-ranking-rrf-pgvector.md`
- `docs/setup-evidence/P3/research/external-context-injection-token-budget.md`
- `docs/setup-evidence/P3/research/external-dnr-safe-mode-memory-filtering.md`
- `docs/setup-evidence/P3/research/external-consolidation-apscheduler.md`
- `docs/setup-evidence/P3/research/security-safety-risk-011-015.md`

## Known State Before Implementation

- P3-010 is complete and already provides async hybrid recall with `RRF_K = 60`, 90-day recency half-life, DNR exclusion when `exclude_dnr=True`, principal classification ceiling, `safe_mode`, `DEFAULT_TOKEN_BUDGET = 4000`, `_apply_token_budget()`, and `safe_content`.
- `HardStopHandler.is_safe` is the safe-mode integration point.
- `prompt_loader.py` has primitive memory context support but no bounded recall integration.
- `src/memory/consolidation.py` does not exist.
- `tests/memory/` does not exist and should be created by implementation steps as needed.
- No implementation has started for this batch.

## Reconciled Contradictions and Binding Decisions

### Classification order

Use the actual order from `src/memory/embeddings.py`, not inconsistent secondary prose:

`Public(0) < Internal(1) < Restricted(2) < Confidential(3) < Critical(4)`

Implementation agents must verify this from code before editing. Unknown/null classification fails closed as Critical for recall and injection safety.

### Safe mode memory behavior

External research suggested disabling memory entirely in safe mode. Guinevere binding requirements override that. Safe mode must:

- Use `HardStopHandler.is_safe` as runtime source.
- Keep DNR absolute.
- Block Critical.
- Redact/summarize Restricted and Confidential.
- Inject only neutral Public/Internal summaries.
- Block emotional, surveillance, yandere-escalation, or persona-punishment content even if classification is lower.
- Avoid raw content in logs/evidence and avoid punitive violation records.

### Execution order

Local research recommended safety-first reordering, but user explicitly required `P3-011 -> P3-012 -> P3-013 -> P3-014`, with P3-015 after P3-014. Binding execution order is:

1. STEP-P3-011
2. STEP-P3-012
3. STEP-P3-013
4. STEP-P3-014
5. STEP-P3-015

Step N+1 starts only after Step N implementation, parent verification, evidence, tracker sync, and auditor PASS.

### APScheduler version

P3-015 must inspect installed dependency/imports. If APScheduler 3.x is installed or `apscheduler.schedulers.asyncio.AsyncIOScheduler` is available, use the v3 `AsyncIOScheduler` pattern from StepPrompts. If 4.x is actually installed, adapt to `AsyncScheduler`. Do not change dependency versions without explicit approval.

## Master Todo and Dependency Map

| Order | Step | Dependency | Owner | Gate before next step |
|---:|---|---|---|---|
| 1 | STEP-P3-011 Hybrid ranking tuning | P3-010 complete | One implementation sub-agent | Parent read changed files, diagnostics/tests PASS, evidence, auditor PASS |
| 2 | STEP-P3-012 Context injection | STEP-P3-011 PASS | One implementation sub-agent | Parent read changed files, diagnostics/tests PASS, evidence, auditor PASS |
| 3 | STEP-P3-013 Do-not-recall hardening/API | STEP-P3-012 PASS | One implementation sub-agent | Parent read changed files, diagnostics/tests PASS, evidence, auditor PASS |
| 4 | STEP-P3-014 Safe-mode memory gate | STEP-P3-013 PASS | One implementation sub-agent | Parent read changed files, diagnostics/tests PASS, evidence, auditor PASS |
| 5 | STEP-P3-015 Daily consolidation job | STEP-P3-014 PASS | One implementation sub-agent | Parent read changed files, diagnostics/tests PASS, evidence, auditor PASS |

## Collision Scan

| Shared surface | Steps | Collision handling |
|---|---|---|
| `src/memory/read_pipeline.py` | P3-011, P3-013, P3-014 | Serialized; each later agent reads prior changes before editing. |
| `src/memory/write_pipeline.py` | P3-013, possible P3-015 | Serialized; P3-015 must preserve DNR functions/events. |
| `src/memory/__init__.py` | All export-creating steps | Parent or current step owner updates only after reading current exports. |
| `src/core/services/prompt_loader.py` | P3-012, P3-014 integration | P3-012 creates baseline; P3-014 extends safe-mode behavior. |
| `src/core/main.py` | P3-015 | P3-015 only after prior memory gates pass. |
| `tests/memory/` | All steps | Serialized additions; avoid deleting prior tests. |
| `PROGRESS.md`, `CHECKLIST.md` | All steps | Parent-owned tracker sync after each auditor PASS. |
| Evidence directories | All steps | One directory per step; parent verifies file existence/content. |

No implementation may run in parallel in this batch.

## Global Safety and Secret Handling Invariants

- DNR is absolute: no recall, prompt injection, consolidation, summaries, caches, or evidence may expose DNR content.
- DNR and classification filters must run before ranking/fusion and before prompt assembly.
- Safe mode uses `HardStopHandler.is_safe`; no local self-detection in memory code.
- Critical content is blocked in safe mode.
- Restricted/Confidential content is redacted or summarized; raw content never injected in safe mode.
- Only neutral Public/Internal summaries may be injected in safe mode.
- No raw memory, raw prompt, raw surveillance, intimate data, vectors, or secrets in logs/evidence.
- Unknown classification fails closed.
- DB credentials via SOPS-managed environment only; no plaintext credentials.
- OpenRouter/9Router key only via `GUINEVERE_9ROUTER_API_KEY` if needed.
- Never touch Aizanta services, ports, DBs, Redis DBs, or credentials.
- Canonical Guinevere ports remain PostgreSQL 5433, PgBouncer 5434, Redis 6380, 9Router 20128.
- Do not use type suppression, empty catch, skipped tests, or destructive DB operations.

## Step Implementation Designs

### STEP-P3-011 - Hybrid ranking tuning

Goal: tune and test ranked hybrid recall while preserving all P3-010 safety gates.

Required design:

- Keep `RRF_K = 60`.
- Add/confirm tunable weighted RRF parameters: `vector_weight = 0.5`, `fts_weight = 0.5`.
- Keep 90-day recency half-life.
- Apply recency as bounded boost, not relevance override: max 10 percent boost.
- Add/confirm both-signal bonus: vector + FTS presence multiplier `1.25`.
- Bound candidate pool to a deterministic maximum, e.g. `min(limit * EXPANDED_LIMIT_MULTIPLIER, 200)` or documented existing equivalent.
- Ensure DNR and classification ceiling filters execute before ranking/fusion.
- Use precomputed embeddings only; no direct OpenAI/Ollama calls.

Likely files:

- `src/memory/read_pipeline.py`
- `src/memory/__init__.py` if exports are added
- `tests/memory/test_read_pipeline_hybrid.py`

Evidence:

- `docs/setup-evidence/P3/STEP-P3-011/verification.md`
- `docs/setup-evidence/P3/STEP-P3-011/auditor-gate.md`

Acceptance checks:

- RRF k=60 verified.
- Weighted vector/FTS tuning verified.
- 90-day half-life verified.
- DNR pre-filter test PASS.
- Classification fail-closed/ceiling test PASS.
- Deterministic ranking test PASS.

### STEP-P3-012 - Context injection

Goal: inject bounded top-k memory context into system prompt without displacing safety/system/user content.

Required design:

- Default memory token budget: 4000 tokens.
- Default top-k: 3 for prompt injection. Rationale: lower default reduces prompt risk; recall can still retrieve larger sets internally.
- Memory context is discardable; system prompt, safety instructions, and current user input are protected.
- Use only `safe_content` from recall results, never `raw_content`.
- Call recall with `exclude_dnr=True`, caller-supplied `safe_mode`, principal, limit/top-k, and token budget.
- If memory exceeds budget: reduce/truncate memory entries or drop memory, never trim protected prompt sections.
- Add metadata-only logging for memory count, token estimate, truncation/drop reason; no raw content.
- Integrate through `prompt_loader.py` or a small context assembler called by it; do not edit System Prompt Master text.

Likely files:

- `src/core/services/prompt_loader.py`
- `src/core/services/__init__.py` if needed
- `tests/memory/test_prompt_context_injection.py`

Evidence:

- `docs/setup-evidence/P3/STEP-P3-012/verification.md`
- `docs/setup-evidence/P3/STEP-P3-012/auditor-gate.md`

Acceptance checks:

- Non-empty top-k context appears in system prompt when safe memories exist.
- DNR memories excluded.
- Prompt uses `safe_content` only.
- Token budget/truncation behavior documented and tested.
- Safe-mode flag can be propagated but P3-014 finalizes behavior.

### STEP-P3-013 - Do-not-recall hardening/API

Goal: provide controlled DNR mark/unmark flow and prove zero bypass across recall and injection paths.

Required design:

- Add `mark_memory_dnr()` and, if local AC permits, `unmark_memory_dnr()` with explicit consent ledger/audit events.
- Restrict mutation principal to authorized core principal, e.g. `guinevere_core`.
- Events: `MEMORY_DNR_MARKED`; reversal event such as `DNR_REVOKED` only if implemented.
- Keep query-level `do_not_recall = false` filters in all recall query builders.
- Add pre-injection verification that no DNR result reaches prompt assembly.
- Add metadata-only violation counter/log if a DNR item appears after recall; never include raw content.
- Consolidation and derived summaries must exclude DNR.

Likely files:

- `src/memory/write_pipeline.py`
- `src/memory/read_pipeline.py` if post-query guard needed
- `src/memory/__init__.py`
- `tests/memory/test_dnr.py`

Evidence:

- `docs/setup-evidence/P3/STEP-P3-013/verification.md`
- `docs/setup-evidence/P3/STEP-P3-013/auditor-gate.md`

Acceptance checks:

- Setting `do_not_recall=True` causes recall empty for that episode across vector/FTS/recency/context injection.
- DNR mutation emits metadata-only consent/audit event.
- Unauthorized principal cannot mutate DNR.
- DNR reversal, if implemented, is explicit and audited.
- Zero raw DNR content in logs/evidence.

### STEP-P3-014 - Safe-mode memory gate

Goal: integrate `HardStopHandler.is_safe` with memory recall/injection and enforce safe-mode classification/content behavior.

Required design:

- Runtime safe-mode state comes from caller/`HardStopHandler.is_safe`, not memory self-detection.
- `safe_mode=True` recall/injection behavior:
  - DNR still applies.
  - Critical blocked/placeholder.
  - Restricted and Confidential redacted/summarized.
  - Public/Internal only if neutral and safe.
  - Emotional/surveillance/persona escalation content blocked.
- Preserve AC-SAFE-001: safe word/hard stop cannot be bypassed by memory.
- Ensure safe-mode output uses `safe_content` and never raw content.
- Metadata-only logs for redaction/block counts.

Likely files:

- `src/memory/read_pipeline.py`
- `src/core/services/prompt_loader.py`
- `src/core/services/hard_stop_handler.py` only if integration helper is needed; avoid changing trigger semantics.
- `tests/memory/test_safe_mode_memory.py`

Evidence:

- `docs/setup-evidence/P3/STEP-P3-014/verification.md`
- `docs/setup-evidence/P3/STEP-P3-014/auditor-gate.md`

Acceptance checks:

- `HardStopHandler.is_safe=True` leads to `safe_mode=True` memory recall/injection in integration test.
- Critical blocked.
- Restricted/Confidential redacted or summarized.
- Only neutral Public/Internal summaries injected.
- DNR remains absolute.
- AC-SAFE-001 preserved.

### STEP-P3-015 - Daily consolidation job

Goal: implement schedulable daily episodic-to-semantic consolidation without weakening DNR/classification/safe-mode boundaries.

Required design:

- Create `src/memory/consolidation.py`.
- Inspect APScheduler installed version before coding.
- Schedule daily job id `daily_consolidation` for 03:00 Asia/Bangkok.
- Use async DB/session pattern consistent with repo.
- Exclude DNR episodes from consolidation.
- Skip safe-word/crisis/formal-hold records if identifiable.
- Preserve provenance/source episode IDs.
- Preserve highest classification among source episodes/facts.
- Idempotent upsert by deterministic content hash or equivalent stable key.
- No hard delete by default; stale pruning is configurable dry-run/archive/soft-delete first.
- Job errors must log metadata and re-raise; no empty catch.

Likely files:

- `src/memory/consolidation.py`
- `src/memory/__init__.py`
- `src/core/main.py` or scheduler registration surface
- `tests/memory/test_consolidation.py`

Evidence:

- `docs/setup-evidence/P3/STEP-P3-015/verification.md`
- `docs/setup-evidence/P3/STEP-P3-015/auditor-gate.md`

Acceptance checks:

- Scheduler registers `daily_consolidation` at 03:00 Asia/Bangkok or equivalent verified trigger.
- Consolidation excludes DNR.
- Semantic facts preserve provenance and highest classification.
- Idempotent repeated run.
- Configurable stale pruning does not hard-delete by default.
- Tests PASS. `systemctl status guinevere-scheduler` remains service-level evidence caveat unless service is actually installed/approved.

## Delegation Assignments

Each implementation step must use exactly one implementation sub-agent and must include a prompt with TASK, EXPECTED OUTCOME, REQUIRED TOOLS, MUST DO, MUST NOT DO, CONTEXT, and explicit evidence path. Parent must retain task IDs for continuation.

After each implementation step:

1. Parent reads changed source/test/evidence/tracker files.
2. Parent runs `lsp_diagnostics` on changed Python files or relevant directory.
3. Parent runs targeted tests for that step.
4. Parent verifies evidence file has the 12-section minimum schema.
5. Parent syncs `PROGRESS.md` and `CHECKLIST.md` only for the completed step.
6. Parent launches an independent auditor with report path.
7. Parent reads auditor report.
8. Valid findings are fixed via same implementation task ID.
9. Auditor is continued via same auditor task ID until PASS.
10. Only then mark step todo completed and proceed.

## Evidence Minimum Schema Per Step

Each `verification.md` must include:

1. What Was Done
2. Files Changed
3. Validation Results
4. Evidence Artifacts
5. Doc-Sync Impact
6. Boundary Compliance
7. Rollback/Re-run Safety
8. Design Decisions/Caveats
9. Auditor Gate
10. Security Scan
11. Acceptance Criteria Mapping
12. Footer

## Auditor Matrix

| Step | Auditor report path | Required auditor focus |
|---|---|---|
| P3-011 | `docs/setup-evidence/P3/STEP-P3-011/auditor-gate.md` | Ranking correctness, DNR/classification pre-filters, no raw logs, tests/evidence. |
| P3-012 | `docs/setup-evidence/P3/STEP-P3-012/auditor-gate.md` | Prompt injection safety, token budget, safe_content-only, DNR exclusion, protected content preserved. |
| P3-013 | `docs/setup-evidence/P3/STEP-P3-013/auditor-gate.md` | DNR 100 percent exclusion, ledger/audit, unauthorized mutation blocked, zero bypass. |
| P3-014 | `docs/setup-evidence/P3/STEP-P3-014/auditor-gate.md` | HardStopHandler integration, safe-mode classification behavior, AC-SAFE-001, no raw content. |
| P3-015 | `docs/setup-evidence/P3/STEP-P3-015/auditor-gate.md` | Scheduler correctness, DNR exclusion, provenance/classification preservation, idempotency, no destructive pruning. |

Auditor verdicts: PASS permits completion; NEEDS REVIEW or FAIL blocks completion until fixed or documented false-positive accepted by parent.

## Tracker Sync Plan

After each step auditor PASS:

- Update `PROGRESS.md` for that step from unchecked/pending to complete with evidence and auditor path.
- Update `CHECKLIST.md` exact row for that step only.
- Do not mark phase-level integration/security/rollback rows complete unless separately verified.
- Do not commit unless explicitly requested.

## Rollback Plan

- Prefer minimal diffs and app-layer changes.
- For each step, rollback by reverting files touched by that step only.
- Tests use synthetic/fake data only.
- No production DB migrations expected. If a migration becomes necessary, stop and ask/consult before applying.
- P3-015 consolidation must support idempotent re-run and non-destructive pruning; hard delete is out of scope.
- Scheduler registration must be safe to start/stop without affecting Aizanta.

## Verification Commands and Evidence

Minimum commands per step, adjusted to actual repo tooling:

- `lsp_diagnostics` on changed Python files or relevant directories.
- Targeted pytest for new/changed tests, e.g. `python -m pytest tests/memory/test_*.py` or exact step file.
- If markdown tooling exists, targeted markdown lint for touched evidence/tracker files.
- Optional full deterministic memory test subset after P3-015.

Parent must record exact commands, exit codes, and pre-existing failure split in each step evidence.

## Caveats / Blockers to Watch

- Planner sub-agent failed to write this file; parent created this planner file to unblock the mandatory file-based gate. Parent must read/verify this file before implementation.
- Actual classification order must be confirmed from source before P3-014 edits.
- APScheduler version must be confirmed before P3-015 implementation.
- `systemctl status guinevere-scheduler` checklist item may not be satisfiable in code-only environment without service deployment approval; document as caveat unless service exists and checking it is safe.
- Any need for schema migration, destructive operation, Aizanta shared-resource touch, or secret exposure is a hard blocker requiring user approval.

## Execution Checklist

- [ ] Parent verifies this plan file exists.
- [ ] Parent reads this plan fully.
- [ ] Parent syncs active todos to this dependency map.
- [ ] STEP-P3-011 implementation delegated to exactly one sub-agent.
- [ ] STEP-P3-011 parent verification complete.
- [ ] STEP-P3-011 auditor PASS.
- [ ] STEP-P3-012 implementation delegated to exactly one sub-agent.
- [ ] STEP-P3-012 parent verification complete.
- [ ] STEP-P3-012 auditor PASS.
- [ ] STEP-P3-013 implementation delegated to exactly one sub-agent.
- [ ] STEP-P3-013 parent verification complete.
- [ ] STEP-P3-013 auditor PASS.
- [ ] STEP-P3-014 implementation delegated to exactly one sub-agent.
- [ ] STEP-P3-014 parent verification complete.
- [ ] STEP-P3-014 auditor PASS.
- [ ] STEP-P3-015 implementation delegated to exactly one sub-agent.
- [ ] STEP-P3-015 parent verification complete.
- [ ] STEP-P3-015 auditor PASS.
- [ ] Final report includes changed files, validation, evidence, auditor paths, caveats, and next P3-016.

## Footer

Generated for Guinevere P3 memory safety batch on 2026-06-02. This planner gate is binding only after parent read/verification.