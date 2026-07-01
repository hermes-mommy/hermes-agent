# P2 Round-2 Adversarial Verification: Notification / Fallback / Gotify

**Date:** 2026-06-25
**Auditor:** Claude Code (read-only subagent — round-2 adversary)
**Source:** `docs/setup-evidence/legacy-audit/P2/audits/round-1/notification-fallback-gotify.md`
**Methodology:** Independently verify each R1 finding; attempt to refute; miss-hunt for gaps.

---

## PART 1: FINDING-BY-FINDING VERIFICATION

### P2-AUD-R1-001 [CRITICAL] — `send_alert()` is NEVER called
- **R1 claim:** `send_alert()` is defined but never invoked from any production module.
- **Independent verification:** Grep `send_alert` across `src/`, `hermes-config/`, `scripts/`:
  - `src/discord/notifications.py:201` — definition only
  - `src/discord/shadow_monitor.py:211` — different method (`self._send_alert` using webhooks, not `notifications.send_alert`)
  - `src/discord/listeners/x_reactions.py:197` — comment referencing `send_alert` (not a call)
  - `safety_integration.py:458` — comment referencing `send_alert` (not a call)
  - Zero actual imports or calls of `notifications.send_alert`
- **Verdict:** **CONFIRMED — CRITICAL**. The entire SEV routing pipeline is dead code. No production path invokes it.
- **Refutation attempt:** Maybe `send_alert` is called via dynamic dispatch? No `getattr` or `__import__` patterns found. Maybe it's called from a test? Yes, `test_notifications.py` calls it — but tests don't count as production code. **Cannot refute.**

### P2-AUD-R1-002 [CRITICAL] — AC-DISCORD-003 targets non-existent `#alerts` channel
- **R1 claim:** Acceptance criterion requires `#alerts` channel, but it doesn't exist.
- **Independent verification:**
  - Read `docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md:129` — "SEV0 and SEV1 alerts must reach #alerts within 15 seconds"
  - Read `docs/10-governance/12-SRS_v1.0.md:75` — SRS-FR-016 references `#alerts`
  - Read `docs/10-governance/13-FSD_v1.0.md:209` — FSD references `#alerts`
  - Read `channel-ids.yaml` — 14 channels, none named `#alerts` or `guinevere-alerts`
  - Read `notifications.py:33` — SEV0/SEV1 route to `system-health`
- **Verdict:** **CONFIRMED — CRITICAL**. Governance docs specify a channel that doesn't exist. Code routes to a different channel. The acceptance criterion is unverifiable.
- **Refutation attempt:** Could `#alerts` be a governance-level alias for `system-health`? No alias mechanism exists. The governance docs are separate from the implementation. Different teams could have specified different names. **Cannot refute — this is a governance/implementation misalignment.**

### P2-AUD-R1-003 [HIGH] — Gotify has no SOPS token and no runtime evidence
- **R1 claim:** `secrets/gotify.enc.yaml` doesn't exist. No systemd unit. No runtime confirmation.
- **Independent verification:**
  - Checked `secrets/` — no `gotify.enc.yaml` or `gotify-secrets.yaml`
  - Checked `vps-mirror/systemd-live/` — no gotify unit
  - Checked `systemd/` — no gotify unit
  - Read `.env.example:214` — `GOTIFY_APP_TOKEN=your-gotify-app-token-here` (placeholder)
  - Read `docs/40-operations/47-WebSocketLifecycle_v1.0.md:351` — references `secrets/gotify.enc.yaml` which does not exist
- **Verdict:** **CONFIRMED — HIGH**. No SOPS token, no systemd unit, no deployment evidence. Operations doc references non-existent file.
- **Refutation attempt:** Maybe Gotify is deployed via Docker without a systemd unit? Docker compose exists but no evidence of `docker-compose up`. **Cannot refute — needs runtime verification.**

### P2-AUD-R1-004 [MEDIUM] — Gotify port 8081 consistent, old docs say 8080
- **R1 claim:** Code and compose both use 8081. Old audit claimed 8080.
- **Independent verification:** Confirmed `gotify_fallback.py:32` — 8081. Confirmed `docker-compose.yml:7` — `"127.0.0.1:8081:80"`. Old audit P2-AUDIT-COMPLETE.md:64 — "Port 8080". Code and compose are consistent.
- **Verdict:** **CONFIRMED** — but NOT a current bug. Old audit inaccuracy. **Downgrade to LOW.**
- **Refutation attempt:** No current mismatch exists. **Cannot refute — but severity overstated.**

