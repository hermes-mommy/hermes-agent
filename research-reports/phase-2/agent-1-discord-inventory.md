# Phase 2: Discord Bot Command Inventory

**Context**: Migration of Guinevere Discord bot from custom Hermes implementation to Hermes Agent CLI.
**Goal**: Map every command in `src/discord/` — handler function, what it does, what it calls, and migration complexity.
**Date**: 2026-06-04
**Scope**: All `cmd_*.py`, `commands.py`, and `conversational_handler.py` in `src/discord/`.

---

## 1. Command Registry Overview (`commands.py`)

The canonical command registry defines **33 slash commands** grouped into **7 categories**.
All commands are strictly **Faiz-only** (enforced via `is_faiz_interaction`, which checks `guild.owner_id == user.id`).
All slash command responses are **ephemeral**.

| Category | Commands | Count |
|---|---|---|
| `core` | `status`, `mood`, `help`, `safeword`, `new`, `history` | 6 |
| `loop` | `loop-start`, `loop-stop`, `loop-pause`, `loop-resume`, `loops`, `evidence`, `loop-priority` | 7 |
| `memory` | `memory-search`, `memory-add`, `memory-forget`, `memory-export` | 4 |
| `surveillance` | `surveillance-status`, `surveillance-pause`, `surveillance-resume` | 3 |
| `finance` | `cost`, `budget`, `cost-alert` | 3 |
| `system` | `approve`, `deny`, `approve-all`, `focus`, `casual`, `consent`, `punishment`, `reward` | 8 |
| `admin` | `restart-service`, `backup-now`, `health-check`, `clear-cache` | 4 |

---

## 2. Detailed Command Inventory

### 2.1 Core Commands

| Command | Handler Signature | Backend Calls | Session? | Memory? | Response Format | Migration Complexity |
|---|---|---|---|---|---|---|
| `/status` | `status_callback(interaction)` | None (uses degraded placeholders for P3/P4/P5/P7) | No | No | Embed | **Low** (Static data, ready for Hermes integration) |
| `/mood` | `mood_callback(interaction)` | None (degraded placeholders) | No | No | Embed | **Low** |
| `/help` | `help_callback(interaction)` | `command_categories()` (local registry) | No | No | Embed | **Low** |
| `/safeword` | `safeword_callback(interaction)` | `HardStopHandler` (local state) | No | No | Embed | **Low** |
| `/new` | `new_session_callback(interaction)` | `HermesSessionAdapter.clear_session` (Redis DB4) | **Yes** | No | Embed | **Medium** (Direct Hermes adapter call) |
| `/history` | `history_callback(interaction)` | `HermesSessionAdapter.get_history` (Redis DB4) | **Yes** | No | Embed | **Medium** (Direct Hermes adapter call) |

### 2.2 Loop Commands

| Command | Handler Signature | Backend Calls | Session? | Memory? | Response Format | Migration Complexity |
|---|---|---|---|---|---|---|
| `/loop-start` | `loop_start_callback(interaction)` | Internal API (`POST /api/v1/loops`) via `httpx` | No | No | Embed | **Medium** (Requires API key, HTTP client) |
| `/loop-stop` | `loop_stop_callback(interaction)` | Internal API (`POST /api/v1/loops/{id}/cancel`) | No | No | Embed | **Medium** |
| `/loop-pause` | `loop_pause_callback(interaction)` | `LoopManager` (local state) | No | No | Embed | **Low** |
| `/loop-resume` | `loop_resume_callback(interaction)` | `LoopManager` (local state) | No | No | Embed | **Low** |
| `/loops` | `loops_callback(interaction)` | `LoopManager.list_loops()` | No | No | Embed | **Low** |
| `/evidence` | `evidence_callback(interaction)` | `LoopManager` (local state, artifact metadata) | No | No | Embed | **Low** |
| `/loop-priority` | `loop_priority_callback(interaction)` | `LoopManager` (local state) | No | No | Embed | **Low** |

### 2.3 Memory Commands

