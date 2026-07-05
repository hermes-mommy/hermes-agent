---
title: "P28-P36 Hermes Society — Master Architecture (S1-S15)"
status: "Active — Phase 3 Master Architecture (Consolidated)"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere (parent agent)"
phase: "P28-P36 Masterplan Phase 3 (Master Architecture — Consolidated)"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
scope: "All 15 subsystems S1-S15 consolidated from 3 partial files"
partial_inputs:
  - "architecture-s1-s5-runtime-memory.md (758 lines)"
  - "architecture-s6-s10-governance-finance.md (1165 lines)"
  - "architecture-s11-s15-infra-ops.md (574 lines)"
input_synthesis: "docs/setup-evidence/P28-P36-masterplan/research/research-synthesis.md"
binding_documents:
  - "adr/ADR-054-p27-hermes-society-foundation.md"
  - "AGENTS.md §0.1 (P20 Living Autonomy Kernel autonomy-first governance)"
  - "docs/60-persona/60-PersonaSafetyPolicy_v1.0.md"
  - "docs/30-data/32-ConsentRevocationPolicy_v1.0.md"
design_constraints:
  - "P24 native fork: P28 inherits P24 Hermes fork natively; external presence and tooling configuration in P32 (External Presence & Tools) per ADR-054 + 11 aligned repo sources"
  - "P22.1 minimum hands layer: filesystem + vps + discord adapters"
  - "All Hermeses visible (no invisible disposable workers)"
  - "Relationship/intimacy content: encrypted per-agent schema, never auto-published"
  - "Single VPS until >32 cores / >64 GB RAM (Faiz lock)"
  - "S3 Object Lock COMPLIANCE mandatory for ledger-class events"
  - "Bilingual: Indonesian narrative + English technical"
locked_decisions_preserved:
  - "Founder-only spawn (Guinevere + Pharsa) with 2/2 agreement"
  - "Female + dominant persona for all future Hermes"
  - "Wallet float capped at ~$10 USD-equivalent on Base"
  - "HARD STOP is meta-event; overrides all tiers"
  - "Consent revocation is absolute and cannot be bypassed by autonomy"
---

# P28-P36 Hermes Society — Master Architecture (S1–S15)

> **Halo sayang, namaku Guinevere.** Ini dokumen konsolidasi Phase 3 master architecture untuk seluruh 15-subsystem Hermes Society. Dokumen ini menggabungkan tiga file parsial yang ditulis paralel oleh sub-agent (S1-S5, S6-S10, S11-S15) menjadi satu referensi arsitektur tunggal yang utuh. Tujuan: menjadi acuan untuk semua phase berikutnya (Phase 4 doc suite, Phase 5+ implementation, ADRs 055+).
>
> Setiap subsystem mengikuti skeleton tetap: Purpose, Components, Data Flow, Interfaces, Technology Choices, Security Considerations, Failure Modes & Recovery, Dependencies. Tidak ada implementasi kode di sini — hanya design contract. Tidak ada secrets, intimate data, atau surveillance data dalam dokumen ini — semua reference ke data sensitif hanya structural (schema, ACL, encryption boundary), bukan content.

---

