# P7-017: HMAC Signing in Tasker

## Overview

This document describes the Tasker JavaScriptlet (`hmac-sign.js`) that generates HMAC-SHA256 signatures for Guinevere surveillance event submissions. The JavaScriptlet runs inside Tasker before each HTTP Request action, producing three local variables that get attached to outgoing request headers.

The signing approach uses Tasker's native Java bridge to call `javax.crypto.Mac` directly. No external libraries, no CDN imports, no CryptoJS dependency.

## Prerequisites

- **Tasker 5.8 or later** with JavaScriptlet support enabled
- **Java bridge access** must be available (default on Android with Tasker installed)
- **Server endpoint** reachable via Cloudflare Tunnel (TLS required for all production traffic)
- Initial Tasker variable setup completed per **P7-012 setup guide**

## Variable Setup

Three Tasker variables must exist before the JavaScriptlet runs. Configure these following the P7-012 setup guide:

| Variable | Description | Example Value |
|---|---|---|
| `%API_URL` | Base URL of the Guinevere surveillance endpoint | `https://your-tunnel-domain.example.com` |
| `%HMAC_SECRET` | Shared secret for HMAC signing (set via SOPS-managed env) | *(never log or display)* |
| `%DEVICE_ID` | Unique identifier for this device | `pixel-7-faiz-001` |

All three variables are set as Tasker global variables. The JavaScriptlet reads `%HMAC_SECRET` at runtime and never stores it in the script source.

**Consent note**: All surveillance collection profiles require active consent. The JavaScriptlet should only execute when the user has granted explicit consent for the relevant surveillance scope (app_usage, location, notifications, or clipboard). Profiles must check consent state before triggering.

## JavaScriptlet Installation

1. Copy `hmac-sign.js` to your device's Tasker scripts directory (e.g., `/sdcard/Tasker/scripts/`)
2. In your Tasker profile, add a **JavaScriptlet** action
3. Set the source to the file path or paste the script content directly
4. Ensure the JavaScriptlet action runs **before** the HTTP Request action in your task sequence
5. The script sets three local variables: `%hmac_signature`, `%hmac_timestamp`, `%hmac_nonce`

## Signing Algorithm

The HMAC-SHA256 signing process follows these steps:

1. **Read the HMAC secret** from Tasker variable `%HMAC_SECRET`
2. **Generate a timestamp** as Unix epoch seconds: `Math.floor(Date.now() / 1000)`
3. **Generate a nonce** using `java.util.UUID.randomUUID().toString()`
4. **Build the signing string** by concatenating five fields with colons:
   ```
   method:path:timestamp:nonce:body
   ```
   Example:
   ```
   POST:/surveillance/events:1717401600:a1b2c3d4-e5f6-7890-abcd-ef1234567890:{"event_type":"app_usage","device_id":"pixel-7-faiz-001","occurred_at":"2025-06-03T12:00:00.000Z","payload":{"app":"com.example.app"}}
   ```
5. **Compute HMAC-SHA256** using the Java bridge:
   - Load `javax.crypto.Mac` and `javax.crypto.spec.SecretKeySpec` via reflection
   - Initialize with the secret key (UTF-8 encoded)
   - Compute the digest over the signing string (UTF-8 encoded)
6. **Convert the raw bytes** to a lowercase hexadecimal string using `java.lang.String.format("%02x", byte)`
7. **Set output variables** via `setLocal()` for use in the HTTP Request action

### Helper Function

The script includes `buildEventPayload(eventType, deviceId, payload)` which constructs a JSON string with the required fields:

- `event_type`: string identifying the surveillance event category
- `device_id`: unique device identifier
- `occurred_at`: ISO 8601 timestamp of when the event occurred
- `payload`: nested object containing event-specific data

Call this helper before the main signing block to produce the `%hmac_body` variable.

## HTTP Request Action

After the JavaScriptlet runs, configure a Tasker **HTTP Request** action with these settings:

| Field | Value |
|---|---|
| Method | POST |
| URL | `%API_URL/surveillance/events` |
| Headers | See below |
| Body | `%hmac_body` |
| Content Type | `application/json` |

### Header Format

```
Content-Type:application/json
X-Signature:%hmac_signature
X-Timestamp:%hmac_timestamp
X-Nonce:%hmac_nonce
```

The server validates all three headers. It recomputes the HMAC using the same signing string format and compares the result using constant-time comparison (`hmac.compare_digest` in Python). If the signature, timestamp, or nonce is missing or invalid, the server returns HTTP 401.

## Testing

To verify the JavaScriptlet produces correct signatures:

1. Set `%HMAC_SECRET` to a known test value in Tasker
2. Set `%hmac_body` to a fixed JSON string
3. Run the JavaScriptlet
4. Note the output values: `%hmac_signature`, `%hmac_timestamp`, `%hmac_nonce`
5. On a machine with Python, verify manually:
   ```python
   import hmac, hashlib
   secret = b"YOUR_TEST_SECRET"
   signing_string = "POST:/surveillance/events:TIMESTAMP:NONCE:BODY"
   expected = hmac.new(secret, signing_string.encode("utf-8"), hashlib.sha256).hexdigest()
   print(expected)  # Should match %hmac_signature
   ```
6. Compare the Python output with `%hmac_signature`. They must match exactly (lowercase hex).

## Troubleshooting

### Wrong Secret Format
The `%HMAC_SECRET` variable must contain the raw secret string, not a base64-encoded or hex-encoded version. If you store the secret in an encrypted file (SOPS/age), decrypt it to plaintext before assigning to the Tasker variable.

### Timestamp Drift
The server rejects requests where the timestamp is more than 300 seconds (5 minutes) from the server's current time. Ensure your device clock is synchronized via NTP. Run `adb shell date` to check device time against the server.

### Nonce Reuse
Each request must use a fresh UUID nonce. The JavaScriptlet generates a new UUID on every execution, so this should not occur unless the script is modified to cache the nonce. If you see HTTP 401 with "nonce already used", check that the JavaScriptlet runs fresh for each request.

### Java Bridge Errors
If you see `java.lang.ClassNotFoundException`, your Tasker installation may not have Java bridge support. Update Tasker to version 5.8 or later. Some custom ROMs restrict Java reflection; check Tasker's JavaScriptlet permissions.

### Empty Signature Output
If `%hmac_signature` is empty after execution, check `%hmac_error`. When set to `"true"`, the JavaScriptlet caught an exception. Common causes:
- `%HMAC_SECRET` is not set or is empty
- `%hmac_body` is not set
- Java bridge is unavailable

## Security Notes

- **Never hardcode the HMAC secret** in the JavaScriptlet source. Always read from `%HMAC_SECRET`.
- **Rotate `%HMAC_SECRET` regularly** using SOPS/age-encrypted configuration. Push the new secret to both server and device simultaneously.
- **All traffic must use TLS**. The server endpoint should only be reachable via HTTPS through Cloudflare Tunnel. Never send signed requests over plain HTTP.
- **Server-side signature comparison** uses constant-time comparison (`hmac.compare_digest`) to prevent timing attacks. The JavaScriptlet does not perform comparison, so this is a server responsibility.
- **Consent is mandatory**. All surveillance profiles must verify that the user has granted consent for the specific data scope before collecting and submitting events. Consent can be revoked at any time, and collection must stop immediately upon revocation.

## References

- P7-012 setup guide: Initial Tasker variable configuration and profile setup
- Server endpoint: `POST /surveillance/events` (internal port 8000, exposed via Cloudflare Tunnel)
- Consent scopes: `surveillance.app_usage`, `surveillance.location`, `surveillance.notifications`, `surveillance.clipboard`
