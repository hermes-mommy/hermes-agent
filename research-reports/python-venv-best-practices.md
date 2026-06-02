# Python Virtual Environment Best Practices — Guinevere Production Research

> **Researched**: 2026-05-31 | **Target**: Ubuntu 24.04, Python 3.12, UV, systemd service deployment
> **Sources**: PEP 832, Data Mammoth, Miguel Grinberg, Hynek Schlawack, Astral/UV docs, mod_wsgi docs, StackOverflow, Real Python, GitHub gitignore

---

## 1. .venv Location — Project Root is the Standard

### Recommendation: Use `.venv/` in project root

| Factor | Verdict |
|---|---|
| **PEP 832 (2024)** | Standardizes `.venv` directory/file in project root as the canonical location ([source](https://peps.python.org/pep-0832/)) |
| **UV default** | `uv sync` / `uv venv` creates `.venv` in project root automatically |
| **Python docs** | "A common directory location for a virtual environment is `.venv`" ([source](https://docs.python.org/3/tutorial/venv.html)) |
| **IDE discovery** | VS Code, PyCharm all auto-detect `.venv/` in project root |
| **systemd compatibility** | Works fine — just use absolute path in `ExecStart` |

**PEP 832 also defines a `.venv` *file* fallback**: if you must store the venv elsewhere (e.g., `/opt/guinevere/.venv`), create a `.venv` text file at project root containing the path to the real venv. Tools will follow it.

### Centralized venv directories: NOT recommended for production

- `~/.virtualenvs/` — fragile for systemd services because service users may not have access to other users' home dirs
- `/opt/` — possible but adds path indirection with no benefit over project-root `.venv`
- **Exception**: When deploying multiple app instances per host, use `/opt/{app}/venv` pattern (per-mod_wsgi hardening guide)

**For Guinevere**: `/home/guinevere/code/guinevere/.venv` is correct.

---

## 2. UV venv vs python -m venv

### UV is the recommended standard for 2026

| Aspect | `python -m venv` | `uv venv` / `uv sync` |
|---|---|---|
| **Speed** | Baseline | 10-100x faster |
| **Lockfile** | None (manual `pip freeze > requirements.txt`) | Automatic `uv.lock` (cross-platform, hash-verified) |
| **Venv management** | Manual create, manual activate | Automatic — `uv sync` creates if missing |
| **Python version mgmt** | External (pyenv/asdf) | Built-in (`uv python install 3.12`) |
| **Auto .gitignore** | Since Python 3.11+ creates `.gitignore` inside `.venv/` | Creates `.gitignore` inside `.venv/` |
| **Activation needed?** | Yes — `source .venv/bin/activate` | No — `uv run` handles it automatically |
| **CI/CD integration** | Verbose multi-step | Seamless (`uv sync --frozen`) |
| **Dependency groups** | Manual (multiple requirements files) | Built-in (`--dev`, `--no-dev`) |
| **Project scaffolding** | No | `uv init` creates full project structure |

**Sources**:
- [Real Python: Managing Python Projects With uv](https://realpython.com/python-uv/)
- [Data Mammoth: Install Python on Ubuntu 24.04](https://data-mammoth.com/support/install-guides/how-to-install-python-ubuntu)
- [BSWEN: venv vs virtualenv vs uv comparison](https://docs.bswen.com/blog/2026-03-15-python-venv-virtualenv-uv-comparison/)
- [Hynek: Production Docker Containers with uv](https://hynek.me/articles/docker-uv/)

### When to use venv instead

- Minimal scripts with 0-2 dependencies
- Python 2 legacy (uv doesn't support it)
- Environments where installing an external binary is not allowed
- Maximum simplicity / no external tooling

### For Guinevere: **Use UV**. No question.

---

## 3. systemd Activation Strategy — The Battle-Tested Pattern

### THE RULE: Never use `source activate` in systemd

```systemd
# ❌ WRONG — systemd doesn't support shell sourcing
ExecStartPre=source /path/to/.venv/bin/activate     # Fails silently
ExecStart=/bin/bash -c 'source .venv/bin/activate && python app.py'  # Fragile, security risk
```

### ✅ CORRECT PATTERN: Use the venv's python interpreter directly

**Source**: StackOverflow ([link](https://stackoverflow.com/questions/37211115/how-to-enable-a-virtualenv-in-a-systemd-service-unit)), pythontutorials.net ([link](https://www.pythontutorials.net/blog/how-to-enable-a-virtualenv-in-a-systemd-service-unit/)), Miguel Grinberg ([link](https://blog.miguelgrinberg.com/post/running-a-flask-application-as-a-service-with-systemd))

```systemd
[Unit]
Description=Guinevere Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/code/guinevere

# ✅ Use the venv's python directly (Solution 1)
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m app.main

# ✅ Set PATH to include venv bin (Solution 2 — for console_scripts like gunicorn)
Environment="PATH=/home/guinevere/code/guinevere/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="VIRTUAL_ENV=/home/guinevere/code/guinevere/.venv"

# Restart policy
Restart=on-failure
RestartSec=5s
StartLimitIntervalSec=60
StartLimitBurst=5

# Security hardening
PrivateTmp=yes
NoNewPrivileges=yes

[Install]
WantedBy=multi-user.target
```

### For console_scripts (gunicorn, uvicorn, etc.)

When using tools like gunicorn that are installed as console_scripts in the venv:

```systemd
# Option A: Via venv python -m
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m gunicorn -w 4 -b 127.0.0.1:8000 app:app

# Option B: Direct console_script path (requires PATH set)
Environment="PATH=/home/guinevere/code/guinevere/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/guinevere/code/guinevere/.venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app
```

**Both work.** Option B is cleaner when you have multiple console_script tools.

### CRITICAL: ExecStart first arg must be an absolute literal path

```systemd
# ❌ WRONG — systemd does NOT expand variables in ExecStart's first argument
ExecStart=${VENV_PATH}/bin/python app.py     # Code=203/EXEC

# ❌ WRONG — relative paths not allowed
ExecStart=.venv/bin/python app.py            # Unit fails to load

# ✅ CORRECT — absolute literal path
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python app.py
```

**Source**: [StackOverflow](https://stackoverflow.com/questions/48464270/systemd-execstart-python-daemon-dynamically-using-virtualenv-from-environment-va), systemd.exec(5) man page

### Secrets: Use EnvironmentFile, never bake into unit

```systemd
EnvironmentFile=/etc/guinevere/env
# File permissions: chmod 600, owned by root:guinevere
```

---

## 4. .gitignore Pattern for .venv

### Standard entries from GitHub's Python.gitignore

```gitignore
# Virtual environments
.venv
venv/
env/
ENV/
env.bak/
venv.bak/

# UV-specific
.python-version       # Only if you want to pin Python (commit this if desired)

# Environment files (keep these separate from .venv)
.env
.envrc
```

**Source**: [GitHub gitignore/Python.gitignore](https://github.com/github/gitignore/blob/main/Python.gitignore)

**Key insight**: UV automatically creates a `.gitignore` file *inside* `.venv/` that ignores everything. Even without the top-level `.gitignore` entry, the nested `.gitignore` protects you. But **always add the top-level entry too** for clarity and for tools that don't traverse into `.venv/`.

---

## 5. What to Install Initially vs On-Demand

### Initial venv setup (one-time)

```bash
# Create the project first
cd /home/guinevere/code/guinevere
uv init --python 3.12

# Add core runtime dependencies
uv add fastapi uvicorn[standard] pydantic-settings httpx \
    discord.py \
    redis \
    asyncpg \
    prometheus-client

# Add development dependencies
uv add --dev pytest pytest-asyncio pytest-cov \
    ruff mypy \
    pre-commit

# Lock and sync
uv sync --frozen
```

### Production install (in CI/CD or deployment script)

```bash
uv sync --frozen --no-dev   # Only runtime deps, exact lockfile match
```

**Key rules from battle-tested patterns** (Hynek Schlawack, Nick Janetakis, Caktus Group):
1. **Lockfile first**: Always `uv sync --frozen` or `uv sync --locked` in production — never re-resolve
2. **`--no-dev` in production**: Development dependencies (pytest, ruff, mypy) must never reach production
3. **Docker multi-stage**: Install deps in build stage, copy only `.venv/` to runtime
4. **Separate dependency groups**: Use `[dependency-groups]` in `pyproject.toml` for dev, test, lint groups
5. **Byte-compile**: Set `UV_COMPILE_BYTECODE=1` for faster startup

### On-demand installs (during development)

```bash
uv add <new-package>         # Auto-updates pyproject.toml + uv.lock + .venv
uv add --dev <new-dev-pkg>   # Dev-only dependency
uv remove <package>           # Clean removal
```

---

## 6. Permissions — Owned by Service User

### Best practice for production

```bash
# Create dedicated service user
sudo useradd -r -s /bin/false -m -d /home/guinevere guinevere

# Create project directory
sudo mkdir -p /home/guinevere/code/guinevere
sudo chown -R guinevere:guinevere /home/guinevere/code

# Create the venv AS the service user
sudo -u guinevere uv venv /home/guinevere/code/guinevere/.venv
sudo -u guinevere uv sync --frozen --no-dev

# Verify ownership
ls -la /home/guinevere/code/guinevere/.venv/bin/python
# Should show: guinevere:guinevere

# Optionally: make venv read-only for the service user after setup
# (Prevents accidental runtime modifications)
chmod -R a-w /home/guinevere/code/guinevere/.venv
chmod u+w /home/guinevere/code/guinevere/.venv  # Keep write for upgrades
```

### Key rules from mod_wsgi security hardening guide

**Source**: [mod_wsgi Security Hardening](https://modwsgi.readthedocs.io/en/latest/user-guides/security-hardening.html)

1. **Do not run as root** — Create a dedicated service user per application
2. **Do not reuse shared users** — No `www-data`, `nobody`, etc.
3. **Venv owned by app user** — The user running the systemd service must own the venv
4. **Code read-only for app user** — The app user should be able to read but not write code (deployment user owns code)
5. **Venv read-only after setup** — Prevents accidental `pip install` at runtime
6. **Separate venv per component** — Never share a venv across different applications

### Warning: Don't use `/home/` paths with systemd

Some systemd configurations fail with `Permission denied` when referencing paths under `/home/`. If this happens:

```systemd
# ❌ May fail on some distros:
ExecStart=/home/guinevere/.venv/bin/python ...

# ✅ Workaround: Use /opt/ or ensure home directory has proper permissions
ExecStart=/opt/guinevere/.venv/bin/python ...
```

**Source**: [StackOverflow](https://stackoverflow.com/questions/69486599/permission-denied-for-virtualenv-python-when-using-systemd)

For Ubuntu 24.04, `/home/` works as long as the service user has `rx` permissions on the parent directories.

---

## 7. Complete Reference: Production systemd Unit File

```systemd
[Unit]
Description=Guinevere — Autonomous AI Companion Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/code/guinevere

# Use venv python directly — no shell, no activation
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m guinevere.main

# Environment: venv PATH + VIRTUAL_ENV + project-specific
Environment="PATH=/home/guinevere/code/guinevere/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="VIRTUAL_ENV=/home/guinevere/code/guinevere/.venv"
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONDONTWRITEBYTECODE=1"

# Secrets (chmod 600, owned by root:guinevere)
EnvironmentFile=/etc/guinevere/env

# Migrations (separate oneshot service)
ExecStartPre=/home/guinevere/code/guinevere/.venv/bin/python -m alembic upgrade head

# Restart policy
Restart=on-failure
RestartSec=5s
StartLimitIntervalSec=60
StartLimitBurst=5

# Security hardening
PrivateTmp=yes
NoNewPrivileges=yes
ProtectSystem=full
ProtectHome=yes

[Install]
WantedBy=multi-user.target
```

### Migration one-shot service (run separately from runtime service)

```systemd
[Unit]
Description=Guinevere Database Migration
Before=guinevere.service

[Service]
Type=oneshot
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m alembic upgrade head
Environment="PATH=/home/guinevere/code/guinevere/.venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/etc/guinevere/env

[Install]
WantedBy=multi-user.target
```

---

## Summary Decision Matrix for Guinevere

| Concern | Recommendation | Rationale |
|---|---|---|
| **Package manager** | UV | 10-100x faster, lockfile, auto venv, Python version mgmt |
| **Venv location** | `/home/guinevere/code/guinevere/.venv` | PEP 832 standard, UV default, IDE discovery |
| **Python version** | 3.12 | Native on Ubuntu 24.04, no deadsnakes needed |
| **systemd ExecStart** | Absolute path to `.venv/bin/python` | No shell activation needed — venv python has baked-in sys.path |
| **Production install** | `uv sync --frozen --no-dev` | Lockfile-verified, no dev deps |
| **Service user** | `guinevere` | Dedicated, non-root, owns venv |
| **Permissions** | `guinevere:guinevere`, `chmod 755` | Service user reads + executes; write only when upgrading |
| **Secrets** | `EnvironmentFile=/etc/guinevere/env` | 600 permissions, root-owned, injected by systemd |
| **Migrations** | Separate oneshot service | Avoids race conditions, clean separation of concerns |
| **.gitignore** | `.venv/`, `venv/`, `env/` | Plus UV auto-creates nested `.gitignore` |
| **Rollback** | Preserve previous `.venv` during deploy | Swap `.venv-next` → `.venv` pattern |

---

## Key Sources

1. [PEP 832 — Virtual Environment Discovery](https://peps.python.org/pep-0832/)
2. [Data Mammoth — Install Python on Ubuntu 24.04 VPS](https://data-mammoth.com/support/install-guides/how-to-install-python-ubuntu)
3. [Miguel Grinberg — Flask + systemd](https://blog.miguelgrinberg.com/post/running-a-flask-application-as-a-service-with-systemd)
4. [Hynek Schlawack — Production Docker Containers with uv](https://hynek.me/articles/docker-uv/)
5. [StackOverflow — Enable virtualenv in systemd](https://stackoverflow.com/questions/37211115/how-to-enable-a-virtualenv-in-a-systemd-service-unit)
6. [mod_wsgi — Virtual Environments Guide](https://modwsgi.readthedocs.io/en/develop/user-guides/virtual-environments.html)
7. [mod_wsgi — Security Hardening](https://modwsgi.readthedocs.io/en/latest/user-guides/security-hardening.html)
8. [Real Python — Managing Python Projects With uv](https://realpython.com/python-uv/)
9. [Caktus Group — Migrating Django to uv](https://www.caktusgroup.com/blog/2025/06/11/migrating-python-django-projects-uv/)
10. [GitHub gitignore — Python.gitignore](https://github.com/github/gitignore/blob/main/Python.gitignore)
11. [Python docs — venv module](https://docs.python.org/3/library/venv.html)
12. [Python docs — Virtual Environments tutorial](https://docs.python.org/3/tutorial/venv.html)