# P7-014: Tasker Location Profile

## Overview

This document describes the Tasker location profile for Guinevere surveillance. The profile captures GPS coordinates on a periodic interval and monitors geofencing entry/exit events. Location data is packaged into HMAC-signed HTTP requests and submitted to the Guinevere surveillance ingestion API.

Two sub-profiles operate under this step:

1. **Periodic GPS polling.** Captures latitude, longitude, accuracy, and altitude at a configurable interval (default 15 minutes).
2. **Geofence monitoring.** Detects entry into and exit from named geographic zones, reporting the zone name and timing data.

Both sub-profiles share the same event type (`location`) and follow the same signing and submission flow described in P7-017.

## Prerequisites

Before setting up the location profile, complete the base Tasker configuration from the **P7-012 setup guide**. That guide covers global variable setup (`%API_URL`, `%HMAC_SECRET`, `%DEVICE_ID`), permission grants, and battery optimization exemptions.

Additional requirements specific to the location profile:

| Requirement | Detail |
|---|---|
| Tasker version | 5.8 or later |
| GPS | Enabled on device (Settings > Location > ON) |
| Location permission | "Allow all the time" for Tasker (required for background GPS and geofencing) |
| HMAC configuration | Completed per P7-012, with `%HMAC_SECRET` populated |
| Network connectivity | Mobile data or Wi-Fi for HTTP submission |

The location permission must be set to "Allow all the time" rather than "Allow only while using the app." Without this, Android stops GPS polling when Tasker moves to the background.

## GPS Profile Setup

### Trigger Configuration

The GPS polling profile uses Tasker's built-in **Time** context combined with a **Get Location** action. This approach gives more predictable timing than the Location context alone, which depends on system location updates.

1. Create a new profile in Tasker
2. Context: **Time** > set repeating interval to 15 minutes
3. Name the profile: `Guinevere GPS Poll`

### Task Actions

The task performs three steps in sequence:

1. **Get Location.** Add a **Get Location** action (Location category). Configure:
   - Source: GPS (with network fallback)
   - Timeout: 60 seconds
   - This populates Tasker built-in variables: `%LOC` (lat,lng), `%LOCACC` (accuracy in meters), `%LOCALT` (altitude in meters)

2. **Build payload and sign.** Add a **JavaScriptlet** action that calls the HMAC signing code from P7-017. The JavaScriptlet:
   - Parses `%LOC` into latitude and longitude
   - Reads `%LOCACC` for accuracy
   - Reads `%LOCALT` for altitude (may be unset if GPS cannot determine altitude)
   - Calls `buildEventPayload("location", deviceId, payload)` to construct the JSON body
   - Computes HMAC-SHA256 and sets `%hmac_signature`, `%hmac_timestamp`, `%hmac_nonce`

3. **HTTP Request.** Add an **HTTP Request** action:
   - Method: POST
   - URL: `%API_URL/surveillance/events`
   - Content Type: `application/json`
   - Body: `%hmac_body`
   - Headers: `X-Signature:%hmac_signature`, `X-Timestamp:%hmac_timestamp`, `X-Nonce:%hmac_nonce`

### Polling Interval

The default interval is 15 minutes. This value balances location freshness against battery consumption. To adjust:

1. Open the `Guinevere GPS Poll` profile
2. Edit the Time context
3. Change the repeat interval to the desired number of minutes
4. Shorter intervals (5 minutes or less) increase battery drain significantly
5. Longer intervals (30+ minutes) reduce location granularity

### Error Handling

If GPS fails to acquire a fix within the timeout:

- `%LOC` remains empty or contains the last known location
- The JavaScriptlet should check for empty `%LOC` and skip submission if no valid coordinates exist
- Set a local variable `%location_error` to `"no_fix"` for debugging in Tasker's Run Log

## Geofencing Profile Setup

### Trigger Configuration

The geofence profile uses Tasker's **Location** context with a defined geographic zone. Tasker monitors entry and exit events for the zone using a combination of GPS and network location.

