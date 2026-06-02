# MCP Server Security Patterns — Research Report

**Date**: 2026-06-02
**Scope**: Filesystem path whitelist, shell command whitelist/danger blocking, git operation-level auth
**Downstream**: P6-006 (filesystem Write-Notify), P6-013 (git Write-Notify), P6-016 (shell Destructive-Approval)

---

## 1. FILESYSTEM MCP — Path Whitelist Enforcement

### 1.1 Official MCP Filesystem Server (Node.js/TypeScript)

**Repo**: [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) @ `64b1cb0208cc49a4f5ae55fa71df5cf67a3cdc3d`

#### Core Pattern: `isPathWithinAllowedDirectories()`

**Evidence** ([path-validation.ts](https://github.com/modelcontextprotocol/servers/blob/64b1cb0208cc49a4f5ae55fa71df5cf67a3cdc3d/src/filesystem/path-validation.ts#L11-L86)):

Key security attributes:
- **Null byte rejection**: `absolutePath.includes('\x00')` → reject (line 23)
- **Path normalization**: `path.resolve(path.normalize(absolutePath))` (line 30)
- **Prefix collision protection**: Uses `normalizedPath.startsWith(normalizedDir + path.sep)` NOT raw `startsWith` (line 84) — prevents `/home/user/project2` matching `/home/user/project`
- **Root directory special case**: `normalizedDir === path.sep` handled (lines 72-74)
- **Windows drive root handling**: Drive letter prefix with separator enforcement (lines 77-82)

#### Validation Pipeline: `validatePath()`

**Evidence** ([lib.ts](https://github.com/modelcontextprotocol/servers/blob/64b1cb0208cc49a4f5ae55fa71df5cf67a3cdc3d/src/filesystem/lib.ts#L99-L140)):

4-stage pipeline:
1. `expandHome()` → resolve `~`
2. `path.resolve()` → absolute path
3. `isPathWithinAllowedDirectories()` → boundary check
4. `fs.realpath()` → symlink resolution, then re-check boundary

For non-existent files: validates parent directory's realpath instead (lines 125-133).

#### Atomic Writes: TOCTOU Prevention

**Evidence** ([lib.ts](https://github.com/modelcontextprotocol/servers/blob/64b1cb0208cc49a4f5ae55fa71df5cf67a3cdc3d/src/filesystem/lib.ts#L161-L185)):

```typescript
// Stage 1: O_EXCL for new files (fails if symlink exists)
await fs.writeFile(filePath, content, { flag: 'wx' });

// Stage 2: If EEXIST, write to random temp file then atomic rename
const tempPath = `${filePath}.${randomBytes(16).toString('hex')}.tmp`;
await fs.writeFile(tempPath, content, 'utf-8');
await fs.rename(tempPath, filePath);  // rename doesn't follow symlinks
```

`fs.rename()` is the key: it replaces the target atomically without following symlinks.

#### Directory Access Control

**Evidence** ([lib.ts](https://github.com/modelcontextprotocol/servers/blob/64b1cb0208cc49a4f5ae55fa71df5cf67a3cdc3d/src/filesystem/lib.ts#L11-L21)):

```
setAllowedDirectories(dirs)  // Replace whitelist
getAllowedDirectories()      // Read current whitelist
```

Two configuration methods:
1. **CLI args** at startup
2. **MCP Roots protocol** for runtime updates via `roots/list_changed` notifications

#### Tool Annotations: read-only/write/destructive hints

Each tool declares:
- `readOnlyHint`: true/false
- `idempotentHint`: true/false (for write tools)
- `destructiveHint`: true/false

This enables clients to auto-approve safe reads while gating writes.

### 1.2 Go Filesystem MCP Server (`portertech/filesystem-mcp-server`)

**Repo**: [portertech/filesystem-mcp-server](https://github.com/portertech/filesystem-mcp-server) @ `3b3e5a05d7d2bfb107dc9e7583315976cc8bf897`

#### Path Validation with Symlink TOCTOU Protection

**Evidence** ([security/validate.go](https://github.com/portertech/filesystem-mcp-server/blob/3b3e5a05d7d2bfb107dc9e7583315976cc8bf897/internal/security/validate.go#L25-L86)):

`ValidatePath()` — 6 checkpoints:
1. Empty path → `ErrEmptyPath`
2. Null byte → `ErrNullByte`
3. `pathutil.NormalizePath()` — `ExpandHome()` + `filepath.Abs()` + `filepath.Clean()`
4. `os.Lstat()` → detect symlinks
5. `filepath.EvalSymlinks()` — resolve symlinks
6. `IsPathWithinAllowedDirectories()` — boundary check with resolved paths

Separation of concerns with distinct validators:
- `ValidatePath()` — for reads, follows symlinks if target is allowed
- `ValidateFinalPath()` — for writes/deletes, **rejects symlinks** entirely
- `ValidatePathForCreation()` — for new files, walks up to existing parent
- `ValidateNoSymlinksInPath()` — walks each path segment checking for symlinks (prevents TOCTOU during directory creation)

#### Prefix Collision Protection

**Evidence** ([security/validate.go](https://github.com/portertech/filesystem-mcp-server/blob/3b3e5a05d7d2bfb107dc9e7583315976cc8bf897/internal/security/validate.go#L209-L233)):

```go
// Add separator to prevent /tmp matching /tmpfoo
if strings.HasPrefix(cleanPath, cleanAllowed+string(filepath.Separator)) {
    return true
}
```

Exact same pattern as the Node.js version — requires trailing separator.

#### Atomic Writes via O_EXCL Temp Files

**Evidence** ([tools/write.go](https://github.com/portertech/filesystem-mcp-server/blob/3b3e5a05d7d2bfb107dc9e7583315976cc8bf897/internal/tools/write.go#L56-L105)):

```go
// O_EXCL prevents symlink attacks on new files
f, err := os.OpenFile(tmpName, os.O_WRONLY|os.O_CREATE|os.O_EXCL, perm)
// ... write, sync, close ...
os.Rename(tmpName, path)  // atomic rename
```

Also validates parent directories with `safeMkdirAll()` which calls `ValidateNoSymlinksInPath()` to prevent symlink TOCTOU in directory creation path.

#### Thread-Safe Directory Registry

**Evidence** ([registry/directories.go](https://github.com/portertech/filesystem-mcp-server/blob/3b3e5a05d7d2bfb107dc9e7583315976cc8bf897/internal/registry/directories.go#L22-L162)):

- `sync.RWMutex` for concurrent read safety
- Pre-resolves symlinks at init time (`resolved []string`)
- `Set()` replaces entire set atomically
- `Validate()` and `ValidateForCreation()` methods with pre-resolved dirs

### 1.3 Known CVEs and Mitigations

**Key CVEs**: CVE-2025-53110 (prefix matching bypass), CVE-2025-53109 (symlink bypass)
- Both have been patched with the trailing-separator and full symlink resolution patterns above

---

## 2. SHELL MCP — Command Whitelist & Dangerous Command Blocking

### 2.1 `blazickjp/shell-mcp-server` (Python)

**Repo**: [blazickjp/shell-mcp-server](https://github.com/blazickjp/shell-mcp-server) @ `309537a344fd48325644876dcb552bb39eb7a6fc`

**Evidence** ([config.py](https://github.com/blazickjp/shell-mcp-server/blob/309537a344fd48325644876dcb552bb39eb7a6fc/src/shell_mcp_server/config.py#L14-L44)):

Pattern: **Directory whitelist + Shell whitelist**

```python
class Settings:
    ALLOWED_DIRECTORIES: List[str]  # cwd must be within one of these
    ALLOWED_SHELLS: Dict[str, str]  # shell name → absolute path
    COMMAND_TIMEOUT: int = 30

    def is_path_allowed(self, path: str) -> bool:
        abs_path = os.path.abspath(path)
        return any(abs_path.startswith(allowed_dir) for allowed_dir in self.ALLOWED_DIRECTORIES)
```

**Evidence** ([server.py](https://github.com/blazickjp/shell-mcp-server/blob/309537a344fd48325644876dcb552bb39eb7a6fc/src/shell_mcp_server/server.py#L62-L108)):

Dual validation at runtime:
1. `settings.is_path_allowed(cwd)` — working directory check
2. `shell not in settings.ALLOWED_SHELLS` — shell binary check
3. Platform-aware execution (`shell_cmd = [shell_path, '-c', command]`)
4. `asyncio.wait_for()` with timeout — prevents runaway processes

**Limitation**: No command-level whitelist/danger list — relies on shell-path restriction and directory sandbox only.

### 2.2 Comprehensive Dangerous Command Lists

#### PraisonAI — Production-Grade List

**Evidence** ([PraisonAI execute_command.py](https://github.com/MervinPraison/PraisonAI/blob/main/src/praisonai/praisonai/code/tools/execute_command.py#L19-L37)):

```python
DANGEROUS_COMMANDS = {
    'rm', 'rmdir', 'del', 'format', 'mkfs',
    'dd', 'shred', 'chmod', 'chown', 'chgrp',
    'kill', 'killall', 'pkill',
    'shutdown', 'reboot', 'halt', 'poweroff',
    'sudo', 'su', 'doas',
    'curl', 'wget', 'ssh', 'scp', 'rsync',
    'mv', 'cp',  # Can be destructive
}

# Regex patterns for destructive intent
_FORBIDDEN_PATTERNS = [
    re.compile(r'rm\s+-[rf]{1,2}\s+[/~]'),       # rm -rf / or ~/
    re.compile(r'rm\s+-[rf]{1,2}\s+\.'),          # rm -rf .
    re.compile(r'>\s*/dev/(sd[a-z]|nvme|hd[a-z])'),  # Overwrite disk
    re.compile(r'mkfs\b'),                         # Format filesystem
]
```

#### OpenDerisk — Concise Minimal List

**Evidence** ([OpenDerisk local_sandbox.py](https://github.com/derisk-ai/OpenDerisk/blob/main/packages/derisk-core/src/derisk_core/sandbox/local_sandbox.py#L6-L14)):

```python
FORBIDDEN_COMMANDS = {
    "rm -rf /", "mkfs", "dd if=/dev/zero",
    ":(){ :|:& };:",  # Fork bomb
}
```

#### Agent0 — Comprehensive Extended List

**Evidence** ([Agent0 bash_session.py](https://github.com/aiming-lab/Agent0/blob/main/Agent0/executor_train/verl_tool/servers/tools/utils/bash_session.py#L16-L30)):

```python
forbidden_commands = [
    'rm -rf /', 'dd if=', 'mkfs', 'fdisk', 'mount', 'umount',
    'passwd', 'su ', 'sudo ', 'chroot', 'systemctl', 'service',
    'iptables', 'ufw', 'firewall-cmd',
    'nc ', 'ncat ', 'telnet ', 'ssh ', 'scp ', 'rsync ',
    'curl http', 'wget http', 'lynx', 'w3m',
    'crontab', 'batch',
]
```

#### ruvnet/ruflo — TypeScript Reference

**Evidence** ([ruflo safe-executor.ts](https://github.com/ruvnet/ruflo/blob/main/v3/%40claude-flow/security/src/safe-executor.ts#L124-L133)):

```typescript
const DANGEROUS_COMMANDS = [
    'rm', 'rmdir', 'del', 'format', 'mkfs',
    'dd', 'shred', 'chmod', 'chown', 'chgrp',
    'kill', 'killall', 'pkill',
    'shutdown', 'reboot', 'halt', 'poweroff',
    'sudo', 'su', 'doas',
    'curl', 'wget',
];
```

#### AWS Labs AgentCore — Pattern-Focused

**Evidence** ([AWSLabs agent.py](https://github.com/awslabs/agentcore-samples/blob/main/03-integrations/agentic-frameworks/claude-agent/claude-hooks/agent.py#L26)):

```python
BLOCKED_COMMANDS = ["rm -rf /", "rm -rf /*", "mkfs.", ":(){:|:&}:;", "dd if=/dev/zero"]
BLOCKED_WRITE_PATHS = ["/etc/", "/usr/", "/sys/", "/proc/", "/boot/"]
```

### 2.3 Recommended Unified Blocked Command List

Based on synthesis of all implementations above, here is the canonical categorized list:

**Category: Data Destruction**
| Command | Risk |
|---|---|
| `rm`, `rmdir`, `del` | File/directory deletion |
| `rm -rf /`, `rm -rf /*`, `rm -rf ~` | Root/home wipe |
| `dd if=`, `dd if=/dev/zero` | Disk overwrite |
| `shred` | Secure file wipe |
| `mkfs`, `fdisk`, `format` | Filesystem format/partition |
| `> /dev/sd*`, `> /dev/nvme*`, `> /dev/hd*` | Raw disk overwrite |

**Category: Privilege Escalation**
| Command | Risk |
|---|---|
| `sudo`, `su`, `doas`, `chroot` | Root access |
| `chmod`, `chown`, `chgrp` | Permission changes |
| `passwd` | Password manipulation |

**Category: System Control**
| Command | Risk |
|---|---|
| `shutdown`, `reboot`, `halt`, `poweroff` | System power |
| `kill`, `killall`, `pkill` | Process termination |
| `systemctl`, `service` | Service control |
| `crontab`, `batch`, `at` | Scheduled tasks |

**Category: Network Exfiltration & Remote Access**
| Command | Risk |
|---|---|
| `curl`, `wget` | Data exfiltration |
| `ssh`, `scp`, `rsync` | Remote access |
| `nc`, `ncat`, `telnet` | Raw network |
| `iptables`, `ufw`, `firewall-cmd` | Firewall changes |
| `mount`, `umount` | Filesystem mount |
| `:(){ :\|:& };:` | Fork bomb |

### 2.4 Command Whitelist Approach

For P6-016 (shell Destructive-Approval), the recommended approach is a **tiered model**:

1. **Allowlist**: Commands always allowed (e.g., `git`, `python`, `npm`, `ls`, `cat`, `grep`, `find`)
2. **Require Approval**: Commands in the dangerous list above — require explicit operator approval
3. **Blocked**: Commands matching `_FORBIDDEN_PATTERNS` regex patterns — never execute

Additional protections:
- Command substitution blocking: reject `$()`, backticks, `<()`, `>()`
- Path argument validation: extract all paths from command args and validate against allowed directories
- Timeout: hard timeout (30s default)
- Process group: kill entire process tree on timeout

---

## 3. GIT MCP — Operation-Level Auth

### 3.1 Official GitHub MCP Server (Go)

**Repo**: [github/github-mcp-server](https://github.com/github/github-mcp-server) @ `2a5d38a2825519e109bcbd3ccfd13a459582a455`

This is the reference implementation. It does NOT directly execute local `git` CLI commands — it uses the GitHub API via `go-github` SDK.

#### Read-Only Tool Enforcement via AST-Level Static Analysis

**Evidence** ([toolvalidation/readonlyhint.go](https://github.com/github/github-mcp-server/blob/2a5d38a2825519e109bcbd3ccfd13a459582a455/pkg/toolvalidation/readonlyhint.go#L45-L59)):

```go
// ScanReadOnlyHint parses every non-test .go file and returns a violation for
// each mcp.Tool composite literal that does NOT explicitly set
// Annotations.ReadOnlyHint.
```

This is a **compile-time enforcement**: no tool can be registered without explicitly declaring whether it's read-only. Every tool registration looks like:

```go
mcp.Tool{
    Name: "get_repository_tree",
    Annotations: &mcp.ToolAnnotations{
        ReadOnlyHint: true,  // MUST be explicitly set
    },
    // ...
}
```

#### OAuth Scope-Based Tool Filtering

**Evidence** ([scope_filter.go](https://github.com/github/github-mcp-server/blob/2a5d38a2825519e109bcbd3ccfd13a459582a455/pkg/github/scope_filter.go#L42-L64)):

```go
func CreateToolScopeFilter(tokenScopes []string) inventory.ToolFilter {
    return func(_ context.Context, tool *inventory.ServerTool) (bool, error) {
        // Read-only tools requiring only repo/public_repo work on public repos without any scope
        if tool.Tool.Annotations.ReadOnlyHint && onlyRequiresRepoScopes(tool.AcceptedScopes) {
            return true, nil
        }
        return scopes.HasRequiredScopes(tokenScopes, tool.AcceptedScopes), nil
    }
}
```

Dual-axis filtering:
1. Read-only tools with `repo`/`public_repo` scope → always available (public repos don't need auth)
2. Write tools or tools needing other scopes → filtered by token scopes

#### Multi-Layer Filter Pipeline

**Evidence** ([filters.go](https://github.com/github/github-mcp-server/blob/2a5d38a2825519e109bcbd3ccfd13a459582a455/pkg/inventory/filters.go#L85-L121)):

```go
func (r *Inventory) isToolEnabled(ctx context.Context, tool *ServerTool) bool {
    // 1. Tool's own Enabled function
    // 2. Read-only filter (WithReadOnly)
    // 3. Builder filters (OAuth scopes, feature flags)
    // 4. Toolset filter (enabled categories)
}
```

Filters are composed declaratively:
```go
reg := NewBuilder().
    SetTools(tools).
    WithReadOnly(true).         // only read tools
    WithToolsets([]string{"repos", "issues"}).  // only these categories
    WithFilter(CreateToolScopeFilter(tokenScopes)).
    Build()
```

#### Inventory Architecture

**Evidence** ([registry.go](https://github.com/github/github-mcp-server/blob/2a5d38a2825519e109bcbd3ccfd13a459582a455/pkg/inventory/registry.go#L27-L63)):

```go
type Inventory struct {
    tools              []ServerTool
    readOnly           bool               // if true, filter out write tools
    enabledToolsets    map[ToolsetID]bool // category whitelist
    filters            []ToolFilter       // pluggable filters (OAuth, feature flags)
    featureChecker     FeatureFlagChecker
}
```

### 3.2 Git Tool Annotations Pattern

Every tool in the official GitHub MCP server declares its read/write status:

**Evidence** ([git.go](https://github.com/github/github-mcp-server/blob/2a5d38a2825519e109bcbd3ccfd13a459582a455/pkg/github/git.go#L42-L52)):

```go
// Read example: get_repository_tree
Tool{
    Name: "get_repository_tree",
    Annotations: &mcp.ToolAnnotations{
        Title:        "Get repository tree",
        ReadOnlyHint: true,  // ← explicit
    },
    // ...
}

// Write example: create_or_update_file
Tool{
    Name: "create_or_update_file",
    Annotations: &mcp.ToolAnnotations{
        Title:        "Create or update file",
        ReadOnlyHint: false,           // ← explicit
        DestructiveHint: true,         // ← explicit
        IdempotentHint: false,         // ← explicit
    },
    // ...
}
```

### 3.3 Recommended Git MCP Security Pattern (for P6-013)

For a local `git` CLI-based MCP server (not GitHub API), the recommended pattern:

**Operation Classification**:
```
Read-Only (auto-allow):
  git status, git log, git show, git diff, git stash list
  git branch --list, git tag --list, git remote --verbose
  git config --get, git describe, git rev-parse

Idempotent Write (approve once, safe to retry):
  git stash push/pop, git branch --delete (safe if merged)
  git tag --annotate, git config --set

Destructive Write (explicit approval required):
  git push, git push --force, git push --delete
  git reset --hard, git clean -fd, git checkout --
  git rebase, git rebase --abort/--skip/--continue
  git commit --amend (already pushed), git reflog delete
  git branch -D (force delete)
```

**Implementation Pattern**:
```python
OPERATIONS = {
    "read": {
        "commands": ["status", "log", "show", "diff", "branch", "tag", "remote", "config", "describe", "rev-parse", "stash list"],
        "flags": ["--list", "--get", "--verbose", "--oneline", "--name-only", "--name-status"],
    },
    "write_idempotent": {
        "commands": ["stash", "branch -d", "tag -a", "config --add"],
    },
    "write_destructive": {
        "commands": ["push", "reset", "clean", "rebase", "commit --amend"],
        "flags": ["--force", "--hard", "--delete", "-f", "-D"],
        "require_approval": True,
    },
}
```

---

## 4. Cross-Cutting Security Patterns

### 4.1 Tool Annotations (MCP Spec)

Every tool in MCP should declare three booleans:

| Annotation | Meaning | Client Behavior |
|---|---|---|
| `readOnlyHint` | No side effects, no state change | Auto-approve |
| `idempotentHint` | Safe to retry with same args | Client can retry on failure |
| `destructiveHint` | Overwrites or mutates existing data | Client should gate with approval |

Official filesystem server mapping example:

| Tool | readOnlyHint | idempotentHint | destructiveHint |
|---|---|---|---|
| `read_text_file` | true | — | — |
| `write_file` | false | true | true |
| `edit_file` | false | false | true |
| `move_file` | false | false | true |

### 4.2 Defense-in-Depth Stack

For maximum security, layer all three patterns:

1. **Process isolation**: Container/sandbox with read-only root filesystem, dropped capabilities
2. **Path whitelist**: Exact directory allowlist with separator-enforced prefix matching
3. **Symlink resolution**: `realpath()`/`EvalSymlinks()` before every boundary check
4. **Atomic writes**: Temp file + `O_EXCL` + rename pattern
5. **TOCTOU prevention**: Reject symlinks for write operations
6. **Command whitelist**: Tiered allowlist/approve/block system
7. **Timeout enforcement**: Hard timeouts on all operations
8. **Audit logging**: Structured logs with redaction for all tool invocations

### 4.3 Prefix Collision Prevention (Critical Pattern)

The single most important security pattern shared across all implementations:

```python
# WRONG — prefix collision vulnerable
if path.startswith(allowed_dir):
    return True  # /tmp/foo matches /tmp/foobar

# CORRECT — separator enforcement
if path == allowed_dir or path.startswith(allowed_dir + os.sep):
    return True  # /tmp/foobar does NOT match /tmp/foo
```

Both the official Node.js server and the Go server implement this identically.

---

## 5. Source References

| Source | SHA/Ref | Key File |
|---|---|---|
| Official MCP Filesystem (TS) | `64b1cb0` | `src/filesystem/path-validation.ts` |
| Official MCP Filesystem (TS) | `64b1cb0` | `src/filesystem/lib.ts` |
| Go Filesystem MCP Server | `3b3e5a0` | `internal/security/validate.go` |
| Go Filesystem MCP Server | `3b3e5a0` | `internal/tools/write.go` |
| Go Filesystem MCP Server | `3b3e5a0` | `internal/registry/directories.go` |
| Shell MCP Server (Python) | `309537a` | `src/shell_mcp_server/config.py` |
| Shell MCP Server (Python) | `309537a` | `src/shell_mcp_server/server.py` |
| PraisonAI | — | `praisonai/code/tools/execute_command.py` |
| ruvnet/ruflo (TS) | — | `v3/@claude-flow/security/src/safe-executor.ts` |
| AWSLabs AgentCore | — | `claude-hooks/agent.py` |
| Agent0 (bash_session) | — | `tools/utils/bash_session.py` |
| OpenDerisk (Python) | — | `sandbox/local_sandbox.py` |
| Official GitHub MCP (Go) | `2a5d38a` | `pkg/github/scope_filter.go` |
| Official GitHub MCP (Go) | `2a5d38a` | `pkg/toolvalidation/readonlyhint.go` |
| Official GitHub MCP (Go) | `2a5d38a` | `pkg/inventory/filters.go` |
| Official GitHub MCP (Go) | `2a5d38a` | `pkg/inventory/registry.go` |

---

## 6. Downstream Implementation Recommendations

### P6-006 (filesystem — Write-Notify, Path Whitelist)
- Implement `isPathWithinAllowedDirectories()` using separator-enforced prefix matching (from §1.1)
- Implement `validatePath()` 4-stage pipeline (from §1.1)
- Add atomic writes with temp-file + `O_EXCL` + rename (from §1.2)
- Add tool annotations: `readOnlyHint`, `idempotentHint`, `destructiveHint`
- Monitor `allowedDirectories` via config, reject runtime changes without explicit re-auth

### P6-013 (git — Write-Notify)
- Classify all git operations into read / idempotent-write / destructive-write (from §3.3)
- Add `Write-Notify` hook: intercept write-classified operations before execution
- Gate destructive operations: `push --force`, `reset --hard`, `clean -fd` require approval
- Register tool annotations on every operation

### P6-016 (shell — Destructive-Approval with Command Whitelist)
- Implement tiered command model: allowlist / require-approval / blocked (from §2.4)
- Deploy the unified blocked command list (from §2.3)
- Add regex patterns for `rm -rf /`, `> /dev/sd*`, `mkfs` (from §2.2)
- Reject command substitution (`$()`, backticks, process substitution)
- Extract and validate file/directory paths from command arguments against allowed directories
- Add timeout enforcement with process-group kill