# P7-015: Tasker Notification Profile

## Overview

This document describes the Tasker profile configuration for capturing notification metadata on Android. The profile intercepts incoming notifications, extracts the source app name, notification title, and a truncated text preview, then packages the data into an HMAC-signed event and submits it to the Guinevere surveillance API.

The notification profile collects only metadata and a brief text preview. It does not capture full notification content, attached images, action buttons, or reply text. This approach balances contextual awareness with privacy minimization.

**Event flow:**

```
Notification arrives -> AutoNotification intercepts -> Tasker task extracts fields -> HMAC sign (P7-017) -> POST to Guinevere API
```

## Prerequisites

Before setting up the notification profile, complete the initial Tasker setup described in **P7-012**. The following must already be in place:

| Requirement | Detail |
|---|---|
| **Tasker 5.8 or later** | Core automation engine with JavaScriptlet support |
| **AutoNotification plugin** | Google Play Store (joaomgcd). Required for notification interception. |
| **Notification Listener access** | Android Settings > Apps > Special app access > Notification access > AutoNotification ON |
| **Global variables configured** | `%API_URL`, `%HMAC_SECRET`, `%DEVICE_ID` set per P7-012 |
| **HMAC JavaScriptlet installed** | Signing script from P7-017 available at `/sdcard/Tasker/scripts/hmac-sign.js` |
| **Battery optimization disabled** | Tasker and AutoNotification set to Unrestricted (see P7-012, Section 1.4) |

### Alternative: Built-in Notification Event

Tasker 5.8 includes a built-in "Notification" event trigger that works without AutoNotification. If you prefer not to install the plugin, use the built-in trigger instead. The built-in trigger provides `%ntitle` (notification title), `%ntext` (notification body), and `%npackage` (source package name). However, AutoNotification offers richer filtering and more reliable interception on newer Android versions.

## Profile Setup

### Step 1: Create the Profile

1. Open Tasker and go to the **PROFILES** tab
2. Tap the **+** button
3. Select **Event**
4. Choose one of the following triggers:

| Option | Path | Notes |
|---|---|---|
| **AutoNotification Intercept** | Plugin > AutoNotification > Intercept | Requires AutoNotification plugin. More reliable, richer data. |
| **Built-in Notification** | Event > Notification | No plugin required. Limited field access. |

#### AutoNotification Intercept Configuration

When using AutoNotification, configure the intercept event:

1. **Action**: Intercept
2. **Filter by package**: Leave empty to capture all, or specify allowed packages
3. **Cancel notification**: No (let the notification display normally)
4. **Only on status bar**: Yes (avoid intercepting notification removals)

The intercept event exposes these AutoNotification variables:

| Variable | Content |
|---|---|
| `%antitle` | Notification title text |
| `%antext` | Notification body text |
| `%anpackage` | Source app package name (e.g., `com.example.messaging`) |
| `%anchannelid` | Notification channel ID (may be null) |
| `%angroup` | Notification group key |

#### Built-in Notification Configuration

When using the built-in Notification event:

1. **Owner Application**: Leave blank to capture all apps
2. The event exposes: `%ntitle`, `%ntext`, `%npackage`

### Step 2: Create the Task

Create a new task named `Guinevere-Notification-Capture` with these actions in order:

**Action 1: Consent Check (If condition)**

```
If: %CONSENT_NOTIFICATIONS ~ true
```

Skip all subsequent actions if the consent variable is not true. This provides client-side filtering to avoid wasting bandwidth on events the server will reject.

**Action 2: Variable Set (extract fields)**

Set local variables from the intercepted notification:

| Variable | Value (AutoNotification) | Value (Built-in) |
|---|---|---|
| `%notif_app` | `%anpackage` | `%npackage` |
| `%notif_title` | `%antitle` | `%ntitle` |
| `%notif_text` | `%antext` | `%ntext` |
| `%notif_channel` | `%anchannelid` | (not available) |

**Action 3: Variable Truncate (text preview)**

Truncate `%notif_text` to 100 characters maximum:

```
Variable Set: %notif_text_preview = %notif_text
Variable Search Replace: %notif_text_preview, regex: ^(.{100}).*, Replace: $1...
```

If the original text is 100 characters or fewer, no truncation occurs. If longer, the preview is cut to 100 characters with an ellipsis appended.

**Action 4: JavaScriptlet (HMAC signing)**

