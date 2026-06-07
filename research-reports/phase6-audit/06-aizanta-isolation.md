# Phase 6 Brutal Audit — Aizanta Isolation

**Verdict: PASS**

## Scope
Audit target: post-ADR-035 Hermes migration isolation, with hard boundary that Guinevere must not touch Aizanta PostgreSQL (5432) or Redis (6379). Canonical Guinevere ports are PostgreSQL `5433` and Redis `6380`.

## Method
I reviewed the requested source/config surfaces and cross-checked the Hermes guard layer and tool implementations for explicit port blocking and canonical-port use.

### Files inspected directly
- `src/mcp/tools/postgres_tool.py`
- `src/mcp/tools/redis_tool.py`
- `hermes-config/config.yaml`
- `hermes-config/hooks/hybrid_guards.py`
- `hermes-config/plugins/auth_overlay/` handlers and plugin docs
- `pyproject.toml`

### Search surfaces scanned for `aizanta`
Case-insensitive search was performed across the repository’s code/config/docs surfaces, including `src/`, `hermes-config/`, `tests/`, `docs/`, `migrations/`, `config/` (absent as a top-level directory), and root docs such as `README.md`, `AGENTS.md`, and `PROGRESS.md`.

## Port isolation findings

### 1) Source code port references

#### `src/mcp/tools/postgres_tool.py`
- Line 10: `Port: 5433 (Guinevere), not 5432 (Aizanta).`
- Lines 94-118: default host/port/database are hardcoded to `localhost`, `5433`, `guinevere`, and `guinevere_readonly`.
- Line 116: explicit comment states `5433 — hardcoded, no env override (Aizanta isolation)`.

**Assessment:** PASS. This tool is pinned to the canonical Guinevere PostgreSQL port and explicitly rejects the Aizanta port in documentation/comments.

#### `src/mcp/tools/redis_tool.py`
- Line 9: `Port: 6380 (non-standard, project config)`.
- Lines 41-44: `_REDIS_PORT = 6380`, `_REDIS_USERNAME = "guinevere_core"`, default DB 5.
- Lines 133-140: Redis client is always created with port `6380`.

**Assessment:** PASS. This tool is pinned to the canonical Guinevere Redis port.

### 2) Guard-layer blocking rules

#### `hermes-config/hooks/hybrid_guards.py`
Relevant lines:
- 9: `Port isolation (block standard 5432/6379, protect canonical 5433/6380)`
- 163-184: explicit standard-port and canonical-port maps/patterns
- 165-166: `5432: "postgresql"`, `6379: "redis"`
- 170-173: canonical Guinevere ports `5433`, `6380`, `20128`
- 178-184: regexes that match host:port, `port = ...`, and `-p ...` forms for `5432` and `6379`
- 586: docstring text describing that the guard blocks PostgreSQL 5432 and Redis 6379 reserved for Aizanta

**Assessment:** PASS. This is an explicit fail-closed port isolation rule set, and it includes the Aizanta standard ports as blocked patterns.

### 3) Auth overlay blocking behavior

#### `hermes-config/plugins/auth_overlay/`
No separate `auth_overlay.py` file exists at the requested path; the overlay is implemented as a package.

Inspected files:
- `__init__.py`
- `auth_handler.py`
- `forbidden_handler.py`
- `approval_handler.py`
- `notify_handler.py`

Findings:
- `__init__.py` lines 17-22 describe `DESTRUCTIVE_APPROVAL → block`, `FORBIDDEN → block`, and fail-closed blocking on unexpected exceptions.
- `auth_handler.py` contains repeated block/fail-closed paths, including:
  - explicit `return None  # Explicitly blocked internal name.`
  - `Unknown — will be blocked fail-closed.`
  - `Operation ... is forbidden.`
  - `Unhandled auth level — blocked for safety.`
- `forbidden_handler.py` returns a consistent `block` action dict for forbidden operations.

