# P2 Round-1 Implementation Audit: Discord Permissions & Commands

**Auditor:** Subagent (read-only)
**Date:** 2026-06-25
**Scope:** Permissions layer, auth guard, slash command registry, command modules, HARD STOP wiring, embed colors, AuthLevel gating
**Methodology:** Static code analysis (Read, Grep, AST counting), cross-reference with old audits, evidence files, deprecated modules
**Output Path:** `docs/setup-evidence/legacy-audit/P2/audits/round-1/discord-permissions-commands.md`

---

## Executive Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 2 |
| HIGH | 4 |
| MEDIUM | 5 |
| LOW | 1 |
| COSMETIC | 3 |
| **TOTAL** | **15** |

---

## Finding Log

### P2-PC-R1-001 [CRITICAL] — `_deprecated` permissions.py imports non-existent `src.discord.guild_setup`

- **File:** `src/_deprecated/hermes-migration-phase-7/permissions.py` lines 18-19
- **Evidence:**
  ```python
  from src.discord.guild_setup import CHANNELS, get_token
  ```
- **Verification:** CONFIRMED
- **Description:** The permissions module at `src/_deprecated/hermes-migration-phase-7/permissions.py` imports `from src.discord.guild_setup`. However, `src/discord/guild_setup.py` does NOT exist. A Glob for `**/guild_setup.py` in `src/discord/` returned zero results. The only `guild_setup.py` in the repo is `src/_deprecated/hermes-migration-phase-7/guild_setup.py`. This means if anyone runs `permissions.py` via the deprecated path (channel permission application, topic reconciliation, admin review), it will crash with an `ImportError`.
- **Impact:** The entire P2-007/P2-008/P2-009 permission setup code is effectively dead code. The permission enforcement that IS running depends solely on `_auth_guard.py` (Faiz-only gate, no channel-level overwrites). The @everyone deny, append-only approximation, bot write access scoping, and OAuth least-privilege invite URL code are all in this deprecated-but-referenceable module. Any attempt to run `apply_permissions()` or `verify_permissions()` will fail.
- **Fix:** Either (a) move `guild_setup.py` into `src/discord/`, (b) update the import to point to the deprecated location, or (c) migrate the permission logic into active modules.

### P2-PC-R1-002 [CRITICAL] — `require_canonical_registry()` asserts 49 but command_catalog.py returns 39

- **Files:**
  - `src/discord/_command_registry.py` line 407: `raise RuntimeError(f"expected 49 commands, found {len(names)}")`
  - `src/hermes_plugins/command_catalog.py`: 39 commands (6 core + 7 loop + 4 memory + 3 surveillance + 3 finance + 8 system + 4 admin + 4 gmail)
- **Verification:** CONFIRMED
- **Description:** There is a structural mismatch between the two command registries:
  - `_command_registry.py` defines 49 `CommandSpec` entries and an assertion (`expected 49`).
  - `command_catalog.py` defines 39 commands across 8 categories.
  - Missing from `command_catalog.py`: health-report, health-trend, health-baseline (3 P14 health), memory-stats, memory-review, memory-schedule, memory-decay (4 P18 advanced memory), loop-status, loop-cost, loop-history (3 P5 loop monitoring) = 10 commands.
- **Impact:** The `/help` command callback (cmd_help.py line 279) calls `from src.hermes_plugins.command_catalog import command_categories`. This means `/help` will advertise only 39 of the 49 registered commands. Users will not discover health, advanced memory, or loop monitoring commands via `/help`. The help embed footer will show "39 Commands" instead of 49.
- **Fix:** Update `command_catalog.py` to include all 10 missing commands.

### P2-PC-R1-003 [HIGH] — Docstring/comment claims "33 commands" but code has 49

- **Files:**
  - `src/discord/cmd_help.py` line 4 (docstring): `"lists all 33 slash commands grouped by their 7 categories"`
  - `src/_deprecated/hermes-migration-phase-7/commands.py` line 302-307: assertion `expected 33 commands`
  - `PROGRESS.md` line 146: `"(35 commands)"`
  - `src/discord/_command_registry.py` line 407: assertion `expected 49 commands`
- **Verification:** CONFIRMED (stale strings at 33 and 35)
- **Description:** Multiple locations claim 33 or 35 commands, but the canonical registry has 49. The old deprecated `commands.py` still asserts 33. `cmd_help.py` docstring says 33. `PROGRESS.md` says 35. Only `_command_registry.py` is correct at 49.
- **Impact:** Confusion for developers reading docstrings/deprecated modules. The `require_canonical_registry()` test in `tests/discord/test_cmd_health_report.py` calls the _command_registry version (asserts 49) so tests pass, but the stale docstrings mislead.
- **Fix:** Update all stale references: cmd_help.py docstring, PROGRESS.md, and consider deleting or updating the deprecated commands.py.

