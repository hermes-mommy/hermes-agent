# P7-Audit: Surveillance Module Dependency Map

Date: 2026-06-03
Scope: 14 files in `src/surveillance/` plus `src/discord/cmd_surveillance_status.py`, `cmd_surveillance_pause.py`, `cmd_surveillance_resume.py`, and `src/core/main.py`.

## Verdict

PASS: Complete dependency map produced. No circular imports detected in the current `src/surveillance/` implementation. Main risks are package `__init__.py` importing every submodule, `get_retention_days` name collision, exported private `_map_event_to_scope`, non-exported `safe_mode.check_message_safety`, and production wiring gap in `consumer.main()` DB session factory.

## 1. Module Inventory

| # | File | Role |
|---|---|---|
| 1 | `src/surveillance/__init__.py` | package re-export API |
| 2 | `src/surveillance/auth.py` | HMAC-SHA256 FastAPI dependency |
| 3 | `src/surveillance/classification.py` | data classification mapping |
| 4 | `src/surveillance/consent_gate.py` | fail-closed consent checker |
| 5 | `src/surveillance/consumer.py` | async Redis-to-DB consumer |
| 6 | `src/surveillance/models.py` | Pydantic request/response models |
| 7 | `src/surveillance/redis_buffer.py` | Redis DB2 event buffer |
| 8 | `src/surveillance/replay.py` | timestamp + nonce replay protection |
| 9 | `src/surveillance/retention.py` | retention constants and tier helpers |
| 10 | `src/surveillance/router.py` | FastAPI `/surveillance/events` router |
| 11 | `src/surveillance/safe_mode.py` | HARD STOP/safe-mode surveillance guard |
| 12 | `src/surveillance/secret_scanner.py` | secret detection/redaction |
| 13 | `src/surveillance/secrets.py` | SOPS/env HMAC secret loader |
| 14 | `src/surveillance/timescale.py` | TimescaleDB ingestion writer |

## 2. Per-file Imports

### `src/surveillance/__init__.py`

Imports/re-exports:
- `src.surveillance.auth`: `HMACVerification`, `verify_hmac`
- `src.surveillance.classification`: `ClassificationResult`, `DataClassification`, `classify_event`, `get_retention_days`
- `src.surveillance.consent_gate`: `ConsentCheckResult`, `ConsentStatus`, `check_consent`, `invalidate_cache`
- `src.surveillance.consumer`: `SurveillanceConsumer`, `_map_event_to_scope`
- `src.surveillance.models`: `ErrorResponse`, `SurveillanceEventRequest`, `SurveillanceEventResponse`
- `src.surveillance.redis_buffer`: `RedisSurveillanceBuffer`, `SurveillanceBuffer`, `create_buffer`
- `src.surveillance.replay`: `check_nonce`, `validate_timestamp`
- `src.surveillance.router`: `surveillance_router`
- `src.surveillance.safe_mode`: `ConfrontationDecision`, `SurveillanceSafeModeGuard`
- `src.surveillance.secret_scanner`: `ScanResult`, `redact_secrets`, `scan_text`
- `src.surveillance.secrets`: `get_hmac_secret`
- `src.surveillance.retention`: retention constants, `RetentionTier`, `calculate_retention_until`, `get_retention_policy_summary`, plus `get_retention_days as get_tier_retention_days`
- `src.surveillance.timescale`: `IngestionResult`, `TimescaleIngester`

Internal surveillance imports: all 13 sibling modules.
Risk: importing `src.surveillance` loads almost the entire package. Do not add `from src.surveillance import ...` inside surveillance submodules or circular imports may appear.

### `src/surveillance/auth.py`

Stdlib: `hashlib`, `hmac`, `dataclasses.dataclass`.
Third-party: `structlog`, `fastapi.Header`, `fastapi.HTTPException`, `fastapi.Request`.
Internal surveillance: `src.surveillance.replay.check_nonce`, `validate_timestamp`; `src.surveillance.secrets.get_hmac_secret`.
Dependency chain: `auth -> replay`, `auth -> secrets`.
Circular risk: none; both dependencies are leaf modules.

