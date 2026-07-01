# P2 Implementation Gap Register

**Date:** 2026-06-25
**Auditor:** Read-only implementation audit
**Scope:** Every placeholder, mock, hardcoded, fallback, unwired, half-implemented, or superseded surface in P2.
**Method:** Cross-referenced all audit files against source code.

---

## 1. GAPS BY CATEGORY

### 1.1 DEAD CODE (Implemented but never called/invoked)

| ID | Surface | What's Missing | Severity | Superseded By |
|----|---------|---------------|----------|--------------|
| GAP-DEAD-001 | `notifications.py:201` `send_alert()` | **NEVER CALLED from any production module.** Entire SEV routing pipeline (SEV0-SEV4 matrix, embed builder, Gotify fallback, ping/thread features) is dead code. Zero imports by any production file. | CRITICAL | P20 `alertmanager.yml` (separate alerting path) |
| GAP-DEAD-002 | `cmd_pc.py` (445 lines) | **Fully implemented but never registered.** Not in `_command_registry.py`, not imported by `_entrypoint.py`. 445 lines of dead code. | HIGH | None — true gap |
| GAP-DEAD-003 | `gotify_fallback.py` `send_fallback()` | **Technically callable from `notifications.py:230-233`**, but `send_alert()` is never called, so the fallback never fires. Well-tested code with zero production utility. | HIGH | None — true gap |
| GAP-DEAD-004 | `_entrypoint.py` `_sync_handler()` callback | **Never invoked.** The `sync_handler` is defined but no `tree.on_sync` or `tree.on_error` event is wired to call it. | LOW | None — true gap |

### 1.2 UNWIRED / INACTIVE

| ID | Surface | What's Missing | Severity | Superseded By |
|----|---------|---------------|----------|--------------|
| GAP-UNWIRED-001 | HARD STOP text detection | **CORRECTION: HARD STOP IS wired.** `_entrypoint.py:155-157` calls `handle_safeword_message_async`. The docstring in `cmd_safeword.py:598-601` is stale. This is a DOCS gap, not an implementation gap. | N/A (false positive) | N/A |
| GAP-UNWIRED-002 | `listeners/x_reactions.py` | **Module exists but is not wired into `_entrypoint.py`.** The `on_x_reaction` handler is defined but never registered as a listener. | LOW | None — true gap |
| GAP-UNWIRED-003 | `listeners/gmail_reactions.py` | **Module exists but is not wired into `_entrypoint.py`.** The `on_gmail_reaction` handler is defined but never registered. | LOW | None — true gap |
| GAP-UNWIRED-004 | `loops/x_poster_dashboard.py` | **Module exists in `loops/` package but `loops/__init__.py` is empty.** No import or wiring in `_entrypoint.py`. | LOW | None — true gap |

### 1.3 HALF-IMPLEMENTED

| ID | Surface | What's Missing | Severity | Superseded By |
|----|---------|---------------|----------|--------------|
| GAP-HALF-001 | Gotify deployment | **Docker compose exists but:** no SOPS-encrypted token (`secrets/gotify.enc.yaml` missing), no systemd unit, no `GOTIFY_APP_TOKEN` in any EnvironmentFile, no evidence of `docker-compose up`. P2-020/021 checkboxes remain unchecked in PROGRESS.md. | HIGH | None — true gap |
| GAP-HALF-002 | P2-009 Administrator OAuth reauthorization | **Documented as needed but NOT done.** `permissions.py` is deprecated (ImportError on `src.discord.guild_setup`). No active least-privilege mechanism. Administrator permission still active. CHECKLIST.md:290 shows unchecked. | HIGH | None — true gap |
| GAP-HALF-003 | Channel-level permissions (P2-007/P2-008) | **All permission code is in `src/_deprecated/hermes-migration-phase-7/permissions.py`** which has an ImportError and is effectively dead. No active permission module. | MEDIUM | None — true gap |
| GAP-HALF-004 | `/help` command completeness | **`command_catalog.py` has 39 commands** but `_command_registry.py` has 49. Users miss 10 commands in /help output (health, advanced memory, loop monitoring). The code dynamically generates output, so it's a data gap, not a logic gap. | MEDIUM | None — true gap |
| GAP-HALF-005 | Shadow pipeline | **`shadow_pipeline.py` defaults to `enabled=False`, `traffic_pct=0`.** No deployment mechanism. No shadow-mode evidence. Hermes migration (phase-2-discord.md) outlines shadow mode but it's aspirational. | MEDIUM | Hermes Gateway (planned) |
| GAP-HALF-006 | P2-020 Gotify "install + test" | **PROGRESS.md checkbox is CHECKED** but code is dead, no SOPS token, no systemd unit, no runtime evidence. The checkbox is inaccurate. | MEDIUM | None — true gap |
| GAP-HALF-007 | P2-021 Discord→Gotify fallback | **PROGRESS.md checkbox is CHECKED** but `send_alert()` is never called, so the fallback never fires. Gotify token is not deployed. The checkbox is inaccurate. | MEDIUM | None — true gap |

