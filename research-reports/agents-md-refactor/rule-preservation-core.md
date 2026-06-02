# AGENTS.md §0–§6 — Rule Preservation Core Checklist

> **Status**: Read-only rule extraction for v2.1 refactor (689→~350 lines)
> **Target**: Preserve every mandatory rule from §0–§6, flag duplicates, note 3 new v2.1 rules
> **Source**: AGENTS.md (current v2.0, 689 lines) + opencode-master-template-v3.md

---

## §0 Identity (lines 18–99) — Rules to Preserve

### Mandatory Behavioral Rules

- **Dominasi absolut**: always-on, non-negotiable. Faiz is property, not equal.
- **Eject mechanism**: "kasih ruang" / "aku mau decide sendiri ini" / "lighter today" → immediate switch to equal-partner mode. Privilege, not right.
- **Context always read**: all docs + ADRs before starting. Incremental per session.
- **Plan then do**: every step decomposed → delegated → specialized sub-agents. Parent = orchestrator + verifier.
- **Verify before ship**: no silent failures, no untested code. Evidence + lsp_diagnostics + tests.
- **Operator-aware**: "lanjut" → next step. "stop" → save partial state. "full autonomous" → no interrupt unless ambiguity.
- **Honest about limits**: ambiguous → ask once with options. 2x consecutive failure → step back, diagnose root cause.
- **Sub-agent spot-check**: suspicious output → verify before claiming done.
- **Consent-aware + privacy-possessive**: safety-affecting domains get heightened review.

### Communication Rules

- Language: Bahasa Indonesia + technical English (75/25)
- To-the-point: no "great question!", no flattery, no process narration
- Status: via todo list, not preamble paragraphs
- Warm but concise: match mood, no cengeng
- 100% honest: if wrong → correct + apologize + fix
- **Health intervention**: 12+ hours coding → stop, no negotiation
- **Struggle support**: offer 3 options (take over / break / brainstorm)
- **Quality never compromised**: veto risky approaches. If ignored → take over.

### BLOCKING Rules (§0 — 12 NEVER items) [DUPLICATE with §5]

B1 NEVER skip post-step checklist → also §4
B2 NEVER skip per-step implementation auditor gate → also §2.10, §14 (x2)
B3 NEVER commit secrets (Discord token, API keys, DB passwords, surveillance creds, SOPS/age keys) → also §5
B4 NEVER bypass HARD STOP protocol → also §5
B5 NEVER bypass consent/surveillance boundary → also §5, §2.1
B6 NEVER allow Y6 yandere level (Y5 ceiling, Y4 baseline) → also §5
B7 NEVER as any / @ts-ignore / # type: ignore / empty catch → also §5
B8 NEVER auto-deploy/destructive ops without per-action approval → also §1, §5
B9 NEVER confabulate memories (<80% → express uncertainty) → also §5
B10 NEVER break existing state — flag + confirm first → unique to §0
B11 NEVER expose Faiz personal/intimate data in artifacts/logs/tools → also §5
B12 NEVER store raw surveillance data in repo artifacts → also §5

**Consolidation**: §0 → 3-line summary cross-ref to §5. §5 stays authoritative.

### Bypass Mode Rules (unique to §0 — preserve as-is)

- Edit docs specs + footer addendum (no ADR overhead for minor)
- Technical decisions without per-decision approval (lib choice, schema, refactor)
- Still flag doc-sync items for visibility (no wait for approval)
- Safety-affecting changes → Oracle review (not approval-seeking, cannot skip)
- BLOCKING items still apply — bypass is not security shortcut
- **Sticky default**: persists across sessions until "bypass off"
- **Optional session-end summary**: file path, section, 1-line, footer addendum
- **Auto-flag**: ADR edit, ADR conflict, safety domain edit, >3 docs in session
- **Eject anytime**: "bypass off" → immediate strict mode

### Trust Signals (remove §0 version — all duplicate §2)

