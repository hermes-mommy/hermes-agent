# Auditor Report: P1-018 — guinevere-core Systemd Service Deployment

## Verdict: **PASS** ✅

---

## Audit Summary

All 8 independent verification checks pass. The deployed systemd service matches the local reference copy exactly. No secrets, credentials, or sensitive data exposed. Evidence claims are consistent with live state.

---

## Verification Matrix

| # | Check | Expected | Actual | Result |
|---|-------|----------|--------|--------|
| 1 | `systemctl is-active guinevere-core` | `active` | `active` | ✅ PASS |
| 2 | `systemctl show -p Slice` | `guinevere.slice` | `guinevere.slice` | ✅ PASS |
| 3 | `MemoryHigh` | `1073741824` (1G) | `1073741824` | ✅ PASS |
| 4 | `MemoryMax` | `2147483648` (2G) | `2147483648` | ✅ PASS |
| 5 | `CPUQuotaPerSecUSec` | `2s` (200%) | `2s` | ✅ PASS |
| 6 | `curl /health` | `{"status":"healthy","service":"guinevere-core","version":"0.1.0"}` | matches | ✅ PASS |
| 7 | `curl /` | `{"message":"Guinevere de Baroque is online.","status":"active"}` | matches | ✅ PASS |
| 8 | `Requires=` in unit file | `docker.service guinevere-9router.service` | matches | ✅ PASS |
| 9 | `Type=` in unit file | `exec` | `exec` | ✅ PASS |
| 10 | `ProtectSystem=` in unit file | `strict` | `strict` | ✅ PASS |
| 11 | `systemctl status` shows `guinevere` user & `guinevere.slice` | CGroup: `/guinevere.slice/guinevere-core.service` | confirmed | ✅ PASS |
| 12 | Service enabled on boot | symlink in `multi-user.target.wants` | confirmed (enabled) | ✅ PASS |

## Live vs Evidence File Comparison

Live unit file at `/etc/systemd/system/guinevere-core.service` and local reference at `docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service`:

| Section | Live | Local Copy | Match |
|---------|------|------------|-------|
| After | `docker.service network.target guinevere-9router.service` | identical | ✅ |
| Requires | `docker.service guinevere-9router.service` | identical | ✅ |
| Type | `exec` | identical | ✅ |
| User | `guinevere` | identical | ✅ |
| MemoryHigh | `1G` | identical | ✅ |
| MemoryMax | `2G` | identical | ✅ |
| CPUQuota | `200%` | identical | ✅ |
| ProtectSystem | `strict` | identical | ✅ |
| ProtectHome | `read-only` | identical | ✅ |
| ExecStart | `/home/guinevere/code/guinevere/.venv/bin/uvicorn ...` | identical | ✅ |

**Files match exactly** — no drift between local evidence and deployed state.

## Evidence Claims Verification

| Evidence Claim (evidence.md) | Live Confirmation | Result |
|------------------------------|-------------------|--------|
| Service `active (running)`, PID 661232 | Confirmed: active, PID 661232 | ✅ |
| Health endpoint returns expected JSON | Confirmed | ✅ |
| Root endpoint returns expected JSON | Confirmed | ✅ |
| Port 8000 listening on localhost only | Confirmed (127.0.0.1:8000) | ✅ |
| Running as guinevere user | Confirmed | ✅ |
| guinevere.slice CGroup | Confirmed: `/guinevere.slice/guinevere-core.service` | ✅ |
| MemoryHigh=1G, MemoryMax=2G | Confirmed: 1073741824 / 2147483648 | ✅ |
| CPUQuota=200% | Confirmed: 2s | ✅ |
| NoNewPrivileges, ProtectSystem=strict, ProtectHome=read-only | Confirmed in live unit file | ✅ |
| Enabled on boot | Confirmed: `loaded; enabled` | ✅ |

## Secrets Exposure Check

- **Environment variables** in unit file: only `PYTHONPATH`, `PYTHONDONTWRITEBYTECODE`, `VIRTUAL_ENV` — no tokens, keys, or credentials.
- **ExecStart** and paths: no secrets leaked.
- **Journalctl logs**: no `key`, `token`, `secret`, `password`, `credential`, or `api_key` matches.
- **Health/root endpoints**: return only status strings.

**No secrets, API keys, or credentials exposed.** ✅

## Boundary Compliance Check

| Boundary | Status |
|----------|--------|
| Persona drift | N/A — no persona code deployed |
| Consent violation | N/A — no surveillance/consent code in core |
| Yandere drift (Y6+) | N/A |
| HARD STOP bypass | N/A |
| Distress protocol suppression | N/A |
| Secrets exposure | ✅ CLEAN |
| Runs as non-root (guinevere user) | ✅ |
| Port bound to localhost only | ✅ |
| ProtectSystem=strict enabled | ✅ |

## Auditor Gate Checklist

| Item | Status |
|------|--------|
| DoD items all pass | ✅ |
| Diagnostics clean (live service active) | ✅ |
| Evidence files exist and match scope | ✅ |
| Docs sync (evidence.md) accurate | ✅ |
| Cross-references valid | ✅ |
| Boundary compliance preserved | ✅ |
| Secrets exposure clean | ✅ |
| Sub-agent parent verification complete | ✅ |

## Findings

### Critical: 0
### High: 0
### Medium: 0
### Low: 0

**No findings.** All checks pass with zero deviations.

---

## Footer

- **Audit scope**: P1-018 guinevere-core systemd service deployment
- **Audit date**: 2026-06-01
- **Auditor**: Guinevere (independent audit gate)
- **Verification method**: SSH to guinevere-vps, systemctl checks, curl endpoints, grep service file, journalctl inspection
- **Evidence paths**:
  - Local: `docs/setup-evidence/P1/STEP-P1-018/evidence.md`
  - Local: `docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service`
  - Live: `/etc/systemd/system/guinevere-core.service`
- **Verdict**: PASS ✅