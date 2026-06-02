# External Research Report: SOPS + age Encryption/Decryption Workflows for Python Projects

| Field | Value |
|---|---|
| **Scope** | P0 / STEP-P0-013 |
| **Date** | 2026-05-31 |
| **Author** | Guinevere (Librarian Agent) |
| **Status** | Complete |

## 1. Executive Summary

SOPS (Secrets OPerationS) + age is the **de facto standard** for Git-native secret management in 2026. It replaces the fragile "just don't commit `.env`" policy with encrypt-at-rest secrets that are safe to version-control. For Python projects, the integration patterns range from calling the `sops` binary via subprocess at startup to using `pydantic-settings-sops` for seamless Pydantic model hydration.

**Key findings for Guinevere:**

- **Recommended approach**: Call `sops` binary via `subprocess` at service startup (pre-bootstrap pattern), or use `sops exec-env`/`exec-file` in entrypoint scripts.
- **Production pattern**: Decrypt to `/run/` (tmpfs/memory-backed), never write plaintext to persistent disk.
- **CI/CD**: GitHub Actions can decrypt via `SOPS_AGE_KEY` secret, but best practice is to decrypt only on the target server.
- **Key management**: Private keys NEVER in repo, only in server filesystem or secret store.

---

## 2. Python Libraries for SOPS Decryption

### 2.1 Option A: `pydantic-settings-sops` (Recommended for Pydantic users)

