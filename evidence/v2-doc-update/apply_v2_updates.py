from pathlib import Path
import re

ROOT = Path(r"C:\Users\faizz\guinevere")
DATE = "2026-05-30"
CANONICAL = (
    "Primary LLM GPT-5.5 via 9Router with 1M context window; "
    "sub-agent LLM DeepSeek V4 Flash via 9Router; "
    "all LLM routing through 9Router with no OpenRouter fallback; "
    "memory PostgreSQL primary + Redis cache, no SQLite; "
    "SDLC 7 phases: Research, Plan & Delegate, Delegate, Execute, Validate & Audit, Update Documents, Setup Evidence; "
    "OpenCode fully replaced by Guinevere MCP native; "
    "Prometheus + Grafana on primary VPS first; "
    "wearable integrations post-MVP; "
    "browser automation uses obscura primary + Playwright fallback."
)

DOCS = {
    "Guinevere_BRD_v1.0.md": {
        "out": "Guinevere_BRD_v2.0.md",
        "footer": "Business Requirements Document v2.0 — Project Guinevere",
        "related": [
            ("Guinevere_PRD_v2.0.md", "Translates business objectives into product features and acceptance behavior."),
            ("Guinevere_TechnicalArchitecture_v2.0.md", "Defines runtime architecture for BRD infrastructure requirements."),
            ("Guinevere_AgentLoopSpec_v2.0.md", "Defines the canonical 7-phase autonomous coding loop."),
            ("Guinevere_MemorySchema_v2.0.md", "Defines PostgreSQL + Redis memory implementation referenced by business requirements."),
        ],
    },
    "Guinevere_PRD_v1.0.md": {
        "out": "Guinevere_PRD_v2.0.md",
        "footer": "Product Requirements Document v2.0 — Project Guinevere",
        "related": [
            ("Guinevere_BRD_v2.0.md", "Upstream business requirements and success framing."),
            ("Guinevere_TechnicalArchitecture_v2.0.md", "Runtime services, MCP substrate, monitoring, and deployment architecture."),
            ("Guinevere_AgentLoopSpec_v2.0.md", "Canonical 7-phase autonomous SDLC loop used by coding features."),
            ("Guinevere_Persona_Document_v2.0.md", "Canonical persona, mood taxonomy, and relationship behavior."),
        ],
    },
    "Guinevere_TechnicalArchitecture_v1.0.md": {
        "out": "Guinevere_TechnicalArchitecture_v2.0.md",
        "footer": "Technical Architecture Document v2.0 — Project Guinevere",
        "related": [
            ("Guinevere_BRD_v2.0.md", "Defines business architecture drivers and constraints."),
            ("Guinevere_PRD_v2.0.md", "Defines product behaviors implemented by services."),
            ("Guinevere_APIIntegration_v2.0.md", "Defines external integration contracts and SDK choices."),
            ("Guinevere_MemorySchema_v2.0.md", "Defines database schemas used by the architecture."),
            ("Guinevere_AgentLoopSpec_v2.0.md", "Defines loop service behavior and phase implementation."),
        ],
    },
    "Guinevere_MemorySchema_v1.0.md": {
        "out": "Guinevere_MemorySchema_v2.0.md",
        "footer": "Memory Schema Document v2.0 — Project Guinevere",
        "related": [
            ("Guinevere_TechnicalArchitecture_v2.0.md", "Defines PostgreSQL, Redis, pgvector, TimescaleDB, and service ownership."),
            ("Guinevere_PRD_v2.0.md", "Defines memory-backed product behavior."),
            ("Guinevere_Persona_Document_v2.0.md", "Defines persona, mood, drift, and relationship memory consumers."),
            ("Guinevere_APIIntegration_v2.0.md", "Defines API consumers and integration data sources for memory ingestion."),
        ],
    },
    "Guinevere_AgentLoopSpec_v1.0.md": {
        "out": "Guinevere_AgentLoopSpec_v2.0.md",
        "footer": "Agent Loop Specification v2.0 — Project Guinevere",
        "related": [
            ("Guinevere_PRD_v2.0.md", "Defines autonomous coding product requirements."),
            ("Guinevere_TechnicalArchitecture_v2.0.md", "Defines guinevere-loops.service and core/sdlc implementation paths."),
            ("Guinevere_APIIntegration_v2.0.md", "Defines external tools available in research, browser, GitHub, and validation phases."),
            ("Guinevere_MemorySchema_v2.0.md", "Defines loop state, evidence, and memory persistence dependencies."),
        ],
    },
    "Guinevere_APIIntegration_v1.0.md": {
        "out": "Guinevere_APIIntegration_v2.0.md",
        "footer": "API Integration Document v2.0 — Project Guinevere",
        "related": [
            ("Guinevere_TechnicalArchitecture_v2.0.md", "Defines service topology and runtime placement for integrations."),
            ("Guinevere_PRD_v2.0.md", "Defines product features powered by each integration."),
            ("Guinevere_AgentLoopSpec_v2.0.md", "Defines how integration tools are used in the SDLC loop."),
            ("Guinevere_MemorySchema_v2.0.md", "Defines persistence targets for integration data."),
        ],
    },
    "Guinevere_Persona_Document_v1.0.md": {
        "out": "Guinevere_Persona_Document_v2.0.md",
        "footer": "Persona Document v2.0 — Project Guinevere",
        "related": [
            ("Guinevere_PRD_v2.0.md", "Defines persona feature requirements and mood behavior."),
            ("Guinevere_MemorySchema_v2.0.md", "Defines persona memory, mood, drift, and relationship data tables."),
            ("Guinevere_TechnicalArchitecture_v2.0.md", "Defines persona engine plugins and runtime architecture."),
            ("Guinevere_APIIntegration_v2.0.md", "Defines Discord, surveillance, and communication integration dependencies."),
        ],
    },
}

