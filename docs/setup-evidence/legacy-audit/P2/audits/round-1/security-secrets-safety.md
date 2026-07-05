# P2 Round-1 Security / Secrets / Safety Audit Report

**Date:** 2026-06-25
**Auditor:** Claude Code (read-only subagent)
**Dimension:** Security / Secrets / Safety
**Method:** Static code review, filesystem inspection, grep pattern analysis, prior-audit recheck
**Output path:** `docs/setup-evidence/legacy-audit/P2/audits/round-1/security-secrets-safety.md`

---

## Executive Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 3 |
| MEDIUM | 3 |
| LOW | 4 |
| COSMETIC | 1 |
| **TOTAL** | **12** |
| (INFO positive findings) | (3) |

---

## Recheck of Prior Audit Findings (P2-AUDIT-COMPLETE.md / P2-FIX-PLAN.md)

### P2-002 (CRITICAL in prior audit): Bot token + SOPS storage
- **Original finding:** "Encrypted secret MISSING. Token stored in plaintext in ~/.hermes/.env."
- **Current status:** FIXED. `secrets/discord-secrets.enc.yaml` EXISTS at repo root and IS properly SOPS-encrypted with AES256_GCM and an age recipient. Contains keys `discord_bot_token` and `discord_bot_id` (verified ciphertext structure, values not printed). The fix plan from P2-FIX-PLAN.md Phase 1 was carried out.
- **HOWEVER:** See new finding P2-AUD-R1-001 below -- the age secret key itself is stored in plaintext.
- **Verification:** CONFIRMED-FIXED with residual risk

### P2-010 (discrepancy in prior audit): 33 vs 35 commands
- **Original finding:** "PROGRESS.md claims 33 commands. Code has 35."
- **Current status:** CHECKLIST.md line 265 still says `commands_count=33`. The code in `_entrypoint.py` registers 13 wired callbacks + stub generation from `COMMAND_SPECS` (35 specifications). CHECKLIST is stale.
- **Verification:** CONFIRMED (33-vs-35 mismatch persists)

### P2-020 (Gotify port mismatch)
- **Original finding:** Port 8080 responds `{"status":"up"}` but Gotify binary not in PATH.
- **Current status:** `gotify_fallback.py` line 32 hardcodes `GOTIFY_URL = "http://localhost:8081"` (port 8081). The prior audit referenced port 8080. The port mismatch between code (8081) and old evidence (8080) persists. Needs runtime verification to determine which port is active.
- **Verification:** CONFIRMED (port mismatch, needs runtime)

---

## Detailed Findings

### P2-AUD-R1-001 [CRITICAL] -- Age secret key stored in plaintext repo file

| Field | Value |
|-------|-------|
| Severity | CRITICAL |
| File | `secrets/new-age-key.txt` |
| Lines | 3 total |
| Verification | CONFIRMED |

**Description:**
`secrets/new-age-key.txt` contains the PRIVATE age key (format: `AGE-SECRET-KEY-[REDACTED]`) in plaintext. This age identity is the SAME key referenced in `.sops.yaml` (`age12c4w4cgm228yrwjueay0vdsxwdmta69mk8wlyqt7mukrqp86r5xs5u6r0w`) and is used to encrypt `secrets/discord-secrets.enc.yaml`. Any attacker with access to this file can decrypt `discord-secrets.enc.yaml` and extract the Discord bot token, `discord_bot_id`, and any other secrets encrypted with the same key.

**Impact:**
Complete compromise of Discord bot token, bot identity validation key, and any other secrets encrypted under this age identity. The age key file should NOT be in the repo at all -- it belongs only on the VPS at `/home/guinevere/secrets/age-key.txt`.

**Recommendation:**
1. Immediately remove `secrets/new-age-key.txt` from version control.
2. Verify via `git rm` that it is removed from git history (or force-push after a sensitive-data scrub).
3. Rotate the Discord bot token (the encrypted secret is now as good as plaintext).
4. Generate a new age key pair, update `.sops.yaml`, re-encrypt all secrets.

---

### P2-AUD-R1-002 [HIGH] -- `systemd/guinevere-discord.service` references plaintext `.env.discord`

| Field | Value |
|-------|-------|
| Severity | HIGH |
| File | `systemd/guinevere-discord.service` (line 13) |
| Verification | CONFIRMED |

**Description:**
The `systemd/guinevere-discord.service` template uses `EnvironmentFile=/home/guinevere/code/guinevere/.env.discord`, which points to a plaintext env file. This is the template unit in the repo that would be deployed if someone copies it to `/etc/systemd/system/`.

