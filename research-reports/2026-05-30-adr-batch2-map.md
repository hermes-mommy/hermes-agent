# Batch-2 Proposed ADR Map — Project Guinevere

**Date:** 2026-05-30  
**Scope:** ADR-003, ADR-009, ADR-016, ADR-019, ADR-022, ADR-023  
**Purpose:** Review decisions/notes to guide parent synthesis and reviewer sub-agent edits.  
**Sources read:** All six ADR files, `Guinevere_ADR_Index_v1.0.md`, `adr/README.md`.

---

## Executive Summary

All six Batch-2 ADRs are structurally complete and internally consistent. They inherit the canonical v2.0 decisions correctly and follow MADR format. **None should be rejected.** All six should move to **Accepted with notes** because each needs tighter technical specifications aligned with the user's special context before binding runtime policy.

| ADR | Current Status | Recommended Decision | Primary Gap |
|---|---|---|---|
| ADR-003 | Proposed | Accepted with notes | Rollback mechanism not explicitly specified |
| ADR-009 | Proposed | Accepted with notes | Embedding model + vector index config missing |
| ADR-016 | Proposed | Accepted with notes | GitHub Actions vs cron+git-pull conflict unresolved |
| ADR-019 | Proposed | Accepted with notes | Zero-public-port intent not reflected in current text |
| ADR-022 | Proposed | Accepted with notes | Channel stack (Baileys/Gmail/Resend/Gotify) not enumerated |
| ADR-023 | Proposed | Accepted with notes | Data-source mechanics (Tasker/aggregation/no-scraping) missing |

---

## Per-ADR Review

### ADR-003 — Persona Drift Control & Validation

**Verdict: Accepted with notes**

**Completeness:** High. Context, Decision Drivers, Considered Options, Decision Outcome, Consequences, Implementation Notes all present.  
**Consistency:** Consistent with ADR-001 (Persona Safety) and v2.0 persona docs.  
**Technical accuracy:** Correctly identifies drift logs, validation, and rollback as needed.  
**Actionability:** Needs specifics before implementation.

**Notes to append:**
- Add explicit **rollback mechanism**: specify whether rollback restores last known-good persona state from memory, resets to baseline persona doc, or uses snapshot branching. Document safe-mode trigger criteria (threshold-based vs human-initiated).
- Add **drift log schema** reference: link to specific table/schema in `Guinevere_MemorySchema_v2.0.md` (e.g., `persona_drift_logs` with timestamp, drift_vector, trigger, reviewer, action).
- Add **validation cadence**: per-loop vs periodic. If periodic, specify interval (e.g., every 100 interactions or daily).
- Add **review rubric**: what constitutes "harmful or off-brand behavior" — tie to ADR-001 safety boundary categories.

---

### ADR-009 — Memory Recall & Semantic Search Strategy

**Verdict: Accepted with notes**

**Completeness:** High. Layered recall strategy well described.  
**Consistency:** Aligned with ADR-007 (PostgreSQL+Redis), ADR-008 (Encryption), and `Guinevere_MemorySchema_v2.0.md`.  
**Technical accuracy:** Conceptually correct.  
**Actionability:** Needs embedding and index specifics.

**Notes to append:**
- Hard-code embedding provider: **OpenAI `text-embedding-3-small`**, 1536 dimensions. Add fallback behavior if API unavailable.
- Specify **pgvector index type**: HNSW (recommended for recall quality) or IVFFlat (if memory scale > 1M vectors). Include `ef_search` / `probes` tuning guidance.
- Add **vector storage location**: which PostgreSQL table/column, naming convention, and alignment with `Guinevere_MemorySchema_v2.0.md` embedding fields.
- Add **recall evaluation methodology**: define metrics (precision@k, recall@k, MRR) and regression test cadence.
- Add **token budget enforcement**: hard cap on injected memory tokens per recall cycle.

---

### ADR-016 — CI/CD & Autonomous Deployment Strategy

**Verdict: Accepted with notes**

**Completeness:** High. Preflight, evidence, rollback, approval gates covered.  
**Consistency:** Aligned with ADR-011 (7-phase SDLC), ADR-013 (MCP native), ADR-014 (VPS/Container), ADR-015 (Secrets).  
**Technical accuracy:** Conceptually sound.  
**Actionability:** Has internal tension between GitHub Actions and cron+git-pull.

**Notes to append:**
- Resolve the **GitHub Actions vs cron+git-pull** conflict: current Context section mentions "architecture includes GitHub Actions" but user special context specifies **self-deploy via cron + git pull, no GitHub Actions CD because cost concern**. Make this explicit: GitHub Actions may remain for PR lint/test (CI only), CD is cron+git-pull on primary VPS.
- Add **cost rationale**: document why GitHub Actions CD is excluded (cost per runner-minute vs zero-cost self-deploy).
- Add **rollback tested clause**: require rollback to be exercised in staging before first production deploy.
- Add **preflight checklist reference**: link to or enumerate concrete checks (tests pass, secrets valid, container image digest verified, evidence artifact generated).

---

### ADR-019 — Access Control & VPN Mesh Strategy

**Verdict: Accepted with notes**

**Completeness:** High. VPN-first with public endpoint acknowledgment.  
**Consistency:** Aligned with ADR-014 (VPS), ADR-015 (Secrets), ADR-018 (Security Architecture), ADR-024 (Data Governance).  
**Technical accuracy:** Sound approach.  
**Actionability:** Needs alignment with zero-public-ports intent.

