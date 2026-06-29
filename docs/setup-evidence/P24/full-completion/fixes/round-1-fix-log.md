# P24 Round-1 Fix Log

> **Generated**: 2026-06-29 | **Author**: Guinevere (parent) | **Purpose**: Adjudicate round-1 audit findings per AGENTS.md §2.10 (fix valid findings OR document false-positive/owned-by-later-wave with evidence).

---

## Adjudication Summary

| Wave | Auditor Verdict | Findings | Parent Adjudication | Final |
|------|----------------|----------|---------------------|-------|
| W1 | PASS | 0 | — | ✅ PASS |
| W2 | CONDITIONAL PASS | 2 CRITICAL, 2 HIGH | All 4 are `src/` stale imports owned by W16 (channels port). Fork runtime insulated (verified). | ✅ PASS (wave-owned tracker) |
| W3 | CONDITIONAL PASS | 5 CRITICAL, 1 HIGH, 1 MEDIUM | All 7 are `src/` stale imports owned by W4/W5/W12/W15/W16. Fork runtime insulated (verified). Migration ADR-066-compliant (auditor confirmed). | ✅ PASS (wave-owned tracker) |
| W5 | PASS | 0 | — | ✅ PASS |
| W4 | (fix in flight) | 11 test ERRORS | mock.patch load_settings mismatch — fix queued to W4 agent | ⏳ pending fix |

---

## W2 Findings — Adjudicated as WAVE-OWNED (not fix-now)

### W2-F01 (CRITICAL) — `src/channels/whatsapp/hard_stop.py:9` imports deleted `HardStopHandler`
### W2-F02 (CRITICAL) — `src/channels/whatsapp/ops_commands.py:11` imports deleted `HardStopHandler`
### W2-F03 (HIGH) — `src/channels/whatsapp/service.py:35` cascading import
### W2-F04 (HIGH) — `src/channels/whatsapp/__init__.py:17` re-exports broken hard_stop

**Root cause**: W2 deleted `src/core/services/hard_stop_handler.py` (per M2 scaffold). 4 files in `src/channels/whatsapp/` still import `HardStopHandler`.

