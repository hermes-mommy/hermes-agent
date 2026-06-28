# R6 — registry / browser / x-poster ground-truth research

Date: 2026-06-28
Scope: read-only verification of three brutal-audit findings against current code.

## Per-finding verdict table

| #   | Finding                                       | Verdict     | Location                                                          | Notes                                                                             |
| --- | --------------------------------------------- | ----------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| F23 | Registry read race in `get()` / `list_all()`  | HOLDS       | `src/life_integrations/registry.py:117-156, 200-209`              | Reads are sync, do not acquire `_lock`; `self._adapters` mutation not serialised. |
| F20 | Browser adapter status drift (docs vs code)   | HOLDS (DOCS)| `src/life_integrations/adapters/browser_adapter.py:31-178`        | Code is honest config_missing-aware; documentation lag is the real defect.        |
| F10 | X Poster logs first 8 chars of access token   | HOLDS       | `src/x_poster/main.py:67`                                         | Token fragment `settings.x_access_token[:8] + "..."` emitted via `structlog`.    |

---

## F23 — Registry race condition in `get()` & `list_all()`

### Verdict: HOLDS

The audit's claim is accurate: write paths (`register`/`unregister`) are async and gated by `asyncio.Lock`, but the read paths (`get`, `list_all`, `list_by_capability`, `get_audit_summary`) are synchronous and do NOT acquire `self._lock`.

### Exact quotes

`src/life_integrations/registry.py:42-44` — storage + lock:

```python
self._adapters: dict[IntegrationId, BaseIntegrationAdapter] = {}
import asyncio
self._lock = asyncio.Lock()
```

`src/life_integrations/registry.py:82-100` — `register` (async, takes lock, lines 92-95):

```python
async def register(self, adapter: BaseIntegrationAdapter) -> None:
    ...
    integration_id = adapter.integration_id
    async with self._lock:
        if integration_id in self._adapters:
            raise ValueError(f"Integration '{integration_id}' already registered")
        self._adapters[integration_id] = adapter
    logger.info(...)
```

`src/life_integrations/registry.py:102-115` — `unregister` (async, takes lock, lines 111-114):

```python
async def unregister(self, integration_id: IntegrationId) -> None:
    ...
    async with self._lock:
        if integration_id not in self._adapters:
            raise KeyError(f"Integration '{integration_id}' not registered")
        del self._adapters[integration_id]
    logger.info("integration.unregistered", integration_id=integration_id)
```

`src/life_integrations/registry.py:117-131` — `get` (SYNC, no lock):

```python
def get(self, integration_id: IntegrationId) -> BaseIntegrationAdapter:
    """Get an adapter by integration ID."""
    ...
    if integration_id not in self._adapters:
        raise KeyError(f"Integration '{integration_id}' not registered")
    return self._adapters[integration_id]
```

`src/life_integrations/registry.py:133-139` — `list_all` (SYNC, no lock):

```python
def list_all(self) -> list[BaseIntegrationAdapter]:
    """Return all registered adapters."""
    ...
    return list(self._adapters.values())
```

`src/life_integrations/registry.py:141-156` — `list_by_capability` (SYNC, no lock):

```python
return [
    adapter
    for adapter in self._adapters.values()
    if adapter.has_capability(capability)
]
```

`src/life_integrations/registry.py:200-209` — `get_audit_summary` (SYNC, no lock):

```python
return {
    integration_id: adapter.get_audit_context()
    for integration_id, adapter in self._adapters.items()
}
```

Note the docstring on `src/life_integrations/registry.py:35-38` claims reads "take a snapshot under the lock" — but the actual implementations contradict this contract.

### Caller inventory — callers that would change if signatures went `async`

`registry.get(...)`:

| File:line                                  | Caller             | Context                                |
| ------------------------------------------ | ------------------ | -------------------------------------- |
| `src/life_integrations/router.py:122`      | `ActionRouter.execute`           | Production — caught via `try/except KeyError`. Result returned even if not registered. |
| `src/life_integrations/router.py:240`      | `ActionRouter.dry_run`           | Production — caught via `try/except KeyError`. Returns UNKNOWN tier. |

`registry.list_all(...)` (in production code, not tests/docs):

| File:line                                  | Caller             | Context                                |
| ------------------------------------------ | ------------------ | -------------------------------------- |
| `src/core/api/routes.py:255`               | `GET /api/v1/integrations/status` | Production — iterates to render status rows. |
| `src/core/api/routes.py:233`               | docstring only (no actual call here, calls `check_all_status`). | — |
| `scripts/p22_smoke_test.py:92-93`          | `--smoke` script    | Script — called synchronously.        |
| `docs/setup-evidence/P22/full-completion/research/user-facing-control-surface.md:298, 463, 867` | research notes | Documentation only, not executable. |

