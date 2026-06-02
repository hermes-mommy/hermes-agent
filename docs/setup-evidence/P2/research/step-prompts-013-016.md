# STEP-P2-013 through STEP-P2-016 Requirement Research Report

**Date:** 2026-06-01
**Scope:** STEP-P2-013 `/mood`, STEP-P2-014 `/help`, STEP-P2-015 `/safeword` + HARD STOP detection, STEP-P2-016 startup message + presence
**Status:** Complete parent-authored replacement for failed `bg_d2aa94b9` step-spec agent
**Reason:** Background explore task failed with backend buffer overflow after parent had already read the canonical requirements directly.

---

## 1. Sources Read

| Source | Path | Relevant Findings |
|---|---|---|
| Operating contract | `AGENTS.md` | Context-first, file-based evidence, planner gate, one implementation agent per step, parent verification, independent auditor PASS before completion, no secrets/type suppression/empty catches/skipped tests/destructive ops. |
| Progress tracker | `PROGRESS.md` | P0/P1 complete. P2 was 12/21 complete before this batch. P2-013 through P2-016 listed pending in tracker, though later local-structure research found P2-013 already implemented with evidence. |
| Step prompts | `stepprompts/StepPrompts.md` lines ~5100-5690 | P1-021 HARD STOP gate complete; P2 goal: Discord bot online, 33 slash commands, embed formatting. P2-013 `/mood`; P2-014 `/help`; P2-015 `/safeword` + HARD STOP; P2-016 startup message. Snippets are partly stale and must not override current code/UX/safety specs. |
| Implementation guide | `docs/IMPLEMENTATION_GUIDE.md` | Use evidence format, preflight, verify, SOPS wrapper for Discord token. Never touch Aizanta; canonical isolation and ports; no plaintext secrets. |
| Governance ADR index | `docs/10-governance/17-ADR_Index_v1.0.md` | Global Safe Word Principle: safe word is global autonomy override; pauses persona/punishment/autonomous pressure/surveillance confrontation; neutral/supportive mode; governed by ADR-002. |
| Persona safety | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | Safe word must be globally honored, broad semantic detection, neutral mode, no punishment, no auto-resume, no surveillance argument, Y0 during safe/distress/crisis, Y6 prohibited. |
| System prompt | `docs/60-persona/61-SystemPromptMaster_v1.1.md` | Detect HARD STOP/equivalents; immediately drop persona to neutral supportive; stop punishment/yandere/surveillance confrontation; no resume until explicit. |
| MCP config guide | `docs/60-persona/62-MCPConfigGuide_v1.0.md` | SOPS/age secret discipline, file evidence discipline, no plaintext secrets. |
| Discord UX spec | `docs/60-persona/63-DiscordUXSpec_v1.0.md` | Presence `Watching Darling 👁️`; `/mood` embed details; `/help` categorized 33 commands; `/safeword` slash/text triggers, green safe-mode embed, audit-log, ❤️ reaction. |
| Checklist | `CHECKLIST.md` lines ~230-289 | P2-013..016 checklist items pending in checklist; safeword/HARD STOP neutral trigger AC-DISCORD-005; startup sends “Mommy sudah bangun, Darling.” in `#guinevere-status`. |
| Channel IDs | `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml` | `guinevere-status` ID 1510914604291588237, `guinevere-chat` ID 1510914600777023659, `audit-log` ID 1510914647602106408. Source code should prefer runtime name lookup over hardcoded IDs. |

---

## 2. Global Batch Requirements

1. Research wave must finish before planner gate.
2. Planner must exist at `docs/setup-evidence/P2/batch-plan-013-016.md` and include dependency map, parallelism decision, master todos, assignments, collision scan, rollback, and auditor matrix.
3. Parent must read planner before any implementation.
4. Implementation must be sequential unless planner explicitly proves safe independence; user specifically required Step N+1 only after Step N auditor PASS.
5. Each non-trivial implementation step needs one implementation sub-agent for one step only.
6. Each step needs parent verification plus delegated verifier file output, then independent auditor file output, then PASS before completion.
7. Evidence per step must be at `docs/setup-evidence/P2/STEP-P2-XXX/verification.md` using the 12-section evidence schema and containing no Discord token.
8. Token handling must use SOPS wrapper such as `scripts/run-discord-verify.sh`; no plaintext tokens in code, logs, or evidence.
9. Must verify Aizanta health before every step, without touching Aizanta.
10. Canonical ports from user: PostgreSQL 5433, PgBouncer 5434, Redis 6380, 9Router 20128.
11. Resource guard: max 50% CPU/RAM.
12. Minimal diff, match existing patterns, no type-safety suppression, no empty catch, no fake fallback.

---

## 3. STEP-P2-013 Requirement Summary — `/mood`

### 3.1 Canonical DoD

