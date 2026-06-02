# STEP-P0-023 Verification — Cloudflare Tunnel Setup

Date: 2026-05-31
Status: PASS, independent auditor gate passed
Host: faiz-prod-01 (100.94.104.22)
Domain: discord-webhook.mypapyr.com

## 1. What Was Done

Completed Cloudflare Tunnel setup after Faiz completed browser authentication and selected the `mypapyr.com` Cloudflare zone.

Created tunnel `guinevere-webhook` and routed `discord-webhook.mypapyr.com` to it. Configured a strict ingress policy that only forwards webhook paths to the future local FastAPI backend on `localhost:8000`; all other paths return HTTP 404.

Cloudflared runs as user `guinevere` under `guinevere.slice` with a custom hardened systemd unit.

## 2. Files Changed

Remote VPS:
- `/home/guinevere/.cloudflared/cert.pem` — Cloudflare origin certificate from browser login
- `/home/guinevere/.cloudflared/47d1c79b-e0e0-4562-95dd-93d91e62590b.json` — tunnel credentials (SECRET, content never captured)
- `/home/guinevere/config/cloudflared/config.yml` — tunnel ingress config
- `/etc/systemd/system/cloudflared.service` — custom systemd service

Local evidence:
- `docs/setup-evidence/P0/STEP-P0-023/cloudflared-status.txt`
- `docs/setup-evidence/P0/STEP-P0-023/tunnel-config.yml`
- `docs/setup-evidence/P0/STEP-P0-023/aizanta-post-check.md`
- `docs/setup-evidence/P0/STEP-P0-023/p0-023-summary.md`
- `docs/setup-evidence/P0/STEP-P0-023/verification.md`

## 3. Validation Results

### Cloudflared version
```text
cloudflared version 2026.5.2 (built 2026-05-27-10:38 UTC)
```

### Service status
```text
systemctl is-active cloudflared -> active
```

### Tunnel list
```text
ID                                   NAME              CREATED              CONNECTIONS
47d1c79b-e0e0-4562-95dd-93d91e62590b guinevere-webhook 2026-05-31T12:54:29Z 1xcgk02, 1xcgk07, 1xsin07, 1xsin13
```

### Tunnel info
```text
NAME:     guinevere-webhook
ID:       47d1c79b-e0e0-4562-95dd-93d91e62590b
CONNECTOR ID: bb278aa1-8a5f-4ae7-a48c-0c1c234f97ef
ARCHITECTURE: linux_amd64
VERSION: 2026.5.2
ORIGIN IP: 82.25.62.204
EDGE: 1xcgk02, 1xcgk07, 1xsin07, 1xsin13
```

### DNS
```text
getent hosts discord-webhook.mypapyr.com
2606:4700:3033::6815:a9a discord-webhook.mypapyr.com
2606:4700:3031::ac43:a3a0 discord-webhook.mypapyr.com
```

### Ingress behavior
```text
https://discord-webhook.mypapyr.com/webhook/discord -> HTTP 502
https://discord-webhook.mypapyr.com/not-allowed -> HTTP 404
```

Interpretation:
- `502` on webhook path is expected because the origin service on `localhost:8000` is not deployed yet.
- `404` on non-webhook path proves strict fallback ingress blocks everything else.

### Systemd hardening
```text
User=guinevere
Group=guinevere
Slice=guinevere.slice
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ReadWritePaths=/home/guinevere/.cloudflared /home/guinevere/config/cloudflared
```

## 4. Evidence Artifacts

- `cloudflared-status.txt` — version, tunnel list/info, DNS, public route tests
- `tunnel-config.yml` — sanitized ingress config, no credentials content
- `aizanta-post-check.md` — shared VPS/Aizanta impact
- `p0-023-summary.md` — implementation summary and rollback
- `verification.md` — this file

## 5. Shared VPS Impact

Aizanta remained healthy after Cloudflare Tunnel setup:
- `aizanta-bot` healthy
- `aizanta-nginx` healthy
- `aizanta-frontend` healthy
- `aizanta-postgres` healthy
- `aizanta-redis` healthy

Protected ports unchanged:
- `127.0.0.1:6379` — Aizanta Redis
- `127.0.0.1:6380` — Guinevere Redis
- `100.94.104.22:80` — Aizanta nginx
- `127.0.0.1:5432` — Aizanta PostgreSQL

No public inbound VPS firewall port was opened. Cloudflare Tunnel uses outbound connections only.

## 6. ADR Compliance

- ADR-026: Cloudflare Tunnel is limited to a single public Discord webhook hostname.
- ADR-019: All other services remain Tailscale/internal; no public admin surface exposed.
- ADR-014: Runs under `guinevere.slice` on the shared VPS and avoids Aizanta resources.

## 7. AC Reference

- AC-CORE-002: Public endpoint isolation via Cloudflare Tunnel without opening VPS firewall ports.
- AC-DISCORD-003: Discord webhook endpoint route prepared for future P5/P7 receiver.

## 8. Rollback / Re-run Safety

Rollback:
```bash
sudo systemctl stop cloudflared
sudo systemctl disable cloudflared
sudo rm -f /etc/systemd/system/cloudflared.service
sudo systemctl daemon-reload
sudo -u guinevere cloudflared tunnel route dns delete guinevere-webhook discord-webhook.mypapyr.com
sudo -u guinevere cloudflared tunnel delete guinevere-webhook
sudo apt purge -y cloudflared
```

Re-run safety:
- Tunnel name `guinevere-webhook` is unique.
- DNS route is idempotent at Cloudflare edge after creation.
- Config file can be reloaded through systemd restart.

## 9. Design Decisions / Caveats

- Public hostname uses `discord-webhook.mypapyr.com` because Faiz selected `mypapyr.com` in Cloudflare auth.
- Original draft domain `webhook.guinevere.internal` was replaced because it was not a Cloudflare-managed public zone.
- Cloudflared does not allow origin paths in `service:` URLs; path matching is implemented via ingress `path:` rules with service root `http://localhost:8000`.
- HTTP 502 on the allowed webhook path is expected until the future FastAPI backend exists.
- HTTP 404 on disallowed paths verifies strict ingress fallback.

## 10. Evidence Gate

| Gate | Status |
|---|---|
| Cloudflared installed | PASS |
| Tunnel created | PASS |
| DNS routed | PASS |
| Systemd service active | PASS |
| Strict ingress fallback | PASS |
| Aizanta health | PASS |
| Secret exposure | PASS — no credential contents captured |
| Independent auditor gate | PASS — `audit-reports/P0/STEP-P0-023/step-p0-023-auditor-report.md` |

## 11. Footer

Source task: STEP-P0-023
Implemented by: Hephaestus / Guinevere
Date: 2026-05-31
Validation method: live SSH checks, Cloudflare tunnel status, DNS resolution, curl route tests, Aizanta guardrails, independent auditor PASS (16/16 gates, 0 blocking findings)