1. Create a new profile in Tasker
2. Context: **Location** > **New named zone**
3. Configure the zone:
   - Name: a descriptive label (e.g., `home`, `office`, `gym`)
   - Center coordinates: set the latitude and longitude for the zone center
   - Radius: set the trigger radius in meters (recommended 100 to 200 meters)
4. Create two profiles per zone: one for **Enter** and one for **Exit**

### Entry Task

When the device enters a geofence zone:

1. **Capture event data.** Add a **JavaScriptlet** action that:
   - Reads the zone name from `%PACTIVE` or a hardcoded zone identifier
   - Records the entry timestamp in ISO 8601 format
   - Sets the `geofence` field in the payload with `action: "enter"` and `zone_name`
   - Calls the HMAC signing code from P7-017

2. **Submit event.** Add an **HTTP Request** action with the same configuration as the GPS profile.

### Exit Task

When the device exits a geofence zone:

1. **Capture event data.** Add a **JavaScriptlet** action that:
   - Reads the zone name
   - Calculates duration inside the zone (if entry timestamp was stored in a Tasker variable)
   - Sets the `geofence` field with `action: "exit"`, `zone_name`, and `duration_seconds`
   - Calls the HMAC signing code from P7-017

2. **Submit event.** Add an **HTTP Request** action with the same configuration as the GPS profile.

### Multiple Zones

To monitor multiple zones, create separate profile pairs (Enter + Exit) for each zone. Each zone needs its own named zone definition in Tasker. Store zone entry timestamps in separate Tasker variables (e.g., `%ZONE_HOME_ENTRY_TIME`, `%ZONE_OFFICE_ENTRY_TIME`) to track duration correctly.

## Event Format

### GPS Polling Payload

```json
{
  "event_type": "location",
  "device_id": "%DEVICE_ID",
  "occurred_at": "2026-01-01T12:00:00Z",
  "payload": {
    "latitude": 0.0,
    "longitude": 0.0,
    "accuracy_meters": 10,
    "altitude_meters": null,
    "geofence": null
  }
}
```

Field descriptions:

| Field | Type | Description |
|---|---|---|
| `event_type` | string | Always `"location"` for this profile |
| `device_id` | string | Device identifier from `%DEVICE_ID` |
| `occurred_at` | string | ISO 8601 timestamp of the GPS fix |
| `payload.latitude` | number | Latitude in decimal degrees (placeholder: 0.0) |
| `payload.longitude` | number | Longitude in decimal degrees (placeholder: 0.0) |
| `payload.accuracy_meters` | number | GPS accuracy estimate in meters |
| `payload.altitude_meters` | number or null | Altitude in meters above sea level, or null if unavailable |
| `payload.geofence` | object or null | Null for periodic GPS polls |

### Geofence Entry Payload

```json
{
  "event_type": "location",
  "device_id": "%DEVICE_ID",
  "occurred_at": "2026-01-01T08:30:00Z",
  "payload": {
    "latitude": 0.0,
    "longitude": 0.0,
    "accuracy_meters": 50,
    "altitude_meters": null,
    "geofence": {
      "action": "enter",
      "zone_name": "office"
    }
  }
}
```

### Geofence Exit Payload

```json
{
  "event_type": "location",
  "device_id": "%DEVICE_ID",
  "occurred_at": "2026-01-01T17:45:00Z",
  "payload": {
    "latitude": 0.0,
    "longitude": 0.0,
    "accuracy_meters": 50,
    "altitude_meters": null,
    "geofence": {
      "action": "exit",
      "zone_name": "office",
      "duration_seconds": 33300
    }
  }
}
```

### Geofence Field Descriptions

| Field | Type | Description |
|---|---|---|
| `payload.geofence.action` | string | `"enter"` or `"exit"` |
| `payload.geofence.zone_name` | string | Name of the geofence zone |
| `payload.geofence.duration_seconds` | number | Time spent inside the zone (exit events only) |

## HMAC Signing

All location events are signed using the HMAC-SHA256 JavaScriptlet described in **P7-017**. The signing process:

1. Build the JSON payload using `buildEventPayload("location", deviceId, payload)`
2. Compute HMAC-SHA256 over the signing string `POST:/surveillance/events:{timestamp}:{nonce}:{body}`
3. Set `%hmac_signature`, `%hmac_timestamp`, `%hmac_nonce` for the HTTP Request action

The server validates every incoming signature. Requests with missing, expired, or invalid signatures are rejected with HTTP 401.

See `docs/setup-evidence/P7/STEP-P7-017/tasker-hmac-jslet.md` for the full JavaScriptlet implementation and testing instructions.

## Consent

Location data collection requires active consent for the scope `surveillance.location`.

### Consent Enforcement

The Guinevere API checks the consent ledger on every incoming event. If `surveillance.location` is not active:

- The API returns HTTP 403 (Forbidden)
- The event is not stored or processed

### Client-Side Consent Check (Optional)

To avoid sending events that will be rejected, you can configure Tasker to check consent state before submission:

1. Create a periodic task that queries the consent status endpoint
2. Store the result in `%CONSENT_LOCATION` (true/false)
3. Add an If condition to both the GPS and geofence tasks: only execute the HTTP Request action when `%CONSENT_LOCATION` equals `true`

This client-side check is optional. The server always enforces consent regardless of client behavior.

### Consent Revocation

When consent for `surveillance.location` is revoked:

- The API immediately stops accepting location events
- Tasker profiles continue running but receive HTTP 403 responses
- No location data is stored during the revocation period
- Re-granting consent resumes data acceptance immediately

## Battery Optimization

Location tracking is one of the most battery-intensive surveillance profiles. Apply these optimizations:

### GPS vs. Network Location

| Mode | Accuracy | Battery Impact | Use When |
|---|---|---|---|
| GPS only | High (5 to 15 meters) | High | Outdoor accuracy critical |
| Network location | Medium (50 to 500 meters) | Low | Indoor, battery saving |
| GPS + Network | High with fallback | Medium | Recommended default |

Configure the **Get Location** action source to "Any" (GPS + network) for balanced behavior. Tasker uses GPS when available and falls back to network location when GPS cannot acquire a fix (e.g., indoors).

### Nighttime Polling Reduction

To reduce battery drain during sleeping hours:

1. Add a Time context condition to the GPS polling profile
2. Set active hours (e.g., 06:00 to 23:00)
3. GPS polling stops outside this window
4. Geofence profiles remain active since they use lower-power passive monitoring

### Adaptive Polling

Consider reducing the polling interval when the device is stationary:

1. Add a condition that checks the device's movement state (via accelerometer or activity recognition)
2. If stationary for more than 30 minutes, increase the polling interval to 60 minutes
3. Resume 15-minute polling when movement is detected

This approach requires Tasker's **AutoTools** plugin or Android's built-in activity recognition API.

## Privacy

GPS location data is classified as **Confidential** under the Guinevere Data Governance and Classification Policy. This classification imposes the following requirements:

### Data Handling Rules

| Rule | Detail |
|---|---|
| Encryption in transit | TLS mandatory (HTTPS only) |
| Encryption at rest | Encrypted storage in TimescaleDB |
| Access control | RBAC restricted to authorized roles |
| Retention | Subject to data retention policy schedule |
| Audit logging | All access to location data is logged |
| No plaintext in logs | GPS coordinates must not appear in application logs |

### Artifact Restrictions

- **No real coordinates in documentation.** This document uses placeholder values (0.0) for all latitude and longitude fields.
- **No coordinates in exported Tasker backups.** Scrub location data from any Tasker profile exports before sharing.
- **No coordinates in version control.** Never commit files containing real GPS coordinates.
- **No coordinates in test fixtures.** Use synthetic coordinates for testing.

### Surveillance Boundary

Location collection operates within the consent boundaries defined by the operator. The Guinevere system does not:

- Track location without explicit consent
- Share location data with third parties
- Store location data beyond the configured retention period
- Expose location data through unauthorized API endpoints

## Troubleshooting

### GPS Not Acquiring Fix

