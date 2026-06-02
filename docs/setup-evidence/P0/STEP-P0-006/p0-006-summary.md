# STEP-P0-006 Summary — CrowdSec Setup

Date: 2026-05-31
Implementer: Hephaestus / Guinevere workflow

## Summary

STEP-P0-006 installed and configured CrowdSec on the shared VPS for community-driven threat detection and collaborative IP reputation. The implementation used the current CrowdSec packagecloud repository, installed CrowdSec engine `1.7.8`, enabled core Linux/SSH/nginx content, created a trusted CrowdSec allowlist before bouncer enablement, and installed the official nftables firewall bouncer.

The StepPrompts draft referenced `crowdsec-firewall-bouncer-ufw`, but live package resolution and external research confirmed that package does not exist. The host uses `iptables v1.8.10 (nf_tables)` and `nftables v1.0.9`, so the correct low-risk remediation component for Ubuntu 24.04 is `crowdsec-firewall-bouncer-nftables`.

## Runtime Changes

- Added CrowdSec packagecloud apt source via `https://install.crowdsec.net`.
- Installed `crowdsec` package `1.7.8`.
- Installed `crowdsec-firewall-bouncer-nftables` package `0.0.34`.
- Enabled/started `crowdsec.service`.
- Enabled/started `crowdsec-firewall-bouncer.service`.
- Created CrowdSec allowlist `guinevere-trusted` containing:
  - `127.0.0.1/8`
  - `::1`
  - `100.94.104.22`
  - `100.112.201.124`
- Installed/enabled CrowdSec collections:
  - `crowdsecurity/linux`
  - `crowdsecurity/sshd`
  - `crowdsecurity/nginx`
  - `crowdsecurity/whitelist-good-actors`

## Files Changed Locally

Evidence files under `docs/setup-evidence/P0/STEP-P0-006/`:

- `crowdsec-status.txt`
- `crowdsec-collections.txt`
- `crowdsec-whitelist-proof.txt`
- `crowdsec-bouncer-proof.txt`
- `crowdsec-test.log`
- `aizanta-post-check.md`
- `coexistence-proof.md`
- `p0-006-summary.md`
- `verification.md`

Tracker/doc sync after verification:

- `PROGRESS.md`
- `CHECKLIST.md`
- `stepprompts/StepPrompts.md`

## Security Decisions

- The bouncer API key was generated on the VPS and not copied into repository evidence.
- Samm/operator Tailscale IP and VPS Tailscale IP were allowlisted before bouncer validation.
- Safe TEST-NET IP `192.0.2.1` was used for remediation testing.
- No test ban was performed against Samm/operator IP or VPS IP.
- Nginx collection was installed, but no fake host nginx acquisition was created because Aizanta nginx runs in Docker and `/var/log/nginx` is absent on host.

## Validation Highlights

- CrowdSec service active.
- Firewall bouncer service active.
- Bouncer listed as valid and polling local API.
- CAPI status confirms community blocklist pulling is enabled.
- CAPI decisions are present from community sources.
- TEST-NET decision entered nftables set and was removed cleanly.
- SSH remained accessible.
- Aizanta containers remained healthy.
- Protected Aizanta ports remained unchanged.

## Caveats

- Console-selected premium/extra blocklists require CrowdSec Console enrollment and UI selection. The free CAPI community blocklist pull is active without extra operator action.
- Docker/UFW bypass considerations remain architectural caveats; P0-006 did not change Docker networking.
- CrowdSec nginx collection is installed but not actively acquiring host nginx logs because no host nginx logs exist.

## Rollback

Preferred rollback sequence:

```bash
sudo systemctl stop crowdsec-firewall-bouncer
sudo apt purge -y crowdsec-firewall-bouncer-nftables
sudo systemctl stop crowdsec
sudo apt purge -y crowdsec
sudo rm -rf /etc/crowdsec /var/lib/crowdsec /var/log/crowdsec.log
sudo nft list tables | grep crowdsec || true
ssh guinevere-vps "whoami && hostname"
```

Rollback must be followed by Aizanta container/port checks.
