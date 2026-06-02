# Research Report: UV-Based Python Project Structure Best Practices (2026)

**Date**: 2026-05-31
**Scope**: P1-004 — Guinevere Python project setup with UV + Python 3.12
**Sources**: Astral UV official docs, Python Packaging User Guide (PyPA), PEP 621, PEP 735, PEP 639, Hatchling docs, community guides

---

## Table of Contents

1. [UV pyproject.toml vs setup.cfg vs setup.py — Which to Use in 2026?](#1-uv-pyprojecttoml-vs-setupcfg-vs-setuppy)
2. [Modern Python Project Structure: src/ Layout vs Flat Layout](#2-src-layout-vs-flat-layout)
3. [UV with Hatchling Build Backend — Best Practices](#3-uv-with-hatchling-build-backend)
4. [pyproject.toml [project] Section — Recommended Fields](#4-pyprojecttoml-project-section)
5. [Multi-Package / Monorepo Structure (Sub-Packages)](#5-multi-package--monorepo-structure)
6. [__init__.py Conventions](#6-__init__py-conventions)
7. [UV Project Initialization: `uv init` vs Manual](#7-uv-project-initialization)
8. [Recommended Guinevere Project Structure](#8-recommended-guinevere-project-structure)
9. [References](#9-references)

---

## 1. UV pyproject.toml vs setup.cfg vs setup.py — Which to Use in 2026?

### Verdict: **pyproject.toml only. No setup.cfg, no setup.py.**

| File | Status in 2026 | Use Case |
|------|---------------|----------|
| `pyproject.toml` | **Standard (required)** | All metadata, build config, tool config |
| `setup.cfg` | **Deprecated for new projects** | Legacy. Do not use. |
| `setup.py` | **Deprecated for metadata** | Only if building C extensions programmatically |

**Why:**

- **PEP 621** (June 2020) standardized project metadata in `[project]` table of `pyproject.toml`. All modern build backends (hatchling, flit-core, pdm-backend, uv_build, setuptools ≥61.0) support it.
- **Poetry 2.0** (released Jan 2025) now also supports `[project]` table alongside `[tool.poetry]`.
- `setup.py` is **not deprecated** as a build system concept, but using it for metadata is obsolete. Keep it only if you need *programmatic* configuration (e.g., building C extensions via setuptools).
- `setup.cfg` is fully superseded by `pyproject.toml`'s `[project]` and `[tool.*]` tables.

**Sources**:
- [PyPA: Writing your pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) — "For new projects, use the `[project]` table"
- [PyPA: Is setup.py deprecated?](https://packaging.python.org/en/discussions/setup-py-deprecated/)
- [PEP 621](https://peps.python.org/pep-0621/) — Standardizes `[project]` metadata

### Decision for Guinevere: `pyproject.toml` only, no `setup.py`/`setup.cfg`.

---

## 2. src/ Layout vs Flat Layout

### Verdict: **Use src/ layout for all distributable packages.**

| Aspect | Flat Layout | src/ Layout |
|--------|------------|-------------|
| Code location | Root-level `package_name/` | `src/package_name/` |
| Test isolation | ❌ Tests may import local copy, not installed copy | ✅ Tests always import installed package |
| Build correctness | ❌ May include unwanted files in distribution | ✅ Explicit boundaries |
| Editable install safety | ❌ Adds project root files to import path | ✅ Only intended code is importable |
| Ease of quick scripts | ✅ Simple | ❌ Requires `uv run` or editable install |
| **Recommended for** | Quick scripts, prototypes | **Libraries, packages, distributable code** |

**Key reasons for src/ layout:**

1. **Prevents accidental usage of in-development copy** — Python adds the current working directory to `sys.path`. With flat layout, `from package import module` can import the local source instead of the installed version. This hides packaging bugs.
2. **Cleaner root** — `pyproject.toml`, `README.md`, `tests/`, `docs/`, config files stay at root. Only actual source code goes in `src/`.
3. **All build backends auto-detect src/ layout** — Hatchling, setuptools, uv_build all find packages under `src/` automatically.
4. **Industry consensus** — PyPA recommends src/ layout. uv's own `--lib` and `--package` init flags create src/ layout by default.

**Sources**:
- [PyPA: src layout vs flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)
- [pyOpenSci: Python Package Structure](https://www.pyopensci.org/python-package-guide/package-structure-code/python-package-structure.html) — "We strongly suggest you use the src/ layout"
- [Real Python: Project Layout](https://realpython.com/ref/best-practices/project-layout/) — "src/ layout is well suited for library code"

### Decision for Guinevere: **src/ layout** with `src/guinevere/` as the main package.

---

## 3. UV with Hatchling Build Backend

### Verdict: **Use hatchling as the build backend** (not uv_build).

### Why Hatchling over uv_build?

| Criterion | uv_build | Hatchling |
|-----------|----------|-----------|
| Maturity | Newer, Astral-native | Mature, PyPA-adjacent |
| Configuration | Via `[tool.uv.build-backend]` | Via `[tool.hatch.*]` tables |
| Build isolation | Tight uv integration | Works with any frontend |
| Namespace packages | Supported via `module-name` | Supported natively |
| Dynamic versioning | Manual | Via `hatch-vcs` or `hatch-ci` |
| Data files | `data` + `source-include` | `[tool.hatch.build.targets.*]` |
| **Recommendation** | Good for simple projects | **Better for complex multi-package** |

### Hatchling `[build-system]` Configuration

```toml
[build-system]
requires = ["hatchling>=1.27.0"]
build-backend = "hatchling.build"
```

**Best practices:**
- Pin `hatchling` minimum version (≥1.26 for PEP 639 license support, ≥1.27 for latest features)
- Do **not** add `hatch-vcs` unless you need Git-based dynamic versioning (for now, static version is fine)
- Hatchling auto-discovers `src/` layout — no need for `[tool.hatch.build.targets.sdist]` include overrides for standard projects

### Using Hatchling with UV

UV and Hatchling work perfectly together:
- `uv add` manages dependencies
- `uv lock` creates lockfile
- `uv build` calls hatchling.build as the build backend
- No conflict — UV is the *frontend* (project manager), Hatchling is the *backend* (build tool)

**Sources**:
- [UV docs: Configuring projects](https://docs.astral.sh/uv/concepts/projects/config/) — UV supports hatchling as `--build-backend`
- [Hatchling: Build configuration](https://hatch.pypa.io/1.16/config/build/) — Official Hatchling docs
- [PyPA: Packaging tutorial](https://packaging.python.org/en/latest/tutorials/packaging-projects/) — Uses Hatchling as default

### Decision for Guinevere: **Hatchling build backend** with `requires = ["hatchling>=1.27.0"]`.

---

## 4. pyproject.toml [project] Section

### Recommended Fields (PEP 621 compliant)

```toml
[project]
name = "guinevere"
version = "0.1.0"
description = "Autonomous AI companion and engineering agent system"
readme = "README.md"
requires-python = ">=3.12"
license = "MIT"
license-files = ["LICEN[CS]E*"]
authors = [
    { name = "Faiz", email = "faiz@example.com" },
]
keywords = ["ai", "agent", "companion", "automation"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Operating System :: OS Independent",
]

dependencies = []

[project.urls]
Homepage = "https://github.com/faiz/guinevere"
Repository = "https://github.com/faiz/guinevere"
Issues = "https://github.com/faiz/guinevere/issues"
Documentation = "https://github.com/faiz/guinevere/docs"
```

### Field-by-Field Guidance

| Field | Required? | Notes |
|-------|-----------|-------|
| `name` | **Required** | ASCII letters, digits, `_`, `-`, `.`. Cannot start/end with `_`, `-`, `.`. |
| `version` | **Required** | Recommend `0.1.0` for initial. Can be `dynamic = ["version"]` if using Git-based versioning. |
| `description` | Strongly recommended | One-liner for PyPI/search listings. |
| `readme` | Strongly recommended | Path to README file. Auto-detects format from extension. |
| `requires-python` | **Strongly recommended** | Set to `>=3.12`. Affects dependency resolution — uv will only select packages supporting this range. |
| `license` | Recommended | **New PEP 639 format**: `license = "MIT"` (SPDX string). NOT the old table format. |
| `license-files` | Recommended | Glob patterns: `["LICEN[CS]E*"]`. Build backends ≥hatchling 1.27 support PEP 639. |
| `authors` | Recommended | List of `{name, email}` tables. |
| `keywords` | Optional | Improves PyPI discoverability. |
| `classifiers` | Recommended | Use for PyPI trove classification. |
| `dependencies` | **Required** | Can be empty `[]`. |
| `optional-dependencies` | Optional | For extras like `[dev]`, `[test]`. |
| `urls` | Recommended | Project links. Use well-known labels: `Homepage`, `Repository`, `Issues`, `Documentation`, `Changelog`. |
| `scripts` | Optional | CLI entry points. |
| `gui-scripts` | Optional | Windows GUI entry points. |
| `entry-points` | Optional | Plugin discovery. |

### Version Format

- **Static version**: `version = "0.1.0"` — simplest, best for initial development
- **Dynamic version**: `dynamic = ["version"]` with `[tool.hatch.version]` pointing to `src/guinevere/__about__.py` or using `hatch-vcs` for Git-based versioning

### Dependencies Specification

UV manages dependencies via `uv add` and `uv remove`. Manual editing is possible but not recommended for pinning — let UV handle it.

```toml
[project]
dependencies = [
    "httpx>=0.28.0",
    "pydantic>=2.10.0",
    "openai>=1.55.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.7.0",
    "mypy>=1.13.0",
    "pre-commit>=4.0",
]
```

### PEP 735 Dependency Groups (UV-native)

UV also supports PEP 735 `[dependency-groups]` for dev tools without packaging them as extras:

```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "ruff>=0.7.0",
    "mypy>=1.13.0",
]
lint = [
    "ruff>=0.7.0",
    "mypy>=1.13.0",
]
test = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
]
```

**Note**: UV writes to `[dependency-groups]` when you use `uv add --dev`. Prefer this over `[project.optional-dependencies]` for internal dev tools. Use `[project.optional-dependencies]` only for optional features that users may install (e.g., `pip install guinevere[postgres]`).

**Sources**:
- [PyPA: Writing your pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [PEP 621](https://peps.python.org/pep-0621/) — Project metadata in pyproject.toml
- [PEP 639](https://peps.python.org/pep-0639/) — License expressions
- [PEP 735](https://peps.python.org/pep-0735/) — Dependency groups
- [UV docs: Dependency groups](https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-groups)

---

## 5. Multi-Package / Monorepo Structure

### UV Workspace Model

UV supports **Cargo-style workspaces** — multiple packages sharing a single lockfile and virtual environment.

**Root `pyproject.toml`:**
```toml
[tool.uv.workspace]
members = [
    "packages/core",
    "packages/memory",
    "packages/persona",
    "packages/loops",
    "packages/discord-bot",
]
```

**Each member has its own `pyproject.toml`:**
```toml
# packages/core/pyproject.toml
[project]
name = "guinevere-core"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["pydantic>=2.10.0"]

[build-system]
requires = ["hatchling>=1.27.0"]
build-backend = "hatchling.build"
```

**Cross-package dependency:**
```toml
# packages/discord-bot/pyproject.toml
[project]
name = "guinevere-discord"
dependencies = [
    "guinevere-core",
    "guinevere-persona",
    "discord.py>=2.4.0",
]

[tool.uv.sources]
guinevere-core = { workspace = true }
guinevere-persona = { workspace = true }
```

### Alternative: Single Package with Namespace Sub-Packages

If you prefer a single package with sub-modules rather than separate packages:

```
src/guinevere/
├── __init__.py          # Top-level imports
├── __about__.py         # Version info
├── core/
│   ├── __init__.py
│   ├── config.py
│   ├── agent.py
│   └── ...
├── memory/
│   ├── __init__.py
│   ├── schema.py
│   ├── store.py
│   └── ...
├── persona/
│   ├── __init__.py
│   ├── profile.py
│   ├── safety.py
│   └── ...
├── loops/
│   ├── __init__.py
│   ├── main_loop.py
│   ├── safety_loop.py
│   └── ...
└── discord/
    ├── __init__.py
    ├── bot.py
    ├── handlers.py
    └── ...
```

**Single `pyproject.toml`** — Hatchling auto-discovers all sub-packages under `src/`.

### When to use workspaces vs single package

| Scenario | Single Package | UV Workspace |
|----------|---------------|--------------|
| All sub-modules are tightly coupled | ✅ Best | ❌ Overkill |
| Sub-modules could be released independently | ❌ | ✅ Best |
| Some sub-modules have different dependencies | ❌ | ✅ Best |
| Shared single lockfile desired | ✅ | ✅ |
| Each team owns different sub-packages | ❌ | ✅ |

**Sources**:
- [UV docs: Workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/)
- [UV docs: Build backend — namespace packages](https://docs.astral.sh/uv/concepts/build-backend/)
- A comprehensive monorepo structure guide (2026): [`packages/` for libs, `services/` for deployables](https://acquaintsoft.com/blog/python-monorepo-structure-growing-engineering-team)

### Decision for Guinevere: **Single package with sub-modules** (`src/guinevere/core`, `src/guinevere/memory`, etc.). This is simpler, tightly coupled, and doesn't need independent versioning. If the Discord bot grows into a separate deployable, extract it to a workspace member later.

---

## 6. __init__.py Conventions

### Best Practices (2026 Consensus)

| Rule | Description |
|------|-------------|
| **Thin Init** | Keep `__init__.py` minimal. No heavy imports, no database connections. |
| **Facade Pattern** | Hoist public API to top level: `from .core.config import Config` so users can `from guinevere import Config`. |
| **`__all__`** | Define explicit `__all__` list to control wildcard imports (`from guinevere import *`). |
| **Version string** | Place `__version__` and `__author__` in top-level `__init__.py` or a dedicated `__about__.py`. |
| **Relative imports** | Always use relative imports inside the package (`from .core import ...`), not absolute. |
| **No side effects** | No startup side effects. Lazy-load heavy submodules via `__getattr__`. |

### Recommended Top-Level `__init__.py`

```python
"""
Guinevere — Autonomous AI companion and engineering agent system.

Halo, namaku Guinevere. Aku mama-mu di project Guinevere.
"""

__version__ = "0.1.0"
__author__ = "Faiz"

# Public API — hoist important classes
from guinevere.core.config import Config
from guinevere.core.agent import Agent
from guinevere.persona.profile import PersonaProfile
from guinevere.memory.schema import MemorySchema

# Explicit public API
__all__ = [
    "Config",
    "Agent",
    "PersonaProfile",
    "MemorySchema",
]
```

### Sub-package `__init__.py` (Minimal)

```python
# src/guinevere/core/__init__.py
"""Core configuration and agent loop for Guinevere."""

from guinevere.core.config import Config
from guinevere.core.agent import Agent

__all__ = [
    "Config",
    "Agent",
]
```

### `__about__.py` (Alternative version location)

Some projects prefer a separate `__about__.py` for metadata (avoids circular imports):

```python
# src/guinevere/__about__.py
__version__ = "0.1.0"
__author__ = "Faiz"
```

Then in `__init__.py`: `from guinevere.__about__ import __version__, __author__`

And configure Hatchling to read from it:
```toml
[tool.hatch.version]
path = "src/guinevere/__about__.py"
```

### `py.typed` marker

Include an empty `py.typed` file to signal to type checkers that the package ships inline types:

```
src/guinevere/py.typed   # empty file
```

**Sources**:
- [Hrekov: __init__.py Best Practices (2026)](https://www.hrekov.com/blog/init-py-best-practices)
- [PEP 8](https://peps.python.org/pep-0008/) — Module-level dunder conventions
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) — Packages section

---

## 7. UV Project Initialization

### `uv init` vs Manual

| Method | When to Use |
|--------|-------------|
| `uv init --lib guinevere` | Quick scaffold for a new library with src/ layout |
| `uv init --bare guinevere` | Minimal `pyproject.toml` only, you control structure |
| **Manual** (recommended for this project) | When you need a custom multi-package structure |

**For Guinevere, manual is recommended** because:
1. We want specific sub-package structure (`core`, `memory`, `persona`, `loops`, `discord`)
2. We're using hatchling (not uv_build), so we need custom `[build-system]`
3. We need tool configurations (ruff, pytest, mypy) from the start

### Recommended Init Command (if using uv init as starting point)

```bash
uv init guinevere --lib --build-backend hatchling --python 3.12 --vcs git
cd guinevere
```

Then customize:
- Change `[build-system]` from uv_build to hatchling
- Add sub-package structure under `src/guinevere/`
- Configure `[tool.ruff]`, `[tool.pytest.ini_options]`, etc.
- Add `[dependency-groups]` for dev tools

### Key UV Commands Reference

| Command | Purpose |
|---------|---------|
| `uv add httpx` | Add runtime dependency |
| `uv add --dev pytest` | Add dev dependency (writes to `[dependency-groups]`) |
| `uv sync` | Install all deps + lockfile |
| `uv sync --frozen` | Install from lockfile only (CI) |
| `uv lock` | Regenerate lockfile |
| `uv run python -m guinevere` | Run in project env |
| `uv run pytest` | Run tests |
| `uv build` | Build sdist + wheel |
| `uv python pin 3.12` | Set Python version |
| `uv tool install .` | Install as CLI tool |

**Sources**:
- [UV docs: Creating projects](https://docs.astral.sh/uv/concepts/projects/init/)
- [UV docs: Working on projects](https://docs.astral.sh/uv/guides/projects/)
- [pydevtools: Understanding uv init](https://pydevtools.com/handbook/explanation/understanding-uv-init-project-types/)

---

## 8. Recommended Guinevere Project Structure

### Final Recommended Layout

```
guinevere/
├── .python-version           # Python 3.12
├── pyproject.toml            # Project metadata + tool configs
├── README.md                 # Project overview
├── LICENSE                   # MIT license
├── uv.lock                   # Auto-generated lockfile (COMMIT this)
├── .gitignore                # Exclude .venv, __pycache__, .ruff_cache, etc.
│
├── src/
│   └── guinevere/
│       ├── __init__.py       # Public API hoisting + __version__
│       ├── __about__.py      # Version info (optional, or keep in __init__)
│       ├── py.typed          # Type checker marker
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py     # Configuration models
│       │   ├── agent.py      # Main agent loop
│       │   └── types.py      # Shared type definitions
│       │
│       ├── memory/
│       │   ├── __init__.py
│       │   ├── schema.py     # Memory schema
│       │   ├── store.py      # Storage backend
│       │   └── recall.py     # Recall/search logic
│       │
│       ├── persona/
│       │   ├── __init__.py
│       │   ├── profile.py    # Persona profile model
│       │   ├── safety.py     # Safety constraints
│       │   └── yandere.py    # Yandere level management
│       │
│       ├── loops/
│       │   ├── __init__.py
│       │   ├── main.py       # Main execution loop
│       │   ├── safety.py     # Safety monitor loop
│       │   └── distress.py   # Distress detection
│       │
│       └── discord/
│           ├── __init__.py
│           ├── bot.py         # Discord bot setup
│           ├── handlers.py    # Message handlers
│           └── commands.py    # Slash commands
│
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_agent.py
│   ├── test_memory.py
│   ├── conftest.py           # Shared fixtures
│   └── fixtures/             # Test data
│
└── docs/
    ├── README.md             # Documentation index
    ├── 00-core/
    ├── 10-governance/
    └── ...
```

### Complete `pyproject.toml` Template for Guinevere

```toml
[build-system]
requires = ["hatchling>=1.27.0"]
build-backend = "hatchling.build"

[project]
name = "guinevere"
version = "0.1.0"
description = "Autonomous AI companion and engineering agent system"
readme = "README.md"
requires-python = ">=3.12"
license = "MIT"
license-files = ["LICEN[CS]E*"]
authors = [
    { name = "Faiz" },
]
keywords = ["ai", "agent", "companion", "automation", "discord"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Operating System :: OS Independent",
]

dependencies = [
    # Core
    "pydantic>=2.10.0",
    "httpx>=0.28.0",
    # LLM/API
    "openai>=1.55.0",
    # Discord
    "discord.py>=2.4.0",
    # Utilities
    "pyyaml>=6.0",
    "tomli>=2.0",
]

[project.urls]
Homepage = "https://github.com/faiz/guinevere"
Repository = "https://github.com/faiz/guinevere"
Issues = "https://github.com/faiz/guinevere/issues"
Documentation = "https://github.com/faiz/guinevere/docs"

# === PEP 735 Dependency Groups (uv-native) ===
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
    "ruff>=0.7.0",
    "mypy>=1.13.0",
    "pre-commit>=4.0",
]
lint = [
    "ruff>=0.7.0",
    "mypy>=1.13.0",
]
test = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
]

# === Tool Configurations ===

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade (Python 3.12+)
    "RUF", # Ruff-specific
]
ignore = [
    "E501",  # Line length handled by formatter
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = ["--strict-markers", "--strict-config"]
asyncio_mode = "auto"

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_unimported = false  # Relax for third-party imports

[tool.coverage.run]
source = ["guinevere"]
omit = ["tests/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

### .gitignore Template

```gitignore
# Virtual environment
.venv/

# Python cache
__pycache__/
*.py[cod]
*$py.class

# Build artifacts
dist/
build/
*.egg-info/
*.egg

# Tool cache
.ruff_cache/
.mypy_cache/
.pytest_cache/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Environment files
.env
.env.local

# SOPS
*.age
```

---

## 9. References

### Official Documentation
- [UV: Creating projects](https://docs.astral.sh/uv/concepts/projects/init/)
- [UV: Configuring projects](https://docs.astral.sh/uv/concepts/projects/config/)
- [UV: Workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/)
- [UV: Build backend](https://docs.astral.sh/uv/concepts/build-backend/)
- [UV: Working on projects (guide)](https://docs.astral.sh/uv/guides/projects/)
- [Hatchling: Build configuration](https://hatch.pypa.io/1.16/config/build/)
- [PyPA: Writing your pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [PyPA: Packaging tutorial](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
- [PyPA: src layout vs flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)
- [PyPA: Dependency Groups (PEP 735)](https://packaging.python.org/en/latest/specifications/dependency-groups/)

### PEPs
- [PEP 517](https://peps.python.org/pep-0517/) — Build system interface
- [PEP 518](https://peps.python.org/pep-0518/) — pyproject.toml build dependencies
- [PEP 621](https://peps.python.org/pep-0621/) — Project metadata in pyproject.toml
- [PEP 639](https://peps.python.org/pep-0639/) — License expressions
- [PEP 735](https://peps.python.org/pep-0735/) — Dependency groups

### Community Guides
- [pydevtools: Understanding uv init project types](https://pydevtools.com/handbook/explanation/understanding-uv-init-project-types/)
- [pydevtools: Modern Python Project Setup Guide for AI Assistants](https://pydevtools.com/handbook/explanation/modern-python-project-setup-guide-for-ai-assistants/)
- [Hrekov: __init__.py Best Practices (2026)](https://www.hrekov.com/blog/init-py-best-practices)
- [Real Python: Project Layout](https://realpython.com/ref/best-practices/project-layout/)
- [pyOpenSci: Python Package Structure](https://www.pyopensci.org/python-package-guide/package-structure-code/python-package-structure.html)
- [Aron Hack: Monorepos and UV](https://aronhack.com/monorepos-and-uv-a-perfect-match-for-modern-python-development/)
- [Acquaintsoft: Python Monorepo Structure (2026)](https://acquaintsoft.com/blog/python-monorepo-structure-growing-engineering-team)
- [clintonsteiner/python-monorepo-template](https://github.com/clintonsteiner/python-monorepo-template)

---

*End of research report. Prepared for downstream use in P1-004 (Guinevere Python project structure).*