# SQLAlchemy 2.x Model Patterns for PostgreSQL / Multi-Schema / Extensions

**Date:** 2026-06-02
**Scope:** Production patterns for `src/memory/models.py` in Project Guinevere
**Focus:** SQLAlchemy 2.x declarative typing, PostgreSQL types, multi-schema mapping, TimescaleDB, indexes, and cross-schema relationships

## Executive summary

For a production ORM layer targeting PostgreSQL + `asyncpg` + Alembic autogenerate, the recommended baseline is SQLAlchemy 2.x **annotated declarative** style:

- Use `Mapped[T]` + `mapped_column()` for all ORM fields.
- Prefer SQLAlchemy 2.x native types or dialect types (`Uuid`, `JSONB`, `ARRAY`, `BYTEA`, `TSVECTOR`) rather than legacy `Column(...)` style.
- Use explicit schema assignment per model via `__table_args__ = {"schema": "..."}` or a shared `MetaData(schema=...)` default when appropriate.
- Use Alembic `include_schemas=True` and `include_name` filters for multi-schema autogenerate.
- Define PostgreSQL indexes explicitly with `Index(...)`; partial indexes use `postgresql_where=...`, and index method uses `postgresql_using="gin"` / `btree` / etc.
- For TimescaleDB hypertables, create the table with SQLAlchemy, then convert it to a hypertable in migration code or post-DDL SQL; do **not** assume SQLAlchemy has first-class hypertable support.

This matches current SQLAlchemy 2.0 docs and Alembic autogenerate guidance.

---

## 1) SQLAlchemy 2.x `Mapped[]` annotation style

### Recommended style

Use annotated declarative mappings:

```python
from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user_account"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

**Why this style:** SQLAlchemy 2.x docs present `Mapped[...]` + `mapped_column()` as the primary declarative mapping approach, with nullability inferred from typing and ORM-specific configuration carried by `mapped_column()`.

### Old `Column(...)` style

```python
from sqlalchemy import Column, Integer, String

class LegacyUser(Base):
    __tablename__ = "legacy_user"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
```

This still works, but for a new codebase it is not the preferred style when you want full ORM typing and cleaner autogenerate-friendly declarations.

### asyncpg + Alembic autogenerate guidance

Use the 2.x typed declarative style for new models. It is compatible with `asyncpg`, and it is the style SQLAlchemy’s 2.x docs center on for modern ORM mappings. Alembic autogenerate works from `MetaData`, so the main requirement is that your metadata accurately reflects models and schemas.

**Practical recommendation:**
- Use `Mapped[...]` everywhere.
- Use explicit types where PostgreSQL behavior matters.
- Keep defaults/server defaults explicit for Alembic visibility.

**Evidence:**
- SQLAlchemy annotated declarative with `Mapped` and `mapped_column()` is the documented modern style.
- SQLAlchemy notes that mapped columns infer datatype/nullability from `Mapped`.

**Source docs:**
- SQLAlchemy declarative mapping docs: https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html
- SQLAlchemy 2.0 “What’s New” typing section: https://docs.sqlalchemy.org/en/20/changelog/whatsnew_20.html

---

## 2) PostgreSQL-specific types in SQLAlchemy 2.x

### 2.1 UUID type with asyncpg

Prefer SQLAlchemy’s PostgreSQL UUID/Uuid support for UUID primary keys.

```python
import uuid
from uuid import UUID

from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

class Event(Base):
    __tablename__ = "event"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
```

If you want backend-agnostic behavior, SQLAlchemy 2.x also documents the built-in `Uuid` type as the preferred generic UUID type in modern code.

```python
from sqlalchemy import Uuid

id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
```

**Recommendation for Guinevere:** use PostgreSQL UUID when PostgreSQL is the only target; use generic `Uuid` if portability matters.

### 2.2 ARRAY

```python
from sqlalchemy.dialects.postgresql import ARRAY

class TaggableThing(Base):
    __tablename__ = "taggable_thing"

    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
```

You can also rely on type annotations for collection shape, but keep the explicit PostgreSQL `ARRAY(String)` for clarity.

### 2.3 JSON / JSONB

Use `JSONB` for PostgreSQL-first production use when indexing/querying structured payloads.

```python
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

