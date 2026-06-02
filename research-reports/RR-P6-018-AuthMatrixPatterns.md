# Research Report: 4-Level Authorization Matrix Patterns for MCP Tool Systems

| Field | Value |
|---|---|
| Task | P6-018 Auth Matrix Verification |
| Date | 2026-06-02 |
| Type | Librarian Research — TYPE D (Comprehensive) |
| Status | Complete |
| Evidence Root | `research-reports/` |

---

## 1. Executive Summary

Four production-ready authorization matrix patterns exist for tool/API systems that map cleanly to Guinevere's 4-level model:

| Auth Level | Behavior | Production Analog |
|---|---|---|
| **Read-Auto** | Auto-execute, no approval | `AutoApproveBackend` (PraisonAI) |
| **Write-Notify** | Execute + notify operator | `ConsoleBackend` / WebhookBackend (PraisonAI) |
| **Destructive-Approval** | Require explicit approval before execution | `@require_approval(risk_level="critical")` (PraisonAI) |
| **Forbidden** | Always blocked | `PERMISSION_PRESETS["safe"]` frozenset deny-list |

The **PraisonAI Agents** library (`MervinPraison/PraisonAI`) provides the most complete production implementation of this exact pattern, with a decorator-driven approval system backed by a pluggable protocol-based backend architecture.

---

## 2. Decorator Pattern — `@require_approval` with Risk Levels

### 2.1 The Decorator (Primary Reference)

