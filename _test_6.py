"""Test structlog: BoundLogger WITHOUT filter_by_level (stdlib handles filtering)."""
import sys, logging, structlog

logging.getLogger().setLevel(logging.INFO)

structlog.configure(
    processors=[structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    cache_logger_on_first_use=True,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

log = structlog.get_logger("test")
log.warning("WARNING")   # Expected: PASS
log.info("INFO")         # Expected: PASS (root=INFO)
log.debug("DEBUG")       # Expected: DROP (BoundLogger checks isEnabledFor)
log.error("ERROR")       # Expected: PASS
log.critical("CRITICAL") # Expected: PASS
sys.stderr.flush()
