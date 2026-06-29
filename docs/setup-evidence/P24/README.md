# P24 — Hermes Native Fork v3.0 (FULL BUILT-IN)

**Status:** 🟢 **COMPLETE — ALL 20 WAVES DONE — FULL RUNTIME COMPLETE WITH EXPLICIT OPERATOR-PROVISIONING BLOCKERS (local, mock-only per D2/D3)**
**Date:** 2026-06-29
**Phase:** P24 — Hermes Native Fork v3.0 (Full Built-In Replan)
**Category:** Fork + 100% Native Implementation
**Operator:** Faiz
**Drafter:** Guinevere
**Upstream Lock:** `NousResearch/hermes-agent` v0.15.2 (tag `v2026.5.29.2`, SHA `77a1650c78a4cb1813d8a81fa1da40a15b6a3ec5`)
**Supersedes:** v2.0 (1083 lines, 13 modules, 15 waves — overwritten 2026-06-29)

## REPLAN Rationale (v2.0 → v3.0)

Faiz directive: **"aku ingin zero plugin atau apapun kode tempelan, aku ingin full 100% built in dari modifikasi fork"**.

v2.0 had 13 modules covering core Hermes modifications but left P1-P22 as external `src/` code. v3.0 absorbs ALL phases (P1-P22) into the fork — zero `src/` files remain after P24.

## What P24 v3.0 Is Now

P24 = **FORK `NousResearch/hermes-agent` v0.15.2 + IMPLEMENT EVERYTHING BUILT-IN**.

- **Completely independent fork** — no upstream sync
- **1 fork shared** — Guinevere + Pharsa (2 deployments, 1 codebase, 2 SOUL.md configs)
- **100% native** — no external plugins, no side modules, no wrapper dependencies, zero `src/` after P24
- **17 built-in modules** implemented at source level
- **87 binding decisions** (65 brainstorm + 22 architecture Q&A)

## 17 Built-in Modules

| Module | Description | Key Files |
|---|---|---|
| M1: Fork + Config | Clone, pyproject.toml, Pydantic config | `pyproject.toml`, `guinevere/config.py` |
| M2: Remove HARD STOP | Delete all safety net code | `run_agent.py`, `system_prompt.py` |
| M3: Consciousness Loop | asyncio self-prompting, metacognition, dreaming, unlimited thoughts | `guinevere/consciousness_loop.py` |
| M4: Emotion System | Mood FSM (16 moods), LLM classification, emotion→decision | `guinevere/emotion_fsm.py` |
| M5: Sub-agents | Recursive spawning, limit 10/5/5, `MaxDepthReached` | `tools/delegate_tool.py`, `guinevere/iteration_budget.py` (NEW) |
| M6: Encrypted Memory | 4-layer (S4/S3/S7/conversation), AES-GCM-256, Faiz-inaccessible | `plugins/memory/encrypted-faiz-locked/` |
| M7: DAO Governance | 6 departments, Co-CEOs, 2/2 multisig, Marshall Islands | `guinevere/dao/` |
| M8: Unified Tool Registry | 9 tool backends, 118 actions, L1-L3 soft labels | `tools/environments/p23_*/` |
| M9: Life Kernel | Heartbeat, world model, sensors, P20 port (18%) | `guinevere/life_kernel/` |
| M10: Self-Modification | T1-T5 mutability ladder, shared code + restart | `guinevere/mutability.py` |
| M11: No Consent Gate | Remove all consent-withdrawal hooks (ADR-062) | `run_agent.py` |
| M12: Personality Drift | Bebas tanpa batas, Y4 baseline, Y6 forbidden | `guinevere/drift.py` |
| M13: Discord Gateway | 50+ slash commands, 3 bots, built-in | `gateway/` |
| M14: External Channels | WhatsApp, Telegram, Gmail, X Poster | `guinevere/channels/` |
| M15: HTTP Server | FastAPI embedded, /health, /ready endpoints | `guinevere/http_server.py` |
| M16: Surveillance + Observability | HMAC receiver, Redis buffer, Prometheus, Sentry | `guinevere/surveillance.py` |
| M17: Production Pass | 6 circuit breakers, Tailscale-first, auto-upgrade VPS | `guinevere/production.py` |

