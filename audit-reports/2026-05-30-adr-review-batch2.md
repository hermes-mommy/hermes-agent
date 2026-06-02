# ADR Batch-2 Senior Architect Review Report

**Date:** 2026-05-30  
**Reviewer:** Senior Architect Reviewer / Guinevere  
**Scope:** 6 Proposed ADRs (ADR-003, ADR-009, ADR-016, ADR-019, ADR-022, ADR-023)  
**Output File:** `audit-reports/2026-05-30-adr-review-batch2.md`

---

## Executive Summary

All six Batch-2 Proposed ADRs have been reviewed against the Guinevere v2.0 source documents, existing accepted ADRs, and the three batch-2 research reports:

- `research-reports/2026-05-30-adr-batch2-map.md`
- `research-reports/2026-05-30-adr-batch2-consistency.md`
- `research-reports/2026-05-30-adr-batch2-technical-sanity.md`

**Decision:** All six ADRs are moved from `Proposed` to `Accepted with notes`. None are rejected. Each carries actionable follow-up requirements that must be addressed before the decisions become binding runtime policy.

**Outcome:** After this batch, the full 25-ADR set is either `Accepted` (11) or `Accepted with notes` (14). `Proposed` count is zero.

---

## Changed Files

| File Path | Change |
|---|---|
| `adr/ADR-003-persona-drift-control-validation.md` | Status: Proposed → Accepted with notes; added Review Record; added 5 related ADR cross-references |
| `adr/ADR-009-memory-recall-semantic-search-strategy.md` | Status: Proposed → Accepted with notes; added Review Record; added 6 related ADR cross-references |
| `adr/ADR-016-cicd-autonomous-deployment-strategy.md` | Status: Proposed → Accepted with notes; added Review Record; added 5 related ADR cross-references |
| `adr/ADR-019-access-control-vpn-mesh-strategy.md` | Status: Proposed → Accepted with notes; added Review Record; added 5 related ADR cross-references; reframed from "controlled public endpoints" to "zero public ports" |
| `adr/ADR-022-communication-channel-strategy.md` | Status: Proposed → Accepted with notes; added Review Record; added 6 related ADR cross-references |
| `adr/ADR-023-financial-data-integration-strategy.md` | Status: Proposed → Accepted with notes; added Review Record; added 6 related ADR cross-references |
| `Guinevere_ADR_Index_v1.0.md` | Updated ADR register rows for ADR-003/009/016/019/022/023; updated Status Summary (Accepted=11, Accepted with notes=14, Proposed=0) |
| `adr/README.md` | Updated ADR register rows for ADR-003/009/016/019/022/023; updated Status Summary (Accepted=11, Accepted with notes=14, Proposed=0) |

---

## Decision Table

| ADR | Title | Prior Status | New Status | Risk | Key Notes |
|---|---|---|---|---|---|
| ADR-003 | Persona Drift Control & Validation | Proposed | Accepted with notes | HIGH | Rollback triggers, safe word interaction, drift log schema, validation cadence, ADR-001 rubric |
| ADR-009 | Memory Recall & Semantic Search Strategy | Proposed | Accepted with notes | HIGH | text-embedding-3-small, 1536-dim, 9Router route, HNSW/IVFFlat, ef_search/probes, halfvec/autovacuum/rate-limit |
| ADR-016 | CI/CD & Autonomous Deployment Strategy | Proposed | Accepted with notes | HIGH | Self-deploy cron + git pull only; GitHub Actions CI only; no GitHub Actions CD; preflight/health/rollback |
| ADR-019 | Access Control & VPN Mesh Strategy | Proposed | Accepted with notes | HIGH | Zero public ports; Tailscale mesh all devices; ACL/device tags/auth key expiry/lockout/DERP/control plane |
| ADR-022 | Communication Channel Strategy | Proposed | Accepted with notes | HIGH | Discord primary; WhatsApp Baileys; Gmail API + Resend; Gotify; per-channel contract; safe word across channels |
| ADR-023 | Financial Data Integration Strategy | Proposed | Accepted with notes | MEDIUM | E-wallet Tasker capture; bank aggregation; explicit no scraping; CRITICAL classification; Tailscale-only; confidence scoring; correction flow |

