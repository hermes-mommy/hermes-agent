# Phase 6-7 Planning: Deprecated Files Inventory & Deletion Risk Assessment

**Generated**: 2026-06-05  
**Context**: ADR-035 Hermes Migration (Phases 6-7)  
**Purpose**: Complete inventory of deprecated files to be archived/deleted after Hermes migration cutover, including dependency mapping and deletion risk assessment.

---

## 1. Target Deprecated Files Inventory

### 1.1 Discord Handler Files (Phase 2 Cutover Obsolete)
| File Path | Line Count | Status | Primary Role |
|---|---|---|---|
| src/discord/conversational_handler.py | 515 | EXISTS | Legacy conversational flow, bridge to memory/LLM |
| src/discord/bot.py | 473 | EXISTS | GuinevereBot class, command tree, lifecycle |
| src/discord/commands.py | 278 | EXISTS | Command registry, permission helpers, categories |
| src/discord/permissions.py | 418 | EXISTS | Role/permission validation utilities |
| src/discord/guild_setup.py | 316 | EXISTS | Channel/category provisioning, token retrieval |
| src/discord/startup.py | 253 | EXISTS | on_ready lifecycle hooks, startup logging |
| src/discord/_embed_helpers.py | 222 | EXISTS | Embed formatting, defer/followup utilities |
| src/discord/intents.py | 79 | EXISTS | Discord gateway intent configuration |
| **Subtotal** | **2,554 lines** | | |

### 1.2 Adapter/Bridge Files (Hermes Replaces)
| File Path | Line Count | Status | Primary Role |
|---|---|---|---|
| src/hermes/session_adapter.py | 302 | EXISTS | Legacy Hermes Agent SDK wrapper (skip_memory=True) |
| src/hermes/memory_bridge.py | 262 | EXISTS | Legacy memory recall/store bridge (deprecated in Phase 3) |
| src/core/services/llm_router.py | 98 | EXISTS | Legacy LLM routing (replaced by Hermes native routing) |
| **Subtotal** | **662 lines** | | |

**Total Deprecated Code**: ~3,216 lines

---

## 2. Import Dependency Map

### 2.1 High-Risk Dependencies (Will Break If Deleted Prematurely)

| Deprecated File | Importing File(s) | Import Statement | Risk Level |
|---|---|---|---|
| src/discord/commands.py | src/hermes_plugins/commands_high/help.py | rom src.discord.commands import command_categories | **HIGH** |
| src/discord/conversational_handler.py | src/discord/hermes_conversational.py | rom src.hermes.memory_bridge import HermesMemoryBridge (indirect) | **HIGH** |
| src/hermes/memory_bridge.py | src/discord/conversational_handler.py | rom src.hermes.memory_bridge import HermesMemoryBridge | **HIGH** |
| src/hermes/memory_bridge.py | src/discord/hermes_conversational.py | rom src.hermes.memory_bridge import HermesMemoryBridge | **HIGH** |
| src/core/services/llm_router.py | src/discord/conversational_handler.py | rom src.core.services.llm_router import LLMRouter, MODELS, TaskType | **MEDIUM** |
| src/core/services/llm_router.py | src/discord/hermes_conversational.py | rom src.core.services.llm_router import MODELS, TaskType | **MEDIUM** |
| src/discord/bot.py | 	ests/discord/test_bot.py | rom src.discord.bot import GuinevereBot | **MEDIUM** (Test only) |
| src/discord/conversational_handler.py | 	ests/discord/test_conversational_handler.py | rom src.discord.conversational_handler import ... | **MEDIUM** (Test only) |

### 2.2 Documentation & StepPrompts References (Already Marked STALE)
The following files contain references that are **already annotated** with <!-- STALE: ... --> comments, indicating awareness of obsolescence:
- stepprompts/StepPrompts.md (12+ references to GuinevereBot, commands.Bot, discord.Client)
- esearch-reports/stepprompts-audit/stale-refs-sweep.md
- esearch-reports/stepprompts-audit/execution/cleanup-report.md
- docs/setup-evidence/adr-035/verification.md

### 2.3 Internal Cross-References
- src/hermes/__init__.py imports HermesSessionAdapter from session_adapter.py and contains docstrings referencing conversational_handler.py.
- src/discord/permissions.py imports CHANNELS, get_token from src/discord/guild_setup.py.

---

## 3. Old Pattern References Sweep

### 3.1 commands.Bot / discord.ext.commands
- **Found in**: 15 files, 50+ matches.
- **Key locations**: 	ests/discord/test_bot.py, stepprompts/StepPrompts.md (marked STALE), esearch-reports/stepprompts-audit/.
- **Assessment**: Safe to delete from source code post-cutover. Test files will need rewriting or deletion. StepPrompts references are already flagged.

### 3.2 GuinevereBot
- **Found in**: 17 files, 50+ matches.
- **Key locations**: src/discord/bot.py (definition), 	ests/discord/test_bot.py, stepprompts/StepPrompts.md (marked STALE), src/discord/shadow_pipeline.py (docstring).
- **Assessment**: Class definition will be deleted. Docstrings in shadow_pipeline.py and hermes_conversational.py should be updated to reference "Hermes gateway" instead.

