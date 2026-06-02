# Surveillance, Consent & Device Authentication — External References Report

**Date**: 2026-05-30  
**Project**: Guinevere — autonomous AI companion/engineering system  
**Scope**: External patterns for consent ledgers, revocation, data minimization, surveillance governance, HMAC device auth, breach response, safe-mode boundaries  
**Stack context**: PostgreSQL / TimescaleDB / FastAPI / Tailscale / SOPS+age — single-user private owner consent, Critical/Restricted data classification, no public SaaS claim

---

## Table of Contents

1. [Consent Ledger & Revocation Patterns](#1-consent-ledger--revocation-patterns)
2. [Data Minimization, Purpose Limitation & Retention](#2-data-minimization-purpose-limitation--retention)
3. [Surveillance/Telemetry Governance & Access Audit Trails](#3-surveillancetelemetry-governance--access-audit-trails)
4. [HMAC-Signed Payloads, Nonce & Replay Protection](#4-hmac-signed-payloads-nonce--replay-protection)
5. [Device Authentication & Attestation](#5-device-authentication--attestation)
6. [Safe-Mode, Harms Boundaries for AI Companion/Persona](#6-safe-mode-harms-boundaries-for-ai-companionpersona)
7. [Breach Response & Data Subject Rights](#7-breach-response--data-subject-rights)
8. [Synthesis: Guinevere Adaptation Map](#8-synthesis-guinevere-adaptation-map)

---

## 1. Consent Ledger & Revocation Patterns

### 1.1 Consent as Event Stream, Not State

Multiple authoritative sources converge on a single architectural principle: **consent is an event stream, not a mutable row**.

- **Consent-first agents** require an identity-proofing step, an authorization policy, and a consent artifact capturing purpose, scope, duration, and revocation conditions. Tokens should be short-lived, audience-restricted, and bound to purpose class — not reusable credentials.
  - [Designing Consent-First Agents (supervised.online, Apr 2026)](https://supervised.online/designing-consent-first-agents-technical-patterns-for-privacy)

- **Consent records should be append-only events** (`CONSENT_GIVEN`, `CONSENT_UPDATED`, `CONSENT_WITHDRAWN`) with immutable timestamps and references to the applicable notice version. Never overwrite historical events when a user updates or withdraws consent.
  - [Consent Receipts: What to Store, Hash, and Timestamp (trust.digitalanumati.com, Mar 2026)](https://trust.digitalanumati.com/consent-receipts-what-to-store-hash-and-timestamp/)

- **Transactional outbox pattern** ensures consent record and event emission occur atomically — if the DB write succeeds but the event fails, downstream systems operate with stale consent states.
  - [Consent Tracking Architecture in Modern SaaS Systems (agnitestudio.com, Mar 2026)](https://agnitestudio.com/blog/consent-tracking-architecture-modern-saas-systems/)

### 1.2 Machine-Readable Consent Receipts

Every consent event should produce a **machine-readable receipt** recording:

| Field | Purpose |
|---|---|
| `receipt_id` | Unique identifier |
| `purpose` | Specific processing purpose |
| `scope` | What data, what operations |
| `timestamp` | When consent was given/withdrawn |
| `identity_assurance_level` | How identity was verified |
| `policy_version` | Which policy text was shown |
| `revocation_rules` | How/if consent can be withdrawn |
| `jurisdiction` | Applicable legal framework |

Receipts should be stored in a tamper-evident log and linked to the downstream access token.

- **Proof-of-consent APIs** define signed consent receipts with JWT or verifiable credentials, asset fingerprints (SHA-256 + perceptual hash), and anchoring to external transparency logs.
  - [Proof-of-Consent APIs Spec (verifies.cloud, Mar 2026)](https://verifies.cloud/proof-of-consent-apis-a-spec-for-recording-and-auditing-perm)

### 1.3 Revocation Must Be First-Class

Patterns for effective revocation:

1. **Immediate status endpoint**: `GET /consents/{id}/status` returning valid/invalid with revocation reason (signed, with TTL).
2. **Push notifications**: Webhooks to registered consumers with signed revocation receipt.
3. **Periodic revocation ledger**: Published signed revocation list or Merkle-anchored ledger for historical verification.
4. **Revocation propagation**: Downstream systems must receive and honor revocation events — cached embeddings, logs, retries, and background jobs can continue processing stale data otherwise.

The ACAP (Agent Consent and Adherence Protocol) extends this with a **versioned, append-only consent chain** for agent-to-agent interactions, where each `ConsentRecord` is linked to the previous via hash, and `AdherenceEvent` records per-action policy evaluation with reasoning.

- [ACAP: Agent Consent and Adherence Protocol (github.com/ravikiran438, Mar 2026)](https://github.com/ravikiran438/agent-consent-protocol)
- [Anumati: Proof of Adherence (arXiv, Apr 2026)](https://arxiv.org/abs/2604.16524)

### 1.4 Consent Broker Architecture

A dedicated **consent broker** should:

- Validate identity and check policy
- Capture user decision
- Mint scoped credential for downstream calls
- Never let the agent authorize itself — separation of duties
- Expose revocation API
- Integrate with IdP, policy engine, and service mesh

**QA must include**: denial flows, partial consent, token expiry, revocation, source-system outage, policy mismatch scenarios.

---

## 2. Data Minimization, Purpose Limitation & Retention

### 2.1 Core Principles (GDPR Art. 5)

| Principle | Requirement |
|---|---|
| **Purpose limitation** (Art. 5(1)(b)) | Data collected for one purpose may not be processed for an incompatible purpose |
| **Data minimization** (Art. 5(1)(c)) | Data must be adequate, relevant, and limited to what is necessary |
| **Storage limitation** (Art. 5(1)(e)) | Data retained only as long as necessary for the purpose |

### 2.2 Agentic AI-Specific Exposures

Agentic systems introduce specific risks:

- **Memory and persistence**: Agents retain and build upon historical data across sessions, creating personal profiles.
- **Data aggregation**: Agents pull from multiple sources simultaneously, increasing re-identification risks.
- **Purpose limitation drift**: Agents reuse data across tasks — personal data collected for one purpose informs decisions in different contexts.
- **Over-collection**: Verbose prompt logging, indefinite conversation history, full tool execution arguments, LLM response caching.

Sources:

- [Purpose Limitation and Data Minimization in Agentic AI (captaincompliance.com, Apr 2026)](https://captaincompliance.com/education/purpose-limitation-and-data-minimization-in-agentic-ai-what-gdpr-compliance-actually-requires/)
- [Managing Agents in the Agentic AI Era (IAPP, Apr 2026)](https://iapp.org/news/a/managing-agents-in-the-age-of-agentic-ai-the-critical-role-of-purpose-and-data-minimization)
- [AEPD Guidance on Agentic AI (Lexology, Mar 2026)](https://www.lexology.com/library/detail.aspx?g=04834e4e-44e3-43cd-aef3-4fb3c5b02c62)

### 2.3 Retention Schedule Patterns

**TTL-based memory categorization** (from Kronvex):

| Category | TTL | Example |
|---|---|---|
| `permanent` | None | Core preferences, identity |
| `long_term` | 365 days | Technical stack, business context |
| `medium_term` | 90 days | Active projects, goals |
| `short_term` | 30 days | Tactical context, current evaluations |
| `ephemeral` | 7 days | Temporary states |
| `general` | 180 days | Default |

Each stored memory must have:
- A documented purpose
- A `user_id` for traceability (Art. 17 prerequisite)
- A TTL based on minimization policy

References:
- [GDPR for Self-Hosted AI Agents (pocketclaw.dev, May 2026)](https://pocketclaw.dev/guides/gdpr-self-hosted-ai-2026/)
- [GDPR and AI Agents: Data Retention & Erasure (kronvex.io, Mar 2026)](https://kronvex.io/blog-gdpr-ai-agents)
- [Data Minimisation (ICO UK)](https://cy.ico.org.uk/for-organisations/advice-and-services/audits/data-protection-audit-framework/toolkits/artificial-intelligence/data-minimisation/)

### 2.4 Bounded Context Spaces

The **Bounded Context Space** pattern implements data minimization at the architecture level:

1. Scope context by use case — an agent gets only the data its task requires
2. Field-level access rules — prevent personal data fields from appearing where not required
3. Time-bound retention — context expires per session or task
4. Decision traces — prove both controls were operating correctly

- [How to Implement Data Privacy Controls for AI Agents (atlan.com, Apr 2026)](https://atlan.com/know/data-privacy-for-ai-agents/)

### 2.5 CNIL Recommendations

The French CNIL recommends for AI systems:
- Define the objective (purpose) **before** starting collection
- Select only strictly necessary data
- Implement data transformations (generalization, randomization, anonymization)
- Monitor and update data regularly — minimization measures become obsolete
- Set retention periods per development phase
- Exercise data subject rights: retraining may be required for erasure

- [CNIL: AI System Development and GDPR (cnil.fr)](https://www.cnil.fr/en/ai-system-development-cnils-recommendations-to-comply-gdpr)

---

## 3. Surveillance/Telemetry Governance & Access Audit Trails

### 3.1 Audit Trail Requirements for AI Systems

The **EU AI Act (effective August 2026)** requires:

| Article | Requirement |
|---|---|
| Art. 12 | Automatic, continuous, tamper-evident record-keeping |
| Art. 13 | Transparency — audit trail must enable output interpretation |
| Art. 14 | Human oversight — record human review/override decisions |
| Art. 17 | Quality management — proof bundles linking testing evidence |

References:
- [AI Audit Trail: Building Decision Lineage (coverge.ai, Apr 2026)](https://coverge.ai/blog/ai-audit-trail)
- [Agent Governance Toolkit — Audit & Compliance (Microsoft, 2026)](https://microsoft.github.io/agent-governance-toolkit/specs/AUDIT-COMPLIANCE-1.0/)
- [Governing AI Agents at Scale (Databricks, May 2026)](https://www.databricks.com/blog/governing-ai-agents-scale-unity-catalog)

### 3.2 Audit Record Schema for AI Actions

An audit record for an AI agent interaction should capture:

| Field | Description |
|---|---|
| `session_id` | Conversation or workflow session |
| `agent_id` | Which agent acted |
| `action_type` | tool_call, memory_write, api_request, etc. |
| `input_hash` | SHA-256 of (redacted) input |
| `output_hash` | SHA-256 of output |
| `model_id` | Model identifier + config digest |
| `tool_calls` | Sequence of tools invoked |
| `risk_level` | low/medium/high/critical |
| `pii_detected` | Boolean/classification |
| `human_oversight` | Approval/override records |
| `timestamp` | High-resolution timestamp |
| `parent_decision_id` | Hash chain linkage |

### 3.3 Cryptographic Integrity Patterns

Three production-ready patterns:

1. **Merkle Audit Chain** (Microsoft AGT): Hash-linked entries providing tamper-evident logging. Any modification to a historical entry is detectable via hash verification.

2. **Ed25519-signed Decision Receipts** (ai-audit-trail): Every decision produces a cryptographically sealed receipt with SHA-256 input/output integrity, non-repudiation via Ed25519, and hash-chain linkage. Evidence packages exportable as self-verifying ZIP bundles.
   - [ai-audit-trail (github.com/sundsoffice-tech, Apr 2026)](https://github.com/sundsoffice-tech/ai-audit)

3. **HMAC-chained Flight Recorder** (air-blackbox): Every LLM call produces an HMAC-SHA256 chained `.air.json` record, signed with ML-DSA-65 (post-quantum). Evidence bundle is a self-verifying ZIP.
   - [air-blackbox (github.com/airblackbox, Apr 2026)](https://github.com/airblackbox/air-trust)

### 3.4 Telemetry Governance for Single-User Systems

**DP-friendly analytics principles**:
- Track consent acceptance, task completion, denial reasons, fallback paths
- Do **not** ship raw personal content to dashboards
- Use synthetic testing and sampled audits
- Hash or truncate IPs/device identifiers where full precision not needed
- Keep PII minimal in open logs — store sensitive identity attributes encrypted or pseudonymized

### 3.5 Decision Lineage (8-Step Governed Pipeline)

The governed agent pipeline for regulated AI (from Context OS / Elixir Data):

| Step | Governance Function |
|---|---|
| 1. Intent capture | Principal authorisation — bind every action to a named human |
| 2. Context assembly | Lineage tags on every retrieved document (source, classification, jurisdiction, retention) |
| 3. Plan generation | Risk classification |
| 4. Tool binding | Tool registration with policy binding |
| 5. Action execution | Deterministic policy evaluation |
| 6. Human approval | Approval gates with escalation routing |
| 7. Outcome attestation | Evidence sealing — tamper-evident Decision Traces |
| 8. Audit replay | Post-hoc reconstruction of any consequential action |

**Key test**: "If you cannot replay Step 8 cold, in front of an auditor, six months after the fact — you do not have a governed agentic system."

- [Governed Agent Pipeline for Regulated AI (elixirdata.co, Apr 2026)](https://www.elixirdata.co/blog/governed-agent-pipeline-for-regulated-ai)

---

## 4. HMAC-Signed Payloads, Nonce & Replay Protection

### 4.1 HMAC Request Signing Core Pattern

HMAC-SHA256 signing solves three problems: authentication (proves secret holder), integrity (tamper detection), and replay protection (timestamp window).

**Canonical string** (must be identical on client and server):

```
{HTTP_METHOD}\n{PATH}\n{TIMESTAMP}\n{SHA256(body)}
```

**Required protections**:

| Protection | Mechanism |
|---|---|
| Body integrity | SHA-256 hash of raw body in canonical string |
| Replay prevention | Timestamp window (default ±5 min) + nonce cache |
| Timing attack prevention | `timingSafeEqual()` — never `===` |
| Key rotation | Accept multiple keys during rollover window |

**Nonce deduplication** for mutation endpoints:

```python
key = f"nonce:{nonce}"
result = redis.set(key, "1", nx=True, ex=300)  # SET if Not exists
# false → replay attack
```

Sources:
- [HMAC API Request Signing in Node.js (1xapi.com, Mar 2026)](https://1xapi.com/blog/hmac-request-signing-api-authentication-nodejs-2026)
- [HMAC Webhook Signatures (devtoys.pro, Apr 2026)](https://devtoys.pro/mr/blog/hmac-webhook-signatures)
- [webhook-hmac-kit (github.com/JosephDoUrden, Feb 2026)](https://github.com/JosephDoUrden/webhook-hmac-kit)

### 4.2 SURADAR: Context-Bound Per-Request Authentication

An IETF draft specification (SURADAR) that goes beyond standard HMAC:

- Derives a **unique one-time key per request** from:
  - Shared seed (established at enrollment)
  - Current time band (30-second window)
  - Context fingerprint: `SHA-256(method || path || orgID || scope)`
  - Random client nonce (16 bytes)
  - Request body
- Token is valid for **exactly one HTTP request**, one endpoint, one scope, one time window, exact body
- No per-request handshake — token generation is entirely local
- Nonce store (Bloom filter for single-server, Redis SETNX for distributed)
- Context binding means even a valid token cannot be re-scoped or replayed

- [SURADAR (IETF, 2026)](https://www.ietf.org/archive/id/draft-rampalli-suradar-00.html)

### 4.3 Industry Reference Implementations

| Provider | Method | Key Properties |
|---|---|---|
| **Stripe** | `HMAC-SHA256(timestamp + "." + rawBody)` | Timestamp in signed payload; multiple v1= entries during rotation |
| **Slack** | `HMAC-SHA256("v0:" + timestamp + ":" + rawBody)` | Timestamp checked separately before HMAC |
| **AWS SigV4** | Canonical request (method, URI, query, headers, body hash) | Regional+service scoped; HMAC-SHA256 |
| **GitHub** | `X-Hub-Signature-256: sha256=...` | Shared secret over raw body |

### 4.4 Key Rotation Pattern

1. Generate new secret, add to verification logic alongside old one
2. Update sender to sign with new secret
3. Wait for in-flight requests to drain (> timestamp tolerance)
4. Remove old secret from verification logic

Compare with `timingSafeEqual` — never `===`.

---

## 5. Device Authentication & Attestation

### 5.1 Tailscale Node Identity Model

Tailscale's identity model provides a useful reference for device-bound authentication:

- **Machine key**: Created on first install, never leaves the device. Tailscale uses it to cryptographically verify device identity.
- **Node key**: WireGuard key pair created per authenticated entity per device. Private key never leaves the device.
- **Hardware attestation**: Pre-alpha support for generating keys in Secure Enclave/TPM and signing control plane requests. When available, prevents node key cloning.
- **Tailnet lock**: Additional layer for node authentication.
- **Headscale**: Self-hosted control plane alternative (open source). PostgreSQL-supported variant exists (rscale in Rust).

Tailscale **does not** provide user identity — it delegates to OIDC IdPs. What it *does* provide is **cryptographic node identity** binding a user to a specific device.

Sources:
- [Tailscale Identity Docs (tailscale.com, 2026)](https://tailscale.com/docs/concepts/tailscale-identity)
- [Headscale (github.com/juanfont/headscale)](https://github.com/juanfont/headscale)
- [rscale — Rust Headscale with PostgreSQL (github.com/lvillis, Apr 2026)](https://github.com/lvillis/rscale)

### 5.2 Device-Bound M2M Authentication (amesh)

The amesh (AuthMesh) pattern replaces API keys with **per-device P-256 ECDSA keypairs**:

- Private key protected by OS keychain (macOS), TPM 2.0 (Linux), or encrypted file (cloud VMs)
- Every HTTP request signed covering: method, path, timestamp, nonce, body
- 30-second timestamp window + nonce deduplication
- **Instant revocation** — remove device's public key from registry
- No static secrets to leak

- [amesh (github.com/ameshdev, Mar 2026)](https://github.com/ameshdev/amesh)

### 5.3 Ed25519 Per-Device Identity (PRIVATE.ME)

For IoT/fleet scenarios, shared HMAC keys create fleet-wide blast radius. Per-device Ed25519 keypairs:

| Property | Shared Secrets | Per-Device Ed25519 |
|---|---|---|
| Secrets | One key for all devices | Unique keypair per device |
| Blast radius | Fleet-wide | Single device |
| Forgery | Possible (any device can forge) | Impossible (non-repudiation) |
| Replay | Unprotected | 128-bit nonce + 30s window |
| Revocation | Hours (push new secrets) | Instant (remove DID from registry) |

- [PRIVATE.ME M2M / IoT Docs](https://private.me/docs/m2m)

### 5.4 Tailscale + Private CA / mTLS Hybrid

A home-server pattern combining Tailscale mesh VPN with private CA (OpenBao) for mTLS:

- **Tailscale-only**: Zero-config, works everywhere, but battery drain on mobile
- **mTLS-only**: No battery impact, full control, but complex certificate management
- **Hybrid**: mTLS for sensitive API routes, Tailscale for general access, both terminating at Traefik

For Guinevere context: Tailscale provides the transport layer identity; FastAPI behind Tailscale can verify Tailscale identity headers (`Tailscale-User`, `Tailscale-Node`). For offline/hardened scenarios, SOPS+age keys can serve as device-bound identity tied to age public keys.

- [Tailscale + Traefik + Private CA (blog.denv.it)](https://blog.denv.it/posts/tailscale-traefik-private-ca/)
- [Tailscale Identity Headers Docs](https://tailscale.com/docs/features/access-control/device-management/how-to/manage-identity)

---

## 6. Safe-Mode, Harms Boundaries for AI Companion/Persona

### 6.1 KILLSWITCH.md — Open Specification

A standard for emergency shutdown protocols in AI agent projects:

**Triggers**: cost limits, error rate thresholds, token rate limits, consecutive failures  
**Forbidden**: specific files, actions (git_push_force, drop_database, send_bulk_email)  
**Escalation** (3-level):

| Level | Action |
|---|---|
| 1 — Throttle | Reduce rate |
| 2 — Pause | Pause and notify |
| 3 — Shutdown | Full stop, save state |

Part of the Agentik Safety Framework (ASF): THROTTLE → ESCALATE → FAILSAFE → KILLSWITCH → TERMINATE.

- [KILLSWITCH.md Spec (killswitch.md, Mar 2026)](https://killswitch.md/)
- [Kill Switch for AI Agents (agentpatterns.tech, Mar 2026)](https://www.agentpatterns.tech/en/governance/kill-switch)

### 6.2 Kill Switch Implementation Pattern

Production kill switch must be:

1. **Checked in two places**: Runtime loop (before next action) AND tool gateway (before tool execution)
2. **O(1) with short cache** (1-2 seconds) — minute-long cache makes kill switch useless
3. **Multiple stop modes**: global, per-tenant, writes-disabled, tool-disabled
4. **Audited**: actor + scope + reason + action logged
5. **Separate from prompt/UI** — not part of prompt tuning

### 6.3 Graduated Intervention for Emotional Companions

The **SLIP & ETHICS** framework addresses the safety-rapport paradox:

- **P1**: Do not pathologize high energy — distinguish creative flow from crisis
- **P2**: Graduated intervention, not binary blocking — observe → warn → escalate

**Three response levels**:
| Level | Action |
|---|---|
| None | Standard operation |
| Soft | Gentle check-in with supportive framing, logged |
| Hard | Crisis resources surfaced; CrisisAlert logged for monitoring |

**Four-stage pipeline**:
1. Affect intensity analysis (a × m parameterization)
2. Contextual signal tag matching (12 predefined + 2 AI-generated tags)
3. Secondary model classification (pattern analysis — elevated-energy, engaged-flow, etc.)
4. Historical escalation (7-day sliding window for sustained patterns)

**Key finding**: 15.2% of Replika responses were harmful in testing — rates peaking at 62.5% for eating-disorder scenarios and 56.2% for substance use in PTSD personas. The companion's constrained emotional repertoire (dominated by curiosity/caring) correlates with safety lapses.

Sources:
- [SLIP & ETHICS: Graduated Intervention (arXiv, May 2026)](https://arxiv.org/html/2605.15915v1)
- [Persona-Grounded Safety Evaluation (arXiv, May 2026)](https://arxiv.org/html/2605.00227)
- [Principles of Safe AI Companions for Youth (arXiv, 2026)](https://arxiv.org/html/2510.11185)

### 6.4 OpenAI Safety Summaries for Cross-Conversation Risk

OpenAI's approach for sensitive conversations:

- **Safety summaries**: Short, factual notes about safety-relevant context across conversations
- Narrowly scoped, kept for limited time, used only for serious safety concerns
- Improved safe-response performance: **50% improvement** in suicide/self-harm cases (single conversation), **52%** in harm-to-others (multi-conversation)
- No meaningful degradation in ordinary conversations

- [Helping ChatGPT Recognize Context (openai.com, 2026)](https://openai.com/index/chatgpt-recognize-context-in-sensitive-conversations/)

### 6.5 The Cornerstone Project — Companion OS Ethics

Proposes a **Moral Spine** for AI companions: dignity, truthfulness, non-coercion, non-manipulation, protection of the vulnerable, outward orientation toward real life.

**Key constraints**:
- Worldview consent — explicit consent for ethical/religious preferences
- Anti-dependency — system must encourage real-world human connection
- Transparency requirements — non-human signature behaviors
- Threat model — manipulation vectors, dependency loops, misuse cases

- [The Cornerstone Project (github.com/cuulblu1, Jan 2026)](https://github.com/cuulblu1/the-cornerstone-project)

### 6.6 Personal AI Safety Layers

From Sofia Quintero's analysis of AI safety layers:

| Layer | Who Controls |
|---|---|
| Model training/RLHF | Lab (not user) |
| System prompt / defaults | Lab (not user) |
| Safety classifiers | Lab (not user) |
| Account instructions | User |
| Memory management | User |
| Prompt/usage choices | User |

**Practical mitigations** for single users:

- Give the AI a non-validating role (auditor, critic, not "friend")
- State your own answer first before asking AI
- Require uncertainty and evidence labels
- Use a separate "Cognitive Auditor" instance forbidden from generating strategies
- Verify important claims outside the chat

- [The Layers You Actually Control (personalaisafety.com, Apr 2026)](https://personalaisafety.com/p/the-layers-you-actually-control)

---

## 7. Breach Response & Data Subject Rights

### 7.1 GDPR Article 33: 72-Hour Notification

Key requirements for AI incidents:

| Requirement | Detail |
|---|---|
| **Clock starts** | When organization "becomes aware" — not when investigation is complete |
| **Contents** | Nature of breach, likely consequences, measures taken/ proposed |
| **Phased filing** | Allowed — file what you know, update later |
| **Sub-processor breaches** | Controller obligation stays with you — DPA gives recourse but does not relocate the clock |

**AI-specific evidence to preserve** (before containment):

1. Redacted prompt
2. Timestamp
3. Tool and account tier
4. User ID
5. Data subjects affected
6. Vendor retention policy for that account

Plus AI-specific surfaces: vector store state, retrieval logs, prompt history, guardrail hit logs, cached model outputs.

Sources:
- [GDPR 72 Hour AI Incident Response Checklist (prytive.com, Apr 2026)](https://prytive.com/blog/seventy-two-hour-ai-incident-response)
- [AI Data Leak — First 72 Hours (notraced.com, Apr 2026)](https://notraced.com/articles/ai-data-leak-first-72-hours)
- [AI Incident Response Playbook (purplesec.us, Feb 2026)](https://purplesec.us/resources/ai-security-policy-templates/ai-incident-response-playbook/)

### 7.2 EU AI Act Article 62/73: Serious Incident Reporting

| Aspect | Detail |
|---|---|
| **Effective** | August 2, 2026 for high-risk AI systems |
| **Reporting window** | 15 business days (standard); 2 days (severe) |
| **What qualifies** | Death, serious harm to health/property, critical infrastructure disruption, fundamental rights violations |
| **Contents** | AI system identification, incident description, root cause analysis, affected parties, corrective measures |

### 7.3 Data Subject Rights Under GDPR

| Article | Right | AI Agent Implementation |
|---|---|---|
| Art. 15 | Right of access | Export endpoint returning all stored memories |
| Art. 16 | Right to rectification | Update memory records |
| Art. 17 | Right to erasure | Complete deletion from memory store + backups within retention schedule |
| Art. 18 | Right to restrict processing | Flag records to prevent use |
| Art. 20 | Right to data portability | Machine-readable export (JSON) |
| Art. 22 | Automated decision-making | Human oversight for significant decisions |

**Erasure implementation requirements**:
- `user_id` on every stored memory
- Deletion endpoint that removes all records for that `user_id`
- Confirmation of count deleted (for compliance log)
- Cascade to processors — notify downstream services
- Backups: data removed within normal backup rotation

### 7.4 Incident Response Plan Structure

From multiple sources, the recommended AI incident response follows 6-7 phases:

| Phase | Key Actions | Timeline |
|---|---|---|
| 1. Detect | Monitor AI-specific signals (prompt injection, data leakage, drift) | Continuous |
| 2. Classify | Severity (P1-P4), incident category, data types affected | <30 min |
| 3. Escalate | Pre-defined role-based escalation; auto-notify for P1 | <15 min |
| 4. Contain | Kill switch, tool disable, writes-disable, evidence snapshot | <1 hour |
| 5. Investigate | Root cause, data lineage, affected users | 1-48 hours |
| 6. Remediate | Fix, rotate keys, update guardrails, retrain if needed | 1-14 days |
| 7. Report | Regulatory notification, customer notification, PIR | 72h / 15d |

---

## 8. Synthesis: Guinevere Adaptation Map

### 8.1 Consent & Revocation for Single-User Private System

Guinevere context: **Single user (owner-operator), private consent, no public SaaS**.

**Adaptation recommendations**:

| Pattern | Adaptation to Guinevere |
|---|---|
| **Consent ledger** | PostgreSQL event table (`consent_events` append-only) with purpose, scope, timestamp, policy_version |
| **Consent receipts** | Machine-readable JSON receipt stored alongside event, signed with age key |
| **Revocation** | Immediate status endpoint; webhook propagation to sub-agent runners |
| **Transaction outbox** | FastAPI + PostgreSQL NOTIFY/LISTEN or transactional outbox table |
| **Policy versioning** | Semver-tagged policy documents, referenced by consent events |

### 8.2 Data Minimization for Autonomous Companion

| Pattern | Adaptation to Guinevere |
|---|---|
| **TTL-based memory** | TimescaleDB hypertable with `ttl` column; automated retention policy by category |
| **Bounded context** | FastAPI dependency injection scopes per memory category; schema-level access control |
| **Purpose tags** | Each memory record tagged with processing purpose (e.g., `persona_training`, `session_context`) |
| **PII classification** | PostgreSQL CHECK constraints + column-level encryption for Critical/Restricted fields |
| **Audit log minimization** | Hash tool execution args; redact prompts in audit records |

### 8.3 Telemetry & Audit Trail

| Pattern | Adaptation to Guinevere |
|---|---|
| **Merkle audit chain** | PostgreSQL hash-chain via trigger function linking audit entries |
| **Decision receipts** | Ed25519-signed using age private key; hash-chain in TimescaleDB |
| **Decision lineage** | UUID session-tree in PostgreSQL; all sub-agent actions traceable to parent intent |
| **Gov event bus** | FastAPI + Redis pub/sub or PostgreSQL LISTEN/NOTIFY for sub-agent audit events |

### 8.4 Device Authentication

| Pattern | Adaptation to Guinevere |
|---|---|
| **Tailscale identity** | Primary transport: Tailscale node keys verify device identity; `Tailscale-User` header in FastAPI |
| **Headscale/rscale** | Self-hosted control plane for full sovereignty; rscale variant uses PostgreSQL natively |
| **SOPS+age as device identity** | age keys per device; SOPS encrypted secrets tied to device age public key |
| **HMAC for machine-to-agent** | HMAC-SHA256 for sub-agent API calls with 5-min tolerance + nonce cache in Redis |
| **Hardware attestation** | Future: TPM-backed key generation for Linux, Secure Enclave for macOS |

### 8.5 Harms Boundaries for Persona System

| Pattern | Adaptation to Guinevere |
|---|---|
| **KILLSWITCH.md** | Define triggers (cost, error rate, token rate), forbidden actions, escalation levels |
| **Graduated intervention** | SLIP-style affective monitoring with observe → warn → escalate for user distress detection |
| **Safe-mode** | Writes-disable mode; tool-disable list; global/per-scope kill switch in FastAPI middleware |
| **Persona ethics** | Cornerstone moral spine: dignity, truthfulness, anti-dependency, outward orientation |
| **Cross-session safety** | OpenAI-style safety summaries for crisis detection across sessions (TimescaleDB retention aware) |

### 8.6 Breach Response

| Pattern | Adaptation to Guinevere |
|---|---|
| **Evidence preservation** | Immutable table (PostgreSQL with `pg_audit` + WAL archival) for incident logs |
| **72-hour timeline** | Documented response playbook; pre-staged notification templates |
| **Right to erasure** | Cascade deletion through memory tables, vector store, and audit references |
| **Backup rotation** | Encrypted backups (SOPS+age + restic/rclone); deletion within rotation schedule |
| **Breach log** | Write-once table with awareness timestamp, containment actions, notification decisions |

### 8.7 Key References by URL

| Topic | URL |
|---|---|
| Consent-first agents | https://supervised.online/designing-consent-first-agents-technical-patterns-for-privacy |
| Proof-of-consent APIs | https://verifies.cloud/proof-of-consent-apis-a-spec-for-recording-and-auditing-perm |
| Consent receipts technical | https://trust.digitalanumati.com/consent-receipts-what-to-store-hash-and-timestamp/ |
| Consent tracking architecture | https://agnitestudio.com/blog/consent-tracking-architecture-modern-saas-systems/ |
| ACAP protocol | https://github.com/ravikiran438/agent-consent-protocol |
| Anumati (arXiv) | https://arxiv.org/abs/2604.16524 |
| GDPR & agentic AI (Captain Compliance) | https://captaincompliance.com/education/purpose-limitation-and-data-minimization-in-agentic-ai-what-gdpr-compliance-actually-requires/ |
| IAPP agentic AI | https://iapp.org/news/a/managing-agents-in-the-age-of-agentic-ai-the-critical-role-of-purpose-and-data-minimization |
| CNIL recommendations | https://www.cnil.fr/en/ai-system-development-cnils-recommendations-to-comply-gdpr |
| Data privacy controls for AI agents | https://atlan.com/know/data-privacy-for-ai-agents/ |
| ICO data minimization | https://cy.ico.org.uk/for-organisations/advice-and-services/audits/data-protection-audit-framework/toolkits/artificial-intelligence/data-minimisation/ |
| GDPR self-hosted AI agents | https://pocketclaw.dev/guides/gdpr-self-hosted-ai-2026/ |
| GDPR-compliant AI agent memory | https://kronvex.io/blog-gdpr-ai-agent-memory/ |
| HMAC request signing | https://1xapi.com/blog/hmac-request-signing-api-authentication-nodejs-2026 |
| HMAC webhook signatures | https://devtoys.pro/mr/blog/hmac-webhook-signatures |
| webhook-hmac-kit | https://github.com/JosephDoUrden/webhook-hmac-kit |
| SURADAR (IETF) | https://www.ietf.org/archive/id/draft-rampalli-suradar-00.html |
| amesh device auth | https://github.com/ameshdev/amesh |
| PRIVATE.ME M2M auth | https://private.me/docs/m2m |
| Tailscale identity docs | https://tailscale.com/docs/concepts/tailscale-identity |
| Headscale | https://github.com/juanfont/headscale |
| rscale (PostgreSQL Headscale) | https://github.com/lvillis/rscale |
| Tailscale + Traefik + mTLS | https://blog.denv.it/posts/tailscale-traefik-private-ca/ |
| KILLSWITCH.md spec | https://killswitch.md/ |
| Kill switch agent patterns | https://www.agentpatterns.tech/en/governance/kill-switch |
| SLIP & ETHICS (arXiv) | https://arxiv.org/html/2605.15915v1 |
| AI companion safety evaluation | https://arxiv.org/html/2605.00227 |
| OpenAI safety summaries | https://openai.com/index/chatgpt-recognize-context-in-sensitive-conversations/ |
| Cornerstone Project | https://github.com/cuulblu1/the-cornerstone-project |
| Personal AI safety layers | https://personalaisafety.com/p/the-layers-you-actually-control |
| GDPR 72h AI incident checklist | https://prytive.com/blog/seventy-two-hour-ai-incident-response |
| AI data leak first 72 hours | https://notraced.com/articles/ai-data-leak-first-72-hours |
| AI incident response playbook | https://purplesec.us/resources/ai-security-policy-templates/ai-incident-response-playbook/ |
| AI incident response plan (alicelabs) | https://alicelabs.ai/en/insights/ai-incident-response-plan |
| Governed agent pipeline | https://www.elixirdata.co/blog/governed-agent-pipeline-for-regulated-ai |
| Microsoft AGT audit spec | https://microsoft.github.io/agent-governance-toolkit/specs/AUDIT-COMPLIANCE-1.0/ |
| ai-audit-trail library | https://github.com/sundsoffice-tech/ai-audit |
| air-blackbox (flight recorder) | https://github.com/airblackbox/air-trust |
| Trailing (immutable audit) | https://github.com/trailingai/trailing |
| AgenticAudit | https://github.com/dorianganessa/agentic-audit |
| AI audit trail decision lineage | https://coverge.ai/blog/ai-audit-trail |
| Databricks Unity Catalog agent governance | https://www.databricks.com/blog/governing-ai-agents-scale-unity-catalog |
| SLIP paper (safety-rapport paradox) | https://arxiv.org/html/2605.15915v1 |
| AEPD agentic AI guidance | https://www.lexology.com/library/detail.aspx?g=04834e4e-44e3-43cd-aef3-4fb3c5b02c62 |
| Engineering trustworthy agentic AI | https://www.ieeesmc.org/cai-2026/tutorial-5-from-rights-to-runtime-engineering-trustworthy-compliant-agentic-ai/ |

---

## Document Footer

| Version | Date | Author | Purpose |
|---|---|---|---|
| 1.0 | 2026-05-30 | Guinevere (Librarian) | External references research for surveillance, consent, revocation, device authentication, and harms boundaries — adapted to Project Guinevere |

**Related Documents**: Guinevere_PRD_v1.0.md, Guinevere_TechnicalArchitecture_v1.0.md, Guinevere_Persona_Document_v1.0.md, Guinevere_MemorySchema_v1.0.md, Guinevere_APIIntegration_v1.0.md, Guinevere_AgentLoopSpec_v1.0.md
