# Metis Planner Analysis — P1-001 to P1-003

| Field | Value |
|-------|-------|
| **Scope** | P1-001 (Python 3.12), P1-002 (UV), P1-003 (venv) |
| **Date** | 2026-05-31 |
| **Consultant** | Metis (Pre-Planning Consultant) |
| **Analysis Type** | Pre-Execution Risk Analysis |
| **Verdict** | **CONDITIONALLY SOUND** — 5 hard requirements must be met |

---

## 1. Intent Classification

**Type**: Mid-sized Task with Research Validation
**Confidence**: High
**Rationale**: Three bounded, sequential infrastructure steps (Python → UV → venv) with clear inputs/outputs. Research has identified corrections to the original StepPrompts.md.

---

## 2. StepPrompts.md P1-001 — Factual Errors

| Line | Error | Correction |
|------|-------|------------|
| 3236 | "Using deadsnakes PPA for the latest stable 3.12 on Ubuntu 24.04" | Ubuntu 24.04 (Noble) ships Python 3.12.3 natively. No PPA needed. |
| 3248 | `sudo add-apt-repository -y ppa:deadsnakes/ppa` | Dead snakes PPA does NOT provide Python 3.12 for noble. Will fail. |
| 3252 | `python3.12-distutils` | Does not exist for Python 3.12+. Distutils removed per PEP 632. |
| 3255 | `curl -sS https://bootstrap.pypa.io/get-pip.py \| python3.12` | Works but not idiomatic. `python3.12 -m ensurepip --upgrade` is preferred. |

**Corrected P1-001 Commands:**

```bash
# Step 1: Verify Python 3.12 availability
apt-cache policy python3.12

# Step 2: Install Python 3.12 from native repos (NO deadsnakes PPA)
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev python3-pip

# Step 3: Bootstrap pip via ensurepip
python3.12 -m ensurepip --upgrade
python3.12 -m pip install setuptools
```

---

## 3. Risk Analysis

### Risk 1: Python 3.12 NOT in default repos (HIGH — blocks P1 entirely)
- **Scenario**: Ubuntu 24.04 image was customized/minimized and Python 3.12 was stripped.
- **Impact**: `apt install python3.12` fails. Entire P1 phase blocked.
- **Mitigation**: Preflight must explicitly test `apt-cache show python3.12`. Fallback plan needed.

### Risk 2: apt lock contention with Aizanta (MEDIUM)
- **Scenario**: `unattended-upgrades` or Aizanta CI locks `/var/lib/dpkg/lock`.
- **Impact**: P1-001 fails, partial install state.
- **Mitigation**: Preflight check `lsof /var/lib/dpkg/lock`. Retry with exponential backoff (30s, 60s, 120s).

### Risk 3: Non-interactive SSH PATH isolation (HIGH — breaks P1-002→P1-003 handoff)
- **Scenario**: P1-002 adds `export PATH` to `.bashrc`. P1-003 runs as new SSH command — `.bashrc` is NOT sourced for non-interactive shells.
- **Impact**: `uv` command not found. Error cascade.
- **Mitigation**: Execute P1-001/002/003 in a SINGLE SSH session, OR P1-003 uses `~/.local/bin/uv` explicitly.

### Risk 4: SSH timeout on apt install (MEDIUM)
- **Scenario**: `apt install` downloads ~80MB. Default SSH timeout may trigger.
- **Impact**: SSH drops mid-install, package state indeterminate.
- **Mitigation**: Use `screen`/`tmux` or set `ServerAliveInterval 15`.

### Risk 5: uv installer run with sudo (MEDIUM)
- **Scenario**: AI agent uses `sudo curl ... | sh` because previous commands used `sudo apt`.
- **Impact**: uv binary at `/usr/local/bin/uv` owned by root, or writes to system config.
- **Mitigation**: **HARD GUARD**: P1-002 MUST NOT use sudo. Run as guinevere user only.

### Risk 6: `/home/guinevere/code/guinevere` may not exist (MEDIUM)
- **Scenario**: P0 directory structure was local-only, not on VPS.
- **Impact**: P1-003 `cd /home/guinevere/code/guinevere` fails.
- **Mitigation**: Preflight must verify `test -d /home/guinevere/code/guinevere`. Create if missing.

