# StepPrompts Audit Report — Dimensions D3 (Security Compliance) & D4 (Shared VPS Compliance)

**Auditor:** Senior Independent Auditor
**Date:** 2026-05-31
**Document Audited:** `stepprompts/StepPrompts.md` (v1.0, 7360 lines, 252 steps across 12 phases)
**Reference Documents:** ADR-015, ADR-018, ADR-019, ADR-008, Security Policy v1.0, Access Control RBAC/ABAC Matrix v1.0, Encryption & Key Management Standard v1.0, PROGRESS.md

---

## Executive Summary

StepPrompts.md demonstrates strong security awareness in the infrastructure foundation (Phase 0). SOPS+age secrets management, PostgreSQL hardening with pg_hba.conf, Redis requirepass, Tailscale-only admin access, and resource isolation are well-implemented. However, **four CRITICAL findings** and **six HIGH findings** compromise the security posture, primarily in later phases where plaintext credential files are created on disk, Docker admin passwords are hardcoded in docker-compose, and Shared VPS impact notes are absent for 223 of 252 steps.

**Verdict: NEEDS REVIEW** — 4 CRITICAL findings block production deployment. Must be fixed before implementation begins.

---

## DIMENSION 3: SECURITY COMPLIANCE FINDINGS

### CRITICAL FINDINGS

```
[CRITICAL] P1-007 (line 3528): Plaintext API key file created on disk
Step P1-007 creates an unencrypted environment file at `secrets/.env.9router` with the 
placeholder `NINE_ROUTER_API_KEY=PLACEHOLDER_KEY`, then in P1-008 (line 3590) replaces it 
with the real operator API key: `echo "NINE_ROUTER_API_KEY=<operator-provides-key>" > secrets/.env.9router`.
This contradicts ADR-015 which mandates "Plaintext secrets are forbidden in ADRs, docs, 
code, evidence, logs, and sub-agent reports." The `.env.9router.sops` file created earlier 
in the same step is never actually used by the systemd service.
Fix: The systemd service should decrypt from SOPS at startup, not read from a plaintext env file. 
Use a wrapper script: `ExecStart=/bin/bash -c 'source <(sops -d secrets/.env.9router.sops) && exec 9router ...'`
or use tmpfs-backed decryption that the service reads at boot.
```

```
[CRITICAL] P2-017 (line 5611): Plaintext Discord bot token written to disk
Step P2-017 creates unencrypted `secrets/.env.discord` with the bot token in plaintext:
`echo "DISCORD_BOT_TOKEN=${BOT_TOKEN}" > secrets/.env.discord`. The token was first decrypted 
from SOPS (line 5610: `BOT_TOKEN=$(sops -d secrets/discord-secrets.yaml ...)`) and then 
written as plaintext. While chmod 600 is applied, this still violates ADR-015.
Fix: Same pattern as P1-007. Use SOPS decryption at service startup only, never persist plaintext.
```

```
[CRITICAL] P8-001 (line 6962): Hardcoded Grafana admin password in docker-compose.yml
`GF_SECURITY_ADMIN_PASSWORD=changeme` is hardcoded in the Grafana Docker compose configuration.
This is a plaintext credential in a config file that would be committed to the repository.
Per ADR-015 and Security Policy §1.4, this is a direct violation.
Fix: Use `${GF_SECURITY_ADMIN_PASSWORD}` environment variable reference in docker-compose.yml,
and supply the value from a SOPS-encrypted .env file or Docker secrets.
```

```
[CRITICAL] P2-020 (line 5682): Hardcoded Gotify admin password in docker-compose.yml
`GOTIFY_DEFAULTUSER_PASS=changeme` is hardcoded in the Gotify Docker compose configuration.
Same violation pattern as the Grafana password above.
Fix: Use `${GOTIFY_DEFAULTUSER_PASS}` environment variable reference, supplied from SOPS-encrypted secrets.
```

### HIGH FINDINGS

