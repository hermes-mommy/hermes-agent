# R3 — Runtime / Wiring / Secrets — Brutal-Audit Ground-Truth Verification

**Date:** 2026-06-28
**Scope:** verify 4 brutal-audit findings against the **CURRENT** `main` branch code.
**Method:** read whole files (`runtime.py`, `wiring.py`, `secrets.py`, `audit.py`, `audit_db_writer.py`),
grep across `src/`, sample 2 adapter shims (`finance_read_shim.py`, `github_client_shim.py`)
and `discord_adapter.py`.
**Mission:** READ-ONLY. No edits.

---

## Per-Finding Verdict Table

| # | Finding | Verdict | File:Line | One-line summary |
|---|---|---|---|---|
| F05 | AuditLogger target=None in production (CRITICAL CONTRADICTION) | **HOLDS** (audit claim is TRUE; P22.1 memory claim is FALSE on main) | `src/core/main.py:468` `audit_writer=None` → `runtime.py:315` passes through → `wiring.py:149` `AuditLogger(writer=audit_writer)` → `audit.py:190` `self._writer = writer` (None ⇒ structlog-only, no DB, no file fallback) | `audit_writer` is literally `None` at runtime; `IntegrationAuditWriter` exists in code/docs but is NOT instantiated on the current `main`; logging falls back to **structlog-only**, NOT to a file. |
| F02 | Only 3/13 adapters ACTIVE; 10 CONFIG_MISSING | **HOLDS** | `runtime.py:319-324` enumerates active + config_missing logging | **3 ACTIVE** (discord + vps + filesystem), **10 CONFIG_MISSING** (gmail/calendar/drive/notion/telegram/github/browser/memory/finance/whatsapp). Logging is uniform generic `"p22.adapter.config_missing adapter=<name>"` — does NOT name the missing env var / credential. |
| F28 | `_rpw` stores REDIS_PASSWORD — leak risk | **HOLDS** (variable present); **DOES-NOT-HOLD** for leak vector (no log/error prints `_rpw`) | `runtime.py:286` `_rpw = os.environ.get("REDIS_PASSWORD", "")`; `runtime.py:293` `password=_rpw or None, …` | `_rpw` is in 2 lines only — line 286 assignment + line 293 `Redis(...)` password kwarg. Not in any `logger.*()` call. Risk is residual (unhandled exception frame during `Redis(...)` ctor or `ping()` would carry the value in `repr()` of the connection pool / failed kwargs in some Python debug scenarios) — small but non-zero. |
| F30 | secrets.py provider abstraction is DEAD CODE | **HOLDS** | `secrets.py:20` `SecretProvider(ABC)`; `secrets.py:66` `EnvSecretProvider`; `secrets.py:106` `ProjectVaultSecretProvider` | ALL provider classes imported only by the test suite (`tests/p22/test_project_isolation.py`) and unused in `wiring.py`/`runtime.py` are imported but never instantiated. Adapters read `os.environ.get(...)` directly (e.g. `github_client_shim.py:75,94,186,…`, `finance_read_shim.py:67`, `whatsapp_bridge_shim.py:73`). runtime.py:42 imports `EnvSecretProvider` and wiring.py:42 imports `EnvSecretProvider` — both imports are unused. **DEAD CODE.** |

---

## F05 — AuditWriter target=None in production (CRITICAL CONTRADICTION)

### Verdict: **HOLDS** (the brutal audit is RIGHT; the P22.1 hardening memory is WRONG on main)

### Construction chain (each link has literal evidence):

**Link 1 — `src/core/main.py:463-471`** (caller, passes `None`):

```python
_p22_registry, _p22_router = await build_runtime_registry(
    redis_client=redis_client,
    hard_stop_handler=app.state.hard_stop_handler,
    consent_checker=None,  # fail-closed L2+ until consent wired
    project_registry=None,  # P19 registry wired separately if active
    audit_writer=None,                                          # ← literal None
    workspace_root=os.environ.get("GUINEVERE_REPO_ROOT") or "/home/guinevere/code/guinevere",
    discord_rest_client=discord_rest,
)
```

