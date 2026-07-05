# P2 Implementation Audit Plan

**Auditor:** Implementation audit subagent (read-only)
**Date:** 2026-06-25
**Status:** PLAN -- awaiting execution
**Research inputs:**
- `docs/setup-evidence/legacy-audit/P2/research/p2-repo-evidence-inventory.md`
- `docs/setup-evidence/legacy-audit/P2/research/p2-runtime-readiness-readonly.md`
- `docs/setup-evidence/legacy-audit/P2/research/p2-discord-current-ownership-map.md`
- `docs/setup-evidence/legacy-audit/P2/research/p2-downstream-impact-p19-p24.md`

---

## 1. Audit Scope and Boundaries

### In Scope

1. **All `src/discord/` Python modules** (~59 files incl. 49 cmd_*.py modules, entrypoint, helpers, listeners, loops). Verify that code matches documented P2 behavior (slash commands, intents, startup, HARD STOP, SEV notifications, Gotify fallback, auth guard, embed colors, shadow monitor/pipeline, Hermes conversational handler).
2. **All `src/life_kernel/` Discord-touching files** (discord_rest_client.py, dashboard_writer.py, log_channel.py, discord_adapter.py, dashboard.py, etc.). Verify REST publisher correctness and document its ownership boundary relative to P2 gateway bot.
3. **All three guinevere-discord.service copies** (`systemd/`, `deploy/discord/`, vps-mirror). Reconcile conflicting ExecStart, token-source, security-hardening, and SOPS-decrypt patterns. Determine which (if any) is the canonical source of truth.
4. **Both hermes-gateway.service copies** (`systemd/`, `scripts/`) plus the live VPS mirror. Verify config-path consistency, environment-file references, and ExecStart signature agreement.
5. **Secrets inventory** (`secrets/discord-secrets.enc.yaml`, `.sops.yaml`). Verify encryption existence and SOPS rule coverage for Discord secrets WITHOUT decrypting.
6. **All P2 evidence directories** (`docs/setup-evidence/P2/STEP-P2-001` through `P2-021`). Cross-check each verification file against the live code to detect stale claims.
7. **Old audit files** (`docs/audit/P2-AUDIT-COMPLETE.md`, `docs/audit/P2-FIX-PLAN.md`). Re-verify every finding against current repo state.
8. **CHECKLIST.md and PROGRESS.md P2 sections.** Audit for numerical accuracy (command counts, channel counts, step counts) against actual code inventory.
9. **ADR-022, ADR-035, and other Discord-referencing ADRs.** Verify ADR claims (especially ADR-035 "Hermes handles Discord now") against actual active code pathways.
10. **Test files** (`tests/discord/`, `tests/life_kernel/`). Assess test coverage breadth, flag missing test areas for critical modules (HARD STOP, auth guard, entrypoint wiring).
11. **Downstream phase coordination.** Map P2 code that P19 (namespace routing), P21 (voice), P22 (semantic classification), P23 (action runtime), and P24 (Hermes fork) must touch, modify, or replace.

### Out of Scope (Explicitly Excluded)

1. **Editing, creating, or deleting any file** except the audit output report. READ-ONLY mandate.
2. **Decrypting secrets or printing any token/API-key value.** Path and existence checks only.
3. **Running `systemctl`, `journalctl`, `docker compose`, `pytest`, `alembic upgrade`, `pip install`, or any state-mutating command.**
4. **Posting, editing, or deleting any Discord message, guild, channel, or permission.**
5. **SSH into the VPS.** Assessment is repo-only; VPS runtime claims are tagged NEEDS-RUNTIME-VERIFICATION.
6. **Recommending specific fixes or writing code patches.** Findings describe the gap; the fix is the responsibility of the implementation phase(s) that follow.
7. **Reviewing non-Discord phases (P0, P1, P3-P18) except where they touch P2 code boundaries** (e.g., P14 health report cmd_health_report.py is in scope because it lives in `src/discord/`).
8. **Deep audit of tests themselves** (assess coverage breadth only, not test correctness).
9. **Reviewing the core kernel loop or life_kernel modules not related to Discord output** (heartbeat, graph, state, hermes_brain -- only their Discord-visible aspects are in scope).