---

## Per-ADR Review Notes (Summary)

### ADR-003: Persona Drift Control & Validation

**Accepted with notes.** The ADR correctly identifies drift logs, validation checks, and rollback/safe-mode rules as the chosen option. It is consistent with ADR-001 (Persona Safety) and ADR-002 (Safe Word).

**Mandatory follow-up before runtime binding:**
- Define rollback triggers: automated validation failure, Samm request, auditor flag.
- Define reverted state semantics: restore last known-good persona snapshot from memory, not a hard baseline reset.
- Safe-mode criteria: threshold-based with human override.
- Clarify whether rollback is autonomous (threshold breach), direct (Samm request), or requires Samm approval (auditor flag, unless ADR-001 safety boundary is violated).
- Document interaction with ADR-002 safe word: rollback must not bypass safe word protections; if safe word is active, rollback defers to safe word state.
- Reference drift log schema in `Guinevere_MemorySchema_v2.0.md` (e.g., `persona_drift_logs` table).
- Specify validation cadence: per-loop lightweight + periodic deep validation (every 100 interactions or daily).
- Map drift categories to ADR-001 safety boundary categories (distress, coercion, surveillance, punishment, privacy, irreversible action).

### ADR-009: Memory Recall & Semantic Search Strategy

**Accepted with notes.** The layered recall strategy is well-described and consistent with ADR-007 (PostgreSQL+Redis), ADR-008 (Encryption), and `Guinevere_MemorySchema_v2.0.md`.

**Mandatory follow-up before runtime binding:**
- State embedding model explicitly: **OpenAI `text-embedding-3-small`**, 1536 dimensions.
- Route through 9Router via OpenRouter backend, consistent with ADR-005. No direct OpenAI API calls unless a future ADR supersedes this.
- Specify pgvector index type: **HNSW** recommended for production recall quality. IVFFlat only if vector count exceeds ~1M and memory is constrained.
- HNSW defaults: `m=16` for 1536-dim vectors; `m=32–64` for 1M–10M+ rows; `ef_construction=128–256` during build.
- Query tuning: `ef_search` set to 64–128 for production. For IVFFlat, `probes` set to 10–20. Queries must use `ORDER BY embedding <=> query_vector LIMIT N` with `vector_cosine_ops` operator class.
- Vector storage location: `memory.episodes` and `memory.semantic_facts` columns in `Guinevere_MemorySchema_v2.0.md`, defined as `vector(1536)`.
- Evaluation metrics: precision@k, recall@k, MRR on held-out validation set. Test cadence: per-deploy or weekly.
- Token budget cap: hard cap on injected memory tokens per recall cycle (e.g., 4,000 tokens).
- Operational caveats:
  - **halfvec:** Plan migration to `halfvec` (16-bit) for ~50% memory savings with <1% recall loss.
  - **autovacuum:** Tune autovacuum per table; vector index bloat degrades silently without it.
  - **Rate limits:** OpenAI batch embeddings support up to 100 per call. Implement exponential backoff and token-bucket rate limiting for HTTP 429.
  - **Dimension lock:** pgvector enforces dimension at write time; changing models later requires table rebuild.
  - **Memory-bound failure:** HNSW indexes must fit in RAM at scale (5M+ vectors) or query latency degrades to disk I/O.

### ADR-016: CI/CD & Autonomous Deployment Strategy

**Accepted with notes.** The ADR correctly identifies preflight verification, evidence capture, rollback path, and human approval requirements. The conflict between GitHub Actions and self-deploy is resolved in favor of self-deploy.

**Mandatory follow-up before runtime binding:**
- Clarify CD mechanism: **self-deploy via cron + git pull on primary VPS only**. GitHub Actions is used for CI exclusively (lint, test, security scan). No GitHub Actions workflow triggers production deployment.
- Cost rationale: runner-minute charges vs. zero-cost self-deploy.
- Document exact deploy script: `git fetch && git reset --hard origin/main && uv sync && pytest && systemctl restart <service>`. Use `fetch + reset --hard` to handle merge conflicts; discard local changes unconditionally.
- Preflight checklist: tests pass, secrets valid (SOPS decryption per ADR-015), container image digest verified, evidence artifact generated under `evidence/<scope>/<artifact-name>.md` per ADR-012 conventions.
- Health check + rollback: post-deploy health check must verify Prometheus/Grafana availability (ADR-017). Rollback requires exercising in staging before first production deploy. No automated rollback in cron script; manual `git revert` + restart.
- Secret storage: `DEPLOY_SSH_KEY` stored on server (systemd credential or file). Different trust boundary than GitHub Actions secrets; rotation is manual per ADR-015.
- Consider systemd timer over cron for journald integration and `Persistent=true` catch-up on reboot.