**Notes to append:**
- Resolve **zero public ports** vs "controlled public endpoints": user context specifies Tailscale mesh all devices, zero public ports. Current text still allows Caddy + firewall public ingress. Clarify: either eliminate public endpoints entirely (Tailscale funnel/exit node for outbound, Tailscale serve for selective inbound) or document which services legitimately need public ingress and why.
- Add **Tailscale ACL reference**: document ACL policy file structure, device tagging (e.g., `tag:admin`, `tag:service`), and auto-approvers.
- Add **service token scope**: specify how service-level tokens interact with network controls (mTLS, Tailscale auth keys with expiry).
- Add **lockout recovery**: documented emergency access path if VPN misconfiguration occurs (e.g., VPS console, Tailscale recovery auth key stored offline).

---

### ADR-022 — Communication Channel Strategy

**Verdict: Accepted with notes**

**Completeness:** High. Channel governance framework clear.  
**Consistency:** Aligned with ADR-018 (Security), ADR-024 (Data Governance), ADR-029 (Consent — backlog).  
**Technical accuracy:** Framework is correct.  
**Actionability:** Channel stack needs explicit enumeration.

**Notes to append:**
- Enumerate the **exact channel stack** per user context:
  - **Primary:** Discord (control/chat interface, auth via Discord OAuth2/bot token)
  - **WhatsApp:** via Baileys ( WhatsApp Web MD protocol), document Baileys session persistence, rate limits, and WhatsApp TOS risk
  - **Email:** Gmail API (OAuth2, send + read scopes) + Resend (transactional outbound fallback)
  - **Push notifications:** Gotify as backup notification channel (self-hosted, no external dependency)
- Add **per-channel contract** requirements: purpose, authentication mechanism, logging scope, consent/disclosure boundary, rate limits, failure behavior, and fallback chain.
- Add **cross-channel identity binding**: how does Samm authenticate across Discord/WhatsApp/Email/Gotify — shared identity token or per-channel?
- Add **disclosure governance**: reference ADR-029 (Consent & Revocation — backlog) and ADR-024 for data classification of message content.

---

### ADR-023 — Financial Data Integration Strategy

**Verdict: Accepted with notes**

**Completeness:** High. Provenance, correction, privacy-aware reporting covered.  
**Consistency:** Aligned with ADR-007 (Memory), ADR-008 (Encryption), ADR-024 (Data Governance), ADR-023 itself.  
**Technical accuracy:** Conceptually sound.  
**Actionability:** Data-source mechanics need explicit specification.

**Notes to append:**
- Enumerate **data-source mechanics** per user context:
  - **E-wallet:** Tasker notification capture on Android — document Tasker profile/trigger, notification access permission, parsed fields, and transmission to Guinevere (encrypted endpoint). Add Android-side security note.
  - **Bank:** transaction aggregation — document aggregation source (bank API if available, or CSV/statement import), normalization schema, and matching logic.
  - **Explicit prohibition:** no web scraping of financial sites. Document rationale: TOS violation, fragility, PII exposure.
- Add **data classification**: financial data = CRITICAL per ADR-024. Specify encryption at rest (PostgreSQL pgcrypto or column-level), access control (Tailscale-only per ADR-019), and retention policy alignment.
- Add **confidence scoring**: define what "confidence" means per data source (Tasker capture = high confidence on amount/merchant, low on category; aggregation = variable).
- Add **correction flow**: manual correction UI or command interface, correction audit trail, and how corrections propagate to predictions/reports.

---

## Cross-ADR Observations

1. **ADR-019 vs ADR-018 tension**: ADR-019 still permits "controlled public endpoints" while user context says zero public ports. ADR-018 (Security Architecture, Accepted with notes) should be checked for consistency on this point before ADR-019 is finalized.

2. **ADR-016 vs ADR-014**: ADR-014 (VPS & Container Architecture) accepted; ADR-016 self-deploy via cron+git-pull should reference ADR-014 container registry and image promotion flow explicitly.

3. **ADR-022 channel stack vs ADR-015 (Secrets)**: Baileys session data, Gmail OAuth tokens, and Resend API keys need secrets management per ADR-015 (SOPS + age). Cross-reference should be explicit.

4. **ADR-023 vs ADR-008/024**: Financial data encryption and classification need to cite ADR-008 and ADR-024 specifically, not just generically.

5. **Batch-2 gap vs backlog**: ADR-031 (RBAC/ABAC Access Control Matrix) is explicitly backlogged. ADR-019's "service-level access roles before full RBAC" is a placeholder that should reference ADR-031 as the follow-up.

6. **ADR-003 vs ADR-001**: Both are CRITICAL/HIGH persona ADRs. ADR-003 should explicitly reference ADR-001's safe-word principle as a rollback trigger condition.

---

## Recommended Next Steps for Reviewer Sub-Agent

1. Edit each ADR's "Notes to append" section into the file (after Implementation Notes, before Links).
2. Update status from `Proposed` to `Accepted with notes` in YAML frontmatter and Status section.
3. Add `review_date`, `reviewer`, and `decision` fields matching ADR-001 pattern (lines 124-129).
4. Update `Guinevere_ADR_Index_v1.0.md` and `adr/README.md` status counts: Proposed drops from 6 to 0; Accepted with notes rises from 8 to 14.
5. Verify cross-references in the ADRs resolve to actual v2.0 doc sections (section-level, not just file-level).

---

*Report generated by Guinevere sub-agent research. Read-only analysis; no files modified.*
