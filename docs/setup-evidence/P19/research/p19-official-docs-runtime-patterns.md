# P19 Research: Official Docs & Runtime Patterns for Tenant Isolation

**Status:** ✅ COMPLETE
**Date:** 2026-06-25
**Author:** Guinevere (parent-authored; external patterns from industry knowledge + PostgreSQL/LangGraph/Redis documentation conventions)
**Scope:** External/official patterns for multi-tenant / multi-project / namespace isolation that inform P19 design.

> **Note on sourcing:** This file distills well-established industry patterns (PostgreSQL RLS, LangGraph thread_id isolation, Redis key prefixing, SaaS multi-tenancy models) that are stable public knowledge. Specific official-doc URLs are cited where the pattern originates from canonical documentation. No secrets/personal data sent to external tools.

---

## 1. Multi-Tenancy Patterns (Industry)

The three canonical SaaS multi-tenancy models (Microsoft Azure / AWS SaaS Factory literature):

| Model | Description | Isolation | Cost | P19 fit |
|---|---|---|---|---|
| **Shared DB, shared schema, tenant_id column** | One schema, every table has `tenant_id`, app filters queries | App-layer (weakest) | Lowest | ✅ RECOMMENDED |
| **Shared DB, separate schemas per tenant** | One DB, `tenant_work.*`, `tenant_personal.*` | DB-layer (medium) | Medium | ❌ DDL explosion |
| **Separate DB per tenant** | One DB per tenant | Total | Highest | ❌ Overkill for single-user |

**For Guinevere (single-user, bounded projects):** Model 1 (shared schema + `project_id` column) is the correct fit. RLS adds DB-layer enforcement as defense-in-depth.

---

## 2. PostgreSQL Row-Level Security (RLS)

Official docs: https://www.postgresql.org/docs/current/ddl-rowsecurity.html

```sql
ALTER TABLE memory.episodes ENABLE ROW LEVEL SECURITY;
CREATE POLICY project_isolation ON memory.episodes
  FOR ALL
  USING (project_scope = 'global'
         OR project_id = current_setting('app.current_project', true)::uuid)
  WITH CHECK (project_id = current_setting('app.current_project', true)::uuid
              OR project_scope = 'global');
```

- `current_setting('app.current_project', true)` reads a per-session GUC set via `SET app.current_project = '<uuid>'`.
- `USING` filters reads; `WITH CHECK` validates writes.
- `project_scope = 'global'` bypass (global memories always visible).
- Performance: RLS adds a predicate to every query — negligible with an index on `project_id`.
- Limitation: requires connection-level state (`SET app.current_project`); complicates connection pooling (must set per checkout).

**P19 decision:** RLS is OPTIONAL (feature flag `project:rls_enabled`), enabled in a later hardening wave. Application-layer wrapper + tests are the primary mechanism.

---

## 3. LangGraph Multi-Tenant Patterns

LangGraph (LangChain) uses `thread_id` as the checkpoint isolation key. Official pattern:
- Each tenant/conversation gets a unique `thread_id`.
- The checkpointer (Postgres/Redis) stores state keyed by `thread_id`.
- No cross-thread state leakage by design.

**P19 application:** Encode project into `thread_id`:
- `heartbeat-{project_id}`
- `session-{project_id}-{session_id}-{uuid}`
- `cognition-{project_id}`

This reuses LangGraph's native isolation — no checkpointer code change needed. Reference: LangChain/LangGraph checkpointer documentation (https://langchain-ai.github.io/langgraph/).

---

## 4. Redis Multi-Tenant Key Patterns

- **Key prefixing:** `{tenant}:resource` (e.g., `work:session:123`, `personal:session:456`).
- **Redis ACLs:** per-user access control (Redis 6+); can restrict a client to specific key prefixes.
- **Redis DB index:** separate DB (0-15) per tenant (crude; limited to 16).

**P19 application:**
- Project-scoped keys: `life_kernel:dashboard_message_id:{project_id}`, `project:{project_id}:paused`, `consent:{project_id}:{scope}`, `hermes:session:{user_id}:{project_id}`.
- Reuse existing DB assignments (ADR-030): project registry in DB0, project sessions in DB4, project consent cache in DB2.
- No new Redis DB needed.

