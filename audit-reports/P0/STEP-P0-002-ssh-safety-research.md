# STEP P0-002 — SSH Safety & Hardening Research Report

**Prepared**: 2026-05-31
**Context**: Guinevere P0-002 — adding new user SSH access to Ubuntu 24.04 shared VPS. Must avoid lockout and preserve existing sessions (Aizanta user + faiz-prod root).
**Scope**: ssh-copy-id/authorized_keys setup, sshd_config validation (`sshd -t`), safe reload vs restart, session preservation, file permissions, sudoers safety, Ubuntu 24.04-specific differences.

---

## 1. Ubuntu 24.04 Critical Differences (OpenSSH + systemd)

### 1.1 Socket Activation (Breaking Change from 22.04)

Ubuntu 24.04 (Noble Numbat) ships OpenSSH **9.6p1** and manages sshd via **systemd socket activation** — a shift from the traditional service-only model.

| Aspect | Ubuntu 22.04 (legacy) | Ubuntu 24.04 (current) |
|---|---|---|
| Service unit | `sshd.service` enabled directly | `ssh.socket` enabled; triggers `ssh.service` on-demand |
| Start command | `systemctl start sshd` | `systemctl start ssh.socket` |
| Status check | `systemctl is-active sshd` | `systemctl is-active ssh.socket` |
| Enable at boot | `systemctl enable sshd` | `systemctl enable ssh.socket` |
| Port config | In `sshd_config` | Via `systemctl edit ssh.socket` OR in config drop-in |
| Reload command | `systemctl reload sshd` | `systemctl reload ssh` (still works) |

**Critical**: `sshd -t` may fail with `/run/sshd missing` because in socket-activated mode, the directory may not exist at boot time.

```bash
# Fix before running sshd -t:
sudo mkdir -p /run/sshd
sudo sshd -t
```

Both `/var/run/sshd` and `/run/sshd` are symlinked to the same location.

### 1.2 Drop-in Config Directory

Ubuntu 24.04 has `Include /etc/ssh/sshd_config.d/*.conf` near the top of `sshd_config`. Drop-in files are parsed in lexicographic order; **first match wins**. Using drop-ins is recommended over editing the main file:

- Survives package upgrades
- Makes diffs readable
- Keeps changes explicit

**Recommended**: Create `50-hardening.conf` (or `99-hardening.conf`) in `/etc/ssh/sshd_config.d/`.

### 1.3 Deprecated/Removed Directives

- **`Protocol 2`** — ignored; modern OpenSSH is SSH-2 only.
- **`RSAAuthentication`** — removed.
- **`ChallengeResponseAuthentication`** — deprecated alias for `KbdInteractiveAuthentication`. Set both for compatibility.
- **DSA keys** — removed in OpenSSH 10.0. Use Ed25519 or RSA.

---

## 2. New User & Key Authentication Setup

### 2A: Create the User (if new)

```bash
sudo adduser <username>
sudo usermod -aG sudo <username>   # for sudo access if needed
```

### 2B: ssh-copy-id (Manual)

`ssh-copy-id` automates installing a public key onto a remote server. It:

1. Logs into the remote host with password
2. Creates `~/.ssh` and `~/.ssh/authorized_keys` if they don't exist (with `umask 077`)
3. Appends the public key (deduplicating by default)
4. Sets permissions: `~/.ssh` mode 0700, `~/.ssh/authorized_keys` mode 0600

