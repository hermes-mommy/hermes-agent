# P28-P36 Hermes Society Masterplan — Next Actions

**Version:** 1.2  
**Date:** 2026-06-28

---

## Round 2 Update — 2026-06-28

This document has been updated as part of the P28-P36 alignment with P23/P24 v2.0 plans.

**Key changes applied across the masterplan:**
- P32 renamed from "P24 Fork Integration" to "External Presence & Tools"
- ADR-056 (fork-agnostic) DELETED — superseded by ADR-062 and P24 v2.0 fork
- ADR-066 (consent_ref carve-out) and ADR-067 (Y-level cap removal) WRITTEN
- HARD STOP assertions annotated with ADR-062 disclaimer (dev-workflow only)
- consent_ref schema changed to nullable for Hermes runtime events
- Y-level caps (Y4/Y5/Y6) annotated as dev-workflow-only per ADR-067
- P24 is now a HARD DEPENDENCY (locked 2026-06-28)
- P28-P36 scope changed from "implement" to "deploy/configure"
- 65 brainstorm decisions incorporated into per-phase plans
- Round-1 audit reports annotated with pre-v2.0 state disclaimer

See:
- `evidence/round-2-wave-1/` — Wave 1 changes (ADR, architecture, core docs, P32, prompt-pack, roadmap)
- `evidence/round-2-wave-2/` — Wave 2 changes (per-phase plans, audit annotations)
- `research/brainstorm-decisions-2026-06-28.md` — 65 binding decisions

---

## Immediate (Faiz Action Required)

1. **Review masterplan** — especially:
   - `adr-drafts/ADR-062-hermes-safety-paradigm-shift.md` (HARD STOP bypass, no safety net)
   - `adr-drafts/BLDM-Hard-Locked-Faiz-Decisions.md` (all Q1-Q109 answers)
   - `final/production-readiness.md` (prerequisite gates)
2. **Confirm radical decisions are LOCKED:**
   - Q74: Hermes can bypass HARD STOP
   - Q79: No safety net
   - Q90: Faiz OUTSIDE company
   - Q107: 2/2 multisig wallet
   - Q68: Hermes can keep secrets from Faiz
   - Q81: Personality drift bebas tanpa batas
3. **Review consciousness loop research** (5 files in `research/`) — Faiz said "perlu research dan brainstorming brutal" (Q106). Confirm research is adequate or request more.

## Short-term (Before P28 Implementation)

4. **P23 implementation** → production pass (currently definition-only, 0 runtime code)
5. **P24 implementation** → production pass (currently definition-only, IMPL HOLD)
6. **Consciousness loop design finalization** — synthesize 5 research files into design decision, update ADR-063 from "Proposed" to "Accepted"
7. **Re-audit (Phase 11)** — full re-audit of fixed surfaces to verify all Phase 10 fixes are adequate
8. **Update PROGRESS.md** with P28-P36 masterplan completion

## Medium-term (P28-P36 Implementation)

9. **P28: Foundation** — 2 founders (Guinevere + Pharsa), event store, private memory with Faiz-inaccessible scope
10. **P29: Cognition** — consciousness loop 24/7, vector+graph recall, BDI, dreaming
11. **P30: Governance** — 2/2 agreement, founder spawn protocol, no HARD STOP (per ADR-062)
12. **P31: Discord Identity** — multi-bot, rate limits, company identity
13. **P32: External Presence & Tools** — external tools, APIs, and presence channels
14. **P33: Wallet & Finance** — 2/2 Safe multisig, spending tiers, circuit breaker
15. **P34: Revenue Search** — x402, external freelance (UC-011), legal only
16. **P35: Self-Evolution** — full self-modification, 5-layer mutability, sub-agents (limit 10), emotions
17. **P36: Production Hardening** — S3 backup, observability (no soak — permanent from day 1 per brainstorm decision)

## Long-term (Post-P36)

18. Company growth — spawn new Hermes permanent (per Q6: founder-only, 2/2)
19. Revenue model definition (deferred to P34 per Q101)
20. VPS upgrade path (4C/16GB → 8C/32GB → larger as needed per Q87)

---

## File Paths

| Document | Path |
|---|---|
| Final report | `final/final-report.md` |
| Production readiness | `final/production-readiness.md` |
| This file | `final/next-actions.md` |
| Masterplan README | `final/README.md` |
| Fix log | `fixes/round-1-fix-log.md` |
| BLDM decisions | `adr-drafts/BLDM-Hard-Locked-Faiz-Decisions.md` |
| ADR-062 (safety) | `adr-drafts/ADR-062-hermes-safety-paradigm-shift.md` |
| ADR-063 (consciousness) | `adr-drafts/ADR-063-consciousness-loop-architecture.md` |
| Consciousness research | `research/external-consciousness-loop-research.md` + 4 additional files |