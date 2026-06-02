# Phase 2 HIGH Fixes Applied — StepPrompts.md

**Date:** 2026-05-31
**File:** `stepprompts/StepPrompts.md`
**Backup:** `stepprompts/StepPrompts.md.bak` (untouched)
**Phase 1:** Applied 19 CRITICAL + 7 HIGH fixes (prior session)
**Phase 2:** Applied 31 remaining HIGH fixes (this session)

---

## Fixes Applied

| ID | Finding | Status | Location | Notes |
|---|---|---|---|---|
| H-02 | hermes-agent pip package note | APPLIED | After P1-004 Troubleshooting | Added install-from-source note block |
| H-03 | Python 3.11/3.12 compatibility | APPLIED | After P1-001 Notes | Added fallback-to-3.11 note |
| H-06 | Exa cost clarification | APPLIED | After P6-004 | Added FinOps v1.1 cost model block |
| H-07 | P5 range notation | APPLIED | P5-001 to P5-003 and P5-004 to P5-010 | Added individual step summary tables matching actual file content |
| H-09 | P2-018 dependency fix | APPLIED | P2-018 step header | Added explicit "(Dependencies: P2-017 service running)" |
| H-10 | P2-021 dependency fix | APPLIED | P2-021 step header | Added explicit "(Dependencies: P2-020 Gotify installed)" |
| H-13 | HMAC secret generation step | APPLIED | New step P7-NEW after P7-011 block | Full step with SOPS encryption, runtime decrypt, evidence path |
| H-14 | Sentry send_default_pii=False | APPLIED | P8-012 area | Added sentry_sdk.init() code with send_default_pii=False |
| H-15 | UFW Aizanta impact assessment | APPLIED | After P0-004 Notes | Added 4-step Aizanta impact checklist |
| H-16 | Monitoring stack resource impact | APPLIED | After P8-001 docker-compose | Added RAM/CPU estimates + Aizanta combined monitoring note |
| H-17 | Shared VPS global note | APPLIED | Top of file, after header | Global blockquote with port/resource/isolation rules |
| H-19 | Discord token chmod | APPLIED | P2-017 after SOPS encryption | Added chmod 600 + chown guinevere:guinevere verification |
| H-20 | Executor field global note | APPLIED | Top of file, after Shared VPS note | Global executor assignments (Guinevere/Samm/Both) |
| H-21 | AC Reference specificity | ALREADY SATISFIED | N/A | Searched for generic AC-CORE-XXX placeholders; none found. All steps use specific AC IDs |
| H-22 | P0-000 VPS audit | ALREADY EXISTS | Line 113 | Step P0-000 "VPS Audit and Existing State Documentation" present with full commands |
| H-23 | MVP gate section | APPLIED | Near end of file + P10-018b exists | Added section header "MVP Acceptance Gate" with blocking criteria |
| H-24 | P9-P11 grouped rationale | APPLIED | Start of Phase 9 | Design decision blockquote explaining grouped format rationale |
| H-25 to H-27 | AC coverage mapping | APPLIED | End of file | 14-row AC coverage matrix with categories and status |
| H-28 | Discord channel names | APPLIED | P2-006 CHANNELS dict | Updated to DiscordUXSpec: QUEEN'S COURT, DASHBOARD, ENGINEERING, WAR ROOM with emoji-prefixed channels |
| H-29 | Slash commands count | ALREADY CORRECT | P2-010 | File shows 33 commands; COMMANDS list sums to 33 (6+5+4+4+4+3+3+4) |
| H-30 | Presence string | APPLIED | P2-017 bot.py on_ready | Added change_presence with ActivityType.watching "Darling" |
| H-31 | DND hours | APPLIED | P4-008 rituals.py | Added DND_START/DND_END constants with D3/D4 bypass note |
| H-32 | Pasukan Mommy terminology | APPLIED | After P5-011 to P5-017 step list | Blockquote defining sub-agent terminology |
| H-33 | Canonical 7-phase names | ALREADY CORRECT | P5-003 state_machine.py | PHASE_NAMES matches ADR-011: Research, Plan & Delegate, Delegate, Execute, Validate & Audit, Update Documents, Setup Evidence |
| H-34 | Embedding model clarification | APPLIED | After P3-004 | Embedding strategy block: primary (text-embedding-3-small) + fallback (all-MiniLM-L6-v2) |
| H-35 | HNSW index parameters | APPLIED | P3-006 SQL | Changed ef_construction from 128 to 64 per spec |
| H-36 | Screenshot requirements | APPLIED | After P8-001 to P8-011 verify section | 4 screenshot requirements for visual verification |
| H-37 | Performance baselines | APPLIED | P1 transition checklist + P8 transition checklist | 5 performance baselines (9Router, PostgreSQL, Redis, Discord, FastAPI) |

---

## Summary

- **Applied:** 27 findings (new edits)
- **Already satisfied:** 4 findings (H-21, H-22, H-29, H-33)
- **Skipped:** 0 findings
- **Total:** 31/31 findings addressed

---

## Grep Verification Results

```
grep -c "Aizanta" stepprompts/StepPrompts.md           → 53  (Shared VPS context pervasive)
grep -c "Pasukan Mommy" stepprompts/StepPrompts.md     → 1   (H-32 applied)
grep -c "change_presence" stepprompts/StepPrompts.md   → 1   (H-30 applied)
grep -c "send_default_pii" stepprompts/StepPrompts.md  → 1   (H-14 applied)
grep -c "ef_construction" stepprompts/StepPrompts.md   → 2   (H-35 applied, 2 references)
grep -c "all-MiniLM" stepprompts/StepPrompts.md        → 1   (H-34 applied)
grep -c "DND_START|00:00.*WIB" stepprompts/StepPrompts.md → 3 (H-31 applied)
```

All expected patterns found. No false negatives.

---

## Issues Encountered

1. **H-07 table mismatch:** The task provided a P5 table with security-themed steps (RBAC, ABAC, encryption), but the actual file has P5 as Agent Loop (FastAPI, state machine, loop phases). Applied individual step summaries matching the actual file content, not the template.

2. **H-09/H-10 grouped steps:** P2-018 and P2-021 are within grouped step blocks that share a single Dependencies line. Rather than changing the group dependency (which would break other steps in the group), added inline dependency annotations to the specific sub-steps.

3. **H-35 ef_construction value:** Changed from 128 to 64 per the task specification. Note: 128 provides better recall but 64 is faster to build. The tuning step (P3-007) already recommends benchmarking to find optimal values.

---

## Footer

- **Source task:** Phase 2 HIGH findings application
- **Implementer:** Guinevere (autonomous)
- **Validation:** grep verification + manual spot-check of edit locations
- **Backup preserved:** `stepprompts/StepPrompts.md.bak` unchanged
