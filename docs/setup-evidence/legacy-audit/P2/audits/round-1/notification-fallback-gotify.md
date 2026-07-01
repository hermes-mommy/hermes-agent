# P2 Round-1 Implementation Audit: Notification Routing & Gotify Fallback

**Auditor:** P2 Round-1 (notification-fallback-gotify dimension)  
**Date:** 2026-06-25  
**Scope:** `notifications.py`, `gotify_fallback.py`, SEV routing matrix, Gotify deployment, channel-name drift, `#alerts` acceptance criteria  
**Methodology:** Code review, filesystem inspection, AST parsing, grep cross-referencing, evidence-doc comparison  

---

## 1. EXECUTIVE SUMMARY

| Metric | Value |
|--------|-------|
| Total findings | 12 |
| CRITICAL | 2 |
| HIGH | 1 |
| MEDIUM | 4 |
| LOW | 2 |
| COSMETIC | 3 |

---

## 2. FINDINGS

### P2-AUD-R1-001 — CRITICAL — `send_alert()` is NEVER called from any consumer

- **File:** `src/discord/notifications.py:201` (definition)
- **Evidence:** Grep for `notifications.send_alert` and `from.*notifications import.*send_alert` across `src/` returns zero results. Grep for `send_alert` returns only the definition in `notifications.py`, `shadow_monitor.py:211` (a different method using webhooks, not `notifications.send_alert`), and `safety_integration.py:458` (a comment referencing it, no actual call).
- **Description:** The entire SEV routing infrastructure is defined (matrix, embed builder, channel lookup, Gotify fallback) but **never invoked**. No module imports `notifications.send_alert` or calls it. Shadow monitor uses its own webhook-based alert. Safety gate in `safety_integration.py` logs a warning instead of calling `send_alert`. The x_poster and gmail notification systems use their own independent `NotificationService` classes.
- **Impact:** CRITICAL. Zero runtime alert delivery. All SEV routing, Gotify fallback, ping/thread features are dead code. AC-DISCORD-003 (SEV0/SEV1 to #alerts within 15s) will always fail. This makes P2-019 (Notification routing) effectively unimplemented in practice.
- **Verification:** CONFIRMED

### P2-AUD-R1-002 — CRITICAL — Acceptance criterion AC-DISCORD-003 targets `#alerts` channel that does not exist

- **Files:**
  - `docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md:129` — "SEV0 and SEV1 alerts must reach `#alerts` within 15 seconds"
  - `docs/10-governance/12-SRS_v1.0.md:75` — SRS-FR-016 lists `#alerts` channel
  - `docs/10-governance/13-FSD_v1.0.md:209` — FSD references `#alerts` channel
  - `docs/setup-evidence/hermes-migration/phase-2-discord.md:69` — migration config references `guinevere-alerts`
  - `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml` — **no `#alerts` or `guinevere-alerts` channel listed** (14 channels total, none named alerts)
  - `src/discord/notifications.py:33-34` — code routes SEV0/SEV1 to `system-health`
- **Description:** Three-way channel-name drift: (1) SRS/FSD/acceptance criteria require `#alerts`; (2) Hermes migration doc references `guinevere-alerts`; (3) runtime code routes to `system-health`. The `#alerts` channel does not exist in `channel-ids.yaml`. The AC-DISCORD-003 acceptance criterion is marked NOT-RUN with EVIDENCE-GAP-DISCORD-003.
- **Impact:** Acceptance criteria cannot be met because the target channel does not exist. Multiple governance documents are inconsistent.
- **Verification:** CONFIRMED

### P2-AUD-R1-003 — HIGH — Gotify deployment has no SOPS-encrypted token and no runtime evidence

- **Files:**
  - `docs/setup-evidence/P2/STEP-P2-020/docker-compose.yml` — compose file only (no systemd unit)
  - `src/discord/gotify_fallback.py:49` — `token = os.environ.get("GOTIFY_APP_TOKEN", "")`
  - `secrets/` — no gotify-related encrypted file exists (`secrets/gotify.enc.yaml` does not exist)
  - `vps-mirror/systemd-live/` — no gotify unit
  - `.env.example:214` — `GOTIFY_APP_TOKEN=your-gotify-app-token-here`
  - `docs/40-operations/47-WebSocketLifecycle_v1.0.md:351` — references `secrets/gotify.enc.yaml` which does not exist
- **Description:** Gotify has a Docker compose artifact but no SOPS-encrypted token file, no systemd service, and no runtime confirmation. The VPS health verifier in P2-020 deferred verification (NEEDS RUNTIME). The operations doc references a `secrets/gotify.enc.yaml` that does not exist in the repo.
- **Impact:** Gotify fallback will silently fail (`send_fallback` returns False when `GOTIFY_APP_TOKEN` is unset). No runtime alert delivery path exists. Operations documentation references non-existent files.
- **Verification:** CONFIRMED for repo evidence; NEEDS RUNTIME for actual VPS deployment

### P2-AUD-R1-004 — MEDIUM — Gotify URL port: 8081 is consistent between code and compose, but old docs reference 8080

- **Files:**
  - `src/discord/gotify_fallback.py:32` — `GOTIFY_URL: str = "http://localhost:8081"`
  - `docs/setup-evidence/P2/STEP-P2-020/docker-compose.yml:7` — `"127.0.0.1:8081:80"`
  - Old `docs/audit/P2-AUDIT-COMPLETE.md:64` — "Port 8080 responds `{"status":"up"}` on `/health`"
- **Description:** The seed fact stated a port mismatch (8081 vs 8080). Verification shows the code and compose file both use **8081**, which is correct. The old audit's mention of 8080 was from a previous state (before the compose file was created) and is now stale. No mismatch exists in current code/artifacts. However, the old audit claim about port 8080 was never corrected in P2-AUDIT-COMPLETE.md.
- **Impact:** LOW. No actual mismatch in current code. Stale documentation only.
- **Verification:** CONFIRMED (no current mismatch; old audit is stale)

### P2-AUD-R1-005 — LOW — GOTIFY_APP_TOKEN is set only via environment, but deployment never sets it

- **File:** `src/discord/gotify_fallback.py:49` — `token = os.environ.get("GOTIFY_APP_TOKEN", "")`
- **Description:** The token is read from env var correctly, but there is no SOPS-encrypted token file (no `secrets/gotify.enc.yaml`), and none of the systemd environment files reference `GOTIFY_APP_TOKEN`. The only reference in `secrets/` is the Discord bot token file. Without the token being deployed, the fallback is disabled.
- **Impact:** Fallback always returns False silently. No notification path to Gotify.
- **Verification:** CONFIRMED

### P2-AUD-R1-006 — MEDIUM — Gotify is not deployed as systemd service; only Docker compose artifact exists

- **Files:**
  - `vps-mirror/systemd-live/` — no gotify unit
  - `docs/setup-evidence/P2/STEP-P2-020/docker-compose.yml` — compose file only
  - `docs/audit/P2-AUDIT-COMPLETE.md:64` — "Gotify binary not in PATH. No systemd service. May be running via Docker"
- **Description:** The deployment artifact is Docker compose only. There is no systemd unit, no timer, and no evidence file confirming `docker-compose up -d` was ever run on the VPS. The old audit marked this as PARTIAL. The VPS health verifier was deferred. No improvement found since the old audit.
- **Impact:** Gotify fallback is non-functional in practice. No runtime alert delivery path to Gotify.
- **Verification:** NEEDS RUNTIME (repo shows no systemd unit, but VPS may have Docker instance running)

### P2-AUD-R1-007 — MEDIUM — `send_alert()` broad except swallows all errors, returns False

- **File:** `src/discord/notifications.py:235-237`
  ```python
  except Exception as exc:
      logger.error("Failed to send %s alert: %s", sev, exc, exc_info=True)
      return False
  ```
- **Description:** The outer exception handler in `send_alert()` catches ALL exceptions, including `AttributeError`, `TypeError`, `KeyError`, network errors, auth errors, serialization issues. It logs the error but returns False, making all failures indistinguishable. This masks configuration problems during debugging (e.g., bad channel name, missing intents, network unreachable). Unlike `gotify_fallback.send_fallback()` which distinguishes timeout vs connection error vs HTTP error, `send_alert()` treats all failures identically.
- **Impact:** Silent failures mask configuration issues. Impossible to distinguish "channel not found" from "network timeout" from "auth failure" without reading logs in detail.
- **Verification:** CONFIRMED

### P2-AUD-R1-008 — MEDIUM — `SRS_v1.0.md`, `FSD_v1.0.md`, and `PRD_v2.2.md` consistently reference `#alerts` channel that does not exist in `channel-ids.yaml`

- **Files:**
  - `docs/10-governance/12-SRS_v1.0.md:75,78,146,202,326,357,397` — seven references to `#alerts`
  - `docs/10-governance/13-FSD_v1.0.md:209,233,235,1130,1132` — five references to `#alerts`
  - `docs/00-core/01-PRD_v2.2.md:55` — references `#alerts`
  - `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml` — 14 channels listed, none named `#alerts` or `guinevere-alerts`
- **Description:** Three core governance documents (PRD, SRS, FSD) consistently name `#alerts` as a required channel, but no such channel exists in the canonical `channel-ids.yaml`. The code routes SEV0/SEV1 to `system-health` instead. This is not just a doc bug: it means the system architecture (governance docs) and the implementation (code + channel-ids.yaml) are fundamentally misaligned on the alert destination channel.
- **Impact:** Documentation-implementation mismatch. Acceptance testing against `#alerts` will fail. Represents a missing channel in the Discord server setup.
- **Verification:** CONFIRMED

### P2-AUD-R1-009 — LOW — Gotify priority mapping is correct but unused because fallback never fires

- **File:** `src/discord/gotify_fallback.py:41-44`
  ```python
  def get_priority(severity: str) -> int:
      mapping = {"SEV0": 10, "SEV1": 7, "SEV2": 5, "SEV3": 3, "SEV4": 1}
      return mapping.get(severity.upper().strip(), 0)
  ```
- **Description:** Priority mapping is well-defined and tested (`test_gotify_fallback.py:31-37` covers all 5 SEVs). However, because `send_alert()` is never called (finding P2-AUD-R1-001), the Gotify fallback in `notifications.py` (called only from `send_alert` for SEV0/SEV1 at lines 230-233) never fires. The fallback is also disconnected from the gotify_fallback module's own `send_fallback` function, which is independently testable but never called from any production code path.
- **Impact:** Well-tested code with zero production utility. Dead code.
- **Verification:** CONFIRMED

### P2-AUD-R1-010 — COSMETIC — Bare `import discord` at line 240 is dead code

- **File:** `src/discord/notifications.py:240`
  ```python
  import discord  # noqa: E402  # isort: skip
  ```
- **Description:** This import is at the bottom of the file after the `send_alert()` function definition. AST analysis confirms two `discord` imports exist: (1) `from discord import utils as discord_utils` at line 19-22 (in a try/except), and (2) `import discord` at line 240. The `send_alert` function has its own fallback re-import at line 208 (`import discord as discord_module`). The line 240 import never affects anything after it because there is no code after it. It is dead code that could theoretically crash the module if `discord.py` is not installed.
- **Impact:** COSMETIC. Does not crash because `send_alert()` is never called (so the import is never triggered during normal operation). If `send_alert()` were to be called, the `from discord import utils` at line 19 can also crash but has its own try/except. The bottom-of-file `import discord` is not in a try/except and could crash on import.
- **Verification:** CONFIRMED

### P2-AUD-R1-011 — COSMETIC — HARD STOP text detection IS wired, contradicting old docstring claim

- **Files:**
  - `src/discord/cmd_safeword.py:591-600` — `handle_safeword_message` docstring says "No bot.py listener exists yet... inactive until P2-017"
  - `src/discord/_entrypoint.py:155-157` — actually imports and calls `handle_safeword_message_async`
  - `src/discord/_entrypoint.py:132-138` — registers `_on_message_listener` which calls `handle_safeword_message_async`
- **Description:** The docstring on `handle_safeword_message` at line 598-601 claims "No bot.py listener exists yet. This function is callable and documented but inactive until P2-017 wires it." However, the actual active entrypoint (`_entrypoint.py`) DOES wire it: `_register_hard_stop_listener` registers `_on_message_listener` which imports and calls `handle_safeword_message_async`. The old docstring is stale. Different from notification routing, the HARD STOP listener IS active.
- **Impact:** COSMETIC. Stale docstring may mislead auditors but does not affect functionality.
- **Verification:** CONFIRMED

### P2-AUD-R1-012 — COSMETIC — `to_discord_embed()` has error handling for `add_field` but other embed methods lack protection

- **File:** `src/discord/notifications.py:190-198`
  ```python
  def to_discord_embed(data: NotificationEmbedData) -> DiscordEmbedProtocol:
      d = _get_discord_embed_module()
      embed = d.Embed(title=data.title, description=data.description, colour=d.Colour(data.color))
      for field in data.fields:
          add_field = getattr(embed, "add_field", None)
          if callable(add_field):
              add_field(name=field.name, value=field.value, inline=field.inline)
      embed.set_footer(text=data.footer_text)
      return embed
  ```
- **Description:** The function uses `getattr(callable)` pattern for `add_field` (defensive), but then calls `embed.set_footer()` directly without the same protection. If the embed factory returns a stub that lacks `set_footer`, this would throw `AttributeError`. The `send_alert()` handler would catch it (broad except), but the asymmetry is inconsistent with the otherwise defensive design.
- **Impact:** COSMETIC. Minor design inconsistency. Would only manifest with non-standard embed factories.
- **Verification:** CONFIRMED

---

## 3. RE-VERIFICATION OF PRIOR FINDINGS (P2-AUDIT-COMPLETE.md)

| Old Finding | Status | Current State |
|---|---|---|
| P2-002: Encrypted secret MISSING | ✅ PARTIALLY RESOLVED | `secrets/discord-secrets.enc.yaml` now EXISTS and is SOPS-encrypted (AES256_GCM, age key). Verified encrypted format without decrypting. Content shows `discord_bot_token` and `discord_bot_id` as SOPS-encrypted values. |
| P2-020: Gotify port 8080 | ✅ RESOLVED | Compose file now uses 8081, matching code. No port mismatch in current artifacts. |
| P2-019: Notification routing ⚠️ PARTIAL | ⬇️ NEW: CRITICAL | Old audit marked PARTIAL. New finding shows `send_alert()` is NEVER called, making the entire routing infrastructure dead code. Severity escalated. |
| P2-010: 33 vs 35 command count | ⏸️ Out of scope | Not covered in this dimension |

---

## 4. GOTIFY DEPLOYMENT STATUS SUMMARY

| Artifact | Exists | Status |
|---|---|---|
| Docker compose (`STEP-P2-020/docker-compose.yml`) | YES | Contains gotify/server:latest, 127.0.0.1:8081:80, external network, volume mount |
| SOPS-encrypted token (`secrets/gotify.enc.yaml`) | NO | Does not exist. Operations doc references it but file absent. |
| systemd unit | NO | No `guinevere-gotify.service` in repo or vps-mirror |
| Evidence of `docker-compose up` | NO | No verification file confirms deployment |
| VPS health check | DEFERRED | Old verifier marked NEEDS RUNTIME |

**Verdict:** Gotify expects deployment via Docker compose. Without a systemd unit or cron to manage the container lifecycle, it depends on manual `docker-compose up -d` on the VPS. This is **NEEDS RUNTIME VERIFICATION**.

---

## 5. CHANNEL NAME DRIFT MAP

| Document | Channel Name for Alerts | Exists in channel-ids.yaml? |
|---|---|---|
| SRS v1.0, FSD v1.0, PRD v2.2, AC-Catalog | `#alerts` | NO |
| phase-2-discord.md (Hermes config) | `guinevere-alerts` | NO |
| `notifications.py` (runtime code) | `system-health` | YES |
| `channel-ids.yaml` | N/A | Yes (system-health: 1510914612038471720) |

---

## 6. RECOMMENDED ACTIONS

| Priority | Action |
|----------|--------|
| 🔴 CRITICAL | Wire `notifications.send_alert()` into a production code path (shadow_monitor, safety_integration, or on_message handler) |
| 🔴 CRITICAL | Resolve channel-name drift: create `#alerts` or `guinevere-alerts` channel, update `channel-ids.yaml`, reconcile SRS/FSD/PRD references |
| 🟡 HIGH | Create SOPS-encrypted `secrets/gotify.enc.yaml` with `GOTIFY_APP_TOKEN` for deployment |
| 🟡 MEDIUM | Deploy Gotify via Docker compose or systemd unit on VPS; verify with health check |
| 🟡 MEDIUM | Add `GOTIFY_APP_TOKEN` to systemd environment loading for the relevant service unit |
| 🔵 LOW | Update stale docstring in `cmd_safeword.py:598-601` |
| 🔵 LOW | Correct P2-AUDIT-COMPLETE.md port 8080 mention to 8081 |
| 🟢 COSMETIC | Remove dead `import discord` at `notifications.py:240` or wrap in try/except |

---

## 7. VERIFICATION NOTES

- All findings are CONFIRMED via static analysis of repo files. Runtime verification is explicitly noted where applicable.
- No files were edited, created, or deleted except this output file.
- No secrets were decrypted, logged, or reproduced.
- No Discord API calls were made. No services were restarted.
- Environment: Windows dev box (bash), not VPS.

---

*End of audit report.*
