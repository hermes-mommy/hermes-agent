# Scaffold: STEP-P6-011 — time

## Expected Files

- `src/mcp/tools/time_tools.py` — Timezone conversion and scheduling utilities
- `tests/mcp/test_time_tools.py` — Unit tests for all time operations

## Forbidden Patterns

- `as any`
- `@ts-ignore`
- `# type: ignore`
- `cast(`
- `except Exception:` (empty/swallowed)
- `except:` (bare)
- `print(` (use structlog)
- `import logging` (use structlog)
- Manual timezone offset math (use `zoneinfo` or `pytz`)
- `datetime.utcnow()` (deprecated; use `datetime.now(timezone.utc)`)

## Required Commands

| Command | Expected Exit Code | Notes |
|---------|-------------------|-------|
| `python -m pytest tests/mcp/test_time_tools.py -v` | 0 | All tests pass |
| `python -m ruff check src/mcp/tools/time_tools.py` | 0 | No lint errors |
| `python -m mypy src/mcp/tools/time_tools.py` | 0 | No type errors |

## Implementation Details

### Key Design

- **Timezone Library:** `zoneinfo` (Python 3.12 stdlib) for IANA timezone support
- **Default Timezone:** `Asia/Jakarta` (WIB, UTC+7)
- **Auth Level:** `AuthLevel.READ_AUTO` for all operations
- **Cost:** $0

### Function Signatures

```python
async def current_time(timezone: str = "Asia/Jakarta", format: str = "YYYY-MM-DD HH:mm:ss") -> str:
    """Get current date and time in specified timezone."""

async def convert_time(
    source_timezone: str,
    target_timezone: str,
    time: str,
) -> str:
    """Convert time between IANA timezones."""

async def days_in_month(date: str | None = None) -> int:
    """Get number of days in a month. Defaults to current month."""

async def relative_time(time: str) -> str:
    """Get human-readable relative time from now (e.g., '3 hours ago')."""

async def get_timestamp(time: str) -> int:
    """Get Unix timestamp for a datetime string."""

async def get_week_year(date: str | None = None) -> dict[str, int]:
    """Get week number and ISO week for a date."""
```

### Test Cases

- `convert_time("UTC", "Asia/Jakarta", "2026-05-31 12:00:00")` → `"2026-05-31 19:00:00"` (WIB = UTC+7)
- `convert_time("Asia/Jakarta", "UTC", "2026-06-01 00:00:00")` → `"2026-05-31 17:00:00"`
- `days_in_month("2026-02-15")` → `28` (2026 not a leap year)
- `days_in_month("2024-02-15")` → `29` (2024 leap year)

### Error Handling

- Invalid timezone → raise `ValueError` with list of valid IANA zones
- Invalid date format → raise `ValueError` with expected format

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-011/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-011/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] No API keys or secrets
- [ ] Auth level `READ_AUTO` enforced for all operations
- [ ] `zoneinfo` used for timezone handling (not manual offset math)
- [ ] WIB conversion: UTC 12:00 → Jakarta 19:00 verified in tests
- [ ] `datetime.now(timezone.utc)` used instead of deprecated `datetime.utcnow()`
- [ ] `structlog` used for all logging
- [ ] All 6 functions implemented and tested