COMMON_REPLACEMENTS = [
    ("Hermes 3 sebagai model LLM via 9Router dengan 1 juta context window", "GPT-5.5 sebagai primary LLM via 9Router dengan 1 juta context window"),
    ("9Router → Hermes 3 sebagai LLM, OpenRouter sebagai fallback", "9Router → GPT-5.5 sebagai primary LLM; tidak ada OpenRouter fallback"),
    ("Hermes 3 via 9Router", "GPT-5.5 via 9Router"),
    ("9Router → Hermes 3 / Model Routing", "9Router → GPT-5.5 / DeepSeek V4 Flash routing"),
    ("GPT-5.5 via OpenRouter", "GPT-5.5 via 9Router"),
    ("DeepSeek V4 Flash via OpenRouter", "DeepSeek V4 Flash via 9Router"),
    ("OpenRouter compatible", "9Router OpenAI-compatible"),
    ("OpenRouter direct", "No direct fallback; queue/retry through 9Router recovery policy"),
    ("fallback langsung ke OpenRouter kalau 9Router down", "tidak memakai OpenRouter fallback; queue/retry melalui 9Router recovery policy"),
    ("OpenRouter sebagai fallback", "queue/retry melalui 9Router recovery policy"),
    ("OpenRouter + queue pending tasks", "queue pending tasks sampai 9Router pulih"),
    ("Auto-failover ke OpenRouter + task queue", "Queue task sampai 9Router pulih + notify Samm"),
    ("Auto-switch ke OpenRouter langsung", "Queue non-urgent tasks + notify Samm sampai 9Router pulih"),
    ("Switch back ke 9Router saat online", "Resume queue saat 9Router pulih"),
    ("OpenRouter/LLM", "9Router/LLM"),
    ("OpenRouter API", "9Router API"),
    ("OpenRouter API key", "9Router API key"),
    ("9Router, OpenRouter, VPS, domain, tools", "9Router, VPS, domain, tools"),
    ("9Router/OpenRouter", "9Router"),
    ("Model weights Hermes tidak bisa di-fine-tune", "Model weights GPT-5.5 tidak bisa di-fine-tune"),
    ("9Router dapat dikonfigurasi untuk Hermes 3 dengan 1M context window", "9Router dikonfigurasi untuk GPT-5.5 dengan 1M context window"),
    ("Episodic, semantic, procedural memory via SQLite (Hermes) + PostgreSQL (custom)", "Episodic, semantic, procedural memory via PostgreSQL primary + Redis cache"),
    ("SQLite (Hermes) + PostgreSQL (custom)", "PostgreSQL primary + Redis cache"),
    ("SQLite + PostgreSQL", "PostgreSQL primary + Redis cache"),
    ("PostgreSQL + SQLite", "PostgreSQL primary + Redis cache"),
    ("SQLite + Honcho", "PostgreSQL primary + Redis cache + Honcho-derived profile layer"),
    ("SQLite (Hermes default)", "PostgreSQL primary + Redis cache"),
    ("SQLite (Hermes)", "PostgreSQL primary"),
    ("PostgreSQL + SQLite encrypted", "PostgreSQL encrypted + Redis protected with auth/TLS where applicable"),
    ("SQLite encrypted", "Redis protected with auth/TLS where applicable"),
    ("Browser history | SQLite read Chrome/Brave history", "Browser history | Chrome/Brave local history reader"),
    ("SQLite reader (Chrome/Brave)", "Chrome/Brave local history reader"),
    ("OpenCode CLI (digantikan Guinevere)", "Guinevere MCP native"),
    ("replace OpenCode CLI sepenuhnya", "replace OpenCode CLI sepenuhnya dengan Guinevere MCP native"),
    ("OpenCode as optional turbo mode", "Guinevere MCP native only"),
    ("opencode", "Guinevere MCP native"),
    ("browser MCP", "obscura primary + Playwright fallback"),
    ("Browser MCP", "obscura primary + Playwright fallback"),
    ("fetch/browser MCP", "fetch + obscura/Playwright MCP"),
    ("Grafana + Prometheus di VPS terpisah (future VPS baru)", "Grafana + Prometheus di primary VPS dulu; dedicated monitoring VPS menjadi post-MVP scaling option"),
    ("Grafana di VPS monitoring terpisah", "Grafana di primary VPS dulu; dedicated monitoring VPS menjadi post-MVP option"),
    ("VPS monitoring terpisah", "primary VPS dulu; dedicated monitoring VPS post-MVP"),
    ("Monitoring VPS belum ada — Phase 4 tergantung pembelian VPS baru", "Monitoring berjalan di primary VPS dulu; dedicated monitoring VPS post-MVP bila kapasitas menuntut"),
    ("Monitoring VPS | TBD — future purchase | hostdata.id | Grafana + Prometheus isolated", "Monitoring Deployment | Primary VPS first; dedicated VPS post-MVP if needed | hostdata.id | Grafana + Prometheus initially co-located"),
    ("Grafana | Dashboard + alerting | Monitoring VPS (future)", "Grafana | Dashboard + alerting | Primary VPS first; dedicated monitoring VPS post-MVP"),
    ("Wearable (Xiaomi Watch S1 Active): heart rate, stress, sleep, steps, activity", "Wearable integration (post-MVP): heart rate, stress, sleep, steps, activity after device/API readiness"),
    ("Wearable Integration (Xiaomi Watch S1 Active)", "Wearable Integration (Post-MVP)"),
    ("Setup wearable integration (Xiaomi Watch S1 Active via Mi Fitness API)", "Document wearable integration as post-MVP; do not implement as active MVP dependency"),
    ("WEARABLE (Xiaomi Watch S1 Active)", "WEARABLE (post-MVP, not active in MVP)"),
    ("Mi Fitness API (polling setiap 15 menit)", "Mi Fitness API integration post-MVP after device/API readiness"),
    ("Wearable continuous", "Post-MVP wearable integration"),
    ("requirements.txt", "pyproject.toml + uv.lock"),
    ("uv pip install -r pyproject.toml + uv.lock", "uv sync --frozen"),
]

