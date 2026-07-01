# P19 Runtime Activation — Execution Plan

**Date:** 2026-06-27 10:55 WIB
**Author:** Guinevere (parent)
**Phase:** RA-1 — Activation Plan

---

## 1. Preflight Summary

See `p19-runtime-preflight.md`. Key findings:
- DB schema P19 fully present (no redeploy needed).
- Redis flag OFF in db0 + db6. Runtime heartbeat reads flag from **db6** (main.py:367 `redis://...@localhost:6380/6`).
- **Running core process has PRE-P19 code** (started 08:26 06-25; P19 files scp'd 20:30 06-25). `cognition_registry_initialized` never logged. **Core restart REQUIRED.**
- **Discord `/project` NOT wired** into bot command tree. UX DEFERRED (separate code work).
- P20 baseline healthy.

## 2. Target Status

**P19 RUNTIME ACTIVATED — UX DEFERRED**

Rationale: core runtime (project_id in heartbeat/graph/cognition/audit) can be activated via flag ON + core restart. Discord `/project` UX requires code wiring in `_entrypoint.py` (not a flag/restart job) → deferred to a separate work item, documented honestly.

## 3. Services to Restart

| Service | Restart? | Why |
|---|---|---|
| guinevere-core | ✅ YES | Running process has pre-P19 code; must reload to get ProjectAwareCognitionRegistry + flag-read paths |
| guinevere-discord | ❌ NO | `/project` not wired; restarting won't register it. Defer. |
| guinevere-mcp / 9router / monitoring / obscura / whatsapp / x-poster | ❌ NO | Unrelated to P19 runtime |

**Only guinevere-core restarts.** All other services untouched.

## 4. Execution Sequence

### Step 1: Backup/Snapshot State (before activation)
- Capture: Redis flag old value (None), service status, recent logs tail, DB counts (semantic_facts=6, kg_entities=6, audit_journal count), P20 baseline.
- No secrets.

### Step 2: Controlled core restart (BEFORE flag ON)
- `sudo systemctl restart guinevere-core.service`
- Rationale: load P19 code FIRST (with flag still OFF), verify it comes back healthy in flag-OFF (byte-identical P20) mode. This is the canary step.
- Verify: active, NRestarts stable, no crash loop, no traceback, `cognition_registry_initialized` log appears, brain think_complete active, dashboard editing.

### Step 3: Turn flag ON
- `redis SET feature:projects:enabled true` in **db6** (the DB heartbeat reads).
- Also set in db0 for consistency (where life_kernel:dashboard_message_id lives).
- Verify runtime reads it: heartbeat log should show project_id populated, `feature:projects:enabled` flag-on path active.

### Step 4: Runtime functionality proof
- `cognition_registry_initialized max_active=3` in startup log.
- Heartbeat logs carry `project_id=00000000-0000-0000-0000-000000000001` (or default).
- New `life_kernel.audit_journal` rows include project_id in metadata (chain_version=2).
- ProjectScopedMemoryStore scoped query returns only default-project facts.
- No global memory leakage (flag ON still scopes to default project = all existing data).
- Discord `/project`: NOT active (deferred — documented, not claimed).

### Step 5: P20 non-regression proof
- Heartbeat/life kernel cycling.
- Brain think_complete active, fallback 0.
- Dashboard/log writer OK (canonical id).
- hard_stop false.
- No GraphRecursionError, no traceback.
- NRestarts stable after controlled restart.

### Step 6: Soak/observation
- Monitor 5-10 min after activation.
- Capture logs + metrics.
- If errors → rollback (flag OFF, optional restart).
- No runtime-active claim without clean observation.

## 5. Rollback Plan

### Rollback OFF (flag only — instant, no restart)
- `redis DEL feature:projects:enabled` in db0 + db6.
- Runtime reads flag OFF next heartbeat → P19 transparent, P20 byte-identical.
- No restart needed for flag rollback (runtime re-reads flag each cycle).

### Rollback service (if core crash loop / regression)
- `redis DEL feature:projects:enabled` (db0 + db6) — flag OFF.
- `sudo systemctl restart guinevere-core.service` — restart with flag OFF (byte-identical P20).
- Verify P20 healthy.
- If structural damage: restore from `/tmp/p19_backup_20260626_2145.dump` (mode 600, from P19-012 schema deploy).

### Rollback evidence
- All activations have rollback. Flag rollback is instant (DEL). Service rollback is restart-with-flag-OFF.

## 6. Acceptance Criteria

| # | Criterion |
|---|---|
| AC-1 | guinevere-core restarted safely, loads P19 code (cognition_registry_initialized logged) |
| AC-2 | feature:projects:enabled=true live in db6 (read by runtime) |
| AC-3 | P19 project context used in real runtime path (project_id in heartbeat/graph/audit) |
| AC-4 | Project ID appears in DB/log/audit where expected |
| AC-5 | P20 remains healthy (NRestarts stable, brain active, 0 fallback, hard_stop false, no recursion/traceback) |
| AC-6 | Discord `/project` DEFERRED (documented, not claimed active) |
| AC-7 | No traceback/crash loop |
| AC-8 | No secret leak |
| AC-9 | Audit 1 findings fixed |
| AC-10 | Audit 2 PASS |

## 7. Hard Stop Criteria (abort activation)

- Core fails to come back active after restart → rollback (restart with flag OFF), investigate.
- Crash loop / GraphRecursionError → rollback.
- Brain fallback storm after flag ON → flag OFF, investigate.
- hard_stop_requested becomes True (not operator-initiated) → rollback.
- Dashboard stops editing → rollback.
- Memory OOM risk (cur approaching max) → rollback.
- Any secret in logs → rollback + investigate.

## 8. Audit Matrix (Round 1 — 7 dimensions)

| # | Dimension | Scope |
|---|---|---|
| 1 | Runtime activation / P20 regression | core restart safe, flag ON, P20 healthy |
| 2 | Project-scoping correctness | project_id used in runtime path, no global leak |
| 3 | DB / audit-chain | audit_journal project_id + chain_version semantics |
| 4 | Discord project UX | /project deferred status honest, no false claim |
| 5 | Security / secrets | no secrets in evidence/logs, flag value redacted |
| 6 | Rollback / idempotency | flag rollback instant, service rollback proven |
| 7 | Evidence / docs consistency | schema-pass vs runtime-active distinguished, no overclaim |

## 9. Evidence Paths

| # | File | Phase |
|---|---|---|
| 1 | p19-runtime-preflight.md | ✅ DONE |
| 2 | p19-activation-plan.md | ✅ DONE (this) |
| 3 | p19-service-restart-evidence.md | Step 2 |
| 4 | p19-flag-enable-evidence.md | Step 3 |
| 5 | p19-project-runtime-proof.md | Step 4 |
| 6 | p19-discord-project-ux-proof.md | Step 4 (deferred status) |
| 7 | p19-p20-non-regression.md | Step 5 |
| 8 | p19-soak-observation.md | Step 6 |
| 9-15 | audits/round-1/*.md | Audit 1 |
| 16-22 | audits/round-2/*.md | Audit 2 |
| 23 | p19-runtime-activation-final-report.md | Finalisasi |
| 24 | p19-runtime-activation-auditor-gate.md | Finalisasi |

## 10. Footer

| Field | Value |
|---|---|
| Plan status | READY TO EXECUTE |
| Core restart | REQUIRED (load P19 code) |
| Flag ON | db6 (+db0) |
| Discord UX | DEFERRED (separate code work) |
| Rollback | instant flag DEL + restart-with-flag-OFF |
| Next step | Phase 2: Activation implementation |