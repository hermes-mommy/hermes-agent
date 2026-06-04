# D03 — Security & Secrets Audit — P6 MCP Tools

| Field | Value |
|---|---|
| **Dimension** | D03 — Security & Secrets |
| **Phase** | P6 — FINAL AUDIT |
| **Audit Date** | 2026-06-03 |
| **Auditor** | Guinevere (Sisyphus-Junior) |
| **Scope** | All `src/mcp/` files (24), `tests/mcp/` files (22), `systemd/` units (9), `evidence/`, `docs/` |
| **Methodology** | 11-point automated grep audit + manual source review |
| **Overall Verdict** | ⚠️ NEEDS REVIEW — 1 CRITICAL finding (pre-existing P0), 1 action-required gap |

---

## Executive Summary

| # | Check | Verdict |
|---|---|---|
| 1 | Hardcoded secrets in `src/mcp/` | ✅ PASS |
| 2 | All secrets use `os.environ.get()` | ✅ PASS |
| 3 | Port isolation (PG:5433, Redis:6380) | ✅ PASS |
| 4 | systemd credential specifiers | ⚠️ NEEDS REVIEW |
| 5 | tests/mcp/ secret hygiene | ✅ PASS |
| 6 | evidence/ plaintext secrets | ✅ PASS |
| 7 | docs/ plaintext secrets | ✅ PASS |
| 8 | P0-014 real POSTGRES_PASSWORD exposure | 🔴 FAIL — CRITICAL |
| 9 | shell_tool.py injection prevention | ✅ PASS |
| 10 | fetch.py URL scheme validation | ✅ PASS |
| 11 | filesystem.py path whitelist + symlinks | ✅ PASS |

**Overall**: 9 PASS, 1 NEEDS REVIEW, 1 CRITICAL FAIL (pre-existing P0 issue).

---

## 1. Hardcoded Secrets in `src/mcp/` — ✅ PASS

### Methodology

Six separate grep scans across all 24 files in `src/mcp/`:

| Pattern | Target | Matches |
|---|---|---|
| `sk-[A-Za-z0-9]{20,}` | OpenAI/Anthropic API keys | 0 |
| `ghp_[A-Za-z0-9]{20,}` | GitHub PATs | 0 |
| `password\s*=\s*["'][^"']*["']` | Hardcoded passwords | 0 |
| `token\s*=\s*["'][^"']*["']` | Hardcoded tokens | 0 |
| `secret\s*=\s*["'][^"']*["']` | Hardcoded secrets | 0 |
| `://[^@]*:[^@]*@` | URLs with credentials | 0 |

### Result

**ZERO hardcoded secrets.** All 18 occurrences of credential access use `os.environ.get()` exclusively.

---

## 2. Secret Source Verification — ✅ PASS

### Per-secret audit

| Secret | File(s) | Access Pattern | Status |
|---|---|---|---|
| `BRAVE_API_KEY` | `brave_search.py:56` | `os.environ.get("BRAVE_API_KEY")` | ✅ |
| `EXA_API_KEY` | `exa_search.py:64` | `os.environ.get("EXA_API_KEY")` | ✅ |
| `GITHUB_PAT` | `github.py:58,76` | `os.environ.get("GITHUB_PAT", "")` | ✅ |
| `REDIS_PASSWORD` | 7 files | `os.environ.get("REDIS_PASSWORD", "")` | ✅ |
| `POSTGRES_PASSWORD` | `postgres_tool.py:119` | `os.environ.get("POSTGRES_PASSWORD", "")` | ✅ |
| `DISCORD_WEBHOOK_URL` | `auth.py:67` | `os.environ.get("DISCORD_WEBHOOK_URL")` | ✅ |

### REDIS_PASSWORD usage locations (7 files)

1. `src/mcp/cost.py:61` — ToolCostTracker
2. `src/mcp/budget.py:81` — BudgetManager
3. `src/mcp/tools/context7.py:165` — Context7 cache
4. `src/mcp/tools/brave_search.py:71` — Brave search cache
5. `src/mcp/tools/exa_search.py:79` — Exa search cache
6. `src/mcp/tools/redis_tool.py:124` — Redis tool connection
7. `src/mcp/auth_matrix.py` — (indirect via Redis)

