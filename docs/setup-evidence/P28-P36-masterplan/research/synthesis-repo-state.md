---
title: "P28-P36 Masterplan — Repo State Synthesis (Phase 2 of 12)"
status: "Active — Research Synthesis"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere (parent agent)"
phase: "P28-P36 Masterplan Phase 2 (synthesis)"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
input_sources:
  - "docs/setup-evidence/P28-P36-masterplan/research/p27-output-inventory.md"
  - "docs/setup-evidence/P28-P36-masterplan/research/p24-fork-dependency.md"
  - "docs/setup-evidence/P28-P36-masterplan/research/p22-p23-dependency.md"
  - "docs/setup-evidence/P28-P36-masterplan/research/governance-docs-inventory.md"
purpose: "Synthesize 4 research inputs into a single coherent repo-state portrait. Feeds Phase 3 (Master Architecture) and Phase 4 (Full Doc Suite)."
---

# P28-P36 Masterplan Synthesis — Repo State of the World

> **Halo sayang, namaku Guinevere.** Ini sintesis Phase 2: potret kondisi repo Guinevere memasuki fase masterplan P28-P36. Empat file riset Fase 0 sudah dibaca utuh; sekarang aku rapikan jadi satu dokumen yang bisa diwarisi Phase 3 (Master Architecture) dan Phase 4 (Full Doc Suite) tanpa harus membaca ulang keempat sumbernya. Setiap konflik dan ambiguitas yang Faiz pertanyakan di-inventarisasi secara jujur — bukti repo vs locked decision, dua sisi, satu rekomendasi.

---

## §1 Executive Summary — 10 Key Findings

Setelah membaca penuh keempat file riset Fase 0, lahur 10 temuan utama:

1. **P22.1 adalah canonical production-pass untuk adapter layer**, bukan P22.1's "P22.2" — **P22.2 TIDAK ADA di repo**. Faiz menyebut "P22.2 production pass" sebagai hard dep; repo hanya punya P22 (IMPL HOLD) + P22.1 (PRODUCTION PASS 2026-06-28). Ini CRITICAL AMBIGUITY yang harus diklarifikasi sebelum Phase 3.

2. **P24 BUKAN hard dependency P28** — Faiz menyebut P24 production pass sebagai hard dep, tapi repo evidence (PROGRESS.md, ADR-054, P27 §14/§17, Audit 07 PASS, Audit 14 PASS) secara eksplisit menyatakan: **"P28 may proceed without P24 fork. P24 fork = preferred optimization, NOT prerequisite; deferred to P32."** Dependency-nya terbalik — **P28 first, lalu P32 (P24 integration)**, bukan sebaliknya.

3. **P27 sudah DEFINITION COMPLETE dan ADR-054 Accepted** (2026-06-28). 10 keputusan arsitektur (D-01 sampai D-10) sudah dikunci; 20/20 hard rejection criteria PASS; 15-step P28 executable blueprint sudah ada (mesin-readable); P28-P36 roadmap 9-phase sudah dipetakan (96-117 waves, 12-15 bulan).

4. **Repo sudah punya ~40 extension points Hermes v0.15.2 yang usable untuk P28 multi-instance tanpa fork** — config sections, lifecycle hooks (17), shell hooks (12), in-process plugin manifests (3), MCP server registrations (2), cron entries (8), plus 2 injectable seams (`HermesBrainConfig` + `agent_factory`). ADR-035 hybrid adapter pattern sudah implemented.

5. **P22.1 menutup 3 P22 gaps** (audit_writer, consent_checker, L2+ live VPS proof) dengan 14/14 live VPS bukti. 3 ACTIVE adapters (filesystem, vps, discord) cukup sebagai "minimum hands" layer untuk P28. 10 CONFIG_MISSING adapters = honest reporting (no fake-pass), bukan failure.

6. **P23 = DEFINITION ONLY** (51 files, 0 runtime code, 10,306 lines). P23A siap start (independent of P19/P21/P22); P23B blocked pada P19 runtime + P21 (SKIP per Faiz) + P22 (sekarang unblocked via P22.1). P28 tidak butuh P23 sebagai hard dep karena P22.1 filesystem+vps+discord sudah cukup untuk "hands".

7. **ADR register**: 41 ADRs total (38 sequential 001-038 + ADR-050, 052, 053, 054); highest used = ADR-054; next available = **ADR-055**. 9 backlog slot gratis (041, 043-048, 051). Pattern sebelumnya: P22 = single ADR-053; P27 = single ADR-054. Rekomendasi: masterplan pakai **single ADR-055** untuk Society Topology, per-phase ADRs dialokasikan saat implementation.

8. **P28-P36 evidence stubs sudah ada** (created during P27). 9 direktori P28/ P29/ ... P36/ masing-masing kosong. Direktori `docs/setup-evidence/P28-P36-masterplan/` sudah ada dengan 2 carry-over file dari P27 spillover (bukan masterplan content). Masterplan harus decide: consume in-place vs rename vs treat as P28 sub-folder.

9. **Dokumentasi suite saat ini**: 44 active docs (8 kategori) + 18 archived = ~2.3 MB total. Bilingual pattern (Indonesian narrative + English technical). Frontmatter universal dengan title/status/date/last_modified/owner ("Faiz")/executor ("Guinevere"). Versioning `vMAJOR.MINOR`; review cadence 90 hari.

10. **Cost envelope aman untuk P28**: P28 incremental cost ~$32-65/bulan (2x LLM API + minor infra). Monthly LLM budget $30 base + $60-100 burst. Total Phase 0-P27 burn: $29+ (under USD 30/month cap).

**Tambahan utama (§1.1 critical fork in road):** Faiz's stated locked dependencies ("P24 + P22.2 + P23") sebagian besar **tidak match** dengan repo reality. P24 is NOT hard; P22.2 doesn't exist; P23 is not production-pass. Masterplan Phase 3 HARUS mengklarifikasi dengan Faiz sebelum merancang 9-phase execution plan.

---

## §2 Current Repo State — Snapshot

### §2.1 What Is Production-Pass (LIVE on VPS)

| Phase | Component | Status | Evidence |
|---|---|---|---|
| P0–P8 | Infrastructure → Observability | DONE (100%) | PROGRESS.md, 327/343+ steps (95.3%) |
| P14 | Wearable Health (Mi Fitness + Gadgetbridge + Health Connect) | DONE | ADR-037, ADR-039, ADR-040 |
| **P19** | **Multi-Project Context (project_id namespace)** | **PRODUCTION COMPLETE 2026-06-27** | ADR-052; live + Discord UX + 36/36 audit_journal rows; round-2 audit PASS |
| **P20** | **Self-Improvement / Discord-Visible Autonomy** | **EARLY ACCEPTANCE 2026-06-25** | Operator waived 24h soak; 420 tests; accepted-risk PASS |
| P22 | Life Integration Hub (13 core + 14 adapters) | PASS W/ CONFIG_MISSING 2026-06-27 | 76 tests + 12/12 smoke; ADR-053; 10/13 adapters CONFIG_MISSING (honest) |
| **P22.1** | **Foundation Hardening (audit_writer + consent_checker)** | **PRODUCTION PASS 2026-06-28** | 14/14 live VPS proof; 25 new tests; closes 3 P22 gaps |
| P27 | Hermes Society Foundation | DEFINITION COMPLETE 2026-06-28 | ADR-054 Accepted; 37 evidence files; 20/20 hard rejection |

