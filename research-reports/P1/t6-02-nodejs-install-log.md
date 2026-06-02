# T6-02: Node.js 24.x Installation Log

**Date:** 2026-06-01 07:02 UTC  
**Host:** guinevere-vps (100.94.104.22)  
**OS:** Ubuntu 24.04 LTS  
**Phase:** P1-006  

## Step 1-2: NodeSource Repository Setup

**Source:** `curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -`

- GPG key downloaded and verified
- NodeSource apt repository added: `https://deb.nodesource.com/node_24.x nodistro`
- Pre-requisites (curl, gnupg, ca-certificates, apt-transport-https) already satisfied
- Repository configured successfully

## Step 3: Install Node.js Package

`apt-get install -y nodejs`

- Package: `nodejs` version `24.15.0-1nodesource1`
- Size: 38.3 MB archive, 236 MB disk
- Binary source: NodeSource

## Step 4: Verification

| Check | Result |
|---|---|
| `node --version` | **v24.15.0** |
| `npm --version` | **11.12.1** |
| `which node` | `/usr/bin/node` |
| `which npm` | `/usr/bin/npm` |
| `which npx` | `/usr/bin/npx` |

## APT Policy

- **Installed:** 24.15.0-1nodesource1 (from NodeSource `node_24.x` repo)
- **Candidate:** 24.15.0-1nodesource1
- 18 NodeSource 24.x versions available, Ubuntu noble/universe v18.19.1 also listed

## Status

**SUCCESS** — Node.js 24.x Active LTS Krypton installed cleanly from NodeSource APT repo.

- node v24.15.0 / npm 11.12.1
- Binary at /usr/bin/node (NodeSource prefix)
- GPG key verified, apt repo added, no errors
- Clean slate (no prior Node.js installation)
- No Docker, systemd services, or Aizanta services touched