# P19 Research: Agent-Loop & Session Isolation Per-Project

**Status:** ✅ COMPLETE
**Date:** 2026-06-25
**Author:** Guinevere (parent-authored from scout reports + direct reads)
**Scope:** How the agent-loop and session model evolve to isolate project contexts.

---

## 1. Executive Summary

Sessions and agent loops are **global today**: Hermes sessions key on `user_id` only, `LoopContext` has no `project_id`, and `SessionGraph` uses `session_id` (session ≠ project). P19 must make sessions and agent loops **project-aware** so project A's session/loop cannot see project B's history, memory, or tools — while the shared persona remains one.

**Recommended design:** Encode `project_id` into session keys (`hermes:session:{user_id}:{project_id}`), `LoopContext` (new `project_id` field), `SessionGraph` thread_id (`session-{project_id}-{session_id}-{uuid}`), and run one `BackgroundCognition` per active project (bounded).

---

## 2. Current Session Model

### 2.1 Life-kernel session (`src/life_kernel/session_graph.py`)
- `SessionGraph(session_id)` — `session_graph.py:32`.
- `create_session_graph(session_id)` — `session_graph.py:46`.
- `thread_id = f"session-{session_id}-{uuid}"` — `session_graph.py:41-43`.
- `SessionState` TypedDict has `session_id` and `sdlc_phase`, **no `project_id`**.
- `SessionProfileManager`, `DiscordThreadManager`, `SessionWorktree` — in-memory dicts, `session_graph.py:333-456`.

### 2.2 Hermes session (`src/hermes/_session_adapter.py`)
- `HermesSessionAdapter`, Redis key `hermes:session:{user_id}` — `_session_adapter.py:57, 125`.
- Session data: `history`, `created_at`, `last_used`, `turn_count`.
- Max 20 turns, TTL 2h — `_session_adapter.py:54`.
- `REDIS_DB=4` — `_session_adapter.py:45-58`.
- **No `project_id` in session key.**

### 2.3 Discord session binding
- `GuinevereBot.on_message()` → `handle_conversation()` for `#guinevere-chat` (`hermes_conversational.py:358`).
- Channel check: hardcoded `GUINEVERE_CHAT_CHANNEL_ID = 1510914600777023659` (`hermes_conversational.py:50`).
- **No channel→project mapping.**

---

## 3. Per-Project Session Design

### 3.1 Option A: project_id in session key (RECOMMENDED)
- Hermes session key: `hermes:session:{user_id}:{project_id}` (DB4).
- SessionGraph thread_id: `session-{project_id}-{session_id}-{uuid}`.
- `SessionState` gets `project_id` field.
- Pros: Simple, backward-compatible (old keys still work if project_id omitted → default).
- Cons: Key namespace grows.

### 3.2 Option B: separate session manager per project
- One `HermesSessionAdapter` instance per project.
- Pros: Clean isolation.
- Cons: Object proliferation; shared Redis connection.

### 3.3 Option C: project context injected into existing session
- Session stores a `project_id` field internally; recall/store reads it.
- Pros: Minimal key change.
- Cons: Session history still mixed if not filtered.

### 3.4 Recommendation
**Option A** for Hermes sessions + Option C semantics (project_id in session metadata used to filter recall). SessionGraph uses Option A thread_id.

---

## 4. Agent-Loop Stack (ADR-011, 7-phase SDLC)

The 7-phase loop (plan/decompose/delegate/verify/audit/fix/report) runs per `LoopContext`. `project_id` must flow:

1. `LoopManager.start_loop(task, goal, priority, project_id)` — new param.
2. `LoopContext` gets `project_id` field (`context.py:57-119`).
3. `SystemPromptBuilder.build_volatile_tier()` includes `[PROJECT: {project_id}]` in prompt.
4. `ConversationLoop` passes `project_id` to memory recall (`recall_for_context(..., project_id)`).
5. `ToolRegistry` / tool selector can restrict available tools by project (e.g., project "work" has GitHub tool, project "personal" does not).
6. `LoopStateStore` persists `project_id` in `projects.loop_instances`.

---

## 5. Concurrent Project Execution

Can Guinevere run project A's agent loop concurrently with project B's? **Yes**, with bounded concurrency:

- Each project's loop runs as an independent `LoopContext` + LangGraph thread.
- Concurrency capped at N (e.g., 3 active projects' loops simultaneously) to bound LLM cost/resource.
- P20 heartbeat dispatches per-project cycles; when Faiz is silent, idle autonomy picks the top-priority project (or rotates).

---

## 6. Hermes Turn Core

`src/discord/hermes_conversational.py` — Discord message → Hermes turn:
1. `on_message` → `handle_conversation`.
2. Determine `project_id`:
   - Explicit: Faiz used `/project <name>` → active project in Redis DB0 `project:active:{channel_id}` or `project:active:global`.
   - Channel-bound: channel→project mapping (e.g., `#project-alpha-dev` → project `alpha`).
   - Default: `default` project if none specified.
3. `_process_and_respond()` passes `project_id` to `HermesMemoryBridge.recall_for_context()` and `store_conversation()`.
4. `HermesSessionAdapter.send_message(user_id, content, system_prompt, project_id)` uses `hermes:session:{user_id}:{project_id}` key.

---

## 7. Discord Channel-to-Project Mapping

### 7.1 Option A: one Discord channel per project
- Dedicated thread/channel per project (e.g., `#guinevere-work`, `#guinevere-personal`).
- Channel→project mapping in `projects.project_registry.default_channel_id` or a Redis map.

### 7.2 Option B: channel-agnostic with /project switcher
- Single `#guinevere-chat` + `/project <name>` to switch active project (sticky per channel or per user).

### 7.3 Option C: hybrid (RECOMMENDED)
- Default `#guinevere-chat` uses `/project` switcher (active project stored per channel in Redis DB0).
- Optional dedicated per-project channels for high-traffic projects (channel→project static mapping).
- `channel-ids.yaml` already has `project-alpha-dev`, `project-alpha-docs`, `project-beta-dev` — these can map to projects `alpha`, `beta`.

---

## 8. Session Worktree Isolation

`src/life_kernel/session_graph.py` `SessionWorktree` — git worktree per session.
- Worktree path must be project-aware: `/opt/guinevere/worktrees/{project_id}/{session_id}/`.
- Prevents cross-project file collision.

---

## 9. Memory Recall in Session

When Hermes recalls memory mid-turn, the recall filters by the session's `project_id`:
- `recall_for_context(query, ..., project_id=ctx.project_id)`.
- Returns only project-scoped + global memories (per memory-namespace research §7).

---

## 10. Background Cognition Isolation

`src/life_kernel/cognition.py` `BackgroundCognition` — 6 asyncio loops (observer, memory, critic, curiosity, self_improvement, guardian).

### 10.1 Option A: one BackgroundCognition per project (RECOMMENDED)
- Spawn one `BackgroundCognition` instance per active project, each with `graph_config = {"thread_id": f"cognition-{project_id}", "project_id": project_id}`.
- Bounded to N active projects.
- Pros: Clean per-project observations; simple.
- Cons: N×6 loops (bounded).

### 10.2 Option B: single BackgroundCognition with project rotation
- One instance iterates over projects each tick.
- Pros: Fewer loops.
- Cons: Complex scheduling; single point of failure.

### 10.3 Recommendation
**Option A**, bounded to e.g. 3 concurrent active projects. Idle projects' cognition pauses (saves cost).

---

## 11. Self-Improvement Isolation

`src/life_kernel/self_improve.py`:
- `ReflectionEvaluator` generates improvement candidates.
- Candidates are **per-project** — a refactor candidate for project A's code must not be promoted into project B's context.
- `_source_loop()` derives loop id from `thread_id` (`self_improve.py:121`); with project-encoded thread_id, candidates are naturally project-scoped.
- `ImprovementTracker` filters candidates by `project_id`.

---

## 12. Graph Checkpointer Isolation

`src/life_kernel/checkpoint.py`:
- Postgres + Redis dual checkpointer.
- Isolation is via `thread_id` (LangGraph convention).
- With `thread_id=heartbeat-{project_id}` and `session-{project_id}-...`, checkpoints are naturally isolated — **no checkpointer code change needed**.

---

## 13. Session Timeout & Eviction

- Per-project TTL (default 2h, configurable per project).
- Eviction: LRU per project when session count exceeds limit.
- Evicted sessions: history summarized (existing `session_summaries` mechanism) with `project_id` preserved.

---

## 14. Cross-Project Session Reference

- By default, project A's session cannot reference project B's memory.
- Explicit cross-project recall API: `recall_across_projects(query, project_ids=[...])` — requires `consent.memory.cross_project` scope (Faiz-approved, audited). Used rarely for "what did I decide across all projects about X".

---

## 15. Hard Rejection: Session Leak

- Test: session in project A must not see project B's history.
- `test_session_isolation`: create session in project A, write history, switch to project B, recall → empty (project B-specific).
- Session key includes `project_id`; recall filters by `project_id`.

---

## 16. P21 Voice Session

- P21 voice turns bind to a session.
- Voice channel can be project-bound (`#guinevere-voice-work`) or single voice channel with `/voice project <name>` switcher.
- Voice episodes carry `project_id` (P21 forward-compat seam already specifies nullable `project_id`).

---

## 17. P22 Integration Session

- P22 sensors (calendar, github, notion) do NOT create sessions; they produce observations tagged with `project_id`.
- P22 actuators (write-notify) run within the project's autonomy scope.

---

## 18. Hard Rejection Checks

1. **Session leak across projects:** ✅ MITIGATED — `project_id` in session key + recall filter.
2. **Agent loop not project-aware:** ✅ MITIGATED — `LoopContext.project_id` + system prompt + tool selection.
3. **Background cognition mixes projects:** ✅ MITIGATED — one BackgroundCognition per project, bounded.
4. **Self-improvement cross-contamination:** ✅ MITIGATED — candidates project-scoped via thread_id.

---

## 19. Conclusion

P19 makes sessions and agent loops project-aware by encoding `project_id` into Hermes session keys, `LoopContext`, `SessionGraph` thread_id, and worktree paths. Background cognition runs one instance per active project (bounded). Self-improvement candidates are project-scoped. Cross-project recall is an explicit, consent-gated, audited API. The shared persona stays one; only the context is partitioned.