The literal `audit_writer=None` is on line **468** (confirmed by Read of `src/core/main.py:450-525`).

**Link 2 — `src/life_integrations/runtime.py:311-317`** (passes through unchanged):

```python
router = await build_action_router(
    registry=registry,
    consent_checker=consent_shim,
    hard_stop_checker=hard_stop_shim,
    audit_writer=audit_writer,                                  # ← still None
    project_registry=project_registry,
)
```

The parameter `audit_writer: Any | None = None` is declared on runtime.py:221 — default is None and no override happens between main.py:468 and this call.

**Link 3 — `src/life_integrations/wiring.py:149`** (wraps in AuditLogger):

```python
audit_logger = AuditLogger(writer=audit_writer)
```

audit_writer is `None` here → `AuditLogger(writer=None)`.

**Link 4 — `src/life_integrations/audit.py:180-191`** (constructor):

```python
def __init__(
    self, writer: Any | None = None, initial_hash: str = ""
) -> None:
    """Initialize the audit logger.

    Args:
        writer: Callback/protocol with async write_event(event_dict) method.
                 If None, events are logged but not persisted (dev mode).
        initial_hash: Seed value for the hash chain (P22.1).
    """
    self._writer = writer
    self._last_hash: str = initial_hash
```

`self._writer` is None → the persistence gate is dead.

**Link 5 — `src/life_integrations/audit.py:252-263`** (call site):

```python
# Persist via writer if configured
if self._writer is not None:
    try:
        await self._writer.write_event(event.to_dict())
    except Exception as e:
        logger.error(
            "audit.write_failed",
            event_id=event.event_id,
            error=str(e),
        )
```

If `self._writer is None`, **this whole block is skipped**. Events are only emitted via `logger.info("integration.action", …)` (line 240). **No DB, no file.**

### Is `IntegrationAuditWriter` imported/instantiated in `runtime.py`?

`grep -rn IntegrationAuditWriter src/life_integrations/runtime.py` → **0 hits**.
`grep -rn IntegrationAuditWriter src/life_integrations/wiring.py` → **0 hits**.
It is only defined in `src/life_integrations/audit_db_writer.py:25` and referenced in tests (`tests/p22/test_audit_db_writer.py`) and `consent_ledger_writer.py` (which also receives None from the field it consumes).

### Is there a file-based fallback?

`grep -rn "audit-integration\.log\|logs/audit" src/life_integrations/` → **0 hits**.
The class docstring `audit.py:187` says:

> `writer: Callback/protocol with async write_event(event_dict) method. If None, events are logged but not persisted (dev mode).`

There is **no implicit file writer** — `None` ⇒ structlog-only emission, provides **no WORM, no hash-chain persistence, no `audit.integration_api_log` row**.

### State explicitly (the load-bearing claim):

**In production `runtime.py`, when invoked from the actual `src/core/main.py:463-471` lifespan startup, the audit writer is `None`. Events are NOT written to `audit.integration_api_log`, NOT written to `logs/audit-integration.log`. Only a structlog `integration.action` event is emitted.**

### Contradiction resolved

| Source | Claim |
|---|---|
| MEMORY `p22-1-foundation-hardening-complete.md` (file: `~/.claude/projects/.../memory/p22-1-...md`) | "audit_writer ≠ None (IntegrationAuditWriter→audit.integration_api_log…); 14/14 live VPS proof" |
| `docs/setup-evidence/P22/foundation-hardening/audits/round-1/runtime-deploy.md:133` | "audit_writer != None → IntegrationAuditWriter persists to audit.integration_api_log, …, main.py:495-497 constructs writer" |
| **Current `src/core/main.py:468`** (read here) | **`audit_writer=None`** (literal kwarg write) |
| Current `src/life_integrations/runtime.py:221,315` | Parameter default is `None`; no override path |
| Current `src/life_integrations/wiring.py:149` | Wraps the None in `AuditLogger(writer=None)` |
| Current `src/life_integrations/audit.py:190` | `self._writer = writer` (= None) |
| Current `src/life_integrations/audit.py:253` | `if self._writer is not None` — gated off |