### `src/surveillance/classification.py`

Stdlib: `dataclasses.dataclass`, `enum.StrEnum`, `typing.Final`.
Third-party: `structlog`.
Internal surveillance: none.
Dependency chain: leaf.

### `src/surveillance/consent_gate.py`

Stdlib: `json`, `os`, `dataclasses.dataclass`, `datetime.datetime`, `datetime.timezone`, `enum.StrEnum`, `typing.Any`, `typing.Protocol`, `typing.runtime_checkable`.
Third-party: `redis.asyncio as aioredis`, `structlog`.
Internal surveillance: none.
External integration: Redis DB2 consent cache; database consent ledger (`consent.consent_ledger`) via injected DB session.
Dependency chain: leaf.

### `src/surveillance/consumer.py`

Stdlib: `asyncio`, `json`, `os`, `signal`, `uuid`, `datetime.datetime`, `datetime.timezone`, `typing.Any`, `Callable`, `Protocol`, `runtime_checkable`.
Third-party: `structlog`; lazy `redis.asyncio as aioredis` inside `main()`.
Internal surveillance: `classification.classify_event`, `consent_gate.check_consent`, `redis_buffer.SurveillanceBuffer`, `secret_scanner.scan_text`; lazy `redis_buffer.RedisSurveillanceBuffer` inside `main()`.
Dependency chain: `consumer -> classification`, `consumer -> consent_gate`, `consumer -> redis_buffer`, `consumer -> secret_scanner`.
Circular risk: none; all are leaf modules.
Important gap: `main()` defines `db_session_factory()` that raises `NotImplementedError`, so production TimescaleDB wiring is incomplete.

### `src/surveillance/models.py`

Stdlib: `datetime.datetime`, `typing.Any`, `typing.Literal`.
Third-party: `pydantic.BaseModel`, `ConfigDict`, `Field`, `field_validator`.
Internal surveillance: none.
Dependency chain: leaf.

### `src/surveillance/redis_buffer.py`

Stdlib: `json`, `os`, `dataclasses.dataclass`, `typing.Any`, `Protocol`, `runtime_checkable`.
Third-party: `redis.asyncio as aioredis`, `structlog`.
Internal surveillance: none.
External integration: Redis DB2 list buffer (`surveillance:buffer`).
Dependency chain: leaf.

### `src/surveillance/replay.py`

Stdlib: `os`, `time`.
Third-party: `redis.asyncio as aioredis`, `structlog`, `fastapi.HTTPException`.
Internal surveillance: none.
External integration: Redis DB2 nonce store (`surveillance:nonce:*`).
Dependency chain: leaf.

### `src/surveillance/retention.py`

Stdlib: `datetime.datetime`, `datetime.timedelta`, `enum.StrEnum`, `typing.Any`, `typing.Final`.
Third-party: `structlog`.
Internal surveillance: none.
Dependency chain: leaf.

### `src/surveillance/router.py`

Stdlib: `datetime.datetime`, `datetime.timezone`, `uuid.uuid4`.
Third-party: `structlog`, `fastapi.APIRouter`, `fastapi.Depends`.
Internal surveillance: `auth.HMACVerification`, `auth.verify_hmac`, `models.SurveillanceEventRequest`, `models.SurveillanceEventResponse`.
Dependency chain: `router -> auth -> replay/secrets`; `router -> models`.
Circular risk: none.

### `src/surveillance/safe_mode.py`

Stdlib: `re`, `collections.abc.Callable`, `dataclasses.dataclass`, `typing.Final`.
Third-party: `structlog`.
Internal surveillance: none.
External internal dependency: `src.core.services.hard_stop_handler.SafetyState`.
Dependency chain: `safe_mode -> src.core.services.hard_stop_handler`.
Circular risk: none found; `hard_stop_handler.py` references surveillance only as text, not import.

