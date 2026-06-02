# STEP-P0-004 Verification — UFW Firewall Rules

Date: 2026-05-31
Step: P0-004
Host: faiz-prod-01 / 100.94.104.22
Status: PASS, independent auditor gate passed

## 1. What Was Done

Configured the shared VPS firewall posture for P0-004 using a preserve-and-tighten approach.

The VPS already had UFW enabled with the correct default posture:

- deny incoming
- allow outgoing
- deny routed
- SSH `22/tcp` allowed

The destructive `ufw --force reset` command from the generic draft command block was intentionally not used because this is a shared VPS with live Aizanta services and active SSH recovery constraints.

The only missing rule was added:

```bash
sudo ufw allow 41641/udp comment 'Tailscale'
```

This completed the intended P0-004 firewall shape while preserving SSH access and Aizanta runtime state.

## 2. Files Changed

Repository evidence files created:

- `docs/setup-evidence/P0/STEP-P0-004/ufw-status.txt`
- `docs/setup-evidence/P0/STEP-P0-004/aizanta-post-check.md`
- `docs/setup-evidence/P0/STEP-P0-004/port-scan.txt`
- `docs/setup-evidence/P0/STEP-P0-004/nmap-scan.png`
- `docs/setup-evidence/P0/STEP-P0-004/p0-004-summary.md`
- `docs/setup-evidence/P0/STEP-P0-004/verification.md`

Tracker files synced after runtime verification:

- `PROGRESS.md`
- `CHECKLIST.md`
- `stepprompts/StepPrompts.md`

VPS runtime state changed:

- Added UFW rule: `41641/udp ALLOW IN Anywhere # Tailscale`
- Added UFW IPv6 rule: `41641/udp (v6) ALLOW IN Anywhere (v6) # Tailscale`

VPS runtime state intentionally preserved:

- Existing SSH rule `22/tcp ALLOW IN Anywhere # SSH key-only`
- UFW default policies
- Aizanta containers and ports
- Docker networks
- PostgreSQL/Redis bindings
- `/home/aizanta/`

## 3. Validation Results

### 3.1 Baseline UFW State

Command:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "sudo ufw status verbose && sudo ufw status numbered && tailscale version && ip -brief addr show tailscale0"
```

Output:

```text
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), deny (routed)
New profiles: skip

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    Anywhere                   # SSH key-only
22/tcp (v6)                ALLOW IN    Anywhere (v6)              # SSH key-only

Status: active

     To                         Action      From
     --                         ------      ----
[ 1] 22/tcp                     ALLOW IN    Anywhere                   # SSH key-only
[ 2] 22/tcp (v6)                ALLOW IN    Anywhere (v6)              # SSH key-only

1.98.3
  tailscale commit: a16e0f20cff0acd5617fd1b315df32cdad17a8fa
  long version: 1.98.3-ta16e0f20c-ge0c644472
  other commit: e0c6444725a27ff911a18cc4b18575d8700339d5
  go version: go1.26.3 (tailscale/go e877d97384)
tailscale0       UNKNOWN        100.94.104.22/32 fd7a:115c:a1e0::8f3b:6816/128 fe80::379f:c94c:3695:af1/64
```

### 3.2 Aizanta Guardrail Before Firewall Change

Command:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "docker ps --format '{{.Names}} {{.Status}} {{.Ports}}' | grep aizanta"
```

Output:

```text
aizanta-bot Up 7 days (healthy) 8000/tcp
aizanta-nginx Up 7 days (healthy) 100.94.104.22:80->80/tcp
aizanta-frontend Up 7 days (healthy) 3000/tcp
aizanta-postgres Up 7 days (healthy) 127.0.0.1:5432->5432/tcp
aizanta-redis Up 7 days (healthy) 127.0.0.1:6379->6379/tcp
```

Command:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "ss -tlnp | grep -E '5432|6379|80'"
```

Output:

```text
LISTEN 0      4096                     127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=52688,fd=8))
LISTEN 0      4096                 100.94.104.22:80         0.0.0.0:*    users:(("docker-proxy",pid=235002,fd=8))
LISTEN 0      4096                     127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=52721,fd=8))
```

### 3.3 SSH Guardrail Before Firewall Change

Command:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 guinevere-vps "whoami && hostname"
```

Output:

```text
guinevere
faiz-prod-01
```

### 3.4 Dry-Run Before Applying Rule

Command:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "sudo ufw --dry-run allow 41641/udp comment 'Tailscale'"
```

Relevant output excerpt:

```text
### tuple ### allow tcp 22 0.0.0.0/0 any 0.0.0.0/0 in comment=535348206b65792d6f6e6c79
-A ufw-user-input -p tcp --dport 22 -j ACCEPT

### tuple ### allow udp 41641 0.0.0.0/0 any 0.0.0.0/0 in comment=5461696c7363616c65
-A ufw-user-input -p udp --dport 41641 -j ACCEPT

### tuple ### allow tcp 22 ::/0 any ::/0 in comment=535348206b65792d6f6e6c79
-A ufw6-user-input -p tcp --dport 22 -j ACCEPT

