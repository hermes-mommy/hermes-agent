# P21 Voice Interface — Dependency-Collision Research

> **CURRENT-STATUS NOTE (post-finalization cleanup, 2026-06-25):** The body of this
> file is a **pre-finalization snapshot** captured 2026-06-24 during the P21 research
> wave. At that time the dependency statuses were: P19 NOT STARTED, P20 PRODUCTION
> STABILIZED / PRODUCTION PASS HOLD, P22 NOT STARTED, P21 README NOT STARTED.
> **Current status (2026-06-25):** P21 is **DEFINITION COMPLETE — IMPLEMENTATION HOLD
> UNTIL P20 CONTINUATION PASS** (see `docs/setup-evidence/P21/README.md`); P22 is
> **DEFINITION COMPLETE — IMPLEMENTATION HOLD UNTIL P20 CONTINUATION PASS** (renamed
> "Life Integration Hub", see `docs/setup-evidence/P22/README.md`, dated 2026-06-25);
> P19 remains NOT STARTED; P20 remains in PRODUCTION PASS HOLD. The collision analysis,
> non-interference contract, P19 forward-compat seam, and P21-owns-voice decision below
> remain valid; only the *status labels* of P21/P22 have advanced from NOT STARTED →
> DEFINITION COMPLETE. Where the body says "P22 NOT STARTED" or "P21 README NOT STARTED",
> read it as the historical snapshot; the current label is DEFINITION COMPLETE for both.

| Field | Value |
|---|---|
| Status | PLANNING — research-only, no implementation, deploy, or restart |
| Author | P21 specialist #7 — dependency-collision researcher |
| Date | 2026-06-24 (snapshot); current-status note added 2026-06-25 |
| Phase | P21 Voice Interface (planning), intersects P19 (NOT STARTED), P20 (PRODUCTION STABILIZED, PRODUCTION PASS HOLD), P22 (NOT STARTED — *snapshot; now DEFINITION COMPLETE*) |
| Audience | Planner gate, AGENTS.md §2.6 collision-scan, and any future P21 implementation work |
| Source-of-truth | `docs/setup-evidence/P19/README.md`, `docs/setup-evidence/P20/README.md`, `docs/setup-evidence/P20/plan/p5-p20-living-autonomy-kernel-replan.md`, `docs/setup-evidence/P22/README.md`, `docs/setup-evidence/P21/README.md`, `src/life_kernel/`, `src/core/`, `src/discord/`, `src/hermes/`, `src/memory/`, `src/surveillance/`, `alembic/versions/`, `AGENTS.md` §2.6, `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md`, `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` |

> **Headline.** P21 is a *new input surface* (V-022-class voice transcript) that flows as plain text into the existing `hermes_conversational.handle_conversation()` pipeline. It must reuse HARD STOP (`src/core/services/hard_stop_handler.py`), DistressDetector, and SafeModeController — not duplicate them. It must be strictly additive to P20's life_kernel (new voice sensor adapter, new dashboard fields) and must NEVER touch the 1s HARD-STOP loop semantics, the 6-interval heartbeat schedule, the `life_kernel:hard_stop` Redis key contract, the `hermes_brain.AIAgent` wrapper, or the Hermes conversational core. P19 seams are forward-compatible. P22 does not own voice.

---

## 1. P21 surfaces in scope (per grounding)

| Surface | Existing path | P21 role |
|---|---|---|
| HARD STOP classifier (text) | `src/core/services/hard_stop_handler.py` | Reused as-is. Voice transcript → `HardStopHandler.check(transcript)` before anything else. No re-implementation. |
| DistressDetector + SafeModeController | `src/persona/safe_mode.py` | Reused as-is. `DistressDetector.detect()` runs on the transcript string. |
| Prompt-injection sanitizer (Trust L6) | `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` §3 | New V-022 voice transcript is classified as Trust Level 6 (untrusted), gets source label (`source=voice_transcript`), XML-delimited quarantine before reaching L1-L6 layers. |
| Hermes conversational turn | `src/discord/hermes_conversational.py` | Voice turn = STT → `handle_conversation()` (reused) → TTS(response). Voice is a NEW front-end; back-end pipeline is unchanged. |
| life_kernel heartbeat | `src/life_kernel/heartbeat.py` | Untouched. New voice sensor adapter added *next to* existing adapters in `src/life_kernel/sensor_adapters/`; heartbeat schedule (1s/10s/30s/60s/5m/1h) is invariant. |
| life_kernel HermesBrain | `src/life_kernel/hermes_brain.py` | Untouched. P21 may add a new `voice_brain.py` thin wrapper if needed but MUST NOT modify `hermes_brain.py` while P20 is in HOLD. |
| life_kernel graph (LangGraph) | `src/life_kernel/graph.py`, `src/life_kernel/state.py` | Untouched. New voice observations flow into `state["observations"]` via existing add-observations reducer (capped at 100). |
| Sensor registry | `src/life_kernel/sensors.py` | New `voice_sensor_adapter.py` registered; existing `SensorRegistry` Protocol unchanged. |
| Dashboard | `src/life_kernel/dashboard.py`, `src/life_kernel/dashboard_writer.py` | New dashboard section (`## VOICE`) added additively; existing sections untouched. New state fields added to `LifeMindState` TypedDict with `NotRequired[...]` and default backfill. |
| Memory models | `src/memory/models.py` | Reuse. Voice episode = same `Episodes` row with `source='voice_transcript'`, optional `project_id` (forward-compat for P19). No new table. |
| Surveillance models | `src/surveillance/models.py` | Voice is a *first-class surveillance stream* (per `P21/README.md` L13-15). New table for raw voice stream with same `ClassificationMetaMixin` envelope + V-022 trust level. |
| Hard-stop Redis key | `life_kernel:hard_stop` (heartbeat.py:273) | Untouched. P21 voice HARD STOP path uses the same Redis key for the kernel; the kernel's 1s loop remains the canonical detector. |
| Redis DBs (6) | DB0..DB5 | Voice uses a new keyspace inside an existing DB; no new DB. Candidate: extend DB3 (session) with `voice:session:{user_id}:...` OR add new keys to DB4 (pubsub) for wake-word / VAD events. |
| Discord bot | `src/discord/`, `src/discord/bot.py` (per grounding) | New discord.py voice client (PTT) joins a voice channel; transcript flows to the same `handle_conversation()` path. Slash commands in `#guinevere-chat` continue to work — no overwrite. |
| HermeS memory bridge | `src/hermes/_memory_bridge.py` | Untouched. Voice episodes use the same `recall_for_context` API; the only new parameter is the optional `project_id`. |
| SOPS secrets | `secrets/guinevere-secrets.yaml`, `secrets/discord-secrets.enc.yaml`, `secrets/.gitignore` | New `secrets/voice-secrets.enc.yaml` (STT/TTS provider keys). Does NOT clash with `mcp.production.yaml.sops` because voice providers are not MCP tools. |
| Migration | `alembic/versions/p20_001_life_kernel_schema.py` (parent), `p5_024` (grandparent) | New alembic migration `p21_001_voice_stream.py` chained AFTER `p20_001` (depends_on=p20_001). New schema `voice` (or `surveillance.voice_stream` if reusing). |

