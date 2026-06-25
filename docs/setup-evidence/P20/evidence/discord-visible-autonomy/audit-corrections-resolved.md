# Brutal Audit Corrections — Resolution Evidence (2026-06-24)

This file resolves the 5 blockers raised in the brutal audit correction. Each has live VPS proof (no secrets).

---

## Blocker 1 — `guinevere-discord.service` state mismatch ✅ RESOLVED (masked)

**Problem:** systemctl showed `is-enabled: enabled`, `is-active: inactive` — NOT masked, but evidence said "masked by design".

**Action:** Properly masked the unit (backed up the real unit file, removed it, symlinked to `/dev/null`).

Live proof:
```
$ systemctl mask guinevere-discord.service
Created symlink /etc/systemd/system/guinevere-discord.service → /dev/null
$ systemctl is-enabled guinevere-discord.service
masked
$ systemctl is-active guinevere-discord.service
inactive
$ ls -la /etc/systemd/system/guinevere-discord.service
lrwxrwxrwx ... guinevere-discord.service -> /dev/null
```
Backup preserved at `/etc/systemd/system/guinevere-discord.service.bak`. The standalone bot is now genuinely masked by design; the core REST publisher is the correct Discord writer.

---

## Blocker 2 — Memory headroom ✅ RESOLVED (2G/4G)

**Problem:** `MemoryHigh=384M`, `MemoryMax=512M`, current ~402MB (above High) — too tight for a 16GB VPS soak.

**Action:** Tuned the memory drop-in (only `guinevere-core.service`); VPS has 15Gi RAM / 10Gi available.

`/etc/systemd/system/guinevere-core.service.d/memory.conf`:
```
[Service]
MemoryHigh=2G
MemoryMax=4G
```
Live proof after daemon-reload + restart:
```
MemoryCurrent=498434048   (~475M, well under High)
MemoryHigh=2147483648     (2G)
MemoryMax=4294967296      (4G)
core is-active: active    NRestarts=0  Result=success
```
**No other service disturbed** — before/after snapshot of active guinevere services identical:
```
guinevere-core.service
guinevere-mcp.service
guinevere-monitoring.service
guinevere-whatsapp.service
guinevere-x-poster.service
(diff: IDENTICAL)
```

---

## Blocker 3 — Dashboard message ID mismatch ✅ RESOLVED (canonical)

**Problem:** Two IDs appeared — `1518941820569256036` and `1518941820569256030` — from the duplicate-creation window.

**Action:** Fetched live via REST (token never printed); deleted stale duplicates; set Redis to the canonical id.

Live proof (REST):
```
dashboard embed count: 1
  id=1519135545501028549  created=2026-06-24T00:22:18  edited=2026-06-24T00:26:25
redis life_kernel:dashboard_message_id = 1519135545501028549
```
**Canonical dashboard message ID: `1519135545501028549`** in channel `1510914604291588237`. All evidence/final reports updated to this single canonical id. The old `...030`/`...036` messages were deleted.

---

## Blocker 4 — `dashboard_publish_failed TypeError` (06:14 WIB) ✅ RESOLVED (root-caused + fixed + regression test)

**Problem:** `dashboard_publish_failed error_type=TypeError` recurring every cycle (06:15, 06:16, 06:17, ... 07:12, 07:13, 07:15). NOT transient.

**Root cause:** `_NOT_FOUND_HINTS = (10008, "Unknown Message", "10008")` contained the **int** `10008`. In `DashboardWriter._is_not_found`, `any(hint in text for hint in _NOT_FOUND_HINTS)` evaluated `10008 in <str>` → `TypeError: 'in <string>' requires string as left operand, not int`. This crashed the recovery branch every time `edit_message` failed (the stored message had become "unknown/gone"), so the dashboard could never recover/recreate — publish failed every cycle. The real error message (captured after adding `error_message=str(exc)[:400]` to the warning):
```
dashboard_publish_failed error_message="'in <string>' requires string as left operand, not int" error_type=TypeError
```

**Fix (`src/life_kernel/dashboard_writer.py`):** All hints are strings:
```python
_NOT_FOUND_HINTS = ("10008", "Unknown Message")
```

