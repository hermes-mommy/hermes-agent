# Guinevere Deployment Guide v1.0

**Document Type:** Deployment Guide — Complete VPS Deployment, Configuration, and Operations  
**Version:** 1.0  
**Status:** Accepted  
**Lifecycle:** Proposed → Accepted → Deprecated → Superseded  
**Last Updated:** 2026-05-30  
**Owner:** Faiz — single-user owner and final authority  
**Executor:** Guinevere de Baroque — autonomous system steward  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  

---

## Document Control

| Attribute | Value |
|---|---|
| **Version** | 1.0 |
| **Date** | 2026-05-30 |
| **Author** | Guinevere / Hephaestus |
| **Status** | Accepted |
| **Reviewers** | Faiz (Operator) |
| **Supersedes** | N/A |
| **Next Review** | 2026-08-30 (quarterly) |

---

## Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines runtime architecture, service inventory, infrastructure, network topology, and resource allocation. |
| `Guinevere_PRD_v2.0.md` | Defines product features and user-facing behavior implemented by deployed services. |
| `Guinevere_APIIntegration_v2.0.md` | Defines external API contracts, SDK selections, and integration configurations. |
| `Guinevere_MemorySchema_v2.0.md` | Defines database schemas, indexes, and data models deployed to PostgreSQL. |
| `Guinevere_AgentLoopSpec_v2.0.md` | Defines autonomous SDLC loop behavior deployed via guinevere-loops.service. |
| `Guinevere_Observability_AlertingSpec_v1.0.md` | Defines metrics, dashboards, alert rules deployed via Prometheus + Grafana + Loki. |
| `Guinevere_SecretsRotationRunbook_v1.0.md` | Defines rotation schedule and procedures for secrets managed by SOPS + age. |
| `Guinevere_EncryptionKeyManagementStandard_v1.0.md` | Defines key management standards enforced during deployment. |
| `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` | Defines incident severity, response procedures, and escalation paths. |
| `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` | Defines user roles, permissions, and access boundaries enforced on deployed services. |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Defines data classification rules applied to backup and log content. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Defines persona safety boundaries preserved during all deployment operations. |
| `Guinevere_Cost_FinOps_Model_v1.0.md` | Defines budget constraints (30 USD/month hard cap) enforced during infrastructure provisioning. |
| `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md` | Defines SLO targets that monitoring and alerting must satisfy. |
| `adr/ADR-028-llm-router-outage-graceful-degradation.md` | Defines 4-tier LLM failover chain deployed via guinevere-ollama.service. |
| `adr/ADR-004-primary-llm-model-selection.md` | Defines primary LLM model (GPT-5.5 via 9Router). |
| `adr/ADR-005-llm-router-failover-strategy.md` | Defines LLM router failover strategy, implicitly amended by ADR-028. |
| `adr/ADR-017-monitoring-stack-selection.md` | Defines Prometheus + Grafana monitoring stack on primary VPS. |
| `adr/ADR-018-security-architecture-defense-in-depth.md` | Defines defense-in-depth security architecture deployed on VPS. |
| `Guinevere_Security_Policy_v1.0.md` | Defines security controls, threat mitigations, STRIDE analysis, KILLSWITCH framework, and incident response procedures deployed by this guide. |
| `Guinevere_TDD_Guide_v1.0.md` | Defines CI/CD test pipeline, coverage gates, and deployment verification test strategy enforced during releases. |
---

## Executive Summary

This document provides the complete, step-by-step deployment guide for Project Guinevere on a single Ubuntu 24.04 LTS VPS (4 Core CPU, 16GB RAM, 120GB SSD). Every command is concrete and copy-pasteable. Every configuration file is complete. Every systemd unit includes hardening directives.

**Deployment architecture:**

- **Primary VPS**: hostdata.id (or any Ubuntu 24.04 VPS with 4C/16GB/120GB)
- **Services**: guinevere-core, guinevere-surveillance, guinevere-scheduler, guinevere-loops, guinevere-windows-sync, guinevere-discord, guinevere-whatsapp, guinevere-ollama, docker (PostgreSQL + Redis + monitoring containers), caddy, tailscaled, cloudflared
- **LLM routing**: 9Router (primary) -> OpenRouter (secondary) -> Ollama local (third-level) -> Graceful Degradation (ADR-028 v3.0)
- **Network**: Tailscale mesh (zero public ports) + Cloudflare Tunnel (Discord webhook endpoint)
- **Monitoring**: Prometheus + Grafana + Loki + Promtail + Alertmanager
- **Secrets**: SOPS + age encryption, per-service encrypted environment files
- **Database**: PostgreSQL 16 + pgvector + TimescaleDB via Docker, PgBouncer connection pooling, Redis (RDB+AOF) via Docker
- **Firewall**: UFW + fail2ban + CrowdSec defense-in-depth
- **Backup**: WAL streaming (continuous) + pg_dump (daily) + Redis snapshots + encrypted offsite to Cloudflare R2 and idcloudhost S3

**Target audience:** Faiz (operator) and Guinevere (autonomous executor). This guide assumes basic Linux familiarity but provides every command explicitly.

**Operator directives applied (from questionnaire option B selections):**
- Ubuntu 24.04 LTS as target OS with standard hardening (SSH key-only, UFW, fail2ban)
- systemd as service manager with full hardening (ProtectSystem, PrivateTmp, NoNewPrivileges, resource limits)
- Cloudflare Tunnel for Discord webhook with full ingress rules as systemd service
- Tailscale for internal networking with MagicDNS, HTTPS certificates, device approval
- SOPS + age for secrets management with test encrypt/decrypt workflow
- Prometheus + Grafana + Loki for monitoring with scrape targets and retention config
- Ollama as third-level fallback per ADR-028 v3.0 (Phi-3-mini / Mistral-7B, 4GB RAM cap)
- pyenv for Python version management
- Per-service environment files, all SOPS encrypted
- Step-by-step Discord bot setup with guild-specific slash commands
- WhatsApp service via Neonize (pure Python) with QR code auth as systemd unit
- Concrete commands only -- no `see documentation` placeholders

---

## 1. Deployment Architecture Overview

### 1.1 Single VPS Architecture Diagram

```mermaid
graph TB
    subgraph Tailscale[`Tailscale Mesh Network (100.x.x.x)`]
        ANDROID[`Android HP (Tasker + AutoInput)`]
        WINDOWS[`Windows Laptop (Python Daemon)`]
        VPS[`VPS Primary guinevere.internal 4C/16GB/120GB`]
        SAMMLAPTOP[`Faiz Laptop (Admin Access)`]
    end

    subgraph Services[`VPS Internal Services`]
        CORE[`guinevere-core Hermes Agent`]
        SURV[`guinevere-surveillance FastAPI :8000`]
        SCHED[`guinevere-scheduler APScheduler`]
        LOOPS[`guinevere-loops SDLC Runner`]
        WSYNC[`guinevere-windows-sync WebSocket :8001`]
        DISCORD[`guinevere-discord Discord Bot`]
        WA[`guinevere-whatsapp Neonize Service`]
        OLLAMA[`guinevere-ollama :11434`]
    end

    subgraph Docker[`Docker Containers`]
        PG[`PostgreSQL 16 +pgvector+TimescaleDB :5432`]
        REDIS[`Redis 7 RDB+AOF :6379`]
        PGB[`PgBouncer :6432`]
        PROM[`Prometheus :9090`]
        GRAF[`Grafana :3000`]
        LOKI[`Loki :3100`]
    end

    CADDY[`Caddy Reverse Proxy`]
    CF[`Cloudflare Tunnel cloudflared`]
    TS[`tailscaled`]

    ANDROID -->|`HTTP POST Tailscale`| SURV
    WINDOWS -->|`WebSocket Tailscale`| WSYNC
    SAMMLAPTOP -->|`Tailscale SSH`| VPS

    CORE --> PG
    CORE --> REDIS
    SURV --> PG
    SURV --> REDIS
    LOOPS --> PG
    LOOPS --> REDIS
    DISCORD --> CORE
    WA --> CORE
    OLLAMA -.->|`Tier 3 fallback`| CORE

    CF -->|`Outbound only`| CADDY
    CADDY --> SURV
    CADDY --> GRAF

    PROM -->|`Scrape`| CORE
    PROM -->|`Scrape`| SURV
    PROM -->|`Scrape`| SCHED
    PROM -->|`Scrape`| LOOPS
    PROM -->|`Node Exporter`| VPS
    PROM -->|`PG Exporter`| PG
    PROM -->|`Redis Exporter`| REDIS
    GRAF --> PROM
    GRAF --> LOKI
    LOKI -->|`Promtail`| VPS
```

### 1.2 Component Inventory

| Service | Port | Protocol | User | Dependencies | Restart Policy |
|---|---|---|---|---|---|
| guinevere-core | N/A (internal) | -- | guinevere | postgresql, redis, 9router | Always, 10s |
| guinevere-surveillance | 8000 | HTTP/REST | guinevere | postgresql, redis | Always, 10s |
| guinevere-scheduler | N/A (internal) | -- | guinevere | postgresql, redis, guinevere-core | Always, 30s |
| guinevere-loops | N/A (internal) | -- | guinevere | postgresql, redis, guinevere-core | On-failure, 10s |
| guinevere-windows-sync | 8001 | WebSocket | guinevere | redis | Always, 10s |
| guinevere-discord | N/A (gateway) | WSS | guinevere | guinevere-core | Always, 10s |
| guinevere-whatsapp | N/A (gateway) | WSS | guinevere | guinevere-core | Always, 10s |
| guinevere-ollama | 11434 | HTTP | ollama | network-online | On-demand (Tier 3 only) |
| postgresql (Docker) | 5432 | TCP | postgres | docker | Always |
| redis (Docker) | 6379 | TCP | redis | docker | Always |
| pgbouncer | 6432 | TCP | guinevere | postgresql | Always, 5s |
| prometheus (Docker) | 9090 | HTTP | root | docker | Always |
| grafana (Docker) | 3000 | HTTP | root | docker, prometheus | Always |
| loki (Docker) | 3100 | HTTP | root | docker | Always |
| caddy | 443/80 | HTTPS | caddy | network-online | Always |
| tailscaled | N/A | WireGuard | root | network-online | Always |
| cloudflared | N/A | HTTPS (outbound) | root | network-online | Always |
| fail2ban | N/A | -- | root | ufw | Always |
| crowdsec | N/A | -- | root | network-online | Always |

### 1.3 Network Topology

| Component | Address | Access Method | Notes |
|---|---|---|---|
| VPS Primary | 100.x.x.x (Tailscale) | Tailscale only | Zero public ports |
| guinevere.internal | 100.x.x.x:8000 | Tailscale + JWT | Surveillance API |
| guinevere.internal | 100.x.x.x:8001 | Tailscale + JWT | Internal API + WebSocket |
| postgres.internal | 100.x.x.x:5432 | Tailscale + PgBouncer | Database |
| redis.internal | 100.x.x.x:6379 | Tailscale + auth | Cache/Queue |
| metrics.internal | 100.x.x.x:9090 | Tailscale only | Prometheus |
| grafana.internal | 100.x.x.x:3000 | Tailscale only | Dashboard |
| Cloudflare Tunnel | webhook.domain.com | HTTPS (outbound) | Discord webhook only |
| Android HP | 100.x.x.x (Tailscale) | Tailscale client | Tasker HTTP POST |
| Windows Laptop | 100.x.x.x (Tailscale) | Tailscale client | WebSocket + admin SSH |

### 1.4 Resource Requirements

| Resource | Minimum | Recommended | Notes |
|---|---|---|---|
| CPU | 4 cores | 4 cores | hostdata.id standard plan |
| RAM | 16GB | 16GB | 4GB core + 4GB DB + 4GB observability + 4GB OS |
| Disk | 120GB SSD | 120GB SSD | PostgreSQL grows; cold storage to R2 at 90 days |
| Swap | 8GB | 8GB | vm.swappiness=10 |
| Bandwidth | 1TB/month | 2TB/month | Surveillance uploads + LLM API traffic |
| Network | Public IP required | Public IP required | For initial setup only; all ports closed after Tailscale |

### 1.5 Resource Allocation Baseline

| Service Group | RAM Allocation | CPU Allocation | Notes |
|---|---|---|---|
| Guinevere core + plugins | 4GB | 2 cores | Hermes daemon + persona + memory |
| PostgreSQL + Redis (Docker) | 4GB | 1 core | Shared buffers, working memory |
| Observability + workers | 4GB | 1 core | Prometheus, Grafana, Loki, scheduler |
| OS + buffer | 4GB | Shared | System reserve + Ollama (Tier 3) |
---

## 2. Prerequisites & Environment Setup

### 2.1 VPS Provisioning

#### 2.1.1 Provider Selection

Primary provider: **hostdata.id**
Alternative: Any Ubuntu 24.04 VPS with 4C/16GB/120GB SSD works (DigitalOcean, Linode, AWS Lightsail, etc.)

**Selection criteria:**
- Ubuntu 24.04 LTS available as OS image
- Minimum 4 vCPU, 16GB RAM, 120GB SSD
- Network: Public IPv4 address, minimum 1TB bandwidth
- Location: Singapore or Jakarta preferred (low latency to Indonesia)
- Snapshots: Provider must support VPS snapshots for DR

#### 2.1.2 Initial SSH Access and Key Setup

```bash
# Generate SSH key pair (if not already created)
ssh-keygen -t ed25519 -C "faiz@guinevere-admin" -f ~/.ssh/guinevere_vps_ed25519

# Copy public key to VPS (use provider root password for first time)
ssh-copy-id -i ~/.ssh/guinevere_vps_ed25519.pub root@<VPS_PUBLIC_IP>

# Test SSH login with key
ssh -i ~/.ssh/guinevere_vps_ed25519 root@<VPS_PUBLIC_IP>
```

#### 2.1.3 Initial System Update

```bash
# Update package lists and upgrade all packages
apt update && apt upgrade -y

# Install essential tools
apt install -y curl wget git jq htop iotop nethogs unzip apt-transport-https \
  ca-certificates gnupg lsb-release software-properties-common \
  build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev \
  libsqlite3-dev libncursesw5-dev xz-utils tk-dev libxml2-dev \
  libxmlsec1-dev libffi-dev liblzma-dev net-tools lsof strace tcpdump

# Clean up
apt autoremove -y && apt clean
```

#### 2.1.4 Timezone, Locale, Hostname Configuration

```bash
# Set timezone to Asia/Jakarta (WIB, UTC+7)
timedatectl set-timezone Asia/Jakarta

# Set hostname
hostnamectl set-hostname guinevere

# Configure locale
localectl set-locale LANG=en_US.UTF-8
locale-gen en_US.UTF-8

# Configure /etc/hosts
cat > /etc/hosts << 'EOF'
127.0.0.1   localhost
127.0.1.1   guinevere guinevere.internal
::1         localhost ip6-localhost ip6-loopback
ff02::1     ip6-allnodes
ff02::2     ip6-allrouters
EOF

# Verify
hostnamectl
timedatectl
localectl
```

