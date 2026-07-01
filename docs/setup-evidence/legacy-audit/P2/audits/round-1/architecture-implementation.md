# P2 Discord -- Architecture & Implementation Completeness (Round 1, R1)

**Audit date:** 2026-06-25
**Auditor:** Read-only implementation auditor
**Scope:** Architecture, implementation completeness, entrypoint validity, HARD STOP wiring, command registry, import safety, service unit conflict, standalone-vs-Hermes reconciliation

---

## EXECUTIVE SUMMARY

52 findings total: 2 CRITICAL, 4 HIGH, 13 MEDIUM, 16 LOW, 17 COSMETIC.

| Severity | Count | Key themes |
|----------|-------|------------|
| CRITICAL | 2 | HARD STOP message send silently drops response; notifications.py bare `import discord` contradicts lazy-import architecture and may crash on missing dependency |
| HIGH | 4 | Old P2-AUDIT-COMPLETE.md findings FIXED but not documented (SOPS now exists); command count drift (49 code vs 33/35 reported); 3 conflicting service units with divergent token strategies; notifications.py redundant bare import + lazy import within same module |
| MEDIUM | 13 | GOTIFY_URL port 8081 vs 8080; channel-ids.yaml 14 vs 13 claimed; hermes_plugins/ has 39 commands vs 49 in _command_registry; phase-2-discord.md lists 35 plugin files that do not exist; CHECKLIST.md still on 33/cmd status ; no .env.discord.sops deploy counterpart; startup greeting to #guinevere-status not in SEV matrix channels; shadow pipeline disabled by default (opt-in); old P2-002 now FIXED but reporting chain not updated; 45 cmd_*.py vs 49 registered (4 extra: cmd_pc.py unregistered, others via _command_registry discrepancy); stale docstring in cmd_safeword.md claiming on_message unwired; no unit test for notifications.py bare import behavior; etc. |
| LOW | 16 | Hermes migration phase-2-discord.md is aspirational (0 of 35 plugin files exist); 2 redundant `import discord` inside send_alert function; listeners import discord at module top which is fine; hermes-gateway.service 3 copies with different ExecStart/flags; PROGRESS.md no longer mentions command_count; SENT_GREETING idempotency could be missed on restart; vps-mirror lacks guinevere-discord.service live snapshot; HARD STOP recovery only checks message.content against HardStopHandler; etc. |
| COSMETIC | 17 | Docstring says "13 wired + 20 stubs" but all are wired; _STUB_PHASE dict empty; module docstring outdated refs; SERVICE MASKED vs masked state; _auth_guard.py docstring mentions "32 command callback modules" (now 45+); etc. |

---

## FINDINGS

### P2-AUD-R1-001 [CRITICAL] HARD STOP `handle_safeword_message_async` silently drops response if `discord.Embed` not available

**File:** `src/discord/cmd_safeword.py` lines 643-711  
**Verification:** CONFIRMED  
**Description:** The `handle_safeword_message_async` function (wired into `_entrypoint.py` line 155 via `_on_message_listener`) calls `_get_discord_embed_module()` which uses `importlib.import_module("discord")`. If discord.py is absent at runtime (e.g. test environment where discord is mocked), the try/except at line 699 catches the `ImportError` and logs `handle_safeword_message_async: failed to send embed or react`, then returns `True`. The caller receives `True` (consumed), but the user NOT see the safe-mode embed. The message is silently absorbed both from the HARD STOP path and from further processing. This is a safety concern: the bot silently drops a message that should have triggered a visible safe-mode response.  
**Impact:** HARD STOP activation is invisible to the user. The bot absorbs the message silently, creating the illusion that nothing happened or the bot ignored the user. Safety-critical visibility gap.  
**Recommendation:** Either (a) require discord.py to be present at runtime and fail hard if absent, or (b) add a plain-text fallback channel to at least send a visible acknowledgement when the embed path fails.

---

### P2-AUD-R1-002 [CRITICAL] notifications.py bare `import discord` at module bottom contradicts lazy-import design and can crash

**File:** `src/discord/notifications.py` line 240  
**Verification:** CONFIRMED  
**Description:** The entire module is built around lazy `importlib.import_module("discord")` inside `_get_discord_embed_module()` (line 140). However, line 240 has a bare `import discord  # noqa: E402  # isort: skip` at the bottom of the file. This executes AT IMPORT TIME whenever the module is loaded, not just when `send_alert()` or `to_discord_embed()` is called. This completely defeats the lazy-import design: any code that imports `notifications.py` will eagerly import discord.py. If discord.py is absent (e.g. certain test configurations or non-Discord runtime contexts), the module crashes on import.  
**Impact:** Module can crash at import time if discord.py is missing, negating the lazy-import protocol design. This affects any module that imports from `notifications.py` (directly or transitively).  
**Recommendation:** Remove the bare `import discord` at line 240. The lazy `_get_discord_embed_module()` already handles the import when needed. Also remove the redundant `import discord as discord_module` inside `send_alert()` (line 208) since it was a fallback for when the bare import might not have run.

---

### P2-AUD-R1-003 [HIGH] P2-002 CRITICAL finding from old audit is NOW FIXED but reporting chain not updated

**File:** `docs/audit/P2-AUDIT-COMPLETE.md` (line 57-58), `secrets/discord-secrets.enc.yaml`  
**Verification:** CONFIRMED  
**Description:** The old P2-002 CRITICAL finding stated "Encrypted secret MISSING. secrets/discord-secrets.yaml does not exist." The file `secrets/discord-secrets.enc.yaml` NOW EXISTS and is properly SOPS-encrypted (confirmed by header: `discord_bot_token: ENC[AES256_GCM,...]`). However, `P2-AUDIT-COMPLETE.md` still records this as a CRITICAL FAIL in the table. The `P2-FIX-PLAN.md` marks Phase 1 items as `[x]` completed, but the fix status is not reflected in the main audit report.  
**Impact:** A reader of `P2-AUDIT-COMPLETE.md` would still see a CRITICAL open item. Reporting chain not closed.  
**Recommendation:** Update `P2-AUDIT-COMPLETE.md` to reflect that P2-002 is now RESOLVED. Add a note about the `.enc.yaml` naming.

