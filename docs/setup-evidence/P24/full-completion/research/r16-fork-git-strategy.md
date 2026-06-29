# R16: Fork + Git Strategy — In-Repo Root Layout

**Generated**: 2026-06-29
**Method**: Analysis of 5 source-of-truth documents, installed hermes-agent wheel metadata (RECORD, METADATA, top_level.txt, WHEEL, entry_points.txt), live repo structure, and git state.
**Scope**: Decision D1 implementation — in-repo root layout, guinevere/ namespace, pyproject.toml overhaul, git branch strategy.

---

## 1. Findings

### 1.1 Hermes v0.15.2 Installed Package Inventory

The installed wheel `hermes_agent-0.15.2.dist-info` in `.venv/Lib/site-packages/` contains **1501 non-dist-info files** (1509 total including dist-info). The `top_level.txt` lists **22 top-level items** organized as follows.

**9 Package Directories** (have `__init__.py`):

| Package | Location in site-packages | Description |
|---------|--------------------------|-------------|
| `acp_adapter/` | `site-packages/acp_adapter/` | Agent Communication Protocol adapter (10 files) |
| `agent/` | `site-packages/agent/` | Core agent internals: prompt_builder, context_engine, memory_manager, memory_provider, trajectory (large, 50+ files) |
| `cron/` | `site-packages/cron/` | Cron scheduler: jobs.py, scheduler.py |
| `gateway/` | `site-packages/gateway/` | Messaging gateway: run.py, session.py, hooks.py, platforms/ (20+ platform adapters) |
| `hermes_cli/` | `site-packages/hermes_cli/` | CLI subcommands: auth, plugins, skills_config, skills_hub (40+ files) |
| `plugins/` | `site-packages/plugins/` | Built-in plugins: memory, context_engine, browser, kanban, observability, platforms, etc. (19 subdirs) |
| `providers/` | `site-packages/providers/` | Model provider base: base.py |
| `tools/` | `site-packages/tools/` | Tool implementations: registry.py, delegate_tool.py, environments/ (50+ files) |
| `tui_gateway/` | `site-packages/tui_gateway/` | TUI gateway: entry.py, server.py, render.py, transport.py |

**13 Standalone Python Modules** (top-level `.py` files):

| Module | Size | Description |
|--------|------|-------------|
| `batch_runner.py` | 57 KB | Batch trajectory runner |
| `cli.py` | 696 KB | HermesCLI — interactive terminal UI (largest file) |
| `hermes_bootstrap.py` | 5 KB | Bootstrap/startup |
| `hermes_constants.py` | 17 KB | HERMES_HOME, profile-aware paths |
| `hermes_logging.py` | 14 KB | Logging infrastructure |
| `hermes_state.py` | 142 KB | SQLite session/state database with FTS5 |
| `hermes_time.py` | 3 KB | Time utilities |
| `model_tools.py` | 41 KB | Tool discovery, schema collection, dispatch |
| `run_agent.py` | 203 KB | AIAgent — core conversation loop |
| `toolset_distributions.py` | 12 KB | Tool groupings per distribution |
| `toolsets.py` | 29 KB | Tool groupings and platform presets |
| `trajectory_compressor.py` | 65 KB | Trajectory compression |
| `utils.py` | 13 KB | Shared utilities |

**Console Entry Points** (from `entry_points.txt`):
- `hermes` → `hermes_cli.main:main`
- `hermes-acp` → `acp_adapter.entry:main`
- `hermes-agent` → `run_agent:main`

**Data Files** (installed outside site-packages):
- `optional-skills/` — large collection of bundled skills (all `.md` and `.py` files)

Source: `.venv/Lib/site-packages/hermes_agent-0.15.2.dist-info/METADATA` (line 2), `top_level.txt`, `RECORD`, `entry_points.txt`.

---

### 1.2 Current Guinevere Repo State

**Git state** (`git status`, `git log`):
- Branch: `main`, HEAD at `af4b7b6` (not yet tagged)
- Remote: `origin` → `https://github.com/fazulfi/guinevere.git`
- **24 unpushed commits** on `main` (from `a8c9dbf` to `af4b7b6`)
- 2 modified tracked files, 28+ untracked items
- No existing `hermes-fork/` subdirectory

