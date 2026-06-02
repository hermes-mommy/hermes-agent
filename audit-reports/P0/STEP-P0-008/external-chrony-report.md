# External Research Report: Chrony & Timezone Configuration on Ubuntu 24.04

> **Scope**: Best practices for resolving chrony vs systemd-timesyncd conflict, setting timezone to Asia/Jakarta, and configuring chrony with Indonesian NTP pools on Ubuntu 24.04 shared VPS.
> **Context**: Aizanta autonomous AI system + CrowdSec + fail2ban security monitoring stack.
> **Date**: 2026-05-31
> **Version**: 1.0

---

## Table of Contents

1. [Ubuntu 24.04 Default NTP: systemd-timesyncd vs chrony](#1-ubuntu-2404-default-ntp-systemd-timesyncd-vs-chrony)
2. [Chrony 4.5 Configuration Best Practices](#2-chrony-45-configuration-best-practices)
3. [Timezone Change Safety (Asia/Jakarta)](#3-timezone-change-safety-asiajakarta)
4. [Timezone + Docker](#4-timezone--docker)
5. [Verification Commands](#5-verification-commands)
6. [UFW and NTP Port 123](#6-ufw-and-ntp-port-123)
7. [Rollback Procedures](#7-rollback-procedures)
8. [Known Issues and Gotchas](#8-known-issues-and-gotchas)
9. [References](#9-references)

---

## 1. Ubuntu 24.04 Default NTP: systemd-timesyncd vs chrony

### 1.1 Current Default (Ubuntu 24.04 LTS)

**Ubuntu 24.04 LTS uses `systemd-timesyncd` as the default NTP service.** Chrony becomes the default starting from Ubuntu 25.10 (Questing Quokka), as announced at the Ubuntu Engineering Sprint in May 2025.

| Attribute | Ubuntu 24.04 LTS | Ubuntu 25.10+ |
|---|---|---|
| Default NTP | systemd-timesyncd | chrony |
| Chrony auto-installed | No | Yes (replaces timesyncd) |
| NTS support | No (timesyncd lacks it) | Yes (chrony, enabled by default) |
| Package priority | systemd-timesyncd: important | chrony: important, timesyncd: optional |

**Source**: [Ubuntu Server Documentation — About time synchronisation](https://ubuntu.com/server/docs/_sources/explanation/networking/about-time-synchronisation.md.txt):
> "Since Ubuntu 25.10 `chrony` is used to synchronize time by default."
> "Chrony is replacing `systemd-timesyncd` as the default in Ubuntu 25.10 and `ntpdate`/`ntpd`, which was the default before Ubuntu 18.04 LTS."

### 1.2 Should Both Run Simultaneously?

**Absolutely not.** Running both chrony and systemd-timesyncd simultaneously is a blocking conflict. Both services attempt to control and adjust the system clock, leading to:

- Conflicting time adjustments
- Unstable timekeeping with oscillating offsets
- Potential clock jumps that break security monitoring, log correlation, and database timestamps
- The `time-daemon` virtual package conflict (chrony and systemd-timesyncd both provide `time-daemon`)

**Source**: [DigitalOcean — Time Synchronization Ubuntu](https://www.digitalocean.com/community/tutorials/how-to-set-up-time-synchronization-on-ubuntu-20-04):
> "Only one time synchronization service should run at a time, as running multiple services like `timesyncd`, `chrony`, or `ntpd` simultaneously can lead to conflicts and inconsistent system time."

**Source**: [chrony FAQ](https://chrony-project.org/faq):
> "`systemd-timesyncd` is a very simple NTP client included in the `systemd` suite. It lacks almost all features of `chrony` and other advanced client implementations."

### 1.3 Comparison Table

| Feature | systemd-timesyncd | chrony 4.5 |
|---|---|---|
| Accuracy | ±100ms typical | ±1ms typical |
| Multiple server polling | No (single server) | Yes (falseticker detection) |
| Network instability handling | Limited | Excellent |
| Startup synchronization | Slower | Fast (with `iburst`) |
| Drift correction | Basic | Advanced and adaptive |
| Resource usage | ~2MB | ~4MB |
| NTP server capability | No | Yes |
| NTS (Network Time Security) | No | Yes (v4.5+) |
| VM/cloud support | Basic | Excellent |
| Socket activation (zero-downtime restart) | N/A | Yes (v4.5+) |
| Hardware timestamping/PPS/GPS | No | Yes |

### 1.4 Safe Transition: Disable systemd-timesyncd → Enable chrony

On Ubuntu 24.04, **installing chrony does NOT automatically disable systemd-timesyncd** (unlike Ubuntu 25.10+ where it does). You must do it manually:

```bash
# Step 1: Stop and disable systemd-timesyncd
sudo systemctl stop systemd-timesyncd
sudo systemctl disable systemd-timesyncd
sudo systemctl mask systemd-timesyncd  # Prevent accidental re-enable

# Step 2: Install chrony
sudo apt update && sudo apt install chrony -y

# Step 3: Enable and start chrony
sudo systemctl enable chrony
sudo systemctl start chrony

# Step 4: Verify
timedatectl status
systemctl status chrony
```

**Critical note on Ubuntu 24.04**: The `apt install chrony` on 24.04 does NOT auto-mask timesyncd. On 25.10+, `apt-mark auto chrony && apt install systemd-timesyncd` is the rollback pattern, and `apt-mark auto systemd-timesyncd && apt install chrony` is the forward pattern. On 24.04, you manage both services manually.

**Source**: [DigitalOcean guide](https://www.digitalocean.com/community/tutorials/how-to-set-up-time-synchronization-on-ubuntu-20-04):
> "Before installing `chrony`, you need to disable the default `systemd-timesyncd` service to prevent conflicts between time synchronization services."

### 1.5 Why chrony for Aizanta/Security Monitoring?

For a VPS running Aizanta security monitoring with CrowdSec and fail2ban:

1. **Better accuracy** (±1ms vs ±100ms) — critical for security event correlation
2. **Falseticker detection** — chrony can detect and exclude misbehaving NTP servers
3. **iburst** — faster initial sync after boot/network recovery
4. **Adaptive drift correction** — maintains accuracy across reboots
5. **VM-friendly** — VPS environments often have clock drift; chrony handles this better
6. **NTS support** — encrypted NTP (though not all Indonesian pools support it yet)

---

## 2. Chrony 4.5 Configuration Best Practices

### 2.1 Recommended `/etc/chrony/chrony.conf` for Indonesian VPS

```conf
# Chrony configuration for Indonesian VPS
# Optimized for: Asia/Jakarta timezone, shared VPS, security monitoring

# Indonesian NTP pools (id.pool.ntp.org)
# ~30 active servers in Indonesian zone
pool id.pool.ntp.org iburst maxsources 4
pool 0.id.pool.ntp.org iburst maxsources 4
pool 1.id.pool.ntp.org iburst maxsources 4
pool 2.id.pool.ntp.org iburst maxsources 4
pool 3.id.pool.ntp.org iburst maxsources 4

# Fallback: Global pools (lower latency if Indonesian pool is slow)
pool pool.ntp.org iburst maxsources 2

# Fallback: Ubuntu pools (always available)
pool ntp.ubuntu.com iburst maxsources 2

# Record clock drift rate for persistence across reboots
driftfile /var/lib/chrony/drift

# Allow clock to be stepped if offset > 1 second in first 3 updates
# Critical for initial boot sync without disrupting running services
makestep 1.0 3

# Enable kernel synchronization of real-time clock (RTC)
# Keeps hardware clock in sync without userspace overhead
rtcsync

# Log directory for tracking/troubleshooting
logdir /var/log/chrony

# Log tracking measurements and statistics
log tracking measurements statistics

# Optional: Stratum 10 fallback if all sources unreachable
# Prevents "unsynchronized" status during brief network outages
local stratum 10

# Source directory for additional configuration
# Ubuntu places pool configs here
sourcedir /etc/chrony/sources.d

# Additional config directory
confdir /etc/chrony/conf.d

# Restrict chronyc access to localhost only (security)
bindcmdaddress 127.0.0.1
bindcmdaddress ::1

# Do not serve NTP to other hosts (client-only)
# Omit 'allow' directives for client-only operation
```

### 2.2 Directive Explanations

| Directive | Purpose | Why Important |
|---|---|---|
| `pool <server> iburst` | Dynamic server pool with fast initial burst | `iburst` sends 4 packets in 2 seconds on startup instead of waiting for normal poll interval. Faster sync after boot. |
| `maxsources 4` | Max servers to use from each pool | Pool DNS returns multiple IPs; use up to 4 for redundancy without excess traffic |
| `driftfile` | Records system clock drift rate | Persists learned drift across reboots. Prevents repeating the learning phase. Path: `/var/lib/chrony/drift` on Ubuntu |
| `makestep 1.0 3` | Step clock if offset > 1s in first 3 updates | Allows initial correction without permanently allowing steps. After 3 updates, chrony only slews (smooth adjustment). |
| `rtcsync` | Sync hardware RTC with system clock | Updates RTC every 11 minutes via kernel. Essential for accurate time after power loss. |
| `logdir` | Log directory path | `/var/log/chrony` on Ubuntu. Used by `chronyc` for tracking data. |
| `log tracking measurements statistics` | Enable detailed logging | Helps diagnose sync issues. Minimal disk overhead. |
| `local stratum 10` | Fallback when all sources unreachable | Prevents "unsynchronized" status. Stratum 10 is low-priority — won't be chosen over real sources. |
| `sourcedir` | Directory for additional source configs | Ubuntu places pool definitions in `/etc/chrony/sources.d/` |
| `bindcmdaddress` | Restrict chronyc command socket | Security: only localhost can query chrony status |

### 2.3 Indonesian NTP Pool Details

| Pool Address | Description | Active Servers |
|---|---|---|
| `id.pool.ntp.org` | Primary Indonesian pool | ~30 |
| `0.id.pool.ntp.org` | Sub-pool 0 | Rotating subset |
| `1.id.pool.ntp.org` | Sub-pool 1 | Rotating subset |
| `2.id.pool.ntp.org` | Sub-pool 2 (also provides IPv6) | Rotating subset |
| `3.id.pool.ntp.org` | Sub-pool 3 | Rotating subset |

**Notable Indonesian NTP servers in the pool** (from pool.ntp.org zone listing):
- Maxindo NTP servers (Jakarta) — e.g., `1.ntp.maxindo.net.id`, `2.ntp.maxindo.net.id`
- Servers hosted by Indonesian ISPs and universities

**Source**: [pool.ntp.org — Indonesia zone](https://www.ntppool.org/en/zone/id):
> "To use this specific pool zone, add the following to your ntp.conf file:
> `server 0.id.pool.ntp.org`, `server 1.id.pool.ntp.org`, `server 2.id.pool.ntp.org`, `server 3.id.pool.ntp.org`"

**Note on IPv6**: Only zone names prefixed with `2` (e.g., `2.id.pool.ntp.org`) provide IPv6 addresses in addition to IPv4. The other prefixes (0, 1, 3, or no prefix) return IPv4 addresses only.

### 2.4 Configuration File Structure on Ubuntu 24.04

```
/etc/chrony/
├── chrony.conf                      # Main config (driftfile, makestep, rtcsync, etc.)
├── conf.d/                          # Additional config drop-ins
│   └── ubuntu-nts.conf             # NTS certificate config (Ubuntu 25.10+)
└── sources.d/                       # NTP source definitions
    └── ubuntu-ntp-pools.sources    # Default Ubuntu pool (25.10+)
```

**For Ubuntu 24.04**: The `sources.d/` and `conf.d/` directories may not exist by default (they were introduced for 25.10+). On 24.04, all configuration goes in `/etc/chrony/chrony.conf` or in drop-in files you create yourself in `/etc/chrony/conf.d/`.

### 2.5 NTS (Network Time Security) Consideration

NTS is chrony's encrypted NTP authentication mechanism. On Ubuntu 25.10+, it's enabled by default with Ubuntu NTS pools. On Ubuntu 24.04, you can enable it manually, but **Indonesian NTP pools do NOT support NTS**. NTS requires:
- Port 4460/TCP for NTS Key Exchange (NTS-KE)
- Port 123/UDP for the actual NTP traffic
- Server-side NTS support

For Indonesian pools, use plain NTP (without `nts` option). If you want NTS for the Ubuntu fallback pools:

```conf
# NTS-enabled Ubuntu pools (requires port 4460/TCP outbound)
pool 1.ntp.ubuntu.com iburst maxsources 1 nts prefer
pool 2.ntp.ubuntu.com iburst maxsources 1 nts prefer
```

---

## 3. Timezone Change Safety (Asia/Jakarta)

### 3.1 How `timedatectl set-timezone` Works

```bash
sudo timedatectl set-timezone Asia/Jakarta
```

When this command executes, three things happen atomically:

1. **`/etc/localtime`** symlink is updated to point to `/usr/share/zoneinfo/Asia/Jakarta`
2. **`/etc/timezone`** file is updated with the text `Asia/Jakarta` (Debian/Ubuntu specific; deprecated in newer systemd but still updated)
3. **`systemd-timedated`** broadcasts the change via D-Bus to all active systemd units

**No reboot is required.** The system clock continues ticking; only the display offset changes (UTC+7 instead of UTC+0).

### 3.2 Impact on Running Services

| Service | Impact | Restart Required? | Notes |
|---|---|---|---|
| **systemd (timers, services)** | Picks up new timezone automatically via D-Bus | **No** | systemd-timedated broadcasts to all units |
| **Docker Engine** | Engine uses host clock (epoch seconds unchanged); containers may show old timezone | **Containers: Yes** (see §4) | Docker daemon itself doesn't need restart |
| **PostgreSQL** | Uses its own tzdata; `show timezone` will show old value until restart | **Yes** | `timezone` in postgresql.conf; restart needed to pick up `/etc/localtime` change |
| **Redis** | Timezone-agnostic (stores Unix timestamps); `INFO server` shows host time | **No** | Redis uses `gettimeofday()` which reads host clock |
| **fail2ban** | Caches timezone at startup; will log in old timezone until restart | **Yes** | Known bug: DST/timezone changes cause timestamp mismatch warnings |
| **CrowdSec** | Runs in UTC by default; timezone change in host doesn't affect it | **Restart if you want TZ change** | Set `TZ` in systemd override for local timezone |
| **rsyslog/syslog** | Caches timezone at startup | **Yes** | Must restart to pick up new timezone in log timestamps |
| **cron** | Caches timezone at startup | **Yes** | Cron jobs may fire at wrong times until restart |
| **Nginx/Apache** | Log timestamps reflect new timezone on next log entry | **Reload recommended** | Access/error logs use `strftime()` which reads `/etc/localtime` |

### 3.3 Recommended Service Restart Sequence After Timezone Change

```bash
# Step 1: Set timezone
sudo timedatectl set-timezone Asia/Jakarta

# Step 2: Restart services that cache timezone (in dependency order)
sudo systemctl restart rsyslog           # Logs first
sudo systemctl restart cron              # Cron jobs
sudo systemctl restart fail2ban          # Security monitoring
sudo systemctl restart crowdsec          # Security monitoring (if TZ changed)
sudo systemctl restart postgresql        # Database
# Docker containers: see §4

# Step 3: Verify
date
timedatectl status
sudo systemctl list-timers               # Check cron-like timers use new timezone
```

### 3.4 Why Restart is Needed for Some Services

The key insight: `timedatectl set-timezone` updates `/etc/localtime` (a symlink). Services that read `/etc/localtime` **at startup** and cache the result need a restart. Services that call `localtime_r()` or `strftime()` on every log entry will pick up the change automatically because these functions read `/etc/localtime` on each call.

- **Automatic pickup**: services that call `localtime_r()` per-event (most modern C/Go/Rust apps)
- **Needs restart**: services that cache timezone at startup (Java/JVM apps, PostgreSQL, fail2ban, rsyslog, cron)

**Source**: [idroot — Setting Up Timezone Ubuntu](https://idroot.us/setting-up-timezone-ubuntu-26-04/):
> "systemd-timedated broadcasts the change to all active systemd units via D-Bus, so running services pick up the new timezone without restarting. No reboot needed."

**Source**: [StackOverflow — Should I reboot after timedatectl](https://askubuntu.com/questions/1145565/should-i-reboot-after-set-new-timezone-using-timedatectl):
> "Yes. You will need to restart the cron and rsyslog services on your system. They obtain their timezones when they start up, and don't detect overall system timezone changes."

---

## 4. Timezone + Docker

### 4.1 Core Problem

**Docker containers do NOT inherit the host's timezone.** Most base images (Alpine, Ubuntu, Debian) default to UTC regardless of the host's timezone setting. The container reads time from the host kernel (epoch seconds are always identical), but the **displayed local time** depends on the container's own timezone configuration.

**Critical understanding**: Epoch seconds (`date +%s`) will ALWAYS match between host and containers. The "drift" is only in how that epoch is converted to human-readable time.

### 4.2 Options for Handling Docker Timezone

#### Option A: Keep Containers in UTC (Recommended for Production)

Industry best practice: run everything in UTC, convert at the display layer.

```yaml
# docker-compose.yml
services:
  app:
    image: myapp:latest
    environment:
      - TZ=UTC
  postgres:
    image: postgres:15
    environment:
      - TZ=UTC
      - PGTZ=UTC
```

**Pros**: No DST bugs, trivial log correlation across services, standard for distributed systems.
**Cons**: Application logs won't match WIB (UTC+7) in syslog, may confuse human operators.

#### Option B: Set TZ Environment Variable in Containers

```yaml
# docker-compose.yml
services:
  app:
    image: myapp:latest
    environment:
      - TZ=Asia/Jakarta
  postgres:
    image: postgres:15
    environment:
      - TZ=Asia/Jakarta
      - PGTZ=Asia/Jakarta
```

**Requires**: `tzdata` package installed in the container image. Minimal images may lack it.

#### Option C: Bind-mount Host's /etc/localtime

```yaml
# docker-compose.yml
services:
  app:
    image: myapp:latest
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /etc/timezone:/etc/timezone:ro    # Optional, Debian/Ubuntu only
    environment:
      - TZ=Asia/Jakarta
```

**Pros**: Container automatically tracks host timezone changes.
**Cons**: On Ubuntu 24.04, `/etc/localtime` may be a regular file instead of symlink when bind-mounted, causing some Python libraries (e.g., `tzlocal`) to fail with `ZoneInfoNotFoundError`. Mounting `/usr/share/zoneinfo` directory is more robust.

#### Option D: Full Mount (Most Robust)

```yaml
# docker-compose.yml
services:
  app:
    image: myapp:latest
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /usr/share/zoneinfo:/usr/share/zoneinfo:ro
    environment:
      - TZ=Asia/Jakarta
```

### 4.3 Recommendation for Guinevere

**For initial deployment, keep containers in UTC and convert at display layer.** This is the safest approach because:

1. No timezone-related bugs in application logic
2. Log correlation between host syslog (WIB) and container logs (UTC) is a fixed +7h offset
3. PostgreSQL stores `timestamptz` in UTC internally regardless of display timezone
4. Redis is timezone-agnostic (Unix timestamps)
5. Can always switch to WIB per-container later via `TZ` env var

**Later**: If you want container logs in WIB, add `TZ=Asia/Jakarta` to docker-compose.yml and recreate containers.

### 4.4 Docker Time Namespace

Docker supports time namespaces (`CLONE_NEWTIME`) since kernel 5.6+, but this is for **virtualized clock offsets** (making a container think it's in a different time), not timezone display. Not relevant for timezone configuration. The container always shares the host's monotonic and wall clocks.

---

## 5. Verification Commands

### 5.1 Timezone Verification

```bash
# Check current timezone
timedatectl status

# Expected output fields:
#   Time zone: Asia/Jakarta (WIB, +0700)
#   System clock synchronized: yes
#   NTP service: active

# Verify /etc/localtime symlink
ls -la /etc/localtime
# Expected: /etc/localtime -> /usr/share/zoneinfo/Asia/Jakarta

# Verify /etc/timezone content
cat /etc/timezone
# Expected: Asia/Jakarta

# Verify date output
date
# Expected: Sun May 31 2026 ... WIB (or similar, UTC+7)
```

### 5.2 Chrony Verification

```bash
# Check chrony service status
systemctl status chrony

# Check chrony tracking (system clock accuracy)
chronyc tracking

# Key output fields:
#   Reference ID    : A9FEA97B (some NTP server IP)
#   Stratum         : 2 or 3 (lower = closer to atomic clock)
#   Ref time        : [current time]
#   System time     : [offset, should be < 1ms]
#   Last offset     : [last correction]
#   RMS offset      : [average offset, should be < 10ms]
#   Frequency       : [drift rate in ppm]
#   Leap status     : Normal (not Insert/Delete)

# Check NTP sources (which servers are being used)
chronyc sources

# Expected: lines starting with ^* = selected source
#   ^* = currently selected (best) source
#   ^+ = acceptable source
#   ^- = not selected
#   ^? = unreachable

# Check source statistics
chronyc sourcestats

# Force immediate sync check (one-shot, no time change)
chronyd -Q 'pool id.pool.ntp.org iburst'

# Check if chrony is the active time source
timedatectl show-timesync
# Or on newer systemd:
timedatectl timesync-status
```

### 5.3 Service-Specific Verification

```bash
# PostgreSQL timezone
sudo -u postgres psql -c "SHOW timezone;"
# Expected after restart: Asia/Jakarta (or whatever postgresql.conf specifies)

# Docker container time
docker exec <container_name> date
# Compare with host: date

# fail2ban status
sudo fail2ban-client status
# Check that jails are active and log timestamps look correct

# CrowdSec status
sudo cscli metrics
# Check that log parsing is working with current timestamps

# Systemd timers (cron-equivalents)
systemctl list-timers --all
# Verify Next column shows WIB times

# rsyslog timestamps
tail -5 /var/log/syslog
# Verify timestamps are in WIB
```

### 5.4 Alternative to `ntpdate -q`

`ntpdate` is deprecated on Ubuntu 24.04. Use chrony's built-in check instead:

```bash
# One-shot time check (does NOT set the clock)
chronyd -Q 'pool id.pool.ntp.org iburst'

# One-shot sync (sets the clock and exits)
chronyd -q 'pool id.pool.ntp.org iburst'
```

---

## 6. UFW and NTP Port 123

### 6.1 Your Current UFW Configuration

```
Default: deny (incoming), allow (outgoing), disabled (routed)
```

### 6.2 Do You Need an Explicit UFW Rule for NTP Client?

**Short answer: With "deny incoming, allow outgoing" defaults, NO explicit rule is needed for chrony as an NTP client.**

Here's why:

1. **chrony as a client** sends outbound UDP packets to remote port 123 (NTP servers)
2. The **outgoing** default policy is "allow", so these packets go through
3. **UFW uses iptables/nftables with connection tracking** (stateful firewall)
4. The return UDP packets from NTP servers are classified as `ESTABLISHED,RELATED` by conntrack
5. UFW's `before.rules` includes: `-A ufw-before-input -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT`
6. Therefore, the response packets from NTP servers are automatically allowed

### 6.3 When You WOULD Need an Explicit Rule

| Scenario | Rule Needed |
|---|---|
| Outgoing default is `deny` | Yes: `sudo ufw allow out 123/udp` |
| Acting as NTP server (allowing inbound sync requests) | Yes: `sudo ufw allow 123/udp` |
| Using NTS (Network Time Security) | Yes: `sudo ufw allow out 4460/tcp` (for NTS-KE) |
| Stateless firewall (no conntrack) | Yes: explicit inbound rule needed for UDP responses |

### 6.4 Recommendation

With your current UFW defaults (`deny incoming, allow outgoing`), chrony will work without any additional firewall rules. The outbound NTP traffic is allowed by the outgoing policy, and return traffic is handled by connection tracking.

**However**, for explicitness and documentation, you may add:

```bash
# Optional: explicit allow for clarity (not technically required)
sudo ufw allow out 123/udp comment 'NTP client - chrony'

# If you later enable NTS:
# sudo ufw allow out 4460/tcp comment 'NTS Key Exchange for chrony'
```

### 6.5 Verification

```bash
# Check UFW rules
sudo ufw status verbose

# Verify NTP connectivity
chronyc sources
# If sources show ^* or ^+, connectivity is working
# If sources show ^? (unreachable), check firewall

# Packet-level verification
sudo tcpdump -i eth0 -n udp port 123
# Should show outbound NTP requests and inbound responses
```

---

## 7. Rollback Procedures

### 7.1 Full Rollback: Revert to systemd-timesyncd + UTC

```bash
# Step 1: Stop chrony
sudo systemctl stop chrony
sudo systemctl disable chrony

# Step 2: Re-enable systemd-timesyncd
sudo systemctl unmask systemd-timesyncd
sudo systemctl enable systemd-timesyncd
sudo systemctl start systemd-timesyncd

# Step 3: Revert timezone to UTC
sudo timedatectl set-timezone Etc/UTC

# Step 4: Restart affected services
sudo systemctl restart rsyslog cron fail2ban postgresql

# Step 5: Verify
timedatectl status
date
chronyc tracking  # Should fail or show no sources
```

### 7.2 Partial Rollback: Keep chrony, Revert Timezone Only

```bash
# Revert timezone to UTC
sudo timedatectl set-timezone Etc/UTC

# Restart affected services
sudo systemctl restart rsyslog cron fail2ban crowdsec postgresql

# Verify
timedatectl status
date
```

### 7.3 Partial Rollback: Keep Timezone, Switch NTP Source

```bash
# If Indonesian pools are unreliable, switch to Ubuntu pools
sudo nano /etc/chrony/chrony.conf
# Comment out id.pool.ntp.org lines
# Uncomment/add Ubuntu pools:
# pool ntp.ubuntu.com iburst maxsources 4

sudo systemctl restart chrony

# Verify
chronyc sources
chronyc tracking
```

### 7.4 Emergency Rollback Script

```bash
#!/bin/bash
# emergency-rollback-ntp-tz.sh
# Full rollback to pre-change state

set -euo pipefail

echo "=== Rolling back NTP and timezone changes ==="

# Stop chrony
systemctl stop chrony 2>/dev/null || true
systemctl disable chrony 2>/dev/null || true

# Re-enable systemd-timesyncd
systemctl unmask systemd-timesyncd 2>/dev/null || true
systemctl enable systemd-timesyncd
systemctl start systemd-timesyncd

# Revert timezone
timedatectl set-timezone Etc/UTC

# Restart services
systemctl restart rsyslog cron fail2ban crowdsec postgresql 2>/dev/null || true

echo "=== Rollback complete ==="
timedatectl status
```

---

## 8. Known Issues and Gotchas

### 8.1 Timezone Change Mid-Session

**Issue**: Changing timezone while services are running causes some services to log in the old timezone while others use the new timezone.

**Impact**:
- Log correlation becomes unreliable during the transition window
- fail2ban may misinterpret timestamps and miss or incorrectly ban IPs
- CrowdSec's time-machine mode may misparse log timestamps

**Mitigation**: Execute the full service restart sequence (§3.3) immediately after timezone change. The window of inconsistency is the time between `timedatectl set-timezone` and the last service restart.

### 8.2 Leap Seconds

**Issue**: Leap seconds can cause clock jumps or stalls in systems not handling them properly.

**Chrony behavior**:
- By default, chrony performs a **smooth slew** for leap seconds (spreads the 1-second correction over ~2000 seconds)
- This is configured via `leapsecmode slew` (default) or `leapsecmode step`
- The `leapsectz` directive can be used to specify a timezone file for leap second data

**For Aizanta/CrowdSec/fail2ban**: Leap seconds are transparently handled by chrony's smooth slew. No service disruption expected. The 1-second correction is spread over ~33 minutes, so per-second timestamps are virtually unaffected.

**Configuration** (if explicit handling is desired):
```conf
# In chrony.conf — smooth slew (default, recommended)
leapsecmode slew

# Or step (immediate 1s correction — NOT recommended for security monitoring)
# leapsecmode step
```

### 8.3 Docker Time Namespace

**Issue**: Docker's `CLONE_NEWTIME` time namespace (kernel 5.6+) allows containers to have virtualized clocks, but this is NOT related to timezone display.

**Impact on your setup**: None. Docker time namespaces are for testing/debugging scenarios where you need a container to think it's a different point in time. Your containers will always share the host's wall clock (epoch seconds).

**Gotcha**: Don't confuse "time namespace" with "timezone configuration". They are completely independent concepts.

### 8.4 chrony vs systemd-timesyncd Socket/Port Conflict

**Issue**: If both chrony and systemd-timesyncd are enabled, they may both try to bind to UDP port 123 or conflict on clock adjustments.

**Symptoms**:
- `chronyd` fails to start with "cannot bind to port 123"
- Time oscillates between two values
- `timedatectl` shows "NTP service: n/a" or conflicting information

**Resolution**:
```bash
# Ensure only one is active
sudo systemctl list-unit-files | grep -E 'timesyncd|chrony|ntp'
# Disable all except the one you want
sudo systemctl mask systemd-timesyncd ntp ntpd
sudo systemctl enable chrony
sudo systemctl start chrony
```

### 8.5 /etc/timezone Deprecation

**Issue**: The `/etc/timezone` file is Debian-specific and is being deprecated in newer systemd versions. On systemd 252.6+, `timedatectl set-timezone` may not update it.

**Current state on Ubuntu 24.04** (systemd 255.4): `/etc/timezone` IS still updated by `timedatectl set-timezone`. This is maintained by Debian/Ubuntu patches.

**Impact**: Some applications check `/etc/timezone` instead of `/etc/localtime`. After timezone change, verify both files are consistent:

```bash
cat /etc/timezone          # Should say: Asia/Jakarta
ls -la /etc/localtime      # Should point to: /usr/share/zoneinfo/Asia/Jakarta
```

### 8.6 PostgreSQL and /etc/localtime

**Issue**: PostgreSQL has a peculiar behavior with `Etc/UTC` timezone setting. If `TimeZone = 'Etc/UTC'` is set in `postgresql.conf` AND `/etc/localtime` is mounted/changed to a different timezone, PostgreSQL may silently use the system timezone instead of UTC.

**Source**: [DBA StackExchange](https://dba.stackexchange.com/questions/338259/relationship-between-etc-localtime-and-etc-utc-in-postgresql):
> "Despite the fact that the query `show timezone;` showed the time zone `Etc/UTC`, in fact all requests related to the time output worked as if the time zone from `/etc/localtime` was really there."

**Mitigation**: If you want PostgreSQL in UTC regardless of host timezone, use `TimeZone = 'UTC'` or `TimeZone = 'GMT'` (not `Etc/UTC`), or set `PGTZ=UTC` environment variable.

### 8.7 fail2ban Timezone Sensitivity

**Issue**: fail2ban caches timezone information at startup. After a timezone change, it may log "Detected a log entry Xh before/after the current time" warnings and incorrectly calculate ban expiration times.

**Source**: [Debian Bug #1084958](https://bugs-devel.debian.org/cgi-bin/bugreport.cgi?bug=1084958):
> "After changing to Daylight Savings time, fail2ban reports timestamp error... Restarting the fail2ban service fixes the issue."

**Mitigation**: Always restart fail2ban after timezone change:
```bash
sudo systemctl restart fail2ban
```

fail2ban v0.11.2+ includes an `inOperation` mode that detects timezone mismatches and treats deviating timestamps as "now" to prevent bypass. However, this is a safety net, not a fix — restart is still required.

### 8.8 CrowdSec Timezone Behavior

**Issue**: CrowdSec runs in UTC by default. In "live" mode, log timestamps are ignored (only the current runtime datetime matters). In "time-machine" mode, timestamps are parsed and converted to UTC.

**Key points**:
- **Live mode**: Timezone change on host does NOT affect CrowdSec's detection (it uses its own UTC clock)
- **Time-machine mode**: Parses timestamps from logs, handles timezone offsets (+0700 etc.)
- **Ubuntu 24.04 syslog format**: Changed from BSD format (`Jan 13 22:04:36`) to RFC3339/ISO8601 (`2026-01-13T22:04:36.123456+07:00`). CrowdSec parsers updated to handle this, but requires parser update and CrowdSec restart.

**If you want CrowdSec to display alerts in WIB**: Set `TZ` environment variable in the systemd override:

```bash
sudo systemctl edit crowdsec
# Add:
# [Service]
# Environment=TZ=Asia/Jakarta

sudo systemctl restart crowdsec
```

### 8.9 Chrony 4.5 on Ubuntu 24.04 — AppArmor Profile

**Known issue**: chrony 4.5-1ubuntu4 on Ubuntu 24.04 (Noble) had a bug where the AppArmor profile prevented `timemaster` from accessing the chrony socket. Fixed in the same package version.

**Source**: [Ubuntu Changelog](https://lists.ubuntu.com/archives/noble-changes/2024-April/034891.html):
> "Fix failure to start timemaster due to lack of rw permissions on chrony socket. (LP: #2032805)"

### 8.10 Socket Activation (chrony 4.5+)

chrony 4.5 introduced systemd socket activation for zero-downtime restarts. The systemd service manager pre-binds NTP server sockets and passes them to chronyd. This is useful if you're running chrony as an NTP server, but **not relevant for client-only operation**.

---

## 9. References

### 9.1 Official Ubuntu Documentation

| Resource | URL |
|---|---|
| Ubuntu Server — About time synchronisation | https://ubuntu.com/server/docs/_sources/explanation/networking/about-time-synchronisation.md.txt |
| Ubuntu Server — Chrony client configuration | https://ubuntu.com/server/docs/_sources/how-to/networking/chrony-client.md.txt |
| Ubuntu Server — timedatectl and timesyncd | https://ubuntu.com/server/docs/how-to/networking/timedatectl-and-timesyncd/ |
| Ubuntu Server — Serving NTP with chrony | https://ubuntu.com/server/docs/how-to/networking/serve-ntp-with-chrony |
| Ubuntu Manpage — chrony.conf(5) | https://manpages.ubuntu.com/manpages/stonking/man5/chrony.conf.5.html |
| Ubuntu Manpage — chronyd(8) | https://manpages.ubuntu.com/manpages/resolute/man8/chronyd.8.html |

### 9.2 systemd Documentation

| Resource | URL |
|---|---|
| timedatectl(1) manpage | https://www.freedesktop.org/software/systemd/man/254/timedatectl.html |
| systemd-timedated.service(8) | https://www.freedesktop.org/software/systemd/man/254/systemd-timedated.service.html |
| localtime(5) manpage | https://www.freedesktop.org/software/systemd/man/254/localtime.html |

### 9.3 Chrony Project

| Resource | URL |
|---|---|
| chrony FAQ | https://chrony-project.org/faq |
| chrony.conf(5) upstream documentation | https://chrony-project.org/doc/chrony.conf.html |
| chrony GitLab repository | https://gitlab.com/chrony/chrony |
| chrony installation guide | https://gitlab.com/chrony/chrony/-/blob/master/doc/installation.adoc |

### 9.4 NTP Pool Project

| Resource | URL |
|---|---|
| Indonesia NTP Pool zone | https://www.ntppool.org/en/zone/id |
| NTP Pool setup guide | https://api.ntppool.org/use.html |
| NTP Pool — Indonesia (Bahasa) | https://api.ntppool.org/id/use.html |

### 9.5 Community Discussions & Guides

| Resource | URL |
|---|---|
| DigitalOcean — Time Synchronization Ubuntu | https://www.digitalocean.com/community/tutorials/how-to-set-up-time-synchronization-on-ubuntu-20-04 |
| VPS.DO — Time Synchronization on Ubuntu Server | https://vps.do/how-to-configure-time-synchronization-on-ubuntu-server/ |
| MangoHost — Time Synchronization Ubuntu 24 | https://mangohost.net/blog/how-to-set-up-time-synchronization-on-ubuntu-24/ |
| idroot — Setting Up Timezone Ubuntu | https://idroot.us/setting-up-timezone-ubuntu-26-04/ |
| DotLinux — Configuring NTP on Ubuntu 24.04 | https://www.dotlinux.net/blog/configuring-ntp-on-ubuntu-24-04/ |
| Ubuntu Devel — PSA: chrony by default (25.10+) | https://lists.ubuntu.com/archives/ubuntu-devel/2025-May/043355.html |

### 9.6 Docker & Timezone

| Resource | URL |
|---|---|
| Baeldung — Docker Container Timezone | https://www.baeldung.com/ops/docker-set-timezone |
| cr0x.net — Docker Time Zone Drift | https://cr0x.net/en/docker-container-timezone-drift-fix/ |
| OneUptime — Docker Timezone Mismatch Fix | https://oneuptime.com/blog/post/2026-02-08-how-to-fix-docker-timezone-mismatch-between-host-and-container/view |
| StackOverflow — Docker container timezone | https://stackoverflow.com/questions/63180991 |
| ServerFault — Docker container time & timezone | https://serverfault.com/questions/683605 |

### 9.7 Security Monitoring & Timezone

| Resource | URL |
|---|---|
| CrowdSec Discourse — Log format and timezone | https://discourse.crowdsec.net/t/i-want-to-verify-how-crowdsec-handles-log-format/2450 |
| Debian Bug #1084958 — fail2ban DST timestamp error | https://bugs-devel.debian.org/cgi-bin/bugreport.cgi?bug=1084958 |
| fail2ban PR #2814 — Extended datepattern handling | https://github.com/fail2ban/fail2ban/pull/2814 |
| CrowdSec Issue #4199 — Syslog parser RFC3339 | https://github.com/crowdsecurity/crowdsec/issues/4199 |
| DBA StackExchange — PostgreSQL /etc/localtime | https://dba.stackexchange.com/questions/338259 |

---

## Appendix A: Quick Reference — Execution Sequence

```bash
# ═══════════════════════════════════════════════════════
# PHASE 1: Consolidate NTP to chrony only
# ═══════════════════════════════════════════════════════

# Stop and mask systemd-timesyncd
sudo systemctl stop systemd-timesyncd
sudo systemctl disable systemd-timesyncd
sudo systemctl mask systemd-timesyncd

# Install chrony
sudo apt update && sudo apt install chrony -y

# Configure chrony (see §2.1 for full config)
sudo cp /etc/chrony/chrony.conf /etc/chrony/chrony.conf.bak
sudo nano /etc/chrony/chrony.conf
# Add Indonesian pools, makestep, rtcsync, driftfile, etc.

# Start chrony
sudo systemctl enable chrony
sudo systemctl start chrony

# Verify NTP
chronyc tracking
chronyc sources

# ═══════════════════════════════════════════════════════
# PHASE 2: Set timezone to Asia/Jakarta
# ═══════════════════════════════════════════════════════

# Set timezone
sudo timedatectl set-timezone Asia/Jakarta

# Verify
timedatectl status
date

# ═══════════════════════════════════════════════════════
# PHASE 3: Restart timezone-sensitive services
# ═══════════════════════════════════════════════════════

sudo systemctl restart rsyslog
sudo systemctl restart cron
sudo systemctl restart fail2ban
sudo systemctl restart crowdsec        # If you want TZ change
sudo systemctl restart postgresql      # If you want TZ change

# ═══════════════════════════════════════════════════════
# PHASE 4: Verify everything
# ═══════════════════════════════════════════════════════

# Timezone
timedatectl status
date
cat /etc/timezone
ls -la /etc/localtime

# NTP
chronyc tracking
chronyc sources
chronyc sourcestats

# Services
sudo systemctl list-timers
sudo -u postgres psql -c "SHOW timezone;"
docker exec <container> date           # Compare with host
tail -5 /var/log/syslog                # Check timestamp format
sudo fail2ban-client status
sudo cscli metrics
```

## Appendix B: Summary of Decisions

| Decision | Choice | Rationale |
|---|---|---|
| NTP service | chrony (not timesyncd) | Better accuracy, falseticker detection, iburst, VM-friendly |
| NTP pools | Indonesian (id.pool.ntp.org) + Ubuntu fallback | Lowest latency for Jakarta VPS |
| Timezone | Asia/Jakarta (WIB, UTC+7) | Operator requirement |
| Docker timezone | UTC initially, WIB later via TZ env | Safest, no DST bugs, can change per-container |
| NTS | Not enabled (Indonesian pools don't support it) | Plain NTP with Indonesian pools, NTS with Ubuntu fallback later if needed |
| UFW | No additional rules needed | Outgoing allowed by default, conntrack handles return traffic |
| Service restarts | Yes, for rsyslog, cron, fail2ban, PostgreSQL | They cache timezone at startup |

---

*Report generated: 2026-05-31 | Author: Guinevere (Librarian research) | Version: 1.0*
