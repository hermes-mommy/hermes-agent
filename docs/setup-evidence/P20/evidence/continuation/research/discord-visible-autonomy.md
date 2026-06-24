# P20 Discord-Visible Autonomy — Research Report

**Researcher:** Discord-visible autonomy specialist agent  
**Scope:** Verify that the life_kernel's Discord dashboard and log channel present a living, autonomous Guinevere rather than raw technical loop state, and identify gaps that would prevent an outside observer from concluding "Guinevere visibly generates meaningful autonomous agenda without Faiz trigger."  
**Date:** 2026-06-24  
**Output file:** `docs/setup-evidence/P20/evidence/continuation/research/discord-visible-autonomy.md`

---

## 1. Executive Summary

The dashboard and lifecycle log are **live** and **edit-not-spam** is correctly implemented, but the visible surface currently reads as a **technical loop counter**, not a living agenda. The dashboard embed shows phase, cycle/act/session counts, and placeholders for `last_autonomous_decision`, `next_planned_action`, and `memory_status`, but those fields are mostly populated by stub logic (`idle_node` picks one of three hard-coded strings via `random.choice`, `act_node` does not produce real actions, and `memory_status` is never set by any node). The log channel is **calm by design** — one lifecycle line per 5 minutes, deduped — but the content is limited to `phase/acts/decision/next/hard_stop`, so it reads as a heartbeat ticker rather than a narrative of autonomous intent.

**Bottom line:** A viewer looking at `#guinevere-status` sees a bot is running, but cannot yet tell whether Guinevere autonomously decided to do anything meaningful. Wiring the dashboard/log to the **LLM-enriched idle, act, and observe nodes**, plus **real P16/P18 context**, is required to cross the line from "loop alive" to "living agenda visible."

---

## 2. Current State Evidence (file:line)

### 2.1 Dashboard renderer
`src/life_kernel/dashboard.py` builds a Discord embed with these fields (rendered every 60s by the heartbeat):
- `Status`, `Mode` (current phase), `Current Focus`, `Last Decision`, `Last Action Result`, `Next Planned Action`, `Current Agenda`, `HARD STOP`, `Memory`, `Uptime`, `Heartbeat`, `Cycles`.
  - `src/life_kernel/dashboard.py:285-386`

Key code:

```python
"name": "Current Focus",
"value": self._truncate_field(self._sanitize(str(state.get("current_focus", "—")))),
```
`src/life_kernel/dashboard.py:321-323`

```python
"name": "Next Planned Action",
"value": self._truncate_field(self._sanitize(str(state.get("next_planned_action", "—")))),
```
`src/life_kernel/dashboard.py:336-338`

```python
"name": "Memory",
"value": self._truncate_field(self._sanitize(str(state.get("memory_status", "—")))),
```
`src/life_kernel/dashboard.py:351-353`

The `_format_agenda` method limits to 5 goals and falls back to "No active agenda".
`src/life_kernel/dashboard.py:188-199`

Sanitization is present: API keys, bearer tokens, and `key=value` credential patterns are redacted.
`src/life_kernel/dashboard.py:27-35`

### 2.2 Dashboard writer — edit-not-spam, Redis persistence, recovery
`src/life_kernel/dashboard_writer.py` stores the dashboard message id in Redis key `life_kernel:dashboard_message_id`, recovers by scanning recent bot messages, and always PATCHes in place.
`src/life_kernel/dashboard_writer.py:40-118`

```python
_NOT_FOUND_HINTS = ("10008", "Unknown Message")
```
`src/life_kernel/dashboard_writer.py:46`

```python
async def update_dashboard(self, state: LifeMindState) -> None:
    if not getattr(self._client, "enabled", True):
        return
    checksum = self._renderer._state_checksum(state)
    if checksum == self._last_published_checksum:
        return
    ...
    await self._client.edit_message(self._channel_id, message_id, embed=embed)
```
`src/life_kernel/dashboard_writer.py:126-161`

`publish_hard_stop` bypasses the checksum skip so a live halt is immediately visible.
`src/life_kernel/dashboard_writer.py:184-218`

### 2.3 Log channel — calm, append-only, fail-soft
`src/life_kernel/log_channel.py` defines:
- `LogChannel` abstract interface.
- `DiscordLogChannel` POSTs new messages (never edits), fails soft.
- `StructlogLogChannel` fallback for tests/no-token environments.

`src/life_kernel/log_channel.py:54-150`

### 2.4 Discord REST client — token safety, retries, timeout
`src/life_kernel/discord_rest_client.py` reads token from `DISCORD_BOT_TOKEN` env, never logs it, retries on 5xx/429, and caps every request at 10s.
`src/life_kernel/discord_rest_client.py:80-177`

### 2.5 Heartbeat — 60s decision + dashboard/log publishing, throttled lifecycle log
`_heartbeat_60s` invokes the graph, then publishes the dashboard and calls `_log_lifecycle_milestone`.
`src/life_kernel/heartbeat.py:421-488`

