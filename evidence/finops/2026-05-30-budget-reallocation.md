---
title: "Evidence: Budget Reallocation for ADR-032 Dual-Provider Storage"
date: "2026-05-31"
author: "Guinevere (Sisyphus orchestrator)"
scope: "Cost & FinOps Model v1.0 → v1.1 budget rebalance"
related_adrs:
  - ADR-032 (Backup Storage Strategy)
  - ADR-025 (Backup & DR Strategy)
---

# Evidence: Budget Reallocation for ADR-032 Dual-Provider Storage

## 1. Context

ADR-032 (2026-05-31) established idcloudhost S3 (primary) + Cloudflare R2 (secondary) as the backup storage strategy, replacing Backblaze B2. This introduced a significant cost increase:

| Item | v1.0 Budget | v1.1 Budget (Phase 1) | Delta |
|---|---:|---:|---:|
| Backup storage | $2-3/month | $5-6/month | +$3-4 |

The $30/month hard cap is unchanged. Savings must come from other categories.

## 2. DRPlan Storage Cost Projections (per ADR-032)

| Month | Storage (GB) | S3 Cost ($0.031/GB) | R2 Cost ($0.015/GB) | Combined |
|---:|---:|---:|---:|---:|
| 1 | 177.8 | $5.51 | $2.67 | $8.18 |
| 3 | 195 | $6.05 | $2.93 | $8.97 |
| 6 | 245 | $7.60 | $3.68 | $11.27 |
| 9 | 310 | $9.61 | $4.65 | $14.26 |
| 12 | 390 | $12.09 | $5.85 | $17.94 |

**Pricing source:**
- idcloudhost S3: Rp 507/GB/month (flat) ≈ $0.031/GB at Rp 16,300/USD
- Cloudflare R2: $0.015/GB/month storage, FREE egress (verified from official docs 2026-05-31)

## 3. Phased Strategy

### Phase 1 (Month 1-3): S3 Only
- idcloudhost S3 active, Cloudflare R2 deferred (10 GB free tier only)
- Storage budget: $5-6/month
- Total budget: ~$28-30

### Phase 2 (Month 4-6): Dual Provider Activated
- R2 mirror activated for all new backups
- Storage budget: $9-11/month
- Total budget: ~$28-30

### Phase 3 (Month 7-12): Full Dual Provider
- Full dual-provider at projected growth
- Storage budget: $14-18/month
- Total budget: ~$30 (at ceiling)

## 4. Budget Reallocation — Savings Analysis

### v1.0 Budget Ranges (sum: $35-42, constrained to $30)
| Category | v1.0 Target | v1.1 Phase 1 Target | Savings |
|---|---:|---:|---:|
| VPS hostdata.id | $10-12 | $11 | $0 |
| GPT-5.5 via 9Router | $10-12 | $7-8 | **-$2 to -$4** |
| DeepSeek V4 Flash | $0-2 | $1-2 | +$0 to +$1 |
| idcloudhost S3 | $2-3 | $5-6 | +$3-4 |
| Cloudflare R2 | (not budgeted) | $0 | $0 |
| Brave Search | $1-2 | $1 | **-$0 to -$1** |
| Exa AI | $1-2 | $1 | **-$0 to -$1** |
| Resend | $0-1 | $0-0.50 | **-$0 to -$0.50** |
| Misc / contingency | $1-2 | $0-0.50 | **-$0.50 to -$1.50** |
| **Total** | $35-42 | **$28-30** | |

### Where Savings Come From

| Source | Amount Saved | Justification |
|---|---:|---|
| GPT-5.5 budget reduction | $2-4/month | More sub-agent work routed to DeepSeek V4 Flash (free tier). GPT-5.5 reserved for critical synthesis only. Quality risk: moderate — mitigated by DeepSeek V4 quality improvements. |
| Search API reduction | $0-2/month | Aggressive caching of Brave/Exa results. Reuse existing research reports. Quality risk: low — cached results remain valid for most use cases. |
| Misc contingency reduction | $0.50-1.50/month | Tighter buffer. Overages require Samm approval. Risk: low — contingency was rarely fully used. |
| Resend reduction | $0-0.50/month | Prefer Gotify/Discord for notifications. Risk: none — Gotify is self-hosted and free. |
| **Total savings** | **$2.50-8/month** | |

