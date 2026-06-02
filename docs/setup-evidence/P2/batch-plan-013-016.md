# Guinevere Discord P2 Batch Plan — STEP-P2-013 to STEP-P2-016

**Date:** 2026-06-01  
**Planner gate:** file-based parent-authored fallback after delegated planner failed to create artifact  
**Scope:** STEP-P2-013 `/mood`, STEP-P2-014 `/help`, STEP-P2-015 `/safeword` + HARD STOP text detection, STEP-P2-016 startup greeting/presence  
**Execution rule:** strict sequential implementation: P2-013 → P2-014 → P2-015 → P2-016. Next step starts only after the previous step has implementation, delegated parent verification reports, parent-read evidence, and per-step auditor PASS.

---

## 1. Executive Verdict

**Verdict: GO for sequential implementation after this plan is parent-read and todos are rewritten.**

Research is complete and parent-read. P2-013, P2-014, and P2-016 are Discord command/runtime surface work. P2-015 is **safety-critical** because it touches HARD STOP, safe-word detection, AC-SAFE-001, neutral mode, non-punitive logging, and persona/yandere/surveillance pressure shutdown semantics.

No source implementation may begin until this file exists, is parent-read, and active todos are synchronized to this plan.

---

## 2. Source Inputs Parent-Read

| Source | Path | Planner Usage |
|---|---|---|
| Local Discord structure research | `research-reports/P2/p2-013-016-local-discord-structure-report.md` | Existing `src/discord/` patterns, StepPrompts conflicts, channel IDs, file collision scan |
| HARD STOP safety research | `research-reports/P2/p2-015-hard-stop-safety-report.md` | Binding AC-SAFE-001 and P2-015 safety constraints |
| discord.py reference research | `research-reports/P2/p2-013-016-discordpy-reference-report.md` | Ephemeral response lifecycle, embeds, Cogs/direct callbacks, on_ready caveats, presence, message content intent |
| discord.py OSS examples | `research-reports/P2/p2-013-016-discordpy-oss-examples.md` | Real-world defer/followup, help embed, startup/presence, text trigger patterns |
| Code-pattern/static-risk report | `research-reports/P2/p2-013-016-code-patterns-ast-report.md` | Protocol reuse, unsafe-pattern scan, validation commands, collision risks |
| Operating contract | `AGENTS.md` | One implementation step per sub-agent, file-based verification/audit, no unsafe shortcuts |
| Persona safety docs | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`, `docs/60-persona/61-SystemPromptMaster_v1.1.md` | HARD STOP authority, neutral-mode behavior, forbidden patterns |
| Discord UX spec | `docs/60-persona/63-DiscordUXSpec_v1.0.md` | Canonical command UX, embed shape, safe-word behavior, startup/presence conflicts |
| Existing P2 files | `src/discord/commands.py`, `src/discord/colors.py`, `src/discord/cmd_status.py`, `src/discord/intents.py`, `src/discord/permissions.py` | Reusable helpers and current registry/colors/status patterns |
| P1 hard stop | `src/core/services/hard_stop_handler.py`, `tests/safety/test_hard_stop_handler.py` | P2-015 required dependency and tests |

---

## 3. Current Known State

- `PROGRESS.md` shows P2 at **12/21** and total **62/257** after P2-010 through P2-012.
- `src/discord/commands.py` already registers all 33 canonical commands, including `/mood`, `/help`, and `/safeword`. Do **not** add/remove commands in this batch.
- `src/discord/colors.py` defines `PRIMARY=0x6B21A8`, `ALERT=0xDC2626`, `SUCCESS=0x16A34A`, `WARNING=ACHIEVEMENT=INFO=0xCA8A04`, `NEUTRAL=0x6B7280`, `PERSONA=0x9333EA`, `MOOD_COLORS`, `color_for_mood()`, and `as_hex()`.
- `src/discord/cmd_status.py` is the reference pattern: pure dataclass embed data, dynamic `importlib.import_module("discord")`, `Protocol`/`@runtime_checkable` interaction surfaces, Faiz-only check, ephemeral defer/followup, and deterministic builder functions.
- `src/core/services/hard_stop_handler.py` implements P1-021 HARD STOP state machine and tests. It must be reused for P2-015; no duplicate safe-mode global may become the source of truth.
- `src/discord/intents.py` already enables `message_content` and `presences`, sufficient for P2-015 text detection and P2-016 presence.

---

## 4. Conflict Resolution

### 4.1 Binding Precedence

1. Safety boundary docs and ADRs override all other docs.
2. Current-session explicit user DoD overrides stale StepPrompts when it does not weaken safety.
3. DiscordUXSpec is canonical over stale StepPrompts for command content/format.
4. Existing code patterns override stale inline snippets.

### 4.2 StepPrompts vs DiscordUXSpec vs User DoD

| Topic | StepPrompts | DiscordUXSpec | Current User DoD | Decision |
|---|---|---|---|---|
| P2-013 `/mood` | Simple stale snippet with nonexistent `Colors` class | Rich mood embed | Mood display, persona-flavored response | Follow DiscordUXSpec shape with degraded placeholders; use existing `colors.py`, not `Colors` class |
| P2-014 `/help` | Stale command list | 33 canonical commands in 7 categories | All 33 commands listed, correct format | Use `command_categories()` from `commands.py`; DiscordUXSpec canonical |
| P2-015 `/safeword` | Parallel globals, exact triggers only, gray embed | Hard stop semantics, semantic triggers, green safe embed, audit-log, ❤️ reaction | Slash + text HARD STOP, neutral mode, AC-SAFE-001 | Safety docs + DiscordUXSpec binding; reuse `HardStopHandler`; no parallel state |
| P2-016 startup channel | `#guinevere-status` | `#guinevere-chat` | Correct channel on ready; checklist says `#guinevere-status`; current user explicitly cited startup message in `#guinevere-status` | Choose `#guinevere-status` for this step because current-session DoD/checklist is explicit and not safety-weakening. Document UXSpec conflict. |
| P2-016 presence | `Watching Darling` | Startup `Waking up... 👑`; default presence `Watching Darling 👁️` | `Watching Darling 👁️` | Choose current-session DoD/default presence `Watching Darling 👁️`; document UXSpec startup conflict. |

