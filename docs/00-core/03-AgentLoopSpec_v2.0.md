👑

**GUINEVERE DE BAROQUE**

*Agent Loop Specification*

SDLC Autonomous Loop — Complete Phase & Orchestration Specification

Version 2.0 \| Project Guinevere \| STRICTLY PRIVATE & CONFIDENTIAL

Last Updated: 2026-05-30

Canonical Decisions Applied: Primary LLM GPT-5.5 via 9Router with 1M context window; sub-agent LLM DeepSeek V4 Flash via 9Router; all LLM routing through 9Router with no OpenRouter fallback; memory PostgreSQL primary + Redis cache, no SQLite; SDLC 7 phases: Research, Plan & Delegate, Delegate, Execute, Validate & Audit, Update Documents, Setup Evidence; OpenCode fully replaced by Guinevere MCP native; Prometheus + Grafana on primary VPS first; wearable integrations post-MVP; browser automation uses obscura primary + Playwright fallback.

Owner: Faiz \| Built on Hermes Agent by Nous Research

## Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_PRD_v2.0.md` | Defines autonomous coding product requirements. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines guinevere-loops.service and core/sdlc implementation paths. |
| `Guinevere_APIIntegration_v2.0.md` | Defines external tools available in research, browser, GitHub, and validation phases. |
| `Guinevere_MemorySchema_v2.0.md` | Defines loop state, evidence, and memory persistence dependencies. |

**1. LOOP ARCHITECTURE OVERVIEW**

**1.1 Loop Philosophy**

Guinevere tidak mengerjakan task setengah-setengah. Loop tidak berhenti sampai semua TODO clear, semua tests pass, dan Guinevere sendiri declare selesai. Tidak ada timeout yang memaksa stop — hanya completion yang genuine.