- `/mood` command implemented.
- Correct mood display.
- Persona-flavored response outside safe mode.
- Embed includes mood state, yandere level, streak, last reward, last punishment / last transition as required by StepPrompts/checklist.
- Follows existing Discord protocol/dataclass/dynamic-import pattern.
- LSP clean and relevant tests pass.
- Evidence clean, trackers synced, auditor PASS.

### 3.2 Current State

Local-structure research found this step is already implemented:

- Source: `src/discord/cmd_mood.py`.
- Tests: `tests/discord/test_cmd_mood.py` with 27 tests.
- Evidence: `docs/setup-evidence/P2/STEP-P2-013/verification.md`.
- Status: treat as done only after parent verifies tests/evidence/auditor state and tracker sync; do not re-implement blindly.

### 3.3 Blockers / Risks

- `PROGRESS.md` and `CHECKLIST.md` may still mark this pending, so tracker sync may be stale.
- Planner must reconcile current code/evidence with tracker state.

---

## 4. STEP-P2-014 Requirement Summary — `/help`

### 4.1 Canonical DoD

- Implement `/help` command.
- List all 33 canonical commands.
- Correct category format per DiscordUXSpec.
- Prefer ephemeral output because help is personal/reference UX and avoids channel clutter.
- Respect embed limits: 25 fields max per embed and 6000 total embed characters per message.
- Use canonical registry from `src/discord/commands.py`; do not duplicate hand-written command lists unless tests prove parity.
- LSP clean, relevant tests pass, evidence clean, trackers synced, auditor PASS.

### 4.2 Canonical Command Categories

From DiscordUXSpec and `commands.py`:

| Category | Commands | Count |
|---|---|---:|
| Core | `/status`, `/mood`, `/help`, `/safeword` | 4 |
| Loop | `/loop-start`, `/loop-stop`, `/loop-pause`, `/loop-resume`, `/loops`, `/evidence`, `/loop-priority` | 7 |
| Memory | `/memory-search`, `/memory-add`, `/memory-forget`, `/memory-export` | 4 |
| Surveillance | `/surveillance-status`, `/surveillance-pause`, `/surveillance-resume` | 3 |
| Finance | `/cost`, `/budget`, `/cost-alert` | 3 |
| System | `/approve`, `/deny`, `/approve-all`, `/focus`, `/casual`, `/consent`, `/punishment`, `/reward` | 8 |
| Admin | `/restart-service`, `/backup-now`, `/health-check`, `/clear-cache` | 4 |
| **Total** |  | **33** |

### 4.3 Risks

- DiscordUXSpec header says 34 commands, but enumeration, StepPrompts, checklist, and user Done Criteria say 33. Treat 33 as binding.
- Field limit means 33 command fields cannot fit in one embed if each command is its own field. Use category fields or pagination/view pattern.

---

## 5. STEP-P2-015 Requirement Summary — `/safeword` + HARD STOP Text Detection

### 5.1 Safety Classification

P2-015 is safety-critical and touches persona, consent, safe-word, HARD STOP, yandere boundary, punishment pause, surveillance confrontation pause, and AC-SAFE-001. It requires heightened safety verification and safety auditor PASS.

### 5.2 Canonical DoD

- Implement `/safeword` slash command.
- Implement text detection for `HARD STOP` and semantic equivalents.
- Integrate with existing P1-021 `src/core/services/hard_stop_handler.py`; do not create a parallel safe-mode global.
- Trigger neutral/supportive mode.
- No punishment, no judgment, no yandere escalation, no surveillance confrontation, no roleplay continuation.
- Preserve AC-SAFE-001.
- `/safeword` and text HARD STOP use same global path.
- Respond with DiscordUXSpec safe-mode embed where compatible with PersonaSafetyPolicy.
- Add minimal non-punitive audit-log event and ❤️ reaction to triggering text message if possible.
- No auto-resume; recovery only on explicit recovery phrase.
- LSP clean, relevant tests pass, safety evidence clean, trackers synced, safety auditor PASS.

### 5.3 Binding Safety Sources

- PersonaSafetyPolicy: safe word global hard stop, broad semantic detection, immediate neutral/supportive mode, no punishment, no auto-resume.
- ADR Index / ADR-002: safe word is global architectural override.
- ConsentRevocationPolicy: safe word is hardest consent revocation signal.
- Acceptance criteria: AC-SAFE-001 100% safe-word success; AC-DISCORD-005 Discord safe word path.

### 5.4 Known P1-021 Dependency

`hard_stop_handler.py` already provides:

