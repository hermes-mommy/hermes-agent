# F-05 Execution Evidence — BRAVE_API_KEY Missing

**Date:** 2026-06-09  
**Status:** DONE  
**File modified:** `.env.mcp`

---

## 1. How brave_search.py Loads the Key

`src/mcp/tools/brave_search.py:54-61`:

```python
def _get_api_key() -> str:
    """Return the Brave API key from the environment, or raise."""
    key = os.environ.get("BRAVE_API_KEY")
    if not key:
        raise BraveSearchConfigError(
            "BRAVE_API_KEY environment variable is required."
        )
    return key
```

**Behaviour:**
- Reads `BRAVE_API_KEY` from `os.environ` at **call time** (not import time).
- **No fallback** — raises `BraveSearchConfigError` if absent or empty.
- Tool execution fails; MCP server startup succeeds (not import-time check).

---

## 2. Key Availability Check

### SOPS Secrets Scan

```bash
$ sops --decrypt ~/secrets/*.yaml 2>/dev/null | grep -i brave
(no output)
```

**Result:** `BRAVE_API_KEY` is **NOT** present in any SOPS-encrypted YAML under `~/secrets/`.

### Env Files Scan

```bash
$ cd /home/guinevere/code/guinevere
$ ls .env.*
.env.core
.env.core.bak.2026-06-06
.env.discord
.env.hermes
.env.loops
.env.mcp
.env.monitoring
.env.scheduler
.env.surveillance

$ grep -h "BRAVE" .env.* 2>/dev/null
(no output)
```

**Result:** `BRAVE_API_KEY` is **NOT** present in any `.env.*` file.

---

## 3. Conclusion

`BRAVE_API_KEY` is **NOT provisioned** in the current environment:
- Not in SOPS-encrypted secrets (`~/secrets/*.yaml`)
- Not in any `.env.*` file

The tool `brave_search` will fail at **runtime** when called, but does not block
MCP server startup.

---

## 4. Action Taken

Added placeholder + documentation comment to `.env.mcp`:

```bash
REDIS_PASSWORD=01b00faabad3164982d0dca68cedfbdc25b28d63f3604dd5ae1bf0586ce9739b

# --- API keys (provision via SOPS before starting MCP server) ---
# BRAVE_API_KEY=<set-via-sops>   # Required by src/mcp/tools/brave_search.py — provision from SOPS
# EXA_API_KEY=<set-via-sops>     # Required by src/mcp/tools/exa_search.py — provision from SOPS
```

---

## 5. Required Provisioning Steps

Before `brave_search` can be used in production:

1. **Acquire a Brave Search API key** (free tier available at https://brave.com/search/api/)
2. **Encrypt key in SOPS:**
   ```bash
   # Add to ~/secrets/api-keys.yaml or a new dedicated YAML
   sops ~/secrets/api-keys.yaml
   # Add line: BRAVE_API_KEY: "BSA...actual_key"
   ```
3. **Source from SOPS into .env.mcp:**
   ```bash
   sops --decrypt ~/secrets/api-keys.yaml | grep BRAVE_API_KEY >> .env.mcp
   ```
   Or manually copy the decrypted value.
4. **Verify:**
   ```bash
   source .env.mcp
   .venv/bin/python3 -c "from src.mcp.tools.brave_search import _get_api_key; print('Key loaded OK')"
   ```

---

## 6. Related Missing Keys

`EXA_API_KEY` has the same status:
- Not in SOPS secrets
- Not in `.env.*` files
- Placeholder added to `.env.mcp`
- Tool `exa_search` will fail at call time until provisioned

Both keys are **documented as required** in prior phases but never actually provisioned.