**Recovery proof (after fix):**
```
[info] dashboard_message_gone_recreating      # _is_not_found now works (int-safe)
[info] dashboard_created message_id=1519135545501028549   # recreated
[debug] dashboard_edited message_id=1519135545501028549   # editing resumes
```
Over a 3-min window after fix: `dashboard_edited=5`, `dashboard_publish_failed=0`, `dashboard_edit_failed=0`. A successful `dashboard_edited` happened repeatedly AFTER the failure — the recurring TypeError is eliminated.

**Regression tests (`tests/life_kernel/test_dashboard.py`):**
- `test_is_not_found_with_int_code_hint_is_string_safe` — all hints are `str`; `_is_not_found` does not raise.
- `test_update_dashboard_recovers_when_message_gone` — edit fails with "gone" → writer recreates + persists new id (no crash).

31 dashboard tests pass.

---

## Blocker 5 — Soak gate ✅ ENFORCED (PASS HOLD) → SUPERSEDED by operator waiver

**Status at time of correction:** `VISIBLE AUTONOMY ONLINE — SOAK IN PROGRESS — P20 PASS HOLD`.

The audit explicitly forbids upgrading to PRODUCTION PASS until a full 24h clean soak completes. Core was restarted during this correction work (2026-06-24 07:27 WIB), so the soak clock restarted. The 24h gate is **not** met. No claim of PRODUCTION PASS is made.

> **Superseded 2026-06-25:** The PASS HOLD above was the correct status at
> the time of the 2026-06-24 brutal audit. On 2026-06-25, after the
> continuation + SAF-CONS-01 cleanup deploy (`03f84b5`, soak reset to
> 08:26:43 WIB), Faiz **explicitly waived the remaining 24h soak wait**.
> The 24h gate remains **not completed** (waived, not satisfied). Binding
> status is now **P20 EARLY PRODUCTION ACCEPTANCE — OPERATOR WAIVED 24H
> SOAK — PASS WITH ACCEPTED RISK** — not an unconditional PRODUCTION PASS
> and not a "24h soak completed" claim. See `operator-soak-waiver.md`.

Soak-start state (post-correction):
```
core: active, NRestarts=0, Result=success
brain: think_complete stable, fallback=0
dashboard: edited in place (no publish failures)
HARD STOP: CLEAR
```

---

## Summary

| Blocker | Status | Proof |
|---|---|---|
| 1. discord service masked | ✅ masked | `is-enabled: masked`, symlink→/dev/null |
| 2. memory 2G/4G | ✅ tuned | `MemoryHigh=2G MemoryMax=4G`, no service disturbed |
| 3. canonical dashboard ID | ✅ `1519135545501028549` | REST fetch, single message, Redis set |
| 4. TypeError root cause + fix | ✅ fixed + regression test | int→str hints; 5 edits/0 fail after fix |
| 5. PASS HOLD | ✅ enforced | 24h soak not complete; status unchanged |

## 2026-06-24 23:11 WIB — 9Router Quota Blocker (external, no code change)

**Finding:** Soak monitor detected `hermes_brain_fallback_used=16` / `think_complete=0` over 5 min. Root cause: 9Router account free-tier quota exhausted — every `/v1/chat/completions` returns HTTP 200 with body `{"error":"[429]: FreeUsageLimitError ... Rate limit exceeded"}`. AIAgent gets a response lacking usage fields → HermesBrain `_fallback_response()` fires every cycle.

**Classification:** EXTERNAL blocker (operator account quota). NOT a code defect. The code fails soft correctly: kernel alive (NRestarts=0), dashboard edits in place (8/5min), HARD STOP clean, no GraphRecursionError, no OOM (723MB/2G).

**Resolution:** No restart performed (cannot clear a quota). No code change made. Operator action required: top up/switch the 9Router key (`GUINEVERE_9ROUTER_API_KEY` in `/home/guinevere/code/guinevere/.env.core`) to a paid tier, or repoint `model="guinevere"` at a non-quota backend. Once `hermes_brain_think_complete > 0` resumes, the existing 24h soak clock (target 2026-06-25 07:27 WIB) continues uninterrupted.

**Impact on P20 PRODUCTION PASS:** HOLD remains. Two conditions outstanding: (1) operator resolves 9Router quota so the brain actually thinks; (2) a full 24h clean soak with `think_complete > 0` and zero blockers. The continuation code itself (locally committed, audited PASS/PASS_WITH_NOTES across 2 waves, 420 tests green) is ready to deploy once the operator unblocks quota.
