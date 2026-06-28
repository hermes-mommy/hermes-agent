# P22 Brutal-Audit R1 Research — Discord + FastAPI

**Sub-agent**: research (READ-ONLY)
**Scope**: 4 findings (F01, F07, F26, F27) against CURRENT code
**Date**: 2026-06-28
**Method**: Direct file reads of `_entrypoint.py`, `_command_registry.py`, `cmd_integrations.py`, `cmd_consent.py`, `routes.py`, `main.py` plus targeted Grep searches across `src/`.

---

## Verdict Table

| Finding | Claim | Verdict | One-line Proof |
|---------|-------|---------|----------------|
| **F01** | Discord slash commands NOT REGISTERED in bot tree | **HOLDS** | `cmd_integrations` is NOT imported anywhere in `src/discord/_entrypoint.py` — confirmed by Grep; `_entrypoint.py:setup_hook` imports 35 callbacks (lines 169-208) but the 6 P22 `*_callback`s from `cmd_integrations.py` are absent; `COMMAND_SPECS` has 35 entries (asserted by `require_canonical_registry()`); adding 6 P22 commands would crash the count check at `_command_registry.py:296-297` (`if len(names) != 35: raise RuntimeError(f"expected 35 commands, found {len(names)}")`). |
| **F07** | No rate limiting on FastAPI endpoints | **HOLDS** | The ONLY middleware configured on the `app = FastAPI(...)` singleton at `src/core/main.py:695` is `app.add_middleware(_PrometheusMiddleware)` (defined at lines 677-693); Grep across `src/core/api/` for `slowapi|Limiter|rate_limit|RateLimit|throttle|add_middleware` returns zero hits; no 429 handling exists in `routes.py`; only `Depends(get_api_key)` (verified at `src/core/api/auth.py:31-54`, no per-key/IP throttle) gates the 5 mutation endpoints, leaving 5 read endpoints fully unauthenticated and unmetered. |
| **F26** | `consent_callback` name collision across cmd_consent.py and cmd_integrations.py | **HOLDS** | Grep `def consent_callback` across `src/discord/` returns exactly 2 hits: `src/discord/cmd_consent.py:67:async def consent_callback(...)` and `src/discord/cmd_integrations.py:451:async def consent_callback(...)` — both files define identically-named async coroutines with the same `(interaction: Any)` signature; collision is dormant because `cmd_integrations` is currently NOT imported by `_entrypoint.py` (only `cmd_consent.consent_callback` is bound at `_entrypoint.py:192`), but a future fix to F01 that imports `cmd_integrations` will create a name-collision landmine. |
| **F27** | Bare `except Exception` in cmd_integrations.py | **HOLDS** | Grep `except Exception` in `src/discord/cmd_integrations.py` returns single match at **line 130**: `except Exception as exc:  # noqa: BLE001 — boundary fall-through` — located inside the helper `_call_integrations_api(method, path, json_body, params)` (function defined at lines 83-136), wrapped around the `try` block at lines 105-115 containing `httpx.AsyncClient(...).request(...)` and `response.raise_for_status()` plus `response.json()`. The `# noqa: BLE001` comment is present, asserting intent, but the surrounding document comment at lines 96-101 explicitly notes "Failures are logged but never raised so the Discord callback can always render an embed" — i.e. the bare except is the deliberate boundary fall-through, contradicting AGENTS.md §5's "no bare except" rule. |

---

## F01 — Discord slash commands NOT REGISTERED in bot tree — HOLDS

### Evidence

**Grep — `cmd_integrations` imports in `_entrypoint.py`:**
- 0 hits. The only `cmd_*` imports under `# ── 20 Batch D Wired (RG-010..RG-014)` at lines 184-204 and `# ── 13 Original Wired` at lines 169-181 — no `cmd_integrations`.
- The Hermes Phase 1 imports at lines 206-207 likewise do not touch `cmd_integrations`.

**Commands registered into `GuinevereBot.tree` in `setup_hook`** (`_entrypoint.py:159-432`):
35 unique `self.tree.command(name="...")` invocations at the following line numbers (from Grep `^\s+name="`):

```
218 status          258 surveillance-status   304 approve          346 restart-service
223 mood            263 surveillance-pause    309 deny              351 backup-now
228 help            268 surveillance-resume   314 approve-all       356 health-check
233 safeword        273 cost                  319 focus             361 clear-cache
238 memory-search   278 budget                324 casual            368 loop-pause
243 memory-add      285 memory-forget         329 consent           373 loop-resume
248 loop-start      290 memory-export         334 punishment        378 loops
253 loop-stop       297 cost-alert            339 reward            383 evidence
                                                      388 loop-priority
                                                      395 new
                                                      400 history
```

