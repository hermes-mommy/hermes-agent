# External Research: Age Key Safety — Generation, Storage, Backup & Access Control

**Task**: STEP-P0-012 — Generate age encryption key pair for SOPS
**Research Date**: 2026-05-31
**Scope**: Best practices for age key lifecycle with focus on Guinevere project (Ubuntu 24.04 LTS VPS)
**Risk Level**: **HIGH** — private key compromise breaks all encryption
**Mandate**: NEVER expose the private key

---

## Table of Contents

1. [Age Tool Overview & Version Availability](#1-age-tool-overview--version-availability)
2. [Key Generation Best Practices](#2-key-generation-best-practices)
3. [SOPS Age Key Discovery & Storage Locations](#3-sops-age-key-discovery--storage-locations)
4. [File Permissions & Access Control](#4-file-permissions--access-control)
5. [Backup Strategies](#5-backup-strategies)
6. [Key Rotation & Revocation Procedures](#6-key-rotation--revocation-procedures)
7. [Audit Logging for Key Access](#7-audit-logging-for-key-access)
8. [What to NEVER Do](#8-what-to-never-do)
9. [Round-Trip Encryption Test Procedure](#9-round-trip-encryption-test-procedure)
10. [Recommended Key Naming Conventions](#10-recommended-key-naming-conventions)
11. [Summary of Recommendations for Guinevere](#11-summary-of-recommendations-for-guinevere)
12. [Sources](#12-sources)

---

## 1. Age Tool Overview & Version Availability

### What is age?

**age** (A Good Encryption) is a simple, modern, and secure file encryption tool by Filippo Valsorda and Ben Cartwright-Cox. It features:

- Small explicit keys (X25519 or ML-KEM-768+X25519 hybrid)
- No config options
- UNIX-style composability (pipes, stdin/stdout)
- SSH key compatibility
- Post-quantum support via `-pq` flag (v1.3.0+)

**Source**: [GitHub — FiloSottile/age](https://github.com/FiloSottile/age)

### Ubuntu 24.04 (Noble) — Package Availability

| Source | Version | PQ Support | Command |
|--------|---------|------------|---------|
| `apt` (universe) | **1.1.1-1ubuntu0.24.04.3** | ❌ No | `sudo apt install age` |
| GitHub binary | **v1.3.1** (latest) | ✅ Yes (`-pq`) | Manual install |

**CRITICAL FINDING**: The Ubuntu 24.04 apt repository ships `age v1.1.1`, which does **NOT** support post-quantum keys (`-pq` flag). For post-quantum support, install the **latest binary from GitHub**.

**Source**: [Ubuntu Noble age package details](https://packages.ubuntu.com/source/noble/age), [knuth.info analysis](https://knuth.info/posts/the-solo-stack/dotfiles/why-apt-install-age-isnt-enough/)

### Recommended Installation (v1.3.1+)

```bash
# Remove outdated apt version if present
sudo apt remove age

# Download and install latest binary
AGE_VERSION="1.3.1"
cd /tmp
curl -LO "https://github.com/FiloSottile/age/releases/download/v${AGE_VERSION}/age-v${AGE_VERSION}-linux-amd64.tar.gz"
tar xzf "age-v${AGE_VERSION}-linux-amd64.tar.gz"
sudo mv age/age age/age-keygen /usr/local/bin/
rm -rf age "age-v${AGE_VERSION}-linux-amd64.tar.gz"

# Verify
age-keygen --version   # Expected: v1.3.1
```

**Source**: [FiloSottile/age README — Installation](https://github.com/FiloSottile/age?tab=readme-ov-file#installation)

> **Note**: Verify the downloaded binary via [Sigsum proofs](https://github.com/FiloSottile/age/blob/main/SIGSUM.md).

---

## 2. Key Generation Best Practices

### Standard X25519 Key

```bash
age-keygen -o ~/.config/sops/age/keys.txt
```

Output format:
```
# created: 2026-05-31T14:00:00+07:00
# public key: age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p
AGE-SECRET-KEY-1QP9GM0M3CU...
```

### Post-Quantum Hybrid Key (ML-KEM-768 + X25519) — RECOMMENDED

```bash
age-keygen -pq -o ~/.config/sops/age/keys.txt
```

Output format:
```
# created: 2026-05-31T14:00:00+07:00
# public key: age1pq197gewjr6cswan...xpgettdwp
AGE-SECRET-KEY-PQ-1...
```

**Why PQ?** Post-quantum ML-KEM-768 (CRYSTALS-Kyber) + X25519 hybrid ensures protection against future quantum attacks. The private key is ~2,089 bytes (fits in a single QR code v40).

**Source**: [FiloSottile/age README — Post-quantum keys](https://github.com/FiloSottile/age#post-quantum-keys), [coldkey tool](https://github.com/pike00/coldkey)

### Generation Security Principles

| Principle | Practice |
|-----------|----------|
| **Entropy source** | `age-keygen` uses OS randomness (`/dev/urandom`), which is FIPS 140-2/3 compliant |
| **No custom RNG** | Never roll your own random number generator |
| **Generate locally** | Generate on the target machine, never on a shared/cloud system |
| **No network** | Air-gap generation when possible (`--network none` in Docker) |
| **Memory safety** | `mlockall()` prevents key material from being swapped to disk |
| **File permissions** | Immediately `chmod 600` after generation |

**Source**: [OWASP Key Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet), [NIST SP 800-133r3](https://csrc.nist.gov/News/2026/recommendation-for-cryptographic-key-generation)

### Dockerized Generation (Coldkey Pattern)

For maximum isolation during generation, use a pattern inspired by `coldkey`:

```bash
docker run --rm \
  --network none \
  --read-only \
  --cap-drop ALL \
  --cap-add IPC_LOCK \
  --security-opt no-new-privileges:true \
  --tmpfs /tmp:rw,noexec,nosuid,size=10m \
  -v "$(pwd)/output:/output:rw" \
  distroless/static:nonroot \
  age-keygen -o /output/keys.txt
```

**Source**: [pike00/coldkey — Security model](https://github.com/pike00/coldkey#security-model)

---

## 3. SOPS Age Key Discovery & Storage Locations

### SOPS Identity Discovery Order

SOPS searches for age identities in the following **order** during decryption:

```
1.  SOPS_AGE_SSH_PRIVATE_KEY_FILE env var
2.  SOPS_AGE_SSH_PRIVATE_KEY_CMD env var
3.  ~/.ssh/id_ed25519  (fallback)
4.  ~/.ssh/id_rsa      (fallback)
5.  SOPS_AGE_KEY env var           (direct key content as string)
6.  SOPS_AGE_KEY_FILE env var      (path to key file)
7.  SOPS_AGE_KEY_CMD env var       (command that outputs keys)
8.  $XDG_CONFIG_HOME/sops/age/keys.txt       (Linux, if XDG_CONFIG_HOME is set)
9.  $HOME/.config/sops/age/keys.txt          (Linux, fallback)
10. $HOME/Library/Application Support/sops/age/keys.txt  (macOS)
11. %AppData%\sops\age\keys.txt              (Windows)
```

**Source**: [getsops/sops — age/keysource.go](https://github.com/getsops/sops/blob/main/age/keysource.go)

### Environment Variables Reference

| Variable | Description | Security Level |
|----------|-------------|----------------|
| `SOPS_AGE_KEY` | Private key as a string (inline) | ⚠️ **RISKY** — leaks in process listings, shell history, CI logs |
| `SOPS_AGE_KEY_FILE` | Path to the key file | ✅ **RECOMMENDED** — file-backed, predictable |
| `SOPS_AGE_KEY_CMD` | Command that outputs the key | ✅ **BEST** — can integrate with secret managers, vaults |
| `SOPS_AGE_RECIPIENT` | Passed to `SOPS_AGE_KEY_CMD` to specify which key to return | ✅ Contextual |
| `SOPS_AGE_RECIPIENTS` | Comma-separated list of recipients (public keys) | ✅ Safe (public keys) |
| `SOPS_AGE_SSH_PRIVATE_KEY_FILE` | Path to SSH private key | ✅ Alternative |
| `SOPS_AGE_SSH_PRIVATE_KEY_CMD` | Command that outputs SSH private key | ✅ Alternative |

**Source**: [getsops/sops — age/keysource.go constants](https://github.com/getsops/sops/blob/main/age/keysource.go#L10-L35)

### Recommended Storage Location for Guinevere

**Primary path**: `~/.config/sops/age/keys.txt`

This is the **default SOPS discovery path** on Linux. Storing here means SOPS finds the key automatically — no env var needed.

**Alternative** (if decoupling from SOPS): `~/.config/age/key.txt`

If the key is shared with other tools (chezmoi, etc.), some practitioners prefer a canonical location and use explicit env vars to point each tool to it.

**Source**: [knuth.info — Why apt install age Isn't Enough](https://knuth.info/posts/the-solo-stack/dotfiles/why-apt-install-age-isnt-enough/), [SOPS official docs](https://getsops.io/docs/)

---

## 4. File Permissions & Access Control

### Essential Permissions

| File | Permission | Rationale |
|------|-----------|-----------|
| Private key (`keys.txt`) | **`0600`** (owner read/write only) | Prevents unauthorized users/processes from reading |
| Public key (`recipient.txt`) | **`0644`** (world-readable) | Safe to share, needed for encryption |
| Encrypted `.env` files | **`0600`** or **`0640`** | Decrypted versions must never be world-readable |
| Decrypted secrets at rest | **`0600`** root-owned | Only root and the target service should read |

### Setting Permissions

```bash
# After key generation — IMMEDIATELY
chmod 600 ~/.config/sops/age/keys.txt

# Public key (extracted) — can be shared
grep '^# public key:' ~/.config/sops/age/keys.txt | cut -d' ' -f4 > ~/.config/sops/age/recipient.txt
chmod 644 ~/.config/sops/age/recipient.txt

# Decrypted secrets on VPS
sudo chown root:root /etc/guinevere/secrets.env
sudo chmod 600 /etc/guinevere/secrets.env
```

### Access Control Matrix

| Actor | Private Key | Public Key | Encrypted SOPS Files | Decrypted Secrets |
|-------|-------------|------------|---------------------|-------------------|
| Key owner (Faiz) | ✅ Read | ✅ Read | ✅ Read | ✅ Read |
| VPS root | ❌ Deny (key off-server) | ✅ Read | ✅ Read | ✅ Read (deployment) |
| App service user | ❌ Deny | ❌ Deny | ❌ Deny | ✅ Read (via systemd) |
| CI/CD pipeline | ❌ Deny (use SOPS_AGE_KEY_CMD) | ✅ Read | ✅ Read | ✅ Read (encrypted) |
| Other users | ❌ Deny | ✅ Read | ❌ Deny | ❌ Deny |

**Source**: [HostMyCode — Linux VPS secrets rotation with sops + age](https://www.hostmycode.com/blog/linux-vps-secrets-rotation-sops-age-practical-workflow-2026), [ITNotes — Managing Git Secrets with SOPS and Age](https://itnotes.dev/managing-git-secrets-safely-with-mozilla-sops-and-age-a-lightweight-hashicorp-vault-alternative/)

---

## 5. Backup Strategies

### The Cold Key Problem

> **Critical**: The age private key must NEVER be backed up to the same cloud storage that the key encrypts. If your backup bucket is encrypted with the same key that protects the backup, you have a circular dependency — lose the key and you lose all access.

**Source**: [pike00 — SOPS + age cheatsheet](https://gist.github.com/pike00/6504ec5734ac7604efa3367c52904b2d)

### Recommended Backup Tiers

#### Tier 1: Paper Backup (Cold Storage) — PRIMARY

Use **coldkey** or manual QR code generation for a printable backup.

```bash
# Using coldkey (Docker-based, no network)
git clone https://github.com/pike00/coldkey.git
cd coldkey

# Generate new key + paper backup
just docker-run

# Or backup existing key to paper
just docker-backup ~/.config/sops/age/keys.txt
```

Paper backup contents:
- Raw key text (monospace for manual transcription)
- QR code(s) with capacity annotation
- SHA-256 checksum for verification
- Step-by-step recovery instructions

**Procedure**:
1. Print the HTML document
2. Store in a fireproof safe (home + bank safe deposit box)
3. Verify checksum on print vs. original key
4. Label with: "Guinevere SOPS age key — generated YYYY-MM-DD"

**Source**: [pike00/coldkey](https://github.com/pike00/coldkey)

#### Tier 2: Password Manager — SECONDARY

Store the full private key content in a password manager entry:

| Manager | Suitability |
|---------|-------------|
| **Bitwarden** | ✅ Encrypted attachment or secure note |
| **1Password** | ✅ Document item type |
| **KeePassXC** | ✅ Local encrypted database |
| **LastPass** | ⚠️ Use with caution (recent breaches) |

**Source**: [ITNotes — SOPS tips](https://itnotes.dev/managing-git-secrets-safely-with-mozilla-sops-and-age-a-lightweight-hashicorp-vault-alternative/)

#### Tier 3: Shamir Secret Sharing (Advanced)

Split the key into N shares where M are required for reconstruction:

```bash
# Using ssss (Shamir's Secret Sharing Scheme)
# Requires the key to be hex-encoded first
age-keygen -o /tmp/key.txt
xxd -p /tmp/key.txt > /tmp/key.hex
ssss-split -t 3 -n 5 < /tmp/key.hex
# Distribute 5 shares to trusted individuals/locations
# Any 3 can reconstruct
```

**Not recommended for Guinevere v1** — adds complexity. Paper backup + password manager is sufficient.

#### Tier 4: Hardware Token (Future)

- **YubiKey** via [`age-plugin-yubikey`](https://github.com/str4d/age-plugin-yubikey)
- Key never leaves the hardware token
- PIV slot storage
- Requires physical possession to decrypt

### What NOT to Do for Backup

| ❌ Bad Practice | Why |
|----------------|-----|
| Backup to same cloud as encrypted data | Circular dependency — lose key, lose all |
| Email the key to yourself | Email is not encrypted at rest by default |
| Store in unencrypted USB drive | Physical theft = full compromise |
| Store in repo `.gitignore`'d file | Git history still has it if ever committed |
| Print without checksum | Transcription errors are silent data loss |

---

## 6. Key Rotation & Revocation Procedures

### Scheduled Rotation (Quarterly)

Age keys themselves don't expire, but access control should be reviewed:

| Trigger | Action |
|---------|--------|
| Time-based (quarterly) | Re-encrypt all secrets to same key (re-wraps data key) |
| Team member offboarding | Remove their public key from `.sops.yaml`, re-encrypt |
| CI/CD identity change | Generate new CI key, re-encrypt |
| Post-incident | Emergency rotation (see below) |

### Rotation Procedure (Compromise Suspected)

```bash
# 1. Generate new keypair
age-keygen -pq -o ~/.config/sops/age/keys-new.txt
chmod 600 ~/.config/sops/age/keys-new.txt

# 2. Extract new public key
grep '^# public key:' ~/.config/sops/age/keys-new.txt

# 3. Update .sops.yaml with new recipient
#    (replace age: entry with new public key)

# 4. Re-encrypt ALL .sops files
for f in $(find . -name '*.sops.yaml' -o -name '*.sops.env'); do
  sops decrypt "$f" | sops encrypt /dev/stdin > "$f.new"
  mv "$f.new" "$f"
done

# 5. Verify every file decrypts with new key
for f in $(find . -name '*.sops.yaml' -o -name '*.sops.env'); do
  sops decrypt "$f" > /dev/null || echo "FAIL: $f"
done

# 6. Only after verification, swap keys
mv ~/.config/sops/age/keys-new.txt ~/.config/sops/age/keys.txt

# 7. Verify one more time
just secrets verify

# 8. Update backups with new key
#     - Update paper backup
#     - Update password manager entry
#     - Destroy old backup material
```

**Source**: [pike00 — SOPS + age rotation cheatsheet](https://gist.github.com/pike00/6504ec5734ac7604efa3367c52904b2d)

### Revocation Procedure

When a key is compromised:

1. **Immediately** generate a new keypair
2. **Remove** the compromised public key from `.sops.yaml`
3. **Re-encrypt** all secrets (same procedure as rotation)
4. **Verify** the compromised key can no longer decrypt (test on isolated machine)
5. **Log incident** with timestamp, reason, scope
6. **Rotate all actual secrets** (database passwords, API tokens) that were encrypted
7. **Document** in incident report

### Recipient Offboarding (Non-Compromise)

When a team member leaves:

```bash
# 1. Remove their public key from .sops.yaml
# 2. Update key set:
sops updatekeys secrets.enc.yaml
# 3. Verify old key can't decrypt (on their machine or a machine that only has their key)
# 4. Commit updated encrypted files
```

**Source**: [ITNotes — Managing Git Secrets with SOPS and Age](https://itnotes.dev/managing-git-secrets-safely-with-mozilla-sops-and-age-a-lightweight-hashicorp-vault-alternative/)

---

## 7. Audit Logging for Key Access

### What to Log

| Event | Log Level | Content |
|-------|-----------|---------|
| Key generation | `INFO` | Timestamp, user, hostname, key fingerprint (public only) |
| Decryption attempt | `INFO` | Timestamp, user, process, file path |
| Decryption failure | `WARN` | Timestamp, user, process, reason |
| Key file access | `audit` | `auditd` rule on `keys.txt` |
| Key rotation | `INFO` | Old fingerprint → new fingerprint |
| Revocation | `CRITICAL` | Full incident details |

### Implementation for Guinevere

#### Linux auditd Rule

```bash
# /etc/audit/rules.d/sops-age-key.rules
-w /home/faiz/.config/sops/age/keys.txt -p rwxa -k sops-age-key
```

#### SOPS_AGE_KEY_CMD Audit Pattern

Using `SOPS_AGE_KEY_CMD` provides a natural audit point:

```bash
#!/bin/bash
# /usr/local/bin/sops-age-key-provider.sh
logger -p auth.info "SOPS age key accessed by PID $$ ($(whoami)) for recipient: ${SOPS_AGE_RECIPIENT}"
cat ~/.config/sops/age/keys.txt
```

Then set: `export SOPS_AGE_KEY_CMD="/usr/local/bin/sops-age-key-provider.sh"`

**Source**: [getsops/sops — keysource.go `SOPS_AGE_KEY_CMD`](https://github.com/getsops/sops/blob/main/age/keysource.go#L90-L100)

### What NOT to Log

| ❌ Never Log | Why |
|-------------|-----|
| The private key itself | Obvious — full compromise |
| Decrypted secret values | They are the protected data |
| `SOPS_AGE_KEY` env var value | Leaks via process env in crash dumps |
| Full key file path in error output | Information disclosure |

---

## 8. What to NEVER Do

### Absolute Prohibitions

| # | Prohibition | Risk | Source |
|---|-------------|------|--------|
| 1 | **Commit key to Git** (even with `.gitignore`) | Accidental push, history mining | Universal |
| 2 | **Paste key in chat/slack/Discord** | Logged forever, no recall | [AGENTS.md §5](file:///C:/Users/faizz/guinevere/AGENTS.md) |
| 3 | **Store key in environment variables** | Leaks via `/proc`, crash dumps, CI logs | SOPS docs |
| 4 | **Hardcode key in source code** | Obvious — code review bypass | OWASP |
| 5 | **Expose key in logs/error messages** | Log aggregation = single point of leak | OWASP |
| 6 | **Backup key to same cloud as encrypted data** | Circular dependency, single point of failure | [pike00 coldkey](https://gist.github.com/pike00/6504ec5734ac7604efa3367c52904b2d) |
| 7 | **Send key to external MCP/web tools** | Third-party compromise, no control | [AGENTS.md §14](file:///C:/Users/faizz/guinevere/AGENTS.md) |
| 8 | **Use `SOPS_AGE_KEY` in CI logs/build output** | Build log retention = credential leak | CI/CD best practices |
| 9 | **Use weak permissions (> 0600)** | Any user on system can read and decrypt | Linux security |
| 10 | **Reuse the same key across environments** | Prod/staging/dev separation violated | NIST SP 800-57 |
| 11 | **Store key on VPS where it decrypts** | Server compromise = key compromise | [HostMyCode](https://www.hostmycode.com/blog/linux-vps-secrets-rotation-sops-age-practical-workflow-2026) |
| 12 | **Keep only one copy of the key** | Single disk failure = permanent data loss | OWASP |

### Dangerous Anti-Patterns

```bash
# ❌ NEVER: Store key in env var (leaks everywhere)
export SOPS_AGE_KEY="AGE-SECRET-KEY-1..."

# ❌ NEVER: Echo key in build scripts
echo "AGE-SECRET-KEY-1..." | sops ...

# ❌ NEVER: Commit key even in .gitignore'd files
echo "AGE-SECRET-KEY-1..." >> .gitignore
git add keys.txt     # Someone WILL commit this eventually

# ❌ NEVER: Pipe decrypted secrets to stdout in CI
sops -d secrets.enc.yaml   # Visible in CI logs

# ❌ NEVER: Store key on the same VPS it protects
scp keys.txt ubuntu@vps:~/.config/sops/age/   # Server breach = full compromise

# ❌ NEVER: Use SOPS_AGE_KEY with inline content in CI variables
# GitLab/Actions store env var content in logs on error
```

---

## 9. Round-Trip Encryption Test Procedure

Before declaring the key operational, perform this verification.

### Step 1: Verify Key File Integrity

```bash
# Check file exists and has correct permissions
ls -la ~/.config/sops/age/keys.txt
# Expected: -rw------- 1 faiz faiz 2089 May 31 14:00 keys.txt

# Compute checksum for future verification
sha256sum ~/.config/sops/age/keys.txt > ~/.config/sops/age/keys.txt.sha256
cat ~/.config/sops/age/keys.txt.sha256
```

### Step 2: Extract and Verify Public Key

```bash
# Extract public key from comment
PUBKEY=$(grep '^# public key:' ~/.config/sops/age/keys.txt | cut -d' ' -f4)
echo "Recipient: $PUBKEY"

# Verify format (standard or PQ)
if [[ "$PUBKEY" == age1pq1* ]]; then
    echo "✅ Post-quantum hybrid key (ML-KEM-768 + X25519)"
elif [[ "$PUBKEY" == age1* ]]; then
    echo "✅ Standard X25519 key"
else
    echo "❌ Unknown key format"
fi
```

### Step 3: Round-Trip Encryption Test

```bash
# Create test file
echo "Guinevere age key round-trip test $(date)" > /tmp/age-test.txt

# Encrypt
age -r "$PUBKEY" -o /tmp/age-test.txt.age /tmp/age-test.txt
echo "✅ Encryption successful"

# Decrypt
age -d -i ~/.config/sops/age/keys.txt -o /tmp/age-test-decrypted.txt /tmp/age-test.txt.age
echo "✅ Decryption successful"

# Compare
diff /tmp/age-test.txt /tmp/age-test-decrypted.txt && echo "✅ Round-trip VERIFIED" || echo "❌ Round-trip FAILED"

# Cleanup
shred -u /tmp/age-test.txt /tmp/age-test-decrypted.txt
rm -f /tmp/age-test.txt.age
```

### Step 4: SOPS Integration Test

```bash
# Create a test SOPS file
echo "test_secret: hello-world" > /tmp/test-sops.yaml
sops --encrypt --age "$PUBKEY" /tmp/test-sops.yaml > /tmp/test-sops.enc.yaml
echo "✅ SOPS encryption successful"

# Decrypt with SOPS (auto-discovers key at default path)
sops --decrypt /tmp/test-sops.enc.yaml
echo "✅ SOPS decryption successful"

# Cleanup
rm -f /tmp/test-sops.yaml /tmp/test-sops.enc.yaml
```

### Step 5: Backup Verification

```bash
# Verify paper backup by scanning QR code
# (manual step: scan QR, compare reconstructed key with original)

# Verify password manager backup
# (manual: copy key from password manager, decrypt test file)

# Verify checksum
sha256sum -c ~/.config/sops/age/keys.txt.sha256
echo "✅ Backup verification complete"
```

---

## 10. Recommended Key Naming Conventions

### File Naming

| File | Convention | Example |
|------|-----------|---------|
| Primary private key | `keys.txt` | `~/.config/sops/age/keys.txt` |
| Backup key (rotated) | `keys.txt.YYYY-MM-DD` | `keys.txt.2026-05-31` |
| Public key for sharing | `guinevere.pub` | `~/.config/sops/age/guinevere.pub` |
| Recipient list (team) | `recipients.txt` | `ops/secrets/recipients.txt` |
| Old key (retired) | `keys.retired.YYYY-MM-DD` | `keys.retired.2026-01-15` |

### Environment Separation

| Environment | Path Pattern |
|-------------|-------------|
| Development | `~/.config/sops/age/keys.dev.txt` |
| Staging | `~/.config/sops/age/keys.staging.txt` |
| Production | `~/.config/sops/age/keys.txt` |
| CI/CD | Per-CI identity in CI secret store |

### Metadata in Key File

The age key file header (comment lines) should be preserved and augmented:

```
# created: 2026-05-31T14:00:00+07:00
# public key: age1pq1...
# environment: production
# hostname: faiz-workstation
# purpose: Guinevere SOPS secrets encryption
# rotation: quarterly
AGE-SECRET-KEY-PQ-1...
```

> **Never modify** the `AGE-SECRET-KEY-*` line. Only add/keep `#` comment lines for metadata.

---

## 11. Summary of Recommendations for Guinevere

### Decision Matrix

| Aspect | Recommendation | Rationale |
|--------|---------------|-----------|
| **Key type** | Post-quantum hybrid (`age-keygen -pq`) | Future-proof, ML-KEM-768+X25519 |
| **Install method** | GitHub binary v1.3.1 | apt version (1.1.1) lacks PQ support |
| **Key location** | `~/.config/sops/age/keys.txt` | Default SOPS path on Linux |
| **Permissions** | `0600` for private, `0644` for public | Least privilege |
| **Primary backup** | Paper backup (coldkey QR) | Air-gapped, offline |
| **Secondary backup** | Password manager (Bitwarden) | Accessible DR |
| **Key discovery** | `SOPS_AGE_KEY_FILE` env var for CI, default path for local | Explicit when needed, implicit when safe |
| **CI/CD approach** | GitHub Actions secret + `SOPS_AGE_KEY_CMD` wrapper | Script-based, audit-logged |
| **Rotation cadence** | Quarterly or on team change | NIST SP 800-57 recommendation |
| **Key on VPS?** | **NO** — decrypt locally, copy plaintext via SSH | Server compromise ≠ key compromise |

### Guardrails for Generation Step

When executing STEP-P0-012:

```bash
# ✅ DO:
cd /tmp && age-keygen -pq -o /tmp/keys.txt
chmod 600 /tmp/keys.txt
mv /tmp/keys.txt ~/.config/sops/age/keys.txt
sha256sum ~/.config/sops/age/keys.txt > ~/.config/sops/age/keys.txt.sha256
grep '^# public key:' ~/.config/sops/age/keys.txt | cut -d' ' -f4 > ~/.config/sops/age/guinevere.pub
chmod 644 ~/.config/sops/age/guinevere.pub

# Verify round-trip (see Section 9)
# Create paper backup (see Section 5)
# Store in password manager (see Section 5)
# Clean up any temp files: shred -u /tmp/keys.txt

# ❌ NEVER:
# - Leave temp key files around
# - Email the key
# - Commit key to repo
# - Paste in chat
# - Use SOPS_AGE_KEY env var with inline key
# - Skip the backup step before using the key
```

---

## 12. Sources

### Primary Sources

| Source | URL | Accessed |
|--------|-----|----------|
| age GitHub repository | https://github.com/FiloSottile/age | 2026-05-31 |
| age README (installation) | https://github.com/FiloSottile/age?tab=readme-ov-file | 2026-05-31 |
| age v1.3.1 release | https://github.com/FiloSottile/age/releases/tag/v1.3.1 | 2026-05-31 |
| SOPS age/keysource.go | https://github.com/getsops/sops/blob/main/age/keysource.go | 2026-05-31 |
| SOPS official docs | https://getsops.io/docs/ | 2026-05-31 |
| Ubuntu noble age package | https://packages.ubuntu.com/source/noble/age | 2026-05-31 |

### Secondary Sources (Best Practices & Analysis)

| Source | URL | Key Contribution |
|--------|-----|------------------|
| pike00/coldkey | https://github.com/pike00/coldkey | PQ key paper backup, security model |
| pike00 SOPS+age cheatsheet | https://gist.github.com/pike00/6504ec5734ac7604efa3367c52904b2d | Key rotation, cold key problem |
| ITNotes — Git Secrets with SOPS | https://itnotes.dev/managing-git-secrets-safely-with-mozilla-sops-and-age-a-lightweight-hashicorp-vault-alternative/ | Team workflow, .sops.yaml, pre-commit hooks |
| HostMyCode — VPS rotation 2026 | https://www.hostmycode.com/blog/linux-vps-secrets-rotation-sops-age-practical-workflow-2026 | VPS deployment pattern, systemd integration |
| knuth.info — Why apt install age isn't enough | https://knuth.info/posts/the-solo-stack/dotfiles/why-apt-install-age-isnt-enough/ | Ubuntu 24.04 apt vs binary version gap |
| DeepWiki — SOPS age | https://deepwiki.com/getsops/sops/3.5-age | SOPS age key discovery deep dive |
| OWASP Key Management Cheat Sheet | https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet | Key lifecycle, storage, revocation standards |
| NIST SP 800-133r3 (2026 draft) | https://csrc.nist.gov/News/2026/recommendation-for-cryptographic-key-generation | Key generation standards, PQC references |
| OneUptime — Key Management | https://oneuptime.com/blog/post/2026-01-30-encryption-key-management-details/view | Key hierarchy, HSM, rotation strategies |
| Security StackExchange — age backups | https://security.stackexchange.com/questions/281767/why-not-use-the-age-tool-for-encrypted-backups | age backup forgery analysis, threat model |

---

*Report prepared for Guinevere project — STEP-P0-012 audit context.*
*No actual keys were generated, accessed, or exposed during this research.*