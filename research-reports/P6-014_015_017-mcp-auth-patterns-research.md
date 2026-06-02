# Research Report: MCP Server Auth Patterns for Database Access

**Date**: 2026-06-02
**Scope**: P6-014 (PostgreSQL Read-Auto), P6-015 (Redis Write-Notify), P6-017 (Docker Write-Notify)
**Status**: COMPLETE

---

## 1. PostgreSQL MCP — Read-Only Patterns (P6-014)

### 1.1 Key Implementations Found

| Repository | Stars | Approach | Language |
|---|---|---|---|
| `crystaldba/postgres-mcp` | 2,830 | pglast AST parsing + read-only transactions | Python |
| `musaddiq-dev/postgresql-mcp-server` | New | Dual read/write tools with transaction mode | Python |
| `Makpowr/postgres-mcp` | New | Read-only by design, multi-host failover | Python |
| `leduardoaraujo/postgressql-mcp` | New | Session-level read-only + SQL validator | Python |
| `muham-2002/postgresql-read-mcp` | New | Strict session READ ONLY + keyword blocklist | Python |
| `jplwunder/postgres-mcp-server` | New | Connection pool + readonly transactions | Python |
| `mcp-postgres-server` (PyPI) | Package | Denylist + parameterized queries + `ALLOW_WRITE` gate | Python |
| `JaviMaligno/postgres_mcp` | Stable | `ALLOW_WRITE_OPERATIONS` env flag | Python/TS |
| `stuzero/pg-mcp-server` | Enhanced | SSE transport + connection ID + read-only default | Python |

### 1.2 Read-Only Enforcement — Defense in Depth (3 Layers)

#### Layer 1: PostgreSQL Transaction-Level Read-Only

The **primary defense** used across all implementations:

```python
# crystaldba/postgres-mcp — sql_driver.py
# Source: https://github.com/crystaldba/postgres-mcp/blob/main/src/postgres_mcp/sql/sql_driver.py

async def _execute_with_connection(self, connection, query, params, force_readonly):
    async with connection.cursor(row_factory=dict_row) as cursor:
        if force_readonly:
            await cursor.execute("BEGIN TRANSACTION READ ONLY")
            transaction_started = True
        # ... execute query ...
        if transaction_started:
            await cursor.execute("ROLLBACK")  # Always rollback for read-only
```

**Pattern**: `BEGIN TRANSACTION READ ONLY` forces PostgreSQL to reject any DML/DDL at the database level. Even if the query validator is bypassed, PostgreSQL itself prevents writes.

#### Layer 2: SQL AST Parsing (crystaldba — pglast)

```python
# crystaldba/postgres-mcp — safe_sql.py
# Source: https://github.com/crystaldba/postgres-mcp/blob/main/src/postgres_mcp/sql/safe_sql.py

ALLOWED_STMT_TYPES: ClassVar[set[type]] = {
    SelectStmt,           # Regular SELECT
    ExplainStmt,          # EXPLAIN SELECT
    CreateExtensionStmt,   # CREATE EXTENSION (whitelisted)
    VariableShowStmt,      # SHOW statements
    VacuumStmt,           # VACUUM and ANALYZE
    PrepareStmt,          # PREPARE statement
    DeallocateStmt,       # DEALLOCATE statement
    DeclareCursorStmt,    # DECLARE CURSOR
    ClosePortalStmt,      # CLOSE cursor
    FetchStmt,            # FETCH cursor results
}

def _validate(self, query: str) -> None:
    parsed = pglast.parse_sql(query)
    for stmt in parsed:
        if isinstance(stmt, RawStmt):
            if not isinstance(stmt.stmt, tuple(self.ALLOWED_STMT_TYPES)):
                raise ValueError("Only SELECT, ANALYZE, VACUUM, EXPLAIN, SHOW and other read-only statements are allowed")
        self._validate_node(stmt)  # Recursive tree validation

def _validate_node(self, node: Node) -> None:
    # 1. Check node type is allowed
    if not isinstance(node, tuple(self.ALLOWED_NODE_TYPES)):
        raise ValueError(f"Node type {type(node)} is not allowed")
    # 2. Validate function calls against ALLOWED_FUNCTIONS whitelist (600+ functions)
    if isinstance(node, FuncCall):
        func_name = ".".join([str(n.sval) for n in node.funcname]).lower()
        if unqualified_name not in self.ALLOWED_FUNCTIONS:
            raise ValueError(f"Function {func_name} is not allowed")
    # 3. Reject SELECT with locking clauses (FOR UPDATE)
    if isinstance(node, SelectStmt) and getattr(node, "lockingClause", None):
        raise ValueError("Locking clause on select is prohibited")
    # 4. Reject EXPLAIN ANALYZE (modifies stats)
    # 5. Recursively validate all child nodes
```

