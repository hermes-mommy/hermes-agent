# R05 — Consent Revocation Cascade Audit

**Date:** 2026-06-27
**Scope:** End-to-end audit of what happens when consent is revoked across the system.
**Method:** Static read of every file that writes to `consent:grants` (Redis DB0), every file that reads the `consent.consent_ledger` table, every file that imports `check_consent` / `invalidate_cache`, and every consumer hook (wearable writer, gmail router/consumer, surveillance consumer, whatsapp gate, KG manager, persona plugin).
**Conclusion (TL;DR):** Consent revocation is **preventive-only at ingestion**, **preventive-only at the KG write/uplink seam**, and **partially-reactive at the tool-call hook in `safety_plugin.py` (Gate 10)** — via safe-mode, NOT via direct consent lookup. There is **NO consumer-facing cascade** that stops persona injection, surveillance in-flight batches, wearable in-flight batches, or KG edge reads once a grant is revoked. The system makes no use of the `consent:grants` Redis key, which is a vestigial global flag set left orphaned by the P19/P22 surveillance refactor that moved truth to the `consent.consent_ledger` table.

---

## 1. Inventory of Consent Checkpoints (the "Where")

The system has EIGHT distinct consent surfaces. They do not cross-talk.

| # | Store | Writer(s) | Reader(s) | Reactive or Preventive | Notes |
|---|---|---|---|---|---|
| C1 | `consent:grants` — Redis DB0 (JSON set) | `src/discord/cmd_consent.py`, `src/hermes_plugins/commands_system/consent.py` | **NONE consumed by runtime.** Only the writer modules re-read it. | Preventive (but no consumer reads it). | **Orphan flag.** See §3. |
| C2 | `consent.consent_ledger` — Postgres (`status` ∈ {ACTIVE, PAUSED, WITHDRAWN}) | `src/surveillance/consent_gate.py` (via direct INSERT during grant/pause/revoke), `src/wearable/health_consent.py` (direct INSERT), DB migrations | `src/surveillance/consent_gate.py:_query_ledger()`, `src/wearable/health_consent.py:_query_ledger()` via Redis DB2 cache | Preventive. Cache TTL 300s. Fail-closed on DB failure. | Canonical, with cache. Production truth. |
| C3 | `consent:surveillance:*` — Redis DB2 cache | `src/surveillance/consent_gate.py:_cache_result()` | `src/surveillance/consent_gate.py:_try_cache_lookup()` (called by `check_consent`) | Preventive; cache invalidation via `invalidate_cache()` on revoke. | 300s TTL. |
| C4 | `consent:wearable-health:*` — Redis DB2 cache | `src/wearable/health_consent.py:_cache_result()` | `_try_cache_lookup()` → `check_wearable_consent()` | Preventive. Per-scope cache invalidation on revoke. | 300s TTL. |
| C5 | `guinevere:consent:email` — Redis (key, no TTL) | `src/gmail/consent_manager.py:grant_consent()/revoke_consent()` | `EmailConsentManager.get_consent_status()` (`!email-status`), and `check_email_consent()` delegates to C2/C3. | Preventive only (pipeline guard). | Secondary audit-mirror; truth is still C2/C3. |
| C6 | `guinevere:whatsapp:consent` — Redis hash | `src/channels/whatsapp/consent_manager.py:grant()/revoke()` | `WhatsAppConsentManager.evaluate()` (per-message gate) | Preventive. | Hash with `granted`, `granted_by`, `timestamp`, `revoked_at`. |
| C7 | `memory.kg_consent_audit` — Postgres | `src/knowledge_graph/consent/audit.py:ConsentAuditor.log_consent_event()` (called by `ConsentManager.revoke_consent()` before tombstoning) | `ConsentAuditor.get_audit_trail()`, `verify_audit_integrity()` | Audit trail only — does NOT gate reads/writes. | Carries consent_token, not revoke state. |
| C8 | KG in-memory `is_active` truth | `ConsentManager.revoke_consent()` tombstones `kg_entities` and `kg_edges` rows | KG queries that filter `is_tombstoned = FALSE` (`backfill_validator.py`, `consent/manager.py:get_consent_scope()`) | Reactive at the DB level — but only after `_query_ledger` returns WITHDRAWN at the next preventive call. | Tombstone cascade is best-effort (manager logs and returns 0/0 on tombstone failure). |

### 1.1 — Consumers of `check_consent(...)` (the actual call-sites)

