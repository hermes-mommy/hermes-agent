# Evidence — STEP-P1-001: Python 3.12 Runtime

## What Was Done
Installed Python 3.12 runtime, development headers, and virtual environment support on the Guinevere VPS (faiz-prod-01, Ubuntu 24.04).

## Approach
Python 3.12.3 was already present as the system default on Ubuntu 24.04 (`python3` and `python3.12` both resolve to 3.12.3). No deadsnakes PPA was needed (confirmed deadsnakes does not provide Python 3.12 for noble). Installed missing supplemental packages via apt.

## SSH Aliases Used (from `~/.ssh/config`)
```bash
ssh guinevere-vps          # → guinevere@100.94.104.22 (user operations)
ssh guinevere-root         # → root@100.94.104.22 (apt install requiring root)
```

## Commands Executed (corrected from original StepPrompts.md)
```bash
# Verify existing Python (as guinevere user)
ssh guinevere-vps "python3 --version && python3.12 --version"
# → Python 3.12.3, Python 3.12.3

# Install supplemental packages (as root via guinevere-root alias)
ssh guinevere-root "apt install -y python3.12-venv python3.12-dev python3-pip"
```

## Deviations from Original StepPrompts.md
| Original Command | Correction | Reason |
|---|---|---|
| `add-apt-repository ppa:deadsnakes/ppa` | REMOVED | Dead snakes does NOT provide Python 3.12 for Ubuntu 24.04 (noble) |
| `apt install python3.12-distutils` | REMOVED | Package does not exist — distutils removed from Python 3.12 (PEP 632) |
| `curl get-pip.py \| python3.12` | REMOVED | Not needed — `python3-pip` installed via apt |
| `python3.12-venv` not in original | ADDED | Required for venv creation |
| `python3.12-dev` not in original | ADDED | Required for building Python C extensions |

All corrections documented in Metis planner report: `audit-reports/P1/planner/metis-analysis-001-003.md`

## Final Package State
```
ii  libpython3.12-dev:amd64           3.12.3-1ubuntu0.13
ii  libpython3.12-minimal:amd64       3.12.3-1ubuntu0.13
ii  libpython3.12-stdlib:amd64        3.12.3-1ubuntu0.13
ii  libpython3.12t64:amd64            3.12.3-1ubuntu0.13
ii  python3.12                        3.12.3-1ubuntu0.13
ii  python3.12-dev                    3.12.3-1ubuntu0.13
ii  python3.12-minimal                3.12.3-1ubuntu0.13
ii  python3.12-venv                   3.12.3-1ubuntu0.13
```

## Validation Results
| Check | Result | Evidence |
|---|---|---|
| `python3.12 --version` | Python 3.12.3 | `python-version.txt` |
| `python3.12 -m pip --version` | pip 24.0 | Via apt-installed python3-pip |
| `python3.12 -m venv --help` | Shows help | venv module functional |
| `dpkg -l \| grep python3.12` | 8 packages | All 3.12.3-1ubuntu0.13 |
| `ensurepip` | Disabled (Ubuntu policy) | Expected — PEP 668, venv handles this |
| `setuptools` system-wide | Blocked by PEP 668 | Expected — will install in venv in P1-003 |

## Evidence Artifacts
- `docs/setup-evidence/P1/STEP-P1-001/python-version.txt` — Python version output
- `docs/setup-evidence/P1/STEP-P1-001/evidence.md` — This file
- `research-reports/P1/python-detection-p0-audit.md` — Research: P0 audit Python detection analysis
- `research-reports/P1/python-312-ubuntu-2404.md` — Research: Python 3.12 on Ubuntu 24.04
- `research-reports/P1/distutils-ensurepip.md` — Research: distutils removal, ensurepip analysis
- `audit-reports/P1/planner/metis-analysis-001-003.md` — Planner analysis

## ADR Compliance
| ADR | Requirement | Status |
|---|---|---|
| ADR-014 | Python 3.12 as runtime | ✅ 3.12.3 installed |
| ADR-014 | systemd service architecture | ✅ venv ready for systemd |

## Shared VPS / Aizanta Impact
- No Aizanta services touched (Docker containers, PostgreSQL, Redis, Caddy)
- Only apt install, no port or service changes
- No reboot required (kernel update deferred — informational only)

## Rollback / Re-run Safety
- Idempotent: `apt install -y` is safe to re-run
- To remove: `apt purge python3.12-venv python3.12-dev python3-pip`
- Python 3.12 core should NOT be removed (it's the system default)

## Design Decisions
1. Did not use deadsnakes PPA (not needed, not available for noble)
2. Did not install `python3.12-distutils` (doesn't exist)
3. Used `apt install python3-pip` instead of `get-pip.py` (PEP 668-safe)
4. `ensurepip` is disabled per Ubuntu policy — UV in P1-002/P1-003 will handle venv pip

## Footer
| Field | Value |
|---|---|
| Source Task | STEP-P1-001 — Python 3.12 Runtime |
| Date | 2026-05-31 |
| Implementer | Guinevere (Sisyphus parent) |
| Validation Method | Live SSH read-only verification |
| Evidence Root | `docs/setup-evidence/P1/STEP-P1-001/` |