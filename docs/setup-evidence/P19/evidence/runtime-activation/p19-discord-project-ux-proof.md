# P19 Runtime Activation — Discord Project UX Proof (DEFERRED)

**Date:** 2026-06-27 11:40 WIB
**Author:** Guinevere (parent)
**Phase:** RA-2 Step 4 — Discord UX (deferred)

---

## 1. Status: DEFERRED — NOT CLAIMED ACTIVE

**Discord `/project` command UX is NOT active.** This document honestly records the deferred status and why.

## 2. Why `/project` Is NOT Live

| Check | Result | Implication |
|---|---|---|
| cmd_project.py deployed to VPS | ✅ (scp'd 2026-06-27 08:42) | File exists and imports cleanly |
| project_session.py deployed | ✅ | File exists and imports cleanly |
| `/project` registered in bot command tree | ❌ **NO** | Bot does NOT expose the command |
| Why not registered | `_entrypoint.py` setup_hook hardcodes 13 wired + 20 stubs; cmd_project is NOT wired | Code change required |
| guinevere-discord.service | active (enabled+active since 2026-06-25 19:45) | Bot is running, but without /project |
| feature:projects:enabled | ON (just set) | Flag ON alone does NOT register slash commands |

## 3. What Would Be Required for `/project` Live

1. **Code change in `_entrypoint.py`**: Register `cmd_project` slash command in the `setup_hook` command tree (currently hardcodes 13 wired callbacks — add `/project` as 14th).
2. **Restart guinevere-discord.service**: To load the new command registration.
3. **Discord API sync**: Slash commands sync to the guild.

This is a **non-trivial code change** (touching the bot entrypoint + command registration), not just a flag flip or restart. It was NOT part of the P19-012 schema deploy, and the activation spec allows deferring it.

## 4. Why Defer Is Correct

- The operator's allowed final statuses include **"P19 RUNTIME ACTIVATED — UX DEFERRED"**.
- The runtime activation proof (project-scoped thread_id, memory adapter, KG search) does NOT depend on Discord UX.
- `/project` is a Discord **interaction layer** on top of the core project-scoped runtime — the core works without it.
- Wiring `/project` requires modifying P20-closed discord service code, which is a separate scope.
- Claiming "Discord /project active" without live proof would violate hard-rejection criteria.

## 5. Existing Discord Flow — Untouched

The existing Discord flow (dashboard via REST, 13 slash commands, log channel) is intact — verified in P19-012 deploy phase (audit round-1 UX-02/UX-03). The activation did NOT touch guinevere-discord.service.

## 6. Footer

| Field | Value |
|---|---|
| Discord /project status | **DEFERRED** — not wired into bot, not active |
| File deployed | ✅ (cmd_project.py + project_session.py on VPS) |
| Registered in command tree | ❌ NO |
| Activatable | Requires code change + bot restart (separate work) |
| Existing Discord flow | intact (untouched) |