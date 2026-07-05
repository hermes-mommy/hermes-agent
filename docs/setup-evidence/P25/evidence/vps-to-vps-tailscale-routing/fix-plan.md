# P25 — VPS-to-VPS Tailscale Routing: Fix Plan

**Date:** 2026-06-27 ~13:40 WIB
**Status:** READY FOR IMPLEMENTATION

---

## Diagnosis Summary

- **Root cause:** `tailscaled` on ninerouter-vps runs with `--tun=userspace-networking` hardcoded in systemd unit.
- **Effect:** No kernel `tailscale0` interface, no Tailscale CGNAT routes in routing table.
- **Verdict:** Type A (route issue). No firewall fix needed on guinevere-vps.

## Fix: Switch to Kernel TUN Mode

### Step 1: Create systemd drop-in override

`/etc/systemd/system/tailscaled.service.d/override.conf`

```ini
[Service]
# Replace existing ExecStart (which includes --tun=userspace-networking)
# with kernel TUN mode (no --tun flag, defaults to kernel TUN).
ExecStart=
ExecStart=/usr/sbin/tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/run/tailscale/tailscaled.sock --port=41641 $FLAGS
```

### Step 2: Reload + restart

```bash
systemctl daemon-reload
systemctl restart tailscaled
```

### Step 3: Verify

```bash
# Kernel TUN interface exists
ip link show tailscale0

# Routes include CGNAT
ip route get 100.94.104.22
# Expected: dev tailscale0 or via tailscale0

# Connectivity to 9Router
curl -v http://100.94.104.22:20128/v1/models
# Expected: JSON list of models (not timeout)
```

## Safety

- ✅ No firewall touched (UFW not even installed on ninerouter-vps).
- ✅ No SSH rule changed.
- ✅ Port 20128 not exposed to public internet (never added to firewall, service only listens on 0.0.0.0:20128 but firewall blocks inbound anyway... wait, no UFW on ninerouter. But 9Router is running ON ninerouter itself — port 20128 is for the local 9Router service. The target is guinevere-vps:20128.)
- ✅ Service restart is `tailscaled` only, not 9Router or any other service.
- ✅ No secrets printed.

## Rollback

```bash
rm /etc/systemd/system/tailscaled.service.d/override.conf
systemctl daemon-reload
systemctl restart tailscaled
```

## Hard Rejection Criteria

- ❌ Firewall disabled/reset/flushed — PASS (no firewall change).
- ❌ SSH rule removed/changed — PASS (no SSH change).
- ❌ Public 20128 exposed — PASS.
- ❌ Claim fixed without curl succeeding — VERIFY.
- ❌ Route still via venet0 — VERIFY.
- ❌ Secret printed — PASS.
- ❌ Unrelated services restarted — PASS (only tailscaled).

---

*Ready to execute.*
