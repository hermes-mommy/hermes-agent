"""Test structlog level filtering."""
import logging
logging.getLogger().setLevel(logging.INFO)

import structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    cache_logger_on_first_use=True,
)

log = structlog.get_logger("test.ns")
log.debug("should_not_appear")
log.info("should_appear")
print("Root level:", logging.getLogger().level)
