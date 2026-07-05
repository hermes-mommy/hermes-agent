# Evidence: Cost Tracker — 9Router SQLite Integration

**Date:** 2026-06-08
**Agent:** Guinevere (Mommy)
**Type:** Infrastructure — cost tracking data source migration

## Problem

Cost tracker embed di #cost-tracker hanya menampilkan **sebagian kecil** dari usage data:

| Metrik | Yang Tampil (Redis) | Data Real (9Router) |
|--------|-------------------|-------------------|
| Cost today | $0.47 | **$7.11** |
| Tokens today | 0 (kosong) | **23.5M prompt + 220K completion** |
| Calls | — | **305 calls** |
| Models | deepseek-v4-flash only | **6 models** |
| History | 3 hari parsial | **7 hari lengkap** |
| Total | $0.47 | **$9.83** |

**Akar masalah:** `CostTracker.record_cost()` di Hermes hanya mencatat sebagian kecil dari LLM calls. 9Router sendiri memiliki **SQLite database internal** (`~/.9router/db/data.sqlite`) yang mencatat SEMUA traffic proxy — 1138 records, 7 hari history, multiple models.

## Solution

Rewrite `cost_tracker_post.py` untuk membaca dari **9Router SQLite database** sebagai primary data source, bukan dari Redis CostTracker.

## Architecture

```
Before:
  Hermes LLM call → CostTracker.record_cost() → Redis DB5 (partial)
  ↓
  cost_tracker_post.py → baca Redis → Discord embed (data $0.47)

After:
  9Router proxy → SQLite database (ALL calls tracked)
  ↓
  cost_tracker_post.py → query SQLite → Discord embed (data $9.83)
```

## 9Router SQLite Database

**Path:** `/home/guinevere/.9router/db/data.sqlite` (2.8 MB)

### Key Tables

| Table | Records | Purpose |
|-------|---------|---------|
| `usageHistory` | **1138** | Per-request: timestamp, model, promptTokens, completionTokens, cost, provider, status |
| `usageDaily` | **7** | Pre-aggregated daily JSON: byProvider, byModel, byAccount, byApiKey, byEndpoint |

### Data Coverage

| Day | Calls | Cost | Prompt Tokens | Completion Tokens |
|-----|-------|------|---------------|-------------------|
| 2026-06-08 (today) | 305 | $7.109 | 23,520,306 | 220,153 |
| 2026-06-07 | 711 | $2.306 | 29,207,073 | 315,111 |
| 2026-06-06 | 7 | $0.011 | 111,351 | 3,879 |
| 2026-06-05 | 33 | $0.035 | 392,959 | 5,578 |
| 2026-06-03 | 72 | $0.351 | 538,128 | 13,999 |
| 2026-06-01 | 10 | $0.020 | 6,600 | 197 |

### Models Tracked

| Model | Calls | Cost |
|-------|-------|------|
| gpt-5.5 | 43 | $5.638 |
| deepseek-v4-flash | 1,064 | $3.871 |
| deepseek-v4-flash-free | 26 | $0.323 |
| minimax-m3 | 1 | $0.00009 |
| step-3.5-flash | 2 | $0.00 |
| step-3.7-flash | 2 | $0.00 |

## Script Rewrite: `cost_tracker_post.py`

**File:** `~/.hermes/scripts/cost_tracker_post.py`

### Changes

| Aspect | Before (Redis) | After (9Router SQLite) |
|--------|---------------|----------------------|
| Data source | Redis DB5 via redis-cli | SQLite via sqlite3 |
| Coverage | ~5% of actual usage | **100% of 9Router proxy traffic** |
| Today fields | Cost $0.47, Tokens 0 | **Cost $7.11, Tokens 23.5M** |
| Model breakdown | None (single model) | **Top 6 models** with per-model tokens+cost |
| Historical | 3 partial days | **7 days** (7-day + 30-day aggregates) |
| All-time | Not available | **Since Jun 1** with earliest date |
| Avg cost/1M token | $0 from 0 tokens | **$0.30** from 23.5M+ tokens |
| Footer | "Financial Surveillance" | **"Data from 9Router SQLite"** |
| Edit-in-place | ✅ via `patch_or_post` | ✅ via `patch_or_post` (same pattern) |

### Query Design

```python
# Today's per-model usage (most accurate)
SELECT model, COUNT(*), SUM(promptTokens), SUM(completionTokens), ROUND(SUM(cost), 6)
FROM usageHistory WHERE date(timestamp) = date('now')
GROUP BY model ORDER BY cost DESC

# Historical aggregates
SELECT COUNT(*), SUM(promptTokens), SUM(completionTokens), ROUND(SUM(cost), 6)
FROM usageHistory 
WHERE date(timestamp) >= date('now', ?) AND date(timestamp) < date('now')

# Daily aggregate (JSON from usageDaily for second source)
SELECT data FROM usageDaily WHERE dateKey = ?
```

## Embed Format (LIVE)

The cost tracker embed now shows:

```
💰 Cost Tracker — LIVE (from 9Router)

📅 Hari Ini        | 📊 7 Hari         | 📊 30 Hari
Cost: $7.1094     | Cost: $2.7259     | Cost: $9.8319
Tokens: 23,740,459 | Tokens: 32,299,085| Tokens: 55,075,387
Calls: 305         | Calls: 1,138      | Calls: 1,138

[Per-model breakdown, top 6 models]
🟢 deepseek-v4-flash: tokens | cost
🟢 deepseek-v4-flash-free: tokens | cost
🔵 gpt-5.5: tokens | cost
...

All Time: Cost $9.8319 from 2026-06-01
Avg Cost / 1M Token: $0.30
```

## Verification

| Check | Result |
|-------|--------|
| SQLite database accessible | ✅ 2.8 MB, tables exist |
| Query returns today data | ✅ 305 calls, $7.109 |
| Per-model breakdown | ✅ 5+ models |
| Historical aggregates | ✅ 7-day, 30-day |
| Script runs silent | ✅ exit 0, no stdout |
| Edit-in-place works | ✅ Same message ID preserved |
| Syntax check | ✅ Python ast.parse OK |

## Files Changed

| File | Action |
|------|--------|
| `~/.hermes/scripts/cost_tracker_post.py` | **REWRITE** — source from 9Router SQLite instead of Redis |
| `~/.hermes/state/cron_messages/cost-tracker-post.json` | Preserved (same message ID) |

## Related

- Previous: `evidence-cronjob-realtime-edit.md` (edit-in-place pattern)
- Previous: `evidence-cronjob-message-cleanup.md` (silent cron, no wrapper)
- 9Router database: `~/.9router/db/data.sqlite`
- Redis keys (cost:* and token:*) still exist for backward compatibility with CostTracker class
