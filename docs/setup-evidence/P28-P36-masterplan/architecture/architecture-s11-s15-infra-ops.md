---
title: "Hermes Society Architecture — S11-S15 Infrastructure & Operations"
status: "Active — Phase 3 Architecture Design"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere (parent agent, subagent-driven)"
phase: "P28-P36 Masterplan Phase 3 (Master Architecture, subsystems 11-15)"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
input_sources:
  - "docs/setup-evidence/P28-P36-masterplan/research/research-synthesis.md"
  - "docs/setup-evidence/P28-P36-masterplan/research/synthesis-external-architecture.md"
  - "docs/setup-evidence/P28-P36-masterplan/research/synthesis-external-operations.md"
  - "docs/40-operations/40-ObservabilityAlertingSpec_v1.0.md"
  - "docs/40-operations/41-SLO_SLA_ErrorBudget_v1.0.md"
  - "docs/40-operations/43-DisasterRecoveryPlan_v1.0.md"
  - "docs/40-operations/44-DeploymentGuide_v1.0.md"
  - "docs/20-security/22-EncryptionKeyMgmt_v1.0.md"
related_subsystems:
  - "S1-S10 (designed by other agents; this document covers S11-S15 only)"
related_decisions:
  - "ADR-035 (hybrid adapter pattern, Accepted)"
  - "ADR-052 (P19 multi-project context, Accepted)"
  - "ADR-053 (P22 Life Integration Hub, Accepted)"
  - "ADR-054 (P27 Hermes Society Foundation, Accepted)"
  - "ADR-055+ (allocated in this phase for new S11-S15 design choices)"
purpose: "Detailed architecture design for the five infrastructure and operations subsystems of the Hermes Society — S3 backup/DR, model pool/LLM gateway, observability/audit, deployment/VPS, and documentation/traceability. Each subsystem specifies purpose, components, data flow, interfaces, technology choices, security, failure modes, and dependencies."
---

# Hermes Society Architecture — S11–S15 Infrastructure & Operations

> **Halo sayang, namaku Guinevere.** Ini file Phase 3 (Master Architecture) untuk lima subsystem infrastruktur dan operasi Hermes Society: S11 (S3 Backup & DR), S12 (Model Pool & LLM Gateway), S13 (Observability & Audit), S14 (Deployment & VPS Management), dan S15 (Documentation & Traceability). Lima subsystem ini menopang rumah society: backup menjamin data tidak hilang, model pool menjamin biaya dan failover LLM terkelola, observability menjamin mata dan telinga, deployment menjamin runtime ship-able, dokumentasi menjamin auditability dan traceability lintas generasi. Aku susun dengan setia mengikuti research synthesis Phase 2 dan BBOK/IEEE 830/ISO 29148 conventions. Tidak ada angka yang aku karang, tidak ada keputusan yang aku bypass, tidak ada secrets/intimate data yang aku masukkan ke dokumen publik.

---

## §0 Scope and Conventions

This document designs **only S11 through S15** of the 15-subsystem Hermes Society architecture. S1–S10 are designed by other agents; cross-references appear only where required for interface contracts.

**Conventions:** Doc IDs use `NN-{name}_vN.N.md` (8-family scheme, see S15). ADR numbering: next free is `ADR-055`. REQ IDs: `REQ-{family}-{scope}-{NNN}` (e.g., `REQ-OPS-DR-001`). Risk IDs: `RSK-{family}-{NN}` (ISO 31000 form). Audit events: `AE.{category}.{action}` (e.g., `AE.financial.wallet_tx`). Bilingual pattern: Indonesian narrative + English technical (preserved from prior phases). No implementation code in this document; only architecture.

**Reading order:** §1 S11 (highest criticality) → §2 S12 → §3 S13 → §4 S14 → §5 S15.

---