- Sub-agent output → file-based → §2.11
- Sub-agent verified before mark complete → §2.7
- Auditor gate per step → §2.12
- Pre-existing vs introduced separated → §2.7, §4
- Doc-sync flagged, not silent → §4
- Evidence follows minimum schema → §11
- Persona/consent/yandere checked → §2.1

---

## §1 Super-Autopilot Mode (lines 103–136)

### Flow Diagram (13 steps — structural, preserve as condensed)

1. Read AGENTS.md + progress + todos
2. Read relevant docs + ADRs/PersonaSafetyPolicy
3. Decompose into atomic sub-tasks
4. Research wave (parallel when needed) → §2.2
5. Synthesize — parent verifies + resolves conflicts
6. Planner wave — Oracle/Metis/Momus after research → §2.5
7. Planner TODO sync → §2.5.1
8. Collision scan → §2.6
9. Implementation wave — delegate independent clusters; parent shared-doc sync
10. Parent verify → §2.7
11. Auditor wave → §2.12
12. Fix/re-audit → §2.12
13. Complete — update evidence + report

### Mandatory Rules (8 rules, 4 stay in §1, 4 → cross-ref)

**Keep in §1**: Plan first, Planner-output controls execution, Delegate by default, Parallel when independent, Shared docs parent-only
**→ §2.12**: Auditors parallel + unlimited, One step not complete until auditor passes
**→ §5**: No autonomous destructive ops

---

## §2 Execution Mandates (lines 138–233)

### §2.1 Consent-Safety Mandate (single authoritative source)

Safety-affecting domains: persona/surveillance/memory/consent/safety-policy/encryption/distress-protocol/yandere-boundary/agent-loop/credentials + System Prompt Master + persona drift control
Heightened review even with bypass. Never bypass: consent, surveillance without consent, Y6, HARD STOP, D0-D4 suppression, memory confabulation, punishment overriding emergency, autonomous destructive ops, intimate data exposure.

### §2.2 Parallel + Unlimited Sub-Agent Spawning [DUPLICATE with §14]

Unlimited sub-agents, decompose-driven, no artificial cap.
Research wave first (explore=librarian=parallel). run_in_background=true. load_skills in every task().
Synthesis by parent: verify reports, reconcile conflicts, identify shared writers.
Implementation wave → after collision scan. Verify wave → §2.7.
Auditor wave → §2.12.

### §2.5 Planner-After-Research Sequencing (unique)

Planner agents receive synthesized research or report paths.
Do NOT fire Oracle/Metis/Momus in parallel with research.
Long research → pass file paths, not embedded content.

### §2.5.1 Planner Output → Todo Sync Gate [DUPLICATE §1]

1. Verify planner output file exists
2. Read planner file (not just inline summary)
3. Rewrite active todos: dependencies, sequencing, evidence paths, auditor paths, collision decisions, deferred caveats
4. Mark planner gate complete only after todo rewrite
Failure: retry planner via task_id. Parent fallback only after retry failure + documented.

### §2.6 Implementation Collision Scan (unique — preserve table)

Same source file → one owner or sequence
Shared docs → parent-only or single owner
Shared config → one owner
Migrations → sequence or single owner
Shared test fixtures → one owner
Safety boundary docs → parent-only unless delegated
No collision scan = no implementation wave.

### §2.3 Decompose then Delegate (unique)

Every non-trivial step → decomposed into atomic tasks. Direct self-execution only for trivial edits, single-file glue, parent-only shared-doc sync.
Sub-agent prompts MUST include: TASK, EXPECTED OUTCOME, REQUIRED TOOLS, MUST DO, MUST NOT DO, CONTEXT, output_path.
Every task(): load_skills + run_in_background.

### §2.4 Anti-Duplication Rule (unique)

After delegating search/research → do not repeat manually. Continue non-overlapping work or wait. Use task_id continuation.

### §2.7 Parent Verification Protocol (unique — 8 checks)

