# P0 Infrastructure Step Audit — Post ADR-035 (Hermes Migration)

**Audit Date:** 2026-06-05
**Auditor:** Guinevere (Sisyphus-Junior)
**Source:** `stepprompts/StepPrompts.md` P0 steps + `adr/ADR-035-hermes-migration.md`
**Evidence Base:** `docs/setup-evidence/P0/` (all 29 steps have evidence), `adr/ADR-Index.md`

---

## Executive Summary

ADR-035 (Hermes NousResearch Migration Architecture, Accepted 2026-06-04) adopts a **Hybrid Hermes Migration** (Option D) with 5 pillars:

| Pillar | Decision | Infrastructure Impact |
|---|---|---|
| 1. Discord | MIGRATE to Hermes native gateway | `bot.py` replaced; no infra change |
| 2. Memory | HYBRID (PostgreSQL+pgvector primary unchanged) | **Zero change** to PostgreSQL, pgvector, TimescaleDB |
| 3. Safety | HOOKS + PLUGINS | New hook scripts; Redis DB5 for safety state |
| 4. MCP | HYBRID (5 native + 7 custom preserved) | No infra change |
| 5. LLM | RETAIN 9Router at `localhost:20128` | **Zero change** |

**Audit Conclusion:** ADR-035 preserves all P0 infrastructure. PostgreSQL, Redis, Caddy, Tailscale, SOPS, Cloudflare Tunnel, Docker, UFW, fail2ban, CrowdSec, swap, cgroups, and NTP are **all retained as-is**. The migration adds few requirements: Hermes config directories (already in P0-003), Hermes-specific backup scope (P0-027), and Hermes-aware Caddy routing (P0-024). Most steps are **VALID**; a small subset needs minor updates.

---

## Classification Schema

| Classification | Meaning |
|---|---|
| **VALID** | Step unchanged by ADR-035; commands, verification, and rollback remain correct |
| **NEEDS-UPDATE** | Step remains fundamentally correct but requires minor scope/note additions for Hermes awareness |
| **STALE** | Step partially outdated due to ADR-035 decisions; non-trivial updates needed |
| **OBSOLETE** | Step no longer needed post-ADR-035 |

---

## Per-Step Classification

### P0-000: VPS Audit and Existing State Documentation

**Classification:** VALID
**Reasoning:** Read-only audit step. ADR-035 runs on the same shared VPS (`hostdata.id 4C/16GB`). No infrastructure change. The audit baseline remains valid — services, ports, and resources are unchanged.
**ADR-035 Reference:** §D11 "Shared VPS compatibility — Hermes runs in same Python environment, no additional processes... Port isolation unchanged."

---

### P0-001: Create guinevere Linux User

**Classification:** VALID
**Reasoning:** The `guinevere` user owns all services including Hermes. ADR-035 hook scripts run under this user (`/home/guinevere/code/guinevere/hooks/`). Hermes gateway runs as a systemd service under `guinevere`. No change.
**ADR-035 Reference:** All hook paths use `/home/guinevere/code/guinevere/`.

---

### P0-002: SSH Config Update

**Classification:** VALID
**Reasoning:** SSH access is operator-facing, not affected by agent framework migration. Key-based auth and alias remain valid.
**ADR-035 Reference:** None needed — SSH is orthogonal to Hermes.

---

### P0-003: Directory Structure Creation

**Classification:** VALID
**Reasoning:** The original step already includes `config/hermes/` in the directory tree. ADR-035 adds files under this path (`config/hermes/config.yaml`, `config/hermes/hooks.yaml`, `config/hermes/SOUL.md`, `config/hermes/mcp-servers.yaml`) — all within the existing structure. No update needed.

---

### P0-004: UFW Firewall Rules

**Classification:** VALID
**Reasoning:** ADR-035 does not change any port requirements. Hermes Discord gateway uses the same Discord WebSocket/HTTP ports as `bot.py`. UFW rules (SSH only + Tailscale 41641/udp) remain correct.
**ADR-035 Reference:** §D11 "Port isolation unchanged."

---

### P0-005: fail2ban Configuration

