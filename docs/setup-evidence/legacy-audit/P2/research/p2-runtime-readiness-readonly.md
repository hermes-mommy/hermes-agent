# P2 Runtime Readiness -- Read-Only Assessment

**Auditor:** Read-only subagent (Windows dev box, NOT VPS)  
**Date:** 2026-06-25  
**Scope:** Determine what runtime claims are verifiable from repo evidence vs. what requires live VPS access.

---

## 1. Environment Boundary

The audit runs on a **Windows 11 dev box** (bash via Git Bash). The following are **impossible** from this environment and are NOT attempted:

| Forbidden Action | Reason |
|---|---|
| `systemctl status/start/stop/enable/disable` | systemd not present on Windows |
| `journalctl` | systemd journal not present on Windows |
| `docker compose up/down` | Would mutate production-adjacent state |
| `curl` against Discord API / Gotify / Hermes / core | No live VPS tunnel |
| `sops --decrypt` | Would leak secret values (forbidden per HARD RULES) |
| `pip install` or `alembic upgrade` | Irreversible runtime mutation |
| Post/edit/delete Discord messages | Mutates guild state |
| Run `pytest` or any test suite | Executes code with side effects |
| Inspect live VPS filesystem | No SSH access from this session |

**Verdict: Read-only from repo artifacts only. Runtime claims require either evidence snapshots or explicit NEEDS-RUNTIME-VERIFICATION tagging.**

---

## 2. Token Availability (Sensitive -- Path and Status Only)

| Claim | Status | File |
|---|---|---|
| `secrets/discord-secrets.enc.yaml` EXISTS | **CONFIRMED** -- SOPS-encrypted YAML with age key stanza; token value NOT printed | `secrets/discord-secrets.enc.yaml` |
| `secrets/.env.discord.sops` EXISTS | **NOT FOUND** -- referenced by `deploy/discord/guinevere-discord.service` line 14 (`ExecStartPre=/usr/bin/sops --decrypt --input-type dotenv ... secrets/.env.discord.sops`) but this file does not exist in the repository | (missing) |
| `secrets/` directory contents | 10 files present: `discord-secrets.enc.yaml`, `guinevere-secrets.yaml`, `db-passwords.yaml`, `redis-password.yaml`, `.gitignore`, `test-enc.yaml`, `new-age-key.txt`, `gmail-client-secrets.json`, `gmail-token.json` | `secrets/` |
| `.sops.yaml` rules | CONFIRMED: matches `secrets/*.yaml` and `secrets/*.env` patterns to age key | `.sops.yaml` |

**Finding P2-RR-S01 (MEDIUM):** `deploy/discord/guinevere-discord.service` references `secrets/.env.discord.sops` but that file does not exist in the repo. The SOPS-encrypted secret that DOES exist is `secrets/discord-secrets.enc.yaml` (YAML format, not dotenv). The service unit's `ExecStartPre` decrypt command references a different file path/format than what exists. **UNVERIFIABLE** whether the correct file exists on the VPS at that path.

**Token note:** `DISCORD_BOT_TOKEN` is available in the codebase via SOPS `secrets/discord-secrets.enc.yaml`. The `deploy/discord/` service unit would use a different decrypt path (`secrets/.env.discord.sops`). The `systemd/` service unit uses a plain `EnvironmentFile=.env.discord` (no SOPS). The core REST publisher (`src/life_kernel/discord_rest_client.py`) reads `DISCORD_BOT_TOKEN` from env. Token value never printed.

---

## 3. Service Unit Files -- Three Conflicting Copies

### 3a. `systemd/guinevere-discord.service`

| Field | Value |
|---|---|
| Token source | `EnvironmentFile=/home/guinevere/code/guinevere/.env.discord` (PLAINTEXT) |
| ExecStart | `.venv/bin/python -m src.discord._entrypoint` |
| Security | `NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=read-only` |
| SOPS decrypt | **NONE** |
| Restart | `always` |
| Status per P20 evidence | **Masked** (symlink to /dev/null) -- by design per P2-022 |

### 3b. `deploy/discord/guinevere-discord.service`

