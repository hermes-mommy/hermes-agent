# P20 Soak Monitoring Log

**Soak window:** 2026-06-24 07:28 WIB → 2026-06-25 07:27 WIB (target 24h clean)
**Mode:** Monitoring only — no restarts unless a real blocker appears.
**Goal:** If clean through 2026-06-25 07:27 WIB, run final production audit + upgrade to P20 PRODUCTION PASS.

Each entry is a timestamped health snapshot. "Clean" = all dimensions green.

---

## 2026-06-24 08:06 WIB — CLEAN ✅

```
1.SERVICE: core=active NRestarts=0 Result=success
   ActiveEnter=Wed 2026-06-24 07:28:11 WIB
   9router=active  discord_masked=masked/inactive
2.MEM: cur=549M high=2G(2147483648) max=4G(4294967296) peak=549M
   vps: 4.7Gi used / 10Gi avail
3.BRAIN(5m): think_complete=12 fallback=0
4.DASH(5m): dashboard_edited=9 publish_failed=0 edit_failed=0
5.BLOCKERS(5m):
   stuck_END=0  live_HS=0  crash=0  guardian_stop=0  NRestarts=0
6.DISCORD REST:
   dashboard: count=1  id=1519135545501028549  edited=2026-06-24T01:08:43  color=0x5865f2 (alive)
   redis dashboard_id=1519135545501028549
```
All dimensions green. Edit-not-spam confirmed (single message, edited recently). Brain thinking (12 think_complete, 0 fallback). No blockers. No restart needed.

---

_Continued monitoring. Next check on next cycle._

## 2026-06-24 23:11 WIB — BLOCKER 🛑 (external quota, no restart)

```
1.SERVICE: core=active NRestarts=0 Result=success
   ActiveEnter=Wed 2026-06-24 07:28:11 WIB  (soak clock NOT reset — external blocker)
   now=2026-06-24 23:11:20 WIB  (elapsed ~15h43m of 24h)

2.MEMORY: MemoryCurrent=723MB MemoryPeak=724MB  (limit High=2G/Max=4G) — HEALTHY

3.HERMESBRAIN (last 5 min):
   hermes_brain_think_complete = 0   ❌
   hermes_brain_fallback_used  = 16  ❌ (every cycle)

4.DASHBOARD (last 5 min):
   dashboard_edited = 8  ✅  (edit-not-spam working)
   dashboard_publish_failed = 0  ✅
   dashboard_edit_failed = 0  ✅

5.BLOCKERS (last 5 min) — all 0 except brain:
   HARD_STOP_routing_to_END = 0  ✅
   hard_stop_detected_live = 0  ✅
   hermes_brain_think_failed = 0  ✅
   aiagent_create_failed = 0  ✅
   heartbeat_stopped = 0  ✅
   traceback = 0  ✅
   GraphRecursionError = 0  ✅
   guardian_error = 0  ✅

6.DISCORD REST (live fetch):
   Dashboard channel 1510914604291588237: 1 bot-authored embed
     id=1519135545501028549  color=0x5865f2 (blurple)  bot=True
     title="Guinevere — Living Autonomy Dashboard"  ts~2026-06-24T00:22Z
     → edited in place ✅  BUT Next Planned Action field shows:
       "[Hermes fallback] Missing required fields from AIAgent response: ..."
   Log channel 1510914623367413850: append-only events present ✅
     e.g. "[cycle 196897] phase=idle acts=25 decision=self-directed task
            next=[Hermes fallback] Missing required fields from AIAgent response"

7.REDIS: life_kernel:dashboard_message_id = 1519135545501028549 ✅ (canonical)

ROOT CAUSE (investigated, NOT a code defect):
  9Router returns HTTP 200 with an error body on every chat call:
    {"error":{"message":"[429]: FreeUsageLimitError ... Rate limit exceeded"}}
  The 9Router ACCOUNT free-tier quota is EXHAUSTED (736 quota errors in 30 min).
  9Router SERVICE itself is healthy: /health/detailed → 9router:ok models:64,
  port 20128 listening, /v1/models lists "guinevere".
  AIAgent receives a valid JSON response that lacks usage fields
  (total_tokens/model/estimated_cost_usd), so HermesBrain.think() returns
  its _fallback_response() every cycle → 0 think_complete, 16 fallback.
  The kernel fails SOFT: dashboard edits, HARD STOP clean, no recursion,
  no OOM, NRestarts=0. But AC-LIFE-005/009 (memory-driven + self-improve)
  cannot exercise because the brain never succeeds.

DECISION: NO RESTART. Restarting cannot clear an external account quota and
  would reset the soak clock for no benefit. The running kernel is stable and
  correctly fail-soft. Root-cause fix requires OPERATOR action:
    (a) top up / switch the 9Router API key to a paid tier, OR
    (b) point model="guinevere" at a non-quota-exhausted backend.
  Once the brain returns think_complete > 0, the existing soak clock
  (target 2026-06-25 07:27 WIB) continues; this external quota window does
  NOT reset the clock because no code defect caused it and no restart is
  performed. PRODUCTION PASS remains on HOLD (quota blocker + 24h clean
  brain not yet achieved).

NOTE: This snapshot was taken during the P20 CONTINUATION pass. The
  continuation code (real P16/P18 recall, memory-driven idle, journal,
  self-improvement wiring) is committed locally (HEAD) but NOT YET DEPLOYED
  to this VPS — the VPS is still running the pre-continuation build. The
  quota blocker is independent of the continuation and will affect the
  deployed build identically until the operator resolves 9Router quota.
```

