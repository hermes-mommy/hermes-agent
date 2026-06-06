# Step 5 — Config Registration and VPS Deploy — Implementation Report

**Date:** 2026-06-06  
**Step:** 5 of Phase 6  
**Evidence root:** `docs/setup-evidence/phase-6/STEP-5/`  
**Plan scaffold:** Step 5 from `docs/setup-evidence/phase-6/plan.md` (lines 232–240)  
**Operator:** Guinevere (subagent, delegated)  
**VPS host:** `guinevere-vps` (`100.94.104.22`, user `guinevere`)  

---

## 1. Files Changed

### Local (repo)

| File | Action | Description |
|---|---|---|
| `hermes-config/config.yaml` | Modified | Added budget hook entry to `hooks.pre_tool_call` before consent gate |

### VPS (`/home/guinevere/.hermes/`)

| File | Action | Description |
|---|---|---|
| `config.yaml` | Modified | Added budget hook entry to `hooks.pre_tool_call` before consent gate |
| `config.yaml.pre-phase6-20260606-041313` | Created | Pre-modification backup (14753 bytes) |
| `hooks/budget_check.py` | Updated | SCP latest local version (MD5 now matches local: `ed580921`) |

---

## 2. Exact Changes to `hermes-config/config.yaml` (local)

**Added before consent gate in `hooks.pre_tool_call`:**

```yaml
    # Budget gate — fail-closed LLM cost check (Pillar 5, Phase 6).
    # Runs before consent gate (priority 100 > 90). Uses Redis Lua to check
    # monthly $30 cap and per-tool daily caps. Any Redis/Lua error = block.
    - event: pre_tool_call
      command: "python3 ~/.hermes/hooks/budget_check.py"
      timeout_ms: 500
      on_failure: block
      priority: 100
```

**Resulting `hooks.pre_tool_call` order (priority descending):**

1. Budget check — priority 100, timeout 500ms, on_failure block
2. Consent gate — priority 90, timeout 200ms, on_failure block (unchanged)

**Existing hooks preserved unchanged:**

- `hooks.post_tool_call`: DNR filter — priority 70, timeout 50ms, on_failure block
- `hooks.pre_tool_call[1]`: Consent gate — priority 90, timeout 200ms, on_failure block

---

## 3. Commands Executed (redacted where sensitive)

### Local YAML validation

```powershell
python validate_yaml.py hermes-config/config.yaml
# Output: 2 pre_tool_call hooks, 1 post_tool_call hook, YAML parse: OK
```

### VPS deployment

```bash
# Test connectivity
ssh guinevere-vps "echo SSH_OK"

# Backup VPS config
ssh guinevere-vps 'cp ~/.hermes/config.yaml ~/.hermes/config.yaml.pre-phase6-$(date -u +%Y%m%d-%H%M%S)'

# Update budget_check.py (local > VPS)
scp hermes-config/hooks/budget_check.py guinevere-vps:~/.hermes/hooks/budget_check.py

# Insert budget hook entry via Python YAML manipulation
scp insert_budget_hook.py guinevere-vps:/tmp/
ssh guinevere-vps 'python3 /tmp/insert_budget_hook.py'

# Clean up temp files
ssh guinevere-vps 'rm -f /tmp/insert_budget_hook.py /tmp/validate_vps_config.py'
```

### VPS validation

```bash
# Verify hook files exist
ls -la ~/.hermes/hooks/{budget_check.py,budget_lua.py,budget_lua_extended.py,_hook_utils.py}

# Python compile checks
python3 -m py_compile ~/.hermes/hooks/budget_check.py      # PASS
python3 -m py_compile ~/.hermes/hooks/_hook_utils.py       # PASS
python3 -m py_compile ~/.hermes/hooks/budget_lua.py        # PASS
python3 -m py_compile ~/.hermes/hooks/budget_lua_extended.py # PASS

# YAML parse validation
python3 validate_vps_config.py /home/guinevere/.hermes/config.yaml
# Output: 2 pre_tool_call hooks (budget 100, consent 90), 1 post_tool_call (dnr 70)

# Confirm entries
grep -A5 budget_check ~/.hermes/config.yaml   # priority=100, timeout=500, block
grep -A5 consent_gate ~/.hermes/config.yaml   # priority=90, still present
grep -A5 dnr_filter ~/.hermes/config.yaml     # priority=70, still present

# Confirm backup
ls -la ~/.hermes/config.yaml.pre-phase6-*
```