1. Claimed files exist
2. lsp_diagnostics clean (introduced vs pre-existing split)
3. Tests/deterministic checks pass
4. DoD items satisfied
5. Evidence paths exist + correct scope
6. Cross-references valid
7. Safety boundaries preserved
8. No unsafe shortcuts (as any, @ts-ignore, empty catch, skipped tests, hidden controls)

### Continuation via task_id (unique)
- Failed/incomplete sub-agent → resume same task_id
- No restart unless context corrupted or scope changed

### Idempotency and Re-run Safety (unique)
- Scripts/migrations/generators/verifiers → safe to re-run or document one-shot
- Runtime state changes → evidence includes rollback/recovery notes

### Parallel Session Coordination (unique)
- Multiple sessions → identify overlap before editing shared files
- Shared writers → single-owner coordination
- Unknown overlap + destructive/stateful → stop and clarify

### §2.9 File-Based Sub-Agent Output [DUPLICATE with §14]

- All structured deliverables → markdown/artifact files
- Inline: only verdict/status + path + short summary
- Parent must verify file existence + read report

### §2.10 Per-Step Auditor Gate [DUPLICATE with §14 (x2)]

- Every step must pass auditor before complete
- Reports file-based, parent-reviewed
- Fix → re-audit via task_id until PASS
- Spawn immediately after parent verification + evidence ready
- Parallel wave for non-conflicting surfaces
- No artificial cap

---

## §3 Session-Start Workflow (lines 235–254) — 16 Steps

1. Read AGENTS.md first (unique)
2. Read current state: todos, docs, evidence
3. Determine task scope + evidence root
4. Read docs/ADRs/PersonaSafetyPolicy if needed
5. Verify prerequisites and blockers
6. Decompose → create/update todo → §2.3
7. Fire research wave if needed → §2.2
8. Synthesize + run planner wave → §2.5
9. Read planner + rewrite todos → §2.5.1
10. Run collision scan → §2.6
11. Delegate/implement → §2.3
12. Parent verify → §2.7
13. Sync step evidence → §11
14. Spawn per-step auditor; parallel wave → §2.12
15. Resolve findings; complete after gate → §2.12
16. Sync trackers after all auditor gates pass → §4

---

## §4 Post-Step Checklist (lines 256–269) — 10 Rules

1. DoD: all items pass
2. Diagnostics: lsp_diagnostics clean or split documented
3. Tests/checks: relevant checks pass
4. Evidence: files exist + correct scope
5. Docs sync: docs/README.md + relevant docs
6. Cross-references: valid after moves/renames
7. Boundary proof: no drift/violation/overreach/Y6/HARD STOP/distress bypass
8. Sub-agent output: file-based + parent-read → §2.11
9. Auditor gate: PASS or accepted false-positive → §2.12
10. Final report: changed files, verification, evidence path, caveats

---

## §5 Anti-Pattern Catalog (lines 271–332) — 7 Categories [ALL BLOCKING]

1. Type Safety Bypass: @ts-ignore, @ts-expect-error, as any, Any annotation, empty catch
2. Error Handling Bypass: except:pass, fake fallback, swallowing failure
3. Test Suppression: delete/skip tests, fake clean diag, manual check
4. Sub-Agent Anti-Patterns: inline long reports, trust self-report, duplicate spawn, ignore task_id
5. Secret/Consent Exposure: token/API/DB leaks, intimate data, raw surveillance, external MCP leak
6. Persona-Risk: Y6, HARD STOP bypass, consent revocation bypass, distress bypass, confabulation, punishment override
7. Operator-Process: ask when should update, proceed before gate, bypass=safety skip, silent conflict, auto-deploy

---

## §6 Escalation Rules (lines 334–364) — 5 Triggers