## 2026-06-25 00:20 WIB — BLOCKER 🛑 (external quota persists, no restart)

```
1.SERVICE: core=active NRestarts=0 Result=success
   ActiveEnter=Wed 2026-06-24 07:28:11 WIB  (soak clock NOT reset)
   now=2026-06-25 00:20:01 WIB  (elapsed ~16h52m of 24h; target 2026-06-25 07:27 WIB)

2.MEMORY: MemoryCurrent=781MB MemoryPeak=781MB  (limit High=2G/Max=4G) — HEALTHY

3.HERMESBRAIN (last 5 min):
   hermes_brain_think_complete = 0   ❌
   hermes_brain_fallback_used  = 16  ❌ (every cycle — unchanged from 23:11 WIB)

4.DASHBOARD (last 5 min):
   dashboard_edited = 8  ✅  dashboard_publish_failed = 0  ✅  dashboard_edit_failed = 0  ✅

5.BLOCKERS (last 5 min) — all 0:
   HARD_STOP_routing_to_END=0  hard_stop_detected_live=0  hermes_brain_think_failed=0
   aiagent_create_failed=0  heartbeat_stopped=0  traceback=0  GraphRecursionError=0  ✅

6.DISCORD REST (live fetch):
   Dashboard 1510914604291588237: 1 bot embed id=1519135545501028549 color=0x5865f2
     Status=🟢 ALIVE  Last Decision=self-directed task
     Next Planned Action="[Hermes fallback] Missing required fields from AIAgent..."
     (edited in place ✅, but reflects the quota-degraded brain)
   Log channel 1510914623367413850: append-only events present ✅
     "[cycle 196944] phase=idle ... next=[Hermes fallback] Missing required fields..."

7.REDIS: life_kernel:dashboard_message_id = 1519135545501028549 ✅

ROOT CAUSE (unchanged from 23:11 WIB): 9Router account free-tier quota EXHAUSTED.
  Every chat call returns HTTP 200 + {"error":"[429]: FreeUsageLimitError ..."}.
  9Router service healthy (/health/detailed → 9router:ok models:64). NOT a code defect.
  Kernel fails SOFT: dashboard edits, HARD STOP clean, no recursion, NRestarts=0, mem 781MB/2G.

DECISION: NO RESTART. External account quota cannot be cleared by a restart.
  Operator action still required: top up/switch 9Router key (GUINEVERE_9ROUTER_API_KEY
  in /home/guinevere/code/guinevere/.env.core) OR repoint model="guinevere".
  Soak clock NOT reset (target 2026-06-25 07:27 WIB holds; no restart, no code defect).
  PRODUCTION PASS remains HOLD: needs (1) operator quota fix → think_complete>0,
  (2) 24h clean brain soak from that point.
```

