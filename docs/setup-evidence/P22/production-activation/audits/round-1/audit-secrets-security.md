# P22 Production Activation — Audit Round 1: Secrets-Security

**Auditor**: independent auditor (Claude subagent)
**Date**: 2026-06-27
**Scope**: secrets-security dimension, P22 Runtime Wiring (commits `ec53f70`, `fdf6f33`)
**Verdict**: **PASS** (with one low-severity informational note)

---

## Verdict

**PASS**

The P22 production activation wiring obeys the SecretProvider pattern and leaks no
secrets to code, commits, logs, or runtime journal. Round 1 has no hard-rejection
criterion violated. Round 2 may proceed.

---

## Findings

| # | Severity | Title | Detail | Evidence |
|---|---|---|---|---|
| 1 | info | Audit detector regex strings appear in `src/life_integrations/audit.py` | `_VALUE_SECRET_PATTERNS` contains literal substrings `ghp_`, `sk-`, `ya29.`, `xox`, `AIza`, `BEGIN ... PRIVATE KEY`, `Bearer` for value-level redaction. These are NOT leaked credentials — they are documented detection patterns. Allowed per audit task brief ("audit.py detector regex is OK"). | `src/life_integrations/audit.py:120-126` |
| 2 | info | `runtime.py` reads `REDIS_URL` and `REDIS_PASSWORD` directly from env for SYNC HardStopShim | The runtime builds a SYNC redis client by reading `REDIS_URL`/`REDIS_PASSWORD` from env. Values are passed to `sync_redis_lib.Redis(password=_rpw or None, …)` for connection setup only; never logged or printed. Logger emits only the event key (`p22.hard_stop_shim.sync_redis_ready` / `sync_redis_failed`). This is an infrastructure connection param (not an adapter secret), but flagged for traceability. INFO-only — not a failure. | `src/life_integrations/runtime.py:209-227` |
| 3 | info | Adapter files use `secret_refs=("sec-…",)` ID-only references | All 14 adapter files reference secret IDs (e.g. `sec-github-pat`, `sec-discord-bot`, `sec-gmail-oauth`); none instantiate secrets themselves. The `SecretProvider` base class + `EnvSecretProvider` + `ProjectVaultSecretProvider` are defined in `secrets.py` and provide the abstraction. No raw `os.environ.get(...)` / `os.getenv(...)` exists in any adapter. Adapters only carry an integration_id and secret_refs tuple for downstream provider resolution. | `src/life_integrations/secrets.py`, `src/life_integrations/adapters/*.py` (14 files) |

No CRITICAL, HIGH, or MEDIUM findings.

---

## What Was Verified

### 1. Source code scan for plaintext secrets
- **Tool**: regex against `ghp_`, `sk-`, `ya29.`, `xox[bp]-`, `AIza[a-zA-Z0-9_-]{20,}`, `BEGIN ... PRIVATE KEY`, `Bearer ...`
- **Scope**: `src/life_integrations/` (runtime.py, _shims.py, audit.py, secrets.py, base.py, consent.py, errors.py, permissions.py, project_context.py, registry.py, router.py, scheduler.py, types.py, wiring.py, adapters/__init__.py plus all 14 adapters, adapters/_clients/__init__.py and memory_pipeline_shim.py) and `src/core/main.py`
- **Hits**: 2 — both inside `audit.py:120-135` regex string literals (the detector itself). **Zero plaintext secrets present.**

### 2. Commit content scan (ec53f70, fdf6f33)
- `git diff ec53f70~1..ec53f70 -- src/ alembic/ | grep -E "^\+" | grep -E "(ghp_|sk-|ya29\.|xox[bp]-|AIza[B...]|BEGIN .*PRIVATE KEY|Bearer ...)` → only `audit.py` regex strings, NOT secrets.
- `git diff fdf6f33~1..fdf6f33 -- src/ alembic/ | grep ...` → **zero matches**.
- `.env.core` values present in working tree are not staged into these commits (`.gitignore` already excludes `.env.*` since before ec53f70).

### 3. VPS journalctl scan
- `sudo journalctl -u guinevere-core --since "10 minutes ago" | grep -iE "(ghp_|sk-[A-Za-z0-9]{20,}|ya29\\.[A-Za-z0-9]+|xox[bp]-|AIza[A-Za-z0-9_-]{20,}|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY)"` → **zero matches**.
- Confirms runtime has not logged any token-shaped value during the activation window.

