# P0-022 Summary — Tailscale VPN Mesh Configuration

**Date**: 2026-05-31
**Step**: P0-022
**ADR**: ADR-019 (Zero Public Ports)

## What Was Done
Verified Tailscale is running (v1.98.3), connected, and operational on faiz-prod-01. VPS tailscale IP: 100.94.104.22. Operator device (faizzzzz, 100.112.201.124) is active with direct connection (17ms). MagicDNS (tail05ac84.ts.net) is working. Created ACL policy file with grants + SSH rules + auto-approvers. ACL policy application requires Tailscale admin console — Faiz must apply manually.

## Runtime State
- Tailscale 1.98.3, systemd-managed, auto-starts
- UFW allows 41641/udp (added in P0-004)
- 7 tailnet devices, operator on direct connection
- No current ACL restrictions (default: everything allowed)
- Tags pending: tag:service needs admin console approval

## Files Created
- `docs/setup-evidence/P0/STEP-P0-022/tailscale-acl-policy.jsonc` — ACL policy (grants + SSH + auto-approvers)
- `docs/setup-evidence/P0/STEP-P0-022/tailscale-status.txt` — live state verification

## ADR Compliance
- ADR-019: Zero public ports maintained. Tailscale mesh active for internal admin/services
- ACL policy enforces group:admin full access, tag:service service-to-service only
- SSH over Tailscale configured in ACL grants + SSH rules

## Caveats
- ACL policy is prepared but NOT applied — requires Faiz to paste into admin console
- Device tags pending admin approval
- Tailscale SSH not yet enabled (needs `tailscale set --ssh` after tagging)
- Auth key expiry: headless VPS uses user auth (fazulfi@github), no auth key yet