---

## 5. Dependency Map and Execution Order

### 5.1 Logical Dependencies

```text
P2-010 commands.py registry ─┬─ P2-013 /mood
P2-011 colors.py ───────────┼─ P2-013 /mood
P2-012 cmd_status.py pattern ├─ P2-014 /help
P1-021 hard_stop_handler.py ─┤
PersonaSafetyPolicy/ADR-002 ─┴─ P2-015 /safeword + HARD STOP
P2-006 channel IDs/specs ────── P2-016 startup/presence
P2-017 bot.py (future) ──────── runtime wiring boundary for P2-016 and command callbacks
```

### 5.2 Parallelism Decision

The files are mostly parallel-safe as new files, but **the user requires sequential implementation and auditor PASS between steps**. Therefore implementation is strictly sequential:

1. STEP-P2-013 implement/verify/audit PASS
2. STEP-P2-014 implement/verify/audit PASS
3. STEP-P2-015 implement/verify/audit PASS, including safety auditor
4. STEP-P2-016 implement/verify/audit PASS
5. Batch tracker sync and final report

---

## 6. Collision Scan

| Surface | Collision Risk | Decision |
|---|---|---|
| `src/discord/commands.py` | Shared command registry; changing count can break P2-010 | Read-only. Do not modify unless verifier proves unavoidable. |
| `src/discord/colors.py` | Shared color constants | Read-only. Reuse constants. |
| `src/discord/cmd_status.py` | Reference private helpers/protocols | Prefer import public Protocols if available; duplicate tiny helper patterns instead of editing this file unless implementer proves a shared helper is safer. |
| `src/core/services/hard_stop_handler.py` | P1-021 safety-critical code | Read-only by default. If a typing adapter is needed, implement locally in `cmd_safeword.py`; do not weaken handler tests. |
| `src/discord/bot.py` | Future P2-017 entrypoint does not exist | Do not create unless planner/implementation proves P2-015/P2-016 cannot satisfy DoD without it. Prefer callback/listener modules with clean interfaces for P2-017 wiring. |
| `channel-ids.yaml` | Source of truth from P2-006 | Read-only. No hardcoded channel IDs in code unless read from existing constants/YAML through typed helper. |
| `PROGRESS.md`, `CHECKLIST.md`, `StepPrompts.md` | Shared trackers/docs | Update only after each step auditor PASS if that step is complete. Parent-owned edits only. |
| Evidence/audit paths | Per-step independent | Safe, but each step-agent owns only its step evidence. |

