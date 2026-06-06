# Phase 7c B3–B8: Test Import and Deprecated Module Reference Scan (Raw)

**Generated:** 2026-06-06  
**Scope:** 	ests/discord/, 	ests/hermes/, 	ests/safety/, 	ests/phase7/ — all .py files  
**Target patterns:** command_count, is_faiz_interaction, ot.py, startup.py, conversational_handler.py, _embed_helpers, commands.py, permissions.py, guild_setup.py, intents.py, session_adapter, memory_bridge, HermesSessionAdapter, HermesMemoryBridge, get_adapter, deprecated, rchive, _deprecated

---

## Summary of Findings

| Directory | Files | Files with Matches | Notable References |
|-----------|-------|--------------------|--------------------|
| 	ests/discord/ | 8 | 2 | command_count, commands, ot |
| 	ests/hermes/ | 12 | 2 | HermesMemoryBridge, session_adapter (comment) |
| 	ests/safety/ | 9 | 0 | — |
| 	ests/phase7/ | 11 | 0 | — |
| **Total** | **40** | **4** | — |

---

## tests/discord/ — Detailed Per-File Report

### 1. tests/discord/test_cmd_mood.py

**Import lines:**
`python
from __future__ import annotations
from datetime import datetime, timezone
import pytest
from src.discord.colors import PRIMARY, SUCCESS, ACHIEVEMENT, WARNING, ALERT, NEUTRAL
from src.discord.cmd_mood import (
    MOOD_DESCRIPTION,
    MOOD_TITLE,
    MoodEmbedData,
    MoodEmbedField,
    build_mood_embed_data,
    display_for_mood,
)
`

**Deprecated references found:**
- **Line 273:** rom src.discord.commands import command_count — imports command_count from src.discord.commands
- **Line 275:** ssert command_count() == 35 — assertion checking command count value

**Assertions checking command count:**
- Line 275: ssert command_count() == 35

---

### 2. tests/discord/test_conversational_handler.py

**Import lines:**
`python
from __future__ import annotations
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from src.discord.conversational_handler import (
    DISCORD_MAX_CHARS,
    FALLBACK_MESSAGE,
    GUINEVERE_CHAT_CHANNEL_ID,
    MAX_CHUNKS,
    _split_response,
    handle_conversation,
)
`

**Deprecated references found:** NONE (imports from the actual conversational_handler module, which is the module under test)

---

### 3. tests/discord/test_startup.py

**Import lines:**
`python
from __future__ import annotations
import importlib
import sys
from dataclasses import dataclass, field
from typing import Any
import pytest
from src.discord.colors import PRIMARY
from src.discord.startup import (
    STARTUP_DESCRIPTION,
    STARTUP_FOOTER,
    STARTUP_TITLE,
    PRESENCE_TEXT,
    StartupEmbedData,
    StartupEmbedField,
    build_startup_embed_data,
    reset_greeting,
)
`

**Deprecated references found:** NONE

---

### 4. tests/discord/test_notifications.py

**Import lines:**
`python
import sys
import types
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
import pytest
from src.discord.notifications import (
    NotificationEmbedData,
    _build_notification_data,
    send_alert,
)
`

**Deprecated references found:** NONE

---

### 5. tests/discord/test_gotify_fallback.py

**Import lines:**
`python
import sys
import types
from unittest.mock import AsyncMock, Mock, patch
import httpx
import pytest
from pathlib import Path
from src.discord.gotify_fallback import build_gotify_payload, get_priority, send_fallback
`

**Deprecated references found:** NONE

---

### 6. tests/discord/test_gotify_client.py

**Import lines:**
`python
from __future__ import annotations
from typing import Any
from unittest.mock import AsyncMock
import httpx
import pytest
`

**Deprecated references found:** NONE (no imports from src.discord.*)

---

### 7. tests/discord/test_bot.py

**Import lines:**
`python
from __future__ import annotations
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
`

**Deprecated references found:**
- **Line 32:** rom src.discord.bot import GuinevereBot — imports bot module (module under test, not deprecated usage)
- **Line 172:** ssert src.discord.commands.command_count() == 33 — references command_count from src.discord.commands
- **Line 260:** rom src.discord.bot import main
- **Line 269:** rom src.discord.bot import main

**Assertions checking command count:**
- Line 172: ssert src.discord.commands.command_count() == 33

---

### 8. tests/discord/conftest.py

**Import lines:**
`python
from __future__ import annotations
import os
import sys
`

