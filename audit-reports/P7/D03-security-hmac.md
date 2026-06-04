# D03 Security Audit: HMAC-SHA256, Replay Protection, SOPS, TLS

> **Audit ID**: D03
> **Phase**: P7 Surveillance
> **Date**: 2026-06-03
> **Auditor**: Security Auditor (automated)
> **Scope**: Authentication, replay protection, secret management, TLS configuration

## Overall Verdict: PASS

All critical security boundaries are correctly implemented. Three minor informational findings are noted below.

---

## 1. HMAC Verification Chain Analysis

**File**: `src/surveillance/auth.py`
**Verdict**: PASS

### Execution Order

The `verify_hmac` FastAPI dependency enforces a three-stage verification chain in the correct order:

| Stage | Operation | Cost | Failure Mode |
|-------|-----------|------|--------------|
| 1 | Timestamp validation | Free (no I/O) | HTTP 401 |
| 2 | Nonce deduplication | Redis SET NX EX | HTTP 409 (replay) or HTTP 503 (Redis down) |
| 3 | HMAC signature comparison | CPU (SHA-256) | HTTP 401 |

This ordering is optimal. Expired requests are rejected before consuming Redis I/O. Replay attempts are rejected before the CPU-expensive HMAC computation. The sequence minimizes resource waste under attack.

**Evidence**: `auth.py` lines 61-83. The three stages are explicitly numbered and commented in source.

### Dependency Injection

`verify_hmac` is a FastAPI dependency with three required headers:

- `X-Signature` (the HMAC hex digest)
- `X-Timestamp` (Unix epoch seconds)
- `X-Nonce` (unique request identifier)