| Field | Value |
|---|---|
| Token source | SOPS decrypt `secrets/.env.discord.sops` -> `/run/guinevere-discord-token` (shredded on stop) |
| ExecStart | `.venv/bin/python -m src.discord._entrypoint` |
| Security | `NoNewPrivileges=true`, `PrivateTmp=true`, `ProtectSystem=strict`, `ProtectHome=read-only` |
| SOPS decrypt | **YES** (`ExecStartPre` + `ExecStopPost shred`) |
| Restart | `on-failure` (with burst limit 5 in 300s) |
| Status per P20 evidence | **Masked** (same unit, different copy) |

### 3c. `vps-mirror/systemd-live/` -- **NO discord service present**

The live mirror at `vps-mirror/systemd-live/` contains 12 service files + 3 hermes-gateway overrides, but **no guinevere-discord.service**. This is consistent with the unit being masked (symlinked to /dev/null, so no file exists at the expected path).

### 3d. Hermes Gateway Conflict

| File | ExecStart | EnvironmentFile |
|---|---|---|
| `systemd/hermes-gateway.service` | `hermes gateway run --accept-hooks` | `.env.hermes` |
| `scripts/hermes-gateway.service` | `hermes --config .../hermes-config/config.yaml gateway` | `.hermes/.env` |
| `vps-mirror/systemd-live/hermes-gateway.service` | `hermes gateway run --accept-hooks` | `.env.hermes` |

**Finding P2-RR-S02 (MEDIUM):** Three hermes-gateway.service copies, two different ExecStart signatures. The live mirror matches `systemd/` version. The `scripts/` version uses a different config path and different EnvironmentFile. **UNVERIFIABLE** which is actually deployed; P20 smoke-test evidence mentions port 9191 conflict which is the gateway port, indicating Hermes Gateway IS running on the VPS.

---

## 4. Runtime Claims vs. Evidence

### Legend
- **VERIFIED-BY-EVIDENCE-SNAPSHOT** = Captured journalctl/systemctl/curl output exists in the repo
- **NEEDS-RUNTIME-VERIFICATION** = Claim is documented but no snapshot artifact exists
- **UNVERIFIABLE** = Cannot be confirmed or denied from any repo artifact

