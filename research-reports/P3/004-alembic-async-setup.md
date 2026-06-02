# Alembic Async + Multi-Schema PostgreSQL Research

## Scope
Research for best-practice Alembic 1.x setup with SQLAlchemy 2.x async (`asyncpg`) and PostgreSQL multi-schema migrations, including `env.py`, autogenerate, version table placement, and production code examples.

## Primary Findings

### 1) Official Alembic async `env.py` pattern
Alembic’s official cookbook shows that Alembic does **not** expose a native async API, but it can run migrations against an async SQLAlchemy engine via `async_engine_from_config()` and `connection.run_sync()`.

The canonical pattern is:

```python
import asyncio

from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool
from alembic import context


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())
```

This pattern is documented in Alembic’s cookbook and matches the official `async` template in the Alembic repo.

### 2) `create_async_engine` vs `async_engine_from_config`
- **`async_engine_from_config`** is the official Alembic cookbook pattern for `env.py` because it reads from Alembic config (`alembic.ini` / `pyproject.toml`) and preserves template compatibility.
- **`create_async_engine`** is used in Alembic docs primarily for **programmatic** migration invocation from app code, where you already have the URL in Python.

Production guidance:
- Use `async_engine_from_config()` in `env.py`.
- Use `create_async_engine()` only when Alembic is invoked programmatically inside your application or tests and you control the URL in Python.

### 3) Multi-schema PostgreSQL with Alembic
Alembic’s runtime docs explicitly document these knobs:
- `include_schemas=True` makes autogenerate scan all schemas returned by inspector `get_schema_names()`.
- `include_name` should be used to filter schemas/tables **before reflection**.
- `version_table_schema` places the Alembic version table in a specific schema.

Important behavior from the docs:
- `include_schemas=True` alone scans **all** schemas and will often over-detect changes in PostgreSQL installations that include extra schemas such as PostGIS.
- The docs recommend pairing it with `include_name` for schema filtering.

A documented filtering pattern is:

```python
def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name in [None, "schema_one", "schema_two"]
    elif type_ == "table":
        return parent_names["schema_qualified_table_name"] in target_metadata.tables
    else:
        return True

context.configure(
    target_metadata=target_metadata,
    include_name=include_name,
    include_schemas=True,
)
```

### 4) `include_object` vs `include_name`
- **`include_name`** is the preferred hook when the goal is to exclude schemas/tables early, because it avoids reflection of skipped schemas.
- **`include_object`** is still useful for object-level filtering after reflection, but it is less efficient.

For your use case, docs and maintainer guidance strongly indicate:
- Prefer `include_name` for schema-level selection.
- Use `include_object` only for finer-grained object filtering inside included schemas.

### 5) Version table placement
Alembic supports:
- One shared version table in a chosen schema via `version_table_schema=...`
- Separate version tables per schema if you are running migrations independently for each schema/tenant

Official runtime docs expose `version_table_schema`; Alembic internals confirm version table creation uses that schema directly.

Practical guidance from maintainers/issues:
- If you have one application with many explicit schemas and a single migration stream, a **single version table** is usually simpler.
- If you are doing schema-per-tenant and migrating each schema separately, use **one version table per schema**.

### 6) Declarative models and schemas
Production code and issue discussions confirm standard SQLAlchemy 2.x schema declaration patterns:

```python
class MyModel(Base):
    __tablename__ = "my_table"
    __table_args__ = {"schema": "tenant_schema"}
```

Autogenerate works best when:
- tables are explicitly schema-qualified in models where needed,
- default schema handling matches PostgreSQL `search_path`,
- and `include_schemas=True` / `include_name` is aligned with the schema strategy.

Important PostgreSQL caveat from Alembic maintainers:
- If the PostgreSQL `search_path` contains extra schemas or `$user`, tables may reflect as `None` schema or unexpected default schema values.
- Avoid naming `public` explicitly in models if it is the true default schema; rely on default schema behavior unless you have a reason not to.

### 7) Migration for schemas that do not exist yet
Relevant best practice from docs/issues:
- Alembic autogenerate does **not** create missing schemas automatically unless the migration explicitly does so.
- For first migration / bootstrap, the migration should include explicit `op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS ..."))` or dialect-specific `CreateSchema` logic before creating schema-qualified tables.
- For existing databases, the initial revision should usually be a baseline / stamp or a carefully reviewed autogenerate against the live DB.

### 8) Autogenerate best practices
Official docs and changelog notes:
- Run `alembic revision --autogenerate` against a **single, representative schema target** when all schemas are supposed to stay in sync.
- Use `include_name` / `include_schemas` to limit reflection.
- Be careful with default schemas and PostgreSQL `search_path`.
- Migration scripts should remain deterministic and not rely on reflection quirks.