### P2-AUD-R1-005 [LOW] — GOTIFY_APP_TOKEN only via env, deployment never sets it
- **R1 claim:** No `GOTIFY_APP_TOKEN` in any SOPS file or systemd environment.
- **Independent verification:**
  - Grep `GOTIFY_APP_TOKEN` across repo — found in `.env.example:214` (placeholder), `gotify_fallback.py:49` (env read), `docs/40-operations/47-WebSocketLifecycle_v1.0.md:351` (reference). No systemd EnvironmentFile sets it. No SOPS file contains it.
- **Verdict:** **CONFIRMED — LOW**. Token env var is never populated in deployment.
- **Refutation attempt:** The VPS might have it set in a runtime env file not in the repo. **Cannot verify without VPS access.**

### P2-AUD-R1-006 [MEDIUM] — Gotify not deployed as systemd service
- **R1 claim:** Only Docker compose artifact exists. No systemd unit.
- **Independent verification:** Checked `vps-mirror/systemd-live/` — 12 units, none gotify-related. Checked `systemd/` — no gotify unit. Checked `deploy/` — no gotify directory. Docker compose file exists at `docs/setup-evidence/P2/STEP-P2-020/docker-compose.yml`.
- **Verdict:** **CONFIRMED — MEDIUM**. Docker compose only. No systemd deployment. No evidence of container runtime.
- **Refutation attempt:** VPS may have a Docker container running without systemd. **NEEDS RUNTIME VERIFICATION.**

### P2-AUD-R1-007 [MEDIUM] — `send_alert()` broad except swallows all errors
- **R1 claim:** `except Exception` at line 235 catches everything, returns False.
- **Independent verification:** Read `notifications.py:235-237` — confirmed `except Exception as exc: logger.error(...); return False`. All failure modes (channel not found, network error, auth error, serialization error) are indistinguishable.
- **Verdict:** **CONFIRMED — MEDIUM**. Silent failure masking. But since `send_alert()` is never called, this is latent.
- **Refutation attempt:** The broad except is dead code since `send_alert()` is never called. **Cannot refute — latent bug.**

### P2-AUD-R1-008 [MEDIUM] — SRS/FSD/PRD reference `#alerts` channel that doesn't exist
- **R1 claim:** Core governance documents consistently name `#alerts` but no such channel exists.
- **Independent verification:** Grep `#alerts` across `docs/10-governance/` — found in SRS (7 refs), FSD (5 refs), PRD (1 ref). All reference a channel that doesn't exist in `channel-ids.yaml`.
- **Verdict:** **CONFIRMED — MEDIUM**. Governance docs are misaligned with implementation.
- **Refutation attempt:** Could `#alerts` be a planned channel not yet created? No evidence of a planned creation. **Cannot refute.**

### P2-AUD-R1-009 [LOW] — Gotify priority mapping correct but unused
- **R1 claim:** `get_priority()` mapping is well-defined but never called in production.
- **Independent verification:** `gotify_fallback.py:41-44` — priority mapping is correct. Tests exist at `test_gotify_fallback.py:31-37`. But `send_fallback()` is only called from `send_alert()`, which is never called. Dead code.
- **Verdict:** **CONFIRMED — LOW**. Well-tested, never used.
- **Refutation attempt:** The mapping is correct. The bug is the dead call path, not the mapping. **Confirmed.**

### P2-AUD-R1-010 [COSMETIC] — Bare `import discord` at line 240
- **R1 claim:** `notifications.py:240` has dead `import discord`.
- **Independent verification:** Read the file — confirmed. As noted in the security round-2 verification, `shadow_monitor.py` imports `notifications.py`, so this import IS executed. **This is NOT dead code — it's a live import chain.**
- **Verdict:** **CONFIRMED — upgraded from COSMETIC to HIGH**. The import chain `shadow_monitor.py → notifications.py → import discord` would crash if `discord.py` is absent.
- **Refutation attempt:** This is a real crash path, not cosmetic. **Upgraded.**

### P2-AUD-R1-011 [COSMETIC] — HARD STOP docstring stale
- **R1 claim:** `cmd_safeword.py` docstring says "No bot.py listener exists yet" but `_entrypoint.py` wires it.
- **Independent verification:** Read `cmd_safeword.py:598-601` — "No bot.py listener exists yet. This function is callable and documented but inactive until P2-017 wires it." Read `_entrypoint.py:155-157` — DOES wire it. The docstring is stale.
- **Verdict:** **CONFIRMED — COSMETIC**. Stale docstring. Functionality is correct.
- **Refutation attempt:** The docstring is wrong. **Cannot refute — but cosmetic.**

### P2-AUD-R1-012 [COSMETIC] — `to_discord_embed()` inconsistent error handling
- **R1 claim:** `add_field` uses defensive `getattr(callable)` but `set_footer` doesn't.
- **Independent verification:** Read `notifications.py:190-198` — confirmed asymmetry. `add_field` checks `getattr(embed, "add_field", None)` and `callable()`. `set_footer` is called directly without protection.
- **Verdict:** **CONFIRMED — COSMETIC**. Design inconsistency. Would only matter with non-standard embed factories.
- **Refutation attempt:** This is cosmetic. In practice, `discord.Embed` always has `set_footer`. **Cannot refute — but cosmetic.**

