"""Finance sensor adapter (placeholder) for the Living Autonomy Kernel."""

from __future__ import annotations

from guinvere.life_kernel.sensor_adapters.base import BaseSensorAdapter


class FinanceSensorAdapter(BaseSensorAdapter):
    """Placeholder adapter for financial data polling.

    In future milestones this may report account balances and transactions.
    This adapter **MUST NOT** perform payments or transfers in v1, and no
    external finance API is called.
    """

    SENSOR_NAME = "finance"
    OBSERVATION_TYPE = "balance"
    DEFAULT_CONTENT = (
        "Financial data polling placeholder — account balances and "
        "transactions are not fetched in v1. No payment or transfer is performed."
    )
