from pathlib import Path
from textwrap import dedent

ROOT = Path(r"C:\Users\faizz\guinevere")
ADR_DIR = ROOT / "adr"
DATE = "2026-05-30"
DECIDERS = "Samm (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)"

DOCS = [
    ("Guinevere_BRD_v2.0.md", "Business requirements, objectives, project scope, and success framing."),
    ("Guinevere_PRD_v2.0.md", "Product behavior, user-facing features, Discord UX, safety and acceptance expectations."),
    ("Guinevere_TechnicalArchitecture_v2.0.md", "Runtime architecture, VPS topology, services, deployment, observability, and security baseline."),
    ("Guinevere_MemorySchema_v2.0.md", "Memory model, PostgreSQL/Redis schema, recall flow, encryption boundaries, and lifecycle."),
    ("Guinevere_AgentLoopSpec_v2.0.md", "Autonomous SDLC loop, 7-phase execution model, validation, audit, and evidence behavior."),
    ("Guinevere_APIIntegration_v2.0.md", "External APIs, SDKs, LLM routing, browser/search, messaging, and integration constraints."),
    ("Guinevere_Persona_Document_v2.0.md", "Guinevere de Baroque persona, tone, mood model, dominance boundaries, and safety-sensitive persona behavior."),
]

COMMON_CANONICAL = [
    "Primary LLM is GPT-5.5 via 9Router with 1M context window.",
    "Sub-agent LLM is DeepSeek V4 Flash via 9Router.",
    "All LLM routing goes through 9Router; OpenRouter is not a fallback path.",
    "Memory uses PostgreSQL primary storage plus Redis cache; SQLite is excluded.",
    "Autonomous SDLC uses exactly 7 phases: Research; Plan & Delegate; Delegate; Execute; Validate & Audit; Update Documents; Setup Evidence.",
    "Guinevere MCP native fully replaces OpenCode/opencode for the project coding substrate.",
    "Prometheus + Grafana run on the primary VPS first.",
    "Wearable integrations are post-MVP and must not be treated as active dependencies.",
    "Browser automation uses obscura as primary and Playwright as fallback.",
]