**Assessment:** PASS for general blocking posture. However, I did **not** find a port-specific 5432/6379 check inside the auth_overlay package itself from the inspected files. The explicit Aizanta-port enforcement is instead implemented in `hybrid_guards.py`.

### 4) Configuration audit

#### `hermes-config/config.yaml`
Key findings:
- Line 199: canonical ports are documented as `Redis 6380, Postgres 5433, 9Router 20128`.
- No `5432` or `6379` references were found in this config file.
- No `DATABASE_URL` or `REDIS_URL` values were present in this file.

**Assessment:** PASS. The runtime config documents the canonical ports and does not expose Aizanta ports.

#### `pyproject.toml`
- No Aizanta dependency references found.
- Dependencies are standard package/runtime dependencies only.

**Assessment:** PASS.

### 5) Import / dependency scan

#### `src/`
- No Aizanta-specific runtime dependency imports were found in application source.
- Remaining `aizanta` matches in source are isolation-related path blockers inside `src/mcp/tools/shell_tool.py` and `src/mcp/tools/filesystem.py`, which are defensive controls, not functional Aizanta dependencies.

**Assessment:** PASS.

## Aizanta reference inventory by classification

Below are the meaningful `aizanta` references I found in the audited runtime surfaces and their classification.

| File | Line(s) | Snippet | Classification | Impact |
|---|---:|---|---|---|
| `src/mcp/tools/postgres_tool.py` | 10, 94-118 | Port 5433, not 5432 | DOCUMENTATION / CONFIG_FALLBACK | Safe canonical-port pinning |
| `src/mcp/tools/redis_tool.py` | 9, 41-44, 133-140 | Port 6380 only | DOCUMENTATION / CONFIG_FALLBACK | Safe canonical-port pinning |
| `src/mcp/tools/shell_tool.py` | 89-96 | `/home/aizanta`, `/etc/aizanta`, etc. blocked | CODE_DEPENDENCY (defensive guard) | Safe isolation enforcement |
| `src/mcp/tools/filesystem.py` | 82-85 | `/home/aizanta`, `/etc/aizanta`, etc. blocked | CODE_DEPENDENCY (defensive guard) | Safe isolation enforcement |
| `hermes-config/hooks/hybrid_guards.py` | 9, 163-184, 586 | Block 5432/6379, protect 5433/6380 | CODE_DEPENDENCY | Critical pass/fail boundary control |
| `hermes-config/config.yaml` | 199 | `Redis 6380, Postgres 5433, 9Router 20128` | DOCUMENTATION | Canonical-port declaration |
| `hermes-config/plugins/auth_overlay/*` | various | block/fail-closed handlers | HISTORICAL_COMMENT / DOCUMENTATION | General safety posture; no port-specific Aizanta dependency found |

## Verdict rationale

**PASS** because:
1. Canonical Guinevere ports are consistently pinned to `5433` and `6380` in the runtime code.
2. The explicit port-blocking guard in `hermes-config/hooks/hybrid_guards.py` blocks the Aizanta ports `5432` and `6379`.
3. No runtime config surfaced an Aizanta `DATABASE_URL`/`REDIS_URL` override or a direct Aizanta dependency in `pyproject.toml`.
4. `auth_overlay` is fail-closed and blocks forbidden operations, but the actual port isolation is implemented in the guard layer, which is correct for this boundary.

## VPS audit status
I did **not** execute `ss -tlnp` or SSH-based checks because no SSH credentials were provided in this session and the task explicitly says not to SSH if credentials are unavailable.

**Result:** Not executed / N/A for this audit run.

## Conclusion
Guinevere’s runtime code and Hermes guard layer show zero functional touch to Aizanta PostgreSQL/Redis ports. The isolation boundary is enforced by explicit blocking of `5432` and `6379`, while Guinevere’s own tools are pinned to `5433` and `6380`.

**Final verdict: PASS**
