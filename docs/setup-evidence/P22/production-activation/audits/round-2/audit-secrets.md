# P22 Production Activation — Audit Round 2 (FINAL GATE): Secrets-Security

**Auditor**: independent auditor (Claude subagent)
**Date**: 2026-06-28
**Scope**: secrets-security dimension, P22 Runtime Wiring (commits `ec53f70`, `fdf6f33`, `c27e0d5`)
**Round-1 verdict**: PASS (3 INFO notes — no HIGH/MEDIUM findings)
**Verdict**: **PASS**

---

## Verdict

**PASS** — secret hygiene dimension remains clean. All round-1 findings hold; no new
critical/high/medium regressions were introduced by the round-1 fix commit `c27e0d5`. The
SecretProvider pattern is correctly extended, the sync-redis HardStop path does not log
REDIS_PASSWORD values, the runtime-only env reads for `REDIS_URL` / `REDIS_PASSWORD` are
contained to `runtime.py:209-210`, the detector regex in `audit.py` is intentional and
documented, and live VPS journalctl shows zero secret-shaped values. Round-2 final gate
can pass.

---

## Round-1 Findings Resolution

Round-1 had **3 INFO** notes and **0 HIGH/MEDIUM** findings. The relevant claims to
re-verify are:

| R1 # | Title | Status | Evidence |
|---|---|---|---|
| R1-1 | `audit.py:120-126` detector regex literal substrings (`ghp_`, `sk-`, `ya29.`, `xox`, `AIza`, `BEGIN … PRIVATE KEY`, `Bearer`) — documented detection patterns, NOT leaked credentials | **RESOLVED — pattern unchanged, by design** | `src/life_integrations/audit.py:120-126` shows `_VALUE_SECRET_PATTERNS = _re.compile(r"(ghp_[a-zA-Z0-9]{20,}|sk-[a-zA-Z0-9]{20,}|ya29\.[a-zA-Z0-9]+|…")`. No round-2 commit modified these regexes. Grep across `src/life_integrations/` for live secret shapes: 0 matches outside the detector itself; 2 matches are exactly the regex literal (allowed). |
| R1-2 | `runtime.py:209-227` reads `REDIS_URL` + `REDIS_PASSWORD` directly from env for sync HardStop shim — connection params only, never logged | **RESOLVED — holds in round-2** | `runtime.py:215-218`: `sync_redis_lib.Redis(password=_rpw or None, …)` — value passed into client ctor only. Logger emissions at L220/L223 are `p22.hard_stop_shim.sync_redis_ready` / `p22.hard_stop_shim.sync_redis_failed` (event key only, value redacted). No print/log of `_rpw`. Grep across `src/life_integrations/` for `logger.(error|info|warning).*(password|REDIS_PASSWORD|_rpw|_rurl)`: 0 matches. |
| R1-3 | Adapter files use `secret_refs=("sec-…",)` ID-only references | **RESOLVED — confirmed for all 14 adapters** | Grep across `src/life_integrations/adapters/` for `password\|REDIS_PASSWORD\|api_key\|token` (case-insensitive): only `secret_refs=("sec-…")` ID strings + adapter-name docstrings — zero raw secrets, zero `os.environ.get(...)`, zero `os.getenv(...)` calls. |

Round-1 had **no HIGH/MEDIUM** findings — formally there is nothing to "fix". The
round-1-fix-log (`fixes/round-1-fix-log.md`) confirms that **all HIGH/MEDIUM findings
from other dimensions were addressed**; r1 secret dimension itself was PASS. Round-2
specifically verifies that the fix commit `c27e0d5` did not introduce any new secret
leakage.

### c27e0d5 Round-1 Fix Commit — Secret Hygiene Check

The fix commit `c27e0d5` (`fix(p22): audit round-1 fixes — HARD STOP regression test,
scheduler start, honest status`) modified:

- `src/core/main.py` — added scheduler.start() in lifespan (no secret read/write).
- `src/life_integrations/_shims.py` — added HardStopShim construction-time hard-fail
  for async redis + no handler (operational safety, no secret read).
- `src/life_integrations/adapters/discord_adapter.py`, `whatsapp_adapter.py` —
  replaced `__import__('datetime')` with top-level imports (forbidden pattern removal).
