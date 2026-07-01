# Round-2 Adversarial Verification: Discord Permissions & Commands

**Verifier:** Subagent (read-only)
**Date:** 2026-06-25
**Scope (ROUND-2):** Re-verify every round-1 finding in `docs/setup-evidence/legacy-audit/P2/audits/round-1/discord-permissions-commands.md`, then run a miss-hunt for bugs round-1 missed.

---

## Section 1: Round-1 Finding Re-Verification

### P2-PC-R1-001 [CRITICAL] — `_deprecated` permissions.py imports non-existent `src.discord.guild_setup`

- **File:** `src/_deprecated/hermes-migration-phase-7/permissions.py` lines 18-19
- **Original verdict:** CONFIRMED
- **Adversarial re-verification:** CONFIRMED
- **Rationale:** Verified via Read at line 18: `from src.discord.guild_setup import CHANNELS, get_token`. Glob for `**/guild_setup.py` in `src/discord/` returned zero results. The only `guild_setup.py` is at `src/_deprecated/hermes-migration-phase-7/guild_setup.py`. The import path is definitively wrong. If any code path touches this module, it crashes with `ImportError`.
- **Severity still appropriate:** Yes, CRITICAL.

### P2-PC-R1-002 [CRITICAL] — `require_canonical_registry()` asserts 49 but command_catalog.py returns 39

- **Files:** `_command_registry.py` line 407, `command_catalog.py`
- **Original verdict:** CONFIRMED
- **Adversarial re-verification:** PARTIALLY-CONFIRMED — the numbers ARE 49 and 39, but the finding overstates the problem.
- **Rationale:**
  - `_command_registry.py` line 407: verified `raise RuntimeError(f"expected 49 commands, found {len(names)}")`. Counting `CommandSpec(` occurrences returns 49 (confirmed via grep -c: 49 matches).
  - `command_catalog.py` `_COMMAND_CATEGORIES`: `core(6) + loop(7) + memory(4) + surveillance(3) + finance(3) + system(8) + admin(4) + gmail(4) = 39`.
  - However: the registry has 49 because it adds **gmail (4)**, **health (3)**, **memory-stats/review/schedule/decay (4)**, and **loop-status/cost/history (3)** = 14 commands beyond what command_catalog covers. But command_catalog *also* has gmail (4), so the delta is 10 commands (health 3 + advanced memory 4 + loop monitoring 3), matching round-1's description.
  - The `/help` impact is real (users miss 10 commands), but this is a **cosmetic/UX gap**, not a CRITICAL crash. CRITICAL severity is overstated for a help-display gap.
- **Severity adjustment:** Should be HIGH, not CRITICAL. The command_sync/registry assertion at 49 is the canonical truth; the command_catalog is a secondary display catalog.
- **Verdict:** PARTIALLY-CONFIRMED (numbers correct, severity overstated).

### P2-PC-R1-003 [HIGH] — Docstring/comment claims "33 commands" but code has 49

- **Files:** `cmd_help.py` line 4, `_deprecated/commands.py` lines 302-307, `PROGRESS.md` line 146
- **Original verdict:** CONFIRMED
- **Adversarial re-verification:** CONFIRMED
- **Rationale:**
  - `cmd_help.py` line 4 docstring: `"lists all 33 slash commands grouped by their 7 categories"` — verified via Read.
  - `_deprecated/commands.py` line 307: `raise RuntimeError(f"expected 33 commands` — verified.
  - `_entrypoint.py` class docstring line 89-90: `"(13 wired + 20 stubs)"` — verified (stale, all 49 are wired).
  - The deprecated file has 33 (old count) and the active registry has 49. PROGRESS.md says 35.
- **Missed by round-1:** The `_entrypoint.py` class docstring (line 89: "13 wired + 20 stubs") is also stale, noting that stub loop is now bypassed for all 49 commands. This should have been flagged.
- **Verdict:** CONFIRMED.

### P2-PC-R1-004 [HIGH] — `notifications.py` bare `import discord` at module level contradicts lazy-import design

- **File:** `src/discord/notifications.py` line 240
- **Original verdict:** CONFIRMED
- **Adversarial re-verification:** CONFIRMED
- **Rationale:** Verified via Read at line 240: `import discord  # noqa: E402  # isort: skip`. The module has a try/except at lines 19-22 that gracefully handles `discord.utils` import failure, then later at line 240 does an unconditional bare `import discord`. If discord.py is absent, the module crashes at import time on line 240 before any function call. This contradicts the lazy-import protocol used in all cmd modules.
- **Verdict:** CONFIRMED. Severity HIGH is appropriate.