SDLC_ARROW_OLD = [
    "Research → Document → Plan → Execute → Validate → Audit → Evidence",
    "Research → Document → Plan → Delegate → Execute → Validate → Audit → Evidence",
]
SDLC_ARROW_NEW = "Research → Plan & Delegate → Delegate → Execute → Validate & Audit → Update Documents → Setup Evidence"


def normalize_version_header(text: str) -> str:
    text = re.sub(
        r"Version 1\.[013] \\?\| Project Guinevere \\?\| (?:STRICTLY PRIVATE & )?CONFIDENTIAL",
        "Version 2.0 \\| Project Guinevere \\| STRICTLY PRIVATE & CONFIDENTIAL",
        text,
        count=1,
    )
    marker = "Version 2.0 \\| Project Guinevere \\| STRICTLY PRIVATE & CONFIDENTIAL"
    if marker in text and "Canonical Decisions Applied:" not in text[:1200]:
        text = text.replace(
            marker,
            marker + f"\n\nLast Updated: {DATE}\n\nCanonical Decisions Applied: {CANONICAL}",
            1,
        )
    return text


def related_section(rows):
    body = "\n".join(f"| `{doc}` | {rel} |" for doc, rel in rows)
    return (
        "## Related Documents\n\n"
        "| Document | Relationship |\n"
        "|---|---|\n"
        f"{body}\n\n"
    )