**Contrast:**
- `deploy/discord/guinevere-discord.service` (the intended deploy unit) correctly uses SOPS decrypt -> `/run/guinevere-discord-temp` -> shred on stop.
- The `systemd/` template is STALE and would deploy a PLAINTEXT path if used.

**Impact:**
If anyone deploys using `systemd/guinevere-discord.service` instead of `deploy/discord/guinevere-discord.service` (e.g., following old docs, or automated deploy scripts that reference the systemd/ path), the Discord bot token would be loaded from a plaintext file.

**Recommendation:**
Replace the `systemd/` template with the SOPS-based version from `deploy/discord/`, or add an explicit comment/warning that it is superseded by the deploy version.

---

### P2-AUD-R1-003 [HIGH] -- Scripts parse plaintext env files for DISCORD_BOT_TOKEN

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Files | `scripts/finance_weekly_report.py` lines 25-34, `scripts/finance_dashboard_update.py` lines 25-34 |
| Verification | CONFIRMED |

**Description:**
Both `finance_weekly_report.py` and `finance_dashboard_update.py` open `~/.hermes/.env` directly, parse it line-by-line searching for `DISCORD_BOT_TOKEN`, and extract the value. This is inherently insecure -- the token is read from a plaintext file on disk, bypassing any SOPS decryption.

Additionally, the `hermes-config/hooks/finance_hook.py` function `_get_bot_token()` (lines 150-169) tries `os.environ.get("DISCORD_BOT_TOKEN")` first, then falls back to parsing multiple `.env` files (`~/.env.hermes`, `~/.env.discord`, `~/.env.core`) as plaintext. This means even if the main service uses SOPS, the Hermes hooks may read the token from a plaintext fallback.

**Impact:**
The Discord bot token exists in plaintext on disk in `~/.hermes/.env` (and potentially other `.env.*` files) accessible to any process running as the `guinevere` user, and discoverable via filesystem listing.

**Recommendation:**
1. Remove the `~/.hermes/.env` plaintext token storage -- use SOPS-decrypted runtime files only.
2. Refactor finance hooks to read token only from environment (which should be SOPS-decrypted into memory by systemd).
3. The scripts should be updated to accept token via argument or environment variable only.

---

### P2-AUD-R1-004 [HIGH] -- Plaintext secrets in `secrets/backup/` and `secrets/` directory

| Field | Value |
|-------|-------|
| Severity | HIGH |
| Files | `secrets/backup/cloudflare-r2-plaintext.env`, `secrets/backup/idcloudhost-s3-plaintext.env`, `secrets/backup/restic-password-plaintext.env`, `secrets/gmail-token.json`, `secrets/gmail-client-secrets.json` |
| Verification | CONFIRMED |

**Description:**
The `secrets/backup/` directory contains plaintext env files with production cloud credentials:
- Cloudflare R2: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `RESTIC_REPOSITORY`
- IDCloudHost S3: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- Restic backup password

Additionally, `secrets/gmail-token.json` and `secrets/gmail-client-secrets.json` contain plaintext Google OAuth tokens and client secrets.

While `secrets/` is listed in `.gitignore`, these files are present on disk and any attacker with filesystem access can use them directly.

**Note:** The `.gitignore` pattern `secrets/` ignores the directory, but `secrets/discord-secrets.enc.yaml` and `secrets/new-age-key.txt` (and all other files in secrets/) would also be excluded from git tracking, meaning the repo-in-`.git` does NOT contain them. This limits the blast radius to local disk only. However, `secrets/new-age-key.txt` plus `secrets/discord-secrets.enc.yaml` together form the critical chain: the age key decrypts the Discord token.

**Impact:**
Any process or user with read access to the `secrets/` directory can obtain production infrastructure credentials and the ability to decrypt the Discord bot token.

**Recommendation:**
1. Move age private key (`new-age-key.txt`) to a secure location outside the repo (VPS-only).
2. Delete plaintext backup credential files from `secrets/backup/`.
3. Document that `secrets/` should only contain SOPS-encrypted files.

---

### P2-AUD-R1-005 [MEDIUM] -- Administrator permission still active on Discord bot

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Source | CHECKLIST.md line 290 |
| Verification | CONFIRMED |

**Description:**
CHECKLIST.md section 4.4 Security Checks line 290 shows:
```
- [ ] No ADMINISTRATOR permission on bot -- not yet satisfied; P2-009 documented controlled OAuth reauthorization to reduce scope from Administrator
```
The Administrator permission is still active and marked as NOT satisfied. This grants the bot unrestricted access to the guild -- all channels, all permissions, ability to ban/kick, manage roles, etc. The CHECKLIST correctly identifies this as a long-term risk.