**Classification:** VALID
**Reasoning:** fail2ban protects SSH only. No change from Hermes migration. The existing configuration covers both Guinevere and Aizanta SSH access.
**ADR-035 Reference:** Not affected.

---

### P0-006: CrowdSec Setup

**Classification:** VALID
**Reasoning:** CrowdSec monitors all VPS traffic (SSH, web). No change from Hermes migration. Community blocklists and nftables bouncer remain correct.
**ADR-035 Reference:** Not affected.

---

### P0-007: Swap Configuration

**Classification:** VALID
**Reasoning:** System-level swap (4GB, swappiness=10) is unchanged. ADR-035 does not alter memory requirements — Hermes runs in the same Python environment.
**ADR-035 Reference:** §D11 "cgroup limits unchanged."

---

### P0-008: NTP and Timezone Configuration

**Classification:** VALID
**Reasoning:** Timezone (Asia/Jakarta, WIB UTC+7) and chrony NTP remain correct. Hermes cron (Phase 7) uses system time. Persona rituals (5 daily) run on WIB schedule.
**ADR-035 Reference:** Phase 7 mentions `hermes cron` which depends on system time.

---

### P0-009: cgroup Resource Limits

**Classification:** VALID
**Reasoning:** ADR-035 explicitly confirms: "cgroup limits unchanged." Guinevere slice (8GB RAM, 2 CPU cores) remains valid. Hermes gateway replaces `bot.py` process — same resource profile.
**ADR-035 Reference:** §D11, constraints table: "cgroup limits unchanged."

---

### P0-010: Docker Network Creation

**Classification:** VALID
**Reasoning:** Docker is still used for Prometheus, Grafana, and Loki (observability stack). `guinevere-net` bridge network (172.28.0.0/16) remains correct. No Hermes containers are added.
**ADR-035 Reference:** Observability stack preserved (Phase 7).

---

### P0-011: SOPS Installation

**Classification:** VALID — with Hermes awareness note
**Reasoning:** SOPS remains the master secret encryption tool for infrastructure-level secrets (DB passwords, Redis passwords, API keys for 9Router, backup credentials). ADR-035 adds `hermes secrets` for Hermes-level API key management as a complementary tool — not a replacement. The step itself is unchanged.
**ADR-035 Reference:** §Negative #8: "Secrets encrypted via `hermes secrets`." However, SOPS handles infrastructure secrets; `hermes secrets` handles Hermes runtime keys. Both coexist.

**Flag:** The step currently makes no mention of `hermes secrets`. Recommend adding a note: "Hermes-specific API keys (Discord bot token for Hermes gateway, agent skills API keys) may use `hermes secrets` instead of SOPS. SOPS remains authoritative for infrastructure secrets (DB credentials, backup keys, 9Router API keys)."

---

### P0-012: age Key Generation and Backup

**Classification:** VALID
**Reasoning:** The age key pair is the master encryption key for SOPS. ADR-035 requires SOPS for infrastructure secrets (unchanged). The age key is unaffected.
**ADR-035 Reference:** Not affected.

---

### P0-013: SOPS Secrets File Structure

**Classification:** NEEDS-UPDATE
**Reasoning:** The secrets template (`guinevere-secrets.yaml`) must include Hermes-aware entries:
1. 9Router API key (`llm.nine_router_api_key`) — already present
2. Discord bot token — already present (but note: Hermes gateway needs the same token)
3. Hermes-specific: agent skills API keys, Gotify tokens, webhook URLs
4. The `.sops.yaml` `path_regex` should include `config/hermes/` paths if any Hermes config files contain encrypted values

**Update required:** Add Hermes secrets section to the template; extend `.sops.yaml` path regex to cover Hermes config paths. Also document the SOPS-vs-`hermes secrets` boundary.

---

### P0-014: PostgreSQL 16 Setup

**Classification:** VALID
**Reasoning:** ADR-035 Pillar 2 (Memory = HYBRID) **explicitly preserves** PostgreSQL+pgvector as primary write authority. Config unchanged: port 5433, `listen_addresses = 'localhost'`, database name `guinevere` (ADR-031). No change whatsoever.
**ADR-035 Reference:** §Pillar 2: "PostgreSQL+pgvector primary write authority unchanged — 47 tables, 12 schemas."

