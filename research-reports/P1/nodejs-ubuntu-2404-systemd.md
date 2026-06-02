# Node.js Installation on Ubuntu 24.04 (Noble) for Production — Research Report

**Date:** 2026-06-01  
**Scope:** P1 — Guinevere infrastructure dependencies  
**Context:** Installing Node.js for running 9Router (npm package) as a production service

---

## 1. Executive Summary

| Approach | Node.js Version | Production Ready? | Recommendation |
|---|---|---|---|
| `apt install nodejs` (Ubuntu repo) | **18.19.1** | ❌ EOL since Apr 2025 | **Do NOT use** — end-of-life, no security patches |
| NodeSource APT repo | **24.x** (Active LTS) | ✅ Yes | **RECOMMENDED** for production |
| NodeSource APT repo | **22.x** (Maintenance LTS) | ✅ Yes | Acceptable alternative |
| nvm | any version | ⚠️ Per-user, not systemd-friendly | Development only |

**Bottom line:** `sudo apt install nodejs npm` gives Node.js 18.x which is **end-of-life**. Use **NodeSource** for Node.js 24.x (Active LTS, codename "Krypton"), install via their APT repository with `apt install nodejs` (includes npm). Write a systemd unit file with `ExecStart=/usr/bin/node /opt/9router/index.js` (or the actual entrypoint).

---

## 2. Ubuntu 24.04 Default Repository: What You Get

**Source:** Ubuntu packages noble (universe)  
**Package version:** `18.19.1+dfsg-6ubuntu5`  
**npm version:** `9.2.0~ds1-2` (separate package: `sudo apt install npm`)

**Status:** Node.js 18.x (Hydrogen) — **End-of-Life since April 2025**

- Ubuntu 24.04 ships Node.js 18.x in its `universe` repository
- This version is past its upstream EOL date (2025-04-30 per nodejs.org/release)
- No longer receives security patches from the Node.js project
- Ubuntu may still ship security backports, but critical CVEs are not guaranteed

| Ubuntu Release | Default `nodejs` | Upstream Status |
|---|---|---|
| Ubuntu 26.04 LTS (Resolute) | 22.22.x | Maintenance LTS |
| **Ubuntu 24.04 LTS (Noble)** | **18.19.1** | **End-of-life** |
| Ubuntu 22.04 LTS (Jammy) | 12.22.x | End-of-life |

