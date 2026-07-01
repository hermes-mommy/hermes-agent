# P23 Audit Round 1 — Runtime / Deploy Readiness

> **Auditor:** independent. **Date:** 2026-06-25.  
> **Scope:** P23 "Embodied Operations / Personal OS Action Layer" — runtime architecture, deployment, canary/rollback, soak, and coexistence with existing Guinevere services.  
> **Authority documents audited:**
> - `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md`
> - `docs/setup-evidence/P23/research/p23-observability-dashboard-audit-research.md`
> - `docs/setup-evidence/P23/research/p23-vps-cli-deploy-action-research.md`
> - `docs/setup-evidence/P23/research/p23-official-docs-tooling-research.md`
> - `docs/setup-evidence/P20/README.md`
> - `docs/IMPLEMENTATION_GUIDE.md` §6
> - `docs/40-operations/44-DeploymentGuide_v1.0.md`
> - `adr/ADR-016-cicd-autonomous-deployment-strategy.md`

---

## 1. Audit Scope

Evaluate whether P23's runtime/deploy design satisfies the eight hard requirements for deploy readiness:

1. `guinevere-actions` systemd service isolation/independence and resource ceiling.
2. Feature-flag rollout discipline (`p23.enabled` default off → smoke → soak → stays on).
3. P23-020 24h soak mirroring LK-017 with regression, Aizanta, and audit-hash checks.
4. P23 self-deployment gate is L3 (backup → canary → smoke → rollback).
5. No port collisions and no reuse of 9191.
6. Coexistence with `guinevere-core`, `guinevere-mcp`, `guinevere-scheduler`, `guinevere-surveillance`, `guinevere-obscura` without port/DB/resource collision.
7. Wave scaffolds P23-019 (E2E) and P23-020 (deploy/soak) reach final PASS.
8. The plan respects PLANNING-ONLY (no deploy/restart in this phase).

---

## 2. Findings

### 2.1 `guinevere-actions` systemd service design

**Severity:** INFO  
**Path:** `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:995-1000`

The plan defines the new service with the correct independent-stop semantics:

- `After=guinevere-core.service` is declared (`:995`).
- **No `Requires=`** is declared, so `systemctl stop guinevere-actions` does not stop `guinevere-core`.
- `MemoryLimit`/`CPUQuota` scoped (`:995-1000`).
- It mirrors the existing `guinevere-mcp.service`/`guinevere-loops.service` pattern but corrects the over-tight coupling by omitting `Requires=`.

**Recommendation:** Ensure the eventual unit file explicitly omits `Requires=guinevere-core.service` and adds `MemoryMax=`, `CPUQuota=`, `Slice=guinevere.slice`, and `ReadWritePaths=` consistent with existing units. No finding prevents planning-phase acceptance.

---

### 2.2 Feature-flag rollout

**Severity:** INFO  
**Path:** `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:595-596`, `:602-604`

- `p23.enabled:false` default is stated (`:596`).
- Per-executor flags `p23.<executor>_enabled:false` are also specified (`:603`).
- Rollback path = flag-off + verify core unaffected (`:602-604`).

**Recommendation:** Document the exact Redis key and PG `system.feature_flags` row format in P23-001 governance. No blocker.

---

### 2.3 Soak strategy (P23-020)

**Severity:** INFO  
**Path:** `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:583-589`, `:997-1008`

The soak explicitly mirrors LK-017:

- 24h production soak.
- Action queue live (L1/L2 autonomously).
- HARD-STOP tested.
- P20 regression: `pytest tests/life_kernel/` 420 passed / 7 skipped (`:585`).
- Aizanta impact checks: `systemctl status aizanta-*`, `docker ps --filter name=aizanta`, `redis-cli -n 10 PING` (`:586`).
- Audit hash-chain integrity verified (`:588`).

**Recommendation (at audit time):** P20 status was "EARLY PRODUCTION ACCEPTANCE — OPERATOR WAIVED 24H SOAK"; the P23-020 24h soak cannot start until the P20 axis is satisfied. The plan correctly gates P23-020 on P20 pass + P19 definition pass (`:998`). **DOC-GATE cleanup 2026-06-25:** current gate is P20 axis satisfied by operator accepted-risk waiver (fresh runtime incident preflight before LOCKED-file edits) + P19 namespace contract readiness (P19 definition complete 2026-06-25). (P23-020 own 24h soak remains valid post-implementation.)

---

### 2.4 Deploy gate for P23 itself

**Severity:** INFO  
**Path:** `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:597-600`, `p23-vps-cli-deploy-action-research.md:131-158`