```python
_LIFECYCLE_LOG_THROTTLE_SECONDS = 300  # at most one lifecycle log line per 5 min
```
`src/life_kernel/heartbeat.py:31`

```python
line = (
    f"[cycle {cycles}] phase={phase} acts={acts} "
    f"decision={decision} next={next_action} hard_stop={hard_stop}"
)
now = time.time()
if line == self._last_log_line or (now - last_t) < _LIFECYCLE_LOG_THROTTLE_SECONDS:
    return
```
`src/life_kernel/heartbeat.py:510-522`

### 2.6 Graph nodes — LLM enrichment exists but memory/KG adapters are never injected
`graph.py`:
- `observe_node` checks `kg_adapter` and `memory_adapter` from state; if both are present it builds `DecisionContextBuilder`, otherwise it stores a placeholder context.
  - `src/life_kernel/graph.py:158-170`
- The placeholder is hard-coded: `world_model_available = False`.
  - `src/life_kernel/graph.py:129`
- `idle_node` uses `random.choice` over three hard-coded strings when no brain proposal is available.
  - `src/life_kernel/graph.py:463-468`
- When `hermes_brain` is supplied, `_make_brain_idle` generates a real agenda proposal via `hermes_brain.think(...)` and stores it in `next_planned_action`.
  - `src/life_kernel/graph.py:604-635`
- When `hermes_brain` is supplied, `_make_brain_act` proposes a concrete next action and stores it in `next_planned_action`.
  - `src/life_kernel/graph.py:564-600`

`state.py` defines the optional adapter keys but no node currently populates them:
```python
kg_adapter: NotRequired[Any]
memory_adapter: NotRequired[Any]
```
`src/life_kernel/state.py:207-211`

`p16_adapter.py` and `p18_adapter.py` are stubs returning mock data.
`src/life_kernel/p16_adapter.py:39-99`
`src/life_kernel/p18_adapter.py:40-102`

---

## 3. VPS Live Check

Command executed (no secrets printed):
```bash
ssh -o ConnectTimeout=10 guinevere-vps 'redis-cli -a "$(grep REDIS_PASSWORD /etc/guinevere-core.env ... )" -p 6380 -n 6 GET life_kernel:dashboard_message_id ...; journalctl ...'
```

Result:
- Redis returned `NOAUTH Authentication required.`, indicating the password extraction did not match the env file format or the key is not yet set.
- `journalctl` output was suppressed by the same auth notice.

Interpretation: the SSH path is reachable, but the live verification command failed at Redis auth. The code-level evidence above shows the dashboard writer is designed to persist `life_kernel:dashboard_message_id` in Redis DB 6; if that key were present and readable, it would confirm the dashboard message has been created. A follow-up should run the command with the correct auth or via the core service's own env.

---

## 4. Gap Table

| id | severity | title | current_state | required_state | files | vision-ref |
|----|----------|-------|---------------|---------------|-------|------------|
| gap-lk-dash-01 | high | `memory_status` never set | Dashboard shows "—" for Memory; no node writes it | A node (observe or reflect) writes a concise memory/recall summary to `memory_status` | `src/life_kernel/graph.py`, `src/life_kernel/state.py`, `src/life_kernel/dashboard.py` | V-003, LK-010 |
| gap-lk-dash-02 | high | Agenda items are static/random | `idle_node` picks from 3 hard-coded strings via `random.choice` | LLM-enriched idle produces unique, contextual self-directed agenda items every cycle | `src/life_kernel/graph.py:463-468`, `src/life_kernel/graph.py:604-635` | V-003 |
| gap-lk-dash-03 | high | No real P16/P18 context in state | `kg_adapter` and `memory_adapter` are optional, never injected; `DecisionContextBuilder` gets a placeholder | Real adapters are injected into graph config/configurable and `observe_node` builds enriched context | `src/life_kernel/graph.py:158-170`, `src/life_kernel/p16_adapter.py`, `src/life_kernel/p18_adapter.py`, `src/life_kernel/state.py:207-211` | LK-010 |
| gap-lk-dash-04 | medium | `current_focus` is never populated | Dashboard field always shows "—" | Decide or act node sets `current_focus` to the active goal/commitment/concern in focus | `src/life_kernel/graph.py:175-253`, `src/life_kernel/dashboard.py:321-323` | V-003 |
| gap-lk-dash-05 | medium | Log line lacks autonomous intent narrative | Line is `[cycle X] phase=... acts=... decision=... next=... hard_stop=...` | Log line includes a one-sentence autonomous intent, e.g. "decided to explore X because Y" | `src/life_kernel/heartbeat.py:494-528` | V-003 |
| gap-lk-dash-06 | low | Dashboard does not show recalled memory count | Memory field is a plain string; no count/summary of KG/memory signals | Dashboard Memory field shows e.g. "recalled 3 memories, 2 KG concepts" | `src/life_kernel/dashboard.py:351-353`, `src/life_kernel/graph.py:158-170` | LK-010 |
| gap-lk-dash-07 | low | No visible evidence when Hermes brain fallback is used | Fallback path returns empty string silently; dashboard may show stale "next" | Graph logs a `brain_fallback` marker and dashboard shows "LLM fallback" badge | `src/life_kernel/graph.py:68-94`, `src/life_kernel/dashboard.py:285-386` | LK-004 |

