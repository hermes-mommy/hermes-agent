# FastAPI HMAC Webhook Patterns — Production Reference

> Research report for Guinevere surveillance event receiver (`POST /surveillance/events`)
> Generated 2026-06-02 | Sources: FastAPI, Pydantic, redis-py, structlog, 10+ OSS codebases

---

## 1. Middleware vs Per-Endpoint HMAC Verification

### Recommendation: Per-Endpoint Dependency (NOT Middleware)

For a **single endpoint** (`POST /surveillance/events`), use a FastAPI dependency — not middleware.

**Why not middleware:**

| Factor | Middleware (`BaseHTTPMiddleware`) | Dependency (`Depends`) |
|--------|-----------------------------------|------------------------|
| Scope control | Applies to ALL routes unless filtered | Single route, explicit opt-in |
| Error propagation | Must catch internally or return 401 | Raises `HTTPException` — clean |
| Request body access | Requires `request.body()` — consumes stream | Can be done before model parse |
| Testing | Harder — must exercise full middleware stack | Trivial — call the callable |
| Performance | Extra hop in ASGI pipeline for every request | Only runs on target routes |

**Production evidence:**

The EverOS HMAC middleware
([source](https://github.com/EverMind-AI/EverOS/blob/afb8fab21e1778620b1d916513dec52d6d0f6d9a/methods/EverCore/src/core/middleware/hmac_signature_middleware.py#L54-L142))
applies HMAC verification as global middleware but adopts a "fail-soft" approach — failed verification does NOT block the request (line 120-121). This is because the middleware serves many endpoints with mixed auth. For single-endpoint, you want "fail-hard."

The ai-trading-agent
([source](https://github.com/flukelaster/ai-trading-agent/blob/e85c1861a0132c870df27b807afa6e9f26205c57/backend/app/api/routes/webhooks.py#L41-L90))
does per-endpoint verification inline — cleaner, explicit, and fails hard.

### Preferred Pattern: `Depends` callable

```python
import hmac
import hashlib
import time
from typing import Annotated
from fastapi import Depends, Header, HTTPException, Request, status

async def verify_hmac_signature(
    request: Request,
    x_signature: Annotated[str, Header(alias="X-Signature")],
    x_timestamp: Annotated[str, Header(alias="X-Timestamp")],
    x_nonce: Annotated[str, Header(alias="X-Nonce")],
    redis: Redis = Depends(get_redis),
) -> None:
    """HMAC-SHA256 verification with replay protection. Raises 401 on failure."""
    body = await request.body()

    # 1. Parse timestamp
    try:
        ts = int(x_timestamp)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid timestamp format")

    # 2. Time-window check (5 minutes)
    now = int(time.time())
    if abs(now - ts) > 300:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Request expired")

    # 3. Nonce replay check (atomic SET NX EX)
    nonce_key = f"nonce:{x_nonce}"
    if not await redis.set(nonce_key, "1", nx=True, ex=600):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Replay detected")

    # 4. Build signature data
    sig_data = f"{request.method}|{request.url.path}|{ts}|{x_nonce}|"
    sig_data_bytes = sig_data.encode() + body

    # 5. Constant-time comparison
    expected = hmac.new(
        SECRET_KEY.encode(), sig_data_bytes, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(x_signature, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid signature")


@app.post("/surveillance/events")
async def receive_event(
    payload: SurveillanceEvent,
    _: None = Depends(verify_hmac_signature),
):
    ...
```

**Key design choices:**

- **`request.body()` BEFORE model parse**: HMAC signs the raw bytes, not the parsed JSON. Read body once and store for both verification and parsing. (Use `request.state.raw_body` or re-read via FastAPI's cached body.)
- **Include body in signature string**: Unlike EverOS (`{METHOD}|{URL_PATH}|{TIMESTAMP}|{NONCE}` — line 259), include the body. This prevents tampering with the payload. The SimpleTuner pattern ([source](https://github.com/bghira/SimpleTuner/blob/main/simpletuner/simpletuner_sdk/server/routes/webhooks.py#L97)) appends raw body bytes: `f"{id}.{timestamp}.".encode() + body`.
- **`hmac.compare_digest`**: Mandatory for constant-time comparison to prevent timing attacks. Used by OpenAI ([source](https://github.com/openai/openai-python/blob/main/src/openai/resources/webhooks/webhooks.py#L112)), Sentry ([source](https://github.com/getsentry/sentry/blob/master/src/sentry/integrations/bitbucket/webhook.py#L49)), and OpenHands ([source](https://github.com/OpenHands/OpenHands/blob/main/enterprise/server/routes/integration/github.py#L48)).

---

## 2. Nonce Storage Patterns (Redis SET NX EX)

### Canonical Pattern: `SET key value NX EX ttl`

The industry-standard pattern for one-shot nonce tracking. Two excellent production examples:

**EverOS** ([source](https://github.com/EverMind-AI/EverOS/blob/afb8fab21e1778620b1d916513dec52d6d0f6d9a/methods/EverCore/src/core/middleware/hmac_signature_middleware.py#L203-L207)):
```python
nonce_key = f"nonce:{nonce_header}"
expire_seconds = self.time_window_seconds * 2  # 2× window for safety margin

nonce_stored = await self.redis_provider.set(
    nonce_key, str(request_timestamp), ex=expire_seconds, nx=True
)
if not nonce_stored:
    # Replay attack detected
    return False
```

**ai-trading-agent** ([source](https://github.com/flukelaster/ai-trading-agent/blob/e85c1861a0132c870df27b807afa6e9f26205c57/backend/app/api/routes/webhooks.py#L86-L90)):
```python
_WEBHOOK_NONCE_TTL_SECONDS = 300  # 5 minutes

redis_client = getattr(request.app.state, "redis", None)
if redis_client is not None:
    nonce_key = f"webhook:nonce:{alert.nonce}"
    if not await redis_client.set(nonce_key, "1", nx=True, ex=_WEBHOOK_NONCE_TTL_SECONDS):
        raise HTTPException(status_code=409, detail="replay detected")
```

**Why SET NX EX is correct:**

| Property | Why |
|----------|-----|
| `NX` | Atomic — only succeeds if key does not exist. No race condition between CHECK and SET. |
| `EX` | Auto-cleanup — no need for a cron job or manual deletion. |
| TTL = 2× window | EverOS uses `time_window * 2` (10 min for 5 min window). This tolerates clock skew. |
| Key namespace | `nonce:{value}` or `webhook:nonce:{value}` for easy scanning and debugging. |

**Avoid:** `GET` then `SET` (race condition), `SETEX` without `NX` (overwrites), in-memory dict (no horizontal scaling).

### TTL Selection Formula

```
nonce_ttl = time_window_seconds * 2 + clock_skew_buffer
```

- `time_window_seconds`: 300 (5 minutes)
- `clock_skew_buffer`: 60 (1 minute for client/server clock drift)
- **Result: ~660 seconds** — round to 600 (10 min) for simplicity.

### Failure Mode: Graceful Degradation

If Redis is unavailable, you have two choices:
- **Fail-closed** (default for surveillance security): raise 503 Service Unavailable.
- **Fail-open** (EverOS style, [source](https://github.com/EverMind-AI/EverOS/blob/afb8fab21e1778620b1d916513dec52d6d0f6d9a/methods/EverCore/src/core/middleware/hmac_signature_middleware.py#L227-L232)): log warning, skip nonce check. Only acceptable if signature+timestamp validation still blocks replays within the window.

---

## 3. Pydantic v2 Models — Strict Validation

### Pattern: `model_config = ConfigDict(extra="forbid", strict=True)`

For webhook payloads, you want **strict validation** — no silent type coercion, no ignored extra fields.

```python
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Literal

class SurveillanceEvent(BaseModel):
    model_config = ConfigDict(
        extra="forbid",      # Reject unknown fields
        strict=True,         # No type coercion (int "1" → 1 is rejected)
        frozen=True,         # Immutable after creation
    )

    event_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[a-f0-9-]{36}$",  # UUID v4 format
    )
    event_type: Literal[
        "screen_capture", "app_foreground", "location_update",
        "battery_status", "network_change", "heartbeat",
    ]
    device_id: str = Field(min_length=1, max_length=64)
    timestamp: datetime  # ISO 8601 with timezone
    payload: dict = Field(
        max_length=100,  # Max 100 KV pairs
    )
```

**Pydantic v2 key settings for webhooks:**

| Setting | Value | Why |
|---------|-------|-----|
| `extra` | `"forbid"` | Attackers inject unknown fields; reject them. |
| `strict` | `True` | Prevent type coercion — `"123"` must not become `123`. |
| `frozen` | `True` | Immutable data through the pipeline. |
| `str_strip_whitespace` | `True` | Auto-trim headers and string fields. |
| `validate_default` | `True` | Validate default values too. |

### Field-Level Constraints

```python
from pydantic import Field, field_validator
import uuid

# Regex pattern for nonce validation
nonce: str = Field(
    max_length=64,
    pattern=r"^[A-Za-z0-9_-]+$",
    description="Unique per-request token — rejected on replay",
)

# Custom validator for event_id
@field_validator("event_id")
@classmethod
def validate_uuid(cls, v: str) -> str:
    try:
        uuid.UUID(v)
    except ValueError:
        raise ValueError("event_id must be a valid UUID v4")
    return v

# Timestamp tolerance check (post-parse)
@field_validator("timestamp")
@classmethod
def validate_not_future(cls, v: datetime) -> datetime:
    from datetime import timezone
    now = datetime.now(timezone.utc)
    if v > now + timedelta(minutes=5):
        raise ValueError("timestamp cannot be more than 5 minutes in the future")
    return v
```

**Field validators run AFTER type validation**, so you have a clean `datetime` object to work with.

### Reference: ai-trading-agent Pydantic model

From [webhooks.py](https://github.com/flukelaster/ai-trading-agent/blob/e85c1861a0132c870df27b807afa6e9f26205c57/backend/app/api/routes/webhooks.py#L23-L34):

```python
class TradingViewAlert(BaseModel):
    symbol: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")
    action: str = Field(pattern=r"^(?i:BUY|SELL)$")
    price: float | None = None
    key: str = Field(min_length=8, max_length=256)
    timestamp: int | None = Field(None)
    nonce: str | None = Field(None, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
```

---

## 4. Error Handling — HTTP 401/403 Responses

### Status Code Decision Matrix for Webhook Auth

| Condition | Status | Detail | Headers |
|-----------|--------|--------|---------|
| Missing `X-Signature` header | 401 | "Missing signature header" | `WWW-Authenticate: HMAC-SHA256` |
| Invalid timestamp format | 400 | "Invalid timestamp format" | — |
| Expired timestamp (>5 min) | 401 | "Request expired" | — |
| Replay detected (nonce reuse) | 409 | "Replay detected" | — |
| Signature mismatch | 401 | "Invalid signature" | — |
| Malformed JSON body | 400 | `str(e)` (sanitized) | — |
| Unknown extra fields | 422 | Pydantic validation errors | — |
| Redis unavailable | 503 | "Service temporarily unavailable" | `Retry-After: 30` |

### Key distinctions:

- **401 vs 403**: `401` = authentication failed (bad signature, expired). `403` = authenticated but not authorized (wrong role). Most HMAC failures are 401 — the caller hasn't proven identity.
- **409 Conflict for replay**: Industry-standard for "you already sent this." See Stripe, GitHub webhooks.
- **400 vs 422**: 400 for parsing errors (timestamp not an int), 422 for Pydantic validation failures (FastAPI default).
- **503 for Redis down**: Fail-closed. Include `Retry-After` header so senders back off.

### Implementation pattern:

```python
from fastapi import status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI

app = FastAPI()

@app.exception_handler(HTTPException)
async def auth_exception_handler(request: Request, exc: HTTPException):
    """Ensure WWW-Authenticate header on 401s."""
    headers = getattr(exc, "headers", {}) or {}
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        headers.setdefault("WWW-Authenticate", 'HMAC-SHA256 realm="surveillance"')
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers,
    )
```

**Reference**: The `NOT_AUTHENTICATED` pattern from private-gpt
([source](https://github.com/zylon-ai/private-gpt/blob/main/private_gpt/server/utils/auth.py#L26-L30)):
```python
NOT_AUTHENTICATED = HTTPException(
    status_code=401,
    detail="Not authenticated",
    headers={"WWW-Authenticate": 'Basic realm="All the API", charset="UTF-8"'},
)
```

---

## 5. structlog Logging — Security Events

### Pattern: Contextual Bind + Key-Value Logging

structlog is the dominant choice in production FastAPI codebases for security logging. Used by Apache Airflow
([source](https://github.com/apache/airflow/blob/main/airflow-core/src/airflow/api_fastapi/auth/tokens.py#L43)),
Skyvern AI ([source](https://github.com/Skyvern-AI/skyvern/blob/main/skyvern/forge/sdk/routes/streaming/auth.py#L16)),
and Read the Docs ([source](https://github.com/readthedocs/readthedocs.org/blob/main/readthedocs/oauth/clients.py#L9)).

### Setup

```python
import structlog
from structlog.types import ProcessorReturn

logger = structlog.get_logger(__name__)

# Configure renderer
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if DEBUG else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

### Security Event Logging Patterns

```python
# 1. Auth failure — bind context, log once
async def verify_hmac_signature(...) -> None:
    log = logger.bind(
        client_ip=request.client.host if request.client else "unknown",
        endpoint="POST /surveillance/events",
        request_id=request.headers.get("X-Request-ID", ""),
    )

    # Missing header
    if not x_signature:
        log.warning(
            "hmac_auth_failure",
            reason="missing_signature",
            headers_present=[h for h in ["x-signature", "x-timestamp", "x-nonce"]
                            if h in request.headers],
        )
        raise HTTPException(status_code=401, detail="Missing signature header")

    # Replay detected
    if not await redis.set(nonce_key, "1", nx=True, ex=600):
        log.warning(
            "hmac_replay_detected",
            nonce=x_nonce[:8] + "...",  # Truncate for safety
            timestamp=x_timestamp,
        )
        raise HTTPException(status_code=409, detail="Replay detected")

    # Signature mismatch
    log.warning(
        "hmac_auth_failure",
        reason="signature_mismatch",
    )
```

### Don't Log Secrets

**Never log**: the raw secret key, full nonce values (truncate to first 8 chars), the full body of failed requests, or the expected signature (it leaks HMAC oracle info).

### Prometheus Metrics from structlog

Tie logs to metrics for alerting:

```python
from prometheus_client import Counter

HMAC_AUTH_FAILURES = Counter(
    "surveillance_hmac_auth_failures_total",
    "HMAC authentication failures",
    ["reason"],  # missing_signature, signature_mismatch, replay, expired
)

HMAC_REPLAY_ATTEMPTS = Counter(
    "surveillance_hmac_replay_attempts_total",
    "Replay attack attempts detected",
)
```

---

## 6. Redis List vs Stream — Event Buffering

### Decision: Redis Stream (`XADD`) for Event Buffering

| Feature | List (`LPUSH`/`RPOP`) | Stream (`XADD`/`XREAD`) |
|---------|----------------------|--------------------------|
| Append-only | Yes | Yes |
| Consumer groups | ❌ Manual coordination | ✅ `XREADGROUP` built-in |
| ACK/retry | ❌ Must implement | ✅ `XACK` with PEL |
| Max length capping | Manual `LTRIM` | ✅ `MAXLEN` built-in |
| Timestamp per entry | ❌ Must add yourself | ✅ Auto-generated ms IDs |
| Range queries | ❌ `LRANGE` only | ✅ `XRANGE`/`XREVRANGE` |
| Blocking read | `BLPOP` | `XREAD BLOCK` |
| TTL on stream | Manual `EXPIRE` | ✅ `PEXPIRE` via Lua |

### Stream Pattern

**Litestar's `XADD_EXPIRE` Lua script**
([source](https://github.com/litestar-org/litestar/blob/522a9c95bfee945bd9688ca96fa7254c3652231a/litestar/channels/backends/_redis_xadd_expire.lua)):

```lua
local data = ARGV[1]
local limit = ARGV[2]
local exp = ARGV[3]
local maxlen_approx = ARGV[4]

for i, key in ipairs(KEYS) do
    if maxlen_approx == 1 then
        redis.call("XADD", key, "MAXLEN", "~", limit, "*",
                    "data", data, "channel", ARGV[i + 4])
    else
        redis.call("XADD", key, "MAXLEN", limit, "*",
                    "data", data, "channel", ARGV[i + 4])
    end
    redis.call("PEXPIRE", key, exp)
end
```

This atomically: (1) adds entry with MAXLEN cap, (2) sets PEXPIRE for auto-cleanup. Lightweight and safe — no orphaned streams.

### Recommended Implementation for Surveillance Events

```python
import json
from redis.asyncio import Redis

SURVEILLANCE_STREAM = "surveillance:events"
STREAM_MAXLEN = 10_000          # Max entries
STREAM_TTL_MS = 3600_000        # 1 hour TTL (vs your 5-min raw, use longer)

async def buffer_event(redis: Redis, event: SurveillanceEvent) -> str:
    """Buffer an event into the Redis stream for async processing."""
    payload = event.model_dump_json()

    # XADD with MAXLEN cap
    entry_id = await redis.xadd(
        SURVEILLANCE_STREAM,
        {
            "event_type": event.event_type,
            "device_id": event.device_id,
            "payload": payload,
            "received_at": str(int(time.time() * 1000)),
        },
        maxlen=STREAM_MAXLEN,
        approximate=True,  # ~MAXLEN for performance
    )

    # Set TTL on the stream key itself
    await redis.pexpire(SURVEILLANCE_STREAM, STREAM_TTL_MS)

    return entry_id.decode() if isinstance(entry_id, bytes) else entry_id
```

**Why `approximate=True`**: `~MAXLEN` tells Redis to trim in blocks rather than exactly. Massively reduces overhead at high throughput. Used by AutoGPT ([source](https://github.com/Significant-Gravitas/AutoGPT/blob/master/autogpt_platform/backend/backend/copilot/stream_registry.py#L296)), DocsGPT ([source](https://github.com/arc53/DocsGPT/blob/main/application/events/publisher.py#L103)), and OpenSail ([source](https://github.com/TesslateAI/OpenSail/blob/main/orchestrator/app/services/gateway/delivery_client.py#L73)).

### Consumer Pattern

```python
CONSUMER_GROUP = "surveillance-processors"
CONSUMER_NAME = f"processor-{socket.gethostname()}"

async def setup_consumer_group(redis: Redis):
    """Idempotent consumer group creation."""
    try:
        await redis.xgroup_create(
            SURVEILLANCE_STREAM, CONSUMER_GROUP, id="0", mkstream=True,
        )
    except ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

async def process_events(redis: Redis):
    """Read pending + new events from the stream."""
    while True:
        # 1. Claim any pending (unacked) messages first
        pending = await redis.xpending_range(
            SURVEILLANCE_STREAM, CONSUMER_GROUP, min="-", max="+", count=10,
        )
        for entry in pending:
            messages = await redis.xrange(
                SURVEILLANCE_STREAM, min=entry["entry_id"], max=entry["entry_id"],
            )
            for msg_id, fields in messages:
                await handle_surveillance_event(fields)
                await redis.xack(SURVEILLANCE_STREAM, CONSUMER_GROUP, msg_id)

        # 2. Read new messages
        results = await redis.xreadgroup(
            CONSUMER_GROUP, CONSUMER_NAME,
            {SURVEILLANCE_STREAM: ">"},  # ">" = new messages only
            count=10, block=5000,
        )
        if results:
            for stream_name, messages in results:
                for msg_id, fields in messages:
                    await handle_surveillance_event(fields)
                    await redis.xack(SURVEILLANCE_STREAM, CONSUMER_GROUP, msg_id)
```

### Alternative: Redis List (Simpler, for single-consumer)

If you don't need consumer groups or horizontal scaling, a Redis List with LPUSH+LTRIM+EXPIRE is simpler. Saleor's `RedisBuffer` pattern
([source](https://github.com/saleor/saleor/blob/fc0bf5215a47bf44dcba93932c1b366e114e051d/saleor/webhook/observability/buffers.py#L118-L128)):

```python
def _put_events(self, key, events, client=None):
    start_index = -self.max_size
    events_data = [self.encode(event) for event in events[start_index:]]
    client.lpush(key, *events_data)
    client.ltrim(key, 0, max(0, self.max_size - 1))
    client.expire(key, self.timeout)
    return max(0, len(events) - self.max_size)
```

This does three operations atomically (in a pipeline): `LPUSH` → `LTRIM` (cap) → `EXPIRE`. Simple, battle-tested.

### When to use List vs Stream

| Scenario | Use |
|----------|-----|
| Single consumer, ordered FIFO | **List** (`LPUSH`/`RPOP`) |
| Multiple consumers, at-least-once | **Stream** (`XREADGROUP`) |
| Replay/delay/retry logic needed | **Stream** (PEL tracks unacked) |
| Simple burst buffer, fire-and-forget | **List** |
| Need to query by time range | **Stream** (`XRANGE`) |

For Guinevere's surveillance events, **Stream** is the better choice — the consumer group abstraction lets you add more processors later without changing the producer.

---

## Complete Endpoint Skeleton

Bringing all patterns together:

```python
# routes/surveillance.py
import hmac
import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from redis.asyncio import Redis
from prometheus_client import Counter

router = APIRouter(prefix="/surveillance", tags=["surveillance"])
logger = structlog.get_logger(__name__)

# --- Metrics ---
HMAC_FAILURES = Counter("surv_hmac_failures", "HMAC auth failures", ["reason"])
REPLAY_DETECTED = Counter("surv_replay_total", "Replay attempts detected")

# --- Config ---
HMAC_SECRET = secrets.token_hex(32)  # Load from env/SOPS
TIME_WINDOW_SECONDS = 300
NONCE_TTL_SECONDS = 660
STREAM_MAXLEN = 10_000
STREAM_TTL_MS = 3_600_000

# --- Models ---
class SurveillanceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    event_id: str = Field(min_length=36, max_length=36)
    event_type: Literal[
        "screen_capture", "app_foreground", "location_update",
        "battery_status", "network_change", "heartbeat",
    ]
    device_id: str = Field(min_length=1, max_length=64)
    timestamp: datetime
    payload: dict

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        import uuid
        try: uuid.UUID(v); return v
        except ValueError: raise ValueError("Invalid UUID")

    @field_validator("timestamp")
    @classmethod
    def not_too_future(cls, v: datetime) -> datetime:
        if v > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("Future timestamp")
        return v


# --- HMAC Dependency ---
async def verify_hmac(
    request: Request,
    x_signature: Annotated[str, Header(alias="X-Signature")],
    x_timestamp: Annotated[str, Header(alias="X-Timestamp")],
    x_nonce: Annotated[str, Header(alias="X-Nonce")],
    redis: Redis = Depends(get_redis),
) -> None:
    log = logger.bind(
        ip=request.client.host if request.client else "unknown",
        endpoint=f"{request.method} {request.url.path}",
    )

    # Parse timestamp
    try:
        ts = int(x_timestamp)
    except ValueError:
        log.warning("hmac_auth_failure", reason="bad_timestamp")
        HMAC_FAILURES.labels(reason="bad_timestamp").inc()
        raise HTTPException(status_code=400, detail="Invalid timestamp")

    # Time window
    if abs(int(time.time()) - ts) > TIME_WINDOW_SECONDS:
        log.warning("hmac_auth_failure", reason="expired")
        HMAC_FAILURES.labels(reason="expired").inc()
        raise HTTPException(status_code=401, detail="Request expired")

    # Nonce replay
    nonce_key = f"nonce:{x_nonce}"
    if not await redis.set(nonce_key, "1", nx=True, ex=NONCE_TTL_SECONDS):
        log.warning("hmac_replay", nonce=x_nonce[:8])
        REPLAY_DETECTED.inc()
        raise HTTPException(status_code=409, detail="Replay detected")

    # Signature
    body = await request.body()
    sig_data = f"{request.method}|{request.url.path}|{ts}|{x_nonce}|"
    expected = hmac.new(HMAC_SECRET.encode(), sig_data.encode() + body, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(x_signature, expected):
        log.warning("hmac_auth_failure", reason="bad_signature")
        HMAC_FAILURES.labels(reason="bad_signature").inc()
        raise HTTPException(status_code=401, detail="Invalid signature")


# --- Endpoint ---
@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def receive_surveillance_event(
    event: SurveillanceEvent,
    request: Request,
    redis: Redis = Depends(get_redis),
    _: None = Depends(verify_hmac),
):
    """Receive a surveillance event. Buffered to Redis Stream for async processing."""

    entry_id = await redis.xadd(
        "surveillance:events",
        {
            "event_type": event.event_type,
            "device_id": event.device_id,
            "payload": event.model_dump_json(),
            "received_at": str(int(time.time() * 1000)),
        },
        maxlen=STREAM_MAXLEN,
        approximate=True,
    )
    await redis.pexpire("surveillance:events", STREAM_TTL_MS)

    logger.info("event_received",
                event_type=event.event_type,
                device_id=event.device_id,
                stream_id=entry_id.decode() if isinstance(entry_id, bytes) else entry_id)

    return {"status": "accepted", "event_id": event.event_id}
```

---

## Source Index

| Pattern | Source | SHA / Line |
|---------|--------|------------|
| HMAC middleware with nonce | EverMind-AI/EverOS | [`afb8fab` L203-L207](https://github.com/EverMind-AI/EverOS/blob/afb8fab21e1778620b1d916513dec52d6d0f6d9a/methods/EverCore/src/core/middleware/hmac_signature_middleware.py#L203-L207) |
| HMAC middleware full verify | EverMind-AI/EverOS | [`afb8fab` L144-L285](https://github.com/EverMind-AI/EverOS/blob/afb8fab21e1778620b1d916513dec52d6d0f6d9a/methods/EverCore/src/core/middleware/hmac_signature_middleware.py#L144-L285) |
| Per-endpoint webhook HMAC | flukelaster/ai-trading-agent | [`e85c186` L41-L90](https://github.com/flukelaster/ai-trading-agent/blob/e85c1861a0132c870df27b807afa6e9f26205c57/backend/app/api/routes/webhooks.py#L41-L90) |
| `hmac.compare_digest` in webhooks | OpenHands | [GitHub events L48](https://github.com/OpenHands/OpenHands/blob/main/enterprise/server/routes/integration/github.py#L48) |
| `hmac.compare_digest` in SDK | openai/openai-python | [webhooks.py L112](https://github.com/openai/openai-python/blob/main/src/openai/resources/webhooks/webhooks.py#L112) |
| Body-included HMAC signature | SimpleTuner | [webhooks.py L97](https://github.com/bghira/SimpleTuner/blob/main/simpletuner/simpletuner_sdk/server/routes/webhooks.py#L97) |
| `NOT_AUTHENTICATED` header pattern | private-gpt | [auth.py L26-L30](https://github.com/zylon-ai/private-gpt/blob/main/private_gpt/server/utils/auth.py#L26-L30) |
| structlog in auth | Apache Airflow | [tokens.py L43](https://github.com/apache/airflow/blob/main/airflow-core/src/airflow/api_fastapi/auth/tokens.py#L43) |
| structlog in auth | Skyvern AI | [org_auth_token_service.py L9](https://github.com/Skyvern-AI/skyvern/blob/main/skyvern/forge/sdk/services/org_auth_token_service.py#L9) |
| Redis SET NX EX nonce | RuoYi-Vue3-FastAPI | [transport_crypto_util.py L323](https://github.com/insistence/RuoYi-Vue3-FastAPI/blob/master/ruoyi-fastapi-backend/utils/transport_crypto_util.py#L323) |
| Redis List buffer (LPUSH+LTRIM+EXPIRE) | saleor/saleor | [`fc0bf52` L118-L128](https://github.com/saleor/saleor/blob/fc0bf5215a47bf44dcba93932c1b366e114e051d/saleor/webhook/observability/buffers.py#L118-L128) |
| Redis Stream XADD+MAXLEN | AutoGPT | [stream_registry.py L296](https://github.com/Significant-Gravitas/AutoGPT/blob/master/autogpt_platform/backend/backend/copilot/stream_registry.py#L296) |
| Redis Stream XADD+PEXPIRE Lua | litestar-org/litestar | [`522a9c9` L1-L13](https://github.com/litestar-org/litestar/blob/522a9c95bfee945bd9688ca96fa7254c3652231a/litestar/channels/backends/_redis_xadd_expire.lua#L1-L13) |
| Redis Stream consumer group | DocsGPT | [publisher.py L103](https://github.com/arc53/DocsGPT/blob/main/application/events/publisher.py#L103) |
| Pydantic v2 ConfigDict | pydantic/pydantic | [config.py L72](https://github.com/pydantic/pydantic/blob/main/pydantic/config.py#L72) |