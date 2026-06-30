"""Sensor adapters package for the Living Autonomy Kernel (LK-011)."""

from __future__ import annotations

from guinvere.life_kernel.sensor_adapters.base import BaseSensorAdapter
from guinvere.life_kernel.sensor_adapters.browser_adapter import BrowserSensorAdapter
from guinvere.life_kernel.sensor_adapters.discord_adapter import DiscordSensorAdapter
from guinvere.life_kernel.sensor_adapters.finance_adapter import FinanceSensorAdapter
from guinvere.life_kernel.sensor_adapters.gmail_adapter import GmailSensorAdapter
from guinvere.life_kernel.sensor_adapters.repo_adapter import RepoSensorAdapter
from guinvere.life_kernel.sensor_adapters.surveillance_adapter import SurveillanceSensorAdapter
from guinvere.life_kernel.sensor_adapters.vps_adapter import VPSSensorAdapter
from guinvere.life_kernel.sensor_adapters.wearable_adapter import WearableSensorAdapter

__all__ = [
    "BaseSensorAdapter",
    "BrowserSensorAdapter",
    "DiscordSensorAdapter",
    "FinanceSensorAdapter",
    "GmailSensorAdapter",
    "RepoSensorAdapter",
    "SurveillanceSensorAdapter",
    "VPSSensorAdapter",
    "WearableSensorAdapter",
]
