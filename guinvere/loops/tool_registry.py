"""Unified tool registry for Guinevere agent loops.

Wraps the existing 16 MCP tools with a ``BaseTool`` protocol and exposes
them through a ``ToolRegistry`` that supports auth-level enforcement,
timeout-controlled execution, and schema generation for OpenAI and
Anthropic function calling.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import time
import types
import typing
from dataclasses import dataclass
from typing import Any, Callable, Protocol, get_args, get_origin, get_type_hints

import structlog

from guinvere.mcp.auth import AuthLevel

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 30
MAX_TOOL_OUTPUT = 100_000


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class BaseTool(Protocol):
    """Protocol describing a callable MCP tool.

    Concrete implementations are async callables that accept keyword
    arguments matching the tool's parameter schema and return a value
    that the registry serialises for the caller.
    """

    async def __call__(self, **kwargs: Any) -> Any:  # noqa: D401
        ...


@dataclass(frozen=True)
class ToolDefinition:
    """Static metadata describing a registered tool.

    The ``parameters`` field contains a JSON-Schema-compatible dict for
    the tool's input arguments, suitable for LLM function-calling APIs.
    """

    name: str
    description: str
    parameters: dict[str, Any]
    auth_level: AuthLevel
    timeout_seconds: int = DEFAULT_TIMEOUT


@dataclass(frozen=True)
class ToolResult:
    """Result of a single tool invocation."""

    success: bool
    output: str
    error: str | None
    tokens_used: int
    cost_usd: float
    duration_ms: float


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------


class ToolRegistry:
    """Central registry for MCP tools used by agent loops.

    Maintains a mapping of tool names to their metadata and callables,
    enforces the four-level authorization model, applies a configurable
    execution timeout, and can emit OpenAI/Anthropic function-calling
    schemas.
    """

    def __init__(self, tool_selector: Any | None = None) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._impls: dict[str, Callable[..., Any]] = {}
        self._tool_selector = tool_selector

    # ------------------------------------------------------------------
    # Registration API
    # ------------------------------------------------------------------

    def register(
        self,
        tool: ToolDefinition,
        func: Callable[..., Any] | None = None,
    ) -> None:
        """Register a tool definition and optional callable implementation."""
        self._tools[tool.name] = tool
        if func is not None:
            self._impls[tool.name] = func

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry."""
        self._tools.pop(name, None)
        self._impls.pop(name, None)

    def get(self, name: str) -> ToolDefinition | None:
        """Return the ``ToolDefinition`` for *name* or ``None``."""
        return self._tools.get(name)

    def list_tools(
        self,
        auth_level: AuthLevel | str | None = None,
    ) -> list[ToolDefinition]:
        """Return all registered tools, optionally filtered by auth level."""
        tools = list(self._tools.values())
        if auth_level is None:
            return tools
        target = auth_level.value if isinstance(auth_level, AuthLevel) else auth_level
        return [t for t in tools if t.auth_level.value == target]

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(
        self,
        name: str,
        params: dict[str, Any],
        context: dict[str, Any] | None = None,
        *,
        approved: bool = False,
        caller_id: str | None = None,
    ) -> ToolResult:
        """Execute the named tool with timeout and auth enforcement.

        Args:
            name: Registered tool name.
            params: Keyword arguments to pass to the tool implementation.
            context: Optional runtime context for logging/audit.
            approved: Required to be ``True`` for ``DESTRUCTIVE_APPROVAL`` tools.
            caller_id: Identity of the caller; required for destructive operations.

        Returns:
            A ``ToolResult`` summarising the invocation.
        """
        start = time.perf_counter()
        tool = self.get(name)

        if tool is None:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{name}' is not registered.",
                tokens_used=0,
                cost_usd=0.0,
                duration_ms=0.0,
            )

        impl = self._impls.get(name)
        if impl is None:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{name}' has no callable implementation.",
                tokens_used=0,
                cost_usd=0.0,
                duration_ms=0.0,
            )

        try:
            if tool.auth_level is AuthLevel.FORBIDDEN:
                raise PermissionError(f"Tool '{name}' is forbidden.")

            if tool.auth_level is AuthLevel.DESTRUCTIVE_APPROVAL:
                if caller_id is None:
                    raise PermissionError(
                        "Destructive operations require caller identification"
                    )
                if not approved:
                    raise PermissionError(
                        f"Tool '{name}' requires explicit approved=True kwarg."
                    )
                logger.info(
                    "destructive_tool_approved",
                    tool_name=name,
                    caller_id=caller_id,
                    approved=approved,
                    context=context,
                )

            if tool.auth_level is AuthLevel.WRITE_NOTIFY:
                logger.info(
                    "tool_audit_write_notify",
                    tool_name=name,
                    context=context,
                )

            timeout = tool.timeout_seconds or DEFAULT_TIMEOUT

            if inspect.iscoroutinefunction(impl):
                result = await asyncio.wait_for(
                    impl(**params),
                    timeout=timeout,
                )
            else:
                # Run synchronous tools in the default executor so the
                # timeout still applies.
                loop = asyncio.get_running_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: impl(**params)),
                    timeout=timeout,
                )

            output = _serialise_output(result)
            if len(output) > MAX_TOOL_OUTPUT:
                output = output[:MAX_TOOL_OUTPUT]

            duration_ms = (time.perf_counter() - start) * 1000.0
            tokens_used = _estimate_tokens(params, output)

            return ToolResult(
                success=True,
                output=output,
                error=None,
                tokens_used=tokens_used,
                cost_usd=_estimate_cost(name, tool.auth_level),
                duration_ms=duration_ms,
            )
        except asyncio.TimeoutError as exc:
            duration_ms = (time.perf_counter() - start) * 1000.0
            return ToolResult(
                success=False,
                output="",
                error=str(exc),
                tokens_used=0,
                cost_usd=0.0,
                duration_ms=duration_ms,
            )
        except Exception as exc:  # noqa: BLE001
            duration_ms = (time.perf_counter() - start) * 1000.0
            logger.warning(
                "tool_execution_failed",
                tool_name=name,
                error=str(exc),
                exc_info=True,
            )
            return ToolResult(
                success=False,
                output="",
                error=str(exc),
                tokens_used=0,
                cost_usd=0.0,
                duration_ms=duration_ms,
            )

    # ------------------------------------------------------------------
    # Schema generation
    # ------------------------------------------------------------------

    def generate_openai_schema(self) -> list[dict[str, Any]]:
        """Generate OpenAI function-calling schema for all registered tools."""
        schema: list[dict[str, Any]] = []
        for tool in self._tools.values():
            schema.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
            )
        return schema

    def generate_anthropic_schema(self) -> list[dict[str, Any]]:
        """Generate Anthropic tool_use schema for all registered tools."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters,
            }
            for tool in self._tools.values()
        ]

    # ------------------------------------------------------------------
    # Validation / selection helpers
    # ------------------------------------------------------------------

    def validate_required(self, required: list[str]) -> bool:
        """Return ``True`` if every tool in *required* is registered."""
        return all(name in self._tools for name in required)

    async def select_tool(
        self,
        task_type: str,
        query: str = "",
        constraints: dict[str, Any] | None = None,
    ) -> Any:
        """Delegate to the optional tool selector for priority-aware routing."""
        if self._tool_selector is None:
            raise RuntimeError("No tool_selector configured on this registry.")
        return await self._tool_selector.select_tool(
            task_type=task_type,
            query=query,
            constraints=constraints,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_tool_registry_from_mcp(tool_selector: Any | None = None) -> ToolRegistry:
    """Build a ``ToolRegistry`` populated with the 16 existing MCP tools.

    Discovers decorated tool functions in ``src.mcp.tools`` using the
    same module list used by the MCP server, derives each tool's auth
    level from the ``@require_approval`` wrapper, and registers a JSON
    schema generated from its signature.
    """
    # Import the tools package so its registration side-effects run.
    import guinvere.mcp.tools as tools_pkg  # noqa: PLC0415

    registry = ToolRegistry(tool_selector=tool_selector)

    modules: list[Any] = getattr(tools_pkg, "_TOOL_MODULES", [])
    for module in modules:
        for _attr_name, obj in inspect.getmembers(module):
            if not inspect.iscoroutinefunction(obj):
                continue
            auth_level = getattr(obj, "_auth_level", None)
            if not isinstance(auth_level, AuthLevel):
                continue

            wrapper = obj
            original = getattr(wrapper, "__wrapped__", wrapper)

            tool_name = getattr(wrapper, "_auth_tool_name", None) or original.__name__
            description = (original.__doc__ or "").strip()
            parameters = _build_schema_from_signature(original)

            tool = ToolDefinition(
                name=tool_name,
                description=description,
                parameters=parameters,
                auth_level=auth_level,
                timeout_seconds=DEFAULT_TIMEOUT,
            )
            registry.register(tool, func=original)

    return registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_schema_from_signature(func: Callable[..., Any]) -> dict[str, Any]:
    """Return a JSON-Schema-like dict describing *func*'s parameters."""
    sig = inspect.signature(func)
    try:
        hints = get_type_hints(func)
    except Exception:  # noqa: BLE001
        logger.debug("get_type_hints_fallback", func_name=getattr(func, "__name__", str(func)), exc_info=True)
        hints = {}

    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        # Skip internal dependency-injection parameters such as the
        # filesystem tool's FilesystemConfig default.
        if _is_internal_param(param_name, param):
            continue

        param_schema = _type_to_schema(hints.get(param_name, Any))
        if not param_schema:
            param_schema = {"type": "string"}

        if param.default is not inspect.Parameter.empty:
            param_schema["default"] = _normalise_default(param.default)
        else:
            required.append(param_name)

        properties[param_name] = param_schema

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _is_internal_param(param_name: str, param: inspect.Parameter) -> bool:
    """Return ``True`` for parameters that should be hidden from LLM schemas."""
    if param_name in {"config"}:
        return True
    default = param.default
    if default is not inspect.Parameter.empty and hasattr(default, "__module__"):
        module = str(default.__module__)
        if module.startswith("guinvere.mcp.tools"):
            return True
    return False


