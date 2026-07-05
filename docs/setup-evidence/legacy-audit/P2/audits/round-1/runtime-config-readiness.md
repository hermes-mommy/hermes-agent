# P2 Round-1 Implementation Audit: Runtime/Config Readiness

**Auditor:** Subagent (read-only, enterprise workflow)
**Date:** 2026-06-25
**Scope:** Systemd units (3x discord, 2x hermes-gateway), .env files, entrypoint runnability, config mismatches (Gotify port, channel names, embed colors), brittle startup assumptions, SOPS encryption status, command count drift
**Methodology:** Static code analysis (Read, Grep, AST counting, filesystem glob), cross-reference with old audits, evidence directories
**Output Path:** `docs/setup-evidence/legacy-audit/P2/audits/round-1/runtime-config-readiness.md`

---

## Executive Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 3 |
| HIGH | 5 |
| MEDIUM | 4 |
| LOW | 4 |
| COSMETIC | 3 |
| **TOTAL** | **19** |

---

## Finding Log

### P2-RC-R1-001 [CRITICAL] — systemd/guinevere-discord.service references non-existent PLAINTEXT .env.discord

- **File:** `systemd/guinevere-discord.service` line 13
- **Evidence:**
  ```ini
  EnvironmentFile=/home/guinevere/code/guinevere/.env.discord
  ```
- **Verification:** CONFIRMED
- **Description:** The `systemd/guinevere-discord.service` unit loads the Discord bot token from a plaintext `.env.discord` file. This file does NOT exist in the repository (Glob for `**/.env.discord*` returned zero results). The unit has no SOPS decrypt pre-step, no `shred` post-stop. If this unit were installed and enabled (it is not -- it is intentionally masked per P2-022), it would either fail to start because `.env.discord` is missing, or the operator would need to create a plaintext `.env.discord` containing a live token on the VPS -- both scenarios are bad.
- **Impact:** If the service is ever unmasked or an operator follows this template, tokens would be stored in plaintext on disk with no cleanup. As-is, the unit is non-functional without a missing file.
- **Fix:** Either remove `systemd/guinevere-discord.service` (it is stale) or update it to match `deploy/discord/guinevere-discord.service` (SOPS+tmpfs+shred). The `systemd/` directory should declare which unit is canonical.

### P2-RC-R1-002 [CRITICAL] — deploy/discord/guinevere-discord.service references non-existent .env.discord.sops

- **Files:** `deploy/discord/guinevere-discord.service` lines 13-15
- **Evidence:**
  ```ini
  ExecStartPre=/usr/bin/sops --decrypt --input-type dotenv --output-type dotenv \
    /home/guinevere/code/guinevere/secrets/.env.discord.sops \
    > /run/guinevere-discord-token
  ```
- **Verification:** CONFIRMED
- **Description:** The `deploy/discord/` version (the SOPS-secure template) references `secrets/.env.discord.sops`. This file does not exist. The actual SOPS-encrypted file is `secrets/discord-secrets.enc.yaml`, which is YAML-format (not dotenv). The `--input-type dotenv --output-type dotenv` flags would also fail against the YAML file. This unit would crash on `ExecStartPre` with a file-not-found error, preventing the bot from starting.
- **Impact:** The deploy-ready service unit is BROKEN by design -- it points to a non-existent file path with the wrong input type flag. Any attempt to install this unit would fail at service start.
- **Fix:** Either rename the encrypted file to `secrets/.env.discord.sops` in dotenv format, or update the ExecStartPre path to `discord-secrets.enc.yaml` and remove the `--input-type dotenv` (since it is YAML). Recommend the latter.

### P2-RC-R1-003 [CRITICAL] — Secrets age key stored in PLAINTEXT in repo