PLUS a wrapper at lines 212-214:
```python
async def surveillance_status_command(interaction: object) -> None:
    """Slash-command adapter without test-only injection parameters."""
    await surveillance_status_callback(interaction)
```
which is the callback bound at line 258 above. No integration command names appear in this list (`integration-status`, `integration-capabilities`, `integration-test`, `integration-missing`, `integration-consent`, `integration-dry-run` are ALL absent).

**Stub loop** (lines 427-432):
```python
for spec in COMMAND_SPECS:
    if spec.name in core_names:
        continue  # Already wired above
    phase = _STUB_PHASE.get(spec.name, 4)
    cb = _make_stub_callback(spec.name, phase)
    self.tree.command(name=spec.name, description=spec.description, guild=discord.Object(id=GUILD_ID))(cb)
```
The `core_names` tuple (lines 406-426) is hard-coded to 35 entries — none of the 6 P22 integration names exist in `core_names`, AND none of the 6 are in `COMMAND_SPECS` either, so the stub loop would ALSO skip them (line 428: `if spec.name in core_names: continue` only skips, it does not auto-stub names that are absent from registry).

### `_command_registry.py` specifics

**`COMMAND_SPECS` (lines 130-253):**
- Grammar check: `powershell Select-String '^    CommandSpec\(' | Measure` returns **35**.
- Function `command_count()` at line 265: `return len(COMMAND_SPECS)`.
- `EXPECTED_COMMAND_NAMES` at line 255: tuple of all 35 names from specs.
- None of the 35 specs are P22 commands. The 6 P22 command names are not present anywhere in `COMMAND_SPECS` (verified by visual scan of lines 131-252).

**`require_canonical_registry()` (lines 292-307):**
```python
def require_canonical_registry() -> None:
    """Validate local command invariants before any Discord sync."""
    names = [spec.name for spec in COMMAND_SPECS]
    if len(names) != 35:
        raise RuntimeError(f"expected 35 commands, found {len(names)}")
    ...
```
- Asserts exactly 35 commands. Adding 6 P22 specs to `COMMAND_SPECS` would make the count 41 → RuntimeError on `setup_hook` boot.
- __FIX BUNDLED__: importing `cmd_integrations` AND wiring 6 commands requires bumping the count check from 35 → 41 (audit says 41; matches lines 411-413 of audit report).

### `cmd_integrations.py` callbacks (lines 176-647)

All 6 callbacks (audit-claimed names — confirming):

| Slash command (audit claim) | Function name | Line | Endpoint called |
|---------------------------|---------------|------|-----------------|
| `integration-status` | `status_callback` | **176** | `GET /api/v1/integrations/status` |
| `integration-capabilities` | `capabilities_callback` | **252** | `GET /api/v1/integrations/capabilities` |
| `integration-test` | `test_callback` | **319** | `POST /api/v1/integrations/test` |
| `integration-missing` | `missing_callback` | **379** | `GET /api/v1/integrations/missing` |
| `integration-consent` | `consent_callback` | **451** | `GET/POST /api/v1/integrations/consent` |
| `integration-dry-run` | `dry_run_callback` | **576** | `POST /api/v1/integrations/dry-run` |

Note: `cmd_integrations.py` is plain Python with **no `@app.command` or `@tree.command` decorators** — these are async coroutine functions registered externally by `_entrypoint.py:setup_hook`. The `__all__` at line 650-657 confirms the same 6 names. The audit's 6 P22 command name strings are the slash names (`integration-status` etc.) that would become `self.tree.command(name=...)` calls if wired.

### Contradiction audit

The audit claim — "Discord slash commands NOT REGISTERED in bot tree" — is **accurate**. The 6 P22 callbacks in `cmd_integrations.py` exist and have tests, but `_entrypoint.py` does not import `cmd_integrations`, has no `tree.command(name="integration-status", ...)`, and the `core_names` allowlist + `COMMAND_SPECS` registry are both frozen at 35 (not 41) — so they cannot be wired without code changes. From Discord's POV, the `/integration-*` slash commands do not exist on the live guild tree.

---

## F07 — No rate limiting on FastAPI endpoints — HOLDS

### Middleware configured

`src/core/main.py` (the active FastAPI app singleton):

```python
# line 645-649
app = FastAPI(
    title="Guinevere Core",
    version="0.1.0",
    lifespan=lifespan,
)

# line 677-693
class _PrometheusMiddleware(BaseHTTPMiddleware):
    """Track request count and duration for Prometheus."""
    ...
    async def dispatch(self, request: StarletteRequest, call_next: RequestResponseEndpoint) -> Response:
        method = request.method
        endpoint = request.url.path
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start
        _REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=str(response.status_code)).inc()
        _REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        return response

# line 695
app.add_middleware(_PrometheusMiddleware)
```