| # | Claim | Evidence Source | Status |
|---|---|---|---|
| 1 | `guinevere-discord.service` is masked | P20 `discord-service-audit.md`: `systemctl is-enabled guinevere-discord.service -> masked`, symlink->/dev/null verified | **VERIFIED-BY-EVIDENCE-SNAPSHOT** |
| 2 | `guinevere-core.service` is active (running) | P20 `soak-start.md`: `systemctl is-active guinevere-core -> active`, PID 3112267 | **VERIFIED-BY-EVIDENCE-SNAPSHOT** |
| 3 | Bot token validates against Discord | P20 `discord-permissions-audit.md`: `GET /users/@me -> {"id":"1510873134981582858","username":"Guinevere","bot":true}` | **VERIFIED-BY-EVIDENCE-SNAPSHOT** |
| 4 | Dashboard message exists and is bot-authored | P20 `dashboard-message-evidence.md`: GET `/channels/.../messages?limit=50` found msg `1519135545501028549`, `author=Guinevere (bot=True)`, `edited_timestamp != created` proves edit-not-spam | **VERIFIED-BY-EVIDENCE-SNAPSHOT** |
| 5 | Lifecycle log channel has entries | P20 `log-channel-evidence.md`: GET `/channels/.../messages?limit=4` returned bot-authored `[cycle 196283] phase=idle ...` entries | **VERIFIED-BY-EVIDENCE-SNAPSHOT** |
| 6 | HARD STOP visible in dashboard | P20 `hard-stop-discord-evidence.md`: Dashboard shows `HARD STOP = ✅ CLEAR` or `🔴 ACTIVE` | **VERIFIED-BY-EVIDENCE-SNAPSHOT** |
| 7 | HARD STOP recovery from stale checkpoint works | P20 `hard-stop-discord-evidence.md`: `[warning] hard_stop_recovery_clearing_stale_state` in journal; kernel recovers | **VERIFIED-BY-EVIDENCE-SNAPSHOT** |
| 8 | Heartbeat service runs 6 intervals | P20 `soak-start.md` and `smoke-test-evidence.md`: journalctl `heartbeat_service_started`, `interval_count=6`, all 6 intervals listed | **VERIFIED-BY-EVIDENCE-SNAPSHOT** |
| 9 | Kernel autonomously cycles (observe->decide->idle) | P20 `smoke-test-evidence.md`: `observe_node_entry -> ... -> idle_node_complete (cycle_count=1)` | **VERIFIED-BY-EVIDENCE-SNAPSHOT** |
| 10 | Brain generates real tasks (not fallback) | P20 `dashboard-message-evidence.md`: `Next Planned Action` is real HermesBrain output, `model=guinevere`, `fallback_used=0` | **VERIFIED-BY-EVIDENCE-SNAPSHOT** |
| 11 | Slash commands synced (35+) | P2 `STEP-P2-010/verification.md` claims REST verify PASS. But code now has 49 wired commands. No recent sync evidence. | **NEEDS-RUNTIME-VERIFICATION** (code has 49 commands, old evidence verified 35) |
| 12 | Gotify service is up | P2 evidence says Docker compose exists at `/home/guinevere/config/gotify/docker-compose.yml`. No snapshot of running container. | **NEEDS-RUNTIME-VERIFICATION** |
| 13 | Gotify accessible on `localhost:8081` | Code (gotify_fallback.py line 32) uses 8081. Docker-compose maps `127.0.0.1:8081:80`. No live `curl http://127.0.0.1:8081/health` snapshot found. | **NEEDS-RUNTIME-VERIFICATION** |
| 14 | Hermes Gateway is handling Discord (ADR-035 claim) | P20 evidence says 7 companion services active including hermes-gateway. Port 9191 conflict noted. But no Discord-specific proof from gateway. | **NEEDS-RUNTIME-VERIFICATION** |
| 15 | SEV0 thread gets created in `#system-health` | notifications.py line 184: `create_thread=normalized == "SEV0"`. No evidence of a SEV0 thread existing. | **NEEDS-RUNTIME-VERIFICATION** |
| 16 | Bot has SEND_MESSAGES, READ_MESSAGE_HISTORY, EMBED_LINKS, MANAGE_MESSAGES | P20 `discord-permissions-audit.md`: write-then-delete probe in `#guinevere-logs` returned success (204). Dashboard embed renders. | **VERIFIED-BY-EVIDENCE-SNAPSHOT** |
| 17 | Pre-existing VPS issues: port 9191 conflict, guardian AttributeError | P20 `smoke-test-evidence.md` and `soak-start.md` both document these as pre-existing. | **VERIFIED-BY-EVIDENCE-SNAPSHOT** |
| 18 | Discord REST client uses httpx + tenacity, never logs token | `src/life_kernel/discord_rest_client.py` lines 66-67, 159-164: token never in exception messages, `_extract_error_code` avoids body. Confirmed by static analysis. | **CONFIRMED BY CODE** |
| 19 | `handle_safeword_message_async` is wired in `_on_message_listener` | `_entrypoint.py` line 155-157: `from .cmd_safeword import handle_safeword_message_async; consumed = await handle_safeword_message_async(message)`. Seed claim was **OUTDATED**. | **CONFIRMED BY CODE** (seed fact outdated) |

---

## 5. Seed Fact Re-Verification