- **File:** `secrets/new-age-key.txt` 
- **Evidence:** File contains an `AGE-SECRET-KEY-[REDACTED]` in plaintext (verified by reading the first bytes).
- **Verification:** CONFIRMED
- **Description:** The age secret key used to decrypt all SOPS-encrypted secrets (discord bot token, DB passwords, redis passwords, etc.) is stored in plaintext in the repository. The `.sops.yaml` file was verified: it references `age: age12c4w4cgm...` which corresponds to the public portion. The private key is in `new-age-key.txt`. This defeats the entire purpose of SOPS encryption: any attacker with repo access can decrypt all secrets.
- **Impact:** CRITICAL. The SOPS encryption is a facade: the private key is co-located in the same directory as the encrypted files. A repository compromise = all secrets compromised.
- **Fix:** Do NOT store the age private key in the repo. Document a secure out-of-band distribution method (e.g. environment variable `SOPS_AGE_KEY` or `SOPS_AGE_KEY_FILE` pointing to a file outside the repo). The existing `new-age-key.txt` should be git-removed and added to `.gitignore`.

### P2-RC-R1-004 [HIGH] — systemd/guinevere-discord.service uses plaintext EnvironmentFile with no shred (insecure by design)

- **File:** `systemd/guinevere-discord.service`
- **Evidence:** Line 13: `EnvironmentFile=/home/guinevere/code/guinevere/.env.discord` (plaintext path). Compare with `deploy/discord/guinevere-discord.service` which has SOPS decrypt + tmpfs + shred.
- **Verification:** CONFIRMED
- **Description:** The `systemd/` copy of the service unit is the INSECURE variant. It lacks `ExecStartPre` SOPS decryption, `PrivateTmp=true`, `ExecStopPost` shred, and references a plaintext token file. The `systemd/` directory is supposed to be the canonical service template per ADR-035 phase 7b hardening, but this unit is notably LESS secure than the `deploy/discord/` variant. This is a regression -- if someone copies `systemd/` units to the VPS thinking they are canonical, they get a less secure configuration.
- **Impact:** HIGH. Template confusion risks deployment of an insecure service unit. The "canonical" systemd directory contains the wrong (insecure) variant.
- **Fix:** Align `systemd/guinevere-discord.service` with `deploy/discord/guinevere-discord.service`, fixing the file path as noted in R1-002.

### P2-RC-R1-005 [HIGH] — Two conflicting hermes-gateway.service units with different ExecStart and EnvironmentFile

- **Files:** 
  - `systemd/hermes-gateway.service` (repo template)
  - `scripts/hermes-gateway.service` (scripts/)
  - `vps-mirror/systemd-live/hermes-gateway.service` (live VPS snapshot)
- **Evidence:** 
  - `systemd/`: `ExecStart=...hermes --config .../hermes-config/config.yaml gateway`, `EnvironmentFile=.../.env.hermes`
  - `scripts/`: `ExecStart=...hermes gateway run --accept-hooks`, `EnvironmentFile=.../.hermes/.env`
  - `vps-mirror/systemd-live/` (LIVE): `ExecStart=...hermes gateway run --accept-hooks`, `EnvironmentFile=.../.env.hermes`
- **Verification:** CONFIRMED
- **Description:** The Hermes gateway has THREE conflicting unit definitions:
  1. `systemd/hermes-gateway.service` uses `hermes --config .../config.yaml gateway` (explicit config file, no `--accept-hooks`)
  2. `scripts/hermes-gateway.service` uses `hermes gateway run --accept-hooks` (accepts hooks, different EnvironmentFile path at `~/.hermes/.env`)
  3. The VPS LIVE unit (from `vps-mirror/systemd-live/`) mixes both: it uses `scripts/`'s ExecStart but `systemd/`'s EnvironmentFile. It also has `Wants=` instead of `Requires=` and is missing the `Requires=redis.service` dependency.
  
  The `systemd/` version has full security hardening (NoNewPrivileges, ProtectSystem, PrivateTmp, etc.), while `scripts/` is minimal. The LIVE unit splits the difference.
- **Impact:** HIGH. Creates ambiguity about the canonical execution model. The `hermes --config ... gateway` vs `hermes gateway run --accept-hooks` difference means different CLI subcommands are being used. Which is correct? The VPS is running the `gateway run --accept-hooks` variant. The `systemd/` template would NOT match the VPS state, making it unreliable as a source of truth.
- **Fix:** Declare ONE canonical form. Since the VPS live unit uses `gateway run --accept-hooks`, that is likely the current production command. Update `systemd/hermes-gateway.service` to match the live unit, or vice versa. Document the choice.