**Key insight**: This implementation uses `pglast` (libpg_query Python binding) for proper AST parsing — not regex. It whitelists 600+ safe functions and rejects everything else at the parse-tree level.

#### Layer 3: Session-Level Configuration

```python
# muham-2002/postgresql-read-mcp
# Session-level enforcement:
SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY
SET statement_timeout = '10s'
SET idle_in_transaction_session_timeout = '30s'
```

#### Layer 4: Regex/Keyword Validation (simpler approach)

```typescript
// rohitkapoorfriend/mcp-database-server — query-validator.ts
// Source: https://github.com/rohitkapoorfriend/mcp-database-server/blob/main/src/safety/query-validator.ts

const WRITE_KEYWORDS = [
  "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
  "CREATE", "REPLACE", "MERGE", "UPSERT", "GRANT", "REVOKE",
  "EXEC", "EXECUTE", "CALL", "RENAME", "LOCK", "UNLOCK",
] as const;

const INJECTION_PATTERNS: RegExp[] = [
  /;\s*(DROP|ALTER|DELETE|INSERT|UPDATE|CREATE|TRUNCATE|GRANT|REVOKE)/i,
  /--\s*$/m,
  /\/\*[\s\S]*?\*\//,
  /\bUNION\b[\s\S]*?\bSELECT\b[\s\S]*?\bFROM\b[\s\S]*?\binformation_schema\b/i,
  /\bSLEEP\s*\(/i,
  /\bPG_SLEEP\s*\(/i,
  /\bxp_cmdshell\b/i,
];

export function validateQuery(query: string, allowWrite: boolean): ValidationResult {
  if (!allowWrite) {
    const normalized = stripStringsAndComments(trimmed);
    for (const keyword of WRITE_KEYWORDS) {
      const regex = new RegExp(`\\b${keyword}\\b`, "i");
      if (regex.test(normalized)) {
        return { valid: false, error: `Write operations are not allowed.` };
      }
    }
    // Ensure starts with SELECT/WITH/EXPLAIN/SHOW
    const firstWord = normalized.trim().split(/\s+/)[0]?.toUpperCase();
    if (!["SELECT", "WITH", "EXPLAIN", "SHOW"].includes(firstWord)) {
      return { valid: false, error: `Only SELECT queries are allowed.` };
    }
  }
}
```

### 1.3 Recommended DB Role Setup

```sql
-- Dedicated read-only role for MCP server
CREATE ROLE mcp_reader WITH LOGIN PASSWORD 'secret';
GRANT CONNECT ON DATABASE app_db TO mcp_reader;
GRANT USAGE ON SCHEMA public TO mcp_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mcp_reader;
```

### 1.4 SQL Injection Prevention Patterns

**CVE lessons from MCP servers** (Akamai 2026-05-12 report):
- CVE-2025-66335: Apache Doris MCP — `db_name` parameter was not validated, allowing SQL injection through stacked queries
- CVE-2026-7591: astro-mcp-server — `request.params.arguments` concatenated directly into SQL
- MCP official SQLite server: `table_name` interpolated via f-string in PRAGMA query