**Evidence** ([packages.ubuntu.com](https://packages.ubuntu.com/en/noble/nodejs)):  
Version 18.19.1+dfsg-6ubuntu5 confirmed.  
**Evidence** ([nodejs.org/en/about/previous-releases](https://nodejs.org/en/about/previous-releases)):  
v18 Hydrogen EOL since March 2025.

**Verdict:** ❌ `sudo apt install nodejs` is **not suitable** for production in June 2026.

---

## 3. NodeSource APT Repository Support for Ubuntu 24.04

**Source:** [nodesource/distributions DEV_README.md](https://github.com/nodesource/distributions/blob/master/DEV_README.md)  
**Status:** ✅ Fully supported

### Supported Node.js Versions on Ubuntu Noble

| Node Version | Codename | Support Status | NodeSource Available? |
|---|---|---|---|
| 24.x | Krypton | **Active LTS** (until Oct 2026, then Maintenance until Apr 2028) | ✅ Yes |
| 22.x | Jod | **Maintenance LTS** (until Apr 2027) | ✅ Yes |
| 20.x | Iron | **EOL** (since Mar 2026) | ✅ Yes (but don't use) |
| 18.x | Hydrogen | **EOL** (since Apr 2025) | ✅ Yes (but don't use) |

**Evidence** ([DEV_README.md](https://github.com/nodesource/distributions/blob/master/DEV_README.md)):  
Ubuntu Noble ^24.04 supported for Node 18x, 20x, 21x, 22x, 23x, 24x — all ✅.

**Evidence** ([nodesource/distributions PR #1862](https://github.com/nodesource/distributions/pull/1862)):  
Node 24.x support added, setup_24.x scripts available.

### Installation Method (Manual, Recommended)

```bash
# Prerequisites
sudo apt update
sudo apt install -y ca-certificates curl gnupg

# Import GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
  | sudo gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg

# Add repository for Node.js 24.x (Active LTS)
NODE_MAJOR=24
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" \
  | sudo tee /etc/apt/sources.list.d/nodesource.list

# Install
sudo apt update
sudo apt install -y nodejs

# Verify
node --version   # v24.x
npm --version    # included with nodejs package
```

**Note:** The `nodistro` suite is used, not distro-specific codenames. This works across all supported Ubuntu versions.

---

## 4. Latest Node.js LTS as of June 2026

**Source:** [nodejs/Release schedule](https://github.com/nodejs/release/blob/main/README.md)  
**Source:** [nodejs.org/releases](https://nodejs.org/en/about/previous-releases)

### Current Release Status (June 2026)

| Version | Status | Codename | Released | EOL |
|---|---|---|---|---|
| **24.x** | **Active LTS** ✅ | **Krypton** | May 2025 | Apr 2028 |
| 22.x | Maintenance LTS | Jod | Apr 2024 | Apr 2027 |
| 26.x | Current (not yet LTS) | — | May 2026 | Apr 2029 (LTS Oct 2026) |
| 25.x | Maintenance (ending soon) | — | Oct 2025 | Jun 2026 |
| 20.x | **EOL** ❌ | Iron | Apr 2023 | Mar 2026 |

### Latest Versions Available

| Channel | Latest Version | Date |
|---|---|---|
| Node 24.x (LTS) | **24.15.0** (24.16.0 released May 21 but pending NodeSource sync) | 2026-05 |
| Node 22.x (LTS) | **22.22.3** | 2026-05 |
| Node 26.x (Current) | **26.2.0** | 2026-05 |

### Schedule Note

Starting with Node 27 (April 2027), Node.js moves to an **annual release cadence** — one major per year, all become LTS.

**Recommendation:** Use **Node.js 24.x (Krypton)** — Active LTS with support until April 2028.

---

## 5. npm Global Install Path on Ubuntu

When Node.js is installed via **NodeSource APT repository**:

```bash
npm config get prefix
# Result: /usr
```

| Prefix | Global Bins | Global Modules | Binaries Symlinked To |
|---|---|---|---|
| `/usr` | `/usr/bin` | `/usr/lib/node_modules` | `/usr/bin/<name>` |
| `/usr/local` | `/usr/local/bin` | `/usr/local/lib/node_modules` | `/usr/local/bin/<name>` |

**When NodeSource installs:** `npm config get prefix` returns `/usr`, so:
- Global binaries → `/usr/bin/`
- Global modules → `/usr/lib/node_modules/`

**When building from source / tarball into `/usr/local`:** prefix would be `/usr/local`

**Evidence** ([npm docs](https://docs.npmjs.com/cli/v10/configuring-npm/folders/)):  
> When in global mode, executables are linked into `{prefix}/bin` on Unix.

**Evidence** ([npm manpages](https://manpages.ubuntu.com/manpages/jammy/en/man1/npm-prefix.1.html)):  
> `npm prefix -g` shows the global prefix; bins go to `{prefix}/bin`.

---

## 6. systemd Service Patterns for Node.js

### 6.1 Canonical Production Unit File

**Source:** Multiple production guides (OneUptime, CloudBees, NodeSource blog, DigitalOcean)  
**Best practice:** Use **direct node binary**, NOT `npm start` in ExecStart.

```ini
# /etc/systemd/system/9router.service
[Unit]
Description=9Router - Node.js Production Service
Documentation=https://github.com/yourorg/9router
After=network-online.target
Wants=network-online.target

[Service]
# Run as non-root dedicated user
User=nodeapp
Group=nodeapp

# Working directory
WorkingDirectory=/opt/9router

# USE DIRECT NODE BINARY PATH (NOT npm start)
# For globally installed packages:
#   npm prefix -g = /usr  → ExecStart=/usr/bin/<package-name>
#   npm prefix -g = /usr/local → ExecStart=/usr/local/bin/<package-name>
# For local app entrypoint:
ExecStart=/usr/bin/node /opt/9router/index.js

# Restart policy
Restart=on-failure
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=3

# Production environment
Environment=NODE_ENV=production
Environment=PORT=3000

# Load secrets from env file (secure with chmod 640)
EnvironmentFile=/opt/9router/.env

# Security hardening
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/9router/logs /tmp

# Logging via journald
StandardOutput=journal
StandardError=journal
SyslogIdentifier=9router

[Install]
WantedBy=multi-user.target
```

### 6.2 Why NOT `npm start` in ExecStart

**Source:** ServerFault, multiple guides

Problems with `ExecStart=/usr/bin/npm start`:
1. `npm start` is a wrapper that spawns `node` as a child process — systemd tracks the npm process, not the Node.js process
2. Signal handling (SIGTERM on restart) goes to npm, not to node — graceful shutdown breaks
3. Extra overhead from npm CLI parsing package.json on every start
4. npm may resolve paths differently under systemd's minimal environment

**Correct pattern:** Always use the **direct node binary** with the absolute path to the entrypoint script.

### 6.3 For Globally Installed npm Packages

If 9Router is installed via `npm install -g 9router`:

```bash
# Check where global bins are installed
npm prefix -g
# → /usr  (NodeSource install)
# → /usr/local  (source/tarball install)

# Find the exact binary path
which 9router
# → /usr/bin/9router  if prefix=/usr
# → /usr/local/bin/9router  if prefix=/usr/local
```

Then in systemd unit:
```ini
# For NodeSource install (prefix=/usr):
ExecStart=/usr/bin/9router

# For source/tarball install (prefix=/usr/local):
ExecStart=/usr/local/bin/9router
```

### 6.4 Dedicated Service User

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin nodeapp
sudo mkdir -p /opt/9router
sudo chown -R nodeapp:nodeapp /opt/9router
```

### 6.5 Production Dependency Installation

```bash
# Deterministic install — use npm ci, NOT npm install
sudo -u nodeapp npm ci --production --prefix /opt/9router
```

**Evidence** ([nodebestpractices](https://github.com/goldbergyoni/nodebestpractices)):  
> "Run `npm ci` to strictly do a clean install matching package.json and package-lock.json."

### 6.6 Security Hardening Summary

| Directive | Purpose |
|---|---|
| `User=nodeapp` | Non-root execution |
| `NoNewPrivileges=yes` | Prevent privilege escalation |
| `ProtectSystem=strict` | Read-only /usr and /etc |
| `ProtectHome=yes` | No access to /home, /root |
| `ReadWritePaths=` | Only allow writes to specific dirs |
| `EnvironmentFile=` | Secrets out of unit file, chmod 640 |
| `Restart=on-failure` | Auto-restart on crash (not on clean exit) |

### 6.7 Service Lifecycle Commands

```bash
sudo systemctl daemon-reload
sudo systemctl enable 9router.service   # Start on boot
sudo systemctl start 9router.service    # Start now
sudo systemctl status 9router.service   # Check status
sudo systemctl restart 9router.service  # Restart
sudo journalctl -u 9router.service -f   # Tail logs
```

---

## 7. Recommendation for Guinevere / 9Router

### Production Installation Steps

```bash
# 1. Install Node.js 24.x via NodeSource
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
  | sudo gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
NODE_MAJOR=24
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" \
  | sudo tee /etc/apt/sources.list.d/nodesource.list
sudo apt update
sudo apt install -y nodejs

# 2. Create service user
sudo useradd --system --no-create-home --shell /usr/sbin/nologin nodeapp

# 3. Create app directory
sudo mkdir -p /opt/9router
sudo chown nodeapp:nodeapp /opt/9router

# 4. Install 9router globally (or clone + npm ci)
sudo npm install -g 9router
# Verify binary location
which 9router   # → /usr/bin/9router

# 5. Create systemd unit (template above)
sudo nano /etc/systemd/system/9router.service

# 6. Create env file
sudo nano /opt/9router/.env
sudo chown root:nodeapp /opt/9router/.env
sudo chmod 640 /opt/9router/.env

# 7. Enable and start
sudo systemctl daemon-reload
sudo systemctl enable 9router.service
sudo systemctl start 9router.service
```

---

## 8. Sources

| Source | URL |
|---|---|
| Ubuntu noble nodejs package | https://packages.ubuntu.com/en/noble/nodejs |
| NodeSource distributions README | https://github.com/nodesource/distributions |
| NodeSource Ubuntu support table | https://github.com/nodesource/distributions/blob/master/DEV_README.md |
| Node.js releases / previous releases | https://nodejs.org/en/about/previous-releases |
| Node.js release schedule | https://github.com/nodejs/release/blob/main/README.md |
| Node.js release schedule evolution (2026) | https://nodejs.org/en/blog/announcements/evolving-the-nodejs-release-schedule |
| Node.js 24.x latest release | https://github.com/nodejs/node/releases/tag/v24.16.0 |
| npm folders docs | https://docs.npmjs.com/cli/v10/configuring-npm/folders/ |
| npm prefix manpage | https://manpages.ubuntu.com/manpages/jammy/en/man1/npm-prefix.1.html |
| systemd Node.js guide (OneUptime) | https://oneuptime.com/blog/post/2026-03-02-how-to-set-up-nodejs-as-a-systemd-service-on-ubuntu/view |
| Running Node.js with systemd (CloudBees) | https://www.cloudbees.com/blog/running-node-js-linux-systemd |
| NodeSource blog: systemd basics | http://nodesource.com/blog/running-your-node-js-app-with-systemd-part-1/ |
| Node best practices (Goldbergyoni) | https://github.com/goldbergyoni/nodebestpractices |
| Deploy node on Linux guide | https://expeditedsecurity.com/blog/deploy-node-on-linux/ |
| Linux FS hierarchy: /usr/bin vs /usr/local/bin | https://unix.stackexchange.com/questions/8656/usr-bin-vs-usr-local-bin-on-linux |
| UbuntuUpdates noble nodejs | https://www.ubuntuupdates.org/package/core/noble/universe/base/nodejs |
| Linuxize guide: Node.js on Ubuntu 24.04 (2026) | https://linuxize.com/post/how-to-install-node-js-on-ubuntu-24-04/ |
| Raff Technologies guide (2026) | https://rafftechnologies.com/learn/tutorials/install-nodejs-ubuntu-24-04 |

---

## 9. Key Decisions for StepPrompts

1. **Replace** `sudo apt install -y nodejs npm` → use **NodeSource** for Node.js 24.x
2. **systemd ExecStart:** use **direct node binary** (`/usr/bin/node /opt/9router/index.js`) NOT `npm start`
3. **npm global path** when installed via NodeSource: `/usr/bin/<binary>` (prefix = `/usr`)
4. **Production install:** `npm ci --production` not `npm install`
5. **Security:** dedicated `nodeapp` user, `ProtectSystem=strict`, `EnvironmentFile` for secrets