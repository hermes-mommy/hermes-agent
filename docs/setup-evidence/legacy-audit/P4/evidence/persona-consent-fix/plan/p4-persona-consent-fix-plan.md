# P4 Persona/Consent Fix — Executable Implementation Plan

**Date:** 2026-06-27
**Phase:** 2 — Planner Gate
**Lane:** C
**Author:** Guinevere (orchestrator)
**Status:** READY FOR IMPLEMENTATION
**Evidence Root:** `docs/setup-evidence/legacy-audit/P4/evidence/persona-consent-fix/`

---

## Executive Summary

PersonaPlugin injects persona state into every LLM call but never checks consent or safety state. Consent revocation updates Redis but no runtime consumer acts on it. 5 of 6 behavioral engines are not fully wired to runtime. Rituals are marked deprecated but docs say complete. 2 CRITICAL, 4 HIGH, 4 MEDIUM.

**Target: Make consent revocation actually enforced, PersonaPlugin consent-aware, and dead code resolved.**

---

## Master Todo

| # | Step | Severity | Deps | Parallel |
|---|------|----------|------|----------|
| C1 | Add consent check to PersonaPlugin | CRITICAL | None | parallel |
| C2 | Add HARD STOP / safety check to PersonaPlugin | CRITICAL | None | parallel |
| C3 | Implement consent revocation cascade | HIGH | C1 | sequential |
| C4 | Wire MoodEngine to prompt_loader (KI-06) | HIGH | None | parallel |
| C5 | Wire DistressDetector to Discord on_message (KI-05) | HIGH | None | parallel |
| C6 | Resolve dead code: wire or deprecate 6 engines | MEDIUM | None | parallel |
| C7 | Resolve rituals deprecated mismatch | MEDIUM | None | parallel |
| C8 | Add runtime logging proof for persona injection | MEDIUM | C1, C2 | sequential |
| C9 | Wire YandereEngine persistence (KI-03) | MEDIUM | None | parallel |
| C10 | Run all tests, verify P20/P19 regression | GATE | C1-C9 | sequential |

---

## Dependency Map

```
C1 (consent check) ── C3 (revocation cascade) ──┐
C2 (safety check) ───────────────────────────────┤
C4 (mood→prompt_loader) ─────────────────────────┤
C5 (distress→on_message) ────────────────────────┤
C6 (dead code resolution) ───────────────────────┤
C7 (rituals docs fix) ───────────────────────────┤
C8 (runtime logging) ────────────────────────────┤
C9 (yandere persistence) ────────────────────────┤
                                                  └── C10 (tests + regression)
```

C1-C7+C9 can run in parallel. C3 depends on C1. C8 depends on C1+C2. C10 is the final gate.

---

## Collision Scan

| Step | Files Touched | Collision Risk |
|------|--------------|----------------|
| C1 | `src/hermes/plugins/persona_plugin.py` | HIGH — also touched by C2, C8 |
| C2 | `src/hermes/plugins/persona_plugin.py` | HIGH — shares with C1 |
| C3 | `src/discord/cmd_consent.py` + new orchestrator | MEDIUM |
| C4 | `src/core/services/prompt_loader.py` | LOW |
| C5 | `src/discord/bot.py` (or message handler) | MEDIUM — P20 Discord path |
| C6 | `src/persona/__init__.py` + multiple engine files | MEDIUM |
| C7 | `src/persona/__init__.py` + docs | LOW |
| C8 | `src/hermes/plugins/persona_plugin.py` | HIGH — shares with C1, C2 |
| C9 | `src/persona/yandere_fsm.py` + `src/memory/db.py` | LOW |

**Mitigation:** C1 and C2 are implemented together in a single step (same file). C8 follows C1+C2. Parent owns persona_plugin.py edits.

---

## Per-Step Verification Scaffolds

### C1+C2: Add Consent + Safety Gates to PersonaPlugin

**Expected Files:**
- `src/hermes/plugins/persona_plugin.py` — modified

**Forbidden Patterns:**
- `# type: ignore`, `as any`
- `except Exception` swallowing
- Blocking the LLM call (must return None, not raise)
- Breaking existing persona injection when consent is granted

**Required Commands:**
- `python -m pytest tests/persona/ -v -k "persona_plugin"` → exit 0
- `python -c "from src.hermes.plugins.persona_plugin import PersonaPlugin; p = PersonaPlugin(); print('OK')"` → exit 0

**Hard Rejection:**
- PersonaPlugin still injects without consent check
- PersonaPlugin still injects during HARD STOP
- Existing tests break
- Consent check blocks LLM call (should only skip injection, return None)

**Evidence:**
- `docs/setup-evidence/legacy-audit/P4/evidence/persona-consent-fix/implementation/C1-C2-persona-plugin-gates.md`

---

### C3: Consent Revocation Cascade

**Expected Files:**
- `src/discord/cmd_consent.py` — modified (add Redis pub/sub)
- NEW: `src/consent/revocation_orchestrator.py` (or similar)

**Forbidden Patterns:**
- Tight coupling between consent and persona/surveillance modules
- Blocking Redis calls in hot path

**Required Commands:**
- `python -m pytest tests/consent/ -v` → exit 0

**Hard Rejection:**
- Consent revocation still doesn't stop persona injection
- No cascade mechanism
- Existing tests break

**Evidence:**
- `docs/setup-evidence/legacy-audit/P4/evidence/persona-consent-fix/implementation/C3-consent-cascade.md`

---

### C4: Wire MoodEngine to Prompt Loader

**Expected Files:**
- `src/core/services/prompt_loader.py` — modified

