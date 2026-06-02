# STEP-P0-006 Coexistence Proof

Date: 2026-05-31

## Existing Security Stack

Before P0-006, P0-004 and P0-005 had already established:

- UFW active with default deny incoming / allow outgoing / deny routed.
- SSH `22/tcp` allowed.
- Tailscale `41641/udp` allowed.
- fail2ban active with UFW action and `sshd` jail.
- Aizanta containers healthy and protected ports unchanged.

## After CrowdSec

CrowdSec added:

- `crowdsec` package `1.7.8`.
- `crowdsec-firewall-bouncer-nftables` package `0.0.34`.
- CrowdSec local API on `127.0.0.1:8080`.
- nftables tables `ip crowdsec` and `ip6 crowdsec6`.
- CrowdSec allowlist `guinevere-trusted` with localhost, VPS Tailscale IP, and Samm/operator Tailscale IP.
- CAPI decisions pulled from CrowdSec community blocklist.

## Coexistence Checks

Commands:

```bash
systemctl is-active crowdsec
systemctl is-active crowdsec-firewall-bouncer
ssh -o BatchMode=yes -o ConnectTimeout=10 guinevere-vps "whoami && hostname"
docker ps --format '{{.Names}} {{.Status}} {{.Ports}}' | grep aizanta
ss -tlnp | grep -E '5432|6379|80'
cscli decisions list --ip 192.0.2.1
```

Outputs:

```text
crowdsec: active
crowdsec-firewall-bouncer: active
ssh guinevere-vps: guinevere / faiz-prod-01
Aizanta containers: all Up 7 days (healthy)
Protected ports: 127.0.0.1:6379, 100.94.104.22:80, 127.0.0.1:5432 unchanged
TEST-NET decision cleanup: No active decisions
```

## Notes

- CrowdSec and fail2ban now run in parallel. This is intentional for defense-in-depth.
- fail2ban writes UFW deny rules; CrowdSec bouncer writes nftables sets/chains. These are separate mechanisms.
- Docker/UFW bypass caveat remains a shared-VPS architectural consideration from P0-004. P0-006 did not modify Docker networking.