Run the HMAC signing JavaScriptlet from **P7-017**. Before calling it, build the event payload:

```javascript
var payload = JSON.stringify({
    "app_name": local("notif_app"),
    "title": local("notif_title"),
    "text_preview": local("notif_text_preview"),
    "channel_id": local("notif_channel") || null
});

var body = buildEventPayload("notification", global("DEVICE_ID"), payload);
setLocal("hmac_body", body);
```

Then invoke the signing script (or inline the signing logic from P7-017). After execution, three local variables are set: `%hmac_signature`, `%hmac_timestamp`, `%hmac_nonce`.

**Action 5: HTTP Request**

| Field | Value |
|---|---|
| Method | POST |
| URL | `%API_URL/surveillance/events` |
| Content Type | `application/json` |
| Body | `%hmac_body` |
| Headers | See below |

Header configuration:

```
Content-Type:application/json
X-Signature:%hmac_signature
X-Timestamp:%hmac_timestamp
X-Nonce:%hmac_nonce
```

## Event Format

The JSON payload sent to the Guinevere API follows this structure:

```json
{
    "event_type": "notification",
    "device_id": "%DEVICE_ID",
    "occurred_at": "2026-01-01T12:00:00Z",
    "payload": {
        "app_name": "com.example.messaging",
        "title": "New Message",
        "text_preview": "Hello, this is a...",
        "channel_id": null
    }
}
```

### Field Descriptions

| Field | Type | Description |
|---|---|---|
| `event_type` | string | Always `"notification"` for this profile |
| `device_id` | string | Device UUID from `%DEVICE_ID` (configured per P7-012) |
| `occurred_at` | string | ISO 8601 timestamp when the notification arrived |
| `payload.app_name` | string | Package name of the app that posted the notification |
| `payload.title` | string | Notification title text (full, not truncated) |
| `payload.text_preview` | string | Notification body text, truncated to 100 characters |
| `payload.channel_id` | string or null | Android notification channel ID, if available |

### Example Payloads

**Messaging app notification:**

```json
{
    "event_type": "notification",
    "device_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "occurred_at": "2026-01-15T09:30:00Z",
    "payload": {
        "app_name": "com.example.messaging",
        "title": "New Message",
        "text_preview": "Hey, are you free for lunch today? I was thinking we could try that new place around the c...",
        "channel_id": "direct_messages"
    }
}
```

**Social media notification:**

```json
{
    "event_type": "notification",
    "device_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "occurred_at": "2026-01-15T14:22:00Z",
    "payload": {
        "app_name": "com.example.social",
        "title": "3 new likes",
        "text_preview": "Your post got 3 new likes from users in your network.",
        "channel_id": "engagement"
    }
}
```

**System notification (filtered out, not captured):**

System notifications from `com.android.systemui`, `com.google.android.gms`, and similar packages are excluded by the filtering rules below.

## Filtering

Not all notifications should be captured. The profile applies filtering to exclude noise and focus on notifications that provide meaningful context.

### Exclusion List

The following package names are excluded. Notifications from these apps are never captured:

| Package Name | Reason |
|---|---|
| `com.android.systemui` | System UI notifications (battery, connectivity) |
| `com.google.android.gms` | Google Play Services background notifications |
| `com.android.settings` | Settings alerts |
| `com.google.android.packageinstaller` | App install/update prompts |
| `com.android.vending` | Play Store notifications |
| `com.google.android.googlequicksearchbox` | Google app suggestions |

### Inclusion Priority

Notifications from these app categories are prioritized for capture:

| Category | Example Packages | Priority |
|---|---|---|
| Messaging | `com.example.messaging`, `com.example.chat` | High |
| Social media | `com.example.social`, `com.example.network` | High |
| Email | `com.example.email`, `com.example.mail` | Medium |
| Calendar | `com.example.calendar` | Medium |
| News | `com.example.news` | Low |

### Filter Implementation

In the Tasker task, add a Variable Search Replace action after extracting `%notif_app`:

```
If: %notif_app ~ com.android.systemui|com.google.android.gms|com.android.settings|com.google.android.packageinstaller|com.android.vending
    Stop
End If
```

This stops the task before any data is collected or sent for excluded packages.

## HMAC Signing

Every notification event submitted to the Guinevere API must carry a valid HMAC-SHA256 signature. The signing logic is implemented in the reusable JavaScriptlet created by **P7-017**.

