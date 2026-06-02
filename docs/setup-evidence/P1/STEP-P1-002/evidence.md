# Evidence — STEP-P1-002: UV Package Manager

## What Was Done
Installed UV 0.11.17 (Astral's fast Python package manager) as the guinevere user on faiz-prod-01 VPS. UV replaces pip/virtualenv/pipenv/poetry for Guinevere.

## Commands Executed
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**NO sudo used** — UV installer detects EUID and installs per-user to `~/.local/bin/`.

## Verification
| Check | Result |
|---|---|
| `uv --version` | uv 0.11.17 |
| `which uv` | /home/guinevere/.local/bin/uv |
| PATH in .bashrc | Already present (no change needed) |

## Evidence Artifacts
- `docs/setup-evidence/P1/STEP-P1-002/uv-version.txt` — UV version output
- `docs/setup-evidence/P1/STEP-P1-002/evidence.md` — This file
- `research-reports/P1/uv-package-manager.md` — Research: UV setup best practices

## Rollback / Re-run Safety
- To remove: `rm ~/.local/bin/uv ~/.local/bin/uvx`
- Idempotent: `curl | sh` detects existing install and updates
- No system packages touched

## Design Decisions
1. Per-user install (not system-wide pip install) — follows UV docs recommendation
2. Added PATH in .bashrc for interactive use; P1-003 uses explicit `$HOME/.local/bin/uv`

## Footer
| Field | Value |
|---|---|
| Source Task | STEP-P1-002 — UV Package Manager |
| Date | 2026-05-31 |
| Implementer | Guinevere (Sisyphus parent) |
| Validation Method | Live SSH verification |
| Evidence Root | `docs/setup-evidence/P1/STEP-P1-002/` |