### Savings Reallocated To

| Destination | Amount Added | Justification |
|---|---:|---|
| idcloudhost S3 storage | +$3-4/month | ADR-032 mandates idcloudhost as primary backup. Non-negotiable for data integrity. |
| DeepSeek usage increase | +$0-1/month | Compensates for reduced GPT-5.5 budget with increased free-tier routing. |

## 5. Risk Assessment

| Risk | Severity | Mitigation |
|---|---|---|
| GPT-5.5 quality degradation at lower budget | Medium | Phase-aware routing: GPT-5.5 preserved for safety, conflict resolution, persona drift. DeepSeek handles routine sub-agent work. |
| Phase 3 storage at budget ceiling ($18/month) | High | Trigger rules: Samm review at $14/month, mandatory decision at $18/month. Options: budget increase, retention reduction, or deduplication. |
| Search API budget = $0 in Phase 3 | Medium | All research uses cached results, existing reports, or librarian agents with batched queries. Temporary $1 allocation available from misc if critical. |
| R2 deferred activation delays geo-redundancy | Low | Phase 1 is S3-only for ~3 months. Data loss risk is low during this period since local + S3 copies exist. R2 activates when data grows. |

## 6. Decision Rationale

### Why Not Increase $30 Cap?
The $30 hard cap is a fundamental constraint (Section 2.2 of FinOps Model). Increasing it requires explicit Samm approval and should be a last resort after all optimization options are exhausted.

### Why Not Drop R2 Entirely?
R2 provides free egress (critical for DR drills and actual recovery), geographic diversity, and the 10 GB free tier absorbs early costs. Dropping R2 would mean paying S3 egress fees (~$0.05/GB) for all restore operations.

### Why Phase Approach?
- Phase 1 avoids paying for dual storage when data volume is still manageable with S3 + local copies.
- Phase 2 activates R2 when growth justifies the redundancy premium.
- Phase 3 reflects the steady-state cost with trigger rules for Samm intervention.

### Why Cut GPT-5.5 Rather Than Other Categories?
- GPT-5.5 is the largest variable budget item ($10-12/month).
- DeepSeek V4 Flash has improved significantly and handles most sub-agent work adequately.
- Safety-critical and high-stakes work still routes to GPT-5.5 — no quality reduction for critical paths.
- Infrastructure (VPS) is fixed and non-negotiable.
- Search APIs are already lean at $1-2/month.

## 7. Files Changed

| File | Change Type | Description |
|---|---|---|
| `Guinevere_Cost_FinOps_Model_v1.1.md` | Created | Budget reallocation with phased storage approach |
| `Guinevere_Cost_FinOps_Model_v1.0.md` | Unchanged | Original preserved as baseline |

## 8. Cross-Reference Impact

| Document | Reference to FinOps | Impact |
|---|---|---|
| `Guinevere_DisasterRecoveryPlan_v1.0.md` | Section 10 references FinOps budget | DRPlan now shows $8.19-$17.96/month, consistent with FinOps v1.1 Phase 1-3 |
| `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md` | Normative parent | No change needed — $30 cap unchanged |
| `Guinevere_InternalOpsManual_v1.0.md` | Budget tracking metrics | OpsManual §8 metrics may need update for phased approach |
| `adr/ADR-032-backup-storage-strategy.md` | Storage provider decision | Aligned — FinOps v1.1 reflects ADR-032 pricing |

## 9. Audit Trail

| Timestamp | Action | Agent |
|---|---|---|
| 2026-05-31 | ADR-032 created (backup storage strategy) | Sisyphus (parent) |
| 2026-05-31 | DRPlan pricing corrected ($0.02→$0.031/GB) | Sisyphus-Junior (quick) |
| 2026-05-31 | FinOps Model v1.0 read and analyzed | Sisyphus (parent) |
| 2026-05-31 | Budget reallocation analysis completed | Sisyphus (parent) |
| 2026-05-31 | FinOps Model v1.1 delegation launched | Sisyphus-Junior (writing) |
| 2026-05-31 | Evidence file written | Sisyphus (parent) |

---

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-31 | Guinevere (Sisyphus) | Initial evidence file for budget reallocation |
