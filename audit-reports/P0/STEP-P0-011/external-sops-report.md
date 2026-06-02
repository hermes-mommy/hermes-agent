# External Research Report: SOPS (Secrets OPerationS)

**Task**: STEP-P0-011 — installing SOPS on Ubuntu 24.04 VPS
**Date**: 2026-05-31
**Author**: Guinevere (LIBRARIAN)
**Scope**: SOPS version selection, installation methods, Ubuntu 24.04 considerations, age backend, configuration patterns, verification, known pitfalls

---

## 1. Project Overview

| Attribute | Detail |
|---|---|
| Repository | [github.com/getsops/sops](https://github.com/getsops/sops) |
| License | MPL 2.0 |
| Language | Go |
| Governance | CNCF Sandbox project |
| Official Docs | [https://getsops.io/docs/](https://getsops.io/docs/) |
| Latest Release | **v3.13.1** (2026-05-16) |
| Downloads (v3.13.1 linux.amd64) | ~48K+ in 2 weeks |

SOPS (Secrets OPerationS) encrypts **values only** in structured files (YAML/JSON/ENV/INI/BINARY), keeping keys and structure visible for readable Git diffs. It supports AWS KMS, GCP KMS, Azure Key Vault, HuaweiCloud KMS, HashiCorp Vault, PGP, and **age** backends.

**Key encryption model**: Hybrid encryption — a random data encryption key (DEK) encrypts file contents with AES-256-GCM; then the DEK itself is encrypted with each configured master key (age public keys, KMS keys, PGP keys).

---

## 2. Age Backend — Recommended for This Deployment

### 2.1 Why Age Over PGP/KMS

| Criterion | age | PGP/GPG | AWS/GCP KMS |
|---|---|---|---|
| Infrastructure | None | GPG keyring | Cloud account + IAM |
| Key format | Single X25519 key pair | Complex keyring with subkeys | Cloud-managed |
| Attack surface | Minimal binary, no keyring | Large (gpg agent, keyserver, trust db) | Network-dependent |
| Cryptography | X25519 + ChaCha20-Poly1305 | RSA or Curve25519; legacy defaults | Provider-specific |
| Offline | ✅ Yes | ✅ Yes | ❌ No (needs network) |
| Key rotation | Replace file + `sops updatekeys` | Subkey rotation | Automatic (cloud) |

**Recommendation from multiple sources**: Age is the **preferred backend for all new deployments** (official docs, CNCF docs, Flux docs, multiple 2026 guides). Use cloud KMS only when IAM-based access control is needed for team environments.

### 2.2 Age Support in SOPS — Version History

| SOPS Version | Age Support |
|---|---|
| v3.7.0+ | Initial age support (PR #688) |
| v3.9.0+ | SSH keys via age supported |
| v3.10.0+ | Age plugin support (PR #1641, merged 2025-02-27) |
| v3.13.x | Latest — stable, mature age integration |

**Any version ≥ v3.7.0 supports age**. The minimum for production use with age is **v3.9.x** which adds SSH key support. For this deployment, **v3.13.1** is the latest stable.

---

## 3. Installation Methods (Ubuntu 24.04)

### 3.1 Method Comparison

| Method | Pros | Cons | Recommendation |
|---|---|---|---|
| **Binary download** (recommended) | Official, version-pinned, simple | Manual download | ✅ **RECOMMENDED** |
| **.deb package** from releases | dpkg install, system-managed | v3.13.1 .deb available but must be downloaded | ✅ Good alternative |
| `go install` | From source, no external binary | Requires Go ≥ 1.25, slower | ❌ Overkill for VPS |
| `apt` (official repos) | Familiar | **NOT AVAILABLE** in Ubuntu repos | ❌ |
| Third-party apt repo (Cloudsmith) | apt-based | Third-party, version lagging | ❌ Not recommended |

### 3.2 ⚠️ Ubuntu 24.04 APT — NOT AVAILABLE

SOPS is **not packaged** in official Ubuntu 24.04 repositories. The GitHub discussion [#960](https://github.com/getsops/sops/discussions/960) confirms:

```
$ sudo apt-get install sops
E: Unable to locate package sops
```

Third-party repos (e.g., Cloudsmith from CloudPosse) exist but lag behind (v3.11.0-1 as of latest scan) and introduce unnecessary trust dependencies.

### 3.3 Recommended Installation: Binary Download (v3.13.1)

From official release page [v3.13.1](https://github.com/getsops/sops/releases/tag/v3.13.1):

```bash
# Download the binary
curl -LO https://github.com/getsops/sops/releases/download/v3.13.1/sops-v3.13.1.linux.amd64

# Move to PATH
sudo mv sops-v3.13.1.linux.amd64 /usr/local/bin/sops

# Make executable
sudo chmod +x /usr/local/bin/sops

# Verify
sops --version
# Expected: sops 3.13.1 (latest)
```

### 3.4 Alternative: .deb Package

```bash
curl -LO https://github.com/getsops/sops/releases/download/v3.13.1/sops_3.13.1_amd64.deb
sudo dpkg -i sops_3.13.1_amd64.deb
sops --version
```

### 3.5 Installing age (Separate Binary)

SOPS uses the age **library** embedded (for decryption of the DEK), but for key generation you need the `age` CLI:

```bash
sudo apt update
sudo apt install -y age
age --version
# Expected: age 1.x.y
```

This installs `age-keygen` and `age` CLI tools. Ubuntu 24.04 ships age in its official repos.

---

## 4. Verification & Integrity Checks

### 4.1 Checksums Verification (Cosign + GitHub OIDC)

SOPS v3.13.1 release artifacts include a checksums file signed with Cosign:

```bash
# Download checksums + signature
curl -LO https://github.com/getsops/sops/releases/download/v3.13.1/sops-v3.13.1.checksums.txt
curl -LO https://github.com/getsops/sops/releases/download/v3.13.1/sops-v3.13.1.checksums.pem
curl -LO https://github.com/getsops/sops/releases/download/v3.13.1/sops-v3.13.1.checksums.sig

# Verify checksums file signature
cosign verify-blob sops-v3.13.1.checksums.txt \
  --certificate sops-v3.13.1.checksums.pem \
  --signature sops-v3.13.1.checksums.sig

# Verify binary integrity
sha256sum -c sops-v3.13.1.checksums.txt --ignore-missing
```

### 4.2 SLSA Provenance Verification

Also available via `slsa-verifier` with the `sops-v3.13.1.intoto.jsonl` provenance file.

### 4.3 Quick Sanity Check

```bash
# Check binary type
file /usr/local/bin/sops
# Expected: ELF 64-bit LSB executable, x86-64, statically linked

# Check version
sops --version
```

---

## 5. Age Key Generation & Setup

### 5.1 Generate Key Pair

```bash
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt
```

Output example:
```
# created: 2026-05-31T14:00:00+07:00
# public key: age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p
AGE-SECRET-KEY-1...
```

**Critical**: Save the public key (`age1...`) for `.sops.yaml`. Back up `keys.txt` securely (password manager, encrypted backup) — **there is no recovery mechanism** if the private key is lost.

### 5.2 Key Permission Requirements

SOPS **refuses** to use a keys.txt file readable by other users:

```bash
chmod 600 ~/.config/sops/age/keys.txt
```

### 5.3 Key Discovery Order (Decryption)

When decrypting, SOPS searches for age identities in this order:

| Location | Config Mechanism |
|---|---|
| `$SOPS_AGE_KEY` env var | Inline key content (best for CI/CD) |
| `$SOPS_AGE_KEY_FILE` env var | Custom path to key file |
| `$SOPS_AGE_KEY_CMD` env var | Command output providing key |
| `$XDG_CONFIG_HOME/sops/age/keys.txt` | Linux standard (if XDG_CONFIG_HOME set) |
| `$HOME/.config/sops/age/keys.txt` | Fallback on Linux |
| SSH keys (`~/.ssh/id_ed25519`, `~/.ssh/id_rsa`) | Automatic fallback |
| `$SOPS_AGE_SSH_PRIVATE_KEY_FILE` | Custom SSH key path |

### 5.4 Hybrid Post-Quantum Keys (Optional)

age supports hybrid post-quantum identities (ML-KEM-768 + X25519):

```bash
age-keygen -pq -o ~/.config/sops/age/keys.txt
```

---

## 6. `.sops.yaml` Configuration Patterns

### 6.1 Basic Pattern — Single Age Recipient

```yaml
# .sops.yaml (place at repository root)
creation_rules:
  - path_regex: .*\.yaml$
    age: >-
      age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p
```

### 6.2 Multiple Recipients (Team Setup)

```yaml
creation_rules:
  - path_regex: .*secrets\.yaml$
    age: >-
      age1alice_public_key,
      age1bob_public_key,
      age1carol_public_key
```

### 6.3 Per-Environment Keys

```yaml
creation_rules:
  - path_regex: environments/production/.*\.yaml$
    age: age1prod_key_here

  - path_regex: environments/staging/.*\.yaml$
    age: age1staging_key_here

  - path_regex: environments/development/.*\.yaml$
    age: >-
      age1dev_key_here,
      age1another_dev_key
```

### 6.4 Partial Encryption (`encrypted_regex`)

```yaml
creation_rules:
  - path_regex: .*\.yaml$
    encrypted_regex: "^(data|stringData|password|apiKey|token|secret)$"
    age: age1your_public_key
```

### 6.5 Key Groups with Shamir Threshold (M-of-N)

```yaml
creation_rules:
  - path_regex: critical/.*\.yaml$
    shamir_threshold: 2
    key_groups:
      - age:
          - age1alice_key
      - age:
          - age1bob_key
      - kms:
          - arn: "arn:aws:kms:us-east-1:...:key/..."
```

Requires 2 of 3 key groups to decrypt (useful for disaster recovery).

### 6.6 ⚠️ File Naming

The config file **must** be named exactly `.sops.yaml`. Other names (`.sops.yml`, `sops.yaml`) won't be auto-discovered — you'd need `--config .sops.yml`.

### 6.7 Lookup Behavior

SOPS searches from the **working directory (CWD)** upward for `.sops.yaml`. The `path_regex` is relative to the `.sops.yaml` file location.

---

## 7. Common Usage Commands

```bash
# Encrypt a file
sops --encrypt secrets.yaml > secrets.enc.yaml

# Decrypt to stdout
sops --decrypt secrets.enc.yaml

# Edit encrypted file in $EDITOR
sops secrets.enc.yaml

# Add/remove recipients (after updating .sops.yaml)
sops updatekeys secrets.enc.yaml

# Rotate data key
sops rotate -i secrets.enc.yaml

# Encrypt with specific age recipients
sops --encrypt --age age1publickey... secrets.yaml > secrets.enc.yaml
```

---

## 8. Known Pitfalls & Mitigations

### 8.1 Architecture Mismatch (Critical)

**Issue**: Downloading the wrong architecture binary (e.g., `linux.arm64` on `x86_64`, or historic v3.7.2 bug where linux.amd64 was actually ARM64).

**Mitigation**:
```bash
# Verify architecture
uname -m
# x86_64 -> use linux.amd64
# aarch64 -> use linux.arm64

# Verify downloaded binary
file /path/to/sops-binary
# Expected: ELF 64-bit LSB executable, x86-64, statically linked
```

### 8.2 Binary Permissions

**Issue**: Binary not executable or not in PATH.

**Mitigation**:
```bash
sudo chmod +x /usr/local/bin/sops
# Verify PATH includes /usr/local/bin
echo $PATH
```

### 8.3 Wrong Age Recipient Key

**Issue**: Encrypting to a key the VPS cannot decrypt (wrong public key used).

**Mitigation**:
- Always define recipients in `.sops.yaml`, not in team memory
- Verify public key before encrypting: `grep '^# public key:' ~/.config/sops/age/keys.txt`
- Test decryption immediately after encryption

### 8.4 Keys.txt Permissions Too Permissive

**Issue**: `SOPS` refuses keys.txt readable by other users.

**Mitigation**:
```bash
chmod 600 ~/.config/sops/age/keys.txt
# OR (even stricter for VPS)
chmod 400 ~/.config/sops/age/keys.txt  # owner read-only
```

### 8.5 Environment Variable Not Set

**Issue**: SOPS can't find the age key if using a non-standard path.

**Mitigation**:
```bash
export SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt
# Add to ~/.bashrc or ~/.profile for persistence
```

### 8.6 Lost Private Key = Permanent Data Loss

**Issue**: No recovery mechanism — if the private key is the only recipient on a file, secrets are gone permanently.

**Mitigation**:
- **Always** add at least 2 recipients (your key + a backup/CI key)
- Back up `keys.txt` to a password manager (1Password, Bitwarden)
- For critical files, use key groups with Shamir threshold for M-of-N recovery

### 8.7 Editor Mode Re-encrypts (Noisy Diffs)

**Issue**: Running `sops file.yaml` in editor mode re-encrypts all values, rotating the data key. This makes Git diffs noisy.

**Mitigation**:
- Use `--encrypt` / `--decrypt` flags for automation scripts (not editor mode)
- Only use editor mode for interactive editing

### 8.8 CI/CD Key Exposure

**Issue**: Storing age private keys in CI/CD variables unsafely.

**Mitigation**:
- Use `SOPS_AGE_KEY` env var (not a file) in CI/CD
- Store as **secret** in GitHub Actions / GitLab CI
- Prefer cloud KMS for CI/CD when IAM roles are available (audit trail)

---

## 9. Recommended Version Decision

| Criterion | Verdict |
|---|---|
| **Version** | **v3.13.1** (latest stable, released 2026-05-16) |
| **Why this version** | Latest security fixes, mature age support, SLSA provenance, Cosign-verified checksums |
| **Backend** | **age** (no infrastructure, offline-capable, modern crypto) |
| **Install method** | Binary download or .deb from GitHub releases |
| **Age CLI install** | `sudo apt install -y age` (Ubuntu 24.04 official repos) |

### Decision Matrix

```
                    ┌─────────────────────────────┐
                    │   Install SOPS on Ubuntu     │
                    │   24.04 VPS                  │
                    └─────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
               Binary .deb              go install
               (RECOMMENDED)            (NOT recommended)
                    │                       │
            ┌───────┴───────┐       Needs Go ≥1.25
            │               │       on a production VPS
        v3.13.1         Older
        (LATEST)        versions
            │
    ┌───────┴───────┐
    │               │
  linux.amd64    linux.arm64
  (x86_64 VPS)   (ARM64 VPS)
```

---

## 10. References

1. **Official SOPS Docs (age section)**: [https://getsops.io/docs/#encrypting-using-age](https://getsops.io/docs/#encrypting-using-age)
2. **SOPS GitHub Releases**: [https://github.com/getsops/sops/releases](https://github.com/getsops/sops/releases)
3. **SOPS v3.13.1 Release**: [https://github.com/getsops/sops/releases/tag/v3.13.1](https://github.com/getsops/sops/releases/tag/v3.13.1)
4. **SOPS GitHub (README)**: [https://github.com/getsops/sops](https://github.com/getsops/sops)
5. **Flux SOPS Guide**: [https://fluxcd.io/flux/guides/mozilla-sops/](https://fluxcd.io/flux/guides/mozilla-sops/)
6. **VPS Secrets Management (2026)**: HostMyCode — sops + age on Linux VPS
7. **ITNotes SOPS+Age Guide**: [https://itnotes.dev/managing-git-secrets-safely-with-mozilla-sops-and-age/](https://itnotes.dev/managing-git-secrets-safely-with-mozilla-sops-and-age/)
8. **Ubuntu APT SOPS Discussion**: [https://github.com/getsops/sops/discussions/960](https://github.com/getsops/sops/discussions/960)

---

*Report written by GUINEVERE (LIBRARIAN) for STEP-P0-011 — installation of SOPS on Ubuntu 24.04 VPS. No installation, SSH access, or secret exposure occurred during this research.*