### `src/surveillance/secret_scanner.py`

Stdlib: `math`, `re`, `collections.Counter`, `dataclasses.dataclass`, `dataclasses.field`, `typing.Final`.
Third-party: `structlog`.
Internal surveillance: none.
Dependency chain: leaf.

### `src/surveillance/secrets.py`

Stdlib: `os`, `subprocess`, `pathlib.Path`.
Third-party: `structlog`, `yaml`.
Internal surveillance: none.
External integration: environment variable `SURVEILLANCE_HMAC_SECRET`; SOPS subprocess decrypt of `secrets/guinevere-secrets.yaml`.
Dependency chain: leaf.

### `src/surveillance/timescale.py`

Stdlib: `uuid`, `dataclasses.dataclass`, `datetime.datetime`, `datetime.timezone`, `typing.Any`, `typing.Callable`.
Third-party: `structlog`, `sqlalchemy.func`, `insert`, `select`, `text`.
Internal surveillance: none.
External internal dependency: `src.memory.models.IngestionLog`, `src.memory.models.SurveillanceEvents`.
External integration: PostgreSQL/TimescaleDB `surveillance.events`, `surveillance.ingestion_log`.
Dependency chain: `timescale -> src.memory.models`.
Circular risk: none found; `src.memory.models` does not import `src.surveillance`.

## 3. Internal Dependency Graph

```text
__init__ -> auth, classification, consent_gate, consumer, models, redis_buffer,
            replay, router, safe_mode, secret_scanner, secrets, retention, timescale

auth -> replay
auth -> secrets
router -> auth
router -> models
consumer -> classification
consumer -> consent_gate
consumer -> redis_buffer
consumer -> secret_scanner
consumer.main() -> redis_buffer.RedisSurveillanceBuffer (lazy)
safe_mode -> src.core.services.hard_stop_handler.SafetyState
timescale -> src.memory.models.IngestionLog, SurveillanceEvents
```

Leaf modules with no surveillance imports: `classification.py`, `consent_gate.py`, `models.py`, `redis_buffer.py`, `replay.py`, `retention.py`, `secret_scanner.py`, `secrets.py`.

## 4. External Modules Importing Surveillance

### `src/core/main.py`

Line 139:
```python
from src.surveillance.router import surveillance_router
```
Line 141:
```python
app.include_router(surveillance_router)
```
Effect: mounts FastAPI `/surveillance` router.

### `src/discord/cmd_surveillance_status.py`

Function-level lazy imports:
- Line 157: `from src.surveillance.consent_gate import check_consent`
- Line 180: `from src.surveillance.redis_buffer import create_buffer`
- Line 207: `from src.surveillance.redis_buffer import create_buffer`
- Line 229: `from src.surveillance.redis_buffer import create_buffer`

Top-level imports are only `typing.Any`, `typing.Awaitable`, `typing.Callable`, `structlog`, and `.colors.SURVEILLANCE`.

### `src/discord/cmd_surveillance_pause.py`

No imports from `src.surveillance`. Top-level imports: `typing.Any`, `structlog`, `.colors.SURVEILLANCE`. Pause state is module-local (`_paused`).

### `src/discord/cmd_surveillance_resume.py`

No imports from `src.surveillance`. Top-level imports: `typing.Any`, `structlog`, `.colors.SURVEILLANCE`. Resume state is module-local (`_paused`).

### `src/discord/bot.py`

Lines 173-175 import Discord command callbacks only:
```python
from .cmd_surveillance_status import surveillance_status_callback
from .cmd_surveillance_pause import surveillance_pause_callback
from .cmd_surveillance_resume import surveillance_resume_callback
```
No direct `src.surveillance` import.

## 5. Other External References