**Impact:**
If the bot were compromised (token leaked), the attacker would have full guild administrator access, not just the limited permissions needed for its operation.

**Recommendation:**
Plan a controlled OAuth reauthorization flow to reduce to minimal required permissions (send messages, read message history, embed links, attach files, use slash commands, add reactions, manage threads in designated channels). Track this as P2-009 completion.

---

### P2-AUD-R1-006 [MEDIUM] -- Multiple consumers share same DISCORD_BOT_TOKEN

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Files | Multiple -- see description |
| Verification | CONFIRMED |

**Description:**
The same `DISCORD_BOT_TOKEN` is consumed by multiple system components:

1. `src/discord/_entrypoint.py` -- standalone Discord bot (gateway connection, masked per ADR-035)
2. `src/life_kernel/discord_rest_client.py` -- core REST publisher (httpx outbound-only, no gateway session)
3. Hermes Gateway (`hermes gateway run --accept-hooks`) -- reads from `DISCORD_BOT_TOKEN` env var via `.venv/site-packages`
4. `src/core/api/routes.py` -- alertmanager webhook (REST outbound)
5. `hermes-config/hooks/finance_hook.py` -- REST calls for Discord message operations
6. Hermes plugins (`plugins/platforms/discord/adapter.py`) -- standalone Discord adapter

If both `guinevere-discord.service` (unmasked) and `hermes-gateway.service` run Discord gateway sessions simultaneously with the same token, Discord will disconnect one due to token collision. The REST-only consumers (items 2, 4, 5) are safe from collision as they don't open gateway sessions.

Currently, `guinevere-discord.service` is masked per ADR-035, so only the Hermes gateway should be active. But the masking can be removed, and the stale `systemd/` template has no masking directive.

**Impact:**
Risk of Discord gateway session disconnection if both services are active. Also makes token rotation more complex (must update all consumers simultaneously).

**Recommendation:**
1. Document the single-token architecture decision and ensure only ONE gateway consumer is active at a time.
2. Consider using separate tokens for life_kernel REST client if isolation is needed (though this adds complexity).
3. Ensure the masking of `guinevere-discord.service` is documented and enforced in deploy scripts.

---

### P2-AUD-R1-007 [MEDIUM] -- Raw Discord action paths bypass consent/safety gates

| Field | Value |
|-------|-------|
| Severity | MEDIUM |
| Files | `src/core/api/routes.py:314-320`, `src/life_kernel/discord_rest_client.py`, `hermes-config/hooks/finance_hook.py:150-169` |
| Verification | CONFIRMED |

**Description:**
Multiple components send messages to Discord using direct REST API calls, bypassing the HARD STOP / consent / safety gates in the P20/P23 framework:

- `src/core/api/routes.py` lines 314-320: Alertmanager webhook posts alerts to Discord channel directly using `DISCORD_BOT_TOKEN` and `DISCORD_ALERT_CHANNEL_ID`. No HARD STOP check before posting. No consent boundary check. This is a raw production-alerting path that should remain functional during safe mode, so this may be by design.

- `src/life_kernel/discord_rest_client.py`: The P20 dashboard publisher is intentionally designed as "Option-B core-integrated REST publisher" that bypasses the gateway. It's described as "purely outbound status publishing" so the lack of consent/safety gates is by design. But this means dashboard/log messages continue during HARD STOP safe mode.

- `hermes-config/hooks/finance_hook.py`: Finance hooks can delete Discord messages and post embeds without passing through any safety gate.

**Impact:**
During HARD STOP safe mode, dashboard updates, alert messages, and finance operations may still post to Discord channels, potentially leaking the safe mode signal or operating outside the operator's expected safety boundary. Also, these paths bypass P20/P23 consent/semantic-action gates.

**Recommendation:**
1. Document which Discord-writing components are exempt from HARD STOP (e.g., health alerts, cost tracker) and ensure this is intentional.
2. Add a HARD STOP gate in finance_hook message deletion that checks safe mode before deleting user messages.
3. For the alertmanager webhook, ensure it only writes to designated alert channels, not to channels where the operator expects safety gating.

---

### P2-AUD-R1-008 [LOW] -- `notifications.py` bare `import discord` at module level

| Field | Value |
|-------|-------|
| Severity | LOW |
| File | `src/discord/notifications.py` line 240 |
| Verification | CONFIRMED |

