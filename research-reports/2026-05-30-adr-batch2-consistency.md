
# ADR Batch-2 Consistency Dependency Report

**Date**: 2026-05-30
**Scope**: 6 Proposed ADRs (ADR-003, ADR-009, ADR-016, ADR-019, ADR-022, ADR-023) against 19 accepted/accepted-with-notes ADRs and v2.0 source documents.
**Purpose**: Pre-review consistency check for parent synthesis before senior architect review.

---

## Executive Summary

Batch-2 Proposed ADRs are broadly consistent with locked canonical decisions (9Router routing, PostgreSQL+Redis, 7-phase SDLC, MCP native, zero SQLite, Prometheus+Grafana primary VPS, wearable post-MVP, obscura+Playwright). However, six material conflicts, multiple missing cross-references, and one status/index inconsistency require resolution before acceptance.

**Critical findings**: 2
**High findings**: 4
**Medium findings**: 6
**Missing cross-references**: 22+ across all 6 ADRs

---

## 1. ADR-003: Persona Drift Control & Validation

### 1.1 Conflict — Underspecified Rollback vs. ADR-001/ADR-002 Autonomy

**Severity**: HIGH
**Status**: Blocking

ADR-003 proposes "rollback/safe-mode rules" for persona drift but does not define the operational mechanism. This creates a direct tension with:

- **ADR-001 (Accepted with notes)**: Section 5.3 of Guinevere_Persona_Document_v2.0.md states: *"Guinevere memiliki otonomi penuh untuk update persona dan memory-nya sendiri tanpa izin Samm."* ADR-003's rollback mechanism must clarify whether it restricts this autonomy or provides a safety override.
- **ADR-002 (Accepted with notes)**: The safe word is defined as a "global architectural override" that pauses persona escalation. ADR-003 does not address how persona rollback interacts with safe word state — does a rollback also reset safe word activation? Can rollback override safe word protections?

**Reviewer Note**: Add explicit rollback semantics:
1. What triggers rollback (automated validation failure vs. Samm request vs. auditor flag)?
2. What state is reverted (persona parameters, memory entries, mood, violation log)?
3. How does rollback interact with ADR-002's safe word state?
4. Does rollback require Samm approval or is it autonomous?

### 1.2 Missing Cross-References

**Severity**: MEDIUM
**Status**: Blocking for acceptance

ADR-003 Related Documents section only cites v2.0 source docs (Persona_Document, MemorySchema, AgentLoopSpec). It does NOT cite any of the 8 CRITICAL/HIGH-risk accepted ADRs that directly govern persona behavior:

| Missing Reference | Reason |
|---|---|
| ADR-001 Persona Safety & Ethical Boundary | ADR-003 is the implementation mechanism for ADR-001's safety boundary audit requirement |
| ADR-002 User Autonomy & Safe Word | Rollback must not bypass safe word protections |
| ADR-008 Memory Encryption & Key Management | Rollback must handle encrypted persona data (intimate key per ADR-008) |
| ADR-012 Sub-Agent Orchestration Governance | If drift validation uses sub-agents, file-based output rules apply |
| ADR-024 Data Governance & Classification | Drift log data class must be defined per ADR-024 |

**Reviewer Note**: Add ADR-001, ADR-002, ADR-008, ADR-012, ADR-024 to Related Documents.

### 1.3 Minor Note — ADR-001 Review Item Not Closed

ADR-001 review record states: *"Note to add explicit review cadence and runtime prompt binding mechanism in a future revision."* ADR-003 partially addresses review cadence but does not mention runtime prompt binding. This is a known open item but not blocking for ADR-003 itself.

---

## 2. ADR-009: Memory Recall & Semantic Search Strategy

### 2.1 Special Attention — text-embedding-3-small / OpenAI Route Consistency with 9Router

**Severity**: HIGH
**Status**: Blocking

**Finding**: The embedding model route is ambiguous across documents:

