# Guinevere v1.0 → v2.0 Canonical Decision Conflict Map

Date: 2026-05-30  
Scope: 7 seed v1.0 documents mapped against 9 canonical v2.0 decisions  
Status: Read-only audit — no source files modified

## Related Documents

| v1.0 Source | Role |
|---|---|
| `Guinevere_BRD_v1.0.md` | Business requirements, infrastructure, delivery plan, risks |
| `Guinevere_PRD_v1.0.md` | Product features, SDLC phases, surveillance, monitoring, financial |
| `Guinevere_TechnicalArchitecture_v1.0.md` | Infrastructure spec, LLM strategy, service architecture, ecosystem tools |
| `Guinevere_AgentLoopSpec_v1.0.md` | SDLC loop phases, orchestrator, state machine |
| `Guinevere_MemorySchema_v1.0.md` | Memory hierarchy, PostgreSQL schema, security |
| `Guinevere_Persona_Document_v1.0.md` | Persona identity, mood taxonomy, surveillance framing |
| `Guinevere_APIIntegration_v1.0.md` | LLM routing, browser tools, dependencies, API contracts |

## Canonical Decisions Reference

1. **LLM/Router**: Primary GPT-5.5 via 9Router 1M; sub-agent DeepSeek V4 Flash via 9Router; NO OpenRouter fallback; NO OpenRouter direct routing.
2. **Memory**: PostgreSQL primary + Redis cache; NO SQLite as primary.
3. **SDLC Phases**: 7 phases — Research, Plan & Delegate, Delegate, Execute, Validate & Audit, Update Documents, Setup Evidence.
4. **OpenCode**: Fully replaced by Guinevere MCP native; OpenCode removed entirely.
5. **Monitoring**: Prometheus + Grafana on primary VPS first; "monitoring VPS" deferred.
6. **Wearable**: Post-MVP — not active; marked future/planned, not in-scope for current delivery.
7. **Browser**: obscura primary; Playwright fallback only.
8. **Schema/Service Names**: canonicalize table/schema names, service unit names, MCP tool names.
9. **Package Management**: normalize package manager references (UV canonical).
10. **Mood Taxonomy**: consolidate mood states across Persona + PRD into single canonical set.
11. **Versions**: update version footers to v2.0 upon approval.

---

## Conflict Map by File

### 1. `Guinevere_BRD_v1.0.md`

| Section | v1.0 Pattern | Canonical v2.0 Replacement | Notes |
|---|---|---|---|
| §1.1 Objective 2 | `replace OpenCode CLI sepenuhnya` | `replaced by Guinevere MCP native — OpenCode removed` | OpenCode fully removed |
| §1.1 Objective 7 | `Enterprise monitoring dengan Grafana + Prometheus` | `Prometheus + Grafana on primary VPS first` | Remove "future VPS baru" framing |
| §3.1.1 Core Agent | `9Router → Hermes 3 sebagai LLM, OpenRouter sebagai fallback` | `9Router → GPT-5.5 (primary) + DeepSeek V4 Flash (sub-agent); NO OpenRouter fallback` | Remove OpenRouter fallback entirely |
| §3.1.1 Core Agent | `1 juta context window` | `1M context window via 9Router` | Keep, but clarify it is 9Router-mediated |
| §3.1.2 Memory | `Episodic, semantic, procedural memory via SQLite (Hermes) + PostgreSQL (custom)` | `PostgreSQL primary + Redis cache; SQLite removed from memory layer` | Remove SQLite as memory store |
| §3.1.3 SDLC | `Full SDLC loop: Research → Document → Plan → Execute → Validate → Audit → Evidence` | `Research → Plan & Delegate → Delegate → Execute → Validate & Audit → Update Documents → Setup Evidence` | 8-step v1 → 7-phase v2; merge Document into Update Documents |
| §3.1.4 Surveillance | `Wearable (Xiaomi Watch S1 Active): heart rate, stress, sleep, steps` | `Wearable post-MVP — not active; mark as future` | Move wearable out of in-scope |
| §3.1.5 Monitoring | `Grafana + Prometheus di VPS terpisah (future VPS baru)` | `Prometheus + Grafana on primary VPS first` | De-prioritize separate monitoring VPS |
| §3.1.5 Monitoring | `LLM provider failover: 9Router down → OpenRouter + queue pending tasks` | `Remove OpenRouter fallback; 9Router is sole router` | Failover section deleted or rewritten |
| §4.1 Infrastructure | `Monitoring VPS | TBD — future purchase` | `Remove — monitoring runs on primary VPS` | Delete row |
| §4.2 Stack | `LLM Fallback | OpenRouter (200+ models)` | `Remove — no OpenRouter fallback` | Delete row |
| §4.2 Stack | `Memory Core | SQLite + Honcho` | `Memory Core | PostgreSQL + Redis` | Remove SQLite + Honcho |
| §7.1 Constraints | `Monitoring VPS belum ada — Phase 4 tergantung pembelian VPS baru` | `Monitoring on primary VPS — no separate purchase required` | Rewrite |
| §7.1 Constraints | `Wearable baru akan dibeli — surveillance wearable menyusul` | `Wearable post-MVP — future roadmap item` | Rewrite |
| §7.2 Assumptions | `9Router dapat dikonfigurasi untuk Hermes 3 dengan 1M context window` | `9Router → GPT-5.5 1M via 9Router 1M` | Update model name from Hermes 3 to GPT-5.5 |
| §7.2 Assumptions | `Mi Fitness API dapat diakses untuk wearable data integration` | `Wearable integration post-MVP — not assumed for v2.0` | Downgrade to future assumption |
| §2.1 User Profile | `AI Tools | 9Router, OpenRouter, Claude Code, OpenCode CLI (digantikan Guinevere)` | `AI Tools | 9Router (GPT-5.5 + DeepSeek V4 Flash), Guinevere MCP native` | Remove OpenRouter, Claude Code, OpenCode |