#### 2.1.5 User Creation with sudo

```bash
# Create guinevere daemon user (no login shell)
useradd -r -m -d /home/guinevere -s /usr/sbin/nologin -c "Guinevere daemon" guinevere

# Create faiz admin user
useradd -m -d /home/faiz -s /bin/bash -c "Faiz - admin" faiz

# Set strong password for faiz (used for sudo auth)
passwd faiz

# Create guinevere group for shared resources
groupadd -f guinevere-svc
usermod -aG guinevere-svc guinevere
usermod -aG guinevere-svc faiz

# Configure sudoers -- faiz gets full sudo, guinevere gets scoped access
cat > /etc/sudoers.d/guinevere << 'EOF'
# Faiz - full admin access
faiz ALL=(ALL:ALL) ALL

# Guinevere - scoped access only
guinevere ALL=(root) NOPASSWD: /usr/bin/systemctl restart guinevere-*, \
  /usr/bin/systemctl stop guinevere-*, \
  /usr/bin/systemctl start guinevere-*, \
  /usr/bin/systemctl status guinevere-*, \
  /usr/bin/systemctl reload guinevere-*, \
  /usr/bin/docker restart postgresql, \
  /usr/bin/docker restart redis, \
  /usr/bin/docker restart prometheus, \
  /usr/bin/ufw reload, \
  /usr/bin/apt update, \
  /usr/bin/apt upgrade -y
EOF

chmod 440 /etc/sudoers.d/guinevere

# Set up SSH keys for faiz user
mkdir -p /home/faiz/.ssh
cp /root/.ssh/authorized_keys /home/faiz/.ssh/authorized_keys
chown -R faiz:faiz /home/faiz/.ssh
chmod 700 /home/faiz/.ssh
chmod 600 /home/faiz/.ssh/authorized_keys

# Set up directory structure for guinevere user
mkdir -p /home/guinevere/{core,surveillance,scheduler,loops,windows-sync,discord,whatsapp,config,data/{logs,cache,backups},scripts}
chown -R guinevere:guinevere /home/guinevere
chmod 750 /home/guinevere
```

#### 2.1.6 SSH Hardening

```bash
# Move SSH to non-standard port and harden
cat > /etc/ssh/sshd_config.d/99-guinevere-hardening.conf << 'EOF'
# Port -- non-standard to reduce noise
Port 2222

# Protocol and authentication
PermitRootLogin no
PasswordAuthentication no
PermitEmptyPasswords no
PubkeyAuthentication yes
AuthenticationMethods publickey
MaxAuthTries 3
MaxSessions 3
LoginGraceTime 20

# Session management
ClientAliveInterval 300
ClientAliveCountMax 2
TCPKeepAlive no

# Restrict forwarding
X11Forwarding no
AllowTcpForwarding no
AllowAgentForwarding no
GatewayPorts no
PermitTunnel no

# Restrict users
AllowUsers faiz guinevere

# Cryptographic settings (modern, strong only)
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com
HostKeyAlgorithms ssh-ed25519,ssh-ed25519-cert-v01@openssh.com,rsa-sha2-512,rsa-sha2-256

# Logging
LogLevel VERBOSE

# Banner
Banner /etc/ssh/banner
EOF

# Create SSH banner
cat > /etc/ssh/banner << 'EOF'
***************************************************************************
*                    GUINEVERE VPS -- AUTHORIZED ACCESS ONLY              *
*          All connections are logged and monitored. Disconnect now       *
*          if you are not an authorized user.                             *
***************************************************************************
EOF

# Validate SSH config before restarting
sshd -t

# Restart SSH (keep current session open, test new connection before closing)
systemctl restart sshd
```

**IMPORTANT:** Before closing your current SSH session, open a new terminal and test:
```bash
ssh -i ~/.ssh/guinevere_vps_ed25519 -p 2222 faiz@<VPS_PUBLIC_IP>
```

### 2.2 OS Hardening (CIS Benchmark Adapted)

#### Step 1: Filesystem Hardening

```bash
# Secure /tmp as tmpfs with noexec,nosuid
cat > /etc/systemd/system/tmp.mount << 'EOF'
[Unit]
Description=Temporary Directory (/tmp)
ConditionPathIsSymbolicLink=!/tmp
DefaultDependencies=no
Conflicts=umount.target
Before=local-fs.target umount.target
After=swap.target

[Mount]
What=tmpfs
Where=/tmp
Type=tmpfs
Options=size=2G,noexec,nosuid,nodev,mode=1777

[Install]
WantedBy=local-fs.target
EOF

systemctl daemon-reload
systemctl enable --now tmp.mount

# Secure shared memory
echo "tmpfs /dev/shm tmpfs defaults,noexec,nosuid,nodev 0 0" >> /etc/fstab
mount -o remount /dev/shm
```

#### Step 2: Service Minimization

```bash
# Disable unnecessary services
systemctl disable --now snapd 2>/dev/null || true
systemctl disable --now avahi-daemon 2>/dev/null || true
systemctl disable --now cups 2>/dev/null || true
systemctl disable --now cups-browsed 2>/dev/null || true
systemctl disable --now bluetooth 2>/dev/null || true
systemctl disable --now apport 2>/dev/null || true
systemctl disable --now whoopsie 2>/dev/null || true
systemctl disable --now ModemManager 2>/dev/null || true

# Remove snap completely (saves disk space)
apt purge -y snapd 2>/dev/null || true
rm -rf /snap /var/snap /var/lib/snapd /var/cache/snapd /usr/lib/snapd

# Mask services to prevent re-enablement
systemctl mask snapd.service snapd.socket 2>/dev/null || true
```

#### Step 3: Network Hardening (sysctl)

```bash
cat > /etc/sysctl.d/99-cis-hardening.conf << 'EOF'
# === CIS Benchmark -- Network Hardening ===
net.ipv4.tcp_syncookies = 1
net.ipv4.ip_forward = 0
net.ipv4.conf.all.forwarding = 0
net.ipv6.conf.all.forwarding = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2
net.ipv4.tcp_syn_retries = 5
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_probes = 5
net.ipv4.tcp_keepalive_intvl = 15
net.netfilter.nf_conntrack_max = 131072

# === CIS Benchmark -- Kernel Hardening ===
kernel.randomize_va_space = 2
fs.suid_dumpable = 0
kernel.yama.ptrace_scope = 1
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
fs.protected_symlinks = 1
fs.protected_hardlinks = 1
kernel.unprivileged_bpf_disabled = 1
net.core.bpf_jit_harden = 2

# === Performance Tuning for Guinevere ===
fs.file-max = 2097152
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 1024
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.core.rmem_default = 1048576
net.core.wmem_default = 1048576
net.ipv4.tcp_rmem = 4096 1048576 16777216
net.ipv4.tcp_wmem = 4096 1048576 16777216
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65535
EOF

sysctl --system
```

#### Step 4: User/Account Security

```bash
apt install -y libpam-pwquality

cat > /etc/security/pwquality.conf << 'EOF'
minlen = 16
dcredit = -1
ucredit = -1
lcredit = -1
ocredit = -1
maxrepeat = 3
maxclassrepeat = 4
gecoscheck = 1
enforcing = 1
EOF

# Lock system accounts
for user in bin daemon adm lp sync shutdown halt mail news uucp proxy www-data backup list irc gnats nobody systemd-network systemd-resolve messagebus; do
  usermod -L "$user" 2>/dev/null || true
  usermod -s /usr/sbin/nologin "$user" 2>/dev/null || true
done

# Set restrictive umask
sed -i 's/UMASK.*022/UMASK 027/' /etc/login.defs
echo "umask 027" >> /etc/profile.d/umask.sh
```

#### Step 5: File Permissions Hardening

```bash
chmod 600 /etc/shadow
chmod 644 /etc/passwd
chmod 644 /etc/group
chmod 600 /etc/crontab
chmod 700 /etc/cron.d
chmod 700 /etc/cron.daily
chmod 700 /etc/cron.hourly
chmod 700 /etc/cron.weekly
chmod 700 /etc/cron.monthly

echo "guinevere" > /etc/cron.allow
echo "faiz" >> /etc/cron.allow
echo "root" >> /etc/cron.allow
rm -f /etc/cron.deny
chmod 600 /etc/cron.allow
```

#### Step 6: Audit Logging (auditd)

```bash
apt install -y auditd audispd-plugins

cat > /etc/audit/rules.d/guinevere.rules << 'EOF'
-D
-b 8192
-f 1
-w /etc/passwd -p wa -k identity_changes
-w /etc/group -p wa -k identity_changes
-w /etc/shadow -p wa -k identity_changes
-w /etc/gshadow -p wa -k identity_changes
-w /etc/sudoers -p wa -k sudoers_changes
-w /etc/sudoers.d/ -p wa -k sudoers_changes
-w /etc/ssh/sshd_config -p wa -k sshd_config
-w /etc/ssh/sshd_config.d/ -p wa -k sshd_config
-w /etc/crontab -p wa -k cron_changes
-w /etc/cron.d/ -p wa -k cron_changes
-w /etc/systemd/system/ -p wa -k systemd_changes
-w /home/guinevere/core/ -p wa -k guinevere_core_changes
-w /home/guinevere/config/ -p wa -k guinevere_config_changes
-w /var/log/faillog -p wa -k login_events
-w /var/log/lastlog -p wa -k login_events
-w /sbin/insmod -p x -k kernel_modules
-w /sbin/rmmod -p x -k kernel_modules
-w /sbin/modprobe -p x -k kernel_modules
-a always,exit -F arch=b64 -S init_module -S finit_module -k kernel_modules
-a always,exit -F arch=b64 -S delete_module -k kernel_modules
-w /etc/network/ -p wa -k network_changes
-w /etc/ufw/ -p wa -k firewall_changes
EOF

augenrules --load
systemctl restart auditd
```

#### Step 7: Firewall Setup (UFW)

```bash
ufw --force reset
ufw default deny incoming
ufw default allow outgoing

# Allow SSH on non-standard port (rate limited) -- temporary
ufw limit 2222/tcp comment "SSH non-standard port"

# Allow Tailscale
ufw allow 41641/udp comment "Tailscale WireGuard"
ufw allow in on tailscale0 comment "All Tailscale interface traffic"

ufw logging on medium
ufw --force enable
ufw status verbose
```

#### Step 8: Intrusion Detection (fail2ban)

```bash
apt install -y fail2ban

cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
banaction = ufw
backend = systemd

[sshd]
enabled = true
port = 2222
filter = sshd
logpath = %(sshd_log)s
maxretry = 3
bantime = 86400

[ufw]
enabled = true
port = all
filter = ufw
logpath = /var/log/ufw.log
maxretry = 10

[fastapi-auth]
enabled = true
port = 8000,8001
filter = fastapi-auth
logpath = /home/guinevere/data/logs/surveillance.log
maxretry = 10
bantime = 1800
EOF

cat > /etc/fail2ban/filter.d/fastapi-auth.conf << 'EOF'
[Definition]
failregex = ^.*authentication failed.*client_ip=<HOST>.*$
            ^.*invalid HMAC signature.*source=<HOST>.*$
ignoreregex =
EOF

systemctl enable --now fail2ban
fail2ban-client status
```

#### Step 9: Additional Hardening -- Kernel + AppArmor

```bash
apt install -y apparmor apparmor-utils apparmor-profiles

cat > /etc/apparmor.d/home.guinevere.core << 'EOF'
#include <tunables/global>
profile guinevere-core /home/guinevere/core/** flags=(enforce) {
  #include <abstractions/base>
  #include <abstractions/python>
  #include <abstractions/nameservice>
  /home/guinevere/core/** r,
  /home/guinevere/config/** r,
  /home/guinevere/data/** rw,
  /home/guinevere/.venv/** r,
  /home/guinevere/data/logs/** w,
  /home/guinevere/data/cache/** w,
  network inet stream,
  network inet6 stream,
  deny /etc/shadow r,
  deny /etc/sudoers* r,
  deny /root/** rw,
  deny capability sys_admin,
}
EOF

apparmor_parser -r /etc/apparmor.d/home.guinevere.core
aa-status | head -30
```

#### Step 10: Unattended Security Updates

```bash
apt install -y unattended-upgrades apt-listchanges

cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'EOF'
Unattended-Upgrade::Allowed-Origins {
  "${distro_id}:${distro_codename}-security";
  "${distro_id}:${distro_codename}-updates";
};
Unattended-Upgrade::Package-Blacklist { "postgresql*"; "redis*"; };
Unattended-Upgrade::DevRelease "false";
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "03:00";
EOF

cat > /etc/apt/apt.conf.d/20auto-upgrades << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
EOF

systemctl enable --now unattended-upgrades
```

#### Step 11: Swap Configuration

```bash
fallocate -l 8G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo "/swapfile none swap sw 0 0" >> /etc/fstab
echo "vm.swappiness=10" > /etc/sysctl.d/98-swap.conf
echo "vm.vfs_cache_pressure=50" >> /etc/sysctl.d/98-swap.conf
sysctl -p /etc/sysctl.d/98-swap.conf
free -h
swapon --show
```

#### Step 12: NTP Time Synchronization

```bash
cat > /etc/systemd/timesyncd.conf << 'EOF'
[Time]
NTP=0.id.pool.ntp.org 1.id.pool.ntp.org 2.id.pool.ntp.org 3.id.pool.ntp.org
FallbackNTP=0.asia.pool.ntp.org 1.asia.pool.ntp.org
RootDistanceMaxSec=5
PollIntervalMinSec=32
PollIntervalMaxSec=2048
EOF

systemctl restart systemd-timesyncd
timedatectl set-ntp true
timedatectl status
```

#### Step 13: journald Configuration

```bash
mkdir -p /etc/systemd/journald.conf.d

cat > /etc/systemd/journald.conf.d/guinevere.conf << 'EOF'
[Journal]
SystemMaxUse=500M
SystemKeepFree=1G
MaxRetentionSec=30day
Compress=yes
ForwardToSyslog=no
MaxLevelStore=debug
EOF

systemctl restart systemd-journald
```

#### Step 14: CrowdSec Installation

```bash
curl -s https://install.crowdsec.net | sudo sh
cscli collections install crowdsecurity/linux
cscli collections install crowdsecurity/sshd
cscli collections install crowdsecurity/nginx
cscli hub update
cscli bouncers add guinevere-ufw-bouncer
cscli parsers install crowdsecurity/syslog
cscli parsers install crowdsecurity/sshd-logs
systemctl enable --now crowdsec
```

#### Step 15: Lynis Security Audit

```bash
apt install -y lynis
lynis audit system --no-colors --quick | tail -20
# Target: score 75+ after all hardening steps
```

### 2.3 Runtime Dependencies

#### Python 3.12+ via pyenv