- **ADR-009**: States "embedding model routed via 9Router-compatible embedding endpoint" but does not name the model.
- **Guinevere_APIIntegration_v2.0.md** section 2.3 (Model Cost Strategy) lists: 	ext-embedding-3-small at $0.02/M tokens — this is an OpenAI model name.
- **Guinevere_APIIntegration_v2.0.md** section 2.1 (9Router Configuration) shows the 9Router config with openrouter as the backend provider, routing to openai/gpt-5.5.
- **ADR-005 (Accepted)**: States *"All LLM routing goes through 9Router; OpenRouter is not a fallback path"* — this refers to OpenRouter as a fallback, not as a backend provider. Using OpenRouter as the backend for 9Router is acceptable per ADR-005.

**The ambiguity**: Is 	ext-embedding-3-small routed through 9Router (via OpenRouter backend) or called directly to OpenAI API? ADR-009 must specify:
1. The exact embedding model name
2. Whether it routes through 9Router or is called directly
3. If direct, how this aligns with ADR-005's "all LLM routing through 9Router" principle

**Reviewer Note**: ADR-009 should explicitly state: "Embedding generation routes through 9Router via the same OpenRouter backend used for GPT-5.5 and DeepSeek V4 Flash, consistent with ADR-005. Model: text-embedding-3-small via 9Router/OpenRouter backend. No direct OpenAI API calls."

### 2.2 Missing Cross-References

**Severity**: MEDIUM
**Status**: Blocking for acceptance

| Missing Reference | Reason |
|---|---|
| ADR-004 Primary LLM Model Selection | Recall depends on 9Router routing; GPT-5.5 context window assumptions |
| ADR-005 LLM Router & Failover Strategy | Embedding route must follow 9Router-only policy |
| ADR-006 Sub-Agent LLM Model Strategy | Sub-agents performing recall use DeepSeek V4 Flash |
| ADR-007 Memory Storage Backend | pgvector and TimescaleDB are ADR-007 decisions |
| ADR-008 Memory Encryption & Key Management | Encrypted fields (intimate/sensitive) must not be recalled without key access |
| ADR-024 Data Governance & Classification | Recall must respect data class boundaries (intimate data recall restrictions) |

**Reviewer Note**: Add ADR-004, ADR-005, ADR-006, ADR-007, ADR-008, ADR-024 to Related Documents.

### 2.3 Consistency with MemorySchema v2.0

ADR-009's layered recall strategy is consistent with the existing schema:
- memory.episodes has embedding vector(1536) with IVFFlat index ✓
- memory.semantic_facts has embedding vector(1536) ✓
- FTS5 keyword search is already defined ✓
- TimescaleDB hypertable enables time-weighted queries ✓

No schema changes proposed by ADR-009 — this is good. ADR-009 should explicitly state it is a governance/configuration overlay, not a schema change.

---

## 3. ADR-016: CI/CD & Autonomous Deployment Strategy

### 3.1 Special Attention — No GitHub Actions CD

**Severity**: HIGH
**Status**: Blocking

**Finding**: ADR-016's title and description mention "CI/CD" but do not explicitly exclude GitHub Actions as the deployment mechanism.

**Canonical v2.0 decision** (Guinevere_TechnicalArchitecture_v2.0.md section 10.2):
> *"Guinevere deploy dirinya sendiri via cron — tidak ada GitHub Actions CD (menghindari biaya per-menit)."*

**ADR-016 text**: *"Adopt CI/CD with explicit preflight verification, evidence capture, rollback path, and human approval requirements..."*

This is ambiguous. CI (testing, linting) uses GitHub Actions per v2.0 section 10.1. CD (deployment) must use self-deploy cron, NOT GitHub Actions. ADR-016 must make this distinction explicit to prevent future misinterpretation.

**Reviewer Note**: Add a dedicated section: "CD Mechanism: Self-Deploy Cron Only. GitHub Actions is used for CI only (test, lint, security scan). Deployment to production uses Guinevere self-deploy cron (git pull + uv sync + test + systemctl restart). No GitHub Actions workflow triggers production deployment."