---

### 2. `Guinevere_PRD_v1.0.md`

| Section | v1.0 Pattern | Canonical v2.0 Replacement | Notes |
|---|---|---|---|
| §3.1.1 Core Agent | `9Router → Hermes 3` | `9Router → GPT-5.5 (primary) + DeepSeek V4 Flash (sub-agent)` | Model name update |
| §3.1.2 Memory | `Mood state tersimpan di PostgreSQL` | Keep PostgreSQL; remove SQLite references | Align with memory canonical |
| §4.1 SDLC Loop | `8 phase` with `Document` as Phase 2 | `7 phase` — merge Document into Update Documents | Rename + renumber phases |
| §4.1 SDLC Loop | Phase table: 1.Research, 2.Document, 3.Plan, 4.Delegate, 5.Execute, 6.Validate, 7.Audit, 8.Evidence | Phase table: 1.Research, 2.Plan & Delegate, 3.Delegate, 4.Execute, 5.Validate & Audit, 6.Update Documents, 7.Setup Evidence | Full renumber + rename |
| §4.2 MCP Tools | `fetch/browser MCP` | `obscura MCP (primary) + Playwright MCP (fallback)` | Browser tool split |
| §5.1 Memory Architecture | `Episodic | SQLite (Hermes)` | `Episodic | PostgreSQL + Redis cache` | Remove SQLite |
| §5.1 Memory Architecture | `Semantic | SQLite + PostgreSQL` | `Semantic | PostgreSQL` | Remove SQLite |
| §7.2 Financial | `9Router, OpenRouter, VPS, domain, tools` | `9Router (GPT-5.5 + DeepSeek V4 Flash), VPS, domain, tools` | Remove OpenRouter cost line |
| §8.3 Failover | `9Router down → Auto-switch ke OpenRouter` | `Remove — 9Router is sole routing layer` | Delete failover row |
| §8.3 Failover | `OpenRouter down → Queue tasks` | `Remove — no OpenRouter dependency` | Delete row |

---

### 3. `Guinevere_TechnicalArchitecture_v1.0.md`