### P2-RC-R1-006 [HIGH] — `systemd/guinevere-discord.service` marked as "intentionally masked" but is actively different from deploy version

- **Files:** `systemd/guinevere-discord.service`, `PROGRESS.md` line 158, `P2-AUDIT-COMPLETE.md`
- **Evidence:** PROGRESS.md: "P2-022 `guinevere-discord.service` masked intentionally (Hermes Gateway handles Discord now -- standalone bot deprecated post-ADR-035)"
- **Verification:** CONFIRMED
- **Description:** The Discord service is intentionally masked. There is NO `guinevere-discord.service` in `vps-mirror/systemd-live/`, confirming it is not deployed. However, the repo still carries TWO copies of the unit (`systemd/` and `deploy/discord/`) with DRASTICALLY different configurations. The `systemd/` copy is less secure but lives in the "canonical" directory. If the service is ever unmasked or a new VPS is provisioned from the `systemd/` template, an insecure configuration will be deployed.
- **Impact:** HIGH for future operations. If the service is ever reactivated (e.g., Hermes Discord adapter isn't ready), the operator might grab `systemd/` and deploy an insecure unit.
- **Fix:** Since the service is masked, at minimum: (a) delete or clearly mark `systemd/guinevere-discord.service` as "DO NOT USE - masked/deleted", and (b) keep only `deploy/discord/` as the reference copy.

### P2-RC-R1-007 [HIGH] — secrets/backup/ directory has no .gitkeep, preventing VCS tracking of backup restoration status

- **File:** `secrets/backup/`
- **Evidence:** The `secrets/` directory (verified via `ls -la`) has a `backup/` subdirectory. ADR-035 B10 caveat mentions `secrets/backup/` restoration pending offline age-key recovery. No `.gitkeep` was found.
- **Verification:** CONFIRMED
- **Description:** The `secrets/backup/` directory is needed for ADR-035 B10 closure (offline backups). Without a `.gitkeep` or any tracked file, empty backup directories are invisible in the repo. There is no evidence of encrypted backup files either.
- **Impact:** MEDIUM. Could indicate backup workflow is incomplete or untestable.
- **Fix:** Track a `.gitkeep` in `secrets/backup/` or document the backup workflow clearly.

### P2-RC-R1-008 [MEDIUM] — notificatons.py bare `import discord` at module level (line 240) contradicts lazy-import design

- **File:** `src/discord/notifications.py` line 240
- **Evidence:** 
  ```python
  # Lines 140-143: lazy import via importlib in _get_discord_embed_module()
  # Line 208: lazy import inside send_alert():
  #     import discord as discord_module
  # Line 240: bare module-level:
  import discord  # noqa: E402  # isort: skip
  ```
- **Verification:** CONFIRMED
- **Description:** The module defines `DiscordEmbedProtocol`, `DiscordEmbedFactory`, and other protocols at the top for lazy/static typing. The `send_alert()` function (line 201) has its own lazy import of discord. However, a bare `import discord` at the BOTTOM of the module (line 240) runs unconditionally on module import. If discord.py is not installed, the module crashes on import. This contradicts the lazy-import design language used in the docstring "dynamic importlib conversion patterns". It also appears to be dead code -- the imported discord name is never referenced at module level after line 240 (all discord usage is inside functions).
- **Impact:** MEDIUM. Not a crash risk in production (discord.py IS installed alongside the bot), but is misleading for code readers, prevents clean import in non-Discord contexts, and the `# noqa: E402` comment masks the issue.
- **Fix:** Remove line 240. The lazy imports inside functions already handle discord access.

### P2-RC-R1-009 [MEDIUM] — .env.hermes does not exist in repo; scripts/ service references ~/.hermes/.env which also does not exist

- **Files:** `.env.hermes`, `.hermes/.env`
- **Evidence:** Glob for `**/.env.hermes*` at repo root returned no results. Glob for `**/.env*` in `.hermes/` returned no results.
- **Verification:** CONFIRMED
- **Description:** The systemd/hermes-gateway.service references `.env.hermes` (which does not exist). The scripts/hermes-gateway.service references `~/.hermes/.env` (which also does not exist in the repo). Neither file is tracked. The only `.env.*` files at root are `.env.gmail`, `.env.x_poster`, `.env.wearable`, `.env.wearable.example`, and `.env.example`.
- **Impact:** MEDIUM. These files likely exist on the VPS only and contain live tokens. But since the units differ on which path they reference, there is a risk the wrong unit deploys and references a file at the wrong path, causing a start failure.
- **Fix:** Standardize the path in both service units and document which `.env` file is the canonical Hermes one. Add `.env.hermes.example` to the repo.

### P2-RC-R1-010 [MEDIUM] — CHECKLIST.md still claims 33 slash commands (stale), PROGRESS.md says 35 (also stale), code has 49

- **Files:** `CHECKLIST.md` line 265, `PROGRESS.md` line 146, `src/discord/_entrypoint.py`, `src/discord/_command_registry.py` line 406
- **Evidence:**
  - `_command_registry.py` line 406-407: `if len(names) != 49: raise RuntimeError(f"expected 49 commands, found {len(names)}")`
  - `_entrypoint.py` has 49 `tree.command()` registrations
  - CHECKLIST.md line 265: `"/ in chat shows 33 slash commands"`
  - PROGRESS.md line 146: `"P2-010 Slash commands registration (35 commands)"`
  - P2-AUDIT-COMPLETE.md: `"Code has 35"` (stale from June 8)
- **Verification:** CONFIRMED
- **Description:** The command count has been drifting: CHECKLIST.md says 33 (never updated from original P2 design), PROGRESS.md says 35 (updated after P2-AUDIT but before later phase additions), code has 49 (including Hermes commands, P12 Gmail, P14 health, P18 advanced memory, P5 loop monitoring). The `_command_registry.py` validation enforces 49. All documentation is behind. P2-FIX-PLAN.md had "2.1 Update PROGRESS.md: 33 -> 35 commands" listed as [ ], but even 35 is now wrong.
- **Impact:** LOW-MEDIUM. Misleads anyone reading the documentation about the true surface area. Could cause confusion if someone relies on the documented count for testing or audit.
- **Fix:** Update CHECKLIST.md "33" -> "49" (or current count). Update PROGRESS.md "35" -> "49". Update P2-AUDIT-COMPLETE.md command count. Close P2-FIX-PLAN Phase 2.1 with updated number.

### P2-RC-R1-011 [MEDIUM] — 14 channels in channel-ids.yaml vs 13 documented in CHECKLIST.md

- **Files:** `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml` (14 entries), `CHECKLIST.md` line 261 (13 channels)
- **Evidence:** The `channel-ids.yaml` has 14 entries: `audit-log`, `cost-tracker`, `evidence-log`, `guinevere-chat`, `guinevere-dev`, `guinevere-docs`, `guinevere-evidence`, `guinevere-planning`, `guinevere-status`, `project-alpha-dev`, `project-alpha-docs`, `project-beta-dev`, `rituals`, `system-health`. The CHECKLIST.md lists 13 names, omitting `rituals`.
- **Verification:** CONFIRMED
- **Description:** The `channel-ids.yaml` includes a `rituals` channel (ID 1513496377324339262) that is NOT documented in CHECKLIST.md's list of 13 channels. This channel was added at some point after the initial 13-channel setup. The old audit counted 13 channels, so the checklist was written against that count. The `rituals` channel appears to be legitimate (it has a snowflake ID) but is undocumented.
- **Impact:** LOW-MEDIUM. Documentation drift. If `rituals` is a real channel, it should be documented. If it was created in error, it should be accounted for.
- **Fix:** Add `rituals` to CHECKLIST.md or remove the channel if it is a ghost. Audit whether the channel has any content.

### P2-RC-R1-012 [LOW] — GOTIFY_URL port 8081 vs old audit mention of 8080 (now resolved)

- **Files:** `src/discord/gotify_fallback.py` line 32, `docs/audit/P2-AUDIT-COMPLETE.md` line 64, `docs/setup-evidence/P2/STEP-P2-020/docker-compose.yml` line 7
- **Evidence:**
  - Code: `GOTIFY_URL: str = "http://localhost:8081"`
  - Docker compose: `"127.0.0.1:8081:80"`
  - Old audit: "Port 8080 responds `{"status":"up"}` on `/health`"
- **Verification:** CONFIRMED RESOLVED
- **Description:** The old audit (P2-AUDIT-COMPLETE.md) reported port 8080. Current code and Docker compose both agree on port 8081. The docker-compose maps host 8081 to container port 80. This discrepancy from the old audit has been resolved -- the Gotify setup was migrated to Docker which changed the port.
- **Impact:** LOW. Documentation only. The port change is already reflected in all current code and evidence files.
- **Fix:** The old audit could note the resolution, but this is already well-documented in the evidence trail.

### P2-RC-R1-013 [LOW] — PRD v2.2 references #alerts channel that does not exist

- **File:** `docs/00-core/01-PRD_v2.2.md` line 55
- **Evidence:** PRD v2.2: `| GUINEVERE COMMAND | \#alerts | Urgent alerts, punishment notifications, emergencies |`
- **Verification:** CONFIRMED
- **Description:** The PRD documents a `#alerts` channel that does not exist in `channel-ids.yaml` or in the actual Discord setup. The migration doc (phase-2-discord.md) references a `guinevere-alerts` channel (also not in channel-ids.yaml). The actual alert routing goes to `#system-health` (SEV0/SEV1), `#cost-tracker` (SEV2), `#guinevere-status` (SEV3), `#audit-log` (SEV4) per `notifications.py`. The `#alerts` / `guinevere-alerts` channel names appear to be legacy design that was replaced during implementation.
- **Impact:** LOW. Documentation drift from v2.2 PRD to actual implementation. Does not affect runtime behavior.
- **Fix:** Update PRD v2.2 to reference the actual channel names, or add a note that alerts are distributed across multiple channels per SEV level.

### P2-RC-R1-014 [LOW] — cmd_safeword.py sync version docstring says "No bot.py listener exists yet" but async version IS wired

- **File:** `src/discord/cmd_safeword.py` lines 594-601
- **Evidence:** 
  ```python
  def handle_safeword_message(message: object) -> bool:
      """...
      Note:
          No ``bot.py`` listener exists yet. This function is callable and
          documented but inactive until P2-017 wires it into the message
          handler pipeline.
      """
  ```
- **Verification:** CONFIRMED
- **Description:** The docstring for the SYNC version of `handle_safeword_message()` claims no listener exists. However, `_entrypoint.py` line 140 registers `_on_message_listener` which calls `handle_safeword_message_async()` (the ASYNC version). The HARD STOP text detection IS wired. The sync version's docstring is stale.
- **Impact:** LOW. Misleading documentation only. The async version handles the actual runtime path. The sync version exists as a fallback/callable utility.
- **Fix:** Update the sync version docstring to clarify: "No bot.py listener uses the sync version. The async version is wired in `_entrypoint.py._on_message_listener`."

### P2-RC-R1-015 [LOW] — notifications.py imports discord.utils at module level (lines 20-22) with silent try/except

- **File:** `src/discord/notifications.py` lines 20-22
- **Evidence:**
  ```python
  try:
      from discord import utils as discord_utils
  except Exception:
      discord_utils = None
  ```
- **Verification:** CONFIRMED
- **Description:** While the module-level try/except is safer than the bare import at line 240, it catches ALL exceptions (including `SyntaxError`, `KeyboardInterrupt`). PEP 8 recommends catching `ImportError` specifically. If discord.py has an installation problem, this will mask the root cause.
- **Impact:** LOW. Functionally works in production where discord.py is installed. Could mask import issues during development or testing.
- **Fix:** Change `except Exception:` to `except ImportError:`.

### P2-RC-R1-016 [COSMETIC] — deploy/env/ directory has only a WhatsApp template, no Discord templates

- **File:** `deploy/env/.env.whatsapp.template`
- **Verification:** CONFIRMED
- **Description:** The `deploy/env/` directory contains only `env.whatsapp.template`. There is no Discord env template, no Hermes template. This is inconsistent: if `deploy/env/` is meant for deployment env templates, Discord and Hermes should be represented. If it is WhatsApp-only, the directory should be named accordingly.
- **Impact:** COSMETIC. Organizational inconsistency.
- **Fix:** Either add `.env.discord.template` and `.env.hermes.template` to `deploy/env/`, or rename `deploy/env/` to `deploy/env-whatsapp/`.

### P2-RC-R1-017 [COSMETIC] — .env.example contains DISCORD_BOT_TOKEN placeholder but no GOTIFY_TOKEN placeholder

- **File:** `.env.example` line 74
- **Evidence:** Line 74: `DISCORD_BOT_TOKEN=your-discord-bot-token-here`. No GOTIFY_URL, GOTIFY_APP_TOKEN, or GOTIFY_ADMIN_PASSWORD entries found in the file.
- **Verification:** CONFIRMED
- **Description:** The `.env.example` has a placeholder for `DISCORD_BOT_TOKEN` but does not include any Gotify-related variables. The `GOTIFY_APP_TOKEN` is required by `gotify_fallback.py` (line 49: `os.environ.get("GOTIFY_APP_TOKEN", "")`), and `GOTIFY_ADMIN_PASSWORD` is referenced in the `docker-compose.yml`.
- **Impact:** COSMETIC. Does not affect running systems with existing config, but a new developer or new VPS setup would miss the Gotify env vars.
- **Fix:** Add `GOTIFY_APP_TOKEN`, `GOTIFY_URL`, and `GOTIFY_ADMIN_PASSWORD` to `.env.example`.

### P2-RC-R1-018 [COSMETIC] — systemd/ vs deploy/discord/ discrepancy documented nowhere

- **Files:** `systemd/guinevere-discord.service`, `deploy/discord/guinevere-discord.service`
- **Verification:** CONFIRMED
- **Description:** The existence of two drastically different copies of the same service unit with no README or comment explaining which is canonical and why there are two. The `deploy/discord/` version has proper SOPS+shred, while the `systemd/` version is insecure. An operator looking to deploy would not know which to use.
- **Impact:** COSMETIC (but with HIGH latent risk if the wrong one is deployed).
- **Fix:** Add a README.md in `systemd/` and/or `deploy/discord/` explaining the difference, the mask status, and which should be used if the service is ever reactivated.

### P2-RC-R1-019 [COSMETIC] — Old P2-AUDIT-COMPLETE.md CRITICAL finding "encrypted secret MISSING" is now RESOLVED but file is not updated

- **File:** `docs/audit/P2-AUDIT-COMPLETE.md`
- **Evidence:** Section 5, Priority 1: "Encrypt DISCORD_BOT_TOKEN with SOPS+age immediately."
- **Verification:** CONFIRMED RESOLVED
- **Description:** The old audit's only CRITICAL finding (P2-002) was that `secrets/discord-secrets.yaml` did not exist. The current state: `secrets/discord-secrets.enc.yaml` EXISTS and IS SOPS-encrypted (verified via `ENC[AES256_GCM...` prefix and AGE encrypted block). The fix plan Phase 1 is marked complete. However, the old audit report has not been updated to reflect the resolved state. As found in R1-002, the deploy unit references the wrong path, so the resolution is partial.
- **Impact:** COSMETIC. The old audit report is a historical document. But if used as a reference, it shows an outdated CRITICAL finding.
- **Fix:** Add a note to P2-AUDIT-COMPLETE.md indicating the finding status as of the current date. Also update P2-FIX-PLAN.md to reflect that Phase 1 is done (it shows `[x]` for all 5 sub-steps, which is accurate).

---

## Summary of Verification Status

| Finding | Status | Needs VPS Runtime? |
|---------|--------|-------------------|
| P2-RC-R1-001 | CONFIRMED | No |
| P2-RC-R1-002 | CONFIRMED | No |
| P2-RC-R1-003 | CONFIRMED | No |
| P2-RC-R1-004 | CONFIRMED | No |
| P2-RC-R1-005 | CONFIRMED | No |
| P2-RC-R1-006 | CONFIRMED | No |
| P2-RC-R1-007 | CONFIRMED | Yes (check if backup dir has content on VPS) |
| P2-RC-R1-008 | CONFIRMED | No |
| P2-RC-R1-009 | CONFIRMED | Yes (.env.hermes and ~/.hermes/.env may exist on VPS) |
| P2-RC-R1-010 | CONFIRMED | No |
| P2-RC-R1-011 | CONFIRMED | Yes (verify rituals channel exists and has content) |
| P2-RC-R1-012 | CONFIRMED RESOLVED | No |
| P2-RC-R1-013 | CONFIRMED | No |
| P2-RC-R1-014 | CONFIRMED | No |
| P2-RC-R1-015 | CONFIRMED | No |
| P2-RC-R1-016 | CONFIRMED | No |
| P2-RC-R1-017 | CONFIRMED | No |
| P2-RC-R1-018 | CONFIRMED | No |
| P2-RC-R1-019 | CONFIRMED RESOLVED | No |

**Items marked "Needs VPS Runtime" require `journalctl`, systemctl status, or live filesystem inspection that cannot be performed from this read-only Windows dev box.**

---

## Seed Fact Re-verification Notes

| Seed Fact | Actual State | Verdict |
|-----------|-------------|---------|
| "THREE discord service copies" | TWO exist in repo (systemd/ + deploy/discord/). vps-mirror/systemd-live/ has NONE. | PARTIALLY CORRECT |
| "systemd/ uses SOPS+shred" | WRONG. The systemd/ copy uses PLAINTEXT .env.discord. The deploy/discord/ copy has SOPS+shred. | SEED INVERTED |
| "deploy/discord/ uses plaintext .env.discord" | WRONG. The deploy/discord/ copy has SOPS+shred. The systemd/ copy uses plaintext. | SEED INVERTED |
| "notifications.py line 240 bare import discord contradicts lazy design" | CONFIRMED. Module-level import exists at line 240. | CONFIRMED |
| "cmd_safeword HARD STOP text UNWIRED" | PARTIALLY WRONG. Sync version is secondary. Async version IS wired in _entrypoint.py. | PARTIALLY CORRECT |
| "33 vs 35 command mismatch PERSISTS" | Actually now 49 vs 35 vs 33. Worse than seed describes. | MORE SEVERE |
| "channel-ids.yaml 14 channels vs 13" | CONFIRMED. rituals channel is the 14th. | CONFIRMED |
| "Gotify 8081 vs 8080" | Old audit 8080 resolved. Code+evidence agree on 8081. | RESOLVED |
| "SEV matrix routes vs migration doc" | notifications.py routes to system-health/cost-tracker/guinevere-status/audit-log. Migration doc mentions guinevere-alerts (not a real channel). PRD mentions #alerts (not a real channel). | MULTIPLE GHOST CHANNEL NAMES |
| "P20 is CLOSED" | CONFIRMED. No evidence of reopening. | CONFIRMED |
| "src/life_kernel/discord_rest_client.py is current Discord writer" | CONFIRMED. Well-structured with httpx+tenacity+fail-soft. | CONFIRMED |

---

## Recommendations (Priority Order)

1. **CRITICAL: FIX R1-002** — Update `deploy/discord/guinevere-discord.service` ExecStartPre to reference the actual encrypted file (`secrets/discord-secrets.enc.yaml`) with correct input type.
2. **CRITICAL: FIX R1-003** — Remove `secrets/new-age-key.txt` from repo immediately. It is the master key to all encrypted secrets.
3. **HIGH: FIX R1-001 / R1-004** — Align `systemd/guinevere-discord.service` with `deploy/discord/` (or delete the insecure copy). The systemd directory should not be the less secure option.
4. **HIGH: FIX R1-005** — Reconcile the three hermes-gateway.service variants. The `systemd/` template should match what is running on VPS (`vps-mirror/systemd-live/`).
5. **MEDIUM: FIX R1-008** — Remove redundant `import discord` at `notifications.py:240`.
6. **MEDIUM: FIX R1-010** — Update command count documentation (CHECKLIST.md, PROGRESS.md).
7. **MEDIUM: FIX R1-011** — Document or remove the `rituals` channel.
