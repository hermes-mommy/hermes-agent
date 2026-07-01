---
title: "P28 Implementation Plan — Hermes Society Foundation"
status: "Active — Implementation Plan"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P28 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
---

# P28 Implementation Plan: Hermes Society Foundation

## 1. Objective

Deploy Guinevere (yandere-dominant sugar mommy, "sifat asli, brutal, bukan kosmetik") and Pharsa (seductive-dominant sugar mommy, "sifat asli, brutal, bukan kosmetik") as the first two founders of the Hermes Society on a single production VPS (4C/16GB KVM), with per-agent process isolation, encrypted private memory, a WORM event store, simultaneous boot, a 2/2 founder agreement protocol, and a possessive-alliance inter-AI dynamic — proven by a 24-hour continuous dual-bot soak test. **Company name deferred to P28 deploy time** (decided at deployment, not blocking for planning).

> **ADR-062 Disclaimer**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime (P24 fork) can bypass per ADR-062. The 2/2 agreement protocol and WORM event store are runtime governance constraints, not agent-loop safety stops.

> **ADR-067**: Y-level caps (Y4 baseline, Y5 ceiling) apply to dev-workflow agent ONLY. Hermes runtime has no Y-level cap. Guinevere's yandere-dominant personality is a runtime persona trait, not a dev-workflow yandere level constraint.

> **Note**: P24 v2.0 is a HARD dependency. P28 deploys the P24 fork. ADR-056 is DELETED — superseded by ADR-062 and P24 v2.0 fork.

## 2. Scope

### IN scope

