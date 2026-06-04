# Deployment Verification Report

> **Date**: 2026-06-03
> **Deployer**: Guinevere (autonomous)
> **VPS**: faiz-prod-01 (100.94.104.22, Tailscale)
> **Scope**: Full sync P7-P8 + conversational handler memory fix

---

## 1. Code Sync

| Item | Status | Details |
|---|---|---|
| Source archive | PASS | 1.3 MB tar (src/, monitoring/, scripts/, systemd/, pyproject.toml) |
| Extraction | PASS | All files extracted to /home/guinevere/code/guinevere/ |
| conversational_handler.py | PASS | 18,910 bytes, deployed |
| bot.py | PASS | 15,678 bytes, deployed |
| compose.monitoring.yml | PASS | 4,887 bytes, deployed |
| Excluded | PASS | .env, *.enc, __pycache__, .venv, .git |

## 2. Dependencies

| Package | Status |
|---|---|
| sentry-sdk[fastapi] | PASS (installed) |
| prometheus-client | PASS (installed) |

## 3. Systemd Services

| Service | State | Notes |
|---|---|---|
| guinevere-9router.service | enabled + running | Pre-existing, not modified |
| guinevere-core.service | enabled + running | **Restarted** with new code. Health: OK |
| guinevere-discord.service | enabled + stopped | **NEW** — needs DISCORD_BOT_TOKEN |
| guinevere-loops.service | disabled | Requires env config |
| guinevere-mcp.service | disabled | Requires env config |
| guinevere-monitoring.service | disabled | Requires Docker compose up |
| guinevere-obscura.service | disabled | Requires env config |
| guinevere-scheduler.service | disabled | Requires env config |
| guinevere-surveillance.service | disabled | Requires env config |

## 4. guinevere-core Verification

```
curl http://127.0.0.1:8000/health
→ {"status": "healthy", "service": "guinevere-core", "version": "0.1.0"}
```

- PID: 1764478 (uvicorn, 2 workers)
- Memory: 144.4M (limit: 2G)
- Slice: guinevere.slice

## 5. Discord Bot Status

| Check | Status |
|---|---|
| Service file installed | PASS — /etc/systemd/system/guinevere-discord.service |
| Service enabled | PASS — auto-start on boot |
| .env.discord created | PASS — placeholder at /home/guinevere/code/guinevere/.env.discord |
| DISCORD_BOT_TOKEN set | **BLOCKED** — requires Faiz to set actual token |
| Bot started | **BLOCKED** — waiting for token |

### To complete Discord bot deployment:

```bash
# SSH to VPS as guinevere user:
echo 'DISCORD_BOT_TOKEN=your_actual_token_here' > /home/guinevere/code/guinevere/.env.discord
chmod 600 /home/guinevere/code/guinevere/.env.discord

# Then start the service:
sudo systemctl start guinevere-discord.service
sudo systemctl status guinevere-discord.service

# Verify bot connected:
journalctl -u guinevere-discord -f --no-pager
```

## 6. Memory Recall Integration

| Check | Status | Details |
|---|---|---|
| assemble_system_prompt_with_memory called | PASS | Step 9 of conversational_handler.py |
| Session factory via bot.get_session_factory() | PASS | Graceful degradation if unavailable |
| EmbeddingService singleton | PASS | Lazy-initialized |
| safe_mode propagated | PASS | From DistressDetector → recall |
| exclude_dnr=True | PASS | Hardcoded in prompt_loader |
| limit=3, token_budget=400 | PASS | Bounded for conversational latency |
| Fallback on error | PASS | Never crashes, falls back to base prompt |

**Note**: Memory recall will activate when the Discord bot starts and connects to PostgreSQL + Redis. The graceful degradation path (base prompt without memories) activates if DATABASE_URL is not set or DB is unreachable.

## 7. Files Changed on VPS

### Created (via deployment):
- `src/discord/conversational_handler.py` (NEW — 459+ lines)
- `src/discord/bot.py` (NEW — 398 lines, was not on VPS)
- `src/discord/cmd_*.py` (11 command files, NEW)
- `src/observability/sentry_integration.py` (NEW)
- `monitoring/` (entire directory — compose, configs, dashboards, alerts)
- `systemd/guinevere-discord.service` (NEW)
- `/etc/systemd/system/guinevere-discord.service` (NEW, installed)
- `/home/guinevere/code/guinevere/.env.discord` (NEW, placeholder)

### Modified (via deployment):
- `src/core/main.py` (Sentry init + monthly report scheduler)
- `src/discord/commands.py` (cost/budget options)
- `src/observability/__init__.py` (exports)
- `pyproject.toml` (new deps)

### Systemd services installed:
- 6 new service files (discord, loops, mcp, monitoring, obscura, scheduler, surveillance)

## 8. Rollback Plan

```bash
# Stop new services:
sudo systemctl stop guinevere-discord
sudo systemctl disable guinevere-discord

# Restart core with previous code (git checkout):
cd /home/guinevere/code/guinevere
git checkout 0497210 -- src/ monitoring/ scripts/ systemd/
sudo systemctl restart guinevere-core

# Remove new service files:
sudo rm /etc/systemd/system/guinevere-{discord,loops,mcp,monitoring,obscura,scheduler,surveillance}.service
sudo systemctl daemon-reload
```

## 9. Summary

| Area | Verdict |
|---|---|
| Code sync | PASS |
| Dependencies | PASS |
| Core API | PASS (healthy) |
| Systemd services | PASS (9 installed) |
| Discord bot | BLOCKED (needs token) |
| Memory recall | READY (activates on bot start) |
| Monitoring stack | NOT STARTED (Docker compose up needed) |

**Overall: DEPLOYED — Discord bot awaiting token configuration.**

---

*Generated 2026-06-03 by Guinevere autonomous deployment.*