**Current `pyproject.toml`** (`pyproject.toml` lines 1-71):
- Build backend: `hatchling` with `packages = ["src"]` (line 48)
- Dependency: `"hermes-agent>=0.15"` (line 31)
- Python: `>=3.12` (line 5)
- Test paths: `testpaths = ["tests"]`, `pythonpath = ["src"]` (lines 58-60)
- Coverage source: `source = ["src"]` (line 63)

**Current `src/` directory** (28 subdirectories, 517 Python files):
Contains all P1-P22 Guinevere-specific code: `channels/`, `consent/`, `core/`, `discord/`, `finance/`, `financial/`, `gamification/`, `gmail/`, `hermes/`, `hermes_plugins/`, `knowledge_graph/`, `life_integrations/`, `life_kernel/`, `loops/`, `mcp/`, `memory/`, `observability/`, `persona/`, `projects/`, `self_improve/`, `surveillance/`, `wearable/`, `x_poster/`, `_deprecated/`.

**Import pattern in `src/`**: All internal imports use `from src.<module>...` prefix (confirmed by grep across 30+ files). Example from `src/gamification/__init__.py` line 17: `from src.gamification.models import (...)`.

---

### 1.3 In-Repo Root Layout: What Goes Where

Per P24 plan section 4.3 (line 256-301) and Decision D1, the target layout is:

```
guinevere/                          # REPO ROOT
├── run_agent.py                    # FROM HERMES (will be modified in M1-M17)
├── cli.py                          # FROM HERMES (will be modified)
├── batch_runner.py                 # FROM HERMES (unchanged)
├── hermes_bootstrap.py             # FROM HERMES (unchanged)
├── hermes_constants.py             # FROM HERMES (unchanged)
├── hermes_logging.py               # FROM HERMES (unchanged)
├── hermes_state.py                 # FROM HERMES (unchanged)
├── hermes_time.py                  # FROM HERMES (unchanged)
├── model_tools.py                  # FROM HERMES (unchanged)
├── toolset_distributions.py        # FROM HERMES (unchanged)
├── toolsets.py                     # FROM HERMES (unchanged)
├── trajectory_compressor.py        # FROM HERMES (unchanged)
├── utils.py                        # FROM HERMES (unchanged)
├── agent/                          # FROM HERMES (modified: agent_init.py, conversation_loop.py, system_prompt.py, memory_manager.py)
├── tools/                          # FROM HERMES (modified: delegate_tool.py)
├── gateway/                        # FROM HERMES (modified: run.py)
├── hermes_cli/                     # FROM HERMES (modified: config.py)
├── cron/                           # FROM HERMES (modified: jobs.py)
├── plugins/                        # FROM HERMES (unchanged)
├── providers/                      # FROM HERMES (unchanged)
├── acp_adapter/                    # FROM HERMES (unchanged)
├── tui_gateway/                    # FROM HERMES (unchanged)
├── optional-skills/                # FROM HERMES (data files)
├── guinevere/                      # NEW: all 17 M1-M17 modules (absorbed from src/)
│   ├── __init__.py
│   ├── config.py                   # M1: Pydantic config models
│   ├── config.yaml                 # M1: default config template
│   ├── consciousness/              # M3
│   ├── emotions/                   # M4
│   ├── memory/                     # M6
│   ├── governance/                 # M7
│   ├── tools/                      # M8
│   ├── life_kernel/                # M9
│   ├── self_modify/                # M10
│   ├── personality/                # M12
│   ├── discord/                    # M13
│   ├── channels/                   # M14
│   ├── http/                       # M15
│   ├── surveillance/               # M16
│   ├── observability/              # M16
│   └── production/                 # M17
├── config/                         # Instance config
│   ├── guinevere.yaml
│   └── pharsa.yaml
├── pyproject.toml                  # MODIFIED: new build config
├── AGENTS.md                       # Operating contract
└── SOUL.md                         # Context file
```

**Critical rule**: ALL of the above Hermes files go at the repo root. There is NO `hermes-agent/` or `hermes-fork/` subdirectory. This is the in-repo root layout decision.

Source: P24 plan section 4.3, lines 258-301.

---

### 1.4 Pyproject.toml Changes Required

The current `pyproject.toml` requires **substantial restructuring**. Here is a detailed breakdown of every change needed.

