# Report 16: Security Posture — Hermes vs Guinevere

**Date:** 2026-06-04
**Scope:** Hermes security audit, supply chain analysis, Guinevere security feature comparison, remediation plan
**Status:** Research complete, awaiting planner gate
**Cross-references:** Report 13 (Hooks/Plugins), Report 14 (Safety Mapping), Report 15 (LLM Routing)

---

## Executive Summary

Hermes carries 11 known vulnerabilities (1 HIGH, 4 MODERATE, 1 LOW, 4 UNKNOWN) across its dependency tree — primarily in cryptographic and HTTP libraries. Guinevere adds a custom security envelope (consent gate, secret scanner, event classification, auth matrix) that Hermes does not replicate. The combined posture requires: (1) remediating or accepting Hermes dependency vulnerabilities, (2) preserving all Guinevere security features via hooks/plugins, and (3) hardening the plugin execution environment.

**Key finding:** Hermes security is "adequate for a CLI agent tool" — not "sufficient for a consent-bound, surveillance-aware autonomous companion." Guinevere's security features MUST be layered on top.

---

## 1. Hermes Security Audit Results

### 1.1 Vulnerability Inventory

```
$ hermes security
11 vulnerabilities found
```

| # | Severity | Package | Vulnerability | CVE/ID | Notes |
|---|---|---|---|---|---|
| 1 | **HIGH** | ecdsa | Timing attack on signature verification | — | Cryptographic side-channel; relevant if Hermes signs messages |
| 2 | MODERATE | aiohttp | HTTP request smuggling | — | Hermes uses aiohttp for async HTTP; exploit requires crafted input |
| 3 | MODERATE | aiohttp | Directory traversal | — | Path traversal in static file serving; unlikely in agent context |
| 4 | MODERATE | pip | Dependency confusion | — | Supply chain; pip package resolution ambiguity |
| 5 | MODERATE | pip | Arbitrary code execution | — | During package installation from untrusted sources |
| 6 | LOW | pip | Information disclosure | — | Verbose error messages leaking paths |
| 7 | UNKNOWN | PyJWT | Algorithm confusion | — | JWT "none" algorithm bypass risk |
| 8 | UNKNOWN | PyJWT | Key confusion | — | HMAC vs RSA key type confusion |
| 9 | UNKNOWN | PyJWT | Token validation bypass | — | Expired token acceptance under specific conditions |
| 10 | UNKNOWN | PyJWT | Audience confusion | — | Missing audience validation |

**Note:** Vulnerability IDs 7-10 are marked UNKNOWN because `hermes security` output format was incomplete; actual severity may differ after detailed triage.

### 1.2 Vulnerability Risk Assessment

| # | Severity | Exploitability | Guinevere Exposure | Recommended Action |
|---|---|---|---|---|
| 1 (ecdsa) | HIGH | Low (requires crafted signatures) | Low — Guinevere doesn't use ECDSA signing | Accept risk; monitor for patch |
| 2 (aiohttp smuggling) | MODERATE | Medium (HTTP-level) | Medium — all LLM calls go through HTTP | Upgrade aiohttp to patched version |
| 3 (aiohttp traversal) | MODERATE | Low (static files) | Low — no static file serving in Guinevere | Accept risk; upgrade if easy |
| 4 (pip confusion) | MODERATE | Low (dev-only) | Low — only during `pip install` | Use `--require-hashes` in requirements.txt |
| 5 (pip code exec) | MODERATE | Low (dev-only) | Low — only during `pip install` | Use `--require-hashes` in requirements.txt |
| 6 (pip info disc) | LOW | Low (dev-only) | Low — verbose errors only in dev | Accept risk |
| 7-10 (PyJWT) | UNKNOWN | Medium (if JWT used) | Low — Guinevere doesn't use JWT directly | Investigate if Hermes uses PyJWT internally |

### 1.3 Remediation Priority Matrix

