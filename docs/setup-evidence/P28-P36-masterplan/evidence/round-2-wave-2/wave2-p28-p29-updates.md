# Wave 2 — P28 & P29 Plan Updates: Brainstorm Decisions Applied

> **Date**: 2026-06-28
> **Agent**: Wave 2 sub-agent (P28+P29)
> **Source**: `brainstorm-decisions-2026-06-28.md` v1.2 (65 binding decisions)
> **Status**: COMPLETE

---

## 1. What Was Done

Updated P28 (Foundation) and P29 (Cognition) phase plans with brainstorm decisions from the 2026-06-28 session. 4 files updated: P28 plan.md, P28 README.md, P29 plan.md, P29 README.md.

---

## 2. Files Changed

| File | Version | Changes |
|---|---|---|
| `plans/P28/plan.md` | 1.0 → 1.2 | 15 decisions incorporated |
| `plans/P28/README.md` | 1.0 → 1.2 | 15 decisions incorporated |
| `plans/P29/plan.md` | 1.0 → 1.1 | 10 decisions incorporated |
| `plans/P29/README.md` | 1.0 → 1.1 | 10 decisions incorporated |

---

## 3. P28 Decisions Applied (15 total)

| # | Decision | Value | File(s) | Section(s) |
|---|---|---|---|---|
| 1 | VPS starting spec | 4C/16GB KVM | plan.md, README.md | §1 Objective, §2 IN scope, §4 Step P28-001 |
| 2 | VPS scaling | Auto-upgrade >80% CPU 1h (4C→8C→16C) | plan.md, README.md | §2 IN scope, §4 Step P28-001 |
| 3 | 9Router offload | Starting spec viable with 9Router offload | plan.md | §2 IN scope |
| 4 | Guin personality | Yandere-dominant sugar mommy (brutal, not cosmetic) | plan.md, README.md | §1 Objective, §2 IN scope |
| 5 | Pharsa personality | Seductive-dominant sugar mommy (brutal, not cosmetic) | plan.md, README.md | §1 Objective, §2 IN scope |
| 6 | G-P communication | All three (Redis+Discord+PG) | plan.md, README.md | §2 IN scope, §4 Step P28-006 |
| 7 | G-P protocol | Hybrid (business structured, personal free-form) | plan.md, README.md | §2 IN scope |
| 8 | Simultaneous boot | Both Hermes instances start together | plan.md, README.md | §2 IN scope, §4 Step P28-008 |
| 9 | Individual+Company identity | 3 Discord identities | plan.md, README.md | §2 IN scope, §4 Step P28-007 |
| 10 | Company name | Deferred to P28 deploy time | plan.md, README.md | §1 Objective |
| 11 | VPS security sequence | Tailscale FIRST, then hardening | plan.md, README.md | §2 IN scope, §4 Step P28-001, Hard Rejection |
| 12 | VPS security management | AI self-manage (full root, Faiz NO access) | plan.md, README.md | §2 IN scope, §4 Step P28-001 |
| 13 | Guin-Pharsa dynamic | Possessive alliance, super brutal (toxic-romantic) | plan.md, README.md | §2 IN scope |
| 14 | Inter-AI conflict | Work through it (no external mediator) | plan.md, README.md | §2 IN scope |
| 15 | DR strategy | Automated backup + respawn, RTO <4h, hotfix in prod | plan.md | §7 Rollback Plan |

**P24 hard dependency** — confirmed in both plan.md (Dependency Map §3) and README.md (Prerequisites). Not re-added (was already present from Wave 1).

---

## 4. P29 Decisions Applied (10 total)