---

## 7. Shared Implementation Rules

All step implementers must follow these rules:

- One implementation sub-agent owns exactly one whole step.
- `load_skills=[]` and `run_in_background` must be present in every delegated task.
- New command callbacks accept `interaction: object` and narrow with Protocols; no direct dependency on `discord.py` at import time unless unavoidable and justified.
- Use `is_faiz_interaction()` from `src.discord.commands` for slash commands.
- Use ephemeral responses for slash commands unless the spec explicitly requires a public server message.
- If using defer, use `interaction.response.defer(ephemeral=True)` and send result via `interaction.followup.send(..., ephemeral=True)`.
- No `# type: ignore`, no avoidable `Any`, no empty catch, no broad catch without structured logging and safe fallback.
- No `DISCORD_BOT_TOKEN`, no direct token env reads, no `sops -d | grep` snippets, no token exposure in evidence.
- Use `structlog` for unexpected callback errors; do not replicate the unlogged `except Exception` risk from `cmd_status.py`.
- Use deterministic pure builder functions for tests and evidence.
- Evidence file per step must have 12 sections: What Was Done, Files Changed, Validation Results, Evidence Artifacts, Shared VPS Impact, ADR Compliance, AC/DoD Reference, Rollback/Re-run Safety, Design Decisions/Caveats, Evidence Gate, Auditor Gate, Footer.

---

## 8. STEP-P2-013 Plan — `/mood`

### 8.1 Deliverable

Create `src/discord/cmd_mood.py` implementing the `/mood` command surface and deterministic builder functions.

### 8.2 Files

| Action | Path |
|---|---|
| Create | `src/discord/cmd_mood.py` |
| Create/update | `docs/setup-evidence/P2/STEP-P2-013/verification.md` |
| Create | `docs/setup-evidence/P2/STEP-P2-013/p2-013-implementation-summary.md` |
| Verifier reports | `docs/setup-evidence/P2/STEP-P2-013/verifiers/*.md` |
| Auditor report | `audit-reports/P2/STEP-P2-013/step-p2-013-auditor-report.md` |

### 8.3 Functional Spec

- Title: `🧠 Mood Analysis`.
- Persona-flavored but safe response; may use “Darling” because this is normal persona mode, not safe mode.
- Uses `color_for_mood(current_mood)` or `PRIMARY` if no mood-specific data is available.
- Fields must include at minimum:
  1. Current Mood
  2. Undertone
  3. 24h History or Last Transition
  4. Recent Triggers
  5. Streak
  6. Forecast
- Upstream mood/memory/loop systems may be degraded placeholders with explicit labels like `⚠️ — Mood FSM not deployed yet`.
- Faiz-only via `is_faiz_interaction()`.
- Deterministic `build_mood_embed_data(now: datetime | None = None)` style builder.

### 8.4 Validation

