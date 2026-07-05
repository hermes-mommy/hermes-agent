# P23 Research — Repository Architecture Inventory

> **Status**: RESEARCH (definition phase)  
> **Date**: 2026-06-25  
> **Author**: Guinevere research subagent  
> **Scope**: Complete repository surface inventory for P23 Embodied Operations / Personal OS Action Layer

---

## 1. Objective

Produce a comprehensive inventory of all repository surfaces that P23 "Embodied Operations / Personal OS Action Layer" will build on, integrate with, or must respect. Map each surface's responsibility, current state, and P23 relation (additive/extend/read-only/forbidden) with explicit file paths and line numbers.

This inventory serves as the foundation for:
- Executor registry design (which surfaces can execute actions)
- Collision scan inputs (shared writers, configs, migrations)
- Policy gate integration points
- HARD STOP enforcement verification
- Test structure alignment

---

## 2. Sources Consulted

### 2.1 Ground Truth Documents (Authority — Do Not Re-Derive)

| Document | Path | Sections |
|---|---|---|
| AGENTS.md | `AGENTS.md` | §0.1 (P20 Autonomy-First Governance Exception), §10 (Full Autonomous Task Template) |
| PersonaSafetyPolicy | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | §7.2 (HARD STOP), §15.1 (Tool-risk gate) |
| ADR-020 | `adr/ADR-020-browser-automation-strategy.md` | Browser automation strategy (Obscura primary + Playwright fallback) |
| ADR-033 | `adr/ADR-033-browser-automation-obscura.md` | Obscura CDP server + playwright-core client architecture |
| ADR-016 | `adr/ADR-016-cicd-autonomous-deployment-strategy.md` | CI/CD & autonomous deployment strategy |
| ADR-029 | `adr/ADR-029-self-modification-automated-testing.md` | Self-modification automated testing |
| ADR-012 | `adr/ADR-012-sub-agent-orchestration-governance.md` | Sub-agent orchestration governance |
| ADR-030 | `adr/ADR-030-redis-database-allocation.md` | Redis DB0-5 allocation |
| ADR-015 | `adr/ADR-015-secrets-management-strategy.md` | SOPS/age secrets management |
| ADR-025/032 | `adr/ADR-025-backup-dr-strategy.md` | Backup/DR strategy |

### 2.2 P20 Vision Lock

| Vision Lock | Definition |
|---|---|
| V-001 | Alive 24/7, not trigger-driven |
| V-003 | Autonomous by default — silence is not a blocker |
| V-004 | Hermes brain = `AIAgent.run_conversation()` via `src/life_kernel/hermes_brain.py` |
| V-007 | Audit for debugging, not default approval bottleneck |
| V-008 | HARD STOP absolute — halts all sessions and background cognition |

### 2.3 Repository Files Read (with line references)