- `src/discord/commands.py`: command metadata strings for surveillance commands; no Python import.
- `src/discord/cmd_help.py`: help category string; no Python import.
- `src/memory/models.py`: SQLAlchemy models for schema `surveillance`; no Python import from `src.surveillance`.
- `src/memory/read_pipeline.py` and `write_pipeline.py`: textual/source-label references to surveillance; no Python import.
- `src/core/services/hard_stop_handler.py`: textual status message references surveillance; no Python import.

## 6. Circular Import Risk

Current state: no active circular imports detected.

Risk notes:
1. `__init__.py` imports all submodules. If any submodule imports from package root (`from src.surveillance import X`) instead of direct sibling module paths, it can create a circular import.
2. `safe_mode.py -> src.core.services.hard_stop_handler` is safe now because `hard_stop_handler.py` does not import surveillance.
3. `timescale.py -> src.memory.models` is safe now because `memory.models` does not import surveillance.
4. `router -> auth -> replay/secrets` and `consumer -> leaf modules` are acyclic.

## 7. `__init__.py` Exports vs Actual Usage

Exports present and valid:
- Public FastAPI/API: `surveillance_router`, `SurveillanceEventRequest`, `SurveillanceEventResponse`, `ErrorResponse`, `verify_hmac`, `HMACVerification`.
- Pipeline: `SurveillanceConsumer`, `SurveillanceBuffer`, `RedisSurveillanceBuffer`, `create_buffer`, `_map_event_to_scope`.
- Gates/helpers: `check_consent`, `invalidate_cache`, `check_nonce`, `validate_timestamp`, `get_hmac_secret`, `scan_text`, `redact_secrets`, `SurveillanceSafeModeGuard`.
- Classification/retention: `ClassificationResult`, `DataClassification`, `classify_event`, `get_retention_days`, `RetentionTier`, retention constants/helpers, `get_tier_retention_days`.
- Timescale: `IngestionResult`, `TimescaleIngester`.

Potential export mismatches:
1. `safe_mode.check_message_safety` exists but is not imported/exported by `__init__.py`; use direct import `from src.surveillance.safe_mode import check_message_safety` if needed.
2. `_map_event_to_scope` is exported despite private underscore naming. This is likely for tests but is unusual as package API.
3. `get_retention_days` exists in both `classification.py` and `retention.py`. Package root exports classification `get_retention_days`; retention version is exported as `get_tier_retention_days`.

## 8. External Integration Points

| Integration | Files | Notes |
|---|---|---|
| FastAPI | `router.py`, `auth.py`, `core/main.py` | `/surveillance/events`, HMAC dependency, app router include |
| Redis DB2 | `replay.py`, `redis_buffer.py`, `consent_gate.py`, Discord status command | nonce store, event buffer, consent cache/status |
| PostgreSQL / TimescaleDB | `timescale.py`, `consumer.py`, `src.memory.models` | `surveillance.events`, `surveillance.ingestion_log`; consumer DB session not wired in `main()` |
| SOPS / YAML secrets | `secrets.py` | `SURVEILLANCE_HMAC_SECRET` env override or `sops --decrypt secrets/guinevere-secrets.yaml` |
| Discord | `cmd_surveillance_status.py`, `cmd_surveillance_pause.py`, `cmd_surveillance_resume.py`, `bot.py` | Slash commands; only status command imports surveillance modules lazily |
| Core HARD STOP | `safe_mode.py` | Imports `SafetyState` from core service |

## 9. Summary Findings

- Dependency graph is shallow and acyclic.
- 8/14 modules are leaf modules with no surveillance imports.
- External consumers are limited and explicit: `core/main.py` for FastAPI router, `cmd_surveillance_status.py` for status queries, and Discord bot command callback wiring.
- No missing `__init__.py` exports are blocking current usage because all actual external imports use direct module paths, not package-root imports.
- Main improvement candidates: avoid future package-root imports inside submodules, consider whether `check_message_safety` should be exported, clarify `_map_event_to_scope` public/private intent, and wire `consumer.main()` to a real DB session factory.
