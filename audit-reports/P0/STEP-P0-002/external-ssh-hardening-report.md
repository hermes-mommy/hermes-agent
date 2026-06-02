# External Research Report: SSH Hardening & Safe Rollout — Ubuntu 24.04 / OpenSSH

**Task**: STEP-P0-002  
**Date**: 2026-05-31  
**Scope**: Best-practice sshd_config hardening, safe rollout sequence, lockout prevention, fail2ban/CrowdSec readiness  
**Target**: Ubuntu 24.04 LTS (Noble Numbat) — OpenSSH 9.6p1 (patched)

---

## 1. Pre-Flight: Know Your Current State

Before changing anything, inventory the effective configuration and existing access paths:

| Action | Command | Purpose |
|---|---|---|
| Check OpenSSH version | `sshd -V` or `dpkg -l openssh-server` | Confirm patched against CVE-2024-6387 (≥ `1:9.6p1-3ubuntu13.3`) |
| Effective config dump | `sudo sshd -T` | Show merged config (includes + defaults) |
| Validate syntax | `sudo sshd -t` | No output = OK. **Never reload if this fails.** |
| List listeners | `sudo ss -tulpn \| grep sshd` | Confirm which ports/interfaces sshd binds |
| Check firewall | `sudo ufw status verbose` or `sudo nft list ruleset` | Know what's allowed before changing |
| Backup config | `sudo cp -a /etc/ssh /etc/ssh.back.$(date +%F)` | Rollback path |