```bash
su - guinevere -s /bin/bash << 'PYENV_INSTALL'
curl https://pyenv.run | bash

cat >> ~/.bashrc << 'PROFILE'
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
PROFILE

export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

pyenv install 3.12.8
pyenv global 3.12.8
python --version
pip --version
PYENV_INSTALL

# Install UV (fast Python package manager)
su - guinevere -s /bin/bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
```

#### Node.js (REMOVED -- Neonize replaces Baileys)

> **Note:** Node.js was previously required for the Baileys WhatsApp bridge. ADR-022 revision (2026-06-03) replaced Baileys with Neonize (pure Python). Node.js is no longer needed. The nvm installation section has been removed.

#### Ollama Installation

```bash
curl -fsSL https://ollama.com/install.sh | sh
useradd -r -m -d /home/ollama -s /usr/sbin/nologin ollama 2>/dev/null || true

# Pre-download models (CRITICAL -- must be done before production)
ollama pull phi3:mini-4k-instruct-q4_K_M
ollama pull mistral:7b-instruct-v0.3-q4_K_M

ollama list

mkdir -p /etc/ollama
cat > /etc/ollama/ollama.conf << 'EOF'
OLLAMA_HOST=127.0.0.1:11434
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_NUM_PARALLEL=1
OLLAMA_KEEP_ALIVE=5m
OLLAMA_ORIGINS=http://127.0.0.1
EOF
```

#### System Tools Verification

```bash
echo "=== System Tools Verification ==="
python3.12 --version 2>/dev/null && echo "OK Python 3.12" || echo "FAIL Python"
uv --version 2>/dev/null && echo "OK UV" || echo "FAIL UV"
# Node.js no longer required (Neonize replaced Baileys -- ADR-022 rev 2026-06-03)
git --version && echo "OK Git"
jq --version && echo "OK jq"
ollama --version && echo "OK Ollama"
```
### 2.4 Secrets Management (SOPS + age)

#### Installation

```bash
apt install -y age

SOPS_VERSION="3.9.4"
curl -LO "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/sops-v${SOPS_VERSION}.linux.amd64"
mv "sops-v${SOPS_VERSION}.linux.amd64" /usr/local/bin/sops
chmod +x /usr/local/bin/sops

sops --version
age --version
```

#### Age Key Generation and Backup

```bash
mkdir -p /etc/sops/age
chmod 700 /etc/sops/age
age-keygen -o /etc/sops/age/keys.txt
chmod 600 /etc/sops/age/keys.txt
chown root:guinevere-svc /etc/sops/age/keys.txt

echo "=== PUBLIC KEY (copy this to .sops.yaml) ==="
grep "public key:" /etc/sops/age/keys.txt

age-keygen -y /etc/sops/age/keys.txt > /etc/sops/age/public.txt
cp /etc/sops/age/keys.txt /root/age-key-backup-$(date +%Y%m%d).txt
chmod 600 /root/age-key-backup-*.txt
```

#### .sops.yaml Configuration

```bash
AGE_PUBLIC_KEY=$(grep "public key:" /etc/sops/age/keys.txt | awk '{print $NF}')

cat > /home/guinevere/.sops.yaml << EOF
creation_rules:
  - path_regex: secrets/.*\\.env\\.sops$
    age:
      - "${AGE_PUBLIC_KEY}"
  - path_regex: config/.*\\.sops$
    age:
      - "${AGE_PUBLIC_KEY}"
EOF

chown guinevere:guinevere /home/guinevere/.sops.yaml
```

#### Secrets File Structure and Encryption Workflow

```bash
mkdir -p /home/guinevere/secrets

# Create master secrets file (plaintext first, then encrypt)
cat > /home/guinevere/secrets/guinevere.env.plain << 'EOF'
# === LLM Configuration ===
NINEROUTER_API_KEY=your-9router-api-key-here
NINEROUTER_BASE_URL=https://api.9router.com/v1
OPENROUTER_API_KEY=your-openrouter-api-key-here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# === Discord ===
DISCORD_BOT_TOKEN=your-discord-bot-token-here
DISCORD_APPLICATION_ID=your-discord-app-id-here
DISCORD_GUILD_ID=your-discord-guild-id-here
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxx/yyy

# === Database ===
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=guinevere
POSTGRES_USER=guinevere_core
POSTGRES_PASSWORD=CHANGE_ME_STRONG
PGBOUNCER_PASSWORD=CHANGE_ME_PGB
REDIS_PASSWORD=CHANGE_ME_REDIS

# === GitHub ===
GITHUB_PAT=your-github-pat-here
GITHUB_WEBHOOK_SECRET=your-webhook-secret-here

# === Surveillance ===
TASKER_HMAC_SECRET=CHANGE_ME_HMAC
WINDOWS_HMAC_SECRET=CHANGE_ME_WHMAC

# === Storage ===
CLOUDFLARE_R2_ACCESS_KEY=your-r2-access-key
CLOUDFLARE_R2_SECRET_KEY=your-r2-secret-key
CLOUDFLARE_R2_ENDPOINT=https://account-id.r2.cloudflarestorage.com
CLOUDFLARE_R2_BUCKET=guinevere-backups
IDCLOUDHOST_S3_ACCESS_KEY=your-s3-key
IDCLOUDHOST_S3_SECRET_KEY=your-s3-secret
IDCLOUDHOST_S3_ENDPOINT=https://s3.idcloudhost.com
IDCLOUDHOST_S3_BUCKET=guinevere-backups

# === Email ===
RESEND_API_KEY=your-resend-api-key
GMAIL_OAUTH_CLIENT_ID=your-gmail-client-id
GMAIL_OAUTH_CLIENT_SECRET=your-gmail-client-secret
GMAIL_OAUTH_REFRESH_TOKEN=your-gmail-refresh-token

# === Search ===
BRAVE_SEARCH_API_KEY=your-brave-api-key
EXA_API_KEY=your-exa-api-key

# === Monitoring ===
SENTRY_DSN=your-sentry-dsn
GRAFANA_ADMIN_PASSWORD=CHANGE_ME_GRAFANA
GOTIFY_TOKEN=your-gotify-token

# === Encryption ===
FERNET_KEY=CHANGE_ME_FERNET
AGE_PUBLIC_KEY=age1...from-keygen
EOF

# Auto-generate strong passwords
sed -i "s|CHANGE_ME_STRONG|$(openssl rand -base64 32)|" /home/guinevere/secrets/guinevere.env.plain
sed -i "s|CHANGE_ME_PGB|$(openssl rand -base64 24)|" /home/guinevere/secrets/guinevere.env.plain
sed -i "s|CHANGE_ME_REDIS|$(openssl rand -base64 24)|" /home/guinevere/secrets/guinevere.env.plain
sed -i "s|CHANGE_ME_HMAC|$(openssl rand -hex 32)|" /home/guinevere/secrets/guinevere.env.plain
sed -i "s|CHANGE_ME_WHMAC|$(openssl rand -hex 32)|" /home/guinevere/secrets/guinevere.env.plain
sed -i "s|CHANGE_ME_GRAFANA|$(openssl rand -base64 20)|" /home/guinevere/secrets/guinevere.env.plain
sed -i "s|CHANGE_ME_FERNET|$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')|" /home/guinevere/secrets/guinevere.env.plain

# Encrypt
cp /home/guinevere/secrets/guinevere.env.plain /home/guinevere/secrets/guinevere.env.sops
SOPS_AGE_KEY_FILE=/etc/sops/age/keys.txt sops --encrypt --in-place /home/guinevere/secrets/guinevere.env.sops

# Remove plaintext
shred -u /home/guinevere/secrets/guinevere.env.plain

# Verify
SOPS_AGE_KEY_FILE=/etc/sops/age/keys.txt sops --decrypt /home/guinevere/secrets/guinevere.env.sops | head -5
```

#### Per-Service Secrets

```bash
# Create per-service secret files
SOPS_AGE_KEY_FILE=/etc/sops/age/keys.txt sops --decrypt /home/guinevere/secrets/guinevere.env.sops | \
  grep -E "^(NINEROUTER_|OPENROUTER_|DISCORD_BOT_TOKEN|POSTGRES_PASSWORD|REDIS_PASSWORD|GITHUB_PAT|FERNET_KEY|SENTRY_DSN)" \
  > /home/guinevere/secrets/core.env.plain

SOPS_AGE_KEY_FILE=/etc/sops/age/keys.txt sops --decrypt /home/guinevere/secrets/guinevere.env.sops | \
  grep -E "^(TASKER_HMAC|WINDOWS_HMAC|POSTGRES_|REDIS_)" \
  > /home/guinevere/secrets/surveillance.env.plain

for f in /home/guinevere/secrets/*.env.plain; do
  target="${f%.plain}.sops"
  cp "$f" "$target"
  SOPS_AGE_KEY_FILE=/etc/sops/age/keys.txt sops --encrypt --in-place "$target"
  shred -u "$f"
done

chown -R guinevere:guinevere /home/guinevere/secrets
```

#### Secret Rotation Procedure

```bash
cat > /home/guinevere/scripts/rotate-secret.sh << 'SCRIPT'
#!/bin/bash
# Usage: ./rotate-secret.sh <service> <key_name> <new_value>
set -euo pipefail
SERVICE="${1:?Usage: rotate-secret.sh <service> <key_name> <new_value>}"
KEY_NAME="${2:?Missing key name}"
NEW_VALUE="${3:?Missing new value}"
SECRETS_DIR="/home/guinevere/secrets"
SOPS_KEY="/etc/sops/age/keys.txt"
BACKUP_DIR="/home/guinevere/data/backups/secrets"

mkdir -p "$BACKUP_DIR"
cp "${SECRETS_DIR}/${SERVICE}.env.sops" "${BACKUP_DIR}/${SERVICE}.env.sops.$(date +%Y%m%d%H%M%S)"
SOPS_AGE_KEY_FILE="$SOPS_KEY" sops --decrypt "${SECRETS_DIR}/${SERVICE}.env.sops" > /tmp/rotate_temp.env
sed -i "s|^${KEY_NAME}=.*|${KEY_NAME}=${NEW_VALUE}|" /tmp/rotate_temp.env
cp /tmp/rotate_temp.env "${SECRETS_DIR}/${SERVICE}.env.sops"
rm -f /tmp/rotate_temp.env
SOPS_AGE_KEY_FILE="$SOPS_KEY" sops --encrypt --in-place "${SECRETS_DIR}/${SERVICE}.env.sops"
systemctl restart "guinevere-${SERVICE}"
echo "OK: Secret rotatedated for ${SERVICE}/${KEY_NAME}"
SCRIPT
chmod +x /home/guinevere/scripts/rotate-secret.sh
```

#### Emergency Key Recovery

```bash
cat > /home/guinevere/scripts/emergency-key-recovery.sh << 'SCRIPT'
#!/bin/bash
set -euo pipefail
BACKUP_KEY="${1:?Usage: emergency-key-recovery.sh <path-to-backup-key>}"
mkdir -p /etc/sops/age
cp "$BACKUP_KEY" /etc/sops/age/keys.txt
chmod 600 /etc/sops/age/keys.txt
chown root:guinevere-svc /etc/sops/age/keys.txt
SOPS_AGE_KEY_FILE=/etc/sops/age/keys.txt sops --decrypt /home/guinevere/secrets/guinevere.env.sops > /dev/null
echo "OK: Key recovery successful"
SCRIPT
chmod +x /home/guinevere/scripts/emergency-key-recovery.sh
```
---

## 3. Service Deployment

### 3.1 guinevere-core (Main Agent Service)

```ini
# /etc/systemd/system/guinevere-core.service
[Unit]
Description=Guinevere Core Agent -- Hermes Agent + Persona Engine
After=network-online.target docker.service pgbouncer.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=simple
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/core
EnvironmentFile=-/run/guinevere/core.env
ExecStartPre=/usr/bin/sops --decrypt --output /run/guinevere/core.env /home/guinevere/secrets/core.env.sops
ExecStart=/home/guinevere/.venv/bin/python main.py
Restart=always
RestartSec=10
WatchdogSec=60
MemoryMax=4G
MemoryHigh=3584M
CPUQuota=200%
TasksMax=512
LimitNOFILE=65536
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ReadWritePaths=/home/guinevere/data /home/guinevere/core /run/guinevere
ReadOnlyPaths=/home/guinevere/config /home/guinevere/secrets
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
RestrictNamespaces=true
RestrictRealtime=true
RestrictSUIDSGID=true
LockPersonality=true
ProtectClock=true
ProtectControlGroups=true
ProtectHostname=true
ProtectKernelLogs=true
ProtectKernelModules=true
ProtectKernelTunables=true
PrivateDevices=true
SystemCallArchitectures=native
SystemCallFilter=@system-service
SystemCallFilter=~@privileged
SystemCallFilter=~@resources
CapabilityBoundingSet=
AmbientCapabilities=
StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-core
TimeoutStopSec=30
KillMode=mixed
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
```

```bash
mkdir -p /run/guinevere
chown guinevere:guinevere /run/guinevere
cat > /etc/tmpfiles.d/guinevere.conf << 'EOF'
d /run/guinevere 0755 guinevere guinevere -
EOF
systemctl daemon-reload
systemctl enable guinevere-core
```

**Health check endpoint:**
```bash
curl -s http://127.0.0.1:8100/health | jq .
# Expected: {"status": "healthy", "tier": 1, "version": "1.0.0"}
```

### 3.2 guinevere-surveillance (FastAPI Service)

```ini
# /etc/systemd/system/guinevere-surveillance.service
[Unit]
Description=Guinevere Surveillance Receiver -- FastAPI endpoints
After=network-online.target docker.service pgbouncer.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=simple
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/surveillance
EnvironmentFile=-/run/guinevere/surveillance.env
ExecStartPre=/usr/bin/sops --decrypt --output /run/guinevere/surveillance.env /home/guinevere/secrets/surveillance.env.sops
ExecStart=/home/guinevere/.venv/bin/uvicorn api:app --host 127.0.0.1 --port 8000 --workers 2 --timeout-keep-alive 65 --timeout-graceful-shutdown 30 --access-log --log-level info
Restart=always
RestartSec=10
MemoryMax=512M
MemoryHigh=448M
CPUQuota=100%
TasksMax=256
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ReadWritePaths=/home/guinevere/data /run/guinevere
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
RestrictNamespaces=true
ProtectKernelModules=true
ProtectKernelTunables=true
ProtectControlGroups=true
PrivateDevices=true
SystemCallArchitectures=native
CapabilityBoundingSet=
AmbientCapabilities=
StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-surveillance
TimeoutStopSec=30
KillMode=mixed
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
```

### 3.3 guinevere-windows-sync (WebSocket Server)

