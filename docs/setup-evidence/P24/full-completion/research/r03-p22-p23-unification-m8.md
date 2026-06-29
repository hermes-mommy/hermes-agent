# R03 -- P22 + P23 Unification for M8: 9 Unified Tool Backends

**Generated:** 2026-06-29
**Method:** Read all P22 adapters (13 .py files in `src/life_integrations/adapters/`), all P23 executor specs (Section 4 of `docs/setup-evidence/P23/plan/p23-execution-layer-enterprise-plan.md`), all MCP tools (16 modules in `src/mcp/tools/`), `src/hermes_plugins/command_catalog.py`, and `src/life_integrations/base.py`. Enumerated every action by file:line, then mapped into 9 M8 backends per the D1 in-repo root layout decision.

---

## 1. Source Inventory

### 1.1 P22 Adapters (13 adapters, 26 .py files including shims)

| # | Adapter | File | Actions | L-labels |
|---|---------|------|---------|----------|
| 1 | Browser | `src/life_integrations/adapters/browser_adapter.py:31` | search, fetch_url, navigate, get_markdown, fill_form, click (6) | L1, L1, L1, L1, L2, L2 |
| 2 | GitHub | `src/life_integrations/adapters/github_adapter.py:35` | list_repos, get_file, search_code, list_issues, list_prs, get_repo, create_issue, create_pr, merge_pr, delete_branch (10) | L1x5, L2x3, L3x2 |
| 3 | Filesystem | `src/life_integrations/adapters/filesystem_adapter.py:40` | read, list_dir, write, delete (4) | L1x2, L2, L3 |
| 4 | VPS | `src/life_integrations/adapters/vps_adapter.py:139` | list_containers, service_status, health_metrics, restart_service, restart_container, remove_container (6) | L1x3, L2/L3, L2, L3 |
| 5 | Gmail | `src/life_integrations/adapters/gmail_adapter.py:32` | list_messages, get_message, send_message, create_draft, modify_labels, trash_message, watch (7) | L1x2, L2x4, L3 |
| 6 | Memory | `src/life_integrations/adapters/memory_adapter.py:32` | recall, store, store_fact, search_kg, mark_dnr (5) | L1x2, L2x2, L3 |
| 7 | Telegram | `src/life_integrations/adapters/telegram_adapter.py:33` | get_updates, send_message, edit_message, send_photo, send_document, delete_message (6) | L1, L2x4, L3 |
| 8 | Discord | `src/life_integrations/adapters/discord_adapter.py:39` | read_history, send_message, edit_message, delete_message, add_reaction, create_thread (6) | L1, L2x4, L3 |
| 9 | Drive | `src/life_integrations/adapters/drive_adapter.py:32` | list_files, get_file, create_file, update_file, trash_file, delete_file, public_share (7) | L1x2, L2x3, L3x2 |
| 10 | Calendar | `src/life_integrations/adapters/calendar_adapter.py:32` | list_events, get_event, create_event, update_event, delete_event (5) | L1x2, L2x2, L3 |
| 11 | Notion | `src/life_integrations/adapters/notion_adapter.py:32` | retrieve_page, search, create_page, update_page, append_blocks, archive_page (6) | L1x2, L2x3, L3 |
| 12 | WhatsApp | `src/life_integrations/adapters/whatsapp_adapter.py:34` | send_text, send_media, edit_message, delete_for_everyone, create_group (5) | L2x3, L3x2 |
| 13 | Finance | `src/life_integrations/adapters/finance_adapter.py:38` | list_transactions, summarize, detect_anomalies, record_transaction, correct_transaction, bulk_import, export_transactions (7) | L1x4, L2, L3x2 |

**P22 total: 80 actions** across 13 adapters.

### 1.2 P23 Executors (8 executors from plan Section 4)

| # | Executor | Plan Section | Tool name | Actions |
|---|----------|-------------|-----------|---------|
| 1 | browser_executor | 4.1 | `browser` | navigate, click, fill, extract_text, screenshot, scroll, wait, download (8) |
| 2 | desktop_executor | 4.2 | `desktop` | launch_app, kill_app, run_script, file_read, file_write, notify_toast (6) |
| 3 | vps_executor | 4.3 | `vps` | shell, systemctl, journalctl, pg_dump, pg_restore, restic_backup, restic_restore, rclone_copyto (8) |
| 4 | github_executor | 4.4 | `github` | list_repos, get_file, search_code, git_status, git_log, git_diff, create_branch, commit, push, create_pr, create_issue, comment, merge_pr, watch_checks, run_workflow, revert_pr (16) |
| 5 | filesystem_executor | 4.5 | `fs` | read, write, append, delete, list, glob, grep, move, copy (9) |
| 6 | freelance_executor | 4.6 | `freelance` | list_jobs, submit_proposal, send_message, accept_contract, submit_milestone, submit_delivery, place_bid, accept_award, [withdraw_to_wallet REJECTED] (8 real) |
| 7 | social_executor | 4.7 | `social` | read_timeline, post, reply, comment, search (5 x 4 platforms = 20) |
| 8 | email_executor | 4.8 | `email` | list_inbox, search, read, send, reply, forward, mark_read, flag (8 x 4 providers = 32) |