---

### P0-015: pgvector Extension Installation

**Classification:** VALID
**Reasoning:** pgvector 0.7.0+ (1536-dim embeddings, HNSW indexes) is preserved verbatim. ADR-035 does not change the embedding pipeline or vector storage. All 7 memory files (3,941 lines) are preserved.
**ADR-035 Reference:** §Pillar 2 table: "Embedding pipeline — 1536-dim HNSW — Unchanged."

---

### P0-016: TimescaleDB Extension Installation

**Classification:** VALID
**Reasoning:** TimescaleDB for surveillance events and observability metrics is unchanged. ADR-035 preserves all surveillance and observability infrastructure.
**ADR-035 Reference:** §Pillar 2: all PostgreSQL schemas preserved.

---

### P0-017: PostgreSQL Users Creation

**Classification:** VALID
**Reasoning:** Role-separated PostgreSQL users (`guinevere_core`, `guinevere_surveillance`, `guinevere_scheduler`, `guinevere_readonly`, `guinevere_backup`) are unchanged. Hermes plugins (`GuinevereSafetyPlugin`, `memory_plugin.py`) connect as `guinevere_app` or `guinevere_core` — same users.
**ADR-035 Reference:** Plugin config uses `postgresql://guinevere_app@localhost/guinevere` — consistent with existing user model.

---

### P0-018: PostgreSQL Security Hardening

**Classification:** VALID
**Reasoning:** SSL enforcement, `pg_hba.conf` restrictions, and password policies are unchanged. Hermes connects as a PostgreSQL client — same auth path.
**ADR-035 Reference:** Not affected.

---

### P0-019: PgBouncer Connection Pooling Setup

**Classification:** VALID
**Reasoning:** PgBouncer on port 5434 pools connections from all services including Hermes plugins. No change needed.
**ADR-035 Reference:** Not affected.

---

### P0-020: Redis 7 Setup

**Classification:** NEEDS-UPDATE — ADR-030 DB assignment conflict flagged
**Reasoning:** The step correctly sets up Redis on port 6380 with authentication and 16 databases. However, ADR-035 §ADR Cross-Reference Notes identifies a **pre-existing Redis DB assignment conflict** between the runtime code and ADR-030:

| DB | ADR-030 Canonical | Current Runtime | Hermes Plugin Usage (ADR-035) |
|---|---|---|---|
| DB0 | Task Queue | Task Queue | — |
| DB1 | LLM Cache | LLM Cache | — |
| DB2 | Surveillance buffer | **Consent cache** (`consent_gate.py`) | Consent cache (hook `pre_tool_call`) |
| DB3 | Sessions | Sessions | — |
| DB4 | Pub/Sub | **Session cache** (`session_adapter.py`) | Shadow mode: separate DB |
| DB5 | Rate limiting | Rate limiting | **Safety state** (`GuinevereSafetyPlugin`) |

ADR-035 states: "ADR-030 should be updated (via superseding ADR or addendum) to reflect actual runtime Redis assignments, or Hermes-specific uses should migrate to DB6+ if available."

**Update required:** Add a note documenting the ADR-030 conflict. The step's DB assignment table currently reflects ADR-030 canonical values, which contradict runtime. Either update to match runtime or flag the conflict and reference the pending ADR-030 resolution.

---

### P0-021: Redis ACL Configuration

**Classification:** NEEDS-UPDATE
**Reasoning:** The step is marked "Not Started" and defines ACL users for `guinevere_core`, `guinevere_surveillance`, `guinevere_scheduler`, `guinevere_discord`, and `guinevere_monitoring`. ADR-035 introduces:
1. **Hermes safety plugin** uses Redis DB5 — needs an ACL user (e.g., `guinevere_hermes_safety`)
2. **Hermes consent hook** uses Redis DB2 — covered by existing `guinevere_core` or needs a dedicated user
3. **Hermes shadow mode** uses a separate Redis DB — may need a distinct user during migration

