"""Test structlog: verify filter_by_level behavior per level."""
import sys
import structlog
import logging

# Set root to INFO
logging.getLogger().setLevel(logging.INFO)
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    cache_logger_on_first_use=True,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

log = structlog.get_logger("test")
# Force-resolve proxy by calling a method
log.warning("____WARNING____")  # Expected: PASS
log.info("____INFO____")  # Expected: PASS (INFO >= INFO)
log.debug("____DEBUG____")  # Expected: DROP
log.error("____ERROR____")  # Expected: PASS
log.critical("____CRITICAL____")  # Expected: PASS
sys.stderr.flush()