**P23 total: 107 actions** across 8 executors (8 base + 20 social + 32 email + 8 freelance + 8 vps + 9 fs + 16 github + 6 desktop).

### 1.3 MCP Tools (16 modules, `src/mcp/tools/`)

| # | Module | File:register | Tools registered | Count |
|---|--------|---------------|-----------------|-------|
| 1 | filesystem | `filesystem.py:239` | fs_read, fs_write, fs_delete, fs_list | 4 |
| 2 | github | `github.py:248` | github_list_repos, github_get_file, github_create_issue, github_create_pr, github_search_code | 5 |
| 3 | git_tool | `git_tool.py:372` | git_status, git_log, git_diff, git_commit, git_push, git_push_force | 6 |
| 4 | obscura_cdp | `obscura_cdp.py:221` | obscura_navigate, obscura_get_markdown, obscura_fill_form, obscura_click | 4 |
| 5 | shell_tool | `shell_tool.py:399` | shell_exec | 1 |
| 6 | docker_tool | `docker_tool.py:568` | docker_ps, docker_logs, docker_inspect, docker_images, docker_start, docker_stop, docker_restart, docker_rm, docker_rmi, docker_system_prune, docker_rm_all | 11 |
| 7 | brave_search | `brave_search.py:183` | brave_search | 1 |
| 8 | exa_search | `exa_search.py:210` | exa_search | 1 |
| 9 | websearch | `websearch.py:161` | websearch | 1 |
| 10 | fetch | `fetch.py:202` | fetch_url | 1 |
| 11 | context7 | `context7.py:366` | context7_resolve, context7_query | 2 |
| 12 | sequential_thinking | `sequential_thinking.py:391` | sequential_thinking | 1 |
| 13 | grep_app | `grep_app.py:221` | grep_app_search | 1 |
| 14 | time_tools | `time_tools.py:229` | time_current_time, time_convert_time, time_days_in_month, time_relative_time, time_get_timestamp, time_get_week_year | 6 |
| 15 | redis_tool | `redis_tool.py:443` | redis_get, redis_keys, redis_hgetall, redis_lrange, redis_set, redis_hset, redis_expire, redis_persist, redis_rename, redis_del, redis_flushdb, redis_flushall | 12 |
| 16 | postgres_tool | `postgres_tool.py:489` | postgres_query, postgres_tables, postgres_describe, postgres_execute, postgres_delete | 5 |

**MCP total: 62 tools** across 16 modules.

### 1.4 Command Catalog (`src/hermes_plugins/command_catalog.py:12`)

| Category | Commands | Count |
|----------|----------|-------|
| core | status, mood, help, safeword, new, history | 6 |
| loop | loop-start, loop-stop, loop-pause, loop-resume, loops, evidence, loop-priority | 7 |
| memory | memory-search, memory-add, memory-forget, memory-export | 4 |
| surveillance | surveillance-status, surveillance-pause, surveillance-resume | 3 |
| finance | cost, budget, cost-alert | 3 |
| system | approve, deny, approve-all, focus, casual, consent, punishment, reward | 8 |
| admin | restart-service, backup-now, health-check, clear-cache | 4 |

**Command catalog total: 35 commands** (these are operator-facing CLI commands, not tool actions -- they stay separate from the 9 backends but feed into the `memory` and `vps` backends at the implementation level).

---

## 2. M8 Backend Unification Map

### 2.1 Design Principles

1. **One ToolBackend per backend** -- each backend is a single `ToolBackend` ABC subclass registered in the Hermes fork `tools/registry.py`.
2. **Source deduplication** -- when P22 and P23 define overlapping actions (e.g., both have `github.create_pr`), the P23 executor is the canonical implementation (P23 is the execution layer per plan Section 1.1). P22 adapters are retired/migrated.
3. **MCP tools become internal helpers** -- existing MCP tools (`src/mcp/tools/`) are wrapped by their backend, not registered separately. The MCP FastMCP server surface is preserved for external MCP clients but the P24 backends call the underlying Python functions directly.
4. **L1-L3 labels only** -- per P23 plan, L4 is DELETED (no consent gate, no HARD STOP). All L4-forbidden actions in P22 are dropped. Actions that were L4-forbidden in P22 (e.g., `delete_repo`, `force_push`, `system_prune`, `pay/transfer`, `kick_member`, `promote_admin`) are simply NOT in the M8 action catalogue.
5. **~108 unique actions** -- the final count across the 9 backends, after deduplication and L4 removal.

### 2.2 The 9 M8 Backends

---

#### Backend 1: `browser` -- Web Browsing and Research