```
[HIGH] P0-020/P0-021: Missing Redis rename-command for dangerous commands
The Redis configuration in P0-020 includes `requirepass` but does NOT include `rename-command` 
directives for dangerous commands. Security Policy §2.13 (Config/Secrets Management, Threat 12.6) 
and standard Redis hardening recommend renaming or disabling:
- FLUSHDB
- FLUSHALL  
- CONFIG
- DEBUG
- SHUTDOWN
- KEYS
Per ADR-018 defense-in-depth, this is a missing layer.
Fix: Add to P0-020 redis-guinevere.conf:
  rename-command FLUSHDB ""
  rename-command FLUSHALL ""
  rename-command CONFIG ""
  rename-command DEBUG ""
  rename-command SHUTDOWN ""
  rename-command KEYS ""
```

```
[HIGH] P0-002/P0-004: SSH hardening is incomplete
The SSH setup in P0-002 configures key-based auth and ed25519 keys, but does NOT:
1. Explicitly disable root login (`PermitRootLogin no`)
2. Disable password authentication (`PasswordAuthentication no`)  
3. Configure a non-standard SSH port (per ADR-018 defense-in-depth)
4. Restrict which users can SSH (`AllowUsers guinevere samm`)
5. Set `MaxAuthTries` or `LoginGraceTime`
The Security Policy §1.2 Layer 2 (Host) mandates "SSH key-only auth" but the implementation
does not enforce this at the sshd_config level.
Fix: Add an explicit SSH hardening step in P0 that modifies /etc/ssh/sshd_config with:
  PermitRootLogin no
  PasswordAuthentication no
  MaxAuthTries 3
  LoginGraceTime 30
  AllowUsers guinevere samm
  Port <non-standard>
```

```
[HIGH] P7-001/P7-002: HMAC secret generation step is missing
The `hmac_secret` for surveillance endpoints is listed as "PLACEHOLDER" in the P0-013 secrets
template (line 1193), but NO step in P0-P7 explicitly generates a cryptographically strong HMAC
secret and stores it in SOPS. The surveillance E2E test (P7-021, line 6914) references `$HMAC_SECRET` 
as an environment variable but it was never set up.
Fix: Add a step in P7 (e.g., P7-002) that generates the HMAC secret:
  `openssl rand -hex 32`
and stores it encrypted in SOPS: `secrets/surveillance-secrets.yaml`.
```

```
[HIGH] P8-012/P8-013: Missing explicit Sentry send_default_pii=false configuration
P8-013 mentions "Sentry scrubber (remove PII)" but the step description (line 7021) does NOT 
include the specific configuration `send_default_pii=False` or `before_send` event processor. 
Per Security Policy §2.11 (Monitoring, Threat 5.4), PII must be scrubbed from error reports.
Fix: Explicitly add in the Sentry SDK initialization step:
  ```python
  sentry_sdk.init(
      dsn=...,
      send_default_pii=False,
      before_send=strip_pii,
  )
  ```
```

```
[HIGH] P0-018: PostgreSQL SSL not configured
P0-018 hardens pg_hba.conf correctly but explicitly states (line 1781): "SSL certificates can 
be added later if remote access is needed via Tailscale." Security Policy §1.2 Layer 4 (Data) 
mandates "data encrypted at rest and in transit." While PostgreSQL listens on localhost only,
all connections between services and the database are unencrypted on the loopback interface.
This is a defense-in-depth gap.
Fix: Add explicit step to generate self-signed TLS certificates for PostgreSQL or defer to P10 
with explicit documentation. At minimum, document the risk acceptance in an ADR.
```

```
[HIGH] P2-005/P2-006: Discord bot token exposed in process list
Lines 5000-5001, 5074-5075: `DISCORD_BOT_TOKEN=$(sops -d secrets/discord-secrets.yaml | grep ...)` 
decrypts the token into a shell variable, which is visible in `/proc/<pid>/environ` and process 
listing. This is a transient exposure but still a plaintext secret in memory.
Fix: Use a wrapper that pipes SOPS output directly to the Python script without storing in a 
shell variable, e.g.:
  `sops -d secrets/discord-secrets.yaml | python scripts/setup-categories.py`
```

