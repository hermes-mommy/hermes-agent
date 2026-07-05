# P2 Discord Writer Ownership Map — Implementation Audit

**Date:** 2026-06-25  
**Auditor:** Read-only subagent  
**Scope:** Identify every Discord writer surface, reconcile token sources, map ownership, assess duplicate-writer collision risk, cite ADR-035 and P2-022.

---

## Executive Summary

Three Discord writer surfaces exist in the repository. Only **one gateway** (Hermes Gateway) is active at runtime; the standalone discord.py bot is **masked** per P2-022/ADR-035. The core REST publisher (Option-B, P20) coexists safely because it uses HTTPS REST, not a WebSocket gateway. All three surfaces read the **same** `DISCORD_BOT_TOKEN` environment variable from different files/contexts, creating a latent collision risk if the masked standalone bot were ever re-enabled.

---

## Writer Surface Details

### Surface 1: Standalone discord.py Gateway Bot

| Property | Detail |
|---|---|
| **Code location** | `src/discord/_entrypoint.py` — `GuinevereBot` class wrapping `commands.Bot` |
| **Module files** | `src/discord/` directory, ~59 `.py` files incl. 49+ `cmd_*.py`, `_startup.py`, `_intents.py`, `notifications.py`, `gotify_fallback.py`, `hermes_conversational.py`, `shadow_pipeline.py`, `listeners/`, `loops/` |
| **Legacy archived** | `src/discord/bot.py.bak.pre-phase2` and `conversational_handler.py.bak.pre-phase2` — old standalone bot renamed, not deleted |
| **Writes what** | Slash commands (49 registered in `_entrypoint.py:setup_hook`), chat responses (`#guinevere-chat` via `hermes_conversational.py`), startup greeting (`_startup.py:on_ready` → `#guinevere-status`), SEV notifications (`notifications.py:send_alert`), HARD STOP embeds |
| **Token source** | `os.environ["DISCORD_BOT_TOKEN"]` |
| **Token file** | Two competing service unit mechanisms: **systemd/guinevere-discord.service** (`EnvironmentFile=.env.discord`, plaintext) vs. **deploy/discord/guinevere-discord.service** (SOPS-decrypt `/secrets/.env.discord.sops` → `/run/guinevere-discord-token`, shredded on stop) |
| **Runtime status** | **MASKED** (P2-022, ADR-035). Intentionally disabled. |
| **Verification** | `vps-mirror/systemd-live/` contains NO `guinevere-discord.service` — confirms the VPS has no live standalone bot unit |
| **Collision risk** | Would cause **gateway session collision** if re-enabled while Hermes gateway is connected (same token → two WebSocket sessions → Discord disconnects one) |

#### Finding P2-OWN-001 — HARD STOP listener IS wired, contradicting cmd_safeword docstring

- **File:** `src/discord/_entrypoint.py`, lines 132–160
- **Evidence:** `_register_hard_stop_listener()` calls `self.listen("on_message")` which fires BEFORE main `on_message`. It lazy-imports `handle_safeword_message_async` from `cmd_safeword` and invokes it. CONFIRMED wired.
- **Contradiction:** `cmd_safeword.py` line 598 docstring says: "No bot.py listener exists yet. This function is callable and documented but inactive until P2-017 wires it." This documentation is **stale** — the wire IS present in `_entrypoint.py`.
- **Severity:** COSMETIC / LOW (stale docstring, not a functional bug)
- **Verification:** CONFIRMED

#### Finding P2-OWN-002 — Command count 49, not 35, not 33

- **File:** `src/discord/_command_registry.py`, line 406
- **Evidence:** `require_canonical_registry()` asserts `len(names) == 49`. The `COMMAND_SPECS` tuple contains exactly 49 spec entries. The original P2 scope was 35 commands, but P12 (+4 email), P14 (+3 health), P18 (+4 memory), P5 (+3 loop monitor), and Hermes Phase 1 (+2 session) expanded to 49.
- **Old discrepancy (33 vs 35):** PROGRESS.md has been updated to say 35 (line ~146). But the code has 49. The 33-vs-35 discrepancy is superseded; the new discrepancy is 35-in-PROGRESS vs 49-in-code.
- **Severity:** MEDIUM (documentation out of sync with code)
- **Verification:** CONFIRMED

