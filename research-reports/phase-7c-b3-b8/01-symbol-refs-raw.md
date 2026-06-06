# Symbol Reference Report — Phase 7c (B3-B8) Deprecated Surface Dependencies

**Generated:** 2026-06-06  
**Targets:** command_count, command_categories, command_catalog, is_faiz_interaction  
**Scope:** Entire C:\Users\faizz\guinevere codebase (source, tests, docs, evidence, reports)

---

## 1. command_count

### 1.1 Definitions

| File | Line | Type | Content |
|------|------|------|---------|
| src/discord/commands.py | 261 | **function definition** | def command_count() -> int: |
| src/hermes_plugins/command_catalog.py | 49 | **function definition** | def command_count() -> int: |

### 1.2 Direct Imports / Calls

| File | Line | Type | Content |
|------|------|------|---------|
| 	ests/discord/test_cmd_mood.py | 270 | **docstring comment** | """Importing command_count must return the canonical registry size and be safe.""" |
| 	ests/discord/test_cmd_mood.py | 273 | **import** | rom src.discord.commands import command_count |
| 	ests/discord/test_cmd_mood.py | 275 | **call (assert)** | ssert command_count() == 35 |
| 	ests/discord/test_bot.py | 172 | **call (assert)** | ssert src.discord.commands.command_count() == 33 |

### 1.3 Local Helper with Same Name (different file)

| File | Line | Type | Content |
|------|------|------|---------|
| src/hermes_plugins/commands_high/help.py | 71 | **local function definition** | def _compute_command_count(categories: dict[str, tuple[str, ...]]) -> int: |
| src/hermes_plugins/commands_high/help.py | 89 | **call (local helper)** | cmd_count = _compute_command_count(cats) |
| src/discord/cmd_help.py | 249 | **local function definition** | def _compute_command_count(categories: dict[str, tuple[str, ...]]) -> int: |
| src/discord/cmd_help.py | 325 | **call (local helper)** | cmd_count = _compute_command_count(data.categories) |

### 1.4 Log / Metric Usage (unrelated context)

