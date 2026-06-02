# STEP-P0-004 Summary — UFW Firewall Rules

Date: 2026-05-31
Step: P0-004
Host: faiz-prod-01 / 100.94.104.22
Scope: UFW firewall rules for shared VPS

## What Was Done

P0-004 was completed with a preserve-and-tighten approach instead of the destructive reset path in the draft command block.

The VPS already had UFW active with:

- default deny incoming
- default allow outgoing
- default deny routed
- SSH port 22 allowed for key-only access

Because this is a shared VPS and Aizanta is already running, `ufw --force reset` was intentionally not used. Resetting would have increased lockout and service disruption risk without improving the final P0-004 state.

The implemented change was additive only:

```bash
sudo ufw allow 41641/udp comment 'Tailscale'
```

This preserved the existing SSH rule and added the Tailscale direct-connection UDP rule required by the step prompt and later P0/P0-022 expectations.

## Files and Runtime State Changed

Runtime VPS change:

- Added UFW allow rule for UDP `41641` with comment `Tailscale`.
- Preserved existing `22/tcp` SSH allow rule.
- Preserved UFW default policies: deny incoming, allow outgoing, deny routed.
- Did not reset UFW.
- Did not modify Aizanta containers, Docker networks, PostgreSQL, Redis, nginx, or `/home/aizanta/`.

Local evidence files:

- `docs/setup-evidence/P0/STEP-P0-004/ufw-status.txt`
- `docs/setup-evidence/P0/STEP-P0-004/aizanta-post-check.md`
- `docs/setup-evidence/P0/STEP-P0-004/port-scan.txt`
- `docs/setup-evidence/P0/STEP-P0-004/nmap-scan.png`
- `docs/setup-evidence/P0/STEP-P0-004/p0-004-summary.md`
- `docs/setup-evidence/P0/STEP-P0-004/verification.md`

Expected tracker files synced after verification:

- `PROGRESS.md`
- `CHECKLIST.md`
- `stepprompts/StepPrompts.md`

## Verification Summary

Final UFW state:

```text
Status: active
Default: deny (incoming), allow (outgoing), deny (routed)
22/tcp        ALLOW IN    Anywhere       # SSH key-only
41641/udp     ALLOW IN    Anywhere       # Tailscale
22/tcp (v6)   ALLOW IN    Anywhere (v6)  # SSH key-only
41641/udp (v6) ALLOW IN   Anywhere (v6)  # Tailscale
```

SSH remained reachable:

```text
SSH still works
guinevere
faiz-prod-01
```

Aizanta remained healthy:

```text
aizanta-bot Up 7 days (healthy) 8000/tcp
aizanta-nginx Up 7 days (healthy) 100.94.104.22:80->80/tcp
aizanta-frontend Up 7 days (healthy) 3000/tcp
aizanta-postgres Up 7 days (healthy) 127.0.0.1:5432->5432/tcp
aizanta-redis Up 7 days (healthy) 127.0.0.1:6379->6379/tcp
```

Port fallback checks from the Windows workstation over Tailscale:

- TCP 22 reachable: `TcpTestSucceeded : True`
- TCP 5433 not reachable: `TcpTestSucceeded : False`
- TCP 6380 not reachable: `TcpTestSucceeded : False`
- TCP 41641 not reachable, expected because Tailscale direct connections use UDP 41641.

## Design Decision

The main decision was not to run `sudo ufw --force reset`.

Reasoning:

1. UFW was already active and had the correct default deny/allow posture.
2. SSH was already allowed.
3. Resetting UFW remotely risks SSH lockout and shared-service disruption.
4. Aizanta runs on the same VPS and must not be disrupted.
5. The only missing step requirement was the explicit Tailscale UDP 41641 allow rule.

## Caveats

- `nmap` is not installed in the local Windows environment, so `nmap-scan.png` is a screenshot-style artifact documenting the fallback checks, not a real nmap output.
- Docker-published ports can bypass UFW INPUT-chain expectations; Aizanta nginx remains bound to `100.94.104.22:80` as pre-existing shared-VPS state and was not modified.
- Generic public SSH remains allowed for this transitional step. ADR-019 target state is zero public admin surfaces via Tailscale, expected to be tightened in later VPN/access-control steps.

## Rollback

If the P0-004 additive rule must be removed:

```bash
sudo ufw delete allow 41641/udp
sudo ufw status verbose
ssh guinevere-vps "echo ok"
```

Do not run a broad `ufw reset` on this shared VPS unless a console recovery path is active and Aizanta impact is explicitly accepted.

## Footer

Source task: STEP-P0-004
Implementer: Hephaestus / Guinevere operating workflow
Validation method: live SSH/UFW checks, Aizanta Docker checks, fallback port probes, evidence files, parent verification, independent auditor gate
