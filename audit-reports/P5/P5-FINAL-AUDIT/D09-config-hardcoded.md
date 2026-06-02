# D09 — Config & Hardcoded Values Audit

| Field | Value |
|---|---|
| **Audit ID** | P5-FINAL-AUDIT / D09 |
| **Scope** | All P5 Agent Loop files + related API, Discord, and systemd files |
| **Auditor** | Independent Config Auditor |
| **Date** | 2026-06-02 |
| **Verdict** | **NEEDS REVIEW** |

---

## 1. Files Scanned

| # | File | Lines |
|---|---|---|
| 1 | `src/loops/manager.py` | 272 |
| 2 | `src/loops/guardian.py` | 157 |
| 3 | `src/loops/enforcer.py` | 132 |
| 4 | `src/loops/cost.py` | 194 |
| 5 | `src/loops/scheduler.py` | 175 |
| 6 | `src/loops/verify.py` | 183 |
| 7 | `src/loops/artifacts.py` | 110 |
| 8 | `src/loops/evidence.py` | 194 |
| 9 | `src/core/api/auth.py` | 62 |
| 10 | `src/core/api/routes.py` | 90 |
| 11 | `src/discord/cmd_loop_start.py` | 453 |
| 12 | `src/discord/cmd_loop_stop.py` | 522 |
| 13 | `src/discord/bot.py` (lines 1–348) | 348 |
| 14 | `systemd/guinevere-loops.service` | 16 |
| 15 | `systemd/guinevere-scheduler.service` | 16 |
| 16 | `src/core/services/cost_tracker.py` | 68 |

---

## 2. Hardcoded Values Catalog

### 2.1 URLs

| Value | File | Line | Env Configurable? | Should Be? | Risk |
|---|---|---|---|---|---|
| `http://localhost:8000` | `cmd_loop_start.py` | 48 | ❌ No | ✅ Yes — `GUINEVERE_API_BASE_URL` | Medium — deployment port/hostname changes require code edit |
| `http://localhost:8000` | `cmd_loop_stop.py` | 48 | ❌ No | ✅ Yes — same env var | Medium — duplicated across two files |

### 2.2 Ports

| Value | File | Line | Env Configurable? | Should Be? | Risk |
|---|---|---|---|---|---|
| `6380` (Redis port default) | `cost.py` | 29 | ⚠️ Default param, overridable at call site | ✅ Yes — `REDIS_PORT` | Low — caller can override |
| `6380` (Redis port default) | `cost_tracker.py` | 13 | ⚠️ Default param, overridable at call site | ✅ Yes — `REDIS_PORT` | Low — caller can override |
| `8000` (embedded in URL) | `cmd_loop_start.py` | 48 | ❌ No (inside URL string) | ✅ Yes | Medium — see §2.1 |

### 2.3 Timeouts

| Value | File | Line | Env Configurable? | Should Be? | Risk |
|---|---|---|---|---|---|
| `timeout=10.0` (HTTP client) | `cmd_loop_start.py` | 350 | ❌ No | ✅ Yes — `API_HTTP_TIMEOUT` | Low — 10s is reasonable default |
| `timeout=10.0` (HTTP client) | `cmd_loop_stop.py` | 331 | ❌ No | ✅ Yes — same env var | Low |
| `timeout=10.0` (HTTP client) | `cmd_loop_stop.py` | 350 | ❌ No | ✅ Yes — same env var | Low |
| `timeout=30` (subprocess) | `verify.py` | 113 | ❌ No | ⚠️ Optional — `VERIFY_COMMAND_TIMEOUT` | Low — 30s is a safe default |

### 2.4 Guardian Thresholds (Class Constants)

| Value | File | Line | Env Configurable? | Should Be? | Risk |
|---|---|---|---|---|---|
| `HEARTBEAT_INTERVAL = 30` (seconds) | `guardian.py` | 27 | ❌ No | ✅ Yes — `GUARDIAN_HEARTBEAT_INTERVAL` | Low — operational tuning |
| `PROGRESS_TIMEOUT = 300` (5 min) | `guardian.py` | 28 | ❌ No | ✅ Yes — `GUARDIAN_PROGRESS_TIMEOUT` | Low — operational tuning |
| `RESOURCE_CHECK = 60` (seconds) | `guardian.py` | 29 | ❌ No | ⚠️ Optional — `GUARDIAN_RESOURCE_CHECK` | Low |
| `HEARTBEAT_INTERVAL * 3` (stale multiplier) | `guardian.py` | 120 | ❌ No | ⚠️ Optional | Low — derived value |