### tuple ### allow udp 41641 ::/0 any ::/0 in comment=5461696c7363616c65
-A ufw6-user-input -p udp --dport 41641 -j ACCEPT

Result:
Rules updated
Rules updated (v6)
```

Interpretation: this was UFW dry-run output showing the resulting generated rules. The actual state was applied only in the next command.

### 3.5 Applied Firewall Rule

Command:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "sudo ufw allow 41641/udp comment 'Tailscale'"
```

Output:

```text
Rule added
Rule added (v6)
```

### 3.6 SSH Verification After Firewall Change

Command:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 guinevere-vps "echo 'SSH still works' && whoami && hostname"
```

Output:

```text
SSH still works
guinevere
faiz-prod-01
```

### 3.7 Final UFW State

Command:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "sudo ufw status verbose && sudo ufw status numbered"
```

Output:

```text
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), deny (routed)
New profiles: skip

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    Anywhere                   # SSH key-only
41641/udp                  ALLOW IN    Anywhere                   # Tailscale
22/tcp (v6)                ALLOW IN    Anywhere (v6)              # SSH key-only
41641/udp (v6)             ALLOW IN    Anywhere (v6)              # Tailscale

Status: active

     To                         Action      From
     --                         ------      ----
[ 1] 22/tcp                     ALLOW IN    Anywhere                   # SSH key-only
[ 2] 41641/udp                  ALLOW IN    Anywhere                   # Tailscale
[ 3] 22/tcp (v6)                ALLOW IN    Anywhere (v6)              # SSH key-only
[ 4] 41641/udp (v6)             ALLOW IN    Anywhere (v6)              # Tailscale
```

Command:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "sudo ufw show added"
```

Output:

```text
Added user rules (see 'ufw status' for running firewall):
ufw allow 22/tcp comment 'SSH key-only'
ufw allow 41641/udp comment 'Tailscale'
```

### 3.8 Port Probe Fallback

`nmap` was unavailable locally:

```text
nmap : The term 'nmap' is not recognized as the name of a cmdlet, function, script file, or operable program.
```

Fallback checks used `Test-NetConnection` from the Windows workstation over Tailscale.

SSH expected reachable:

```text
ComputerName     : 100.94.104.22
RemoteAddress    : 100.94.104.22
RemotePort       : 22
InterfaceAlias   : Tailscale
SourceAddress    : 100.112.201.124
TcpTestSucceeded : True
```

Guinevere PostgreSQL target port expected blocked/closed:

```text
ComputerName           : 100.94.104.22
RemoteAddress          : 100.94.104.22
RemotePort             : 5433
InterfaceAlias         : Tailscale
SourceAddress          : 100.112.201.124
PingSucceeded          : True
PingReplyDetails (RTT) : 17 ms
TcpTestSucceeded       : False
```

Guinevere Redis target port expected blocked/closed:

```text
ComputerName           : 100.94.104.22
RemoteAddress          : 100.94.104.22
RemotePort             : 6380
InterfaceAlias         : Tailscale
SourceAddress          : 100.112.201.124
PingSucceeded          : True
PingReplyDetails (RTT) : 17 ms
TcpTestSucceeded       : False
```

Tailscale UDP caveat:

```text
ComputerName           : 100.94.104.22
RemoteAddress          : 100.94.104.22
RemotePort             : 41641
InterfaceAlias         : Tailscale
SourceAddress          : 100.112.201.124
PingSucceeded          : True
PingReplyDetails (RTT) : 17 ms
TcpTestSucceeded       : False
```

This is expected because the fallback checks TCP, while Tailscale direct connections use UDP 41641.

### 3.9 Aizanta Guardrail After Firewall Change

Command:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "docker ps --format '{{.Names}} {{.Status}} {{.Ports}}' | grep aizanta"
```

Output:

```text
aizanta-bot Up 7 days (healthy) 8000/tcp
aizanta-nginx Up 7 days (healthy) 100.94.104.22:80->80/tcp
aizanta-frontend Up 7 days (healthy) 3000/tcp
aizanta-postgres Up 7 days (healthy) 127.0.0.1:5432->5432/tcp
aizanta-redis Up 7 days (healthy) 127.0.0.1:6379->6379/tcp
```