```ini
# /etc/systemd/system/guinevere-windows-sync.service
[Unit]
Description=Guinevere Windows Sync -- WebSocket server
After=network-online.target docker.service guinevere-surveillance.service
Wants=network-online.target

[Service]
Type=simple
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/windows-sync
EnvironmentFile=-/run/guinevere/surveillance.env
ExecStart=/home/guinevere/.venv/bin/python websocket_server.py
Restart=always
RestartSec=10
MemoryMax=256M
CPUQuota=50%
TasksMax=128
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ReadWritePaths=/home/guinevere/data /run/guinevere
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
PrivateDevices=true
SystemCallArchitectures=native
CapabilityBoundingSet=
StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-windows-sync
TimeoutStopSec=15

[Install]
WantedBy=multi-user.target
```

### 3.4 guinevere-loops (SDLC Loop Runner)

```ini
# /etc/systemd/system/guinevere-loops.service
[Unit]
Description=Guinevere SDLC Loop Runner -- Autonomous coding loops
After=network-online.target docker.service guinevere-core.service
Wants=network-online.target
Wants=guinevere-core.service

[Service]
Type=simple
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/loops
EnvironmentFile=-/run/guinevere/core.env
ExecStart=/home/guinevere/.venv/bin/python loop_runner.py
Restart=on-failure
RestartSec=10
StartLimitIntervalSec=300
StartLimitBurst=5
MemoryMax=512M
MemoryHigh=448M
CPUQuota=100%
TasksMax=256
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ReadWritePaths=/home/guinevere/data /home/guinevere/core /run/guinevere
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
PrivateDevices=true
SystemCallArchitectures=native
CapabilityBoundingSet=
StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-loops
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

### 3.5 guinevere-scheduler (Task Scheduler)

```ini
# /etc/systemd/system/guinevere-scheduler.service
[Unit]
Description=Guinevere Scheduler -- APScheduler + daily rituals
After=network-online.target docker.service guinevere-core.service
Wants=network-online.target

[Service]
Type=simple
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/scheduler
EnvironmentFile=-/run/guinevere/core.env
ExecStart=/home/guinevere/.venv/bin/python scheduler_main.py
Restart=always
RestartSec=30
MemoryMax=256M
CPUQuota=50%
TasksMax=128
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ReadWritePaths=/home/guinevere/data /run/guinevere
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
PrivateDevices=true
SystemCallArchitectures=native
CapabilityBoundingSet=
StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-scheduler
TimeoutStopSec=15

[Install]
WantedBy=multi-user.target
```

#### Systemd Timers

```ini
# /etc/systemd/system/guinevere-selfdeploy.timer
[Unit]
Description=Guinevere Self-Deploy Timer -- nightly at 03:00 WIB

[Timer]
OnCalendar=*-*-* 03:00:00 Asia/Jakarta
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/guinevere-selfdeploy.service
[Unit]
Description=Guinevere Self-Deploy -- git pull + uv sync + restart

[Service]
Type=oneshot
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/core
ExecStart=/home/guinevere/scripts/self-deploy.sh
StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-selfdeploy
```

```ini
# /etc/systemd/system/guinevere-backup.timer
[Unit]
Description=Guinevere Daily Backup Timer -- 02:00 WIB

[Timer]
OnCalendar=*-*-* 02:00:00 Asia/Jakarta
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/guinevere-backup.service
[Unit]
Description=Guinevere Daily Backup

[Service]
Type=oneshot
User=root
ExecStart=/home/guinevere/scripts/backup.sh
StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-backup
```

### 3.6 guinevere-discord (Discord Bot)

```ini
# /etc/systemd/system/guinevere-discord.service
[Unit]
Description=Guinevere Discord Bot -- Primary user interface
After=network-online.target guinevere-core.service
Wants=network-online.target
Wants=guinevere-core.service

[Service]
Type=simple
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/discord
EnvironmentFile=-/run/guinevere/core.env
ExecStart=/home/guinevere/.venv/bin/python bot.py
Restart=always
RestartSec=10
MemoryMax=512M
CPUQuota=50%
TasksMax=256
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ReadWritePaths=/home/guinevere/data /run/guinevere
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
PrivateDevices=true
SystemCallArchitectures=native
CapabilityBoundingSet=
StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-discord
TimeoutStopSec=30
KillSignal=SIGINT

[Install]
WantedBy=multi-user.target
```

**Discord Bot Setup (step-by-step):**
1. Navigate to https://discord.com/developers/applications
2. Click New Application -> Name: `Guinevere de Baroque` -> Create
3. Go to Bot tab -> Click Reset Token -> Copy token -> Store in SOPS as DISCORD_BOT_TOKEN
4. Enable Privileged Gateway Intents: MESSAGE CONTENT, PRESENCE, SERVER MEMBERS (all ON)
5. Go to OAuth2 -> URL Generator -> Scopes: bot, applications.commands
6. Bot Permissions: Send Messages, Read Messages, Embed Links, Attach Files, Read Message History, Use Slash Commands, Manage Messages
7. Copy generated invite URL -> Visit URL -> Select private server -> Authorize
8. Copy Application ID and Guild ID -> Store in SOPS

**Slash command registration (guild-specific for instant updates):**
```python
# In bot.py
import os, discord
from discord import app_commands
GUILD_ID = discord.Object(id=int(os.environ["DISCORD_GUILD_ID"]))
@bot.event
async def on_ready():
    bot.tree.copy_global_to(guild=GUILD_ID)
    await bot.tree.sync(guild=GUILD_ID)
    print(f"Discord bot online as {bot.user.name}")
```

### 3.7 guinevere-whatsapp (WhatsApp Service via Neonize)

```ini
# /etc/systemd/system/guinevere-whatsapp.service
[Unit]
Description=Guinevere WhatsApp Service -- Neonize (pure Python)
After=network-online.target guinevere-core.service postgresql.service
Wants=network-online.target

[Service]
Type=simple
User=guinevere
Group=guinevere
Slice=guinevere.slice
WorkingDirectory=/home/guinevere/guinevere
EnvironmentFile=-/run/guinevere/whatsapp.env
ExecStartPre=/usr/bin/sops --decrypt --output /run/guinevere/whatsapp.env /home/guinevere/secrets/whatsapp.env.sops
ExecStart=/home/guinevere/guinevere/.venv/bin/python -m src.whatsapp.main
Restart=always
RestartSec=10
MemoryMax=512M
CPUQuota=50%
TasksMax=256
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ReadWritePaths=/home/guinevere/data /run/guinevere
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
PrivateDevices=true
SystemCallArchitectures=native
CapabilityBoundingSet=
StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-whatsapp
TimeoutStopSec=15

[Install]
WantedBy=multi-user.target
```

```bash
# No additional setup required -- Neonize is installed via pip (included in guinevere requirements.txt)
# Session stored in PostgreSQL (Neonize native backend)
# DB credentials managed via SOPS
```

**QR Code Pairing Procedure:**
1. Start service: `systemctl start guinevere-whatsapp`
2. Watch logs: `journalctl -u guinevere-whatsapp -f`
3. QR code appears in terminal logs (or Discord notification with QR image)
4. On WhatsApp phone: Settings -> Linked Devices -> Link a Device -> Scan QR
5. For headless VPS, use pairing code via Discord command: `!wa-pair`
6. Verify session: `psql -U guinevere -d guinevere -c "SELECT * FROM whatsapp_sessions LIMIT 1;"`

### 3.8 guinevere-ollama (Local LLM Fallback -- ADR-028 Tier 3)

```ini
# /etc/systemd/system/guinevere-ollama.service
[Unit]
Description=Guinevere Ollama -- Local LLM fallback (ADR-028 Tier 3)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ollama
Group=ollama
EnvironmentFile=/etc/ollama/ollama.conf
ExecStart=/usr/local/bin/ollama serve
Restart=on-failure
RestartSec=5
MemoryMax=4G
MemoryHigh=3840M
CPUQuota=200%
TasksMax=128
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/home/ollama /var/lib/ollama
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
PrivateDevices=false
DeviceAllow=/dev/kvm rw
StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-ollama
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

```bash
mkdir -p /var/lib/ollama
chown ollama:ollama /var/lib/ollama
systemctl daemon-reload
systemctl enable guinevere-ollama
# NOT starting now -- only on Tier 3 entry per ADR-028

# Test commands (when running):
# curl -s http://127.0.0.1:11434/api/tags | jq '.models[].name'
# curl -s http://127.0.0.1:11434/api/generate -d '{"model":"phi3:mini-4k-instruct-q4_K_M","prompt":"Hello","stream":false}' | jq '.response'
```

### 3.9 Docker Services

#### Docker Installation

```bash
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker guinevere

cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "50m", "max-file": "3" },
  "storage-driver": "overlay2",
  "live-restore": true,
  "default-ulimits": { "nofile": { "Name": "nofile", "Hard": 65536, "Soft": 65536 } }
}
EOF

systemctl daemon-reload
systemctl enable --now docker
```

#### Docker Compose

```bash
mkdir -p /opt/guinevere-docker

cat > /opt/guinevere-docker/docker-compose.yml << 'EOF'
version: "3.9"
services:
  postgresql:
    image: timescale/timescaledb:latest-pg16
    container_name: postgresql
    restart: always
    environment:
      POSTGRES_DB: guinevere
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: "${POSTGRES_PASSWORD}"
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8 --locale=C"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init-db:/docker-entrypoint-initdb.d
    ports: ["127.0.0.1:5432:5432"]
    command: >
      postgres -c shared_buffers=2GB -c effective_cache_size=6GB -c work_mem=64MB
      -c maintenance_work_mem=512MB -c max_connections=200 -c max_wal_size=2GB
      -c min_wal_size=512MB -c checkpoint_completion_target=0.9 -c wal_buffers=64MB
      -c random_page_cost=1.1 -c effective_io_concurrency=200
      -c log_min_duration_statement=1000 -c log_checkpoints=on -c jit=off
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits: { memory: 4G, cpus: "1.0" }

  redis:
    image: redis:7-alpine
    container_name: redis
    restart: always
    command: >
      redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 1gb
      --maxmemory-policy allkeys-lru --save 60 1000 --appendonly yes --appendfsync everysec
    volumes: [redisdata:/data]
    ports: ["127.0.0.1:6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits: { memory: 1G, cpus: "0.5" }

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: always
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./prometheus/alert-rules.yml:/etc/prometheus/alert-rules.yml
      - prometheusdata:/prometheus
    ports: ["127.0.0.1:9090:9090"]
    command: ["--config.file=/etc/prometheus/prometheus.yml", "--storage.tsdb.path=/prometheus", "--storage.tsdb.retention.time=30d", "--storage.tsdb.retention.size=10GB", "--web.enable-lifecycle"]
    deploy:
      resources:
        limits: { memory: 2G, cpus: "0.5" }

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: always
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: "${GRAFANA_ADMIN_PASSWORD}"
      GF_SERVER_ROOT_URL: http://grafana.internal:3000
      GF_USERS_ALLOW_SIGN_UP: "false"
      GF_AUTH_ANONYMOUS_ENABLED: "false"
    volumes:
      - grafanadata:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    ports: ["127.0.0.1:3000:3000"]
    depends_on: [prometheus]
    deploy:
      resources:
        limits: { memory: 512M, cpus: "0.25" }

  loki:
    image: grafana/loki:latest
    container_name: loki
    restart: always
    volumes:
      - ./loki/loki-config.yml:/etc/loki/loki-config.yml
      - lokidata:/loki
    ports: ["127.0.0.1:3100:3100"]
    command: -config.file=/etc/loki/loki-config.yml
    deploy:
      resources:
        limits: { memory: 1G, cpus: "0.5" }

volumes:
  pgdata: { driver: local }
  redisdata: { driver: local }
  prometheusdata: { driver: local }
  grafanadata: { driver: local }
  lokidata: { driver: local }
EOF
```

#### Database Init Scripts

```bash
mkdir -p /opt/guinevere-docker/init-db

cat > /opt/guinevere-docker/init-db/01-extensions.sql << 'SQL'
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "timescaledb";
SQL

cat > /opt/guinevere-docker/init-db/02-users.sql << 'SQL'
CREATE USER guinevere_core WITH PASSWORD 'CHANGE_ME';
CREATE USER guinevere_surveillance WITH PASSWORD 'CHANGE_ME';
CREATE USER guinevere_financial WITH PASSWORD 'CHANGE_ME';
CREATE USER guinevere_readonly WITH PASSWORD 'CHANGE_ME';
CREATE USER guinevere_admin WITH PASSWORD 'CHANGE_ME';
CREATE USER pgbouncer_admin WITH PASSWORD 'CHANGE_ME';
CREATE USER pgbouncer_stats WITH PASSWORD 'CHANGE_ME';
SQL

cat > /opt/guinevere-docker/init-db/03-schemas.sql << 'SQL'
CREATE SCHEMA IF NOT EXISTS memory;
CREATE SCHEMA IF NOT EXISTS persona;
CREATE SCHEMA IF NOT EXISTS behavior;
CREATE SCHEMA IF NOT EXISTS surveillance;
CREATE SCHEMA IF NOT EXISTS financial;
CREATE SCHEMA IF NOT EXISTS projects;
CREATE SCHEMA IF NOT EXISTS system_schema;
CREATE SCHEMA IF NOT EXISTS social;
GRANT USAGE ON SCHEMA memory TO guinevere_core;
GRANT USAGE ON SCHEMA persona TO guinevere_core;
GRANT USAGE ON SCHEMA behavior TO guinevere_core;
GRANT USAGE ON SCHEMA projects TO guinevere_core;
GRANT USAGE ON SCHEMA system_schema TO guinevere_core;
GRANT USAGE ON SCHEMA social TO guinevere_core;
GRANT USAGE ON SCHEMA surveillance TO guinevere_core;
GRANT USAGE ON SCHEMA financial TO guinevere_core;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA memory TO guinevere_core;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA persona TO guinevere_core;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA behavior TO guinevere_core;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA projects TO guinevere_core;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA system_schema TO guinevere_core;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA social TO guinevere_core;
GRANT SELECT ON ALL TABLES IN SCHEMA surveillance TO guinevere_core;
GRANT SELECT ON ALL TABLES IN SCHEMA financial TO guinevere_core;
GRANT USAGE ON SCHEMA surveillance TO guinevere_surveillance;
GRANT INSERT, SELECT ON ALL TABLES IN SCHEMA surveillance TO guinevere_surveillance;
GRANT ALL ON ALL TABLES IN SCHEMA financial TO guinevere_financial;
GRANT USAGE ON SCHEMA financial TO guinevere_financial;
GRANT USAGE ON SCHEMA memory TO guinevere_readonly;
GRANT USAGE ON SCHEMA persona TO guinevere_readonly;
GRANT USAGE ON SCHEMA surveillance TO guinevere_readonly;
GRANT USAGE ON SCHEMA financial TO guinevere_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA memory TO guinevere_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA persona TO guinevere_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA surveillance TO guinevere_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA financial TO guinevere_readonly;
ALTER ROLE guinevere_admin WITH SUPERUSER;
ALTER DEFAULT PRIVILEGES IN SCHEMA memory GRANT SELECT, INSERT, UPDATE TO guinevere_core;
ALTER DEFAULT PRIVILEGES IN SCHEMA persona GRANT SELECT, INSERT, UPDATE TO guinevere_core;
ALTER DEFAULT PRIVILEGES IN SCHEMA surveillance GRANT INSERT, SELECT TO guinevere_surveillance;
ALTER DEFAULT PRIVILEGES IN SCHEMA financial GRANT ALL TO guinevere_financial;
ALTER DEFAULT PRIVILEGES IN SCHEMA memory GRANT SELECT TO guinevere_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA persona GRANT SELECT TO guinevere_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA surveillance GRANT SELECT TO guinevere_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA financial GRANT SELECT TO guinevere_readonly;
SQL
```