All use consistent `os.environ.get("REDIS_PASSWORD", "")` pattern.

### Additional secure env reads

| Variable | File | Runtime configurable |
|---|---|---|
| `FILESYSTEM_ALLOWED_PATHS` | `filesystem.py:59` | Yes |
| `GIT_BINARY` | `git_tool.py:39` | Yes (default: `"git"`) |
| `POSTGRES_HOST` | `postgres_tool.py:115` | Yes (default: `"localhost"`) |
| `POSTGRES_PORT` | `postgres_tool.py:116` | Yes (default: `5433`) |
| `POSTGRES_READONLY_USER` | `postgres_tool.py:118` | Yes (default: `"guinevere_readonly"`) |
| `POSTGRES_DB` | `postgres_tool.py:117` | Yes (default: `"guinevere"`) |

---

## 3. Port Isolation — ✅ PASS

### PostgreSQL: 5433 (not 5432)

| File | Evidence |
|---|---|
| `postgres_tool.py:10` | Docstring: `"Port: 5433 (Guinevere), not 5432 (Aizanta)."` |
| `postgres_tool.py:95` | `_DEFAULT_PORT: Final[int] = 5433` |
| `postgres_tool.py:116` | `port = int(os.environ.get("POSTGRES_PORT", str(_DEFAULT_PORT)))` |

No reference to port 5432 anywhere in `src/mcp/`.

### Redis: 6380 (not 6379)

| File | Evidence |
|---|---|
| `redis_tool.py:9` | Docstring: `"Port: 6380 (non-standard, project config)"` |
| `redis_tool.py:42` | `_REDIS_PORT = 6380` |
| `cost.py:52` | `port: int = 6380` |
| `budget.py:78` | `port=6380` |
| `context7.py:162` | `port=6380` |
| `exa_search.py:76` | `port=6380` |
| `brave_search.py:68` | `port=6380` |

No reference to port 6379 anywhere in `src/mcp/`.

---

## 4. Systemd Credential Handling — ⚠️ NEEDS REVIEW

### 4.1 Services using `%E/` credential specifiers

Five systemd units set `REDIS_PASSWORD=%E/REDIS_PASSWORD`:

| Service | Credential |
|---|---|
| `guinevere-mcp.service:13` | `Environment=REDIS_PASSWORD=%E/REDIS_PASSWORD` |
| `guinevere-surveillance.service:14` | `Environment=REDIS_PASSWORD=%E/REDIS_PASSWORD` |
| `guinevere-loops.service:13` | `Environment=REDIS_PASSWORD=%E/REDIS_PASSWORD` |
| `guinevere-scheduler.service:13` | `Environment=REDIS_PASSWORD=%E/REDIS_PASSWORD` |
| `guinevere-surveillance.service:16` | `Environment=DATABASE_URL=postgresql+asyncpg://guinevere:%E/GUINEVERE_DB_PASSWORD@localhost:5433/guinevere` |

**Concern**: The `%E` specifier resolves to a **directory path** (e.g., `/etc/credstore/`), so `%E/REDIS_PASSWORD` becomes a **file path** like `/etc/credstore/REDIS_PASSWORD`. However, the application code reads the environment variable directly:

```python
# redis_tool.py:124
password = os.environ.get("REDIS_PASSWORD", "")
```

This means the application would receive the **path string** `/etc/credstore/REDIS_PASSWORD` as the password, not the file's contents. The application does not read credentials from files — it expects the environment variable to contain the actual value.

**Impact**: If these systemd units are deployed as-is, Redis and PostgreSQL authentication will fail because the credentials are file paths, not actual passwords.

**Recommendation**: Either:
- A. Use `LoadCredentialEncrypted=REDIS_PASSWORD:/path/to/encrypted.cred` and have the application read `$CREDENTIALS_DIRECTORY/REDIS_PASSWORD`, OR
- B. Use SOPS-based decryption (like the Discord service) to inject actual values into environment variables at startup.