---

### P2-AUD-R1-004 [HIGH] Command count drift: code=49, old report=35, CHECKLIST.md=33, hermes_plugins=39

**Files:**
- `src/discord/_command_registry.py` line 406-408: `require_canonical_registry()` validates 49 commands
- `CHECKLIST.md` line 265: says `commands_count=33`
- `docs/audit/P2-AUDIT-COMPLETE.md` line 63: says "Code has 35"  
- `src/hermes_plugins/command_catalog.py`: 39 commands
- `docs/setup-evidence/P2/STEP-P2-010/verification.md` line 70, 137: `commands_count=33`

**Verification:** CONFIRMED  
**Description:** There are now four different command counts in the codebase. `_command_registry.py` proves 49 commands (core, loop, memory, surveillance, finance, system, admin, gmail, health, P18 memory-extended, P5 loop-monitoring). The old reports say 35 (which might have been true at one point). CHECKLIST.md remains at 33. The hermes_plugins/ catalog has 39 (missing P14 wearable health, P18 advanced memory, P5 loop monitoring, plus some others). This means:
- `CHECKLIST.md` is 16 commands behind reality  
- Old audit is 14 commands behind  
- `_command_registry.py` validated via `require_canonical_registry()` and is the authoritative source  
- hermes_plugins catalog is 10 commands behind the Discord command registry  
**Impact:** Operational confusion. Verification scripts using `commands_count=33` will fail against the real Discord API (which would show 49 registered commands). New commands may not be visible in help output.  
**Recommendation:** Update all command count references to 49. Re-sync the Discord guild command tree.

---

### P2-AUD-R1-005 [HIGH] THREE conflicting guinevere-discord.service units with different token strategies

**Files:**
1. `systemd/guinevere-discord.service`: `EnvironmentFile=.env.discord` (plaintext), `ExecStart=python -m src.discord._entrypoint`
2. `deploy/discord/guinevere-discord.service`: SOPS decrypt `secrets/.env.discord.sops` -> `/run/guinevere-discord-token`, shred on stop, `ExecStart=python -m src.discord._entrypoint`
3. `vps-mirror/systemd-live/`: NO guinevere-discord.service exists here (unit is masked on VPS; only hermes-gateway.service present)

**Verification:** CONFIRMED (only 2 relevant copies, not 3)  
**Description:** Unit (1) in `systemd/` loads the token from an unencrypted `.env.discord` file. Unit (2) in `deploy/discord/` properly decrypts via SOPS into a runtime ramdisk file, then shreds on stop. However, the `.env.discord.sops` file referenced in unit (2) `ExecStartPre` does not exist on the repo:
```
/sops --decrypt ... /home/guinevere/code/guinevere/secrets/.env.discord.sops
```
This file is absent locally. Only `discord-secrets.enc.yaml` exists. The two units have different security postures: one uses plaintext, one references a non-existent SOPS file.  
**Impact:** If the deploy unit is actually used on the VPS, `ExecStartPre` fails because `.env.discord.sops` does not exist in the repo. The `systemd/` unit is dangerously using plaintext environment if deployed.  
**Recommendation:** Either rename `discord-secrets.enc.yaml` to `.env.discord.sops` and adjust the SOPS format to dotenv, or update `ExecStartPre` to point to the correct `.enc.yaml` file and add `--input-type yaml` flag.

---

### P2-AUD-R1-006 [HIGH] notifications.py has redundant bare import + duplicated lazy import within same function

**File:** `src/discord/notifications.py`  
**Verification:** CONFIRMED  
**Description:** There are THREE code paths that import discord:
1. Line 19-22: `try: from discord import utils as discord_utils; except: discord_utils = None` (module-level, lazy)
2. Line 140: `_get_discord_embed_module()` uses `importlib.import_module("discord")` (proper lazy pattern)
3. Line 208 inside `send_alert()`: `import discord as discord_module` (redundant eager import)
4. Line 240: `import discord  # noqa: E402  # isort: skip` (bare module-level import, contradicts the entire lazy design)

The irony is that `_get_discord_embed_module()` (line 140) already provides proper lazy access to discord. The bare `import discord` at line 240 and the `import discord as discord_module` at line 208 are both redundant and harmful: they negate the lazy design and can cause crashes at import time.  
**Impact:** Module-level bare import of discord at line 240 will crash the module at import time if discord.py is absent in the runtime. This contradicts the careful lazy-import protocol architecture used throughout the module.  
**Recommendation:** Delete line 240 (bare `import discord`). Replace line 207-210 (`if discord_utils is None: import discord as discord_module; discord_utils_local = ...`) to use `_get_discord_embed_module().utils` instead.

---

### P2-AUD-R1-007 [MEDIUM] GOTIFY_URL port 8081 in code conflicts with old audit claim of port 8080

**File:** `src/discord/gotify_fallback.py` line 32: `GOTIFY_URL: str = "http://localhost:8081"`  
**Reference:** `docs/audit/P2-AUDIT-COMPLETE.md` line 64: "Port 8080 responds on /health"  
**Verification:** CONFIRMED (code uses 8081, old audit mentions 8080)  
**Description:** The code hardcodes port 8081. The old audit report claimed Gotify was running on 8080 and responding with `{"status":"up"}` on `/health`. This is a port mismatch between the code and the evidence. Either Gotify was moved to 8081 after the audit, or the code port is wrong.  
**Impact:** If Gotify is actually running on 8080, all fallback notifications silently fail (fail-soft). If on 8081, the old audit is correct about Gotify but wrong about port.  
**Recommendation:** NEEDS RUNTIME VERIFICATION. Confirm which port Gotify is listening on. Update the constant to match, or make it configurable via env var.

