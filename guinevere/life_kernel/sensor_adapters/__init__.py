"""Sensor adapters package for the Living Autonomy Kernel (LK-011)."""

from __future__ import annotations

from guinevere.life_kernel.sensor_adapters.base import BaseSensorAdapter
from guinevere.life_kernel.sensor_adapters.browser_adapter import BrowserSensorAdapter
from guinevere.life_kernel.sensor_adapters.discord_adapter import DiscordSensorAdapter
from guinevere.life_kernel.sensor_adapters.finance_adapter import FinanceSensorAdapter
from guinevere.life_kernel.sensor_adapters.gmail_adapter import GmailSensorAdapter
from guinevere.life_kernel.sensor_adapters.repo_adapter import RepoSensorAdapter
from guinevere.life_kernel.sensor_adapters.surveillance_adapter import SurveillanceSensorAdapter
from guinevere.life_kernel.sensor_adapters.vps_adapter import VPSSensorAdapter
from guinevere.life_kernel.sensor_adapters.wearable_adapter import WearableSensorAdapter

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
