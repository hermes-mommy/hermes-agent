# P2 Discord -- Consolidated Bug Register (All Severities)

**Generated:** 2026-06-25
**Updated:** 2026-06-26 V2 — direct-SSH live-VPS reconciled
**Method:** Deduplication of all round-1 and round-2 findings across 6 audit dimensions (all 6 R2 files present and verified). V2 uses direct SSH to `guinevere-vps` as authoritative source of truth — `vps-mirror` is STALE.
**Source files:** 12 audit files (6 R1 + 6 R2) across 6 dimensions.

**Total raw findings across all files:** ~200 (heavy duplication across dimensions)
**2026-06-26 V2 update:** V1 used stale `vps-mirror` and incorrectly classified the bot as masked. V2 uses direct SSH: bot is active+enabled, token is plaintext on VPS, no SOPS deployed. 5 new V2 findings added. All CRITICAL/HIGH reclassified.

---

## Summary Table

Computed from 84 detailed `### P2-BUG-NNN [SEVERITY]` headings below.

| Severity | Count |
|----------|-------|
| CRITICAL | 5 |
| HIGH | 14 |
| MEDIUM | 19 |
| LOW | 19 |
| COSMETIC | 27 |
| **TOTAL** | **84** |

### Live VPS Reclassification V2 (CRITICAL + HIGH only, 2026-06-26 direct SSH)

**V2 CORRECTION:** V1 used stale `vps-mirror` and assumed bot was masked. Direct SSH proves bot is `active+enabled`. All FALLBACK_REACTIVATION_RISK findings are now live risks. Three REPO_ONLY_DRIFT findings elevated to CONFIRMED_ON_VPS because the bot is actually running.

| Bug ID | Title | Severity | V1 Class | V2 Class | Rationale |
|--------|-------|----------|----------|----------|-----------|
| P2-BUG-001 | Age key plaintext on disk | CRITICAL | DESIGN_RISK_DORMANT | **CONFIRMED_ON_VPS** | Age key exists on VPS at `/home/guinevere/secrets/age-key.txt` |
| P2-BUG-002 | `send_alert()` never called | CRITICAL | REPO_ONLY_DRIFT | **CONFIRMED_ON_VPS** | Bot is active — dead SEV pipeline on live service |
| P2-BUG-003 | `#alerts` channel nonexistent | CRITICAL | DOC_STALE_ONLY | **DOC_STALE_ONLY** | Unchanged — channel naming drift |
| P2-BUG-004 | Broken deploy unit | CRITICAL | FALLBACK_RISK | **CONFIRMED_ON_VPS** | Deployed unit uses plaintext `.env.discord` — no SOPS |
| P2-BUG-005 | systemd/ template plaintext env | HIGH | FALLBACK_RISK | **CONFIRMED_ON_VPS** | The deployed unit IS the plaintext template |
| P2-BUG-006 | Scripts parse plaintext env | HIGH | REPO_ONLY_DRIFT | **REPO_ONLY_DRIFT** | Finance scripts not deployed on VPS |
| P2-BUG-007 | Conflicting hermes units | HIGH | REPO_ONLY_DRIFT | **REPO_ONLY_DRIFT** | Unchanged |
| P2-BUG-008 | 4-way command count drift | HIGH | DOC_STALE_ONLY | **DOC_STALE_ONLY** | Unchanged |
| P2-BUG-009 | `cmd_pc.py` dead code | HIGH | REPO_ONLY_DRIFT | **CONFIRMED_ON_VPS** | Bot is active — dead code on live service |
| P2-BUG-010 | Plaintext backup creds | HIGH | DESIGN_RISK_DORMANT | **DESIGN_RISK_DORMANT** | Dev box only |
| P2-BUG-011 | Administrator permission | HIGH | DESIGN_RISK_DORMANT | **CONFIRMED_ON_VPS** | Bot is active with Administrator scope |
| P2-BUG-012 | Broken permissions module | HIGH | REPO_ONLY_DRIFT | **CONFIRMED_ON_VPS** | Bot is active — no runtime permission enforcement |
| P2-BUG-013 | Incomplete /help output | HIGH | DOC_STALE_ONLY | **CONFIRMED_ON_VPS** | Bot is active — users see incomplete /help |
| P2-BUG-014 | Gotify undeployed | HIGH | CONFIRMED_ON_VPS | **CONFIRMED_ON_VPS** | LoadState=not-found confirmed |
| P2-BUG-015 | Safety gate bypasses | HIGH | REPO_ONLY_DRIFT | **REPO_ONLY_DRIFT** | Unchanged |
| P2-BUG-016 | Missing env files | HIGH | FALLBACK_RISK | **FALSE_POSITIVE** | `.env.discord` EXISTS on VPS (808 bytes) |
| **P2-BUG-080 (NEW V2)** | **Discord token in PLAINTEXT on VPS** | **CRITICAL** | — | **CONFIRMED_ON_VPS** | `.env.discord` contains plaintext token. No SOPS deployed. `discord-secrets.enc.yaml` never deployed to VPS. VPS `secrets/` dir has no discord file. |
| **P2-BUG-081 (NEW V2)** | **P2-022 "masked" claim is FALSE** | **HIGH** | — | **CONFIRMED_ON_VPS** | `systemctl is-active guinevere-discord` → `active`. `is-enabled` → `enabled`. PROGRESS.md:158 claim is false. |
| **P2-BUG-082 (NEW V2)** | **Two services share same token** | **HIGH** | — | **CONFIRMED_ON_VPS** | Both `guinevere-discord` + `hermes-gateway` read `DISCORD_BOT_TOKEN`. No collision detected but shared plaintext token. |
| **P2-BUG-083 (NEW V2)** | **Inflated log error count — broad grep misleading** | **MEDIUM** | — | **CONFIRMED_ON_VPS** | Broad grep of 2,485 matches is 98.4% X-poster `state=failed` polling (2,448/2,485). Real errors: 2 `[ERROR]`, 0 Tracebacks, 1 CRITICAL/FATAL match. Original HIGH severity was incorrect. → **DOWNGRADED TO MEDIUM**. |
| **P2-BUG-084 (NEW V2)** | **vps-mirror is STALE** | **MEDIUM** | — | **CONFIRMED_ON_VPS** | `vps-mirror/systemd-live/` has no discord unit. Live VPS has it at `/etc/systemd/system/`. The mirror is out of sync. |

**V2 key conclusion:** V1 incorrectly assumed bot was masked. 8 findings changed from FALLBACK_RISK/REPO_ONLY_DRIFT/DESIGN_RISK_DORMANT to CONFIRMED_ON_VPS because the bot IS actively running. 5 new V2 findings from direct SSH. 1 FALSE_POSITIVE corrected. Live VPS: bot is active, stable, but token is plaintext and Administrator scope is active.

---

## CRITICAL

### P2-BUG-001 [CRITICAL] Age secret key stored in plaintext on disk (git-ignored but co-located)

- **Dimension:** Security/Secrets, Runtime-Config
- **File:** `secrets/new-age-key.txt`
- **Description:** The private age key (`AGE-SECRET-KEY-[REDACTED]`) is stored in plaintext in the `secrets/` directory alongside the SOPS-encrypted files it decrypts. Round-2 verified the file IS git-ignored (not in git history), but it remains on disk and defeats SOPS co-location security: any filesystem compromise exposes all encrypted secrets. `.sops.yaml` references the corresponding public key.
- **Impact:** Full compromise of Discord bot token, bot ID, DB passwords, Redis passwords, and all other SOPS-encrypted secrets if filesystem access is obtained.
- **Verification:** CONFIRMED (git-ignored, not tracked, but present on disk)
- **Blocker for:** P19 (multi-project secrets), P24 (Hermes fork convergence -- all secrets under one key)
- **Source findings:** P2-AUD-R1-001 (security), P2-RC-R1-003 (runtime), P2-RC-R2-003 (runtime R2)

### P2-BUG-002 [CRITICAL] notifications.py send_alert() is NEVER CALLED -- entire alert pipeline is dead code

- **Dimension:** Notification/Fallback, Architecture
- **File:** `src/discord/notifications.py` (entire module, 241 lines)
- **Description:** Grep across entire `src/` tree confirms zero imports of `send_alert` from any production module. The SEV routing matrix (SEV0->system-health, SEV1->system-health, SEV2->cost-tracker, SEV3->guinevere-status, SEV4->audit-log), Gotify fallback dispatch, embed builder, and channel lookup are all defined but never invoked. Only `tests/discord/test_notifications.py` imports the module.
- **Impact:** Zero runtime alert delivery via Discord notifications module. SEV0/SEV1 critical alerts never reach Discord channels via this path. P2-019 (notification routing) is effectively unimplemented at runtime.
- **Verification:** CONFIRMED
- **Blocker for:** P22 (raw/full access -- notification routing needed for action safety)
- **Source findings:** P2-AUD-R2-002 (architecture R2), P2-NF-R1-001 (notification)

