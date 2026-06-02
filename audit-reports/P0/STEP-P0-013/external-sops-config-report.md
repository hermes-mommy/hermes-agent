# External Research Report: SOPS + age Configuration for Guinevere

**Report Date**: 2026-05-31
**Task**: STEP-P0-013 — Creating `.sops.yaml` configuration for Guinevere Python project
**Scope**: SOPS `.sops.yaml` best practices, encrypted-regex patterns, encrypted_suffix conventions, age backend, secrets directory structure, CI integration, real-world examples
**Sources**: getsops.io official docs, DeepWiki (getsops/sops), GitHub code search, blog posts, community discussions

---

## Table of Contents

1. [Official SOPS Documentation — `.sops.yaml` Structure](#1-official-sops-documentation)
2. [encrypted-regex Best Practices](#2-encrypted-regex-best-practices)
3. [encrypted_suffix & Encrypted File Suffix Conventions](#3-encrypted_suffix--encrypted-file-suffix-conventions)
4. [Secrets Directory Structure & `.gitignore` Patterns](#4-secrets-directory-structure)
5. [SOPS + age Workflow for Python Projects](#5-sops--age-workflow-for-python-projects)
6. [GitHub Actions / CI Integration](#6-github-actions--ci-integration)
7. [Real-World `.sops.yaml` Examples from Open-Source Projects](#7-real-world-examples)
8. [Common Pitfalls & Avoidance](#8-common-pitfalls)
9. [Round-Trip Testing: Encrypt → Decrypt → Verify](#9-round-trip-testing)
10. [Recommended Configuration for Guinevere](#10-recommended-configuration-for-guinevere)

---

## 1. Official SOPS Documentation — `.sops.yaml` Structure

### 1.1 File Location & Naming

SOPS looks for a `.sops.yaml` configuration file in the **current working directory and parent directories (up to 100 levels)**. The file **must** be named `.sops.yaml` — `.sops.yml` will **not** be automatically discovered (SOPS issues a warning and ignores it unless `--config .sops.yml` is passed).

**Source**: [getsops.io/docs](https://getsops.io/docs/#using-sops-yaml-conf-to-select-kms-pgp-and-age-for-new-files)

### 1.2 Configuration File Structure

The `.sops.yaml` file is parsed into a `configFile` struct containing these main sections:

```yaml
# Top-level sections
creation_rules:     # (Required) Rules determining which keys encrypt which files
destination_rules:  # (Optional) Rules for sops publish command
stores:             # (Optional) Format-specific options (YAML/JSON indent)
```

**Source**: [DeepWiki: getsops/sops configuration](https://deepwiki.com/getsops/sops/2.1-configuration)

### 1.3 Creation Rule Object

Each creation rule supports these fields:

| Field | Type | Description |
|-------|------|-------------|
| `path_regex` | string | Go regex matching file paths (relative to `.sops.yaml` location) |
| `encrypted_regex` | string | Regex: only encrypt keys matching this pattern |
| `unencrypted_regex` | string | Regex: leave keys matching this pattern **un**encrypted |
| `encrypted_suffix` | string | Encrypt keys ending with this suffix |
| `unencrypted_suffix` | string | Leave keys ending with this suffix unencrypted |
| `encrypted_comment_regex` | string | Encrypt if comment matches regex |
| `unencrypted_comment_regex` | string | Leave unencrypted if comment matches regex |
| `mac_only_encrypted` | bool | Only include encrypted values in MAC |
| `key_groups` | list | Advanced: Shamir Secret Sharing key groups |
| `shamir_threshold` | int | Number of key groups required for decryption |
| `age` | string/list | Age recipients |
| `pgp` | string/list | PGP fingerprints |
| `kms` | string/list | AWS KMS ARNs |
| `gcp_kms` | string/list | GCP KMS resource IDs |
| `azure_keyvault` | string/list | Azure Key Vault URLs |
| `hc_vault_transit_uri` | string/list | HashiCorp Vault transit URIs |
| `hckms` | list | HuaweiCloud KMS keys |

**Critical rule**: Only **one** of `{encrypted,unencrypted}_{regex,suffix,comment_regex}` can be used per rule.

### 1.4 Rule Evaluation

Rules are evaluated **sequentially, top to bottom**. The **first match wins**. This means:
- Place **more specific rules first**
- Place **catch-all rules last**
- A broad `path_regex: .*` at the top will match everything and prevent later specific rules from ever being evaluated

### 1.5 Age Backend Configuration

```yaml
creation_rules:
  - path_regex: secrets/.*\.yaml$
    age:
      - age1yt3tfqlfrwdwx0z0ynwplcr6qxcxfaqycuprpmy89nr83ltx74tqdpszlw
```

For age, SOPS looks for private keys in:
1. **Linux**: `$XDG_CONFIG_HOME/sops/age/keys.txt` → falls back to `$HOME/.config/sops/age/keys.txt`
2. **macOS**: `$XDG_CONFIG_HOME/sops/age/keys.txt` → falls back to `$HOME/Library/Application Support/sops/age/keys.txt`
3. **Windows**: `%AppData%\sops\age\keys.txt`

Override via environment variables:
- `SOPS_AGE_KEY_FILE` — path to key file
- `SOPS_AGE_KEY` — key content directly
- `SOPS_AGE_KEY_CMD` — command to output keys

**SSH key support**: SOPS + age also supports SSH keys (`ssh-ed25519`, `ssh-rsa`) as recipients. SOPS searches `SOPS_AGE_SSH_PRIVATE_KEY_FILE`, `~/.ssh/id_ed25519`, `~/.ssh/id_rsa`.

**Source**: [getsops.io/docs/#encrypting-using-age](https://getsops.io/docs/#encrypting-using-age)

---

## 2. encrypted-regex Best Practices

### 2.1 General Principles

- `encrypted_regex` matches **YAML/JSON keys** (not values) — only the values under matching keys are encrypted
- Regex is applied relative to the YAML tree path
- Use **Go-compatible regex syntax** (as SOPS is written in Go)
- Case-insensitive flag `(?i)` is supported

### 2.2 Recommended Patterns by Use Case

#### For Python/.env-style YAML configs (application secrets)

```yaml
encrypted_regex: '(?i)(api_key|api_secret|token|password|secret|private_key|discord_token|database_url|redis_url|auth_token|access_key|secret_key|client_secret|webhook|credential)'
```

This catches most common secret key names case-insensitively.

#### For Kubernetes Secrets (data/stringData)

```yaml
encrypted_regex: '^(data|stringData)$'
```

This is the **most common pattern** in Flux/GitOps repos — only encrypts the actual secret data, keeping metadata (`apiVersion`, `kind`, `metadata`) readable in diffs.

#### For catch-all rule (encrypt everything)

```yaml
# Omit encrypted_regex entirely — SOPS encrypts ALL values by default
```

#### For selective encryption with unencrypted exemptions

```yaml
unencrypted_regex: '^(TZ|PUID|PGID|LOG_LEVEL|NODE_ENV|COMPOSE_PROJECT_NAME)$'
```

Leaves non-secret config keys readable. From [Will Pike's blog](https://pikemd.com/blog/sops-age-docker-compose/).

#### Real-world pattern from toboshii/home-ops

```yaml
encrypted_regex: '((?i)(pass|secret($|[^N])|key|token|^data$|^stringData))'
```

This is a nuanced pattern that:
- Matches `pass` (covers `password`, `passphrase`)
- Matches `secret` but excludes `secretName` (`secret($|[^N])` avoids matching "secretName")
- Matches `key`, `token`
- Matches exact `data` and `stringData` for K8s Secrets

**Source**: [toboshii/home-ops/.sops.yaml](https://github.com/toboshii/home-ops/blob/main/.sops.yaml)

### 2.3 Specific Patterns for Guinevere Secrets (Python Project)

Based on Guinevere's architecture (Discord bot, PostgreSQL, Redis, Prometheus, Grafana, LLM APIs, surveillance):

| Secret Key Pattern | encrypted_regex Target | Example Keys |
|--------------------|----------------------|--------------|
| Discord tokens | `discord_token` | `DISCORD_TOKEN`, `discord_bot_token` |
| Database URLs | `database_url` | `DATABASE_URL`, `postgres_url` |
| Redis URLs | `redis_url` | `REDIS_URL`, `redis_connection_string` |
| API keys | `api_key` | `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` |
| LLM provider keys | `(llm\|ai)_(api_key\|token)` | `LLM_API_KEY`, `AI_PROVIDER_TOKEN` |
| Surveillance credentials | `surveillance_(key\|token\|secret)` | `SURVEILLANCE_API_KEY` |
| Grafana/Prometheus | `grafana_(password\|api_key)\|prometheus` | `GRAFANA_API_KEY` |
| JWT secrets | `jwt_secret\|session_secret` | `JWT_SECRET_KEY` |
| Encryption keys | `encryption_key\|sops_age_key` | `ENCRYPTION_KEY` |
| Generic secrets | `(password\|secret\|token\|key\|credential)` | Any sensitive field |

### 2.4 Regex Testing

Go regex syntax differs slightly from PCRE/JS. Key differences:
- No `\d` — use `[0-9]`
- No lookahead/lookbehind
- `(?i)` for case-insensitive is supported
- `$` for end-of-string anchoring works

Test patterns using Go's regex playground before deploying.

---

## 3. encrypted_suffix & Encrypted File Suffix Conventions

### 3.1 encrypted_suffix Usage

```yaml
creation_rules:
  - path_regex: .*\.yaml$
    encrypted_suffix: _secret
```

Only keys ending with `_secret` get encrypted. E.g., `db_password_secret` would be encrypted, `db_host` would not.

### 3.2 When to Use Suffix vs Regex

| Approach | Best For |
|----------|----------|
| `encrypted_regex` | Fine-grained key-level control, K8s Secrets, consistent key naming |
| `encrypted_suffix` | When you control key naming conventions and want explicit markers |
| `unencrypted_regex` | When you want to encrypt everything except explicitly listed keys |
| `encrypted_comment_regex` | When using YAML comments to mark secrets |

For a Python project like Guinevere, `encrypted_regex` is **recommended** over `encrypted_suffix` because you're likely using consistent key naming from environment variables (uppercase `DATABASE_URL`, `DISCORD_TOKEN`, etc.) rather than suffix conventions.

### 3.3 Encrypted File Suffix Conventions

Community conventions for naming encrypted files:

| Convention | Example | Use Case |
|-----------|---------|----------|
| `*.sops.yaml` | `secrets.sops.yaml` | **Most common** — clear marker, SOPS-aware |
| `*.sops.yml` | `config.sops.yml` | Less common (SOPS won't auto-detect .sops.yml) |
| `*.enc.yaml` | `.env.enc.yaml` | Common in CI/CD ecosystems |
| `*.env.sops` | `app.env.sops` | For dotenv-format files |
| `*secret*.sops.yaml` | `discord-secret.sops.yaml` | Kubernetes-style naming |
| `*.age-enc.yaml` | `data.age-enc.yaml` | Explicit about encryption backend |

**Recommendation for Guinevere**: Use `.sops.yaml` suffix for structured configs and `.sops.env` for dotenv-style files.

---

## 4. Secrets Directory Structure

### 4.1 Recommended Layout for Guinevere

```
guinevere/
├── .sops.yaml                          # Root config — SOPS auto-discovers this
├── .gitignore                          # Excludes decrypted plaintext files
├── secrets/
│   ├── .gitkeep                        # Ensures directory is tracked
│   ├── prod/
│   │   ├── discord.sops.yaml           # Discord bot token
│   │   ├── database.sops.yaml          # PostgreSQL credentials
│   │   ├── redis.sops.yaml             # Redis credentials
│   │   ├── llm-keys.sops.yaml          # OpenAI/Anthropic/etc API keys
│   │   ├── surveillance.sops.yaml      # Surveillance API keys
│   │   ├── monitoring.sops.yaml        # Grafana/Prometheus credentials
│   │   └── secrets.sops.env            # Dotenv-style fallback
│   └── dev/
│       ├── discord.sops.yaml
│       ├── database.sops.yaml
│       └── ...
├── scripts/
│   ├── decrypt-secrets.sh              # Helper script
│   └── encrypt-secrets.sh              # Helper script
└── .github/
    └── workflows/
        └── decrypt-deploy.yml          # CI workflow
```

Alternative layout (flatter, simpler for small projects):

```
guinevere/
├── .sops.yaml
├── .gitignore
├── secrets.sops.yaml                   # All secrets in one file (fine for small teams)
├── secrets.sops.env                    # Dotenv format alternative
```

### 4.2 `.gitignore` Patterns

```gitignore
# Decrypted/plaintext secrets — NEVER commit these
secrets/**/*.dec.yaml
secrets/**/*.decrypted.yaml
secrets/**/*.plaintext.yaml
*.dec.yaml
*.decrypted
*.plaintext

# Age private keys — NEVER commit these
*.agekey
keys.txt
age-key.txt
!*.agekey.example

# Decrypted output directories
secrets/decrypted/
secrets/plain/

# Env files that might contain plaintext secrets
.env
.env.*
!.env.example
!.env.sops
```

### 4.3 `.gitattributes` for SOPS Diffs

```gitattributes
# Show decrypted content in git diff (local only)
*.sops.yaml diff=sops
*.sops.env diff=sops
```

Configure the diff driver:
```bash
git config diff.sops.textconv "sops --decrypt"
```

This makes `git diff` show decrypted values locally, while the encrypted version is what gets committed and pushed.

### 4.4 Where to Put `.sops.yaml`

- **Repo root** — SOPS auto-discovers from CWD walking up 100 levels
- **Subdirectory** — If you pass `--config path/to/.sops.yaml` explicitly
- SOPS searches from the **working directory** (CWD), not the file's directory

---

## 5. SOPS + age Workflow for Python Projects

### 5.1 Installation

**Install `sops` binary** (not via pip — SOPS is a Go binary):

```bash
# Linux/macOS
curl -sL https://github.com/getsops/sops/releases/download/v3.13.1/sops-v3.13.1.linux.amd64 -o /usr/local/bin/sops
chmod +x /usr/local/bin/sops

# macOS via Homebrew
brew install sops age

# Windows via scoop
scoop install sops age
```

**Version note**: As of May 2026, the latest SOPS release is **v3.13.1** (released 2026-05-16).

### 5.2 Generate Age Keypair

```bash
# Generate a new keypair
age-keygen -o ~/.config/sops/age/keys.txt

# Output:
# Public key: age1yt3tfqlfrwdwx0z0ynwplcr6qxcxfaqycuprpmy89nr83ltx74tqdpszlw
# Secret key: AGE-SECRET-KEY-...
```

**NEVER** commit the private key. Protect it:
```bash
chmod 600 ~/.config/sops/age/keys.txt
```

### 5.3 Encrypt Secrets

```bash
# Using .sops.yaml rules (auto-detected)
sops --encrypt secrets/prod/database.yaml > secrets/prod/database.sops.yaml

# Encrypt in-place
sops --encrypt --in-place secrets/prod/database.yaml

# For dotenv files
sops --encrypt --input-type dotenv --output-type dotenv .env > .env.sops
```

### 5.4 Decrypt Secrets

```bash
# Decrypt to stdout (safe — no file written)
sops --decrypt secrets/prod/database.sops.yaml

# Decrypt to file (careful — plaintext on disk)
sops --decrypt secrets/prod/database.sops.yaml > secrets/prod/database.yaml

# Decrypt dotenv
sops --decrypt --output-type dotenv secrets.sops.env > .env
```

### 5.5 Edit Encrypted Files Safely

```bash
# Opens in $EDITOR, decrypts on open, re-encrypts on save
sops secrets/prod/database.sops.yaml
```

### 5.6 Python Integration Patterns

#### Pattern A: Decrypt at deploy time (recommended for CI)

Decrypt secrets as part of deployment, never at runtime. The decrypted values are injected as environment variables or written to a temp file.

```bash
# In deployment script
export $(sops --decrypt --output-type dotenv secrets.sops.env | xargs)
python app.py
```

#### Pattern B: pydantic-settings-sops

For Python projects using pydantic, [pavelzw/pydantic-settings-sops](https://github.com/pavelzw/pydantic-settings-sops) provides native SOPS integration:

```python
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from pydantic_settings_sops import SOPSConfigSettingsSource

class Settings(BaseSettings):
    model_config = SettingsConfigDict(yaml_file="secrets.sops.yaml")
    
    discord_token: str
    database_url: str
    redis_url: str
    openai_api_key: str
    
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

Requires `SOPS_AGE_KEY` or `SOPS_AGE_KEY_FILE` to be set at runtime.

#### Pattern C: Runtime decryption with env fallback

```python
import os
import subprocess
import json
from pathlib import Path

def load_sops_secrets(sops_path: str) -> dict:
    """Decrypt SOPS file and return as dict."""
    result = subprocess.run(
        ["sops", "--decrypt", "--output-type", "json", sops_path],
        capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)

# Usage
if os.path.exists("secrets.sops.yaml"):
    secrets = load_sops_secrets("secrets.sops.yaml")
    os.environ.update(secrets)
```

#### Pattern D: himitsubako library

For a multi-backend Python credential abstraction (SOPS + age + macOS Keychain + Bitwarden + direnv), see [himitsubako](https://pypi.org/project/himitsubako/0.9.0/). It provides `hmb init` that scaffolds the entire setup.

---

## 6. GitHub Actions / CI Integration

### 6.1 Basic Workflow: Install SOPS, Decrypt, Deploy

```yaml
name: Deploy with Decrypted Secrets

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install SOPS
        run: |
          SOPS_VERSION="v3.13.1"
          curl -sLO "https://github.com/getsops/sops/releases/download/${SOPS_VERSION}/sops-${SOPS_VERSION}.linux.amd64"
          chmod +x sops-${SOPS_VERSION}.linux.amd64
          sudo mv sops-${SOPS_VERSION}.linux.amd64 /usr/local/bin/sops

      - name: Install age
        run: |
          sudo apt-get update && sudo apt-get install -y age

      - name: Decrypt secrets
        env:
          SOPS_AGE_KEY: ${{ secrets.SOPS_AGE_KEY }}
        run: |
          sops --decrypt secrets/prod/database.sops.yaml > /tmp/database.yaml
          sops --decrypt --output-type dotenv secrets/prod/secrets.sops.env > /tmp/.env

      - name: Deploy
        run: |
          # Source decrypted env
          source /tmp/.env
          python deploy.py
```

### 6.2 Using a GitHub Action for SOPS

```yaml
- name: Install SOPS
  uses: mdgreenwald/mozilla-sops-action@v1.4.1
  with:
    file: secrets.enc.yaml
```

Or use the `sops-exec-action` for running commands with decrypted env:

```yaml
- uses: LNSD/sops-exec-action@v1
  env:
    SOPS_AGE_KEY: ${{ secrets.AGE_SECRET_KEY }}
  with:
    env_file: .env.sops
    run: |
      python -m pytest
      python app.py
```

### 6.3 CI Best Practices

1. **Store age private key as GitHub Secret**: `SOPS_AGE_KEY` → raw key content
2. **Use `SOPS_AGE_KEY` env var** (not a file) for CI — avoids writing key to disk
3. **Never pipe decrypted secrets to logs**: Redact output or use `sops --decrypt` piped directly to app
4. **Use separate age keys per environment**: Dev key for dev, prod key for prod
5. **Validate encryption in CI** (without private key):

```yaml
- name: Validate SOPS encryption format
  run: |
    for f in $(find secrets -name '*.sops.yaml'); do
      # Check that file has sops metadata
      grep -q "sops:" "$f" || { echo "Missing sops metadata in $f"; exit 1; }
      # Check that values are encrypted
      grep -q "ENC\[" "$f" || { echo "Plaintext value found in $f"; exit 1; }
    done
```

### 6.4 GitLab CI Example

```yaml
deploy:
  image: alpine:latest
  before_script:
    - apk add --no-cache sops age
    - export SOPS_AGE_KEY="$SOPS_AGE_KEY"
  script:
    - sops --decrypt secrets.sops.yaml > /tmp/secrets.yaml
    - python deploy.py
```

---

## 7. Real-World Examples

### 7.1 toboshii/home-ops (GitOps, Flux)

```yaml
creation_rules:
  - path_regex: provision/.*\.sops\.ya?ml
    unencrypted_regex: "^(kind)$"
    key_groups:
      - age:
          - age1nfn3vxpsgm49ljgs8kxevga9makhh9aply6ddgf9wplsfuwpcv2qzmqatc
  - path_regex: cluster/.*\.sops\.ya?ml
    encrypted_regex: '((?i)(pass|secret($|[^N])|key|token|^data$|^stringData))'
    key_groups:
      - age:
          - age1nfn3vxpsgm49ljgs8kxevga9makhh9aply6ddgf9wplsfuwpcv2qzmqatc
  - path_regex: .*\.sops\.ya?ml
    key_groups:
      - age:
          - age1nfn3vxpsgm49ljgs8kxevga9makhh9aply6ddgf9wplsfuwpcv2qzmqatc
  - path_regex: .*\.sops\.toml
    key_groups:
      - age:
          - age1nfn3vxpsgm49ljgs8kxevga9makhh9aply6ddgf9wplsfuwpcv2qzmqatc
```

**Notable**: YAML anchors for key groups, nuanced `encrypted_regex` with negative lookahead workaround, separate rules for different file types.

**Source**: [toboshii/home-ops/.sops.yaml](https://github.com/toboshii/home-ops/blob/main/.sops.yaml)

### 7.2 budimanjojo/home-cluster (GitOps, Flux, Talos)

```yaml
creation_rules:
  - encrypted_regex: '^(data|stringData|caBundle)$'
    path_regex: 'cluster/.*\.sops\.ya?ml$'
    age: >-
      age1zeqkpfz7e3s207ynea0z0auc0mrct0pc7w4sh6j3d0c4qac3dahqj9ufdg
  - path_regex: 'talos/.*\.sops\.ya?ml$'
    age: >-
      age1zeqkpfz7e3s207ynea0z0auc0mrct0pc7w4sh6j3d0c4qac3dahqj9ufdg
  - path_regex: '.*-secret\.sops\.ya?ml$'
    age: >-
      age1zeqkpfz7e3s207ynea0z0auc0mrct0pc7w4sh6j3d0c4qac3dahqj9ufdg
```

**Notable**: Block scalar (`>-`) for multiline readability, includes `caBundle` in encrypted fields, separate rules for Talos configs, `-secret.sops.yaml` naming convention.

**Source**: [budimanjojo/home-cluster/.sops.yaml](https://github.com/budimanjojo/home-cluster/blob/main/.sops.yaml)

### 7.3 clearlybaffled/homelab (with YAML anchors)

```yaml
keys_groups: &default_keys
  - age:
    - &age age1e764qpphm5nlzp04qf6zcq8f400390d9wmzramq84hqp60k6qyvqsvgg45

creation_rules:
  - path_regex: .*\.sops\.yaml
    encrypted_regex: "^(data|stringData)$"
    key_groups: *default_keys
  - key_groups: *default_keys
```

**Notable**: Uses YAML anchors (`&default_keys` / `*default_keys`) to avoid repeating the age key across rules. Catch-all rule at bottom with no `path_regex` (matches everything).

**Source**: [clearlybaffled/homelab/.sops.yaml](https://github.com/clearlybaffled/homelab/blob/main/.sops.yaml)

### 7.4 Docker Compose + dotenv Pattern (Will Pike's blog)

```yaml
creation_rules:
  - path_regex: .*\.env(\.sops)?$
    input_type: dotenv
    output_type: dotenv
    age: &age_key "age1pq1rlg3cuef3cpp0zfgg4me2kpgkkwpy5tj84hr89zsgc8l3jkq6avr48..."
    unencrypted_regex: "^(TZ|PUID|PGID|UMASK|PGDATA|LOG_LEVEL|NODE_ENV|COMPOSE_PROJECT_NAME)$"
  - path_regex: .*\.(pem|key)(\.sops)?$
    age: *age_key
  - path_regex: .*credentials(\.sops)?\.json$
    age: *age_key
    encrypted_regex: "TunnelSecret"
```

**Notable**: `unencrypted_regex` to keep non-secret config readable, `input_type: dotenv` / `output_type: dotenv` for `.env` files, YAML anchor `&age_key`, `.sops` suffix for binary files.

**Source**: [pikemd.com/blog/sops-age-docker-compose/](https://pikemd.com/blog/sops-age-docker-compose/)

### 7.5 Multi-Environment with YAML Anchors (SOPS documentation)

```yaml
creation_rules:
  # Production — most restricted
  - path_regex: environments/production/.*\.yaml$
    age: age1prodkey...
    encrypted_regex: ^(data|stringData)$
  # Staging — different key
  - path_regex: environments/staging/.*\.yaml$
    age: age1stagingkey...
    encrypted_regex: ^(data|stringData)$
  # Development — dev key
  - path_regex: environments/development/.*\.yaml$
    age: age1devkey...
    encrypted_regex: ^(data|stringData)$
```

**Source**: [oneuptime.com/blog](https://oneuptime.com/blog/post/2026-03-13-how-to-configure-sops-creation-rules-in-sops-yaml-for-flux/view)

---

## 8. Common Pitfalls

### 8.1 Wrong Age Key Path

**Problem**: SOPS can't find the private key.
**Solution**: Set `SOPS_AGE_KEY_FILE` or `SOPS_AGE_KEY` explicitly. Check default key locations (`~/.config/sops/age/keys.txt`).

```bash
export SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt
```

### 8.2 Missing encrypted_regex — Entire File Encrypted

**Problem**: Without `encrypted_regex`, SOPS encrypts **all** values, including metadata like `apiVersion`, `kind`, `name`. This breaks `kubectl diff` and makes code review useless.

**Solution**: Always specify `encrypted_regex` for structured files. For GitOps/K8s: `encrypted_regex: '^(data|stringData)$'`.

### 8.3 Double-Encryption

**Problem**: Running `sops --encrypt` on an already-encrypted file wraps the encrypted content in another layer.
**Solution**: Always encrypt from plaintext source. Use `sops edit` (opens decrypted, re-encrypts on save) instead of `sops --encrypt` on previously encrypted files.

### 8.4 Committing the Private Key

**Problem**: Age private key (`AGE-SECRET-KEY-...`) ends up in the repo.
**Solution**: Add `*.agekey`, `keys.txt`, `age-key.txt` to `.gitignore`. Never store private keys in the repo. Use environment variables or secret managers.

### 8.5 Wrong Recipient Public Key

**Problem**: Encrypted to wrong age public key → nobody can decrypt.
**Solution**: Keep recipients in `.sops.yaml`, not in memory. Test decryption immediately after encrypting. Use `sops updatekeys` to fix.

### 8.6 Forgetting to Commit `.sops.yaml`

**Problem**: `.sops.yaml` not in repo → team members and CI can't encrypt new files.
**Solution**: Commit `.sops.yaml` to the repository. It only contains **public** keys, which are safe to share.

### 8.7 Broad `path_regex` Catch-All First

**Problem**: Catch-all rule at top matches everything, preventing specific rules from ever being reached.
**Solution**: Order rules most-specific-first. Catch-all goes last (or omitted).

### 8.8 `.sops.yml` Instead of `.sops.yaml`

**Problem**: File named `.sops.yml` won't be auto-discovered.
**Solution**: Name it exactly `.sops.yaml`. Pass `--config .sops.yml` only if you have a strong reason.

### 8.9 Decrypted Files in CI Artifacts

**Problem**: Decrypted secrets persist in CI artifacts, logs, or cache layers.
**Solution**: Pipe decrypted output directly to the consuming process. Use `/tmp/` for temp files. Clean up after use. Never upload decrypted files as artifacts.

---

## 9. Round-Trip Testing

### 9.1 Manual Round-Trip Test

```bash
# Create a test secrets file
cat > /tmp/test-secret.yaml << 'EOF'
database_url: "postgresql://user:pass@localhost:5432/db"
discord_token: "my.discord.bot.token"
api_key: "sk-abc123"
EOF

# Encrypt
sops --encrypt /tmp/test-secret.yaml > /tmp/test-secret.sops.yaml

# Verify encrypted file has sops metadata
grep -q "sops:" /tmp/test-secret.sops.yaml && echo "✓ Has sops metadata"
grep -q "ENC\[" /tmp/test-secret.sops.yaml && echo "✓ Values are encrypted"

# Decrypt back
sops --decrypt /tmp/test-secret.sops.yaml > /tmp/test-secret-decrypted.yaml

# Verify round-trip (plaintext matches)
diff /tmp/test-secret.yaml /tmp/test-secret-decrypted.yaml && echo "✓ Round-trip: PASS"

# Verify encrypted_regex only encrypts target keys
sops --decrypt /tmp/test-secret.sops.yaml | grep -q "database_url:" && echo "✓ Key names preserved"
```

### 9.2 Automated Round-Trip Test Script

```bash
#!/bin/bash
# test-sops-roundtrip.sh
set -euo pipefail

TEST_FILE=$(mktemp)
ENC_FILE=$(mktemp)
DEC_FILE=$(mktemp)
trap 'rm -f "$TEST_FILE" "$ENC_FILE" "$DEC_FILE"' EXIT

# Create test data with various secret patterns
cat > "$TEST_FILE" << 'EOF'
discord_token: "my.discord.token"
database_url: "postgresql://user:pass@localhost:5432/guinevere"
redis_url: "redis://:password@localhost:6379/0"
openai_api_key: "sk-proj-abc123def456"
surveillance_api_key: "sv-xyz789"
grafana_password: "grafana-secret-123"
jwt_secret: "jwt-signing-key-here"
log_level: "INFO"  # Non-secret, should stay readable if using unencrypted_regex
EOF

echo "=== Original ==="
cat "$TEST_FILE"

echo ""
echo "=== Encrypting ==="
sops --encrypt "$TEST_FILE" > "$ENC_FILE"
echo "Encrypted written to $ENC_FILE"
head -5 "$ENC_FILE"

echo ""
echo "=== Decrypting ==="
sops --decrypt "$ENC_FILE" > "$DEC_FILE"

echo ""
echo "=== Comparing ==="
if diff "$TEST_FILE" "$DEC_FILE"; then
    echo "✓ ROUND-TRIP: PASS — Encrypted and decrypted content matches"
    exit 0
else
    echo "✗ ROUND-TRIP: FAIL — Content mismatch"
    exit 1
fi
```

### 9.3 CI Round-Trip Validation

```yaml
- name: Validate SOPS round-trip
  env:
    SOPS_AGE_KEY: ${{ secrets.SOPS_AGE_KEY }}
  run: |
    for f in $(find secrets -name '*.sops.yaml'); do
      echo "Testing: $f"
      # Decrypt and verify it produces valid YAML
      sops --decrypt "$f" | python -c "import yaml,sys; yaml.safe_load(sys.stdin); print('  Valid YAML')"
    done
```

---

## 10. Recommended Configuration for Guinevere

Based on all research, here is the recommended `.sops.yaml` for Guinevere:

```yaml
# .sops.yaml — Guinevere Secrets Configuration
# SOPS + age encryption with fine-grained encrypted_regex

# YAML anchor for the age public key (replace with actual key)
x-guinevere-age: &guinevere-age
  - age1yt3tfqlfrwdwx0z0ynwplcr6qxcxfaqycuprpmy89nr83ltx74tqdpszlw

creation_rules:
  # Rule 1: Production secrets — strictest encrypted_regex
  - path_regex: secrets/prod/.*\.sops\.yaml$
    encrypted_regex: >-
      (?i)(discord_token|database_url|redis_url|api_key|api_secret|
      token|password|secret|private_key|jwt_secret|session_secret|
      encryption_key|auth_token|access_key|secret_key|client_secret|
      webhook|credential|surveillance|grafana|prometheus|
      openai|anthropic|llm_)
    key_groups: *guinevere-age

  # Rule 2: Development secrets — same regex, separate key if desired
  - path_regex: secrets/dev/.*\.sops\.yaml$
    encrypted_regex: >-
      (?i)(discord_token|database_url|redis_url|api_key|api_secret|
      token|password|secret|private_key|jwt_secret|session_secret|
      encryption_key)
    key_groups: *guinevere-age

  # Rule 3: Dotenv files — preserve key=value structure
  - path_regex: .*\.sops\.env$
    input_type: dotenv
    output_type: dotenv
    encrypted_regex: >-
      (?i)(discord_token|database_url|redis_url|api_key|token|
      password|secret|private_key|jwt_secret|credential)
    key_groups: *guinevere-age

  # Rule 4: Catch-all for any other .sops.yaml files
  - path_regex: .*\.sops\.yaml$
    encrypted_regex: >-
      (?i)(discord_token|database_url|redis_url|api_key|token|
      password|secret|private_key|credential)
    key_groups: *guinevere-age
```

### Explanation of Design Decisions

1. **YAML anchor (`&guinevere-age`)**: avoids repeating the age public key across rules. Makes key rotation a single-line change.

2. **Most-specific-first ordering**: `secrets/prod/` matches before `secrets/dev/` before `*.sops.env` before catch-all.

3. **Production has stricter regex**: includes surveillance/Grafana/Prometheus/LLM keys that dev might not need.

4. **Dotenv rule uses `input_type: dotenv`**: preserves the `KEY=value` format rather than converting to YAML.

5. **Broad but targeted `encrypted_regex`**: catches all Guinevere-relevant secret patterns while leaving metadata and non-secret config keys readable.

6. **No `unencrypted_regex`**: keeping the config simple — if a key doesn't match the encrypted pattern, it stays plaintext by default.

### Setup Checklist

```bash
# 1. Generate age keypair
age-keygen -o ~/.config/sops/age/keys.txt

# 2. Copy public key into .sops.yaml (replace placeholder above)

# 3. Create secrets directory structure
mkdir -p secrets/prod secrets/dev

# 4. Encrypt first secret file
sops --encrypt secrets.yaml > secrets/prod/secrets.sops.yaml

# 5. Verify round-trip
sops --decrypt secrets/prod/secrets.sops.yaml | diff - secrets.yaml

# 6. Add plaintext source to .gitignore
echo "secrets/**/*.yaml" >> .gitignore
# (but NOT secrets/**/*.sops.yaml)

# 7. Set up git diff driver
git config diff.sops.textconv "sops --decrypt"
```

---

## Sources Index

| Source | URL | Key Insights |
|--------|-----|--------------|
| getsops.io official docs | https://getsops.io/docs/ | `.sops.yaml` structure, age backend, creation rules |
| DeepWiki: getsops/sops config | https://deepwiki.com/getsops/sops/2.1-configuration | Config file location, rule evaluation, key groups |
| GitHub: getsops/sops | https://github.com/getsops/sops | Latest releases (v3.13.1), 21.8k stars |
| toboshii/home-ops | https://github.com/toboshii/home-ops | Real-world nuanced encrypted_regex pattern |
| budimanjojo/home-cluster | https://github.com/budimanjojo/home-cluster | Block scalar, -secret.sops.yaml naming |
| clearlybaffled/homelab | https://github.com/clearlybaffled/homelab | YAML anchors for DRY key groups |
| pydantic-settings-sops | https://github.com/pavelzw/pydantic-settings-sops | Python native SOPS integration |
| DevOpsil SOPS guide | https://devopsil.com/articles/2026-03-22-sops-encrypted-secrets-gitops | CI/CD patterns, multi-env configs |
| Will Pike's blog | https://pikemd.com/blog/sops-age-docker-compose/ | `unencrypted_regex`, dotenv patterns |
| Hey! Linux blog | https://blog.heylinux.com/en/2026/02/using-sops-age-to-encrypt-files/ | encrypted_regex with case-insensitive flag |
| OneUptime blog | https://oneuptime.com/blog/post/2026-03-13-how-to-configure-sops-creation-rules-in-sops-yaml-for-flux/view | Creation rules, Flux integration |
| HostMyCode blog | https://www.hostmycode.com/blog/linux-vps-secrets-management-sops-age-2026 | VPS secrets, .gitignore patterns |
| cgoolsby/sops-for-companies | https://github.com/cgoolsby/sops-for-companies | Enterprise patterns, CI/CD workflows |
| LNSD/sops-exec-action | https://github.com/LNSD/sops-exec-action | GitHub Action for SOPS exec |
| SafeOps Academy | https://safeops.work/course/chapter-03-secrets-management/ | Multi-org secrets, path_regex patterns |