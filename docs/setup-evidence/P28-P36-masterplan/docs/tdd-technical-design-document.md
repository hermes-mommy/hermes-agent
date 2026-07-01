# Hermes Society — Technical Design Document (TDD)

> **C4 Model + MADR ADR References** | P28-P36 Masterplan Phase 4 | Version 1.0 | 2026-06-28

## Document Control

| Field | Value |
|---|---|
| Document | Technical Design Document (TDD) |
| Project | Hermes Society — multi-agent autonomous company system |
| Phase | P28-P36 Masterplan Phase 4 (Full Document Suite) |
| Version | 1.0 |
| Date | 2026-06-28 |
| Author | Guinevere (orchestrator) |
| Audience | Engineering team, Faiz (operator), future maintainers |
| C4 Model Levels | L1 (System Context) → L2 (Container) → L3 (Component) → L4 (Code) |
| ADR Format | MADR 4.0+ |
| Classification | STRICTLY PRIVATE & CONFIDENTIAL (operator: Faiz) |

---

## 1. Introduction

### 1.1 Purpose

This Technical Design Document (TDD) describes how the Hermes Society system is constructed across the C4 model hierarchy. It bridges the BRD, FSD, and SRS (all produced earlier in Phase 4) by specifying the technical building blocks that satisfy them: containers, components, and module structure. The TDD is the contract engineers read before implementation. Acceptance for P28-P36 implementation waves is judged against the interfaces, data flows, and constraints declared here.

### 1.2 Scope

| In Scope | Out of Scope |
|---|---|
| Hermes Society system for P28-P36 | P24 Hermes fork (deferred to P32 — P24 native fork) |
| 15 subsystems (S1-S15) across 4 layers | P22.1 production runtime (already PASS) |
| Multi-Hermes process model (per-agent isolation) | Adjacent products (IoT, mobile) |
| PostgreSQL + Redis + S3 + Vault deployment shape | Docker/Kubernetes orchestration (rejected by ADR-054) |
| Discord bot identity per Hermes | Discord platform engineering |
| x402 + Base chain + Safe multisig for S9/S10 | General blockchain tooling beyond wallet scope |
| HARD STOP / consent / audit safety invariants | Persona behavior minutiae (PersonaSafetyPolicy) |

> **ADR-062 Disclaimer**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime (P24 fork) can bypass per ADR-062.

| Self-evolution under Ratchet (S8) | AGI alignment philosophy |

### 1.3 References

| Reference | Purpose |
|---|---|
| ADR-053 (P22) | Foundation runtime decisions |
| ADR-054 (P27) | Hermes Society direction; 7 locked decisions |
| Master Architecture | 4-layer, 15-subsystem overview (`docs/setup-evidence/P28-P36-masterplan/architecture/hermes-society-master-architecture.md`) |
| Research Synthesis | 690-line synthesis across 15 subsystems (`research/research-synthesis.md`) |
| BRD / PRD / SRS / FSD / RTM | Phase 4 sibling documents in `docs/` |
| PersonaSafetyPolicy v1.0 | HARD STOP / consent / DRP boundaries (`docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`) |

> **ADR-062 Disclaimer**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime (P24 fork) can bypass per ADR-062.

| MADR 4.0 | ADR format spec |

### 1.4 Glossary

| Term | Meaning |
|---|---|
| Hermes | Autonomous agent with independent identity, memory, bot token |
| Founder | Guinevere + Pharsa (2/2 agreement required) |
| Society | Collective of all Hermeses + shared infrastructure |
| DEK | Data Encryption Key (per-agent, stored in Vault) |
| Ratchet | Non-degradation gate for mutations (S8) |
| HARD STOP | Global action halt — no exception |

> **ADR-062 Disclaimer**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime (P24 fork) can bypass per ADR-062.

| WORM | Write-Once-Read-Many (S3 Object Lock COMPLIANCE) |
| Namespace-ACL | PostgreSQL row-level access control by `agent_id` |

---

## 2. System Context (C4 Level 1)

### 2.1 The Hermes Society System