These are the ONLY call-sites that ask "may I proceed?" — every other consent-named function is either a *write* path or a feed into these.

| Caller | Module | Defer-to gate? | Re-check on revoke? |
|---|---|---|---|
| SurveillanceConsumer (Redis DB2 buffer drain) | `src/surveillance/consumer.py:190` | Per-event — fail-closed. | Yes (pre-check per event). But event-already-queued events: see §4. |
| Discord `cmd_surveillance_status.py:162` | Status display only — no gate. | N/A. |
| Discord `cmd_surveillance_pause.py:122` | Invalidates cache, does NOT re-check per-event. | No. |
| Discord `cmd_pc.py` (`/phone-control`) | `cmd_pc.py:236` — calls `check_consent("surveillance.app_usage")`. | Preventive. |
| Hermes `/surveillance-pause`, `/surveillance-status`, `/surveillance-resume` plugins | `commands_surveillance/*.py` | Invalidation only. |
| Gmail router | `src/gmail/router.py:330` calls `_check_consent(project_id=...)` (in the same module, line 443). | Preventive per-message. |
| Gmail service/consent_manager wrapper | `src/gmail/service.py:802` (mock fallback) and `src/gmail/consent_manager.py:125,178,289`. | Preventive per call. |
| Wearable writer (`_write_batch`) | `src/wearable/writer.py:129` calls `check_metric_consent(metric_type)` per-batch. | Preventive per write batch. Cache hits skip DB. |
| Wearable alert router | `src/wearable/alert_router.py:186` (failure path only; not a primary gate). | Preventive. |
| KG `ConsentManager.check_consent` (token-shape validator) | `src/knowledge_graph/consent/manager.py:220` | Defensive. Returns False on malformed token or principal mismatch. |
| KG `backfill_validator.check_consent_compliance` | `src/knowledge_graph/ingestion/backfill_validator.py:655` | Audit-time only. |
| KG hard-stop gate (`check_hard_stop`) | `src/knowledge_graph/consent/manager.py:643` | Cross-references `SAFE_WORD_INDICATORS` in `memory.episodes`. Globally FAIL-CLOSED. |
| KG DNR gate (`check_dnr`) | `src/knowledge_graph/consent/manager.py:704` | Transitive: entity → incident edges → semantic_facts → episode.do_not_recall. FAIL-CLOSED. |
| Hermes `safety_plugin.pre_tool_call` | `src/hermes/safety_plugin.py:903` — Gate 10 blocks tool calls when `SafeModeController.is_active`. | Reactive to **safe-mode** state, not consent directly. |

There is **NO** consumer in `src/persona/` that calls `check_consent`. There is **NO** call in `src/hermes/plugins/persona_plugin.py` to `check_consent` or to read `consent:grants`.

---

## 2. What Happens When Consent is Revoked (Per-Surface Cascade)

### 2.1 — Inside `src/discord/cmd_consent.py` (the user-facing trigger)

`consent_callback()` at line 141: on `revoke`, the handler
1. Reads `consent:grants` from Redis DB0 (`_get_grants`).
2. Calls `grants.discard(key)` and writes back (`_save_grants`).
3. Logs `consent_revoked` to structlog.
4. Sends a Discord ephemeral embed.

**What happens AFTER this returns:**
- The Redis key is updated. No subscribers, no pub/sub fan-out, no event broadcast.
- The **/consent** command in Hermes (`src/hermes_plugins/commands_system/consent.py`) performs an identical write to the same `consent:grants` Redis DB0 key — there is no coordination between Discord-side and Hermes-side grants; they treat `consent:grants` as a flat set of strings (e.g., `"wearable"`, `"surveillance"`), not structured `{scope, project_id, status, granted_at}` tuples.

### 2.2 — Surveillance surface (C2/C3)

If revocation enters via the *surveillance* consent ledger (the canonical path for surveillance scopes):
1. `src/discord/cmd_consent.py` only writes `consent:grants`. It does NOT touch the `consent.consent_ledger`. So the revocation is **NOT** reflected in C2/C3.
2. To revoke via the canonical path requires a *different* command path — there is no Discord/Hermes revocation endpoint that writes a WITHDRAWN row to `consent.consent_ledger`. This is a known seam: see §5.

