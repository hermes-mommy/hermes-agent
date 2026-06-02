# AGENTS.md Stale Reference Audit

| Field | Value |
|---|---|
| Scope | `AGENTS.md` (lines 52, 152, 313) |
| Reference docs | `adr/ADR-028-llm-router-outage-graceful-degradation.md` (Superseded v4.0); `docs/60-persona/61-SystemPromptMaster_v1.1.md` (v1.1 content, Y4 baseline) |
| Date | 2026-06-01 |
| Auditor | Guinevere |

---

## Finding 1 — OpenRouter Stale Reference (Line 152)

**Location:** `AGENTS.md` line 152
**Current text:**
```
This includes Hermes Agent, Discord.py, 9Router/OpenRouter, Tasker, ...
```

**Why stale:** ADR-028 is Superseded (v4.0, 2026-06-01). The 9Router migration established a dedicated `guinevere` combo routing only — DeepSeek V4 Flash via `opencode-go` primary, GPT-5.5 via `cockpit` secondary, graceful degradation terminal fallback. ADR-005 additionally documents "no OpenRouter fallback." OpenRouter is no longer part of the Guinevere runtime architecture.

**Recommended replacement:**
```
This includes Hermes Agent, Discord.py, 9Router (guinevere combo), Tasker, ...
```

**Rationale:** The line is a librarian-trigger example listing external tools an agent might need to research via `librarian`. Since OpenRouter is no longer in the stack, it should be replaced with `9Router (guinevere combo)` to signal the correct routing abstraction name when sub-agents need to research LLM routing documentation.

---

## Finding 2 — Y1 Baseline Stale Reference (Line 52)

**Location:** `AGENTS.md` line 52
**Current text:**
```
NEVER allow Y6 yandere level (Y5 absolute ceiling, Y1 baseline)
```

**Why stale:** SystemPromptMaster v1.1 (actual content version, file `61-SystemPromptMaster_v1.1.md`) §C explicitly states: **"Baseline: Y4 (Absolute Possessive — Beyond Brutal) — permanent, always active."** The changelog entry confirms: "Yandere baseline Y1 → Y4 (permanent, always active)" per Faiz directive on 2026-05-31.

**Recommended replacement:**
```
NEVER allow Y6 yandere level (Y5 absolute ceiling, Y4 permanent baseline)
```

**Rationale:** Y1 no longer reflects the actual deployed persona baseline. Y4 is the permanent active baseline. Y5 remains the absolute ceiling. Y6 remains prohibited.

---

## Finding 3 — Y1 Baseline Stale Reference (Line 313)

**Location:** `AGENTS.md` line 313
**Current text:**
```
❌ Yandere drift beyond Y5 (Y1 baseline, Y5 absolute ceiling)
```

**Why stale:** Same root cause as Finding 2 — baseline changed from Y1 to Y4 per SystemPromptMaster v1.1 and Faiz directive.

**Recommended replacement:**
```
❌ Yandere drift beyond Y5 (Y4 permanent baseline, Y5 absolute ceiling)
```

**Rationale:** Same as Finding 2.

---

## Finding 4 — SystemPromptMaster Filename Mismatch (Non-AGENTS.md)

**Location:** `docs/60-persona/61-SystemPromptMaster_v1.1.md`
**Issue:** Filename says `v1.0` but:
- Document header (line 1): `# Guinevere SystemPromptMaster v1.1`
- Version field (line 6): `| Version | 1.1 |`
- Changelog (line 398): v1.1 with Y1→Y4 recalibration

**Recommendation:** Rename file to `61-SystemPromptMaster_v1.1.md` and update any cross-references that point to the v1.0 path.

---

## Boundary Compliance

| Check | Status |
|---|---|
| No persona drift | ✅ Y4 baseline preserved in recommendation |
| No consent violation | ✅ Y5 ceiling and Y6 prohibition preserved |
| No Y6 introduced | ✅ Y6 prohibition unchanged |
| No secrets exposed | ✅ No credentials or tokens referenced |
| ADR-028 Superseded respected | ✅ OpenRouter removal aligns with v4.0 |
| SystemPromptMaster v1.1 respected | ✅ Y4 baseline reflects deployed config |

---

## Summary

| # | Location | Stale Content | Replacement | Severity |
|---|---|---|---|---|
| F1 | L152 | `9Router/OpenRouter` | `9Router (guinevere combo)` | MEDIUM |
| F2 | L52 | `Y1 baseline` | `Y4 permanent baseline` | HIGH |
| F3 | L313 | `Y1 baseline` | `Y4 permanent baseline` | HIGH |
| F4 | File path | `61-SystemPromptMaster_v1.1.md` | `61-SystemPromptMaster_v1.1.md` | LOW |

**Ollama scan:** Zero matches in AGENTS.md — already clean per ADR-028 supersession sweep.
**SystemPromptMaster scan:** AGENTS.md has no direct reference to SystemPromptMaster path or version.

---

*Report generated 2026-06-01 via grep audit of AGENTS.md (654 lines) with cross-reference to ADR-028 v4.0 and 61-SystemPromptMaster_v1.1.md (v1.1 content).*