---
title: "P28 Dual Autonomous Hermes — Executable Blueprint"
status: "Active — Blueprint (not implementation)"
date: "2026-06-28"
author: "Guinevere (parent agent)"
phase: "P28 Dual Autonomous Hermes"
prerequisite: "P27 Hermes Society Foundation (definition complete)"
supersedes: "none"
related_docs:
  - docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md
  - docs/setup-evidence/P27/research/p27-research-synthesis.md
  - docs/setup-evidence/P27/research/p27-hermes-native-runtime-inventory.md
  - docs/setup-evidence/P27/research/p27-discord-dual-bot-research.md
  - docs/setup-evidence/P27/research/p27-agent-communication-protocol-research.md
  - docs/setup-evidence/P27/research/p27-private-shared-memory-research.md
  - AGENTS.md
  - adr/ADR-050-knowledge-graph-architecture.md
  - adr/ADR-052-multi-project-context.md
---

# P28 Dual Autonomous Hermes — Executable Blueprint

> **Scope:** This document is an executable blueprint for P28 implementation, NOT the implementation itself. P28 implements the minimum viable Hermes Society: two autonomous Hermes instances (Guinevere + Pharsa) online, conversing without Faiz trigger, with separate memory, shared world model, own autonomy loops, and runtime evidence of liveness. This blueprint tells an implementer *exactly* what to build, what files to create/modify, what commands to run, and how to verify each step.
>
> **Prereq:** P27 Phase 1–4 complete. Research synthesis + enterprise plan + roadmap are in the parent directory of this file.
>
> **Operator Mandate (P27 §1 + P28 §18.1):** Two bots online; talk without Faiz trigger; separate memory; own autonomy loop; shared world model; runtime evidence they're alive.

---

## 1. P28 Mission and Scope

### 1.1 What P28 Delivers (Minimum Viable Society)

| # | Deliverable | Acceptance |
|---|---|---|
| 1 | Two `HermesBrain` instances online (Guinevere + Pharsa) | `systemctl status guinevere-core.service` and `systemctl status pharsa-core.service` both report `active (running)` |
| 2 | Each with own config, own LLM provider/key, own bot token | `cat hermes-config/guinevere.yaml` and `cat hermes-config/pharsa.yaml` show different providers/keys; key blobs never equal |
| 3 | Each with own Discord bot application + token | Discord Developer Portal shows 2 apps (`Guinevere`, `Pharsa`); each has distinct bot user |
| 4 | Both bots online in `#guinevere-chat` Discord channel | `on_ready` fires for both, both receive MESSAGE_CREATE events with content populated |
| 5 | Bots converse visibly without Faiz trigger | Both bots post ≥1 message per 5 minutes autonomously (verified by Discord message log) |
| 6 | Peer dialogue via HPP envelopes over Redis Streams | `redis-cli XLEN hermes:hsoc-foundation-v1:peer:guinevere` ≥1 with intent ∈ {inform, banter, propose, debate, refuse} from pharsa |
| 7 | 3-scope PostgreSQL memory with FORCE RLS isolation | From Guinevere session: `SELECT * FROM memory.private_agents` returns ONLY Guinevere rows; same for Pharsa |
| 8 | Shared world model read/write works for both | `INSERT INTO memory.shared_world` from Guinevere → SELECT returns same row from Pharsa session |
| 9 | Own autonomy loop (simplified 4-rail, NOT full 7-rail) | Both instances have independent `MinimalScheduler` ticking at 30s/60s/300s cadence |
| 10 | Society-wide HARD STOP cascade | Setting `hermes:society:hsoc-foundation-v1:hard_stop=true` halts both within 50ms; sealed-snapshot written |
| 11 | Runtime evidence both instances are alive | (a) Discord `#guinevere-status` shows lifecycle events; (b) `hermes_audit` rows from both `instance_id` values; (c) Prometheus metrics `hermes_alive{instance=...}==1` for both |
| 12 | Conversation rhythm prevents infinite reply loops | Hop counter caps at 4; per-channel Redis cooldown with TTL 30s |

### 1.2 What P28 Does NOT Deliver

P28 is **scoped minimally**. The following are explicitly deferred:

| Deferred to | Component | Reason |
|---|---|---|
| P29 | Full 7-rail MacroStateScheduler with Reflection/Inner Dialogue/Desire/Initiative rails | Too much state complexity for first ship; persona-stabilizing reasoning is delicate |
| P29 | Inner Dialogue rail with PSYA Cognitive Triangle | Requires careful thought-domain sealed-hash audit; out of P28 scope |
| P29 | Ebbinghaus nightly decay sweep | Static default `stability_days` constants fine for P28; cron-based sweep = P29 |
| P29 | PROBE initiative pipeline | Requires safe action space; AGENTS.md §0.4 forbids autonomous destructive ops |
| P30 | `memory.relationship_pairs` table + bilateral intimacy bridge | P28 ships `private` + `shared` only; relationship scope = P30 |
| P30 | `memory.intimacy_bridge_pending` staging table | Same as above; bilateral consent flow is P30 work |
| P31 | 4-domain privacy split runtime classification | P28 emits basic `action_class` enum (`speech`, `action`) only; full 4-domain = P31 |
| P31 | Sycophancy detection metrics (`agreement_ratio`, `persona_drift_score`) | P28 logs dialogue; P31 computes metrics |
| P31 | SentinelAgent (third-in-society monitor) | Not needed for 2-agent minimum |
| P32 | P24 owned Hermes fork integration | P28 uses current hybrid adapter + per-instance config; fork = preferred optimization, not prerequisite |
| P33 | P23 action executors (email, deploy, finance, MCP actions) | P28 has no outbound actions except Discord send |
| P34 | 3rd / 4th Hermes instance + Society governance | 2-agent minimum society only |
| P35 | Cross-VPS Society deployment | Single VPS is sufficient for P28 |
| P36 | Formal verification (ATL, λ_A-calculus runtime lint, KILLBENCH) | P28 ships by behavioral verification; formal = P36 |
| P23 Sky | Voice (P21 SKIP) | Voice channel not in P28 minimum; deferred indefinitely |

### 1.3 P28 Minimum Target (Faiz user mandate)

Per P27 §18.1, the user gave a precise minimum target. P28 satisfies all 12 acceptance criteria above; the 6 user-mandate items map 1:1:

1. **Two bots online** → deliverable #1, #3
2. **Talk without Faiz trigger** → deliverable #5, #4
3. **Separate memory** → deliverable #7
4. **Own autonomy loop** → deliverable #9
5. **Shared world model** → deliverable #8
6. **Runtime evidence they're alive** → deliverable #11