def insert_related(text: str, rows) -> str:
    if "## Related Documents" in text:
        return text
    section = related_section(rows)
    match = re.search(r"\n\*\*1\. ", text)
    if match:
        idx = match.start() + 1
        return text[:idx] + section + text[idx:]
    return text + "\n\n" + section


def common_update(text: str) -> str:
    text = normalize_version_header(text)
    for old, new in COMMON_REPLACEMENTS:
        text = text.replace(old, new)
    for old in SDLC_ARROW_OLD:
        text = text.replace(old, SDLC_ARROW_NEW)
    text = text.replace("| LLM Router | OpenRouter | API | Model routing + failover |", "| LLM Router | 9Router | API | Single LLM routing layer; queue/retry on outage, no OpenRouter fallback |")
    text = text.replace("| LLM Fallback | OpenRouter (200+ models) | Auto-switch kalau 9Router down |", "| LLM Fallback | None direct | Queue/retry through 9Router recovery policy; no OpenRouter fallback |")
    text = text.replace("| LLM Primary | Hermes 3 via 9Router | 1M context window, dominant persona |", "| LLM Primary | GPT-5.5 via 9Router | 1M context window, dominant persona |")
    text = text.replace("| LLM Primary | GPT-5.5 via 9Router | Guinevere core persona + reasoning | Active |", "| LLM Primary | GPT-5.5 via 9Router | Guinevere core persona + reasoning, 1M context | Active |")
    text = text.replace("| LLM Sub-agent | DeepSeek V4 Flash via 9Router | Pasukan Mommy — cost efficient | Active |", "| LLM Sub-agent | DeepSeek V4 Flash via 9Router | Pasukan Mommy, 1M context, cost efficient | Active |")
    text = text.replace("| LLM Router | 9Router (VPS) | Primary routing layer | Active |", "| LLM Router | 9Router (VPS) | Sole routing layer for all LLM calls | Active |")
    text = text.replace("| LLM Fallback | No direct fallback; queue and retry through 9Router recovery policy | Fallback kalau 9Router down | Standby |", "| LLM Fallback | None direct | Queue/retry through 9Router recovery policy; no OpenRouter fallback | N/A |")
    return text