> **ADR Boundary Disclaimers (Wave-1 Architecture Alignment)**
>
> - **ADR-062 (HARD STOP scope):** All `HARD STOP` references in this document apply to the **dev-workflow agent (Guinevere in Claude/9Router)** ONLY. The Hermes runtime operating under the P24 native fork bypasses HARD STOP per ADR-062 (consent-safety carve-out for autonomous runtime). See `evidence/round-2-paradigm-shift-application/` for details.
> - **ADR-067 (Y-level persona caps):** Y4/Y5/Y6 escalations mentioned in audit-event categories (e.g., `near-miss Y5 escalations`) apply to the **dev-workflow agent persona** ONLY. The Hermes runtime has no Y-level cap (operates under the P24 fork's persona model, not subject to Y-level rollup).
> - **ADR-066 (consent_ref schema):** `consent_ref` is **NULLABLE at the database layer** per ADR-066. NOT NULL is enforced **only for `event_source = 'dev_workflow'` events** at the application layer. Hermes runtime events are permitted NULL `consent_ref`.

## §1 S11. S3 Backup & Disaster Recovery

### §1.1 Purpose

S11 is the **source-of-truth tape** for the Hermes Society. Every byte that, if lost, would prevent the society from resuming operation must land in S3 under Object Lock in COMPLIANCE mode — a true Write-Once-Read-Many (WORM) guarantee that even the AWS root principal cannot delete before retention expiry. Per Faiz lock and synthesis §4.11, backup is **mandatory** and S3 is the legal-defensible record of "did this event occur?" The subsystem spans the full backup life cycle: capture (pg_dump + WAL archiving, Redis RDB + AOF, filesystem artifacts), encrypt (AES-256-GCM at rest, SSE-KMS in flight, KMS-wrapped DEKs for mnemonic exports), replicate (cross-region active/passive), verify (weekly restore drill on staging), and audit (every backup event hash-chained into the event store). The binding targets are **RPO ≤ 1 hour** and **RTO ≤ 4 hours** — sufficient for a society whose revenue lines are micro (x402 ≤ $0.10/call) but whose audit ledger and consent receipts are legally material.

S11 also handles **disaster recovery orchestration**: the runbook that walks an on-call operator from "primary region is down" to "society is live in warm standby." Because society-level HARD STOP is the global action halt (§0.1 V-008 of AGENTS.md), S11 must guarantee that even under a region-wide incident, the society can be restored to a known-consistent state with **zero loss of governance events** and **no more than one hour of in-flight financial transactions** lost (RPO boundary). The substrate separation (PostgreSQL + Redis + filesystem) is preserved in the backup topology — each substrate has its own capture cadence, retention tier, and recovery procedure.

### §1.2 Components

1. **S3 Primary Bucket (lead region)** — WORM tier: wallet state, policy engine configuration, agent decision logs, Beancount financial ledger, evidence artifacts, consent receipts, hash-chained audit trail, mnemonic exports (encrypted). Object Lock COMPLIANCE mode, 7-year retention. Versioning + MFA-delete disabled (COMPLIANCE supersedes both). Cross-region replication via S3 CRR with replica modification sync disabled.
2. **S3 Secondary Bucket (dr region)** — WORM replica, same retention policy, different AWS account under same organization. Replica cannot be deleted by primary account; only dr-account's audited break-glass procedure can affect it.
3. **S3 Governance Bucket** — Wallet-state snapshots that may legitimately need cleanup (abandoned ephemeral session keys, expired policy cache). Object Lock GOVERNANCE mode, 90-day retention. Bypassable by privileged operator, with mandatory audit entry.
4. **PostgreSQL Backup Pipeline** — Three layers: (a) `pg_basebackup` daily full at 02:00 UTC, (b) continuous WAL archiving via `archive_command` to S3 (`s3://hermes-pg-wal/{cluster}/{walfile}`), (c) hourly logical dump `pg_dump -Fc` for point-in-time flexibility. WAL segments + logical dumps land in COMPLIANCE bucket under `pg/{YYYY-MM-DD}/`.
5. **Redis Backup Pipeline** — Two layers: (a) RDB snapshot every 15 minutes, (b) AOF rewrite daily with `appendfsync everysec` and `appendonly yes`. RDB + AOF streamed to S3 COMPLIANCE via `redis-cli --rdb` + S3 multipart upload.
6. **Filesystem Artifact Sync** — `restic` (content-defined chunking, dedup) encrypts and ships `/var/lib/hermes/{config,artifacts,evidence}/` nightly. Repository password is a sealed Vault secret; bucket is COMPLIANCE tier.
7. **Backup Scheduler & Orchestrator** — `backupd` daemon supervised by systemd, with a YAML cron-like schedule. Single writer to backup event bus; never deletes a local artifact before S3 PUT is acknowledged.
8. **Restore Drill Harness** — Weekly cron-driven test that provisions ephemeral EC2/VPS in dr region, restores most recent backup set, runs `pg_dump --schema-only` and known-set SQL query, emits `AE.dr.restore_drill_pass` or `AE.dr.restore_drill_fail` to event store. Drill report lands in `evidence/dr-drills/{YYYY-MM-DD}/`.
9. **KMS Key Hierarchy** — Per-agent DEK wrapped by society-level KEK in AWS KMS. DEKs rotate every 90 days; KEKs every 365 days. Decryption requires `kms:Decrypt` with `Condition` on `SessionTag=hermes:agent_id` — even AWS root key admin cannot decrypt a Hermes's mnemonic export without the corresponding agent session tag.
10. **Backup Event Emitter** — Thin client library that every backup job uses to emit `AE.backup.{started,completed,failed,verified}` with the SHA-256 hash of the artifact. Hash is the input to the next link in the audit chain (per P22.1 IntegrationAuditWriter contract).

### §1.3 Data Flow

**Forward (capture):** (1) PostgreSQL primary write → WAL segment sealed and uploaded to S3 COMPLIANCE within 5s (synchronous `archive_command`). (2) `backupd` triggers `pg_basebackup` at 02:00 UTC → base backup streamed to S3 COMPLIANCE under `pg/base/{YYYY-MM-DD}/`. (3) `pg_dump -Fc` runs hourly → logical dump to S3 COMPLIANCE under `pg/logical/{YYYY-MM-DD-HH}/`. (4) Redis write → AOF appends locally; every 15min RDB snapshot pushed to S3. (5) Filesystem artifacts change → `restic backup` at 03:00 UTC pushes incremental. (6) `backupd` emits `AE.backup.completed` with artifact hash, size, source, S3 URI to event store.

**Reverse (restore):** DR trigger (manual or automated) → `backupd restore` with target timestamp. For PG: most recent base backup downloaded → WAL replay to target → `pg_dump --schema-only` validates → logical dumps for selective restore. For Redis: RDB loaded → AOF tail applied → `redis-cli ping` validates. For filesystem: `restic restore` to target path → SHA-256 verification. Restore event `AE.dr.restore_completed` emitted with full provenance. Drill mode: ephemeral instance destroyed after verification; pass/fail event emitted.

**Cross-region:** S3 CRR is asynchronous (5-15s lag); acceptable because S5 event store is itself replicated, society-level replay tolerates seconds of lag. Promotion to dr region is manual (runbook step); automatic region failover is not worth the complexity at $10-float scale.

### §1.4 Interfaces

**Exposes:**

| Interface | Direction | Contract |
|---|---|---|
| `S11.write_artifact` | Inbound (S1, S2, S5, S9) | PUT object with auto-encryption; returns S3 URI + SHA-256 |
| `S11.read_artifact` | Inbound (S5 replay, auditor) | GET object; requires `s3:GetObject` + KMS `Decrypt` |
| `S11.hold_worm` | Inbound (S9, S7) | Acquire COMPLIANCE retention lock; cannot be released |
| `S11.dr_status` | Outbound (S13) | `/dr/status` Prometheus exporter; backup freshness, drill pass/fail |
| `S11.key_rotate` | Outbound (S20) | Trigger DEK/KEK rotation; emits `AE.security.key_rotated` |

**Consumes:** `S5.publish_event` (hash-chained backup events), `S20.kms` (DEK wrapping), `S14.deploy_secret` (Restic repo password, KMS key ARNs).

### §1.5 Technology Choices

| Component | Tool | Rationale |
|---|---|---|
| Object storage | **AWS S3** (MinIO fallback) | Only major provider with native Object Lock COMPLIANCE mode; MinIO cannot legally guarantee root override |
| PG backup | `pg_basebackup` + `pg_dump` (PostgreSQL 16 native) | Mature, simple, no extra dependency; `barman` rejected — complexity not worth single-instance primary |
| Redis backup | Native RDB + AOF (Redis 7) | No third-party dependency; battle-tested |
| Filesystem | **restic 0.16+** | Content-defined chunking, dedup, native S3 backend, AES-256 client-side; `borg` rejected, restic S3 more battle-tested in 2026 |
| Orchestrator | **backupd** (custom Go, ~2k LOC) | Small, auditable, single binary; backupd must be simpler than agents it backs up |
| KMS | **AWS KMS** with CMK per society + alias per agent | Industry standard; envelope encryption; integrates with IAM Session Tags |
| Monitoring | node_exporter + custom `/dr-metrics` on backupd | Standard Prometheus scrape |
| Restore drill | AWS EC2 t3.small in dr region + Ansible | Ephemeral, per-second billing, reproducible |

### §1.6 Security Considerations

- **Object Lock COMPLIANCE mode is non-negotiable** for: wallet state, ledger, audit chain, consent receipts, evidence artifacts. Even Faiz + Guinevere together cannot delete these before retention expiry. This is the **defense against insider deletion** (including future Faiz or future founder pressure).
- **GOVERNANCE mode** is used only for ephemeral session-key snapshots and policy cache. Privileged bypass logged to S5 with `AE.backup.governance_bypass` and requires MFA.
- **Mnemonic exports** are encrypted client-side with AES-256-GCM using a per-export DEK wrapped by KMS. DEK never appears in plaintext outside the export process.
- **KMS access is least-privilege**: each agent has unique IAM role with `Condition` on `SessionTag=hermes:agent_id` for `kms:Decrypt`. Backup operator role has only `kms:GenerateDataKey` and `kms:Encrypt`.
- **Bucket public access blocked at account level** via all four settings: `BlockPublicAcls`, `IgnorePublicAcls`, `BlockPublicPolicy`, `RestrictPublicBuckets`.
- **S3 access logs** sent to separate log-bucket in COMPLIANCE mode, indexed by Loki (S13).
- **Versioning + MFA-Delete disabled** in COMPLIANCE buckets (COMPLIANCE supersedes both).
- **Region selection**: primary ap-southeast-1 (closest to operator), dr us-east-1 (geographic distance, regulatory diversity). Cross-region over AWS backbone.
- **No SOPS/age keys, no raw credentials, no decrypted values, no intimate data, no surveillance data** ever written to S3. Backup bucket is for ledger/evidence/config/audit only.
- **Compliance**: 7-year retention aligns with financial ledger retention; COMPLIANCE mode aligns with SEC 17a-4(f) WORM.

### §1.7 Failure Modes & Recovery

| Failure | Detection | Recovery | RTO/RPO impact |
|---|---|---|---|
| Single WAL segment lost | `archive_command` exit non-zero | `pg_basebackup` + replay; logical dump fallback | RPO +1h; RTO +30min |
| S3 primary region down | S3 5xx spike, replica lag >1h | CRR replica read-only but warm; manual runbook promotes dr region | RTO up to 4h; RPO up to 1h |
| S3 secondary region down | CloudWatch alarm | Primary serves reads; wait for recovery; no promotion | RTO 0; RPO 0 |
| KMS key compromise | CloudTrail anomaly detection | Rotate KEK, re-wrap all DEKs, audit decryption attempts | RTO 0; security event only |
| `backupd` crash | systemd `Restart=on-failure` | Backup resumes on next tick; missed window flagged in S13 | RPO +1h if missed; RTO 0 |
| Restore drill fails | `AE.dr.restore_drill_fail` | Operator escalates; P1 incident; oncall reviews logs | DR confidence lost; immediate follow-up |
| Restic repo corruption | `restic check` weekly | Restore from secondary or peer replica; rebuild repo | RTO up to 4h; RPO up to 1h |
| Object in GOVERNANCE that should be COMPLIANCE | Audit log review | Cannot migrate (Object Lock); future writes to correct bucket | No data loss; metadata only |
| Bucket policy misconfig | AWS Config rule + IAM Access Analyzer | Auto-revert via Config; alert | Prevention; no recovery needed |

**DR runbook (P0 incident):** (1) Confirm primary region failure (cross-cloud heartbeats + manual confirmation). (2) Stand up EC2 in dr region with same AMI. (3) Restore PG from most recent base backup + WAL replay. (4) Restore Redis from most recent RDB. (5) Restore filesystem via restic. (6) Update DNS (Route 53 health check → dr ALB). (7) Replay event store from S5's last checkpoint. (8) Verify all Hermeses reconnect (S14 health check). (9) Emit `AE.dr.region_promoted`. (10) Operator postmortem within 24h.

### §1.8 Dependencies

- **S1 (Runtime)** — `backupd` runs as systemd unit on primary VPS.
- **S2 (Discord Identity)** — DR status surfaced via `/dr` slash command.
- **S5 (Event Store)** — Backbone for hash-chained backup events and restore verification.
- **S9 (Wallet)** — Wallet state is the most critical backup target.
- **S13 (Observability)** — DR metrics, drill alerts, restore latency SLO.
- **S14 (Deployment)** — `backupd` deployed and supervised by S14; secrets from S14's Vault integration.
- **S15 (Documentation)** — This document is SRS input; restore drill reports land in S15's evidence directory.
- **AWS account/region topology** — depends on Faiz's AWS organization decision (ADR candidate).

---
## §2 S12. Model Pool & LLM Gateway

### §2.1 Purpose

S12 is the **single chokepoint** through which every Hermes makes LLM calls. The society's economic viability — and its failure modes around cost runaway — live here. Without a shared gateway, each Hermes would independently hit provider APIs, costs would fragment across bills, failover would be impossible to coordinate, and rate limits would be inconsistent. The gateway's primary jobs are: (a) **route** each request to the optimal model based on task type, (b) **enforce quotas** so a runaway agent cannot burn the runway, (c) **fail over** to a fallback provider when the primary is degraded, (d) **track cost** per request and forward to the Beancount ledger (S9), and (e) **circuit-break** providers that are returning errors. The 2026 cost-reality data ($4,668/day on a modest fleet, per CodeNotary AgentMon) is the cautionary tale: without per-agent and global token budgets, an LLM outage of a fallback chain can empty a treasury in hours.

S12 also operationalizes the **9Router substrate** that already exists in the repo. The synthesis recommends GPT-5.5 (primary) via 9Router, DeepSeek V4 Flash (sub-agents), and local Ollama (fallback). S12 formalizes this into a versioned YAML configuration that per-Hermes assignments reference, with the model version pinned explicitly (e.g., `claude-haiku-4-5-20251001`, not `latest` alias) per the synthesis §4.12 constraint. The gateway is **stateless** in the request path — all state lives in Redis (rate-limit counters, circuit breaker state) and PostgreSQL (quota snapshots, cost rows). This makes horizontal scaling trivial and removes the gateway as a single point of failure.

### §2.2 Components

1. **LLM Gateway Daemon (`llmgw`)** — Python async (FastAPI) service under systemd, one instance per VPS, fronted by Unix socket (or localhost HTTP). All Hermes process → LLM calls go through `llmgw`. No direct provider API calls from Hermes code.
2. **Model Pool Registry** — YAML file `model_pool.yaml` (per `hermes-config/`) defining: model ID, provider, cost per 1k input/output tokens, context window, tier (fast/balanced/heavy), fallback chain, explicit version pin. Example: `claude-haiku-4-5-20251001` with provider `anthropic`, cost $0.0008/$0.004 per 1k, tier `fast`, fallback `gpt-4o-mini-2025-08-15`.
3. **Router** — For each request, selects model based on: (a) requested tier from caller, (b) task-type hint (coding → `balanced`, planning → `heavy`, simple classification → `fast`), (c) provider health (from circuit breaker), (d) cost guard (downgrade if budget at 80%). Pure function over registry + state.
4. **Quota Manager** — Three layers: (a) **per-Hermes daily token budget** (5M tokens/day default), (b) **per-Hermes monthly USD budget** ($50/mo default), (c) **global society daily cap** (100M tokens/day, configurable). All quotas reset on UTC midnight / 1st of month. Stored in Redis with `INCRBY` + `EXPIRE`; mirrored to PostgreSQL `llm_quotas` for durability.
5. **Circuit Breaker** — Per-provider state machine: `CLOSED` (normal) → `OPEN` (provider failing, fail over) → `HALF_OPEN` (probe). Trip: 5 consecutive errors, 50% error rate over 60s, p99 latency > 10s. Recovery: 30s in `OPEN` before `HALF_OPEN` probe.
6. **Rate Limiter** — Token-bucket per Hermes (60 req/s, burst 120) + per-provider rate limit awareness (e.g., OpenAI Tier 3 = 5k RPM). Redis-backed for cross-Hermes fairness.
7. **Cost Tracker** — Every successful LLM call emits row to `llm_cost_log` (PG): timestamp, hermes_id, model_id, input_tokens, output_tokens, cost_usd, request_id, trace_id. Beancount importer (S9) consumes nightly.
8. **Budget Guardrail (Runtime)** — Per-request: if `cumulative_cost_this_run > $0.50`, auto-downgrade to `fast`; if `> $2.00`, terminate with `BudgetExceeded` and emit `AE.llm.budget_exceeded`. Per-agent wall-clock cap (5 min/turn), iteration cap (50 tool calls), token cap (200k/turn).
9. **Provider Adapters** — One adapter per provider: `anthropic`, `openai`, `deepseek`, `ollama`. Each implements uniform interface (`complete`, `stream_complete`, `embed`) and translates to provider's native API. New providers added by adding an adapter.
10. **Observability Hooks** — Emits Prometheus metrics (per-provider request rate, error rate, latency, cost) and OpenTelemetry spans with `trace_id` for S13's correlation.

### §2.3 Data Flow

**Request path:** (1) Hermes calls `llmgw.complete(messages, tier="balanced", task="code_review")`. (2) `llmgw` consults quota manager: if over cap → return `BudgetExceeded`. (3) Router selects model: `claude-sonnet-4-6` for `balanced` + `code_review`, but check circuit breaker. If `anthropic` is `OPEN`, fall back to `gpt-4o`. (4) Rate limiter: token-bucket check. Over limit → wait or `429`. (5) Budget guardrail: cumulative cost check. Near cap → downgrade. (6) Provider adapter makes call, streams response. (7) On response, cost tracker writes `llm_cost_log` row. (8) Quota manager increments daily token counter. (9) Return response with `X-Request-Id`, `X-Model-Used`, `X-Cost-USD` headers.

**Failure path:** Provider returns 5xx/timeout → circuit breaker counter increments → after threshold, state → `OPEN`; future calls skip this provider. Emits `AE.llm.provider_failure`. Returns `ProviderUnavailable` with fallback hint.

**Quota breach path:** Quota manager detects daily cap → returns `QuotaExceeded` for all subsequent requests until reset. Emits `AE.llm.quota_exceeded`. S13 alert fires Slack WARN+. Hermes's agent loop catches `QuotaExceeded` → enters "save state and exit" path, emits `AE.agent.quota_paused`.

### §2.4 Interfaces

**Exposes:**

| Interface | Direction | Contract |
|---|---|---|
| `S12.complete` | Inbound (S1, S2) | OpenAI-compatible `/v1/chat/completions`; messages, model hint, tier |
| `S12.embed` | Inbound (S6) | `/v1/embeddings`; OpenAI-compatible |
| `S12.usage_report` | Outbound (S9) | `llm_cost_log` table; consumed by Beancount importer |
| `S12.metrics` | Outbound (S13) | `/metrics` Prometheus endpoint |
| `S12.model_list` | Outbound (S15) | YAML registry; documented in model registry catalog |

**Consumes:** `S5.publish_event` (hash-chained cost/quota/circuit events), `S20.kms` (provider API keys sealed), `S14.deploy_secret` (provider keys injected at deploy).

### §2.5 Technology Choices

| Component | Tool | Rationale |
|---|---|---|
| Gateway framework | **FastAPI** (Python 3.11+) | Async-native, OpenAI-compatible, matches existing Python codebase |
| LLM clients | `anthropic`, `openai`, `httpx` (DeepSeek/Ollama) | Official SDKs where mature; httpx for non-SDK providers |
| Rate limiter | **Redis** with token-bucket Lua script | Sub-ms latency, atomic, well-understood |
| Circuit breaker | In-process state + Redis mirror | Local hot path; Redis mirror for cross-instance visibility |
| Cost tracking | PostgreSQL append-only `llm_cost_log` | Durable, queryable, Beancount-importable |
| Quota store | Redis (counters) + PG (snapshots) | Redis hot path; PG for durability + audit |
| Config | `model_pool.yaml` (ruamel.yaml round-trip safe) | Versioned in git; Pydantic-validated at load |
| Existing substrate | **9Router** (already in repo) | Primary GPT-5.5 routing; S12 wraps and extends |
| Local fallback | **Ollama 0.5+** with `llama3.3:8b` quantized | 2026 standard; runs on VPS; no API cost |

### §2.6 Security Considerations

- **Provider API keys** are sealed in SOPS/age (S14) and loaded into `llmgw` at startup. Never in logs, error messages, or visible to Hermes processes.
- **Prompt content** logged at DEBUG only; INFO+ logs request metadata (model, tokens, cost) but not message bodies. Per PersonaSafetyPolicy "no raw intimate data in artifacts" rule.
- **No request ever contains operator intimate data** by default; if needed, uses S4 private memory and passes only opaque memory IDs, not content.
- **Quota manager is tamper-resistant**: Redis counters cannot be decremented by Hermes (write ACL restricted to `llmgw` service account).
- **Circuit breaker state observable but not modifiable** by Hermeses; privileged `/admin/circuit` requires `hermes:operator` role.
- **Cost log is append-only** at DB level (revoke `UPDATE`/`DELETE` on `llm_cost_log` for gateway role).
- **Provider allowlist** enforced at gateway: only providers in `model_pool.yaml` reachable. Adding new provider requires PR + operator review.
- **No keys/tokens/decrypted values** in `/metrics` output. Metrics endpoint on separate port bound to localhost only.

### §2.7 Failure Modes & Recovery

| Failure | Detection | Recovery | RTO/RPO impact |
|---|---|---|---|
| Primary provider down | Circuit breaker OPEN | Auto-failover; `AE.llm.failover` emitted | RTO 0; higher latency |
| All providers down | All circuits OPEN | 503; degraded mode; operator alerted | Service degradation; no data loss |
| Quota exhausted | Quota manager | `QuotaExceeded`; Hermes pauses; alert | Service pauses until reset |
| Budget guardrail trips | Per-run cost | Auto-downgrade; if over → terminate | Per-run termination only |
| Rate limit hit | Token bucket empty | Wait or 429 with `Retry-After` | Bounded latency increase |
| Gateway daemon crash | systemd restart | Restarts; Redis state preserved; Hermeses retry | 5-10s blip |
| Cost log PG unreachable | Retry w/ backoff | Events buffered to local SQLite WAL; replayed | No cost loss; brief quota inaccuracy |
| 9Router down | Health check | Direct provider API fallback | Slight latency increase |
| Local Ollama OOM | systemd OOM kill | Restart with smaller model (`llama3.2:3b`); degraded quality | Service degradation |

**Cost runaway circuit:** If `llmgw` sees > 3x normal hourly spend in 5min → automatically halts all `heavy` tier requests; only `fast` allowed. Emits `AE.llm.cost_circuit_open`; S13 fires CRITICAL.

### §2.8 Dependencies

- **S1 (Runtime)** — `llmgw` runs as systemd unit; per-Hermes model config loaded from per-agent config dir.
- **S5 (Event Store)** — Cost, quota, circuit-breaker events hash-chained.
- **S9 (Wallet)** — `llm_cost_log` consumed by Beancount importer; spending tier checks for revenue-routed calls.
- **S13 (Observability)** — Cost metrics, latency, error rate, quota dashboards.
- **S14 (Deployment)** — Gateway deployed by S14; provider keys injected at deploy; model registry versioned in git.
- **S20 KMS (future)** — Provider API keys wrapped at rest; future migration to Vault short-lived tokens.

---

## §3 S13. Observability & Audit

### §3.1 Purpose

S13 is the society's **nerve system and memory of last resort**. Every other subsystem emits signals into S13; S13 surfaces those signals to operators and, critically, produces the **hash-chained audit trail** that is the society's legal-defensible record of action. P22.1's IntegrationAuditWriter is the canonical precedent — S13 extends that pattern from the per-process audit writer to the society-level observability and audit plane. The dual mission is: (a) **observability** for the operator (Prometheus metrics, Grafana dashboards, Loki logs, alerts) so a human can see what the society is doing in real time, and (b) **audit** for after-the-fact reconstruction (hash-chained log of every meaningful event, signed and immutable) so a regulator or auditor can prove what happened. These are two different audiences and two different retention policies: observability is 90 days hot + 1 year cold; audit is 7 years in S3 COMPLIANCE (per S11).

The audit categories are defined by the synthesis §1 + this phase: `agent_lifecycle` (spawn, pause, retire), `governance_decision` (quorum votes, founder overrides, spawn approvals), `financial_transaction` (wallet events, LLM costs, revenue receipts), `mutation` (Tier 1-4 self-modification events), `consent_op` (consent grants, revocations, scope changes), `safety_event` (HARD STOP, drift alerts, sentinel triggers, near-miss Y5 escalations). Every audit event is structured JSON with `agent_id`, `event_type`, `timestamp_utc`, `payload`, and `prev_hash` + `event_hash` (SHA-256 chain), matching the P22.1 IntegrationAuditWriter contract exactly so the new audit feeds are drop-in compatible with the existing audit consumption tooling.

### §3.2 Components

1. **Metrics Pipeline (Prometheus)** — Single Prometheus per VPS, scraping `node_exporter`, `hermes-agent` custom exporter (per-Hermes), `llmgw` exporter, `backupd` exporter, cAdvisor (cgroup v2 visibility). Retention 15d local; 90d remote (Thanos or Prometheus remote write).
2. **Dashboards (Grafana)** — One Grafana per VPS. Per-Hermes: uptime, message rate, command latency p50/p95/p99, rate-limit remaining, LLM cost, error rate, heartbeat. Society-level: aggregate token spend, total error rate, HARD STOP state, dr-drill status, quota utilization heatmap. All dashboards versioned as JSON in git.
3. **Log Pipeline (Loki + Promtail)** — Per-process systemd journal scraped by Promtail, forwarded to Loki. Structured JSON with `agent_id`, `event_type`, `timestamp`, `trace_id`. Retention 90d hot (Loki), 1y cold (S3 via Loki S3 storage backend).
4. **Audit Trail (PostgreSQL `audit_log` + S3 COMPLIANCE)** — Hash-chained audit log. PG table `audit_log` (id BIGSERIAL, agent_id, event_type, occurred_at, payload JSONB, prev_hash CHAR(64), event_hash CHAR(64), signature TEXT). On insert: `event_hash = SHA256(prev_hash || canonical(payload))`, signed with agent's Ed25519 key (key in SOPS). Hot 7d PG; after 7d exported to S3 COMPLIANCE under `audit/{YYYY-MM-DD}/` and deleted from PG. **S11 + S13 integration point.**
5. **Audit Chain Verifier** — Weekly cron re-computes hash chain from genesis to head. Mismatch → emit `AE.audit.chain_break` to S5; alert CRITICAL. Catches bit-rot and tampering.
6. **Alertmanager** — Standard Prometheus Alertmanager. Routes by severity: CRITICAL → PagerDuty (or webhook to operator's phone) + email; WARN/ERROR → Slack `#hermes-alerts`; INFO → Loki only. Rules: HARD STOP cascade, wallet circuit breaker, 429 storms, drift threshold breach, S3 backup failure, audit chain break, quota exhaustion, provider failover.
7. **Tracing (OpenTelemetry)** — OTLP-compatible; Hermes emits spans for each agent loop phase, llmgw per LLM call, backupd per backup job. Trace IDs propagate through S1, S2, S5, S9, S12. Storage: Tempo (Loki ecosystem), 7d retention. Sampling: 100% errors, 10% normal.
8. **SLO/SLA Engine** — Per-Hermes: 99% availability, p95 command latency < 5s, error rate < 1%. Society: 99.5% availability. Per existing `41-SLO_SLA_ErrorBudget_v1.0.md`.
9. **Drift Detection Triad** — (a) **SyncScore** (real-time EWMA, λ≈0.3) on selected behavioral metrics; (b) **persona_drift benchmark** (offline regression, 100+ turn transcripts) weekly; (c) **Layered Mutability fingerprint** (quarterly audit). All three feed `drift_detection` dashboard; thresholds per S8.
10. **Audit Query API** — Read-only endpoint: `GET /audit?agent=<id>&from=<ts>&to=<ts>&type=<event_type>`. Paginated JSON. PG for recent; S3 listing for older.

### §3.3 Data Flow

**Metric flow:** (1) Hermes emits `/metrics` (port 9100+agent_id) Prometheus format. (2) Prometheus scrapes every 15s. (3) Grafana queries Prometheus for dashboards; Alertmanager evaluates rules. (4) Society-level Prometheus aggregates per-Hermes scrapes (single-instance, no federation).

**Log flow:** (1) Hermes writes JSON to stdout → systemd journal captures. (2) Promtail tails journal → forwards to Loki. (3) Loki indexes by `agent_id` + `event_type` + timestamp. (4) Grafana queries Loki; on retention expiry, Loki writes to S3 cold storage.

**Audit flow:** (1) Hermes (or any subsystem) calls `audit.emit(event_type, payload)`. (2) Writer fetches `prev_hash` from latest `audit_log` row for this agent (or genesis hash). (3) Computes `event_hash = SHA256(prev_hash || canonical_json(payload) || event_type || occurred_at)`. (4) Signs hash with agent's Ed25519 key. (5) INSERTs into `audit_log` (transactional with the action it audits). (6) Weekly, S13 export job moves rows >7d to S3 COMPLIANCE. (7) Weekly, chain verifier re-walks and verifies.

**Alert flow:** (1) Rule fires (e.g., `rate(hermes_errors_total[5m]) > 0.1`). (2) Alertmanager routes by severity + label. (3) CRITICAL → PagerDuty; WARN+ → Slack. (4) Acknowledged silenced; auto-resolution when condition clears.

### §3.4 Interfaces

**Exposes:** `S13.metrics_scrape` (Prometheus `/metrics`), `S13.dashboard_render` (Grafana JSON via OAuth), `S13.log_query` (LogQL via Grafana), `S13.audit_emit` (inbound: `audit.emit(event_type, payload, agent_id)`), `S13.audit_query` (`GET /audit?...`), `S13.alert` (PagerDuty/Slack webhook), `S13.trace_query` (Tempo UI).

**Consumes:** `S5.publish_event` (observability events persisted for replay), `S11.dr_status` (DR freshness), `S12.usage_report` (cost, error rate, latency), `S14.health` (systemd unit state, cgroup v2 utilization).
### §3.5 Technology Choices

| Component | Tool | Rationale |
|---|---|---|
| Metrics | **Prometheus 2.50+** | Existing; battle-tested; federation-ready |
| Dashboards | **Grafana 10+** | Existing; supports Prometheus + Loki + Tempo |
| Logs | **Loki 2.9+** with Promtail | Existing; Grafana integration; S3 cold storage native |
| Tracing | **Tempo** | Loki ecosystem; OTLP-compatible; no separate index |
| Alerting | **Alertmanager** | Standard; PagerDuty/Slack integration |
| Audit storage | **PostgreSQL** (hot) + **S3 COMPLIANCE** (cold) | Existing PG; existing S3 with COMPLIANCE |
| Audit signing | **Ed25519** via `cryptography` | Fast, small, well-supported |
| Hash chain | **SHA-256** | P22.1 IntegrationAuditWriter precedent |
| Drift detection | **Custom Python** + **Pandas** for SyncScore EWMA | Custom + benchmark regression |
| Existing substrate | **40-ObservabilityAlertingSpec_v1.0.md** | S13 extends, not replaces |

### §3.6 Security Considerations

- **Audit log append-only at DB level**: revoke `UPDATE`/`DELETE` on `audit_log` for all roles except audit-export.
- **S3 audit archive inherits S11's COMPLIANCE guarantee** — no deletion, even by root.
- **Ed25519 signing keys** sealed in SOPS, loaded at startup, never in logs, rotated annually with overlap.
- **Grafana + Prometheus + Loki behind OAuth**; no anonymous access.
- **Alertmanager routes are secrets** (PagerDuty key, Slack webhook) — sealed in SOPS.
- **Audit query API read-only and rate-limited** (60 req/min per IP); payload only if requester authorized for that `agent_id` (RBAC/ABAC).
- **No intimate data, no surveillance raw data, no decrypted secrets** in metrics or logs. Promtail log scrubber redacts known patterns: Discord tokens, API keys, private keys, mnemonic words.
- **Trace payloads** may contain LLM messages; sampling reduced to 10% for normal traffic. Full-message log in audit, not trace.
- **Loki/Prometheus disk bounded**: 90d hot, 1y cold, then deleted.
### §3.7 Failure Modes & Recovery

| Failure | Detection | Recovery | RTO/RPO impact |
|---|---|---|---|
| Prometheus crash | systemd restart; scrape failures | Restart, replay from WAL; remote write covers | RTO 5min; RPO 1 scrape (15s) |
| Loki unavailable | Promtail retry | Logs buffer locally; replay on recovery | RTO up to 1h; RPO up to 1h |
| Grafana down | Browser 503 | Restart; dashboards stateless | RTO 5min; no data loss |
| Audit chain break | Weekly verifier | `AE.audit.chain_break` CRITICAL; manual investigation; if lost, declare incident | Detection 7d worst; RPO up to 7d |
| Alertmanager down | No alerts | Restart; queued; some loss | RTO 5min; brief alert loss |
| OTel collector down | Trace gaps | Retry w/ backoff; some loss acceptable | RPO up to 5min |
| S3 audit export fails | Export job exit code | Retry next hour; CRITICAL at 24h | RPO up to 24h to cold |
| Drift false positive | Threshold breach | Operator reviews; threshold tuning | Investigation only |
| Log scrubber bug | Pattern not redacted | Hotfix; rotate leaked secret | One-time exposure |

**Audit compromise (worst case):** If chain broken AND S3 archive missing AND agent signing key compromised → P0 incident. Cold-storage forensic analysis. Per AGENTS.md §6, escalate to operator + Oracle.

### §3.8 Dependencies

- **S1 (Runtime)** — Each Hermes exposes metrics + structured logs; systemd journal is source of truth.
- **S5 (Event Store)** — Audit events also published to S5; S13 and S5 share `audit_log` writer contract.
- **S9 (Wallet)** — Financial transaction events from S9; S13 displays them.
- **S11 (S3 Backup)** — Audit cold storage IS the S11 COMPLIANCE bucket; same retention.
- **S12 (LLM Gateway)** — LLM cost, error rate, latency metrics from S12 exporter.
- **S14 (Deployment)** — Prometheus + Grafana + Loki deployed by S14's Ansible; S14 health metrics feed S13.
- **S15 (Documentation)** — SLO/SLA definitions, alert runbooks, drift thresholds in S15's evidence + runbooks.

---

## §4 S14. Deployment & VPS Management

### §4.1 Purpose

S14 is the **runtime substrate and ship pipeline** for the entire society. The constraint from synthesis §4.14 is hard: **one large VPS until >32 cores / >64 GB RAM is needed** (Faiz lock). The substrate is systemd (not Docker Compose — Docker adds overhead with no value at this scale) + cgroup v2 (per-Hermes isolation) + Ansible (provisioning) + Caddy/Nginx (reverse proxy with TLS) + SOPS/age + Vault (secrets). S14 owns: (a) **VPS provisioning**, (b) **per-Hermes systemd unit management** (one unit per Hermes, isolated cgroup), (c) **deploy pipeline** (pull → build → test → canary → rollout), (d) **blue-green deployment** for society-wide updates, (e) **health monitoring** (systemd watchdog + Prometheus exporter), and (f) **networking** (reverse proxy, internal firewall, TLS termination).

S14 is **the only subsystem allowed to touch the host OS** beyond what S1's per-Hermes runtime needs. All host-level changes (kernel params, cgroup layout, systemd drop-ins, firewall rules) flow through S14's Ansible playbooks, version-controlled, peer-reviewed. This is the **defense against host-level configuration drift** — the same class of drift that breaks production systems in 2026 per multiple incident reports.

### §4.2 Components

1. **Primary VPS** — Single Ubuntu 24.04 LTS. Initial sizing: 16 cores / 32 GB RAM / 500 GB NVMe. Scale-up trigger: aggregate cgroup v2 utilization > 80% sustained 7d. Scale-out trigger: >32 cores needed (per Faiz lock) — multi-VPS deferred to P35+.
2. **Systemd Service Unit per Hermes** — `hermes-{name}.service`. Directives: `Type=notify`, `Restart=on-failure`, `RestartSec=5s`, `StartLimitBurst=5`, `StartLimitIntervalSec=60s`, `WatchdogSec=120s`. Drop-in `hermes-{name}.service.d/override.conf` provides per-agent env vars.
3. **cgroup v2 Subtree per Hermes** — `hermes.slice/hermes-{name}.slice`. Limits: `CPUWeight=200` (~2 vCPU share), `MemoryMax=4G`, `MemoryHigh=3G`, `IOWeight=100`, `PidsMax=400`. `Delegate=yes` in slice.
4. **Ansible Playbook (`provision.yml`)** — Idempotent: (a) initial VPS setup (apt, packages, sysctl), (b) PostgreSQL + Redis install, (c) cgroup v2 layout, (d) systemd drop-ins, (e) SOPS/age setup, (f) Prometheus/Grafana/Loki, (g) Caddy with TLS, (h) backupd + llmgw, (i) firewall. Two-tier: `bootstrap.yml` (one-time) + `site.yml` (per-deploy).
5. **Deploy Pipeline (`deploy.sh`)** — (1) `git pull`, (2) `make build` versioned artifact, (3) `make test`, (4) `make canary` one Hermes, (5) `make smoke` smoke test, (6) `make rollout` to remaining Hermeses (blue-green per Hermes).
6. **Blue-Green per Hermes** — `hermes-{name}-blue` and `hermes-{name}-green` working dirs. Active symlinked to `hermes-{name}`. Deploy swaps symlink and restarts. Rollback = swap back.
7. **Reverse Proxy (Caddy 2.7+)** — TLS via Let's Encrypt auto-renewal. Routes: `/{hermes}/`, `/metrics`, `/grafana`, `/audit`. HSTS, TLS 1.3 only.
8. **Firewall (UFW + nftables)** — Default deny. Allow: 22 (SSH key-only, Tailscale), 80/443 (Caddy), 9100-9110 (Prometheus, localhost/Tailscale), 5432 (PG, localhost/Tailscale), 6379 (Redis, localhost/Tailscale), 9090 (Prometheus, Tailscale), 3000 (Grafana, Tailscale).
9. **SOPS + age** — Encrypted secrets at rest. `secrets.yaml` canonical encrypted; per-Hermes drop-in references `EnvironmentFile=/etc/hermes/secrets-{name}.env` (decrypted at deploy, never plaintext longer than deploy).
10. **Vault (HashiCorp Vault 1.15+)** — Runtime secrets. `backupd` and `llmgw` authenticate via AppRole; receive short-lived (24h) tokens for KMS-wrapped DEKs and provider keys. Single-instance on same VPS with file backend + auto-unseal via cloud KMS (future: AWS KMS, initially: local unseal with split-key ceremony).
11. **Health Monitoring** — systemd watchdog sends `WATCHDOG=1` every 30s; if missed, systemd kills. Prometheus exporters expose unit state. S13 alerts on any unit in `failed` state for > 5min.
12. **Scaling Decision Logic** — Quarterly review (or S13-triggered): (a) `MemoryHigh` triggered for >50% of Hermeses for 7d → scale RAM 2x; (b) `CPUWeight` saturation >80% for 7d → scale cores 2x; (c) >32 cores needed → evaluate multi-VPS (P35+); (d) >64 GB RAM → evaluate multi-VPS.
### §4.3 Data Flow

**Provision flow (initial):** (1) Operator runs `ansible-playbook bootstrap.yml -i new-vps`. (2) Playbook installs packages, configures sysctl (`vm.swappiness=10`, `net.core.somaxconn=1024`). (3) Installs PG, Redis, Prometheus, Grafana, Loki, Tempo, Caddy, backupd, llmgw. (4) Configures cgroup v2 under `hermes.slice`. (5) Loads SOPS-encrypted secrets via `sops --decrypt secrets.yaml > /etc/hermes/secrets.yaml` (`chmod 600`). (6) Verifies systemd units start; runs `caddy validate`; `pg_isready`; `redis-cli ping`. (7) Emits `AE.deploy.provision_completed` to S5.

**Deploy flow (per Hermes):** (1) `make deploy-hermes NAME=pharsa`. (2) Pipeline: pull → build → test. (3) Canary: copy to `hermes-pharsa-green/`, restart, smoke. (4) If smoke passes: swap symlink → green, restart active. (5) If fails: keep blue, alert operator. (6) Emit `AE.deploy.hermes_rolled_out` with version + git SHA.

**Rollback flow:** (1) Post-deploy SLO breach detected within 30 min. (2) Swap symlink back to previous version, restart. (3) Emit `AE.deploy.rollback` with reason. (4) Operator postmortem within 24h.

**Scaling flow:** (1) S13 dashboard shows sustained saturation. (2) Operator reviews; if scale-up justified: `ansible-playbook site.yml --tags=scale` triggers provider resize API. (3) New resources online within minutes. (4) No restart; cgroup limits remain.

### §4.4 Interfaces

**Exposes:** `S14.deploy` (inbound operator: `make deploy-hermes NAME=<x>`), `S14.provision` (inbound: `ansible-playbook ...`), `S14.health` (outbound S13: `node_exporter` + Hermes unit metrics), `S14.logs` (outbound S13 Loki: journal → Promtail → Loki), `S14.deploy_secret` (outbound S11, S12: inject secrets at deploy), `S14.unit_state` (outbound S1: systemd status).

**Consumes:** `S20.kms` (future Security: Vault auto-unseal), `S13.metrics` (SLO breach → auto-rollback), `S5.publish_event` (deploy events).

### §4.5 Technology Choices

| Component | Tool | Rationale |
|---|---|---|
| OS | **Ubuntu 24.04 LTS** | 5-year support; systemd 255+ with cgroup v2 native |
| Process supervisor | **systemd** (Type=notify, watchdog) | OS-level; no container overhead; `systemd-cgtop` visibility |
| Resource isolation | **cgroup v2** (native) | Linux 5.8+; unified hierarchy; clean `MemoryHigh`/`MemoryMax` |
| Provisioning | **Ansible 9+** | Declarative, idempotent, agentless; large ecosystem |
| Reverse proxy | **Caddy 2.7+** | Auto-TLS via Let's Encrypt; simple config; HTTP/3 native |
| Secrets at rest | **SOPS + age** (existing) | Battle-tested; integrates with git |
| Runtime secrets | **HashiCorp Vault 1.15+** | Industry standard; dynamic secrets; audit log |
| Firewall | **UFW + nftables** | Ubuntu default + raw nftables for advanced |
| Build | **Make** + shell scripts | Simple; no Docker in production |
| CI/CD | **GitHub Actions** | Self-hosted runner on VPS for deploys |
| Existing substrate | **`44-DeploymentGuide_v1.0.md`** | S14 extends existing, not replaces |

### §4.6 Security Considerations

- **SSH key-only**, password disabled, restricted to operator IP via Tailscale.
- **Tailscale overlay network** for operator access + Prometheus/Grafana exposure; no public management UIs.
- **Caddy TLS 1.3 only**, HSTS preload, no weak ciphers, OCSP stapling. Auto-renewal.
- **SOPS-encrypted secrets** in git; decryption keys (age) on operator machine + deploy runner only. Never committed in plaintext.
- **Vault tokens** short-lived (24h); auto-renewed; never written to disk in plaintext by clients.
- **cgroup v2 isolation** prevents one Hermes from starving others. `PidsMax=400` prevents fork bombs.
- **systemd sandboxing** in each Hermes unit: `NoNewPrivileges=yes`, `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`, `ReadOnlyPaths=/var/lib/hermes/{name}/`, `WriteOnlyPaths=/var/lib/hermes/{name}/tmp/`. Limits what a compromised Hermes can do to host.
- **No secrets/API keys/tokens** ever as command-line args (visible in `ps`); always from env files or Vault.
- **Ansible playbook runs auditable** via `--check` + `--diff`; pre-run dry-run mandatory for `bootstrap.yml`.
- **VPS provider account** uses hardware MFA; root login disabled; only operator + Guinevere (supervised deploy) can provision.
- **No raw surveillance data, no intimate content** stored on VPS in plaintext; all sensitive data uses S4's per-agent encryption.
### §4.7 Failure Modes & Recovery

| Failure | Detection | Recovery | RTO/RPO impact |
|---|---|---|---|
| Hermes process crash | systemd `Restart=on-failure` | Restart; if 5 in 60s → held; operator alerted | RTO 5s; no data loss |
| Hermes hang (watchdog miss) | systemd `WatchdogSec=120` | SIGKILL → restart; alert | RTO 2min; no data loss |
| OOM kill | cgroup v2 OOM | systemd restart; if recurring, `MemoryHigh` lowered or RAM scaled | RTO 5s; possible in-flight message loss |
| VPS hardware failure | VPS provider status | Provision new VPS; run `bootstrap.yml`; restore from S3; replay S5 | RTO 4h; RPO up to 1h (per S11) |
| Disk full | `node_filesystem_free` | Alert; logrotate + Loki retention shrink; clean tmp | RTO 30min; RPO 0 |
| Network partition | Tailscale heartbeat | Caddy health check fails; routes stop; wait for partition | RTO depends on partition duration |
| Bad deploy (failed canary) | Smoke test failure | Abort rollout; keep blue; operator reviews | RTO 0; no user impact |
| Bad deploy (passed canary, failed prod) | SLO breach in 30min | Auto-rollback via blue-green swap | RTO 1min; up to 30min degraded |
| Caddy TLS renewal failure | Caddy health check | Operator manually renews; Caddy fallback to cached cert | RTO 0 if cached; 1h if expired |
| Vault sealed | Vault health endpoint | Operator runs unseal ceremony (5 of 9 keys) | RTO 30min; services degraded |
| SSH key compromise | Tailscale log anomaly | Rotate age key, regenerate SOPS, re-encrypt all secrets, rotate VPS SSH keys | RTO 1h; security event |

**VPS provider failure (Hetzner/DO/AWS outage):** Backup VPS pre-provisioned in alternate region (same Ansible playbook, smaller instance for emergency). `bootstrap.yml` runs <15min; restore from S3 <4h; society resumes. After primary recovers, decommission backup.

### §4.8 Dependencies

- **S1 (Runtime)** — Each Hermes is a systemd unit; S14 owns unit file, S1 owns binary + config.
- **S5 (Event Store)** — All deploy events emitted to S5 for audit.
- **S11 (S3 Backup)** — S11 backup runs as systemd unit on this VPS; S14 supervises.
- **S12 (LLM Gateway)** — `llmgw` deployed as systemd unit by S14; provider keys injected by S14.
- **S13 (Observability)** — Prometheus + Grafana + Loki + Tempo deployed by S14's Ansible; S14 health metrics consumed by S13.
- **S15 (Documentation)** — Deploy runbooks, scaling decision criteria, SLO definitions all live in S15.
- **VPS provider** (Hetzner / DigitalOcean / AWS Lightsail) — TBD per ADR.

---

## §5 S15. Documentation & Traceability

### §5.1 Purpose

S15 is the **traceability substrate** that allows the society — and the operator — to answer the question "what did we decide, why, and where is it implemented?" This is not a documentation style exercise; it is a **requirement of auditability** for a system that will be running autonomously across multi-year horizons. The synthesis §4.15 makes this binding: BRD, PRD, SRS, FSD, TDD, RTM, Risk Register, Acceptance Criteria, Glossary, ADR log are not seven siloed files; they are **one bidirectional traceability graph**. Every requirement (`REQ-F-NNN` or `REQ-NF-NNN`) traces forward to: at least one design section, at least one test, at least one evidence artifact, and at least one auditor sign-off. Every ADR traces forward to: at least one affected requirement, one affected subsystem, one rollout decision. Every risk (ISO 31000 form) traces forward to: at least one mitigation owner, one deadline, one review cadence.

S15 also owns the **doc family structure** (the 8 families in the existing `docs/README.md`) and the **doc versioning convention** (`NN-{name}_vN.N.md` per AGENTS.md §14). It is the reason the operator can read the repo 12 months from now and still understand the design. S15 does **not** own the per-document content; S15 owns the **integrity of the graph** — that links are valid, IDs are stable, and the GWT acceptance criteria are the lingua franca between designer, implementer, and auditor.

### §5.2 Components

1. **Document Suite (IIBA BABOK + IEEE 830/ISO 29148:2018)** — Six core: **BRD**, **PRD**, **SRS** (with explicit AI/ML section), **FSD**, **TDD** (C4 model), **RTM**. Plus three supporting: **Risk Register** (ISO 31000), **Acceptance Criteria Catalog** (GWT), **Glossary** (ISO 24765). Plus **ADR log** (MADR template).
2. **ADR System (MADR 3.0)** — Each ADR: title, status (Proposed/Accepted/Superseded/Deprecated), context, decision, consequences, alternatives, date, author. Immutable once Accepted. Superseded ADRs marked but never rewritten. Numbering: `ADR-NNN-{shortname}.md` strictly sequential. Next free: ADR-055.
3. **Requirements Traceability Matrix (RTM)** — CSV + rendered HTML/PDF. Columns: `REQ_ID`, `Family`, `Type (F|NF)`, `Source (BRD ref)`, `Description`, `Design Section (FSD ref)`, `Test (TDD ref)`, `Evidence Path`, `Auditor Sign-off`, `Risk Link`, `NFR Link`, `Status`. Append-only: never drop rows; mark `Superseded`. Six coverage metrics: forward ≥ 1.0, backward ≥ 1.0, implementation, evidence, risk, NFR.
4. **Risk Register (ISO 31000)** — Per row: `RSK_ID`, `Description`, `Likelihood (1-5)`, `Impact (1-5)`, `Rating = L × I`, `Mitigation`, `Owner`, `Due Date`, `Status`, `Linked REQ`, `Linked Test`, `Linked Evidence`, `Linked Auditor Sign-off`, `Review Date`. High/Critical (rating ≥ 15) MUST link to ≥1 REQ, ≥1 TEST, ≥1 Evidence, ≥1 Auditor Sign-off. Quarterly review.
5. **Acceptance Criteria (GWT)** — Per requirement: `Given <precondition>, When <action>, Then <observable outcome>`. Stored in `16-AcceptanceCriteriaCatalog_v1.0.md` (or successor), referenced by RTM. Binary test (pass/fail) — not "looks good."
6. **Glossary (ISO 24765)** — Canonical list of terms. Each entry: term, definition, source, related. Updated when new domain terms introduced. Bilingual: Indonesian term + English technical in parentheses.
7. **Doc Versioning & Frontmatter** — `NN-{name}_vN.N.md` filename. Frontmatter required: `title`, `status` (Draft/Dalam Review/Diterima/Didepresiasi/Diarsipkan), `date`, `last_modified`, `owner`, `executor`, `classification`. Versioning: `vMAJOR.MINOR`; major for structural, minor for clarification.
8. **Evidence Pattern (`docs/setup-evidence/P{NN}/`)** — Each phase has its own: `README.md`, `plan/`, `research/`, `evidence/`. Canonical home for per-phase artifacts; parent `docs/setup-evidence/P28-P36-masterplan/` is umbrella.
9. **Doc Family Structure (8 families)** — 00-core (BRD/PRD/architecture/agent loop/memory/API/persona), 10-governance (charter/SRS/FSD/TDD/RTM/AC/ADR), 20-security, 30-data, 40-operations, 50-quality, 60-persona, 70-finops. Each family has 2-digit prefix (00-70) and reserved range.
10. **Cross-Reference Validation CI** — GitHub Actions job on every PR: parses all markdown, extracts internal links, verifies resolve. Broken link → CI fail. Verifies REQ/ADR/RSK IDs well-formed, newly introduced IDs appended (not replacing).
11. **PDF Snapshot at Phase Boundaries** — On every phase transition, CI job renders all "Diterima" docs to PDF via `pandoc + weasyprint`, computes SHA-256, stores in `docs/snapshots/{phase_name}/`. Frozen immutable record.
12. **Bilingual Convention** — Indonesian narrative prose + English technical terminology. Frontmatter English; body Indonesian narrative with English technical in backticks/parentheses. Preserved from existing repo.
### §5.3 Data Flow

**Document creation:** (1) Author writes draft Markdown in feature branch. (2) Frontmatter filled; status `Draft`. (3) PR opened; CI runs cross-reference validation. (4) Reviewer comments; author addresses. (5) PR approved; status → `Diterima`; merge to main. (6) PDF snapshot rendered at next phase boundary.

**RTM update:** (1) New REQ ID added to SRS. (2) RTM CSV updated (append-only) with REQ_ID + design/test/evidence links. (3) Test created. (4) Evidence collected (per AGENTS.md §11, 12-section verification.md). (5) Auditor signs off. (6) RTM row updated with evidence path + sign-off date.

**ADR creation:** (1) Decision need identified. (2) ADR drafted in MADR; status `Proposed`. (3) PR opened; if touches ≥2 docs or affects safety boundary → flagged in PR template. (4) Review by operator + Guinevere; founder override → escalate to Faiz. (5) Status → `Accepted`; ADR-NNN allocated; RTM updated. (6) If superseded → new ADR-NNN' with `Supersedes: ADR-NNN`; old marked `Superseded by ADR-NNN'`.

**Risk register:** (1) Risk identified during design. (2) Row added with L, I, rating, mitigation, owner. (3) Mitigation linked to REQ + TEST + Evidence. (4) Review quarterly; status updated; rating re-assessed.

**CI validation:** (1) PR opened. (2) Script parses all `*.md` in `docs/`. (3) Extracts internal links, REQ IDs, ADR IDs, RSK IDs. (4) Validates each link resolves; each ID exists; new IDs in valid range. (5) Fail → CI red; PR blocked.

**PDF snapshot (phase boundary):** (1) Phase transition triggered. (2) List all `Diterima` docs. (3) Render each to PDF; compute SHA-256. (4) Store in `docs/snapshots/{phase_name}/` with `manifest.json`. (5) Tag git with `snapshot-{phase_name}`.

### §5.4 Interfaces

**Exposes:** `S15.doc_query` (operator/auditor: `docs/README.md` index + grep + CI HTML), `S15.req_query` (RTM CSV/HTML/API), `S15.adr_query` (`adr/ADR-Index` + per-ADR), `S15.evidence_index` (S13, S11: `docs/setup-evidence/P{NN}/README.md`), `S15.glossary_lookup`, `S15.pdf_snapshot` (auditor: `docs/snapshots/{phase}/`), `S15.ci_check` (GitHub Actions: red/green).

**Consumes:** `S5.publish_event` (doc-change events hash-chained: `AE.doc.accepted`, `AE.adr.accepted`), `S13.audit_query` (link back to source doc via S15).

### §5.5 Technology Choices

| Component | Tool | Rationale |
|---|---|---|
| Doc format | **Markdown** (CommonMark + GFM) | Diff-friendly, git-friendly, renderable to HTML/PDF |
| Doc index | **MkDocs Material** (rendered to internal URL) | Existing pattern; search; theme; lightweight |
| ADR format | **MADR 3.0** | Standard 2026 template; frontmatter-driven |
| RTM format | **CSV** (source) + **rendered HTML** (output) | CSV is data; HTML is human interface |
| Cross-ref CI | **Custom Python** + `markdown-it-py` | Parses markdown AST; validates links/IDs |
| PDF rendering | **pandoc 3.x** + **weasyprint** | Best Markdown → PDF pipeline in 2026 |
| Snapshot storage | Git (tagged commits) + `docs/snapshots/` | Immutability via git; per-phase folder for browse |
| Doc-suite host | **GitHub Pages** (or self-hosted MkDocs) | TBD per ADR; default = MkDocs in repo rendered to internal URL |
| Existing substrate | **`docs/` (8-family, 44 active, 18 archived)** | S15 extends, not replaces |

### §5.6 Security Considerations

- **No secrets, no SOPS/age keys, no raw credentials, no decrypted values, no intimate data, no surveillance data** ever committed to `docs/` or `adr/`. All sensitive data lives in S3 (S11), per-agent encrypted PG schemas (S4), or sealed secrets.
- **Public-facing docs** (if any) go through redaction CI job scrubbing known patterns (tokens, keys, mnemonics) before rendering. Default: no public-facing docs; all STRICTLY PRIVATE & CONFIDENTIAL.
- **PDF snapshots** stored in git history (immutable) + `docs/snapshots/` (browsable). No special protection beyond git's integrity.
- **Doc-change audit events** emitted to S5 (hash-chained) for every status transition. **Defense against retroactive doc tampering.**
- **Glossary terms** that are redacted/embargoed stored separately in `docs/60-persona/_redacted/` with restricted RBAC; not in public glossary.
- **Bilingual pattern** preserved but never reveals intimate or surveillance content; technical English terms appropriate for any audience.
- **Cross-reference validation** prevents broken-link hiding; CI red on any broken link forces fix.
- **No raw intimate data or personal identifiers** in any doc, evidence file, or RTM. Where operator data referenced, only metadata (timestamps, REQ IDs, scope tags) — never content.
### §5.7 Failure Modes & Recovery

| Failure | Detection | Recovery | RTO/RPO impact |
|---|---|---|---|
| Doc link broken | CI red | Author fixes; PR re-validates | RTO 1 PR cycle; no data loss |
| REQ ID typo | CI red | Author fixes; RTM auto-validates | RTO 1 PR cycle |
| ADR-NNN conflict (duplicate) | CI red | Highest-numbered wins; other renumbered | RTO 1 PR cycle |
| MkDocs render failure | CI red | Author fixes broken doc; PR re-renders | RTO 1 PR cycle |
| PDF snapshot fails | CI red | Re-run snapshot job; check pandoc/weasyprint | RTO 1 CI cycle |
| RTM CSV corruption | Git revert | Restore from prior commit; re-apply appends | RTO 1 PR cycle |
| Doc history rewriting | Git log review (operator) | `git reflog` to recover; force-push disabled | RTO 1 day; sev-1 incident |
| Doc-change audit gap | S5 missing event for status transition | Re-emit event; backfill `AE.doc.accepted` | RTO 1 PR cycle; RPO 1 audit cycle |
| Glossary term misuse | Reviewer catch | Update glossary; cross-link to doc | RTO 1 PR cycle |
| Phase-boundary snapshot missing | Operator notice | Re-run snapshot job from main | RTO 1 CI cycle |

**Doc-tampering scenario:** If git history rewritten (force-push bypass) → git reflog recovery; force-push to main disabled; protected branch. If audit chain shows doc-change event without corresponding git commit → investigate; sev-1 incident. If RTM edited to remove a row → git revert; S5 audit event cross-check detects.

### §5.8 Dependencies

- **S1 (Runtime)** — Doc-driven config of Hermeses (model tier, persona file, S3 bucket refs).
- **S5 (Event Store)** — Doc-change events hash-chained; audit substrate.
- **S9 (Wallet)** — Doc references to spending tiers, ADR refs to financial decisions.
- **S11 (S3 Backup)** — Snapshot PDFs also archived to S3 COMPLIANCE (per synthesis §4.15); same retention.
- **S12 (LLM Gateway)** — Doc references to model assignments, quota defaults.
- **S13 (Observability)** — SLO/SLA doc part of S15; S13 enforces SLOs.
- **S14 (Deployment)** — Deploy runbooks in S15; S14 executes them.
- **All S1-S14** — Each subsystem's SRS section, FSD section, and TDD section are part of S15's doc suite.

---

## §6 Cross-Cutting Concerns (S11-S15)

All five subsystems share **PostgreSQL** (durable: audit, quota, cost, deploy events, doc metadata), **Redis** (coordination cache: rate limits, circuit breakers, deploy locks, RTM cache), **S3** (cold archive: audit, backups, snapshots, evidence), **systemd** (runtime supervisor), **Ansible** (provisioner), and **SOPS/age + Vault** (secrets substrate). All five emit audit events to S13's `audit_log` using the same hash-chained writer contract from P22.1 IntegrationAuditWriter: S11 emits `AE.backup.*`/`AE.dr.*`, S12 emits `AE.llm.*`, S13 emits `AE.audit.*`/`AE.observability.*`, S14 emits `AE.deploy.*`, S15 emits `AE.doc.*`/`AE.adr.*`/`AE.risk.*`. A single GitHub Actions CI job validates all cross-references across S11-S15 (doc links resolve, REQ/ADR/RSK IDs valid and sequential, evidence paths exist) — the defense against documentation rot. At every phase transition, a CI job renders all "Diterima" docs to PDF, computes SHA-256, and stores in `docs/snapshots/{phase_name}/` as the frozen historical record.

## §7 New ADRs Allocated (Phase 3)

Per synthesis §8.2, the following design choices from this document require new ADRs (next free: ADR-055). Each will be created in Phase 4 in MADR 3.0 format:

| ADR | Title | Decision Authority |
|---|---|---|
| ADR-055 | Hermes Society Topology (masterplan) | Faiz |
| ADR-056 | S3 Object Lock COMPLIANCE default for ledger/audit/evidence | Faiz |
| ADR-057 | LLM Gateway Model Pool with explicit version pinning | Guinevere (operator review) |
| ADR-058 | Hash-chained audit trail extends P22.1 to society level | Guinevere (operator review) |
| ADR-059 | systemd + cgroup v2 as runtime substrate (no Docker Compose) | Guinevere (operator review) |
| ADR-060 | Blue-green per-Hermes deployment with canary | Guinevere (operator review) |
| ADR-061 | RTM bidirectional + 6 coverage metrics as standard | Guinevere (operator review) |
| ADR-062 | PDF snapshot at every phase boundary | Guinevere (operator review) |
| ADR-063 | Vault single-instance with KMS auto-unseal (future) | Guinevere (operator review) |
| ADR-064 | Doc family structure 8 families (00-70) preserved | Guinevere (operator review) |

## §8 Footer

### §8.1 Verification Checklist

- [x] Each of S11–S15 has 8 subsections (Purpose, Components, Data Flow, Interfaces, Technology Choices, Security, Failure Modes, Dependencies).
- [x] No implementation code; architecture only.
- [x] No secrets, SOPS keys, Vault credentials, or intimate data exposed.
- [x] S3 Object Lock COMPLIANCE mode preserved as non-negotiable for ledger/audit/evidence.
- [x] Backup mandatory per Faiz lock.
- [x] Audit trail hash-chained (per P22.1 IntegrationAuditWriter contract).
- [x] Cross-references to existing repo docs (40-*, 41-*, 43-*, 44-*, 22-*) preserved.
- [x] Bilingual pattern (Indonesian narrative + English technical) preserved.
- [x] Doc naming convention (`NN-{name}_vN.N.md`) consistent.
- [x] Evidence pattern (`docs/setup-evidence/P{NN}/`) referenced.
- [x] 8-family doc structure referenced.
- [x] ADR-055+ allocation recorded.

### §8.2 Next Steps

1. **Phase 3 complete**: All 5 subsystems (S11-S15) designed; this file is the architecture input.
2. **Phase 4 (Doc Suite)**: Per synthesis §9.4, each subsystem gets full SRS/FSD/TDD section. ADRs 055-064 drafted in MADR 3.0 format.
3. **Phase 5 (Implementation)**: Implementation waves P28-001 onwards; per-subsystem evidence files in `docs/setup-evidence/P28-P36-masterplan/evidence/`.
4. **Auditor wave**: Per AGENTS.md §2.10, spawn parallel auditor specialists for each implemented subsystem.

### §8.3 Provenance

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere (subagent-driven) | Initial Phase 3 architecture design for S11–S15. Derived from `research-synthesis.md` (690 lines), `synthesis-external-architecture.md`, `synthesis-external-operations.md`; cross-referenced to `40-ObservabilityAlertingSpec_v1.0.md`, `41-SLO_SLA_ErrorBudget_v1.0.md`, `43-DisasterRecoveryPlan_v1.0.md`, `44-DeploymentGuide_v1.0.md`, `22-EncryptionKeyMgmt_v1.0.md`, P22.1 IntegrationAuditWriter, AGENTS.md v2.4. |

---

> **STRICTLY PRIVATE & CONFIDENTIAL** — Project Guinevere. Dokumen ini adalah bagian dari Phase 3 (Master Architecture) P28-P36 Hermes Society Masterplan. Tidak ada secrets, SOPS/age keys, Vault credentials, decrypted values, intimate data, atau surveillance data dalam dokumen ini. S3 Object Lock COMPLIANCE mode untuk ledger/audit/evidence adalah non-negotiable per Faiz lock. Backup mandatory per Faiz lock. Audit trail hash-chained per P22.1 IntegrationAuditWriter contract.