# Research: Python Virtual Environment Best Practices (2025/2026)

| Field | Value |
|-------|-------|
| **Research Agent** | Librarian |
| **Date** | 2026-05-31 |
| **Sources** | PEP 832, systemd docs, Real Python, production patterns |
| **Verdict** | .venv in project root, systemd uses .venv/bin/python directly |

---

## Key Findings

### Venv Location
- **`.venv` in project root** is the standard (PEP 832 proposal, adopted by community)
- NOT `~/.virtualenvs/` (centralized) — project-specific venvs are the convention

### Systemd + Venv

```ini
[Service]
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m uvicorn app:app
Environment="VIRTUAL_ENV=/home/guinevere/code/guinevere/.venv"
Environment="PATH=/home/guinevere/code/guinevere/.venv/bin:/usr/local/bin:/usr/bin:/bin"
```

**NEVER**: `ExecStart=/bin/bash -c "source .venv/bin/activate && python ..."` — wrong.

### Permissions
- `.venv/` owned by service user (`guinevere:guinevere`)
- Read-only for other users

### .gitignore
```
.venv/
__pycache__/
*.pyc
.env
```

### UV Venv vs python -m venv
- **Prefers `uv venv`**: faster, handles PEP 668, downloads managed Python if needed
- `uv venv --python 3.12 .venv` → creates venv at `.venv`

### Production pip install
- `uv pip install` for simple dependency lists
- `uv sync --frozen --no-dev` for pyproject.toml projects
- Production should pin exact versions: `uv pip freeze > requirements.lock`

| Field | Value |
|-------|-------|
| **Source** | bg_0545071e — Python venv best practices 2025 |
| **File** | research-reports/P1/python-venv-best-practices.md |