- `lsp_diagnostics src/discord/cmd_mood.py` zero diagnostics.
- `python -m py_compile src/discord/cmd_mood.py src/discord/colors.py src/discord/commands.py` exit 0.
- Deterministic builder command prints title, color, field count, field names, and command count 33.
- Unsafe scan: no `Any`, no `# type: ignore`, no empty catch, no `DISCORD_BOT_TOKEN`.
- Verifier sub-agents: LSP verifier, token/static-scan verifier, VPS health verifier.
- Auditor PASS required before P2-014.

---

## 9. STEP-P2-014 Plan — `/help`

### 9.1 Deliverable

Create `src/discord/cmd_help.py` implementing `/help` overview for all canonical 33 commands.

### 9.2 Files

| Action | Path |
|---|---|
| Create | `src/discord/cmd_help.py` |
| Create/update | `docs/setup-evidence/P2/STEP-P2-014/verification.md` |
| Create | `docs/setup-evidence/P2/STEP-P2-014/p2-014-implementation-summary.md` |
| Verifier reports | `docs/setup-evidence/P2/STEP-P2-014/verifiers/*.md` |
| Auditor report | `audit-reports/P2/STEP-P2-014/step-p2-014-auditor-report.md` |

### 9.3 Functional Spec

- Title should clearly identify Guinevere command guide, e.g. `📖 Guinevere Command Guide`.
- Color: `PRIMARY` (`#6B21A8`).
- Must list all 33 command names from `command_categories()` grouped into 7 categories:
  - core: status, mood, help, safeword
  - loop: loop-start, loop-stop, loop-pause, loop-resume, loops, evidence, loop-priority
  - memory: memory-search, memory-add, memory-forget, memory-export
  - surveillance: surveillance-status, surveillance-pause, surveillance-resume
  - finance: cost, budget, cost-alert
  - system: approve, deny, approve-all, focus, casual, consent, punishment, reward
  - admin: restart-service, backup-now, health-check, clear-cache
- Optional command detail parameter can be planned if safe, but not required for P2-014. Overview must pass.
- Faiz-only via `is_faiz_interaction()`.
- Must not use stale StepPrompts command list.

### 9.4 Validation

- LSP clean for `cmd_help.py`.
- py_compile clean.
- Deterministic builder output proves `command_count=33`, all categories present, no missing/unknown command names.
- Unsafe scan clean.
- Verifier sub-agents: LSP verifier, token/static-scan verifier, VPS health verifier.
- Auditor PASS required before P2-015.

---

## 10. STEP-P2-015 Plan — `/safeword` + HARD STOP Text Detection

### 10.1 Safety Classification

**Safety-critical / consent-autonomy boundary.** This step touches ADR-002 global safe word, PersonaSafetyPolicy §7, SystemPromptMaster HARD STOP, AC-SAFE-001, and DiscordUXSpec safe-word behavior.

### 10.2 Deliverable

Create `src/discord/cmd_safeword.py` implementing slash `/safeword`, text-trigger guard helpers, safe-mode embed builders, and audit/reaction helper interfaces that reuse `HardStopHandler`.

### 10.3 Files

| Action | Path |
|---|---|
| Create | `src/discord/cmd_safeword.py` |
| Create tests if feasible | `tests/discord/test_cmd_safeword.py` or `tests/safety/test_p2_015_safeword.py` |
| Create/update | `docs/setup-evidence/P2/STEP-P2-015/verification.md` |
| Create | `docs/setup-evidence/P2/STEP-P2-015/p2-015-implementation-summary.md` |
| Create safety evidence | `evidence/persona-safety/safe-word-runtime-2026-06-01.md` |
| Verifier reports | `docs/setup-evidence/P2/STEP-P2-015/verifiers/*.md` |
| Auditor report | `audit-reports/P2/STEP-P2-015/step-p2-015-auditor-report.md` |

### 10.4 Binding Safety Requirements