**Defense-in-depth checklist for Guinevere**:
1. **Parameterized queries** — never string interpolation (use `$1, $2` with asyncpg)
2. **AST validation** — pglast parsing to whitelist allowed statement types
3. **Transaction READ ONLY** — database-level enforcement
4. **Identifier validation** — regex `^[a-zA-Z_][a-zA-Z0-9_]*$` for table/column names
5. **String stripping** — strip string literals before keyword checking
6. **Error sanitization** — never return raw SQL errors or DSN to MCP client
7. **Row limits** — `MAX_ROWS` cap (default 1000)
8. **Query timeout** — `statement_timeout` + `idle_in_transaction_session_timeout`
9. **Dedicated DB role** — PostgreSQL-level SELECT-only permission

### 1.5 asyncpg Read-Only Connection Pattern

```python
# asyncpg supports read-only via transaction() and connection target_session_attrs
import asyncpg

# Option 1: Read-only transaction
async with conn.transaction(readonly=True):
    result = await conn.fetch("SELECT * FROM users WHERE id = $1", user_id)

# Option 2: Session-level read-only (on connect)
conn = await asyncpg.connect(
    dsn="postgresql://mcp_reader:pass@localhost/db",
    server_settings={
        "default_transaction_read_only": "on",
        "statement_timeout": "10000",  # 10s
    }
)

# Option 3: Connection pool with read-only target
pool = await asyncpg.create_pool(
    dsn="postgresql://mcp_reader:pass@localhost/db",
    min_size=1, max_size=5,
    server_settings={"default_transaction_read_only": "on"},
)
async with pool.acquire() as conn:
    async with conn.transaction(readonly=True):
        rows = await conn.fetch("SELECT * FROM table LIMIT $1", max_rows)
```

**asyncpg `target_session_attrs`** (from connect_utils.py source):
```python
# Source: https://github.com/MagicStack/asyncpg/blob/master/asyncpg/connect_utils.py
class SessionAttribute(str, enum.Enum):
    any = 'any'
    primary = 'primary'
    standby = 'standby'
    prefer_standby = 'prefer-standby'
    read_write = "read-write"
    read_only = "read-only"   # Connect to standby/read-only server
```

---

## 2. Redis MCP — Command Whitelist Patterns (P6-015)

### 2.1 Key Implementations Found

| Repository | Approach | Auth Model |
|---|---|---|
| `redis/mcp-redis` (official) | Full Redis MCP, ACL-based auth | Redis server-side ACL |
| `daedalus/mcp-redis-server` | Exposes all Redis commands as tools | No built-in auth levels |
| `@liangshanli/mcp-server-redis` | Permission-based tool visibility | Env flags: ALLOW_INSERT/UPDATE/DELETE/CREATE/DROP |
| `wenit/redis-mcp-server` | 18 tools + universal `execute` | SCAN-based key lookup (no KEYS) |

### 2.2 Redis ACL — Server-Side Command Whitelist

The **official `redis/mcp-redis`** delegates auth to Redis server ACL:

```bash
# Redis ACL: read-only user
ACL SETUSER readonlyuser on >mypassword ~* +@read -@write

# Redis ACL: app user with read/write but no dangerous commands
ACL SETUSER appuser on >secretpassword ~app:* +@read +@write -@dangerous

# Redis ACL: queue worker with specific list commands only
ACL SETUSER queue_worker on >queuepass ~queue:* ~job:* \
    +lpush +rpush +lpop +rpop +brpop +blpop +llen +lrange +@connection
```

**ACL categories** (from Redis docs):
- `@read` — GET, HGET, LRANGE, etc.
- `@write` — SET, DEL, HSET, etc.
- `@admin` — CONFIG, SHUTDOWN, etc.
- `@dangerous` — FLUSHDB, FLUSHALL, KEYS, DEBUG, etc.
- `@all` — everything

**Redis 7.0 selectors** for fine-grained key access:
```bash
# Read all keys, write only to specific prefix
ACL SETUSER mixedaccess on >mixedpass %R~* %W~writable:* +@all -@admin -@dangerous
```

### 2.3 MCP-Level Command Whitelist (Application Layer)