---

## 2. P20 dependency map — P21 vs the Living Autonomy Kernel

### 2.1 P20 surfaces P21 touches

| P20 file | What P21 does | Conflict? |
|---|---|---|
| `src/life_kernel/heartbeat.py` | New `voice_sensor_adapter.py` registers with `SensorRegistry`. **Heartbeat code untouched** (file appears in `git status` as untracked? — needs verification; do NOT modify). | None. The 1s loop is invariant per P20 plan BD-001..BD-012. |
| `src/life_kernel/hermes_brain.py` | Untouched. Voice turn uses `AIAgent.run_conversation()` indirectly via `HermesSessionAdapter`. | None. |
| `src/life_kernel/graph.py` | Untouched. New `state["voice_*"]` fields added with `NotRequired` to `LifeMindState` TypedDict (additive, back-compatible). | None IF state additions are additive; collision only if a reducer or default is changed. |
| `src/life_kernel/state.py` | Add `voice_last_transcript: NotRequired[str]`, `voice_session_id: NotRequired[str]`, `voice_stream_active: NotRequired[bool]`. All `NotRequired` with safe-default reads. | None. Pure addition. |
| `src/life_kernel/sensors.py` | New `voice_sensor_adapter.py` in `src/life_kernel/sensor_adapters/`. Implements the existing `_SensorAdapter` Protocol. | None. Existing Protocol and registry unchanged. |
| `src/life_kernel/sensor_adapters/` | Add `voice_sensor_adapter.py`. Existing files (`discord_adapter`, `gmail_adapter`, `finance_adapter`, `wearable_adapter`, `surveillance_adapter`, `vps_adapter`, `repo_adapter`, `browser_adapter`) untouched. | None. New file in same dir. |
| `src/life_kernel/dashboard.py` | New `_voice_section(state)` rendered additively. Section appears after existing HEARTBEAT/STATE/GOALS sections. | None IF additive. |
| `src/life_kernel/dashboard_writer.py` | Untouched (Discord edit-only). | None. |
| `src/life_kernel/cognition.py` | Untouched. | None. |
| `src/life_kernel/journal.py` | Optional: write a journal entry when a voice session starts/ends. | None — Journal is append-only with `add_journal_reducer` cap 1000. |
| `src/life_kernel/log_channel.py` | Untouched. | None. |
| `src/life_kernel/checkpoint.py` | Untouched. | None. |
| `src/life_kernel/redis_client.py` | Optional: read/write `voice:state:{user_id}` keys using existing client. No new DB. | None. |
| `src/life_kernel/discord_rest_client.py` | Untouched. | None. |
| `src/life_kernel/domain_minds/email_mind.py`, `finance_mind.py`, `engineer_mind.py` | Untouched. | None. |
| `src/life_kernel/p18_adapter.py`, `p16_adapter.py` | Untouched. Voice episodes flow through P18 memory bridge; P19 project_id is a forward-compat field. | None. |
| `src/life_kernel/self_improve.py` | Untouched. | None. |
| `src/life_kernel/session_graph.py` | Optional: voice session = per-session graph instance; reuse existing session manager. | None IF additive. |
| `src/core/main.py` | Optional: add voice bot startup wire AFTER P20 lifespan. Must not break existing FastAPI lifespan order (safety → kernel → loop scheduler). | LOW. Sequence: voice wiring goes AFTER kernel wiring to avoid startup-order collision. |

### 2.2 Non-interference contract with P20

1. **1s HARD-STOP loop is invariant.** `heartbeat._heartbeat_1s()` reads `life_kernel:hard_stop` from Redis and dispatches `graph.ainvoke({"hard_stop_requested": True, "is_active": False}, ...)`. P21 NEVER alters this loop, the Redis key, the 1s period, or the fail-closed semantics (Redis unreachable → no state change).
2. **6-interval schedule is invariant.** 1s / 10s / 30s / 60s / 5m / 1h are not re-tuned by P21. The 60s decision heartbeat may optionally surface a "voice active" indicator; the OBSERVE→DECIDE cycle logic is unchanged.
3. **HARD STOP is set on the SAME Redis key.** When voice transcript contains a safe-word, voice path sets `life_kernel:hard_stop` (or invokes the `HardStopHandler._trigger()` flow that already does so). The kernel's 1s loop is the SINGLE detector — voice does not bypass it.
4. **Voice is a new sensor, not a new life-mind phase.** New `voice_sensor_adapter.py` implements the existing `SensorRegistry` Protocol. The 30s awareness heartbeat pulls voice observations the same way it pulls wearable, finance, gmail, etc.
5. **Voice observations flow through the existing `add_observations_reducer`.** No new reducer, no new state-machine edge, no graph topology change. Voice observations are observations; that's it.
6. **Voice turn = STT(transcript) → existing `handle_conversation()` → TTS(response).** No new code path for safety, distress, mood, memory recall, system-prompt assembly, Hermes invocation, or response chunking. P21 does NOT call `HermesBrain.think()` directly; the kernel's brain is reserved for kernel decisions, not conversational turns.
7. **Production-pass HOLD means no edits to P20 files during P20 soak.** Per the LK-017 production-stabilization note (`docs/setup-evidence/P20/README.md` L73-76), the kernel is in 24h clean-soak observation; P21 implementation is BLOCKED on those files until PASS. The exception: P21 may add NEW files (e.g. `src/life_kernel/sensor_adapters/voice_sensor_adapter.py`) and add NEW TypedDict fields (additive, `NotRequired`); both are non-conflicting with running soak.
8. **Voice is NOT a domain mind.** `domain_minds/` is a per-domain self-directed reasoning unit. Voice is an input surface, not a self-directed cognitive area. No `voice_mind.py` is needed; if one is ever added, it must be sequenced AFTER P20 continuation pass.

### 2.3 P20 → P21 dependency arrows

```text
P21 (voice input)
   │
   ├── reads: src/core/services/hard_stop_handler.py (HARD STOP on transcript)
   ├── reads: src/persona/safe_mode.py (DistressDetector, SafeModeController)
   ├── reads: src/hermes/adapter.py (HermesSessionAdapter, shared with Discord)
   ├── reads: src/hermes/_memory_bridge.py (recall_for_context)
   ├── reads: src/memory/models.py (Episodes insert + project_id field)
   ├── reads: src/discord/hermes_conversational.py (handle_conversation — THE orchestrator)
   ├── reads: src/life_kernel/sensors.py (SensorRegistry Protocol only)
   ├── writes (additive only): src/life_kernel/state.py (NotRequired fields)
   ├── writes (new file only): src/life_kernel/sensor_adapters/voice_sensor_adapter.py
   ├── writes (new file only): src/voice/ (P21 package, fresh dir)
   ├── writes (new file only): alembic/versions/p21_001_voice_stream.py
   └── writes (new file only): secrets/voice-secrets.enc.yaml
```

