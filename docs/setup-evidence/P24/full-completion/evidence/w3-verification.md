# W3 Verification — M11 No Consent Gate (ADR-066)

**Date**: 2026-06-29
**Wave**: W3
**Task**: Delete consent modules from src/; clean stale imports in surviving code; write alembic migration for consent_ref nullable (ADR-066).

---

## What Was Done

1. **Deleted consent files** (7 files + 1 directory):
   - `src/consent/__init__.py` — DELETED
   - `src/consent/revocation_handler.py` — DELETED
   - `src/consent/` directory — DELETED
   - `src/surveillance/consent_gate.py` — DELETED
   - `src/life_integrations/consent.py` — DELETED
   - `src/life_integrations/consent_checker.py` — DELETED
   - `src/life_integrations/consent_ledger_writer.py` — DELETED
   - `src/wearable/health_consent.py` — DELETED
   - `hermes-config/hooks/consent_gate.py` — DELETED

2. **Created alembic migration**: `alembic/versions/p24_consent_ref_nullable.py`
   - Adds `event_source` column (default 'dev_workflow') to 5 society event-store tables
   - Makes `consent_ref` nullable (for event_source='hermes_runtime')
   - Adds CHECK constraint: dev_workflow rows MUST have consent_ref NOT NULL
   - Defensive: skips tables that don't exist (D2 local-only, no live PG)

3. **Stale import cleanup in surviving code**: NO cleanup needed.
   - `guinevere/`, `agent/`, `tools/`, `run_agent.py` — 0 matches for consent_gate/consent_checker/ConsentGate/ConsentChecker
   - Surviving references in `guinevere/surveillance/buffer.py` and `guinevere/surveillance/receiver.py` are **docstrings/comments only** (ADR-062 documentation), not active imports.

---

## Files Deleted

| File | Status |
|------|--------|
| `src/consent/__init__.py` | DELETED |
| `src/consent/revocation_handler.py` | DELETED |
| `src/consent/` directory | DELETED |
| `src/surveillance/consent_gate.py` | DELETED |
| `src/life_integrations/consent.py` | DELETED |
| `src/life_integrations/consent_checker.py` | DELETED |
| `src/life_integrations/consent_ledger_writer.py` | DELETED |
| `src/wearable/health_consent.py` | DELETED |
| `hermes-config/hooks/consent_gate.py` | DELETED |

---

## Migration

**Path**: `alembic/versions/p24_consent_ref_nullable.py`

**Chain**: `p22_002_revoke_truncate_audit` → `p24_consent_ref_nullable`

**Behavior**:
- Inspects 5 society event-store tables (society_event_memory, society_event_decision, society_event_action, society_event_drift, society_event_publication)
- Skips tables that don't exist (D2 defensive)
- For existing tables: adds `event_source` column (default 'dev_workflow'), makes `consent_ref` nullable, adds CHECK constraint

---

## Stale-Import Cleanup Notes (r18 §6.1)

**Surviving fork code (guinevere/, agent/, tools/, run_agent.py)**: 0 active consent imports. 2 docstring references (ADR-062 documentation) — acceptable.

**src/ files with consent imports (pending owning wave cleanup)**: 33 files still reference deleted consent modules. These will be cleaned in their owning waves:

- **W5 (surveillance)**: `src/surveillance/consumer.py`, `src/surveillance/__init__.py`
- **W12 (life_integrations)**: `src/life_integrations/base.py`, `registry.py`, `router.py`, `runtime.py`, `wiring.py`, `_shims.py`
- **W13 (wearable)**: `src/wearable/alert_router.py`, `mood_integration.py`, `sync.py`, `writer.py`
- **W16 (gmail)**: `src/gmail/consent_manager.py`, `commands/consent.py`, `draft/generator.py`, `router.py`, `service.py`, `tests/test_e2e_gmail.py`, `audit/security-audit.md`
- **Other waves**: `src/channels/whatsapp/` (3 files), `src/core/main.py`, `src/core/api/routes.py`, `src/discord/` (3 files), `src/hermes_plugins/commands_surveillance/` (3 files), `src/knowledge_graph/` (2 files), `src/life_integrations/adapters/_clients/github_client_shim.py`

---

## Validation Results

### Required Commands

```bash
# 1. Verify deletions
ls src/consent/ src/surveillance/consent_gate.py src/life_integrations/consent.py src/life_integrations/consent_checker.py src/life_integrations/consent_ledger_writer.py src/wearable/health_consent.py hermes-config/hooks/consent_gate.py 2>&1
# Result: "No such file or directory" for all — PASS

# 2. Import test
.venv/Scripts/python.exe -c "import guinevere; print('guin OK')"
# Result: "guin OK" exit 0 — PASS

# 3. Migration exists
ls alembic/versions/p24_consent_ref_nullable.py
# Result: exists — PASS

# 4. No consent_gate in surviving fork
grep -rn 'consent_gate' guinevere/ agent/ tools/ run_agent.py 2>/dev/null
# Result: 2 docstring matches (not active code) — PASS
```

---

## Forbidden Pattern Scan

| Pattern | Surviving Code | Result |
|---------|----------------|--------|
| `consent_gate` (ACTIVE) | guinevere/, agent/, tools/, run_agent.py | 0 active matches (2 docstring refs) — PASS |
| `consent_ref NOT NULL` for hermes_runtime | alembic migration | CHECK constraint enforces NOT NULL only for dev_workflow — PASS |

---

## Caveats

1. **src/ files still have consent imports**: 33 files in src/ reference deleted consent modules. These will cause ImportError if src/ is imported directly. This is expected — src/ is being deleted across waves (W5, W12, W13, W16, etc.). The surviving fork code (guinevere/) has no consent imports.

2. **Migration not applied**: D2 local-only, no live PG. Migration file exists and syntax-valid, but not applied to any database.

3. **Docstring references**: 2 files in guinevere/surveillance/ mention consent_gate in docstrings (ADR-062 documentation). These are not active code and don't cause ImportError.

4. **hermes-config/hooks/consent_gate.py deleted**: This was a standalone hook file, not imported by surviving code.

---

## Footer

**Verdict**: W3 PASS
**Files deleted**: 9 (7 files + 1 directory + 1 hook file)
**Migration**: `alembic/versions/p24_consent_ref_nullable.py` — defensive, syntax-valid
**Stale imports in surviving code**: 0 active (2 docstring refs acceptable)
**import guinevere**: exit 0