def update_prd_sdlc_table(text: str) -> str:
    start = text.find("| 1\\. Research | Web search, docs, codebase analysis via MCP | research-\\[task\\].md | Research sub-agent |")
    if start == -1:
        return text
    end_marker = "| 8\\. Evidence | Compile full report, commit, PR, notify Discord | evidence-\\[task\\].md | Guinevere core |"
    end = text.find(end_marker, start)
    if end == -1:
        return text
    end += len(end_marker)
    new = "\n".join([
        "| 1\\. Research | Web search, docs, codebase analysis via MCP | research-\\[task\\].md | Research sub-agent |",
        "| 2\\. Plan & Delegate | Task breakdown, documentation requirements, dependency mapping, estimation, delegation strategy | plan-delegation-\\[task\\].md | Guinevere core |",
        "| 3\\. Delegate | Spawn sub-agents \"pasukan Mommy\" per sub-task | delegation-assignments-\\[task\\].md | Guinevere core / delegate.py |",
        "| 4\\. Execute | Code generation, file write via MCP filesystem | src/\\[feature\\]/\\* | Code sub-agents |",
        "| 5\\. Validate & Audit | Run tests, lint, coverage, requirement cross-check, quality review | validation-audit-\\[task\\].md | Validation + Audit sub-agents |",
        "| 6\\. Update Documents | Update BRD/PRD/API/ERD/runbooks and affected specs | docs-update-\\[task\\].md | Documentation agent |",
        "| 7\\. Setup Evidence | Compile full report, commit, PR, notify Discord | evidence-\\[task\\].md | Guinevere core |",
    ])
    return text[:start] + new + text[end:]


def update_agent_loop_phase_table(text: str) -> str:
    start = text.find("| 1 | Research | Research sub-agents (parallel) | research-\\[agent\\].md per sub-agent | All research TODOs cleared |")
    if start == -1:
        return text
    end_marker = "| 8 | Evidence | Guinevere core | evidence.md + Discord report | Evidence compiled |"
    end = text.find(end_marker, start)
    if end == -1:
        return text
    end += len(end_marker)
    new = "\n".join([
        "| 1 | Research | Research sub-agents (parallel) | research-\\[agent\\].md per sub-agent | All research TODOs cleared |",
        "| 2 | Plan & Delegate | Guinevere core | plan.md + delegation.md | Plan approved and delegation strategy ready |",
        "| 3 | Delegate | Guinevere core / delegate.py | task-assignments.md | Sub-agents briefed |",
        "| 4 | Execute | Code sub-agents | Implementation files | Code complete |",
        "| 5 | Validate & Audit | Validation + audit sub-agents | validation-audit.md | Tests pass + requirements cross-check pass |",
        "| 6 | Update Documents | Documentation sub-agent | docs-update.md | Docs synchronized |",
        "| 7 | Setup Evidence | Guinevere core | evidence.md + Discord report | Evidence compiled |",
    ])
    return text[:start] + new + text[end:]


