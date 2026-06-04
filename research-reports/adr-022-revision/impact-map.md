# ADR-022 Revision: Baileys → Neonize — Impact Map

**Date:** 2026-06-03
**Author:** Guinevere (parent synthesis)
**Status:** Research complete, ready for planner gate

---

## 1. Change Summary

| Aspect | Before | After |
|--------|--------|-------|
| Library | Baileys (Node.js, WhatsApp Web MD) | Neonize (Python, whatsmeow wrapper) |
| Language | JavaScript/TypeScript | Python 3.12 |
| Process model | Separate Node.js subprocess + HTTP bridge | Single Python process, native asyncio |
| Protocol | WhatsApp Web MD (JS reimplementation) | whatsmeow (Go, compiled into Python extension) |
| Session storage | File-based (SOPS encrypted) | Redis (SOPS encrypted) or file-based |
| Package | `@whiskeysockets/baileys` (npm) | `neonize>=0.3.18,<0.4.0` (pip) |
| Systemd unit | `guinevere-whatsapp.service` (Node.js) | Same name, Python entrypoint |
| Bridge | HTTP REST bridge on localhost:3000 | Direct Python import (no bridge) |

## 2. Binding Decisions Locked (from requirements-p11-whatsapp.md §9)

| # | Change | Affects |
|---|--------|---------|
| 1 | Replace Baileys with Neonize | Decision, Context, Consequences |
| 2 | Remove Node.js subprocess dependency | Implementation Notes, Consequences |
| 3 | Replace HTTP bridge with direct integration | Implementation Notes |
| 4 | Keep: separate systemd, SOPS, per-channel, safe-word | (unchanged) |
| 5 | Version pinning: `neonize>=0.3.18,<0.4.0` | Implementation Notes |
| 6 | Add whatsmeow protocol break strategy | New: Risks section |
| 7 | Update risk assessment (single-process trade-off) | Consequences |

## 3. File Change Priority Map

### Priority 1 — MUST CHANGE (ADR-022 revision scope)

| File | Change Type | Lines Affected |
|------|------------|----------------|
| `adr/ADR-022-communication-channel-strategy.md` | Major revision | ~20 lines across 6 sections |
| `docs/10-governance/17-ADR_Index_v1.0.md` | Row update | Line 86 (status + note) |
| `adr/README.md` | Row update | Line 89 (status + note) |
| `docs/10-governance/decisions-log.md` | New row | Append entry #002 |

### Priority 2 — SHOULD UPDATE (operational Baileys refs in active docs)

| File | Current Content | Scope Decision |
|------|----------------|----------------|
| `docs/00-core/05-APIIntegration_v2.0.md` | §7.1 WhatsApp Baileys section, code examples | OUT OF SCOPE for ADR-022 revision; flag for P11 implementation |
| `docs/10-governance/12-SRS_v1.0.md` | SRS-IR-006/007 Baileys HTTP API | OUT OF SCOPE; flag for P11 |
| `docs/10-governance/13-FSD_v1.0.md` | WhatsApp/Baileys processing spec | OUT OF SCOPE; flag for P11 |
| `docs/10-governance/11-FeasibilityStudy_v1.0.md` | ~15 Baileys refs (fragility, adapter) | OUT OF SCOPE; historical assessment |
| `docs/20-security/20-SecurityPolicy_v1.0.md` | Component 8: WhatsApp (Baileys) | OUT OF SCOPE; flag for P11 |
| `docs/20-security/23-SecretsRotationRunbook_v1.0.md` | sec-baileys-session | OUT OF SCOPE; flag for P11 |
| `docs/30-data/30-DataGovernance_Classification_v1.0.md` | 1 ref | OUT OF SCOPE |
| `docs/40-operations/44-DeploymentGuide_v1.0.md` | §3.7 full systemd unit with Node.js | OUT OF SCOPE; flag for P11 |
| `docs/40-operations/45-InternalOpsManual_v1.0.md` | Baileys session check | OUT OF SCOPE; flag for P11 |
| `docs/10-governance/14-TDD_Guide_v1.0.md` | C4 diagrams | OUT OF SCOPE |
| `docs/10-governance/15-RTM_v1.0.md` | INT-002 WhatsApp/Baileys | OUT OF SCOPE |

### Priority 3 — ACCEPTABLE (no change needed)

- All `research-reports/` — comparative analysis, historical documentation
- All `audit-reports/` — historical audit findings
- `stepprompts/StepPrompts.md` P11 section — already documents ADR-022 revision requirement, baileys-antiban as reference
- `docs/_archive/` — v1.0 archived docs
- `docs/IMPLEMENTATION_GUIDE.md` — already updated ("Neonize...replaces Baileys")

## 4. ADR-022 Detailed Change Specification

### 4.1 Status Section (line ~6)
- **ADD:** "Superseded in part by revision 2026-06-03. WhatsApp integration library changed from Baileys (Node.js) to Neonize (Python). See Revision History."
- **KEEP:** Original "Accepted with notes" status in YAML frontmatter

### 4.2 Context Section (line ~40)
- **ADD:** New bullet: "Neonize (Python, wraps whatsmeow/Go) evaluated as alternative to Baileys — eliminates Node.js subprocess dependency, enables native asyncio integration, pip-installable."

### 4.3 Decision Outcome (line ~90)
- **CHANGE:** "WhatsApp via Baileys (WhatsApp Web MD protocol)" → "WhatsApp via Neonize (Python, wraps whatsmeow Go library)"
- **CHANGE:** "Node.js subprocess for WhatsApp" → "Python-native Neonize client"
- **CHANGE:** "HTTP bridge between Python core and Node.js WhatsApp" → "Direct Python integration via Neonize asyncio API"