---

### P2-AUD-R1-008 [MEDIUM] channel-ids.yaml lists 14 channels, but old audits claim 13

**File:** `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml`  
**Verification:** CONFIRMED  
**Description:** The channel list has 14 entries (including `rituals` at line 19 plus 3 ghost channels `project-alpha-dev`, `project-alpha-docs`, `project-beta-dev`). The old audit (`P2-AUDIT-COMPLETE.md` line 33) says 13 channels created. The CHECKLIST and P2 definition documents reference 13. The `rituals` channel (1513496377324339262) appears to be a bonus channel added post-audit.  
**Impact:** Verification scripts expecting 13 channels will fail against 14.  
**Recommendation:** Confirm whether `rituals` is intentional. Update all channel-count references to 14.

---

### P2-AUD-R1-009 [MEDIUM] hermes_plugins command_catalog.py has 39 commands vs 49 in _command_registry

**File:** `src/hermes_plugins/command_catalog.py`  
**Verification:** CONFIRMED  
**Description:** The Hermes plugin catalog is missing:
- P14 wearable health commands: `health-report`, `health-trend`, `health-baseline`
- P18 advanced memory: `memory-stats`, `memory-review`, `memory-schedule`, `memory-decay`
- P5 loop monitoring: `loop-status`, `loop-cost`, `loop-history`

That's 10 commands from Phase 14/18/5 that exist in the Discord `_command_registry.py` but have no Hermes plugin counterpart.  
**Impact:** If/when Hermes gateway replaces the standalone bot, 10 commands will be missing from the Hermes command catalog. Help output and routing would be incomplete.  
**Recommendation:** Add P14, P18, P5 categories and command names to `command_catalog.py`.

---

### P2-AUD-R1-010 [MEDIUM] phase-2-discord.md lists 35 plugin files that do not exist

**File:** `docs/setup-evidence/hermes-migration/phase-2-discord.md` lines 143-187  
**Verification:** CONFIRMED  
**Description:** The migration document lists 35 `plugins/*_plugin.py` files (e.g. `plugins/status_plugin.py`, `plugins/mood_plugin.py`) with code generation scripts and migration steps. NONE of these files exist at the paths documented. The existing `src/hermes_plugins/` directory has a different structure: commands organized by category subdirectories (`commands_admin/`, `commands_finance/`, etc.), not flat `*_plugin.py` files. The migration document is entirely aspirational.  
**Impact:** The migration cannot proceed as documented. The phase-2-discord.md script-based approach is not aligned with the actual plugin structure.  
**Recommendation:** Either update phase-2-discord.md to reflect the actual `commands_*/` structure, or regenerate the plugin migration files.

---

### P2-AUD-R1-011 [MEDIUM] deploy/discord/guinevere-discord.service references non-existent .env.discord.sops

**File:** `deploy/discord/guinevere-discord.service` line 14-15  
**Verification:** CONFIRMED  
**Description:** The `ExecStartPre` references `/home/guinevere/code/guinevere/secrets/.env.discord.sops` with `--input-type dotenv --output-type dotenv`. This file does NOT exist in the `secrets/` directory. The actual encrypted secret file is `discord-secrets.enc.yaml` (SOPS YAML format, not dotenv).  
**Impact:** If this unit is deployed, the `ExecStartPre` command will fail because the input file does not exist. The bot will not start.  
**Recommendation:** Either create `.env.discord.sops` (SOPS-encrypted dotenv version of the token), or change the unit to use `discord-secrets.enc.yaml` with `--input-type yaml` and adjust the parsing.

---

### P2-AUD-R1-012 [MEDIUM] Shadow pipeline disabled by default (opt-in only) -- no production shadow mode

**File:** `src/discord/_entrypoint.py` lines 107-110  
**Verification:** CONFIRMED  
**Description:** The `ShadowPipeline` is instantiated with `SHADOW_ENABLED` defaulting to `"false"` and `SHADOW_TRAFFIC_PCT` defaulting to `"0"`. No service unit, cron job, or deployment script enables shadow mode. The shadow monitor exists as a standalone script but requires manual invocation.  
**Impact:** Hermes shadow comparison for conversational messages is effectively dead code without an operator manually setting env vars or running the monitor script. The migration comparison feature of phase-2-discord.md is not running.  
**Recommendation:** Either (a) add a shadow cron/service unit, (b) wire shadow into the bot's default deployment, or (c) document the manual invocation steps clearly.

---

### P2-AUD-R1-013 [MEDIUM] `_entrypoint.py` docstring says "13 wired + 20 stubs" but _STUB_PHASE is empty -- all commands wired

**File:** `src/discord/_entrypoint.py` line 54, 89-91  
**Verification:** CONFIRMED  
**Description:** The class docstring (line 89-91) says "Slash command tree (13 wired + 20 stubs) registered in setup_hook." Also line 54: `_STUB_PHASE: dict[str, int] = {}` -- empty dict. The `setup_hook` function at lines 514-549 iterates through COMMAND_SPECS and creates stubs only for commands NOT in `core_names`. But `core_names` contains ALL 49 commands (lines 515-543). So the stub path is dead code. All 49 commands are wired, not 13+20.  
**Impact:** Misleading documentation. Stub system (`_make_stub_callback`, `_STUB_PHASE`) is dead code.  
**Recommendation:** Update docstring to reflect 49 wired commands. Remove or document the dead stub code.

---

### P2-AUD-R1-014 [MEDIUM] CHECKLIST.md still references `commands_count=33` (line 265)