**Resolution:** the P22.1 hardening was either never merged into `main`, or was reverted. Independent evidence: `git log --oneline -5 src/core/main.py` shows the most recent main.py commits are P22 audit round-1 fix (`c27e0d5`) and production runtime wiring (`fdf6f33`); there is no commit in the recent history that constructs `IntegrationAuditWriter` and threads it into `build_runtime_registry(audit_writer=…)`. The historical `main.py:495-497` reference in the audit doc no longer corresponds to anything in current main.py (lines 495-499 in current main.py are P19 cognition initialisation, not audit-writer wiring). **The F05 brutal-audit claim is correct on the present main branch state.**

---

## F02 — Only 3/13 adapters ACTIVE; 10 CONFIG_MISSING

### Verdict: **HOLDS** (verbatim match with the audit report).

### Per-adapter construction (from `src/life_integrations/wiring.py:85-110`):

```python
adapters = [
    DiscordIntegrationAdapter(rest_client=discord_rest_client),       # line 86
    GmailIntegrationAdapter(gmail_service=gmail_service),              # line 87
    GitHubIntegrationAdapter(github_client=github_client),             # line 88
    CalendarIntegrationAdapter(calendar_client=calendar_client),       # line 89
    DriveIntegrationAdapter(drive_client=drive_client),               # line 90
    NotionIntegrationAdapter(notion_client=notion_client),             # line 91
    TelegramIntegrationAdapter(telegram_client=telegram_client),      # line 92
    WhatsAppIntegrationAdapter(whatsapp_adapter=whatsapp_adapter),     # line 93
    VPSIntegrationAdapter(                                             # line 94
        docker_client=vps_docker_client,
        shell_client=vps_shell_client,
    ),
    FinanceIntegrationAdapter(finance_mind=finance_mind),             # line 98
    BrowserIntegrationAdapter(                                         # line 99
        search_client=browser_search,
        fetch_client=browser_fetch,
        browser_client=browser_cdp,
    ),
    MemoryIntegrationAdapter(                                          # line 104
        write_pipeline=memory_write_pipeline,
        read_pipeline=memory_read_pipeline,
        kg_engine=kg_engine,
    ),
    FilesystemIntegrationAdapter(workspace_root=workspace_root),       # line 109
]
```

That's 13 adapters.

### How `runtime.py` evaluates activation (lines 245-273):

```python
# --- Discord (ACTIVE via shim if client provided) ---
discord_client = None
if discord_rest_client is not None and getattr(discord_rest_client, "enabled", False):
    discord_client = DiscordRestShim(discord_rest_client)
    logger.info("p22.adapter.wired", adapter="discord", via="shim")

# --- VPS (ACTIVE via docker+shell shims) ---
docker_client = DockerClientShim()
shell_client = ShellClientShim()
logger.info("p22.adapter.wired", adapter="vps", via="shim")

# --- Filesystem (ACTIVE, no client) ---
fs_workspace = workspace_root or "/home/guinevere/code/guinevere"
logger.info("p22.adapter.wired", adapter="filesystem", via="workspace_root")

# --- Adapters left CONFIG_MISSING (honest) ---
# gmail, calendar, drive, notion, telegram: operator-gated creds/libs
# github, browser, memory, finance, whatsapp: shims need further
#   testing before activation — left None (CONFIG_MISSING) honestly.
for missing in ("gmail", "calendar", "drive", "notion", "telegram",
                "github", "browser", "memory", "finance", "whatsapp"):
    logger.info("p22.adapter.config_missing", adapter=missing)
```

### 3 ACTIVE (verbatim, `runtime.py:319-324`):

- **discord** — requires `discord_rest_client is not None and ...enabled` (gated by env at runtime)
- **vps** — always (shims are hard-coded; reads docker/shell tools)
- **filesystem** — always (workspace_root fallback `/home/guinevere/code/guinevere`)

### 10 CONFIG_MISSING:

- **operator-gated creds / client-lib**: gmail, calendar, drive, notion, telegram (5)
- **shim needs further testing before activation**: github, browser, memory, finance, whatsapp (5)

