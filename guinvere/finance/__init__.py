"""Finance module — Personal finance tracking via casual chat input."""

from guinvere.finance.parser import FinanceParser, ParseResult
from guinvere.finance.db import FinanceDB
from guinvere.finance.plugin import FinancePlugin, get_finance_plugin, process_finance_message
from guinvere.finance.hook import FinanceHook, get_finance_hook, on_message

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