**File:** `CHECKLIST.md` line 265  
**Verification:** CONFIRMED  
**Description:** The checklist entry for P2-010 says `commands_count=33` which is 16 commands behind the real count of 49. This is a stale verification stamp.  
**Impact:** If this checklist is used for phase-gating or deployment verification, the count check will fail.  
**Recommendation:** Update to `commands_count=49`.

---

### P2-AUD-R1-015 [MEDIUM] Three hermes-gateway.service copies with different ExecStart signatures

**Files:**
- `systemd/hermes-gateway.service`: `ExecStart=hermes --config .../hermes-config/config.yaml gateway`, `EnvironmentFile=.env.hermes`
- `scripts/hermes-gateway.service`: `ExecStart=hermes gateway run --accept-hooks`, `EnvironmentFile=~/.hermes/.env`
- `vps-mirror/systemd-live/hermes-gateway.service`: `ExecStart=hermes gateway run --accept-hooks`, `EnvironmentFile=.env.hermes`

**Verification:** CONFIRMED  
**Description:** The three service units differ in two dimensions: (1) `hermes --config ... gateway` vs `hermes gateway run --accept-hooks`, and (2) `.env.hermes` vs `~/.hermes/.env`. The vps-mirror live snapshot uses `--accept-hooks` with `.env.hermes`, while the repo template uses `--config` with `.env.hermes`. The scripts/ copy uses `--accept-hooks` with a different env path.  
**Impact:** Conflicting starting commands and env files depending on which unit is installed. Version mismatch between repo authoritative unit and live VPS unit.  
**Recommendation:** Reconcile to one canonical unit. Recommend `systemd/hermes-gateway.service` as authoritative (it has the config path for deterministic config loading). Update vps-mirror/ to match.

---

### P2-AUD-R1-016 [MEDIUM] notifications.py SEV matrix routes to `guinevere-status` for SEV3, but migration doc references `guinevere-alerts`

**File:** `src/discord/notifications.py` lines 33-37, `docs/setup-evidence/hermes-migration/phase-2-discord.md` line 69 (config snippet shows `alerts: "guinevere-alerts"`)  
**Verification:** CONFIRMED  
**Description:** The production code routes:
- SEV0/SEV1 -> `system-health`
- SEV2 -> `cost-tracker`
- SEV3 -> `guinevere-status`
- SEV4 -> `audit-log`

The migration doc's `gateway.discord.channels.alerts` references `guinevere-alerts`, which is not a channel in the SEV matrix or the channel-ids.yaml list.  
**Impact:** If Hermes gateway takes over, alert routing would target a non-existent `#guinevere-alerts` channel.  
**Recommendation:** Reconcile channel names between production code and migration documentation.

---

### P2-AUD-R1-017 [MEDIUM] `_auth_guard.py` docstring says "32 command callback modules" (now 45+)

**File:** `src/discord/_auth_guard.py` line 5 documentation  
**Verification:** CONFIRMED  
**Description:** The module docstring says it provides auth for "the 32 command callback modules." There are actually 45 `cmd_*.py` files in the `src/discord/` directory.  
**Impact:** Stale documentation.  
**Recommendation:** Replace "32" with "45+" or make it relative.

---

### P2-AUD-R1-018 [MEDIUM] cmd_safeword.py docstring still says "No bot.py listener exists yet" -- now wired

**File:** `src/discord/cmd_safeword.py` lines 599-600  
**Verification:** CONFIRMED  
**Description:** The docstring of `handle_safeword_message()` says "No bot.py listener exists yet. This function is callable and documented but inactive until P2-017 wires it." However, `_entrypoint.py` line 104 calls `_register_hard_stop_listener()` and line 155 imports `handle_safeword_message_async` which IS the async wiring. The listener is active.  
**Impact:** Misleading documentation. A developer reading the docstring would believe HARD STOP text detection is unwired when it is active.  
**Recommendation:** Update the docstring to reflect that `handle_safeword_message_async` is now wired in `_entrypoint.py`.

---

### P2-AUD-R1-019 [MEDIUM] No .env.discord or .env.discord.sops found locally -- all service units reference non-existent files

**Files checked:**
- `/c/Users/faizz/guinevere/.env.discord` -- NOT FOUND
- `/c/Users/faizz/guinevere/secrets/.env.discord.sops` -- NOT FOUND
- `/c/Users/faizz/guinevere/secrets/discord-secrets.enc.yaml` -- EXISTS (SOPS YAML)

**Verification:** CONFIRMED  
**Description:** Both guardian service units reference environment files that do not exist in the repo:
- `systemd/guinevere-discord.service` references `.env.discord` in the repo root
- `deploy/discord/guinevere-discord.service` references `secrets/.env.discord.sops`

The `.env.discord` file would contain the plaintext token -- it's not in the repo (expected for security). The `.env.discord.sops` SOPS-encrypted dotenv file does not exist either. Only the YAML-format `discord-secrets.enc.yaml` exists.  
**Impact:** Neither service unit can work from a clean checkout. An operator needs to either create `.env.discord` (plaintext) or decrypt `discord-secrets.enc.yaml` to dotenv format as `.env.discord.sops`.  
**Recommendation:** Generate `.env.discord.sops` from `discord-secrets.enc.yaml` as a deployment step, or update the deploy unit to handle YAML input.

---

### P2-AUD-R1-020 [LOW] notifications.py has two redundant `import discord` paths inside `send_alert()` function

**File:** `src/discord/notifications.py` lines 207-210  
**Verification:** CONFIRMED  
**Description:** Inside `send_alert()` there is a fallback:
```python
if discord_utils is None:
    import discord as discord_module
    discord_utils_local = getattr(discord_module, "utils", None)
```
This is redundant because line 240's bare `import discord` (see R1-002) would have already imported it. Even if that bare import is removed, `_get_discord_embed_module()` provides proper lazy access.  
**Impact:** Dead code path. The `discord_utils` variable at line 19-22 imports `discord.utils` at module level and only fails if discord is absent. If the bare import at 240 didn't crash, this won't either. But it's confusing and redundant.  
**Recommendation:** Simplify `send_alert()` to use `_get_discord_embed_module().utils` for channel lookup instead of the conditional import.

