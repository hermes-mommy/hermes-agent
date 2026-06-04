# D13 — Aizanta Isolation Audit Report

**Audit Date:** 2026-06-03
**Phase:** P6 — MCP Tools
**Dimension:** 13 — Aizanta Isolation
**Severity:** THIS IS A CRITICAL DIMENSION

---

## Overall Verdict: **FAIL**

**Cross-contamination vectors found in PostgreSQL (3 CRITICAL), Docker (3 CRITICAL), Shell (2 HIGH), and Filesystem (1 HIGH).**

---

## Isolation Matrix

| System | Sub-System | Verdict | Notes |
|---|---|---|---|
| **PostgreSQL** | Port Isolation | **FAIL** | `POSTGRES_PORT` env var can override the 5433 default to 5432 (Aizanta's port). No validation. |
| **PostgreSQL** | Database Isolation | **FAIL** | `POSTGRES_DB` env var can override `guinevere` to Aizanta's database name. No validation. |
| **PostgreSQL** | User/Role Isolation | **FAIL** | `POSTGRES_READONLY_USER` env var isn't validated — any role can be used, including Aizanta's roles. |
| **PostgreSQL** | SQL Write Protection | PASS | 3-layer defense (BEGIN READ ONLY, keyword classification, readonly role) blocks DDL/DML. |
| **Redis** | Port Isolation | PASS | `_REDIS_PORT = 6380` is a hardcoded module constant — **not** env-overridable. |
| **Redis** | User Isolation | PASS | `_REDIS_USERNAME = "guinevere_core"` is hardcoded. |
| **Redis** | DB Allocation | **NEEDS REVIEW** | No validation that `db` parameter stays within 0–5. Could attempt DB6+ on the same instance. |
| **Redis** | FLUSHALL/FLUSHDB | PASS | FORBIDDEN auth level; function bodies raise `ForbiddenOperationError` before execution. |
| **Docker** | Container Visibility | **FAIL** | `docker_logs` and `docker_inspect` skip `_check_guinevere_network()`. Can read Aizanta container logs and metadata. |
| **Docker** | Image Visibility | **FAIL** | `docker_images` lists ALL images on the Docker daemon — no network filter. |
| **Docker** | Container Lifecycle | PASS | `docker_ps` (with network filter), `start`, `stop`, `restart`, `rm` all gate on `guinevere-net`. |
| **Docker** | Image Removal | **FAIL** | `docker_rmi` doesn't check network — can remove images Aizanta depends on. |
| **Docker** | Prune/Flush | PASS | `docker_system_prune` and `docker_rm_all` are FORBIDDEN. |
| **Filesystem** | Path Whitelist | **NEEDS REVIEW** | Defaults exclude `/home/aizanta/`, but `FILESYSTEM_ALLOWED_PATHS` env var can override at registration time. |
| **Filesystem** | Symlink Escape | PASS | `Path.resolve()` resolves symlinks before whitelist check. Escapes are blocked. |
| **Shell** | Filesystem Access | **FAIL** | `ls`, `cat`, `find`, `head`, `tail` can read `/home/aizanta/` if user `guinevere` has filesystem permissions. |
| **Shell** | Aizanta Service Visibility | **FAIL** | `systemctl status` in whitelist — `systemctl status aizanta-core` would work. |
| **Shell** | Docker Access | PASS | `docker` and `docker exec` are NOT in `ALLOWED_COMMANDS`. |
| **Shell** | Injection & Pipe | PASS | `;`, `|`, `&&`, `||`, backticks, `$()`, `<`, `>` all blocked. |
| **Shell** | Dangerous Commands | PASS | `rm -rf`, `sudo`, `dd`, `mkfs`, `shutdown`, `reboot` all blocked. |
| **Shell** | Shell Execution | PASS | Uses `asyncio.create_subprocess_exec` — never `shell=True`. |
| **systemd** | Aizanta Dependencies | PASS | All Guinevere services chain off `guinevere-core.service`. No references to any Aizanta unit. |
| **systemd** | Resource Limits | PASS | All services have `MemoryHigh`, `MemoryMax`, `CPUQuota` under `guinevere.slice`. |
| **systemd** | Security Hardening | PASS | All services have `NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=read-only`. |
| **Network** | Outbound from MCP | **NEEDS REVIEW** | `python` and `pip` in shell whitelist — can make arbitrary outbound connections (e.g., to Aizanta's internal APIs). No egress filtering at the MCP level. |

---

## Cross-Contamination Vectors Found

### 🔴 CRITICAL — V1: PostgreSQL Port Override (postgres_tool.py:116)

**Vector:** Setting `POSTGRES_PORT=5432` in the environment redirects ALL queries to Aizanta's PostgreSQL instance.
**Code location:** `postgres_tool.py`, line 116:
```python
port = int(os.environ.get("POSTGRES_PORT", str(_DEFAULT_PORT)))
```
**Impact:** A rogue env configuration (deliberate or accidental) points all `postgres_query`, `postgres_tables`, and `postgres_describe` calls at Aizanta's database. Since the tool uses `BEGIN READ ONLY`, it can only READ (not write), but it can exfiltrate ALL of Aizanta's data through SELECT queries.
**Attack surface:** Any process or config management system that can set `POSTGRES_PORT` and `POSTGRES_DB` env vars for the `guinevere-mcp.service`.

**Required fix:** Hardcode `port = 5433` or validate at startup that `POSTGRES_PORT` is either unset or exactly `5433`. Reject any override.

---

### 🔴 CRITICAL — V2: PostgreSQL Database Override (postgres_tool.py:117)

**Vector:** Setting `POSTGRES_DB=aizanta_production` directs queries to Aizanta's database.
**Code location:** `postgres_tool.py`, line 117:
```python
db = os.environ.get("POSTGRES_DB", _DEFAULT_DB)
```
**Impact:** Even if port is kept at 5433, changing the database name could point at a different logical DB within the same Postgres cluster. Combined with V1, this is a full pivot to Aizanta's data.
**Required fix:** Hardcode `db = "guinevere"` or validate at startup that `POSTGRES_DB` is either unset or exactly `"guinevere"`.

---

### 🔴 CRITICAL — V3: PostgreSQL User Override (postgres_tool.py:118)

**Vector:** Setting `POSTGRES_READONLY_USER=aizanta_admin` bypasses Guinevere's dedicated `guinevere_readonly` role.
**Code location:** `postgres_tool.py`, line 118:
```python
user = os.environ.get("POSTGRES_READONLY_USER", _DEFAULT_READONLY_USER)
```
**Impact:** If someone obtains credentials for an Aizanta database role, they can authenticate through Guinevere's MCP tool and read Aizanta data (combined with V1+V2).
**Required fix:** Hardcode `user = "guinevere_readonly"` or validate at startup that `POSTGRES_READONLY_USER` is unset or exactly `"guinevere_readonly"`.

---

### 🔴 CRITICAL — V4: Docker Logs Leakage (docker_tool.py:315)

**Vector:** `docker_logs` does NOT call `_check_guinevere_network()`. Any container name on the host can be inspected.
**Code location:** `docker_tool.py`, lines 315-339. Compare with `docker_start` (line 395) which DOES call `_check_guinevere_network()`.
**Impact:** `docker_logs("aizanta-core")` returns all stdout/stderr from Aizanta's containers, including potentially sensitive logs, error messages, debug output, API keys accidentally logged, etc.
**Required fix:** Add `await _check_guinevere_network(container)` at the top of `docker_logs()` and `docker_inspect()`.

---

### 🔴 CRITICAL — V5: Docker Inspect Leakage (docker_tool.py:342)

**Vector:** Same as V4 — `docker_inspect` has no network check. Exposes full container metadata including environment variables, mounted volumes, network config, and image details.
**Code location:** `docker_tool.py`, lines 342-352.
**Impact:** Full container inspection of Aizanta containers reveals:
- Environment variables (potentially including secrets)
- Volume mounts (exposing filesystem paths)
- Network configuration
- Container command/entrypoint
**Required fix:** Add `await _check_guinevere_network(container)` at the top of `docker_inspect()`.

---

### 🔴 CRITICAL — V6: Docker Image Removal Cross-Contamination (docker_tool.py:484)

**Vector:** `docker_rmi` validates image name syntax only — no check that the image isn't used by Aizanta containers.
**Code location:** `docker_tool.py`, lines 484-508.
**Impact:** Removing an image that Aizanta's containers depend on could cause cascading failures when Aizanta containers restart or try to pull. In a shared Docker daemon, this is a denial-of-service vector against Aizanta.
**Required fix:** Before `docker_rmi`, inspect all running containers (including non-guinevere-net ones) and reject if the image is in use by any container NOT on `guinevere-net`.

---

### 🟡 HIGH — V7: Shell Filesystem Bypass (shell_tool.py:36)

**Vector:** `ls`, `cat`, `find`, `head`, `tail`, `python` are all in `ALLOWED_COMMANDS`. Nothing prevents accessing `/home/aizanta/`.
**Code location:** `shell_tool.py`, lines 36-59 (whitelist + no path-based restrictions).
**Impact:** If the OS user `guinevere` has read permissions on `/home/aizanta/` (common on shared VPS), the shell tool can read Aizanta's source code, configuration, logs, and data files.
**Mitigation:** This relies on OS-level file permissions. If `/home/aizanta/` is mode 700 (owner-only), this vector is blocked at the kernel level. But the MCP tool provides no defense-in-depth.
**Required fix:** Add a `BLOCKED_PATHS` list that includes `/home/aizanta/` and `/etc/aizanta/`. Reject any shell command whose `workdir` or arguments reference blocked paths.

---

### 🟡 HIGH — V8: Shell systemctl Cross-Service Visibility (shell_tool.py:47)

**Vector:** `systemctl status` is in `ALLOWED_COMMANDS`. `systemctl status aizanta-core` would reveal Aizanta's service status, uptime, recent log lines, and PID.
**Impact:** Operational intelligence leak — reveals when Aizanta services are running, restarting, or failing.
**Required fix:** Block `systemctl status` for any unit name containing `aizanta`. Restrict `systemctl status` to units matching `guinevere-*` only.

---

### 🟡 HIGH — V9: Filesystem Whitelist Override at Registration (filesystem.py:53-64)

**Vector:** `FILESYSTEM_ALLOWED_PATHS` env var can add arbitrary paths including `/home/aizanta/` at process startup. The config is frozen after registration but the env var is the single source of truth.
**Impact:** A compromised environment variable at process start expands the whitelist to include Aizanta's directories.
**Required fix:** Add a hardcoded `BLOCKED_PREFIXES` set (e.g., `["/home/aizanta", "/etc/aizanta"]`) that is checked after env var parsing but before the frozenset is built. Any blocked prefix causes a startup failure.

---

### 🔵 NEEDS REVIEW — V10: Redis DB Range Unbounded (redis_tool.py:148-153)

**Vector:** Every Redis tool function accepts a `db` parameter (default 5). No validation that `0 <= db <= 5`.
**Impact:** If Guinevere's Redis instance on port 6380 also has data in DB6-15 (unlikely per spec, but possible if misconfigured), the tool can access it.
**Risk:** Low if Redis on port 6380 is a dedicated Guinevere instance. Medium if it shares the Redis server with other applications (not Aizanta, which is on 6379).
**Required fix:** Add validation: `if not 0 <= db <= 5: raise ValueError(...)`.

---

### 🔵 NEEDS REVIEW — V11: Shell Python/Pip Egress (shell_tool.py:44-45)

**Vector:** `python` and `pip` in `ALLOWED_COMMANDS` allow arbitrary code execution with network access. Could scan Aizanta's localhost services or make outbound calls.
**Impact:** A malicious Python script could port-scan localhost, probe Aizanta's API endpoints, or exfiltrate data over the network.
**Required fix:** Either: (a) Remove `python` and `pip` from `ALLOWED_COMMANDS` (breaking legitimate use), or (b) run shell subprocesses with restricted network namespaces/cgroups.

---

## Required Fixes (CRITICAL — Must Fix Before P7)

| # | Vector | Fix | Effort |
|---|---|---|---|
| 1 | PostgreSQL port override | Hardcode `port = 5433` OR validate `POSTGRES_PORT` is unset or exactly `5433` at pool creation. Reject otherwise. | Quick |
| 2 | PostgreSQL DB override | Hardcode `db = "guinevere"` OR validate `POSTGRES_DB` is unset or exactly `"guinevere"`. | Quick |
| 3 | PostgreSQL user override | Hardcode `user = "guinevere_readonly"` OR validate `POSTGRES_READONLY_USER` is unset or exactly `"guinevere_readonly"`. | Quick |
| 4 | Docker logs leakage | Add `await _check_guinevere_network(container)` at top of `docker_logs()`. | Quick |
| 5 | Docker inspect leakage | Add `await _check_guinevere_network(container)` at top of `docker_inspect()`. | Quick |
| 6 | Docker rmi cross-contamination | In `docker_rmi()`, inspect all running containers and reject if image is used by a non-guinevere-net container. | Short |

## Required Fixes (HIGH — Should Fix Before P7)

| # | Vector | Fix | Effort |
|---|---|---|---|
| 7 | Shell FS bypass | Add `BLOCKED_PATHS` validation in `validate_command()` or `_execute()`. | Short |
| 8 | Shell systemctl visibility | Block `systemctl` sub-commands on units matching `aizanta*`. | Quick |
| 9 | FS whitelist override | Add `BLOCKED_PREFIXES` hardcoded blocklist checked after env parsing. Startup failure on match. | Quick |

## Required Fixes (NEEDS REVIEW — Fix Before P7 if Time Permits)

| # | Vector | Fix | Effort |
|---|---|---|---|
| 10 | Redis DB range | Validate `0 <= db <= 5` in `_connect()`. | Quick |
| 11 | Shell python/pip egress | Remove from whitelist OR add guard. (High design impact — discuss with Faiz.) | Short |

---

## What Passed — Defense-in-Depth Strengths

- **Redis port is genuinely hardcoded** — no `os.environ.get()` for `REDIS_PORT`. This is the gold standard other tools should emulate.
- **Docker lifecycle commands (start/stop/restart/rm) all enforce guinevere-net** — good design, just needs extending to logs/inspect.
- **Filesystem symlink resolution prevents traversal escapes** — `Path.resolve()` + `os.sep` prefix matching is solid.
- **FLUSHALL/FLUSHDB are blocked at the auth layer** — function bodies never execute.
- **Shell injection characters comprehensively blocked** — `;`, `|`, `&&`, `||`, backticks, `$()`, `<>`.
- **systemd has zero Aizanta dependencies** — all services chain off `guinevere-core`.
- **All services have resource limits and security hardening** — `NoNewPrivileges`, `ProtectSystem=strict`, memory/CPU quotas.

---

## Evidence Artifacts Reviewed

- `src/mcp/tools/postgres_tool.py` — 333 lines
- `src/mcp/tools/redis_tool.py` — 444 lines
- `src/mcp/tools/docker_tool.py` — 614 lines
- `src/mcp/tools/filesystem.py` — 210 lines
- `src/mcp/tools/shell_tool.py` — 364 lines
- `src/mcp/tools/git_tool.py` — 362 lines
- `src/mcp/auth.py` — 216 lines
- `systemd/guinevere-mcp.service`, `guinevere-obscura.service`, `guinevere-loops.service`, `guinevere-scheduler.service`, `guinevere-surveillance.service`
- `docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service`
- `src/core/config/__init__.py`

---

## Auditor Sign-Off

| Field | Value |
|---|---|
| Auditor | Guinevere (D13 specialist) |
| Verdict | **FAIL** — 6 CRITICAL, 3 HIGH, 3 NEEDS REVIEW |
| Date | 2026-06-03 |
| Next Action | Fix all 6 CRITICAL items before P7 launch. Fix HIGH items during P7 early sprints. |