"""Test structlog: verify configure at module top vs in function."""
import sys
import structlog
import logging

# Simulate module-level logging setup
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

# Simulate what happens when consciousness module imports create a logger
# BEFORE the lifespan function runs (module import time)
log_module = structlog.get_logger("test.premodule")
# Also test: fastapi and uvicorn might call get_logger too
# Simulate lifespan function creating consciousness logger
log_lifespan = structlog.get_logger("test.lifespan")
print(f"Module logger type: {type(log_module)}", file=sys.stderr)
print(f"Lifespan logger type: {type(log_lifespan)}", file=sys.stderr)

# These should NOT appear
log_module.debug("module_debug_should_be_filtered")
log_lifespan.debug("lifespan_debug_should_be_filtered")
# This SHOULD appear
log_module.info("module_info_should_appear")
log_lifespan.info("lifespan_info_should_appear")
print("DONE", file=sys.stderr)