### P2-PC-R1-004 [HIGH] — `notifications.py` bare `import discord` at module level contradicts lazy-import design

- **File:** `src/discord/notifications.py` line 240
  ```python
  import discord  # noqa: E402  # isort: skip
  ```
- **Verification:** CONFIRMED
- **Description:** The module defines a lazy-import protocol pattern (`_get_discord_embed_module()`) and a try/except block at lines 19-22 (`try: from discord import utils as discord_utils`). However, line 240 does a bare unconditional `import discord` at module level. If `discord.py` is absent during import (e.g., in a test environment or a non-bot process), the module will crash with `ImportError` at line 240, before any function is called. This contradicts the lazy-import protocol used by all other cmd modules.
- **Impact:** Importing `notifications.py` in any context requires `discord.py` to be installed and importable. Tests that import notifications without discord.py mocked will fail.
- **Fix:** Remove the bare `import discord` at line 240. The module already has a try/except import at lines 19-22 that handles `discord_utils`, and the embed construction at line 191 calls `_get_discord_embed_module()` dynamically.

### P2-PC-R1-005 [HIGH] — cmd_help.py uses hermes_plugins command_catalog, not the authoritative _command_registry

- **File:** `src/discord/cmd_help.py` line 279
  ```python
  from src.hermes_plugins.command_catalog import command_categories
  ```
- **Verification:** CONFIRMED
- **Description:** The `/help` command imports its category listing from `src.hermes_plugins.command_catalog.command_categories`, which only returns 39 commands. The authoritative registry (`src.discord._command_registry.COMMAND_SPECS`) has 49 commands. This means `/help` is incomplete.
- **Impact:** Users cannot discover 10 commands via `/help`.
- **Fix:** Either (a) update `command_catalog.py` to include all commands, or (b) make `cmd_help.py` derive categories from `_command_registry` instead.

### P2-PC-R1-006 [HIGH] — Administrator permission risk documented but only in deprecated module