**Forbidden Patterns:**
- Blocking Redis calls in prompt loading
- Breaking prompt loading when Redis is down

**Required Commands:**
- `python -m pytest tests/core/ -v -k "prompt"` → exit 0

**Hard Rejection:**
- Prompt loader still uses placeholder mood value
- Prompt loading fails when Redis is unavailable

**Evidence:**
- `docs/setup-evidence/legacy-audit/P4/evidence/persona-consent-fix/implementation/C4-mood-prompt-loader.md`

---

### C5: Wire DistressDetector to Discord

**Expected Files:**
- `src/discord/bot.py` (or message handler) — modified

**Forbidden Patterns:**
- Blocking the message pipeline
- Breaking HARD STOP detection

**Required Commands:**
- `python -m pytest tests/discord/ -v -k "distress or safe_mode"` → exit 0

**Hard Rejection:**
- DistressDetector still not called on messages
- Message pipeline broken
- HARD STOP detection broken

**Evidence:**
- `docs/setup-evidence/legacy-audit/P4/evidence/persona-consent-fix/implementation/C5-distress-on-message.md`

---

### C6: Dead Code Resolution

**Expected Files:**
- `src/persona/__init__.py` — modified (add/remove exports)
- `src/persona/streak_tracker.py` — modified (wire)
- `src/persona/milestone_engine.py` — modified (wire)
- `src/persona/ritual_scheduler.py` — mark DEPRECATED

**Forbidden Patterns:**
- Deleting code without deprecation notice
- Breaking imports

**Required Commands:**
- `python -c "from src.persona import *; print('OK')"` → exit 0
- `python -m pytest tests/persona/ -v` → exit 0

**Hard Rejection:**
- Imports break
- Tests fail
- Wired engines still don't work

**Evidence:**
- `docs/setup-evidence/legacy-audit/P4/evidence/persona-consent-fix/implementation/C6-dead-code-resolution.md`

---

### C7: Rituals Deprecated Mismatch

**Expected Files:**
- `src/persona/__init__.py` — update deprecation docs
- `docs/README.md` — update if needed
- `PROGRESS.md` — update P4 ritual status
- `CHECKLIST.md` — update P4 ritual status

**Forbidden Patterns:**
- Silent removal without doc update
- Claiming "complete" when deprecated

**Required Commands:**
- `grep -c 'DEPRECATED' src/persona/__init__.py` → ≥ 1

**Hard Rejection:**
- Docs still say rituals are complete without noting deprecation
- Rituals removed without Hermes cron verification

**Evidence:**
- `docs/setup-evidence/legacy-audit/P4/evidence/persona-consent-fix/implementation/C7-rituals-docs-fix.md`

---

### C8: Runtime Logging Proof

**Expected Files:**
- `src/hermes/plugins/persona_plugin.py` — add structured logging

**Forbidden Patterns:**
- Logging sensitive persona state values
- Logging raw prompt content

**Required Commands:**
- `grep -c 'persona_plugin_inject' src/hermes/plugins/persona_plugin.py` → ≥ 1

**Hard Rejection:**
- No log evidence of persona injection available
- Logs contain sensitive data

**Evidence:**
- Production log snippet showing persona injection (or simulation evidence)

---

### C9: YandereEngine Persistence

**Expected Files:**
- `src/persona/yandere_fsm.py` — modified (add persist method)
- `src/memory/db.py` — modified (add write_yandere_state helper)

**Forbidden Patterns:**
- Blocking DB writes in FSM transitions
- Data loss on restart

**Required Commands:**
- `python -m pytest tests/persona/test_yandere_fsm.py -v` → exit 0

**Hard Rejection:**
- Yandere state still lost on restart
- DB writes fail silently

**Evidence:**
- `docs/setup-evidence/legacy-audit/P4/evidence/persona-consent-fix/implementation/C9-yandere-persistence.md`

---

### C10: Test Suite + P20/P19 Regression

**Expected Files:**
- All test files pass

**Required Commands:**
- `python -m pytest tests/persona/ -v` → exit 0
- `python -m pytest tests/consent/ -v` → exit 0
- `python -m pytest tests/discord/ -v -k "consent or persona"` → exit 0
- `python -m pytest tests/life_kernel/ -v` → exit 0 (P20 regression)

**Hard Rejection:**
- Any test failure
- P20 NRestarts > 0
- Secret leak in any file
- Consent revocation still source-false

**Evidence:**
- `docs/setup-evidence/legacy-audit/P4/evidence/persona-consent-fix/verification/p4-persona-consent-fix-verification.md`

---

## Rollback Plan

Per step:
1. `git diff HEAD` → review changes
2. `git stash` → revert all
3. Restart guinevere-core

For main.py / Discord bot changes:
1. Backup file → edit → restart → smoke test
2. If P20 disturbed: revert immediately

## Deploy Policy

- **NO auto-deploy.** All changes are code-only until operator approval.
- Discord bot changes (C5) require: backup → canary restart → verify bot online → full deploy
- PersonaPlugin changes (C1, C2, C8) are hot-reloaded by Hermes if plugin system supports it

## Auditor Matrix

| Step | Auditor Dimensions |
|------|-------------------|
| C1+C2 | Consent, safety, persona, code quality |
| C3 | Consent cascade, Redis pub/sub, integration |
| C4 | Prompt loading, mood, integration |
| C5 | Discord, distress, safety, integration |
| C6 | Architecture, dead code, imports |
| C7 | Docs, deprecation, cross-references |
| C8 | Logging, observability, PII safety |
| C9 | DB persistence, yandere, state management |
| C10 | Full regression, P20/P19 boundary, secrets |