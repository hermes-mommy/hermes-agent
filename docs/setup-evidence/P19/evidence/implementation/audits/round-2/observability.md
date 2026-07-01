# P19 Round-2 Observability Audit

Auditor: p19-observability-auditor
Date: 2026-06-26

---

## 1. src/loops/metrics.py — Prometheus metrics have project_id label

**PASS**

All three metric families carry `project_id`:

| Metric | Line | Labels |
|--------|------|--------|
| `guinevere_loop_events_total` | L21-25 | `event_type`, `project_id` |
| `guinevere_loop_cycles_total` | L27-31 | `project_id` |
| `guinevere_loop_phase_duration_seconds` | L33-38 | `phase`, `project_id` |

Observer helpers (`observe_loop_event` L47, `observe_loop_cycle` L52, `observe_phase_duration` L57) all accept `project_id: str = DEFAULT_PROJECT`.

---

## 2. src/life_kernel/metrics.py — Prometheus metrics have project_id label

**PASS**

All three metric families carry `project_id`:

| Metric | Line | Labels |
|--------|------|--------|
| `guinevere_lk_records_total` | L21-25 | `source`, `project_id` |
| `guinevere_lk_heartbeat_healthy` | L27-31 | `project_id` |
| `guinevere_lk_cognition_cycles_total` | L33-37 | `project_id` |

Observer helpers (`observe_record` L46, `set_heartbeat_healthy` L51, `observe_cognition_cycle` L60) all accept `project_id: str = DEFAULT_PROJECT`.

---

## 3. src/loops/audit_writer.py — write_event accepts project_id

**PASS**

- `AuditEvent` dataclass: `project_id: uuid.UUID | None = None` (L31).
- `AuditWriter.write_event`: `project_id: uuid.UUID | None = None` parameter (L52).
- project_id is stamped into `event_payload` JSONB at L84-85, persisted in the DB row at L103, and logged structurally at L118.

---

## 4. src/life_kernel/domain_minds/durability.py — record accepts project_id

**PASS**

- Abstract `DurabilityBackend.record`: `project_id: uuid.UUID | None = None` (L31).
- `PostgresAuditJournal.record`: `project_id: uuid.UUID | None = None` (L119); stamps into stored entry at L138-139.
- `InMemoryJournal.record`: `project_id: uuid.UUID | None = None` (L239); stamps into stored entry at L247-248.

---

## 5. src/knowledge_graph/consent/audit.py — log_consent_event accepts project_id

**PASS**

- `ConsentAuditor.log_consent_event`: `project_id: uuid.UUID | None = None` keyword arg (L102).
- project_id is injected into `effective_metadata` dict at L128-130, which is then serialized to JSONB and written to `memory.kg_consent_audit.metadata_jsonb`.
- Global safety events (HARD_STOP, DNR) correctly pass `project_id=None` per the docstring at L127.

---

## 6. Hash chain versioning (chain_version field)

**FAIL**

No `chain_version` field exists anywhere in the codebase. The `AuditTrail` model (`src/memory/models.py` L1078-1097) has columns `event_hash` and `previous_hash` but no chain version column. The `AuditEvent` dataclass (`src/loops/audit_writer.py` L17-31) likewise has no version field. No Alembic migration references `chain_version`. The hash chain is flat (no versioning to support schema evolution or chain rotation).

---

## 7. monitoring/grafana/dashboards/guinevere-p19-projects.json

**FAIL**

File does not exist. The `monitoring/grafana/dashboards/` directory contains 9 dashboards (agent-loop, database-memory, finops, hermes, infrastructure, llm-cost-latency, persona-safety, x-poster, x-poster-enterprise) but none for P19 multi-project observability. No dashboard groups metrics by `project_id`.

---

## 8. Per-project log channel prefix [project:slug]

**PASS**

`DiscordLogChannel` (`src/life_kernel/log_channel.py`) implements per-project prefixing:

- Constructor accepts `project_id: str | None` (L109).
- `_project_prefix` property returns `f"[project:{self._project_id}] "` when set, empty string otherwise (L131-135).
- `write()` prepends the prefix at L143: `prefixed = f"{self._project_prefix}{message}"`.
- Structlog fallback also uses the prefixed message (L149).
- `src/discord/cmd_consent.py` also uses the `[project:` prefix pattern.

---

## Summary

| # | Check | Verdict |
|---|-------|---------|
| 1 | loops/metrics.py project_id label | PASS |
| 2 | life_kernel/metrics.py project_id label | PASS |
| 3 | audit_writer.py write_event project_id | PASS |
| 4 | durability.py record project_id | PASS |
| 5 | consent/audit.py log_consent_event project_id | PASS |
| 6 | Hash chain versioning (chain_version) | FAIL |
| 7 | guinevere-p19-projects.json dashboard | FAIL |
| 8 | Per-project log channel prefix | PASS |

**Overall: 6 PASS / 2 FAIL**

The two failures are infrastructure gaps, not code defects: (a) no `chain_version` field exists for hash chain schema evolution, and (b) no Grafana dashboard surfaces per-project metrics. The core P19 observability wiring in Prometheus counters, audit writers, durability backends, consent auditing, and Discord log channels is complete and correct.
