# P7-016: Tasker Clipboard Profile

## Overview

This profile monitors clipboard changes on Android devices and forwards clipboard content to the Guinevere server for secret scanning. The server-side scanner (P7-009) detects sensitive data like API keys, passwords, and tokens, then redacts them before storage.

The workflow is simple: clipboard changes trigger a Tasker task, which captures the text, signs it with HMAC, and sends it to the server. The server handles all secret detection and redaction.

## Prerequisites

Before setting up this profile, ensure you have:

- **Tasker 5.8+** installed on your Android device
- **AutoTools plugin** (required for clipboard monitoring on Android 10+)
- Active consent scope: `surveillance.clipboard` (see P7-012 for consent setup)
- HMAC signing key configured (see P7-017)
- Guinevere server endpoint accessible from your device

Note: Android 10 and later restrict clipboard access for background apps. AutoTools provides a workaround by using accessibility services.

## Profile Setup

### Trigger Configuration

**Event:** Clipboard Change

1. Open Tasker and create a new Profile
2. Select **Event** > **AutoTools** > **Clipboard** (if using AutoTools)
   - Alternative: Use Tasker's built-in **State** > **Clipboard** context (Android 9 and below only)
3. Configure the trigger to fire on any clipboard change

### Task Actions

Create a task with these actions in sequence:

**Action 1: Capture Clipboard Text**
- Use AutoTools action to read clipboard content
- Store in variable `%CLIP_TEXT`

**Action 2: Debounce Check**
- Check if last clipboard event was less than 5 seconds ago
- If yes, exit task (prevents battery drain from rapid clipboard changes)
- Update timestamp variable `%LAST_CLIP_EVENT`

**Action 3: Build JSON Payload**
- Construct the event payload (see Event Format section below)
- Use Tasker's JavaScript or HTTP Request action

**Action 4: HMAC Sign**
- Generate HMAC signature using the configured signing key
- Add signature to request headers (see P7-017 for HMAC implementation)

**Action 5: POST to Server**
- Send signed payload to Guinevere ingestion endpoint
- Handle network errors gracefully (log and continue, don't block clipboard)

## Event Format

The clipboard event uses this JSON structure:

```json
{
  "event_type": "clipboard",
  "device_id": "%DEVICE_ID",
  "occurred_at": "2026-01-01T12:00:00Z",
  "payload": {
    "text": "example clipboard content",
    "length": 26
  }
}
```

**Field Descriptions:**

- `event_type`: Always `"clipboard"` for this profile
- `device_id`: Unique identifier for the device (set during P7-012 setup)
- `occurred_at`: ISO 8601 timestamp when clipboard changed
- `payload.text`: The clipboard content (will be scanned and redacted server-side)
- `payload.length`: Character count of the original text

## Secret Scanning Integration

All clipboard content goes through server-side secret scanning before storage. This happens automatically and requires no client-side configuration.

### How the Pipeline Works

1. **Clipboard Capture**: Tasker captures the raw clipboard text and sends it to the server
2. **Server Receives Event**: The ingestion endpoint accepts the clipboard event
3. **Secret Scanner Runs**: P7-009 secret scanner analyzes the text for sensitive patterns:
   - API keys (AWS, GitHub, OpenAI, etc.)
   - Passwords and credentials
   - Bearer tokens and JWTs
   - Private keys and certificates
   - Database connection strings
4. **Redaction**: Detected secrets are replaced with `[REDACTED]`
5. **Storage**: The event is stored with redacted content (never dropped)

### Why Server-Side Scanning?

Client-side scanning would require shipping secret detection patterns to the device, creating security risks and maintenance overhead. Server-side scanning keeps patterns centralized, allows real-time updates, and provides better audit trails.

### Example Redaction Flow

**Original clipboard content:**
```
My API key is sk_test_1234567890abcdef and my password is SecretPass123
```

**After server-side scanning:**
```
My API key is [REDACTED] and my password is [REDACTED]
```

The event is preserved with full metadata. Only the sensitive values are replaced.

## HMAC Signing

All clipboard events must be signed using HMAC before transmission. This ensures event integrity and prevents tampering.

See **P7-017: HMAC Signing** for:
- Key generation and storage
- Signature algorithm (HMAC-SHA256)
- Header format
- Verification process on the server

## Consent Requirements

This profile requires active consent scope: `surveillance.clipboard`

- Consent must be explicitly granted during P7-012 setup
- User can revoke consent at any time via the Guinevere control interface
- When consent is revoked, the profile stops capturing clipboard data
- Revocation does not delete previously captured events (they remain redacted)

## Privacy and Data Classification

Clipboard data is classified as **Restricted** (highest sensitivity level).

**Privacy protections:**

- Raw clipboard text is scanned for secrets before storage
- Detected secrets are replaced with `[REDACTED]`
- The event is preserved (not dropped) with redacted content
- Access to clipboard events requires elevated permissions
- Audit logs track all access to clipboard data

**Why Restricted classification?**

Clipboards often contain sensitive information: passwords copied from password managers, API keys from documentation, private messages, financial data. Even after redaction, the remaining context can be sensitive.

## Battery Optimization

Clipboard monitoring can drain battery if not throttled. This profile includes debouncing:

- **Maximum rate**: 1 event per 5 seconds
- **Implementation**: Tasker checks timestamp before processing
- **Effect**: Rapid clipboard changes (like copying multiple items in succession) are batched

This reduces network requests and server load while maintaining useful event capture.

## Troubleshooting

### Clipboard Monitoring Not Working

**Android 10+ devices:**
- Ensure AutoTools plugin is installed and has accessibility permissions
- Go to Settings > Accessibility > AutoTools and enable the service
- Some manufacturers (Xiaomi, Huawei) require additional battery optimization exceptions

**Android 9 and below:**
- Built-in Tasker clipboard context should work without AutoTools
- Check Tasker permissions in Settings > Apps > Tasker > Permissions

### Common Issues

**Problem:** Profile triggers but no events reach server
- Check network connectivity
- Verify HMAC key is configured correctly (P7-017)
- Check server endpoint URL in the HTTP Request action
- Review Tasker logs for errors

**Problem:** Events are dropped or missing
- Verify debounce logic isn't too aggressive (5 seconds is the minimum)
- Check if consent scope `surveillance.clipboard` is active
- Review server logs for ingestion errors

**Problem:** Secrets not being redacted
- Secret scanning happens server-side (P7-009)
- Check server logs for scanner errors
- Verify the scanner service is running
- Test with known secret patterns (use test keys, never real ones)

**Problem:** High battery usage
- Confirm debounce is working (check `%LAST_CLIP_EVENT` variable)
- Reduce clipboard monitoring frequency if needed
- Consider disabling the profile during low-battery situations

### AutoTools Setup

1. Install AutoTools from Play Store
2. Open AutoTools and grant accessibility permissions
3. In Tasker, install AutoTools plugin integration
4. Test clipboard monitoring with a simple task before enabling the full profile

### Android Version Differences

- **Android 9 and below**: Native clipboard access works in background
- **Android 10-12**: Requires AutoTools or similar accessibility-based solution
- **Android 13+**: Additional restrictions may apply, check AutoTools documentation for updates

## References

- **P7-009**: Secret Scanner (server-side detection and redaction)
- **P7-012**: Device Setup and Consent Management
- **P7-017**: HMAC Signing Implementation