---

## 4. Validation Results

| Check | Result |
|---|---|
| Local YAML parse (`yaml.safe_load`) | PASS — 2 pre_tool_call hooks, 1 post_tool_call hook |
| Local budget hook entry (priority 100, block, timeout 500) | PASS |
| Local consent gate (priority 90, block, timeout 200) | PRESERVED |
| Local DNR filter (priority 70, block, timeout 50) | PRESERVED |
| VPS hook files exist (4 files) | PASS |
| VPS `budget_check.py` py_compile | PASS |
| VPS `_hook_utils.py` py_compile | PASS |
| VPS `budget_lua.py` py_compile | PASS |
| VPS `budget_lua_extended.py` py_compile | PASS |
| VPS YAML parse | PASS |
| VPS budget hook entry (priority 100, block, timeout 500) | PASS |
| VPS consent gate preserved | PASS |
| VPS DNR filter preserved | PASS |
| VPS backup exists | PASS — `config.yaml.pre-phase6-20260606-041313` |
| Forbidden pattern check: `on_failure: warn` | NOT FOUND (clean) |
| Forbidden pattern check: `timeout_ms > 1000` | NOT FOUND (clean) |

---

## 5. Evidence Artifacts

| Artifact | Path |
|---|---|
| Implementation report | `docs/setup-evidence/phase-6/STEP-5/implementation-report.md` |
| VPS backup | `~/.hermes/config.yaml.pre-phase6-20260606-041313` |

---

## 6. Doc-Sync Impact

- `hermes-config/config.yaml` — modified (budget hook registered)
- No spec/ADR changes needed — budget hook registration was already planned in `plan.md` Step 5

---

## 7. Boundary Compliance

- No secrets/credentials printed, copied, or committed
- No SSH keys, API keys, Redis passwords, or env values exposed
- `DISCORD_APPROVAL_WEBHOOK`, `NINEROUTER_API_KEY`, and `GUINEVERE_REDIS_URL` are referenced by env var name only
- Consent gate and DNR filter remain intact and unchanged
- `plugins.enabled` not touched
- `hermes-gateway` not restarted (Step 8)

---

## 8. Rollback / Re-run Safety

- **Rollback VPS:** `cp ~/.hermes/config.yaml.pre-phase6-20260606-041313 ~/.hermes/config.yaml; sudo systemctl restart hermes-gateway`
- **Rollback local:** `git checkout -- hermes-config/config.yaml` (or manual reverse edit)
- **Re-run safety:** Executing the Python insert script again would add a duplicate entry. To re-run safely, restore from backup first or verify the entry doesn't already exist.

---

## 9. Design Decisions / Caveats

- Used Python `yaml.safe_load` + `yaml.dump` for VPS config modification to preserve YAML structure and avoid sed regex fragility
- VPS `budget_check.py` was out of sync with local version (different MD5). Latest version pushed via SCP. Other three hook files (`budget_lua.py`, `budget_lua_extended.py`, `_hook_utils.py`) already matched
- VPS config uses a different key order for hook entries (dict-style vs the local YAML's explicit format). The Python YAML dumper reordered keys slightly but all values preserved exactly
- Priority 100 > 90 ensures budget check runs before consent gate, as designed in `plan.md` §6.2
- `on_failure: block` means any Redis/Lua failure will prevent the tool call, enforcing fail-closed behavior

---

## 10. Next Action

Proceed to **Step 6** — Fallback chain verification.

---

## Footer

**Report written by:** Guinevere (subagent)  
**Parent verification:** Pending (Step 8 restart gate)  
**Auditor gate:** Pending (parallel audit batch in Step 12)