**Official refs**:
- [sshd_config(5) — OpenBSD man pages](https://man.openbsd.org/sshd_config.5) — canonical reference for all directives
- [sshd(8) — OpenBSD man pages](https://man.openbsd.org/OpenBSD-7.7/sshd.8) — `-t` test mode, `-T` extended test mode, SIGHUP reload
- [Ubuntu manpage: sshd_config](https://manpages.ubuntu.com/manpages/kinetic/man5/sshd_config.5.html) — Debian/Ubuntu-specific defaults (Include directive, KbdInteractiveAuthentication default)

---

## 2. Core Hardening Directives

### 2.1 Authentication & Access Control

**Always use a drop-in file** (`/etc/ssh/sshd_config.d/50-hardening.conf`) — survives package upgrades, clean diffs, explicit ownership. Ubuntu 24.04's `sshd_config` already has `Include /etc/ssh/sshd_config.d/*.conf` at the top.

```
# /etc/ssh/sshd_config.d/50-hardening.conf

# === AUTHENTICATION ===
PermitRootLogin no                  # Non-negotiable. Use sudo.
PasswordAuthentication no           # After verifying key auth works
KbdInteractiveAuthentication no     # Replaces ChallengeResponseAuthentication in OpenSSH 9.x
PubkeyAuthentication yes            # Explicitly enable
AuthenticationMethods publickey     # Require key auth; no password fallback

# === RATE LIMITING ===
MaxAuthTries 3                      # Per-connection auth attempts
MaxSessions 3                       # Concurrent sessions per connection
LoginGraceTime 20                   # Seconds to complete auth (default 120)
MaxStartups 10:30:60                # Start dropping 30% of conns at 10 unauthenticated; drop all at 60
# PerSourcePenalties crash:90 authfail:5 noauth:1 grace-exceeded:20 max:600   # OpenSSH 9.8+ only

# === SESSION HYGIENE ===
ClientAliveInterval 300             # Send keepalive every 5 min
ClientAliveCountMax 2               # Disconnect after 2 missed (10 min total)
TCPKeepAlive yes

# === FORWARDING (disable unless needed) ===
X11Forwarding no
AllowAgentForwarding no
AllowTcpForwarding no
PermitTunnel no
PermitUserEnvironment no

# === LOGGING ===
LogLevel VERBOSE                    # Logs key fingerprint per auth
SyslogFacility AUTH

# === BANNER / INFO LEAKAGE ===
DebianBanner no                     # Hide OS version from SSH banner
# Banner /etc/ssh/banner.txt       # Optional legal notice

# === ALLOWLIST (choose one pattern) ===
# AllowGroups ssh-users             # Group-based (easier to manage)
# AllowUsers deploy admin           # User-based (explicit)
```

**Key interactions:**
- `AllowUsers` and `AllowGroups` are evaluated in order: DenyUsers → AllowUsers → DenyGroups → AllowGroups. A deny at any stage blocks the user.
- `AuthenticationMethods publickey` is strict — removes any password/keyboard-interactive path.
- On Ubuntu 24.04, `KbdInteractiveAuthentication` replaces the deprecated `ChallengeResponseAuthentication`. Set **both** to `no` for compatibility across OpenSSH versions.

### 2.2 Cryptographic Algorithms (Optional — When Compliance Requires It)

Ubuntu 24.04's OpenSSH 9.6 defaults are already modern. **Algorithm pinning is not required for most deployments** and can cause client compatibility issues. Only pin when compliance (CIS, STIG, PCI-DSS) demands it.

If pinning is needed, the [sshaudit.com hardening guide](https://www.sshaudit.com/hardening_guides.html) recommends:

```
HostKey /etc/ssh/ssh_host_ed25519_key        # Prefer Ed25519 over RSA
HostKey /etc/ssh/ssh_host_rsa_key            # Keep RSA for older clients

KexAlgorithms sntrup761x25519-sha512@openssh.com,curve25519-sha256,curve25519-sha256@libssh.org,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512

Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes256-ctr,aes192-ctr,aes128-gcm@openssh.com,aes128-ctr

MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,umac-128-etm@openssh.com

RequiredRSASize 3072
PubkeyAcceptedAlgorithms sk-ssh-ed25519-cert-v01@openssh.com,ssh-ed25519-cert-v01@openssh.com,rsa-sha2-512-cert-v01@openssh.com,rsa-sha2-256-cert-v01@openssh.com,sk-ssh-ed25519@openssh.com,ssh-ed25519,rsa-sha2-512,rsa-sha2-256
```

> **Risk**: Algorithm pinning freezes your crypto at current best-practice. Package updates won't introduce new algorithms. Audit periodically and update pinned lists when OpenSSH deprecates older algorithms.

### 2.3 Break-Glass / Emergency Access

Always keep an alternative access path before locking down:

1. **Console access** (cloud serial console, IPMI/iDRAC, KVM) — test that it works before starting.
2. **Break-glass user** — a dedicated user with key-only auth, sudo access, and a known-working key.
3. **Canary sshd on alternate port** — temporarily run a second sshd instance on a different port with the new strict config, test it, then apply to the real daemon.

**Match blocks** let you scope looser settings for emergency users while enforcing strict defaults for everyone:

```
Match User breakglass
    PasswordAuthentication no
    PubkeyAuthentication yes
    PermitRootLogin no
    # But allow TCP forwarding if needed for tunnels
    AllowTcpForwarding yes
```

---

## 3. Safe Rollout Sequence (Lockout Prevention)

This is the single most critical section. SSH lockouts are almost always self-inflicted, and entirely preventable.

### 3.1 Golden Rules

1. **Never close your existing SSH session** until a *new* session successfully authenticates with the new config.
2. **Always run `sudo sshd -t` before any reload.** No output = syntax OK. Errors = fix before proceeding.
3. **Prefer `systemctl reload ssh` over `restart`.** Reload sends SIGHUP — existing sessions survive. Restart tears down the daemon.
4. **Stage changes.** Apply network controls first, then key auth, then disable passwords, then root login.
5. **Test from a second terminal, not the one you're editing from.**

### 3.2 Staged Rollout Plan

```
Phase 0: Pre-flight
├── sudo sshd -T > /root/sshd-effective.before    # Record baseline
├── sudo cp -a /etc/ssh /etc/ssh.back.$(date +%F) # Full backup
├── sudo sshd -t                                   # Confirm current config is valid
└── Verify console/out-of-band access works

Phase 1: Network-first tightening
├── Add UFW/nftables allow rules for admin IPs/VPN ranges (add before remove)
├── Test connectivity from each allowed network
└── Only then remove broad "Anywhere" rules

Phase 2: Key auth verification (before disabling passwords)
├── Ensure every admin user has a working key pair deployed
├── ssh-copy-id user@server                         # Deploy public key
├── ssh -o PasswordAuthentication=no user@server    # Test key-only login
├── Verify automation/service accounts too
└── Do NOT disable passwords yet

Phase 3: Apply hardening drop-in
├── Write /etc/ssh/sshd_config.d/50-hardening.conf
├── sudo sshd -t                                    # MUST pass
├── sudo sshd -T | grep -E 'passwordauth|permitroot|allowusers'  # Verify effective
├── sudo systemctl reload ssh                       # Reload (not restart)
├── From a NEW terminal: ssh user@server            # Test fresh login
├── Keep old session open until new one works
└── Only close old session after confirming new connection

Phase 4: Verify + monitor
├── ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no user@server
│   └── Should return "Permission denied (publickey)"
├── ssh root@server
│   └── Should return "Permission denied"
├── sudo journalctl -u ssh -n 20                    # Check auth logs
├── Run ssh-audit against server                    # Verify no [fail] entries
└── Monitor logs daily for 1 week after enforcement
```

### 3.3 Important: `sshd -t` vs `sshd -T` vs `sshd -G`

| Flag | What it does | When to use |
|---|---|---|
| `sshd -t` | Test mode — validates config syntax and host key sanity. No output = OK. | **Every single time** before reload |
| `sshd -T` | Extended test mode — prints the *effective* merged config to stdout (includes defaults, all include files) | After reload to verify changes took effect |
| `sshd -G` | Parse and print config (like `-T` but without key sanity checks) | Staging a config before host keys exist |
| `sshd -t -f /path/to/file` | Test a *staged* config file before it goes live | Validating proposed changes before deploy |

### 3.4 Recovery: What To Do If Locked Out

| Symptom | Likely Cause | Fix |
|---|---|---|
| "Connection refused" | sshd not listening (bad config, failed reload, wrong port) | Use console/VNC, check `sshd -t`, `journalctl -u ssh`, fix and reload |
| "Permission denied (publickey)" | Key auth fails (wrong key, bad `~/.ssh` permissions, AllowUsers typo) | From existing session: `sshd -T` to verify effective config; check `~/.ssh` perms (700/600) |
| "Connection timed out" | Firewall blocking new port or IP | Check UFW/nftables/cloud SG rules |
| Reload succeeded but no new logins | `AllowUsers` or `AllowGroups` excludes you, or `AuthenticationMethods` too strict | Use existing session to fix the drop-in, `sshd -t`, reload |

**If you have no existing session**: Use out-of-band console (cloud provider serial console, IPMI, iDRAC, KVM). Fix the config, run `sshd -t`, then `systemctl reload ssh`. If no console access exists, attach the system disk to another instance, fix the config file, re-attach.

---

## 4. Relevant sshd_config Options — Reference

| Directive | Recommended | Default (Ubuntu 24.04) | Notes |
|---|---|---|---|
| `PermitRootLogin` | `no` | `prohibit-password` | Use `prohibit-password` only if root key login is unavoidable |
| `PasswordAuthentication` | `no` | `yes` | **Most impactful single change** — eliminates brute-force vector |
| `KbdInteractiveAuthentication` | `no` | `no` (Ubuntu default) | Must also be set; replaces deprecated `ChallengeResponseAuthentication` |
| `PubkeyAuthentication` | `yes` | `yes` | Explicitly enable when disabling passwords |
| `AuthorizedKeysFile` | `.ssh/authorized_keys` (default) | `.ssh/authorized_keys .ssh/authorized_keys2` | Default is fine; consider `AuthorizedKeysCommand` for centralized key mgmt |
| `AllowUsers` / `AllowGroups` | Set one | (not set) | **Whitelist approach** — blocks all unlisted users. Test before applying |
| `AuthenticationMethods` | `publickey` | `any` | Strict key-only. Removes all non-key auth paths |
| `MaxAuthTries` | `3` | `6` | Per-connection limit; protects against brute-force |
| `LoginGraceTime` | `20` | `120` | Time window to complete auth; shorter = less DoS surface |
| `MaxStartups` | `10:30:60` | `10:30:100` | Connection rate throttling (DHEat DoS mitigation) |
| `ClientAliveInterval` | `300` | `0` (no keepalive) | Cleans up dead/stale sessions |
| `ClientAliveCountMax` | `2` | `3` | Disconnect after N missed keepalives |
| `X11Forwarding` | `no` | `yes` (Ubuntu) | Disable unless GUI forwarding is explicitly needed |
| `AllowAgentForwarding` | `no` | `yes` | Disable unless SSH agent forwarding workflow exists |
| `AllowTcpForwarding` | `no` | `yes` | Disable unless SSH tunneling is required |
| `LogLevel` | `VERBOSE` | `INFO` | Logs key fingerprint — critical for audit trail |
| `DebianBanner` | `no` | `yes` | Hides OS version from SSH banner |

> **Note on `AuthorizedKeysFile`**: The default (`.ssh/authorized_keys`) is sufficient for most deployments. For fleets, consider `AuthorizedKeysCommand` with a central key store, or SSH Certificate Authority (CA) — both eliminate authorized_keys sprawl.

---

## 5. Fail2Ban & CrowdSec Readiness

### 5.1 Fail2Ban — Recommended Baseline

Fail2Ban monitors auth logs and temporarily bans IPs after repeated failures. Install from Ubuntu repos:

```ini
# /etc/fail2ban/jail.d/sshd.local
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 3
banaction = nftables-multiport
ignoreip = 127.0.0.1/8 ::1 10.0.0.0/8 192.168.0.0/16   # Add your trusted IPs

[sshd]
enabled = true
backend = systemd
port = ssh           # Change if using non-default port
maxretry = 3
findtime = 600
bantime = 86400      # 24h for SSH
```

**Recidive jail** — escalates bans for repeat offenders:
```ini
[recidive]
enabled = true
logpath = /var/log/fail2ban.log
bantime = 7d
findtime = 1d
maxretry = 5
```

**Disable password auth *before* relying on Fail2Ban.** Fail2Ban is a reactive control — it only bans *after* failed attempts. Key-only auth prevents the attempts entirely.

### 5.2 CrowdSec — Modern Alternative

CrowdSec adds **community threat intelligence** — IPs blocked by other servers are proactively blocked on yours before they even attempt authentication.

**Install on Ubuntu 24.04:**
```bash
curl -s https://install.crowdsec.net | sudo sh
sudo apt update && sudo apt install -y crowdsec
sudo cscli collections install crowdsecurity/sshd
sudo systemctl enable --now crowdsec

# Install firewall bouncer (nftables)
sudo apt install -y crowdsec-firewall-bouncer-nftables
sudo systemctl enable --now crowdsec-firewall-bouncer
```

**Key advantages over Fail2Ban:**
- Community blocklist — proactive, not reactive
- Decoupled detect/enforce architecture
- Native journald acquisition (no fragile log parsing)
- First-class IPv6 support
- Prometheus metrics built-in

### 5.3 Choosing Between Them

| Scenario | Recommendation |
|---|---|
| Single VPS, SSH only | Fail2Ban is sufficient and simpler |
| Multi-service box (SSH + web + VPN) | CrowdSec for unified detection across services |
| Fleet of 3+ servers | CrowdSec — shared threat intelligence scales |
| Compliance requirements (SOC2, PCI-DSS) | CrowdSec — richer audit trail and metrics |
| Minimal resource constraints | Fail2Ban (~30MB RAM, Python); CrowdSec (~50MB, Go) |

**Running both**: Possible but ensure they don't fight over the same firewall chains. Use `set-only` mode in CrowdSec's bouncer if Fail2Ban already manages nftables rules.

---

## 6. Risks & Caveats

| Risk | Mitigation |
|---|---|
| **Lockout from bad config** | Keep second session open; always `sshd -t` before reload; prefer reload over restart |
| **Algorithm pinning breaks clients** | Don't pin unless compliance requires it. If pinning, inventory client SSH versions first |
| **AllowUsers excludes service accounts** | Inventory all automation users (rsync, Ansible, monitoring) before enabling AllowUsers |
| **AllowGroups typo blocks everyone** | `sshd -t` won't catch semantic errors in group names. Test with a second session |
| **Reload failure goes unnoticed** | Check `journalctl -u ssh -n 20` after reload. If reload failed, old config is still active |
| **CVE-2024-6387 (regreSSHion)** | Ensure `openssh-server ≥ 1:9.6p1-3ubuntu13.3` — patched via `apt upgrade` or `unattended-upgrades` |
| **CVE-2025-26465 / CVE-2025-26466** | Fixed in later USN updates. Verify with `apt-cache policy openssh-server` |
| **Cloud-init overwrites drop-in** | On Ubuntu cloud images, `50-cloud-init.conf` may set `PasswordAuthentication yes`. Ensure your drop-in loads *after* (`99-hardening.conf`) or explicitly override |

---

## 7. Reference URLs

| Source | URL |
|---|---|
| OpenBSD sshd_config(5) man page (canonical) | https://man.openbsd.org/sshd_config.5 |
| OpenBSD sshd(8) man page (flags, signals) | https://man.openbsd.org/OpenBSD-7.7/sshd.8 |
| Ubuntu manpage: sshd_config (Debian defaults) | https://manpages.ubuntu.com/manpages/kinetic/man5/sshd_config.5.html |
| Ubuntu Security: CVE-2024-6387 regreSSHion fix | https://ubuntu.com/blog/ubuntu-regresshion-security-fix |
| Ubuntu Security: USN-6859-1 (OpenSSH) | https://lists.ubuntu.com/archives/ubuntu-security-announce/2024-July/008406.html |
| Ubuntu Security: USN-7270-1 (OpenSSH 2025) | https://ubuntu.com/security/notices/USN-7270-1 |
| Ubuntu blog: SSH hardening from keys to cloud identity | https://ubuntu.com/blog/how-to-harden-ubuntu-ssh-cloud |
| Ubuntu CIS benchmarks for 24.04 | https://ubuntu.com/blog/hardening-automation-for-cis-benchmarks-now-available-for-ubuntu-24-04-lts |
| sshaudit.com hardening guides | https://www.sshaudit.com/hardening_guides.html |
| cr0x.net — Pragmatic Ubuntu 24.04 SSH checklist | https://cr0x.net/en/ubuntu-ssh-hardening-checklist/ |
| msbiro.net — Opinionated sshd_config hardening 2025 | https://www.msbiro.net/posts/back-to-basics-sshd-hardening/ |
| virtua.cloud — SSH hardening VPS guide 2026 | https://www.virtua.cloud/learn/en/tutorials/ssh-security-config-linux-vps |
| CrowdSec installation on Ubuntu 24.04 | https://data-mammoth.com/support/security/how-to-install-crowdsec-ubuntu |
| CrowdSec vs Fail2Ban comparison | https://dev.to/patrickbloemit/goodbye-fail2ban-hardening-netbird-caddy-with-crowdsec-29g6 |
| DigitalOcean — SSH hardening full stack | https://www.digitalocean.com/community/tutorials/hardening-ssh-fail2ban |

---

## 8. Verification Checklist

After implementing, verify each control:

- [ ] `sudo sshd -T | grep passwordauthentication` → `passwordauthentication no`
- [ ] `sudo sshd -T | grep permitrootlogin` → `permitrootlogin no`
- [ ] `sudo sshd -T | grep pubkeyauthentication` → `pubkeyauthentication yes`
- [ ] `sudo sshd -T | grep -i kbdinteractive` → `kbdinteractiveauthentication no`
- [ ] `sudo sshd -T | grep maxauthtries` → `maxauthtries 3`
- [ ] `sudo sshd -T | grep allowusers` → shows configured users (if set)
- [ ] `ssh -o PreferredAuthentications=password user@server` → "Permission denied (publickey)"
- [ ] `ssh root@server` → "Permission denied"
- [ ] `ssh user@server` → successful login (key auth)
- [ ] `sudo journalctl -u ssh -n 10 \| grep "Accepted"` → shows recent successful key auth
- [ ] `sudo fail2ban-client status sshd` → shows active jail (if using Fail2Ban)
- [ ] `sudo cscli metrics` → shows parsed events (if using CrowdSec)
- [ ] `ssh-audit <server>` → no `[fail]` entries

---

*Report prepared for STEP-P0-002. Recommendations are based on OpenSSH 9.6p1 on Ubuntu 24.04 LTS. Adjust algorithm pinning and access lists per local compliance requirements and client inventory.*