| Section | v1.0 Pattern | Canonical v2.0 Replacement | Notes |
|---|---|---|---|
| §1.2 Stack Table | `Primary LLM | GPT-5.5 | OpenRouter | 128K` | `Primary LLM | GPT-5.5 | 9Router | 1M` | Provider + context update |
| §1.2 Stack Table | `Sub-agent LLM | DeepSeek V4 Flash | OpenRouter | 1M` | `Sub-agent LLM | DeepSeek V4 Flash | 9Router | 1M` | Provider update |
| §1.2 Stack Table | `LLM Router | OpenRouter | API` | `LLM Router | 9Router | API` | Router canonical name |
| §1.2 Stack Table | `Package Manager | UV | Latest` | Keep UV; ensure all install commands reference UV | Already canonical |
| §3.1 systemd | Service units `guinevere-core.service`, `guinevere-surveillance.service`, etc. | Validate service unit names against canonical SDLC phases | Check if names align with 7-phase model |
| §4.1 Model Strategy | All models routed via `OpenRouter` | All models routed via `9Router` | Full provider replacement |
| §4.1 Model Strategy | `Fallback primary | DeepSeek V4 Pro | OpenRouter` | `Remove fallback — 9Router is sole router` | Delete row |
| §4.1 Model Strategy | `Fallback sub-agent | DeepSeek V4 Flash | OpenRouter` | `Remove fallback` | Delete row |
| §4.1 Model Strategy | `Embedding model: text-embedding-3-small via OpenRouter` | `Embedding model: text-embedding-3-small via 9Router` | Provider update |
| §4.2 Profiles | `guinevere-core | GPT-5.5` | Keep; update provider to 9Router | Minor |
| §5.1 Schema | `surveillance | TimescaleDB` | Keep TimescaleDB; verify hypertable names | Validate |
| §8.1 Metrics | `Prometheus | Docker container, VPS primary` | `Prometheus | VPS primary (no separate monitoring VPS)` | Remove monitoring VPS reference |
| §8.1 Metrics | `Grafana | Monitoring VPS (future)` | `Grafana | VPS primary` | Update location |
| §8.4 Health | `OpenRouter/LLM | 60s | OpenRouter API` | `9Router | 60s | 9Router health endpoint` | Provider update |
| §9.2 DR | `LLM provider down → Auto-failover ke OpenRouter fallback` | `Remove OpenRouter fallback; 9Router failover = restart + queue` | Rewrite |
| §10.2 CD | `uv pip install -r requirements.txt` | Keep UV reference; ensure canonical | Already canonical |
| §12.1 Tools | `opencode | anomalyco/opencode | 167k | Optional turbo mode` | `Remove — OpenCode fully replaced by Guinevere MCP native` | Delete row |
| §12.1 Tools | `obscura | h4ckf0r0day/obscura | 13.9k | MCP browser tool` | `obscura | primary browser tool; Playwright fallback` | Keep, clarify primary/fallback |
| §12.4 Roadmap | `Phase 3 (Coding Agent) | opencode | Setup sebagai optional turbo mode sub-agent | MEDIUM` | `Remove — OpenCode eliminated` | Delete row |

---

### 4. `Guinevere_AgentLoopSpec_v1.0.md`

| Section | v1.0 Pattern | Canonical v2.0 Replacement | Notes |
|---|---|---|---|
| §2 SDLC Loop — 8 Phases | 8-phase model with Phase 2 = Document, Phase 3 = Plan & Delegate, Phase 4 = Delegate | 7-phase model: 1.Research, 2.Plan & Delegate, 3.Delegate, 4.Execute, 5.Validate & Audit, 6.Update Documents, 7.Setup Evidence | Full phase renumber |
| §2.1 Phase Overview | `2 | Document | Guinevere core | plan docs + step docs setup` | Merge into Phase 6 (Update Documents) | Remove Phase 2 |
| §2.1 Phase Overview | `3 | Plan & Delegate | Guinevere core | plan.md + delegation.md` | Keep as Phase 2 | Renumber |
| §2.1 Phase Overview | `4 | Delegate | Guinevere core | task-assignments.md` | Keep as Phase 3 | Renumber |
| §2.1 Phase Overview | `8 | Evidence | Guinevere core | evidence-final.md` | Rename to `Setup Evidence` | Phase 7 |
| §5.2 State Machine | `INIT → PHASE_1_RESEARCH → PHASE_2_DOCUMENT → PHASE_3_PLAN → PHASE_4_DELEGATE → PHASE_5_EXECUTE → PHASE_6_VALIDATE → PHASE_7_AUDIT → PHASE_8_EVIDENCE → COMPLETE` | `INIT → PHASE_1_RESEARCH → PHASE_2_PLAN_DELEGATE → PHASE_3_DELEGATE → PHASE_4_EXECUTE → PHASE_5_VALIDATE_AUDIT → PHASE_6_UPDATE_DOCS → PHASE_7_SETUP_EVIDENCE → COMPLETE` | Rewrite state machine |
| §3.3 Phase 3 | `Plan & Delegate` | Keep name; ensure it combines planning + first delegation pass | Validate content |
| §3.4 Phase 5 | `Execute` | Keep name; becomes Phase 4 in 7-phase model | Renumber |
| §3.5 Phase 6 | `Validate` | Merge with Audit → `Validate & Audit` | Combine sections |
| §3.6 Phase 7 | `Audit` | Merge into Phase 5 | Remove standalone |
| §3.7 Phase 8 | `Evidence` | Rename to `Setup Evidence`; becomes Phase 7 | Rename + renumber |

