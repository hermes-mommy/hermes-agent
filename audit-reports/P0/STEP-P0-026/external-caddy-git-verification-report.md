# External Caddy & Git Verification Report

> **Purpose**: Provide verification criteria for P0-024 (Caddy + Tailscale reverse proxy setup) and P0-025 (Git repo init/GitHub private repo setup). Based on current best practices as of 2026-05-31.

---

## 1. Caddy + Tailscale — No Port 80 Conflict

### Background

Caddy's Automatic HTTPS expects port 80 for HTTP-01 ACME challenges and HTTP→HTTPS redirects. When Tailscale or another process already binds port 80, Caddy fails with `bind: permission denied` or `address already in use`.

### Verification Criteria

| # | Criteria | Source |
|---|----------|--------|
| 1.1 | **Explicit `http_port` / `https_port` override** — If port 80/443 are unavailable, set `{ http_port 8080 https_port 8443 }` in the Caddyfile global options block to avoid port conflicts. | [Caddy Docs — Global Options](https://caddyserver.com/docs/caddyfile/options) |
| 1.2 | **`auto_https disable_redirects` for Tailscale-only setups** — When Caddy sits behind Tailscale (which terminates TLS), disable Caddy's built-in HTTP→HTTPS redirect to prevent it from claiming port 80. Use `{ auto_https disable_redirects }` if no public ACME is needed. | [Caddy Community — I need Caddy to stop using port 80](https://caddy.community/t/i-need-caddy-to-stop-using-port-80/26397) |
| 1.3 | **Tailscale `bind tailscale/` directive** — For tailnet-only sites, bind to the Tailscale interface: `bind tailscale/<nodename>`. This avoids binding to `0.0.0.0:80` entirely. | [tailscale/caddy-tailscale README](https://github.com/tailscale/caddy-tailscale/blob/main/README.md#network-listener) |
| 1.4 | **Non-root user binding** — If running as non-root on Linux without port 80/443, either: (a) `sudo setcap cap_net_bind_service=+ep $(which caddy)`, or (b) use high ports (≥1024) and forward via Tailscale `serve`. | [Caddy Docs — Reverse Proxy Quick-start](https://caddyserver.com/docs/quick-starts/reverse-proxy) |
| 1.5 | **Tailscale `serve` on alternative port** — Use `tailscale serve --http=8080 localhost:8080` or `tailscale serve --https=8443 localhost:8080` when Tailscale handles TLS termination and forwards to Caddy on a non-privileged port. | [Tailscale Docs — serve command](https://tailscale.com/docs/reference/tailscale-cli/serve) |
| 1.6 | **Docker `network_mode: host` caveat** — When Caddy runs in Docker behind Tailscale Funnel, host networking is required so Caddy can reach `localhost` backends; avoids Docker NAT complications but shares host port namespace. | [Caddy + Tailscale Funnel blog — 2026](https://vipinpg.com/blog/configuring-tailscale-funnel-with-caddy-reverse-proxy-for-exposing-local-llm-apis-without-opening-firewall-ports-or-vps-tunnels/) |

### Recommended Caddyfile Pattern (Tailscale-only, no port 80)

```caddyfile
{
    # Disable HTTP→HTTPS redirect when Tailscale terminates TLS
    auto_https disable_redirects

    # Optional: only if binding on non-standard ports
    # http_port 8080
    # https_port 8443
}

:80 {
    bind tailscale/guinevere
    reverse_proxy localhost:8000
}
```

> **Note**: With `bind tailscale/`, Caddy listens **only** on the Tailscale interface — no port 80/443 conflict with the host.

---

## 2. Tailscale Binding Patterns

### 2.1 `caddy-tailscale` Plugin vs Native Tailscale

| Approach | When to Use |
|----------|------------|
| **Native Tailscale** (no plugin) | Tailscale already installed on host. Caddy binds to `tailscale0` interface IP. Simpler, one less plugin dependency. |
| **`caddy-tailscale` plugin** | Caddy runs in a container without host Tailscale, or multiple Caddy sites need separate Tailscale node identities. Uses `bind tailscale/<name>`. |

### 2.2 `ts.net` Certificate Auto-Discovery

Caddy 2.5+ automatically recognizes `*.ts.net` domains and fetches certificates from the local Tailscale instance at handshake time. No `tls` directive needed.

```caddyfile
service.machine.tailnet.ts.net {
    reverse_proxy backend:8080
}
```

**Requirement**: Tailscale HTTPS must be enabled in the Tailscale admin console, and Caddy must have access to the Tailscale socket (root or `TS_PERMIT_CERT_UID` configured).

### 2.3 Key Constraints

- Wildcard certificates **not available** from Tailscale; each subdomain gets its own cert (Caddy handles this automatically).
- `.ts.net` certs are **tailnet-only** — not valid for public internet access.
- Auth keys expire after 90 days; for persistent nodes, use non-ephemeral auth key (state persisted) or OAuth client secret.
- `bind tailscale/` requires the trailing slash and a named node configuration.

### References

- [tailscale/caddy-tailscale README](https://github.com/tailscale/caddy-tailscale/blob/main/README.md)
- [Caddy Automatic HTTPS for `.ts.net`](https://caddyserver.com/docs/automatic-https#activation)
- [Use Caddy to Manage Tailscale HTTPS Certificates](https://tailscale.com/blog/caddy)

---

## 3. Git Repo Initialization — Secrets & `.gitignore`

### 3.1 Pre-First-Commit Checklist

| # | Criteria | Source |
|---|----------|--------|
| 3.1 | **`.gitignore` before first `git add`** — Create `.gitignore` before any files are staged. Git only ignores files that were never tracked. Adding `.gitignore` after a commit does not remove secrets already in history. | [Secure Your Ship — Starting a New Repository](https://secureyour.sh/setup/new-repo/) |
| 3.2 | **Ignore all env/credential files** — Minimum pattern: `.env`, `.env.*`, `*.pem`, `credentials.json`, `*.key`, `secrets/`, `*.log`, `node_modules/`, `__pycache__/`, `.DS_Store`, `dist/`, `build/`. | [GitHub Security Checklist — 2026](https://checkyourvibe.dev/blog/checklists/github-repo-checklist) |
| 3.3 | **`git init` with intent** — Initialize with `git init` from project root. Verify `git status` before first commit. `git add -A` is risky — always review staged files first. | [Precision AI Academy — Git Guide 2026](https://precisionaiacademy.com/blog/git-github-guide-2026) |
| 3.4 | **Global `.gitignore` as safety net** — Set `git config --global core.excludesFile ~/.gitignore_global` with OS-specific patterns (`.DS_Store`, `Thumbs.db`) as backup. | [domelic/github-repository-setup](https://github.com/domelic/github-repository-setup) |
| 3.5 | **Verify git identity before first commit** — `git config user.name` and `git config user.email` should be set globally or per-repo. Must match a verified GitHub email for commit signing. | [GitHub Docs — Telling Git about your signing key](https://docs.github.com/en/authentication/managing-commit-signature-verification/telling-git-about-your-signing-key) |

### 3.2 No-Secrets Enforcement Verification

```bash
# Pre-commit hook (recommended: detect-secrets or pre-commit framework)
pip install detect-secrets
detect-secrets scan --baseline .secrets.baseline

# Or use git-secrets
git secrets --install
git secrets --register-aws

# GitHub push protection (enable in repo settings)
# Blocks commits containing supported secret patterns before push
```

| # | Criteria | Source |
|---|----------|--------|
| 3.6 | **Enable Secret Scanning + Push Protection** — In GitHub repo Settings → Code security & analysis → enable Secret Scanning and Push Protection. Blocks API keys, tokens, passwords on push. | [GitHub Security Guide — 2026](https://juergenkoller.software/en/blog/github-repositories-security.html) |
| 3.7 | **BFG Repo-Cleaner for historical secrets** — If a secret was committed, use `bfg --delete-files .env` or `git filter-branch` to purge from history. Rotate compromised secrets regardless. | [How to Harden — GitHub Guide](https://howtoharden.com/guides/github/) |
| 3.8 | **Never hardcode credentials** — Use environment variables or secrets managers (GitHub Secrets, 1Password, Doppler, HashiCorp Vault). Even in private repos, treat creds as compromised if committed. | [Blog — Private Code Repository Security](https://blog.shartech.cloud/private-code-repository-best-practices-security-guide/) |

---

## 4. GitHub Branch Protection (Rulesets)

### 4.1 Modern Approach: Rulesets (2024+)

GitHub recommends **rulesets** over legacy branch protection rules. Rulesets support layering (multiple rulesets apply simultaneously), evaluation mode, and visibility to all repo readers.

### 4.2 Minimum Branch Protection Ruleset

| # | Rule | Purpose |
|---|------|---------|
| 4.1 | **Require pull request before merging** | Prevents direct pushes to `main`/`master` |
| 4.2 | **Require at least 1 approval** | Ensures code review (2 for L2/critical repos) |
| 4.3 | **Dismiss stale approvals on new commits** | Forces re-review after changes |
| 4.4 | **Block force pushes** | Prevents history rewrite on protected branches |
| 4.5 | **Restrict deletions** | Prevents accidental branch deletion |
| 4.6 | **Require signed commits** | Ensures all commits are cryptographically verified (see §5) |
| 4.7 | **Require status checks** (if CI exists) | Blocks merge if tests/lint fail |
| 4.8 | **Enforce for admins** | No bypass for repository admins |

### 4.3 "Protect Main" vs "Check Main" Pattern

Two-ruleset approach from solo-dev best practices:

| Ruleset | Rules | Bypass |
|---------|-------|--------|
| **"Check Main"** | PR required, 1 approval, signed commits, status checks | Repository Admin + CI bot |
| **"Protect Main"** | Block force pushes, restrict deletions | **Zero bypass actors** (not even admins) |

### 4.4 Verification Commands

```bash
# Check branch protection via GitHub CLI
gh api repos/OWNER/REPO/branches/main/protection

# Check rulesets
gh api repos/OWNER/REPO/rulesets

# Create ruleset via API
# (prefer UI at Settings → Rules → Rulesets for initial setup)
```

### References

- [GitHub Docs — About Rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [GitHub Hardening Guide — 2026](https://howtoharden.com/guides/github/)
- [Foropoulos — Solo Dev Repo Setup](https://foropoulosnow.com/blog/posts/github-repo-setup-solo-developer-guide)

---

## 5. Commit Signing Caveats

### 5.1 Supported Methods

| Method | Git Version | Key Management | Ease |
|--------|-------------|---------------|------|
| **GPG** | All versions | Manual key generation, expiration, revocation | Moderate |
| **SSH** | Git 2.34+ | Reuse existing SSH auth key, simplest setup | Easy |
| **S/MIME** | Enterprise | Organizational PKI | Complex |

### 5.2 Critical Verification Requirements

| # | Criteria | Why It Matters |
|---|----------|----------------|
| 5.1 | **Email in signing key must match verified GitHub email** | GitHub compares the commit email against the key UID. Mismatch → "Unverified" badge. |
| 5.2 | **Add key as *signing* key, not just *authentication* key** | In GitHub Settings → SSH and GPG keys, SSH keys have separate checkboxes for Authentication vs Signing. |
| 5.3 | **`git config commit.gpgsign true`** (or `gpg.format ssh` + `user.signingkey`) | Without this, commits are not signed by default. Use `-S` flag per-commit or set globally. |
| 5.4 | **Vigilant mode** (`Flag unsigned commits as unverified`) | Settings → SSH and GPG keys → Vigilant mode. Combined with branch protection "Require signed commits", this ensures no unsigned commit can land on main. |
| 5.5 | **SSH `allowedSignersFile` for local verification** | For SSH-signed commits, configure `gpg.ssh.allowedSignersFile` to verify signatures locally (`git log --show-signature`). |

### 5.3 Common Failure Modes

| Symptom | Root Cause | Fix |
|---------|------------|-----|
| "gpg: signing failed: No secret key" | `user.signingkey` doesn't match any local key | `gpg --list-secret-keys` to verify key ID |
| Commits show "Unverified" on GitHub | Email in commit differs from verified email on GitHub | `git config user.email` must match GitHub verified email |
| SSH signing doesn't work | Git < 2.34, or key added only for auth not signing | Upgrade Git, add SSH key as signing key |
| Signed but "Partially verified" | Expired or revoked key used | Update/renew GPG key or switch to SSH |
| GPG passphrase prompt every commit | gpg-agent not caching credentials | Configure `gpg-agent` or use `GPG Suite` (macOS) / `Gpg4win` (Windows) |

### 5.4 Quick Setup (SSH — Recommended)

```bash
# 1. Use existing SSH key or generate new one
ssh-keygen -t ed25519 -C "your.email@example.com"

# 2. Tell Git to use SSH signing
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git config --global commit.gpgsign true

# 3. Add public key to GitHub as Signing key
# Settings → SSH and GPG keys → New SSH Key → Key Type: Signing Key

# 4. Enable Vigilant mode (same page)
# Flag unsigned commits as unverified → check the box

# 5. Verify
git log --show-signature -1
```

### References

- [GitHub Docs — Signing commits](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits)
- [GitHub Docs — About commit signature verification](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification)
- [Signing Your Git Commits: From Zero to Verified — 2026](https://tenthirtyam.org/dispatches/2026/03/23/signing-your-git-commits-from-zero-to-verified/)
- [Stack Overflow — GPG vs SSH signing](https://stackoverflow.com/questions/73489997/whats-the-difference-between-signing-commits-with-ssh-versus-gpg)

---

## Appendix: Verification Checklist Summary for P0-024/P0-025

### Caddy + Tailscale (P0-024)

- [ ] Port 80/443 not in conflict with other processes (check via `netstat -ano | findstr :80`)
- [ ] `auto_https disable_redirects` set for Tailscale-only sites OR `http_port`/`https_port` configured
- [ ] Tailscale `bind` directive used to avoid binding to host network interfaces
- [ ] `.ts.net` domain used for automatic certificate provisioning OR `tls { get_certificate tailscale }` specified
- [ ] Non-root user binding handled via `setcap` or high ports
- [ ] Tailscale auth key configured (via `TS_AUTHKEY` env or global config)
- [ ] Caddy logs show no `bind: permission denied` or `address already in use` errors

### Git Init / GitHub (P0-025)

- [ ] `.gitignore` created and committed **before** any code files
- [ ] `.env`, `*.pem`, `*.key`, `secrets/` in `.gitignore`
- [ ] `git init` done from correct project root
- [ ] `git config user.name` and `user.email` set correctly
- [ ] No credentials visible in `git status` staged files
- [ ] GitHub Secret Scanning + Push Protection enabled
- [ ] Branch protection / rulesets configured on `main`
  - [ ] PRs required
  - [ ] At least 1 approval required
  - [ ] Force pushes blocked
  - [ ] Signed commits required (if signing is set up)
- [ ] Commit signing configured (SSH or GPG)
- [ ] Signing key matches verified GitHub email
- [ ] Vigilant mode enabled (flags unsigned commits)

---

*Generated: 2026-05-31 | Research sources linked inline | For P0-024/P0-025 verification gate*