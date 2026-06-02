---
title: "Evidence: Cross-Document Conflict Resolution"
date: "2026-05-31"
author: "Guinevere (Sisyphus orchestrator)"
scope: "Resolution of 3 CRITICAL + 3 HIGH findings from cross-reference validation"
related_adrs:
  - ADR-030 (Redis DB Assignments)
  - ADR-031 (Database Naming Convention)
  - ADR-032 (Backup Storage Strategy)
---

# Evidence: Cross-Document Conflict Resolution

## 1. Overview

This evidence file documents the resolution of conflicts discovered during cross-reference validation of 3 newly generated documents: Test Plan, DR Plan, and Internal Operations Manual.

### Source Validation

| Audit | Report Path | Score | Verdict |
|---|---|---|---|
| Test Plan Audit | `audit-reports/2026-05-30-test-plan-audit.md` | 24/25 | PASS |
| DR Plan Audit | `audit-reports/2026-05-30-dr-plan-audit.md` | 24/25 | PASS |
| Ops Manual Audit | `audit-reports/2026-05-30-ops-manual-audit.md` | 25/25 | PASS |
| Cross-Reference Validation | `audit-reports/2026-05-30-cross-reference-validation.md` | 16/24 (8 FAIL) | NEEDS REVIEW |

### Conflict Summary

| ID | Severity | Conflict | Status | ADR |
|---|---|---|---|---|
| CRX-18 | CRITICAL | Redis DB assignments conflict across docs | **RESOLVED** | ADR-030 |
| CRX-03 | CRITICAL | Database name: `guinevere_db` vs `guinevere` | **RESOLVED** | ADR-031 |
| CRX-17 | CRITICAL | Backup storage: Backblaze B2 vs R2+S3 | **RESOLVED** | ADR-032 |
| CRX-07 | HIGH | PgBouncer deployment: systemctl vs Docker | **RESOLVED** | ADR-014 ref |
| CRX-14 | HIGH | Related Documents path prefix inconsistency | **RESOLVED** | Direct patch |
| CRX-01 | HIGH | Service inventory incomplete/inconsistent | **DEFERRED** | Future ADR |

---

## 2. CRX-18: Redis DB Assignments (CRITICAL)

### Problem
DRPlan line 225 listed Redis DBs as: `cache, session, queue, buffer, rate-limit, pubsub`
Canonical order (APIIntegration v2.0 §9.2): `task queue, LLM cache, surveillance buffer, sessions/working memory, pub/sub, rate limiting`

DB assignments comparison:

| DB | DRPlan (wrong) | Canonical (correct) |
|---|---|---|
| DB0 | cache | task queue |
| DB1 | session | LLM cache |
| DB2 | queue | surveillance buffer |
| DB3 | buffer | sessions/working memory |
| DB4 | rate-limit | pub/sub |
| DB5 | pubsub | rate limiting |

**Safety impact**: CRX-18 was safety-critical — safe-word state lives in DB3 (sessions/working memory). Mislabeling could cause wrong DB to be flushed during emergency.

### Resolution

**ADR Created**: `adr/ADR-030-redis-db-assignments.md`
- Status: Accepted
- Risk Level: CRITICAL

**Files Patched:**
- `Guinevere_DisasterRecoveryPlan_v1.0.md` line 225 (and line 84 executive summary): DB order corrected to canonical

**Verification:**
```
grep "DB0-DB5" DRPlan → 1 match with correct canonical order ✅
TestPlan CHAOS-005 (DB0=task queue): already correct ✅
TestPlan CHAOS-006 (DB3=safe-word sessions): already correct ✅
```

---

## 3. CRX-03: Database Name (CRITICAL)

### Problem
TestPlan line 532 and TDD Guide lines 805, 824 used `guinevere_db` instead of canonical `guinevere`.

### Resolution

**ADR Created**: `adr/ADR-031-database-naming.md`
- Status: Accepted
- Risk Level: HIGH
- Convention: `guinevere` (no `_db` suffix), env suffixes: `_test`, `_staging`

**Files Patched:**
| File | Line | Old | New |
|---|---|---|---|
| `Guinevere_TestPlan_v1.0.md` | 532 | `guinevere_db` | `guinevere` |
| `Guinevere_TDD_Guide_v1.0.md` | 805 | `guinevere_db` | `guinevere` |
| `Guinevere_TDD_Guide_v1.0.md` | 824 | `guinevere_db` | `guinevere` |