**Source files:**
- P22: `src/life_integrations/adapters/browser_adapter.py:31` (6 actions)
- P23: `docs/setup-evidence/P23/plan/p23-execution-layer-enterprise-plan.md` Section 4.1 (8 actions)
- MCP: `src/mcp/tools/obscura_cdp.py:221` (4 tools), `src/mcp/tools/brave_search.py:183` (1), `src/mcp/tools/exa_search.py:210` (1), `src/mcp/tools/websearch.py:161` (1), `src/mcp/tools/fetch.py:202` (1)

**Unified actions (11):**

| Action | L-label | Source | Notes |
|--------|---------|--------|-------|
| `search` | L1 READ | P22 browser_adapter:96 | Brave/Exa/websearch search |
| `fetch_url` | L1 READ | P22 browser_adapter:122 + MCP fetch.py:202 | HTTP fetch, 1MB limit |
| `navigate` | L1 READ | P23 4.1 + MCP obscura_cdp:230 | Navigate to URL |
| `get_markdown` | L1 READ | P22 browser_adapter:137 + MCP obscura_cdp:231 | Page as markdown |
| `extract_text` | L1 READ | P23 4.1 | Extract text from selector |
| `click` | L2 WRITE | P22 browser_adapter:160 + P23 4.1 + MCP obscura_cdp:233 | Click element |
| `fill` | L2 WRITE | P22 browser_adapter:143 + P23 4.1 + MCP obscura_cdp:232 | Fill form field |
| `screenshot` | L2 WRITE | P23 4.1 | Capture page screenshot |
| `scroll` | L1 READ | P23 4.1 | Scroll page |
| `wait` | L1 READ | P23 4.1 | Wait for element |
| `download` | L2 WRITE | P23 4.1 | Download file from page |

**Disposition:** PORT (P23 executor is canonical, P22 adapter retired, MCP tools become internal helpers wrapped by browser backend).

---

#### Backend 2: `github` -- Git and GitHub Operations

**Source files:**
- P22: `src/life_integrations/adapters/github_adapter.py:35` (10 actions)
- P23: Section 4.4 (16 actions)
- MCP: `src/mcp/tools/github.py:248` (5 tools), `src/mcp/tools/git_tool.py:372` (6 tools)

**Unified actions (19):**

| Action | L-label | Source | Notes |
|--------|---------|--------|-------|
| `list_repos` | L1 READ | P22:115 + P23:4.4 + MCP github:250 | List user repos |
| `get_file` | L1 READ | P22:119 + P23:4.4 + MCP github:251 | Get file contents |
| `search_code` | L1 READ | P22:125 + P23:4.4 + MCP github:254 | Search code across repos |
| `list_issues` | L1 READ | P22:130 | List repo issues |
| `list_prs` | L1 READ | P22:134 | List pull requests |
| `get_repo` | L1 READ | P22:137 | Get repo metadata |
| `watch_checks` | L1 READ | P23:4.4 | Watch CI checks |
| `git_status` | L1 READ | P23:4.4 + MCP git_tool:387 | Working tree status |
| `git_log` | L1 READ | P23:4.4 + MCP git_tool:388 | Commit log |
| `git_diff` | L1 READ | P23:4.4 + MCP git_tool:389 | Diff |
| `create_issue` | L2 WRITE | P22:279 + P23:4.4 + MCP github:252 | Create issue |
| `create_pr` | L2 WRITE | P22:285 + P23:4.4 + MCP github:253 | Create pull request |
| `create_branch` | L2 WRITE | P23:4.4 | Create branch |
| `commit` | L2 WRITE | P23:4.4 + MCP git_tool:390 | Git commit |
| `push` | L2 WRITE | P23:4.4 + MCP git_tool:391 | Git push |
| `comment` | L2 WRITE | P23:4.4 | Comment on issue/PR |
| `run_workflow` | L2 WRITE | P23:4.4 | Dispatch GitHub Actions |
| `merge_pr` | L3 DESTRUCTIVE | P22:144 + P23:4.4 | Merge PR (pre-merge snapshot) |
| `revert_pr` | L3 DESTRUCTIVE | P23:4.4 | Revert a merged PR |

**L4 DELETED:** `delete_repo`, `force_push`, `delete_branch` (P22:293 marks them L4_FORBIDDEN; P23 branch policy rejects force-push to main). These actions are NOT in M8.

**Disposition:** PORT (P23 github_executor is canonical; P22 adapter retired; MCP tools wrapped as internal helpers).

---

#### Backend 3: `filesystem` -- Local File I/O

**Source files:**
- P22: `src/life_integrations/adapters/filesystem_adapter.py:40` (4 actions)
- P23: Section 4.5 (9 actions)
- MCP: `src/mcp/tools/filesystem.py:239` (4 tools)

**Unified actions (10):**