### 3.2 Missing Cross-References

**Severity**: MEDIUM
**Status**: Blocking for acceptance

| Missing Reference | Reason |
|---|---|
| ADR-013 Guinevere MCP Native OpenCode Replacement | CI must test MCP native toolchain, not OpenCode |
| ADR-014 VPS & Container Architecture | Deployment targets the single-primary-VPS topology |
| ADR-015 Secrets Management | Self-deploy must handle SOPS decryption at startup |
| ADR-017 Monitoring Stack Selection | Post-deploy health checks must verify Prometheus/Grafana |
| ADR-012 Sub-Agent Orchestration Governance | Deployment evidence must follow file-based output rules |

**Reviewer Note**: Add ADR-013, ADR-014, ADR-015, ADR-017, ADR-012 to Related Documents.

### 3.3 Minor — Evidence Path Convention

ADR-016 mentions "evidence capture" but does not reference ADR-012's evidence directory conventions (evidence/<scope>/<artifact-name>.md). Should align with ADR-012.

---

## 4. ADR-019: Access Control & VPN Mesh Strategy

### 4.1 Special Attention — CRITICAL CONFLICT: Zero Public Ports

**Severity**: CRITICAL
**Status**: Blocking — requires explicit superseding or resolution

**Finding**: ADR-019 explicitly chooses "VPN-first admin access with **controlled public endpoints**" (Option 3). This directly contradicts two accepted canonical decisions:

1. **Guinevere_TechnicalArchitecture_v2.0.md** section 2.1: *"Public Ports: NONE — semua via Tailscale internal"*
2. **ADR-014 (Accepted)** VPS & Container Architecture: Tailscale-only access model
3. **ADR-018 (Accepted with notes)** Security Architecture: *"Network perimeter: Tailscale mesh — zero public ports: All external access blocked"*

**ADR-019's rationale**: "Public integrations still need secure ingress." But the v2.0 architecture already handles this through:
- Discord (external service, no VPS port exposure)
- GitHub (external service, no VPS port exposure)
- 9Router (local VPS service, accessed internally)
- Caddy on Tailscale-internal addresses (not public)

**Resolution options**:
1. ADR-019 supersedes the zero-public-ports decision — but this requires explicit "supersedes" declaration and weakens ADR-018's defense-in-depth.
2. ADR-019 aligns with zero public ports — public integrations use existing external service channels (Discord webhooks, GitHub webhooks via Tailscale-routed Caddy), not new public VPS endpoints.

**Reviewer Note**: This is the most critical conflict in batch-2. The senior architect reviewer must choose: (a) explicitly supersede ADR-014/ADR-018/v2.0 with documented risk acceptance, or (b) reframe ADR-019 to maintain zero public ports and use Tailscale+routed Caddy for all admin surfaces.

### 4.2 Missing Cross-References

**Severity**: MEDIUM
**Status**: Blocking for acceptance

| Missing Reference | Reason |
|---|---|
| ADR-014 VPS & Container Architecture | Network topology dependency — direct conflict |
| ADR-018 Security Architecture & Defense-in-Depth | ADR-019's public endpoints weaken ADR-018's network perimeter |
| ADR-015 Secrets Management | Service tokens for public endpoints need SOPS-managed secrets |
| ADR-008 Memory Encryption & Key Management | Access control must not bypass memory encryption boundaries |
| ADR-024 Data Governance & Classification | Public endpoints expand data exposure surface |

**Reviewer Note**: Add ADR-014, ADR-018, ADR-015, ADR-008, ADR-024 to Related Documents.

---

## 5. ADR-022: Communication Channel Strategy

### 5.1 Missing Cross-References

**Severity**: MEDIUM
**Status**: Blocking for acceptance