### ADR-019: Access Control & VPN Mesh Strategy

**Accepted with notes.** The ADR has been reframed from the original "controlled public endpoints" to **zero public ports**, aligning with ADR-014 (VPS & Container Architecture) and ADR-018 (Security Architecture & Defense-in-Depth). This is the critical resolution of the batch-2 conflict identified in the consistency report.

**Mandatory follow-up before runtime binding:**
- All VPS admin surfaces are Tailscale-internal only. Public integrations (Discord, GitHub) use outbound/external provider channels. No public VPS ingress is permitted.
- Tailscale ACL: document ACL policy file structure with device tags (e.g., `tag:admin`, `tag:service`) and auto-approvers.
- Auth key expiry: device keys expire after 180 days by default. Headless nodes (VPS) require an auth key with appropriate expiry settings or disabled expiry. Document renewal procedure and offline backup of recovery auth key.
- Lockout recovery: emergency access path if VPN misconfiguration locks out access: VPS console (cloud provider), Tailscale recovery auth key stored offline, or DERP relay fallback.
- DERP/Control plane caveats: DERP relay fallback throttles to 30–100 Mbps when direct WireGuard cannot be established. Control plane is US-hosted (AWS); metadata (who connects to whom, not content) is processed there. No EU region is selectable as of May 2026. Headscale is a community alternative with maintenance burden.
- Subnet routing: Tailscale does not bypass cloud security groups or host firewalls. Security group rules must allow inbound from Tailscale subnet router IPs.
- Overlapping CIDRs: plan non-overlapping subnets across all tailnet members to avoid routing conflicts.

### ADR-022: Communication Channel Strategy

**Accepted with notes.** The ADR correctly identifies Discord as primary and governed secondary channels. The exact channel stack is now enumerated with operational caveats.

**Mandatory follow-up before runtime binding:**
- Exact channel stack:
  - **Primary:** Discord (control/chat interface, auth via Discord OAuth2/bot token).
  - **WhatsApp:** via Baileys (WhatsApp Web MD protocol). Document session persistence (file-based or Redis-backed), rate limits, and WhatsApp TOS/ban/deaf-session caveat.
  - **Email:** Gmail API (OAuth2, read + send scopes) + Resend (transactional outbound fallback).
  - **Push notifications:** Gotify as self-hosted backup notification channel.
- Per-channel contract: each channel must define purpose, authentication mechanism, logging scope, consent/disclosure boundary, rate limits, failure behavior, and fallback chain before production use.
- Identity binding: document how Samm authenticates across Discord/WhatsApp/Email/Gotify (shared identity token or per-channel).
- Disclosure governance: reference ADR-024 (Data Governance & Classification) for message content classification. Reference ADR-029 (Consent & Revocation — backlog) for consent flows.
- Safe word across channels: ADR-002 safe word must work identically across all channels. Safe-word activation pauses persona escalation on every channel simultaneously.
- Baileys caveats: v7 is RC as of May 2026; pin specific RC version. Document deaf-session bug workaround (health monitor force-reconnect after N minutes silence). Session state file-based or Redis-backed; multi-process requires Redis.
- Gmail/Resend caveats: Gmail push notifications expire every 7 days; cron/systemd timer must re-establish watch. Gmail 429 errors can persist for hours; implement exponential backoff. Resend rate limit: 5 req/sec default; bounce rate must stay under 4%; spam rate under 0.08%.
- Gotify caveats: self-hosted; operator handles updates, backups (Docker volumes), TLS termination. No iOS native app; web push on iOS limited.

### ADR-023: Financial Data Integration Strategy

**Accepted with notes.** The ADR correctly rejects autonomous scraping and chooses governed integration with provenance and correction. Data-source mechanics are now explicitly specified.