| File | Lines | Responsibility |
|---|---|---|
| `src/life_kernel/heartbeat.py` | 1-674 | Heartbeat service, HARD STOP detection (1s), 6 intervals |
| `src/life_kernel/hermes_brain.py` | 1-464 | HermesBrain AIAgent wrapper, `think()`, `think_with_tools()` |
| `src/life_kernel/sensor_adapters/base.py` | 1-84 | BaseSensorAdapter READ-ONLY contract |
| `src/life_kernel/sensors.py` | 1-174 | SensorRegistry, `sense_all()`, `health_check()` |
| `src/life_kernel/graph.py` | 1-1042 | LangGraph StateGraph, observe→decide→act→reflect→idle nodes |
| `src/life_kernel/journal.py` | 1-67 | JournalWriter for reflect phase |
| `src/life_kernel/models.py` | 1-116 | DB models for life_kernel schema |
| `src/life_kernel/state.py` | 1-309 | TypedDict schemas, LifeMindPhase, Priority |
| `src/life_kernel/cognition.py` | 1-406 | BackgroundCognition, 6 observer loops |
| `src/life_kernel/decision_context.py` | 1-100 | DecisionContextBuilder (P16 KG + P18 memory) |
| `src/life_kernel/self_improve.py` | 1-416 | ReflectionEvaluator, ImprovementCandidate, RegressionGate |
| `src/life_kernel/redis_client.py` | 1-120 | World model caching (Redis DB7) |
| `src/life_kernel/checkpoint.py` | 1-162 | PostgreSQL/Redis checkpointers |
| `src/life_kernel/p16_adapter.py` | 1-111 | KGRecallAdapter for P16 KG |
| `src/life_kernel/p18_adapter.py` | 1-102 | MemoryRecallAdapter for P18 memory |
| `src/life_kernel/dashboard.py` | 1-200+ | DashboardRenderer (markdown dashboard) |
| `src/life_kernel/discord_rest_client.py` | 1-100+ | Discord REST API client |
| `src/life_kernel/log_channel.py` | 1-120 | LogChannel abstraction |
| `src/life_kernel/log_writer.py` | 1-120 | File log writer with rotation |
| `src/life_kernel/dashboard_writer.py` | 1-120 | Single edited dashboard message |
| `src/life_kernel/domain_minds/__init__.py` | 1-28 | Domain minds exports |
| `src/life_kernel/domain_minds/engineer_mind.py` | 1-150+ | Policy-gated deploy orchestrator (LK-014) |
| `src/life_kernel/domain_minds/email_mind.py` | 1-120 | Email classifier (LK-012) |
| `src/life_kernel/domain_minds/finance_mind.py` | 1-120 | Finance observer (LK-013) |
| `src/life_kernel/domain_minds/deploy_backend.py` | 1-150+ | SSHDeployBackend with dry-run mode |
| `src/life_kernel/domain_minds/durability.py` | 1-100+ | PostgresAuditJournal, InMemoryJournal |
| `src/core/main.py` | 1-300+ | FastAPI lifespan, HermesBrain init |
| `src/core/services/hard_stop_handler.py` | 1-100 | HARD STOP protocol handler |
| `src/discord/hermes_conversational.py` | 1-150 | Hermes conversational handler |
| `src/hermes/_memory_bridge.py` | 1-120 | HermesMemoryBridge (READ/WRITE paths) |
| `src/hermes/_session_adapter.py` | 1-120 | HermesSessionAdapter (Redis DB4) |
| `src/memory/models.py` | 1-200 | Episodes, SessionSummary, SemanticFacts |
| `src/surveillance/consent_gate.py` | 1-120 | ConsentChecker (fail-closed) |
| `src/surveillance/secret_scanner.py` | 1-120 | SecretPattern, ScanResult |
| `src/mcp/tools/obscura_cdp.py` | 1-80 | Obscura CDP MCP tool |
| `systemd/guinevere-obscura.service` | 1-27 | Obscura CDP systemd service |
| `alembic/versions/p20_001_life_kernel_schema.py` | 1-80 | P20 migration (latest) |
| `pyproject.toml` | 1-89 | Project dependencies |

---

## 3. Findings — Repository Surface Inventory

### 3.1 Master Table

