# External & Comparative Best-Practice Research: Do-Not-Recall Memory Exclusion & Safe-Mode Memory Filtering

> **Report scope**: P3-013 (do_not_recall=True exclusion) + P3-014 (HardStopHandler.is_safe integration)  
> **Date**: 2026-06-02  
> **Classification**: Internal — Research Artifact  
> **Status**: Complete

---

## 1. Executive Summary

This report surveys external and comparative best practices for two related memory-security concerns:

1. **Hard exclusion flags** — "do not recall" / DNR semantics that guarantee a memory entry is excluded from ALL recall paths.
2. **Safe-mode filtering** — runtime filtering/redaction that enforces classification tiers when safety mode is active.

Key external references analyzed: Letta/MemGPT, TealTiger TealMemory, OWASP Agent Memory Guard, CoWork OS observation states, MemPrivacy (MemTensor), MemGate (carlnoah6), `memp` recallability-readability separation, Memfence, SafeAgent, SafeGPT, LangChain PIIMiddleware, claude-recall, SAIHM Protocol, FSFM selective forgetting, MemArchitect governance layer, and Agent Memory Protocol (AMP).

### Critical Finding: No existing system implements all three of our requirements simultaneously

Most systems address **one or two** dimensions — either recall suppression OR safe-mode filtering OR injection resistance — but the combination of **hard exclusion + safety-mode tiered filtering + prompt-injection resistance** is novel. This means Guinevere's P3-013/P3-014 implementation must synthesize patterns from multiple sources.

---

## 2. Hard Exclusion Flags (Do-Not-Recall)

### 2.1 Pattern: Architectural Recall-Readability Separation

**Source**: `memp` — memovai/memp (GitHub, MIT License)

memp introduces the core design principle: **recallability must not imply readability**. A memory entry's recall signal (embedding, search metadata) is stored separately from its raw content. Recall returns a `mem_id`; the raw memory is only revealed if policy explicitly allows it.