If a WITHDRAWN row exists in `consent.consent_ledger` (via direct DB write, migration, or the `/surveillance-pause` command which only invalidates cache, not the ledger):
- `check_consent()` reads DB2 cache first; if cache is `WITHDRAWN`, returns BLOCK.
- If cache miss → DB lookup → WITHDRAWN → returns BLOCK and caches the WITHDRAWN verdict.
- `SurveillanceConsumer` (`src/surveillance/consumer.py:190`) would drop subsequent events.
- **Pre-queued events in Redis DB2 buffer**: NOT processed for re-check. Already-popped events in `process_event()` running pipeline: the consent check at step 2 (line 188) drops the event, but only *if* the cache has refreshed. If a WITHDRAWN row was inserted AFTER the consumer's cache TTL (300s) elapsed, the consumer may receive cached ALLOW verdicts for up to 300s.
- `invalidate_cache()` is best-effort: it deletes the Redis DB2 key but does not async-poke the consumer. The consumer's next call to `check_consent()` will see a cache miss and fall through to DB (which now reflects WITHDRAWN).
- **The pause command** (`cmd_surveillance_pause.py` and Hermes plugin equivalent) sets `_paused = True` (Discord side; Hermes side also `_paused = True`), invalidates cache for all 5 surveillance scopes, but does NOT stop already-running tasks. The `_paused` flag is referenced via `is_paused()` — but **no consumer reads `is_paused()`**. See `src/discord/cmd_surveillance_pause.py:34` — `is_paused()` is exported but **no call-site imports it**. The `_paused` flag is dead code at the consumer-orchestration level.

### 2.3 — Wearable surface (C2/C4)

1. `revoke_consent(scope) → _write_consent_entry(scope, ConsentStatus.WITHDRAWN)` → INSERT into `consent.consent_ledger` → `await invalidate_consent_cache(scope)` → deletes `consent:wearable-health:{scope}` from Redis DB2.
2. `HealthIngestionWriter._write_batch` (`src/wearable/writer.py:129`) calls `check_metric_consent(metric_type)` per-metric-type per-batched-write — fail-closed.
3. Active in-flight `asyncpg` pool transactions: still commit. There is **no cooperative cancellation** in `src/wearable/writer.py`. A revoke that lands DURING a batch → already-batched samples that haven't yet been upserted will be inserted if their `await upsert()` succeeds; the cache-miss / DB-hit for the NEXT batch will BLOCK.
4. Alert router (`src/wearable/alert_router.py:186`) logs `alert_consent_gate_failed` but does not pre-check.

### 2.4 — Gmail / Email surface (C2/C3/C5)

1. `!email-consent-revoke` → `src/gmail/commands/consent.py:handle_consent_revoke()` → calls `EmailConsentManager.revoke_consent(actor)` → writes `guinevere:consent:email` (secondary metadata key) with status=WITHDRAWN.
2. The next `check_email_consent()` call → `ConsentChecker.check_consent("surveillance.email")` → BLOCK.
3. **BUT**: `EmailConsentManager.revoke_consent()` does NOT call `invalidate_cache()` on the surveillance scope. The Redis DB2 cache for `consent:surveillance:surveillance.email` will return ALLOW up to 300s after the metadata key is updated.
4. `src/gmail/router.py:330` calls `await self._check_consent(project_id=...)` per-message — fail-closed (line 443 implementation): any exception → BLOCK.

### 2.5 — WhatsApp surface (C6 secondary)

`WhatsAppConsentManager.evaluate()` runs synchronously per-message (`src/channels/whatsapp/consent_manager.py:105`):
- Reads Redis hash `guinevere:whatsapp:consent` → if `granted=false`, returns BLOCK with response "WhatsApp access is not enabled yet. Consent is required..."
- If Redis read fails → fail-closed BLOCK.
- Revocation: `revoke()` writes the hash with `granted=false`. Immediate effect on next `evaluate()` call (no cache).
- This surface is **fully reactive** — there is no TTL or async layer.

### 2.6 — Knowledge Graph (C7 + C8)

`ConsentManager.revoke_consent(consent_token)` (`src/knowledge_graph/consent/manager.py:345`):
1. Writes write-ahead audit row `REVOKE_CONSENT` (own transaction).
2. Tombstones `kg_entities` for every entity_id attached to a token-carrying edge.
3. Tombstones `kg_edges` WHERE `consent_token = :token`.
4. Best-effort: if the tombstoning UPDATE raises, logs and returns 0/0 (audit row is canonical).

