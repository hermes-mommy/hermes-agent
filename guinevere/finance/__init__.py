"""Finance module — Personal finance tracking via casual chat input."""

from guinevere.finance.parser import FinanceParser, ParseResult
from guinevere.finance.db import FinanceDB
from guinevere.finance.plugin import FinancePlugin, get_finance_plugin, process_finance_message
from guinevere.finance.hook import FinanceHook, get_finance_hook, on_message

__all__ = [
    "FinanceParser",
    "ParseResult",
    "FinanceDB",
    "FinancePlugin",
    "FinanceHook",
    "get_finance_plugin",
    "get_finance_hook",
    "process_finance_message",
    "on_message",
]