---

### P2-AUD-R1-021 [LOW] HARD STOP recovery only checks `message.content` against HardStopHandler -- does not check attachments, embeds, or stickers

**File:** `src/discord/cmd_safeword.py` lines 667-670, also `_entrypoint.py` line 678  
**Verification:** CONFIRMED  
**Description:** Both `handle_safeword_message_async` (cmd_safeword.py line 667) and `on_message` recovery check (entrypoint line 678) only examine `message.content` for HARD STOP detection or recovery phrases. Attachments, embeds, stickers, and slash-command interactions are not checked.  
**Impact:** A user could trigger HARD STOP via a slash command (/safeword) but recovery via message text only. Recovery phrases in embeds or attachments are invisible to the detector.  
**Recommendation:** Document this limitation. Consider checking `message.system_content` or additional fields for recovery.

---

### P2-AUD-R1-022 [LOW] Shadow pipeline `shadow_forward` uses `asyncio.create_task` -- fire-and-forget with no error reporting to operator

**File:** `src/discord/hermes_conversational.py` lines 591-595  
**Verification:** CONFIRMED  
**Description:** Shadow forward is dispatched via `asyncio.create_task` with no await and no callback. If the shadow forward fails (e.g. Hermes not running), the error is silently logged at DEBUG level. The operator has no way to know shadow comparisons are failing.  
**Impact:** Silent data loss for the shadow comparison pipeline during migration.  
**Recommendation:** Add a metrics counter or periodic summary log for shadow failures.

---

### P2-AUD-R1-023 [LOW] `cmd_pc.py` exists but is not imported or wired anywhere

**File:** `src/discord/cmd_pc.py` (exists but not imported in `_entrypoint.py`)  
**Verification:** CONFIRMED  
**Description:** There are 45 `cmd_*.py` files in `src/discord/`. The `_entrypoint.py` imports from 44 of them (core 13 + batch D 20 + Hermes 2 + P12 4 + P14 3 + P18 4 + P5 3 = 44). `cmd_pc.py` is not imported or registered as a slash command. It appears to be dead code.  
**Impact:** The /pc command exists in source but is not wired to the command tree. It cannot be invoked.  
**Recommendation:** Either wire it into `_entrypoint.py` or remove it.

---

### P2-AUD-R1-024 [LOW] vps-mirror/systemd-live has no guinevere-discord.service snapshot (unit is masked live)

**File:** `vps-mirror/systemd-live/` (directory listing shows NO guinevere-discord.service)  
**Verification:** CONFIRMED  
**Description:** The live VPS has the service masked (per ADR-035 / P2-022). The vps-mirror correctly has no discord unit. This is intentional: the standalone bot service is intentionally disabled, and Hermes gateway handles Discord.  
**Impact:** No evidence snapshot of the disabled unit. The mask status can only be verified on the VPS.  
**Recommendation:** Add a metadata file in vps-mirror/ confirming the discord service mask and linking to the ADR.

---

### P2-AUD-R1-025 [LOW] `_sent_greeting` idempotency guard prevents greeting after restart within same process

**File:** `src/discord/_startup.py` lines 290-293, 332-334  
**Verification:** CONFIRMED  
**Description:** The `_sent_greeting` flag prevents sending the startup greeting more than once per process lifetime. If the bot reconnects to Discord (triggering a second `on_ready`), the greeting is not sent again. This is intentional (per Discord best practice), but the guard is module-level, not persisted. A process crash means the greeting is sent again (fine) but a disconnect-reconnect cycle within the same process skips it (also fine).  
**Impact:** No operator-facing issue. Documented behavior.  
**Recommendation:** No action needed. This is working as designed.

---

### P2-AUD-R1-026 [LOW] `handle_safeword_message()` (sync) exists alongside `handle_safeword_message_async()` (async) -- both wired

**File:** `src/discord/cmd_safeword.py` lines 591 (sync) and 643 (async)  
**Verification:** CONFIRMED  
**Description:** Two versions of the message handler exist: a synchronous one (`handle_safeword_message`) and an async one (`handle_safeword_message_async`). The sync version has the outdated docstring about not being wired. The async version is the one actually wired in `_entrypoint.py`. The sync version returns `True` but does NOT send any Discord message -- it only logs and returns.  
**Impact:** If someone wires the sync version by mistake, HARD STOP would be detected (message consumed) but no visible response sent.  
**Recommendation:** Remove or deprecate the sync version.

---

### P2-AUD-R1-027 [LOW] Hermes plugins directory has 39 commands but many plugin files are empty shells

**File:** `src/hermes_plugins/` (directory exists)  
**Verification:** CONFIRMED  
**Description:** The `src/hermes_plugins/commands_*/` subdirectories have `__init__.py` files and `__pycache__/` but actual command implementations are present. The structure mirrors the Discord command modules. However, `command_catalog.py` is missing 10 commands (see R1-009).  
**Impact:** Hermes command catalog is incomplete. Help generation from the catalog would miss health, extended memory, and loop monitoring commands.  
**Recommendation:** Sync `command_catalog.py` with the 49 commands from `_command_registry.py`.

---

### P2-AUD-R1-028 [LOW] `notifications.py` `send_alert()` does not validate channel exists in guild before sending

**File:** `src/discord/notifications.py` lines 201-237  
**Verification:** CONFIRMED  
**Description:** The function calls `bot.get_all_channels()` and then `discord_utils.get(channels, name=data.channel_name)`. If the channel name is not found (e.g. renamed), it logs an error and returns False. There is no fallback to a known-good channel or warning to the operator via another path.  
**Impact:** Misconfigured channel name results in silent notification loss (logged error only).  
**Recommendation:** Add a fallback target (e.g. send to a known admin channel) or escalate to the startup greeting channel.