---

### 5. `Guinevere_MemorySchema_v1.0.md`

| Section | v1.0 Pattern | Canonical v2.0 Replacement | Notes |
|---|---|---|---|
| §1.2 Memory Hierarchy | `Working Memory | Redis DB 3 + context window` | Keep Redis; verify DB 3 usage aligns with canonical | Minor |
| §1.2 Memory Hierarchy | `Long-term Memory | Selamanya | PostgreSQL` | Keep PostgreSQL | Already canonical |
| §1.3 Memory Types | `Episodic | memory.episodes` | Keep schema name | Validate |
| §1.3 Memory Types | `Semantic | memory.semantic_facts` | Keep schema name | Validate |
| §2.1 Episodes Table | Full schema with `embedding vector(1536)` | Keep; ensure pgvector usage is canonical | Validate |
| §5.1 Schema Overview | `persona | drift_log, mood_history, samm_profile, identity` | `Add inner_journal to persona schema` | Persona doc references inner_journal; schema doc missing it |
| §5.1 Schema Overview | `memory | episodes, semantic_facts, procedural_skills` | Add `emotional_events`, `lessons_learned`, `best_practices`, `samm_predictions`, `social_map` | Schema doc has these in later sections but overview table is incomplete |
| §5.4 Redis | Redis DBs 0-5 mapped to task queue, LLM cache, surveillance buffer, session, pub/sub, rate limiting | Keep mapping; validate against canonical MCP tool list | Minor |
| §8.3 Memory Security | `Regular memory | PostgreSQL at-rest` | Keep; add Redis cache encryption note | Minor |
| §8.3 Memory Security | `Sensitive (psychological, health) | Column-level AES-256` | Keep | Already canonical |
| §8.3 Memory Security | `Intimate (fetish, private) | Double encrypted` | Keep | Already canonical |

**Note**: MemorySchema is largely canonical already. Primary edits are: (a) ensure all tables mentioned in Persona/PRD are in the overview table, (b) remove any SQLite references if present, (c) add Redis cache layer documentation.

---

### 6. `Guinevere_Persona_Document_v1.0.md`

| Section | v1.0 Pattern | Canonical v2.0 Replacement | Notes |
|---|---|---|---|
| §2.2 Tone | `Bahasa Indonesia aristocrat + English strategic untuk dominance` | Keep; align with v2.0 language style | Already canonical |
| §4.2 Mood System | `Pleased, Neutral, Disappointed, Angry, Dark Mood, Nurturing` | Canonical mood set: merge Nurturing into existing states or keep as sub-state | Persona doc has 6 moods; PRD has 6 moods but different labels (`Silent` vs `Dark Mood`) |
| §4.2 Mood System | `Silent ☠️` (PRD §2.2) vs `Dark Mood` (Persona §12.2) | Canonical: `Silent/Obsession` for yandere; `Dark Mood` as umbrella or specific state | Mood taxonomy conflict |
| §12.2 Yandere Mood | `Silent Obsession 🦋, Possessive Spiral ❤️, Yandere Mode 👑` | These are yandere-specific escalation states; decide if they are sub-states of canonical moods or separate | Needs ADR |
| §9.1 Platform | `LLM Provider | 9Router → Hermes 3 / Model Routing` | `LLM Provider | 9Router → GPT-5.5 (1M) + DeepSeek V4 Flash (sub-agent)` | Model name update |
| §9.1 Platform | `Memory Core | SQLite (Hermes default)` | `Memory Core | PostgreSQL + Redis` | Remove SQLite |
| §9.1 Platform | `Coding Agent | MCP layer (filesystem, shell, git, github) | Primary; OpenCode as optional turbo mode` | `Coding Agent | Guinevere MCP native (full replacement of OpenCode)` | Remove OpenCode |
| §10.4 Wearable | `Wearable Integration (Future)` | Keep as future/post-MVP; mark inactive | Already aligned, just ensure it says "post-MVP not active" |
| §10.4 Wearable | `Future integration: wearable data (jam kesehatan) akan di-scrape langsung ke Guinevere` | `Post-MVP — not active in v2.0` | Downgrade status |