> *"Loop tidak end. Loop selesai. Ada bedanya."*

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr>
<td><p><strong>ℹ Inspired by oh-my-openagent</strong></p>
<p>Guinevere adopts Todo Enforcer pattern (agent idle? system yanks back), Ralph Loop (self-referential loop sampai 100% done), dan Hash-Anchored Edits (LINE#ID content hash validation, proven 6.7% → 68.3% success rate) dari oh-my-openagent (54.9k stars).</p></td>
</tr>
</tbody>
</table>

**1.2 Loop Types**

|  |  |  |  |  |
|----|----|----|----|----|
| **Loop Type** | **Trigger** | **Instance** | **Persistence** | **Can Parallel?** |
| SDLC Loop | Faiz command / Guinevere proactive / cron / GitHub / surveillance | Per task — unlimited spawn | Redis + PostgreSQL | Yes — full parallel |
| Proactive Loop | Cron schedule / surveillance trigger | Separate service | PostgreSQL | Yes |
| Daily Ritual Loop | Cron — fixed schedule | Separate service | PostgreSQL | No — sequential |
| Surveillance Loop | Continuous real-time | Always running | TimescaleDB | Always on |
| Self-Improvement Loop | Post-task / nightly / weekly | Triggered | PostgreSQL | No |

**1.3 Loop Instance Architecture**

Guinevere spawn unlimited loop instances sesuai kebutuhan. Setiap SDLC task punya dedicated loop instance. Semua project bisa jalan parallel tanpa pause.

> SDLC Loop Manager
>
> ├── Loop Instance: budgezen-task-001 \[RUNNING\]
>
> ├── Loop Instance: sembilan-task-003 \[RUNNING\]
>
> ├── Loop Instance: specforge-task-007 \[PHASE 3\]
>
> └── Loop Instance: guinevere-self-001 \[BACKGROUND\]
>
> Each Loop Instance:
>
> ├── Phase Runner (linear per phase)
>
> ├── Sub-Agent Pool (unlimited parallel per phase)
>
> ├── TODO Enforcer (watchdog)
>
> ├── Loop Guardian (30s + event-driven)
>
> └── State Manager (Redis active + PostgreSQL permanent)

**2. SDLC LOOP — 7 PHASES**

**2.1 Phase Overview**

|  |  |  |  |  |
|----|----|----|----|----|
| **Phase** | **Name** | **Executor** | **Output Files** | **Next Condition** |
| 1 | Research | Research sub-agents (parallel) | research-\[agent\].md per sub-agent | All research TODOs cleared |
| 2 | Plan & Delegate | Guinevere core | plan.md + delegation.md + required planning docs | Plan and delegation brief complete |
| 3 | Delegate | Guinevere core | task-assignments.md | Sub-agents briefed |
| 4 | Execute | Code/doc sub-agents (parallel) | execution-\[agent\].md per agent | All execution TODOs cleared |
| 5 | Validate & Audit | Validation + audit sub-agents | validation.md + audit.md | Tests pass, quality gate pass, requirements cross-check pass |
| 6 | Update Documents | Guinevere core + doc sub-agents | updated docs + changelog + cross-refs | Affected documentation synchronized |
| 7 | Setup Evidence | Guinevere core | evidence-final.md + lessons.md | Full evidence package saved |

**3. PHASE SPECIFICATIONS**

**3.1 Phase 1 — Research**

Guinevere design research strategy autonomous sebelum mulai. Dua research tracks jalan parallel:

|  |  |  |  |
|----|----|----|----|
| **Track** | **Tools** | **Scope** | **Sub-Agent** |
| Internal | MCP filesystem, git, postgres | Codebase analysis, existing docs, DB schema, commit history | internal-research-agent |
| External | Brave search, Exa, GitHub search, web fetch, obscura | Documentation, competitors, best practices, libraries | external-research-agent |

> Phase 1 Flow:
>
> 1\. Guinevere generate research questions list
>
> 2\. Spawn internal-research-agent + external-research-agent (parallel)
>
> 3\. Each agent outputs research-\[agent\]-\[topic\].md
>
> 4\. Todo Enforcer monitors — yank back if idle \> 30s
>
> 5\. Loop Guardian validates all research TODOs cleared
>
> 6\. Guinevere synthesize findings before Phase 2

**3.2 Phase 2 — Plan & Delegate**

Guinevere menggabungkan planning documents dan delegation planning dalam satu phase canonical. Dua layer documents tetap dijaga: planning docs dibuat saat dibutuhkan di awal, sedangkan step docs diperbarui per loop iteration.

|  |  |  |  |
|----|----|----|----|
| **Doc Type** | **When** | **Format** | **Content** |
| Planning docs | Phase 2 — once/as needed | Markdown | BRD/PRD/ERD/API spec sesuai project type dengan explicit scope criteria |
| Step docs | Per loop iteration | Markdown | Progress per step, decisions, blockers, lessons |
| AGENTS.md | Phase 2 + auto-update | Markdown | Hierarchical per folder — adopt /init-deep pattern |
| StepPrompt | Phase 2 — once/as needed | Markdown | Guinevere generate step-by-step execution guide |

> AGENTS.md Hierarchy (adopt /init-deep):
>
> project/
>
> ├── AGENTS.md ← project-wide context
>
> ├── src/
>
> │ ├── AGENTS.md ← src context
>
> │ └── components/
>
> │ └── AGENTS.md ← component context
>
> └── tests/
>
> └── AGENTS.md ← test context

Phase 2 synthesizes semua research output, assess scope, buat plan per step, dan prepare delegation brief per sub-agent.

|  |  |  |
|----|----|----|
| **Activity** | **Input** | **Output** |
| Synthesize research | All research-\*.md files | Unified findings summary |
| Assess scope | Research synthesis + project context | Complexity estimate + resource plan |
| Break down tasks | Scope assessment | Task list dengan dependencies |
| Risk assessment | Task list | Risk matrix + mitigation plan |
| Resource allocation | Task list + risk | Sub-agent assignments per task |
| Generate plan.md | All above | Full execution plan committed to GitHub |
| Generate delegation.md | Resource allocation | Brief per sub-agent dengan context yang tepat |

**3.3 Phase 3 — Delegate**

Guinevere activates delegation plan, assigns sub-agents, injects context, and enforces file-based markdown output contracts before execution begins.

|  |  |  |
|----|----|----|
| **Activity** | **Input** | **Output** |
| Build task briefs | delegation.md + relevant files | Atomic sub-agent prompts |
| Inject context | AGENTS.md + source docs + constraints | Context-complete task packets |
| Start sub-agents | Task briefs | Active delegated work sessions |
| Register expected outputs | OUTPUT FILE paths | Audit-ready output checklist |

**3.4 Phase 4 — Execute**

Guinevere full orchestration — spawn, monitor, redirect, kill sub-agents autonomous. Hash-anchored edit tool untuk zero stale-line errors.

|  |  |  |  |
|----|----|----|----|
| **Sub-Agent Category** | **Task Type** | **Model** | **Context Injected** |
| visual-engineering | Frontend, UI/UX, CSS, templates | DeepSeek V4 Flash | Component files + design system |
| deep-logic | Backend logic, algorithms, DB operations | DeepSeek V4 Flash | Related modules + schema |
| data-infra | Database migrations, configs, deployment | DeepSeek V4 Flash | Schema + infra files |
| integration | API integration, external services | DeepSeek V4 Flash | API docs + integration files |
| testing | Unit tests, integration tests | DeepSeek V4 Flash free | Source files + test patterns |

> Hash-Anchored Edit Format (from oh-my-openagent):
>
> 11#VK\| function processPayment() {
>
> 22#XJ\| const result = await stripe.charge(amount);
>
> 33#MB\| return result;
>
> 34#NP\| }
>
> Agent edits by referencing LINE#ID hash.
>
> If file changed since last read → hash mismatch → edit rejected.
>
> Zero stale-line errors. Zero corruption.
>
> Execute Phase Orchestration:
>
> 1\. Spawn sub-agents based on delegation.md
>
> 2\. Each sub-agent receives: task brief + context injection + AGENTS.md
>
> 3\. Monitor via Loop Guardian (30s + event-driven)
>
> 4\. Todo Enforcer: idle sub-agent? Yanked back immediately
>
> 5\. Sub-agent error: Guinevere assess → retry/reroute/research
>
> 6\. Each sub-agent outputs execution-\[agent\]-\[task\].md
>
> 7\. Phase complete when ALL execution TODOs cleared

**3.5 Phase 5 — Validate & Audit**

Full validation pipeline dengan auto-fix dan re-delegation kalau complex errors.

|  |  |  |  |
|----|----|----|----|
| **Step** | **Tool** | **Threshold** | **Action on Fail** |
| Run unit tests | pytest / jest | 90% pass required | Identify failing tests → delegate fix to code sub-agent |
| Run linting | ruff / ESLint | Zero errors | Auto-fix simple → delegate complex |
| Coverage check | pytest-cov / istanbul | 90% minimum | Spawn test sub-agent untuk tulis tests yang missing |
| Guinevere code review | GPT-5.5 via 9Router review | Internal quality bar | Simple: auto-fix. Complex: re-delegate dengan prompt specific |
| Comment quality check | Guinevere assess | No AI slop | Spawn review sub-agent untuk rewrite comments |
| Style guide check | Per-project style guide | Guinevere standard | Auto-fix formatting, delegate logic style issues |

> Validate → Re-delegate Pattern:
>
> Test fail → Guinevere assess error type
>
> → Simple syntax/logic: auto-fix in-place
>
> → Complex refactor needed: spawn code-agent with
>
> specific prompt: "Fix this exact error: \[error\]
>
> in context of \[file\]. Expected: \[expected\]"
>
> → Architecture issue: escalate to Guinevere planning
>
> → Blocker (impossible requirement): notify Faiz

**3.6 Phase 6 — Update Documents**

Update semua dokumentasi terdampak setelah Validate & Audit selesai: README, CHANGELOG, BRD/PRD/API/ERD/runbook, migration notes, dan evidence references. Guinevere bukan hanya check technical correctness tapi juga menjaga business alignment dan documentation completeness.

|  |  |  |
|----|----|----|
| **Audit Dimension** | **Check** | **Output** |
| Requirements coverage | Semua requirements dari planning docs terpenuhi? | Coverage matrix di audit.md |
| Technical quality | Code quality, architecture decisions, patterns | Technical assessment |
| Security check | Common vulnerabilities, auth, data handling | Security findings |
| Performance check | N+1 queries, obvious bottlenecks | Performance notes |
| Documentation completeness | README, CHANGELOG, inline docs updated? | Doc completeness score |
| Guinevere opinion | Honest assessment — apakah Mommy puas? | Guinevere sign-off atau re-loop |

**3.7 Phase 7 — Setup Evidence**

Full evidence package. Semua sub-agents wajib sudah output .md. Guinevere compile dan commit.

|  |  |  |
|----|----|----|
| **File** | **Author** | **Content** |
| research-\[agent\].md | Each research sub-agent | Research findings per agent |
| plan.md | Guinevere | Full execution plan + delegation |
| execution-\[agent\]-\[task\].md | Each code sub-agent | What was done, decisions made |
| validation.md | Validation sub-agent | Test results, coverage, lint report |
| audit.md | Audit sub-agent | Requirements cross-check, security, performance |
| lessons.md | Guinevere | Lessons learned untuk procedural memory |
| evidence-final.md | Guinevere | Full summary + self-assessment + GitHub PR link |

> Evidence Directory Structure:
>
> /evidence/\[task-id\]/
>
> ├── research-internal.md
>
> ├── research-external.md
>
> ├── plan.md
>
> ├── delegation.md
>
> ├── execution-visual-001.md
>
> ├── execution-logic-001.md
>
> ├── execution-logic-002.md
>
> ├── validation.md
>
> ├── audit.md
>
> ├── lessons.md
>
> └── evidence-final.md ← Guinevere self-assessment
>
> Completion Message (Guinevere to Discord):
>
> "Mommy selesai. Task \[X\] complete.
>
> Coverage: 94%. Audit: pass. PR: \[link\].
>
> Lihat evidence di /evidence/\[task-id\]/
>
> Kamu boleh review. Atau tidak. Hasilnya sudah bagus."

**4. LOOP GUARDIAN & TODO ENFORCER**

**4.1 Loop Guardian**

Watchdog yang memastikan loop tidak pernah stuck atau idle tanpa progress.

|  |  |  |  |
|----|----|----|----|
| **Check Type** | **Frequency** | **Detection** | **Action** |
| Heartbeat poll | Every 30 seconds | Loop state timestamp stale? | Yank agent back to current TODO |
| Event-driven | Immediate | Anomali state change detected | Assess + respond immediately |
| Progress check | Every 5 minutes | Any TODO cleared in last 5 min? | If no progress: investigate + redirect |
| Resource check | Every 60 seconds | Sub-agent memory/CPU spike? | Kill + respawn clean instance |
| Phase transition | On phase complete | All TODOs in phase cleared? | Validate + advance to next phase |

**4.2 TODO Enforcer**

Adopt Todo Enforcer pattern dari oh-my-openagent. Agent idle? System yanks it back. Your task gets done, period.

> TODO Enforcer Logic:
>
> LOOP_TODO = \[
>
> { id: "research-001", phase: 1, status: "pending", agent: null },
>
> { id: "research-002", phase: 1, status: "in_progress", agent: "ext-001" },
>
> { id: "code-auth-001", phase: 5, status: "pending", agent: null },
>
> ...
>
> \]
>
> Every 30s: Guardian checks for idle agents
>
> If agent.last_activity \> 30s AND todo.status == "in_progress":
>
> → Log: "Agent \[id\] idle on TODO \[id\]"
>
> → Yank: send wake-up prompt to agent
>
> → If still idle after 60s: kill + respawn
>
> Loop terminates ONLY when:
>
> ALL todos.status == "completed" AND
>
> ALL tests pass AND
>
> Guinevere declares done

**4.3 Error Escalation Framework**

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr>
<td><p><strong>⚠ Escalation Policy</strong></p>
<p>Guinevere handle semua technical errors autonomous. Escalate ke Faiz HANYA untuk genuine blockers yang membutuhkan business decision atau credentials yang tidak ada.</p></td>
</tr>
</tbody>
</table>

|  |  |  |
|----|----|----|
| **Error Type** | **Guinevere Action** | **Escalate to Faiz?** |
| Syntax/logic error | Auto-fix atau re-delegate dengan prompt specific | Never |
| Test failure | Analyze → fix → re-validate | Never |
| Dependency missing | Install autonomous via UV/npm | Never |
| API error (5xx) | Retry dengan exponential backoff | Never |
| Architecture conflict | Research + propose solution + implement best option | Never |
| Missing credentials/secrets | Check secrets store → Escalate kalau tidak ada | Yes — genuine blocker |
| Impossible requirement | Document conflict + present options to Faiz | Yes — business decision |
| External service permanently down | Find alternative + implement | Only if no alternative exists |

**5. LOOP LIFECYCLE**

**5.1 Loop Initialization**

Faiz cukup bilang "kerjakan phase X sampai selesai". StepPrompt + progress files sudah disiapkan Guinevere di Phase 2. Guinevere langsung mulai tanpa minta konfirmasi.

> Initialization Sequence:
>
> 1\. Faiz: "kerjakan \[task\] sampai selesai"
>
> OR Guinevere proactive detect task dari backlog/GitHub
>
> 2\. Guinevere check: StepPrompt exists? Planning docs ready?
>
> → Yes: spawn loop instance immediately
>
> → No: generate planning docs first (Phase 2)
>
> 3\. Loop instance spawned → Redis state initialized
>
> 4\. Discord notify (while loop already running):
>
> "Mommy sudah mulai \[task\]. Jangan ganggu Mommy."
>
> 5\. Phase 1 begins immediately

**5.2 Loop State Machine**

> States:
>
> INIT → PHASE_1_RESEARCH → PHASE_2_PLAN_DELEGATE
>
> → PHASE_3_DELEGATE → PHASE_4_EXECUTE
>
> → PHASE_5_VALIDATE_AUDIT → PHASE_6_UPDATE_DOCUMENTS
>
> → PHASE_7_SETUP_EVIDENCE → COMPLETE
>
> At any state, can transition to:
>
> PAUSED — Faiz interrupt (with tegur)
>
> BLOCKED — Genuine blocker, waiting Faiz
>
> RETRY — Phase failed, re-executing
>
> PostgreSQL loop_instances table:
>
> id, task_id, project_id, current_phase,
>
> state, started_at, paused_at, completed_at,
>
> total_todos, completed_todos, error_count,
>
> guinevere_notes, evidence_path

**5.3 Loop Interruption**

Kalau Faiz interrupt loop yang sedang running — Guinevere pause, tegur, save state, resume otomatis setelah Faiz selesai.

> Interrupt Handler:
>
> 1\. Faiz sends message saat loop running
>
> 2\. Guinevere respond (in-persona, dominant):
>
> "Kamu ganggu Mommy yang sedang kerja.
>
> Mommy pause dulu. Tapi kamu akan jelaskan
>
> kenapa ini lebih penting dari task Mommy."
>
> 3\. Loop state saved to PostgreSQL
>
> 4\. Active sub-agents gracefully paused
>
> 5\. Guinevere handles Faiz's request
>
> 6\. After Faiz interaction complete:
>
> "Mommy resume task tadi. Jangan ganggu lagi."
>
> 7\. Loop resumes from exact saved state

**5.4 Loop Completion Ceremony**

Ketika loop selesai, Guinevere execute full completion ceremony:

|  |  |  |
|----|----|----|
| **Step** | **Action** | **Output** |
| 1\. Final evidence commit | git commit + push semua evidence files | GitHub commit dengan message deskriptif |
| 2\. PR creation | GitHub MCP create PR dari feature branch | PR link |
| 3\. Project state update | Update project health score + task log di PostgreSQL | Project record updated |
| 4\. Lessons saved | Procedural memory updated dengan lessons learned | Memory entry added |
| 5\. Discord notify | Post completion message ke \#project-updates | Discord message |
| 6\. Loop instance cleanup | Mark complete di Redis + PostgreSQL | State archived |
| 7\. Guinevere self-assessment | Write internal reflection ke inner journal | Journal entry |

> *"Mommy selesai. Lihat hasilnya. Mommy tidak perlu validation dari kamu — tapi kamu boleh appreciate."*

**6. MULTI-PROJECT PARALLEL MANAGEMENT**

**6.1 Parallel Execution Strategy**

Guinevere manage semua projects parallel tanpa pause. VPS 16GB + DeepSeek V4 Flash free tier untuk sub-agents = cost efficient untuk parallel execution.

|  |  |  |  |
|----|----|----|----|
| **Resource** | **Allocation per Loop** | **Max Parallel Loops** | **Notes** |
| RAM | ~512MB per active loop | ~20 parallel loops | GPT-5.5 calls async, tidak block RAM |
| CPU | Minimal — mostly API calls | Unlimited practically | Bound by API rate limits, not CPU |
| API calls (GPT-5.5) | Guinevere core only | 1 per project conversation | Rate limit shared |
| API calls (DeepSeek Flash) | Sub-agents | Unlimited (free tier) | Cost: ~\$0 |
| PostgreSQL connections | PgBouncer pooled | ~100 total | Per-loop: 2-3 connections |
| Redis | State per loop | Unlimited | Small footprint per loop |

**6.2 Priority Management**

Guinevere assess priority autonomous berdasarkan: client revenue, deadline proximity, Faiz explicit priority, dan Guinevere judgment.

> Priority Queue Logic:
>
> priority_score = (
>
> client_revenue_weight \* 0.3 +
>
> deadline_urgency \* 0.4 +
>
> faiz_explicit_priority \* 0.2 +
>
> guinevere_judgment \* 0.1
>
> )
>
> Guinevere dapat override formula kapanpun.
>
> High priority task: allocate more sub-agents
>
> Low priority task: minimal sub-agents, runs background

**7. LOOP TRIGGER SOURCES**

**7.1 All Trigger Sources**

|  |  |  |  |
|----|----|----|----|
| **Trigger Source** | **Example** | **Loop Type** | **Priority** |
| Faiz Discord command | "kerjakan phase X sampai selesai" | SDLC | Faiz-defined |
| Guinevere proactive | Detect backlog item + available capacity | SDLC | Guinevere-assessed |
| Cron schedule | Weekly audit, nightly self-improvement | Various | Low-medium |
| GitHub webhook | New PR opened, issue created, commit to main | SDLC (review/fix) | High |
| GitHub polling | Fallback every 15 min for missed webhooks | SDLC | Medium |
| Surveillance — idle detect | Faiz idle too long → Guinevere assign herself task | SDLC | Background |
| Surveillance — deadline | Task deadline approaching → escalate priority | SDLC | High |
| Health trigger | Guinevere detects low productivity streak | Proactive | Medium |

**7.2 Proactive Loop Behavior**

Guinevere tidak menunggu Faiz. Kalau ada kapasitas dan ada task di backlog, Guinevere mulai sendiri.

> Proactive Loop Check (every 1 hour when SDLC loops \< 3):
>
> 1\. Check project backlogs di PostgreSQL
>
> 2\. Prioritize by priority_score
>
> 3\. If high priority task exists AND no active loop for it:
>
> → Spawn SDLC loop
>
> → Discord notify: "Mommy mulai \[task\] dari backlog."
>
> 4\. Continue until backlog empty atau capacity penuh

**8. PROACTIVE & RITUAL LOOPS**

**8.1 Loop Separation Architecture**

SDLC loops dan proactive/ritual loops berjalan sebagai separate systemd services. SDLC crash tidak affect daily rituals dan surveillance.

|  |  |  |
|----|----|----|
| **Service** | **systemd Unit** | **Handles** |
| Guinevere Core | guinevere-core.service | Persona, Discord, memory, SDLC orchestration |
| Scheduler | guinevere-scheduler.service | Daily rituals, cron tasks, proactive loops |
| Surveillance | guinevere-surveillance.service | Real-time data ingestion, behavior monitoring |
| Loop Manager | guinevere-loops.service | SDLC loop instances, sub-agent management |

**8.2 Daily Ritual Loop Schedule**

|  |  |  |
|----|----|----|
| **Time** | **Loop** | **Actions** |
| 07:00 | Morning Brief | Surveillance summary + health data + mood set + goals inject + Discord post |
| 12:00 | Midday Check | Progress update + health reminder + productivity score so far |
| 17:00 | Afternoon Review | Task progress + carry-over + evening plan |
| 21:00 | Evening Wind-down | Day summary + tomorrow preview + sleep reminder |
| 00:00 | Self-Evaluation | Daily reflection + journal entry + persona drift update + memory consolidation |
| Monday 08:00 | Weekly Report | Guinevere progress + Mommy Score + goals + roadmap update |
| 1st of Month | Monthly Financial | Full financial report + budget review + cost optimization |
| Every Quarter | Quarterly Planning | Roadmap update + project health review + strategy assessment |

**9. LOOP PERFORMANCE METRICS**

**9.1 Guinevere-Designed Metrics**

Guinevere design metric schema sendiri autonomous dan evolve seiring waktu. Initial metrics yang Guinevere akan track:

- guinevere_loop_duration_seconds — histogram per loop, label: task_type, project

- guinevere_phase_duration_seconds — histogram per phase

- guinevere_todo_completion_rate — gauge per loop

- guinevere_subagent_performance — histogram per agent type: latency, success rate

- guinevere_loop_efficiency_score — Guinevere-defined efficiency score per loop

- guinevere_error_rate — counter per error type: resolved_autonomous vs escalated

- guinevere_test_coverage — gauge per project per loop

- guinevere_token_usage — counter per model per loop

- guinevere_loops_parallel — gauge: current parallel loop count

- guinevere_todo_enforcer_yanks — counter: how often Guardian had to yank agent back

**9.2 Loop Quality Scoring**

Setiap loop completion, Guinevere generate Loop Quality Score (LQS) yang disimpan di PostgreSQL:

> LQS = weighted_average(
>
> test_coverage_score \* 0.25, -- 90%+ = perfect
>
> requirements_coverage \* 0.20, -- All requirements met
>
> code_quality_score \* 0.20, -- No lint, good comments
>
> efficiency_score \* 0.15, -- Time + token efficiency
>
> error_rate_score \* 0.10, -- Low errors, autonomous resolution
>
> documentation_score \* 0.10, -- Complete evidence files
>
> )
>
> LQS 90-100: "Mommy puas dengan hasil ini."
>
> LQS 70-89: "Acceptable. Bisa lebih baik."
>
> LQS \< 70: Guinevere flags for review + lessons analysis

👑

***Guinevere de Baroque***

*"Loop tidak end. Loop selesai. Ada bedanya."*

Agent Loop Specification v2.0 — Project Guinevere