**Update required:** Add `guinevere_hermes_safety` ACL user with access to DB5. Document which existing ACL user covers Hermes consent cache (DB2) and session management. Update ACL password storage to include Hermes-specific passwords.

---

### P0-022: Tailscale Configuration

**Classification:** VALID
**Reasoning:** Tailscale VPN mesh for secure internal access is unchanged. Operator access to Grafana:3000, Prometheus:9090 over Tailscale remains. No Hermes dependency on Tailscale beyond what already exists.
**ADR-035 Reference:** Not affected.

---

### P0-023: Cloudflare Tunnel Setup

**Classification:** VALID
**Reasoning:** Cloudflare Tunnel provides the single public endpoint for Discord webhook receiver (ADR-026). ADR-035 does not change the webhook architecture — Hermes Discord gateway still needs a public endpoint for Discord's outbound webhooks and interactions endpoint.
**ADR-035 Reference:** Not affected.

---

### P0-024: Caddy Reverse Proxy

**Classification:** NEEDS-UPDATE
**Reasoning:** Caddy currently serves as reverse proxy for internal services and Discord webhook routing. Post-ADR-035, the routing topology shifts:

1. **Discord webhook receiver**: Hermes gateway handles Discord WebSocket + HTTP interactions natively. The Caddy route for Discord interaction endpoint should point to Hermes gateway instead of `bot.py`'s HTTP endpoint (if one existed).
2. **Gotify notifications**: Still routed through Caddy — unchanged.
3. **Health check endpoints**: Hermes gateway exposes health endpoints that Caddy should route.
4. **Internal services** (Grafana, Prometheus): Still Tailscale-only, unchanged.

**Update required:** Add Caddy route for Hermes gateway health endpoint (`/health` or similar). Update Discord webhook route target if Hermes exposes a different HTTP listener. Document which services Caddy fronts post-migration.

---

### P0-025: Git Repository Initialization

**Classification:** VALID
**Reasoning:** Git repository on the VPS is unchanged. ADR-035 adds new files under `config/hermes/`, `hooks/`, `plugins/` — all within the existing repo. `.gitignore` should exclude Hermes SQLite state (`~/.hermes/state.db`).
**ADR-035 Reference:** Phase 0 includes version pinning for Hermes (`--require-hashes`). `.gitignore` should be updated but the step itself is valid.

---

### P0-026: GitHub PAT and SOPS Storage

**Classification:** VALID
**Reasoning:** GitHub PAT for private repo access and SOPS-encrypted storage remain valid. ADR-035 does not change the GitHub integration pattern. Hermes may add `hermes secrets` as a secondary store but GitHub PAT stays in SOPS.
**ADR-035 Reference:** Not directly affected.

---

### P0-027: Backup Baseline

**Classification:** NEEDS-UPDATE
**Reasoning:** ADR-035 introduces `hermes backup` and `hermes checkpoints` as operational tooling. The backup baseline must include:

1. **Hermes state**: `~/.hermes/state.db` (transient session state and FTS5 search indexes)
2. **Hermes config**: `config/hermes/config.yaml`, `config/hermes/hooks.yaml`, `config/hermes/SOUL.md`, `config/hermes/mcp-servers.yaml`, `config/hermes/auth_matrix.yaml`
3. **Hook scripts**: `hooks/*.py`
4. **Plugin files**: `plugins/*.py`
5. **Hermes checkpoints**: Integration with `restic` snapshots

The existing restic-based backup (PostgreSQL dump, config files) is still valid — Hermes paths should be added to the backup scope.

**Update required:** Add Hermes paths to `restic` backup include list. Document `hermes backup` vs `restic` boundary: `hermes backup` handles agent operational state; `restic` handles full system backups per ADR-025/ADR-032.

---

### P0-028: Pre-flight Verification

**Classification:** NEEDS-UPDATE
**Reasoning:** The phase transition checklist currently checks only P0 infrastructure. Post-ADR-035, the checklist should also verify Hermes readiness before P1 begins:

**Additional checks needed:**
- [ ] `hermes --version` returns v0.15.2 (pinned)
- [ ] `hermes doctor` all green
- [ ] `hermes security` zero HIGH/MODERATE findings (Phase 0 gate)
- [ ] `config/hermes/SOUL.md` exists with Guinevere identity
- [ ] `config/hermes/config.yaml` valid syntax
- [ ] `config/hermes/hooks.yaml` valid syntax
- [ ] Hook scripts at `/home/guinevere/code/guinevere/hooks/` executable
- [ ] Redis DB5 accessible for safety plugin state
- [ ] Hermes config directory permissions correct (`chmod 750`)
- [ ] `.gitignore` excludes `~/.hermes/state.db`

**ADR-035 Reference:** Phase 0 gate: "`hermes doctor` clean + `hermes security` zero HIGH/MODERATE."

---

## Summary Table

| Step | Name | Classification | ADR-035 Impact |
|---|---|---|---|
| P0-000 | VPS Audit | **VALID** | None |
| P0-001 | Create guinevere User | **VALID** | None |
| P0-002 | SSH Config | **VALID** | None |
| P0-003 | Directory Structure | **VALID** | Hermes dir already included |
| P0-004 | UFW Firewall | **VALID** | Port isolation unchanged |
| P0-005 | fail2ban | **VALID** | None |
| P0-006 | CrowdSec | **VALID** | None |
| P0-007 | Swap | **VALID** | cgroup limits unchanged |
| P0-008 | NTP/Timezone | **VALID** | Hermes cron depends on it |
| P0-009 | cgroup Limits | **VALID** | Explicitly confirmed unchanged |
| P0-010 | Docker Network | **VALID** | Observability stack preserved |
| P0-011 | SOPS Installation | **VALID** | `hermes secrets` is complementary |
| P0-012 | age Key Generation | **VALID** | None |
| P0-013 | SOPS Secrets Structure | **NEEDS-UPDATE** | Add Hermes entries, extend path regex |
| P0-014 | PostgreSQL 16 | **VALID** | Explicitly preserved — Pillar 2 |
| P0-015 | pgvector | **VALID** | Explicitly preserved |
| P0-016 | TimescaleDB | **VALID** | Explicitly preserved |
| P0-017 | PostgreSQL Users | **VALID** | Same users used by Hermes plugins |
| P0-018 | PostgreSQL Hardening | **VALID** | None |
| P0-019 | PgBouncer | **VALID** | None |
| P0-020 | Redis 7 Setup | **NEEDS-UPDATE** | ADR-030 DB assignment conflict flagged |
| P0-021 | Redis ACL | **NEEDS-UPDATE** | Add Hermes safety user; ACL scope change |
| P0-022 | Tailscale | **VALID** | None |
| P0-023 | Cloudflare Tunnel | **VALID** | Discord webhook still needed |
| P0-024 | Caddy Reverse Proxy | **NEEDS-UPDATE** | Add Hermes gateway routes |
| P0-025 | Git Repository | **VALID** | `.gitignore` update needed (minor) |
| P0-026 | GitHub PAT + SOPS | **VALID** | None |
| P0-027 | Backup Baseline | **NEEDS-UPDATE** | Add Hermes state + config to scope |
| P0-028 | Pre-flight Verification | **NEEDS-UPDATE** | Add Hermes readiness checks |

---

## Summary Counts

| Classification | Count | Steps |
|---|---|---|
| **VALID** | 23 | P0-000 through P0-012, P0-014 through P0-019, P0-022, P0-023, P0-025, P0-026 |
| **NEEDS-UPDATE** | 6 | P0-013, P0-020, P0-021, P0-024, P0-027, P0-028 |
| **STALE** | 0 | — |
| **OBSOLETE** | 0 | — |

---

## Flagged Overlaps with Hermes Configuration

### 1. Redis DB Assignment Conflict (P0-020, P0-021)

**Severity:** MEDIUM
**Description:** ADR-030 assigns DB2=Surveillance, DB4=Pub/Sub, but runtime code uses DB2=Consent cache, DB4=Session cache. ADR-035 adds DB5=Safety state (new). The P0-020 and P0-021 steps reference ADR-030 canonical values.