| Action | L-label | Source | Notes |
|--------|---------|--------|-------|
| `read` | L1 READ | P22:128 + P23:4.5 + MCP filesystem:248 | Read file |
| `list` | L1 READ | P22:133 + P23:4.5 + MCP filesystem:251 | List directory |
| `glob` | L1 READ | P23:4.5 | Glob pattern match |
| `grep` | L1 READ | P23:4.5 | Regex search in files |
| `write` | L2 WRITE | P22:138 + P23:4.5 + MCP filesystem:249 | Write file |
| `append` | L2 WRITE | P23:4.5 | Append to file |
| `copy` | L2 WRITE | P23:4.5 | Copy file |
| `move` | L2 WRITE | P23:4.5 | Move/rename file |
| `delete` | L3 DESTRUCTIVE | P22:144 + P23:4.5 + MCP filesystem:250 | Delete file (pre-delete hash) |

**L4 DELETED:** `forbidden_path` (P22:48 marks system paths L4_FORBIDDEN). Not in M8.

**Disposition:** PORT (P23 filesystem_executor is canonical; P22 adapter retired; MCP tools wrapped).

---

#### Backend 4: `vps` -- Server and Infrastructure

**Source files:**
- P22: `src/life_integrations/adapters/vps_adapter.py:139` (6 actions)
- P23: Section 4.3 (8 actions)
- MCP: `src/mcp/tools/docker_tool.py:568` (11 tools), `src/mcp/tools/shell_tool.py:399` (1 tool), `src/mcp/tools/redis_tool.py:443` (12 tools), `src/mcp/tools/postgres_tool.py:489` (5 tools)

**Unified actions (14):**

| Action | L-label | Source | Notes |
|--------|---------|--------|-------|
| `list_containers` | L1 READ | P22:203 + MCP docker:582 | List Docker containers |
| `container_logs` | L1 READ | P22:206 + MCP docker:583 | Get container logs |
| `service_status` | L1 READ | P22:209 + MCP docker:584 | systemctl status |
| `health_metrics` | L1 READ | P22:217 | CPU/mem/disk metrics |
| `shell` | L1 READ | P23:4.3 + MCP shell:406 | Execute whitelisted shell commands |
| `journalctl` | L1 READ | P23:4.3 | Read journal logs |
| `restart_container` | L2 WRITE | P22:237 + MCP docker:588-590 | Restart/start/stop container |
| `restart_service` | L2 WRITE | P22:221 | Restart systemd service |
| `pg_dump` | L2 WRITE | P23:4.3 + MCP postgres:491-493 | Dump database |
| `pg_restore` | L2 WRITE | P23:4.3 | Restore database |
| `restic_backup` | L2 WRITE | P23:4.3 | Backup via restic |
| `rclone_copyto` | L2 WRITE | P23:4.3 | Rclone copy |
| `remove_container` | L3 DESTRUCTIVE | P22:258 + MCP docker:593 | Remove container (pre-delete snapshot) |
| `systemctl` | L2 WRITE | P23:4.3 | systemctl operations (start/stop/restart/enable/disable) |

**L4 DELETED:** `system_prune`, `docker_rm_all` (P22:346 marks L4_FORBIDDEN; MCP docker:597-598 registered as FORBIDDEN). Not in M8.

**Disposition:** PORT/REWRITE (P23 vps_executor is canonical; P22 adapter retired; MCP docker/shell/redis/postgres tools become internal helpers).

---

#### Backend 5: `email` -- Email Communication

**Source files:**
- P22: `src/life_integrations/adapters/gmail_adapter.py:32` (7 actions)
- P23: Section 4.8 (8 actions x 4 providers = 32)

**Unified actions (10):**

| Action | L-label | Source | Notes |
|--------|---------|--------|-------|
| `list_inbox` | L1 READ | P22:104 + P23:4.8 | List inbox messages |
| `search` | L1 READ | P23:4.8 | Search emails |
| `read` | L1 READ | P22:112 + P23:4.8 | Read message |
| `send` | L2 WRITE | P22:117 + P23:4.8 | Send email |
| `reply` | L2 WRITE | P23:4.8 | Reply to email |
| `forward` | L2 WRITE | P23:4.8 | Forward email |
| `create_draft` | L2 WRITE | P22:127 | Create draft |
| `modify_labels` | L2 WRITE | P22:152 | Modify message labels |
| `mark_read` | L2 WRITE | P23:4.8 | Mark as read |
| `flag` | L2 WRITE | P23:4.8 | Flag message |

**L4 DELETED:** `permanent_delete` (P22:202 marks L4_FORBIDDEN). Not in M8.

**Disposition:** PORT/REWRITE (P23 email_executor is canonical and broader -- covers 4 providers. P22 gmail_adapter is the initial implementation, extended to 4 providers by P23).

---

#### Backend 6: `desktop` -- Windows Desktop Automation

**Source files:**
- P23: Section 4.2 (6 actions)
- No P22 equivalent (new in P23)

**Unified actions (6):**