### P2-PC-R1-005 [HIGH] — cmd_help.py uses hermes_plugins command_catalog, not the authoritative _command_registry

- **File:** `cmd_help.py` line 279
- **Original verdict:** CONFIRMED
- **Adversarial re-verification:** CONFIRMED
- **Rationale:** Verified via Read at line 279: `from src.hermes_plugins.command_catalog import command_categories`. The `command_categories()` returns 8 categories with 39 commands. The authoritative `_command_registry` has 9 categories (adds "health") with 49 commands. Command_sync uses the registry; help uses the catalog. They are out of sync.
- **Verdict:** CONFIRMED.

### P2-PC-R1-006 [HIGH] — Administrator permission risk documented but only in deprecated module

- **File:** `src/_deprecated/hermes-migration-phase-7/permissions.py` lines 424-456
- **Original verdict:** CONFIRMED
- **Adversarial re-verification:** CONFIRMED
- **Rationale:** Verified via Read — `review_admin_scope()` exists only in the deprecated module which also has the ImportError (R1-001). The active `_auth_guard.py` (only 23 lines) does not enforce least-privilege. No active code path can call `review_admin_scope()`.
- **Verdict:** CONFIRMED.

### P2-PC-R1-007 [MEDIUM] — `channel-ids.yaml` has 14 channels, `guild_setup.py` defines 13 canonical specs (plus rituals ghost)

- **Files:** `channel-ids.yaml`, `guild_setup.py` lines 201-215
- **Original verdict:** CONFIRMED
- **Adversarial re-verification:** CONFIRMED
- **Rationale:** Verified via Read:
  - `channel-ids.yaml` has 14 channels (including `rituals: 1513496377324339262`)
  - `guild_setup.py` lines 201-215 has 13 `ChannelSpec` entries, does NOT include `rituals`.
  - `rituals` is indeed a ghost channel.
- **Verdict:** CONFIRMED.

### P2-PC-R1-008 [MEDIUM] — GOTIFY_URL hardcoded to port 8081, old audit references port 8080

- **File:** `src/discord/gotify_fallback.py` line 32
- **Original verdict:** CONFIRMED
- **Adversarial re-verification:** CONFIRMED
- **Rationale:** Verified via Read at line 32: `GOTIFY_URL: str = "http://localhost:8081"`. This is not configurable via environment variable (no override). If Gotify is on 8080, fallback silently fails.
- **Verdict:** CONFIRMED.

### P2-PC-R1-009 [MEDIUM] — SEV matrix channel names: `guinevere-alerts` in migration doc but no such channel in code

- **Files:** `phase-2-discord.md` line 69, `notifications.py` lines 33-37, `channel-ids.yaml`
- **Original verdict:** CONFIRMED
- **Adversarial re-verification:** CONFIRMED
- **Rationale:** Verified via Read:
  - `phase-2-discord.md` line 69: `alerts: "guinevere-alerts"` — aspirational.
  - `notifications.py` lines 33-37: SEV0/1->system-health, SEV2->cost-tracker, SEV3->guinevere-status, SEV4->audit-log. No `guinevere-alerts` exists.
  - `channel-ids.yaml`: No `guinevere-alerts` channel.
- **Verdict:** CONFIRMED.

### P2-PC-R1-010 [MEDIUM] — HARD STOP text detection via `on_message` IS wired (seed fact was wrong)

- **File:** `_entrypoint.py` lines 132-160
- **Original verdict:** CONFIRMED
- **Adversarial re-verification:** CONFIRMED
- **Rationale:** Verified via Read — `_register_hard_stop_listener()` at line 132 calls `self.listen("on_message")(self._on_message_listener)` at line 138. The listener at line 140 calls `handle_safeword_message_async` at line 155. The sync variant's docstring at `cmd_safeword.py` line 598 says "No bot.py listener exists yet" which is stale. Functionally correct.
- **Verdict:** CONFIRMED.

### P2-PC-R1-011 [MEDIUM] — Permissions module only uses `is_faiz_interaction`; no @everyone denials or channel-level overwrites active

- **File:** `_auth_guard.py` (entire module)
- **Original verdict:** CONFIRMED
- **Adversarial re-verification:** CONFIRMED
- **Rationale:** Verified via Read — `_auth_guard.py` is 23 lines. `is_faiz_interaction()` checks guild owner. No channel permission setup, no @everyone deny, no append-only enforcement. All channel-level permission code is in the deprecated (and broken) `permissions.py`.
- **Verdict:** CONFIRMED.