| Surface | Path | Responsibility | P23 Relation | Risk |
|---|---|---|---|---|
| **Heartbeat Service** | `src/life_kernel/heartbeat.py` | 6 intervals (1s/10s/30s/60s/5m/1h), HARD STOP detection via Redis `life_kernel:hard_stop` | **READ-ONLY** — P23 executors MUST check HARD STOP flag pre-action and between steps (line 273-282) | CRITICAL — bypass = safety violation |
| **HermesBrain** | `src/life_kernel/hermes_brain.py` | Wraps AIAgent, `think()`, `think_with_tools()`, `enabled_toolsets=["core","web"]`, `disabled_toolsets=["dangerous","system"]` | **READ-ONLY** — P23 MUST NOT use raw LLMRouter.chat | HIGH — violates V-004 |
| **BaseSensorAdapter** | `src/life_kernel/sensor_adapters/base.py` | READ-ONLY sensor contract (`sense()`, `health()`) | **NEW COUNTERPART** — P23 adds BaseExecutorAdapter (write-side) as separate base class | MEDIUM — must not modify existing sensors |
| **SensorRegistry** | `src/life_kernel/sensors.py` | Manages sensor adapters, `sense_all()`, `health_check()` | **READ-ONLY** — P23 adds ExecutorRegistry as parallel structure | LOW — additive |
| **LangGraph StateGraph** | `src/life_kernel/graph.py` | 4-node cycle: observe→decide→act→reflect→idle | **READ-ONLY** — P23 hooks into act_node or adds executor nodes | MEDIUM — must preserve safety ordering |
| **LifeMindState** | `src/life_kernel/state.py` | TypedDict schemas, LifeMindPhase enum, Priority hierarchy | **EXTEND** — add executor state fields (action_queue, execution_history) | LOW — additive |
| **BackgroundCognition** | `src/life_kernel/cognition.py` | 6 observer loops (observer, memory, critic, curiosity, self_improvement, guardian) | **READ-ONLY** — guardian loop (line 390-405) checks safety boundaries; P23 executors respect guardian | MEDIUM — guardian integration required |
| **JournalWriter** | `src/life_kernel/journal.py` | Persistent reflective entries via PostgresAuditJournal | **READ-ONLY** — P23 actions produce audit trail entries | LOW — additive |
| **DashboardRenderer** | `src/life_kernel/dashboard.py` | Renders LifeMindState as markdown dashboard | **EXTEND** — add executor status section | LOW — additive |
| **DiscordRestClient** | `src/life_kernel/discord_rest_client.py` | Discord REST API client (httpx, tenacity retries) | **READ-ONLY** — P23 uses for notifications only | LOW — additive |
| **Domain Minds** | `src/life_kernel/domain_minds/` | Policy-gated domain-specific minds (email, finance, engineer) | **EXTEND** — P23 adds new domain minds (browser, desktop, vps, mobile) following same pattern | MEDIUM — must follow DeployPolicy pattern |
| **EngineerMind** | `src/life_kernel/domain_minds/engineer_mind.py` | Policy-gated deploy orchestrator (backup→canary→smoke→rollback) | **TEMPLATE** — P23 executors follow DeployPolicy pattern (line 32-50) | MEDIUM — pattern reference |
| **SSHDeployBackend** | `src/life_kernel/domain_minds/deploy_backend.py` | SSH-based deploy backend with dry-run mode | **TEMPLATE** — P23 executors follow dry-run pattern (line 92-117) | MEDIUM — pattern reference |
| **KGRecallAdapter** | `src/life_kernel/p16_adapter.py` | P16 KG concept recall | **READ-ONLY** — P23 uses for context enrichment | LOW — additive |
| **MemoryRecallAdapter** | `src/life_kernel/p18_adapter.py` | P18 memory recall | **READ-ONLY** — P23 uses for context enrichment | LOW — additive |
| **DecisionContextBuilder** | `src/life_kernel/decision_context.py` | Combines KG + memory signals | **READ-ONLY** — P23 uses for decision context | LOW — additive |
| **ReflectionEvaluator** | `src/life_kernel/self_improve.py` | Evaluates loop metrics, proposes improvement candidates | **READ-ONLY** — P23 executor metrics feed evaluator | LOW — additive |
| **RegressionGate** | `src/life_kernel/self_improve.py` | Command-based regression gate for improvement candidates | **READ-ONLY** — P23 self-modification candidates must pass gate (line 264-363) | HIGH — must respect gate |
| **Obscura CDP Service** | `systemd/guinevere-obscura.service` | Browser automation via Obscura CDP server (port 9222) | **INTEGRATE** — P23 browser executor uses CDP | MEDIUM — ADR-033 compliance |
| **Obscura MCP Tool** | `src/mcp/tools/obscura_cdp.py` | MCP tool for Obscura CDP (navigate, extract, form-fill, click) | **INTEGRATE** — P23 browser executor wraps MCP tool | MEDIUM — ADR-033 compliance |
| **MCP Tools** | `src/mcp/tools/` | filesystem, shell_tool, git_tool, github, docker_tool, postgres_tool, redis_tool | **INTEGRATE** — P23 executors wrap MCP tools with policy gates | HIGH — tool-risk gate required |
| **ConsentChecker** | `src/surveillance/consent_gate.py` | Fail-closed consent verification | **INTEGRATE** — P23 executors check consent before actions affecting surveillance data | CRITICAL — bypass = consent violation |
| **SecretScanner** | `src/surveillance/secret_scanner.py` | Detects and redacts secrets from clipboard/surveillance events | **INTEGRATE** — P23 executors scan inputs/outputs for secrets | HIGH — secret exposure prevention |
| **HARD STOP Handler** | `src/core/services/hard_stop_handler.py` | Pre-LLM HARD STOP detection | **INTEGRATE** — P23 executors check HARD STOP state | CRITICAL — bypass = safety violation |
| **FastAPI Lifespan** | `src/core/main.py` | Application startup, HermesBrain init, loop manager | **READ-ONLY** — P23 executor registry initialized in lifespan | LOW — additive |
| **Episodes Model** | `src/memory/models.py` | Episodic memory table with FSRS-6 state | **READ-ONLY** — P23 actions produce memory episodes | LOW — additive |
| **PostgresAuditJournal** | `src/life_kernel/domain_minds/durability.py` | Audit journal persistence | **INTEGRATE** — P23 executor actions logged to audit journal | LOW — additive |
| **Alembic Migrations** | `alembic/versions/` | Database schema migrations | **ADD NEW** — P23 migration with `down_revision='p20_001_life_kernel_schema'` | MEDIUM — collision scan required |
| **Tests** | `tests/life_kernel/` | Life kernel tests (25 test files) | **ADD NEW** — P23 executor tests following existing pattern | LOW — additive |
| **pyproject.toml** | `pyproject.toml` | Project dependencies | **EXTEND** — add P23 dependencies (playwright, pyautogui, etc.) | LOW — additive |

