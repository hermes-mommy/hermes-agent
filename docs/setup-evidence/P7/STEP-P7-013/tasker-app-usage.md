# P7-013: Tasker App Usage Profile

## Overview

This document describes how to create the Tasker profile that tracks foreground app usage on an Android device. The profile captures two event types: app entry (when an app comes to the foreground) and app exit (when an app leaves the foreground). Each event is packaged into an HMAC-signed HTTP request and submitted to the Guinevere surveillance ingestion API.

The profile monitors which app is currently in the foreground, records when the user switches to a new app, and calculates how long the previous app was visible. This gives a continuous picture of device usage patterns without requiring any additional hardware or third-party services beyond Tasker itself.

**Event flow:**

```
Android foreground change --> Tasker profile fires --> HMAC-signed POST --> Guinevere API (/surveillance/events)
```

---

## Prerequisites

Before building this profile, complete the following:

| Requirement | Detail |
|---|---|
| Tasker | Version 5.8 or later installed and running |
| AutoTools plugin | Optional. Some Tasker builds expose app-switch contexts natively; AutoTools provides additional helper actions if needed |
| P7-012 setup guide | Complete the initial Tasker variable configuration (`%API_URL`, `%HMAC_SECRET`, `%DEVICE_ID`). See `docs/setup-evidence/P7/STEP-P7-012/tasker-setup-guide.md` |
| Usage Access permission | Grant Tasker access to usage statistics. Go to Settings > Apps > Special app access > Usage access > toggle ON for Tasker |
| Battery optimization disabled | Exempt Tasker from battery optimization. See Section 1.4 in the P7-012 setup guide |
| HMAC JavaScriptlet | The signing script from P7-017 must be available. See `docs/setup-evidence/P7/STEP-P7-017/tasker-hmac-jslet.md` |
| Active consent | The consent scope `surveillance.app_usage` must be granted in the Guinevere consent ledger before events will be accepted by the API |

---

## Profile Setup

### Step 1: Create the Profile

1. Open Tasker
2. Go to the **PROFILES** tab
3. Tap the **+** button to create a new profile
4. Select **Application** as the context type
5. Leave the application filter empty to trigger on any app switch (or select specific apps if you only want to track a subset)
6. Name the profile `App Usage Tracker`

Tasker's Application context fires when the specified application enters the foreground (entry task) and when it leaves the foreground (exit task). This gives you both events from a single profile definition.

### Step 2: Create the Entry Task

The entry task fires when an app comes to the foreground. It captures the app name and timestamp, then signs and sends the event.

1. Tap **New Task** when prompted after creating the profile
2. Name it `App Usage Entry`
3. Add the following actions in order:

**Action 1: Record the current time**