### P2-BUG-003 [CRITICAL] AC-DISCORD-003 targets #alerts channel that does not exist anywhere

- **Dimension:** Notification/Fallback, Evidence/Docs, Permissions/Commands
- **Files:** `docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md:129`, `docs/10-governance/12-SRS_v1.0.md:75`, `docs/10-governance/13-FSD_v1.0.md:209`, `docs/setup-evidence/hermes-migration/phase-2-discord.md:69`, `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml`
- **Description:** Three-way channel-name drift: (1) SRS/FSD/AC-catalog require `#alerts`; (2) Hermes migration doc references `guinevere-alerts`; (3) runtime code routes to `system-health`. Neither `#alerts` nor `guinevere-alerts` exists in `channel-ids.yaml` (14 channels, zero named "alerts"). The acceptance criterion AC-DISCORD-003 ("SEV0 and SEV1 alerts must reach #alerts within 15 seconds") is unmeetable.
- **Impact:** Acceptance testing for alert routing always fails. Governance documents and implementation are fundamentally misaligned on alert destination.
- **Verification:** CONFIRMED
- **Blocker for:** None (documentation/governance issue, not runtime code blocker)
- **Source findings:** P2-AUD-R1-016 (architecture), P2-EVD-007 (evidence), P2-NF-R1-002 (notification), P2-PC-R1-009 (permissions)

### P2-BUG-004 [CRITICAL] deploy/discord/guinevere-discord.service references non-existent .env.discord.sops with wrong format flags

- **Dimension:** Runtime-Config, Security/Secrets
- **File:** `deploy/discord/guinevere-discord.service` lines 13-15
- **Description:** `ExecStartPre` references `secrets/.env.discord.sops` with `--input-type dotenv --output-type dotenv`. This file does NOT exist. The actual encrypted file is `secrets/discord-secrets.enc.yaml` (SOPS YAML format, not dotenv). The unit would fail to start with file-not-found on ExecStartPre. Additionally, even if the file existed, the `--input-type dotenv` flag is wrong for a YAML file.
- **Impact:** The deploy-ready service unit is broken by design. Any activation attempt fails immediately.
- **Verification:** CONFIRMED
- **Blocker for:** None currently (service is masked per P2-022), but blocks any future reactivation
- **Source findings:** P2-AUD-R1-005 (architecture), P2-AUD-R1-011 (architecture), P2-RC-R1-002 (runtime), P2-EVD-005 (evidence), P2-EVD-014 (evidence)

---

## HIGH

### P2-BUG-005 [HIGH] systemd/guinevere-discord.service references non-existent plaintext .env.discord (also affects shadow-monitor)

- **Dimension:** Runtime-Config, Security
- **Files:** `systemd/guinevere-discord.service:13`, `systemd/guinevere-shadow-monitor.service:13`
- **Description:** Both units reference `EnvironmentFile=/home/guinevere/code/guinevere/.env.discord` which does not exist in the repo. The `systemd/` version has no SOPS decrypt, no PrivateTmp, no shred -- the insecure variant. If someone deploys using the `systemd/` template, either the service fails (file missing) or the operator must create a plaintext token file.
- **Impact:** Broken service units that would require a plaintext token on disk if deployed.
- **Verification:** CONFIRMED
- **Blocker for:** None currently (masked), blocks future reactivation
- **Source findings:** P2-RC-R1-001 (runtime), P2-RC-R1-004 (runtime), P2-RC-R2-NEW-001 (runtime R2), P2-AUD-R1-005 partial (architecture), P2-SEC-R1-002 (security)

### P2-BUG-006 [HIGH] Two conflicting hermes-gateway.service units (three variants total)

- **Dimension:** Runtime-Config, Evidence/Docs
- **Files:** `systemd/hermes-gateway.service`, `scripts/hermes-gateway.service`, `vps-mirror/systemd-live/hermes-gateway.service`
- **Description:** Three copies with different ExecStart and EnvironmentFile combinations:
  - `systemd/`: `hermes --config .../config.yaml gateway` + `.env.hermes`
  - `scripts/`: `hermes gateway run --accept-hooks` + `~/.hermes/.env`
  - `vps-mirror/live`: `hermes gateway run --accept-hooks` + `.env.hermes` (hybrid)
  The VPS live unit is a hybrid of the other two. No single file matches another exactly.
- **Impact:** Confusion about canonical execution model. Deploying from wrong template causes start failure or wrong config.
- **Verification:** CONFIRMED
- **Blocker for:** P24 (Hermes fork -- must reconcile before merge)
- **Source findings:** P2-AUD-R1-015 (architecture), P2-RC-R1-005 (runtime), P2-EVD-009 (evidence)

### P2-BUG-007 [HIGH] Command count four-way drift: code=49, PROGRESS=35, CHECKLIST=33, hermes_catalog=39

- **Dimension:** Evidence/Docs, Architecture, Permissions/Commands
- **Files:** `src/discord/_command_registry.py:406-407`, `CHECKLIST.md:265`, `PROGRESS.md:146`, `src/hermes_plugins/command_catalog.py`
- **Description:** `_command_registry.py` validates 49 commands via `require_canonical_registry()`. CHECKLIST.md says 33, PROGRESS.md says 35, hermes_plugins catalog has 39 (missing 10 commands: 3 health, 4 advanced memory, 3 loop monitoring). The old P2-AUDIT-COMPLETE.md says 35. cmd_help.py docstring says 33. cmd_help.py uses the 39-command catalog, so /help shows 10 fewer commands than registered.
- **Impact:** Users cannot discover 10 commands via /help. Verification scripts using old counts fail. Documentation is unreliable.
- **Verification:** CONFIRMED
- **Blocker for:** None (displays correctly via Discord sync; only help/docs are wrong)
- **Source findings:** P2-AUD-R1-004 (architecture), P2-RC-R1-010 (runtime), P2-EVD-002 (evidence), P2-EVD-011 (evidence), P2-PC-R1-002 (permissions), P2-PC-R1-003 (permissions), P2-PC-R1-005 (permissions)

### P2-BUG-008 [HIGH] cmd_pc.py (445 lines) completely unwired -- dead code

- **Dimension:** Permissions/Commands, Architecture
- **File:** `src/discord/cmd_pc.py` (444 lines)
- **Description:** Fully implemented P15-010 Windows daemon status command with auth guard, 6 injectable data gatherers, 15 try/except blocks for graceful degradation. NOT in `_command_registry.py`, NOT imported in `_entrypoint.py`, NOT in `command_catalog.py`. The /pc command does not exist at runtime.
- **Impact:** 444 lines of dead code. P15-010 feature is MIA at runtime.
- **Verification:** CONFIRMED
- **Blocker for:** None
- **Source findings:** P2-AUD-R1-023 (architecture), P2-AUD-R2 (architecture R2), P2-PC-R2-001 (permissions R2)

### P2-BUG-009 [HIGH] Plaintext cloud credentials in secrets/backup/ on disk

- **Dimension:** Security/Secrets
- **Files:** `secrets/backup/restic-password-plaintext.env`, `secrets/backup/idcloudhost-s3-plaintext.env`, `secrets/backup/cloudflare-r2-plaintext.env`
- **Description:** Three files contain live production credentials in plaintext: restic repository password, IDCloudHost S3 access keys, Cloudflare R2 access keys. The `secrets/backup/README.md` says to "shred the plaintext files" after re-encrypting, but they remain. All files are git-ignored by `secrets/` rule.
- **Impact:** Filesystem compromise exposes backup repository password, primary backup target (IDCloudHost S3), and secondary backup target (Cloudflare R2).
- **Verification:** CONFIRMED
- **Blocker for:** P19 (multi-project secrets scope)
- **Source findings:** P2-RC-R2-NEW-002 (runtime R2), P2-SEC-R1-004 (security)

### P2-BUG-010 [HIGH] Administrator permission still active on Discord bot with no active reduction mechanism