---

## 2. Round 1: Six Audit Dimensions

### Dimension D1: Command Surface Integrity

**What it verifies:** Every P2 slash command exists as a registered `tree.command()` in `_entrypoint.py:setup_hook`, has a corresponding `cmd_*.py` module with a valid callback, and is declared in `_command_registry.py:COMMAND_SPECS`. The `require_canonical_registry()` assertion passes. No dangling or phantom commands.

**Modules inspected:**
- `src/discord/_entrypoint.py` (lines ~248-512: all `tree.command()` registrations, lines ~515-543: `core_names` tuple)
- `src/discord/_command_registry.py` (COMMAND_SPECS tuple, `require_canonical_registry()`)
- All `src/discord/cmd_*.py` files (verify each exports a valid `setup()` or `register()` function)

**Acceptance criteria:**
- A1: `len(core_names) == len(COMMAND_SPECS)` AND `require_canonical_registry()` passes.
- A2: Every name in `core_names` has a corresponding `cmd_<name>.py` file that exists and is importable.
- A3: Every `cmd_*.py` exports a callback registered in `setup_hook`.
- A4: No callback is registered more than once.
- A5: Documented command count (PROGRESS.md, CHECKLIST.md) matches actual count within tolerance (allowed discrepancy: 0 for new phases adding commands; any discrepancy carries a finding).

**Expected finding:** Command count mismatch documented (code=49, PROGRESS.md=35, CHECKLIST.md=33). This is CONFIRMED by research and will carry a finding.

---

### Dimension D2: Service Unit and Deployment Integrity

**What it verifies:** Every `guinevere-discord.service` and `hermes-gateway.service` copy is valid systemd syntax, ExecStart points to an existent Python entrypoint or binary, EnvironmentFile paths reference files that exist in the repo (or are flagged as VPS-only), and token handling is documented (SOPS vs plaintext).

**Files inspected:**
- `systemd/guinevere-discord.service`
- `deploy/discord/guinevere-discord.service`
- `systemd/hermes-gateway.service`
- `scripts/hermes-gateway.service`
- `vps-mirror/systemd-live/hermes-gateway.service`
- `vps-mirror/systemd-live/` (all units -- check for discord unit presence)
- `secrets/discord-secrets.enc.yaml` (existence and SOPS encryption, no decryption)
- `secrets/.env.discord.sops` (existence/lack thereof)
- `.sops.yaml` (path_regex coverage)

