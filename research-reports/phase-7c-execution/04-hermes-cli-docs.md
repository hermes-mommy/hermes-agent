# Hermes Agent CLI, Backup, Checkpoint & Install/PATH Research

**Date**: 2026-06-06
**Source**: [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) (official repo)
**Docs**: <https://hermes-agent.nousresearch.com/docs/>

---

## 1. Project Identity

| Field | Value |
|-------|-------|
| Project | **Hermes Agent** by Nous Research |
| Repo | <https://github.com/NousResearch/hermes-agent> |
| License | MIT |
| CLI entrypoint | `hermes` |
| Docs home | <https://hermes-agent.nousresearch.com/docs/> |
| CLI reference | <https://hermes-agent.nousresearch.com/docs/reference/cli-commands> |

---

## 2. CLI Executable: `hermes`

The single entry point is the `hermes` command:

```bash
hermes [global-options] <command> [subcommand/options]
```

Global options include `--version`, `--profile`, `--resume`, `--checkpoints`, `--yolo`, `--tui`, `--cli`, etc.

Full CLI reference with all commands:
<https://hermes-agent.nousresearch.com/docs/reference/cli-commands>

---

## 3. Backup Command: `hermes backup`

**Docs**: <https://hermes-agent.nousresearch.com/docs/reference/cli-commands#hermes-backup>

Creates a zip archive of Hermes configuration, skills, sessions, and data. Excludes the hermes-agent codebase itself.

### Usage

```bash
hermes backup                          # Full backup to ~/hermes-backup-<date>.zip
hermes backup -o /path/to/output.zip   # Full backup to specific path
hermes backup --quick                  # Quick: only critical state files
hermes backup --quick --label "pre-upgrade"  # Labeled quick snapshot
```

### Options

| Option | Description |
|--------|-------------|
| `-o`, `--output <path>` | Output path for zip (default: `~/hermes-backup-<date>.zip`) |
| `-q`, `--quick` | Quick snapshot: only config.yaml, state.db, .env, auth, cron jobs |
| `-l`, `--label <label>` | Label for quick snapshot |

### Exclusions

The backup **excludes**:
- `*.db-wal`, `*.db-shm`, `*.db-journal` — SQLite WAL/shared-memory/journal sidecars (the `.db` file uses `sqlite3.backup()` for consistent snapshot)
- `checkpoints/` — per-session trajectory caches (hash-keyed, regenerated per session)
- The `hermes-agent` code itself (user-data backup only)

### Safety

- Uses SQLite's `backup()` API — safe to run while Hermes is running (WAL-mode safe).
- PR #7997 added this command; docs issue #8488 (closed) tracked documenting it.

---

## 4. Import Command: `hermes import`

**Docs**: <https://hermes-agent.nousresearch.com/docs/reference/cli-commands#hermes-import>

Restores a previously created Hermes backup zip into your Hermes home directory.

### Usage

```bash
hermes import ~/hermes-backup-20260423.zip         # Prompts before overwriting
hermes import ~/hermes-backup-20260423.zip --force # Skip confirmation prompt
```

### Options

| Option | Description |
|--------|-------------|
| `-f`, `--force` | Skip the existing-installation confirmation prompt |

### Safety Warnings

- **Stop the gateway before importing** to avoid conflicts with running processes (from docs).
- All files in the archive overwrite existing files in your Hermes home directory.

---

## 5. Checkpoints: `hermes checkpoints` & `/rollback`

**Docs**: <https://hermes-agent.nousresearch.com/docs/user-guide/checkpoints-and-rollback>

### Architecture

The checkpoint system uses shadow git repos under `~/.hermes/checkpoints/<hash>/` — a per-project shadow store. The real project `.git` is never touched.

Checkpoints are **opt-in per session** (as of v2):

```bash
hermes chat --checkpoints
```

Configure defaults in `~/.hermes/config.yaml`:

```yaml
checkpoints:
  enabled: true           # master switch (default in v1 was on, v2 is off)
  max_snapshots: 50       # max checkpoints per directory
  max_size_mb: 500        # max total checkpoint store size
```

### CLI Commands: `hermes checkpoints`

| Subcommand | Description |
|------------|-------------|
| `status` (default) | Show total size, project count, per-project breakdown |
| `list` | Alias for status |
| `prune` | Force cleanup sweep — delete orphans/stale, GC, enforce size cap |
| `clear` | Nuke the entire checkpoint base (asks unless `-f`) |
| `clear-legacy` | Delete only `legacy-*` archives from v1 migration |

Prune flags:

| Option | Description |
|--------|-------------|
| `--retention-days N` | Drop projects last touched > N days ago (default: 7) |
| `--max-size-mb N` | Drop oldest commits until ≤ N MB (default: 500) |
| `--keep-orphans` | Skip deleting projects whose cwd no longer exists |
| `-f`, `--force` | Skip confirmations (for clear/clear-legacy) |

### In-Session Slash Commands: `/rollback`

| Command | Description |
|---------|-------------|
| `/rollback` | List all checkpoints with change stats |
| `/rollback <N>` | Restore to checkpoint N (also undoes last chat turn) |
| `/rollback diff <N>` | Preview diff between checkpoint N and current state |
| `/rollback <N> <file>` | Restore a single file from checkpoint N |

### Triggered By

Checkpoints are automatically created before:
- File tools: `write_file`, `patch`
- Destructive terminal commands: `rm`, `rmdir`, `cp`, `install`, `mv`, `sed -i`, `truncate`, `dd`, `shred`, `>`, `>>`, `git reset`/`clean`/`checkout`

### Safety

- Safe to run `hermes checkpoints` any time — does not require agent to be running.
- `hermes checkpoints clear` is **irreversible** — asks for confirmation.
- Checkpoints don't survive restore to another install (hash-keyed per session).

---

## 6. Install Layout & PATH Conventions

**Docs**: <https://github.com/NousResearch/hermes-agent/blob/main/website/docs/getting-started/installation.md>

### Install Methods

| Method | Code Location | `hermes` Binary | Data Dir |
|--------|--------------|-----------------|----------|
| **pip install** | Python site-packages | `~/.local/bin/hermes` (console_scripts) | `~/.hermes/` |
| **Per-user (git installer)** | `~/.hermes/hermes-agent/` | `~/.local/bin/hermes` (symlink to venv) | `~/.hermes/` |
| **Root-mode** (`sudo curl ... | sudo bash`) | `/usr/local/lib/hermes-agent/` | `/usr/local/bin/hermes` | `/root/.hermes/` (or `$HERMES_HOME`) |

### The `~/.local/bin/hermes` Symlink Convention

The **official, documented** install path for per-user installations is `~/.local/bin/hermes`, which is a **symlink** into the venv:

- **pip install**: Python's `console_scripts` entry point → `~/.local/bin/hermes`
- **Git installer**: Explicit symlink → `~/.local/bin/hermes` → `~/.hermes/hermes-agent/venv/bin/hermes`

This is the **recommended** approach in the official docs.

### PATH Setup

The installer adds `~/.local/bin` to your shell's PATH via `~/.bashrc`/`~/.zshrc`. After installation:

```bash
source ~/.bashrc   # or: source ~/.zshrc
```

If `hermes: command not found`, the FAQ says:

> **The installer adds `~/.local/bin` to your PATH. If you use a non-standard shell config, add `export PATH="$HOME/.local/bin:$PATH"` manually.**

Source: <https://hermes-agent.nousresearch.com/docs/reference/faq#hermes-command-not-found-after-installation>

---

## 7. Systemd Service & PATH for Unprivileged Users

**Docs**: <https://hermes-agent.nousresearch.com/docs/getting-started/installation#non-sudo--system-service-user-installs>

### Official Guidance

This is directly relevant to Phase 7c VPS setup. The installation docs explicitly cover running Hermes as a dedicated unprivileged user:

> **Running Hermes as a dedicated unprivileged user (e.g. a `hermes` systemd service account) is supported.**

**Key PATH concern for systemd services:**

> **The installer writes the launcher to `~/.local/bin/hermes`. System service accounts often have a minimal PATH that doesn't include `~/.local/bin`. Either add it to the user's environment, or symlink the launcher into a system location:**

**Option A** — Add to service user's profile:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

**Option B** — Symlink system-wide (run as admin):
```bash
sudo ln -s /home/hermes/.hermes/hermes-agent/venv/bin/hermes /usr/local/bin/hermes
```

### Gateway Systemd Service Installation

```bash
hermes gateway install               # Install as user service (Linux)
sudo hermes gateway install --system # Install as boot-time system service (Linux)
hermes gateway start                 # Start the service
hermes gateway status                # Check status
journalctl --user -u hermes-gateway -f  # View user service logs
journalctl -u hermes-gateway -f         # View system service logs
```

**Important systemd detail**: The gateway captures your shell PATH at install time. The docs warn:

> **launchd plists are static — if you install new tools after setting up the gateway, run `hermes gateway install` again to capture the updated PATH.**

