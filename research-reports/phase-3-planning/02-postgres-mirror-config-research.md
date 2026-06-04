# Phase 3 Planning: PostgreSQL Mirror Configuration Research

**Date**: 2026-06-04  
**Context**: Phase 3 Memory Bridge migration. ADR-035 requires PostgreSQL as primary store with Hermes read-only access.  
**Goal**: Define the optimal PostgreSQL read-only mirror/replication architecture, RBAC, RLS, and operational procedures.

---

## 1. PostgreSQL Replication Options for Read-Only Access

For a "mirror sync" providing read-only access to Hermes, there are four primary architectural patterns. **Streaming Replication** is the recommended approach for this use case.

| Option | Mechanism | Pros | Cons | Verdict for Hermes |
|---|---|---|---|---|
| **Streaming Replication** | Byte-for-byte WAL shipping from primary to standby. | Near real-time (sub-ms lag), Hot Standby (read-only queries), exact cluster clone, lowest overhead. | Replicates entire cluster (no per-table filtering), requires same PG major version. | ✅ **Recommended**. True "mirror", simplest operational model for read scaling. |
| **Logical Replication** | Publish/subscribe model decoding WAL into row-level changes. | Per-table granularity, cross-version support, subscriber is independent (can have different indexes). | Higher overhead, does not replicate DDL, historical bug with `pgvector` updates (fixed in v0.5.2+). | ⚠️ Alternative only if Hermes needs a strictly isolated subset of tables. |
| **Foreign Data Wrappers (FDW)** | Queries remote tables as if local via `postgres_fdw`. | No data duplication, real-time reads. | High network overhead per query, no predicate pushdown for complex joins, not a true replica. | ❌ Not suitable for high-volume read scaling. |
| **Periodic Sync (ETL/Cron)** | Batch `pg_dump` or logical dump on a schedule. | Simple to script. | Data staleness, high I/O spikes during sync, not a true "mirror". | ❌ Violates real-time memory bridge requirements. |

**Conclusion**: "Mirror sync" in ADR context implies **Streaming Replication** (Hot Standby). It provides real-time, read-only access with minimal lag and is the industry standard for this pattern.

---

## 2. RBAC Approach: `hermes_memory_bridge` Role

To enforce SELECT-only access securely, use the principle of least privilege. Do not rely solely on connection-level enforcement; combine it with strict RBAC.

```sql
-- 1. Create the dedicated read-only role
CREATE ROLE hermes_memory_bridge LOGIN PASSWORD 'secure_password_here';

-- 2. Limit connection count to prevent resource exhaustion
ALTER ROLE hermes_memory_bridge CONNECTION LIMIT 50;

-- 3. Grant schema usage (mandatory gatekeeper)
GRANT USAGE ON SCHEMA memory TO hermes_memory_bridge;

-- 4. Grant SELECT on all existing tables in the schema
GRANT SELECT ON ALL TABLES IN SCHEMA memory TO hermes_memory_bridge;

-- 5. CRITICAL: Set default privileges for future tables
-- This ensures new tables created by the migration role are automatically readable
ALTER DEFAULT PRIVILEGES FOR ROLE memory_owner IN SCHEMA memory
  GRANT SELECT ON TABLES TO hermes_memory_bridge;

-- 6. Revoke default public access to prevent accidental exposure
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA memory FROM PUBLIC;
```

**Anti-Pattern Warning**: Forgetting `ALTER DEFAULT PRIVILEGES` is the #1 cause of production outages when new tables are added via migrations. The role will silently lack access until manually granted.

---

## 3. PostgreSQL Row-Level Security (RLS) for Multi-Principal Isolation

If the memory store is multi-tenant, RLS is the safest way to guarantee isolation at the database layer, preventing application-layer `WHERE tenant_id = ?` omissions.

```sql
-- 1. Enable RLS on the table
ALTER TABLE memory_events ENABLE ROW LEVEL SECURITY;

-- 2. FORCE RLS (Critical: prevents table owners from bypassing policies)
ALTER TABLE memory_events FORCE ROW LEVEL SECURITY;

-- 3. Create policy using session variable (most performant pattern)
CREATE POLICY tenant_isolation ON memory_events
  USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
```

**Performance & Operational Rules**:
1. **Indexing is mandatory**: Every RLS-protected table must have a composite index starting with `tenant_id` (e.g., `CREATE INDEX idx_tenant_time ON memory_events (tenant_id, created_at);`). Without this, RLS causes sequential scans. Overhead with proper indexing is typically **2-5%**.
2. **Connection Pooling Hazard**: If using PgBouncer in `transaction` pooling mode, the tenant context **must** be set using `SET LOCAL app.current_tenant_id = '...'` *inside* the transaction block. Using `SET SESSION` will leak the tenant context to the next request on the reused connection.
3. **Testing**: Automated tests must explicitly `SET LOCAL ROLE hermes_memory_bridge` and assert cross-tenant data is inaccessible.

---

## 4. pgvector Compatibility with Replication

**Yes, pgvector is fully compatible with PostgreSQL replication.** It uses the standard Write-Ahead Log (WAL), meaning both streaming and logical replication handle vector columns correctly.