- P23's own deployment is classified L3 with backup → canary → smoke → rollback (`:599`).
- The L3 gate sequence is fully detailed in the VPS/SSH research (`p23-vps-cli-deploy-action-research.md:131-158`).
- Backup uses `pg_dump` + file snapshot + S3/R2 via restic/rclone, with sentinel `/home/guinevere/.backup/last-success`.

**Recommendation:** Add a concrete `systemd/guinevere-actions.service` template as a planning artifact (not deployed) so the wave-020 scaffold has a file to edit. Not a blocker for planning phase.

---

### 2.5 Port collision

**Severity:** INFO  
**Path:** `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:597`, `p23-observability-dashboard-audit-research.md:95-96`

- P23 is designed to use no new inbound port; it consumes PG/Redis and outbound executors (`:597`).
- If a dedicated metrics HTTP server is ever needed, the plan forbids port 9191 (`llm_metrics`) and requires reuse of the shared registry or a port ≠ 9191 (`p23-observability-dashboard-audit-research.md:95-96`).

**Recommendation:** None; design is collision-free.

---

### 2.6 Coexistence with core/mcp/scheduler/surveillance/obscura

**Severity:** LOW (observation)  
**Path:** `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:596-598`, `docs/IMPLEMENTATION_GUIDE.md:605-638`

- The plan states P23 coexists with existing services without port/DB collision (`:596-598`).
- IMPLEMENTATION_GUIDE §6 defines the shared-VPS isolation matrix (Guinevere vs Aizanta) and the `guinevere-*` / `aizanta-*` prefix convention (`docs/IMPLEMENTATION_GUIDE.md:609-619`).
- P23 uses PG schema `p23` + `audit.action_log`, Redis DB0/DB3/DB5, and `guinevere-*` systemd names only.

**Recommendation:** Verify during implementation that the new service uses `Slice=guinevere.slice` and the same `ReadWritePaths` as existing units. No planning-phase blocker.

---

### 2.7 Wave scaffolds end-to-end to final PASS

**Severity:** INFO  
**Path:** `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:984-1008`

- P23-019 is the E2E scenario suite covering all executors + HARD-STOP + self-debug + audit integrity (`:984-996`).
- P23-020 is the production deploy/canary/rollback/soak/final gate with concrete required commands and evidence (`:997-1008`).
- Both waves are BLOCKED until prerequisites complete, and both include explicit hard-rejection criteria and rollback/re-run safety.

**Recommendation:** None; scaffolds are complete.

---

### 2.8 PLANNING-ONLY compliance

**Severity:** PASS  
**Path:** `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:50-55`, `:1000`, `:1051-1053`

- The plan repeatedly states that this is a planning phase with NO implementation, deploy, restart, secret edit, or service disruption (`:50-55`).
- P23-020 explicitly forbids "deploy/restart in this planning phase" (`:1000`).
- No `systemd/guinevere-actions.service` file exists on disk.
- No `src/life_kernel/executors/` directory exists.
- No `p23.enabled` runtime code exists in `src/`.

**Finding:** PLANNING-ONLY is respected.

---

## 3. Hard-Rejection Criteria Check (#13, #15, #16, #18)

| Hard-rejection criterion | Plan reference | Verdict |
|---|---|---|
| **#13** Production service others can be disrupted without isolation proof | `p23-embodied-operations-enterprise-plan.md:596-598`, `p23-vps-cli-deploy-action-research.md:3.4` — isolation matrix, Aizanta-proof, independent service | PASS |
| **#15** Tests/soak/deploy gate does not reach final production proof | `p23-embodied-operations-enterprise-plan.md:984-1008` — P23-019 E2E + P23-020 24h soak + final gate | PASS |
| **#16** Implementation waves not end-to-end from first file to deploy/soak/final PASS | `p23-embodied-operations-enterprise-plan.md:41-676` dependency map + §46 wave list | PASS |
| **#18** Evidence created before verification pass | No P23 evidence/verification files created before this audit; P23-001..020 evidence directories are not yet created. PLANNING-ONLY holds. | PASS |

---

## 4. Verdict

**PASS** — Runtime / Deploy Readiness

The P23 plan provides a complete, well-grounded runtime and deploy-readiness design. The `guinevere-actions` service is specified with correct independent-stop semantics, resource limits, and coexistence rules. The feature-flag rollout, L3 deploy gate, 24h soak mirroring LK-017, and Aizanta-isolation proof are all defined. No port collisions are introduced. The wave scaffolds P23-019 and P23-020 are end-to-end to final PASS. Critically, the plan strictly respects PLANNING-ONLY: no implementation files, no systemd service file, no restart/deploy actions, and no runtime evidence created before verification.

**Output path:** `C:\Users\faizz\guinevere\docs\setup-evidence\P23\evidence\audits\round-1\runtime-deploy-readiness.md`
