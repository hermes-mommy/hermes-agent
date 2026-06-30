"""Life Kernel — autonomous 24/7 runtime for Guinevere.

Merged exports: legacy LangGraph autonomy loop (graph/state/checkpoint) +
D1-native brain (HermesBrain/hermes_brain) + simple_tools/world_model.

Modules:
    graph       — create_life_mind_graph (LangGraph observe->decide->act cycle)
    state       — kernel state types
    checkpoint  — postgres/redis checkpointers for graph
    heartbeat   — six-interval autonomous clock (1s/10s/30s/60s/5m/1h)
    hermes_brain — AIAgent wrapper (the brain driving LLM autonomy in graph)
    world_model — entity graph with queries
    sensors     — sensor registry and concrete adapters
    simple_tools — calendar/drive/notion/finance thin wrappers (M8 delegates)
    dashboard / dashboard_writer / log_channel / discord_rest_client — P20 visibility
"""

from __future__ import annotations

# Legacy LangGraph autonomy loop (ported from src/life_kernel/)
from guinvere.life_kernel.graph import create_life_mind_graph
from guinvere.life_kernel.state import (
    LifeMindPhase,
    LifeMindState,
    Priority,
    SessionState,
)
from guinvere.life_kernel.checkpoint import (
    create_postgres_checkpointer,
    create_redis_checkpointer,
)
from guinvere.life_kernel.dashboard import DashboardRenderer
from guinvere.life_kernel.discord_rest_client import DiscordRestClient, DiscordRestError
from guinvere.life_kernel.dashboard_writer import DashboardWriter
from guinvere.life_kernel.heartbeat import HeartbeatInterval, HeartbeatService
from guinvere.life_kernel.log_channel import DiscordLogChannel, LogChannel, StructlogLogChannel
from guinvere.life_kernel.log_writer import LogWriter
from guinvere.life_kernel.models import HeartbeatRecord
from guinvere.life_kernel.hermes_brain import HermesBrain, HermesBrainConfig
from guinvere.life_kernel.cognition import BackgroundCognition
from guinvere.life_kernel.sensors import SensorRegistry
from guinvere.life_kernel.p16_adapter import KGRecallAdapter
from guinvere.life_kernel.p18_adapter import MemoryRecallAdapter
from guinvere.life_kernel.decision_context import DecisionContextBuilder
from guinvere.life_kernel.session_graph import (
    SessionGraph,
    SessionWorktree,
    SessionProfile,
    SessionProfileManager,
    DiscordThreadManager,
)

# D1-native extras (P24 brain + simple tools + world model)
from guinvere.life_kernel.simple_tools import (
    CalendarTool,
    DriveTool,
    FinanceTool,
    NotionTool,
)
from guinvere.life_kernel.world_model import WorldModel

__all__ = [
    # LangGraph autonomy loop
    "create_life_mind_graph",
    "LifeMindPhase",
    "LifeMindState",
    "Priority",
    "SessionState",
    "create_postgres_checkpointer",
    "create_redis_checkpointer",
    "SessionGraph",
    "SessionWorktree",
    "SessionProfile",
    "SessionProfileManager",
    "DiscordThreadManager",
    # Brain
    "HermesBrain",
    "HermesBrainConfig",
    "BackgroundCognition",
    # Heartbeat + sensors
    "HeartbeatInterval",
    "HeartbeatService",
    "SensorRegistry",
    "WearableSensorAdapter",
    "CalendarSensorAdapter",
    "FinanceSensorAdapter",
    "SensorAdapter",
    # Recall adapters
    "KGRecallAdapter",
    "MemoryRecallAdapter",
    "DecisionContextBuilder",
    # P20 visibility
    "DashboardRenderer",
    "DiscordRestClient",
    "DiscordRestError",
    "DashboardWriter",
    "DiscordLogChannel",
    "LogChannel",
    "StructlogLogChannel",
    "LogWriter",
    "HeartbeatRecord",
    # D1-native simple tools + world model
    "CalendarTool",
    "DriveTool",
    "FinanceTool",
    "NotionTool",
    "WorldModel",
]
