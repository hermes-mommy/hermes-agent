# Phase 0: Security Remediation — Detailed Procedure

## Overview

| Property | Value |
|---|---|
| **Duration** | 2-3 days |
| **Risk Level** | LOW |
| **Dependencies** | NONE — first phase, can start immediately |
| **Blocks** | Phase 1 (BLOCKING), Phase 6 (NON-BLOCKING) |
| **Gate** | `hermes doctor` clean + `hermes security` zero HIGH/MODERATE |
| **Rollback Time** | < 5 minutes (`pip install -r pre-migration-pip-*.txt`) |

### Goal Statement

Establish a security-hardened baseline for the entire migration. All Python dependencies must be patched, hash-verified, and free of HIGH or MODERATE severity vulnerabilities. The Hermes runtime must pass `hermes doctor` (all checks green) and `hermes security` (zero actionable findings) before any safety code is deployed.

### Pre-Conditions

- [ ] `hermes-agent v0.15.2` installed on VPS (confirmed by P1-004)
- [ ] `git status` is clean (no uncommitted changes)
- [ ] All 7 Guinevere systemd services running healthy
- [ ] PostgreSQL accessible on port 5433
- [ ] Redis accessible on port 6380
- [ ] `pip freeze` baseline saved

---

## Step-by-Step Procedure

### Step 0.1: Run `hermes security` scan

**Command:**
```bash
hermes security --format json > /tmp/phase0-security.json
```

**Expected output:**
```json
{
  "vulnerabilities": [...],
  "summary": {
    "HIGH": 0,
    "MODERATE": 0,
    "LOW": "≤11 resolved or documented"
  }
}
```

**Verification:**
```bash
python -c "
import json
d = json.load(open('/tmp/phase0-security.json'))
high = [v for v in d.get('vulnerabilities', []) if v['severity'] in ('HIGH', 'MODERATE')]
assert len(high) == 0, f'{len(high)} unresolved HIGH/MODERATE: {high}'
print('PASS: Zero HIGH/MODERATE findings')
"
```

**Troubleshooting:**
- If NEW HIGH/CRITICAL findings appear (beyond the 11 known from Report 16) → triage individually. Patch if fix available. Document acceptance if no fix exists.
- If ecdsa timing attack appears (known, no patch) → document in `risk-register.md` with justification: "Guinevere does not use ECDSA signing."
- If `hermes security` command not found → verify `hermes-agent==0.15.2` is installed and in PATH.

### Step 0.2: Upgrade aiohttp to patched version

**Command:**
```bash
cd /home/guinevere/code/guinevere
source .venv/bin/activate
pip install aiohttp>=3.9.0
```

**Expected output:**
```
Successfully installed aiohttp-3.9.*
```

**Verification:**
```bash
python -c "import aiohttp; v=aiohttp.__version__; parts=[int(x) for x in v.split('.')[:2]]; assert parts >= [3,9], f'aiohttp {v} < 3.9.0'; print(f'PASS: aiohttp {v}')"
```

**Troubleshooting:**
- If `pip install` fails with dependency conflict → check `pip check` output. Isolate conflicting package. Try minimum patched version that resolves CVE.
- If discord.py WebSocket disconnects after upgrade → rollback immediately: `pip install -r /home/guinevere/backups/pre-migration-pip-*.txt`
- If `pip check` reports conflicts → document conflicts and assess runtime impact. 24hr soak test required before proceeding.

### Step 0.3: Add `--require-hashes` to pip install commands

**Command:**
```bash
cd /home/guinevere/code/guinevere
source .venv/bin/activate
pip install pip-tools
pip-compile --generate-hashes requirements.in -o requirements-hashes.txt
pip install --require-hashes -r requirements-hashes.txt
```

**Expected output:**
```
Successfully installed [all packages with hash verification]
```

**Verification:**
```bash
pip install --require-hashes -r requirements-hashes.txt --dry-run
echo "Exit code: $?"
# Expected: 0
```

