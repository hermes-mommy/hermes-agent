# P9v2 Evidence — Personal Finance System Implementation

**Date:** 2026-06-09
**Phase:** P9 v2 (Redesigned)
**Last Updated:** 2026-06-09 21:30 WIB

---

## Summary

Complete personal finance management system implemented via chat-based input with realtime dashboard. Direct finance path in Discord adapter bypasses shell hook for deterministic message deletion.

## Components Implemented

### 1. Database Schema ✅
- Schema: `finance` in PostgreSQL (localhost:5433)
- Tables: `accounts`, `transactions`, `debts`, `categories`
- Indexes: 6 indexes for performance
- Default categories: 14 categories (8 expense, 3 income, 1 transfer, 2 others)

### 2. Initial Data ✅
**Accounts (6):**
| Name | Type | Balance |
|---|---|---|
| Trust Wallet | investment | Rp 12,529,100 |
| Stockbit | investment | Rp 3,455,592 |
| OKX | investment | Rp 3,079,000 |
| Sea Bank | bank | Rp 1,879,012 |
| Blu BCA | bank | Rp 23,661 |
| Cash | cash | Rp 10,000 |
| **Total** | | **Rp 20,976,365** |

**Debts (5):**
| Person | Amount | Description |
|---|---|---|
| Shopee PayLater | Rp 4,582,167 | Variable monthly |
| Shopee Pinjam #1 | Rp 333,286 | 1 cicilan lagi |
| Shopee Pinjam #2 | Rp 563,797 | 1 cicilan lagi |
| Shopee Pinjam #3 | Rp 7,894,170 | 10 cicilan lagi |
| GoPayLater | Rp 184,712 | 2 cicilan lagi |
| **Total** | **Rp 13,558,132** | |

### 3. Transaction Parser ✅
- File: `src/finance/parser.py` (294 lines)
- Casual message detection (income/expense/transfer/debt)
- Amount parsing (25rb, 1.5jt, 500k, etc.)
- Category classification (14 categories)
- Confidence scoring

### 4. Database Layer ✅
- File: `src/finance/db.py` (327 lines)
- Account balance management
- Transaction CRUD
- Debt tracking (remaining is generated column: amount - paid)
- Summary queries (today, week, month, categories)

### 5. Hermes Plugin ✅
- File: `src/finance/plugin.py` (221 lines)
- Dashboard data formatting
- Discord embed structure

### 6. Finance Hook ✅
- File: `src/finance/hook.py` (178 lines)
- Process transaction from message content + channel_id + author_id
- Dashboard update trigger via subprocess

### 7. Direct Finance Path (adapter.py) ✅
- **Method:** `_try_finance_intercept()` at lines 4710-4797
- **Called from:** `on_message()` line 854-859, BEFORE `_handle_message()`
- **Channel ID:** `1513833533032894494` (#finance)
- **Full Discord message object available:** channel.id, message.id, author.id, content
- **Flow:**
  1. Check channel_id matches #finance
  2. Filter: content ≥3 chars, not command, has digit
  3. Call `src/finance.hook.get_finance_hook().process()`
  4. On success: `await message.delete()` → return True (short-circuit)
  5. On failure: return False (fall to general flow)
- **Shell hook DISABLED** in config.yaml — no double processing

### 8. Discord Channel ✅
- Channel: `#finance` (ID: 1513833533032894494)
- Topic: "💰 Realtime finance dashboard — Papa laporkan pengeluaran, Mama catat"

### 9. Dashboard Embed ✅
- Message ID: 1513835211522052106
- Content: Full dashboard with accounts, today, week, categories, debts, recent transactions
- Updates in-place when new transactions are recorded
- Script: `scripts/finance_dashboard_update.py`

### 10. Weekly Report ✅
- Cron job: `finance-weekly-report` (Minggu 20:00 WIB)
- Script: `scripts/finance_weekly_report.py`
- Delivery: Discord

---

## How It Works (Updated)

1. **Faiz sends casual message** in #finance: "makan nasi goreng 25rb"
2. **Discord adapter** (`adapter.py:on_message`) receives full message object
3. **Direct intercept** (`_try_finance_intercept()`) catches it BEFORE general conversation flow
4. **Finance hook** (`src/finance/hook.py`) parses and stores transaction
5. **Database** inserts transaction and updates account balance
6. **Dashboard updater** refreshes the embed in #finance
7. **Source message deleted** via `await message.delete()` (deterministic — has message.id)
8. **Returns True** — message does NOT enter general conversation flow

**Non-finance messages:** `_try_finance_intercept()` returns False → falls to `_handle_message()` → normal Hermes flow.

---

## Architecture Decision: Direct Path vs Shell Hook

| Aspect | Shell Hook (OLD) | Direct Path (CURRENT) |
|---|---|---|
| Location | `hermes-config/hooks/finance_hook.py` | `adapter.py:_try_finance_intercept()` |
| Trigger | `pre_llm_call` hook | `on_message` event |
| channel_id | Unreliable (often missing from metadata) | ✅ Deterministic (from message.channel.id) |
| message_id | Unreliable (often missing) | ✅ Deterministic (from message.id) |
| Delete message | ❌ Non-deterministic | ✅ `await message.delete()` |
| Double processing | Risk (if both paths active) | ✅ Shell hook disabled |
| Status | DISABLED | LIVE |

---

## Files

| File | Lines | Purpose |
|---|---|---|
| `src/finance/__init__.py` | ~20 | Module exports |
| `src/finance/parser.py` | 294 | Casual message parser |
| `src/finance/db.py` | 327 | PostgreSQL operations |
| `src/finance/plugin.py` | 221 | Dashboard formatting |
| `src/finance/hook.py` | 178 | Finance processing hook |
| `scripts/finance_dashboard_update.py` | ~310 | Dashboard embed updater |
| `scripts/finance_weekly_report.py` | ~250 | Weekly report generator |
| `docs/designs/p9-personal-finance-v2.md` | ~254 | Design document |
| `adapter.py` (lines 4710-4797) | ~87 | Direct finance intercept |

**Total: ~1,740+ lines of finance code**

---

## Status: ✅ COMPLETE & LIVE

All P9v2 components implemented. Direct finance path active in adapter.py. Shell hook disabled. System is live and processing transactions.
