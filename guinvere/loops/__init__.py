"""Guinevere Agent Loop system — 7-phase autonomous SDLC engine."""

from guinvere.loops.state_machine import LoopPhase, LoopStateMachine, PHASE_NAMES
from guinvere.loops.state_store import LoopStateStore, LoopState, LoopStatus
from guinvere.loops.artifacts import evidence_dir, write_artifact, read_artifact, artifact_exists
from guinvere.loops.evidence import EvidencePipeline
from guinvere.loops.manager import LoopManager
from guinvere.loops.scheduler import LoopScheduler
from guinvere.loops.cost import LoopCostTracker
from guinvere.loops.guardian import LoopGuardian
from guinvere.loops.enforcer import TodoEnforcer
from guinvere.loops.hash_anchor import compute_line_hash, validate_edit, HashAnchorError
from guinvere.loops.sub_agent import SubAgentSpawner
from guinvere.loops.contract import TaskContract, build_contract, contract_to_prompt
from guinvere.loops.budget import IterationBudget, BudgetExhaustedError, BudgetSnapshot
from guinvere.loops.verify import OutputVerifier
from guinvere.loops.sandbox import SandboxVerifier, SandboxResult
from guinvere.loops.context import LoopContext, LoopContextBuilder, advance_phase
from guinvere.loops.prompts import SystemPromptBuilder, build_system_prompt
from guinvere.loops.conversation import ConversationLoop, ConversationResult, ToolCallRecord, run_conversation
from guinvere.loops.concurrency import (
    ConcurrencyLimiter,
    TokenBucket,
    ResourceLimits,
    ResourceGate,
    ConcurrencyDecision,
)
from guinvere.loops.circuit_breaker import (
    CircuitState,
    DependencyCircuitBreaker,
    CircuitBreakerOpenError,
    StuckDetector,
    StuckReport,
    SafetyGate,
    GateDecision,
)
from guinvere.loops.retry import (
    ErrorClass,
    ErrorTaxonomy,
    RetryPolicy,
    RetryExecutor,
    RetryResult,
    retry_with_backoff,
)
from guinvere.loops.escalation import (
    EscalationProtocol,
    EscalationTier,
    EscalationEvent,
)
from guinvere.loops.phases.base import PhaseArtifact, TokenUsage, BasePhaseHandler
from guinvere.loops.review_fork import BackgroundReviewFork, ReviewForkResult, ReviewSuggestion, create_review_fork
from guinvere.loops.curator import CuratorLoop, CuratorTask, CuratorResult, create_curator
from guinvere.loops.testing_gate import TestingGate, TestResult, GateDecision as TestingGateDecision
from guinvere.loops.reflection import ReflectionExtractor, ReflectionEntry, extract_reflection
from guinvere.loops.audit_writer import AuditWriter, AuditEvent, compute_hash
from guinvere.loops.safety_integration import (
    LoopSafetyGate,
    SafetyEvent,
    SafetyAction,
    register_safety_gate,
)
from guinvere.loops.hermes_bridge import HermesBridge, create_hermes_bridge
from guinvere.loops.recovery import (
    RecoveryManager,
    Checkpoint,
    RecoveryResult,
    PhaseCheckpoint,
)
from guinvere.loops.skill_library import (
    SkillLibrary,
    SkillEntry,
    SkillSearchResult,
    SkillLibraryError,
    MAX_STEPS_PER_SKILL,
    MAX_DESCRIPTION_LENGTH,
    SKILL_TYPES,
)
from guinvere.loops.tool_registry import (
    ToolRegistry,
    ToolDefinition,
    ToolResult,
    create_tool_registry_from_mcp,
)
from guinvere.loops.priority import (
    PriorityScorer,
    PriorityScore,
    CostEstimate,
)
from guinvere.loops.dedup import DeduplicationFilter
from guinvere.loops.backlog import Backlog, BacklogItem
from guinvere.loops.discovery import (
    DiscoveryEngine,
    TaskSignal,
    SignalCollector,
)
from guinvere.loops.environment import (
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