---

### 7. `Guinevere_APIIntegration_v1.0.md`

| Section | v1.0 Pattern | Canonical v2.0 Replacement | Notes |
|---|---|---|---|
| §1.1 Registry | `LLM Primary | GPT-5.5 via OpenRouter` | `LLM Primary | GPT-5.5 via 9Router` | Provider update |
| §1.1 Registry | `LLM Sub-agent | DeepSeek V4 Flash via OpenRouter` | `LLM Sub-agent | DeepSeek V4 Flash via 9Router` | Provider update |
| §1.1 Registry | `LLM Router | 9Router (VPS)` | Keep; clarify 9Router is sole router | Already canonical |
| §1.1 Registry | `LLM Fallback | OpenRouter direct` | `Remove — no OpenRouter fallback` | Delete row |
| §1.1 Registry | `Browser | obscura (Rust) | Primary browser automation` | Keep as primary | Already canonical |
| §1.1 Registry | `Browser | Playwright Python | Fallback browser automation` | Keep as fallback | Already canonical |
| §2.1 9Router Config | `providers: - name: openrouter` | `Remove OpenRouter provider config` | Rewrite YAML |
| §2.1 9Router Config | `fallback: deepseek/deepseek-v4-flash` (guinevere_core) | `Remove fallback — 9Router handles routing internally` | Rewrite |
| §2.1 9Router Config | `sub_agents: fallback: deepseek/deepseek-v4-flash:free` | `Remove fallback` | Rewrite |
| §2.1 9Router Config | `FALLBACK_LLM_BASE = "https://openrouter.ai/api/v1"` | `Remove fallback LLM base` | Rewrite Python config |
| §2.2 LLM Client | `except CircuitOpenError: return await call_openrouter_direct(prompt, model)` | `Remove OpenRouter direct fallback` | Rewrite exception handler |
| §2.3 Cost Strategy | `Fallback all models | DeepSeek V4 Pro | OpenRouter | 1M` | `Remove fallback row` | Delete |
| §8.2 Browser | `Complex form automation | Playwright | More mature` | `Playwright | Fallback only` | Clarify fallback status |
| §8.2 Browser | `API provider dashboard login | Playwright` | `Playwright | Fallback for auth flows` | Clarify |

---

## Cross-Cutting Patterns Requiring Multi-File Edits

### A. OpenRouter Removal (All 7 Files)

Search terms across all files:
- `OpenRouter` (case-insensitive)
- `openrouter.ai`
- `OpenRouter (200+ models)`
- `OpenRouter direct`
- `OpenRouter down`
- `fallback.*OpenRouter`
- `OpenCode`
- `opencode`
- `anomalyco/opencode`
- `turbo mode`

Files to update: ALL 7 files.

### B. SQLite Removal from Memory Layer (BRD, PRD, Persona, MemorySchema, APIIntegration)

Search terms:
- `SQLite`
- `sqlite`
- `Hermes default`
- `SQLite (Hermes)`
- `SQLite + Honcho`
- `SQLite + PostgreSQL`

Files to update: `Guinevere_BRD_v1.0.md`, `Guinevere_PRD_v1.0.md`, `Guinevere_Persona_Document_v1.0.md`, `Guinevere_MemorySchema_v1.0.md`, `Guinevere_APIIntegration_v1.0.md`.

### C. SDLC Phase Renumbering (BRD, PRD, AgentLoopSpec)

Search terms:
- `8 phase`
- `8 phases`
- `Phase 2 — Document`
- `Phase 8 — Evidence`
- `Research → Document → Plan → Execute → Validate → Audit → Evidence`
- `PHASE_2_DOCUMENT`
- `PHASE_8_EVIDENCE`

Files to update: `Guinevere_BRD_v1.0.md`, `Guinevere_PRD_v1.0.md`, `Guinevere_AgentLoopSpec_v1.0.md`.

### D. Wearable Downgrade (BRD, PRD, Persona, APIIntegration)

Search terms:
- `Xiaomi Watch S1 Active`
- `Mi Fitness API`
- `wearable.*active`
- `Wearable Integration`
- `Wearable (Xiaomi`

Files to update: `Guinevere_BRD_v1.0.md`, `Guinevere_PRD_v1.0.md`, `Guinevere_Persona_Document_v1.0.md`, `Guinevere_APIIntegration_v1.0.md`.