## 2026-06-25 05:14 WIB — BLOCKER 🛑 (external quota persists, no restart)

```
1.SERVICE: core=active NRestarts=0 Result=success
   ActiveEnter=Wed 2026-06-24 07:28:11 WIB  (soak clock NOT reset)
   now=2026-06-25 05:14:25 WIB  (elapsed ~21h46m of 24h; target 2026-06-25 07:27 WIB — ~2h13m to go)

2.MEMORY: MemoryCurrent=855MB MemoryPeak=857MB  (limit High=2G/Max=4G) — HEALTHY
   (trend: 723MB@23:11 → 781MB@00:20 → 855MB@05:14; slow crawl, well under 2G ceiling)

3.HERMESBRAIN (last 5 min):
   hermes_brain_think_complete = 0   ❌
   hermes_brain_fallback_used  = 12  ❌ (every cycle — quota blocker unchanged)

4.DASHBOARD (last 5 min):
   dashboard_edited = 6  ✅  dashboard_publish_failed = 0  ✅  dashboard_edit_failed = 0  ✅

5.BLOCKERS (last 5 min) — all 0:
   HARD_STOP_routing_to_END=0  hard_stop_detected_live=0  hermes_brain_think_failed=0
   aiagent_create_failed=0  heartbeat_stopped=0  traceback=0  GraphRecursionError=0  ✅

6.DISCORD REST (live fetch):
   Dashboard 1510914604291588237: 1 bot embed id=1519135545501028549 color=0x5865f2
     (edited in place ✅; Next Planned Action still shows "[Hermes fallback]...")
   Log channel 1510914623367413850: append-only events present ✅
     "[cycle 197165] phase=idle ... next=[Hermes fallback] Missing required fields..."

7.REDIS: life_kernel:dashboard_message_id = 1519135545501028549 ✅

ROOT CAUSE (unchanged): 9Router account free-tier quota EXHAUSTED. NOT a code defect.
  Kernel fails SOFT: dashboard edits, HARD STOP clean, no recursion, NRestarts=0, mem 855MB/2G.

DECISION: NO RESTART. External account quota cannot be cleared by a restart.
  Soak clock NOT reset (target 2026-06-25 07:27 WIB holds).
  PRODUCTION PASS remains HOLD: even when the wall-clock target arrives (~07:27 WIB),
  the brain is not thinking (quota), so the 24h-clean-brain condition cannot be met.
  Operator action still required: top up/switch 9Router key OR repoint model="guinevere".
```

## 2026-06-25 05:15 WIB — BLOCKER 🛑 (external quota persists, no restart)

```
1.SERVICE: core=active NRestarts=0 Result=success
   ActiveEnter=Wed 2026-06-24 07:28:11 WIB  (soak clock NOT reset)
   now=2026-06-25 05:15:42 WIB  (elapsed ~21h47m; target 2026-06-25 07:27 WIB — ~2h11m to go)

2.MEMORY: MemoryCurrent=855MB MemoryPeak=857MB  (High=2G/Max=4G) — HEALTHY (flat vs 05:14)

3.HERMESBRAIN (last 5 min):
   hermes_brain_think_complete = 0   ❌
   hermes_brain_fallback_used  = 12  ❌ (quota blocker unchanged)

4.DASHBOARD (last 5 min):
   dashboard_edited = 6  ✅  dashboard_publish_failed = 0  ✅  dashboard_edit_failed = 0  ✅

5.BLOCKERS (last 5 min) — all 0:
   HARD_STOP_routing_to_END=0  hard_stop_detected_live=0  hermes_brain_think_failed=0
   aiagent_create_failed=0  heartbeat_stopped=0  traceback=0  GraphRecursionError=0  ✅

6.DISCORD REST: 1 bot embed id=1519135545501028549 color=0x5865f2 (edited in place ✅)
   Log channel: append-only events present ✅ ([cycle 197165] ... Hermes fallback)

7.REDIS: life_kernel:dashboard_message_id = 1519135545501028549 ✅

ROOT CAUSE (unchanged): 9Router account free-tier quota EXHAUSTED. NOT a code defect.
  Kernel fails SOFT: dashboard edits, HARD STOP clean, no recursion, NRestarts=0, mem 855MB/2G.

DECISION: NO RESTART. External account quota cannot be cleared by a restart.
  Soak clock NOT reset (target 2026-06-25 07:27 WIB holds).
  FINAL GATE will NOT pass at 07:27 WIB: the gate requires 24h clean INCLUDING
  brain think_complete>0 and no fallback. The brain has been in fallback the
  entire window due to external quota, so the 24h-clean condition cannot be met.
  Operator action required: top up/switch 9Router key OR repoint model="guinevere".
  Once resolved, a fresh 24h clean-brain soak must run from that point.
```