**Description:**
At line 240, after the module has defined lazy `importlib.import_module("discord")` patterns, there is a bare `import discord  # noqa: E402  # isort: skip`. This contradicts the lazy-import design used in other modules (cmd_safeword.py, _startup.py, etc.) and will crash the module on import if `discord` is absent.

**Impact:**
If `notifications.py` is imported in an environment without `discord.py` installed (e.g., during testing, or in a non-Discord runtime context), the module will `ImportError` at line 240, even though the function-level import at line 208 (`import discord as discord_module`) already handles this gracefully. The bare import at line 240 is dead code that overrides the lazy pattern.

**Recommendation:**
Remove line 240 (`import discord  # noqa: E402  # isort: skip`). The function-level import at line 208 already handles the case where `discord.utils` is needed but `discord_utils` is None.

---

### P2-AUD-R1-009 [LOW] -- `gotify_fallback.py` port mismatch (8081 vs 8080)

| Field | Value |
|-------|-------|
| Severity | LOW |
| File | `src/discord/gotify_fallback.py` line 32 |
| Verification | CONFIRMED |

**Description:**
`gotify_fallback.py` line 32 hardcodes `GOTIFY_URL = "http://localhost:8081"`. The prior audit (P2-AUDIT-COMPLETE.md) reports port 8080 as the verified endpoint. Old evidence references Gotify running on port 8080. This is a port mismatch between code and old evidence. Needs runtime verification to determine which port is actually active on the VPS.

**Impact:**
If Gotify is listening on 8080 but the code sends to 8081, the Gotify fallback silently fails for SEV0/SEV1 notifications. The code defines this as fail-soft (returns False on connection error), so the impact is a silent notification gap for the highest severity alerts.

**Recommendation:**
1. Verify VPS Gotify port with `ss -tlnp | grep gotify` at runtime.
2. Document the correct port in code and evidence.
3. Consider making the port configurable via environment variable.

---

### P2-AUD-R1-010 [LOW] -- Stale `systemd/guinevere-shadow-monitor.service` references plaintext `.env.discord`

| Field | Value |
|-------|-------|
| Severity | LOW |
| File | `systemd/guinevere-shadow-monitor.service` (line 13) |
| Verification | CONFIRMED |

**Description:**
The `systemd/guinevere-shadow-monitor.service` unit also references `EnvironmentFile=/home/guinevere/code/guinevere/.env.discord` (plaintext). This unit does not exist in `deploy/discord/` or `vps-mirror/`, so it may be unused. But it represents a stale unit that would deploy with plaintext token access if re-enabled.

**Impact:**
If shadow monitoring is re-enabled using the systemd template, it would read the Discord token from a plaintext file.

**Recommendation:**
Update or remove the stale shadow-monitor service template.

---

### P2-AUD-R1-011 [LOW] -- channel-ids.yaml has 14 channels, CHECKLIST says 13

| Field | Value |
|-------|-------|
| Severity | LOW |
| File | `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml` |
| Verification | CONFIRMED |

**Description:**
`channel-ids.yaml` lists 14 channels including `rituals` (ID: `1513496377324339262`). The CHECKLIST.md line 261 says "13 channels." The prior audit listed 13 channels with 3 active (23%). The `rituals` channel was added/mapped but not reflected in documentation counts. This does not affect security directly but represents a documentation drift that could hide channel configuration issues.

**Recommendation:**
Ensure `rituals` channel is properly documented in all relevant docs (channel-ids.yaml is the SOURCE, so CHECKLIST and other docs should reference 14, not 13).

---

### P2-AUD-R1-012 [LOW/COSMETIC] -- PROGRESS.md / CHECKLIST.md command count (33 vs 35) still stale

| Field | Value |
|-------|-------|
| Severity | COSMETIC |
| File | `CHECKLIST.md` line 265 |
| Verification | CONFIRMED |

**Description:**
CHECKLIST.md line 265 still reads `commands_count=33` while the code defines 35 `COMMAND_SPECS` entries. This mismatch persists from the prior P2-AUDIT-COMPLETE.md finding. Not a security issue but indicates documentation drift.

**Recommendation:**
Update PROGRESS.md and CHECKLIST.md to reflect 35 commands. (Was listed in P2-FIX-PLAN.md Phase 2 but marked as not yet done.)

---

## Positive Findings (INFO)

### P2-AUD-R1-901 [INFO] -- HARD STOP IS properly wired in `_entrypoint.py`

