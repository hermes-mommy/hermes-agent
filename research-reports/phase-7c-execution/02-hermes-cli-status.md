# Hermes CLI Status — VPS PATH & Availability Report

**Task**: Phase 7c — Research Hermes CLI availability and PATH status on `guinevere-vps`
**Date**: 2026-06-06
**Method**: SSH read-only commands via `guinevere-vps` host
**Scope**: CLI existence, PATH coverage, systemd integration, backup/checkpoint subcommand readiness

---

## 1. Executive Summary

| Check | Status | Detail |
|-------|--------|--------|
| Hermes CLI exists | ✅ YES | `/home/guinevere/code/guinevere/.venv/bin/hermes` |
| Symlink exists | ✅ YES | `~/.local/bin/hermes → /home/guinevere/code/guinevere/.venv/bin/hermes` |
| CLI on PATH (non-interactive SSH) | ❌ NO | System default PATH only; `.bashrc` returns early for non-interactive shells |
| CLI on PATH (interactive/login shell) | ✅ YES | Via `.profile` → `$HOME/.local/bin:$PATH` and `. "$HOME/.local/bin/env"` |
| CLI on PATH (systemd hermes-gateway) | ✅ YES | Explicit PATH includes both `.local/bin` and project venv |
| `hermes --version` | ✅ YES | `Hermes Agent v0.15.2 (2026.5.29.2)` |
| `hermes backup --help` | ✅ YES | Subcommand available (creates zip archives — read-only help confirmed) |
| `hermes checkpoints --help` | ✅ YES | Subcommand available (status/list/prune/clear/clear-legacy) |
| `hermes checkpoints status` | ✅ YES | Works (0 B, no projects yet) |
| `hermes doctor` | ✅ YES | Works (minor warnings only — optional packages, auth not configured) |

---

## 2. Executable Path Discovery

### 2.1 `which hermes` (non-interactive SSH)
```
→ Empty / not found
```
`which hermes` returns nothing because non-interactive SSH shells (the default for `ssh host 'command'`) do NOT source `.bashrc` beyond the early-return guard.

### 2.2 `ls ~/.local/bin/hermes`
```
lrwxrwxrwx 1 guinevere guinevere 47 Jun  5 07:51 /home/guinevere/.local/bin/hermes
  → /home/guinevere/code/guinevere/.venv/bin/hermes
```
Symlink exists and is valid.

### 2.3 `ls /home/guinevere/.venv/bin/hermes`
```
ls: cannot access '/home/guinevere/.venv/bin/hermes': No such file or directory
```
The default venv path does NOT exist. The project venv is at `/home/guinevere/code/guinevere/.venv/`.

### 2.4 `ls /home/guinevere/code/guinevere/.venv/bin/hermes`
```
-rwxrwxr-x 1 guinevere guinevere 328 Jun  1 00:04 /home/guinevere/code/guinevere/.venv/bin/hermes
```
**Primary executable.** 328-byte Python entry-point script:

```python
#!/home/guinevere/code/guinevere/.venv/bin/python
import sys
from hermes_cli.main import main
if __name__ == "__main__":
    sys.exit(main())
```

### 2.5 `echo $PATH` — Non-interactive SSH
```
/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin
```
**`~/.local/bin` is NOT present.** This is the PATH seen by:
- Automated scripts
- Cron jobs (unless PATH is set explicitly)
- SSH non-interactive command execution

### 2.6 `echo $PATH` — Interactive / Login Shell
With `.profile` sourcing:
```
$HOME/.local/bin:$PATH
```
The `.profile` contains:
```bash
if [ -d "$HOME/.local/bin" ] ; then
    PATH="$HOME/.local/bin:$PATH"
fi
. "$HOME/.local/bin/env"
```

### 2.7 With Venv Activated
```bash
source /home/guinevere/code/guinevere/.venv/bin/activate
which hermes   → /home/guinevere/code/guinevere/.venv/bin/hermes
hermes --version → Hermes Agent v0.15.2 (2026.5.29.2)
```

---

## 3. PATH Gap Analysis

### 3.1 Root Cause

The `.bashrc` has an early-return guard for non-interactive shells at line ~7:
```bash
case $- in
    *i*) ;;
      *) return;;
esac
```

The PATH-adding logic (`. "$HOME/.local/bin/env"`) is at the **very end** of `.bashrc`, so it is **never reached** in non-interactive mode. The `.profile` (which adds `~/.local/bin`) is only sourced by login shells.

| Shell Type | Sourced Files | `~/.local/bin` on PATH? |
|---|---|---|
| Non-interactive SSH (default) | none of user's shell configs | ❌ NO |
| Interactive non-login SSH (`-t`) | `.bashrc` (but returns early) | ❌ NO (unless `-t` + `bash -l`) |
| Login shell (`bash -l`) | `.profile` → `.bashrc` | ✅ YES |
| Interactive login (SSH login) | `.profile` → `.bashrc` | ✅ YES |
| Systemd service | Explicit PATH in unit file | ✅ YES |

### 3.2 Systemd Service PATH (No Issue)

The `hermes-gateway.service` unit explicitly sets:
```
Environment=PATH=/home/guinevere/.local/bin:/home/guinevere/code/guinevere/.venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=VIRTUAL_ENV=/home/guinevere/code/guinevere/.venv
ExecStart=/home/guinevere/code/guinevere/.venv/bin/hermes gateway run --accept-hooks
```
This is **correctly configured** and needs no changes.

---

## 4. Subcommand Readiness