### MEDIUM FINDINGS

```
[MEDIUM] P0-017: Database passwords briefly in bash variables
Lines 1555-1559: Passwords generated with `openssl rand -base64 32` and stored in shell variables 
(CORE_PASS, SURV_PASS, etc.) before SOPS encryption. These are visible in process memory during 
execution. Acceptable for one-time setup but should be documented as a known risk.
Fix: Document the transient exposure and note that passwords are only in memory during initial setup.
```

```
[MEDIUM] P8-001: Docker Compose version "3" is obsolete
Line 6944: `version: "3"` in docker-compose.yml. Modern Docker Compose (v2+) does not require 
the version field and it triggers a deprecation warning.
Fix: Remove the `version` field from all docker-compose files.
```

```
[MEDIUM] P0-020: Redis configuration has no ACL file directive for persistence
P0-021 creates ACL users via `redis-cli` and uses `ACL SAVE`, but the redis-guinevere.conf in 
P0-020 does not include an `aclfile` directive. Without this, ACL state may not persist across 
service restarts depending on Redis version behavior.
Fix: Add `aclfile /etc/redis/redis-guinevere-users.acl` to the redis config and verify ACL LOAD on startup.
```

```
[MEDIUM] P5-002: FastAPI authentication mechanism not specified
P5-002 (line 6439) mentions "JWT or API key middleware for internal API security" but the step 
implementation (lines 6396-6436) only creates route stubs without actual authentication middleware.
No JWT validation, no API key checking, no middleware.
Fix: Implement explicit authentication middleware in the FastAPI routes or add a dedicated step for auth setup.
```

```
[MEDIUM] P6-016: Shell MCP tool whitelist insufficient
P6-016 (line 6786-6787) defines ALLOWED_COMMANDS and BLOCKED_COMMANDS but the blocked list uses 
string matching which can be bypassed:
- `rm -rf` is blocked but `rm -r -f` or `rm --recursive --force` may pass
- `chmod 777` is blocked but `chmod -R 777` may pass
Fix: Use command-level deny/allow with argument parsing, not string matching. Consider using a 
sandbox like nsjail or bubblewrap for shell execution.
```

```
[MEDIUM] P1-005: Safety configuration uses string comparison for yandere level
Line 3297-3298: `yandere_max: "Y5"` in YAML config. If the config file is modified to "Y6", 
the application must enforce the ceiling in code. The step doesn't show explicit code enforcement.
Fix: Ensure the yandere FSM code (P4-004) has a hardcoded ceiling that cannot be overridden by config.
```

```
[MEDIUM] P0-004: UFW reset removes existing rules
Line 474: `sudo ufw --force reset` removes ALL existing firewall rules, including any Aizanta-specific
rules that may already be configured. This is noted in the Shared VPS Notes but the CAUTION 
message is insufficient — the step should verify Aizanta rules before resetting.
Fix: Add pre-check: `sudo ufw status > /tmp/ufw-pre-reset.txt` and post-restore of Aizanta rules.
```

```
[MEDIUM] P7-010: Consent verification gate implementation not shown
P7-010 (line 6843) mentions "Check Samm's consent status before storing" but the actual 
implementation code is not provided in the step. The surveillance API code (P7-001, lines 6848-6872) 
does not include consent checking.
Fix: Add explicit consent check implementation in the surveillance event handler.
```

### LOW FINDINGS

```
[LOW] P0-024: Caddy tls internal generates self-signed certificates
This is documented and acceptable for Tailscale-internal use. Not a finding requiring action, 
but worth noting for future production upgrade.
```