**Critical Caveat for Logical Replication**:  
There was a known bug in pgvector versions prior to `v0.5.2` where logical replication of `UPDATE` statements on vector columns would fail with `ERROR: malformed vector literal`.  
- **Mitigation**: Ensure both primary and replica are running pgvector **v0.5.2 or higher** (preferably `v0.6.x` or `v0.7.x`).  
- **Streaming Replication**: Does not suffer from this bug, as it replicates at the block/WAL level, not the logical row level. This is another reason Streaming Replication is preferred for the mirror.

---

## 5. Connection Pooling Best Practices with Read Replicas

| Tool | Architecture | Read Replica Support | Verdict |
|---|---|---|---|
| **PgBouncer** | Lightweight, single-process. | No native load balancing. Requires application-level routing (e.g., libpq `target_session_attrs=prefer-standby`) or external proxy (HAProxy). | ✅ **Recommended** for pure connection multiplexing. Pair with Patroni for HA. |
| **Pgpool-II** | Multi-process middleware. | Native read/write splitting. Parses SQL to route `SELECT` to replicas and writes to primary. | ⚠️ Use only if you specifically need middleware-level query parsing and automated failover. Higher CPU/memory overhead. |

**Recommended Stack for Phase 3**:  
`Application` → `PgBouncer (transaction mode)` → `Patroni-managed Primary + Streaming Replica`.  
Use libpq's `target_session_attrs=read-write` for the primary pool and `target_session_attrs=prefer-standby` for the Hermes read pool.

---

## 6. Monitoring Patterns for Replication Lag Detection

Use `postgres_exporter` with Prometheus and Grafana. Do not rely on manual checks.

**Key Metrics to Scrape**:
- `pg_replication_lag_seconds`: Scraped from the **replica** node. Represents time-based lag.
- `pg_stat_replication_pg_wal_lsn_diff`: Scraped from the **primary** node. Represents lag in bytes per replica.
- `pg_replication_is_replica == 1`: Label to identify replica nodes in Grafana dashboards.

**Recommended Prometheus Alert Rules**:
```yaml
groups:
  - name: postgresql_replication
    rules:
      - alert: PostgreSQLReplicationLagWarning
        expr: pg_replication_lag_seconds > 30
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Replication lag > 30s on {{ $labels.instance }}"
          
      - alert: PostgreSQLReplicationLagCritical
        expr: pg_replication_lag_seconds > 300
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Critical replication lag > 5m on {{ $labels.instance }}"
```

---

## 7. Rollback and Failover Procedures

Replication configuration changes must be reversible. Document and test these procedures before Phase 3 execution.

### Scenario A: Streaming Replication Failover & Switchback
1. **Failover**: If primary fails, promote the replica:  
   `SELECT pg_promote();` or `pg_ctl promote -D /var/lib/postgresql/data`
2. **Switchback (Old Primary returns)**: The old primary's timeline has diverged. Do not just restart it. Use `pg_rewind` to synchronize it with the new primary:  
   `pg_rewind --target-pgdata=/var/lib/postgresql/data --source-server='host=new_primary port=5432 user=rewind_user'`
3. **Reconfigure as Standby**: After rewinding, create `standby.signal` and set `primary_conninfo` in `postgresql.auto.conf` to point to the new primary, then start the service.

### Scenario B: Logical Replication Rollback
1. On subscriber: `DROP SUBSCRIPTION hermes_memory_sub;`
2. On publisher: `DROP PUBLICATION hermes_memory_pub;`
3. No data directory synchronization is required.

**Rule**: Never run `pg_rewind` or `pg_basebackup` on a running target without understanding the timeline divergence. Always test failover in a staging environment that mirrors production data volume.

---

## 8. Clarification: "Mirror Sync" in ADR Context

In PostgreSQL architecture, the term "mirror sync" definitively refers to **real-time Streaming Replication**, not periodic batch synchronization. 

- **Real-time (Streaming)**: WAL records are shipped continuously. Lag is typically sub-second. The replica is immediately available for read-only queries (Hot Standby). This satisfies the Memory Bridge requirement for Hermes to have near-real-time access to memory state.
- **Periodic (Batch)**: Introduces staleness, I/O spikes, and potential data loss windows. It is an anti-pattern for a live AI memory bridge.

**Actionable Directive for Phase 3 Planner**:  
The planner must specify **Streaming Replication** with a dedicated Hot Standby node, configured with the `hermes_memory_bridge` RBAC role, and monitored via `postgres_exporter` lag alerts.

---

## 9. Next Steps for Phase 3 Planner

1. Define the exact `postgresql.conf` parameters for the replica (`hot_standby = on`, `max_standby_streaming_delay = 30s`).
2. Draft the migration script that creates the `hermes_memory_bridge` role and applies `ALTER DEFAULT PRIVILEGES`.
3. Verify `pgvector` version on both primary and target replica nodes (must be ≥ v0.5.2).
4. Update the Phase 3 collision scan to ensure no other sub-agent is modifying `pg_hba.conf` or replication roles concurrently.