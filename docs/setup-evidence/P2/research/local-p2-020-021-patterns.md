# Local Codebase Research: P2-020 / P2-021 Patterns

**Date:** 2026-06-01
**Scope:** Local-only references for Gotify installation, Discord→Gotify fallback, notification routing, and related evidence for P2-020/P2-021.
**Status:** Complete

## Executive Summary

The local codebase already contains the canonical P2-020/P2-021 step definitions in `stepprompts/StepPrompts.md`, the progress/checklist trackers, prior research, and notification routing implementation context. The strongest local references are:

- `stepprompts/StepPrompts.md` lines 5812-5884 for the exact P2-020/P2-021 step payloads.
- `PROGRESS.md` lines 139-141 and `CHECKLIST.md` lines 257-259 for current completion state.
- `docs/setup-evidence/P2/research/step-prompts-017-019.md` lines 14-16, 22-30, 349-350 for adjacent batch context and deferred Gotify items.
- `docs/setup-evidence/P2/batch-017-019-final-report.md` lines 181-186 for the batch handoff note that P2-020 is next.
- `audit-reports/stepprompts-audit/D2-D5-adr-dependency.md` lines 201-218 for dependency correction: P2-021 should depend on P2-020, not only P2-019.
- `audit-reports/2026-05-31-stepprompts-full-audit.md` lines 50-53 for hardcoded Gotify password findings.
- `src/discord/notifications.py`, `src/discord/startup.py`, `src/discord/bot.py`, `src/discord/guild_setup.py`, and `src/discord/permissions.py` as local implementation touchpoints for notification routing and related channels.
- `docs/setup-evidence/P2/STEP-P2-019/p2-019-implementation-summary.md` for the current SEV routing architecture that P2-020/P2-021 will extend.

## Exact Local References

### 1) StepPrompts canonical P2-020 / P2-021 definitions

**File:** `stepprompts/StepPrompts.md`

- Lines **5812-5847**: P2-020 Gotify installation.
  - Docker compose at `/home/guinevere/config/gotify/docker-compose.yml`
  - Image: `gotify/server:latest`
  - Port mapping: `127.0.0.1:8081:80`
  - Volume: `/home/guinevere/data/gotify:/app/data`
  - Environment uses `GOTIFY_DEFAULTUSER_PASS=${GOTIFY_ADMIN_PASSWORD}` with SOPS-encrypted secrets note.
  - Start commands: `docker compose up -d`, `curl -s http://localhost:8081/version`
- Lines **5849-5884**: P2-021 Discord→Gotify fallback.
  - Module path: `src/discord/gotify_fallback.py`
  - Fallback URL: `http://localhost:8081`
  - Function: `async def send_gotify(title: str, message: str, priority: int = 5)`
  - Uses `httpx.AsyncClient()` and POSTs to `/message`
  - Logs `gotify_sent`, `gotify_failed`, `gotify_unreachable`
  - Test command posts to `/message`
  - Verification/evidence/rollback text included.
- Line **5849** explicitly annotates the dependency as “P2-020 Gotify installed”.
- Line **5882** lists evidence paths using `docs/setup-evidence/P2/STEP-P2-020/` and `.../STEP-P2-021/`.

**Older stale copy:** `stepprompts/StepPrompts.md.bak`
- Same section exists around lines **5665-5732**, useful only as backup context, not canonical.

### 2) Progress / checklist state

**File:** `PROGRESS.md`
- Lines **139-141**:
  - P2-019 notification routing test = done
  - P2-020 Gotify installation + test = pending
  - P2-021 Discord → Gotify fallback test = pending

**File:** `CHECKLIST.md`
- Lines **255-259**:
  - P2-017 active service check done
  - P2-018 gateway connected done
  - P2-019 SEV0 thread within 15s done
  - P2-020 `systemctl status gotify` active; test notification received on phone pending
  - P2-021 simulate Discord outage → Gotify fallback notification sent pending

### 3) Batch / research context showing P2-020/021 as deferred

**File:** `docs/setup-evidence/P2/research/step-prompts-017-019.md`
- Lines **14-16**: P2-020/021 are separate steps after P2-017..019; StepPrompts section contains stale snippets.
- Lines **22-30**: local source list includes `src/discord/startup.py`, `src/discord/cmd_safeword.py`, and checklist evidence; this batch set the pattern context for later work.
- Lines **349-350**: deferred items table explicitly lists Gotify installation = P2-020 and Discord→Gotify fallback = P2-021.
- Lines **299-302**: P2-019 has no Gotify integration yet; module exposes `send_alert()` for future wiring.

**File:** `docs/setup-evidence/P2/batch-017-019-final-report.md`
- Lines **181-186**: tracker sync says P2 is 19/21 and next is P2-020 Gotify installation + test, then P2-021 full integration test.

