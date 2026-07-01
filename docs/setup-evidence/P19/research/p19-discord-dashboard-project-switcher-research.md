# P19 Research: Discord/Dashboard Project Switcher UX

**Status:** ✅ COMPLETE
**Date:** 2026-06-25
**Author:** Guinevere (parent-authored from scout reports + direct reads)
**Scope:** Discord UX + dashboard design for explicit, auditable project switching.

---

## 1. Executive Summary

The Discord UX today is **single-project**: one `#guinevere-chat`, one dashboard message (`life_kernel:dashboard_message_id`), one log channel. P19 adds an **explicit, auditable project switcher** (`/project` command mirroring the existing `/focus`/`/casual` pattern), per-project dashboards, and per-project log channels. Every switch is logged to the audit trail.

**Key invariant (hard rejection):** Every project switch must be logged. Dashboard for project A must not show project B's goals/agenda.

---

## 2. Current Discord UX

From `docs/60-persona/63-DiscordUXSpec_v1.0.md` and scout:
- Channel layout: `#guinevere-chat`, `#guinevere-status`, `#guinevere-planning`, `#guinevere-voice` (P21 planned).
- Slash commands: `/status`, `/mood`, `/help`, `/safeword`, `/new`, `/history`, `/focus`, `/casual`, `/consent`, `/loop-*`, `/memory-*`, `/surveillance-*`, `/cost`, `/budget`, etc.
- Embed palette: purple `#6B21A8` default, green `#16A34A` safe-mode (`DiscordUXSpec §4.1`).
- Presence states: "Watching over Darling 💜", "Loop active 🔄", etc.

---

## 3. Current Dashboard

- `src/life_kernel/dashboard.py:19-285` — `DashboardRenderer` renders `LifeMindState` to markdown/embeds.
- `src/life_kernel/dashboard_writer.py:59-126` — `DashboardWriter` edits single Discord message in place (edit-not-spam).
- Redis key: `life_kernel:dashboard_message_id` (GLOBAL).
- Channel from env `LIFE_KERNEL_DASHBOARD_CHANNEL_ID` (`src/core/main.py:375-387`).

---

## 4. Current Log Channel

- `src/life_kernel/log_channel.py:54-150` — `DiscordLogChannel` / `StructlogLogChannel`.
- Channel from env `LIFE_KERNEL_LOG_CHANNEL_ID`.
- Fail-soft: falls back to structlog.

---

## 5. Project Registry UX

How Faiz sees all projects:
- `/projects list` — list all active/archived projects.
- `/projects create <slug> <name>` — create a new project (Faiz-only, audited).
- `/projects archive <slug>` — archive a project (stops autonomous work, keeps data).
- `/projects info <slug>` — show project details (default channel, dashboard channel, consent summary).

---

## 6. Project Switcher UX

### 6.1 Option A: /project <name> (explicit switch, sticky per channel)
- `/project work` — sets active project to `work` for the current channel.
- Stored in Redis DB0: `project:active:{channel_id}` = `<project_uuid>`.
- Sticky until switched again or `/project default`.

### 6.2 Option B: per-channel default project
- `/project set-default <name>` — sets the default project for the current channel.
- Each channel has one default project.

### 6.3 Option C: per-thread default project
- Each Discord thread can have its own project.

### 6.4 Recommendation: A + B combined
- Explicit `/project <name>` switch (sticky per channel).
- Per-channel default via `/project set-default <name>` (survives restart).
- `/project` with no args shows current active project.
- Falls back to `default` if none set.

---

## 7. Default Project When Faiz Silent

If Faiz doesn't specify a project:
1. Current channel has a default project → use that.
2. No default → use `default` (matches P22 default namespace).
3. P20 idle autonomy (when Faiz silent): picks based on top-priority goal across all active projects, with explicit project label in the output ("Working on project: work — ...").

---

## 8. Dashboard Per-Project

### 8.1 Option A: one dashboard message per project
- Each active project has its own dashboard message.
- Redis key: `life_kernel:dashboard_message_id:{project_id}`.
- Dashboard channel: same `#guinevere-status` (multiple messages) or per-project status channel.

### 8.2 Option B: single dashboard with project tabs
- One message, embed fields per project.
- Pros: compact.
- Cons: Discord embed field limit (25 fields); hard to read with many projects.

### 8.3 Option C: /dashboard <project> creates per-project dashboard
- On-demand per-project dashboard.

### 8.4 Recommendation: A
- One dashboard message per active project.
- Redis key `life_kernel:dashboard_message_id:{project_id}`.
- Bounded to top-N active projects (e.g., 3) to avoid message spam; archived/idle projects' dashboards paused.

---

## 9. Log Channel Per-Project