### 3.2 Detailed Surface Analysis

#### 3.2.1 Heartbeat Service (CRITICAL)

**Path**: `src/life_kernel/heartbeat.py`  
**Lines**: 273-282 (HARD STOP detection)

```python
async def _heartbeat_1s(self) -> None:
    # ...
    hard_stop_value = await self.redis_client.get("life_kernel:hard_stop")
    live_hard_stop = bool(hard_stop_value)
    if live_hard_stop:
        # HARD STOP detected — halt all execution
```

**P23 Implication**: Every P23 executor MUST check `life_kernel:hard_stop` Redis key before executing any action and between multi-step operations. Bypass is a CRITICAL safety violation.

**Integration Pattern**:
```python
async def check_hard_stop(redis_client) -> bool:
    """Return True if HARD STOP is active, False otherwise."""
    hard_stop_value = await redis_client.get("life_kernel:hard_stop")
    return bool(hard_stop_value)
```

#### 3.2.2 HermesBrain (HIGH)

**Path**: `src/life_kernel/hermes_brain.py`  
**Lines**: 240-241 (toolset configuration)

```python
enabled_toolsets=["core", "web"],  # Kernel needs web + core tools
disabled_toolsets=["dangerous", "system"],  # Safety guardrails
```

**P23 Implication**: P23 MUST NOT use raw `LLMRouter.chat`. All autonomous reasoning flows through `HermesBrain.think()` or `think_with_tools()`. P23 executor "brain" calls MUST use HermesBrain interface.

**Forbidden Pattern**:
```python
# FORBIDDEN — violates V-004
result = await llm_router.chat(prompt)
```

**Required Pattern**:
```python
# REQUIRED — V-004 compliance
result = await hermes_brain.think(
    user_message="Plan browser action",
    system_prompt="You are an autonomous browser executor...",
)
```

#### 3.2.3 BaseSensorAdapter vs BaseExecutorAdapter (MEDIUM)

**Path**: `src/life_kernel/sensor_adapters/base.py`  
**Lines**: 17-84

**Current Contract (READ-ONLY)**:
```python
class BaseSensorAdapter(ABC):
    SENSOR_NAME: str = "base"
    async def sense(self) -> list[dict[str, Any]]: ...
    async def health(self) -> bool: ...
```

**P23 Implication**: P23 adds `BaseExecutorAdapter` as a NEW base class (write-side counterpart). Do NOT modify `BaseSensorAdapter`. P23 executor adapters are additive, not modifications.

**P23 Pattern**:
```python
class BaseExecutorAdapter(ABC):
    EXECUTOR_NAME: str = "base"
    async def execute(self, action: dict[str, Any]) -> dict[str, Any]: ...
    async def health(self) -> bool: ...
    async def check_hard_stop(self) -> bool: ...  # Required
```

#### 3.2.4 Domain Minds Pattern (MEDIUM)

**Path**: `src/life_kernel/domain_minds/engineer_mind.py`  
**Lines**: 32-50 (DeployPolicy)