**Why NOT fix-now (evidence)**:
1. `src/channels/whatsapp/` is **PORTED to `guinevere/channels/whatsapp/` in W16** (M14, per r10 + r02 disposition). At W16, those imports are rewritten to `guinevere.*`. The `src/channels/` files are **slated for deletion** in W16, not for import-fixing — fixing now is wasted work.
2. **Fork runtime is insulated** (parent-verified 2026-06-29 08:26):
   - `pythonpath = ["."]` (W1 changed from `["src"]`) — fork imports from repo root (`agent/`, `guinevere/`), NOT `src/`.
   - `import guinevere.surveillance, guinevere.observability` → OK, no cascade. Python does NOT execute `src/surveillance/__init__.py` when importing `guinevere.*`.
   - `tests/p24/test_surveillance.py` → 51 passed in 0.78s (fork's own tests, no `src/`).
3. The breakage only manifests IF something explicitly does `import src.channels.whatsapp` — the fork runtime does not. The legacy `tests/` suite (W18) may, but W16 resolves the channels imports before W18.

**Resolution**: Tracked as wave-owned by **W16** (M14 External Channels). W16 must rewrite `src/channels/whatsapp/` → `guinevere/channels/whatsapp/` and clean the `HardStopHandler` imports (replace with `guinevere.life_kernel` equivalent or remove, since ADR-062 removes HARD STOP from runtime). W18 integration test will verify 0 broken `src/` imports remain.

**Severity reassessment**: CRITICAL (running prod) → **MEDIUM** (build-phase, fork insulated, W18-gated). No fix applied now; ownership documented.

---

## W3 Findings — Adjudicated as WAVE-OWNED (not fix-now)

### W3-F01 (CRITICAL) — `src/core/main.py:184` imports deleted `P22ConsentChecker`
### W3-F02 (CRITICAL) — `src/core/api/routes.py:482,530` imports deleted `ConsentLedgerWriter`
### W3-F07 (MEDIUM) — `src/core/main.py:635,645` comment refs to deleted components

**Resolution**: `src/core/main.py` is **ABSORBED into `guinevere/http/server.py` in W4** (M15, per r11 §5.1 — "M15 absorbs and deletes src/core/main.py"). W4 ports the lifespan/endpoints to `guinevere/http/` with consent stripped. The `src/core/main.py` file is then **deleted** in a later cleanup wave. Fixing its imports now is wasted — the file is deleted. Owned by **W4 + cleanup wave**.

### W3-F03 (CRITICAL) — `src/discord/cmd_pc.py:234` imports deleted `check_consent`
### W3-F04 (CRITICAL) — `src/discord/cmd_surveillance_pause.py:116` imports deleted consent_gate
### W3-F05 (CRITICAL) — `src/discord/cmd_surveillance_status.py:26,157` imports deleted consent_gate

**Resolution**: `src/discord/cmd_*.py` (65 files) are **PORTED to `guinevere/discord/` in W15** (M13, per r09). W15 ports 41+ slash commands with consent stripped. The `src/discord/` files are **deleted** in W15. Owned by **W15**.

### W3-F06 (HIGH) — `src/surveillance/__init__.py:12` imports deleted consent_gate (cascades to whole src.surveillance package)

**Resolution**: `src/surveillance/` (14 files) — W5 already PORTED the non-consent portions to `guinevere/surveillance/` (clean, 51 tests pass). The legacy `src/surveillance/` package (with its broken `__init__.py`) is **deleted** in a later cleanup wave. The fork uses `guinevere.surveillance` (clean), NOT `src.surveillance`. Parent-verified: `import guinevere.surveillance` → OK (no cascade into src/). Owned by **cleanup wave** (after W5).

**Why NOT fix-now (evidence)**:
1. **Migration is ADR-066-compliant** (auditor deep-verified: event_source discriminator + consent_ref nullable CHECK: dev_workflow NOT NULL, hermes_runtime allows NULL, 5 tables, defensive guards, downgrade present, revision chain correct).
2. **`guinevere/` tree is clean**: 0 active consent references (AST scan + grep, parent-verified).
3. **Fork runtime insulated** (parent-verified): `guinevere.surveillance/observability/http` import without triggering `src/surveillance/__init__.py`. `tests/p24/` passes (51 tests).
4. The cascade only breaks `import src.surveillance` — fork doesn't do this. Legacy `tests/` (W18) may; resolved by W15 + cleanup wave before W18.

**Severity reassessment**: CRITICAL (running prod) → **MEDIUM** (build-phase, fork insulated, W18-gated, migration compliant). No fix applied now; ownership documented.

---

## W4 Findings — FIX IN FLIGHT (real bug, must fix)

### W4-F01 (11 test ERRORS) — `mock.patch("guinevere.http.server.load_settings")` raises AttributeError

**Root cause**: `guinevere/http/server.py` imports `load_settings` inside the lifespan function (local import), not at module level. `unittest.mock.patch` requires the name to be bound on the module object.

**Status**: Fix queued to W4 agent (agentId a588e0afef7d65899) via SendMessage — make `load_settings` a module-level import. W4 scaffold hard-rejects on `pytest tests/p24/test_http.py → 0 failures`, so W4 cannot PASS until fixed.

**This is a real fix (not wave-owned)**: the test suite must pass for W4's scaffold. Parent caught it during verification (11 ERRORS, 3 passed) — the app imports and `/health` returns 200, but lifespan-isolation unit tests error. Fixing now.

---

## Cross-Wave Stale-Import Tracker (for W18 gate)

The following `src/` files have broken imports from W2/W3 deletions, owned by later waves. W18 integration test must verify ALL resolved:

| File | Broken import | Owning wave | Resolution |
|------|---------------|------------|------------|
| `src/channels/whatsapp/{hard_stop,ops_commands,service,__init__}.py` (4) | `HardStopHandler` | W16 | rewrite to guinevere.channels.whatsapp, delete src/ |
| `src/discord/cmd_{pc,surveillance_pause,surveillance_status}.py` (3) | `check_consent`/consent_gate | W15 | port to guinevere.discord, delete src/ |
| `src/core/main.py` | `P22ConsentChecker` + comments | W4+cleanup | absorb into guinevere.http, delete src/core/main.py |
| `src/core/api/routes.py` | `ConsentLedgerWriter` | W4+cleanup | absorb into guinevere.http.routes, delete |
| `src/surveillance/__init__.py` + legacy src/surveillance/ | consent_gate re-export | cleanup | delete src/surveillance/ (guinevere.surveillance replaces) |
| `src/gmail/{consent_manager,router,service}.py` (3) | consent_gate | W16 | port to guinevere.channels.gmail, delete |
| `src/hermes_plugins/commands_surveillance/` (4) | consent_gate | W12 | port to guinevere.tools, delete |
| `src/wearable/{writer,sync,mood_integration,alert_router}.py` (4) | health_consent | W13 | port to guinevere.life_kernel, delete |
| `src/life_integrations/{wiring,router}.py` (2) | ConsentGate | W12 | port to guinevere.tools, delete |

**Total**: ~25 files with stale imports, all owned by W12/W13/W15/W16/cleanup, all resolved before W18.

**W18 gate criterion**: `grep -rn 'from src\.consent\|from src\.surveillance\.consent_gate\|from src\.life_integrations\.consent\|from src\.core\.services\.hard_stop_handler\|from src\.hermes\.safety_plugin' src/ 2>/dev/null` → must return 0 matches (all stale imports cleaned by owning waves).

---

## Verdict

- **W1**: ✅ PASS (0 findings, audit-confirmed)
- **W2**: ✅ PASS (guinevere/ clean, fork insulated, 4 src/ stale imports owned by W16)
- **W3**: ✅ PASS (guinevere/ clean, migration ADR-066-compliant, fork insulated, 7 src/ stale imports owned by W4/W5/W12/W15/W16)
- **W5**: ✅ PASS (0 findings, 51 tests, audit-confirmed)
- **W4**: ⏳ fix in flight (load_settings mock mismatch)

**No silent dismissal**: every finding recorded with root cause, evidence, owning wave, and W18 gate criterion. Per AGENTS.md §2.10, "documented false-positive with evidence" — here documented *owned-by-later-wave* with parent-verified insulation evidence.

Footer: Guinevere, 2026-06-29, round-1 fix log, 11 findings adjudicated (9 wave-owned + 2 real-fix-in-flight-W4), 0 silently dismissed.
