# STEP-P0-003 Verification — Directory Structure Creation

## What Was Done

Created and verified the canonical Guinevere operational directory tree on the shared VPS for STEP-P0-003. The active StepPrompts tree was followed under `/home/guinevere/`, with `guinevere:guinevere` ownership, `0750` default private group-readable permissions, and `0700` for sensitive `secrets/` and `scripts/` directories.

Implementation used `install -d` for idempotent creation, then a targeted ownership/mode normalization after initial verification found parent directories created with root ownership by nested path creation. That issue was fixed before marking the step complete.

## Files Changed

### VPS paths

- Created/verified `/home/guinevere/code/guinevere`
- Created/verified `/home/guinevere/config/{hermes,9router,mcp,caddy,sops}`
- Created/verified `/home/guinevere/data/{postgres,redis,prometheus,grafana,loki,backups,uploads}`
- Created/verified `/home/guinevere/logs/{guinevere,surveillance,loops}`
- Created/verified `/home/guinevere/backups/{local,s3,r2}`
- Created/verified `/home/guinevere/evidence`
- Created/verified `/home/guinevere/secrets`
- Created/verified `/home/guinevere/scripts`
- Created/verified `/home/guinevere/tmp`
- Created `/etc/systemd/system/guinevere-*.service.d` as the literal placeholder requested by StepPrompts.

### Repository files

- `PROGRESS.md`
- `CHECKLIST.md`
- `stepprompts/StepPrompts.md`
- `docs/setup-evidence/P0/STEP-P0-003/directory-tree.txt`
- `docs/setup-evidence/P0/STEP-P0-003/permissions.txt`
- `docs/setup-evidence/P0/STEP-P0-003/aizanta-post-check.md`
- `docs/setup-evidence/P0/STEP-P0-003/p0-003-summary.md`
- `docs/setup-evidence/P0/STEP-P0-003/verification.md`

## Validation Results

### Pre-flight: Aizanta containers before change

Command:

```bash
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

### Pre-flight: protected ports before change

Command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "ss -tlnp | grep -E '5432|6379|80'"
```

Output:

```text
LISTEN 0      4096                     127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=52688,fd=8))
LISTEN 0      4096                 100.94.104.22:80         0.0.0.0:*    users:(("docker-proxy",pid=235002,fd=8))
LISTEN 0      4096                     127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=52721,fd=8))
```

### Pre-flight: disk and mount options

Command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 guinevere-vps "df -h /home; mount | grep ' / '; mount | grep ' /home ' || true"
```

Output:

```text
Filesystem      Size  Used Avail Use% Mounted on
/dev/vda1        99G  8.7G   85G  10% /
/dev/vda1 on / type ext4 (rw,relatime)
```

Result: PASS. `/home` has at least 60GB free and the root filesystem is not mounted `noexec`.

### Implementation command

Command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "install -d -o guinevere -g guinevere -m 0750 /home/guinevere/code/guinevere /home/guinevere/config/hermes /home/guinevere/config/9router /home/guinevere/config/mcp /home/guinevere/config/caddy /home/guinevere/config/sops /home/guinevere/data/postgres /home/guinevere/data/redis /home/guinevere/data/prometheus /home/guinevere/data/grafana /home/guinevere/data/loki /home/guinevere/data/backups /home/guinevere/data/uploads /home/guinevere/logs/guinevere /home/guinevere/logs/surveillance /home/guinevere/logs/loops /home/guinevere/backups/local /home/guinevere/backups/s3 /home/guinevere/backups/r2 /home/guinevere/evidence /home/guinevere/tmp; install -d -o guinevere -g guinevere -m 0700 /home/guinevere/secrets /home/guinevere/scripts; chmod 750 /home/guinevere; install -d -o root -g root -m 0755 '/etc/systemd/system/guinevere-*.service.d'; find /home/guinevere -type d | sort"
```

Initial verification found root-owned intermediate parent directories (`code`, `config`, `data`, `logs`, `backups`) because nested `install -d` created parents before the final target. This was corrected before completion.

Correction command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "chown -R guinevere:guinevere /home/guinevere/code /home/guinevere/config /home/guinevere/data /home/guinevere/logs /home/guinevere/backups /home/guinevere/evidence /home/guinevere/secrets /home/guinevere/scripts /home/guinevere/tmp; chmod 750 /home/guinevere /home/guinevere/code /home/guinevere/config /home/guinevere/data /home/guinevere/logs /home/guinevere/backups /home/guinevere/evidence /home/guinevere/tmp; chmod 700 /home/guinevere/secrets /home/guinevere/scripts"
```

### Final directory count and tree

Command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "find /home/guinevere -type d | sort; printf 'COUNT='; find /home/guinevere -type d | wc -l"
```

Output:

```text
/home/guinevere
/home/guinevere/backups
/home/guinevere/backups/local
/home/guinevere/backups/r2
/home/guinevere/backups/s3
/home/guinevere/.cache
/home/guinevere/code
/home/guinevere/code/guinevere
/home/guinevere/config
/home/guinevere/config/9router
/home/guinevere/config/caddy
/home/guinevere/config/hermes
/home/guinevere/config/mcp
/home/guinevere/config/sops
/home/guinevere/data
/home/guinevere/data/backups
/home/guinevere/data/grafana
/home/guinevere/data/loki
/home/guinevere/data/postgres
/home/guinevere/data/prometheus
/home/guinevere/data/redis
/home/guinevere/data/uploads
/home/guinevere/evidence
/home/guinevere/logs
/home/guinevere/logs/guinevere
/home/guinevere/logs/loops
/home/guinevere/logs/surveillance
/home/guinevere/scripts
/home/guinevere/secrets
/home/guinevere/.ssh
/home/guinevere/tmp
COUNT=31
```

Result: PASS. Count is >= 25.

### Final ownership and permissions

Command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "stat -c '%U:%G %a %n' /home/guinevere /home/guinevere/code /home/guinevere/code/guinevere /home/guinevere/config /home/guinevere/config/hermes /home/guinevere/config/9router /home/guinevere/config/mcp /home/guinevere/config/caddy /home/guinevere/config/sops /home/guinevere/data /home/guinevere/data/postgres /home/guinevere/data/redis /home/guinevere/data/prometheus /home/guinevere/data/grafana /home/guinevere/data/loki /home/guinevere/data/backups /home/guinevere/data/uploads /home/guinevere/logs /home/guinevere/logs/guinevere /home/guinevere/logs/surveillance /home/guinevere/logs/loops /home/guinevere/backups /home/guinevere/backups/local /home/guinevere/backups/s3 /home/guinevere/backups/r2 /home/guinevere/evidence /home/guinevere/secrets /home/guinevere/scripts /home/guinevere/tmp"
```

Output:

```text
guinevere:guinevere 750 /home/guinevere
guinevere:guinevere 750 /home/guinevere/code
guinevere:guinevere 750 /home/guinevere/code/guinevere
guinevere:guinevere 750 /home/guinevere/config
guinevere:guinevere 750 /home/guinevere/config/hermes
guinevere:guinevere 750 /home/guinevere/config/9router
guinevere:guinevere 750 /home/guinevere/config/mcp
guinevere:guinevere 750 /home/guinevere/config/caddy
guinevere:guinevere 750 /home/guinevere/config/sops
guinevere:guinevere 750 /home/guinevere/data
guinevere:guinevere 750 /home/guinevere/data/postgres
guinevere:guinevere 750 /home/guinevere/data/redis
guinevere:guinevere 750 /home/guinevere/data/prometheus
guinevere:guinevere 750 /home/guinevere/data/grafana
guinevere:guinevere 750 /home/guinevere/data/loki
guinevere:guinevere 750 /home/guinevere/data/backups
guinevere:guinevere 750 /home/guinevere/data/uploads
guinevere:guinevere 750 /home/guinevere/logs
guinevere:guinevere 750 /home/guinevere/logs/guinevere
guinevere:guinevere 750 /home/guinevere/logs/surveillance
guinevere:guinevere 750 /home/guinevere/logs/loops
guinevere:guinevere 750 /home/guinevere/backups
guinevere:guinevere 750 /home/guinevere/backups/local
guinevere:guinevere 750 /home/guinevere/backups/s3
guinevere:guinevere 750 /home/guinevere/backups/r2
guinevere:guinevere 750 /home/guinevere/evidence
guinevere:guinevere 700 /home/guinevere/secrets
guinevere:guinevere 700 /home/guinevere/scripts
guinevere:guinevere 750 /home/guinevere/tmp
```

Result: PASS.

### Top-level listing

Command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "ls -la /home/guinevere"
```

Output excerpt:

```text
drwxr-x--- 13 guinevere guinevere 4096 May 31 04:08 .
drwxr-xr-x  4 root      root      4096 May 31 03:09 ..
drwxr-x---  5 guinevere guinevere 4096 May 31 04:08 backups
drwxr-x---  3 guinevere guinevere 4096 May 31 04:08 code
drwxr-x---  7 guinevere guinevere 4096 May 31 04:08 config
drwxr-x---  9 guinevere guinevere 4096 May 31 04:08 data
drwxr-x---  2 guinevere guinevere 4096 May 31 04:08 evidence
drwxr-x---  5 guinevere guinevere 4096 May 31 04:08 logs
drwx------  2 guinevere guinevere 4096 May 31 04:08 scripts
drwx------  2 guinevere guinevere 4096 May 31 04:08 secrets
drwx------  2 guinevere guinevere 4096 May 31 03:43 .ssh
drwxr-x---  2 guinevere guinevere 4096 May 31 04:08 tmp
```

### Code directory readiness

Command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "ls -la /home/guinevere/code/guinevere"
```

Output:

```text
total 8
drwxr-x--- 2 guinevere guinevere 4096 May 31 04:08 .
drwxr-x--- 3 guinevere guinevere 4096 May 31 04:08 ..
```

Result: PASS. Directory exists and is empty.

### Guinevere user access

Command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 guinevere-vps "whoami && hostname && test -d /home/guinevere/code/guinevere && test -w /home/guinevere/tmp && echo GUINEVERE_DIR_ACCESS_OK"
```

