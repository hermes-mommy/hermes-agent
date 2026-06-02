# STEP-P0-006 Verification — CrowdSec Setup

| Field | Value |
|---|---|
| Step | STEP-P0-006 |
| Phase | P0 Infrastructure |
| Date | 2026-05-31 |
| Status | PASS, independent auditor gate passed |
| Host | `faiz-prod-01` / `100.94.104.22` |
| Implementer | Hephaestus / Guinevere workflow |

## 1. What Was Done

Installed and configured CrowdSec for collaborative threat detection on the shared VPS. The implementation installed CrowdSec engine `1.7.8`, enabled SSH/Linux/nginx security collections, created the `guinevere-trusted` allowlist before bouncer enablement, installed the official nftables firewall bouncer `0.0.34`, verified CAPI/community blocklist pull, and validated bouncer enforcement using safe TEST-NET IP `192.0.2.1`.

The implementation intentionally did not use the StepPrompts draft package `crowdsec-firewall-bouncer-ufw` because live package resolution confirmed the package is unavailable. The host uses `nf_tables`, so `crowdsec-firewall-bouncer-nftables` is the correct CrowdSec remediation component.

## 2. Files Changed

### Local repository files

Created evidence files:

- `docs/setup-evidence/P0/STEP-P0-006/crowdsec-status.txt`
- `docs/setup-evidence/P0/STEP-P0-006/crowdsec-collections.txt`
- `docs/setup-evidence/P0/STEP-P0-006/crowdsec-whitelist-proof.txt`
- `docs/setup-evidence/P0/STEP-P0-006/crowdsec-bouncer-proof.txt`
- `docs/setup-evidence/P0/STEP-P0-006/crowdsec-test.log`
- `docs/setup-evidence/P0/STEP-P0-006/aizanta-post-check.md`
- `docs/setup-evidence/P0/STEP-P0-006/coexistence-proof.md`
- `docs/setup-evidence/P0/STEP-P0-006/p0-006-summary.md`
- `docs/setup-evidence/P0/STEP-P0-006/verification.md`

Tracker/docs to sync after parent verification:

- `PROGRESS.md`
- `CHECKLIST.md`
- `stepprompts/StepPrompts.md`

### VPS runtime files/services

- Added CrowdSec apt repository source via official install script.
- Installed `crowdsec` package `1.7.8`.
- Installed `crowdsec-firewall-bouncer-nftables` package `0.0.34`.
- CrowdSec config under `/etc/crowdsec/` created by package setup.
- Bouncer config under `/etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml` created by package setup; API key retained on VPS only and redacted from evidence.
- Enabled services:
  - `crowdsec.service`
  - `crowdsec-firewall-bouncer.service`

## 3. Validation Results

### SSH access

Command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 guinevere-vps "whoami && hostname"
```

Output:

```text
guinevere
faiz-prod-01
```

### Package/backend resolution

Command:

```bash
iptables -V
nft --version
apt-cache policy crowdsec crowdsec-firewall-bouncer-nftables crowdsec-firewall-bouncer-iptables crowdsec-firewall-bouncer-ufw
```

Key output:

```text
iptables v1.8.10 (nf_tables)
nftables v1.0.9
crowdsec candidate: 1.7.8 from packagecloud any/any
crowdsec-firewall-bouncer-nftables candidate: 0.0.34
crowdsec-firewall-bouncer-iptables candidate: 0.0.34
crowdsec-firewall-bouncer-ufw: no package candidate shown
```

### Service status

Command:

```bash
systemctl is-active crowdsec
systemctl is-active crowdsec-firewall-bouncer
```

Output:

```text
active
active
```

### Installed package versions

Command:

```bash
dpkg-query -W crowdsec crowdsec-firewall-bouncer-nftables
```

Output:

```text
crowdsec	1.7.8
crowdsec-firewall-bouncer-nftables	0.0.34
```

### Collections

Command:

```bash
cscli collections list -o human | grep -E 'crowdsecurity/(linux|sshd|nginx|whitelist-good-actors)'
```

Output:

```text
crowdsecurity/linux                  enabled  /etc/crowdsec/collections/linux.yaml
crowdsecurity/nginx                  enabled  /etc/crowdsec/collections/nginx.yaml
crowdsecurity/sshd                   enabled  /etc/crowdsec/collections/sshd.yaml
crowdsecurity/whitelist-good-actors  enabled  /etc/crowdsec/collections/whitelist-good-actors.yaml
```

### Allowlist

Command:

```bash
cscli allowlists inspect guinevere-trusted
cscli allowlists check 100.112.201.124
cscli allowlists check 100.94.104.22
```

Output excerpt:

```text
Allowlist: guinevere-trusted
127.0.0.1/8      P0-006 trusted localhost plus Samm and VPS Tailscale IPs  never
::1              P0-006 trusted localhost plus Samm and VPS Tailscale IPs  never
100.94.104.22    P0-006 trusted localhost plus Samm and VPS Tailscale IPs  never
100.112.201.124  P0-006 trusted localhost plus Samm and VPS Tailscale IPs  never

