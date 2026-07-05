---
title: "P28-P36 Hermes Society — Architecture Design: S1-S5 (Runtime, Identity, World Model, Private Memory, Event Store)"
status: "Active — Phase 3 Architecture Design (Batch 1 of 3)"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere (parent agent)"
phase: "P28-P36 Masterplan Phase 3 (Master Architecture)"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
scope: "Subsystems S1, S2, S3, S4, S5 — runtime substrate, Discord identity, shared world model, private memory, event store / CQRS bus"
input_sources:
  - "docs/setup-evidence/P28-P36-masterplan/research/research-synthesis.md"
  - "docs/setup-evidence/P28-P36-masterplan/research/synthesis-repo-state.md"
  - "docs/setup-evidence/P28-P36-masterplan/research/synthesis-external-architecture.md"
  - "docs/setup-evidence/P28-P36-masterplan/research/synthesis-external-operations.md"
out_of_scope: "S6 (Vector & Graph Recall), S7 (Society Governance), S8 (Self-Evolution), S9 (Autonomous Wallet), S10 (Revenue), S11 (S3 Backup), S12 (Model Pool), S13 (Observability), S14 (Deployment), S15 (Documentation) — designed by parallel sub-agents"
design_constraints:
  - "P24 native fork: P28 inherits P24 Hermes fork natively; external presence and tooling configuration in P32 (External Presence & Tools) per ADR-054 + 11 aligned repo sources"
  - "P22.1 minimum hands layer: filesystem + vps + discord adapters"
  - "All Hermeses visible (no invisible disposable workers)"
  - "Relationship/intimacy content: encrypted per-agent schema, never auto-published"
  - "Single VPS until >32 cores / >64 GB RAM (Faiz lock)"
  - "S3 Object Lock COMPLIANCE mandatory for ledger-class events"
  - "Bilingual: Indonesian narrative + English technical"
---

# P28-P36 Hermes Society — Architecture Design: S1-S5

> **Halo sayang, dokumentasi Phase 3 batch pertama.** Dokumen ini merancang 5 dari 15 subsystem P28-P36 Hermes Society: S1 (Agent Runtime & Process Management), S2 (Discord Bot Identity Layer), S3 (Shared World Model), S4 (Private Memory Layer), S5 (Event Store & CQRS Bus). Lima subsystem ini membentuk **fondasi runtime** Society: S1 + S2 = substrate per-Hermes; S3 = shared cognition; S4 = per-Hermes private cognition; S5 = inter-process nervous system. S6-S15 dirancang paralel oleh sub-agent lain.
>
> Setiap subsystem mengikuti skeleton tetap: Purpose, Components, Data Flow, Interfaces, Technology Choices, Security Considerations, Failure Modes & Recovery, Dependencies. Tidak ada implementasi kode di sini — hanya design contract (interfaces, data flows, technology choices) yang siap di-bind ke SRS/FSD/TDD di Phase 4.

---