| Missing Reference | Reason |
|---|---|
| ADR-001 Persona Safety & Ethical Boundary | Channel responses trigger persona behavior; safety boundaries must apply cross-channel |
| ADR-002 User Autonomy & Safe Word | Safe word must work identically across all channels |
| ADR-010 Surveillance Data Retention | Communication logs may contain surveillance-derived content |
| ADR-024 Data Governance & Classification | Each channel's data must be classified per ADR-024 |
| ADR-018 Security Architecture | Channel auth must align with defense-in-depth |
| ADR-021 Wearable Integration Post-MVP | Gotify/FCM is notification, not wearable — should be explicitly distinguished |

**Reviewer Note**: Add ADR-001, ADR-002, ADR-010, ADR-024, ADR-018, ADR-021 to Related Documents.

### 5.2 Minor — Disclosure Boundary Ambiguity

ADR-022 states: "Each channel must define purpose, authentication, logging, consent/disclosure, rate limits, and failure behavior before production use." This is good policy but does not reference ADR-001's explicit safety boundaries for what MUST NEVER be disclosed via any channel (intimate data, surveillance raw data, etc.).

---

## 6. ADR-023: Financial Data Integration Strategy

### 6.1 Special Attention — PRD v2.0 "Scraping" Terminology Conflict

**Severity**: MEDIUM
**Status**: Blocking for consistency

**Finding**: ADR-023 explicitly rejects "autonomous scraping/parsing without schema" (Option 2) and chooses "Governed financial integration with provenance." This is correct and consistent with the spirit of the architecture.

However, **Guinevere_PRD_v2.0.md** section 7.1 (Financial Data Collection) uses different terminology:
- "GoPay: API / app scraping"
- "OVO: API / app scraping"  
- "Dana: API / app scraping"
- "Rekening bank: Mutasi bank scraping / Tasker"

The word "scraping" appears 4 times in the PRD for financial data collection. Meanwhile, **Guinevere_APIIntegration_v2.0.md** section 6.1 correctly describes this as "Tasker notification capture" — NOT scraping.

**ADR-009's no-scraping stance** is architecturally correct (notification capture via Tasker is reliable and real-time, as the API doc states). But the PRD's "app scraping" language creates a cross-document inconsistency that could mislead future implementers.

**Reviewer Note**: PRD v2.0 section 7.1 should be updated to replace "app scraping" with "Tasker AutoNotification capture" to align with the API Integration doc and ADR-023's no-scraping decision. This is a v2.0 doc update, not an ADR change.

### 6.2 Missing Cross-References

**Severity**: MEDIUM
**Status**: Blocking for acceptance

| Missing Reference | Reason |
|---|---|
| ADR-007 Memory Storage Backend | Financial data stored in PostgreSQL inancial.* schema |
| ADR-008 Memory Encryption & Key Management | Financial data is "sensitive" per ADR-008; encryption applies |
| ADR-015 Secrets Management | Financial API credentials (if any) need SOPS management |
| ADR-024 Data Governance & Classification | Financial data class must be explicitly mapped |
| ADR-010 Surveillance Data Retention | Financial retention policy differs from surveillance "selamanya" |
| ADR-018 Security Architecture | Financial data access controls must align with defense-in-depth |

**Reviewer Note**: Add ADR-007, ADR-008, ADR-015, ADR-024, ADR-010, ADR-018 to Related Documents.

### 6.3 Minor — ADR-021 Interaction

ADR-023 mentions "wearable data" in passing (health data processor). Should explicitly note that wearable financial data is post-MVP per ADR-021.

---

## 7. Cross-Cutting Issues

### 7.1 Status Field Mismatch — Body vs. Index

**Severity**: MEDIUM
**Affected ADRs**: ADR-001, ADR-002, ADR-008, ADR-012, ADR-018, ADR-024, ADR-025

All 7 ADRs have frontmatter status: "Accepted with notes" but the body ## Status section still reads "Proposed." The Guinevere_ADR_Index_v1.0.md correctly reflects "Accepted with notes" for these ADRs.

**Impact**: If anyone reads the ADR body without checking the index, they will incorrectly believe these ADRs are still Proposed.

**Reviewer Note**: This is a pre-existing issue across the entire ADR set, not batch-2 specific. Recommend a global fix: update the ## Status body section to match the frontmatter for all 19 accepted/accepted-with-notes ADRs.