`registry.list_by_capability(...)`, `registry.get_audit_summary(...)`: NO callers in production code (no matches).

### Recommendation for the implementer

The fix that minimises blast radius is to keep signatures synchronous and snapshot the dict under the lock inside the read methods:

```python
def get(self, integration_id: IntegrationId) -> BaseIntegrationAdapter:
    # sync — caller cannot await; no lock acquisition possible here
    if integration_id not in self._adapters:           # race window here
        raise KeyError(...)
    return self._adapters[integration_id]
```

Two viable paths:

1. **Thread-safe snapshot** (recommended, no caller changes): replace `self._adapters.values()` and dictionary membership with a snapshot dict (`dict(self._adapters)`) taken under `self._lock` via a NEW async helper (e.g. `async def _snapshot() -> dict`). Reads stay sync, but each read first calls the helper. Cleaning this up requires either (a) making every caller async, which forces a wider ripple through `ActionRouter.execute` (line 122) and the `/api/v1/integrations/status` route (line 255), or (b) a `threading.Lock` (sync) instead of `asyncio.Lock` so readers can actually acquire it without `await`. The codebase is dual-async/`asyncio.run`-only at the entry point so `asyncio.Lock` is correct for writers but readers cannot `await` it without redirecting the call graph — meaning the lock provides no protection across the synchronous read path today.

2. **Switch to `threading.RLock` + keep signatures sync**: writers must `await self._lock` → drop async for register/unregister, which is a bigger blast radius than (1). NOT recommended.

Pragmatic outcome: the safer, scope-minimal fix is to add a NEW async `await self._snapshot()` helper and route critical reads (router.get → router._adapter_for) via it. Alternatively, document the contract that `register/unregister` must only be called on composition/first-init (the way `wiring.py:113` uses it), where there are no concurrent readers. Today that is the actual invariant — `wiring.build_default_registry()` is the sole caller of `register` and is awaited once during FastAPI startup before any read can fire.

### Contradiction

Class docstring promises "Async-safe via asyncio.Lock for register/unregister operations. Read operations (get/list) take a snapshot under the lock to avoid concurrent mutation races." (`src/life_integrations/registry.py:35-38`).
Reality: no reader acquires the lock; no snapshot helper exists. The class advertises a guarantee it does not enforce.

---

## F20 — Browser adapter status drift

### Verdict: HOLDS (documentation drift only; code behavior is honest)

### Current state of `BrowserIntegrationAdapter`

`src/life_integrations/adapters/browser_adapter.py:31-178`. The adapter is wired with three optional clients (`__init__`, lines 45-78):

```python
def __init__(
    self,
    search_client: Any | None = None,
    fetch_client: Any | None = None,
    browser_client: Any | None = None,
) -> None:
    """Initialize with optional search/fetch/browser clients.
    Args:
        search_client: Search tool wrapper (None = CONFIG_MISSING).
        fetch_client: Fetch tool wrapper (None = CONFIG_MISSING).
        browser_client: Obscura CDP wrapper (None = CONFIG_MISSING).
    """
    config = IntegrationConfig(
        integration_id="browser",
        ...
        secret_refs=("sec-brave-api", "sec-exa-api"),
```

### Health check (lines 80-84)

```python
async def health_check(self) -> IntegrationHealth:
    """Check browser/research connectivity."""
    if self._search is None and self._fetch is None and self._browser is None:
        return IntegrationHealth.UNKNOWN
    return IntegrationHealth.OK
```

Honest: returns `UNKNOWN` instead of faking `OK` when NO clients are provided.

### `search` action — CONFIG_MISSING path is HONEST (lines 96-120)

```python
if action_lower == "search":
    # L1 search — fail-closed-but-actionable. When no search client
    # (no BRAVE_API_KEY/EXA_API_KEY provisioned), return an HONEST
    # structured config_missing result instead of raising. The router
    # routes this to operator provisioning. Never fake success.
    if self._search is None:
        logger.info(
            "browser.config_missing",
            action=action,
            reason="BRAVE_API_KEY/EXA_API_KEY not provisioned",
        )
        return {
            "success": False,
            "config_missing": True,
            "reason": "BRAVE_API_KEY/EXA_API_KEY not provisioned",
            "action": action,
        }
```

### Required MCP shims (3 instances)

The audit's "3 MCP tools need instance shims" claim maps cleanly to the three constructor parameters of `BrowserIntegrationAdapter` (`search_client`, `fetch_client`, `browser_client`). These are the three bare MCP client instantiation paths the production wiring would need to wire:

1. `search_client` — would be a wrapper around `src/mcp/tools/brave_search.py` + `exa_search.py` + `websearch.py`. Currently the constructor expects a `.search(query)` coroutine; no adapter in `src/life_integrations/adapters/` produces one. → **needs instance shim**.
2. `fetch_client` — wrapper around `src/mcp/tools/fetch.py`. Expects `await fetch(url) -> str`. → **needs instance shim**.
3. `browser_client` — wrapper around `src/mcp/tools/obscura_cdp.py`. Expects `navigate(url)`, `fill_form(url, selector, value)`, `click(url, selector)`. → **needs instance shim**.

### Status reality check

- The adapter's L1 read code (`search`, `fetch_url`, `navigate`, `get_markdown`) returns a structured `config_missing=True` result rather than raising — i.e. `Oks (local)` claims from implementation reports are misleading: any production wiring without the 3 client shims surfaces `CONFIG_MISSING`.
- L2 write code (`fill_form`, `click`) **RAISES** `ConfigurationMissingError` ("never silently fake success", lines 144-147, 161-164). Code behavior is strict-fail-closed.
- Net: the audit's claim "production status = CONFIG_MISSING" is correct (no shims wired). Implementation report claims of "OK (local)" were probably passes with a dummy/in-process mock client, not the real MCP tool wrappers.

### Documentation drift

| Says                                                     | Reality                                                                                         |
| -------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Implementation report: "OK (local with mock client)"     | Code correctly returns `config_missing=True` / raises `ConfigurationMissingError` when real MCP clients absent. |
| Production activation report: `CONFIG_MISSING`           | Real wiring targets the 3 un-instantiated MCP shims. Code is honest; **docs disagreed with each other**. |

### Recommendation for implementer

Either (a) add real instance shims (Brave/Exa/Websearch wrappers, fetch wrapper, Obscura CDP wrapper) under `src/mcp/tools/` and wire them at `wiring.build_default_registry()` — then status flips to OK, OR (b) update implementation report to drop the "(local)" qualifier and adopt CONFIG_MISSING across both reports so docs match code.

---

## F10 — X Poster logs first 8 chars of access token

### Verdict: HOLDS

### Exact line — `src/x_poster/main.py:62-68`

```python
        await service.start()
        await health.start()
        logger.info(
            "x_poster.main_started",
            health_port=settings.health_port,
            metrics_port=settings.metrics_port,
            media_root=settings.media_root,
            x_access_token=settings.x_access_token[:8] + "..." if settings.x_access_token else "not_set",
        )
```

Specifically line 67:

```python
            x_access_token=settings.x_access_token[:8] + "..." if settings.x_access_token else "not_set",
```

### Function context

`_run()` (lines 32-83) is the asyncio service entry point. After `await service.start()` and `await health.start()`, it emits the `x_poster.main_started` event with the truncated token fragment in the `x_access_token` kwarg. The truncation operator precedence is correct (`A if B else C` evaluates fully), so the only logged values are the first 8 chars + "..." OR the literal "not_set" — no full token ever reaches this line.

### Logger configuration

It is `structlog.get_logger("x_poster.main")` (line 29), configured via `configure_xposter_logging(...)` at lines 36-41. The event "x_poster.main_started" writes via `logger.info(...)` to whatever log backend is configured (default: stdout/JSON line file per `log_output_path`). Severity is `INFO` — meaning EVERY successful startup of the x_poster process leaves the token prefix in the log stream.

### Severity

This is a **real but bounded leak**: 8 chars of an X API access token persistently surfaced in normal operational logs. With access tokens being ~50-character OAuth bearer strings, the prefix is enough to fingerprint a token and does not constitute full disclosure, but:

- Combined with timestamps and request counts in the same logfile, it provides a token fingerprint usable by any compromise of the log store.
- It violates the principle of "no secrets in logs" that AGENTS.md and the P22 audit framework both reference.
- Defaults to `not_set` if the token is empty/unset, so missing-config is obvious from logs.

### Recommendation for implementer

Redact the kwarg. Acceptable fixes (in order of preference):

1. Remove the `x_access_token` kwarg from the `x_poster.main_started` log entirely. Presence/absence can be inferred via a boolean flag: `x_access_token_present: bool(settings.x_access_token)`.
2. Replace with a hash/prefix length only: `x_access_token_prefix_len: len(settings.x_access_token) if settings.x_access_token else 0`.
3. If fingerprinting for ops debugging is desired, log only the SHA-256 fingerprint (first 6 hex chars) computed locally — never the raw token prefix.

Option (1) is the cleanest — the operational need for "is token set?" is the only signal readers actually use, and the `present: bool` form carries it without leaking the prefix.

---

## Cross-cutting summary

- F23 is a real concurrency bug masked by the current init-then-read lifecycle. The class docstring overstates the guarantee.
- F20 is documentation drift only — the code path is honest. Audit "CONFIG_MISSING" reflects that production wiring has no MCP shims; "OK (local)" implementation reports were probably mock-client passes.
- F10 is an actual leak (prefix of secret in INFO log); fix is one-line.

No code was edited during this research.