- **Dimension:** Security/Secrets, Permissions/Commands
- **Files:** `CHECKLIST.md:290`, `src/_deprecated/hermes-migration-phase-7/permissions.py:424-456`
- **Description:** CHECKLIST.md explicitly marks "No ADMINISTRATOR permission on bot" as NOT satisfied. The `review_admin_scope()` function exists only in the deprecated (and broken) permissions.py. The active `_auth_guard.py` (23 lines) only checks guild owner identity. No active mechanism enforces least-privilege.
- **Impact:** If the bot token is compromised, the attacker has full guild administrator access (ban/kick, manage roles, all channels, all permissions).
- **Verification:** CONFIRMED
- **Blocker for:** P22 (raw/full access -- must resolve before granting broader permissions)
- **Source findings:** P2-SEC-R1-005 (security), P2-PC-R1-006 (permissions)

### P2-BUG-011 [HIGH] notifications.py bare `import discord` at line 240 contradicts lazy-import design

- **Dimension:** Architecture, Permissions/Commands, Runtime-Config
- **File:** `src/discord/notifications.py:240`
- **Description:** Module defines lazy `importlib.import_module("discord")` pattern, then has a bare `import discord  # noqa: E402  # isort: skip` at the bottom of the file. This executes at import time. If discord.py is absent, the module crashes on import. The module is currently dead code (never imported by production), so the crash is latent, but any future import triggers it.
- **Impact:** Latent import-time crash risk in non-Discord contexts (tests, non-bot processes). Design contradiction.
- **Verification:** CONFIRMED
- **Blocker for:** None (module is dead code currently)
- **Source findings:** P2-AUD-R1-002 (architecture), P2-AUD-R1-006 (architecture), P2-RC-R1-008 (runtime), P2-PC-R1-004 (permissions), P2-SEC-R1-008 (security), P2-PC-R2-003 (permissions R2)

### P2-BUG-012 [HIGH] Permissions module in deprecated/ has ImportError for non-existent guild_setup

- **Dimension:** Permissions/Commands
- **File:** `src/_deprecated/hermes-migration-phase-7/permissions.py:18-19`
- **Description:** `from src.discord.guild_setup import CHANNELS, get_token` -- `src/discord/guild_setup.py` does NOT exist. Only the deprecated copy exists at `src/_deprecated/hermes-migration-phase-7/guild_setup.py`. Any execution of this module crashes with ImportError. All P2-007/P2-008/P2-009 permission code (channel overwrites, @everyone deny, append-only, OAuth least-privilege) is effectively dead.
- **Impact:** The entire channel-level permission management system is broken and inaccessible.
- **Verification:** CONFIRMED
- **Blocker for:** P22 (raw/full access -- permission enforcement needed)
- **Source findings:** P2-PC-R1-001 (permissions)

### P2-BUG-013 [HIGH] hermes_plugins command_catalog.py missing 10 commands -- /help incomplete

- **Dimension:** Permissions/Commands, Architecture
- **File:** `src/hermes_plugins/command_catalog.py`
- **Description:** The catalog has 39 commands (8 categories). The authoritative registry has 49 (9 categories). Missing: health-report, health-trend, health-baseline (P14), memory-stats, memory-review, memory-schedule, memory-decay (P18), loop-status, loop-cost, loop-history (P5). cmd_help.py uses this catalog for /help output.
- **Impact:** Users cannot discover 10 commands via /help. Help embed footer shows wrong count.
- **Verification:** CONFIRMED
- **Blocker for:** None
- **Source findings:** P2-AUD-R1-009 (architecture), P2-PC-R1-002 (permissions), P2-PC-R1-005 (permissions)

### P2-BUG-014 [HIGH] .env.hermes and ~/.hermes/.env do not exist in repo; .env.discord also missing

- **Dimension:** Runtime-Config
- **Files:** `.env.hermes`, `.hermes/.env`, `.env.discord`
- **Description:** All three env files referenced by service units are absent from the repo. The hermes-gateway.service references `.env.hermes` (systemd/) or `~/.hermes/.env` (scripts/). The discord service references `.env.discord`. None exist. Fresh clone + deploy would fail for all three services.
- **Impact:** No clean-clone deployment path works for any Discord or Hermes service unit.
- **Verification:** CONFIRMED
- **Blocker for:** None (VPS has them on disk)
- **Source findings:** P2-RC-R1-009 (runtime), P2-EVD-019 (evidence), P2-AUD-R1-005 (architecture)

### P2-BUG-015 [HIGH] Gotify deployment has no SOPS-encrypted token, no systemd unit, no runtime evidence

- **Dimension:** Notification/Fallback
- **Files:** `docs/setup-evidence/P2/STEP-P2-020/docker-compose.yml`, `src/discord/gotify_fallback.py:49`
- **Description:** Gotify has only a Docker compose artifact. No `secrets/gotify.enc.yaml` exists (operations doc references it). No systemd unit. No VPS health check evidence. `GOTIFY_APP_TOKEN` env var is never set in any service unit. The fallback silently returns False when the token is empty.
- **Impact:** Gotify fallback is non-functional in practice. No alert delivery via Gotify.
- **Verification:** NEEDS-RUNTIME (Docker container may be running on VPS without systemd)
- **Blocker for:** None
- **Source findings:** P2-NF-R1-003 (notification), P2-NF-R1-005 (notification), P2-NF-R1-006 (notification)

### P2-BUG-016 [HIGH] Raw Discord action paths bypass HARD STOP / consent / safety gates

- **Dimension:** Security/Secrets
- **Files:** `src/core/api/routes.py:314-320`, `src/life_kernel/discord_rest_client.py`, `hermes-config/hooks/finance_hook.py:150-169`
- **Description:** Multiple components send Discord messages via direct REST API, bypassing the HARD STOP / consent / safety framework: alertmanager webhook, P20 dashboard publisher, finance hooks (can also delete messages). During HARD STOP safe mode, these paths continue operating.
- **Impact:** Safe mode does not fully silence Discord interactions. Dashboard updates, alerts, and finance operations may continue posting during HARD STOP.
- **Verification:** CONFIRMED
- **Blocker for:** P22 (raw/full access -- safety gates must cover all write paths), P23 (embodied ops)
- **Source findings:** P2-SEC-R1-007 (security)

---

## MEDIUM

### P2-BUG-017 [MEDIUM] Stale docstring: cmd_safeword.py says "No bot.py listener exists yet" but async version IS wired

- **Dimension:** Architecture, Permissions/Commands, Notification/Fallback
- **File:** `src/discord/cmd_safeword.py:597-601`
- **Description:** Sync version `handle_safeword_message` docstring says "No bot.py listener exists yet. This function is callable and documented but inactive until P2-017 wires it." The async version `handle_safeword_message_async` IS wired in `_entrypoint.py` line 155. The docstring references deprecated `bot.py`.
- **Impact:** Misleading to developers; may cause redundant wiring attempts.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-018 (architecture), P2-EVD-015 (evidence), P2-PC-R1-010 (permissions), P2-NF-R1-011 (notification), P2-RC-R1-014 (runtime)

### P2-BUG-018 [MEDIUM] Three surveillance cmd modules duplicate is_faiz_interaction instead of importing from _auth_guard

- **Dimension:** Permissions/Commands
- **Files:** `src/discord/cmd_surveillance_pause.py:58-73`, `src/discord/cmd_surveillance_resume.py:58-73`, `src/discord/cmd_surveillance_status.py:48-63`
- **Description:** Three modules define their own `is_faiz_interaction()` with identical logic instead of importing from `_auth_guard`. All 42 other modules correctly import. Maintenance hazard: auth logic changes would silently skip these 3 modules.
- **Impact:** Maintenance risk; duplicated code; auth changes not propagated.
- **Verification:** CONFIRMED
- **Source findings:** P2-PC-R2-002 (permissions R2)

### P2-BUG-019 [MEDIUM] _entrypoint.py stub loop is dead code; creates duplicate-registration trap

- **Dimension:** Permissions/Commands, Architecture
- **File:** `src/discord/_entrypoint.py:54, 544-549`
- **Description:** `_STUB_PHASE` is empty dict. The stub loop iterates COMMAND_SPECS and generates stubs for names NOT in `core_names`. Since `core_names` includes all 49 commands, the loop never fires. `_STUB_PHASE` and `_make_stub_callback` are dead code. Trap: adding a new CommandSpec without updating `core_names` causes duplicate Discord registrations.
- **Impact:** Dead code with maintenance trap.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-013 (architecture), P2-AUD-R1-033 (architecture), P2-PC-R2-004 (permissions R2)

### P2-BUG-020 [MEDIUM] GUINEVERE_API_KEY handled inconsistently across cmd modules (2 silent, 5 warn)