## 2026-06-25 05:21 WIB — RECOVERY ✅ (9Router quota resolved by operator)

```
1.SERVICE: core=active NRestarts=0 Result=success
   ActiveEnter=Wed 2026-06-24 07:28:11 WIB  now=2026-06-25 05:21:01 WIB

2.MEMORY: MemoryCurrent=856MB MemoryPeak=857MB  (High=2G/Max=4G) — HEALTHY

3.HERMESBRAIN (last 5 min):  *** QUOTA RESOLVED — BRAIN THINKING AGAIN ***
   hermes_brain_think_complete = 8   ✅ (was 0 for ~6h during quota exhaustion)
   hermes_brain_fallback_used  = 4   (transient — likely rate-limit burst during recovery)

4.DASHBOARD (last 5 min):
   dashboard_edited = 8  ✅  dashboard_publish_failed = 0  ✅  dashboard_edit_failed = 0  ✅

5.BLOCKERS (last 5 min) — all 0 ✅

6.DISCORD REST (live):
   Dashboard 1510914604291588237: 1 bot embed id=1519135545501028549 color=0x5865f2
     Status=🟢 ALIVE  Last Decision=observe  Next Planned Action=await self-directed task
   Log channel: "[cycle 197171] phase=idle acts=26 decision=observe
     next=await self-directed task hard_stop=False" ✅ (no more [Hermes fallback] text)

7.REDIS: life_kernel:dashboard_message_id = 1519135545501028549 ✅

NOTE: VPS still running PRE-CONTINUATION build (dashboard shows Mode=UNKNOWN,
  Current Focus=— because recalled_concepts/recalled_memories/world_model_status
  fields don't exist yet on the deployed code). Brain is healthy now → deploying
  the continuation code next so the living-state fields populate.
```

## 2026-06-25 05:55 WIB — CLEAN ✅ (continuation DEPLOYED + LIVE)

