"""Life Kernel — autonomous 24/7 runtime for Guinevere.

Provides the heartbeat clock, entity world model, sensor registry,
and simple tool wrappers that drive Guinevere's autonomous behavior.

Modules:
    heartbeat   — six-interval autonomous clock (1s/10s/30s/60s/5m/1h)
    world_model — entity graph with queries
    sensors     — sensor registry and concrete adapters
    simple_tools — calendar/drive/notion/finance thin wrappers (M8 delegates)
"""

from guinevere.life_kernel.heartbeat import HeartbeatInterval, HeartbeatService
from guinevere.life_kernel.sensors import (
    CalendarSensorAdapter,
    FinanceSensorAdapter,
    SensorAdapter,
    SensorRegistry,
    WearableSensorAdapter,
)
from guinevere.life_kernel.simple_tools import (
    CalendarTool,
    DriveTool,
    FinanceTool,
    NotionTool,
    wire,
)
from guinevere.life_kernel.world_model import WorldModel

__all__ = [
    "HeartbeatInterval",
    "HeartbeatService",
    "WorldModel",
    "SensorAdapter",
    "SensorRegistry",
    "WearableSensorAdapter",
    "CalendarSensorAdapter",
    "FinanceSensorAdapter",
    "CalendarTool",
    "DriveTool",
    "FinanceTool",
    "NotionTool",
    "wire",
    "HermesBrain",
    "HermesBrainConfig",
]