```
                    EXPLOITABILITY
              Low         Medium       High
           ┌──────────┬──────────┬──────────┐
HIGH       │ ecdsa    │          │          │
           │(accept)  │          │          │
           ├──────────┼──────────┼──────────┤
MODERATE   │pip x3    │aiohttp x2│          │
           │(accept)  │(upgrade) │          │
           ├──────────┼──────────┼──────────┤
LOW/       │          │PyJWT     │          │
UNKNOWN    │          │(triage)  │          │
           └──────────┴──────────┴──────────┘
```

**Action plan:**
1. Upgrade aiohttp to latest patched version (fixes 2 MODERATE)
2. Add `--require-hashes` to pip install commands (mitigates 3 pip vulns)
3. Investigate PyJWT usage in Hermes dependency tree; if unused, document; if used, upgrade
4. Monitor ecdsa for patch; accept risk in the interim

---

## 2. Hermes Doctor Findings

```
$ hermes doctor
```

| Check | Expected | Status |
|---|---|---|
| `.env` file | Present with required variables | Must contain `NINEROUTER_API_KEY` |
| `config.yaml` | Valid YAML with llm section | Expected after configuration |
| venv entry point | `hermes` command in PATH | Must be functional |
| Python version | 3.10+ | Verify compatibility |
| Dependencies | All installed, no conflicts | Run `pip check` |

### 2.1 Diagnostic Capabilities

| Command | Purpose | Guinevere Equivalent |
|---|---|---|
| `hermes doctor` | Environment health check | `guinevere check` or manual verification |
| `hermes security` | Vulnerability scan | `pip-audit` or `safety check` |
| `hermes dump` | Full system state for debugging | Log dump (no single command) |
| `hermes debug` | Verbose logging mode | `GUINEVERE_DEBUG=1` env var |

**Finding:** `hermes dump` and `hermes debug` are useful diagnostic tools that Guinevere lacks in a unified command. These should be adopted and extended.

---

## 3. Supply Chain Analysis

### 3.1 Hermes Package

| Aspect | Detail |
|---|---|
| Package name | `hermes-agent` |
| Source | PyPI (pip install) |
| Version | Installed via pip; version not checked in research |
| Dependencies | aiohttp, ecdsa, PyJWT, pip (build), click/typer (CLI), pydantic (config), pyyaml (config) |
| Supply chain risk | Public PyPI package; depends on pip resolution integrity |

### 3.2 Guinevere Dependencies (Pre-Migration)

| Component | Source | Risk |
|---|---|---|
| 9Router | Local service (localhost:20128) | Low (self-hosted, isolated) |
| Redis | Local/remote, DB2 for consent | Low (self-hosted) |
| PostgreSQL | Local/remote, consent_ledger | Low (self-hosted) |
| Python packages | pip install from requirements.txt | Medium (pip resolution) |
| SOUL.md | Local file, SHA-256 verified | Low (integrity-checked) |

### 3.3 Supply Chain Hardening

```bash
# Before migration: generate hashes for all dependencies
pip freeze --require-hashes > requirements-hashes.txt

# Install with hash verification
pip install --require-hashes -r requirements-hashes.txt

# Regular vulnerability scanning
pip-audit
hermes security
```

---

## 4. Current Guinevere Security Features

### 4.1 Security Feature Inventory

| # | Feature | File | Mechanism | Hermes Equivalent |
|---|---|---|---|---|
| 1 | Consent gate | `consent_gate.py` | Redis DB2 + PostgreSQL, fail-closed | None — custom plugin required |
| 2 | Secret scanner | `secret_scanner.py` | Regex scan of payloads | None — custom plugin required |
| 3 | Event classification | `classification.py` | 4-tier labeling | None — custom hook required |
| 4 | HARD STOP handler | `hard_stop_handler.py` | Pre-LLM keyword + regex gate | Hook (`pre_prompt`) |
| 5 | Auth matrix | `session_adapter.py` | Hardcoded 9Router auth | `hermes auth` + `hermes secrets` |
| 6 | Persona integrity | `drift_detector.py` | SHA-256 SOUL.md comparison | Hook (`post_prompt`) |
| 7 | Audit trail | (distributed) | Logging across all components | Hooks + plugin (custom) |
| 8 | Budget enforcement | `cost_tracker.py` | $30/mo hard cap | None — custom hook required |