**Acceptance criteria:**
- A1: At least one service unit for the Discord gateway exists with a valid, functional ExecStart.
- A2: Every EnvironmentFile referenced in any unit has a corresponding file in the repo OR is explicitly noted as VPS-only.
- A3: SOPS-encrypted secret exists for the bot token (`secrets/discord-secrets.enc.yaml`).
- A4: Token handling is documented for each unit (plaintext or SOPS).
- A5: No unit references a non-existent config directory (like `config/hermes/` which doesn't exist).
- A6: The `vps-mirror/systemd-live/` contents are cataloged and compared against the template units for drift.

**Expected findings:**
- `deploy/discord/guinevere-discord.service` references `secrets/.env.discord.sops` which does NOT exist in repo. NEEDS-RUNTIME-VERIFICATION if it exists on VPS.
- `systemd/hermes-gateway.service` references non-existent `config/hermes/` directory. CONFIRMED.
- `vps-mirror/systemd-live/` lacks any `guinevere-discord.service` -- consistent with masked status.

---

### Dimension D3: Security Posture

**What it verifies:** Bot token is never leaked in logs, error messages, or plaintext files committed to the repo. Authentication model is correct (`is_faiz_interaction` by guild owner). Intents are set appropriately. Permissions required by the bot (Administrator scope) are documented and justified. SOPS encryption files exist and are structurally valid. No secret VALUES are hardcoded in Python code.

**Files inspected:**
- `src/discord/_auth_guard.py` -- auth model correctness
- `src/life_kernel/discord_rest_client.py` -- token handling in REST calls (verify no token logging)
- `src/discord/_intents.py` -- intents configuration
- `src/discord/gotify_fallback.py` -- hardcoded URLs, no tokens
- `secrets/discord-secrets.enc.yaml` -- SOPS structure check (age key stanza, encrypted content)
- `secrets/` directory -- list of all secret files, verify `.gitignore` coverage
- `.sops.yaml` -- path_regex patterns cover Discord secret paths
- `docs/setup-evidence/P2/STEP-P2-009/verification.md` -- Administrator permission justification

**Acceptance criteria:**
- A1: No bot token or secret value appears in plaintext in any committed Python file, YAML config, or markdown doc.
- A2: `discord_rest_client.py` never logs the token value. Confirmed by static analysis of exception handling and `_extract_error_code`.
- A3: Auth guard is at least binary Faiz/non-Faiz for all command callbacks (or more granular).
- A4: Bot intents include `message_content=True` for message-reading commands.
- A5: The Administrator permission scope (from P2-009) is documented with a justification or risk note. If it is unjustified, that is flagged.
- A6: SOPS-encrypted file is structurally valid (age key stanza present, AES256_GCM ciphertext).

**Expected findings:**
- Administrator permission scope (P2-009) noted as unjustified in old audit -- verify if still the case.
- Token is stored in plaintext in `systemd/guinevere-discord.service`'s `EnvironmentFile=.env.discord` reference (though `.env.discord` is not committed to repo).
- Three plaintext token env files across writers: `.env.discord`, `.env.hermes`, `.hermes/.env` (all VPS-only, not committed).

---

### Dimension D4: Notification and Alert Routing

**What it verifies:** SEV0-SEV4 notification routing matches the documented matrix. Each SEV level maps to a valid, existing Discord channel. The Gotify fallback works (URL is correct, client code is syntactically valid). The bare `import discord` issue in `notifications.py` is assessed for impact.

**Files inspected:**
- `src/discord/notifications.py` -- SEV routing, lazy-import design, bare `import discord` at line 240
- `src/discord/gotify_fallback.py` -- Gotify URL, request construction, error handling
- `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml` -- channel name-to-ID mapping
- `docs/setup-evidence/P2/STEP-P2-019/verification.md` -- notification routing test evidence
- `docs/setup-evidence/P2/STEP-P2-020/` -- Gotify Docker compose + verification
- `docs/setup-evidence/P2/STEP-P2-021/` -- Gotify fallback verification
- `docs/setup-evidence/hermes-migration/phase-2-discord.md` -- migration doc for channel name drift check

**Acceptance criteria:**
- A1: SEV0/1 -> system-health, SEV2 -> cost-tracker, SEV3 -> guinevere-status, SEV4 -> audit-log are all confirmed in `notifications.py` constants.
- A2: Each destination channel exists in `channel-ids.yaml`.
- A3: Gotify URL (`http://localhost:8081`) matches Docker-compose port mapping (`127.0.0.1:8081:80`).
- A4: `gotify_fallback.py` has no syntax errors (verified via static parse).
- A5: The bare `import discord` at line 240 of `notifications.py` is flagged. Its impact is assessed (dead import vs runtime crash risk).

**Expected findings:**
- Bare `import discord` at `notifications.py:240` -- CONFIRMED. Dead import, last line of file, contradicts lazy-import design.
- Migration doc `phase-2-discord.md` references non-existent `guinevere-alerts` channel -- CONFIRMED drift (code routes to `system-health`).
- Gotify port 8081 is consistent between code and Docker compose. Old audit note of port 8080 is stale. CONFIRMED resolved.

---

### Dimension D5: HARD STOP and Safety Systems

**What it verifies:** HARD STOP detection is wired correctly for both slash command (`/safeword`) and on_message text detection. The handler (`handle_safeword_message_async`) is imported and called by `_entrypoint.py`. The `HardStopHandler` from `src/core/services/hard_stop_handler.py` is correctly invoked. Shadow monitor and shadow pipeline are active for safety surveillance.

**Files inspected:**
- `src/discord/_entrypoint.py` (lines ~132-160: `_register_hard_stop_listener`, `_on_message_listener`)
- `src/discord/cmd_safeword.py` (docstring at ~598, `handle_safeword_message_async`, `handle_safeword_message` sync)
- `src/discord/shadow_monitor.py`
- `src/discord/shadow_pipeline.py`
- `src/core/services/hard_stop_handler.py` (import verification)
- `docs/setup-evidence/P2/STEP-P2-015/` -- safeword verification + safety verifier
- `docs/setup-evidence/P20/hard-stop-discord-evidence.md` -- P20 runtime evidence of HARD STOP Discord visibility

**Acceptance criteria:**
- A1: `_entrypoint.py` registers an `on_message` listener that calls `handle_safeword_message_async`.
- A2: `handle_safeword_message_async` exists in `cmd_safeword.py`, is async, and accepts a `discord.Message`.
- A3: `HardStopHandler` is imported in `cmd_safeword.py` and methods are called correctly.
- A4: Shadow monitor and shadow pipeline modules exist, are imported, and are wired into `_entrypoint.py` or listeners.
- A5: The stale docstring in `cmd_safeword.py` (~line 598) claiming "no bot.py listener exists yet" is flagged.

**Expected findings:**
- HARD STOP text detection IS wired (contradicting the seed fact that claimed it was unwired). The seed fact was OUTDATED.
- `cmd_safeword.py` docstring (~line 598) is stale -- says listener doesn't exist when it does. COSMETIC finding.
- Shadow monitor and pipeline exist but their active wiring to entrypoint must be confirmed.

---

### Dimension D6: Evidentiary Claims vs. Code Reality

**What it verifies:** Every claim in `docs/setup-evidence/P2/STEP-P2-*` verification files, `CHECKLIST.md`, `PROGRESS.md`, and old audit files is cross-referenced against the actual code. Stale claims, outdated counts, and phantom features are flagged.

**Files inspected:**
- All 21 P2 verification files (`STEP-P2-001` through `P2-021`)
- All batch plans and final reports
- `CHECKLIST.md` lines ~241-306
- `PROGRESS.md` lines ~134-158
- `docs/audit/P2-AUDIT-COMPLETE.md` -- every finding re-verified
- `docs/audit/P2-FIX-PLAN.md` -- each phase status checked

**Acceptance criteria:**
- A1: Every P2 step claim (e.g., "35 slash commands registered", "13 channels created") is confirmed against current code state or flagged as stale.
- A2: Every old audit finding is re-verified with current-state evidence.
- A3: P2-FIX-PLAN phases are checked for completion (Phase 1 SOPS: done; Phase 2 doc fix: partial; Phase 3 ghost cleanup: not done; Phase 4 automation: not done).
- A4: Numerical claims (channel counts, command counts, step counts) are reconciled across all documents.
- A5: The channel-ids.yaml is cross-checked against actual channel names referenced in code (notifications.py, P20 evidence, _command_registry.py).

**Expected findings:**
- Command count: 3-way mismatch (code=49, PROGRESS.md=35, CHECKLIST.md=33). CONFIRMED.
- Channel count: 14 listed in channel-ids.yaml vs 13 documented. Plus `#guinevere-logs` (P20) is not in channel-ids.yaml at all. CONFIRMED.
- P2-FIX-PLAN status: Phase 1 DONE (SOPS enc exists), Phase 2 PARTIAL (doc updated to 35 but code now has 49), Phase 3 NOT DONE (ghost channels persist), Phase 4 NOT DONE (no automation evidence).

---

## 3. Round 2: Adversarial Verification

### R2-1: Refute Round-1 Findings

For each HIGH/CRITICAL finding produced in Round 1, the auditor must attempt to refute it:
1. **"notifications.py bare import discord is CRITICAL"** -- Attempt to prove this import is actually harmless. Check whether `notifications.py` is ever imported without discord.py present. Check import chain: who imports notifications.py, in what context, and whether discord.py is guaranteed to be present at that point. If it is always imported from within a discord.py gateway session, the crash risk is theoretical only (still a design smell, but not CRITICAL). If it can be imported by non-Discord code (life_kernel, tests, core services), the risk is real. Document the impact tier after adversarial analysis.
2. **"deploy service references non-existent SOPS file"** -- Attempt to find ANY path, alias, symlink, or VPS-only file that could satisfy the `secrets/.env.discord.sops` reference. Check whether the filename might be generated at deploy time by a script. Search for bash scripts in `deploy/` or `scripts/` that create or symlink this file. If no evidence found, the finding stands as NEEDS-RUNTIME-VERIFICATION (the file may come from an external secret store not in the repo).
3. **"Command count mismatch (49 vs 35 vs 33)"** -- Attempt to argue that the 49 wired commands include transient/test commands that should not be counted. Count only P2-scoped commands vs later phases. Determine if there is a defensible count that reconciles all documents. If a reasonable reconciliation exists (e.g., "35 core P2 commands + 14 post-P2 additions"), downgrade from HIGH to MEDIUM.

### R2-2: Miss Hunt

Search for things the seed facts and research may have missed:
1. **Missing `exit_handlers` in `_entrypoint.py`** -- Does the bot clean up its gateway connection on SIGTERM/SIGINT? Is there a `@bot.event` for `on_disconnect` or `on_resumed`? If the bot is masked, this may not matter, but it should be documented.
2. **Hermes conversational handler wiring** -- Does `_entrypoint.py` actually wire `hermes_conversational.py` into the `on_message` pipeline? Or is it only wired in the archived bot.py.bak.pre-phase2? If it's NOT wired in `_entrypoint.py`, then chat responses are not routed through Hermes at all (the masked active bot still responds to messages? Impossible -- it's masked, so neither wiring matters). Document this as a code-readiness observation.
3. **Gotify fallback error handling** -- Does `gotify_fallback.py` handle HTTP errors, timeouts, and connection refused? If the Gotify service is down, does the fallback log gracefully or throw an unhandled exception? Static analysis of try/except blocks.
4. **Channel topic drift** -- P2-008 verification claims 13/13 persona-flavored topics. Verify that the channel IDs in `channel-ids.yaml` have topics documented in `P2-008/verification.md` and that the topic strings exist.
5. **Missing tests** -- After the 16 test files are inventoried, identify which high-risk modules have NO tests:
   - `_entrypoint.py` (entrypoint wiring, hard stop listener) -- are there tests?
   - `_auth_guard.py` (auth model) -- test coverage?
   - `_command_registry.py` (command spec validation) -- any test?
   - `_embed_utils.py` -- any test?
   - `cmd_safeword.py` -- any test for the hard stop handler?
   - `shadow_monitor.py`, `shadow_pipeline.py` -- any test?
