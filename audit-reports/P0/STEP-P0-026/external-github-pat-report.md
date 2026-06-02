# External Research Report: GitHub Fine-Grained PAT Best Practices

**Step**: STEP-P0-026
**Date**: 2026-05-31
**Research Type**: Conceptual (TYPE A) — GitHub documentation and community best practices
**Sources**: Official GitHub Docs + GitHub Changelog + Community guides

---

## 1. Executive Summary

GitHub recommends **fine-grained Personal Access Tokens (PATs)** over classic PATs for all scenarios where they are supported. For private repo git push/pull over HTTPS, the minimum required permissions are:

| Operation | Min Permission | Access Level |
|---|---|---|
| `git pull` (read) | `Contents` | `read` |
| `git push` (write) | `Contents` | `write` |
| Both (auto) | `Metadata` | `read` (auto-granted) |

Fine-grained PATs were promoted to **General Availability on 2025-03-18** and are now enabled by default for all organizations.

---

## 2. Fine-Grained PAT vs Classic PAT vs Alternatives

| Feature | Fine-Grained PAT | Classic PAT | GitHub App | SSH Key |
|---|---|---|---|---|
| **Scope** | Per-repo or per-org | All repos user can access | Per-repo or per-org | Per-repo |
| **Permissions** | Granular (Contents, Metadata, etc.) | Broad scopes (`repo`, `admin:org`) | Granular + short-lived tokens | Read/write per key |
| **Expiration** | Configurable (1-366 days or infinite) | Configurable | 8-hour default (refreshable) | No expiration |
| **Generation** | GitHub UI / URL templates | GitHub UI | GitHub org settings | `ssh-keygen` |
| **Recommended for** | Personal CLI use, scripts | Legacy fallback only | Team automation, long-lived CI | Server/headless environments |
| **Git operations** | HTTPS only | HTTPS only | Via installation token | SSH only |

**Official recommendation**: Use fine-grained PATs whenever possible. Use `gh auth login` (GitHub CLI) or Git Credential Manager (GCM) instead of manual PAT management when feasible.

**Official source**: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens

---

## 3. Minimum Permissions for Private Repo Git Push/Pull

### Fine-Grained PAT

For `git push`/`git pull` over HTTPS to a **private repository**, the only required repository permission is:

| Permission | Access Level | Required For |
|---|---|---|
| `Contents` | `read` | `git pull`, `git clone`, `git fetch` |
| `Contents` | `write` | `git push` (includes read) |
| `Metadata` | `read` | **Auto-granted** — required for repo discovery |

**Minimum for push access**: `Contents: Read and write` (implies `read` for pull).

**Minimum for pull-only access**: `Contents: Read` + `Metadata: Read` (Metadata is auto-granted).

**Important**: `write` access level implicitly includes `read`. You do not need to set both — setting `contents=write` covers both push and pull.

**Sources**:
- https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#repository-permissions
- https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens
- Community verified: https://openillumi.com/en/en-github-pat-403-forbidden-permission-fix/

### Classic PAT (Not Recommended)

If fine-grained PATs are not an option (e.g., for outside collaborators on org repos), classic PAT requires the `repo` scope (full access to all repos the user can access).

**Source**: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token-classic

---

## 4. Expiration and Rotation

### Default Behavior
- Fine-grained PAT default expiration: **30 days** (configurable 1-366 days, or infinite for personal projects)
- Classic PAT: No expiration required by default, but auto-revoked after **1 year of inactivity**

### Organization/Enterprise Policies
- Maximum lifetime policy: org owners can set max 1-366 days for fine-grained PATs
- Default org policy (if enabled): **366 days** max
- Policies enforced at token creation and on each API/Git call
- Non-compliant tokens receive `403` responses

### Rotation Best Practices
1. **Set explicit expiration**: 90 days recommended for org tokens; shorter for CI
2. **Use `gh auth login`**: GitHub CLI handles token rotation automatically via keychain
3. **Track via security log**: `oauth_authorization.destroy` events mark revocation/expiration
4. **Automate rotation**: For scripts, store PAT in GitHub Actions secrets or SOPS and regenerate periodically
5. **Never use infinite lifetimes for org-facing tokens**

**Sources**:
- https://docs.github.com/en/enterprise-cloud@latest/admin/enforcing-policies/enforcing-policies-for-your-enterprise/enforcing-policies-for-personal-access-tokens-in-your-enterprise
- https://github.blog/changelog/2024-10-18-new-pat-rotation-policies-preview-and-optional-expiration-for-fine-grained-pats/
- https://github.blog/changelog/2025-03-18-fine-grained-pats-are-now-generally-available/