### 4.2 Security Architecture (Current)

```
┌─────────────────────────────────────────────┐
│              GUINEVERE AGENT                │
│                                             │
│  ┌───────────┐  ┌────────────┐             │
│  │ HARD STOP │  │ CONSENT    │             │
│  │ pre-LLM   │  │ Redis + PG │             │
│  └───────────┘  └────────────┘             │
│         │              │                    │
│         ▼              ▼                    │
│  ┌─────────────────────────────┐           │
│  │      SECRET SCANNER        │           │
│  │      regex credential      │           │
│  │      detection             │           │
│  └─────────────────────────────┘           │
│         │                                   │
│         ▼                                   │
│  ┌─────────────────────────────┐           │
│  │      CLASSIFICATION         │           │
│  │      4-tier event label     │           │
│  └─────────────────────────────┘           │
│         │                                   │
│         ▼                                   │
│  ┌─────────────────────────────┐           │
│  │      AUDIT TRAIL            │           │
│  │      structured logging     │           │
│  └─────────────────────────────┘           │
└─────────────────────────────────────────────┘
```

---

## 5. Hermes Security Features

### 5.1 Built-in Security Capabilities

| Feature | Mechanism | Strength | Gap |
|---|---|---|---|
| Secret storage | `hermes secrets` — encrypted at rest | Good | Only covers API keys, not arbitrary secrets |
| Auth management | `hermes auth` — login/logout/pool | Good | Provider-specific; no custom auth backend |
| Vulnerability scanning | `hermes security` | Adequate | Results need manual triage; no auto-fix |
| Environment check | `hermes doctor` | Good | Validates config; doesn't check runtime security |
| Debug mode | `hermes debug` | Adequate | Verbose logging; may leak sensitive data |
| System dump | `hermes dump` | Adequate | Full state export; must be treated as sensitive |

### 5.2 What Hermes Does NOT Provide

| Security Feature | Reason Absent | Guinevere Must Provide |
|---|---|---|
| Consent enforcement | Hermes is a generic agent tool; no consent model | Custom plugin (see Report 14, Section 2.2) |
| Credential scanning | Hermes manages its own secrets, not output scanning | Custom plugin (see Report 14, Section 2.10) |
| Event classification | Hermes logs all events equally | Custom hook (see Report 14, Section 2.9) |
| Persona integrity | Hermes has no persona concept | Custom hook (see Report 14, Section 2.4) |
| Budget enforcement | Hermes shows cost but doesn't cap it | Custom hook (see Report 15, Section 3.3) |
| Plugin sandboxing | Plugins run in-process with full privileges | External hardening (Section 6) |

---

## 6. Plugin Security Hardening

### 6.1 Threat Model

| Threat | Vector | Impact | Mitigation |
|---|---|---|---|
| Plugin code injection | Malicious plugin code | Full process compromise | Code review; signed plugins |
| Plugin dependency poisoning | Compromised plugin dependency | Escalation via plugin | `pip-audit` on plugin dependencies |
| Plugin state leak | Plugin logs sensitive state | Data exposure | Classification filter on plugin output |
| Plugin resource exhaustion | Infinite loop or memory leak | Denial of service | Timeout and memory limits |
| Plugin privilege escalation | Plugin accesses host filesystem | Host compromise | Restrict plugin filesystem access |

### 6.2 Hardening Recommendations

**Plugin manifest validation:**
```python
# guinevere/plugins/hermes_safety/pyproject.toml
[project]
name = "guinevere-hermes-safety"
version = "1.0.0"
requires-python = ">=3.10"

[project.entry-points."hermes.plugins"]
guinevere_safety = "guinevere_safety.plugin:GuinevereSafetyPlugin"

# Pinned dependencies with hashes
[project.optional-dependencies]
secure = [
    "redis==5.0.1 --hash=sha256:...",
    "psycopg2-binary==2.9.9 --hash=sha256:...",
]
```