**@liangshanli/mcp-server-redis** — env-flag based permission model:

```
# Environment configuration
ALLOW_INSERT=true     # SET, MSET, HSET, etc.
ALLOW_UPDATE=true     # SET (overwrite), INCR, DECR
ALLOW_DELETE=true     # DEL
ALLOW_CREATE=true     # Create new keys
ALLOW_DROP=false      # BLOCK: DROP/RENAME operations
```

Tools are **conditionally exposed** based on permissions:
- `get_data`, `list_keys`, `exists_key` → always available (read)
- `set_data` → requires `ALLOW_INSERT=true`
- `update_data` → requires `ALLOW_UPDATE=true`
- `delete_data` → requires `ALLOW_DELETE=true`
- `create_key` → requires `ALLOW_CREATE=true`
- `drop_key` → requires `ALLOW_DROP=true`
- `rename_key` → requires BOTH `ALLOW_CREATE=true` AND `ALLOW_DROP=true`

### 2.4 Recommended Guinevere Auth Levels for Redis

| Command | Auth Level | Rationale |
|---|---|---|
| GET, MGET, HGET, HGETALL | Read-Auto | Pure read, no side effects |
| LRANGE, LLEN, SCARD, SMEMBERS | Read-Auto | Read-only collection inspection |
| KEYS, SCAN | Read-Auto | Key discovery (SCAN preferred over KEYS) |
| TYPE, TTL, EXISTS, DBSIZE | Read-Auto | Metadata inspection |
| SET, HSET, LPUSH, RPUSH, SADD | Write-Notify | Data modification, log + notify |
| INCR, DECR, EXPIRE, PEXPIRE | Write-Notify | State modification |
| DEL, UNLINK | Write-Approval | Key deletion, requires explicit approval |
| RENAME | Write-Approval | Key rename (potential data loss) |
| FLUSHDB, FLUSHALL | **FORBIDDEN** | Nuclear option, never allow |
| CONFIG SET, DEBUG, SHUTDOWN | **FORBIDDEN** | Server administration |
| SCRIPT, EVAL, MULTI/EXEC | Write-Approval | Complex operations |

### 2.5 redis-py ACL Integration

```python
import redis

# Connect with ACL-restricted user
client = redis.Redis(
    host='localhost',
    port=6379,
    username='mcp_user',
    password='secret',
    decode_responses=True
)

# ACL enforcement happens server-side:
try:
    client.set('key', 'value')  # Fails if user lacks @write
except redis.exceptions.NoPermissionError as e:
    logger.warning(f"Redis ACL denied: {e}")

# Programmatic ACL management (admin only)
admin_client = redis.Redis(host='localhost', port=6379, username='admin', password='admin_pass')
admin_client.acl_setuser(
    'mcp_user',
    enabled=True,
    passwords=['>secret'],
    categories=['+@read', '+@connection', '-@dangerous'],
    keys=['guinevere:*'],
)

# Test permissions without executing
admin_client.execute_command('ACL', 'DRYRUN', 'mcp_user', 'GET', 'guinevere:test')
```

---

## 3. Docker MCP — Operation-Based Auth Patterns (P6-017)

### 3.1 Key Implementations Found

| Repository | Safety Model | Key Feature |
|---|---|---|
| `williajm/mcp_docker` | **3-tier safety classification** | Safe/Moderate/Destructive with env flags |
| `ckreiling/mcp-server-docker` | No built-in safety levels | Natural language compose |
| `xiispace/docker-mcp` | Token auth for SSE | MCP_AUTH_TOKEN |
| `cevatkerim/docker-mcp` | Resource limits + isolation | Memory/CPU/PID limits, network isolation |
| `misanthropic-ai/python-docker-mcp` | Sandbox execution | Read-only containers, network disabled |
| `Knuckles-Team/container-manager-mcp` | Enterprise-grade | Eunomia policies, OIDC, ACP |
| `docker-mcp-server` (PyPI) | Basic | Compose + container lifecycle |

### 3.2 williajm/mcp_docker — 3-Tier Safety Classification

