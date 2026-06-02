# STEP-P7-012 — Android Tasker Setup Guide for Guinevere Surveillance

## Overview

This guide walks through setting up Tasker on Android to collect surveillance data and send it to the Guinevere API. Tasker acts as the on-device data collector, packaging events into HMAC-signed HTTP requests that flow through the surveillance ingestion pipeline.

**Event flow:**

```
Android Tasker -> HMAC-signed HTTP POST -> Guinevere API (/surveillance/events) -> Redis DB2 buffer -> Async Consumer -> TimescaleDB
```

Tasker collects four event types from the Android device:

| Event Type | Step | Description |
|---|---|---|
| App usage | P7-013 | Foreground app name and usage duration |
| Location | P7-014 | GPS coordinates and geofence triggers |
| Notifications | P7-015 | App name, notification title, and text |
| Clipboard | P7-016 | Clipboard text content on copy events |

Each event is signed with HMAC-SHA256 before transmission. The API rejects unsigned or improperly signed requests.

---

## 1. Prerequisites

### 1.1 Device Requirements

| Requirement | Minimum |
|---|---|
| Android version | 8.0 (Oreo, API 26) or higher |
| RAM | 2 GB free |
| Storage | 50 MB for Tasker + plugins |
| Network | Active internet connection (mobile data or Wi-Fi) |

### 1.2 Required Apps

| App | Source | Purpose |
|---|---|---|
| **Tasker** | Google Play Store (paid) | Core automation engine |
| **AutoNotification** | Google Play Store (plugin) | Notification interception (P7-015) |
| **AutoInput** | Google Play Store (plugin) | Clipboard monitoring helper (P7-016) |

### 1.3 Required Permissions

Tasker needs the following Android permissions to collect surveillance data. Grant each one when prompted during setup or in Settings > Apps > Tasker > Permissions.

| Permission | Used By | Why |
|---|---|---|
| Usage Access | P7-013 (app usage) | Read foreground app and usage duration |
| Location (Always Allow) | P7-014 (location) | GPS polling and geofence triggers in background |
| Notification Access | P7-015 (notifications) | Intercept notification content via AutoNotification |
| Read Clipboard | P7-016 (clipboard) | Capture clipboard text on copy events |
| Background Activity | All profiles | Keep Tasker profiles running when app is not foreground |
| Draw Over Apps | AutoInput | Required by AutoInput for clipboard monitoring |

### 1.4 Battery Optimization

Disable battery optimization for Tasker and its plugins. Without this, Android will kill background profiles and data collection stops.

1. Go to **Settings > Apps > Tasker > Battery**
2. Select **Unrestricted** (or "Don't optimize")
3. Repeat for AutoNotification and AutoInput
4. On Samsung/Xiaomi/Huawei devices, also disable the manufacturer's aggressive battery killer. See [dontkillmyapp.com](https://dontkillmyapp.com) for device-specific steps.

---

## 2. Installation

### 2.1 Install Tasker

1. Open Google Play Store
2. Search for "Tasker" by joaomgcd
3. Purchase and install
4. Open Tasker and grant initial permissions when prompted
5. Complete the onboarding tutorial (you can skip the example profiles)

### 2.2 Install Plugins

1. Search Play Store for "AutoNotification" and install it
2. Search Play Store for "AutoInput" and install it
3. Open each plugin once to activate their accessibility services

### 2.3 Enable Required System Settings

**Usage Access:**
1. Settings > Apps > Special app access > Usage access
2. Toggle ON for Tasker

**Notification Access:**
1. Settings > Apps > Special app access > Notification access
2. Toggle ON for AutoNotification

**Accessibility Service (AutoInput):**
1. Settings > Accessibility > AutoInput
2. Toggle ON

---

## 3. Configuration

All configuration values are stored as Tasker global variables. This keeps sensitive data out of profile definitions and makes rotation straightforward.

### 3.1 Set Up Global Variables