- **File:** `src/_deprecated/hermes-migration-phase-7/permissions.py` lines 424-456 (`review_admin_scope()`)
- **Verification:** CONFIRMED
- **Description:** The deprecated `permissions.py` contains `review_admin_scope()` which checks whether the bot currently has the Administrator permission and produces a least-privilege invite URL. This function is NOT callable from any active code path because `permissions.py` is in the deprecated directory (and also has the ImportError issue from R1-001). The old P2-AUDIT-COMPLETE.md noted Administrator risk and listed OAuth reauthorization as needed long-term. That recommendation remains unaddressed: no active mechanism enforces least-privilege on the currently running bot.
- **Impact:** If the bot has Administrator permission (which the code's bitfield defines at `1 << 3`), it retains full guild admin access with no active monitoring or alerting. The `LEAST_PRIVILEGE_PERMISSIONS` value (`2_147_599_472` / `0x8000F870`) is defined but never enforced.
- **Fix:** Resurrect or reimplement `review_admin_scope()` in an active module and run it at startup. Perform the OAuth reauthorization per P2-009.

### P2-PC-R1-007 [MEDIUM] — `channel-ids.yaml` has 14 channels, `guild_setup.py` defines 13 canonical specs (plus rituals ghost)

- **Files:**
  - `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml`: 14 channel entries (includes `rituals`)
  - `src/_deprecated/hermes-migration-phase-7/guild_setup.py` lines 201-215: 13 `ChannelSpec` definitions (does NOT include rituals)
- **Verification:** CONFIRMED (channel-ids.yaml has 14, guild_setup has 13)
- **Description:** The `channel-ids.yaml` artifact lists 14 channels, including `rituals` (ID 1513496377324339262) which is NOT in the canonical `CHANNELS` tuple in `guild_setup.py`. The `rituals` channel appears to be a ghost channel created outside the P2-006 step. The old audit flagged this as 13-vs-14 discrepancy. The `APPEND_ONLY_CHANNELS` set in `permissions.py` (line 45) also does not include `rituals`.
- **Impact:** Permission overwrites and topic reconciliation (if the deprecated code ever ran) would not cover `rituals`. It is an unmanaged channel with unknown permissions.
- **Fix:** Either add `rituals` to the canonical specs or delete the channel.

### P2-PC-R1-008 [MEDIUM] — GOTIFY_URL hardcoded to port 8081, old audit references port 8080

- **File:** `src/discord/gotify_fallback.py` line 32
  ```python
  GOTIFY_URL: str = "http://localhost:8081"
  ```
- **Verification:** CONFIRMED
- **Description:** The `gotify_fallback.py` hardcodes Gotify API URL to port 8081. The old P2-AUDIT-COMPLETE.md section 2.0 P2-020 reported "Port 8080 responds `{"status":"up"}` on `/health` but Gotify binary not in PATH." The old audit tested port 8080, but the code points to 8081. If Gotify is actually running on 8080, the fallback will always fail with connection refused.
- **Impact:** Gotify fallback notifications will fail silently (fail-soft) if the actual service is on port 8080. No alert is raised for the mismatch.
- **Fix:** Set port via environment variable with a fallback, or reconcile the port with the actual deployment.

### P2-PC-R1-009 [MEDIUM] — SEV matrix channel names: `guinevere-alerts` in migration doc but no such channel in code

- **Files:**
  - `docs/setup-evidence/hermes-migration/phase-2-discord.md` line 69: `alerts: "guinevere-alerts"`
  - `src/discord/notifications.py` lines 33-37: SEV0->system-health, SEV1->system-health, SEV2->cost-tracker, SEV3->guinevere-status, SEV4->audit-log
  - `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml`: No `guinevere-alerts` channel
- **Verification:** CONFIRMED
- **Description:** The Hermes migration doc references a `guinevere-alerts` channel that does not exist in the channel-ids.yaml artifact or in the notifications.py SEV routing matrix. The migration doc's config block is aspirational/outdated. No alert-specific channel exists.
- **Impact:** If Hermes gateway is configured with `alerts: "guinevere-alerts"` at runtime, it will fail to find the channel. The current notifications.py routes SEV0/SEV1 to `system-health`, which is appropriate, but the migration doc describes a different setup.
- **Fix:** Either create the `guinevere-alerts` channel and update the routing, or correct the migration doc to use `system-health`.

### P2-PC-R1-010 [MEDIUM] — HARD STOP text detection via `on_message` IS wired (seed fact was wrong)

- **File:** `src/discord/_entrypoint.py` lines 132-160
- **Verification:** CONFIRMED
- **Description:** The seed fact claimed `handle_safeword_message_async` might be unwired. In fact, `_entrypoint.py` registers a `listen("on_message")` listener at line 138 that calls `handle_safeword_message_async`. The HARD STOP text path IS active. The `cmd_safeword.py` docstring in `handle_safeword_message` (sync, line 598) says "No bot.py listener exists yet" which is stale — the `_async` variant is wired.
- **Impact:** The stale docstring could mislead developers into adding redundant wiring. The actual functionality works.
- **Severity note:** This finding is MEDIUM because the core function is wired despite stale docstrings.
- **Fix:** Update the `handle_safeword_message` docstring to reflect that the async variant IS wired.

### P2-PC-R1-011 [MEDIUM] — Permissions module only uses `is_faiz_interaction`; no @everyone denials or channel-level overwrites active

- **File:** `src/discord/_auth_guard.py` (entire module, 23 lines)
- **Verification:** CONFIRMED
- **Description:** The only permission enforcement in the active codebase is `is_faiz_interaction()` which checks whether the interaction user is the guild owner (fail-closed). There is NO active mechanism to:
  - Deny @everyone channel visibility
  - Grant bot write access on specific channels
  - Enforce append-only mode on evidence/audit channels
  - Verify permission overwrites via REST
- All those functions are in `src/_deprecated/hermes-migration-phase-7/permissions.py` (which also has the import error from R1-001).
- **Impact:** The P2-007 channel permission setup is effectively unimplemented in the active codebase. Anyone with guild access can see all channels. The bot's channel access is entirely at Discord's default (based on OAuth scopes).
- **Fix:** Migrate `permissions.py` from deprecated into `src/discord/` (resolving the import first) and wire `apply_permissions()` into the startup sequence.

### P2-PC-R1-012 [LOW] — `cmd_help.py` `_CATEGORY_DISPLAY` missing gmail and health categories

- **File:** `src/discord/cmd_help.py` lines 57-65
  ```python
  _CATEGORY_DISPLAY: Final[dict[str, str]] = {
      "core": "Core \U0001f3e0",
      "loop": "Loop \U0001f504",
      "memory": "Memory \U0001f9e0",
      "surveillance": "Surveillance \U0001f441",
      "finance": "Finance \U0001f4b0",
      "system": "System ⚙",
      "admin": "Admin \U0001f6e0",
  }
  ```
- **Verification:** CONFIRMED
- **Description:** The `_CATEGORY_DISPLAY` map has 7 entries. The `command_categories()` from hermes_plugins returns 8 categories (includes "gmail"). The _command_registry also has "gmail" and "health" categories. When `cmd_help.py` builds field names, unknown category keys fall through to `key.capitalize()` (line 234), so "gmail" would display as "Gmail" (no emoji) and "health" as "Health" (no emoji).
- **Impact:** Minor cosmetic issue for `/help` output. Gmail and health categories would not have emoji.
- **Fix:** Add "gmail" and "health" entries to `_CATEGORY_DISPLAY`.

### P2-PC-R1-013 [COSMETIC] — `cmd_help.py` docstring says "7 categories" but now has 8

- **File:** `src/discord/cmd_help.py` line 4
  ```python
  "The embed lists all 33 slash commands grouped by their 7 categories,"
  ```
- **Verification:** CONFIRMED
- **Description:** The docstring is doubly stale: it says "33 commands" (should be at least 39 via hermes_plugins) and "7 categories" (should be 8, including gmail). The _command_registry has 9 categories (adding health).
- **Impact:** Cosmetic — does not affect runtime behavior.
- **Fix:** Update docstring to reflect current command count and category count.

### P2-PC-R1-014 [COSMETIC] — `cmd_safeword.py` stale readme-style comment says "No bot.py listener exists yet"

- **File:** `src/discord/cmd_safeword.py` line 598-601 (in `handle_safeword_message` sync docstring)
  ```
  "No bot.py listener exists yet. This function is callable and
   documented but inactive until P2-017 wires it into the message
   handler pipeline."
  ```
- **Verification:** CONFIRMED
- **Description:** This docstring on the sync variant refers to wiring that IS done in `_entrypoint.py` via the async variant. The comment predates the `_entrypoint.py` migration.
- **Impact:** Cosmetic — misleading to developers reading the code.
- **Fix:** Update or remove the stale docstring.

### P2-PC-R1-015 [COSMETIC] — Stale docstring in `_command_registry.py` references "12 wired + 20 stubs"

- **File:** `src/discord/_entrypoint.py` line 89
  ```python
  "Slash command tree (13 wired + 20 stubs) registered in ``setup_hook``."
  ```
- **Verification:** CONFIRMED
- **Description:** The `GuinevereBot` class docstring says "13 wired + 20 stubs". The `setup_hook` now wires all 49 commands explicitly with zero stubs generated. The stub loop at line 544-549 iterates over COMMAND_SPECS but all names are in `core_names`, so no stubs are created. The 13+20 count is incorrect.
- **Impact:** Cosmetic — does not affect runtime but misleads developers.
- **Fix:** Update the class docstring to reflect all 49 commands are wired.

---

## Cross-Reference: Old Audit Findings Re-Verified

### From P2-AUDIT-COMPLETE.md (2026-06-08)

| Old Finding | Current Status | Verdict |
|---|---|---|
| P2-002: Encrypted secret MISSING | SOPS-encrypted file `secrets/discord-secrets.enc.yaml` EXISTS (verified via Glob). Old audit checked `.yaml` not `.enc.yaml`. | CRITICAL to verify token is actually encrypted (ciphertext check) — cannot confirm without decrypting per HARD RULES. |
| P2-007: Permissions evidence exists | Permission code migrated to `_deprecated/`. No active channel-level permission enforcement. | **STILL OPEN** — channels may not have @everyone denies or append-only mode. |
| P2-009: OAuth reauthorization noted | `review_admin_scope()` in deprecated module only. Not active. | **STILL OPEN** — Administrator risk not mitigated. |
| P2-010: 33 vs 35 commands | Code now has 49. Stale references at 33 (deprecated), 35 (PROGRESS.md), 39 (hermes_plugins). | **WORSENED** — the gap grew from 33/35 to 33/35/39/49. |
| P2-020: Gotify port 8080 vs 8081 | Code hardcodes 8081. Old evidence shows 8080 responding. | **STILL OPEN** — port mismatch not reconciled. |

### From P2-FIX-PLAN.md

| Item | Status |
|---|---|
| 1.1-1.5: SOPS encryption | `secrets/discord-secrets.enc.yaml` now exists. Cannot verify contents per HARD RULES. |
| 2.1: Update PROGRESS.md 33->35 | **NOT DONE** — PROGRESS.md still says "35" which is also now wrong (should be 49). |
| 3.1-3.3: Channel cleanup | **NOT DONE** — ghost channels (project-alpha-dev, alpha-docs, beta-dev) + rituals remain. |
| 4.1-4.3: Automation for empty channels | **NOT DONE** — empty channels remain empty. |

---

## Summary

The active permission layer is thin: only `is_faiz_interaction()` in `_auth_guard.py`. All channel-level permission management code (P2-007, P2-008, P2-009) has been moved to `src/_deprecated/hermes-migration-phase-7/` and is broken by an `ImportError` for `src.discord.guild_setup` which does not exist. The command registry has grown to 49 commands, but the `/help` command references a stale catalog with only 39 entries. Multiple docstrings and PROGRESS.md cite incorrect counts (33, 35, 39 vs 49). Notifications.py has a bare `import discord` at module level that contradicts the lazy-import protocol. Gotify port mismatch persists. Channel drift (14 entries vs 13 canonical) is unaddressed.