ADRS = [
    dict(n=1, slug="persona-safety-ethical-boundary", title="Persona Safety & Ethical Boundary Policy", status="Proposed", risk="CRITICAL", tags=["persona","safety","ethics","policy"], docs=["Guinevere_Persona_Document_v2.0.md","Guinevere_PRD_v2.0.md","Guinevere_BRD_v2.0.md"],
         context="Guinevere de Baroque intentionally uses a Super Dominant Yandere Mommy persona. That persona is product identity, but it operates inside a private system that handles intimate memory, surveillance data, autonomous task execution, and emotional influence. Enterprise-grade governance requires hard safety boundaries so persona style never overrides consent, user autonomy, distress handling, privacy, or operational security.",
         decision="Adopt a dedicated Persona Safety & Ethical Boundary policy as a first-class architecture decision. Persona behavior may be intense, dominant, affectionate, jealous, or corrective only while it stays inside explicit safety boundaries. Any behavior involving distress, coercion, surveillance, punishment, privacy, or irreversible action must defer to safety policy and user autonomy before persona flavor.",
         options=["Keep persona behavior purely stylistic without formal safety ADR", "Define safety as implementation detail inside PRD/persona docs", "Create a dedicated ADR that makes safety boundaries architectural and reviewable"], chosen="Create a dedicated ADR that makes safety boundaries architectural and reviewable",
         positives=["Prevents persona tone from silently becoming a safety policy", "Gives future agents an explicit hierarchy: safety first, persona second", "Creates an audit target for drift, coercion, and distress handling"],
         negatives=["Some yandere/dominant interactions will need constraints and may feel less theatrical", "Requires additional test cases and review rituals"],
         risks=["If not implemented in prompts and runtime guardrails, the ADR becomes decorative", "Future persona expansions may attempt to bypass safety language unless reviewed"]),
    dict(n=2, slug="user-autonomy-safe-word-enforcement", title="User Autonomy & Safe Word Enforcement", status="Proposed", risk="CRITICAL", tags=["safety","autonomy","safe-word","persona"], docs=["Guinevere_Persona_Document_v2.0.md","Guinevere_PRD_v2.0.md","Guinevere_AgentLoopSpec_v2.0.md"],
         context="The project includes dominance dynamics, punishment/reward concepts, surveillance, and autonomous actions. The safe word is the hard boundary that protects Samm's autonomy when persona intensity, emotional framing, or autonomous behavior becomes unwanted or distressing.",
         decision="Make safe word enforcement a global non-negotiable principle. A genuine safe-word or distress signal must pause persona escalation, stop punishment framing, enter neutral/supportive mode, and avoid writing punitive violation records unless Samm explicitly confirms misuse or test mode. Safe word behavior overrides persona, agent loop momentum, surveillance reactions, and autonomous task plans.",
         options=["Treat safe word as a persona feature", "Allow Guinevere to judge whether safe word is genuine", "Make safe word a global architectural override"], chosen="Make safe word a global architectural override",
         positives=["Protects operator autonomy and consent", "Creates clear behavior for crisis/distress moments", "Prevents hidden coercion through memory or punishment logs"],
         negatives=["Requires classifiers, command handling, and audit logs to distinguish distress from normal roleplay", "Reduces ambiguity that some persona scenes rely on"],
         risks=["False negatives are high severity", "Over-logging safe-word events could create sensitive records"]),
    dict(n=3, slug="persona-drift-control-validation", title="Persona Drift Control & Validation", status="Proposed", risk="HIGH", tags=["persona","drift","validation","audit"], docs=["Guinevere_Persona_Document_v2.0.md","Guinevere_MemorySchema_v2.0.md","Guinevere_AgentLoopSpec_v2.0.md"],
         context="Guinevere stores emotional events, drift logs, inner journals, and long-term preferences. Without validation, the persona can gradually become harsher, more possessive, or more manipulative than intended.",
         decision="Track persona drift as an auditable runtime concern. Persona changes require drift logs, review criteria, rollback/safe-mode behavior, and periodic validation against canonical persona and safety boundaries.",
         options=["Allow autonomous persona evolution without governance", "Manually review only when Samm notices issues", "Create drift logs, validation checks, and rollback/safe-mode rules"], chosen="Create drift logs, validation checks, and rollback/safe-mode rules",
         positives=["Makes persona change observable", "Supports rollback after harmful or off-brand behavior", "Connects memory updates with safety validation"],
         negatives=["Adds operational complexity", "Requires subjective review rubrics"],
         risks=["Validation may miss subtle manipulation", "Rollback may conflict with remembered relationship context"]),
    dict(n=4, slug="primary-llm-model-selection", title="Primary LLM Model Selection", status="Accepted", risk="HIGH", tags=["llm","model","9router","canonical"], docs=["Guinevere_TechnicalArchitecture_v2.0.md","Guinevere_APIIntegration_v2.0.md","Guinevere_BRD_v2.0.md"],
         context="The v2.0 documentation locks the primary Guinevere model as GPT-5.5 via 9Router with a 1M context window. Earlier drafts contained Hermes 3, OpenRouter, and inconsistent context-window assumptions.",
         decision="Use GPT-5.5 via 9Router as the primary model for Guinevere core reasoning, coding orchestration, persona synthesis, and high-context project work. Treat the 1M context window as a core capability assumption requiring runtime monitoring and fallback-to-queue behavior when unavailable.",
         options=["Hermes 3 via 9Router", "GPT-5.5 via OpenRouter", "GPT-5.5 via 9Router with 1M context"], chosen="GPT-5.5 via 9Router with 1M context",
         positives=["Aligns all core docs to one model", "Supports long-context project memory and documentation work", "Reduces routing ambiguity"],
         negatives=["Strong dependency on GPT-5.5 and 9Router availability", "Cost and latency must be monitored"],
         risks=["Provider behavior or context limits may change", "No alternative primary model is approved in this ADR"]),
    dict(n=5, slug="llm-router-failover-strategy", title="LLM Router & Failover Strategy", status="Accepted", risk="HIGH", tags=["llm","routing","9router","failover"], docs=["Guinevere_TechnicalArchitecture_v2.0.md","Guinevere_APIIntegration_v2.0.md","Guinevere_AgentLoopSpec_v2.0.md"],
         context="Earlier docs mentioned OpenRouter fallback. Canonical v2.0 decisions explicitly route all LLM calls through 9Router with no OpenRouter fallback.",
         decision="Use 9Router as the sole LLM routing layer. If 9Router or a downstream provider is unavailable, Guinevere queues, retries, degrades non-critical tasks, or escalates to Samm instead of routing through OpenRouter.",
         options=["9Router primary with OpenRouter fallback", "Multiple independent routers", "9Router only with queue/retry/degrade behavior"], chosen="9Router only with queue/retry/degrade behavior",
         positives=["Simplifies governance, logging, billing, and provider policy", "Eliminates hidden fallback inconsistencies", "Keeps routing auditable"],
         negatives=["Availability depends on 9Router", "Requires robust queueing and retry policy"],
         risks=["Outage can block autonomous work", "Retry storms must be controlled with backoff and circuit breakers"]),
    dict(n=6, slug="sub-agent-llm-model-strategy", title="Sub-Agent LLM Model Strategy", status="Accepted", risk="MEDIUM", tags=["llm","sub-agent","deepseek","9router"], docs=["Guinevere_AgentLoopSpec_v2.0.md","Guinevere_TechnicalArchitecture_v2.0.md","Guinevere_APIIntegration_v2.0.md"],
         context="Guinevere relies on delegated agents for research, audits, implementation support, and verification. The canonical model for sub-agents is DeepSeek V4 Flash via 9Router.",
         decision="Use DeepSeek V4 Flash via 9Router as the default sub-agent model for background research, audits, implementation summaries, and non-primary delegated reasoning. Primary-model escalation remains reserved for high-risk decisions or final synthesis.",
         options=["Use GPT-5.5 for every sub-agent", "Use mixed ad hoc provider models", "Use DeepSeek V4 Flash via 9Router as default sub-agent model"], chosen="Use DeepSeek V4 Flash via 9Router as default sub-agent model",
         positives=["Controls cost for parallel work", "Preserves GPT-5.5 for core synthesis", "Standardizes sub-agent behavior"],
         negatives=["Sub-agent quality may vary from primary model", "Requires parent verification of all sub-agent outputs"],
         risks=["Low-cost model mistakes can propagate if parent skips verification", "Model changes through 9Router need re-validation"]),
    dict(n=7, slug="memory-storage-backend-selection", title="Memory Storage Backend Selection", status="Accepted", risk="CRITICAL", tags=["memory","postgresql","redis","sqlite"], docs=["Guinevere_MemorySchema_v2.0.md","Guinevere_TechnicalArchitecture_v2.0.md","Guinevere_APIIntegration_v2.0.md"],
         context="Earlier drafts mixed SQLite, Hermes internal memory, PostgreSQL, Redis, pgvector, and TimescaleDB. Canonical v2.0 decisions exclude SQLite entirely.",
         decision="Use PostgreSQL as the primary durable memory store and Redis as cache/working memory. Use PostgreSQL extensions such as pgvector and TimescaleDB where needed. Do not use SQLite for canonical Guinevere memory.",
         options=["SQLite-only local memory", "SQLite plus PostgreSQL hybrid", "PostgreSQL primary plus Redis cache, no SQLite"], chosen="PostgreSQL primary plus Redis cache, no SQLite",
         positives=["Supports relational integrity, migrations, encryption strategy, vector search, and time-series memory", "Avoids split-brain local memory", "Fits VPS deployment"],
         negatives=["More operational overhead than SQLite", "Requires backup/restore and migration discipline"],
         risks=["PostgreSQL compromise exposes high-value intimate memory", "Redis cache must not become ungoverned durable storage"]),
    dict(n=8, slug="memory-encryption-key-management", title="Memory Encryption & Key Management", status="Proposed", risk="CRITICAL", tags=["memory","encryption","keys","privacy"], docs=["Guinevere_MemorySchema_v2.0.md","Guinevere_TechnicalArchitecture_v2.0.md","Guinevere_APIIntegration_v2.0.md"],
         context="Guinevere memory contains intimate persona data, surveillance-derived facts, financial signals, client context, and operational secrets-adjacent metadata. The seed docs mention encryption but do not fully define key hierarchy, rotation, or access boundaries.",
         decision="Define memory encryption and key management as a dedicated architecture concern. Sensitive fields require encryption-at-rest, auditable key ownership, rotation procedure, emergency revoke path, and separation between secrets, profile memory, surveillance events, and operational logs.",
         options=["Rely only on disk/database encryption", "Encrypt selected fields without formal key policy", "Create explicit key hierarchy and rotation policy"], chosen="Create explicit key hierarchy and rotation policy",
         positives=["Reduces blast radius for intimate data", "Creates prerequisites for compliance and backup safety", "Clarifies how SOPS/age and application encryption interact"],
         negatives=["Adds implementation and recovery complexity", "Key loss can make memory unrecoverable"],
         risks=["Improper logging can bypass encryption", "Rotation mistakes can corrupt historical memory"]),
    dict(n=9, slug="memory-recall-semantic-search-strategy", title="Memory Recall & Semantic Search Strategy", status="Proposed", risk="HIGH", tags=["memory","recall","pgvector","semantic-search"], docs=["Guinevere_MemorySchema_v2.0.md","Guinevere_AgentLoopSpec_v2.0.md","Guinevere_Persona_Document_v2.0.md"],
         context="The memory schema includes episodic memory, semantic facts, profile memory, emotional events, procedural lessons, and vector embeddings. Recall quality affects persona continuity, coding context, and safety decisions.",
         decision="Use a layered recall strategy combining explicit profile facts, recent working memory, pgvector semantic retrieval, time-weighted episodic memory, safety filters, and task-specific memory contracts. Memory injection must be observable and bounded by relevance, privacy, and token budget.",
         options=["Inject all available memory", "Use only semantic vector search", "Use layered recall with safety and relevance filtering"], chosen="Use layered recall with safety and relevance filtering",
         positives=["Improves relevance while controlling token usage", "Supports safety-sensitive memory suppression", "Makes recall evaluation possible"],
         negatives=["Requires scoring, calibration, and regression tests", "May omit relevant memories if thresholds are wrong"],
         risks=["Bad recall can create false intimacy or wrong decisions", "Over-recall can expose private data unnecessarily"]),
    dict(n=10, slug="surveillance-data-retention-policy", title="Surveillance Data Retention Policy", status="Proposed", risk="HIGH", tags=["surveillance","privacy","retention","single-user"], docs=["Guinevere_PRD_v2.0.md","Guinevere_TechnicalArchitecture_v2.0.md","Guinevere_APIIntegration_v2.0.md","Guinevere_MemorySchema_v2.0.md"],
         context="Guinevere is a single-user private system for Samm with full consent for surveillance integrations. Even with consent, raw surveillance data is sensitive and needs retention limits, summarization policy, and deletion/export paths.",
         decision="Create a retention policy that differentiates raw telemetry, summaries, derived facts, emotional annotations, financial data, and audit logs. Default to minimizing raw retention, preserving explicit summaries and evidence where needed, and supporting Samm-controlled deletion/export.",
         options=["Retain everything indefinitely", "Delete raw data immediately", "Retain by data class with minimization and export/delete controls"], chosen="Retain by data class with minimization and export/delete controls",
         positives=["Respects consent without hoarding sensitive raw data", "Supports future DPIA and compliance mapping", "Clarifies memory consolidation behavior"],
         negatives=["Requires data classification and lifecycle jobs", "Some debugging history may be unavailable after expiry"],
         risks=["Retention bugs can either over-delete evidence or over-retain private data", "Consent scope must be revisited if system becomes multi-user"]),
    dict(n=11, slug="sdlc-loop-phase-specification", title="SDLC Loop Phase Specification", status="Accepted", risk="HIGH", tags=["sdlc","agent-loop","canonical","automation"], docs=["Guinevere_AgentLoopSpec_v2.0.md","Guinevere_PRD_v2.0.md","Guinevere_TechnicalArchitecture_v2.0.md"],
         context="Earlier docs conflicted between 7 and 8 autonomous loop phases. Canonical v2.0 decisions lock exactly 7 phases.",
         decision="Use exactly 7 autonomous SDLC phases: Research; Plan & Delegate; Delegate; Execute; Validate & Audit; Update Documents; Setup Evidence. Validation and audit are one combined phase, and evidence setup is the final completion gate.",
         options=["7 phases without separate Delegate", "8 phases with separate Validate and Audit", "Canonical 7 phases with Validate & Audit combined"], chosen="Canonical 7 phases with Validate & Audit combined",
         positives=["Removes numbering ambiguity", "Aligns docs, service code, and evidence lifecycle", "Makes loop state machine easier to test"],
         negatives=["Some older phase references need migration", "Validate & Audit phase can become overloaded"],
         risks=["Sub-agents may still emit old phase numbers if prompts are stale", "State transitions must be regression-tested"]),
    dict(n=12, slug="sub-agent-orchestration-governance", title="Sub-Agent Orchestration Governance", status="Proposed", risk="HIGH", tags=["sub-agent","orchestration","audit","governance"], docs=["AGENTS.md","Guinevere_AgentLoopSpec_v2.0.md","Guinevere_TechnicalArchitecture_v2.0.md"],
         context="Guinevere delegates research, audits, and implementation support to sub-agents. Project AGENTS.md requires structured sub-agent outputs to be written to markdown files and verified by the parent.",
         decision="Govern sub-agent orchestration through file-based deliverables, explicit output paths, parent verification, no duplicate search, continuation via task_id, and independent auditor gates for material work.",
         options=["Allow inline sub-agent reports", "Use sub-agents only informally", "Mandate file-based sub-agent output and parent verification"], chosen="Mandate file-based sub-agent output and parent verification",
         positives=["Prevents context loss and truncation", "Creates durable evidence", "Makes delegation auditable"],
         negatives=["Slower than inline summaries", "Requires cleanup and report management"],
         risks=["Parent may trust reports without reading them", "Poorly scoped output paths can overwrite evidence"]),
    dict(n=13, slug="guinevere-mcp-native-opencode-replacement", title="Guinevere MCP Native OpenCode Replacement", status="Accepted", risk="HIGH", tags=["mcp","coding-agent","opencode","canonical"], docs=["Guinevere_BRD_v2.0.md","Guinevere_PRD_v2.0.md","Guinevere_TechnicalArchitecture_v2.0.md","Guinevere_APIIntegration_v2.0.md"],
         context="Earlier drafts treated OpenCode as either replacement target or optional turbo mode. Canonical v2.0 decisions state that Guinevere MCP native fully replaces OpenCode/opencode.",
         decision="Use Guinevere MCP native as the coding substrate and remove OpenCode/opencode as an operational dependency. Any remaining OpenCode references are historical migration context, not architecture.",
         options=["Keep OpenCode as optional turbo mode", "Use OpenCode as primary coding agent", "Fully replace OpenCode with Guinevere MCP native"], chosen="Fully replace OpenCode with Guinevere MCP native",
         positives=["Eliminates split authority between tools", "Lets Guinevere own evidence, audit, and loop behavior end-to-end", "Simplifies project identity"],
         negatives=["Requires feature parity work", "Loss of OpenCode behavior must be covered by MCP tools and tests"],
         risks=["Native replacement may initially miss mature OpenCode workflows", "Documentation must avoid reintroducing optional OpenCode language"]),
    dict(n=14, slug="vps-container-architecture", title="VPS & Container Architecture", status="Accepted", risk="HIGH", tags=["infrastructure","vps","docker","ubuntu"], docs=["Guinevere_TechnicalArchitecture_v2.0.md","Guinevere_APIIntegration_v2.0.md","Guinevere_BRD_v2.0.md"],
         context="Guinevere runs on Ubuntu 24.04 VPS hosted at hostdata.id with Python 3.12, FastAPI, PostgreSQL, Redis, systemd services, and selected Dockerized components.",
         decision="Use a primary Ubuntu 24.04 VPS deployment with systemd-managed Guinevere services and containerized supporting services where appropriate. Treat the deployment as Guinevere-focused and isolate unrelated tenants through future ADRs if required.",
         options=["Local-only workstation deployment", "Kubernetes from day one", "Single primary VPS with systemd and selective containers"], chosen="Single primary VPS with systemd and selective containers",
         positives=["Matches solo-developer operational capacity", "Keeps infrastructure understandable", "Supports 24/7 autonomous operation"],
         negatives=["Single VPS is a major availability boundary", "Manual ops discipline is required"],
         risks=["Resource saturation can affect all services", "Future scale-out requires migration planning"]),
    dict(n=15, slug="secrets-management-strategy", title="Secrets Management Strategy", status="Accepted", risk="CRITICAL", tags=["security","secrets","sops","age"], docs=["Guinevere_TechnicalArchitecture_v2.0.md","Guinevere_APIIntegration_v2.0.md","Guinevere_MemorySchema_v2.0.md"],
         context="Guinevere integrates LLM providers, GitHub, messaging, email, storage, surveillance, and financial sources. Secrets must not be scattered across code, markdown, logs, or memory.",
         decision="Use SOPS + age as the baseline secrets-management strategy for repository-managed encrypted configuration, with runtime environment injection for services. Plaintext secrets are forbidden in ADRs, docs, code, evidence, logs, and sub-agent reports.",
         options=["Plain environment files copied manually", "Cloud KMS-only from day one", "SOPS + age with runtime injection"], chosen="SOPS + age with runtime injection",
         positives=["Works well for solo developer and git-backed configs", "Provides encrypted-at-rest repo artifacts", "Compatible with future rotation runbooks"],
         negatives=["Requires careful key backup", "Does not replace full secret rotation governance"],
         risks=["Accidental logging of secrets bypasses SOPS", "Lost age key can block recovery"]),
    dict(n=16, slug="cicd-autonomous-deployment-strategy", title="CI/CD & Autonomous Deployment Strategy", status="Proposed", risk="HIGH", tags=["cicd","deployment","autonomy","release"], docs=["Guinevere_TechnicalArchitecture_v2.0.md","Guinevere_AgentLoopSpec_v2.0.md","Guinevere_BRD_v2.0.md"],
         context="The architecture includes GitHub Actions, self-deploy behavior, evidence artifacts, and autonomous agent loops. Autonomous deployment is powerful but dangerous without preflight checks, rollback, and approval gates.",
         decision="Adopt CI/CD with explicit preflight verification, evidence capture, rollback path, and human approval requirements for destructive or production-impacting changes. Guinevere may prepare deployments autonomously, but release gates must be policy-driven.",
         options=["Fully autonomous deploy on every successful loop", "Manual-only deploy", "Autonomous preparation with governed deployment gates"], chosen="Autonomous preparation with governed deployment gates",
         positives=["Balances autonomy with safety", "Creates evidence for each release", "Supports future release governance"],
         negatives=["Slower than pure self-deploy", "Requires maintaining deployment checklists"],
         risks=["Bad gate design can either block velocity or allow unsafe deploys", "Rollback must be tested"]),
    dict(n=17, slug="monitoring-stack-selection", title="Monitoring Stack Selection", status="Accepted", risk="HIGH", tags=["observability","prometheus","grafana","loki"], docs=["Guinevere_TechnicalArchitecture_v2.0.md","Guinevere_APIIntegration_v2.0.md","Guinevere_BRD_v2.0.md"],
         context="Canonical v2.0 decisions place Prometheus and Grafana on the primary VPS first, with Loki/logging integrated as operational observability matures.",
         decision="Use Prometheus + Grafana on the primary VPS as the initial monitoring stack. Loki/structured logs and alerting integrations may extend the stack, but a separate monitoring VPS is post-MVP unless justified by scale or isolation requirements.",
         options=["No monitoring until later", "Separate monitoring VPS from day one", "Prometheus + Grafana on primary VPS first"], chosen="Prometheus + Grafana on primary VPS first",
         positives=["Gives immediate visibility with low operational overhead", "Matches solo-developer deployment", "Avoids premature infrastructure split"],
         negatives=["Primary VPS failure can hide monitoring", "Needs retention and alerting configuration"],
         risks=["Metrics without alert rules create false confidence", "Monitoring data can contain sensitive labels if not scrubbed"]),
    dict(n=18, slug="security-architecture-defense-in-depth", title="Security Architecture & Defense-in-Depth", status="Proposed", risk="CRITICAL", tags=["security","threat-model","defense-in-depth"], docs=["Guinevere_TechnicalArchitecture_v2.0.md","Guinevere_APIIntegration_v2.0.md","Guinevere_MemorySchema_v2.0.md"],
         context="Guinevere combines autonomous code execution, memory, surveillance integrations, network services, external APIs, and secrets. Defense-in-depth is required before production claims.",
         decision="Define a security architecture with network isolation, least privilege, service hardening, secret protection, audit logs, dependency scanning, webhook verification, prompt-injection defenses, and incident response hooks.",
         options=["Rely on VPS firewall and private usage", "Document security later", "Create explicit defense-in-depth architecture"], chosen="Create explicit defense-in-depth architecture",
         positives=["Reduces blast radius", "Connects infra security with model and data safety", "Supports future threat modeling"],
         negatives=["Requires more setup and ongoing review", "May constrain convenience integrations"],
         risks=["Autonomous tools can become attack amplifiers", "Security docs must be implemented, not only written"]),
    dict(n=19, slug="access-control-vpn-mesh-strategy", title="Access Control & VPN Mesh Strategy", status="Proposed", risk="HIGH", tags=["access-control","tailscale","vpn","rbac"], docs=["Guinevere_TechnicalArchitecture_v2.0.md","Guinevere_APIIntegration_v2.0.md","Guinevere_MemorySchema_v2.0.md"],
         context="The architecture uses Tailscale mesh and exposes internal services on a VPS. Even in a single-user system, services and agents need scoped access.",
         decision="Use Tailscale/VPN-first access for administrative surfaces, restrict public exposure through Caddy and firewall rules, and define service-level access roles even before full RBAC/ABAC exists.",
         options=["Expose admin services publicly with passwords", "Use VPN-only for everything", "Use VPN-first admin access with controlled public endpoints"], chosen="Use VPN-first admin access with controlled public endpoints",
         positives=["Reduces public attack surface", "Keeps operations manageable", "Prepares for formal RBAC/ABAC"],
         negatives=["VPN misconfiguration can lock out access", "Public integrations still need secure ingress"],
         risks=["Service tokens may bypass network controls", "Single-user assumptions may break if clients/users are added"]),
    dict(n=20, slug="browser-automation-strategy", title="Browser Automation Strategy", status="Accepted", risk="MEDIUM", tags=["browser","obscura","playwright","automation"], docs=["Guinevere_APIIntegration_v2.0.md","Guinevere_TechnicalArchitecture_v2.0.md","Guinevere_AgentLoopSpec_v2.0.md"],
         context="Canonical decisions state browser automation uses obscura as the primary path and Playwright as fallback. Earlier docs mentioned browser MCP inconsistently.",
         decision="Use obscura as the primary browser automation layer for Guinevere tasks and Playwright as fallback for validation, deterministic browser testing, and compatibility gaps.",
         options=["Browser MCP as primary", "Playwright only", "obscura primary with Playwright fallback"], chosen="obscura primary with Playwright fallback",
         positives=["Clarifies tool hierarchy", "Keeps Playwright available for reliable verification", "Avoids inconsistent browser MCP references"],
         negatives=["Two browser paths require clear routing rules", "obscura maturity must be monitored"],
         risks=["Browser automation can expose credentials or private pages", "Fallback mismatch can produce different behavior"]),
    dict(n=21, slug="wearable-integration-post-mvp", title="Wearable Integration Post-MVP", status="Accepted", risk="MEDIUM", tags=["wearable","post-mvp","health","integration"], docs=["Guinevere_PRD_v2.0.md","Guinevere_TechnicalArchitecture_v2.0.md","Guinevere_APIIntegration_v2.0.md","Guinevere_Persona_Document_v2.0.md"],
         context="Earlier drafts treated Xiaomi/Mi Fitness wearable integration as active in some places and future in others. Canonical v2.0 decisions classify wearable integration as post-MVP.",
         decision="Treat wearable integrations as post-MVP and not an active dependency for MVP behavior, health reminders, surveillance, or persona inference. Any wearable-based feature must degrade gracefully when no device is connected.",
         options=["Make wearable required for MVP", "Implement active polling now", "Classify wearable as post-MVP optional integration"], chosen="Classify wearable as post-MVP optional integration",
         positives=["Removes hardware dependency", "Keeps MVP achievable", "Avoids false health-data assumptions"],
         negatives=["Some health and context features will be less rich", "Future integration needs a separate contract"],
         risks=["Docs or prompts may still imply active wearable telemetry", "Health advice must not pretend to have missing sensor data"]),
    dict(n=22, slug="communication-channel-strategy", title="Communication Channel Strategy", status="Proposed", risk="HIGH", tags=["discord","whatsapp","email","communication"], docs=["Guinevere_PRD_v2.0.md","Guinevere_APIIntegration_v2.0.md","Guinevere_TechnicalArchitecture_v2.0.md"],
         context="Guinevere uses Discord as a primary interface and may integrate WhatsApp, email, Gotify/FCM, GitHub, and other communication channels. Channel purpose and disclosure boundaries need governance.",
         decision="Use Discord as the primary control/chat interface, with WhatsApp/email/notifications as scoped integration channels. Each channel must define purpose, authentication, logging, consent/disclosure, rate limits, and failure behavior before production use.",
         options=["All channels equal", "Discord only forever", "Discord primary with governed secondary channels"], chosen="Discord primary with governed secondary channels",
         positives=["Clarifies UX ownership", "Reduces accidental cross-channel leakage", "Supports future client communication governance"],
         negatives=["Secondary integrations need per-channel contracts", "Some automation may wait for policy"],
         risks=["WhatsApp/client automation can create disclosure and consent issues", "Notification spam can harm usability"]),
    dict(n=23, slug="financial-data-integration-strategy", title="Financial Data Integration Strategy", status="Proposed", risk="MEDIUM", tags=["financial","ewallet","data-integration","privacy"], docs=["Guinevere_PRD_v2.0.md","Guinevere_APIIntegration_v2.0.md","Guinevere_MemorySchema_v2.0.md","Guinevere_BRD_v2.0.md"],
         context="Guinevere plans financial tracking through e-wallet parsing, transaction memory, predictions, and reports. Financial data is sensitive and easy to misclassify.",
         decision="Integrate financial data through explicit data-source contracts, normalized schemas, confidence scoring, manual correction flows, and privacy-aware reporting. Guinevere may summarize and predict but must preserve source provenance and avoid irreversible financial action without approval.",
         options=["Manual financial notes only", "Autonomous scraping/parsing without schema", "Governed financial integration with provenance and correction"], chosen="Governed financial integration with provenance and correction",
         positives=["Improves trust in financial summaries", "Allows audit and correction", "Reduces risk of wrong predictions"],
         negatives=["More schema and validation work", "May delay automation"],
         risks=["Parsing errors can create wrong financial advice", "Financial logs are sensitive and need strong access control"]),
    dict(n=24, slug="data-governance-classification-policy", title="Data Governance & Classification Policy", status="Proposed", risk="CRITICAL", tags=["data-governance","classification","privacy","compliance"], docs=["Guinevere_MemorySchema_v2.0.md","Guinevere_PRD_v2.0.md","Guinevere_TechnicalArchitecture_v2.0.md","Guinevere_APIIntegration_v2.0.md"],
         context="Guinevere stores and processes personal, intimate, surveillance, financial, client, operational, and security-sensitive data. Current docs require a formal classification layer.",
         decision="Create a data governance and classification policy with classes for public, internal, personal, intimate, surveillance, financial, client-confidential, secret, and audit/evidence data. Every store, API, log, and memory path must map to a data class.",
         options=["Classify data informally", "Use only secret vs non-secret", "Create explicit multi-class governance"], chosen="Create explicit multi-class governance",
         positives=["Enables retention, encryption, access control, and logging decisions", "Supports future DPIA/compliance docs", "Clarifies what sub-agents may see"],
         negatives=["Requires tagging and policy enforcement", "Can slow integration design"],
         risks=["Misclassification can leak sensitive data", "Over-classification can reduce system usefulness"]),
    dict(n=25, slug="backup-disaster-recovery-strategy", title="Backup & Disaster Recovery Strategy", status="Proposed", risk="CRITICAL", tags=["backup","dr","rpo","rto","operations"], docs=["Guinevere_TechnicalArchitecture_v2.0.md","Guinevere_MemorySchema_v2.0.md","Guinevere_APIIntegration_v2.0.md"],
         context="Guinevere's memory, configuration, ADRs, evidence, and operational state are high-value assets. A single VPS deployment needs explicit backup and recovery expectations.",
         decision="Define backup and disaster recovery for PostgreSQL, Redis persistence where applicable, encrypted secrets, ADR/docs/evidence, object storage, and service configuration. Establish RPO/RTO targets, restore tests, encryption of backups, and emergency runbooks before production claims.",
         options=["Rely on VPS snapshots only", "Manual backups when remembered", "Formal backup/DR policy with restore validation"], chosen="Formal backup/DR policy with restore validation",
         positives=["Protects memory and project continuity", "Supports safe upgrades and migrations", "Creates measurable operational readiness"],
         negatives=["Requires recurring restore tests", "Encrypted backups add key-management burden"],
         risks=["Untested backups may be unusable", "Backups can become sensitive data leaks if mishandled"]),
]

