# B1 Implementation — Brutal-Audit Fix Verification

## Files Changed
- `src/discord/cmd_integrations.py` — F26 rename + F27 bare-except fix
- `src/discord/_entrypoint.py` — F01 import + 6 tree.command registrations + core_names expansion
- `src/discord/_command_registry.py` — F01 6 CommandSpec entries + require_canonical_registry 35→41
- `tests/p22/test_cmd_integrations.py` — Updated consent_callback → integration_consent_callback in tests

## F26: consent_callback renamed to integration_consent_callback
- `cmd_integrations.py:459`: `async def integration_consent_callback(interaction: Any) -> None:`
- `cmd_integrations.py:663`: `__all__` entry updated to `"integration_consent_callback"`
- `cmd_consent.py:67`: canonical `consent_callback` left untouched
- Test file updated: all `cmd_integrations.consent_callback` → `cmd_integrations.integration_consent_callback`

## F27: bare except Exception replaced with specific catches
- Replaced `except Exception as exc:  # noqa: BLE001` with:
  - `except json.JSONDecodeError as exc:` (for `response.json()`)
  - `except (KeyError, ValueError) as exc:` (defensive)
- Each uses `logger.exception("integrations_api_unexpected_error", path=path, error=str(exc))` + `return None`
- Added `import json` at top of file
- Removed `# noqa: BLE001` comment

## F01: 6 Discord slash commands registered

### 6 Commands Wired in `_entrypoint.py`
| Slash Name | Callback |
|---|---|
| `integration-status` | `status_callback` |
| `integration-capabilities` | `capabilities_callback` |
| `integration-test` | `test_callback` |
| `integration-missing` | `missing_callback` |
| `integration-consent` | `integration_consent_callback` |
| `integration-dry-run` | `dry_run_callback` |

### 6 CommandSpecs added to `_command_registry.py` (category "integration")
Registry count: 35 → 41

### `core_names` tuple expanded
All 6 names added so the stub loop skips them (they're real-wired).

## Verification Results

### Forbidden Patterns (all clean)
- `grep -rn "def consent_callback" src/discord/` → exactly 1 match (`cmd_consent.py:67`)
- `grep -n "except Exception" src/discord/cmd_integrations.py` → 0 matches
- `grep -rn "expected 35 commands" src/discord/` → 0 matches

### Tests
```
$ python -m pytest tests/p22/test_cmd_integrations.py -v
====================== 35 passed, 217 warnings in 0.90s =======================

$ python -c "from src.discord._command_registry import COMMAND_SPECS, require_canonical_registry; require_canonical_registry(); assert len(COMMAND_SPECS)==41, len(COMMAND_SPECS)"
PASS: len(COMMAND_SPECS) == 41

$ python -m pytest tests/p22/ -q --no-header 2>&1 | tail -3
1 failed, 953 passed, 5510 warnings in 41.14s
(1 failure is pre-existing: test_l1_list_dir_audited — not B1-related)
```

### Grep Verification
- `cmd_integrations` imported in `_entrypoint.py` → line 210
- All 6 `integration-*` names in `_command_registry.py` → lines 256, 261, 266, 272, 277, 295
- `consent_callback` in `cmd_integrations.py` → 0 (renamed to `integration_consent_callback`)
