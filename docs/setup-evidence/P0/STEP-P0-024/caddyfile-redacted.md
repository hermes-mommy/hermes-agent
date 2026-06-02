# P0-024 — Caddyfile Evidence (Redacted)

**Source:** `/etc/caddy/Caddyfile` on VPS (`faiz-prod-01`)  
**Symlink target:** `/home/guinevere/config/caddy/Caddyfile`  
**Date:** 2026-05-31  
**Step:** P0-024 — Caddy Reverse Proxy

---

## Caddyfile Content

```caddy
{
    admin off
    auto_https off
    http_port 18080
    https_port 18443
}

# Guinevere Internal Services (Tailscale only)

# FastAPI backend
guinevere-vps:8443 {
    bind 100.94.104.22 127.0.0.1
    tls internal
    reverse_proxy localhost:8000
}

# Grafana
guinevere-vps:3443 {
    bind 100.94.104.22 127.0.0.1
    tls internal
    reverse_proxy localhost:3000
}

# Prometheus
guinevere-vps:9443 {
    bind 100.94.104.22 127.0.0.1
    tls internal
    reverse_proxy localhost:9090
}
```

## Configuration Notes

| Setting | Value | Purpose |
|---|---|---|
| `admin off` | Disabled | Security — no admin API exposure |
| `auto_https off` | Disabled | Internal/Tailscale-only, no public ACME |
| `http_port` | 18080 | Offset to avoid Aizanta port 80 |
| `https_port` | 18443 | Offset port for HTTPS |
| Bind IP | `100.94.104.22` (Tailscale) + `127.0.0.1` | No public internet exposure |
| TLS | `tls internal` | Self-signed, Tailscale-only trust domain |

## Port Map

| Site | Port | Backend | Access |
|---|---|---|---|
| FastAPI | 8443 | `localhost:8000` | Tailscale + localhost |
| Grafana | 3443 | `localhost:3000` | Tailscale + localhost |
| Prometheus | 9443 | `localhost:9090` | Tailscale + localhost |

## Security Notes

- Port 2019 (Caddy admin API): **Must be `admin off`** or bound to localhost-only
- All 3 sites bind Tailscale IP only — not reachable from public internet
- `tls internal` generates self-signed certs — valid within Tailscale trust domain
- Aizanta port 80 (nginx) is NOT touched

**Footer:**  
Source: P0-024 auditor finding B5#4 resolution  
Date: 2026-05-31  
Author: Guinevere