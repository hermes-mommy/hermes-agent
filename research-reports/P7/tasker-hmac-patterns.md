# Tasker HMAC-Signed HTTP POST Patterns — Research Report

> **Report**: P7 Tasker HMAC Patterns  
> **Date**: 2026-06-02  
> **Scope**: Working Tasker patterns for HMAC-SHA256 signed HTTP POST with JSON payloads, surveillance data collection (app usage, GPS, notifications, clipboard)  
> **Status**: COMPLETE

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Approach A: Native HTTP Request Action (Tasker 5.8+)](#2-approach-a-native-http-request-action)
3. [Approach B: JavaScriptlet with XMLHttpRequest](#3-approach-b-javascriptlet-with-xmlhttprequest)
4. [HMAC-SHA256 Signing — JavaScriptlet with CryptoJS](#4-hmac-sha256-signing--javascriptlet-with-cryptojs)
5. [HMAC-SHA256 Signing — Native Java Bridge (No CryptoJS)](#5-hmac-sha256-signing--native-java-bridge)
6. [Nonce Generation](#6-nonce-generation)
7. [Surveillance Profile: App Usage Tracking](#7-surveillance-profile-app-usage-tracking)
8. [Surveillance Profile: GPS Location / Geofencing](#8-surveillance-profile-gps-location--geofencing)
9. [Surveillance Profile: Notification Capture](#9-surveillance-profile-notification-capture)
10. [Surveillance Profile: Clipboard Monitoring](#10-surveillance-profile-clipboard-monitoring)
11. [Error Handling & Retry Logic](#11-error-handling--retry-logic)
12. [Battery Optimization: Batching vs Real-Time](#12-battery-optimization-batching-vs-real-time)
13. [Complete Tasker XML Task Snippet](#13-complete-tasker-xml-task-snippet)
14. [References & Sources](#14-references--sources)

---

## 1. Executive Summary

Two viable approaches exist for HMAC-signed HTTP POST in Tasker:

| Approach | Crypto Library | Complexity | Headers Support | Best For |
|---|---|---|---|---|
| **Native HTTP Request** (v5.8+) | Pre-computed in JavaScriptlet, then passed to HTTP Request action | Low | Native `Key:Value` format | Simple signing, few headers |
| **JavaScriptlet + XMLHttpRequest** | CryptoJS bundled inline or Java `javax.crypto` | Medium | Full `setRequestHeader()` control | Complex multi-header auth flows |

**Recommendation for Guinevere**: Use **Approach B (JavaScriptlet + XMLHttpRequest)** for maximum control over headers and signing flow. CryptoJS must be bundled inline (Tasker has no npm/CDN in JavaScriptlet). Alternatively, use Tasker's native Java bridge (`javax.crypto.Mac`) for HMAC without external dependencies.

---

## 2. Approach A: Native HTTP Request Action

Tasker's built-in **HTTP Request** action (v5.8+) supports custom headers natively.

**Source**: [Tasker HTTP Request docs](https://tasker.joaoapps.com/userguide/en/help/ah_http_request.html)

### Headers Format

```
Content-Type:application/json
X-HMAC:%hmac_signature
X-Nonce:%nonce_value
X-Timestamp:%timestamp_value
```

One header per line. Separate key from value with `:` (no extra spaces).

### Workflow

```
Step 1: JavaScriptlet — compute HMAC signature → set local variables
Step 2: Variable Set — assemble JSON body
Step 3: HTTP Request — POST with headers referencing %variables
```

### Limitation

Tasker variable interpolation in headers (`%hmac_signature`) requires the signing to happen in a prior action. Cannot compute HMAC inline in the HTTP Request action itself.

---

## 3. Approach B: JavaScriptlet with XMLHttpRequest

This is the **recommended approach** — all signing and HTTP in one action.

**Source**: [Tasker JavaScript Support](https://tasker.joaoapps.com/userguide/en/javascript.html), [Habitica Tasker integration](https://habitica.fandom.com/wiki/User_blog:LadyAlys/Android%27s_Tasker_app_and_HabitRPG%27s_API)

### Pattern (from Habitica wiki)

```javascript
function add_item() {
    var http = new XMLHttpRequest(); 
    http.open("POST", http_post_url, false);  // synchronous
    http.setRequestHeader("Content-Type", "application/json");
    http.setRequestHeader("x-api-user", HabitrpgUserid);
    http.setRequestHeader("x-api-key", HabitrpgApIToken);
    http.send(http_post_data); 
    return(http.responseText); 
} 
try { 
    var result = add_item();
}
catch(e) {
    var error = e.message;
}
```

### Pattern (from Home Assistant integration)

```javascript
const url = global('%HA_URL') + local('par1');
const token = 'Bearer ' + global('%HA_TOKEN');
const xhttp = new XMLHttpRequest();
xhttp.open('POST', url, false);
xhttp.setRequestHeader('Authorization', token);
xhttp.send(local('par2'));
if (xhttp.status != 200) { 
    console.error(xhttp.status + ' - ' + xhttp.responseText); 
}
```

### Key Tasker JavaScript Rules

- **Local variables** (lowercase, e.g. `%myvar`) → accessible directly as `myvar` (no `%` prefix)
- **Global variables** → accessed via `global('%VARNAME')` 
- **Setting variables back** → `setLocal('varname', value)` or `setGlobal('%VARNAME', value)`
- **XMLHttpRequest** is available natively in Tasker's JavaScript runtime
- **JSON** is available natively
- `open()` third parameter `false` = synchronous (required for Tasker JavaScriptlet)

---

## 4. HMAC-SHA256 Signing — JavaScriptlet with CryptoJS

### CryptoJS Bundling Requirement

Tasker's JavaScriptlet runtime does **NOT** include CryptoJS by default. You must either:

1. **Inline the CryptoJS HMAC-SHA256 module** directly in the JavaScriptlet code
2. **Use the JavaScript action** (not JavaScriptlet) pointing to a `.js` file that includes CryptoJS
3. **Use Tasker's native Java bridge** (see §5)

### CryptoJS Inline Pattern

Minimal CryptoJS core + HMAC + SHA256 (~15KB minified). Include at top of JavaScriptlet:

```javascript
// === CryptoJS Minimal Bundle (core + sha256 + hmac) ===
// Source: https://cdnjs.cloudflare.com/ajax/libs/crypto-js/4.2.0/crypto-js.min.js
// Paste the minified CryptoJS here, or use only these modules:
// - core.min.js
// - sha256.min.js  
// - hmac.min.js
// - enc-base64.min.js (if base64 output needed)
// - enc-hex.min.js (if hex output needed)

// === Signing Logic ===
var API_SECRET = global('%GUINEVERE_SECRET');
var timestamp = Math.floor(Date.now() / 1000).toString();
var nonce = java.util.UUID.randomUUID().toString();

var payload = JSON.stringify({
    event_type: event_type,
    device_id: device_id,
    timestamp: timestamp,
    data: payload_data
});

// HMAC string to sign: timestamp + nonce + payload
var signString = timestamp + nonce + payload;
var hmacHash = CryptoJS.HmacSHA256(signString, API_SECRET);
var signature = CryptoJS.enc.Hex.stringify(hmacHash);

// Send the request
var url = global('%GUINEVERE_API_URL');
var http = new XMLHttpRequest();
http.open('POST', url, false);
http.setRequestHeader('Content-Type', 'application/json');
http.setRequestHeader('X-HMAC', signature);
http.setRequestHeader('X-Nonce', nonce);
http.setRequestHeader('X-Timestamp', timestamp);
http.send(payload);

// Capture response
var responseCode = http.status;
var responseData = http.responseText;
setLocal('http_code', responseCode.toString());
setLocal('http_response', responseData);
setLocal('http_error', (http.status >= 400) ? 'true' : 'false');
```

### CryptoJS HMAC Usage Pattern (from multiple GitHub sources)

```javascript
// Basic HMAC-SHA256 → hex string
var hash = CryptoJS.HmacSHA256("Message", "Secret Passphrase");
var hexHash = hash.toString(CryptoJS.enc.Hex);

// HMAC-SHA256 → base64 string  
var hash = CryptoJS.HmacSHA256(message, secret_key);
var base64Hash = CryptoJS.enc.Base64.stringify(hash);

// Progressive HMAC (for large payloads)
var hmac = CryptoJS.algo.HMAC.create(CryptoJS.algo.SHA256, secretKey);
hmac.update("Part 1");
hmac.update("Part 2");
var hash = hmac.finalize();
```

**Sources**: 
- [CryptoJS docs](https://cryptojs.gitbook.io/docs)
- [AWS IoT SigV4 signing pattern](https://github.com/aws-samples/aws-iot-examples/blob/master/deviceSimulator/mqtt-lib.js)
- [FineUploader S3 signing](https://github.com/FineUploader/fine-uploader/blob/master/client/js/s3/request-signer.js)

---

## 5. HMAC-SHA256 Signing — Native Java Bridge

**No external library needed.** Tasker's JavaScriptlet can access Java classes directly via the `Packages` object or global scope.

```javascript
// === Native Java HMAC-SHA256 (no CryptoJS needed) ===
function hmacSha256(message, secret) {
    var mac = javax.crypto.Mac.getInstance("HmacSHA256");
    var secretKeySpec = new javax.crypto.spec.SecretKeySpec(
        new java.lang.String(secret).getBytes("UTF-8"),
        "HmacSHA256"
    );
    mac.init(secretKeySpec);
    var rawHmac = mac.doFinal(new java.lang.String(message).getBytes("UTF-8"));
    
    // Convert to hex string
    var hexString = new java.lang.StringBuilder();
    for (var i = 0; i < rawHmac.length; i++) {
        var hex = java.lang.Integer.toHexString(0xff & rawHmac[i]);
        if (hex.length() == 1) hexString.append('0');
        hexString.append(hex);
    }
    return hexString.toString();
}

// === Usage ===
var API_SECRET = global('%GUINEVERE_SECRET');
var timestamp = Math.floor(Date.now() / 1000).toString();
var nonce = java.util.UUID.randomUUID().toString();

var payload = JSON.stringify({
    event_type: "location_update",
    device_id: global('%DEVID'),
    timestamp: timestamp,
    data: {
        latitude: allatitude,
        longitude: allongitude,
        accuracy: alaccuracy
    }
});

var signString = timestamp + nonce + payload;
var signature = hmacSha256(signString, API_SECRET);

var http = new XMLHttpRequest();
http.open('POST', global('%GUINEVERE_API_URL'), false);
http.setRequestHeader('Content-Type', 'application/json');
http.setRequestHeader('X-HMAC', signature);
http.setRequestHeader('X-Nonce', nonce);
http.setRequestHeader('X-Timestamp', timestamp);
http.send(payload);

setLocal('http_code', http.status.toString());
setLocal('http_response', http.responseText);
```

**Advantage**: No CryptoJS dependency, smaller JavaScriptlet, uses Android's built-in `javax.crypto`.  
**Disadvantage**: Slightly more verbose Java interop code.

---

## 6. Nonce Generation

### Option A: Java UUID (Recommended)

```javascript
var nonce = java.util.UUID.randomUUID().toString();
```

Generates a standard UUID v4 string (e.g., `550e8400-e29b-41d4-a716-446655440000`).

### Option B: Timestamp-Based Nonce

```javascript
var nonce = Date.now().toString(36) + Math.random().toString(36).substring(2, 10);
```

Combines base-36 epoch millis with random suffix. Shorter than UUID but collision-resistant.

### Option C: Tasker Built-in Variables

```javascript
// %TIMES = seconds since epoch (Tasker built-in)
// %TIMEMS = milliseconds since epoch (Tasker built-in)
var nonce = timems + '-' + Math.floor(Math.random() * 1000000);
```

**Recommendation**: Use **Option A (Java UUID)** — standard format, guaranteed uniqueness, server can validate format.

---

## 7. Surveillance Profile: App Usage Tracking

### Method 1: App Changed Event (Tasker 5.8+) — Recommended

**Source**: [Tasker 5.8 changelog](https://tasker.joaoapps.com/changes/changes5.8.html), [App Info action docs](https://tasker.joaoapps.com/userguide/en/help/ah_app_info.html)

```xml
<!-- Profile: App Usage Tracker -->
<Profile>
    <nme>Guinevere App Usage Tracker</nme>
    <Event>
        <!-- App Changed event (code 20871 in Tasker 5.8+) -->
        <code>20871</code>
        <pri>0</pri>
    </Event>
    <!-- Entry Task: Record App Start -->
    <mid0>100</mid0>
    <!-- Exit Task: Record App End -->
    <mid1>101</mid1>
</Profile>
```

**Entry Task actions:**

```
A1: Variable Set → %app_start_time = %TIMES
A2: Variable Set → %app_start_name = %appname
A3: Variable Set → %app_start_package = %appdata(0)
```

**Exit Task actions (when app loses focus):**

```
A1: Variable Set → %app_end_time = %TIMES
A2: Variable Set → %app_duration = %app_end_time - %app_start_time
A3: JavaScriptlet → (sign + POST to Guinevere API)
```

**Available variables from App Changed event:**
- `%appname` — Display name of the app
- `%appclass` — Activity class name
- `%appdata(0)` — Package name
- `%appdata(1)` — App label/name

### Method 2: Application Context + Per-App Profiles

```xml
<!-- Per-app context: activates while app is foreground -->
<Profile>
    <nme>Guinevere Track Chrome</nme>
    <App>
        <cls0>com.android.chrome</cls0>
        <fg>true</fg>  <!-- foreground only -->
    </App>
    <mid0>200</mid0>  <!-- entry: record start -->
    <mid1>201</mid1>  <!-- exit: calculate duration + POST -->
</Profile>
```

### Method 3: App Info Action (Usage Stats)

```javascript
// Tasker App Info action with:
// Input: most(time,1440:0,10) → last 24h, top 10 apps by time
// With "Get All Details" checked
// Output variables: %app_name(), %app_usage_time(), %app_package()
```

**Source**: [App Info docs](https://tasker.joaoapps.com/userguide/en/help/ah_app_info.html) — `most(time,X:Y,Z)` where X=minutes lookback start, Y=minutes lookback end, Z=count.

### Method 4: Logcat-Based Activity Tracking

For granular activity-level tracking within apps, use `Logcat Entry` event with `ActivityTrigger activityPauseTrigger` filter. See [Activity State Changes project](https://github.com/Taskomater/Activity-State-Changes-Tasker-Project) for a complete implementation.

**Battery note**: App Changed event and Application Context use the same monitoring mechanism. [Source](https://tasker.helprace.com/i730-app-info-usage-time-of-an-app): "Both of those use the same amount of battery."

---

## 8. Surveillance Profile: GPS Location / Geofencing

### Method 1: AutoLocation Plugin — Recommended for Geofencing

**Source**: [AutoLocation on joaoapps.com](https://joaoapps.com/autolocation/what-it-is/)

**Geofence entry/exit variables:**
- `%allatitude` — Latitude
- `%allongitude` — Longitude
- `%alaccuracy` — Accuracy in meters
- `%alaltitude` — Altitude
- `%alspeed` — Speed
- `%albearing` — Bearing
- `%altime` — Fix time
- `%alprovider` — Provider used

```xml
<Profile>
    <nme>Guinevere Geofence Home</nme>
    <Event>
        <!-- AutoLocation Geofence Enter -->
        <code>59471</code>
        <Str>
            <nme>Geofence Name</nme>
            <val>Home</val>
        </Str>
        <Str>
            <nme>Status</nme>
            <val>enter</val>
        </Str>
    </Event>
    <mid0>300</mid0>
</Profile>
```

### Method 2: Built-in Location Context

```xml
<Profile>
    <nme>Guinevere Location Zone Work</nme>
    <Loc>
        <lat>-6.2088</lat>        <!-- Jakarta coordinates example -->
        <lon>106.8456</lon>
        <rad>200</rad>             <!-- 200m radius -->
        <gps>true</gps>
        <net>true</net>
    </Loc>
    <mid0>301</mid0>
    <mid1>302</mid1>
</Profile>
```

**Tasker built-in location variables** (always available):
- `%LOC` — Last known location (lat,lon)
- `%GPS` — Last GPS fix
- `%NETLOC` — Last network location
- `%TIMES` — Timestamp (seconds since epoch)

### Method 3: Periodic Location via Time Context

```xml
<Profile>
    <nme>Guinevere Periodic GPS</nme>
    <Time>
        <from>
            <min>15</min>  <!-- every 15 minutes -->
        </from>
        <rep>true</rep>
        <repType>2</repType>  <!-- repeat minutes -->
    </Time>
    <mid0>303</mid0>
</Profile>
```

Entry task: `Get Location` action → then JavaScriptlet to sign+POST.

**Battery ranking** (ascending): Cell Near < Network Location < WiFi Near < GPS Location  
**Source**: [Tasker Power Usage](https://tasker.joaoapps.com/userguide/en/power.html)

---

## 9. Surveillance Profile: Notification Capture

### Method 1: AutoNotification Intercept — Recommended

**Source**: [AutoNotification docs](https://joaoapps.com/autonotification/), [AutoApps Variables](https://joaoapps.com/variables/)

```xml
<Profile>
    <nme>Guinevere Notification Capture</nme>
    <Event>
        <!-- AutoNotification Intercept event -->
        <code>38521</code>
        <Str>
            <nme>Action Type</nme>
            <val>created</val>
        </Str>
        <!-- Optional: filter by app package -->
        <!-- Leave empty to capture ALL notifications -->
    </Event>
    <mid0>400</mid0>
</Profile>
```

**Available variables from AutoNotification Intercept:**

| Variable | Description |
|---|---|
| `%anapp` | App name (display) |
| `%anpackage` | Package name |
| `%antitle` | Notification title |
| `%antext` | Notification body text |
| `%anticker` | Ticker text |
| `%antitlebig` | Expanded title (KitKat+) |
| `%ansubtext` | Subtext |
| `%ansummarytext` | Summary text |
| `%aninfotext` | Info text |
| `%antextlines` | Text lines array |
| `%anbutton1text` | Button 1 label |
| `%anbutton2text` | Button 2 label |
| `%anbutton3text` | Button 3 label |
| `%anpeople` | People list |
| `%antag` | Notification tag |
| `%anid` | Notification ID |
| `%anstatus` | Created or Cancelled |
| `%anwhen` | Show When timestamp |

### Method 2: Built-in Notification Event (Basic)

```xml
<Profile>
    <nme>Guinevere Basic Notification</nme>
    <Event>
        <code>400</code>  <!-- Notification event -->
        <Str>
            <nme>Owner Application</nme>
            <!-- empty = all apps -->
        </Str>
        <Str>
            <nme>Title</nme>
            <!-- empty = all titles -->
        </Str>
    </Event>
    <mid0>401</mid0>
</Profile>
```

Built-in variables: `%NTITLE`, `%NTEXT`, `%NBARICON`, `%NBARSUBTEXT`  
**Limitation**: Built-in Notification event only catches text notifications, not rich notifications. AutoNotification required for full capture.

### Entry Task for Notification Capture

```javascript
// JavaScriptlet: Sign and POST notification data
var notifData = {
    event_type: "notification",
    device_id: global('%DEVID'),
    timestamp: Math.floor(Date.now() / 1000).toString(),
    data: {
        app: anapp,           // from %anapp
        package_name: anpackage,  // from %anpackage
        title: antitle,       // from %antitle
        text: antext,         // from %antext
        ticker: anticker,     // from %anticker
        subtext: ansubtext,   // from %ansubtext
        tag: antag,           // from %antag
        id: anid,             // from %anid
        status: anstatus      // created/cancelled
    }
};
// → proceed to sign and POST (see §4 or §5)
```

---

## 10. Surveillance Profile: Clipboard Monitoring

### Variable Set Event on %CLIP

**Source**: [XDA Clipboard Manager tutorial](https://www.xda-developers.com/make-clipboard-manager-with-tasker-autotools/)

```xml
<Profile>
    <nme>Guinevere Clipboard Capture</nme>
    <Event>
        <!-- Variable Set event -->
        <code>3050</code>
        <Str>
            <nme>Variable</nme>
            <val>%CLIP</val>
        </Str>
        <Str>
            <nme>Value</nme>
            <val>*</val>  <!-- match any value -->
        </Str>
        <Int>
            <nme>User Variables Only</nme>
            <val>0</val>
        </Int>
    </Event>
    <mid0>500</mid0>
</Profile>
```

**Entry Task:**

```
A1: Variable Set → %clip_content = %CLIP
A2: Variable Set → %clip_timestamp = %TIMES
A3: JavaScriptlet → (sign + POST to Guinevere API)
```

```javascript
// JavaScriptlet for clipboard capture
var clipData = {
    event_type: "clipboard",
    device_id: global('%DEVID'),
    timestamp: Math.floor(Date.now() / 1000).toString(),
    data: {
        content: clip_content,   // from %CLIP
        timestamp: clip_timestamp
    }
};
// → sign and POST
```

**Note**: %CLIP is a monitored variable — Tasker automatically tracks clipboard changes when it's used in any context or task.

---

## 11. Error Handling & Retry Logic

### Pattern: Retry with Exponential Backoff

```javascript
// === Retry Logic with Exponential Backoff ===
function postWithRetry(url, headers, body, maxRetries) {
    maxRetries = maxRetries || 3;
    var lastError = '';
    
    for (var attempt = 0; attempt < maxRetries; attempt++) {
        try {
            var http = new XMLHttpRequest();
            http.open('POST', url, false);
            
            // Set all headers
            for (var key in headers) {
                http.setRequestHeader(key, headers[key]);
            }
            
            http.send(body);
            
            if (http.status >= 200 && http.status < 300) {
                setLocal('http_code', http.status.toString());
                setLocal('http_response', http.responseText);
                setLocal('http_error', 'false');
                setLocal('http_attempts', (attempt + 1).toString());
                return true;
            }
            
            // Server error (5xx) — worth retrying
            if (http.status >= 500) {
                lastError = 'Server error: ' + http.status;
            } else {
                // Client error (4xx) — do NOT retry
                setLocal('http_code', http.status.toString());
                setLocal('http_response', http.responseText);
                setLocal('http_error', 'true');
                setLocal('http_error_msg', 'Client error: ' + http.status);
                return false;
            }
        } catch (e) {
            lastError = e.message;
        }
        
        // Exponential backoff: 1s, 2s, 4s
        if (attempt < maxRetries - 1) {
            var delayMs = Math.pow(2, attempt) * 1000;
            // Tasker's tk() for Wait action
            tk.performTask('WaitMs', 0, delayMs.toString());
        }
    }
    
    // All retries exhausted
    setLocal('http_error', 'true');
    setLocal('http_error_msg', 'Max retries exceeded: ' + lastError);
    setLocal('http_attempts', maxRetries.toString());
    return false;
}
```

### Alternative: Tasker-Native Retry with Goto

```
Task: Guinevere POST With Retry
A1: Variable Set → %retry_count = 0
A2: Variable Set → %max_retries = 3

--- Loop Start ---
A3: JavaScriptlet → (sign payload + POST, set %http_error)
A4: If → %http_error eq false
A5:   Stop
A6: End If

A7: Variable Add → %retry_count = 1
A8: If → %retry_count > %max_retries
A9:   Flash → "Guinevere POST failed after %max_retries attempts"
A10:  Stop
A11: End If

A12: Wait → MS: %retry_count * 2000  (exponential-ish)
A13: Goto → A3  (retry)
```

---

## 12. Battery Optimization: Batching vs Real-Time

### Strategy: Event Buffering with Periodic Flush

```javascript
// === Batch Events and Flush Periodically ===

// Append event to local queue (stored as global variable)
function enqueueEvent(eventData) {
    var queue = global('%EVENT_QUEUE') || '[]';
    var events = JSON.parse(queue);
    events.push(eventData);
    setGlobal('%EVENT_QUEUE', JSON.stringify(events));
    setGlobal('%EVENT_COUNT', events.length.toString());
}

// Flush queue — called by periodic profile
function flushQueue() {
    var queue = global('%EVENT_QUEUE') || '[]';
    var events = JSON.parse(queue);
    
    if (events.length === 0) return;
    
    var batch = {
        event_type: "batch",
        device_id: global('%DEVID'),
        timestamp: Math.floor(Date.now() / 1000).toString(),
        events: events,
        count: events.length
    };
    
    // Sign and POST the batch
    var payload = JSON.stringify(batch);
    var signature = hmacSha256(payload, global('%GUINEVERE_SECRET'));
    
    var http = new XMLHttpRequest();
    http.open('POST', global('%GUINEVERE_API_URL') + '/batch', false);
    http.setRequestHeader('Content-Type', 'application/json');
    http.setRequestHeader('X-HMAC', signature);
    http.setRequestHeader('X-Batch-Count', events.length.toString());
    http.send(payload);
    
    if (http.status >= 200 && http.status < 300) {
        // Clear queue on success
        setGlobal('%EVENT_QUEUE', '[]');
        setGlobal('%EVENT_COUNT', '0');
    }
    // On failure, keep queue for next flush attempt
}
```

### Battery Optimization Profile

```xml
<!-- Flush every 15 minutes -->
<Profile>
    <nme>Guinevere Batch Flush</nme>
    <Time>
        <from><min>15</min></from>
        <rep>true</rep>
        <repType>2</repType>
    </Time>
    <!-- Only flush when connected (save battery) -->
    <State>
        <code>160</code>  <!-- WiFi Connected -->
    </State>
    <mid0>600</mid0>  <!-- flush task -->
</Profile>
```

### Recommended Batching Strategy

| Event Type | Real-Time | Batch Interval | Rationale |
|---|---|---|---|
| Geofence enter/exit | ✅ Real-time | — | Low frequency, high importance |
| App usage (app changed) | ❌ Batch | 15 min | High frequency, moderate importance |
| Notification capture | ❌ Batch | 5 min | Very high frequency, moderate importance |
| Clipboard | ❌ Batch | 10 min | Medium frequency, variable importance |
| Battery/charging state | ✅ Real-time | — | Low frequency, high importance |

### Tasker Power Consumption Hierarchy

From [Tasker Power Usage docs](https://tasker.joaoapps.com/userguide/en/power.html), contexts ranked by power consumption (ascending):

```
Other State < Day/Time < Calendar < Cell Near < App < BT Near < Network Location < WiFi Near < GPS < Sensors
```

**Display-off optimization**: Tasker batches all active checks (GPS, Net, WiFi, App) when display is off to minimize wake time.

**Key recommendation**: 
- Use `Display State` context to disable surveillance profiles when screen is off
- Use AutoLocation geofencing (uses Google Fused Provider) instead of raw GPS
- Set `Tasker Settings → Monitor → App Check Method → App Usage Stats` for better battery efficiency

---

## 13. Complete Tasker XML Task Snippet

### Unified "Sign and POST" Task

```xml
<TaskerData sr="" dvi="1" tv="6.3.9">
    <Task sr="task100">
        <id>100</id>
        <nme>Guinevere Sign And POST</nme>
        <pri>100</pri>
        <rty>2</rty>
        <Action sr="act0" ve="7">
            <!-- JavaScriptlet: HMAC sign + POST -->
            <code>547</code>
            <Str sr="arg0" ve="3">
                <!-- The full JavaScriptlet code -->
                <![CDATA[
// === Guinevere HMAC-SHA256 Sign + POST ===

function hmacSha256(message, secret) {
    var mac = javax.crypto.Mac.getInstance("HmacSHA256");
    var secretKeySpec = new javax.crypto.spec.SecretKeySpec(
        new java.lang.String(secret).getBytes("UTF-8"), "HmacSHA256"
    );
    mac.init(secretKeySpec);
    var rawHmac = mac.doFinal(
        new java.lang.String(message).getBytes("UTF-8")
    );
    var hexString = new java.lang.StringBuilder();
    for (var i = 0; i < rawHmac.length; i++) {
        var hex = java.lang.Integer.toHexString(0xff & rawHmac[i]);
        if (hex.length() == 1) hexString.append('0');
        hexString.append(hex);
    }
    return hexString.toString();
}

function postWithRetry(url, signHeaders, body, maxRetries) {
    maxRetries = maxRetries || 3;
    for (var attempt = 0; attempt < maxRetries; attempt++) {
        try {
            // Re-sign on each attempt (fresh timestamp)
            var ts = Math.floor(Date.now() / 1000).toString();
            var nonce = java.util.UUID.randomUUID().toString();
            var signString = ts + nonce + body;
            var sig = hmacSha256(signString, global('%GUINEVERE_SECRET'));

            var http = new XMLHttpRequest();
            http.open('POST', url, false);
            http.setRequestHeader('Content-Type', 'application/json');
            http.setRequestHeader('X-HMAC', sig);
            http.setRequestHeader('X-Nonce', nonce);
            http.setRequestHeader('X-Timestamp', ts);
            http.send(body);

            if (http.status >= 200 && http.status < 300) {
                setLocal('http_code', http.status.toString());
                setLocal('http_response', http.responseText);
                setLocal('http_error', 'false');
                return true;
            }
            if (http.status < 500) {
                // Client error — no retry
                setLocal('http_code', http.status.toString());
                setLocal('http_error', 'true');
                setLocal('http_error_msg', http.responseText);
                return false;
            }
        } catch (e) {
            setLocal('http_error_msg', e.message);
        }
        // Brief wait before retry
        try { 
            java.lang.Thread.sleep(
                Math.pow(2, attempt) * 1000
            ); 
        } catch(e2) {}
    }
    setLocal('http_error', 'true');
    setLocal('http_code', '-1');
    return false;
}

// Build payload from Tasker local variables
var payload = JSON.stringify({
    event_type: event_type,
    device_id: global('%DEVID'),
    timestamp: Math.floor(Date.now() / 1000).toString(),
    data: JSON.parse(payload_json)
});

var apiUrl = global('%GUINEVERE_API_URL');
postWithRetry(apiUrl, {}, payload, 3);
                ]]>
            </Str>
            <Int sr="arg1" val="0"/>
        </Action>
    </Task>
</TaskerData>
```

### Required Global Variables

Set these before any surveillance profiles run:

| Variable | Description | Example |
|---|---|---|
| `%GUINEVERE_API_URL` | API endpoint | `https://api.guinevere.local/v1/events` |
| `%GUINEVERE_SECRET` | HMAC shared secret | (stored securely, never in repo) |
| `%DEVID` | Device identifier | `faiz-phone-01` |
| `%EVENT_QUEUE` | Batch queue (JSON array) | `[]` |
| `%EVENT_COUNT` | Queue length | `0` |

---

## 14. References & Sources

### Official Tasker Documentation
- [HTTP Request Action](https://tasker.joaoapps.com/userguide/en/help/ah_http_request.html)
- [JavaScript Support](https://tasker.joaoapps.com/userguide/en/javascript.html)
- [Variables Reference](https://tasker.joaoapps.com/userguide/en/variables.html)
- [Application Context](https://tasker.joaoapps.com/userguide/en/appcontext.html)
- [Event Index](https://tasker.joaoapps.com/userguide/en/help/eh_index.html)
- [App Info Action](https://tasker.joaoapps.com/userguide/en/help/ah_app_info.html)
- [Power Usage](https://tasker.joaoapps.com/userguide/en/power.html)
- [Tasker 5.8 Changelog](https://tasker.joaoapps.com/changes/changes5.8.html)

### Plugins (joaoapps.com)
- [AutoLocation](https://joaoapps.com/autolocation/what-it-is/) — Geofencing + Activity Detection
- [AutoNotification](https://joaoapps.com/autonotification/) — Notification Intercept + Creation
- [AutoApps Variables Reference](https://joaoapps.com/variables/) — All plugin variable lists

### GitHub Repositories
- [StephenGregory/TaskerJavaScriptHelpers](https://github.com/StephenGregory/TaskerJavaScriptHelpers) — JavaScript sandbox for Tasker
- [Taskomater/Tasker-XML-Info](https://github.com/Taskomater/Tasker-XML-Info) — XML structure documentation
- [Taskomater/Activity-State-Changes-Tasker-Project](https://github.com/Taskomater/Activity-State-Changes-Tasker-Project) — Activity tracking via logcat

### Community Patterns
- [Habitica + Tasker integration](https://habitica.fandom.com/wiki/User_blog:LadyAlys/Android%27s_Tasker_app_and_HabitRPG%27s_API) — XMLHttpRequest with custom headers
- [Home Assistant + Tasker](https://flemmingss.com/how-to-use-tasker-with-home-assistant/) — JavaScriptlet HTTP POST pattern
- [XDA Clipboard Manager](https://www.xda-developers.com/make-clipboard-manager-with-tasker-autotools/) — %CLIP monitoring pattern

### CryptoJS References
- [CryptoJS Documentation](https://cryptojs.gitbook.io/docs)
- [AWS SigV4 signing with CryptoJS](https://github.com/aws-samples/aws-iot-examples/blob/master/deviceSimulator/mqtt-lib.js)
- [Postman HMAC pre-request script](https://gist.github.com/asoorm/637be0b463a7a313a1ea01de20ebf8c9)

---

## Appendix: Decision Matrix

| Factor | JavaScriptlet + Java Bridge | JavaScriptlet + CryptoJS | Native HTTP Request |
|---|---|---|---|
| **Dependencies** | None (uses javax.crypto) | CryptoJS bundle (~15KB) | None |
| **Code size** | Medium (~40 lines) | Small (~15 lines + bundle) | Smallest (split across 2 actions) |
| **Maintainability** | Good (standard Java crypto) | Good (well-documented lib) | Good (UI-driven) |
| **Flexibility** | Full control | Full control | Limited to pre-computed values |
| **Tasker version** | Any with JS support | Any with JS support | 5.8+ |
| **Performance** | Fast (native Java) | Moderate (JS crypto) | Fast (native HTTP) |
| **Recommended for Guinevere** | ✅ Primary | ✅ Fallback | ⚠️ Secondary only |