- **Dimension:** Runtime-Config
- **Files:** `src/discord/cmd_loops.py:42`, `src/discord/cmd_evidence.py:118`, `src/discord/cmd_loop_start.py:344-349`, `cmd_loop_stop.py:385-390`, `cmd_loop_pause.py:57-62`, `cmd_loop_resume.py:58-63`, `cmd_loop_priority.py:81-86`
- **Description:** cmd_loops and cmd_evidence pass an empty API key silently (no empty-check). 5 other loop cmd modules check for empty and send warning embed. Inconsistent handling.
- **Impact:** /loops and /evidence commands silently fail when GUINEVERE_API_KEY is unset (opaque API errors).
- **Verification:** CONFIRMED
- **Source findings:** P2-RC-R2-NEW-004 (runtime R2)

### P2-BUG-021 [MEDIUM] 8+ modules hardcode localhost with no env-var override

- **Dimension:** Runtime-Config
- **Files:** `cmd_casual.py:38`, `cmd_clear_cache.py:40`, `cmd_consent.py:45`, `cmd_focus.py:45`, `cmd_punishment.py:60`, `cmd_reward.py:46`, `cmd_health_check.py:35`, `gotify_fallback.py:32`
- **Description:** At least 8 modules hardcode `localhost` and/or specific ports (6380 for Redis, 8000 for health API, 8081 for Gotify) with no env-var fallback. Prevents reconfiguration without code changes.
- **Impact:** Architectural constraint preventing scaling or reconfiguration.
- **Verification:** CONFIRMED
- **Source findings:** P2-RC-R2-NEW-005 (runtime R2)

### P2-BUG-022 [MEDIUM] secrets/ directory entirely git-ignored; encrypted production secrets NOT tracked

- **Dimension:** Runtime-Config, Security
- **File:** `.gitignore:24` (`secrets/`)
- **Description:** `git ls-files secrets/` returns empty. The SOPS-encrypted `discord-secrets.enc.yaml` exists on disk but is NOT git-tracked. Fresh clone has zero secrets. Combined with P2-BUG-004 (deploy unit references wrong path), the deploy flow is doubly broken.
- **Impact:** Disaster recovery requires out-of-band secret distribution. VPS rebuild from git clone would have no encrypted secrets.
- **Verification:** CONFIRMED
- **Source findings:** P2-RC-R2-NEW-003 (runtime R2)

### P2-BUG-023 [MEDIUM] _build_safeword_fields() ignores handler state -- embed always shows static text

- **Dimension:** Architecture
- **File:** `src/discord/cmd_safeword.py:330-348`
- **Description:** `_build_safeword_fields(handler: HardStopHandler)` takes handler parameter but returns hardcoded values: "Safe mode active" always, "Paused" always, "Y0" always. The handler parameter is unused. `safeword_callback` at line 567 calls `handler.check("safeword")` but discards the return value.
- **Impact:** /safeword always shows "Safe mode active" regardless of actual state. If recovery was just triggered, user sees misleading "Safe mode active" embed.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-029 (architecture R2 upgrade from LOW to MEDIUM), P2-AUD-R1-050 (architecture)

### P2-BUG-024 [MEDIUM] Shadow pipeline disabled by default with no deployment mechanism

- **Dimension:** Architecture
- **File:** `src/discord/_entrypoint.py:107-110`
- **Description:** ShadowPipeline defaults to `enabled=false`, `traffic_pct=0`. No service unit, cron, or deployment script enables shadow mode. The shadow monitor is a standalone script requiring manual invocation.
- **Impact:** Hermes shadow comparison for migration is effectively dead code.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-012 (architecture)

### P2-BUG-025 [MEDIUM] phase-2-discord.md lists 35 plugin files that do not exist

- **Dimension:** Evidence/Docs
- **File:** `docs/setup-evidence/hermes-migration/phase-2-discord.md:143-187`
- **Description:** Migration document lists 35 `plugins/*_plugin.py` files. NONE exist. The actual `src/hermes_plugins/` uses `commands_*/` subdirectory structure, not flat plugin files.
- **Impact:** Migration cannot proceed as documented. Entirely aspirational plan.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-010 (architecture)

### P2-BUG-026 [MEDIUM] P2-002 CRITICAL finding from old audit is PARTIALLY RESOLVED -- reporting chain not closed

- **Dimension:** Evidence/Docs
- **Files:** `docs/audit/P2-AUDIT-COMPLETE.md:57-58`, `secrets/discord-secrets.enc.yaml`
- **Description:** Old audit's CRITICAL finding (encrypted secret missing) is partially fixed: `discord-secrets.enc.yaml` exists and IS SOPS-encrypted. But: (a) old audit still records CRITICAL FAIL, (b) naming mismatch (`enc.yaml` vs `.yaml`), (c) no `.env.discord.sops` for deploy unit, (d) file is not git-tracked.
- **Impact:** Misleading audit trail. Confusion about what is fixed.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-003 (architecture), P2-EVD-005 (evidence), P2-EVD-010 (evidence)

### P2-BUG-027 [MEDIUM] Multiple consumers share same DISCORD_BOT_TOKEN -- gateway collision risk

- **Dimension:** Security/Secrets
- **Files:** Multiple (6 consumers identified)
- **Description:** The same `DISCORD_BOT_TOKEN` is used by: standalone bot (masked), core REST publisher, Hermes gateway, alertmanager webhook, finance hooks, Hermes Discord adapter. If both standalone bot and Hermes gateway run simultaneously, Discord disconnects one due to token collision.
- **Impact:** Gateway session disconnection if both services are active. Complex token rotation.
- **Verification:** CONFIRMED
- **Source findings:** P2-SEC-R1-006 (security)

### P2-BUG-028 [MEDIUM] Channel count: 14 in channel-ids.yaml vs 13 documented; 3 ghost channels + 1 undocumented

- **Dimension:** Evidence/Docs, Runtime-Config
- **Files:** `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml`, `CHECKLIST.md:261`
- **Description:** channel-ids.yaml has 14 entries. CHECKLIST says 13. Extra channels: `rituals` (undocumented), `project-alpha-dev`, `project-alpha-docs`, `project-beta-dev` (ghost/prototype channels). The `guinevere-dev` channel is used as `guinevere-logs` by P20 but not renamed.
- **Impact:** Channel inventory inaccurate. Ghost channels consume Discord resources.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-008 (architecture), P2-EVD-003 (evidence), P2-RC-R1-011 (runtime), P2-PC-R1-007 (permissions), P2-SEC-R1-011 (security)

### P2-BUG-029 [MEDIUM] cmd_safeword.py sync version exists alongside async -- sync is dead code

- **Dimension:** Architecture
- **File:** `src/discord/cmd_safeword.py:591` (sync), `643` (async)
- **Description:** `handle_safeword_message` (sync) returns True/False but sends no Discord message. `handle_safeword_message_async` sends embed and reaction. Only async version is wired. Sync version is dead code with stale docstring.
- **Impact:** If someone wires the sync version by mistake, HARD STOP would consume messages without any visible response.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-026 (architecture)

### P2-BUG-030 [MEDIUM] send_alert() broad except swallows all errors identically

- **Dimension:** Notification/Fallback
- **File:** `src/discord/notifications.py:235-237`
- **Description:** Outer exception handler catches ALL exceptions, logs error, returns False. All failure modes are indistinguishable (channel not found vs network timeout vs auth failure). Unlike gotify_fallback which distinguishes error types.
- **Impact:** Impossible to diagnose configuration problems from error return alone.
- **Verification:** CONFIRMED
- **Source findings:** P2-NF-R1-007 (notification)

### P2-BUG-031 [MEDIUM] _entrypoint.py duplicate close() method -- first is dead code

- **Dimension:** Architecture
- **File:** `src/discord/_entrypoint.py:567-569` and `640-650`
- **Description:** `GuinevereBot` defines `async def close()` twice. Python uses the second definition. The first (simple `await super().close()`) is dead code. The second (full version with dashboard cleanup) is the active one.
- **Impact:** Future developers editing the first close() will find their changes don't take effect.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R2-001 (architecture R2 miss-hunt)

### P2-BUG-032 [MEDIUM] vps-mirror hermes-gateway.service is hybrid of two conflicting templates