**Troubleshooting:**
- If hash mismatch → regenerate with `pip-compile --generate-hashes` using current versions.
- If `pip-compile` fails → verify `pip-tools` is installed. Check `requirements.in` for unresolved references.
- If version pin conflicts with `--require-hashes` → regenerate hashes for pinned versions only. Do not upgrade unpinned packages during Phase 0.

### Step 0.4: Accept ecdsa timing attack risk

**Command:**
```bash
# Check if ecdsa is in dependency tree
pipdeptree | grep ecdsa || echo "ecdsa not in dependency tree"
```

**Expected output:**
```
ecdsa not in dependency tree
-- OR --
ecdsa==X.Y.Z (dependency of: ...)
```

**Documentation (create `risk-register.md`):**
```bash
cat > /home/guinevere/code/guinevere/risk-register.md << 'EOF'
# Risk Register — Phase 0 Accepted Risks

## R-P0-04-001: ecdsa Timing Attack (HIGH, Unpatched)

**Status**: ACCEPTED — no patch available
**Justification**: Guinevere codebase does not use ECDSA signing or key generation.
The ecdsa package is present only as a transitive dependency. No attack surface exists.
**Mitigation**: Subscribe to CVE notifications. If ECDSA ever imported by Guinevere code → alert.
**Review Date**: 2026-07-04 (30 days)
EOF
```

**Verification:**
```bash
grep -r "import ecdsa\|from ecdsa" /home/guinevere/code/guinevere/src/ && echo "WARNING: ECDSA used" || echo "PASS: ECDSA not imported"
```

### Step 0.5: Triage PyJWT vulnerabilities (x4 UNKNOWN)

**Command:**
```bash
pipdeptree | grep -i pyjwt
grep -r "import jwt\|from jwt\|import PyJWT\|from PyJWT" /home/guinevere/code/guinevere/src/ --include="*.py" || echo "No JWT imports found"
```

**Expected output:**
```
No JWT imports found
-- OR --
PyJWT==X.Y.Z (used by: ...)
```

**Troubleshooting:**
- If PyJWT is imported anywhere in Guinevere code → upgrade to latest version: `pip install PyJWT>=2.8.0`
- If PyJWT is only a transitive dependency of Hermes → bind to patched Hermes version or document exclusion.
- If PyJWT not used → document exclusion in risk register: "PyJWT vulnerabilities are non-exploitable — no JWT handling in Guinevere codebase."

### Step 0.6: Run `hermes doctor`

**Command:**
```bash
hermes doctor --verbose 2>&1 | tee /tmp/phase0-doctor.txt
```

**Expected output:**
```
[PASS] Python version: 3.11.x
[PASS] Hermes version: 0.15.2
[PASS] Config file: /home/guinevere/config/hermes/config.yaml
[PASS] Plugin directory: .../guinevere/plugins/
[PASS] Hook directory: .../guinevere/hooks/
[PASS] All checks passed.
```

**Verification:**
```bash
python -c "
import re
with open('/tmp/phase0-doctor.txt') as f:
    content = f.read()
    fails = re.findall(r'(FAIL|WARN|ERROR)', content)
    assert len(fails) == 0, f'Doctor failures: {fails}'
print('PASS: hermes doctor all green')
"
```

**Troubleshooting:**
- If config path is wrong → set `HERMES_CONFIG_PATH=/home/guinevere/config/hermes/config.yaml`
- If plugin/hook directories missing → create them: `mkdir -p /home/guinevere/code/guinevere/plugins /home/guinevere/code/guinevere/hooks`
- If Python version check fails → verify venv Python is 3.11+: `python --version`

### Step 0.7: Create pre-migration checkpoint

**Command:**
```bash
# Hermes checkpoint
hermes checkpoints create --label "pre-migration-phase0-$(date +%Y%m%d-%H%M%S)"

# Git tag
cd /home/guinevere/code/guinevere
git tag "pre-hermes-migration-$(date +%Y%m%d-%H%M%S)"
git push origin --tags

# Save pip freeze for rollback
source .venv/bin/activate
pip freeze > /home/guinevere/backups/pre-migration-pip-$(date +%Y%m%d).txt

# PostgreSQL full dump
sudo -u postgres pg_dump -Fc guinevere > /home/guinevere/backups/pre-migration-$(date +%Y%m%d).dump

# Record current safety baseline
python -m pytest tests/safety/ -v --tb=short > /home/guinevere/backups/pre-migration-safety-baseline.txt 2>&1
```