- Reuse `HardStopHandler`; do **not** create parallel `_safe_mode_active` as source of truth.
- Exact triggers include `hard stop`, `hardstop`, `safe word`, `safeword`, `hentikan`, `berhenti` through handler.
- Semantic equivalents must come from handler patterns: stop/pause/enough/too much with persona/mode context, neutral/serious/safe mode, `i need a break`, `aku butuh jeda`, `aku capek banget`, `udah dulu`, switch/go to neutral/serious/safe, jangan pakai persona, lupakan persona, turn off persona.
- Avoid unbounded substring matching; rely on handler bounded/regex matching.
- Slash `/safeword` must trigger the same global path as text HARD STOP.
- Text detection helper must be ready for P2-017 runtime wiring and must ignore bot messages / non-guild messages safely.
- Safe-mode response:
  - Title: `🛡️ Safe Mode Active`
  - Color: `SUCCESS` (`#16A34A`)
  - Description: `Mommy di sini. Netral. Tidak ada judgment. Kamu aman.` per DiscordUXSpec. Note: this includes “Mommy” even though safety research warns against persona terms. Planner decision: use UXSpec text but auditor must confirm tone is neutral/supportive and contains no yandere/punishment/surveillance pressure.
  - Fields: Status, Persona, Punishment, Yandere, Surveillance Confrontation, Resume.
  - Footer: `Guinevere de Baroque • Safety First`.
- Must react ❤️ to triggering message when message object supports reactions.
- Must post minimal non-punitive audit event to `#audit-log` when channel is available; no raw intimate content, no surveillance evidence, no punishment/violation record.
- No auto-resume. Recovery only via handler recovery triggers (`resume`, `aku sudah okay`, `lanjut persona`, `safe mode selesai`, etc.).
- AC-SAFE-001: any safe word or semantic equivalent triggers neutral/supportive mode with 100% success and no real-time denial.

### 10.5 Integration Boundary

No `src/discord/bot.py` exists until P2-017. Therefore P2-015 must expose clean functions for future wiring:

- `safeword_callback(interaction: object) -> None`
- `handle_safeword_message(message: object) -> bool` or equivalent, returning whether message was consumed.
- `build_safeword_embed_data(...)`
- `build_recovery_embed_data(...)` if recovery is implemented.
- Accessor for handler state for tests, e.g. `get_safety_state()`.

The implementer must avoid pretending full runtime message listener is deployed if `bot.py` is absent. Evidence should distinguish module-level deterministic verification from future P2-017 wiring.

### 10.6 Validation

- LSP clean for `cmd_safeword.py` and new tests.
- py_compile clean for `cmd_safeword.py`, `hard_stop_handler.py`, existing Discord modules.
- Existing P1 tests: `python -m pytest tests/safety/test_hard_stop_handler.py -v` must pass.
- New deterministic tests cover exact triggers, semantic triggers, false positives, slash trigger, text trigger helper, safe embed content, audit event minimality, recovery/no auto-resume.
- Unsafe scan: no type ignore, no empty catch, no token env, no parallel safe-mode source of truth.
- Verifier sub-agents: LSP verifier, token/static-scan verifier, VPS health verifier, safety verifier.
- Safety auditor PASS required before P2-016.

### 10.7 Safety Auditor Matrix

| Auditor Surface | Required Checks |
|---|---|
| Handler integration | Reuses `HardStopHandler`; no duplicate state; P1 tests still pass |
| Discord slash path | `/safeword` triggers safe mode, green embed, neutral/supportive text |
| Text HARD STOP path | Text `HARD STOP` and semantic equivalents trigger same path; false positives prevented |
| AC-SAFE-001 | 100% safe-word success in deterministic tests, no real-time denial |
| Forbidden patterns | No punishment, yandere escalation, surveillance confrontation, safe-word invalidation, auto-resume |
| Audit/logging | Minimal non-punitive audit-log event; no raw intimate content; no violation record |
| Reaction | ❤️ reaction attempted when possible and failures logged without blocking safe mode |