**Cascade effects:**
- Anything reading `kg_entities`/`kg_edges` with `WHERE is_tombstoned = FALSE` will skip the tombstoned rows. This **IS** partially-reactive.
- **But the truth source is the consent ledger**, not the tombstone. If a writer bypasses the tombstone WHERE clause (manual SQL, raw asyncpg session, or a query that omits the filter), the data is still returned.
- `RLSPolicyManager.upgrade_rls_with_consent_awareness()` is **deferred to P16-008** (per the docstring at line 222 of `src/knowledge_graph/consent/rls.py`) — meaning DB-level RLS does NOT currently filter rows by `consent_token` validity. The placeholder RLS only filters `is_tombstoned`.
- `check_dnr` is a defensive read-time gate that follows `do_not_recall` episode flags, NOT revocation. Revocation merely tombstones the entity; the episode's `do_not_recall` flag remains untouched unless the operator manually sets it.

### 2.7 — Hermes Safety Plugin (Gate 10)

**`src/hermes/safety_plugin.py:877 pre_tool_call`** — has a gate labelled "Gate 10 Consent/Safe-mode". Implementation:
```python
if self._distress_available and self._safe_mode_controller is not None and self._safe_mode_controller.is_active:
    return { "action": "block", "reason": "CONSENT_SAFE_MODE", ... }
```
**This is reactive to `SafeModeController.is_active`, NOT to consent directly.**
- `SafeModeController.is_active` SET BY: D2+ distress (`auto_activate` after `force_safe_mode`) or HARD STOP keyword (only if `force_safe_mode` is called — see KNOWN-ISSUES.md PR-01: HARD STOP keyword does NOT currently activate SafeModeController).
- **NOT set by**: any consent revocation (Discord `/consent action:revoke`, Hermes `/consent`, wearable revoke, etc.).
- This means: revoke consent for surveillance → `SurveillanceConsumer` will drop events (preventive), but **`pre_tool_call` will not block persona-driven tool calls because `SafeModeController.is_active` is still `False`**.

### 2.8 — Persona (the missing gap)

`src/hermes/plugins/persona_plugin.py:536 pre_llm_call` — reads mood/yandere/punishment/reward from Redis DB5 and injects `[PERSONA STATE]` block into the system prompt.
- **No consent check.** No `check_consent()` call. No `consent:grants` read. No read of the `consent.consent_ledger` table.
- A revoke via either `/consent` command path leaves `persona_plugin.py` untouched. It keeps injecting `[PERSONA STATE] Y{yandere_level}` blocks even after the operator has revoked persona-related consent.

---

## 3. The `consent:grants` Redis Key: Vestigial

**No runtime component reads `consent:grants`.** Grep confirms only the writers read it (`src/discord/cmd_consent.py:52,66` and `src/hermes_plugins/commands_system/consent.py:39,53` — both are local helpers, not hook recipes).

This key was the original P7-010 consent surface. P19-009 refactored consent to project-scoped rows in `consent.consent_ledger`, and the global "block of strings in Redis" was deprecated but **never deleted nor migrated**. **When Faiz issues `/consent action:revoke category:wearable`:**
1. `consent:grants` strips `wearable` (or `wearable:project_xyz`).
2. **Nothing in the wearable pipeline reads `consent:grants`.** `check_wearable_consent(scope)` reads `consent:wearable-health:{scope}` from Redis DB2 and falls back to `consent.consent_ledger`. It never touches `consent:grants`.
3. So this revocation is a **no-op for runtime behavior** unless followed by a separate ledger write.

This means the `/consent` command exposed to operators is misleading: it suggests revocation is global, but only the surveillance-pause/open-actor commands write the actual safety state. (The wearable revocation path *does* require going through `src/wearable/health_consent.py:revoke_consent()` or a direct ledger insert.)

---

## 4. Reactive vs Preventive — Scoreboard