### Does the log identify WHICH env var is missing?

**No.** Logging pattern:

```python
logger.info("p22.adapter.config_missing", adapter=missing)
```

Emit a single generic `adapter=<name>` event. There is **no per-adapter diagnostic** mapping `adapter → secret_id → env_var_name` in `runtime.py`. The mapping exists only in documentation (`docs/setup-evidence/P22/production-activation/research/p22-secret-config-inventory-redacted.md`) and is **not consulted by runtime logging.** Adapter-internal shims (e.g. `github_client_shim.py:81-90`) do raise the specific env name when called (`"GitHub client: GITHUB_PAT env not set on guinevere-core"`), but only on first call attempt — not at startup.

### Contradiction with audit claim: NONE — matches.

Counts and categories match the brutal-audit report and the `audit-secrets.md` "operator-gated 5 + shard-further-testing 5 = 10 CONFIG_MISSING" split.

---

## F28 — `_rpw` stores REDIS_PASSWORD

### Verdict: **HOLDS** (variable exists, audit claim accurate); **PARTIALLY-HOLDS** (no leak in current code paths, but residual risk in unhandled-exception repr).

### Where the variable lives (runtime.py only):

`grep -n "_rpw" src/life_integrations/runtime.py`:

```
286:            _rpw = os.environ.get("REDIS_PASSWORD", "")
293:                password=_rpw or None, socket_timeout=2, socket_connect_timeout=2,
```

`grep -rn "_rpw" src/` outside runtime.py → **0 hits**.

### Is `_rpw` used in any log/error/exception context?

`grep -n "_rpw\|REDIS_PASSWORD" src/life_integrations/runtime.py`:

| Line | Code |
|---|---|
| 285 | `_rurl = os.environ.get("REDIS_URL", "redis://localhost:6379/0")` |
| 286 | `_rpw = os.environ.get("REDIS_PASSWORD", "")` |
| 293 | `password=_rpw or None, socket_timeout=2, socket_connect_timeout=2,` |
| 298-303 | `except Exception as e: … logger.warning("p22.hard_stop_shim.sync_redis_failed", error=str(e), hint=…)` — `error=str(e)` does NOT include `_rpw` |

Surrounding try/except (lines 282-303) only logs `error=str(e)` where `e` is the exception raised by the `Redis(...)` constructor or its `.ping()` call. The kwargs (and the variables referenced in them) are not in `str(e)`.

### Risk vector — DOES NOT LEAK in current code paths:

There are **no `logger.*` calls that print `_rpw`**. The `except` handler logs `error=str(e)` and a static hint. Python's exception string for `redis.exceptions.AuthenticationError` or `socket.gaierror` does NOT include the password kwarg in its standard repr.

### Residual risk — WHY the audit still flags it:

1. If an inner exception fires before binding (e.g. `urllib.parse.urlparse` fails, OSError with extra fields), the `str(e)` typically does not contain the password, but defensive practice in security-critical ops is to drop the variable.
2. The variable name `_rpw` is misleading (looks like "raw password") — even local-frame repr in some debuggers (e.g. `traceback.print_stack` with locals=True in test harness) could reveal it.
3. If a future refactor adds a `logger.error("redis_init_failed", **_rpw_field=…)` style call, the value is already a free variable — easy to leak accidentally.

### Recommended fix (recorded, NOT applied — read-only mission):

