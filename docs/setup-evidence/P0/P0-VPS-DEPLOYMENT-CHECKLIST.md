# P0 Open Items — VPS Deployment Checklist

**Purpose:** Resolve all 6 P0 FINAL AUDIT open items requiring VPS access  
**Target:** `faiz-prod-01` (Tailscale IP: `100.94.104.22`, user: `guinevere`)  
**Date:** 2026-05-31

---

## Pre-flight

```bash
# SSH into VPS
ssh guinevere@100.94.104.22

# Verify identity
whoami && hostname
```

---

## B1 — Encrypt + Shred Plaintext Secrets (CRITICAL)

**Risk:** 3 plaintext files with LIVE credentials on disk. CRITICAL — must resolve before any git operations.

```bash
cd /home/guinevere/code/guinevere

# Verify plaintext files exist
ls -la secrets/backup/*-plaintext.env

# Verify SOPS is installed
sops --version
# Expected: sops 3.8.0+ 

# Verify age key exists
ls -la /home/guinevere/secrets/age-key.txt
export SOPS_AGE_KEY_FILE="/home/guinevere/secrets/age-key.txt"

# Step 1: Encrypt restic password
sops --encrypt \
  --input-type dotenv \
  --output-type dotenv \
  secrets/backup/restic-password-plaintext.env \
  > secrets/backup/restic-password.env

# Step 2: Encrypt idcloudhost S3
sops --encrypt \
  --input-type dotenv \
  --output-type dotenv \
  secrets/backup/idcloudhost-s3-plaintext.env \
  > secrets/backup/idcloudhost-s3.env

# Step 3: Encrypt Cloudflare R2
sops --encrypt \
  --input-type dotenv \
  --output-type dotenv \
  secrets/backup/cloudflare-r2-plaintext.env \
  > secrets/backup/cloudflare-r2.env

# Step 4: Verify encrypted files exist and are readable
ls -la secrets/backup/*.env
head -c 80 secrets/backup/restic-password.env  # Should show SOPS JSON

# Step 5: Test decrypt (without printing secrets)
sops --decrypt secrets/backup/restic-password.env | head -c 80
# Expected: RESTIC_PASSWORD=... (confirm it decrypts)

# Step 6: SHRED plaintext files (DESTRUCTIVE)
shred -u secrets/backup/restic-password-plaintext.env
shred -u secrets/backup/idcloudhost-s3-plaintext.env
shred -u secrets/backup/cloudflare-r2-plaintext.env

# Step 7: Verify plaintext is GONE
ls -la secrets/backup/*-plaintext.env
# Expected: "No such file or directory"
```

**Verification:**
- [ ] 3 `*.env` files exist (encrypted, SOPS JSON format)
- [ ] 3 `*-plaintext.env` files are GONE
- [ ] `sops --decrypt` works on each encrypted file

---

## B3-C — Add Guinevere User to Docker Group

**Context:** P0-011 auditor found `guinevere` user cannot run `docker ps`. This blocks pre-flight and health checks.

```bash
# Add guinevere user to docker group
sudo usermod -aG docker guinevere

# Verify (requires re-login to take effect)
groups guinevere
# Expected: guinevere : guinevere docker

# Test after re-login (new SSH session)
ssh guinevere@100.94.104.22
docker ps
# Expected: list of running containers
```

**Verification:**
- [ ] `groups guinevere` includes `docker`
- [ ] In new SSH session, `docker ps` works without sudo

---

## B5#1 — Caddyfile Symlink to Config Directory

**Context:** P0-024 auditor found Caddyfile not symlinked to `/home/guinevere/config/caddy/`.

```bash
# Create config directory
mkdir -p /home/guinevere/config/caddy

# If Caddyfile exists in config dir already, backup
if [ -f /home/guinevere/config/caddy/Caddyfile ]; then
  cp /home/guinevere/config/caddy/Caddyfile /home/guinevere/config/caddy/Caddyfile.bak
fi

# Symlink /etc/caddy/Caddyfile to config dir
sudo ln -sf /etc/caddy/Caddyfile /home/guinevere/config/caddy/Caddyfile

# Verify
ls -la /home/guinevere/config/caddy/Caddyfile
# Expected: lrwxrwxrwx ... /home/guinevere/config/caddy/Caddyfile -> /etc/caddy/Caddyfile
```