- **Dimension:** Runtime-Config, Evidence/Docs
- **File:** `vps-mirror/systemd-live/hermes-gateway.service`
- **Description:** Uses `scripts/`'s ExecStart (`hermes gateway run --accept-hooks`) but `systemd/`'s EnvironmentFile (`.env.hermes`). Also uses `Wants=` instead of `Requires=` for dependencies. Doesn't match either canonical template exactly.
- **Impact:** Using vps-mirror as restore source produces a unit matching neither template.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R2-008 (architecture R2)

### P2-BUG-033 [MEDIUM] .env.example placeholder values not commented out for sensitive fields

- **Dimension:** Runtime-Config
- **File:** `.env.example:74`
- **Description:** Sensitive fields like `DISCORD_BOT_TOKEN=your-discord-bot-token-here` are not prefixed with `#`. Copying `.env.example` to `.env` sets placeholder values that pass `if not token:` checks, then fail cryptically at Discord API auth.
- **Impact:** Confusing error messages for new deployments instead of clear "token not set" failures.
- **Verification:** CONFIRMED
- **Source findings:** P2-RC-R2-NEW-010 (runtime R2)

---

## LOW

### P2-BUG-034 [LOW] cmd_help.py _CATEGORY_DISPLAY missing gmail and health categories

- **Dimension:** Permissions/Commands
- **File:** `src/discord/cmd_help.py:57-65`
- **Description:** Display map has 7 entries. Missing "gmail" and "health". Unknown categories fall through to `key.capitalize()` with no emoji.
- **Impact:** Gmail and health categories display without emoji in /help.
- **Verification:** CONFIRMED
- **Source findings:** P2-PC-R1-012 (permissions)

### P2-BUG-035 [LOW] command_catalog.py command_count() returns 39 instead of 49

- **Dimension:** Permissions/Commands
- **File:** `src/hermes_plugins/command_catalog.py:50-52`
- **Description:** `sum(len(cmds) for cmds in _COMMAND_CATEGORIES.values())` returns 39. Canonical count is 49.
- **Impact:** Downstream consumers get wrong count.
- **Verification:** CONFIRMED
- **Source findings:** P2-PC-R2-005 (permissions R2)

### P2-BUG-036 [LOW] require_canonical_registry() never called at startup

- **Dimension:** Permissions/Commands
- **File:** `src/discord/_command_registry.py:402-418`
- **Description:** The validation function (duplicate check, count check, payload length check) is never called by `_entrypoint.py` or any startup code. Only test files call it.
- **Impact:** Registry errors (duplicates, wrong count) not caught until Discord sync fails at runtime.
- **Verification:** CONFIRMED
- **Source findings:** P2-PC-R2-006 (permissions R2)

### P2-BUG-037 [LOW] notifications.py SEV routing uses channel NAME not ID

- **Dimension:** Notification/Fallback, Runtime-Config
- **File:** `src/discord/notifications.py:215`
- **Description:** `channel = discord_utils_local.get(channels, name=data.channel_name)` resolves by name, not snowflake ID. Channel renaming breaks all SEV alert routing silently.
- **Impact:** Silent notification loss if any channel is renamed.
- **Verification:** CONFIRMED
- **Source findings:** P2-RC-R2-NEW-006 (runtime R2), P2-PC-R2-007 (permissions R2)

### P2-BUG-038 [LOW] Gotify priority mapping inverted (SEV0=10 highest, SEV4=1 lowest)

- **Dimension:** Notification/Fallback, Architecture
- **File:** `src/discord/gotify_fallback.py:43`
- **Description:** SEV0 (informational, lowest severity 0-4) maps to Gotify priority 10 (highest). SEV4 (audit) maps to 1 (lowest). This seems inverted: informational alerts get maximum Gotify priority.
- **Impact:** Gotify shows SEV0 alerts at highest priority.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-049 (architecture), P2-PC-R2-008 (permissions R2)

### P2-BUG-039 [LOW] HARD STOP recovery only checks message.content -- ignores attachments, embeds, stickers

- **Dimension:** Architecture
- **Files:** `src/discord/cmd_safeword.py:667-670`, `src/discord/_entrypoint.py:678`
- **Description:** Both detection and recovery only examine `message.content`. Attachments, embeds, stickers, and system content are not checked.
- **Impact:** Recovery phrases in non-text content are invisible to the detector.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-021 (architecture)

### P2-BUG-040 [LOW] Shadow pipeline fire-and-forget with no error reporting to operator

- **Dimension:** Architecture
- **File:** `src/discord/hermes_conversational.py:591-595`
- **Description:** `asyncio.create_task(shadow.shadow_forward(...))` discards the coroutine result. No `add_done_callback`, no await. Shadow comparison failures are logged at DEBUG only.
- **Impact:** Silent data loss for migration comparison pipeline.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-022 (architecture)

### P2-BUG-041 [LOW] vps-mirror/systemd-live has no guinevere-discord.service snapshot

- **Dimension:** Architecture, Evidence/Docs
- **File:** `vps-mirror/systemd-live/`
- **Description:** No discord service unit in vps-mirror (intentional: service is masked per ADR-035/P2-022). But no metadata file documenting the mask decision either.
- **Impact:** VPS restore does not include the masked service definition.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-024 (architecture)

### P2-BUG-042 [LOW] scripts/ finance modules parse plaintext .env files for DISCORD_BOT_TOKEN

- **Dimension:** Security/Secrets
- **Files:** `scripts/finance_weekly_report.py:25-34`, `scripts/finance_dashboard_update.py:25-34`, `hermes-config/hooks/finance_hook.py:150-169`
- **Description:** Scripts open `~/.hermes/.env` and parse line-by-line for `DISCORD_BOT_TOKEN`. Finance hooks fall back to parsing multiple `.env` files. Bypasses SOPS decryption.
- **Impact:** Token exists in plaintext on disk accessible to any process running as the guinevere user.
- **Verification:** CONFIRMED
- **Source findings:** P2-SEC-R1-003 (security)

### P2-BUG-043 [LOW] notifications.py try/except catches all Exception instead of ImportError

- **Dimension:** Runtime-Config, Architecture
- **File:** `src/discord/notifications.py:20-22`
- **Description:** `except Exception:` catches SyntaxError, KeyboardInterrupt, etc. PEP 8 recommends `except ImportError:` specifically. Could mask installation issues.
- **Impact:** Masks root cause during development/testing.
- **Verification:** CONFIRMED
- **Source findings:** P2-RC-R1-015 (runtime)

### P2-BUG-044 [LOW] cmd_health_check.py calls internal API without auth headers

- **Dimension:** Runtime-Config
- **File:** `src/discord/cmd_health_check.py:45-49`
- **Description:** `client.get(HEALTH_URL)` with no auth headers, unlike other cmd modules that send `X-Guinevere-API-Key`.
- **Impact:** Returns 401/403 if API enforces auth on /health. Inconsistent with other modules.
- **Verification:** CONFIRMED
- **Source findings:** P2-RC-R2-NEW-007 (runtime R2)

### P2-BUG-045 [LOW] gmail_reactions.py has hardcoded fallback channel ID not in channel-ids.yaml

- **Dimension:** Runtime-Config
- **File:** `src/discord/listeners/gmail_reactions.py:54`
- **Description:** Hardcoded fallback `1515062963705221130` when `GMAIL_TARGET_CHANNEL_ID` env var is unset. This ID is not documented in channel-ids.yaml.
- **Impact:** If env var is absent, Gmail reaction listener silently targets an undocumented channel.
- **Verification:** CONFIRMED
- **Source findings:** P2-RC-R2-NEW-008 (runtime R2)

### P2-BUG-046 [LOW] PRD v2.2 references #alerts channel that does not exist

- **Dimension:** Evidence/Docs
- **File:** `docs/00-core/01-PRD_v2.2.md:55`
- **Description:** PRD lists `#alerts` as a Discord channel. Does not exist in channel-ids.yaml or runtime.
- **Impact:** Governance document misalignment.
- **Verification:** CONFIRMED
- **Source findings:** P2-RC-R1-013 (runtime)

### P2-BUG-047 [LOW] SRS v1.0 and FSD v1.0 consistently reference #alerts channel (7+5 references)

- **Dimension:** Evidence/Docs
- **Files:** `docs/10-governance/12-SRS_v1.0.md` (7 refs), `docs/10-governance/13-FSD_v1.0.md` (5 refs)
- **Description:** 12 total references to `#alerts` across two governance documents. Channel does not exist.
- **Impact:** Acceptance criteria and requirements traceability broken for alert routing.
- **Verification:** CONFIRMED
- **Source findings:** P2-NF-R1-008 (notification)

### P2-BUG-048 [LOW] listeners/x_reactions.py exists but is never wired

