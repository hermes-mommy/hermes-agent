# W16 — M14 External Channels — Verification Evidence

**Date:** 2026-06-29
**Wave:** W16 (M14 External Channels)
**Branch:** feat/p24-hermes-fork

---

## Files Created (11 files, 3106 lines total)

| File | Lines | Role |
|------|-------|------|
| `guinevere/channels/__init__.py` | 97 | Channel registry, ChannelId/ChannelStatus enums, lazy registration |
| `guinevere/channels/_bridge.py` | 275 | Consciousness bridge (M3), OutboundMessage/SendResult DTOs, `wire(agent)` |
| `guinevere/channels/whatsapp/__init__.py` | 11 | Package re-export |
| `guinevere/channels/whatsapp/adapter.py` | 568 | WhatsApp adapter (Neonize, envelopes, formatter, rate limiter, reconnect) |
| `guinevere/channels/gmail/__init__.py` | 14 | Package re-export |
| `guinevere/channels/gmail/adapter.py` | 510 | Gmail adapter (OAuth2, QuotaTracker, SyncEngine, EmailCategory taxonomy) |
| `guinevere/channels/x/__init__.py` | 14 | Package re-export |
| `guinevere/channels/x/adapter.py` | 410 | X adapter (OAuth2 Bearer, CircuitBreaker, QueueManager, RetryEngine) |
| `guinevere/channels/telegram/__init__.py` | 15 | Package re-export |
| `guinevere/channels/telegram/adapter.py` | 677 | Telegram adapter (httpx Bot API, per-chat throttle, pre-delete snapshot) |
| `tests/p24/test_channels.py` | 515 | 44 tests (imports, CONFIG_MISSING, send actions, envelopes, bridge, registry, forbidden patterns) |

## Files Deleted (84 files)

- `src/channels/` (22 files, ~3368 lines) — WhatsApp channel package
- `src/gmail/` (36 files, ~12723 lines) — Gmail integration package
- `src/x_poster/` (26 files, ~5201 lines) — X/Twitter poster package

## Condensation Summary

- **Source:** 84 files, ~21,292 lines
- **Dest:** 11 files, 3,106 lines
- **Ratio:** 85% reduction (84 -> 11 files, 21k -> 3k lines)
- **Telegram:** Synthesized from `src/life_integrations/adapters/telegram_adapter.py` + `_clients/telegram_client.py`

## Required Commands Output

### VERIFY 1: Import 4 channels
```
$ .venv/Scripts/python.exe -c "from guinevere.channels import whatsapp, gmail, x, telegram; print('4 channels OK')"
4 channels OK
```

### VERIFY 2: pytest
```
$ .venv/Scripts/python.exe -m pytest tests/p24/test_channels.py -q
............................................                             [100%]
44 passed in 0.31s
```

### VERIFY 3: Old dirs deleted
```
$ ls src/channels/ src/gmail/ src/x_poster/ 2>&1
ls: cannot access 'src/channels/': No such file or directory
ls: cannot access 'src/gmail/': No such file or directory
ls: cannot access 'src/x_poster/': No such file or directory
```

### VERIFY 4: No forbidden patterns
```
$ grep -rn 'consent_gate\|hard_stop\|safe_mode\|external.*mcp\|from src\.' guinevere/channels/
(exit 1 — 0 matches)
```

### VERIFY 5: CONFIG_MISSING markers present
```
$ grep -rn 'CONFIG_MISSING' guinevere/channels/ | head -5
guinevere/channels/gmail/adapter.py:8:CONFIG_MISSING: when GmailSettings credentials ...
guinevere/channels/gmail/adapter.py:29:# ---- CONFIG_MISSING detection ----
guinevere/channels/gmail/adapter.py:285:... CONFIG_MISSING is reported at adapter level.
guinevere/channels/gmail/adapter.py:376:CONFIG_MISSING: when Gmail credentials ...
guinevere/channels/gmail/adapter.py:435:... error=f"CONFIG_MISSING: ...
(many more — exit 0)
```

## Key Design Decisions

1. **ChannelSender protocol**: All adapters implement `channel_id`, `is_config_missing`, `send_message()` returning `SendResult`.
2. **CONFIG_MISSING (D2)**: All 4 channels detect missing credentials at construction time and return `CONFIG_MISSING` status.
3. **ConsciousnessBridge**: Unified bridge for M3 autonomous sending across all channels via `OutboundMessage` DTOs.
4. **`wire(agent)`**: Parent-owned agent_init append function — does NOT edit agent_init.py.
5. **No consent/hard_stop**: All safety/governance modules stripped from channel adapters (moved to governance).
6. **No external MCP**: All channels are built-in native Guinevere packages.
7. **Telegram rewrite**: Synthesized from two source implementations using httpx Bot API client with per-chat throttle and 429 retry_after respect.

## Acceptance Checklist

- [x] 4 channels (WhatsApp/Gmail/X/Telegram) all built-in guinevere/channels/
- [x] No external MCP server
- [x] CONFIG_MISSING markers (D2 — no real creds)
- [x] Strip consent + hard_stop from all ported channels
- [x] Clean stale imports (consent_gate, hard_stop_handler, src.hermes.adapter)
- [x] `wire(agent)` (parent-owned agent_init append)
- [x] Consciousness bridge for autonomous sending
- [x] All 44 tests pass
- [x] All verification commands exit 0 (except ls which correctly shows "No such file")