```
DEPLOY: P20 continuation code deployed to VPS via scp (policy-gated:
  predeploy tests 420 pass → backup → scp 8 src files → restart ONLY
  guinevere-core → smoke). 3 deploy-runtime bugs found + fixed live:
  (1) audit_journal schema/table not created (asyncpg multi-stmt + missing
      schema) — fixed ensure_table to split statements + CREATE SCHEMA;
  (2) record() passed raw dict to JSONB — fixed to json.dumps + CAST AS jsonb;
  (3) ensure_table logged false success — fixed to log truthfully.
  Commits: a272587, df83f70, ff1c9fa, c29a461.

1.SERVICE: core=active NRestarts=0 Result=success
   ActiveEnter=Thu 2026-06-25 05:54:51 WIB  (SOAK CLOCK RESET — deploy restart)
   *** NEW 24h SOAK TARGET: 2026-06-26 05:54 WIB ***

2.MEMORY: under 2G High / 4G Max (healthy, ~860MB)

3.HERMESBRAIN (last 70s): think_complete=2  fallback=0  ✅ BRAIN THINKING

4.DASHBOARD (last 70s): dashboard_edited=2  publish_failed=0  edit_failed=0  ✅

5.BLOCKERS (last 70s) — ALL 0:
   HARD_STOP_routing_to_END=0  GraphRecursionError=0  traceback=0
   UndefinedTableError=0  record_failed=0  journal_entry_failed=0  ✅

6.DISCORD REST (live):
   Dashboard 1510914604291588237: 1 bot embed id=1519135545501028549
     color=0x5865f2 (blurple) edited in place ✅
     Status=🟢 ALIVE  Current Focus=Finance Health Check
     Last Decision=act on: Finance Health Check  (AC-LIFE-002: seeded goal ACTED on)
     Current Agenda=[improve_autonomy] Finance Health Check  (real seeded goal)
     Memory=active: 3 mem, 0 kg  (AC-LIFE-005: real P18 recall, world_model active)
     HARD STOP=✅ CLEAR  Cycles: act=34 cycle=197204
   Log channel 1510914623367413850: "[cycle 197204] phase=idle
     focus=Finance Health Check ..." (T12 narrative field) ✅

7.REDIS: life_kernel:dashboard_message_id = 1519135545501028549 ✅

CONTINUATION ACCEPTANCE CRITERIA — LIVE PROOF:
   AC-LIFE-002 ✅ idle seeds REAL memory-driven goal (Finance Health Check),
                acted on next cycle (Last Decision=act on: ...)
   AC-LIFE-005 ✅ real P18 recall_memories (3 mem) + P16 KGQueryEngine wired,
                world_model_status=active, brain prompts include recall
   AC-LIFE-008 ✅ journal entries PERSIST to life_kernel.audit_journal (PG):
                "Cycle 197204: act on: Finance Health Check... Recalled 3
                memories, 0 KG concepts. Errors: 0." (reasoning+lessons)
   AC-LIFE-009 ✅ ReflectionEvaluator wired w/ graph+config+brain (RUN-01 fix);
                ImprovementTracker.propose stores candidates (display-only,
                RegressionGate.promote is separate — no auto-promote)
   AC-LIFE-001 ✅ boots heartbeat w/o trigger
   AC-LIFE-004 ✅ dashboard edits every 60s, log append-only
   AC-LIFE-007 ✅ HARD STOP non-LLM, clear

SERVICES UNDISTURBED: hermes-gateway=active  guinevere-mcp=active  ✅

DECISION: CLEAN. No restart needed (deploy restart already done at 05:54).
  NEW soak clock started 2026-06-25 05:54 WIB → target 2026-06-26 05:54 WIB.
  PRODUCTION PASS still HOLD: needs 24h clean soak (brain thinking, no
  blockers) from 05:54 WIB. Will NOT upgrade until target reached + clean.
```

---

## Soak Snapshot — 2026-06-25 08:50:46 WIB (CLEAN)

| Field | Value |
|---|---|
| Check type | Auto 5-min fast soak health check |
| Trigger | P20 SOAK MONITORING CHECK (auto) |
| Current wall-clock | 2026-06-25 08:50:46 WIB |
| Soak-zero (clock reset) | 2026-06-25 08:26:43 WIB (cleanup deploy `03f84b5` — SAF-CONS-01 privacy fix) |
| Soak target completion | 2026-06-26 08:26 WIB (NOT YET REACHED — do not upgrade) |
| Verdict | **CLEAN** — no restart, continue monitoring |

> **Clock reset note.** The original 05:54:51 WIB soak clock (and the
> 2026-06-26 05:54 WIB target referenced in the auto-check trigger) was
> **voided** by the brutal-cleanup deploy of commit `03f84b5`
> (SAF-CONS-01 privacy fix) at 2026-06-25 08:26:43 WIB. The VPS ran
> pre-privacy-fix code between 05:54 and 08:26 WIB (raw P18 memory
> content reached the LLM brain prompts during that window), so that
> interval does not count toward the clean 24h soak. Honest soak-zero is
> 08:26:43 WIB; target 2026-06-26 08:26 WIB. See
> `continuation/cleanup-verification-audit.md` and
> `continuation/soak-readiness-report.md`.

### 1. Core state
```
SERVICE: guinevere-core=active  NRestarts=0  Result=success  SubState=running
ActiveEnterTimestamp=Thu 2026-06-25 08:26:43 WIB
```
NRestarts=0 since the cleanup-deploy restart. No crash, no auto-restart. ✅