100.112.201.124 is allowlisted by item 100.112.201.124 from guinevere-trusted
100.94.104.22 is allowlisted by item 100.94.104.22 from guinevere-trusted
```

### CAPI / community blocklist

Command:

```bash
cscli capi status
cscli decisions list --origin CAPI | sed -n '1,80p'
```

Output excerpt:

```text
You can successfully interact with Central API (CAPI)
Sharing signals is enabled
Pulling community blocklist is enabled
Pulling blocklists from the console is enabled

ID  Source  Scope:Value        Reason          Action  expiration
2   CAPI    Ip:185.220.101.100 ssh:bruteforce  ban     166h58m39s
3   CAPI    Ip:147.185.132.100 ssh:bruteforce  ban     166h58m39s
```

### Metrics

Command:

```bash
cscli metrics
```

Output excerpt:

```text
file:/var/log/auth.log  Lines read 225  Lines parsed 33  Lines poured to bucket 27
Local API Bouncers Metrics: cs-firewall-bouncer-1780205575 /v1/decisions/stream GET 28
crowdsecurity/sshd-logs          140 hits, 5 parsed
crowdsecurity/sshd-success-logs  135 hits, 28 parsed
crowdsecurity/ssh-bf             Current Count 3, Instantiated 4, Poured 5
```

### Bouncer proof

Command:

```bash
cscli bouncers list
nft list table ip crowdsec | grep -E 'table ip crowdsec|set crowdsec-blacklists|chain crowdsec|ip saddr @crowdsec'
```

Output excerpt:

```text
cs-firewall-bouncer-1780205575  127.0.0.1  valid  crowdsec-firewall-bouncer  v0.0.34