### 2.5 Enforcer Thresholds (Class Constants)

| Value | File | Line | Env Configurable? | Should Be? | Risk |
|---|---|---|---|---|---|
| `IDLE_THRESHOLD = 30` (seconds → yank) | `enforcer.py` | 25 | ❌ No | ✅ Yes — `ENFORCER_IDLE_THRESHOLD` | Low — operational tuning |
| `KILL_THRESHOLD = 60` (seconds → kill) | `enforcer.py` | 26 | ❌ No | ✅ Yes — `ENFORCER_KILL_THRESHOLD` | Low — operational tuning |

### 2.6 File Paths

| Value | File | Line | Env Configurable? | Should Be? | Risk |
|---|---|---|---|---|---|
| `/home/guinevere/evidence/loops` | `artifacts.py` | 17 | ❌ No | ✅ Yes — `EVIDENCE_ROOT` | **High** — path is deployment-specific; fails on dev machines or different VPS layouts |
| `/home/guinevere/code/guinevere` | `guinevere-loops.service` | 9–10 | N/A (systemd) | ⚠️ Acceptable — systemd unit | Low — expected in unit files |
| `/home/guinevere/code/guinevere` | `guinevere-scheduler.service` | 9–10 | N/A (systemd) | ⚠️ Acceptable — systemd unit | Low — expected in unit files |
| `.venv/bin/python` | `guinevere-loops.service` | 10 | N/A (systemd) | ⚠️ Acceptable | Low |
| `.venv/bin/python` | `guinevere-scheduler.service` | 10 | N/A (systemd) | ⚠️ Acceptable | Low |

### 2.7 API Keys / Fallbacks

| Value | File | Line | Env Configurable? | Should Be? | Risk |
|---|---|---|---|---|---|
| `"guinevere-dev-key"` (dev fallback) | `auth.py` | 15 | ⚠️ Partial — reads `GUINEVERE_API_KEY` first, falls back to dev key with warning | ❌ **Must NOT fall back** — remove dev fallback entirely in production code | **HIGH** — if env var is unset, auth silently degrades to a known key |
| `"guinevere-dev-key"` (fallback) | `cmd_loop_start.py` | 344 | ⚠️ `os.environ.get("GUINEVERE_API_KEY", "guinevere-dev-key")` | ❌ Same as above | **HIGH** — client-side fallback; any caller without env var sends known key |
| `"guinevere-dev-key"` (fallback) | `cmd_loop_stop.py` | 384 | ⚠️ `os.environ.get("GUINEVERE_API_KEY", "guinevere-dev-key")` | ❌ Same as above | **HIGH** — identical pattern |

### 2.8 Guild IDs

| Value | File | Line | Env Configurable? | Should Be? | Risk |
|---|---|---|---|---|---|
| `1_510_876_414_671_323_206` | `bot.py` | 37 | ❌ No | ✅ Yes — `DISCORD_GUILD_ID` | Medium — guild ID is deployment-specific; testing/staging needs different value |

### 2.9 Redis Configuration

| Value | File | Line | Env Configurable? | Should Be? | Risk |
|---|---|---|---|---|---|
| `host="localhost"` (default) | `cost.py` | 28 | ⚠️ Default param | ⚠️ Acceptable — caller can override | Low |
| `db=5` (default) | `cost.py` | 30 | ⚠️ Default param | ⚠️ Optional — `REDIS_DB` | Low |
| `username="guinevere_core"` | `cost.py` | 37 | ❌ No | ✅ Yes — `REDIS_USERNAME` | Medium — credential in source code |
| `host="localhost"` (default) | `cost_tracker.py` | 13 | ⚠️ Default param | ⚠️ Acceptable | Low |
| `db=5` (default) | `cost_tracker.py` | 13 | ⚠️ Default param | ⚠️ Optional | Low |
| `username="guinevere_core"` | `cost_tracker.py` | 14 | ❌ No | ✅ Yes — `REDIS_USERNAME` | Medium — credential in source code |

### 2.10 Timezone