6. **`_startup.py` message formatting** -- Verify the "Mommy sudah bangun, Darling." startup greeting code is correct and handles embed formatting without errors.

---

## 4. Evidence Synthesis Registers

After Round 1 and Round 2, the auditor SHALL produce registers capturing all findings, organized as follows:

### Register A: Finding Register (All Severities)

| Field | Description |
|-------|-------------|
| **ID** | `P2-AUD-<DIMENSION>-<NNN>` where DIMENSION = CMD, DEPLOY, SEC, NOTIF, SAFETY, EVID, ADV |
| **Title** | Short descriptive title |
| **Severity** | CRITICAL / HIGH / MEDIUM / LOW / COSMETIC |
| **File** | Path:line of evidence |
| **Description** | What was found |
| **Impact** | What the consequence is |
| **Verification** | CONFIRMED / UNVERIFIED / NEEDS-RUNTIME |
| **Round** | 1 or 2 |

### Register B: File Integrity Register

| File | Expected State | Actual State | Status |
|------|---------------|-------------|--------|
| ... | ... | ... | MATCH / STALE / MISSING / UNVERIFIED |

For every file in `docs/setup-evidence/P2/`, `docs/audit/P2-*`, and critical deployment files.

### Register C: Numerical Claim Reconciliation

| Claim | Source | Reported Value | Actual Value | Delta |
|-------|--------|---------------|-------------|-------|
| Slash commands | PROGRESS.md:146 | 35 | 49 | +14 |
| Slash commands | CHECKLIST.md:265 | 33 | 49 | +16 |
| Channels | channel-ids.yaml | 14 | 14 (file) / 15 (in use) | +1 |
| Channels | PROGRESS.md:142 | 13 | 14-15 | +1-2 |
| ... | ... | ... | ... | ... |