Open Tasker, go to the **VARS** tab, and create these global variables:

| Variable | Description | Example Value |
|---|---|---|
| `%API_URL` | Guinevere API HTTPS endpoint | `https://YOUR-ENDPOINT.example.com` |
| `%HMAC_SECRET` | HMAC signing secret (from SOPS) | Loaded at runtime (see below) |
| `%DEVICE_ID` | Unique identifier for this device | A UUID you generate |

#### Setting %API_URL

This is the HTTPS endpoint for the Guinevere surveillance ingestion API. The URL depends on your deployment method:

- **Cloudflare Tunnel:** `https://YOUR-TUNNEL-NAME.example.com`
- **Tailscale:** `https://YOUR-TAILSCALE-HOSTNAME`

The endpoint must use HTTPS. Tasker will reject plaintext HTTP connections.

1. In Tasker, go to **VARS** tab
2. Tap the **+** button
3. Name: `API_URL`
4. Value: your HTTPS endpoint (no trailing slash)
5. Tap the checkmark to save

#### Setting %HMAC_SECRET

The HMAC secret is used to sign every event request. This secret comes from the SOPS-encrypted secrets store and must never appear in plaintext in Tasker profiles, exported XML, or version control.

**Loading the secret at runtime:**

1. Decrypt the HMAC secret from SOPS on a trusted machine:
   ```bash
   sops --decrypt secrets/surveillance/tasker-hmac.enc.yaml | grep hmac_secret
   ```
2. Copy the decrypted value to your clipboard
3. On the Android device, open Tasker > **VARS** tab
4. Create variable `HMAC_SECRET` and paste the value
5. Clear your clipboard immediately after pasting

**Important:** Do not write the HMAC secret in any Tasker task action, profile description, or exported backup. Store it only in the `%HMAC_SECRET` global variable. If you export Tasker profiles for backup, scrub the variable value before sharing.

#### Setting %DEVICE_ID

Generate a UUID to uniquely identify this device. The API uses this to attribute events to the correct device.

1. Generate a UUID (e.g., `uuidgen` on Linux/macOS, or use an online generator)
2. In Tasker, go to **VARS** tab
3. Create variable `DEVICE_ID` with the UUID value
4. Example format: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`

### 3.2 Verify Variables

After setting all three variables, confirm they are correct:

1. Go to **VARS** tab in Tasker
2. Verify `%API_URL` starts with `https://`
3. Verify `%HMAC_SECRET` is populated (not empty)
4. Verify `%DEVICE_ID` contains a valid UUID

---

## 4. Profile Overview

Each surveillance data type has its own Tasker profile. The profiles are created in subsequent steps (P7-013 through P7-016). This section describes what each profile does.

### 4.1 P7-013 — App Usage Profile

| Field | Value |
|---|---|
| **Event type** | `app_usage` |
| **Trigger** | Time-based (every 15 minutes) or app-switch event |
| **Data collected** | Foreground app package name, usage duration since last report |
| **Consent scope** | `surveillance.app_usage` |

The profile uses Android's UsageStatsManager (via Tasker's usage access permission) to determine which app is in the foreground and for how long. It fires on a periodic interval and reports accumulated usage.

### 4.2 P7-014 — Location Profile

| Field | Value |
|---|---|
| **Event type** | `location` |
| **Trigger** | Location change (geofence) or periodic (every 30 minutes) |
| **Data collected** | Latitude, longitude, accuracy, altitude, speed |
| **Consent scope** | `surveillance.location` |

The profile queries GPS when triggered. For geofencing, it uses Tasker's Location event with enter/exit triggers around defined coordinates. Coordinates are configured per-user based on consent boundaries.

### 4.3 P7-015 — Notification Profile

| Field | Value |
|---|---|
| **Event type** | `notification` |
| **Trigger** | AutoNotification intercept event |
| **Data collected** | Source app package name, notification title, notification text |
| **Consent scope** | `surveillance.notifications` |