| Symptom | Cause | Fix |
|---|---|---|
| `%LOC` is empty after Get Location | GPS disabled or no satellite visibility | Enable GPS in device settings. Move outdoors for initial fix. |
| Get Location times out | Weak GPS signal | Increase timeout to 120 seconds. Ensure clear sky view. |
| Location shows last known position | GPS stale cache | Toggle GPS off and on. Wait for fresh fix. |

### Permission Issues

| Symptom | Cause | Fix |
|---|---|---|
| Profile runs but no location data | Location permission set to "While using app" | Change to "Allow all the time" in Settings > Apps > Tasker > Permissions > Location |
| Geofence not triggering | Background location restricted | Same fix as above. Also check Settings > Location > App permissions > Tasker |
| Permission revoked after reboot | Custom ROM aggressive permission management | Re-grant permission. Consider using a device without aggressive permission revocation. |

### Battery Optimization Interference

| Symptom | Cause | Fix |
|---|---|---|
| GPS polling stops after screen off | Android battery optimization | Disable battery optimization for Tasker (Settings > Apps > Tasker > Battery > Unrestricted) |
| Geofence events delayed or missed | Doze mode | Disable battery optimization. On Samsung/Xiaomi/Huawei, follow dontkillmyapp.com for device-specific steps |
| Polling interval inconsistent | Adaptive battery | Disable adaptive battery for Tasker in Settings > Battery > Adaptive battery |

### Indoor Accuracy

GPS signals are weak indoors. When the device is inside a building:

- Accuracy values may exceed 100 meters
- Altitude readings are unreliable or unavailable
- Network location provides better indoor results than GPS alone

The **Get Location** action with source set to "Any" automatically uses network location as a fallback. Check `%LOCACC` to assess the quality of each fix. Fixes with accuracy worse than 500 meters may indicate network-only location with poor cell tower triangulation.

### Geofence False Triggers

| Symptom | Cause | Fix |
|---|---|---|
| Enter/exit fires repeatedly at zone boundary | Device oscillating near zone edge | Increase zone radius to 200+ meters. Add a cooldown timer (minimum 5 minutes between events for the same zone). |
| Zone enter fires but exit never fires | Exit detection range too small | Increase zone radius. Ensure location permission is set to "Allow all the time." |
| No geofence events at all | Location permission or battery optimization | Check permissions and battery settings per the tables above. |

### HTTP Submission Failures

| Symptom | Cause | Fix |
|---|---|---|
| HTTP 401 | Invalid HMAC signature | Verify `%HMAC_SECRET` is correct. See P7-017 troubleshooting. |
| HTTP 403 | Consent not active for `surveillance.location` | Grant consent via Discord command or consent API. |
| HTTP 400 | Malformed JSON | Verify the JavaScriptlet output. Check for unescaped characters in zone names. |
| Connection timeout | Network unavailable or wrong URL | Verify `%API_URL`. Check device network connectivity. |

## References

| Document | Path |
|---|---|
| Tasker Setup Guide (P7-012) | `docs/setup-evidence/P7/STEP-P7-012/tasker-setup-guide.md` |
| HMAC JavaScriptlet (P7-017) | `docs/setup-evidence/P7/STEP-P7-017/tasker-hmac-jslet.md` |
| Surveillance Data Policy | `docs/30-data/SurveillanceDataPolicy.md` |
| Consent Revocation Policy | `docs/30-data/ConsentRevocationPolicy.md` |
| Data Governance and Classification | `docs/30-data/DataGovernance.md` |
| Security Policy | `docs/20-security/SecurityPolicy.md` |
| Persona Safety Policy | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` |

---

## Footer

| Field | Value |
|---|---|
| **Step** | STEP-P7-014 |
| **Date** | 2026-06-03 |
| **Author** | Guinevere (autonomous engineering agent) |
| **Scope** | Documentation: Tasker location profile for GPS polling and geofencing |
| **Dependencies** | P7-012 (Tasker setup), P7-017 (HMAC signing) |
| **Evidence path** | `docs/setup-evidence/P7/STEP-P7-014/tasker-location.md` |