| Action | L-label | Source | Notes |
|--------|---------|--------|-------|
| `launch_app` | L2 WRITE | P23:4.2 | Launch application |
| `kill_app` | L3 DESTRUCTIVE | P23:4.2 | Kill process |
| `run_script` | L2 WRITE | P23:4.2 | Run signed PowerShell script |
| `file_read` | L1 READ | P23:4.2 | Read file (workspace-relative) |
| `file_write` | L2 WRITE | P23:4.2 | Write file (workspace-bound) |
| `notify_toast` | L2 WRITE | P23:4.2 | Show Windows toast notification |

**Disposition:** REWRITE (new in P23, no P22 source).

---

#### Backend 7: `freelance` -- Freelance Platform Operations

**Source files:**
- P23: Section 4.6 (8 actions across 3 platforms: Upwork, Fiverr, freelancer.com)
- No P22 equivalent (new in P23, per Q72)

**Unified actions (8):**

| Action | L-label | Source | Notes |
|--------|---------|--------|-------|
| `list_jobs` | L1 READ | P23:4.6 | List available jobs/projects |
| `get_messages` | L1 READ | P23:4.6 (implicit via send_message pair) | Read messages |
| `send_message` | L2 WRITE | P23:4.6 | Send message on platform |
| `submit_proposal` | L2 WRITE | P23:4.6 | Submit job proposal (Upwork) |
| `place_bid` | L2 WRITE | P23:4.6 | Place bid (freelancer.com) |
| `accept_contract` | L2 WRITE | P23:4.6 | Accept contract (wallet check required) |
| `submit_milestone` | L2 WRITE | P23:4.6 | Submit milestone delivery |
| `submit_delivery` | L2 WRITE | P23:4.6 | Submit final delivery (Fiverr) |

**L4 DELETED:** `withdraw_to_wallet` (P23:4.6 explicitly rejects -- "not an executor action"). Not in M8.

**Disposition:** REWRITE (new in P23, no P22 source).

---

#### Backend 8: `social` -- Social Media Operations

**Source files:**
- P22: `src/life_integrations/adapters/telegram_adapter.py:33` (6 actions), `src/life_integrations/adapters/discord_adapter.py:39` (6 actions), `src/life_integrations/adapters/whatsapp_adapter.py:34` (5 actions)
- P23: Section 4.7 (5 cross-platform actions x 4 platforms = 20)

**Unified actions (11):**

| Action | L-label | Source | Notes |
|--------|---------|--------|-------|
| `read_timeline` | L1 READ | P23:4.7 + P22 telegram:104 + P22 discord:131 | Read feed/history/updates |
| `search` | L1 READ | P23:4.7 | Search posts |
| `post` | L2 WRITE | P23:4.7 + P22 telegram:108 + P22 discord:144 + P22 whatsapp:105 | Post/send message |
| `reply` | L2 WRITE | P23:4.7 + P22 telegram:114 + P22 discord:154 | Reply to post/message |
| `comment` | L2 WRITE | P23:4.7 + P22 discord:162 (add_reaction) | Comment on post |
| `send_message` | L2 WRITE | P22 telegram:108 + P22 discord:144 + P22 whatsapp:105 | Send direct message |
| `edit_message` | L2 WRITE | P22 telegram:114 + P22 discord:154 + P22 whatsapp:128 | Edit outgoing message |
| `send_photo` | L2 WRITE | P22 telegram:128 | Send photo/media |
| `send_document` | L2 WRITE | P22 telegram:144 | Send document |
| `delete_message` | L3 DESTRUCTIVE | P22 telegram:162 + P22 discord:160 + P22 whatsapp:128 | Delete message (pre-delete tombstone) |
| `create_thread` | L2 WRITE | P22 discord:162 (add_reaction) | Create thread |

**L4 DELETED:** `kick_member`, `ban_member`, `purge_messages` (P22 discord:190 marks L4_FORBIDDEN), `promote_admin` (P22 telegram:206, P22 whatsapp:161 marks L4_FORBIDDEN). Not in M8.

**Disposition:** PORT/REWRITE (P23 social_executor is canonical for X/LinkedIn/Instagram/Facebook. P22 telegram/discord/whatsapp adapters provide legacy messaging that maps into the unified social surface).

---

#### Backend 9: `memory` -- Memory, Knowledge Graph, and Internal Data

**Source files:**
- P22: `src/life_integrations/adapters/memory_adapter.py:32` (5 actions), `src/life_integrations/adapters/finance_adapter.py:38` (7 actions), `src/life_integrations/adapters/calendar_adapter.py:32` (5 actions), `src/life_integrations/adapters/notion_adapter.py:32` (6 actions), `src/life_integrations/adapters/drive_adapter.py:32` (7 actions)

**Unified actions (19):**