### 9.1 Option A: one log channel per project
- `#guinevere-log-work`, `#guinevere-log-personal`.
- Pros: clean separation.
- Cons: channel proliferation.

### 9.2 Option B: single log channel with project tag
- One `#guinevere-log`, each message prefixed `[work]` / `[personal]`.

### 9.3 Recommendation: A for top-3 projects, B as fallback
- Up to 3 active projects get dedicated log channels (configured in `projects.project_registry.log_channel_id`).
- Additional projects log to the shared `#guinevere-log` with a `[project:slug]` prefix.

---

## 10. Presence State Per-Project

Current: "Watching over Darling 💜" / "Loop active 🔄".
Per-project: "Working on: work 🛠️" / "Personal tasks 🏠" / "Loop active [work] 🔄".

Precedence (mirrors P21 A14): SEV0 > HARD STOP > voice-armed > project-loop-active > default.

---

## 11. Embed Palette Consistency

DiscordUXSpec §4.1 purple `#6B21A8` default — consistent across all projects. Optional project-specific accent color (stored in `projects.project_registry.accent_color`) for project dashboards/switch confirmations.

---

## 12. Audit Trail for Project Switch

Every `/project` switch → audit row:
- `actor` (Faiz user_id)
- `from_project_id`, `to_project_id`
- `timestamp`
- `channel_id`
- `correlation_id`

Written to `audit.audit_trail` (event_type `project_switched`). Mirrored to `#audit-log`.

---

## 13. P21 Voice Project Selection

- P21 voice channel can be project-bound or single channel with `/voice project <name>`.
- Recommendation: single `#guinevere-voice` + `/voice project <name>` switcher (mirrors `/project`).
- Voice episodes carry `project_id`.

---

## 14. P22 Integration Project Selection

- P22 sensors configured per project: `projects.project_registry.p22_integrations` JSONB (e.g., `{"calendar": "work@gmail.com", "github": "work-org/work-repo"}`).
- Each project has its own integration accounts.

---

## 15. Hard Rejection: Non-Auditable Switch

- Every `/project` switch writes an audit row. No silent switch.
- `/project` command requires Faiz auth (`is_faiz_interaction()`).

---

## 16. Hard Rejection: Implicit Cross-Project Leak via UX

- Dashboard for project A renders only project A's `LifeMindState` (goals, commitments, concerns, journal from project A's graph state).
- `/status` shows current project's status.
- `/memory-search` scoped to current project unless `/memory-search --all-projects` (consent-gated).

---

## 17. Mockup: /projects list

```
┌─────────────────────────────────────┐
│ 👑 GUINEVERE — PROJECTS              │
├─────────────────────────────────────┤
│ 🟢 default    Default Project        │
│    (active, dashboard: #status)      │
│ 🟢 work       Work Project           │
│    (active, dashboard: #status,      │
│     log: #log-work)                  │
│ 🟡 personal  Personal                │
│    (paused)                          │
│ ⚪ alpha      Project Alpha           │
│    (archived 2026-06-20)             │
├─────────────────────────────────────┤
│ Use /project <name> to switch.       │
└─────────────────────────────────────┘
```

---

## 18. Mockup: /project work

```
✅ Switched to project: **work**
📊 Dashboard: #guinevere-status (project:work)
📝 Log: #guinevere-log-work
[audit: project_switched default→work by Faiz]
```

---

## 19. Mockup: Per-project dashboard embed

Fields:
- `PROJECT` — work
- `PHASE` — act
- `HEARTBEAT` — 1s/60s active
- `MEMORY` — 1,204 episodes (42 recalled last cycle)
- `KG` — 318 entities
- `CURRENT FOCUS` — deploy feature X
- `NEXT ACTION` — run smoke tests
- `GOALS` — 3 active
- `COMMITMENTS` — 2 active
- `CONCERNS` — 1 (cost ceiling)
- `JOURNAL` — last entry: "Refactored auth module..."

---

## 20. Hard Rejection Checks

1. **Project switch not explicit/auditable:** ✅ MITIGATED — `/project` command + audit row.
2. **Dashboard cross-project leak:** ✅ MITIGATED — per-project `LifeMindState` + `dashboard_message_id:{project_id}`.
3. **Default project undefined when silent:** ✅ MITIGATED — channel default → `default` fallback.

---

## 21. Conclusion

P19 adds an explicit `/project` switcher (mirroring `/focus`/`/casual`), per-project dashboards (`life_kernel:dashboard_message_id:{project_id}`), per-project log channels (top-3 dedicated, rest tagged), project-aware presence states, and a project registry UX (`/projects list/create/archive/info`). Every switch is audited. Dashboards render only the active project's state. Default project resolves via channel default → `default` fallback.