---

## 5. Risks

| risk | mitigation |
|------|------------|
| **Spam/regression to POST spam** if edit logic breaks (e.g. message id lost and not recovered). | Redis persistence + recovery scan + `_last_published_checksum` skip already mitigate; add a metric/alert if `dashboard_created` occurs more than once per hour. |
| **Secret leakage in dynamic LLM-generated agenda text.** | `_sanitize()` is applied to every dynamic string before Discord; continue enforcing no raw state dumps. |
| **Edit-not-spam regression if `DiscordRestClient.enabled` is misread.** | `DashboardWriter.update_dashboard` and `publish_hard_stop` both guard on `getattr(self._client, "enabled", True)`; keep unit tests for disabled-client path. |
| **LLM timeout/proposal latency blocks heartbeat.** | `_safe_think` uses `asyncio.wait_for` with 30s timeout and swallows exceptions; dashboard publishing itself is wrapped in try/except and never re-raised. |
| **Memory/KG wiring could expose internal query details.** | Only summarized counts and top concept/memory names should reach Discord; redact any UUIDs or raw embeddings. |

---

## 6. Hard-Rejection Flags

None identified in the current code. The implementation satisfies:
- HARD STOP is non-LLM and absolute (`decide_node` checks `hard_stop_requested` first; `_heartbeat_1s` checks Redis live flag and calls `stop()` before any brain call).
- No raw `LLMRouter.chat` path; brain is only `HermesBrain.think`.
- "Heartbeat" terminology preserved (no user-facing "pulse").
- No secrets are printed to Discord (sanitization patterns exist; token is never logged).
- Display-only autonomy (no DMs/side-effects).

---

## 7. Concrete Recommendation for Implementation Phase

To make `#guinevere-status` unambiguous evidence of autonomous agenda, the next implementation pass should:

1. **Inject real P16/P18 adapters into graph state.**
   - Update the graph builder/config to pass `kg_adapter` and `memory_adapter` into the configurable state.
   - Replace `p16_adapter.py`/`p18_adapter.py` stubs with thin wrappers over `src.knowledge_graph.query.*` and `src.memory.read_pipeline.recall_memories`.
   - In `observe_node`, build the decision context and write a concise summary to a new state field (e.g. `memory_status` or `recall_summary`).

2. **Populate `current_focus`, `last_autonomous_decision`, `next_planned_action` from the brain.**
   - `decide_node` already sets `last_autonomous_decision` when brain is used.
   - Ensure `act_node` and `idle_node` always produce meaningful text when `hermes_brain` is available; the wrappers already do this.
   - Make the static fallback less mechanical: include the selected goal/task description rather than a generic string.

3. **Enrich the lifecycle log line.**
   - Extend `_log_lifecycle_milestone` to include the brain-generated `next_planned_action` or `last_autonomous_decision` as a one-sentence narrative, while keeping the 5-minute throttle and dedup.
   - Example target: `[cycle 42] phase=act decision=act_on_engineering next="draft ADR for wearable health pipeline" focus=engineering hard_stop=false`.

4. **Add dashboard fields for recalled context.**
   - Add a "Recalled Context" field showing counts and the top 1-2 concept/memory names, truncated and sanitized.
   - Keep it display-only; do not expose raw embeddings or full query strings.

5. **Add a brain-fallback visibility badge.**
   - When `_safe_think` returns empty, set a state flag `brain_fallback=True`; render a small badge in the embed footer or a dedicated field.
   - This makes outages visible rather than silently stale.

6. **Verify live on VPS.**
   - Re-run the Redis/journalctl command with correct auth and confirm `life_kernel:dashboard_message_id` exists and dashboard edits are occurring.
   - Confirm `#guinevere-logs` receives one lifecycle line per 5 minutes and the line contains an autonomous intent.

---

## 8. Conclusion

The Discord-visible autonomy infrastructure is solid: edit-not-spam, token safety, throttled calm log, and non-LLM HARD STOP are all in place. The missing piece is **content**: the dashboard and log still expose the skeleton of the loop rather than the mind of the agent. Once P16/P18 context is wired and the brain-generated `next_planned_action`/`current_focus`/`memory_status` fields are consistently populated, the Discord channels will become unambiguous evidence that Guinevere is generating her own agenda without operator trigger.