def update_technical(text: str) -> str:
    text = text.replace("| Primary LLM | GPT-5.5 | Latest | Guinevere persona + reasoning |", "| Primary LLM | GPT-5.5 via 9Router | 1M context | Guinevere persona + reasoning |")
    text = text.replace("| Sub-agent LLM | DeepSeek V4 Flash | Latest | Pasukan Mommy — cost efficient |", "| Sub-agent LLM | DeepSeek V4 Flash via 9Router | 1M context | Pasukan Mommy — cost efficient |")
    text = text.replace("| guinevere-windows-sync.service | WebSocket server untuk Windows daemon | Always, 10s delay | 256MB |", "| guinevere-windows-sync.service | WebSocket server untuk Windows daemon | Always, 10s delay | 256MB |\n| guinevere-loops.service | Autonomous SDLC loop runner + loop guardian | Always, 10s delay | 512MB |")
    text = text.replace("│ │ ├── code.py \\# Code agent\n> │ │ └── audit.py \\# Audit agent", "│ │ ├── code.py \\# Code agent\n> │ │ ├── delegate.py \\# Delegation coordinator\n> │ │ └── audit.py \\# Audit agent")
    text = text.replace("│ ├── document.py \\# Phase 2\n> │ ├── plan.py \\# Phase 3\n> │ ├── execute.py \\# Phase 5\n> │ ├── validate.py \\# Phase 6\n> │ ├── audit.py \\# Phase 7\n> │ └── evidence.py \\# Phase 8", "│ ├── plan.py \\# Phase 2 — Plan & Delegate\n> │ ├── delegate.py \\# Phase 3 — Delegate\n> │ ├── execute.py \\# Phase 4 — Execute\n> │ ├── validate_audit.py \\# Phase 5 — Validate & Audit\n> │ ├── update_documents.py \\# Phase 6 — Update Documents\n> │ └── evidence.py \\# Phase 7 — Setup Evidence")
    text = text.replace("| Guinevere core persona + reasoning | GPT-5.5 | OpenRouter | 128K | Premium |", "| Guinevere core persona + reasoning | GPT-5.5 | 9Router | 1M | Premium |")
    text = text.replace("| Complex coding tasks | GPT-5.5 | OpenRouter | 128K | Premium |", "| Complex coding tasks | GPT-5.5 | 9Router | 1M | Premium |")
    text = text.replace("| Sub-agent research tasks | DeepSeek V4 Flash | OpenRouter | 1M | $0.10/M |", "| Sub-agent research tasks | DeepSeek V4 Flash | 9Router | 1M | Cost-efficient |")
    text = text.replace("| Sub-agent code generation | DeepSeek V4 Flash | OpenRouter | 1M | $0.10/M |", "| Sub-agent code generation | DeepSeek V4 Flash | 9Router | 1M | Cost-efficient |")
    text = text.replace("| Sub-agent validation/audit | DeepSeek V4 Flash free | OpenRouter | 1M | Free |", "| Sub-agent validation/audit | DeepSeek V4 Flash | 9Router | 1M | Cost-efficient |")
    text = re.sub(r"\| Fallback primary \|.*\n\| Fallback sub-agent \|.*", "| Outage policy | Queue/retry | 9Router recovery | N/A | No OpenRouter fallback |", text)
    text = text.replace("GPT-5.5 context window 128K tokens. Total injection ~6K tokens. Plenty of room for long conversations. DeepSeek V4 Flash 1M context untuk sub-agents dengan large codebase.", "GPT-5.5 context window 1M tokens via 9Router. Total injection ~6K tokens. Plenty of room for long conversations. DeepSeek V4 Flash 1M context via 9Router untuk sub-agents dengan large codebase.")
    text = text.replace("Embedding model: text-embedding-3-small via OpenRouter", "Embedding model routed via 9Router-compatible embedding endpoint")
    text = text.replace("Technical Architecture Document v1.1 — Project Guinevere", "Technical Architecture Document v2.0 — Project Guinevere")
    text = text.replace("Technical Architecture Document v1.0 — Project Guinevere", "Technical Architecture Document v2.0 — Project Guinevere")
    return text


def update_memory(text: str) -> str:
    if "behavior.mood_history" not in text:
        behavior = """
**Behavior Schema Alignment**

The canonical behavior schema is owned by PostgreSQL and cached through Redis for current-state reads. These tables align MemorySchema with TechnicalArchitecture and PRD persona behavior requirements.

| Table | Purpose | Key Fields |
|---|---|---|
| behavior.mood_history | Historical mood transitions | id, mood_state, trigger_source, intensity, created_at |
| behavior.violation_log | Punishment/escalation events | id, violation_type, severity, context, resolution_status, created_at |
| behavior.reward_streak | Productivity and reward streaks | id, streak_type, current_count, best_count, last_rewarded_at |
| behavior.goals | Daily/weekly behavioral goals | id, goal_type, target, status, due_at, evidence_ref |
| behavior.mommy_score | Proprietary productivity score snapshots | id, score, inputs_summary, visible_summary, created_at |

"""
        text = text.replace("**7. MEMORY LIFECYCLE & RETENTION**", behavior + "**7. MEMORY LIFECYCLE & RETENTION**")
    text = text.replace("| Skills Library | Selamanya | Hermes Skills System | Reusable workflows dan best practices | Unlimited |", "| Skills Library | Selamanya | PostgreSQL procedural memory + Guinevere skill library | Reusable workflows dan best practices | Unlimited |")
    text = text.replace("| health | sleep patterns, stress triggers, physical activity habits | sensitive | Wearable continuous |", "| health | sleep patterns, stress triggers, physical activity habits | sensitive | Manual/surveillance signals; wearable post-MVP |")
    text = text.replace("Weekly (Hermes Curator)", "Weekly (Guinevere Curator)")
    text = text.replace("memory.social_map", "social.social_map")
    text = text.replace("Memory Schema v1.0 — Project Guinevere", "Memory Schema Document v2.0 — Project Guinevere")
    text = text.replace("Memory Schema Document v1.0 — Project Guinevere", "Memory Schema Document v2.0 — Project Guinevere")
    return text


