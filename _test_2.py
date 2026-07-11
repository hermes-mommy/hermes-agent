"""Test structlog default behavior on VPS."""
import sys
import structlog

# Test 1: Get a logger with DEFAULT config
log1 = structlog.get_logger("test.default")
print("Type of log1:", type(log1), file=sys.stderr)

# Test 2: Configure with stdlib + filter
import logging
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
log2 = structlog.get_logger("test.configured")
log2.debug("debug_should_not_appear")
log2.info("info_should_appear")
print("Type of log2:", type(log2), file=sys.stderr)
