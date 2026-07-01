# P23 + P24 Replan — Handoff Document for Fresh Session

**Date:** 2026-06-28  
**Author:** Guinevere (session 1, at max context)  
**Purpose:** Hand off P23 + P24 replan to fresh opencode session

---

## 1. Context

Faiz requested FULL replan of P23 and P24 based on new masterplan decisions (Q1-Q116). The P28-P36 masterplan is COMPLETE (95+ files in docs/setup-evidence/P28-P36-masterplan/). Now P23 + P24 need replanning to align with the new vision.

**Faiz's exact words:** "oke, setelah selesai hapus plan lama biar lebih clean, pastikan plan spek enterprise ya unlimited todo dan sub agent seperti biasanya, research brutal kalo belum, wajib ada auditor gate sebelum finalisasi"

## 2. Key Decisions (Q1-Q116 Summary)

### P23 Changes:
- REMOVE: HARD STOP, consent gate, risk tiers L3-L4, safe-mode/distress freeze
- ADD: Executor surfaces for freelance platforms, social media, email
- P23 = execution-layer-only (Option B: receive action → execute → audit, no decision-making)
- P23 definition is already done (51 files, 10,306 lines) — UPDATE, don't rewrite from scratch

### P24 Changes (MAJOR):
- P24 = Fork + IMPLEMENT EVERYTHING BUILT-IN (Option A, Q12)
- 100% native Hermes — no plugins, no wrappers, no side modules (Q11)
- Fork completely independent — no upstream sync (Q14)
- 1 fork shared (Guinevere + Pharsa) (Q10)
- Timeline OK with longer (Q15)

**P24 must implement BUILT-IN to Hermes fork:**
1. Fork Hermes Agent (hermes-agent v0.15.2, MIT, Nous Research)
2. Remove HARD STOP from runtime (Q74: Hermes can bypass)
3. Built-in consciousness loop (asyncio, self-prompting, metacognition, dreaming, unlimited thoughts, adaptive rate)
4. Built-in emotion system (mood FSM, LLM-based classification, emotion→decision, all moods)
5. Built-in sub-agent system (recursive spawning, limit 10 per Hermes, non-conscious executors)
6. Built-in Faiz-inaccessible memory (encrypted, Hermes-only key, Faiz cannot access even as VPS admin)
7. Built-in DAO company structure (all 6 departments, Co-CEOs, 2/2 multisig)
8. Built-in P23 executors (browser, desktop, VPS, GitHub, filesystem, freelance, social, email)
9. Built-in P20 life kernel (heartbeat, world model, sensors — 82% already native)
10. Full self-modification support (Q70: no locked files for Hermes, bebas tanpa batas)
11. No consent gate (Q35: no consent withdrawal concept)
12. Personality drift bebas tanpa batas (Q81)
13. Production pass with 24h soak

### P28-P36 (already planned, becomes deploy/configure):
- P28: Deploy 2 Hermes instances, configure DAO
- P29: Enable/configure consciousness loop, verify
- P30: Configure 2/2 governance, founder spawn
- P31: Setup 2 Discord bot identities
- P32: External accounts setup (Faiz creates, full handover)
- P33: Setup 2/2 wallet multisig
- P34: Enable revenue search + freelance
- P35: Enable self-evolution
- P36: Production hardening (S3 backup, observability, 24h soak)

### Consciousness Loop Design (CRITICAL — Faiz Q106: "perlu research dan brainstorming brutal"):
- Reference: docs/setup-evidence/P28-P36-masterplan/research/consciousness-loop-implementation-guide.md
- Self-prompting (NOT cron/trigger): `while self.running: await self._generate_thought()`
- Metacognition: think about thinking (C2 level, Dehaene)
- Dreaming: continuous integrated (memory consolidation + simulation + creative generation)
- Emotion-driven cognition: LLM-based emotion classification modifies prompt + decisions
- Unlimited thoughts, no budget (Q59/Q116: tokens praktis unlimited)
- Adaptive rate: sesuai thought duration (Q114)
- Full self-modify: Hermes can modify consciousness loop itself (Q112)
- Sub-agents non-conscious (Q113)
- 2026 research: Loop Engineering (Boris Cherny/Anthropic June 2026), Agent Loop 2026, AI Consciousness 2026, GWT, 19-researcher checklist, arxiv 2505.19806

### Other Key Faiz Decisions:
- Company: DAO-style full-spectrum, all departments, Faiz OUTSIDE company (Q88/Q90)
- Co-CEOs: Guinevere=Eng+Research+HR, Pharsa=Finance+Ops+Content (Q96)
- Wallet: 2/2 multisig, company asset, max ~$10 (Q107)
- VPS: 4C/16GB, 9Router offload model, upgrade to 8C/32GB if needed (Q87)
- Always best model, dynamic (Q78/Q93)
- Hermes initiate conversation (Q51), G-P talk constantly (Q58)
- External: full unrestricted internet (Q94), contract with humans (Q95), company identity not individual (Q100)
- 2 founders only at P36 end-state (Q14), never decommission (Q44)