```
[LOW] P0-012: age key backup instruction is manual only
Line 1097-1099: "Store in password manager, safe, or offline backup" — no automated backup 
verification step. If the operator forgets to back up the key, all encrypted secrets become 
unrecoverable.
Fix: Add a verification step that confirms backup exists before proceeding.
```

```
[LOW] P0-013: .gitignore in secrets/ has exclusion for *.sops.yaml
Line 1232: `!*.sops.yaml` allows .sops.yaml to be committed. This is the config file (not secrets) 
but the pattern could accidentally allow a secrets file with .sops.yaml extension.
Fix: Use explicit filenames instead of wildcard exclusions.
```

```
[LOW] P2-002: Discord token verification truncates to 20 chars
Line 4853: `sops -d secrets/discord-secrets.yaml | grep discord_bot_token | head -c 20`
This only verifies the first 20 characters. A corrupted token after char 20 would not be caught.
Fix: Use `sops -d ... | python -c "import yaml,sys; d=yaml.safe_load(sys.stdin); assert len(d['discord_bot_token']) > 50"`
```

```
[LOW] Appendix A: Quick reference shows plaintext password variable
Line 7259: `redis-cli -a $REDIS_PASS -n 0 INFO` — the $REDIS_PASS variable contains the decrypted 
password in the shell session. While this is expected for operator use, the quick reference should 
note this.
```

---

## DIMENSION 4: SHARED VPS COMPLIANCE FINDINGS

### CRITICAL FINDINGS

None for D4 specifically.

### HIGH FINDINGS

```
[HIGH] P1-P11 (223 steps): Missing "Shared VPS Notes" sections
Of the 252 total steps, only Phase 0 steps (29 steps) consistently include "Shared VPS Notes" 
in their Notes sections. The remaining 223 steps in Phases 1-11 do NOT include explicit Shared 
VPS impact assessment notes. This contradicts the document's own rule (line 25): 
"Shared VPS awareness. Guinevere shares infrastructure with Aizanta. Every step includes VPS 
impact notes where relevant."

Specific gaps:
- P1 (LLM + Hermes): No Shared VPS notes except P1-012 (Ollama RAM)
- P2 (Discord): No Shared VPS notes in any of 21 steps
- P3 (Memory): No Shared VPS notes in any of 19 steps
- P4 (Persona): No Shared VPS notes in any of 19 steps
- P5 (Agent Loop): No Shared VPS notes in any of 23 steps
- P6 (MCP Tools): No Shared VPS notes in any of 21 steps
- P7 (Surveillance): No Shared VPS notes in any of 22 steps
- P8 (Observability): No Shared VPS notes (but Docker ports bind to localhost ✓)
- P9-P11: No Shared VPS notes in any of 62 steps

Steps most likely to impact Aizanta:
- P8-001 (Docker compose for Prometheus/Grafana/Loki — resource consumption)
- P5-018/P5-019 (New systemd services — CPU/memory)
- P7-018 (Surveillance service — continuous background processing)
- P6-017 (Docker MCP tool — container management)

Fix: Add "Shared VPS Notes" to every step that:
1. Creates or modifies systemd services (CPU/memory impact)
2. Creates Docker containers (network/resource impact)
3. Modifies system configuration (shared impact)
4. Installs system packages (disk space)
5. Uses significant network bandwidth
```

```
[HIGH] P0-004: UFW reset may disrupt Aizanta firewall rules
Line 474: `sudo ufw --force reset` removes ALL existing UFW rules. If Aizanta has existing 
firewall rules (e.g., allowing specific ports for Aizanta's web services), this reset will 
remove them. The Notes section says "Do NOT block ports Aizanta needs" but the reset command 
itself removes those ports.

Fix: Before reset:
1. Export current UFW rules: `sudo ufw status numbered > /tmp/ufw-backup.txt`
2. Identify Aizanta-specific rules
3. Reset UFW
4. Re-add Guinevere rules
5. Re-add Aizanta rules from backup
```