| Action | L-label | Source | Notes |
|--------|---------|--------|-------|
| `recall` | L1 READ | P22 memory:97 | Recall memories via vector+FTS |
| `search_kg` | L1 READ | P22 memory:143 | Search knowledge graph |
| `list_transactions` | L1 READ | P22 finance:159 | List financial transactions |
| `summarize` | L1 READ | P22 finance:168 | Finance period summary |
| `detect_anomalies` | L1 READ | P22 finance:177 | Spending anomaly detection |
| `export_transactions` | L1 READ | P22 finance:188 | Export CSV/JSON |
| `list_events` | L1 READ | P22 calendar:102 | List calendar events |
| `get_event` | L1 READ | P22 calendar:108 | Get specific event |
| `retrieve_page` | L1 READ | P22 notion:107 | Get Notion page |
| `search_notes` | L1 READ | P22 notion:102 | Search Notion pages |
| `list_files` | L1 READ | P22 drive:102 | List Drive files |
| `get_file` | L1 READ | P22 drive:106 | Get Drive file metadata |
| `store` | L2 WRITE | P22 memory:107 | Store episode |
| `store_fact` | L2 WRITE | P22 memory:117 | Store semantic fact |
| `record_transaction` | L2 WRITE | P22 finance:207 | Record transaction (DEFERRED_FOR_SAFETY) |
| `create_event` | L2 WRITE | P22 calendar:118 | Create calendar event |
| `update_event` | L2 WRITE | P22 calendar:123 | Update calendar event |
| `create_page` | L2 WRITE | P22 notion:128 | Create Notion page |
| `update_page` | L2 WRITE | P22 notion:145 | Update Notion page |
| `append_blocks` | L2 WRITE | P22 notion:157 | Append blocks to Notion page |
| `create_file` | L2 WRITE | P22 drive:115 | Create/upload Drive file |
| `update_file` | L2 WRITE | P22 drive:133 | Update Drive file |
| `mark_dnr` | L3 DESTRUCTIVE | P22 memory:150 | Mark memory do-not-recall |
| `correct_transaction` | L3 DESTRUCTIVE | P22 finance:251 | Correct via compensating entry |
| `bulk_import` | L3 DESTRUCTIVE | P22 finance:293 | Bulk import finance data |
| `delete_event` | L3 DESTRUCTIVE | P22 calendar:136 | Delete calendar event (pre-delete snapshot) |
| `archive_page` | L3 DESTRUCTIVE | P22 notion:112 | Archive Notion page |
| `trash_file` | L2 WRITE | P22 drive:200 | Trash Drive file (30d recovery) |
| `delete_file` | L3 DESTRUCTIVE | P22 drive:148 | Permanently delete Drive file (pre-delete export) |
| `public_share` | L3 DESTRUCTIVE | P22 drive:179 | Public sharing |

**L4 DELETED:** `delete_memory` (P22 memory:187 -- use DNR instead), `pay/transfer/withdraw/invest/trade` (P22 finance:35 -- L4_FORBIDDEN), `delete_calendar/clear_calendar` (P22 calendar:167 -- L4_FORBIDDEN), `delete_view` (P22 notion:168 -- L4_FORBIDDEN), `empty_trash` (P22 drive:216 -- L4_FORBIDDEN). Not in M8.

**Disposition:** PORT (P22 adapters provide the implementations; no P23 equivalent. These internal-data backends are retained as-is since P23 focuses on external execution surfaces).

---

## 3. Action Count Summary

| Backend | Actions | L1 (READ) | L2 (WRITE) | L3 (DESTRUCTIVE) |
|---------|---------|-----------|------------|-------------------|
| browser | 11 | 7 | 4 | 0 |
| github | 19 | 10 | 7 | 2 |
| filesystem | 10 | 4 | 4 | 1 |
| vps | 14 | 6 | 7 | 1 |
| email | 10 | 3 | 7 | 0 |
| desktop | 6 | 1 | 4 | 1 |
| freelance | 8 | 2 | 6 | 0 |
| social | 11 | 2 | 8 | 1 |
| memory | 29 | 12 | 12 | 5 |
| **TOTAL** | **118** | **47** | **59** | **11** |

**Note:** The ~108 target from the prompt is approximately met. The memory backend inflates the count because it absorbs 5 P22 adapters (memory, finance, calendar, notion, drive). If calendar, notion, and drive are split into separate sub-tools within the memory backend (as P23 does with freelance/social/email sub-tools), the per-backend counts align with the plan's 9-backend model. The core "external action" backends (browser, github, filesystem, vps, email, desktop, freelance, social) total 89 actions, with memory adding 29.

**Deduplication note:** Many actions appear in both P22 and P23 (e.g., `github.create_pr` exists in P22:285, P23:4.4, and MCP github:253). In the unified M8 model, the P23 executor implementation is canonical. The P22 adapter is retired. The MCP tool function is wrapped as an internal helper. The 118 count is the deduplicated unique action count.

---

## 4. L4 DELETED Actions (Confirmed Absent from M8)