---

## 3. P19 dependency map — forward-compatible seam for project namespaces

### 3.1 P19 status

Per `docs/setup-evidence/P19/README.md` L1-2, L47-49: **P19 is NOT STARTED** — no `src/projects/`, no migration, no schema. Planned scope: per-project memory partitioning, scoped surveillance filters, project-aware agent loop, project switcher.

### 3.2 P21 ↔ P19 collision

P21 is a *new input surface* (voice transcript) and a *new surveillance stream* (raw audio). P19 will eventually partition memory + surveillance by project. If P19 lands BEFORE P21 is in production, P21 voice must respect project boundaries from day one. If P19 lands AFTER P21, P21 voice must accept a P19 retrofit.

### 3.3 Forward-compatible seam

| Surface | P21 design (P19-agnostic) | P19 retrofit |
|---|---|---|
| `Episodes` row | Add `project_id: Mapped[Optional[uuid.UUID]]` (nullable) to `src/memory/models.py` (additive migration, default NULL = default project). | P19 fills non-NULL when a project is active. |
| `voice_stream` table | Add `project_id UUID NULL` column. | P19 filters queries by project_id; sets per-project RLS. |
| `LifeMindState` | Add `current_project_id: NotRequired[str]`. | P19 sets it via project switcher. |
| `voice_sensor_adapter.sense()` | Returns observations with `{"project_id": <str|None>, ...}`. | P19 enriches with project metadata from registry. |
| HermeS recall | `bridge.recall_for_context(query, principal, project_id=None, ...)` — add `project_id` param as kwarg with default `None`. | P19 passes current project_id; recall filters by it. |
| Consent ledger | Voice stream records consent scope as `consented_projects: ARRAY[UUID]`. | P19 reads scope registry; enforces per-project consent. |

### 3.4 Why the seam must be designed now (not later)

Per `P19/README.md` L7-13, project namespace is a **memory partitioning** primitive. A voice episode stored without a `project_id` field cannot be retroactively partitioned without a backfill migration. P21's data model (memories + voice stream) is the highest-stakes retroactive migration in the system. A nullable `project_id` column on day 1 is essentially free; backfilling after the fact is a destructive operation that touches the most intimate data layer (memory).

### 3.5 Decision

- **Default project**: until P19 lands, all voice episodes / voice stream rows have `project_id = NULL` (default project = Faiz-global). This is forward-compatible and lets P19 promote the default project into a real project without a backfill.
- **No code path references a `src/projects/` import**: P21 uses optional `project_id` parameters throughout; if P19 isn't there, every call site is `project_id=None` and behaviour is identical to today.
- **Migration ordering**: P21 migration precedes P19; P19 references P21's nullable column.

---

## 4. P22 integration map — voice is NOT deferred to P22

### 4.1 P22 status

Per `docs/setup-evidence/P22/README.md` L1-2, L48-49: **P22 is NOT STARTED** — TBD integrations. Candidates: calendar, note-taking, task boards, code hosting, additional chat platforms (NOT explicitly including voice). The README explicitly states "Specific integrations and scope are TBD."

### 4.2 Voice ownership

Voice is a **first-class input surface** (parallel to Discord text), not a "third-party integration" in the P22 sense. P22's language ("third-party integrations beyond the core surface already covered by earlier phases") frames P22 as connectors to external SaaS. Voice is internal infrastructure (STT/TTS providers are infrastructure, not user-facing integrations).

**Decision: P21 OWNS voice. Voice is NOT deferred to P22.** This is consistent with the P21 README's L7-12 "first-class surveillance stream" framing and with the absence of voice from P22's candidate list.

### 4.3 P22 candidates voice could later invoke

When P22 lands with calendar / note apps / task boards, voice could in the FUTURE invoke those via Hermes tool-calling (e.g. "Guinevere, add this to my calendar"). That is a Phase-N+ capability, not a P21 deliverable. P21 must NOT pre-design voice-tool-calling hooks for TBD P22 integrations; doing so would couple voice to TBD contracts.

| P22 candidate | Voice use case (future) | P21 touch point |
|---|---|---|
| Calendar provider | "schedule a meeting" via voice | Hermes tool schema only; voice does not hardcode calendar MCP name. |
| Note-taking app | "save this note" via voice | Same: tool schema. |
| Task board | "add task X" via voice | Same: tool schema. |
| Additional chat platforms | None (voice = Discord voice for now) | None. |

**Design rule**: P21 voice is a *delivery surface*, not a *tool author*. Voice translates audio ↔ text and lets the existing conversational turn + Hermes tools handle the rest. P22 integrations add tools; voice doesn't reach into tool internals.

---

## 5. Shared-writer collision scan (AGENTS.md §2.6)

Per `AGENTS.md` L176-189 (§2.6 Collision Scan): same source/doc file, shared docs, shared config, migrations, shared tests/fixtures, and safety boundary docs all require one owner or explicit sequencing.

### 5.1 Files in P21's reach vs P20's lock

