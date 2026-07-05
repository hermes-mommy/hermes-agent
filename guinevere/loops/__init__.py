"""Guinevere Agent Loop system — 7-phase autonomous SDLC engine."""

from guinevere.loops.state_machine import LoopPhase, LoopStateMachine, PHASE_NAMES
from guinevere.loops.state_store import LoopStateStore, LoopState, LoopStatus
from guinevere.loops.artifacts import evidence_dir, write_artifact, read_artifact, artifact_exists
from guinevere.loops.evidence import EvidencePipeline
from guinevere.loops.manager import LoopManager
from guinevere.loops.scheduler import LoopScheduler
from guinevere.loops.cost import LoopCostTracker
from guinevere.loops.guardian import LoopGuardian
from guinevere.loops.enforcer import TodoEnforcer
from guinevere.loops.hash_anchor import compute_line_hash, validate_edit, HashAnchorError
from guinevere.loops.sub_agent import SubAgentSpawner
from guinevere.loops.contract import TaskContract, build_contract, contract_to_prompt
from guinevere.loops.budget import IterationBudget, BudgetExhaustedError, BudgetSnapshot
from guinevere.loops.verify import OutputVerifier
from guinevere.loops.sandbox import SandboxVerifier, SandboxResult
from guinevere.loops.context import LoopContext, LoopContextBuilder, advance_phase
from guinevere.loops.prompts import SystemPromptBuilder, build_system_prompt
from guinevere.loops.conversation import ConversationLoop, ConversationResult, ToolCallRecord, run_conversation
from guinevere.loops.concurrency import (
    ConcurrencyLimiter,
    TokenBucket,
    ResourceLimits,
    ResourceGate,
    ConcurrencyDecision,
)
from guinevere.loops.circuit_breaker import (
    CircuitState,
    DependencyCircuitBreaker,
    CircuitBreakerOpenError,
    StuckDetector,
    StuckReport,
    SafetyGate,
    GateDecision,
)
from guinevere.loops.retry import (
    ErrorClass,
    ErrorTaxonomy,
    RetryPolicy,
    RetryExecutor,
    RetryResult,
    retry_with_backoff,
)
from guinevere.loops.escalation import (
    EscalationProtocol,
    EscalationTier,
    EscalationEvent,
)
from guinevere.loops.phases.base import PhaseArtifact, TokenUsage, BasePhaseHandler
from guinevere.loops.review_fork import BackgroundReviewFork, ReviewForkResult, ReviewSuggestion, create_review_fork
from guinevere.loops.curator import CuratorLoop, CuratorTask, CuratorResult, create_curator
from guinevere.loops.testing_gate import TestingGate, TestResult, GateDecision as TestingGateDecision
from guinevere.loops.reflection import ReflectionExtractor, ReflectionEntry, extract_reflection
from guinevere.loops.audit_writer import AuditWriter, AuditEvent, compute_hash
from guinevere.loops.safety_integration import (
    LoopSafetyGate,
    SafetyEvent,
    SafetyAction,
    register_safety_gate,
)
from guinevere.loops.hermes_bridge import HermesBridge, create_hermes_bridge
from guinevere.loops.recovery import (
    RecoveryManager,
    Checkpoint,
    RecoveryResult,
    PhaseCheckpoint,
)
from guinevere.loops.skill_library import (
    SkillLibrary,
    SkillEntry,
    SkillSearchResult,
    SkillLibraryError,
    MAX_STEPS_PER_SKILL,
    MAX_DESCRIPTION_LENGTH,
    SKILL_TYPES,
)
from guinevere.loops.tool_registry import (
    ToolRegistry,
    ToolDefinition,
    ToolResult,
    create_tool_registry_from_mcp,
)
from guinevere.loops.priority import (
    PriorityScorer,
    PriorityScore,
    CostEstimate,
)
from guinevere.loops.dedup import DeduplicationFilter
from guinevere.loops.backlog import Backlog, BacklogItem
from guinevere.loops.discovery import (
    DiscoveryEngine,
    TaskSignal,
    SignalCollector,
)
from guinevere.loops.environment import (
    EnvironmentMonitor,
    EnvironmentSnapshot,
    ServiceStatus,
    SystemResources,
)

__all__ = [
    "ConcurrencyLimiter",
    "TokenBucket",
    "ResourceLimits",
    "ResourceGate",
    "ConcurrencyDecision",
    "LoopStateStore",
    "LoopState",
    "IterationBudget",
    "BudgetExhaustedError",
    "BudgetSnapshot",
    "LoopPhase",
    "LoopStateMachine",
    "LoopStatus",
    "PHASE_NAMES",
    "evidence_dir",
    "write_artifact",
    "read_artifact",
    "artifact_exists",
    "EvidencePipeline",
    "LoopManager",
    "LoopScheduler",
    "LoopCostTracker",
    "LoopGuardian",
    "TodoEnforcer",
    "compute_line_hash",
    "validate_edit",
    "HashAnchorError",
    "SubAgentSpawner",
    "TaskContract",
    "build_contract",
    "contract_to_prompt",
    "OutputVerifier",
    "SandboxVerifier",
    "SandboxResult",
    "LoopContext",
    "LoopContextBuilder",
    "advance_phase",
    "SystemPromptBuilder",
    "build_system_prompt",
    "ConversationLoop",
    "ConversationResult",
    "ToolCallRecord",
    "run_conversation",
    "CircuitState",
    "DependencyCircuitBreaker",
    "CircuitBreakerOpenError",
    "StuckDetector",
    "StuckReport",
    "SafetyGate",
    "GateDecision",  # from circuit_breaker.py
    "ErrorClass",
    "ErrorTaxonomy",
    "RetryPolicy",
    "RetryExecutor",
    "RetryResult",
    "retry_with_backoff",  # from retry.py
    "TestingGate",
    "TestResult",
    "TestingGateDecision",  # alias for testing_gate.GateDecision (different fields)
    "PhaseArtifact",
    "TokenUsage",
    "BasePhaseHandler",
    "BackgroundReviewFork",
    "ReviewForkResult",
    "ReviewSuggestion",
    "create_review_fork",
    "CuratorLoop",
    "CuratorTask",
    "CuratorResult",
    "create_curator",
    "ReflectionExtractor",
    "ReflectionEntry",
    "extract_reflection",
    "AuditWriter",
    "AuditEvent",
    "compute_hash",
    "ToolRegistry",
    "ToolDefinition",
    "ToolResult",
    "create_tool_registry_from_mcp",
    "SkillLibrary",
    "SkillEntry",
    "SkillSearchResult",
    "SkillLibraryError",
    "MAX_STEPS_PER_SKILL",
    "MAX_DESCRIPTION_LENGTH",
    "SKILL_TYPES",
    "PriorityScorer",
    "PriorityScore",
    "CostEstimate",
    "DeduplicationFilter",
    "Backlog",
    "BacklogItem",
    "DiscoveryEngine",
    "TaskSignal",
    "SignalCollector",
    "RecoveryManager",
    "Checkpoint",
    "RecoveryResult",
    "PhaseCheckpoint",
    "LoopSafetyGate",
    "SafetyEvent",
    "SafetyAction",
    "register_safety_gate",
    "HermesBridge",
    "create_hermes_bridge",
    "EnvironmentMonitor",
    "EnvironmentSnapshot",
    "ServiceStatus",
    "SystemResources",
    "EscalationProtocol",
    "EscalationTier",
    "EscalationEvent",
]