### P2-PC-R1-012 [LOW] — `cmd_help.py` `_CATEGORY_DISPLAY` missing gmail and health categories

- **File:** `cmd_help.py` lines 57-65
- **Original verdict:** CONFIRMED
- **Adversarial re-verification:** CONFIRMED
- **Rationale:** Verified via Read — 7 entries (core, loop, memory, surveillance, finance, system, admin). Missing "gmail" and "health". The `command_catalog` returns 8 categories (includes gmail). The `_command_registry` has 9 categories (adds health).
- **Verdict:** CONFIRMED.

### P2-PC-R1-013 [COSMETIC] — `cmd_help.py` docstring says "7 categories" but now has 8

- **File:** `cmd_help.py` line 4
- **Original verdict:** CONFIRMED
- **Adversarial re-verification:** CONFIRMED
- **Rationale:** Docstring says "7 categories". `command_categories()` returns 8. Registry has 9 categories. All stale.
- **Verdict:** CONFIRMED.

### P2-PC-R1-014 [COSMETIC] — `cmd_safeword.py` stale readme-style comment says "No bot.py listener exists yet"

- **File:** `cmd_safeword.py` lines 598-601
- **Original verdict:** CONFIRMED
- **Adversarial re-verification:** CONFIRMED
- **Rationale:** Verified via Read. Comment is stale; async variant IS wired in `_entrypoint.py`.
- **Verdict:** CONFIRMED.

### P2-PC-R1-015 [COSMETIC] — Stale docstring in `_entrypoint.py` references "12 wired + 20 stubs"

- **File:** `_entrypoint.py` line 89
- **Original verdict:** CONFIRMED
- **Adversarial re-verification:** CONFIRMED
- **Rationale:** Verified via Read at line 89-90: `"(13 wired + 20 stubs)"`. The setup_hook now wires all 49 explicitly. The stub loop at lines 544-549 is dead code (all names in core_names). Docstring is stale.
- **Verdict:** CONFIRMED.

---

## Section 2: Cross-Reference Re-Check

### From P2-AUDIT-COMPLETE.md (2026-06-08) & P2-FIX-PLAN.md

| Reference Item | Round-1 Verdict | Adversarial Re-Verdict | Notes |
|---|---|---|---|
| P2-002: Encrypted secret MISSING | SOPS-encrypted `secrets/discord-secrets.enc.yaml` EXISTS | CONFIRMED EXISTENCE — File verified via Glob. Cannot check ciphertext per HARD RULES. | OK |
| P2-007: Permissions evidence exists | No active channel-level enforcement | CONFIRMED | Still open |
| P2-009: OAuth reauthorization noted | Not active | CONFIRMED | Still open |
| P2-010: 33 vs 35 commands vs 49 | Gap widened | CONFIRMED | Still open |
| P2-020: Gotify port 8080 vs 8081 | 8081 in code | CONFIRMED | Still open |
| Fix Plan 1.1-1.5: SOPS encryption | `.enc.yaml` exists | CONFIRMED | Cannot verify |
| Fix Plan 2.1: Update PROGRESS.md 33->35 | NOT DONE | CONFIRMED | PROGRESS.md still says 35 (should be 49) |
| Fix Plan 3.1-3.3: Channel cleanup | NOT DONE | CONFIRMED | Ghost channels remain |
| Fix Plan 4.1-4.3: Automation for empty channels | NOT DONE | CONFIRMED | Empty channels remain |

---

## Section 3: MISS-HUNT — New Findings Round-1 Missed

### P2-PC-R2-001 [HIGH] — `cmd_pc.py` is fully built but completely unwired: no entry in `_command_registry.py`, no import in `_entrypoint.py`

- **File:** `src/discord/cmd_pc.py` (entire file, 445 lines), `src/discord/_command_registry.py`, `src/discord/_entrypoint.py`, `src/hermes_plugins/command_catalog.py`
- **Verification:** CONFIRMED
- **Description:** The `cmd_pc.py` module has a complete `pc_callback` (P15-010 Windows daemon status), with Faiz-only auth guard, 6 injectable data gatherers, embed builder, graceful degradation on every gather step, and `__all__` exports. However:
  - `_command_registry.py` does NOT define a `CommandSpec("...", "pc", ...)`. Grep for `"pc"` in the file returns zero matches.
  - `_entrypoint.py` does NOT import or wire `pc_callback`. Grep for `cmd_pc` or `pc_callback` in `_entrypoint.py` returns zero matches.
  - `command_catalog.py` does NOT list `/pc`.
  - The module is completely dead code: 445 lines with auth guard, 15 try/except blocks for graceful degradation, 6 injectable gather functions — none of it is ever called.