def _normalise_default(value: Any) -> Any:
    """Return a JSON-serialisable default value or ``None``."""
    if isinstance(value, (str, int, float, bool, list, dict, type(None))):
        return value
    return None


def _type_to_schema(tp: Any) -> dict[str, Any]:
    """Map a Python type annotation to a JSON Schema fragment."""
    if tp is str:
        return {"type": "string"}
    if tp is int:
        return {"type": "integer"}
    if tp is float:
        return {"type": "number"}
    if tp is bool:
        return {"type": "boolean"}
    if tp in (list,):
        return {"type": "array"}
    if tp in (dict,):
        return {"type": "object"}
    if tp is Any:
        return {}

    origin = get_origin(tp)
    args = get_args(tp)

    if origin in (typing.Union, getattr(types, "UnionType", None)):
        non_none = [a for a in args if a is not type(None)]
        if len(args) == 2 and len(non_none) == 1:
            return _type_to_schema(non_none[0])
        return {}

    if origin in (list,):
        items = _type_to_schema(args[0]) if args else {}
        return {"type": "array", "items": items}

    if origin in (dict,):
        return {"type": "object"}

    return {}


def _serialise_output(result: Any) -> str:
    """Convert a tool result to a string, truncating if necessary."""
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(result)


def _estimate_tokens(params: dict[str, Any], output: str) -> int:
    """Rough token count from input + output character length."""
    try:
        input_chars = len(json.dumps(params, ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        input_chars = 0
    return (input_chars + len(output)) // 4


def _estimate_cost(name: str, auth_level: AuthLevel) -> float:
    """Return a fixed per-call cost if one is known, otherwise 0.0."""
    try:
        from guinvere.mcp.cost import _TOOL_COSTS  # noqa: PLC0415

        cost = _TOOL_COSTS.get(name, 0.0)
        if cost < 0:
            return 0.0
        return cost
    except Exception:  # noqa: BLE001
        logger.debug("cost_estimation_failed", tool_name=name, exc_info=True)
        return 0.0