| Value | File | Line | Env Configurable? | Should Be? | Risk |
|---|---|---|---|---|---|
| `"Asia/Bangkok"` | `scheduler.py` | 17 | ❌ No | ✅ Yes — `GUINEVERE_TIMEZONE` | Low — operator timezone may change |
| `timezone(timedelta(hours=7))` (WIB) | `cmd_loop_start.py` | 36 | ❌ No | ⚠️ Optional — derived from TZ | Low — WIB display offset |
| `timezone(timedelta(hours=7))` (WIB) | `cmd_loop_stop.py` | 36 | ❌ No | ⚠️ Optional — derived from TZ | Low — WIB display offset |

### 2.11 Service Names (systemd)

| Value | File | Line | Env Configurable? | Should Be? | Risk |
|---|---|---|---|---|---|
| `guinevere-core.service` | `guinevere-loops.service` | 3–4 | N/A (systemd) | ❌ N/A — expected in unit files | None |
| `guinevere-loops.service` | `guinevere-scheduler.service` | 3–4 | N/A (systemd) | ❌ N/A — expected in unit files | None |
| `guinevere.slice` | `guinevere-loops.service` | 13 | N/A | ❌ N/A | None |
| `guinevere.slice` | `guinevere-scheduler.service` | 13 | N/A | ❌ N/A | None |
| `RestartSec=10` | both service files | 12 | N/A | ⚠️ Optional via systemd override | None |

### 2.12 Budget Thresholds

| Value | File | Line | Env Configurable? | Should Be? | Risk |
|---|---|---|---|---|---|
| `30` (monthly cap default from Redis) | `cost_tracker.py` | 48 | ⚠️ Reads from Redis key `budget:monthly_cap`, fallback 30 | ⚠️ Redis-configurable; fallback should be env | Low |
| `ratio >= 1.0` → `HARD_STOP` | `cost_tracker.py` | 60 | ❌ No | ⚠️ Optional — policy ratio | Low — fixed policy |
| `ratio >= 0.833` → `CRITICAL` | `cost_tracker.py` | 62 | ❌ No | ⚠️ Optional | Low |
| `ratio >= 0.5` → `WARNING` | `cost_tracker.py` | 64 | ❌ No | ⚠️ Optional | Low |
| `current >= 1.0` → `NORMAL_ALERT` | `cost_tracker.py` | 66 | ❌ No | ⚠️ Optional | Low |

### 2.13 Other Constants

| Value | File | Line | Env Configurable? | Should Be? | Risk |
|---|---|---|---|---|---|
| `"!"` (command prefix) | `bot.py` | 118 | ❌ No | ⚠️ Optional | None |
| `"/api/v1"` (route prefix) | `routes.py` | 14 | ❌ No | ⚠️ Optional — API versioning | Low |
| `"loop:cost"` (Redis key prefix) | `cost.py` | 20 | ❌ No | ⚠️ Optional | None |
| `"X-Guinevere-API-Key"` (header name) | `auth.py` | 13 | ❌ No | ⚠️ Optional | None — protocol constant |

---

## 3. Security-Sensitive Findings

### 3.1 CRITICAL: Dev API Key Fallback (3 locations)

**Files:** `auth.py:15`, `cmd_loop_start.py:344`, `cmd_loop_stop.py:384`

The string `"guinevere-dev-key"` is used as a fallback when `GUINEVERE_API_KEY` is not set. While `auth.py` logs a warning, the fallback is still active. This means:

- If the env var is accidentally unset in production, authentication degrades to a **known, publicly-visible key** in the source code.
- The same fallback exists client-side (`cmd_loop_start.py`, `cmd_loop_stop.py`), so the Discord bot would send this known key to the API.
- **Recommendation:** Remove the dev fallback entirely. Raise an error or refuse to start if `GUINEVERE_API_KEY` is not set. At minimum, add a `GUINEVERE_ENV` check (only allow fallback when `GUINEVERE_ENV=development`).

### 3.2 MEDIUM: Redis Username Hardcoded

**Files:** `cost.py:37`, `cost_tracker.py:14`

The Redis username `"guinevere_core"` is hardcoded as a string literal, not read from environment. While the password IS env-configurable (`REDIS_PASSWORD`), the username is not. This couples the code to a specific Redis ACL configuration.

**Recommendation:** Add `REDIS_USERNAME` env var with `"guinevere_core"` as default.

### 3.3 MEDIUM: Hardcoded Evidence Path

**File:** `artifacts.py:17`

`/home/guinevere/evidence/loops` is a module-level constant. This will fail on:
- Developer machines (different home directory)
- CI/CD environments
- Docker containers
- Any VPS with a different user layout