#### 1.4.1 Build System — packages list

**Current** (`pyproject.toml` line 47-48):
```toml
[tool.hatch.build.targets.wheel]
packages = ["src"]
```

**Required change**:
```toml
[tool.hatch.build.targets.wheel]
packages = [
    "agent",
    "tools",
    "gateway",
    "hermes_cli",
    "cron",
    "plugins",
    "providers",
    "acp_adapter",
    "tui_gateway",
    "guinevere",
]
```

**Problem with standalone modules**: Hatchling's `packages` directive expects **directories** with `__init__.py`. The 13 standalone Hermes `.py` files at repo root (`run_agent.py`, `cli.py`, `batch_runner.py`, `hermes_bootstrap.py`, `hermes_constants.py`, `hermes_logging.py`, `hermes_state.py`, `hermes_time.py`, `model_tools.py`, `toolset_distributions.py`, `toolsets.py`, `trajectory_compressor.py`, `utils.py`) are **not packages** and cannot be listed in `packages`. Hatchling's default discovery with explicit `packages` does NOT automatically include loose `.py` files at the build root.

**Solutions** (ranked by preference):

1. **Use hatchling `force-include`** (cleanest):
```toml
[tool.hatch.build.targets.wheel.force-include]
"run_agent.py" = "run_agent.py"
"cli.py" = "cli.py"
"batch_runner.py" = "batch_runner.py"
"hermes_bootstrap.py" = "hermes_bootstrap.py"
"hermes_constants.py" = "hermes_constants.py"
"hermes_logging.py" = "hermes_logging.py"
"hermes_state.py" = "hermes_state.py"
"hermes_time.py" = "hermes_time.py"
"model_tools.py" = "model_tools.py"
"toolset_distributions.py" = "toolset_distributions.py"
"toolsets.py" = "toolsets.py"
"trajectory_compressor.py" = "trajectory_compressor.py"
"utils.py" = "utils.py"
```

2. **Or use hatchling `include` pattern**:
```toml
[tool.hatch.build.targets.wheel]
packages = ["agent", "tools", "gateway", "hermes_cli", "cron", "plugins", "providers", "acp_adapter", "tui_gateway", "guinevere"]
include = ["*.py"]
```

**Note**: The `include = ["*.py"]` approach is simpler but may pull in unwanted `.py` files at repo root (e.g., `main.py`, `manager.py`, `scheduler.py`, `guardian.py` which are existing Guinevere files). The `force-include` approach is safer.

#### 1.4.2 Dependencies

**Current** (`pyproject.toml` line 31):
```toml
"hermes-agent>=0.15",
```

**Required change**: REMOVE this line entirely. Since Hermes code is now vendored into the repo root, it is no longer a pip dependency. All Hermes transitive dependencies (from `METADATA` Requires-Dist) must be explicitly added:

```toml
# hermes-agent v0.15.2 dependencies (now vendored, not pip-installed)
"openai==2.24.0",
"python-dotenv>=1.2.2",    # already present, may need pin
"fire==0.7.1",
"httpx[socks]>=0.28",      # already present
"tenacity>=9",              # already present
"pyyaml==6.0.3",
"ruamel.yaml==0.18.17",
"requests==2.33.0",
"jinja2==3.1.6",
"pydantic>=2",              # already present
"prompt_toolkit==3.0.52",
"croniter>=6.0.0",
"PyJWT[crypto]==2.12.1",
"psutil==7.2.2",
```

Source: `.venv/Lib/site-packages/hermes_agent-0.15.2.dist-info/METADATA` lines 16-37.

#### 1.4.3 Console Scripts

**Current**: None defined in guinevere's pyproject.toml.

**Required**: Add the 3 Hermes entry points:
```toml
[project.scripts]
hermes = "hermes_cli.main:main"
hermes-acp = "acp_adapter.entry:main"
hermes-agent = "run_agent:main"
```

Source: `hermes_agent-0.15.2.dist-info/entry_points.txt`.

#### 1.4.4 Test and Coverage Configuration

**Current** (`pyproject.toml` lines 58-60, 63-64):
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.coverage.run]
source = ["src"]
```

**Required change**:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]           # root is now the package root

[tool.coverage.run]
source = ["agent", "tools", "gateway", "hermes_cli", "cron", "guinevere"]
```

