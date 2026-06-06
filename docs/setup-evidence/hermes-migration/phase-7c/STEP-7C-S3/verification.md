# Step 7C-S3 — VPS Hermes CLI Non-Interactive PATH Fix: Verification

**Date**: 2026-06-06  
**Operator**: Sisyphus  
**Step**: 7C-S3 (Phase 7c safe subset)

---

## 1. Summary

Applied minimal shell-profile PATH adjustment to `/home/guinevere/.bashrc` so `hermes` resolves in non-interactive SSH shells. No service restart, no systemd edit, no backup zip created.

---

## 2. What Was Done

- **Root cause identified**: `~/.bashrc` sourced `. "$HOME/.local/bin/env"` at line 119, but the non-interactive early return (`case $- in *i*) ;; *) return;; esac`) at lines 6-9 caused the shell to exit before reaching that line.
- **Fix applied**: Added `. "$HOME/.local/bin/env"` at line 5 of `~/.bashrc`, immediately after the header comments and before the non-interactive early return.
- **Environment**: `~/.local/bin/hermes` is a symlink → `/home/guinevere/code/guinevere/.venv/bin/hermes`. The `env` script conditionally prepends `~/.local/bin` to PATH if not already present.

---

## 3. Files Changed

| File | Action |
|---|---|
| `/home/guinevere/.bashrc` | Modified — inserted `. "$HOME/.local/bin/env"` at line 5 |

No local files changed (except this evidence file).

---

## 4. Validation Results

### Before Fix

| Check | Result |
|---|---|
| `systemctl is-active hermes-gateway` | `active` |
| `command -v hermes \|\| true` | `hermes NOT FOUND in PATH` |
| `~/.bashrc` lines | 119 |
| `~/.local/bin/hermes` exists | Yes (symlink) |
| Venv hermes via full path | Hermes Agent v0.15.2 |

### After Fix

| Check | Expected | Actual | Status |
|---|---|---|---|
| `command -v hermes` | Resolves to path | `/home/guinevere/.local/bin/hermes` | ✅ PASS |
| `hermes --version` | Exit 0 | Hermes Agent v0.15.2 | ✅ PASS |
| `hermes backup --help >/dev/null` | Exit 0 | Exit 0 (output suppressed) | ✅ PASS |
| `hermes checkpoints status` | Exit 0 | Checkpoint base info | ✅ PASS |
| `systemctl is-active hermes-gateway` | `active` | `active` | ✅ PASS |
| Backup zip created? | No | No zip files found | ✅ PASS |
| Service restart occurred? | No | Confirmed no restart | ✅ PASS |

---

## 5. Evidence Artifacts

| Artifact | Path |
|---|---|
| Before backup (attempt 1) | `/home/guinevere/.bashrc.backup.20260606-184750` |
| Before backup (clean) | `/home/guinevere/.bashrc.backup.20260606-185001` |
| Current file | `/home/guinevere/.bashrc` (121 lines, syntax OK) |
| Verification report | This file |

---

## 6. Doc-Sync Impact

None. No documentation changes needed — this is a runtime-only fix for CLI availability.

---

## 7. Boundary Compliance

| Boundary | Status |
|---|---|
| No service restart | ✅ |
| No systemd edit | ✅ |
| No SSH daemon/firewall change | ✅ |
| No Aizanta paths touched | ✅ |
| No secrets printed | ✅ |
| No live `hermes backup` write | ✅ (only `--help` and status) |
| No backup zip created | ✅ |

---

## 8. Rollback / Re-run Safety

- **Rollback**: `cp ~/.bashrc.backup.20260606-185001 ~/.bashrc`
- **Idempotent**: Fix script is safe to re-run; the env script's `case` statement prevents duplicate PATH entries.

---

## 9. Design Decisions / Caveats

- Chose to source `.local/bin/env` before the early return rather than move the entire non-interactive guard. This is the minimal change — only PATH is affected for non-interactive shells.
- The existing `env` script on the VPS handles PATH deduplication via `case ":${PATH}:" in *:"$HOME/.local/bin":*) ;; *) ... esac`.
- Interactive shells still source the same line at the original position (line 120); the `case` guard prevents duplicate PATH entries.
- No systemd unit changes needed because systemd already uses explicit full path to the venv binary.

---

## 10. Acceptance Criteria Mapping

| Criteria | Status |
|---|---|
| Minimal remote shell-profile fix applied | ✅ |
| Timestamped backup created before edit | ✅ |
| `command -v hermes` succeeds after fix | ✅ |
| `hermes --version` succeeds | ✅ |
| `hermes backup --help` + `hermes checkpoints status` succeed | ✅ |
| `hermes-gateway` remains active before/after | ✅ |
| No service restart occurred | ✅ |
| No backup zip created | ✅ |
| Evidence files written | ✅ |

---

## Footer

Step 7C-S3 implementation complete. Ready for auditor gate.