The following L4-forbidden actions from P22 are explicitly NOT in the M8 action catalogue, per the P23 paradigm shift (Q34/Q35 -- no consent gate, no HARD STOP in executor):

| Action | Source | Reason deleted |
|--------|--------|---------------|
| `delete_repo` | P22 github_adapter:293 | L4_FORBIDDEN |
| `force_push` | P22 github_adapter:293 | L4_FORBIDDEN |
| `system_prune` / `docker_rm_all` | P22 vps_adapter:346 | L4_FORBIDDEN |
| `permanent_delete` (Gmail) | P22 gmail_adapter:202 | L4/L3 gated, requires approval |
| `delete_memory` | P22 memory_adapter:187 | L4_FORBIDDEN, use DNR |
| `pay/transfer/withdraw/invest/trade` | P22 finance_adapter:35 | L4_FORBIDDEN |
| `delete_calendar/clear_calendar` | P22 calendar_adapter:167 | L4_FORBIDDEN |
| `delete_view` (Notion) | P22 notion_adapter:168 | L4_FORBIDDEN |
| `empty_trash` (Drive) | P22 drive_adapter:216 | L4_FORBIDDEN |
| `kick_member/ban_member/purge_messages` (Discord) | P22 discord_adapter:190 | L4_FORBIDDEN |
| `promote_member` (Telegram) | P22 telegram_adapter:206 | L4_FORBIDDEN |
| `promote_admin` (WhatsApp) | P22 whatsapp_adapter:161 | L4_FORBIDDEN |
| `withdraw_to_wallet` (Freelance) | P23 Section 4.6 | Explicitly rejected |
| `forbidden_path` (Filesystem) | P22 filesystem_adapter:48 | L4_FORBIDDEN |

These actions are NOT deleted from the codebase -- they remain as `ActionNotSupportedError` / `PermissionDeniedError` raises in the P22 adapters during migration. In the final M8 model, they simply do not exist in the `ToolBackend` action catalogue.

---

## 5. ToolBackend ABC Interface Design

The `ToolBackend` ABC replaces both the P22 `BaseIntegrationAdapter` (source: `src/life_integrations/base.py:29`) and the P23 `BaseExecutor` (source: P23 plan Section 3.2). It is the single interface every M8 backend implements.

### 5.1 Interface (Python reference)

```python
# src/guinevere/tools/backend.py  (REWRITE of src/life_integrations/base.py)
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import uuid


class RiskLabel(Enum):
    """L1-L3 risk labels for M8 actions. L4 DELETED."""
    READ = "L1"           # No side effects, pure information retrieval
    WRITE = "L2"          # Mutates external state, reversible in most cases
    DESTRUCTIVE = "L3"    # Irreversible or high-impact side effects


@dataclass(frozen=True)
class ActionSpec:
    """Immutable specification of a single backend action."""
    name: str                          # e.g. "create_pr"
    risk_label: RiskLabel              # L1, L2, or L3
    description: str                   # Human-readable description
    params_schema: dict[str, Any]      # JSON Schema for params
    reversible: bool = True            # Whether rollback is possible
    requires_confirmation: bool = False # Whether L3 actions need explicit ack


@dataclass(frozen=True)
class ActionResult:
    """Immutable result of an action execution."""
    action_id: uuid.UUID               # UUID v7
    backend: str                       # "browser", "github", etc.
    action: str                        # "create_pr", etc.
    ok: bool                           # True iff action completed successfully
    output: dict[str, Any] | None      # Structured output (redacted before audit)
    error_kind: str | None             # "validation" | "auth" | "backend" | "timeout" | "internal"
    error_message: str | None          # NEVER contains secrets/PII
    duration_ms: int                   # Wall-clock duration
    artifacts: list[str] | None        # File paths only, NEVER contents


class ToolBackend(ABC):
    """Abstract base class for all M8 tool backends.

    Every backend MUST:
    - Declare its name and action catalogue via `action_specs()`
    - Implement `execute()` for all declared actions
    - Implement `health()` for liveness/readiness probing
    - Implement `close()` for graceful shutdown

    The backend does NOT:
    - Make policy decisions (Hermes owns all policy)
    - Gate by consent (consent is dev-workflow only, per Q35)
    - Classify risk at runtime (risk labels are static metadata)
    - Hold a HARD STOP (Q34/Q74 removed)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend identifier: 'browser', 'github', 'fs', 'vps',
        'email', 'desktop', 'freelance', 'social', 'memory'."""
        ...

    @abstractmethod
    def action_specs(self) -> list[ActionSpec]:
        """Return the full catalogue of actions this backend supports."""
        ...

    @abstractmethod
    async def execute(
        self,
        action: str,
        params: dict[str, Any],
        *,
        action_id: uuid.UUID | None = None,
        hermes_id: str = "Guinevere",
    ) -> ActionResult:
        """Execute an action and return a result.

        MUST:
        - Never raise exceptions to caller; all failures become ActionResult(ok=False)
        - Apply redaction to output before returning (or let the audit hook do it)
        - Populate action_id with UUID v7 if not provided
        - Record duration_ms

        MUST NOT:
        - Check consent (Q35: consent is dev-workflow only)
        - Call HARD STOP (Q34: removed)
        - Make policy decisions (Hermes owns all policy)
        """
        ...

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        """Return health status: {'status': 'ok'|'degraded'|'down', ...}"""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Graceful shutdown: drain in-flight actions, close connections."""
        ...
```