**Verification:**
- [ ] `/home/guinevere/config/caddy/Caddyfile` is a symlink to `/etc/caddy/Caddyfile`
- [ ] Content matches Caddy configuration

---

## B5#2 — Disable Caddy Admin API (Port 2019)

**Context:** P0-024 auditor found port 2019 (Caddy admin) may be listening. Evidence file claims `admin off` but auditor flagged a discrepancy.

```bash
# Step 1: Check if Caddyfile has admin off
grep "admin" /etc/caddy/Caddyfile
# Expected: admin off

# Step 2: Check if port 2019 is listening
ss -tlnp | grep 2019
# If port 2019 IS listening, restart Caddy with new config

# Step 3: If admin line is missing or wrong, add/fix it
# Should already read: { admin off } at top of Caddyfile

# Step 4: Reload Caddy
sudo systemctl reload caddy

# Step 5: Verify port 2019 is NOT listening
ss -tlnp | grep 2019
# Expected: (no output)

# Step 6: Verify Caddy is still healthy
systemctl status caddy
ss -tlnp | grep -E '8443|3443|9443'
# Expected: 3 ports listening on Tailscale IP
```

**Verification:**
- [ ] `grep admin /etc/caddy/Caddyfile` shows `admin off`
- [ ] `ss -tlnp | grep 2019` returns NOTHING
- [ ] Caddy service is active/running
- [ ] Ports 8443/3443/9443 are still listening

---

## B5#3 — Verify Prometheus Binding

**Context:** P0-024 auditor flagged that Prometheus binding claim in evidence may not match actual config.

```bash
# Check Prometheus scrape config
sudo cat /etc/prometheus/prometheus.yml | grep -A 5 "scrape_configs"

# Check Prometheus binding
ss -tlnp | grep prometheus
# Or check the port 9090 binding
ss -tlnp | grep 9090

# Verify Prometheus service status
sudo systemctl status prometheus

# If Prometheus is not yet installed (P1 phase), note this
# and verify the Caddy reverse proxy config still forwards to localhost:9090
```

**Verification:**
- [ ] Prometheus bound to expected IP/port OR documented as "P1 phase, backend not running"
- [ ] Caddy reverse proxy for `guinevere-vps:9443 → localhost:9090` is correct and ready
- [ ] `tls internal` certs valid for Tailscale trust domain

---

## Final Verification — Run Pre-flight Check

```bash
cd /home/guinevere/code/guinevere

# Make sure pre-flight check is executable
chmod +x scripts/preflight-check.sh

# Run full pre-flight check
bash scripts/preflight-check.sh

# Review the output
# Expected: All PASS or documented WARN (Aizanta ports 5432/6379 = expected WARN)
# Exit code 0 = all PASS
echo "Exit code: $?"
```

---

## Post-Fix Checklist

| # | Item | Command to Verify | Status |
|---|---|---|---|
| B1 | Secrets encrypted | `ls secrets/backup/*.env` (3 files exist, SOPS JSON) | [ ] |
| B1 | Plaintext shredded | `ls secrets/backup/*-plaintext.env` (should fail) | [ ] |
| B3-C | Docker group | `groups guinevere \| grep docker` | [ ] |
| B5#1 | Caddy symlink | `ls -la /home/guinevere/config/caddy/Caddyfile` | [ ] |
| B5#2 | Port 2019 off | `ss -tlnp \| grep 2019` (no output) | [ ] |
| B5#3 | Prometheus binding | Verified or documented as P1 | [ ] |
| ALL | Pre-flight | `bash scripts/preflight-check.sh; echo $?` (exit 0) | [ ] |

---

**Footer:**  
Source: P0 FINAL AUDIT (audit-reports/P0/P0-FINAL-AUDIT.md)  
Date: 2026-05-31  
SSH target: `guinevere@100.94.104.22` (faiz-prod-01, Tailscale required)