The signing process:

1. Build the JSON event payload using `buildEventPayload("notification", deviceId, payload)`
2. Generate a UUID nonce and Unix timestamp
3. Construct the signing string: `POST:/surveillance/events:{timestamp}:{nonce}:{body}`
4. Compute HMAC-SHA256 over the signing string using `%HMAC_SECRET`
5. Set output variables `%hmac_signature`, `%hmac_timestamp`, `%hmac_nonce`

The server validates all three headers. It recomputes the HMAC and compares using constant-time comparison. Requests with missing, expired, or mismatched signatures receive HTTP 401.

See **P7-017** (`docs/setup-evidence/P7/STEP-P7-017/`) for the full JavaScriptlet implementation, testing instructions, and troubleshooting.

## Consent

The notification profile requires active consent scope `surveillance.notifications` in the Guinevere consent ledger.

### Enforcement Layers

| Layer | Mechanism | Behavior |
|---|---|---|
| **Server-side** | API checks consent ledger on every incoming event | Returns HTTP 403 if `surveillance.notifications` is not granted |
| **Client-side** | Tasker checks `%CONSENT_NOTIFICATIONS` before processing | Skips the task entirely if consent is not active |

The server-side check is authoritative. The client-side check is an optimization to reduce rejected requests and save battery.

### Consent Lifecycle

- **Grant**: Via Discord command or consent API
- **Revoke**: Via Discord command. Takes effect immediately. The API stops accepting notification events.
- **Re-grant**: Via Discord command. Collection resumes on the next intercepted notification.

The notification profile does not cache consent state for longer than one task execution. Each notification trigger re-checks the consent variable.

## Privacy

### Data Classification

Notification metadata is classified as **Confidential** under the Guinevere Data Governance policy. This classification requires:

- Encrypted transport (TLS via Cloudflare Tunnel)
- HMAC-signed requests
- No plaintext storage in Tasker logs or exported backups
- Access restricted to authorized components only

### Text Preview Truncation

The `text_preview` field is truncated to **100 characters** maximum. This limit provides enough context for activity awareness without capturing full message bodies. The truncation happens on-device before the payload is constructed.

### What Is NOT Collected

| Data | Collected | Reason |
|---|---|---|
| App package name | Yes | Identifies the source app |
| Notification title | Yes | Provides topic context |
| Text preview (100 chars) | Yes | Brief content indicator |
| Channel ID | Yes | Helps categorize notification type |
| Full notification body | No | Excessive for context purposes |
| Attached images/media | No | Privacy boundary |
| Action buttons | No | Not relevant to surveillance |
| Inline reply text | No | User input is not surveillance data |
| Notification sound/vibration | No | Not relevant |
| Sender contact details | No | Personal data boundary |

### Retention

Notification events follow the standard surveillance data retention policy. Events are buffered in Redis DB2 and consumed into TimescaleDB. Retention period is governed by the Surveillance Data Policy (`docs/30-data/SurveillanceDataPolicy.md`).

## Battery Optimization

### Notification Batching

During periods of high notification volume, the profile applies batching to reduce network requests and battery drain:

**Batching rule**: If more than 5 notifications arrive within 60 seconds, subsequent notifications in that window are collected but held in a local buffer. The buffer flushes as a single batched request after the burst subsides (60-second quiet period).

**Implementation approach:**

1. On each notification, increment a counter: `%notif_count`
2. Reset the counter after 60 seconds of no new notifications
3. If `%notif_count` exceeds 5, queue the event payload in `%notif_queue` (Tasker array variable)
4. After the quiet period, send all queued events in a single HTTP request or as sequential requests with shared signing

**Alternative (simpler)**: Send each notification immediately but add a 10-second cooldown between HTTP requests. Notifications that arrive during the cooldown are queued and sent after the cooldown expires.

### Background Operation

To keep the notification profile running reliably:

- Disable battery optimization for Tasker and AutoNotification (P7-012, Section 1.4)
- On Samsung, Xiaomi, and Huawei devices, follow device-specific steps at dontkillmyapp.com
- Enable Tasker's "Use Root" option if available, for more reliable background operation
- Keep Tasker's "Beginner Mode" disabled to access all profile options

## Troubleshooting

### Notification Listener Permission Not Working