#### Finding P2-OWN-003 — notifications.py line 240 bare `import discord` contradicts lazy-import design

- **File:** `src/discord/notifications.py`, line 240
- **Evidence:** BARE `import discord  # noqa: E402  # isort: skip` at module level, AFTER all class/protocol definitions. The rest of the module (including `_get_discord_embed_module()`) uses `importlib.import_module("discord")` for lazy loading. If `discord.py` is absent at module import time, this line will raise `ModuleNotFoundError` and crash the import.
- **Impact:** If `discord` is not in the Python environment (e.g. tests, core-only run), importing `notifications.py` fails. The `importlib` pattern elsewhere in the module was designed to prevent exactly this.
- **Severity:** HIGH (defeats the lazy-import safety pattern, can crash at import time)
- **Verification:** CONFIRMED

---

### Surface 2: Hermes Gateway

| Property | Detail |
|---|---|
| **Code location** | `src/hermes/` (6 .py files), `src/hermes_plugins/` (33 .py files mirroring discord cmd_*.py) |
| **Writes what** | Slash commands (via hermes_plugins `command_catalog.py` and per-command plugins marked "Migrated from src/discord/cmd_*.py"), chat responses (via `hermes_conversational.py` → `src/hermes/adapter.py` → `HermesSessionAdapter`), session management |
| **Token source** | `DISCORD_BOT_TOKEN` from environment file |
| **Token file** | Three conflicting service unit references: **systemd/hermes-gateway.service** → `.env.hermes` (but ExecStart uses `--config .../hermes-config/config.yaml` — **this config directory does not exist**); **scripts/hermes-gateway.service** → `/home/guinevere/.hermes/.env` (ExecStart = `hermes gateway run --accept-hooks`); **vps-mirror/systemd-live/hermes-gateway.service** → `/home/guinevere/code/guinevere/.env.hermes` (ExecStart = `hermes gateway run --accept-hooks`) |
| **Runtime status** | **ACTIVE** (present in `vps-mirror/systemd-live/hermes-gateway.service` — this is the live VPS unit) |
| **Config collision** | `systemd/hermes-gateway.service` references `--config /home/guinevere/code/guinevere/hermes-config/config.yaml gateway` but `config/hermes/` directory does **not exist** in the repo. This unit file is **non-functional** as written. |
| **Verification** | vps-mirror confirms the live VPS uses `hermes gateway run --accept-hooks` path, NOT the `--config` path |
| **Hermes Discord adapter** | `src/hermes/` has NO Discord-specific code — no discord.py imports, no gateway WebSocket logic. The files reference Discord only as "user_id" context for sessions/memory. The actual Discord gateway connection is managed by the `hermes` CLI binary, not by `src/hermes/` Python code. |
| **hermes_plugins Discord references** | Each plugin file has a header comment "Migrated from src/discord/cmd_*.py" but the plugin code itself does not import discord.py — it uses Hermes' own `ctx` pattern. Some plugins reference `guinevere-discord` in restart lists (e.g. `restart_service.py:31`). |

#### Finding P2-OWN-004 — Hermes gateway service unit mismatch (two conflicting units, one dead path)

- **systemd/hermes-gateway.service** references `ExecStart=/home/guinevere/code/guinevere/.venv/bin/hermes --config /home/guinevere/code/guinevere/hermes-config/config.yaml gateway`
- **Problem:** `config/hermes/` directory does not exist in the repository. This unit is non-functional.
- **scripts/hermes-gateway.service** uses `hermes gateway run --accept-hooks` with `EnvironmentFile=/home/guinevere/.hermes/.env`
- **vps-mirror/systemd-live/hermes-gateway.service** uses `hermes gateway run --accept-hooks` with `EnvironmentFile=/home/guinevere/code/guinevere/.env.hermes`
- **Impact:** The repo's `systemd/hermes-gateway.service` is disconnected from the live VPS config. The scripts/ and vps-mirror versions are the canonical ones.
- **Severity:** MEDIUM (repo unit stale, could cause confusion during redeployment)
- **Verification:** CONFIRMED

