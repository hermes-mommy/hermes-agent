# Mi Fitness Cloud API Research

Date: 2026-06-18
Scope: Xiaomi Mi Fitness / Zepp Life cloud API for health-data extraction in Python.

## Executive summary

For 2024–2026, the most practical options are **unofficial** and split into two families:

1. **Mi Fitness / Xiaomi Health cloud via Xiaomi account cookies** (`userId` + `passToken`) — best fit for newer Xiaomi wearable cloud sync.
2. **Zepp Life / Huami cloud session** (`apptoken`) — still useful for older / Huami-era flows and some Amazfit devices.

The strongest recent evidence points to **Mi Fitness cloud being enough for daily activity, steps, distance, active calories, heart rate, and body measurements**, while **sleep and workouts are not yet consistently confirmed** in current Xiaomi cloud implementations.

For a production pipeline, the safest recommendation is:
- **Primary**: `mi-fitness-mcp` for Xiaomi Mi Fitness cloud.
- **Fallback / compatibility**: `zepp-life-mcp` if the device/account is still on the older Zepp Life / Huami flow.
- **Token helper**: `huami-token` only for watch pairing/BLE keys, not for health metrics extraction.

---

## 1) Library comparison

| Library / project | Language | Auth flow | Data scope | Best use | Reliability notes |
|---|---|---|---|---|---|
| `kubulashvili/mi-fitness-mcp` | Python | Xiaomi account cookies: `userId` + `passToken` | Confirmed: daily activity, steps, distance, active calories, heart rate, body measurements; sleep/workouts not yet confirmed | Xiaomi Mi Fitness cloud extraction | Explicitly says cloud endpoint coverage is still being confirmed; region-sensitive (`ru` usually) |
| `kubulashvili/zepp-life-mcp` | Python | `apptoken` + `userId` | Steps, sleep, heart rate, workouts, body measurements; export-file mode also supported | Zepp Life / older Huami accounts | README warns cloud coverage varies by account/region/upstream endpoint stability; export mode is safest |
| `argrento/huami-token` | Python | Xiaomi or Amazfit login to get pairing/BLE keys | Bluetooth pairing keys and AGPS downloads, not health metrics | Device pairing / Gadgetbridge use | Useful for pairing keys; not for health extraction |
| `mi-fitness` (PyPI) | Python SDK | Token-based; family-sharing and cloud access | Heart rate, sleep, steps, calories, valid stand, intensity, SpO2, weight, blood pressure, latest snapshots, aggregated history | Health data API wrapper | Warns endpoints can change; exposes explicit token-expiry and captcha/device-untrusted errors |
| `Mi-Fitness-Sync` | Python CLI | Persisted auth state; Xiaomi login flow | Workout activities and exports (GPX/TCX/FIT) | Workout export / Strava sync | Notes endpoint/cookie/signature changes may break it; some captcha/approval flows are not automated |

### Recommendation
If you want the **broadest current Xiaomi Mi Fitness cloud coverage**, start with **`mi-fitness-mcp` + `mi-fitness` SDK exploration**. If your current devices/accounts are still on Huami/Zepp Life, keep **`zepp-life-mcp`** as a compatibility fallback.

---

## 2) Auth flow diagram

### Mi Fitness / Xiaomi cloud

```text
Xiaomi account login page
  -> browser devtools cookies
  -> extract userId + passToken
  -> configure mi-fitness-mcp / client
  -> authenticated cloud requests to Mi Fitness endpoints
```

### Zepp Life / Huami cloud

```text
Zepp Life login page
  -> browser devtools cookie inspection
  -> extract apptoken (+ userId)
  -> configure zepp-life-mcp / client
  -> authenticated cloud requests to Zepp endpoints
```

### `mi-fitness` SDK-style flow

```text
Login / token acquisition
  -> token refresh handled by client
  -> read latest snapshot or aggregated data
  -> APIError / TokenExpiredError / CaptchaRequiredError on failure
```

### Observations
- Recent Xiaomi/Mi Fitness tooling does **not** present as OAuth2 in the usual public-developer sense.
- The practical auth surface is **cookies / session tokens**, not a formal public OAuth client registration.
- For some helper tools, a saved auth state or keyring-stored token is used.

---

## 3) Endpoint catalog

### Historical / daily summary endpoint from legacy Mi Fit / Huami flow

Evidence from older reverse-engineering and still-useful as a reference pattern:

- `POST https://account.huami.com/v2/client/login`
- `GET https://api-mifit.huami.com/v1/data/band_data.json`

