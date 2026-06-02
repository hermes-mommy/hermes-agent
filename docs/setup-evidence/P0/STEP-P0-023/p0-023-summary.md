# STEP-P0-023 Summary — Cloudflare Tunnel Setup

Date: 2026-05-31
Status: Complete, pending auditor gate

## What Was Done

P0-023 was originally blocked by browser authentication. Faiz completed the Cloudflare browser login and selected the `mypapyr.com` zone. After that, the tunnel was created and deployed.

## Runtime Changes

- Installed `cloudflared` v2026.5.2 via APT
- Created tunnel `guinevere-webhook`
- Tunnel ID: `47d1c79b-e0e0-4562-95dd-93d91e62590b`
- Routed DNS: `discord-webhook.mypapyr.com`
- Created config: `/home/guinevere/config/cloudflared/config.yml`
- Created systemd unit: `/etc/systemd/system/cloudflared.service`
- Service runs as `guinevere:guinevere` in `guinevere.slice`
- Strict ingress only allows webhook paths:
  - `/webhook/discord*`
  - `/discord/webhook*`
  - all other paths return 404

## Validation

- `cloudflared --version` -> 2026.5.2
- `systemctl is-active cloudflared` -> active
- `cloudflared tunnel list` -> `guinevere-webhook` active with 4 edge connections
- DNS resolves for `discord-webhook.mypapyr.com`
- Allowed webhook path returns 502 because backend on localhost:8000 is not deployed yet (expected)
- Non-allowed path returns 404 (strict ingress verified)
- Aizanta 5/5 healthy

## Caveat

The tunnel is live, but the origin backend service on `localhost:8000` does not exist yet. The public webhook route therefore returns HTTP 502 until the future Discord webhook receiver is deployed. This is expected and documented.

## Rollback

```bash
sudo systemctl stop cloudflared
sudo systemctl disable cloudflared
sudo rm -f /etc/systemd/system/cloudflared.service
sudo systemctl daemon-reload
sudo -u guinevere cloudflared tunnel route dns delete guinevere-webhook discord-webhook.mypapyr.com
sudo -u guinevere cloudflared tunnel delete guinevere-webhook
sudo apt purge -y cloudflared
```
