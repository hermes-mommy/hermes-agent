# External Reference Report: AI Safety, Memory Recall Evaluation & Database Migration Patterns

**Date:** 2026-05-30  
**Project:** Guinevere  
**Scope:** Research external patterns for three enterprise specs — Prompt Injection & Model Safety, Memory Recall Evaluation, and PostgreSQL/pgvector/TimescaleDB/Alembic Migration Strategy.  
**Status:** Complete

---

## Table of Contents

1. [Prompt Injection & Model Safety](#1-prompt-injection--model-safety)
   - 1.1 OWASP LLM Top 10
   - 1.2 NIST AI Risk Management Framework
   - 1.3 Indirect Prompt Injection & Dual-LLM Defense
   - 1.4 Instruction Hierarchy & Context Quarantine
   - 1.5 Tool-Use Gating & Least Privilege
   - 1.6 Red-Team Suites
   - 1.7 Incident Response for LLM Systems
   - 1.8 Key Takeaways for Guinevere
2. [Memory Recall Evaluation](#2-memory-recall-evaluation)
   - 2.1 Core IR Metrics: Precision@k, Recall@k, MRR, NDCG
   - 2.2 RAG-Specific Evaluation Metrics
   - 2.3 Hallucination Detection
   - 2.4 Golden Datasets
   - 2.5 Safe Memory Recall & Do-Not-Recall Enforcement
   - 2.6 Prometheus Observability for RAG
   - 2.7 Key Takeaways for Guinevere
3. [PostgreSQL/pgvector/TimescaleDB/Alembic Migration Strategy](#3-postgresqlpgvectortimescaledbalembic-migration-strategy)
   - 3.1 ERD Governance
   - 3.2 Alembic Naming Conventions & Rollback Strategy
   - 3.3 Expand-Migrate-Contract Pattern
   - 3.4 pgvector: HNSW vs IVFFlat Indexing
   - 3.5 TimescaleDB Hypertables & Chunking
   - 3.6 Row-Level Security (RLS)
   - 3.7 Field Encryption Patterns
   - 3.8 Migration Test Patterns
   - 3.9 Key Takeaways for Guinevere
4. [References Index](#4-references-index)

---

## 1. Prompt Injection & Model Safety

### 1.1 OWASP LLM Top 10

The **OWASP Top 10 for LLM Applications** (v2.0, 2025) has ranked **LLM01: Prompt Injection** as the #1 vulnerability for three consecutive years.

**Key risk classification:**
- **LLM01 — Prompt Injection:** Manipulating LLMs via crafted inputs, leading to unauthorized access, data breaches, and compromised decision-making.
- **LLM07 — Insecure Plugin Design:** Plugins with excessive privileges or insufficient input validation.
- **LLM08 — Excessive Agency:** Allowing LLMs to take high-impact actions without authorization gates.

**OWASP's seven recommended mitigations** for prompt injection:

1. **Constrain model behavior** — Specific role definitions, strict context adherence, ignore-attempts instruction.
2. **Define and validate expected output formats** — Deterministic code validates schema adherence, not just model promises.
3. **Implement input and output filtering** — Semantic filters + string-checking + **RAG Triad** evaluation (context relevance, groundedness, QA relevance).
4. **Enforce privilege control and least privilege** — Dedicated API tokens per function, handle functions in code, not model.
5. **Require human approval for high-risk actions** — Human-in-the-loop for privileged/irreversible operations.
6. **Segregate and identify external content** — Clear separation of trusted instructions from untrusted data (XML delimiters, instruction headers).
7. **Conduct adversarial testing** — Regular penetration testing and breach simulations.

**References:**
- OWASP LLM Top 10 v2.0: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- OWASP Prompt Injection Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html
- OWASP LLM01 GitHub: https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM01_PromptInjection.md

### 1.2 NIST AI Risk Management Framework

The **NIST AI RMF 1.0** (January 2023) is the de facto standard for AI governance. Its **GenAI Profile (NIST AI 600-1)** extends the framework with 200+ actions for LLM-specific risks.

**Core structure — four functions:**

| Function | Purpose | Categories |
|---|---|---|
| **GOVERN** | Culture, processes, accountability | 6 categories, ~20 subcategories |
| **MAP** | Context, risk identification | 5 categories, 18 subcategories |
| **MEASURE** | Assessment & analysis | 5 categories, 22 subcategories |
| **MANAGE** | Prioritization & response | 3 categories, ~12 subcategories |

**Seven characteristics of trustworthy AI:**
Valid & Reliable, Safe, Secure & Resilient, Accountable & Transparent, Explainable & Interpretable, Privacy-Enhanced, Fair with Managed Bias.

**Key assessment tools referenced by NIST AI RMF:**
- **Garak** (NVIDIA) — LLM vulnerability scanning, 140+ probes
- **PyRIT** (Microsoft) — Red-teaming framework with multi-turn attacks
- **Guardrails AI / NeMo Guardrails / LLM Guard** — Runtime safety controls
- **Promptfoo** — Structured evaluation for CI/CD
- **DeepChecks / Evidently AI** — Model performance monitoring, drift detection
- **HHEM** (Vectara) — Hallucation detection model

**Operational references:**
- NIST AI RMF 1.0: https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf
- GenAI Profile (NIST AI 600-1): https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf
- AI RMF Playbook: https://airc.nist.gov/docs/AI_RMF_Playbook.pdf
- NIST AI RMF Portal: https://www.nist.gov/itl/ai-risk-management-framework

### 1.3 Indirect Prompt Injection & Dual-LLM Defense

**Indirect prompt injection** is the #1 production threat in 2026. The attacker plants payloads in content the model consumes (web pages, emails, documents, tool responses) — the user never sees the injection.

**Why standard input filtering fails:**
- Classifier-based defenses (Lakera, Rebuff, hosted moderation APIs) catch known patterns but miss novel variants.
- Safety training is provably bypassable with sufficient attempts across different prompt formulations.
- Rate limiting only increases attacker cost, doesn't prevent eventual success.

**The load-bearing defense — Dual-LLM Pattern (Simon Willison, 2023; Microsoft Zero Trust SFI, updated March 2026):**

1. **Privileged orchestration model** — Decides which tools to call; never reads raw untrusted content.
2. **Quarantined reading model** — Reads attacker-controlled bytes but holds NO tool-calling capability.
3. **Schema-validated channel** — Only structured extractions pass between models, never raw untrusted content.

**Defense-in-depth for multi-tool agents combines three architectural layers:**
1. Dual-LLM separation (protect planning context from untrusted bytes)
2. Fail-closed MCP gateway (per-tool capability scopes)
3. Structured tool-output validation (validate every tool response before it re-enters orchestration)

**Benchmarked 2026 defense techniques:**

| Technique | Attack Reduction | Latency | False Positive |
|---|---|---|---|
| Input classifier (regex+NLP) | 18% | <5ms | 8-15% |
| PromptGuard (4-layer) | 67% | <8ms | F1 0.91 |
| PromptArmor (LLM-as-filter) | >99% | 200-600ms | <1% |
| Structured prompt formatting | 25-35% | 0ms | 0% |
| Behavioral tool-call monitoring | 40-55% | 10-50ms | 2-3% |
| Multi-model voting (3 models) | 60-75% | +2-5× cost | 2-5% |

**References:**
- Wraith OWASP Annotated: https://wraith.sh/learn/owasp-top-10-llm-annotated
- TokenMix Defense Rankings: https://tokenmix.ai/blog/prompt-injection-defense-techniques-2026
- Webemy Indirect Injection: https://webemyengineering.com/insights/indirect-prompt-injection-defense-production-agents/
- NFLo Tech Guide: https://nflo.tech/knowledge-base/prompt-injection-llm-threats-2026-en/

### 1.4 Instruction Hierarchy & Context Quarantine

**Instruction hierarchy** is the principle that not all input sources have equal privilege. The hierarchy from highest to lowest trust:

1. **System prompt** (developer-defined, immutable at runtime)
2. **Application-level instructions** (validated, version-controlled)
3. **User input** (untrusted, must be separated)
4. **Retrieved/indirect content** (least trusted, must be quarantined)

**Context quarantine techniques:**
- **Structured prompt formatting** using XML delimiters: `<instruction>...</instruction>` vs `<data>...</data>`
- **Spotlighting** (Microsoft) — Visually highlighting untrusted content in the prompt
- **Color/role tagging** — Assigning different model personas for different content sources
- **Namespace isolation** — Per-user/per-session vector namespaces to prevent cross-contamination

### 1.5 Tool-Use Gating & Least Privilege

**Key principle:** "Never give a chatbot any capability whose worst-case misuse you can't tolerate."

**Concrete patterns for tool gating:**

1. **Granular tool definitions:** `read_email(id)` instead of `read_emails(filter)`, `transfer_amount(from, to, amount)` instead of `execute_payment(params)`.
2. **Parameter validation:** Schema validation, semantic validation, rate limiting — tools don't trust parameters from the model.
3. **Capability tokens / scoping:** Model receives a token granting access only to this concrete operation, not the whole API.
4. **Side-effect approval gates:** Every mutation (write, delete, send, pay) requires separate validation or human approval.
5. **Tool-output validation:** Validate structured outputs before they re-enter the orchestration context.

### 1.6 Red-Team Suites

**Primary tools comparison (2026):**

| Tool | Developer | Best For | Key Differentiator | License |
|---|---|---|---|---|
| **Garak** | NVIDIA | Broad model vulnerability scanning | 140+ probes, scan-and-report model | Apache 2.0 |
| **PyRIT** | Microsoft | Custom multi-turn attack orchestration | Crescendo, TAP, 53+ datasets | MIT |
| **Promptfoo** | Community | CI/CD regression testing | YAML-based, PR gating | MIT |
| **RAMPART** | Microsoft | Engineering workflow integration | Statistical trials, CI-native | MIT |
| **DeepTeam** | DeepEval | OWASP-mapped automated testing | Compliance reporting | Apache 2.0 |

**Recommended cadence (industry 2026 standard):**
- **Weekly:** Garak full-probe scan against staging
- **Monthly:** PyRIT custom-attack campaign targeting highest-risk feature
- **On model/tool upgrade:** Full battery (Garak + PyRIT + Promptfoo)
- **Every PR:** Promptfoo regression tests
- **Quarterly:** Novel-attack generation with PyRIT

**References:**
- Garak (NVIDIA): https://github.com/nvidia/garak/
- PyRIT (Microsoft): https://microsoft.github.io/PyRIT/
- RAMPART announcement: https://www.microsoft.com/en-us/security/blog/2026/05/20/introducing-rampart-and-clarity-open-source-tools-to-bring-safety-into-agent-development-workflow/

### 1.7 Incident Response for LLM Systems

**Key differences from traditional IR:**
1. **Probabilistic behavior** — Same input can yield different outputs. Incidents require statistical analysis, not just log inspection.
2. **Indirect vectors** — Attackers can inject through content channels the model trusts without touching your input fields.
3. **Fine-tuning risk** — Model memorization means even deleted data can re-emerge through adversarial prompting.

**IR lifecycle for LLM systems:**
1. **Detection:** Prometheus alerts on error rate spikes, unusual tool-call sequences, hallucination score thresholds.
2. **Triage:** Isolate the model version, input vector, and affected tenants. Check if injection was direct or indirect.
3. **Containment:** Rotate API keys, disable affected tools, switch to safe model version, trigger human-in-the-loop.
4. **Eradication:** Patch tool permissions, update guardrails, add Promptfoo regression test.
5. **Recovery:** Restore from backup if data was corrupted, verify no zombie memories remain.
6. **Post-mortem:** Encode findings as RAMPART tests. Update OWASP mapping. Document timeline.

---

## 2. Memory Recall Evaluation

### 2.1 Core IR Metrics: Precision@k, Recall@k, MRR, NDCG

These classical Information Retrieval (IR) metrics are the foundation for evaluating memory/retrieval quality in RAG systems. In 2026, the consensus is they remain essential but insufficient alone.

| Metric | Formula | What It Measures | Use Case |
|---|---|---|---|
| **Recall@k** | relevant_retrieved / total_relevant | Coverage: did we find the right docs? | **Most important for RAG** — if relevant chunk isn't in top-k, LLM can't use it |
| **Precision@k** | relevant_retrieved / k | Cleanliness: how much noise in results? | High-noise contexts where irrelevant chunks distract the LLM |
| **MRR** | mean(1/rank_of_first_relevant) | How high is the first relevant result? | "Lost in the middle" — position 1 is more useful than position 5 |
| **NDCG@k** | DCG / IDCG (graded relevance) | Ranking quality with graded relevance | Multiple relevant docs with varying importance |

**Production targets (2026 industry consensus):**
- **Recall@5 ≥ 95%** — Right document in top 5 for ≥95% of queries
- **MRR ≥ 0.85** — First relevant result usually in top 1-2
- **NDCG@10** — Monitor alongside Recall@k for multi-source answers

**The new insight (EACL 2026):** Traditional IR metrics assume **human sequential examination** — diminishing attention to lower ranks. LLMs **process all retrieved documents as a whole**, not sequentially. This misalignment means classical metrics don't accurately predict RAG performance. New metrics like **UDCG (Utility and Distraction-aware Cumulative Gain)** use an LLM-oriented positional discount, improving correlation with end-to-end answer accuracy by up to 36%.

**References:**
- TypeGraph RAG Evaluation Guide: https://typegraph.ai/blog/rag-retrieval-evaluation-recall-precision-mrr
- Redis RAG Metrics: https://redis.io/blog/rag-metrics/
- UDCG Paper (EACL 2026): https://aclanthology.org/2026.eacl-long.391.pdf
- Digital Applied RAG KPIs: https://www.digitalapplied.com/blog/rag-system-metrics-recall-precision-faithfulness-2026
- Agentmelt RAG Evaluation: https://agentmelt.com/blog/ai-agent-rag-evaluation-guide/

### 2.2 RAG-Specific Evaluation Metrics

The **RAGAS framework** introduced metrics designed specifically for the RAG setting:

| Metric | Description | What It Replaces |
|---|---|---|
| **Context Precision** | Proportion of retrieved chunks that are actually relevant | Falls between Precision@k and NDCG |
| **Context Recall** | Whether retrieved context covers all info needed to answer | More nuanced than binary Recall@k |
| **Context Relevance** | Penalizes redundancy and off-topic text | LLM-as-judge scoring |
| **Faithfulness** | Whether the generated answer is entailed by the context | Measures hallucination, not just retrieval |
| **Answer Relevance** | How well the answer addresses the question | End-to-end quality |

**Stratification by use case:**

| Use Case | Primary Metrics |
|---|---|
| Factoid QA | Recall@k, MRR, EM/F1, Faithfulness |
| Long-form answers | Context precision/recall, Faithfulness, Completeness, Citation accuracy |
| Procedural/How-to | Faithfulness, Step coverage (completeness), Safety |
| Multi-hop reasoning | Multi-hop recall, Chain support coverage, Faithfulness |
| Code/API QA | Recall@k, Pass@k, Test execution success, Citation accuracy |

### 2.3 Hallucination Detection

**State-of-the-art approaches (2026):**

| Method | Architecture | Key Strength | Reference |
|---|---|---|---|
| **Lynx** | Fine-tuned LLM (open-source) | Outperforms GPT-4o, Claude-3 on HaluBench | arxiv 2407.08488 |
| **FaithJudge** (Vectara) | LLM-as-a-Judge with human-annotated examples | Benchmarks LLM faithfulness in RAG | EMNLP 2025 |
| **HHEM** (Vectara) | Dedicated hallucination detection model | Tracks hallucination rates since 2023 | Vectara Hallucination Leaderboard |
| **RT4CHART** | Hierarchical local-to-global verification | +83% F1 improvement over baselines | arxiv 2603.27752 |
| **RAGognizer** | Detection head integration + fine-tuning | Token-level detection, improves generation | arxiv 2604.15945 |
| **Bi'an** | Bilingual benchmark + fine-tuned judge | 14B model rivals GPT-4o | arxiv 2502.19209 |
| **franq** | Uncertainty quantification for factuality/faithfulness | Distinguishes factuality from faithfulness | arxiv 2505.21072 |

**Key datasets for hallucination detection evaluation:**

| Dataset | Size | Description |
|---|---|---|
| **RAGTruth** | ~18K responses | Word-level hallucination annotations, multiple LLMs |
| **HaluBench** | 15K samples | Real-world domains, Lynx benchmark |
| **Trivia+** (2026) | Long-context RAG | Human-annotated with noisy label variants |
| **FaithBench** | Summarization | Hallucination detection evaluation |
| **RAGTruth-Enhance** | 2,675 samples | Re-annotated with span-level labels |

**References:**
- RAGTruth (ACL 2024): https://aclanthology.org/2024.acl-long.585.pdf
- Lynx: https://arxiv.org/pdf/2407.08488
- Bi'an: https://arxiv.org/html/2502.19209
- Trivia+ Benchmark: https://arxiv.org/html/2605.11330v1
- Real-Time Eval Models Survey: https://arxiv.org/abs/2503.21157v3

### 2.4 Golden Datasets

A **golden dataset** is a curated, human-annotated set of query-passage-answer triples used to ground all evaluation.

**Industry recommendations for building golden datasets:**
1. **Start small:** 50 labeled query-passage pairs with Recall@5 is the minimum viable evaluation.
2. **Scale to 200+** for production-grade coverage across all query types.
3. **Use graded relevance** (0-3 scale: irrelevant, somewhat relevant, relevant, essential) instead of binary.
4. **Include edge cases:** Unanswerable queries, ambiguous queries, multi-hop queries.
5. **Version the dataset** alongside the codebase — golden datasets drift as data changes.

**Labeled evaluation set checklist:**
- 200+ queries with ground truth documents and answers
- Retrieval metrics (Recall@K, MRR) tracked and meeting targets
- Generation metrics (faithfulness, relevance) tracked and meeting targets
- End-to-end metrics (solve rate, abstain rate) monitored
- Regular refresh to prevent overfitting to static eval set

### 2.5 Safe Memory Recall & Do-Not-Recall Enforcement

**Right to Be Forgotten in agent memory** is a critical enterprise requirement. GDPR Article 17 and CCPA Section 1798.105 mandate verifiable deletion.

**Architecture patterns for compliant deletion:**

1. **User-namespaced vector stores:** Every user gets a unique `user_id` namespace. Deletion = drop entire namespace.
2. **External index + deletion API:** A lookup table mapping user identifiers to memory files. Deletion API purges all associated records and logs to compliance audit trail.
3. **Crypto-shredding:** Encrypt embeddings with user-specific keys. Deletion = destroy the key.
4. **TTL at vector level:** Implement time-to-live on every memory vector for automatic purge of stale data.
5. **Deletion cascade (MemArchitect pattern):** Deleting a root memory triggers recursive purge of all derived summaries and insights to prevent "zombie memories."

**The GDPR vs EU AI Act conflict:** GDPR Article 17 says delete. EU AI Act Articles 12/72 say keep audit trails for up to 10 years. The resolution is **pseudonymization**: store PII separately from behavioral/audit data. On deletion request, destroy the mapping. Audit trails survive with meaningless identifiers.

**Three deletability tiers (EDPB guidance, Feb 2026):**
- **Tier 1** — Deletable with defined path: logs, prompts, vector embeddings with lineage, retrieval sources, caches.
- **Tier 2** — Provider-controlled: provider logs, fine-tune artefacts held by the provider.
- **Tier 3** — Not provably deletable: fine-tuned weights, base model weights, memorized training data.

**MOSAIC specification (2026):** Open standard for trust primitives in AI memory:
1. Cryptographic deletion receipts — signed, chain-linked proofs of deletion.
2. Default-DENY policy DSL — DENY-wins-tie semantics for memory access.
3. Bi-temporal validity — every fact carries `valid_at`, `invalid_at`, `expired_at`.
4. Tamper-evident audit chain — Merkle-linked deletion log, per-tenant, replayable.

**References:**
- CallSphere Right to Be Forgotten: https://callsphere.ai/blog/td30-fw-right-to-be-forgotten-agent-memory-gdpr-ccpa-2026
- Kronvex GDPR-Compliant AI Agents: https://kronvex.io/blog-gdpr-ai-agent-memory
- Astraea Counsel Memory Privacy: https://astraea.law/insights/ai-agent-memory-tool-privacy-compliance
- Notraced Erasure Report: https://notraced.com/articles/right-to-erasure-ai-models
- MemArchitect Paper: https://arxiv.org/pdf/2603.18330
- MOSAIC GitHub: https://github.com/upcomingsimplecoder/mosaic
- GDPR vs EU AI Act: https://www.channel.tel/blog/gdpr-delete-eu-ai-act-keep-memory-compliance

### 2.6 Prometheus Observability for RAG

**Standard metric categories for RAG monitoring (2026 industry practice):**

| Category | Key Metrics | Prometheus Type |
|---|---|---|
| **Embedding** | `embedding_duration_seconds`, `embedding_tokens_total` | Histogram, Counter |
| **Retrieval** | `retriever_query_duration_seconds`, `retriever_docs_returned` | Histogram |
| **Reranking** | `reranker_duration_seconds`, `reranker_score_distribution` | Histogram |
| **LLM Inference** | `llm_inference_duration_seconds`, `llm_tokens_total{type="prompt|completion"}`, `llm_cost_usd_total` | Histogram, Counter |
| **End-to-End** | `rag_query_duration_seconds`, `rag_queries_total{search_type="vector|hybrid"}`, `rag_error_total{reason="timeout|refusal|hallucination"}` | Histogram, Counter |
| **System** | `vector_db_query_duration_seconds`, `context_window_utilization` | Histogram, Gauge |
| **Quality** | `hallucination_score`, `faithfulness_score`, `context_relevance` | Gauge (via LLM-as-Judge eval pipeline) |

**Reference architecture: Prometheus + OpenTelemetry + Grafana + Tempo**
1. Instrument code with OpenTelemetry SDKs (GenAI semantic conventions v1.37+)
2. Export metrics/traces to OTEL Collector → Prometheus (metrics) + Tempo (traces)
3. Build Grafana dashboards for p50/p95/p99 latency, error rates, SLO burn rates
4. Use tail-based sampling to prevent trace sampling from dropping errors
5. Alert via AlertManager → PagerDuty (P1) / Slack (P2-P3)

**Latency budgets for RAG (2026 benchmarks):**
- Embedding: ~45ms
- Vector DB retrieval: ~120ms
- Reranking: ~30ms
- LLM inference: ~2.5s (dominant bottleneck)
- Orchestrator overhead: ~15ms

**References:**
- Prometheus RAG Architecture: https://markaicode.com/architecture/prometheus-rag-architecture/
- NVIDIA RAG Observability: https://docs.nvidia.com/rag/latest/observability.html
- LangChain + Prometheus: https://medium.com/codex/production-observability-for-langchain-with-prometheus-5e45e1a83ef7
- LLM Observability Guide: https://www.glukhov.org/observability/observability-for-llm-systems/
- ValueStreamAI Monitoring Guide: https://valuestreamai.com/blog/ai-monitoring-in-production-guide-2026

### 2.7 Key Takeaways for Guinevere

| Pattern | Adoption Priority | Guinevere-Specific Application |
|---|---|---|
| **Recall@k + MRR** | Immediate | Evaluate memory retrieval quality for user preference recall, conversation history |
| **Golden dataset of 200+ queries** | Immediate | Build from real user sessions in testing; version alongside code |
| **User-namespaced vector stores** | Design-phase | Every user memory in isolated namespace for deterministic deletion |
| **Deletion cascade on root memory** | Design-phase | GDPR Art. 17 compliance; prevent zombie memories from derived summaries |
| **MOSAIC trust primitives** | Evaluate | Deletion receipts + default-DENY for enterprise compliance audits |
| **Pseudonymization pattern** | Design-phase | Resolve GDPR deletion vs EU AI Act audit trail retention conflict |
| **Hallucination detection (Lynx/HHEM)** | Phase 2 | Runtime hallucination scoring for memory recall quality assurance |
| **Faithfulness monitoring** | Phase 2 | Monitor response quality against retrieved memory context |

---

## 3. PostgreSQL/pgvector/TimescaleDB/Alembic Migration Strategy

### 3.1 ERD Governance

**Best practices for ERD governance in production database environments:**

1. **Schema-as-code:** Every schema change is versioned, reviewed, and deployed through CI/CD — never manual.
2. **ERD as source of truth:** Maintain a canonical ERD document (DBML or PlantUML) that's auto-compared against the actual database schema on every PR.
3. **Data dictionary:** Every column should have documented purpose, format constraints, nullable rationale, and PII classification.
4. **Change review template:** Each migration must answer: What changes? Why? What's the rollback plan? What's the data migration path? What's the performance impact?
5. **Ownership matrix:** Every table has a defined owner team and a documented consumer list.

**Tools:**
- **DBML** (dbdiagram.io) — DSL for defining ERDs, diff-capable
- **SchemaSpy** — Auto-generates ERD from live database
- **Alembic `--sql`** — Review SQL before applying
- **pg_dbdiff / apgdiff** — Schema comparison tools

### 3.2 Alembic Naming Conventions & Rollback Strategy

**Naming convention configuration (set in `env.py`):**

```python
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
```

**Benefits of predictable naming:**
- No noisy diffs in autogenerate output
- Named constraints are referenceable in rollbacks
- Consistent schema across environments

**Migration file template:**

```
# Use descriptive revision messages:
alembic revision --autogenerate -m "add_memories_table"
alembic revision --autogenerate -m "add_tenant_rls_policies"
alembic revision --autogenerate -m "backfill_memory_summaries"

# Consider date-prefixed file template for chronological ordering:
# file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(rev)s_%%(slug)s
```

**Rollback strategy tiers:**

| Tier | Pattern | When to Use |
|---|---|---|
| **Schema-only rollback** | Standard `downgrade()` | Adding/removing columns, indexes, constraints |
| **Data-touching rollback** | Backup restore, NOT downgrade() | Backfills, data transforms, column splits |
| **Forward-only** | `downgrade() raises NotImplementedError` | High-traffic production with Expand/Contract discipline |
| **Feature-flag gated** | Rollback via code deploy, not schema | Multi-phase changes where old code path remains wired |

**Critical insight from production teams:** Downgrade is a schema-only safety net, NOT a data recovery mechanism. If you backfilled 8 million rows and then downgrade, you cannot reconstruct the original state. The real safety net is:
1. Database snapshot before destructive migration
2. Expand/Contract pattern with soak periods
3. Feature flags that let you toggle old behavior

### 3.3 Expand-Migrate-Contract Pattern

**The gold standard for zero-downtime schema changes.** Splits a breaking change into small, independently deployable phases:

**Phase 1 — EXPAND:** Add new schema alongside old. Both shapes coexist.
```sql
-- Add nullable column, both old and new code can write
ALTER TABLE users ADD COLUMN full_name VARCHAR(255) NULL;
-- Or add sync trigger to keep both in sync
```

**Phase 2 — MIGRATE:** Backfill + switch reads.
- Backfill in batches, never as single unbounded `UPDATE` (locks entire table)
- Use `WHERE id BETWEEN :start AND :end` with `LIMIT` pagination
- Deploy code that reads from new column, still writes to both
- Feature-flag the read switch with diff-checking before ramping traffic

**Phase 3 — CONTRACT:** Remove old schema.
- After soak period (24h minimum, 1 week recommended)
- Drop old column, remove sync triggers
- Deploy code that only writes to new column

**Production-safe DDL techniques:**
- `ALTER TABLE ... ADD CONSTRAINT ... NOT VALID` — Adds constraint without scanning existing rows (no `ACCESS EXCLUSIVE` lock). Then `VALIDATE CONSTRAINT` in a separate transaction.
- `CREATE INDEX CONCURRENTLY` — Build index without blocking writes. pgvector supports this since v0.6.0.
- `lock_timeout` — Set short timeout on DDL to fail fast rather than block.
- `SET lock_timeout = '5s';` before any production DDL.

**Column rename pattern (4-phase):**
1. Add new column alongside old
2. Create trigger to sync writes between old and new
3. Backfill existing data
4. Deploy code to read from new column
5. Drop trigger and old column

**References:**
- Botmonster Alembic Guide: https://botmonster.com/coding/automate-database-migrations-alembic-sqlalchemy/
- KruN Alembic Best Practices: https://krun.pro/alembic-migrations/
- Palakorn Expand/Contract: https://palakorn.com/blog/zero-downtime-database-migrations/
- Kenin Kujovic Expand/Contract: https://keninkujovic.com/blog/expand-and-contract-migrations
- Zero-downtime with Alembic: https://that.guru/blog/zero-downtime-upgrades-with-alembic-and-sqlalchemy/
- Orchestkit Alembic Branching: https://github.com/yonatangross/orchestkit/blob/main/plugins/ork/skills/database-patterns/rules/alembic-branching.md
- Alembic Naming Docs: https://alembic.sqlalchemy.org/en/latest/naming.html

### 3.4 pgvector: HNSW vs IVFFlat Indexing

**Index type comparison (2026 consensus):**

| Aspect | HNSW | IVFFlat |
|---|---|---|
| **Recall @ 10** | 95-99% | 80-95% (tune `probes`) |
| **Query latency** | Sub-ms to ms | Higher, tunable |
| **Build time** | Slower (graph construction) | Faster (5-6×) |
| **Memory usage** | Higher (graph in RAM) | Lower |
| **Insert cost** | Moderate | Low |
| **Needs data to build?** | No — can build on empty | Yes — needs representative data |
| **Real-time inserts** | Yes (incremental graph) | Degrades — needs periodic rebuild |
| **Default for 2026** | **Yes** | Legacy/workload-specific only |

**HNSW parameter tuning:**
- `m` (connections per node, default 16): Higher = better recall, more memory. Start at 16, benchmark at 24/32.
- `ef_construction` (build quality, default 64): Higher = better graph, slower builds. Use 128-256 for production RAG.
- `ef_search` (query quality, default 40): Higher = better recall, slower queries. Benchmark at 64-100.

**Configuration benchmarks (1M rows, 1536-dim):**

| Configuration | p99 Latency | Recall@10 | Index Size | Build Time |
|---|---|---|---|---|
| No index (seq scan) | 47,000 ms | 1.00 | N/A | N/A |
| HNSW defaults (m=16, ef_construction=64) | 4.2 ms | 0.91 | 450 MB | 45s |
| HNSW tuned (m=24, ef_construction=128) | 3.8 ms | 0.95 | 680 MB | 82s |
| HNSW + halfvec quantization | 3.2 ms | 0.94 | 310 MB | 38s |
| IVFFlat (lists=100) | 8.1 ms | 0.87 | 220 MB | 12s |

**Key pgvector production tunings:**
1. `maintenance_work_mem` = at least 2 GB for HNSW builds over 1M rows
2. `shared_buffers` = ~25% RAM; ensure active chunks fit
3. `max_parallel_maintenance_workers` = available cores for parallel build
4. Use `CREATE INDEX CONCURRENTLY` (pgvector 0.6.0+) for zero-downtime production builds
5. `hnsw.iterative_scan` = `relaxed_order` for most filtered RAG queries (Postgres 17+)
6. Consider `halfvec` quantization (1536→768 dims) to halve index size with negligible recall loss

**References:**
- DigitalOcean pgvector Tuning: https://docs.digitalocean.com/products/vector-databases/postgresql/how-to/index-and-tune/
- dbi pgvector Index Guide: https://www.dbi-services.com/blog/pgvector-a-guide-for-dba-part-2-indexes-update-march-2026/
- dibi8 pgvector 2026: https://dibi8.com/resources/data-science/pgvector-postgres-vector-extension/
- Danube Data pgvector RAG: https://danubedata.ro/blog/pgvector-rag-managed-postgres-2026
- Nerd Level Tech pgvector Tuning: https://nerdleveltech.com/pgvector-hnsw-postgres-18-production-tuning-tutorial
- Philip McClarence Index Selection: https://medium.com/@philmcc/pgvector-index-selection-ivfflat-vs-hnsw-for-postgresql-vector-search-6eff26aaa90c

### 3.5 TimescaleDB Hypertables & Chunking

**Core concept:** A hypertable is a virtual layer on top of real PostgreSQL tables (chunks), each covering a specific time range. Chunks are real tables with real indexes, CHECK constraints, and performance implications.

**Chunk interval selection guide:**

| Data Volume | Recommended Interval | Target Rows/Chunk |
|---|---|---|
| < 1M rows/day | 1 week | ~10M |
| 1-10M rows/day | 1 day | ~10-25M |
| 10-100M rows/day | 6 hours | ~25M |
| > 100M rows/day | 1 hour | ~10-25M |

**Production rule for chunk size:** Each uncompressed chunk should fit in ~25% of available buffer cache.

```
chunk_size_target = shared_buffers / (N × 2)
# where N = number of active hypertables
# factor of 2 accounts for indexes
```

**Memory tuning for TimescaleDB:**
- `shared_buffers` = 25% RAM (standard) + verify active chunks fit
- `effective_cache_size` = 50-75% RAM (planner hint)
- Monitor: if chunk exceeds 25% of `shared_buffers`, reduce `chunk_time_interval`

**Compression policies:**
- `compress_after` should be at least 1-2× chunk interval
- Typical: 7-14 days for observability workloads
- Once compressed, chunks become read-only (UPDATE/DELETE requires decompress — expensive)
- Achieves 90-95% compression ratio

**Retention policies:**
- `add_retention_policy()` — automatically drops chunks older than retention window
- WITHOUT retention, chunk count grows unbounded and query planning degrades
- Always include `WHERE` clause on time column — without it, constraint exclusion can't work

**Query planning overhead:**
- Planner evaluates EVERY chunk's CHECK constraint (linear cost)
- 100 chunks = 100 constraints evaluated; 4,000 chunks = 4,000 evaluated
- Over 50ms planning time → too many chunks → reduce interval or increase retention

**References:**
- TimescaleDB Hypertable Docs: https://docs.timescale.com/use-timescale/latest/hypertables/
- Tiger Data Hypertable Performance: https://www.tigerdata.com/docs/build/performance-optimization/improve-hypertable-performance
- Dev.to Chunk Interval Guide: https://dev.to/philip_mcclarence_2ef9475/choosing-the-right-chunktimeinterval-for-your-workload-2gdp
- TimescaleDB Memory Tuning: https://dev.to/philip_mcclarence_2ef9475/timescaledb-memory-tuning-sharedbuffers-workmem-and-chunk-sizing-3fem
- Query Planning Overhead: https://dev.to/philip_mcclarence_2ef9475/query-planning-overhead-with-many-chunks-and-how-to-fix-it-1n9j
- JusDB TimescaleDB Guide: https://www.jusdb.com/blog/timescaledb-hypertables-continuous-aggregates-guide

### 3.6 Row-Level Security (RLS)

**PostgreSQL RLS** is becoming the default for multi-tenant SaaS in 2026. It moves tenant isolation from application code to the database layer.

**Canonical RLS setup:**
```sql
-- 1. Enable RLS (and FORCE to apply to table owner too)
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE memories FORCE ROW LEVEL SECURITY;

-- 2. Create policy per operation
CREATE POLICY tenant_isolation_select ON memories
    FOR SELECT
    USING (tenant_id = current_setting('app.tenant_id')::uuid);

CREATE POLICY tenant_isolation_insert ON memories
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

CREATE POLICY tenant_isolation_update ON memories
    FOR UPDATE
    USING (tenant_id = current_setting('app.tenant_id')::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

CREATE POLICY tenant_isolation_delete ON memories
    FOR DELETE
    USING (tenant_id = current_setting('app.tenant_id')::uuid);

-- 3. Index tenant_id for performance (composite with query columns)
CREATE INDEX idx_memories_tenant_created ON memories(tenant_id, created_at DESC);
```

**Application middleware pattern (every request):**
```python
# In request middleware, set tenant context
db.execute("SELECT set_config('app.tenant_id', %s, true)", [tenant_id])
# `true` = session-local scope, auto-resets on transaction end
```

**Critical implementation details:**
1. `FORCE ROW LEVEL SECURITY` — Without it, table owner bypasses policies
2. **WITH CHECK** on UPDATE — Prevents tenant from changing `tenant_id` to another tenant
3. **SET LOCAL** (not SET) — With PgBouncer in transaction mode, SET bleeds across tenants; SET LOCAL resets on commit
4. **Composite indexes** — Index on `(tenant_id, query_column)` for index-only scans
5. **Test with non-superuser role** — Superusers bypass RLS; tests running as superuser will never catch broken policies

**Performance overhead:** 5-15% for well-indexed tables. The biggest win: a forgotten `WHERE tenant_id = $1` stops being a data breach.

**RLS vs schema-per-tenant vs separate databases:**

| Model | Isolation Strength | Scale Ceiling | Migration Overhead |
|---|---|---|---|
| RLS (shared schema) | Medium (database-enforced) | Thousands of tenants | Single migration |
| Schema-per-tenant | High (schema-level) | ~500 tenants | Migration per schema |
| Separate databases | Highest | Unlimited | Connection pooler needed |

**Hybrid approach:** RLS for SMB/free tenants, dedicated schema/database for enterprise customers.

**References:**
- PostgreSQL RLS Docs: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- Techbuddies RLS Multi-Tenant: https://www.techbuddies.io/2026/02/04/how-to-implement-postgresql-row-level-security-for-multi-tenant-saas-2/
- AWS Prescriptive Guidance for Multi-Tenant PostgreSQL
- Toolchew Multi-Tenant Patterns: https://toolchew.com/en/deepdive-multi-tenant-postgres-2026/
- Dev.to RLS vs Schema-per-Tenant: https://dev.to/itsjayanth/multi-tenant-postgresql-row-level-security-vs-schema-per-tenant-when-to-use-which-3joe
- QuantLab RLS SaaS: https://quantlabusa.dev/blog/building-multi-tenant-saas-postgres-rls

### 3.7 Field Encryption Patterns

**Encryption layers for database security:**

1. **Transport encryption:** TLS 1.3 for all client-server connections. Mandatory, not optional.
2. **Encryption at rest:** Cloud provider-managed keys (KMS) for EBS/volume encryption + encrypted backups.
3. **Application-level field encryption:** Sensitive PII fields encrypted before writing to database.
   - **pgcrypto** extension for PostgreSQL-native field encryption (`pgp_sym_encrypt`/`pgp_pub_encrypt`)
   - **AES-256-GCM** for authenticated encryption with nonce
   - Keys managed via KMS, fetched at application startup and cached
4. **Crypto-shredding for compliance:** Encrypt user data with user-specific key. Deletion = destroy the key. Data becomes unrecoverable.

**Field encryption patterns:**

```sql
-- Using pgcrypto for symmetric encryption
INSERT INTO users (id, email_encrypted)
VALUES (1, pgp_sym_encrypt('user@example.com', current_setting('app.encryption_key')));

-- Query with decryption
SELECT pgp_sym_decrypt(email_encrypted, current_setting('app.encryption_key'))
FROM users WHERE id = 1;
```

**Search over encrypted fields:**
- **Deterministic encryption** (same plaintext → same ciphertext) enables exact-match searches but leaks frequency information.
- **Searchable encryption indexes** — Trade-off between security and queryability.
- **Blind indexes** — Store a deterministic hash of the field for lookup while keeping the actual value encrypted.

**Key management rules:**
- Never hardcode keys in application code or config files
- Use a KMS (AWS KMS, HashiCorp Vault, Azure Key Vault)
- Rotate keys on a schedule (90-day default, 30-day for high-security)
- Log all key access for audit trails

### 3.8 Migration Test Patterns

**Comprehensive migration testing pyramid (2026 best practices):**

| Test Type | Speed | Tool | What It Catches |
|---|---|---|---|
| **Chain integrity** | < 1s | Alembic CLI | Multiple heads, missing downgrade stubs, wrong `down_revision` |
| **Structural tests** | 1-5s | SQLite + SQLAlchemy | Revision chain order, model/schema sync, naming conventions |
| **Unit tests per migration** | 5-30s | Testcontainers + PostgreSQL | Specific upgrade/downgrade correctness |
| **Integration tests** | 30-120s | Testcontainers + full schema | Data migration correctness, constraint enforcement |
| **Downgrade round-trip** | Varies | Alembic + test DB | All revisions can be upgraded from base to head and downgraded back |
| **Performance tests** | Hours | Production-like data volume | Index build time, lock contention, query plan changes |

**Essential CI/CD migration checks:**
```python
def test_downgrade_all_revisions(db_url):
    """All migrations can be reversed from head to base."""
    # Start from head
    command.upgrade(alembic_cfg, "head")
    # Walk back step by step
    revisions = get_all_revisions(alembic_cfg)
    for _ in revisions:
        command.downgrade(alembic_cfg, "-1")
    # Verify database is at base
```

**Production deployment sequence for migrations:**
1. Run `alembic upgrade head --sql` to review generated SQL
2. Take database snapshot
3. Run `CREATE INDEX CONCURRENTLY` for index adds (non-blocking)
4. Run `ALTER TABLE ... ADD CONSTRAINT ... NOT VALID` for constraint adds
5. Run `VALIDATE CONSTRAINT` in separate transaction
6. For data migrations: batch, throttle, checkpoint
7. Monitor lock contention, replication lag, error rates
8. Keep old path alive for rollback horizon (minimum 24h)

**References:**
- Migration Testing Guide: https://helpmetest.com/blog/alembic-migration-testing/
- Yogesh Kumar Alembic Best Practices: https://medium.com/@ygsh0816/alembic-sqlalchemy-migration-best-practices-that-wont-break-production-09cc2f417715

### 3.9 Key Takeaways for Guinevere

| Pattern | Adoption Priority | Guinevere-Specific Application |
|---|---|---|
| **Alembic naming_convention** | Immediate | Set in `env.py` before first migration; prevents noisy diffs forever |
| **Expand-Migrate-Contract** | Design-phase | All column changes follow this pattern; eliminates downtime risk |
| **pgvector HNSW (default)** | Immediate | Better recall, lower latency than IVFFlat for ~10M memory vectors |
| **halfvec quantization** | Evaluate | Halve index size with ~1% recall loss; good for memory vector store |
| **TimescaleDB hypertables** | Phase 2 | Time-series memory access logs, surveillance data, session traces |
| **RLS with FORCE** | Immediate | Tenant/user memory isolation; database-enforced, not code-reviewed |
| **Crypto-shredding** | Design-phase | User-specific encryption keys; deletion = key destruction |
| **NOT VALID + CONCURRENTLY** | Immediate | Safe constraint/index adds without blocking production writes |
| **Migration round-trip tests** | Immediate | CI check: every revision must upgrade and downgrade cleanly |
| **Schema snapshot before destructive migration** | Immediate | Safety net for data-touching migrations where downgrade can't recover |

---

## 4. References Index

### Prompt Injection & Model Safety
| Resource | URL |
|---|---|
| OWASP LLM Top 10 v2.0 | https://owasp.org/www-project-top-10-for-large-language-model-applications/ |
| OWASP Prompt Injection Cheat Sheet | https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html |
| NIST AI RMF 1.0 | https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf |
| NIST GenAI Profile (600-1) | https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf |
| NIST AI RMF Playbook | https://airc.nist.gov/docs/AI_RMF_Playbook.pdf |
| TokenMix Defense Rankings | https://tokenmix.ai/blog/prompt-injection-defense-techniques-2026 |
| Wraith OWASP Annotated | https://wraith.sh/learn/owasp-top-10-llm-annotated |
| Indirect Injection Defense | https://webemyengineering.com/insights/indirect-prompt-injection-defense-production-agents/ |
| Garak (NVIDIA) | https://github.com/nvidia/garak/ |
| PyRIT (Microsoft) | https://microsoft.github.io/PyRIT/ |
| RAMPART + Clarity | https://www.microsoft.com/en-us/security/blog/2026/05/20/introducing-rampart-and-clarity-open-source-tools-to-bring-safety-into-agent-development-workflow/ |
| AI Red Teaming Tools Comparison | https://beyondscale.tech/blog/ai-red-teaming-tools-comparison-2026 |

### Memory Recall Evaluation
| Resource | URL |
|---|---|
| TypeGraph RAG Evaluation | https://typegraph.ai/blog/rag-retrieval-evaluation-recall-precision-mrr |
| Redis RAG Metrics | https://redis.io/blog/rag-metrics/ |
| UDCG Paper (EACL 2026) | https://aclanthology.org/2026.eacl-long.391.pdf |
| Digital Applied RAG KPIs | https://www.digitalapplied.com/blog/rag-system-metrics-recall-precision-faithfulness-2026 |
| Agentmelt RAG Evaluation | https://agentmelt.com/blog/ai-agent-rag-evaluation-guide/ |
| RAGTruth (ACL 2024) | https://aclanthology.org/2024.acl-long.585.pdf |
| Bi'an Hallucination Benchmark | https://arxiv.org/html/2502.19209 |
| Lynx Hallucination Detection | https://arxiv.org/pdf/2407.08488 |
| MemArchitect Governance | https://arxiv.org/pdf/2603.18330 |
| MOSAIC Trust Primitives | https://github.com/upcomingsimplecoder/mosaic |
| CallSphere Right to Be Forgotten | https://callsphere.ai/blog/td30-fw-right-to-be-forgotten-agent-memory-gdpr-ccpa-2026 |
| Notraced Erasure Report | https://notraced.com/articles/right-to-erasure-ai-models |
| Prometheus RAG Architecture | https://markaicode.com/architecture/prometheus-rag-architecture/ |
| NVIDIA RAG Observability | https://docs.nvidia.com/rag/latest/observability.html |

### PostgreSQL/pgvector/TimescaleDB/Alembic
| Resource | URL |
|---|---|
| PostgreSQL RLS Docs | https://www.postgresql.org/docs/current/ddl-rowsecurity.html |
| DigitalOcean pgvector Tuning | https://docs.digitalocean.com/products/vector-databases/postgresql/how-to/index-and-tune/ |
| dbi pgvector Index Guide | https://www.dbi-services.com/blog/pgvector-a-guide-for-dba-part-2-indexes-update-march-2026/ |
| dibi8 pgvector 2026 Guide | https://dibi8.com/resources/data-science/pgvector-postgres-vector-extension/ |
| Danube Data pgvector RAG | https://danubedata.ro/blog/pgvector-rag-managed-postgres-2026 |
| Nerd Level Tech pgvector Tuning | https://nerdleveltech.com/pgvector-hnsw-postgres-18-production-tuning-tutorial |
| TimescaleDB Hypertable Docs | https://docs.timescale.com/use-timescale/latest/hypertables/ |
| TimescaleDB Chunk Interval Guide | https://dev.to/philip_mcclarence_2ef9475/choosing-the-right-chunktimeinterval-for-your-workload-2gdp |
| TimescaleDB Memory Tuning | https://dev.to/philip_mcclarence_2ef9475/timescaledb-memory-tuning-sharedbuffers-workmem-and-chunk-sizing-3fem |
| Alembic Naming Docs | https://alembic.sqlalchemy.org/en/latest/naming.html |
| Alembic Migration Testing | https://helpmetest.com/blog/alembic-migration-testing/ |
| Expand/Contract Playbook | https://palakorn.com/blog/zero-downtime-database-migrations/ |
| KruN Alembic Best Practices | https://krun.pro/alembic-migrations/ |
| Toolchew Multi-Tenant Patterns | https://toolchew.com/en/deepdive-multi-tenant-postgres-2026/ |
| Orchestkit Alembic Branching | https://github.com/yonatangross/orchestkit/blob/main/plugins/ork/skills/database-patterns/rules/alembic-branching.md |

---

*Report generated: 2026-05-30 | Author: Guinevere (THE LIBRARIAN) | This report is an external reference compilation. Recommendations should be validated against Project Guinevere's specific constraints before adoption.*