### 1.4 HARDCODED / BRITTLE

| ID | Surface | What's Missing | Severity | Superseded By |
|----|---------|---------------|----------|--------------|
| GAP-HARD-001 | `gotify_fallback.py:32` `GOTIFY_URL = "http://localhost:8081"` | **Hardcoded URL.** No env var override. No configuration file. | LOW | None |
| GAP-HARD-002 | `notifications.py:33-37` channel names | **Hardcoded channel names** (`system-health`, `cost-tracker`, `guinevere-status`, `audit-log`). No configuration mapping. Channel rename requires code change. | LOW | None |
| GAP-HARD-003 | `_startup.py:338` `name="guinevere-status"` | **Hardcoded channel name** for startup greeting. No configuration. | LOW | None |
| GAP-HARD-004 | `cmd_safeword.py` embed fields | **Static embed fields** — "Safe mode active", "Neutral / supportive", "Y0", "Paused". No dynamic state from handler. `_build_safeword_fields` returns identical tuples regardless of handler state. | LOW | None |
| GAP-HARD-005 | `shadow_monitor.py:90` `GUILD_ID` hardcoded | **`1510876414671323206`** is hardcoded instead of reading from environment. | LOW | None |

### 1.5 SUPERSEDED (Gap because intentionally replaced)

| ID | Surface | What's Missing | Severity | Superseded By |
|----|---------|---------------|----------|--------------|
| GAP-SUP-001 | Standalone `guinevere-discord.service` | **Intentionally masked per P2-022 / ADR-035.** The service is not running — this is DESIGN, not a gap. But the transition is not documented clearly enough. | LOW (design) | Hermes Gateway + P20 REST publisher |
| GAP-SUP-002 | `bot.py.bak.pre-phase2` + `conversational_handler.py.bak.pre-phase2` | **Old standalone bot archived.** No imports of these files. Clean archiving. | COSMETIC | `_entrypoint.py` (current entrypoint) |
| GAP-SUP-003 | Slash commands → Hermes plugins | **phase-2-discord.md plans 35 plugin files.** 0 exist at documented paths. Actual architecture uses `commands_*/` subdirectories under `hermes_plugins/`. The migration doc is aspirational. | MEDIUM | Hermes Gateway (partial — 47 Hermes plugins exist) |
| GAP-SUP-004 | `notifications.py` channel routing vs P20 dashboard writer | **P2 notifications use direct channel names.** P20 uses `discord_rest_client.py` for dashboard/log publishing. Two separate writing paths. | LOW | P20 REST publisher |

---

## 2. GAP VS SUPERSEDED DISTINCTION

**True gaps** (need implementation):
- GAP-DEAD-001: `send_alert()` never called → wire into production path
- GAP-DEAD-002: `cmd_pc.py` dead code → register or delete
- GAP-HALF-001: Gotify deployment → deploy + SOPS token
- GAP-HALF-002: Administrator OAuth → reauthorize with reduced scope
- GAP-HALF-003: Channel permissions → fix deprecated module
- GAP-HALF-004: /help completeness → add missing commands to catalog
- GAP-UNWIRED-002/003/004: Unwired listeners/loops → wire or delete

**Superseded gaps** (intentional, just need docs):
- GAP-SUP-001: Masked service → document transition clearly
- GAP-SUP-002: Archived .bak files → document archive
- GAP-SUP-003: Hermes plugin migration → update migration doc to reflect actual structure
- GAP-SUP-004: Dual Discord writers → document complementary architecture

---

## 3. SEVERITY SUMMARY

| Category | Count | CRITICAL | HIGH | MEDIUM | LOW | COSMETIC |
|----------|-------|----------|------|--------|-----|----------|
| Dead Code | 4 | 1 | 2 | 0 | 1 | 0 |
| Unwired | 3 | 0 | 0 | 0 | 3 | 0 |
| Half-Implemented | 7 | 0 | 2 | 5 | 0 | 0 |
| Hardcoded | 5 | 0 | 0 | 0 | 5 | 0 |
| Superseded | 4 | 0 | 0 | 1 | 2 | 1 |
| **TOTAL** | **23** | **1** | **4** | **6** | **11** | **1** |

---

## 4. RECOMMENDED FIX ORDER

1. Wire `send_alert()` into production path (or delete `notifications.py` if P20 alertmanager entirely replaces it)
2. Deploy Gotify with SOPS token + systemd unit (or document that P2-020/021 are deferred)
3. Complete Administrator OAuth reauthorization (P2-009)
4. Register `cmd_pc.py` or delete the 445-line dead module
5. Fix deprecated `permissions.py` (P2-007/P2-008)
6. Add missing commands to `/help` catalog
7. Wire or delete unwired listeners/loops
8. Make hardcoded URLs/channel names configurable

---

*End of implementation gap register.*