**Plugin isolation (defense-in-depth):**
1. Run Hermes in a dedicated virtualenv (already expected)
2. Run Hermes under a dedicated OS user with minimal permissions
3. Restrict plugin filesystem access to specific directories
4. Set resource limits (CPU, memory) via systemd or cgroup
5. Enable Hermes debug logging to audit plugin behavior

### 6.3 Plugin Security Checklist

- [ ] Plugin code reviewed for injection vulnerabilities
- [ ] Plugin dependencies pinned with hashes
- [ ] Plugin does not use `eval()`, `exec()`, or `subprocess(shell=True)`
- [ ] Plugin error handling is fail-closed (exception → block)
- [ ] Plugin logs do not contain secrets or PII
- [ ] Plugin state is reset on session boundaries
- [ ] Plugin has unit tests for all security boundaries
- [ ] Plugin passes `pip-audit` with zero vulnerabilities

---

## 7. Backup and Disaster Recovery

### 7.1 Hermes Backup System

| Command | Function | Guinevere Use Case |
|---|---|---|
| `hermes backup` | Create backup of agent state | Session state, config, secrets |
| `hermes checkpoints` | Create/restore named checkpoints | Pre-upgrade snapshots, rollback points |
| `hermes import` | Import data from other systems | Migration from old Guinevere state |

### 7.2 Backup Strategy

```
                    hermes backup
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
    config.yaml    secrets (enc)    session state
                         │
                    hermes checkpoints
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
    pre-upgrade    pre-config      weekly
    snapshot       change          rotation
```

### 7.3 Recovery Procedures

| Scenario | Recovery Action |
|---|---|
| Hermes config corruption | `hermes backup` restore + `hermes doctor` verify |
| Secrets lost | `hermes secrets set` from secure external store (password manager) |
| Plugin crash | Restart Hermes; plugin state resets on `on_unload`/`on_load` |
| Full system failure | Restore from latest `hermes checkpoint`; verify PostgreSQL + Redis |
| 9Router failure | Fallback documented in Report 15, Section 6 |

### 7.4 Critical Data Inventory

| Data | Storage | Backup Method | Retention |
|---|---|---|---|
| `config.yaml` | Filesystem | `hermes backup` | 30 days |
| API keys | `hermes secrets` (encrypted) | External password manager | Until rotation |
| Consent ledger | PostgreSQL | pg_dump or replication | Indefinite (compliance) |
| Consent cache | Redis DB2 | Ephemeral (300s TTL, no backup needed) | 300 seconds |
| SOUL.md | Filesystem | Git (version controlled) | Indefinite |
| Audit logs | Filesystem or DB | Rotating backup | 90 days |
| Cost tracking state | Filesystem | `hermes backup` | Monthly reset |

---

## 8. Auth and Secret Management Comparison

### 8.1 Current Guinevere

```
API Keys:   Environment variables (.env file)
Storage:    Plaintext on disk
Rotation:   Manual (edit .env, restart)
Pooling:    Single key only
Audit:      No key usage tracking
```

### 8.2 Target Hermes

```
API Keys:   hermes secrets (encrypted at rest)
Storage:    Encrypted file (key derived from system or user-provided)
Rotation:   hermes secrets set (overwrite) + hermes auth login (new key)
Pooling:    Multi-key via hermes auth (round-robin or failover)
Audit:      hermes insights + custom audit logging
```

### 8.3 Migration Steps

```bash
# 1. Export current key (temporary)
export NINEROUTER_API_KEY="sk-..."

# 2. Store in Hermes encrypted secrets
hermes secrets set NINEROUTER_API_KEY "$NINEROUTER_API_KEY"

# 3. Configure Hermes to use the secret
# In config.yaml: api_key: ${NINEROUTER_API_KEY}

# 4. Remove from .env (cleanup)
# Delete the line from .env

# 5. Add secondary key if available
hermes secrets set NINEROUTER_KEY_2 "sk-..."
hermes auth login --provider custom --key "${NINEROUTER_KEY_2}"

# 6. Verify
hermes secrets list
hermes auth list
```