#### PgBouncer Configuration

```bash
apt install -y pgbouncer
mkdir -p /etc/pgbouncer

cat > /etc/pgbouncer/pgbouncer.ini << 'EOF'
[databases]
guinevere = host=127.0.0.1 port=5432 dbname=guinevere pool_size=30 pool_mode=transaction
guinevere_admin = host=127.0.0.1 port=5432 dbname=guinevere pool_size=5 pool_mode=session

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
auth_query = SELECT usename, passwd FROM pg_shadow WHERE usename=$1
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
min_pool_size = 5
reserve_pool_size = 5
reserve_pool_timeout = 3
server_idle_timeout = 600
server_lifetime = 3600
server_connect_timeout = 15
query_timeout = 30
query_wait_timeout = 120
idle_transaction_timeout = 15
max_db_connections = 100
log_pooler_errors = 1
admin_users = pgbouncer_admin
stats_users = pgbouncer_stats
stats_period = 60
EOF

mkdir -p /etc/systemd/system/pgbouncer.service.d
cat > /etc/systemd/system/pgbouncer.service.d/override.conf << 'EOF'
[Service]
ExecStart=
ExecStart=/usr/sbin/pgbouncer -u guinevere /etc/pgbouncer/pgbouncer.ini
Restart=always
RestartSec=5
EOF

systemctl daemon-reload
systemctl enable pgbouncer
```

#### Start Docker Stack

```bash
SOPS_AGE_KEY_FILE=/etc/sops/age/keys.txt sops --decrypt /home/guinevere/secrets/guinevere.env.sops > /opt/guinevere-docker/.env
chmod 600 /opt/guinevere-docker/.env

cd /opt/guinevere-docker
docker compose up -d

echo "Waiting for PostgreSQL..."
until docker exec postgresql pg_isready -U postgres 2>/dev/null; do sleep 2; done
echo "PostgreSQL ready"

echo "Waiting for Redis..."
until docker exec redis redis-cli -a "$(grep REDIS_PASSWORD /opt/guinevere-docker/.env | cut -d= -f2)" ping 2>/dev/null | grep -q PONG; do sleep 2; done
echo "Redis ready"

# Generate PgBouncer userlist
docker exec postgresql psql -U postgres -Atc \
  "SELECT concat('\"', rolname, '\" \"', rolpassword, '\"') FROM pg_authid WHERE rolpassword IS NOT NULL;" \
  > /etc/pgbouncer/userlist.txt
chmod 600 /etc/pgbouncer/userlist.txt
chown guinevere:guinevere /etc/pgbouncer/userlist.txt

systemctl start pgbouncer
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```
---

## 4. Network Configuration

### 4.1 Cloudflare Tunnel

```bash
# Install cloudflared from APT
mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/cloudflared.list
apt update && apt install -y cloudflared

# Authenticate (run on local machine, copy cert.pem to VPS)
# cloudflared tunnel login
# scp -P 2222 ~/.cloudflared/cert.pem root@<VPS_IP>:/root/.cloudflared/cert.pem

# Create tunnel
cloudflared tunnel create guinevere
# Note the Tunnel UUID

TUNNEL_UUID="<YOUR_TUNNEL_UUID>"

# Create DNS route
cloudflared tunnel route dns guinevere webhook.yourdomain.com

# Configuration file
mkdir -p /etc/cloudflared
cat > /etc/cloudflared/config.yml << EOF
tunnel: ${TUNNEL_UUID}
credentials-file: /root/.cloudflared/${TUNNEL_UUID}.json

ingress:
  - hostname: webhook.yourdomain.com
    path: /webhook/.*
    service: http://127.0.0.1:8000
    originRequest:
      noTLSVerify: true
      connectTimeout: 10s
      keepAliveTimeout: 90s

  - hostname: grafana.yourdomain.com
    service: http://127.0.0.1:3000

  - service: http_status:404
EOF

# Install as systemd service
cloudflared service install
systemctl daemon-reload
systemctl enable --now cloudflared

# Verify
cloudflared tunnel info guinevere
cloudflared tunnel list
```

**Troubleshooting checklist:**
- Tunnel shows "inactive": check `cloudflared tunnel info guinevere` for connection status
- 502 errors: verify FastAPI service is running on port 8000
- DNS not resolving: check `dig webhook.yourdomain.com` — CNAME should point to tunnel UUID
- Connection timeouts: verify `connectTimeout` in config.yml, check firewall not blocking outbound HTTPS

### 4.2 Tailscale

```bash
# Install Tailscale from official repo (NOT Snap)
curl -fsSL https://tailscale.com/install.sh | sh
systemctl enable --now tailscaled

# Authenticate with auth key and tag
# Generate reusable auth key: https://login.tailscale.com/admin/settings/keys
tailscale up \
  --authkey=tskey-auth-XXXXX \
  --advertise-tags=tag:server \
  --hostname=guinevere-vps \
  --ssh \
  --accept-dns=true

# In admin panel: Enable MagicDNS, Disable Key Expiry for guinevere-vps

# Verify
tailscale status
tailscale ip -4
```

#### Tailscale ACL Policy

```json
{
  "groups": { "group:admin": ["faiz@example.com"] },
  "tagOwners": {
    "tag:server": ["group:admin"],
    "tag:operator": ["group:admin"],
    "tag:monitoring": ["group:admin"]
  },
  "acls": [
    { "action": "accept", "src": ["tag:operator", "group:admin"], "dst": ["tag:server:*"] },
    { "action": "accept", "src": ["tag:server"], "dst": ["tag:server:*"] }
  ],
  "ssh": [
    { "action": "accept", "src": ["tag:operator", "group:admin"], "dst": ["tag:server"], "users": ["faiz", "guinevere"] }
  ],
  "autoApprovers": { "routes": { "10.0.0.0/24": ["tag:server"] }, "exitNode": [] }
}
```

#### Lock SSH to Tailscale Only

```bash
ufw delete limit 2222/tcp
ufw allow in on tailscale0 to any port 2222 proto tcp comment "SSH via Tailscale only"
ufw reload
ufw status verbose
```

### 4.3 Complete Firewall Rules (Final State)

```bash
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow in on tailscale0 to any port 2222 proto tcp comment "SSH via Tailscale"
ufw allow 41641/udp comment "Tailscale WireGuard"
ufw allow in on tailscale0 comment "Tailscale internal"
ufw allow in on lo comment "Loopback"
ufw logging on medium
ufw --force enable

echo "=== Final UFW Rules ==="
ufw status verbose
echo ""
echo "=== Listening Ports ==="
ss -tlnp | grep LISTEN
```

---

## 5. Monitoring & Observability Stack

### 5.1 Prometheus

```bash
mkdir -p /opt/guinevere-docker/prometheus

cat > /opt/guinevere-docker/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  scrape_timeout: 10s

rule_files:
  - "alert-rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["host.docker.internal:9093"]

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: "node"
    static_configs:
      - targets: ["host.docker.internal:9100"]
        labels:
          instance: "guinevere-vps"

  - job_name: "guinevere-core"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["host.docker.internal:8100"]
        labels:
          service: "core"

  - job_name: "guinevere-surveillance"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["host.docker.internal:8000"]
        labels:
          service: "surveillance"

  - job_name: "guinevere-scheduler"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["host.docker.internal:8101"]
        labels:
          service: "scheduler"

  - job_name: "guinevere-loops"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["host.docker.internal:8102"]
        labels:
          service: "loops"

  - job_name: "postgresql"
    static_configs:
      - targets: ["host.docker.internal:9187"]
        labels:
          service: "postgresql"

  - job_name: "redis"
    static_configs:
      - targets: ["host.docker.internal:9121"]
        labels:
          service: "redis"

  - job_name: "ollama"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["host.docker.internal:11434"]
        labels:
          service: "ollama"
EOF
```

#### Alert Rules

```bash
cat > /opt/guinevere-docker/prometheus/alert-rules.yml << 'EOF'
groups:
  - name: infrastructure
    rules:
      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 85
        for: 10m
        labels: { severity: warning }
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"
          description: "CPU above 85% for 10 min (current: {{ $value }}%)"
      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100 > 90
        for: 5m
        labels: { severity: critical }
        annotations:
          summary: "High memory usage"
          description: "Memory above 90% for 5 min (current: {{ $value }}%)"
      - alert: DiskSpaceLow
        expr: (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100 < 15
        for: 5m
        labels: { severity: warning }
        annotations:
          summary: "Low disk space"
          description: "Available below 15% (current: {{ $value }}%)"
      - alert: DiskSpaceCritical
        expr: (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100 < 5
        for: 2m
        labels: { severity: critical }
        annotations:
          summary: "Critical disk space"
          description: "Available below 5% (current: {{ $value }}%)"
      - alert: SwapUsageHigh
        expr: (node_memory_SwapTotal_bytes - node_memory_SwapFree_bytes) / node_memory_SwapTotal_bytes * 100 > 50
        for: 5m
        labels: { severity: warning }
        annotations:
          summary: "High swap usage"
          description: "Swap above 50% -- possible memory pressure"

  - name: services
    rules:
      - alert: ServiceDown
        expr: guinevere_systemd_unit_state{state="active"} == 0
        for: 1m
        labels: { severity: critical }
        annotations:
          summary: "Service {{ $labels.unit }} is down"
      - alert: ServiceRestarting
        expr: increase(guinevere_systemd_unit_restarts_total[10m]) > 3
        labels: { severity: warning }
        annotations:
          summary: "Service {{ $labels.unit }} restarting frequently"

  - name: database
    rules:
      - alert: PostgreSQLDown
        expr: pg_up == 0
        for: 1m
        labels: { severity: critical }
        annotations:
          summary: "PostgreSQL is down"
      - alert: RedisDown
        expr: redis_up == 0
        for: 1m
        labels: { severity: critical }
        annotations:
          summary: "Redis is down"
      - alert: PgBouncerConnectionsWaiting
        expr: pgbouncer_pools_cl_waiting > 0
        for: 30s
        labels: { severity: warning }
        annotations:
          summary: "PgBouncer clients waiting"
          description: "{{ $value }} clients waiting"

  - name: llm
    rules:
      - alert: LLMTierDegraded
        expr: guinevere_llm_tier > 1
        for: 2m
        labels: { severity: warning }
        annotations:
          summary: "LLM at Tier {{ $value }}"
      - alert: LLMTierCritical
        expr: guinevere_llm_tier >= 3
        for: 1m
        labels: { severity: critical }
        annotations:
          summary: "LLM at Tier {{ $value }} -- local/degraded"

  - name: cost
    rules:
      - alert: DailyCostOverBudget
        expr: increase(guinevere_llm_cost_usd_total[24h]) > 2.0
        labels: { severity: warning }
        annotations:
          summary: "Daily LLM cost exceeds $2.00"
          description: "24h cost: ${{ $value }}"
      - alert: MonthlyCostProjectedOverBudget
        expr: guinevere_llm_cost_usd_total / (day_of_month() / 30) > 30
        labels: { severity: critical }
        annotations:
          summary: "Monthly cost projected exceeds $30 budget"
EOF
```

#### Exporters

```bash
# Node Exporter
NODE_EXPORTER_VERSION="1.8.2"
curl -LO "https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
tar xzf "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
cp "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter" /usr/local/bin/
rm -rf "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64"*
useradd -r -s /usr/sbin/nologin node_exporter 2>/dev/null || true

cat > /etc/systemd/system/node_exporter.service << 'EOF'
[Unit]
Description=Prometheus Node Exporter
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=node_exporter
ExecStart=/usr/local/bin/node_exporter --collector.systemd --collector.processes --web.listen-address=127.0.0.1:9100
Restart=always
RestartSec=5
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# PostgreSQL Exporter
POSTGRES_EXPORTER_VERSION="0.16.0"
curl -LO "https://github.com/prometheus-community/postgres_exporter/releases/download/v${POSTGRES_EXPORTER_VERSION}/postgres_exporter-${POSTGRES_EXPORTER_VERSION}.linux-amd64.tar.gz"
tar xzf "postgres_exporter-${POSTGRES_EXPORTER_VERSION}.linux-amd64.tar.gz"
cp "postgres_exporter-${POSTGRES_EXPORTER_VERSION}.linux-amd64/postgres_exporter" /usr/local/bin/
rm -rf "postgres_exporter-${POSTGRES_EXPORTER_VERSION}.linux-amd64"*

cat > /etc/systemd/system/postgres_exporter.service << 'EOF'
[Unit]
Description=Prometheus PostgreSQL Exporter
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=guinevere
Environment="DATA_SOURCE_NAME=postgresql://guinevere_readonly:READONLY_PASSWORD@127.0.0.1:6432/guinevere?sslmode=disable"
ExecStart=/usr/local/bin/postgres_exporter --web.listen-address=127.0.0.1:9187
Restart=always
RestartSec=5
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Redis Exporter
REDIS_EXPORTER_VERSION="1.67.0"
curl -LO "https://github.com/oliver006/redis_exporter/releases/download/v${REDIS_EXPORTER_VERSION}/redis_exporter-v${REDIS_EXPORTER_VERSION}.linux-amd64.tar.gz"
tar xzf "redis_exporter-v${REDIS_EXPORTER_VERSION}.linux-amd64.tar.gz"
cp "redis_exporter-v${REDIS_EXPORTER_VERSION}.linux-amd64/redis_exporter" /usr/local/bin/
rm -rf "redis_exporter-v${REDIS_EXPORTER_VERSION}.linux-amd64"*

cat > /etc/systemd/system/redis_exporter.service << 'EOF'
[Unit]
Description=Prometheus Redis Exporter
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=guinevere
Environment="REDIS_ADDR=redis://127.0.0.1:6379"
Environment="REDIS_PASSWORD=REDIS_PASSWORD_HERE"
ExecStart=/usr/local/bin/redis_exporter --web.listen-address=127.0.0.1:9121
Restart=always
RestartSec=5
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now node_exporter postgres_exporter redis_exporter
```

### 5.2 Grafana