```
[HIGH] P8-001: Monitoring stack resource consumption not assessed for Aizanta
The Docker compose for Prometheus, Grafana, and Loki (lines 6944-6977) creates three containers
that run continuously. Combined, these can consume 500MB-1GB RAM and significant CPU during 
scraping. No Shared VPS impact assessment exists for this step.
Fix: Add Shared VPS Notes assessing RAM/CPU impact and confirming the guinevere.slice cgroup
limits cover the monitoring containers.
```

### MEDIUM FINDINGS

```
[MEDIUM] P0-014: PostgreSQL instance sharing not fully assessed
Notes mention "If Aizanta also uses PostgreSQL, use separate database names and users" but don't 
address:
1. Whether Aizanta's PostgreSQL version is compatible with installing PG 16 alongside
2. Whether shared `shared_buffers` allocation could starve Aizanta
3. Whether the shared postgres user could create cross-database access
Fix: Add explicit check in P0-000 audit for Aizanta's PostgreSQL version and configuration.
```

```
[MEDIUM] P0-020: Redis port conflict resolution is manual
Line 2022: "Use a different port for Guinevere Redis (e.g., 6380). Update config and all references."
This is reactive — the conflict is discovered during implementation, not pre-empted.
Fix: Add port availability check to P0-000 audit and pre-assign Guinevere Redis to port 6380
if Aizanta uses 6379.
```

```
[MEDIUM] P0-010: Docker subnet overlap not pre-checked
Line 987-988: Troubleshooting mentions subnet overlap detection but it's reactive. The
P0-000 audit should explicitly document Aizanta's Docker subnets.
Fix: Add Docker network inventory to P0-000 VPS audit.
```

```
[MEDIUM] P0-009: cgroup limits apply to guinevere user only
The guinevere.slice limits apply to services running as the `guinevere` user. If any Guinevere
service runs as a different user (e.g., Redis as `redis` user, Docker as root), those processes 
are NOT limited by the slice. This could allow Guinevere to exceed its 8GB allocation.
Fix: Verify all Guinevere services use `Slice=guinevere.slice` AND `User=guinevere` (or 
appropriate user within the slice).
```

```
[MEDIUM] P0-006: CrowdSec monitors ALL VPS traffic
CrowdSec's community-sourced decisions could ban IPs that Aizanta depends on (e.g., Aizanta's
API clients, webhooks, or monitoring endpoints). No mechanism exists to whitelist Aizanta-critical
IPs from CrowdSec decisions.
Fix: Add CrowdSec whitelist configuration for known Aizanta endpoints.
```

```
[MEDIUM] No disk space monitoring for shared VPS
Multiple steps create data (PostgreSQL, Redis, logs, surveillance events, backups) that 
accumulate over time. No step explicitly monitors disk space usage to ensure Guinevere doesn't
fill the VPS disk, which would impact Aizanta.
Fix: Add disk space monitoring to P8 (Observability) and include alerting when disk > 80%.
```

### LOW FINDINGS

```
[LOW] P0-007: Swap file is system-wide
Line 758: "This swap is system-wide, benefiting both Guinevere and Aizanta." This is positive 
but should be documented as a shared resource decision.
```

```
[LOW] P0-008: NTP timezone change affects all services
Setting timezone to Asia/Jakarta affects ALL services on the VPS, including Aizanta. If Aizanta 
expects a different timezone, this could cause log timestamp mismatches.
Fix: Check Aizanta's timezone expectations in P0-000 audit.
```

```
[LOW] P0-001: guinevere user home directory permissions
Line 299: `chmod 750 /home/guinevere` — the home directory is readable by group. On a shared 
VPS, ensure the guinevere group doesn't include any Aizanta users.
```

---

## CROSS-DIMENSION FINDINGS