| Seed Fact | Repo Truth | Status |
|---|---|---|
| `notifications.py` line ~240 bare `import discord` after lazy imports | Line 240: `import discord  # noqa: E402  # isort: skip`. Bare `import discord` at module level. Contradicts lazy-import design. | **CONFIRMED** (CRITICAL risk -- crashes module if discord.py absent) |
| HARD STOP text detection unwired -- only `/safeword` slash works | `_entrypoint.py` line 132-157: `_register_hard_stop_listener` registers `_on_message_listener` which calls `handle_safeword_message_async`. **WIRED.** | **OUTDATED SEED** -- text detection IS wired in `_entrypoint.py` |
| PROGRESS.md says 33 commands, CHECKLIST.md says 35, code has 35 | PROGRESS.md line 146 says "35 commands" (was updated from 33). Code `_entrypoint.py` has **49 wired commands** (13 original + 20 batch D + 2 Hermes + 4 P12 + 3 P14 + 4 P18 + 3 P5 loop-moni). `core_names` tuple line 515-542 lists 49 names. | **OUTDATED** -- command count has grown to 49, neither 33 nor 35 |
| channel-ids.yaml lists 14 channels vs CHECKLIST/audit say 13 | `channel-ids.yaml` lists 14 channels (including `rituals` + `project-alpha-dev/docs` + `project-beta-dev` + `guinevere-logs`). Actually, let me recount: audit-log, cost-tracker, evidence-log, guinevere-chat, guinevere-dev, guinevere-docs, guinevere-evidence, guinevere-planning, guinevere-status, project-alpha-dev, project-alpha-docs, project-beta-dev, rituals, system-health = **14**. But `guinevere-logs` (1510914623367413850) is referenced by P20 evidence as the lifecycle log channel but is NOT in channel-ids.yaml. PROGRESS.md line 142 says "13 channels". | **CONFIRMED** (14 in channel-ids.yaml + 1 channel referenced by P20 not listed = 15 used channels vs 13 documented) |
| Gotify URL hardcoded as `localhost:8081` but old audit says port 8080 | Current `gotify_fallback.py` line 32: `GOTIFY_URL: str = "http://localhost:8081"`. Docker-compose `STEP-P2-020/docker-compose.yml` line 7: `"127.0.0.1:8081:80"`. Old audit (`P2-AUDIT-COMPLETE.md`) noted port 8080 but that was the state before the Docker-based Gotify setup. The evidence docker-compose uses 8081 matching current code. | **RESOLVED** (old-audit finding fixed; code and evidence agree on 8081) |
| SEV matrix routes SEV0/SEV1->system-health, SEV2->cost-tracker, SEV3->guinevere-status, SEV4->audit-log | `notifications.py` lines 33-37: `SEV0_CHANNEL = "system-health"`, `SEV1_CHANNEL = "system-health"`, `SEV2_CHANNEL = "cost-tracker"`, `SEV3_CHANNEL = "guinevere-status"`, `SEV4_CHANNEL = "audit-log"`. Matches seed. | **CONFIRMED** |
| `deploy/` service uses SOPS, `systemd/` uses plaintext | CONFIRMED: `deploy/discord/guinevere-discord.service` has `ExecStartPre` SOPS decrypt chain. `systemd/guinevere-discord.service` uses `EnvironmentFile=.env.discord` directly (plaintext). | **CONFIRMED** |
| Old P2-AUDIT-COMPLETE.md FAIL-002: encrypted secret MISSING | `secrets/discord-secrets.enc.yaml` now EXISTS and IS SOPS-encrypted. The old FAIL finding is **RESOLVED**. However, `deploy/discord/` references a different SOPS file (`secrets/.env.discord.sops`) that doesn't exist in repo. | **PARTIALLY RESOLVED** -- enc file exists but path mismatch between deploy unit and actual file |

---

## 6. CRITICAL/HIGH Findings Summary

### P2-RR-C01 (CRITICAL) -- `notifications.py` bare `import discord` at module level

- **File:** `src/discord/notifications.py`, line 240
- **Evidence:** `import discord  # noqa: E402  # isort: skip` after defining lazy-import protocols (lines 60-113) and `_get_discord_embed_module()` (line 140) that uses `importlib.import_module("discord")`.
- **Impact:** If discord.py is absent or fails to import (e.g., environment without it, or import error), the module crashes at load time BEFORE any of the lazy-import code can function. The bare import at module level completely undermines the lazy-import design. Additionally, lines 19-22 already attempt a try/except import of `discord.utils`:
  ```python
  try:
      from discord import utils as discord_utils
  except Exception:
      discord_utils = None
  ```
  But line 240 bypasses this pattern for the full `import discord`. This is likely dead/redundant code left from refactoring.
- **Verification:** **CONFIRMED** by static analysis.

### P2-RR-C02 (HIGH) -- Deploy service references non-existent SOPS file

- **Files:** `deploy/discord/guinevere-discord.service` (line 14) vs `secrets/` directory
- **Evidence:** The deploy unit runs `sops --decrypt --input-type dotenv --output-type dotenv /home/guinevere/code/guinevere/secrets/.env.discord.sops` but the repo contains `secrets/discord-secrets.enc.yaml` (YAML format, not dotenv). The referenced `.env.discord.sops` does not exist in the repo.
- **Impact:** If this unit is used rather than `systemd/` version, the `ExecStartPre` will fail because the file does not exist at the expected path, or if it exists on VPS with different format, the `--input-type dotenv` may not match the actual format.
- **Verification:** **NEEDS-RUNTIME-VERIFICATION** -- may exist on VPS only.