**Recommendation:** Read from `EVIDENCE_ROOT` env var with the current path as default.

---

## 4. Configurability Summary

| Category | Total Values | Env-Configurable | Hardcoded (acceptable) | Hardcoded (should fix) |
|---|---|---|---|---|
| URLs | 2 | 0 | 0 | **2** |
| Ports | 3 | 2 (defaults) | 0 | 1 (in URL) |
| Timeouts | 4 | 0 | 2 | 2 |
| Guardian thresholds | 4 | 0 | 2 | 2 |
| Enforcer thresholds | 2 | 0 | 0 | **2** |
| File paths | 5 | 0 | 4 (systemd) | **1** |
| API keys/fallbacks | 3 | 3 (partial) | 0 | **3** |
| Guild IDs | 1 | 0 | 0 | **1** |
| Redis config | 6 | 3 (passwords) | 2 (defaults) | **1** (username) |
| Timezone | 3 | 0 | 2 | 1 |
| Service names | 5 | 0 | 5 (systemd) | 0 |
| Budget thresholds | 5 | 1 (Redis) | 4 | 0 |
| Other constants | 4 | 0 | 4 | 0 |
| **TOTAL** | **47** | **9** | **23** | **15** |

---

## 5. Recommended Environment Variables

| Proposed Env Var | Default | Replaces | Files |
|---|---|---|---|
| `GUINEVERE_API_BASE_URL` | `http://localhost:8000` | Hardcoded URL | `cmd_loop_start.py`, `cmd_loop_stop.py` |
| `API_HTTP_TIMEOUT` | `10.0` | `timeout=10.0` | `cmd_loop_start.py`, `cmd_loop_stop.py` |
| `GUARDIAN_HEARTBEAT_INTERVAL` | `30` | Class constant | `guardian.py` |
| `GUARDIAN_PROGRESS_TIMEOUT` | `300` | Class constant | `guardian.py` |
| `ENFORCER_IDLE_THRESHOLD` | `30` | Class constant | `enforcer.py` |
| `ENFORCER_KILL_THRESHOLD` | `60` | Class constant | `enforcer.py` |
| `EVIDENCE_ROOT` | `/home/guinevere/evidence/loops` | Module constant | `artifacts.py` |
| `DISCORD_GUILD_ID` | `1510876414671323206` | Module constant | `bot.py` |
| `REDIS_USERNAME` | `guinevere_core` | Hardcoded string | `cost.py`, `cost_tracker.py` |
| `REDIS_PORT` | `6380` | Default param | `cost.py`, `cost_tracker.py` |
| `GUINEVERE_TIMEZONE` | `Asia/Bangkok` | Module constant | `scheduler.py` |

---

## 6. Verdict

### **NEEDS REVIEW**

**Rationale:**

- **No fully-passing env configurability.** 15 out of 47 hardcoded values should be made configurable via environment variables.
- **Security-sensitive issue:** The `"guinevere-dev-key"` fallback in 3 locations is a security concern. If `GUINEVERE_API_KEY` is unset, authentication degrades to a known value present in the source code. This is the primary blocker for a PASS verdict.
- **Operational rigidity:** Hardcoded evidence path, guild ID, and URL mean the code cannot be deployed to a different environment without source modifications.
- **Mitigating factors:** Redis passwords ARE env-configurable. Discord bot token IS env-configurable. DATABASE_URL IS env-configurable. Systemd unit files contain expected hardcoded paths. Budget cap IS Redis-configurable. These prevent a FAIL verdict.

### Blocking Issue (must fix before PASS):

1. Remove `"guinevere-dev-key"` fallback or gate it behind `GUINEVERE_ENV=development`.

### Recommended Fixes (non-blocking):

2. Add `GUINEVERE_API_BASE_URL` env var for API URL.
3. Add `EVIDENCE_ROOT` env var for artifact path.
4. Add `DISCORD_GUILD_ID` env var for guild ID.
5. Add `REDIS_USERNAME` env var for Redis ACL username.
6. Make guardian/enforcer thresholds env-configurable.

---

## 7. Footer

| Item | Detail |
|---|---|
| Auditor | Independent Config Auditor (automated) |
| Scope | 16 files, 47 hardcoded values cataloged |
| Method | Line-by-line source review |
| No source code modified | ✅ Confirmed |