- `src/life_integrations/base.py` — `check_status` rewrite to map UNKNOWN→CONFIG_MISSING
  (status-mapping fix, no secret read).
- `src/life_integrations/project_context.py` — same `__import__` removal.
- `src/life_integrations/wiring.py` — corrected docstring (no code change for secrets).
- `tests/p22/test_shims.py` — new tests (no secrets involved).

Grep across the diff for added lines containing "password/secret/api_key/token/bearer":
**0 matches** for any secret-shaped content. Round-1 M2 forbidden-pattern removal is
the only secret-adjacent fix and is purely a stylistic change.

---

## New Findings

| # | Severity | Title | Detail | Evidence |
|---|---|---|---|---|
| 1 | info | `runtime.py:209-210` still reads `REDIS_URL` + `REDIS_PASSWORD` directly from env (in-tree infra connection) | This is the only raw-env-read site in `runtime.py`. The values are passed to `sync_redis_lib.Redis(…, password=_rpw or None, …)` (client ctor) and are NEVER logged/printed. Round-1 INFO R1-2 carried it forward. Recommendation (from r1) — abstract these via `SecretProvider` for portability — has NOT been applied, but it is a portability hardening, not a leak. **No new leak introduced.** | `src/life_integrations/runtime.py:209-210` |
| 2 | info | `src/core/main.py:20-21` aliases `9ROUTER_API_KEY` from `GUINEVERE_9ROUTER_API_KEY` at module import time | Pre-existing P20 alias mechanism. Both names refer to env-var keys, NOT to secret values. The OS env value is not logged. | `src/core/main.py:20-21` |
| 3 | info | `src/core/main.py:140-148` (surveillance consumer) reads `REDIS_PASSWORD` once at startup | Pre-existing P20 infrastructure, sets `password=_redis_password` (passed to aioredis client). No logging. | `src/core/main.py:140-148` |
| 4 | info | `src/core/main.py:401-403` reads `REDIS_PASSWORD` for life_kernel async redis client | Pre-existing P20 infrastructure, builds `_redis_url = f"redis://guinevere_core:{_redis_password}@localhost:6380/6"`. URL is passed to `aioredis.from_url(_redis_url)` but NOT logged. | `src/core/main.py:401-403` |
| 5 | info | `src/core/main.py:746-749` health handler has `os.environ.get("REDIS_URL", "redis://localhost:***@localhost:5433/guinevere_core")` — the default string contains an intentional placeholder `***` (NOT a real password) to avoid leaking the env var | The fallback already redacts the password slot by writing literal `***`. If env var is set, it is the operator's URL — passed to `aioredis.from_url` only, never printed into the response. | `src/core/main.py:746-749` |

**No CRITICAL, HIGH, or MEDIUM new findings.** Round-2 dimension remains clean.

---

## What Was Verified

### 1. Source code scan for plaintext secrets (round-2 re-scan)

- **Tool**: regex `ghp_[a-zA-Z0-9]{20,}|sk-[a-zA-Z0-9]{20,}|ya29\.[a-zA-Z0-9]+|xox[baprs]-[a-zA-Z0-9-]+|AIza[a-zA-Z0-9_-]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|Bearer\s+[a-zA-Z0-9._-]{20,}` (case-insensitive)
- **Scope**: `src/life_integrations/` (all 16 module files + `adapters/` subdir with 14 adapters + `_clients/` shims) and `src/core/main.py`
- **Hits**: 2 — both inside `src/life_integrations/audit.py:121` and `:135` as literal regex strings (the detector itself). **Zero plaintext secrets present.**

### 2. Logger + print leakage check

- `grep -rEn "logger\.(error|info|warning|debug).*(REDIS_PASSWORD|_rpw|_rurl|password.*value)" src/` → no value-leaking log calls.
- `grep -rEn "print.*(token|secret|password|api_key|REDIS_PASSWORD|_rpw|_rurl)" src/life_integrations src/core/main.py` → 0 value-printing matches.

### 3. Raw env reads audit

- `grep -rEn "os\.environ|os\.getenv" src/life_integrations/` → 3 hits total:
  - `runtime.py:209` — `REDIS_URL` (infra)
  - `runtime.py:210` — `REDIS_PASSWORD` (infra)
  - `secrets.py:93` — `EnvSecretProvider.get_secret` (correctly localized in provider)