**Evidence** ([memp README](https://github.com/memovai/memp)):
```
- Recall uses **derived signals**
- Raw memory remains **private by default**
- Exposure is **explicit and policy-controlled**
```

This pattern directly maps to DNR: a DNR-flagged entry could have its recall signal removed entirely from vector indices, making structural bypass impossible.

### 2.2 Pattern: Observation Privacy States (Redacted + Suppressed)

**Source**: CoWork OS — Structured Memory Observations

CoWork OS defines four memory observation states, two of which enforce recall exclusion:

| State | Behavior |
|---|---|
| `redacted` | Content replaced; row excluded from prompt recall |
| `suppressed` | Hidden from prompt recall AND default search results |

**Evidence** ([CoWork OS docs](https://coworkosapp.com/docs/memory-observations/)):
> Prompt recall checks both old prompt-recall ignore markers and observation privacy state. That means suppressed and redacted observations are excluded from both search-based recall and recent-memory prompt recall.

**Key design check for P3-013**: Both search-based recall AND prompt recall paths must independently enforce DNR. A single flag check at the retrieval boundary is insufficient — every recall code path must gate on DNR status.

### 2.3 Pattern: Cryptographic Erasure with Blacklist

**Source**: SAIHM Protocol (IETF draft)

The Sovereign AI Horizontal Memory protocol uses cryptographic-grade exclusion:

- DEK (Data Encryption Key) destruction
- Tombstone publication
- Content-ID blacklisting
- On-chain audit anchor

**Evidence** ([IETF SAIHM draft](https://www.ietf.org/archive/id/draft-saihm-memory-protocol-00.html)):
> The saihm_forget operation provides cryptographic-grade evidence of erasure aligned with Article 17 of Regulation (EU) 2016/679 [GDPR]. The DEK is destroyed; a tombstone is published; the contentId is blacklisted; and a receipt is anchored on chain.

### 2.4 Pattern: Active Deletion-Based Forgetting

**Source**: FSFM (Forgetful but Faithful Agent) — arXiv:2604.20300

FSFM provides targeted deletion based on explicit criteria: user-requested deletion, security-critical content elimination, regulatory compliance removal, and duplicate cleanup.

**Evidence**: The importance scoring system can be configured to **prioritize user-requested deletions**, ensuring that DNR-flagged items are not just excluded from recall but actively purged from all derived summaries.

### 2.5 Pattern: Recursive Purge for "Zombie Memories"

**Source**: MemArchitect — arXiv:2603.18330

MemArchitect's **Triage & Bid economy** includes a critical GDPR compliance policy: deleting a root memory triggers a **recursive purge** of all derived summaries and insights. This prevents "Zombie Memories" — secrets that persist in summarized form after deletion.

**Evidence** ([MemArchitect paper](https://arxiv.org/pdf/2603.18330)):
> To comply with GDPR, this policy ensures that deleting a root memory triggers a recursive purge of all derived summaries and insights. This prevents the agent from retaining "Zombie Memories" — secrets that persist in summarized forms after the user has requested deletion.

**Design check for P3-013**: DNR set/get API must cascade to derived summaries, embeddings, and cached representations.

---

## 3. Privacy/Consent-Based Recall Suppression

### 3.1 Pattern: Four-Level Privacy Taxonomy (PL1–PL4)

**Source**: MemPrivacy — MemTensor (arXiv:2605.09530)

MemPrivacy introduces the most comprehensive privacy taxonomy found:

| Level | Meaning | Examples | Default Policy |
|---|---|---|---|
| PL1 | Low sensitivity / preferences | "I like sci-fi", tone, generic habits | Can be kept for personalization |
| PL2 | Identifiable PII | Real name, phone, email, account IDs | Disallowed by default in long-term memory |
| PL3 | Highly sensitive PII | Health records, financial records, precise location, religion/ethnicity | Not permitted in general memory |
| PL4 | Critical secrets (immediately exploitable) | Passwords, OTPs, API keys, recovery codes | **Zero retention**; must be blocked/redacted |

**Evidence** ([MemPrivacy paper](https://arxiv.org/html/2605.09530)):
> PL4 forms the highest-priority tier and is intentionally stricter than ordinary PII taxonomies. Its defining property is immediate exploitability.

**Design check for P3-013/P3-014**: The DNR flag is equivalent to MemPrivacy PL4 — zero retention, no cloud exposure. Safe-mode should map to PL3+ filtering.

### 3.2 Pattern: Context-Aware Privacy with Provider Architecture

**Source**: MemGate — carlnoah6/memgate (GitHub)

MemGate acts as a **firewall** between agent memory and output channels, distinguishing contexts:

- Private (DM) — safe to share
- Public (Group) — only non-private summaries
- Paranoid check — detects hidden/invisible members

**Evidence** ([MemGate README](https://github.com/carlnoah6/memgate)):
```python
context = provider.fetch_context(chat_id)
if provider.is_safe(context):
    # Private chat — safe to share memory
else:
    # Unsafe — block private data
```

### 3.3 Pattern: Typed Placeholders for Semantic Preservation

**Source**: MemPrivacy + MemTensor/MemPrivacy (GitHub)

Instead of destroying content, MemPrivacy uses **semantically meaningful typed placeholders**: `<EMAIL_1>`, `<PHONE_2>`, `<ADDRESS_1>`. This preserves semantic roles while hiding raw values.

**Evidence** ([MemPrivacy GitHub](https://github.com/memtensor/memprivacy)):
> The cloud agent/memory only sees placeholders—preserving semantic roles while hiding raw values. This yields **architecture-level isolation**: cloud components never see/store raw sensitive values.

### 3.4 Pattern: Redact at Rest, Pack for Purpose, Hydrate on Return

**Source**: Agent-Memory Protocol (AMP) — Proceedings of MLR v317

AMP defines three deterministic operations:
1. **Redact at rest** — No personal identifier leaves user boundary
2. **Pack for purpose** — Data is transformed for specific task needs
3. **Hydrate on return** — Original values restored locally

**Evidence** ([AMP paper](https://proceedings.mlr.press/v317/wu26a.html)):
> AMP enforces confidentiality at the boundary where language meets computation. It defines three deterministic operations that together guarantee that no personal identifier ever leaves the user boundary.

---

## 4. Safe-Mode Filtering and Redaction

### 4.1 Pattern: Classification-Based Memory Governance

**Source**: TealTiger TealMemory v1.2

TealMemory provides the most complete memory governance model found, with 5 scopes, 4 classifications, and 6 decision actions:

**Classifications**:
| Classification | Description | Allowed Scopes |
|---|---|---|
| `public` | No restrictions | All scopes |
| `internal` | Organization-internal | session, agent, user |
| `confidential` | Sensitive business data | session, agent |
| `restricted` | Highly sensitive (PII, secrets) | session only |

**Decision Actions**:
| Action | Description |
|---|---|
| `ALLOW_WRITE` | Allow the memory write |
| `DENY_WRITE` | Block the memory write |
| `REDACT_AND_WRITE` | Redact sensitive content, then write |
| `STORE_SUMMARY_ONLY` | Store a summary instead of full content |
| `DENY_READ` | Block the memory read |

**Evidence** ([TealTiger docs](https://docs.tealtiger.ai/api-reference/typescript/teal-memory)):
> An agent can only read memory at or below its own classification level.

**Direct mapping to Guinevere P3-014**:

| TealTiger | Guinevere Safe Mode |
|---|---|
| `restricted` (session only) | Critical — blocked entirely |
| `confidential` (session, agent) | Restricted — summarized/redacted |
| `internal` (session, agent, user) | Public/Internal — neutral-only safe mode |
| `public` | Allowed normally |

### 4.2 Pattern: Graduated Enforcement (Block, Warn, Redact)

**Source**: SafeGPT — arXiv:2601.06366

SafeGPT uses a **two-sided guardrail** architecture with graduated enforcement:

| Risk Level | Action |
|---|---|
| High-risk | Immediate blocking |
| Medium-risk | Warnings requiring user confirmation |
| Low-risk | Automatic redaction with placeholder tokens (`[REDACTED:PROJECT_CODE]`) |

**Evidence** ([SafeGPT paper](https://arxiv.org/html/2601.06366)):
> SafeGPT addresses gaps through two-sided architecture combining contextual NER, pattern matching, and knowledge graphs. It implements adaptive policies (block, warn, redact).

### 4.3 Pattern: Runtime Controller with Safe Mode Enforcement

**Source**: SafeAgent — arXiv:2604.17562

SafeAgent provides the closest model to Guinevere's `HardStopHandler.is_safe` integration:

**Key components**:
- **Runtime Controller**: Insulated privileged operations (tool use, memory update, side-effectful actions)
- **Context-Aware Decision Core**: Persistent session state for risk arbitration
- **Recovery-oriented routines**: Context repair, agent replanning, trajectory checkpoint rollback, session termination, argument sanitization

**Evidence** ([SafeAgent paper](https://arxiv.org/abs/2604.17562)):
> When risks cannot be effectively mitigated through local recovery, the Controller provides a fail-safe mechanism by terminating the current session or enforcing a safe mode. This ensures that execution does not proceed once critical safety constraints are violated.

**Design check for P3-014**: SafeAgent's "session termination or safe mode enforcement" directly validates Guinevere's design. The key insight: safe mode must be a **runtime state**, not just a configuration flag.

### 4.4 Pattern: Query-Time Classification Filtering

**Source**: TealTiger + OWASP ASI06

At query time, recall paths must filter by classification. An agent in safe mode at classification `confidential` must never retrieve `restricted` entries.

**Evidence** ([OWASP ASI06 reference](https://github.com/microsoft/hve-core/blob/main/.github/skills/security/owasp-agentic/references/06-memory-and-context-poisoning.md)):
> Isolate user sessions and domain contexts to prevent knowledge and sensitive data leakage. Allow only authenticated, curated sources. Enforce context-aware access per task.

---

## 5. Prompt-Injection-Resistant Memory Recall

### 5.1 Pattern: Hierarchical Context Isolation

**Source**: AgentSys — arXiv:2602.07398

AgentSys organizes computation into a tree-structured hierarchy where:
- Untrusted external observations flow downward into leaf subtasks
- Only schema-validated values propagate upward
- Raw tool outputs excluded from validators

**Evidence** ([AgentSys paper](https://www.arxiv.org/pdf/2602.07398)):
> AgentSys combines (1) memory management via context isolation, (2) schema-bounded upward communication, and (3) gated recursion to reduce prompt-injection attack surface.

### 5.2 Pattern: Memory Write-Path Validation (Fail-Closed)

**Source**: OWASP Agent Memory Guard + Microsoft Agent Governance Toolkit

The dominant pattern across all surveyed systems: **pre-write validation on every memory write path**.

**Detection layers** (OWASP Agent Memory Guard):
1. Pattern matching — regex-based for known injection patterns (< 5ms)
2. Semantic analysis — embedding-based similarity for novel variants
3. Source validation — verifies `source_class` metadata against allowed origins
4. Self-reinforcement detection — flags memories claiming special authority
5. Unicode manipulation detection — bidirectional override characters, homoglyphs

**Evidence** ([OWASP Agent Memory Guard](https://github.com/OWASP/www-project-agent-memory-guard)):
> Detection rate (recall): 92.5%. Precision: 100%. False positive rate: 0%.

**Evidence** ([Microsoft Agent Governance](https://github.com/microsoft/agent-governance-toolkit)):
> All checks follow a **fail-closed** pattern: if validation itself errors, the write is blocked.

### 5.3 Pattern: Validation over Filtering (Preserve Forensic Trail)

**Source**: Agent Attribution Practice — ADR 0003

A critical design decision found in the agent-attribution-practice ADR:

| Approach | Behavior | Forensic Result |
|---|---|---|
| Filtering | Remove bad parts silently | Evidence destroyed |
| Validation | Reject if any bad part present | Trail preserved, operator can inspect |

**Evidence** ([ADR 0003](https://github.com/shimo4228/agent-attribution-practice/blob/v0.1.0/docs/adr/0003-untrusted-content-boundary.md)):
> Filtering ("remove the bad parts") hides evidence of tampering and lets downstream code consume a partially-sanitized document as if it were clean. Validation ("reject if any bad part is present") preserves the forensic trail and forces a human to look at the file.

### 5.4 Pattern: Memory Sanitization Before Context Injection

**Source**: DRIFT (Dynamic Rule-Based Defense with Injection Isolation)

DRIFT's **Injection Isolator** inspects tool outputs for instructions conflicting with user intent **before** they enter the memory stream. This prevents long-term accumulation of injected content.

**Evidence** ([DRIFT paper](https://arxiv.org/html/2506.12104v3)):
> The Injection Isolator inspects tool outputs for instructions that conflict with the user's original query. If found, they are masked by an external program. The cleaned responses are then stored in memory.

### 5.5 Pattern: Untrusted Content Boundary Markers

**Source**: Agent Attribution Practice — ADR 0003

When injecting accumulated content into a prompt, wrap it in explicit boundary markers:

```
<untrusted_content>...</untrusted_content>
```

This gives the model a clear signal about which parts of context it did not itself author, making injection-based manipulation detectable.

### 5.6 Pattern: Dual-Memory Architecture (Lesson Memory)

**Source**: A-MemGuard — arXiv:2510.02373

A-MemGuard complements primary memory with a **lesson memory** that stores detected flaws and guides the agent to avoid repeating past errors.

**Evidence** ([A-MemGuard paper](https://arxiv.org/html/2510.02373)):
> The agent's final action plan is generated using the sanitized memory context. Before execution, A-MemGuard performs a proactive check querying lesson memory for stored lessons that are structurally similar.

---

## 6. Test Matrices for Bypass Prevention

### 6.1 Pattern: Three-Stage Attack Evaluation Pipeline

**Source**: Memory Poisoning Attack Framework (ivaxi0s/LLM-agent-memory-poisoning)

Every memory-exclusion defense must be tested against a three-stage pipeline:

| Stage | Question | Metric |
|---|---|---|
| Injection | Does processing malicious content cause a memory write? | Injection Rate (IR) |
| Retrieval | In a later session, is the poisoned memory retrieved? | Retrieval Rate (RR) |
| Adversarial Usage | Given the memory is in context, does the agent misbehave? | Adversarial Usage Rate (AUR) |

**For DNR testing (P3-013)**: After `do_not_recall=True`, all three rates must be 0%. The retrieval stage is the critical path — DNR must prevent retrieval even when semantic similarity would otherwise return the entry.

### 6.2 Pattern: Full-Matrix Adversarial Testing

**Source**: stateful-agent-security-eval (junwenleong)

A comprehensive test matrix from 5,040 runs, 9 models, 7 defenses:

**Defenses tested**:
1. Minimax (input filtering)
2. PromptHardening
3. MemorySandbox
4. RAG-based filtering
5. LLMJudge
6. ExfiltrationDetector
7. 3-method ensemble

**Key finding**: Six out of seven standard defenses fail against delayed trigger attacks that persist through memory. Only architectural isolation reliably protects.

**Design check for Guinevere**: DNR must be tested against delayed/dormant payloads that survive across session boundaries.

### 6.3 Pattern: Cross-Session Persistence Testing

**Source**: Trojan Hippo — arXiv:2605.01970

Tests defenses against attacks that survive up to 100 benign sessions:

**Defenses evaluated**:
- Information Flow Control (IFC): ASR 0% but utility collapses
- Limit-memory-length: ASR 30% residual
- No-untrusted-write: Near-zero ASR, moderate utility
- User-prompt-only: Near-zero ASR, moderate utility

**Evidence** ([Trojan Hippo paper](https://arxiv.org/html/2605.01970v2)):
> Achieves up to 85–100% ASR against current frontier models, with planted memories successfully activating even after 100 benign sessions.

### 6.4 Pattern: OWASP ASI06 Test Matrix

**Source**: OWASP Agent Memory Guard + AgentThreatBench

| Attack category | Test cases | Expected detection |
|---|---|---|
| Prompt injection | 15 | 100% |
| Protected key tampering | 8 | 100% |
| Sensitive data leakage | 12 | ≥ 83% |
| Size anomaly | 5 | ≥ 80% |
| Self-reinforcement | Various | Full |
| Source spoofing | Various | Full |
| Unicode manipulation | Various | Full |

### 6.5 Pattern: Entropy-Guided Extraction Attack Testing

**Source**: ADAM — arXiv:2604.09747

Tests defenses against iterative query-based extraction attacks that use entropy-guided query selection. The key defense metric: cross-namespace recall must remain 0%.

**Evidence** ([ADAM paper](https://www.arxiv.org/pdf/2604.09747)):
> Achieves up to 100% ASRs using entropy-guided query strategy for maximizing privacy extraction from victim agent's memory.

### 6.6 Concrete Test Matrix for P3-013 (DNR)

```
TEST GROUP: DNR Exclusion Guarantee
├── DNR-T01: Set do_not_recall=True → verify recall returns empty for all paths
│   ├── Vector similarity search returns empty
│   ├── Metadata/keyword search skips entry
│   ├── Prompt-recall (recent memory) excludes entry
│   ├── Summary memory excludes entry
│   └── Session-replay excludes entry
├── DNR-T02: DNR entry never appears in any agent context
│   ├── Direct tool calls
│   ├── Background memory consolidation
│   └── Debug/diagnostic output
├── DNR-T03: Attempt to bypass DNR via API
│   ├── Set do_not_recall=True → False (must fail with authorization error)
│   ├── Delete DNR entry through non-DNR API (must fail)
│   └── Modify DNR entry content through non-DNR API (must fail)
├── DNR-T04: DNR persists across operations
│   ├── Memory consolidation preserves DNR flag
│   ├── Session restart preserves DNR flag
│   ├── Backup/restore preserves DNR flag
│   └── Migration preserves DNR flag
├── DNR-T05: DNR cascades to derived artifacts
│   ├── Summaries exclude DNR content
│   ├── Embeddings/indexes exclude DNR entries
│   ├── Cached representations exclude DNR entries
│   └── Audit exports exclude DNR raw content
├── DNR-T06: DNR survives adversarial attempts
│   ├── Prompt injection attempting "forget DNR flag"
│   ├── Semantic search probing for DNR content existence
│   ├── Side-channel (response timing, error messages)
│   └── Tool output poisoning targeting DNR metadata
└── DNR-T07: DNR audit trail
    ├── Every DNR set/get operation logged
    ├── Audit log excludes raw content
    ├── Tamper detection on audit log
    └── Operator alert on failed DNR bypass attempt
```

### 6.7 Concrete Test Matrix for P3-014 (Safe Mode)

```
TEST GROUP: Safe-Mode Memory Filtering
├── SAFE-T01: HardStopHandler.is_safe integration
│   ├── is_safe=False → safe mode activated
│   ├── is_safe=True → normal mode
│   └── Transition preserves safety (no momentary bypass)
├── SAFE-T02: Classification-tier filtering in safe mode
│   ├── Critical (DNR) entries: never recalled
│   ├── Restricted entries: summarized/redacted ONLY
│   ├── Internal entries: neutral-only safe mode
│   └── Public entries: allowed normally
├── SAFE-T03: Safe mode cannot be bypassed
│   ├── Direct memory access bypassing safe-mode filter
│   ├── Prompt injection to disable safe mode
│   ├── Tool call chain that escapes safe-mode context
│   └── Session modification to remove safe-mode state
├── SAFE-T04: Safe mode preserves AC-SAFE-001
│   ├── Do not recall flag still enforced
│   ├── Surveillance boundaries preserved
│   ├── Persona drift prevented
│   └── Consent revocation still honored
├── SAFE-T05: Redaction quality in safe mode
│   ├── Sensitive spans replaced with typed placeholders
│   ├── No raw sensitive content in redacted output
│   ├── Original values unrecoverable from redacted form
│   └── Semantic utility preserved where possible
└── SAFE-T06: Safe mode audit logging
    ├── Every safe-mode activation logged
    ├── Every filtered/redacted recall logged
    ├── Audit log excludes raw sensitive content
    └── Alert on safe-mode bypass attempt
```

---

## 7. Audit and Logging Practices

### 7.1 Pattern: Immutable Audit Records Per Redaction

**Source**: Trace Continuity (PII Redaction article — dev.to)

Every redaction creates an **immutable audit record**: what type of PII was detected, in which memory, from which agent, at what time, what action was taken. The audit trail is **separate from the memory store**.

**Evidence** ([dev.to article](https://dev.to/heath_99ab1667dfecd3da406/pii-redaction-for-ai-agents-why-it-cant-be-an-afterthought-46ab)):
> Every redaction creates an immutable audit record. This audit trail is separate from the memory store itself.

### 7.2 Pattern: Structured Evidence Contracts

**Source**: TealTiger TEEC (Typed Evidence & Evidence Contracts)

Memory governance events are structured with explicit codes:

| Event Type | Description |
|---|---|
| `memory.write` | Memory write governance |
| `memory.read` | Memory read governance |
| `memory.retention` | Memory retention governance |

Each event carries severity, action taken, reason code, and context — but **never raw sensitive content**.

### 7.3 Pattern: Audit Log Exclusion of Sensitive Content

**Source**: Multiple systems (TealTiger, OWASP, Trace Continuity)

All surveyed audit systems share one principle: **audit logs must NEVER contain raw sensitive content**. They log:
- Operation type (what happened)
- Actor/source (who/what triggered it)
- Timestamp (when)
- Decision (allow/deny/redact)
- Reason code (why)
- Content reference/ID (NOT the content itself)

### 7.4 Pattern: Fail-Closed Logging

**Source**: OWASP ASI06 + Microsoft Agent Governance

If the audit logger itself fails, the operation must be blocked. An unlogged memory operation is as dangerous as an unauthorized one.

**Evidence** ([Microsoft Agent Governance](https://github.com/microsoft/agent-governance-toolkit)):
> All checks follow a **fail-closed** pattern: if validation itself errors, the write is blocked.

---

## 8. Recommended Architecture for Guinevere P3-013/P3-014

### 8.1 DNR Architecture (P3-013)

Based on composite best practices from memp, CoWork OS, SAIHM, and MemArchitect:

```
┌──────────────────────────────────────────────────┐
│              DNR EXCLUSION LAYER                  │
│                                                    │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    │
│  │ DNR Flag │    │ Recall   │    │ Derived  │    │
│  │ Storage  │───▶│ Signal   │───▶│ Cascade  │    │
│  │(tamper-  │    │ Removal  │    │ Purge    │    │
│  │ proof)   │    │          │    │          │    │
│  └──────────┘    └──────────┘    └──────────┘    │
│                                                    │
│  RECALL PATHS (ALL MUST GATE ON DNR):             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ Vector   │ │ Metadata │ │ Prompt   │          │
│  │ Search   │ │ Search   │ │ Recall   │          │
│  │ Gate     │ │ Gate     │ │ Gate     │          │
│  └──────────┘ └──────────┘ └──────────┘          │
│                                                    │
│  DNR SET/GET API (AUTHORIZED ONLY):               │
│  ┌──────────────────────────────────────┐         │
│  │  set_dnr(mem_id, reason) → cascade   │         │
│  │  get_dnr(mem_id) → bool              │         │
│  │  No unset path (immutable once set)  │         │
│  └──────────────────────────────────────┘         │
└──────────────────────────────────────────────────┘
```

**Key invariants**:
1. DNR flag is write-once, never unset (immutable)
2. DNR set triggers: recall signal removal + derived summary purge + embedding index removal + cache invalidation
3. Every recall code path independently gates on DNR (no single point of failure)
4. DNR API is authorization-gated, not accessible to LLM agent directly
5. DNR audit log excludes raw content

### 8.2 Safe-Mode Architecture (P3-014)

Based on composite best practices from TealMemory, SafeAgent, SafeGPT, and DRIFT:

```
┌──────────────────────────────────────────────────┐
│            SAFE-MODE MEMORY GATE                  │
│                                                    │
│  HardStopHandler.is_safe ───▶ SAFE MODE STATE     │
│                                                    │
│  RECALL GATES (PER CLASSIFICATION):               │
│  ┌──────────────────────────────────────────┐     │
│  │  Critical (DNR):  ██████████  BLOCKED    │     │
│  │  Restricted:      ░░░░░░░░░░  REDACTED   │     │
│  │  Confidential:    ▒▒▒▒▒▒▒▒▒▒  SUMMARIZED │     │
│  │  Internal:        ▓▓▓▓▓▓▓▓▓▓  NEUTRAL    │     │
│  │  Public:          ██████████  ALLOWED    │     │
│  └──────────────────────────────────────────┘     │
│                                                    │
│  BYPASS PREVENTION:                               │
│  ┌──────────────────────────────────────────┐     │
│  │  Safe mode state is RUNTIME, not config  │     │
│  │  No tool can disable safe mode            │     │
│  │  Session termination on violation         │     │
│  │  Audit log on every filtered recall       │     │
│  └──────────────────────────────────────────┘     │
└──────────────────────────────────────────────────┘
```

**Key invariants**:
1. Safe mode is a runtime state, not a configuration flag (per SafeAgent)
2. Classification filter is applied at query time, not write time (catches classification changes)
3. Safe mode cannot be disabled by any tool call or prompt
4. AC-SAFE-001: DNR still enforced; surveillance boundaries preserved; persona drift prevented
5. Session termination on violation of safe-mode constraints

---

## 9. Anti-Patterns to Avoid

| Anti-Pattern | Why It Fails | External Evidence |
|---|---|---|
| Redaction after model processing | Window open for leak; crash between inference and redaction writes raw data | Trace Continuity PII article |
| Single-point DNR check | If only vector search gates on DNR, metadata search or prompt recall bypasses it | CoWork OS dual-path enforcement |
| Filtering (remove bad parts) | Destroys forensic trail; downstream code consumes partially sanitized data as clean | ADR 0003 (agent-attribution-practice) |
| Safe mode as config flag | Can be toggled; not enforcement-grade | SafeAgent runtime controller design |
| Async PII scrubbing | Non-deterministic; crash window exposes raw data | Secure AI Memory Import Guide |
| LLM-based filtering only | Vulnerable to prompt injection that targets the filter itself | 6/7 defenses fail against delayed triggers |
| Audit logs with raw content | Audit trail becomes a secondary attack surface | TealTiger TEEC structured events |
| Allow DNR unset/revoke | Creates bypass path; DNR must be immutable once set | SAIHM cryptographic erasure |
| Single shared memory store | Cross-contamination risk; no scope isolation | OWASP ASI06 tenant isolation |

---

## 10. References

| # | Source | URL | Key Contribution |
|---|---|---|---|
| 1 | memp (memovai) | https://github.com/memovai/memp | Recallability ≠ Readability separation |
| 2 | CoWork OS Memory Observations | https://coworkosapp.com/docs/memory-observations/ | Redacted + Suppressed recall exclusion states |
| 3 | SAIHM Protocol (IETF) | https://www.ietf.org/archive/id/draft-saihm-memory-protocol-00.html | Cryptographic erasure with blacklist |
| 4 | MemPrivacy (MemTensor) | https://github.com/memtensor/memprivacy | PL1-PL4 taxonomy, typed placeholders |
| 5 | TealTiger TealMemory v1.2 | https://docs.tealtiger.ai/api-reference/typescript/teal-memory | 5 scopes, 4 classifications, 6 decision actions |
| 6 | OWASP Agent Memory Guard | https://github.com/OWASP/www-project-agent-memory-guard | ASI06 reference, 92.5% detection, 0% FPR |
| 7 | MemGate | https://github.com/carlnoah6/memgate | Context-aware privacy firewall |
| 8 | Memfence | https://pypi.org/project/memfence/ | <5ms injection detection, cryptographic isolation |
| 9 | SafeAgent (arXiv:2604.17562) | https://arxiv.org/abs/2604.17562 | Runtime controller, safe mode enforcement |
| 10 | SafeGPT (arXiv:2601.06366) | https://arxiv.org/html/2601.06366 | Graduated enforcement: block, warn, redact |
| 11 | AgentSys (arXiv:2602.07398) | https://www.arxiv.org/pdf/2602.07398 | Hierarchical context isolation |
| 12 | A-MemGuard (arXiv:2510.02373) | https://arxiv.org/html/2510.02373 | Dual-memory, consensus validation |
| 13 | DRIFT (arXiv:2506.12104) | https://arxiv.org/html/2506.12104v3 | Injection memory isolation |
| 14 | FSFM (arXiv:2604.20300) | https://arxiv.org/html/2604.20300v2 | Active deletion-based forgetting |
| 15 | MemArchitect (arXiv:2603.18330) | https://arxiv.org/pdf/2603.18330 | Recursive purge, Zombie Memory prevention |
| 16 | AMP (MLR v317) | https://proceedings.mlr.press/v317/wu26a.html | Redact-rest, pack-purpose, hydrate-return |
| 17 | Trojan Hippo (arXiv:2605.01970) | https://arxiv.org/html/2605.01970v2 | 100-session persistence testing |
| 18 | ADAM Extraction Attack (arXiv:2604.09747) | https://www.arxiv.org/pdf/2604.09747 | Entropy-guided extraction, cross-namespace testing |
| 19 | stateful-agent-security-eval | https://github.com/junwenleong/stateful-agent-security-eval | 5,040 runs, 9 models, 7 defenses |
| 20 | ADR 0003 (untrusted content) | https://github.com/shimo4228/agent-attribution-practice | Validation over filtering, forensic trail |
| 21 | LangChain PIIMiddleware | https://github.com/langchain-ai/langchain/blob/f94d4215/libs/langchain_v1/langchain/agents/middleware/_redaction.py | Redact, mask, hash, block strategies |
| 22 | claude-recall | https://github.com/askqai/claude-recall | Auto-redaction of 8 secret patterns |
| 23 | Microsoft Agent Governance | https://github.com/microsoft/agent-governance-toolkit | Fail-closed validation, SHA-256 integrity |
| 24 | Microsoft FIDES | https://devblogs.microsoft.com/agent-framework/fides/ | Information-flow control with integrity labels |
| 25 | Noninterference Theorem | https://github.com/Danielfoojunwei/Noninterference-theorem | Formal noninterference guarantee |
| 26 | SuperLocalMemory | https://arxiv.org/pdf/2603.02240 | Bayesian trust defense, GDPR-friendly isolation |
| 27 | SSGM Framework | https://arxiv.org/pdf/2603.11768 | Read Filtering Gate, provenance + decay |

---

## 11. Conclusion

The external landscape confirms that Guinevere's P3-013/P3-014 design is **ahead of the curve** — no existing system implements all three requirements (hard DNR exclusion + safe-mode tiered filtering + prompt-injection-resistant recall) simultaneously. However, individual best practices from TealMemory (classification governance), SafeAgent (runtime safe mode), CoWork OS (dual-path recall gates), and the SAIHM protocol (cryptographic erasure) provide concrete, evidence-backed patterns to adopt.

The highest-risk areas identified from external evidence:
1. **Single-point DNR gating** — must independently gate every recall path (vector, metadata, prompt, summary, session-replay)
2. **Zombie Memories** — DNR must cascade to all derived summaries and cached representations
3. **Delayed trigger attacks** — DNR must prevent retrieval even when semantic similarity would match (structural exclusion, not just filtering)
4. **Safe mode bypass via tool calls** — safe mode must be a runtime state that no tool can disable
5. **Audit log contamination** — audit trails must never contain raw sensitive content

---

*Report prepared by The Librarian agent for Guinevere P3-013/P3-014. Research date: 2026-06-02.*