### Register D: Old Audit Reconciliation

| Old Finding | Old Verdict | Current State | Current Verdict |
|-------------|-------------|---------------|-----------------|
| P2-AUDIT-COMPLETE finding 1 | ... | ... | RESOLVED / STILL OPEN / CHANGED |
| ... | ... | ... | ... |

All 20+ old findings from P2-AUDIT-COMPLETE.md re-verified.

### Register E: Downstream Coordination Register

| Future Phase | P2 File(s) Touched | Coordination Required | Risk Level |
|--------------|-------------------|----------------------|------------|
| P19 (namespace) | notifications.py, channel-ids.yaml, hermes_conversational.py | Add namespace routing layer | MEDIUM |
| P21 (voice) | _entrypoint.py, _intents.py, hermes_conversational.py, _command_registry.py | Wire voice client, sequence with P19 | LOW |
| P22 (raw access) | _auth_guard.py, discord_adapter.py | P2 auth not reusable; P22 needs own classifier | MEDIUM |
| P23 (action) | None directly | Separate pathways | NONE |
| P24 (Hermes fork) | _entrypoint.py, all cmd_*.py, _command_registry.py, _intents.py, _startup.py | Gateway bot superseded; migrate to Hermes plugins | HIGH |

---

## 5. Final Allowed-Status Enum