- `grep -rEn "os\.environ|os\.getenv" src/life_integrations/adapters/` → **0 hits**. None of the 14 adapters read env directly.

### 4. Commit content scan (ec53f70, fdf6f33, c27e0d5)

- `git diff ec53f70~1..ec53f70 -- src/ alembic/ | grep "^+" | grep -E "(ghp_|sk-[A-Za-z0-9]|ya29\.|xox[bp]|AIza[a-zA-Z0-9_-]|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|Bearer )"` → 2 hits, both audit.py regex strings (round-1 deterministic — allowed).
- `git diff fdf6f33~1..fdf6f33 -- src/ alembic/ | grep "^+" | grep ...` → 0 matches.
- `git diff c27e0d5~1..c27e0d5 -- src/ | grep "^+" | grep ...` → 0 matches.
- `.env.core` excluded by `.gitignore` (line 28-29: `.env.*` and `*.env`); none of the three commits modify `.gitignore` to reintroduce an `.env*` allowlist; no `.env*` file appears in any of the three commits' `--name-only` output.

### 5. `.env` file commit check

- `git diff ec53f70~1..ec53f70 --name-only | grep '\.env'` → 0 matches.
- `git diff fdf6f33~1..fdf6f33 --name-only | grep '\.env'` → 0 matches.
- `git diff c27e0d5~1..c27e0d5 --name-only | grep '\.env'` → 0 matches.
- `cat .gitignore` confirms `.env.*` and `*.env` are ignored (`!.env.example` is the only exception). VPS-side `/home/guinevere/code/guinevere/.env.core` is present at mode `-rw-------` (mode 600, owned by user `guinevere`) which is the expected local-only secret file.

### 6. Live VPS journalctl scan — secret-shaped values

- `sudo journalctl -u guinevere-core --since '10 minutes ago' | grep -iE "(ghp_|sk-[A-Za-z0-9]{20,}|ya29\.[A-Za-z0-9_-]+|xox[bp]-?[A-Za-z0-9-]+|AIza[A-Za-z0-9_-]{20,}|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|Bearer [A-Za-z0-9_.-]+)"` → **0 matches**. Confirms runtime has not logged any token-shaped value in the activation window.
- `sudo journalctl -u guinevere-core --since '10 minutes ago' | grep -E "REDIS_PASSWORD|password="` → 0 matches.
- `sudo journalctl -u guinevere-core --since '10 minutes ago' | grep -E "p22\.|hard_stop"` → `p22.hard_stop_shim.sync_redis_ready` event present (event key only — confirms runtime.py:220 path executed live). No values, no error stack containing password.

### 7. Audit metadata redaction (still in place)

- `audit.py:120-126` — value-pattern regex unchanged.
- `audit.py:139-148` — two-layer redactor (key-name + value-pattern) unchanged.
- `audit.py:149-150` — long-string truncation `len(v) > 100 → f"<long:{len(v)}>"` unchanged.
- `secrets.py:155-168` — `redact_secret()` helper for safe repr (`first4****last4`, or `<redacted>` / `<none>`) unchanged.

### 8. Round-1 detected patterns independently reconfirmed

- All 14 adapter files: only `secret_refs=("sec-…")` ID-style references; no `os.environ`/`os.getenv`; no `GH_TOKEN`/`GITHUB_PAT`/`DISCORD_BOT_TOKEN` literals.
- The audit detector pattern `r"(ghp_[a-zA-Z0-9]{20,}|sk-[a-zA-Z0-9]{20,}|ya29\.[a-zA-Z0-9]+|…)"` is the only place those literal substrings appear in source code. By audit task brief ("audit.py detector regex is OK"). Confirmed unchanged in `c27e0d5`.

### 9. Round-1 INFO note R1-2 carried forward (no regression in c27e0d5)