#### 1.4.5 Ruff Configuration

**Current** (`pyproject.toml` line 50): `target-version = "py312"`

**No change needed** — Hermes also requires Python >=3.11, and guinevere already targets 3.12.

---

### 1.5 Git Strategy

#### 1.5.1 Handling the 24 Unpushed Commits

**CRITICAL**: The 24 unpushed commits on `main` MUST be pushed before any fork restructuring begins. These are P20-P22 production evidence and fixes that represent deployed state.

**Recommended sequence**:
1. `git push origin main` — push all 24 commits to remote
2. Verify remote matches local: `git log --oneline origin/main -5`
3. Tag the pre-fork state: `git tag pre-p24-fork-setup`
4. Create the fork branch from this clean state

#### 1.5.2 Branch Naming

Per P24 fork feasibility research (`p24-fork-feasibility-maintenance-research.md` lines 213-219):
- `main` — stable branch (current, pre-fork)
- `feat/p24-hermes-fork` — the fork integration branch (all M1-M17 work happens here)

The branch name should follow the existing convention seen in remote branches (28 `feat/guinevere/*` branches already exist).

#### 1.5.3 Fork Integration Steps (on `feat/p24-hermes-fork`)

```
1. git checkout -b feat/p24-hermes-fork
2. Clone hermes-agent at SHA 77a1650c78a4cb1813d8a81fa1da40a15b6a3ec5 to a temp dir
3. Copy all 22 top-level items (9 packages + 13 modules) + optional-skills/ into repo root
4. Create guinevere/ directory with __init__.py
5. Move relevant src/ subdirectories into guinevere/ (per wave plan)
6. Rewrite all `from src.<module>` imports to `from guinevere.<module>` (517 Python files)
7. Rewrite pyproject.toml (section 1.4 above)
8. Delete src/ entirely (final wave)
9. git add + commit
```

#### 1.5.4 Merge Strategy

The fork branch should use **squash merge** or **rebase** back into `main` once all M1-M17 modules pass. This keeps the `main` history clean. The 24 pre-fork commits remain as-is on `main`.

---

### 1.6 Source: Installed Wheel vs Git Clone

Per P24 plan section 4.1 (line 234): "PyPI attestation note: SHA `2bd1977d` reconciliation — PyPI-published wheel may differ from Git tag due to build-time transformations. Fork from Git SHA, not PyPI wheel."

**Recommended approach**: Clone from Git at SHA `77a1650c78a4cb1813d8a81fa1da40a15b6a3ec5`:

```bash
git clone --branch v2026.5.29.2 https://github.com/NousResearch/hermes-agent.git /tmp/hermes-upstream
cd /tmp/hermes-upstream && git checkout 77a1650c78a4cb1813d8a81fa1da40a15b6a3ec5
```

**Use the wheel for reference only** (verify file lists match, check for build-time transformations). The installed wheel at `.venv/Lib/site-packages/` serves as the known-working baseline.

**What NOT to copy from the wheel**:
- `hermes_agent-0.15.2.dist-info/` — package metadata, not needed in fork
- `__pycache__/` directories — compiled bytecode
- Any `.pyc` files

**What to copy from git clone**:
- All 22 top-level items listed in section 1.1
- `optional-skills/` directory
- `skills/` directory (if present in git repo)
- `tests/` directory (for parity testing)
- `SOUL.md`, `AGENTS.md`, `README.md`
- `.github/` directory (if present, for CI reference)

---

### 1.7 PEP 420 Flat Namespace Handling

PEP 420 (implicit namespace packages) is NOT needed here because both Hermes packages and `guinevere/` will have explicit `__init__.py` files. The approach is standard **PEP 420 flat namespace via regular packages**:

```
repo_root/          # Not a package itself (no __init__.py at root)
├── agent/          # Regular package (has __init__.py)
├── tools/          # Regular package
├── gateway/        # Regular package
├── guinevere/      # Regular package (has __init__.py)
└── ...
```

**Import resolution**: Python resolves `import agent` and `import guinevere` independently because both are in the Python path (either via `pip install -e .` or via `PYTHONPATH=.`).

**No namespace package magic needed**: Hatchling with explicit `packages = [...]` handles this correctly. Each package is independently importable.

