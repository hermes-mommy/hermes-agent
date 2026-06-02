# STEP-P0-002 — External Readiness & Blocker Inventory

**Step:** P0-002 — SSH Config Update (alias + key-based auth)
**Phase:** P0 Infrastructure Foundation
**Date:** 2026-05-31
**Scope:** External prerequisites, Windows client considerations, ssh-copy-id alternatives, authorized_keys permissions, sshd validation, lockout rollback
**Focus:** Gaps between Unix-native StepPrompt and Windows-based operator environment

---

## 1. Host Prerequisites (VPS Side)

### 1.1 Non-Negotiable Prerequisites

| Prerequisite | Status | How to Verify | Requires VPS Access? |
|---|---|---|---|
| Ubuntu 24.04 (Noble) installed | ✅ Per P0-000 | `lsb_release -a` w/ root | Yes (existing root session) |
| OpenSSH server running | ✅ Per P0-000 | `systemctl is-active ssh.socket` | Yes |
| `guinevere` user exists | ✅ Per P0-001 | `id guinevere` | Yes (root session) |
| `guinevere` has sudo group | ✅ Per P0-001 | `groups guinevere` | Yes |
| VPS IPv4 address known | ❓ Check | From VPS provider dashboard or `ip addr` | Maybe |
| VPS provider web console known | ❓ Check | Hetzner Console / DigitalOcean Recovery / Vultr SOL | No (portal) |
| Root password available | ✅ Per P0-000 | Stored in secret management | No |
| Existing SSH session as root active | ❓ Check | From local machine | Pending |

### 1.2 Ubuntu 24.04 OpenSSH Version

```bash
# Check from existing root session:
ssh -V                  # Client version (on local machine)
ssh -o ProtocolKeepAlives=1 root@<vps-ip> "sshd -V 2>&1 || dpkg -l openssh-server | tail -1"
```

Ubuntu 24.04 ships **OpenSSH 9.6p1**. Key implications:

| Change | Impact on StepPrompt | Reference |
|---|---|---|
| **Socket activation** (`ssh.socket`) | `systemctl restart sshd` broken — use `ssh` not `sshd` for service name | [AskUbuntu: ssh/sshd breaking changes in 24.04](https://askubuntu.com/questions/1550366/ssh-sshd-breaking-changes-in-24-04) |
| `/run/sshd` may not exist | `sshd -t` fails without `sudo mkdir -p /run/sshd` first | cr0x SSH hardening guide |
| Drop-in config (`/etc/ssh/sshd_config.d/*.conf`) | Use `50-hardening.conf` instead of editing main config | [sshd_config(5)](https://man.openbsd.org/sshd_config.5) |
| `Protocol 2` directive ignored | Don't include — harmless but deprecated | bigiron.cc hardening guide |
| `ChallengeResponseAuthentication` deprecated | Use `KbdInteractiveAuthentication` instead | OpenSSH release notes |

### 1.3 Known Host Key (First Connection)

The first `ssh root@<vps-ip>` will prompt for host key verification:

```
The authenticity of host '<vps-ip>' can't be established.
ED25519 key fingerprint is SHA256:...
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

- **Blocker if non-interactive**: SSH commands in scripts will hang. Add `-o StrictHostKeyChecking=accept-new` for first connection, or verify fingerprint from provider dashboard.
- **Windows-specific**: OpenSSH for Windows stores known_hosts at `%USERPROFILE%\.ssh\known_hosts` — same path convention as Unix.

---

## 2. Windows/OpenSSH Client Considerations (CRITICAL GAPS)

The StepPrompt at lines 381–411 assumes a **Unix environment** with bash. The operator runs on **Windows 10/11 with PowerShell**. Every command category below has a Windows adaptation.

### 2.1 Path Convention Differences

| Unix Path | Windows Equivalent | Notes |
|---|---|---|
| `~/.ssh/` | `%USERPROFILE%\.ssh\` | PowerShell: `$env:USERPROFILE\.ssh\` |
| `~/.ssh/id_ed25519` | `%USERPROFILE%\.ssh\id_ed25519` | Same filename, different dir prefix |
| `~/.ssh/config` | `%USERPROFILE%\.ssh\config` | Same filename — **note: no extension** |
| `/etc/ssh/sshd_config` | (VPS-Linux only) | N/A for Windows client |
| `/etc/ssh/sshd_config.d/` | (VPS-Linux only) | N/A for Windows client |

**Critical**: PowerShell interprets `~` as `$env:USERPROFILE`, but the `ssh` command itself uses Unix-style paths in config files. The `config` file on Windows must use **forward slashes** or **escaped backslashes** for `IdentityFile`:

```
# Windows ~/.ssh/config — works:
IdentityFile C:/Users/samm/.ssh/id_ed25519
# Also works:
IdentityFile /C/Users/samm/.ssh/id_ed25519
```

**Source**: [Win32-OpenSSH wiki — Security protection of various files](https://github.com/PowerShell/Win32-OpenSSH/wiki/Security-protection-of-various-files-in-win32-openssh)

### 2.2 Command Translation Table

| StepPrompt Command (Unix) | Windows Equivalent | Notes |
|---|---|---|
| `test -f ~/.ssh/id_ed25519.pub \|\| ssh-keygen ...` | `if (-not (Test-Path "$env:USERPROFILE\.ssh\id_ed25519.pub")) { ssh-keygen -t ed25519 -C "samm@guinevere" -f "$env:USERPROFILE\.ssh\id_ed25519" -N """" }` | PowerShell conditional with double-escape on `-N ""` |
| `ssh-copy-id root@<vps-ip>` | See §3 below | **NOT AVAILABLE** on Windows OpenSSH |
| `cat >> ~/.ssh/config << 'EOF'` | See §2.3 below | Here-string via `Add-Content` or `Out-File -Append` |
| `chmod 600 ~/.ssh/config` | `icacls "$env:USERPROFILE\.ssh\config" /inheritance:r /grant "$env:USERNAME:(R,W)"` | Or use WSL `chmod` if available |
| `sed -i '/Host guinevere-vps/,/^$/d' ~/.ssh/config` | No direct equivalent — use `Get-Content` + filter + `Set-Content` | Rollback requires manual or scripted edit |

### 2.3 SSH Config File Creation on Windows

The StepPrompt heredoc approach (`cat >> ~/.ssh/config << 'EOF'`) does not work in PowerShell. Use this instead:

```powershell
# Create/append SSH config entry for guinevere-vps
@"
Host guinevere-vps
    HostName <vps-ip>
    User guinevere
    IdentityFile $env:USERPROFILE\.ssh\id_ed25519
    ServerAliveInterval 60
    ServerAliveCountMax 3
"@ | Add-Content -Path "$env:USERPROFILE\.ssh\config" -Encoding UTF8
```

**Source**: [Microsoft Learn — OpenSSH Key Management](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_keymanagement)

### 2.4 Windows Permission Model for SSH Files

On Windows, file permissions are ACL-based, not `chmod` octal. OpenSSH for Windows enforces strict ACL checks:

| File | Required ACL | Verification Command |
|---|---|---|
| `%USERPROFILE%\.ssh\` | Owner only (F) + SYSTEM (F) | `icacls "$env:USERPROFILE\.ssh"` |
| `%USERPROFILE%\.ssh\config` | Owner only (F), no other users | `icacls "$env:USERPROFILE\.ssh\config"` |
| `%USERPROFILE%\.ssh\id_ed25519` | Owner only (F) | `icacls "$env:USERPROFILE\.ssh\id_ed25519"` |
| `%USERPROFILE%\.ssh\authorized_keys` | Owner only (F) | (only on VPS/Linux) |

**Common Windows error**: `Bad owner or permissions on ~/.ssh/config`

**Fix**:
```powershell
# Remove inheritance and set owner-only access
icacls "$env:USERPROFILE\.ssh\config" /inheritance:r /grant "$env:USERNAME:(F)"
```

**Source**: [PowerShell/Win32-OpenSSH Issue #1722 — Bad owner or permissions](https://github.com/PowerShell/Win32-OpenSSH/issues/1722)

---

## 3. ssh-copy-id Alternatives on Windows

The StepPrompt at lines 386–389 uses `ssh-copy-id`, which **does not ship with Windows OpenSSH client**. This is a blocking gap.

### 3.1 Option Matrix

| Option | Effort | Dependencies | Risk | Recommended For |
|---|---|---|---|---|
| **A: PowerShell one-liner** | Minimal | OpenSSH client (built-in) | Low | First-time setup |
| **B: Manual SCP + append** | Medium | `scp` (built-in) | Low | When one-liner fails |
| **C: WSL ssh-copy-id** | Low | WSL installed + `ssh` package | Low | If WSL is already configured |
| **D: Third-party script** | Low | Download `.ps1` | Medium | Repeated use across hosts |
| **E: Git Bash ssh-copy-id** | Low | Git for Windows | Low | If Git Bash already installed |

### 3.2 Option A: PowerShell One-Liner (Recommended — No Dependencies)

This is the most portable and requires no additional software:

```powershell
# Copy id_ed25519.pub to root@<vps-ip>
type "$env:USERPROFILE\.ssh\id_ed25519.pub" | ssh root@<vps-ip> "umask 077; mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys"

# Copy id_ed25519.pub to guinevere@<vps-ip>
type "$env:USERPROFILE\.ssh\id_ed25519.pub" | ssh guinevere@<vps-ip> "umask 077; mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys"
```

**What this does** (same as `ssh-copy-id`):
1. Reads public key locally via `type` (PowerShell alias for `Get-Content`)
2. Pipes it through SSH session to remote host
3. Remote side runs: `umask 077` → `mkdir -p ~/.ssh` → `cat >> ~/.ssh/authorized_keys`
4. Correct permissions: `.ssh/` created with 0700, `authorized_keys` created with 0600 (via umask)

**Sources**:
- [Christopher Hart — Windows 10 OpenSSH Equivalent of ssh-copy-id](https://www.chrisjhart.com/Windows-10-ssh-copy-id/)
- [SuperUser — Alternative to ssh-copy-id on Windows](https://superuser.com/questions/1747549/alternative-to-ssh-copy-id-on-windows)
- [ServerFault — Is there an equivalent to ssh-copy-id for Windows?](https://serverfault.com/questions/224810/is-there-an-equivalent-to-ssh-copy-id-for-windows)

### 3.3 Option B: Manual SCP + SSH Append

For when the one-liner fails (e.g., no pipe support in some SSH configurations):

```powershell
# Step 1: Copy public key to VPS via SCP
scp "$env:USERPROFILE\.ssh\id_ed25519.pub" root@<vps-ip>:~/id_ed25519.pub.tmp

# Step 2: SSH in and append to authorized_keys
ssh root@<vps-ip> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat ~/id_ed25519.pub.tmp >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && rm ~/id_ed25519.pub.tmp"
```

### 3.4 Option C: WSL ssh-copy-id

If WSL is already installed on the operator machine:

```powershell
wsl ssh-copy-id -i ~/.ssh/id_ed25519.pub root@<vps-ip>
```

**Caveat**: WSL paths (`~/.ssh/`) map to WSL's own home, not Windows `%USERPROFILE%\.ssh\`. You may need to copy keys or use `wslpath`:

```powershell
wsl ssh-copy-id -i "$(wslpath "$env:USERPROFILE\.ssh\id_ed25519.pub")" root@<vps-ip>
```

### 3.5 Option D: PowerShell ssh-copy-id Script

Third-party script (not in repo, download from GitHub):

```powershell
# Download and run
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/joshkerr/ssh-copy-id/main/ssh-copy-id-simple.ps1" -OutFile "$env:TEMP\ssh-copy-id.ps1"
powershell "$env:TEMP\ssh-copy-id.ps1" root@<vps-ip>
```

**Source**: [joshkerr/ssh-copy-id on GitHub](https://github.com/joshkerr/ssh-copy-id)

### 3.6 Option E: Git Bash ssh-copy-id

If Git for Windows is installed, `ssh-copy-id` ships with its Git Bash:

```powershell
# Using Git Bash's ssh-copy-id
& "C:\Program Files\Git\usr\bin\ssh-copy-id" -i "$env:USERPROFILE\.ssh\id_ed25519.pub" root@<vps-ip>
```

---

## 4. authorized_keys Permissions (VPS Linux Side)

### 4.1 Required Permissions

| Path | Mode | Owner | Purpose |
|---|---|---|---|
| `~/.ssh/` | `0700` (drwx------) | Target user | Parent directory |
| `~/.ssh/authorized_keys` | `0600` (-rw-------) | Target user | Authorized public keys |
| `~/.ssh/authorized_keys2` | `0600` | Target user | Fallback (rarely used) |

**Fix commands** (run on VPS):
```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
chown $(whoami):$(whoami) ~/.ssh/authorized_keys
```

### 4.2 The `ssh-copy-id` Guarantee

The `ssh-copy-id` tool (and the PowerShell one-liner with `umask 077`) automatically sets correct permissions. If doing manual copy, you MUST set them explicitly or key auth will fail silently:

```
ssh user@host "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

**Source**: [OpenBSD's ssh-copy-id in contrib](https://github.com/openssh/openssh-portable/blob/master/contrib/ssh-copy-id) — Lines 170-180 show `umask 077` + `mkdir -p .ssh` + `cat >> .ssh/authorized_keys`

### 4.3 Why Wrong Permissions Fail Silently

OpenSSH server (`sshd`) checks permissions on `authorized_keys` before accepting them:

- If `~/.ssh/` is group-writable or other-writable → **key ignored**
- If `authorized_keys` is group-writable or other-writable → **key ignored**
- If `~/.ssh/` or `authorized_keys` is owned by wrong user → **key ignored**
- `sshd` does NOT log "permissions wrong" at default `LogLevel` — it just falls through to the next auth method

**Debug** (on VPS):
```bash
# Check sshd log for details:
journalctl -u ssh --no-pager | tail -20
# Or in real-time:
sudo tail -f /var/log/auth.log | grep sshd
```

### 4.4 Administrators_authorized_keys (Windows SSH Server Only)

If the VPS were a Windows SSH server (it's not — it's Ubuntu), administrators would need `%ProgramData%\ssh\administrators_authorized_keys` with ACL of `SYSTEM:F` + `Administrators:F`. This is **NOT applicable** to the Ubuntu target.

**Source**: [Microsoft Learn — OpenSSH Key Management](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_keymanagement), [PowerShell/Win32-OpenSSH Wiki](https://github.com/PowerShell/Win32-OpenSSH/wiki)

---

## 5. sshd Validation Commands

### 5.1 Safe Validation Sequence (Run on VPS Before Disconnecting)

Always validate BEFORE applying changes that could lock you out:

```bash
# Step 1: Backup existing SSH config
sudo cp -a /etc/ssh /etc/ssh.backup.$(date +%Y%m%d)

# Step 2: Dump effective config for comparison
sudo sshd -T > /root/sshd-effective-before.txt

# Step 3: Create hardening drop-in
sudo tee /etc/ssh/sshd_config.d/50-hardening.conf > /dev/null << 'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
EOF

# Step 4: Validate syntax (Ubuntu 24.04 workaround)
sudo mkdir -p /run/sshd
sudo sshd -t
# Silent = syntax OK; errors = fix before proceeding

# Step 5: Reload (NOT restart) to apply changes
sudo sshd -t && sudo systemctl reload ssh
```

### 5.2 Key Validation Commands

| Command | What It Checks | Example Output |
|---|---|---|
| `sudo sshd -t` | Syntax check (silent = OK) | (no output = valid) |
| `sudo sshd -T \| grep -iE 'passwordauth\|permitrootlogin\|pubkeyauth'` | Effective config values | `passwordauthentication no` |
| `sudo sshd -T \| grep -i 'allowusers'` | User whitelist (if set) | `allowusers guinevere aizanta` |
| `systemctl is-active ssh.socket` | Socket activation status | `active` |
| `systemctl status ssh --no-pager` | SSH service detailed status | `● ssh.service - OpenSSH...` |
| `journalctl -u ssh --no-pager \| tail -20` | Recent SSH auth logs | `Accepted publickey for guinevere...` |

**Source**: [sshd_config(5)](https://man.openbsd.org/sshd_config.5), [sshaudit.com hardening guides](https://www.sshaudit.com/hardening_guides.html)

### 5.3 Ubuntu 24.04 Socket Activation Trap

```bash
# ❌ WRONG — will not work on Ubuntu 24.04:
systemctl restart sshd

# ✅ CORRECT — service is called "ssh" not "sshd":
systemctl status ssh      # check status
systemctl reload ssh       # apply config changes safely
systemctl restart ssh      # only if absolutely necessary (drops sessions)
```

---

## 6. Lockout Rollback Strategy

### 6.1 Prevention (Must Do Before Hardening)

| Rule | Why |
|---|---|
| **Keep active session alive** | Never close the root session until key auth is verified for ALL users |
| **Test in second terminal** | Open NEW terminal/window — verify key auth works there |
| **Test AS EACH USER** | Verify both `guinevere` and existing users (`aizanta`) can still log in |
| **Verify sudo works** | `sudo whoami` must return `root` for guinevere user |
| **Backup before changes** | `sudo cp -a /etc/ssh /etc.ssh.backup.$(date +%Y%m%d)` |
| **Prefer reload over restart** | `sudo sshd -t && sudo systemctl reload ssh` — reload preserves sessions |

### 6.2 Rollback Scenarios

#### Scenario A: Still Connected (Active Session Alive)

```bash
# From the still-open root session:
sudo rm /etc/ssh/sshd_config.d/50-hardening.conf
sudo sshd -t && sudo systemctl reload ssh
```

#### Scenario B: Disconnected But Password Auth Failed

If `PasswordAuthentication no` breaks password-based fallback but key auth also fails:

```bash
# Use VPS provider web console (Hetzner Console / DigitalOcean Recovery)
# Log in as root via console
sudo nano /etc/ssh/sshd_config.d/50-hardening.conf
# Delete or comment out the problematic line
sudo sshd -t && sudo systemctl reload ssh
```

#### Scenario C: Completely Locked Out

| Recovery Method | Access | Time Estimate |
|---|---|---|
| VPS provider web console | Direct root shell via browser | 2-5 min |
| Rescue mode / recovery ISO | Boot minimal OS, mount filesystem, fix config | 10-15 min |
| Provider API reboot + cloud-init | If cloud-init configured with recovery script | 5-10 min |

**Critical Pre-flight**: Confirm VPS provider's out-of-band access method BEFORE starting P0-002.

### 6.3 Windows-Side Rollback (Local SSH Config)

```powershell
# Remove guinevere-vps alias from config
$config = Get-Content "$env:USERPROFILE\.ssh\config"
$newConfig = $config -notmatch '(?s)Host guinevere-vps.*?(?=\n\S|\z)'
$newConfig | Set-Content "$env:USERPROFILE\.ssh\config" -Encoding UTF8
```

Or manually edit `%USERPROFILE%\.ssh\config` in Notepad.

### 6.4 VPS-Side Rollback Script Template

Save this on VPS before hardening (requires existing session):

```bash
cat > /root/rollback-ssh.sh << 'ROLLBACK'
#!/bin/bash
# Rollback SSH hardening from P0-002
set -euo pipefail
BACKUP_DIR="/etc/ssh.backup.$(date +%Y%m%d)"
if [ -d "$BACKUP_DIR" ]; then
    rm -f /etc/ssh/sshd_config.d/50-hardening.conf
    sudo sshd -t && sudo systemctl reload ssh
    echo "Rollback applied. SSH config restored."
else
    echo "No backup found at $BACKUP_DIR"
    exit 1
fi
ROLLBACK
chmod +x /root/rollback-ssh.sh
```

**Location to keep**: `/root/rollback-ssh.sh` on the VPS (run before disabling password auth).

---

## 7. Blocker Summary

### 7.1 Critical Blockers (Must Resolve Before Starting)

| # | Blocker | Affected StepPrompt Line | Resolution |
|---|---|---|---|
| B1 | `ssh-copy-id` not available on Windows | 386, 389 | Use PowerShell one-liner (§3.2) |
| B2 | StepPrompt uses `bash` heredoc for config | 392-399 | Use `Add-Content` in PowerShell (§2.3) |
| B3 | `chmod 600` on Windows has no direct equivalent | 402 | Use `icacls` or skip (Windows SSH reads ACL not Unix perms) |
| B4 | `sed -i` rollback not available on Windows | 426 | Use PowerShell regex filter (§6.3) |
| B5 | StepPrompt references `~/.ssh/` — works on Windows but path semantics differ | 382-411 | Forward-slash paths in config file; `$env:USERPROFILE` in PowerShell (§2.1) |

### 7.2 Warning Blockers (Must Know Before Starting)

| # | Blocker | Risk | Mitigation |
|---|---|---|---|
| W1 | `sshd -t` fails on Ubuntu 24.04 without `/run/sshd` | Medium — validation step fails | Run `sudo mkdir -p /run/sshd` first (§5.1) |
| W2 | Service is `ssh` not `sshd` on Ubuntu/Debian | Medium — wrong command silently fails | Use `systemctl reload ssh` (§5.3) |
| W3 | VPS provider console access not verified | High — no fallback if locked out | Confirm before starting (§6.2) |
| W4 | Existing users (`aizanta`) must be included if `AllowUsers` is set | High — can lock out existing sessions | List ALL users in `AllowUsers` (see SSH safety research §8) |
| W5 | `known_hosts` first-connection prompt blocks automation | Low — workaround available | Use `-o StrictHostKeyChecking=accept-new` for first connection (§1.3) |

### 7.3 Information Blockers (Need Operator Input)

| # | Item | Required From |
|---|---|---|
| I1 | VPS IP address (for `<vps-ip>` placeholders) | VPS provider dashboard or P0-000 output |
| I2 | VPS provider name + console URL | Operator knowledge |
| I3 | Confirm root password is accessible | Operator |
| I4 | Decide whether password auth should remain enabled temporarily | Operator preference |
| I5 | Confirm `aizanta` user exists and has working key auth (pre-existing) | Existing SSH setup |

---

## 8. Adapted Execution Sequence for Windows

Complete sequence that accounts for all blockers above:

```powershell
# ============================================================
# STEP-P0-002: EXECUTION SEQUENCE (Windows-Adapted)
# ============================================================
# Prerequisites:
#   1. VPS IP known -> set $VPS_IP
#   2. Root password accessible
#   3. VPS console access confirmed
#   4. P0-001 complete (guinevere user exists)
# ============================================================

# ---- Phase 1: Verify local key exists ----
if (-not (Test-Path "$env:USERPROFILE\.ssh\id_ed25519.pub")) {
    ssh-keygen -t ed25519 -C "samm@guinevere" -f "$env:USERPROFILE\.ssh\id_ed25519" -N '""'
}

# ---- Phase 2: Copy key to VPS (ssh-copy-id equivalent) ----
# For root (password prompt will appear — this is the ONE TIME)
type "$env:USERPROFILE\.ssh\id_ed25519.pub" | ssh root@<vps-ip> "umask 077; mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys"

# For guinevere
type "$env:USERPROFILE\.ssh\id_ed25519.pub" | ssh guinevere@<vps-ip> "umask 077; mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys"

# ---- Phase 3: Verify key auth (KEEP FIRST SESSION OPEN) ----
# Open NEW PowerShell window and test:
ssh -o StrictHostKeyChecking=accept-new guinevere@<vps-ip> "whoami && hostname"
# Should return: guinevere + hostname (no password prompt)

# ---- Phase 4: Add SSH alias to local config ----
@"
Host guinevere-vps
    HostName <vps-ip>
    User guinevere
    IdentityFile $env:USERPROFILE\.ssh\id_ed25519
    ServerAliveInterval 60
    ServerAliveCountMax 3
"@ | Add-Content -Path "$env:USERPROFILE\.ssh\config" -Encoding UTF8

# Fix Windows config permissions (if SSH complains)
icacls "$env:USERPROFILE\.ssh\config" /inheritance:r /grant "$env:USERNAME:(F)" 2>$null

# ---- Phase 5: Test alias ----
ssh guinevere-vps "whoami && hostname"

# ---- Phase 6: Harden SSH (VPS side - via existing root session) ----
# SSH into VPS as root, then run:
#   sudo cp -a /etc/ssh /etc/ssh.backup.$(date +%Y%m%d)
#   sudo tee /etc/ssh/sshd_config.d/50-hardening.conf > /dev/null << 'EOF'
#   PasswordAuthentication no
#   KbdInteractiveAuthentication no
#   PubkeyAuthentication yes
#   PermitRootLogin no
#   EOF
#   sudo mkdir -p /run/sshd
#   sudo sshd -t && sudo systemctl reload ssh
#
# ---- Phase 7: Verify from second terminal ----
# ssh guinevere-vps "whoami && hostname"
# THEN close original root session
```

---

## 9. References

### Official Documentation

| Source | URL | Relevance |
|---|---|---|
| Microsoft Learn — OpenSSH Key Management | [learn.microsoft.com/.../openssh_keymanagement](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_keymanagement) | Windows SSH key setup, administrators_authorized_keys |
| Win32-OpenSSH Wiki — Permission Security | [github.com/PowerShell/Win32-OpenSSH/wiki/...](https://github.com/PowerShell/Win32-OpenSSH/wiki/Security-protection-of-various-files-in-win32-openssh) | Windows ACL requirements for SSH files |
| sshd_config(5) man page | [man.openbsd.org/sshd_config.5](https://man.openbsd.org/sshd_config.5) | All sshd directives, default values |
| ssh_config(5) man page | [man.openbsd.org/ssh_config.5](https://man.openbsd.org/ssh_config.5) | Client config file format, supported directives |
| OpenBSD ssh-copy-id source | [openssh-portable/contrib/ssh-copy-id](https://github.com/openssh/openssh-portable/blob/master/contrib/ssh-copy-id) | Reference implementation — umask 077, mkdir, cat append |

### Windows-Specific References

| Source | URL | Relevance |
|---|---|---|
| Christopher Hart — Windows ssh-copy-id equivalent | [chrisjhart.com/Windows-10-ssh-copy-id](https://www.chrisjhart.com/Windows-10-ssh-copy-id/) | PowerShell one-liner pattern |
| SuperUser — alternative to ssh-copy-id on Windows | [superuser.com/q/1747549](https://superuser.com/questions/1747549/alternative-to-ssh-copy-id-on-windows) | `type` + `ssh` pipe pattern |
| ServerFault — equivalent to ssh-copy-id for Windows | [serverfault.com/q/224810](https://serverfault.com/questions/224810/is-there-an-equivalent-to-ssh-copy-id-for-windows) | Multiple methods (script, Git Bash, manual) |
| GitHub Issue #1722 — Bad owner or permissions | [github.com/PowerShell/Win32-OpenSSH/issues/1722](https://github.com/PowerShell/Win32-OpenSSH/issues/1722) | Windows config file permission errors |
| GitHub Issue #2301 — Request ssh-copy-id | [github.com/PowerShell/Win32-OpenSSH/issues/2301](https://github.com/PowerShell/Win32-OpenSSH/issues/2301) | Official feature request (still open) |

### Ubuntu 24.04 & SSH Hardening References

| Source | URL | Relevance |
|---|---|---|
| AskUbuntu — ssh/sshd breaking changes in 24.04 | [askubuntu.com/q/1550366](https://askubuntu.com/questions/1550366/ssh-sshd-breaking-changes-in-24-04) | Socket activation, service name, /run/sshd |
| cr0x Ubuntu SSH hardening checklist | [cr0x.net/en/ubuntu-ssh-hardening-checklist](https://cr0x.net/en/ubuntu-ssh-hardening-checklist/) | Staged changes, verify before enforce, reload over restart |
| sshaudit.com hardening guides | [sshaudit.com/hardening_guides.html](https://www.sshaudit.com/hardening_guides.html) | Ubuntu 24.04 crypto/cipher hardening |
| Linuxize SSH hardening guide | [linuxize.com/post/ssh-hardening-best-practices](https://linuxize.com/post/ssh-hardening-best-practices/) | Key-based auth, sshd -t, permissions |
| Bigiron hardening sshd_config on Debian | [bigiron.cc/guides/hardening-sshd-config-on-debian-2026](https://www.bigiron.cc/guides/hardening-sshd-config-on-debian-2026) | Drop-in pattern, KbdInteractiveAuthentication, reload behavior |
| OneUptime Ubuntu SSH hardening | [oneuptime.com/blog/post/2026-01-07-ubuntu-ssh-hardening](https://oneuptime.com/blog/post/2026-01-07-ubuntu-ssh-hardening/view) | Backup strategy, step-by-step |

### Third-Party Tools on GitHub

| Source | URL | Relevance |
|---|---|---|
| joshkerr/ssh-copy-id (PowerShell) | [github.com/joshkerr/ssh-copy-id](https://github.com/joshkerr/ssh-copy-id) | Native Windows ssh-copy-id implementation |
| kwrkb/ssh-pushkey | [github.com/kwrkb/ssh-pushkey](https://github.com/kwrkb/ssh-pushkey) | SSH public key deployment for Windows, handles ACL |
| n8tg/ssh-copy-id (PowerShell) | [github.com/n8tg/ssh-copy-id](https://github.com/n8tg/ssh-copy-id) | Another PowerShell ssh-copy-id implementation |
| CharlesGodwin gist — ssh-copy-id for Windows | [gist.github.com/CharlesGodwin/93f858...](https://gist.github.com/CharlesGodwin/93f85838c8dbb2c4f931a3c52e598dfa) | PowerShell script with auto-detect, dedup logic |
| crosstyan gist — Windows ssh-copy-id | [gist.github.com/crosstyan/ba26b27...](https://gist.github.com/crosstyan/ba26b27e9ce38ab410322f10e267c06c) | WSL-based approach + PowerShell fallback |

---

## 10. Verdict

**Readiness Status**: ⚠️ **BLOCKED — 5 Critical Issues** (B1–B5)

**The StepPrompt is not directly executable from a Windows environment.** Every command operates under Unix assumptions (bash, `ssh-copy-id`, `chmod`, `sed`, heredoc). While the concepts are correct, the operator on Windows needs adapted alternatives for every phase.

**Summary of adaptations required**:
1. Replace `ssh-copy-id` with PowerShell one-liner pipe (`type ... | ssh ... "umask 077; mkdir -p; cat >> ..."`)
2. Replace heredoc config creation with `Add-Content` / here-string
3. Skip or adapt `chmod 600` — Windows uses ACL (`icacls`)
4. Replace `sed -i` rollback with PowerShell filter
5. Verify VPS console access before hardening (safety net)

**All 5 critical blockers have documented workarounds** in this report. No blocker requires changes to the VPS or additional software purchases.