- **Dimension:** Architecture
- **File:** `src/discord/listeners/x_reactions.py`
- **Description:** X Poster reaction listener file exists but is never imported in `_entrypoint.py`. Dead code alongside gmail_reactions.py (which IS wired).
- **Impact:** X Post reactions are not handled.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R2-006 (architecture R2 miss-hunt)

### P2-BUG-049 [LOW] loops/ directory in src/discord/ is empty stub -- only re-exports from x_poster

- **Dimension:** Architecture
- **File:** `src/discord/loops/__init__.py`
- **Description:** Contains only `__init__.py` which re-exports `create_dashboard` from `src.x_poster.discord.dashboard`. No actual loop implementations.
- **Impact:** Misleading directory name; placeholder for future use.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R2-005 (architecture R2 miss-hunt)

### P2-BUG-050 [LOW] notifications.py send_alert() does not validate channel exists before sending

- **Dimension:** Notification/Fallback
- **File:** `src/discord/notifications.py:215-218`
- **Description:** If channel name is not found, logs error and returns False. No fallback to a known-good channel or escalation path.
- **Impact:** Misconfigured channel name results in silent notification loss.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-028 (architecture)

### P2-BUG-051 [LOW] _command_registry.py magic constant 49 has no explanatory comment

- **Dimension:** Architecture
- **File:** `src/discord/_command_registry.py:406`
- **Description:** `if len(names) != 49:` -- no comment explaining where 49 came from. Given history of drift (33->35->42->46->49), this is a maintenance risk.
- **Impact:** Adding P19/P21 commands without updating this assertion causes hard crash.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R2-010 (architecture R2 miss-hunt)

### P2-BUG-052 [LOW] .env.example missing GOTIFY_URL and GOTIFY_ADMIN_PASSWORD placeholders

- **Dimension:** Runtime-Config
- **File:** `.env.example`
- **Description:** `.env.example` has `GOTIFY_APP_TOKEN` (line 214, confirmed by R2) but is missing `GOTIFY_URL` and `GOTIFY_ADMIN_PASSWORD`. New developers miss these config vars.
- **Impact:** New VPS setup would lack Gotify configuration guidance.
- **Verification:** CONFIRMED
- **Source findings:** P2-RC-R1-017 partial (runtime, R2 corrected GOTIFY_APP_TOKEN claim)

---

## COSMETIC

### P2-BUG-053 [COSMETIC] Pervasive counting discrepancies across entire codebase

- **Dimension:** Architecture, Evidence/Docs
- **Files:** Multiple
- **Description:** Summary of stale numbers: `_auth_guard.py` says 32 modules (now 45+), `_entrypoint.py` says 13+20 (now 49+0), CHECKLIST says 33 (now 49), PROGRESS says 35 (now 49), old audit says 35 (now 49), hermes_plugins says 39 (now 49), channel count 13 (now 14), cmd_help says 7 categories (now 9).
- **Impact:** No stated number can be trusted without cross-checking.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-030 (architecture), P2-PC-R1-013 (permissions), P2-SEC-R1-012 (security)

### P2-BUG-054 [COSMETIC] _entrypoint.py bare except catching AttributeError for old discord.py compat

- **Dimension:** Architecture
- **File:** `src/discord/_entrypoint.py:758-761`
- **Description:** Catches `AttributeError` broadly to support discord.py <2.4. With 2.7.1 installed, this is dead code. Broad catch could mask unrelated AttributeErrors.
- **Impact:** Safety concern: unrelated AttributeErrors silently caught.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-031 (architecture)

### P2-BUG-055 [COSMETIC] _entrypoint.py GUILD_ID comment references non-existent guild_setup.py

- **Dimension:** Architecture
- **File:** `src/discord/_entrypoint.py:48`
- **Description:** Comment says "Canonical guild ID from guild_setup.py" -- no such file exists.
- **Impact:** Misleading reference.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-032 (architecture)

### P2-BUG-056 [COSMETIC] gotify_fallback.py hardcoded GOTIFY_URL not configurable via env var

- **Dimension:** Architecture, Runtime-Config
- **File:** `src/discord/gotify_fallback.py:32`
- **Description:** `GOTIFY_URL` is hardcoded. No env var override.
- **Impact:** Port/host changes require code edits.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-035 (architecture), P2-PC-R2-008 (permissions R2)

### P2-BUG-057 [COSMETIC] cmd_safeword.py P2-017 step references are stale

- **Dimension:** Architecture
- **File:** `src/discord/cmd_safeword.py:20, 597`
- **Description:** Comments reference "P2-017" as the wiring step. Wiring is done in `_entrypoint.py`, not a specific P2 step.
- **Impact:** Misleading step references.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-036 (architecture)

### P2-BUG-058 [COSMETIC] _startup.py docstring shows wiring pattern already implemented

- **Dimension:** Architecture
- **File:** `src/discord/_startup.py:18-21`
- **Description:** Docstring shows code block for wiring into bot.py. This is already done in `_entrypoint.py:625`.
- **Impact:** Stale documentation.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-037 (architecture)

### P2-BUG-059 [COSMETIC] _entrypoint.py imports create_dashboard from x_poster at module top

- **Dimension:** Architecture
- **File:** `src/discord/_entrypoint.py:34`
- **Description:** Module-level `from src.x_poster.discord import create_dashboard`. If x_poster has import-time side effects, they execute on bot startup.
- **Impact:** Bot startup depends on x_poster module being healthy at import time.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-039 (architecture)

### P2-BUG-060 [COSMETIC] FOOTER_TEXT says "System Alert" but used for status and audit channels

- **Dimension:** Architecture, Notification/Fallback
- **File:** `src/discord/notifications.py:31`
- **Description:** Footer is "Guinevere de Baroque System Alert" but module routes to #guinevere-status and #audit-log which are not alert channels.
- **Impact:** Context slightly off for non-alert notifications.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-040 (architecture), P2-NF-R1-010 (notification)

### P2-BUG-061 [COSMETIC] send_alert() silently drops non-thread_name kwargs

- **Dimension:** Architecture, Notification/Fallback
- **File:** `src/discord/notifications.py:201, 227`
- **Description:** `**kwargs` accepted but only `thread_name` is used. All other kwargs silently ignored.
- **Impact:** Callers passing unexpected kwargs get no feedback.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-041 (architecture), P2-NF-R1-012 (notification)

### P2-BUG-062 [COSMETIC] _entrypoint.py imports finance hook at module top

- **Dimension:** Architecture
- **File:** `src/discord/_entrypoint.py:33`
- **Description:** `from src.finance.hook import on_message as process_finance_message` at module level. Bot startup depends on finance module health.
- **Impact:** Finance module import failure prevents Discord bot startup.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-042 (architecture), P2-AUD-R2-004 (architecture R2)

### P2-BUG-063 [COSMETIC] gotify_fallback.py 24-line structlog fallback emulation

- **Dimension:** Architecture
- **File:** `src/discord/gotify_fallback.py:7-31`
- **Description:** Complex 24-line fallback for when structlog is not installed. Adds maintenance burden for rare case.
- **Impact:** Dead/complex fallback code.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-043 (architecture)

### P2-BUG-064 [COSMETIC] _intents.py get_intents() does not cache result

- **Dimension:** Architecture
- **File:** `src/discord/_intents.py:71-96`
- **Description:** Creates intents from scratch on every call. Single bot instance makes this negligible.
- **Impact:** None for single-bot deployments.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-044 (architecture)

### P2-BUG-065 [COSMETIC] command_count() function unused in production code

- **Dimension:** Architecture
- **File:** `src/discord/_command_registry.py:375-378`
- **Description:** `command_count()` returns 49 but is only called in test files, not production.
- **Impact:** Utility function without callers.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-045 (architecture)

### P2-BUG-066 [COSMETIC] P2-FIX-PLAN.md Phase 2.2 not done; Phase 4 not started

- **Dimension:** Evidence/Docs
- **File:** `docs/audit/P2-FIX-PLAN.md`
- **Description:** Phase 2.1 done, 2.2 not done (PROGRESS.md count). Phase 3 (channel cleanup) not done. Phase 4 (automation) not done.
- **Impact:** Fix plan partially completed.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-046 (architecture), P2-EVD-011 (evidence)

### P2-BUG-067 [COSMETIC] hermes_conversational.py hardcodes GUINEVERE_CHAT_CHANNEL_ID