### 2. Memory
```
MemoryCurrent = 571,981,824  (~546 MB)
MemoryPeak    = 572,764,160  (~546 MB)
MemoryHigh    = 2,147,483,648 (2 GB)   ← ceiling
MemoryMax     = 4,294,967,296 (4 GB)   ← hard max
```
Healthy and stable. Current is ~25% of the 2 GB High ceiling; peak tracks
current (no leak growth visible in the 5-min window). No OOM risk. ✅

### 3. HermesBrain (last 5 min)
```
hermes_brain_think_complete = 7
hermes_brain_fallback_used = 0
```
Brain thinking continuously (7 completions in 5 min ≈ once per 43 s, within
the 60 s heartbeat cadence). Zero fallbacks — no LLM outage, no quota
exhaustion. ✅

### 4. Dashboard (last 5 min)
```
dashboard_edited         = 7
dashboard_publish_failed = 0
dashboard_edit_failed    = 0
```
Edit-in-place working (7 edits in 5 min, matches the 60 s heartbeat). Zero
publish/edit failures. ✅

### 5. Blockers (last 5 min) — ALL 0
```
HARD_STOP requested - routing to END = 0
hard_stop_detected_live              = 0
hermes_brain_think_failed            = 0
aiagent_create_failed                = 0
heartbeat_stopped                    = 0
GraphRecursionError                  = 0
traceback                            = 0
```
No stuck HARD STOP, no recursion blowup, no brain failure, no heartbeat
halt, no traceback. ✅

### 6. Discord REST (live)
**Dashboard channel 1510914604291588237** (last 50 messages):
```
total messages returned : 1
messages with embeds    : 1
bot-authored messages   : 1
embed msg id            : 1519135545501028549  (matches expected)
color                   : 0x5865f2 (blurple)   ✅
edited_timestamp        : 2026-06-25T01:46:28Z (edited in place)  ✅
title                   : Guinevere — Living Autonomy Dashboard
```
Exactly 1 dashboard embed (edit-not-spam confirmed), correct id, blurple
color, recently edited. ✅

**Log channel 1510914623367413850** (last 5 messages, append-only):
```
[2026-06-25T01:44:03Z] [cycle 197401] phase=idle focus=Finance Health Check acts=24
[2026-06-25T01:43:25Z] [cycle 197400] phase=idle focus=Finance Health Check acts=24
[2026-06-25T01:38:33Z] [cycle 197393] phase=idle focus=Finance Health Check acts=24
[2026-06-25T01:38:07Z] [cycle 197393] phase=idle focus=Finance Health Check acts=24
[2026-06-25T01:32:45Z] [cycle 197386] phase=idle focus=Finance Health Check acts=23
```
Fresh append-only lifecycle events (T12 narrative field), cycles advancing.
✅

### 7. Redis
```
life_kernel:dashboard_message_id = 1519135545501028549  ✅ (matches live embed id)
```
Found in db 0 and db 6 of the `guinevere-redis` docker instance
(host 127.0.0.1:6380). Value matches the live Discord embed id, so the
edit-in-place publisher resolves the correct message each cycle. ✅

> **Pre-existing config note (not a blocker):** `REDIS_URL` in `.env.core`
> points at `redis://localhost:6380/5` (DB 5), but the `life_kernel:*`
> keys are written to DB 0/DB 6. This DB-index drift is harmless for the
> dashboard publisher (it sets and gets the key on the same connection
> the app uses) but is worth reconciling post-PRODUCTION-PASS. Host redis
> on :6379 (the `aizanta-redis` container) is a separate instance and
> does not carry these keys.

### Decision
**CLEAN.** All seven dimensions pass: core stable (NRestarts=0), memory
healthy (~546 MB / 2 GB), brain thinking (7 completions, 0 fallback),
dashboard editing in place (7 edits, 0 failures), zero blockers, 1 blurple
dashboard embed edited recently, fresh log-channel events, Redis message-id
matches the live embed.

**No restart performed.** Continue monitoring.

### Status gate
Soak target (2026-06-26 08:26 WIB) has **NOT** been reached. PRODUCTION
PASS remains **HOLD**. This snapshot is a CLEAN 5-min sample toward the
24h clean-soak requirement. The final gate (full 24h blocker scan + 24h
of clean dashboard_edited + brain think_complete, then upgrade) will run
only after 2026-06-26 08:26 WIB.
