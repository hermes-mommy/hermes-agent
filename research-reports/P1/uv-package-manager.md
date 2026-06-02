# Research: UV Package Manager Setup (2025/2026)

| Field | Value |
|-------|-------|
| **Research Agent** | Librarian |
| **Date** | 2026-05-31 |
| **Sources** | Astral docs, GitHub, PyPI |
| **Verdict** | UV 0.11.17 — curl|sh install, Python 3.12 Tier 1 |

---

## Key Findings

- **Version**: UV 0.11.17 (May 2026)
- **Install**: `curl -LsSf https://astral.sh/uv/install.sh | sh` → `~/.local/bin/uv`
- **Python 3.12**: Tier 1 support (fully tested, all features available)
- **Replaces**: pip, pip-tools, virtualenv, pipenv, poetry entirely

## UV + Systemd

Systemd ExecStart: use `/path/to/.venv/bin/python` directly — NEVER `source activate`.
Set `Environment="VIRTUAL_ENV=/path/to/.venv"` in service unit.

## UV vs System Python (PEP 668)

UV handles PEP 668 externally-managed environments correctly. venvs created by UV bypass the marker.

## Production Patterns

- Install per-user (NO sudo): `~/.local/bin/`
- Add to PATH in `.bashrc`: `export PATH="$HOME/.local/bin:$PATH"`
- Production install: `uv sync --frozen --no-dev`
- `uv pip install` for projects without pyproject.toml

## P1-002 Command (Confirmed Correct)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
uv --version
uv python list
```

## Critical Guard

**DO NOT use sudo.** The UV installer detects EUID and adjusts behavior. Running with sudo will install to system paths owned by root.

| Field | Value |
|-------|-------|
| **Source** | bg_0c2d3cbd — UV package manager 2026 |
| **File** | research-reports/P1/uv-package-manager.md |