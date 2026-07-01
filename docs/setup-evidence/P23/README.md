# P23 — Execution Layer (REPLANNED)

**Status:** 🟡 **DRAFT — REPLAN PLAN WRITTEN, AWAITING AUDITOR GATE**
**Date:** 2026-06-28
**Phase:** Expansion (P23) — REPLAN
**Owner:** Faiz (operator)
**Drafter:** Guinevere
**Supersedes:** `p23-embodied-operations-enterprise-plan.md` (DELETED 2026-06-28)

## REPLAN Rationale

The previous P23 plan baked a 7-step policy gate (classify → HARD-STOP → distress → consent → namespace → execute → audit), L1-L4 risk tiers, `SemanticActionClassifier`, `AuthLevel` 1:1 mapping, Faiz-in-the-loop approval, and `life_kernel:hard_stop` runtime listener. Faiz Q34/Q35/Q74/Q79/Q80 paradigm-shifted (per ADR-062 + BLDM Section 6) — Hermes Society runtime has NO HARD STOP, NO consent-withdrawal concept, and Faiz holds only emergency-kill via Hermes-consumed kill stamp.

P23 is now a **pure execution layer**: Hermes (P24) owns ALL decisions; P23 executors just `receive action → execute → return result + audit trail`.

## What P23 Is Now

P23 is the **execution layer** of the Hermes Society runtime — 8 executor surfaces registered as **built-in tools inside the Hermes Agent fork** (`tools/registry.py`) that Hermes calls directly via the tool registry to perform real-world actions.

P23 executors are pure: **receive action dict → execute → return result dict + audit trail**. They do NOT classify risk, gate by consent, or hold a policy decision. Every decision lives upstream in Hermes.

## 8 Executor Surfaces

| Executor | Surface | Status |
|---|---|---|
| Browser | Obscura CDP (Chrome DevTools Protocol) | Existing MCP adapter → refactor to Hermes native |
| Desktop | Windows automation (pyautogui/uiautomation) | Existing MCP adapter → refactor |
| VPS | SSH + Docker + systemd | Existing MCP adapter → refactor |
| GitHub | GitHub CLI + API | Existing MCP adapter → refactor |
| Filesystem | Read/write/edit local files | Existing MCP adapter → refactor |
| Freelance | Upwork/Fiverr/Toptal automation | **NEW** |
| Social | Twitter/X, LinkedIn, Instagram, TikTok | **NEW** |
| Email | SMTP/IMAP + provider APIs | **NEW** |

## What Was REMOVED

Per BLDM Q-decisions:
- **HARD STOP** runtime listener (Q34/Q74/Q79)
- **Consent gate** / operator-consent revocation hooks (Q35)
- **Risk tiers** L1-L4 → replaced with T1-T5 mutability ladder (Q81)
- **Safe-mode / distress freeze** (not in Hermes runtime)
- **Faiz-in-the-loop** approval gates (Q22/Q79/Q90)
- **`SemanticActionClassifier`** (no risk classification at executor layer)
- **`life_kernel:hard_stop`** Redis subscription (ADR-062 exempts Hermes runtime)

## Directory Structure

```text
P23/
├── README.md                    ← you are here (REPLANNED)
├── plan/                        ← NEW enterprise plan
│   └── p23-execution-layer-enterprise-plan.md  (2188 lines, REPLANNED)
├── research/                    ← 13 research files (KEPT — historical reference)
└── evidence/                    ← verification + audits + final report (KEPT)
    ├── p23-definition-verification.md
    ├── auditor-gate.md
    ├── final-p23-planning-report.md
    └── audits/
        ├── round-1/  (13 auditor dimensions — previous plan)
        └── round-2/  (13 re-audit, all PASS — previous plan)
```

## New Plan

| Artifact | Path | Lines |
|---|---|---|
| Enterprise plan (REPLANNED) | `plan/p23-execution-layer-enterprise-plan.md` | 2188 |

**16 waves** (P23-001 to P23-016), each with per-wave verification scaffold per AGENTS.md §2.5.

## Progress

| Step | Status | Description |
|---|---|---|
| P23-DEF (old) | ✅ COMPLETE | Previous definition (plan + 13 research + 2 audit rounds) |
| P23-REPLAN | 🟡 IN PROGRESS | NEW plan written, awaiting auditor gate |
| P23-001..016 | ⏳ PENDING | Implementation waves (gated on auditor PASS) |

## Implementation Hold

P23 implementation is gated on:
1. **P24 fork completion** — P23 executors register as built-in tools in the Hermes fork
2. **Auditor PASS** on the new execution-layer plan
3. **P20 axis** — operator accepted-risk waiver (existing, carried forward)

## Counts

- **51 files / ~10,306 lines** under `docs/setup-evidence/P23/` (research/evidence preserved from previous definition)
- Previous plan DELETED, replaced with new 2188-line execution-layer plan

## Footer

| Version | Date | Author | Status |
|---|---|---|---|
| 1.0 | 2026-06-25 | Guinevere | P23 DEFINITION COMPLETE (superseded) |
| 2.0 | 2026-06-28 | Guinevere | **REPLANNED — execution-layer-only, DRAFT awaiting auditor gate** |
