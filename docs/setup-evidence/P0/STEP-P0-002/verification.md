# STEP-P0-002 Verification — SSH Config Update

**Step:** P0-002 — SSH Config Update  
**Date:** 2026-05-31  
**Implementer:** Hephaestus / Guinevere orchestration  
**Evidence root:** `docs/setup-evidence/P0/STEP-P0-002/`  
**Status:** PASS, independent auditor gate passed

## What Was Done

- Confirmed the local Ed25519 SSH key exists and fingerprinted it.
- Discovered the VPS access endpoint from prior P0 evidence: `100.94.104.22` (`faiz-prod-01`).
- Verified pre-change Aizanta container and protected-port health.
- Diagnosed two blockers:
  - `guinevere` was not in the existing SSH `AllowUsers` list.
  - `/home/guinevere/.ssh/authorized_keys` contained malformed key data after a PowerShell pipe attempt.
- Created a rollback backup of the existing SSH hardening drop-in before editing it.
- Added `guinevere` to the existing `AllowUsers root aizanta` directive without removing Aizanta or root break-glass access.
- Repaired `/home/guinevere/.ssh/authorized_keys` with the correct single-line Ed25519 public key and secure ownership/mode.
- Validated `sshd -t` and reloaded the Ubuntu `ssh` service.
- Added local Windows OpenSSH alias `guinevere-vps` to `C:\Users\faizz\.ssh\config`.
- Repaired local SSH config ACLs after Windows OpenSSH rejected a stale inherited unknown SID.
- Verified both direct and alias SSH login as `guinevere` without a password prompt.
- Re-verified Aizanta remained healthy after the SSH changes.

## Files Changed

### Local machine

- `C:\Users\faizz\.ssh\config` — added `Host guinevere-vps`; tightened ACLs so Windows OpenSSH accepts the config.
- `PROGRESS.md` — marked P0-002 complete and updated counters from 2/257 to 3/257, P0 2/29 to 3/29.
- `CHECKLIST.md` — marked SSH key-based authentication and P0-002 verification complete.
- `stepprompts/StepPrompts.md` — marked P0-002 status, pre-flight, and verification checkboxes complete.
- `docs/setup-evidence/P0/STEP-P0-002/ssh-test.log`
- `docs/setup-evidence/P0/STEP-P0-002/ssh-config.txt`
- `docs/setup-evidence/P0/STEP-P0-002/aizanta-post-check.md`
- `docs/setup-evidence/P0/STEP-P0-002/ssh-hardening-summary.md`
- `docs/setup-evidence/P0/STEP-P0-002/p0-002-summary.md`
- `docs/setup-evidence/P0/STEP-P0-002/verification.md`

### VPS

- `/home/guinevere/.ssh/authorized_keys` — replaced malformed key content with the correct Ed25519 public key.
- `/etc/ssh/sshd_config.d/99-aizanta-hardening.conf` — changed `AllowUsers root aizanta` to `AllowUsers root aizanta guinevere`.
- `/etc/ssh/sshd_config.d/99-aizanta-hardening.conf.pre-p0-002` — rollback backup created before editing the SSH drop-in.

## Validation Results

### Local SSH key exists and is Ed25519

Command:

```powershell
Test-Path "$env:USERPROFILE\.ssh\id_ed25519.pub"
ssh-keygen -lf "$env:USERPROFILE\.ssh\id_ed25519.pub"
```

Output:

```text
True
256 SHA256:HxrFdsBqqwbRptgUEiDcGfQlErtYY7yANR1NvRtkI5k fazulfi@github (ED25519)
```

### Local OpenSSH client version

Command:

```powershell
ssh -V
```

Output:

```text
OpenSSH_for_Windows_9.5p2, LibreSSL 3.8.2
```

### Pre-action Aizanta container health

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

### Pre-action protected port check

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

### SSH configuration syntax and rollback backup

Command:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "sudo test -f /etc/ssh/sshd_config.d/99-aizanta-hardening.conf.pre-p0-002 && echo backup-present && sudo sshd -t && echo sshd-config-valid"
```

Output:

```text
backup-present
sshd-config-valid
```

### Authorized key fingerprint on VPS

Command:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "sudo ssh-keygen -lf /home/guinevere/.ssh/authorized_keys"
```

Output:

```text
256 SHA256:HxrFdsBqqwbRptgUEiDcGfQlErtYY7yANR1NvRtkI5k fazulfi@github (ED25519)
```

### Effective SSH settings for guinevere

Command:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "sudo sshd -T -C user=guinevere,host=faiz-prod-01,addr=100.112.201.124 | grep -E '^(permitrootlogin|pubkeyauthentication|passwordauthentication|kbdinteractiveauthentication|authorizedkeysfile|allowusers|authenticationmethods)'"
```

Output:

```text
permitrootlogin without-password
pubkeyauthentication yes
passwordauthentication no
kbdinteractiveauthentication no
authorizedkeysfile .ssh/authorized_keys .ssh/authorized_keys2
allowusers root
allowusers aizanta
allowusers guinevere
authenticationmethods any
```

Result: password and keyboard-interactive authentication are disabled; public-key auth is enabled; `guinevere` is allowed without removing existing `root` and `aizanta` access.

### Direct guinevere SSH login

Command:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 guinevere@100.94.104.22 "whoami && hostname"
```

Output:

```text
guinevere
faiz-prod-01
```

Result: PASS — direct key-based SSH login works without password prompt.

### Local alias parse

Command:

```powershell
ssh -G guinevere-vps
```

Relevant output:

```text
host guinevere-vps
user guinevere
hostname 100.94.104.22
identitiesonly yes
serveralivecountmax 3
serveraliveinterval 60
identityfile ~/.ssh/id_ed25519
```