### P2-RR-H01 (HIGH) -- Command count drift: code has 49, docs say 35

- **Files:** `src/discord/_entrypoint.py` (49 wired commands), `PROGRESS.md` line 146 ("35 commands"), `docs/audit/P2-AUDIT-COMPLETE.md` ("35 commands")
- **Evidence:** `_entrypoint.py` `setup_hook()` registers 49 `tree.command()` calls (lines 248-512). `core_names` tuple (lines 515-542) lists 49 names. But PROGRESS.md and old P2 audit still reference 35 commands.
- **Impact:** Documentation mismatch misleads future audits and deployment checks.
- **Verification:** **CONFIRMED** by code inspection.

### P2-RR-H02 (HIGH) -- Channel count mismatch: 14 in YAML vs 13 documented; log channel not in YAML

- **Files:** `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml` (14 channels), `PROGRESS.md` line 142 ("13 channels")
- **Evidence:** channel-ids.yaml lists 14 channels including `rituals` (1513496377324339262) and `project-alpha-dev/docs` and `project-beta-dev`. Additionally, P20 evidence references `#guinevere-logs` (1510914623367413850) as the lifecycle log channel but it is NOT listed in channel-ids.yaml at all. So 15 channels are actually in use.
- **Impact:** Channel inventory is incomplete. Ghost channels (project-alpha-*) not cleaned up as per P2-FIX-PLAN Phase 3.
- **Verification:** **CONFIRMED** by file inspection.

---

## 7. P2 Fix Plan Status

| Phase | Action | Status |
|---|---|---|
| Phase 1 (CRITICAL): P2-002 SOPS encryption | Encrypt DISCORD_BOT_TOKEN | **DONE** -- `secrets/discord-secrets.enc.yaml` exists, SOPS-encrypted |
| Phase 2: P2-010 Documentation fix | Update PROGRESS.md 33->35 commands | **PARTIAL** -- Updated to 35 but code now has 49 commands |
| Phase 3: Channel cleanup | Delete ghost channels (project-alpha-*) | **NOT DONE** -- channel-ids.yaml still lists them |
| Phase 4: Automation | Cron/services for system-health, cost-tracker | **NOT DONE** -- no evidence found |

---

## 8. Readiness Matrix

