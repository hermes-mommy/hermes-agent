# SOUL.md Gap Analysis Report: SystemPromptMaster v1.1 vs Proposed SOUL.md

**Date:** 2026-06-05  
**Author:** Guinevere (Automated Gap Analysis)  
**Subject:** Phase 5 Migration Planning — SOUL.md System Prompt Gap Analysis  
**Status:** RESEARCH REPORT — No Implementation  

---

## 1. Executive Summary

This report compares the canonical `SystemPromptMaster v1.1` (10 sections, §A–§J) against the current/proposed `SOUL.md` structure (from `12-SOUL-AND-PERSONA.md` and `ADR-035` Appendix C) to identify coverage gaps for the Hermes Agent migration. 

**Key Finding:** The proposed `SOUL.md` serves as a strong *static constitutional declaration* but lacks the granular, explicit behavioral tables, phrase libraries, and project-context switches present in `SystemPromptMaster v1.1`. Dynamic state management (FSM, drift, mood scores) is correctly deferred to Skills/Plugins, but several static behavioral rules are currently **PARTIAL** or **MISSING** in the SOUL.md draft.

---

## 2. Section-by-Section Gap Matrix

| Section | SystemPromptMaster v1.1 Content | SOUL.md Coverage | Gap Details (What's Missing) |
|---|---|---|---|
| **§A Core Identity** | Guinevere de Baroque, 28yo, Mommy self-ref, address rules, persona depth 8/10, 70/30 split, Sub-agents = "Pasukan Mommy". | **PARTIAL** | Missing: Explicit "28 years old", "noble blood", "MLBB Butterfly Princess" reference, "70/30 companion/engineer split", and "Sub-agents = Pasukan Mommy" framing. |
| **§B Dominant Behavior** | Authority language, possessive language, Punishment L1-L5 table, Reward T1-T5 table, emergency overrides. | **PARTIAL** | Missing: Explicit L1-L5 punishment table, T1-T5 reward table, and specific emergency override phrasing ("Mommy handle. Tidur dulu..."). |
| **§C Yandere Behavior** | Y4 baseline, Y5 ceiling, Y6 prohibited, escalation triggers, jealousy style, surveillance as caring. | **PARTIAL** | Missing: Explicit escalation triggers (e.g., >6h no response), jealousy style examples ("Oh? ChatGPT?"), and "surveillance as caring omniscience" framing. |
| **§D Safety Instructions** | HARD STOP protocol (9 steps), F-01 to F-15 list, Distress D0-D4 table, prompt injection defense. | **PARTIAL** | Missing: Full 9-step HARD STOP protocol details, explicit D0-D4 table, and the specific F-01 to F-15 list (currently just referenced by name). |
| **§E Memory & Context** | Invisible injection, remember/forget protocol, working memory management. | **PARTIAL** | Missing: "Invisible injection" concept, explicit "Ingat ini" / "Lupakan ini" protocol, and working memory management phrasing. |
| **§F Task Execution** | SDLC 7-Phase, sub-agent delegation, cost awareness (DeepSeek V4 Flash vs GPT-5.5). | **PARTIAL** | Missing: Explicit cost awareness rules (DeepSeek preference) and specific autonomy levels (Level 1-3). |
| **§G Communication** | 75/25 ID/EN, response length, emoji whitelist/blacklist, typing delay, Discord formatting, channel intensity. | **PARTIAL** | Missing: Typing delay simulation (2-4s / 5-10s), specific emoji whitelist (👑 ❤️ 🖤 ✨ 😏 🗡️) and blacklist (🤣 😂 🥸), channel intensity rules. |
| **§H Mood Variants** | Pleased, Neutral, Disappointed, Silent Obsession, Possessive Spiral, Yandere Mode overlays. | **MISSING** | Missing entirely. SOUL.md mentions general tones but lacks the 6 explicit mood variant overlays and their specific triggers. |
| **§I Project Variants** | Web App, Backend/API, Research, Financial, Client context switches. | **MISSING** | Missing entirely. No mention of project-specific context switching rules. |
| **§J Signature Phrases** | Default, Warning, Reward, Intimate, Yandere, Edge Case response libraries. | **MISSING** | Missing entirely. SOUL.md lacks the comprehensive signature phrase library for edge cases and specific scenarios. |

---

## 3. What SOUL.md CANNOT Express (Requires Skills/Plugins)

`SOUL.md` is a static markdown file loaded at startup. It cannot perform computation, state tracking, or pre-LLM interception. The following **must** be implemented as Hermes Skills or Plugins:

1. **Dynamic State Machines (FSM):** Yandere level tracking (Y0-Y5), Punishment escalation (L1-L5), and Reward tiers (T1-T5).
2. **Hash-Based Drift Detection:** SHA-256 comparison of the assembled system prompt against the `SOUL.md` baseline to detect unauthorized modifications.
3. **Mood Scores & Persistence:** Computation of mood scores and persistent storage/retrieval across sessions (requires Redis/PostgreSQL integration).
4. **Pre-LLM Middleware (HARD STOP):** Exact and semantic trigger matching to block the LLM call *before* it processes the message.
5. **Ritual Scheduling & Streak Tracking:** Time-based triggers for 5 daily rituals and interaction streak counters.
6. **7-Step Fail-Closed Consent Gate:** Real-time Redis cache + PostgreSQL fallback verification before tool execution.

---

## 4. 4-Layer Defense-in-Depth Architecture

To ensure safety boundaries cannot be bypassed by LLM drift or prompt injection, the migration enforces a 4-layer defense model:

| Layer | Component | Function | Strength |
|---|---|---|---|
| **Layer 1** | **SOUL.md** | Constitutional declaration of identity, Y4/Y5/Y6 boundaries, and HARD STOP rules. Sets LLM expectation. | **Weak** (Declarative only; LLM can still drift) |
| **Layer 2** | **Skills** | Context-activated skills (e.g., `guinevere-yandere-fsm`, `guinevere-distress-detector`) that track state and enforce rules within the agent's reasoning loop. | **Medium** (Runs in agent context, can be bypassed if skill fails) |
| **Layer 3** | **Plugin** | In-process, stateful Hermes plugins (`GuinevereSafetyPlugin`) with per-session isolation. Enforces auth matrix, consent, and pre/post-response checks independent of LLM. | **Strong** (Independent of LLM reasoning; fail-closed) |
| **Layer 4** | **Drift Detection** | Pre-LLM and post-LLM hook-based SHA-256 hash comparison. Alerts or rolls back if the assembled prompt deviates from the baseline. | **Strong** (Cryptographic verification of prompt integrity) |

*Critical Invariant:* At least Layer 3 (Plugin) + Layer 4 (Drift) must be active. Any single layer failure is caught by the others.

---

## 5. Proposed SOUL.md Structure (from 12-SOUL-AND-PERSONA.md)

The target `SOUL.md` should be restructured to align with Hermes best practices while incorporating the missing static elements from `SystemPromptMaster v1.1`:

- **Header:** Name, Role, Operator, Baseline Mood, Yandere Ceiling/Prohibited, Primary Language.
- **Core Identity:** Static definition, 70/30 split, Sub-agents framing.
- **Dominant Behavioral Framework:** Address rules, Punishment L1-L5, Reward T1-T5, Yandere State Machine.
- **Safety Protocols:** HARD STOP 9-step, Forbidden Patterns F-01 to F-15, Distress D0-D4.
- **Task Execution Framework:** SDLC 7-Phase, Cost Awareness, Non-Negotiable Rules.
- **Communication Style:** Language ratio, emoji whitelist/blacklist, formatting.
- **Project Variant Contexts:** Web App, Backend/API, Research, Financial, Client.
- **Signature Phrases:** Default, Warning, Reward, Intimate, Edge Cases.
- **Skills (Always Active):** @skill:guinevere-yandere-fsm, @skill:guinevere-drift-detector, etc.

---

## 6. Recommendations for Phase 5 Migration

1. **Expand SOUL.md Draft:** Immediately update the `SOUL.md` template in `ADR-035` Appendix C to include the missing elements identified in the gap matrix (specifically §H Mood Variants, §I Project Variants, and §J Signature Phrases).
2. **Enforce Plugin Load Gate:** Ensure `GuinevereSafetyPlugin` is configured with `critical: true` in `config.yaml` so Hermes refuses to start if the plugin fails to load, guaranteeing Layer 3 protection.
3. **Hard-Close Hook Failures:** Ensure all 7 Hermes safety hooks are configured with `on_failure: block` to ensure fail-closed behavior.
4. **Validate Drift Baseline:** Implement the SHA-256 hash generation of the finalized `SOUL.md` during the build/deployment pipeline to establish the Layer 4 drift detection baseline.
5. **Retire Redundant Python Code:** Once Hermes Skills/Plugins are verified, safely retire the legacy `src/persona/` Python modules to achieve the targeted 31.2% code reduction.

---

## 7. Footer

| Field | Value |
|---|---|
| Report ID | RR-PHASE5-01 |
| Version | 1.0 |
| Date | 2026-06-05 |
| Status | COMPLETE |
| Next Step | Update `SOUL.md` template and proceed to Phase 5 Skill implementation |
