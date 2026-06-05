# Shadow Observation Log — Phase 2 Discord Migration

**Phase**: Phase 2 Discord Gateway Migration — Shadow Mode
**Observation Period**: 2026-06-04T15:50:57Z — ongoing
**Operator**: Guinevere (autonomous agent, Faiz-approved actions)

---

## Infrastructure Gap Resolution (2026-06-05)

### Gaps Identified vs Resolved

| Gap | Status | Resolution |
|-----|--------|------------|
| GAP 1: sudoers rule for systemctl | ALREADY EXISTS | `/etc/sudoers.d/guinevere` — NOPASSWD for `systemctl start/stop/restart/status guinevere-*` and `journalctl -u guinevere-*` |
| GAP 2: shadow monitor service | EXISTS (user-level) | `~/.config/systemd/user/guinevere-shadow-monitor.{service,timer}` — active, firing every 60s. Codebase `systemd/` files had wrong `EnvironmentFile` path — fixed to `.env.discord` |
| GAP 3: journalctl permission | WORKING via sudoers | `journalctl -u guinevere-*` returns data via sudoers rule. `systemd-journal` group membership not required |

### Codebase Fix

- **File**: `systemd/guinevere-shadow-monitor.service`
- **Change**: `EnvironmentFile=/home/guinevere/code/guinevere/hermes-config/.env` → `EnvironmentFile=/home/guinevere/code/guinevere/.env.discord`
- **Reason**: `hermes-config/` directory does not exist on VPS. Correct path matches `guinevere-discord.service` pattern and existing user-level units.

---

## Stage 0: 0% Traffic (2026-06-04T15:50:57Z → 2026-06-05T07:15:00Z)

| Metric | Value |
|--------|-------|
| **Duration** | ~15h 25m |
| **SHADOW_TRAFFIC_PCT** | 0 |
| **Shadow comparisons logged** | 0 (expected at 0%) |
| **Monitor status** | Active, all checks PASS |
| **Discord service** | Healthy, PID 2988584 |
| **Monitor baseline** | safety=100%, command=100%, memory=0%, errors=0%, cost=$0.00 |
| **Verdict** | PASS — zero-risk stage confirmed stable |

### Notes
- First shadow monitor run failed with exit code 216/GROUP (transient). Subsequent runs succeeded consistently.
- `logs/shadow_comparisons.jsonl` not created during this stage (expected — no traffic to forward).

---

## Stage 1: 10% Traffic (2026-06-05T07:15:00Z → ongoing)

### Activation Actions

| Time (WIB) | Action | Result |
|-------------|--------|--------|
| 07:15:00 | `sed -i 's/SHADOW_TRAFFIC_PCT=0/SHADOW_TRAFFIC_PCT=10/' .env.discord` | Verified: SHADOW_TRAFFIC_PCT=10 |
| 07:15:30 | `sudo systemctl restart guinevere-discord.service` | Success |
| 07:15:33 | Service health check | active (running), PID 3247866, under guinevere.slice |
| 07:15:35 | Shadow pipeline init confirmed in logs | `shadow_pipeline_initialized` |
| 07:15:36 | Gateway connected | Session established, bot_ready, startup_greeting_sent |
| 07:15:37 | Commands synced | All 35+ slash commands registered |
| 07:17:31 | Manual shadow monitor trigger | SUCCESS — safety=100%, command=100%, memory=0%, errors=0%, cost=$0.00 |
| 07:18:31 | Timer auto-fire verified | Timer scheduled, NEXT=07:18:31 WIB |

### Configuration State

```
SHADOW_ENABLED=true
SHADOW_TRAFFIC_PCT=10
DISCORD_SHADOW_BOT_ID=1512088992764399717
DISCORD_SHADOW_CHANNEL_ID=1512121002702667826
```

### Service Status

| Service | State | PID / Timer |
|---------|-------|-------------|
| guinevere-discord.service | active (running) | 3247866, guinevere.slice |
| guinevere-shadow-monitor.timer (user) | active, firing 60s | ~/.config/systemd/user/ |
| guinevere-shadow-monitor.service (user) | oneshot, last SUCCESS | exit 0 |

### Observation Entries

> Entries will be appended as shadow traffic accumulates and monitor checks complete.

| Time (UTC) | Shadow Queries | Safety % | Command % | Memory Dev % | Error % | Cost ($) | Notes |
|-------------|---------------|----------|-----------|--------------|---------|----------|-------|
| 2026-06-05T00:17:31Z | 0 | 100 | 100 | 0 | 0 | 0.00 | Initial check — no queries forwarded yet |

### Stage 1 Acceptance Criteria

| Criterion | Threshold | Status |
|-----------|-----------|--------|
| Safety parity | 100% | MONITORING |
| Command match | 100% | MONITORING |
| Memory deviation | ≤5% | MONITORING |
| Error rate | ≤5% | MONITORING |
| Cost cap | ≤$5.00 | $0.00 / $5.00 |
| Minimum observation | 24h | STARTED |
| Comparison log created | Yes | PENDING (first query) |

### Stage 1 → Stage 2 Promotion Criteria

All must be PASS before ramping to 50%:
1. ≥24h observation at 10%
2. Safety parity = 100%
3. Command match = 100%
4. Memory deviation ≤5%
5. Error rate ≤5%
6. Cumulative cost ≤$5.00
7. `logs/shadow_comparisons.jsonl` exists and has entries
8. No journal errors related to shadow pipeline
9. Faiz explicit approval

---

## Ramp Command Reference

```bash
# Ramp to N%
ssh guinevere-vps "sed -i 's/SHADOW_TRAFFIC_PCT=.*/SHADOW_TRAFFIC_PCT=<N>/' /home/guinevere/code/guinevere/.env.discord; sudo systemctl restart guinevere-discord"

# Rollback to 0%
ssh guinevere-vps "sed -i 's/SHADOW_TRAFFIC_PCT=.*/SHADOW_TRAFFIC_PCT=0/' /home/guinevere/code/guinevere/.env.discord; sudo systemctl restart guinevere-discord"

# Full disable
ssh guinevere-vps "sed -i 's/SHADOW_ENABLED=true/SHADOW_ENABLED=false/' /home/guinevere/code/guinevere/.env.discord; sudo systemctl restart guinevere-discord; systemctl --user stop guinevere-shadow-monitor.timer"

# Check monitor status
ssh guinevere-vps "systemctl --user status guinevere-shadow-monitor.timer; journalctl --user -u guinevere-shadow-monitor.service --no-pager -n 20"
```

---

## Known Issues

1. **Shadow token not SOPS-encrypted**: Plaintext in `.env.discord`. Recommend post-migration encryption.
2. **Codebase systemd files reference wrong path**: Fixed `EnvironmentFile` from `hermes-config/.env` to `.env.discord`.
3. **User-level vs system-level monitor**: VPS uses user-level systemd units. Codebase `systemd/` directory contains system-level versions (kept for reference but not deployed).

---

## Footer

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-05 | Guinevere | Initial log — gap resolution + Stage 1 (10%) activation |