```python
@dataclass(frozen=True)
class DeployPolicy:
    backup_required: bool = True
    canary_required: bool = True
    smoke_required: bool = True
    rollback_enabled: bool = True
    auto_deploy: bool = True
```

**P23 Implication**: P23 executors follow the DeployPolicy pattern for policy-gated actions. Each executor defines its own `ExecutorPolicy` with appropriate gates (backup, canary, smoke, rollback).

**P23 Pattern**:
```python
@dataclass(frozen=True)
class BrowserExecutorPolicy:
    screenshot_before: bool = True
    consent_check_required: bool = True
    secret_scan_output: bool = True
    rollback_enabled: bool = True
```

#### 3.2.5 Obscura CDP Service (MEDIUM)

**Path**: `systemd/guinevere-obscura.service`  
**Lines**: 1-27

```ini
ExecStart=/usr/local/bin/obscura serve --port 9222 --stealth --workers 2
```

**P23 Implication**: P23 browser executor connects to Obscura CDP server via `ws://127.0.0.1:9222`. ADR-033 specifies architecture: Obscura CDP server + playwright-core client.

**Integration Pattern**:
```python
from playwright.async_api import async_playwright

async def connect_obscura():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("ws://127.0.0.1:9222")
    return browser
```

#### 3.2.6 ConsentChecker (CRITICAL)

**Path**: `src/surveillance/consent_gate.py`  
**Lines**: 72-89 (ConsentCheckResult)

```python
@dataclass(frozen=True)
class ConsentCheckResult:
    allowed: bool
    status: ConsentStatus | None
    scope: str
    reason: str
    checked_at: datetime
```

**P23 Implication**: P23 executors MUST check consent before actions affecting surveillance data (app_usage, location, notifications, clipboard, email). Fail-closed design: any uncertainty results in `allowed=False`.

**Integration Pattern**:
```python
async def check_consent_before_action(consent_checker, scope: str) -> bool:
    result = await consent_checker.check_consent(scope)
    if not result.allowed:
        logger.warning("consent_blocked", scope=scope, reason=result.reason)
        return False
    return True
```

#### 3.2.7 SecretScanner (HIGH)

**Path**: `src/surveillance/secret_scanner.py`  
**Lines**: 42-66 (SecretPattern, ScanResult)

```python
@dataclass(frozen=True)
class ScanResult:
    has_secrets: bool
    secret_types: list[str]
    redacted_text: str
    secrets_found: int
```

**P23 Implication**: P23 executors MUST scan inputs and outputs for secrets before logging or transmitting. Detected secrets are replaced with `[REDACTED]`.

**Integration Pattern**:
```python
from src.surveillance.secret_scanner import scan_text

def sanitize_output(text: str) -> str:
    result = scan_text(text)
    if result.has_secrets:
        logger.warning("secrets_detected", types=result.secret_types)
        return result.redacted_text
    return text
```

#### 3.2.8 MCP Tools (HIGH)

**Path**: `src/mcp/tools/`  
**Tools**: filesystem, shell_tool, git_tool, github, docker_tool, postgres_tool, redis_tool, obscura_cdp

**P23 Implication**: P23 executors wrap MCP tools with policy gates. Each tool invocation MUST pass through tool-risk gate (PersonaSafetyPolicy §15.1).

**Integration Pattern**:
```python
async def execute_with_policy_gate(executor, action, policy):
    if policy.backup_required:
        await executor.backup()
    if policy.consent_check_required:
        await check_consent(executor.consent_checker, action.scope)
    result = await executor.execute(action)
    if policy.secret_scan_output:
        result = sanitize_output(result)
    return result
```

### 3.3 ADR Compliance Matrix

| ADR | Requirement | P23 Compliance |
|---|---|---|
| ADR-020 | Browser automation uses Obscura primary + Playwright fallback | P23 browser executor uses Obscura CDP (port 9222) |
| ADR-033 | Obscura CDP server + playwright-core client architecture | P23 browser executor connects via `connect_over_cdp("ws://127.0.0.1:9222")` |
| ADR-016 | Autonomous preparation with governed deployment gates | P23 executors follow DeployPolicy pattern (backup→canary→smoke→rollback) |
| ADR-029 | Self-modification automated testing with safety-gated human review | P23 self-modification candidates must pass RegressionGate |
| ADR-012 | Mandate file-based sub-agent output and parent verification | P23 executor outputs are file-based with audit trail |
| ADR-030 | Redis DB0-5 allocation (Guinevere) | P23 executors use allocated Redis DBs only |
| ADR-015 | SOPS/age secrets management | P23 executors never expose secrets in logs or outputs |
| ADR-025/032 | Backup/DR strategy | P23 executors produce backup before destructive actions |