**Source**: [OpenBSD's ssh-copy-id in contrib](https://github.com/openssh/openssh-portable/blob/master/contrib/ssh-copy-id)

```bash
# From LOCAL machine (with temporary password auth enabled):
ssh-copy-id -i ~/.ssh/id_ed25519.pub <username>@<vps-ip>
```

### 2C: Manual authorized_keys Setup (if ssh-copy-id unavailable)

```bash
# On the server as the target user:
mkdir -p ~/.ssh
chmod 700 ~/.ssh
# Paste public key into:
cat >> ~/.ssh/authorized_keys << 'EOF'
ssh-ed25519 AAAA... your-key-comment
EOF
chmod 600 ~/.ssh/authorized_keys
```

### 2D: Verify Key Auth Works

**BEFORE disabling password auth**, open a **second terminal** and test:

```bash
ssh -i ~/.ssh/id_ed25519 <username>@<vps-ip>
```

If it works without a password prompt, key auth is confirmed.

---

## 3. File Permission Requirements

| Path | Mode | Owner | Purpose |
|---|---|---|---|
| `~/.ssh/` | `0700` (drwx------) | User | Parent directory for all SSH files |
| `~/.ssh/authorized_keys` | `0600` (-rw-------) | User | Public keys allowed to authenticate |
| `~/.ssh/id_*` (private keys) | `0600` (-rw-------) | User | Private keys — highly sensitive |
| `~/.ssh/id_*.pub` (public keys) | `0644` (-rw-r--r--) | User | Public keys — not sensitive |
| `~/.ssh/config` | `0600` | User | Client config (contains host info) |
| `~/.ssh/known_hosts` | `0644` | User | Known remote host keys |
| `/etc/ssh/ssh_host_*` | `0600` | Root | Host private keys |
| `sshd_config` + drop-ins | `0644` | Root | Daemon config files |

**Check command**:
```bash
ls -la ~/.ssh/
# drwx------ 2 user user 4096 ...
# -rw------- 1 user user  789 ... authorized_keys
```

**Fix command**:
```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
chmod 600 ~/.ssh/id_*
```

---

## 4. sshd_config Validation (`sshd -t`)

### 4.1 How to Validate

```bash
sudo mkdir -p /run/sshd    # Ubuntu 24.04 workaround for socket activation
sudo sshd -t                # Silent = syntax OK; errors = fix before reload
```

### 4.2 View Effective Configuration

```bash
sudo sshd -T | grep -iE 'passwordauthentication|permitrootlogin|pubkeyauthentication|allowusers'
```

`sshd -T` dumps the **merged effective configuration** — all includes resolved, all defaults applied. This is the config sshd actually uses.

### 4.3 Backup Before Changes

```bash
sudo cp -a /etc/ssh /etc/ssh.backup.$(date +%Y%m%d)
sudo sshd -T > /root/sshd-effective-before.txt
```

---

## 5. Safe Reload vs Restart

| Action | Command | Existing Sessions | Risk Profile |
|---|---|---|---|
| **Reload** | `sudo systemctl reload ssh` | **Preserved** — SIGHUP sent to sshd | Low — broken config won't drop current sessions |
| **Restart** | `sudo systemctl restart ssh` | **Dropped** — service stopped and started | High — if config is broken, you're locked out |

**Rule**: Always prefer `reload` over `restart` for config changes.

**Ubuntu 24.04 note**: The service is called `ssh` (not `sshd`) on Debian/Ubuntu systems.

```bash
# Safe reload sequence:
sudo sshd -t && sudo systemctl reload ssh
```

---

## 6. Session Preservation Strategy

### 6.1 Golden Rules

1. **Never close your active session** until the new config is verified
2. **Open a second session** (new terminal) to test changes
3. **Test key auth BEFORE disabling password auth**
4. **Test as the new user BEFORE disabling root login**

### 6.2 Recovery on your VPS provider

Most VPS providers offer:
- **Web console / VNC** (Hetzner Console, DigitalOcean Recovery, Vultr SOL)
- **Serial console** via provider dashboard
- **Recovery mode / rescue system** that boots a minimal OS

**Always know your provider's out-of-band access method before starting.**

### 6.3 If Locked Out While Existing Session Is Alive

```bash
# From the still-connected session:
sudo nano /etc/ssh/sshd_config.d/50-hardening.conf
# Fix the issue (e.g., enable password auth temporarily)
sudo sshd -t && sudo systemctl reload ssh
```

### 6.4 If Completely Locked Out (No Active Session)

- Use VPS provider web console to log in as root
- Check journal: `journalctl -u ssh --no-pager | tail -20`
- Restore from backup: `sudo cp /etc/ssh.backup.20260531/sshd_config /etc/ssh/sshd_config`
- Or remove the problematic drop-in
- Reload SSH: `sudo systemctl reload ssh`

---

## 7. Disabling Password Auth (Safe Sequence)

**NEVER** disable password auth before verifying key auth works.

### Safe Staged Workflow

```bash
# Phase 1: Add key for the new user
ssh-copy-id -i ~/.ssh/id_ed25519.pub <newuser>@<vps-ip>

# Phase 2: Test key login from a SECOND terminal
ssh -i ~/.ssh/id_ed25519 <newuser>@<vps-ip>
# (close this test session, DO NOT close original)

# Phase 3: Create hardening drop-in
sudo tee /etc/ssh/sshd_config.d/50-hardening.conf > /dev/null << 'EOF'
# Managed hardening — Ubuntu 24.04
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
EOF

# Phase 4: Validate
sudo mkdir -p /run/sshd
sudo sshd -t && sudo systemctl reload ssh

# Phase 5: Verify from second terminal again
ssh -i ~/.ssh/id_ed25519 <newuser>@<vps-ip>
# If this works, you can now safely close the original session
```

---

## 8. Additional Hardening Directives (Stage After Verification)

After key auth is verified for all users, consider these:

```bash
# /etc/ssh/sshd_config.d/99-hardening-advanced.conf
# === Auth ===
MaxAuthTries 3
MaxSessions 3
LoginGraceTime 30
AuthenticationMethods publickey

# === Rate limiting ===
MaxStartups 10:30:60

# === Session hygiene ===
ClientAliveInterval 300
ClientAliveCountMax 2
TCPKeepAlive no

# === Forwarding (disable if not needed) ===
X11Forwarding no
AllowAgentForwarding no
AllowTcpForwarding no       # or yes if SSH tunneling needed
PermitTunnel no
PermitUserEnvironment no

# === Access control (whitelist) ===
AllowUsers <newuser> aizanta   # Add ALL users that need SSH

# === Logging ===
LogLevel VERBOSE
```

**CRITICAL GOTCHA with `AllowUsers` / `AllowGroups`**: Forgetting to include existing users (like `aizanta` or automation accounts) will lock them out. Always list ALL users that need access.

---

## 9. Sudoers Safety

### 9.1 Adding User to sudo Group

```bash
sudo usermod -aG sudo <username>
```

Use `-aG` (append, not replace) to avoid removing existing group memberships.

### 9.2 Test sudo in New Session

```bash
# After SSH key login as new user:
sudo whoami
# Should print: root
```

### 9.3 sudoers File Safety

- **Always use `visudo`** to edit sudoers — it validates syntax before saving
- Never edit `/etc/sudoers` directly with a text editor
- Custom rules go in `/etc/sudoers.d/` files (e.g., `/etc/sudoers.d/<username>`)
- A broken sudoers file can be recovered via: `pkexec visudo` or VPS web console

### 9.4 Passwordless sudo (Optional)

```bash
# /etc/sudoers.d/<username>
<username> ALL=(ALL) NOPASSWD: ALL
```

Use `visudo -f /etc/sudoers.d/<username>` to create.

---

## 10. Verified Safe Workflow — Complete Sequence

```text
1. Identify VPS provider's out-of-band access method (console/kvm)
2. Check existing users/groups: getent group sudo
3. BACKUP: sudo cp -a /etc/ssh /etc/ssh.backup.$(date +%Y%m%d)
4. Add new user (if needed): sudo adduser <user> && sudo usermod -aG sudo <user>
5. Install SSH key: ssh-copy-id -i ~/.ssh/id_ed25519.pub <user>@<vps-ip>
6. TEST KEY in second terminal (KEEP FIRST SESSION OPEN)
7. Create drop-in: apply hardening via /etc/ssh/sshd_config.d/50-hardening.conf
8. Validate: sudo mkdir -p /run/sshd && sudo sshd -t
9. RELOAD (not restart): sudo systemctl reload ssh
10. TEST NEW SESSION with key auth, verify sudo works
11. ONLY THEN close original session
12. Verify Aizanta and other existing users still have access
```

---

## 11. Source References

| Source | Evidence |
|---|---|
| **sshd_config(5)** man page | OpenBSD manual — [sshd_config(5)](https://man.openbsd.org/sshd_config.5). Key directives: `AuthorizedKeysFile`, `PasswordAuthentication`, `PermitRootLogin`, `KbdInteractiveAuthentication`, `AllowUsers`, `ClientAliveInterval`, `MaxAuthTries`, `MaxStartups` |
| **Ubuntu 24.04 socket activation** | [AskUbuntu: ssh/sshd breaking changes](https://askubuntu.com/questions/1550366/ssh-sshd-breaking-changes-in-24-04) — systemd socket activation, `/run/sshd` fix, `ssh.socket` vs `sshd.service` |
| **Cr0x SSH Hardening Checklist** | [cr0x.net: Ubuntu 24.04 SSH hardening](https://cr0x.net/en/ubuntu-ssh-hardening-checklist/) — Staged changes, verify before enforce, reload over restart, break-glass user, `sshd -T` for effective config |
| **Linuxize SSH Hardening Guide** | [linuxize.com: SSH Hardening](https://linuxize.com/post/ssh-hardening-best-practices/) — Key-based auth, `sshd -t` validation, `systemctl restart ssh`, permission requirements |
| **Big Iron: Hardening sshd_config** | [bigiron.cc/guides/hardening-sshd-config-on-debian-2026](https://www.bigiron.cc/guides/hardening-sshd-config-on-debian-2026) — Drop-in pattern, `Protocol` removed, `KbdInteractiveAuthentication`, `TCPKeepAlive no`, reload behavior |
| **OneUptime SSH Hardening** | [oneuptime.com/blog/post/2026-01-07-ubuntu-ssh-hardening](https://oneuptime.com/blog/post/2026-01-07-ubuntu-ssh-hardening/view) — Backup strategy, drop-in config, step-by-step hardening |
| **sshaudit.com Hardening Guides** | [sshaudit.com/hardening_guides.html](https://www.sshaudit.com/hardening_guides.html) — Ubuntu 24.04 specific: Ed25519 priority, KEX/Cipher/MAC allowlists, `RequiredRSASize 3072` |
| **HariSekhon: ssh.sh** | [GitHub: ~/.ssh manual setup pattern](https://github.com/HariSekhon/DevOps-Bash-tools/blob/master/.bash.d/ssh.sh#L170) — `umask 077`, `mkdir -p`, dedup keys, `chmod 0600` |
| **OpenBSD ssh-copy-id source** | [openssh-portable/contrib/ssh-copy-id](https://github.com/openssh/openssh-portable/blob/master/contrib/ssh-copy-id) — Source of `ssh-copy-id`: creates `.ssh` with 0700, appends key, sets 0600 on authorized_keys |
| **wp-in-a-box: safe reload pattern** | [GitHub: sshd -t && systemctl reload sshd](https://github.com/pothi/wp-in-a-box/blob/main/bookworm-deb-boot.sh#L244) — Production-proven pattern: validate then reload |
| **ZeonEdge: SSH Hardening 2026** | [zeonedge.com/blog/ssh-hardening-2026-complete-guide-linux-server](https://zeonedge.com/blog/ssh-hardening-2026-complete-guide-linux-server) — 99-hardening.conf example, `AuthenticationMethods publickey`, crypto hardening |
| **Vucense: Ubuntu 24.04 Security Checklist** | [vucense.com/dev-corner/ubuntu-24-04-lts-server-setup-post-install-security-checklist-2026](https://vucense.com/dev-corner/ubuntu-24-04-lts-server-setup-post-install-security-checklist-2026) — Drop-in pattern, `AllowUsers`, backup, reload |
| **Wikibooks OpenSSH Client Config** | [en.wikibooks.org/wiki/OpenSSH/Client_Configuration_Files](https://en.wikibooks.org/wiki/OpenSSH/Client_Configuration_Files) — authorized_keys, .ssh permissions, key management |
| **KDE: generate-and-send-ssh-key** | [GitHub: chmod pattern](https://github.com/centic9/generate-and-send-ssh-key/blob/master/generate-and-send-ssh-key.sh#L147) — `chmod go-w ~ && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys` |

---

## 12. Key Verdicts for Downstream (Parent Implementation)

| Topic | Verdict |
|---|---|
| **Primary access method** | `ssh-copy-id` or manual `mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat key >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys` |
| **Config validation** | `sudo mkdir -p /run/sshd && sudo sshd -t` **required** before any reload |
| **Reload vs restart** | **Always** `sudo systemctl reload ssh`. Never restart unless explicitly necessary. |
| **Session preservation** | Keep existing session open throughout; test new session in parallel terminal before closing old one |
| **Disable password auth** | Only AFTER verifying key auth works from second terminal |
| **Disable root login** | Only AFTER verifying sudo works for new user |
| **Ubuntu 24.04 trap** | Socket activation: use `ssh.socket` for status/enable, `ssh` for reload. `/run/sshd` may need `mkdir -p`. |
| **`AllowUsers` gotcha** | Must include ALL users that need access — forgetting existing users causes lockout |
| **Drop-in pattern** | Use `/etc/ssh/sshd_config.d/50-hardening.conf`, not direct edits to main sshd_config |
| **Sudoers safety** | Always `visudo`; use `/etc/sudoers.d/` for per-user config; test with `sudo whoami` in new session |
| **Backup first** | `sudo cp -a /etc/ssh /etc/ssh.backup.$(date +%Y%m%d)` before any changes |
| **Recovery plan** | Know VPS out-of-band console; restore from backup if locked out; reload not restart |