**Verification:**
```
grep "guinevere_db" *.md → 0 matches in canonical docs ✅
grep "guinevere" DRPlan → present and correct ✅
```

---

## 4. CRX-17: Backup Storage Provider (CRITICAL)

### Problem
DRPlan referenced Backblaze B2 (~120 references) while OpsManual used Cloudflare R2 + idcloudhost S3. Operator confirmed canonical: idcloudhost S3 (primary) + Cloudflare R2 (secondary), NO Backblaze B2.

### Resolution

**ADR Created**: `adr/ADR-032-backup-storage-strategy.md`
- Status: Accepted
- Risk Level: CRITICAL
- Decision: idcloudhost S3 primary + Cloudflare R2 secondary, Backblaze B2 removed

**Pricing (verified 2026-05-31):**
| Provider | Storage/GB/bulan | Egress |
|---|---|---|
| idcloudhost S3 (primary) | Rp 507 (flat, ~$0.031/GB) | Included |
| Cloudflare R2 (secondary) | $0.015 (~Rp 245) | FREE |

**DRPlan Rewrite (deep agent, 9m 37s):**
- ~130+ edits across 2946 lines
- All `b2:` rclone remotes → `idcloudhost:` (primary) + `r2:` (secondary)
- All `B2_BUCKET`/`B2_PREFIX` variables → `PRIMARY_BUCKET`/`SECONDARY_BUCKET`/`S3_PREFIX`
- All `Backblaze B2` text → `idcloudhost S3 (primary) + Cloudflare R2 (secondary)`
- Mermaid diagram redesigned: dual-provider subgraphs
- Pricing section: complete rewrite with dual-provider costs
- Appendix C renamed: "Backblaze B2 Bucket Structure" → "idcloudhost S3 + Cloudflare R2 Bucket Structure"
- Glossary: B2 definition → idcloudhost S3 and Cloudflare R2 definitions
- Appendix G cost projection: recalculated 12-month table
- Troubleshooting table: single B2 entry → separate entries for both providers
- ADR-032 referenced in 10 contextual locations throughout document

**Verification:**
```
grep "b2:" DRPlan → 0 matches ✅
grep "B2_BUCKET" DRPlan → 0 matches ✅
grep "B2_PREFIX" DRPlan → 0 matches ✅
grep "b2-hard-delete" DRPlan → 0 matches ✅
grep "Backblaze" DRPlan → 1 match (intentional "NOT used" disclaimer) ✅
grep "systemctl restart guinevere-pgbouncer" DRPlan → 0 matches ✅
Remaining "B2" matches: 4 — all "Redis DB2" (database number 2 = surveillance buffer per ADR-030) ✅
```

**OpsManual**: No changes needed — already used correct R2 + S3 references.
**TestPlan**: No B2 references present.

---

## 5. CRX-07: PgBouncer Deployment Model (HIGH)

### Problem
DRPlan line 1765 used `systemctl restart guinevere-pgbouncer` (systemd), but PgBouncer runs as Docker container per TechnicalArchitecture v2.0 and ADR-014.

### Resolution

**File Patched:**
- `Guinevere_DisasterRecoveryPlan_v1.0.md`: `systemctl restart guinevere-pgbouncer` → `docker restart guinevere-pgbouncer`

**Verification:**
```
grep "systemctl restart guinevere-pgbouncer" DRPlan → 0 matches ✅
grep "docker restart guinevere-pgbouncer" DRPlan → 1 match (line 1848) ✅
```

---

## 6. CRX-14: Related Documents Path Prefix (HIGH)

### Problem
OpsManual lines 20, 25 used `docs/` prefix on document paths that don't use it elsewhere.

### Resolution

**File Patched:**
| File | Line | Old | New |
|---|---|---|---|
| `Guinevere_InternalOpsManual_v1.0.md` | 20 | `docs/Guinevere_Deployment_Guide_v1.0.md` | `Guinevere_Deployment_Guide_v1.0.md` |
| `Guinevere_InternalOpsManual_v1.0.md` | 25 | `docs/Guinevere_Security_Policy_v1.0.md` | `Guinevere_Security_Policy_v1.0.md` |

---

## 7. CRX-01: Service Inventory Inconsistency (HIGH — DEFERRED)

### Status
Deferred to future ADR. Service inventory differences across docs reflect different levels of detail appropriate to each document's audience (test engineers vs DR operators vs ops team). Not a factual conflict but a scope difference.