- **Dimension:** Architecture
- **File:** `src/discord/hermes_conversational.py:50`
- **Description:** Channel snowflake `1_510_914_600_777_023_659` hardcoded. Channel deletion+recreation changes the ID.
- **Impact:** Hard-coded dependency on channel snowflake.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-048 (architecture)

### P2-BUG-068 [COSMETIC] Recovery check could catch recovery phrases from slash commands

- **Dimension:** Architecture
- **File:** `src/discord/_entrypoint.py:678`
- **Description:** `handler.check_recovery(message.content)` on raw content. A message like "aku sudah okay" could be misidentified as recovery.
- **Impact:** Low-exploitability edge case.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-051 (architecture)

### P2-BUG-069 [COSMETIC] deploy/env/ has only WhatsApp template, no Discord or Hermes templates

- **Dimension:** Runtime-Config
- **File:** `deploy/env/.env.whatsapp.template`
- **Description:** No Discord or Hermes env template in deploy/env/.
- **Impact:** Organizational inconsistency.
- **Verification:** CONFIRMED
- **Source findings:** P2-RC-R1-016 (runtime)

### P2-BUG-070 [COSMETIC] systemd/ vs deploy/discord/ discrepancy documented nowhere

- **Dimension:** Runtime-Config, Evidence/Docs
- **Files:** `systemd/guinevere-discord.service`, `deploy/discord/guinevere-discord.service`
- **Description:** No README explaining why two drastically different copies of the same service unit exist or which is canonical.
- **Impact:** Operator confusion about which to deploy.
- **Verification:** CONFIRMED
- **Source findings:** P2-RC-R1-018 (runtime)

### P2-BUG-071 [COSMETIC] Old P2-AUDIT-COMPLETE.md CRITICAL finding still shows as open

- **Dimension:** Evidence/Docs
- **File:** `docs/audit/P2-AUDIT-COMPLETE.md`
- **Description:** Table still shows P2-002 as CRITICAL FAIL. Should be marked partially resolved.
- **Impact:** Misleading audit report.
- **Verification:** CONFIRMED
- **Source findings:** P2-RC-R1-019 (runtime), P2-EVD-010 (evidence)

### P2-BUG-072 [COSMETIC] to_discord_embed() asymmetric error handling (add_field has getattr guard, set_footer does not)

- **Dimension:** Notification/Fallback
- **File:** `src/discord/notifications.py:190-198`
- **Description:** `add_field` uses `getattr(callable)` pattern, but `set_footer` is called directly. Inconsistent defensive design.
- **Impact:** Minor asymmetry; only manifests with non-standard embed factories.
- **Verification:** CONFIRMED
- **Source findings:** P2-NF-R1-012 (notification)

### P2-BUG-073 [COSMETIC] GUILD_ID hardcoded, DISCORD_GUILD_ID in .env.example is ignored

- **Dimension:** Runtime-Config
- **Files:** `src/discord/_entrypoint.py:48`, `.env.example:77`
- **Description:** `.env.example` has `DISCORD_GUILD_ID` placeholder but code uses hardcoded constant. Documentation/code mismatch.
- **Impact:** Developers assume guild ID is configurable but it isn't.
- **Verification:** CONFIRMED
- **Source findings:** P2-RC-R2-NEW-009 (runtime R2)

### P2-BUG-074 [COSMETIC] phase-2-discord.md Gantt chart has no dates

- **Dimension:** Evidence/Docs
- **File:** `docs/setup-evidence/hermes-migration/phase-2-discord.md`
- **Description:** Gantt chart (Day 1-8) has no start date. Document is entirely aspirational.
- **Impact:** None. Planning document.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-052 (architecture)

### P2-BUG-075 [COSMETIC] Missing auditor-gate.md in P2 step evidence directories

- **Dimension:** Evidence/Docs
- **File:** `docs/setup-evidence/P2/STEP-P2-*/`
- **Description:** Later phases include auditor-gate.md in step evidence dirs. P2 directories do not.
- **Impact:** Evidence in different location than later-phase conventions.
- **Verification:** CONFIRMED
- **Source findings:** P2-EVD-012 (evidence)

### P2-BUG-076 [COSMETIC] cmd_help.py docstring says "33 commands" and "7 categories"

- **Dimension:** Permissions/Commands, Evidence/Docs
- **File:** `src/discord/cmd_help.py:4`
- **Description:** Doubly stale: 33->49 commands, 7->9 categories.
- **Impact:** Misleading docstring.
- **Verification:** CONFIRMED
- **Source findings:** P2-EVD-013 (evidence), P2-PC-R1-013 (permissions), P2-AUD-R2-007 (architecture R2)

### P2-BUG-077 [COSMETIC] _auth_guard.py docstring says "32 command callback modules"

- **Dimension:** Architecture
- **File:** `src/discord/_auth_guard.py:5`
- **Description:** Should be "45+" not "32".
- **Impact:** Stale documentation.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-017 (architecture)

### P2-BUG-078 [COSMETIC] _entrypoint.py class docstring says "13 wired + 20 stubs"

- **Dimension:** Architecture
- **File:** `src/discord/_entrypoint.py:89-91`
- **Description:** All 49 commands are wired, 0 stubs. Docstring is stale.
- **Impact:** Misleading documentation.
- **Verification:** CONFIRMED
- **Source findings:** P2-AUD-R1-013 (architecture), P2-PC-R1-015 (permissions)

### P2-BUG-079 [COSMETIC] Old P2-AUDIT-COMPLETE.md Gotify port 8080 claim is stale

- **Dimension:** Evidence/Docs, Notification/Fallback
- **File:** `docs/audit/P2-AUDIT-COMPLETE.md:64`
- **Description:** Old audit says port 8080. Code and docker-compose consistently use 8081. Old audit claim is incorrect.
- **Impact:** Misleading historical record.
- **Verification:** CONFIRMED
- **Source findings:** P2-EVD-006 (evidence), P2-EVD-016 (evidence), P2-NF-R1-004 (notification)

---

## V2 LIVE VPS FINDINGS (2026-06-26)

These 5 findings were discovered during direct-SSH live VPS reconciliation. They are NOT from the original 6-dimension audit — they are live VPS findings that contradict or extend the original audit's assumptions.

### P2-BUG-080 [CRITICAL] Discord bot token in PLAINTEXT on live VPS — no SOPS encryption deployed

- **Dimension:** Security/Secrets, Runtime-Config
- **File:** `/home/guinevere/code/guinevere/.env.discord` (VPS live file, 808 bytes, chmod 600, owner guinevere)
- **Description:** Direct SSH to `guinevere-vps` confirmed the Discord bot token is stored in PLAINTEXT in `.env.discord`. The repo contains `secrets/discord-secrets.enc.yaml` (SOPS-encrypted) and the `deploy/discord/guinevere-discord.service` unit references `secrets/.env.discord.sops` (SOPS decrypt pattern), but NEITHER was ever deployed to the VPS. The VPS `secrets/` directory contains `age-key.txt`, `db-passwords.yaml`, `github-pat.yaml`, `redis-acl-passwords.yaml`, `redis-password.yaml`, `vnc-password.txt` — no `discord-secrets.enc.yaml`, no `.env.discord.sops`. The deployed `guinevere-discord.service` uses `EnvironmentFile=/home/guinevere/code/guinevere/.env.discord` (plaintext, no SOPS).
- **Impact:** The Discord bot token (and DB password, Redis password, and other credentials in the same file) are in plaintext on disk. Any filesystem compromise exposes all credentials. The SOPS encryption pipeline is a repo-only artifact that was never deployed.
- **VPS evidence:** `systemctl cat guinevere-discord.service` → `EnvironmentFile=/home/guinevere/code/guinevere/.env.discord`. `ls -la /home/guinevere/secrets/` → no discord file. `ls -la /home/guinevere/code/guinevere/.env.discord` → 808 bytes, chmod 600.
- **Verification:** CONFIRMED_ON_VPS (direct SSH, 2026-06-26 02:14 WIB)
- **V2 classification:** CONFIRMED_ON_VPS
- **Blocker for:** P19 (multi-project secrets), P24 (Hermes fork convergence)
- **Source findings:** Live VPS SSH direct (V2 reconciliation)

### P2-BUG-081 [HIGH] PROGRESS.md P2-022 claim "masked intentionally" is FALSE — standalone bot is active+enabled