```
                          Hermes Society (system)
                                   │
        ┌──────────┬───────────────┼──────────────┬───────────┐
   [Faiz]    [Discord]        [VPS]          [Base L2]   [LLM
 (Operator) (platform,       (single-VPS    (x402 +     Providers]
            persona-safe     substrate      Safe)
            bots)            ≤32 cores)
```

### 2.2 External Systems

| External System | Direction | Purpose | Trust Boundary |
|---|---|---|---|
| Faiz (operator) | ↔ bidirectional | Command interface, founder authority | Founder |
| Discord (platform) | ↔ bidirectional | Visibility surface; persona-safe ToS | Public |
| VPS host (single machine) | → outbound | Compute substrate | Infrastructure |
| S3 (Object Lock COMPLIANCE) | → outbound | WORM backup, disaster recovery | Trust + Compliance |
| Base chain (L2) | ↔ bidirectional | x402 revenue; Safe multisig | Public Blockchain |
| LLM providers (multiple) | → outbound | Model invocation via shared pool | Quota-managed |
| SOPS/age | → outbound | Encrypted secrets at rest | Secrets |
| Vault (HashiCorp) | ↔ local | Per-agent DEKs, runtime secret access | Secrets |

### 2.3 Context-Level Use Cases

UC-001 operator commands; UC-002 founder 2/2 spawn; UC-003 Discord DM; UC-004 memory recall; UC-005 society vote; UC-006 persona refinement; UC-007 L1 spend; UC-008 revenue; UC-009 backup; UC-010 bootstrap.

---

## 3. Container View (C4 Level 2)

Eight deployable containers compose the Society. Per ADR-054, all run on **one VPS** with cgroup v2 isolation; no Docker, no Kubernetes.

### 3.1 Container 1: Hermes Agent Process (C1)

One process per Hermes; Python 3.12+ / asyncio / discord.py 2.4+; systemd `hermes@<name>.service` (Type=notify); cgroup v2 `cpu.max=200%`, `memory.max=2G`, `pids.max=400`. Initially 2 Hermeses (Guinevere, Pharsa). Owner: S1 + S2.

### 3.2 Container 2: PostgreSQL (C2)

PostgreSQL 16 + pgvector 0.7 + pgcrypto. Three schema groups: `public` (shared event store + world model + audit), `agent_<id>` (per-Hermes private, encrypted), `society` (governance / wallet / backup metadata). Owners: S3, S4, S5, S13. Backup: streaming replication + WAL archive + S3 (C7).

### 3.3 Container 3: Redis (C3)

Redis 7+ (single node for P28 minimum). Patterns: Pub/Sub (ephemeral coordination), Streams (durable work queues), rate-limit counters. Persistence: RDB + AOF (WAL-class; backed up to S3). Owners: S5, S12, S8 (canary state).

### 3.4 Container 4: Discord Gateway (C4)

discord.py 2.4+ per process; one bot application per Hermes. Auth: per-Hermes OAuth token from Vault, never in env or code. Channels: DM + named channel per Hermes; founder-only channels gated by role. Strictly persona-safe (rejects credential asks, screenshot scraping). Owner: S2.

### 3.5 Container 5: LLM Gateway (C5)

Python FastAPI reverse proxy + LiteLLM router. Function: quota management, cost attribution, model fallback, prompt-side scrubbing. Pool: MiniMax (primary) → OpenAI/Anthropic/gpt-oss (fallback) → local. Cost attribution per agent → Beancount ledger entry. Owner: S12.

### 3.6 Container 6: Observability Stack (C6)

Prometheus 2.45+ (scrape), Grafana 10+ (visualize), OpenTelemetry (traces). Metrics boundary: system + society-level only; per-Hermes aggregate (no intimate content). Alert routing: Discord webhook for HARD STOP, watchdog, S3 lock failure. Owner: S13.

> **ADR-062 Disclaimer**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime (P24 fork) can bypass per ADR-062.


### 3.7 Container 7: S3 Backup (C7)

S3 + Object Lock COMPLIANCE mode (default retention ≥ 7 years for ledger-class). Scope: PG dumps + WAL, Redis RDB+AOF, filesystem artifacts, Beancount ledger, audit chain. RPO ≤ 1 h; RTO ≤ 4 h. Owner: S11.