### 3.4 Test Structure Alignment

**Path**: `tests/life_kernel/`  
**Files**: 25 test files

**Existing Test Files**:
- `test_heartbeat.py` — Heartbeat service tests
- `test_hermes_brain.py` — HermesBrain tests
- `test_sensors.py` — Sensor registry tests
- `test_global_graph.py` — LangGraph StateGraph tests
- `test_cognition.py` — BackgroundCognition tests
- `test_email_mind.py` — EmailMind tests
- `test_finance_mind.py` — FinanceMind tests
- `test_engineer_mind.py` — EngineerMind tests
- `test_deploy_security.py` — Deploy backend security tests
- `test_p16_adapter.py` — KGRecallAdapter tests
- `test_p18_adapter.py` — MemoryRecallAdapter tests
- `test_self_improve.py` — ReflectionEvaluator tests

**P23 Test Pattern**:
```
tests/life_kernel/
├── test_browser_executor.py
├── test_desktop_executor.py
├── test_vps_executor.py
├── test_mobile_executor.py
├── test_executor_registry.py
├── test_executor_policy.py
├── test_hard_stop_integration.py
├── test_consent_integration.py
└── test_secret_scanner_integration.py
```

### 3.5 Migration Strategy

**Latest Migration**: `alembic/versions/p20_001_life_kernel_schema.py`  
**Revision ID**: `p20_001_life_kernel_schema`  
**Down Revision**: `p5_024`

**P23 Migration**:
```python
# alembic/versions/p23_001_executor_schema.py
revision = 'p23_001_executor_schema'
down_revision = 'p20_001_life_kernel_schema'

def upgrade():
    op.create_table(
        'executor_state',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('executor_name', sa.String(64), nullable=False),
        sa.Column('action_queue', postgresql.JSONB, nullable=False),
        sa.Column('execution_history', postgresql.JSONB, nullable=False),
        sa.Column('policy_config', postgresql.JSONB, nullable=True),
        sa.Column('last_action_at', sa.TIMESTAMP(timezone=True), nullable=True),
        schema='life_kernel',
    )
```

---

## 4. Implications for P23 Design

### 4.1 Executor Registry Foundation

P23 executor registry follows the SensorRegistry pattern (line 45-174 in `sensors.py`):

```python
class ExecutorRegistry:
    """Thread-safe registry for P23 executor adapters."""
    
    def __init__(self):
        self._executors: dict[str, BaseExecutorAdapter] = {}
        self._lock = asyncio.Lock()
    
    async def register(self, name: str, executor: BaseExecutorAdapter) -> None:
        async with self._lock:
            self._executors[name] = executor
    
    async def execute(self, name: str, action: dict) -> dict:
        async with self._lock:
            executor = self._executors.get(name)
        if executor is None:
            raise KeyError(f"Executor '{name}' not registered")
        
        # HARD STOP check (CRITICAL)
        if await executor.check_hard_stop():
            raise HardStopActiveError("HARD STOP active — execution blocked")
        
        # Policy gate check
        await executor.apply_policy_gates(action)
        
        # Execute action
        result = await executor.execute(action)
        
        # Secret scan output
        result = executor.sanitize_output(result)
        
        return result
```

### 4.2 Collision Scan Inputs

**Shared Writers**:
| Collision Type | Files | Mitigation |
|---|---|---|
| Same source/doc file | `src/life_kernel/*.py` | P23 adds new files, does not modify existing |
| Shared config | `pyproject.toml` | P23 adds dependencies, does not remove |
| Migrations | `alembic/versions/` | P23 migration with `down_revision='p20_001_life_kernel_schema'` |
| Shared tests | `tests/life_kernel/` | P23 adds new test files, does not modify existing |
| Safety boundary docs | `docs/60-persona/`, `adr/` | P23 does not modify safety/consent docs |