---

## 5. Using PAT for Git Operations Over HTTPS

### How It Works
1. Create a fine-grained PAT via GitHub Settings → Developer Settings → Fine-grained tokens
2. Use as password when Git prompts for credentials:
   ```
   git clone https://github.com/owner/repo.git
   Username: <your-github-username>
   Password: <the-pat-token-value>
   ```
3. **PATs work ONLY with HTTPS remotes**, not SSH

### Git Credential Caching (GCM)
- **Git Credential Manager** (GCM) securely stores the PAT in OS keychain (Windows Credential Manager, macOS Keychain, Linux libsecret)
- After first auth, GCM handles subsequent requests transparently
- No need to re-enter PAT on each operation

### GitHub CLI (`gh auth login`)
- Alternative to manual PAT management
- `gh auth login` creates and stores a token automatically
- Token managed by `gh` — rotation handled automatically
- For headless use: `gh auth login --with-token < token.txt`

**Sources**:
- https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#using-a-personal-access-token-on-the-command-line
- https://github.com/GitCredentialManager/git-credential-manager
- https://docs.github.com/en/github-cli/github-cli/about-github-cli

---

## 6. Pre-filled Token Templates (URL Parameters)

GitHub supports URL-parameter-based token creation templates for repeatable setup:

**Push access template URL**:
```
https://github.com/settings/personal-access-tokens/new
  ?name=Repo-writing+token
  &description=Just+contents:write
  &contents=write
```

**Read-only template URL**:
```
https://github.com/settings/personal-access-tokens/new
  ?name=Repo-reading+token
  &description=Just+contents:read
  &contents=read
```

**Supported URL parameters**:
| Param | Type | Example | Notes |
|---|---|---|---|
| `name` | string | `Deploy%20Bot` | ≤ 40 chars, URL-encoded |
| `description` | string | `Used+for+deployments` | ≤ 1024 chars |
| `target_name` | string | `octodemo` | User or org slug |
| `expires_in` | int / `none` | `30` or `none` | 1-366 days |
| `<permission>` | `read`/`write`/`admin` | `contents=write` | As many as needed |

**Source**: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#pre-filling-fine-grained-personal-access-token-details-using-url-parameters

---

## 7. Testing PAT Push/Pull Safely

### Safe Test Procedure (dry-run before live)
```bash
# 1. Clone with PAT (first-time auth prompts for password)
git clone https://github.com/<owner>/<test-repo>.git
# Username: <your-github-username>
# Password: <pat-value>

# 2. Verify pull works
cd <test-repo>
git pull

# 3. Test push safety with a test branch (not main)
git checkout -b test-pat-verification
echo "# PAT test" >> README.md
git add README.md
git commit -m "test: verify PAT push access"

# 4. Push to test branch
git push origin test-pat-verification

# 5. If successful, delete test branch
git push origin --delete test-pat-verification
git checkout main
git branch -D test-pat-verification
```

### Common Error: 403 Forbidden
- **Cause**: FG-PAT created with zero/default permissions does not include `Contents: write`
- **Fix**: Edit PAT permissions to set `Contents: Read and write`
- For classic PATs: ensure `repo` scope is selected

### Common Error: `fatal: Authentication failed`
- **Cause**: Using password instead of PAT as the password field
- **Fix**: Use PAT value as password; username is your GitHub username (not email)

### Credential Manager Safety
- Use `git config --global credential.helper manager-core` (Windows) or `git config --global credential.helper osxkeychain` (macOS)
- This stores PAT encrypted in OS keychain, not plaintext

**Sources**:
- https://openillumi.com/en/en-github-pat-403-forbidden-permission-fix/
- https://thelinuxcode.com/how-to-authenticate-git-push-with-github-using-a-token-2026-guide/

---

## 8. Secret Storage via SOPS

For storing PATs (or other secrets) in Git repositories, **Mozilla SOPS** with **age** encryption is the recommended approach:

### Basic SOPS + age Workflow
```bash
# 1. Install age and sops
# 2. Generate an age keypair
age-keygen -o key.txt
# Public key: age1...
# Private key: stored in key.txt (protect this)

# 3. Create .sops.yaml in repo root
cat > .sops.yaml << 'EOF'
creation_rules:
  - path_regex: secrets\.enc\.yaml$
    age: age1...  # your public key
EOF

# 4. Encrypt a secret file
sops --encrypt --age age1... --in-place secrets.enc.yaml

# 5. Decrypt at runtime
sops --decrypt secrets.enc.yaml
```