---

## PART 2: MISS-HUNT — Findings Round-1 Missed

### P2-AUD-R2-NTF-001 [HIGH] — `shadow_monitor.py` imports `NotificationEmbedField` from `notifications.py`, creating a live import chain that would crash
- **Evidence:** `src/discord/shadow_monitor.py:17` — `from .notifications import NotificationEmbedField`. `notifications.py:240` — `import discord`. If `discord.py` is absent, this chain crashes on import.
- **Impact:** Any module importing `shadow_monitor` or `notifications` crashes. This is a HIGH severity crash bug, not cosmetic.
- **Severity:** HIGH
- **Verification:** CONFIRMED

### P2-AUD-R2-NTF-002 [MEDIUM] — `shadow_monitor.py` has its own `_send_alert()` method using webhooks — duplicate notification path
- **Evidence:** `src/discord/shadow_monitor.py:211` — `async def _send_alert(self, ...)` sends via webhook URL, not through `notifications.send_alert()`. This is a second, independent notification path that bypasses the SEV routing matrix.
- **Impact:** Two notification systems: `notifications.py` (dead code) and `shadow_monitor.py` (webhook-based, also disabled). No unified notification path.
- **Severity:** MEDIUM
- **Verification:** CONFIRMED

### P2-AUD-R2-NTF-003 [MEDIUM] — `shadow_pipeline.py` is disabled by default (`enabled=False`, `traffic_pct=0`)
- **Evidence:** Read `src/discord/shadow_pipeline.py` — defaults to `enabled=False`, `traffic_pct=0`. No deployment mechanism to enable it.
- **Impact:** The shadow pipeline (Hermes parity testing) is implemented but disabled. If P2 shadow mode was a deliverable, it's not operational.
- **Severity:** MEDIUM
- **Verification:** CONFIRMED

### P2-AUD-R2-NTF-004 [LOW] — `gotify_fallback.py` has `GOTIFY_URL` hardcoded — no env var override
- **Evidence:** `gotify_fallback.py:32` — `GOTIFY_URL: str = "http://localhost:8081"`. No `GOTIFY_URL` env var override. Hardcoded URL.
- **Impact:** If Gotify runs on a different port or host, the fallback silently fails. No configuration flexibility.
- **Severity:** LOW
- **Verification:** CONFIRMED

### P2-AUD-R2-NTF-005 [LOW] — `notifications.py:230-233` only calls Gotify fallback for SEV0/SEV1
- **Evidence:** `notifications.py:230-233` — `if normalized in ("SEV0", "SEV1"): from .gotify_fallback import send_fallback as _send_gotify; await _send_gotify(title, description, normalized)`. Only SEV0/SEV1 trigger Gotify. SEV2-4 are Discord-only.
- **Impact:** This is by design (Gotify is for critical alerts only), but it means SEV2-4 notifications have no fallback if Discord is down.
- **Severity:** LOW
- **Verification:** CONFIRMED

---

## 3. VERIFICATION SUMMARY

| Round-1 ID | Severity | Round-2 Verdict | Notes |
|------------|----------|----------------|-------|
| R1-001 | CRITICAL | CONFIRMED | send_alert() never called |
| R1-002 | CRITICAL | CONFIRMED | #alerts channel nonexistent |
| R1-003 | HIGH | CONFIRMED | Gotify no SOPS token |
| R1-004 | MEDIUM→LOW | CONFIRMED (downgraded) | Port 8081 consistent |
| R1-005 | LOW | CONFIRMED | GOTIFY_APP_TOKEN never set |
| R1-006 | MEDIUM | CONFIRMED | Gotify no systemd unit |
| R1-007 | MEDIUM | CONFIRMED | Broad except swallows errors |
| R1-008 | MEDIUM | CONFIRMED | Governance docs #alerts drift |
| R1-009 | LOW | CONFIRMED | Priority mapping unused |
| R1-010 | COSMETIC→HIGH | **UPGRADED** | `import discord` is live crash path |
| R1-011 | COSMETIC | CONFIRMED | Stale HARD STOP docstring |
| R1-012 | COSMETIC | CONFIRMED | Inconsistent error handling |

**Round-1: 12/12 findings CONFIRMED. 2 severity changes (1 downgraded MED→LOW, 1 upgraded COSM→HIGH). 5 new findings from miss-hunt (1 HIGH, 2 MED, 2 LOW).**

**Total in this dimension: 12 confirmed + 5 new = 17 unique findings.**

---

*End of round-2 adversarial verification for notification/fallback/gotify dimension.*