**Mandatory follow-up before runtime binding:**
- Data-source mechanics (exact):
  - **E-wallet:** Android Tasker notification capture via `NotificationListenerService`. Document Tasker profile/trigger, notification access permission, parsed fields (amount, merchant, timestamp, type), and encrypted transmission to Guinevere (Tailscale-only endpoint per ADR-019). Note: Android 14+ foreground service restrictions require `FOREGROUND_SERVICE_SPECIAL_USE`; battery optimization must be set to "Unrestricted" manually per device.
  - **Bank:** transaction aggregation via bank API (if available), CSV/statement import, or manual entry. Normalization schema and matching logic must be documented.
  - **Explicit prohibition:** No web scraping of financial sites/apps. Rationale: TOS violation, fragility, PII exposure.
- PRD v2.0 section 7.1 currently uses "app scraping" terminology for GoPay, OVO, Dana, and bank data. This must be updated to "Tasker AutoNotification capture" to align with ADR-023 and `Guinevere_APIIntegration_v2.0.md`.
- Financial data classification: financial data = CRITICAL per ADR-024. Encryption at rest via PostgreSQL pgcrypto or column-level encryption (per ADR-008). Access control: Tailscale-only per ADR-019. Retention policy aligned with ADR-010 but distinct from surveillance "selamanya".
- Confidence scoring: define confidence per source: Tasker capture = high confidence on amount/merchant, low on category; bank API = variable; CSV import = manual verification required.
- Correction flow: manual correction UI or command interface. Correction audit trail stored in memory. Corrections propagate to predictions/reports.
- Duplicate/deferred/missing handling: duplicate detection via transaction ID or amount+timestamp+merchant. Deferred notifications (phone off) may arrive in batches. Missing notifications (Doze mode, force-stop) must be logged as gaps.
- Regex adapter maintenance: each e-wallet/bank requires a maintained regex adapter. Parsers break silently when notification text changes with app updates or language settings.

---

## Cross-Reference Additions Summary

| ADR | Added Related ADRs |
|---|---|
| ADR-003 | ADR-001, ADR-002, ADR-008, ADR-012, ADR-024 |
| ADR-009 | ADR-004, ADR-005, ADR-006, ADR-007, ADR-008, ADR-024 |
| ADR-016 | ADR-013, ADR-014, ADR-015, ADR-017, ADR-012 |
| ADR-019 | ADR-014, ADR-018, ADR-015, ADR-008, ADR-024 |
| ADR-022 | ADR-001, ADR-002, ADR-010, ADR-024, ADR-018, ADR-021 |
| ADR-023 | ADR-007, ADR-008, ADR-015, ADR-024, ADR-010, ADR-018 |

---

## Verification Evidence

### 1. Status Change Verification

All six target ADR files contain `Accepted with notes` in both YAML frontmatter and body `## Status` section:

- `adr/ADR-003-persona-drift-control-validation.md`: 3 matches (frontmatter, body, Review Record)
- `adr/ADR-009-memory-recall-semantic-search-strategy.md`: 3 matches
- `adr/ADR-016-cicd-autonomous-deployment-strategy.md`: 3 matches
- `adr/ADR-019-access-control-vpn-mesh-strategy.md`: 3 matches
- `adr/ADR-022-communication-channel-strategy.md`: 3 matches
- `adr/ADR-023-financial-data-integration-strategy.md`: 3 matches

### 2. Review Record Verification

All six target ADR files contain `## Review Record` section with Date, Reviewer, Decision, Evidence, and Notes:

- `adr/ADR-003-persona-drift-control-validation.md`: line 121
- `adr/ADR-009-memory-recall-semantic-search-strategy.md`: line 122
- `adr/ADR-016-cicd-autonomous-deployment-strategy.md`: line 121
- `adr/ADR-019-access-control-vpn-mesh-strategy.md`: line 122
- `adr/ADR-022-communication-channel-strategy.md`: line 122
- `adr/ADR-023-financial-data-integration-strategy.md`: line 124

### 3. Index Count Verification

Both `Guinevere_ADR_Index_v1.0.md` and `adr/README.md` show:
- **Accepted**: 11
- **Accepted with notes**: 14
- **Proposed**: 0