On Linux, there is no static PATH capture mentioned for systemd (systemd uses the service user's PATH), but the same principle applies for tool availability.

---

## 8. Symlinking Venv CLI into `~/.local/bin`: Assessment

### Is it conventional?

**Yes.** The official installer does exactly this:
- Per-user installs place `hermes` at `~/.local/bin/hermes` as a symlink to the venv binary
- This follows the XDG base directory / POSIX convention for per-user binaries
- Python's `pip install --user` also places console_scripts in `~/.local/bin`

### Is it safe?

**Yes, with caveats:**

1. **`~/.local/bin` must be in PATH.** Systemd service users typically have a minimal PATH that doesn't include it — the docs explicitly address this.

2. **The symlink target must not break.** If the venv Python or the repo path changes, the symlink becomes dangling. The installer manages this, but manual symlinks need maintenance.

3. **Alternative for systemd: symlink to `/usr/local/bin`.** The docs explicitly recommend this for service accounts when PATH manipulation is impractical:
   ```bash
   sudo ln -s /home/hermes/.hermes/hermes-agent/venv/bin/hermes /usr/local/bin/hermes
   ```

### Caveats for systemd

- **PATH isolation**: systemd units run with a minimal PATH (`/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin` by default). If using `~/.local/bin`, ensure it's added to the service unit's `Environment=` or service user's profile.
- **Virtual env activation**: The `hermes` launcher script in the venv `bin/` handles Python/env resolution — symlinking it directly is safe because it's a self-contained wrapper.
- **Gateway PATH capture**: `hermes gateway install` captures the current PATH for launchd (macOS). On Linux systemd, the unit inherits the service user's environment — ensure `~/.local/bin` (or the symlink target) is resolvable.

---

## 9. Key Documentation URLs

| Resource | URL |
|----------|-----|
| Hermes Agent Homepage | <https://hermes-agent.nousresearch.com/> |
| CLI Commands Reference | <https://hermes-agent.nousresearch.com/docs/reference/cli-commands> |
| Installation Guide | <https://hermes-agent.nousresearch.com/docs/getting-started/installation> |
| Checkpoints & Rollback | <https://hermes-agent.nousresearch.com/docs/user-guide/checkpoints-and-rollback> |
| Messaging Gateway | <https://hermes-agent.nousresearch.com/docs/user-guide/messaging/> |
| FAQ & Troubleshooting | <https://hermes-agent.nousresearch.com/docs/reference/faq> |
| Updating & Uninstalling | <https://hermes-agent.nousresearch.com/docs/getting-started/updating> |
| GitHub Repo | <https://github.com/NousResearch/hermes-agent> |
| Install Script (raw) | <https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh> |
| Installation.md (GitHub) | <https://github.com/NousResearch/hermes-agent/blob/main/website/docs/getting-started/installation.md> |
| Issue #8488 (backup docs) | <https://github.com/NousResearch/hermes-agent/issues/8488> |

---

## 10. Uncertainties & Ambiguities

1. **`hermes backup` encryption**: No mention of password/encryption for backup zips. The backup is a plain zip file. If sensitive data is in `~/.hermes/`, the zip should be stored securely.

2. **`hermes import` overwrite behavior**: Says "All files in the archive overwrite existing files" — no merge/diff mode is documented. Partial restores are not supported.

3. **Checkpoint v2 migration**: The "clear-legacy" command references v1→v2 migration archives, but the migration trigger and backward-compatibility window are not precisely documented.

4. **Systemd Environment propagation**: The docs say the gateway captures PATH for launchd at install time but don't specify if Linux systemd does the same static capture or relies on the service user's dynamic environment.

5. **`$HERMES_HOME` vs `~/.hermes/`**: The default is `~/.hermes/`. When `$HERMES_HOME` is set, it overrides the data directory. This affects backup/restore scope and systemd service resolution, but the precise interaction is only documented in passing.

---

## 11. Summary for Phase 7c

### If `hermes` command not found on VPS:

**Recommended fix (from official docs, Option B):**
```bash
sudo ln -s /home/hermes/.hermes/hermes-agent/venv/bin/hermes /usr/local/bin/hermes
```

**Alternative (Option A):**
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

### Backup workflow:
```bash
hermes backup --quick --label "pre-update-YYYYMMDD"
```
Use `--quick` for speed (state files only), omit for full data backup.

### Before destructive VPS operations:
- Take a quick backup: `hermes backup --quick`
- Leave checkpoints enabled if using interactive sessions
- The backup zip goes to `~/hermes-backup-<date>.zip` by default