| Command | Handler Signature | Backend Calls | Session? | Memory? | Response Format | Migration Complexity |
|---|---|---|---|---|---|---|
| `/memory-search` | `memory_search_callback(interaction)` | DB direct (`recall_memories` via SQLAlchemy), `EmbeddingService` | No | **Yes** | Embed | **High** (Requires DB session factory, vector search) |
| `/memory-add` | `memory_add_callback(interaction)` | DB direct (`store_episode` via SQLAlchemy), `EmbeddingService` | No | **Yes** | Embed | **High** (Requires DB session factory, vector embedding) |
| `/memory-forget` | `memory_forget_callback(interaction)` | DB direct (`UPDATE memories SET dnr = true`) | No | **Yes** | Embed | **Medium** (Requires DB session factory) |
| `/memory-export` | `memory_export_callback(interaction)` | DB direct (`SELECT` metadata), sends file via DM | No | **Yes** | Embed + **File (DM)** | **High** (Requires DB session, DM channel creation) |

### 2.4 Surveillance Commands

| Command | Handler Signature | Backend Calls | Session? | Memory? | Response Format | Migration Complexity |
|---|---|---|---|---|---|---|
| `/surveillance-status` | `surveillance_status_callback(interaction)` | `check_consent`, `redis_buffer` (peek) | No | No | Embed | **Medium** (Consent gate + Redis buffer interaction) |
| `/surveillance-pause` | `surveillance_pause_callback(interaction)` | Local state (`_paused`), `invalidate_cache` (consent gate) | No | No | Embed | **Low** |
| `/surveillance-resume` | `surveillance_resume_callback(interaction)` | Local state (`_paused`) | No | No | Embed | **Low** |

### 2.5 Finance Commands

| Command | Handler Signature | Backend Calls | Session? | Memory? | Response Format | Migration Complexity |
|---|---|---|---|---|---|---|
| `/cost` | `cost_callback(interaction)` | Redis DB5 (`CostTracker` scan) | No | No | Embed | **Medium** (Redis scan logic, trend calculation) |
| `/budget` | `budget_callback(interaction)` | Redis DB5 (`CostTracker`, `budget:monthly_cap`) | No | No | Embed | **Medium** |
| `/cost-alert` | `cost_alert_callback(interaction)` | Redis DB5 (`cost:alert_threshold`) | No | No | Embed | **Low** |

### 2.6 System Commands

| Command | Handler Signature | Backend Calls | Session? | Memory? | Response Format | Migration Complexity |
|---|---|---|---|---|---|---|
| `/approve` | `approve_callback(interaction)` | Local state (`src.mcp.auth._pending_approvals`) | No | No | Embed | **Low** |
| `/deny` | `deny_callback(interaction)` | Local state (`src.mcp.auth._pending_approvals`) | No | No | Embed | **Low** |
| `/approve-all` | `approve_all_callback(interaction)` | Local state (`src.mcp.auth._pending_approvals`) | No | No | Embed | **Low** |
| `/focus` | `focus_callback(interaction)` | Redis DB0 (`persona:focus_mode`) | No | No | Embed | **Low** |
| `/casual` | `casual_callback(interaction)` | Redis DB0 (`persona:interaction_mode`) | No | No | Embed | **Low** |
| `/consent` | `consent_callback(interaction)` | Redis DB0 (`consent:grants` JSON set) | No | No | Embed | **Low** |
| `/punishment` | `punishment_callback(interaction)` | Redis DB0 (`persona:punishment_log` JSON list) | No | No | Embed | **Low** |
| `/reward` | `reward_callback(interaction)` | Redis DB0 (`persona:reward_log` JSON list) | No | No | Embed | **Low** |

### 2.7 Admin Commands

| Command | Handler Signature | Backend Calls | Session? | Memory? | Response Format | Migration Complexity |
|---|---|---|---|---|---|---|
| `/restart-service` | `restart_service_callback(interaction)` | OS Subprocess (`sudo systemctl restart guinevere-*`) | No | No | Embed | **High** (Requires OS-level execution, strict whitelist) |
| `/backup-now` | `backup_now_callback(interaction)` | OS Subprocess (`scripts/guinevere-backup.sh daily`) | No | No | Embed | **High** (Requires OS-level execution) |
| `/health-check` | `health_check_callback(interaction)` | External API (`httpx` GET `http://localhost:8000/health/detailed`) | No | No | Embed | **Medium** (HTTP client, parsing health JSON) |
| `/clear-cache` | `clear_cache_callback(interaction)` | Redis DB0 (`r.flushdb()`, requires `confirm=True`) | No | No | Embed | **Low** |

