# STEP-P0-003 — External Directory Readiness Report

**Step:** P0-003 — Create `/home/guinevere` directory tree
**Phase:** P0 Infrastructure Foundation
**Date:** 2026-05-31
**Scope:** Linux app directory layout, permissions, idempotent creation, systemd integration points, shared VPS safety
**Context:** Create the `guinevere` user's home directory tree on a shared Ubuntu 24.04 VPS alongside existing Aizanta deployment. Aizanta must not be touched.

---

## 1. FHS Directory Placement — Which Root for Which Data

### 1.1 Summary Table

| Path | FHS Purpose | systemd Directive | Use for Guinevere | Owner |
|---|---|---|---|---|
| `/home/guinevere/` | Normal user home directory (P0-001 already created user) | N/A (user home) | **Primary app tree**: code, config, venv, data | `guinevere:guinevere` |
| `/etc/guinevere/` | Host-specific configuration | `ConfigurationDirectory=` | Static config files shipped with app | `root:root` (service *reads* only) |
| `/var/lib/guinevere/` | Persistent private state data | `StateDirectory=` | DB files, persistent runtime state | `guinevere:guinevere` (or dynamic user) |
| `/var/log/guinevere/` | Persistent log data | `LogsDirectory=` | Application logs | `guinevere:guinevere` |
| `/run/guinevere/` | Runtime ephemeral data (cleaned on boot) | `RuntimeDirectory=` | PID files, sockets, locks | `guinevere:guinevere` (auto-cleaned) |
| `/var/cache/guinevere/` | Application cache data | `CacheDirectory=` | Temporary cache, downloads | `guinevere:guinevere` |

### 1.2 Critical Distinctions