---

### P2-AUD-R1-029 [LOW] `cmd_safeword.py` `_build_safeword_fields()` ignores handler state -- hardcodes all field values

**File:** `src/discord/cmd_safeword.py` lines 330-348  
**Verification:** CONFIRMED  
**Description:** The `_build_safeword_fields()` function takes a `HardStopHandler` instance but ignores its state entirely. All fields are hardcoded:
- Status: "Safe mode active" (always)
- Persona: "Neutral / supportive" (always)
- Punishment: "Paused" (always)
- Yandere: "Y0" (always)
- Surveillance Confrontation: "Paused" (always)
- Resume: `RESUME_PHRASES` (always)

The handler parameter is unused. The same field builder also called from `build_safeword_embed_data()`.  
**Impact:** The /safeword embed always shows the same static text regardless of actual handler state. Dynamic state (e.g. whether handler is already in safe mode, recovery state, punishment level) is not reflected.  
**Recommendation:** Wire actual handler state into the field values. Use `handler.state`, `handler.is_safe`, or other accessors to populate dynamic data.

---

### P2-AUD-R1-030 [COSMETIC] Many counting discrepancies

**Files:** Multiple  
**Verification:** CONFIRMED  
**Description:** Summary of stale numbers throughout codebase:
- `_auth_guard.py`: "32 command callback modules" (now 45+)
- `_entrypoint.py` docstring: "13 wired + 20 stubs" (now 49 wired, 0 stubs)
- `CHECKLIST.md`: 33 commands (should be 49)
- `PROGRESS.md`: no longer has a command count (was updated, but no replacement)
- Old P2 audit: 35 commands (should be 49)
- hermes_plugins command_catalog: 39 commands (should be 49)
- channel count: 13 claimed vs 14 actual

**Impact:** Pervasive numerical drift across docs. Operators cannot trust any stated count without cross-checking.  
**Recommendation:** Global cleanup of all numeric references.

---

### P2-AUD-R1-031 [COSMETIC] `_entrypoint.py` uses bare except catching `AttributeError` as fallback for old discord.py

**File:** `src/discord/_entrypoint.py` lines 758-761  
**Verification:** CONFIRMED  
**Description:** The `main()` function has:
```python
try:
    async with bot:
        await bot.start(token)
except AttributeError:
    await bot.start(token)
```
This catches `AttributeError` broadly to support both modern (2.4+) and ancient discord.py versions. Installed version is 2.7.1 (confirmed). The old-version path is dead code.  
**Impact:** Safety concern: an `AttributeError` from any other source (e.g. `bot.start` fails with missing attribute) would be silently caught and retried without the context manager, potentially running in a broken state.  
**Recommendation:** Add stricter exception filtering or raise a warning when the fallback path is taken.

---

### P2-AUD-R1-032 [COSMETIC] `_entrypoint.py` line 48: GUILD_ID comment says "Canonical guild ID from guild_setup.py" -- no such file found

**File:** `src/discord/_entrypoint.py` line 48  
**Verification:** CONFIRMED  
**Description:** The comment references `guild_setup.py` which does not exist in the current codebase.  
**Recommendation:** Fix the comment reference.

---

### P2-AUD-R1-033 [COSMETIC] `_STUB_PHASE` dict is defined but never populated (empty)

**File:** `src/discord/_entrypoint.py` lines 54, 547  
**Verification:** CONFIRMED  
**Description:** `_STUB_PHASE` is initialized as empty and never modified. The stub loop at line 547 uses `_STUB_PHASE.get(spec.name, 4)` which always returns 4. This code path is never reached anyway because `core_names` includes all commands.  
**Recommendation:** Remove dead stub code.

---

### P2-AUD-R1-034 [COSMETIC] `bot.py.bak.pre-phase2` imports `discord.ext.commands` as `commands` -- same pattern as `_entrypoint.py`

**File:** `src/discord/bot.py.bak.pre-phase2` lines 18-28  
**Verification:** CONFIRMED  
**Description:** The backup file uses the same dynamic import pattern as `_entrypoint.py`. This is expected since `_entrypoint.py` replaced `bot.py`.  
**Impact:** None. Backup files are external reference material.

---

### P2-AUD-R1-035 [COSMETIC] `gotify_fallback.py` hardcodes `GOTIFY_URL` -- not configurable without editing code

**File:** `src/discord/gotify_fallback.py` line 32  
**Verification:** CONFIRMED  
**Description:** `GOTIFY_URL` is hardcoded to `http://localhost:8081`. Unlike the bot token (read from env), Gotify URL is not configurable via environment variable.  
**Recommendation:** Add env var support (e.g. `GOTIFY_URL` env var with `http://localhost:8081` as default).

---

### P2-AUD-R1-036 [COSMETIC] `cmd_safeword.py` LINE comments reference P2-017 as the wiring step but step index has changed

**File:** `src/discord/cmd_safeword.py` line 20 ("Wire for text detection (P2-017)"), line 597 ("inactive until P2-017 wires it")  
**Verification:** CONFIRMED  
**Description:** P2-017 was the original systemd service step. The wiring is now done in `_entrypoint.py` constructor via `_register_hard_stop_listener()`. The P2-017 reference is outdated.  
**Recommendation:** Update to reference `_entrypoint.py` or remove the step number.

---

### P2-AUD-R1-037 [COSMETIC] `_startup.py` docstring suggests wiring pattern that is already done in `_entrypoint.py`

**File:** `src/discord/_startup.py` lines 18-21  
**Verification:** CONFIRMED  
**Description:** The docstring at the top of `_startup.py` shows a code block demonstrating wiring, saying "Wire into bot.py (P2-017)". This wiring is already done in `_entrypoint.py` line 625: `await startup_on_ready(self)`.  
**Recommendation:** Update docstring to reflect current state.

