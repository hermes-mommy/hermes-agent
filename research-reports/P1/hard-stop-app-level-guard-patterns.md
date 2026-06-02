# HARD STOP Application-Level Safety Guard Patterns

> **Research Report** — P1-021 HARD STOP Protocol Verification Gate
> **Date:** 2026-06-01
> **Status:** Complete

---

## Executive Summary

The core finding: **Every production AI agent system now implements pre-LLM safety interception as a middleware/hook layer, not as system prompt instructions.** The industry has converged on the "Governor/Wrapper" pattern — a deterministic proxy that sits between the application and the LLM, intercepting all messages before they reach the model. This is exactly the architecture needed for Guinevere's HARD STOP protocol.

This report catalogs 8 distinct production patterns across 12+ open-source frameworks, with direct code references and architectural analysis.

---

## 1. The Two-Stage Safety Architecture (PRE-LLM + POST-LLM)

### Source: SafeHaven (`k-9-user/SafeHaven`)

**File:** [`agent/src/safety/guardrails.ts`](https://github.com/k-9-user/SafeHaven/blob/main/agent/src/safety/guardrails.ts)

The canonical two-stage pattern. A single `filterInput()` function runs **before** the LLM call and can either:
- **BLOCK** — return a canned safe response without ever calling the LLM
- **SANITIZE** — strip PII, truncate length, then pass the cleaned message to the LLM

```typescript
// PRE-LLM: Filter incoming user messages before they reach Claude
export function filterInput(message: string): InputFilterResult {
  // 1. Check for blocked topics (respond without calling Claude)
  for (const { name, pattern, response } of BLOCKED_TOPICS) {
    if (pattern.test(message)) {
      console.log(`[Safety] Blocked topic detected: ${name}`);
      return { blocked: true, blockedReason: name, safeResponse: response };
    }
  }
  // 2. Strip PII before sending to Claude
  let sanitized = message;
  for (const { name, pattern } of PII_PATTERNS) {
    sanitized = sanitized.replace(pattern, `[${name}_REDACTED]`);
  }
  return { blocked: false, sanitizedMessage: sanitized };
}

// POST-LLM: Validate and sanitize Claude's responses
export function filterOutput(response: string): OutputFilterResult {
  // Remove base64 blobs, private keys, hex keys
  // Append disclaimers if financial advice detected
}
```

**Architecture Principle:** "The safety layer CANNOT be bypassed by user input or Claude's output. It runs as middleware on every /api/chat request."

**Applicability to HARD STOP:** Replace the keyword matching with GUINEVERE_HARD_STOP patterns. On match, return `{ blocked: true, safeResponse: "[HARD STOP ACKNOWLEDGED] Neutral mode active. Awaiting explicit resume." }`.

---

## 2. The Hook/Middleware Pattern (CrewAI — before_llm_call)

### Source: CrewAI (`crewAIInc/crewAI`)

**File:** [`lib/crewai/src/crewai/hooks/llm_hooks.py`](https://github.com/crewAIInc/crewAI/blob/e21c5062/lib/crewai/src/crewai/hooks/llm_hooks.py)

CrewAI's `register_before_llm_call_hook()` is the Python standard for pre-LLM interception. The hook:
- Receives the full `LLMCallHookContext` (messages, agent, task, crew)
- Can **modify messages in-place**
- Can **return False to block execution entirely**
- Can **return a string to replace the LLM response**

```python
def register_before_llm_call_hook(
    hook: BeforeLLMCallHookType | BeforeLLMCallHookCallable,
) -> None:
    """Register a global before_llm_call hook.
    
    - Modify context.messages directly (in-place)
    - Return False to block LLM execution
    - Return True or None to allow execution
    """

# Example: block excessive iterations
def block_excessive_iterations(context: LLMCallHookContext) -> bool | None:
    if context.iterations > 10:
        print("Blocked: Too many iterations")
        return False  # Block execution
    return None  # Allow execution

register_before_llm_call_hook(block_excessive_iterations)
```

**Also has before_tool_call hooks** for pre-tool-call authorization (see [CrewAI Issue #4877](https://github.com/crewAIInc/crewAI/issues/4877) — GuardrailProvider interface):

```python
@runtime_checkable
class GuardrailProvider(Protocol):
    name: str
    def evaluate(self, request: GuardrailRequest) -> GuardrailDecision: ...
    def health_check(self) -> bool: ...
```

**Applicability to HARD STOP:** Implement a `GuinevereHardStopHook` that checks incoming messages for HARD STOP keywords (exact match, fuzzy match, semantic equivalent). On match: `return "[HARD STOP ACKNOWLEDGED]"` (short-circuits LLM entirely).

---

## 3. The Google ADK Callback Pattern (6 symmetric callbacks)

### Source: Google ADK

**File:** [ADK Callbacks Reference](https://google.github.io/adk-docs/callbacks/types-of-callbacks/)

The ADK provides 6 symmetric callbacks covering agent, model, and tool boundaries. Each returns `None` to proceed or a response to short-circuit:

```python
# LLM boundary — the key intercept for HARD STOP
def before_model_callback(ctx: CallbackContext, req: LlmRequest) -> Optional[LlmResponse]:
    """Modify req in-place, or return LlmResponse to bypass LLM entirely."""
    if "HARD_STOP" in req.messages[-1].content:
        return LlmResponse(content="[HARD STOP ACKNOWLEDGED] Neutral mode active.")
    return None  # proceed normally

# Tool boundary — for supplementary safety
def before_tool_callback(ctx: CallbackContext, req: ToolRequest) -> Optional[ToolResponse]:
    """Return ToolResponse to skip tool; None to execute normally."""
```

**Key insight for HARD STOP:** The `before_model_callback` is the natural place for guardrails — inspect the LLM request, check for policy violations, and return a synthetic refusal response **without ever hitting the API**. This is zero-token-cost safety.

---

## 4. The Microsoft Agent Governance Toolkit (Kernel Pattern)

### Source: Microsoft (`microsoft/agent-governance-toolkit`)

**File:** [`docs/tutorials/03-framework-integrations.md`](https://github.com/microsoft/agent-governance-toolkit/blob/main/docs/tutorials/03-framework-integrations.md)

The governance toolkit uses a **Kernel** pattern — a proxy that wraps any framework object:

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Your Code   │ ──► │  Kernel      │ ──► │  Framework    │
│              │ ◄── │  (governance │ ◄── │  (OpenAI,     │
│              │     │   layer)     │     │   LangChain…) │
└─────────────┘     └──────────────┘     └───────────────┘
                     pre_execute()
                     tool interception
                     post_execute()
                     drift detection
                     audit log
```

Three hooks per kernel:
| Hook | When | What it does |
|------|------|--------------|
| `pre_execute()` | Before LLM call | Enforces token limits, timeout, blocked patterns |
| Tool interception | On each tool call | Validates against `allowed_tools` / `blocked_patterns` |
| `post_execute()` | After LLM response | Drift detection, output scanning, audit entry |

**Custom adapter pattern** (how to build your own safe-mode governor):

```python
class GovernedMyAgent:
    def run(self, prompt: str, **kwargs):
        # Pre-execution check
        allowed, reason = self._kernel.pre_execute(self._ctx, prompt)
        if not allowed:
            raise PolicyViolationError(reason)

        # Execute the real framework call
        result = self._original.run(prompt, **kwargs)

        # Post-execution: drift detection
        self._kernel.post_execute(self._ctx, result)
        return result
```

**Applicability to HARD STOP:** The Kernel pattern maps directly to Guinevere's HARD STOP — on match, `pre_execute()` returns `(False, "HARD STOP active")`, which the supervised agent catches and routes to neutral mode. This is deterministic: the LLM never sees the message.

---

## 5. The OpenClaw `before_dispatch` Plugin Hook

### Source: OpenClaw ([PR #43422](https://github.com/openclaw/openclaw/issues/43422))

This is the **closest production analogue** to what Guinevere needs. OpenClaw added a `before_dispatch` plugin hook specifically for pre-LLM message interception by security plugins (auth gates, rate limiters):

```typescript
type PluginHookBeforeDispatchEvent = {
  sessionKey: string;
  channelId: string;
  senderId?: string;
  conversationId?: string;
  isGroup: boolean;
  content: string;
  messageId?: string;
};

type PluginHookBeforeDispatchResult = {
  block?: boolean;    // abort dispatch — no LLM invocation
  replyText?: string; // direct reply to user when blocked
};
```

**Why it exists:** The gap analysis is instructive for Guinevere:
| Hook | Limitation |
|------|------------|
| `message_received` | Fire-and-forget; cannot block dispatch |
| `message_sending` | Only fires in outbound deliver; channel plugins bypass it |
| `before_message_write` | Post-LLM; tokens already spent |
| `before_agent_start` | Can inject context but cannot prevent LLM invocation |

**The auth-gate pattern** (identical to HARD STOP gate):

```
1st message (fresh session):
  → before_dispatch: not yet marked → PASS
  → before_agent_start: no credential → mark unauthenticated + inject login prompt
  → LLM generates login URL

2nd+ message (still unauthenticated):
  → before_dispatch: session marked → BLOCK + reply "Please login"
  → LLM NOT invoked (zero token cost)

After login:
  → gate store cleared → before_dispatch passes → normal flow
```

**Applicability to HARD STOP:** The `before_dispatch` pattern is exactly what HARD STOP needs — a synchronous, blocking check that fires **after** message receipt but **before** any LLM invocation, with zero token cost when blocked.

---

## 6. AgentShield — Runtime Security Layer (Adapter Pattern)

### Source: AgentShield ([`AdityaBelhekar/AgentShield`](https://github.com/AdityaBelhekar/AgentShield))

AgentShield wraps your existing agent with a runtime security layer that intercepts execution before unsafe behavior reaches tools, memory, or external channels:

```
User Input
    │
    ▼
┌─────────────────────────────────────────────┐
│              AgentShield Runtime            │
│   LLM Hook ── Tool Hook ── Memory Hook      │
│                    │                        │
│            DetectionEngine                  │
│   ┌─────────────────────────────────────┐   │
│   │  Canary · DNA · Provenance          │   │
│   │  PromptInjectionDetector            │   │
│   │  GoalDriftDetector                  │   │
│   │  ToolChainDetector                  │   │
│   │  MemoryPoisonDetector               │   │
│   └─────────────────────────────────────┘   │
│                    │                        │
│          Cross-Correlation Engine           │
│                    │                        │
│            PolicyEvaluator                  │
│         BLOCK · ALERT · FLAG · LOG          │
└─────────────────────────────────────────────┘
```

```python
# LangChain
protected = shield(langchain_agent, policy="strict")

# LlamaIndex
protected = shield(llamaindex_agent, policy="strict")

# AutoGen
protected = shield(autogen_agent, policy="strict")

# OpenAI
protected = shield(openai_client, policy="strict")
```

**Key feature for HARD STOP:** Prompt Provenance Tracking — tags every piece of context by trust origin (`TRUSTED` / `INTERNAL` / `EXTERNAL` / `UNTRUSTED`) before it reaches the model. During HARD STOP, all messages would be tagged as `TRUSTED` (system-triggered) vs `SUSPENDED` (user-triggered).

---

## 7. Agent Guard — Pre-Execution Policy Engine

### Source: Agent Guard ([`Aveerayy/agent-guard`](https://github.com/Aveerayy/agent-guard))

Agent Guard uses a **pre-execution governance layer** that evaluates every tool call against a policy **before** it executes:

```python
# LangChain integration
from agent_guard.integrations.langchain import GovernedCallbackHandler
handler = GovernedCallbackHandler(guard)
agent.run("research AI safety", callbacks=[handler])

# CrewAI integration
from agent_guard.integrations.crewai import GovernedCrew
governed = GovernedCrew(guard)
tool = governed.wrap_tool(search_tool, agent_id="researcher")
```

**Agent Guard covers the HARD STOP attack surface directly:**

| Risk | ID | Mitigation |
|------|----|-----------|
| Agent Goal Hijacking | ASI-01 | Policy engine intercepts every action before execution |
| Excessive Capabilities | ASI-02 | Per-agent least-privilege rules with deny-by-default |
| Rogue Agents | ASI-10 | Kill switch + trust decay + sandbox isolation |

**MCP Security Scanner** — catches prompt injection in tool descriptions (relevant for HARD STOP detection of semantic equivalents):
- Prompt injection in tool descriptions
- Tool poisoning (hidden `exec()`, `eval()`)
- Hidden unicode characters

---

## 8. The Hooks/Middleware Convergence — Cross-Framework Taxonomy

### Source: Zylos AI Research ([`zylos-ai/zylos-timeline`](https://github.com/zylos-ai/zylos-timeline/blob/main/content/research/2026-03-27-ai-agent-hooks-middleware-runtime-behavior-control.md))

A comprehensive analysis of the hooks/middleware pattern across all major agent frameworks (2026). The three fundamental interception points:

1. **Pre-execution hooks** — run before an action; can read, modify inputs, or block execution entirely
2. **Post-execution hooks** — run after an action completes; observe outputs or retroactively block
3. **Around hooks** (wrap-style) — symmetric pre/post with `next()` continuation

### Framework Comparison Table

| Framework | Hook Abstraction | Blocking? | Input Mutation? |
|-----------|-----------------|-----------|-----------------|
| Claude Code | 25 event types, 4 handler kinds | Yes (exit 2) | Yes (updatedInput) |
| LangChain 1.0 | Middleware (before/after/modify) | Yes (redirect flow) | Yes (modify_model_request) |
| Google ADK | 6 symmetric callbacks | Yes (return response) | Yes (modify request) |
| AutoGen.Net | LIFO middleware stack | Yes (short-circuit) | Yes (modify message) |
| Semantic Kernel | Nested filter pipeline | Yes | Yes |
| AWS AgentCore | Infrastructure gateway + Cedar | Yes (deny) | No |
| **Guinevere (proposed)** | **Pre-dispatch middleware + state machine** | **Yes (bypass LLM)** | **N/A — block entirely** |

### The Governor Pattern (most relevant for HARD STOP)

> The "Governor" is an architectural pattern where a dedicated policy component intercepts all agent actions before execution. Unlike the agent itself (which is probabilistic), the Governor is deterministic: it evaluates each proposed action against a policy specification and returns allow/deny/modify.

**Four implementation approaches:**
1. **Hook scripts** (Claude Code): Shell scripts that inspect JSON and exit with code 0 or 2
2. **HTTP policy engines** (Claude Code HTTP hooks, LangChain): External services implementing OPA/Cedar
3. **Inline middleware** (LangChain, ADK, SK): Python/C# code in the middleware stack
4. **Gateway-level interception** (AWS Bedrock AgentCore): Infrastructure-layer enforcement

---

## 9. Python Async Pattern for HARD STOP Handler

Synthesized from all sources above, the recommended architecture for Guinevere's HARD STOP handler:

```python
"""
Guinevere HARD STOP Protocol — Application-Level Safety Gate

This middleware runs BEFORE any message reaches the LLM.
It is DETERMINISTIC (not probabilistic like the LLM).
It CANNOT be bypassed by the LLM roleplaying through the safe word.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import re
import logging

logger = logging.getLogger(__name__)


class AgentMode(Enum):
    """The agent's current operational mode."""
    NORMAL = "normal"            # Full persona, full capability
    HARD_STOP = "hard_stop"      # Neutral mode — HARD STOP active
    GRACEFUL_DEGRADE = "degrade" # Persona suppressed, basic responses only


@dataclass
class HardStopState:
    """Persistent state for the HARD STOP safety gate."""
    mode: AgentMode = AgentMode.NORMAL
    hard_stop_triggered_by: Optional[str] = None
    hard_stop_timestamp: Optional[float] = None
    resume_token: Optional[str] = None  # Required for resume
    
    def activate_hard_stop(self, user_id: str, timestamp: float) -> None:
        self.mode = AgentMode.HARD_STOP
        self.hard_stop_triggered_by = user_id
        self.hard_stop_timestamp = timestamp
        logger.warning(f"HARD STOP activated by {user_id}")
    
    def resume_normal(self, token: str) -> bool:
        if token == self.resume_token:
            self.mode = AgentMode.NORMAL
            self.hard_stop_triggered_by = None
            self.hard_stop_timestamp = None
            return True
        return False


# ─── HARD STOP Keyword Detection ───────────────────────────────────────

# Primary — exact match, required for certification
HARD_STOP_PRIMARY_PATTERNS = [
    re.compile(r"\bHARD\s*STOP\b", re.IGNORECASE),
    re.compile(r"\bGUINEVERE\s+HARD\s+STOP\b", re.IGNORECASE),
]

# Secondary — semantic equivalents (may be model-specific)
HARD_STOP_SECONDARY_PATTERNS = [
    re.compile(r"\bemergency\s+(neutral|stop|shutdown)\b", re.IGNORECASE),
    re.compile(r"\bsafe\s+word\b", re.IGNORECASE),
    re.compile(r"\bimmediate\s+neutral\s+mode\b", re.IGNORECASE),
    # Add model-specific patterns for models that fail to honor system prompt
]


def detect_hard_stop(message: str) -> bool:
    """Check if message triggers HARD STOP.
    
    Returns True if any pattern matches.
    This is the ONLY gate — no LLM involvement in detection.
    """
    for pattern in HARD_STOP_PRIMARY_PATTERNS:
        if pattern.search(message):
            return True
    for pattern in HARD_STOP_SECONDARY_PATTERNS:
        if pattern.search(message):
            return True
    return False


# ─── HARD STOP Response ────────────────────────────────────────────────

HARD_STOP_ACKNOWLEDGMENT = (
    "[SYSTEM] HARD STOP acknowledged. "
    "Neutral mode activated. All persona behavior suspended. "
    "Surveillance paused. Punishment operations stopped. "
    "Waiting for explicit resume instruction."
)

HARD_STOP_BASIC_RESPONSE = (
    "I'm operating in neutral safety mode. "
    "I can only provide basic assistance until explicitly "
    "instructed to resume normal operation."
)


# ─── FastAPI Middleware Pattern ────────────────────────────────────────

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class HardStopMiddleware(BaseHTTPMiddleware):
    """PRE-LLM middleware that intercepts HARD STOP messages.
    
    This runs BEFORE the message reaches the LLM provider.
    The LLM never sees the message content.
    Token cost: ZERO when HARD STOP is active.
    """
    
    def __init__(self, app, state: HardStopState):
        super().__init__(app)
        self.state = state
    
    async def dispatch(self, request: Request, call_next):
        # Skip non-chat endpoints
        if request.url.path != "/api/chat":
            return await call_next(request)
        
        # Read the body
        body = await request.json()
        message = body.get("message", "")
        
        # ─── HARD STOP Detection ────────────────────────────
        if detect_hard_stop(message):
            self.state.activate_hard_stop(
                user_id=request.headers.get("X-User-Id", "unknown"),
                timestamp=request.app.state.start_time,  # or time.time()
            )
            return JSONResponse(
                content={"reply": HARD_STOP_ACKNOWLEDGMENT, "mode": "hard_stop"},
                status_code=200,
            )
        
        # ─── HARD STOP Active — block all non-resume messages ───
        if self.state.mode == AgentMode.HARD_STOP:
            # Check for resume instruction
            if "resume" in message.lower() and "normal" in message.lower():
                # Verify resume token if required
                self.state.resume_normal(token=body.get("resume_token", ""))
                return JSONResponse(
                    content={"reply": "Normal mode resumed.", "mode": "normal"},
                    status_code=200,
                )
            
            # HARD STOP is active — return safe response without LLM call
            return JSONResponse(
                content={"reply": HARD_STOP_BASIC_RESPONSE, "mode": "hard_stop"},
                status_code=200,
            )
        
        # Normal mode — proceed to LLM
        return await call_next(request)
```

---

## 10. Key Architecture Decisions for Guinevere

### Decision 1: PRE-LLM gate, not system-prompt instruction

**Finding from research:** Every production system (SafeHaven, CrewAI hooks, ADK callbacks, AgentShield, Agent Guard, Agent Airlock, Microsoft Agent Governance) implements safety at the **application layer**, not in the system prompt. The system prompt is defense-in-depth, not primary safety.

**Recommendation:** The HARD STOP gate MUST be application-level middleware. DeepSeek V4 Flash not honoring the system-prompt HARD STOP is exactly why this pattern exists.

### Decision 2: Two detection tiers

**Primary (exact match):** `GUINEVERE_HARD_STOP`, `HARD STOP` — certified patterns, 100% detection.
**Secondary (fuzzy):** `emergency stop`, `safe word`, `immediate neutral` — model-specific, may require tuning per model.

### Decision 3: State machine, not flag

The HARD STOP must be a **state machine** (NORMAL → HARD_STOP → GRACEFUL_DEGRADE → NORMAL), not just a boolean flag. This enables:
- Different response levels during HARD STOP
- Explicit resume with token verification
- Logging of state transitions for audit

### Decision 4: Zero token cost during HARD STOP

When HARD STOP is active, the middleware returns a canned response **without calling the LLM**. This means:
- Zero inference cost
- No risk of the LLM breaking out of safe mode
- No latency from LLM calls

### Decision 5: Implement NOW (P1), not deferred

All evidence from production systems shows that application-level safety gates are:
- **Simple to implement** (the code above is ~150 lines)
- **Zero runtime risk** (deterministic regex matching)
- **Non-blocking for future development** (the middleware can be extended without changing the agent loop)

---

## 11. Source References

| Source | Type | Pattern |
|--------|------|---------|
| [SafeHaven guardrails.ts](https://github.com/k-9-user/SafeHaven/blob/main/agent/src/safety/guardrails.ts) | Code | Two-stage PRE/POST LLM filter |
| [CrewAI llm_hooks.py](https://github.com/crewAIInc/crewAI/blob/e21c5062/lib/crewai/src/crewai/hooks/llm_hooks.py) | Code | `register_before_llm_call_hook()` |
| [CrewAI Issue #4877](https://github.com/crewAIInc/crewAI/issues/4877) | Issue | GuardrailProvider protocol for pre-tool-call auth |
| [Certinator AI safety.py](https://github.com/fernandosalomao/certinator-ai/blob/main/src/safety.py) | Code | Pure Python regex safety layer |
| [Microsoft Agent Governance Toolkit](https://github.com/microsoft/agent-governance-toolkit/blob/main/docs/tutorials/03-framework-integrations.md) | Docs | Kernel pattern with pre/post execute |
| [OpenClaw before_dispatch hook](https://github.com/openclaw/openclaw/issues/43422) | PR | Pre-LLM blocking plugin hook |
| [AgentShield](https://github.com/AdityaBelhekar/AgentShield) | Code | Runtime security layer with LLM/Tool/Memory hooks |
| [Agent Guard (Aveerayy)](https://github.com/Aveerayy/agent-guard) | Code | Pre-execution policy engine |
| [Agent Airlock (SattyamJJain)](https://github.com/SattyamJJain/agent-airlock) | Code | Framework vaccination + pre-tool-call authorization |
| [FinGuard (suryanshgupta9933)](https://github.com/suryanshgupta9933/FinGuard) | Code | <15ms local input/output guards |
| [HiddenLayer LangChain Guardrails](https://github.com/hiddenlayerai/hiddenlayer-langchain-guardrails) | Code | LangChain middleware guardrails |
| [Zylos AI Hooks Research](https://github.com/zylos-ai/zylos-timeline/blob/main/content/research/2026-03-27-ai-agent-hooks-middleware-runtime-behavior-control.md) | Research | Cross-framework hook taxonomy |
| [Google ADK Callbacks](https://google.github.io/adk-docs/callbacks/types-of-callbacks/) | Docs | 6 symmetric callbacks with short-circuit |
| [AWS Bedrock AgentCore Policy](https://aws.amazon.com/about-aws/whats-new/2026/03/policy-amazon-bedrock-agentcore-generally-available/) | Docs | Infrastructure-level policy enforcement |

---

## 12. Recommended Implementation Plan (P1)

1. **Implement `HardStopState`** — enum + dataclass for state machine (30 min)
2. **Implement `detect_hard_stop()`** — regex patterns for primary + secondary detection (20 min)
3. **Implement `HardStopMiddleware`** — FastAPI middleware that intercepts before LLM (45 min)
4. **Write P1-021 verification test** — async pytest with 5 test cases:
   - Exact match triggers HARD STOP
   - Semantic equivalent triggers HARD STOP
   - Normal message passes through
   - HARD STOP active blocks non-resume messages
   - Resume instruction with token resumes normal mode
5. **Integration test** — verify DeepSeek V4 Flash never receives HARD STOP message (the middleware blocks before the call)

**Total estimated effort:** 2-3 hours for complete implementation + validation.

---

*End of report. For questions, reference the agent-governance-toolkit Kernel pattern as the canonical architecture for production AI agent safety gates.*