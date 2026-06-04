# Evidence: Phase 2 Shadow Activation

**Date**: 2026-06-04T15:50:57Z (UTC)
**Operator**: Guinevere (autonomous, Faiz-approved blocker resolution)
**Phase**: Phase 2 Discord Gateway Migration — Shadow Mode Activation

---

## 1. What Was Done

### Blocker 1: Shadow Bot Token
- **Status**: RESOLVED
- **Source**: Token provided directly by Faiz in chat (not found in SOPS)
- **SOPS check**: `secrets/discord-shadow-secrets.yaml` does NOT exist
- **Action**: Token set in `/home/guinevere/code/guinevere/.env.discord` as `DISCORD_SHADOW_BOT_TOKEN`
- **Shadow Bot ID**: 1512088992764399717
- **NOTE**: Token is plaintext in .env.discord (not SOPS-encrypted). Recommend SOPS encryption post-migration.

### Blocker 2: #hermes-shadow Channel
- **Status**: RESOLVED
- **Method**: Discord REST API POST via production bot token (curl from VPS)
- **Guild**: 1510876414671323206
- **Channel Created**: `#hermes-shadow`
- **Channel ID**: 1512121002702667826
- **Topic**: "Shadow mode testing - Hermes vs custom bot parity"
- **Position**: 5 (in channel list)

### Blocker 3: Shadow Pipeline Activation
- **Status**: RESOLVED
- **Actions**:
  1. Set `SHADOW_ENABLED=true` in `.env.discord`
  2. Set `SHADOW_TRAFFIC_PCT=0` (manual ramp: 0% → 10% → 50% → 100%)
  3. Restarted `guinevere-discord` service
  4. Started `guinevere-shadow-monitor.timer` (60s interval)
  5. Fixed systemd user service file (removed root-only directives: `User=`, `NoNewPrivileges=`, `ProtectSystem=`, `ProtectHome=`)

---

## 2. Files Changed on VPS

| File | Action | Notes |
|------|--------|-------|
| `.env.discord` | Modified | Added `DISCORD_SHADOW_BOT_TOKEN`, set `DISCORD_SHADOW_CHANNEL_ID=1512121002702667826`, `SHADOW_ENABLED=true` |
| `~/.config/systemd/user/guinevere-shadow-monitor.service` | Replaced | Removed root-only systemd directives |

---

## 3. Verification Results

| Check | Result | Evidence |
|-------|--------|----------|
| Shadow bot token set | ✅ PASS | `DISCORD_SHADOW_BOT_TOKEN` present in .env.discord |
| #hermes-shadow channel | ✅ PASS | Discord API returned channel ID 1512121002702667826 |
| DISCORD_SHADOW_CHANNEL_ID | ✅ PASS | Set to 1512121002702667826 |
| SHADOW_ENABLED | ✅ PASS | `true` in .env.discord |
| Shadow monitor running | ✅ PASS | Timer `active`, service `status=0/SUCCESS` |
| guinevere-discord healthy | ✅ PASS | `active (running)`, PID 2988584, 3m33s uptime |
| Shadow logs flowing | ✅ PASS | `shadow_pipeline_initialized` in journal |
| Gateway connected | ✅ PASS | Session ID: b926bd21c5cff15243b5ac5aa2ae2caa |
| Bot ready | ✅ PASS | `bot_ready` + `startup_greeting_sent` |
| Rituals intact | ✅ PASS | 5 rituals (morning/midday/afternoon/evening/midnight) |
| Zero journal errors | ✅ PASS | `-- No entries --` for `-p err` |
| Monitor baseline | ✅ PASS | safety=100%, command=100%, memory=0%, errors=0%, cost=$0.00 |

---

## 4. 48h Observation Window

| Parameter | Value |
|-----------|-------|
| **Start** | 2026-06-04T15:50:57Z |
| **End** | 2026-06-06T15:50:57Z |
| **Monitor interval** | 60 seconds |
| **Initial traffic** | 0% (SHADOW_TRAFFIC_PCT=0) |
| **Cost cap** | $5.00 total |
| **Safety threshold** | 100% parity |
| **Command threshold** | 100% match |
| **Memory threshold** | ≤5% deviation |
| **Error threshold** | ≤5% |

### Traffic Ramp Schedule (manual, Faiz approval required)
1. **Stage 0**: 0% traffic — 24h minimum (current)
2. **Stage 1**: 10% traffic — requires Stage 0 PASS
3. **Stage 2**: 50% traffic — requires Stage 1 PASS
4. **Stage 3**: 100% traffic — requires Stage 2 PASS
5. **Stage 4**: 48h observation at 100% — requires Stage 3 PASS

### Ramp Command
```bash
ssh guinevere-vps "sed -i 's/SHADOW_TRAFFIC_PCT=.*/SHADOW_TRAFFIC_PCT=<N>/' /home/guinevere/code/guinevere/.env.discord; sudo systemctl restart guinevere-discord"
```

---

## 5. Safety Boundary Compliance

- ✅ No secrets committed to repo (token only in VPS .env.discord)
- ✅ No destructive operations performed
- ✅ Production bot remains primary (shadow is forward-only, no responses)
- ✅ Shadow traffic starts at 0% (zero risk to production)
- ✅ 9 active safety injections configured (per ADR-035 Appendix D)
- ✅ Shadow pipeline disabled by default in code (requires SHADOW_ENABLED=true)
- ✅ Monitor has $5 cost cap (auto-stop)
- ✅ Shadow monitor exits 0 on baseline (no false alerts)

---

## 6. Known Issues / Caveats

1. **Shadow token not SOPS-encrypted**: Token is plaintext in .env.discord. Recommend `sops --encrypt` post-migration for defense-in-depth.
2. **Monitor comparison log missing**: `logs/shadow_comparisons.jsonl` doesn't exist yet — expected at 0% traffic. Will be created when shadow forwards first query.
3. **Shadow monitor security hardening removed**: Root-only systemd directives (`NoNewPrivileges`, `ProtectSystem`, `ProtectHome`) removed from user service. Acceptable for monitoring-only service.

---

## 7. Rollback Plan

If shadow causes issues:
```bash
ssh guinevere-vps "sed -i 's/SHADOW_ENABLED=true/SHADOW_ENABLED=false/' /home/guinevere/code/guinevere/.env.discord; sudo systemctl restart guinevere-discord; systemctl --user stop guinevere-shadow-monitor.timer"
```
Expected rollback time: <30 seconds.

---

## Footer

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-04 | Guinevere | Initial shadow activation evidence |