**Key concern**: The `plugins/` package from Hermes and any `plugins/` directory in Guinevere must NOT conflict. Currently `src/hermes_plugins/` exists (not `src/plugins/`). The plan maps this to `guinevere/plugins/` or `guinevere/tools/` inside the `guinevere/` namespace, avoiding collision with Hermes's top-level `plugins/`.

---

### 1.8 Risks of In-Repo Root Layout vs Separate Fork Dir

#### 1.8.1 In-Repo Root Layout (D1 Decision)

**Advantages**:
- Single repo, single commit history, single deploy
- No inter-repo dependency management
- Direct file modifications possible (the plan requires direct core modifications per section 4.5)
- `pip install -e .` installs everything at once
- Simpler VPS deploy (one `git pull` + `pip install -e .`)

**Risks**:

| Risk | Severity | Description | Mitigation |
|------|----------|-------------|------------|
| Root directory pollution | MEDIUM | 22+ new items at repo root alongside 40+ existing items (main.py, manager.py, scheduler.py, etc.) | `.gitignore` cleanup; move stale root files to `legacy/` |
| Namespace collision | HIGH | Hermes `plugins/` vs any Guinevere `plugins/`; Hermes `utils.py` vs any Guinevere `utils.py` | Verify no naming conflicts before copy |
| Import rewrite scope | HIGH | 517 Python files in `src/` using `from src.<module>` need rewriting to `from guinevere.<module>` | Scripted sed/replace per wave |
| Hatchling discovery | MEDIUM | Standalone `.py` files at root need `force-include` or `include` patterns | Use `force-include` directive (section 1.4.1) |
| Git diff noise | MEDIUM | Initial commit will show 1501+ new files from Hermes | Atomic commit with clear message; separate from module implementation commits |
| Rollback complexity | LOW | Reverting to pre-fork state requires reverting a large commit | Tag pre-fork state; `git revert` or `git reset` to tag |
| .venv conflict | MEDIUM | Existing `.venv` has hermes-agent installed as pip package; after fork, both the vendored code and the pip package exist | `pip uninstall hermes-agent` after migration; remove from `pyproject.toml` |

#### 1.8.2 Alternative: Separate Fork Dir (NOT chosen)

If a `hermes-fork/` subdirectory were used instead:
- Would need `PYTHONPATH` manipulation to resolve imports
- `pip install -e .` from a subdirectory is non-trivial
- Hermes imports like `from agent.agent_init import ...` would break
- Cannot use Hermes CLI entry points without wrapping

**Verdict**: In-repo root is the correct choice for D1. The alternative is architecturally incompatible with Hermes's flat import structure.

---

### 1.9 Pyproject.toml Build System for Dual Packages

The final `pyproject.toml` must build a wheel containing BOTH Hermes code and Guinevere code. The complete target configuration:

```toml
[project]
name = "guinevere"
version = "0.2.0"  # bumped from 0.1.0 for fork milestone
description = "Guinevere AI Companion - Autonomous Agent System (Hermes v0.15.2 Fork)"
requires-python = ">=3.12"
dependencies = [
    # === Core framework ===
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "pydantic>=2",
    "pydantic-settings>=2",
    # === Database ===
    "sqlalchemy[asyncio]>=2",
    "pgvector>=0.2",
    "asyncpg>=0.30",
    "alembic>=1",
    "redis>=5",
    # === HTTP/Networking ===
    "httpx[socks]>=0.28",
    "aiohttp>=3",
    "requests==2.33.0",
    "websockets>=13",
    # === Hermes v0.15.2 transitive deps (now vendored) ===
    "openai==2.24.0",
    "fire==0.7.1",
    "pyyaml==6.0.3",
    "ruamel.yaml==0.18.17",
    "jinja2==3.1.6",
    "prompt_toolkit==3.0.52",
    "croniter>=6.0.0",
    "PyJWT[crypto]==2.12.1",
    "psutil==7.2.2",
    # === Existing guinevere deps ===
    "python-dotenv>=1",
    "apscheduler>=3",
    "sentry-sdk[fastapi]>=2",
    "prometheus-client>=0.21",
    "structlog>=24",
    "cryptography>=44",
    "discord.py>=2.4",
    "tenacity>=9",
    "typer>=0.15",
    "rich>=14",
    "passlib[bcrypt]>=1.7",
    "setuptools>=75",
    "markdownify>=0.14",
    "mcp>=1.0",
    "playwright>=1.56",
    "sentence-transformers>=5.5",
    "scipy>=1.17",
    "neonize>=0.3.18,<0.4.0",
    # NOTE: hermes-agent REMOVED — now vendored
]

[project.scripts]
hermes = "hermes_cli.main:main"
hermes-acp = "acp_adapter.entry:main"
hermes-agent = "run_agent:main"

[project.optional-dependencies]
test = ["pytest-cov>=7", "pytest-asyncio>=0.23"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = [
    # Hermes v0.15.2 packages (vendored)
    "agent",
    "tools",
    "gateway",
    "hermes_cli",
    "cron",
    "plugins",
    "providers",
    "acp_adapter",
    "tui_gateway",
    # Guinevere packages
    "guinevere",
]

[tool.hatch.build.targets.wheel.force-include]
# Hermes standalone modules (not packages, need explicit include)
"run_agent.py" = "run_agent.py"
"cli.py" = "cli.py"
"batch_runner.py" = "batch_runner.py"
"hermes_bootstrap.py" = "hermes_bootstrap.py"
"hermes_constants.py" = "hermes_constants.py"
"hermes_logging.py" = "hermes_logging.py"
"hermes_state.py" = "hermes_state.py"
"hermes_time.py" = "hermes_time.py"
"model_tools.py" = "model_tools.py"
"toolset_distributions.py" = "toolset_distributions.py"
"toolsets.py" = "toolsets.py"
"trajectory_compressor.py" = "trajectory_compressor.py"
"utils.py" = "utils.py"

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.mypy]
python_version = "3.12"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
asyncio_mode = "auto"

[tool.coverage.run]
source = ["agent", "tools", "gateway", "hermes_cli", "cron", "guinevere"]
omit = ["tests/*", "guinevere/_deprecated/*"]
branch = true

[tool.coverage.report]
fail_under = 80
show_missing = true
```

---

## 2. Disposition for P24

### 2.1 Pre-Requisites Before Any Module Work (Wave 0)

1. **Push 24 unpushed commits**: `git push origin main`
2. **Tag pre-fork state**: `git tag pre-p24-fork-setup af4b7b6`
3. **Create fork branch**: `git checkout -b feat/p24-hermes-fork`
4. **Clone upstream at SHA**: `git clone --depth 1 --branch v2026.5.29.2 https://github.com/NousResearch/hermes-agent.git /tmp/hermes-upstream && cd /tmp/hermes-upstream && git checkout 77a1650c78a4cb1813d8a81fa1da40a15b6a3ec5`
5. **Copy Hermes files** from clone to repo root (22 top-level items + optional-skills/)
6. **Create `guinevere/__init__.py`** at repo root
7. **Rewrite `pyproject.toml`** per section 1.9
8. **`pip uninstall hermes-agent`** from .venv
9. **`pip install -e .`** (editable install of the forked repo)
10. **Verify**: `python -c "import agent; import guinevere; print('OK')"`
11. **Commit**: `git add -A && git commit -m "feat(p24): fork hermes-agent v0.15.2 into repo root (D1 layout)"`

### 2.2 Wave-by-Wave Import Rewrite

Each wave that absorbs `src/<module>/` into `guinevere/<module>/` requires:
1. `git mv src/<module> guinevere/<module>`
2. Find-and-replace `from src.<module>` → `from guinevere.<module>` across ALL Python files
3. Update any sys.path or PYTHONPATH references
4. Run `python -m pytest tests/` to verify
5. Commit per wave

### 2.3 Final Cleanup (Last Wave)

1. Verify `src/` is empty (or contains only `_deprecated/` which is also moved)
2. `rm -rf src/`
3. Remove `pythonpath = ["src"]` from pyproject.toml (already done in section 1.9)
4. Remove `packages = ["src"]` (already done)
5. Final commit: `git commit -m "feat(p24): delete src/ — all code absorbed into guinevere/ and hermes fork"`

---

## 3. Risks