### 9) Error handling patterns
From docs and production discussions, common failure modes include:
- `schema does not exist` → create schema before table creation
- `permission denied for schema` → grant `USAGE`, `CREATE` as needed, or run with a role that owns the schema
- duplicate table/column errors → usually indicate autogenerate scope mismatch, bad schema filtering, or running an initial migration twice without baseline/stamp discipline

Recommended handling:
- Add an explicit bootstrap migration for schema creation.
- Keep autogenerate scope narrow and predictable.
- For pre-existing databases, use `alembic stamp head` after validating schema baseline when appropriate.

## Official Documentation Evidence

### Async migration support
Source: Alembic cookbook
- `Using Asyncio with Alembic`
- `Programmatic API use (connection sharing) With Asyncio`
- `async` template in Alembic repo

Key points:
- `async_engine_from_config()` in `env.py`
- `await connection.run_sync(do_run_migrations)`
- `asyncio.run(run_async_migrations())`

### Multi-schema autogenerate
Source: Alembic runtime/autogenerate docs
- `include_schemas=True` scans all schemas
- `include_name` is recommended for filtering schemas before reflection
- `version_table_schema` places the version table in a chosen schema

## Production Code Evidence from GitHub

### 1) Official Alembic async template
Repo: `sqlalchemy/alembic`
File: `alembic/templates/async/env.py`
Pattern:
- imports `async_engine_from_config`
- defines `do_run_migrations(connection)`
- defines `async def run_async_migrations()`
- calls `asyncio.run(run_async_migrations())`

### 2) `pyproject_async` template
Repo: `sqlalchemy/alembic`
File: `alembic/templates/pyproject_async/env.py`
Same async pattern as above, confirming it is the maintained template path.

### 3) Production FastAPI example
Repo: `fastapi-practices/fastapi-best-architecture`
File: `backend/alembic/env.py`
Observed pattern:
- imports `async_engine_from_config`
- uses `asyncio.run(run_async_migrations())`
- customizes `context.configure()` with `compare_type=True`, `compare_server_default=True`, `transaction_per_migration=True`

This confirms real-world usage of Alembic async env.py in a production FastAPI codebase.

### 4) Production async Alembic startup flow
Repo: `nanotaboada/python-samples-fastapi-restful`
PR evidence shows:
- Alembic with async SQLAlchemy support
- startup migration execution via `alembic upgrade head`
- `alembic/env.py` adapted for async-aware migration execution

### 5) Multi-schema / include hooks evidence
Repo: `sqlalchemy/alembic`
Tests and runtime source confirm:
- `include_schemas` behavior
- `include_name` schema filtering
- `version_table_schema` support

## Recommended Architecture for Guinevere

### Option A — single migration stream, many schemas
Best when:
- 12 schemas are part of one app
- schema models are explicit in SQLAlchemy
- you want one Alembic history

Recommended config:
- `include_schemas=True`
- `include_name` filter to only allow your schemas + default schema
- `version_table_schema` set to a dedicated admin schema or default schema you control
- `__table_args__ = {"schema": "..."}` in each model that is not in the default schema

### Option B — schema-per-tenant migrations
Best when:
- each schema is a copy of the same logical application schema
- you want one version table per schema
- you run Alembic repeatedly with schema context

Recommended config:
- pass schema name using `-x tenant=...`
- switch search path in `env.py`
- set `version_table_schema` to the target tenant schema
- ensure migrations are run once per schema/tenant

## Suggested env.py Shape

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from myapp.models import Base  # or equivalent

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

SCHEMAS = {None, "public", "schema_a", "schema_b"}  # example only


def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name in SCHEMAS
    if type_ == "table":
        return parent_names["schema_qualified_table_name"] in target_metadata.tables
    return True


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,
        compare_type=True,
        compare_server_default=True,
        version_table_schema="alembic_meta",
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())
```

## Notes / Caveats
- Alembic autogenerate is very sensitive to PostgreSQL `search_path`.
- `include_schemas=True` without a filter will often produce noisy diffs in Postgres installations with extension schemas.
- If migration is against existing DBs, baseline/stamp strategy should be defined before generating revisions.
- If some schemas must be excluded forever, encode that in `include_name`, not by post-processing generated scripts.

## Evidence Quality
- Official docs: strong
- Source code in Alembic repo: strong
- Production example from FastAPI project: medium-strong
- GitHub discussions/issues: useful for maintainer guidance and caveats

## Recommended Next Step
Use the official async template as the base, then add `include_schemas=True`, a strict `include_name` filter, and an explicit `version_table_schema` strategy based on whether Guinevere uses a single migration stream or schema-per-tenant model.