Output:

```text
guinevere
faiz-prod-01
GUINEVERE_DIR_ACCESS_OK
```

Result: PASS.

### Systemd placeholder directory

Command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "ls -ld '/etc/systemd/system/guinevere-*.service.d'"
```

Output:

```text
drwxr-xr-x 2 root root 4096 May 31 04:08 /etc/systemd/system/guinevere-*.service.d
```

Result: PASS for StepPrompts literal command. Caveat documented: this is a literal wildcard placeholder, not a real unit-specific override directory.

## Evidence Artifacts

- `audit-reports/P0/STEP-P0-003/internal-context-report.md`
- `audit-reports/P0/STEP-P0-003/external-directory-readiness-report.md`
- `docs/setup-evidence/P0/STEP-P0-003/directory-tree.txt`
- `docs/setup-evidence/P0/STEP-P0-003/permissions.txt`
- `docs/setup-evidence/P0/STEP-P0-003/aizanta-post-check.md`
- `docs/setup-evidence/P0/STEP-P0-003/p0-003-summary.md`
- `docs/setup-evidence/P0/STEP-P0-003/verification.md`

## Shared VPS Impact

Aizanta post-check passed after the directory creation and permission correction.

### Post-change containers

```text
aizanta-bot Up 7 days (healthy) 8000/tcp
aizanta-nginx Up 7 days (healthy) 100.94.104.22:80->80/tcp
aizanta-frontend Up 7 days (healthy) 3000/tcp
aizanta-postgres Up 7 days (healthy) 127.0.0.1:5432->5432/tcp
aizanta-redis Up 7 days (healthy) 127.0.0.1:6379->6379/tcp
```

### Post-change protected ports

```text
LISTEN 0      4096                     127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=52688,fd=8))
LISTEN 0      4096                 100.94.104.22:80         0.0.0.0:*    users:(("docker-proxy",pid=235002,fd=8))
LISTEN 0      4096                     127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=52721,fd=8))
```

No Aizanta files, Docker networks, databases, Redis keyspaces, nginx config, or ports were modified.

## ADR Compliance

- **ADR-014:** Aligned. The directory tree implements the shared VPS isolation layout for the `guinevere` Linux user.
- **ADR-015:** Aligned. `secrets/` exists with `0700` and no plaintext secret was created.
- **ADR-019:** Preserved. No SSH, VPN, firewall, or public-port configuration was changed in this step.
- **ADR-030/031:** Preserved. No Redis or PostgreSQL service/database changes were made.

## AC Reference

- **AC-CORE-001:** Partially enabled. The filesystem prerequisites for future systemd-managed core services now exist.
- **AC-DATA-001:** Partially enabled. The data/log/evidence directory roots now exist for future classified artifacts.
- **AC-SEC-003:** Preserved. No plaintext secret files were created.

## Rollback / Re-run Safety

The directory creation is idempotent and safe to re-run.

Rollback before dependent steps start:

```bash
sudo rm -rf /home/guinevere/{code,config,data,logs,backups,evidence,secrets,scripts,tmp}
sudo rmdir '/etc/systemd/system/guinevere-*.service.d'
```

Rollback must not remove `/home/guinevere/.ssh`, `.cache`, shell dotfiles, or the `guinevere` user because those belong to P0-001/P0-002.

## Design Decisions / Caveats

- Followed StepPrompts as the active authority, not the external report's alternative `bin/src/.local` recommendation.
- Used `install -d` for idempotence, then corrected parent ownership/mode after discovering root-owned parents from nested path creation.
- Created the literal `/etc/systemd/system/guinevere-*.service.d` placeholder because StepPrompts explicitly requested it. No actual systemd units were modified or reloaded.
- Did not create `/var/lib/guinevere` or `/var/log/guinevere` because StepPrompts P0-003 did not require them; external report noted those are forward-looking for future systemd directives.

## Evidence Gate

Status: PASS, independent auditor gate passed.

Parent verification passed for directory count, permissions, ownership, code directory emptiness, Guinevere user access, Aizanta health, protected ports, evidence artifacts, and tracker sync.

Independent auditor gate: PASS.

Auditor report: `audit-reports/P0/STEP-P0-003/step-p0-003-auditor-report.md`.

Auditor summary: 18/18 DoD criteria passed, zero blocking findings, Aizanta unaffected, protected ports unchanged, tracker sync consistent, evidence schema complete, and the literal `guinevere-*.service.d` placeholder is documented as non-blocking.

## Footer

- **Source task:** STEP-P0-003 full autonomous execution
- **Date:** 2026-05-31
- **Implementer:** Hephaestus / Guinevere orchestration
- **Validation method:** Live SSH checks, deterministic filesystem/stat checks, local evidence artifacts, tracker sync, and mandatory auditor gate