```bash
mkdir -p /opt/guinevere-docker/grafana/provisioning/{datasources,dashboards,alerting}

cat > /opt/guinevere-docker/grafana/provisioning/datasources/datasources.yml << 'EOF'
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
    jsonData:
      timeInterval: "15s"
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: false
    jsonData:
      maxLines: 1000
EOF

cat > /opt/guinevere-docker/grafana/provisioning/dashboards/dashboards.yml << 'EOF'
apiVersion: 1
providers:
  - name: "Guinevere"
    orgId: 1
    folder: "Guinevere"
    type: file
    disableDeletion: false
    editable: true
    updateIntervalSeconds: 30
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: true
EOF

mkdir -p /opt/guinevere-docker/grafana/dashboards
```

### 5.3 Loki

```bash
mkdir -p /opt/guinevere-docker/loki

cat > /opt/guinevere-docker/loki/loki-config.yml << 'EOF'
auth_enabled: false
server:
  http_listen_port: 3100
  grpc_listen_port: 9096
common:
  instance_addr: 127.0.0.1
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory
query_range:
  results_cache:
    cache:
      embedded_cache:
        enabled: true
        max_size_mb: 100
schema_config:
  configs:
    - from: "2026-01-01"
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h
limits_config:
  reject_old_samples: true
  reject_old_samples_max_age: 168h
  max_entries_limit_per_query: 5000
  ingestion_rate_mb: 10
  ingestion_burst_size_mb: 20
compactor:
  working_directory: /loki/compactor
  compaction_interval: 10m
  retention_enabled: true
  retention_delete_delay: 2h
  delete_request_store: filesystem
analytics:
  reporting_enabled: false
EOF
```

#### Promtail

```bash
PROMTAIL_VERSION="3.3.2"
curl -LO "https://github.com/grafana/loki/releases/download/v${PROMTAIL_VERSION}/promtail-linux-amd64.zip"
unzip -o "promtail-linux-amd64.zip"
cp promtail-linux-amd64 /usr/local/bin/promtail
rm -f "promtail-linux-amd64.zip" promtail-linux-amd64
chmod +x /usr/local/bin/promtail

mkdir -p /etc/promtail
cat > /etc/promtail/promtail-config.yml << 'EOF'
server:
  http_listen_port: 9080
  grpc_listen_port: 0
positions:
  filename: /tmp/positions.yaml
clients:
  - url: http://127.0.0.1:3100/loki/api/v1/push
scrape_configs:
  - job_name: journal
    journal:
      max_age: 12h
      labels:
        job: systemd-journal
    relabel_configs:
      - source_labels: ["__journal__systemd_unit"]
        target_label: "unit"
      - source_labels: ["__journal_syslog_identifier"]
        target_label: "service"
  - job_name: guinevere-app-logs
    static_configs:
      - targets: [localhost]
        labels:
          job: guinevere-app
          __path__: /home/guinevere/data/logs/*.log
    pipeline_stages:
      - json:
          expressions:
            level: level
            service: service
      - labels:
          level:
          service:
EOF

cat > /etc/systemd/system/promtail.service << 'EOF'
[Unit]
Description=Promtail Log Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=guinevere
Group=guinevere
ExecStart=/usr/local/bin/promtail -config.file=/etc/promtail/promtail-config.yml
Restart=always
RestartSec=5
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/tmp /home/guinevere/data/logs
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now promtail
```

### 5.4 Alertmanager

```bash
ALERTMANAGER_VERSION="0.28.0"
curl -LO "https://github.com/prometheus/alertmanager/releases/download/v${ALERTMANAGER_VERSION}/alertmanager-${ALERTMANAGER_VERSION}.linux-amd64.tar.gz"
tar xzf "alertmanager-${ALERTMANAGER_VERSION}.linux-amd64.tar.gz"
cp "alertmanager-${ALERTMANAGER_VERSION}.linux-amd64/alertmanager" /usr/local/bin/
cp "alertmanager-${ALERTMANAGER_VERSION}.linux-amd64/amtool" /usr/local/bin/
rm -rf "alertmanager-${ALERTMANAGER_VERSION}.linux-amd64"*

mkdir -p /etc/alertmanager /var/lib/alertmanager

cat > /etc/alertmanager/alertmanager.yml << 'EOF'
global:
  resolve_timeout: 5m
route:
  group_by: ["alertname", "severity"]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: "discord-default"
  routes:
    - match: { severity: critical }
      receiver: "discord-critical"
      repeat_interval: 1h
    - match: { severity: warning }
      receiver: "discord-warning"
      repeat_interval: 4h
receivers:
  - name: "discord-critical"
    discord_configs:
      - webhook_url: "DISCORD_WEBHOOK_URL_HERE"
        title: "CRITICAL: {{ .GroupLabels.alertname }}"
        message: "{{ range .Alerts }}{{ .Annotations.summary }}\n{{ .Annotations.description }}\n{{ end }}"
  - name: "discord-warning"
    discord_configs:
      - webhook_url: "DISCORD_WEBHOOK_URL_HERE"
        title: "WARNING: {{ .GroupLabels.alertname }}"
        message: "{{ range .Alerts }}{{ .Annotations.summary }}\n{{ end }}"
  - name: "discord-default"
    discord_configs:
      - webhook_url: "DISCORD_WEBHOOK_URL_HERE"
        title: "{{ .GroupLabels.alertname }}"
        message: "{{ range .Alerts }}{{ .Annotations.summary }}\n{{ end }}"
inhibit_rules:
  - source_match: { severity: "critical" }
    target_match: { severity: "warning" }
    equal: ["alertname"]
EOF

cat > /etc/systemd/system/alertmanager.service << 'EOF'
[Unit]
Description=Prometheus Alertmanager
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=guinevere
Group=guinevere
ExecStart=/usr/local/bin/alertmanager --config.file=/etc/alertmanager/alertmanager.yml --storage.path=/var/lib/alertmanager --web.listen-address=127.0.0.1:9093
Restart=always
RestartSec=5
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/var/lib/alertmanager

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now alertmanager
```
---

## 6. Database Management

### 6.1 PostgreSQL Operations

#### Alembic Migration Setup

```bash
cd /home/guinevere/core
su - guinevere -s /bin/bash << 'ALEMBIC'
cd ~/core
eval "$(pyenv init -)"
uv run alembic init alembic
sed -i "s|^sqlalchemy.url.*|sqlalchemy.url = postgresql://guinevere_admin:ADMIN_PASSWORD@127.0.0.1:6432/guinevere|" alembic.ini
uv run alembic revision --autogenerate -m "initial_schema"
uv run alembic upgrade head
uv run alembic current
ALEMBIC
```

#### Index Creation (pgvector + FTS + TimescaleDB)

```bash
docker exec -i postgresql psql -U postgres -d guinevere << 'SQL'
-- pgvector index for semantic memory search
CREATE INDEX IF NOT EXISTS idx_memory_embeddings_ivfflat
  ON memory.episodes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Full-text search index on episodes
CREATE INDEX IF NOT EXISTS idx_memory_episodes_fts
  ON memory.episodes USING gin(to_tsvector('english', coalesce(content, '')));

-- TimescaleDB hypertables for surveillance
SELECT create_hypertable('surveillance.activity_log', 'created_at', if_not_exists => TRUE);
SELECT create_hypertable('surveillance.location_history', 'recorded_at', if_not_exists => TRUE);
SELECT create_hypertable('surveillance.health_data', 'recorded_at', if_not_exists => TRUE);

-- TimescaleDB compression policies (compress after 7 days)
SELECT add_compression_policy('surveillance.activity_log', INTERVAL '7 days');
SELECT add_compression_policy('surveillance.location_history', INTERVAL '7 days');
SELECT add_compression_policy('surveillance.health_data', INTERVAL '7 days');

-- TimescaleDB retention (keep raw data 90 days)
SELECT add_retention_policy('surveillance.activity_log', INTERVAL '90 days');
SQL
```

#### Vacuum and Optimize Schedule

```bash
cat > /etc/systemd/system/guinevere-db-vacuum.timer << 'EOF'
[Unit]
Description=PostgreSQL VACUUM ANALYZE -- weekly

[Timer]
OnCalendar=Sun *-*-* 04:00:00 Asia/Jakarta
Persistent=true

[Install]
WantedBy=timers.target
EOF

cat > /etc/systemd/system/guinevere-db-vacuum.service << 'EOF'
[Unit]
Description=PostgreSQL VACUUM ANALYZE

[Service]
Type=oneshot
ExecStart=/usr/bin/docker exec postgresql psql -U postgres -d guinevere -c "VACUUM ANALYZE;"
StandardOutput=journal
StandardError=journal
SyslogIdentifier=guinevere-db-vacuum
EOF

systemctl daemon-reload
systemctl enable --now guinevere-db-vacuum.timer
```

#### Corruption Detection

```bash
# Run pg_amcheck for corruption detection
docker exec postgresql pg_amcheck -U postgres -d guinevere --heapallindexed -v 2>&1 | tail -20

# If corruption found, restore from latest backup:
# /home/guinevere/scripts/restore-db.sh /path/to/backup.age
```

### 6.2 Future PostgreSQL Migration Path

```bash
# Template for migration to dedicated PostgreSQL server
# 1. Dump all data
docker exec postgresql pg_dumpall -U postgres > /tmp/full_dump.sql

# 2. Transfer to new server
scp -P 2222 /tmp/full_dump.sql faiz@new-server:/tmp/

# 3. Restore on new server
ssh -p 2222 faiz@new-server 'docker exec -i postgresql psql -U postgres < /tmp/full_dump.sql'

# 4. Verify
docker exec postgresql psql -U guinevere_readonly -h new-server-ip -d guinevere -c "SELECT count(*) FROM memory.episodes;"
```

---

## 7. Backup & Disaster Recovery

### 7.1 Backup Strategy

| Data | Method | Frequency | Destination | Retention |
|---|---|---|---|---|
| PostgreSQL (hot) | WAL streaming | Continuous | Cloudflare R2 | Forever |
| PostgreSQL (cold) | pg_dumpall + gzip | Daily 02:00 WIB | idcloudhost S3 | 30 days local, forever offsite |
| Redis | RDB snapshot | Hourly + AOF | Local + R2 | 7 days local, forever offsite |
| Guinevere config | git push | Per commit | GitHub private repo | Forever |
| Secrets (.env.sops) | git push (encrypted) | Per change | GitHub private repo | Forever |
| Surveillance screenshots | Encrypted upload | Real-time | R2 + idcloudhost | Forever |
| VPS snapshot | hostdata.id snapshot | Weekly | hostdata.id | 4 snapshots rotating |

### 7.2 Complete Backup Script

```bash
#!/bin/bash
# /home/guinevere/scripts/backup.sh
set -euo pipefail

BACKUP_DIR="/home/guinevere/data/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p "${BACKUP_DIR}"/{postgres,redis,config,logs}
echo "[$(date)] Starting backup..."

# 1. PostgreSQL dump
echo "  -> PostgreSQL dump..."
docker exec postgresql pg_dumpall -U postgres --clean | gzip > "${BACKUP_DIR}/postgres/pg_dumpall_${DATE}.sql.gz"
echo "  OK: $(du -h "${BACKUP_DIR}/postgres/pg_dumpall_${DATE}.sql.gz" | cut -f1)"

# 2. Redis snapshot
echo "  -> Redis RDB snapshot..."
docker exec redis redis-cli -a "${REDIS_PASSWORD}" BGSAVE 2>/dev/null
sleep 5
docker cp redis:/data/dump.rdb "${BACKUP_DIR}/redis/dump_${DATE}.rdb"

# 3. Configuration backup
echo "  -> Configuration files..."
tar czf "${BACKUP_DIR}/config/config_${DATE}.tar.gz" \
  /home/guinevere/secrets/ /home/guinevere/config/ \
  /etc/systemd/system/guinevere-*.service \
  /etc/pgbouncer/ /etc/cloudflared/ /etc/alertmanager/ 2>/dev/null || true

# 4. Encrypt backups
echo "  -> Encrypting..."
for f in "${BACKUP_DIR}/postgres/pg_dumpall_${DATE}.sql.gz" \
         "${BACKUP_DIR}/redis/dump_${DATE}.rdb" \
         "${BACKUP_DIR}/config/config_${DATE}.tar.gz"; do
  if [ -f "$f" ]; then
    age -r "$(cat /etc/sops/age/public.txt)" -o "${f}.age" "$f"
    rm -f "$f"
  fi
done

# 5. Upload to R2
echo "  -> Uploading to R2..."
rclone copy "${BACKUP_DIR}/postgres/" "r2:guinevere-backups/postgres/" --transfers 4 2>/dev/null || echo "  WARN: R2 upload failed"
rclone copy "${BACKUP_DIR}/redis/" "r2:guinevere-backups/redis/" --transfers 4 2>/dev/null || true

# 6. Upload to idcloudhost S3
echo "  -> Uploading to S3..."
rclone copy "${BACKUP_DIR}/postgres/" "idcloudhost:guinevere-backups/postgres/" --transfers 4 2>/dev/null || echo "  WARN: S3 upload failed"

# 7. Cleanup old backups
echo "  -> Cleaning up (>${RETENTION_DAYS} days)..."
find "${BACKUP_DIR}/postgres/" -name "*.age" -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}/redis/" -name "*.age" -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}/config/" -name "*.age" -mtime +${RETENTION_DAYS} -delete

# 8. Verify backup integrity
LATEST_PG=$(ls -t "${BACKUP_DIR}/postgres/"*.age 2>/dev/null | head -1)
if [ -n "$LATEST_PG" ]; then
  age -d -i /etc/sops/age/keys.txt "$LATEST_PG" | gunzip -t && echo "  OK: Verified" || echo "  FAIL: CORRUPT"
fi

echo "[$(date)] Backup complete"
```

### 7.3 Restore Procedures

#### Full System Restore

```bash
#!/bin/bash
# /home/guinevere/scripts/full-restore.sh
set -euo pipefail

echo "============================================"
echo " GUINEVERE FULL SYSTEM RESTORE"
echo "============================================"

# Phase 2: Restore age key
if [ ! -f /etc/sops/age/keys.txt ]; then
  echo "ERROR: Restore age key first from backup"
  exit 1
fi

# Clone repository
git clone git@github.com:faiz/guinevere-de-baroque.git /home/guinevere/core
chown -R guinevere:guinevere /home/guinevere/core

# Phase 3: Start Docker + restore PostgreSQL
cd /opt/guinevere-docker
docker compose up -d postgresql redis
sleep 10

LATEST_BACKUP=$(rclone lsf r2:guinevere-backups/postgres/ 2>/dev/null | sort -r | head -1)
if [ -n "$LATEST_BACKUP" ]; then
  rclone copy "r2:guinevere-backups/postgres/${LATEST_BACKUP}" /tmp/
  age -d -i /etc/sops/age/keys.txt "/tmp/${LATEST_BACKUP}" | gunzip | docker exec -i postgresql psql -U postgres
  echo "OK: PostgreSQL restored"
fi

# Phase 4: Restore Redis
LATEST_REDIS=$(rclone lsf r2:guinevere-backups/redis/ 2>/dev/null | sort -r | head -1)
if [ -n "$LATEST_REDIS" ]; then
  rclone copy "r2:guinevere-backups/redis/${LATEST_REDIS}" /tmp/
  docker stop redis
  age -d -i /etc/sops/age/keys.txt "/tmp/${LATEST_REDIS}" > /opt/guinevere-docker/redisdata/dump.rdb
  docker start redis
  echo "OK: Redis restored"
fi

# Phase 5: Deploy application
su - guinevere -s /bin/bash << 'DEPLOY'
cd ~/core
eval "$(pyenv init -)"
uv sync --frozen
DEPLOY

# Phase 6: Start services
systemctl start pgbouncer
for svc in guinevere-core guinevere-surveillance guinevere-scheduler guinevere-loops guinevere-discord guinevere-whatsapp guinevere-windows-sync; do
  systemctl start "$svc"
  sleep 2
done

# Phase 7: Verify
systemctl is-active guinevere-core guinevere-surveillance guinevere-scheduler guinevere-loops guinevere-discord
docker ps --format "table {{.Names}}\t{{.Status}}"
echo "Restore complete. Run pre-flight checks."
```