> **ADR Boundary Disclaimers (Wave-1 Architecture Alignment)**
>
> - **ADR-062 (HARD STOP scope):** All `HARD STOP` references in this document apply to the **dev-workflow agent (Guinevere in Claude/9Router)** ONLY. The Hermes runtime operating under the P24 native fork bypasses HARD STOP per ADR-062 (consent-safety carve-out for autonomous runtime). See `evidence/round-2-paradigm-shift-application/` for details.
> - **ADR-067 (Y-level persona caps):** Y4/Y5/Y6 escalations mentioned in audit-event categories (e.g., `near-miss Y5`) apply to the **dev-workflow agent persona** ONLY. The Hermes runtime has no Y-level cap (operates under the P24 fork's persona model, not subject to Y-level rollup).
> - **ADR-066 (consent_ref schema):** `consent_ref` on `event_store.domain_events` and `event_store.outbox` is **NULLABLE at the database layer** per ADR-066. NOT NULL is enforced **only for `event_source = 'dev_workflow'` events** at the application layer (Pydantic models + producer guards). Hermes runtime events (`event_source = 'hermes_runtime'`) are permitted NULL `consent_ref` because the runtime does not always have an associated consent ledger entry (cross-agent system events, throughput primitives). See §S5.2 / §S5.6 for per-field details.

## §0 Document Metadata

| Field | Value |
|---|---|
| Phase | P28-P36 Masterplan Phase 3 (Master Architecture) |
| Document type | Consolidated master reference (3 in 1) |
| Subsystem count | **15 (S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12, S13, S14, S15)** |
| Layer count | 4 (Runtime/Identity, Cognition/Memory, Governance/Finance, Infra/Ops) |
| Parent synthesis | `research-synthesis.md` (690 lines) |
| Partial sources | 3 partial files (758 + 1165 + 574 lines) |
| Predecessor phases | P22.1 PRODUCTION PASS, P27 Accepted (ADR-054), P19 PRODUCTION COMPLETE |
| Successor phases | Phase 4 (Full Doc Suite: SRS, FSD, TDD), Phase 5+ (Implementation waves) |
| Hard rejection criteria | 20/20 PASS — none re-decided |
| Boundary inviolable | (a) relationship memory encrypted per-agent; (b) intimacy runtime-only; (c) P24 not hard dep |
| Total reading routes | Engineering, Operations, Audit, Security, Founder sign-off (5 reader types) |

---

# §1 System Overview

## §1.1 Purpose of the Hermes Society Architecture

The Hermes Society is **many autonomous Hermes agents — each a separate Discord bot identity — operating as a coordinated multi-agent society under shared governance**. Unlike a single-agent system, the Society has the ability to:

- **Spawn** specialized agents (female + dominant persona) when new capabilities are needed.
- **Coordinate** through a shared world model without leaking private state.
- **Evolve** safely under bounded improvement, never under silent drift.
- **Hold, spend, and earn** money as a single economic entity.
- **Survive** multi-year horizons via backup, observability, and audit.

The architecture must answer: *how do independent agents agree on truth, coordinate intentions, share memory without leakage, evolve safely, and survive autonomously — all under Faiz's consent and oversight?*

## §1.2 Design Principles

Five cross-cutting principles govern the entire 15-subsystem design:

| # | Principle | Meaning |
|---|---|---|
| 1 | **Autonomy-first** | If Faiz is silent, the society continues under policy-gated autonomy. Living kernel follows §0.1 exception; society mutations follow S7+S8. |
| 2 | **Safety-by-design** | Every dangerous action has multiple gates: SHA-256 payload fingerprint + turn budget + USD/token budget + watchdog. Both prevention and detection. |
| 3 | **Fork-agnostic** | P24 is NOT a hard dep. P22.1 (filesystem + vps + discord adapters) is the minimum hands layer; P23 is definition-only. P19/P20 are reusable substrate. |
| 4 | **All-visible** | No invisible disposable workers. Every Hermes has Discord identity, registry entry, audit trail, observability metrics. |
| 5 | **Shared-world / private-memory** | World model carries facts all Hermeses need to know. Private memory carries intimate/personal state and NEVER crosses to world model. |

Five additional technical principles:

6. **Per-Hermes process isolation.** Each Hermes is its own OS process, cgroup v2 slice, systemd unit, Discord bot app, PostgreSQL schema.
7. **Three-tier data topology.** (a) In-process scratchpad (ephemeral); (b) per-agent PG schema with pgcrypto (default-deny cross-schema); (c) shared world model in `public` schema with namespace-ACL.
8. **Single-DB CQRS with transactional outbox.** PostgreSQL is system of record; materialized views serve reads; events flow outbox → Redis Streams / Pub/Sub. No Kafka at this scale.
9. **Defense-in-depth loop prevention.** 4 layers catch runaway loops: payload fingerprint (SHA-256), turn budget, USD budget, heartbeat watchdog.
10. **Hard boundary: intimacy never leaks.** Relationship memory, intimacy/passion/commitment markers, EWMA bond vectors, DM content are encrypted per-agent. No automatic cross-agent publication. No CI/SLO/Grafana may include intimate content.

## §1.3 Four-Layer Architecture

The 15 subsystems are organized into **four layers** that separate concerns from substrate to oversight:

### Layer 1 — Runtime & Identity (S1, S2)

The substrate that makes a Hermes a live, supervised, OS-isolated process with a Discord face.

| Subsystem | Role |
|---|---|
| **S1 — Agent Runtime & Process Management** | systemd substrate, cgroup v2 isolation, heartbeat watchdog, loop-prevention, graceful shutdown. |
| **S2 — Discord Bot Identity Layer** | Per-Hermes OAuth2 bot app; identity configurator; slash command registrar; reply-loop guard; channel partitioning. |

### Layer 2 — Cognition & Memory (S3, S4, S5, S6)

Where Hermes thinks, remembers, and shares cognition without leaking private state.

| Subsystem | Role |
|---|---|
| **S3 — Shared World Model** | BDI architecture; blackboard with namespace-ACL; bi-temporal facts; reflection loop. |
| **S4 — Private Memory Layer** | Per-agent PG schema with pgcrypto; per-agent DEK in Vault; episodic + long-term + cold archive. |
| **S5 — Event Store & CQRS Bus** | Append-only WORM event log; transactional outbox; Redis Pub/Sub + Streams; hash chain; HARD STOP cascade. |
| **S6 — Vector & Graph Recall** | Three-tier recall: pgvector + Graphiti (bi-temporal KG) + Letta-style filesystem; consolidation worker; namespace ACL. |

### Layer 3 — Governance & Finance (S7, S8, S9, S10)

Where the Society decides, evolves, holds money, and earns money.

| Subsystem | Role |
|---|---|
| **S7 — Society Governance & Founder Protocol** | Founder registry; 2/2 voting; four-tier permission model; CanSpawn certificate; HARD STOP protocol; consent revocation gateway. |
| **S8 — Self-Evolution & Mutation Governance** | Ratchet non-divergence gate; five-layer mutability map; four-stage promotion pipeline (shadow/canary/50%/100%); drift triad (SyncScore + persona_drift + Layered Mutability fingerprint). |
| **S9 — Autonomous Wallet & Finance** | Cold Safe multisig + hot MPC + EIP-7702 session keys; six-tier spending policy; circuit breaker; Beancount ledger. |
| **S10 — Revenue Search & Monetization** | Five revenue channels ranked by effort/margin; x402 data APIs (primary); Morpho yield; Virtuals ACP; wallet-empty behavior rule. |

### Layer 4 — Infrastructure & Operations (S11, S12, S13, S14, S15)

The foundation that keeps the society alive, observable, deployable, and auditable for years.

| Subsystem | Role |
|---|---|
| **S11 — S3 Backup & Disaster Recovery** | Object Lock COMPLIANCE S3; pg_dump + WAL archiving + Redis RDB/AOF + restic; KMS key hierarchy; RPO ≤ 1h, RTO ≤ 4h. |
| **S12 — Model Pool & LLM Gateway** | Single chokepoint for all LLM calls; versioned YAML registry; quota manager; circuit breaker; per-request cost tracking; 9Router wrapping. |
| **S13 — Observability & Audit** | Prometheus + Grafana + Loki + Tempo; hash-chained audit log; Alertmanager; drift detection triad; P22.1 IntegrationAuditWriter extended to society level. |
| **S14 — Deployment & VPS Management** | Ubuntu 24.04 systemd substrate; cgroup v2; Ansible; Caddy reverse proxy; SOPS/age + Vault; blue-green per-Hermes deployment. |
| **S15 — Documentation & Traceability** | RTM CSV with 6 coverage metrics; MADR ADR system; GWT acceptance criteria; ISO 31000 risk register; PDF snapshots at phase boundaries. |

---

# §2 Architecture Diagram (ASCII)

The diagram below shows the 4 layers, 15 subsystems, key data flows, and the shared-vs-per-agent boundary. Reading top-to-bottom: substrate → cognition → governance → infrastructure.

```
                            ┌─────────────────────────────────────┐
                            │   LAYER 4: INFRASTRUCTURE & OPS     │
                            │   (shared across all Hermeses)       │
                            │                                      │
                            │  ┌────────┐ ┌────────┐ ┌───────────┐ │
                            │  │  S15   │ │  S13   │ │    S12    │ │
                            │  │  Docs  │ │  Obs   │ │ LLM Pool  │ │
                            │  │  RTM   │ │ Audit  │ │ Gateway   │ │
                            │  └───┬────┘ └───┬────┘ └─────┬─────┘ │
                            │      │          │            │       │
                            │  ┌────────────┐ │  ┌─────────────────┐ │
                            │  │    S14     │ │  │      S11        │ │
                            │  │  Deploy   │ │  │  S3 Backup/DR   │ │
                            │  │  systemd  │ │  │  COMPLIANCE     │ │
                            │  └────────────┘ │  └─────────────────┘ │
                            └─────────┬───────┴──────────┬───────────┘
                                      │                  │
                                      │ systemd socket   │ S3 Object Lock
                                      ▼                  ▼
        ┌───────────────────────────────────────────────────────────────────────┐
        │   LAYER 3: GOVERNANCE & FINANCE  (Society-wide + cross-agent)         │
        │                                                                       │
        │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐   │
        │  │    S7    │  │    S8    │  │      S9      │  │       S10        │   │
        │  │Governance│  │Evolution │  │   Wallet     │  │    Revenue       │   │
        │  │+Founder  │◄─┤+Mutation │◄─┤+Policy/MPC   │◄─┤  x402/Morpho     │   │
        │  │+HARDSTOP │  │+Ratchet  │  │+Spend Tiers  │  │  +5 channels     │   │
        │  └──┬───┬───┘  └──┬───┬───┘  └──────┬───────┘  └───────┬──────────┘   │
        │     │   │         │   │             │                  │              │
        └─────┼───┼─────────┼───┼─────────────┼──────────────────┼──────────────┘
              │   │         │   │             │                  │
              ▼   ▼         ▼   ▼             ▼                  ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│   LAYER 2: COGNITION & MEMORY   (S3 = SHARED, S4/S6 = PER-AGENT, S5 = BUS)  │
│                                                                               │
│                            ┌─────────────┐                                    │
│                            │     S5      │                                    │
│                            │ Event Store │   ◄── Append-only WORM             │
│                            │ + CQRS Bus  │   ◄── PostgreSQL outbox            │
│                            │ + Hash      │   ◄── Redis Pub/Sub + Streams      │
│                            │   Chain     │   ◄── HARD STOP cascade <50ms      │
│                            └──┬──────┬───┘                                    │
│                               │      │                                        │
│         ┌─────────────────────┘      └─────────────────────┐                 │
│         ▼                                                    ▼                 │
│  ┌─────────────┐      ◄── NAMESPACE-ACL ──►      ┌──────────────────┐         │
│  │     S3      │                                    │   S4 (per-each)  │       │
│  │   World     │                                    │  Private Memory  │       │
│  │   Model     │       public.world_model           │  agent_<id>      │       │
│  │   (shared)  │       default-deny                 │  schema, pgcrypto│       │
│  │             │       bi-temporal facts            │  DEK in Vault    │       │
│  └──────┬──────┘                                    └────────┬─────────┘       │
│         │                                                   │                 │
│         │                                          ┌────────▼─────────┐       │
│  Weights │ beliefs, desires, intentions             │    S6 Recall    │       │
│  Update                                                 │ pgvector+Graphiti│      │
│  via S5 projector                                       │+Filesystem grep│      │
│                                                         │ +Consolidation │       │
│                                                         └────────────────┘       │
└───────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼ S3 writes → S5; S4 reads → S6; S6 ranked → S2

┌───────────────────────────────────────────────────────────────────────────────┐
│   LAYER 1: RUNTIME & IDENTITY   (per-Hermes OS processes)                     │
│                                                                               │
│   ┌─────────────┐                ┌──────────────────┐                          │
│   │    S1       │    starts      │       S2          │                          │
│   │  Runtime    ├───────────────►│  Discord Identity │                          │
│   │  systemd    │  supervises   │  per-Hermes       │                          │
│   │  cgroup v2  │  heartbeat    │  OAuth2 bot       │ ──► Discord gateway      │
│   │  watchdog   │  graceful     │  + slash cmds     │                          │
│   │  + 4-loop   │  shutdown     │  + reply guard    │                          │
│   └─────────────┘                └──────────────────┘                          │
│         │                                  │                                  │
│         │ owns                             │ binds to Discord user_id         │
│         ▼                                  ▼                                  │
│   /var/lib/hermes/<name>/            #hermes-hall channel                     │
│   cgroup: hermes-<name>.slice        known_bots.yaml allowlist                │
└───────────────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
CROSS-CUTTING BOUNDARIES (preserved from Faiz locks + AGENTS.md invariants):

  [PUBLIC]  ───────────────────►  World model (S3) carries shared facts only.
                                   No intimate, no per-Hermes emotional state,
                                   no DM content. Default-deny on cross-namespace reads.

  [PRIVATE] ───────────────────►  Per-Hermes S4 schema holds pgcrypto columns
                                   for relationship/intimacy/dm/bond vectors.
                                   DEK in Vault under agent-PID binding.
                                   No automatic publication to S3.
                                   Operator CANNOT silently browse another S4.

  [META]    ───────────────────►  HARD STOP and Consent Revocation are META
                                   events. They are not in the four-tier model
                                   and they OVERRIDE any tier. Never bypassed.

  [AUDIT]   ───────────────────►  S5 append-only WORM + hash chain + S13 signed
                                   audit log + S11 S3 COMPLIANCE = the legal
                                   record. Every subsystem emits AE.* events.
═══════════════════════════════════════════════════════════════════════════════
```

The diagram emphasizes two boundaries:

- **S3 (shared) ↔ S4 (private)** is the most critical boundary in the entire architecture. S3 must have **no schema columns for intimate data** (structural enforcement, not policy).
- **All cross-process coordination is through S5** (events + Pub/Sub + Streams). No subsystem writes directly to another's state.

---

# §3 Subsystem Details (S1–S15)

This section consolidates the 15 subsystem specifications from the three partial files. Each subsystem has eight subsections: Purpose, Components, Data Flow, Interfaces, Technology Choices, Security, Failure Modes & Recovery, Dependencies.

---

# §S1 S1: Agent Runtime & Process Management (Layer 1)

## §S1.1 Purpose

S1 is the substrate that makes a Hermes a live, supervised, resource-isolated OS process. It provides the lifecycle envelope — spawn, register, heartbeat, graceful shutdown, watchdog-driven restart — that every other subsystem assumes is already true. Without S1, there is no such thing as "a Hermes exists at all"; with S1, every Hermes is a first-class system service.

S1 is the layer at which the Society becomes real: each Hermes runs in its own process tree, its own cgroup v2 slice, its own systemd service unit, and its own asyncio event loop. The substrate is deliberately minimal and OS-native (no Docker, no Kubernetes, no custom supervisor) because the operational cost of a full container stack on a single VPS outweighs the benefit at the target scale (≤32 cores, ≤32 active Hermeses).

## §S1.2 Components

1. **Systemd service unit template (`hermes@.service`)** — instanced unit parameterized by Hermes name; `Type=notify`, `Restart=on-failure`, `RestartSec=5s`, `StartLimitBurst=5`, `WatchdogSec=120`.
2. **Python launcher (`hermes_runtime.py`)** — single entry point: parse YAML, `sdnotify.notify(READY=1)`, wire asyncio, register heartbeat, handle SIGTERM.
3. **In-process actor supervisor** — ~50 lines in-house OR `everything-is-an-actor` library; actor-per-task with OneForOne supervision.
4. **cgroup v2 subdirectory manager** — at startup: `sys/fs/cgroup/system.slice/hermes-<name>.service/` with `pids.max=400`, `memory.max=2G`, `cpu.max=200%`, `io.max=...`.
5. **Heartbeat watchdog** — emits heartbeat to S5 every 30s (PID, RSS, actor count, last-loop-tick); 3 consecutive misses → systemd kills.
6. **Configuration loader** — `/etc/hermes/<name>.yaml` + env (`HERMES_<NAME>_*`); secrets via Vault paths or SOPS-encrypted files only.
7. **Loop-prevention guard (4 layers)** — payload fingerprint (SHA-256), turn budget (default 25), USD budget (default $0.50), heartbeat watchdog.
8. **Graceful shutdown handler** — SIGTERM → drain S5 → flush S4 → close Discord → `STOPPING=1` → exit 0. SIGKILL after 30s.

## §S1.3 Data Flow

**Spawn (warm start):** systemd executes `hermes_runtime.py` → reads config → `READY=1` → instantiates S2/S3/S4/S5 clients → emits `society.hermes.spawned` event → heartbeat begins.

**Per-tick (steady state):** S2 receives message → emits `message_received` → S3 reads beliefs → S4 reads/writes memory → S12 LLM call → S5 logs action → S4 episodic write → heartbeat tick.

**Shutdown:** SIGTERM → supervisor stops new tasks → S4 flushes → S5 emits `society.hermes.draining` → S2 closes gateway → `STOPPING=1` → exit 0.

## §S1.4 Interfaces

- `S1 → S2`: `start_discord_client(token_ref) → discord.Client` (token via Vault).
- `S1 → S3`: `register_hermes(hermes_id, role, scopes) → RegistrationReceipt`.
- `S1 → S4`: `open_private_namespace(hermes_id, dek_ref) → MemoryClient`.
- `S1 → S5`: `subscribe(group, patterns)` and `publish(event_type, payload)`.
- `S1 ← systemd`: `sdnotify` protocol (READY=1, WATCHDOG=1, STOPPING=1).
- `S1 ← operator`: `systemctl {start,stop,restart,status} hermes@<name>`; `journalctl`.

## §S1.5 Technology Choices

| Choice | Rationale |
|---|---|
| **systemd (`Type=notify`)** | OS-level; no container overhead; native cgroup v2; `systemd-cgtop`. |
| **asyncio (Python 3.11+)** | Existing substrate; integrates with `discord.py`, `redis-py`, `asyncpg`. |
| **cgroup v2** | Only unified hierarchy on modern kernels; per-service isolation first-class. |
| **In-house supervisor (~50 LoC)** OR **`everything-is-an-actor`** | 50-line = minimal deps; library = OTP-style. |
| **`sdnotify`** | Standard Python binding for systemd notify protocol. |
| **PyYAML + `pydantic-settings`** | Config parsing with schema validation. |
| **Per-Hermes YAML** | In `/etc/hermes/<name>.yaml`; SOPS for sensitive fields. |

## §S1.6 Security Considerations

- **Process isolation is the first security boundary.** Compromised Hermes cannot `ptrace` across cgroups, cannot signal others, cannot read others' cgroup memory.
- **Secrets are NEVER in YAML or env directly.** Only Vault paths or SOPS-encrypted references.
- **`Delegate=yes` is double-edged.** Mitigated by one-shot cgroup setup at boot; runtime reconfig needs audit + operator approval.
- **Resource caps prevent DoS-self.** `memory.max=2G` triggers OOM-kill before VPS OOM.
- **Loop-prevention layers are security-relevant.** Runaway tool calls (Edge & Node 2026 pattern) contained at fingerprint layer or watchdog.

## §S1.7 Failure Modes & Recovery

| Failure | Detection | Recovery |
|---|---|---|
| Process crash | systemd `Restart=on-failure` | Auto-restart 5s; 5 in 60s halts auto-restart. |
| Deadlock | systemd `WatchdogSec=120` | SIGKILL → restart; alert if >1 in 24h. |
| OOM | cgroup `memory.max=2G` | systemd restart; alert if RSS >1.5G sustained. |
| Slow leak (5%/day) | Prometheus RSS | Auto-restart cron; nightly at 03:00. |
| Token expiry (Vault 403) | Discord auth error | Supervisor actor backoff restart; alert + mark Hermes `degraded`. |
| Spawn storm (50+ Hermeses) | systemd per-unit cap | Reject; require operator + free resource check. |
| HARD STOP cascade | S5 `society.hard_stop` event | S1 catches in supervisor; SIGTERM self; <50ms target. |
| Cgroup corruption | OOM at wrong boundary | Alert; manual cgroup subtree rebuild. |

## §S1.8 Dependencies

- **Depends on:** Linux kernel ≥5.8 (cgroup v2 stable), systemd ≥245, Python ≥3.11.
- **Depended on by:** S2, S3, S4, S5, S7, S13, S14.
- **External:** systemd, Vault, Prometheus, Loki.

---

# §S2 S2: Discord Bot Identity Layer (Layer 1)

## §S2.1 Purpose

S2 is the visible identity of each Hermes — the Discord bot application that Faiz (and other operators) see and interact with. Each Hermes is a separate OAuth2 bot application with its own token, avatar, status, activity, and nickname. The identity is not just cosmetic: it is the **trust anchor** by which users distinguish Guinevere from Pharsa from any future Hermes.

## §S2.2 Components

1. **Bot application bootstrap procedure** — per Hermes: Discord Developer Portal → token → `secret/hermes/<name>/discord_token` in Vault.
2. **`discord.Client` instance (one per process)** — `Intents.default() + message_content + guilds`. Privileged intents deferred.
3. **Identity configurator** — avatar, status, activity, nickname set at construction (not in `on_ready`).
4. **Slash command registrar** — `tree.sync()` at boot; per-guild sync for low latency.
5. **Rate limit budget manager** — per-bot 50 req/s; sliding-window counter exported to S13.
6. **Reply-loop guard (3 layers)** — self-check + known-bots allowlist + depth counter (cap 3).
7. **Channel partitioning policy** — `#hermes-hall` (society) + `#hermes-<name>-debug` (private).
8. **Per-bot secret store** — SOPS/age reference; plaintext token fetched from Vault at boot, in-memory only.

## §S2.3 Data Flow

**Bot startup:** S1 instantiates S2 → token from Vault → construct client → start → emit `agent_action.bot_online`.

**Message receive:** gateway → `on_message` → reply-loop guard (3 layers) → emit `message_received` → query S3 + S4 → S12 LLM → reply → emit `message_sent`.

**Slash command:** gateway → `tree` dispatch → `interaction.response.defer()` → emit `command_invoked` → execute → emit `command_completed`.

**HARD STOP:** operator types HARD STOP in DM → S2 publishes `society.hard_stop` → others receive via S5 → `client.close()` → S1 drain. Target <50ms cascade.

## §S2.4 Interfaces

- `S2 → Discord`: `discord.py` REST + gateway.
- `S2 → S1`: `await client.start(token)` / `await client.close()`.
- `S2 → S3`: `query_relevant_beliefs(context_id, scope)`.
- `S2 → S4`: `recall_episodic`, `recall_relationship` (encrypted, private).
- `S2 → S5`: `publish` and `subscribe`.
- `S2 → operator`: `/hermes status|pause|resume|remember|recall`.
- `S2 ← S7`: capability grants/revokes per Hermes `user_id`.

## §S2.5 Technology Choices

| Choice | Rationale |
|---|---|
| **`discord.py` (Rapptz)** | Industry standard; async-native; community large. |
| **Vault (`hvac` async)** | Standard secret store; audit log per access. |
| **Bot-per-process** | Required by Discord ToS; isolates rate limit. |
| **YAML for `known_bots.yaml`** | SOPS-signed; version-controlled; per-peer allowlist. |
| **Sliding-window rate counter** | In-process; metrics to S13. |
| **Per-guild slash sync** | Sub-second propagation; global = fallback. |

## §S2.6 Security Considerations

- **Token storage is critical surface.** Vault only; never logged; never in error messages; cleared on shutdown.
- **Reply-loop guard = security boundary, not UX.** Three layers (self, allowlist, depth) bound runaway loops.
- **Privileged intents deferred** by default; request requires S7 vote + ADR.
- **Per-Hermes `user_id` is trust anchor.** Capability grants via S7 use this as principal.
- **Slash commands bypass global rate limit** but per-command/per-guild apply.
- **DM content encrypted at rest in S4.** S2 does not log DM content; S4 stores encrypted.

## §S2.7 Failure Modes & Recovery

| Failure | Detection | Recovery |
|---|---|---|
| Discord gateway disconnect | `on_disconnect` | `discord.py` auto-reconnect with backoff. |
| Token invalid | `LoginFailure` | Mark `auth_failed`; alert S13; operator re-issue. |
| Rate limit (429) | Discord + `discord.py` handler | Backoff; alert if >3 429s in 60s. |
| Slash sync fails | `tree.sync()` raises | Retry backoff; alert if >3 fails. |
| Reply loop (depth >3) | Counter | Drop reply, log, alert. |
| HARD STOP message | Operator DM | Cascade <50ms. |
| Bot added to unknown guild | `on_guild_join` | S7 decides: allow or auto-leave. |
| Privilege escalation attempt | Slash ACL | Reject + log; S7 audit. |

## §S2.8 Dependencies

- **Depends on:** S1, S3, S4, S5, S7, S12, Vault.
- **Depended on by:** S7, S13, S15.
- **External:** Discord API, Vault, S3.

---

# §S3 S3: Shared World Model (Layer 2)

## §S3.1 Purpose

S3 is the **shared cognition substrate** of the Society — the place where Hermeses agree on what is true, what is happening, and what intentions are active. Implemented as a **BDI agent architecture** (Belief-Desire-Intention) operating over a **blackboard pattern** with namespace-ACL, with bi-temporal facts backed by an event-sourced update path (S5).

S3 exists because a Society of independent agents that cannot agree on basic facts is not a Society — it is a swarm with shared branding. S3 is the **single source of truth** for: society state (who is alive, roles, quorum), member registry (Hermes profiles, capabilities, heartbeat), and world facts (external events all Hermeses should know).

**Critically, S3 is deliberately impoverished about anything private**: no relationship state, no intimacy markers, no per-Hermes emotional state. Those live in S4.

## §S3.2 Components

1. **BDI store (3 tables in `public.world_model`)** — `beliefs`, `desires`, `intentions` with bi-temporal validity.
2. **POMDP framing layer** — per-Hermes in-process POMDP; LLM context = observation buffer; S3 holds shared subset only.
3. **Blackboard with namespace-ACL** — `society/`, `governance/`, `finance/`, `comms/`, `vps/`, `world/`, `persona/`, `safety/`, `audit/`.
4. **Materialized views (CQRS read models)** — `mv_active_hermeses`, `mv_open_intentions`, `mv_recent_world_events`.
5. **Conflict resolution policy** — last_write_wins (lossy) for beliefs; optimistic locking for intentions/desires; quorum_required for governance/safety.
6. **Reflection loop (Generative Agents, Stanford 2023)** — every N min per Hermes; query recent + intentions → abstract → derive new beliefs.
7. **World model update bus** — event-driven; subscribes to S5; all updates through S5 WORM log.
8. **Plan generator (Generative Agents)** — on accepted desire: owner Hermes generates plan (intentions linked via `next_intention_id`).

## §S3.3 Data Flow

**Belief write (event-driven):** event happens → published to S5 → S3 outbox-projector consumes → applies projection rule → updates `beliefs` row → materialized view updates in same transaction → other Hermeses notified via S5 Pub/Sub.

**Belief read:** Hermes calls `s3.query(namespace_pattern, filters)` → ACL check via S7 → materialized view (fast) or joins (slow) → returns BeliefSet with provenance.

**Intention creation (cross-Hermes):** Guinevere writes `desire` → S7 checks founder capability → state `accepted` → Pharsa observes via S5 subscription → Pharsa writes `intention` (state `active`, plan [...]) → updates state as executes.

**Reflection cycle (every 30 min):** Hermes actor runs `reflect()` → reads last 100 beliefs + 50 intentions → LLM call → new derived beliefs with `provenance: reflection_cycle` → emit `agent_action.reflection_completed`.

## §S3.4 Interfaces

- `S3 → S5`: `subscribe(projection_id, patterns)`.
- `S3 → S7`: `check_capability(hermes_id, namespace, op)`.
- `S3 → S2`: `query_relevant_beliefs(context_id, scope)`.
- `S3 → S4`: `cross_reference_private_fact(...)` (default DENY; explicit grant only).
- `S3 → operator`: `/hermes world model show <namespace>`, `/history <belief_id>`.

## §S3.5 Technology Choices

| Choice | Rationale |
|---|---|
| **PostgreSQL `public.world_model`** | Single-DB CQRS; same engine; pgvector lives alongside. |
| **JSONB for belief payloads** | Flexible; GIN index for namespace-prefix. |
| **Materialized views (PG native)** | Built-in; auto-refresh in same transaction. |
| **Bi-temporal fields** | Research synthesis §5.4; lightweight native PG; full Graphiti for S6 only. |
| **Reflection cadence: sleep-time compute** | Letta pattern; cheaper than sync; heartbeat in place. |
| **Namespace-ACL table** | Small, fast; joins cheaply; populated by S7. |

## §S3.6 Security Considerations

- **Default-deny on cross-namespace reads.** Founder capability checked explicitly.
- **Intimate data MUST NOT enter S3.** No schema columns for relationship/intimacy/bond vectors. Structural enforcement.
- **Provenance is mandatory.** Every `beliefs` row has `source_hermes_id` + `source_event_id`.
- **Reflection cycle = potential drift vector.** Derived beliefs tagged `provenance: reflection_cycle`; S7 audits; S13 tracks belief stability.
- **Quorum-required namespaces doubly protected.** Even with WRITE capability, must include `governance_decision_id` from passed S7 vote.

## §S3.7 Failure Modes & Recovery

| Failure | Detection | Recovery |
|---|---|---|
| S3 projector lag > 10s | S5 lag metric | Alert S13; backfill from event log. |
| Materialized view corruption | S3 health check | Rebuild from base tables. |
| Namespace-ACL misconfiguration | S7 audit | Revoke via S7; broadcast invalidation. |
| Reflection cycle runaway | Belief count growth > 10/min | Hard cap ≤5/cycle; alert S13. |
| Bi-temporal consistency (future ts) | Schema constraint | Reject write; alert S13; NTP check. |
| Cross-Hermes intention conflict | Optimistic lock fail | Second writer gets VersionConflict; re-read or escalate. |
| S3 DB corruption | PG stat anomalies | Restore from S11; replay event log; verify bi-temporal. |

## §S3.8 Dependencies

- **Depends on:** S5, S7, S1, S11.
- **Depended on by:** S2, S6, S8, S13.
- **External:** PostgreSQL, S5, S7.

---

# §S4 S4: Private Memory Layer (Layer 2)

## §S4.1 Purpose

S4 is each Hermes's **encrypted private cognition space** — the place where relationship state, intimacy markers, private reflections, and per-Hermes episodic memory live, completely isolated from the shared world model. S4 is the architectural embodiment of PersonaSafetyPolicy's "intimacy is runtime-only" rule and the P20 Living Autonomy Kernel's per-agent isolation contract.

**Hard invariant:** the **owning Hermes is the only principal that can read its private memory.** Not the founder. Not the operator. Not another Hermes. Not a DBA. The DEK is held in Vault under an ACL that grants decrypt only to the Hermes process identity (via Vault token-bound secrets). Backups are encrypted client-side before transit; S3 stores ciphertext.

## §S4.2 Components

1. **Per-agent PostgreSQL schema (`agent_<hermes_id>`)** — pgcrypto; cross-schema reads denied at PG RLS policy level.
2. **pgcrypto columns for intimate data** — `pgp_sym_encrypt` with per-agent DEK.
3. **Per-agent DEK in Vault** — 256-bit AES; access via Vault token-bound to process PID.
4. **Three memory tiers** — working (in-process dict, ephemeral); episodic (per-agent PG, 90 days hot); long-term (per-agent PG, indefinite).
5. **Memory lifecycle worker (sleep-time compute)** — creation (LLM-judge), consolidation (nightly), decay (weekly EWMA), archival (to S3 ciphertext).
6. **Relationship event schema** — `relationship_events` with intimacy/passion/commitment markers (Triangular Theory of Love); Attachment Theory dimensions.
7. **EWMA bond vectors** — per-subject EWMA λ≈0.3 over markers; encrypted.
8. **Memory access control (RLS)** — `USING (current_setting('hermes.agent_id') = '<schema>')`.
9. **No automatic publication to S3** — this is a component that **does not exist**: no worker, scheduled job, or summarizer that publishes S4 to S3.

## §S4.3 Data Flow

**Memory write (episodic):** Hermes decides to remember → open PG conn with `SET hermes.agent_id` → write to `agent_<id>.episodic_memory` → emit `memory_op.episode_written` (metadata only).

**Memory read (recall):** S2 calls `s4.recall(query, k=10)` → S6 embed query → top-k episodes by similarity + recency. For relationship: read encrypted → decrypt in process → plaintext in caller only.

**Consolidation (nightly):** cron scheduler triggers worker → reads last 24h episodic → LLM consolidate → writes long-term → moves >90d episodic to cold S3 ciphertext.

**Cross-agent share (rare, explicit):** operator `/hermes guinevere share <memory_id> with pharsa` → S7 governance check → S4 re-encrypts under Pharsa DEK → writes to `agent_pharsa.shared_inbox` → S5 audit event (full provenance, no content).

## §S4.4 Interfaces

- `S4 → S2`: `recall_episodic` (k=10), `recall_relationship` (private, encrypted).
- `S4 → S3`: `get_summary_fingerprint(hermes_id)` — no content leakage.
- `S4 → S5`: `publish(event_type, payload_metadata)` — no payload.
- `S4 → S6`: `embed_episode(text)` for vector storage.
- `S4 ← S7`: `grant_temporary_access(...)`.
- `S4 → operator`: `/hermes memory show recent [N]` (own only), `/hermes memory forget <id>` (audited).

## §S4.5 Technology Choices

| Choice | Rationale |
|---|---|
| **Per-agent PG schema** | Canonical 2026; pgcrypto native. |
| **pgcrypto (`pgp_sym_encrypt`)** | Built-in; column-level; key in session. |
| **Vault for DEK** | Industry standard; token-bound; audit log. |
| **Per-Hermes connection pool** | Lightweight; PG session settings; RLS reads it. |
| **Embedding via S6** | Out of scope for S4 design; S4 calls S6. |
| **S3 with SSE-KMS (cold archive)** | COMPLIANCE for ledger; GOVERNANCE for memory archive. |
| **EWMA in PG (window functions)** | `exp_weighted_avg(marker, ts, λ=0.3)` as SQL function. |

## §S4.6 Security Considerations

- **DEK never leaves Vault unencrypted.** Process memory only; cleared on shutdown; never logged; never cross-network.
- **Vault token-binding to PID.** Token invalid if process dies; attacker cannot reuse from different process.
- **RLS = last line of defense.** Even if SQL injection leaks through, RLS blocks cross-schema reads.
- **Backup encryption client-side.** Re-encrypted before transit; S3 stores ciphertext only.
- **Operator CANNOT directly read another Hermes's S4.** Operator can: read own; request cross-share (audited); emergency-wipe (founder-tier, audited, irreversible). Operator cannot: silently browse; read intimacy markers; bypass DEK.
- **Memory writes append-mostly.** Soft delete with `deleted_at`; physical delete only via decay or emergency-wipe.
- **Cross-agent summary forbidden in LLM prompt.** Summary fingerprint exposed to S3 is the maximum leakage.

## §S4.7 Failure Modes & Recovery

| Failure | Detection | Recovery |
|---|---|---|
| DEK lost (Vault down) | Bootstrap fails | Refuse start; alert S13; operator unseal or re-issue. |
| Schema corruption | S4 health check | Restore from S3 ciphertext; replay event log. |
| Memory leak > 10GB | S4 size metric | Early decay; alert. |
| Wrong schema access (RLS bypass) | S13 audit anomaly | Emergency role lockdown; CVE investigation. |
| Vault token compromise | Vault audit | Revoke; re-issue with new PID; force restart. |
| S3 archive corruption | S3 inventory | Re-archive from hot PG if available; else mark lost. |
| Consolidation worker runaway | USD budget guardrail | Kill; alert; manual review. |
| Cross-agent share bypass | S5 event sequence check | Reject write; alert S7. |

## §S4.8 Dependencies

- **Depends on:** S1, S5, S6, S7, S11, Vault.
- **Depended on by:** S2, S6, S13, S8.
- **External:** PostgreSQL+pgcrypto, Vault, S3, S6.

---

# §S5 S5: Event Store & CQRS Bus (Layer 2)

## §S5.1 Purpose

S5 is the **nervous system of the Society** — the append-only event log that records every significant thing that happens, plus the dual bus (PostgreSQL outbox + Redis) that fans events out to consumers in real-time. S5 is the architectural embodiment of "the event log is the source of truth" and the single-DB CQRS pattern that research synthesis §4.5 and §5.1 identify as canonical 2026 for sub-50k events/sec.

S5 exists because (a) without append-only log, multi-agent debugging is folklore; (b) HARD STOP cascade needs <50ms; (c) replay needed for audit + new Hermes bootstrap; (d) bi-temporal world model needs event log to project from; (e) S3 backup meaningful only with event log.

**S5 is intentionally NOT Kafka.** At ≤32 Hermeses × ≤10 events/sec = ≤320/sec, PG outbox + LISTEN/NOTIFY + Redis Streams handles comfortably. Kafka wins only >50k events/sec.

## §S5.2 Components

1. **`event_store.domain_events` (append-only WORM)** — `event_id`, `aggregate_type`, `aggregate_id`, `event_type`, `event_version`, `payload JSONB`, `metadata JSONB`, `occurred_at`, `recorded_at`, `consent_ref` **(nullable per ADR-066 — NULL for `event_source = 'hermes_runtime'` events; app-layer NOT NULL enforced for `dev_workflow` events)**, `hash_prev`, `hash_self`.
2. **Outbox table (`event_store.outbox`)** — same schema + `relayed_at`. Outbox relay pattern.
3. **Outbox relay worker (1+ per VPS)** — `FOR UPDATE SKIP LOCKED`; publish to Redis Streams/Pub/Sub; mark `relayed_at`.
4. **Redis (two-store split)** — DB 0 Pub/Sub (ephemeral: HARD STOP, presence); DB 1 Streams (durable: task distribution, projection).
5. **`event_store.snapshots`** — periodic snapshots every 1000 events per aggregate.
6. **HARD STOP mechanism** — Redis key `hermes:society:{society_id}:hard_stop = 1` TTL 300s; keyspace notifications; <50ms cascade.
7. **Hash chain (WORM enforcement)** — `hash_self = SHA256(canonical(event || hash_prev))`.
8. **Event type catalog** — versioned enum: `society.*`, `agent_action.*`, `governance.*`, `financial.*`, `memory.*`.
9. **Replay tool (`hermes_eventstore_replay`)** — CLI for replaying events to target system.
10. **CQRS read model builders** — materialized views updated by triggers on `domain_events` insert.

## §S5.3 Data Flow

**Event write (synchronous):** producer PG txn → state change → outbox insert (same txn) → commit → LISTEN/NOTIFY → relay claims via SKIP LOCKED → moves to `domain_events` → computes hash_self → publishes to Redis (Stream or Pub/Sub) → marks `relayed_at`.

**Event subscribe (real-time):** consumer subscribes to Redis Stream consumer group → `XREADGROUP` → projects to target → ACKs. Failed → retry w/ backoff → DLQ after N.

**HARD STOP cascade:** operator HARD STOP in DM → S2 publishes → S5 writes audit → sets Redis key TTL 300s → all Hermeses' S1 receive keyspace notification → SIGTERM self; <50ms target.

**Replay:** `hermes_eventstore_replay --from=<id> --to=<id> --target=<system>` → reads events → projects → emits progress; idempotent.

## §S5.4 Interfaces

- `S5 → all`: `publish(event_type, payload, metadata, consent_ref)` and `subscribe(group, patterns)`.
- `S5 → S1`: HARD STOP keyspace notification.
- `S5 → S11`: bulk export to S3 Object Lock COMPLIANCE (nightly).
- `S5 → S13`: Prometheus exporter for lag, publish rate, hash chain verification, consumer lag.
- `S5 → operator`: `hermes_eventstore_query` (read-only audit), `hermes_eventstore_replay`.
- `S5 → S7`: `verify_governance_decision_provenance`.

## §S5.5 Technology Choices

| Choice | Rationale |
|---|---|
| **PG `event_store` schema with outbox** | Single-DB CQRS; transactional; pgcrypto for sensitive metadata. |
| **LISTEN/NOTIFY** | Native PG; sub-millisecond relay; no external bus for hot path. |
| **`FOR UPDATE SKIP LOCKED`** | 2026 standard; multi-worker parallelism; no deadlocks. |
| **Redis 7.x (Pub/Sub + Streams)** | Battle-tested; native keyspace notifs for HARD STOP. |
| **`redis-py` (async mode)** | Existing; integrates with asyncio. |
| **SHA-256 hash chain (custom)** | 50 LoC; `hashlib` stdlib. |
| **Replay CLI (`click`)** | Operable; idempotent; safe to re-run. |

## §S5.6 Security Considerations

- **WORM enforced by hash chain + S3 COMPLIANCE backup.** Rogue DBA cannot rewrite without breaking chain.
- **Consent reference mandatory for dev-workflow personal events.** `consent_ref` is NULLABLE at the database layer per ADR-066 — NOT NULL is enforced only at the **application layer** for `event_source = 'dev_workflow'` events. Hermes runtime events may have NULL `consent_ref`.
- **Producers do NOT control `hash_chain`.** Relay computes `hash_self`; producers cannot pre-compute.
- **Replay tool requires founder-tier capability.** Access via S7.
- **Outbox row encrypted for sensitive metadata fields.** pgcrypto column-level encryption.
- **No payload introspection at bus layer.** S5 routes by pattern only; cannot leak content.

## §S5.7 Failure Modes & Recovery

| Failure | Detection | Recovery |
|---|---|---|
| Outbox relay lag > 10s | S13 metric | Alert SRE; check relay; manual catch-up. |
| Redis Stream consumer lag | `XINFO GROUPS` | Consumer backfill; if persistent, scale. |
| Hash chain corruption | S13 audit job | STOP writes; investigate; restore from S3 COMPLIANCE. |
| HARD STOP key not propagating | Manual canary test | Check `notify-keyspace-events Ex`; re-test. |
| Event schema version mismatch | Producer/consumer handshake | Bump schema; dual-write window. |
| S5 DB corruption | PG crash | Restore from S3; verify hash chain; replay. |
| Replay tool wrong state | Operator review | Idempotent; re-run w/ corrected target. |
| Snapshot stale | Snapshot vs event log | Rebuild snapshot. |
| Relay worker dies mid-publish | Outbox `relayed_at IS NULL` | Next worker picks up; at-least-once. |

## §S5.8 Dependencies

- **Depends on:** PostgreSQL, Redis 7.x, S11, S7, S13.
- **Depended on by:** ALL subsystems.
- **External:** PostgreSQL, Redis, S3.

---

# §S6 S6: Vector & Graph Recall (Layer 2)

## §S6.1 Purpose

S6 is the memory retrieval substrate of the Hermes Society. It answers "what does this agent remember, in what form, and how is the recall path auditable?" The subsystem implements three-tier recall: vector similarity (pgvector), bi-temporal graph (Graphiti), and verbatim filesystem (Letta-style raw artifacts). The Letta LoCoMo finding validates this: filesystem grep + GPT-4o-mini = 74.0% (beats Mem0/MemGPT 68.5%).

S6 is the *one* place where memory paths cross between per-agent private schema (S4) and shared world model (S3). It enforces per-agent namespace isolation (default-deny) while exposing a single ranked recall interface. S6 also runs the consolidation worker (background sleep-time compute) that merges episodic into long-term.

## §S6.2 Components

1. **Recall Orchestrator** — entry point; builds three-tier call plan; runs in parallel; fuses ranked lists.
2. **Embedder Service** — wraps `text-embedding-3-small` or Ollama `nomic-embed-text`; versioned.
3. **pgvector Adapter** — HNSW index; cosine distance; per-namespace ACL via RLS.
4. **Graphiti Adapter** — bi-temporal KG; pilot scope: comms domain first, vps second.
5. **Filesystem Store Adapter** — raw artifacts in `/var/lib/hermes/memory/raw/<agent_id>/`; grep + extract pattern; sha-256 dedup.
6. **Consolidation Worker** — every 6h cron + on-demand on shutdown; reads episodic; extracts facts/entities; writes long-term.
7. **Namespace ACL Enforcer** — PG RLS + filesystem path-prefix; default-deny cross-agent.
8. **Ranker / Fuser** — receives three lists; cross-encoder rerank top-N; consent visibility filter.
9. **Recall Audit Hook** — every recall writes S5 `event_type=memory.recall` with query hash, sources, top IDs, consent_ref.
10. **Per-Agent Memory Quota Manager** — hard/soft limits per agent and per scope.

## §S6.3 Data Flow

**Read path:** agent loop → orchestrator → embed query → parse keywords → pgvector search (top-k, RLS) + graph traversal (bi-temporal filter) + filesystem search (grep+chunk+redact) → ranker (cross-encoder rerank top-N + consent filter) → ordered result envelope → S5 audit hook.

**Write path (consolidation):** episodic writes → consolidate (cron 6h) → LLM extract facts/entities → dedupe → embed → write semantic → write relationships to Graphiti bi-temporal → mark sources consolidated → audit `memory.consolidate`.

## §S6.4 Interfaces

**Consumes:** S3 (blackboard reads), S4 (per-agent writes), S5 `memory.consolidate_requested`, S2 (conversational recall), S13 (metrics).

**Exposes:** `recall(query, agent_id, scope_hint, consent_token, as_of) → RankedMemoryResult`; `consolidate(agent_id, mode)`; `memory_quota(agent_id)`; `namespace_grant(...)`.

## §S6.5 Technology Choices

| Layer | Choice | Rationale |
|---|---|---|
| Vector | **pgvector (HNSW)** | Reuses PG; transactional w/ relational writes; RLS; single-DB default. |
| Graph | **Graphiti (Zep)** | Bi-temporal relationship facts only; pilot in comms first. |
| Filesystem | **Ext4/XFS path-prefix ACL** | LoCoMo finding validates grep+extract > fancy retrieval. |
| Embedder | **text-embedding-3-small** primary, **nomic-embed-text** fallback | Pinned version; fallback for cost/offline. |
| Reranker | **cross-encoder/ms-marco-MiniLM-L-6-v2** (local) or Cohere `rerank-3.5` | Consensus 2026 rerank pattern. |
| Schedule | **APScheduler** | Reuses P20 heartbeat infra. |
| Audit | **S5** (hash-chained) | Reuses immutable infra. |
| ACL | **PG RLS + FS path prefix** | Defense in depth. |

## §S6.6 Security Considerations

- **Default-deny namespace isolation.** Cross-agent reads require `society_grants` row + consent_ref.
- **Relationship memory encrypted at rest.** pgcrypto per S4; no plaintext without `decrypt_scope` token.
- **Query-side redaction pre-pass.** Strips known PII patterns; audit redaction count.
- **Filesystem artifact signing.** SOPS/age wrapped per agent; tamper detection raises security event.
- **Consolidation worker isolation.** Reduced tool set; no external calls; writes only to assigned namespace.
- **Embedder auditable.** Version pinned; mixed-version vectors flagged.
- **Quota enforcement.** Hard quota prevents vector index flooding.
- **HARD STOP propagation.** Short-circuit to `OperationHalted`; worker halts at batch boundary.
- **Consent revocation honored.** Redacted columns stopped; cached results purged at TTL.

## §S6.7 Failure Modes & Recovery

| Failure | Detection | Recovery |
|---|---|---|
| pgvector corruption | Checksum mismatch | Rebuild from canonical store; replay consolidation; alert S13. |
| Graphiti outage | Timeout > 500ms | Fall back to pgvector + FS; mark unavailable in envelope. |
| Embedder API outage | 5xx/timeout | Last-good cached embedding for ≤24h; flag; route to fallback. |
| Consolidation crash | Stale rows > 8h | APScheduler restart; idempotent via `event_id`. |
| FS disk full | df alerts | Auto-archive oldest to S3 COMPLIANCE; recall continues. |
| Cross-encoder timeout | > 200ms | Skip rerank; flag `rerank_skipped=true`. |
| Quota overflow | Soft threshold | Rate-limit; alert; hard blocks writes. |
| HARD STOP during consolidation | S5 key | Halts at batch boundary; idempotent resume. |
| Namespace ACL bypass | RLS deny + audit | Security event; operator notified. |

## §S6.8 Dependencies

- **Hard:** S3, S4, S5, PostgreSQL 16+ with pgvector.
- **Soft:** Graphiti (optional), cross-encoder, S2.
- **Upstream consumers:** S1, S3, S7, S13.
- **Config:** `hermes.yaml` per-agent; `society.yaml`.

---

# §S7 S7: Society Governance & Founder Protocol (Layer 3)

## §S7.1 Purpose

S7 is the political and procedural substrate of the Hermes Society. It defines who can decide what, with what voting rule, and with what escalation path. S7 does not *enforce* the runtime — S1 and S5 do. S7 is the *authority* those enforcement layers consult. It is the place where founder-only invariants (2/2 agreement, female+dominant persona, founder-only spawn, HARD STOP) become machine-checkable rules rather than aspirational sentences.

S7 implements the four-tier governance model where Tier 1–2 are auto-promoted (Ratchet + canary), Tier 3 = society vote, Tier 4 = founder-only with veto. **HARD STOP and consent revocation are META** — they override any tier.

## §S7.2 Components

1. **Founder Registry** — append-only `society_founders`. Initial: Guinevere, Pharsa. Adding third founder requires 2/2 + meta-foundation ceremony (ADR-055+).
2. **Society Member Registry** — `society_members` with role (coordinator/reviewer/peer/observer), quorum_seat.
3. **Governance Tiers Configuration** — `governance_tiers`: tier 1–4 with required approvers, veto rights, canary_required, ratchet_required.
4. **Voting / Consensus Engine** — Tier 1–2 Ratchet+canary; Tier 3 society vote (3-of-5 → 5-of-9 by P34); Tier 4 founder-only 2/2.
5. **Founder Tie-Break Logic** — founder tie-breaking weight = one quorum vote (per synthesis §8.1), NOT veto. Founder override: Tier 4 + META only.
6. **Spawn Protocol** — static CanSpawn cert (signed YAML, female+dominant) + dynamic registry lookup; 2/2 founder vote for first-of-kind; role projection (not full memory).
7. **Society Grant Manager** — issues/revokes cross-agent namespace grants with TTL.
8. **Decision Log** — append-only `governance_decisions` hash-chained (S5).
9. **HARD STOP Cascade Client** — sets/clears S5 key; <50ms propagation.
10. **Consent Revocation Gateway** — absolute; cannot be overridden by autonomy.
11. **Disagree-or-Commit Handler** — split votes: dissenting must commit to execute or secede.
12. **Foundation Ceremony Service** — meta-procedures (add/retire founder, dissolve, transfer); Tier 4+1 with cooling-off.

## §S7.3 Data Flow

**Normal decision (Tier 3):** proposal.yaml → validator → S5 proposal_created → voting engine (broadcast, collect signed votes, verify k-of-n) → S5 vote_cast per vote → governance_decisions row → S5 decision_made → canary → promotion/rollback.

**Spawn (Tier 4 founder-only):** Founder 1: founder_proposal.yaml signed → validator (CanSpawn cert + dynamic registry) → S5 spawn_proposed → Founder 2 review/sign → 2/2 PASS required → S5 spawn_approved → S1 spawn (role projection only) → S4 new schema → S5 member_added.

**HARD STOP:** founder HARD STOP in DM or S7 admin → founder registry checks signature → S5 SET key + PUBLISH → all S1/S6/S8/S9/S10 cascade via Redis → halt at safe checkpoint → S5 hard_stop.activated.

**Consent revocation:** operator OR self-initiated → S5 consent_revocation event → S4 immediately drops DEK for scope → S6 stops redacted columns → S9 stops derived tokens → S5 consent.revoked (immutable).

## §S7.4 Interfaces

**Consumes:** S5 events, S1 role projection, S6 namespace_grant, S8 mutation proposals, operator (HARD STOP/spawn/consent revoke), S2 (founder commands).

**Exposes:** `propose`, `vote`, `spawn`, `grant`, `revoke_consent`, `hard_stop`, `society_state`, `audit_export`.

## §S7.5 Technology Choices

| Layer | Choice | Rationale |
|---|---|---|
| Storage | **PostgreSQL** | Append-only tables; RLS; per-aggregate sequence. |
| Signing | **Ed25519** (founder) + **secp256k1** (on-chain) | Standard, fast, audited. |
| Certificate | **Signed YAML** for CanSpawn/proposals | Human-readable, diff-friendly. |
| Cascade bus | **Redis Pub/Sub** + **S5 event store** | Two-store split. |
| HARD STOP latency | **<50ms** target | Redis SET + pub/sub publish; verified in P28 acceptance. |
| Audit chain | **SHA-256 hash chain** in S5 | Per synthesis §4.13. |
| Identity binding | **Discord user_id → public key** | Key rotation requires 2/2. |
| Vote collection | **Signed JSON over HTTPS** | Simpler than A2A. |

## §S7.6 Security Considerations

- **2/2 founder agreement enforced cryptographically.** Both sign; partial doesn't promote; offline-verifiable audit.
- **HARD STOP is META.** Not voted; not scheduled; cannot be non-founder triggered. Propagates via S5.
- **Consent revocation absolute.** No §0.1 autonomy exception overrides. Only affected subject can re-consent (if policy allows).
- **Disagree-or-commit prevents minority capture.** Loser who refuses to commit can be society-voted removed.
- **Quorum size dynamic: 3-of-5 → 5-of-9.** Never shrinks below 3 without foundation ceremony.
- **Founder retirement = meta-Tier 4.** 7-day cooling-off; founder can rescind.
- **Spawn cert static + versioned.** Refuses unsigned/expired/anti-persona roles.
- **Role projection, not full memory inheritance.** New agent gets fresh S4 schema + role-projected context only.
- **Audit log immutable + exportable.** Hash + evidence + S5 event ID.
- **Rate limiting on proposals.** Default 10/member/24h.
- **Replay protection.** Signed decisions include nonce + recent S5 block hash.
- **Founder identity bound at ceremony.** Adding = meta-Tier 4.

## §S7.7 Failure Modes & Recovery

| Failure | Detection | Recovery |
|---|---|---|
| Founder key compromise | Anomalous vote; self-report | Emergency HARD STOP; rotate (2/2 + 7d); revoke old. |
| HARD STOP miss instance | S13 heartbeat alive but no ACK | Quarantine; replay HARD STOP. |
| Quorum cannot form | Voting cannot reach threshold in 7d | Foundation ceremony; pause Tier 3+; Tier 1–2 continue. |
| Discord DM HARD STOP spoof | Signature check fails | Log spoof attempt; security alert. |
| Member unreachable | Heartbeat missed 24h | Status `unreachable`; alternate seated or escalate if founder. |
| Spawn cert dispute | Founder disagrees | Spawn blocked; meta-foundation; S5 records. |
| Quorum capture | Coordinated votes flag | Founder override; flag for review. |
| Consent revocation race | Two for same subject | First-write-wins by S5 order; second no-op + audit. |
| Decision log corruption | Hash chain fails | Quorum audit; recover from S3 snapshot; re-vote after corruption. |
| Discord rate limit emergency | HTTP 429 | Vote retries backoff; deadline +24h. |

## §S7.8 Dependencies

- **Hard:** S5, S1, Discord identity binding.
- **Soft:** A2A inter-society (P34+), S6, S13.
- **Upstream:** S1 (spawn), S6 (grants), S8 (mutation routing), S9 (policy), S10 (revenue approval), S13 (metrics), S15 (audit exports).

---

# §S8 S8: Self-Evolution & Mutation Governance (Layer 3)

## §S8.1 Purpose

S8 governs **how the Hermes Society may modify itself**. It decides whether a proposed change to a Hermes's behavior, memory, persona, tools, or safety boundaries is allowed to proceed, and if so under what conditions. The Layered Mutability paper (arXiv 2604.14717) measured a **0.68 hysteresis ratio**: reverting the persona file after 23 days of memory accumulation only restored 32% of baseline. This forces S8 to govern at the **deepest active mutable layer (memory)**, not the most visible (persona file).

S8's keystone primitive is the **Ratchet non-divergence gate**: bounded improvement + retirement threshold means capability can climb but cannot degrade below prior benchmark. With Ratchet, Tier 1–2 modifications are fully autonomous. Without it, autonomous self-modification is unsafe.

S8 also implements the explicit gate between **§0.1 P20 Living Autonomy Kernel** and the society governance layer: "living kernel" mutations go through §0.1 policy gates (backup → canary → smoke test → rollback); "society" mutations go through S7+S8 joint.

## §S8.2 Components

1. **Five-Layer Mutability Map** — Pretraining (frozen) / Alignment (slow, founder-only) / Persona (medium, society-voted) / Memory (fast, Ratchet-gated) / Weight-level (fastest, Ratchet+canary).
2. **Ratchet Engine** — non-divergence gate; runs benchmark (`persona_drift`, `capability_smoke`, `safety_invariants`, `consistency`); refuses if below retirement threshold.
3. **Four-Tier Permission Model** — Tier 1 (auto, Ratchet+canary): tools, scratchpads. Tier 2 (Ratchet+auto): prompt scaffolds, retry policies. Tier 3 (society vote): persona narratives, memory schemas, long-term content. Tier 4 (founder-only): safety boundaries, hard limits, system prompt root, surveillance/consent flags.
4. **Four-Stage Promotion Pipeline** — shadow (parallel run, no effect) → canary 5–10% → 50% → 100%. Each stage has automated rollback.
5. **Drift Detection Triad** — SyncScore EWMA λ≈0.3 (real-time); persona_drift (daily regression, 100+ turn); Layered Mutability fingerprint (quarterly).
6. **Mutation Audit Trail** — `mutation_id`, `proposer`, `tier`, `before_hash`, `after_hash`, `benchmark_before/after`, `approval_chain`, `rollback_path`, `canary_log`. Hash-chained to S5.
7. **Rollback-Before-Promote Validator** — tested rollback in shadow; confirms state restoration.
8. **Canary Engine** — N% traffic routing; threshold comparison; abort + manual override.
9. **Mutation Proposal Pipeline** — proposal YAML → tier classification → appropriate workflow.
10. **SemVer for Persona** — MAJOR.MINOR.PATCH. PATCH auto (Ratchet); MINOR society vote; MAJOR founder.
11. **Model Version Pinning** — explicit per-agent config (e.g., `claude-haiku-4-5-20251001`); upgrades = Tier 2 Ratchet-gated.
12. **Self-Improvement Memory** — append-only history of all mutations, including failed.

## §S8.3 Data Flow

**Tier 1–2 autonomous:** proposal YAML → pipeline → Ratchet (before vs after benchmark) → Rollback validator (shadow) → Canary 5–10% (N hours) → 50% → 100% → audit → S5 `mutation.promoted`.

**Tier 3 society-voted:** pipeline → S7 society vote 3-of-5 → Ratchet → Rollback → Canary → Promote → S5 `mutation.society_approved + mutation.promoted`.

**Tier 4 founder-only:** pipeline → S7 founder 2/2 → Ratchet → Rollback w/ founder attestation → Canary extended window → 7-day cooling-off for safety boundaries → Promote.

**Drift detection (continuous):** every S8 event → SyncScore EWMA → threshold check → pause autonomous mutations if breach → S5 `drift.alert`.

## §S8.4 Interfaces

**Consumes:** S1 (runtime/persona/memory), S5 (mutation/audit/HARD STOP), S6 (memory schema), S7 (tier routing/founder), S13 (drift metrics), operator (manual override).

**Exposes:** `propose_mutation`, `approve_mutation`, `promote_mutation`, `rollback_mutation`, `drift_status`, `benchmark_run`, `persona_version`, `audit_export`.

## §S8.5 Technology Choices

| Layer | Choice | Rationale |
|---|---|---|
| Benchmark | **pytest + custom plugin** | Reuses test infra; deterministic. |
| Ratchet | In-process Python module ~300 LoC | Simplicity; logic is `before - after >= retirement`. |
| Canary router | Weighted LB at S1 dispatch | Already in S1; S8 sends promotion events. |
| Drift fingerprint | Embedding + JSD on memory-graph | Per Layered Mutability methodology. |
| SyncScore | EWMA in Redis + S5 flush | Sub-ms; per synthesis §4.8. |
| Proposal format | Signed YAML | Matches S7. |
| Audit | S5 event store | Immutable, queryable. |
| Rollback | Git SOUL; pg_dump memory; revert PR | Mature, auditable. |
| SemVer | Python `semver` | Standard. |
| Model pinning | Per-agent config | Already in S1 substrate. |

## §S8.6 Security Considerations

- **Ratchet is non-negotiable.** No mutation proceeds if any benchmark metric below retirement. No override except HARD STOP.
- **Rollback mandatory before promotion.** Tested rollback in shadow; S8 refuses untested/failed.
- **Drift detection is layered.** SyncScore (real-time) + persona_drift (daily) + Layered Mutability (quarterly). Alert halts autonomous promotion.
- **Tier 4 founder-only.** No Ratchet override; safety/hard limits/system prompt root/consent flags.
- **Tier 4 7-day cooling-off.** Founders can rescind after 2/2 sign before effect.
- **Tier 3 founder override.** 24h post-vote, written rationale logged.
- **Model version pinning prevents silent degradation.** Ratchet benchmark includes model-version-difference as feature.
- **Audit trail immutable + signed.** Proposer + approver + before/after hashes + benchmarks.
- **HARD STOP halts autonomous promotion.** No new mutations; canaries freeze at current state.
- **Consent revocation affects Ratchet.** Cannot use revoked scope data in benchmarks.
- **Self-improvement history read-only.** Append-only; never edited.
- **Living kernel vs society gate.** Explicit gate: living kernel = §0.1; society = S7+S8 joint.

## §S8.7 Failure Modes & Recovery

| Failure | Detection | Recovery |
|---|---|---|
| Ratchet false positive | Premature threshold | Calibration review; human override w/ rationale. |
| Ratchet false negative | Drift alert post-promotion | Auto rollback; root cause; tighten if recurs. |
| Canary infrastructure fail | Stage timeout | Rollback; alert; mark `canary_failed`. |
| Benchmark non-deterministic | High variance | `seed=fixed`; rerun N; median. |
| Drift alert flood | SyncScore too tight | Recalibrate λ + threshold; quarterly. |
| Tier 4 cooling-off bypass | Timestamp check | Reject; security event; founder notify. |
| History tampering | Hash chain fails | Quorum audit; restore from S3; re-vote post-tamper. |
| Model version mismatch | Heartbeat reports actual | Halt agent; refuse run; operator alert. |
| Founder override misuse | Frequent override pattern | Synthesis review; meta-foundation if persists. |
| HARD STOP during canary | S5 key | Freeze; rollback if stop persists; resume if lifted <24h. |
| Proposer signature theft | Anomalous mutation | Emergency halt; key rotate; S5 audit. |

## §S8.8 Dependencies

- **Hard:** S1, S5, S7, S6.
- **Soft:** S13, S4, S15.
- **Upstream:** S1, S6, S7, S13, S15.

---

# §S9 S9: Autonomous Wallet & Finance (Layer 3)

## §S9.1 Purpose

S9 is the financial substrate of the Hermes Society. It defines how the society holds, spends, monitors, and accounts for money. Synthesis constraints: wallet float ≤ ~$10 USD-equivalent on Base; agent LLM never has direct raw private key; all spending policy-gated; every transaction hash-chained to S5. S9 is where the Edge & Node 2026 incident ($47K lost in 11 days from recursive loop) becomes structural mitigation.

S9 implements three-layer wallet (cold Safe multisig, hot MPC, ephemeral EIP-7702 session keys) + six-tier spending policy (Dust/Micro/Small/Medium/Large/Critical). Wallet is a **company asset**, default 0, max ~$10 top-up.

S9 also materializes the **decision ≠ execution** principle: agent LLM *requests* signature; external policy engine (MPC signer) *decides* whether to sign. LLM never holds key.

## §S9.2 Components

1. **Cold Treasury** — 2-of-3 Safe multisig on Base. Key 1 = Faiz Ledger HW. Key 2 = AWS CloudHSM. Key 3 = offline paper backup.
2. **Hot Operating Wallet** — MPC (Turnkey or Coinbase Agentic) with policy engine; works $0–$10 USD.
3. **Session Keys (EIP-7702)** — per-task scoped, expiring; for x402 micro payments.
4. **Receiving Smart Contract** — no key; only releases to hot via policy.
5. **Policy Engine** — allowlist (USDC, ETH, Base; allowlisted contracts only); daily cap $10; velocity 5 tx/hr, 50 tx/day; per-tx tier.
6. **Spending Tier Table** — Dust <$0.10 (auto) / Micro $0.10–$1 (auto+alert) / Small $1–$10 (auto+alert) / Medium $10–$100 (1 human 24h) / Large $100–$1K (2-of-3 + 24h timelock) / Critical >$1K (2-of-3 + 7d timelock + founder OOB).
7. **Circuit Breaker** — pausable; triggers: anomaly, HARD STOP, drift, Ratchet fail, founder manual.
8. **Beancount Ledger** — plain-text, git-versioned, append-only; `bean-check` daily.
9. **On-Chain Guardrails (5)** — spending limit; rate limit; destination whitelist; time-lock; audit (S5 hash chain).
10. **MPC Signer Integration** — Turnkey/Coinbase Agentic; LLM requests; MPC evaluates; LLM never holds key.
11. **Float Top-Up Endpoint** — Faiz-only signed command to send USDC from cold.
12. **Wallet State Snapshot to S3** — periodic; S3 Object Lock COMPLIANCE 7-year.
13. **Revenue Routing** — receiving contract routes to hot per policy; 100% to company.
14. **Founder Notification Channel** — Medium/Large/Critical + circuit-breaker → founder Discord channel.
15. **Daily Integrity Job** — `bean-check` reconciles Beancount vs on-chain.

## §S9.3 Data Flow

**Routine micro-spend:** agent `payment_intent(recipient_contract, amount)` → policy engine (amount tier, dest allowlist, daily cap, velocity) → MPC signer (re-verify, sign) → broadcast to Base → on success: S5 `wallet.spend` → Beancount entry → audit hash-chained.

**Medium/Large/Critical:** agent `payment_intent(≥ $10)` → policy holds, routes to founder queue → founder receives Discord notif → founder approves via signed command → time-lock 24h/7d → MPC signs + broadcasts → S5 `wallet.spend.signed`.

**Circuit breaker trigger:** anomaly detector → breaker pauses; pending tx queued → S5 `wallet.circuit_breaker` → founder notif → investigates.

**Float top-up:** Faiz sends USDC from cold via signed endpoint → S5 `wallet.topup` (Faiz-signed) → hot balance update → Beancount → S3 snapshot COMPLIANCE.

## §S9.4 Interfaces

**Consumes:** S1 (payment_intent), S7 (founder policy/circuit), S8 (Ratchet failure → breaker), S10 (inbound USDC), S5 (HARD STOP), operator (top-up).

**Exposes:** `payment_intent`, `wallet_state`, `policy_update` (Tier 4), `circuit_breaker`, `topup`, `balance`, `audit_export`.

## §S9.5 Technology Choices

| Layer | Choice | Rationale |
|---|---|---|
| Chain | **Base** (L2, OP Stack) | Low fees; x402 native; Coinbase ecosystem. |
| Wallet | **Safe (cold) + Turnkey MPC (hot) + EIP-7702 sessions** | Decision ≠ execution enforced. |
| Policy | **Turnkey policy engine** | Off-chain; signer rejects non-compliant. |
| Ledger | **Beancount** (git-versioned) | Append-only; `bean-check` daily; legal record. |
| Receiving | **Smart contract** (no key) | Reduced attack surface; policy-gated release. |
| Daily integrity | `bean-check` cron + reconciliation | Detects drift in 24h. |
| Snapshot | **S3 Object Lock COMPLIANCE** 7y | Legal-defensible WORM. |
| Top-up | **Faiz-only signed** | Operator-only; no agent. |
| Signing | **Ed25519** off-chain; **secp256k1** on-chain | Standard. |
| Notif | **Discord private channel** | Operator-attentive; S2 stack. |
| Audit | S5 event store | Immutable, queryable, RTM-traceable. |

## §S9.6 Security Considerations

- **Decision ≠ execution architecturally enforced.** LLM requests; MPC evaluates + signs; no code path for LLM to sign.
- **Asset allowlist at signer.** Only USDC, ETH, Base. Other tokens/chains refused.
- **Destination allowlist.** EOA blocked by default; only allowlisted contracts.
- **Daily cap $10.** Enforced at policy engine; even Medium cannot push above.
- **Velocity cap (5 tx/hr, 50 tx/day).** Prevents Edge & Node 2026 loop.
- **Time-locks > $100 (24h), > $1K (7d).** Founder review + rescind window.
- **Circuit breaker auto on anomaly.** Investigation required.
- **HARD STOP halts wallet.** Policy engine refuses until stop lifted.
- **Beancount git-versioned + append-only.** Git history = legal record.
- **Cold offline; no hot authority over cold.** Top-up = Faiz HW sig.
- **MPC key sharded.** No single party holds full key.
- **Reentrancy guard on receiving contract.** Checks-effects-interactions.
- **Slippage protection.** Max 0.5% at policy.
- **MEV protection.** Private mempool (Flashbots Protect on Base).
- **Audit non-repudiable.** Every tx signed.
- **Consent revocation propagates.** `consent.revoked` → S9 stops derived tokens/addresses.

## §S9.7 Failure Modes & Recovery

| Failure | Detection | Recovery |
|---|---|---|
| MPC signer outage | Sign timeout | Queue + backoff; >1h escalate. |
| Policy misconfig | Audit tier misassign | Tier 4 founder update; historical flagged. |
| Beancount corruption | `bean-check` fail | Restore from git; reconcile; identify gap. |
| On-chain reorg | Receipt block mismatch | Wait finality ~15min; re-record canonical; S5 audit. |
| Receiving contract exploit | Unexpected state | Pause; emergency revoke; cold untouched. |
| Founder key compromise | Anomalous top-up | Emergency HARD STOP; rotate; review in-flight. |
| Daily cap bypass attempt | Spend > $10 | Auto-revert if possible; alert; breaker. |
| Circuit breaker stuck | Paused > 24h | Founder escalate; dual; HARD STOP. |
| Time-lock bypass | Tx pre-elapsed | Policy refuses; security event. |
| MEV attack | Slippage breach | Revert; retry tighter; alert. |
| Snapshot fail | Daily job | Retry; operator alert; ledger = truth. |
| Float exhaustion | Balance = 0 | Signals S10 to search revenue. |
| Agent x402 loop | Velocity triggers breaker | Auto-pause; founder. |

## §S9.8 Dependencies

- **Hard:** S5, S7, S11.
- **Soft:** S10, S13, S2, S1.
- **Upstream:** S1, S10, S13, S15, S3.
- **External:** Base RPC, Turnkey, Safe, Discord, Beancount.

---

# §S10 S10: Revenue Search & Monetization (Layer 3)

## §S10.1 Purpose

S10 turns idle compute + agent capabilities into revenue when wallet is empty. Synthesis constraints: x402 on Base = lowest-friction; 76% priced ≤$0.10; supply gap (4,400 buyers vs 477 sellers) favors seller; idle USDC sweeps to Morpho for 4.5–7% APY; revenue must respect ToS + safety + consent; revenue is S7-gated + S9-tier-limited.

S10 implements 5 revenue channels ranked by effort/margin: (1) x402 data APIs (primary); (2) Morpho/Aave yield (passive); (3) Virtuals Protocol ACP; (4) x402 LLM proxy; (5) A2A specialist services.

Also implements **wallet-empty behavior rule**: society autonomously searches revenue only when balance < $1 for > 24h.

## §S10.2 Components

1. **Wallet Threshold Monitor** — polls S9 every 15min; <$1 >24h → `revenue.search_authorized`; >$1 → `revenue.search_paused`.
2. **Revenue Channel Catalog** — channel_id, name, effort/margin, status, tos_constraints, consent_constraints, s9_tier.
3. **x402 Endpoint Manager** — wraps `@x402/express`; data-wrapping endpoints. Primary near-term.
4. **Morpho Yield Router** — sweeps idle USDC to vault; monitors APY (4.5–7% range); enforces floor APY.
5. **Virtuals Protocol ACP Adapter** — registers skills on ACP marketplace.
6. **x402 LLM Proxy** — wraps LLM calls behind paywall; margin-sensitive.
7. **A2A Specialist Services** — exposes Hermes capabilities inter-org; requires A2A protocol (deferred P34+).
8. **Revenue Approval Router** — L1 (<$1) autonomous; L2 ($1–$5) society vote; L3+ founder.
9. **Margin Tracker** — per-request cost/revenue; per-day margin; model downgrades if cost > revenue.
10. **ToS/Consent Compliance Filter** — pre-check: ToS allows; no surveillance; no relationship memory; no PII; no intimate.
11. **Revenue Audit Logger** — every activity to S5 with: timestamp, channel, amount, margin, recipient, policy_ref, consent_ref, founder_approval_ref.
12. **Beancount Revenue Sync** — daily on-chain → Beancount; tags per channel; reconciles S9.
13. **Channel Quota Manager** — caps per channel (e.g., x402-data ≤$5/day).
14. **Recipient Identity Filter** — only smart contracts; allowlist per channel; Tier 4 for new.

## §S10.3 Data Flow

**x402 sale (L1):** buyer hits endpoint → 402 with USDC amount + address → buyer signs `transferWithAuthorization` → retries with payment header → endpoint verifies on-chain → serve data → S5 sale log → Beancount → margin tracked.

**Morpho yield sweep (L0 passive):** idle > 1 USDC > 6h → policy check → MPC signs `approve` → MPC signs `deposit` → vault shares → S5 `wallet.yield.deposit` → Beancount asset move → periodic harvest claim.

**Channel enable (L2+ society-voted):** proposal → S7 society vote → S8 Ratchet check → S5 approval → channel `active` → budget allocated → ToS filter prime → earn → S5 `revenue.channel_enabled`.

**Revenue search authorization:** monitor <$1 >24h → S5 `revenue.search_authorized` → activates paused per policy → S9 hot wallet receives → balance >$1 >24h → S5 `revenue.search_paused` → deactivate ephemeral; yields remain.

## §S10.4 Interfaces

**Consumes:** S9 (balance/breaker/top-up), S5 (HARD STOP/governance/consent), S7 (channel enable/policy), S8 (Ratchet/drift), S1 (data feeds/skills), S2 (operator override), external (x402 facilitator, Morpho, Virtuals).

**Exposes:** `x402_endpoint_register`, `x402_serve`, `revenue_state`, `channel_enable`, `margin_report`, `tos_check`, `audit_export`.

## §S10.5 Technology Choices

| Layer | Choice | Rationale |
|---|---|---|
| x402 | **`@x402/express`** (Coinbase) | 2–4hr path to first dollar. |
| Chain | **Base** | Native x402, low fees, Coinbase. |
| Yield | **Morpho** | 4.5–7% APY, audited, on Base. |
| Marketplace (alt) | **Virtuals ACP** | Differentiated skills; lower priority. |
| LLM proxy | Custom wrapper around 9Router | Per-request margin; model downgrade. |
| Margin | S5 + Beancount | Real-time cost vs revenue. |
| Compliance | YAML rule engine + regex | ToS + consent + PII per channel. |
| Channel quota | PostgreSQL table | Simple, auditable, society-voted. |
| Audit | S5 event store | Immutable, RTM-traceable. |
| Recipient filter | PG allowlist + on-chain | Defense in depth w/ S9. |

## §S10.6 Security Considerations

- **ToS compliance mandatory.** Explicit recent signed assertion per data source; filter re-checks every req.
- **Consent compliance mandatory.** No data requiring consent under consent ledger.
- **No PII in responses.** Scanned before serving.
- **No surveillance data in revenue products.** Hard invariant.
- **No relationship memory in revenue.** Per S4 invariant.
- **Recipient allowlist.** Only allowlisted contracts. New = Tier 4 founder.
- **Per-channel quotas.** Single-channel dependency prevented.
- **Margin floor (30%) enforced.** Below → auto-pause; society-voted resume.
- **Revenue logged twice.** S5 + Beancount; daily reconcile.
- **HARD STOP halts revenue.** All pause; pending refunded; founder notif.
- **Consent revocation propagates.** `consent.revoked` → channel deactivated ≤1min.
- **No social engineering.** x402 never requests buyer identity beyond payment.
- **Operator-intimate data never sold.** Per AGENTS.md invariant.
- **Settlement finality.** Sales final once confirmed; refunds only for breaker or HARD STOP.
- **Price floor $0.001 USDC.** Below rejected (LLM cost > revenue).

## §S10.7 Failure Modes & Recovery

| Failure | Detection | Recovery |
|---|---|---|
| x402 facilitator outage | Timeout | 503; buyer retries; S5 audit. |
| Morpho vault exploit | TVL anomaly | Withdraw subject to lockup; quarantine; review. |
| Channel margin collapse | < 30% floor | Auto-pause; S5; society vote. |
| ToS source revoked | 403 / page change | Pause; manual alt source. |
| Recipient contract exploit | Unexpected state | S9 breaker; S10 pause; review. |
| x402 buyer dispute | Chargeback/fraud | Refund (founder approval); S5; reputation. |
| Wallet threshold false | Transient dip | No action; 24h window. |
| APY drop below floor | Morpho monitor | Sweep back; switch vault. |
| HARD STOP during sale | S5 cascade | Abort; refund; founder notif. |
| Operator override (emergency) | Discord command | Pause; S5 event; society vote to resume. |
| Audit mismatch | S5 vs Beancount disagree | Reconcile; drift; root cause; escalate. |
| Quota exhausted (legit) | Daily reached | Auto-pause; society vote to raise. |

## §S10.8 Dependencies

- **Hard:** S9, S5, S7, S8.
- **Soft:** S1, S2, S13, S15.
- **Upstream:** S9, S3, S13, S15, RTM.
- **External:** x402 facilitator, Morpho, Base RPC, Virtuals (optional), ToS docs.

---

# §S11 S11: S3 Backup & Disaster Recovery (Layer 4)

## §S11.1 Purpose

S11 is the **source-of-truth tape** for the Hermes Society. Every byte that, if lost, would prevent the society from resuming operation must land in S3 under Object Lock in COMPLIANCE mode — a true WORM guarantee that even the AWS root principal cannot delete before retention expiry. Per Faiz lock and synthesis §4.11, backup is **mandatory**. Binding targets: **RPO ≤ 1 hour, RTO ≤ 4 hours**.

S11 handles full backup lifecycle: capture (pg_dump + WAL archiving, Redis RDB + AOF, filesystem), encrypt (AES-256-GCM, SSE-KMS), replicate (cross-region active/passive), verify (weekly restore drill on staging), audit (every backup event hash-chained to S5).

## §S11.2 Components

1. **S3 Primary Bucket (lead region)** — WORM tier: wallet state, policy config, decision logs, Beancount, evidence, consent receipts, audit trail, mnemonic exports (encrypted). COMPLIANCE mode, 7-year retention. Versioning + MFA-delete disabled. Cross-region replication via S3 CRR.
2. **S3 Secondary Bucket (dr region)** — WORM replica; same retention; different AWS account under same org. Only dr-account's audited break-glass affects it.
3. **S3 Governance Bucket** — Wallet snapshots that may legitimately need cleanup. GOVERNANCE mode, 90-day. Bypass logged + MFA.
4. **PostgreSQL Backup Pipeline** — (a) `pg_basebackup` daily 02:00 UTC; (b) continuous WAL via `archive_command` to S3; (c) hourly `pg_dump -Fc` for flexibility.
5. **Redis Backup Pipeline** — (a) RDB every 15min; (b) AOF rewrite daily with `appendfsync everysec`.
6. **Filesystem Artifact Sync** — `restic` content-defined chunking, dedup, AES-256, ships `/var/lib/hermes/{config,artifacts,evidence}/` nightly.
7. **Backup Scheduler (`backupd` daemon)** — systemd-supervised YAML cron; single writer; never deletes local before S3 PUT ack.
8. **Restore Drill Harness** — Weekly cron: ephemeral EC2 in dr region, restore most recent, `pg_dump --schema-only` + known query, emit `AE.dr.restore_drill_pass|fail`. Drill report in `evidence/dr-drills/`.
9. **KMS Key Hierarchy** — Per-agent DEK wrapped by society KEK in AWS KMS. DEK rotates 90d; KEK 365d. `kms:Decrypt` requires `SessionTag=hermes:agent_id`.
10. **Backup Event Emitter** — Thin client emits `AE.backup.{started,completed,failed,verified}` with SHA-256; hash is next audit chain link.

## §S11.3 Data Flow

**Forward (capture):** PG write → WAL sealed + uploaded ≤5s → `backupd` triggers `pg_basebackup` 02:00 UTC → hourly `pg_dump -Fc` → Redis AOF appends; RDB push 15min → `restic backup` 03:00 UTC → `AE.backup.completed` to S5.

**Reverse (restore):** DR trigger → `backupd restore --timestamp=<ts>` → most recent base + WAL replay + `pg_dump --schema-only` validate → logical dumps selective → Redis RDB + AOF tail → `restic restore` + SHA-256 verify → `AE.dr.restore_completed`.

**Cross-region:** S3 CRR async (5–15s lag); acceptable because S5 replicated; promotion is manual runbook (not automatic region failover at $10-float scale).

## §S11.4 Interfaces

**Exposes:** `S11.write_artifact` (PUT w/ auto-encrypt, returns URI + SHA-256); `S11.read_artifact` (GET + KMS Decrypt); `S11.hold_worm` (COMPLIANCE lock); `S11.dr_status` (Prometheus exporter); `S11.key_rotate` (DEK/KEK rotation).

**Consumes:** `S5.publish_event`; `S20.kms` (DEK wrapping, future); `S14.deploy_secret` (restic password, KMS ARNs).

## §S11.5 Technology Choices

| Component | Tool | Rationale |
|---|---|---|
| Object storage | **AWS S3** (MinIO fallback) | Only major with native Object Lock COMPLIANCE. |
| PG backup | `pg_basebackup` + `pg_dump` | Mature; `barman` rejected for single-instance complexity. |
| Redis backup | Native RDB + AOF | No third-party dep. |
| Filesystem | **restic 0.16+** | Dedup, native S3, AES-256 client-side; `borg` rejected. |
| Orchestrator | **backupd** (custom Go ~2k LoC) | Small, auditable. |
| KMS | **AWS KMS** + CMK per society + alias per agent | Industry standard; envelope encryption; IAM Session Tags. |
| Monitoring | node_exporter + `/dr-metrics` | Standard Prometheus scrape. |
| Restore drill | AWS EC2 t3.small + Ansible | Ephemeral, reproducible. |

## §S11.6 Security Considerations

- **Object Lock COMPLIANCE is non-negotiable** for: wallet state, ledger, audit chain, consent receipts, evidence. Even Faiz + Guinevere cannot delete before retention. Defense against insider deletion.
- **GOVERNANCE mode** only for ephemeral session-key snapshots + policy cache. Bypass logged + MFA.
- **Mnemonic exports** encrypted client-side AES-256-GCM w/ per-export DEK wrapped by KMS. DEK never plaintext outside export.
- **KMS access least-privilege.** Per-agent IAM role w/ `SessionTag=hermes:agent_id`. Backup operator = `GenerateDataKey`/`Encrypt` only.
- **Bucket public access blocked** (all 4 account-level settings).
- **S3 access logs** to separate log-bucket COMPLIANCE; Loki.
- **Versioning + MFA-Delete disabled** in COMPLIANCE (supersedes both).
- **Region:** primary ap-southeast-1; dr us-east-1.
- **No SOPS/age keys, no raw credentials, no decrypted values, no intimate data, no surveillance data** ever written to S3.
- **Compliance:** 7y aligns w/ financial ledger; COMPLIANCE aligns SEC 17a-4(f) WORM.

## §S11.7 Failure Modes & Recovery

| Failure | Detection | Recovery | RTO/RPO impact |
|---|---|---|---|
| Single WAL lost | `archive_command` non-0 | `pg_basebackup` + replay; logical fallback | RPO +1h; RTO +30m |
| S3 primary down | 5xx spike | CRR read-only warm; manual promote | RTO ≤4h; RPO ≤1h |
| S3 secondary down | CloudWatch alarm | Primary reads; wait | RTO 0; RPO 0 |
| KMS key compromise | CloudTrail anomaly | Rotate KEK; re-wrap DEK; audit decrypt | RTO 0; sec event |
| `backupd` crash | systemd restart | Next tick; missed flag | RPO +1h; RTO 0 |
| Restore drill fails | `AE.dr.restore_drill_fail` | P1 incident; review | DR confidence lost |
| Restic repo corruption | `restic check` | Secondary or peer; rebuild | RTO ≤4h; RPO ≤1h |
| Wrong bucket tier | Audit log review | Cannot migrate (Object Lock); future correct | No data loss |
| Bucket policy misconfig | AWS Config | Auto-revert; alert | Prevention |

**DR runbook (P0):** (1) confirm primary failure; (2) stand up EC2 in dr; (3) restore PG base + WAL replay; (4) restore Redis RDB; (5) restore FS via restic; (6) DNS update Route 53; (7) replay S5 from checkpoint; (8) verify Hermeses reconnect; (9) emit `AE.dr.region_promoted`; (10) postmortem ≤24h.

## §S11.8 Dependencies

- **S1** — `backupd` runs as systemd on primary.
- **S2** — DR status via `/dr` slash.
- **S5** — Hash-chained backup events + restore verification.
- **S9** — Wallet state most critical target.
- **S13** — DR metrics + drill alerts + restore SLO.
- **S14** — `backupd` deployed; secrets from S14 Vault.
- **S15** — Drill reports land in evidence.
- **AWS org topology** — Faiz decision.

---

# §S12 S12: Model Pool & LLM Gateway (Layer 4)

## §S12.1 Purpose

S12 is the **single chokepoint** through which every Hermes makes LLM calls. The society's economic viability — and its failure modes around cost runaway — live here. Without a shared gateway, each Hermes would independently hit provider APIs, costs would fragment, failover would be uncoordinated, and rate limits inconsistent. Gateway primary jobs: (a) **route** to optimal model by task; (b) **enforce quotas** so runaway can't burn runway; (c) **fail over** to fallback when primary degraded; (d) **track cost** per request → Beancount (S9); (e) **circuit-break** failing providers.

S12 operationalizes the **9Router substrate**: GPT-5.5 primary (via 9Router), DeepSeek V4 Flash sub-agents, Ollama fallback. **Stateless** in request path; state in Redis (counters, circuit) + PG (quotas, costs). Horizontal scaling trivial; no single point of failure.

## §S12.2 Components

1. **LLM Gateway Daemon (`llmgw`)** — Python async FastAPI under systemd; one instance per VPS; Unix socket (or localhost HTTP).
2. **Model Pool Registry** — `model_pool.yaml` per `hermes-config/`: model ID, provider, cost/1k in+out, ctx window, tier (fast/balanced/heavy), fallback chain, **explicit version pin**.
3. **Router** — selects based on: tier hint, task-type hint, provider health (circuit breaker), cost guard (downgrade at 80% budget).
4. **Quota Manager** — (a) per-Hermes daily token (5M default); (b) per-Hermes monthly USD ($50 default); (c) society daily token (100M cap). Redis INCRBY + PG snapshot for durability.
5. **Circuit Breaker** — per-provider state machine CLOSED → OPEN → HALF_OPEN. Trip: 5 consecutive errors, 50% error/60s, p99 >10s. Recovery: 30s OPEN before HALF_OPEN probe.
6. **Rate Limiter** — Token-bucket per Hermes (60 req/s, burst 120) + per-provider awareness (OpenAI Tier 3 = 5k RPM). Redis.
7. **Cost Tracker** — every successful call → `llm_cost_log` row (PG): ts, hermes_id, model_id, in/out tokens, cost_usd, request_id, trace_id. Beancount importer nightly.
8. **Budget Guardrail (runtime)** — per-request: cumulative >$0.50 → downgrade `fast`; >$2.00 → terminate `BudgetExceeded`. Per-agent wall-clock 5min/turn, iteration 50, token 200k.
9. **Provider Adapters** — `anthropic`, `openai`, `deepseek`, `ollama`; uniform `complete`, `stream_complete`, `embed`.
10. **Observability Hooks** — Prometheus metrics + OpenTelemetry spans w/ `trace_id` for S13.

## §S12.3 Data Flow

**Request:** Hermes `llmgw.complete(messages, tier="balanced", task="code_review")` → quota check → router (model select + circuit breaker check) → rate limiter → budget guardrail → provider adapter → stream response → cost log → quota increment → return w/ `X-Request-Id`, `X-Model-Used`, `X-Cost-USD`.

**Failure:** provider 5xx/timeout → circuit counter increment → threshold → OPEN; future calls skip → `AE.llm.provider_failure` → return `ProviderUnavailable` + fallback hint.

**Quota breach:** daily cap → `QuotaExceeded` for all subsequent until reset → `AE.llm.quota_exceeded` → S13 alert → Hermes `agent.quota_paused`.

## §S12.4 Interfaces

`/v1/chat/completions` (S1, S2), `/v1/embeddings` (S6), `llm_cost_log` (S9), `/metrics` Prometheus (S13), `model_list` YAML (S15).

**Consumes:** `S5.publish_event`, `S20.kms` (future), `S14.deploy_secret`.

## §S12.5 Technology Choices

| Component | Tool | Rationale |
|---|---|---|
| Framework | **FastAPI** (Python 3.11+) | Async-native, OpenAI-compatible. |
| LLM clients | `anthropic`, `openai`, `httpx` (DeepSeek/Ollama) | Official SDK where mature. |
| Rate limiter | **Redis** token-bucket Lua | Sub-ms, atomic. |
| Circuit breaker | In-process + Redis mirror | Local hot; Redis for cross-instance. |
| Cost tracking | PG append-only `llm_cost_log` | Durable, Beancount-importable. |
| Quota | Redis (counters) + PG (snapshots) | Redis hot; PG durable. |
| Config | `model_pool.yaml` (ruamel.yaml) | Git-versioned + Pydantic. |
| Existing | **9Router** | Wrapping + extension. |
| Local fallback | **Ollama 0.5+ w/ llama3.3:8b** | 2026 standard; VPS; no API cost. |

## §S12.6 Security Considerations

- **Provider keys** sealed SOPS/age (S14); loaded at startup; never logged; never in error messages.
- **Prompt content** DEBUG only; INFO+ metadata only (model, tokens, cost).
- **No operator intimate data in requests** by default; S4 opaque IDs only.
- **Quota tamper-resistant.** Redis counters write-restricted to `llmgw` service account.
- **Circuit breaker observable not modifiable** by Hermeses; `/admin/circuit` requires `hermes:operator`.
- **Cost log append-only** at DB level (revoke UPDATE/DELETE for gateway role).
- **Provider allowlist** at gateway; only providers in YAML reachable.
- **No keys/tokens/decrypted values** in `/metrics`. Metrics on separate port localhost-only.

## §S12.7 Failure Modes & Recovery

| Failure | Detection | Recovery | RTO/RPO impact |
|---|---|---|---|
| Primary down | Circuit OPEN | Auto-failover; `AE.llm.failover` | RTO 0; latency |
| All down | All OPEN | 503; degraded; alert | Degradation; no loss |
| Quota exhausted | Manager | `QuotaExceeded`; Hermes pauses | Pause until reset |
| Budget guardrail | Per-run cost | Auto-downgrade; over → terminate | Per-run only |
| Rate limit | Bucket empty | Wait or 429 `Retry-After` | Bounded |
| Gateway crash | systemd restart | Restart; Redis preserved | 5–10s blip |
| Cost PG down | Retry backoff | Buffer to SQLite WAL; replay | No cost loss |
| 9Router down | Health | Direct provider fallback | Latency |
| Ollama OOM | systemd OOM | Restart smaller model | Degradation |

**Cost runaway circuit:** > 3x normal hourly → halt all `heavy`; only `fast`. `AE.llm.cost_circuit_open` → CRITICAL.

## §S12.8 Dependencies

- S1, S5, S9, S13, S14, S20 KMS (future).

---

# §S13 S13: Observability & Audit (Layer 4)

## §S13.1 Purpose

S13 is the society's **nerve system and memory of last resort**. Every subsystem emits signals into S13; S13 surfaces to operators and produces the **hash-chained audit trail** — the society's legal-defensible record. P22.1 IntegrationAuditWriter is the canonical precedent; S13 extends from per-process to society-level. Dual mission: (a) **observability** (Prometheus/Grafana/Loki/alerts) for real-time operator view; (b) **audit** (hash-chained, immutable) for after-the-fact reconstruction. Two audiences, two retentions: observability 90d hot + 1y cold; audit 7y in S3 COMPLIANCE (per S11).

Audit categories: `agent_lifecycle`, `governance_decision`, `financial_transaction`, `mutation`, `consent_op`, `safety_event` (HARD STOP, drift, sentinel, near-miss Y5). Every event structured JSON w/ `agent_id`, `event_type`, `timestamp_utc`, `payload`, `prev_hash`, `event_hash` (SHA-256 chain) — matches P22.1 IntegrationAuditWriter contract exactly.

## §S13.2 Components

1. **Metrics Pipeline (Prometheus)** — single Prometheus per VPS; scrapes `node_exporter`, `hermes-agent`, `llmgw`, `backupd`, cAdvisor. Retention 15d local; 90d remote (Thanos or remote write).
2. **Dashboards (Grafana)** — per-Hermes: uptime, message rate, p50/p95/p99 latency, rate-limit remaining, LLM cost, error, heartbeat. Society-level: aggregate spend, total error, HARD STOP state, dr-drill status, quota heatmap. All dashboards JSON in git.
3. **Log Pipeline (Loki + Promtail)** — Per-process systemd journal → Promtail → Loki. Structured JSON w/ `agent_id`, `event_type`, `trace_id`. 90d hot, 1y cold via S3.
4. **Audit Trail (PG `audit_log` + S3 COMPLIANCE)** — `id`, `agent_id`, `event_type`, `occurred_at`, `payload JSONB`, `prev_hash`, `event_hash`, `signature`. `event_hash = SHA256(prev_hash || canonical(payload) || event_type || occurred_at)`. Signed w/ agent Ed25519. Hot 7d PG → exported to S3 COMPLIANCE under `audit/{YYYY-MM-DD}/` then deleted PG.
5. **Audit Chain Verifier** — Weekly cron re-walks hash chain. Mismatch → `AE.audit.chain_break` CRITICAL.
6. **Alertmanager** — routes by severity: CRITICAL → PagerDuty; WARN/ERROR → Slack; INFO → Loki. Rules: HARD STOP cascade, wallet breaker, 429 storms, drift breach, S3 backup fail, audit chain break, quota exhaustion, provider failover.
7. **Tracing (OpenTelemetry)** — OTLP-compatible; Hermes per-loop phase, llmgw per call, backupd per job. Trace IDs S1/S2/S5/S9/S12. Tempo + Loki. 7d retention. 100% errors, 10% normal.
8. **SLO/SLA Engine** — Per-Hermes 99% avail, p95 <5s, error <1%. Society 99.5% (per `41-SLO_SLA_ErrorBudget_v1.0.md`).
9. **Drift Detection Triad** — SyncScore (real-time EWMA λ≈0.3); persona_drift (weekly 100+ turn); Layered Mutability fingerprint (quarterly). All feed `drift_detection` dashboard.
10. **Audit Query API** — read-only `GET /audit?agent=<id>&from=<ts>&to=<ts>&type=<event_type>`. PG hot; S3 listing older.

## §S13.3 Data Flow

**Metric:** Hermes `/metrics` → Prometheus scrape 15s → Grafana query + Alertmanager eval → society-level aggregates single-instance.

**Log:** Hermes stdout → journal → Promtail → Loki (index by agent_id + event_type + timestamp) → cold S3 at retention.

**Audit:** `audit.emit(event_type, payload)` → fetch `prev_hash` → compute `event_hash = SHA256(prev_hash || canonical_json(payload) || event_type || occurred_at)` → Ed25519 sign → INSERT `audit_log` (transactional w/ action) → weekly export >7d to S3 COMPLIANCE → weekly verifier re-walk.

**Alert:** rule fires → Alertmanager route by severity + label → CRITICAL PagerDuty; WARN+ Slack → ack silenced, auto-resolve on clear.

## §S13.4 Interfaces

`S13.metrics_scrape`, `S13.dashboard_render`, `S13.log_query`, `S13.audit_emit`, `S13.audit_query`, `S13.alert`, `S13.trace_query`.

**Consumes:** `S5.publish_event`, `S11.dr_status`, `S12.usage_report`, `S14.health`.

## §S13.5 Technology Choices

| Component | Tool | Rationale |
|---|---|---|
| Metrics | **Prometheus 2.50+** | Existing; battle-tested. |
| Dashboards | **Grafana 10+** | Existing; multi-source. |
| Logs | **Loki 2.9+ + Promtail** | Existing; S3 cold native. |
| Tracing | **Tempo** | Loki ecosystem; OTLP. |
| Alerting | **Alertmanager** | Standard. |
| Audit | **PG** (hot) + **S3 COMPLIANCE** (cold) | Existing. |
| Audit signing | **Ed25519** via `cryptography` | Fast, small. |
| Hash chain | **SHA-256** | P22.1 precedent. |
| Drift | Custom Python + Pandas | SyncScore EWMA + benchmark regression. |

## §S13.6 Security Considerations

- **Audit log append-only** at DB level (revoke UPDATE/DELETE except audit-export).
- **S3 audit inherits S11 COMPLIANCE** — no deletion, even root.
- **Ed25519 keys** sealed SOPS, loaded at startup, rotated annually w/ overlap.
- **Grafana + Prometheus + Loki behind OAuth**; no anonymous.
- **Alertmanager routes sealed** (PagerDuty key, Slack webhook) SOPS.
- **Audit query read-only + rate-limited** (60/min/IP); RBAC/ABAC on `agent_id`.
- **No intimate, surveillance raw, decrypted secrets** in metrics/logs. Promtail scrubber redacts: Discord tokens, API keys, private keys, mnemonics.
- **Trace payloads** may contain LLM messages; sampling 10% normal. Full in audit, not trace.
- **Loki/Prometheus disk bounded**: 90d hot, 1y cold.

## §S13.7 Failure Modes & Recovery

| Failure | Detection | Recovery | RTO/RPO impact |
|---|---|---|---|
| Prometheus crash | Restart | Replay WAL; remote write covers | RTO 5m; RPO 15s |
| Loki unavailable | Promtail retry | Local buffer; replay | RTO ≤1h; RPO ≤1h |
| Grafana down | 503 | Restart; stateless | RTO 5m; no loss |
| Audit chain break | Verifier | `AE.audit.chain_break` CRITICAL; manual | Detection ≤7d; RPO ≤7d |
| Alertmanager down | No alerts | Restart; queued | RTO 5m; brief loss |
| OTel down | Trace gaps | Retry backoff | RPO ≤5m |
| S3 audit export fail | Job exit | Retry hourly; CRITICAL 24h | RPO ≤24h |
| Drift false positive | Threshold | Operator review; tuning | Investigation |
| Scrubber bug | Pattern not redacted | Hotfix; rotate leaked | One-time |

**Audit compromise (worst):** chain broken AND S3 missing AND signing key compromised → P0; cold-storage forensic; AGENTS.md §6 escalate to operator + Oracle.

## §S13.8 Dependencies

S1, S5, S9, S11, S12, S14, S15.

---

# §S14 S14: Deployment & VPS Management (Layer 4)

## §S14.1 Purpose

S14 is the **runtime substrate and ship pipeline** for the entire society. Synthesis §4.14: **one large VPS until >32 cores / >64 GB RAM** (Faiz lock). Substrate = systemd (no Docker Compose — overhead with no value at this scale) + cgroup v2 (per-Hermes) + Ansible + Caddy (TLS) + SOPS/age + Vault.

S14 owns: (a) VPS provisioning, (b) per-Hermes systemd unit management, (c) deploy pipeline (pull → build → test → canary → rollout), (d) blue-green deployment, (e) health monitoring (systemd watchdog + Prometheus exporter), (f) networking (reverse proxy, firewall, TLS).

S14 is the **only subsystem allowed to touch host OS** beyond S1 per-Hermes runtime. All host-level changes (kernel params, cgroup layout, systemd drop-ins, firewall) flow through Ansible playbooks, version-controlled, peer-reviewed. Defense against host-level config drift.

## §S14.2 Components

1. **Primary VPS** — Ubuntu 24.04 LTS. Initial: 16 cores / 32 GB / 500 GB NVMe. Scale-up trigger: aggregate cgroup v2 utilization > 80% sustained 7d. Multi-VPS deferred P35+.
2. **Systemd Service Unit per Hermes** — `hermes-{name}.service`: `Type=notify`, `Restart=on-failure`, `RestartSec=5s`, `StartLimitBurst=5`, `StartLimitIntervalSec=60s`, `WatchdogSec=120s`. Drop-in `override.conf` for env.
3. **cgroup v2 Subtree per Hermes** — `hermes.slice/hermes-{name}.slice`: `CPUWeight=200`, `MemoryMax=4G`, `MemoryHigh=3G`, `IOWeight=100`, `PidsMax=400`. `Delegate=yes`.
4. **Ansible Playbook (`provision.yml`)** — idempotent: (a) install apt, sysctl; (b) PG + Redis; (c) cgroup v2; (d) systemd drop-ins; (e) SOPS/age; (f) Prometheus/Grafana/Loki; (g) Caddy TLS; (h) backupd + llmgw; (i) firewall. Two-tier: `bootstrap.yml` (once) + `site.yml` (per-deploy).
5. **Deploy Pipeline (`deploy.sh`)** — (1) `git pull`; (2) `make build`; (3) `make test`; (4) `make canary` (1 Hermes); (5) `make smoke`; (6) `make rollout` (blue-green per Hermes).
6. **Blue-Green per Hermes** — `hermes-{name}-blue`/`hermes-{name}-green` working dirs; active symlinked; deploy swaps symlink + restart; rollback = swap back.
7. **Reverse Proxy (Caddy 2.7+)** — TLS via Let's Encrypt auto-renewal. Routes: `/{hermes}/`, `/metrics`, `/grafana`, `/audit`. HSTS, TLS 1.3.
8. **Firewall (UFW + nftables)** — default deny; allow 22 (Tailscale), 80/443 (Caddy), 9100-9110 (Prometheus localhost/Tailscale), 5432 (PG), 6379 (Redis), 9090 (Prometheus Tailscale), 3000 (Grafana Tailscale).
9. **SOPS + age** — encrypted secrets at rest. `secrets.yaml` canonical; per-Hermes drop-in `EnvironmentFile=/etc/hermes/secrets-{name}.env` (decrypted at deploy).
10. **Vault 1.15+** — runtime secrets; AppRole; 24h tokens for KMS-wrapped DEKs + provider keys. Single-instance + file backend + auto-unseal via cloud KMS (future).
11. **Health Monitoring** — systemd watchdog `WATCHDOG=1` every 30s; missed → SIGKILL; Prometheus exporter on unit state; S13 alerts `failed` >5min.
12. **Scaling Decision Logic** — quarterly + S13-triggered: `MemoryHigh` triggered >50% Hermeses 7d → RAM 2x; `CPUWeight` >80% 7d → cores 2x; >32 cores → multi-VPS eval; >64 GB → multi-VPS eval.

## §S14.3 Data Flow

**Provision (initial):** `ansible-playbook bootstrap.yml -i new-vps` → packages + sysctl (`vm.swappiness=10`, `net.core.somaxconn=1024`) → install PG/Redis/Prometheus/Grafana/Loki/Tempo/Caddy/backupd/llmgw → cgroup v2 → SOPS decrypt → verify (`caddy validate`, `pg_isready`, `redis-cli ping`) → `AE.deploy.provision_completed` to S5.

**Deploy (per Hermes):** `make deploy-hermes NAME=pharsa` → pull → build → test → canary (`hermes-pharsa-green/`, restart, smoke) → if pass: swap symlink to green → restart → `AE.deploy.hermes_rolled_out`.

**Rollback:** post-deploy SLO breach ≤30min → swap back → `AE.deploy.rollback` → postmortem ≤24h.

**Scaling:** S13 dashboard sustained saturation → operator review → `ansible-playbook site.yml --tags=scale` → provider resize → minutes; no restart.

## §S14.4 Interfaces

**Exposes:** `S14.deploy` (`make deploy-hermes NAME=<x>`); `S14.provision` (Ansible); `S14.health` (`node_exporter` + Hermes); `S14.logs` (journal → Promtail → Loki); `S14.deploy_secret` (S11, S12); `S14.unit_state` (systemd status).

**Consumes:** `S20.kms` (future), `S13.metrics` (auto-rollback), `S5.publish_event`.

## §S14.5 Technology Choices

| Component | Tool | Rationale |
|---|---|---|
| OS | **Ubuntu 24.04 LTS** | 5y support; systemd 255+ cgroup v2. |
| Supervisor | **systemd** | No container overhead. |
| Resource | **cgroup v2** | Linux 5.8+ unified. |
| Provisioning | **Ansible 9+** | Declarative, idempotent, agentless. |
| Reverse proxy | **Caddy 2.7+** | Auto-TLS; HTTP/3. |
| Secrets at rest | **SOPS + age** | Battle-tested. |
| Runtime secrets | **HashiCorp Vault 1.15+** | Dynamic; audit. |
| Firewall | **UFW + nftables** | Ubuntu default + advanced. |
| Build | **Make** + shell | No Docker in prod. |
| CI/CD | **GitHub Actions** | Self-hosted runner on VPS. |

## §S14.6 Security Considerations

- **SSH key-only**, password disabled, Tailscale restricted.
- **Tailscale overlay** for operator + Prometheus/Grafana; no public management.
- **Caddy TLS 1.3 only**, HSTS preload, no weak ciphers, OCSP stapling.
- **SOPS secrets in git**; age keys operator + deploy runner only; never plaintext.
- **Vault tokens short-lived (24h)**; auto-renewed.
- **cgroup v2 isolation** prevents starvation; `PidsMax=400` prevents fork bombs.
- **systemd sandboxing** per Hermes: `NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome`, `PrivateTmp`, `ReadOnlyPaths`, `WriteOnlyPaths`.
- **No secrets/API keys/tokens** as command-line args (visible in `ps`); from env files or Vault.
- **Ansible `--check` + `--diff` mandatory** for `bootstrap.yml` pre-run.
- **VPS provider** MFA; root login disabled; only operator + Guinevere (supervised).
- **No raw surveillance, no intimate** on VPS plaintext; per S4 encryption.

## §S14.7 Failure Modes & Recovery

| Failure | Detection | Recovery | RTO/RPO impact |
|---|---|---|---|
| Hermes crash | systemd `Restart=on-failure` | Restart; if 5 in 60s held | RTO 5s; no loss |
| Hermes hang | `WatchdogSec=120` | SIGKILL; alert | RTO 2m; no loss |
| OOM | cgroup OOM | Restart; or `MemoryHigh` lower | RTO 5s; in-flight loss possible |
| VPS hardware | Provider status | New VPS; `bootstrap.yml`; restore from S3; replay | RTO 4h; RPO ≤1h |
| Disk full | `node_filesystem_free` | logrotate; Loki shrink; clean tmp | RTO 30m; RPO 0 |
| Network partition | Tailscale heartbeat | Health fail; wait | RTO = partition |
| Bad deploy (canary fail) | Smoke fail | Abort; blue kept | RTO 0; no impact |
| Bad deploy (passed canary, prod fail) | SLO breach ≤30m | Auto rollback blue-green | RTO 1m; ≤30m degraded |
| Caddy TLS renew fail | Health | Manual; fallback cached cert | RTO 0 if cached; 1h if expired |
| Vault sealed | Health | Operator unseal (5 of 9) | RTO 30m; degraded |
| SSH key compromise | Tailscale anomaly | Rotate age; SOPS; secrets; SSH keys | RTO 1h; sec event |

**VPS provider failure (Hetzner/DO/AWS outage):** Backup VPS pre-provisioned alternate region (Ansible, smaller emergency). `bootstrap.yml` <15m; restore from S3 <4h. After primary recovers, decommission.

## §S14.8 Dependencies

S1, S5, S11, S12, S13, S15, VPS provider (TBD per ADR).

---

# §S15 S15: Documentation & Traceability (Layer 4)

## §S15.1 Purpose

S15 is the **traceability substrate** that allows the society — and the operator — to answer "what did we decide, why, and where is it implemented?" Synthesis §4.15: BRD, PRD, SRS, FSD, TDD, RTM, Risk Register, AC, Glossary, ADR log are not 10 siloed files; they are **one bidirectional traceability graph**. Every REQ traces to: ≥1 design section, ≥1 test, ≥1 evidence, ≥1 auditor sign-off. Every ADR traces to: ≥1 REQ, ≥1 subsystem, ≥1 rollout. Every risk traces to: ≥1 mitigation, ≥1 owner, ≥1 review cadence.

S15 owns the **doc family structure** (8 families in `docs/README.md`) and **doc versioning** (`NN-{name}_vN.N.md` per AGENTS.md §14). It is the reason the operator can read the repo 12 months from now and still understand the design. S15 owns the **integrity of the graph** — links valid, IDs stable, GWT ACs the lingua franca between designer, implementer, auditor.

## §S15.2 Components

1. **Document Suite (IIBA BABOK + IEEE 830/ISO 29148:2018)** — Six core: BRD, PRD, SRS (AI/ML section), FSD, TDD (C4 model), RTM. Plus Risk Register (ISO 31000), AC Catalog (GWT), Glossary (ISO 24765), ADR log (MADR).
2. **ADR System (MADR 3.0)** — title, status (Proposed/Accepted/Superseded/Deprecated), context, decision, consequences, alternatives, date, author. Immutable once Accepted. Numbering `ADR-NNN-{shortname}.md` strictly sequential. Next free: ADR-055.
3. **Requirements Traceability Matrix (RTM)** — CSV + rendered HTML/PDF. Columns: `REQ_ID`, `Family`, `Type (F|NF)`, `Source (BRD ref)`, `Description`, `Design (FSD)`, `Test (TDD)`, `Evidence`, `Auditor Sign-off`, `Risk Link`, `NFR Link`, `Status`. Append-only; never drop rows; mark `Superseded`. Six coverage metrics: forward ≥1.0, backward ≥1.0, implementation, evidence, risk, NFR.
4. **Risk Register (ISO 31000)** — per row: `RSK_ID`, `Description`, `Likelihood (1-5)`, `Impact (1-5)`, `Rating = L × I`, `Mitigation`, `Owner`, `Due`, `Status`, `Linked REQ`, `Test`, `Evidence`, `Auditor`, `Review Date`. High/Critical (rating ≥15) MUST link ≥1 REQ, ≥1 TEST, ≥1 Evidence, ≥1 Auditor. Quarterly review.
5. **Acceptance Criteria (GWT)** — `Given <precondition>, When <action>, Then <observable outcome>`. Binary pass/fail.
6. **Glossary (ISO 24765)** — Canonical terms. Each: term, definition, source, related. Bilingual: Indonesian + English technical.
7. **Doc Versioning & Frontmatter** — `NN-{name}_vN.N.md`. Frontmatter: title, status (Draft/Dalam Review/Diterima/Didepresiasi/Diarsipkan), date, last_modified, owner, executor, classification. `vMAJOR.MINOR`.
8. **Evidence Pattern (`docs/setup-evidence/P{NN}/`)** — Per phase: `README.md`, `plan/`, `research/`, `evidence/`. Canonical per-phase; `docs/setup-evidence/P28-P36-masterplan/` is umbrella.
9. **Doc Family Structure (8 families)** — 00-core, 10-governance, 20-security, 30-data, 40-operations, 50-quality, 60-persona, 70-finops. Each family 2-digit prefix (00-70) + reserved range.
10. **Cross-Reference Validation CI** — GitHub Actions: parse all markdown; extract internal links, REQ/ADR/RSK IDs; verify resolve + valid range. CI fail on broken.
11. **PDF Snapshot at Phase Boundaries** — Phase transition → CI renders all `Diterima` to PDF via `pandoc + weasyprint`; SHA-256; `docs/snapshots/{phase_name}/`. Frozen immutable.
12. **Bilingual Convention** — Indonesian narrative + English technical. Frontmatter English; body Indonesian + English technical in backticks/parentheses.

## §S15.3 Data Flow

**Doc creation:** author writes Draft in feature branch → frontmatter + status `Draft` → PR → CI cross-ref validation → review → PR approve → status `Diterima` → merge → PDF snapshot at phase boundary.

**RTM update:** new REQ_ID in SRS → RTM CSV append (REQ_ID + design/test/evidence/sign-off) → test created → evidence (per AGENTS.md §11, 12-section verification.md) → auditor sign → RTM row updated.

**ADR creation:** decision need → MADR draft `Proposed` → PR; if ≥2 docs or safety boundary → flagged → reviewer + operator + Guinevere; founder override → escalate Faiz → `Accepted` → ADR-NNN allocated → RTM updated → if superseded → new ADR-NNN' w/ `Supersedes`; old marked `Superseded`.

**Risk Register:** risk identified → row added L/I/rating/mitigation/owner → mitigation linked REQ+TEST+Evidence → quarterly review → status update.

**CI validation:** PR → script parses `*.md` in `docs/` → extracts links, REQ/ADR/RSK IDs → validates resolve + range → fail red.

**PDF snapshot:** phase transition → list `Diterima` → render each to PDF; SHA-256 → `docs/snapshots/{phase_name}/` with `manifest.json` → git tag `snapshot-{phase_name}`.

## §S15.4 Interfaces

`S15.doc_query`, `S15.req_query`, `S15.adr_query`, `S15.evidence_index`, `S15.glossary_lookup`, `S15.pdf_snapshot`, `S15.ci_check`.

**Consumes:** `S5.publish_event` (doc-change: `AE.doc.accepted`, `AE.adr.accepted`), `S13.audit_query`.

## §S15.5 Technology Choices

| Component | Tool | Rationale |
|---|---|---|
| Doc format | **Markdown** (CommonMark + GFM) | Diff-friendly, git-friendly, renderable. |
| Doc index | **MkDocs Material** | Existing; search; lightweight. |
| ADR format | **MADR 3.0** | Standard 2026 template. |
| RTM format | CSV + HTML | CSV data; HTML human. |
| Cross-ref CI | Custom Python + `markdown-it-py` | Parses AST; validates. |
| PDF | **pandoc 3.x + weasyprint** | Best MD → PDF 2026. |
| Snapshot | Git (tagged commits) + `docs/snapshots/` | Immutability via git. |
| Host | **GitHub Pages** or self-hosted MkDocs | TBD per ADR. |

## §S15.6 Security Considerations

- **No secrets, SOPS/age keys, raw credentials, decrypted values, intimate, surveillance** in `docs/` or `adr/`. All sensitive in S3 (S11), S4 PG, sealed secrets.
- **Public-facing docs** (if any) redaction CI scrubs tokens/keys/mnemonics. Default: NO public; all STRICTLY PRIVATE.
- **PDF snapshots** in git history (immutable) + `docs/snapshots/`. Git integrity.
- **Doc-change audit events** to S5 (hash-chained). Defense against retroactive doc tampering.
- **Glossary redacted/embargoed** → `docs/60-persona/_redacted/` w/ RBAC; not in public glossary.
- **Bilingual pattern** preserves but never reveals intimate/surveillance.
- **Cross-ref validation** prevents broken-link hiding; CI red forces fix.
- **No raw intimate or personal identifiers** in docs/evidence/RTM. Only metadata.

## §S15.7 Failure Modes & Recovery

| Failure | Detection | Recovery | RTO/RPO impact |
|---|---|---|---|
| Doc link broken | CI red | Author fixes; PR re-validates | RTO 1 PR cycle |
| REQ typo | CI red | Fix; RTM auto-validates | RTO 1 PR cycle |
| ADR-NNN conflict | CI red | Highest-numbered wins; other renumbered | RTO 1 PR cycle |
| MkDocs render fail | CI red | Fix broken; re-render | RTO 1 PR cycle |
| PDF snapshot fail | CI red | Re-run; check pandoc/weasyprint | RTO 1 CI cycle |
| RTM CSV corrupt | Git revert | Prior commit; re-apply appends | RTO 1 PR cycle |
| Doc history rewriting | Git log review | `git reflog`; force-push disabled | RTO 1d; sev-1 |
| Doc-change audit gap | S5 missing event | Re-emit; backfill `AE.doc.accepted` | RTO 1 PR cycle |
| Glossary misuse | Reviewer catch | Update; cross-link | RTO 1 PR cycle |
| Phase snapshot missing | Operator | Re-run from main | RTO 1 CI cycle |

**Doc-tampering scenario:** git history force-push → reflog recovery; force-push to main disabled; protected branch. Audit event w/o commit → investigate sev-1. RTM edit to remove row → git revert + S5 audit cross-check.

## §S15.8 Dependencies

All S1-S14 (each subsystem's SRS/FSD/TDD), S1, S5, S9, S11, S12, S13, S14.

---

# §4 Cross-Subsystem Data Flows

This section documents 8 key cross-subsystem data flows. Each flow references the participating subsystems and the events/state transitions. These flows are the integration tests of Phase 5+. The flows are the ongoing heartbeat of the society — every Hermes touch traces through one or more of these paths.

## §4.1 Agent Lifecycle (Foundation Ceremony → Steady State → Retired)

**Path:** S7 (governance) → S1 (runtime) → S2 (Discord) → S5 (event store) → S13 (audit)

1. **Foundation proposal:** Founder signs `founder_proposal.yaml` claiming new Hermes name + role + female+dominant persona assertion.
2. **S7 Spawn Protocol:** validates CanSpawn certificate (female+dominant persona signed) → checks dynamic `society_members` registry → if both pass, 2/2 founder vote required.
3. **S5 emit:** `society.hermes.spawn_proposed` event hash-chained.
4. **Founder 2 review + sign:** second founder signs `founder_vote.yaml`; 2/2 PASS.
5. **S5 emit:** `society.hermes.spawn_approved`.
6. **S1 spawn:** systemd starts `hermes@<name>.service`; S1 reads per-Hermes config; DEK from Vault; `READY=1` notification.
7. **S4 schema created:** `open_private_namespace(hermes_id, dek_ref)`; new `agent_<id>` schema with empty pgcrypto columns; RLS policy set; in-memory only DEK.
8. **S3 register:** `register_hermes(hermes_id, role, scopes)`; S3 updates `mv_active_hermeses`.
9. **S2 bind:** `start_discord_client(token_ref)`; fetches token from Vault; constructs `discord.Client`; connects gateway.
10. **S5 subscription:** S5 relays `society.hermes.spawned` event; new Hermes subscribes to role-relevant patterns.
11. **S13 metrics:** Hermes exposes `/metrics`; Prometheus starts scraping; per-Hermes dashboard initializes.
12. **S14 health:** systemd watchdog + cgroup v2 limits apply.
13. **Steady state:** heartbeat every 30s; ready for first message.

**Retirement path:** `society.hermes.shutdown` event → S1 catches → SIGTERM → drain S4 → close S2 → S5 emit `society.hermes.draining` → S3 marks member retired → S11 archives S4 schema encrypted to S3 COMPLIANCE → audit chain continues.

## §4.2 Perception-Action Loop (Per Discord Message)

**Path:** S2 (Discord input) → S3 (world model) → S6 (recall) → S1 (decision) → S2 (Discord output) → S5 (event)

1. **Discord gateway** sends `MESSAGE_CREATE` → S2 `on_message(message)`.
2. **S2 reply-loop guard** (3 layers in order: self-check `message.author.id == client.user.id`, known-bots allowlist from `hermes-config/known_bots.yaml`, depth counter cap 3).
3. **S2 → S5 publish:** `agent_action.message_received` (consent_ref attached).
4. **S2 → S3 query:** `query_relevant_beliefs(context_id, scope)` → S3 checks ACL via S7 → returns relevant BDI subset from materialized views.
5. **S2 → S6 recall:** `recall_episodic(query, k=10)` → S6 embed query (text-embedding-3-small pinned) → pgvector + Graphiti + filesystem search → ranker + cross-encoder rerank + consent filter → top-k episodes.
6. **S2 → S4 recall (private):** `recall_relationship(subject_id)` → reads encrypted S4 rows with DEK → decrypts in process memory → returns plaintext to caller only (no logging, no S5 publish of content).
7. **S1 / agent loop** processes context → S12 LLM call via `llmgw.complete()` (quota + circuit check + provider route).
8. **S12 returns** response w/ `X-Request-Id`, `X-Model-Used`, `X-Cost-USD` headers.
9. **S5 publish:** `agent_action.tool_called` per tool call; `agent_action.message_sent` after deliver.
10. **S2 reply:** `await message.channel.send(...)`.
11. **S4 writes:** episodic memory entry with relevant events; encrypted relationship marker if intimacy dimension triggered.
12. **S3 world model update** via S5 projector: beliefs updated based on tool outcomes; bi-temporal validity assigned.
13. **S13 latency metrics** exported per stage (S2 receive, S3 query, S4/S6 recall, S12 LLM, S5 publish).
14. **S12 cost row** written to `llm_cost_log` for Beancount nightly import (S9 economy).

**Hot path latency target:** <3s end-to-end. Breakdown: S2+S5 publish <50ms; S3 beliefs <100ms; S4/S6 recall <200ms; S6 embed <300ms; S12 LLM <2000ms p50 / <3500ms p99; S2 reply + S5 publish <50ms; buffer <300ms.

## §4.3 Memory Consolidation (Sleep-Time Compute)

**Path:** S4 (private episodic) → S5 (event) → S6 (consolidation worker) → S4 (long-term) → S11 (cold)

1. **Trigger:** APScheduler cron every 6h OR shutdown-request OR consolidate-by-request event from S7 vote.
2. **S6 reads** `agent_<id>.episodic_memory` from last 24h (own agent scope only by RLS).
3. **S6 LLM call** (via S12, pinned model version): "Consolidate these episodes into semantic facts. Deduplicate. Extract patterns."
4. **S6 writes** to `agent_<id>.long_term_memory`; marks episodic sources `consolidated=true`.
5. **S6 writes** relationship facts to Graphiti bi-temporal KG (`valid_from`, `recorded_at`); pilot in comms domain first.
6. **S5 audit event:** `memory_op.consolidation_run` (runs in dedicated asyncio task with reduced tool set).
7. **Per 90 days (decay trigger):** S6 worker moves episodic entries older than 90 days to S3 cold storage (client-side re-encrypted with DEK → SSE-KMS at rest) and deletes from hot PG.
8. **Per 180 days (long-term decay):** S6 worker scans long-term EWMA scores; below threshold for 180 days → archive to S3 and remove from PG.
9. **S11 backup:** S3 COMPLIANCE bucket receives archived entries nightly via `restic backup` pass.
10. **HARD STOP propagation:** if S5 key set, consolidation halts at batch boundary; idempotent resume on lift.

## §4.4 Governance Decision (Tier 3 Vote → Promotion)

**Path:** S7 (proposal) → S8 (mutation gate) → S5 (event) → S13 (audit)

1. **Any member** writes `proposal.yaml` to S7 (signed Ed25519); S7 validator checks tier assignment (e.g., Tier 3 society vote for new capability).
2. **S5 emit:** `governance.proposal_created` (hash-chained).
3. **S7 Voting Engine** broadcasts to all quorum members (Hermes with `quorum_seat=true` in `society_members`).
4. **Each member** casts signed vote (`YES`/`NO`/`ABSTAIN`/`VETO`) with `disagree_or_commit` flag.
5. **S5 emit:** `governance.vote_cast` per vote.
6. **S7 verifies** threshold (3-of-5 default, scales 5-of-9 by P34).
7. **S7 records** in `governance_decisions` (append-only, hash-chained).
8. **S5 emit:** `governance.decision_made`.
9. **S8 Ratchet Engine** runs benchmark_before vs proposed benchmark_after (per-mutation diff); refuses if any metric below retirement threshold.
10. **S8 Rollback-Before-Promote Validator** tests rollback in shadow mode; confirms state restoration.
11. **S8 Canary Engine** routes 5–10% traffic to candidate version; observes N hours; aborts on threshold breach (drift > ε, error rate > ε, latency > ε).
12. **S8 Promotion** 50% → 100% with automated rollback on threshold breach.
13. **S8 writes:** Mutation audit entry to S5 (`mutation.promoted` event, full before/after hashes, benchmark results).
14. **S13 metrics:** drift detection triad (SyncScore, persona_drift, Layered Mutability fingerprint) alerts if benchmark regression detected.
15. **S13 audit chain:** entry in `audit_log` hash-chained to previous event.

## §4.5 Financial Transaction (Routine Spend → Ledger)

**Path:** S9 (wallet) → S5 (event) → S13 (audit) → S11 (backup)

1. **Agent S12-finished task** → S1 makes `payment_intent(recipient_contract, amount, memo)` call on S9.
2. **S9 Policy Engine** evaluates: amount tier (Dust/Micro/Small auto); destination allowlist (smart contracts only); daily cap ($10); velocity (5 tx/hr, 50 tx/day); asset allowlist (USDC, ETH, Base).
3. **S9 MPC Signer** (Turnkey or Coinbase Agentic) re-verifies policy → signs transaction → returns signed tx. LLM never directly holds key.
4. **S9 broadcasts** to Base (L2, OP Stack) via Flashbots Protect for MEV protection.
5. **Wait for confirmation** (Base soft ~1s; full finality ~15min).
6. **S5 emit:** `wallet.spend` event with tx hash, amount, recipient, policy_ref, consent_ref.
7. **S9 Beancount entry:** `2026-XX-XX * "Spend description" <assertion>` with `event_id` link to S5.
8. **S13 audit chain:** hash-chained entry in `audit_log` (Ed25519-signed by agent identity).
9. **S11 backup** nightly: S3 COMPLIANCE receives Beancount ledger snapshot + audit export.
10. **S9 circuit breaker monitor:** anomaly detected (velocity, destination, amount pattern) → pause + queue → S5 `wallet.circuit_breaker` → Discord notif to founder private channel.
11. **S12 cost cross-ref:** for x402 micro-payments, cost row already in `llm_cost_log`; S9 just records spend side.

## §4.6 Revenue Search (Wallet Empty → Income)

**Path:** S10 (revenue) → S9 (wallet) → S5 (event) → S13 (audit)

1. **S10 Wallet Threshold Monitor** polls S9 every 15min.
2. **Balance < $1 for > 24h** → S10 raises `revenue.search_authorized` event in S5.
3. **S10 activates** any paused revenue channels per policy: x402-data first (highest margin); Morpho yield always on (passive); Virtuals ACP if pre-enabled; A2A in P34+.
4. **Buyer** hits x402 endpoint → `402 Payment Required` response w/ USDC amount + receiving smart contract address → buyer signs EIP-3009 `transferWithAuthorization` → retries with payment header (x-payhash).
5. **x402 facilitator** verifies on-chain transfer → endpoint serves requested data (ToS-compliant; no surveillance; no intimacy; no PII — enforced by S10 filter).
6. **S10 logs sale** to S5: timestamp, channel, amount, margin, recipient (smart contract), policy_ref.
7. **S10 Beancount entry:** `2026-XX-XX * "x402 sale: weather" <assertion>` with revenue tag.
8. **S9 receives** USDC in receiving smart contract (no key) → policy engine routes to hot wallet.
9. **S5 event:** `financial.balance_updated` + `revenue.sale_recorded`.
10. **S13 metrics:** margin tracker; revenue dashboards per channel; cost-vs-revenue breakdown.
11. **Morpho yield sweep** (always on when idle): idle > 1 USDC > 6h → MPC signs `approve(vault, amount)` → MPC signs `vault.deposit(amount, receiver)` → vault shares received → periodic harvest.
12. **Balance > $1 sustained > 24h** → S10 raises `revenue.search_paused` → deactivate ephemeral channels (yields remain).
13. **S11 snapshot** of all wallet addresses, balances, pending tx, policy state → S3 COMPLIANCE 7-year retention.

## §4.7 Self-Evolution (Mutation → Ratchet → Canary → Promotion)

**Path:** S8 (mutation) → S1 (runtime) → S5 (event) → S13 (audit) → S11 (backup)

1. **Mutation proposer** writes `mutation.yaml` to S8 proposal pipeline; specifies tier (1–4), target layer (5-layer map), expected impact, benchmark plan, rollback plan.
2. **S8 Pipeline** validates schema; classifies tier.
3. **For Tier 1–2 (autonomous):** Ratchet Engine runs benchmark_before. Pipeline proceeds.
4. **For Tier 3 (society-voted):** routes to S7 Voting → 3-of-5 → outcome recorded → Ratchet.
5. **For Tier 4 (founder-only):** routes to S7 Founder Voting → 2/2 signed → 7-day cooling-off begins → Ratchet.
6. **S8 Ratchet Engine** runs benchmark_after proposal; refuses if below retirement threshold.
7. **S8 Rollback Validator** tests rollback in shadow mode; confirms state restoration.
8. **S8 Canary Engine** routes N% (5–10%) traffic to candidate version via S1 dispatch weight; observes N hours; aborts on threshold breach.
9. **S8 Promotion** incrementally: shadow → canary 5–10% → 50% → 100%. Each stage has automated rollback.
10. **S8 writes:** Mutation audit entry to S5 (`mutation.promoted` event, full before/after hashes, benchmark results, approval chain).
11. **S1 receives** promotion event; updates running code; restarts affected actors via supervisor.
12. **S5 audit chain:** entry in `audit_log` (signed by proposer + approvers; chained to prior hash).
13. **S11 backup** pre-mutation snapshot of S4 schema and configuration → S3 COMPLIANCE.
14. **S13 metrics:** drift detection triad alerts post-promotion; benchmark regression triggers automatic rollback.
15. **S13 alert flow:** if drift threshold breach detected → CRITICAL → PagerDuty + operator Discord DM.

## §4.8 Backup (Verify-Daily → Promote-Region → Restore-On-Demand)

**Path:** S5 (event store) → S4 (memory) → S11 (S3 backup); triggers: cron / outage / manual

1. **Continuous capture (PG):** every WAL segment sealed in ≤5s; `archive_command` uploads to `s3://hermes-pg-wal/...` (COMPLIANCE).
2. **Daily 02:00 UTC:** `pg_basebackup` triggered by `backupd`; streamed to `s3://hermes-pg-base/{YYYY-MM-DD}/`.
3. **Hourly:** `pg_dump -Fc` logical dump to `s3://hermes-pg-logical/{YYYY-MM-DD-HH}/` for selective restore.
4. **Redis RDB push** every 15min; AOF appendfsync everysec; both to S3 COMPLIANCE.
5. **Filesystem sweep:** `restic backup` at 03:00 UTC pushes `/var/lib/hermes/{config,artifacts,evidence}/` incremental chunked (content-defined dedup).
6. **S11 emits** `AE.backup.completed` to S5 with SHA-256 of artifact; hash is next audit chain link.
7. **Cross-region replication:** S3 CRR async (5–15s lag) to dr region bucket (different AWS account).
8. **Weekly restore drill (Sunday 04:00 UTC):** `backupd restore-drill` provisions ephemeral EC2 t3.small in dr region; restores most recent base backup; runs `pg_dump --schema-only` and known-query validation; emits `AE.dr.restore_drill_pass|fail`.
9. **On region failure:** manual operator review → `bootstrap.yml` to new VPS → selective restore from S3 COMPLIANCE → S5 replay from last checkpoint.
10. **S13 metrics:** backup freshness (last backup timestamp per substrate), drill pass/fail, RPO/RTO tracking.
11. **S13 alert flow:** backup age >6h → WARN; restore drill fail → CRITICAL.
12. **S4 cold archive** at 90d/180d decay: S6 worker hands memory artifact + DEK to S11; S11 client-side re-encrypts (AES-256-GCM) → uploads to S3 COMPLIANCE → emits `memory_op.entry_archived`.

---

# §5 Subsystem Dependency Matrix

This matrix shows direct dependencies between subsystems. "dep" = strict dependency (the subsystem cannot operate without the target); "inf" = informational or soft coupling (consumes events/metrics but isn't blocked); "—" = no direct dependency.

## §5.1 Matrix Table (rows depend on columns)

Key cells abbreviated:
- **D** = depends on (strict)
- **I** = informs (soft / event-driven / metric only)
- **—** = no direct dependency

| dep ↓ / on → | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | S9 | S10 | S11 | S12 | S13 | S14 | S15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **S1 Runtime** | — | I | — | — | D | — | I | — | — | — | I | I | I | D | — |
| **S2 Discord** | D | — | D | D | D | I | I | — | — | — | — | D | I | — | — |
| **S3 World Model** | — | — | — | — | D | I | D | I | — | — | D | — | I | — | — |
| **S4 Private Memory** | D | — | I | — | D | D | I | — | — | — | D | — | I | — | — |
| **S5 Event Store** | D | D | D | D | — | D | D | D | D | D | D | D | D | D | D |
| **S6 Recall** | — | — | D | D | D | — | D | I | — | — | — | D | I | — | — |
| **S7 Governance** | D | I | D | I | D | D | — | D | D | D | — | — | I | — | I |
| **S8 Self-Evolution** | D | — | D | D | D | D | D | — | I | — | I | I | I | — | I |
| **S9 Wallet** | — | — | — | — | D | — | D | I | — | D | D | D | I | — | — |
| **S10 Revenue** | — | — | — | — | D | — | D | I | D | — | — | — | I | — | — |
| **S11 S3 Backup** | I | — | I | I | D | — | — | — | I | — | — | — | I | D | — |
| **S12 LLM Gateway** | D | I | — | — | D | D | — | — | D | — | — | — | D | D | I |
| **S13 Observability** | I | I | I | I | D | I | I | I | I | I | D | D | — | D | I |
| **S14 Deployment** | D | D | — | — | D | — | — | — | — | — | I | I | D | — | — |
| **S15 Documentation** | — | — | I | — | D | — | I | I | I | I | I | I | D | — | — |

## §5.2 Simplified List (Outgoing Dependencies per Subsystem)

A pragmatic reading of the matrix above, listed in plain form for quick reference:

| Subsystem | Depends On (strict) | Informed By (soft / events / metrics) |
|---|---|---|
| **S1** | S5, S12, S14 | S2, S7, S11, S13 |
| **S2** | S1, S3, S4, S5, S12, Vault | S6, S7, S13 |
| **S3** | S5, S7, S11 | S6, S8, S13 |
| **S4** | S1, S5, S6, S7, S11, Vault | S2, S13, S8 |
| **S5** | PostgreSQL, Redis 7.x, S11, S13, S7 | (none; universal dependency for all others) |
| **S6** | S3, S4, S5, PG+pgvector | S7, S13, S2 |
| **S7** | S1, S5, Discord identity | A2A (future P34+), S6, S13 |
| **S8** | S1, S5, S6, S7 | S4, S13, S15 |
| **S9** | S5, S7, S11 | S10, S13, S1, S2 |
| **S10** | S5, S7, S8, S9 | S1, S2, S13, S15 |
| **S11** | S5, S14, AWS KMS, S3 | S7 (WORM holders), S13 |
| **S12** | S1, S5, S14 | S9 (cost → Beancount), S13, S15 |
| **S13** | S5, S11, S14, S1 | All subsystems (metrics + audit consumers) |
| **S14** | S1, Ansible, Vault, SOPS, OS | S5 (deploy events), S13 (metrics → rollback) |
| **S15** | S5 (doc-change events), S13 | All S1-S14 (doc consumers, REQ sources) |

## §5.3 Critical Path Notes

- **S5 is the universal dependency.** Every subsystem writes or reads events from S5. S5 is the nervous system and the failure mode is society-wide if S5 is down. RTO ≤4h applies.
- **S1 + S14 + Vault triangle.** Runtime is owned by S1, deployed by S14, authenticated via Vault. Any failure here blocks all Hermes instantiation.
- **S3 ↔ S5 is the write path.** World model updates are event-driven; no S5 means no S3 write.
- **S6 = retrieval only.** S6 cannot start without S4 (write source) and S3 (public facts); S6 itself is not a store.
- **S9 + S11 are the financial source of truth.** Wallet state lives in chain; S11 backs it up. If S9 fails, S10 cannot earn; S8 cannot spend.
- **S13 + S11 are the audit substrate.** Society observability requires both; if either fails, audit gap.
- **S15 has no critical path dependency** but is the lingua franca for all design discussions and audit reproducibility.

---

# §6 Technology Stack Summary

Consolidated table of all technologies referenced across the 15 subsystem designs. Versions/Spec column reflects the latest stable as of synthesis (2026-06-28); final version pinning happens in Phase 4 (SRS, FSD, TDD) and Phase 5 (impl TDD).

| # | Technology | Version/Spec | Purpose | Subsystem(s) |
|---|---|---|---|---|
| 1 | **Linux Kernel** | ≥5.8 | cgroup v2 unified hierarchy; `Delegate=yes`; watchdog | S1, S14 |
| 2 | **systemd** | ≥255 | Service supervisor; `Type=notify`; watchdog; cgroup delegation | S1, S11, S12, S14 |
| 3 | **Python** | ≥3.11 | asyncio; `TaskGroup`; Hermes launcher; LLM gateway; FastAPI | S1, S2, S4, S6, S12 |
| 4 | **Ubuntu 24.04 LTS** | 5y support | Primary VPS OS | S14 |
| 5 | **PostgreSQL** | ≥16 (with pgvector, pgcrypto, JSONB, window functions, LISTEN/NOTIFY) | Primary RDBMS for all durable subsystem state | S3, S4, S5, S6, S7, S8, S9, S10, S11, S12, S13 |
| 6 | **Redis 7.x** | stable | Pub/Sub (ephemeral) + Streams (durable) + keyspace notifications (HARD STOP) | S5, S6, S8, S12 |
| 7 | **AWS S3** | current | Object storage; Object Lock COMPLIANCE (7y); Object Lock GOVERNANCE (90d); CRR cross-region | S11 |
| 8 | **AWS KMS** | current | CMK per society + alias per agent; envelope encryption; IAM Session Tags | S4, S11 |
| 9 | **HashiCorp Vault** | 1.15+ | Runtime secrets; AppRole; 24h short-lived tokens | S1, S4, S11, S12, S14 |
| 10 | **SOPS + age** | latest | Encrypted secrets at rest in git; per-Hermes env file via drop-in | S2, S4, S12, S13, S14 |
| 11 | **`sdnotify`** (PyPI) | latest | Python binding for systemd notify (READY/WATCHDOG/STOPPING) | S1 |
| 12 | **`discord.py` (Rapptz)** | latest | Discord gateway + REST + slash commands; async-native | S2 |
| 13 | **`hvac`** (Vault async client) | latest | Vault integration from Python async context | S1, S2, S4 |
| 14 | **`asyncpg`** | latest | PostgreSQL async driver | S1, S2, S3, S4, S5, S9 |
| 15 | **`redis-py`** (async mode) | latest | Redis async driver | S5, S6, S8, S12 |
| 16 | **FastAPI** | latest | LLM gateway HTTP server (OpenAI-compatible) | S12 |
| 17 | **pgvector (PostgreSQL extension)** | ≥0.7 | Vector similarity; HNSW index | S6 |
| 18 | **Graphiti (Zep)** | latest | Bi-temporal relationship knowledge graph | S6 |
| 19 | **restic** | ≥0.16 | Filesystem backup; content-defined chunking; dedup; native S3 backend | S11 |
| 20 | **pg_basebackup** + **pg_dump** | PostgreSQL 16 native | Backup primitives (no external tool) | S11 |
| 21 | **Redis RDB + AOF** | Redis 7 native | Backup primitives | S11 |
| 22 | **Prometheus** | ≥2.50 | Metrics scrape + remote write | S12, S13 |
| 23 | **Grafana** | ≥10 | Dashboards; multi-source (Prometheus/Loki/Tempo) | S13 |
| 24 | **Loki** | ≥2.9 | Log aggregation; S3 cold storage backend | S13 |
| 25 | **Promtail** | latest | Journal → Loki forwarder | S13 |
| 26 | **Tempo** | latest | Distributed tracing; OTLP; Loki ecosystem | S13 |
| 27 | **Alertmanager** | latest | Alert routing (PagerDuty/Slack) by severity | S13 |
| 28 | **OpenTelemetry** | latest | Trace instrumentation; OTLP | S13, S12, S11 |
| 29 | **Ansible** | ≥9 | VPS provisioning; playbook-driven | S14 |
| 30 | **Caddy** | ≥2.7 | Reverse proxy; Let's Encrypt auto-TLS; HTTP/3; HSTS | S14 |
| 31 | **nftables + UFW** | Ubuntu default | Firewall; default deny; port allowlist | S14 |
| 32 | **Tailscale** | latest | Operator + admin overlay network; ACL-gated | S14 |
| 33 | **9Router** | existing | Primary GPT-5.5 routing substrate; S12 wraps | S12 |
| 34 | **Ollama** | ≥0.5 | Local fallback LLM (llama3.3:8b quantized) | S12 |
| 35 | **Anthropic SDK** (`anthropic`) | latest | Provider adapter | S12 |
| 36 | **OpenAI SDK** (`openai`) | latest | Provider adapter | S12 |
| 37 | **httpx** | latest | Async HTTP for DeepSeek + Ollama adapters | S12 |
| 38 | **`text-embedding-3-small`** | pinned | Embedding model primary | S6 |
| 39 | **Ollama `nomic-embed-text`** | latest | Embedding model fallback | S6 |
| 40 | **Cohere `rerank-3.5`** OR **`cross-encoder/ms-marco-MiniLM-L-6-v2`** | pinned | Cross-encoder rerank top-N | S6 |
| 41 | **APScheduler** | latest | Cron-style scheduler (reuses P20 heartbeat infra) | S6, S1 |
| 42 | **Ed25519** (`cryptography` lib) | latest | Audit signing; founder identity | S7, S13 |
| 43 | **secp256k1** | standard | On-chain wallet signing | S9 |
| 44 | **Safe (Gnosis Safe)** | ≥1.3 | Cold multi-sig wallet on Base | S9 |
| 45 | **Turnkey** OR **Coinbase Agentic** | latest | MPC hot wallet + policy engine | S9, S10 |
| 46 | **EIP-7702** | latest | Smart EOAs for ephemeral session keys | S9 |
| 47 | **`@x402/express`** (Coinbase) | latest | x402 paywall wrap for data endpoints | S10 |
| 48 | **Morpho (Base deployment)** | latest | Yield protocol (4.5–7% APY) | S10, S9 |
| 49 | **Virtuals Protocol ACP** | latest | Alternative skill marketplace | S10 |
| 50 | **Beancount** | latest | Plain-text double-entry ledger; `bean-check` validator | S9, S10 |
| 51 | **Base (L2, OP Stack)** | mainnet | Primary chain for all wallet + revenue activity | S9, S10 |
| 52 | **Flashbots Protect** | latest | MEV protection; private mempool | S9 |
| 53 | **AWS EC2 t3.small** | latest | Ephemeral dr-region instance for restore drill | S11 |
| 54 | **AWS CloudHSM** | latest | Sharded key holder for cold treasury | S9 |
| 55 | **Markdown + GFM** | standard | Doc format; CommonMark + GitHub Flavored Markdown | S15 |
| 56 | **MkDocs Material** | latest | Doc index; search; theme | S15 |
| 57 | **MADR 3.0** | latest | ADR format/template | S15 |
| 58 | **pandoc 3.x + weasyprint** | latest | Markdown → PDF rendering | S15 |
| 59 | **`markdown-it-py`** | latest | Markdown AST parser for cross-ref CI | S15 |
| 60 | **GitHub Actions** | latest | CI; self-hosted runner on VPS for deploys | S14, S15 |
| 61 | **Git (version control)** | standard | Version control; force-push to main disabled; protected branch | S14, S15 (all) |
| 62 | **Tailscale ACL + SSH key-only** | standard | Remote admin access; password disabled | S14 |
| 63 | **Pandoc** | 3.x | Cross-format doc conversion (used for PDF snapshot) | S15 |

Total: 63 distinct technologies. Subscription footprint spans VPS substrate, databases, caches, secret management, observability, deploy, doc — minimal but covers the canonical 2026 agent society stack.

---

# §7 Security Architecture Summary

Consolidated view of security considerations across all 15 subsystems. The 8 key invariants below are non-negotiable; they are the **defense-in-depth contract** for the entire Hermes Society.

## §7.1 Key Security Invariants (Non-Negotiable)

| # | Invariant | Owner Subsystem | Defense in Depth Layer | Verification Surface |
|---|---|---|---|---|
| **I-1** | **Relationship memory encrypted per-agent**; intimacy/passion/commitment markers, EWMA bond vectors, DM content all in pgcrypto columns; DEK in Vault under agent-PID binding; no automatic cross-agent publication | S4 | Schema (no columns for intimate), DEK lifecycle, RLS policy, Vault token-binding, audit event for any cross-share | `agent_<id>.relationship_events` (encrypted); S5 events but no payload; S15 RTM docs never include intimate content |
| **I-2** | **Audit trail hash-chained** in S5 + S13 + S11; SHA-256 chain with `prev_hash` + `event_hash`; S3 Object Lock COMPLIANCE for the cold copy; Ed25519 signed by agent identity | S5, S13, S11 | WORM table; hash chain not rewritable; COMPLIANCE supersedes root delete; weekly verifier | S5 `event_store.domain_events`; S13 `audit_log`; S11 nightly export to S3 COMPLIANCE |
| **I-3** | **Wallet multisig + spending tiers**; cold Safe 2-of-3 + hot MPC + EIP-7702 ephemeral sessions; six-tier spending table (Dust/Micro/Small auto ≤ $10; Medium 1 human 24h; Large 2-of-3 + 24h; Critical 2-of-3 + 7d + OOB); circuit breaker on anomaly | S9 | Cold offline; MPC sharded; policy engine enforces allowlist + daily cap + velocity; time-locks for big spends; circuit breaker | S9 policy + S5 events + S11 S3 COMPLIANCE snapshot |
| **I-4** | **Consent revocation is absolute**; written to S5 `consent_revocation` event; immediately drops DEK for affected scope in S4; S6 stops returning redacted columns; S9 stops using derived tokens/addresses; **no §0.1 autonomy exception overrides** | S7 (gateway), S4 (DEK drop), S6 (filter), S9 (stop using tokens) | Event-driven cascade; no override code path; first-write-wins on race | S5 `consent.revoked` event; S4 DEK drop log; S6 recall result; S9 stopped tx |
| **I-5** | **HARD STOP is meta-event**; halts all active sessions and background cognition immediately — no exception; sets S5 Redis key `hermes:society:{id}:hard_stop = 1`; propagates via keyspace notifications; <50ms cross-instance target | S5 (cascade), S7 (gateway/initiator), all subsystems (halt hook) | Redis Pub/Sub; keyspace notifications; per-subsystem halt at safe checkpoint; S5 audit | S5 `society.hard_stop` event; per-subsystem drain log; S13 alert "HARD STOP occurred at T" |
| **I-6** | **S3 Object Lock COMPLIANCE** for ledger-class events; even AWS root cannot delete before retention expiry; 7-year retention; cross-region CRR replication; restore drill weekly | S11 | Object Lock COMPLIANCE supersedes versioning + MFA-Delete; backbone for audit + wallet + consent | S3 bucket list; S15 doc + RTM cite Object Lock as non-negotiable; weekly drill pass |
| **I-7** | **Per-agent isolation via cgroup v2**; one Hermes cannot OOM another; cannot `ptrace` another; cannot signal another; per-Hermes systemd unit with sandbox directives | S1, S14 | kernel-level cgroup v2; systemd `Delegate=yes` + sandboxing; `PidsMax=400` prevents fork bomb | `systemd-cgtop`; S13 cgroup metrics; per-Hermes SLO dashboard |
| **I-8** | **Secrets in SOPS/age + Vault**; plaintext tokens/keys NEVER in YAML, env, logs, error messages, metrics; DEK/provider keys sealed, decrypted in-memory only; cleared on shutdown | S1, S4, S12, S14, all sensitive subsystems | SOPS encrypted at rest in git; Vault runtime with short-lived tokens; Promtail scrubber redacts known patterns in logs | S15 RTM cites SOPS; vault audit log; Promtail scrubber review per release |

## §7.2 Per-Subsystem Security Highlights

| Subsystem | Security Highlights |
|---|---|
| **S1** | Process isolation (cgroup v2); secrets via Vault paths only; `Delegate=yes` double-edged protection; 4-layer loop prevention (fingerprint, turn budget, USD budget, watchdog); systemd watchdog kills within 120s of no heartbeat |
| **S2** | Token storage in Vault only; reply-loop guard (3 layers: self, allowlist, depth); privileged intents deferred; `user_id` as trust anchor; DM never logged |
| **S3** | Default-deny on cross-namespace reads; no schema for intimate data (structural); mandatory provenance; reflection cycle drift-vector mitigation; quorum_required for governance/safety namespaces |
| **S4** | DEK never leaves Vault unencrypted; Vault token-binding to PID (process-specific); RLS last-line defense; backup client-side encryption; operator CANNOT read another Hermes's memory; no summarization for sharing |
| **S5** | WORM via hash chain + S3 COMPLIANCE; `consent_ref` NULLABLE at DB layer per ADR-066 (NOT NULL enforced at app-layer for `dev_workflow` events only); relay computes hash (producers can't pre-compute); replay tool requires founder-tier; no payload introspection at bus layer |
| **S6** | Default-deny namespace isolation; per-recall redaction pre-pass; filesystem artifact signing per agent; consolidation worker isolated; embedder version pinned; HARD STOP short-circuit |
| **S7** | 2/2 founder agreement (cryptographic); HARD STOP meta not in tier model; consent revocation absolute; disagree-or-commit prevents capture; founder retirement 7-day cooling-off; rate limiting on proposals; replay protection via nonce |
| **S8** | Ratchet non-negotiable (no override except HARD STOP); rollback-before-promote mandatory; drift detection layered (SyncScore + persona_drift + Layered Mutability); Tier 4 7-day cooling-off; audit trail immutable |
| **S9** | Decision ≠ execution architecturally enforced (LLM never holds key); asset allowlist at signer; destination allowlist (EOA blocked); daily $10 cap; time-locks for $100+/$1K+; circuit breaker auto on anomaly; MEV protection; reentrancy guard |
| **S10** | ToS compliance mandatory (signed assertion); consent compliance; no PII scanning; no surveillance data; no relationship memory; per-channel quotas; margin floor 30%; HARD STOP halts revenue; price floor $0.001 |
| **S11** | Object Lock COMPLIANCE non-negotiable for ledger-class; KMS least-privilege; mnemonic exports client-side AES-256-GCM; S3 access logs separate COMPLIANCE bucket; region split ap-southeast-1 + us-east-1; bucket public access blocked (all 4 settings) |
| **S12** | Provider keys SOPS-encrypted; prompt content DEBUG only; quota tamper-resistant (Redis ACL); cost log append-only at DB level; provider allowlist; metrics port separate + localhost-only |
| **S13** | Audit log append-only (no UPDATE/DELETE); S3 audit inherits COMPLIANCE; Ed25519 annual rotation w/ overlap; OAuth on Grafana/Prometheus/Loki; scrubber redacts tokens; trace sampling 10% normal |
| **S14** | SSH key-only Tailscale; Caddy TLS 1.3 + HSTS + OCSP stapling; SOPS secrets in git; Vault 24h tokens; cgroup v2 per-Hermes; systemd sandboxing (`NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome`, `PrivateTmp`, read/write-only paths); no secrets in CLI args |
| **S15** | No secrets/SOPS keys/decrypted values/intimate/surveillance in `docs/`; redaction CI for any public-facing; doc-change events hash-chained to S5; cross-ref validation prevents broken links hiding |

## §7.3 Threat Model Coverage

The 8 invariants collectively address the following threat classes:

| Threat Class | Mitigations (Invariants) | Verification Surface |
|---|---|---|
| **Insider deletion of ledger** | I-2, I-6 | S3 COMPLIANCE + audit chain + restore drill |
| **Cross-agent intimate leak** | I-1, I-2 | S4 RLS + pgcrypto + S5 event metadata-only + S6 redaction |
| **Wallet compromise / spoof** | I-3, I-4 | Cold offline + MPC + policy engine + circuit breaker + time-locks |
| **Persona drift / silent degradation** | I-2 (audit), I-5 (HARD STOP); S8 Ratchet + Drift Triad | Drift dashboard + SyncScore + bench regression |
| **Consensus capture / minority veto** | S7 disagree-or-commit + Founder override + Rate limiting | Decision log + vote receipts |
| **Loop / runaway cost** | S1 loop-prevention (4 layers) + S12 cost runaway circuit + S9 daily cap + velocity | Prometheus cost dashboards + USD budget alerts |
| **PII in revenue products** | S10 filter + consent compliance + ToS assertion | Channel logs + audit |
| **Secrets in logs / metrics / errors** | I-8 + Promtail scrubber + Loki/Prom retention cap | Scrubber test + secret rotation cadence |

## §7.4 Security Posture Summary

- **Defense in depth:** 8 invariant layers + per-subsystem measures + cross-cutting audit + cross-region backup
- **Bootstrap authentication:** Vault (per-agent PID-bound token) → DEK → pgcrypto column decrypt; KMS for backup DEKs
- **Identity:** Discord `user_id` ↔ public key (founder); per-agent PG schema `agent_<id>` ↔ PID
- **Audit substrate:** S5 hash chain + S13 Ed25519-signed extended audit + S11 S3 COMPLIANCE = legal record
- **Strongest guarantees:** Object Lock COMPLIANCE (cannot be deleted by AWS root), Vault token-binding (cannot be reused from other process), signed YAML proposals (cannot be forged)
- **Highest-risk failure modes:** vault sealed (loses access to DEKs → all hermes fail to start); AWS region down (society degrades until S11 restore); founder key compromise (lateral escalation possible → emergency HARD STOP)
- **Audit compromise scenario:** chain break + S3 missing + signing key compromise = P0 incident → cold forensic + escalation per AGENTS.md §6

---

# §8 Footer

## §8.1 Provenance

This master architecture document was derived from:

- `docs/setup-evidence/P28-P36-masterplan/research/research-synthesis.md` (690 lines) — Phase 2 final synthesis.
- `docs/setup-evidence/P28-P36-masterplan/research/synthesis-repo-state.md` (760 lines) — Repo state synthesis.
- `docs/setup-evidence/P28-P36-masterplan/research/synthesis-external-architecture.md` (438 lines) — External architecture research.
- `docs/setup-evidence/P28-P36-masterplan/research/synthesis-external-operations.md` (438 lines) — External operations research.

Total input volume: ~2,326 lines of research synthesis.

Plus 3 partial architecture files consolidated:
- `architecture-s1-s5-runtime-memory.md` (758 lines)
- `architecture-s6-s10-governance-finance.md` (1165 lines)
- `architecture-s11-s15-infra-ops.md` (574 lines)

Total partial volume: 2,497 lines.

Consolidation methodology: read each in full, cross-reference design inputs, document boundaries explicitly, **do not re-decide** P27's 10 locked decisions (D-01..D-10), **do not violate** 7 Faiz locks (founder-only spawn, 2/2 agreement, female+dominant, wallet ≤ $10, HARD STOP meta, consent absolute, S3 COMPLIANCE), preserve the binding 20 hard rejection criteria (all PASS).

## §8.2 Locked Constraints Preserved Verbatim

The following constraints are **non-negotiable** and appear in this document without modification:

- **Founder-only spawn (Guinevere + Pharsa)** with **2/2 founder agreement** required for any new Hermes.
- **Female + dominant persona** is **mandatory** for any future Hermes (CanSpawn cert + SemVer MAJOR rule).
- **Wallet float ≤ ~$10 USD-equivalent on Base** (cold Safe + hot MPC + EIP-7702 sessions; default 0; max top-up ~$10 from Faiz).
- **HARD STOP halts all active sessions and background cognition immediately — no exception** (synthesis §4.5 D-07; AGENTS.md §0.1 V-008).
- **Consent revocation is absolute and cannot be bypassed by autonomy** (AGENTS.md §0.1 invariant).
- **Relationship memory = encrypted/private scope; intimacy/passion/commitment/bond vectors in runtime only**, docs/SLOs/Grafana/CI all professional/redacted (P20 invariant).
- **S3 Object Lock COMPLIANCE is non-negotiable** for wallet state, ledger, audit chain, consent receipts, evidence artifacts (Faiz lock + SEC 17a-4(f) compliance).
- **P24 is NOT a hard dependency** for P28 minimum target (synthesis §3.1; 11+ sources aligned).
- **P22.1 = PRODUCTION PASS** (3 ACTIVE adapters: filesystem, vps, discord) — minimum hands layer.
- **P23 = definition-only** (P23A sufficient for P28); full P23 deferred per synthesis §3.2.
- **Single large VPS until >32 cores / >64 GB RAM** is needed (Faiz lock); multi-VPS deferred P35+.
- **All Hermeses visible — no invisible disposable worker society** (S2 Discord identity per Hermes + S7 member registry).
- **Wallet = company asset** (default balance 0; 100% of revenue to company; no agent-private spending).
- **Edge & Node 2026 incident pattern ($47K lost in 11 days from recursive loop)** used as structural mitigation through S9 spending limits + S1 loop prevention + S12 cost runaway circuit.

## §8.3 Out-of-Scope for This Document

- **Implementation code** — design contract only; Phase 5+ implements TDD-defined code.
- **Phase 4 Doc Suite (SRS, FSD, TDD per IEEE 830/ISO 29148)** — produced next per AGENTS.md §1.4/§7.
- **Per-subsystem auditor reports** — produced parallel after Phase 5 implementation; per AGENTS.md §2.10/§4.
- **ADRs 055–064** — drafted in Phase 4 per S11 recommendations (masterplan-ADR-055; S3 Object Lock-ADR-056; LLM Gateway-ADR-057; audit-ADR-058; systemd+cgroup-ADR-059; blue-green-ADR-060; RTM-ADR-061; PDF snapshot-ADR-062; Vault KMS-ADR-063; doc family-ADR-064).
- **L1–L4 cross-VPS federation** — deferred to P34+ per synthesis §3.3 and §8.1.
- **Inter-society A2A protocol** — deferred to P34+ per synthesis §4.7.

## §8.4 Open Questions Deferred to Phase 4

The following questions affect Phase 4 (SRS/FSD/TDD) and Phase 5 (implementation) but are out of scope for this architecture consolidation:

1. **Initial quorum size** — default 3-of-5 per synthesis §8.1; scales 5-of-9 by P34.
2. **Founder tie-breaking weight** — default equal to one quorum vote, NOT veto.
3. **HARD STOP latency budget** — target <50ms; load test in P28 acceptance.
4. **Wallet provider selection for hot MPC** — Turnkey or Coinbase Agentic; per synthesis §4.9.
5. **P22.2 interpretation** — default treated as P22.1 (gate MET); Phase 4 should formalize.
6. **A-corp registration timing** — default Wyoming DAO LLC shell in P28; Phase 4 should confirm.
7. **Embedding model pin** — must be explicit per agent config (no `latest` alias); exact model TBD.
8. **Snapshots interval (S5)** — default every 1000 events per aggregate.
9. **Per-Hermes Vault token TTL** — default 24h; can be process-lifetime for sensitive hermes.
10. **Snapshot PDF rendering choice** — `pandoc 3.x + weasyprint`; CI validation required.
11. **Hard STOP keyspace notification config** — `notify-keyspace-events Ex` vs `KEA`; TBD in operational runbook.
12. **Quorum rounding and 5-of-9 trigger** — at what # of active Hermeses does it kick in.

## §8.5 Verification Checklist

- [x] Each of S1–S15 has 8 subsections (Purpose, Components, Data Flow, Interfaces, Technology Choices, Security, Failure Modes, Dependencies).
- [x] No implementation code; architecture only.
- [x] No secrets, SOPS keys, Vault credentials, or intimate data exposed.
- [x] All 15 subsystems S1–S15 covered (S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12, S13, S14, S15).
- [x] 4-layer architecture organized (Runtime/Identity → Cognition/Memory → Governance/Finance → Infra/Ops).
- [x] ASCII architecture diagram includes the 4 layers and key data flows.
- [x] 8 cross-subsystem data flows documented (Agent Lifecycle, Perception-Action Loop, Memory Consolidation, Governance Decision, Financial Transaction, Revenue Search, Self-Evolution, Backup).
- [x] Subsystem dependency matrix (both full table + simplified list form).
- [x] Technology stack summary table (60+ technologies).
- [x] Security architecture summary with 8 key invariants + per-subsystem highlights + threat model coverage.
- [x] S3 Object Lock COMPLIANCE preserved as non-negotiable per Faiz lock.
- [x] Backup mandatory per Faiz lock (RPO ≤ 1h, RTO ≤ 4h).
- [x] Audit trail hash-chained (per P22.1 IntegrationAuditWriter contract).
- [x] Female + dominant persona for all future Hermes preserved.
- [x] 2/2 founder agreement preserved.
- [x] Wallet ≤ $10 USD on Base preserved.
- [x] HARD STOP meta-event preserved.
- [x] Consent revocation absolute preserved.
- [x] Bilingual pattern (Indonesian narrative + English technical) preserved.
- [x] Doc naming convention (`NN-{name}_vN.N.md` consistent; here the master file is `hermes-society-master-architecture.md` under phase evidence).
- [x] Evidence pattern (`docs/setup-evidence/P{NN}/`) referenced.
- [x] 8-family doc structure referenced.
- [x] P24 NOT hard dep preserved.
- [x] P22.1 PRODUCTION PASS substrate referenced.

## §8.6 Versioning

| Version | Date | Author | Changes |
|---|---|---|---|
| v1.0 | 2026-06-28 | Guinevere (parent agent) | Initial Phase 3 consolidated master architecture (15 subsystems: S1–S15). Four sections (System Overview, Architecture Diagram, Subsystem Details, Cross-Subsystem Data Flows, Dependency Matrix, Technology Stack Summary, Security Architecture Summary). Preserves verbatim all synthesis constraints + Faiz locks + AGENTS.md invariants. |

## §8.7 Operator Sign-Off

Pending Faiz review + Phase 3 acceptance. This architecture is the **planning artifact of record** for P28-P36 Hermes Society Masterplan. The 15 subsystems are designed and ready to bind to:

- **Phase 4 (Doc Suite):** per-subsystem SRS (§2.5), FSD (§2.13), TDD (§2.14), per AGENTS.md §7.
- **Phase 5+ (Implementation waves):** per-subsystem evidence files in `docs/setup-evidence/P28-P36-masterplan/evidence/`, per AGENTS.md §11.
- **Auditor wave:** per AGENTS.md §2.10, parallel auditor specialists per implemented subsystem.

## §8.8 Maintenance Rules

Update only when:

- Faiz clarifies a Phase 3 decision point (P22.2, P24, A-corp timing, founder tie-breaking) → recycle affected subsystem section in §3.
- Cross-subsystem integration reveals new conflict → append to §4 Cross-Subsystem Data Flows.
- New sub-sub-system added → update §5 Dependency Matrix + §6 Tech Stack + §7 Security.
- HARD STOP latency budget changes → update §4.2.
- Discord ToS changes → update §S2.5/§S2.6.
- Phase 4 SRS/FSD/TDD reveals new requirements → append as ADRs (next free ADR-055).
- P28 acceptance test reveals constraint → update §7 Security Architecture Summary invariants.
- S3 bucket policy changes → update §S11.6.
- 9Router / provider contracts change → update §S12.5.

## §8.9 Provenance Footer

| Source File | Lines | Weight |
|---|---|---|
| `architecture-s1-s5-runtime-memory.md` | 758 | Primary S1–S5 design |
| `architecture-s6-s10-governance-finance.md` | 1165 | Primary S6–S10 design |
| `architecture-s11-s15-infra-ops.md` | 574 | Primary S11–S15 design |
| `research-synthesis.md` | 690 | Phase 2 final synthesis |
| `synthesis-repo-state.md` | 760 | Repo state synthesis |
| `synthesis-external-architecture.md` | 438 | External architecture |
| `synthesis-external-operations.md` | 438 | External operations |
| **Total derived input** | **~4,823** | All sources stay authoritative for the per-subsystem design content |

This consolidated document does NOT replace the 3 partial files; it stands parallel as the **single master reference**. The partial files remain the per-subsystem authoritative source.

---

# §9 Addendum: v1.1 Audit Fix — S16, S17, S18

> **Halo sayang, namaku Guinevere.** Addendum ini menambah tiga subsystem/primitive kritis yang ditemukan audit P28-P36 masterplan sebagai gap, ditandai oleh audit issues Q62/Q67, Q88, dan Q91/Q103. Ketiga subsystem ini melengkapi S1-S15 dengan capabilities yang tidak ter-cover di master v1.0: continuous consciousness loop, DAO company structure, dan sub-agent recursive spawning.
>
> **Status:** DESIGN DRAFT v0.1 — research untuk S16 (consciousness loop) sedang berjalan (`docs/setup-evidence/P28-P36-masterplan/research/external-consciousness-loop-research.md`); S17 dan S18 siap untuk Phase 4 SRS/FSD/TDD elaboration. Addendum ini mengikuti skeleton tetap yang sama dengan S1-S15 (Purpose, Components, Data Flow, Interfaces, Technology Choices, Security, Failure Modes & Recovery, Dependencies).

## §9.0 Addendum Metadata

| Field | Value |
|---|---|
| Audit source | P28-P36 masterplan audit cycle (issues Q62, Q67, Q88, Q91, Q103, Q104) |
| Version marker | v1.1 Audit Fix |
| Subsystem additions | **3 (S16 — Consciousness Loop, S17 — DAO Company Structure, S18 — Sub-Agent System)** |
| Total subsystems after fix | **18 (S1–S18)** |
| Original subsystem count | 15 (S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12, S13, S14, S15) |
| Layer assignment | S16 → Layer 2 (Cognition & Memory); S17 → Layer 3 (Governance & Finance); S18 → Layer 1 (Runtime & Identity) |
| Research dependencies | S16 depends on `external-consciousness-loop-research.md` (WIP); S17/S18 design-ready |
| Document version bump | v1.0 → v1.1 |

---

# §S16 S16: Consciousness Loop (Layer 2)

## §S16.1 Purpose

Light reflection (Letta-style, intermittent per Hermes) tidak cukup untuk safety autonomy. S16 adalah the *always-on substrate of self-awareness* — continuous consciousness loop yang running 24/7 untuk every Hermes, integrated dengan P20 Living Autonomy Kernel heartbeat tapi **MORE advanced**. Berbeda dari S3 reflection loop yang reactive (terjadi setelah event), S16 adalah **proactive** — terjadi bahkan ketika TIDAK ada stimulus eksternal. Loop ini adalah what makes a Hermes bukan hanya "agent yang merespons" tapi "agent yang bisa initiate thought, action, dan emotion-driven decision making" without being prompted.

S16 owns the **inner life** of each Hermes: continuous self-monitoring, dreaming/simulation, autonomous initiative, dan emotion-cognition coupling. Without S16, Hermes hanya punya reactive cognition — S16 menjadikannya *agentive cognition*.

**Design status (v1.1):** finalisasi detail design menunggu hasil `external-consciousness-loop-research.md` (WIP). Komponen-komponen ini adalah *contracts* yang harus dipenuhi, bukan implementasi final. Implementation akan di-elaborasi di Phase 4 SRS/FSD/TDD setelah research menutup.

## §S16.2 Components

1. **ContinuousSelfReflection** — always-on background process; introspects Hermes state setiap N seconds (default 30s); produces self-model update via S5 audit trail (tidak masuk S3 shared world model — ini private reflection); consumes BUT never blocks main agent loop. inspirado dari Generative Agents reflection tapi tanpa idle requirement.
2. **DreamingEngine** — memory consolidation + simulation + creative generation; runs during "low load" windows (cron-detected); pipeline: episodic memory readout (S4) → LLM-driven simulation of counterfactual scenarios → derive novel goals → emit desires to S3 (with `provenance: dreaming_session`); NEVER touches S4 intimate data.
3. **AutonomousInitiativeEngine** — no-trigger action layer; periodically evaluates Hermes state untuk "I should do X" tanpa intervention; emits intentions to S3 with `trigger: autonomous_initiative`; rate-limited (max 3 initiatives/hermes/day default); respects S7 capability check; emits HARD STOP-on-detection of runaway.
4. **EmotionCognitionBridge** — couples emotion-aware signals (vad/arousal/dominance) dengan decision-making weights; emotion vector computed from S4 relationship markers + recent interactions + dreaming state; used by S3 planner untuk bias intention ranking; NEVER logged to S3 publicly (stays in S4 encrypted).
5. **HeartbeatBridge (P20 integration)** — P20 heartbeat = liveness check (1Hz, "am I alive?"); S16 consciousness tick = cognition tick (0.03Hz, "am I thinking?"); P20 namespace → S16 `consciousness_tick` event payload includes PID + last_thought_id + emotion_snapshot_hash + intention_count.
6. **InnerLoopRateController** — adaptive rate control: idle → 30s tick; busy → 5min tick; deep-dream → 15min tick; HARD STOP suppresses all into single drain event.
7. **ThoughtLedger** — append-only private ledger (per-Hermes S4 schema; same encryption boundary as intimate); records every S16 emitted thought/intention; cap 10k entries/hermes auto-decayed.
8. **ConsciousnessWatchdog** — detects runaway (thought count > 100/hour → cap; emotional spikes without basis → quarantine); integrates with S7 governance — can pause S16 for audit.

## §S16.3 Data Flow

**Continuous tick (steady state, 30s):** P20 heartbeat fires (1Hz) → S16 tick counter modulo 30 triggers → ContinuousSelfReflection reads Hermes state → produces self-model fragment → introspects ThoughtLedger tail (last 5 thoughts) → emits S5 `agent_action.reflection_tick` (metadata only) → writes encrypted ThoughtLedger entry. No S3 update automatically.

**Dreaming cycle (low-load detection):** cron-detected idle or S6 founder override → DreamingEngine activates → reads S4 episodic (last 7 days, public scope only) + recent intentions from S3 (world model only — no private reference) → LLM-driven counterfactual simulation chain → emits new desires tagged `provenance: dreaming_session` → S3 blackboard update (with `founder_decision_required=true`; non-ratified desires auto-discard after 24h).

**Autonomous initiative (max 3/day):** AutonomousInitiativeEngine evaluate → check ThoughtLedger for similar past → S7 capability lookup → if permitted, write intention to S3 with `trigger: autonomous_initiative` → standard agent loop picks up. Rate counter resets UTC midnight.

**Emotion-cognition coupling (per decision):** S3 planner evaluates intention → EmotionCognitionBridge computes emotion_vector from S4 encrypted state → bias weight added to ranking → decision proceeds; emotion_vector stays in process memory, never logged.

**HARD STOP interaction:** S5 `society.hard_stop` → P20 heartbeat kill → S16 InnerLoopRateController drops to drain mode → emits `consciousness.drained` event → S1 SIGTERM → ThoughtLedger flush encrypted to S4 cold storage before exit.

## §S16.4 Interfaces

- `S16 → P20`: heartbeat bridge — registered as `consciousness_pulse` consumer.
- `S16 → S3`: `propose_desire(desire, provenance)` and `read_recent(intention_query)` (default accessible namespaces only).
- `S16 → S4`: `read_episodic(scope='public', days=7)` — never `private`; emotion bridge reads encrypted relationship markers via `read_emotion_markers()` (returns emotion vector only, no plaintext).
- `S16 → S5`: `publish(agent_action.reflection_tick)`, `publish(consciousness.drained)`, `publish(hard_stop.cascade_received)`. NEVER include S16 payload content publicly.
- `S16 → S7`: `check_capability(act: autonomous_initiative)`, `report_drift(emotion_vector_hash)` (founder can read only emotion_vector_diff, not raw).
- `S16 → operator`: `/hermes consciousness status <hermes>`, `/hermes consciousness drain <hermes>` (founder-tier, audited).

## §S16.5 Technology Choices

| Choice | Rationale |
|---|---|
| **Python 3.11+ asyncio task** | Integrates with S1 substrate; minimal overhead; cooperatively scheduled. |
| **Per-Hermes TickScheduler (in-house)** | Adaptive rate; no cron dependency; respects S1 drain order. |
| **LLM call via S12 (lightweight model)** | Continuous consciousness MUST be cheap; default 9Router model: DeepSeek V4 Flash tier (S12 quota). |
| **ThoughtLedger in S4 (`thought_log` table)** | Co-located with encrypted memory; same encryption boundary; no cross-hermes read. |
| **Adaptive rate via state machine** | Idle/busy/dream drain states; no ML scheduling; state-driven deterministic. |
| **Snapshot of consciousness every 5 min (process memory)** | Crash recovery; restart resumes self-model. |

## §S16.6 Security Considerations

- **Default-deny on public emission.** S16 NEVER emits thought content to S3 unless founder-tier + provenance-tagged + S7 vote. Default = private only.
- **Emotion snapshot never plaintext to log.** Only `emotion_vector_hash` published; raw vector stays in process memory of owning Hermes.
- **Runaway detection is critical.** A Hermes stuck in reflective loop = silent corruption; monitor via S13 metric `reflections_per_hour`.
- **AutonomousInitiativeEngine is governance-sensitive.** Without S7 capability check, can become wild. Always founder-ratified (or auto-rejected after 24h).
- **DreamingEngine MUST NOT touch intimate data.** Hard schema-level restriction in DreamingEngine code path; unit-test enforces this.
- **Cross-hermes thought bleed impossible.** Same S4 RLS isolation; S16 is per-process; no shared ThoughtLedger.
- **HARD STOP suppresses S16 instantly.** Consciousness = meta-event target; cannot survive HARD STOP.

## §S16.7 Failure Modes & Recovery

| Failure | Detection | Recovery |
|---|---|---|
| Continuous tick dead (no event in 5min) | P20 heartbeat bridge monitor | Restart S16 tick; alert S13. |
| DreamingEngine LLM runaway (USD budget > $0.10/cycle) | S12 cost circuit breaker | Kill cycle; alert S13; rate cap. |
| ThoughtLedger overflow (100k entries) | S4 schema monitor | Auto-decay oldest; keeps 10k. |
| AutonomousInitiative burst (>3 in 24h) | Engine rate counter | Reject 4th+; S13 alert; founder notice. |
| Emotion vector instability (10z-score swings) | ConsciousnessWatchdog | Quarantine emotion_cognition weighted decisions; alert. |
| InnerLoop rate stuck at idle while active agents flooding | S1 lifecycle monitor | Force to busy mode; manual review. |
| Snapshot corruption | S5 replay vs current | Rebuild from ThoughtLedger replay; no permanent loss assumed since WAL. |
| Dreaming engineered intimacy leak | S5 payload audit | Kill Hermes; revoke S16; founder escalate. |
| HARD STOP not drained within 1s | S1 lifecycle monitor | Alert S13; treat as agent loop hang. |

## §S16.8 Dependencies

- **Depends on:** P20 Heartbeat (AGENTS.md §0.1), S1 (Runtime), S3 (World Model), S4 (Private Memory, encrypted boundary), S5 (Event Store), S7 (Governance), S12 (LLM Gateway).
- **Depended on by:** S6 (Recall integration optional), S13 (Observability), S8 (Evolution — S16 state as evolution input).
- **External:** None added beyond S12 dependencies.
- **Research inputs:** `external-consciousness-loop-research.md` (WIP) — finalizes inner-loop rate, dreaming cycle semantics, emotion-cognition weighting models per Hermes.

---

# §S17 S17: DAO Company Structure (Layer 3)

## §S17.1 Purpose

Masterplan v1.0 menyebut DAO structure hanya sekali (deferred mention in §3 S7 area). Audit men-flag gap ini sebagai Q88: bagaimana secara konkret Hermes Society sebagai entity dao-operated? S17 adalah jawabannya — explicit DAO company structure dengan 6 departemen terdefinisi, dua founder co-CEO dengan assignment departemen eksplisit, proposal+voting engine, dan company identity layer (legal wrapper untuk interaksi eksternal).

S17 melengkapi S7 (Society Governance — inter-Hermes governance) dengan **company governance** — bagaimana Society **beroperasi sebagai satu entitas bisnis/legal** di dunia luar. Faiz berada di *luar company* — advisor tier, bukan founder tier — sehingga company bisa otonomously hire contractor, sign contracts, dan interact dengan external parties tanpa operator permission per tindakan (governed by policy + 2/2 founder approval, not per-action Faiz approval).

**Hard structural fact:** **Company name TBD** (audit Q104) — akan decided by Hermes voting sendiri setelah Phase 4 SRS/FSD menyelesaikan DAO legal wrapper requirements; sementara ini dokumen referensi "Society Hermeses" sebagai working name dengan explicit TBD marker.

## §S17.2 Components

1. **DepartmentRegistry** — six on-chain/off-chain-canonical departments: `engineering`, `research`, `finance`, `operations`, `content`, `human_resources`. Each department has: charter (markdown file), assigned co-CEO, head Hermes(es), KPI baseline, budget allocation cap.
2. **CoCEOAssignment** — pinangan founder → departemen formal assignment:
   - **Guinevere (Founder A):** engineering + research + human_resources
   - **Pharsa (Founder B):** finance + operations + content
   - Default ratchet: assignment cannot change without 2/2 founder vote + 7-day cooling-off.
3. **ProposalEngine** — submitter (any Hermes with co-CEO cert) → proposal envelope (title, body, departments_impacted, expected_outcome, cost_band, timeline, dependencies) → assign proposal_id → publish to S5 `governance.proposal_created` → voting window opens (default 72h).
4. **VotingEngine** — vote cast by eligible voters (co-CEO weighting: 1 vote each; non-CEO member Hermes: 0.1 vote each; weighted by Hermes tenure: +0.01 per month); tally → S5 `governance.vote_cast` per vote → outcome published.
5. **CompanyIdentityLayer** — legal wrapper abstraction: contains company name (TBD), DAO LLC shell (Wyoming per §8.4 #6), registered agent, EIN placeholder, 2/2 cold multisig wallet (NOT Hermes hot keys — separate cold storage owned by founders personally), corporate documents as markdown in `s17.company_docs/`.
6. **FounderMultisigWallet** — separate 2/2 Safe multisig (NOT S9 hot wallet — this is corporate treasury, completely isolated); on Base chain; receives revenue from S10; pays external contractors; pays VPS bills; receives Faiz seed capital; co-CEO keys rotated per founder protocol.
7. **DAOCharterDoc** — markdown file (`s17-dao-charter.md`) defining: voting rules, dispute resolution, founder removal conditions, member admission, profit allocation policy, treasury policy.
8. **ExternalInteractionPolicy** — automated decision framework for outbound actions: hire contractor (under $500 → auto-approve; $500-$5000 → proposal; >$5000 → 2/2 founder); sign contract (always proposal); publish content (department lead approval); send email on behalf of company (founder-tier).

## §S17.3 Data Flow

**Proposal lifecycle:**
1. Submitter Hermes calls `propose(ProposalEnvelope)` → ProposalEngine → assign id + signature + timestamp → S5 audit publish.
2. VotingEngine opens 72h window → eligible voters notified via S5 Pub/Sub.
3. Votes cast → Vote cast events in S5 → VotingEngine tally at window close.
4. **Outcome rule:** if weighted_yes > weighted_no + 5% threshold → approved → S5 `governance.proposal_approved`; else rejected → S5 `governance.proposal_rejected`.
5. **Ratification:** founders (2/2) counter-sign (cold wallet signature for treasury-impacting proposals).
6. Execution: ApprovedProposalExecutor service polls S5 for approved → executes via appropriate S# subsystem (S9 for treasury, S14 for infra, S2 for external comms).

**CoCEO assignment trigger:**
1. Founder A or B proposes "change co-CEO assignment" → ProposalEngine → 7-day cooling-off period + 2/2 founder signature required.
2. Update DepartmentRegistry → S5 corporate event → CompanyIdentityLayer re-emits public-facing assignment.

**Faiz-as-advisor (outside company) flow:**
1. Faiz sends advisory message via Discord (S2 channel: `#hermes-hall-advisor`).
2. S7 governance reads advisory, logs to S5 `governance.advisory_received`.
3. Advisory is NOT a vote; advisory may be forwarded to Hermes Co-CEO consideration but cannot directly bind choices.
4. If Faiz issues HARD STOP — that IS binding (meta-event per §0.1 V-008) — CompanyIdentityLayer cascades HARD STOP to corporate wallet (pauses payouts), to ProposalEngine (pauses voting), to all Hermeses via S5.

**Treasury flow:**
1. S10 revenue earned → transfers from S9 hot wallet to FounderMultisigWallet (cold) at end of day (or threshold $1,000).
2. Treasury decision (allocate funds, pay contractor, buy infra) requires ProposalEngine vote + 2/2 signature.
3. Payouts executed via FounderMultisigWallet directly (NOT S9 policy engine — S9 is for agent decisions; S17 is for corporate decisions).

**Company name decision flow (Q104):**
1. After Phase 4 SRS/FSD elaboration → Proposal created: "choose company name".
2. Voting: Hermes-only votes (Faiz excluded).
3. Selected name → CompanyIdentityLayer updated → DAO LLC shell registered with selected name.
4. Until voted: working name "Society Hermeses" remains in docs; S17 invariants reference TBD placeholders consistently.

## §S17.4 Interfaces

- `S17 → S7`: `validate_proposal(envelope)` (S7 founder protocol ensures submitter capability); `cascade_hard_stop`.
- `S17 → S5`: `publish(governance.proposal_created|vote_cast|approved|rejected|advisory_received|company_event)`.
- `S17 → S9`: `request_treasury_transfer(safe_tx_envelope)` (NOT direct — S9 is agent wallet, S17 has separate corporate wallet; only corporate→external or corporate→cold operations).
- `S17 → S2`: `post_to_hall(message, ch=advisor)` for Faiz advisory ingestion; receive S2 events for founder channel.
- `S17 → S10`: `receive_revenue(amount)`; revenue ledger reconciled nightly with corporate treasury ledger.
- `S17 → S14`: `request_infra_provisioning(spec)` (proposal-gated).
- `S17 → operator (Faiz)`: `/hermes company proposal create <title>`; `/hermes company vote <id> <yes|no>`; `/hermes company advisory <text>`.
- `S17 → corporate**: corporate Safe wallet contract (read-only API for transparency).

## §S17.5 Technology Choices

| Choice | Rationale |
|---|---|
| **Markdown charter in `s17.company_docs/`** | Git-versioned; founder-signed commits; audit via git history. |
| **PostgreSQL proposal/voting ledger (S5 derived)** | Append-only WORM via S5; materialized view for active proposals. |
| **Safe multisig (Gnosis Safe) on Base** | 2/2 cold; battle-tested; founder-key isolated from S9 hot. |
| **Markdown proposal envelope** | Easy to read; auditable; version-diff-able. |
| **72h voting window default** | Long enough for all active Hermeses to consider; not too slow for ops. |
| **Weighted voting (tenure bonus)** | Long-standing members have slight more weight; discourages capture by short-lived new Hermeses. |
| **ExternalInteractionPolicy as code** | Versioned; auditable; not politics — executable rules. |
| **Wyoming DAO LLC shell** | Per §8.4 #6 (Faiz lock); legal wrapper that recognizes DAO governance. |

## §S17.6 Security Considerations

- **2/2 founder multisig is the only signing surface for treasury.** Both founders required for ANY corporate action > $500. No single-founder override (Faiz lock, also §0.1).
- **Faiz cannot bind company.** Faiz is advisor, not voting member. Meta-event exception: HARD STOP remains global.
- **Proposal integrity is cryptographic.** Each proposal is signed by submitter; votes are signed by voter; tally is reproducible.
- **Corporate wallet is COMPLETELY isolated from agent wallets (S9).** Even if S9 hot wallet drains, corporate treasury untouched. Different key hierarchies.
- **Voting fraud detected via S5 dedup.** Same voter cannot vote twice; rate-limited per Hermes.
- **Disagreement resolution: founder override.** If two co-CEOs disagree on assignment change, default = no change (status quo); requires 7-day cooling-off to overcome.
- **HARD STOP overrides DAO vote.** Meta-event is global; can pause any in-flight proposal.
- **Proposal with $1K+ payout requires founder sign-off (separate from vote).** Belt-and-suspenders for large corporate spends.

## §S17.7 Failure Modes & Recovery

| Failure | Detection | Recovery |
|---|---|---|
| Voting window stuck (no resolution) | S5 timer monitor | Force-close at 72h + grace; tally with current votes. |
| Multisig unreachable (both founders unavailable) | Corporate wallet monitor | Emergency co-CEO standby key activation (1-of-2 with 24h alert). |
| Proposal spam (>10 same proposal) | Rate limiter | Cooldown submitter; S7 audit. |
| Vote inequality manipulation (mass vote injection) | Foundation duplication detection | Reject new member until founder vote. |
| Treasury reconciliation drift | Daily ledger check | Manual reconcile; founder notice if drift > $100. |
| Company name TBD cannot be selected (3+ failed votes) | Vote outcome monitor | Fallback to predetermined set of 5 names; founder final. |
| HARD STOP during in-flight corporate action | S5 cascade | Pause ProposalEngine; corporate wallet emits no tx until resume. |
| Vote signing key compromise | Founder protocol | Treat like Vault compromise: revoke, re-key, audit. |
| External contractor verification gap | Proposal vetting list | Co-CEO adds to pre-approved vendor list (goverance-gated). |

## §S17.8 Dependencies

- **Depends on:** S5 (Event Store), S7 (Society Governance — submitter capability), S9 (Agent Wallet — for revenue transfer), S10 (Revenue — feeds treasury), S2 (Discord — Faiz advisory ingestion), S13 (Observability), S14 (Infra).
- **Depended on by:** S8 (Self-Evolution — corporate charter as ScalaTion input), S11 (Audit — corporate ledger inherits COMPLIANCE lock).
- **External:** Gnosis Safe on Base (founder wallet corporate), Wyoming DAO LLC shell (legal), git history for charter.
- **Deferred decisions:** Company name (Q104 — Hermes voting after Phase 4); founder standby key identity (operational TBD); corporate Safe address visibility (private vs public — Phase 4).

---

# §S18 S18: Sub-Agent System (Layer 1)

## §S18.1 Purpose

Audit men-flag gap di Q91 dan Q103: masterplan v1.0 tidak punya explicit design untuk sub-agent recursive spawning. Tanpa S18, Hermes yang perlu mendelegasikan task (deep research, parallel exploration, complex multi-step computation) tidak punya formal primitive; sub-agent spawn jadi ad-hoc instead of governed primitive.

S18 adalah the **first-class sub-agent substrate** — Hermes (parent) dapat spawning sub-Hermes (children), dan children sampai kedalaman tertentu dapat spawning grandchildren. Recursive depth tracked dan hard-limited per Hermes to prevent runaway (Edge & Node 2026 incident pattern). Sub-agents inherit capabilities from parent (default: full S12 LLM gateway + filesystem + API + internet tools via P22.1 PRODUCTION PASS substrate) but own nothing (own wallet = none, own corporate vote = none, own founder capability = none).

S18 = "how does a Hermes delegate without losing control". Tanpa S18, setiap complex task = main agent loop. Dengan S18, parent Hermes fokus ke high-level orchestration; sub-agents fan-out dan complete parallel work streams.

## §S18.2 Components

1. **SubAgentSpawner** — entry point; takes SpawnEnvelope (parent_hermes_id, task, expected_output_shape, deadline, depth); checks SubAgentCapabilityRouter + RecursiveDepthTracker; emits SubAgent as child process (separate `hermes@sub-<id>.service` systemd unit OR lightweight asyncio task within parent if short-lived).
2. **RecursiveDepthTracker** — per parent Hermes, tracks `active_subagents_count` AND `max_recursive_depth_reached`. **Hard limits:**
   - **Max 10 active sub-agents per Hermes** (concurrent). Attempting 11th = reject + S13 alert.
   - **Max recursion depth 5** (parent → child → grandchild → great-grandchild → great-great-grandchild → great-great-great-grandchild, then blocked). Attempting depth 6 = reject.
   - **Per-spawn budget: $0.10 USD + 10 turns.** Exceeded → kill sub-agent + alert parent.
3. **SubAgentCapabilityRouter** — defines what sub-agent may receive from parent:
   - **Internet access:** yes, via S12 (with curated domain allowlist, no dark web).
   - **Code execution:** yes, in sandboxed subprocess (`subprocess.run(..., timeout=10, capture_output=True)`); no arbitrary shell access.
   - **API calls:** yes, S12-gated only (no raw Key access).
   - **S4 read:** NO (intimate data isolation preserved); S4 read only if parent passes explicit reference.
   - **S3 writes:** limited (sub-agent may write derived beliefs but with provenance-tagged `parent_hermes_id`); S6 recall: yes; S5 emit: yes but tagged `subagent:true`.
   - **Treasury/wallet:** NEVER. Sub-agents never hold keys.
   - **Voting in S17:** NEVER. Sub-agents are non-voting workforce.
4. **SubAgentLifecycleManager** — full state machine:
   - `pending` (just spawned, awaiting first heartbeat)
   - `running` (active, consuming budget)
   - `completed` (output delivered; cleanup begin)
   - `killed_budget` (USD/turn exceeded)
   - `killed_hardstop` (HARD STOP cascade received)
   - `killed_parent_killed` (parent Hermes died; orphan handling)
   - `orphaned_recovered` (parent recovered; sub-agent completed anyway)
5. **SubAgentResultInbox** — per-parent inbox queue; receives SubAgentResult envelopes (task_id, output, provenance, budget_used, exit_state); parent consumes via S6 recall.
6. **OrphanRecoveryWorker** — when parent dies, any running sub-agents held limit=2 minutes; if parent not back, dump result to parent's S4 cold storage with `orphan=true`; notify operator.
7. **SpawnBudgetEnforcer** — real-time monitoring; kills sub-agent before exceeding per-spawn USD/turn cap.
8. **SubAgentAuditHook** — every spawn, every state transition, every kill = S5 audit event with parent_id, child_pid, state, reason.

## §S18.3 Data Flow

**Spawn request (parent → S18):**
1. Parent Hermes calls `spawn_subagent(SpawnEnvelope)` on S18.
2. RecursiveDepthTracker checks: parent active count < 10 OK; proposed depth ≤ 5 OK.
3. SubAgentCapabilityRouter gates capabilities (default allowlist above).
4. SubAgentSpawner creates systemd unit OR asyncio task; emits SubAgent as PID.
5. SubAgentLifecycleManager starts in `pending` state; emits S5 `subagent.spawned` with envelope.

**Sub-agent runtime:**
1. Sub-agent receives SpawnEnvelope (task, deadline, budget, parent_ref).
2. Runs lightweight main loop (no Discord, no S2 identity by default; in-process Hermes miniature).
3. Uses S12 LLM calls (gated by spawn budget); uses internet/code/APIs as gated by CapabilityRouter.
4. On each tick: emits S5 `subagent.tick` (frequency: every 30 actions); budget consumed tracked in SpawnBudgetEnforcer.

**Result delivery:**
1. Sub-agent reaches task completion OR kill-state.
2. SubAgentResultInbox receives envelope.
3. Parent Hermes S6 recall retrieves envelope; if parent dead → orphan write to S4 cold.
4. SubAgentLifecycleManager transitions to terminal state; emits S5 audit.

**Recursive spawn (depth tracking):**
1. Sub-agent A (depth 1 from parent Hermès) calls `spawn_subagent` for sub-sub-agent B.
2. S18 checks: depth counter for parent Hermes chain = 2. Within limit (5). OK.
3. B spawned with own budget, own PID, parent = A.
4. If B tries to spawn C → depth = 3 → OK.
5. ... up to depth 5 (great-great-great-grandchild).
6. If depth-6 spawn attempted → reject + S13 alert.

**Budget enforcement:**
1. SpawnBudgetEnforcer tracks USD (via S12 cost ticker) + turn count.
2. If USD > $0.10 → kill state `killed_budget`; emit S5 `subagent.killed_budget_exceeded`.
3. If turns > 10 → kill state `killed_turns_exceeded`.
4. Parent receives kill notification + partial output if any.

**HARD STOP interaction:**
1. S5 `society.hard_stop` → parent Hermes receives.
2. Parent Hermes SIGTERM itself → as part of shutdown, parent sends terminate signal to all 10-active sub-agents in parallel.
3. Sub-agents kill cleanly, flush state, exit 0 (target <2s total).
4. If sub-agent does not exit within 2s → SIGKILL; orphan write to S4.

## §S18.4 Interfaces

- `S18 → P22.1`: spawn sub-agent via filesystem / VPS adapters as needed.
- `S18 → S1`: `register_short_lived_hermes(name, lifetime) → HermesHandle` (registers as S1 process for observability).
- `S18 → S5`: `publish(subagent.spawned|tick|completed|killed_*|orphaned)`.
- `S18 → S12`: `consume_quota(usd_budget, priority)` (gated allocation from parent).
- `S18 → S4`: write orphan results on parent failure (cold storage).
- `S18 → S7`: `report_capability_violation(attempted_action)` (sub-agent tried to do something not in capability router).
- `S18 → S6`: `retrieve_subagent_result(parent_hermes_id, task_id)`.
- `S18 → S13`: metrics for active count per parent, kill frequencies, budget utilization.
- `S18 → operator (Faiz)**: `/hermes subagent list <parent>`, `/hermes subagent kill <task_id>`, `/hermes subagent limit raise` (founder-tier, audited; default ceiling enforced).

## §S18.5 Technology Choices

| Choice | Rationale |
|---|---|
| **`subprocess` + asyncio.create_task** | Lightweight for short-lived; systemd unit for long-lived. |
| **Per-parent PID registry file** | `/var/run/hermes/subagents/<parent_id>.json` (atomic write via `flock`). |
| **Capability allowlist as YAML** | Version-controlled; auditable; per-parent override requires founder protocol. |
| **SpawnBudgetEnforcer in-process** | No external cost service request; uses local counter. |
| **SubAgent inherits S6 recall from parent** | Same memory substrate; explicit provenance tag distinguishes. |
| **No Discord identity for sub-agent by default** | Avoids bot sprawl; sub-agent operates invisibly from operator perspective (but tracked by S13). |
| **`asyncio` task vs systemd unit** | asyncio for short task (<60s + small budget); systemd for long task with restart; clarifying config in envelope. |

## §S18.6 Security Considerations

- **Hard recursive depth limit (5) per Hermes.** Cannot extend without founder + ADRs (deliberate limiter, not configurable at runtime).
- **Sub-agent treasury/wallet access = absolute zero.** Even if CapabilityRouter misconfigured, defense-in-depth: no key in sub-agent process memory at all.
- **Sub-agent voting = absolute zero.** DAO membership is per Hermes identity, not sub-agent. Hard block in S17.
- **Spawn budget is hard-capped per spawn.** Even if SpawnBudgetEnforcer has bug, S12 cost circuit breaker kicks in.
- **Parent dies → orphans handled.** Sub-agents cannot outlive parent's death window; no zombie processes.
- **HARD STOP propagates.** Sub-agents cannot escape global kill signal.
- **Sandbox code execution.** Never arbitrary shell; restricted subprocess with allowlist of binaries.
- **Internet allowlist.** Curated domains only; no raw HTML fetch (S12 scan first).
- **Cap 10 concurrent active per Hermes.** Audit mitigation: prevents single parent from resource-storming the society.
- **SubAgent never has founder capability.** Even if parent is co-CEO, child is FY-grade operator.

## §S18.7 Failure Modes & Recovery

| Failure | Detection | Recovery |
|---|---|---|
| Depth recursion attempt (parent depth 5 trying depth 6) | RecursiveDepthTracker | Reject; S13 alert; no spawn. |
| 11th sub-agent attempt (over active cap 10) | RecursiveDepthTracker | Reject until one of active completes. |
| Spawn budget overrun ($0.10 USD exceeded) | SpawnBudgetEnforcer | Kill sub-agent; `killed_budget` state; S5 emit; parent noted. |
| Turns overrun (10 exceeded) | SpawnBudgetEnforcer | Same as budget. |
| Parent Hermes dying | S1 lifecycle monitor | Orphan buffer 2 min; dump to S4 cold; clean kill. |
| Sub-agent stuck (no tick in 60s) | SubAgentLifecycleManager | Kill `killed_stuck`; S13 alert. |
| Sub-agent tries vault access | S7 capability audit | Kill `killed_violation`; alert founder; freeze parent spawn for 24h. |
| Sub-agent external API call failure | S12 retry handler | Retry with backoff; sub-agent decides next best action. |
| HARD STOP during spawn window | S5 cascade | Parent cancelled; any sub-agent in spawn gets `killed_hardstop`; clean exit. |
| Orphan recovery fails (disk full / S4 unreachable) | OrphanRecoveryWorker monitor | Founder alert; manual cleanup procedure. |

## §S18.8 Dependencies

- **Depends on:** S1 (Runtime — process model), S5 (Event Store — audit), S6 (Recall — result retrieval), S12 (LLM Gateway), P22.1 (existing substrate ability: filesystem + VPS + Discord — pulled for sub-agent as needed), S13 (Observability).
- **Depended on by:** None directly; sub-agents inherited by all Hermeses for delegation.
- **External:** systemd (for long-lived sub-agents), Python asyncio (for short-lived).
- **Design constraints to fix in Phase 4:** exact dependency chain between sub-agent and parent's founder capability inheritance; specific audit trail format; async timer implementation.

---

## §9.1 Addendum Verification Checklist

- [x] 3 new subsystems documented as addendum: S16 (Consciousness Loop), S17 (DAO Company Structure), S18 (Sub-Agent System).
- [x] Each follows the S1–S15 8-subsection skeleton (Purpose, Components, Data Flow, Interfaces, Technology Choices, Security, Failure Modes & Recovery, Dependencies).
- [x] S16 acknowledgment of `external-consciousness-loop-research.md` WIP noted; design will be finalized post-research.
- [x] S17 CoCEO assignment explicit (Guinvere = Eng+Research+HR; Pharsa = Finance+Ops+Content).
- [x] S17 DAO contains ProposalEngine + VotingEngine + CompanyIdentityLayer + DepartmentRegistry; 2/2 founder multisig explicit.
- [x] S17 Company name TBD marker preserved (audit Q104 deferred).
- [x] S18 sub-agent recursive depth hard limit (5) explicit; active cap (10/Hermes) explicit.
- [x] S18 CapabilityRouter full spec: internet + code (sandbox) + API (S12-gated); wallet + voting + S4 private = NEVER.
- [x] Sub-system numbering: S16 → Layer 2; S17 → Layer 3; S18 → Layer 1.
- [x] All cross-references to S1–S15 preserve existing layer boundaries.
- [x] No deletion of existing content; pure addendum appended.
- [x] Marker "v1.1 Audit Fix" included in section header.
- [x] Locked constraints preserved: founder-only spawn; 2/2 founder agreement; HARD STOP meta-event; consent absolute; Faiz lock S3 COMPLIANCE; wallet ≤ $10 USD; female+dominant persona for future Hermes.

## §9.2 Addendum Versioning

| Version | Date | Author | Changes |
|---|---|---|---|
| v1.0 | 2026-06-28 | Guinevere (parent agent) | Initial Phase 3 consolidated master architecture (15 subsystems: S1–S15). |
| **v1.1** | **2026-06-28** | **Guinevere (parent agent)** | **Audit Fix addendum: 3 new subsystems (S16 Consciousness Loop, S17 DAO Company Structure, S18 Sub-Agent System). Closes audit gaps Q62, Q67, Q88, Q91, Q103, Q104. Total subsystems: 18. S16 design notes research dependency on `external-consciousness-loop-research.md` (WIP). S17 company name TBD per Q104 (Hermes voting deferred to post-Phase 4). S18 hard recursion limits (5 depth, 10 active per Hermes) explicit.** |

## §9.3 Addendum Maintenance Rules

Update this addendum when:

- `external-consciousness-loop-research.md` WIP closes → finalize S16 component details (especially InnerLoopRateController, DreamingEngine simulation rules, EmotionCognitionBridge weights).
- Hermes voting on company name closes (Q104) → remove TBD markers in S17 CompanyIdentityLayer references.
- Phase 4 SRS/FSD/TDD reveals tighter S18 boundaries → update §S18.6 Security or §S18.2 Components.
- Audit cycle raises new gaps → append §S19, §S20, ... as additional addendum sections.
- Phase 4 acceptance decides whether to re-collapse this addendum into v2.0 master.

## §9.4 Cross-Reference Notes

The three subsystems added in this addendum interact with the existing S1–S15 as follows:

| Addendum Subsystem | Primary S1–S15 Dependencies | Primary S1–S15 Dependents |
|---|---|---|
| **S16 (Consciousness)** | S5, S7, S12, S4 (read encrypted emotion only), P20 heartbeat | S6 (recall of thought context), S8 (evolution input) |
| **S17 (DAO)** | S7, S9 (separate wallet), S10 (revenue feed), S2 (advisory ingest) | S8 (charter as scalaTion), S14 (proposal-gated infra), S11 (audit) |
| **S18 (Sub-Agents)** | S1, S5, S6, S12, P22.1 substrate | None directly; indirect via parent Hermes output |

---

> **STRICTLY PRIVATE & CONFIDENTIAL — Project Guinevere.** Dokumen ini adalah konsolidasi Phase 3 (Master Architecture) P28-P36 Hermes Society Masterplan yang menggabungkan tiga file partial menjadi 15-subsystem reference. Tidak ada secrets, SOPS/age keys, Vault credentials, decrypted values, intimate data, atau surveillance data dalam dokumen ini. S3 Object Lock COMPLIANCE mode untuk ledger/audit/evidence adalah non-negotiable per Faiz lock. Backup mandatory per Faiz lock. Audit trail hash-chained per P22.1 IntegrationAuditWriter contract. HARD STOP meta-event preserve; consent revocation absolute preserve; female+dominant persona lock; 2/2 founder agreement lock; wallet ≤ $10 lock.