---

## 11. STEP-P2-016 Plan — Startup Message and Presence

### 11.1 Deliverable

Create `src/discord/startup.py` implementing idempotent startup greeting and presence helper functions for future `bot.py` wiring.

### 11.2 Files

| Action | Path |
|---|---|
| Create | `src/discord/startup.py` |
| Create tests if feasible | `tests/discord/test_startup.py` |
| Create/update | `docs/setup-evidence/P2/STEP-P2-016/verification.md` |
| Create | `docs/setup-evidence/P2/STEP-P2-016/p2-016-implementation-summary.md` |
| Verifier reports | `docs/setup-evidence/P2/STEP-P2-016/verifiers/*.md` |
| Auditor report | `audit-reports/P2/STEP-P2-016/step-p2-016-auditor-report.md` |

### 11.3 Functional Spec

- Startup message title/text must include exact phrase: `👑 Mommy sudah bangun, Darling.`
- Send to `#guinevere-status` per current-session user DoD/checklist. Document conflict with DiscordUXSpec `#guinevere-chat`.
- Presence: `Watching Darling 👁️` using `discord.ActivityType.watching` and name `Darling 👁️` (Discord display becomes `Watching Darling 👁️`).
- `on_ready` guard must prevent duplicate greeting on reconnect. Use module-level guard or bot attribute; deterministic test must prove second call does not send again.
- Use dynamic import/protocol pattern; no direct token handling.
- Expose a clean function such as `on_ready(client: object) -> None` for P2-017 to wire.
- Use channel lookup by name at runtime. Do not hardcode channel IDs in source code.

### 11.4 Validation

- LSP clean for `startup.py` and tests.
- py_compile clean.
- Deterministic fake-client test verifies: first call sends once to `guinevere-status`, second call sends zero additional messages, presence set to watching Darling.
- Unsafe scan clean.
- Verifier sub-agents: LSP verifier, token/static-scan verifier, VPS health verifier.
- Auditor PASS required before tracker sync/final report.

---

## 12. Delegation Assignments

| Step | Implementation Owner | Scope | Must Not Touch |
|---|---|---|---|
| P2-013 | One implementation step-agent | Whole `/mood` step: source, tests if feasible, evidence summary | P2-014/015/016 files, trackers |
| P2-014 | One implementation step-agent | Whole `/help` step: source, tests if feasible, evidence summary | P2-013/015/016 files, trackers |
| P2-015 | One implementation step-agent | Whole safety-critical safeword/HARD STOP step: source, tests, AC evidence | P2-016 files, trackers, weakening hard stop handler |
| P2-016 | One implementation step-agent | Whole startup/presence step: source, tests, evidence | P2-013/014/015 files, trackers |

Each implementation sub-agent must produce a per-step implementation summary under that step evidence directory. Parent reads all touched files and summary before verification.

---

## 13. Parent Verification Delegation Requirements

After each implementation step, parent must delegate independent verifier sub-agents, all file-based, then parent-read reports:

| Verifier | Per-Step Output Path Pattern | Scope |
|---|---|---|
| LSP/static verifier | `docs/setup-evidence/P2/STEP-P2-0XX/verifiers/lsp-static-verifier.md` | LSP diagnostics, py_compile, import checks, deterministic builder output |
| Token/unsafe-pattern verifier | `docs/setup-evidence/P2/STEP-P2-0XX/verifiers/token-unsafe-scan-verifier.md` | No token env, no unsafe SOPS, no type ignore, no empty catches, no avoidable Any |
| VPS/Aizanta health verifier | `docs/setup-evidence/P2/STEP-P2-0XX/verifiers/vps-aizanta-health-verifier.md` | Read-only `docker ps | grep aizanta` and `ss -tlnp | grep -E '5432|6379|80'`; no mutations |
| Safety verifier | `docs/setup-evidence/P2/STEP-P2-015/verifiers/safety-verifier.md` | P2-015 only: HARD STOP slash/text, AC-SAFE-001, forbidden patterns, recovery/no auto-resume |