```
[MEDIUM] P2-017 systemd service uses EnvironmentFile with plaintext file
The guinevere-discord.service (line 5599) references:
  `EnvironmentFile=/home/guinevere/code/guinevere/secrets/.env.discord`
This file contains the plaintext Discord token. While this is a standard systemd pattern, 
it should be noted that:
1. The plaintext file persists on disk (D3 violation)
2. Any process with read access to the guinevere user's home can read it (D3 violation)
3. The systemd service itself is fine — the issue is the file creation pattern
This is a D3 finding that manifests through a systemd configuration pattern.
```

```
[MEDIUM] No step explicitly verifies that no plaintext secrets are in the repository
There is no step that runs a secret scanner (e.g., gitleaks, detect-secrets, trufflehog) 
against the repository to verify no plaintext secrets have been committed. P0-025 creates 
.gitignore rules but doesn't verify their effectiveness.
Fix: Add a CI step (P10-008 or P10-011) that runs secret scanning.
```

```
[LOW] Evidence file paths don't follow a consistent convention
Some steps use `evidence/phase-N/step-MMM/` while the document header references 
`evidence/phase-0/step-000/`. The PROGRESS.md doesn't specify a convention.
```

---

## SUMMARY TABLE

| Dimension | Status | Findings | Critical | High | Medium | Low |
|-----------|--------|----------|----------|------|--------|-----|
| D3: Security Compliance | NEEDS REVIEW | 21 | 4 | 6 | 8 | 5 |
| D4: Shared VPS Compliance | NEEDS REVIEW | 10 | 0 | 3 | 6 | 3 |
| Cross-Dimension | NEEDS REVIEW | 3 | 0 | 0 | 2 | 1 |
| **TOTAL** | **NEEDS REVIEW** | **34** | **4** | **9** | **16** | **9** |

---

## TOP PRIORITY FIXES (Must resolve before implementation)

1. **Eliminate all plaintext credential files** — P1-007, P1-008, P2-017 must use SOPS-only patterns. No `.env.*` plaintext files should ever be written to disk.

2. **Remove hardcoded Docker passwords** — P8-001, P2-020 must use environment variable references sourced from SOPS-encrypted files.

3. **Add Shared VPS Notes to P1-P11** — Every infrastructure-impacting step needs explicit Aizanta impact assessment.

4. **Add SSH hardening step** — Root login disable, password auth disable, non-standard port.

5. **Add Redis dangerous command renaming** — FLUSHDB, FLUSHALL, CONFIG, DEBUG, SHUTDOWN.

6. **Add HMAC secret generation step** — Currently missing from P7.

---

## POSITIVE OBSERVATIONS

The following security practices are well-implemented and worth acknowledging:

1. **SOPS+age pattern is consistent** throughout P0 — correct `sops --encrypt --age` usage
2. **PostgreSQL pg_hba.conf** is properly hardened with scram-sha-256, localhost only, reject-all
3. **Redis requirepass** is set with per-service ACL users
4. **Tailscale-only admin access** is correctly implemented with zero public ports
5. **cgroup resource limits** (8GB RAM, 200% CPU) are properly configured
6. **Docker network isolation** (guinevere-net) is correctly separated from Aizanta
7. **User isolation** (guinevere user with scoped sudoers) is well-designed
8. **P0-000 VPS audit** provides excellent baseline documentation
9. **P0-028 pre-flight verification** includes explicit Aizanta check
10. **File permissions** (600 for secrets, 700 for secrets dir, 440 for sudoers) are correct
11. **Yandere FSM ceiling enforcement** in code (Y5 max, Y6 forbidden) is safety-critical
12. **HARD STOP detection** implementation with multiple trigger patterns is robust

---

*Audit completed: 2026-05-31*
*Auditor: Senior Independent Auditor*
*Methodology: Line-by-line review of all 7360 lines against ADR-015, ADR-018, ADR-019, ADR-008, Security Policy v1.0, Access Control Matrix v1.0, Encryption Key Management Standard v1.0*
*Tool: Manual audit with pattern matching for credentials, ports, permissions, and Shared VPS Notes*
