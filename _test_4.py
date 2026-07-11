"""Test structlog: explicit flush to stderr."""
import sys
import structlog
import logging
import os

# Configure at module level
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
log.debug("test_debug")
log.info("test_info")
log.warning("test_warning")
sys.stderr.flush()
os.fsync(sys.stderr.fileno())