### 7.2 Missing Cross-References Across All Batch-2 ADRs

**Severity**: MEDIUM
**Status**: Pattern issue

None of the 6 batch-2 Proposed ADRs cite any other ADR in their Related Documents section. They only cite v2.0 source docs. This means:

- ADR-003 (persona drift) doesn't cite ADR-001, ADR-002, ADR-008
- ADR-009 (semantic search) doesn't cite ADR-004, ADR-005, ADR-007, ADR-008
- ADR-016 (CI/CD) doesn't cite ADR-013, ADR-014, ADR-015, ADR-017
- ADR-019 (VPN/access) doesn't cite ADR-014, ADR-018
- ADR-022 (communication) doesn't cite ADR-001, ADR-002, ADR-010
- ADR-023 (financial) doesn't cite ADR-007, ADR-008, ADR-015, ADR-024

**Reviewer Note**: Each batch-2 ADR must add at minimum the directly dependent accepted ADRs to its Related Documents table. The current Related Documents sections only reference v2.0 source docs, which is insufficient for an ADR that depends on prior accepted decisions.

### 7.3 ADR Index Update Requirements

If any batch-2 ADR is accepted, the following index updates are needed:

1. **ADR-003**: Index already shows "Proposed" — no change if stays Proposed; update to "Accepted" if approved.
2. **ADR-009**: Index already shows "Proposed" — same.
3. **ADR-016**: Index already shows "Proposed" — same.
4. **ADR-019**: If accepted with the current "controlled public endpoints" language, the index's canonical decision map must be updated to note this as a partial superseding of ADR-014's zero-public-ports decision. If reframed to zero public ports, no canonical map change needed.
5. **ADR-022**: Index already shows "Proposed" — same.
6. **ADR-023**: Index already shows "Proposed" — same.

No ADR numbers need renumbering. No superseding relationships are declared in batch-2 ADRs (all say supersedes: "N/A").

---

## 8. Special Attention Items — Summary for Reviewer

| # | ADR | Issue | Severity | Required Action |
|---|---|---|---|---|
| 1 | ADR-003 | Rollback mechanism underspecified; conflicts with ADR-001 autonomy and ADR-002 safe word | HIGH | Define rollback semantics and safe word interaction |
| 2 | ADR-009 | text-embedding-3-small route ambiguous — direct OpenAI vs. 9Router | HIGH | Explicitly state embedding model routes through 9Router |
| 3 | ADR-016 | CI/CD title ambiguous — GitHub Actions CD not explicitly excluded | HIGH | Explicitly exclude GitHub Actions CD; mandate self-deploy cron |
| 4 | ADR-019 | "Controlled public endpoints" directly contradicts zero-public-ports in ADR-014/ADR-018/v2.0 | CRITICAL | Either supersede zero-public-ports explicitly or reframe to zero public ports |
| 5 | ADR-022 | No cross-channel safe word / persona safety linkage | MEDIUM | Add ADR-001 and ADR-002 to Related Documents |
| 6 | ADR-023 | PRD v2.0 uses "scraping" terminology; ADR-023 rejects scraping | MEDIUM | Update PRD v2.0 section 7.1 to use "notification capture" language |

---

## 9. Recommended Reviewer Checklist

For each batch-2 ADR, the senior architect reviewer should verify:

- [ ] ADR-003: Rollback mechanism is operationally defined; safe word interaction is explicit; ADR-001/ADR-002/ADR-008 cross-references added.
- [ ] ADR-009: Embedding model and route (9Router vs. direct) is unambiguous; ADR-004/005/006/007/008/024 cross-references added.
- [ ] ADR-016: CI vs. CD distinction is explicit; GitHub Actions CD is explicitly excluded; self-deploy cron mechanism is detailed; ADR-013/014/015/017/012 cross-references added.
- [ ] ADR-019: Zero-public-ports conflict is resolved — either with explicit superseding of ADR-014/ADR-018 or reframed to maintain zero public ports; ADR-014/018/015/008/024 cross-references added.
- [ ] ADR-022: Cross-channel persona safety and safe word behavior is defined; ADR-001/002/010/024/018/021 cross-references added.
- [ ] ADR-023: No-scraping stance is consistent with PRD v2.0 terminology; PRD v2.0 section 7.1 updated if needed; ADR-007/008/015/024/010/018 cross-references added.
- [ ] All 6 ADRs: Body ## Status section updated to match frontmatter (if this global fix is done alongside batch-2 review).
- [ ] All 6 ADRs: At minimum, directly dependent accepted ADRs are added to Related Documents tables.

---

## 10. Files Analyzed

### Batch-2 Proposed ADRs
- C:\Users\faizz\guinevere\adr\ADR-003-persona-drift-control-validation.md
- C:\Users\faizz\guinevere\adr\ADR-009-memory-recall-semantic-search-strategy.md
- C:\Users\faizz\guinevere\adr\ADR-016-cicd-autonomous-deployment-strategy.md
- C:\Users\faizz\guinevere\adr\ADR-019-access-control-vpn-mesh-strategy.md
- C:\Users\faizz\guinevere\adr\ADR-022-communication-channel-strategy.md
- C:\Users\faizz\guinevere\adr\ADR-023-financial-data-integration-strategy.md

### Accepted/Accepted-with-Notes ADRs Reviewed
- C:\Users\faizz\guinevere\adr\ADR-001-persona-safety-ethical-boundary.md
- C:\Users\faizz\guinevere\adr\ADR-002-user-autonomy-safe-word-enforcement.md
- C:\Users\faizz\guinevere\adr\ADR-004-primary-llm-model-selection.md
- C:\Users\faizz\guinevere\adr\ADR-005-llm-router-failover-strategy.md
- C:\Users\faizz\guinevere\adr\ADR-006-sub-agent-llm-model-strategy.md
- C:\Users\faizz\guinevere\adr\ADR-007-memory-storage-backend-selection.md
- C:\Users\faizz\guinevere\adr\ADR-008-memory-encryption-key-management.md
- C:\Users\faizz\guinevere\adr\ADR-010-surveillance-data-retention-policy.md
- C:\Users\faizz\guinevere\adr\ADR-011-sdlc-loop-phase-specification.md
- C:\Users\faizz\guinevere\adr\ADR-012-sub-agent-orchestration-governance.md
- C:\Users\faizz\guinevere\adr\ADR-013-guinevere-mcp-native-opencode-replacement.md
- C:\Users\faizz\guinevere\adr\ADR-014-vps-container-architecture.md
- C:\Users\faizz\guinevere\adr\ADR-015-secrets-management-strategy.md
- C:\Users\faizz\guinevere\adr\ADR-017-monitoring-stack-selection.md
- C:\Users\faizz\guinevere\adr\ADR-018-security-architecture-defense-in-depth.md
- C:\Users\faizz\guinevere\adr\ADR-020-browser-automation-strategy.md
- C:\Users\faizz\guinevere\adr\ADR-021-wearable-integration-post-mvp.md
- C:\Users\faizz\guinevere\adr\ADR-024-data-governance-classification-policy.md
- C:\Users\faizz\guinevere\adr\ADR-025-backup-disaster-recovery-strategy.md

### v2.0 Source Documents
- C:\Users\faizz\guinevere\Guinevere_TechnicalArchitecture_v2.0.md
- C:\Users\faizz\guinevere\Guinevere_APIIntegration_v2.0.md
- C:\Users\faizz\guinevere\Guinevere_Persona_Document_v2.0.md
- C:\Users\faizz\guinevere\Guinevere_MemorySchema_v2.0.md
- C:\Users\faizz\guinevere\Guinevere_PRD_v2.0.md
- C:\Users\faizz\guinevere\Guinevere_ADR_Index_v1.0.md

---

*Report generated by Guinevere sub-agent consistency checker. Read-only analysis — no files modified.*
