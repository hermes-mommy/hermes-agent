---
adr: 032
title: "Backup Storage Strategy — idcloudhost S3 Primary + Cloudflare R2 Backup"
status: "Accepted"
date: "2026-05-31"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - backup
  - storage
  - s3
  - cloudflare
  - r2
  - idcloudhost
  - dr
risk_level: "CRITICAL"
supersedes: "N/A"
related_documents:
  - adr/ADR-025-backup-disaster-recovery-strategy.md
  - Guinevere_APIIntegration_v2.0.md
  - Guinevere_TechnicalArchitecture_v2.0.md
---

# ADR-032: Backup Storage Strategy — idcloudhost S3 Primary + Cloudflare R2 Backup

## Status

Accepted

## Date

2026-05-31

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

backup, storage, s3, cloudflare, r2, idcloudhost, dr

## Risk Level

CRITICAL

## Supersedes

N/A — Supplements ADR-025 (Backup & Disaster Recovery Strategy) with specific storage provider decisions.

## Related Documents

| Document | Relationship |
|---|---|
| [`ADR-025-backup-disaster-recovery-strategy.md`](ADR-025-backup-disaster-recovery-strategy.md) | Parent DR strategy; this ADR specifies the storage provider layer |
| [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md) | Integration constraints for cloud storage providers |
| [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md) | Infrastructure topology including backup targets |

## Context

During cross-reference validation of the Test Plan, DR Plan, and Ops Manual (2026-05-30), a CRITICAL discrepancy was found in backup storage provider references:

| Document | Backup Storage Referenced |
|---|---|
| `Guinevere_DisasterRecoveryPlan_v1.0.md` | Backblaze B2 (~120 references) |
| `Guinevere_InternalOpsManual_v1.0.md` | Cloudflare R2 + idcloudhost S3 |
| `Guinevere_TestPlan_v1.0.md` | No specific provider references |

The DRPlan was written assuming Backblaze B2 as the sole backup storage provider, while the OpsManual was written assuming a dual-provider model (Cloudflare R2 + idcloudhost S3). Neither matched the canonical decision.

### Canonical Decision (per Operator direction and APIIntegration v2.0)

- **Primary backup storage**: idcloudhost S3 (Indonesia-local S3-compatible storage)
- **Secondary backup storage**: Cloudflare R2 (S3-compatible, free egress)
- **NOT used**: Backblaze B2 — removed from the architecture

### Rationale for Provider Selection