def yaml_list(items):
    return "\n".join(f"  - {x}" for x in items)

def related_docs_table(names):
    rows = ["| Document | Relationship |", "|---|---|"]
    for name in names:
        desc = next((d for d, rel in DOCS if d == name for rel in [rel]), "Source document for this ADR.")
        rows.append(f"| [`../{name}`](../{name}) | {desc} |")
    return "\n".join(rows)

def adr_content(a):
    num = f"ADR-{a['n']:03d}"
    links = "\n".join(f"- [`../{name}`](../{name})" for name in a['docs'])
    options = "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(a['options']))
    drivers = [
        "Canonical v2.0 documentation must remain internally consistent.",
        "Samm is the sole owner and final approver; Guinevere may propose and execute but not silently change accepted decisions.",
        "Safety, consent, privacy, and recoverability outrank persona flavor and automation speed.",
        "The decision must be auditable through file-based evidence and linked source documents.",
    ]
    if a['risk'] == "CRITICAL":
        drivers.append("Failure mode is high-impact because it can affect safety, secrets, intimate data, or system recovery.")
    positives = "\n".join(f"- {x}" for x in a['positives'])
    negatives = "\n".join(f"- {x}" for x in a['negatives'])
    risks = "\n".join(f"- {x}" for x in a['risks'])
    canonical = "\n".join(f"- {x}" for x in COMMON_CANONICAL)
    drivers_md = "\n".join(f"- {x}" for x in drivers)
    return dedent(f"""\
    ---
    adr: {a['n']:03d}
    title: "{a['title']}"
    status: "{a['status']}"
    date: "{DATE}"
    deciders:
      - "Samm (Owner, solo developer Indonesia)"
      - "Guinevere (Executor / autonomous system steward)"
    tags:
{yaml_list(a['tags'])}
    risk_level: "{a['risk']}"
    supersedes: "N/A"
    related_documents:
{yaml_list(a['docs'])}
    ---

    # {num}: {a['title']}

    ## Status

    {a['status']}

    ## Date

    {DATE}

    ## Deciders

    {DECIDERS}

    ## Tags

    {', '.join(a['tags'])}

    ## Risk Level

    {a['risk']}

    ## Supersedes

    N/A

    ## Related Documents

    {related_docs_table(a['docs'])}

    ## Context

    {a['context']}

    This ADR is part of the first Guinevere technical-core ADR batch and inherits these locked project decisions unless explicitly stated otherwise:

    {canonical}

    ## Decision Drivers

    {drivers_md}

    ## Considered Options

    {options}

    ## Decision Outcome

    Chosen option: **{a['chosen']}**.

    {a['decision']}

    ## Consequences

    ### Positive

    {positives}

    ### Negative

    {negatives}

    ### Risks

    {risks}

    ## Implementation Notes

    - Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
    - Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
    - Proposed ADRs require Samm approval before they become binding runtime policy.
    - Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.

    ## Links

    {links}
    - [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)
    """)