**Resolution path:** ADR-030 should be superseded or amended to reflect actual runtime assignments. Until resolved, P0-020/P0-021 should document the conflict and reference the actual runtime usage. This is a **pre-existing issue** not introduced by ADR-035 — ADR-035 only surfaces it.

### 2. SOPS vs hermes secrets Boundary (P0-011, P0-013)

**Severity:** LOW
**Description:** ADR-035 introduces `hermes secrets` for Hermes-level API key management, while SOPS continues to handle infrastructure secrets. The boundary between the two systems is not explicitly documented.

**Resolution path:** P0-013 should define which secrets go where: SOPS for infrastructure (DB credentials, 9Router API key, backup credentials, GitHub PAT); `hermes secrets` for Hermes runtime (Discord bot token for gateway, skills API keys, webhook URLs). This avoids secret duplication or divergence.

### 3. Caddy Route Changes (P0-024)

**Severity:** LOW
**Description:** Hermes Discord gateway replaces `bot.py` and may expose different HTTP endpoints. Caddy routes need to point to the correct Hermes listener for Discord webhook verification and health checks.

**Resolution path:** After Hermes gateway is configured in Phase 2, update Caddy config to route Discord interactions endpoint to Hermes gateway's HTTP listener. Health check route should proxy to `hermes gateway status` endpoint.

### 4. Hermes Backup Scope (P0-027)

**Severity:** LOW
**Description:** The current backup baseline covers PostgreSQL dumps and config files via restic. ADR-035 adds `hermes backup` and `hermes checkpoints` for agent operational state. The backup scope needs to include `~/.hermes/state.db` and `config/hermes/`.

**Resolution path:** Add Hermes paths to restic include list. Phase 7 configures `hermes backup` automated pipeline — coordinate with existing restic backups to avoid duplication.

### 5. Pre-flight Hermes Readiness (P0-028)

**Severity:** MEDIUM
**Description:** The P0→P1 phase transition checklist currently checks only infrastructure services (PostgreSQL, Redis, Tailscale, UFW, SOPS, restic). Post-ADR-035, P1 includes Hermes-specific tasks (SOUL.md customization, hook development). The transition should verify Hermes is installed and healthy before P1 begins.

**Resolution path:** Add `hermes doctor` and `hermes security` checks to the P0→P1 transition checklist. Ensure Hermes v0.15.2 is installed and pinned with `--require-hashes`.

---

## Conclusion

**All 29 P0 steps remain functionally valid.** ADR-035's hybrid migration explicitly preserves PostgreSQL, Redis, and all infrastructure services. No step is OBSOLETE or STALE. Six steps need minor updates to document Hermes awareness:

1. **P0-013** — extend SOPS secrets template and `.sops.yaml` regex
2. **P0-020** — document ADR-030 Redis DB assignment conflict
3. **P0-021** — add Hermes safety plugin Redis ACL user
4. **P0-024** — add Hermes gateway routes to Caddy
5. **P0-027** — include Hermes state and config in backup scope
6. **P0-028** — add Hermes readiness checks to phase transition

These updates are **non-blocking** — infrastructure setup proceeds identically regardless. The updates should be applied before Phase 1 (Safety Foundation) begins, as Phase 1 requires Hermes to be installed and healthy.

---

## Evidence References

| Evidence | Path |
|---|---|
| StepPrompts source | `stepprompts/StepPrompts.md` (lines 144–3240, P0 section) |
| ADR-035 | `adr/ADR-035-hermes-migration.md` (2,514 lines, Accepted 2026-06-04) |
| ADR Index | `adr/ADR-Index.md` (35 ADRs registered) |
| P0 Evidence | `docs/setup-evidence/P0/` (all 29 steps have evidence directories) |
| Hermes phase-0 | `docs/setup-evidence/hermes-migration/phase-0-security.md` |

---

**Footer:** P0 Infrastructure Audit — Post ADR-035 Hermes Migration — Prepared by Guinevere (Sisyphus-Junior) on 2026-06-05. This is a read-only audit report. No step prompts were modified.