- `runtime.py:209-227` (sync_redis env-reads) — still 4 lines, semantics unchanged:
  - `os.environ.get("REDIS_URL", "redis://localhost:6379/0")` → `_rurl`
  - `os.environ.get("REDIS_PASSWORD", "")` → `_rpw`
  - parsed host/port/db into localvars
  - `sync_redis_lib.Redis(host=…, port=…, db=…, password=_rpw or None, …)`
  - `sync_redis.ping()` then `logger.info("p22.hard_stop_shim.sync_redis_ready")` — emits event key only.
  - `except Exception as e:` branch emits `p22.hard_stop_shim.sync_redis_failed` with `error=str(e)` (no password).
- The fix commit `c27e0d5` did NOT modify `runtime.py`. Behaviour is identical between round-1 and round-2.

---

## Hard-Rejection Check

| # | Criterion | Result |
|---|---|---|
| H1 | Plaintext secrets in adapter code (`ghp_/sk-/ya29./xox/AIza/BEGIN.*PRIVATE KEY/Bearer`) | **PASS** — 0 hits across `src/life_integrations/` + `src/core/main.py`. The only `ghp_/sk-/ya29.` text is inside the `audit.py:121` *detector regex* (allowed). |
| H2 | Adapter code reading env directly (`os.environ.get`/`os.getenv` in adapters/*) | **PASS** — 0 hits. All 14 adapters use `secret_refs=("sec-…")` ID references exclusively. |
| H3 | Secret value in logged output (VPS journalctl last 10 min) | **PASS** — 0 matches for any secret shape; `REDIS_PASSWORD=…` substring absent; `p22.hard_stop_shim.sync_redis_ready` present (event key only, value not logged). |
| H4 | Secret value in commit content (`ec53f70`, `fdf6f33`, `c27e0d5`) | **PASS** — `c27e0d5` has 0 secret-shape changes; `fdf6f33` has 0; `ec53f70` has only audit.py regex notation. |
| H5 | Fake "PASS" claim (no SecretProvider but claimed compliance) | **PASS** — `SecretProvider(ABC)`, `EnvSecretProvider`, `ProjectVaultSecretProvider` all in place (`src/life_integrations/secrets.py`); `redact_secret()` helper available; audit two-layer redactor running on every action. |
| H6 | Print/log of resolved secret values | **PASS** — `get_secret` returns the value to the caller (intended authentication use only); `provider.get_secret(...)` results are never observed in any log call site. Confirmed by greps in §2. |
| H7 | `.env` values committed | **PASS** — none of the three commits stage any `.env*` file; `.gitignore` excludes `.env.*`/`*.env`; only `!.env.example` is allowlisted; no changes to the allowlist. |
| H8 | Round-1 fix commit `c27e0d5` introduces new secret leakage | **PASS** — diff grep for `^+(password|secret|api_key|token|bearer)` returns 0 substantive hits; the only added lines referencing those words are `__import__('datetime')` removal comments + adapter-name documentation (no values). |
| H9 | Adapter-level raw SECRET reads (env parsed + literal pasted) | **PASS** — adapters only have ID strings (`sec-…-token`, `sec-…-oauth`, `sec-…-pat`), not real secret values. |

**No hard-rejection criterion violated.**

---

## Recommendation

1. (Carry-forward R1-3.) When porting `runtime.py:209-210` to `SecretProvider`, the
   contract should keep REDIS_PASSWORD out of stdout. Currently no leak exists; this is a
   portability+auditability hardening, not a fix.
2. (Carry-forward R1-rec.) P24 fork convergence contract — keep the grep invariant
   `os.environ|os.getenv src/life_integrations/adapters/` returning empty across future
   integration phases. Round-2 confirms the invariant holds.
3. (Carry-forward post-P22 hardening.) When `ProjectVaultSecretProvider` becomes the
   production source (vs. the current `EnvSecretProvider` fallback), `redact_secret()`
   `secrets.py:155-168` is already in place; reuse it on any error-path log emissions.

---

## Conclusion

**PASS.** The secrets-security dimension is clean at round-2 final gate. All round-1
findings hold, with no new secret-shape leakage from the round-1 fix commit `c27e0d5`.
Live VPS state confirms no secret-shaped values have been emitted to journalctl over the
last 10 minutes; the `p22.hard_stop_shim.sync_redis_ready` event-key log is present
without a password value. Source code + commit content + adapter codebase + audit
detector regex all hold their round-1 contracts. P22 production activation can complete
its round-2 final gate on this dimension.