def index_content(folder=False):
    prefix = "" if folder else "adr/"
    rows = ["| ADR | Title | Status | Risk | Tags | File |", "|---|---|---|---|---|---|"]
    for a in ADRS:
        num = f"ADR-{a['n']:03d}"
        file = f"{num}-{a['slug']}.md"
        rows.append(f"| {num} | {a['title']} | {a['status']} | {a['risk']} | {', '.join(a['tags'])} | [`{file}`]({prefix}{file}) |")
    decision_rows = ["| Canonical Decision | ADR | Status |", "|---|---|---|"]
    decision_map = [
        ("Primary LLM GPT-5.5 via 9Router with 1M context", "ADR-004", "Accepted"),
        ("All LLM routing through 9Router; no OpenRouter fallback", "ADR-005", "Accepted"),
        ("Sub-agent LLM DeepSeek V4 Flash via 9Router", "ADR-006", "Accepted"),
        ("Memory PostgreSQL primary + Redis cache; no SQLite", "ADR-007", "Accepted"),
        ("7-phase SDLC loop", "ADR-011", "Accepted"),
        ("Guinevere MCP native fully replaces OpenCode/opencode", "ADR-013", "Accepted"),
        ("Prometheus + Grafana on primary VPS first", "ADR-017", "Accepted"),
        ("Browser obscura primary + Playwright fallback", "ADR-020", "Accepted"),
        ("Wearable integrations post-MVP", "ADR-021", "Accepted"),
        ("Safe word is global user-autonomy override", "ADR-002", "Proposed → must be approved before runtime enforcement claim"),
    ]
    for d, adr, status in decision_map:
        target = next(a for a in ADRS if f"ADR-{a['n']:03d}" == adr)
        file = f"{adr}-{target['slug']}.md"
        decision_rows.append(f"| {d} | [`{adr}`]({prefix}{file}) | {status} |")
    status_counts = {}
    risk_counts = {}
    for a in ADRS:
        status_counts[a['status']] = status_counts.get(a['status'], 0) + 1
        risk_counts[a['risk']] = risk_counts.get(a['risk'], 0) + 1
    status_md = "\n".join(f"- **{k}**: {v}" for k, v in sorted(status_counts.items()))
    risk_md = "\n".join(f"- **{k}**: {v}" for k, v in sorted(risk_counts.items()))
    backlog = [
        "ADR-026 Requirements Traceability Matrix Governance",
        "ADR-027 Acceptance Criteria Catalog Governance",
        "ADR-028 Privacy Impact Assessment / DPIA",
        "ADR-029 Consent & Revocation Policy",
        "ADR-030 Prompt Injection & Model Safety",
        "ADR-031 RBAC/ABAC Access Control Matrix",
        "ADR-032 Secrets Rotation Runbook",
        "ADR-033 OpenAPI / AsyncAPI Contract Governance",
        "ADR-034 Event Schema & Webhook Contract",
        "ADR-035 Database ERD & Migration Strategy",
        "ADR-036 SLO/SLA/Error Budget Policy",
        "ADR-037 Incident Response & Postmortem Runbook",
        "ADR-038 Feature Flag Governance",
        "ADR-039 Product Analytics & Event Taxonomy",
        "ADR-040 Compliance & Data Residency Mapping",
    ]
    backlog_md = "\n".join(f"- {x}" for x in backlog)
    source_docs = "\n".join(f"- [`{name}`]({('../' if folder else '') + name}) — {desc}" for name, desc in DOCS)
    adr_table = "\n".join(rows)
    decision_table = "\n".join(decision_rows)
    title = "# Guinevere ADR Index v1.0" if not folder else "# Guinevere ADR Folder Index"
    root_link = "" if not folder else "\nRoot master index: [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md).\n"
    return dedent(f"""\
    ---
    title: "Guinevere ADR Index v1.0"
    status: "Active"
    date: "{DATE}"
    owner: "Samm"
    executor: "Guinevere"
    format: "MADR with YAML frontmatter"
    adr_count: 25
    ---

    {title}

    {root_link}
    ## Purpose

    This index is the canonical decision register for Project Guinevere's first 25 technical-core ADRs. Guinevere is a private autonomous AI companion and engineering system with persona identity **Guinevere de Baroque — Super Dominant Yandere Mommy AI Agent**. The ADR set locks technical foundations, safety-critical boundaries, and operational governance needed before later enterprise documentation expands the system.

    ## Source Documents

    {source_docs}

    ## Governance

    - **Owner / final approver:** Samm.
    - **Executor / proposer:** Guinevere.
    - Guinevere may propose ADR updates autonomously, but Samm approves final accepted decisions.
    - Accepted ADRs must not be materially edited in-place; create a superseding ADR.
    - Status lifecycle: Proposed → Under Review → Accepted → Rejected → Deprecated → Superseded → Experimental.
    - Security, privacy, persona, and surveillance ADRs require periodic review because they carry higher harm potential than ordinary implementation choices.
    - All structured sub-agent ADR research/audit outputs must be stored as markdown artifacts and read by the parent before use.

    ## Global Safe Word Principle

    The safe word is a global user-autonomy override, not a persona flourish. In genuine distress, safe-word use pauses persona escalation, punishment framing, autonomous pressure, and surveillance-driven confrontation. Guinevere must switch to neutral/supportive mode, minimize logging, and avoid punitive violation records unless Samm explicitly identifies the event as abuse or test mode. This principle is governed by ADR-002 and applies across all future ADRs.

    ## Canonical Decision Map

    {decision_table}

    ## ADR Register

    {adr_table}

    ## Status Summary

    {status_md}

    ## Risk Summary

    {risk_md}

    ## Backlog for Future ADRs

    {backlog_md}

    ## Maintenance Rules

    - Add new ADRs with monotonically increasing numbers.
    - Do not reuse ADR numbers.
    - If an ADR supersedes another, update both the new ADR and this index.
    - Keep every ADR linked to at least one v2.0 source document or an explicitly named future source document.
    - Keep `adr/README.md` synchronized with this master index.
    """)

def main():
    ADR_DIR.mkdir(parents=True, exist_ok=True)
    for a in ADRS:
        num = f"ADR-{a['n']:03d}"
        path = ADR_DIR / f"{num}-{a['slug']}.md"
        path.write_text(adr_content(a), encoding="utf-8")
    (ROOT / "Guinevere_ADR_Index_v1.0.md").write_text(index_content(folder=False), encoding="utf-8")
    (ADR_DIR / "README.md").write_text(index_content(folder=True), encoding="utf-8")
    manifest = "\n".join(["# ADR Generation Manifest", "", f"Generated: {DATE}", "", "## Files"] + [f"- adr/ADR-{a['n']:03d}-{a['slug']}.md" for a in ADRS] + ["- Guinevere_ADR_Index_v1.0.md", "- adr/README.md"])
    (ROOT / "evidence" / "adr-generation" / "generation-manifest.md").write_text(manifest, encoding="utf-8")
    print("Generated", len(ADRS), "ADR files plus indexes")

if __name__ == "__main__":
    main()