---

### Surface 3: Core REST Publisher (P20 Option-B)

| Property | Detail |
|---|---|
| **Code location** | `src/life_kernel/discord_rest_client.py` (264 lines) |
| **Supporting files** | `src/life_kernel/dashboard_writer.py` (248 lines), `src/life_kernel/log_channel.py` (166 lines) |
| **Writes what** | Dashboard message in `#guinevere-status` (edit-in-place, one message, PATCH not POST), lifecycle log in `#guinevere-logs` (append-only POST) |
| **Token source** | `os.environ.get("DISCORD_BOT_TOKEN")` — same as other writers |
| **Connection type** | HTTPS REST (httpx.AsyncClient), **no WebSocket/gateway** |
| **Runtime status** | **ACTIVE** (P20 CLOSED, confirmed live in PROGRESS.md line 977: dashboard message `1519135545501028549` in `#guinevere-status`, bot-authored, edited in place; log channel `#guinevere-logs` receives lifecycle events) |
| **Fail-soft** | Every call wrapped in try/except with structlog fallback. Token never logged. |
| **Collision risk** | **None** — REST API calls do not conflict with gateway WebSocket connections |

---

## Token Source Comparison

| Writer | File | Token Source | SOPS-encrypted? | Collision with active? |
|---|---|---|---|---|
| Standalone bot (systemd unit) | `.env.discord` | EnvFile plaintext | NO | Would collide with Hermes gateway if re-enabled |
| Standalone bot (deploy unit) | `/run/guinevere-discord-token` | SOPS-decrypt, shredded on stop | YES (originally) | Would collide with Hermes gateway if re-enabled |
| Hermes Gateway (systemd unit, dead) | `.env.hermes` (via `--config` path that doesn't exist) | N/A | N/A | Unit is non-functional |
| Hermes Gateway (scripts unit) | `.hermes/.env` | EnvFile plaintext | NO | Currently the active gateway — only one allowed |
| Hermes Gateway (vps-mirror live) | `.env.hermes` | EnvFile plaintext | NO | Currently the active gateway |
| Core REST Publisher | `DISCORD_BOT_TOKEN` env var | Via caller's env | Depends on caller | None (REST, no WebSocket) |

**Observations:**
- All three writers read the SAME variable name (`DISCORD_BOT_TOKEN`) from different files.
- Only the `deploy/discord/` service unit implements SOPS decryption for the token.
- The Hermes gateway services (scripts/, vps-mirror) read the token in plaintext from `.env.hermes` or `.hermes/.env`.
- The standalone bot service (systemd/) also reads in plaintext from `.env.discord`.

---

## Duplicate-Writer Risk Assessment

### Gateway Session Collision (CRITICAL)

If two gateway-based bots connect to Discord with the **same bot token**, Discord's gateway will disconnect one of them (first-connected wins, second gets error 4004 or gets force-disconnected). This is a hard platform limitation.

**Current state:** The standalone bot (`guinevere-discord.service`) is **masked** (P2-022). Only the Hermes gateway connects via WebSocket. **No collision currently occurs.**

**Latent risk:** If the standalone bot were accidentally re-enabled (e.g. `systemctl unmask guinevere-discord && systemctl start guinevere-discord`), it would open a second gateway session with the same token and cause a collision. The bot.py.bak.pre-phase2 file remains on disk and could be recovered.

### REST + Gateway Coexistence (SAFE)

The core REST publisher uses `httpx.AsyncClient` to call `https://discord.com/api/v10` endpoints. REST API calls and gateway WebSockets are independent; Discord allows both from the same bot simultaneously. No collision.

### Token Leakage Risk (MEDIUM)

The same `DISCORD_BOT_TOKEN` is stored in multiple plaintext env files:
- `.env.discord` (plaintext)
- `.env.hermes` (plaintext)
- `.hermes/.env` (plaintext)

Only the deploy version of the standalone bot service uses SOPS-decryption + shred. This means the token is trivially recoverable from any of these files if the VPS is compromised.

---

## SEV Notification Channel Name Drift

**Source file:** `src/discord/notifications.py`, lines 33–37

| SEV | Code channel | Migration doc channel | Exist in channel-ids.yaml? |
|---|---|---|---|
| SEV0 | `system-health` | `guinevere-alerts` (phase-2-discord.md) | YES (`system-health`) |
| SEV1 | `system-health` | `guinevere-alerts` | YES |
| SEV2 | `cost-tracker` | — | YES |
| SEV3 | `guinevere-status` | — | YES |
| SEV4 | `audit-log` | — | YES |

The migration document `phase-2-discord.md` references a channel `guinevere-alerts` (line 69: `alerts: "guinevere-alerts"`) which does **not exist** in `channel-ids.yaml` or `_command_registry.py`. The actual code routes SEV0/SEV1 to `system-health`, which exists. The doc is stale.

**Verification:** CONFIRMED  
**Severity:** LOW (doc out of sync with code; code is correct)

---

## Gotify Port Verification

| Claim | Value | Source |
|---|---|---|
| Code hardcodes | `http://localhost:8081` | `gotify_fallback.py:32` |
| Deployment evidence | Port 8081, Docker `127.0.0.1:8081:80` | `P2/batch-plan-020-021.md`, `local-p2-020-021-patterns.md` |
| Old audit (P2-AUDIT-COMPLETE.md) | Port 8080 health responds `{"status":"up"}` | Historical: Gotify Docker may have been on 8080 initially |
| **Verdict** | **8081 is current canonical port** — code matches deployment evidence | |

**Verification:** CONFIRMED — 8081 is correct, not 8080.

---

## Channel Count Verification

`channel-ids.yaml` lists **14 channels** (including `rituals` + 3 ghost channels: `project-alpha-dev`, `project-alpha-docs`, `project-beta-dev`). The `rituals` channel (ID `1513496377324339262`) is not part of the original 13-channel P2-006 set and appears to have been added later. The 3 ghost channels were flagged in the old P2-AUDIT for cleanup.

**Verification:** CONFIRMED (14 vs expected 13)  
**Severity:** LOW (ghost channels are cosmetic but should be cleaned up per P2-FIX-PLAN)

---

## ADR-035 / P2-022 Compliance

- **ADR-035** mandates Hermes Gateway as the sole Discord gateway after migration.
- **P2-022** states `guinevere-discord.service` is "intentionally masked."
- **P2-AUDIT-COMPLETE.md** (2026-06-08) PASSed P2-022 as "Service masked."
- **Current verification:** `vps-mirror/systemd-live/` contains NO discord unit and DOES contain `hermes-gateway.service`. This is consistent with the masked state claim.
- **PROGRESS.md** line 158 confirms: "guinevere-discord.service masked intentionally (Hermes Gateway handles Discord now — standalone bot deprecated post-ADR-035)."
- **P20 PROGRESS.md** evidence (line 977) confirms core REST publisher is the active dashboard writer.

**Conclusion:** ADR-035 compliance is TEXT-CONFIRMED (standalone bot masked, Hermes gateway ACTIVE, core REST publisher ACTIVE). Full runtime verification of Hermes gateway's Discord WebSocket connectivity requires live VPS inspection (NEEDS RUNTIME).

---

## Ownership Table

| Surface | Status | Token Source | Writes What | Active Runtime |
|---|---|---|---|---|
| Standalone discord.py bot (`src/discord/_entrypoint.py`) | **MASKED** (P2-022) | `DISCORD_BOT_TOKEN` from `.env.discord` (plaintext) or `/run/guinevere-discord-token` (SOPS+shred) | Slash commands, chat, startup greeting, SEV notifications | NO — intentionally disabled |
| Hermes Gateway (`hermes-gateway.service`) | **ACTIVE** | `DISCORD_BOT_TOKEN` from `.env.hermes` / `.hermes/.env` (plaintext) | Slash commands (via hermes_plugins), chat responses (via HermesSessionAdapter) | YES — per vps-mirror, confirmed in PROGRESS.md |
| Core REST Publisher (`src/life_kernel/discord_rest_client.py`) | **ACTIVE** | `DISCORD_BOT_TOKEN` from environment variable | Dashboard (#guinevere-status, edit-in-place), Lifecycle log (#guinevere-logs, append-only) | YES — P20 CLOSED, verified live edits |

### Who owns Discord writing right now?

**Hermes Gateway** owns the gateway connection (slash commands, chat responses).  
**Core REST Publisher** owns dashboard/log output (outbound REST only).  
**Standalone bot** owns nothing — it is masked and dormant.

### Is runtime responsibility correctly assigned to ONE writer?

**YES for gateway** — only Hermes Gateway has an active WebSocket.  
**YES for REST** — only core REST publisher writes dashboard/logs (outbound-only, no collision risk).  
**No duplicate gateway collision** is present or likely.

---

## Findings Summary

| ID | Severity | Title | File:Line |
|---|---|---|---|
| P2-OWN-001 | COSMETIC | Stale docstring in cmd_safeword.py says HARD STOP listener inactive | `src/discord/cmd_safeword.py:598` |
| P2-OWN-002 | MEDIUM | Command count: PROGRESS.md says 35, code has 49 | `_command_registry.py:406` |
| P2-OWN-003 | HIGH | Bare `import discord` at line 240 defeats lazy-import safety | `src/discord/notifications.py:240` |
| P2-OWN-004 | MEDIUM | systemd/hermes-gateway.service references non-existent config path | `systemd/hermes-gateway.service:31` |
| — | INFO | Token stored in 3 plaintext env files across writers | `.env.discord`, `.env.hermes`, `.hermes/.env` |
| — | LOW | Migration doc references non-existent `guinevere-alerts` channel | `phase-2-discord.md:69` |
| — | LOW | 14 channels in channel-ids.yaml vs expected 13 (`rituals` extra + 3 ghosts) | `channel-ids.yaml` |

### Verification Status Key

- **CONFIRMED:** Verified by static code/file inspection
- **NEEDS-RUNTIME:** Cannot be confirmed without VPS access or live systemctl/journalctl
- **UNVERIFIED:** Conflicting or ambiguous evidence

---

## Appendix: Files Examined

- `src/discord/_entrypoint.py` — Bot class, on_message, setup_hook, hard stop wiring
- `src/discord/notifications.py` — SEV routing, lazy-import, bare discord import
- `src/discord/gotify_fallback.py` — Gotify URL and port
- `src/discord/cmd_safeword.py` — HARD STOP handler, docstring
- `src/discord/_command_registry.py` — Command count (49)
- `src/discord/hermes_conversational.py` — Chat handler, Hermes integration
- `src/discord/_startup.py` — Startup greeting
- `src/discord/_intents.py` — Gateway intents
- `src/life_kernel/discord_rest_client.py` — Core REST client
- `src/life_kernel/dashboard_writer.py` — Dashboard message management
- `src/life_kernel/log_channel.py` — Log channel abstraction
- `src/hermes/adapter.py` — Hermes session adapter
- `src/hermes_plugins/` — 33 migrated Discord plugins
- `systemd/guinevere-discord.service` — Systemd unit (plaintext env)
- `deploy/discord/guinevere-discord.service` — Deploy unit (SOPS decrypt)
- `systemd/hermes-gateway.service` — Hermes unit (dead config path)
- `scripts/hermes-gateway.service` — Hermes unit (active path)
- `vps-mirror/systemd-live/hermes-gateway.service` — Live VPS unit
- `vps-mirror/systemd-live/` — All live units (no discord unit)
- `secrets/discord-secrets.enc.yaml` — SOPS-encrypted exists, valid
- `docs/setup-evidence/hermes-migration/phase-2-discord.md` — Migration plan
- `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml` — Channel list
- `docs/audit/P2-AUDIT-COMPLETE.md` — Old audit (2026-06-08)
- `docs/audit/P2-FIX-PLAN.md` — Old fix plan
- `PROGRESS.md` — Phase tracking