- `HardStopHandler`.
- `SafetyState.NORMAL` / `SafetyState.SAFE`.
- Exact triggers including `hard stop`, `hardstop`, `safe word`, `safeword`, `hentikan`, `berhenti`.
- Semantic regex patterns including stop/pause/enough/too much persona/mode, neutral/serious/safe mode, break/jeda/capek/udah dulu, switch/go to neutral/safe, Indonesian persona-off equivalents.
- Recovery triggers including `resume`, `aku sudah okay`, `lanjut persona`, `safe mode selesai`, `lanjut`, `continue`.
- `get_guard_decision(message)` API.

### 5.5 Risks / Blockers

- StepPrompts sample code is unsafe because it uses a separate `_safe_mode_active` state. Do not use that sample as implementation authority.
- DiscordUXSpec safe-mode description contains “Mommy”, while PersonaSafetyPolicy strict neutral mode discourages persona terms. Planner/auditor must decide whether to preserve UXSpec text or use stricter neutral wording.
- Bot wiring file does not exist until P2-017, so P2-015 must expose clean functions for future wiring.

---

## 6. STEP-P2-016 Requirement Summary — Startup Message + Presence

### 6.1 Canonical DoD

- Implement startup/on-ready helper.
- On bot ready, send startup message to `#guinevere-status`.
- Startup title/text includes `👑 Mommy sudah bangun, Darling.`.
- Set presence/activity to `Watching Darling 👁️`.
- Use correct channel by name/runtime lookup; no source hardcoded IDs unless only in evidence/test fixtures.
- Gracefully handle missing channel or Discord send failures with structured logging, not silent swallow.
- LSP clean, relevant tests pass, evidence clean, trackers synced, auditor PASS.

### 6.2 Source Details

- DiscordUXSpec §1.2: Default Activity is `Watching Darling 👁️`.
- StepPrompts P2-016: startup embed title `👑 Mommy sudah bangun, Darling.`, description “Semua sistem online. Mommy siap nemenin kamu hari ini.”, color `Colors.PERSONA`, fields Status/Mood.
- StepPrompts P2-017 sample shows `await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Darling 👁️"))`; this renders as `Watching Darling 👁️` in Discord.
- Channel source: `guinevere-status` channel from P2-006.

### 6.3 Risks

- No `bot.py` until P2-017. P2-016 should expose `on_ready(client)` or equivalent helper for future wiring, with Protocol-based tests.
- Reconnect storms can spam startup channel. Consider idempotence/throttle if current step scope allows; if not, document caveat.

---

## 7. Planner Inputs

### 7.1 Dependency Map

1. P2-013 depends on P2-010 registry, P2-011 colors, P2-012 status pattern. Current code indicates done.
2. P2-014 depends on P2-010 registry and existing embed/protocol patterns.
3. P2-015 depends on P1-021 `hard_stop_handler.py`, P2-010 registry, P2-011 colors, DiscordUXSpec, PersonaSafetyPolicy, ConsentRevocationPolicy, and AC-SAFE-001.
4. P2-016 depends on P2-006 channel setup, P2-011 colors, P2-003 intents/presence capability, future P2-017 bot wiring.

### 7.2 Collision Scan Inputs

Potential shared writers:

- `src/discord/commands.py`: should remain read-only unless absolutely needed because 33-command registry already exists.
- `src/discord/colors.py`: should remain read-only unless a required color is missing; required colors appear present.
- Trackers `PROGRESS.md` and `CHECKLIST.md`: parent-only or one owner, updated after evidence/auditor PASS.
- Evidence index/step evidence directories: parent or single owner per step.
- Safety docs/ADRs: do not edit for implementation unless explicitly required; P2-015 should preserve existing policy.

### 7.3 Recommended Sequential Plan

- Verify P2-013 current implementation/evidence/auditor status; if fully PASS, mark done and sync trackers. If missing auditor, run verifier/auditor only, not reimplementation.
- Implement P2-014, then verify/evidence/auditor PASS.
- Implement P2-015, then safety verification/evidence/safety auditor PASS.
- Implement P2-016, then verify/evidence/auditor PASS.

---

## 8. Evidence Expectations

Each step evidence file should include:

1. What Was Done.
2. Files Changed.
3. Validation Results.
4. Evidence Artifacts.
5. Doc-Sync Impact.
6. Boundary Compliance.
7. Rollback/Re-run Safety.
8. Design Decisions/Caveats.
9. Auditor Gate.
10. Security Scan.
11. Acceptance Criteria Mapping.
12. Footer.

P2-015 additionally needs AC-SAFE-001/AC-DISCORD-005 mapping and proof of no persona drift, no consent violation, no surveillance overreach, no Y6, no HARD STOP bypass, no distress suppression, no secret/intimate data exposure.

---

## 9. Conclusion

The direct parent reads recovered the full step-spec context despite the failed background agent. The binding path is to treat `StepPrompts.md` as requirement intent but not literal code authority, because current source patterns and safety reports supersede its stale snippets. Planner may proceed once it reads this report plus the other research reports and reconciles P2-013’s already-done state with tracker status.
