# P2 Discord Bot — Downstream Impact Assessment: P19–P24

**Date:** 2026-06-25
**Auditor:** Implementation audit subagent (read-only)
**Scope:** P2 Discord bot/infrastructure impact on roadmap phases P19 through P24
**Methodology:** Code inspection (src/discord/, src/life_kernel/discord_rest_client.py), systemd unit review, plan/research/evidence directory review for each target phase.

---

## Current P2 State Summary (as of 2026-06-25)

| Aspect | Verified State |
|--------|---------------|
| Entrypoint | `src/discord/_entrypoint.py` — `GuinevereBot(_BotBase)` wrapping `commands.Bot`, 770 lines |
| Commands wired | 49 via `setup_hook` (13 original + 20 batch-D + 2 Hermes + 4 P12 + 3 P14 + 4 P18 + 3 P5) |
| Command specs in `_command_registry.py` | 49 `CommandSpec` entries |
| CHECKLIST.md claim | 33 (STALE — line 265) |
| PROGRESS.md claim | 35 (STALE — line 146) |
| Actual wired | 49 |
| Auth model | `_auth_guard.py` — `is_faiz_interaction()` via guild.owner_id check (binary Faiz/non-Faiz). **No AuthLevel enums used anywhere in src/discord/** |
| Active Discord service | **MASKED** (P2-022). P20 uses `src/life_kernel/discord_rest_client.py` (Option-B REST publisher) for dashboard/log publishing |
| Intents | `voice_states=True`, `message_content=True`, `members=True`, `presences=True`, `guilds=True`, `messages=True`, `reactions=True` |
| HARD STOP listener | **WIRED** — `_entrypoint.py:132-160` registers `_on_message_listener` via `self.listen("on_message")` which calls `handle_safeword_message_async` from `cmd_safeword.py`. Seed fact claiming it was "UNWIRED" is INCORRECT |
| Notifications SEV matrix | SEV0/1->system-health, SEV2->cost-tracker, SEV3->guinevere-status, SEV4->audit-log |
| `notifications.py` line 240 | Bare `import discord` at **last line of file** — dead import, no code follows it; contradicts lazy-import pattern used elsewhere in the module |
| Gotify URL | Hardcoded `http://localhost:8081`. Old audit referenced port 8080. Mismatch persists |
| Channel-ids.yaml | 14 channels listed (includes `rituals` + 3 ghost channels: `project-alpha-dev`, `project-alpha-docs`, `project-beta-dev`) |
| Secrets | `secrets/discord-secrets.enc.yaml` EXISTS and IS SOPS-encrypted (age key). P2-002 CRITICAL finding from old audit (2026-06-08) is PARTIALLY FIXED — encrypted file exists now |
| Service files | Two copies with conflicting setups: `systemd/guinevere-discord.service` (plaintext `.env.discord`), `deploy/discord/guinevere-discord.service` (SOPS decrypt to `/run/guinevere-discord-token` with shred). Deploy version is more secure |
| VPS mirror systemd | No `guinevere-discord.service` in `vps-mirror/systemd-live/` — consistent with masked status |

**Command count notes:** The old 33/35 mismatch (CHECKLIST.md line 265 says 33, old PROGRESS.md/audit say 35) has grown to a **three-way mismatch**: CHECKLIST.md=33, PROGRESS.md line 146=35, actual wired=49. P2-FIX-PLAN.md step 2.1 (update PROGRESS.md) was partially done (PROGRESS.md now says 35 instead of 33) but still lags the 49-code reality.

---

## Per-Phase Impact Table

| Phase | P2 Compatibility | Blocker(s) | Detail |
|-------|-----------------|-----------|--------|
| **P19** (Multi-Project Context) | Partial | MEDIUM — P2 channel routing is single-project. No /project command surface exists. P2's notification SEV matrix routes to fixed channel names, not per-project variants | P19 research (`p19-discord-dashboard-project-switcher-research.md`) explicitly documents single-project Discord UX. P19 plans additive `/project` commands and per-project dashboards via P20 REST publisher, not via P2 gateway. P2 cmd_pc.py reads a `project` field from Windows events but this is unrelated to P19 namespace routing. P2 is NOT namespace-aware. P19 will extend (not conflict with) P2's pattern. **Mitigation:** P19-008 must thread `project_id` into `hermes_conversational.py` (per audit finding P21P22-01); P2's `_entrypoint.py` `on_message` pipeline must propagate `project_id` to the conversational handler after P19 lands. |
| **P20** (Living Autonomy Kernel) | Full | None | P2 gateway is intentionally masked (P2-022). P20 uses `src/life_kernel/discord_rest_client.py` (Option-B REST publisher) for outbound dashboard/log publishing. Same `DISCORD_BOT_TOKEN`, no session collision because P2 gateway is inactive. P20 CLOSED (early production acceptance, operator waived 24h soak). No conflict. P2 and P20 complement each other: P2 gateway for interactive commands (when un-masked), P20 REST publisher for autonomous status publishing. |
| **P21** (Voice) | Compatible | LOW — P21 modifies P2 files (coordination needed) | `_intents.py` includes `voice_states=True` — enables Discord voice state gateway events. P21 plan (`p21-voice-interface-enterprise-plan.md`) specifies: new `src/discord/_voice_client.py`, new `src/discord/cmd_voice.py`, modify `src/discord/_entrypoint.py` (wire voice client init), modify `src/discord/hermes_conversational.py` (refactor `_process_turn_core`), modify `src/discord/_command_registry.py` (add `/voice*` commands). **P2 does NOT claim voice readiness it should not** — `voice_states` is a passive intent enabling gateway events, not a claim of voice implementation. **Coordination needed:** P21-003 refactor of `hermes_conversational.py` and P19-008 `project_id` threading must be sequenced. P21 plan acknowledges this. |
| **P22** (Raw/Full Discord Access) | Partial | MEDIUM — P2's binary Faiz-only gate is incompatible with P22's semantic classification mandate | P22 plan (`p22-full-capability-raw-access-replan.md`) lists Discord as "Existing-Merge" — extend placeholder `discord_adapter.py` to full actuator under namespace `p22:comms:discord`. **Key conflict:** P2 uses `is_faiz_interaction()` (guild.owner_id check) for ALL command gating — a binary Faiz/non-Faiz gate. P22 mandates L2/L3/L4 "MUST NOT proceed on AuthLevel-only gating" and requires **semantic classification** by parsed intent + provider operation + side-effect risk. P2's gate is coarser than AuthLevel enums (which P22 already rejects as insufficient). **Mitigation:** P22's Discord actuator operates independently of P2's gateway command surface. P2 commands remain the user-facing Discord surface (slash commands). P22 adds an actuator layer ABOVE/BESIDE P2, with its own semantic classifier. P2's `is_faiz_interaction` is sufficient for its interactive command role; P22's semantic classification is needed for autonomous write/delete/admin operations. No direct merge conflict — P22's `discord_adapter.py` is a new file. |
| **P23** (Action Runtime) | Compatible | None | P23 plan (`p23-embodied-operations-enterprise-plan.md` §3.1): "Discord dashboard/log UX for action state" — P23 consumes P2's Discord surface for display. P23 executors wrap MCP tools, NOT P2 commands. **No P2 command path bypasses P23 gates** — P2 commands are user-facing slash commands; P23 actions fire through `BaseExecutorAdapter` + `SemanticActionClassifier` + 7-step policy gate, completely separate pathways. P2's `is_faiz_interaction` is a baseline auth guard; P23's risk classification operates above it. P23's AuthLevel mandate (AuthLevel is INPUT only, not 1:1 with L1-L4) does not conflict with P2 because P2 doesn't use AuthLevel at all. |
| **P24** (Hermes Fork Convergence) | Partial — needs adaptation | HIGH — P2 gateway bot architecture is obsolete under P24 full fork | P24 research (`p24-discord-comms-channel-convergence-research.md` §1) verifies: Discord is "standalone REST publisher", NOT Hermes Gateway-integrated. ADR-035 claim that "Hermes Gateway handles Discord now" is misleading — the active Discord writer is P20's REST publisher, and the gateway bot is masked. Under P24 full owned fork: **(a)** P2's `GuinevereBot` + `_entrypoint.py` + 49 `cmd_*.py` modules + `_intents.py` + `_startup.py` become obsolete — replaced by Hermes native gateway plugins. 47 Hermes command plugins (`src/hermes_plugins/`) already exist. **(b)** `src/life_kernel/discord_rest_client.py` (P20 REST publisher) remains valid as fork-internal P20 core code — it is fork-internal already. **(c)** `notifications.py`, `gotify_fallback.py`, `_embed_utils.py`, `colors.py` utility modules may survive as internal helpers or Hermes plugin utilities. **(d)** `hermes_conversational.py` is the Hermes turn-core adapter and stays relevant as the bridge between Discord messages and Hermes brain. **Verdict:** P2's interactive command infrastructure has a clear migration path to Hermes plugins. P2's utility/notification modules are partially reusable. P2's bot architecture is superseded. **No P2 code prevents or blocks P24 fork convergence.** P24 plan (§6) already accounts for this. |

---

## Detailed Blockers and Findings

### P2-AUD-P19-001 [MEDIUM] P2 Channel Names Not Namespace-Aware
- **File:** `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml`, `src/discord/notifications.py`
- **Description:** P2 notification routing uses fixed channel names (`system-health`, `cost-tracker`, `guinevere-status`, `audit-log`). P19 multi-project routing would need per-project channel variants or a routing layer above P2. Channel-ids.yaml lists 14 channels including 3 ghost channels (`project-alpha-dev`, `project-alpha-docs`, `project-beta-dev`) — which could serve as a template for per-project channels but are currently unused.
- **Impact:** P19 must add a routing layer; P2 provides no namespace seam.
- **Verification status:** CONFIRMED

### P2-AUD-P19-002 [LOW] cmd_pc.py Has Stale Project Awareness
- **File:** `src/discord/cmd_pc.py:149-182`
- **Description:** `cmd_pc.py` reads a `project` and `branch` field from Windows events and displays them in embeddings. This is unrelated to P19 multi-project namespace routing and does not satisfy any P19 requirement.
- **Impact:** None — unrelated. Documented to avoid confusion.
- **Verification status:** CONFIRMED

### P2-AUD-P20-001 [INFO] P2 Rest Publisher Aligns with P20 Architecture
- **File:** `src/life_kernel/discord_rest_client.py`, `src/discord/_entrypoint.py`
- **Description:** P2 gateway is intentionally masked (confirmed by absence from `vps-mirror/systemd-live/`). P20 REST publisher is the active Discord writer. No conflict. Architecture is correct per P20 design.
- **Impact:** Positive alignment. No action needed.
- **Verification status:** CONFIRMED

### P2-AUD-P21-001 [LOW] P21 Must Coordinate with P2 File Edits
- **File:** `src/discord/_entrypoint.py`, `src/discord/hermes_conversational.py`, `src/discord/_command_registry.py`
- **Description:** P21 plan specifies modifying `_entrypoint.py` (wire voice client), `hermes_conversational.py` (refactor `_process_turn_core`), and `_command_registry.py` (add `/voice*` commands). P19 also touches `hermes_conversational.py`. P21 plan acknowledges sequencing requirement (P21-003 after P19-008).
- **Impact:** Coordination required, not a blocker. P21 contains a collision seam with P19 on `hermes_conversational.py`.
- **Verification status:** CONFIRMED

### P2-AUD-P22-001 [MEDIUM] P2 Faiz-Only Gate Incompatible with P22 Semantic Classification
- **File:** `src/discord/_auth_guard.py`
- **Description:** P2's sole auth mechanism is `is_faiz_interaction()` — a binary check that the interaction user is the Discord guild owner. P22 mandates that L2/L3/L4 operations be classified semantically by parsed intent + provider operation + side-effect risk. P2's gate is coarser than AuthLevel (which P22 also rejects as insufficient alone). P2 has no concept of L1/L2/L3/L4 tiers.
- **Impact:** P22's Discord adapter must implement semantic classification independently. P2's auth guard is insufficient for P22 autonomous write/delete/admin operations. The two coexist (P2 for interactive commands, P22 for autonomous actuators) but P2 provides no reusable auth infrastructure for P22.
- **Verification status:** CONFIRMED

### P2-AUD-P23-001 [INFO] P2 Commands Do Not Bypass P23 Gates
- **File:** `src/discord/cmd_*.py` (all 35+ command callbacks)
- **Description:** All P2 command callbacks execute within the gateway bot process, not via P23 executor adapters. P23 action layer operates independently. No P2 code path circumvents P23's 7-step policy gate, semantic classifier, or HARD STOP.
- **Impact:** None. Architecturally clean separation.
- **Verification status:** CONFIRMED

### P2-AUD-P24-001 [HIGH] P2 Gateway Bot Architecture Is Obsolete Under P24 Fork
- **File:** `src/discord/_entrypoint.py`, `src/discord/cmd_*.py` (49 command modules)
- **Description:** P2's `GuinevereBot(commands.Bot)` architecture is a standalone gateway bot. P24 full owned fork replaces the interactive command surface with Hermes native gateway plugins. 47 Hermes command plugins already exist in `src/hermes_plugins/`. P2's `cmd_*.py` modules represent duplicate command surface that would be migrated to Hermes plugin format. P2 command count (49 wired) diverges significantly from documented counts (33/35), suggesting ongoing organic growth without corresponding architecture migration tracking.
- **Impact:** P2 interactive command infrastructure has limited remaining lifespan under P24 convergence. Migration to Hermes plugins is the intended path (per ADR-035, P24 plan). P2 utility modules (`notifications.py`, `colors.py`, `_embed_utils.py`, `gotify_fallback.py`) may survive as helpers. P20 REST publisher (`discord_rest_client.py`) remains fork-internal and does not need migration.
- **Verification status:** CONFIRMED

### P2-AUD-P24-002 [MEDIUM] Command Count Drift Undermines Migration Planning
- **Files:** `CHECKLIST.md:265`, `PROGRESS.md:146`, `src/discord/_entrypoint.py:515-543`
- **Description:** Three different command counts exist: CHECKLIST.md=33, PROGRESS.md=35, actual wired=49. The 49 wired commands span 7 phase groups (original 13, batch-D 20, Hermes 2, P12 4, P14 3, P18 4, P5 3). No single source of truth tracks the full command roster for migration planning. P24's plugin migration scope is unclear without accurate command inventory.
- **Impact:** P24 migration planning is undermined by incomplete/contradictory command counts. A full command inventory must be established before P24 wave execution.
- **Verification status:** CONFIRMED

---

## Additional P2 Seed-Fact Corrections

| Seed Fact | Verification | Correction |
|-----------|-------------|-----------|
| `handle_safeword_message_async` unwired | **INCORRECT** — it IS wired in `_entrypoint.py:155-157` via `_on_message_listener` registered in `_register_hard_stop_listener` | Wired. The docstring in `cmd_safeword.py:598-600` is stale ("No bot.py listener exists yet"). |
| 33 vs 35 command mismatch PERSISTS | **CONFIRMED but obsolete** — CHECKLIST.md=33 (line 265), PROGRESS.md=35 (line 146), actual=49 | Three-way mismatch, not two-way. |
| Gotify port mismatch | **CONFIRMED** — code says 8081, old audit says 8080 | Port mismatch persists. Needs runtime VPS verification. |
| `notifications.py` bare `import discord` | **CONFIRMED** — line 240, last line of file, dead code | Dead import that would execute at module load time, contradicting lazy-import pattern. No actual impact because nothing uses it, but it creates an import-time dependency on discord.py. |
| Channel-ids.yaml 13 vs 14 | **CONFIRMED** — 14 channels (includes `rituals` + 3 ghosts) | The 14th channel (`rituals`, ID 1513496377324339262) was likely added after the old audit counted 13. |
| P2-002 CRITICAL partially fixed | **CONFIRMED** — `secrets/discord-secrets.enc.yaml` now exists and is SOPS-encrypted | Old audit CRITICAL finding (missing encrypted secret) is resolved. However, `systemd/guinevere-discord.service` still references plaintext `.env.discord` while `deploy/discord/guinevere-discord.service` uses SOPS — deployment may use less secure unit. |

---

## Summary Table

| Phase | Compatibility | Blocker Severity | Key Issue |
|-------|--------------|-----------------|-----------|
| P19 | Partial | MEDIUM | No namespace routing in P2 channel/notification design |
| P20 | Full | NONE | REST publisher complements masked gateway |
| P21 | Compatible | LOW | File collision on hermes_conversational.py with P19 |
| P22 | Partial | MEDIUM | Binary Faiz-only gate ≠ semantic classification mandate |
| P23 | Compatible | NONE | Separate pathways (P2=interactive, P23=executor) |
| P24 | Partial — needs migration | HIGH | Gateway bot architecture superseded by Hermes plugins |

**Overall P2 roadmap health:** P2 provides a working Discord foundation that does not actively block any downstream phase. The two highest-significance items are (a) P24 migration of the gateway bot to Hermes plugins (inevitable, already planned), and (b) P22's need for independent semantic classification on Discord operations (P2's auth model is not reusable). P19/P21 coordination on `hermes_conversational.py` edits is manageable. The 49-vs-35-vs-33 command count drift is a documentation debt that impedes accurate migration planning.