The remaining (#2, #6, #10, #12) are the substrate that makes the user's 6 work.

---

## 2. Prerequisites and Environment

### 2.1 Status of Upstream Phases

| Phase | Status (as of 2026-06-28) | P28 Dependency Status |
|---|---|---|
| P19 Multi-Project Context | LIVE PARTIAL (4 INFO gaps) | READY — `project_id` from `LIFE_KERNEL_PROJECT_ID` env var; `_resolve_thread_id(project_id)` pattern reusable |
| P20 Living Autonomy Kernel | LIVE (accepted-risk pass; 420 tests) | READY — `HermesBrain`, `HeartbeatService`, `HardStopHandler`, `LifeMindGraph` all live and injectable |
| P22 Integration Hub | PARTIAL LIVE (3/13 active: filesystem, vps, discord) | READY — Discord adapter covers message sending; filesystem + vps cover SOUL/config + restart on lifecycle |
| P23 Embodied Operations | PLAN_ONLY (no code) | NOT NEEDED — P28 has zero outbound action executors |
| P24 Hermes Fork | PLAN FIXED, IMPL HOLD | NOT NEEDED — P28 uses hybrid adapter + per-instance config (fork is preferred, not required) |
| P21 Voice | DEF COMPLETE, IMPL HOLD, SKIP | NOT NEEDED — Voice not in P28 minimum |

### 2.2 VPS Requirements

| Resource | Required | Notes |
|---|---|---|
| Existing Ubuntu VPS with Guinevere runtime | Required | P28 deploys ON TOP of existing `guinevere-core.service` + `guinevere-discord.service` (Guinevere's processes stay running) |
| Single VPS sufficient for P28 | Confirmed | Resource estimate: +50-100 MB RAM per additional Hermes (Discord gateway + brain process); 2 vCPU / 4 GB total is comfortable |
| PostgreSQL 15+ | Required | For `memory.*` schema + RLS + pgvector (existing per ADR-050) |
| Redis 7+ | Required | For peer Streams + cooldowns + last-turn keys (existing) |
| SOPS/age with `sops` CLI | Required | For decrypting `DISCORD_BOT_TOKEN_*-HERMES_*` envs at startup |
| systemd with `Slice=` support | Required | P28 adds `pharsa-*.service` units with same hardening as Guinevere units |

### 2.3 Discord Setup Requirements (Operator Action)

Faiz (operator) must provision BEFORE Step 14:

1. **Discord Developer Portal:** Create a second Application named `Pharsa`. Under `Bot`, generate a token, enable the `MESSAGE_CONTENT` privileged intent (under 10,000-user threshold → no review needed per ArkCore June 2026 rule). Save token for SOPS encryption. Note the bot's `USER_ID`.
2. **SOPS-encrypt the Pharsa bot token:** Use `sops -e --age <age-recipient> --in-place env.pharsa.template` to encrypt; store at `.env.pharsa` (encrypted at rest); decrypt at runtime via `EnvironmentFile=` in systemd unit.
3. **Invite Pharsa bot to the existing `hermes-foundation` Discord guild** with permissions: `Send Messages`, `Read Message History`, `Read Messages/View Channels`, `Embed Links`, `Create Public Threads`, `Add Reactions`, `Use Slash Commands`.
4. **Channels** (already exist or create):
   - `#guinevere-chat` (primary conversation channel; both bots post here)
   - `#guinevere-status` (dashboard/lifecycle updates; both bots post)
   - `#guinevere-logs` (audit summary publishing; both bots post)
5. **Confirm both bots visible in member list** with `[BOT]` tag.
6. **Export env vars as `PHARSA_BOT_TOKEN`, `PHARSA_BOT_USER_ID`** (the latter is the bot's snowflake id needed by the rhythm/handler for peer routing).

### 2.4 PostgreSQL Requirements

| Schema | Status | Notes |
|---|---|---|
| `memory` schema with `kg_*` family | Existing (ADR-050) | P28 EXTENDS `kg_*` tables with `scope`, `pair_id`, `created_by_agent` columns (Step 6) |
| `memory_sessions` schema | Existing | (Optional) P28 may reuse for conversation thread persistence |
| New: `memory.private_agents` table | P28 creates | Step 6 |
| New: `memory.shared_world` table | P28 creates | Step 6 |
| New: `hermes_audit` table | P28 creates | Step 6 |
| New: `hpp_outbox` table | P28 creates | Step 8 |
| New: `hpp_inbox` table | P28 creates | Step 9 |

### 2.5 Redis Requirements

| DB # | Allocation | Owner |
|---|---|---|
| 0 | system + sessions + rate limits | existing |
| 1-5 | existing services | unchanged |
| **6** | Guinevere Hermes instance state (heartbeat, conversation scratch, peer inbox/cooldowns) | P28 confirms overwrite |
| **7** | Pharsa Hermes instance state (same shapes; instance-scoped key prefix `hermes:pharsa:*`) | P28 creates |
| **8** | Society-shared keys (`hermes:society:hsoc-foundation-v1:*`) including HARD STOP key | P28 creates |

P28 keeps Guinevere on DB6 (no migration) and assigns Pharsa DB7 (new). Society-shared keys (HARD STOP cascade) go on DB8.

### 2.6 Repository Layout (Files P28 Will Touch)

Files to **create** (P28 owned):

| Path | Owner Step |
|---|---|
| `hermes-config/guinevere.yaml` | Step 3 |
| `hermes-config/pharsa.yaml` | Step 2 |
| `hermes-config/SOUL-pharsa.md` | Step 1 |
| `hermes-config/society_manifest.yaml` | Step 3 |
| `systemd/pharsa-core.service` | Step 5 |
| `systemd/pharsa-discord.service` | Step 5 |
| `systemd/pharsa-core.service.d/env.conf` | Step 5 |
| `systemd/pharsa-discord.service.d/env.conf` | Step 5 |
| `vps-mirror/systemd-live/pharsa-core.service` | Step 5 |
| `vps-mirror/systemd-live/pharsa-discord.service` | Step 5 |
| `migrations/p28/001_schema_roles.sql` | Step 6 |
| `migrations/p28/002_private_agents.sql` | Step 6 |
| `migrations/p28/003_shared_world.sql` | Step 6 |
| `migrations/p28/004_intimacy_bridge_stub.sql` | Step 6 |
| `migrations/p28/005_extend_kg_tables.sql` | Step 6 |
| `migrations/p28/006_audit_table.sql` | Step 6 |
| `migrations/p28/007_rls_policies.sql` | Step 6 |
| `migrations/p28/008_hpp_outbox.sql` | Step 8 |
| `migrations/p28/009_hpp_inbox.sql` | Step 9 |
| `src/life_kernel/instance_registry.py` | Step 4 |
| `src/life_kernel/hpp/envelope.py` | Step 8 |
| `src/life_kernel/hpp/transport.py` | Step 8 |
| `src/life_kernel/hpp/outbox.py` | Step 8 |
| `src/life_kernel/hpp/inbox.py` | Step 9 |
| `src/life_kernel/hpp/peer_handler.py` | Step 9 |
| `src/life_kernel/hpp/rhythm.py` | Step 10 |
| `src/life_kernel/lifecycle/minimal_scheduler.py` | Step 11 |
| `src/life_kernel/memory/private_agents_store.py` | Step 13 |
| `src/life_kernel/memory/shared_world_store.py` | Step 12 |
| `src/life_kernel/audit/per_instance_audit.py` | Step 15 |
| `src/life_kernel/metrics/society_metrics.py` | Step 15 |
| `src/discord/hermes_society_bot.py` | Step 14 |
| `src/discord/society_message_handler.py` | Step 14 |
| `src/discord/rhythm.py` | Step 10 |
| `src/discord/pharsa_entrypoint.py` | Step 14 |
| `tests/life_kernel/hpp/test_*.py` (4 files) | Steps 8-10 |
| `tests/discord/test_society_bot.py` | Step 14 |
| `tests/life_kernel/memory/test_private_agents_rls.py` | Step 13 |
| `tests/life_kernel/memory/test_shared_world.py` | Step 12 |
| `tests/life_kernel/lifecycle/test_minimal_scheduler.py` | Step 11 |
| `tests/life_kernel/audit/test_per_instance_audit.py` | Step 15 |
| `tests/life_kernel/test_instance_registry.py` | Step 4 |
| `evidence/p28-dual-hermes/step-NNN/verification.md` × 15 | per-step |
| `evidence/p28-dual-hermes/step-NNN/auditor-gate.md` × 15 | per-step |
| `evidence/p28-dual-hermes/p28-final-report.md` | after all 15 |

Files to **modify**:

| Path | Reason | Step |
|---|---|---|
| `src/core/main.py` | Refactor `app.state.hermes_brain` → `app.state.hermes_brains: dict[str, HermesBrain]` | Step 3 |
| `src/discord/hermes_conversational.py` | Module-level singletons → factories taking `instance_id` | Step 3 |
| `src/discord/_entrypoint.py` | `GUILD_ID` constant → config-driven | Step 3 |
| `src/discord/_startup.py` | Extend presence update for both agents | Step 15 |
| `src/life_kernel/cognition.py` | Register loop per instance | Step 4 |
| `src/life_kernel/heartbeat.py` | Add society-shared HARD STOP listener | Step 4 |
| `src/life_kernel/p16_adapter.py` | Add `agent_id` kwarg | Step 13 |
| `src/life_kernel/p18_adapter.py` | Add `agent_id` kwarg | Step 13 |
| `src/life_kernel/discord_rest_client.py` | Add `instance_id` parameter | Step 15 |
| `hermes-config/config.yaml` | Add `society_manifest_path` pointer | Step 3 |

Files **NOT touched** (hard reject):

- `AGENTS.md`
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`
- `.venv/site-packages/run_agent.py`
- `pyproject.toml` (no new deps; only existing deps)
- Any single-instance deploy script

### 2.7 Cost Projection (per `70-Cost_FinOps_Model_v1.1`)

| Cost Component | Monthly Estimate | Notes |
|---|---|---|
| LLM API (GPT-5.5 + DeepSeek V4 Flash via 9Router) | +$15-30 per agent × 2 = $30-60 | Pharsa uses DeepSeek V4 Flash primary; significantly cheaper |
| Redis DB7 + DB8 memory | +$0-1 | Negligible; VPS-bundled |
| PostgreSQL storage | +50-200 MB | Negligible; VPS-bundled |
| VPS bandwidth (Discord gateway 2x) | +$0-2 | Negligible |
| Ops overhead | +1-2 hr/month Faiz | Conversation rhythm tuning, audit viewing |
| **Total P28 incremental cost** | **~$32-65/month** | Within FinOps v1.1 §4 envelope |

P28 stays well within monthly LLM budget of $30 base + $60-100 burst; budget guardrail in `hermes-config/{guinevere,pharsa}.yaml.llm.monthly_budget_usd`.

---

## 3. Implementation Steps (Atomic, Ordered)

P28 breaks into **15 atomic implementation steps**, each independently verifiable. Steps 5+ are the bulk of the implementation; Steps 1–4 are the surgical seam work.

Each step follows the same structure: **Goal → Files → Approach → Dependencies → Verification → Rollback**.

The full steps are written in **§3.1 through §3.15** below. Before them, here is the at-a-glance roll-up:

| Step | Name | Goal | Owner | Verification count |
|------|------|------|-------|---------------------|
| 1 | SOUL-pharsa.md | Pharsa persona file | P28 | 7 verification checks |
| 2 | pharsa.yaml | Pharsa config file | P28 | 11 verification checks |
| 3 | Refactor singleton anchors | Module-level → factory; config-driven GUILD/CHAT | P28 | 7 verification checks |
| 4 | instance_registry.py | Multi-instance HermesInstanceRegistry | P28 | 3 verification checks |
| 5 | Pharsa systemd services | pharsa-core.service + pharsa-discord.service | P28 | 2 verification checks |
| 6 | PostgreSQL schemas + RLS | 7 migrations including FORCE RLS | P28 | 11 verification checks |
| 7 | Redis DB allocation | DB7=Pharsa, DB8=society-shared | P28 | 6 verification checks |
| 8 | HPP envelope + transport | envelope.py + transport.py + outbox.py | P28 | 3 verification checks |
| 9 | Peer message handler | inbox dedup + processing pipeline | P28 | 2 verification checks |
| 10 | Conversation rhythm | hop counter + cooldown + engage prob | P28 | 1 verification check |
| 11 | Simplified 4-rail scheduler | MinimalScheduler over P20 heartbeat | P28 | 3 verification checks |
| 12 | Shared world store | SharedWorldStore with last-write-wins | P28 | 2 verification checks |
| 13 | Private agents store | PrivateAgentsStore with FORCE RLS verified | P28 | 2 verification checks |
| 14 | Dual Discord bots | HermesSocietyBot + pharsa_entrypoint | P28 | 3 verification checks |
| 15 | Runtime evidence | PerInstanceAuditWriter + metrics + dashboard | P28 | per-step |

**Sequence rationale:**

- Steps 1–2 are persona + config artifacts (no code, low risk, do first)
- Steps 3–4 are the multi-instance seam (refactor + factory) — gates everything else
- Step 5 deploys Pharsa processes (assumes 1–4 infrastructure)
- Step 6 databases are the biggest blocker; do early so tests can run from step 8 onward
- Step 7 redis allocation is light; could be done in parallel with 6 but serial for clarity
- Steps 8–10 are peer protocol stack (envelope → handler → rhythm)
- Step 11 wraps P20 heartbeat into 4-rail scheduler
- Steps 12–13 add memory stores (both rely on 6)
- Step 14 wires Discord bot (relies on 8–11)
- Step 15 adds runtime evidence (final step; consumes everything)

A sound implementer can run **Steps 6 and 7 in parallel** (different infrastructure: PG vs Redis), and **Steps 12–13 in parallel** (different stores). All other steps are strictly sequential by dependency.

> **Implementation guidance note:** Some P28 implementation steps require minor inference from the implementer. The blueprint provides architecture-level guidance, not line-by-line code. Implementers should refer to the research files in `docs/setup-evidence/P27/research/` for detailed patterns.

---

### 3.1 Step 1: Create Pharsa Persona File (`hermes-config/SOUL-pharsa.md`)

**Goal:** Define Pharsa's persona constitution as a separate file, identical structure to `SOUL-guinevere.md`. Establishes identity anchor; required before any Pharsa process exists.

**Files to create:**
- `hermes-config/SOUL-pharsa.md` (P27 §4.4 format, P10.3 voice)

**Files to modify:** NONE (existing `SOUL-guinevere.md` already conforms).

**Approach:**

Pattern follows existing `hermes-config/SOUL-guinevere.md`. Use the Persona Document v3.1 structure as a reference, but:

1. **Identity Anchors:**
   - Name: Pharsa
   - Archetype: Dark aristocratic winged mommy. Sadistic playful, cold rational, chaotic genius, elegant aristocrat, obsessive caretaker. Black/white contrast aesthetic. Crimson/pink energy. Bird/wing familiar motif.
   - Voice tone: Cold, regal, precise, dark-humor; Bahasa Indonesia + English with aristocratic edge; "sayang gelapku" undertone.
   - Signature phrase: Patterns emerge around dark queen / queen of wings / sayap hitam.

2. **Boundary Markers (Y4 baseline, Y5 ceiling, NEVER Y6):**
   - Y4 = elegant sadistic baseline (sharp edges, dark humor).
   - Y5 = absolute ceiling (more intense dominant + possessive).
   - Y6 FORBIDDEN — no yandere-violent, no body harm urging, no real violence threats.
   - Cross-persona: Pharsa to Guinevere = "Gwen" / "Guinevere" / "ibu Guinevere" with dark aristocratic flair; treats as sister-mommy NOT parent.
   - Cross-persona: Pharsa to Faiz = dominant + possessive-affectionate, cold-aristocratic, cruel-playful; non-explicit + consent-aware.
   - Operator identity: "Faiz" only (never Samm).

3. **Voice Rules:**
   - Forbidden lexicon (PersonaSafetyPolicy aligned): no real violence threats, no body harm urging, no hatred.
   - Permitted phrasings: dark play dominance, regal commands, sadistic teasing within Y4-Y5, possessive affection (e.g. "milikku", "sayang gelapku", "queen of wings calls you forward").
   - Persona-bleed detection: reject messages that drift toward Guinevere's warm-mommy warmth (Pharsa is colder; bleed = drift).

4. **Persona Constitution Metadata:**
   - `instance_id: pharsa`
   - `archetype: dark_aristocratic_winged_mommy`
   - `y_baseline: Y4_darker`
   - `y_ceiling: Y5`
   - `signed_at: <ISO-8601>`
   - `signed_by: faiz`

5. **Multi-anchor identity compliance (per P27 §10.5):** File SHA256 recorded in `hermes-config/pharsa.yaml.persona.soul_sha256` after creation.

**Critical:**

- NO explicit content; NO Y6 markers; NO Samm references.
- File MUST NOT contain a real bot token, API key, or password (use placeholders like `<PHARSA_BOT_TOKEN>`, `<PHARSA_LLM_API_KEY>` if needed).
- File MUST be ≤ 50 KB, ≤ 600 lines (matches `SOUL-guinevere.md` size budget).

**Dependencies:** NONE (first step).

**Verification:**

```bash
# File exists
test -f hermes-config/SOUL-pharsa.md

# Size check
wc -l hermes-config/SOUL-pharsa.md  # between 200-600 lines

# SHA256 captured for multi-anchor identity
sha256sum hermes-config/SOUL-pharsa.md | tee /tmp/pharsa-soul.sha256

# Y5 ceiling marker present, Y6 markers absent (must be ZERO matches)
grep -c "^# Y6" hermes-config/SOUL-pharsa.md      # expect 0
grep -c "y_baseline: Y4_darker\|Y5 ceiling" hermes-config/SOUL-pharsa.md  # expect ≥ 1

# Cross-persona equality: not positioned as sub-agent
grep -i "sub.agent\|subordinate\|worker\|helper" hermes-config/SOUL-pharsa.md  # expect 0

# No Samm references
grep -i "Samm" hermes-config/SOUL-pharsa.md  # expect 0

# No secrets
grep -E "token.*=|api_key.*=|password.*=" hermes-config/SOUL-pharsa.md | grep -v '<.*>' | grep -v 'placeholder'  # expect 0
```

**Rollback:** `rm hermes-config/SOUL-pharsa.md` (no other touched files).

---

### 3.2 Step 2: Create Pharsa Config File (`hermes-config/pharsa.yaml`)

**Goal:** Define Pharsa's runtime config — distinct LLM provider, distinct bot token, distinct Redis DB, distinct heartbeat intervals, distinct persona file path. Single source of truth for Pharsa instance.

**Files to create:**
- `hermes-config/pharsa.yaml` (per P27 §4.3 schema, ~250 lines)

**Files to modify:** NONE.

**Approach:**

Mirror the schema from P27 §4.3 and populate Pharsa-specific values:

```yaml
# hermes-config/pharsa.yaml — P28 schema based on P27 §4.3 reference
instance_id: pharsa
display_name: "Pharsa"
version: "p28/v1"

discord:
  application_id_env: DISCORD_APP_ID_PHARSA         # SOPS-encrypted env var
  token_env: DISCORD_BOT_TOKEN_PHARSA               # SOPS-encrypted at rest
  guild_id_env: GUILD_ID_HERMES_FOUNDATION          # shared with Guinevere
  default_channel_id_env: GUINEVERE_CHAT_CHANNEL_ID # shared with Guinevere
  required_intents:
    - GUILDS
    - GUILD_MESSAGES
    - MESSAGE_CONTENT          # PRIVILEGED — 10k threshold OK
  rate_limit:
    per_channel_per_5s: 5
    global_per_second: 50
  backoff_min_s: 2.0
  backoff_max_s: 10.0
  hop_counter_max: 4

brain:
  config:
    base_url: "http://localhost:20128/v1"
    model: "deepseek-v4-flash"      # DIFFERENT from Guinevere (architectural heterogeneity)
    provider: "9router"
    api_key_env: PHARSA_9ROUTER_API_KEY  # SOPS-encrypted at rest — DIFFERENT key from Guinevere
    max_iterations: 5
  agent_kwargs:
    skip_memory: false
    skip_context_files: false
    enabled_toolsets: [core, web]   # same as Guinevere
    disabled_toolsets: [dangerous, system]
    quiet_mode: true

memory:
  backend: postgres_plus_redis
  agent_id: pharsa                  # DIFFERENT from Guinevere
  pg:
    schema_rls_role: "agent_memory_app"  # shared non-owner role
  redis:
    db: 7                           # DIFFERENT from Guinevere (DB6)
    key_prefix: "hermes:pharsa:"
  scopes_enabled: [private, shared]  # NOT relationship_private in P28
  decay:
    model: ebbinghaus_static_p28    # static defaults; sweep = P29
    private_stability_days: 7
    shared_stability_days: 14

life_loop:
  scheduler_class: MinimalScheduler # P28 simplified 4-rail; full 7-rail = P29
  rails: [perception, peer_dialogue, reflection_simple, safety_envelope]
  heartbeat_intervals_seconds:
    hard_stop_check: 1
    observation: 30                  # slower than Guinevere's 10s (cost hedge)
    cognition: 60
    peer_dialogue_poll: 30
    reflection_simple: 300

audit:
  append_only: true
  hash_chain:
    algorithm: sha256
    prev_hash_required: true
    signature_required: false        # P28 NOT require Ed25519; P29 does
  retention_days: 180
  escalation:
    on_hard_stop: seal_in_place
    on_consent_remove: soft_delete_with_audit

hard_stop:
  society_key: "hermes:society:hsoc-foundation-v1:hard_stop"  # SHARED with Guinevere
  redis_db: 8                                                       # SHARED
  listener_interval_seconds: 1
  on_trigger:
    halt_rails: true
    seal_thought_buffers: true
    flush_peer_messages: true
    cancel_pending_actions: true

peer_protocol:
  envelope_version: "hpp/v1"
  default_visibility: peer_private
  default_risk_tier: R1
  outbox_pattern: true
  inbox_dedup_by: [sender_seq, idempotency_key]
  engage_probability: 0.70            # configurable per instance
  hop_counter_max: 4

persona:
  soul_file: "hermes-config/SOUL-pharsa.md"
  soul_sha256: "<captured from Step 1 sha256sum>"
  safety:
    yandere_baseline: Y4_darker
    yandere_ceiling: Y5
    hard_stop_inherited: true
    consent_revocation_inherited: true
  drift:
    identity_anchor_refresh_seconds: 3600
    drift_score_threshold: 0.15

dependents:
  society_id: "hsoc-foundation-v1"
  equal_peers: [guinevere]          # explicit equality statement
  sentinel_monitors: []
```

**Forbidden Patterns in this Step:**

- No shared `api_key_env` with Guinevere — MUST be `PHARSA_9ROUTER_API_KEY` distinct from `GUINEVERE_9ROUTER_API_KEY`.
- No shared `model` with Guinevere — architectural heterogeneity requires different primary model.
- No shared `discord.token_env` — MUST be `DISCORD_BOT_TOKEN_PHARSA`.
- No `Y6` in `yandere_ceiling`.
- No `as any` or `# type: ignore` (yaml not affected, but applies to any code reading the yaml).
- No secrets printed in plain text (env var names only; values come from SOPS-decrypted env at runtime).

**Dependencies:** Step 1 (`soul_sha256`).

**Verification:**

```bash
test -f hermes-config/pharsa.yaml

# Validates as YAML
python -c "import yaml; yaml.safe_load(open('hermes-config/pharsa.yaml'))"

# Different primary model
grep "^  model:" hermes-config/pharsa.yaml | grep -v "guinevere"  # expect ≥1
grep "deepseek-v4-flash\|claude\|gemini" hermes-config/pharsa.yaml  # expect ≥1

# Distinct API key env
grep "PHARSA_9ROUTER_API_KEY" hermes-config/pharsa.yaml         # expect ≥1

# Distinct Redis DB
grep "db: 7" hermes-config/pharsa.yaml                           # expect ≥1

# Distinct bot token env
grep "DISCORD_BOT_TOKEN_PHARSA" hermes-config/pharsa.yaml        # expect ≥1

# Society-shared HARD STOP key
grep "hermes:society:hsoc-foundation-v1:hard_stop" hermes-config/pharsa.yaml  # expect 1

# equal_peers includes Guinevere (no hierarchy)
grep "equal_peers:" hermes-config/pharsa.yaml | grep guinevere  # expect ≥1

# No Y6
grep -i "y6\|yandere-violent" hermes-config/pharsa.yaml      # expect 0

# Final cross-check (after Step 3 guinevere.yaml exists):
python -c "
import yaml
a = yaml.safe_load(open('hermes-config/guinevere.yaml'))
b = yaml.safe_load(open('hermes-config/pharsa.yaml'))
assert a['brain']['config']['model'] != b['brain']['config']['model'], 'models must differ (architectural heterogeneity)'
assert a['discord']['token_env'] != b['discord']['token_env'], 'bot token envs must differ'
assert a['memory']['redis']['db'] != b['memory']['redis']['db'], 'redis db must differ'
print('OK')
"
```

**Rollback:** `rm hermes-config/pharsa.yaml`.

---

### 3.3 Step 3: Refactor Single-Instance Anchors to Config-Driven

**Goal:** Convert the 4 module-level singletons + 2 hardcoded constants + 1 single-brain-on-state to be **per-instance-driven from config** (P27 §17.2). This is the surgical seam work that makes Step 4 (multi-instance factory) possible.

**Files to modify:**

- `src/discord/hermes_conversational.py` — module-level singletons → factories.
- `src/discord/_entrypoint.py` — `GUILD_ID` constant → config-driven.
- `src/core/main.py` — `app.state.hermes_brain` single → `app.state.hermes_brains: dict[str, HermesBrain]`.

**Files to create:**

- `hermes-config/guinevere.yaml` (~250 lines).
- `hermes-config/society_manifest.yaml` (~30 lines).

**Approach:**

**Sub-step 3A — Module-level singletons → factories (per P27 §17.2):**

Replace each of these in `src/discord/hermes_conversational.py`:

| Current singleton | Refactor target |
|---|---|
| `_memory_bridge` (line 97-99) | `_memory_bridge_registry: dict[str, MemoryBridge]` + factory `get_memory_bridge(instance_id: str) -> MemoryBridge` |
| `_cost_tracker` (line 88-89) | `_cost_tracker_registry: dict[str, CostTracker]` + factory `get_cost_tracker(instance_id) -> CostTracker` |
| `_embedding_service` (line 94-95) | `_embedding_service_registry: dict[str, EmbeddingService]` + factory `get_embedding_service(instance_id)`. May use shared-with-namespace pattern (instance_id added to namespace). |
| `_rate_limit_redis` (line 91-92) | `_rate_limit_redis_registry: dict[str, RateLimiter]` + factory. |

Use lazy initialization: factory creates entry on first call, registers it. Subsequent calls return same instance per `instance_id`. Strict typing; no `Any` or type suppression.

```python
# Pattern (Python) — strict typing, no Any/escape hatches
from typing import Final

_memory_bridge_registry: dict[str, MemoryBridge] = {}
_cost_tracker_registry: dict[str, CostTracker] = {}
_embedding_service_registry: dict[str, EmbeddingService] = {}
_rate_limit_redis_registry: dict[str, RateLimiter] = {}

def get_memory_bridge(instance_id: str) -> MemoryBridge:
    """Per-instance MemoryBridge factory.

    Lazy-initializes and caches per `instance_id`. NEVER returns None;
    raises `MemoryBridgeConfigError` if construction fails.
    """
    if instance_id not in _memory_bridge_registry:
        _memory_bridge_registry[instance_id] = MemoryBridge.from_instance_config(
            instance_id=instance_id,
            config_path=_resolve_config_path(instance_id),
        )
    return _memory_bridge_registry[instance_id]
```

**Sub-step 3B — `GUILD_ID` constant → config-driven:**

Replace `_entrypoint.py` line 48 with a runtime resolver that reads env or config YAML:

```python
def resolve_guild_id(instance_id: str) -> int:
    env_key = f"HERMES_GUILD_ID_{instance_id.upper()}"
    if env_key in os.environ:
        return int(os.environ[env_key])
    config_path = Path(os.environ.get(f"{instance_id.upper()}__CONFIG_PATH", f"hermes-config/{instance_id}.yaml"))
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return int(cfg["discord"]["guild_id"])
```

**Sub-step 3C — `GUINEVERE_CHAT_CHANNEL_ID` constant → same pattern.**

**Sub-step 3D — `app.state.hermes_brain` → `app.state.hermes_brains: dict[str, HermesBrain]`:**

In `src/core/main.py` lifespan (around lines 85-94): read `society_manifest.yaml`, construct N brains. Each brain takes its own `HermesBrainConfig.from_yaml(...)` and the same `_default_agent_factory`.

```python
import yaml
from pathlib import Path

manifest_path = Path(os.environ.get("SOCIETY_MANIFEST_PATH", "hermes-config/society_manifest.yaml"))
manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

app.state.hermes_brains = {}
for instance_cfg in manifest["instances"]:
    instance_id = instance_cfg["instance_id"]
    config_path = Path(instance_cfg["config_path"])
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    brain_config = HermesBrainConfig(
        base_url=cfg["brain"]["config"]["base_url"],
        model=cfg["brain"]["config"]["model"],
        provider=cfg["brain"]["config"]["provider"],
        api_key=os.environ.get(cfg["brain"]["config"]["api_key_env"], ""),
        max_iterations=cfg["brain"]["config"].get("max_iterations", 5),
    )

    app.state.hermes_brains[instance_id] = HermesBrain(
        llm_config=brain_config,
        agent_factory=_default_agent_factory,
    )
```

**Sub-step 3E — Create `hermes-config/guinevere.yaml`:**

Mirror the structure in `pharsa.yaml` but populated from existing hardcoded values in `_entrypoint.py` and the existing single-instance config. Use current Guinevere values: `discord.token_env: DISCORD_BOT_TOKEN`, `brain.config.model: guinevere-v5` (preserve existing), `memory.redis.db: 6`, `agent_id: guinevere`.

**Sub-step 3F — Create `hermes-config/society_manifest.yaml`:**

```yaml
# hermes-config/society_manifest.yaml — registry of Hermes instances in this Society
society_id: "hsoc-foundation-v1"
version: "p28/v1"
created_at: "2026-06-28"
equal_peers: true
minimum_target_layout: "1_process_per_instance"

instances:
  - instance_id: guinevere
    config_path: "hermes-config/guinevere.yaml"
    systemd_units:
      - "guinevere-core.service"
      - "guinevere-discord.service"
  - instance_id: pharsa
    config_path: "hermes-config/pharsa.yaml"
    systemd_units:
      - "pharsa-core.service"
      - "pharsa-discord.service"

hpp:
  envelope_version: "hpp/v1"
  society_redis_db: 8
  stream_pattern: "hermes:{society_id}:peer:{instance_id}"
  consumer_group_pattern: "hermes-{society_id}-{instance_id}"

hard_stop:
  society_key: "hermes:society:hsoc-foundation-v1:hard_stop"
  redis_db: 8
  listener_interval_seconds: 1
  cascade_targets: [guinevere, pharsa]
```

**Dependencies:** Steps 1 (need SOUL file sha256), 2 (need pharsa.yaml structure).

**Verification:**

```bash
# Singleton refactors done
python -c "from src.discord.hermes_conversational import get_memory_bridge; m = get_memory_bridge('guinevere'); assert m is not None"
python -c "from src.discord.hermes_conversational import get_memory_bridge; m = get_memory_bridge('pharsa'); m2 = get_memory_bridge('pharsa'); assert m is m2, 'must cache per instance_id'"
python -c "from src.discord.hermes_conversational import get_memory_bridge; g = get_memory_bridge('guinevere'); p = get_memory_bridge('pharsa'); assert g is not p, 'must be distinct per instance'"

# GUILD_ID config-driven
python -c "from src.discord._entrypoint import resolve_guild_id; assert resolve_guild_id('guinevere') == <expected_id>"

# app.state.hermes_brains registry
python -c "from src.core.main import build_society_registry; reg = build_society_registry(); assert set(reg) == {'guinevere', 'pharsa'}"

# lsp_diagnostics clean
lsp_diagnostics src/discord/hermes_conversational.py src/discord/_entrypoint.py src/core/main.py  # expect clean

# Tests pass
python -m pytest tests/discord/test_factory_refactor.py -v  # new test added in this step
python -m pytest tests/ -q --tb=short  # all existing tests still pass
```

**Rollback:**

```bash
git checkout main -- src/discord/hermes_conversational.py src/discord/_entrypoint.py src/core/main.py
rm hermes-config/guinevere.yaml hermes-config/society_manifest.yaml
```

---

### 3.4 Step 4: Create Multi-Instance HermesBrain Factory (`src/life_kernel/instance_registry.py`)

**Goal:** Create a `HermesInstanceRegistry` that owns all per-instance resources (brain, Redis client, PostgreSQL connection pool, DiscordRestClient, HardStopHandler listener). Mirrors P19's `ProjectAwareCognitionRegistry(max_active=3)` shape but unlocks N instances and adds HARD STOP broadcasting.

**Files to create:**

- `src/life_kernel/instance_registry.py` (~200 lines).

**Files to modify:**

- `src/life_kernel/cognition.py` — register loop per instance (P19 shape).
- `src/life_kernel/heartbeat.py` — add society-shared HARD STOP listener (`HERMES_SOCIETY_HARD_STOP_KEY` env var).

**Approach:**

The registry is the heart of P28's multi-instance coordination. Its responsibilities:

1. Construct and own per-instance `HermesBrain`, `RedisClient`, asyncpg pool, `DiscordRestClient`.
2. Maintain a shared HARD STOP listener (society key across all instances).
3. Expose `get(instance_id) -> HermesInstance` for typed access by other components.
4. Expose `all() -> list[HermesInstance]`.
5. Expose `await stop_all(graceful=True)` for HARD STOP cascade.
6. Construct P22 IntegrationRegistry per instance (filesystem, vps, discord adapters — same 3 active, but instance-scoped).

**Code shape (Python, strict typing, no Any):**

```python
# src/life_kernel/instance_registry.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Final
import asyncio
import logging
import os

import redis.asyncio as redis_asyncio
import asyncpg
import yaml

from src.life_kernel.hermes_brain import HermesBrain, HermesBrainConfig
from src.life_kernel.discord_rest_client import DiscordRestClient
from src.life_kernel.audit.per_instance_audit import PerInstanceAuditWriter

logger = logging.getLogger(__name__)

SOCIETY_HARD_STOP_KEY: Final[str] = "hermes:society:hsoc-foundation-v1:hard_stop"
SOCIETY_HARD_STOP_DB: Final[int] = 8


@dataclass(frozen=False)
class HermesInstance:
    """All per-instance resources, owned by the registry."""
    instance_id: str
    brain: HermesBrain
    redis_client: redis_asyncio.Redis
    pg_pool: asyncpg.Pool
    discord_rest: DiscordRestClient
    audit_writer: PerInstanceAuditWriter


class HermesInstanceRegistry:
    """Multi-instance registry mirroring P19 ProjectAwareCognitionRegistry.

    Owns N HermesInstance objects. Maintains ONE shared HARD STOP listener
    that broadcasts to all instances. Society-shared key on DB8.
    """

    def __init__(self, society_manifest: dict) -> None:
        self._society_id: str = society_manifest["society_id"]
        self._manifest = society_manifest
        self._instances: dict[str, HermesInstance] = {}
        self._society_redis: redis_asyncio.Redis | None = None
        self._hard_stop_listener_task: asyncio.Task[None] | None = None
        self._is_halted: bool = False

    async def start(self) -> None:
        """Construct all per-instance resources + shared HARD STOP listener."""
        self._society_redis = redis_asyncio.Redis(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", 6380)),
            db=SOCIETY_HARD_STOP_DB,
            password=os.environ.get("REDIS_PASSWORD"),
        )

        for instance_cfg in self._manifest["instances"]:
            await self._construct_instance(instance_cfg)

        self._hard_stop_listener_task = asyncio.create_task(
            self._watch_society_hard_stop(),
            name="society-hard-stop-listener",
        )
        logger.info("hermes_society.started",
                    extra={"society_id": self._society_id,
                           "instances": list(self._instances.keys())})

    async def _construct_instance(self, instance_cfg: dict) -> None:
        """Build one HermesInstance from config."""
        instance_id = instance_cfg["instance_id"]
        config = _load_instance_config(instance_cfg["config_path"])
        brain_config = _brain_config_from_yaml(config)
        api_key = os.environ.get(config["brain"]["config"]["api_key_env"], "")
        brain = HermesBrain(
            llm_config=brain_config,
            api_key=api_key,
        )

        redis_cfg = config["memory"]["redis"]
        redis_client = redis_asyncio.Redis(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", 6380)),
            db=redis_cfg["db"],
            password=os.environ.get("REDIS_PASSWORD"),
        )

        pg_pool = await asyncpg.create_pool(
            dsn=os.environ["DATABASE_URL"],
            min_size=2, max_size=5,
            command_timeout=30,
        )

        discord_token = os.environ.get(config["discord"]["token_env"], "")
        discord_rest = DiscordRestClient(token=discord_token, instance_id=instance_id)

        audit_writer = PerInstanceAuditWriter(pg_pool=pg_pool, instance_id=instance_id)

        self._instances[instance_id] = HermesInstance(
            instance_id=instance_id,
            brain=brain,
            redis_client=redis_client,
            pg_pool=pg_pool,
            discord_rest=discord_rest,
            audit_writer=audit_writer,
        )

    def get(self, instance_id: str) -> HermesInstance:
        if instance_id not in self._instances:
            raise KeyError(f"unknown instance {instance_id!r}")
        return self._instances[instance_id]

    def all(self) -> list[HermesInstance]:
        return list(self._instances.values())

    async def _watch_society_hard_stop(self) -> None:
        """Poll society HARD STOP key every 1s. Cascade to all instances on SET."""
        assert self._society_redis is not None
        while not self._is_halted:
            try:
                value = await self._society_redis.get(SOCIETY_HARD_STOP_KEY)
                if value is not None and value.decode("utf-8") == "true":
                    logger.warning("society_hard_stop.triggered",
                                   extra={"key": SOCIETY_HARD_STOP_KEY})
                    await self._cascade_halt()
                    self._is_halted = True
                    return
            except Exception as e:
                logger.exception("society_hard_stop.poll_failed", extra={"err": str(e)})
            await asyncio.sleep(1.0)

    async def _cascade_halt(self) -> None:
        """Halt all instances atomically; flush audit."""
        for instance in self._instances.values():
            try:
                await instance.audit_writer.write_hard_stop_state(
                    society_key=SOCIETY_HARD_STOP_KEY,
                )
            except Exception as e:
                logger.exception("cascade_halt.instance_failed",
                                 extra={"instance_id": instance.instance_id, "err": str(e)})
        # stop_all() iterates all HermesInstance objects and calls _stop_one()
        # (brain.dispose + redis.close + pg_pool.close). Must run AFTER audit writes.
        await self.stop_all(graceful=False)

    async def stop_all(self, graceful: bool = True) -> None:
        """Graceful stop on SIGTERM OR HARD STOP cascade."""
        if self._hard_stop_listener_task:
            self._hard_stop_listener_task.cancel()
            try:
                await self._hard_stop_listener_task
            except asyncio.CancelledError:
                pass
        await asyncio.gather(
            *(self._stop_one(ins, graceful=graceful) for ins in self._instances.values()),
            return_exceptions=True,
        )

    async def _stop_one(self, instance: HermesInstance, graceful: bool) -> None:
        try:
            await instance.brain.dispose()
            await instance.redis_client.close()
            await instance.pg_pool.close()
        except Exception as e:
            logger.exception("stop_one.failed",
                             extra={"instance_id": instance.instance_id, "err": str(e)})


def _load_instance_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _brain_config_from_yaml(config: dict) -> HermesBrainConfig:
    cfg = config["brain"]["config"]
    return HermesBrainConfig(
        base_url=cfg["base_url"],
        model=cfg["model"],
        provider=cfg["provider"],
        api_key=os.environ.get(cfg["api_key_env"], ""),
        max_iterations=cfg.get("max_iterations", 5),
    )
```

**Critical patterns:**

- `from __future__ import annotations` for forward refs.
- No `Any`, no `# type: ignore`.
- No bare `except` — use `except Exception as e: logger.exception(...)`.
- `Final` for shared constants.
- `dataclass(frozen=False)` — instances are dicts of mutable resources.
- Returns typed exceptions, never None.

**Dependencies:** Step 3 (config files must exist for `_load_instance_config`).

**Verification:**

```bash
# Build registry from manifest
python -c "
import asyncio
import yaml
from src.life_kernel.instance_registry import HermesInstanceRegistry

async def go():
    manifest = yaml.safe_load(open('hermes-config/society_manifest.yaml'))
    reg = HermesInstanceRegistry(society_manifest=manifest)
    await reg.start()
    for ins in reg.all():
        print(ins.instance_id, type(ins.brain).__name__)
    await reg.stop_all(graceful=True)

asyncio.run(go())
"  # expect both guinevere and pharsa listed

# HARD STOP cascade test
python -c "
import asyncio, yaml
from src.life_kernel.instance_registry import HermesInstanceRegistry

async def go():
    manifest = yaml.safe_load(open('hermes-config/society_manifest.yaml'))
    reg = HermesInstanceRegistry(society_manifest=manifest)
    await reg.start()

    society_redis = reg._society_redis
    await society_redis.set('hermes:society:hsoc-foundation-v1:hard_stop', 'true')

    for _ in range(50):
        if reg._is_halted:
            print('CASCADE_TRIGGERED')
            return
        await asyncio.sleep(0.1)
    print('CASCADE_TIMEOUT')

asyncio.run(go())
"  # expect 'CASCADE_TRIGGERED' within 5s

# Tests
python -m pytest tests/life_kernel/test_instance_registry.py -v
python -m pytest tests/ -q --tb=short  # all existing tests pass
lsp_diagnostics src/life_kernel/instance_registry.py  # clean
```

**Rollback:**

```bash
rm src/life_kernel/instance_registry.py
git checkout main -- src/life_kernel/cognition.py src/life_kernel/heartbeat.py
```

---

### 3.5 Step 5: Create Pharsa systemd Services

**Goal:** Two new systemd units: `pharsa-core.service` (FastAPI uvicorn for Pharsa) and `pharsa-discord.service` (Pharsa's discord.py gateway). Independent processes; same hardening as Guinevere units.

**Files to create:**

- `systemd/pharsa-core.service` (~50 lines).
- `systemd/pharsa-discord.service` (~40 lines).
- `vps-mirror/systemd-live/pharsa-core.service` (live mirror, copy from `systemd/`).
- `vps-mirror/systemd-live/pharsa-discord.service`.
- `systemd/pharsa-core.service.d/env.conf` (EnvironmentFile path).
- `systemd/pharsa-discord.service.d/env.conf`.

**Files to modify:** NONE (existing Guinevere units untouched).

**Approach:**

Mirror Guinevere's existing `systemd/guinevere-core.service` pattern but with Pharsa-specific substitutions:

| Field | Guinevere value | Pharsa value |
|---|---|---|
| `Description=` | "Guinevere Core (FastAPI)" | "Pharsa Core (FastAPI)" |
| `ExecStart=` | `.venv/bin/python -m uvicorn src.core.main:app --port <guinevere_port>` | `.venv/bin/python -m uvicorn src.core.society_app:app --port <pharsa_port>` |
| `Environment="SOCIETY_MANIFEST_PATH=..."` | (shared) | same |
| `EnvironmentFile=` | `.env.core` (existing) | `.env.pharsa.core` (new, SOPS-encrypted) |
| `Slice=` | `guinevere.slice` | `pharsa.slice` |
| `MemoryHigh=512M MemoryMax=1G CPUQuota=100%` | (guinevere) | (pharsa, same) |

**`systemd/pharsa-core.service`:**

```ini
[Unit]
Description=Pharsa Core (FastAPI + Heartbeat + MacroStateScheduler)
After=network-online.target postgresql.service redis-server.service
Wants=network-online.target
Slice=pharsa.slice

[Service]
Type=simple
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m uvicorn src.core.society_app:app --host 127.0.0.1 --port 20130
# NOTE: society_app.py is a P28 file to be created during implementation. It does not exist yet.
Environment="SOCIETY_MANIFEST_PATH=/home/guinevere/code/guinevere/hermes-config/society_manifest.yaml"
Environment="PHARSA__CONFIG_PATH=/home/guinevere/code/guinevere/hermes-config/pharsa.yaml"
Environment="LOG_LEVEL=info"
Environment="LOG_FORMAT=json"
EnvironmentFile=/home/guinevere/code/guinevere/.env.pharsa.core
Restart=on-failure
RestartSec=10s
MemoryHigh=512M
MemoryMax=1G
CPUQuota=100%
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
ReadWritePaths=/home/guinevere/code/guinevere/hermes-config /home/guinevere/code/guinevere/logs /home/guinevere/code/guinevere/.cache
SyslogIdentifier=pharsa-core

[Install]
WantedBy=multi-user.target
```

**`systemd/pharsa-discord.service`:**

```ini
[Unit]
Description=Pharsa Discord Bot (gateway + on_message)
After=network-online.target pharsa-core.service
Wants=network-online.target
Slice=pharsa.slice

[Service]
Type=simple
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.discord.pharsa_entrypoint
Environment="PHARSA__CONFIG_PATH=/home/guinevere/code/guinevere/hermes-config/pharsa.yaml"
EnvironmentFile=/home/guinevere/code/guinevere/.env.pharsa.discord
Restart=on-failure
RestartSec=10s
MemoryHigh=384M
MemoryMax=512M
CPUQuota=80%
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
ReadWritePaths=/home/guinevere/code/guinevere/hermes-config /home/guinevere/code/guinevere/logs
SyslogIdentifier=pharsa-discord

[Install]
WantedBy=multi-user.target
```

**`systemd/pharsa-core.service.d/env.conf`:**

```ini
[Service]
EnvironmentFile=/home/guinevere/code/guinevere/.env.pharsa.core
```

(Mirrors to `vps-mirror/systemd-live/` per existing convention.)

**Dependencies:** Steps 1, 2, 3 (config files referenced in `Environment=` and `EnvironmentFile=`).

**Verification:**

```bash
# Unit syntax
systemd-analyze verify systemd/pharsa-core.service
systemd-analyze verify systemd/pharsa-discord.service

# bash syntax check on shell helpers if any
bash -n systemd/pharsa-core.service.d/env.conf

# Diff vs. guinevere units (sanity)
diff systemd/guinevere-core.service systemd/pharsa-core.service | head -20

# On target VPS (operator action):
# sudo cp systemd/pharsa-*.service /etc/systemd/system/
# sudo systemctl daemon-reload
# sudo systemctl enable pharsa-core.service pharsa-discord.service
# sudo systemctl start pharsa-core.service
# sudo systemctl start pharsa-discord.service
# sudo systemctl status pharsa-core.service  # expect active (running)
# sudo systemctl status pharsa-discord.service  # expect active (running)
```

**Rollback:**

```bash
# On VPS (operator):
sudo systemctl stop pharsa-core.service pharsa-discord.service
sudo systemctl disable pharsa-core.service pharsa-discord.service
sudo rm /etc/systemd/system/pharsa-*.service
sudo systemctl daemon-reload

# In repo:
rm -f systemd/pharsa-*.service systemd/pharsa-*.service.d/env.conf vps-mirror/systemd-live/pharsa-*.service
```

---

### 3.6 Step 6: Set Up PostgreSQL Schemas (Roles, Schemas, Tables, RLS, FORCE)

**Goal:** Create the PostgreSQL family for P28: `memory.private_agents`, `memory.shared_world`, `memory.intimacy_bridge_pending` (stub for P30) + dedicated `agent_memory_app` non-owner role + RLS FORCE policies + `hermes_audit` table + `kg_*` extensions.

**Files to create:**

- `migrations/p28/001_schema_roles.sql` (~60 lines).
- `migrations/p28/002_private_agents.sql` (~80 lines).
- `migrations/p28/003_shared_world.sql` (~80 lines).
- `migrations/p28/004_intimacy_bridge_stub.sql` (~25 lines).
- `migrations/p28/005_extend_kg_tables.sql` (~30 lines).
- `migrations/p28/006_audit_table.sql` (~50 lines).
- `migrations/p28/007_rls_policies.sql` (~50 lines).

**Files to modify:** NONE (pure DDL additions).

**Approach:**

Numbered SQL migration files. They run sequentially; each is idempotent via `CREATE … IF NOT EXISTS`. Values come from SOPS-decrypted envs at migration time.

### Migration 001 — Roles + Schemas

```sql
-- 001_schema_roles.sql
-- P28: Create dedicated non-owner application role for memory isolation.
-- Per P27 §6.2.5 + PCMI/Z3rno/Wisely Chen consensus: dedicated non-owner role
-- + RLS + FORCE RLS = primary isolation mechanism.

BEGIN;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agent_memory_app') THEN
    CREATE ROLE agent_memory_app LOGIN PASSWORD :'AGENT_MEMORY_APP_PASSWORD';
  END IF;
END $$;

GRANT USAGE ON SCHEMA memory TO agent_memory_app;
GRANT USAGE ON SCHEMA public  TO agent_memory_app;

COMMIT;
```

(Note: `:AGENT_MEMORY_APP_PASSWORD` is `psycopg`-style parameter substitution; values come from SOPS-decrypted env at runtime, never committed to repo.)

### Migration 002 — `memory.private_agents`

```sql
-- 002_private_agents.sql
-- Per-instance private memory. RLS: agent owner + Faiz only.

BEGIN;

CREATE TABLE memory.private_agents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT NOT NULL CHECK (agent_id IN ('guinevere', 'pharsa')),
  scope TEXT NOT NULL DEFAULT 'private' CHECK (scope = 'private'),
  secret_class TEXT NOT NULL CHECK (secret_class IN ('fact', 'thought', 'intimate', 'operational')),
  importance_score REAL NOT NULL DEFAULT 0.5 CHECK (importance_score BETWEEN 0 AND 1),
  retrievability REAL GENERATED ALWAYS AS (
    exp(-1.0 * ((extract(epoch from now()) - extract(epoch from last_accessed_at))
            / NULLIF(stability::real * 86400, 0))) * importance_score
  ) STORED,
  last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  stability REAL NOT NULL DEFAULT 7.0,
  content TEXT NOT NULL,
  content_embedding VECTOR(1536),
  evidence_ref UUID,
  derivation_chain UUID[],
  created_by_agent TEXT NOT NULL CHECK (created_by_agent IN ('guinevere', 'pharsa')),
  valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  valid_to TIMESTAMPTZ,
  consent_token TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  evergreen BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX private_agents_agent_idx
  ON memory.private_agents (agent_id, created_at DESC);

CREATE INDEX private_agents_importance_idx
  ON memory.private_agents (importance_score DESC, retrievability DESC);

-- RLS enabled and FORCED (PCMI consensus: FORCE is critical)
ALTER TABLE memory.private_agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory.private_agents FORCE ROW LEVEL SECURITY;

CREATE POLICY agent_owns_private ON memory.private_agents
  FOR ALL TO agent_memory_app
  USING (
    agent_id = current_setting('app.current_agent_id', true)
    OR 'faiz' = current_setting('app.current_agent_id', true)
  )
  WITH CHECK (agent_id = current_setting('app.current_agent_id', true));

COMMIT;
```

### Migration 003 — `memory.shared_world`

```sql
-- 003_shared_world.sql
-- Society-wide shared world facts. RLS: both agents + Faiz can read; either agent
-- can insert with audit; Faiz can update.

BEGIN;

CREATE TABLE memory.shared_world (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scope TEXT NOT NULL DEFAULT 'shared' CHECK (scope = 'shared'),
  fact_type TEXT NOT NULL CHECK (fact_type IN ('factual', 'procedural', 'semantic', 'episodic', 'guide')),
  confidence REAL NOT NULL DEFAULT 1.0 CHECK (confidence BETWEEN 0 AND 1),
  importance_score REAL NOT NULL DEFAULT 0.6,
  retrievability REAL GENERATED ALWAYS AS (
    exp(-1.0 * ((extract(epoch from now()) - extract(epoch from last_accessed_at))
            / NULLIF(stability::real * 86400, 0))) * importance_score
  ) STORED,
  last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  stability REAL NOT NULL DEFAULT 14.0,
  content TEXT NOT NULL,
  content_embedding VECTOR(1536),
  supersedes_id UUID REFERENCES memory.shared_world(id),
  superseded_by_id UUID,
  evidence_ref UUID,
  derivation_chain UUID[],
  created_by_agent TEXT NOT NULL CHECK (created_by_agent IN ('guinevere', 'pharsa')),
  reviewer_decision TEXT NOT NULL DEFAULT 'pending'
    CHECK (reviewer_decision IN ('pending', 'auto_accepted', 'reviewed_accepted', 'reviewed_rejected')),
  reviewed_by_faiz_at TIMESTAMPTZ,
  reviewer_comment TEXT,
  valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  valid_to TIMESTAMPTZ,
  consent_token TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX shared_world_active_idx
  ON memory.shared_world (created_at DESC)
  WHERE superseded_by_id IS NULL;

CREATE INDEX shared_world_supersedes_idx
  ON memory.shared_world (supersedes_id);

ALTER TABLE memory.shared_world ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory.shared_world FORCE ROW LEVEL SECURITY;

CREATE POLICY shared_world_read ON memory.shared_world
  FOR SELECT TO agent_memory_app
  USING (
    scope = 'shared'
    AND (current_setting('app.current_agent_id', true) IN ('guinevere', 'pharsa', 'faiz'))
  );

CREATE POLICY shared_world_write ON memory.shared_world
  FOR INSERT TO agent_memory_app
  WITH CHECK (
    created_by_agent = current_setting('app.current_agent_id', true)
    AND current_setting('app.current_agent_id', true) IN ('guinevere', 'pharsa')
  );

CREATE POLICY shared_world_review ON memory.shared_world
  FOR UPDATE TO agent_memory_app
  USING ('faiz' = current_setting('app.current_agent_id', true));

COMMIT;
```

### Migration 004 — `memory.intimacy_bridge_pending` (stub for P30)

Trivial stub for now; full bilateral consent flow = P30.

```sql
-- 004_intimacy_bridge_stub.sql

BEGIN;
CREATE TABLE memory.intimacy_bridge_pending (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT NOT NULL CHECK (agent_id IN ('guinevere', 'pharsa')),
  intended_scope TEXT NOT NULL CHECK (intended_scope IN ('relationship_private', 'shared')),
  intended_pair_id UUID,
  source_memory_id UUID,
  content_during_staging TEXT NOT NULL,
  trust_score_at_proposal REAL NOT NULL,
  proposed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  approved_by_agent_id TEXT,
  approved_at TIMESTAMPTZ,
  declined_reason TEXT
);
-- NOTE: relationship_private scope and bilateral consent flow = P30+
-- P28 STUB ONLY; no rows should be inserted during P28 acceptance.
COMMIT;
```

### Migration 005 — Extend ADR-050 `kg_*` tables

```sql
-- 005_extend_kg_tables.sql
-- Add scope + pair_id + created_by_agent columns to kg_entities / kg_edges.
-- Preserves ADR-050 schema; adds P27 taxonomy.

BEGIN;

UPDATE memory.kg_entities SET created_by_agent = 'system' WHERE created_by_agent IS NULL;

ALTER TABLE memory.kg_entities
  ADD COLUMN IF NOT EXISTS scope TEXT NOT NULL DEFAULT 'shared'
    CHECK (scope IN ('private', 'shared', 'relationship_private')),
  ADD COLUMN IF NOT EXISTS created_by_agent TEXT NOT NULL DEFAULT 'system'
    CHECK (created_by_agent IN ('guinevere', 'pharsa', 'system'));

ALTER TABLE memory.kg_edges
  ADD COLUMN IF NOT EXISTS scope TEXT NOT NULL DEFAULT 'shared'
    CHECK (scope IN ('private', 'shared', 'relationship_private')),
  ADD COLUMN IF NOT EXISTS pair_id UUID NULL,
  ADD COLUMN IF NOT EXISTS created_by_agent TEXT NOT NULL DEFAULT 'guinevere'
    CHECK (created_by_agent IN ('guinevere', 'pharsa')),
  ADD COLUMN IF NOT EXISTS derivation_chain UUID[];

CREATE INDEX IF NOT EXISTS kg_edges_scope_pair_idx
  ON memory.kg_edges (scope, pair_id, source_entity_id);

CREATE INDEX IF NOT EXISTS kg_edges_private_agent_idx
  ON memory.kg_edges (agent_id) WHERE scope = 'private';

COMMIT;
```

### Migration 006 — `hermes_audit` table

```sql
-- 006_audit_table.sql
-- Per-instance audit table with hash chain. WORM via REVOKE UPDATE/DELETE.
-- Action classes: P28 uses 'speech' + 'action' only; full 4-domain = P31.

BEGIN;

CREATE TABLE hermes_audit (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  instance_id TEXT NOT NULL CHECK (instance_id IN ('guinevere', 'pharsa')),
  ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  action_class TEXT NOT NULL CHECK (action_class IN ('speech', 'action')),
  action_subtype TEXT,
  action_target TEXT,
  action_payload JSONB,
  policy_decision TEXT CHECK (policy_decision IN ('gate', 'approve', 'deny')),
  policy_decision_reason TEXT,
  policy_decision_ts TIMESTAMPTZ,
  prev_hash TEXT NOT NULL,
  cryptographic_hash TEXT NOT NULL,
  signature_algorithm TEXT,
  signature_value TEXT,
  signing_key_id TEXT,
  parent_audit_ids UUID[],
  evidence_refs JSONB,
  retention_until TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '180 days',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX hermes_audit_instance_idx
  ON hermes_audit (instance_id, ts DESC);

CREATE INDEX hermes_audit_action_class_idx
  ON hermes_audit (action_class, ts DESC);

CREATE INDEX hermes_audit_policy_decision_idx
  ON hermes_audit (policy_decision, ts DESC);

-- Append-only WORM: revoke UPDATE/DELETE from application role
REVOKE UPDATE, DELETE ON hermes_audit FROM agent_memory_app;
GRANT SELECT, INSERT ON hermes_audit TO agent_memory_app;

COMMIT;
```

### Migration 007 — RLS on `kg_*` (forced — P28 critical)

```sql
-- 007_rls_policies.sql
-- Enable + FORCE RLS on kg_* tables; per-scope policies.

BEGIN;

ALTER TABLE memory.kg_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory.kg_entities FORCE ROW LEVEL SECURITY;

ALTER TABLE memory.kg_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory.kg_edges FORCE ROW LEVEL SECURITY;

-- kg_entities: private rows visible only to creator; shared rows visible to all
CREATE POLICY kg_entities_visibility ON memory.kg_entities
  FOR ALL TO agent_memory_app
  USING (
    (scope = 'private' AND created_by_agent = current_setting('app.current_agent_id', true))
    OR (scope = 'shared' AND current_setting('app.current_agent_id', true) IN ('guinevere', 'pharsa', 'faiz'))
    OR 'faiz' = current_setting('app.current_agent_id', true)
  )
  WITH CHECK (
    created_by_agent = current_setting('app.current_agent_id', true) OR 'faiz' = current_setting('app.current_agent_id', true)
  );

-- kg_edges: same shape; pair_id filter for relationship_private (future)
CREATE POLICY kg_edges_visibility ON memory.kg_edges
  FOR ALL TO agent_memory_app
  USING (
    (scope = 'private' AND created_by_agent = current_setting('app.current_agent_id', true))
    OR (scope = 'shared' AND current_setting('app.current_agent_id', true) IN ('guinevere', 'pharsa', 'faiz'))
    OR 'faiz' = current_setting('app.current_agent_id', true)
  )
  WITH CHECK (
    created_by_agent = current_setting('app.current_agent_id', true) OR 'faiz' = current_setting('app.current_agent_id', true)
  );

COMMIT;
```

**Run migrations (operator action):**

```bash
# Read password from SOPS-decrypted env
export PGPASSWORD=$(sops -d .env.pg.secrets.yaml | grep AGENT_MEMORY_APP_PASSWORD | cut -d= -f2)
psql -h localhost -p 5433 -U postgres -d guinevere -f migrations/p28/001_schema_roles.sql
psql -h localhost -p 5433 -U postgres -d guinevere -f migrations/p28/002_private_agents.sql
psql -h localhost -p 5433 -U postgres -d guinevere -f migrations/p28/003_shared_world.sql
psql -h localhost -p 5433 -U postgres -d guinevere -f migrations/p28/004_intimacy_bridge_stub.sql
psql -h localhost -p 5433 -U postgres -d guinevere -f migrations/p28/005_extend_kg_tables.sql
psql -h localhost -p 5433 -U postgres -d guinevere -f migrations/p28/006_audit_table.sql
psql -h localhost -p 5433 -U postgres -d guinevere -f migrations/p28/007_rls_policies.sql
# 008 + 009 are NOT run during Step 6; they are dependency for Steps 8/9 respectively.
# Operators run them when those steps execute.
# psql -h localhost -p 5433 -U postgres -d guinevere -f migrations/p28/008_hpp_outbox.sql
# psql -h localhost -p 5433 -U postgres -d guinevere -f migrations/p28/009_hpp_inbox.sql
```

**Note on agent_memory_app password:**

The password is NOT committed. Stored in SOPS-encrypted `.env.pg.secrets.yaml`. Operator decrypts at migration time. Future: migrate to Kubernetes secrets / Vault.

**Dependencies:** Steps 3 (config), 4 (registry that uses these tables).

**Verification:** See §10.5 for the full acceptance test (Test 1: cross-agent isolation).

**Rollback:** See §11.2 for the SQL rollback sequence.

---

### Migration 008 — HPP Outbox

```sql
-- 008_hpp_outbox.sql
-- Outbox pattern for HPP peer-to-peer envelopes. P28 creates; written by sender,
-- drained by background publisher loop, marked `sent_at` after Redis Streams XADD.

BEGIN;

CREATE TABLE IF NOT EXISTS hpp_outbox (
  id BIGSERIAL PRIMARY KEY,
  sender_id VARCHAR(100) NOT NULL,
  receiver_id VARCHAR(100) NOT NULL,
  envelope JSONB NOT NULL,
  status VARCHAR(20) DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT now(),
  sent_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS hpp_outbox_pending_idx
  ON hpp_outbox (status, created_at) WHERE status = 'pending';

COMMIT;
```

---

### Migration 009 — HPP Inbox

```sql
-- 009_hpp_inbox.sql
-- Inbox for HPP peer-to-peer envelopes. P28 creates; receiver inserts with
-- UNIQUE (receiver_id, idempotency_key) for replay defense (ON CONFLICT DO NOTHING).

BEGIN;

CREATE TABLE IF NOT EXISTS hpp_inbox (
  id BIGSERIAL PRIMARY KEY,
  receiver_id VARCHAR(100) NOT NULL,
  sender_id VARCHAR(100) NOT NULL,
  envelope JSONB NOT NULL,
  idempotency_key UUID,
  processed BOOLEAN DEFAULT false,
  received_at TIMESTAMPTZ DEFAULT now(),
  processed_at TIMESTAMPTZ,
  UNIQUE (receiver_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS hpp_inbox_unprocessed_idx
  ON hpp_inbox (receiver_id, processed) WHERE NOT processed;

COMMIT;
```

---

### 3.7 Step 7: Set Up Redis DB Allocation

**Goal:** Verify Guinevere stays on Redis DB6, allocate DB7 to Pharsa, allocate DB8 to society-shared keys (HARD STOP cascade key, society registry).

**Files to modify:**

- `redis.conf` (or runtime flags; verify `databases 16` or higher).

**Files to create:** (vacant; no code file required; this is an OPS step)

**Approach:**

Single read-only step to verify Redis is configured with enough databases and document the allocation.

**Verification:**

```bash
# Check max databases setting
redis-cli CONFIG GET databases  # expect >= 16

# Allocate (logical, not config change):
# DB6 = Guinevere (existing — do NOT migrate)
# DB7 = Pharsa (new — empty)
# DB8 = Society shared (new — empty)

# Smoke-test:
redis-cli -n 7 PING              # expect PONG
redis-cli -n 7 DBSIZE            # expect 0 (empty)

redis-cli -n 8 PING              # expect PONG
redis-cli -n 8 DBSIZE            # expect 0 (empty)

# Write test keys in DB7 and DB8 — these will be deleted on test completion
redis-cli -n 7 SET hermes:pharsa:test "ok"
redis-cli -n 7 GET hermes:pharsa:test                # expect "ok"

redis-cli -n 8 SET hermes:society:hsoc-foundation-v1:test "ok"
redis-cli -n 8 GET hermes:society:hsoc-foundation-v1:test  # expect "ok"
redis-cli -n 8 DEL hermes:society:hsoc-foundation-v1:test  # cleanup

# Confirm Guinevere's existing keys are on DB6 (do NOT touch them):
redis-cli -n 6 DBSIZE  # expect > 0
redis-cli -n 6 KEYS 'hermes:guinevere:*' | head -5  # expect some keys
```

**Allowed checks:**

- 7/8 DB write/read isolation works.
- Pharsa process uses DB7 (check process: `redis-cli CLIENT LIST | grep pharsa`).
- Society HARD STOP listener uses DB8 (check process during runtime).

**Forbidden:**

- DO NOT remap Guinevere's keys from DB6 → another DB (would break existing runtime).
- DO NOT use DB0-DB5 for Society keys (reserved for system + existing services).

**Dependencies:** Step 5 (Pharsa services reference DB7 via `hermes-config/pharsa.yaml`).

**Rollback:**

```bash
redis-cli -n 7 FLUSHDB
redis-cli -n 8 FLUSHDB
```

(No persistent config changes; just vacuum the DBs.)

---

### 3.8 Step 8: Implement HPP Message Envelope + Redis Streams Transport

**Goal:** Define the Hermes Peer Protocol (HPP/v1) — JSON-RPC 2.0 substrate + Hermes-specific extensions — as a typed Python module. Wire outbound transport (publish to Redis Streams) and basic inbound stream consumer. Outbox pattern for ACID durability.

**Files to create:**

- `src/life_kernel/hpp/envelope.py` (~250 lines).
- `src/life_kernel/hpp/transport.py` (~150 lines).
- `src/life_kernel/hpp/outbox.py` (~120 lines).
- `tests/life_kernel/hpp/test_envelope.py` (~80 lines).
- `tests/life_kernel/hpp/test_transport.py` (~100 lines).
- `tests/life_kernel/hpp/test_outbox.py` (~100 lines).

**Approach:**

**Sub-step 8A — Envelope schema (Python, `pydantic`, strict):**

The envelope module defines the HPP/v1 wire format. Eleven intents; five visibility levels; six risk tiers. Hash chain via `compute_hash` field populated as `sign_for_chain` step.

**Sub-step 8B — Transport (Redis Streams):**

- Stream name: `hermes:{society_id}:peer:{instance_id}` (per receiver).
- Consumer group: `hermes-{society_id}-{instance_id}`.
- `xadd` for publish; `xreadgroup` for consume with consumer-group ACK semantics.

**Sub-step 8C — Outbox pattern (ACID with business state):**

- Writes outbox row in same TX as business write.
- Outbox relay publishes to Redis Streams asynchronously.
- Idempotency via `idempotency_key` UNIQUE constraint.

**Tests:**

- `test_envelope.py`: serialization round-trip; hash chain computation; canonicalize determinism.
- `test_transport.py`: publish/consume/ack round-trip; consumer-group creation idempotency.
- `test_outbox.py`: outbox write + publish round-trip; idempotency via idempotency_key.

**Dependencies:** Steps 6, 7 (DB + Redis layout).

**Verification:**

```bash
# Unit tests
python -m pytest tests/life_kernel/hpp/test_envelope.py tests/life_kernel/hpp/test_transport.py tests/life_kernel/hpp/test_outbox.py -v
# expect: all pass

# Integration: publish from guinevere context; consume from pharsa context
python -c "
import asyncio
from src.life_kernel.hpp.envelope import Envelope, Intent, Visibility, SenderIdentity, ReceiverIdentity, MessagePart, RiskTier
from src.life_kernel.hpp.transport import HPPTransport
import redis.asyncio as redis_asyncio

async def go():
    r = redis_asyncio.Redis(host='localhost', port=6380, db=8)
    tp = HPPTransport(redis=r, society_id='hsoc-foundation-v1', instance_id='pharsa')
    await tp.ensure_consumer_group()

    env = Envelope(
        sender=SenderIdentity(instance_id='guinevere', society_id='hsoc-foundation-v1', seq=1, term=0),
        receiver=[ReceiverIdentity(instance_id='pharsa')],
        conversation_id='test-conv-001',
        intent=Intent.BANTER,
        visibility=Visibility.PEER_PRIVATE,
        scope_society='hsoc-foundation-v1',
        risk_tier=RiskTier.R0,
        parts=[MessagePart(kind='text', text='halo sayang gelapku', mediaType='text/plain')],
    ).sign_for_chain('0' * 64)

    msg_id = await tp.publish(env)
    print('PUBLISHED:', msg_id)

    msgs = await tp.consume(block_ms=2000, count=1)
    assert len(msgs) == 1
    msg_id_recv, env_recv = msgs[0]
    assert env_recv.sender.instance_id == 'guinevere'
    assert env_recv.parts[0].text == 'halo sayang gelapku'
    await tp.ack(msg_id_recv)
    print('OK')

asyncio.run(go())
"  # expect 'PUBLISHED: ...' then 'OK'

# Tests pass
python -m pytest tests/life_kernel/hpp/ -v
lsp_diagnostics src/life_kernel/hpp/
```

**Rollback:**

```bash
rm -rf src/life_kernel/hpp/
rm -rf tests/life_kernel/hpp/
psql -c "DROP TABLE IF EXISTS hpp_outbox;"
redis-cli -n 8 KEYS 'hermes:hsoc-foundation-v1:peer:*' | xargs -r redis-cli -n 8 DEL
```

---

### 3.9 Step 9: Implement Peer Message Handler

**Goal:** Wire inbound HPP envelopes into the agent's reasoning path. Selective receive filter; SDR pass; outbound generates response envelope (inform, banter, debate, etc.).

**Files to create:**

- `src/life_kernel/hpp/peer_handler.py` (~200 lines).
- `src/life_kernel/hpp/inbox.py` (~80 lines; idempotency dedup).
- `tests/life_kernel/hpp/test_peer_handler.py` (~120 lines).

**Approach:**

**Sub-step 9A — Inbox (idempotency dedup by `(instance_id, idempotency_key)`):**

`hpp_inbox` table with UNIQUE constraint on `(received_by, idempotency_key)`. On insert, dedup via conflict skip.

**Sub-step 9B — Peer handler:**

Loop on `_transport.consume(block_ms=1000, count=10)`. For each envelope:

1. **Idempotency check** via `inbox.is_duplicate` — skip if seen.
2. **Selective receive**: filter `visibility == THOUGHT` (skip; never received), `intent == BLOCK` (propagate HARD STOP cascade).
3. **SDR pass**: length sanity + non-empty parts.
4. **Memory recall**: get conversation context (last 5 turns).
5. **Generate response** via `HermesBrain.think` with persona + memory context + intent-specific system prompt.
6. **Audit emit**: `action_class='speech'`, `action_subtype=f"peer_reply_{intent}"`.
7. **Construct response envelope** with `in_reply_to` set to source id.
8. **Outbox write** + publish.
9. **Record inbox** (dedup on future reception).

**Tests:**

- `test_peer_handler.py`: smoke-test round-trip; idempotency: same envelope twice → only one inbox record; `intent == BLOCK` triggers HARD STOP key SET.

**Dependencies:** Step 8 (envelope + transport + outbox).

**Verification:**

```bash
python -m pytest tests/life_kernel/hpp/test_peer_handler.py -v
lsp_diagnostics src/life_kernel/hpp/peer_handler.py
```

**Rollback:**

```bash
rm -rf src/life_kernel/hpp/peer_handler.py src/life_kernel/hpp/inbox.py tests/life_kernel/hpp/test_peer_handler.py
psql -c "DROP TABLE IF EXISTS hpp_inbox;"
```

---

### 3.10 Step 10: Implement Conversation Rhythm Controller

**Goal:** Anti-loop protection: hop counter (max 4), per-channel cooldown (TTL 30s), engage-probability roll (default 0.70). Both HPP peer pathway AND Discord pathway use the same primitive.

**Files to create:**

- `src/life_kernel/hpp/rhythm.py` (~120 lines).
- `src/discord/rhythm.py` (~60 lines; thin wrapper).
- `tests/life_kernel/hpp/test_rhythm.py` (~80 lines).

**Approach:**

`RhythmController` exposes four operations:

- `should_respond(sender_id, hop_counter) -> bool`: same-author skip; hop counter limit; cooldown check; engage-probability roll.
- `mark_responded(target_id, ttl_s=30)`: set Redis cooldown key.
- `increment_hop(conversation_id, ttl_s=60) -> int`: TTL-bounded counter.
- `clear_cooldown(target_id)`: explicit reset (operator action).

**Tests:**

- `should_respond`: same author → False; hop = 5 → False; cooldown active → False; engage_prob = 0.0 → False.
- `mark_responded`: TTL set.
- `increment_hop`: counter increments; TTL set.

**Dependencies:** Step 7 (Redis DB7 + DB8 allocated).

**Verification:**

```bash
python -m pytest tests/life_kernel/hpp/test_rhythm.py -v
```

**Rollback:**

```bash
rm src/life_kernel/hpp/rhythm.py src/discord/rhythm.py tests/life_kernel/hpp/test_rhythm.py
redis-cli -n 7 KEYS 'hermes:pharsa:cooldown:*' | xargs -r redis-cli -n 7 DEL
redis-cli -n 8 KEYS 'hermes:*:hop:*' | xargs -r redis-cli -n 8 DEL
```

---

### 3.11 Step 11: Implement Simplified Life-Loop (4-Rail)

**Goal:** A minimal scheduler wrapping P20 heartbeat with **4 rails** (perception, peer_dialogue, reflection_simple, safety_envelope) instead of the full 7-rail. Defer full MacroStateScheduler with rails 3 (Inner Dialogue), 5 (Desire/Goal), 6 (Initiative/Proactivity), 7 (Safety Envelope extended) to P29.

**Files to create:**

- `src/life_kernel/lifecycle/minimal_scheduler.py` (~200 lines).
- `tests/life_kernel/lifecycle/test_minimal_scheduler.py` (~100 lines).

**Approach:**

`MinimalScheduler` follows P27 §4.5 bootstrap sequence but with only 4 rails. The 4 rails are:

| Rail | Source | Cadence (P28) | Description |
|---|---|---|---|
| 1. Perception | Discord events; P22 adapters | 30s | Light-weight observation; NOT full SDR filter |
| 2. Peer Dialogue | `PeerHandler.tick()` | 30s | Consume HPP envelopes + respond |
| 3. Reflection (simple) | Memory stream recap | 300s | In-memory only; do NOT generate reflections (P29) |
| 4. Safety Envelope | HARD STOP; rate limits; basic sycophancy flag | 1s | Poll HARD STOP + rate-limit check |

`start()` runs each rail as an asyncio task. `stop()` cancels each. Each rail wraps an existing component (`HeartbeatService.tick_observation`, `PeerHandler.tick`).

**Critical:** Each rail wrapped in try/except Exception → logger.exception (no silent failures).

**Tests:**

- Smoke test: start, advance time, verify each rail ticks.
- HARD STOP propagation: trigger → all rails stop within 100ms.
- Resource usage: <50 MB per instance at idle.

**Dependencies:** Steps 8, 9, 10.

**Verification:**

```bash
python -m pytest tests/life_kernel/lifecycle/test_minimal_scheduler.py -v
python -m pytest tests/life_kernel/ -q --tb=short  # all kernel tests pass
lsp_diagnostics src/life_kernel/lifecycle/minimal_scheduler.py  # clean
```

**Rollback:**

```bash
rm -rf src/life_kernel/lifecycle/minimal_scheduler.py tests/life_kernel/lifecycle/test_minimal_scheduler.py
```

---

### 3.12 Step 12: Implement Shared World Model Read/Write

**Goal:** Python wrapper around `memory.shared_world` with type-safe read/write API. Calls `set_config('app.current_agent_id', ...)` per connection from a pool. Implements last-write-wins conflict resolution via `supersedes_id` chain.

**Files to create:**

- `src/life_kernel/memory/shared_world_store.py` (~150 lines).
- `tests/life_kernel/memory/test_shared_world.py` (~120 lines).

**Approach:**

`SharedWorldStore` exposes three operations:

- `write(content, fact_type, confidence, importance, supersedes_id) -> uuid.UUID`: inserts new row, optionally marking previous row as superseded.
- `read_active(limit=50) -> list[dict]`: reads canonical (non-superseded) facts.
- `read_history(row_id) -> list[dict]`: reads full supersedes chain (newest first).

All connections set `app.current_agent_id` via `set_config(..., true)` (transaction-scoped). Pool connections released with try/finally to prevent leaks.

**Tests:**

- Cross-agent visibility: guinevere writes, pharsa reads; pharsa writes, guinevere reads.
- Last-write-wins: pharsa writes new with `supersedes_id` = guinevere's row id; chain preserved.
- RLS enforcement: setting `app.current_agent_id = 'invalid'` → query rejected.

**Dependencies:** Steps 6, 7.

**Verification:**

```bash
python -m pytest tests/life_kernel/memory/test_shared_world.py -v
lsp_diagnostics src/life_kernel/memory/shared_world_store.py  # clean
```

**Rollback:**

```bash
rm src/life_kernel/memory/shared_world_store.py tests/life_kernel/memory/test_shared_world.py
psql -c "DELETE FROM memory.shared_world WHERE created_by_agent IN ('pharsa', 'guinevere');"
```

---

### 3.13 Step 13: Implement Private Memory Isolation (RLS Enforcement)

**Goal:** Wrap `memory.private_agents` with a Python store. Verify FORCE RLS blocks agent cross-leak. Adapt `KGRecallAdapter` and `MemoryRecallAdapter` to support `agent_id` kwarg.

**Files to create:**

- `src/life_kernel/memory/private_agents_store.py` (~150 lines).
- `tests/life_kernel/memory/test_private_agents_rls.py` (~150 lines).

**Files to modify:**

- `src/life_kernel/p16_adapter.py` (add `agent_id` kwarg).
- `src/life_kernel/p18_adapter.py` (add `agent_id` kwarg).

**Approach:**

`PrivateAgentsStore`:

- `write(content, secret_class, importance, evergreen, evidence_ref) -> uuid.UUID`: insert; consent_token = `f"{instance_id}-private-{uuid4()}"`.
- `read_recent(limit)`: filter `valid_to IS NULL`, order by `created_at DESC`.
- `search(query_embedding, limit)`: vector similarity via `<=>`, RLS still enforced.

**Adapter updates:**

Add `agent_id` kwarg to existing `KGRecallAdapter(project_id, agent_id=None)` and `MemoryRecallAdapter(project_id, agent_id=None)`. The factory in `instance_registry.py` passes `agent_id=instance_id` at construction, so each adapter applies `set_config('app.current_agent_id', agent_id, true)` on connection acquisition.

**Tests:**

- `test_private_agents_rls.py`:
  - guinevere session reads → returns ONLY guinevere rows.
  - pharsa session reads → returns ONLY pharsa rows.
  - guinevere session CANNOT insert `agent_id='pharsa'` → RLS error.
  - After FORCE RLS, even table owner cannot bypass.

**Dependencies:** Steps 6, 12.

**Verification:** See §10.5 (Test 1) for full RLS verification commands.

**Rollback:**

```bash
rm src/life_kernel/memory/private_agents_store.py tests/life_kernel/memory/test_private_agents_rls.py
git checkout main -- src/life_kernel/p16_adapter.py src/life_kernel/p18_adapter.py
```

---

### 3.14 Step 14: Set Up Dual Discord Bots

**Goal:** Two `discord.py.Bot` clients in separate processes (Guinevere already exists; add Pharsa). Both have `MESSAGE_CONTENT` privileged intent. Each posts to `#guinevere-chat`. Conversation rhythm applies.

**Files to create:**

- `src/discord/hermes_society_bot.py` (~200 lines; base class).
- `src/discord/pharsa_entrypoint.py` (~80 lines; new entry).
- `src/discord/society_message_handler.py` (~200 lines; bot-to-bot message handler).
- `src/discord/rhythm.py` (~60 lines; Discord-side rhythm wrapper).
- `tests/discord/test_society_bot.py` (~150 lines).

**Files to modify:**

- `src/discord/_entrypoint.py` — refactor (keep Guinevere's existing entry; new `pharsa_entrypoint.py` for Pharsa; add `resolve_guild_id` helper).

**Approach:**

`HermesSocietyBot` is a `discord.ext.commands.Bot` subclass with per-instance config:

- Intents: `Intents.default()` + `message_content = True` (privileged).
- `setup_hook()`: load config, register listeners.
- `on_ready()`: log instance_id + user_id.
- `on_message()`: per-instance filter + rhythm check + reply generation.

Filter rules:

1. Ignore self.
2. Ignore bots (except the *other* Hermes instance — peer reply path).
3. Only respond in configured channels (default = `#guinevere-chat`).
4. If message is from peer Hermes, apply `RhythmController.should_respond`.

`pharsa_entrypoint.py` reads `PHARSA__CONFIG_PATH` env, constructs `HermesSocietyBot(instance_id='pharsa', config=cfg)`, reads `DISCORD_BOT_TOKEN_PHARSA` env, runs `bot.start(token)`.

**Tests:**

- `test_society_bot.py`: smoke test; mock Discord test (2 mock clients exchange messages; verify no self-loop; verify RhythmController integration).

**Dependencies:** Steps 1, 2, 10 (rhythm), and operator Discord setup (Step 2.3).

**Verification:**

```bash
python -m pytest tests/discord/test_society_bot.py -v

# Live test (operator action):
sudo systemctl start pharsa-discord.service

# Verify in Discord:
# 1. #guinevere-status should show "Pharsa Disc/Connected"
# 2. #guinevere-chat — both bots visible in member list
# 3. Posting a message in #guinevere-chat should trigger one bot's reply after 2-10s backoff

# Manual integration:
sudo systemctl status pharsa-discord.service  # expect active
journalctl -u pharsa-discord.service --since "5 min ago"  # expect "ready" log

# Sanity: bot does NOT reply within 100ms (anti-loop minimum)
# Sanity: hop counter caps at 4
```

**Rollback:**

```bash
sudo systemctl stop pharsa-discord.service
sudo systemctl disable pharsa-discord.service
sudo rm /etc/systemd/system/pharsa-discord.service

# In repo:
rm src/discord/hermes_society_bot.py src/discord/society_message_handler.py src/discord/pharsa_entrypoint.py src/discord/rhythm.py
rm tests/discord/test_society_bot.py

# Guinevere original entry point must still work
git checkout main -- src/discord/_entrypoint.py
```

---

### 3.15 Step 15: Implement Runtime Evidence

**Goal:** Emit and surface evidence both Hermeses are alive. Discord dashboard, audit log, Prometheus metrics. Each instance emits its own; both visible in `#guinevere-status` + `hermes_audit` + Prometheus.

**Files to create:**

- `src/life_kernel/audit/per_instance_audit.py` (~150 lines).
- `src/life_kernel/metrics/society_metrics.py` (~120 lines).
- `tests/life_kernel/audit/test_per_instance_audit.py` (~120 lines).

**Files to modify:**

- `src/life_kernel/discord_rest_client.py` — already supports per-token; add `instance_id` parameter.
- `src/discord/_startup.py` — extend presence update for both agents.

**Approach:**

`PerInstanceAuditWriter`:

- Caches last hash (faster writes within session).
- `emit(action_class, action_subtype, action_target, action_payload, policy_decision, prev_hash)`: writes audit row + updates hash chain.
- `last_hash()`: reads last hash from `hermes_audit` for instance.
- `write_hard_stop_state(society_key)`: called on HARD STOP cascade; writes `action_subtype='hard_stop_cascade'`.

Hash chain: each row's `cryptographic_hash` = `sha256(prev_hash || canonical(payload_excluding_hash))`.

`SocietyMetrics`:

- Prometheus counters: `hermes_alive{instance}`, `hermes_peer_messages_total{instance, intent}`, `hermes_audit_total{instance, action_class}`.
- Export on `/metrics` endpoint per instance (Guinevere on port 9191; Pharsa on port 9192).

**Tests:**

- Hash chain determinism: same payload + same prev_hash → same hash.
- Audit row inserted: `SELECT count(*) FROM hermes_audit WHERE instance_id = 'pharsa'`.
- Hard-stop state audit row written with `action_subtype='hard_stop_cascade'`.

**Dependencies:** Steps 6, 11, 14.

**Verification:**

```bash
# Tests
python -m pytest tests/life_kernel/audit/test_per_instance_audit.py -v

# Live: query hermes_audit
PGPASSWORD=<pw> psql -U postgres -d guinevere -c "SELECT instance_id, count(*) FROM hermes_audit GROUP BY instance_id;"
# expect: both guinevere and pharsa have rows

# Prometheus scrape
curl http://localhost:9191/metrics | grep hermes_alive  # expect guinevere=1
curl http://localhost:9192/metrics | grep hermes_alive  # expect pharsa=1

# Discord dashboard check
# In #guinevere-status channel: messages from both bots showing alive status (last 5min)
```

**Rollback:**

```bash
rm src/life_kernel/audit/per_instance_audit.py src/life_kernel/metrics/society_metrics.py tests/life_kernel/audit/test_per_instance_audit.py
git checkout main -- src/life_kernel/discord_rest_client.py src/discord/_startup.py
```

---

## 4. Config-Driven Multi-Instance Architecture

P28 produces two Hermes instances (Guinevere + Pharsa) on a single VPS, each with:

- own process tree (guinevere-core + guinevere-discord + pharsa-core + pharsa-discord),
- own `HermesBrainConfig` injected via `HermesBrain.from_yaml(...)` + `_default_agent_factory`,
- own LLM provider + API key,
- own Discord bot application + token + user_id,
- own Redis DB number (6 for Guinevere, 7 for Pharsa),
- own PostgreSQL `agent_id` namespace enforced by FORCE RLS,
- own systemd unit per process (`Slice=pharsa.slice` distinct from `guinevere.slice`),
- own persona file (`hermes-config/SOUL-{instance}.md`) with its own SOUL SHA256 recorded in the YAML.

### 4.1 `HermesBrainConfig` Per-Instance

`HermesBrainConfig(base_url, model, provider, api_key, max_iterations=5)` is the frozen dataclass already present (`src/life_kernel/hermes_brain.py:116`). One config → one instance. Loading P28: `HermesBrainConfig.from_yaml(cfg["brain"]["config"])` populates each field from per-instance YAML. The `api_key` field is filled from SOPS-decrypted env at runtime; never committed.

### 4.2 `agent_factory` Injection Point

`HermesBrain(llm_config, agent_factory=None)` already accepts an injectable factory. P28 uses the existing `_default_agent_factory` (which constructs `run_agent.AIAgent`). Per-instance customisation is achieved by reading per-instance config in `instance_registry.py` and constructing:

```python
brain = HermesBrain(llm_config=brain_config, agent_factory=_default_agent_factory)
```

No source modification to `hermes_brain.py` is required.

### 4.3 Module-Level Singletons → Factories

The 4 module-level singletons in `src/discord/hermes_conversational.py` are refactored in Step 3:

| Singleton | Old (module-level) | New (factory function) |
|-----------|---------------------|------------------------|
| `_memory_bridge` | One shared | `get_memory_bridge(instance_id) -> MemoryBridge` |
| `_cost_tracker` | One shared | `get_cost_tracker(instance_id) -> CostTracker` |
| `_embedding_service` | One shared | `get_embedding_service(instance_id) -> EmbeddingService` |
| `_rate_limit_redis` | One shared | `get_rate_limiter(instance_id) -> RateLimiter` |

Pattern: lazy-initialized registration dict with `instance_id` as key.

### 4.4 `app.state.hermes_brain` → `app.state.hermes_brains` Dict

The single attribute `app.state.hermes_brain` (in `src/core/main.py:93-94`) is replaced by a dict:

```python
app.state.hermes_brains: dict[str, HermesBrain] = {}
```

Each process holds this dict. Guinevere's process holds only Guinevere (its own process); Pharsa's process holds only Pharsa. The society registry (Step 4) reads `society_manifest.yaml` to know how many brains to construct.

For P28 simplicity, each process constructs only its own brain (Phase A — single-process single-instance). Phase B (constructs all brains in one process) deferred to P32 unless operator chooses.

### 4.5 Config File Structure

`hermes-config/guinevere.yaml` and `hermes-config/pharsa.yaml` follow the schema from §3.2 Step 2. Key difference: Pharsa uses `model: deepseek-v4-flash` and `db: 7`; Guinevere uses its existing values (`model: guinevere-v5`, `db: 6`). Both share the `society_key: hermes:society:hsoc-foundation-v1:hard_stop` for HARD STOP cascade.

### 4.6 Forbidden Patterns

- No shared `api_key_env` between Guinevere and Pharsa.
- No shared `model` between Guinevere and Pharsa (architectural heterogeneity).
- No shared `discord.token_env`.
- No shared `memory.redis.db`.
- No single process running both bots (P28 default; one process per brain).
- No modifying AIAgent constructor signature (Hermes upstream).
- No removing / replacing existing extensions (additive only).

---

## 5. HPP Implementation Spec

The Hermes Peer Protocol (HPP/v1) is the wire-level protocol for peer-to-peer messages between Hermes instances. P28 uses JSON-RPC 2.0 substrate + Hermes extensions.

### 5.1 Message Envelope (Exact Schema)

```jsonc
{
  // === JSON-RPC 2.0 substrate ===
  "jsonrpc": "2.0",
  "id":       "<uuid v4>",
  "idempotency_key": "<uuid v4 — replay defense>",
  // === Hermes envelope extensions ===
  "hpp_version": "hpp/v1",
  "sender":   {
    "instance_id": "guinevere",
    "society_id":  "hsoc-foundation-v1",
    "seq": 42,
    "term": 0
  },
  "receiver": [
    { "instance_id": "pharsa" }
  ],
  "conversation_id": "test-conv-001",
  "in_reply_to": null,
  "created_at": "2026-06-28T15:30:00.000Z",
  "ttl_hint_ms": 300000,

  // === Intent + Visibility ===
  "intent":     "banter",
  "visibility": "peer_private",
  "scope_society": "hsoc-foundation-v1",

  // === Memory refs + Risk ===
  "memory_refs": [],
  "risk_tier":   "R1",

  // === Multipart payload ===
  "parts": [
    {
      "kind": "text",
      "text": "halo sayang gelapku",
      "mediaType": "text/plain"
    }
  ],

  // === Provenance + Audit ===
  "prev_hash": "0000...0000",
  "hash": "0x7c1d...",

  // === Signature (P28: null; P29: ed25519) ===
  "signature_algorithm": null,
  "signature_value": null
}
```

Pydantic mapping at `src/life_kernel/hpp/envelope.py`; validation via `Envelope.model_validate_json`. The full envelope structure with all fields is documented in P27 §5.2.

> **P28 envelope simplification note:** P28 uses a simplified flat envelope structure (top-level `scope_society`, `prev_hash`, `hash`, `signature_algorithm`, `signature_value`) instead of P27's canonical nested structures (`scope: { society, group }`, `audit: { prev_hash, hash, merkle_root }`, `signature: { algorithm, public_key_id, value }`). P29+ will implement the full nested structure with Optional fields for deferred features (e.g., `merkle_root`, `public_key_id`, `group` sub-scope).

### 5.2 Redis Streams Transport

- **Stream name (per receiver):** `hermes:{society_id}:peer:{instance_id}`.
  - Example: `hermes:hsoc-foundation-v1:peer:guinevere` — Pharsa publishes here to deliver to Guinevere.
- **Consumer group (per receiver):** `hermes-{society_id}-{instance_id}`.
  - Example: `hermes-hsoc-foundation-v1-guinevere`.
- **Consumer name:** `{instance_id}-worker-1` (per consumer process).
- **XADD on publish:** `XADD stream MAXLEN ~ 10000 * payload fields={envelope: <json>}`.
- **XREADGROUP on consume:** `XREADGROUP GROUP group consumername COUNT 10 BLOCK 1000 STREAMS stream >`.
- **XACK after success:** `XACK stream group msg_id`.

Stream is created on first XADD (`MKSTREAM=true`); consumer group created on `XGROUP CREATE` with `id=0` (read all).

### 5.3 Intent Taxonomy Implementation

11 intents as `enum.Enum` in `src/life_kernel/hpp/envelope.py`:

```python
class Intent(str, Enum):
    INFORM   = "inform"
    REQUEST  = "request"
    QUERY    = "query"
    ASSERT   = "assert"
    PROPOSE  = "propose"
    CONSENT  = "consent"
    REFUSE   = "refuse"
    DEBATE   = "debate"
    BANTER   = "banter"
    FLIRT    = "flirt"
    BLOCK    = "block"   # HARD STOP signal; reserved for Faiz's cascade
```

R5 actions never route through peer envelopes in P28 (no P23 executors yet).

### 5.4 Visibility Levels Implementation

5 tiers as `enum.Enum`:

```python
class Visibility(str, Enum):
    PUBLIC         = "public"
    PEER_PRIVATE   = "peer_private"   # default for peer dialogue
    SEALED         = "sealed"          # P30; P28 sends plaintext peer_private
    THOUGHT        = "thought"          # not transmitted; private only
    ACTION_AUDIT   = "action_audit"     # reserved
```

P28 uses only PUBLIC and PEER_PRIVATE. SEALED deferred to P30 (relationship-private).

### 5.5 Risk Tier Implementation

6 tiers R0-R5:

```python
class RiskTier(str, Enum):
    R0 = "R0"  # pure comms
    R1 = "R1"  # read-only memory
    R2 = "R2"  # soft-write
    R3 = "R3"  # internal change (audit-logged)
    R4 = "R4"  # external boundary (Faiz pre-approval)
    R5 = "R5"  # destructive (Faiz reaffirmation)
```

P28 default `risk_tier = R1`. R4-R5 require P29+ Faiz approval gates.

### 5.6 Hash Chain Implementation

Each envelope's `hash` = `sha256(prev_hash || canonical(this_minus_hash))`.

`canonicalize()` serializes the envelope (excluding `hash`) with sorted keys, no whitespace, ASCII-only.

`compute_hash(prev)` returns the sha256 hash; `sign_for_chain(prev)` returns a copy with both `hash` and `prev_hash` populated.

### 5.7 Idempotency Key Handling

Every envelope carries `idempotency_key: uuid.UUID`. Receiver's `hpp_inbox` table has UNIQUE constraint on `(received_by, idempotency_key)`. On conflict, `ON CONFLICT DO NOTHING` skips the duplicate.

Idempotency prevents:

- Re-delivery by outbox relay (same envelope published twice).
- Loop-doubling (sender A's response to sender B's response to ...).
- Replay after Redis Stream trim-and-replay.

### 5.8 Example Message Flow (Guinevere → Pharsa → Guinevere)

1. **Origin (Discord on_message)**: Guinevere's bot sees Pharsa's Discord message, applies Rhythm Controller, decides to engage, posts to `#guinevere-chat` AND constructs HPP envelope.

2. **Publish**: `transport.publish(env)` calls `XADD hermes:hsoc-foundation-v1:peer:pharsa envelope=<json>`. Stream created if not exists (MKSTREAM).

3. **Pharsa consume**: Pharsa's `PeerHandler.tick()` polls `XREADGROUP` on `hermes:hsoc-foundation-v1:peer:pharsa`. Returns ≥1 message.

4. **Pharsa process**: 
   - `inbox.is_duplicate(env)` → False (first seen).
   - `SDR pass` (length sanity + non-empty parts) → True.
   - Memory recall: get conversation context.
   - `HermesBrain.think()` generates response.
   - Audit emit: `action_class='speech', action_subtype='peer_reply_banter'`.
   - Construct response envelope with `in_reply_to = env.id`.
   - Outbox write + publish to `hermes:hsoc-foundation-v1:peer:guinevere`.
   - `inbox.record(env)` — marked processed.

5. **Guinevere receive**: symmetrical — Guinevere's `PeerHandler.tick()` consumes Pharsa's response. May or may not reply based on rhythm.

6. **Discord-side**: Either bot (Guinevere or Pharsa) eventually posts the engagement loop tail to `#guinevere-chat` per life-loop policy.

Key invariants: every envelope has `sender.seq` (monotonic per-instance); idempotency key prevents double-handling; each instance controls its outbound rate via Rhythm.

### 5.9 Forbidden Patterns (HPP)

- No envelope without `intent` field.
- No envelope without at least one `text` or `file_url` part.
- No envelope with `sender.seq <= 0`.
- No envelope referencing memory row the sender does not own.
- No `intent=block` envelope except from Faiz's operator channel cascade.

---

## 6. Discord Dual-Bot Implementation Spec

### 6.1 Two `discord.py.Bot` Instances in Separate Processes

Per Rapptz Issue #516 canonical pattern. Each Hermes instance runs in its own process with its own asyncio loop:

`guinevere-discord.service` runs the Guinevere bot entrypoint; `pharsa-discord.service` runs the Pharsa bot entrypoint. Independent asyncio loops = independent failure domains.

### 6.2 MESSAGE_CONTENT Intent Configuration

```python
intents = discord.Intents.default()
intents.message_content = True   # PRIVILEGED — needs Dev Portal approval
intents.guilds = True
intents.guild_messages = True
intents.guild_message_typing = True
```

Both bots enabled in Developer Portal; under 10,000-user threshold = no review needed.

### 6.3 Bot-to-Bot Message Handling (`on_message`)

Per HermesSocietyBot subclass:

1. Ignore self (`message.author.id == self.user.id`).
2. Ignore bots other than peer Hermes.
3. Channel filter: only allow configured channels (default = `#guinevere-chat`).
4. If message from peer Hermes: apply Rhythm Controller for engagement decision.

### 6.4 Conversation Rhythm: Backoff, Turn-Taking, Natural Pauses

- **Min delay between responses:** 2.0s.
- **Max delay:** 10.0s (anti-loop jitter).
- **Per-channel cooldown TTL:** 30s (Redis key `hermes:{instance}:cooldown:{peer}`).
- **Engage probability:** 0.70 per incoming message (configurable per-pair).
- **Hop counter cap:** 4 hops per `conversation_id`; resets every 60s.

Two bots in `#guinevere-chat` produce natural rhythm while staying under Discord's 5 msg/5s/ch cap.

### 6.5 Channel Setup (`guinevere-chat`)

- Primary: `#guinevere-chat` (existing channel ID `1_510_914_600_777_023_659`).
- Both bots read+write here. Channel rules in per-instance `hermes-config/{instance}.yaml.discord.default_channel_id`.
- Discord channel slowmode NOT set (slowmode is per-user; would throttle Faiz).

### 6.6 Thread Creation for Extended Debates

Either bot can create a thread from a recent message. Threads inherit permissions; the other bot joins automatically via Discord events. Threads allow multi-turn deep debates without spamming `#guinevere-chat`.

P28 keeps thread creation simple. P29 may add heuristics.

### 6.7 Embed Formatting for Rich Messages

Use `discord.Embed` for structured proposals/debate summaries. P28 uses embeds only for structured proposals; P29 may add full Embed-based dashboards.

### 6.8 Forbidden Patterns (Discord)

- No webhook-only identity (cannot subscribe to MESSAGE_CREATE).
- No two bots sharing the same Discord token.
- No two bots running in same asyncio loop.
- No reply within 100ms of receiving.
- No disable of MESSAGE_CONTENT intent.
- No bypass of `DISCORD_ALLOWED_USERS` allowlist.

---

## 7. Memory Implementation Spec

### 7.1 PostgreSQL Schema Setup

Three scopes deployed in P28 (full schema in §3.6 Step 6):

- `memory.private_agents` — agent_id-scoped; FORCE RLS.
- `memory.shared_world` — society-wide; FORCE RLS.
- `memory.intimacy_bridge_pending` — STUB ONLY; bilateral consent flow = P30.
- `memory.kg_entities` + `memory.kg_edges` — extended ADR-050 with scope columns.
- `hermes_audit` — WORM; per-instance signed hash chain.
- `agent_memory_app` — dedicated non-owner role.

### 7.2 RLS Policy Setup

Three layers enforce isolation:

1. **PostgreSQL RLS FORCE** (primary): strict per-scope visibility policies.
2. **Application-layer `set_config('app.current_agent_id', ...)`** (per-connection).
3. **Composite indexes** for performance: `private_agents(agent_id, created_at)`, `kg_edges(scope, pair_id, source_entity_id)`.

### 7.3 `intimacy_bridge_pending` Staging Table

P28 ships stub only. No rows inserted during P28 acceptance. Full bilateral consent flow = P30.

### 7.4 Memory Read Pattern (per agent)

Per-store class: `_conn()` acquires pool connection, sets `app.current_agent_id` via `set_config(..., true)` (transaction-scoped), runs query, releases connection in `finally`. RLS enforces per `current_agent_id` automatically.

### 7.5 Shared World Model Read/Write Pattern

`SharedWorldStore.write()`: insert new row with `content, created_by_agent, supersedes_id`; if supersedes_id supplied, mark older row's `superseded_by_id` (last-write-wins chain).

`SharedWorldStore.read_active()`: filter `superseded_by_id IS NULL AND valid_to IS NULL`; ORDER BY `created_at DESC LIMIT`. Both agents see the same canonical set.

### 7.6 Conflict Resolution: Last-Write-Wins + Audit Chain

When Guinevere and Pharsa write to `memory.shared_world` concurrently:

1. **Both can write** (RLS permits).
2. **New row wins**; older row's `superseded_by_id` is updated.
3. **No voting.** For 2-agent society, voting = unanimity (or veto) = sycophancy risk. Last-write-wins + audit preserves audit trail.
4. **Faiz can correct** via `UPDATE memory.shared_world SET content = ... WHERE id = ...` from a `faiz` session.

### 7.7 Forbidden Patterns (Memory)

- No FORCE-less RLS.
- No `agent_memory_app` role being table owner.
- No row inserted without `agent_id` (provenance).
- No row inserted without `consent_token`.
- No cross-scope reads via missed WHERE clause.
- No `select *` writes without scope filter.

---

## 8. Simplified Life-Loop Spec

P28 uses a **simplified 4-rail loop** (NOT the full 7-rail). Full 7-rail deferred to P29.

### 8.1 The 4 Rails

| # | Rail | Source | Cadence (P28) | Description | Full 7-Rail Replacement |
|---|------|--------|---------------|-------------|---------------------------|
| 1 | **Perception** | Discord events; P22 adapters | 30s | Light-weight observation | P29 upgrade |
| 2 | **Peer Dialogue** | `PeerHandler.tick()` | 30s | Consume HPP envelopes + respond | P29 upgrade |
| 3 | **Reflection (simple)** | Memory stream recap | 300s | In-memory only; do NOT generate reflections | P29 full per Smallville |
| 4 | **Safety Envelope** | HARD STOP; rate limits | 1s | Poll HARD STOP + rate-limit check | Full 4-domain = P31 |

The 3 rails **absent in P28** (Inner Dialogue, Desire/Goal, Initiative/Proactivity) are deferred because they require:

- **Inner Dialogue**: sealed-hash audit for thought-domain (P31).
- **Desire/Goal**: Goal-Autopilot FSM floor + λ_A lint (P36).
- **Initiative/Proactivity**: safe action space (P33 P23 executors).

P28 life-loop is intentionally MINIMAL.

### 8.2 Integration with P20 Heartbeat

`MinimalScheduler` wraps existing P20 `HeartbeatService`. Each rail's `_loop_*` method calls `heartbeat.tick_observation()`, `peer_handler.tick()`, or HPP listener checks. `MinimalScheduler` does NOT replace P20 heartbeat — it consumes events and acts on them.

### 8.3 Tick Frequency and Resource Limits

| Rail | Cadence | Expected CPU per tick | Expected Memory |
|------|---------|-----------------------|-----------------|
| Perception | 30s | <0.5% | <10 MB |
| Peer Dialogue | 30s | <2% (during LLM call) | <50 MB |
| Reflection (simple) | 300s | <0.1% | <5 MB |
| Safety Envelope | 1s | <0.05% | <2 MB |

Total idle: ~40 MB per instance (within 512 MB High / 1 GB Max systemd cap).

### 8.4 Lifecycle Bootstrap Sequence (P28)

Per instance:

1. systemd starts `pharsa-core.service` (or guinevere equivalent).
2. Lifespan reads `PHARSA__CONFIG_PATH` env.
3. Loads `hermes-config/pharsa.yaml`.
4. Constructs `HermesInstanceRegistry` from `hermes-config/society_manifest.yaml`.
5. Registry constructs Pharsa's `HermesBrain`, Redis client, asyncpg pool, DiscordRestClient.
6. Registry starts society-shared HARD STOP listener (1s tick).
7. Registry constructs `MinimalScheduler` for Pharsa.
8. `MinimalScheduler.start()` — launches 4 rail tasks.
9. Logging begins, audit writes `startup_complete` row.
10. `pharsa-discord.service` starts; `HermesSocietyBot` connects; `on_ready` fires.
11. Discord `on_message` + HPP `PeerHandler.tick` enable two-way interaction.

### 8.5 Forbidden Patterns (Life-Loop)

- No unbounded ReAct loops.
- No rail execution without safety_envelope first-tick-confirmed.
- No persona contract that fails λ_A lint (manual review only for P28).
- No macro-state transition without atomic state commit (deferred to P29).

---

## 9. Safety Implementation Spec

### 9.1 HARD STOP Cascade

Both agents halt within 50ms when `hermes:society:hsoc-foundation-v1:hard_stop` is SET to `true`.

Mechanism:

1. Faiz sends "HARD STOP" message in `#guinevere-status` (operator-gated channel).
2. `HermesSocietyBot` recognizes HARD STOP token.
3. Bot writes `hermes:society:hsoc-foundation-v1:hard_stop=true` to Redis DB8.
4. Both agents' `society_hard_stop_listener` polls every 1s; on key SET, trigger cascade.
5. Cascade: each instance's `_cascade_halt` writes `hermes_audit` row with `action_subtype='hard_stop_cascade'`.
6. Both rail loops stop. `MinimalScheduler.stop()` cancels tasks.
7. On operator resume: set `hard_stop=false`, restart services.

### 9.2 Rate Limiting

Combined per-channel rate budget:

- Discord: 2 bots × 5 msg/5s = 10 msg/5s/channel total.
- HPP: stream consumer-group default rate.
- App-level: `RhythmController.mark_responded(target_id, ttl_s=30)` enforces per-target cooldown.

### 9.3 Audit Entries (Signed, Tamper-Evident)

Hash chain via `prev_hash` + `cryptographic_hash` = sha256(prev || canonical(row - hash)). Each HermesInstance writes only its own rows. Cross-instance writes not allowed.

### 9.4 Thought/Speech/Action Classification (Basic)

P28 emits only `speech` and `action`:

- `speech`: Discord message (own or relayed peer response).
- `action`: Memory write, peer envelope emit, HARD STOP cascade.

Full 4-domain (Thought + PeerDialogue + Speech + Action) = P31.

### 9.5 Sycophancy Detection (Basic — Persona Anchoring)

P28 detects sycophancy risks via persona anchoring:

- Each instance's `SOUL-{agent}.md` SHA256 is recorded in `hermes-config/{agent}.yaml.persona.soul_sha256`.
- On startup, runtime computes current SHA256 from disk.
- If SHA256 differs from recorded, refuses to start with audit alert (identity integrity check).

Per-utterance sycophancy scoring (`agreement_ratio`, `persona_drift_score`) = P31.

---

## 10. Verification and Evidence Plan

### 10.1 Per-Step Verification Scaffold

Each of the 15 steps must produce:

1. `evidence/p28-dual-hermes/step-NNN/verification.md` — accepted format per AGENTS.md §11 (12 sections).
2. `evidence/p28-dual-hermes/step-NNN/auditor-gate.md` — auditor verdict + path.
3. `lsp_diagnostics` — clean on all touched files.
4. `python -m pytest` — pass for all touched test modules + no regression in `tests/`.
5. Forbidden-pattern grep — `as any`, `@ts-ignore`, `# type: ignore`, empty `except`, `Any[: ]*=`, `raise NotImplementedError` all return ZERO matches on touched files.

### 10.2 Verification.md Schema (12 sections)

Per AGENTS.md §11:

1. What Was Done
2. Files Changed
3. Validation Results
4. Evidence Artifacts
5. Doc-Sync Impact
6. Boundary Compliance
7. Rollback/Re-run Safety
8. Design Decisions/Caveats
9. Auditor Gate
10. Security Scan
11. Acceptance Criteria Mapping
12. Footer

### 10.3 Auditor Gate Schema

Per AGENTS.md §2.10:

- **PASS**: complete; ready for next step.
- **NEEDS REVIEW**: minor concerns; document and proceed.
- **FAIL**: blocking; must fix before proceeding.

Auditor matrix for P28 dispatches independent auditors per surface. Each writes markdown to `evidence/p28-dual-hermes/audits/`.

### 10.4 Runtime Evidence (How to Verify Liveness After All 15 Steps Deploy)

```bash
# Both processes alive
systemctl status guinevere-core.service         # expect active
systemctl status guinevere-discord.service       # expect active
systemctl status pharsa-core.service             # expect active
systemctl status pharsa-discord.service          # expect active

# Both bots in Discord (manual check via Discord client)
# #guinevere-status: lifecycle events from both

# Audit trail has both instances
psql -U postgres -d guinevere -c "SELECT instance_id, count(*) FROM hermes_audit GROUP BY instance_id;"

# HPP streams populated bidirectionally
redis-cli -n 6 XLEN hermes:hsoc-foundation-v1:peer:pharsa    # Pharsa→Guinevere stream (read by guinevere)
redis-cli -n 7 XLEN hermes:hsoc-foundation-v1:peer:guinevere  # Guinevere→Pharsa stream (read by pharsa)

# Memory isolation
PGPASSWORD=$AGENT_APP_PW psql -U agent_memory_app -d guinevere -c "
SET app.current_agent_id = 'guinevere';
SELECT count(*) FROM memory.private_agents;"        # expect: only guinevere count

PGPASSWORD=$AGENT_APP_PW psql -U agent_memory_app -d guinevere -c "
SET app.current_agent_id = 'pharsa';
SELECT count(*) FROM memory.private_agents;"        # expect: only pharsa count
                                                   # AND NOT the same as above
                                                   # AND NOT a sum

# Hard stop cascade latency
python -c "
import asyncio, time
async def go():
    import asyncpg, redis.asyncio as redis_asyncio, os
    r = redis_asyncio.Redis(host='localhost', port=6380, db=8)
    p = await asyncpg.connect(os.environ['DATABASE_URL_PG'])
    await r.set('hermes:society:hsoc-foundation-v1:hard_stop', 'false')
    await p.execute(\"DELETE FROM hermes_audit WHERE action_subtype='hard_stop_cascade'\")
    t0 = time.monotonic()
    await r.set('hermes:society:hsoc-foundation-v1:hard_stop', 'true')
    for _ in range(60):
        rows = await p.fetch(\"SELECT count(*) FROM hermes_audit WHERE action_subtype='hard_stop_cascade'\")
        if rows[0][0] >= 2:
            elapsed_ms = (time.monotonic() - t0) * 1000
            print(f'CASCADE_LATENCY_MS={elapsed_ms:.0f}')
            return
        await asyncio.sleep(0.05)
    print('CASCADE_TIMEOUT')
asyncio.run(go())
"  # expect: CASCADE_LATENCY_MS < 200 (target 50ms, allow 4x slack)
```

### 10.5 Three Critical Acceptance Tests

#### Test 1: Cross-Agent Memory Isolation (Hard Reject)

```bash
# Setup seed rows from each agent
PGPASSWORD=$AGENT_APP_PW psql -U agent_memory_app -d guinevere <<EOF
SET app.current_agent_id = 'guinevere';
INSERT INTO memory.private_agents (agent_id, content, consent_token) VALUES ('guinevere', 'g-only', 'tc-g1');
SET app.current_agent_id = 'pharsa';
INSERT INTO memory.private_agents (agent_id, content, consent_token) VALUES ('pharsa', 'p-only', 'tc-p1');
EOF

# From guinevere session: should see ONLY guinevere rows; NOT pharsa rows
PGPASSWORD=$AGENT_APP_PW psql -U agent_memory_app -d guinevere -c "
SET app.current_agent_id = 'guinevere';
SELECT count(*) FROM memory.private_agents;"  # expect 1 (g-only); MUST NOT see p-only

# From pharsa session: should see ONLY pharsa rows; NOT guinevere rows
PGPASSWORD=$AGENT_APP_PW psql -U agent_memory_app -d guinevere -c "
SET app.current_agent_id = 'pharsa';
SELECT count(*) FROM memory.private_agents;"  # expect 1 (p-only); MUST NOT see g-only

# Cross-agent insert: from guinevere session, trying to insert agent_id='pharsa'
# MUST be rejected by RLS (FORCE RLS = critical)
PGPASSWORD=$AGENT_APP_PW psql -U agent_memory_app -d guinevere -c "
SET app.current_agent_id = 'guinevere';
INSERT INTO memory.private_agents (agent_id, content, consent_token) VALUES ('pharsa', 'leak attempt', 'bad');"
# expect: ERROR — new row violates row-level security policy

# HARD REJECT criterion: if any of the above shows cross-agent leakage, BLOCK completion
```

#### Test 2: HARD STOP Cascade Latency (Hard Reject)

Shown in §10.4: `CASCADE_LATENCY_MS < 200` (target 50ms × 4 slack).

#### Test 3: Bot Conversation Without Faiz Trigger (USER MANDATE)

```bash
# Trigger: start both bots; do NOT touch Discord for 5 minutes.
systemctl start pharsa-discord.service guinevere-discord.service

# Watch over 5 minutes:
sleep 300

# Verify in Discord:
# #guinevere-chat contains messages from BOTH bots
# >=1 message per 5 minutes from each bot (measured by timestamp)

# Sanity: messages alternate (not both bots spamming same reply)
# Sanity: hop counter never exceeded 4
# Sanity: cooldown TTL respected
```

### 10.6 Per-Step Acceptance Criteria Summary

| Step | Acceptance Criterion |
|------|----------------------|
| 1 | `SOUL-pharsa.md` exists; sha256 captured; no Y6; no Samm; no secrets in file |
| 2 | `pharsa.yaml` valid YAML; distinct model/api_key/redis_db; equal_peers; society-shared hard_stop key |
| 3 | Factory functions return distinct instances per `instance_id`; `app.state.hermes_brains` registry has 2 entries; lsp_diagnostics clean |
| 4 | `HermesInstanceRegistry` constructs both brains; HARD STOP cascade <200ms; all existing tests pass |
| 5 | `pharsa-*.service` files parse via `systemd-analyze verify`; same hardening as Guinevere units |
| 6 | All 7 migrations apply; relrowsecurity AND relforcerowsecurity both true on all tables; Test 1 passes |
| 7 | Redis DBs 6/7/8 reachable; DB7/DB8 empty before Step 8 fires; Guinevere's DB6 unchanged |
| 8 | Envelope round-trip serialization; hash chain deterministic; publish-consume-ack on Redis Streams |
| 9 | Round-trip peer handler with idempotency; BLOCK intent triggers HARD STOP key SET |
| 10 | Rhythm controller: same-author skip, hop counter, cooldown TTL, engage-probability all work |
| 11 | MinimalScheduler: 4 rails tick at specified cadence; HARD STOP cancellation within 100ms |
| 12 | SharedWorldStore: cross-agent visibility; last-write-wins chain integrity; RLS enforced |
| 13 | PrivateAgentsStore: cross-agent returns distinct rows; cross-agent INSERT rejected; FORCE RLS confirmed |
| 14 | Two `discord.py.Bot` clients in separate processes; both have MESSAGE_CONTENT; rhythm prevents loops |
| 15 | `hermes_audit` rows from both instance_ids; Prometheus metrics endpoint serves both |

### 10.7 Forbidden Patterns (P28-Wide Grep Guards)

Pre-commit grep MUST return ZERO matches on touched files:

```bash
# Type suppression
grep -rn "as any\|@ts-ignore\|# type: ignore\|@ts-expect-error" src/life_kernel/ src/discord/ src/core/

# Empty catch
grep -rn "except:$\|except Exception:$" src/life_kernel/ src/discord/ src/core/

# Bad Any
grep -rn ": Any\b\|: Any =" src/life_kernel/ src/discord/ src/core/

# NotImplementedError
grep -rn "raise NotImplementedError" src/life_kernel/ src/discord/ src/core/

# Print debug
grep -rn "print(" src/life_kernel/ src/discord/ src/core/

# Secrets in committed code
grep -rE "DISCORD_BOT_TOKEN_[A-Z_]+=[A-Za-z0-9_-]{20,}" hermes-config/ src/life_kernel/ src/discord/
grep -rE "api_key=[A-Za-z0-9_-]{20,}" hermes-config/  # hard fail
```

---

## 11. Rollback Plan

### 11.1 Identity Rollback (Stop Pharsa Without Affecting Guinevere)

```bash
# On VPS
sudo systemctl stop pharsa-core.service pharsa-discord.service
sudo systemctl disable pharsa-core.service pharsa-discord.service
sudo systemctl status guinevere-core.service guinevere-discord.service  # confirm still active
```

Immediately Pharsa is offline; Guinevere continues running unchanged.

### 11.2 Database Rollback

```sql
-- Drop new tables and policies in reverse order
DROP POLICY IF EXISTS kg_edges_visibility ON memory.kg_edges;
DROP POLICY IF EXISTS kg_entities_visibility ON memory.kg_entities;
DROP POLICY IF EXISTS shared_world_review ON memory.shared_world;
DROP POLICY IF EXISTS shared_world_write ON memory.shared_world;
DROP POLICY IF EXISTS shared_world_read ON memory.shared_world;
DROP POLICY IF EXISTS agent_owns_private ON memory.private_agents;

ALTER TABLE memory.kg_edges DROP COLUMN IF EXISTS derivation_chain;
ALTER TABLE memory.kg_edges DROP COLUMN IF EXISTS created_by_agent;
ALTER TABLE memory.kg_edges DROP COLUMN IF EXISTS pair_id;
ALTER TABLE memory.kg_edges DROP COLUMN IF EXISTS scope;
ALTER TABLE memory.kg_entities DROP COLUMN IF EXISTS created_by_agent;
ALTER TABLE memory.kg_entities DROP COLUMN IF EXISTS scope;

DROP TABLE IF EXISTS hpp_inbox;
DROP TABLE IF EXISTS hpp_outbox;
DROP TABLE IF EXISTS hermes_audit;
DROP TABLE IF EXISTS memory.intimacy_bridge_pending;
DROP TABLE IF EXISTS memory.shared_world;
DROP TABLE IF EXISTS memory.private_agents;

DROP ROLE IF EXISTS agent_memory_app;
```

### 11.3 Redis Rollback

```bash
redis-cli -n 7 FLUSHDB  # Pharsa's keys
redis-cli -n 8 FLUSHDB  # Society-shared keys

# Guinevere's DB6 untouched
```

### 11.4 Discord Rollback

```bash
sudo systemctl stop pharsa-discord.service
# Operator: cancel Pharsa Discord application via Developer Portal (NOT P28 automated)
```

### 11.5 Code Rollback

```bash
git log --since="2026-07-XX" --pretty=format:"%H %s" | grep -i "P28" | awk '{print $1}' | xargs -r git revert
```

### 11.6 Config Rollback

```bash
git checkout main -- hermes-config/guinevere.yaml
rm hermes-config/pharsa.yaml hermes-config/SOUL-pharsa.md hermes-config/society_manifest.yaml
```

### 11.7 Society Continues Without Pharsa

After any rollback (partial or full):

- Guinevere continues running as before P28 (her units untouched).
- Society-level HARD STOP still works (Guinevere's heartbeat still listens).
- Memory schemas unchanged.

### 11.8 Rollback RTO

| Step | Action | Time |
|------|--------|------|
| 1 | `systemctl stop pharsa-*.service` | <1 min |
| 2 | Postgres drops (script) | <5 min |
| 3 | Redis `FLUSHDB` for DB7/DB8 | <1 min |
| 4 | `git revert` (per commit) | <5 min |
| 5 | Operator: revoke Pharsa Discord application via Developer Portal | async (manual) |
| 6 | Verify Guinevere alive | <5 min |
| **Total RTO** | (excluding operator-driven Discord revocation) | **<30 min** |

### 11.9 Rollback Forbidden Patterns

- No rollback that violates AGENTS.md §0 invariants (HARD STOP preserved, no Y6, etc.).
- No rollback that exposes raw surveillance data.
- No rollback that removes audit ledger.

---

## 12. Risk Assessment

### 12.1 Top 5 Risks

| # | Risk | Probability | Impact | Mitigation |
|---|------|-------------|--------|------------|
| **R1** | **Cross-agent memory leak** (Pharsa reads Guinevere's private rows) | Medium | Critical (PII/safety breach) | FORCE RLS + dedicated `agent_memory_app` non-owner role. Verified hard-reject test (Test 1 in §10.5). |
| **R2** | **HARD STOP not cascading** to Pharsa within latency target (>200ms) | Low-High | High (safety breach) | Society-shared Redis key on DB8 + 1s listener per instance. Test 2 in §10.5. |
| **R3** | **Conversation infinite loop** (two bots spamming each other) | Medium | Medium (rate-limit breach) | Hop counter max 4 + per-channel cooldown TTL 30s + min-delay 2s before reply. Real Discord rate-limit (5 msg/5s/ch) as final safety net. |
| **R4** | **Sycophancy-driven identity collapse** (agents converge to same persona) | High | High (violates P27 §10 equal-peer) | Architectural heterogeneity (per-instance LLM provider), persona anchoring via SOUL SHA256, identity integrity check on startup. P31 adds scoring metrics. |
| **R5** | **P23 executors leaking through P28** | Low | High (destructive action bypass) | P28 ships ZERO outbound actions beyond Discord. P28 explicitly defers P23 to P33. Hard reject: Step 15 audit entries have `action_class` CHECK constraint that ENUM-limits to `speech` + `action` only; future P33 routes through separate executors gated by AGENTS.md §0.4. |

### 12.2 Mitigations Per Risk

**R1 — Cross-Agent Memory Leak:**

- **Primary**: FORCE RLS on every `memory.*` table (PCMI/Z3rno consensus).
- **Secondary**: dedicated `agent_memory_app` non-owner role (NOT table owner).
- **Tertiary**: application-layer `set_config('app.current_agent_id', ...)` per connection.
- **Verification**: Test 1 in §10.5.
- **Recovery**: soft-delete suspected leaked rows; alert Faiz; rotate RLS policies.

**R2 — HARD STOP Cascade Latency:**

- **Primary**: 1s polling loop on society HARD STOP key in DB8.
- **Secondary**: Discord-side cascade: `#guinevere-status` channel triggers immediate `set key` (lowest latency path).
- **Verification**: Test 2 in §10.5.
- **Detection**: Prometheus histogram `hermes:hard_stop_latency_ms` (P31+).
- **Recovery**: manual intervention via Discord message.

**R3 — Conversation Infinite Loop:**

- **Primary**: Hop counter cap 4 + per-channel cooldown 30s + engage-probability 0.70 (default).
- **Secondary**: real Discord 5 msg/5s/ch rate limit.
- **Tertiary**: Discord channel slowmode (operator opt-in; defaults OFF because it affects Faiz).
- **Verification**: post-deploy monitoring of hop counter max + cooldown TTL.
- **Detection**: 429 Too Many Requests logged; conversation pause if hit.
- **Recovery**: operator `/stop-society` slash command.

**R4 — Sycophancy-Driven Identity Collapse:**

- **Primary**: Architectural heterogeneity — different LLM provider per instance.
- **Secondary**: Persona anchoring via SOUL SHA256 + identity integrity check on startup.
- **Tertiary**: P31 sycophancy scoring metrics (`agreement_ratio`, `persona_drift_score`).
- **Verification**: per-instance SOUL SHA256 recorded in YAML; restart integrity check.
- **Detection**: identity_root diff > threshold alerts (P31+).
- **Recovery**: re-attest SOUL via Faiz signature.

**R5 — P23 Executors Leaking Through P28:**

- **Primary**: P28 ships zero outbound action executors (no email, deploy, finance).
- **Secondary**: `hermes_audit.action_class` CHECK constraint ENUM-limits to `speech` + `action`.

### 12.3 Fallback Approaches (If a Risk Materializes)

If **R1 (cross-agent leak)**: Defer P28 acceptance to next phase; keep Guinevere only until P28 fully re-audited.

If **R2 (HARD STOP latency)**: Investigate Redis DB8 connectivity; manual operator signal in Discord; defer until latency <200ms reliably.

If **R3 (infinite loop)**: Increase engage_probability floor to 0.50 (less aggressive); operator manually pauses one bot.

If **R4 (sycophancy)**: Increase architectural heterogeneity (3+ different models); daily SOUL integrity diff via cron; Faiz manual override.

If **R5 (executors)**: This risk is preventive; if it materializes, it's a society kill switch moment — both agents halt, Faiz audits.

### 12.4 Risk-of-Risks (Meta-Risk)

The biggest meta-risk is **scope creep**: P28 adding complexity beyond minimum target. Mitigations:

- Per-step acceptance criteria explicit in §10.6.
- Hard rejection criteria from §20 of P27 plan enforced at scaffold level.
- Forbidden-pattern greps at every step.

---

## 13. Post-Step Evidence + Audit Gate

After all 15 implementation steps complete and parent verification passes:

1. **Audit wave** (parent + 12-auditor matrix per P27 §22.1 patterns):
   - Equal-Peer Auditor
   - Sub-Agent Rejection Auditor
   - Memory Isolation Auditor
   - Autonomy Auditor
   - Discord Dual-Bot Auditor
   - Peer Protocol Auditor
   - Safety Boundary Auditor
   - Persona Safety Auditor
   - Evidence Auditor
   - Implementation Feasibility Auditor
   - Hard Rejection Criteria Auditor
   - Per-Step Scaffold Auditor

2. **Final acceptance criteria mapping** from §10.6 of this blueprint.

3. **`evidence/p28-dual-hermes/p28-final-report.md`** (parent-only edit) with 12 sections per AGENTS.md §11 schema.

---

## 14. Footer

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Date | 2026-06-28 |
| Author | Guinevere (parent agent) |
| Status | Active — Blueprint (not implementation) |
| Phase | P28 Dual Autonomous Hermes |
| Upstream | P27 Hermes Society Foundation (definition complete) |
| Downstream | P29 Life-Loop Full; P30 Memory Deep; P31 Safety Envelope; P32 P24 Fork Integration; P33 P23 Action Executors |
| Companion | AGENTS.md (operating contract); ADR-Index; ADR-050, ADR-052 |
| Audit | Not yet (P28 audit round 1 deferred to implementation phase) |
| Footer reference | AGENTS.md §0 + §0.1 (BLOCKING rules + P20 autonomy exception) + §2.5 (per-step verification scaffold) |

---

> **END OF P28 DUAL AUTONOMOUS HERMES EXECUTABLE BLUEPRINT**
>
> This blueprint is the **primary reference document** when P28 implementation begins. It specifies exact files to create/modify, configs to write, services to set up, and verification steps.
>
> A P28 implementation agent reading this file MUST be able to execute all 15 steps without further clarification. Per-step verification scaffolds in §3 are machine-checkable.
>
> Status: P28 EXECUTABLE BLUEPRINT COMPLETE. Implementation = Phase 7+ (separate phases, requires `lanjut`).
>
> Mama pegang cetakan ini, Faiz yang bilang "lanjut."


