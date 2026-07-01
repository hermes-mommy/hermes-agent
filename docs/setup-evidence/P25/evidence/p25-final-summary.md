# P25: 9Router VPS Migration — Final Evidence

**Date**: 2026-06-26  
**Status**: COMPLETE — All 14 steps, 2 audit rounds, 3/3 batches PASS

---

## What Was Done

Migrated 9Router (LLM proxy/router) from Windows localhost to VPS (49.12.82.34:39999) as the primary runtime.

## Files Changed

| File | Change |
|---|---|
| `.sisyphus/plans/p25-implementation-plan.md` | Status updated to COMPLETE |
| `~/.config/opencode/opencode.json` | baseURL → `http://100.104.210.75:20128/v1` |
| `~/.claude/settings.json` | ANTHROPIC_BASE_URL → `http://100.104.210.75:20128/v1` |
| VPS: `/etc/systemd/system/9router.service` | Created (source build, custom-server.js, 3.5GB heap) |
| VPS: `/etc/iptables/rules.v4` | Created (ACCEPT tailscale0:20128, DROP venet0:20128) |
| VPS: `/var/lib/9router/db/data.sqlite` | 896K, 92 providerConnections, all 6 config tables imported |
| VPS: `/root/9router/` | Source build of 9Router v0.5.8 from decolua/9router |

## Key Results

| Metric | Value |
|---|---|
| 9Router version | v0.5.8 (source build) |
| Provider connections | 92 (28 providers, 74 models) |
| VPS | 49.12.82.34:39999, Tailscale 100.104.210.75 |
| Health | `/v1/models` returns all models |
| Load test | 16,000 req, 0 errors, CPU 61%, RAM 1.5GB |
| Firewall | Tailscale-only (ACCEPT tailscale0, DROP venet0) |
| Public access | BLOCKED ✅ |
| S3 backup | restic snapshot 18b1e573, 896KB, tagged p25-9router-migration |
| Local 9Router | Kept alive per Faiz |

## Audit Results

| Round | Batch A (S1-S5) | Batch B (S6-S9) | Batch C (S10-S14) |
|---|---|---|---|
| R1 | NEEDS REVIEW (2/5) | NEEDS REVIEW (3/4) | NEEDS REVIEW (5/5, 1 FAIL) |
| R2 | PASS (5/5) | PASS (4/4) | PASS (5/5) |

## Evidence Artifacts

| Step | Evidence |
|---|---|
| S1 | `step1-export.txt` — 92 providerConnections, 8 tables |
| S5 | `step5-verify.txt` — Row counts verified, PRAGMA ok, migrate.sql deleted |
| S10 | `step10-firewall.txt` — iptables rules, persisted |
| S11 | `step11-access-test.txt` — Localhost PASS, Tailscale PASS, public BLOCKED |
| S12 | `step12-endpoints.txt` — opencode.json + settings.json updated |
| S13 | `step13-verify.txt` — Real model request (mimo-v2.5-pro, 2272 tokens) |
| S14 | `step14-shutdown.txt` — Local 9Router kept alive per operator |

## Boundary Compliance

- No secrets in evidence (API key placeholder `<API_KEY>` used)
- No type suppression, no empty catches
- No destructive ops without approval
- Firewall add-only (never reset)
- SSH key auth only (no plaintext passwords)

## Design Decisions

- Source build instead of npm (OpenVZ no Docker, node:sqlite built-in)
- custom-server.js directly (not CLI wrapper, X-Forwarded-For stripping)
- 3.5GB heap (user approved, 3.9GB total VPS RAM)
- Tailscale-only access (no public internet exposure)
- Local 9Router kept alive (operator instruction)

## Caveats

- `tailscale0` ACCEPT rule is no-op in OpenVZ userspace-networking (venet0 DROP is the effective rule)
- Local 9Router still running on port 20128 (PID may respawn)
- S3 endpoint uses is3.cloudhost.id (idcloudhost S3-compatible)
- Only providerConnections config migrated (not usage history, request details, legacy JSON)

## Auditor Gate

- R1: 3 auditors, 3 reports, all findings documented
- R2: 3 re-auditors, 3 reports, ALL PASS
- No remaining findings
- Reports: `audit-reports/P25/batch-*-r2.md`

## Acceptance Criteria

| Criteria | Status |
|---|---|
| 9Router v0.5.8 running on VPS | ✅ |
| 92 providerConnections imported | ✅ |
| /v1/models returns all models | ✅ |
| Client endpoints updated | ✅ |
| Tailscale-only access | ✅ |
| Public internet blocked | ✅ |
| S3 backup exists | ✅ |
| 2 audit rounds complete | ✅ |
| All batches PASS | ✅ |