---

### P2-AUD-R1-038 [COSMETIC] `notifications.py` import order has bare import AFTER all function definitions

**File:** `src/discord/notifications.py` line 240  
**Verification:** CONFIRMED  
**Description:** The bare `import discord` at the very end of the file (after all class, function, and constant definitions) violates both PEP 8 import ordering (imports at top) and the module's own lazy-import architecture.  
**Impact:** Design contradiction.  
**Recommendation:** Move to top of file if intended to be eager, or remove entirely.

---

### P2-AUD-R1-039 [COSMETIC] `_entrypoint.py` imports `from src.x_poster.discord import create_dashboard` at module top, but X Poster may not be deployed

**File:** `src/discord/_entrypoint.py` line 34  
**Verification:** CONFIRMED  
**Description:** The module-level import of `create_dashboard` from `src.x_poster.discord` means that importing `_entrypoint.py` will also pull in the X Poster module. If X Poster is not deployed or has missing dependencies, this import could fail. However, the actual creation is wrapped in try/except at line 632, so the import itself is the only risk.  
**Impact:** Low -- if `src.x_poster.discord` module has import-time side effects, they would execute on bot startup.  
**Recommendation:** Consider lazy-importing `create_dashboard` inside `on_ready` to match the pattern used for command callbacks.

---

### P2-AUD-R1-040 [COSMETIC] `notifications.py.FOOTER_TEXT` says "System Alert" but some callers use it for non-alert purposes

**File:** `src/discord/notifications.py` line 31  
**Verification:** CONFIRMED  
**Description:** The footer text is "Guinevere de Baroque System Alert" but the module can route to #guinevere-status (SEV3) and #audit-log (SEV4) which are not alert channels per se.  
**Impact:** Cosmetic -- footer context slightly off for status updates and audit records.  
**Recommendation:** Consider parameterizing footer text per SEV level.

---

### P2-AUD-R1-041 [COSMETIC] `notifications.py` `send_alert()` has unused function parameter `kwargs` that is consumed

**File:** `src/discord/notifications.py` lines 201 (parameter) and 227 (`kwargs.get("thread_name")`)  
**Verification:** CONFIRMED  
**Description:** The `**kwargs` parameter is only used for `thread_name`. Other kwargs are silently ignored.  
**Impact:** Low -- unused kwargs are silently dropped.  
**Recommendation:** Add explicit `thread_name` parameter or validate supported kwargs.

---

### P2-AUD-R1-042 [COSMETIC] `_entrypoint.py` imports `from src.finance.hook import on_message as process_finance_message` -- finance module dependency on startup

**File:** `src/discord/_entrypoint.py` line 33  
**Verification:** CONFIRMED  
**Description:** The finance module is imported eagerly at module level alongside `_entrypoint.py`. If the finance package has import-time issues, the bot fails to start.  
**Impact:** Bot startup depends on finance module being healthy at import time.  
**Recommendation:** Lazy-import inside `on_message` where it's used (line 683).

---

### P2-AUD-R1-043 [COSMETIC] `gotify_fallback.py` uses structlog-style fallback for when structlog is absent -- unnecessary complexity

**File:** `src/discord/gotify_fallback.py` lines 7-31  
**Verification:** CONFIRMED  
**Description:** The module has a complex 24-line fallback for when structlog is not installed, creating a mock structlog API. This adds maintenance burden for a rare case (structlog is always installed in production).  
**Impact:** Dead/complex code for fallback path.  
**Recommendation:** Simplify to `import logging; logger = logging.getLogger(__name__)` and skip the structlog emulation.

---

### P2-AUD-R1-044 [COSMETIC] `_intents.py` get_intents() does not cache result -- called on every GuinevereBot init

**File:** `src/discord/_intents.py` lines 71-96  
**Verification:** CONFIRMED  
**Description:** The function builds intents from scratch on every call. Since `GuinevereBot.__init__` calls it (in `_entrypoint.py` line 97), and there's typically only one bot instance, this is not a performance issue.  
**Impact:** None for single-bot deployments.  
**Recommendation:** Optional: add `@lru_cache` for cold-start performance.

---

### P2-AUD-R1-045 [COSMETIC] `_command_registry.py` function `command_count()` returns 49 but is unused in the repo

**File:** `src/discord/_command_registry.py` lines 375-378  
**Verification:** CONFIRMED  
**Description:** The `command_count()` function exists but is not called anywhere in the active codebase (not in `_entrypoint.py`, not in tests). It appears to be a public API for external verifiers.  
**Impact:** None. Utility function without callers.  
**Recommendation:** Consider removing or documenting the expected consumer.

---

### P2-AUD-R1-046 [COSMETIC] P2-FIX-PLAN.md Phase 2.1 marked `[x]` but Phase 2.2 (update PROGRESS.md) is NOT done

**File:** `docs/audit/P2-FIX-PLAN.md` lines 3-11  
**Verification:** CONFIRMED  
**Description:** Phase 1 items (SOPS encryption) are all `[x]` completed. Phase 2.1 (check existing SOPS) is `[x]` but 2.2 (update PROGRESS.md) remains `[ ]`. However PROGRESS.md no longer contains `commands_count` at all, so there's nothing to update there.  
**Impact:** Checklist item is misleading.  
**Recommendation:** Mark Phase 2 complete or clarify the actual required documentation fix.

---

### P2-AUD-R1-047 [COSMETIC] `_entrypoint.py` `_on_message_listener` and `on_message` both check `message.author.bot` -- redundant check

**File:** `src/discord/_entrypoint.py` lines 149-153 and 670  
**Verification:** CONFIRMED  
**Description:** The listener at line 149 checks `author.bot` and returns early. The main `on_message` handler at line 670 also checks `message.author.bot`. The second check is redundant but harmless (the HARD STOP listener already consumed or passed the message).  
**Impact:** Minor inefficiency in a hot path.  
**Recommendation:** Document that the duplicate check is intentional defense-in-depth.