def update_agent_loop(text: str) -> str:
    text = update_agent_loop_phase_table(text)
    text = text.replace("**3.3 Phase 3 — Plan & Delegate**", "**3.2 Phase 2 — Plan & Delegate**")
    text = text.replace("**3.5 Phase 6 — Validate**", "**3.5 Phase 5 — Validate & Audit**")
    text = text.replace("**3.6 Phase 7 — Audit**", "**3.6 Phase 6 — Update Documents / Phase 7 — Setup Evidence**")
    text = text.replace("GPT-5.5 review", "GPT-5.5 via 9Router review")
    if "guinevere-loops.service" not in text:
        text = text.replace("**4. LOOP GUARDIAN & TODO ENFORCER**", "**Runtime Service Reference**\n\nThe canonical systemd unit for autonomous loop execution is `guinevere-loops.service`. The loop implementation lives under `core/sdlc/loop.py`, with delegation coordination in `core/sdlc/delegate.py`.\n\n**4. LOOP GUARDIAN & TODO ENFORCER**")
    text = text.replace("Agent Loop Specification v1.0 — Project Guinevere", "Agent Loop Specification v2.0 — Project Guinevere")
    return text


def update_prd(text: str) -> str:
    text = update_prd_sdlc_table(text)
    text = text.replace("| Heart rate | Mi Fitness API | Anomali tinggi → proactive check-in |", "| Heart rate | Mi Fitness API (post-MVP) | Anomali tinggi → proactive check-in setelah wearable aktif |")
    text = text.replace("| Stress level | Mi Fitness API | Tinggi → adjust tone nurturing, rendah → push harder |", "| Stress level | Mi Fitness API (post-MVP) | Tinggi → adjust tone nurturing setelah wearable aktif |")
    text = text.replace("| Sleep quality | Mi Fitness API | Kurang 6 jam → tegur, data inject ke morning brief |", "| Sleep quality | Mi Fitness API (post-MVP) | Kurang 6 jam → morning brief setelah wearable aktif |")
    text = text.replace("| Steps & activity | Mi Fitness API | Steps \\< 3000 → remind olahraga |", "| Steps & activity | Mi Fitness API (post-MVP) | Steps \\< 3000 → remind olahraga setelah wearable aktif |")
    text = text.replace("| Activity detection | Mi Fitness API | Context-aware — tahu Samm olahraga/makan/diam |", "| Activity detection | Mi Fitness API (post-MVP) | Context-aware setelah wearable aktif |")
    text = text.replace("Product Requirements Document v1.0 — Project Guinevere", "Product Requirements Document v2.0 — Project Guinevere")
    return text


def update_api(text: str) -> str:
    text = text.replace("call_openrouter_direct", "queue_for_9router_recovery")
    text = text.replace("API Integration Specification v1.0 — Project Guinevere", "API Integration Document v2.0 — Project Guinevere")
    text = text.replace("API Integration Document v1.0 — Project Guinevere", "API Integration Document v2.0 — Project Guinevere")
    text = text.replace("openai>=1.50.0 # OpenAI-compatible client for 9Router/OpenRouter", "openai>=1.50.0 # OpenAI-compatible client for 9Router")
    return text