Contrary to the seed fact's suggestion that `handle_safeword_message_async` might be unwired, it IS properly wired:
- `GuinevereBot.__init__()` calls `_register_hard_stop_listener()` (line 104/138)
- This registers `self.listen("on_message")(self._on_message_listener)` (line 138)
- `_on_message_listener` (line 140) lazy-imports `handle_safeword_message_async` and calls it
- The main `on_message` (line 654) also checks `handler.is_safe` and blocks non-recovery messages during safe mode

This is a robust dual-layer implementation (listener fires before main `on_message`).

**Verification:** CONFIRMED-POSITIVE

### P2-AUD-R1-902 [INFO] -- `deploy/discord/guinevere-discord.service` correctly uses SOPS decrypt

The `deploy/discord/` version of the service unit:
- `ExecStartPre` runs `sops --decrypt` -> `/run/guinevere-discord-token`
- `EnvironmentFile=/run/guinevere-discord-token` (chmod 600)
- `ExecStopPost` runs `shred -u` to securely delete the decrypted token

This is a secure implementation. The prior audit (P2-AUDIT-COMPLETE.md) may have been looking at the wrong file.

**Verification:** CONFIRMED-POSITIVE

### P2-AUD-R1-903 [INFO] -- Token-unsafe-scan-verifier files exist for steps P2-013 through P2-021

Nine token-unsafe-scan-verifier.md files exist under `docs/setup-evidence/P2/STEP-P2-0{13..21}/verifiers/`. A sample (P2-013) shows comprehensive grep for `DISCORD_BOT_TOKEN`, bare `except:`, `# type: ignore`, and other unsafe patterns. The verifier infrastructure is in place and applied consistently.

**Verification:** CONFIRMED-POSITIVE

---

## Cross-Dimension Findings Summary

| ID | Severity | Title | Impact |
|----|----------|-------|--------|
| 001 | CRITICAL | Age secret key in plaintext repo file | Full Discord token compromise |
| 002 | HIGH | systemd/ template uses plaintext `.env.discord` | Token exposure if deployed from wrong unit |
| 003 | HIGH | Scripts parse plaintext `.env` for token | Token readable from disk by any process |
| 004 | HIGH | Plaintext secrets in secrets/backup/ | Infrastructure credential exposure |
| 005 | MEDIUM | Administrator permission still active | Full guild access if token compromised |
| 006 | MEDIUM | Multiple consumers share same token | Gateway collision risk |
| 007 | MEDIUM | Raw Discord actions bypass safety gates | HARD STOP / consent exceptions in some paths |
| 008 | LOW | `notifications.py` bare `import discord` | Module import breakage |
| 009 | LOW | Gotify port 8081 vs 8080 mismatch | Silent SEV0/SEV1 notification loss |
| 010 | LOW | Stale shadow-monitor service uses plaintext | Token exposure path if re-enabled |
| 011 | LOW | 14 channels listed vs 13 documented | Documentation drift |
| 012 | COSMETIC | Command count 33 vs 35 still stale | Documentation drift |

---

## Recommendations (Priority Order)

1. **IMMEDIATE:** Remove `secrets/new-age-key.txt` from repo; rotate Discord bot token and age key pair.
2. **IMMEDIATE:** Delete or SOPS-encrypt `secrets/backup/` plaintext files.
3. **HIGH:** Align `systemd/guinevere-discord.service` template with the secure `deploy/discord/` version (SOPS decrypt pattern).
4. **HIGH:** Refactor `scripts/finance_weekly_report.py` and `scripts/finance_dashboard_update.py` to read token from environment only, not by parsing `.env` files.
5. **MEDIUM:** Plan Administrator permission reduction (P2-009 completion).
6. **MEDIUM:** Document single-token architecture and ensure only one gateway consumer runs at a time.
7. **LOW:** Remove the dead `import discord` at `notifications.py:240`.
8. **LOW:** Verify Gotify port at runtime; document correct port.
9. **LOW:** Update channel count and command count documentation.

---

## Methodology Notes

- All findings are based on static analysis of the repo at commit `63c5285`.
- No runtime secrets were decrypted, printed, or observed.
- No Discord API calls were made.
- No files were modified except this output file.
- The `secrets/discord-secrets.enc.yaml` content was verified as SOPS-encrypted by reading its first 20 lines (ciphertext + sops metadata). No plaintext values were extracted.
- Age key value was noted only to confirm it IS the plaintext key matching the `.sops.yaml` recipient.
- "NEEDS-RUNTIME" is noted where evidence cannot be confirmed without VPS access.