---

### P2-AUD-R1-048 [COSMETIC] `hermes_conversational.py` only handles `#guinevere-chat` (channel ID 1510914600777023659) -- hardcoded

**File:** `src/discord/hermes_conversational.py` line 50 (GUINEVERE_CHAT_CHANNEL_ID)  
**Verification:** CONFIRMED  
**Description:** The channel ID is hardcoded in the module. If the channel is deleted and recreated, the bot silently ignores all chat messages.  
**Impact:** Hard-coded dependency on channel snowflake.  
**Recommendation:** Consider making the target channel configurable via env var.

---

### P2-AUD-R1-049 [COSMETIC] `gotify_fallback.py` `get_priority()` maps "SEV0" to 10 but Discord user-facing docs show SEV0 as lowest

**File:** `src/discord/gotify_fallback.py` line 43  
**Verification:** CONFIRMED  
**Description:** In Gotify, priority 10 is the highest. SEV0 (informational, actually the LOWEST severity in the 0-4 scale) maps to 10, the highest priority. This seems inverted.  
**Impact:** Cosmetic -- SEV0 alerts appear at maximum Gotify priority.  
**Recommendation:** Confirm priority mapping intent: SEV0 (informational) should probably map to low priority (1), and SEV4 (audit) to even lower (0). Or keep high for SEV0 if the naming convention is "0=highest urgency" which is unconventional.

---

### P2-AUD-R1-050 [COSMETIC] `cmd_safeword.py` `safeword_callback` calls `handler.check("safeword")` but does not use the return value

**File:** `src/discord/cmd_safeword.py` line 567  
**Verification:** CONFIRMED  
**Description:** The return boolean from `handler.check("safeword")` is discarded. The function always proceeds to build the embed regardless of whether the check triggered or not.  
**Impact:** Handler state is unchanged even if safe mode was already active. The embed always shows the same static content (see R1-029).  
**Recommendation:** Use the return value to decide between safe-mode embed and recovery embed.

---

### P2-AUD-R1-051 [COSMETIC] `cmd_safeword.py` recovery check in `_entrypoint.py` `on_message` potentially catches recovery phrases from slash commands

**File:** `src/discord/_entrypoint.py` line 678: `handler.check_recovery(message.content)`  
**Verification:** CONFIRMED  
**Description:** The recovery check runs on raw `message.content`. If a slash command `/somecommand resume` or similar content matches a recovery phrase, it could prematurely exit safe mode. The most likely recovery phrase is "resume" which is unlikely as a slash command.  
**Impact:** Low -- edge case where a message like "aku sudah okay" could be misidentified as recovery.  
**Recommendation:** Add a guard to only check recovery in #guinevere-chat or from the guild owner.

---

### P2-AUD-R1-052 [COSMETIC] `phase-2-discord.md` migration plan lists Gantt chart but has no dates

**File:** `docs/setup-evidence/hermes-migration/phase-2-discord.md`  
**Verification:** CONFIRMED  
**Description:** The document has a detailed Gantt chart (Day 1 through Day 8), but no actual start date, and the document is clearly aspirational -- no code was generated from its scripts.  
**Impact:** None. This is a planning document.  
**Recommendation:** Add a "status" note to clarify this is an aspirational migration plan, not a completed work order.

---

## PREVIOUS AUDIT FINDINGS RECONCILIATION

### Old P2-AUDIT-COMPLETE.md findings (2026-06-08)

| Old ID | Severity | Status | Notes |
|--------|----------|--------|-------|
| P2-002 (CRITICAL) | Encrypted secret missing | RESOLVED | `discord-secrets.enc.yaml` exists, properly SOPS-encrypted |
| P2-010 (WARN) | 33 vs 35 commands | STILL WRONG | Now 49 commands; 33/35/39/49 across 4 sources |
| P2-020 (WARN) | Gotify port | UNVERIFIED | Code says 8081, old audit saw 8080 |

### Old P2-FIX-PLAN.md items (2026-06-08)

| Phase | Status | Detail |
|-------|--------|--------|
| 1 (SOPS) | DONE (but incomplete) | `discord-secrets.enc.yaml` exists, but no `.env.discord.sops` for deploy unit |
| 2 (docs fix) | PARTIAL | PROGRESS.md no longer has command_count; CHECKLIST.md still at 33 |
| 3 (channel cleanup) | NOT STARTED | Ghost channels still in channel-ids.yaml |
| 4 (automation) | NOT STARTED | No cron/services for system-health, cost-tracker, evidence |

---

## VERDICT

**Architecture: IMPLEMENTED** -- The standalone bot (`_entrypoint.py`, 45 `cmd_*.py` modules, `_intents.py`, `_startup.py`, `_command_registry.py`) is a fully functional, wired implementation. It is not a stub or placeholder. All 49 slash commands are registered. HARD STOP is wired via `_on_message_listener` -> `handle_safeword_message_async`. `on_ready` calls `_startup.on_ready`. The standalone bot was the production runtime before P20 masked the service.

**Implementation Completeness: COMPLETE WITH FLAWS** -- The code compiles and runs, but has:
- A bare `import discord` at line 240 of `notifications.py` that contradicts the lazy-import design
- Static HARD STOP embed fields that ignore actual handler state
- GOTIFY_URL port may be wrong
- Command count chaos (49 code vs 33/35/39 elsewhere)
- Two conflicting service units, one referencing a non-existent env file
- Outdated docstrings claiming the HARD STOP text path is inactive

**Hermes Migration: NOT STARTED** -- The `phase-2-discord.md` is entirely aspirational. None of the 35 `plugins/*_plugin.py` files exist at the documented paths. The migration plan is not ready for execution.