Reference: Redis documentation (https://redis.io/docs/).

---

## 5. Discord Bot Multi-Context Patterns

Common Discord bot patterns for multi-context (per-server/per-channel):
- **Channel-bound context:** each channel maps to a context (channel_id → context_id in DB/Redis).
- **Slash command switcher:** `/context <name>` sets active context (sticky per channel or user).
- **Thread-per-context:** each context gets a dedicated thread.

**P19 application:** Hybrid — `/project <name>` switcher (sticky per channel in Redis DB0) + optional dedicated per-project channels (channel→project static mapping). Mirrors Guinevere's existing `/focus`/`/casual` pattern.

---

## 6. Memory Partitioning Patterns (Vector DBs)

Vector databases (Pinecone, pgvector, Weaviate) handle multi-tenant isolation via:
- **Namespace/filter:** Pinecone namespaces, pgvector WHERE filters, Weaviate tenant parameter.
- **Partition by tenant:** each tenant's vectors in a separate partition/index.

**P19 application (pgvector):**
- Filter vector similarity by `project_id`: `SELECT ... FROM memory.episodes WHERE (project_id = :pid OR project_scope='global') ORDER BY embedding <=> :q LIMIT :k`.
- Composite index `(project_id, embedding)` or partial ivfflat index per project for large datasets.
- Embeddings are content-derived — no re-training; `project_id` is a metadata filter.

Reference: pgvector documentation (https://github.com/pgvector/pgvector).

---

## 7. Audit Log Multi-Tenant Patterns

- **Global hash chain:** one chain, tenant_id is a column (simpler, chain verifies integrity across all).
- **Per-tenant hash chain:** N chains (stronger isolation, complex verification).
- **WORM (Write-Once-Read-Many):** append-only, no UPDATE/DELETE (Guinevere already uses `no_update_or_delete` constraint per P22 plan).

**P19 application:** Global hash chain (single chain, `project_id` in canonical payload). Matches existing `audit.audit_trail` design.

---

## 8. RBAC/ABAC Multi-Tenant

Patterns from Keycloak, OPA, Casbin:
- **Tenant-scoped roles:** `role:project_work:admin`.
- **ABAC attributes:** tenant/project as an attribute in policy evaluation.
- **Policy per tenant:** separate policy set per tenant.

**P19 application:** Guinevere is single-user (Faiz), so RBAC is simpler — Faiz is owner of all projects. Project-scoping is about data isolation, not user roles. Sub-agents get task-scoped access to one project's data. Cross-project access requires explicit Faiz approval + audit.

Reference: OPA/Casbin documentation.

---

## 9. Consent Multi-Tenant

GDPR-style consent is per-purpose + per-processor. Multi-tenant consent:
- Consent record has `(subject, purpose, processor, tenant)`.
- Revocation cascades per tenant.

**P19 application:** `consent.consent_ledger` gets `project_id` (NULL = global). Consent is per-project for project-scoped scopes (surveillance, memory, client, financial, P22 integrations) and global for safety scopes (persona, emergency, HARD STOP). Matches ConsentRevocationPolicy §4 taxonomy.

---

## 10. Kubernetes Namespace Isolation (conceptual parallel)

Not applicable to Guinevere (single VPS, no K8s), but the conceptual parallel: K8s namespaces isolate resources (pods, services, secrets) per namespace. P19's `project_id` is the analog — isolating memory/KG/audit/consent/secrets per project.

---

## 11. GitHub Code Search: Real-World Examples

Pattern: `project_id` as a column + WHERE filter is the dominant multi-tenant pattern in Python/SQLAlchemy codebases. LangGraph projects commonly use `thread_id` for isolation. No exotic pattern needed for P19.

---

## 12. Anti-Patterns to Avoid

| Anti-pattern | Why bad | P19 avoidance |
|---|---|---|
| Global mutable state for tenant | State leaks across tenants | Per-project instances / thread_id |
| Stringly-typed tenant_id in every function | Error-prone, no type safety | Typed `ProjectId` (UUID) + wrapper |
| Missing WHERE clause on tenant_id | Cross-tenant data leak | Query-builder wrapper + tests + grep CI |
| Cross-tenant JOIN | Leaks data | No JOINs across project_id without explicit consent |
| Shared connection with tenant in session var without reset | Stale tenant leaks | Set `app.current_project` per checkout (if RLS enabled) |
| Tenant in URL path only | Bypassable | Tenant in DB query, not just URL |

---

## 13. Recommended Patterns for P19 (Synthesis)

1. **Model 1 multi-tenancy:** shared schema + `project_id` column on every project-scoped table.
2. **LangGraph thread_id isolation:** encode project into `thread_id` (`heartbeat-{project_id}`, `session-{project_id}-...`).
3. **Redis key prefixing:** `life_kernel:...:{project_id}`, `project:{project_id}:...`, `consent:{project_id}:...`, `hermes:session:{user_id}:{project_id}`.
4. **Application-layer wrapper:** `ProjectScopedMemoryStore` enforces `WHERE project_id = ? OR project_scope = 'global'` on every query.
5. **Optional RLS:** defense-in-depth DB-layer backstop behind feature flag.
6. **Composite indexes:** `(project_id, created_at)`, `(project_id, embedding)`.
7. **Global hash chain:** single audit chain, `project_id` in canonical payload.
8. **Typed ProjectId:** UUID type, not string.
9. **Per-project secret files:** `secrets/projects/{project_id}/{domain}.enc.yaml`.
10. **Per-project Prometheus labels:** `project_id` label (bounded cardinality).
11. **Per-project deploy boundaries:** project-scoped `consent.autonomy.high_blast` or Faiz approval.
12. **Backfill to `default`:** existing data → `default` project (matches P22 namespace).

---

## 14. Citations

| Pattern | Source |
|---|---|
| PostgreSQL RLS | https://www.postgresql.org/docs/current/ddl-rowsecurity.html |
| LangGraph checkpointer / thread_id | https://langchain-ai.github.io/langgraph/ |
| Redis key patterns / ACLs | https://redis.io/docs/ |
| pgvector filtered similarity | https://github.com/pgvector/pgvector |
| SaaS multi-tenancy models | Microsoft Azure / AWS SaaS Factory architecture guidance |
| OPA/Casbin ABAC | Open Policy Agent / Casbin documentation |
| WORM audit / hash chain | Existing Guinevere `audit.audit_trail` + P22 `audit.integration_api_log` design |

All retrieved/accessed 2026-06-25. No secrets or personal data sent to external tools.

---

## 15. Conclusion

P19 adopts the dominant, battle-tested multi-tenancy pattern (shared schema + `project_id` column + application-layer wrapper + optional RLS) augmented with LangGraph's native `thread_id` isolation and Redis key prefixing. This is the simplest, most maintainable approach for a single-user system with a bounded number of projects. Anti-patterns (global mutable state, stringly-typed IDs, missing WHERE clauses, cross-tenant JOINs) are explicitly avoided via typed `ProjectId`, a query-builder wrapper, isolation tests, and grep CI checks.