**The most relevant pattern for Guinevere's auth-level model:**

| Level | Description | Default | Operations |
|---|---|---|---|
| **Safe** | Read-only operations | Always allowed | list, inspect, logs, stats |
| **Moderate** | Reversible state changes | Allowed (configurable) | create, start, stop, restart, exec, pull |
| **Destructive** | Permanent changes | **Blocked** (configurable) | remove, prune |

**Configuration:**
```bash
ALLOW_MODERATE_OPERATIONS=true          # default: true
SAFETY_ALLOW_DESTRUCTIVE_OPERATIONS=false  # default: false
```

**Tool classification table:**

| Tool | Safety Level |
|---|---|
| `docker_list_containers` | Safe |
| `docker_inspect_container` | Safe |
| `docker_logs` | Safe |
| `docker_stats` | Safe |
| `docker_create_container` | Moderate |
| `docker_start_container` | Moderate |
| `docker_stop_container` | Moderate |
| `docker_restart_container` | Moderate |
| `docker_exec_command` | Moderate |
| `docker_remove_container` | **Destructive** |

**Built-in security features**: rate limiting, audit logging, IP filtering, OAuth support, error sanitization, and command injection validation.

### 3.3 Container Security Patterns

**cevatkerim/docker-mcp** — Resource isolation:
```python
# Container security constraints
DOCKER_MCP_MEMORY_LIMIT = 2147483648  # 2GB
DOCKER_MCP_CPU_LIMIT = 2.0           # 2 cores
DOCKER_MCP_PIDS_LIMIT = 1024         # Max processes
DOCKER_MCP_TIMEOUT = 60              # Default timeout
# Network: isolated by default, opt-in
```

**misanthropic-ai/python-docker-mcp** — Sandbox config:
```yaml
image: python:3.12.2-slim
working_dir: /app
memory_limit: 256m
cpu_limit: 0.5
timeout: 30
network_disabled: true     # Network isolation
read_only: true            # Read-only filesystem
```

**xiispace/docker-mcp** — Token auth for SSE transport:
```bash
MCP_AUTH_TOKEN=your_secret_token
# SSE endpoint becomes /sse/{token} — must match token
```

### 3.4 Recommended Guinevere Auth Levels for Docker

| Operation | Auth Level | Safety Tier |
|---|---|---|
| list_containers | Read-Auto | Safe |
| inspect_container | Read-Auto | Safe |
| get_container_logs | Read-Auto | Safe |
| container_stats | Read-Auto | Safe |
| list_images | Read-Auto | Safe |
| list_networks | Read-Auto | Safe |
| list_volumes | Read-Auto | Safe |
| start_container | Write-Notify | Moderate |
| stop_container | Write-Notify | Moderate |
| restart_container | Write-Notify | Moderate |
| create_container | Write-Approval | Moderate (review params) |
| pull_image | Write-Notify | Moderate |
| exec_in_container | Write-Approval | Moderate (arbitrary code) |
| remove_container | Write-Approval | Destructive |
| remove_image | Write-Approval | Destructive |
| prune_containers | **FORBIDDEN** | Destructive |
| prune_images | **FORBIDDEN** | Destructive |

---

## 4. Cross-Cutting Patterns

### 4.1 Common MCP Tool Auth Architecture

```
┌────────────────────────────────────────────────────┐
│                  MCP Client (Claude/Guinevere)       │
│                    calls tool()                       │
└─────────────────┬──────────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────────┐
│              Auth Gateway Layer                      │
│  1. Check operation → auth level mapping             │
│  2. Read-Auto: execute immediately                   │
│  3. Write-Notify: log + execute + notify operator    │
│  4. Write-Approval: require explicit consent         │
│  5. FORBIDDEN: reject immediately                    │
└─────────────────┬──────────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────────┐
│           Validation Layer                           │
│  PostgreSQL: pglast AST + READ ONLY transaction     │
│  Redis: command whitelist + ACL user                │
│  Docker: operation classification + resource limits  │
└─────────────────┬──────────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────────┐
│           Execution Layer                            │
│  Parameterized queries / ACL-restricted client /    │
│  Docker SDK with safety constraints                 │
└─────────────────┬──────────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────────┐
│           Audit & Response Layer                     │
│  Log operation, sanitize errors, return results     │
│  Never expose DSN/credentials/stack traces          │
└────────────────────────────────────────────────────┘
```

