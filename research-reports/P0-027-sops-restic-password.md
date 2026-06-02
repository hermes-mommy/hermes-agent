# P0-027: SOPS + age untuk Restic Password Management — Production Patterns

**Date**: 2026-05-31  
**Author**: Guinevere / Librarian  
**Scope**: SOPS-encrypted restic password retrieval in shell backup scripts (VPS, age-only)  
**Request**: Production patterns for SOPS-encrypted restic password management — file format, `.sops.yaml` config, shell env var loading, `--password-command`, and best practices.

---

## Table of Contents

1. [SOPS Encrypted File Format for Key-Value Secrets](#1-sops-encrypted-file-format)
2. [`.sops.yaml` Configuration for Age Recipients](#2-sopsyaml-configuration)
3. [Shell Script Patterns — Decrypt & Set Env Vars](#3-shell-script-patterns)
4. [Restic `--password-command` with SOPS](#4-restic---password-command)
5. [`sops exec-env` — Zero-Disk Pattern](#5-sops-exec-env-pattern)
6. [Best Practices: Bulletproof Backup Script](#6-best-practices)
7. [Recommended Implementation](#7-recommended-implementation)

---

## 1. SOPS Encrypted File Format

### Option A: `.env` (dotenv) — Recommended for restic

SOPS natively supports `dotenv` input/output type. This is the cleanest format when you only need to set environment variables.

**Plaintext source** (`restic.env`):
```env
RESTIC_REPOSITORY=s3:https://s3.example.com/my-bucket
RESTIC_PASSWORD=super-secret-password-123
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

**Encrypted output** (`restic.env.sops`) — SOPS encrypts *values only*, keys remain readable:
```env
RESTIC_REPOSITORY=ENC[AES256_GCM,data:mjLv3cdqxwW...,type:str]
RESTIC_PASSWORD=ENC[AES256_GCM,data:fcWnUlISwGl...,type:str]
AWS_ACCESS_KEY_ID=ENC[AES256_GCM,data:JkEsjX9+dTm...,type:str]
AWS_SECRET_ACCESS_KEY=ENC[AES256_GCM,data:TDWZV2vBdB4...,type:str]
sops:
    kms: []
    gcp_kms: []
    azure_kv: []
    hc_vault: []
    age:
        - recipient: age1zeqkpfz7e3s207ynea0z0auc0mrct0pc7w4sh6j3d0c4qac3dahqj9ufdg
          enc: |
            -----BEGIN AGE ENCRYPTED FILE-----
            YWdlLWVuY3J5cHRpb24ub3JnL3YxCi0+IFgyNTUxOSBuV1lKR0...
            -----END AGE ENCRYPTED FILE-----
    lastmodified: "2026-05-31T12:00:00Z"
    mac: ENC[AES256_GCM,data:2PGiDLZgDNID...,type:str]
    version: 3.9.4
```

**Encrypt command**:
```bash
sops --encrypt --input-type dotenv --output-type dotenv restic.env > restic.env.sops
```

### Option B: YAML (for multiple key-value pairs + structured data)

YAML works well when you need `--extract` for individual values:

```yaml
restic_password: ENC[AES256_GCM,data:fcWnUlISwGl...,type:str]
aws_access_key_id: ENC[AES256_GCM,data:JkEsjX9+dTm...,type:str]
sops:
    age:
        - recipient: age1zeqkpfz7e3s207ynea0z0auc0mrct0pc7w4sh6j3d0c4qac3dahqj9ufdg
          enc: |
            -----BEGIN AGE ENCRYPTED FILE-----
            ...
            -----END AGE ENCRYPTED FILE-----
```

**Real-world example** — from `budimanjojo/home-cluster` ([source](https://github.com/budimanjojo/home-cluster/blob/main/restic-secret.sops.yaml)):
```yaml
AWS_ACCESS_KEY_ID: ENC[AES256_GCM,data:JkEsjX9+dTmEGbkibd1flA==,iv:...,tag:...,type:str]
RESTIC_REPOSITORY: ENC[AES256_GCM,data:mjLv3cdqxwWq/wcfcTHEpK1HE7EXaED4Z4zimpxlOQdQKSOLwWSaQZgv24MArDFwlQ==,iv:...,tag:...,type:str]
RESTIC_PASSWORD: ENC[AES256_GCM,data:fcWnUlISwGlDtjv+RIFTzw==,iv:...,tag:...,type:str]
sops:
    age:
        - recipient: age1zeqkpfz7e3s207ynea0z0auc0mrct0pc7w4sh6j3d0c4qac3dahqj9ufdg
          enc: |
            -----BEGIN AGE ENCRYPTED FILE-----
            ...
            -----END AGE ENCRYPTED FILE-----
    lastmodified: "2023-04-21T06:39:30Z"
    version: 3.7.3
```

**Key insight**: The `sops:` metadata footer is appended by SOPS automatically. It contains the encrypted data key (one per age recipient) and integrity MAC. **Never edit or remove the footer.**

---

## 2. `.sops.yaml` Configuration

### Minimal config (single recipient)

Place this at the root of your ops repository:

```yaml
# .sops.yaml
creation_rules:
  - path_regex: secrets/.*\.sops$
    input_type: dotenv
    output_type: dotenv
    age: age1zeqkpfz7e3s207ynea0z0auc0mrct0pc7w4sh6j3d0c4qac3dahqj9ufdg
```

### Environment-separated config (dev/staging/prod)

```yaml
# .sops.yaml
creation_rules:
  - path_regex: secrets/dev/.*\.sops$
    age: age1devkey...,age1backupkey...
    input_type: dotenv
    output_type: dotenv

  - path_regex: secrets/prod/.*\.sops$
    age: age1prodkey...,age1backupkey...
    input_type: dotenv
    output_type: dotenv
```

### With unencrypted fields (keep non-secret values visible)

```yaml
# .sops.yaml
creation_rules:
  - path_regex: restic/.*\.env\.sops$
    input_type: dotenv
    output_type: dotenv
    age: >-
      age1vpskey...,
      age1backupkey...
    unencrypted_regex: "^(RESTIC_REPOSITORY|BACKUP_HOST)$"
```

**Source**: [getsops.io docs on configuration](https://getsops.io/docs/), [DeepWiki .sops.yaml config](https://deepwiki.com/getsops/sops/2.1-configuration)

### Key generation

```bash
# Generate age key pair (already done on your VPS at ~/.config/sops/age/keys.txt)
age-keygen -o ~/.config/sops/age/keys.txt

# Get the public key
age-keygen -y ~/.config/sops/age/keys.txt
# → age1zeqkpfz7e3s207ynea0z0auc0mrct0pc7w4sh6j3d0c4qac3dahqj9ufdg
```

### Multiple recipients (comma-separated, NOT space-separated)

Important gotcha: age recipients in `.sops.yaml` must be **comma-separated**:

```yaml
# CORRECT — comma-separated
age: >-
  age1key1...,
  age1key2...,
  age1key3...

# WRONG — space-separated will fail with "malformed recipient"
age: >-
  age1key1... age1key2... age1key3...
```

**Source**: [getsops/sops discussion #1579](https://github.com/getsops/sops/discussions/1579)

---

## 3. Shell Script Patterns

### Pattern A: `sops exec-env` — Cleanest, zero-disk

SOPS can decrypt and inject variables directly into a child process environment — **no temp files, no disk writes**.

```bash
#!/bin/bash
set -euo pipefail

# SOPS will find the age key at default path ~/.config/sops/age/keys.txt
# Or explicitly: export SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt

sops exec-env /etc/restic/restic.env.sops \
  'restic backup /home/user --verbose'
```

To wrap multiple commands:
```bash
sops exec-env /etc/restic/restic.env.sops \
  'restic backup /home/user && restic forget --prune'
```

**`--pristine` mode**: prevents parent env leakage to child:
```bash
sops exec-env --pristine /etc/restic/restic.env.sops \
  'restic backup /home/user'
```

**`--same-process` mode**: replaces the sops process entirely via `execve`, so signals work correctly:
```bash
sops exec-env --same-process /etc/restic/restic.env.sops \
  'restic backup /home/user'
```

**Source**: [getsops.io docs on exec-env](https://getsops.io/docs/), [DeepWiki exec-env](https://deepwiki.com/getsops/sops/2.4-publishing-and-execution)

### Pattern B: `eval + sops decrypt` — For scripts that need env before start

If you need the variables available for setup steps before the main command:

```bash
#!/bin/bash
set -euo pipefail

# Decrypt .env.sops and export each variable
eval "$(sops --decrypt --output-type dotenv /etc/restic/restic.env.sops | sed '/^sops:/d' | sed 's/^/export /')"

# Now restic auto-picks RESTIC_PASSWORD, RESTIC_REPOSITORY, AWS_* from env
restic backup /home/user
```

**Source**: [OneUptime — SOPS on Ubuntu](https://oneuptime.com/blog/post/2026-03-02-how-to-set-up-sops-for-encrypted-secrets-on-ubuntu/view)

### Pattern C: `sops decrypt --extract` — Single-value extraction

For YAML/JSON files where you only need one key:

```bash
#!/bin/bash
set -euo pipefail

# Extract single value from YAML secrets file
export RESTIC_PASSWORD
RESTIC_PASSWORD=$(sops decrypt --extract '["restic_password"]' /etc/restic/secrets.yaml)

# sops decrypt --extract adds a trailing newline; printf handles it
# (RESTIC_PASSWORD will contain it but restic strips it)

restic backup /home/user
```

**Real-world usage** — from `wimpysworld/nix-config` ([source](https://github.com/wimpysworld/nix-config/blob/main/nixos/_mixins/scripts/install-system/install-system.sh#L229)):
```bash
TOKEN_FILE=$(mktemp)
trap 'rm -f "$TOKEN_FILE"' EXIT
sops decrypt --extract '["flakehub_token"]' "${SECRETS_FILE}" >"$TOKEN_FILE" 2>/dev/null
```

**Source**: [StackOverflow — sops extract trailing newline](https://stackoverflow.com/questions/75869176/how-to-extract-value-with-sops-without-the-extra-newline-in-the-output)

---

## 4. Restic `--password-command`

### The standard approach: `RESTIC_PASSWORD_COMMAND`

Restic supports a `--password-command` flag / `RESTIC_PASSWORD_COMMAND` env var. The command is executed and its **stdout** is read as the password.

```bash
#!/bin/bash
set -euo pipefail

export RESTIC_REPOSITORY="s3:https://s3.example.com/my-bucket"
export RESTIC_PASSWORD_COMMAND="sops decrypt --extract '[\"RESTIC_PASSWORD\"]' /etc/restic/secrets.yaml"

restic backup /home/user
```

### Critical: No pipe support in RESTIC_PASSWORD_COMMAND

Restic does **not** invoke a shell for `--password-command` — it uses `exec` semantics. Pipes are **not supported**:

```bash
# WRONG — pipe is passed as literal argument to sops
export RESTIC_PASSWORD_COMMAND="sops decrypt ... | head -1"
# → "sops: invalid option -- 1"

# CORRECT — wrap in shell explicitly
export RESTIC_PASSWORD_COMMAND="bash -c 'sops decrypt --extract ... /etc/restic/secrets.yaml | head -1'"
```

**Source**: [restic issue #5149](https://github.com/restic/restic/issues/5149)

### For `.env.sops` files with `exec-env`

You don't need `--password-command` at all — the password is already in the environment:

```bash
#!/bin/bash
set -euo pipefail

export SOPS_AGE_KEY_FILE="$HOME/.config/sops/age/keys.txt"

# exec-env injects RESTIC_PASSWORD + RESTIC_REPOSITORY + AWS creds
sops exec-env --same-process /etc/restic/restic.env.sops \
  'restic backup /home/user'
```

### Alternative: `RESTIC_PASSWORD_FILE`

Decrypt to a secured file and point restic at it:

```bash
#!/bin/bash
set -euo pipefail

# Decrypt to a ram-backed location
sops --decrypt --output-type dotenv /etc/restic/restic.env.sops \
  | grep -E '^RESTIC_PASSWORD=' \
  | cut -d= -f2- \
  > /run/secrets/restic-pw

chmod 600 /run/secrets/restic-pw

export RESTIC_REPOSITORY_FILE=/etc/restic/repo-location
export RESTIC_PASSWORD_FILE=/run/secrets/restic-pw

restic backup /home/user

# Clean up
rm -f /run/secrets/restic-pw
```

---

## 5. `sops exec-env` — Zero-Disk Pattern (Deep Dive)

This is the **recommended approach** for production VPS backups.

### How it works

```
┌─────────────┐     decrypt      ┌──────────┐      execve       ┌─────────┐
│ restic.env  │ ───────────────► │  sops    │ ────────────────► │  restic │
│  .sops      │   (age key)      │ exec-env │   (fork + env)    │ backup  │
└─────────────┘                  └──────────┘                   └─────────┘
                                                                    │
                                                             ENVs injected:
                                                             RESTIC_PASSWORD
                                                             RESTIC_REPOSITORY
                                                             AWS_ACCESS_KEY_ID
                                                             AWS_SECRET_ACCESS_KEY
```

**Key properties:**
1. **Plaintext never touches disk** — decrypted values live only in the child process's memory
2. **No shell exposure** — `ps aux` shows the command string, not environment values
3. **FIFO for `exec-file`** — if using `exec-file`, SOPS uses a named pipe by default, not a real file
4. **`--pristine`** — child process inherits only the decrypted variables, not the parent's entire env

### Full systemd timer integration

```ini
# /etc/systemd/system/restic-backup.service
[Unit]
Description=Restic backup (SOPS-decrypted)

[Service]
Type=oneshot
ExecStart=/usr/local/bin/restic-backup
User=root
# No EnvironmentFile= here — SOPS handles decryption internally

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/restic-backup.timer
[Unit]
Description=Daily restic backup

[Timer]
OnCalendar=daily
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
#!/usr/bin/env bash
# /usr/local/bin/restic-backup
set -euo pipefail

export SOPS_AGE_KEY_FILE="$HOME/.config/sops/age/keys.txt"

exec sops exec-env --same-process /etc/restic/restic.env.sops \
  'restic backup \
    --verbose \
    --exclude-caches \
    --exclude-if-present .nobackup \
    --exclude-file /etc/restic/excludes \
    /home/user'
```

**Source**: [getsops.io](https://getsops.io/docs/), [HostMyCode — VPS secrets management](https://www.hostmycode.com/blog/linux-vps-secrets-management-sops-age-2026)

---

## 6. Best Practices

### Bash Safety

```bash
#!/usr/bin/env bash
set -euo pipefail    # exit on error, undefined vars, pipe failures
IFS=$'\n\t'          # strict word splitting
```

### Never Leak to Logs / `ps`

| Anti-pattern | Why it's dangerous | Fix |
|---|---|---|
| `echo $RESTIC_PASSWORD` | Shows in shell history, log files | Never echo secrets |
| `export RESTIC_PASSWORD=$(...)` then `restic` | `ps aux` can read env of running process | Use `sops exec-env` or `--password-command` |
| `sops -d file > /tmp/secret` | /tmp is world-readable | Use `/run/secrets/` or `exec-env` |
| `script.sh --password secret` | `ps aux` shows password in argv | Use `--password-file` or env var |
| Piping through `cat` | Multiple copies of secret in memory | Use `sops --extract` directly |

**Key insight**: `sops exec-env` and `restic --password-command` both avoid putting the password in process argv or parent process environment that could be read via `/proc`.

**Source**: [Smallstep — Command Line Secrets](https://smallstep.com/blog/command-line-secrets/)

### File Permissions

```bash
chmod 600 /etc/restic/restic.env.sops    # encrypted file — only root
chmod 600 ~/.config/sops/age/keys.txt     # age private key
chmod 700 /usr/local/bin/restic-backup    # script
```

### Temp File Discipline

If you must use temp files (e.g., for `--password-file`):
- Use `/run/secrets/` or `/dev/shm/` (tmpfs, no disk write)
- Never use `/tmp` (world-writable)
- Always `trap 'rm -f "$TMPFILE"' EXIT`
- `umask 077` before creating

```bash
#!/bin/bash
set -euo pipefail

TMPFILE=$(mktemp -p /run/secrets)
trap 'rm -f "$TMPFILE"' EXIT
umask 077

sops decrypt --extract '["RESTIC_PASSWORD"]' /etc/restic/secrets.yaml > "$TMPFILE"

restic --password-file "$TMPFILE" backup /home/user
```

### Age Key Protection

- **Never** commit `keys.txt` to git
- `~/.config/sops/age/keys.txt` should be `chmod 600`
- Backup the age private key offline (password manager, encrypted USB)
- For CI/CD, inject `SOPS_AGE_KEY` via secrets manager, never bake into images
- Alternative: `SOPS_AGE_KEY_FILE` points to a gocryptfs/encrypted volume

```bash
# Explicit key file path (useful for non-default locations)
export SOPS_AGE_KEY_FILE="$HOME/.config/sops/age/keys.txt"

# Or pass key content directly (for CI, from a secret store)
export SOPS_AGE_KEY="AGE-SECRET-KEY-1..."
```

### Version Control Discipline

```text
ops-repo/
├── .sops.yaml                  # creation rules — committed
├── secrets/
│   ├── restic.prod.env.sops    # encrypted — committed
│   ├── restic.dev.env.sops     # encrypted — committed
│   └── README.md               # which keys can decrypt which files
├── .gitignore
│   └── *.env                   # never commit plaintext .env files
```

---

## 7. Recommended Implementation

### For your VPS setup

Given: VPS has SOPS + age key at `~/.config/sops/age/keys.txt`.

**Step 1**: Create the encrypted env file
```bash
# Create plaintext source (temporary)
cat > /tmp/restic-plain.env << 'EOF'
RESTIC_REPOSITORY=s3:https://your-bucket.s3.amazonaws.com/restic-repo
RESTIC_PASSWORD=your-strong-password-here
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
EOF

# Encrypt to .env.sops format
sops --encrypt \
  --input-type dotenv \
  --output-type dotenv \
  --age $(age-keygen -y ~/.config/sops/age/keys.txt) \
  /tmp/restic-plain.env > /etc/restic/restic.env.sops

# Remove plaintext
shred -u /tmp/restic-plain.env
chmod 600 /etc/restic/restic.env.sops
```

**Step 2**: Create the backup script
```bash
cat > /usr/local/bin/restic-backup << 'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

export SOPS_AGE_KEY_FILE="$HOME/.config/sops/age/keys.txt"

exec sops exec-env --same-process /etc/restic/restic.env.sops \
  'restic backup \
    --verbose \
    --exclude-caches \
    --exclude-if-present .nobackup \
    /home/user \
    /etc \
    /var/lib'
SCRIPT
chmod 700 /usr/local/bin/restic-backup
```

**Step 3**: Create the systemd service
```ini
# /etc/systemd/system/restic-backup.service
[Unit]
Description=Restic encrypted backup
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/restic-backup
User=root
# No secrets in unit file — SOPS exec-env handles everything in memory
Nice=19
IOSchedulingClass=best-effort
IOSchedulingPriority=7

[Install]
WantedBy=multi-user.target
```

### If you prefer `--password-command` instead of `exec-env`

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

export SOPS_AGE_KEY_FILE="$HOME/.config/sops/age/keys.txt"
export RESTIC_REPOSITORY="s3:https://your-bucket.s3.amazonaws.com/restic-repo"
export AWS_ACCESS_KEY_ID="your-access-key"           # only if S3
export AWS_SECRET_ACCESS_KEY="your-secret-key"        # only if S3

export RESTIC_PASSWORD_COMMAND="sops decrypt --extract '[\"RESTIC_PASSWORD\"]' /etc/restic/secrets.yaml"

# Or for .env.sops format:
# export RESTIC_PASSWORD_COMMAND="bash -c 'sops decrypt --output-type dotenv /etc/restic/restic.env.sops | grep -E \"^RESTIC_PASSWORD=\" | cut -d= -f2-'"

exec restic backup \
  --verbose \
  --exclude-caches \
  --exclude-if-present .nobackup \
  /home/user /etc
```

**Note**: `RESTIC_PASSWORD_COMMAND` is preferred over `RESTIC_PASSWORD` because the password never enters a process environment that could be read via `/proc/*/environ`.

---

## Sources

| Source | URL | Relevance |
|---|---|---|
| SOPS Official Docs | https://getsops.io/docs/ | `exec-env`, file formats, `.sops.yaml` config |
| SOPS DeepWiki — Config | https://deepwiki.com/getsops/sops/2.1-configuration | `.sops.yaml` detail, env vars |
| SOPS DeepWiki — Age | https://deepwiki.com/getsops/sops/3.5-age | Age-specific config, env vars |
| SOPS DeepWiki — exec-env | https://deepwiki.com/getsops/sops/2.4-publishing-and-execution | `exec-env`, `exec-file`, `--pristine`, `--same-process` |
| Restic Scripting Docs | https://github.com/restic/restic/blob/master/doc/075_scripting.rst | `RESTIC_PASSWORD_COMMAND`, scripting env vars |
| Restic — Preparing Repo | https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html | Password options overview |
| budimanjojo/home-cluster | https://github.com/budimanjojo/home-cluster/blob/main/restic-secret.sops.yaml | Real-world SOPS+restic YAML |
| HostMyCode — VPS Secrets 2026 | https://www.hostmycode.com/blog/linux-vps-secrets-management-sops-age-2026 | Deploy-time decrypt, systemd wiring |
| HostMyCode — Secrets Rotation | https://www.hostmycode.com/blog/linux-vps-secrets-rotation-sops-age-practical-workflow-2026 | Recipient rotation, re-encrypt workflow |
| Smallstep — CLI Secrets | https://smallstep.com/blog/command-line-secrets/ | `ps` leakage, env var exposure |
| restic issue #5149 | https://github.com/restic/restic/issues/5149 | Pipe unsupported in RESTIC_PASSWORD_COMMAND |
| wimpysworld/nix-config | https://github.com/wimpysworld/nix-config/blob/main/nixos/_mixins/scripts/install-system/install-system.sh | `sops decrypt --extract` real usage |
| SOPS discussion #1579 | https://github.com/getsops/sops/discussions/1579 | Comma-separated age recipients gotcha |
| StackOverflow — sops extract | https://stackoverflow.com/questions/75869176 | Trailing newline in `--extract` |
| OneUptime — SOPS Ubuntu | https://oneuptime.com/blog/post/2026-03-02-how-to-set-up-sops-for-encrypted-secrets-on-ubuntu/view | `.sops.yaml` examples, dotenv pattern |
| Secrets at Rest: SOPS + age | https://pikemd.com/blog/sops-age-docker-compose/ | `.sops.yaml` with `unencrypted_regex` |
| The Calm Way — VPS | https://www.dchost.com/blog/en/the-calm-way-to-secrets-on-a-vps-gitops-with-sops-age-systemd-magic-and-rotation-you-can-sleep-on/ | Systemd + SOPS workflow |
| NixOS Wiki — Restic + SOPS | https://wiki.nixos.org/wiki/Restic | sops-nix restic integration |