The historical summary endpoint is queried with:
- `query_type=summary`
- `device_type=android_phone`
- `userid=<user_id>`
- `from_date=YYYY-MM-DD`
- `to_date=YYYY-MM-DD`
- header `apptoken: <app_token>`

Response shape:
- JSON object with `data[]`
- each item contains `date_time`
- each day’s `summary` is Base64-encoded JSON with keys like `stp` and `slp`

### Current Xiaomi Mi Fitness cloud usage

Current public Python tooling does not consistently publish all endpoint URLs in README, but it confirms the auth pattern and cloud data classes.
The active project currently confirms these Xiaomi cloud-backed data categories:
- daily activity
- steps
- distance
- active calories
- heart rate
- body measurements

### Zepp Life cloud session

`zepp-life-mcp` documents cloud-session auth with `apptoken`, but does not expose all endpoint URLs in README. It confirms the current cloud path is session-token based and region sensitive.

### Practical note
For Xiaomi cloud, endpoint URLs appear to be **private, reverse-engineered, and region-specific**. Expect host variation and drift.

---

## 4) Data availability matrix

Legend: **Confirmed** = explicitly supported/mentioned in current 2024–2026 tooling; **Likely** = older/compatible tooling supports it; **Not confirmed** = current Xiaomi cloud tooling says it is not yet confirmed.

| Metric | Mi Fitness cloud (`mi-fitness-mcp`) | Zepp Life cloud (`zepp-life-mcp`) | `mi-fitness` SDK | Notes |
|---|---|---|---|---|
| Steps | Confirmed | Confirmed | Confirmed | Core metric in all tools |
| Daily activity / distance / active calories | Confirmed | Confirmed | Confirmed (calories/intensity family) | Mi Fitness MCP explicitly confirms these |
| Heart rate | Confirmed | Confirmed | Confirmed | Includes resting/latest snapshots in SDK |
| Sleep | Not yet confirmed | Confirmed | Confirmed | Current Xiaomi cloud tool says sleep is not yet confirmed |
| Workouts | Not yet confirmed | Confirmed | Likely via activity/workout-related APIs | Xiaomi cloud tool says not yet confirmed |
| SpO2 / blood oxygen | Not confirmed in current Xiaomi cloud README | Not explicit in README | Confirmed | SDK exposes `get_spo2_history` and latest SpO2 |
| Stress | Not confirmed | Not explicit in README | Not explicit in README | Seen in older scripts (InfluxDB exporter), but not well-confirmed in current Xiaomi cloud tooling |
| HRV | Not confirmed | Not explicit in README | Not explicit in README | No strong current evidence in the reviewed tooling |
| Body battery / PAI | Not confirmed | Older tooling may expose PAI | Not explicit in README | Older `zepp_to_influxdb` script mentions PAI; not confirmed in current Xiaomi cloud tooling |
| Weight / body measurements | Confirmed | Confirmed | Confirmed | Xiaomi cloud tool explicitly confirms body measurements |
| Blood pressure | Not confirmed | SDK supports history | Confirmed | Appears in `mi-fitness` SDK, not in current Mi Fitness MCP README |
| Valid stand / intensity | Not confirmed | SDK supports history | Confirmed | More available in SDK than in current Xiaomi cloud README |

---

## 5) Auth and token behavior

### Mi Fitness / Xiaomi
- Most current tooling uses **`userId` + `passToken`** copied from Xiaomi account cookies.
- Region is important; one current project says **`ru` is usually required**.
- The auth state is typically stored locally or in the system keyring.
- No evidence of a public OAuth2 developer flow for health data access.

### Zepp Life / Huami
- Uses **`apptoken`** from the Zepp Life session cookie, plus `userId`.
- `apptoken` is treated as a session token, not a developer API key.
- Some tools store it in the keyring or local state.

### Token lifecycle
From the `mi-fitness` SDK package:
- `TokenExpiredError` exists when token refresh fails.
- `AuthError` covers login problems.
- `CaptchaRequiredError` / `DeviceUntrustedError` indicate anti-abuse gates and SMS/captcha friction.

This strongly suggests the ecosystem is **fragile but token-refresh-aware**, rather than a stable long-lived public API.

---

## 6) Rate limits and abuse controls

I did **not** find a published official Mi Fitness rate-limit document.
What I did find:

- `zepp_to_influxdb` explicitly says the Zepp API has **strict rate limits on the login endpoint**, and recommends bypassing login with pre-extracted `app_token` + `user_id`.
- A Xiaomi cloud token extractor notes **2FA request limits of 3/5 per day depending on region**.
- The `mi-fitness` SDK includes `CaptchaRequiredError` and `DeviceUntrustedError`, implying anti-abuse gating.
- Recent Mi Fitness tooling recommends saving session tokens and avoiding repeated interactive login.

### Practical conclusion
Assume:
- **login is rate-limited** and may trigger captcha/approval
- repeated auth attempts are risky
- production pipelines should use **persisted tokens** and minimize interactive login calls

---

## 7) Reliability assessment

### What looks reliable
- **Daily activity / steps / heart rate / body measurements** are currently the most consistently confirmed Xiaomi cloud metrics.
- The newer `mi-fitness` SDK is feature-rich and explicitly models error states.
- `mi-fitness-mcp` is recent and directly targets Xiaomi cloud with a simple token-based setup.

### What looks fragile
- Cloud endpoints are unofficial, reverse-engineered, and region sensitive.
- README warnings repeatedly mention endpoint/cookie/signature/response-format changes.
- Sleep and workouts are not yet confirmed in current Xiaomi cloud tooling, even though older Zepp/Huami tooling can access them.
- Some metrics may exist in the ecosystem but be unavailable on specific accounts, devices, or regions.

### Ban / breakage risk
- I found no definitive 2024–2026 report of account bans in the reviewed sources, but multiple projects warn of **captcha, approval, or temporary lockouts**.
- The practical risk is less “formal ban” and more **unstable auth + endpoint drift**.

---

## 8) Mi Fitness vs Zepp Life

| Aspect | Mi Fitness | Zepp Life |
|---|---|---|
| Brand / app | Newer Xiaomi wearable app | Older Huami / Amazfit app |
| Typical auth | `userId` + `passToken` | `apptoken` + `userId` |
| Current tooling maturity | Better for Xiaomi cloud-only extraction | Better documented for older cloud/session flows |
| Coverage confidence | Strong for activity, heart rate, body measurements | Strong for steps, sleep, workouts, body measurements |
| Migration impact | Better match for newer Xiaomi wearables | Better match for legacy Amazfit / Huami accounts |

### Bottom line
For Xiaomi-branded wearables already syncing to **Mi Fitness**, use Mi Fitness cloud as primary. For older devices/accounts that still land in **Zepp Life**, Zepp Life tooling remains important.

---

## 9) Data freshness

I did not find a hard SLA for cloud freshness.
Best available evidence suggests:
- data appears **after phone sync uploads to cloud**, but timing varies by account, region, and upstream stability
- `mi-fitness-mcp` suggests querying recent dates and notes that data may not appear if it does not exist in cloud yet
- `Mi-Fitness-Sync` confirms workouts show in Mi Fitness cloud after Bluetooth sync and upload, but third-party integration lag can occur

### Practical expectation
Treat freshness as **minutes to hours after sync**, not real-time streaming. For production, poll with backoff and re-check recent windows.

---

## 10) Recommended approach for Guinevere

### Primary stack
1. **Use `mi-fitness-mcp` as the initial Xiaomi Mi Fitness cloud connector**.
2. Validate `userId` + `passToken` region handling in your target accounts.
3. Add a fallback path for Zepp Life / Huami if some accounts are still on the older ecosystem.
4. For broader metric coverage, evaluate the `mi-fitness` SDK as an extraction layer because it exposes more metrics and structured errors.

### Suggested architecture
- **Cloud sync worker**: token-based polling against Xiaomi cloud
- **Local normalization layer**: map source metrics to your health schema
- **Retry/backoff**: exponential backoff for auth failures / rate-limit-like responses
- **Metrics coverage fallback**: if Mi Fitness cloud lacks sleep/workout on an account, detect and route to Zepp Life or local export alternatives

### Recommendation summary
- **Best current choice for Xiaomi cloud**: `mi-fitness-mcp`
- **Best current choice for richer API surface**: `mi-fitness`
- **Best current compatibility fallback**: `zepp-life-mcp`
- **Best token utility**: `huami-token`

---

## 11) Evidence notes

### Key current sources reviewed
- `kubulashvili/mi-fitness-mcp` README
- `kubulashvili/zepp-life-mcp` README
- `argrento/huami-token` README
- `mi-fitness` PyPI project page
- `kevinkwee/Mi-Fitness-Sync` project description
- legacy reverse-engineering examples for `account.huami.com` / `api-mifit.huami.com`

### Important caveat
The ecosystem is unofficial and changes frequently. Treat every endpoint or field as **probabilistic**, not guaranteed.