### 4.4 Consequences (lines ~100-120)
- **ADD Positive:** "Single-process architecture eliminates Node.js bridge latency (~5-15ms per message)"
- **ADD Positive:** "Native asyncio integration with existing LLM/memory/persona pipeline"
- **ADD Positive:** "pip-installable — no npm/Node.js runtime dependency on VPS"
- **ADD Negative:** "Neonize community smaller (399★ vs Baileys 13K★) — less battle-tested"
- **ADD Negative:** "whatsmeow protocol breaks require Go-level debugging, not Python-level"
- **ADD Risk:** "Protocol break every 2-8 weeks from WhatsApp; whatsmeow upstream typically patches within 24-48h"
- **ADD Risk:** "Rollback plan: maintain Baileys adapter as fallback if Neonize proves unstable in production"

### 4.5 Implementation Notes (lines ~125-135)
- **REPLACE:** Baileys-specific notes (lines 131, 138) with Neonize equivalents:
  - `neonize>=0.3.18,<0.4.0` (pin minor version)
  - Session storage: Redis with SOPS encryption (not file-based)
  - Single Python process (no bridge service)
  - Python 3.12 required (neonize uses modern asyncio features)
  - whatsmeow Go binary compiled at install time (requires Go toolchain on build server only)

### 4.6 Revision History (NEW section)
```markdown
## Revision History

| Version | Date | Change | Author |
|---------|------|--------|--------|
| v1.0 | 2026-05-30 | Initial decision: Baileys (Node.js) for WhatsApp | Faiz + Guinevere |
| v1.1 | 2026-06-03 | Revised: Neonize (Python) replaces Baileys | Faiz + Guinevere |
```

## 5. ADR-Index / adr/README.md Change Spec

### ADR-022 Row Update
- **Before:** `| ADR-022 | Communication Channel Strategy | Accepted with notes | HIGH | discord, whatsapp, email, communication | [link] |`
- **After:** `| ADR-022 | Communication Channel Strategy | Accepted with notes (Revised 2026-06-03: Baileys→Neonize) | HIGH | discord, whatsapp, email, communication | [link] |`

### Status Summary Update
- **ADD to Accepted with notes count:** No change (still "Accepted with notes" base status)
- **ADD footnote:** "*ADR-022 revised 2026-06-03: WhatsApp library changed from Baileys to Neonize. See ADR-022 Revision History.*"

### Status Lifecycle
- **DECISION:** Do NOT add "Revised" as new lifecycle status. Use parenthetical note in status cell instead. Rationale: "Revised" is not a standard ADR lifecycle state; the ADR remains "Accepted" with a documented revision.

## 6. decisions-log.md Change Spec

New entry:
```markdown
| 002 | 2026-06-03 | ADR-022 Revised: Baileys → Neonize for WhatsApp | Communication | ADR-022 v1.1 | Neonize (pure Python, wraps whatsmeow) eliminates Node.js subprocess dependency, enables native asyncio, pip-installable. Trade-off: smaller community (399★), less battle-tested. Rollback: Baileys adapter maintained as fallback. Risk: HIGH (unchanged). | Faiz |
```

## 7. Collision Scan

| File | Writers | Collision Risk |
|------|---------|---------------|
| `adr/ADR-022-communication-channel-strategy.md` | 1 (ADR-022 revision agent) | NONE |
| `docs/10-governance/17-ADR_Index_v1.0.md` | 1 (Index update agent) | NONE |
| `adr/README.md` | 1 (Index update agent) | LOW — same agent handles both Index files |
| `docs/10-governance/decisions-log.md` | 1 (Log update agent) | NONE |

**Zero shared-writer collisions.** All 4 files have distinct owners.

## 8. Verification Strategy (5 grep checks)

| # | Check | Expected |
|---|-------|----------|
| V1 | `grep -i "baileys" adr/ADR-022-communication-channel-strategy.md` | 0 matches in Decision/Implementation sections (allowed in Revision History as historical reference) |
| V2 | `grep "neonize" adr/ADR-022-communication-channel-strategy.md` | ≥3 matches (Decision, Implementation, Consequences) |
| V3 | `grep "Revised 2026-06-03" docs/10-governance/17-ADR_Index_v1.0.md` | 1 match |
| V4 | `grep "ADR-022" docs/10-governance/decisions-log.md` | 1 match (entry #002) |
| V5 | `grep "Revised 2026-06-03" adr/README.md` | 1 match |

## 9. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Other docs still reference Baileys as current | MEDIUM | Flag for P11 implementation; add "See ADR-022 v1.1" note to API Integration doc |
| ADR-022 revision creates inconsistency with SRS/FSD | LOW | SRS/FSD are specification docs; ADR is decision record. ADR supersedes for implementation choice. |
| Status "Accepted with notes (Revised)" is non-standard | LOW | Documented rationale in decisions-log; no new lifecycle state needed |

## 10. Caveats

1. This revision covers ADR-022 and its indexes ONLY. The 11+ other docs with operational Baileys references are flagged for P11 implementation but OUT OF SCOPE for this ADR revision task.
2. Neonize v0.3.18 is the current version as of May 2026. Version may change before P11 implementation begins.
3. The "Accepted with notes (Revised)" status format is a project convention decision — not a standard ADR lifecycle state.