| Subsystem | Preventive (pre-check gates future writes) | Reactive (kills in-flight work) | Verdict |
|---|---|---|---|
| **Surveillance ingestion** (`SurveillanceConsumer`) | Yes — per-event `check_consent()`. | **No.** `_paused` flag is exported but never imported by the consumer. Best-case latency on revocation = next-event-cycle + cache miss. | Preventive-only. |
| **Surveillance tool calls** (`safety_plugin.pre_tool_call`) | Yes — Gate 10 blocks when `SafeModeController.is_active`. | Indirect. Only reacts if SafeMode is also active. | Preventive-only-via-safe-mode. |
| **Surveillance DB2 cache** | Already correctly invalidated by `cmd_surveillance_pause.py`. | N/A — pure data plane. | OK. |
| **Wearable ingestion** (`HealthIngestionWriter._write_batch`) | Yes — per-batch `check_metric_consent()`. | **No.** Active `asyncpg` pool transactions commit; no cooperative cancel. | Preventive-only. |
| **Wearable alerting** | No pre-check in alert_router (only logs failure). | **No.** An alert can fire after revoke and not be blocked. | **GAP.** |
| **Gmail router** | Yes — per-message via `_check_consent()`. | No in-flight cancellation. | Preventive-only. |
| **Gmail cache invalidation on revoke** | **NOT done.** Email revoke writes metadata key only. | N/A. | **MISSING REACTIVE PATH.** |
| **WhatsApp** | Synchronous per-message (`evaluate()`), no cache, fail-closed on Redis failure. | Yes, by design. | Fully reactive (best-case). |
| **KG mutations** | Write-ahead audit, then tombstone. | Tombstone is DB-level, not in-flight cancellation. New writes blocked by `is_tombstoned` filter. | Partially-reactive at the DB level. |
| **KG HARD STOP / DNR** | `check_hard_stop` and `check_dnr` are read-time gates. Both fail-closed. | N/A — read path. | OK. |
| **KG RLS** | **DEFERRED to P16-008.** Placeholder RLS only filters `is_tombstoned`. | N/A. | **GAP.** |
| **Persona plugin (injection)** | **None.** | **None.** | **GAP — this audit's primary finding.** |
| **Mood / Punishment / Reward / Ritual** | Class files do not import consent. Cron-driven rituals in Hermes have no consent hook. | **None.** | **GAP.** |
| **Hermes tool calls (Gate 10)** | Via `SafeModeController.is_active`. | Indirect — requires safe-mode, not consent. | **GAP — relies on safe-mode, not consent.** |
| **Hermes plugin: persona** | No consent check. | No cascade. | **GAP.** |
| **Hermes plugin: surveillance_status/pause/resume** | Read-only / pure invalidation. | No reactive stop of consumers. | Pause is decorative w.r.t. running consumer. |

### 4.1 — Summary

The system has:
- **8 of 14** subsystems with at least a preventive gate.
- **2 of 14** with a real reactive signal (WhatsApp surface, KG tombstone level).
- **6 of 14** with no consent gate whatsoever (PersonaPlugin, mood engine, punishment engine, reward engine, ritual scheduler — none of them check consent).
- **0** cascading reactive mechanism that pushes a revocation from one anchor (e.g., KG revoke) to other consumers (gmail circuit, surveillance circuit, persona circuit, wearable circuit).

---

## 5. The `consent_ledger` Table — Who Reads, Who Writes

Writers (per Grep + read):
- `src/wearable/health_consent.py:_write_consent_entry` (lines 319-337) — INSERT path.
- `src/surveillance/consent_gate.py:_query_ledger` — SELECT only (read).
- **`src/discord/cmd_consent.py` does NOT write to `consent.consent_ledger`.**
- **`src/hermes_plugins/commands_system/consent.py` does NOT write to `consent.consent_ledger`.**
- **`src/gmail/consent_manager.py` does NOT write to `consent_consent_ledger`.** It only writes metadata key `guinevere:consent:email`.
- Hibernate/SQLAlchemy relationships: `src/memory/models.py:995` declares a ForeignKey to `consent.consent_ledger.id`, presumably for trace links.
- Migrations: `alembic/versions/p19_001_project_namespaces.py` adds `project_id` to the table.
- For consent revocation writes to the ledger itself, KG only: `src/knowledge_graph/consent/manager.py:386-398` (via `ConsentAuditor.log_consent_event`).

Readers:
- `src/surveillance/consent_gate.py:_query_ledger` (line 582).
- `src/wearable/health_consent.py:_query_ledger` (line 297).
- Alembic versions and security-audit MD references.

**Net:** there are TWO call-paths that can WITHDRAW the surveillance or wearable scopes:
1. Direct DB call against `consent.consent_ledger` (no UI exposed).
2. The wearable `revoke_consent()` async function exposed via `src/wearable/health_consent.py:218`.

The Discord `/consent` command surface **does not revoke anything in `consent.consent_ledger`** — it only mutates `consent:grants`. This is a **CRITICAL** operational gap.

---

## 6. Exact Code Locations for Fixes

### 6.1 — Critical: PersonaPlugin must check consent before injecting persona state