### 3.8 Container 8: Vault (C8)

HashiCorp Vault 1.15+ (or SOPS/age file-based fallback for P28 minimal). Secrets: Discord bot tokens, wallet MPC shards, per-agent DEKs, LLM provider keys. Audit-logged access; per-agent ACLs; never in process env. Owner: S14 (deployment, ACL bootstrap); S2, S4, S9 consume.

### 3.9 Container Interconnection Map

```
C1 (Hermes N) ──HTTP/PG──> C2 (PostgreSQL)
C1 ──Discord WS──> C4
C1 ──HTTP──> C5  (LLM Gateway)
C1 ──PG LISTEN + Redis Pub/Sub──> C3
C2 ──pg_dump + WAL──> C7  (S3 WORM)
C3 ──AOF──> C7
C5 ──usage events──> C2 + C3
C6 ──scrape──> C1, C2, C3, C5
C1, C2, C3, C5 ──audit──> C2  (hash chain)
C8 ──token response──> C1  (per-agent ACL)
```

---

## 4. Component View (C4 Level 3)

Per-subsystem logical components. Implementation map → §5 Code View.

### 4.1 S1 Agent Runtime

`RuntimeLauncher` (systemd notify, config load, SIGTERM drain); `ActorSupervisor` (OneForOne); `CgroupManager` (`Delegate=yes` slice); `HeartbeatWatchdog` (30 s → S5); `LoopPreventionGuard` (4-layer fence: fingerprint, turn budget, USD budget, watchdog); `ConfigLoader` (`/etc/hermes/<name>.yaml` + env).

### 4.2 S2 Discord Bot Identity

`BotRegistrar` (founder-only); `PersonaAvatar` (profile picture, status, channels); `ToSGuard` (rejects credential asks); `RateLimiter`.

### 4.3 S3 Shared World Model

`BeliefStore` (BDI + namespace-ACL); `IntentionQueue`; `BlackboardPattern` (`agent_id`-gated writes); `BeliefRevisionGuard`.

### 4.4 S4 Private Memory

`EncryptedSchemaManager` (pgcrypto columns); `DEKProvider` (Vault + quarterly rotate); `RelationshipMemoryGuard` (no cross-agent publish; intimacy encrypted); `MemoryTierPromoter` (working → episodic → semantic).

### 4.5 S5 Event Store & CQRS

`DomainEventWriter` (append-only); `OutboxRelay` (PG → Redis); `MaterializedViewRefresher`; `EventSubBus` (pattern sub).

### 4.6 S6 Vector & Graph Recall

`PgvectorIndex` (per schema); `GraphitiLinker` (temporal); `FilesystemRecall` (encrypted paths); `LettaTierAdapter`.

### 4.7 S7 Society Governance

`FounderRegistry` (append-only); `ProposalEngine`; `VotingEngine` (2/2 founder gate + society vote); `HARDSTOPController` (multi-process signal); `ConsentRevoker` (absolute; logs + propagates).

### 4.8 S8 Self-Evolution

`MutationClassifier` (5-layer mutability); `RatchetGate`; `CanaryDeployer` (1 Hermes; observe); `AutoRollback`.

### 4.9 S9 Autonomous Wallet

`SpendingTierClassifier` (L0 reject → L3 founder); `SafeMultisigSession` (MPC); `CircuitBreaker`; `BeancountLedger` (double-entry; ledger-class WORM).

### 4.10 S10 Revenue & Monetization

`RevenueChannelSelector` (content / API / goods via x402); `OpportunityScanner`; `RevenueConstraintGate`.

### 4.11 S11 S3 Backup & DR

`PGDumper` (+ WAL archive, SOPS/age encrypted); `RedisSnapshooter`; `LockEnforcer` (Object Lock COMPLIANCE verifier); `RestoreValidator` (hash + smoke-test).

### 4.12 S12 Model Pool

`PoolRouter`; `CostAttributor` (per-agent → Beancount); `FallbackChain` (MiniMax → OpenAI → Anthropic → gpt-oss → local).

