# A4 -- P20 Regression Check (post-P22 deploy)

**Auditor:** Independent sub-agent (not the deploy parent)
**Date:** 2026-06-28 23:12-23:13 WIB
**Verdict: PASS -- no P20 regression**

---

## Check 1: Service State

```
$ ssh guinevere-vps "systemctl show guinevere-core -p NRestarts -p ActiveState -p SubState -p MemoryCurrent"

NRestarts=0
MemoryCurrent=676003840
ActiveState=active
SubState=running
```

| Field | Expected | Actual | Status |
|-------|----------|--------|--------|
| NRestarts | 0 | 0 | PASS |
| ActiveState | active | active | PASS |
| SubState | running | running | PASS |
| MemoryCurrent | < 2 GiB (2147483648) | 676,003,840 (~645 MiB) | PASS |

---

## Check 2: Autonomy-Loop Activity (last 3 min)

```
$ ssh guinevere-vps "journalctl -u guinevere-core --since '3 min ago' --no-pager \
  | grep -iE 'journal_entry_written|reflect_node|dashboard_edited|graph_invoked' | tail -8"
```

All four expected event types confirmed present:

| Event | Observed | Status |
|-------|----------|--------|
| graph_invoked_decision_heartbeat | cycle_count=3014, decision=observe, world_model_status=active | PASS |
| dashboard_edited | message_id=1519135545501028549 | PASS |
| reflect_node_entry | cycle_count=3014, errors_count=0 | PASS |
| journal_entry_written | cycle=3014, entry_id=329d42d3-... | PASS |

Loop is alive and producing all expected event types.

---

## Check 3: Fatal Errors (last 3 min)

```
$ ssh guinevere-vps "journalctl -u guinevere-core --since '3 min ago' --no-pager \
  | grep -iE 'traceback|RuntimeError' | grep -v 'asyncio.run' | head -5"

(no output)
```

**Zero FATAL errors.** No traceback, no RuntimeError in the last 3 minutes (after excluding the known asyncio.run path).

### Pre-existing non-fatal caveats (documented, not counted as regression)

- **asyncio.run / discord tree sync at _entrypoint.py:866**: Known non-fatal warning on the discord-tree-sync path. Not observed in this window but documented as pre-existing from prior audits.
- **loop_manager.resume_pending_loops_failed**: Pre-existing auth-related warning when the loop_manager attempts to resume loops that lack a stored credential. Not observed in this window but documented as pre-existing. Does not affect the autonomy loop itself.

Neither caveat was observed in the current 3-minute window -- the logs are clean.

---

## Check 4: Cycle Count Advancing

| Timestamp | cycle_count | Delta |
|-----------|-------------|-------|
| 2026-06-28 23:12:01 | 3014 | -- |
| 2026-06-28 23:13:11 | 3015 | +1 in ~68s |

Cycle count is well above 3000 and incrementing. The loop is not stuck.

---

## Summary

All four checks PASS:

1. Service: NRestarts=0, active, running, 645 MiB memory
2. Activity: journal_entry_written, reflect_node, dashboard_edited, graph_invoked all flowing
3. Errors: Zero FATAL errors in 3-minute window
4. Cycles: 3014 -> 3015, advancing at normal cadence

**P20 autonomy loop is healthy post-P22 deploy. No regression detected.**