AutoNotification intercepts incoming notifications and passes their content to a Tasker task. The task packages the notification fields into a JSON payload and sends it to the API.

### 4.4 P7-016 — Clipboard Profile

| Field | Value |
|---|---|
| **Event type** | `clipboard` |
| **Trigger** | Clipboard change event (via AutoInput or Tasker's built-in clip monitor) |
| **Data collected** | Clipboard text content |
| **Consent scope** | `surveillance.clipboard` |

When the user copies text to clipboard, the profile captures the text content and sends it as an event. Binary clipboard data (images, files) is not collected.

---

## 5. HMAC Signing

Every event sent to the Guinevere API must be signed with HMAC-SHA256. The signing logic is implemented in a reusable JavaScriptlet created by step P7-017.

### 5.1 Signature Computation

The signature covers the following canonical string:

```
POST
/surveillance/events
{timestamp}
{nonce}
{request_body}
```

Where:
- `{timestamp}` is the Unix epoch in seconds (`X-Timestamp` header)
- `{nonce}` is a UUID v4 string (`X-Nonce` header)
- `{request_body}` is the full JSON body as transmitted

The HMAC-SHA256 digest is computed using `%HMAC_SECRET` as the key and the canonical string above as the message. The result is hex-encoded and sent in the `X-Signature` header.

### 5.2 Request Headers

| Header | Value | Description |
|---|---|---|
| `Content-Type` | `application/json` | JSON request body |
| `X-Signature` | Hex-encoded HMAC-SHA256 | Request authentication |
| `X-Timestamp` | Unix epoch seconds | Replay window check |
| `X-Nonce` | UUID v4 | Replay protection |

### 5.3 Request Body Structure

```json
{
  "event_type": "app_usage",
  "device_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "payload": {
    "app_package": "com.example.app",
    "duration_seconds": 900
  },
  "occurred_at": "2026-06-02T10:30:00+07:00"
}
```

### 5.4 JavaScriptlet Reference

The signing JavaScriptlet is created in **STEP-P7-017**. Each profile task calls this JavaScriptlet before making the HTTP request. The JavaScriptlet:

1. Generates a UUID nonce
2. Gets the current Unix timestamp
3. Builds the canonical signing string
4. Computes HMAC-SHA256 using `%HMAC_SECRET`
5. Sets the `X-Signature`, `X-Timestamp`, and `X-Nonce` local variables for the HTTP Request action

See `docs/setup-evidence/P7/STEP-P7-017/` for the JavaScriptlet implementation and integration instructions.

---

## 6. Consent Requirements

Guinevere enforces strict consent boundaries on all surveillance data collection. Tasker profiles must not collect data without active consent.

### 6.1 Consent Scopes

Each event type maps to a specific consent scope in the Guinevere consent ledger:

| Event Type | Consent Scope |
|---|---|
| App usage | `surveillance.app_usage` |
| Location | `surveillance.location` |
| Notifications | `surveillance.notifications` |
| Clipboard | `surveillance.clipboard` |

### 6.2 How Consent Works

1. **Grant:** Consent is granted through Discord commands or the consent API
2. **Check:** The Guinevere API verifies consent on every incoming event. Events for scopes without active consent are rejected with HTTP 403
3. **Revoke:** Consent can be revoked at any time via Discord commands. Revocation takes effect immediately and the API stops accepting events for that scope

### 6.3 Consent-Aware Tasker Behavior

The API-side consent check provides the primary enforcement. However, to avoid wasting bandwidth on rejected events, you can optionally configure Tasker to check consent status before sending:

1. Create a periodic task that queries the consent status endpoint
2. Store consent state in Tasker variables (e.g., `%CONSENT_APP_USAGE`)
3. Add an If condition to each profile task: only send events when the corresponding consent variable is `true`

This client-side check is optional. The API always enforces consent regardless.

### 6.4 Safe Mode

When safe mode is activated (via Discord command or distress detection):

- Confrontation features pause
- Surveillance ingestion continues to accept events
- The consent ledger state is preserved
- No data is lost during safe mode

Safe mode does not revoke consent. It pauses Guinevere's response behavior while preserving the data pipeline.

---

## 7. Security Considerations

### 7.1 Transport Security

- **HTTPS only.** Tasker must connect to the API over TLS. Never configure `%API_URL` with an `http://` scheme. The API rejects plaintext connections.
- **Certificate validation.** Tasker's HTTP Request action validates TLS certificates by default. Do not disable certificate validation.

### 7.2 HMAC Signing

- Every request is signed with HMAC-SHA256
- The signature covers the HTTP method, path, timestamp, nonce, and body
- Unsigned or invalid requests are rejected with HTTP 401
- The signing secret is stored in `%HMAC_SECRET` and never embedded in task actions

### 7.3 Replay Protection

- Each request includes a unique nonce (UUID v4)
- The API checks timestamps against a replay window (configurable, default 5 minutes)
- Requests with timestamps outside the window are rejected
- Nonces are tracked server-side to prevent replay of the same signed request

### 7.4 Secret Storage

| Secret | Storage | Rotation |
|---|---|---|
| HMAC secret | `%HMAC_SECRET` Tasker global variable | Rotate via SOPS, update variable on device |
| API URL | `%API_URL` Tasker global variable | Update when endpoint changes |
| Device ID | `%DEVICE_ID` Tasker global variable | Generate once, keep stable |

Never store secrets in:
- Tasker profile/task descriptions
- Exported Tasker XML backups (scrub before sharing)
- Version control
- Log output or toast messages

### 7.5 Data Minimization

Tasker profiles collect only the data fields described in Section 4. Each profile sends the minimum payload needed for the event type. Raw sensor data (camera frames, microphone audio) is not collected by these profiles.

---

## 8. Troubleshooting

### 8.1 Events Not Reaching the API

| Symptom | Possible Cause | Fix |
|---|---|---|
| HTTP 401 response | Invalid HMAC signature | Verify `%HMAC_SECRET` matches the server-side secret. Check timestamp format (Unix epoch seconds, not milliseconds). |
| HTTP 403 response | Consent not granted for scope | Check consent ledger. Grant consent via Discord command. |
| HTTP 400 response | Malformed JSON body | Verify the JSON structure matches Section 5.3. Check for unescaped characters in payload. |
| Connection timeout | Network issue or wrong URL | Verify `%API_URL` is correct and reachable. Test with a browser on the device. |
| SSL certificate error | Certificate validation failure | Verify the endpoint has a valid TLS certificate. Do not disable validation. |
| Profile not triggering | Permission not granted | Check the relevant permission in Settings > Apps > Tasker. |

### 8.2 Battery and Background Issues

| Symptom | Possible Cause | Fix |
|---|---|---|
| Profiles stop after screen off | Battery optimization killing Tasker | Disable battery optimization (Section 1.4) |
| Inconsistent event timing | Android Doze mode | Disable battery optimization; on Samsung/Xiaomi, follow dontkillmyapp.com |
| Location not updating | Background location restricted | Grant "Allow all the time" for location permission |

### 8.3 HMAC Signature Mismatch

If the API returns 401 with a signature mismatch error:

1. Verify `%HMAC_SECRET` is correct (re-decrypt from SOPS and re-enter)
2. Check that the timestamp is in Unix epoch seconds (not milliseconds)
3. Confirm the canonical signing string matches exactly: `POST\n/surveillance/events\n{timestamp}\n{nonce}\n{body}`
4. Verify the body JSON is identical to what is transmitted (no extra whitespace or reordering)
5. Check that the HMAC output is hex-encoded (lowercase), not base64

### 8.4 Plugin Issues

| Symptom | Possible Cause | Fix |
|---|---|---|
| Notifications not intercepted | AutoNotification not enabled | Settings > Apps > Special app access > Notification access > AutoNotification ON |
| Clipboard not detected | AutoInput accessibility service stopped | Settings > Accessibility > AutoInput > ON. Disable battery optimization for AutoInput. |
| Usage stats empty | Usage access not granted | Settings > Apps > Special app access > Usage access > Tasker ON |

---

## 9. Testing

### 9.1 Verify Connectivity

Before testing full profiles, confirm Tasker can reach the API:

1. Create a test task in Tasker with a single **HTTP Request** action
2. Method: `GET`
3. URL: `%API_URL/health` (or the API health endpoint)
4. Run the task manually
5. Check the response. A 200 status means connectivity works.

### 9.2 Test Event Submission

Create a test task that sends a single app_usage event:

1. Add a **JavaScriptlet** action with the HMAC signing code (from P7-017)
2. Set local variables:
   - `event_type` = `app_usage`
   - `payload` = `{"app_package": "com.test.example", "duration_seconds": 60}`
3. Add an **HTTP Request** action:
   - Method: `POST`
   - URL: `%API_URL/surveillance/events`
   - Content Type: `application/json`
   - Body: the JSON from the JavaScriptlet output
   - Headers: `X-Signature: %signature`, `X-Timestamp: %timestamp`, `X-Nonce: %nonce`
4. Run the task
5. Expected: HTTP 200 or 202 response

### 9.3 Test Each Profile

After setting up each profile (P7-013 through P7-016):

1. Trigger the profile manually or wait for its natural trigger
2. Check Tasker's **Run Log** (Menu > Run Log) for execution entries
3. Verify the HTTP request was sent (check the response code in the log)
4. Confirm the event appears in the Guinevere API logs or TimescaleDB

### 9.4 Verify HMAC Signing

To confirm signing works correctly:

1. Send a test event with a known payload
2. Check the server-side logs for the received signature
3. Independently compute the expected HMAC using the same secret, timestamp, nonce, and body
4. The signatures should match exactly

### 9.5 Verify Consent Enforcement

1. Revoke a consent scope via Discord command (e.g., `surveillance.clipboard`)
2. Trigger the clipboard profile
3. Expected: API returns HTTP 403 for that event type
4. Re-grant consent and trigger again
5. Expected: API returns HTTP 200 or 202

---

## 10. References

| Document | Path |
|---|---|
| Surveillance Data Policy | `docs/30-data/SurveillanceDataPolicy.md` |
| Consent Revocation Policy | `docs/30-data/ConsentRevocationPolicy.md` |
| Security Policy | `docs/20-security/SecurityPolicy.md` |
| ADR Index | `docs/10-governance/17-ADR_Index_v1.0.md` |
| Persona Safety Policy | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` |
| HMAC JavaScriptlet (P7-017) | `docs/setup-evidence/P7/STEP-P7-017/` |
| App Usage Profile (P7-013) | `docs/setup-evidence/P7/STEP-P7-013/` |
| Location Profile (P7-014) | `docs/setup-evidence/P7/STEP-P7-014/` |
| Notification Profile (P7-015) | `docs/setup-evidence/P7/STEP-P7-015/` |
| Clipboard Profile (P7-016) | `docs/setup-evidence/P7/STEP-P7-016/` |

---

## Footer

| Field | Value |
|---|---|
| **Step** | STEP-P7-012 |
| **Date** | 2026-06-02 |
| **Author** | Guinevere (autonomous engineering agent) |
| **Scope** | Documentation: Android Tasker setup guide for surveillance data collection |
| **Dependencies** | P7-013 (app usage), P7-014 (location), P7-015 (notifications), P7-016 (clipboard), P7-017 (HMAC JavaScriptlet) |
| **Evidence path** | `docs/setup-evidence/P7/STEP-P7-012/tasker-setup-guide.md` |