### 4. SecretProvider pattern compliance
- `src/life_integrations/secrets.py` defines `SecretProvider(ABC)` with `get_secret(secret_id, project_id=None)` and `has_secret(...)`. Two concrete providers: `EnvSecretProvider(mapping)` and `ProjectVaultSecretProvider(vault, fallback)`.
- **Raw env reads in `src/life_integrations/`**:
  - `runtime.py:209` — `REDIS_URL` (infra connection)
  - `runtime.py:210` — `REDIS_PASSWORD` (infra connection)
  - `secrets.py:93` — inside `EnvSecretProvider.get_secret` (the Provider itself, correctly localized)
  - Total adapter files with raw env: **0** (all 14 adapters).
- `grep -rEn "os.environ|os.getenv" src/life_integrations/adapters/` → zero hits.

### 5. Logger / print leakage check
- `grep -rEn "logger\.(error|info|warning).*(REDIS_PASSWORD|_rpw|_rurl|password.*value)"` → no value-leaking log calls.
- `grep -rEn "print.*(token|secret|password|api_key|REDIS_PASSWORD|_rpw|_rurl)"` → zero matches across `src/life_integrations/` and `src/core/main.py`.

### 6. Audit metadata redaction
- `audit.py:139-148` provides two-layer redaction:
  1. Key-name redaction (keys containing `token/password/secret/key/credential/auth` → `<redacted>`)
  2. Value-pattern redaction (string values matching token/PEM shapes → `<redacted:secret_in_value>`)
- Long-string truncation: `len(v) > 100` → `v[:50] + "…[truncated]"`. Prevents accidental value exposure in audit metadata.

### 7. Hard-coded env reads in adapter code
- All 14 adapter files (browser, calendar, discord, drive, filesystem, finance, github, gmail, memory, notion, telegram, vps, whatsapp) checked for `os.environ.get(...)` or `os.getenv(...)` — none found. Adapters are pure integration shells that accept hydrated clients.

---

## Hard-Rejection Check

| # | Criterion | Result |
|---|---|---|
| H1 | Plaintext secrets in adapter code (`ghp_/sk-/ya29./xox/AIza/BEGIN.*PRIVATE KEY`) | **PASS** — 0 hits |
| H2 | Adapter code reading env directly (`os.environ.get`/`os.getenv` in adapters/*) | **PASS** — 0 hits |
| H3 | Secret value in logged output (journalctl last 10 min) | **PASS** — 0 hits |
| H4 | Secret value in commit content (ec53f70, fdf6f33) | **PASS** — only audit.py regex notation |
| H5 | Fake "PASS" claim (no SecretProvider but claimed compliance) | **PASS** — `SecretProvider(ABC)` defined with `EnvSecretProvider`, `ProjectVaultSecretProvider` concrete implementations; `secrets.py` module shipped |
| H6 | Print/log of resolved secret values | **PASS** — `get_secret` consumers return values to caller; only the structured event keys are logged |
| H7 | `.env` values committed | **PASS** — `.env.*` excluded by `.gitignore` (status shows `M .gitignore` not `.env`); git diff for ec53f70/fdf6f33 contains zero env-shape content |

**No hard-rejection criterion violated.**

---

## Recommendations (for round 2 / future work, not required for round-1 PASS)

1. **Consider abstracting REDIS_PASSWORD in `runtime.py:210` through `SecretProvider`** so the runtime file itself contains zero raw env reads, even for infra. This is purely a portability hardening — current behavior does not leak the password.
2. **Set DEBUG redact-on by default** — `audit.py` already redacts metadata, but the long-string truncation kicks in at 100 chars. SopsSecrets migrating to a vault backend (`ProjectVaultSecretProvider`) later should default to no value-return in error paths.
3. **P24 fork convergence contract** — when migrating to owned fork per P24 plan, the SecretProvider interface is the carrier for fork-internal secret resolution. Recommend enshrining this in P22-FIX as a contract: adapters MUST not import `os` directly. A simple CI grep `grep -rn "os.environ" src/life_integrations/adapters/` should remain empty.
4. **Lifespan shutdown vs password logging** — confirm during round 2 that production main.py lifespan __aexit__ does not echo any client credentials when adapters are torn down.

---

## Conclusion

Secrets-security dimension is clean. Round-2 may proceed without re-audit on this dimension
unless new runtime wiring or new adapters are added.