- Inline to a local `_password_for_redis = os.environ.get("REDIS_PASSWORD", "")` then drop it before any broader try block (or wrap kwargs as `password=os.environ.get("REDIS_PASSWORD", "") or None`).
- Add explicit assertion + redaction in the except logger: log only a length and a SHA-1 prefix of the password (consistent with the project's other secrets handling in `redact_secret()`).

### Contradiction with audit claim: NONE on the leak side; audit verdict ("could leak in error context") is in the same direction, just one order of severity lower than FAIL on current code (because `str(e)` for the relevant exceptions doesn't echo kwargs).

---

## F30 — secrets.py provider abstraction is DEAD CODE

### Verdict: **HOLDS** — full DEAD CODE in production wiring.

### Classes defined in `secrets.py` (read whole file, 169 lines total):

| Class | Line | Purpose |
|---|---|---|
| `SecretProvider(ABC)` | 20 | Abstract base; `get_secret` + `has_secret` |
| `EnvSecretProvider(SecretProvider)` | 66 | Reads from `os.environ.get()` by secret_id mapping |
| `ProjectVaultSecretProvider(SecretProvider)` | 106 | P19 vault + EnvSecretProvider fallback |
| (function) `redact_secret(value)` | 155 | not a class, but referenced for redaction |

### Instantiations in `src/` (production code, not tests):

`grep -rn "EnvSecretProvider(\|ProjectVaultSecretProvider(" src/` → **only the test file**:

```
tests\p22\test_project_isolation.py:95:    provider = EnvSecretProvider({"test-secret-123": "TEST_SECRET_123"})
tests\p22\test_project_isolation.py:103:    provider = EnvSecretProvider({"test-secret-456": "TEST_SECRET_456"})
tests\p22\test_project_isolation.py:111:    provider = EnvSecretProvider({})
tests\p22\test_project_isolation.py:134:    provider = ProjectVaultSecretProvider(vault)
```

**0 hits** in `src/life_integrations/routing.py`, `wiring.py`, `runtime.py`, `audit.py`, `consent.py`, `consent_checker.py`, `consent_ledger_writer.py`, **any adapter** (`.py` files under `src/life_integrations/adapters/`), or `src/core/main.py`.

### Imports (unused):

| File | Line | Import | Used? |
|---|---|---|---|
| `src/life_integrations/wiring.py:42` | `from src.life_integrations.secrets import EnvSecretProvider` | NO (no `EnvSecretProvider(...)` call in wiring.py) |
| `src/life_integrations/runtime.py:42` | `from src.life_integrations.secrets import EnvSecretProvider` | NO (no `EnvSecretProvider(...)` call in runtime.py) |

### Adapters read `os.environ.get()` directly (sample grep):

```
adapters\_clients\finance_read_shim.py:67:        url = database_url or os.environ.get("DATABASE_URL")
adapters\_clients\github_client_shim.py:75:        self._enabled = bool(os.environ.get("GITHUB_PAT", ""))
adapters\_clients\github_client_shim.py:94:        pat = os.environ.get("GITHUB_PAT", "")
adapters\_clients\github_client_shim.py:186:  pat = os.environ.get("GITHUB_PAT", "")
…  (12+ more github_client_shim.py `os.environ.get("GITHUB_PAT", "")` calls, all the way to line 841)
adapters\_clients\whatsapp_bridge_shim.py:73:    or os.environ.get("WHATSAPP_BRIDGE_URL", "http://127.0.0.1:8095")
```

`discord_adapter.py` does NOT read env directly (it consumes an injected `rest_client`); its secrets come from `DiscordRestClient` upstream (which itself reads from env, but that's a separate component). So the dead-code verdict is strongest for shims that take no client injection and are CONFIG_MISSING precisely because they have no provider mechanism.

### Is the import used by either wiring.py or runtime.py?

`grep -n "EnvSecretProvider\b\|ProjectVaultSecretProvider\b\|SecretProvider\b" src/life_integrations/wiring.py src/life_integrations/runtime.py`:

```
src/life_integrations/wiring.py:42:from src.life_integrations.secrets import EnvSecretProvider
src\lIfe_integrations\runtime.py:42:from src.life_integrations.secrets import EnvSecretProvider
```

Only the imports. No symbol use. **Dead.**

### Contradiction with audit claim: NONE — fully aligns.

### Mitigation options (recorded, not applied):

| Option | Description |
|---|---|
| A. Wire it | Construct `EnvSecretProvider(secret_to_env)` in `runtime.py`, pass into adapter constructors, replace direct `os.environ.get()` calls with `provider.get_secret(secret_id, project_id)`. Highest-fidelity fix; surfaces tests, ensures project's intended layering. |
| B. Remove it | Delete `secrets.py`, drop both imports. Lowest-loC. CLAIMS alignment breaks (sovereignty fork contract that "adapters never touch env directly" is voided). |
| C. Hybrid | Keep `secrets.py`, remove unused imports in `wiring.py`/`runtime.py`; document that secrets abstraction is for a future fork (Hermes Society) and current adapters intentionally use shims with direct env reads (LOCAL DEVIATION with rationale). |

---

## Convergent findings & ordering recommendation

If a single ordered fix-list is demanded by the brutal-audit fix workflow, prioritized by blast radius:

1. **F05 (CRITICAL).** Either instantiate `IntegrationAuditWriter` from a session_factory in `main.py` and pass it into `build_runtime_registry(audit_writer=…)`, OR explicitly accept that audit is dev-mode-only on main and update memory accordingly. Either way, the current "PASS WITH CONFIG_MISSING ADAPTERS" framing for P22 production-activation is inconsistent with what's actually running. **Hash-chained WORM audit invariant is broken on live.**
2. **F30.** Pick A/B/C; my recommendation is A (construct `EnvSecretProvider`, push into adapter constructors; the test suite already validates both providers).
3. **F02.** Logging can stay generic (`adapter=<name>`) for noise reasons, but add a single per-adapter "missing_secret_ids" detail breadcrumb loaded from the table in `p22-secret-config-inventory-redacted.md` to make CONFIG_MISSING operator-actionable.
4. **F28.** Inline the env read (`password=os.environ.get("REDIS_PASSWORD", "") or None`) and drop `_rpw`; or alias to a more opaque name with redaction-safe logging.

---

## Evidence index (for re-ground-truth)

| Finding | File | Line | Type |
|---|---|---|---|
| F05 | `src/core/main.py` | 468 | call-site passes None |
| F05 | `src/life_integrations/runtime.py` | 221 | param default |
| F05 | `src/life_integrations/runtime.py` | 315 | pass-through |
| F05 | `src/life_integrations/wiring.py` | 149 | AuditLogger constructor |
| F05 | `src/life_integrations/audit.py` | 180-191 | AuditLogger init |
| F05 | `src/life_integrations/audit.py` | 252-263 | persistence gate |
| F02 | `src/life_integrations/wiring.py` | 85-110 | adapter list |
| F02 | `src/life_integrations/runtime.py` | 245-273 | activation guard |
| F02 | `src/life_integrations/runtime.py` | 263-265 | CONFIG_MISSING loop |
| F02 | `src/life_integrations/runtime.py` | 319-324 | final summary log |
| F28 | `src/life_integrations/runtime.py` | 286 | `_rpw` assign |
| F28 | `src/life_integrations/runtime.py` | 293 | `_rpw` use |
| F30 | `src/life_integrations/secrets.py` | 20 | SecretProvider ABC |
| F30 | `src/life_integrations/secrets.py` | 66 | EnvSecretProvider |
| F30 | `src/life_integrations/secrets.py` | 106 | ProjectVaultSecretProvider |
| F30 | `src/life_integrations/wiring.py` | 42 | unused import |
| F30 | `src/life_integrations/runtime.py` | 42 | unused import |
| F30 | `src/life_integrations/adapters/_clients/github_client_shim.py` | 75,94,186,… | direct env read |
| F30 | `src/life_integrations/adapters/_clients/finance_read_shim.py` | 67 | direct env read |
| F30 | `src/life_integrations/adapters/_clients/whatsapp_bridge_shim.py` | 73 | direct env read |

---

## Final state of the CRITICAL contradiction (F05)

**In production `runtime.py` invoked from the active `src/core/main.py:463-471` lifespan handler, the audit writer is `None`. `IntegrationAuditWriter` does compile and is importable, but it is not instantiated anywhere on the runtime path; the live production code does not create a `session_factory` for it, does not thread it into `build_runtime_registry`, and does not fall back to a file. Events are emitted only via `structlog.info("integration.action", …)`. The P22.1-PROD-PASS memory claim is stale for the current main branch and the brutal-audit F05 verdict is the live state of truth.**