That is the **ONLY** `add_middleware` call in `main.py`. No `slowapi.Limiter`, no per-key throttle, no IP throttling, no custom rate-limit middleware.

**Grep verification** — slowapi/Limiter/rate_limit/throttle/search for `add_middleware` in `src/` returns 23.1KB output saved to `e58c40d4-c684-4db0-be4a-dbc03856caa2/tool-results/call_XwUDaMzG1UNS4E9Hn3lY8AmI.txt`. The only `add_middleware(...)` hit is `src\core\main.py:695:app.add_middleware(_PrometheusMiddleware)` — exactly 1 hit. All other matches are in unrelated modules (`whatsapp/metrics.py`, `gmail/commands/digest.py`, `gmail/client.py:163` returns `RateLimitError` on 429 but that's an upstream Gmail API response handler, not a Guinevere own-API throttle):

- `src/channels/whatsapp/metrics.py:34` — `WHATSAPP_RATE_LIMIT_HITS_TOTAL` (counter for WhatsApp inbound messages, not for the FastAPI app).
- `src/gmail/commands/digest.py:34` — `_RATE_LIMIT_MAX: int = 5` (per-user digest throttle, NOT the FastAPI app).
- `src/gmail/client.py:163` — `if status == 429: return RateLimitError(...)` (Gmail upstream handling).

**Grep on `src/core/api/`** (excluding unrelated modules): zero hits for `slowapi|Limiter|rate_limit|RateLimit|throttle|429|add_middleware`. Routes.py and main.py have no rate-limit middleware.

### Endpoints — auth matrix

`src/core/api/routes.py` — 7 P22 integration endpoints + 4 loop endpoints. Grep on `@(router|app).(get|post...)` returned 11 hits:

| # | Method | Path | Line | `Depends(get_api_key)` | Audit Says | Auth Verified |
|---|--------|------|------|----------------------|-----------|--------------|
| 1 | GET | `/api/v1/loops` | 150 | NO | n/a | NO AUTH |
| 2 | POST | `/api/v1/loops` | 165 | YES (line 169) | n/a | AUTH |
| 3 | GET | `/api/v1/loops/{id}` | 192 | NO | n/a | NO AUTH |
| 4 | POST | `/api/v1/loops/{id}/cancel` | 207 | YES (line 211) | n/a | AUTH |
| 5 | GET | `/api/v1/integrations/status` | 229 | NO | "NO AUTH" | **NO AUTH** |
| 6 | GET | `/api/v1/integrations/capabilities` | 301 | NO | "NO AUTH" | **NO AUTH** |
| 7 | POST | `/api/v1/integrations/test` | 345 | YES (line 349) | "AUTH" | **AUTH** |
| 8 | GET | `/api/v1/integrations/missing` | 423 | NO | "NO AUTH" | **NO AUTH** |
| 9 | GET | `/api/v1/integrations/consent` | 464 | NO | "NO AUTH" | **NO AUTH** |
| 10 | POST | `/api/v1/integrations/consent` | 496 | YES (line 500) | "AUTH" | **AUTH** |
| 11 | POST | `/api/v1/integrations/dry-run` | 583 | YES (line 587) | "AUTH" | **AUTH** |

The audit claims 7 P22 integration endpoints (5, 6, 7, 8, 9, 10, 11 above) which matches routes.py exactly. Auth pattern matches:
- READS no-auth (5, 6, 8, 9) — 4 of 7 P22 endpoints
- MUTATIONS auth-required (7, 10, 11) — 3 of 7 P22 endpoints
- The audit says "the `7 FastAPI endpoints (not 6)`" — confirmed exactly 7 P22 endpoints.

### 429 handling

**Zero** matches for `429` (HexException / rate-limit return code) in `routes.py` or `main.py`. The only `429` matches in `src/` are:
- `src/gmail/client.py:163` — Gmail upstream response handling
- `src/life_integrations/runtime.py` — possibly adapter-level
- The FastAPI app returns no 429 anywhere.

### Contradiction audit

The claim "No rate limiting on FastAPI endpoints" — **accurate**. Single-key (`Depends(get_api_key)` only — no per-key or per-IP throttle); ten of eleven routes (including all 4 read endpoints) allow unlimited polling. Recommended remediation: add `slowapi.Limiter` per-key/IP throttle OR a custom token-bucket middleware.

---

## F26 — `consent_callback` name collision — HOLDS

### Evidence

**Grep `def consent_callback` across `src/discord/`:**

```
src\discord\cmd_consent.py:67:async def consent_callback(interaction: Any) -> None:
src\discord\cmd_integrations.py:451:async def consent_callback(interaction: Any) -> None:
```

**Both** files define an identically-named async coroutine with the same signature.

### src/discord/cmd_consent.py (lines 67-169)

```python
async def consent_callback(interaction: Any) -> None:
    """Handle a ``/consent`` interaction."""
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        action_raw = get_option_value(interaction, "action")
        action = action_raw if action_raw and action_raw in VALID_ACTIONS else DEFAULT_ACTION
        ...
    except Exception:
        logger.exception("consent_callback_failed")
        await followup_send(
            interaction,
            content="⚠️ Consent manager is temporarily unavailable.",
        )
```

Bound to `/consent` slash command via `_entrypoint.py:329-332`:
```python
self.tree.command(
    name="consent",
    description="Show or update consent boundaries.",
    guild=discord.Object(id=GUILD_ID),
)(consent_callback)
```
(import at line 192: `from .cmd_consent import consent_callback`)

### src/discord/cmd_integrations.py (lines 451-570)

```python
async def consent_callback(interaction: Any) -> None:
    """Handle ``/integration-consent consent_action:str [scope:str]``.
    ...
    ``list``     → GET  ``/api/v1/integrations/consent``
    ``grant``    → POST ``/api/v1/integrations/consent``
    ``revoke``   → POST ``/api/v1/integrations/consent``
    """
```

Note: the function is callable as `consent_callback` but is NOT currently bound to any Slack-style `@tree.command` decorator — binding would happen in `_entrypoint.py:setup_hook` if F01 is fixed. Currently in the `__all__` export (lines 650-657) as `consent_callback` (NOT renamed).

### Collision semantics

- Currently a DORMANT landmine: `cmd_integrations` is not imported in `_entrypoint.py` so no namespace clash exists at runtime.
- Module-level: if a future file does `from .cmd_consent import consent_callback` AND `from .cmd_integrations import consent_callback` in the same scope, Python's later import shadow wins. In `_entrypoint.py:setup_hook` only the `cmd_consent` version is bound (line 192), so `cmd_integrations.consent_callback` would be silently dropped.
- Future fix of F01 must rename one of the two — best candidate is renaming `cmd_integrations.consent_callback` → `integration_consent_callback` (private prefix) so it doesn't break `__all__` consumers (only `cmd_integrations.__all__` exports it; not externally imported).

### Contradiction audit

The claim "`consent_callback` name collision across cmd_consent.py and cmd_integrations.py" — **accurate** as stated. The audit correctly notes it's a latent landmine, not a live collision.

---

## F27 — Bare `except Exception` in cmd_integrations.py — HOLDS

### Evidence

**Grep `except Exception` in `src/discord/cmd_integrations.py`:**

```
130:    except Exception as exc:  # noqa: BLE001 — boundary fall-through
```

Single match at line 130, inside the helper `_call_integrations_api(method, path, json_body, params)` (function signature at lines 83-88, docstring lines 89-101, body lines 102-136).

### Surrounding try block and context

```python
# ── HTTP Helper ─────────────────────────────────────────────────────────────

async def _call_integrations_api(
    method: str,
    path: str,
    json_body: dict[str, object] | None = None,
    params: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Call the integrations endpoint family on guinevere-core.
    ...
    Returns:
        Parsed JSON dict on success, ``None`` on any failure (network,
        status code, malformed JSON).  Failures are logged but never
        raised so the Discord callback can always render an embed.
    """
    url = f"{_API_BASE_URL}{_INTEGRATIONS_PREFIX}{path}"
    api_key = os.environ.get("GUINEVERE_API_KEY", "")
    headers = {"X-Guinevere-API-Key": api_key}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.request(
                method=method,
                url=url,
                json=json_body,
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:                       # line 116
        logger.warning(
            "integrations_api_http_error",
            path=path,
            status=exc.response.status_code,
        )
        return None
    except httpx.RequestError as exc:                           # line 123
        logger.warning(
            "integrations_api_request_failed",
            path=path,
            error=str(exc),
        )
        return None
    except Exception as exc:  # noqa: BLE001 — boundary fall-through   # line 130
        logger.exception(
            "integrations_api_unexpected_error",
            path=path,
            error=str(exc),
        )
        return None
```

### Function it's in

`_call_integrations_api` (lines 83-136).

### What the try block does

`httpx.AsyncClient` context manager → `client.request(method, url, json=..., params=..., headers=...)` → `response.raise_for_status()` (raises `httpx.HTTPStatusError` on 4xx/5xx) → `response.json()` (may raise `json.JSONDecodeError` or other on malformed payload).

### Surrounding logic

- Two specific exception handlers exist BEFORE the bare except:
  - `httpx.HTTPStatusError` (line 116-122): logs `integrations_api_http_error`, returns `None`.
  - `httpx.RequestError` (line 123-129): logs `integrations_api_request_failed`, returns `None`.
- The bare `except Exception` at line 130 (with `# noqa: BLE001`) is the catch-all for classes that escape the two specific handlers — e.g. `httpx.InvalidURL`, key errors, `json.JSONDecodeError`. It logs via `logger.exception(...)` (so includes traceback) and returns `None`.

### `# noqa` comment

Yes — `# noqa: BLE001 — boundary fall-through` is on line 130. This documents intent but does not justify the bare except from a strict-policy perspective. AGENTS.md §5 forbids bare `except`; the comment is asserting the boundary-fall-through exception to that rule. The function docstring at lines 96-101 reinforces: *"Failures are logged but never raised so the Discord callback can always render an embed"* — i.e. the always-render-embed contract justifies swallowing ANY exception and degrading to a fallback embed (`_send_unreachable_embed`).

The `noqa: BLE001` specifically suppresses ruff's `BLE001` (blind except) rule. This is a deliberate bypass — not an oversight.

### Contradiction audit

The claim "Bare `except Exception: # noqa: BLE001` in cmd_integrations.py:130" — **accurate**. The line number, the bare form, and the `# noqa: BLE001` annotation all match the audit's claim. The `noqa` comment is INTENTIONAL (boundary fall-through contract), not accidental — but the claim is still FACTUALLY correct: a bare except with a `# noqa` annotation is functionally equivalent to a bare except; ruff would flag it without the suppression. Defensible-by-design, but the audit's "bare except" identification is right.

---

## Cross-cutting observation (informational, NOT a finding)

`cmd_consent.consent_callback` (line 164) ALSO has a bare `except Exception`:
```python
except Exception:
    logger.exception("consent_callback_failed")
    await followup_send(...)
```
without `# noqa`. This is internal to the RG-012 RG and out of scope for F27 (which targeted `cmd_integrations.py:130`). Worth noting for completeness but does not contradict F27.

---

## File:line index for fix-prompt cross-reference

| Finding | File | Line(s) | What |
|---------|------|---------|------|
| F01 | `src/discord/_entrypoint.py` | 159-432 | `setup_hook` (no `cmd_integrations` import, no `tree.command` for `integration-*`) |
| F01 | `src/discord/_command_registry.py` | 130-253 | `COMMAND_SPECS` (35 entries, no P22 names) |
| F01 | `src/discord/_command_registry.py` | 296-297 | `require_canonical_registry` raises if count != 35 |
| F01 | `src/discord/cmd_integrations.py` | 176, 252, 319, 379, 451, 576 | 6 P22 callback definitions |
| F07 | `src/core/main.py` | 677-693, 695 | `_PrometheusMiddleware` + only `add_middleware` call |
| F07 | `src/core/api/auth.py` | 31-54 | `get_api_key` (no throttle, only HMAC compare) |
| F07 | `src/core/api/routes.py` | 150, 165, 192, 207, 229, 301, 345, 423, 464, 496, 583 | All 11 endpoints (P22 auth matrix above) |
| F26 | `src/discord/cmd_consent.py` | 67 | `async def consent_callback(interaction)` |
| F26 | `src/discord/cmd_integrations.py` | 451 | `async def consent_callback(interaction)` |
| F27 | `src/discord/cmd_integrations.py` | 130 | `except Exception as exc:  # noqa: BLE001 — boundary fall-through` |
| F27 | `src/discord/cmd_integrations.py` | 83-136 | `_call_integrations_api` function (try/except context) |

---

## Verdict Summary

All 4 findings (F01, F07, F26, F27) **HOLD** against current code. The brutal-audit-report.md (parent) line citations are substantially correct:

- **F01**: Exact — `cmd_integrations` not imported; 35-commands count check would crash if added.
- **F07**: Exact — only Prometheus middleware; no SlowAPI/Limiter/throttle; auth-only mutation gate (4 of 7 P22 endpoints unauthenticated and unmetered).
- **F26**: Exact — both files have `async def consent_callback(interaction: Any)` at lines 67 and 451 respectively.
- **F27**: Exact — line 130 in `_call_integrations_api`, with `# noqa: BLE001`, intentional but policy-non-compliant.

No contradictions found.