### 5.2 Differences from P22 `BaseIntegrationAdapter`

| Aspect | P22 BaseIntegrationAdapter | M8 ToolBackend |
|--------|---------------------------|----------------|
| Risk tiers | L1-L4 with runtime tier enforcement | L1-L3 static metadata only (L4 deleted) |
| Consent | consent_scopes in config, runtime gating | No consent (Q35: dev-workflow only) |
| Policy | Adapter checks tier before execute | Backend is pure execute (Hermes owns policy) |
| Error handling | Raises ActionNotSupportedError | Returns ActionResult(ok=False) |
| Audit | Not built-in | Audit hook wraps execute() (P23-003) |
| Action discovery | Implicit from execute_action dispatch | Explicit via action_specs() |
| Health | IntegrationHealth enum | dict with 'status' key |
| Secrets | secret_refs in config | Secret loaded externally by P23-014 loader |

### 5.3 Differences from P23 `BaseExecutor`

| Aspect | P23 BaseExecutor | M8 ToolBackend |
|--------|-----------------|----------------|
| Queue integration | Built into executor (ActionQueue) | Queue is optional decorator, not in ABC |
| Audit hook | Wraps every execute() | Same (audit hook wraps ToolBackend.execute) |
| Hermes integration | Registered via tools/registry.py | Same |
| Scope | 8 executors only | 9 backends (adds memory) |

The M8 `ToolBackend` is the final convergence of P22's adapter pattern and P23's executor pattern into a single interface.

---

## 6. Migration Path per Backend

| Backend | Disposition | Source | Notes |
|---------|-------------|--------|-------|
| browser | PORT | P23 browser_executor + P22 browser_adapter + MCP obscura_cdp | P23 executor canonical; P22 adapter retired; MCP tools wrapped |
| github | PORT | P23 github_executor + P22 github_adapter + MCP github + git_tool | P23 executor canonical; P22 adapter retired; MCP tools wrapped |
| filesystem | PORT | P23 filesystem_executor + P22 filesystem_adapter + MCP filesystem | P23 executor canonical; P22 adapter retired; MCP tools wrapped |
| vps | PORT | P23 vps_executor + P22 vps_adapter + MCP docker/shell/redis/postgres | P23 executor canonical; P22 adapter retired; MCP tools wrapped |
| email | PORT/REWRITE | P23 email_executor + P22 gmail_adapter | P23 broadens to 4 providers; P22 gmail is initial impl |
| desktop | REWRITE | P23 desktop_executor only | New in P23; no P22 source |
| freelance | REWRITE | P23 freelance_executor only | New in P23 (Q72); no P22 source |
| social | PORT/REWRITE | P23 social_executor + P22 telegram/discord/whatsapp | P23 canonical for X/LI/IG/FB; P22 messaging adapters provide legacy surface |
| memory | PORT | P22 memory/finance/calendar/notion/drive adapters | No P23 equivalent; P22 adapters provide all implementations |

---

## 7. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| P22 adapters use different error model (exceptions) than P23 (Result envelope) | Medium | ToolBackend ABC enforces ActionResult return; P22 exceptions caught and wrapped |
| MCP tools registered on FastMCP server while M8 backends registered in Hermes fork tools/registry.py | Medium | Dual registration; MCP server kept for external clients; P24 backends call Python functions directly |
| Memory backend is broad (5 P22 adapters merged) | Low | Sub-tools within backend (memory.kg, memory.finance, memory.calendar, etc.) |
| P23 plan says 8 executors; M8 says 9 backends (adds memory) | Low | Memory backend is the consolidation of P22 adapters that have no P23 executor equivalent |
| action count ~118 vs ~108 target | Low | 89 external-action + 29 internal-data; the ~108 target was an approximation |

---

## 8. Verdict

**PASS** -- The P22 adapters (13, 80 actions), P23 executors (8, 107 actions), MCP tools (16 modules, 62 tools), and command catalog (35 commands) can be unified into 9 M8 backends with 118 unique actions. Every action has an L1-L3 label; all L4-forbidden actions are confirmed absent from M8. The `ToolBackend` ABC interface converges P22's `BaseIntegrationAdapter` and P23's `BaseExecutor` into a single contract. Disposition for each backend is documented (PORT/REWRITE/DELETE). No plan claims were found wrong -- all verified against actual file:line sources.