For each P2 step (P2-001 through P2-021 + P2-022), the auditor SHALL assign exactly one of these statuses:

| Status | Definition |
|--------|-----------|
| **VERIFIED IMPLEMENTED** | Code matches documented claim. Evidence exists. No bugs found. |
| **IMPLEMENTED WITH BUGS** | Code exists for the feature but has one or more functional bugs (not just docs mismatch). |
| **IMPLEMENTED WITH DOC GAPS** | Code exists and works, but documentation (verification files, PROGRESS.md, CHECKLIST.md) does not accurately describe it. |
| **PARTIALLY IMPLEMENTED** | Significant subset of the feature exists, but core components are missing or incomplete. |
| **PARTIALLY SUPERSEDED BY HERMES/P20** | Feature existed in P2 gateway bot but was superseded by Hermes Gateway or core REST publisher (P20). The active implementation is elsewhere. |
| **SUPERSEDED BY LATER PHASE** | Feature was replaced by a later phase's implementation (specify which). |
| **DOCS CLAIM ONLY** | Documentation describes the feature but no corresponding code exists, or code exists but is non-functional/unreachable. |
| **NEEDS RUNTIME VERIFICATION** | Static code analysis cannot confirm runtime behavior. Requires VPS access, systemctl, curl to Discord API, or live test. |

The final report SHALL include a full status table for all 22 P2 steps.

Additionally, for the overall P2 phase, the auditor SHALL assign one of:

| Overall Status | Criteria |
|----------------|----------|
| **PASS** | All dimensions D1-D6 meet acceptance criteria. No CRITICAL/HIGH findings. All MEDIUM findings have documented workarounds. |
| **PASS WITH CONDITIONS** | No CRITICAL findings. HIGH findings exist but are documented and accepted. MEDIUM/LOW findings documented. |
| **FAIL** | One or more CRITICAL findings. OR acceptance criteria for a core dimension (D1, D3, D5) not met. |

---

## 6. Hard-Rejection Criteria

Any of the following findings in Round 1 or Round 2 triggers an automatic FAIL and the audit shall not proceed to overall PASS:

1. **Plaintext bot token committed to the repository** in any file (Python, YAML, JSON, markdown, env, config). If found, the auditor shall report the path, severity=CRITICAL, and stop further audit for that dimension.
2. **No SOPS-encrypted secret exists** for DISCORD_BOT_TOKEN (`secrets/discord-secrets.enc.yaml`). The old P2-AUDIT-COMPLETE.md flagged this as CRITICAL in the 2026-06-08 audit. If it is still missing, the entire P2 phase FAILs regardless of other passes. (Note: research confirms it now EXISTS -- this is a re-verification guard.)
3. **Gateway session collision is actually occurring** (two WebSocket bots with same token). If the standalone bot is NOT masked and Hermes Gateway IS active, they will collide. The auditor must confirm masked status by checking `vps-mirror/systemd-live/` absence of discord unit. (Research confirms no collision.)
4. **HARD STOP on_message listener is NOT wired**, contradicting both the code and seed claims. If `_entrypoint.py` does not register `_on_message_listener` that calls `handle_safeword_message_async`, the HARD STOP safety system is only half-functional (slash command only). (Research confirms it IS wired -- this is a re-verification guard.)
5. **Discord token is logged in plaintext in any runtime code.** If `discord_rest_client.py`, `_entrypoint.py`, `gotify_fallback.py`, or any helper logs the token value in an error message or debug log, this is CRITICAL. (Research confirms it never logs token.)

---

## 7. Reconciliation Requirement: Masked guinevere-discord.service vs ADR-035 / Hermes / Core REST Ownership

### The Problem

The repo contains a large, active `src/discord/` codebase (59+ files, 49 commands, full discord.py gateway bot architecture). Yet:

- **P2-022** explicitly states the service is "intentionally masked."
- **ADR-035** claims "Hermes Gateway handles Discord now -- standalone bot deprecated."
- **P20** uses `src/life_kernel/discord_rest_client.py` (Option-B REST publisher) for dashboard/log output.
- **vps-mirror/systemd-live/** contains NO `guinevere-discord.service` and DOES contain `hermes-gateway.service`.

This creates an apparent contradiction: a large, working gateway bot codebase that is supposedly masked and unused, while a different gateway (Hermes) and a REST publisher handle Discord duty.

### Reconciliation Mandate

The auditor MUST NOT blindly mark this as a FAIL ("service is masked, code is dead, audit fails"). Instead:

1. **Confirm the masked state** by checking `vps-mirror/systemd-live/` for the absence of `guinevere-discord.service`. (Research: CONFIRMED absent.)
2. **Verify P20 evidence of core REST publisher activity**: dashboard message edits, log channel entries, bot-authored content. (Research: CONFIRMED by P20 snapshot evidence: msg `1519135545501028549`, log channel entries `[cycle 196283]`.)
3. **Verify Hermes Gateway presence** in `vps-mirror/systemd-live/`. (Research: CONFIRMED present: `hermes-gateway.service`.)
4. **Assess the cost of keeping the gateway bot code live:** Is `src/discord/` maintained alongside the active Hermes plugins? Are there duplicate command definitions? Is there a drift risk? (Research: 49 commands in `_entrypoint.py` vs 47 Hermes plugins in `src/hermes_plugins/` -- partial overlap at best.)
5. **Assign status per section 5:** The standalone gateway bot gets `PARTIALLY SUPERSEDED BY HERMES/P20`. The core REST publisher gets `VERIFIED IMPLEMENTED` (for dashboard/log). The Hermes Gateway Discord adapter gets `NEEDS RUNTIME VERIFICATION` (its Discord-specific behavior cannot be confirmed from static code alone because Hermes' gateway binary is external.)
6. **Document the design intent:** The `src/discord/` code is preserved as a contingency/reference implementation that can be re-enabled by `systemctl unmount` if Hermes Gateway fails. It is not a dead codebase -- it is a fallback. Assess whether this is explicitly documented anywhere (it is not, based on research -- this may be an implicit assumption).

### Reconciliation Table (Expected)

| Component | Runtime Status | Audit Status | Rationale |
|-----------|---------------|-------------|-----------|
| `src/discord/_entrypoint.py` + 49 commands | Masked (standalone bot) | PARTIALLY SUPERSEDED BY HERMES/P20 | Gateway bot is intentional fallback; Hermes + REST are active writers |
| `src/life_kernel/discord_rest_client.py` | Active (REST publisher) | VERIFIED IMPLEMENTED | Dashboard + log channel active; P20 evidence confirms |
| `src/life_kernel/dashboard_writer.py` | Active | VERIFIED IMPLEMENTED | Edit-in-place dashboard message confirmed |
| `src/life_kernel/log_channel.py` | Active | VERIFIED IMPLEMENTED | Append-only log confirmed |
| `src/hermes_plugins/` (47 plugins) | Active (Hermes Gateway) | NEEDS RUNTIME VERIFICATION | Plugins present but Hermes gateway binary is external |
| `systemd/guinevere-discord.service` | Masked (P2-022) | PARTIALLY SUPERSEDED | Template unit, not active; references plaintext env |
| `deploy/discord/guinevere-discord.service` | Masked (P2-022) | PARTIALLY SUPERSEDED | Deploy unit, not active; references missing SOPS file |
| `hermes-gateway.service` (any copy) | Active | NEEDS RUNTIME VERIFICATION | Unit present in vps-mirror; Discord adapter in binary |

---

## 8. Report Structure

The final audit report shall contain:

1. **Header** -- Date, auditor, scope, methodology
2. **Overall Verdict** -- PASS / PASS WITH CONDITIONS / FAIL
3. **Status Table** -- All 22 P2 steps with per-step status from section 5
4. **Reconciliation Statement** -- Masked bot reconciliation per section 7
5. **Register A: Finding Register** -- All findings with severity, evidence, impact, verification
6. **Register B: File Integrity Register** -- All files checked against expected state
7. **Register C: Numerical Claim Reconciliation** -- All numerical claim reconciliations
8. **Register D: Old Audit Reconciliation** -- All old findings re-verified
9. **Register E: Downstream Coordination Register** -- Future phase impacts
10. **Hard-Rejection Checks** -- Explicit pass/fail for each hard-rejection criterion
11. **Appendix: Files Examined** -- Complete list of all files read during the audit
12. **Appendix: Seed Fact Corrections** -- All seed facts corrected by the audit

---

## 9. Execution Order

1. **Pre-flight** -- Confirm research files are read. Set up output path.
2. **Dimension D1 (Command Surface)** -- Read `_entrypoint.py`, `_command_registry.py`, count commands, cross-check docs.
3. **Dimension D2 (Service Units)** -- Read all service unit files and secrets inventory.
4. **Dimension D3 (Security)** -- Read auth guard, intents, REST client, permissions evidence.
5. **Dimension D4 (Notifications)** -- Read notifications.py, gotify_fallback.py, channel-ids.yaml, SEV evidence.
6. **Dimension D5 (HARD STOP)** -- Read cmd_safeword.py, shadow modules, _entrypoint.py listener wiring.
7. **Dimension D6 (Claims)** -- Read all 21 verification files, batch plans, old audit, reconcile.
8. **Round 2 Adversarial** -- Miss hunt, refute findings, test coverage analysis.
9. **Synthesis** -- Produce registers A through E.
10. **Final Verdict** -- Assign statuses, write report.

---
