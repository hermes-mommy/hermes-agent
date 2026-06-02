# P0-024 Summary — Caddy Reverse Proxy

**Date**: 2026-05-31
**Step**: P0-024
**ADR**: ADR-014 (VPS/Container Architecture), ADR-019 (VPN Mesh)

## What Was Done
Installed Caddy 2.11.3 via Cloudsmith official apt repo, created Caddyfile with 3 TLS sites for future backend services (FastAPI, Grafana, Prometheus). TLS internal (self-signed). Binds Tailscale IP (100.94.104.22) and localhost. Service running under guinevere.slice resource limits.

## Runtime Changes (VPS)
- `/etc/apt/sources.list.d/caddy-stable.list` — Cloudsmith repo
- `/etc/caddy/Caddyfile` — 3-site config with TLS internal
- `/etc/systemd/system/caddy.service.d/guinevere-slice.conf` — slice override

## Configuration Details
| Site | Listen | Proxy To | TLS |
|---|---|---|---|
| FastAPI | 100.94.104.22:8443 | localhost:8000 | internal |
| Grafana | 100.94.104.22:3443 | localhost:3000 | internal |
| Prometheus | 127.0.0.1:9443 | localhost:9090 | internal |

## Caveats
- Backends (FastAPI, Grafana, Prometheus) not running yet — expected at P0 phase
- TLS internal = self-signed, browser will warn
- auto_https disabled because port 80 is Aizanta nginx
- Prometheus bound to localhost only (no Tailscale — intentional)