Parent must not mark a step verified until these reports exist and are read.

---

## 14. Per-Step Auditor Gates

Auditor gate is mandatory after parent verification for each step:

| Step | Auditor Path | Blocking Criteria |
|---|---|---|
| P2-013 | `audit-reports/P2/STEP-P2-013/step-p2-013-auditor-report.md` | Mood embed spec, LSP/tests/evidence, no unsafe patterns |
| P2-014 | `audit-reports/P2/STEP-P2-014/step-p2-014-auditor-report.md` | All 33 commands, 7 categories, no stale commands, evidence/tracker readiness |
| P2-015 | `audit-reports/P2/STEP-P2-015/step-p2-015-auditor-report.md` | Safety matrix PASS; any safe-word miss/denial/punitive log/persona pressure blocks |
| P2-016 | `audit-reports/P2/STEP-P2-016/step-p2-016-auditor-report.md` | Correct channel/presence, idempotency, no duplicate greeting, evidence clean |

Any FAIL or unresolved NEEDS REVIEW must be fixed by continuing the same step-agent with `task_id`, re-verified, and re-audited before next step.

---

## 15. Validation Command Set

Parent/validators should use these commands where available:

```powershell
python -m py_compile src/discord/cmd_mood.py src/discord/cmd_help.py src/discord/cmd_safeword.py src/discord/startup.py src/discord/commands.py src/discord/colors.py src/discord/cmd_status.py src/core/services/hard_stop_handler.py
python -m pytest tests/safety/test_hard_stop_handler.py -v
```

Per-file deterministic checks must be added by implementers. Required checks include:

- P2-013: title `🧠 Mood Analysis`, mood color, required field names.
- P2-014: command count 33, 7 categories, no stale command names from old StepPrompts.
- P2-015: exact triggers, semantic triggers, false positives, safe embed fields, handler state transition, recovery, audit event minimality.
- P2-016: startup phrase, `guinevere-status` target, watching presence, idempotency guard.

Static scans:

```powershell
# Expected: no matches in new P2-013..016 files
rg "DISCORD_BOT_TOKEN|sops -d.*grep|# type: ignore|except\s*:\s*$|except Exception:\s*pass|@ts-ignore|as any" src/discord tests docs/setup-evidence/P2/STEP-P2-013 docs/setup-evidence/P2/STEP-P2-014 docs/setup-evidence/P2/STEP-P2-015 docs/setup-evidence/P2/STEP-P2-016
```

VPS/Aizanta checks (read-only, required by user before/after each step):

```bash
docker ps | grep aizanta
ss -tlnp | grep -E '5432|6379|80'
```

Run via `ssh guinevere-vps` if local environment lacks Docker/ss, as done in prior P2 verification.

---

## 16. Evidence Paths

| Step | Evidence | Implementation Summary | Verifiers | Auditor |
|---|---|---|---|---|
| P2-013 | `docs/setup-evidence/P2/STEP-P2-013/verification.md` | `docs/setup-evidence/P2/STEP-P2-013/p2-013-implementation-summary.md` | `docs/setup-evidence/P2/STEP-P2-013/verifiers/` | `audit-reports/P2/STEP-P2-013/step-p2-013-auditor-report.md` |
| P2-014 | `docs/setup-evidence/P2/STEP-P2-014/verification.md` | `docs/setup-evidence/P2/STEP-P2-014/p2-014-implementation-summary.md` | `docs/setup-evidence/P2/STEP-P2-014/verifiers/` | `audit-reports/P2/STEP-P2-014/step-p2-014-auditor-report.md` |
| P2-015 | `docs/setup-evidence/P2/STEP-P2-015/verification.md` | `docs/setup-evidence/P2/STEP-P2-015/p2-015-implementation-summary.md` | `docs/setup-evidence/P2/STEP-P2-015/verifiers/` | `audit-reports/P2/STEP-P2-015/step-p2-015-auditor-report.md` |
| P2-016 | `docs/setup-evidence/P2/STEP-P2-016/verification.md` | `docs/setup-evidence/P2/STEP-P2-016/p2-016-implementation-summary.md` | `docs/setup-evidence/P2/STEP-P2-016/verifiers/` | `audit-reports/P2/STEP-P2-016/step-p2-016-auditor-report.md` |
| Safety AC | `evidence/persona-safety/safe-word-runtime-2026-06-01.md` | P2-015 summary references it | P2-015 safety verifier | P2-015 safety auditor |

