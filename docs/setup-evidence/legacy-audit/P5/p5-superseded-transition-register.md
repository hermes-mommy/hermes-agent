# P5 Superseded/Transition Register

**Date:** 2026-06-27

---

## Superseded Items

### SUPER-001: HermesBridge → Living Autonomy Kernel
- **Original:** `src/loops/hermes_bridge.py` — Redis DB5 pub/sub bridge for Hermes ↔ LoopManager coordination
- **Superseded By:** `src/life_kernel/hermes_brain.py` (HermesBrain) — P20 active autonomous brain
- **Evidence:** `src/core/main.py` line 464: "P5-023: Hermes Bridge is superseded by the Living Autonomy Kernel"
- **Current Status:** Module exists and is exported from `__init__.py` but unused in production path
- **Action Needed:** Remove from exports or mark deprecated

### SUPER-002: P4 Ritual Scheduler → Hermes Native Cron
- **Original:** `src/persona/ritual_scheduler.py` — APScheduler-based persona ritual scheduler
- **Superseded By:** Hermes native cron (`hermes cron create`) registered in ADR-035 Phase 5
- **Evidence:** Module docstring: "deprecated in Phase 5. Use Hermes cron...Scheduled removal: Phase 7"
- **Current Status:** Module remains importable with deprecation warning. Phase 7 has not removed it.
- **Action Needed:** Remove module per deprecation timeline

### SUPER-003: LoopManager as Autonomous Brain → LifeKernel
- **Original:** Phase 5's vision of LoopManager as "7-phase autonomous SDLC engine"
- **Superseded By:** P20 LifeKernel with HermesBrain as active autonomous brain
- **Evidence:** `main.py` passes `llm_router=None` — loop phase handlers are dormant for LLM
- **Current Status:** LoopManager runs as task execution infrastructure (non-LLM). LifeKernel is the active brain.
- **Action Needed:** Update Phase 5 documentation to reflect current role

### SUPER-004: Standalone Discord Loop Commands → Hermes Plugin Commands
- **Original:** `src/discord/cmd_loop_start.py` and `cmd_loop_stop.py` wired via `_entrypoint.py`
- **Superseded By:** `src/hermes_plugins/commands_loop/` — 7 Hermes-native loop commands (start, stop, pause, resume, priority, evidence, loops)
- **Evidence:** Both exist. Hermes plugin commands use httpx calls to API (F-01 fix). Discord commands still registered.
- **Current Status:** Both paths active. Hermes plugin commands are the production path via Hermes gateway.
- **Action Needed:** Document dual-path or deprecate standalone Discord commands

### SUPER-005: APScheduler Persona Rituals → Hermes Cron
- **Original:** `config/hermes/crontab.yaml` (5 cron entries, WIB times)
- **Superseded By:** Hermes native cron CLI registration (`hermes cron create`)
- **Evidence:** ADR-035 Phase 5 verification — 5 cron jobs registered via CLI
- **Current Status:** YAML file approach from original plan replaced by CLI registration
- **Action Needed:** Remove or annotate stale crontab.yaml if it still exists

---

## Transition States

| Component | From | To | Transition Date | Status |
|-----------|------|-----|----------------|--------|
| Hermes integration | HermesBridge | HermesBrain | 2026-06-25 (P20) | ✅ Complete |
| Persona rituals | P4 ritual_scheduler | Hermes native cron | 2026-06-06 (ADR-035) | ⚠️ Deprecated not removed |
| Loop commands | Discord standalone | Hermes plugin | 2026-06-09 (F-01 fix) | ✅ Both active |
| Autonomous brain | LoopManager | LifeKernel | 2026-06-25 (P20) | ✅ Complete (loop dormant) |
| Cron config | crontab.yaml | hermes cron CLI | 2026-06-06 (ADR-035) | ✅ Complete |