### 4.1 `hermes backup --help` (Read-Only)
✅ Available. Creates zip archives of Hermes config/skills/sessions/data.
```
usage: hermes backup [-h] [-o OUTPUT] [-q] [-l LABEL]
  -o OUTPUT       Output path for the zip file (default: ~/hermes-backup-<timestamp>.zip)
  -q, --quick     Quick snapshot: only critical state files
  -l LABEL        Label for the snapshot (only used with --quick)
```
**⚠ Do not run `hermes backup` without `-o` flag — default writes to ~/hermes-backup-<timestamp>.zip.**
**✅ `hermes backup --help` is safe, read-only.**

### 4.2 `hermes checkpoints --help` (Read-Only)
✅ Available. Manages filesystem checkpoint store.
```
COMMAND:
  status          Show total size, project count, per-project breakdown
  list            Alias for 'status'
  prune           Delete orphan/stale checkpoints
  clear           Delete entire checkpoint base
  clear-legacy    Delete legacy archives
```

### 4.3 `hermes checkpoints status` Executed
✅ Works with no side effects.
```
Checkpoint base: /home/guinevere/.hermes/checkpoints
Total size:      0 B
Projects:        0
```
**Safe to run — read-only, no state modification.**

### 4.4 `hermes doctor` (Read-Only)
✅ Works. Reports minor warnings (optional packages, auth not configured).
```
◆ Security Advisories:     ✓ No active advisories
◆ Python Environment:      ✓ Python 3.12.3, ✓ Venv active
◆ Configuration Files:     ✓ All present, ✓ Config version v24
◆ Auth Providers:          ⚠ Several not logged in (expected)
◆ Directory Structure:     ✓ All paths present
```

---

## 5. `~/.local/bin/env` File

This file is sourced by both `.bashrc` and `.profile`:
```bash
case ":${PATH}:" in
    *:"$HOME/.local/bin":*)
        ;;
    *)
        export PATH="$HOME/.local/bin:$PATH"
        ;;
esac
```
It idempotently prepends `~/.local/bin` to PATH if not already present. However, it is placed **after** the interactive guard in `.bashrc`, so non-interactive shells never execute it.

---

## 6. Zero-Disruption Remediation Recommendation

### 6.1 The Problem
Non-interactive SSH sessions (and any script that does not activate the venv) cannot find `hermes` on PATH. The symlink at `~/.local/bin/hermes` exists and is valid, but `~/.local/bin` is not on the default PATH for non-interactive shells.

### 6.2 Recommended Fix (Minimal, No Destructive Changes)

**Add `. "$HOME/.local/bin/env"` before the interactive guard in `.bashrc`.**

Edit `~/.bashrc` and move the line:
```bash
. "$HOME/.local/bin/env"
```
from the end of the file to **before** the interactive check block:
```bash
# ~/.bashrc: executed by bash(1) for non-login shells.
. "$HOME/.local/bin/env"          # <-- ADD HERE

# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac
```

This ensures:
- Non-interactive shells get `~/.local/bin` on PATH (so `hermes` is findable)
- Interactive shells still get it (the line at the end becomes redundant but harmless)
- No symlinks, no bashrc edits beyond this one line move, no systemd changes
- The `env` file itself is idempotent (checks for existing PATH entry)

### 6.3 Alternative (Already Configured)
Use the full path in all scripts:
```bash
/home/guinevere/code/guinevere/.venv/bin/hermes <subcommand>
```
Or activate the venv:
```bash
source /home/guinevere/code/guinevere/.venv/bin/activate && hermes <subcommand>
```

### 6.4 What NOT to Change
| Item | Reason |
|------|--------|
| Systemd service | Already correct — explicit PATH, full ExecStart path |
| `~/.local/bin/hermes` symlink | Valid and correct |
| `.profile` | Works correctly for login shells |
| `/home/guinevere/code/guinevere/.venv/bin/hermes` | Primary executable — no changes needed |

---

## 7. Conclusions

| Question | Answer |
|----------|--------|
| Does `hermes` CLI exist? | ✅ Yes — at `/home/guinevere/code/guinevere/.venv/bin/hermes` |
| Does it work via project venv? | ✅ Yes — `source /home/guinevere/code/guinevere/.venv/bin/activate && hermes` works |
| Are backup subcommands available? | ✅ Yes — `hermes backup --help` confirms zip-based backup |
| Are checkpoints subcommands available? | ✅ Yes — `hermes checkpoints status` works (0 B currently) |
| Does systemd PATH need update? | ❌ No — already explicitly set with both `.local/bin` and project venv |
| Does user PATH need update? | ⚠️ Only for non-interactive shells — simple `.bashrc` edit can fix |
| Safe to proceed with Phase 7c? | ✅ Yes — no blockers found |

---

## 8. Appendix: Commands Executed

All commands were run via `ssh guinevere-vps '<command>'` with no side effects:
- `which hermes` — confirmed not on PATH for non-interactive shells
- `ls ~/.local/bin/hermes` — symlink exists
- `ls /home/guinevere/.venv/bin/hermes` — default venv path absent
- `ls /home/guinevere/code/guinevere/.venv/bin/hermes` — primary executable
- `echo $PATH` — non-interactive PATH
- `bash -l -c "echo \$PATH"` — login shell PATH
- `source .../activate && which hermes` — confirmed venv activation works
- `source .../activate && hermes --version` — v0.15.2
- `source .../activate && hermes --help` — all subcommands listed
- `source .../activate && hermes backup --help` — backup available
- `source .../activate && hermes checkpoints --help` — checkpoints available
- `source .../activate && hermes checkpoints status` — read-only status
- `source .../activate && hermes doctor` — read-only diagnosis
- `systemctl cat hermes-gateway` — full unit file inspected
- `cat ~/.bashrc ~/.profile` — shell configs inspected
- `cat ~/.local/bin/env` — PATH addition script inspected