### 4) ADR / audit evidence for dependency and security concerns

**File:** `audit-reports/stepprompts-audit/D2-D5-adr-dependency.md`
- Lines **201-218**: explicit finding that P2-021 incorrectly depended on P2-019; should depend on P2-020 (or P2-019, P2-020 if both needed).
- Lines **216-218**: rationale—P2-021 sends to Gotify at `http://localhost:8081`, so service installation must exist first.

**File:** `audit-reports/2026-05-31-stepprompts-full-audit.md`
- Lines **50-53**: hardcoded secret findings include P2-020 `GOTIFY_DEFAULTUSER_PASS=changeme`; must use env file + SOPS per ADR-015/Security Policy.

**File:** `audit-reports/stepprompts-audit/phase2-fixes-applied.md`
- Lines **20** and **75**: notes that P2-021 dependency fix was applied in StepPrompts, adding explicit dependency annotation on P2-020.

### 5) Notification routing implementation touchpoints already in code

These are the local source files most relevant to implementing or wiring P2-020/P2-021:

- `src/discord/notifications.py`
  - `send_alert(...)` exists already.
  - Grep results show channel constants:
    - `SEV0_CHANNEL = "system-health"`
    - `SEV1_CHANNEL = "system-health"`
    - `SEV3_CHANNEL = "guinevere-status"`
    - `SEV4_CHANNEL = "audit-log"`
  - This is the primary routing module that future Gotify fallback would likely wrap or extend.
- `src/discord/startup.py`
  - Startup greeting targets `guinevere-status`.
  - `on_ready(client)` exists and is called by bot entrypoint.
- `src/discord/bot.py`
  - Imports `get_intents`, `startup.on_ready`, `handle_safeword_message_async`, and `safeword_callback`.
  - Contains `bot_ready` and `commands_synced` logging hooks.
- `src/discord/guild_setup.py`
  - Declares channel specs for `guinevere-status`, `system-health`, and `audit-log`.
- `src/discord/permissions.py`
  - `APPEND_ONLY_CHANNELS` includes `audit-log` and evidence channels.
- `src/discord/intents.py`
  - `get_intents()` is present and part of the bot wiring.

### 6) Existing evidence from P2-019 that likely anchors P2-020/021 integration

**File:** `docs/setup-evidence/P2/STEP-P2-019/p2-019-implementation-summary.md`
- Lines **4-7**: P2-019 created `src/discord/notifications.py` with protocol-driven SEV routing.
- Lines **25-30**: routing matrix currently maps SEV0/1 to `#system-health`, SEV3 to `#guinevere-status`, SEV4 to `#audit-log`.
- Lines **42-46**: notes channel lookup by name, WIB timestamps, and no hardcoded user IDs.
- This is the immediate implementation baseline for any Gotify fallback wiring.

## Likely Implementation Touchpoints

Based strictly on local files, the likely touchpoints for P2-020/P2-021 are:

1. **Gotify service definition / install path**
   - `stepprompts/StepPrompts.md` says `/home/guinevere/config/gotify/docker-compose.yml` and `/home/guinevere/data/gotify`.
   - Security caveat: the hardcoded password in the stale prompt was audited as invalid; use env/SOPS pattern if implementing.

2. **Gotify fallback module**
   - `src/discord/gotify_fallback.py` is the intended new module path from StepPrompts.
   - The current codebase does not show this file in local source search results, so it is a likely creation point.

3. **Notification routing integration**
   - `src/discord/notifications.py` is the current SEV router and likely needs to call or delegate to Gotify fallback on Discord outage or route failure.
   - `src/discord/bot.py` and `src/discord/startup.py` are the runtime entrypoints where failures and startup/health signals are surfaced.

4. **Channel / severity mapping alignment**
   - `src/discord/guild_setup.py` and `src/discord/permissions.py` establish the canonical channel names and append-only constraints.
   - `CHECKLIST.md` and `PROGRESS.md` define the acceptance criteria and status checks to update after implementation.

5. **Evidence / verification outputs**
   - `docs/setup-evidence/P2/STEP-P2-020/` and `docs/setup-evidence/P2/STEP-P2-021/` are the expected evidence directories per StepPrompts.
   - No local `verification.md` exists yet for P2-019 or these future steps in the current tree search results.

## Notes on Local-Only Constraint

This report uses only local repository files and local evidence. No external documentation or web research was used.

## Footer

- Generated for P2-020 / P2-021 local pattern research.
- Canonical references should be treated as `stepprompts/StepPrompts.md`, `PROGRESS.md`, `CHECKLIST.md`, local `src/discord/*`, and local audit/evidence files listed above.