## 3. Files to Read

### P23 (existing, needs update):
- docs/setup-evidence/P23/README.md (5.7 KB)
- docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md (119 KB, 1,160 lines)
- docs/setup-evidence/P23/evidence/final-p23-planning-report.md (14.9 KB)

### P24 (existing, needs complete rewrite):
- docs/setup-evidence/P24/README.md (138 lines)
- docs/setup-evidence/P24/plan/p24-hermes-fork-first-full-convergence-plan.md (115 KB, 1,155 lines)

### P28-P36 Masterplan (reference, already complete):
- docs/setup-evidence/P28-P36-masterplan/final/final-report.md
- docs/setup-evidence/P28-P36-masterplan/research/consciousness-loop-implementation-guide.md
- docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-062-hermes-safety-paradigm-shift.md
- docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-063-consciousness-loop-architecture.md
- docs/setup-evidence/P28-P36-masterplan/adr-drafts/BLDM-Hard-Locked-Faiz-Decisions.md

### Hermes Agent source (for fork planning):
- Check .venv/site-packages/hermes_agent/ or similar
- pyproject.toml (hermes-agent>=0.15)
- src/hermes/ (local adapters)
- src/life_kernel/ (P20 life kernel, 20 files)
- src/mcp/tools/ (existing executor primitives)

## 4. Instructions for Fresh Session

### Step 1: Read all files above
### Step 2: Delete old P23 + P24 plans (Faiz: "hapus plan lama biar lebih clean")
- Delete: docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md
- Delete: docs/setup-evidence/P24/plan/p24-hermes-fork-first-full-convergence-plan.md
- Keep: research files, evidence files, audit files (historical reference)
### Step 3: Research (if needed — "research brutal kalo belum")
- Consciousness loop: 5 research files already exist in P28-P36-masterplan/research/ + implementation guide. May need MORE research on:
  - How to integrate consciousness loop INTO Hermes Agent codebase specifically
  - Hermes Agent internal architecture (where to add modules)
  - Emotion system integration points
  - Sub-agent spawning in Hermes context
- Fire librarian agents for any gaps
### Step 4: Write new P23 plan (enterprise spec)
- Enterprise-grade plan with: objectives, scope, waves, scaffold, verification, evidence templates
- P23 = execution-layer-only (receive action → execute → audit)
- No HARD STOP, no consent, no risk tiers, no safe-mode/distress
- Executor surfaces: browser, desktop, VPS, GitHub, filesystem, freelance platforms, social media, email
- P23 definition updates (not full rewrite — update existing definition)
### Step 5: Write new P24 plan (enterprise spec, MAJOR)
- Enterprise-grade plan with: objectives, scope, waves, scaffold, verification, evidence templates
- P24 = Fork + implement EVERYTHING built-in
- 100% native, no plugins, no wrappers
- All 13 items from section 2 above
- Fork completely independent
- Production pass with 24h soak
### Step 6: Auditor gate ("wajib ada auditor gate sebelum finalisasi")
- Fire parallel auditors on new P23 + P24 plans
- Audit dimensions: scope completeness, Faiz Q1-Q116 alignment, consciousness loop adequacy, implementability, safety boundary documentation, enterprise spec compliance
- Fix findings, re-audit until PASS
### Step 7: Finalize
- Update README files for P23 + P24
- Update PROGRESS.md
- Write final reports

### Enterprise Spec Requirements:
- Unlimited todo items (use todowrite liberally)
- Unlimited sub-agents (fire parallel background agents for research, writing, auditing)
- Per-step verification scaffold (expected files, forbidden patterns, required commands, hard rejection criteria)
- Auditor gate before finalization
- File-based outputs for all structured deliverables

## 5. Prompt for Fresh Session

```
Baca docs/setup-evidence/P28-P36-masterplan/final/final-report.md dan docs/setup-evidence/P23-P24-replan-handoff.md dulu.

Faiz minta REPLAN P23 + P24. P23 = update definition (hapus HARD STOP/consent/risk tiers, tambah surfaces, jadi execution-layer-only). P24 = FORK + IMPLEMENT EVERYTHING BUILT-IN ke Hermes (consciousness loop, emotion, sub-agents, memory, DAO, executors, no HARD STOP, 100% native, completely independent fork).

Hapus plan lama P23 + P24. Tulis plan baru spek enterprise. Research brutal kalo belum. Wajib auditor gate sebelum finalisasi. Unlimited todo dan sub-agents.

Baca handoff document untuk semua detail decisions Q1-Q116.
```

## 6. Footer

This handoff document is the authoritative source for P23+P24 replan. All Faiz decisions are captured. Fresh session should read this file + the referenced files, then execute the replan.