**`/home/guinevere/`** — This is where the setup script will build the primary tree: `bin/`, `src/`, `config/`, `data/`, `.local/`, `.ssh/`, etc. The FHS specifies that `/home/` is for **normal users only, never for system users** ([FHS](https://specifications.freedesktop.org/fhs/latest/)). The `guinevere` user was created as a normal user in P0-001, so `/home/guinevere/` is the correct primary location.

**`/opt/` is NOT recommended** for Guinevere. The modern systemd file-hierarchy spec explicitly says: *"Using /opt/ is not recommended. It is not integrated with the rest of the distribution"* ([UAPI file-hierarchy](https://uapi-group.org/specifications/specs/linux_file_system_hierarchy/#opt)). `/opt/` is for self-contained third-party packages (like Google Chrome). Guinevere is a first-party app managed through the distribution — home directory or `/var/lib/` is the right choice.

**`/etc/`** should be root-owned and read-only for the running service. Services that write back to `/etc/` blur privilege boundaries and increase operational risk ([DEV.to - Secure Directory Layout](https://dev.to/vast-cow/designing-a-secure-directory-layout-for-services-that-start-as-root-and-then-drop-privileges-1e1b)). For P0-003, there is no urgent need to create `/etc/guinevere/` unless a systemd service unit or sudoers drop-in is being deployed.

**`/var/lib/`** is the primary location for persistent private application data. systemd's `StateDirectory=` directive auto-creates the subdirectory under `/var/lib/` when the service starts ([systemd.exec](https://freedesktop.org/software/systemd/man/latest/systemd.exec.html)). This is the "core writable area" after privileges are dropped. For P0-003 this is forward-looking — create the directory structure now, wire it via systemd later.

---

## 2. `install -d` — Idempotent Directory Creation

### 2.1 Command Pattern

```bash
# Create directory tree with owner, group, and mode in one idempotent command:
install -d -o guinevere -g guinevere -m 0755 /home/guinevere/{bin,src,config,data,.local/{share,lib,bin},.ssh}

# For sensitive directories (private keys, tokens):
install -d -o guinevere -g guinevere -m 0700 /home/guinevere/{.ssh,.secrets}
```

### 2.2 Why `install -d` vs `mkdir -p`

| Feature | `install -d` | `mkdir -p` |
|---|---|---|
| Creates parent dirs | ✅ Yes | ✅ Yes |
| Sets owner (`-o`) | ✅ Single command | ❌ Needs separate `chown` |
| Sets group (`-g`) | ✅ Single command | ❌ Needs separate `chgrp` |
| Sets mode (`-m`) | ✅ Single command | ❌ Needs separate `chmod` |
| Idempotent on existing dirs | ✅ Preserves existing attributes | ⚠️ `mkdir -p` will try to set mode on existing dirs |
| Atomicity | ✅ New inode per creation | ❌ Overwrites existing inode |

Key insight: `install -d` uses `make_dir_parents` with `preserve_existing=true`, meaning if the directory already exists and has the correct owner/group/mode, the command does nothing. `mkdir -p` with `-m` will try to change permissions on existing dirs ([StackExchange](https://unix.stackexchange.com/questions/104982/why-use-install-rather-than-cp-and-mkdir)).

### 2.3 Canonical P0-003 Command Sequence

```bash
# 1. Core home directory tree (world-executable, non-world-readable outside group)
install -d -o guinevere -g guinevere -m 0750 \
  /home/guinevere/bin \
  /home/guinevere/src \
  /home/guinevere/config \
  /home/guinevere/data

# 2. .local XDG hierarchy
install -d -o guinevere -g guinevere -m 0750 \
  /home/guinevere/.local/share \
  /home/guinevere/.local/lib \
  /home/guinevere/.local/bin

# 3. Sensitive directories (private)
install -d -o guinevere -g guinevere -m 0700 \
  /home/guinevere/.ssh \
  /home/guinevere/.secrets

# 4. Forward-looking system-managed directories (optional at P0-003)
install -d -o guinevere -g guinevere -m 0750 \
  /var/lib/guinevere \
  /var/log/guinevere

# 5. Verify
ls -la /home/guinevere/
```

### 2.4 Permission Mode Rationale

| Mode | Use Case | Rationale |
|---|---|---|
| `0750` | App directories (default) | User rwx, group rx, others nothing — standard isolation for shared VPS |
| `0700` | SSH, secrets, tokens | User-only access — no group or world access |
| `0755` | `bin/`, `public/` dirs | If executables need to be accessible by other services |
| `2770` (setgid) | Multi-user collaborative dirs | New files inherit group — not needed for single-user `guinevere` |

---

## 3. Directory Implications — `/home` vs `/opt` vs `/etc` vs `/var/lib`

### 3.1 Decision Matrix for P0-003

| Directory | Recommended for P0-003? | Rationale |
|---|---|---|
| `/home/guinevere/` | **✅ YES (primary)** | Already created by P0-001 useradd; app code, config, and user-owned data belong here |
| `/opt/guinevere/` | ❌ No | FHS: "not recommended" per systemd spec; `/opt/` is for self-contained vendor packages, not first-party apps |
| `/etc/guinevere/` | 🔲 Defer to systemd service creation | Needed when a systemd unit file is deployed; config should be root-owned, read-only for service |
| `/var/lib/guinevere/` | **✅ Create early (empty)** | Future `StateDirectory=` target; having the directory pre-created causes no harm and documents intent |
| `/var/log/guinevere/` | **✅ Create early (empty)** | Future `LogsDirectory=` target; can be wired via systemd or logrotate later |
| `/run/guinevere/` | 🔲 Managed by systemd | `RuntimeDirectory=` auto-creates and cleans on service stop; no need to pre-create |
| `/srv/guinevere/` | ❌ No | `/srv/` is for site-specific data served by the system (FTP, HTTP); irrelevant here |

### 3.2 Key Risks by Directory Choice

**`/home/guinevere/` risks:**
- Mounted on separate partition (common server practice); ensure sufficient disk space
- May be mounted noexec in hardened environments — if so, move `bin/` to `/usr/local/bin/guinevere/` or `/opt/`
- Accessibility: some shared hosting configs restrict `/home/` access — verify `guinevere` can access its own `/home/guinevere/`

**`/var/lib/guinevere/` risks:**
- Not in user `$HOME` — must be explicitly created
- `/var/` may be a separate filesystem; ensure space is adequate
- Backups must cover both `/home/guinevere/` and `/var/lib/guinevere/` separately

**`/etc/guinevere/` risks:**
- Must remain root-owned; the running service should never write to `/etc/` ([source](https://dev.to/vast-cow/designing-a-secure-directory-layout-for-services-that-start-as-root-and-then-drop-privileges-1e1b))
- Introduce only when systemd service unit is being deployed

---

## 4. systemd `StateDirectory`, `LogsDirectory`, `RuntimeDirectory`

### 4.1 Directive Mapping

| Directive | System Path | User Path | Env Variable | Persistence |
|---|---|---|---|---|
| `RuntimeDirectory=` | `/run/{name}` | `$XDG_RUNTIME_DIR/{name}` | `$RUNTIME_DIRECTORY` | Ephemeral (cleaned on stop) |
| `StateDirectory=` | `/var/lib/{name}` | `$XDG_CONFIG_HOME/{name}` | `$STATE_DIRECTORY` | Persistent (survives reboot) |
| `CacheDirectory=` | `/var/cache/{name}` | `$XDG_CACHE_HOME/{name}` | `$CACHE_DIRECTORY` | Persistent (may be cleared) |
| `LogsDirectory=` | `/var/log/{name}` | `$XDG_CONFIG_HOME/log/{name}` | `$LOGS_DIRECTORY` | Persistent (survives reboot) |
| `ConfigurationDirectory=` | `/etc/{name}` | `$XDG_CONFIG_HOME/{name}` | `$CONFIGURATION_DIRECTORY` | Persistent (root-owned) |

Reference: [systemd.exec - RuntimeDirectory, StateDirectory, etc.](https://freedesktop.org/software/systemd/man/latest/systemd.exec.html)

### 4.2 Systemd v240+ Behavior (Ubuntu 24.04 has 255+)

Since systemd v240, these directives automatically set the corresponding environment variables. Ubuntu 24.04 ships systemd 255, so all features are available:

```ini
[Service]
User=guinevere
Group=guinevere

# Creates /run/guinevere (ephemeral, cleaned on stop)
RuntimeDirectory=guinevere
RuntimeDirectoryMode=0750

# Creates /var/lib/guinevere (persistent state)
StateDirectory=guinevere
StateDirectoryMode=0750

# Creates /var/log/guinevere (persistent logs)
LogsDirectory=guinevere
LogsDirectoryMode=0750
```

The process then receives `$RUNTIME_DIRECTORY=/run/guinevere`, `$STATE_DIRECTORY=/var/lib/guinevere`, `$LOGS_DIRECTORY=/var/log/guinevere` as environment variables.

### 4.3 Pre-creation vs systemd auto-creation

For P0-003, the decision is:

- **`/home/guinevere/` tree**: Create manually via `install -d` in setup script (this is the user's home, not a systemd-managed path)
- **`/var/lib/guinevere/`**: Can be pre-created now with `install -d` as documentation of intent, even if no systemd service exists yet. The systemd `StateDirectory=` will use the existing directory if it already exists.
- **`/var/log/guinevere/`**: Same as above — harmless to pre-create.
- **`/run/guinevere/`**: Do NOT pre-create — systemd owns this path and creates/cleans it at service start/stop.

### 4.4 Additional Hardening Directives (future systemd service)

Once a systemd unit is written for Guinevere, these sandboxing directives should be applied:

```ini
[Service]
ProtectSystem=full          # /usr and /etc read-only; /var still writable
ProtectHome=yes             # Hides /home, /root, /run/user from service
PrivateTmp=yes              # Private /tmp and /var/tmp
NoNewPrivileges=yes         # Prevents privilege escalation via setuid
```

Reference: [DoHost - Modern Web Server Sandboxing with Systemd](https://dohost.us/index.php/2026/05/12/beyond-chroot-modern-web-server-sandboxing-with-systemd-directives/)

---

## 5. Shared VPS Safety — Coexisting with Aizanta

### 5.1 Non-Negotiable Constraints

| Constraint | Implementation |
|---|---|
| Do not modify any Aizanta files | Setup script must target only paths under `/home/guinevere/`, `/var/lib/guinevere/`, `/var/log/guinevere/` |
| Do not modify Aizanta's systemd units | No edit to `/etc/systemd/system/aizanta*` |
| Do not modify Aizanta's sshd config | Already preserved in P0-002 — the `AllowUsers` list was extended, not replaced |
| Do not modify Aizanta's sudoers | No `sudo` for `guinevere` beyond what P0-001 grants |
| No port conflicts | Aizanta's published ports must remain unchanged |

### 5.2 Isolation Best Practices for Multi-App VPS

**Principle: one Linux user per application** — this is the foundation of multi-app isolation on a shared VPS ([Blog - Host Multiple Apps on One VPS](https://blog.puncoz.com/securely-host-multiple-apps-single-vps-nginx-php-fpm-cloudflare)). The `guinevere` user already exists from P0-001, and Aizanta runs under its own user.

| Isolation Layer | Mechanism | Status for P0-003 |
|---|---|---|
| **Filesystem** | Separate Linux user + group + `0750`/`0700` dir permissions | ✅ Handled by `install -d` with `-o guinevere -g guinevere -m 0750` |
| **Process** | Processes run as `guinevere` user; cannot signal Aizanta's processes | ✅ Already established (different UIDs) |
| **Memory** | Kernel-enforced via separate UIDs | ✅ Automatic |
| **Network** | Different ports or socket files | 🔲 To be defined in app deployment |
| **systemd sandboxing** | `ProtectHome=yes`, `PrivateTmp=yes`, etc. | 🔲 Future (when systemd unit is written) |
| **Resource limits** | systemd `MemoryMax=`, `CPUQuota=`, `TasksMax=` | 🔲 Future |

### 5.3 Permission Verification Checklist

```bash
# Verify Aizanta isolation — no intersection of writable paths:
find /home/aizanta -type d -perm /o+w 2>/dev/null   # Should return nothing accessible by others
find /home/guinevere -type d -perm /o+w 2>/dev/null # Should return nothing accessible by others

# Verify directory ownership:
stat -c '%U:%G %a %n' /home/guinevere/*
# Expected: guinevere:guinevere 750 /home/guinevere/bin (etc.)
```

### 5.4 Aizanta Non-Interference Guarantee

The setup for P0-003 must:

1. Never `cd` into `/home/aizanta/` or any Aizanta-owned path
2. Never run `systemctl` commands that reference `aizanta*` units
3. Never edit `/etc/ssh/sshd_config*` (already done in P0-002)
4. Never modify sudoers beyond the `guinevere` entry (already done in P0-001)
5. Never bind-mount or symlink across Aizanta's directory tree

---

## 6. Recommended P0-003 Directory Tree Structure

```
/home/guinevere/
├── bin/                         0750  — scripts, entrypoints
├── src/                         0750  — source code, git clones
├── config/                      0750  — app-specific config templates
├── data/                        0750  — downloaded models, datasets
├── .local/
│   ├── bin/                     0750  — user-level executables (in $PATH)
│   ├── lib/                     0750  — private libraries
│   └── share/                   0750  — XDG shared data
├── .ssh/                        0700  — SSH keys (created by ssh-copy-id or manual)
│   ├── authorized_keys          0600
│   └── id_ed25519               0600  — optional, for outbound SSH
├── .secrets/                    0700  — tokens, API keys
└── .bashrc, .profile, etc.      — shell config (from /etc/skel or template)

/var/lib/guinevere/              0750  — persistent state (future StateDirectory=)

/var/log/guinevere/              0750  — app logs (future LogsDirectory=)
```

**Note**: Directories under `/var/lib/` and `/var/log/` are forward-looking. They should be created as empty directories during P0-003 to document intent, but they will not be actively used until the systemd service unit is deployed in a later step.

---

## 7. References

| Resource | URL |
|---|---|
| Filesystem Hierarchy Standard (FHS) 3.0 | https://specifications.freedesktop.org/fhs/latest/ |
| systemd file-hierarchy(7) | https://freedesktop.org/software/systemd/man/latest/file-hierarchy.html |
| systemd.exec(5) — RuntimeDirectory, StateDirectory, LogsDirectory, etc. | https://freedesktop.org/software/systemd/man/latest/systemd.exec.html |
| UAPI Linux File System Hierarchy spec | https://uapi-group.org/specifications/specs/linux_file_system_hierarchy/ |
| Ubuntu FHS documentation | https://documentation.ubuntu.com/project/how-ubuntu-is-made/concepts/filesystem-hierarchy-standard/ |
| `install(1)` — GNU coreutils | https://man7.org/linux/man-pages/man1/install.1.html |
| `install -d` vs `mkdir -p` differences | https://unix.stackexchange.com/questions/104982/why-use-install-rather-than-cp-and-mkdir |
| Multi-app VPS isolation best practices | https://blog.puncoz.com/securely-host-multiple-apps-single-vps-nginx-php-fpm-cloudflare |
| Secure directory layout for privilege-dropping services | https://dev.to/vast-cow/designing-a-secure-directory-layout-for-services-that-start-as-root-and-then-drop-privileges-1e1b |
| Modern web server sandboxing with systemd | https://dohost.us/index.php/2026/05/12/beyond-chroot-modern-web-server-sandboxing-with-systemd-directives/ |
| systemd v240 env var support (Ubuntu 24.04 has 255) | https://stackoverflow.com/questions/59927397/systemd-not-setting-runtime-directory-env-when-it-should |

---

## 8. Blockers & Risks

| Risk | Severity | Mitigation |
|---|---|---|
| `/home/` may be mounted `noexec` | Medium | Verify with `mount \| grep /home`; if `noexec`, move bin/ to `/usr/local/bin/guinevere/` |
| `/var/` on separate partition with limited space | Low | Check `df -h /var/` before creating `/var/lib/guinevere/` and `/var/log/guinevere/` |
| Conflicting sudo rules from Aizanta's deployment | Low | `guinevere` is already in sudo group from P0-001; no further sudo changes needed for P0-003 |
| `umask` causing wrong permissions during manual dir creation | Low | Always use `install -d` with explicit `-m`; avoid `mkdir` + separate `chmod` |
