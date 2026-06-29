# W3 Auditor Gate -- M11 No Consent Gate + ADR-066 Migration

**Auditor**: Independent (sub-agent)
**Date**: 2026-06-29
**Branch**: feat/p24-hermes-fork
**Commit**: d2ca003 (combined W2+W3+W5)

---

## Check Results

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| 9 | `src/consent/` deleted | PASS | `ls: cannot access 'src/consent/': No such file or directory` |
| 9 | `src/surveillance/consent_gate.py` deleted | PASS | `ls: cannot access 'src/surveillance/consent_gate.py': No such file or directory` |
| 9 | `src/life_integrations/consent.py` deleted | PASS | `ls: cannot access 'src/life_integrations/consent.py': No such file or directory` |
| 9 | `src/life_integrations/consent_checker.py` deleted | PASS | `ls: cannot access 'src/life_integrations/consent_checker.py': No such file or directory` |
| 9 | `src/life_integrations/consent_ledger_writer.py` deleted | PASS | `ls: cannot access 'src/life_integrations/consent_ledger_writer.py': No such file or directory` |
| 9 | `src/wearable/health_consent.py` deleted | PASS | `ls: cannot access 'src/wearable/health_consent.py': No such file or directory` |
| 9 | `hermes-config/hooks/consent_gate.py` deleted | PASS | `ls: cannot access 'hermes-config/hooks/consent_gate.py': No such file or directory` |
| 10 | Migration file exists | PASS | `alembic/versions/p24_consent_ref_nullable.py` exists |
| 11 | Migration parses as valid Python | PASS | `ast.parse()` succeeded, exit 0 |
| 12 | Migration implements ADR-066 | PASS | See deep verification below |
| 13 | No active consent references in guinevere/ | PASS | `grep -rn 'consent_gate\|check_consent\|ConsentChecker\|ConsentGate' guinevere/ run_agent.py` = 0 matches |
| 14 | `import guinevere` succeeds | PASS | `python -c "import guinevere; print('OK')"` = OK (from W2 check 7) |

## Deep Verification: Migration ADR-066 Compliance

The migration `p24_consent_ref_nullable.py` (107 lines) implements ADR-066 correctly:

1. **event_source column**: Added as `String(32)`, `NOT NULL`, `server_default='dev_workflow'` -- all existing rows default to `dev_workflow` (L60-69)
2. **consent_ref nullable**: `alter_column` makes `consent_ref` nullable on all 5 tables (L72-77)
3. **CHECK constraint**: `event_source <> 'dev_workflow' OR consent_ref IS NOT NULL` (L80-84)
   - `dev_workflow` rows MUST have `consent_ref NOT NULL` (HARD STOP)
   - `hermes_runtime` rows MAY have `consent_ref IS NULL` (ADR-066 relaxation)
4. **5 tables covered**: `society_event_memory`, `society_event_decision`, `society_event_action`, `society_event_drift`, `society_event_publication` (L29-35)
5. **Defensive**: Uses `_table_exists()` and `_col_exists()` guards -- safe on databases without these tables yet (L54-68)
6. **Downgrade present**: Re-enforces NOT NULL and drops event_source column (L87-107)
7. **Revision chain**: `down_revision = "p22_002_revoke_truncate_audit"` (L25) -- chains to the correct predecessor

ADR-066 semantics: dev_workflow = full consent required; hermes_runtime = consent_ref nullable (Hermes owns decisions).

## Findings

| ID | Severity | Description | Location | Recommended Fix |
|----|----------|-------------|----------|-----------------|
| W3-F01 | CRITICAL | `src/core/main.py` L184 imports `P22ConsentChecker` from deleted `src.life_integrations.consent_checker`. The `_build_consent_checker()` function (L168-185) will raise ModuleNotFoundError at startup. | `src/core/main.py:184` | Update import to `guinevere.surveillance` or stub with None |
| W3-F02 | CRITICAL | `src/core/api/routes.py` L482,530 imports `ConsentLedgerWriter` from deleted `src.life_integrations.consent_ledger_writer`. Two API endpoints will fail at import time. | `src/core/api/routes.py:482,530` | Update imports or remove dead endpoints |
| W3-F03 | CRITICAL | `src/discord/cmd_pc.py` L234 imports `check_consent` from deleted `src.surveillance.consent_gate`. The surveillance PC command will crash. | `src/discord/cmd_pc.py:234` | Remove consent check or update import |
| W3-F04 | CRITICAL | `src/discord/cmd_surveillance_pause.py` L116 imports from deleted `src.surveillance.consent_gate`. Surveillance pause command will crash. | `src/discord/cmd_surveillance_pause.py:116` | Remove consent check or update import |
| W3-F05 | CRITICAL | `src/discord/cmd_surveillance_status.py` L157 imports `check_consent` from deleted `src.surveillance.consent_gate`. Also references `consent_gate.VALID_SURVEILLANCE_SCOPES` at L26. | `src/discord/cmd_surveillance_status.py:26,157` | Remove consent check or update import |
| W3-F06 | HIGH | `src/surveillance/__init__.py` L12 imports from deleted `src.surveillance.consent_gate`. Even `import src.surveillance` will now raise ModuleNotFoundError, cascading to any module that imports from the surveillance package. | `src/surveillance/__init__.py:12` | Update __init__.py to remove consent_gate re-exports |
| W3-F07 | MEDIUM | `src/core/main.py` L635 references `HardStopHandler.is_safe` in a comment, and L645 references `ConsentGateShim` -- both reference deleted components. | `src/core/main.py:635,645` | Update comments to reflect new architecture |

## Cascading Breakage Detail

The `src/surveillance/__init__.py` import from `consent_gate` creates a cascade:
```
import src.surveillance
  -> src/surveillance/__init__.py L12
    -> from src.surveillance.consent_gate import (VALID_SURVEILLANCE_SCOPES, check_consent, ...)
      [DELETED] -- ModuleNotFoundError
```

This means ANY code doing `from src.surveillance.auth import ...` or `from src.surveillance.consent_gate import ...` will fail because the package-level __init__.py fails first.

**Total broken import sites**: 7 files, 12+ import statements across `src/core/`, `src/discord/`, and `src/surveillance/`.

## Verification: Scope Boundary

The audit spec's check 13 (`grep -rn ... guinevere/ run_agent.py`) correctly shows 0 matches within the P24 ported tree. All findings are in `src/`, the P22 operational codebase.

## Verdict

**CONDITIONAL PASS** -- The `guinevere/` tree (P24 ported code) is clean: 0 active consent references, migration correctly implements ADR-066 with dev_workflow NOT NULL + hermes_runtime nullable. However, 7 files in `src/` have broken imports from the 7 deleted consent modules. The `src/surveillance/__init__.py` cascade means the entire `src.surveillance` package is broken. The `src/` tree must be updated or the migration plan must account for `src/` deprecation before merge.

**Findings**: 5 CRITICAL, 1 HIGH, 1 MEDIUM, 0 LOW