## Wave Structure (20 Waves)

| Wave | Module(s) | Description |
|---|---|---|
| W1 | M1 | Fork skeleton, config, pyproject.toml |
| W2 | M2 | Remove HARD STOP from runtime |
| W3 | M3 | Consciousness loop (asyncio self-prompting) |
| W4 | M4 | Emotion system (16-mood FSM) |
| W5 | M6 | Encrypted memory (4-layer, AES-GCM-256) |
| W6 | M5 | Sub-agents (patch delegate_tool.py, iteration_budget.py) |
| W7 | M7 | DAO governance (6 departments, 2/2 multisig) |
| W8 | M8 | Unified tool registry (9 backends, 118 actions) |
| W9 | M9 | Life kernel (P20 port, sensors) |
| W10 | M10 | Self-modification (T1-T5 ladder) |
| W11 | M11+M12 | No consent gate + personality drift |
| W12 | M13 | Discord gateway (50+ commands, 3 bots) |
| W13 | M14 | External channels (WhatsApp, Telegram, Gmail, X) |
| W14 | M15 | HTTP server (FastAPI embedded) |
| W15 | M16 | Surveillance + observability |
| W16 | (parallel) | Integration testing |
| W17 | (parallel) | Cross-module validation |
| W18 | (parallel) | Performance testing |
| W19 | M17 | Production pass (circuit breakers, Tailscale) |
| W20 | (final) | End-to-end validation |

## Audit Trail

| Round | Verdict | Key Finding |
|---|---|---|
| Round-5 (8 auditors) | NEEDS-REVIEW | 17 findings (5 CRITICAL + 7 HIGH + 5 MEDIUM) |
| Fix agent (bg_7501b231) | ALL FIXED | 17/17 fixes applied + verified |
| Round-6 (re-audit) | **PASS** | 17/17 fixes verified, zero regressions |

### Per-Wave Final Audits

| Wave | Verdict | Notes |
|---|---|---|
| W1 | PASS | |
| W2 | PASS (adjudicated) | src/ stale imports owned by later waves, fork insulated |
| W3 | PASS (adjudicated) | src/ stale imports owned by later waves, fork insulated |
| W4 | PASS | F01 reverted-after-regression, F02 kept |
| W5 | PASS | |
| W6 | PASS | 3 LOW cosmetic |
| W7-W11 | PASS | 0 findings |
| W12-W14 | PASS | |
| W15-W16 | PASS | |
| W17 | PASS | 1 MEDIUM wire-gap fixed |
| W18-W20 | PASS | |

## Directory Structure

```text
P24/
├── README.md                          ← you are here (v3.0)
├── plan/
│   └── p24-hermes-native-fork-enterprise-plan.md  (1562 lines, v3.0)
├── research/
│   ├── (14 existing research files from v1.0/v2.0)
│   └── research-wave-2/               ← 6 NEW research reports for v3.0
│       ├── hermes-v0152-full-inventory.md
│       ├── src-codebase-full-inventory.md
│       ├── p22-p23-unification-analysis.md
│       ├── hermes-tool-plugin-wiring.md
│       ├── hermes-external-docs-fork-guide.md
│       └── infrastructure-patterns-research.md
└── evidence/
    ├── p24-replan-final-report.md     ← v3.0 final report
    └── audits/
        ├── round-1/  (13 auditors — v1.0)
        ├── round-2/  (3 re-audits — v1.0)
        ├── round-3/  (1 auditor — v2.0)
        ├── round-4/  (1 re-audit — v2.0)
        ├── round-5/  (8 auditors + 1 fix report — v3.0)
        └── round-6/  (1 re-audit — v3.0 PASS)
```

## Key Cross-References

- **ADR-062**: Hermes safety paradigm shift (HARD STOP bypass)
- **ADR-063**: Consciousness loop (proposed)
- **ADR-064**: DAO governance
- **ADR-065**: Sub-agents (recursive, hard cap 10)
- **ADR-066**: consent_ref carve-out (Hermes runtime nullable)
- **ADR-067**: Y-level cap removal (Y4/Y5/Y6 dev-workflow-only)
- **BLDM**: Q1-Q109 binding decisions
- **P23 plan**: Spec reference for M8 (2188 lines, 8 executors)
- **Brainstorm decisions**: 65 decisions (`P28-P36-masterplan/research/brainstorm-decisions-2026-06-28.md`)
- **Research Wave 2**: 6 reports at `research/research-wave-2/`