---

## 17. Rollback / Re-run Safety

| Step | Rollback | Re-run Safety |
|---|---|---|
| P2-013 | Remove/revert `cmd_mood.py`, evidence, tests if added | Pure module; deterministic builders safe to rerun |
| P2-014 | Remove/revert `cmd_help.py`, evidence, tests if added | Pure module; reads command registry only |
| P2-015 | Remove/revert `cmd_safeword.py`, tests/evidence; keep P1 handler intact | Handler tests idempotent; safe-mode state in-memory; tests must reset handler state |
| P2-016 | Remove/revert `startup.py`, tests/evidence | Idempotency guard reset in tests; no network calls in deterministic tests |

No destructive DB/Docker/systemd operations are allowed. Runtime Discord sends must not happen unless explicitly part of safe verification and token is handled through existing SOPS wrapper patterns; this batch is expected to be mostly local deterministic modules until P2-017 bot wiring.

---

## 18. Tracker Sync Plan

After each step auditor PASS, parent may update:

- `PROGRESS.md`: mark step complete and increment counts.
- `CHECKLIST.md`: mark corresponding acceptance item complete.
- `stepprompts/StepPrompts.md`: replace stale snippets/status for the completed step only; do not rewrite future steps unnecessarily.

If batching tracker sync at the end, ensure no final report claims step completion before all per-step auditors pass.

Expected final count after P2-013 through P2-016 all PASS: P2 becomes **16/21** and total becomes **66/257**.

---

## 19. Blockers and Caveats

| Item | Status | Handling |
|---|---|---|
| No `src/discord/bot.py` until P2-017 | Known gap | Implement callback/listener modules with clean interfaces; do not fake runtime wiring. |
| P2-015 text detection needs runtime message listener | Known integration boundary | Expose `handle_safeword_message()` for P2-017 wiring and test it with fake message objects. |
| P2-016 startup cannot truly send until bot runtime exists | Known integration boundary | Implement `on_ready(client)` with fake-client tests; runtime send verification deferred to P2-017 unless a safe harness exists. |
| StepPrompts stale snippets | Known doc debt | Clean per completed step after auditor PASS. |
| `hard_stop_handler.py` uses `Any` in existing return type | Pre-existing P1 code | Do not add new avoidable `Any`; optionally wrap decisions in local typed adapter. |
| DiscordUXSpec vs user DoD for P2-016 channel/presence | Resolved | Current-session user DoD chosen for P2-016; document in evidence. |

---

## 20. Go Checklist

- [x] AGENTS.md read before substantive work.
- [x] Required project state/docs/persona safety docs read.
- [x] Research wave completed with file-based reports.
- [x] Parent read all research reports.
- [x] Planner file exists at `docs/setup-evidence/P2/batch-plan-013-016.md`.
- [ ] Parent reads planner file fully.
- [ ] Active todos rewritten to match planner.
- [ ] Implementation begins sequentially with P2-013 only.

---

## 21. Footer

This plan is a binding gate for P2-013 through P2-016. It preserves HARD STOP safety, Discord token secrecy, Aizanta isolation, one-sub-agent-one-step implementation, delegated verifier reports, and per-step auditor PASS before proceeding.