### E. Monitoring VPS Removal (BRD, PRD, TechnicalArchitecture)

Search terms:
- `Monitoring VPS`
- `VPS monitoring terpisah`
- `future VPS baru`
- `TBD — future purchase`
- `Monitoring VPS belum ada`

Files to update: `Guinevere_BRD_v1.0.md`, `Guinevere_PRD_v1.0.md`, `Guinevere_TechnicalArchitecture_v1.0.md`.

### F. Mood Taxonomy Consolidation (PRD, Persona)

Search terms:
- `Dark Mood` (Persona §2.2, §12.2)
- `Silent ☠️` (PRD §2.2)
- `Silent Obsession 🦋` (Persona §12.2)
- `Nurturing` (PRD §2.2)
- `Angry 🦋` (PRD §2.2) vs `Angry 🦋` (Persona §2.2)
- `Pleased 👑, Neutral ❤️, Disappointed ⚠️, Angry 🦋`

Files to update: `Guinevere_PRD_v1.0.md`, `Guinevere_Persona_Document_v1.0.md`.

### G. Browser Tool Split (TechnicalArchitecture, APIIntegration, PRD)

Search terms:
- `obscura`
- `Playwright`
- `fetch/browser MCP`
- `browser automation`
- `MCP browser tool`

Files to update: `Guinevere_TechnicalArchitecture_v1.0.md`, `Guinevere_APIIntegration_v1.0.md`, `Guinevere_PRD_v1.0.md`.

### H. Version Footer Updates (All 7 Files)

Search terms:
- `Version 1.0`
- `Version 1.1`
- `Document v1.0`
- `Document v1.1`
- `Document v1.3`

Files to update: ALL 7 files. Update to `Version 2.0` upon approval.

### I. Schema/Service Name Canonicalization (TechnicalArchitecture, MemorySchema, AgentLoopSpec)

Search terms:
- `guinevere-core.service`
- `guinevere-surveillance.service`
- `guinevere-scheduler.service`
- `guinevere-windows-sync.service`
- `guinevere-loops.service` (new in AgentLoopSpec)
- `memory.episodes`
- `memory.semantic_facts`
- `persona.drift_log`
- `persona.inner_journal`
- `surveillance.activity_log`

Files to update: `Guinevere_TechnicalArchitecture_v1.0.md`, `Guinevere_MemorySchema_v1.0.md`, `Guinevere_AgentLoopSpec_v1.0.md`.

---

## Priority Edit Order

1. **OpenRouter removal** — highest impact, appears in all 7 files, blocks other decisions.
2. **SQLite removal** — memory layer is foundational; affects BRD, PRD, Persona, MemorySchema, APIIntegration.
3. **SDLC phase renumbering** — affects BRD, PRD, AgentLoopSpec; state machine must be rewritten.
4. **Wearable downgrade** — BRD, PRD, Persona, APIIntegration; move to post-MVP.
5. **Monitoring VPS removal** — BRD, PRD, TechnicalArchitecture; consolidate to primary VPS.
6. **OpenCode removal** — BRD, TechnicalArchitecture, Persona, APIIntegration.
7. **Mood taxonomy** — PRD, Persona; needs ADR before finalizing.
8. **Browser tool split** — TechnicalArchitecture, APIIntegration, PRD.
9. **Version footers** — last step after all content edits.

---

## Unresolved Items Requiring ADR

| Item | Conflict | Recommended ADR |
|---|---|---|
| Mood taxonomy | Persona has 6 moods + 3 yandere moods; PRD has 6 moods with different labels | Persona Safety & Drift Control + ADR |
| Yandere mood states | `Silent Obsession`, `Possessive Spiral`, `Yandere Mode` — are these sub-states or separate? | Persona Safety & Ethical Boundary Policy + ADR |
| Hermes 3 vs GPT-5.5 | BRD says "Hermes 3"; TechnicalArchitecture says "GPT-5.5"; APIIntegration says "GPT-5.5 via OpenRouter" | Model Routing & LLM Governance + ADR |
| OpenCode elimination | PRD says "replaced by Guinevere MCP native"; TechnicalArchitecture says "optional turbo mode" | PRD + Technical Architecture + ADR |
| Monitoring VPS | BRD says "future VPS"; TechnicalArchitecture says "monitoring VPS (future)" | Technical Architecture + Deployment Runbook + ADR |