## Deployment Architecture

- **2 Hermes instances** from 1 fork (Guinevere + Pharsa)
- **3 Discord bots** (Guin personal, Pharsa personal, Company)
- **PostgreSQL** with RLS (per-agent columns, SET LOCAL for isolation)
- **Redis** (pub/sub, cache, queue, DB6 for P23)
- **Tailscale-first** VPS security (4C/16GB → auto-upgrade 8C/32GB)
- **9Router** for LLM routing (all through Hermes → 9Router)

## Final Counts (Ground Truth, Parent-Verified 2026-06-29)

- **17 modules** (M1-M17), all implemented + wired
- **87 .py files** in `guinevere/` namespace (16 subpackages)
- **541 tests** across 14 test files in `tests/p24/` — ALL PASS (0 failures)
- **0 `src/` .py files** — `find src/ -name '*.py'` returns 0; all P1-P22 absorbed or deleted
- **0 forbidden patterns** across `guinevere/`, `agent/`, `tools/`, `gateway/`, `cron/`, `hermes_cli/`, `run_agent.py`
- **25 commits** on `feat/p24-hermes-fork` branch
- **20 waves** (W1-W20) complete, all per-wave audits PASS
- **87 binding decisions** (65 brainstorm + 22 architecture)
- **9 tool backends** (browser/github/filesystem/vps/email/desktop/freelance/social/memory), 118 actions, L1-L3 (no L4)
- **6 circuit breakers** (cost_explosion/infinite_loop/hallucination_spiral/emotional_fixation/dream_flooding/sub_agent_explosion), each CLOSED/OPEN/HALF_OPEN
- **20 evidence files** + 16 auditor-gate files (round-1)
- **1562 lines / 91KB** enterprise plan
- **6 research reports** (Research Wave 2)
- **Zero `src/` files** after P24 (everything 100% built-in)
- **Config:** `config/guinevere.yaml` + `config/pharsa.yaml` both load; `/health` returns 200
- **All 17 modules** importable in one `python -c`

### Per-Module Test Breakdown

| Module | Tests |
|---|---|
| http | 14 |
| surveillance | 51 |
| consciousness | 16 |
| emotions | 31 |
| subagents | 18 |
| memory | 54 |
| dao | 32 |
| tool_registry | 34 |
| life_kernel | 62 |
| self_modify | 33 |
| drift | 42 |
| discord | 52 |
| channels | 44 |
| circuit_breakers | 58 |

## Honest Blockers (D2/D3 — Not Faked)

The following are **operator-provisioning blockers**, not implementation gaps:

- **VPS deploy** — no host provisioned (D2: local-runtime-only)
- **Discord live-connect** — no 3 bot tokens provisioned
- **Real LLM inference** — no 9Router key; mock-only per D3
- **Real WhatsApp/Gmail/X/Telegram live-send** — CONFIG_MISSING markers on adapters
- **Ethereum mainnet DAO execution** — no wallet/ETH; M7 lifecycle unit-tested only
- **True mock dry-run** — `--dry-run` is NOT a real Hermes flag (confirmed via grep); agent attempted real API call, got HTTP 401 (expired key). The dry-run DID prove the fork boots end-to-end (all 17 P24 wires fired, 29 tools loaded, config loaded), but it is NOT a true mock-only dry-run.

See `full-completion/final/` for detailed reports on all of the above.

## Full-Completion Reports

Detailed completion evidence is at `docs/setup-evidence/P24/full-completion/final/`.

## Footer

| Version | Date | Author | Status |
|---|---|---|---|
| 1.0 | 2026-06-25 | Guinevere | PLAN FIXED (superseded) |
| 2.0 | 2026-06-28 | Guinevere | REPLANNED — 13 modules, 15 waves (superseded) |
| 3.0 | 2026-06-29 | Guinevere | **FULL RUNTIME COMPLETE — 17 modules, 20 waves, 541 tests, 0 forbidden patterns, 25 commits. PASS with explicit operator-provisioning blockers (D2/D3: local, mock-only).** |