### 3.3 conversational_handler
- **Found in**: 18 files, 50+ matches.
- **Key locations**: src/discord/conversational_handler.py, src/hermes/session_adapter.py (docstrings), 	ests/, docs/setup-evidence/.
- **Assessment**: Core legacy file. Docstrings in session_adapter.py and __init__.py referencing it should be cleaned up post-deletion.

### 3.4 session_adapter
- **Found in**: 21 files, 50+ matches.
- **Key locations**: src/hermes/__init__.py, 	ests/hermes/, dr/ADR-035-hermes-migration.md, docs/setup-evidence/.
- **Assessment**: ADR-035 explicitly lists this for deletion. src/hermes/__init__.py will need the import removed.

### 3.5 memory_bridge
- **Found in**: 7 files, 50+ matches.
- **Key locations**: src/discord/conversational_handler.py, src/discord/hermes_conversational.py, migrations/phase-3/004-hermes-memory-bridge-rbac.sql, 	ests/hermes/.
- **Assessment**: Phase 3 already deprecated this in favor of memory_plugin. The SQL migration file should be **retained** for historical rollback purposes, but the Python module can be deleted.

---

## 4. Deletion Risk Assessment & Mitigation

| Risk Category | Files Affected | Risk Level | Mitigation Strategy |
|---|---|---|---|
| **Hermes Plugin Breakage** | src/discord/commands.py | **HIGH** | Extract command_categories to a shared utility (e.g., src/core/constants.py) or inline into src/hermes_plugins/commands_high/help.py **before** deleting commands.py. |
| **Discord Bridge Breakage** | src/discord/conversational_handler.py, src/hermes/memory_bridge.py | **HIGH** | Ensure src/discord/hermes_conversational.py is fully migrated to Hermes native memory hooks before deleting memory_bridge.py. |
| **LLM Routing Breakage** | src/core/services/llm_router.py | **MEDIUM** | Verify Hermes native LLM routing is fully operational and hermes_conversational.py no longer imports MODELS or TaskType. |
| **Test Suite Failure** | 	ests/discord/ | **MEDIUM** | Archive or delete 	ests/discord/test_bot.py, 	est_conversational_handler.py, 	est_startup.py, 	est_cmd_*.py. Update 	ests/discord/conftest.py to remove discord.ext.commands shadowing. |
| **Documentation Drift** | stepprompts/StepPrompts.md, docs/setup-evidence/ | **LOW** | Most references are already marked STALE. Run a final cleanup pass to remove or archive stale step prompts. |
| **Import Chain in Hermes** | src/hermes/__init__.py | **LOW** | Remove rom .session_adapter import HermesSessionAdapter and update module docstrings. |

---

## 5. Recommended Deletion Sequence (Phase 7)

1. **Preparation (Pre-Deletion)**:
   - [ ] Migrate command_categories out of src/discord/commands.py to src/hermes_plugins/commands_high/help.py or src/core/constants.py.
   - [ ] Remove rom .session_adapter import HermesSessionAdapter from src/hermes/__init__.py.
   - [ ] Update docstrings in src/hermes/session_adapter.py, src/discord/shadow_pipeline.py, and src/discord/hermes_conversational.py to remove GuinevereBot/conversational_handler references.

2. **Source Code Deletion**:
   - [ ] Delete src/discord/ directory entirely (after verifying no remaining imports).
   - [ ] Delete src/hermes/session_adapter.py.
   - [ ] Delete src/hermes/memory_bridge.py.
   - [ ] Delete src/core/services/llm_router.py.

3. **Test Suite Cleanup**:
   - [ ] Delete 	ests/discord/ directory.
   - [ ] Delete 	ests/hermes/test_memory_bridge.py.
   - [ ] Update 	ests/hermes/conftest.py or 	est_safety_plugin.py to remove session_adapter import prevention hacks.

4. **Documentation & Evidence Archival**:
   - [ ] Move stepprompts/StepPrompts.md to stepprompts/archive/StepPrompts-v1.md (or perform in-place STALE block removal if approved).
   - [ ] Archive docs/setup-evidence/P2/ and docs/setup-evidence/phase-3/ to docs/setup-evidence/archive/.
   - [ ] **Retain** migrations/phase-3/004-hermes-memory-bridge-rbac.sql for historical rollback reference (do not delete SQL migrations).

5. **Post-Deletion Verification**:
   - [ ] Run uv run python -m pytest tests/ -v to ensure no import errors remain.
   - [ ] Run uv run python -c "import src.hermes; print('Hermes init OK')" to verify clean module initialization.
   - [ ] Run lsp_diagnostics on src/ to confirm zero eportMissingImports errors.

---

## 6. Auditor Gate Checklist

- [x] File existence and line counts verified via PowerShell.
- [x] Import dependency map generated via grep across workspace.
- [x] Old pattern references (commands.Bot, GuinevereBot, etc.) swept and categorized.
- [x] Risk assessment completed with explicit mitigation strategies.
- [x] Deletion sequence ordered to prevent cascade failures.
- [ ] **PENDING**: Parent verification of this report before Phase 7 execution.
- [ ] **PENDING**: Auditor gate pass on final deletion PR.

---
*Generated by Guinevere Autonomous Agent | ADR-035 Phase 6-7 Planning*