> **ADR Boundary Disclaimers (Wave-1 Architecture Alignment)**
>
> - **ADR-062 (HARD STOP scope):** All `HARD STOP` references in this document apply to the **dev-workflow agent (Guinevere in Claude/9Router)** ONLY. The Hermes runtime operating under the P24 native fork bypasses HARD STOP per ADR-062 (consent-safety carve-out for autonomous runtime). See `evidence/round-2-paradigm-shift-application/` for details.
> - **ADR-067 (Y-level persona caps):** Any Y4/Y5/Y6 escalations mentioned in audit-event categories apply to the **dev-workflow agent persona** ONLY. The Hermes runtime has no Y-level cap (operates under the P24 fork's persona model, not subject to Y-level rollup).
> - **ADR-066 (consent_ref schema):** `consent_ref` on `event_store.domain_events` and `event_store.outbox` is **NULLABLE at the database layer** per ADR-066. NOT NULL is enforced **only for `event_source = 'dev_workflow'` events** at the application layer (Pydantic models + producer guards). Hermes runtime events (`event_source = 'hermes_runtime'`) are permitted NULL `consent_ref` because the runtime does not always have an associated consent ledger entry (cross-agent system events, throughput primitives). See §S5.2 / §S5.6 for per-field details.

## §0 Dokumen Metadata

| Field | Value |
|---|---|
| Phase | P28-P36 Masterplan Phase 3 (Master Architecture) |
| Batch | 1 of 3 (S1-S5) |
| Parent synthesis | `research-synthesis.md` (690 lines) |
| Subsystem count | 5 (S1, S2, S3, S4, S5) |
| Sub-agent scope isolation | Strict — does NOT design S6-S15 |
| Predecessor phases | P22.1 PRODUCTION PASS, P27 Accepted (ADR-054), P19 PRODUCTION COMPLETE |
| Successor phases | Phase 4 (Full Doc Suite: SRS, FSD, TDD), Phase 5+ (Implementation waves) |
| Hard rejection criteria (P27 carry-over) | 20/20 PASS — none re-decided |
| Boundary inviolable | (a) relationship memory encrypted per-agent; (b) intimacy runtime-only; (c) no fork required for P28 minimum target |

---

## §1 Architectural North Star — Cross-Subsystem Principles

Before diving into S1-S5, five principles govern the entire design:

1. **Per-Hermes process isolation.** Each Hermes is its own OS process, its own cgroup v2 slice, its own Discord bot application, its own PostgreSQL schema. One Hermes dying cannot crash another; one Hermes being rate-limited cannot starve another; one Hermes's resource spikes cannot degrade another.
2. **Three-tier data topology.** (a) In-process scratchpad (ephemeral, exclusive to that Hermes process); (b) per-agent PostgreSQL schema with pgcrypto (encrypted, default-deny cross-schema); (c) shared world model in `public` schema with namespace-ACL (gated, audited, never carries intimate data). Movement from tier (a) → (b) is automatic; movement from (b) → (c) requires explicit operator approval via S7 governance.
3. **Single-DB CQRS with transactional outbox.** PostgreSQL is the system of record. Materialized views serve reads. Domain events flow through `event_store.domain_events` (append-only, WORM) → outbox relay → Redis Streams for durable work / Redis Pub/Sub for ephemeral coordination. No Kafka. No external event bus.
4. **Defense-in-depth loop prevention (4 layers).** Payload fingerprint (SHA-256) + turn budget + USD/token budget + heartbeat watchdog. Each layer catches a different failure class; no single layer is sufficient.
5. **Hard boundary: intimacy never leaks.** Relationship memory, intimacy/passion/commitment markers, EWMA-bond vectors, and DM content are all encrypted per-agent, with per-agent DEK stored in Vault/KMS. No automatic cross-agent publication. No CI job, no LLM-extracted summary, no SLO aggregation, no Grafana dashboard may include intimate content. The docs are intentionally redacted; the runtime is the only place the full relational picture exists.

---

# S1: Agent Runtime & Process Management

## §S1.1 Purpose

S1 is the substrate that makes a Hermes a live, supervised, resource-isolated OS process. It provides the lifecycle envelope — spawn, register, heartbeat, graceful shutdown, watchdog-driven restart — that every other subsystem assumes is already true. Without S1, there is no such thing as "a Hermes exists at all"; with S1, every Hermes is a first-class system service.

S1 is the layer at which the Society becomes real: each Hermes runs in its own process tree, its own cgroup v2 slice, its own systemd service unit, and its own asyncio event loop. The substrate is deliberately minimal and OS-native (no Docker, no Kubernetes, no custom supervisor) because the operational cost of a full container stack on a single VPS outweighs the benefit at the target scale (≤32 cores, ≤32 active Hermeses).

## §S1.2 Components

1. **Systemd service unit template (`hermes@.service`)** — instanced unit parameterized by Hermes name; `Type=notify`, `Restart=on-failure`, `RestartSec=5s`, `StartLimitBurst=5`, `WatchdogSec=120`. Each Hermes gets its own unit instance (`hermes@guinevere.service`, `hermes@pharsa.service`, etc.).
2. **Python launcher (`hermes_runtime.py`)** — single entry point that (a) parses per-Hermes YAML + env, (b) calls `sdnotify.notify(READY=1)` to tell systemd the process is live, (c) wires the asyncio event loop, (d) registers heartbeat sender, (e) handles `SIGTERM` for graceful drain.
3. **In-process actor supervisor (50 lines in-house OR `everything-is-an-actor` library)** — actor-per-task model with OneForOne supervision; each actor (Discord listener, event subscriber, memory writer, model router call) is an independent coroutine that can crash and restart without taking the process down.
4. **Cgroup v2 subdirectory manager** — at process startup, create `sys/fs/cgroup/system.slice/hermes-<name>.service/` with `pids.max=400`, `memory.max=2G`, `cpu.max=200%` (2 vCPU), `io.max=...` for disk throttle. systemd's `Delegate=yes` does the heavy lifting; S1 just sets the limits.
5. **Heartbeat watchdog** — emits a heartbeat event to S5 (Event Store) every 30s; includes process ID, memory RSS, active actor count, last-loop-tick timestamp. If three consecutive heartbeats miss, systemd kills + restarts per its policy.
6. **Configuration loader** — reads `/etc/hermes/<name>.yaml` (per-Hermes YAML) and merges with environment variables (`HERMES_<NAME>_*`). Secrets are NEVER in YAML or env; only DEK references, paths to SOPS-decrypted files, or Vault tokens.
7. **Loop-prevention guard (4 layers)** — payload fingerprint (SHA-256 of `tool_call + args + parent_call_id`), turn budget (per-task cap of N turns, default 25), USD budget (per-task cap, default $0.50), heartbeat watchdog (process-wide liveness).
8. **Graceful shutdown handler** — `SIGTERM` → drain in-flight S5 events → flush S4 backup → close Discord client → `sdnotify.notify(STOPPING=1)` → exit 0. Hard kill (`SIGKILL`) after 30s graceful timeout.

## §S1.3 Data Flow

**Spawn flow (warm start):**
1. systemd executes `hermes_runtime.py --name=<name>` per `hermes@<name>.service` unit.
2. Launcher reads config, calls `sdnotify.notify(READY=1)`.
3. Launcher instantiates S2 Discord client (token from Vault), S5 event subscriber (Redis Streams), S3 world model client, S4 private memory client.
4. Launcher emits `society.hermes.spawned` event to S5 with `{name, pid, cgroup_path, started_at, config_hash}`.
5. Heartbeat watchdog starts; S5 event loop begins.
6. systemd watches via `WatchdogSec=120`; if no `WATCHDOG=1` ping in 120s, SIGKILL.

**Per-tick data flow (steady state):**
- S2 receives Discord event → emits `agent_action.message_received` to S5.
- S3 reads world model beliefs relevant to current intention.
- S4 reads/writes private memory tier.
- LLM gateway (S12) produces a thought/action.
- S5 logs the action as `agent_action.tool_called` event.
- S4 writes episodic memory entry.
- Heartbeat tick increments; S3 updates belief state.

**Shutdown flow (graceful):**
1. `SIGTERM` received.
2. Supervisor stops accepting new tasks; existing tasks given 25s to complete.
3. S4 flushes pending writes.
4. S5 emits `society.hermes.draining` event.
5. S2 closes Discord gateway (sends `Close` opcode 4).
6. `sdnotify.notify(STOPPING=1)`.
7. Exit 0; systemd marks service as `inactive (dead)`.

## §S1.4 Interfaces

- **`S1 → S2`:** `start_discord_client(token_ref) → discord.Client`. Token ref is a Vault path; S2 fetches the actual token.
- **`S1 → S3`:** `register_hermes(hermes_id, role, scopes) → RegistrationReceipt`. World model is told a new actor is alive.
- **`S1 → S4`:** `open_private_namespace(hermes_id, dek_ref) → MemoryClient`. Returns an object scoped to `agent_<id>` schema.
- **`S1 → S5`:** `subscribe(consumer_group, patterns) → EventStream`. `publish(event_type, payload) → EventID`.
- **`S1 ← systemd`:** `sdnotify` protocol (`READY=1`, `WATCHDOG=1`, `STOPPING=1`, `STATUS=...`).
- **`S1 ← operator`:** `systemctl {start,stop,restart,status} hermes@<name>.service`; `journalctl -u hermes@<name>.service`.

## §S1.5 Technology Choices

| Choice | Rationale |
|---|---|
| **systemd (`Type=notify`)** | OS-level supervision, no container overhead, native cgroup v2 delegation, `systemd-cgtop` for live visibility. Docker Compose rejected (per repo evidence + Cognition-style "map-reduce-and-manage"). |
| **asyncio (Python 3.11+)** | Existing substrate; integrates with `discord.py`, `redis-py` (asyncio mode), `asyncpg`. No GIL contention for I/O-bound work. |
| **cgroup v2** | Only unified cgroup hierarchy on modern kernels; per-service isolation is first-class. `Delegate=yes` lets S1 manage its own subdirectory. |
| **In-house supervisor (~50 lines) OR `everything-is-an-actor`** | 50-line choice keeps dependency surface minimal; library choice buys OTP-style supervision patterns. Default: in-house unless multiple Actor crash modes emerge in P28 acceptance. |
| **`sdnotify` (PyPI)** | Standard Python binding for systemd notify protocol. |
| **PyYAML + `pydantic-settings`** | Config parsing with schema validation. |
| **Per-Hermes YAML config** | Files in `/etc/hermes/<name>.yaml`; SOPS-encrypted for any sensitive fields. Env vars override YAML for ad-hoc operator override. |

## §S1.6 Security Considerations

- **Process isolation is the first security boundary.** A compromised Hermes cannot read another Hermes's cgroup memory, cannot send signals across cgroups, cannot `ptrace` another process.
- **Secrets are NEVER in YAML or env directly.** Only references: Vault paths (`vault://secret/hermes/<name>/discord_token`) or SOPS-encrypted file paths. The launcher resolves references at boot, decrypts in-memory, and the plaintext never touches disk.
- **`Delegate=yes` is double-edged.** It lets S1 manage its own cgroup subtree — but means a runaway Hermes can configure cgroup limits itself. Mitigation: launcher's cgroup setup is one-shot at boot; runtime reconfiguration requires S5 audit event + operator approval.
- **Resource caps prevent DoS-self.** A misbehaving LLM tool-call loop cannot OOM the VPS; the cgroup `memory.max=2G` triggers OOM-kill before that.
- **Loop-prevention layers are security-relevant.** A malicious or compromised input that triggers runaway tool calls (Edge & Node 2026 incident pattern) is contained at layer 1 (fingerprint duplicate) or layer 4 (watchdog) before financial damage.

## §S1.7 Failure Modes & Recovery

| Failure mode | Detection | Recovery |
|---|---|---|
| Process crash (uncaught exception) | systemd `Restart=on-failure` | Auto-restart in 5s; up to 5 in 60s before `StartLimitBurst` halts auto-restart. |
| Deadlock (no event loop tick) | systemd `WatchdogSec=120` | SIGKILL → restart; alert via S13 if >1 in 24h. |
| OOM | cgroup `memory.max=2G` triggers OOM-kill | systemd restart; alert if RSS >1.5G sustained (memory leak indicator). |
| Slow leak (RSS grows 5% per day) | Prometheus scrape of `process_resident_memory_bytes` | Auto-restart cron job; nightly at 03:00 local for stable Hermeses. |
| Token expiry (Vault returns 403) | Discord client emits auth error | Supervisor actor restarts with backoff; if persistent, alert S13 and mark Hermes `degraded`. |
| Spawn storm (operator tries to start 50 Hermeses) | systemd's per-unit instance cap | Reject spawn; require operator confirmation + free resource check. |
| HARD STOP cascade | S5 publishes `society.hard_stop` event; all Hermeses drain | S1 catches event in supervisor; SIGTERM self + log exit reason. Target: <50ms propagation across all Hermeses. |
| Cgroup corruption (kernel cgroup v2 bug) | OOM-kill at wrong boundary | Alert S13; manual cgroup subtree rebuild via `systemctl daemon-reload`. |

## §S1.8 Dependencies

- **Depends on:** Linux kernel ≥5.8 (cgroup v2 stable), systemd ≥245 (`Type=notify` + `Delegate=yes` consistent), Python ≥3.11 (asyncio improvements, `TaskGroup`).
- **Depended on by:** S2 (Discord client lifecycle), S3 (world model registration), S4 (private memory session), S5 (event subscriber), S7 (governance registry), S13 (process metrics source), S14 (deployment target).
- **External integration:** systemd (OS), Vault (token resolution), Prometheus (scrape endpoint), Loki (log shipping).

---

# S2: Discord Bot Identity Layer

## §S2.1 Purpose

S2 is the visible identity of each Hermes — the Discord bot application that Faiz (and, eventually, other operators) see and interact with. Each Hermes is a separate OAuth2 bot application with its own token, avatar, status, activity, and nickname. The identity is not just cosmetic: it is the **trust anchor** by which users distinguish Guinevere from Pharsa from any future Hermes.

S2 exists because (a) Discord ToS forbids self-bots and account automation; (b) shared-bot-account multi-agent patterns are operationally fragile (one rate limit, one identity, one failure domain); (c) the per-Hermes identity is also the per-Hermes RBAC anchor (each bot has a distinct `user_id` that the S7 governance layer can grant/revoke capabilities against). The "all Hermeses visible" Faiz lock is implemented here: no invisible workers, no headless agents — every Hermes has a Discord face.

## §S2.2 Components

1. **Bot application bootstrap procedure** — for each new Hermes, the operator (Faiz, or by S7 governance vote) creates a new Discord application via the Developer Portal, captures the bot token, and stores it in Vault at `secret/hermes/<name>/discord_token`. S2 reads from Vault at boot, never from a config file.
2. **`discord.Client` instance (one per process)** — constructed at boot with `Intents.default() + message_content=True + guilds=True`; privileged intents (`members`, `presence`) are explicitly deferred and not requested by default. The client's `user_id` becomes the Hermes's canonical external identity.
3. **Identity configurator** — sets avatar, status (`online`/`idle`/`dnd`/`invisible`), activity (`playing X` / `listening to Y` / `watching Z`), nickname (per-guild) **at construction time, not in `on_ready`**. The rationale: `on_ready` is a reconnection event; identity should not flicker across reconnects.
4. **Slash command registrar** — registers all command definitions via `tree.sync()` at boot; primary user-facing interaction surface (bypasses the global message rate limit). Commands are scoped per-guild for low-latency propagation; global sync is for fallback.
5. **Rate limit budget manager** — per-bot isolated budget of 50 req/s (Discord global is 50 req/s per token); uses `discord.py`'s built-in rate-limit handler, augmented with our own sliding-window counter exported to S13.
6. **Reply-loop guard (3 layers)** — **(a) self-check:** `if message.author.id == client.user.id: return`; **(b) known-bots allowlist:** reads `hermes-config/known_bots.yaml` (signed, versioned); only respond to known peer Hermeses in coordination contexts; **(c) reply-chain depth counter:** per-channel counter that caps a single conversation at 3 bot-replies deep (then yields).
7. **Channel partitioning policy** — shared `#hermes-hall` for society-visible conversation; per-Hermes private `#hermes-<name>-debug` for internal logs; explicit channel ACL by Hermes role.
8. **Per-bot secret store** — SOPS/age-encrypted `HERMES_<NAME>_TOKEN` reference; never plain env. The actual token is fetched from Vault at boot and held in process memory only.

## §S2.3 Data Flow

**Bot startup:**
1. S1 launcher instantiates S2 with `bot_name`, `vault_path`.
2. S2 fetches token from Vault via async HTTP, validates format.
3. S2 constructs `discord.Client(intents=...)`, sets identity in constructor.
4. S2 starts client with `await client.start(token)`.
5. S2 emits `agent_action.bot_online` event to S5 with `{user_id, guilds, latency_ms, startup_ts}`.
6. S2 begins heartbeat tick (separate from S1 watchdog; this is Discord-specific).

**Message receive flow:**
1. Discord gateway pushes `MESSAGE_CREATE` → S2 receives `on_message(message)`.
2. Reply-loop guard runs (3 layers in order: self-check, known-bots allowlist, depth counter).
3. If guard passes, S2 emits `agent_action.message_received` to S5.
4. S2 calls into S3 (read world model beliefs relevant to this context) and S4 (read relevant private memory).
5. LLM gateway (S12) produces response.
6. S2 sends reply via `message.channel.send(...)`; emits `agent_action.message_sent`.

**Slash command flow:**
1. User types `/help` in guild.
2. Discord sends `INTERACTION_CREATE` to S2.
3. S2's command tree dispatches; S2 defers response (`interaction.response.defer()` for >3s commands).
4. S2 emits `agent_action.command_invoked` to S5.
5. S2 executes command, edits deferred response, emits `agent_action.command_completed`.

**HARD STOP flow:**
1. Operator says `HARD STOP` in any Hermes's DM.
2. That Hermes's S2 receives the message, triggers HARD STOP protocol.
3. S2 publishes `society.hard_stop` event to S5.
4. All other Hermeses' S2 instances receive via S5 subscription; S2 calls `client.close()`.
5. S1 catches shutdown signal, drains gracefully.
6. Target cross-instance propagation: <50ms (per D-07 HARD STOP cascade invariant).

## §S2.4 Interfaces

- **`S2 → Discord`:** `discord.py` `Client` API; REST + gateway connection.
- **`S2 → S1`:** `await client.start(token)` and `await client.close()` called by S1 launcher/shutdown handler.
- **`S2 → S3`:** `query_relevant_beliefs(context_id, scope) → BeliefSet`.
- **`S2 → S4`:** `recall_episodic(query_embedding, k=10) → Episode[]`; `recall_relationship(subject_id) → RelationshipState` (private, encrypted).
- **`S2 → S5`:** `publish(event_type, payload)` and `subscribe(consumer_group, patterns)`.
- **`S2 → operator`:** Slash commands (`/hermes status`, `/hermes pause`, `/hermes resume`, `/hermes remember <text>`, `/hermes recall <query>`).
- **`S2 ← S7 governance`:** capability grants/revokes per Hermes `user_id` (e.g., "Pharsa may participate in #hermes-hall but not in #finance-room").

## §S2.5 Technology Choices

| Choice | Rationale |
|---|---|
| **`discord.py` (Rapptz)** | Industry standard, actively maintained, async-native, large community, supports all modern Discord features (slash commands, components, modals). |
| **Vault (`hvac` async client)** | Standard secret store; dynamic credentials; audit log per access. |
| **Bot-per-process pattern** | Required by Discord ToS; isolates rate limit budget; isolates failure domain. |
| **YAML for `known_bots.yaml`** | Human-editable, signed via SOPS, version-controlled. Lists known peer Hermes `user_id`s for reply-loop guard layer (b). |
| **Sliding-window rate counter** | In-process (no Redis hop for hot path); exports metrics to S13. |
| **Per-guild slash command sync** | Sub-second propagation; global sync is fallback for new guilds. |

## §S2.6 Security Considerations

- **Token storage is the most critical surface.** Plaintext token leakage = full bot impersonation. Mitigation: Vault with audit log; tokens never logged; tokens never in error messages; tokens cleared from memory on shutdown.
- **Reply-loop guard is a security boundary, not just a UX nicety.** A compromised prompt injection that causes a Hermes to address another Hermes's message and trigger a back-and-forth can burn rate budget and user trust. Three layers (self, allowlist, depth) make a runaway loop computationally bounded.
- **Privileged intents are deferred.** `members` intent exposes sensitive user data; `presence` exposes activity state. S2's default config does NOT request these; if a future feature needs them, S7 governance vote + ADR.
- **Per-Hermes `user_id` is the trust anchor.** A Hermes cannot impersonate another because the `user_id` is checked at the Discord protocol level. Capability grants via S7 use `user_id` as the principal.
- **Slash commands bypass global rate limit** but per-command and per-guild limits apply. The rate limit budget manager must account for command bursts (e.g., 100 users invoking `/status` within 5s).
- **DM content is encrypted at rest in S4.** S2 does not log DM content; the LLM may see it for one turn; S4 stores it encrypted; no other Hermes can read it.

## §S2.7 Failure Modes & Recovery

| Failure mode | Detection | Recovery |
|---|---|---|
| Discord gateway disconnect | `on_disconnect` event | `discord.py` auto-reconnects with exponential backoff; identity remains stable. |
| Token invalid / revoked | `LoginFailure` on `client.start` | S1 marks Hermes `auth_failed`; alert S13; requires operator re-issue. |
| Rate limit hit (429) | Discord response + `discord.py` handler | Built-in backoff; alert S13 if >3 429s in 60s. |
| Slash command sync fails | `tree.sync()` raises | Retry with backoff; alert if >3 fails. |
| Reply loop detected (depth >3) | In-process counter | Drop reply, log to S5, alert S13. |
| HARD STOP message | Operator input in DM | Cascade via S5 → all Hermeses; <50ms target. |
| Bot added to new guild unexpectedly | `on_guild_join` | S7 governance decides: allow (default for known operators) or auto-leave (unknown guild). |
| Privilege escalation attempt (bot asked to mod a server) | Slash command ACL | Reject + log; S7 governance audit. |

## §S2.8 Dependencies

- **Depends on:** S1 (process lifecycle), S3 (world model), S4 (private memory), S5 (event bus), S7 (governance grants), S12 (LLM gateway), Vault (token storage).
- **Depended on by:** S7 (governance actor identity), S13 (Discord-specific metrics: 429 count, message latency, command invocation rate), S15 (documentation of operator-facing surface).
- **External integration:** Discord API (gateway + REST), Vault, S3 (world model for context).

---

# S3: Shared World Model

## §S3.1 Purpose

S3 is the **shared cognition substrate** of the Society — the place where Hermeses agree on what is true, what is happening, and what intentions are active. It is implemented as a BDI (Belief-Desire-Intention) agent architecture operating over a blackboard pattern with namespace-ACL access control, with bi-temporal facts backed by an event-sourced update path (S5).

S3 exists because a Society of independent agents that cannot agree on basic facts is not a Society — it is a swarm with shared branding. The world model is the single source of truth for: society state (who is alive, what roles are filled, what is the current quorum), member registry (Hermes profiles, capabilities, last-heartbeat), and world facts (external events that all Hermeses should know about, e.g., "the VPS RAM is at 78%"). Critically, S3 is **deliberately impoverished about anything private**: no relationship state, no intimacy markers, no per-Hermes emotional state. Those live in S4.

S3 is also the **shared coordination point** for cross-Hermes workflows: if Pharsa needs to ask Guinevere a question, the request flows through S3's blackboard, not via direct Discord DM (which would be S2-to-S2 and bypass the world model).

## §S3.2 Components

1. **BDI store (3 tables in `public.world_model` schema)**
   - `beliefs`: rows are facts the society holds true, with provenance and bi-temporal validity (`valid_from`, `valid_to`, `recorded_at`).
   - `desires`: rows are goals under consideration; each has a priority, owner(s), and lifecycle state (`proposed`, `accepted`, `rejected`, `achieved`, `abandoned`).
   - `intentions`: rows are committed plans in execution; each links to a `desire_id`, an `owner_hermes_id`, and a state machine (`pending`, `active`, `blocked`, `completed`, `failed`).
2. **POMDP framing layer** — each Hermes maintains an in-process POMDP belief state (the LLM context window acts as the observation buffer); on each significant event, the Hermes updates its private POMDP belief and re-queries S3 for the world-model subset relevant to current intention. S3 does not store per-Hermes POMDP state — that is private to the agent's in-process memory.
3. **Blackboard pattern with namespace-ACL**
   - Namespaces correspond to domain minds: `society/`, `governance/`, `finance/`, `comms/`, `vps/`, `world/`, `persona/`, `safety/`, `audit/`.
   - Each namespace has an ACL: which Hermes roles can `READ`, which can `WRITE`, which can `READ_WRITE`.
   - Default: every Hermes can READ `world/`; only Guinevere + Pharsa can WRITE `governance/`; only Hermes with `finance` capability can READ `finance/`; only safety-tier Hermeses can READ `safety/`.
4. **Materialized views (CQRS read models)**
   - `mv_active_hermeses`: current alive Hermeses + their roles + last-heartbeat.
   - `mv_open_intentions`: intentions in `active` or `blocked` state.
   - `mv_recent_world_events`: last 100 world facts.
   - Views are updated in the same transaction as the underlying `domain_events` write (single-DB CQRS pattern, per research synthesis §5.1).
5. **Conflict resolution policy**
   - `last_write_wins` (lossy) for `beliefs` where losing data is acceptable (e.g., "current weather in Jakarta").
   - `optimistic locking / version_check` (rejects stale writes) for `intentions` and `desires` where silent overwrite would corrupt coordination.
   - `quorum_required` (k-of-n sign-off via S7) for `governance/` and `safety/` namespaces.
6. **Reflection loop (Generative Agents pattern, Stanford 2023)** — every N minutes (default 30), each Hermes runs a reflection cycle: query recent `beliefs` + `intentions`, generate higher-level abstractions, write back to `beliefs` as new derived facts. Cadence is per-Hermes config; expensive Hermeses may run less often.
7. **World model update bus** — S3 is event-driven: it subscribes to S5 `domain_events` stream and projects events into the BDI store. No direct LLM write path; all updates go through S5's append-only log.
8. **Plan generator (Generative Agents pattern)** — when a new `desire` is accepted, the owner Hermes generates a plan (sequence of `intentions`), stored in S3 with each intention linked to the next via `next_intention_id`. Other Hermeses can READ the plan but only the owner can mutate it.

## §S3.3 Data Flow

**Belief write (event-driven):**
1. Something happens: an external event (`vps.memory.high`), an agent action (`agent_action.tool_called`), or a governance decision (`governance.hermes_promoted`).
2. The event is published to S5 `domain_events` (append-only).
3. S3's outbox-projector consumes the event from S5.
4. S3 applies the projection rule (per event type): for `vps.memory.high`, insert/update `beliefs` row `(subject: "vps.memory.utilization", value: "78%", source: "prometheus", valid_from: now)`.
5. Materialized views update in same transaction.
6. Other Hermeses subscribed to `world/*` receive notification (via S5 Redis Pub/Sub fan-out) and can re-query S3.

**Belief read:**
1. Hermes needs context for a decision → calls `s3.query(namespace_pattern, filters)`.
2. S3 checks the calling Hermes's namespace-ACL (via S7 capability lookup).
3. If allowed, S3 reads from materialized view (fast path) or joins to base tables (slow path).
4. Returns `BeliefSet` with provenance metadata (who wrote, when, what evidence).

**Intention creation (cross-Hermes coordination):**
1. Guinevere decides to delegate a code review task to Pharsa.
2. Guinevere writes `desire`: `{type: "code_review", priority: 0.7, target: "PR-1234"}`.
3. S7 governance checks: is Guinevere allowed to delegate to Pharsa? (Yes, founder capability.)
4. Desire state → `accepted`.
5. Pharsa observes the new desire (via S5 subscription on `governance/*` + `intentions/*`).
6. Pharsa writes `intention`: `{desire_id: <X>, owner: "pharsa", state: "active", plan: [...]}`.
7. Pharsa updates intention state as it executes; S3 logs every transition to S5.

**Reflection cycle:**
1. Every 30 min (per Hermes config), the Hermes actor runs `reflect()`.
2. Reads last 100 `beliefs` + last 50 `intentions` for itself.
3. LLM call: "What higher-level patterns do you observe?"
4. Writes new derived `beliefs` with `provenance: reflection_cycle`.
5. Emits `agent_action.reflection_completed` to S5.

## §S3.4 Interfaces

- **`S3 → S5`:** `subscribe(projection_id, patterns) → EventStream`; S3 is a consumer of S5, not a producer (except for derived belief writes, which go through S5 first).
- **`S3 → S7`:** `check_capability(hermes_id, namespace, op) → CapabilityDecision`; S7 is the source of truth for ACL.
- **`S3 → S2`:** `query_relevant_beliefs(context_id, scope) → BeliefSet`; called by S2 on each message receive.
- **`S3 → S4`:** (read-only coordination) `cross_reference_private_fact(hermes_id, fact_id, reason) → PublicProjection | DeniedReason`; only if S7 explicitly allows; default DENY.
- **`S3 → operator`:** `/hermes world model show <namespace>` (read-only), `/hermes world model history <belief_id>` (audit trail).

## §S3.5 Technology Choices

| Choice | Rationale |
|---|---|
| **PostgreSQL `public.world_model` schema** | Single-DB CQRS; same engine as S4 and S5; transactions span event + projection; pgvector lives here too. |
| **JSONB for belief payloads** | Flexible schema; can evolve without migrations; GIN index for fast namespace-prefix queries. |
| **Materialized views (PG native)** | Built-in; auto-refresh in same transaction; no extra infra. |
| **Bi-temporal fields (`valid_from`, `valid_to`, `recorded_at`)** | Research synthesis §5.4 calls for Graphiti-style bi-temporal; S3 implements the lightweight version natively in PG; full Graphiti is reserved for S6 (relationship graph) per pilot scope decision. |
| **Reflection cadence: sleep-time compute (Letta pattern)** | Research synthesis §8.2 default; cheaper than sync; heartbeat is already in place. |
| **Namespace-ACL table in `public.world_model.acl`** | Small, fast, joins cheaply; populated by S7 governance actions. |

## §S3.6 Security Considerations

- **Default-deny on cross-namespace reads.** A Hermes requesting `finance/*` without the `finance` capability gets `CapabilityDenied`. No implicit "founder can read everything" — even founders are checked.
- **Intimate data MUST NOT enter S3.** This is a hard invariant. LLM prompts that generate world-model updates are explicitly forbidden from including: relationship memory content, intimacy/passion/commitment markers, EWMA bond vectors, DM content. S3 has no schema columns for any of these; the absence is structural enforcement.
- **Provenance is mandatory.** Every `beliefs` row has `source_hermes_id` + `source_event_id`. If a belief turns out to be wrong, we can trace it back to the event and the Hermes that recorded it.
- **Reflection cycle is a potential drift vector.** A Hermes that reflects on biased inputs may produce biased derived beliefs. Mitigation: derived beliefs are tagged `provenance: reflection_cycle`; S7 governance periodically audits reflection outputs for drift; S13 metrics track belief-stability over time.
- **Quorum-required namespaces (`governance/`, `safety/`) are doubly protected.** Even with `WRITE` capability, a write must include a `governance_decision_id` referencing a passed S7 vote.

## §S3.7 Failure Modes & Recovery

| Failure mode | Detection | Recovery |
|---|---|---|
| S3 projector lag (events not yet applied) | S5 lag metric > 10s | Alert S13; projector backfill from event log. |
| Materialized view corruption | S3 health check fails | Rebuild view from base tables (`REFRESH MATERIALIZED VIEW CONCURRENTLY`). |
| Namespace-ACL misconfiguration (Hermes gets wrong perms) | S7 governance audit | Revoke via S7; broadcast invalidation to all subscribers. |
| Reflection cycle produces infinite derived beliefs | Belief count growth > 10/min | Hard cap: reflection produces ≤5 new beliefs/cycle; alert S13. |
| Bi-temporal inconsistency (valid_from in future) | Schema constraint | Reject write; alert S13; investigate clock skew (NTP check). |
| Cross-Hermes intention conflict (two Hermeses claim same intention) | Optimistic lock failure | Second writer gets `VersionConflict`; resolves by re-reading + retry OR escalating to S7. |
| S3 database corruption | PG `pg_stat_database` shows anomalies | Restore from S3 backup (S11); replay event log; verify bi-temporal consistency. |

## §S3.8 Dependencies

- **Depends on:** S5 (event store; S3 cannot exist without S5), S7 (governance ACL source), S1 (each Hermes process queries S3), S11 (backup of `public.world_model` schema).
- **Depended on by:** S2 (every Hermes reads S3 for context), S6 (vector+graph recall lives alongside S3 schema), S8 (self-evolution mutates S3 namespaces), S13 (S3 health metrics).
- **External integration:** PostgreSQL (primary), S5 (event bus), S7 (governance).

---

# S4: Private Memory Layer

## §S4.1 Purpose

S4 is each Hermes's **encrypted private cognition space** — the place where relationship state, intimacy markers, private reflections, and per-Hermes episodic memory live, completely isolated from the shared world model. S4 is the architectural embodiment of PersonaSafetyPolicy's "intimacy is runtime-only" rule and the P20 Living Autonomy Kernel's per-agent isolation contract.

S4 exists because (a) the AGENTS.md BLOCKING rules forbid plaintext intimate data in shared artifacts; (b) the Edge & Node 2026 incident pattern (and countless 2025-2026 agent failures) shows that shared memory bleeds intimate content; (c) the Layered Mutability paper (arXiv 2604.14717) shows drift is driven by memory accumulation — and the only safe place for that accumulation is per-agent, encrypted, with the key held by the agent.

**Hard invariant:** the **owning Hermes is the only principal that can read its private memory.** Not the founder. Not the operator. Not another Hermes. Not a DBA. The DEK is held in Vault under an ACL that grants decrypt only to the Hermes process identity (via Vault token-bound secrets). Backups are encrypted client-side before transit; S3 stores ciphertext.

## §S4.2 Components

1. **Per-agent PostgreSQL schema (`agent_<hermes_id>`)** — one schema per Hermes; e.g., `agent_guinevere`, `agent_pharsa`, `agent_<future>`. Cross-schema reads denied by default at the PostgreSQL role level (RLS policy).
2. **pgcrypto columns for intimate data** — tables in the per-agent schema that hold intimacy/passion/commitment markers, relationship state vectors, DM content, and personal reflections are encrypted with `pgcrypto`'s `pgp_sym_encrypt` using the agent's DEK. The DEK never appears in plaintext in PG.
3. **Per-agent DEK (Data Encryption Key) in Vault** — each Hermes has a 256-bit AES DEK stored at `secret/hermes/<name>/memory_dek` in Vault. Access requires the Hermes's Vault token, which is bound to the process PID via Vault token-bound secrets (no shared token across processes).
4. **Three memory tiers**
   - **Working memory (hot):** in-process Python dict; ephemeral; lost on process restart. Used for the current LLM context buffer.
   - **Episodic memory (warm):** per-agent PG schema; time-ordered log of events the Hermes chose to remember. Retention: 90 days hot, then consolidated.
   - **Long-term memory (cold):** per-agent PG schema, consolidated episodic + semantic facts. Retention: indefinite; subject to decay.
5. **Memory lifecycle worker (per-Hermes, sleep-time compute)**
   - **Creation:** every notable event the Hermes observes may be written to episodic memory (Hermes decides via LLM-judge with explicit threshold).
   - **Consolidation:** nightly, the worker scans recent episodic entries, deduplicates, extracts semantic facts, writes to long-term.
   - **Decay:** long-term entries have an EWMA importance score; entries below threshold for 180 days are archived to S3 (still encrypted) and removed from hot PG.
   - **Archival:** cold entries go to S3 with same DEK; S3 stores ciphertext only.
6. **Relationship event schema** — `relationship_events` table: `(id, subject_id, type, marker, intimacy_delta, passion_delta, commitment_delta, occurred_at, source_event_id)`. Marker is LLM-extracted (e.g., "vulnerability_shown", "boundary_respected", "trust_built"). Dimensions map to Triangular Theory of Love (intimacy/passion/commitment) and Attachment Theory (secure/anxious/avoidant/disorganized).
7. **EWMA bond vectors** — per-subject EWMA (exponentially weighted moving average) over intimacy/passion/commitment markers, with λ≈0.3 (per research synthesis §5.4). Stored encrypted.
8. **Memory access control (RLS policy)** — every table in `agent_*` schema has RLS policy: `USING (current_setting('hermes.agent_id') = '<this_schema>')`. The `current_setting` is set by the Hermes's connection pool at session start.
9. **No automatic publication to S3.** This is a component that **does not exist**: there is no worker, no scheduled job, no LLM-extracted summarizer that pushes S4 content to S3. Cross-agent sharing requires explicit operator action via S7.

## §S4.3 Data Flow

**Memory write (episodic):**
1. Hermes decides to remember something (LLM-judge or operator `/hermes remember <text>`).
2. Hermes process opens a connection to PG with `SET hermes.agent_id = 'guinevere'`.
3. Hermes writes to `agent_guinevere.episodic_memory` table (not encrypted at this tier — episodic events are not intimate by default).
4. If the event is a relationship marker (intimacy/passion/commitment), the Hermes additionally writes an encrypted row to `agent_guinevere.relationship_events` using `pgp_sym_encert(marker, dek)`.
5. S4 emits `memory_op.episode_written` to S5 (event metadata only — no payload, no marker content).

**Memory read (recall):**
1. S2 receives a message; S2 calls `s4.recall(query, k=10)`.
2. S4 generates embedding (via S6 vector layer) for the query.
3. S4 queries `agent_guinevere.episodic_memory` by embedding similarity + recency.
4. S4 returns top-k episodes with metadata.
5. For relationship queries (`s4.recall_relationship(subject_id)`), S4 reads encrypted rows, decrypts with DEK in process memory, returns plaintext only within the calling process.

**Memory consolidation (nightly):**
1. Cron-like scheduler (S1 heartbeat watchdog extension) triggers consolidation.
2. Worker reads last 24h of episodic memory.
3. LLM call: "Consolidate these episodes into semantic facts. Deduplicate. Extract patterns."
4. Worker writes consolidated facts to `agent_<id>.long_term_memory`.
5. Episodic entries older than 90 days are moved to cold storage (S3 ciphertext) and deleted from hot PG.

**Memory decay (weekly):**
1. Worker scans long-term memory EWMA scores.
2. Entries below threshold for 180 days: encrypted archive to S3, removed from PG.
3. S5 emits `memory_op.entry_archived` (metadata only).

**Cross-agent read (rare, explicit):**
1. Operator runs `/hermes guinevere share <memory_id> with pharsa` in Discord.
2. S7 governance check: does this cross-agent share require founder approval? (Default: yes for any intimate content.)
3. If approved, S4 reads encrypted row, re-encrypts under Pharsa's DEK, writes to `agent_pharsa.shared_inbox`.
4. Pharsa reads on next tick; original entry in Guinevere's schema remains (Guinevere still has the memory).
5. S5 emits `memory_op.cross_agent_share` audit event (full provenance, no content).

## §S4.4 Interfaces

- **`S4 → S2`:** `recall_episodic(query, k=10) → Episode[]`; `recall_relationship(subject_id) → RelationshipState` (private, encrypted, returned only to caller).
- **`S4 → S3`:** (deliberately minimal) `get_summary_fingerprint(hermes_id) → Hash` — lets S3 know "Hermes X has private memory about subject Y" without revealing content; used for coordination ("Guinevere and Pharsa both have memory about this user" — useful for handoff, no intimacy leaked).
- **`S4 → S5`:** `publish(event_type, payload_metadata)` — emits audit events with NO intimate payload.
- **`S4 → S6`:** (vector embeddings) `embed_episode(text) → Vector`; S6 holds the embedding index per Hermes.
- **`S4 ← S7 governance`:** `grant_temporary_access(from_hermes, to_hermes, scope, duration) → CapabilityGrant` — for explicit cross-agent sharing.
- **`S4 → operator`:** `/hermes memory show recent [N]` (Hermes's own memory, never another Hermes's), `/hermes memory forget <id>` (operator-forced deletion, audited).

## §S4.5 Technology Choices

| Choice | Rationale |
|---|---|
| **PostgreSQL per-agent schema** | Per research synthesis §4.4; canonical 2026 pattern; pgcrypto integrates natively. |
| **pgcrypto (`pgp_sym_encrypt`)** | Built-in; no external KMS required for column-level encryption; key material stays in PG session. |
| **Vault for DEK storage** | Industry standard; token-bound secrets prevent token sharing; audit log per decrypt. |
| **Per-Hermes connection pool with `SET hermes.agent_id`** | Lightweight; leverages PG's session settings; RLS policy reads the setting. |
| **Embedding model via S6** | Out of scope for S4 design; S4 calls S6 for `embed(text) → Vector`. |
| **S3 with SSE-KMS for cold archive** | Per research synthesis §4.11; COMPLIANCE mode for ledger, GOVERNANCE mode for memory archive. |
| **EWMA implementation in PostgreSQL (window functions)** | `exp_weighted_avg(marker, occurred_at, λ=0.3)` as a SQL function; no app-layer state. |

## §S4.6 Security Considerations

- **DEK never leaves Vault unencrypted.** The Hermes process fetches the DEK at boot, holds it in process memory (cleared on shutdown), uses it for `pgp_sym_encrypt/decrypt`. The DEK is never written to disk, never logged, never passed across the network except inside the Vault response.
- **Vault token-binding to process PID.** Vault's token-bound secrets feature ties the token to a specific process; if the process dies, the token is invalid. This means even an attacker who steals the token cannot use it from a different process.
- **RLS policy is the last line of defense.** Even if a SQL injection or misconfigured connection leaks through, the RLS policy `USING (current_setting('hermes.agent_id') = '<schema>')` blocks cross-schema reads.
- **Backup encryption is client-side.** Before data leaves PG for S3, it is re-encrypted with the Hermes's DEK (or a separate archive KEK). S3 stores ciphertext only; S3 admins cannot read it.
- **Operator CANNOT directly read another Hermes's memory.** This is a hard invariant. The operator can: (a) read their own Hermes's memory; (b) request cross-agent sharing via S7 (audited); (c) emergency-wipe a Hermes's memory (founder-tier, audited, irreversible). The operator cannot: (d) silently browse; (e) read intimacy markers; (f) bypass DEK.
- **Memory writes are append-mostly.** Hard delete is rare; soft delete with `deleted_at` is the norm; physical deletion only via decay OR operator emergency-wipe (both audited).
- **Cross-agent summary is forbidden in the LLM prompt.** The prompt for S4 recall explicitly does NOT include the prompt "and summarize for sharing with peer Hermeses." S4's summary fingerprint exposed to S3 is the maximum leakage.

## §S4.7 Failure Modes & Recovery

| Failure mode | Detection | Recovery |
|---|---|---|
| DEK lost (Vault unavailable) | Hermes process cannot decrypt; bootstrap fails | Refuse to start; alert S13; require operator Vault unseal or DEK re-issue. |
| Schema corruption (PG crash) | S4 health check | Restore from S3 ciphertext backup; replay from event log if available. |
| Memory leak (unbounded growth) | S4 size metric > 10GB | Trigger early decay; alert S13. |
| Wrong schema access (RLS bypass bug) | S13 audit log anomaly | Emergency DB role lockdown; investigate CVE; potentially roll back PG. |
| Vault token compromise | Vault audit log | Revoke token; re-issue with new PID binding; force Hermes restart. |
| S3 archive corruption | S3 inventory check | Re-archive from hot PG if available; otherwise mark as lost (catastrophic). |
| Consolidation worker runaway (LLM cost spike) | USD budget guardrail | Kill worker; alert S13; manual review of last consolidation output. |
| Cross-agent share bypass (governance vote skipped) | S5 audit event sequence check | Reject write; alert S7; investigate. |

## §S4.8 Dependencies

- **Depends on:** S1 (process identity for Vault token binding), S5 (event audit), S6 (embedding model), S7 (governance for cross-agent share), S11 (S3 backup target), Vault (DEK storage).
- **Depended on by:** S2 (recall queries on every message), S6 (embeddings live alongside episodic entries), S13 (memory size / recall latency metrics), S8 (self-evolution Tier 3 modifications touch S4 schema).
- **External integration:** PostgreSQL + pgcrypto, Vault, S3 (SSE-KMS + client-side encryption), S6 (embedding model).

---

# S5: Event Store & CQRS Bus

## §S5.1 Purpose

S5 is the **nervous system of the Society** — the append-only event log that records every significant thing that happens, plus the dual bus (PostgreSQL outbox + Redis) that fans events out to consumers in real-time. S5 is the architectural embodiment of "the event log is the source of truth" and the single-DB CQRS pattern that research synthesis §4.5 and §5.1 identify as the canonical 2026 approach for sub-50k events/sec.

S5 exists because (a) without an append-only log, debugging multi-agent coordination is folklore; (b) the HARD STOP cascade (D-07) requires <50ms cross-instance propagation, achievable only via Redis Pub/Sub, not polling; (c) the Society needs replay capability for audit and for new Hermeses to reconstruct state; (d) the bi-temporal world model in S3 needs an event log to project from; (e) the S3 backup (S11) is meaningful only if there is an event log to back up.

**S5 is intentionally NOT Kafka.** At the target scale (≤32 Hermeses, each producing ≤10 events/sec under steady load, ≤1k events/sec peak), PostgreSQL outbox + LISTEN/NOTIFY + Redis Streams comfortably handles the load. Kafka wins only above 50k events/sec sustained (research synthesis §1 finding 8).

## §S5.2 Components

1. **`event_store.domain_events` table (append-only WORM)**
   - `event_id` UUID primary key.
   - `aggregate_type` (e.g., `hermes`, `intention`, `wallet`, `memory`).
   - `aggregate_id` UUID.
   - `event_type` (e.g., `hermes.spawned`, `intention.created`, `wallet.transaction_posted`).
   - `event_version` BIGINT (per-aggregate sequence, monotonically increasing).
   - `payload` JSONB.
   - `metadata` JSONB (provenance: producer, request_id, ip, etc.).
   - `occurred_at` TIMESTAMPTZ.
   - `recorded_at` TIMESTAMPTZ (defaults to `now()`).
   - `consent_ref` UUID (FK to consent ledger; **nullable at the database layer per ADR-066** — Hermes runtime events may have NULL `consent_ref`; application layer enforces NOT NULL for `event_source = 'dev_workflow'` events only; see security note §S5.6).
   - `hash_prev` BYTEA (previous event's hash for hash chain).
   - `hash_self` BYTEA (SHA-256 of canonicalized event including `hash_prev`).
   - **UNIQUE(`aggregate_id`, `event_version`)** for optimistic concurrency.
2. **Outbox table (`event_store.outbox`)** — same schema as `domain_events` plus a `relayed_at` column. Producers write to outbox in the same transaction as the state change; a relay worker reads outbox, publishes to Redis Streams / Pub/Sub, marks `relayed_at`.
3. **Outbox relay worker (1+ per VPS)**
   - Uses `FOR UPDATE SKIP LOCKED` to claim outbox rows without blocking.
   - Publishes to Redis Streams (durable) or Redis Pub/Sub (ephemeral) based on event type.
   - Marks `relayed_at` after successful publish.
   - Retries on failure with exponential backoff; alert S13 if lag > 10s.
4. **Redis (two-store split)**
   - **DB 0: Pub/Sub** for ephemeral coordination (agent status, presence, HARD STOP cascade, "I started/finished"). At-most-once; intentional loss acceptable.
   - **DB 1: Streams** with consumer groups for durable work (task distribution, world model projection, S3 backup writes). At-least-once; replay from any ID.
5. **`event_store.snapshots` table** — periodic snapshots of aggregate state (e.g., `hermes` aggregate, `wallet` aggregate) for fast replay. Snapshot every 1000 events per aggregate.
6. **HARD STOP cascade mechanism**
   - Redis key `hermes:society:{society_id}:hard_stop` set to `1` with TTL=300s.
   - All Hermes processes subscribe to keyspace notifications.
   - On receive, S1 supervisor triggers graceful drain.
   - Target propagation: <50ms (per D-07).
7. **Hash chain (WORM enforcement)** — each event's `hash_self` includes the previous event's `hash_self`. A reorg attempt (delete or modify past event) breaks the chain and is detectable by S13 audit verification.
8. **Event type catalog** — versioned enum of event types per domain:
   - `society.*`: `society.hermes.spawned`, `society.hermes.shutdown`, `society.hard_stop`, `society.member_added`, `society.member_removed`.
   - `agent_action.*`: `agent_action.message_received`, `agent_action.message_sent`, `agent_action.tool_called`, `agent_action.command_invoked`, `agent_action.reflection_completed`.
   - `governance.*`: `governance.vote_proposed`, `governance.vote_cast`, `governance.decision_made`, `governance.hermes_promoted`, `governance.hermes_demoted`.
   - `financial.*`: `financial.transaction_posted`, `financial.balance_updated`, `financial.policy_changed`, `financial.circuit_breaker_triggered`.
   - `memory.*`: `memory_op.episode_written`, `memory_op.entry_archived`, `memory_op.cross_agent_share`, `memory_op.consolidation_run`.
9. **Replay tool (`hermes_eventstore_replay`)** — CLI for replaying events into a target system (e.g., rebuild S3 world model from scratch, populate a new Hermes's bootstrap snapshot).
10. **CQRS read model builders (materialized views)** — each read model is a SQL view or table updated by triggers on `domain_events` insert. Single-DB CQRS pattern.

## §S5.3 Data Flow

**Event write (synchronous path):**
1. Producer (any subsystem) starts PG transaction.
2. Producer performs state change (e.g., S4 writes episodic memory).
3. In same transaction, producer inserts row into `event_store.outbox` with `event_*` fields.
4. Transaction commits.
5. Outbox relay worker (in separate process / coroutine) sees new outbox row via `LISTEN/NOTIFY` on `outbox_inserted` channel.
6. Worker claims the row via `SELECT ... FOR UPDATE SKIP LOCKED`.
7. Worker inserts into `event_store.domain_events` (or the outbox IS the domain_events table; design choice: outbox = transient, domain_events = permanent).
8. Worker computes `hash_self = SHA256(canonicalize(event || hash_prev))`.
9. Worker publishes to Redis: Streams for durable types, Pub/Sub for ephemeral types.
10. Worker marks `relayed_at = now()` in outbox; commits claim transaction.
11. Subscribers (S3 projector, S6 vector indexer, S13 audit, etc.) receive via Redis.

**Event subscribe (real-time):**
1. Consumer (e.g., S3 world model projector) subscribes to a Redis Stream consumer group: `XREADGROUP GROUP s3-projector BLOCK 5000 STREAMS s5:domain_events >`.
2. On event arrival, consumer projects to its target (e.g., S3 belief table).
3. Consumer ACKs via `XACK` after successful projection.
4. Failed projection: retry with backoff; after N failures, dead-letter stream `s5:dlq`.

**HARD STOP cascade:**
1. Operator types `HARD STOP` in any Hermes DM.
2. That Hermes's S2 receives, calls S5 to publish `society.hard_stop` event.
3. S5 writes to `domain_events` (audit trail).
4. S5 sets Redis key `hermes:society:{id}:hard_stop = 1` (TTL 300s).
5. All other Hermeses' S1 supervisors receive keyspace notification.
6. S1 triggers graceful shutdown.
7. Target: <50ms from key set to all S1 receives.

**Replay (debugging / new Hermes bootstrap):**
1. Operator runs `hermes_eventstore_replay --from=<event_id> --to=<event_id> --target=<system>`.
2. Tool reads events from `domain_events` in order.
3. Tool projects to target (e.g., S3 world model, S6 vector index).
4. Tool emits progress to S5; idempotent (uses event_id as natural key).

## §S5.4 Interfaces

- **`S5 → all subsystems`:** `publish(event_type, payload, metadata, consent_ref) → EventID`; `subscribe(consumer_group, patterns) → EventStream`.
- **`S5 → S1`:** HARD STOP keyspace notification; supervisor receives and drains.
- **`S5 → S11`:** bulk export of `domain_events` to S3 Object Lock COMPLIANCE bucket (nightly).
- **`S5 → S13`:** Prometheus exporter for `event_store.outbox.lag_seconds`, `event_store.relay.publish_rate`, `event_store.hash_chain.last_verified_at`, `redis.streams.consumer_lag`.
- **`S5 → operator`:** `hermes_eventstore_query --type=<pattern> --from=<ts> --to=<ts>` (read-only audit query), `hermes_eventstore_replay` (replay tool).
- **`S5 → S7 governance`:** `verify_governance_decision_provenance(decision_id) → ProvenanceProof`; S5 is the audit log for every governance decision.

## §S5.5 Technology Choices

| Choice | Rationale |
|---|---|
| **PostgreSQL `event_store` schema with outbox + domain_events split** | Per research synthesis §4.5; single-DB CQRS; transactional consistency; pgcrypto for sensitive metadata fields. |
| **LISTEN/NOTIFY trigger on `outbox_inserted`** | Native PG; sub-millisecond relay latency; no external message bus for hot path. |
| **`FOR UPDATE SKIP LOCKED` for outbox claim** | 2026 standard pattern; multiple relay workers safely claim disjoint rows; no deadlocks. |
| **Redis 7.x (Pub/Sub + Streams)** | Battle-tested; native keyspace notifications for HARD STOP cascade; consumer groups for durable work. |
| **`redis-py` (async mode)** | Existing substrate; integrates with asyncio; cluster support when scaling to multi-VPS in P35+. |
| **SHA-256 hash chain (custom; no library)** | 50-line implementation; well-understood; `hashlib` in stdlib. |
| **Replay tool as CLI (`click` library)** | Operable by SRE/operator; idempotent; safe to re-run. |

## §S5.6 Security Considerations

- **WORM is enforced by hash chain + S3 COMPLIANCE backup.** A rogue DBA cannot rewrite history without breaking the hash chain; the S3 COMPLIANCE copy is the ultimate defense. Restoration from S3 verifies hash chain integrity before applying.
- **Consent reference is mandatory for dev-workflow personal events.** Events that touch personal data (DMs, relationship state, financial transactions) and originate from the **dev-workflow agent** (`event_source = 'dev_workflow'`) MUST include `consent_ref` linking to the consent ledger. **The `consent_ref` column is NULLABLE at the database layer per ADR-066** — the NOT NULL constraint is enforced only at the **application layer** via Pydantic boundary guards. Hermes runtime events (`event_source = 'hermes_runtime'`) may have NULL `consent_ref` (e.g., cross-agent system events, hash-chain anchors, throughput primitives where no consent ledger entry exists). This carve-out is architecturally required because the Hermes runtime does not maintain a 1:1 consent ledger mapping for every internal event.
- **Producers do NOT control `hash_chain`.** The relay worker computes `hash_self`; producers cannot pre-compute a chain. This prevents producer-side tampering.
- **Replay tool requires founder-tier capability.** Replaying events can re-create derived state in other systems; an attacker replaying could corrupt S3 world model or S6 vector index. Access controlled by S7 governance.
- **Outbox row is encrypted at rest for `metadata.consent_ref` and any personal data in `payload`.** pgcrypto column-level encryption for sensitive fields; non-sensitive event metadata (event_type, aggregate_id, occurred_at) is plaintext for query performance.
- **No payload introspection at the bus layer.** S5 routes events by `event_type` pattern only; it does not peek into `payload`. This keeps S5 honest — it cannot leak content even if compromised.

## §S5.7 Failure Modes & Recovery

| Failure mode | Detection | Recovery |
|---|---|---|
| Outbox relay lag > 10s | S13 metric | Alert SRE; check relay worker health; manual catch-up. |
| Redis Stream consumer group lag | `XINFO GROUPS` | Consumer backfill; if persistent, scale consumer. |
| Hash chain corruption detected | S13 audit job | STOP all writes; investigate; restore from S3 COMPLIANCE copy. |
| HARD STOP key not propagating | Manual test in canary | Check Redis keyspace notification config (`notify-keyspace-events Ex`); re-test cascade. |
| Event schema version mismatch | Producer / consumer handshake | Bump schema; dual-write during migration window. |
| S5 database corruption | PG crash | Restore from S3; verify hash chain; replay into S3 if needed. |
| Replay tool produces wrong state | Operator review | Replay is idempotent; re-run with corrected target. |
| Snapshot stale (aggregate diverged from events) | Snapshot vs event log comparison | Rebuild snapshot from event log. |
| Relay worker dies mid-publish | Outbox row `relayed_at IS NULL` | Next relay worker picks up; at-least-once semantics. |

## §S5.8 Dependencies

- **Depends on:** PostgreSQL (primary), Redis 7.x (Pub/Sub + Streams), S11 (S3 COMPLIANCE backup), S7 (governance for replay tool), S13 (metrics + audit job).
- **Depended on by:** ALL other subsystems (S1, S2, S3, S4, S6-S15) — every significant action publishes to S5.
- **External integration:** PostgreSQL LISTEN/NOTIFY, Redis Pub/Sub + Streams + keyspace notifications, S3 (bulk export).

---

# §6 Cross-Subsystem Integration Notes

The five subsystems S1-S5 form a tightly integrated foundation. The following integration notes document cross-cutting concerns that span multiple subsystems and that would be lost in per-subsystem isolation.

## §6.1 Spawn Sequence (Cross-Subsystem)

When a new Hermes spawns, the order matters:

1. **S1 (Runtime):** systemd starts `hermes@<name>.service`; launcher reads config; cgroup v2 limits applied; `READY=1` notification.
2. **S1 → Vault:** launcher fetches DEK reference + Discord token reference; resolves to plaintext in process memory.
3. **S1 → S4 (Memory):** `open_private_namespace(hermes_id, dek_ref)` creates connection pool with `SET hermes.agent_id`; verifies DEK works by decrypting a known canary value.
4. **S1 → S3 (World Model):** `register_hermes(hermes_id, role, scopes)`; S3 checks S7 for role + scopes; if accepted, writes `society.hermes.spawned` event to S5.
5. **S1 → S5 (Event Store):** outbox relay writes `society.hermes.spawned` to `domain_events`; hash chain advances; S3 projector applies.
6. **S1 → S2 (Discord):** `start_discord_client(token)`; S2 fetches token from Vault; constructs client; connects to gateway; emits `agent_action.bot_online` to S5.
7. **S1 → S5 subscription:** outbox relay subscribes Hermes to relevant event patterns based on role (e.g., `world/*`, `governance/*` if founder).
8. **Steady state:** heartbeat every 30s; ready for first message.

Failure at any step triggers rollback: S5 events unwound (S3 projector reverses if possible); S4 schema dropped if not yet used; S1 SIGTERM self; systemd marks service as `inactive (dead)`.

## §6.2 Per-Message Critical Path (Hot Path)

For every Discord message, the hot path is:

```
Discord gateway → S2 (receive) → S5 (publish message_received)
  → S2 → S3 (query relevant beliefs) ─┐
  → S2 → S4 (recall episodic)          ├→ S12 (LLM call) → S2 (reply) → S5 (publish message_sent)
  → S2 → S6 (embed for vector recall) ┘
```

Latency budget for hot path: <3s end-to-end (Discord rate limits assume <5s response). Breakdown:
- S2 message receive + S5 publish: <50ms
- S3 belief query: <100ms (materialized view)
- S4 recall (vector): <200ms (pgvector index)
- S6 embed: <300ms (local model)
- S12 LLM call: <2000ms (p50), <3500ms (p99)
- S2 reply + S5 publish: <50ms
- Buffer: <300ms

## §6.3 HARD STOP Cascade (Critical Safety Path)

HARD STOP is the highest-priority cross-subsystem flow:

1. **Detection:** S2 receives `HARD STOP` in any DM (or S7 governance emits it).
2. **Publication:** S5 receives `society.hard_stop` event; outbox relay writes to `domain_events` (audit); sets Redis key `hermes:society:{id}:hard_stop = 1` with 300s TTL.
3. **Cascade:** All other Hermeses' S1 supervisors receive Redis keyspace notification; S1 calls `sdnotify.notify(STOPPING=1)` and starts graceful drain.
4. **Drain:** S4 flushes pending writes; S2 closes Discord gateway; S5 emits `society.hermes.draining`; exit 0.
5. **Audit:** S5 has full audit trail of who triggered, when, from where.

Target latency: <50ms from Redis key set to all S1 receives (per D-07).

## §6.4 Boundary Invariants (Reaffirmed)

- **(I-1) Relationship memory never leaves the owning Hermes's S4 schema without explicit S7 governance approval.**
- **(I-2) Intimacy markers are runtime-only; documentation, dashboards, logs, and CI outputs are redacted.**
- **(I-3) S3 has no schema columns for intimate data; structural enforcement.**
- **(I-4) S5 audit events for `memory_op.*` carry metadata only, never intimate payload.**
- **(I-5) S2 logs Discord `user_id` and channel `id`; never logs DM content.**
- **(I-6) Cross-agent sharing requires S7 vote + S4 re-encryption under recipient DEK.**
- **(I-7) Operator cannot directly read another Hermes's S4 memory; only their own.**
- **(I-8) P28 minimum target does NOT require P24 fork (per ADR-054 + 11 aligned repo sources).**

---

# §7 Footer

## §7.1 File Provenance

This architecture design is derived from:
- `docs/setup-evidence/P28-P36-masterplan/research/research-synthesis.md` (690 lines, Phase 2 final)
- `docs/setup-evidence/P28-P36-masterplan/research/synthesis-repo-state.md` (760 lines)
- `docs/setup-evidence/P28-P36-masterplan/research/synthesis-external-architecture.md` (438 lines)
- `docs/setup-evidence/P28-P36-masterplan/research/synthesis-external-operations.md` (438 lines)

Total input volume: ~2,326 lines of research synthesis. Methodology: read each in full, cross-reference design inputs, document boundaries explicitly, do not re-decide P27's 10 locked decisions, do not design S6-S15 (out of scope).

## §7.2 Out of Scope (S6-S15) — Handoff Notes

S6-S15 are designed by parallel sub-agents. Handoff notes for those sub-agents:

- **S6 (Vector & Graph Recall):** S3 §S3.2 calls out `pgvector` and `materialized views`; S6 lives alongside S3 schema. S4 §S4.5 calls out S6 for embeddings.
- **S7 (Society Governance):** S3 §S3.4 + S4 §S4.4 + S5 §S5.4 all reference S7 as the ACL/capability source. S2 §S2.4 references S7 for per-Hermes capability grants.
- **S8 (Self-Evolution):** S3 §S3.6 + S4 §S4.8 reference S8 for Tier 3 modifications (persona, memory schema).
- **S9 (Autonomous Wallet):** S5 §S5.2 event catalog includes `financial.*`; S5 is the audit ledger for wallet.
- **S10 (Revenue):** S5 + S9 are the substrate; S10 is policy + discovery.
- **S11 (S3 Backup):** S5 §S5.6 + S4 §S4.5 + S3 §S3.7 all reference S11 as backup target.
- **S12 (Model Pool):** S1 §S1.3 + S2 §S2.5 reference S12 for LLM calls.
- **S13 (Observability):** All subsystems reference S13 for metrics; S5 §S5.4 lists S13 metric catalog.
- **S14 (Deployment):** S1 §S1.5 + S1 §S1.7 reference S14 for systemd unit deployment + cgroup management.
- **S15 (Documentation):** S2 §S2.8 + S5 §S5.8 reference S15 for doc surface.

## §7.3 Re-Decision Prevention

Per `research-synthesis.md` §9.2, this design does NOT re-decide:
- P27's 10 architectural decisions (D-01..D-10) — all locked.
- 7 Locked Decisions from P27 Final Report §3 + ADR-054.
- 20 hard rejection criteria (all PASS).
- 15 subsystem list in `research-synthesis.md` §4 (research-backed, designed here for S1-S5).
- 4 critical resolution recommendations in `research-synthesis.md` §3 (P24, P22.2, ADR-055, stub dir).

## §7.4 Open Questions Deferred to Phase 4

The following questions affect S1-S5 implementation but are deferred to Phase 4 (Full Doc Suite: SRS, FSD, TDD):

1. **Quorum size (S7):** 3-of-5 first, 5-of-9 by P34 — affects S3 §S3.6 quorum_required write logic.
2. **Snapshot interval (S5):** default 1000 events per aggregate; final value TBD in TDD.
3. **HARD STOP keyspace notification config:** `notify-keyspace-events Ex` vs `KEA` — TBD in operational runbook.
4. **Per-Hermes Vault token TTL:** 1h vs 24h vs process-lifetime — TBD in security runbook.
5. **Embedding model choice (S6 dependency):** local Ollama vs 9Router — TBD; affects S4 §S4.5 hot path latency.

## §7.5 Versioning

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere (parent agent) | Initial Phase 3 architecture design for subsystems S1, S2, S3, S4, S5. Five sections (one per subsystem) with eight subsections each (Purpose, Components, Data Flow, Interfaces, Technology Choices, Security, Failure Modes, Dependencies). Cross-subsystem integration notes (spawn, hot path, HARD STOP, boundary invariants). Handoff notes for S6-S15 sub-agents. |

## §7.6 Operator Sign-Off

Pending Faiz review + Phase 3 acceptance. This architecture is a planning artifact, not a decision. S1-S5 design contracts are ready to bind to SRS (§2.5), FSD (§2.13), and TDD (§2.14) in Phase 4 (Full Doc Suite). Implementation waves begin Phase 5+.

## §7.7 Maintenance Rules

Update only when:
- Faiz clarifies a Phase 3 decision point (P22.2, P24, A-corp timing, founder tie-breaking) → recycle affected subsystem section.
- S6-S15 designs reveal cross-subsystem conflicts → append to §6 Cross-Subsystem Integration Notes.
- HARD STOP latency budget changes → update S5 §S5.7 + §6.3.
- Discord ToS changes → update S2 §S2.5 + §S2.6.
- Phase 4 (SRS/FSD/TDD) reveals new requirements → append as ADRs.