class Document(Base):
    __tablename__ = "document"

    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
```

**Rule of thumb:**
- `JSONB` for PostgreSQL-specific, queryable, indexable JSON payloads.
- `JSON` only when you want plain JSON semantics or portability.

### 2.4 TSVECTOR

SQLAlchemy exposes PostgreSQL `TSVECTOR` for full-text search columns.

```python
from sqlalchemy.dialects.postgresql import TSVECTOR

class SearchDocument(Base):
    __tablename__ = "search_document"

    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)
```

A common production pattern is to populate this via trigger or computed SQL in migrations rather than purely from ORM setters.

### 2.5 BYTEA for encrypted columns

Use PostgreSQL `BYTEA` for encrypted binary payloads.

```python
from sqlalchemy.dialects.postgresql import BYTEA

class SecretValue(Base):
    __tablename__ = "secret_value"

    ciphertext: Mapped[bytes] = mapped_column(BYTEA, nullable=False)
```

If encryption/decryption is handled via `pgcrypto`, the underlying storage type should still be `BYTEA`.

### 2.6 Custom pgvector VECTOR type

For pgvector, use the project’s vector type wrapper/package in your model layer.

```python
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

class Embedding(Base):
    __tablename__ = "embedding"

    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
```

**Production note:** keep the dimension explicit (`1536`) so schema drift is visible to Alembic and reviewable in code.

---

## 3) Multi-schema models

### 3.1 Per-model schema assignment

```python
class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = {"schema": "audit"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
```

Use this when each domain model belongs to a specific PostgreSQL schema.

### 3.2 Default schema configuration

If most tables share one schema, you can set metadata-level default schema:

```python
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    metadata = MetaData(schema="app")
```

This reduces repetition but is less flexible when your app spans many schemas.

### 3.3 Alembic autogenerate with multiple schemas

Configure Alembic with `include_schemas=True`. Use `include_name` to filter schemas/tables so autogenerate does not treat the other schemas as stray objects.

```python
def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name in [None, "app", "memory", "audit"]
    if type_ == "table":
        return parent_names["schema_qualified_table_name"] in target_metadata.tables
    return True

context.configure(
    connection=connection,
    target_metadata=target_metadata,
    include_schemas=True,
    include_name=include_name,
)
```

**Important:** include `None` if you need the default schema.

---

## 4) TimescaleDB hypertable declaration

SQLAlchemy does not provide a native declarative “hypertable” ORM feature. The production pattern is:

1. Declare the table normally in SQLAlchemy.
2. In Alembic migration, run raw SQL to convert it to a hypertable.

### ORM table definition

```python
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

class MetricSample(Base):
    __tablename__ = "metric_sample"
    __table_args__ = {"schema": "telemetry"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

### Migration-time hypertable conversion

```python
from alembic import op

def upgrade():
    op.execute(
        "SELECT create_hypertable('telemetry.metric_sample', 'observed_at', if_not_exists => TRUE)"
    )
```

### Optional partitioning hints

If you need PostgreSQL partitioning instead, use SQLAlchemy table kwargs only where they are supported by the backend and your migration strategy. For TimescaleDB, the hypertable conversion is typically still done with raw SQL.

**Recommendation:** keep TimescaleDB-specific DDL in migrations, not in ORM class bodies.

---

## 5) Index patterns

### 5.1 Basic explicit index

```python
from sqlalchemy import Index

Index("ix_document_created_at", Document.__table__.c.created_at)
```

### 5.2 GIN index for JSONB / arrays / full-text

```python
Index(
    "ix_document_payload_gin",
    Document.__table__.c.payload,
    postgresql_using="gin",
)
```

### 5.3 Partial index

```python
Index(
    "ix_task_active_created_at",
    Task.__table__.c.created_at,
    postgresql_where=Task.__table__.c.deleted_at.is_(None),
)
```

### 5.4 Composite index

```python
Index(
    "ix_task_workspace_status_created_at",
    Task.__table__.c.workspace_id,
    Task.__table__.c.status,
    Task.__table__.c.created_at,
)
```

### 5.5 Production note

Use named indexes and keep them in `__table_args__` or after class definition, so Alembic can render them cleanly and your schema diff stays deterministic.

Example inside model:

```python
class Task(Base):
    __tablename__ = "task"
    __table_args__ = (
        Index("ix_task_workspace_status_created_at", "workspace_id", "status", "created_at"),
        {"schema": "memory"},
    )
```

---

## 6) Foreign key patterns

### 6.1 Cross-schema foreign key

```python
from sqlalchemy import ForeignKey

class Note(Base):
    __tablename__ = "note"
    __table_args__ = {"schema": "memory"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("core.workspace.id"), nullable=False)
```

### 6.2 Relationship across schemas

```python
from sqlalchemy.orm import relationship

class Workspace(Base):
    __tablename__ = "workspace"
    __table_args__ = {"schema": "core"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    notes: Mapped[list[Note]] = relationship(back_populates="workspace")

class Note(Base):
    __tablename__ = "note"
    __table_args__ = {"schema": "memory"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("core.workspace.id"), nullable=False)
    workspace: Mapped[Workspace] = relationship(back_populates="notes")
```

### 6.3 Production cautions

- Use fully-qualified FK strings: `schema.table.column`.
- Ensure the referenced schema/table exists before migrations run.
- Keep relationship declarations symmetric with `back_populates` where bidirectional access is needed.

---

## Recommended implementation choices for `src/memory/models.py`

For Guinevere’s 47 models across 12 schemas, the safest production baseline is:

1. **Declarative 2.x typing everywhere**: `Mapped[...]` + `mapped_column()`.
2. **UUIDs**: `PGUUID(as_uuid=True)` or `Uuid` depending on portability needs.
3. **JSON payloads**: default to `JSONB` for PostgreSQL-specific models.
4. **Embedding vectors**: `Vector(1536)` with explicit dimension.
5. **Encrypted payloads**: `BYTEA`.
6. **Search text**: `TSVECTOR`.
7. **Multi-schema**: explicit `__table_args__ = {"schema": ...}` per class, or shared `MetaData(schema=...)` only for homogeneous groups.
8. **Hypertables**: raw SQL in Alembic migrations.
9. **Indexes**: explicit named indexes, use `postgresql_using` and `postgresql_where` as needed.
10. **Cross-schema FKs**: always fully qualify schema name.

---

## References

- SQLAlchemy annotated declarative mappings: https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html
- SQLAlchemy typing and ORM modernization: https://docs.sqlalchemy.org/en/20/changelog/whatsnew_20.html
- SQLAlchemy PostgreSQL dialect docs: https://docs.sqlalchemy.org/en/20/dialects/postgresql.html
- SQLAlchemy 2.0 schema definition / metadata: https://docs.sqlalchemy.org/20/core/schema.html
- Alembic autogenerate docs: https://alembic.sqlalchemy.org/en/latest/autogenerate.html
- Alembic cookbook for schema-level multi-tenancy: https://alembic.sqlalchemy.org/en/latest/cookbook.html

---

## Evidence snippets gathered

### Modern declarative typing

```python
class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    fullname: Mapped[str | None]
```

### Alembic include_schemas filtering

```python
def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name in [None, "schema_one", "schema_two"]
```

### PostgreSQL partial index

```python
Index("my_index", my_table.c.id, postgresql_where=my_table.c.value > 10)
```

### PostgreSQL BYTEA encrypted type example

```python
class PGPString(TypeDecorator):
    impl = BYTEA
```

### PostgreSQL TSVECTOR mention

```python
from sqlalchemy.dialects.postgresql import TSVECTOR
```

---

## Decision summary

- **Use the SQLAlchemy 2.x typed declarative style** for the entire model file.
- **Prefer PostgreSQL-native types** for schema fidelity and Alembic clarity.
- **Keep TimescaleDB DDL in migrations** rather than model declarations.
- **Use explicit, named indexes** for stable autogenerate output.
- **Use fully-qualified schema FKs** for all cross-schema relations.