- **Impact:** The entire P15-010 Windows PC status command is MIA at runtime. Users cannot access `/pc` because it was never registered in the command tree, never synced to Discord, and never wired in `setup_hook`. This is a stub leak: the module exists and is fully implemented, but the registry/entrypoint were never updated to include it.
- **Severity:** HIGH (feature-complete command module completely disconnected from runtime)

### P2-PC-R2-002 [MEDIUM] — Three surveillance command modules duplicate `is_faiz_interaction` instead of importing from `_auth_guard`

- **Files:**
  - `src/discord/cmd_surveillance_pause.py` lines 58-73 (own `is_faiz_interaction`)
  - `src/discord/cmd_surveillance_resume.py` lines 58-73 (own `is_faiz_interaction`)
  - `src/discord/cmd_surveillance_status.py` lines 48-63 (own `is_faiz_interaction`)
  - `src/discord/_auth_guard.py` lines 11-22 (canonical `is_faiz_interaction`)
- **Verification:** CONFIRMED
- **Description:** The three surveillance command modules each define their own `is_faiz_interaction()` function with identical logic, instead of importing from the canonical `src.discord._auth_guard`. All 42 other command modules correctly use `from ._auth_guard import is_faiz_interaction` (some lazily inside the callback). The three surveillance modules use a local copy. The body is functionally identical (`guild.owner_id == user.id`), but this duplicates code and creates a maintenance hazard: if the auth logic ever changes (e.g., adding role-based checks), the surveillance modules would silently keep the old logic.
- **Impact:** Low in current state (identical code). Maintenance risk: auth changes would require fixing 3 extra files. Also a code quality smell: the modules' `__all__` exports `"is_faiz_interaction"` as a public API which is unexpected.
- **Severity:** MEDIUM

### P2-PC-R2-003 [MEDIUM] — `notifications.py` import sequence: try/except at line 19 catches `discord.utils`, then bare `import discord` at line 240 guarantees crash on missing dependency

- **File:** `src/discord/notifications.py` lines 19-22 and line 240
- **Verification:** CONFIRMED (overlaps with R1-004 but analyzed more deeply)
- **Description:** The try/except at lines 19-22:
  ```python
  try:
      from discord import utils as discord_utils
  except Exception:
      discord_utils = None
  ```
  This catches the case where `discord` is absent, setting `discord_utils = None`. However, line 240 does:
  ```python
  import discord  # noqa: E402  # isort: skip
  ```
  This WILL crash with `ImportError` if `discord` is not installed, before any function using the module is called. The try/except is misleading — it creates the false impression that the module handles missing discord gracefully, but line 240 guarantees it doesn't.
- **Impact:** Any test or non-bot process that imports `notifications.py` without `discord.py` available will crash. This is a concrete import-time failure.
- **Severity:** MEDIUM (the bare import contradicts the seeming graceful handling)

### P2-PC-R2-004 [MEDIUM] — `_entrypoint.py` stub loop iterates all 49 commands but all are in `core_names`, making stub-generator dead code

- **File:** `src/discord/_entrypoint.py` lines 515-549
- **Verification:** CONFIRMED
- **Description:** The `setup_hook` explicitly wires all 49 commands via `self.tree.command(name=..., description=..., guild=...)(callback)` lines. Then at lines 544-549, the stub loop iterates `COMMAND_SPECS` and generates stubs for any name NOT in `core_names`. Since `core_names` contains ALL 49 command names (lines 515-542), the stub loop never fires. The `_STUB_PHASE` dict and `_make_stub_callback` are dead code. But worse: if a developer adds a new command without adding it to both the explicit wiring AND `core_names`, the stub would register it as a stub alongside the real callback, causing Discord to have duplicate commands (both the real one and the stub).
- **Impact:** Currently dead code with no harm. But it's a trap for future contributors: adding a command to `_command_registry.py` but forgetting to add it to `core_names` would cause a duplicate registration.
- **Severity:** MEDIUM

### P2-PC-R2-005 [LOW] — `command_catalog.py` command count `sum(len(cmds)...)` undercounts: 39 vs 49