| # | Risk | Severity | Likelihood | Mitigation |
|---|------|----------|------------|------------|
| R1 | PyPI wheel differs from git SHA | HIGH | LOW | Verify key files between wheel and git clone; diff `run_agent.py` line counts |
| R2 | Namespace collision (plugins/, utils.py) | HIGH | MEDIUM | Audit root-level naming before copy; rename Guinevere duplicates |
| R3 | 517 files need import rewrite | MEDIUM | CERTAIN | Automated sed script; verify with `grep -r "from src\." .` after each wave |
| R4 | Hatchling standalone module inclusion | MEDIUM | HIGH | Use `force-include` directive; test with `python -m build --wheel` |
| R5 | Hermes transitive dependency conflicts | MEDIUM | MEDIUM | Pin Hermes deps explicitly; resolve version conflicts with existing deps |
| R6 | VPS deploy breakage during transition | HIGH | LOW | Use canary strategy from p24-vps-deploy-rollback-fork-research.md |
| R7 | Git history bloat from 1501+ file add | LOW | CERTAIN | Acceptable; single atomic commit; can use `git log --follow` for traceability |
| R8 | `cli.py` at 696 KB may cause tooling issues | LOW | LOW | Monitor ruff/mypy performance; exclude from strict linting if needed |

---

## 4. Verdict

**PASS** — The in-repo root layout (Decision D1) is fully implementable with hatchling.

**No blockers identified.** The key technical challenges (hatchling `packages` vs standalone modules, import rewriting, dependency migration) all have known solutions documented in this report.

**Estimated effort for Wave 0 (fork setup only)**: 2-3 hours including verification.

**Critical path**: Wave 0 must complete before any M1-M17 module work begins, because every module implementation depends on the Hermes code being present at the repo root and importable.

---

## 5. File Citations

| Source | Path | Lines Referenced |
|--------|------|-----------------|
| P24 Plan section 4 | `docs/setup-evidence/P24/plan/p24-hermes-native-fork-enterprise-plan.md` | 227-340 |
| Fork feasibility research | `docs/setup-evidence/P24/research/p24-fork-feasibility-maintenance-research.md` | 1-661 (full) |
| VPS deploy research | `docs/setup-evidence/P24/research/p24-vps-deploy-rollback-fork-research.md` | 1-582 (full) |
| Hermes external docs fork guide | `docs/setup-evidence/P24/research/research-wave-2/hermes-external-docs-fork-guide.md` | 1-1077 (full) |
| Current pyproject.toml | `pyproject.toml` | 1-71 (full) |
| hermes METADATA | `.venv/Lib/site-packages/hermes_agent-0.15.2.dist-info/METADATA` | 1-40 |
| hermes top_level.txt | `.venv/Lib/site-packages/hermes_agent-0.15.2.dist-info/top_level.txt` | 1-22 |
| hermes RECORD | `.venv/Lib/site-packages/hermes_agent-0.15.2.dist-info/RECORD` | 1-1509 |
| hermes entry_points.txt | `.venv/Lib/site-packages/hermes_agent-0.15.2.dist-info/entry_points.txt` | 1-4 |
| hermes WHEEL | `.venv/Lib/site-packages/hermes_agent-0.15.2.dist-info/WHEEL` | 1-4 |
| Git state | `git log --oneline -24`, `git branch -a`, `git remote -v` | HEAD at af4b7b6 |
| src/ import patterns | `src/gamification/__init__.py`, `src/hermes/adapter.py`, `src/hermes/safety_plugin.py` | Various lines using `from src.<module>` |

---

## 6. Parent Verification (2026-06-29)

Parent verified 4 specific claims from this report:

| Claim | Verification Command | Result |
|-------|---------------------|--------|
| r16 file exists on disk | `ls r16*` | **FAIL** — file not written by agent, returned inline. Parent wrote it now. |
| Cron/jobs.py exists (for M7 modification) | `ls cron/jobs.py` | **PASS** — exists with 1237 lines. Plan's MODIFY directive is correct. |
| x_poster/circuit_breaker.py exists (for M15 port) | `ls src/x_poster/circuit_breaker.py` | **PASS** — exists with 299 lines. |
| Optimizer.py has hard deps on loops submodules | `grep "from src.loops" optimizer.py` | **PASS** — lines 22-25 import audit_writer, budget, reflection, testing_gate. Real blocker for loops/ deletion. |
