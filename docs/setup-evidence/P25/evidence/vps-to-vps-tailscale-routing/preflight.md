# P25 — VPS-to-VPS Tailscale Routing: Preflight

**Date:** 2026-06-27 ~13:30 WIB
**Status:** COMPLETE — Root cause identified.

---

## Source: ninerouter-vps (49.12.82.34:39999)

| Check | Result |
|---|---|
| `hostname` | `ninerouter-vps` |
| `tailscale status` | Both VPSs visible: `100.104.210.75` (vps-9router) and `100.94.104.22` (faiz-prod-01) |
| `tailscale ip -4` | `100.104.210.75` |
| `ip route get 100.94.104.22` | `dev venet0 src 10.35.0.168` — **WRONG**. Should be via `tailscale0`. |
| `ip route show table all` | No Tailscale routes. No `100.64.0.0/10` entry. No `tailscale0` interface anywhere. |
| `ip rule show` | Default rules only (local/main/default). No Tailscale policy rules. |
| `systemctl status tailscaled` | Running since 2026-06-26 15:37 WIB. **Uses `--tun=userspace-networking`** (hardcoded in `/usr/lib/systemd/system/tailscaled.service`). |
| `tailscale netcheck` | UDP works, IPv4/public IP good. Direct connections possible. |
| `ufw status` | **Not installed.** No local firewall. |
| `/dev/net/tun` | Exists (`crw-rw-rw-`). Kernel TUN support available. |
| curl to target | `curl http://100.94.104.22:20128/v1/models` — **TIMEOUT** |
| `tailscaled` logs | Shows `client -> backend close connection` messages for 20128 traffic to/from 100.112.201.124 (local laptop) — 9Router service running locally on 20128. |

## Target: guinevere-vps (faiz-prod-01 / 100.94.104.22)

| Check | Result |
|---|---|
| `hostname` | `faiz-prod-01` |
| `tailscale status` | Both VPSs visible. `100.104.210.75` (vps-9router) status `-` (no direct conn) |
| `ss -ltnp \| grep 20128` | `LISTEN 0 511 0.0.0.0:20128` — PID `next-server (v1`, pid 3296938 |
| `curl localhost:20128/v1/models` | **OK** — 64 models listed |
| `ufw status verbose` | Default deny. Only 22/tcp + 41641/udp allowed. No explicit 20128 rule. |
| `iptables ts-input` | **Rule 2:** `ACCEPT all -- tailscale0 * 0.0.0.0/0 0.0.0.0/0` (ACCEPTS all from tailscale0 BEFORE UFW).
**Rule 5:** `DROP all -- !tailscale0 * 100.64.0.0/10 0.0.0.0/0` (drops CGNAT from non-tailscale). |
| `systemctl status tailscaled` | Running since 2026-05-23. Kernel TUN mode (no `--tun=userspace-networking`). |
| `tailscale ip -4` | `100.94.104.22` |

## Root Cause Classification

**PRIMARY: Type A — Route issue on ninerouter-vps.**
`tailscaled` runs with `--tun=userspace-networking` hardcoded in the systemd unit. In this mode, no kernel TUN interface is created, and no Tailscale CGNAT routes are added to the routing table. Traffic to `100.94.104.22` falls through to the default route (`venet0`), which cannot route CGNAT space → timeout.

**SECONDARY: No firewall issue on guinevere-vps.**
The `ts-input` chain in iptables ACCEPTs all traffic from `tailscale0` before UFW is evaluated. If ninerouter-vps correctly routed via tailscale0, guinevere-vps would accept the connection on any port including 20128. No UFW change needed.

## Fix Required

Switch ninerouter-vps `tailscaled` from userspace-networking mode to kernel TUN mode:

1. Create systemd drop-in override to remove `--tun=userspace-networking` flag.
2. `systemctl daemon-reload`
3. `systemctl restart tailscaled`
4. Verify `tailscale0` interface appears + correct routes.
5. Verify `curl http://100.94.104.22:20128/v1/models` succeeds.

## Hard Rejection Criteria

- ❌ Firewall disabled/reset/flushed on either VPS.
- ❌ SSH rule changed on either VPS.
- ❌ Port 20128 exposed to public internet.
- ❌ Route still via `venet0` after fix.
- ❌ `curl` fails from ninerouter-vps.

---

*Preflight complete — proceeding to fix plan.*
