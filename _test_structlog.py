"""Test structlog configuration behavior."""
import logging
import structlog

print("Default wrapper type:", type(structlog.get_logger("test_default")))

# Try configure
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    cache_logger_on_first_use=True,
)
print("After configure wrapper type:", type(structlog.get_logger("test_configured")))
print("Stdlib root level:", logging.getLogger().level)
print("Root isEnabledFor(DEBUG):", logging.getLogger().isEnabledFor(logging.DEBUG))