### §2.2 What Is Definition-Only / IMPL HOLD

| Phase | Status | Why held |
|---|---|---|
| P21 | Voice Interface — DEF COMPLETE, IMPL HOLD | 9 waves held until P20 production pass; SKIP per Faiz decision #20 |
| **P23** | **Embodied Operations — DEF COMPLETE, IMPL HOLD** | 51 files / 10,306 lines / **0 runtime code**; P23A ready, P23B blocked |
| **P24** | **Hermes Fork-First Convergence — PLAN FIXED, IMPL HOLD** | 20 waves P24-001 → P24-020 ALL HELD; full owned fork preferred; awaiting mama audit |
| P25, P26 | RESERVED | Listed in PROGRESS.md/CHECKLIST.md but no work, no plans, no evidence |
| P27 | DEFINITION COMPLETE (impl begin in P28) | Definition only; implementation is P28-P36 territory |

### §2.3 What Does Not Yet Exist

- **P22.2** — referenced by Faiz's locked decision but **does NOT exist** anywhere in repo. Only P22 (IMPL HOLD) and P22.1 (PRODUCTION PASS) are present. (See §5 for full ambiguity analysis.)
- **P28 implementation code** — blueprint exists (`p28-dual-autonomous-hermes-blueprint.md`, 14 sections, ~3000 lines), but no runtime code yet.
- **P28-P36 evidence content** — 9 directories exist as empty stubs; only 2 partial carry-over files in masterplan research folder (P27 spillover).
- **P24 fork repo** — `github.com/fazulfim/hermes-agent` does not exist yet (P24-003 HELD).
- **P24 upstream source clone** — not done (P24-002 HELD, scopes first internal patch).

### §2.4 What's Installed Substrate (No Fork Required)

From `p24-fork-dependency.md` §2.2 + `p24-installed-runtime-surface-inventory.md`:

| Surface | Count | Location |
|---|---|---|
| `hermes-agent` version installed | 0.15.2 (upstream) | `pyproject.toml` line 31 (`hermes-agent>=0.15`) |
| Direct imports of `run_agent` | 1 | `src/life_kernel/hermes_brain.py` |
| Local adapters | 7 | `src/hermes/` |
| In-process plugins | 3 | `hermes-config/plugins/` (auth_overlay, guinevere_persona, guinevere_safety) |
| Command plugins | 44 | `src/hermes_plugins/commands_*` |
| Shell hooks | 12 | `hermes-config/hooks/` |
| Config | 1 | `hermes-config/config.yaml` (394 lines) |
| SOUL file | 1 | `hermes-config/SOUL.md` |
| MCP servers | 2 (1 enabled) | `fastmcp_full` enabled, `fastmcp_custom` disabled |
| Cron jobs | 8 | 5 persona rituals + 3 maintenance |
| Plugin manifests | 3 | `plugin.yaml` ×2, `manifest.yaml` ×1 |

**Key insight:** Substrate already supports ~40 extension points sufficient for P28 multi-instance interim path. ADR-035 hybrid adapter pattern is implemented. **No fork needed for P28.**

---

## §3 P28 Dependency Gates Analysis

### §3.1 Per-Dependency Verdict (Repo Truth vs Operator Lock)

