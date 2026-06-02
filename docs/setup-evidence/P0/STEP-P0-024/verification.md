# STEP-P0-024 — Verification

**Step**: P0-024 — Caddy Reverse Proxy
**Date**: 2026-05-31
**Status**: PASS, independent auditor gate passed

---

## 1. What Was Done
Installed Caddy 2.11.3 via Cloudsmith official repo. Configured reverse proxy with 3 TLS sites (FastAPI:8443, Grafana:3443, Prometheus:9443) on Tailscale IP and localhost. Service runs under guinevere.slice. Port 80 bypassed (Aizanta nginx). Backends not running yet (P0 infrastructure phase).

## 2. Files Changed
**Remote (VPS)**:
- `/etc/apt/sources.list.d/caddy-stable.list` — NEW
- `/etc/caddy/Caddyfile` — NEW (3 sites, TLS internal)
- `/etc/systemd/system/caddy.service.d/guinevere-slice.conf` — NEW

## 3. Validation Results

### Service
```
caddy.service active (running)
systemctl is-active caddy → active
```

### Listening Ports (ss)
```
100.94.104.22:8443 (caddy)
100.94.104.22:3443 (caddy)
127.0.0.1:9443    (caddy)
```

### Version
```
Caddy v2.11.3
```

### Aizanta Status
```
aizanta-bot, nginx, frontend, postgres, redis — 5/5 healthy
Protected ports unchanged: 127.0.0.1:6379, 100.94.104.22:80, 127.0.0.1:5432
```

## 4. Evidence Artifacts
- `caddy-status.txt` — installation, config, service status
- `caddy-config.txt` — redacted Caddyfile (admin off, auto_https off)
- `aizanta-post-check.md` — Aizanta health verification
- `p0-024-summary.md` — summary and caveats

## 5. Shared VPS Impact
- No port conflict (Caddy: 8443/3443/9443 vs Aizanta: 80)
- No Aizanta containers/ports touched
- Caddy under guinevere.slice (isolated from Aizanta)

## 6. ADR Compliance
- ADR-014: systemd service, guinevere.slice resource caps
- ADR-019: binds Tailscale IP only (no public ports)

## 7. AC Reference
- AC-CORE-001: systemd-managed service

## 8. Rollback / Re-run Safety
- Remove repo: `rm /etc/apt/sources.list.d/caddy-stable.list`
- Remove package: `apt purge caddy`
- Re-run: idempotent (apt install + overwrite Caddyfile)

## 9. Design Decisions / Caveats
- Backends not running (expected for P0 infrastructure)
- TLS self-signed (internal network via Tailscale)
- auto_https off (port 80 collision with Aizanta nginx)
- Prometheus also exposed via Tailscale (monitoring access), not public

## 10. Evidence Gate
| Gate | Status |
|---|---|
| Parent verification | PASS |
| LSP diagnostics | Clean |
| Secret scan | No plaintext secrets |
| Aizanta guardrails | 5/5 healthy |
| Independent auditor gate | PASS |

Auditor report: `audit-reports/P0/STEP-P0-024/step-p0-024-auditor-report.md`
Auditor verdict: PASS after fixes (admin off → port 2019 gone, Caddyfile symlink created, evidence updated)

## 11. Footer
- Source task: STEP-P0-024
- Implementer: Guinevere (Sisyphus agent)
- Auditor: PASS (bg_ffbc20e1, fixes applied, admin off + symlink + evidence corrected)
- Date: 2026-05-31