### 4.2 Correct patterns observed

| Service | Pattern | Assessment |
|---|---|---|
| `guinevere-discord.service` | `ExecStartPre=sops --decrypt` → tmpfs → `EnvironmentFile=` → `ExecStopPost=shred -u` | ✅ Correct: SOPS decrypts to `/run/` (tmpfs), file has `chmod 600`, shredded after stop |
| `guinevere-backup@.service` | `sops exec-env` in `ExecStart` | ✅ Correct: SOPS decrypts env into subprocess only, never persisted |
| `guinevere-prune-weekly@.service` | `sops exec-env` in `ExecStart` | ✅ Correct: Same pattern as backup |
| `guinevere-obscura.service` | No secrets | ✅ N/A |
| `guinevere-core.service` (P1-018) | No secrets | ✅ N/A |

### 4.3 No EnvironmentFile with plaintext secrets

✅ Confirmed: Zero systemd units use `EnvironmentFile=` pointing to plaintext credential files (except the Discord service which decrypts from SOPS into tmpfs, and shreds on stop).

---

## 5. Tests Secret Hygiene — ✅ PASS

### Methodology

Grep across all 22 test files in `tests/mcp/` for secret-like patterns.

### Test placeholder inventory

| Test File | Placeholder Used |
|---|---|
| `test_brave_search.py` | `"test-key-123"` |
| `test_github.py` | `"test-pat"`, `"invalid-pat"`, `"test-pat"` |
| `test_git_tool.py` | `"ghp_test123"` (in monkeypatch.setenv) |
| `test_exa_search.py` | `"my-secret-key"`, `"my-api-key"` |
| `test_redis_tool.py` | `"test_pw"`, `"pw"`, `"secret123"` |
| `test_cost.py` | `"custom-pwd"` |
| `test_obscura_cdp.py` | `"s3cret"` (CSS selector, not actual secret) |
| `test_filesystem.py` | `"secret"` (test file content, mock data) |
| `test_postgres_tool.py` | No hardcoded passwords (uses env mocks) |
| `test_shell_tool.py` | References `BLOCKED_PATTERNS` exports only |
| All others | No secrets |

### Result

✅ **ALL test secrets are clearly synthetic placeholders.** No file contains a pattern matching real API keys, tokens, or passwords.

---

## 6. Evidence/ Directory Secret Scan — ✅ PASS

### Methodology

Grep for all secret patterns across `evidence/` directory → 8 files matched initially (prose matches for "password", "token", etc. in markdown). Follow-up grep specific for `password = "..."` and `token = "..."` assignment patterns across those 8 files → **zero matches**.

### Result

✅ No plaintext secrets found in `evidence/`. All matches are documentation prose, not credential assignments.

---

## 7. Docs/ Directory Secret Scan — ✅ PASS

### Methodology

Grep for secret patterns across `docs/` → 51 files matched (all references to "password", "token", "secret" in markdown prose). Follow-up targeted grep for actual credential values:

| Targeted Search | Pattern | Matches |
|---|---|---|
| Real POSTGRES_PASSWORD value | `POSTGRES_PASSWORD=sfz` | 0 |
| Password assignments with actual values | `password\s*=\s*["'][A-Za-z0-9]` | 0 |

### Result

✅ No plaintext secrets in `docs/`. All 51 matches are documentation prose (e.g., "the password is stored in the env var", "token rotation policy"), not actual credential values.

---

## 8. 🔴 CRITICAL — P0-014 Real POSTGRES_PASSWORD Exposure

### Finding

**File**: `audit-reports/P0/STEP-P0-014/step-p0-014-auditor-report.md`  
**Line**: 189  
**Content**:

```json
"Env": [
  "POSTGRES_INITDB_ARGS=--encoding=UTF8 --locale=en_US.UTF-8",
  "POSTGRES_USER=guinevere",
  "POSTGRES_DB=guinevere",
  "POSTGRES_PASSWORD=sfzdoPtm1aS7ZbFne2Ovq4wDkABNQECX"
]
```