### Risk 7: UV may download its own CPython (LOW-MEDIUM)
- **Scenario**: If uv doesn't find python3.12, it downloads a prebuilt binary (~40MB).
- **Impact**: Extra disk usage. Still works but wasteful.
- **Mitigation**: Run `uv python list` in P1-002 verification. Point explicitly: `UV_PYTHON=/usr/bin/python3.12`.

### Risk 8: No proof Python 3.12 installed from P0 (P0-000 gap)
- P0-000 audit only found Docker containers, never checked `python3 --version`.
- **Mitigation**: Preflight checks both `python3 --version` AND `python3.12 --version`.

### Risk 9: B1 plaintext secrets (informational for P1)
- P1 does NOT touch encryption/secrets. No risk. But evidence files must NOT leak secret paths.
- **Mitigation**: Scrub `SOPS_AGE_KEY_FILE`, `AGE_KEY` from evidence outputs.

---

## 4. Hard Requirements (5 items)

| # | Requirement | Why |
|---|-------------|-----|
| **REQ-1** | Single SSH session for P1-001→002→003 | Preserve PATH across steps |
| **REQ-2** | Preflight: `apt-cache policy python3.12` | Catch "Python not in repos" before install |
| **REQ-3** | Preflight: `test -d /home/guinevere/code/guinevere` | Fail early if directory missing |
| **REQ-4** | apt lock check + retry before P1-001 | Avoid `unattended-upgrades` collision |
| **REQ-5** | StepPrompts.md P1-001 Commands CORRECTED before execution | Current commands contain 3 factual errors |

---

## 5. Directives for Implementation

### Core MUST DO
- **MUST**: Run `scripts/preflight-check.sh --json` first. If exit code ≠ 0, produce categorized failure report.
- **MUST**: Verify Python 3.12 availability with `apt-cache show python3.12` in preflight.
- **MUST**: Execute P1-001, P1-002, P1-003 in a **single SSH session**.
- **MUST**: For P1-001, use corrected command list (no deadsnakes, no distutils, no get-pip.py).
- **MUST**: For P1-002, NO sudo for uv installer. Run as guinevere user.
- **MUST**: For P1-003, add `source ~/.bashrc` or use `~/.local/bin/uv` to handle PATH.
- **MUST**: Verify each package with `dpkg -l | grep python3.12` after P1-001.
- **MUST**: Write evidence to `docs/setup-evidence/P1/STEP-P1-{001,002,003}/`.
- **MUST**: Run per-step auditor gate (independent) after each step.
- **MUST**: Correct StepPrompts.md P1-001 before execution.

### Core MUST NOT
- **MUST NOT**: Use sudo for `curl https://astral.sh/uv/install.sh | sh`
- **MUST NOT**: Add deadsnakes PPA on Ubuntu 24.04 for Python 3.12
- **MUST NOT**: Install `python3.12-distutils` (does not exist)
- **MUST NOT**: Expose SOPS_AGE_KEY_FILE or secrets paths in evidence
- **MUST NOT**: Touch Aizanta services, ports, or docker containers

### Verification Criteria
- **P1-001**: `python3.12 --version` → `Python 3.12.x` AND `dpkg -l | grep python3.12` shows 3 packages
- **P1-002**: `~/.local/bin/uv --version` → version string
- **P1-003**: `.venv/bin/python --version` → `Python 3.12.x` AND package list matches

---

## 6. Verdict

**CONDITIONALLY SOUND** — with 5 hard requirements met. The approach is correct but brittle:
- Single SSH session is the #1 failure point (PATH isolation)
- apt lock + Python not-in-repos are the #2 blockers
- StepPrompts.md P1-001 MUST be corrected before any implementation agent touches this

**The Troubleshooting section of StepPrompts.md (lines 3277–3280) actually lists the correct alternatives — but they're in Troubleshooting, not in Commands. An agent executing blind from the Commands section will fail.**

---

| Field | Value |
|-------|-------|
| **Source task** | P1-001 to P1-003 — Planner Gate Analysis |
| **Date** | 2026-05-31 |
| **Consultant** | Metis (Pre-Planning Consultant) |
| **Method** | Risk analysis + StepPrompts diff + VPS context review |
| **Report Path** | `audit-reports/P1/planner/metis-analysis-001-003.md` |