**Verification:**
```bash
hermes checkpoints --list | grep "pre-migration-phase0"
git tag | grep "pre-hermes-migration"
ls -lh /home/guinevere/backups/pre-migration-*.dump
ls -lh /home/guinevere/backups/pre-migration-pip-*.txt
```

**Troubleshooting:**
- If `pg_dump` fails → check PostgreSQL is running: `sudo systemctl status postgresql`
- If git tag already exists → use timestamp suffix to make unique
- If disk space is low → verify `/home/guinevere/backups/` has ≥ 1GB free

---

## Safety Checkpoint

| # | Check | Command | Expected |
|---|---|---|---|
| P0-T1 | `hermes security` scan | `hermes security --format json \| python -c "..."` | Zero HIGH/MODERATE |
| P0-T2 | `hermes doctor` all green | `hermes doctor --verbose` | All checks PASS |
| P0-T3 | Dependencies hash-verified | `pip install --require-hashes -r requirements-hashes.txt` | Exit code 0 |
| P0-T4 | aiohttp patched >= 3.9.0 | `python -c "import aiohttp; ..."` | Version >= 3.9.0 |
| P0-T5 | Pre-migration checkpoint | `hermes checkpoints --list` | Checkpoint visible |
| P0-T6 | Safety baseline recorded | `pytest tests/safety/ -v` | All existing tests PASS |

---

## Config Changes

### pip-level Changes (No YAML/systemd)

| Change | Command |
|---|---|
| Pin Hermes with hashes | `pip install hermes-agent==0.15.2 --require-hashes -r requirements-hashes.txt` |
| Upgrade aiohttp | `pip install aiohttp>=3.9.0 --require-hashes` |
| Freeze for rollback | `pip freeze > /home/guinevere/backups/pre-migration-pip-*.txt` |

### Environment Variable Changes

None in Phase 0. All existing `.env` files unchanged. Discord token remains in `.env.discord` under SOPS encryption.

---

## File Changes

| File | Action | Description |
|---|---|---|
| `requirements.txt` | MODIFY | Upgrade aiohttp >= 3.9.0, add hash annotations |
| `pyproject.toml` | MODIFY | Update aiohttp version constraint |
| `requirements-hashes.txt` | CREATE | Lockfile with `--require-hashes` for all packages |
| `risk-register.md` | CREATE | Documented acceptance of ecdsa timing attack risk |
| `setup.sh` / `Makefile` | MODIFY | Add `--require-hashes` flag to pip install commands |

---

## Service Management

**No service stops or restarts in Phase 0.** All changes are pip-level dependency fixes within the `.venv`. All 7 Guinevere systemd services continue running as-is.

| Service | Action |
|---|---|
| `guinevere-discord` | KEEP RUNNING |
| `guinevere-loops` | KEEP RUNNING |
| `guinevere-scheduler` | KEEP RUNNING |
| `guinevere-mcp` | KEEP RUNNING |
| `guinevere-surveillance` | KEEP RUNNING |
| `guinevere-monitoring` | KEEP RUNNING |
| `guinevere-obscura` | KEEP RUNNING |

---

## Risk Register

| Risk ID | Description | Score | Mitigation |
|---|---|---|---|
| R-P0-OVER-01 | aiohttp upgrade breaks transitive dependencies | 9 MEDIUM | 24hr soak test with bot.py running post-upgrade |
| R-P0-01-001 | `hermes security` finds NEW vulnerabilities | 6 MEDIUM | Triage, patch, or document before proceeding |
| R-P0-02-001 | aiohttp >= 3.9.0 breaks discord.py or Hermes WebSocket | 12 HIGH | Install in isolated venv first; full pytest suite |
| R-P0-04-001 | ecdsa HIGH vuln — no patch available | 3 LOW | Document in risk-register.md; Guinevere does not use ECDSA |
| R-P0-05-001 | PyJWT UNKNOWN vulns — triage needed | 6 MEDIUM | Search codebase for JWT imports; document or upgrade |
| R-P0-06-001 | `hermes doctor` reveals config rework needed | 4 LOW | Fix incrementally; re-run after each fix |