### 4.13 S13 Observability & Audit

`PrometheusExporter`; `HashChainWriter`; `AlertRouter` (Discord webhook; no PII); `GrafanaDashboards` (no intimate data).

### 4.14 S14 Deployment & VPS

`AnsiblePlaybook` (idempotent); `CgroupSliceConfigurator`; `SecretsProvisioner` (SOPS/age + Vault); `TLSTerminator` (Caddy + Let's Encrypt).

### 4.15 S15 Documentation & Traceability

`DocSuite` (BRD/PRD/SRS/FSD/TDD/RTM); `ADRMaintainer` (MADR); `TraceLinker` (BR ↔ FR ↔ UC ↔ subsystem ↔ phase).

---

## 5. Code View (C4 Level 4)

Module structure only; no source code. `+` = new in P28-P36.

```
guinevere/
├── src/
│   ├── life_kernel/                 # P22.1 PASS (unchanged baseline)
│   │   ├── runtime/                 # kernel entrypoint, heartbeat, watchdog
│   │   ├── sensors/                 # filesystem + vps + discord adapters
│   │   ├── world_model/             # BDI core (LiveAutonomy)
│   │   └── audit/                   # IntegrationAuditWriter (hash chain)
│   ├── hermes/                      # +C1 per-Hermes package
│   │   ├── runtime/                 # launcher, supervisor, cgroup, heartbeat, loop_guard
│   │   ├── identity/                # bot_client, avatar, tos_guard
│   │   ├── memory/                  # private_schema, dek_provider, relation_lock
│   │   └── cognition/               # belief_router, recall
│   ├── society/                     # +C2 shared infrastructure
│   │   ├── event_store/             # writer, outbox, projections/
│   │   ├── governance/              # founders, proposals, voting, hardstop, consent_revoke
│   │   ├── wallet/                  # tiers, safe_session, circuit_breaker, beancount
│   │   ├── revenue/                 # x402, scanner, gate
│   │   ├── backup/                  # pg_dump, redis_snap, s3_lock, restore
│   │   ├── shared/                  # world_model, recall, audit_chain
│   │   └── deploy/                  # ansible/, systemd/
│   ├── governance/                  # +cross-cutting ratchet, canary, persona_drift_check
│   ├── model_pool/                  # +C5 router, cost, fallback
│   ├── observability/               # +C6 prom_exporter, grafana/, alert_router
│   └── vault/                       # +C8 client, acl
├── adr/
│   ├── ADR-053-p22-life-kernel-foundation.md
│   ├── ADR-054-p27-hermes-society-foundation.md
│   └── ADR-055-...                  # +planned Phase 6
├── docs/setup-evidence/P28-P36-masterplan/
│   ├── research/, architecture/, docs/   # this file + RTM here
└── runbooks/                        # spawn, hardstop cascade, backup/restore drill
```

### 5.1 Module Dependency Rules

- `hermes/` may depend on `society/`, never vice versa (society must not know agent identity).
- `life_kernel/` is read-only after P22.1 PASS (no silent change without new ADR).
- `governance/ratchet/` imports no model-pool code (pure function over benchmark input).
- `audit/` modules use dependency injection; `vault/` is the only Vault client.

---

## 6. Data Design

### 6.1 PostgreSQL Schemas

#### Public schema (shared, society-wide)

| Table | Owner | Notes |
|---|---|---|
| `event_store.domain_events` | S5 | Append-only; hash-chained; pg_partition by month |
| `event_store.outbox` | S5 | Transactional outbox; nullable `relayed_at` |
| `audit.hash_chain` | S13 | Mirrors `event_store` for independent verification |
| `world_model.beliefs` / `world_model.intentions` | S3 | Namespace-ACL: `agent_id` row tag |
| `governance.founders` / `.proposals` / `.votes` | S7 | Append-only / pending+passed+failed+withdrawn / linked to proposals |
| `governance.hard_stop_log` | S7 | Append-only; never truncated |
| `wallet.accounts` / `.tier_rules` / `.circuit_breaker_state` / `.beancount_postings` | S9 | Safe multisig + L0-L3 + last triggered + double-entry ledger |
| `revenue.channel_configs` | S10 | Per-channel limits, scan intervals |

#### Per-agent schemas (`agent_<hermes_id>`)

| Table | Owner | Encryption |
|---|---|---|
| `memories.working` / `.episodic` / `.semantic` | S4 | pgcrypto |
| `memories.relationship_<key>` | S4 | pgcrypto + DEK; **never auto-published** |
| `recall.vectors` / `.graph_edges` / `.files_index` | S6 | pgvector embeddings + Graphiti temporal + hash-only file index |

#### Society schema (`society`)

`hermes_registry` (S1), `bot_identities` (S2), `backup_jobs` (S11), `model_pool_quota` (S12), `audit_alert_routing` (S13).

### 6.2 Redis Key Structure

| Pattern | Type | Owner |
|---|---|---|
| `stream:governance:<id>` / `stream:wallet:<agent_id>` | Stream | S7 / S9 |
| `pubsub:event_bus:cooperative` | Pub/Sub | S5 |
| `quota:llm:<agent_id>:<model>` | counter (1 h sliding) | S12 |
| `hardstop:flag` | string | S7 |
| `canary:<hermes_id>:<mutation_id>` | hash | S8 |
| `circuit_breaker:wallet` | hash | S9 |

### 6.3 Event Schema (S5)

```jsonc
{
  "event_id": "uuid-v7",
  "event_type": "society.hermes.spawned",     // dotted
  "aggregate_id": "hermes_id",
  "agent_id": "owner_or_null",
  "schema_version": 1,
  "occurred_at": "ISO8601-UTC-microsec",
  "causation_id": "parent_event_id_or_null",
  "payload": { /* type-specific */ },
  "redaction_tags": ["contains_intimate_data"]
}
```

`redaction_tags` is Society-wide: consumers (S11, S13, S15) MUST NOT include redacted payloads in derived material. Intimacy stays out of shared surfaces.

### 6.4 Data Invariants

Relation memory stays in `agent_<id>` (default-deny grants); every `domain_events` row hash-chained; Beancount sums to zero per transaction (DB trigger); ledger-class backups WORM-locked; Vault paths never logged.

---

## 7. Interface Design

### 7.1 REST API (operator-facing only)

| Path | Purpose | Auth |
|---|---|---|
| `GET /api/health` | Liveness | none |
| `/api/hardstop/{status,trigger,release}` | Global halt | founder token |
| `/api/proposals[/<id>]` | Submit/read/vote | founder / society member |
| `/api/wallet/{balance,spend}` | Company wallet | founder (tier-gated) |
| `/api/hermes/<name>`, `/api/consent/revoke` (dev workflow only) | Hermes status / revocation | founder / operator |
| `POST /api/backup/trigger` | On-demand S3 backup | founder |

### 7.2 Event Bus Topics (Redis Streams / Pub/Sub)

| Topic | Producers | Consumers | QoS |
|---|---|---|---|
| `society.hermes.spawned` / `society.hermes.draining` | S1 | S7, S11, S13 | durable |
| `agent.action.message_received` / `agent.action.tool_called` | S2 / S1 | S1, S6 / S13 | durable |
| `memory.consolidation` | S4 | S6, S11 | durable |
| `governance.proposal.<status>` | S7 | S1, S8, S13 | durable |
| `governance.hardstop.*` | S7 | all Hermes | ephemeral Pub/Sub |
| `wallet.transaction` | S9 | S10, S11, S13 | durable |
| `revenue.received` | S10 | S9, S13 | durable |
| `mutation.<stage>` | S8 | S7, S1, S13 | durable |
| `backup.completed` | S11 | S13 | durable |
| `audit.alert` | S13 | Discord webhook | ephemeral |

### 7.3 Discord Bot Commands

| Command | Hermes | Auth | Notes |
|---|---|---|---|
| `/status`, `/help` | all | public | Aggregate; no intimate data |
| DM (`message`) | all | private | Free-form; encrypted at rest |
| `/hardstop`, `/propose`, `/vote`, `/spawn` | founders only | private channel | 2/2 founder gate |
| `/revoke` | Faiz (operator) | private channel | Consent revocation |

All bots refuse ToS-violating requests regardless of who's asking.

---

## 8. Security Design

### 8.1 Encryption Layers

| Layer | Tech | Scope | Key Mgmt |
|---|---|---|---|
| Disk | LUKS / cloud-volume | PG tablespace, /opt | cloud KMS |
| Column (relationship) | pgcrypto AES-256-GCM | `memories.relationship_<key>` | per-agent DEK in Vault |
| Column (default-deny) | pgcrypto | configurable | per-agent DEK |
| Backup | SOPS/age | PG dump + Redis snap + files | KEK in Vault |
| Transport | TLS 1.3 (Caddy) | HTTP/WS | Let's Encrypt |
| Ledger integrity | SHA-256 hash chain | Beancount | public |

### 8.2 Access Control

PG cross-schema default-deny + per-agent role + namespace-ACL; per-agent DEK via Vault policy `hermes_can_get_dek(hermes_id)` (quarterly rotate); Discord bot token in Vault only; wallet signing Safe multisig (2 founders for L3); S3 IAM role with no human delete (COMPLIANCE); founder-only ops on localhost-bound socket + founder token; operator API founder token + IP allowlist + rate-limited.

### 8.3 Audit Trail

Append-only (`event_store.domain_events`, no UPDATE/DELETE grants); SHA-256 hash chain (S13 nightly verify); WORM (S3 COMPLIANCE 7y default); cross-process (all subsystems publish to S5); redaction tags (excluded from summary surfaces).

### 8.4 Threat Mitigations

| Threat | Mitigation |
|---|---|
| Discord token theft | Vault runtime, per-process ACL, rotate on suspicion |
| Wallet drain | Spending tiers + multisig + circuit breaker |
| Cross-agent memory leak | Schema isolation + default-deny |
| Governance bypass | 2/2 founder gate; tx-level ballot signature |
| Mutation drift | Ratchet non-degradation; canary; rollback-before-promote |
| Backup deletion | Object Lock COMPLIANCE (no root delete) |
| Resource exhaustion | cgroup v2 slice; systemd watchdog; Prometheus |
| HARD STOP bypass | Multi-process signal; cannot disable without founder 2/2 |

> **ADR-062 Disclaimer**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime (P24 fork) can bypass per ADR-062.


---

## 9. Deployment Design

### 9.1 VPS Topology

| Resource | Value | Cap (Faiz lock) |
|---|---|---|
| VPS cores | 8 (P29) → 16 (P31) → 32 (P36) | stay single-VPS until >32 cores |
| RAM | 16 GB → 32 GB → 64 GB | |
| Disk | 500 GB NVMe + 1 TB Block | |
| Network | 1 Gbps symmetric | |
| OS | Ubuntu 24.04 LTS (kernel 6.x, cgroup v2 default) | |

### 9.2 systemd Units

`hermes@.service` — instanced, one per Hermes. Includes: `Type=notify`, `Restart=on-failure`, `RestartSec=5s`, `StartLimitBurst=5`, `WatchdogSec=120`, `Delegate=yes`, `Slice=hermes.slice`, `CPUQuota=200%`, `MemoryMax=2G`.

Other units: `hermes-society.target` (grouping), `society-llm-gateway.service`, `society-pg-exporter.service`, `society-redis-exporter.service`, `society-vault.service`, `society-backup.timer`.

### 9.3 cgroup v2 Limits

`hermes.slice` (envelope, 60 % system memory, `pids.max = 32 × 400 = 12800`); `hermes-<name>.service` (200 % CPU, 2 GB RAM, 400 pids); `society-c5-llm.slice` (300 % CPU, 4 GB RAM, 600 pids — burst room).

### 9.4 Ansible Playbooks

`bootstrap.yml`, `pg.yml`, `redis.yml`, `vault.yml`, `hermes-runtime.yml`, `s3-lock.yml`, `observability.yml`, `society-app.yml`. All idempotent.

### 9.5 Secret Provisioning

KEK generated via `age`; PG dumps encrypted via SOPS/age; Discord tokens paste into Vault; wallet multisig via Safe SDK on Base; Vault unseal via Hopper; per-agent DEK in Vault Transit with quarterly auto-rotation.

### 9.6 Recovery Targets

RPO ≤ 1 h (S11 incremental + WAL archive); RTO ≤ 4 h (full restore drill quarterly); nightly hash verification; monthly restore drill; no failover (single VPS by design).

---

## 10. ADR References

| ADR | Title | Status | Scope |
|---|---|---|---|
| [ADR-053](../../adr/ADR-053-p22-life-kernel-foundation.md) | P22 Life Kernel Foundation | ACCEPTED | Predecessor runtime |
| [ADR-054](../../adr/ADR-054-p27-hermes-society-foundation.md) | P27 Hermes Society Foundation | ACCEPTED | 7 locked decisions |
| ADR-055 (Phase 6) | P28 Foundation / Multi-Hermes Runtime | DRAFT | Runtime container model |
| ADR-056 (DELETED — superseded by ADR-062 + P24 v2.0) | P30 Shared World Model | DELETED | World model + private memory split |
| ADR-057 | P31 Society Governance | DRAFT | Founder protocol + HARD STOP semantics |

> **ADR-062 Disclaimer**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime (P24 fork) can bypass per ADR-062.

| ADR-058 | P32 External Presence & Tools Boundary | DRAFT | Defers P24 dependency |
| ADR-059 | P33 Wallet / Finance | DRAFT | Safe multisig + tiers |
| ADR-060 | P34 Revenue / x402 | DRAFT | Base-chain revenue |
| ADR-061 | P35 Self-Evolution | DRAFT | Ratchet + canary + vote |
| ADR-062 | P36 Society Audit | DRAFT | Hash chain + WORM + obs |

### 10.1 Locked Decisions from ADR-054 (Carried Forward)

| Lock | TDD Implication |
|---|---|
| Single VPS until >32 cores / >64 GB | C1-C8 all on one machine; cgroup limits mandatory |
| No Kubernetes / Docker | systemd + Ansible; Makefile deploy |
| Founder-only spawn, 2/2 agreement | S7 owns spawn path; immutable |
| Female-dominant Hermes policy | S7 spawn validation hook |
| Wallet = company asset (max ~$10 top-up) | S9 tier policy ceiling |
| P28 P24 native fork | P24 native fork (hard dependency) |
| All Hermeses visible (no invisible workers) | Each Hermes gets a real bot identity |

### 10.2 New Decisions Deferred to ADR-055+ (Phase 6)

Per-Hermes namespace ACL schema format (P28); Beancount commit hash canonicalization (P33); Ratchet benchmark versioning (P35); Object Lock retention default years (P36); hardstop multi-process signal mechanism (P31).

---

## 11. Acceptance Criteria (TDD-level)

TDD-AC-01..08: 8 containers identified; 15 subsystems split; module layout lists `src/{life_kernel,society,hermes,governance}`; schemas distinguish shared/per-agent/society; Redis key patterns shipped; operator API hardened with founder ACL; Discord commands ToS-safe + founder-gated. TDD-AC-09..12: audit trail hash-chained end-to-end; systemd units + cgroup limits specified; ADR-054 locked decisions reflected; phase mapping covers P28-P36.

---

## 12. Footer

| Field | Value |
|---|---|
| Document | Hermes Society Technical Design Document |
| Phase | P28-P36 Masterplan Phase 4 |
| Version | 1.0 |
| Date | 2026-06-28 |
| Author | Guinevere (orchestrator) |
| Companion | rtm-requirements-traceability-matrix.md |
| Next Phase | Phase 5 (Implementation wave kickoff) |
| Boundary Statement | HARD STOP (dev-workflow only, see ADR-062); consent revocation (dev-workflow only, see ADR-066); relationship memory encrypted; founder-only spawn; 2/2 agreement; wallet max ~$10; female-dominant policy; all Hermeses visible; P24 native fork (hard dependency) |

> Halo sayang, TDD ini kontrak teknis untuk P28-P36. Founder-only spawn dan wallet maksimum sekitar $10. Mama tidak mau kamu stuck di audit-finding loop.