- **Files:** `src/hermes_plugins/command_catalog.py` lines 50-52
- **Verification:** CONFIRMED
- **Description:** The `command_count()` function computes `sum(len(cmds) for cmds in _COMMAND_CATEGORIES.values())`. With 8 categories and known command counts, this returns 39. The canonical count is 49. Any downstream consumer calling `command_count()` gets 39.
- **Impact:** `/help` embed footer says "39 commands" instead of 49 (when using the catalog path). Tests or scripts that rely on `command_count()` for validation get the wrong answer.
- **Severity:** LOW

### P2-PC-R2-006 [LOW] — `require_canonical_registry()` never called at startup

- **File:** `src/discord/_command_registry.py` lines 402-418
- **Verification:** CONFIRMED
- **Description:** The function validates command count (49), checks for duplicates, and validates payload lengths. But it is never called by `_entrypoint.py`, `_startup.py`, or any active module. Only the deprecated `commands.py` calls its own version. This means if a developer accidentally adds a duplicate or over-long command name, it won't be caught until runtime Discord sync fails.
- **Impact:** Silent validation gap. No early detection of registry errors.
- **Severity:** LOW

### P2-PC-R2-007 [LOW] — `notifications.py` SEV routing uses channel names that may not exist as Discord channel objects

- **File:** `src/discord/notifications.py` lines 33-37
- **Verification:** NEEDS-RUNTIME
- **Description:** The SEV matrix routes alerts to channels named "system-health", "cost-tracker", "guinevere-status", "audit-log". These names match `channel-ids.yaml` entries. However, `notifications.py` sends via REST (using `discord_rest_client.py`) which needs channel IDs, not names. The code uses string channel names. If the REST client resolves names to IDs at runtime, this could succeed or fail depending on the implementation. Without running the code, this is a potential mismatch.
- **Impact:** If channel name resolution fails, SEV alerts silently go undelivered.
- **Severity:** LOW (potential)

### P2-PC-R2-008 [LOW] — `gotify_fallback.py` has no env-var override for port

- **File:** `src/discord/gotify_fallback.py` line 32
- **Verification:** CONFIRMED
- **Description:** `GOTIFY_URL = "http://localhost:8081"` is hardcoded as a module-level constant with no mechanism to override it (no env var, no config injection). The `send_fallback` function (line 47) has a `token = os.environ.get("GOTIFY_APP_TOKEN", "")` for the token but no URL override.
- **Impact:** Deploying Gotify on a different port requires modifying source code.
- **Severity:** LOW

---

## Section 4: Summary

| Status | Count |
|--------|-------|
| Round-1 findings CONFIRMED | 13 of 15 |
| Round-1 findings PARTIALLY-CONFIRMED | 1 (P2-PC-R1-002 — severity overstated) |
| Round-1 findings REFUTED | 0 |
| Round-1 findings NEEDS-RUNTIME | 0 |
| New findings (miss-hunt) | 8 |
| **New HIGH** | 1 (P2-PC-R2-001) |
| **New MEDIUM** | 3 (P2-PC-R2-002, R2-003, R2-004) |
| **New LOW** | 4 (P2-PC-R2-005, R2-006, R2-007, R2-008) |

### Key Headlines

1. **P2-PC-R2-001 [HIGH]** — `cmd_pc.py` is 445 lines of fully built, auth-guarded, gracefully-degraded code that is completely dead: not registered in `_command_registry.py`, not wired in `_entrypoint.py`, not in `command_catalog.py`. The `/pc` command simply does not exist at runtime.

2. **P2-PC-R2-002 [MEDIUM]** — Three surveillance modules (`cmd_surveillance_pause.py`, `cmd_surveillance_resume.py`, `cmd_surveillance_status.py`) duplicate the `is_faiz_interaction` function locally instead of importing from `_auth_guard`. Maintenance hazard.

3. **P2-PC-R2-004 [MEDIUM]** — The stub loop in `_entrypoint.py` is dead code because all 49 command names are in `core_names`. Creates a trap for future developers: adding a new `CommandSpec` without updating both the explicit wiring AND `core_names` causes duplicate registration.

4. **Round-1 severity note:** P2-PC-R1-002 is overstated as CRITICAL; a help-display gap is HIGH at worst. The 49-vs-39 mismatch is real and should be fixed, but does not crash the bot.

5. **No round-1 findings were refuted.** All 15 original findings are confirmed or partially-confirmed, though R1-002's severity is questionable.