---

## 3. Conversational Handler Pipeline (`conversational_handler.py`)

Handles natural text-based conversation in `#guinevere-chat` (Channel ID: `1510914600777023659`).

- **Handler Signature**: `handle_conversation(bot: Any, message: Any) -> bool`
- **Trigger**: Non-bot, non-slash message in `#guinevere-chat`, **Faiz-only** (`guild.owner_id == author.id`).
- **Pipeline Flow**:
  1. **Rate Limiting**: Redis DB0 (`rate:chat:{user_id}:{minute_bucket}`, max 10/min).
  2. **Distress Detection**: `DistressDetector` + `SafeModeController`.
  3. **Mood Evaluation**: Defaults to `Content`.
  4. **Memory Recall**: `HermesMemoryBridge.recall_for_context` (DB + `EmbeddingService`, token budget 800).
  5. **Prompt Assembly**: `get_system_prompt_with_context` + anti-hallucination guard.
  6. **LLM Call**: `HermesSessionAdapter.send_message` (Hermes Agent CLI).
  7. **Response Formatting**: `_split_response` (max 3 chunks of 2000 chars).
  8. **Cost Tracking**: `CostTracker.record_cost` (Redis DB5).
  9. **Memory Write**: `HermesMemoryBridge.store_conversation` (async background task).
  10. **Logging**: `structlog` (metadata only, no raw content).
- **Session State**: **Yes** (`HermesSessionAdapter`).
- **Memory**: **Yes** (`HermesMemoryBridge`).
- **Response Format**: **Plain Text** (chunked).
- **Migration Complexity**: **Very High** (Tightly coupled to Hermes adapter, memory bridge, cost tracker, and distress detection. Requires careful orchestration of async tasks).

---

## 4. Migration Complexity Summary

| Complexity | Count | Commands |
|---|---|---|
| **Low** | 18 | `status`, `mood`, `help`, `safeword`, `loop-pause`, `loop-resume`, `loops`, `evidence`, `loop-priority`, `surveillance-pause`, `surveillance-resume`, `cost-alert`, `approve`, `deny`, `approve-all`, `focus`, `casual`, `consent`, `punishment`, `reward`, `clear-cache` |
| **Medium** | 9 | `new`, `history`, `loop-start`, `loop-stop`, `memory-forget`, `surveillance-status`, `cost`, `budget`, `health-check` |
| **High** | 5 | `memory-search`, `memory-add`, `memory-export`, `restart-service`, `backup-now` |
| **Very High** | 1 | `conversational_handler` (on_message pipeline) |

---

## 5. Key Architectural Observations for Phase 2

1. **Universal Faiz-Only Enforcement**: Every single command and the conversational handler strictly enforces `guild.owner_id == user.id`. This must be preserved in the Hermes Agent CLI migration.
2. **Ephemeral Responses**: All slash commands use `ephemeral=True`. The Hermes Agent CLI must support ephemeral followups.
3. **Session State Coupling**: `/new` and `/history` directly call `HermesSessionAdapter`. The migration must ensure the new Hermes Agent CLI exposes equivalent session management APIs or the Discord layer adapts to the new session storage.
4. **Memory Bridge Dependency**: Memory commands (`search`, `add`, `forget`, `export`) and the conversational handler rely on `HermesMemoryBridge` and `EmbeddingService`. These require the SQLAlchemy session factory to be passed from the bot instance.
5. **OS-Level Admin Commands**: `/restart-service` and `/backup-now` use `asyncio.create_subprocess_exec`. These are high-risk and require strict environment validation (e.g., `sudo` permissions, script existence) in the new deployment.
6. **No Type Suppression**: All handlers use strict typing, `@runtime_checkable` protocols for Discord objects, and explicit error handling. Migration must maintain this discipline.

---
*Generated by Guinevere Research Agent. Read-only analysis. No files modified.*
