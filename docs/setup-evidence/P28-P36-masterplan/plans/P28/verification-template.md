---
title: "P28 Verification Template — Hermes Society Foundation"
status: "Template — per-step verification scaffold"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P28 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
---

# P28 Verification Template — Hermes Society Foundation

## Verification Scaffold

| Step | Expected Files | Forbidden Patterns | Required Commands | Evidence Path | Hard Rejection |
|---|---|---|---|---|---|
| P28-001 | infra/scripts/check-vps-readiness.sh; sops-decrypted .env files | `grep`: `as any`, `# type: ignore`, bare `except:` | `systemctl --version \| grep -E 'systemd 2[5-9][0-9]'` → exit 0; `stat -fc %T /sys/fs/cgroup/` → `cgroup2fs`; `psql --version \| grep -E '1[67]\.'` → exit 0; `redis-cli --version \| grep -E '^redis-cli 7\.'` → exit 0 | docs/setup-evidence/P28/evidence/step-001.md | FAIL if cgroup v1 fallback; FAIL if systemd < 250; FAIL if PostgreSQL < 16; FAIL if Redis < 7 |
| P28-002 | infra/db/00-init-extensions.sql; 01-create-schemas.sql; 02-create-worm-role.sql | grant to PUBLIC; INSERT privilege without explicit role | `psql -f infra/db/00-init-extensions.sql` → exit 0; `\dn` shows `agent_guinevere` and `agent_pharsa`; `has_role('hermes_worm_writer')` = true; `\dp hermes.events` shows INSERT only | docs/setup-evidence/P28/evidence/step-002.md | FAIL if pgcrypto not installed; FAIL if schemas missing; FAIL if WORM role has UPDATE or DELETE |
| P28-003 | infra/db/03-event-store.sql; 04-snapshots.sql; 05-outbox.sql | raw intimacy fields | `\d hermes.events` shows event_id BIGSERIAL, payload JSONB, occurred_at TIMESTAMPTZ; UPDATE blocked by privilege test | docs/setup-evidence/P28/evidence/step-003.md | FAIL if event tables not created; FAIL if UPDATE not blocked; FAIL if outbox missing |
| P28-004 | infra/db/06-agent-guinevere-schema.sql; 07-agent-pharsa-schema.sql | hex/base64 pseudo-encrypt | `\d agent_guinevere.intimacy_journal` shows ciphertext BYTEA; `pgp_sym_decrypt` round-trip succeeds | docs/setup-evidence/P28/evidence/step-004.md | FAIL if intimacy_journal missing ciphertext BYTEA; FAIL if plaintext insert succeeds |
| P28-005 | infra/db/08-founders.sql; 09-proposals.sql; 10-votes.sql; 11-apply-proposal.sql | hardcoded PASS in SQL; bypass function | `SELECT COUNT(*) FROM hermes.founders WHERE role='founder'` = 2; `apply_proposal(<id>)` returns true with 2/2 PASS; returns false with 1/2 or 0/2 | docs/setup-evidence/P28/evidence/step-005.md | FAIL if fewer than 2 founders; FAIL if apply succeeds without 2/2 PASS; FAIL if vote uniqueness not enforced |
| P28-006 | infra/redis/redis-acl.conf | `*` key pattern; using `default` user | `ACL WHOAMI` returns `hermes_guinevere`/`hermes_pharsa`; cross-namespace SET → `NOPERM`; same-namespace SET → `OK` | docs/setup-evidence/P28/evidence/step-006.md | FAIL if cross-namespace write succeeds; FAIL if default user in use; FAIL if ACL bypassable |
| P28-007 | infra/discord/create-bots.md; infra/secrets/*.env.enc; infra/systemd/*.env | shared secrets; one OAuth2 app for two bots | `sops -d infra/secrets/discord-guinevere.env.enc` returns valid token (regex check); `ls -la /opt/hermes/<agent>/config` shows `0700` perms | docs/setup-evidence/P28/evidence/step-007.md | FAIL if working dirs shared; FAIL if secrets unencrypted at rest; FAIL if bot tokens malformed |
| P28-008 | infra/systemd/hermes-guinevere.service; hermes-pharsa.service; hermes-guinevere.slice; hermes-pharsa.slice | `Restart=no`; missing `Slice=` | `systemctl cat hermes-guinevere \| grep Slice==guinevere.slice`; `systemctl cat hermes-pharsa \| grep Slice==pharsa.slice`; `MemoryMax` differs; `/sys/fs/cgroup/hermes.slice/<agent>.slice/memory.max` exists | docs/setup-evidence/P28/evidence/step-008.md | FAIL if Restart != always; FAIL if no Slice directive; FAIL if cgroup not enforced; FAIL if shared slice |
| P28-009 | src/hermes/heartbeat.py; event_writer.py; tests/test_heartbeat.py | magic agent_id; silent `except:` | `python -m pytest tests/test_heartbeat.py -v` → exit 0; `hermes.events` table gains heartbeat rows | docs/setup-evidence/P28/evidence/step-009.md | FAIL if loop crashes in first 10 iterations; FAIL if INSERT blocks > 1s; FAIL if duplicate event_ids |
| P28-010 | docs/setup-evidence/P28/evidence/soak-24h-report.md (preparation file only) | running in dev; not actually waiting 24h | After 24h elapsed: `systemctl is-active hermes-guinevere hermes-pharsa` → active; heartbeat counts ≥ 1440 per agent; RestartCount < 3 per agent | docs/setup-evidence/P28/evidence/soak-24h-report.md | FAIL if either service not active at 24h; FAIL if heartbeat count < 1440; FAIL if RestartCount ≥ 3 |

## Binary Pass/Fail Criteria

1. VPS readiness (systemd ≥ 250 + cgroup v2 + PostgreSQL ≥ 16 + Redis ≥ 7) — PASS/FAIL
2. pgcrypto extension installed in target DB — PASS/FAIL
3. Per-agent schemas `agent_guinevere` and `agent_pharsa` exist — PASS/FAIL
4. WORM role `hermes_worm_writer` has INSERT-only on `hermes.events` — PASS/FAIL
5. WORM role does NOT have UPDATE or DELETE on `hermes.events` — PASS/FAIL (negative test)
6. `hermes.events` created with BIGSERIAL, JSONB, TIMESTAMPTZ — PASS/FAIL
7. `hermes.outbox` created — PASS/FAIL
8. `agent_<agent>.intimacy_journal` uses BYTEA ciphertext column — PASS/FAIL
9. pgcrypto round-trip decrypts correctly — PASS/FAIL
10. `hermes.founders` table has 2 rows with role='founder' — PASS/FAIL
11. Founder agreement: 2/2 PASS → `apply_proposal` returns true — PASS/FAIL
12. Founder agreement: 1/2 PASS → `apply_proposal` returns false — PASS/FAIL (negative test)
13. Redis ACL: cross-namespace write returns NOPERM — PASS/FAIL (negative test)
14. Two Discord OAuth2 bot apps created with separate tokens — PASS/FAIL
15. Both `/opt/hermes/<agent>/config` dirs are `0700` perms — PASS/FAIL
16. systemd `hermes-guinevere.service` has Slice=guinevere.slice — PASS/FAIL
17. systemd `hermes-pharsa.service` has Slice=pharsa.slice — PASS/FAIL
18. cgroup memory.max enforced at runtime for both slices — PASS/FAIL
19. systemd Restart=always on both units — PASS/FAIL
20. Heartbeat cron writes a row to `hermes.events` every 60s — PASS/FAIL
21. Both agents active for 24h straight — PASS/FAIL
22. Heartbeat count ≥ 1440 per agent over 24h — PASS/FAIL
23. RestartCount < 3 per agent over 24h — PASS/FAIL
24. Heartbeat interval deviation ≤ 10s over 24h — PASS/FAIL

## Runtime Proof Requirements

- psql `SELECT COUNT(*) FROM hermes.events WHERE event_type='heartbeat' AND agent_id='<agent>' AND occurred_at > NOW() - INTERVAL '24 hours'` >= 1440 (full output captured in `step-010.md`).
- redis-cli ACL WHOAMI returns the expected user for each agent (full output captured).
- `pg_dump --table=agent_guinevere.intimacy_journal | grep -v 'bytea'` returns empty (no plaintext leakage in dump).
- `pgp_sym_decrypt(ciphertext, current_setting('hermes.symmetric_key'))` round-trip works in cold boot.
- `systemctl show hermes-guinevere --property=SubState` returns `running` 24h after start.
- `systemctl show hermes-pharsa --property=SubState` returns `running` 24h after start.
- journalctl `journalctl -u hermes-guinevere --since "24 hours ago" --no-pager` shows heartbeat markers at 60s ± 10s.
- Discord gateway audit_writer trace shows both bots' `READY`, `HEARTBEAT_ACK` events across the 24h period.

## Parent Verification Checklist

- [ ] Claimed files exist (`ls infra/db/*.sql infra/systemd/*.{service,slice}` all present)
- [ ] Changed files parent-read (parent cross-checks ≥ 30% of new file bodies against plan §4)
- [ ] `lsp_diagnostics` clean on changed Python files (`src/hermes/heartbeat.py`, `event_writer.py`)
- [ ] Tests pass (`python -m pytest tests/test_heartbeat.py -v`)
- [ ] Evidence paths exist (`docs/setup-evidence/P28/evidence/step-{NNN}.md` for all 10 steps)
- [ ] Auditor reports exist (`docs/setup-evidence/P28/evidence/audits/step-{NNN}-audit.md` for all 10 steps)
- [ ] Safety boundaries preserved (no secret redaction failures, no Y5 escalation, no HARD STOP bypass, no consent revocation yanking)
- [ ] No type suppression (`as any`, `# type: ignore`, `@ts-ignore` absent)
- [ ] No empty catches (`grep -rn "except:" src/hermes/ | grep -v "#" | wc -l` = 0)
- [ ] Soak report prepared (`soak-24h-report.md`) with metrics table
- [ ] Rollback commands documented in plan §7 and tested at least once against a non-prod DB

## Footer

Version 1.0 | Date: 2026-06-28 | Author: Guinevere + Faiz
