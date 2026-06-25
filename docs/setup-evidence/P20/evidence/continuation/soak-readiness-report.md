# P20 Continuation — Soak Readiness Report

| Field | Value |
|---|---|
| Date | 2026-06-25 |
| Status | **P20 EARLY PRODUCTION ACCEPTANCE — OPERATOR WAIVED 24H SOAK — PASS WITH ACCEPTED RISK** |
| Soak clock | Reset to **2026-06-25 08:26:43 WIB** (post-privacy-fix restart) |
| Full 24h target | 2026-06-26 08:26 WIB — **operator waived the wait; NOT completed** |
| Cleanup commit | `03f84b5` |
| Waiver | `discord-visible-autonomy/operator-soak-waiver.md` |

> **NOT a 24h-soak-completed claim and NOT an unconditional PRODUCTION PASS.**
> The kernel was SOAK READY (all blocker conditions resolved, verified CLEAN
> snapshot at 08:50:46 WIB), but Faiz explicitly waived the remaining 24h
> wait on 2026-06-25 rather than let the window mature. Acceptance is early,
> with accepted residual risk (see waiver §4). The earlier 05:54 WIB soak
> clock is voided — the VPS ran pre-privacy-fix code (raw P18 memory to the
> LLM) during that window.

## 1. Soak-Readiness Verdict

✅ **SOAK READY.** All soak-blocking conditions are resolved as of the 08:26:43 WIB restart.

| Condition | Required | Actual (post-fix) | Status |
|---|---|---|---|
| Privacy: raw memory content in logs | 0 | 0 | ✅ |
| GraphRecursionError | 0 | 0 | ✅ |
| Traceback | 0 | 0 | ✅ |
| UndefinedTableError | 0 | 0 | ✅ |
| dashboard_publish_failed | 0 | 0 | ✅ |
| journal_entry_failed | 0 | 0 | ✅ |
| hermes_brain_fallback_used | 0 | 0 | ✅ |
| guinevere-core active | yes | active | ✅ |
| Other services undisturbed | yes | hermes-gateway + guinevere-mcp active | ✅ |
| Health endpoint | 200 | 200 OK healthy | ✅ |
| Brain thinking | >0 | think_complete=4 (2 min) | ✅ |
| Recall active | >0 | observe_world_model=4, n_recalled_memories=3 | ✅ |
| Journal persisting | >0 | journal_entry_written=4 | ✅ |

## 2. Why the Earlier Soak Clock Was Voided

The 05:54 WIB deploy restart (commit `c29a461`) did **not** include the SAF-CONS-01 privacy fix. Between 05:54 WIB and 08:26 WIB, the VPS ran code where:

- `_make_brain_decide` and `_make_brain_idle` fed raw P18 memory content (`m.get("content", "")[:60]`) into LLM brain prompts.
- `idle_node` fallback path would log raw memory content via `task_description` → `current_focus` → Discord dashboard + lifecycle log.

This is a **privacy regression on a safety-affecting domain** (memory/consent). Soak time accumulated against pre-fix code is invalid. The 08:26:43 WIB restart is the **honest soak-zero**.

## 3. Pre-Existing (Accepted) Soak Noise

These log patterns appear but are **not soak-blocking** — they are pre-existing infrastructure and historical data, documented in `cleanup-verification-audit.md §4`:

| Pattern | Why accepted |
|---|---|
| Hermes fallback text in checkpoint/state | Historical checkpoint text from pre-deploy; `fallback_used=0` post-fix |
| Failed to load plugin | hermes-gateway plugin loader infra, not Guinevere code |
| loop_manager DB auth warnings | Pre-existing fail-soft pattern F-04; loops continue on DB outage |

These may be investigated post-PRODUCTION-PASS but do not invalidate the soak.

## 4. Pre-Existing (Accepted) Test Warnings

Local `pytest tests/life_kernel/ -q`: **420 passed, 7 skipped, 2242 warnings**.

| Warning class | Count | Status |
|---|---|---|
| pytest-asyncio `get_event_loop_policy` deprecation | ~2280 | Pre-existing (Python 3.14+ plugin compat) |
| pytest-asyncio config deprecation | 1 | Pre-existing |
| P20 test authoring bugs | 0 (were 6) | **Fixed in `03f84b5`** |

The 2242 remaining warnings are a pytest-asyncio plugin compatibility issue, not P20 code. Accepted as pre-existing.

## 5. Monitoring Plan for the 24h Soak

During the soak window (08:26 WIB → 2026-06-26 08:26 WIB), monitor:

1. **Privacy invariant**: `journalctl -u guinevere-core | grep -cE "follow up on recalled context|Recent memories:|memory_summaries"` — must stay **0**.
2. **Blocker patterns**: GraphRecursionError, Traceback, UndefinedTableError, dashboard_publish_failed, journal_entry_failed — must stay **0**.
3. **Brain health**: `hermes_brain_fallback_used` — must stay **0** (or near-zero with documented cause).
4. **Service health**: guinevere-core active, NRestarts stable, `/health` 200.
5. **Dashboard**: edit-in-place working (Discord channel 1510914604291588237).
6. **Log channel**: append-only narrative (Discord channel 1510914623367413850).

## 6. PRODUCTION PASS Criteria

All of the following must hold at 2026-06-26 08:26 WIB:

- [ ] 24h elapsed since 08:26:43 WIB restart with no service restart (except operator-initiated).
- [ ] Privacy invariant: 0 raw memory content in logs across the full window.
- [ ] All blocker patterns: 0 across the full window.
- [ ] Brain thinking continuously (no sustained fallback).
- [ ] Journal persisting continuously.
- [ ] Dashboard + log channel publishing.
- [ ] Independent re-audit of safety-consent surface against `03f84b5` returns PASS.

Only then: **P20 PRODUCTION PASS**.

## 7. Footer

| Field | Value |
|---|---|
| Report date | 2026-06-25 08:27 WIB (waiver 2026-06-25) |
| Soak-zero | 2026-06-25 08:26:43 WIB |
| Cleanup commit | `03f84b5` |
| Status | P20 EARLY PRODUCTION ACCEPTANCE — OPERATOR WAIVED 24H SOAK — PASS WITH ACCEPTED RISK |
| Next gate | (waived) 24h clean soak was the gate; operator waived the wait — see operator-soak-waiver.md |