**Evidence** ([source](https://github.com/MervinPraison/PraisonAI/blob/aaed51eee8c132ec2eea6d2fdc7363cf0d3978a9/src/praisonai-agents/praisonaiagents/approval/__init__.py#L164-L229)):

```python
RiskLevel = Literal["critical", "high", "medium", "low"]

def require_approval(risk_level: RiskLevel = "high"):
    """Decorator to mark a tool as requiring human approval."""
    def decorator(func):
        tool_name = getattr(func, '__name__', str(func))
        reg = get_approval_registry()
        reg.add_requirement(tool_name, risk_level)
        reg._required_tools.add(tool_name)
        reg._risk_levels[tool_name] = risk_level

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Fast paths: already approved, YAML-approved, env auto-approve
            if is_already_approved(tool_name):
                return func(*args, **kwargs)
            if is_yaml_approved(tool_name):
                mark_approved(tool_name)
                return func(*args, **kwargs)
            if is_env_auto_approve():
                mark_approved(tool_name)
                return func(*args, **kwargs)
            # Full approval flow
            decision = run_coroutine_from_any_context(
                request_approval(tool_name, kwargs)
            )
            if not decision.approved:
                raise PermissionError(
                    f"Execution of {tool_name} denied: {decision.reason}"
                )
            mark_approved(tool_name)
            kwargs.update(decision.modified_args)
            return func(*args, **kwargs)

        # Also provides async_wrapper for async functions
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    return decorator
```

### 2.2 Usage in Production Tools

**Evidence** ([shell_tools.py](https://github.com/MervinPraison/PraisonAI/blob/aaed51eee8c132ec2eea6d2fdc7363cf0d3978a9/src/praisonai-agents/praisonaiagents/tools/shell_tools.py#L32)):
```python
@require_approval(risk_level="critical")
def execute_command(self, command: str, cwd=None, timeout=30, ...):
    """Execute a shell command safely."""
```

**Evidence** ([file_tools.py](https://github.com/MervinPraison/PraisonAI/blob/aaed51eee8c132ec2eea6d2fdc7363cf0d3978a9/src/praisonai-agents/praisonaiagents/tools/file_tools.py#L101)):
```python
@require_approval(risk_level="high")
def write_file(self, filepath: str, content: str, encoding: str = 'utf-8') -> bool:
    """Write content to a file."""
```

**Evidence** ([delegation_tools.py](https://github.com/MervinPraison/PraisonAI/blob/aaed51eee8c132ec2eea6d2fdc7363cf0d3978a9/src/praisonai-agents/praisonaiagents/tools/delegation_tools.py#L26)):
```python
@require_approval(risk_level="medium")
def delegate_task(self, task_description: str, agent_type: str = "general", ...):
    """Delegate a task to a sub-agent."""
```

### 2.3 Risk Level Mapping to Guinevere's 4 Levels

| Guinevere Level | PraisonAI `risk_level` | Behavior |
|---|---|---|
| Read-Auto | `"low"` or not in `DEFAULT_DANGEROUS_TOOLS` | Auto-execute, no gate |
| Write-Notify | `"medium"` | Execute + notify (webhook backend) |
| Destructive-Approval | `"high"` or `"critical"` | Block until approved |
| Forbidden | In deny-list frozenset | Always `PermissionError` |

---

## 3. Registry & Protocol Pattern — Centralized Auth State

### 3.1 Approval Registry (Singleton)

**Evidence** ([registry.py](https://github.com/MervinPraison/PraisonAI/blob/aaed51eee8c132ec2eea6d2fdc7363cf0d3978a9/src/praisonai-agents/praisonaiagents/approval/registry.py#L77-L112)):

```python
class ApprovalRegistry:
    """Per-agent approval configuration."""

    def __init__(self) -> None:
        self._global_backend = None
        self._agent_backends: Dict[str, object] = {}
        self._required_tools: Set[str] = set()
        self._risk_levels: Dict[str, str] = {}
        self._agent_tool_auto_approve: Dict[tuple[str, str], bool] = {}
        # Context variables (per-coroutine / per-thread)
        self._approved_context: contextvars.ContextVar[Set[str]] = contextvars.ContextVar(
            "approved_context", default=set()
        )
        self.timeout: float = 300.0
```

### 3.2 Default Dangerous Tools Matrix

**Evidence** ([registry.py L31-47](https://github.com/MervinPraison/PraisonAI/blob/aaed51eee8c132ec2eea6d2fdc7363cf0d3978a9/src/praisonai-agents/praisonaiagents/approval/registry.py#L31-L47)):

```python
DEFAULT_DANGEROUS_TOOLS: Dict[str, str] = {
    "execute_command": "critical",
    "kill_process": "critical",
    "execute_code": "critical",
    "write_file": "high",
    "delete_file": "high",
    "move_file": "high",
    "copy_file": "high",
    "execute_query": "high",
    "evaluate": "medium",
    "crawl": "medium",
    "scrape_page": "medium",
}
```

### 3.3 Permission Presets (Forbidden = Deny Frozenset)

**Evidence** ([registry.py L61-75](https://github.com/MervinPraison/PraisonAI/blob/aaed51eee8c132ec2eea6d2fdc7363cf0d3978a9/src/praisonai-agents/praisonaiagents/approval/registry.py#L61-L75)):

```python
PERMISSION_PRESETS = {
    "default": frozenset({
        "execute_command", "kill_process", "execute_code",
        "delete_file", "move_file", "copy_file",
    }),
    "safe": frozenset(DEFAULT_DANGEROUS_TOOLS.keys()),  # blocks ALL dangerous
    "read_only": frozenset(DEFAULT_DANGEROUS_TOOLS.keys()),
    "full": frozenset(),   # no restrictions
    "off": frozenset(),    # alias of full
}
```

**Key insight**: The `frozenset` pattern provides the **Forbidden** level — tools in this set are always blocked. The `DEFAULT_DANGEROUS_TOOLS` dict provides the risk classification for everything else.

### 3.4 Approval Decision Flow (Fast-Path Chain)

**Evidence** ([registry.py L209-261](https://github.com/MervinPraison/PraisonAI/blob/aaed51eee8c132ec2eea6d2fdc7363cf0d3978a9/src/praisonai-agents/praisonaiagents/approval/registry.py#L209-L261)):

```python
def approve_sync(self, agent_name, tool_name, arguments):
    # 1. Not required → auto-approve
    if not self.is_required(tool_name):
        return ApprovalDecision(approved=True, reason="No approval required")
    # 2. Already approved in context → skip
    if self.is_already_approved(tool_name):
        return ApprovalDecision(approved=True, reason="Already approved")
    # 3. Per-agent auto-approve → skip
    if self.is_auto_approved(tool_name, agent_name):
        self.mark_approved(tool_name)
        return ApprovalDecision(approved=True, reason="Auto-approved (skill)")
    # 4. Env var auto-approve → skip
    if self.is_env_auto_approve():
        ...
    # 5. YAML config auto-approve → skip
    if self.is_yaml_approved(tool_name):
        ...
    # 6. Delegate to backend (console, webhook, agent, etc.)
    backend = self.get_backend(agent_name)
    request = ApprovalRequest(tool_name=tool_name, arguments=arguments, ...)
    decision = backend.request_approval_sync(request)
    if decision.approved:
        self.mark_approved(tool_name)
    return decision
```

---

## 4. Approval Protocol — Pluggable Backend Architecture

### 4.1 Protocol Contract

**Evidence** ([protocols.py](https://github.com/MervinPraison/PraisonAI/blob/aaed51eee8c132ec2eea6d2fdc7363cf0d3978a9/src/praisonai-agents/praisonaiagents/approval/protocols.py#L84-L112)):

```python
@runtime_checkable
class ApprovalProtocol(Protocol):
    """Protocol for tool-execution approval backends.
    
    Implement request_approval to create custom approval channels:
    - Console prompts
    - Webhook / HTTP callbacks
    - Messaging platform replies (Slack, Discord, Telegram)
    - External UI dashboards
    - Auto-approve policies
    """
    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        ...
```

### 4.2 Request & Decision Dataclasses

**Evidence** ([protocols.py L16-52](https://github.com/MervinPraison/PraisonAI/blob/aaed51eee8c132ec2eea6d2fdc7363cf0d3978a9/src/praisonai-agents/praisonaiagents/approval/protocols.py#L16-L52)):

```python
@dataclass
class ApprovalRequest:
    tool_name: str
    arguments: Dict[str, Any]
    risk_level: str           # "critical" | "high" | "medium" | "low"
    agent_name: Optional[str] = None
    session_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ApprovalDecision:
    approved: bool
    reason: str = ""
    modified_args: Dict[str, Any] = field(default_factory=dict)
    approver: Optional[str] = None      # "user", "system", "webhook", ...
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 4.3 Built-in Backends

**Evidence** ([backends.py](https://github.com/MervinPraison/PraisonAI/blob/aaed51eee8c132ec2eea6d2fdc7363cf0d3978a9/src/praisonai-agents/praisonaiagents/approval/backends.py)):

| Backend | Pattern | Use Case |
|---|---|---|
| `AutoApproveBackend` | Always returns `approved=True` | Read-Auto level, test envs |
| `ConsoleBackend` | Rich terminal prompt (yes/no) | CLI interactive approval |
| `CallbackBackend` | Wraps legacy callback function | Backward compatibility |
| `AgentApproval` | Delegates to another AI agent | Multi-agent approval chain |

```python
class AutoApproveBackend:
    """Always approves. Use for bots or trusted unattended environments."""
    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        return ApprovalDecision(approved=True, reason="auto-approved", approver="system")

class ConsoleBackend:
    """Interactive Rich terminal prompt. Default for CLI usage."""
    def _prompt_user(self, request: ApprovalRequest) -> bool:
        risk_colors = {
            "critical": "bold red",
            "high": "red",
            "medium": "yellow",
            "low": "blue",
        }
        # Shows Rich Panel with tool info, asks Confirm
        return Confirm.ask(f"Do you want to execute this {request.risk_level} risk tool?")

class AgentApproval:
    """Delegates approval decisions to another AI agent."""
    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        prompt = self._build_prompt(request)
        response = await approver.achat(prompt)
        approved = "APPROVE" in response and "DENY" not in response
        return ApprovalDecision(approved=approved, ...)
```

---

## 5. Discord Webhook Notification Pattern

### 5.1 Apache Airflow Pattern (Production Reference)

**Evidence** ([airflow discord hook](https://github.com/apache/airflow/blob/main/providers/discord/src/airflow/providers/discord/hooks/discord_webhook.py)):

Airflow implements `DiscordWebhookHook` and `DiscordWebhookAsyncHook` for async Discord notifications. The pattern uses `aiohttp.ClientSession` to POST to Discord webhook URLs with embed payloads.

### 5.2 Custom Discord Notification Backend (Recommended Pattern for Guinevere)

Based on PraisonAI's `ApprovalProtocol` and production Discord webhook patterns:

```python
import aiohttp
from dataclasses import dataclass
from praisonaiagents.approval.protocols import ApprovalProtocol, ApprovalRequest, ApprovalDecision

class DiscordWebhookBackend:
    """Send approval request via Discord webhook. Blocks until operator responds."""
    
    def __init__(self, webhook_url: str, channel_id: str, bot_token: str):
        self.webhook_url = webhook_url
        self.channel_id = channel_id
        self.bot_token = bot_token
        self._pending: dict[str, asyncio.Future] = {}

    async def send_notification(self, request: ApprovalRequest) -> str:
        """Send Discord embed notification, return message_id for tracking."""
        risk_colors = {"critical": 0xFF0000, "high": 0xFF6B6B, "medium": 0xFFD93D, "low": 0x6BCB77}
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "embeds": [{
                    "title": f"🔒 Tool Approval Required: {request.tool_name}",
                    "description": f"**Risk Level:** {request.risk_level.upper()}\n"
                                   f"**Agent:** {request.agent_name}\n"
                                   f"**Arguments:** ```{json.dumps(request.arguments, indent=2)[:1000]}```",
                    "color": risk_colors.get(request.risk_level, 0xCCCCCC),
                    "timestamp": datetime.utcnow().isoformat(),
                }],
                "components": [
                    {"type": 1, "components": [
                        {"type": 2, "style": 3, "label": "✅ Approve", "custom_id": f"approve:{request.tool_name}"},
                        {"type": 2, "style": 4, "label": "❌ Deny", "custom_id": f"deny:{request.tool_name}"},
                    ]}
                ]
            }
            async with session.post(self.webhook_url, json=payload) as resp:
                if resp.status == 204:
                    return "sent"
                raise RuntimeError(f"Discord webhook failed: {resp.status}")

    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        """Send notification, wait for Discord button interaction."""
        await self.send_notification(request)
        # Wait for callback from Discord interaction endpoint
        future = asyncio.get_event_loop().create_future()
        self._pending[request.tool_name] = future
        try:
            decision = await asyncio.wait_for(future, timeout=300.0)
            return decision
        except asyncio.TimeoutError:
            return ApprovalDecision(approved=False, reason="Approval timed out (300s)")

    def handle_interaction(self, custom_id: str, user_id: str):
        """Called by Discord interaction handler to resolve pending approval."""
        action, tool_name = custom_id.split(":", 1)
        if tool_name in self._pending:
            approved = action == "approve"
            self._pending[tool_name].set_result(
                ApprovalDecision(
                    approved=approved,
                    reason=f"{'Approved' if approved else 'Denied'} by {user_id}",
                    approver=user_id,
                )
            )
            del self._pending[tool_name]
```

### 5.3 Fire-and-Forget Notify Pattern (Write-Notify Level)

For the **Write-Notify** level (execute immediately, notify operator after):

```python
async def notify_operator(action: str, tool_name: str, result: str, webhook_url: str):
    """Fire-and-forget Discord notification for Write-Notify level."""
    async with aiohttp.ClientSession() as session:
        payload = {
            "embeds": [{
                "title": f"📋 Tool Executed: {tool_name}",
                "description": f"**Action:** {action}\n**Result:** {result[:500]}",
                "color": 0x3498DB,
                "timestamp": datetime.utcnow().isoformat(),
            }]
        }
        async with session.post(webhook_url, json=payload) as resp:
            if resp.status not in (200, 204):
                logger.warning(f"Notification failed: {resp.status}")
```

---

## 6. Audit Logging Patterns

### 6.1 structlog Pattern (ReadTheDocs Production)

**Evidence** ([readthedocs audit](https://github.com/readthedocs/readthedocs.org/blob/main/readthedocs/audit/apps.py)):

```python
import structlog
log = structlog.get_logger(__name__)

# Usage:
log.info("tool_executed", tool_name="execute_command", risk_level="critical",
         agent_name="worker", approved_by="console", arguments_hash="abc123")
```

### 6.2 Structured AuditLogger Class (OmniAgent Pattern)

**Evidence** ([omniagent audit.py](https://github.com/YeQing17-2026/OmniAgent/blob/main/omniagent/security/audit.py#L39)):

```python
class AuditLogger:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        event_type: str,      # "tool_call", "command_exec", "approval_request"
        action: str,          # "execute", "approve", "deny"
        user_id: str,         # operator or agent identifier
        session_id: str,      # session context
        success: bool,        # whether action succeeded
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "action": action,
            "user_id": user_id,
            "session_id": session_id,
            "success": success,
            "details": details or {},
        }
        # Write to JSONL file with rotation
```

### 6.3 Sentry-Style Named Logger Pattern

**Evidence** ([sentry](https://github.com/getsentry/sentry/blob/master/src/sentry/users/api/endpoints/user_details.py)):

```python
audit_logger = logging.getLogger("sentry.audit.user")
# Separate logger for audit events, can be routed to different handlers/files
```

### 6.4 Recommended Audit Pattern for Guinevere

```python
import structlog
from datetime import datetime, timezone

audit_log = structlog.get_logger("guinevere.audit.tool_auth")

def audit_tool_execution(
    tool_name: str,
    auth_level: str,
    action: str,          # "auto_execute" | "notify" | "approval_requested" | "approved" | "denied" | "forbidden"
    operator: str = "system",
    arguments_hash: str = "",
    session_id: str = "",
    result: str = "",
):
    audit_log.info(
        "tool_auth_event",
        tool_name=tool_name,
        auth_level=auth_level,
        action=action,
        operator=operator,
        arguments_hash=arguments_hash,
        session_id=session_id,
        result=result,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
```

---

## 7. Microsoft Agent Governance Toolkit — Approval Handler Pattern

**Evidence** ([microsoft/agent-governance-toolkit](https://github.com/microsoft/agent-governance-toolkit/blob/main/agent-governance-python/agent-mesh/src/agentmesh/governance/approval.py)):

```python
@dataclass
class ApprovalDecision:
    approved: bool
    approver: str = ""
    reason: str = ""
    decided_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class ApprovalHandler(ABC):
    @abstractmethod
    def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        """Request approval for a policy-gated action."""

class AutoRejectApproval(ApprovalHandler):
    """Automatically rejects all approval requests (fail-safe default)."""
```

**Key insight**: Microsoft uses an ABC (not Protocol) with `AutoRejectApproval` as the fail-safe default — if no handler is configured, everything is denied. This is the correct fail-closed pattern for Guinevere's Forbidden level.

---

## 8. Hyperledger Indy-Node — Multi-Level Auth Constraint

**Evidence** ([indy-node authorizer](https://github.com/hyperledger/indy-node/blob/main/indy_common/authorize/authorizer.py)):

```python
class AbstractAuthorizer(metaclass=ABCMeta):
    def authorize(self, request, auth_constraint, auth_action) -> (bool, str):
        raise NotImplementedError()

class AuthConstraint:
    # Defines required role, signature count, and other constraints
    # authorize() checks: sig_count >= auth_constraint.sig_count
```

This pattern shows how to compose constraints — each tool can have a constraint that checks role, signature count, and other conditions.

---

## 9. Test Pattern — Verifying Decorator Enforcement

**Evidence** ([test_decorator_enforcement.py](https://github.com/MervinPraison/PraisonAI/blob/aaed51eee8c132ec2eea6d2fdc7363cf0d3978a9/src/praisonai/tests/unit/test_decorator_enforcement.py)):

```python
def test_decorator_enforcement():
    from praisonaiagents.approval import require_approval, set_approval_callback, ApprovalDecision
    
    def auto_deny_callback(function_name, arguments, risk_level):
        return ApprovalDecision(approved=False, reason="Test denial")
    
    set_approval_callback(auto_deny_callback)
    
    @require_approval(risk_level="critical")
    def test_function(command: str) -> str:
        return f"Executed: {command}"
    
    try:
        result = test_function("dangerous command")
        assert False, "Should have been denied!"
    except PermissionError:
        pass  # ✅ Correctly blocked
```

---

## 10. Recommended Architecture for Guinevere P6-018

### 10.1 Auth Level Enum & Tool Matrix

```python
from enum import Enum
from typing import Dict

class AuthLevel(str, Enum):
    READ_AUTO = "read_auto"           # Auto-execute, no gate
    WRITE_NOTIFY = "write_notify"     # Execute + Discord notification
    DESTRUCTIVE_APPROVAL = "destructive_approval"  # Block until approved
    FORBIDDEN = "forbidden"           # Always blocked

# Tool → AuthLevel mapping (16 tools)
TOOL_AUTH_MATRIX: Dict[str, AuthLevel] = {
    "discord_search":        AuthLevel.READ_AUTO,
    "discord_get_messages":  AuthLevel.READ_AUTO,
    "memory_recall":         AuthLevel.READ_AUTO,
    "memory_search":         AuthLevel.READ_AUTO,
    "web_search":            AuthLevel.READ_AUTO,
    "web_fetch":             AuthLevel.READ_AUTO,
    "surveillance_get":      AuthLevel.WRITE_NOTIFY,
    "memory_store":          AuthLevel.WRITE_NOTIFY,
    "memory_update":         AuthLevel.WRITE_NOTIFY,
    "discord_send":          AuthLevel.WRITE_NOTIFY,
    "discord_react":         AuthLevel.WRITE_NOTIFY,
    "file_write":            AuthLevel.DESTRUCTIVE_APPROVAL,
    "file_delete":           AuthLevel.DESTRUCTIVE_APPROVAL,
    "shell_execute":         AuthLevel.DESTRUCTIVE_APPROVAL,
    "system_config":         AuthLevel.DESTRUCTIVE_APPROVAL,
    "surveillance_start":    AuthLevel.FORBIDDEN,  # example — adjust per spec
}
```

### 10.2 Enforcement Middleware Pattern

```python
import structlog
audit_log = structlog.get_logger("guinevere.audit.tool_auth")

class AuthEnforcer:
    def __init__(self, matrix: Dict[str, AuthLevel], notifier, approval_backend):
        self.matrix = matrix
        self.notifier = notifier          # DiscordWebhookNotifier
        self.approval_backend = approval_backend  # ApprovalProtocol

    async def enforce(self, tool_name: str, arguments: dict, context: dict) -> bool:
        level = self.matrix.get(tool_name, AuthLevel.FORBIDDEN)
        
        # Audit: log the attempt
        audit_log.info("tool_auth_attempt", tool=tool_name, level=level,
                       session=context.get("session_id"))
        
        if level == AuthLevel.READ_AUTO:
            audit_log.info("tool_auth_auto", tool=tool_name, level=level)
            return True

        if level == AuthLevel.WRITE_NOTIFY:
            # Execute immediately, notify after
            audit_log.info("tool_auth_notify_exec", tool=tool_name)
            # (caller proceeds with execution)
            await self.notifier.notify_write(tool_name, arguments, context)
            return True

        if level == AuthLevel.DESTRUCTIVE_APPROVAL:
            # Block until approved
            decision = await self.approval_backend.request_approval(
                ApprovalRequest(tool_name=tool_name, arguments=arguments,
                                risk_level="critical", agent_name=context.get("agent"))
            )
            audit_log.info("tool_auth_decision", tool=tool_name,
                           approved=decision.approved, approver=decision.approver)
            if not decision.approved:
                raise PermissionError(f"Destructive tool {tool_name} denied: {decision.reason}")
            return True

        if level == AuthLevel.FORBIDDEN:
            audit_log.warning("tool_auth_forbidden", tool=tool_name,
                              session=context.get("session_id"))
            raise PermissionError(f"Tool {tool_name} is FORBIDDEN")
        
        return False
```

### 10.3 Key Design Decisions

| Decision | Pattern Source | Rationale |
|---|---|---|
| `frozenset` deny-list for Forbidden | PraisonAI `PERMISSION_PRESETS` | Immutable, fast membership check |
| `contextvars.ContextVar` for approved state | PraisonAI `ApprovalRegistry` | Thread-safe, async-safe per-coroutine state |
| `Protocol` (structural subtyping) for backends | PraisonAI `ApprovalProtocol` | No inheritance required, duck-typing friendly |
| Fail-closed default | Microsoft `AutoRejectApproval` | If no handler configured → deny |
| `asyncio.wait_for` with timeout | PraisonAI `approve_async` | Prevents infinite blocking on approval |
| `structlog` with named loggers | ReadTheDocs audit | Structured JSON output, queryable in Loki |
| `@require_approval` decorator | PraisonAI | Declarative, colocated with tool definition |

---

## 11. Source Repositories

| Repository | License | Relevance |
|---|---|---|
| [MervinPraison/PraisonAI](https://github.com/MervinPraison/PraisonAI) | MIT | Complete approval system (decorator, registry, protocol, backends) |
| [microsoft/agent-governance-toolkit](https://github.com/microsoft/agent-governance-toolkit) | MIT | Approval handler ABC, fail-safe defaults |
| [apache/airflow](https://github.com/apache/airflow) | Apache-2.0 | Discord webhook async hook |
| [readthedocs/readthedocs.org](https://github.com/readthedocs/readthedocs.org) | MIT | structlog audit logging |
| [YeQing17-2026/OmniAgent](https://github.com/YeQing17-2026/OmniAgent) | Unknown | AuditLogger class with structured events |
| [HKUDS/OpenHarness](https://github.com/HKUDS/OpenHarness) | MIT | MCP-specific auth tool |
| [hyperledger/indy-node](https://github.com/hyperledger/indy-node) | Apache-2.0 | Multi-level auth constraint composition |
| [TracecatHQ/tracecat](https://github.com/TracecatHQ/tracecat) | AGPL-3.0 | ApprovalDecision with override_args |
| [langgenius/dify](https://github.com/langgenius/dify) | Unknown | MCP tools management service |

---

## 12. Next Steps for P6-018 Implementation

1. **Define `TOOL_AUTH_MATRIX`** — Map all 16 Guinevere tools to `AuthLevel` enum values
2. **Implement `AuthEnforcer` middleware** — Using the fast-path chain pattern from PraisonAI
3. **Create `DiscordWebhookBackend`** — Implementing `ApprovalProtocol` for Destructive-Approval level
4. **Create `DiscordNotifyBackend`** — Fire-and-forget notification for Write-Notify level
5. **Wire `structlog` audit logger** — Named `guinevere.audit.tool_auth`, structured JSONL output
6. **Write enforcement tests** — Following PraisonAI's `test_decorator_enforcement.py` pattern
7. **Add `FORBIDDEN` frozenset** — Immutable deny-list checked before any other level

---

*Report generated by Librarian agent for P6-018 auth matrix verification.*
*All permalinks verified as of commit aaed51eee8c132ec2eea6d2fdc7363cf0d3978a9 (PraisonAI main).*