[**pavelzw/pydantic-settings-sops**](https://github.com/pavelzw/pydantic-settings-sops) — Context7 rating: **High** (Benchmark 68)

This is the most **Pythonic** approach. It integrates directly with `pydantic-settings` to decrypt SOPS-encrypted YAML/JSON files into typed Pydantic models.

```python
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from pydantic_settings_sops import SOPSConfigSettingsSource

class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(yaml_file="secrets.yaml")
    db_host: str
    db_port: int = 5432
    db_user: str
    db_password: str

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: BaseSettings,
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings, SOPSConfigSettingsSource(settings_cls))
```

**Pros**: Type-safe, zero boilerplate decryption, supports YAML/JSON SOPS files.
**Cons**: Requires pydantic-settings dependency; limited to the formats pydantic supports.

### 2.2 Option B: `agenv` — Simple age-decrypted env loader

[**zachcheung/agenv**](https://github.com/zachcheung/agenv) — lightweight Python package

```python
from agenv import load_age_env

# Decrypts .env.age and loads into os.environ
load_age_env(".env.age")
```

Key discovery order:
1. `identity` parameter to `load_age_env()`
2. `AGE_SECRET_KEY` env var
3. `AGE_SECRET_KEY_FILE` env var
4. Default: `$HOME/.age/age.key`

**Pros**: Simple, purpose-built for Python env loading.
**Cons**: Uses age directly (not SOPS), so no structured format support; requires age binary separately.

### 2.3 Option C: `dotenvage` — Encrypt individual values in .env files

[**dotenvage**](https://pypi.org/project/dotenvage/) — individual-value encryption (v0.6.0, updated 2026-04)

```python
import dotenvage

loader = dotenvage.EnvLoader()
loaded_files = loader.load()
# Values with keys matching PASSWORD, SECRET, KEY, TOKEN auto-decrypt

# Manual encrypt/decrypt
manager = dotenvage.SecretManager()
encrypted = manager.encrypt_value("my-secret-password")
decrypted = manager.decrypt_value(encrypted)
```

**Pros**: Per-value encryption (not whole-file); auto-detects which keys should be encrypted.
**Cons**: Different from standard SOPS workflow; less ecosystem support.

### 2.4 Option D: `sops-run` — Python wrapper for sops exec-env

[**belthesar/sops-run**](https://github.com/belthesar/sops-run) — CLI wrapper

```bash
sops-run --create bash   # Creates encrypted manifest
sops-run bash script.sh   # Runs command with decrypted env vars
```

Not a library for programmatic use, but useful for development workflow.

### 2.5 Option E: Direct `subprocess` call (Recommended for Guinevere)

The **most battle-tested** pattern in production Python projects: call the `sops` binary via subprocess.

Real-world example from a production Docker deployment ([kienlt's notebook](https://blackmetalz.github.io/no-vault-no-gitops-no-problem-securing-k8s-secrets-with-sops.html), 2026-01):

```python
#!/usr/bin/env python3
import os
import subprocess
import sys

ENCRYPTED_SECRET_PATH = "/etc/secrets/encrypted.env"
AGE_KEY_FILE = "/etc/.yolo/key.txt"
DECRYPTED_ENV_PATH = "/app/.env"

def main():
    # Read age key
    with open(AGE_KEY_FILE, 'r') as f:
        age_key = ''.join(line for line in f if not line.startswith('#')).strip()

    env = os.environ.copy()
    env['SOPS_AGE_KEY'] = age_key

    # Detect format
    with open(ENCRYPTED_SECRET_PATH, 'r') as f:
        first_char = f.read(1)

    if first_char == '{':
        cmd = ['/usr/local/bin/sops', '--decrypt',
               '--input-type', 'json', '--output-type', 'binary',
               ENCRYPTED_SECRET_PATH]
    else:
        cmd = ['/usr/local/bin/sops', '--decrypt', ENCRYPTED_SECRET_PATH]

    with open(DECRYPTED_ENV_PATH, 'wb') as out:
        result = subprocess.run(cmd, env=env, stdout=out, stderr=subprocess.PIPE)

    if result.returncode != 0:
        print(f"FATAL: Decryption failed: {result.stderr.decode()}", file=sys.stderr)
        sys.exit(1)

    # Replace process with the actual application
    os.execvp('streamlit', ['streamlit', 'run', 'report.py'])

if __name__ == '__main__':
    main()
```

**Pros**: Full control, works with any SOPS format, no extra Python dependencies.
**Cons**: Requires `sops` binary installed in the runtime environment.

---

## 3. Pre-Bootstrap Decryption Pattern ("Decrypt → Start")

The canonical pattern for Python services is the **pre-bootstrap decryption**:

### Pattern A: Entrypoint script decrypts → Python app starts

```
┌──────────────────┐     ┌──────────────────┐     ┌────────────────┐
│  docker-entrypoint│────>│  Python          │────>│ Application    │
│  .sh / .py        │     │  (subprocess)    │     │ (uvicorn, etc) │
│  decrypts .env    │     │  loads .env      │     │                │
│  → writes to /run/│     │  into os.environ  │     │                │
└──────────────────┘     └──────────────────┘     └────────────────┘
```

### Pattern B: Shell entrypoint with `sops exec-env`

The most secure pattern — plaintext **never touches disk**:

```bash
#!/bin/bash
# docker-entrypoint.sh
set -euo pipefail

# Decrypt directly into environment of the Python process
exec sops exec-env /app/secrets/prod.env.sops \
  -- python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The `--same-process` flag can be used on Unix to replace the sops process entirely:

```bash
exec sops exec-env --same-process /app/secrets/prod.env.sops \
  -- python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Pattern C: `sops exec-file` for Docker Compose

For Docker Compose stacks, `sops exec-file` decrypts to an in-memory file descriptor and exposes it via `{}`:

```bash
sops exec-file --no-fifo \
  --input-type dotenv --output-type dotenv \
  /app/.env.sops \
  'docker compose -f docker-compose.yml --env-file {} up -d'
```

**Critical**: `--no-fifo` is required on Linux — Docker Compose's `--env-file` needs a seekable file handle, and named pipes (default FIFO behavior) aren't seekable.

---

## 4. Environment Variable Injection Patterns

### 4.1 `source <(sops -d ...)` — Simple but leaky

```bash
# BAD: Variables persist in calling shell after script exits
source <(sops -d /app/secrets/.env.sops)
python app.py
```

### 4.2 `sops exec-env` — Variables scoped to child process (RECOMMENDED)

```bash
# GOOD: Variables exist only in child process address space
sops exec-env /app/secrets/.env.sops 'python app.py'
```

Real-world example from [colorcodebot](https://github.com/AndydeCleyre/colorcodebot/blob/develop/start/local.sh):

```bash
exec sops exec-env "app/sops/colorcodebot.${deployment}.yml" \
  "./venv/bin/python ./colorcodebot.py"
```

### 4.3 Python subprocess with env injection

```python
import os
import subprocess

def decrypt_env(sops_file: str, age_key: str) -> dict:
    """Decrypt a .env.sops file and return as dict."""
    env = os.environ.copy()
    env['SOPS_AGE_KEY'] = age_key

    result = subprocess.run(
        ['sops', '--decrypt', '--output-type', 'dotenv', sops_file],
        capture_output=True, text=True, env=env
    )
    result.check_returncode()

    decrypted = {}
    for line in result.stdout.splitlines():
        if '=' in line and not line.startswith('#'):
            key, _, value = line.partition('=')
            decrypted[key.strip()] = value.strip()
    return decrypted

# Use decrypted vars to launch the app
secrets = decrypt_env('/etc/secrets/.env.sops', key)
merged_env = {**os.environ, **secrets}

subprocess.run(
    ['python', '-m', 'uvicorn', 'app.main:app'],
    env=merged_env
)
```

---

## 5. Docker Entrypoint Patterns

### 5.1 Shell entrypoint with `sops exec-env` (RECOMMENDED)

```dockerfile
FROM python:3.12-slim

# Install sops
RUN apt-get update && apt-get install -y wget \
    && wget -O /usr/local/bin/sops \
       https://github.com/getsops/sops/releases/download/v3.9.4/sops-v3.9.4.linux.amd64 \
    && chmod +x /usr/local/bin/sops \
    && apt-get clean

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Use exec-form to avoid shell expansion issues
# SOPS_AGE_KEY_FILE is mounted as a Docker secret
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

```bash
#!/bin/bash
# docker-entrypoint.sh
set -euo pipefail

# SOPS_AGE_KEY_FILE should be mounted from Docker secrets or volume
# Decrypt and exec — plaintext never on disk
exec sops exec-env --same-process /app/secrets/.env.sops \
  -- "$@"
```

### 5.2 Python entrypoint (subprocess-based)

```dockerfile
FROM python:3.12-slim

# Install sops
RUN wget -O /usr/local/bin/sops \
  https://github.com/getsops/sops/releases/download/v3.9.4/sops-v3.9.4.linux.amd64 \
  && chmod +x /usr/local/bin/sops

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# entrypoint.py handles decryption before starting the app
CMD ["python", "/app/entrypoint.py"]
```

### 5.3 Docker Compose with SOPS sidecar (legacy pattern)

Older pattern using sidecar container and shared volume — **not recommended** for new projects:

```yaml
version: '3'
services:
  sops-sidecar:
    image: mozilla/sops:latest
    volumes:
      - ./secrets:/secrets:ro
      - shared-secrets:/shared
    command: >
      sh -c "sops --decrypt /secrets/secret.enc.env > /shared/secret.env"

  app:
    build: .
    depends_on:
      sops-sidecar:
        condition: service_completed_successfully
    volumes:
      - shared-secrets:/shared:ro
    env_file: /shared/secret.env

volumes:
  shared-secrets:
```

### 5.4 No-shell final image (hardened)

For maximum security, remove the shell from the final image after sops is installed:

```dockerfile
# Remove all shells — prevents anyone exec-ing into container
RUN rm -f /bin/sh /bin/ash /bin/bash /usr/bin/sh 2>/dev/null || true

# Must use exec form of CMD (shell form won't work without a shell)
CMD ["python3", "/app/entrypoint.py"]
```

---

## 6. systemd Service Patterns

### 6.1 Decrypt to /run (tmpfs) at startup (RECOMMENDED)

From [openclaw-infra](https://github.com/matskevich/openclaw-infra/blob/main/scripts/setup-vault.sh) and [dchost.com](https://www.dchost.com/blog/en/the-calm-way-to-secrets-on-a-vps-gitops-with-sops-age-systemd-magic-and-rotation-you-can-sleep-on/):

```ini
[Unit]
Description=My Python App
After=network-online.target

[Service]
Type=simple
User=myapp
Group=myapp

# Create tmpfs directory and decrypt before app starts
ExecStartPre=/usr/bin/mkdir -p /run/myapp
ExecStartPre=/usr/bin/sops --decrypt \
  --output /run/myapp/app.env \
  /srv/myrepo/secrets/app.env.sops

# Load decrypted secrets
EnvironmentFile=/run/myapp/app.env

# Start the app
ExecStart=/usr/local/bin/python -m uvicorn app.main:app

# Clean up on stop
ExecStopPost=/bin/rm -rf /run/myapp

# Hardening
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full
ProtectHome=true

[Install]
WantedBy=multi-user.target
```

**Key points**:
- `/run/` is memory-backed (tmpfs), wiped on reboot
- `ExecStopPost` cleans up decrypted files
- `EnvironmentFile` is loaded by systemd before `ExecStart`

### 6.2 Decrypt helper script + systemd integration

Better to extract the decrypt logic into a dedicated script:

```bash
#!/bin/bash
# /usr/local/bin/decrypt-app-env.sh
set -euo pipefail

SOPS_FILE="/srv/myrepo/secrets/app.env.sops"
AGE_KEY="/etc/sops/age/keys.txt"
RUN_DIR="/run/myapp"

mkdir -p "$RUN_DIR"
chmod 700 "$RUN_DIR"

SOPS_AGE_KEY_FILE="$AGE_KEY" sops --decrypt \
  --input-type dotenv --output-type dotenv \
  "$SOPS_FILE" > "$RUN_DIR/.env"

chmod 600 "$RUN_DIR/.env"
echo "[vault] decrypted to $RUN_DIR/.env"
```

Then in systemd:

```ini
[Service]
ExecStartPre=/usr/local/bin/decrypt-app-env.sh
EnvironmentFile=/run/myapp/.env
ExecStart=/usr/local/bin/python -m app
ExecStopPost=/bin/rm -rf /run/myapp
```

### 6.3 Auto-reload on file change (Path unit)

For zero-downtime secret rotation, use systemd Path unit to detect changes and reload:

```ini
# /etc/systemd/system/myapp-reload.service
[Unit]
Description=Re-decrypt secrets and reload My App

[Service]
Type=oneshot
ExecStart=/usr/bin/sops --decrypt --output /run/myapp/app.env \
  /srv/myrepo/secrets/app.env.sops
ExecStart=/bin/systemctl reload myapp.service
```

```ini
# /etc/systemd/system/myapp.path
[Unit]
Description=Watch encrypted secrets for My App

[Path]
PathChanged=/srv/myrepo/secrets/app.env.sops
Unit=myapp-reload.service

[Install]
WantedBy=multi-user.target
```

### 6.4 Flock-based locking for concurrent starts

Prevent race conditions if multiple services start simultaneously:

```ini
ExecStartPre=/usr/bin/flock -n /run/myapp/.sops.lock \
  /usr/bin/sops --decrypt --output /run/myapp/app.env \
  /srv/myrepo/secrets/app.env.sops
```

---

## 7. Development Workflow

### 7.1 First-time setup

```bash
# 1. Install tools
brew install age sops      # macOS
apt install age sops       # Debian/Ubuntu (may need backports)
# Or download binary directly (see SOPS docs)

# 2. Generate age keypair
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt
chmod 600 ~/.config/sops/age/keys.txt

# For post-quantum hybrid keys (age v1.3.0+):
age-keygen -pq -o ~/.config/sops/age/keys.txt

# 3. Note the public key
age-keygen -y ~/.config/sops/age/keys.txt
# → age1abc123...
```

### 7.2 Project `.sops.yaml` configuration

Create at project root (safe to commit — contains only public keys):

```yaml
creation_rules:
  # Dotenv format: leave non-secret config unencrypted
  - path_regex: .*\.env(\.sops)?$
    input_type: dotenv
    output_type: dotenv
    age: &prod_key "age1abc123..."
    unencrypted_regex: "^(TZ|PUID|PGID|LOG_LEVEL|NODE_ENV|APP_ENV)$"

  # Python YAML config files
  - path_regex: .*secrets.*\.yaml$
    age: *prod_key

  # JSON credential files
  - path_regex: .*credentials(\.sops)?\.json$
    age: *prod_key
    encrypted_regex: "^(api_key|password|token|secret)$"
```

### 7.3 Creating and editing encrypted files

```bash
# Create new encrypted file (opens $EDITOR)
sops secrets/prod.env.sops

# Encrypt existing .env file
sops --encrypt --input-type dotenv --output-type dotenv \
  .env > .env.sops

# Encrypt in-place
sops --encrypt --in-place .env.sops

# Decrypt to stdout (for inspection)
sops --decrypt .env.sops

# Decrypt to file (for local development — be careful not to commit)
sops --decrypt .env.sops > .env
```

### 7.4 direnv integration (automatic env loading on `cd`)

From [jfmaes.me](https://jfmaes.me/blog/stop-committing-your-secrets-you-know-who-you-are/) — SOPS + age + direnv for zero-friction development:

```bash
# .envrc — put in project root
load_encrypted_env() {
  local file="$1"
  [ ! -f "$file" ] && return
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    [[ "$line" == \#* ]] && continue
    export "$line"
  done < <(sops -d "$file")
}

load_encrypted_env .env.sops
load_encrypted_env .env.local.sops
```

Then run `direnv allow` — secrets auto-load when you `cd` into the directory and unload when you leave.

### 7.5 Verify all encrypted files decrypt correctly

```bash
# Decrypt every .sops file to /dev/null
for f in $(find . -name '*.env.sops' -o -name '*.sops.yaml'); do
  sops -d "$f" > /dev/null || echo "FAIL: $f"
done
```

---

## 8. Age Key Management for Teams

### 8.1 Multi-recipient `.sops.yaml`

Multiple age recipients can be added so every team member and every server can decrypt:

```yaml
creation_rules:
  - path_regex: .*\.env\.sops$
    age:
      - "age1alice..."   # Alice's workstation
      - "age1bob..."     # Bob's workstation
      - "age1prod..."    # Production VPS
      - "age1ci..."      # CI/CD runner (optional)
```

SOPS encrypts the data key to **each recipient**, so any holder of a matching private key can decrypt. No need to re-encrypt secrets when the team changes.

### 8.2 Adding/removing team members

```bash
# Add new recipient to .sops.yaml, then:
sops updatekeys --yes secrets/prod.env.sops

# Or re-encrypt explicitly:
sops --decrypt secrets/prod.env.sops \
  | sops --encrypt --age "$NEW_RECIPIENTS" /dev/stdin \
  > secrets/prod.env.sops.new
mv secrets/prod.env.sops.new secrets/prod.env.sops
```

### 8.3 Key rotation in two steps (zero downtime)

From [dchost.com](https://www.dchost.com/blog/en/the-calm-way-to-secrets-on-a-vps-gitops-with-sops-age-systemd-magic-and-rotation-you-can-sleep-on/):

1. **Add new key** → `sops updatekeys` → deploy → all servers can still decrypt
2. **Remove old key** → `sops updatekeys` → deploy → old key can no longer decrypt

### 8.4 Key backup

**Critical**: age has NO key revocation. Lose the private key = lose all secrets encrypted to it.

- Backup private key to a password manager (1Password, Bitwarden)
- NEVER backup the key to the same cloud storage that the key encrypts (the "cold key problem")

### 8.5 Server-specific keys

Generate a **dedicated keypair per server** — never reuse workstation keys:

```bash
sudo mkdir -p /etc/sops/age
sudo chmod 700 /etc/sops/age
sudo age-keygen -o /etc/sops/age/keys.txt
sudo chmod 600 /etc/sops/age/keys.txt
```

---

## 9. CI/CD Patterns

### 9.1 GitHub Actions — Decrypt using `SOPS_AGE_KEY`

**Pattern from production repos** ([kalisio/feathers-distributed](https://github.com/kalisio/feathers-distributed/blob/master/.github/workflows/main.yaml), [timdeschryver/Sandbox](https://github.com/timdeschryver/Sandbox/blob/main/.github/workflows/ci.yml)):

```yaml
name: CI
on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install sops
        run: |
          curl -LO https://github.com/getsops/sops/releases/latest/download/sops-v3.9.4.linux.amd64
          sudo mv sops-v3.9.4.linux.amd64 /usr/local/bin/sops
          sudo chmod +x /usr/local/bin/sops

      - name: Decrypt secrets
        env:
          SOPS_AGE_KEY: ${{ secrets.SOPS_AGE_KEY }}
        run: |
          sops --decrypt config/secrets.enc.json > config/secrets.json

      - name: Run tests
        env:
          SOPS_AGE_KEY: ${{ secrets.SOPS_AGE_KEY }}
        run: ./scripts/run_tests.sh
```

### 9.2 GitHub Actions — Decrypt and update all keys

From [budimanjojo/nix-config](https://github.com/budimanjojo/nix-config/blob/main/.github/workflows/update-sops-keys.yaml):

```yaml
- name: Update SOPS keys
  env:
    SOPS_AGE_KEY: ${{ secrets.SOPS_AGE_KEY }}
  run: |
    find . -type f -name \*.sops.yaml \
      ! -name .sops.yaml \
      -exec sops updatekeys --yes {} \;
```

### 9.3 Security best practice: server-side decrypt only

From [hostmycode.com](https://www.hostmycode.com/blog/linux-vps-secrets-management-sops-age-2026):

> **"Should CI decrypt secrets?" — Usually no. If CI can decrypt prod secrets, then a CI breach is effectively a prod breach. Prefer decrypting on the VPS using a key that lives only on that server."**

Preferred pattern:

1. CI builds and deploys the repo (including encrypted `.env.sops`)
2. VPS pulls the repo
3. VPS decrypts using its own `/etc/sops/age/keys.txt`
4. systemd starts the service with `EnvironmentFile=/run/myapp/.env`

### 9.4 Custom GitHub Action for SOPS

For repeated use, create a reusable action:

```yaml
# .github/actions/load-sops-secrets/action.yml
name: 'Load SOPS Secrets'
description: 'Decrypt SOPS-encrypted files'
inputs:
  age_key:
    description: 'Age private key content'
    required: true
runs:
  using: 'composite'
  steps:
    - run: |
        echo "${{ inputs.age_key }}" > /tmp/age-key.txt
        export SOPS_AGE_KEY_FILE=/tmp/age-key.txt
        find . -name '*.sops' -o -name '*.sops.yaml' \
          | while read f; do
            sops --decrypt "$f" > "${f%.sops}"
          done
      shell: bash
```

---

## 10. `.gitignore` Patterns

### 10.1 Recommended `.gitignore` for SOPS + age projects

```gitignore
# === PLAINTEXT SECRET FILES — NEVER COMMIT ===
# Plain .env files (dangerous if committed)
.env
.env.*
!.env.sops
!.env.enc
!.enc.env

# Common Python env file names
.env.local
.env.development
.env.production
.env.staging

# Decrypted secret files
secrets.yaml
secrets.json
*.decrypted.*

# Age private keys — NEVER COMMIT
age.key
*.age-key
keys.txt
*.key

# sops config with private keys (rare, but be safe)
.sops.yaml  # ← Contains only public keys, so technically safe.
            # But some teams prefer to keep it committed.
            # If you store private keys here, ADD IT TO GITIGNORE.
```

### 10.2 Key principle

| File type | In repo? | In `.gitignore`? |
|---|---|---|
| `.env.sops` (encrypted) | ✅ YES — safe to commit | ❌ No |
| `.env` (plaintext) | ❌ NO — never | ✅ Yes |
| `.enc.env` (encrypted) | ✅ YES | ❌ No |
| `keys.txt` (private key) | ❌ NO — never | ✅ Yes |
| `.sops.yaml` (public keys only) | ✅ YES | ❌ No |

### 10.3 Pre-commit hook to catch plaintext secrets

```bash
#!/bin/bash
# .git/hooks/pre-commit
set -euo pipefail

# Block plaintext .env files from being staged
for file in $(git diff --cached --name-only | grep -E '^\.env$|^\.env\.local$|^secrets\.yaml$|^\.env\.development$'); do
  echo "ERROR: Unencrypted secret file staged: $file"
  echo "Run: sops --encrypt $file > ${file}.sops"
  exit 1
done

# Block files containing DATABASE_URL= pattern (likely secrets) outside .sops files
for file in $(git diff --cached --name-only | grep -v '\.sops'); do
  if git show :"$file" | grep -q '^DATABASE_URL=' 2>/dev/null; then
    echo "ERROR: Potential secret (DATABASE_URL=) in non-SOPS file: $file"
    exit 1
  fi
done
```

---

## 11. Common Mistakes

### 11.1 Committing plaintext `.env`

**The cardinal sin**. Even with `.gitignore`, mistakes happen:

- `git add -A` after generating a new `.env`
- Backup/sync tools that don't respect `.gitignore`
- `git add --force`

**Mitigation**: Use `.gitignore` + pre-commit hooks + encrypted files as the ONLY source of truth.

### 11.2 Wrong age key path

**Symptom**: `sops` fails with "no identity matched" or "failed to decrypt data key".

**Causes**:
- `SOPS_AGE_KEY_FILE` points to wrong path
- Using `SOPS_AGE_KEY` (content) when `SOPS_AGE_KEY_FILE` (path) is expected
- Key file has incorrect permissions (must be `600` or `400`)

**Key discovery order** for SOPS:
1. `SOPS_AGE_KEY` env var (direct key content — highest priority)
2. `SOPS_AGE_KEY_FILE` env var (path to key file)
3. `SOPS_AGE_KEY_CMD` env var (command that outputs key)
4. Default: `~/.config/sops/age/keys.txt`

### 11.3 Broken `encrypted_regex` or `unencrypted_regex`

**Symptom**: Wrong fields are encrypted, or decrypted file has unexpected content.

**Fix**: Test with a sample file:

```bash
sops --config .sops.yaml \
  --input-type dotenv --output-type dotenv \
  -d test.env.sops
```

### 11.4 Wrong file naming (format detection)

SOPS detects format from file **extension**, not content. Common mistakes:

| File name | SOPS format detection | Problem |
|---|---|---|
| `.env.enc` | Binary (no format detected) | Everything becomes `data=` |
| `.enc.env` | ✅ Dotenv (ends in `.env`) | Correct |
| `.env.sops` | ✅ Dotenv (ends in `.env`) | Correct (recommended) |

**Rule**: The encrypted file must end in `.env` for dotenv format detection, or explicitly specify `--input-type` and `--output-type`.

### 11.5 Forgetting `--no-fifo` on Linux

**Symptom**: `docker compose --env-file` fails silently.

**Fix**: Always use `sops exec-file --no-fifo` on Linux. The default FIFO mode uses named pipes which aren't seekable — Docker Compose needs seekable file handles.

### 11.6 Temp file leaks

**Bad**:
```bash
echo "$SECRET" > /tmp/temp-secret.txt
```

**Good**:
```bash
umask 077
TMPFILE=$(mktemp)
trap 'rm -f "$TMPFILE"' EXIT
echo "$SECRET" > "$TMPFILE"
```

### 11.7 No `unencrypted_regex` for config values

Non-secret config (like `TZ`, `NODE_ENV`, `LOG_LEVEL`) should be left unencrypted so `git diff` remains readable:

```yaml
unencrypted_regex: "^(TZ|PUID|PGID|LOG_LEVEL|NODE_ENV|APP_ENV)$"
```

### 11.8 Putting the age private key in CI variables

If the age private key is in CI variables, a CI breach = secrets breach. **Preferred**: decrypt only on the target server that holds the key.

### 11.9 Backing up the age key to the same cloud as the secrets it encrypts

From [Will Pike](https://pikemd.com/blog/sops-age-docker-compose/):

> "The cloud backup trap is the one I think about most. My B2 bucket contains encrypted copies of everything in ~/Documents. If the age key were also in that bucket, a bucket compromise would be enough to decrypt everything in it."

---

## 12. Recommended Architecture for Guinevere

Based on this research, the recommended SOPS + age architecture for Guinevere:

```
┌─────────────────────────────────────────────────────┐
│                   DEVELOPMENT                         │
│                                                       │
│  Developer workstation                                │
│  ├── ~/.config/sops/age/keys.txt  ← age private key   │
│  ├── project/.sops.yaml           ← age public key(s) │
│  ├── project/.env.sops            ← encrypted secrets  │
│  ├── project/.envrc              ← direnv auto-load    │
│  └── sops .env.sops              ← edit secrets        │
│                                                       │
│  Git: commit .env.sops, .sops.yaml                    │
│  Gitignore: .env, keys.txt, age.key                   │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                  DEPLOYMENT                           │
│                                                       │
│  VPS / Docker                                         │
│  ├── /etc/sops/age/keys.txt      ← server private key │
│  ├── /srv/guinevere/.env.sops    ← encrypted secrets  │
│  ├── systemd service:                                 │
│  │   ExecStartPre = sops --decrypt → /run/guinevere/  │
│  │   EnvironmentFile = /run/guinevere/.env            │
│  │   ExecStart = python -m guinevere                  │
│  └── /run/guinevere/.env         ← tmpfs, RAM only    │
│                                                       │
│  Docker alternative:                                   │
│  ├── Dockerfile with sops binary installed             │
│  ├── SOPS_AGE_KEY_FILE mounted as Docker secret       │
│  └── entrypoint.sh: exec sops exec-env ... python ... │
└─────────────────────────────────────────────────────┘
```

### 12.1 Decision matrix for Guinevere

| Concern | Recommendation |
|---|---|
| **Runtime decrypt in Python** | `pydantic-settings-sops` if using Pydantic; `subprocess` + `sops` binary if not |
| **Development workflow** | SOPS + age + direnv for auto-load on `cd` |
| **Docker deployment** | `sops exec-env --same-process` in entrypoint |
| **systemd deployment** | `ExecStartPre` decrypt to `/run/` + `EnvironmentFile` |
| **Key management** | One keypair per environment; multiple recipients in `.sops.yaml` |
| **CI/CD** | Decrypt on server only (avoid key in CI) |
| **Format** | `.env.sops` for dotenv; `--input-type dotenv --output-type dotenv` |

---

## 13. Sources & References

### Official Documentation
- [getsops/sops — Official GitHub](https://github.com/getsops/sops)
- [getsops.io — Official Docs](https://getsops.io/docs/)
- [SOPS age key documentation](https://github.com/getsops/sops/blob/main/_autodocs/api-reference/age-keys.md)

### Python Libraries
- [pydantic-settings-sops](https://github.com/pavelzw/pydantic-settings-sops)
- [agenv (Python age env loader)](https://github.com/zachcheung/agenv)
- [dotenvage (Python)](https://pypi.org/project/dotenvage/)
- [sops-run (Python CLI wrapper)](https://github.com/belthesar/sops-run)

### Production Patterns (2026)
- [Secrets at Rest: SOPS + age for Docker Compose — Will Pike](https://pikemd.com/blog/sops-age-docker-compose/)
- [Linux VPS secrets management — HostMyCode](https://www.hostmycode.com/blog/linux-vps-secrets-management-sops-age-2026)
- [The Calm Way To Secrets On A VPS — DCHost](https://www.dchost.com/blog/en/the-calm-way-to-secrets-on-a-vps-gitops-with-sops-age-systemd-magic-and-rotation-you-can-sleep-on/)
- [SOPS cheatsheet — Will Pike](https://gist.github.com/pike00/6504ec5734ac7604efa3367c52904b2d)
- [No Vault? No GitOps? — Kienlt](https://blackmetalz.github.io/no-vault-no-gitops-no-problem-securing-k8s-secrets-with-sops.html)
- [Managing Git Secrets Safely — ITNotes](https://itnotes.dev/managing-git-secrets-safely-with-mozilla-sops-and-age-a-lightweight-hashicorp-vault-alternative/)
- [Stop Committing Your Secrets — JF Maes](https://jfmaes.me/blog/stop-committing-your-secrets-you-know-who-you-are/)
- [Secure Your Environment Files — Claus Malter](https://blog.cmmx.de/2025/08/27/secure-your-environment-files-with-git-sops-and-age/)
- [SOPS for Docker Compose — Michael O'Leary](https://michaeloleary.net/docker/sops-docker-compose/)

### Real-world GitHub Repositories (confirmed patterns)
- [kalisio/feathers-distributed — GitHub Actions + SOPS_AGE_KEY](https://github.com/kalisio/feathers-distributed/blob/master/.github/workflows/main.yaml)
- [timdeschryver/Sandbox — CI decrypt + test](https://github.com/timdeschryver/Sandbox/blob/main/.github/workflows/ci.yml)
- [budimanjojo/nix-config — SOPS updatekeys CI](https://github.com/budimanjojo/nix-config/blob/main/.github/workflows/update-sops-keys.yaml)
- [AndydeCleyre/colorcodebot — sops exec-env + Python](https://github.com/AndydeCleyre/colorcodebot/blob/develop/start/local.sh)
- [clan-lol/clan-core — Python SOPS key management](https://github.com/clan-lol/clan-core/blob/main/pkgs/clan-cli/clan_cli/secrets/sops.py)
- [matskevich/openclaw-infra — systemd vault script](https://github.com/matskevich/openclaw-infra/blob/main/scripts/setup-vault.sh)
- [tikibozo/plexarr — Docker sops exec-env pattern](https://github.com/tikibozo/plexarr/blob/main/scripts/common.sh)
- [ansible-collections/community.sops — Ansible integration](https://github.com/ansible-collections/community.sops)