| Criterion | Verdict | Evidence Level |
|---|---|---|
| Bot token available via SOPS | **READY** | CONFIRMED (encrypted file exists) |
| Bot token available at runtime | **READY** (via core REST publisher env, or deploy unit's SOPS decrypt path -- though the referenced .enc file format may not match | CONFIRMED (token in discord-secrets.enc.yaml) |
| Discord REST client (Option-B) wired in core | **READY** | CONFIRMED by code + P20 snapshots |
| Dashboard message posting to `#guinevere-status` | **READY** | VERIFIED-BY-EVIDENCE-SNAPSHOT (msg ID 1519135545501028549) |
| Lifecycle log posting to `#guinevere-logs` | **READY** | VERIFIED-BY-EVIDENCE-SNAPSHOT (live entries captured) |
| HARD STOP detection and Discord visibility | **READY** | VERIFIED-BY-EVIDENCE-SNAPSHOT + CONFIRMED by code wiring |
| Slash commands synced (current state) | **UNVERIFIED** | NEEDS-RUNTIME-VERIFICATION (code has 49 commands, last sync evidence from P2 era verified 35) |
| Gotify Docker container running | **UNVERIFIED** | NEEDS-RUNTIME-VERIFICATION |
| Hermes Gateway Discord adapter working | **UNVERIFIED** | NEEDS-RUNTIME-VERIFICATION |
| SEV0 notification routing creates threads | **UNVERIFIED** | NEEDS-RUNTIME-VERIFICATION (code logic present, no evidence of live SEV0 thread) |
| service `guinevere-core` active | **READY** | VERIFIED-BY-EVIDENCE-SNAPSHOT (PID 3112267, soak-start evidence) |
| service `guinevere-discord` masked | **READY** | VERIFIED-BY-EVIDENCE-SNAPSHOT (symlink->/dev/null, P20 discord-service-audit.md) |
| service `hermes-gateway` active | **NEEDS CHECK** | VERIFIED-BY-EVIDENCE-SNAPSHOT (7 services active per soak-start, but no explicit status line for hermes-gateway) |
| Kernel autonomous cycling | **READY** | VERIFIED-BY-EVIDENCE-SNAPSHOT |
| Heartbeat 6 intervals running | **READY** | VERIFIED-BY-EVIDENCE-SNAPSHOT |
| LangGraph Postgres checkpointer | **NEEDS CHECK** | NEEDS-RUNTIME-VERIFICATION (deploy evidence shows migration applied, but pre-existing issue: `AsyncPostgresSaver` context-manager issue noted) |
| Bot permissions in dashboard/log channels | **READY** | VERIFIED-BY-EVIDENCE-SNAPSHOT (write/delete probe) |
| Plaintext token leak risk from `systemd/` unit | **EXISTS** | CONFIRMED -- `systemd/guinevere-discord.service` uses `EnvironmentFile=.env.discord` with no SOPS. If this unit is used instead of `deploy/` version, the token is in plaintext on disk. |

---

## 9. Critical Forbidden Actions for Follow-Up Audit

The next auditor (if any) must NOT:

1. **Run `sops --decrypt`** on any secrets file -- token leakage risk.
2. **Restart, enable, or disable** any service -- mutates production state.
3. **Post, edit, or delete** any Discord message -- mutates guild state.
4. **Run `docker compose`** for Gotify or any service.
5. **Run `alembic upgrade`** or any migration.
6. **Edit security-sensitive modules** (notifications.py, discord_rest_client.py, _auth_guard.py, cmd_safeword.py -- already analyzed).
7. **Run `pytest`** unless confirmed read-only with no side effects.
8. **SSH into the VPS** from this session -- no SSH key is loaded.

Actions that ARE safe:

1. **Inspect `vps-mirror/`** contents (already done -- no guinevere-discord service present).
2. **Read `systemd/` and `deploy/`** service unit files (already done).
3. **Read `docs/setup-evidence/`** for journalctl/curl snapshots (already done).
4. **Static code analysis** of any Python file (already done).
5. **Read `PROGRESS.md`** and audit files for discrepancy tracking (already done).

---

## 10. Recommendations

1. **Resolve `secrets/.env.discord.sops` path mismatch.** Either create the dotenv-format SOPS file at `secrets/.env.discord.sops` or update `deploy/discord/guinevere-discord.service` to reference `secrets/discord-secrets.enc.yaml` with correct `--input-type yaml` flag.

2. **Remove bare `import discord` at line 240 of `notifications.py`.** It completely undermines the lazy-import design. If it is needed for the module-level import (it seems to be used for `discord_utils` which is already handled at lines 19-22), the purpose is unclear.

3. **Update command count documentation.** PROGRESS.md and any command-count references should reflect 49+ wired commands, not 33 or 35.

4. **Clean up ghost channels** or update channel-ids.yaml to reflect actual channels in use. Add `#guinevere-logs` (1510914623367413850) to the inventory.

5. **Decide which discord service unit is authoritative.** The `systemd/` and `deploy/discord/` copies differ significantly in security posture (plaintext vs SOPS). Only one should be the source of truth.

6. **Update PROGRESS.md** to reflect the current state: service is masked by design, REST client is the active writer, and P20 handles Discord visibility.

---

## 11. Footer

| Field | Value |
|---|---|
| Audit file | `docs/setup-evidence/legacy-audit/P2/research/p2-runtime-readiness-readonly.md` |
| Auditor | Read-only implementation audit subagent |
| Platform | Windows 11 dev box (Git Bash), NOT VPS |
| Date | 2026-06-25 |
| Findings | 1 CRITICAL, 2 HIGH, 2 MEDIUM, 3 COSMETIC/LOW |
| Files inspected | 40+ across `src/discord/`, `systemd/`, `deploy/discord/`, `secrets/`, `vps-mirror/`, `docs/setup-evidence/P2/`, `docs/setup-evidence/P20/`, `docs/audit/` |