| File | Line | Type | Content |
|------|------|------|---------|
| src/mcp/tools/redis_tool.py | 402 | **log dict key (unrelated)** | command_counts={ — logging Redis tool registration counts, NOT related to command registry |

### 1.5 Doc / Report / Evidence References (informational)

| File | Line | Type | Content |
|------|------|------|---------|
| udit-reports/P2/STEP-P2-010/step-p2-010-auditor-report.md | 31 | doc ref | ` command_count() returns **33**. Category breakdown matches DiscordUXSpec §11: ` |
| esearch-reports/phase-7c-execution/05-archive-patterns.md | 178 | doc ref | rom src.discord.commands import command_count (migration plan) |
| esearch-reports/phase-7c-execution/01-import-deps.md | 109 | doc ref | commands.py exports ... command_count ... |
| esearch-reports/phase-7c-execution/01-import-deps.md | 221 | doc ref | ssert src.discord.commands.command_count() == 33 |
| esearch-reports/phase-7c-execution/01-import-deps.md | 252 | doc ref | rom src.discord.commands import command_count |
| esearch-reports/phase-7c-execution/01-import-deps.md | 285 | doc ref | test dependency noted |
| esearch-reports/phase-7c-execution/01-import-deps.md | 346, 356 | doc ref | migration options discussion |
| esearch-reports/phase-7c-execution/01-import-deps.md | 427, 454, 467, 502, 508 | doc ref | migration plan steps |
| esearch-reports/phase-7c-b3-b8/01-test-import-scan-raw.md | 5, 13, 42-43, 46, 166, 171, 466, 469-470, 490-491, 509 | doc ref | test dependency scan |
| esearch-reports/phase-7c-b3-b8/01-remaining-imports.md | 202, 210, 223, 249 | doc ref | remaining imports tracking |
| udit-reports/P2/batch-p2-010-012-auditor-report.md | 292 | doc ref | command_count() returns 33 |
| esearch-reports/phase-7-execution/05-deprecated-files.md | 52, 156, 226 | doc ref | deprecated file impact analysis |
| esearch-reports/phase-4-execution/01-mcp-state.md | 402 | doc ref | log output from redis_tool |
| docs/setup-evidence/hermes-phase2-discord/audit-raw/plugins-high.txt | 705, 725 | doc ref | original audit artifact |
| docs/setup-evidence/hermes-migration/phase-7c/STEP-7C-S1/verification.md | 36, 57 | doc ref | verification evidence |
| docs/setup-evidence/hermes-migration/phase-7c/STEP-7C-S1/auditor-gate.md | 25 | doc ref | auditor evidence |
| docs/setup-evidence/hermes-migration/phase-7c/phase-7c-safe-subset-plan.md | 109 | doc ref | plan reference |
| docs/setup-evidence/P2/STEP-P2-013/verification.md | 150 | doc ref | P2 verification |
| docs/setup-evidence/P2/STEP-P2-012/verification.md | 94, 289 | doc ref | P2 verification |
| docs/setup-evidence/P2/STEP-P2-012/p2-012-implementation-summary.md | 71 | doc ref | P2 summary |
| docs/setup-evidence/P2/STEP-P2-010/verification.md | 35, 46, 162, 165 | doc ref | P2 verification |
| docs/setup-evidence/P2/STEP-P2-010/p2-010-implementation-summary.md | 31, 47, 51, 72 | doc ref | P2 summary |
| docs/setup-evidence/P2/batch-plan-013-016.md | 207 | doc ref | P2 batch plan |
| docs/setup-evidence/P2/research/local-discord-structure.md | 32, 330, 505 | doc ref | P2 research |
| docs/setup-evidence/P2/research/discordpy-bot-architecture-p2-017-019.md | 648 | doc ref | P2 research (unrelated self.command_count = 0) |

---

## 2. command_categories

### 2.1 Definitions

| File | Line | Type | Content |
|------|------|------|---------|
| src/discord/commands.py | 267 | **function definition** | def command_categories() -> dict[str, tuple[str, ...]]: |
| src/hermes_plugins/command_catalog.py | 44 | **function definition** | def command_categories() -> dict[str, tuple[str, ...]]: |

### 2.2 Direct Imports / Calls (Source Code)

| File | Line | Type | Content |
|------|------|------|---------|
| src/hermes_plugins/commands_high/help.py | 13 | **import** | rom src.hermes_plugins.command_catalog import command_categories as _command_categories |
| src/hermes_plugins/commands_high/help.py | 86 | **call** | cats = categories if categories is not None else _command_categories() |
| src/discord/cmd_help.py | 279 | **import (lazy)** | rom .commands import command_categories (inside uild_help_embed_data function) |
| src/discord/cmd_help.py | 281 | **call** | cats = categories if categories is not None else command_categories() |

### 2.3 Doc / Report / Evidence References

| File | Line | Type | Content |
|------|------|------|---------|
| udit-reports/P2/STEP-P2-014/step-p2-014-auditor-report.md | 29, 37, 44 | doc ref | auditor checks |
| esearch-reports/phase-7c-execution/01-import-deps.md | 48, 109, 128, 148, 152-153, 335, 337, 345-346, 356, 372, 402, 406, 490, 502 | doc ref | import dependency analysis |
| esearch-reports/phase-7c-b3-b8/01-remaining-imports.md | 16, 120, 124, 127, 223, 233, 262, 266, 283 | doc ref | remaining blockers |
| esearch-reports/phase-7-execution/05-deprecated-files.md | 51, 54, 187, 197, 233, 234, 254, 302 | doc ref | deprecated file impact |
| esearch-reports/phase-6-7-planning/recheck-context-phase7-sections.md | 58, 91, 443 | doc ref | planning |
| esearch-reports/phase-6-7-planning/06-deprecated-files.md | 42, 97, 109 | doc ref | deprecated planning |
| docs/setup-evidence/hermes-phase2-discord/verification-S3.1.md | 51 | doc ref | verification |
| esearch-reports/phase-2/agent-1-discord-inventory.md | 36 | doc ref | inventory |
| docs/setup-evidence/hermes-phase2-discord/audit-raw/verification-reports.txt | 56 | doc ref | verification |
| docs/setup-evidence/hermes-phase2-discord/audit-raw/plugins-high.txt | 720, 722 | doc ref | original audit artifact |
| docs/setup-evidence/hermes-migration/phase-7c/STEP-7C-S1/verification.md | 36, 58, 85 | doc ref | migration verification |
| docs/setup-evidence/hermes-migration/phase-7c/STEP-7C-S1/auditor-gate.md | 16, 25 | doc ref | migration auditor |
| docs/setup-evidence/hermes-migration/phase-7c/phase-7c-safe-subset-plan.md | 109 | doc ref | plan |
| docs/setup-evidence/hermes-migration/batch-plan-phase-7.md | 1138, 1207 | doc ref | batch plan |
| docs/setup-evidence/P2/STEP-P2-014/verifiers/lsp-static-verifier.md | 22 | doc ref | static verifier |
| docs/setup-evidence/P2/STEP-P2-014/verification.md | 16, 78, 79, 102, 140, 177 | doc ref | P2 verification |
| docs/setup-evidence/P2/STEP-P2-014/p2-014-implementation-summary.md | 37 | doc ref | P2 summary |
| docs/setup-evidence/P2/STEP-P2-010/p2-010-implementation-summary.md | 31 | doc ref | P2 summary |
| esearch-reports/P2/p2-013-016-code-patterns-ast-report.md | 227, 245, 246, 251, 260, 601 | doc ref | AST patterns |
| docs/setup-evidence/P2/research/step-prompts-017-019.md | 27 | doc ref | research |
| docs/setup-evidence/P2/research/local-discord-structure.md | 32, 44, 74, 416, 449, 499 | doc ref | research |
| docs/setup-evidence/P2/research/local-command-callbacks-p2-017.md | 68, 162, 181 | doc ref | research |
| docs/setup-evidence/P2/batch-plan-013-016.md | 62, 191 | doc ref | batch plan |

---

## 3. command_catalog

### 3.1 Module File

| File | Line | Type | Content |
|------|------|------|---------|
| src/hermes_plugins/command_catalog.py | 1-51 | **module file** | Hermes-native command catalog — entire file (defines command_categories() and command_count()) |

### 3.2 Imports

| File | Line | Type | Content |
|------|------|------|---------|
| src/hermes_plugins/commands_high/help.py | 13 | **import** | rom src.hermes_plugins.command_catalog import command_categories as _command_categories |

### 3.3 Doc / Evidence References

| File | Line | Type | Content |
|------|------|------|---------|
| esearch-reports/phase-7c-b3-b8/02-test-deprecated-imports.md | 158, 260, 316, 358 | doc ref | test migration plan |
| esearch-reports/phase-7c-b3-b8/01-remaining-imports.md | 16, 262 | doc ref | remaining imports |
| esearch-reports/phase-7-execution/05-deprecated-files.md | 197 | doc ref | deprecated plan |
| docs/setup-evidence/hermes-migration/phase-7c/STEP-7C-S1/verification.md | 13, 36, 58, 74 | doc ref | verification |
| docs/setup-evidence/hermes-migration/phase-7c/STEP-7C-S1/auditor-gate.md | 15, 16, 25 | doc ref | auditor |
| docs/setup-evidence/hermes-migration/phase-7c/phase-7c-safe-subset-plan.md | 77, 93, 109 | doc ref | plan |
| docs/setup-evidence/hermes-migration/phase-7c/phase-7c-safe-subset-completion-report.md | 31, 32, 52 | doc ref | completion |
| docs/setup-evidence/hermes-migration/phase-7c/AUDIT-import-cleanup.md | 31, 32, 38 | doc ref | import cleanup |
| docs/setup-evidence/hermes-migration/batch-plan-phase-7.md | 1144 | doc ref | batch plan |

---

## 4. is_faiz_interaction

### 4.1 Primary Definition

| File | Line | Type | Content |
|------|------|------|---------|
| src/discord/commands.py | 288 | **function definition** | def is_faiz_interaction(interaction: object) -> bool: |

### 4.2 Local Duplicate Definitions (Surveillance Commands)

| File | Line | Type | Content |
|------|------|------|---------|
| src/discord/cmd_surveillance_status.py | 48 | **local function definition** | def is_faiz_interaction(interaction: Any) -> bool: |
| src/discord/cmd_surveillance_resume.py | 58 | **local function definition** | def is_faiz_interaction(interaction: Any) -> bool: |
| src/discord/cmd_surveillance_pause.py | 58 | **local function definition** | def is_faiz_interaction(interaction: Any) -> bool: |

### 4.3 All Direct Import + Call Sites (Source Code — 31 cmd_*.py files + tests)

Each follows the pattern: rom .commands import is_faiz_interaction / if not is_faiz_interaction(interaction):

| File | Import Line | Import Content | Call Line | Call Content |
|------|-------------|---------------|-----------|-------------|
| src/discord/cmd_approve.py | 36 | rom .commands import is_faiz_interaction | 38 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_approve_all.py | 36 | rom .commands import is_faiz_interaction | 38 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_backup_now.py | 39 | rom .commands import is_faiz_interaction | 41 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_budget.py | 526 | rom .commands import is_faiz_interaction | 528 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_casual.py | 43 | rom .commands import is_faiz_interaction | 45 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_clear_cache.py | 45 | rom .commands import is_faiz_interaction | 47 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_consent.py | 69 | rom .commands import is_faiz_interaction | 71 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_cost.py | 582 | rom .commands import is_faiz_interaction | 584 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_cost_alert.py | 137 | rom .commands import is_faiz_interaction | 139 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_deny.py | 36 | rom .commands import is_faiz_interaction | 38 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_evidence.py | 127 | rom .commands import is_faiz_interaction | 129 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_focus.py | 50 | rom .commands import is_faiz_interaction | 52 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_health_check.py | 129 | rom .commands import is_faiz_interaction | 131 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_help.py | 354 | rom .commands import is_faiz_interaction | 356 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_history.py | 49 | rom .commands import is_faiz_interaction | 51 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_loops.py | 92 | rom .commands import is_faiz_interaction | 94 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_loop_pause.py | 36 | rom .commands import is_faiz_interaction | 38 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_loop_priority.py | 44 | rom .commands import is_faiz_interaction | 46 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_loop_resume.py | 37 | rom .commands import is_faiz_interaction | 39 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_loop_start.py | 327 | rom .commands import is_faiz_interaction | 329 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_loop_stop.py | 375 | rom .commands import is_faiz_interaction | 377 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_memory_add.py | 338 | rom .commands import is_faiz_interaction | 340 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_memory_export.py | 203 | rom .commands import is_faiz_interaction | 205 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_memory_forget.py | 135 | rom .commands import is_faiz_interaction | 137 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_memory_search.py | 358 | rom .commands import is_faiz_interaction | 360 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_mood.py | 378 | rom .commands import is_faiz_interaction | 380 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_new_session.py | 36 | rom .commands import is_faiz_interaction | 38 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_punishment.py | 84 | rom .commands import is_faiz_interaction | 86 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_restart_service.py | 53 | rom .commands import is_faiz_interaction | 55 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_reward.py | 68 | rom .commands import is_faiz_interaction | 70 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_safeword.py | 557 | rom .commands import is_faiz_interaction | 559 | if not is_faiz_interaction(interaction): |
| src/discord/cmd_status.py | 380 | rom .commands import is_faiz_interaction | 382 | if not is_faiz_interaction(interaction): |

### 4.4 Surveillance Command Self-Contained Usage (local definition, not import)

| File | Line | Type | Content |
|------|------|------|---------|
| src/discord/cmd_surveillance_status.py | 290 | **call** | if not is_faiz_interaction(interaction): (calls local version at line 48) |
| src/discord/cmd_surveillance_status.py | 360 | **in __all__** | "is_faiz_interaction", |
| src/discord/cmd_surveillance_resume.py | 95 | **call** | if not is_faiz_interaction(interaction): (calls local version at line 58) |
| src/discord/cmd_surveillance_resume.py | 178 | **in __all__** | "is_faiz_interaction", |
| src/discord/cmd_surveillance_pause.py | 91 | **call** | if not is_faiz_interaction(interaction): (calls local version at line 58) |
| src/discord/cmd_surveillance_pause.py | 180 | **in __all__** | "is_faiz_interaction", |

### 4.5 Tests

| File | Line | Type | Content |
|------|------|------|---------|
| 	ests/surveillance/test_discord_commands.py | 4 | **docstring** | ` `is_faiz_interaction` with mocked Discord interactions. ` |
| 	ests/surveillance/test_discord_commands.py | 22 | **import** | is_faiz_interaction, |
| 	ests/surveillance/test_discord_commands.py | 85 | **comment** | # Tests: is_faiz_interaction |
| 	ests/surveillance/test_discord_commands.py | 89 | **test function** | def test_is_faiz_interaction_returns_true_for_owner( |
| 	ests/surveillance/test_discord_commands.py | 93 | **call** | ssert is_faiz_interaction(mock_faiz_interaction) is True |
| 	ests/surveillance/test_discord_commands.py | 96 | **test function** | def test_is_faiz_interaction_returns_false_for_non_owner( |
| 	ests/surveillance/test_discord_commands.py | 100 | **call** | ssert is_faiz_interaction(mock_non_faiz_interaction) is False |
| 	ests/surveillance/test_discord_commands.py | 103 | **test function** | def test_is_faiz_interaction_returns_false_when_guild_none() -> None: |
| 	ests/surveillance/test_discord_commands.py | 108 | **call** | ssert is_faiz_interaction(interaction) is False |
| 	ests/surveillance/test_discord_commands.py | 111 | **test function** | def test_is_faiz_interaction_returns_false_when_user_none() -> None: |
| 	ests/surveillance/test_discord_commands.py | 116 | **call** | ssert is_faiz_interaction(interaction) is False |
| 	ests/surveillance/test_discord_commands.py | 119 | **test function** | def test_is_faiz_interaction_with_missing_attrs() -> None: |
| 	ests/surveillance/test_discord_commands.py | 122 | **call** | ssert is_faiz_interaction(interaction) is False |
| 	ests/surveillance/test_discord_commands.py | 399 | **test function** | def test_is_faiz_interaction_type_safety() -> None: |
| 	ests/surveillance/test_discord_commands.py | 400 | **docstring** | """is_faiz_interaction returns bool, not None.""" |
| 	ests/surveillance/test_discord_commands.py | 401 | **call** | esult = is_faiz_interaction(object()) |

### 4.6 String References in StepPrompts and Research Docs

The symbol is_faiz_interaction appears in ~115 additional references across stepprompts/StepPrompts.md, research reports, evidence files, audit reports, and planning documents as a **text/string reference** (not code). Key representative locations:

| File | Approx. Lines | Context |
|------|--------------|---------|
| stepprompts/StepPrompts.md | 24333, 24374, 47670, 47683, 47880, 47883, 48134, 48146, 48161, 48250, 48452, 50582, 50600, 50684, 50702, 55947, 55953, 55960, 55966, 55986, 56000, 56013, 56036, 56134, 56153, 56783 | Step prompt instructions referencing the guard pattern |
| udit-reports/P7/D14-p8-readiness.md | 24 | readiness audit |
| udit-reports/P7/D04-safety-compliance.md | 110 | safety compliance |
| udit-reports/P5/P5-FINAL-AUDIT/D04-safety-boundary.md | 84 | P5 audit |
| udit-reports/P5/P5-FINAL-AUDIT/D03-security.md | 260-261 | P5 security audit |
| udit-reports/P3/P3-FINAL-AUDIT/P3-FINAL-AUDIT.md | 209 | P3 final audit |
| udit-reports/P3/P3-FINAL-AUDIT/D08-architecture-consistency.md | 68, 73, 91-92, 368, 398 | P3 architecture audit |
| udit-reports/P2/STEP-P2-015/step-p2-015-auditor-report.md | 28 | P2 auditor |
| udit-reports/P2/STEP-P2-014/step-p2-014-auditor-report.md | 32 | P2 auditor |
| udit-reports/P2/STEP-P2-013/step-p2-013-auditor-report.md | 29 | P2 auditor |
| udit-reports/P2/STEP-P2-010/step-p2-010-auditor-report.md | 63, 66, 164 | P2 auditor |
| udit-reports/P2/batch-p2-010-012-auditor-report.md | 21, 262, 266 | P2 batch auditor |
| evidence/phase-5/STEP-P5-020/verification.md | 21, 27, 42, 85 | P5 evidence |
| evidence/phase-5/P5-batch-plan.md | 246 | P5 batch plan |
| evidence/phase-5/auditor-gate-security.md | 23-24 | P5 auditor |
| evidence/phase-5/auditor-gate-discord-integration.md | 29, 45, 60 | P5 auditor |
| docs/setup-evidence/runtime-gaps/STEP-RG-010-014/verification.md | 74 | runtime gap |
| docs/setup-evidence/runtime-gaps/runtime-gap-audit.md | 125, 162, 212, 318 | runtime gap audit |
| docs/setup-evidence/P8/STEP-P8-018/verification.md | 25, 47, 63 | P8 verification |
| docs/setup-evidence/P8/STEP-P8-017/verification.md | 25, 48, 63 | P8 verification |
| docs/setup-evidence/P8/batch-plan-001-023.md | 314, 1919, 1943, 1955, 1958, 1996, 2008, 2011 | P8 batch plan |
| docs/setup-evidence/P7/STEP-P7-020/verification.md | 69 | P7 verification |
| docs/setup-evidence/P7/STEP-P7-020/auditor-gate.md | 31 | P7 auditor |
| docs/setup-evidence/P7/STEP-P7-019/verification.md | 11, 56, 104 | P7 verification |
| docs/setup-evidence/P7/STEP-P7-019/auditor-gate.md | 16, 33-37, 51 | P7 auditor |
| docs/setup-evidence/P3/STEP-P3-016-019/auditor-gate.md | 64, 224 | P3 auditor |
| docs/setup-evidence/P3/batch-plan-016-019.md | 48, 72 | P3 batch plan |
| docs/setup-evidence/P2/STEP-P2-015/verification.md | 19, 62 | P2 verification |
| docs/setup-evidence/P2/STEP-P2-015/p2-015-implementation-summary.md | 21 | P2 summary |
| docs/setup-evidence/P2/STEP-P2-014/verifiers/lsp-static-verifier.md | 24 | P2 verifier |
| docs/setup-evidence/P2/STEP-P2-014/verification.md | 19, 142 | P2 verification |
| docs/setup-evidence/P2/STEP-P2-014/p2-014-implementation-summary.md | 69 | P2 summary |
| docs/setup-evidence/P2/STEP-P2-013/verification.md | 20, 146 | P2 verification |
| docs/setup-evidence/P2/STEP-P2-013/p2-013-implementation-summary.md | 23 | P2 summary |
| docs/setup-evidence/P2/STEP-P2-012/verification.md | 24, 153, 174 | P2 verification |
| docs/setup-evidence/P2/STEP-P2-012/p2-012-implementation-summary.md | 40 | P2 summary |
| docs/setup-evidence/P2/STEP-P2-010/p2-010-implementation-summary.md | 31, 75, 126, 151 | P2 summary |
| docs/setup-evidence/P2/batch-plan-013-016.md | 117, 157, 200 | P2 batch plan |
| docs/setup-evidence/P2/research/step-prompts-017-019.md | 27 | P2 research |
| docs/setup-evidence/P2/research/local-command-callbacks-p2-017.md | 118, 120, 125, 128, 151, 180, 239 | P2 research |
| docs/setup-evidence/P2/research/local-discord-structure.md | 32, 44, 45, 64, 67, 108, 110 | P2 research |
| docs/setup-evidence/hermes-phase2-discord/verification-S3.1.md | 89 | verification |
| docs/setup-evidence/hermes-phase2-discord/audit-raw/verification-reports.txt | 94 | audit artifact |
| docs/setup-evidence/hermes-phase1/auditor-integration.md | 212, 217, 264 | phase 1 |
| docs/setup-evidence/p15-expansion/steps-batch-b.md | 1119, 1125, 1132, 1138, 1158, 1172, 1185, 1208, 1306, 1325 | P15 expansion |
| docs/setup-evidence/p15-expansion/steps-batch-c.md | 629 | P15 expansion |
| docs/setup-evidence/plans/p15-windows-daemon.md | 89, 491, 645 | P15 plan |
| esearch-reports/phase-7c-execution/05-archive-patterns.md | 186, 197, 229, 234, 296 | archive patterns |
| esearch-reports/phase-7c-execution/01-import-deps.md | 48, 109, 111-146, 354, 372, 396, 400, 489, 501 | import deps |
| esearch-reports/phase-7c-b3-b8/01-test-import-scan-raw.md | 5, 494, 517 | test scan |
| esearch-reports/phase-7c-b3-b8/01-remaining-imports.md | 96, 98, 222, 232, 265, 283 | remaining imports |
| esearch-reports/phase-6-execution/04-budget-state.md | 200 | budget state |
| esearch-reports/phase-2/agent-1-discord-inventory.md | 13 | inventory |
| esearch-reports/conversational-handler/research-report.md | 32 | research |
| esearch-reports/hermes-restructure/04-DISCORD-MIGRATION-GAP.md | 51, 121, 190, 292, 353 | migration gap |
| esearch-reports/hermes-restructure/03-DISCORD-GATEWAY.md | 171, 348 | gateway |
| esearch-reports/hermes-restructure/01-CLI-CAPABILITIES.md | 196 | CLI |
| esearch-reports/adr-035-prep/02-architecture-validation.md | 96, 547 | ADR-035 prep |
| esearch-reports/P5-audit/R02-integration-map.md | 11 | P5 audit |
| esearch-reports/P2/p2-013-016-local-discord-structure-report.md | 17, 52, 79, 154, 203 | P2 report |
| esearch-reports/P2/p2-013-016-code-patterns-ast-report.md | 69, 147, 198, 227, 250, 283, 331, 602 | P2 AST report |
| esearch-reports/P7/discord-command-patterns.md | 21, 34, 60, 97 | P7 patterns |
| esearch-reports/stepprompts-audit/P11-P15-audit.md | 178 | stepprompts audit |
| esearch-reports/p14-expansion/P14-021.md | 329, 347, 431, 449 | P14 expansion |
| esearch-reports/p14-expansion/P14-017.md | 70, 272 | P14 expansion |
| esearch-reports/p14-expansion/P14-016.md | 59, 72, 269, 272, 523, 535, 550 | P14 expansion |
| esearch-reports/p14-expansion/discord-patterns.md | 224, 337, 358 | P14 patterns |
| esearch-reports/p11-expansion/P11-019.md | 212, 253 | P11 expansion |

---

## 5. Summary: Live Code Dependencies (Excluding Docs/Reports)

### 5.1 command_count — Live Deps

| Dependency | File | Priority |
|-----------|------|----------|
| Import + call in test | 	ests/discord/test_cmd_mood.py | **HIGH** — test will break if commands.py archived |
| Call in test | 	ests/discord/test_bot.py | **HIGH** — test will break |
| Definition (active) | src/discord/commands.py | **PRIMARY SOURCE** (D03 — deprecated) |
| Definition (migrated) | src/hermes_plugins/command_catalog.py | **REPLACEMENT** (Hermes-native) |
| Local helper (unrelated) | src/hermes_plugins/commands_high/help.py | **LOW** — not derived from D03 |
| Local helper (unrelated) | src/discord/cmd_help.py | **LOW** — also deprecated path |

### 5.2 command_categories — Live Deps

| Dependency | File | Priority |
|-----------|------|----------|
| Import from D03 + call | src/discord/cmd_help.py | **RED BLOCKER** — 1 remaining import from commands.py (D03) |
| Import from replacement | src/hermes_plugins/commands_high/help.py | ✅ **ALREADY FIXED** — imports from command_catalog |
| Definition (active) | src/discord/commands.py | **PRIMARY SOURCE** (D03 — deprecated) |
| Definition (migrated) | src/hermes_plugins/command_catalog.py | **REPLACEMENT** (Hermes-native) |

### 5.3 command_catalog — Live Deps

| Dependency | File | Priority |
|-----------|------|----------|
| Module file | src/hermes_plugins/command_catalog.py | **ACTIVE** — the replacement module |
| Import | src/hermes_plugins/commands_high/help.py | ✅ **CLEAN** — uses replacement |

### 5.4 is_faiz_interaction — Live Deps

| Dependency | File | Priority |
|-----------|------|----------|
| Definition | src/discord/commands.py | **PRIMARY SOURCE** (D03 — deprecated) |
| Imported by 31 cmd_*.py files | src/discord/cmd_*.py | **RED BLOCKER** — cannot archive commands.py without extracting is_faiz_interaction |
| Local duplicate definitions (3 files) | src/discord/cmd_surveillance_*.py | **LOW** — self-contained, not dependent on D03 |
| Tests | 	ests/surveillance/test_discord_commands.py | Tests the local surveillance versions |

---

## 6. Key Findings

1. **is_faiz_interaction is the biggest blocker** — 31 cmd_*.py files import it from src.discord.commands (D03). Cannot archive D03 without extracting this function to a new file (e.g., _auth_guard.py).

2. **command_categories has exactly 1 remaining live import from D03** — src/discord/cmd_help.py:279. The Hermes plugin (help.py) has already been migrated to use command_catalog instead.

3. **command_count has 2 live test dependencies** on D03 — 	est_cmd_mood.py and 	est_bot.py. Both must be updated when D03 is archived.

4. **command_catalog is clean** — it's the replacement module with no remaining dependencies back to D03.

5. **All three surveillance commands** (cmd_surveillance_status.py, cmd_surveillance_pause.py, cmd_surveillance_resume.py) contain **local duplicates** of is_faiz_interaction — they do NOT import from commands.py. These are self-contained but represent code duplication.