**Symptom**: Profile never triggers. No entries in Tasker's Run Log.

**Fix**:
1. Go to Settings > Apps > Special app access > Notification access
2. Verify AutoNotification is toggled ON
3. If already ON, toggle it OFF then ON again (Android sometimes loses the listener registration)
4. Reboot the device if toggling does not work
5. Verify AutoNotification is not restricted by battery optimization

### AutoNotification Intercept Not Firing

**Symptom**: AutoNotification is installed and has notification access, but the intercept event does not trigger.

**Fix**:
1. Open AutoNotification standalone app
2. Go to "Intercept" settings
3. Verify "Enable Intercept" is ON
4. Check the filter configuration. If package filters are set, make sure the target app is included
5. Set "Cancel Notification" to No (canceling can prevent the intercept from completing on some devices)
6. Test by sending a test notification to the device

### Built-in Notification Event Not Triggering

**Symptom**: Using the built-in Notification event (no AutoNotification) but the profile does not fire.

**Fix**:
1. Verify Tasker has notification access: Settings > Apps > Special app access > Notification access > Tasker ON
2. Leave the "Owner Application" field blank to capture all apps
3. Check that the notification is a new notification (not an update to an existing one). The built-in event fires only on new notifications.

### Variables Empty or Null

**Symptom**: The HTTP request sends but `app_name`, `title`, or `text_preview` is empty.

**Fix**:
1. Check which variable source you are using (AutoNotification vs built-in)
2. For AutoNotification: verify `%antitle`, `%antext`, `%anpackage` are populated by adding a Flash action to display them
3. For built-in: verify `%ntitle`, `%ntext`, `%npackage` are populated
4. Some notifications have empty titles or text (e.g., media playback controls). The profile sends them as-is with empty strings.

### HTTP 401 Unauthorized

**Symptom**: API returns HTTP 401 for notification events.

**Fix**:
1. Verify `%HMAC_SECRET` is set and not empty
2. Confirm the JavaScriptlet from P7-017 runs before the HTTP Request action
3. Check that `%hmac_body` matches the exact body sent in the HTTP Request
4. Verify device clock is synchronized (timestamp drift causes signature rejection)
5. See P7-017 Troubleshooting section for detailed signing diagnostics

### HTTP 403 Forbidden

**Symptom**: API returns HTTP 403 for notification events.

**Fix**:
1. Check that consent scope `surveillance.notifications` is granted in the consent ledger
2. Grant consent via Discord command if revoked
3. Update `%CONSENT_NOTIFICATIONS` Tasker variable to `true` if using client-side checking

### High Battery Drain

**Symptom**: Noticeable battery impact after enabling the notification profile.

**Fix**:
1. Enable notification batching (see Battery Optimization section above)
2. Review the exclusion list and add more packages to reduce capture volume
3. Reduce HTTP request frequency by increasing the cooldown between sends
4. Verify battery optimization is properly configured per P7-012

## References

| Document | Path |
|---|---|
| Tasker Setup Guide (P7-012) | `docs/setup-evidence/P7/STEP-P7-012/tasker-setup-guide.md` |
| HMAC JavaScriptlet (P7-017) | `docs/setup-evidence/P7/STEP-P7-017/tasker-hmac-jslet.md` |
| App Usage Profile (P7-013) | `docs/setup-evidence/P7/STEP-P7-013/` |
| Location Profile (P7-014) | `docs/setup-evidence/P7/STEP-P7-014/` |
| Clipboard Profile (P7-016) | `docs/setup-evidence/P7/STEP-P7-016/` |
| Surveillance Data Policy | `docs/30-data/SurveillanceDataPolicy.md` |
| Consent Revocation Policy | `docs/30-data/ConsentRevocationPolicy.md` |
| Data Governance | `docs/30-data/DataGovernance.md` |
| Security Policy | `docs/20-security/SecurityPolicy.md` |

---

## Footer

| Field | Value |
|---|---|
| **Step** | STEP-P7-015 |
| **Date** | 2026-06-03 |
| **Author** | Guinevere (autonomous engineering agent) |
| **Scope** | Documentation: Tasker notification capture profile for surveillance event collection |
| **Dependencies** | P7-012 (Tasker setup), P7-017 (HMAC signing) |
| **Evidence path** | `docs/setup-evidence/P7/STEP-P7-015/tasker-notifications.md` |
