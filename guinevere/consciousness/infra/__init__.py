"""Consciousness infrastructure — ported clean utilities from src/loops/.

Re-exports the 4 modules required by M10 (optimizer.py / W14):
AuditWriter, IterationBudget, ReflectionExtractor, TestingGate.

All public APIs are preserved exactly so W14 can import from here.
"""

from guinevere.consciousness.infra.audit_writer import AuditEvent, AuditWriter
from guinevere.consciousness.infra.budget import (
    BudgetExhaustedError,
    BudgetSnapshot,
    IterationBudget,
)
from guinevere.consciousness.infra.reflection import (
    ReflectionEntry,
    ReflectionExtractor,
    extract_reflection,
)
from guinevere.consciousness.infra.testing_gate import (
    GateDecision as TestingGateDecision,
    TestResult,
    TestingGate,
)

__all__ = [
    "AuditEvent",
    "AuditWriter",
    "BudgetExhaustedError",
    "BudgetSnapshot",
    "IterationBudget",
    "ReflectionEntry",
    "ReflectionExtractor",
    "TestingGate",
    "TestResult",
    "TestingGateDecision",
    "extract_reflection",
]
