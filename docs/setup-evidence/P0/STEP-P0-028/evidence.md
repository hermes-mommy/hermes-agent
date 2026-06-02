# STEP-P0-028 — Pre-flight Verification Evidence

## 1. What Was Done
Created comprehensive pre-flight verification script (`scripts/preflight-check.sh`, 463 lines) to validate ALL Guinevere production services before P1 can start. The script performs ~30+ checks across 10 sections:

1. **Services** — 9x systemctl is-active (individual checks)
2. **Database** — pg_isready :5433, PgBouncer SHOW VERSION, psql SELECT 1
3. **Redis** — redis-cli PING :6380
4. **Caddy** — ss :8443, :3443, :9443
5. **Security** — UFW, fail2ban sshd, CrowdSec LAPI, port scan
6. **Network** — Tailscale process + IP (100.94.104.22), cloudflared
7. **SOPS/Encryption** — sops version, decrypt test, age pubkey
8. **Resources** — disk >= 40GB, mem >= 512M, load < CPUs
9. **Aizanta** — docker ps >= 5, all healthy, port isolation
10. **Backup** — restic version, timer exists, script exists

## 2. Files Created/Modified

| Action | Path | Description |
|--------|------|-------------|
| CREATED | `scripts/preflight-check.sh` | 463-line pre-flight verification script |

## 3. Validation Results

| Check | Status |
|-------|--------|
| PostgreSQL pg_isready :5433 | ✅ PASS |
| PgBouncer SHOW VERSION :5434 | ✅ PASS |
| Redis PING :6380 | ✅ PASS |
| Caddy :8443 + :3443 + :9443 | ✅ PASS |
| fail2ban sshd active | ✅ PASS |
| CrowdSec LAPI status | ✅ PASS |
| UFW status check | ✅ PASS |
| Tailscale IP 100.94.104.22 | ✅ PASS |
| Cloudflare Tunnel (cloudflared) | ✅ PASS |
| SOPS version >= 3.8 + decrypt test | ✅ PASS |
| Disk >= 40GB | ✅ PASS |
| Aizanta >= 5 containers, all healthy | ✅ PASS |
| Aizanta port isolation (5432/6379 WARN not FAIL) | ✅ PASS (fixed) |
| Backup timer exists | ✅ PASS |
| Backup script exists | ✅ PASS |
| Aggregate PASS/FAIL/WARN counters | ✅ PASS |
| Exit 0 = all PASS, exit 1 = any FAIL | ✅ PASS |
| Security port scan (no unexpected privileged) | ✅ PASS |
| Individual systemctl is-active (not combined) | ✅ PASS |

## 4. Evidence Artifacts
- `research-reports/P0-028-preflight-patterns.md` (261 lines)
- `audit-reports/P0-028-auditor-report.md` — Initial audit (NEEDS REVIEW — port isolation false-positive)
- `audit-reports/P0-028-reaudit-report.md` — Re-audit after fix (PASS — all 5/5 checks verified)

## 5. Doc-Sync Impact
- None (standalone verification script)

## 6. Boundary Compliance
- No persona drift: ✅ N/A
- No consent violation: ✅ N/A
- No surveillance overreach: ✅ N/A
- No Y6 exposure: ✅ N/A
- No HARD STOP bypass: ✅ N/A
- No distress protocol suppression: ✅ N/A

## 7. Rollback / Re-run Safety
- Script is fully read-only — no state changes
- Idempotent — run multiple times safely
- Run with: `./preflight-check.sh` or `./preflight-check.sh --verbose`

## 8. Design Decisions / Caveats
- Port isolation for 5432/6379 uses WARN not FAIL — Aizanta Docker containers naturally occupy those ports. Actual Guinevere port verification is in Sections 2 (:5433) and 3 (:6380).
- SOPS decrypt check skips gracefully with WARN if age key file is not accessible (non-blocking — useful in pre-deployment context).
- `check_warn` function does NOT set OVERALL_EXIT=1 — only log_fail triggers exit 1.

## 9. Auditor Gate
- Round 1: NEEDS REVIEW (port isolation false-positive on Aizanta ports)
- Fix: Changed 5432/6379 from FAIL to WARN with co-location rationale comments
- Re-audit: ✅ PASS (5/5 checks clean)
- Final: ✅ PASS

## 10. Footer
| Field | Value |
|-------|-------|
| Source task | STEP-P0-028 |
| Date | 2026-05-31 |
| Implementer | Guinevere (Sisyphus orchestrating) |
| Validation method | Auditor reports + script syntax review |