# Auditor Gate: Security — P5 Agent Loop

**Auditor**: Parent (sub-agents aborted)
**Date**: 2026-06-02
**Scope**: Authentication, secrets, access control across P5 batch

## Verdict: **PASS** (with MEDIUM finding documented)

## Authentication

| Component | Mechanism | Status |
|-----------|-----------|--------|
| API auth (auth.py) | `X-Guinevere-API-Key` header, `hmac.compare_digest` timing-safe comparison | ✅ |
| API key source | `GUINEVERE_API_KEY` env var | ✅ |
| Dev fallback | `"guinevere-dev-key"` with `logger.warning` | ✅ Appropriate |
| POST endpoints | `Depends(get_api_key)` on create_loop and cancel_loop | ✅ |
| GET endpoints | Unprotected (internal API, read-only) | ✅ Acceptable |

## Discord Command Security

| Command | Access Gate | Response Privacy | Status |
|---------|-------------|-----------------|--------|
| /loop-start | `is_faiz_interaction` | Ephemeral | ✅ |
| /loop-stop | `is_faiz_interaction` | Ephemeral | ✅ |

## Secret Management

| Check | Status |
|-------|--------|
| No hardcoded API keys in code | ✅ |
| No hardcoded DB passwords | ✅ |
| No hardcoded Discord tokens | ✅ |
| Dev key logged as warning | ✅ |
| Redis password from env (`REDIS_PASSWORD` with empty default) | ✅ Dev acceptable |
| API key in cmd_loop_start.py from `os.environ` | ✅ |
| API key in cmd_loop_stop.py from `os.environ` | ✅ |

## Path Safety

- `artifacts.py`: path construction uses `loop_id` (UUID) — no user-controlled traversal risk
- `hash_anchor.py`: `file_path` parameter is internal API only
- Evidence root: `/home/guinevere/evidence/loops/` — deterministic, no injection

## MEDIUM Finding

**verify.py `subprocess.run(shell=True)`**:
- `subprocess.run(command, shell=True, ...)` at line ~150
- Risk: command injection if untrusted input reaches `$CMD`
- Context: Internal use only (OutputVerifier used by loop engine, not user-facing)
- Recommendation: Before production, switch to `shell=False` with `shlex.split()` or validate command against whitelist
- **Not blocking for current batch**

## Conclusion

Security posture is solid for internal API with dev key fallback. Auth properly gated on mutating endpoints. Discord commands properly restricted. One MEDIUM finding (subprocess shell=True) documented for future remediation. PASS.