Command:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "ss -tlnp | grep -E '5432|6379|80'"
```

Output:

```text
LISTEN 0      4096                     127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=52688,fd=8))
LISTEN 0      4096                 100.94.104.22:80         0.0.0.0:*    users:(("docker-proxy",pid=235002,fd=8))
LISTEN 0      4096                     127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=52721,fd=8))
```

Aizanta HTTP check:

```text
HTTP/1.1 200 OK
Server: nginx
Content-Type: text/html; charset=utf-8
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-Request-ID: 248e76db8505cfa67b9964c39d1dbf0a
```

## 4. Evidence Artifacts

- `docs/setup-evidence/P0/STEP-P0-004/ufw-status.txt` — baseline, dry-run, applied rule, final UFW state, `ufw show added`.
- `docs/setup-evidence/P0/STEP-P0-004/aizanta-post-check.md` — Aizanta container/port/HTTP verification before and after.
- `docs/setup-evidence/P0/STEP-P0-004/port-scan.txt` — `nmap` unavailable proof and deterministic fallback port checks.
- `docs/setup-evidence/P0/STEP-P0-004/nmap-scan.png` — screenshot-style artifact documenting the fallback scan, explicitly not claiming real nmap output.
- `docs/setup-evidence/P0/STEP-P0-004/p0-004-summary.md` — implementation summary and rollback.
- `audit-reports/P0/STEP-P0-004/internal-context-report.md` — internal P0-004 context research.
- `audit-reports/P0/STEP-P0-004/evidence-pattern-report.md` — evidence/status sync pattern research.
- `audit-reports/P0/STEP-P0-004/external-ufw-safety-report.md` — external UFW lockout/shared-VPS safety research.
- `audit-reports/P0/STEP-P0-004/external-tailscale-ufw-report.md` — external Tailscale/UFW research.

## 5. Shared VPS Impact

PASS — no Aizanta disruption observed.

Shared VPS guardrails were checked before and after the UFW change:

- Aizanta containers remained healthy.
- Protected ports stayed unchanged:
  - `127.0.0.1:5432` PostgreSQL
  - `127.0.0.1:6379` Redis
  - `100.94.104.22:80` nginx
- SSH remained reachable.
- No Aizanta Docker networks, volumes, databases, Redis DBs, nginx config, or `/home/aizanta/` were touched.

The only runtime modification was an additive UFW rule for UDP `41641`.

## 6. ADR Compliance

- ADR-014 (VPS/container architecture): preserved shared VPS isolation and did not touch Aizanta services.
- ADR-018 (Security Architecture & Defense-in-Depth): maintained deny-by-default inbound firewall posture and added explicit Tailscale UDP allowance.
- ADR-019 (Access Control & VPN Mesh Strategy): supports Tailscale direct connections and future zero-public-admin-surface hardening while preserving transitional SSH recovery.
- ADR-030 (Redis DB assignments): no Redis state changed; Guinevere DB0-DB5 and Aizanta DBs untouched.
- ADR-031 (Database naming): no database state changed; `guinevere` DB naming unaffected.

## 7. AC Reference

- AC-CORE-002: supports infrastructure baseline by enforcing host firewall posture for future services.
- AC-SEC-001: host firewall active with only SSH and Tailscale allowed for inbound UFW user rules; Guinevere database/cache target ports are not reachable from the workstation probe.

## 8. Rollback / Re-run Safety

The implementation is idempotent and additive. Re-running the same UFW command now returns an existing-rule skip:

```text
Skipping adding existing rule
Skipping adding existing rule (v6)
```

Rollback for the additive rule:

```bash
sudo ufw delete allow 41641/udp
sudo ufw status verbose
ssh guinevere-vps "echo ok"
```

Do not use broad `ufw reset` on this shared VPS unless an out-of-band console recovery path is active and Aizanta impact has been explicitly accepted.

## 9. Design Decisions / Caveats

### Preserve-and-tighten instead of reset

The step prompt contained a generic `sudo ufw --force reset` command, but live state already had UFW active with default deny incoming and SSH allowed. Resetting would create unnecessary shared-VPS and SSH-lockout risk.

The chosen approach preserved the existing good state and added only the missing Tailscale UDP rule.

### Nmap fallback

`nmap` is not installed locally. The required screenshot artifact is present as a screenshot-style PNG documenting fallback results, but it is not represented as a real `nmap` scan. The authoritative text evidence is `port-scan.txt`.

### Docker/UFW caveat

Docker-published ports can bypass normal UFW INPUT-chain expectations. Aizanta nginx remains bound to `100.94.104.22:80` as pre-existing shared-VPS state. This was not modified in P0-004 because the task requires preserving Aizanta.

### Transitional SSH exposure

SSH `22/tcp` remains allowed publicly as required by P0-004. ADR-019 target state expects later tightening toward Tailscale-only administrative access.

## 10. Evidence Gate

Parent verification status: PASS.

Independent auditor gate: PASS.

Auditor report path:

- `audit-reports/P0/STEP-P0-004/step-p0-004-auditor-report.md`

Auditor summary:

- Live UFW state matched the intended posture: active, deny incoming, allow outgoing, deny routed.
- Only SSH `22/tcp` and Tailscale `41641/udp` user rules were present, including IPv6 equivalents.
- SSH still worked through `guinevere-vps`.
- Aizanta containers remained healthy and protected ports stayed unchanged.
- Evidence files and research reports existed.
- Trackers were synced.
- No secrets were found in P0-004 evidence.
- LSP diagnostics were clean.

Auditor non-blocking caveat resolved after PASS:

- `stepprompts/StepPrompts.md` rollback guidance was updated from the generic broad reset pattern to the safer additive rollback path: `sudo ufw delete allow 41641/udp` followed by UFW and SSH verification.

## 11. Footer

Source task: STEP-P0-004
Date: 2026-05-31
Implementer: Hephaestus / Guinevere operating workflow
Validation method: live SSH/UFW checks, dry-run proof, Aizanta guardrails, fallback port probes, evidence artifacts, parent verification, independent auditor gate