#### Partial Restore (Database Only)

```bash
#!/bin/bash
# /home/guinevere/scripts/restore-db.sh
set -euo pipefail
BACKUP_FILE="${1:?Usage: restore-db.sh <backup_file.age>}"

echo "Decrypting backup..."
age -d -i /etc/sops/age/keys.txt "$BACKUP_FILE" | gunzip > /tmp/restore_dump.sql

echo "Stopping application services..."
systemctl stop guinevere-core guinevere-surveillance guinevere-scheduler guinevere-loops guinevere-discord

echo "Restoring database..."
docker exec -i postgresql psql -U postgres < /tmp/restore_dump.sql
rm -f /tmp/restore_dump.sql

echo "Restarting services..."
for svc in guinevere-core guinevere-surveillance guinevere-scheduler guinevere-loops guinevere-discord; do
  systemctl start "$svc"
  sleep 2
done
echo "OK: Database restore complete"
```

### 7.4 Disaster Recovery Targets

| Scenario | RTO | RPO | Recovery Steps |
|---|---|---|---|
| Service crash | < 30s | 0 | systemd auto-restart |
| VPS full down | < 30 min | < 1 hour | Restore snapshot + WAL replay |
| Database corruption | < 1 hour | < 1 hour | pg_restore from latest backup |
| Redis loss | < 5 min | < 1 hour | AOF replay or RDB restore |
| Secrets compromise | < 1 hour | 0 | SOPS re-encrypt + rotate all keys |
| LLM provider down | < 1 min | 0 | Automatic tier failover (ADR-028) |

### 7.5 DR Test Schedule

| Test | Frequency | Procedure | Evidence |
|---|---|---|---|
| Backup integrity check | Daily | Automated: decrypt + gunzip -t | Log in backup.sh output |
| Restore test (staging) | Monthly | Full restore to staging DB | evidence/dr-drills/ |
| Full DR drill | Quarterly | Complete VPS rebuild from scratch | evidence/dr-drills/ |
| Failover test (LLM) | Monthly | Test all 4 tiers of ADR-028 | Discord notification + log |

---

## 8. Update & Release Management

### 8.1 Self-Deploy Script

```bash
#!/bin/bash
# /home/guinevere/scripts/self-deploy.sh
set -euo pipefail

REPO_DIR="/home/guinevere/core"
LOG_FILE="/home/guinevere/data/logs/deploy.log"
DEPLOY_LOCK="/tmp/guinevere-deploy.lock"

exec 9>"$DEPLOY_LOCK"
flock -n 9 || { echo "Deploy already in progress"; exit 1; }

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

log "=== Starting self-deploy ==="

# Pre-deploy backup
log "Creating pre-deploy backup..."
/home/guinevere/scripts/backup.sh >> "$LOG_FILE" 2>&1 || log "WARN: Backup failed"

cd "$REPO_DIR"
log "Fetching latest changes..."
git fetch origin main
CURRENT=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$CURRENT" = "$REMOTE" ]; then
  log "Already up to date."
  exit 0
fi

log "New commits: $CURRENT -> $REMOTE"
log "Pulling changes..."
git pull origin main

log "Syncing dependencies..."
eval "$(pyenv init -)"
uv sync --frozen

log "Running tests..."
if uv run pytest tests/ -x -q --timeout=60; then
  log "Tests passed"
else
  log "FAIL: Tests failed -- rolling back to previous commit"
  git checkout HEAD~1
  uv sync --frozen
  systemctl restart guinevere-core guinevere-surveillance guinevere-scheduler guinevere-loops guinevere-discord
  log "Rollback complete"
  exit 1
fi

log "Restarting services..."
for svc in guinevere-core guinevere-surveillance guinevere-scheduler guinevere-loops guinevere-discord guinevere-whatsapp; do
  systemctl restart "$svc"
  sleep 3
  systemctl is-active --quiet "$svc" && log "OK: $svc" || log "FAIL: $svc"
done

sleep 10
/home/guinevere/scripts/health-check.sh >> "$LOG_FILE" 2>&1
log "=== Self-deploy complete ==="
```

### 8.2 Manual Deployment Procedure

```bash
# When Guinevere cannot self-deploy:
cd /home/guinevere/core
git fetch origin main
git pull origin main
eval "$(pyenv init -)"
uv sync --frozen

# Run tests
uv run pytest tests/ -x -q --timeout=60

# Restart services in correct order
sudo systemctl restart guinevere-core
sleep 5
sudo systemctl restart guinevere-surveillance guinevere-scheduler guinevere-loops
sleep 3
sudo systemctl restart guinevere-discord guinevere-whatsapp guinevere-windows-sync

# Verify
/home/guinevere/scripts/health-check.sh
```

### 8.3 Rollback Procedure

```bash
#!/bin/bash
# /home/guinevere/scripts/rollback.sh
set -euo pipefail
TARGET_TAG="${1:?Usage: rollback.sh <git-tag-or-commit>}"

echo "Rolling back to: $TARGET_TAG"
cd /home/guinevere/core

# Stop services
systemctl stop guinevere-core guinevere-surveillance guinevere-scheduler guinevere-loops guinevere-discord

# Checkout target
git checkout "$TARGET_TAG"

# Reinstall dependencies
eval "$(pyenv init -)"
uv sync --frozen

# Restart services
for svc in guinevere-core guinevere-surveillance guinevere-scheduler guinevere-loops guinevere-discord guinevere-whatsapp; do
  systemctl start "$svc"
  sleep 3
done

# Verify
/home/guinevere/scripts/health-check.sh
echo "Rollback to $TARGET_TAG complete"
```

### 8.4 GitHub Actions CI Pipeline

```yaml
# .github/workflows/ci.yml
name: Guinevere CI
on:
  push:
    branches: [main, develop, "feature/**"]
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run ruff format --check .

  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --frozen
      - run: uv run mypy . --ignore-missing-imports

  test:
    runs-on: ubuntu-latest
    needs: [lint, type-check]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --frozen
      - run: uv run pytest tests/ -x --timeout=60 --cov=. --cov-report=term-missing

  security-scan:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --frozen
      - run: uv run bandit -r . -x tests/
      - run: uv run safety check

  notify:
    runs-on: ubuntu-latest
    needs: [lint, type-check, test, security-scan]
    if: always()
    steps:
      - name: Notify Discord
        run: |
          STATUS="${{ needs.test.result }}"
          curl -X POST "$DISCORD_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"content\": \"CI $STATUS on ${{ github.ref_name }}\"}"
```
---

## 9. Troubleshooting Guide

### 9.1 Common Issues Table

| Symptom | Likely Cause | Diagnostic Command | Fix |
|---|---|---|---|
| Service won't start | Config error or missing dep | `journalctl -u guinevere-core -n 50` | Check logs, verify secrets decrypt, check DB |
| High memory usage | Ollama running during Tier 1 | `systemctl status guinevere-ollama` | `systemctl stop guinevere-ollama` |
| Discord bot offline | Token expired or bad intents | `journalctl -u guinevere-discord -n 20` | Verify token in SOPS, check Developer Portal |
| WhatsApp disconnected | Session expired or Neonize connection drop | `journalctl -u guinevere-whatsapp -n 20` | Re-pair QR or use `!wa-pair` Discord command |
| DB connection refused | PostgreSQL or PgBouncer down | `docker ps` + `systemctl status pgbouncer` | `docker restart postgresql` |
| Slow LLM responses | Tier degradation | `curl http://127.0.0.1:8100/health` | Check tier, wait for provider |
| Disk full | Logs or DB growth | `df -h` + `du -sh /var/lib/docker/*` | Vacuum DB, clean logs |
| Tailscale disconnected | Auth key expired | `tailscale status` | Re-auth with new key |
| Cloudflare Tunnel down | Process crashed | `systemctl status cloudflared` | `systemctl restart cloudflared` |
| Alert not firing | Alertmanager config issue | `amtool check-config` | Fix config, restart |
| Backup failing | Credentials expired | `journalctl -u guinevere-backup -n 30` | Update rclone config |
| OOM killed | RAM contention | `dmesg -- grep -i oom` | Stop Ollama, add swap |
| Secrets decryption fails | Age key issue | `sops --decrypt secrets/core.env.sops` | Restore from backup |

### 9.2 Service-Specific Troubleshooting

```bash
journalctl -u guinevere-core -f
journalctl -u guinevere-surveillance --since "1 hour ago"
journalctl -u guinevere-discord -n 100 --no-pager
systemctl status guinevere-core -l
systemctl show guinevere-core | grep -E "Memory|CPU|Tasks"
ss -tlnp | grep guinevere
```

### 9.3 Log Analysis

```bash
journalctl -u "guinevere-*" --since "today" | grep -i "error\|exception\|traceback"
dmesg | grep -i "oom\|killed process"
journalctl -k | grep -i "oom"
du -sh /var/log/journal/*/
journalctl --disk-usage
```

### 9.4 Performance Debugging

```bash
top -bn1 | head -20
iotop -bon1 | head -20
ss -tnp | grep -E "ESTAB|TIME_WAIT" | wc -l
ss -s
docker stats --no-stream

# Database slow queries
docker exec postgresql psql -U postgres -d guinevere -c "
  SELECT query, calls, total_exec_time/calls as avg_ms
  FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10;"

# Redis memory
docker exec redis redis-cli -a "$REDIS_PASSWORD" INFO memory | grep used_memory_human
```

### 9.5 Network Debugging

```bash
curl -s -o /dev/null -w "%{http_code} %{time_total}s" \
  "${NINEROUTER_BASE_URL}/models" -H "Authorization: Bearer ${NINEROUTER_API_KEY}"
curl -s -o /dev/null -w "%{http_code}" \
  "https://discord.com/api/v10/users/@me" -H "Authorization: Bot ${DISCORD_BOT_TOKEN}"
dig webhook.yourdomain.com +short
tailscale ping guinevere-vps
tailscale status
```

### 9.6 Database Debugging

```bash
docker exec postgresql psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
docker exec postgresql psql -U postgres -d guinevere -c "
  SELECT pid, usename, state, query_start FROM pg_stat_activity WHERE state != 'idle' ORDER BY query_start;"
docker exec postgresql psql -U postgres -d guinevere -c "
  SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
  FROM pg_tables ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC LIMIT 20;"
psql -h 127.0.0.1 -p 6432 -U pgbouncer_admin pgbouncer -c "SHOW POOLS;"
```

### 9.7 LLM Gateway Debugging

```bash
#!/bin/bash
# /home/guinevere/scripts/test-llm-failover.sh
echo "=== LLM Failover Chain Test ==="
echo "Tier 1: 9Router..."
curl -s -o /dev/null -w "  HTTP %{http_code}\n" "${NINEROUTER_BASE_URL}/models" -H "Authorization: Bearer ${NINEROUTER_API_KEY}"
echo "Tier 2: OpenRouter..."
curl -s -o /dev/null -w "  HTTP %{http_code}\n" "${OPENROUTER_BASE_URL}/models" -H "Authorization: Bearer ${OPENROUTER_API_KEY}"
echo "Tier 3: Ollama..."
systemctl start guinevere-ollama 2>/dev/null || true
sleep 5
curl -s -o /dev/null -w "  HTTP %{http_code}\n" http://127.0.0.1:11434/api/tags
systemctl stop guinevere-ollama 2>/dev/null || true
echo "Tier 4: Graceful degradation (basic Discord commands only)"
echo "=== Test Complete ==="
```

---

## 10. Security Operations

### 10.1 Key Rotation Schedule

| Secret/Key | Frequency | Procedure | Owner |
|---|---|---|---|
| Age encryption key | Annual/compromise | New keypair, update .sops.yaml, re-encrypt | Faiz |
| Discord bot token | Quarterly/compromise | Developer Portal Reset, update SOPS | Guinevere |
| GitHub PAT | Quarterly | Generate new, update SOPS | Guinevere |
| 9Router API key | Per provider | Update SOPS, restart core | Faiz |
| OpenRouter API key | Per provider | Update SOPS, restart core | Faiz |
| PostgreSQL passwords | Quarterly | ALTER USER, update SOPS + PgBouncer | Guinevere |
| Redis password | Quarterly | Update config + SOPS, restart Redis | Guinevere |
| Tasker HMAC | Quarterly/compromise | New secret, update SOPS + Tasker | Faiz |
| Cloudflare R2 keys | Per provider | Update SOPS + rclone | Faiz |
| Grafana password | Quarterly | Grafana UI + SOPS | Faiz |
| Fernet key | Annual | New key, re-encrypt data, update SOPS | Guinevere |

### 10.2 Security Patch Management

```bash
apt update && apt list --upgradable 2>/dev/null | head -20
apt upgrade -y --with-new-pkgs
cat /var/log/unattended-upgrades/unattended-upgrades.log | tail -20
uname -r
```

### 10.3 Vulnerability Scanning

```bash
lynis audit system --no-colors 2>&1 | tail -30
su - guinevere -s /bin/bash -c 'eval "$(pyenv init -)" && cd ~/core && uv run safety check'
# WhatsApp: Neonize (pure Python) -- audited via uv pip audit (no npm)
```

### 10.4 Audit Log Review

```bash
ausearch -k identity_changes --start today | tail -30
ausearch -k sudoers_changes --start this-week
ausearch -k guinevere_core_changes --start today
ausearch -m USER_LOGIN --success no --start today
lastb | head -20
aureport --summary
aureport -au --start this-month
```

### 10.5 Incident Response Quick Reference

| Severity | Response | Escalation | Actions |
|---|---|---|---|
| SEV0 (Total outage) | Immediate | Faiz (phone) | Full DR restore |
| SEV1 (Major) | < 15 min | Discord + Gotify | Root cause, partial restore |
| SEV2 (Minor) | < 1 hour | Discord | Investigate, fix |
| SEV3 (Anomaly) | < 4 hours | Discord log | Log, investigate |
| SEV4 (Cosmetic) | Next sprint | Discord log | Add to backlog |

