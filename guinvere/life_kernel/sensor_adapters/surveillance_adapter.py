"""Surveillance sensor adapter (placeholder) for the Living Autonomy Kernel."""

from __future__ import annotations

from guinvere.life_kernel.sensor_adapters.base import BaseSensorAdapter


class SurveillanceSensorAdapter(BaseSensorAdapter):
    """Placeholder adapter for surveillance data.

    Real surveillance data access is consent-gated and will only be enabled
    after explicit operator consent. This placeholder returns a single alert
    observation explaining that no actual surveillance feed is accessed or
    stored in v1.
    """

    SENSOR_NAME = "surveillance"
    OBSERVATION_TYPE = "alert"
    DEFAULT_CONTENT = (
        "Surveillance data placeholder — access is consent-gated. No raw "
        "surveillance feed is read or stored in v1."
    )