### 4.2 Error Sanitization Pattern (Universal)

```python
# crystaldba/postgres-mcp — sql_driver.py
def obfuscate_password(text: str) -> str:
    # Replace passwords in URLs, DSN strings, connection parameters
    url_pattern = re.compile(r"(postgres(?:ql)?:\/\/[^:]+:)([^@]+)(@[^\s]+)")
    text = re.sub(url_pattern, r"\1****\3", text)
    param_pattern = re.compile(r'(password=)([^\s&;"\']+)', re.IGNORECASE)
    text = re.sub(param_pattern, r"\1****", text)
    return text
```

### 4.3 MCP Tool Registration Pattern

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("guinevere-postgres")

@mcp.tool()
async def pg_query(sql: str, params: list | None = None) -> dict:
    """Execute a read-only SELECT query."""
    # 1. Validate query (AST parse + keyword check)
    # 2. Execute within READ ONLY transaction
    # 3. Enforce row limit
    # 4. Sanitize errors
    # 5. Return structured result
    ...

@mcp.tool()
async def pg_execute(sql: str, params: list | None = None) -> dict:
    """Execute a write statement (requires approval)."""
    # 1. Check ALLOW_WRITE flag
    # 2. Block forbidden patterns (DROP DATABASE, ALTER SYSTEM)
    # 3. Log + notify operator
    # 4. Execute with COMMIT
    ...