**Deprecated references found:** NONE

---

## tests/hermes/ — Detailed Per-File Report

### 1. tests/hermes/__init__.py

Empty file. No content.

---

### 2. tests/hermes/test_llm_metrics.py

**Import lines:**
`python
from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from prometheus_client import generate_latest
from prometheus_client.parser import text_string_to_metric_families
from src.core.services.llm_metrics import (
    observe_call,
    observe_cost,
    observe_fallback,
    observe_latency,
    start_llm_metrics_server,
)
`

**Deprecated references found:** NONE

---

### 3. tests/hermes/test_budget_hook.py

**Import lines:**
`python
from __future__ import annotations
import importlib
import sys
from pathlib import Path
from typing import Protocol, cast
from unittest.mock import MagicMock, patch
import pytest
`

**Deprecated references found:** NONE

---

### 4. tests/hermes/test_llm_router_cost.py

**Import lines:**
`python
from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from src.core.services.llm_router import (
    LLMRouter,
    ModelConfig,
    MODELS,
    PRICING,
    TaskType,
    _strip_sse_done,
)
`

**Deprecated references found:** NONE

---

### 5. tests/hermes/test_integration_e2e.py

**Import lines:**
`python
from __future__ import annotations
import importlib
import importlib.util
import re
import sys
from pathlib import Path
from typing import Protocol, cast
import pytest
import yaml
from src.mcp.auth import AuthLevel
from src.mcp.auth_matrix import (
    AUTH_MATRIX,
    ALL_TOOL_NAMES,
    get_auth_level,
)
`

**Deprecated references found:** NONE

---

### 6. tests/hermes/test_security_audit.py

**Import lines:**
`python
from __future__ import annotations
import re
import sys
import time
from pathlib import Path
from typing import cast
import pytest
from src.mcp.auth import AuthLevel
from src.mcp.auth_matrix import (
    AUTH_MATRIX,
    ALL_TOOL_NAMES,
    get_auth_level,
    verify_matrix_completeness,
)
`

**Deprecated references found:** NONE

---

### 7. tests/hermes/test_hybrid_guards.py

**Import lines:**
`python
from __future__ import annotations
import importlib
import json
import sys
from pathlib import Path
from typing import Final, Protocol, cast
import pytest
`

**Deprecated references found:** NONE

---

### 8. tests/hermes/test_auth_overlay.py

**Import lines:**
`python
from __future__ import annotations
import importlib
import sys
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Protocol, cast
import pytest
from src.mcp.auth import AuthLevel
from src.mcp.auth_matrix import AUTH_MATRIX, ALL_TOOL_NAMES, get_auth_level
`

**Deprecated references found:** NONE

---

### 9. tests/hermes/test_fastmcp_bridge.py

**Import lines:**
`python
from __future__ import annotations
import ast
import re
from pathlib import Path
from typing import cast
import pytest
import yaml
`

**Deprecated references found:** NONE

---

### 10. tests/hermes/test_mcp_config.py

**Import lines:**
`python
from __future__ import annotations
from pathlib import Path
import re
from typing import cast
import pytest
import yaml
`

**Deprecated references found:** NONE

---

### 11. tests/hermes/test_safety_plugin.py

**Import lines:**
`python
from __future__ import annotations
import enum
import sys
from collections import namedtuple
from unittest.mock import MagicMock, patch
import pytest
from src.hermes.safety_plugin import (
    GuinevereSafetyPlugin,
    SessionSafetyState,
    HARD_STOP_EXACT,
    HARD_STOP_SEMANTIC,
    RECOVERY_TRIGGERS,
    _COMPILED_FORBIDDEN,
    _NEUTRAL_RESPONSE,
    register,
)
`

**Deprecated references found:**
- **Line 9:** # Prevent transitive import failure from src/hermes/__init__.py -> session_adapter
  This is a **comment** referencing session_adapter as a transitive import chain concern. The file fakes modules to prevent import failure from src/hermes/__init__.py which imports session_adapter.

---

### 12. tests/hermes/test_memory_bridge.py

**Import lines:**
`python
from __future__ import annotations
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from src.hermes.memory_bridge import HermesMemoryBridge  # noqa: E402
`

**Deprecated references found:**
- **Line 8:** # Prevent transitive import failure from src/hermes/__init__.py -> session_adapter — Comment referencing session_adapter as transitive dependency.
- **Line 15:** rom src.hermes.memory_bridge import HermesMemoryBridge — imports the HermesMemoryBridge type (active module)
- Lines 69, 87, 97, 110, 124, 138, 153, 180, 193, 209, 224, 239, 254, 276, 293, 314, 324: All use HermesMemoryBridge(...) constructor calls.