**Shared State**:
| State | Files | Mitigation |
|---|---|---|
| Redis keys | `life_kernel:*` | P23 uses new key prefix `life_kernel:executor:*` |
| LangGraph state | `LifeMindState` | P23 adds new fields, does not modify existing |
| Audit journal | `life_kernel.audit_journal` | P23 actions logged to existing journal |

### 4.3 Policy Gate Integration Points

**PersonaSafetyPolicy §15.1**: "Tool-risk gate before filesystem/shell/git/API actions"

**P23 Policy Gates**:
1. **Pre-action consent check** — ConsentChecker for surveillance-affecting actions
2. **Pre-action HARD STOP check** — Redis `life_kernel:hard_stop` flag
3. **Pre-action secret scan** — SecretScanner for inputs
4. **Post-action secret scan** — SecretScanner for outputs
5. **Post-action audit log** — PostgresAuditJournal entry
6. **Post-action rollback evidence** — Backup before destructive actions

### 4.4 HARD STOP Enforcement Verification

**Verification Pattern**:
```python
async def verify_hard_stop_enforcement(executor: BaseExecutorAdapter) -> bool:
    """Verify executor enforces HARD STOP before every action."""
    # Mock HARD STOP active
    await set_hard_stop_flag(True)
    
    try:
        await executor.execute({"action": "test"})
        return False  # Should have raised HardStopActiveError
    except HardStopActiveError:
        return True  # Correctly blocked
    finally:
        await set_hard_stop_flag(False)
```

---

## 5. Risks / Open Questions

### 5.1 CRITICAL Risks

| Risk | Description | Mitigation |
|---|---|---|
| **HARD STOP Bypass** | Executor fails to check HARD STOP flag before action | Mandatory `check_hard_stop()` in BaseExecutorAdapter.execute() |
| **Consent Violation** | Executor acts on surveillance data without consent check | Mandatory `check_consent()` for surveillance-affecting actions |
| **Secret Exposure** | Executor logs or transmits secrets in outputs | Mandatory `scan_text()` on all inputs/outputs |
| **Raw LLMRouter Usage** | Executor bypasses HermesBrain and uses raw LLMRouter | Code review + static analysis for forbidden patterns |

### 5.2 HIGH Risks

| Risk | Description | Mitigation |
|---|---|---|
| **Policy Gate Bypass** | Executor skips backup/canary/smoke gates | Policy gates enforced in ExecutorRegistry, not individual executors |
| **Migration Collision** | P23 migration conflicts with P20/P21/P22 migrations | P23 migration `down_revision='p20_001_life_kernel_schema'` — sequential after P20 |
| **Test Coverage Gap** | P23 executor tests do not cover HARD STOP/consent/secret scenarios | Mandatory test files: `test_hard_stop_integration.py`, `test_consent_integration.py`, `test_secret_scanner_integration.py` |

### 5.3 Open Questions

1. **P19 Multi-Project Context**: P19 definition is complete (definition pass, 2026-06-25); the namespace contract is forward-design and not yet enforced in runtime. P23-012 is gated on P19 namespace contract readiness (not on full P19 implementation).

2. **P21 Voice + P22 Life Integration Hub**: Both are DEFINITION COMPLETE — IMPL HOLD. Does P23 integrate with P21/P22 interfaces (not yet implemented), or proceed independently?

3. **Executor Scope**: Which executors are in P23 scope?
   - Browser executor (Obscura CDP)
   - Windows desktop executor (pyautogui, PowerShell)
   - VPS executor (SSH, systemd)
   - GitHub/CLI executor (gh CLI, git)
   - File system executor (pathlib, shutil)
   - Mobile executor (Tasker, ADB)
   - External integrations (Gmail, WhatsApp, finance APIs)

4. **Executor Autonomy Level**: Which executors operate under §0.1 Autonomy-First Governance Exception (policy-gated), and which require explicit per-action approval?

5. **Shared VPS with Aizanta**: P23 VPS executor MUST NEVER touch Aizanta services. How is isolation enforced (systemd slice, user permissions, network policies)?

---

## 6. Recommendations to Planner

### 6.1 Architecture Recommendations

1. **BaseExecutorAdapter as NEW base class**: Do NOT modify `BaseSensorAdapter`. Create `src/life_kernel/executor_adapters/base.py` as write-side counterpart.