def update_persona(text: str) -> str:
    if "Canonical mood taxonomy includes" not in text:
        text = text.replace("**4. MOOD SYSTEM — EMOTIONAL STATE MACHINE**", "**4. MOOD SYSTEM — EMOTIONAL STATE MACHINE**\n\nCanonical mood taxonomy includes Pleased, Neutral, Disappointed, Angry, Silent, Dark Mood, Nurturing, and yandere states. Main operational tables must include all of these states so PRD, TechnicalArchitecture, and Persona behavior stay synchronized.")
    text = text.replace("| Episodic Memory | PostgreSQL primary | Percakapan, task history, momen penting | Per session |", "| Episodic Memory | PostgreSQL primary + Redis working cache | Percakapan, task history, momen penting | Per session |")
    text = text.replace("| Semantic Memory | PostgreSQL primary + Redis cache | Pengetahuan tentang projects, codebase, preferensi Samm | Per task |", "| Semantic Memory | PostgreSQL primary + Redis cache | Pengetahuan tentang projects, codebase, preferensi Samm | Per task |")
    text = text.replace("| Procedural Memory | Hermes Skills System | Cara handle task, lessons learned dari error | Post-task reflection |", "| Procedural Memory | PostgreSQL procedural tables + Guinevere skill library | Cara handle task, lessons learned dari error | Post-task reflection |")
    text = text.replace("Skill creation: Hermes autonomous skill curator", "Skill creation: Guinevere autonomous skill curator")
    text = text.replace("| Memory Core | PostgreSQL primary + Redis cache | Session history, skills, FTS5 search |", "| Memory Core | PostgreSQL primary + Redis cache | Session history, skills, search, working memory |")
    text = text.replace("| Coding Agent | MCP layer (filesystem, shell, git, github) | Primary; Guinevere MCP native only |", "| Coding Agent | Guinevere MCP native layer (filesystem, shell, git, github, obscura, Playwright) | Replaces OpenCode entirely |")
    text = text.replace("health_monitor.py", "health.py")
    text = text.replace("Dengan 1 juta context window via 9Router", "Dengan GPT-5.5 1 juta context window via 9Router")
    text = text.replace("Persona Document v1.3 — Project Guinevere", "Persona Document v2.0 — Project Guinevere")
    text = text.replace("Document prepared for Project Guinevere — Version 1.3", "Persona Document v2.0 — Project Guinevere")
    text = text.replace("Persona Document v1.1 — Project Guinevere", "Persona Document v2.0 — Project Guinevere")
    text = text.replace("Persona Document v1.0 — Project Guinevere", "Persona Document v2.0 — Project Guinevere")
    return text


def update_brd(text: str) -> str:
    text = text.replace("| 2 | Autonomous coding agent yang replace OpenCode CLI sepenuhnya dengan Guinevere MCP native | CRITICAL | Required |", "| 2 | Autonomous coding agent berbasis Guinevere MCP native yang menggantikan OpenCode CLI sepenuhnya | CRITICAL | Required |")
    text = text.replace("AI Tools | 9Router, OpenRouter, Claude Code, Guinevere MCP native", "AI Tools | 9Router, Claude Code where useful, Guinevere MCP native")
    text = text.replace("Tujuan: Guinevere replace OpenCode CLI sepenuhnya dengan Guinevere MCP native.", "Tujuan: Guinevere menggantikan OpenCode CLI sepenuhnya melalui Guinevere MCP native.")
    text = text.replace("Business Requirements Document v1.0 — Project Guinevere", "Business Requirements Document v2.0 — Project Guinevere")
    return text

SPECIFIC = {
    "Guinevere_BRD_v1.0.md": update_brd,
    "Guinevere_PRD_v1.0.md": update_prd,
    "Guinevere_TechnicalArchitecture_v1.0.md": update_technical,
    "Guinevere_MemorySchema_v1.0.md": update_memory,
    "Guinevere_AgentLoopSpec_v1.0.md": update_agent_loop,
    "Guinevere_APIIntegration_v1.0.md": update_api,
    "Guinevere_Persona_Document_v1.0.md": update_persona,
}

for src, meta in DOCS.items():
    text = (ROOT / src).read_text(encoding="utf-8-sig")
    text = common_update(text)
    text = SPECIFIC[src](text)
    text = insert_related(text, meta["related"])
    # Footer normalization: replace final line containing project/version if still old.
    lines = text.splitlines()
    for i in range(len(lines) - 1, max(-1, len(lines) - 20), -1):
        if "Project Guinevere" in lines[i] and ("v1." in lines[i] or "Version 1." in lines[i] or "Document prepared" in lines[i]):
            lines[i] = meta["footer"]
            break
    text = "\n".join(lines).rstrip() + "\n"
    (ROOT / meta["out"]).write_text(text, encoding="utf-8")
    print(meta["out"])