---

## Rollback Procedure

```bash
# === PHASE 0 ROLLBACK (< 5 minutes) ===

# 1. Universal kill-switch
hermes gateway stop

# 2. Rollback pip packages to pre-Phase 0 versions
cd /home/guinevere/code/guinevere
PIP_FREEZE=$(ls -t /home/guinevere/backups/pre-migration-pip-*.txt | head -1)
source .venv/bin/activate
pip install -r "$PIP_FREEZE"

# 3. Verify package versions
pip list | grep -E "aiohttp|ecdsa|pip|PyJWT"

# 4. Rollback git changes
git checkout -- config/hermes/config.yaml
git checkout -- .env 2>/dev/null || true

# 5. Verify git clean
git status

# 6. Verify Hermes still works
hermes --help

# 7. Verify all services healthy
for svc in guinevere-discord guinevere-loops guinevere-scheduler \
           guinevere-mcp guinevere-surveillance guinevere-monitoring guinevere-obscura; do
    sudo systemctl is-active $svc
done
```

---

## Test Commands

```bash
# Unit tests
pytest tests/hermes/test_phase0_security.py::test_require_hashes_enabled -v
pytest tests/hermes/test_phase0_security.py::test_aiohttp_version -v
pytest tests/hermes/test_phase0_security.py::test_no_high_vulnerabilities -v

# Full security scan
hermes security --format json

# Doctor check
hermes doctor --verbose

# Dependencies hash verification
pip install --require-hashes -r requirements-hashes.txt

# Pre-existing safety baseline
python -m pytest tests/safety/ -v --tb=short
```

---

## Pre/Post Security Comparison Table

| Metric | Pre-Phase 0 | Post-Phase 0 |
|---|---|---|
| `hermes security` HIGH findings | Unknown (≥ 11) | **0** |
| `hermes security` MODERATE findings | Unknown | **0** |
| `hermes doctor` status | Unknown | **ALL PASS** |
| aiohttp version | < 3.9.0 (vulnerable) | **≥ 3.9.0** (patched) |
| pip hash verification | Disabled | **Enabled** (`--require-hashes`) |
| PyJWT status | Unknown (4 UNKNOWN vulns) | **Triaged** (patched or documented excluded) |
| ecdsa risk | Unknown (HIGH vuln, no patch) | **Documented** in risk-register.md |
| Safety baseline | Unknown | **Recorded** in backups/ |
| Pre-migration checkpoint | None | **Created** (Hermes + git + pip + PG dump) |

---

## Gate Criteria

| Criterion | Measurement | PASS Threshold |
|---|---|---|
| `hermes security` zero HIGH/MODERATE | `hermes security --format json` | `len(high) == 0` |
| `hermes doctor` all PASS | `hermes doctor --verbose` | Zero FAIL/WARN/ERROR |
| Dependencies hash-verified | `pip install --require-hashes` | Exit code 0 |
| aiohttp patched | `python -c "import aiohttp; ..."` | Version >= 3.9.0 |
| PyJWT triaged | Codebase grep | Either upgraded or documented excluded |
| Pre-migration safety net | `hermes checkpoints --list` | Checkpoint + git tag + PG dump exist |
| 24hr soak (optional) | bot.py running with upgraded deps | No crashes, no WebSocket disconnects |

---

## References

| Document | Relevance |
|---|---|
| `adr/ADR-035-hermes-migration.md` | §Phase 0 — Security Remediation |
| `research-reports/migration-plan/02-risk-per-step.md` | §3 — Phase 0 risks (R-P0-*) |
| `research-reports/migration-plan/03-rollback-procedures.md` | §5 — Phase 0 rollback |
| `research-reports/migration-plan/04-safety-checkpoints.md` | §2 — Phase 0 safety checkpoint |
| `research-reports/migration-plan/07-test-suite.md` | §4 — Phase 0 test suite |
| `research-reports/migration-plan/09-config-migration.md` | §3 — Phase 0 config changes |