**idcloudhost S3 (Primary)**:
- Indonesia-based data residency (aligns with operator's location and potential data sovereignty requirements)
- S3-compatible API — works with standard rclone, boto3, and AWS SDK tooling
- Cost-effective for primary backup storage

**Cloudflare R2 (Secondary)**:
- Zero egress fees — critical for DR restore scenarios where large downloads are needed
- S3-compatible API — same tooling works
- Geographic diversity from idcloudhost (Cloudflare's global network)
- Free tier includes 10GB storage + 10M Class A operations/month

**Backblaze B2 (Removed)**:
- Was the original default in early DR planning
- Replaced by the dual-provider model above for better cost structure (R2 free egress) and data residency (idcloudhost Indonesia)

## Decision Drivers

- Data residency: primary storage in Indonesia aligns with operator requirements.
- Cost optimization: R2 free egress dramatically reduces DR drill and actual recovery costs.
- Redundancy: dual-provider model protects against single-provider outage.
- Tooling compatibility: both providers support S3 API, so existing rclone/boto3 scripts work with minimal changes.
- Consistency: all operational docs must reference the same provider set.

## Considered Options

1. Backblaze B2 only (original DRPlan assumption)
2. Cloudflare R2 only
3. **idcloudhost S3 primary + Cloudflare R2 secondary (chosen)**
4. AWS S3 + R2
5. Multi-provider with B2 + R2 + S3

## Decision Outcome

Chosen option: **idcloudhost S3 primary + Cloudflare R2 secondary, no Backblaze B2**.

### Storage Roles

| Role | Provider | Bucket Name | Purpose |
|---|---|---|---|
| Primary backup | idcloudhost S3 | `guinevere-dr-backups` | Daily/weekly/monthly/yearly backups, WAL archives, evidence sync |
| Secondary backup | Cloudflare R2 | `guinevere-dr-backups` | Cross-region replica, DR drill downloads (free egress) |

### rclone Configuration

```ini
[idcloudhost]
type = s3
provider = Other
access_key_id = <from sops>
secret_access_key = <from sops>
endpoint = https://s3.idcloudhost.com
region = id

[r2]
type = s3
provider = Cloudflare
access_key_id = <from sops>
secret_access_key = <from sops>
endpoint = https://<account-id>.r2.cloudflarestorage.com
region = auto
```

### rclone Command Patterns

```bash
# Upload to primary (idcloudhost S3)
rclone copyto "$LOCAL_FILE" "idcloudhost:guinevere-dr-backups/$REMOTE_PATH"

# Replicate to secondary (Cloudflare R2)
rclone copyto "$LOCAL_FILE" "r2:guinevere-dr-backups/$REMOTE_PATH"

# Restore from secondary (free egress)
rclone copy "r2:guinevere-dr-backups/daily/" "$RESTORE_DIR/daily/"
```

### Pricing (verified 2026-05-31)

| Provider | Storage/GB/bulan | Egress | Free Tier |
|---|---|---|---|
| idcloudhost S3 (primary) | **Rp 507** (flat) | Included in pricing | N/A |
| Cloudflare R2 (secondary) | **$0.015** (~Rp 245) | **GRATIS** | 10 GB storage + 1M Class A ops + 10M Class B ops/month |

**Estimated monthly cost (asumsi ~50 GB total backup footprint)**:
- idcloudhost S3: 50 GB × Rp 507 = **Rp 25.350**
- Cloudflare R2: (50 GB - 10 GB free) × $0.015 = 40 GB × Rp 245 = **Rp 9.800**
- **Total: ~Rp 35.150/bulan** (~$2.15 USD)

> Note: R2 operations cost (Class A: $4.50/million, Class B: $0.36/million) negligible untuk backup workload (write-then-rarely-read pattern).

### Retention Policy (unchanged from ADR-025)

| Tier | Count | Retention | Storage |
|---|---|---|---|
| Daily | 7 | Last 7 days | idcloudhost S3 + R2 + local |
| Weekly | 4 | Sunday backups for 4 weeks | idcloudhost S3 + R2 |
| Monthly | 6 | 1st-of-month for 6 months | idcloudhost S3 + R2 |
| Yearly | 2 | January backups for 2 years | idcloudhost S3 + R2 |
| Permanent | Unlimited | Audit trail, evidence, keys | idcloudhost S3 + R2 |

## Consequences

### Positive

- Eliminates CRITICAL cross-document inconsistency on backup provider.
- R2 free egress reduces DR drill costs significantly vs B2.
- idcloudhost S3 provides Indonesia-local data residency.
- Dual-provider redundancy protects against single-provider failure.

### Negative

- Requires comprehensive rewrite of DRPlan (~120 Backblaze B2 references).
- Dual-provider adds slight operational complexity (rclone config for 2 remotes).
- Pricing calculations in DRPlan use Rp 507/GB (≈$0.031/GB) for idcloudhost S3 and $0.015/GB for Cloudflare R2.

### Risks

- idcloudhost S3 is a smaller provider — monitor for SLA compliance and uptime.
- If idcloudhost S3 has extended outage, R2 serves as failover (and vice versa).
- Pricing models differ from B2 — cost estimates need validation against actual usage.

## Implementation Notes

- DRPlan v1.0 has been comprehensively patched: all ~120 Backblaze B2 references replaced with idcloudhost S3 (primary) and Cloudflare R2 (secondary).
- OpsManual v1.0 already used the correct R2 + S3 providers — no changes needed.
- All rclone commands updated from `b2:guinevere-dr-backups` to `idcloudhost:guinevere-dr-backups` (primary) and `r2:guinevere-dr-backups` (secondary).
- Pricing section in DRPlan recalculated based on idcloudhost S3 and Cloudflare R2 pricing.
- Mermaid diagrams updated to show dual-provider topology.
- Future docs must reference this ADR when specifying backup storage.

## Links

- [`ADR-025-backup-disaster-recovery-strategy.md`](ADR-025-backup-disaster-recovery-strategy.md)
- [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md)
- [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)

## Review Record

- Reviewer: Guinevere (Sisyphus orchestrator)
- Review Date: 2026-05-31
- Decision: Accepted
- Notes: Supplements ADR-025 with specific provider decisions. DRPlan comprehensively patched. B2 fully removed from architecture.

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-31 | Guinevere (Sisyphus) | Initial ADR establishing idcloudhost S3 primary + Cloudflare R2 secondary backup storage, removing Backblaze B2. |