**File:** `src/hermes/plugins/persona_plugin.py:536` (`pre_llm_call`)

**Fix:** insert a `_check_consent(scope: str) -> bool` call in `pre_llm_call` after `_read_persona_state()`, before `_format_persona_block`. Logic:

```python
consented = await self._check_consent("persona.personalization")
if not consented:
    # persona state withdrawal: emit neutral block instead
    logger.info("persona_plugin_consent_revoked", session_id=session_id)
    # Skip injection; do not block the LLM call (safety_plugin handles blocking).
```

**Source of truth for `_check_consent`:** delegate to `SurveillanceConsentChecker.check_consent()` (after adding `persona.personalization` to the valid scopes in `src/surveillance/consent_gate.py`) — this avoids leaking the surveillance DB2 key shape into the persona plugin.

### 6.2 — Critical: `/consent action:revoke` on Discord must write the `consent_consent_ledger` if a placeholder key matches a surveillance scope

**File:** `src/discord/cmd_consent.py:141-153` (`revoke` branch)

**Fix:** in the revoke branch, after `grants.discard(key)`, call a new helper `_revoke_in_ledger(key)` which:
1. Maps the legacy `consent:grants` key (e.g., `"wearable"`) into the canonical scope (`"wearable-health.hr"` group, `"surveillance.app_usage"`, etc.).
2. Calls `src/surveillance/consent_gate.py`'s revoke-helper OR directly inserts a WITHDRAWN row into `consent.consent_ledger`.
3. Calls `await invalidate_cache(<canonical_scope>)` for each affected scope.

### 6.3 — Critical: `EmailConsentManager.revoke_consent()` must call `invalidate_cache("surveillance.email")`

**File:** `src/gmail/consent_manager.py:193` (`revoke_consent`)

**Fix:** at line 234 (after the Redis metadata write), add:
```python
from src.surveillance.consent_gate import invalidate_cache
await invalidate_cache(self._config.scope)
```

This forces the next surveillance check to miss the cache and read fresh from `consent.consent_ledger`.

### 6.4 — Critical: Surveillance pause must stop the consumer, not just flip a flag

**Files:**
- `src/discord/cmd_surveillance_pause.py`
- `src/hermes_plugins/commands_surveillance/surveillance_pause.py`
- `src/surveillance/consumer.py`

**Fix:** `SurveillanceConsumer` must call `is_paused()` at the top of `process_event()` (between `event_type = event.get(...)` and the consent check) and return False (drop) if paused. Add a global module-level registry so `_set_paused_for_testing()`/`is_paused()` lives in `src/surveillance/consumer.py` (not in the command modules), and the command modules import & propagate.

### 6.5 — Critical: PersonaPlugin must respect `SafeModeController.is_active` (in addition to consent)

**File:** `src/hermes/plugins/persona_plugin.py:536`

The `safety_plugin.py:903` Gate 10 already blocks `pre_tool_call`, but `pre_llm_call` is NOT gated by safe-mode. Fix: import `SafeModeController` lazily and early-return neutral injection if `safe_mode.is_active`.

### 6.6 — High: Hard-stop bridge activation from `HardStopHandler` to `SafeModeController`

**File:** `src/persona/safe_mode.py` (`SafeModeController.force_safe_mode`)

Existing infrastructure: KNOWN-ISSUES.md PR-01 notes that HARD STOP keyword detection does NOT currently activate SafeModeController. Add a coordinator (e.g., `src/safety/coordinator.py`) that listens to HardStopHandler events and pumps them into `force_safe_mode(context="hard_stop_keyword")`.

### 6.7 — Medium: Harden revoke_consent tombstone cascade against partial failure

**File:** `src/knowledge_graph/consent/manager.py:401-466`

Currently: tombstoning failure is logged and a 0/0 result returned. Fix: expand the audit row to include the **intended** entity_ids and edge_ids; on tombstoning failure, the audit row records "INTENDED_TO_TOMBSTONE" and `verify_audit_integrity()` flags the difference for re-tombstoning on next operator review.

### 6.8 — Medium: Bring consent:grants to canonical truth — either delete it or migrate it

Two options:
- **Delete:** remove `src/discord/cmd_consent.py:_save_grants`/`_get_grants` and the Hermes equivalent; redirect the commands to a single `consent_admin.py` that writes to `consent.consent_ledger`.
- **Migrate:** write a one-shot Redux migration that reads `consent:grants` JSON, classifies each string by simple prefix map (`wearable` → wearable-health.* group; `surveillance` → surveillance.* scope; etc.), and inserts the corresponding `consent.consent_ledger` rows atomically. Then mark `consent:grants` as a noop.