| File / surface | P20 owner status (soak in progress) | P21 intended touch | Collision risk | Mitigation |
|---|---|---|---|---|
| `src/life_kernel/heartbeat.py` | LOCKED (production-pass HOLD; 1s HARD-STOP loop) | None (P21 does not edit) | NONE | **No edits to `heartbeat.py` during P20 HOLD**. New sensor adapter is a new file. |
| `src/life_kernel/hermes_brain.py` | LOCKED (kernel brain) | None (P21 uses Hermes via `adapter.py`, not `hermes_brain.py`) | NONE | **No edits to `hermes_brain.py` during P20 HOLD**. |
| `src/life_kernel/graph.py` | LOCKED (graph nodes) | None | NONE | **No edits to `graph.py` during P20 HOLD**. |
| `src/life_kernel/state.py` | LOCKED (TypedDict state) | Add `NotRequired` fields only (additive) | LOW | Additive-only with default fallbacks; verify by replaying existing checkpoint JSON. |
| `src/life_kernel/sensors.py` | LOCKED (Protocol) | None — new adapter implements existing Protocol | NONE | New file `src/life_kernel/sensor_adapters/voice_sensor_adapter.py`. |
| `src/life_kernel/sensor_adapters/*` | UNLOCKED (per-adapter files; new ones welcome per LK-011) | Add new `voice_sensor_adapter.py` | NONE | New file; existing adapters untouched. |
| `src/life_kernel/dashboard.py` | LOCKED (renderer) | Add new `_voice_section()` (additive) | LOW | Additive; existing sections unchanged. |
| `src/life_kernel/dashboard_writer.py` | LOCKED (Discord edit-only) | None | NONE | — |
| `src/core/main.py` | SHARED (P20 lifespan + Discord bot startup) | Add voice bot startup wire AFTER kernel init | MEDIUM | Sequence: voice wiring in a separate startup step *after* `guinevere-core` lifespan; verify with p20-001 soak evidence. |
| `src/discord/_entrypoint.py` | UNLOCKED (bot entrypoint) | Add voice client init if P21 owns the voice connection in the same bot | MEDIUM | P21 should add a new `_voice_client.py` next to `_entrypoint.py`; entrypoint wires it AFTER existing bot init. |
| `src/discord/cmd_*.py` | UNLOCKED (per-command files) | Add `cmd_voice.py` for `/voice_join`, `/voice_leave` (slash) | NONE | New file; existing commands untouched. |
| `src/hermes/adapter.py` | LOCKED (HermesSessionAdapter singleton) | None — P21 calls `get_adapter()` like Discord does | NONE | **No edits to `adapter.py` during P20 HOLD**. |
| `src/hermes/_memory_bridge.py` | LOCKED (memory bridge) | Add optional `project_id` kwarg (default `None`) | LOW | Additive kwarg with default; existing callers unchanged. Verify signature compatibility in P20-001 soak evidence. |
| `src/hermes/safety_plugin.py` | LOCKED (Hermes safety) | None | NONE | — |
| `src/hermes/plugins/persona_plugin.py` | LOCKED (Hermes persona) | None | NONE | — |
| `src/memory/models.py` | LOCKED (P18 memory substrate) | Add nullable `project_id` to `Episodes` (and any new `VoiceStream` model) | LOW | Additive nullable column with backfill default. |
| `src/surveillance/models.py` | UNLOCKED (P19-class surveillance schema) | Add `VoiceStream` model + `ClassificationMetaMixin` | LOW | New table; existing tables untouched. |
| `src/core/services/hard_stop_handler.py` | LOCKED (P1-021 app-level safety guard) | None — P21 calls `HardStopHandler.check(transcript)` | NONE | **No edits to `hard_stop_handler.py` during P20 HOLD**. |
| `src/persona/safe_mode.py` | LOCKED (DistressDetector, SafeModeController) | None — P21 calls existing detector/controller | NONE | **No edits to `safe_mode.py` during P20 HOLD**. |
| `docs/setup-evidence/P20/evidence/**` | LOCKED (P20 evidence) | None | NONE | P21 writes to `docs/setup-evidence/P21/evidence/`. |
| `docs/setup-evidence/P19/evidence/**` | UNLOCKED (P19 not started) | None | NONE | — |
| `AGENTS.md` | SHARED (operating contract) | None during P21 planning; future P21 must update §0 if voice adds new contract | NONE | P21 implementation wave may add a §0.2 sub-section for voice contracts; sequenced to single-owner. |
| `secrets/guinevere-secrets.yaml` | LOCKED (existing SOPS envelope) | None — new `voice-secrets.enc.yaml` separate file | NONE | New SOPS file under existing `secrets/.gitignore` rules. |
| `alembic/env.py` | LOCKED | None | NONE | New migration file only. |
| `alembic/versions/p20_001_life_kernel_schema.py` | LOCKED | None — new migration chained AFTER | NONE | New migration `p21_001_voice_stream.py` with `down_revision = 'p20_001_life_kernel_schema'`. |
| `docs/10-governance/17-ADR_Index_v1.0.md` | SHARED (ADR index) | Add ADR for voice-as-injection-surface (V-022) | LOW | Single-owner update after P21 planning; record voice-specific V-022 vector in prompt-injection spec. |
| `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` | LOCKED (V-001..V-021) | Add V-022 voice transcript section | MEDIUM | One-owner update; sequenced to single-edit. |
| `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | LOCKED | None — voice inherits persona policy by Trust L6 classification | NONE | — |
| `docs/60-persona/63-DiscordUXSpec_v1.0.md` | LOCKED (Discord UX) | Optional: add a `§X Voice Channel` section | LOW | Single-owner additive section. |
| `hermes-config/SOUL.md` | LOCKED (persona) | None — voice reads same SOUL.md via existing system-prompt loader | NONE | — |
| `hermes-config/config.yaml` | LOCKED (Hermes config) | None | NONE | — |
| `docs/setup-evidence/P21/README.md` | UNLOCKED (P21 dir is P21's) | P21 owner-edits | NONE | Single-owner (P21). |
| `docs/setup-evidence/P21/plan/*` | UNLOCKED (P21 plan dir) | P21 owner-edits | NONE | Single-owner (P21). |
| `docs/setup-evidence/P21/research/*` | UNLOCKED (P21 research dir) | P21 owner-edits | NONE | Single-owner (P21). |
| `tests/life_kernel/test_*.py` | LOCKED (P20 test suite, 390 passing) | None | NONE | New tests in `tests/voice/` directory. |
| `tests/safety/test_hard_stop_comprehensive.py` | LOCKED | None — P21 voice reuses existing test as evidence | NONE | Voice-specific tests in `tests/voice/test_voice_hard_stop.py`. |
| `tests/discord/test_bot.py` | LOCKED | None | NONE | — |
| `tests/mcp/test_auth_matrix.py` | LOCKED | None — voice is not an MCP tool | NONE | — |
| `tests/hermes/test_safety_plugin.py` | LOCKED | None | NONE | — |
| `src/loops/*` | UNLOCKED but P20 owns | None | NONE | P21 does not use the loops/ package. |
| `src/wearable/*` | UNLOCKED (P14 wearable) | None — voice ≠ wearable; voice may INTERFACE with wearable's alert_router for audio cues | LOW | Future hook (not in P21 v1). |

### 5.2 Sequencing rule (binding)

> **P21 implementation wave is BLOCKED on P20 production-pass.** Per `P20/README.md` L48-49 ("LK-017 PRODUCTION DEPLOYED — SOAK IN PROGRESS — PRODUCTION PASS HOLD") and per AGENTS.md §2.6 collision scan, edits to any LOCKED file in §5.1 above require the P20 production-pass to complete first. P21 PLANNING (research, plan, design) is allowed now; P21 IMPLEMENTATION on those files waits.

> **P21 NEW files (sensors, voice package, alembic migration, secrets file, tests) are UNLOCKED.** Adding a new file under `src/life_kernel/sensor_adapters/`, `src/voice/`, `alembic/versions/`, `secrets/`, or `tests/voice/` does not collide with the P20 soak because no existing production file is modified.

### 5.3 Single-owner rule for shared files

| Shared file | P21 owner | Sequence |
|---|---|---|
| `src/life_kernel/state.py` (additive TypedDict fields) | P21, additive-only | After P20 production-pass; verified by replaying an existing checkpoint to confirm new fields default to absent. |
| `src/hermes/_memory_bridge.py` (additive `project_id` kwarg) | P21, additive-only | Same as above. |
| `src/memory/models.py` (nullable `project_id` column) | P21, additive-only | Same as above; new alembic migration. |
| `src/core/main.py` (voice bot wire) | P21 | After P20 production-pass; voice wire in a separate FastAPI lifespan step. |
| `docs/10-governance/17-ADR_Index_v1.0.md` (V-022 ADR pointer) | P21, single-edit | After P21 plan approved. |
| `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` (V-022 section) | P21, single-edit | After P21 plan approved. |
| `docs/60-persona/63-DiscordUXSpec_v1.0.md` (voice section) | P21, additive | Optional. |

---

## 6. Config / env collision

### 6.1 Existing secret layout (per `secrets/`)

| File | Contents | P21 touch |
|---|---|---|
| `secrets/guinevere-secrets.yaml` | Top-level secrets envelope | None — P21 has its own file. |
| `secrets/db-passwords.yaml` | PostgreSQL | None. |
| `secrets/redis-password.yaml` | Redis | None. |
| `secrets/discord-secrets.enc.yaml` | Discord token | None — voice uses existing Discord token for voice-channel connection. |
| `secrets/gmail-client-secrets.json` | Gmail OAuth | None. |
| `secrets/gmail-token.json` | Gmail token | None. |
| `secrets/backup/`, `secrets/test-enc.yaml` | Backup + test | None. |

### 6.2 P21 secret file (new, separate)

| File | Contents | Format |
|---|---|---|
| `secrets/voice-secrets.enc.yaml` (new) | STT provider key, TTS provider key, wake-word model path, VAD threshold | SOPS-encrypted with `.sops.yaml` `secrets/.*\.yaml$` rule. |

### 6.3 No clash with `mcp.production.yaml.sops`

Per `docs/60-persona/62-MCPConfigGuide_v1.0.md` (sections L114, L219, L226, L329, L426, L433, L549, L654, L773, L781, L898, L904, L1011, L1121, L1222, L1315, L1321, L1424, L1528, L1534, L1680, L1686, L1829, L2033, L2626), the `mcp.production.yaml.sops` file contains the MCP provider keys (brave_search, exa, github, grep_app, websearch, postgres, redis) for the `guinevere-mcp` service. STT/TTS providers are NOT MCP tools — they are direct HTTP API calls from `src/voice/`. Therefore, P21 does not extend `mcp.production.yaml.sops` and there is **no key namespace collision**.

### 6.4 Env vars

| Env var (P21 introduces) | Purpose | Conflict? |
|---|---|---|
| `VOICE_STT_PROVIDER` | STT provider name (deepgram / openai / google / whisper) | NEW; no existing var. |
| `VOICE_TTS_PROVIDER` | TTS provider name | NEW. |
| `VOICE_STT_API_KEY` | STT key (SOPS-loaded) | NEW. |
| `VOICE_TTS_API_KEY` | TTS key (SOPS-loaded) | NEW. |
| `VOICE_WAKE_WORD_ENABLED` | bool | NEW. |
| `VOICE_VAD_THRESHOLD` | float (0.0..1.0) | NEW. |
| `VOICE_PTT_DEFAULT_CHANNEL` | Discord voice channel ID | NEW. |
| `VOICE_DISCORD_TOKEN` | may reuse existing `DISCORD_TOKEN` | NO NEW — reuse existing. |
| `VOICE_RATE_LIMIT_PER_MIN` | mirror of `RATE_LIMIT_MAX` for voice turns | NEW but same semantics as existing. |

### 6.5 `mcp.production.yaml.sops` keys — not touched

| Section | P21 must NOT add | Reason |
|---|---|---|
| `brave_search`, `exa`, `websearch`, etc. | STT/TTS keys are not search providers | — |
| `postgres.passwords.*` | — | — |
| `redis.password` | — | — |
| `github.pat`, `grep_app.api_key` | — | — |

P21 keys live in `secrets/voice-secrets.enc.yaml` and are loaded by `src/voice/config.py` (new). Zero collision.

---

## 7. Migration collision (alembic)

### 7.1 Existing migration chain

| Revision | File | Purpose |
|---|---|---|
| `2bed93fd1dd0` | `alembic/versions/2bed93fd1dd0_baseline_init.py` | Baseline. |
| `e401bb5fd274` | `alembic/versions/e401bb5fd274_initial_schema_47_tables.py` | 47 tables. |
| `65f863220922` | `alembic/versions/65f863220922_add_search_vector_do_not_recall.py` | Search vector. |
| `p5_012` ... `p5_024` | `alembic/versions/p5_*.py` | P5 series. |
| `p18_add_memory_tiers_fsrs` | `alembic/versions/p18_add_memory_tiers_fsrs.py` | P18 memory. |
| `p20_001_life_kernel_schema` | `alembic/versions/p20_001_life_kernel_schema.py` | P20 life_kernel schema. |

The current head is `p20_001_life_kernel_schema` (down_revision: `p5_024`).

### 7.2 P21 migration plan

| Revision | File | Down-revision | Schema(s) touched |
|---|---|---|---|
| `p21_001_voice_stream` (new) | `alembic/versions/p21_001_voice_stream.py` | `p20_001_life_kernel_schema` | New `voice` schema with `voice_stream` table; nullable `project_id` column added to `memory.episodes`. |

**Naming convention check**: existing files use `<source>_<n>_<slug>.py` (e.g. `p20_001_life_kernel_schema.py`, `p5_024_add_session_summaries.py`). P21 must follow the same pattern: `p21_001_<slug>.py` where `<slug>` is the table/feature name (e.g. `p21_001_voice_stream.py`).

**Schema placement options**:
1. New `voice` schema (mirrors `life_kernel`, `memory`, `surveillance`).
2. Inside existing `surveillance` schema as `surveillance.voice_stream` (consistent with P21 README's "first-class surveillance stream" framing).

**Recommendation**: schema = `surveillance.voice_stream`. Reasons: (a) P21 README explicitly calls voice a "surveillance stream"; (b) reuses existing `ClassificationMetaMixin` discipline via `surveillance.*` tables; (c) avoids creating a new top-level schema that future phases would have to learn.

### 7.3 Collision check

- No existing migration file is touched.
- `down_revision` chain is preserved: P21 head → `p20_001` → `p5_024` → ... → baseline. Zero conflict with any in-progress P20 migration.
- New migration introduces a new `voice_stream` table OR a `surveillance.voice_stream` table — no existing table is altered.
- Optional nullable `project_id` on `memory.episodes` is an additive column with `server_default NULL`. P19 will later fill it; P20 memory is unaffected.

### 7.4 Head revision sync

P21 implementation wave must `alembic upgrade head` in the SAME P21 evidence step that introduces the migration. No half-migrated state.

---

## 8. P21 voice HARD STOP path (design, not implementation)

The voice turn's HARD STOP semantics are **not new code** — they are a wire-up of existing infrastructure. Documented here for the planner to confirm the seam is single-source-of-truth.

```text
Voice turn
   │
   ├── STT (Deepgram / OpenAI / Whisper)
   │     → transcript: str
   │
   ├── [INJECTION QUARANTINE — new] src/voice/sanitize.py
   │     → wraps transcript in <untrusted source="voice_transcript" trust="L6">...</untrusted>
   │     → adds trust metadata {trust_level: 6, source_type: voice, ts: ..., classifier_version: ...}
   │
   ├── HardStopHandler.check(transcript)        ← src/core/services/hard_stop_handler.py (LOCKED, reuse)
   │     → if True: set life_kernel:hard_stop, set state.is_active=False, fire callbacks, DO NOT proceed to Hermes
   │
   ├── DistressDetector.detect(transcript)      ← src/persona/safe_mode.py (LOCKED, reuse)
   │     → if D2+: SafeModeController.evaluate → toggle safe mode
   │
   ├── handle_conversation(...)                  ← src/discord/hermes_conversational.py (LOCKED, reuse)
   │     → rate limit → mood → memory recall → Hermes AIAgent → response
   │
   ├── TTS (ElevenLabs / OpenAI / Edge)
   │     → audio response sent to Discord voice channel
   │
   └── log: voice_session_id, transcript_len, TTS_provider, latency_ms
```

**Key**: zero new safety code. Voice reuses HARD STOP, distress, memory recall, Hermes, and chunking. The ONLY new code is the STT/TTS wire, the L6 quarantine wrapper, and the Discord voice-channel connection.

---

## 9. Collision matrix (consolidated)

| File / Config / Migration | P20 owner | P21 touches | Collision risk | Mitigation |
|---|---|---|---|---|
| `src/life_kernel/heartbeat.py` | LOCKED | None | NONE | Do not edit during P20 HOLD. |
| `src/life_kernel/hermes_brain.py` | LOCKED | None | NONE | Do not edit during P20 HOLD. |
| `src/life_kernel/graph.py` | LOCKED | None | NONE | Do not edit during P20 HOLD. |
| `src/life_kernel/state.py` | LOCKED | Additive `NotRequired` fields | LOW | Default-safe additions; checkpoint-replay test. |
| `src/life_kernel/sensors.py` | LOCKED (Protocol) | None | NONE | New adapter file. |
| `src/life_kernel/sensor_adapters/voice_sensor_adapter.py` | N/A (new) | NEW file | NONE | New file; implements existing Protocol. |
| `src/life_kernel/dashboard.py` | LOCKED | Additive `_voice_section()` | LOW | Existing sections untouched. |
| `src/life_kernel/dashboard_writer.py` | LOCKED | None | NONE | — |
| `src/life_kernel/{cognition,journal,checkpoint,redis_client,discord_rest_client,self_improve}.py` | LOCKED | None or read-only | NONE | — |
| `src/life_kernel/p18_adapter.py` / `p16_adapter.py` | LOCKED | None | NONE | Voice observations flow through P18 memory bridge. |
| `src/life_kernel/domain_minds/*` | LOCKED | None | NONE | — |
| `src/life_kernel/session_graph.py` | LOCKED | Optional reuse for per-session voice | NONE | Reuse existing API. |
| `src/core/main.py` | SHARED (P20 lifespan) | Voice bot wire AFTER kernel | MEDIUM | Sequence: voice in a separate lifespan step. |
| `src/core/services/hard_stop_handler.py` | LOCKED (P1-021) | None — reuse | NONE | Do not edit; P21 calls `.check()`. |
| `src/core/services/{cost_tracker,llm_router,llm_metrics,prompt_loader,monthly_report}.py` | LOCKED | None | NONE | Voice runs through existing cost tracking. |
| `src/discord/hermes_conversational.py` | LOCKED | None — voice CALLS `handle_conversation()` | NONE | Do not edit; voice reuses orchestrator. |
| `src/discord/_entrypoint.py` | UNLOCKED | New voice-client init in a sibling file | LOW | Add `src/discord/_voice_client.py`; entrypoint wires it. |
| `src/discord/cmd_*.py` | UNLOCKED (per-command) | New `cmd_voice.py` for slash commands | NONE | New file. |
| `src/discord/{listeners,loops,colors,notifications,_embed_utils,_intents,_startup,_auth_guard,_command_registry,gotify_fallback,shadow_monitor,shadow_pipeline}.py` | LOCKED | None | NONE | — |
| `src/hermes/adapter.py` | LOCKED (HermesSessionAdapter singleton) | None — P21 calls `get_adapter()` | NONE | Do not edit. |
| `src/hermes/_memory_bridge.py` | LOCKED | Additive `project_id` kwarg | LOW | Default `None`; existing callers unchanged. |
| `src/hermes/_session_adapter.py` | LOCKED | None | NONE | — |
| `src/hermes/safety_plugin.py` / `plugins/persona_plugin.py` | LOCKED | None | NONE | — |
| `src/memory/models.py` | LOCKED (P18) | Nullable `project_id` on `Episodes` | LOW | New alembic migration. |
| `src/memory/{consolidation,read_pipeline,__init__,embeddings}.py` | LOCKED | None | NONE | — |
| `src/surveillance/models.py` | UNLOCKED (P19-class) | New `VoiceStream` model | LOW | New table; existing tables untouched. |
| `src/surveillance/{auth,classification,consumer,redis_buffer,replay,retention,router,safe_mode,secret_scanner,secrets,timescale,consent_gate}.py` | LOCKED | None | NONE | Voice uses existing surveillance consent + retention gates. |
| `src/persona/safe_mode.py` | LOCKED | None — P21 calls `DistressDetector.detect()` and `SafeModeController.evaluate()` | NONE | Do not edit. |
| `src/wearable/*` | UNLOCKED (P14) | None in P21 v1 | NONE | Future hook only. |
| `src/loops/*` | UNLOCKED but P20 owns | None | NONE | P21 does not use the loops/ package. |
| `src/voice/*` (new) | NEW (P21) | All P21 voice code | NONE | New package. |
| `src/mcp/*` | LOCKED (MCP layer) | None — voice is not an MCP tool | NONE | — |
| `alembic/versions/p20_001_life_kernel_schema.py` | LOCKED | None | NONE | New migration chained AFTER. |
| `alembic/versions/p21_001_voice_stream.py` (new) | NEW (P21) | NEW file | NONE | `down_revision = p20_001_life_kernel_schema`. |
| `alembic/env.py` | LOCKED | None | NONE | — |
| `secrets/guinevere-secrets.yaml` | LOCKED | None | NONE | New `voice-secrets.enc.yaml` separate. |
| `secrets/voice-secrets.enc.yaml` (new) | NEW (P21) | NEW file | NONE | New SOPS envelope under existing `secrets/.*\.yaml$` rule. |
| `secrets/discord-secrets.enc.yaml` | LOCKED | None — voice reuses existing Discord token | NONE | — |
| `mcp.production.yaml.sops` | LOCKED (MCP keys) | None | NONE | STT/TTS are not MCP tools. |
| `hermes-config/SOUL.md` | LOCKED | None | NONE | Voice reads same SOUL.md via prompt loader. |
| `hermes-config/config.yaml` | LOCKED | None | NONE | — |
| `docs/10-governance/17-ADR_Index_v1.0.md` | SHARED | Add V-022 pointer (single-edit) | LOW | P21 single-owner. |
| `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` | SHARED | Add V-022 section (single-edit) | MEDIUM | P21 single-owner after plan approval. |
| `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | LOCKED | None | NONE | Voice inherits persona policy via Trust L6 classification. |
| `docs/60-persona/61-SystemPromptMaster_v1.1.md` | LOCKED | None | NONE | — |
| `docs/60-persona/62-MCPConfigGuide_v1.0.md` | LOCKED | None — voice is not MCP | NONE | — |
| `docs/60-persona/63-DiscordUXSpec_v1.0.md` | LOCKED | Optional additive §X voice section | LOW | P21 single-owner additive. |
| `docs/setup-evidence/P20/**` | LOCKED (P20 evidence) | None | NONE | P21 evidence in P21 dir. |
| `docs/setup-evidence/P19/**` | UNLOCKED (P19 not started) | None | NONE | — |
| `docs/setup-evidence/P21/**` | NEW (P21) | P21 owns | NONE | Single-owner. |
| `AGENTS.md` | SHARED (operating contract) | Optional §0.2 voice contract | NONE | P21 single-owner. |
| `.sops.yaml` | LOCKED | None | NONE | Existing rule `secrets/.*\.yaml$` already covers new file. |
| `tests/life_kernel/test_*.py` | LOCKED (390 passing) | None | NONE | New tests in `tests/voice/`. |
| `tests/safety/test_hard_stop_comprehensive.py` | LOCKED | None | NONE | Voice reuses as evidence; new tests in `tests/voice/`. |
| `tests/discord/test_bot.py` | LOCKED | None | NONE | — |
| `tests/hermes/test_safety_plugin.py` | LOCKED | None | NONE | — |
| `tests/mcp/test_auth_matrix.py` | LOCKED | None | NONE | — |
| `monitoring/*` | LOCKED (observability) | None | NONE | Voice metrics use existing Prometheus exporters. |
| `scripts/guinevere-backup.sh` | LOCKED | None | NONE | — |
| `pyproject.toml` | LOCKED | New deps (e.g. `discord.py[voice]`, `deepgram-sdk`) | MEDIUM | P21 single-owner; align with P20 audit gates. |
| `uv.lock` | LOCKED | Auto-regenerated by P21 deps | LOW | Generated; verify with `uv lock --check`. |

### 9.1 Risk-class summary

| Risk | Count | Files |
|---|---|---|
| NONE | 39 | LOCKED files P21 does not touch + new files P21 owns |
| LOW (additive, single-edit, sequenced) | 9 | `state.py`, `dashboard.py`, `_memory_bridge.py`, `models.py`, `voice-secrets.enc.yaml`, ADR index, Discord UX spec, alembic env (no edit), `uv.lock` |
| MEDIUM (shared, sequenced-after-HOLD) | 3 | `src/core/main.py`, `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` (V-022), `pyproject.toml` |
| HIGH | 0 | — |

---

## 10. Sequencing plan (binding for P21 implementation wave)

### 10.1 P21 implementation wave is BLOCKED on the following gates

1. **P20 production-pass (LK-017)**: `docs/setup-evidence/P20/README.md` L48-49 — kernel is in 24h clean-soak observation. P21 implementation that touches LOCKED files waits for PRODUCTION PASS.
2. **P19 first OR P21-with-seam**: P19 is NOT STARTED. P21 may proceed with the forward-compat seam (nullable `project_id`) without waiting for P19. P19 will be a future retrofit.
3. **P22 undefined**: P21 owns voice; no gate.

### 10.2 Allowed-now (planning) vs allowed-later (implementation)

| Phase | Allowed now | Blocked until |
|---|---|---|
| Planning / research | ALL P21 file writes under `docs/setup-evidence/P21/`, `research-reports/`, `secrets/voice-secrets.enc.yaml` skeleton, voice provider evaluation, V-022 spec | — |
| P21 NEW files | `src/voice/*`, `src/life_kernel/sensor_adapters/voice_sensor_adapter.py`, `alembic/versions/p21_001_voice_stream.py`, `secrets/voice-secrets.enc.yaml`, `tests/voice/*` | — (NEW files are non-conflicting with P20 soak because no existing file is modified) |
| P21 additive state fields | `src/life_kernel/state.py` (NotRequired additions), `src/memory/models.py` (nullable column) | P20 production-pass (replay-test must pass) |
| P21 wire to existing | `src/core/main.py`, `src/discord/_entrypoint.py`, `src/discord/cmd_voice.py`, `pyproject.toml` | P20 production-pass (soak evidence) |
| P21 doc updates | `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` (V-022), `docs/10-governance/17-ADR_Index_v1.0.md`, `docs/60-persona/63-DiscordUXSpec_v1.0.md` (optional) | P21 plan approved (single-owner edits) |

### 10.3 Concrete sequence

```text
GATE 1 (now): P21 planning
  - Write P21 plan, P21 step prompts, V-022 spec.
  - Write P21 research reports (this file is one of them).
  - Write P21 evidence scaffold.

GATE 2 (after P20 PRODUCTION PASS):
  - P21 implementation wave:
      Wave 1 (parallel, NEW files only):
        - src/voice/ package skeleton (config, types, exceptions, sanitize)
        - src/life_kernel/sensor_adapters/voice_sensor_adapter.py
        - alembic/versions/p21_001_voice_stream.py
        - secrets/voice-secrets.enc.yaml
        - tests/voice/test_voice_sanitize.py
      Wave 2 (parallel, additive-only edits):
        - src/life_kernel/state.py: add NotRequired fields
        - src/memory/models.py: add nullable project_id to Episodes
        - src/hermes/_memory_bridge.py: add project_id kwarg
        - src/life_kernel/dashboard.py: add _voice_section()
        - pyproject.toml: add voice deps
      Wave 3 (sequential after Wave 2, LOCKED-file wires):
        - src/core/main.py: voice bot wire
        - src/discord/_entrypoint.py: voice client init
        - src/discord/cmd_voice.py: slash commands
      Wave 4 (single-owner doc updates):
        - docs/20-security/24-PromptInjection_ModelSafety_v1.0.md (V-022 section)
        - docs/10-governance/17-ADR_Index_v1.0.md (pointer)
        - docs/60-persona/63-DiscordUXSpec_v1.0.md (optional §X voice)
      Wave 5 (P21 evidence + audit):
        - evidence/P21-001..005 verifications
        - auditor gates for each P21 step

GATE 3 (after P21 implementation):
  - Auditor wave (per AGENTS.md §3) — V-022 injection auditor, voice HARD STOP auditor, P20-non-interference auditor, Discord voice UX auditor.
  - Production rollout with 24h soak (mirrors LK-017 pattern).
```

---

## 11. Open questions for the planner

1. **Voice schema placement**: new `voice` schema OR `surveillance.voice_stream`? Recommendation = `surveillance.voice_stream` (consistent with P21 README's "first-class surveillance stream" framing; reuses `ClassificationMetaMixin` envelope).
2. **TTS persona voice**: P21 README mentions "consented persona voice" — is a pre-trained TTS voice (e.g. ElevenLabs voice clone) an intimate-data surface requiring separate consent, OR is it acceptable under the existing surveillance consent umbrella? ADR needed.
3. **Always-listening mode (P21-004)**: is "always-listening" an acceptable L4 surface, or must it require an opt-in token per session? PersonaSafetyPolicy §3.1 may require explicit decision. ADR needed.
4. **P19 dependency on P21 nullable `project_id`**: should the nullable column be added in P21, or wait for P19 to define the project schema first? Recommendation = P21 adds nullable column now (free, forward-compat).
5. **Discord voice library**: `discord.py[voice]` requires `PyNaCl` for encryption; check VPS resource budget. Pyproject update should be reviewed.
6. **STT provider rotation**: P21 README L17 mentions "STT/TTS provider integration with rotation." This is a multi-provider abstraction; is that in P21 scope or P22? Recommendation = P21 owns the abstraction; P22 owns specific SaaS connectors if needed.

---

## 12. Sources and freshness

| Source | Path | Retrieved | Notes |
|---|---|---|---|
| P19 README | `docs/setup-evidence/P19/README.md` | 2026-06-24 | Status: NOT STARTED, 2026-06-18. (Still NOT STARTED as of 2026-06-25.) |
| P20 README | `docs/setup-evidence/P20/README.md` | 2026-06-24 | Status: PRODUCTION STABILIZED, SOAK IN PROGRESS, PRODUCTION PASS HOLD. 5 bugs fixed during stabilization; soak restarted 2026-06-23 12:38 WIB. |
| P20 replan | `docs/setup-evidence/P20/plan/p5-p20-living-autonomy-kernel-replan.md` | 2026-06-24 | Authoritative for P20 architecture; supersedes old P5+P20 merged plan. |
| P20 plan bundle | `docs/setup-evidence/P20/plan/{p5-p20-vision-lock.md, p5-p20-architecture-benchmark.md, p5-p20-living-autonomy-kernel-todo-scaffold.md}` | 2026-06-24 | Referenced for LK-001..LK-017 sequence. |
| P22 README | `docs/setup-evidence/P22/README.md` | 2026-06-24 | Status (snapshot): NOT STARTED, TBD. **Current (2026-06-25): DEFINITION COMPLETE — IMPLEMENTATION HOLD UNTIL P20 CONTINUATION PASS** (renamed "Life Integration Hub"). |
| P21 README | `docs/setup-evidence/P21/README.md` | 2026-06-24 | Status (snapshot): NOT STARTED, 2026-06-18. **Current (2026-06-25): DEFINITION COMPLETE — IMPLEMENTATION HOLD UNTIL P20 CONTINUATION PASS.** |
| HardStopHandler | `src/core/services/hard_stop_handler.py` | 2026-06-24 | Class `HardStopHandler.check(message: str) -> bool`; EXACT_TRIGGERS includes `hard stop`, `safeword`, `hentikan`, `berhenti`; SEMANTIC_PATTERNS + RECOVERY_TRIGGERS. |
| Heartbeat | `src/life_kernel/heartbeat.py` | 2026-06-24 | 6 intervals (1s/10s/30s/60s/5m/1h); 1s loop reads `life_kernel:hard_stop` from Redis; calls `graph.ainvoke({"hard_stop_requested": True, "is_active": False}, ...)`. |
| HermesBrain | `src/life_kernel/hermes_brain.py` | 2026-06-24 | Wraps `AIAgent` for kernel decisions; lazy import. |
| Hermes conversational | `src/discord/hermes_conversational.py` | 2026-06-24 | `handle_conversation()` pipeline: channel/bot/slash/faiz checks → rate limit (DB0) → DistressDetector → SafeModeController → mood → memory recall → HermesSessionAdapter → response chunking → cost tracking → auto-store → shadow forward. |
| LifeMindState | `src/life_kernel/state.py` | 2026-06-24 | TypedDict with `Annotated[list[dict], add_observations_reducer]` (cap 100) and other fields. |
| SensorRegistry | `src/life_kernel/sensors.py` | 2026-06-24 | Protocol `_SensorAdapter` with `name`/`sense`/`health`; thread-safe registry. |
| Sensor adapters | `src/life_kernel/sensor_adapters/{discord,gmail,finance,wearable,surveillance,vps,repo,browser}_adapter.py` | 2026-06-24 | All implement `_SensorAdapter` Protocol. |
| Memory models | `src/memory/models.py` | 2026-06-24 | `Episodes` table with `ClassificationMetaMixin`; `Vector(1536)` embedding; FSRS-6 fields. |
| Prompt injection spec | `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` | 2026-06-24 | Trust hierarchy L1-L6; voice transcript is V-022-class (NEW vector). |
| PersonaSafetyPolicy | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | 2026-06-24 | Authority order; safe-word global hard stop; D0-D4 distress; F-01..F-15 forbidden patterns. |
| Discord UX spec | `docs/60-persona/63-DiscordUXSpec_v1.0.md` | 2026-06-24 | Single private server "Guinevere's Domain"; Faiz-only. |
| MCPConfigGuide | `docs/60-persona/62-MCPConfigGuide_v1.0.md` | 2026-06-24 | `mcp.production.yaml.sops` contains MCP provider keys (brave_search, exa, github, grep_app, websearch, postgres, redis). |
| AGENTS.md §2.6 | `AGENTS.md` L176-189 | 2026-06-24 | Collision scan rules. |
| AGENTS.md §0.1 | `AGENTS.md` L57-92 | 2026-06-24 | P20 autonomy-first exception — applies to kernel runtime only, NOT to dev workflow. |
| Migration chain | `alembic/versions/p20_001_life_kernel_schema.py` (down_revision=p5_024) | 2026-06-24 | P21 chains AFTER. |
| SOPS config | `.sops.yaml` | 2026-06-24 | `secrets/.*\.yaml$` rule covers new voice-secrets file. |

---

## 13. Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-24 | P21 specialist #7 — dependency-collision researcher | Initial collision matrix; P20 LOCKED file map; P19 forward-compat seam; P22 ownership decision; alembic + SOPS + MCP config analysis. |

**Verdict**: **PARTIAL PASS** — P21 is safe to PLAN (research, evidence, V-022 spec, design). P21 is BLOCKED on IMPLEMENTATION of LOCKED-file edits until P20 production-pass. NEW P21 files (under `src/voice/`, `src/life_kernel/sensor_adapters/voice_sensor_adapter.py`, `alembic/versions/p21_001_*.py`, `secrets/voice-secrets.enc.yaml`, `tests/voice/`) are unblocked and non-conflicting with P20 soak.