### Future Action
When service inventory governance ADR is created, standardize:
- Core service list (all docs must include)
- Extended service list (ops/DR docs may include additional)
- Naming convention for systemd units vs Docker containers

---

## 8. ADR Index Update

**File**: `Guinevere_ADR_Index_v1.0.md`

| Metric | Before | After |
|---|---|---|
| ADR count | 29 | 32 |
| Accepted | 15 | 18 |
| CRITICAL risk | 9 | 11 |
| HIGH risk | 14 | 15 |
| Backlog items | ADR-030 to ADR-044 | ADR-033 to ADR-047 |

---

## 9. Files Changed Summary

| File | Change Type | Description |
|---|---|---|
| `adr/ADR-030-redis-db-assignments.md` | Created | Redis DB0-DB5 canonical assignments |
| `adr/ADR-031-database-naming.md` | Created | Database naming convention |
| `adr/ADR-032-backup-storage-strategy.md` | Created | Backup storage provider decision |
| `Guinevere_ADR_Index_v1.0.md` | Modified | Added 3 ADR entries, updated counts |
| `Guinevere_DisasterRecoveryPlan_v1.0.md` | Modified | ~130+ edits: B2→S3/R2, Redis DB fix, PgBouncer fix, pricing rewrite |
| `Guinevere_TestPlan_v1.0.md` | Modified | 1 edit: guinevere_db → guinevere |
| `Guinevere_InternalOpsManual_v1.0.md` | Modified | 2 edits: removed docs/ prefix |
| `Guinevere_TDD_Guide_v1.0.md` | Modified | 2 edits: guinevere_db → guinevere |

---

## 10. Pricing Correction Note

The initial deep agent rewrite used $0.02/GB for idcloudhost S3 storage. This was incorrect.

**Corrected pricing (2026-05-31):**
- **idcloudhost S3**: Rp 507/GB/bulan (flat rate) ≈ $0.031/GB/month
- **Cloudflare R2**: $0.015/GB/month (~Rp 245/GB) — verified from official docs
- **Combined dual-provider rate**: $0.046/GB/month
- **Estimated Month 1 (177.8 GB)**: $8.18 storage + $0.00 drill + $0.01 API = **$8.19/month**
- **Estimated Month 12 (390 GB)**: $17.94 storage + $0.00 drill + $0.02 API = **$17.96/month**
- **Annual projection**: ~$146.55/year ($12.21/month average)

Budget impact: DR sub-budget in `Guinevere_Cost_FinOps_Model_v1.0.md` needs revision from ~$3/month to ~$12/month.

---

## 11. Remaining Items

| Item | Priority | Action Required |
|---|---|---|
| FinOps Model budget update | HIGH | Update DR sub-budget to ~$12/month |
| Re-run cross-reference validation | HIGH | Verify all 3 CRITICAL findings resolved |
| Service inventory ADR (CRX-01) | MEDIUM | Future ADR for service naming governance |
| Cost optimization strategies review | LOW | Section 10.5 savings estimates need recalculation for new rates |

---

## 12. Audit Trail

| Timestamp | Action | Agent |
|---|---|---|
| 2026-05-30 | Cross-reference validation launched | Sisyphus (parent) |
| 2026-05-30 | 3 doc audits + cross-ref validation completed | 4x Sisyphus-Junior |
| 2026-05-31 | Conflict analysis: 3 CRITICAL + 3 HIGH identified | Sisyphus (parent) |
| 2026-05-31 | ADR-030, ADR-031, ADR-032 created | Sisyphus (parent) |
| 2026-05-31 | ADR Index updated (29→32) | Sisyphus (parent) |
| 2026-05-31 | TestPlan patched (guinevere_db → guinevere) | Sisyphus (parent) |
| 2026-05-31 | OpsManual patched (docs/ prefix removed) | Sisyphus (parent) |
| 2026-05-31 | TDD Guide patched (guinevere_db → guinevere) | Sisyphus (parent) |
| 2026-05-31 | DRPlan rewrite delegated (B2→S3/R2, ~130+ edits) | Sisyphus-Junior (deep, 9m 37s) |
| 2026-05-31 | Pricing correction: $0.02→$0.031/GB for idcloudhost | Sisyphus-Junior (quick) |
| 2026-05-31 | Evidence file written | Sisyphus (parent) |

---

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-31 | Guinevere (Sisyphus) | Initial evidence file documenting conflict resolution |