- Action type: **Variables > Variable Set**
- Name: `%entry_time`
- To: `%TIMES` (Tasker's built-in Unix timestamp variable)

This captures the moment the app came to the foreground. The exit task will use this to calculate duration.

**Action 2: Record the current app package name**

- Action type: **Variables > Variable Set**
- Name: `%current_app`
- To: `%APP` (Tasker's built-in variable for the foreground application package name when triggered by an Application context)

If `%APP` is not available in your Tasker version, use the **Code > Run Shell** action with the command `dumpsys activity activities | grep mResumedActivity` and parse the output to extract the package name. AutoTools can also retrieve this value.

**Action 3: Build the event payload**

- Action type: **Code > JavaScriptlet**
- Code:

```javascript
var event_type = "app_usage";
var device_id = global("DEVICE_ID");
var occurred_at = new Date().toISOString();
var payload = {
    app_name: global("current_app"),
    action: "enter",
    duration_seconds: null
};

var body = JSON.stringify({
    event_type: event_type,
    device_id: device_id,
    occurred_at: occurred_at,
    payload: payload
});

setLocal("hmac_body", body);
```

This constructs the JSON body that matches the `SurveillanceEventRequest` Pydantic model on the server. The `action` field indicates the app just entered the foreground, and `duration_seconds` is `null` because the session is still open.

**Action 4: HMAC signing**

- Action type: **Code > JavaScriptlet**
- Source: Include the HMAC signing code from P7-017 (see `docs/setup-evidence/P7/STEP-P7-017/tasker-hmac-jslet.md`)

The JavaScriptlet reads `%hmac_body`, computes the HMAC-SHA256 signature using `%HMAC_SECRET`, and sets three local variables: `%hmac_signature`, `%hmac_timestamp`, `%hmac_nonce`.

**Action 5: Send the event**

- Action type: **Net > HTTP Request**
- Method: `POST`
- URL: `%API_URL/surveillance/events`
- Headers:

```
Content-Type:application/json
X-Signature:%hmac_signature
X-Timestamp:%hmac_timestamp
X-Nonce:%hmac_nonce
```

- Body: `%hmac_body`
- Content Type: `application/json`
- Timeout: 30 seconds

If the request fails (no network, server unreachable), Tasker logs the error. See the Battery Optimization section below for retry strategies.

### Step 3: Create the Exit Task

The exit task fires when an app leaves the foreground. It captures the duration since entry and sends the event.

1. Long-press the `App Usage Entry` task in the profile
2. Select **Add Exit** to attach an exit task
3. Name it `App Usage Exit`
4. Add the following actions in order:

**Action 1: Calculate session duration**

- Action type: **Variables > Variable Set**
- Name: `%exit_time`
- To: `%TIMES`

- Action type: **Variables > Variable Set**
- Name: `%session_duration`
- To: `%exit_time - %entry_time`

This computes the number of seconds the app was in the foreground. If `%entry_time` was never set (profile just created), the value defaults to 0, and the event still sends with a `duration_seconds` of 0.

**Action 2: Build the exit event payload**

- Action type: **Code > JavaScriptlet**
- Code:

```javascript
var event_type = "app_usage";
var device_id = global("DEVICE_ID");
var occurred_at = new Date().toISOString();
var duration = parseInt(local("session_duration"), 10) || 0;
var payload = {
    app_name: global("current_app"),
    action: "exit",
    duration_seconds: duration
};

var body = JSON.stringify({
    event_type: event_type,
    device_id: device_id,
    occurred_at: occurred_at,
    payload: payload
});

setLocal("hmac_body", body);
```

The exit event mirrors the entry event but sets `action` to `"exit"` and includes the calculated `duration_seconds`.

**Action 3: HMAC signing**

Same as Action 4 in the entry task. Include the HMAC signing JavaScriptlet from P7-017.

**Action 4: Send the event**

Same as Action 5 in the entry task. POST to `%API_URL/surveillance/events` with the HMAC headers and `%hmac_body`.

### Step 4: Activate the Profile

1. Tap the back arrow to return to the profiles list
2. Ensure the `App Usage Tracker` profile toggle is ON (green)
3. Wait for the next app switch to trigger the profile
4. Open Tasker's **Run Log** (Menu > Run Log) to confirm both entry and exit tasks executed

---

## Event Format

Every event sent by this profile conforms to the `SurveillanceEventRequest` Pydantic model defined in `src/surveillance/models.py`.

### Entry Event (app comes to foreground)

```json
{
    "event_type": "app_usage",
    "device_id": "%DEVICE_ID",
    "occurred_at": "2026-01-01T12:00:00Z",
    "payload": {
        "app_name": "com.example.app",
        "action": "enter",
        "duration_seconds": null
    }
}
```

### Exit Event (app leaves foreground)

```json
{
    "event_type": "app_usage",
    "device_id": "%DEVICE_ID",
    "occurred_at": "2026-01-01T12:05:30Z",
    "payload": {
        "app_name": "com.example.app",
        "action": "exit",
        "duration_seconds": 330
    }
}
```

### Field Reference

| Field | Type | Description |
|---|---|---|
| `event_type` | string (literal) | Always `"app_usage"`. The server validates this against a fixed set of allowed values |
| `device_id` | string | Unique device identifier from `%DEVICE_ID` global variable |
| `occurred_at` | ISO 8601 datetime | Timestamp when the event happened. Must include timezone information |
| `payload.app_name` | string | Android package name of the foreground app (e.g., `"com.example.browser"`) |
| `payload.action` | string | Either `"enter"` or `"exit"` indicating the direction of the app switch |
| `payload.duration_seconds` | integer or null | Seconds the app was in the foreground. `null` for entry events, integer for exit events |

The server rejects payloads that do not match this schema. Extra top-level fields result in HTTP 422. Missing required fields result in HTTP 422. The `extra="forbid"` constraint on the Pydantic model is strict.

---

## HMAC Signing

Every request sent by this profile must be signed with HMAC-SHA256 before transmission. The signing implementation lives in a reusable JavaScriptlet created by **STEP-P7-017**.

### How It Works

1. The profile task builds the JSON body and stores it in `%hmac_body`
2. The HMAC signing JavaScriptlet (from P7-017) reads `%hmac_body` and `%HMAC_SECRET`
3. The script generates a UUID nonce and Unix timestamp
4. The signing string is constructed: `POST:/surveillance/events:{timestamp}:{nonce}:{body}`
5. HMAC-SHA256 is computed over the signing string using the secret key
6. Three output variables are set: `%hmac_signature`, `%hmac_timestamp`, `%hmac_nonce`
7. The HTTP Request action attaches these as headers

### Required Headers

| Header | Value | Purpose |
|---|---|---|
| `Content-Type` | `application/json` | Body format |
| `X-Signature` | Hex-encoded HMAC-SHA256 digest | Authenticates the request |
| `X-Timestamp` | Unix epoch seconds | Replay window validation (server rejects requests older than 5 minutes) |
| `X-Nonce` | UUID v4 string | Replay protection (server tracks used nonces) |

For the full signing algorithm, Java bridge usage, and troubleshooting, see `docs/setup-evidence/P7/STEP-P7-017/tasker-hmac-jslet.md`.

---

## Consent

This profile requires active consent for the scope `surveillance.app_usage` before the API will accept events.

### How Consent Works

- **Grant:** Consent is granted via Discord command or the consent API
- **Enforcement:** The Guinevere API checks the consent ledger on every incoming event. Events for scopes without active consent are rejected with HTTP 403
- **Revoke:** Consent can be revoked at any time. Revocation takes effect immediately. The API stops accepting `app_usage` events as soon as the scope is revoked

### Optional Client-Side Consent Check

To avoid sending events that will be rejected (saving bandwidth and battery), you can add a consent pre-check to the profile:

1. Create a periodic task (every 30 minutes) that queries the consent status endpoint
2. Store the result in a Tasker variable: `%CONSENT_APP_USAGE` (true/false)
3. Add an **If** condition at the top of both the entry and exit tasks:

```
If %CONSENT_APP_USAGE eq true
    (run all actions)
End If
```

This client-side check is optional. The API always enforces consent server-side regardless of what the device sends.

---

## Battery Optimization

Foreground app tracking is relatively lightweight, but poor network conditions can cause request failures that drain battery if Tasker retries aggressively.

### Retry Strategy

When an HTTP request fails (timeout, 5xx response, no network):

1. **First retry:** Wait 30 seconds
2. **Second retry:** Wait 60 seconds
3. **Third retry:** Wait 120 seconds
4. **After third failure:** Stop retrying. Store the event payload in a Tasker array variable (`%PENDING_EVENTS`) and try again on the next successful network connection

This exponential backoff prevents battery drain from repeated failed requests. Tasker's built-in **Wait** action handles the delays.

### Event Batching

When the device has poor or no signal, events accumulate in the `%PENDING_EVENTS` array. Once connectivity returns:

1. A **WiFi Connected** or **Mobile Data Connected** profile triggers a flush task
2. The flush task iterates through `%PENDING_EVENTS`
3. Each stored event is re-signed (fresh timestamp and nonce) and sent
4. The array is cleared after successful submission

Keep the batch size reasonable (under 50 events). If the array grows beyond that, drop the oldest events to prevent memory pressure.

### Android Battery Settings

Ensure these are configured (as described in P7-012 setup guide Section 1.4):

| Setting | Value |
|---|---|
| Tasker battery optimization | Unrestricted / Don't optimize |
| Background activity | Allowed |
| Manufacturer battery saver | Disabled for Tasker (check dontkillmyapp.com for your device) |

---

## Troubleshooting

### Profile Not Triggering

| Symptom | Cause | Fix |
|---|---|---|
| Entry task never fires | Usage Access permission not granted | Settings > Apps > Special app access > Usage access > Tasker ON |
| Profile toggle is grey | Profile is disabled | Long-press the profile and select Enable |
| Only some apps trigger | Application filter is too narrow | Edit the profile context and clear the application filter to match all apps |
| Profile stops after screen off | Battery optimization killing Tasker | Disable battery optimization for Tasker (see Battery Optimization section) |

### HTTP Errors

| Code | Meaning | Fix |
|---|---|---|
| 401 | HMAC signature invalid | Verify `%HMAC_SECRET` matches server secret. Check that timestamp is Unix seconds (not milliseconds). Re-run the P7-017 test procedure |
| 403 | Consent not active | The scope `surveillance.app_usage` is not granted. Grant consent via Discord command |
| 422 | Payload validation error | Check the JSON structure matches the Event Format section. Ensure `occurred_at` includes timezone info. Ensure no extra top-level fields |
| 5xx | Server error | Wait and retry. The exponential backoff strategy handles this automatically |

### Data Issues

| Symptom | Cause | Fix |
|---|---|---|
| `%APP` variable is empty | Tasker cannot read usage stats | Verify Usage Access is granted. On some Android versions, reboot after granting |
| Duration is always 0 | Entry task did not set `%entry_time` | Check that Action 1 in the entry task runs before the JavaScriptlet. Check the Run Log for errors |
| Duplicate events | Profile fires twice on app switch | Ensure only one Application context profile exists for this event type. Remove duplicate profiles |
| Timestamps are wrong | Device clock is out of sync | Enable automatic date and time in Android settings. Check with `adb shell date` |

### HMAC Signature Mismatch

If the API returns 401:

1. Confirm `%HMAC_SECRET` contains the correct value (re-decrypt from SOPS if needed)
2. Verify the signing string format: `POST:/surveillance/events:{timestamp}:{nonce}:{body}`
3. Check that `%hmac_body` JSON is exactly what gets transmitted (no extra whitespace or field reordering)
4. Verify HMAC output is lowercase hex-encoded
5. Run the P7-017 test procedure with a known payload to cross-check

---

## References

| Document | Path |
|---|---|
| P7-012 Tasker Setup Guide | `docs/setup-evidence/P7/STEP-P7-012/tasker-setup-guide.md` |
| P7-017 HMAC Signing JavaScriptlet | `docs/setup-evidence/P7/STEP-P7-017/tasker-hmac-jslet.md` |
| Surveillance Models (Pydantic) | `src/surveillance/models.py` |
| Surveillance Data Policy | `docs/30-data/SurveillanceDataPolicy.md` |
| Consent Revocation Policy | `docs/30-data/ConsentRevocationPolicy.md` |
| Security Policy | `docs/20-security/SecurityPolicy.md` |

---

## Footer

| Field | Value |
|---|---|
| **Step** | STEP-P7-013 |
| **Date** | 2026-06-03 |
| **Author** | Guinevere (autonomous engineering agent) |
| **Scope** | Documentation: Tasker app usage profile for foreground app tracking |
| **Dependencies** | P7-012 (Tasker setup), P7-017 (HMAC signing) |
| **Evidence path** | `docs/setup-evidence/P7/STEP-P7-013/tasker-app-usage.md` |