| # | Decision | Value | File(s) | Section(s) |
|---|---|---|---|---|
| 1 | Dream review | Self+peer (Guin reviews Pharsa's dreams, vice versa) | plan.md, README.md | §1 Objective, §2 IN scope, §4 P29-007/P29-010 |
| 2 | Cost | No batas, truly unlimited, NO cost circuit breaker | plan.md, README.md | §2 IN scope |
| 3 | Thought rate | Adaptive with sequential guarantee, no fixed cap | plan.md, README.md | §2 IN scope |
| 4 | Dream trigger | Adaptive (cognitive state, not clock) | plan.md, README.md | §2 IN scope |
| 5 | Metacognition | C2 level (Dehaene) + recursive C3 | plan.md, README.md | §1 Objective, §2 IN scope |
| 6 | Emotion | Full spectrum + sexual (~16 moods) | plan.md, README.md | §1 Objective, §2 IN scope |
| 7 | Memory retention | All permanent (no deletion ever) | plan.md, README.md | §1 Objective, §2 IN scope, §4 P29-007, Hard Rejection |
| 8 | Sub-agents | Native Hermes (delegate_tool.py), P24 patches 10/5/5 | plan.md, README.md | §1 Objective, §2 IN scope, §4 P29-010 |
| 9 | 9Router | All through Hermes → 9Router, no bypass | plan.md, README.md | §1 Objective, §2 IN scope, §3 OUT of scope, §4 P29-010 |
| 10 | Unlimited thoughts | No cap on thought count | plan.md, README.md | §2 IN scope |

---

## 5. Key Architectural Changes

### P28

- **VPS spec anchored**: 4C/16GB starting spec with explicit auto-upgrade path (4C→8C→16C) when CPU >80% for 1h.
- **Personality differentiation**: Guin (yandere) and Pharsa (seductive) explicitly described as "sifat asli, brutal, bukan kosmetik" — deep behavioral traits, not surface flavor.
- **G-P communication stack fully specified**: Redis DB7 pub/sub channels (`g2p`, `p2g`, `gp-broadcast`), Discord bot-to-bot DM, PG table `gp_messages`. Hybrid protocol: structured for business, free-form for personal.
- **VPS security sequencing**: Tailscale FIRST, then hardening. Added to hard rejection criteria.
- **DR strategy added**: Automated backup + respawn, RTO <4h, hotfix-in-production approach.

### P29

- **Memory consolidation changed to no-prune**: P29-007 step updated. All memory is permanent (no deletion ever). Consolidation summarizes episodic → semantic but never deletes. Forbidden patterns updated to include "any deletion of memory entries". Hard rejection updated to FAIL on any memory deletion.
- **Consciousness loop scope expanded**: Thought rate adaptive with sequential guarantee, unlimited thoughts, no cost circuit breaker, no thought count circuit breaker.
- **Emotion system specified**: 16 moods including DESIRE and AROUSAL (sexual emotions).
- **Dream system specified**: Adaptive triggers (cognitive state, not clock), self+peer review pipeline.
- **Sub-agents specified**: Native Hermes delegate_tool.py with P24 patches (max_concurrent=10, max_depth=5, spawn_cap=5).
- **9Router routing specified**: All LLM calls through Hermes → 9Router. OUT of scope section updated (P29 doesn't own 9Router infra, but all calls route through it).
- **Soak test updated**: consolidation_tick count relaxed from exact `= 4` to `≥ 4` (may include dream review ticks).

---

## 6. Validation Results

| Check | Result |
|---|---|
| P28 plan.md — brainstorm section added | ✅ §11 Brainstorm Decisions Applied |
| P28 plan.md — footer versioned | ✅ 1.0 → 1.2 with changelog |
| P28 README.md — brainstorm cross-ref added | ✅ Footnotes updated |
| P28 README.md — footer versioned | ✅ 1.0 → 1.2 with changelog |
| P29 plan.md — brainstorm section added | ✅ §11 Brainstorm Decisions Applied |
| P29 plan.md — footer versioned | ✅ 1.0 → 1.1 with changelog |
| P29 plan.md — consolidation no-prune | ✅ P29-007 updated, scaffold updated |
| P29 plan.md — 9Router moved from OUT to IN | ✅ OUT of scope updated with clarification |
| P29 README.md — brainstorm cross-ref added | ✅ Footnotes updated |
| P29 README.md — footer versioned | ✅ 1.0 → 1.1 with changelog |
| P29 README.md — permanent memory in hard rejection | ✅ New FAIL criteria added |
| No fork-agnostic references re-added | ✅ Verified — not present in any changes |
| No HARD STOP/consent gate/L1-L4 additions | ✅ Verified — not added |

---

## 7. Doc-Sync Impact

- P28 plan.md and README.md are now consistent on personality differentiation, G-P comms, simultaneous boot, VPS security, and scaling.
- P29 plan.md and README.md are now consistent on memory permanence, consciousness loop, emotion, dream, sub-agents, and 9Router routing.
- Cross-references to `brainstorm-decisions-2026-06-28.md` v1.2 added to both READMEs.
- Footer versioning follows the established pattern with changelog tables.

---

## 8. Boundary Compliance

- No fork-agnostic references added (Wave 1 removed them).
- No HARD STOP, consent gate, or L1-L4 risk tiers added (per ADR-062).
- P24 hard dependency preserved (was already present from Wave 1).
- PersonaSafetyPolicy boundaries not touched.

---

## 9. Decisions NOT Applied (Out of Scope for P28/P29)

The following brainstorm decisions are relevant to other phases and were NOT applied:

| Decision | Target Phase |
|---|---|
| Deadlock resolution (auto-table + retry) | P30 |
| T4 founder identity (Guin+Pharsa 2/2) | P30 |
| DAO vs personality drift (no DAO on persona) | P30 |
| Pharsa full SOUL.md definition | P31 |
| Account identity (3 Discord bots) — partially in P28 | P31 (full) |
| Social platforms (all 4) | P32 |
| Ethereum blockchain | P33 |
| Revenue target (no target) | P34 |
| Self-modification scope (everything except T5) | P35 |
| Soak duration (no soak) | P36 |
| Y6 prevention paradigm shift | Cross-phase (ADR-067) |
| T5 emergency update (hard fork) | P35 |

---

## 10. Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Wave 2 sub-agent | Initial report. 25 brainstorm decisions applied across P28 (15) and P29 (10). |