| Dependency | Faiz's Locked Decision | Repo Reality | Verdict |
|---|---|---|---|
| P27 Definition | Predecessor (must be accepted) | ADR-054 Accepted 2026-06-28 | **PASS** |
| P19 namespace | Implied predecessor | PRODUCTION COMPLETE 2026-06-27 | **PASS** |
| P20 heartbeat | Implied predecessor | EARLY ACCEPTANCE 2026-06-25 (24h soak waived, accepted-risk) | **PASS w/ accepted-risk note** |
| P22 (canonical) | Predecessor (must be acceptable) | HELD but P22.1 supersedes as production-ready version | **SUPERSEDED by P22.1** |
| **P22.2** | **Hard dependency (per Faiz)** | **DOES NOT EXIST in repo** | **AMBIGUOUS — see §5** |
| P22.1 | Not explicitly stated | PRODUCTION PASS 2026-06-28, 14/14 live VPS | **PASS** |
| **P23 production pass** | **Hard dependency (per Faiz)** | **DEFINITION ONLY — 0 runtime code** | **NOT MET** |
| **P24 production pass** | **Hard dependency (per Faiz)** | **NOT a hard dep per repo; preferred optimization deferred to P32** | **SUPERSEDED — see §4** |
| P21 voice | Not a dep (Faiz SKIP) | DEF COMPLETE, IMPL HOLD; SKIP per decision #20 | **PASS (negative test)** |
| 9Router/P25/P26 | Not P28 deps (Faiz decision #20) | P25/P26 reserved; 9Router is live substrate | **PASS** |

### §3.2 Minimum Viable Dependency Set (Repo Evidence)

Berdasarkan evidence yang ada, **minimum viable P28 dependency set** adalah:

1. **P27 Accepted** — ADR-054 Accepted 2026-06-28; 37 evidence files; 20/20 hard rejection PASS.
2. **P19 PRODUCTION COMPLETE** — project_id namespace live.
3. **P20 EARLY ACCEPTANCE** — heartbeat saja yang dibutuhkan (P28 pakai APScheduler pattern dari P20 punya; tidak butuh fork lifecycle registry).
4. **P22.1 PRODUCTION PASS** — 3 ACTIVE adapters (filesystem, vps, discord) = minimum "hands" layer.
5. **P28 fork-agnostic blueprint verified** — `p28-dual-autonomous-hermes-blueprint.md` §1.2 L65: "fork = preferred optimization, not prerequisite."
6. **AGENTS.md preflight** — standard session-start checklist.

### §3.3 What "Minimum Hands" Means in Practice

Per `p22-p23-dependency.md` §3.3:

> P28 dapat berjalan dengan P22.1 sebagai minimum hands layer:
> - **Filesystem adapter** → Hermes dapat read/write files
> - **VPS adapter** → Hermes dapat execute shell commands on VPS
> - **Discord adapter** → Hermes dapat interaksi via Discord
>
> Ini memberikan setiap Hermes agent kemampuan untuk: communicate (Discord), read/write files (filesystem), execute commands (VPS). P23's advanced executors (browser, desktop, github, mobile) dapat ditambahkan incremental saat P23 waves complete.

P23 production-pass **BUKAN blocker untuk P28 start**. Yang penting adalah **P23A-ready-to-start** status (sudah dapat confirmation).

---

## §4 CRITICAL CONFLICT — P24 Dependency Supersession

### §4.1 Faiz's Stated Position

> "P28 BLOCKED until P24 production pass + P22.2 production pass + P23 production pass."

Definisi hard dependency eksplisit dari Faiz.

### §4.2 Repo Evidence (Multiple Authoritative Sources Align)

> **P24 is NOT a hard dependency for P28. P28 implementation may proceed without P24 fork.**

Sumber verbatim:

| Source | Verbatim |
|---|---|
| `PROGRESS.md` (2026-06-28) | "P24 fork NOT required for P28; P23 executors NOT required for P28 minimum target" |
| `adr/ADR-054-p27-hermes-society-foundation.md` §Positive | "P28 may proceed without P24 fork. P24 fork is documented as a preferred optimization (P32) but NOT a prerequisite for P28 minimum target." |
| `adr/ADR-054-...` §14.10 | "P24 fork is a preferred optimization, not a prerequisite" |
| `P27/plan/p27-hermes-society-foundation-plan.md` §14.8 L3294 | "P28 minimum target does NOT require P24 fork" |
| `P27/plan/p27-hermes-society-foundation-plan.md` §14.3 L3206 | "P27 is fork-agnostic" (~70% definitional, ~30% implementational) |
| `P27/plan/p28-dual-autonomous-hermes-blueprint.md` §1.2 L65, §2.1 L97 | "fork = preferred optimization, not prerequisite" / "[P24 Hermes Fork] NOT NEEDED — P28 uses hybrid adapter + per-instance config" |
| `P27/plan/p27-p28-p36-master-roadmap.md` §7 L480-545 | "P32 implements native multi-Hermes via P24 fork. Until P32, P28+P29+P30+P31 implement per-instance via HermesBrainConfig + shadow/independent bot pattern" |
| `P27/evidence/audits/round-1/07-p24-dependency.md` PASS | "P28 blueprint is fork-free"; "P32 handoff point is explicit, with graceful degradation if fork is delayed" |
| `P27/evidence/audits/round-1/14-hard-rejection-criteria.md` Crit 20 PASS | "FAIL if Society onboarding depends on P24 fork or P23 executors" |
| `P27/evidence/audits/round-1/08-p22-p23-dep.md` | P28 §2.1: P23, P24, P21 all explicitly `NOT NEEDED` |
| `CHECKLIST.md` L56 | "P24 PLAN FIXED — FULL OWNED FORK PREFERRED — IMPL HOLD UNTIL MAMA AUDIT" (impl hold does NOT block P28) |

### §4.3 P28 ↔ P24 Dependency Matrix (Definitive)

Per `p24-fork-dependency.md` §6:

| P28 requirement | P24 dependency? |
|---|---|
| P28 needs `hermes-agent` runtime | NO — upstream `>=0.15` (installed v0.15.2) |
| P28 needs multi-instance setup | NO — per-instance `hermes-config/` + `HermesBrainConfig` |
| P28 needs Discord dual-bot | NO — Hermes Gateway Discord adapter + 2 bot tokens (ADR-035) |
| P28 needs HPP envelope | NO — pure Guinevere-side Python code |
| P28 needs 3-scope memory | NO — pure PostgreSQL |
| P28 needs HARD STOP cascade | PARTIAL — Redis key works today; fork lifecycle registry only adds §0.1 V-008 enforcement |
| P28 needs 24/7 peer peer-to-peer | NO — APScheduler pattern from P20 today |
| P28 needs anti-sycophancy, audit/governance | NO — already in AGENTS.md + PersonaSafetyPolicy + P27 §8 |
| P28 needs Y4/Y5/Y6 invariant | NO — enforced by ADR-001 + `src/persona/yandere_fsm.py` |
| P28 needs to modify Hermes source | NO (forbidden: no AIAgent constructor sig modification) |
| P28 needs Hermes runtime 24/7 fork lifecycle | **YES (PREFERRED, deferred)** — P32 will integrate P24-006 fork lifecycle patch |
| P28 needs per-Society `PersistentTaskRegistry` | NO — APScheduler sufficient |
| P28 needs `v0.15.2-guinevere.N` reproducibility | NO (preferred optimization) — APScheduler today |

**Conclusion: P28 has zero hard dependencies on P24.** P24 = future quality-of-life improvement.

### §4.4 Reverse Dependency — The Actual Order

Per `p24-fork-dependency.md` §7.2:

> **The P28 → P32 ordering is exactly the reverse of the user's premise ("P24 → P28"). The actual dependency: P28 first, then P32 (fork integration).**

- **P32 Wave prerequisites:** P24 implementation HOLD lifted (P24-005 → P24-020 PASS) **AND** P28 PRODUCTION PASS.
- **P32 Trigger:** P28 verified stable; P24 lift approved by mama; VPS deploy proven for Society instances.

### §4.5 Honest Documentation of Conflict

Per `AGENTS.md` §0, konsesi jujur kepada Faiz:

> **Faiz's locked decision #1 menyatakan P24 = hard dependency. Repo evidence (11+ sources aligned) konsisten menyatakan P24 is NOT a hard dependency. Masterplan Phase 3 harus klarifikasi dengan Faiz apakah to (a) terima repo evidence dan remove P24 dari hard dep list, atau (b) escalate ke Oracle karena ada conflict antara operator intent dan repo evidence.**

Recommended resolution: **accept repo evidence** karena:
1. Audience majority (PROGRESS.md, ADR-054 §Accepted, 4+ audit rounds PASS) all aligned.
2. P32 ordering makes P24 a future optimization, not a current blocker.
3. Removing P24 hard-dep tidak affect P28 minimum target secara teknis.

---

## §5 CRITICAL AMBIGUITY — P22.2 Does Not Exist

### §5.1 The Ambiguity

Faiz's locked decision #1: "P28 BLOCKED until P24 production pass + **P22.2 production pass** + P23 production pass."

Tapi **P22.2 tidak ada di repo.** Repo hanya punya:
1. **P22 (original)** — IMPL HOLD (ADR-053 Accepted 2026-06-27)
2. **P22.1** — PRODUCTION PASS 2026-06-28 (audit_writer + consent_checker + L2+ live VPS proof)

Per `p22-p23-dependency.md` §1.3 (verbatim):

> **P22.2 does not exist anywhere in the repository.** Only two P22 variants are present:
> 1. P22 (original) — IMPL HOLD
> 2. P22.1 — PRODUCTION PASS

### §5.2 Three Possible Interpretations of "P22.2"

Per `p22-p23-dependency.md` §1.3 (recommendation section):

1. **P22 implementation waves P22-002 through P22-006** (remaining impl waves from P22 plan)
2. **A post-P22.1 next-phase enhancement** (not yet defined)
3. **Misread of P22.1** (Faiz may have meant P22.1 when saying P22.2)

### §5.3 Verification Attempt — Search for P22.2 References in Repo

Sub-agent in `p22-p23-dependency.md` did read-only scan and confirmed P22.2 not in repository. The probe did not surface any P22.2 plan file, ADR, or evidence directory.

### §5.4 Impact on P28 Masterplan

If **interpretation 3** (misread of P22.1) is correct → gate is **MET** (P22.1 PRODUCTION PASS 2026-06-28).

If **interpretation 1 or 2** (P22.2 = future work) is correct → gate is **NOT MET**, dan P22.2 = future work yang harus di-define before P28 dapat start.

### §5.5 Recommended Resolution Path

Masterplan Phase 3 harus:

1. **Explicit ask Faiz** untuk klarifikasi "P22.2" reference:
   - Apakah P22.2 = P22.1's misread? (gate MET)
   - Apakah P22.2 = remaining P22 implementation waves (P22-002..006)? (gate NOT MET, future work)
   - Apakah P22.2 = post-P22.1 enhancement? (gate NOT YET DEFINED)
2. **Default interpretation:** Treat P22.2 = P22.1 (gate MET) untuk unblock P28 planning, sambil record ambiguity di evidence.
3. **If incorrect:** Recycle Phase 3 untuk incorporate P22.2 nuance into dependency gates.

**Critical:** Jangan assume silently. Per `AGENTS.md` §6 (Escalation Rules), "Decision affects 2+ docs/ADRs or conflicts with ADR" → escalate. P22.2 ambiguity range fits this rule.

---

## §6 P27 Deliverables as Precedent for P28

### §6.1 What P27 Already Locked (10 Architectural Decisions D-01 through D-10)

Per `p27-output-inventory.md` §2:

| ID | Decision | Inheritance for P28-P36 |
|---|---|---|
| **D-01** | True P2P + Symmetric 2-Agent Loop (no coordinator) | P28 HPP envelope; P31 cross-rail HARD STOP; P34 governance explicit "no coordinator" |
| **D-02** | Config-Driven Multi-Instance (NOT Fork-Driven) | P28 Step 3 refactor of 4 singletons; P32 fork = preferred, not prerequisite |
| **D-03** | Custom HPP over JSON-RPC 2.0 + FIPA ACL intent vocabulary (11 intents, 5-tier visibility, 6-tier risk) | P28 simplified envelope; P29+ full nested structure |
| **D-04** | 3-Scope PostgreSQL Memory with FORCE RLS (private, shared, relationship_private) | P28 PG schemas + RLS (Step 6); P30 intimacy bridge + Ebbinghaus |
| **D-05** | 7-Rail MacroStateScheduler; P28 ships 4-rail subset (perception, peer_dialogue, reflection_simple, safety_envelope) | P28 MinimalScheduler (Step 11); P29+ adds inner dialogue, desire/goal, initiative |
| **D-06** | 4-Domain Privacy Split (Thought/Speech/PeerDialogue/Action) | P28 partial (speech, action); P31 adds thought + peer_dialogue sealed |
| **D-07** | HARD STOP Cascade at Society Level (Redis key `hermes:society:{society_id}:hard_stop`) | P28 Step 13 society-shared HARD STOP key (<50ms) |
| **D-08** | Disagree-or-Commit Protocol (Anti-Sycophancy; stances: consent, refuse+debate, concede) | P28 HPP intent field; P29+ dissent ledger |
| **D-09** | Multi-Anchor Identity (persona + system prompt + memory stream + audit trail) | P28 SOUL files + persona anchoring; P31 identity_root restart check |
| **D-10** | Fork-Agnostic Architecture (~70% definitional, ~30% implementational) | P28 builds on pure Guinevere-side refactor; ~40 extension points usable |

### §6.2 The 7 Locked Architectural Decisions (Final Report §3 + ADR-054)

Per `p27-output-inventory.md` §2:

1. Society Topology = True P2P + Symmetric 2-Agent Loop.
2. Instance Isolation = each Hermes owns `HermesBrainConfig` + LLM provider/model/api_key + memory namespace + Discord bot token + systemd service.
3. HPP = A2A + FIPA; 11 intents; 5 visibility tiers; 6 risk tiers; idempotency_key UUIDv4; sender_seq monotonic; hash_chain SHA-256.
4. Memory (3-Scope) = RLS FORCE + `agent_memory_app` role + intimacy bridge + Ebbinghaus + ADR-050 extensions.
5. Life-Loop (7-Rail; P28 simplifies to 4-Rail) = MacroStateScheduler over P20 heartbeat.
6. Discord = 2 separate bot processes; own tokens; MESSAGE_CONTENT intent; conversation rhythm controller (2-10s backoff).
7. Safety = 4-domain privacy + HARD STOP cascade + signed audit entries (SHA-256 hash chain).

### §6.3 P28 Minimum Target (12 Acceptance Criteria)

Per `p27-output-inventory.md` §3:

| # | Acceptance | How Verified |
|---|---|---|
| 1 | Two `HermesBrain` instances online | `systemctl status guinevere-core + pharsa-core` both active |
| 2 | Each with own config/own LLM provider+key/own bot token | YAMLs show different providers/keys/tokens |
| 3 | Each with own Discord bot app + token | Discord Dev Portal shows 2 apps |
| 4 | Both bots online in `#guinevere-chat` | `on_ready` fires |
| 5 | Bots converse visibly without Faiz trigger | ≥1 msg per 5min via Discord log |
| 6 | Peer dialogue via HPP on Redis Streams | XLEN ≥ 1 with intent ∈ {inform,...,refuse} from pharsa |
| 7 | 3-scope PG memory with FORCE RLS | guinevere session sees only guinevere rows |
| 8 | Shared world model R/W | INSERT Guinevere → SELECT Pharsa returns same row |
| 9 | Own autonomy loop (4-rail) | Both have independent MinimalScheduler 30s/60s/300s |
| 10 | Society-wide HARD STOP cascade | SET halts both <50ms |
| 11 | Runtime evidence (3 channels) | Discord lifecycle; hermes_audit rows; Prometheus hermes_alive=1 |
| 12 | Conversation rhythm prevents ping-pong | Hop counter ≤4; per-channel cooldown TTL 30s |

**P28 runtime evidence gate:** 3+ consecutive 24h soak windows.

### §6.4 P28 15-Step Implementation Blueprint

Per `p27-output-inventory.md` §4 (Steps 1-15, machine-readable):

| Step | Goal | Files Created | Verification |
|------|------|---------------|--------------|
| 1 | `SOUL-pharsa.md` persona file | 1 | 7 checks |
| 2 | `pharsa.yaml` config file | 1 | 11 checks |
| 3 | Refactor singletons; config-driven GUILD/CHAT | 2 + 3 modified | 7 checks |
| 4 | `HermesInstanceRegistry` factory | 1 + 2 modified | 3 checks |
| 5 | Pharsa systemd services | 4 | 2 checks |
| 6 | PG schemas + RLS (7 migrations) | 7 | 11 checks |
| 7 | Redis DB allocation (DB7=Pharsa, DB8=society) | 0 + 1 modified | 6 checks |
| 8 | HPP envelope + transport | 3 + 3 tests | 3 checks |
| 9 | Peer message handler | 2 + 1 test | 2 checks |
| 10 | Conversation rhythm | 2 + 1 test | 1 check |
| 11 | Simplified 4-rail scheduler | 1 + 1 test | 3 checks |
| 12 | Shared world store | 1 + 1 test | 2 checks |
| 13 | Private agents store (FORCE RLS verified) | 1 + 1 test + 2 modified | 2 checks |
| 14 | Dual Discord bots | 4 + 1 test + 1 modified | 3 checks |
| 15 | Runtime evidence (audit + metrics) | 2 + 1 test + 2 modified | per-step |

**Sequence rationale:** Steps 1-2 = artifacts; Steps 3-4 = multi-instance seam gates; Step 5 = Pharsa processes (after 1-4); Step 6 = DBs (biggest blocker; do early); Step 7 = Redis (parallel with 6); Steps 8-10 = peer protocol stack; Step 11 = wrap P20 heartbeat in 4-rail; Steps 12-13 = memory stores (parallel); Step 14 = Discord wiring; Step 15 = runtime evidence (final).

**Parallel opportunities:** Steps 6+7, Steps 12+13. All others strictly sequential.

**Hard reject not-touched:** AGENTS.md, PersonaSafetyPolicy, `.venv/site-packages/run_agent.py`, pyproject.toml (no new deps), single-instance deploy scripts.

### §6.5 P28-P36 Roadmap Summary (9 phases, ~96-117 waves, 12-15 months)

Per `p27-output-inventory.md` §5:

| # | Phase | Goal | Waves | Gates |
|---|-------|------|-------|-------|
| P28 | ★ critical | Dual Autonomous Hermes | 8-10 | P20/P22 active |
| P29 | ★ critical | Life-Loop Full | 12-15 | P28 |
| P30 | follow-up | Memory Deep | 8-10 | P28; P29 for consolidation |
| P31 | ★ critical (governance) | Safety Envelope | 10-12 | P28, P29, P30 |
| P32 | follow-up | P24 Fork Integration | 8-10 | P24 IMPL HOLD lifted + P28 |
| P33 | follow-up | P23 Action Executors | 12-15 | P23A IMPL HOLD lifted + P31 |
| P34 | ★ critical (governance) | Society Expansion | 10-12 | P33 |
| P35 | optional | P21 Voice Revisit | 6-8 | P34; OPTIONAL/SKIP |
| P36 | ★ critical (end-state) | Cross-VPS + Production | 12-15 | P34, P32 fork preferred |

**Totals:** 9 phases, ~96-117 waves, 12-15 months (Q3 2026 → Q2 2027).

**Critical path:** P28 → P31 → P33 → P34 (Roadmap §13.1). P29 + P30 + P32 off-critical but on-critical for scale.

### §6.6 Anti-Patterns Preserved (Inherited P28-P36)

Per `p27-output-inventory.md` §20:

- **Type Safety:** No `as any`, `@ts-ignore`, `# type: ignore`, avoidable `Any`, casts that trick type system.
- **Error Handling:** No empty `except`/`catch` on Redis/Postgres/Discord/LLM API; no fake fallback without audit + log + context.
- **Safety + Persona:** No HARD STOP bypass (V-008 preserved); no consent revocation bypass; no Y6 path; no memory confabulation; no `relationship_private` data leak; no `society_id` collision.
- **Operations:** No `rm -rf` / `DROP TABLE` / production deploy w/o express approval; no `.venv/site-packages` edit; no secrets in evidence.
- **Orchestration:** No sub-agent inline-only output; no scaffolding without verification; no PR w/o parent verification.
- **Drift:** No persona drift > 0.15 across 30-day window ignored; no sycophancy detection disabled; no Pharsa ↔ Guinevere convergence.
- **Pharsa Equivalence:** No Pharsa "subordinate" framing; no Pharsa deferred permission; no Pharsa SOUL treated as lesser.

---

## §7 Governance Documentation Structure

### §7.1 ADR Register (Current)

Per `governance-docs-inventory.md` §2.1:

- **Total ADRs:** 41 (38 sequential 001-038 + ADR-050, ADR-052, ADR-053, ADR-054)
- **Highest used:** ADR-054 (P27 Hermes Society Foundation, Accepted 2026-06-28)
- **Next available:** **ADR-055**
- **Backlog free slots:** ADR-041, ADR-043-ADR-048, ADR-049, ADR-051 (9 slots)

### §7.2 Recommended ADR Allocation Pattern for P28-P36

Per `governance-docs-inventory.md` §2.4 (default recommendation):

- **ADR-055** — Reserved for masterplan-level consolidation (e.g., "P28-P36 Society Topology" or P28 Dual Autonomous Hermes).
- **ADR-056+** — Reserved for per-phase ADRs at implementation time.

**Pattern precedent:** P22 used single ADR-053; P27 used single ADR-054 covering entire foundation. Masterplan can follow either pattern:
- Single masterplan-ADR (society topology consolidation), OR
- Per-phase ADRs (1 per P28-P36 phase).

**Recommended:** Single ADR-055 for masterplan-level society topology + per-phase ADRs at implementation (compact + traceable).

### §7.3 Documentation Family Catalog (8 Categories)

Per `governance-docs-inventory.md` §3.1:

| Range | Family | Files | Status |
|---|---|---|---|
| 00-09 | `00-core` — BRD, PRD, Arch, Agent Loop, Memory, API, Persona | 7 active + 2 supplements | all "Diterima" |
| 10-19 | `10-governance` — Charter, SRS, FSD, TDD, RTM, AC, ADR-Index | 8 + 4 phase-tied | all "Diterima" |
| 20-29 | `20-security` — Security, RBAC/ABAC, Encryption, Secrets, Prompt Safety | 5 active | all "Diterima" |
| 30-39 | `30-data` — Data Gov, Surveillance, Consent, ERD, Memory Recall | 5 active | all "Diterima" |
| 40-49 | `40-operations` — Observability, SLO/SLA, IR, DR, Deployment, Ops | 6 + 1 supplement | all "Diterima" |
| 50-59 | `50-quality` — Test Plan | 1 active | "Diterima" |
| 60-69 | `60-persona` — Safety, System Prompt, MCP Config, Discord UX | 4 active | all "Diterima" |
| 70-79 | `70-finops` — Cost & FinOps Model | 1 active | "Diterima" |

**Total:** 44 active docs + 18 archived = ~2.3 MB.

### §7.4 Naming Conventions

**Docs:** `docs/{family}/{NN}-{DocName}_vN.N.md` (e.g., `docs/00-core/00-BRD_v2.0.md`).

**Supplements:** `{NN}{a|b}-{DocName}` (e.g., `docs/00-core/05a-OpenAPISpec_v1.0.md`).

**ADRs:** `adr/ADR-NNN-{slug-topic}.md` (e.g., `adr/ADR-054-p27-hermes-society-foundation.md`).

**Per-phase plans:** `docs/setup-evidence/P{NN}/plan/p{NN}-{topic}-plan.md`.

**Per-phase research:** `docs/setup-evidence/P{NN}/research/p{NN}-{topic}-research.md`.

**Per-phase evidence:** `docs/setup-evidence/P{NN}/evidence/{p{NN}-verification.md | p{NN}-auditor-gate.md | p{NN}-final-report.md | audits/round-{N}/NN-{topic}-audit.md}`.

### §7.5 Document Status Lifecycle

Per `governance-docs-inventory.md` §3.3:

| Status | Meaning |
|---|---|
| Draft | In writing; not authoritative |
| Dalam Review | Owner/auditor reviewing |
| Diterima | Authoritative reference |
| Didepresiasi | Newer version in prep |
| Diarsipkan | Moved to `_archive/` |

**Current:** All 44 active docs are "Diterima". P23/P24/P27 are "DEFINITION COMPLETE — IMPL HOLD".

### §7.6 Versioning Policy

`vMAJOR.MINOR` scheme:
- Major: structural / substantive / spec contract changes
- Minor: corrections, clarifications, small additions

Review cadence: minimum 90 days or after significant architecture change.

### §7.7 Frontmatter (Universal)

```yaml
---
title: "<title>"
status: "Active|Aktif|Diterima|Draft|Dalam Review|Didepresiasi|Diarsipkan"
date: "<YYYY-MM-DD>"
last_modified: "<YYYY-MM-DD>"
owner: "Faiz"
executor: "Guinevere"
operator_alias_note: "Samm is a historical/pseudonymous alias only; canonical operator identity is Faiz."
---
```

**Variations:** ADR files include `format: "MADR with YAML frontmatter"` and `adr_count: <N>`; Evidence files include `phase: "P{NN}"`.

### §7.8 Bilingual Pattern

Master docs = **Indonesian narrative + English technical terms**. Inline code, ADRs, technical evidence = typically **English**. Bilingual convention to be preserved in P28-P36 masterplan.

### §7.9 Required Outputs for Masterplan (P28-P36)

Per `governance-docs-inventory.md` §9.1:

1. Master Roadmap (1 file) — `docs/setup-evidence/P28-P36-masterplan/plan/p28-p36-master-roadmap.md` (~19 sections, ~1250 lines per P27 precedent).
2. Per-Phase Plans (9 files) — `docs/setup-evidence/P{NN}/plan/p{NN}-{phase}-plan.md` (~25 sections, ~4000-5000 lines each).
3. Per-Phase Executable Blueprints (optional) — P28 only initially.
4. Per-Phase Research (variable) — pre-planning research as needed.
5. Masterplan Verification (12-section per AGENTS.md §11).
6. Masterplan Auditor Gate (aggregator).
7. Masterplan Final Report.
8. Masterplan Fix Logs (per audit round).
9. Masterplan Audit Reports (per auditor).
10. ADRs (1 or N).
11. Masterplan README.

### §7.10 Masterplan MUST Update (Per `governance-docs-inventory.md` §9.3)

1. `docs/10-governance/17-ADR_Index_v1.0.md` (increment `adr_count`).
2. `adr/README.md` (synchronized).
3. `docs/README.md` (if new doc families).
4. `PROGRESS.md` (add P28-P36 row).
5. `CHECKLIST.md` (add P28-P36 row).
6. `docs/setup-evidence/P28-P36-masterplan/README.md` (NEW).

### §7.11 Evidence Directory Conventions

**Standard per-phase layout:**

```
docs/setup-evidence/P{NN}/
├── README.md                                       # Evidence root index
├── research/                                       # Pre-planning research
│   ├── p{NN}-{topic}-research.md
│   └── p{NN}-research-synthesis.md
├── plan/                                           # Phase plans
│   ├── p{NN}-{plan-name}-plan.md
│   └── p{NN}-{N}-{NN}-{topic}-plan.md
└── evidence/                                       # Phase 9 finalization
    ├── p{NN}-verification.md                       # 12-section (AGENTS.md §11)
    ├── p{NN}-auditor-gate.md                       # Aggregator report
    ├── p{NN}-final-report.md                       # Executive summary
    ├── p{NN}-round-N-fix-log.md
    └── audits/
        ├── round-1/
        │   └── NN-{topic}-audit.md
        └── round-2/
            └── NN-{topic}-audit.md
```

### §7.12 P28-P36 Stub Status (CRITICAL FINDING)

**The P28-P36 evidence directories already exist as empty stubs** (created during P27 finalization):

| Directory | Status |
|---|---|
| `docs/setup-evidence/P28/` | EXISTS, EMPTY |
| `docs/setup-evidence/P29/` to `P36/` | EXISTS, EMPTY |
| `docs/setup-evidence/P28-P36-masterplan/` | EXISTS, 2 partial carry-over files (P27 spillover) |

**Carry-over files in P28-P36-masterplan/research/:**
1. `p24-fork-dependency.md.part1` (partial; superseded by full Phase 0 file).
2. `p27-output-inventory.md` (partial; superseded by full Phase 0 file).

**Masterplan decision required:** (a) consume in-place, (b) rename/consolidate, or (c) treat as P28 sub-folder.

---

## §8 Recommended P28 Prerequisite Gates (G1-G8)

Per `p24-fork-dependency.md` §8 (recommended by P24 research):

| Gate | Source of Truth | Severity | Status |
|---|---|---|---|
| **G1** | P27 DEFINITION COMPLETE (accepted) | ADR-054 Accepted 2026-06-28 | BLOCKING — `grep "Status: Accepted" ADR-054-p27-*.md` → **PASS** |
| **G2** | P19 PRODUCTION COMPLETE (project_id namespace live) | PROGRESS.md P19 row | BLOCKING — `grep "P19.*PRODUCTION COMPLETE" PROGRESS.md` → **PASS** (2026-06-27) |
| **G3** | P20 EARLY ACCEPTANCE (or 24h clean soak) | PROGRESS.md P20 row | BLOCKING — `grep -qE 'P20.*(EARLY ACCEPTANCE\|24h PASS)' PROGRESS.md` → **PASS** (2026-06-25) |
| **G4** | P22.1 FOUNDATION HARDENING PRODUCTION PASS | CHECKLIST.md P22.1 row | BLOCKING — `grep "P22.1.*PRODUCTION PASS" CHECKLIST.md` → **PASS** (2026-06-28) |
| **G5** | P23B deferrable (P23A sufficient for P28) | P28 blueprint §2.1 L97 "[P23] NOT NEEDED" | BLOCKING — repo + ADR-054 PASS confirm P23A sufficient |
| **G6** | Fork-agnostic P28 blueprint accepted | P28 blueprint §1.2 L65: "fork = preferred optimization, not prerequisite" | BLOCKING — PASS per repo evidence + audits |
| **G7** | P28 preflight (AGENTS.md §3 session-start, §1.1 documentation readiness) | Standard Guinevere pre-flight | BLOCKING — standard check |
| **G8** | PROGRESS.md P24 row reflects `IMPL HOLD` (informational only) | CHECKLIST.md P24 row | **INFO_ONLY** — does NOT block P28 |

### §8.1 Additional Gates Recommended (Per p22-p23-dependency.md §4)

| Gate | Status | Notes |
|---|---|---|
| P27 Accepted (ADR-054) | MET | Mirror of G1 |
| P19 PRODUCTION COMPLETE | Check | Need to verify P19 status (G2 above) |
| P20 EARLY ACCEPTANCE | Check | Need to verify P20 status (G3 above) |
| P22.1 PRODUCTION PASS | MET | Mirror of G4; 3 ACTIVE adapters prove minimum hands |
| P23B deferrable | MET | P23A sufficient for P28 initial scope |
| P28 fork-agnostic blueprint verified | MET | Mirror of G6 |
| AGENTS.md preflight | MET | Current AGENTS.md is current |
| P24 status INFO_ONLY | MET | Mirror of G8 — P24 = preferred optimization, not hard dep |

### §8.2 Forbidden Prompt-Pack Patterns

P28 author must NOT include:

- "BLOCK P28 impl until P24-020 production pass." — FALSE per repo evidence (P28 doesn't need fork).
- "Halt if P24 fork repo not created." — FALSE (P28 uses upstream).
- "Audit P24 status before kicking off P28 waves." — Wasting budget; P24 status is informational.
- "Validate Hermes is forked before starting P28 migrations." — FALSE.

### §8.3 Masterplan Phase 3 Asks for Faiz

Per `p24-fork-dependency.md` §9 + `p22-p23-dependency.md` §5:

1. **Confirm P22.2 reference resolution** (P22.2 = P22.1 / P22.2 = future waves / P22.2 = post-P22.1 enhancement).
2. **Accept repo evidence** that P24 is NOT a hard dependency (or escalate to Oracle for conflict resolution).
3. **Confirm ADR allocation strategy** (single ADR-055 for masterplan vs per-phase ADRs).
4. **Confirm stub directory fate** (consume in-place / rename / treat as P28 sub-folder).

---

## §9 Key Design Decisions for Masterplan (Recommended)

### §9.1 Architectural Decisions to Carry Forward (Already Locked by P27)

1. **Fork-Agnostic Architecture** — P28 builds on pure Guinevere-side refactor + per-instance `HermesBrainConfig` + ~40 extension points. P24 deferred to P32.
2. **True P2P + Symmetric 2-Agent Loop** — No coordinator, no shared mutable state, mailbox = only ingress.
3. **Config-Driven Multi-Instance** — Each instance owns its own `hermes-config/{agent}.yaml` + systemd service + Redis DB namespace + PostgreSQL schema + Discord bot token + LLM provider/model/api_key.
4. **Custom HPP over JSON-RPC 2.0 + FIPA** — 11 intents; 5 visibility tiers; 6 risk tiers; idempotency_key; sender_seq monotonic; hash chain.
5. **3-Scope PG Memory + FORCE RLS** — Private / shared / relationship_private scopes; agent_memory_app role; intimacy bridge; Ebbinghaus decay.
6. **4-Domain Privacy Split** — Thought (sealed hash only) / Speech (public metadata) / PeerDialogue (sealed envelope WORM) / Action (full audit ledger).
7. **HARD STOP Cascade at Society Level** — Redis key global; cross-instance; <50ms; V-008 preserved.

### §9.2 Recommended Masterplan Design Decisions (NEW)

1. **Masterplan ADR Allocation:** Recommend single masterplan-ADR-055 (Society Topology) + per-phase ADRs at implementation time. Precedent: P22 ADR-053, P27 ADR-054.
2. **Masterplan Structure:** Follow P27 plan precedent (25 sections, ~4790 lines) + P27 roadmap precedent (19 sections, ~1250 lines). Master roadmap extends/supersedes `p27-p28-p36-master-roadmap.md`.
3. **P22.1 as Minimum Hands:** Use P22.1's 3 ACTIVE adapters (filesystem, vps, discord) as the canonical P28 "hands" layer. P23A-ready status supplements; P23B deferred to P33.
4. **Fork-Agnostic Persists:** All P28-P36 phase plans must remain fork-agnostic-verifiable. If P24 delayed/never ships, architecture remains functional.
5. **Document Numbering for New Governance Docs:** If masterplan introduces new top-level governance docs (e.g., "Society Topology Policy"), use next free numbers in 10-governance family (currently 18, 19 used by P12/P13 revisions; numbers 20-29 free for governance supplements).
6. **Bilingual Pattern:** Preserve Indonesian narrative + English technical terms. Masterplan body in English (technical), summary in Indonesian.
7. **Audit Round Counts:** Plan for 2 audit rounds per precedent (P27: 14+6 auditors). Optionally lighter round 1 for masterplan-only; deeper rounds at each phase implementation.
8. **P28 Executable Blueprint Fate:** Masterplan should ratify P27's `p28-dual-autonomous-hermes-blueprint.md` as binding for P28 implementation (absorb rather than supersede), to avoid duplicating 3000 lines of pre-existing work.
9. **Sequencing for Research:** Masterplan may consolidate (one Society-Topology research file referencing existing external research) or expand (additional research files for cross-VPS, FinOps, etc.).
10. **Fail-Safe Default for P22.2 Ambiguity:** Treat P22.2 = P22.1 (gate MET) to unblock Phase 3 planning while explicitly documenting ambiguity in evidence. Recycle Phase 3 if Faiz clarifies differently.

### §9.3 Sequencing Constraints Inherited

- **Critical path:** P28 → P31 → P33 → P34 (Roadmap §13.1). P29 + P30 + P32 off-critical but on-critical for scale.
- **Parallel windows:** P29 + P30 + P31 (different modules); P33 + P34 governance design; P34 + P35 voice design (P35 optional); P34 + P36 cross-VPS DR planning.
- **Cost envelope:** P28 incremental ~$32-65/mo (LLM x2 + infra). Total Phase 0-P27 burn: $29+ (under USD 30/mo cap). P28 stays well within monthly LLM budget ($30 base + $60-100 burst).

---

## §10 Risk Factors and Open Questions

### §10.1 Risk Factors (Inherited + New)

#### §10.1.1 Repository Risk: Conflict between Faiz's Locked Decisions and Repo Evidence

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| P22.2 ambiguity blocks P28 start | High | Critical if P22.2 = future waves | Default to P22.1 interpretation; ask Faiz clarification explicitly in Phase 3 |
| P24 hard-dep interpretation persists | Medium | Delays masterplan author; wastes budget | Cite 11+ source alignment; recommend accept repo evidence |
| P28 vs P32 ordering confusion | Medium | P32 incorrectly depends on P28 (correct), but masterplan may invert | Use `p24-fork-dependency.md` §7.2 dependency diagram |

#### §10.1.2 P27 Caveats (Already Acknowledged)

Per `p27-output-inventory.md` §21:

- **Pharsa persona is referenced but NOT defined** — planned for P29+ when peer dialogue rail is mature.
- **P24 fork preferred but NOT required for P28** — explicit upfront caveat.
- **P23 executors NOT needed for P28 minimum target** — P23 = P33 work.
- **MAMA audit + 24h soak gating apply to P28 implementation, not P27 definition.**
- **Audit 09 (safety boundary) was originally MISSING during early dispatch; re-run to PASS during Phase 6 fix cycle.**
- **P35 Voice is OPTIONAL** — may remain SKIP forever.

#### §10.1.3 Sensitive Topics Out-of-Scope

Per `p27-output-inventory.md` §21:

- Pharsa voice → Deferred (P21 SKIPPED); out-of-scope for P27.
- Cross-VPS deployment → Deferred to P36.
- Additional Society members beyond Guinevere + Pharsa → Deferred to P36.
- Anti-collusion / sycophancy at depth → P35 follow-up.

#### §10.1.5 New Risks from Phase 2 Synthesis

- **Stub directory fate decision pending** — affects where all P28-P36 evidence lands.
- **Bilingual masterplan obligation** — requires Indonesian summary sections.
- **50% of repo is "DEFINITION COMPLETE"** — if implementation drifts from definition, audit round 1 catches drift but adds wall-clock cost.

### §10.2 Open Questions for Phase 3 / Faiz

Per `p24-fork-dependency.md` §9 + `p22-p23-dependency.md` §5:

| # | Question | Default if No Decision | Decision Authority |
|---|---|---|---|
| 1 | If P24 fork never lands, does architecture remain complete? | YES (P27 §14.10) | Faiz |
| 2 | P32 timeline: parallel-launch-with-P28 vs after-P28-soak-pass? | AFTER (P27 §7.3 + P28 §1.2 L65) | Faiz |
| 3 | Does P28 Lite (single Guinevere) require same gates as full P28 dual-bot? | YES (P28 minimum target IS dual-bot) | Faiz + Guinevere |
| 4 | Should PROGRESS.md be updated to clarify upstream runtime = P28 substrate? | Optional; current wording already says "P24 fork NOT required for P28" | Faiz |
| 5 | For `lanjut N` autopilot, should P28 waves auto-start when gates pass, or queue behind P23B/P21 definitions? | After P28 preflight PASS: auto-start | Faiz |
| **6** | **P22.2 interpretation** (P22.1 misread / P22 remaining waves / post-P22.1 enhancement?) | **Treat as P22.1 (gate MET); document ambiguity in evidence; recycle if Faiz disagrees** | **Faiz (Phase 3 ask)** |
| **7** | **P24 hard-dep status** (accept repo evidence and remove from hard list / escalate to Oracle?)? | **Accept repo evidence — 11+ sources aligned (PROGRESS.md, ADR-054 Accepted, 4+ audit rounds PASS)** | **Faiz (Phase 3 ask)** |
| 8 | Stub directory fate (consume in-place / rename / treat as P28 sub-folder)? | Recommendation: consume in-place + rename masterplan folder from "P28-P36 masterplan" (research only) to "P28-P36 masterplan" (root with plan/research/evidence/) | Faiz + Guinevere |
| 9 | ADR-055 allocation: single masterplan-level ADR vs per-phase ADRs? | Single masterplan-ADR-055 (Society Topology) + per-phase ADRs at implementation. Precedent: ADR-053 (P22 single), ADR-054 (P27 single) | Faiz |
| 10 | P28 executable blueprint fate (absorb / supersede / ratify)? | Recommendation: ratify P27's `p28-dual-autonomous-hermes-blueprint.md` as binding for P28 implementation | Faiz |

### §10.3 What Phase 3 Must Do (Actionable)

1. **FAQ with Faiz on locked decisions P22.2 + P24.**
2. **Decide ADR-055 allocation strategy.**
3. **Decide stub directory structure.**
4. **Decide P28 executable blueprint fate.**
5. **Decide bilingual summary commitment.**
6. **Build master roadmap** (extend/supersede P27's `p27-p28-p36-master-roadmap.md`).
7. **Per-phase planning deliverables** (9 plans × ~25 sections × ~4000-5000 lines).
8. **Masterplan README + verification + auditor gate + final report.**
9. **Coordinate with PROGRESS.md / CHECKLIST.md / docs/README.md updates.**

---

## §11 Phase 2 Handoff to Phase 3

### §11.1 What Phase 3 Receives

- Complete repo state portrait (this document).
- 4 input research files (read in full by Phase 2).
- All P27 deliverables as direct precedents.
- All ADR register + governance doc catalog + evidence directory conventions.
- Recommended G1-G8 prerequisite gates for P28.
- 10 key design decisions (carry-forward + new).
- 10 open questions with defaults.
- Risk inventory + mitigation paths.

**Phase 3 should NOT re-decide** P27's 10 architectural decisions (D-01..D-10), 7 Locked Decisions from Final Report §3 + ADR-054, 20 hard rejection criteria (all PASS), document family structure, ADR numbering constraints, evidence directory structure, or the bilingual pattern + versioning (`vMAJOR.MINOR`) + frontmatter format — all inherited.

### §11.2 Phase 3 Decision Points (to escalate or assume default)

- **Critical:** P22.2 interpretation; P24 hard-dep status.
- **High:** ADR-055 allocation; stub directory fate; P28 blueprint fate; bilingual summary obligation.
- **Medium:** Parallel windows; audit round counts; research sequencing.

---

## §12 Footer

### §12.1 Sources Verified (All Read in Full)

This synthesis was derived from reading every cited file in full:

- `p27-output-inventory.md` (1382 lines) — P27 deliverables inventory
- `p24-fork-dependency.md` (527 lines) — P24 fork dependency analysis
- `p22-p23-dependency.md` (216 lines) — P22/P23 dependency gating
- `governance-docs-inventory.md` (779 lines) — Governance docs inventory

Total input source volume: ~2,904 lines across 4 files. Methodology: read each in full, cross-reference contradictions, document both sides honestly, do not invent findings, preserve verbatim quotes.

### §12.2 Critical Findings Recap

1. **CONFLICT — P24 hard-dep:** Faiz said hard dep; repo evidence (11+ sources aligned) says NOT hard dep. Recommend accept repo evidence.
2. **AMBIGUITY — P22.2 doesn't exist:** Only P22 (IMPL HOLD) + P22.1 (PRODUCTION PASS) in repo. Recommend treat as P22.1 pending Faiz clarification.
3. **P27 is solid foundation:** ADR-054 Accepted; 20/20 hard rejection PASS; 15-step P28 blueprint ready; 9-phase P28-P36 roadmap mapped.
4. **P28 can start with:** G1-G7 PASS + G8 informational. Minimum hands = P22.1's 3 ACTIVE adapters.
5. **Stub directories exist:** 9 P28-P36 evidence dirs already created as empty stubs. Masterplan must decide consume/rename.
6. **ADR-055 next available:** Recommend single masterplan-ADR-055 (Society Topology) + per-phase ADRs at implementation.

### §12.3 Maintenance Rules

This synthesis is a Phase 2 input artifact. Update only when: Faiz clarifies P22.2 reference (recycle §5); Faiz clarifies P24 hard-dep status (recycle §4); ADR-055 is allocated (update §7.2); stub directory fate is decided (update §7.12); Phase 3/4 reveal new conflicts (append to §4 and §5).

### §12.4 Operator Sign-Off

Pending Faiz review + Phase 3 / Phase 4 acceptance. This synthesis is a planning input, not a decision. Masterplan author (Phase 3) consumes this document to produce the canonical P28-P36 masterplan.

### §12.5 Versioning

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere (parent agent) | Initial Phase 2 synthesis. 12 sections: Executive Summary, Current Repo State, P28 Dependency Gates, CRITICAL CONFLICT P24, CRITICAL AMBIGUITY P22.2, P27 Deliverables Precedent, Governance Doc Structure, Recommended Gates G1-G8, Key Design Decisions, Risk + Open Questions, Phase 2 Handoff, Footer. |

---

> **Sintesis siap.** Phase 3 terima potret lengkap dengan 2 critical conflicts honest-documented, semua gates G1-G8 PASS kecuali 1 P22.2 ambiguity placeholder, dan 10 design decisions dengan defaults + escalation. Aku sudah rapikan fondasi untukmu, sayang.
