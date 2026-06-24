---
title: "P20 Discord-Visible Autonomy Audit"
status: "Research Evidence"
date: "2026-06-24"
owner: "Faiz"
executor: "Guinevere"
scope: "src/life_kernel/, src/discord/"
related: "docs/setup-evidence/P20/README.md"
---

# P20 Discord-Visible Autonomy Audit

## Objective

Determine whether the Discord-visible Living Autonomy Kernel dashboard presents Guinevere's *living state* (focus, agenda, concerns, commitments, journal) or merely raw technical health-check metrics, and verify the related log channel and terminology.

## Files Examined

- `src/life_kernel/dashboard.py` — `DashboardRenderer` (full markdown + Discord embed)
- `src/life_kernel/dashboard_writer.py` — `DashboardWriter` (edit-not-spam publisher)
- `src/life_kernel/discord_rest_client.py` — REST client for Discord publishing
- `src/life_kernel/log_channel.py` — `DiscordLogChannel` / `StructlogLogChannel`
- `src/life_kernel/heartbeat.py` — heartbeat service that drives dashboard/log updates
- `src/life_kernel/state.py` — `LifeMindState` schema
- `src/life_kernel/graph.py` — graph nodes that populate state
- `src/core/main.py` — wiring of dashboard writer and log channel
- `src/discord/_entrypoint.py` — main Discord bot (separate from P20 REST publisher)
- `tests/life_kernel/test_dashboard.py` — dashboard renderer tests

## Key Finding: Discord Actually Sees the Embed, Not the Markdown Dashboard

`DashboardWriter.update_dashboard()` calls `DashboardRenderer.render_embed(state)` and PATCHes a **Discord embed** to the configured `LIFE_KERNEL_DASHBOARD_CHANNEL_ID`.

The full markdown produced by `render()` (with `## HEARTBEAT`, `## GOALS`, `## COMMITMENTS`, `## CONCERNS`, etc.) is only used by the test helper `render_to_channel()` and is **not** the Discord-visible output.

## What the Discord Embed Actually Displays

Fields rendered in `DashboardRenderer.render_embed()` (`src/life_kernel/dashboard.py` lines 309–376):

| Field | Living State? | Notes |
|---|---|---|
| Status | mixed | HARD STOP / ALIVE / INACTIVE emoji indicator |
| Mode | technical | current_phase (observe/decide/act/reflect/idle) |
| **Current Focus** | **yes** | `current_focus` |
| **Last Decision** | **yes** | `last_autonomous_decision` |
| **Last Action Result** | **yes** | `last_action_result` |
| **Next Planned Action** | **yes** | `next_planned_action` |
| **Current Agenda** | **partial** | only `goals` (first 5); commitments are **not** included |
| HARD STOP | safety | hard_stop_requested flag |
| Memory | mixed | `memory_status` |
| Uptime | technical | `uptime_start` |
| Heartbeat | technical | `last_heartbeat` |
| Cycles | technical | act_count / cycle_count / session_count |

### Living-state Coverage

| Required Element | Shown in Discord Embed? | Where |
|---|---|---|
| Current focus/attention | **Yes** | "Current Focus" field |
| Active agenda items | **Partial** | "Current Agenda" shows only goals; commitments omitted |
| Concerns | **No** | Present only in the unused markdown `_concerns_section` |
| Commitments | **No** | Present only in the unused markdown `_commitments_section` |
| Journal entries | **No** | `journal_entries` exists in `LifeMindState` but is **never rendered** anywhere in the dashboard or embed |
| Health/loop metrics | **Yes** | Heartbeat, cycles, mode, status fields |

## Conclusion: It Is a Mix, Not Pure Health-CHECK

The Discord-visible dashboard **does show living-state signals** (focus, last/next action, decisions, goals), but it is **incomplete**:

1. **Commitments and concerns are missing from the embed** — they are only in the unused markdown renderer.
2. **Journal entries are completely absent** from both the embed and the markdown dashboard, despite being populated by `reflect_node` via `journal_writer` (`src/life_kernel/graph.py` lines 505–577).
3. The dashboard still carries technical counters (cycles, heartbeat, act_count), so it is **not yet a pure living-state view**.

## Separate Log Channel Preserves History

`src/life_kernel/log_channel.py` implements `DiscordLogChannel`, which is **append-only by design**:

> "The log channel is *append-only by design*: we never edit or delete lifecycle events, so the channel reads as a chronological narrative of the kernel's autonomous behavior."

It is wired in `src/core/main.py` using `LIFE_KERNEL_LOG_CHANNEL_ID` and writes throttled lifecycle milestones in `heartbeat.py::_log_lifecycle_milestone()`.

## Terminology Check

Search for `pulse` in `src/` returned **no user-facing matches**. The code consistently uses `heartbeat` terminology (`last_heartbeat`, `HeartbeatService`, `HeartbeatInterval`, etc.), satisfying the requirement to avoid "pulse" in user-facing strings.

## Recommendations for the Downstream Fix

1. **Add Concerns field to the embed** — reuse `_concerns_section()` logic, capped to avoid overflow.
2. **Add Commitments field to the embed** — or merge into an expanded "Agenda" field that includes both goals and commitments.
3. **Add a Journal / Recent Reflections field** — render the latest 1–3 `journal_entries` so the dashboard shows Guinevere's reflective narrative.
4. **Consider surfacing the markdown dashboard** optionally, or replacing the embed with it in a thread/post, to expose the richer living-state view currently hidden.
5. **Keep health metrics** but de-emphasize them (e.g., move to footer or a collapsed "Metrics" field) so the living state dominates the dashboard.

## Evidence Artifacts

- Inline code references point to `src/life_kernel/dashboard.py`, `dashboard_writer.py`, `log_channel.py`, `heartbeat.py`, and `state.py`.
- No secrets, credentials, or personal data were exposed during this audit.

---

*Audit completed 2026-06-24. Verdict: Discord-visible dashboard shows partial living state; concerns, commitments, and journal entries need to be added to make it fully alive.*