### Local alias SSH login

Command:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 guinevere-vps "whoami && hostname"
```

Output:

```text
guinevere
faiz-prod-01
```

Result: PASS — `guinevere-vps` logs in as the isolated Guinevere user without password prompt.

### Final Aizanta container health

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

### Final protected port check

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

## Evidence Artifacts

- `docs/setup-evidence/P0/STEP-P0-002/ssh-test.log`
- `docs/setup-evidence/P0/STEP-P0-002/ssh-config.txt`
- `docs/setup-evidence/P0/STEP-P0-002/aizanta-post-check.md`
- `docs/setup-evidence/P0/STEP-P0-002/ssh-hardening-summary.md`
- `docs/setup-evidence/P0/STEP-P0-002/p0-002-summary.md`
- `audit-reports/P0/STEP-P0-002/internal-context-report.md`
- `audit-reports/P0/STEP-P0-002/evidence-pattern-report.md`
- `audit-reports/P0/STEP-P0-002/external-ssh-hardening-report.md`
- `audit-reports/P0/STEP-P0-002/external-readiness-blockers-report.md`

## Shared VPS Impact (Aizanta Status After)

Aizanta remained healthy after P0-002:

- `aizanta-bot`: up and healthy
- `aizanta-nginx`: up and healthy on `100.94.104.22:80`
- `aizanta-frontend`: up and healthy
- `aizanta-postgres`: up and healthy on `127.0.0.1:5432`
- `aizanta-redis`: up and healthy on `127.0.0.1:6379`

No Aizanta files, Docker networks, databases, Redis DBs, nginx config, or service definitions were changed.

## ADR Compliance

- **ADR-014 / shared VPS isolation:** preserved Aizanta containers and protected ports; changed only Guinevere SSH access plus the shared SSH allowlist needed for the `guinevere` Linux user.
- **ADR-015 / secrets:** no private SSH key, password, token, or credential was written into the repo. Only public key fingerprint and non-secret config evidence are recorded.
- **ADR-019 / access-control and VPN mesh:** implements interim key-based SSH access before P0-022 Tailscale VPN mesh. Password login is disabled; key-based access is enforced.
- **ADR-030 / Redis DB assignments:** no Redis changes.
- **ADR-031 / database naming:** no database changes.
- **Security Policy §13.3:** Ed25519 SSH key used; local SSH config ACL tightened; authorized key fingerprint logged.

## AC Reference

- **AC-SEC-001:** P0-002 contributes to secure access control by enforcing key-based SSH login for the isolated `guinevere` user and preserving password-disabled SSH behavior.

## Rollback / Re-run Safety

### SSH server rollback

Keep root key-based access available while rolling back. Then run:

```bash
sudo cp -a /etc/ssh/sshd_config.d/99-aizanta-hardening.conf.pre-p0-002 /etc/ssh/sshd_config.d/99-aizanta-hardening.conf
sudo sshd -t
sudo systemctl reload ssh
```

### Local alias rollback

Remove this block from `C:\Users\faizz\.ssh\config`:

```sshconfig
Host guinevere-vps
    HostName 100.94.104.22
    User guinevere
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

### Authorized key rollback

Do not delete `/home/guinevere/.ssh/authorized_keys` unless another verified Guinevere access path exists. If necessary after confirming alternate access:

```bash
sudo rm -f /home/guinevere/.ssh/authorized_keys
```

### Re-run safety

- Rewriting the same public key into `/home/guinevere/.ssh/authorized_keys` is idempotent when replacing the file with the same single-line key.
- Re-adding `guinevere` to `AllowUsers` is safe only if the line is checked first to avoid duplicate entries.
- Re-running `sshd -t` and `systemctl reload ssh` is safe after syntax validation.

## Design Decisions / Caveats

- Root SSH was not changed from key-only break-glass access to fully disabled root login because `guinevere` does not yet have permissions to repair or reload SSH. Removing root rollback here would violate the no-lockout safety requirement.
- The existing shared SSH hardening file is named `99-aizanta-hardening.conf`; P0-002 made the minimal required edit there instead of creating a conflicting later drop-in with a duplicate `AllowUsers` directive.
- `AuthenticationMethods` remains `any` because public-key authentication is the only usable method after `PasswordAuthentication no` and `KbdInteractiveAuthentication no`; changing it to `publickey` is deferred to a later SSH hardening step if root rollback and recovery access are redesigned.
- `docs/setup-evidence/README.md` was not updated because it does not exist in the repository.

## Evidence Gate

Parent verification completed:

- Direct SSH as `guinevere`: PASS
- Alias SSH via `guinevere-vps`: PASS
- No password prompt with `BatchMode=yes`: PASS
- SSH server syntax validation: PASS
- SSH rollback backup present: PASS
- Aizanta containers healthy: PASS
- Protected Aizanta ports unchanged: PASS
- Shared trackers synced: PASS

Independent auditor gate: PASS.

- Auditor report: `audit-reports/P0/STEP-P0-002/step-p0-002-auditor-report.md`
- Verdict: PASS
- Non-blocking follow-ups: add `docs/setup-evidence/README.md` when the evidence root matures; re-evaluate `PermitRootLogin` and `AuthenticationMethods` after P0-022/P0-004 establish alternative recovery paths.

## Footer

- **Source task:** STEP-P0-002 full autonomous execution
- **Date:** 2026-05-31
- **Implementer:** Hephaestus / Guinevere orchestration
- **Validation method:** direct SSH tests, `sshd -t`, effective SSH config inspection, Aizanta container/port checks, evidence artifact review