---

## 7. Recommended Cascade Mechanism

### 7.1 — Design Goals

1. **Single-source-of-truth revocation**: the operator's revoke action must write to `consent.consent_ledger` (the canonical surface), not to `consent:grants`.
2. **Cross-subsystem fan-out**: a single WITHDRAWN row must invalidate caches in **all** subsystems (surveillance, wearable, gmail, persona, KG) within a bounded latency (≤5s, ideally ≤ 1s).
3. **Pubsub or polling**: use Redis Pub/Sub (channel `consent:revoked:{scope}`) for fan-out. Subscribers gated on this channel invalidate their caches. Polling fallback: 30s.
4. **In-flight cancellation**: where possible, in-flight producers (surveillance consumer, wearable writer) must check at the START of each unit of work, not AFTER the unit-of-work has begun. Add a `try-cancel` interface to asyncpg and aioredis pools.
5. **Persona circuit breaker**: cancel pre-llm-call injection if consent is revoked; emit a neutral `[CONTEXT: PERSONA_DISABLED]` marker so the LLM sees it.

### 7.2 — Implementation Outline

```
/consent action:revoke category:surveillance.app_usage
      │
      ▼ (after auth)
RevokeOrchestrator.revoke(scope, project_id, actor, reason)
      │
      ├── INSERT INTO consent.consent_ledger (status=WITHDRAWN, ...)
      │
      ├── redis_pub("consent:revoked:surveillance.app_usage", {actor, reason, ts})
      │
      ▼ (subscribers)
      ├── SurveillanceConsentCache.invalidate(scope)        [already exists]
      ├── WearableConsentCache.invalidate_if_meta(scope)
      ├── EmailConsentCache.invalidate("surveillance.email")
      ├── KGConsentAuditIntegrator.schedule_revocation_pass() [P16-008]
      └── PersonaConsentSubscriber.mark_scope_revoked(scope)  [NEW]
                        │
                        ▼
              persona_plugin reads revoked_scopes set
              at pre_llm_call start; suppresses matching fields.
```

### 7.3 — File-Locations to Touch (Summary List)

1. **NEW** — `src/consent/orchestrator.py` (single-point revocation API).
2. **NEW** — `src/consent/pubsub.py` (pub/sub channel constants + helpers).
3. **MODIFY** — `src/discord/cmd_consent.py:revoke` branch (call orchestrator, not Redis-only).
4. **MODIFY** — `src/hermes_plugins/commands_system/consent.py:handle` (same).
5. **MODIFY** — `src/gmail/consent_manager.py:revoke_consent` (orchestrator delegation + cache invalidation).
6. **MODIFY** — `src/surveillance/consumer.py:process_event` (read `is_paused()` + cancellable pause flag; subscribe to `consent:revoked:*`).
7. **MODIFY** — `src/wearable/writer.py:_write_batch` (subscribe to scope-specific revocation channel; cancel in-flight batch).
8. **MODIFY** — `src/wearable/alert_router.py` (pre-check before alerts).
9. **MODIFY** — `src/hermes/plugins/persona_plugin.py:pre_llm_call` (check consent + safe-mode; subscribe to `consent:revoked:persona.personalization`).
10. **MODIFY** — `src/persona/safe_mode.py` (HARD STOP → SafeModeController bridge via new coordinator).
11. **MODIFY** — `src/knowledge_graph/consent/manager.py:revoke_consent` (orchestrator delegation; audit on tombstone failure).
12. **MODIFY** — `src/knowledge_graph/consent/rls.py:upgrade_rls_with_consent_awareness` (P16-008 work — implement now if scope allows).

### 7.4 — Tests to Add (Pinned Locations)

- `tests/consent/test_orchestrator.py` — single-point write + cross-cache invalidation.
- `tests/persona/test_persona_plugin_consent.py` — `pre_llm_call` with revoked consent emits neutral block.
- `tests/surveillance/test_consumer_pause_reactive.py` — `_paused=True` between batches → events dropped.
- `tests/wearable/test_writer_revoke_inflight.py` — concurrent revoke during upsert commits; subsequent batch blocked.
- `tests/gmail/test_email_revoke_cache_invalidation.py` — revoke invalidates surveillance DB2 cache.
- `tests/kg/test_knowledge_graph_revoke_under_failure.py` — tombstoning failure flagged in audit row.
- `tests/safety/test_hard_stop_activates_safemode.py` — HARD STOP keyword triggers SafeModeController.