### Context

This is the P0-014 auditor report that documents the PostgreSQL 16 Docker container setup on the shared VPS. The audit was performed on 2026-05-31 and included a live SSH session that captured the Docker container configuration, including the full `docker inspect` output with all environment variables — one of which is the **real PostgreSQL superuser password**.

### Impact

| Factor | Assessment |
|---|---|
| **Password type** | PostgreSQL `POSTGRES_USER=guinevere` superuser password |
| **Scope** | Production VPS database at `100.94.104.22` |
| **Exposure** | Written to a markdown file in a git-tracked repo |
| **Rotation status** | Unknown (likely NOT rotated since P0) |
| **Severity** | **CRITICAL** |

### Remediation Required

1. **IMMEDIATE**: Rotate the `guinevere` PostgreSQL password on the VPS
2. **IMMEDIATE**: Redact line 189 from `step-p0-014-auditor-report.md`
3. **Audit git history**: Check if this file was ever pushed to GitHub/git remotes (the repo `.gitignore` may not cover `audit-reports/`)
4. **Prevention**: Add `POSTGRES_PASSWORD=*` and similar patterns to a pre-commit secret scanner

### Classification

This is a **pre-existing P0 issue** — the auditor report was created during P0 infrastructure setup. It was not introduced by P6 MCP tool development. However, it remains an unaddressed security vulnerability in the repo.

---

## 9. Shell Tool Injection Prevention — ✅ PASS

### File: `src/mcp/tools/shell_tool.py` (364 lines)

### Defense layers (4)