- **Dimension:** Evidence/Docs, Architecture
- **Files:** `PROGRESS.md:158`, `/etc/systemd/system/guinevere-discord.service` (VPS)
- **Description:** PROGRESS.md:158 states `[x] **P2-022** guinevere-discord.service masked intentionally (Hermes Gateway handles Discord now — standalone bot deprecated post-ADR-035)`. Direct SSH proves this is FALSE: `systemctl is-enabled guinevere-discord.service` → `enabled`. `systemctl is-active guinevere-discord.service` → `active (running) since Thu 2026-06-25 19:45:01 WIB`. The service has been running continuously for 6+ hours. The `vps-mirror/systemd-live/` directory (which lacks a discord unit) was used as evidence in V1 — it was STALE.
- **Impact:** The V1 audit, the previous reconciliation, and all downstream analysis that depended on the "masked" assumption were wrong. The standalone bot IS the active Discord gateway, not a dormant fallback. PROGRESS.md is misleading about the live state.
- **VPS evidence:** `systemctl is-active guinevere-discord` → `active`. `systemctl is-enabled guinevere-discord` → `enabled`. `systemctl status guinevere-discord --no-pager` → `Active: active (running) since Thu 2026-06-25 19:45:01 WIB; 6h ago`.
- **Verification:** CONFIRMED_ON_VPS (direct SSH, 2026-06-26)
- **V2 classification:** CONFIRMED_ON_VPS
- **Blocker for:** None (documentation issue, not runtime code)
- **Source findings:** Live VPS SSH direct (V2 reconciliation)

### P2-BUG-082 [HIGH] Two services share same DISCORD_BOT_TOKEN — duplicate gateway consumer risk

- **Dimension:** Security/Secrets, Architecture
- **Files:** `/home/guinevere/code/guinevere/.env.discord` (standalone bot token), `/home/guinevere/code/guinevere/.env.hermes` (Hermes gateway token), `/etc/systemd/system/guinevere-discord.service`, `/etc/systemd/system/hermes-gateway.service`
- **Description:** Both `guinevere-discord.service` and `hermes-gateway.service` read `DISCORD_BOT_TOKEN` from their respective environment files. Both services are active on the live VPS. If both connect to Discord Gateway simultaneously with the same token, Discord will disconnect one session (token collision). Current logs show the standalone bot holding a stable gateway session (RESUMING cleanly, no IDENTIFY collisions), and Hermes Gateway shows no Discord gateway connection events in its journal — suggesting Hermes may be an API-only gateway, not a Discord bot. No duplicate posts or gateway disconnections have been detected.
- **Impact:** Currently no observed collision (bot holds the session stably). But the risk is real: if Hermes Gateway also connects to Discord Gateway, or if either service restarts, token collision could cause disconnections, message delivery gaps, or duplicate responses.
- **VPS evidence:** Both service units have `EnvironmentFile` pointing to their respective `.env` files containing the same token name. `systemctl is-active guinevere-discord` → `active`. `systemctl is-active hermes-gateway` → `active`. Discord journal shows `RESUMED session` (no IDENTIFY collision).
- **Verification:** CONFIRMED_ON_VPS (direct SSH, 2026-06-26)
- **V2 classification:** CONFIRMED_ON_VPS
- **Blocker for:** None currently (no collision detected), but blocks any future attempt to run both as Discord gateway consumers
- **Source findings:** Live VPS SSH direct (V2 reconciliation)

### P2-BUG-083 [MEDIUM] Broad journalctl error grep was inflated — 98.4% X-poster polling noise, real errors ≈ 2

- **Dimension:** Runtime-Config
- **File:** `journalctl -u guinevere-discord --since '24 hours ago'` (VPS live log)
- **Description:** The original V2 finding claimed "2,201 error-related log lines in 24h" at HIGH severity. Re-analysis with strict filtering reveals the broad count was massively inflated by X-poster HTTP polling lines. The X-poster daemon polls `GET http://127.0.0.1:8097/api/posts?state=failed&limit=1` every ~11 seconds. The word `failed` in the URL query parameter matches the broad grep `error|fail|exception`, producing 2,448 false-positive matches out of 2,485 total (98.4%).
  - Broad grep: 2,485 matches
  - `state=failed` polling lines: 2,448 (NOT errors — HTTP 200 OK, healthy polling)
  - `[ERROR]` log level: 2 (real application errors — 9Router provider 404)
  - `Traceback`: 0 (no Python crashes)
  - `CRITICAL` / `FATAL`: 1 (likely `safety_critical: True` metadata, not a crash)
  - Total log lines in 24h: 7,467
- **Impact:** The bot is actually stable — 0 Tracebacks, only 2 application-level errors in 24 hours (both 9Router provider configuration issues, not Discord bugs). The original HIGH severity was incorrect.
- **VPS evidence:** `journalctl -u guinevere-discord --no-pager --since '24 hours ago' | grep -c 'Traceback'` → 0. `| grep -c '\[ERROR\]'` → 2. `| grep -c 'state=failed'` → 2,448.
- **Verification:** CONFIRMED_ON_VPS (direct SSH, 2026-06-26)
- **V2 classification:** CONFIRMED_ON_VPS (severity downgraded from HIGH to MEDIUM)
- **Blocker for:** None — bot is healthy
- **Source findings:** Live VPS SSH direct (V2 reconciliation)

### P2-BUG-084 [MEDIUM] vps-mirror/systemd-live/ is STALE — missing guinevere-discord.service

- **Dimension:** Evidence/Docs
- **File:** `vps-mirror/systemd-live/` (11 files, no discord unit)
- **Description:** The `vps-mirror/systemd-live/` directory contains 11 service units (guinevere-9router, guinevere-core, guinevere-health-check, guinevere-loops, guinevere-mcp, guinevere-monitoring, guinevere-obscura, guinevere-scheduler, guinevere-surveillance, hermes-gateway) but does NOT contain `guinevere-discord.service`. The live VPS has this unit at `/etc/systemd/system/guinevere-discord.service` — active since 2026-06-25. The mirror was never updated to reflect the discord service being active.
- **Impact:** The V1 audit and previous reconciliation used `vps-mirror` as the primary VPS state reference. Because the discord unit was missing from the mirror, V1 incorrectly concluded the bot was "masked / not deployed." The mirror is stale and should not be used as authoritative VPS evidence.
- **VPS evidence:** `ls /etc/systemd/system/guinevere-discord.service` → exists. `vps-mirror/systemd-live/` → no discord unit.
- **Verification:** CONFIRMED_ON_VPS (direct SSH, 2026-06-26)
- **V2 classification:** CONFIRMED_ON_VPS
- **Blocker for:** None (evidence hygiene, not runtime)
- **Source findings:** Live VPS SSH direct (V2 reconciliation)

---

## Blocker Map for Downstream Phases

| Phase | Blocking Bugs |
|-------|--------------|
| **P19** (Multi-Project Context) | P2-BUG-001 (age key co-location), P2-BUG-009 (plaintext backup creds) |
| **P22** (Raw/Full Access) | P2-BUG-002 (dead notifications), P2-BUG-003 (missing #alerts), P2-BUG-010 (Administrator permission), P2-BUG-012 (broken permissions module), P2-BUG-016 (bypass safety gates) |
| **P23** (Embodied Ops) | P2-BUG-016 (bypass safety gates) |
| **P24** (Hermes Fork Convergence) | P2-BUG-004 (broken deploy unit), P2-BUG-006 (conflicting hermes units), P2-BUG-007 (command count drift) |

---

## Severity Distribution by Dimension

**Note:** Bugs are multi-dimensional (each bug can touch multiple dimensions). Per-dimension counts are cross-references, not unique counts. The authoritative total is 84 from the 84 `### P2-BUG-NNN [SEVERITY]` headings in the summary table above.

| Dimension | CRIT | HIGH | MED | LOW | COSM | Row Total (cross-ref) |
|-----------|------|------|-----|-----|------|-----------------------|
| Architecture | 1 | 4 | 5 | 6 | 12 | 28 |
| Evidence/Docs | 1 | 1 | 4 | 4 | 6 | 16 |
| Security/Secrets | 1 | 4 | 1 | 1 | 0 | 7 |
| Runtime/Config | 1 | 3 | 6 | 4 | 5 | 19 |
| Permissions/Commands | 1 | 4 | 4 | 4 | 3 | 16 |
| Notification/Fallback | 1 | 2 | 3 | 2 | 3 | 11 |
| V2 Live VPS | 1 | 2 | 2 | 0 | 0 | 5 |

**Unique bug total (authoritative):** 84 bugs — computed from 84 `### P2-BUG-NNN [SEVERITY]` headings: 5 CRITICAL, 14 HIGH, 19 MEDIUM, 19 LOW, 27 COSMETIC.