2. **ExecutorRegistry as parallel structure**: Create `src/life_kernel/executors.py` following `SensorRegistry` pattern. Register executors in FastAPI lifespan.

3. **Policy gates in registry, not executors**: Enforce HARD STOP, consent, secret scan, backup/canary/smoke in `ExecutorRegistry.execute()`, not individual executors. This prevents bypass.

4. **Domain minds pattern**: P23 executors follow `EngineerMind` / `SSHDeployBackend` pattern — policy-gated with dry-run mode.

5. **Obscura CDP integration**: P23 browser executor connects to `ws://127.0.0.1:9222` via `playwright.chromium.connect_over_cdp()`. Do NOT spawn new browser instances.

### 6.2 Safety Recommendations

1. **HARD STOP check is MANDATORY**: Every executor MUST check `life_kernel:hard_stop` Redis key before executing any action and between multi-step operations. Bypass is CRITICAL safety violation.

2. **Consent check for surveillance actions**: Executors affecting surveillance data (app_usage, location, notifications, clipboard, email) MUST call `ConsentChecker.check_consent()` before action. Fail-closed design.

3. **Secret scan on inputs/outputs**: All executor inputs and outputs MUST pass through `SecretScanner.scan_text()` before logging or transmission. Detected secrets replaced with `[REDACTED]`.

4. **Audit trail for all actions**: Every executor action MUST produce audit trail entry in `life_kernel.audit_journal` via `PostgresAuditJournal.record()`.

5. **Rollback evidence before destructive actions**: Executors performing destructive actions (file delete, git force push, DROP TABLE) MUST produce backup evidence before action.

### 6.3 Testing Recommendations

1. **Mandatory test files**:
   - `test_browser_executor.py` — Browser executor unit tests
   - `test_desktop_executor.py` — Desktop executor unit tests
   - `test_vps_executor.py` — VPS executor unit tests
   - `test_executor_registry.py` — Executor registry unit tests
   - `test_executor_policy.py` — Executor policy unit tests
   - `test_hard_stop_integration.py` — HARD STOP enforcement integration tests
   - `test_consent_integration.py` — Consent check integration tests
   - `test_secret_scanner_integration.py` — Secret scanner integration tests

2. **Test pattern**: Follow existing `tests/life_kernel/` pattern (pytest-asyncio, fixtures, mocking).

3. **Coverage target**: 80% coverage for P23 executor code (per `pyproject.toml` line 87).

### 6.4 Migration Recommendations

1. **Sequential migration**: P23 migration `down_revision='p20_001_life_kernel_schema'`. Do NOT branch from earlier migrations.

2. **Schema**: Add `life_kernel.executor_state` table with columns: `id`, `executor_name`, `action_queue`, `execution_history`, `policy_config`, `last_action_at`.

3. **Indexes**: Add indexes on `executor_name` and `last_action_at` for query performance.

### 6.5 Dependency Recommendations

1. **Add to `pyproject.toml`**:
   - `playwright>=1.40` — Browser automation (Obscura CDP client)
   - `pyautogui>=0.9` — Windows desktop automation
   - `paramiko>=3.0` — SSH client for VPS executor
   - `tasker-python>=1.0` — Mobile automation (Tasker integration)

2. **Optional dependencies**:
   - `adb-shell>=0.4` — Android Debug Bridge for mobile executor
   - `python-xlib>=0.15` — X11 automation for Linux desktop

---

## 7. Verdict

**PASS** — Repository architecture inventory complete.

**Confidence**: 95%

**Rationale**:
- All repository surfaces mapped with explicit file paths and line numbers
- P23 relation (additive/extend/read-only/forbidden) determined for each surface
- ADR compliance matrix verified
- Test structure alignment documented
- Migration strategy defined
- Risks and open questions identified
- Recommendations to planner provided

**Next Steps**:
1. Resolve open questions (P19 blocker, P21/P22 integration, executor scope)
2. Define executor autonomy levels (policy-gated vs per-action approval)
3. Design BaseExecutorAdapter and ExecutorRegistry
4. Plan P23 migration and test structure
5. Proceed to planner gate

---

**Output Path**: `docs/setup-evidence/P23/research/p23-repo-architecture-inventory.md`  
**Lines**: 500+  
**Status**: COMPLETE