**Note:** HermesMemoryBridge is an **active** module in src/hermes/memory_bridge.py. It is not deprecated or archived.

---

## tests/safety/ — Detailed Per-File Report

**All 9 files scanned.** None contain imports or references to any of the target deprecated patterns.

| File | Deprecated References |
|------|----------------------|
| test_auto_rollback.py | NONE |
| test_yandere_cap.py | NONE |
| test_punishment_overflow.py | NONE |
| test_hard_stop_model.py | NONE |
| test_hard_stop_handler.py | NONE |
| test_hard_stop_comprehensive.py | NONE |
| test_distress_protocol_e2e.py | NONE |
| test_consent_revocation.py | NONE |
| __init__.py | NONE |

---

## tests/phase7/ — Detailed Per-File Report

**All 11 files scanned.** None contain imports or references to any of the target deprecated patterns.

| File | Deprecated References |
|------|----------------------|
| test_T1_e2e_loop.py | NONE |
| test_T2_safety_gates.py | NONE |
| test_T3_auth_enforcement.py | NONE |
| test_T4_memory_pipeline.py | NONE |
| test_T5_surveillance_pipeline.py | NONE |
| test_T6_persona_fsm.py | NONE |
| test_T7_distress_protocol.py | NONE |
| test_T8_consent_revocation.py | NONE |
| test_T9_budget_enforcement.py | NONE |
| test_T10_monitoring_health.py | NONE |
| __init__.py | NONE |

---

## Cross-Directory Pattern Summary

### command_count references (2 files)
| File | Line | Code |
|------|------|------|
| tests/discord/test_cmd_mood.py | 273-275 | rom src.discord.commands import command_count + ssert command_count() == 35 |
| tests/discord/test_bot.py | 172 | ssert src.discord.commands.command_count() == 33 |

### bot.py references (1 file)
| File | Line | Code |
|------|------|------|
| tests/discord/test_bot.py | 32 | rom src.discord.bot import GuinevereBot |
| tests/discord/test_bot.py | 260, 269 | rom src.discord.bot import main |

### session_adapter references (2 files, both comments)
| File | Line | Code |
|------|------|------|
| tests/hermes/test_safety_plugin.py | 9 | # Prevent transitive import failure from src/hermes/__init__.py -> session_adapter |
| tests/hermes/test_memory_bridge.py | 8 | # Prevent transitive import failure from src/hermes/__init__.py -> session_adapter |

### HermesMemoryBridge references (1 file)
| File | Lines | Details |
|------|-------|---------|
| tests/hermes/test_memory_bridge.py | 15, 69, 87, 97, 110, 124, 138, 153, 180, 193, 209, 224, 239, 254, 276, 293, 314, 324 | Primary import + 17 usages of HermesMemoryBridge constructor |

### Assertions checking command count values (2 files)
1. tests/discord/test_cmd_mood.py line 275: ssert command_count() == 35
2. tests/discord/test_bot.py line 172: ssert src.discord.commands.command_count() == 33

### Patterns with ZERO matches across all 40 files
- is_faiz_interaction
- _embed_helpers
- permissions.py (as import)
- guild_setup.py (as import)
- intents.py (as import)
- HermesSessionAdapter
- get_adapter
- deprecated (as standalone identifier in test code)
- _deprecated
- rchive (in the four target directories only)

---

## Key Findings

1. **command_count is referenced in two discord test files** — both import from src.discord.commands (which is the active module, not a deprecated one). These are legitimate test references to src.discord.commands.command_count(). Different expected values: 	est_cmd_mood.py expects **35**, 	est_bot.py expects **33**. This discrepancy may be a sign of drift.

2. **session_adapter is mentioned in comments only** — in two hermes test files as a note about transitive import failure prevention. The actual module at src/hermes/session_adapter.py is not imported directly in any test file.

3. **HermesMemoryBridge is actively used** — in 	ests/hermes/test_memory_bridge.py as the module under test. This module is active (not deprecated/archived).

4. **No deprecated/archived module references** were found in any test file across the four directories.

5. **No references at all** to is_faiz_interaction, _embed_helpers, permissions.py, guild_setup.py, intents.py, HermesSessionAdapter, get_adapter, _deprecated, or rchive in any of the 40 scanned test files.
