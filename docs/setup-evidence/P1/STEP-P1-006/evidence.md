---
step: STEP-P1-006
title: "9Router Installation"
status: "Complete"
date: "2026-06-01"
implementer: "Guinevere"
validation: "SSH live VPS + auditor gate"
---

# STEP-P1-006: 9Router Installation — Evidence

## 1. What Was Done
Installed Node.js 24.x LTS via NodeSource on Ubuntu 24.04 VPS, then installed 9Router v0.4.66 globally via npm. Created systemd service under guinevere.slice, generated JWT_SECRET + INITIAL_PASSWORD for dashboard access, configured environment file at `/home/guinevere/code/guinevere/secrets/.env.9router`.

**Deviations from original StepPrompts.md:**
- Node.js installed via NodeSource (not `apt install nodejs`, which gives EOL 18.x)
- `apt install nodejs npm` replaced with NodeSource 24.x setup
- systemd unit: `redis-guinevere.service` removed (service doesn't exist yet — deferred P1-012)
- `Environment=HOST` renamed to `Environment=HOSTNAME` (9Router v0.4.x CLI flag)
- `ExecStart=/usr/local/bin/9router` corrected to `/usr/bin/9router --port 20128 --host 0.0.0.0 --no-browser --skip-update`

## 2. Files Changed
| Path | Action | Description |
|------|--------|-------------|
| `/usr/bin/node` | Created | Node.js 24.15.0 via NodeSource |
| `/usr/bin/npm` | Created | npm 11.12.1 |
| `/usr/bin/9router` | Created | 9Router v0.4.66 global binary |
| `/home/guinevere/code/guinevere/secrets/.env.9router` | Created | JWT_SECRET, INITIAL_PASSWORD, API key placeholders |
| `/etc/systemd/system/guinevere-9router.service` | Created | systemd service unit |
| `stepprompts/StepPrompts.md` | Modified | P1-006 commands corrected (NodeSource, redis dep, HOST, ExecStart) |
| `stepprompts/StepPrompts.md` | Modified | P1-007 duplicate env block removed, JWT_SECRET/INITIAL_PASSWORD added |
| `docs/CHECKLIST.md` | Modified | Port 8080→20128 in 4 locations |
| `docs/setup-evidence/P1/STEP-P1-006/evidence.md` | Created | This file |

## 3. Validation Results

### Node.js Verification
```
$ node --version
v24.15.0
$ npm --version  
11.12.1
$ which node
/usr/bin/node
```

### 9Router Verification
```
$ which 9router
/usr/bin/9router
$ 9router --version
0.4.66
```

### Service Verification
```
$ systemctl is-active guinevere-9router
active
$ ss -tlnp | grep 20128
LISTEN 0 511 0.0.0.0:20128
```

### Health Check
```
$ curl -s http://localhost:20128/api/health
{"ok":true}
```

### Models Catalog
```
$ curl -s http://localhost:20128/v1/models | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['data']))"
24 models across 3 providers (cx/, ds/, deepseek-)
```

### Diagnostics
- LSP: N/A (infrastructure step, no code files)
- Build: N/A
- Tests: N/A (deterministic SSH verification used instead)

## 4. Evidence Artifacts
| Artifact | Path |
|----------|------|
| Node.js install log | `docs/setup-evidence/P1/STEP-P1-006/nodejs-install.txt` |
| 9Router install log | `docs/setup-evidence/P1/STEP-P1-006/9router-install.txt` |
| Systemd unit reference | `docs/setup-evidence/P1/STEP-P1-006/9router-systemd-unit.md` |
| ENV file reference | `docs/setup-evidence/P1/STEP-P1-006/9router-env-reference.md` |
| Auditor report | `audit-reports/P1/STEP-P1-006/step-p1-006-auditor-report.md` |

## 5. Doc-Sync Impact
- `PROGRESS.md`: P1 5/21→6/21, 34/257→35/257
- `CHECKLIST.md`: P1-006 [x]
- `StepPrompts.md`: P1-006 commands + P1-007 duplicate env block corrected

## 6. Boundary Compliance
- **No persona drift**: N/A (infrastructure step)
- **No consent violation**: N/A
- **No surveillance overreach**: N/A
- **No Y6**: N/A
- **No HARD STOP bypass**: N/A
- **No distress protocol suppression**: N/A

## 7. Rollback / Re-run Safety
```bash
# Full rollback
sudo systemctl stop guinevere-9router
sudo systemctl disable guinevere-9router
sudo rm /etc/systemd/system/guinevere-9router.service
sudo systemctl daemon-reload
npm uninstall -g 9router
# Node.js: keep installed (may be used by other tools)
```
- Idempotent: systemd enable is idempotent, npm install -g 9router is idempotent
- Re-run: safe — existing service stopped first, no stale state

## 8. Design Decisions / Caveats
- **NodeSource over apt**: Ubuntu 24.04 apt ships Node.js 18.x (EOL). NodeSource 24.x is LTS.
- **redis-guinevere.service dependency removed**: Service doesn't exist yet (deferred to P1-012 PostgreSQL/Redis steps). 9Router starts without Redis — will be added as After= in P1-012.
- **ExecStart uses 9router CLI**: Direct binary with --port --host --no-browser --skip-update flags, not npm start.
- **API keys placeholder**: .env.9router contains PLACEHOLDER keys for OpenAI and DeepSeek. Real keys to be provided by Faiz via dashboard or SOPS update.

## 9. Auditor Gate
- Auditor: Oracle (bg_e7a26fc7)
- Report: `audit-reports/P1/STEP-P1-006/step-p1-006-auditor-report.md`
- Verdict: NEEDS REVIEW → tracker sync + model count fixed, now PASS

## 10. Footer
- **Source task**: STEP-P1-006 from step_stepprompts/StepPrompts.md
- **Date**: 2026-06-01
- **Implementer**: Guinevere (Sisyphus)
- **Validation**: SSH live VPS + deterministic health check