### PAT-Specific SOPS Usage
```yaml
# secrets.enc.yaml (encrypted with SOPS)
github_pat: <encrypted-value>
repo_url: https://github.com/owner/repo.git
```

### Decryption in CI (GitHub Actions)
```yaml
- name: Decrypt PAT
  run: sops --decrypt secrets.enc.yaml > /tmp/pat.yaml
  env:
    SOPS_AGE_KEY: ${{ secrets.SOPS_AGE_KEY }}
```

### Best Practices for PAT + SOPS
1. Store PAT as an encrypted value in SOPS-encrypted YAML/JSON
2. Commit the encrypted file to Git (safe — values are encrypted)
3. Store the age private key separately (1Password, GitHub Actions secrets, etc.)
4. Never commit unencrypted PAT values
5. Use `.gitattributes` filters for automatic encryption (advanced)

### Alternative: GitHub Actions Secrets
- For CI-only usage, store PAT directly in GitHub Actions secrets
- Access via `${{ secrets.GH_PAT }}` in workflow files
- Simpler than SOPS but only works within GitHub Actions

**Sources**:
- https://github.com/age-sops/sops
- https://docs.github.com/en/actions/security-guides/encrypted-secrets
- https://fluxcd.io/flux/guides/mozilla-sops/
- https://devopsil.com/articles/2026-03-22-sops-encrypted-secrets-gitops/

---

## 9. Known Feature Gaps (Fine-Grained PATs)

Fine-grained PATs **cannot** currently do:
- Access **multiple organizations** with a single token
- Access **Packages** APIs
- Call the **Checks API**
- Access **Projects** owned by a user account
- Contribute to **public repos where user is not a member**
- Contribute as an **outside collaborator** to org repos
- Manage **Enterprise** objects (SCIM, org creation, audit logs)

For these scenarios, fall back to classic PATs or GitHub Apps.

**Source**: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#fine-grained-personal-access-tokens-limitations

---

## 10. Autonomous Blocker: PAT Generation Requires Browser/UI

### Key Finding: PAT CANNOT be generated autonomously

Creating a fine-grained PAT requires:
1. **Interactive browser session** on `github.com/settings/tokens` — requires human authentication
2. **GitHub UI navigation** (Settings → Developer Settings → Fine-grained tokens → Generate new token)
3. **Manual selection** of resource owner, repository access, and permissions
4. **One-time display** of the token value (shown only once at creation)

### What CAN be done autonomously:
- Construct a **pre-filled URL** with desired permissions:
  ```
  https://github.com/settings/personal-access-tokens/new?name=Guinevere+deploy+token&contents=write&expires_in=90
  ```
  (Faiz must open this URL, log in, and generate the token manually)
- After token is created, **store and use** it autonomously via SOPS
- **Revoke** tokens via API if Faiz provides an existing admin token
- **Rotate** expiring tokens if Faiz re-generates and provides the new value

### Recommendation for Guinevere:
1. Faiz generates one fine-grained PAT via the pre-filled URL above
2. Faiz provides the PAT value to Guinevere once
3. Guinevere stores it encrypted via SOPS (age encryption)
4. Guinevere uses it for `git push`/`pull` operations
5. When token expires (e.g., 90 days), Faiz re-generates and provides new value

---

## 11. Reference Links Summary

| Resource | URL |
|---|---|
| Managing PATs (Official Docs) | https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens |
| PAT Permissions Reference | https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens |
| PAT Endpoints Available | https://docs.github.com/en/rest/overview/endpoints-available-for-fine-grained-personal-access-tokens |
| FG-PAT GA Announcement (2025-03-18) | https://github.blog/changelog/2025-03-18-fine-grained-pats-are-now-generally-available/ |
| PAT Rotation Policies (2024-10-18) | https://github.blog/changelog/2024-10-18-new-pat-rotation-policies-preview-and-optional-expiration-for-fine-grained-pats/ |
| Updated Permissions UI (2025-08-26) | https://github.blog/changelog/2025-08-26-template-urls-for-fine-grained-pats-and-updated-permissions-ui/ |
| Keeping API Credentials Secure | https://docs.github.com/en/rest/overview/keeping-your-api-credentials-secure |
| Token Expiration & Revocation | https://github.com/github/docs/blob/main/content/authentication/keeping-your-account-and-data-secure/token-expiration-and-revocation.md |
| SOPS (Secrets OPerationS) | https://github.com/age-sops/sops |
| Git Credential Manager | https://github.com/GitCredentialManager/git-credential-manager |
| GitHub CLI (`gh auth login`) | https://docs.github.com/en/github-cli/github-cli/about-github-cli |

---

*Report prepared for Guinevere project — P0 infrastructure research.*