Missing headers result in HTTP 422 (handled by FastAPI's header validation), not a custom error path. This is correct.

---

## 2. Timing-Safe Comparison

**File**: `src/surveillance/auth.py`, line 82
**Verdict**: PASS

```python
if not hmac.compare_digest(x_signature, expected):
    raise HTTPException(status_code=401, detail="Invalid HMAC signature")
```

`hmac.compare_digest` is the Python standard library's constant-time comparison function. It prevents timing side-channel attacks by comparing the full string regardless of where differences occur.

**Confirmed**: `hmac.compare_digest` is present and is the sole comparison mechanism. No fallback to `==` or string equality exists.

---

## 3. Signing String Format

**File**: `src/surveillance/auth.py`, lines 70-73
**Verdict**: PASS

The signing string is constructed as:

```
<method>:<path>:<timestamp>:<nonce>:<body-as-utf8>
```

Concrete code:

```python
signing_string = (
    f"{request.method}:{request.url.path}:"
    f"{x_timestamp}:{x_nonce}:{body_str}"
)
```

This matches the specification: `method:path:timestamp:nonce:body`.

### Properties Verified

| Component | Source | Correct |
|-----------|--------|---------|
| method | `request.method` (GET, POST, etc.) | Yes |
| path | `request.url.path` (no query string) | Yes |
| timestamp | `x_timestamp` header value (not re-derived) | Yes |
| nonce | `x_nonce` header value | Yes |
| body | `request.body()` decoded as UTF-8 | Yes |

The HMAC is computed over `signing_string.encode("utf-8")` using the secret from `get_hmac_secret()`, with `hashlib.sha256` as the digest algorithm. This is correct.

---

## 4. Nonce Storage: Atomic SET NX EX

**File**: `src/surveillance/replay.py`, line 130
**Verdict**: PASS

```python
result = await redis_client.set(nonce_key, "1", nx=True, ex=NONCE_TTL_SECONDS)
```

### Atomicity

The `SET key value NX EX ttl` command is a single atomic Redis operation. It is NOT a GET-then-SET sequence. There is no race condition window between checking for the nonce and storing it.

- `nx=True`: The SET only succeeds if the key does NOT already exist.
- `ex=NONCE_TTL_SECONDS`: The key expires after `NONCE_TTL_SECONDS` (660) seconds.
- Return value: `True` on first-time set (accepted), `None` on duplicate (replay detected).

### Duplicate Detection

```python
if result is None:
    raise HTTPException(status_code=409, detail="Replay detected")
```

HTTP 409 (Conflict) is the correct status code for a replay attempt. This is distinct from 401 (auth failure) and 503 (service unavailable), enabling clear monitoring and alerting.

---

## 5. Nonce TTL: 660s

**File**: `src/surveillance/replay.py`, line 36
**Verdict**: PASS

```python
NONCE_TTL_SECONDS: int = 660
```

The TTL is 660 seconds, which satisfies the requirement:

- Timestamp window: 300 seconds
- Required minimum: 2 x 300s + 60s buffer = 660 seconds
- Actual value: 660 seconds (exactly meets the requirement)

This ensures that a nonce outlives the entire validity window it guards. A request sent at the edge of the 300-second window still has its nonce stored for an additional 360 seconds after expiry.

---

## 6. Timestamp Window: 300s

**File**: `src/surveillance/replay.py`, lines 33, 79-108
**Verdict**: PASS

```python
TIMESTAMP_WINDOW_SECONDS: int = 300
```

The `validate_timestamp` function:

1. Parses the `X-Timestamp` header as an integer Unix epoch.
2. Computes `diff = abs(now - ts)` (absolute difference, bidirectional).
3. Rejects with HTTP 401 if `diff > 300`.

The bidirectional check (`abs(now - ts)`) correctly handles both clock-ahead and clock-behind scenarios on the client device.

Unparseable timestamps (non-integer, empty, None) are rejected with HTTP 401, not 500. This is correct.

---

## 7. Redis Failure Mode: Fail-Closed (503)

**File**: `src/surveillance/replay.py`, lines 143-150
**Verdict**: PASS

```python
except HTTPException:
    raise
except Exception:
    logger.exception(
        "replay_redis_error",
        nonce_prefix=nonce[:8] if len(nonce) >= 8 else nonce,
    )
    raise HTTPException(status_code=503, detail="Replay protection unavailable")
```

The exception handling is correct:

- `HTTPException` (from the duplicate nonce check) is re-raised unchanged.
- ALL other exceptions (connection refused, timeout, Redis internal error) are caught and converted to HTTP 503.
- The system NEVER falls through to accept a request when Redis is unavailable.

This is fail-closed behavior: when the replay protection system cannot verify a request, the request is rejected. This is the security-correct choice, as opposed to fail-open which would accept unverified requests.

---

## 8. Secret Resolution Chain

**File**: `src/surveillance/secrets.py`
**Verdict**: PASS

### Resolution Order

The `get_hmac_secret()` function resolves the secret in this order:

| Priority | Source | Mechanism | Use Case |
|----------|--------|-----------|----------|
| 1 | Cache | `_cached_secret` singleton check | Subsequent calls in same process |
| 2 | Environment variable | `os.environ.get("SURVEILLANCE_HMAC_SECRET")` | Dev / CI override |
| 3 | SOPS decryption | `sops --decrypt secrets/guinevere-secrets.yaml` | Production |

The resolved value is cached for the process lifetime to avoid repeated SOPS subprocess invocations.

### SOPS Decryption Details

The `_decrypt_sops_secret()` function:

1. Verifies the secrets file exists (`_SECRETS_FILE.exists()`).
2. Invokes `sops --decrypt` as a subprocess with `capture_output=True`.
3. Validates the return code (non-zero raises `RuntimeError`).
4. Parses YAML output and extracts `surveillance.hmac_secret`.
5. Validates the extracted value is a non-empty string.

Each failure mode has a distinct error type and message. The function never returns an empty string or None.

### Secret Isolation

- `secrets/` directory is in `.gitignore` (confirmed).
- No plaintext secret files are tracked in version control.
- The `secrets/guinevere-secrets.yaml` path is resolved relative to the source file, not hardcoded as an absolute path.

---

## 9. Redis DB2 Usage Consistency

**Verdict**: PASS

All security-critical surveillance modules use Redis DB2 consistently:

| Module | DB | Purpose |
|--------|----|---------|
| `replay.py` | DB2 | Nonce deduplication storage |
| `consent_gate.py` | DB2 | Consent verdict cache |
| `consumer.py` | DB2 | Event buffer consumption |
| `redis_buffer.py` | DB2 | Event buffer production |

Namespace isolation within DB2 is achieved via key prefixing (`surveillance:nonce:` for nonces). This prevents key collisions between the nonce store and the event buffer.

### Redis Connection Security

All Redis connections use `os.environ.get("REDIS_PASSWORD", "")` for password authentication. No Redis password is hardcoded in source.

---

## 10. TLS Documentation Completeness

**File**: `docs/setup-evidence/P7/STEP-P7-004/tls-configuration.md`
**Verdict**: PASS

The TLS configuration guide is comprehensive (485 lines) and covers:

| Section | Coverage | Status |
|---------|----------|--------|
| Network architecture | Cloudflare Tunnel + Tailscale HTTPS dual-path | Complete |
| Cloudflare Tunnel setup | Install, auth, create, configure, DNS, start, verify | Complete |
| Tailscale HTTPS setup | Enable, configure serve, persist, verify | Complete |
| Certificate management | Auto-renewal for both providers, renewal failure handling | Complete |
| Port 8000 isolation | Firewall rules (UFW, iptables), verification commands | Complete |
| No plaintext HTTP | Explicit prohibition of http:// for external access | Complete |
| HMAC-TLS independence | Both required, neither replaces the other | Complete |
| Cloudflare WAF | Optional hardening recommendations | Complete |
| Troubleshooting | Provider-specific + general issue resolution | Complete |
| Quick reference table | All key values summarized | Complete |

### TLS Design Correctness

- Internal API port (8000) never faces the public internet directly.
- TLS termination happens at edge (Cloudflare) or Tailscale node.
- Both paths forward to `http://localhost:8000` as plain HTTP (correct for loopback).
- TLS 1.2 minimum is specified.
- Both certificate providers offer automatic renewal.
- The document explicitly states HMAC-SHA256 and TLS serve different purposes and both are required.

### No Sensitive Values in TLS Doc

The TLS guide uses `<your-domain>`, `<TUNNEL_UUID>`, `<hostname>`, `<tailnet>` placeholders throughout. No real domain names, IP addresses, or credentials appear.

---

## 11. Secret Exposure Scan

**Verdict**: PASS

### Tests Directory

All secret values in tests are clearly synthetic:

| File | Value | Assessment |
|------|-------|------------|
| `test_secrets.py` | `test-hmac-secret-aabbccdd` | Synthetic test constant |
| `test_e2e.py` | `test-hmac-secret-for-e2e-only` | Synthetic test constant |
| `test_auth.py` | `wrong-secret-value` | Intentional mismatch for negative test |

All test files use `monkeypatch.setenv("SURVEILLANCE_HMAC_SECRET", ...)` to inject test secrets. No test accesses the real SOPS-encrypted file. No real production secret appears anywhere in the test suite.

### Documentation and Evidence

Grep across `docs/setup-evidence/P7/` found zero matches for hardcoded passwords, secrets, or tokens in the pattern `(password|secret|token|key)\s*[:=]\s*["'][^"']+["']`.

The Tasker setup guide (`STEP-P7-012/tasker-setup-guide.md`) references the HMAC secret only as `%HMAC_SECRET` (a Tasker variable) and explicitly instructs loading from SOPS. No plaintext secret appears.

### Source Code

Grep across `src/surveillance/` found zero hardcoded password values. The Redis password is loaded exclusively from the `REDIS_PASSWORD` environment variable.

### Artifact Scan Summary

| Location | Pattern | Matches | Real Secrets |
|----------|---------|---------|--------------|
| `tests/` | HMAC secret values | 3 distinct synthetic values | None |
| `docs/setup-evidence/P7/` | Password/secret/token patterns | 0 | None |
| `src/surveillance/` | Hardcoded passwords | 0 | None |

---

## 12. Minor Findings (Informational)

### M1: SOPS stderr Leakage in Error Logs

**File**: `src/surveillance/secrets.py`, line 57
**Severity**: Informational

```python
raise RuntimeError(
    f"SOPS decryption failed (exit {result.returncode}): "
    f"{result.stderr.strip()}"
)
```

The SOPS subprocess stderr is included in the error message and logged. In rare edge cases, SOPS error output could contain partial file paths or age key identifiers. This is low risk because:

- The error is raised as an exception, not returned to the client.
- Structured logging captures it server-side only.
- SOPS error messages are typically generic ("failed to decrypt" etc.).

**Recommendation**: Consider truncating stderr to a fixed length or replacing it with a generic message in production.

### M2: Nonce Prefix Logging

**File**: `src/surveillance/auth.py` line 88, `src/surveillance/replay.py` lines 135-136
**Severity**: Informational

The first 8 characters of the nonce are logged for debugging purposes (`nonce_prefix`). This is acceptable practice for operational debugging. The nonce itself is not a secret (it is sent in a plaintext HTTP header), but truncating to a prefix is good practice.

### M3: REDIS_PASSWORD Empty String Fallback

**File**: `src/surveillance/replay.py` line 59
**Severity**: Informational

```python
password=os.environ.get("REDIS_PASSWORD", "")
```

If `REDIS_PASSWORD` is not set, an empty string is passed as the password. This allows connection to Redis instances configured without authentication (e.g., local dev). In production, the environment variable must be set. This is standard practice but should be documented in deployment runbooks.

---

## 13. Audit Checklist Summary

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | HMAC verification chain ordering (timestamp -> nonce -> HMAC) | PASS | `auth.py` lines 61-83 |
| 2 | Timing-safe comparison (`hmac.compare_digest`) | PASS | `auth.py` line 82 |
| 3 | Signing string format (`method:path:timestamp:nonce:body`) | PASS | `auth.py` lines 70-73 |
| 4 | Nonce storage atomic (`SET NX EX`) | PASS | `replay.py` line 130 |
| 5 | Nonce TTL 660s (>= 2x300s + 60s buffer) | PASS | `replay.py` line 36 |
| 6 | Timestamp window 300s | PASS | `replay.py` line 33 |
| 7 | Redis failure mode: fail-closed (503) | PASS | `replay.py` lines 143-150 |
| 8 | Secret resolution: cache -> env -> SOPS | PASS | `secrets.py` lines 82-118 |
| 9 | Redis DB2 consistency across modules | PASS | 4 modules, all DB2 |
| 10 | TLS documentation completeness | PASS | `tls-configuration.md` (485 lines) |
| 11 | Cloudflare Tunnel coverage | PASS | Sections 3.1-3.9 |
| 12 | Tailscale HTTPS coverage | PASS | Sections 4.1-4.5 |
| 13 | No secret exposure in tests | PASS | 3 synthetic values only |
| 14 | No secret exposure in docs/evidence | PASS | Zero pattern matches |
| 15 | No secret exposure in source code | PASS | Zero pattern matches |
| 16 | `secrets/` in `.gitignore` | PASS | `.gitignore` line 24 |
| 17 | Port 8000 isolation documented | PASS | TLS doc section 6 |
| 18 | HMAC-TLS independence documented | PASS | TLS doc section 6 |

---

## Footer

| Item | Value |
|------|-------|
| Audit Date | 2026-06-03 |
| Files Reviewed | `src/surveillance/auth.py`, `src/surveillance/replay.py`, `src/surveillance/secrets.py`, `docs/setup-evidence/P7/STEP-P7-004/tls-configuration.md` |
| Grep Scans | `hmac.compare_digest`, `nx=True`, `db=2`, `REDIS_PASSWORD`, `SURVEILLANCE_HMAC_SECRET`, hardcoded secret patterns |
| Minor Findings | 3 informational (M1, M2, M3) |
| Critical Findings | 0 |
| **Overall Verdict** | **PASS** |