table ip crowdsec {
  set crowdsec-blacklists-CAPI {
  set crowdsec-blacklists-cscli {
  chain crowdsec-chain-input {
    ip saddr @crowdsec-blacklists-CAPI counter name "crowdsec-blacklists-CAPI" drop
    ip saddr @crowdsec-blacklists-cscli counter name "crowdsec-blacklists-cscli" drop
```

### Safe TEST-NET decision validation

Command:

```bash
cscli decisions add --ip 192.0.2.1 --duration 10m --reason guinevere-p0-006-test
sleep 15
cscli decisions list --ip 192.0.2.1
nft list table ip crowdsec | grep -C 2 '192.0.2.1|cscli|crowdsec-blacklists'
cscli decisions delete --ip 192.0.2.1
sleep 12
cscli decisions list --ip 192.0.2.1
nft list table ip crowdsec | grep 192.0.2.1 || echo test_ip_removed
```

Output excerpt:

```text
level=info msg="Decision successfully added"
ID 15000  Source cscli  Ip:192.0.2.1  Reason guinevere-p0-006-test  Action ban

set crowdsec-blacklists-cscli {
  elements = { 192.0.2.1 timeout 9m57s expires 9m44s800ms }
}

level=info msg="1 decision(s) deleted"
No active decisions
test_ip_removed
```

## 4. Evidence Artifacts

- `docs/setup-evidence/P0/STEP-P0-006/crowdsec-status.txt`
- `docs/setup-evidence/P0/STEP-P0-006/crowdsec-collections.txt`
- `docs/setup-evidence/P0/STEP-P0-006/crowdsec-whitelist-proof.txt`
- `docs/setup-evidence/P0/STEP-P0-006/crowdsec-bouncer-proof.txt`
- `docs/setup-evidence/P0/STEP-P0-006/crowdsec-test.log`
- `docs/setup-evidence/P0/STEP-P0-006/aizanta-post-check.md`
- `docs/setup-evidence/P0/STEP-P0-006/coexistence-proof.md`
- `docs/setup-evidence/P0/STEP-P0-006/p0-006-summary.md`
- `audit-reports/P0/STEP-P0-006/internal-context-report.md`
- `audit-reports/P0/STEP-P0-006/evidence-pattern-report.md`
- `audit-reports/P0/STEP-P0-006/external-crowdsec-ubuntu-report.md`
- `audit-reports/P0/STEP-P0-006/external-crowdsec-bouncer-report.md`

## 5. Shared VPS Impact

Aizanta health after implementation:

```text
aizanta-bot Up 7 days (healthy) 8000/tcp
aizanta-nginx Up 7 days (healthy) 100.94.104.22:80->80/tcp
aizanta-frontend Up 7 days (healthy) 3000/tcp
aizanta-postgres Up 7 days (healthy) 127.0.0.1:5432->5432/tcp
aizanta-redis Up 7 days (healthy) 127.0.0.1:6379->6379/tcp
```

Protected ports after implementation:

```text
127.0.0.1:6379      docker-proxy
100.94.104.22:80    docker-proxy
127.0.0.1:8080      crowdsec local API
127.0.0.1:5432      docker-proxy
```

No Aizanta container, Docker network, database, Redis, nginx config, or `/home/aizanta/` path was modified.

## 6. ADR Compliance

- ADR-018: Implements defense-in-depth via CrowdSec detection and firewall remediation.
- ADR-019: Preserves Tailscale/SSH access and explicitly allowlists trusted Tailscale IPs before bouncer validation.
- ADR-014: Compatible with shared VPS architecture; no Aizanta resource or namespace was modified.
- ADR-015: No bouncer API key or credentials were written to repo evidence.

## 7. AC Reference

- AC-SEC-001: Host security baseline now includes CrowdSec, CAPI community blocklist pull, SSH collection, firewall bouncer, and allowlist protection for trusted operator/VPS IPs.

## 8. Rollback / Re-run Safety

Preferred rollback:

```bash
sudo systemctl stop crowdsec-firewall-bouncer
sudo apt purge -y crowdsec-firewall-bouncer-nftables
sudo systemctl stop crowdsec
sudo apt purge -y crowdsec
sudo rm -rf /etc/crowdsec /var/lib/crowdsec /var/log/crowdsec.log
sudo nft list tables | grep crowdsec || true
ssh guinevere-vps "whoami && hostname"
docker ps --format '{{.Names}} {{.Status}} {{.Ports}}' | grep aizanta
ss -tlnp | grep -E '5432|6379|80'
```

Re-run notes:

- `cscli collections install` is idempotent for already-installed collections.
- `cscli allowlists create guinevere-trusted` should be guarded with `|| true` if re-run.
- Do not re-print or store bouncer API keys in repository evidence.

## 9. Design Decisions / Caveats

- Used `crowdsec-firewall-bouncer-nftables`, not nonexistent `crowdsec-firewall-bouncer-ufw`.
- Nginx collection is installed, but no host nginx acquisition was created because Aizanta nginx logs are not present in `/var/log/nginx` on host.
- Console-selected additional blocklists require operator console enrollment/selection; however CAPI community blocklist pulling is enabled and CAPI decisions are active.
- Docker/UFW bypass caveat remains architectural; CrowdSec bouncer nftables chains are active but P0-006 did not modify Docker networking.

## 10. Evidence Gate

Parent verification: PASS.

Parent verification evidence:

- Evidence artifact count: 9 files under `docs/setup-evidence/P0/STEP-P0-006/`.
- `PROGRESS.md` counter sync: `7 / 257 (2.7%)`, P0 `7/29`, P0-006 checked.
- `CHECKLIST.md` P0-006 line checked.
- `StepPrompts.md` P0-006 status/checks synced and invalid `crowdsec-firewall-bouncer-ufw` package corrected to nftables bouncer guidance.
- LSP diagnostics clean on `PROGRESS.md`, `CHECKLIST.md`, `stepprompts/StepPrompts.md`, and this verification file.
- Secret scan over P0-006 evidence: no private keys, tokens, API keys, password assignments, or unredacted bouncer key matches.
- Live checks: CrowdSec active, bouncer active, trusted IP allowlist active, TEST-NET decision cleaned up, collections enabled, CAPI community blocklist pull active, Aizanta healthy, protected ports unchanged.

Independent auditor gate: PASS.

Auditor report: `audit-reports/P0/STEP-P0-006/step-p0-006-auditor-report.md`.

Auditor summary:

- Verdict: PASS.
- DoD matrix: 24/24 PASS.
- Blocking findings: 0.
- Live read-only checks confirmed CrowdSec `1.7.8`, nftables bouncer `0.0.34`, trusted IP allowlist, CAPI community blocklist pull, active nftables enforcement, cleaned TEST-NET decision, SSH availability, fail2ban/UFW coexistence, Aizanta health, protected ports unchanged, clean diagnostics, and no plaintext secrets in evidence.
- Informational observations only: evidence naming differs from a suggested pattern but artifacts are complete; nftables was selected over earlier iptables research based on live Ubuntu 24.04 backend; swap remains 0 as expected before P0-007; Docker/UFW bypass caveat remains documented.

## 11. Footer

Source task: STEP-P0-006 CrowdSec setup
Date: 2026-05-31
Validation method: live SSH commands, CrowdSec/CAPI/nftables checks, Aizanta guardrails, file-based evidence, independent auditor PASS