---

## 11. Scaling Considerations

### 11.1 Vertical Scaling (VPS Upgrade)

1. Snapshot via provider dashboard
2. `systemctl stop guinevere-*`
3. `cd /opt/guinevere-docker && docker compose stop`
4. Upgrade via provider (resize/reboot)
5. Verify: `free -h && nproc && df -h`
6. Update MemoryMax/CPUQuota in units: `systemctl daemon-reload`
7. Update PostgreSQL docker-compose.yml settings
8. Restart everything, verify with health-check.sh

### 11.2 Horizontal Scaling (Future)

| Component | Current | Future |
|---|---|---|
| Application | All on VPS-1 | VPS-1 (core), VPS-2 (scheduler+loops) |
| PostgreSQL | Docker VPS-1 | Dedicated DB server |
| Redis | Docker VPS-1 | Redis sentinel |
| Monitoring | Docker VPS-1 | Dedicated monitoring VPS |

### 11.3 Database Scaling

- Read replicas via streaming replication
- Multi-PgBouncer via SO_REUSEPORT if pool saturation
- TimescaleDB handles time-series partitioning already

---

## 12. Operational Runbooks

### 12.1 Daily Operations Checklist

```bash
#!/bin/bash
# /home/guinevere/scripts/daily-check.sh
echo "=== Daily Check ==="
echo "CPU: $(cat /proc/loadavg | cut -d' ' -f1-3)"
echo "Mem: $(free -h | awk '/Mem:/ {print $3 "/" $2}')"
echo "Disk: $(df -h / | awk 'NR==2 {print $5 " used"}')"
echo "Swap: $(free -h | awk '/Swap:/ {print $3 "/" $2}')"
echo ""
for svc in guinevere-core guinevere-surveillance guinevere-scheduler guinevere-loops guinevere-discord guinevere-whatsapp pgbouncer cloudflared tailscaled; do
  echo "  $svc: $(systemctl is-active $svc 2>/dev/null)"
done
echo ""
docker ps --format "  {{.Names}}: {{.Status}}" 2>/dev/null
echo ""
ERRORS=$(journalctl -u "guinevere-*" --since "24 hours ago" -p err --no-pager 2>/dev/null | grep -c "guinevere" || echo "0")
echo "Errors (24h): $ERRORS"
LATEST=$(ls -t /home/guinevere/data/backups/postgres/*.age 2>/dev/null | head -1)
[ -n "$LATEST" ] && echo "Backup: $(basename $LATEST)" || echo "WARNING: No backups!"
echo "=== Done ==="
```

### 12.2 Weekly Maintenance

| Task | Command | Day |
|---|---|---|
| Disk review | `df -h && du -sh /var/lib/docker/*` | Mon |
| Error logs | `journalctl -u "guinevere-*" --since "7 days ago" -p err` | Mon |
| Backup test | Restore to staging | Wed |
| Audit logs | `aureport --summary --start this-week` | Fri |
| OS updates | `apt list --upgradable` | Fri |
| Tailscale | `tailscale status` | Fri |
| Cost review | Grafana cost dashboard | Fri |

### 12.3 Monthly Security Review

- Lynis audit: `lynis audit system --no-colors`
- Failed logins: `lastb | head -30`
- Sudo usage: `ausearch -m USER_CMD --start this-month`
- CVE check: `uv run safety check && uv pip audit`
- Firewall: `ufw status verbose`
- Tailscale ACLs review
- Rotate due secrets
- CrowdSec: `cscli alerts list --since 30d`
- DR restore test on staging

### 12.4 Quarterly DR Test

```bash
#!/bin/bash
# /home/guinevere/scripts/quarterly-dr-test.sh
echo "=== QUARTERLY DR TEST ==="
echo "Date: $(date)"
echo "Phase 1: Backup accessibility..."
rclone lsf r2:guinevere-backups/postgres/ | sort -r | head -3
echo "Phase 2: Backup decryption..."
LATEST=$(rclone lsf r2:guinevere-backups/postgres/ | sort -r | head -1)
rclone copy "r2:guinevere-backups/postgres/$LATEST" /tmp/dr-test/
age -d -i /etc/sops/age/keys.txt "/tmp/dr-test/$LATEST" | gunzip -t && echo "  OK" || echo "  FAIL"
echo "Phase 3: LLM failover..."
/home/guinevere/scripts/test-llm-failover.sh
echo "DR Test: $(date)" >> /home/guinevere/data/logs/dr-test-results.log
echo "=== Complete ==="
```

### 12.5 Emergency Procedures

**Service Down:** `systemctl restart guinevere-core` / restart all with for loop.

**Disk Full:** `docker system prune -af --volumes` / `journalctl --vacuum-time=7d` / clean old backups.

**OOM:** `dmesg | grep -i oom` / `systemctl stop guinevere-ollama` / add emergency swap: `fallocate -l 4G /swapfile_emergency && chmod 600 /swapfile_emergency && mkswap /swapfile_emergency && swapon /swapfile_emergency`

**Security Incident:** Block IP (`ufw deny from <IP>`) / disable user (`usermod -L <user>`) / rotate secrets / collect evidence (`ausearch --start today > evidence/`) / notify Faiz.

---

## 13. Open Questions & Future Work

### 13.1 Open Questions

| Question | Impact | Resolution | Status |
|---|---|---|---|
| Dedicated monitoring VPS | Observability isolation | ADR + budget | Post-MVP |
| PostgreSQL read replica | Read scaling | Capacity monitoring | Monitor |
| Ollama model updates | Fallback quality | Quarterly review | Track releases |
| Multi-PgBouncer | Pool scaling | Load testing | If saturation |
| Wearable integration | Health surveillance | API readiness | Post-MVP |
| Cloudflare Access for Grafana | Dashboard security | Zero Trust setup | After stable deploy |

### 13.2 Future Work

| Item | Priority | Effort | Dependencies |
|---|---|---|---|
| Ansible provisioning playbook | HIGH | 2-3 days | Stable deploy procedure |
| Grafana dashboards-as-code (5) | HIGH | 1-2 days | Exporters running |
| rclone config for R2 + S3 | HIGH | 2 hours | Storage credentials |
| Sentry integration | MEDIUM | 4 hours | Sentry project |
| Gotify self-hosted | MEDIUM | 2 hours | Docker + Caddy |
| Staging environment | MEDIUM | 1 day | Separate DB + channel |
| Chaos engineering tests | LOW | 2-3 days | Stable production |
| External pentest | LOW | Budget | Annual approval |

---

## Appendix A: Complete Service Port Map

| Service | Port | Protocol | Bind | Purpose |
|---|---|---|---|---|
| guinevere-surveillance | 8000 | HTTP | 127.0.0.1 | FastAPI receiver |
| guinevere-windows-sync | 8001 | WebSocket | 127.0.0.1 | Windows daemon |
| guinevere-core metrics | 8100 | HTTP | 127.0.0.1 | Prometheus |
| guinevere-scheduler metrics | 8101 | HTTP | 127.0.0.1 | Prometheus |
| guinevere-loops metrics | 8102 | HTTP | 127.0.0.1 | Prometheus |
| guinevere-ollama | 11434 | HTTP | 127.0.0.1 | Ollama (Tier 3) |
| PostgreSQL (Docker) | 5432 | TCP | 127.0.0.1 | Database |
| Redis (Docker) | 6379 | TCP | 127.0.0.1 | Cache/Queue |
| PgBouncer | 6432 | TCP | 127.0.0.1 | Pooling |
| Prometheus (Docker) | 9090 | HTTP | 127.0.0.1 | Metrics |
| Grafana (Docker) | 3000 | HTTP | 127.0.0.1 | Dashboard |
| Loki (Docker) | 3100 | HTTP | 127.0.0.1 | Logs |
| Alertmanager | 9093 | HTTP | 127.0.0.1 | Alerts |
| Node Exporter | 9100 | HTTP | 127.0.0.1 | System metrics |
| Redis Exporter | 9121 | HTTP | 127.0.0.1 | Redis metrics |
| PostgreSQL Exporter | 9187 | HTTP | 127.0.0.1 | DB metrics |
| Promtail | 9080 | HTTP | 127.0.0.1 | Log shipping |
| SSH | 2222 | TCP | Tailscale only | Secure shell |
| Tailscale | 41641 | UDP | 0.0.0.0 | WireGuard |

---

## Appendix B: Complete Environment Variables Reference

| Variable | Service | Description |
|---|---|---|
| NINEROUTER_API_KEY | core | 9Router API key |
| NINEROUTER_BASE_URL | core | 9Router base URL |
| OPENROUTER_API_KEY | core | OpenRouter key (Tier 2) |
| OPENROUTER_BASE_URL | core | OpenRouter base URL |
| DISCORD_BOT_TOKEN | core, discord | Bot token |
| DISCORD_APPLICATION_ID | discord | App ID |
| DISCORD_GUILD_ID | discord | Guild ID |
| DISCORD_WEBHOOK_URL | alertmanager | Alert webhook |
| POSTGRES_HOST | all | DB host (127.0.0.1) |
| POSTGRES_PORT | all | DB port (5432) |
| POSTGRES_DB | all | DB name (guinevere) |
| POSTGRES_PASSWORD | core, surv | DB password |
| PGBOUNCER_PASSWORD | pgbouncer | Pool admin pass |
| REDIS_PASSWORD | all | Redis auth |
| GITHUB_PAT | core | GitHub token |
| GITHUB_WEBHOOK_SECRET | core | Webhook secret |
| TASKER_HMAC_SECRET | surveillance | Tasker HMAC |
| WINDOWS_HMAC_SECRET | surveillance | Windows HMAC |
| CLOUDFLARE_R2_ACCESS_KEY | backup | R2 key |
| CLOUDFLARE_R2_SECRET_KEY | backup | R2 secret |
| CLOUDFLARE_R2_ENDPOINT | backup | R2 endpoint |
| CLOUDFLARE_R2_BUCKET | backup | R2 bucket |
| IDCLOUDHOST_S3_ACCESS_KEY | backup | S3 key |
| IDCLOUDHOST_S3_SECRET_KEY | backup | S3 secret |
| IDCLOUDHOST_S3_ENDPOINT | backup | S3 endpoint |
| IDCLOUDHOST_S3_BUCKET | backup | S3 bucket |
| RESEND_API_KEY | core | Email API |
| GMAIL_OAUTH_CLIENT_ID | core | Gmail OAuth |
| GMAIL_OAUTH_CLIENT_SECRET | core | Gmail secret |
| GMAIL_OAUTH_REFRESH_TOKEN | core | Gmail refresh |
| BRAVE_SEARCH_API_KEY | core | Brave Search |
| EXA_API_KEY | core | Exa AI |
| SENTRY_DSN | core | Error tracking |
| GRAFANA_ADMIN_PASSWORD | grafana | Admin pass |
| GOTIFY_TOKEN | core | Push notif |
| FERNET_KEY | core | Encryption key |
| AGE_PUBLIC_KEY | sops | Age public key |
| OLLAMA_HOST | ollama | Bind address |
| OLLAMA_MAX_LOADED_MODELS | ollama | Max models (1) |
| OLLAMA_KEEP_ALIVE | ollama | Keep-alive (5m) |

---

## Appendix C: systemd Unit Files Summary

| Unit | Type | Description |
|---|---|---|
| guinevere-core.service | simple | Main agent (Hermes + Persona) |
| guinevere-surveillance.service | simple | FastAPI receiver (:8000) |
| guinevere-windows-sync.service | simple | WebSocket (:8001) |
| guinevere-loops.service | simple | SDLC loops |
| guinevere-scheduler.service | simple | APScheduler |
| guinevere-discord.service | simple | Discord bot |
| guinevere-whatsapp.service | simple | Neonize WhatsApp service |
| guinevere-ollama.service | simple | Ollama (on-demand) |
| guinevere-selfdeploy.timer | timer | Self-deploy (03:00) |
| guinevere-selfdeploy.service | oneshot | Deploy script |
| guinevere-backup.timer | timer | Backup (02:00) |
| guinevere-backup.service | oneshot | Backup script |
| guinevere-db-vacuum.timer | timer | VACUUM (Sun 04:00) |
| guinevere-db-vacuum.service | oneshot | VACUUM script |
| node_exporter.service | simple | System metrics |
| postgres_exporter.service | simple | DB metrics |
| redis_exporter.service | simple | Redis metrics |
| promtail.service | simple | Log shipping |
| alertmanager.service | simple | Alert routing |
| cloudflared.service | simple | CF Tunnel |
| tailscaled.service | simple | Tailscale VPN |
| pgbouncer.service | simple | Connection pool |

All Guinevere units include: NoNewPrivileges, ProtectSystem=strict, ProtectHome, PrivateTmp, RestrictAddressFamilies, PrivateDevices, SystemCallArchitectures=native, empty CapabilityBoundingSet, MemoryMax, CPUQuota, SOPS EnvironmentFile.

---

## Appendix D: Command Quick-Reference

```bash
# Services
systemctl start/stop/restart/status guinevere-core
journalctl -u guinevere-core -f
systemctl daemon-reload

# Docker
cd /opt/guinevere-docker && docker compose up -d
cd /opt/guinevere-docker && docker compose down
docker logs postgresql --tail 50
docker stats --no-stream

# Secrets
SOPS_AGE_KEY_FILE=/etc/sops/age/keys.txt sops --decrypt secrets/core.env.sops
/home/guinevere/scripts/rotate-secret.sh core KEY "new-value"

# Database
docker exec -it postgresql psql -U postgres -d guinevere
uv run alembic upgrade head

# Monitoring
/home/guinevere/scripts/health-check.sh
/home/guinevere/scripts/daily-check.sh
/home/guinevere/scripts/test-llm-failover.sh

# Backup
/home/guinevere/scripts/backup.sh
/home/guinevere/scripts/restore-db.sh /path/to/backup.age
/home/guinevere/scripts/full-restore.sh

# Network
tailscale status && tailscale ip -4
ufw status verbose
cloudflared tunnel info guinevere
ss -tlnp | grep LISTEN
```

---

## Appendix E: Change Log

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-30 | Guinevere / Hephaestus | Initial deployment guide. Complete VPS provisioning, CIS hardening (15 steps), SOPS + age secrets, all systemd units with hardening, Docker stack, network (Cloudflare Tunnel + Tailscale + UFW), monitoring (Prometheus + Grafana + Loki + Alertmanager), database (Alembic + indexes + vacuum), backup and DR, CI/CD, troubleshooting, security ops, scaling, runbooks, and 5 appendices. All operator Option B directives applied. ADR-028 v3.0 Ollama Tier 3 fully documented. |

---

*Guinevere de Baroque*

*"Mommy sudah design semuanya. Kamu tinggal deploy."*

Deployment Guide v1.0 -- Project Guinevere