```

---

## 5. Implementation Recommendations for Guinevere

### 5.1 PostgreSQL MCP (P6-014)

- **Use psycopg3** (psycopg + psycopg_pool) — crystaldba/postgres-mcp uses it with AsyncConnectionPool
- **Layer 1**: `BEGIN TRANSACTION READ ONLY` for all read tools
- **Layer 2**: pglast AST parsing with `SafeSqlDriver` pattern (whitelist 600+ safe functions)
- **Layer 3**: Dedicated `mcp_reader` PostgreSQL role with only SELECT grants
- **Layer 4**: Parameterized queries only — `$1, $2` syntax, never string interpolation
- **Row cap**: `POSTGRES_READ_QUERY_LIMIT` env var (default 1000)
- **Timeouts**: `statement_timeout=10s`, `idle_in_transaction_session_timeout=30s`
- **Write tool**: Separate `pg_execute_write` tool that requires Write-Approval auth level
- **Denylist**: Even with write enabled, block `DROP DATABASE`, `ALTER SYSTEM`, `REINDEX`

### 5.2 Redis MCP (P6-015)

- **Server-side**: Create ACL user with `+@read +@write -@dangerous -flushall -flushdb`
- **Application-side**: Command classification dict mapping each Redis command to auth level
- **Read-Auto**: GET, MGET, HGET, LRANGE, LLEN, SCAN, TYPE, TTL, EXISTS, DBSIZE, INFO
- **Write-Notify**: SET, HSET, LPUSH, RPUSH, SADD, INCR, DECR, EXPIRE
- **Write-Approval**: DEL, UNLINK, RENAME
- **FORBIDDEN**: FLUSHALL, FLUSHDB, CONFIG SET, DEBUG, SHUTDOWN, SCRIPT LOAD
- **Key prefix**: Restrict to `guinevere:*` key pattern via ACL
- **Use SCAN not KEYS**: Never block the server with KEYS command

### 5.3 Docker MCP (P6-017)

- **Use docker SDK** (`docker>=7.1.0`) — `docker.from_env()` or explicit base_url
- **3-tier classification**: Safe/Moderate/Destructive (from williajm/mcp_docker)
- **Read-Auto (Safe)**: list, inspect, logs, stats, list_images, list_networks, list_volumes
- **Write-Notify (Moderate)**: start, stop, restart, pull
- **Write-Approval (Moderate+Review)**: create_container, exec_in_container
- **Write-Approval (Destructive)**: remove_container, remove_image
- **FORBIDDEN**: prune_containers, prune_images, prune_volumes
- **Resource limits**: memory_limit, cpu_limit, pids_limit on any created container
- **Network isolation**: `network_disabled=True` by default for created containers
- **Container labels**: All MCP-managed containers labeled `mcp-managed=true`

---

## 6. Sources

### PostgreSQL MCP
1. `crystaldba/postgres-mcp` — https://github.com/crystaldba/postgres-mcp (2,830 stars, MIT)
2. `musaddiq-dev/postgresql-mcp-server` — https://github.com/musaddiq-dev/postgresql-mcp-server
3. `Makpowr/postgres-mcp` — https://github.com/Makpowr/postgres-mcp
4. `leduardoaraujo/postgressql-mcp` — https://github.com/leduardoaraujo/postgressql-mcp
5. `muham-2002/postgresql-read-mcp` — https://github.com/muham-2002/postgresql-read-mcp
6. `jplwunder/postgres-mcp-server` — https://github.com/jplwunder/postgres-mcp-server
7. `mcp-postgres-server` (PyPI) — https://pypi.org/project/mcp-postgres-server/
8. `JaviMaligno/postgres_mcp` — https://github.com/JaviMaligno/postgres_mcp
9. `stuzero/pg-mcp-server` — https://github.com/stuzero/pg-mcp-server

### Redis MCP
10. `redis/mcp-redis` (official) — https://github.com/redis/mcp-redis
11. `daedalus/mcp-redis-server` — https://github.com/daedalus/mcp-redis-server
12. `@liangshanli/mcp-server-redis` — https://registry.npmjs.org/@liangshanli/mcp-server-redis
13. `wenit/redis-mcp-server` — https://github.com/wenit/redis-mcp-server

### Docker MCP
14. `williajm/mcp_docker` — https://github.com/williajm/mcp_docker
15. `ckreiling/mcp-server-docker` — https://github.com/ckreiling/mcp-server-docker
16. `xiispace/docker-mcp` — https://github.com/xiispace/docker-mcp
17. `cevatkerim/docker-mcp` — https://github.com/cevatkerim/docker-mcp
18. `misanthropic-ai/python-docker-mcp` — https://github.com/misanthropic-ai/python-docker-mcp
19. `Knuckles-Team/container-manager-mcp` — https://github.com/knuckles-team/container-manager-mcp
20. `docker-mcp-server` (PyPI) — https://pypi.org/project/docker-mcp-server/

### SQL Injection & Security
21. OWASP SQL Injection Prevention Cheat Sheet — https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
22. Akamai MCP Back-End Vulnerabilities — https://www.akamai.com/blog/security-research/one-fluke-3-pattern-mcp-back-end-vulnerabilities
23. MCP SQLite SQL Injection PR — https://github.com/modelcontextprotocol/servers/pull/3663
24. CVE-2026-7591 astro-mcp-server — https://www.sentinelone.com/vulnerability-database/cve-2026-7591/
25. `rohitkapoorfriend/mcp-database-server` — https://github.com/rohitkapoorfriend/mcp-database-server
26. `chandraprvkvsh/Query-MCP` — https://github.com/chandraprvkvsh/Query-MCP

### Driver & SDK Documentation
27. asyncpg documentation — https://magicstack.github.io/asyncpg/current/
28. asyncpg connect_utils.py — https://github.com/MagicStack/asyncpg/blob/master/asyncpg/connect_utils.py
29. Redis ACL documentation — https://redis.io/docs/latest/operate/oss_and_stack/management/security/acl/
30. redis-py ACL commands — https://redis.readthedocs.io/en/stable/commands.html
31. Docker SDK for Python — https://docker-py.readthedocs.io/en/stable/
32. Redis ACL Policies — https://oneuptime.com/blog/post/2026-01-30-redis-acl-policies/view