---

## 8. Critical Gaps (Required for Sign-Off)

| Gap ID | Severity | Description | Owner-Fix | Required for P4 sign-off? |
|---|---|---|---|---|
| GAP-001 | **CRITICAL** | `consent:grants` Redis key is dead — no consumer reads it. | RevokeOrchestrator deletion or migration. | YES. |
| GAP-002 | **CRITICAL** | `/consent` Discord/Hermes commands do not write `consent.consent_ledger`. | Route commands to orchestrator. | YES. |
| GAP-003 | **CRITICAL** | PersonaPlugin has zero consent gating. | Add `_check_consent("persona.personalization")` to `pre_llm_call`. | YES. |
| GAP-004 | **CRITICAL** | `_paused` flag in `cmd_surveillance_pause.py` is not consumed by `SurveillanceConsumer`. | Inject `is_paused` into consumer loop. | YES. |
| GAP-005 | **HIGH** | `EmailConsentManager.revoke_consent` does not invalidate `consent:surveillance:surveillance.email` cache. | Add `invalidate_cache` call. | YES. |
| GAP-006 | **HIGH** | HARD STOP keyword does not activate `SafeModeController`. | Coordinator bridge. | YES (paper-only already acceptable). |
| GAP-007 | **MEDIUM** | KG RLS is placeholder; full consent-aware RLS deferred to P16-008. | Implement upgrade path or document stop-gap. | NO. |
| GAP-008 | **MEDIUM** | Tombstone cascade best-effort — partial failure not flagged. | Audit-row on intended-vs-applied delta. | NO. |
| GAP-009 | **MEDIUM** | Wearable alert router does not pre-check consent before alerts. | Pre-check + alert suppression on revoke. | NO. |
| GAP-010 | **MEDIUM** | `consent_consent_ledger` writes are limited to wearable/surveillance — no general api. | Add general ledger writer. | NO. |

---

## 9. Final Verdict on Revocation Cascade

**Current state: revocation is preventive-only at ingestion edges, with no cross-subsystem fan-out and no in-flight cancellation. There is no cascade.**

The system has the **anatomy** of a revocation cascade (auditor, cache invalidator, tombstoner, write-ahead audit) but the **nervous system** is missing — there is no path from a single revoke action to the various consumers. Each consumer independently re-derives consent from the `consent.consent_ledger` table within a 300s TTL. Until that ends (TTL expiry or the next consumer cycle), in-flight work continues.

**The recommended fix is a single RevokeOrchestrator + Redis pub/sub fan-out** (per §7.2 above), which is the minimal mechanism that turns a preventive-only system into a reactive cascade. Combined with the PersonaPlugin consent check (GAP-003), this would close the persona-channel loophole — the primary reason this audit was commissioned.

---

## 10. Source-of-Truth Cross-References

- Server-side consent writer: `src/discord/cmd_consent.py:40` — `REDIS_KEY = "consent:grants"`.
- Server-side mirror: `src/hermes_plugins/commands_system/consent.py:29` — `REDIS_KEY = "consent:grants"`.
- Canonical ledger writer (only wearable): `src/wearable/health_consent.py:319` — `_write_consent_entry` INSERTs into `consent.consent_ledger`.
- Canonical ledger reader: `src/surveillance/consent_gate.py:582` — `_query_ledger` SELECTs latest `status`.
- Cascade tombstone: `src/knowledge_graph/consent/manager.py:345` — `revoke_consent` tombstones `kg_entities`+`kg_edges`.
- Gate 10 (only safe-mode, NOT consent): `src/hermes/safety_plugin.py:903`.
- Persona plugin (no consent check): `src/hermes/plugins/persona_plugin.py:536` (`pre_llm_call`).
- Consumer (skips revoking events but does not consume `is_paused`): `src/surveillance/consumer.py:188-208`.
- Wearable writer (preventive per-batch only): `src/wearable/writer.py:127-140`.
- Email revoke missing cache invalidation: `src/gmail/consent_manager.py:193-238`.
- WhatsApp fully reactive: `src/channels/whatsapp/consent_manager.py:105-134`.
- Public channel feed (gmail per-message gate): `src/gmail/router.py:330` and `_check_consent` at line 443.

**End of R05 — Consent Revocation Cascade Audit.**