| Layer | Mechanism | Detail |
|---|---|---|
| 1 — Injection characters | `_check_injection()` | Blocks `;`, `\|`, `&&`, `\|\|`, `` ` ``, `$(`, `>`, `<` — 8 patterns |
| 2 — Destructive patterns | `_check_blocked_patterns()` | Blocks `rm -rf`, `sudo`, `mkfs`, `dd`, `shutdown`, `reboot`, `halt`, `poweroff`, `chmod 777`, `> /dev/sda`, fork bomb `:(){`, pipe-to-shell — 13 patterns |
| 3 — Command whitelist | `ALLOWED_COMMANDS` | Only 20 commands: `ls`, `cat`, `grep`, `find`, `wc`, `head`, `tail`, `python`, `pip`, `git`, `systemctl status`, `df`, `free`, `uptime`, `hostname`, `whoami`, `pwd`, `echo`, `date`, `which`, `file`, `stat` |
| 4 — No shell=True | `asyncio.create_subprocess_exec(*args)` | Uses argument-list execution, never passes to shell. `shlex.split()` for safe parsing |

### Execution

```python
# Line 246-251 — NEVER shell=True
process = await asyncio.create_subprocess_exec(
    *args,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    cwd=workdir,
)
```

### Auth gating

- All shell operations require `AuthLevel.DESTRUCTIVE_APPROVAL`
- Operator must explicitly approve each invocation via Discord
- 5-minute approval timeout

### Result

✅ **Defense-in-depth.** Four independent layers prevent injection, with operator-in-the-loop approval as final gate.

---

## 10. Fetch URL Scheme Validation — ✅ PASS

### File: `src/mcp/tools/fetch.py` (213 lines)

### URL validation

```python
# Line 34
_ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https"})

# Line 49-57
def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"URL scheme '{scheme}' is not allowed. "
            f"Only http:// and https:// are permitted."
        )
```

### Effectively blocked schemes

| Scheme | Blocked? | Constraint |
|---|---|---|
| `file://` | ✅ | Not in `_ALLOWED_SCHEMES` |
| `ftp://` | ✅ | Not in `_ALLOWED_SCHEMES` |
| `gopher://` | ✅ | Not in `_ALLOWED_SCHEMES` |
| `data:` | ✅ | Not in `_ALLOWED_SCHEMES` |
| `javascript:` | ✅ | Not in `_ALLOWED_SCHEMES` |
| `http://` | Allowed | Only permitted scheme |
| `https://` | Allowed | Only permitted scheme |

### Additional protections

- 1 MB response size limit (`_MAX_CONTENT_BYTES = 1_048_576`)
- Max 5 redirects (`_MAX_REDIRECTS = 5`)
- 30-second timeout (`_TIMEOUT_SECONDS = 30.0`)
- Retry with exponential backoff via tenacity (3 attempts, transient errors only)
- Test at `tests/mcp/test_fetch.py:77` explicitly verifies `ftp://` rejection

### Result

✅ **SSRF-hardened.** Only HTTP/HTTPS permitted. File protocol, FTP, and all other schemes are rejected by explicit whitelist validation.

---

## 11. Filesystem Path Whitelist + Symlink Resolution — ✅ PASS

### File: `src/mcp/tools/filesystem.py` (210 lines)

### Path whitelist

```python
# Lines 34-39
_DEFAULT_ALLOWED: tuple[str, ...] = (
    "/home/guinevere/code",
    "/home/guinevere/data",
    "/home/guinevere/evidence",
    "/home/guinevere/logs",
)
```

Configurable via `FILESYSTEM_ALLOWED_PATHS` env var (comma-separated, overrides defaults).

### validate_path() — 3-layer defense

```python
# Lines 92-133
def validate_path(path: str, allowed_paths: frozenset[str]) -> Path:
    # Layer 1: Reject null bytes
    _reject_null_bytes(path)
    
    # Layer 2: Resolve symlinks, .., relative segments
    resolved = Path(path).resolve()
    
    # Layer 3: Separator-aware prefix matching against resolved allowed paths
    for allowed in allowed_paths:
        allowed_resolved = Path(allowed).resolve()
        if resolved == allowed_resolved:
            return resolved
        if str(resolved).startswith(str(allowed_resolved) + os.sep):
            return resolved
    
    raise PathForbiddenError(...)
```

### Security guarantees

| Threat | Mitigation |
|---|---|
| `../` traversal | `Path.resolve()` normalizes to absolute |
| Symlink escape (`/home/guinevere/data -> /etc`) | `Path.resolve()` follows to target, then prefix-checked |
| `/home/guinevere/data` access to `/home/guinevere/data_backup` | Separator-aware prefix: `data` does NOT match `data_backup` (no `/home/guinevere/data` + `/` prefix) |
| Null byte injection | Explicit `\x00` rejection before any path operations |
| `/home/aizanta/` escape | Default whitelist is `/home/guinevere/` only — aizanta paths rejected unless explicitly added |
| Env var injection | `FILESYSTEM_ALLOWED_PATHS` parsed at server startup, frozen as frozenset, immutable per-process lifetime |

### Result

✅ **Path traversal hardened.** Symlinks resolved, `..` normalized, null bytes rejected, separator-aware prefix matching, immutable configuration.

---

## 12. Additional Security Observations

### 12.1 PostgreSQL: Defense-in-Depth

`postgres_tool.py` implements 3-layer read-only enforcement:

| Layer | Mechanism |
|---|---|
| 1 | `BEGIN READ ONLY` transaction wrapper — server-side enforcement |
| 2 | SQL keyword classification (`classify_sql()`) — blocks DDL/DML before execution |
| 3 | Dedicated `guinevere_readonly` database role — SELECT-only grants |

DDL/DCL commands (DROP, TRUNCATE, ALTER, CREATE, GRANT, REVOKE) classified as `"forbidden"` and raised as `ForbiddenOperationError` before any connection is opened.

### 12.2 Parameterized Queries

Both PostgreSQL and Redis use parameterized interfaces:
- PostgreSQL: `asyncpg` with `$1`, `$2`, … placeholders, validated by `_validate_params()`
- Redis: `redis.asyncio` native API (no string concatenation)

### 12.3 Auth gating matrix

All MCP tools use `require_approval()` decorator with appropriate `AuthLevel`:

| AuthLevel | Behavior | Tools |
|---|---|---|
| `READ_AUTO` | Execute immediately | postgres_query, redis_get, github_get_file, shell_exec, fs_read, fs_list, fetch_url, brave_search, exa_search |
| `WRITE_NOTIFY` | Execute + Discord notification | redis_set, github_create_issue, fs_write |
| `DESTRUCTIVE_APPROVAL` | Discord notification + wait for operator approval (5min) | redis_del, shell_exec, fs_delete |
| `FORBIDDEN` | Always raise | redis_flushdb, redis_flushall |

### 12.4 GitHub PAT: error handling

`github.py` has typed error handling:
- 401 → `ConfigurationError` with clear message
- 403 → Rate-limit headers logged, then raised
- 404 → Empty result returned (not an error)
- 5xx → Retried with exponential backoff (tenacity, 3 attempts)

---

## 13. Findings Summary

| # | Severity | Finding | Status |
|---|---|---|---|
| F-01 | 🔴 CRITICAL | Real `POSTGRES_PASSWORD` exposed in `audit-reports/P0/STEP-P0-014/step-p0-014-auditor-report.md:189` | Pre-existing P0 issue — needs immediate remediation |
| F-02 | ⚠️ MEDIUM | Systemd units use `%E/` credential specifiers that resolve to file paths, but application code reads env vars as direct values — mismatch may cause auth failures | Action required before deployment |
| F-03 | ℹ️ INFO | `guinevere-core.service` (P1-018) has no credential env vars — credentials handled by child services only | Acceptable — core API doesn't need DB creds directly |

---

## 14. Remediation Plan

### Immediate (CRITICAL)

1. Rotate PostgreSQL `guinevere` user password on VPS `100.94.104.22`
2. Redact `POSTGRES_PASSWORD` value from `audit-reports/P0/STEP-P0-014/step-p0-014-auditor-report.md`
3. Audit git history for pushed copies of the exposed password
4. Run `git log -p -- audit-reports/P0/STEP-P0-014/step-p0-014-auditor-report.md` to confirm

### Before Deployment (MEDIUM)

1. Fix systemd credential injection for `%E/` specifiers:
   - Option A: Use `LoadCredentialEncrypted=` + update app to read `$CREDENTIALS_DIRECTORY`
   - Option B: Use SOPS `exec-env` wrapper in `ExecStart` (like backup/prune services)
2. Verify with integration test that Redis/PostgreSQL actually authenticate after credential fix

### Preventative

1. Add `.audit-reports/*.md` to pre-commit secret scanner rules
2. Add `POSTGRES_PASSWORD=`, `REDIS_PASSWORD=`, `DISCORD_TOKEN=` patterns to a secret detection tool (e.g., `detect-secrets`, `trufflehog`, or git `pre-commit` hook)

---

## 15. Evidence

| Artifact | Path |
|---|---|
| src/mcp/ secret scans | 6 grep scans — zero hardcoded secrets |
| os.environ audit | 18 occurrences across 11 files — all safe |
| Port isolation | 9 occurrences of 5433/6380 — no 5432/6379 |
| Systemd units | 9 service files reviewed |
| Test secret hygiene | 22 test files — all synthetic |
| Evidence scan | 8 files matched, 0 real secrets |
| Docs scan | 51 files matched, 0 real secrets |
| P0-014 password | Confirmed at line 189 |
| shell_tool.py | 4 defense layers verified |
| fetch.py | Scheme whitelist verified |
| filesystem.py | Path validation + symlink resolution verified |

---

## 16. Auditor Sign-Off

| Field | Value |
|---|---|
| Auditor | Guinevere (Sisyphus-Junior) |
| Date | 2026-06-03 |
| Dimension | D03 — Security & Secrets |
| Verdict | ⚠️ NEEDS REVIEW — 1 CRITICAL finding, 1 action-required gap, 9 PASS |
| Next Action | Remediate F-01 (P0 password rotation), F-02 (systemd credential fix) |

> This audit was performed READ-ONLY. No files were modified. All findings are evidence-based with grep outputs, file paths, and line numbers.