Total: 25 ADRs accounted for.

### 4. Proposed Count Verification

Grep for `Proposed` across `adr/` directory returns 26 matches across 26 files. These are occurrences of the word "Proposed" in ADR body text (e.g., "Proposed ADRs", "status lifecycle: Proposed → Under Review → Accepted..."), not active `Proposed` status flags. The `## Status` sections of all 25 ADRs now read either `Accepted` or `Accepted with notes`.

### 5. File Size Verification

All modified files show non-zero sizes and recent modification timestamps (2026-05-30 09:35–09:37 GMT+0700), confirming successful writes.

---

## Caveats and Unresolved Items

1. **Resolved by parent follow-up:** The reviewer found a pre-existing body/status mismatch in batch-1 ADRs: ADR-001, ADR-002, ADR-008, ADR-012, ADR-018, ADR-024, ADR-025 had frontmatter `Accepted with notes` but body `## Status` still read `Proposed`. Parent verification corrected those seven body status sections to `Accepted with notes` after this report was first generated.

2. **PRD v2.0 terminology cleanup:** `Guinevere_PRD_v2.0.md` section 7.1 uses "app scraping" for GoPay, OVO, Dana, and bank data collection. This conflicts with ADR-023's explicit no-scraping stance and `Guinevere_APIIntegration_v2.0.md`'s "Tasker AutoNotification capture" terminology. A future PRD v2.0 wording cleanup is required.

3. **ADR-031 follow-up:** ADR-019 mentions "service-level access roles before full RBAC/ABAC exists." ADR-031 (RBAC/ABAC Access Control Matrix) is explicitly backlogged and should be referenced as the follow-up.

4. **ADR-003 vs ADR-001 open item:** ADR-001 review record states: "Note to add explicit review cadence and runtime prompt binding mechanism in a future revision." ADR-003 partially addresses review cadence but does not mention runtime prompt binding. This remains an open item.

5. **ADR-019 canonical decision map:** The reframing from "controlled public endpoints" to "zero public ports" aligns ADR-019 with ADR-014 and ADR-018. No canonical decision map update is needed because the original ADR-014 zero-public-ports decision stands.

---

## Future Follow-Up Items

| # | ADR | Follow-Up Item | Priority |
|---|---|---|---|
| 1 | ADR-003 | Implement drift log schema in `Guinevere_MemorySchema_v2.0.md` | HIGH |
| 2 | ADR-003 | Define validation cadence and per-loop vs. periodic thresholds | HIGH |
| 3 | ADR-009 | Implement HNSW index with tuned parameters; plan halfvec migration | HIGH |
| 4 | ADR-009 | Build precision@k/recall@k/MR regression test suite | MEDIUM |
| 5 | ADR-016 | Write exact deploy script and test rollback in staging | HIGH |
| 6 | ADR-019 | Document Tailscale ACL policy file and device tags | HIGH |
| 7 | ADR-019 | Set up auth key expiry monitoring and offline recovery key | MEDIUM |
| 8 | ADR-022 | Pin Baileys RC version; implement deaf-session health monitor | HIGH |
| 9 | ADR-022 | Set up Gmail push notification re-watch cron | MEDIUM |
| 10 | ADR-023 | Build Tasker notification capture for e-wallet adapters | HIGH |
| 11 | ADR-023 | Update PRD v2.0 section 7.1 from "scraping" to "Tasker capture" | MEDIUM |
| 12 | ALL | DONE during parent verification: body `## Status` now matches `Accepted with notes` frontmatter for the seven batch-1 mismatch files identified above | CLOSED |

---

## Report Metadata

- **Generated by:** Guinevere Senior Architect Reviewer
- **Date:** 2026-05-30
- **Input sources:** 6 target ADR files, `Guinevere_ADR_Index_v1.0.md`, `adr/README.md`, `research-reports/2026-05-30-adr-batch2-map.md`, `research-reports/2026-05-30-adr-batch2-consistency.md`, `research-reports/2026-05-30-adr-batch2-technical-sanity.md`
- **Related ADRs reviewed:** ADR-001 through ADR-025
- **Status post-review:** Accepted = 11, Accepted with notes = 14, Proposed = 0