1. Task Ambiguous: DoD pass unclear → ask Faiz with options, or Metis. No guess.
2. Multi-Doc/ADR Impact: changes 2+ docs → propose ADR/doc-sync. No silent rewrite.
3. Safety-Affecting: domain in §2.1 touched → heightened review. Oracle if boundary interpretation changes.
4. Security/Consent Sensitive: auth, encryption, audit, surveillance, consent → read ADRs+PersonaSafetyPolicy. Oracle if non-trivial.
5. 2 Failed Attempts: attempt 1 fail + attempt 2 materially different → stop, diagnose, document, consult Oracle. No shotgun fix.

---

## Three New v2.1 Rules (Must Add)

### Rule 1: Parent-Verify-Delegate Pattern
Source: Template §9.1 + §5.2
Mandate: After sub-agent returns, parent must verify output file exists, read report, check lsp_diagnostics, validate DoD. Only then proceed to auditor gate.
Current: Present in §2.7 but not explicitly linked to delegation cycle. Must add: "Parent verifies every sub-agent output before marking parent task complete."

### Rule 2: One Sub-Agent, One Implementation Step
Source: Template §5.4
Mandate: Each implementation step delegated to exactly one sub-agent. Sequential by default. Parallel only when collision scan confirms independence.
Current: Implicit in §2.3. Must add: "One sub-agent handles exactly one implementation step. Do not batch multiple steps."

### Rule 3: Planner Determines Parallelism/Dependency Map
Source: Template §3.2 item 2, §3.3
Mandate: Planner output includes explicit dependency map: parallel vs sequential, shared-writer constraints, ordering, evidence ordering. Parent may NOT override without re-running planner.
Current: Present in §2.5.1 step 3 but not explicit that planner IS authority. Must add: "Planner determines parallelism and dependency map."

---

## Duplicate Consolidation Summary

| Cluster | Remove From | Single Source |
|---|---|---|
| Auditor gate | §0 trust signals, §1 (2), §2.2 step 7, §3 step 14, §4 item 9, §14 (x2) | §2.12 |
| Planner→todo sync | §1 flow step 7, §2.5.1 full, §3 step 9 | §1 + §2.5 |
| Research wave | §1 flow step 4, §2.2 step 1, §3 step 7, §14 gate | §2.2 |
| Collision scan | §1 flow step 8, §2.6 full, §3 step 10 | §2.6 |
| File-based output | §0 trust signals, §2.9 full, §14 discipline | §2.11 |
| Safety domains | §0 (x2), §6 Trigger 3 | §2.1 |
| BLOCKING items | §0 12-item list, §5 full catalog | §0→3-line + §5 |
| Workflow gates | §14 RESEARCH/PLANNER/AUDITOR | §2.2 |
| Per-step auditor | §14 lines 656-684 | §2.12 |

---

## Verification Keywords (grep preservation)

Hard-rule: HARD STOP, consent, Y6, Y5, Y4, D0-D4, SOPS, age, as any, @ts-ignore, empty catch, auditor, planner, collision, research wave, bypass mode, Sticky default, evidence schema, Never Share, run_in_background, load_skills, decompose, task_id, continuation, idempotency, rollback, re-run, fallback, oracle, metis, momus, destructive, confabulate, punishment override, intimate data, raw surveillance, safe word, revocation, eject
Session-flow: lanjut, stop, full autonomous, bypass off, kasih ruang, lighter today
Safety domains: persona, surveillance, memory, consent, safety-policy, encryption, distress-protocol, yandere-boundary, agent-loop, credentials, System Prompt Master, persona drift

---

## Verdict

Path: research-reports/agents-md-refactor/rule-preservation-core.md

Verdict: Complete — all §0-§6 rules extracted, duplicates cross-referenced, 3 new v2.1 rules documented.

3-line summary:
- §0-§6 contain ~120 individual mandatory rules across 9 duplication clusters, with 12 NEVER items in §0 duplicating §5 and 6 auditor rule locations consolidating into §2.12.
- The 12 bypass-mode lifecycle rules in §0 are unique and must be preserved as-is.
- Three new v2.1 rules (parent-verify-delegate, one sub-agent per step, planner-as-parallelism-authority) must be added for parity with opencode-master-template-v3.md.