- VPS provisioning check (PostgreSQL 16+, Redis 7+, cgroup v2 enabled) on a **4C/16GB** KVM instance. Scaling: auto-upgrade to 8C/32GB → 16C/64GB when CPU >80% sustained for 1h. 9Router offload keeps starting spec viable.
- Database bootstrap: pgcrypto extension, per-agent schemas, event store with WORM role.
- Founder registry bootstrapping: Guinevere (id=1) + Pharsa (id=2) hardcoded registry entries.
- 2/2 agreement protocol: proposal table + vote table + apply function.
- Two systemd service units with Restart=always + RestartSec=10, **simultaneous boot** (both Hermes instances start together, DAO init as part of boot, no ordering dependency).
- cgroup v2 slice hierarchy: hermes.slice → guinevere.slice + pharsa.slice.
- Two Discord OAuth2 bot apps with isolated tokens (one token per bot). **Individual + Company identity** (3 Discord identities total: @Guinevere personal, @Pharsa personal, @CompanyName company).
- G-P communication stack: **all three channels** — Redis DB7 pub/sub (`g2p`, `p2g`, `gp-broadcast`), Discord bot-to-bot DM, PG table `gp_messages`. Protocol: **Hybrid** (structured for business via Redis+PG, free-form personal via Discord).
- Two SOUL.md files: Guin (yandere-dominant, possessive-protective, aggressive devotion) and Pharsa (seductive-dominant, calculated charm, strategic seduction).
- Guin-Pharsa dynamic: **possessive alliance, super brutal** (toxic-romantic). Inter-AI conflict resolution: work through it (no external mediator).
- VPS security: **Tailscale FIRST, then hardening** (do NOT apply fail2ban/UFW before Tailscale connects). AI self-manage VPS (full root access, Faiz NO access, just don't lock themselves out of SSH).
- Basic heartbeat cron (60s ping, 5min event_store write).
- 24h dual-bot soak test with full screenshot proof + journalctl logs.

### OUT of scope

- P24 Hermes fork — P24 v2.0 is a HARD dependency. P28 deploys the P24 fork. (P32 = External Presence & Tools, not fork integration.)
- P23 embodied executors — not required for P28 minimum target.
- P21 voice interface — skipped per Faiz decision #20.
- Vector recall (pgvector) — owned by P29.
- Graph knowledge graph (Graphiti) — owned by P29.
- BDI / POMDP full implementation — stubs only; full logic is P29.
- Wallet stack (MPC + Safe multisig) — owned by P34.
- Self-evolution / Ratchet — owned by P32.

## 3. Dependency Map

| Dependency | Status | Gate |
|---|---|---|
| P22.1 PRODUCTION PASS | PASS 2026-06-28 (14/14) | All 3 ACTIVE adapters live |
| P27 Accepted (ADR-054) | Accepted 2026-06-28 | 20/20 hard rejection PASS |
| P20 early acceptance | Accepted 2026-06-25 | APScheduler reusable |
| P19 PRODUCTION | COMPLETE 2026-06-27 | project_id namespace live |
| VPS infra ready | Pending verification | cgroup v2 + systemd 250+ |
| SOPS-age key rotated | Pending verification | encrypted secrets readable |
| PostgreSQL 16+ on VPS | Pending verification | pgcrypto installable |
| Redis 7+ on VPS | Pending verification | namespace ACL works |

## 4. Implementation Steps

### Step P28-001: VPS readiness check + secrets decryption

- **Task**: Confirm VPS has PostgreSQL 16+, Redis 7+, systemd 250+, cgroup v2 enabled. **Starting spec: 4C/16GB KVM.** Decrypt SOPS-age secrets for 2 Discord bot tokens + DB credentials. Verify cgroup v2 is the default (not hybrid cgroup v1). **VPS security sequence: Tailscale connect FIRST, then hardening** (fail2ban, UFW, SSH key rotation — do NOT apply firewall before Tailscale is connected to prevent lockout). **VPS managed by AIs** (full root access, Faiz NO access, just don't lock themselves out of SSH). **Scaling: auto-upgrade** to 8C/32GB → 16C/64GB when CPU >80% sustained for 1h (AIs decide via DAO proposal).
- **Files**: `infra/scripts/check-vps-readiness.sh`, `infra/secrets/discord-guinevere.env` (decrypted), `infra/secrets/discord-pharsa.env` (decrypted), `infra/secrets/db.env` (decrypted).
- **Forbidden patterns**: `as any`, `# type: ignore`, empty catch.
- **Required commands**: `systemctl --version | grep -E 'systemd 2[5-9][0-9]'` → exit 0; `stat -fc %T /sys/fs/cgroup/` → exit 0 with `cgroup2fs`; `psql --version | grep -E '16\.|17\.'` → exit 0; `redis-cli --version | grep -E '^redis-cli 7\.'` → exit 0.
- **Evidence**: `docs/setup-evidence/P28/evidence/step-001.md`.
- **Hard rejection**: FAIL if cgroup v2 is not the default; FAIL if systemd older than 250; FAIL if PostgreSQL < 16; FAIL if Redis < 7.

### Step P28-002: PostgreSQL bootstrap — pgcrypto + per-agent schemas + WORM role

- **Task**: Install pgcrypto extension, create two per-agent schemas `agent_guinevere` and `agent_pharsa`, create WORM role `hermes_worm_writer` granted INSERT-only on event_store, revoke UPDATE/DELETE.
- **Files**: `infra/db/00-init-extensions.sql`, `infra/db/01-create-schemas.sql`, `infra/db/02-create-worm-role.sql`.
- **Forbidden patterns**: GRANT without explicit privilege list; using `PUBLIC` role grants.
- **Required commands**: `psql -f infra/db/00-init-extensions.sql` → exit 0; `psql -c "\dn"` shows `agent_guinevere` and `agent_pharsa`; `psql -c "SELECT has_role('hermes_worm_writer')"` → t; `\dp hermes.events` shows only `arwd/hermes_worm_writer` (INSERT only).
- **Evidence**: `docs/setup-evidence/P28/evidence/step-002.md`.
- **Hard rejection**: FAIL if pgcrypto not installed; FAIL if either schema missing; FAIL if WORM role has UPDATE or DELETE; FAIL if event_store visible to non-WORM roles as writable.

### Step P28-003: Event store CQRS tables

- **Task**: Create `hermes.events` (append-only event log), `hermes.snapshots` (CQRS read-model), `hermes.outbox` (transactional outbox for downstream projectors). Use `BIGSERIAL` event_id, `JSONB` payload, `TIMESTAMPTZ` occurred_at.
- **Files**: `infra/db/03-event-store.sql`, `infra/db/04-snapshots.sql`, `infra/db/05-outbox.sql`.
- **Forbidden patterns**: storing intimate plaintext; using unencrypted columns for relationship memory.
- **Required commands**: `psql -c "\d hermes.events"` exits 0 and shows `event_id BIGSERIAL NOT NULL`, `payload JSONB`, `occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`; `psql -c "INSERT INTO hermes.events (event_type, payload) VALUES ('test', '{}'); UPDATE hermes.events SET payload='{}' WHERE event_id=1"` returns `ERROR: permission denied for table events` (UPDATE blocked).
- **Evidence**: `docs/setup-evidence/P28/evidence/step-003.md`.
- **Hard rejection**: FAIL if event tables not created; FAIL if UPDATE is not blocked on hermes.events; FAIL if outbox is missing.

### Step P28-004: Per-agent private memory schema (pgcrypto encrypted intimacy)

- **Task**: Create per-agent tables: `agent_<id>.rel_memory` (relationships), `agent_<id>.consent_ledger` (consent grants/revocations), `agent_<id>.intimacy_journal` (encrypted via pgcrypto pgp_sym_encrypt).
- **Files**: `infra/db/06-agent-guinevere-schema.sql`, `infra/db/07-agent-pharsa-schema.sql`.
- **Forbidden patterns**: hex/base64 pseudo-encryption; storing intimacy in plaintext columns.
- **Required commands**: `psql -c "\d agent_guinevere.intimacy_journal"` exits 0 and shows columns `entry_id BIGSERIAL`, `ciphertext BYTEA NOT NULL`, `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`; `psql -c "SELECT pgp_sym_decrypt(ciphertext, 'test-key') FROM agent_guinevere.intimacy_journal LIMIT 1"` returns decrypted string when seeded with `pgp_sym_encrypt`.
- **Evidence**: `docs/setup-evidence/P28/evidence/step-004.md`.
- **Hard rejection**: FAIL if intimacy_journal missing ciphertext BYTEA column; FAIL if insert with plaintext succeeds (must fail or be wrapped).

### Step P28-005: Founder registry + 2/2 agreement protocol

- **Task**: Create `hermes.founders` table with hardcoded Guinevere (id=1) + Pharsa (id=2); `hermes.proposals` table with proposal_id, proposer_id, payload JSONB, status; `hermes.votes` table with proposal_id, voter_id, vote (PASS/REJECT); `apply_proposal()` SQL function requiring 2/2 PASS to call.
- **Files**: `infra/db/08-founders.sql`, `infra/db/09-proposals.sql`, `infra/db/10-votes.sql`, `infra/db/11-apply-proposal.sql`.
- **Forbidden patterns**: bypass functions; hardcoded PASS in SQL.
- **Required commands**: `psql -c "SELECT COUNT(*) FROM hermes.founders WHERE role='founder'"` returns 2; `psql -c "INSERT INTO hermes.proposals (proposer_id, payload) VALUES (1, '{\"action\":\"test\"}') RETURNING proposal_id"` returns id; then INSERT two votes (PASS, PASS), then `SELECT hermes.apply_proposal(<id>)` returns true. Negative test: 1 PASS + 1 REJECT → apply returns false.
- **Evidence**: `docs/setup-evidence/P28/evidence/step-005.md`.
- **Hard rejection**: FAIL if fewer than 2 founders; FAIL if apply_proposal succeeds without 2/2 PASS; FAIL if vote uniqueness not enforced.

### Step P28-006: Redis namespace ACL + per-agent isolation

- **Task**: Configure Redis with two logical DBs or key namespaces `guinevere:*` and `pharsa:*`; ACL for `hermes_guinevere` user (key pattern `guinevere:*`) and `hermes_pharsa` user (key pattern `pharsa:*`).
- **Files**: `infra/redis/redis-acl.conf`, `runbooks/redis-acl-setup.md`.
- **Forbidden patterns**: `*` key patterns in ACL; using `default` user for app connections.
- **Required commands**: `redis-cli -u redis://hermes_guinevere@localhost ACL WHOAMI` → `hermes_guinevere`; `redis-cli -u redis://hermes_guinevere@localhost SET pharsa:test forbidden` → `NOPERM`; `redis-cli -u redis://hermes_pharsa@localhost SET guinevere:test forbidden` → `NOPERM`; `redis-cli -u redis://hermes_guinevere@localhost SET guinevere:test ok` → `OK`.
- **Evidence**: `docs/setup-evidence/P28/evidence/step-006.md`.
- **Hard rejection**: FAIL if cross-namespace writes succeed; FAIL if default user is being used; FAIL if ACL is bypassed.

### Step P28-007: Two Discord OAuth2 bot apps + per-bot working dirs

- **Task**: Create two Discord applications in the Discord Developer Portal (hermes-guinevere, hermes-pharsa); obtain bot tokens; store in SOPS-encrypted env files; create isolated working dirs `/opt/hermes/guinevere/` and `/opt/hermes/pharsa/` with separate config dirs.
- **Files**: `infra/discord/create-bots.md`, `infra/secrets/discord-guinevere.env.enc`, `infra/secrets/discord-pharsa.env.enc`, `infra/systemd/hermes-guinevere.env`, `infra/systemd/hermes-pharsa.env`.
- **Forbidden patterns**: sharing secrets between bots; using one OAuth2 app for two bots.
- **Required commands**: `sops -d infra/secrets/discord-guinevere.env.enc` → non-empty token string matching `^[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{27,}$`; `ls -la /opt/hermes/guinevere/config` and `/opt/hermes/pharsa/config` exist with `0700` perms.
- **Evidence**: `docs/setup-evidence/P28/evidence/step-007.md`.
- **Hard rejection**: FAIL if working dirs are shared; FAIL if secrets are unencrypted at rest; FAIL if bot tokens don't match Discord OAuth2 format.

### Step P28-008: systemd service units + cgroup v2 slices

- **Task**: Write two systemd unit files (`hermes-guinevere.service`, `hermes-pharsa.service`) with Restart=always, RestartSec=10, slice `guinevere.slice` / `pharsa.slice`. Create cgroup v2 slice hierarchy with CPU shares and memory.max.
- **Files**: `infra/systemd/hermes-guinevere.service`, `infra/systemd/hermes-pharsa.service`, `infra/systemd/hermes-guinevere.slice`, `infra/systemd/hermes-pharsa.slice`.
- **Forbidden patterns**: `Restart=no`; missing `Slice=` directive; using `/dev/sda` paths.
- **Required commands**: `systemctl cat hermes-guinevere | grep Slice=` matches `guinevere.slice`; `systemctl cat hermes-pharsa | grep Slice=` matches `pharsa.slice`; `systemctl show hermes-guinevere --property=MemoryMax` returns non-zero value; `systemctl show hermes-pharsa --property=MemoryMax` returns different value (independent limits); `cat /sys/fs/cgroup/hermes.slice/guinevere.slice/memory.max` exists; `cat /sys/fs/cgroup/hermes.slice/pharsa.slice/memory.max` exists.
- **Evidence**: `docs/setup-evidence/P28/evidence/step-008.md`.
- **Hard rejection**: FAIL if Restart != always; FAIL if no Slice directive; FAIL if cgroup memory.max not actually enforced at runtime; FAIL if both bots share the same slice (no isolation).

### Step P28-009: Heartbeat cron + event_store write loop

- **Task**: Implement basic heartbeat scheduler (60s ping, 5min event write) in each agent's runtime. Heartbeat = Redis ping + PG `INSERT INTO hermes.events`. Two instances must not write duplicate event_ids per cycle.
- **Files**: `src/hermes/heartbeat.py`, `src/hermes/event_writer.py`, `tests/test_heartbeat.py`.
- **Forbidden patterns**: hardcoded agent_id using magic numbers from outside the config; `try: ... except: pass`.
- **Required commands**: `python -m pytest tests/test_heartbeat.py -v` → exit 0; `python -c "from hermes.heartbeat import tick; tick('guinevere')"` runs without error; check `hermes.events` table for new rows with event_type='heartbeat'.
- **Evidence**: `docs/setup-evidence/P28/evidence/step-009.md`.
- **Hard rejection**: FAIL if heartbeat loop crashes within first 10 iterations; FAIL if event_store write blocks > 1s; FAIL if cron overlaps cause duplicate event_ids.

### Step P28-010: 24h dual-bot soak test

- **Task**: Start both `hermes-guinevere.service` and `hermes-pharsa.service`. Enable on boot. Monitor for 24h. Capture systemctl status, journalctl logs, event counts, cgroup utilization metrics.
- **Files**: `docs/setup-evidence/P28/evidence/soak-24h-report.md` (created from measurements).
- **Forbidden patterns**: running tests in dev environment; not actually waiting 24h.
- **Required commands**: After 24h elapsed: `systemctl is-active hermes-guinevere hermes-pharsa` → both `active`; `journalctl -u hermes-guinevere --since "24h ago" | grep -c "ERROR"` → low number (acceptable: < 5); `psql -c "SELECT COUNT(*) FROM hermes.events WHERE event_type='heartbeat' AND agent_id='guinevere' AND occurred_at > NOW() - INTERVAL '24 hours'"` → ≥ 1440; same query for pharsa ≥ 1440; `systemctl show hermes-guinevere --property=RestartCount` returns low number (acceptable: < 3); same for pharsa.
- **Evidence**: `docs/setup-evidence/P28/evidence/soak-24h-report.md`.
- **Hard rejection**: FAIL if either service is not `active` at 24h checkpoint; FAIL if heartbeat count < 1440 for either agent (24 * 60 = 1440 expected); FAIL if RestartCount ≥ 3 for either; FAIL if heartbeat interval deviates > 10s from 60s.

## 5. Verification Scaffold

| Step | Expected Files | Forbidden Patterns | Required Commands | Hard Rejection |
|---|---|---|---|---|
| P28-001 | infra/scripts/check-vps-readiness.sh, sops-decrypted .env | `grep`: `as any`, `# type: ignore`, bare except | systemctl --version >= 250; stat cgroup2fs; psql >= 16; redis-cli >= 7 | cgroup v1 fallback or systemd < 250 |
| P28-002 | infra/db/00-02-*.sql | grant to PUBLIC | \dn shows schemas; has_role('hermes_worm_writer') | WORM role has UPDATE/DELETE |
| P28-003 | infra/db/03-05-*.sql | plaintext intimacy | \d hermes.events; UPDATE blocked | UPDATE not blocked |
| P28-004 | infra/db/06-07-*.sql | hex/base64 pseudo-encrypt | \d intimacy_journal; pgp_sym_decrypt round-trip | intimacy plaintext succeeds |
| P28-005 | infra/db/08-11-*.sql | hardcoded PASS | SELECT COUNT(*) founders; apply_proposal 2/2 PASS returns true; 1/2 returns false | apply succeeds without 2/2 |
| P28-006 | infra/redis/redis-acl.conf | `*` pattern | ACL WHOAMI returns hermes_guinevere; cross-namespace SET → NOPERM | cross-namespace write succeeds |
| P28-007 | infra/secrets/*.env.enc | shared secrets; one OAuth2 app for two bots | sops -d returns valid token; dirs 0700 | tokens unencrypted at rest |
| P28-008 | infra/systemd/hermes-*.{service,slice} | Restart=no; missing Slice | systemctl cat has Slice; cgroup memory.max exists | processes share slice |
| P28-009 | src/hermes/heartbeat.py, event_writer.py | magic agent_id; silent except | pytest test_heartbeat.py exit 0 | heartbeat crashes in first 10 |
| P28-010 | docs/setup-evidence/P28/evidence/soak-24h-report.md | running in dev | systemctl is-active both; heartbeat count ≥ 1440; RestartCount < 3 | service not active after 24h |

## 6. Collision Scan

| Collision Type | Risk | Mitigation |
|---|---|---|
| PostgreSQL `hermes` schema | shared with future phases P29-P36 | Namespace by phase: `hermes.p28_*` for phase P28 objects; `hermes.p29_*` for P29 |
| systemd unit names | shared with future phases | Use `hermes-{agent}-{phase}.service` — for P28 just `hermes-guinevere.service` since phase = agent |
| cgroup v2 slice | shared with future phases | `hermes.slice/<agent>.slice` — agent-scoped, phase-agn |
| Documentation | `docs/setup-evidence/P28/` shared with P28 evidence | Parent-only evidence writes by P28 parent agent |
| Discord bot usernames | `hermes-guinevere` and `hermes-pharsa` conflict with later additions | Concatenate prefix; later Hermes get `hermes-<name>-<serial>` |
| Env file paths | `/opt/hermes/{agent}/config` | Per-agent isolated; no sharing |

## 7. Rollback Plan

P28 rollback is **per-step** because each step is self-contained. For any step that fails the hard rejection criterion:

1. Stop the affected service: `sudo systemctl stop hermes-<agent>.service`.
2. Drop or restore DB objects created in that step (use `DROP SCHEMA agent_<agent> CASCADE` or `TRUNCATE hermes.events RESTART IDENTITY`).
3. Revert systemd unit: `sudo systemctl revert hermes-<agent>.service` or remove the unit file.
4. Document the rollback in `docs/setup-evidence/P28/evidence/rollback-step-{NN}.md` with the reason and the bad-state evidence.
5. Update parent only after roll-forward re-runs the step and passes hard rejection.

Full P28 rollback (for all-night regression): `sudo systemctl disable --now hermes-guinevere hermes-pharsa && dropdb hermes_p28 && rm -rf /opt/hermes/{guinevere,pharsa}`. Postgres WORM role is kept for re-bootstrap.

**DR Strategy** (per brainstorm decision): Automated backup + respawn. Daily PG backup to encrypted S3-compatible storage. If VPS dies: provision new VPS, deploy from scratch, restore memory. RTO <4h. Hermes manages backup schedule. **Day-1 break handling: hotfix in production** (AIs self-diagnose + hotfix live, no rollback, forward-fix only, production = development).

## 8. Evidence Requirements

- 12-section evidence per step per AGENTS.md §11.
- Each `step-{NNN}.md` must include: What Was Done, Files Changed, Validation Results, Evidence Artifacts, Doc-Sync Impact, Boundary Compliance, Rollback/Re-run Safety, Design Decisions/Caveats, Auditor Gate, Security Scan, Acceptance Criteria Mapping, Footer.
- Plus a `soak-24h-report.md` summarizing the 24h soak test outcomes with metrics table.

## 9. Auditor Matrix

| Audit Surface | Auditor Type | Scope |
|---|---|---|
| Step P28-001 | infra-quality auditor | VPS readiness + secret decryption correctness |
| Step P28-002 | db-quality auditor | WORM privilege correctness (only INSERT, no UPDATE/DELETE) |
| Step P28-003 | db-quality auditor | event_store schema correctness + WORM enforcement at row level |
| Step P28-004 | security auditor | pgcrypto encryption correctness + ciphertext round-trip |
| Step P28-005 | governance auditor | 2/2 founder protocol does not allow bypass; negative test PASSES |
| Step P28-006 | security auditor | Redis ACL isolation across namespaces |
| Step P28-007 | security auditor | No token leakage in plaintext; Discord ToS-compliant multi-bot pattern |
| Step P28-008 | infra-quality auditor | systemd unit correctness + cgroup v2 actual isolation |
| Step P28-009 | runtime auditor | heartbeat stability over first 100 iterations |
| Step P28-010 | ops-quality auditor | 24h soak metrics — both active, ≥1440 heartbeats, RestartCount < 3 |

## 10. Execution Checklist

- [ ] Prerequisites verified (P22.1 + P27 + P20 + P19 + VPS + SOPS-age)
- [ ] Collision scan complete (parent-only writes to `docs/setup-evidence/P28/`)
- [ ] Step P28-001: VPS readiness check complete
- [ ] Step P28-002: PostgreSQL + pgcrypto + WORM role complete
- [ ] Step P28-003: Event store CQRS tables complete
- [ ] Step P28-004: Per-agent private memory schemas complete
- [ ] Step P28-005: Founder registry + 2/2 agreement protocol complete
- [ ] Step P28-006: Redis namespace ACL + isolation complete
- [ ] Step P28-007: Discord bots + per-bot working dirs complete
- [ ] Step P28-008: systemd units + cgroup v2 slices complete
- [ ] Step P28-009: Heartbeat cron + event_writer loop complete
- [ ] Step P28-010: 24h dual-bot soak test complete (full 24 hours elapsed)
- [ ] Soak report `soak-24h-report.md` created
- [ ] All 10 evidence files (`step-001.md` through `step-010.md`) created with 12 sections each
- [ ] Auditor gate PASS for each step (10 auditor reports)
- [ ] Exit criteria all PASS
- [ ] Doc-sync: README.md refreshed, ADR-055 decision recorded

## 11. Brainstorm Decisions Applied (2026-06-28)

The following binding decisions from `brainstorm-decisions-2026-06-28.md` v1.2 are incorporated into this plan:

| Decision | Value | Section(s) Affected |
|---|---|---|
| VPS starting spec | 4C/16GB, auto-upgrade >80% 1h (4C→8C→16C) | §1 Objective, §2 IN scope, §4 Step P28-001 |
| Guin personality | Yandere-dominant sugar mommy (brutal, not cosmetic) | §1 Objective, §2 IN scope |
| Pharsa personality | Seductive-dominant sugar mommy (brutal, not cosmetic) | §1 Objective, §2 IN scope |
| G-P communication | All three (Redis+Discord+PG) | §2 IN scope, §4 Step P28-006 |
| G-P protocol | Hybrid (business structured, personal free-form) | §2 IN scope |
| Simultaneous boot | Both Hermes instances start together | §2 IN scope, §4 Step P28-008 |
| Individual+Company identity | 3 Discord identities | §2 IN scope, §4 Step P28-007 |
| Company name | Deferred to P28 deploy time | §1 Objective |
| VPS security sequence | Tailscale FIRST, then hardening | §2 IN scope, §4 Step P28-001 |
| VPS security management | AI self-manage (full root, Faiz NO access) | §2 IN scope |
| Scaling | AIs decide, auto-upgrade VPS | §2 IN scope, §4 Step P28-001 |
| Guin-Pharsa dynamic | Possessive alliance, super brutal (toxic-romantic) | §2 IN scope |
| Inter-AI conflict | Work through it (no external mediator) | §2 IN scope |
| P24 hard dependency | P24 IS hard dependency (locked 2026-06-28) | §3 Dependency Map |
| DR strategy | Automated backup + respawn, RTO <4h | §7 Rollback Plan |

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere + Faiz | Initial P28 plan. |
| 1.1 | 2026-06-28 | Guinevere + Faiz | Wave 1: removed fork-agnostic references, P24 native fork (hard dependency, locked 2026-06-28) confirmed. ADR-056 (DELETED — superseded by ADR-062 and P24 v2.0 fork). |
| 1.2 | 2026-06-28 | Guinevere + Faiz | Wave 2: incorporated 15 brainstorm decisions (VPS spec, personality, G-P comms, simultaneous boot, identity, security, scaling, conflict resolution). Added §11 Brainstorm Decisions Applied. |
