# D08 Architecture Recheck — P7.5 Remediation Audit

| Field | Value |
|---|---|
| Audit type | Re-audit of CRITICAL findings from D08 |
| Scope | `src/surveillance/router.py`, `src/surveillance/consumer.py`, `tests/surveillance/test_router.py` |
| Auditor | Guinevere (read-only, no source modifications) |
| Date | 2026-06-03 |
| Overall Verdict | **PASS** |

---

## Finding C1 — Router doesn't push events to Redis buffer

**Original issue**: After HMAC/auth passes, the endpoint returns 202 but never pushes the event to the Redis DB2 buffer, so the consumer never sees it.

**Expected fix**: Import `create_buffer`, create module-level `_buffer`, call `await _buffer.push_event(event.model_dump(mode="json"))` in the endpoint after logging.

### Verdict: **PASS**

### Evidence

| Check | Status | Location |
|---|---|---|
| `create_buffer` import exists | PASS | `router.py` line 17: `from src.surveillance.redis_buffer import create_buffer` |
| `_buffer = create_buffer()` at module level | PASS | `router.py` line 26: `_buffer = create_buffer()` |
| `await _buffer.push_event(...)` in endpoint | PASS | `router.py` line 60: `await _buffer.push_event(event.model_dump(mode="json"))` |
| Wrapped in try/except (best-effort) | PASS | `router.py` lines 58-65: `try:` / `except Exception:` logs via `logger.exception("surveillance_buffer_push_error", ...)` — does not re-raise |
| Push happens BEFORE the return statement | PASS | Push at lines 58-65; return at lines 67-71 |

### Code snippet (router.py lines 55-71)

```python
    # Best-effort push to Redis DB2 buffer (P7-005).
    # Never blocks the 202 response - failures are logged only.
    try:
        await _buffer.push_event(event.model_dump(mode="json"))
    except Exception:
        logger.exception(
            "surveillance_buffer_push_error",
            event_id=event_id,
            event_type=event.event_type,
        )

    return SurveillanceEventResponse(
        status="accepted",
        event_id=event_id,
        received_at=datetime.now(tz=timezone.utc),
    )
```

---

## Finding C2 — `consumer.main()` DB session factory raises `NotImplementedError`

**Original issue**: The background worker cannot connect to the database because `main()` raises `NotImplementedError`.

**Expected fix**: Use `create_async_engine` + `async_sessionmaker` with `pool_pre_ping=True`, build URL from `DATABASE_URL` or `GUINEVERE_DB_PASSWORD` env vars, port 5433, `await engine.dispose()` in finally block, platform-aware signal handler.

### Verdict: **PASS**

### Evidence

| Check | Status | Location |
|---|---|---|
| `NotImplementedError` — 0 matches | PASS | `grep NotImplementedError` on `consumer.py` returned zero matches |
| `create_async_engine` used in `main()` | PASS | `consumer.py` line 310: `engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)` |
| `async_sessionmaker` with `class_=AsyncSession, expire_on_commit=False` | PASS | `consumer.py` lines 311-313: `async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)` |
| Port 5433 in connection URL | PASS | `consumer.py` line 305: `f"postgresql+asyncpg://guinevere:{db_password}@localhost:5433/guinevere"` |
| `await engine.dispose()` in finally block | PASS | `consumer.py` lines 340-341: `finally: await engine.dispose()` |
| Signal handler uses platform check | PASS | `consumer.py` lines 330-334: `if os.name != "nt":` adds signal handlers; `else:` logs warning — no `try/except NotImplementedError` |
| Fallback from `DATABASE_URL` to `GUINEVERE_DB_PASSWORD` | PASS | `consumer.py` lines 296-306: checks `DATABASE_URL` first, falls back to `GUINEVERE_DB_PASSWORD`, raises `RuntimeError` if neither set |

### Code snippet (consumer.py lines 293-341, key sections)

```python
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        db_password = os.environ.get("GUINEVERE_DB_PASSWORD", "")
        if not db_password:
            raise RuntimeError(
                "Neither DATABASE_URL nor GUINEVERE_DB_PASSWORD is set. "
                "The consumer requires a PostgreSQL connection to store events."
            )
        database_url = (
            f"postgresql+asyncpg://guinevere:{db_password}"
            f"@localhost:5433/guinevere"
        )

    engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    _session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False,
    )
```

```python
    if os.name != "nt":
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _on_signal)
    else:
        logger.warning("consumer_signal_handler_not_supported", os_name=os.name)

    try:
        await consumer.run()
    finally:
        await engine.dispose()
        logger.info("consumer_db_engine_disposed")
```

---

## Test Coverage — Buffer Push Tests

### Verdict: **PASS**

| Check | Status | Location |
|---|---|---|
| `TestBufferPush` class exists | PASS | `test_router.py` line 170: `class TestBufferPush:` |
| Test: `push_event` called with event data | PASS | `test_router.py` line 173: `test_push_event_called_with_event_data` — asserts `push_event.assert_called_once()`, validates `device_id`, `event_type`, `occurred_at`, `payload` |
| Test: 202 returned when push raises | PASS | `test_router.py` line 193: `test_202_returned_when_push_raises` — mocks `RuntimeError("Redis connection lost")`, asserts `response.status_code == 202` and `data["status"] == "accepted"` |
| Parametrized: push called for every event type | PASS | `test_router.py` line 207: `test_push_event_called_for_every_valid_event` — parametrized over all 12 valid event types |

---

## Summary

| Finding | Original Severity | Recheck Verdict |
|---|---|---|
| C1 — Router doesn't push events to Redis buffer | CRITICAL | **PASS** |
| C2 — `consumer.main()` raises `NotImplementedError` | CRITICAL | **PASS** |

### Overall Verdict: **PASS**

Both CRITICAL architecture findings from the D08 audit have been fully remediated. The pipeline entry point now correctly pushes validated events to the Redis DB2 buffer with best-effort semantics, and the consumer background worker has a working async database session factory with proper engine lifecycle management and cross-platform signal handling. Test coverage confirms both the happy path and failure resilience of the buffer push integration.

---

*Report generated 2026-06-03. Read-only audit — no source files modified.*