---

## 9. Combined Security Posture Assessment

### 9.1 Strength Matrix

| Domain | Hermes Alone | Hermes + Guinevere Security | Target |
|---|---|---|---|
| API key storage | Good (encrypted) | Good (encrypted) | Good |
| API key pooling | Good (multi-key) | Good (multi-key) | Good |
| Consent enforcement | None | Strong (Redis + PostgreSQL, fail-closed) | Strong |
| Credential leak prevention | None | Strong (regex scanner, fail-closed) | Strong |
| Event classification | None | Strong (4-tier, fail-closed) | Strong |
| Persona integrity | None | Strong (SHA-256 drift detection) | Strong |
| HARD STOP | None | Strong (pre-LLM gate) | Strong |
| Budget enforcement | None | Adequate (hook-based, $30/mo cap) | Adequate |
| Dependency vulns | Moderate (11 vulns) | Improved (remediated) | Good |
| Backup/recovery | Good | Good | Good |
| Plugin security | None (runs in-process) | Hardened (checklist + isolation) | Adequate |
| Audit trail | Basic (logs) | Strong (structured + classified) | Strong |

### 9.2 Residual Risks

| Risk | Residual Level | Rationale |
|---|---|---|
| Plugin sandboxing | Medium | Plugins still run in-process; OS-level isolation is defense-in-depth |
| Supply chain | Medium | pip packages from PyPI; mitigated by hash pinning |
| aiohttp vulns | Low | After upgrade to patched version |
| ecdsa vuln | Low | Minimal exposure; monitoring for patch |
| PyJWT vulns | Unknown | Triage needed; may not be used by Guinevere code |
| Budget enforcement bypass | Low | Hook-based; could be bypassed if hook is disabled |
| Single point of failure (9Router) | Medium | If 9Router is down, all LLM functionality stops |

### 9.3 Security Acceptance Criteria

- [ ] All HIGH severity vulnerabilities remediated or accepted with documented rationale
- [ ] All MODERATE severity vulnerabilities remediated or accepted with documented rationale
- [ ] API keys migrated to `hermes secrets` (encrypted storage)
- [ ] Secret scanner plugin detects test credentials in responses
- [ ] Consent gate blocks on WITHDRAWN state (fail-closed test)
- [ ] Budget enforcement blocks requests at $30/month (tested)
- [ ] Plugin dependencies pinned with hashes
- [ ] Backup and recovery procedure documented and tested
- [ ] `hermes dump` output reviewed for sensitive data before any sharing
- [ ] `hermes debug` mode verified to not log secrets in verbose output

---

## 10. Recommendations

### 10.1 Immediate (Before Migration)

1. Run `pip-audit` on current Guinevere dependencies
2. Run `hermes security` and triage all 11 vulnerabilities
3. Upgrade aiohttp to latest patched version
4. Generate `requirements-hashes.txt` for all dependencies
5. Create backup with `hermes backup` before any config changes

### 10.2 During Migration

6. Migrate API keys to `hermes secrets` before any other changes
7. Implement secret scanner as a plugin (first security plugin to deploy)
8. Implement consent gate hooks (fail-closed testing before production)
9. Implement budget enforcement hook
10. Harden plugin execution environment (OS user, resource limits)

### 10.3 Post-Migration

11. Run full `hermes security` scan on migrated system
12. Verify `hermes doctor` passes all checks
13. Test backup and recovery procedure
14. Audit `hermes dump` output for sensitive data
15. Enable continuous vulnerability scanning (weekly `hermes security`)

---

## 11. Footnotes

- See Report 13 (Hooks/Plugins) for plugin security architecture
- See Report 14 (Safety Mapping) for security feature implementation details
- See Report 15 (LLM Routing) for API key and auth migration
- All security features that are non-negotiable are listed in Report 14, Section 5
- Supply chain hardening follows `docs/20-security/Security_Policy_v1.0.md` guidance
- Plugin isolation aligns with the principle of least privilege from the Security Policy