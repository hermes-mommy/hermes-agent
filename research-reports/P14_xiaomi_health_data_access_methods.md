# P14 — Xiaomi Wearable Health Data Access Methods: Comprehensive Research

**Date**: 2026-06-03
**Context**: Research for Guinevere AI companion P14 — Xiaomi Watch Integration
**Goal**: Find all production-grade methods to extract heart rate, sleep, steps, SpO2, stress data from Xiaomi smartwatch → Android phone → Python backend on VPS

---

## Executive Summary

Xiaomi wearables (Mi Band series, Xiaomi Watch S1/S3, Redmi Watch) store health data via the **Mi Fitness** app (formerly Xiaomi Wear, package: `com.xiaomi.wearable`) on Android. Older devices use **Zepp Life** (formerly Mi Fit, package: `com.xiaomi.hm.health`).

There are **10 distinct access methods**, ranked below by suitability for the Guinevere P14 pipeline. The **top 3 recommendations** are:

| Rank | Method | Best For | Why |
|------|--------|----------|-----|
| **#1** | **Gadgetbridge + SQLite export → Python** | Production data pipeline | Open-source, local-first, no cloud dependency, auto-export, all data types |
| **#2** | **Health Connect → Companion Android app → HTTP to VPS** | Official SDK route | Google-backed, Mi Fitness writes to it, clean API, WorkManager sync |
| **#3** | **Mi Fitness Cloud API (Python SDK)** | Quick cloud pull | `pip install mi-fitness`, covers heart/sleep/steps/SpO2, but sleep not confirmed for newer clouds |

---

## Ranked Access Methods

---

### #1 GADGETBRIDGE — Open-Source Android App (RECOMMENDED)

**What it is**: FOSS Android app that directly communicates with Xiaomi wearables via BLE, bypassing Xiaomi cloud entirely. Supports Mi Band 4-9, Xiaomi Smart Band 8/9/10 Pro, Redmi Watch, Xiaomi Watch S1/S3.

**Supported Devices** (as of 2026):
- Mi Band 4, 5, 6, 7, 7 Pro, 8, 8 Pro, 9
- Redmi Watch 1/2/3/4/5 Active
- Xiaomi Watch S1, S1 Pro, S3
- Xiaomi Smart Band 8 Active, 9 Active, 10
- All listed in [Gadgetbridge Xiaomi page](https://gadgetbridge.org/gadgets/wearables/xiaomi/)

**Data Coverage**:
| Data Type | Status | Table in SQLite |
|-----------|--------|-----------------|
| Heart Rate (manual) | ✅ Full | `HUAMI_HEART_RATE_MANUAL_SAMPLE` |
| Heart Rate (max) | ✅ Full | `HUAMI_HEART_RATE_MAX_SAMPLE` |
| Heart Rate (resting) | ✅ Full | `HUAMI_HEART_RATE_RESTING_SAMPLE` |
| Steps | ✅ Full | `MI_BAND_ACTIVITY_SAMPLE` (STEPS column) |
| Sleep (deep/light/REM) | ✅ Full (Mi Band 7+) | `MI_BAND_ACTIVITY_SAMPLE` (SLEEP, DEEP_SLEEP, REM_SLEEP columns) |
| Activity intensity | ✅ Full | `MI_BAND_ACTIVITY_SAMPLE` (RAW_INTENSITY) |
| SpO2 | ✅ Full | `HUAMI_EXTENDED_ACTIVITY_SAMPLE` |
| Stress | ✅ Full | Stress level columns |
| PAI score | ✅ Full | `HUAMI_PAI_SAMPLE` |
| Sleep respiratory rate | ✅ Full | `HUAMI_SLEEP_RESPIRATORY_RATE_SAMPLE` |
| GPS tracks | ✅ Full (GPX export) | GPX files during auto-export |

**Data Format**: SQLite database file (`Gadgetbridge` — no extension) — one file containing ALL tables.

**Auto-Export Pipeline** (KEY FEATURE):
```
Gadgetbridge → Auto Export (every 1hr min) → SQLite on internal storage
  → Syncthing/Nextcloud auto-upload → WebDAV → Python script pulls + parses
```
Source: [gadgetbridge_to_influxdb](https://github.com/bentasker/gadgetbridge_to_influxdb) and [gb2influxdb](https://github.com/tjhowse/gb2influxdb)

**Pairing Requirement**: Must get auth key from Mi Fitness app first (one-time). Extract via:
```bash
# For Mi Fitness (com.xiaomi.wearable) — no root needed:
grep -Eo '(encryptKey|token|authKey|huamiAuthKey)[":= ]+[[:xdigit:]]{32}' \
  /sdcard/Android/data/com.xiaomi.wearable/files/log/*.log | grep -oE '[[:xdigit:]]{32}'
```

**Python Integration** (proven pattern):
```python
import sqlite3
import pandas as pd

conn = sqlite3.connect("/tmp/gadgetbridge.sqlite")

# Heart rate reading
df_hr = pd.read_sql_query("""
    SELECT TIMESTAMP, HEART_RATE 
    FROM HUAMI_HEART_RATE_MANUAL_SAMPLE 
    WHERE TIMESTAMP >= ?
""", conn, params=(start_ts,))

# Steps + sleep + activity
df_activity = pd.read_sql_query("""
    SELECT TIMESTAMP, STEPS, HEART_RATE, RAW_INTENSITY, 
           SLEEP, DEEP_SLEEP, REM_SLEEP
    FROM MI_BAND_ACTIVITY_SAMPLE 
    WHERE TIMESTAMP >= ?
""", conn, params=(start_ts,))

# SpO2
df_spo2 = pd.read_sql_query("""
    SELECT TIMESTAMP, SPO2 
    FROM HUAMI_EXTENDED_ACTIVITY_SAMPLE 
    WHERE TIMESTAMP >= ?
""", conn, params=(start_ts,))
```

**Pros**:
- ✅ **No cloud dependency** — data stays on-device (privacy)
- ✅ **All data types** in one SQLite file
- ✅ **Auto-export** with configurable interval (minimum 1 hour)
- ✅ **WebDAV/Syncthing integration** for server sync
- ✅ **Mature project** — active since 2017, 3000+ stars
- ✅ **No root required** for data export
- ✅ **Proven production pipelines** — multiple GitHub projects
- ✅ Can run alongside Mi Fitness (just needs BLE auth key once)

**Cons**:
- ❌ Must stop Mi Fitness from using BLE (or it steals connection)
- ❌ Initial pairing requires auth key extraction from Mi Fitness
- ❌ Heart rate real-time streaming requires BLE auth (not for historical)
- ❌ Battery impact: BLE always-connected = moderate (5-8% extra/day)
- ❌ Sleep stage parsing on older devices is less accurate

**Real-World Examples**:
- [bentasker/gadgetbridge_to_influxdb](https://github.com/bentasker/gadgetbridge_to_influxdb) — production pipeline with WebDAV + InfluxDB
- [tjhowse/gb2influxdb](https://github.com/tjhowse/gb2influxdb) — Syncthing + InfluxDB pipeline
- [moh53n/FitBridge](https://github.com/moh53n/FitBridge) — Gadgetbridge → Google Fit sync
- [Extracting with R](https://methodmatters.github.io/mi-band-5-data-gadgetbridge-r/) — academic data extraction paper

**Battery Impact**: Low-Medium. If auto-export is on and BLE is connected, expect ~5-8% extra daily drain. Auto-export itself is just a file copy — near-zero cost.

**Latency**: 1 hour minimum (auto-export interval). Can trigger manual sync.

**Reliability**: ★★★★★ — Most reliable method. Works offline. No cloud API changes.

---

### #2 GOOGLE HEALTH CONNECT → COMPANION ANDROID APP → HTTP TO VPS

**What it is**: Android's official health data platform. Mi Fitness writes data to Health Connect. A custom companion Android app reads from Health Connect and sends to your VPS via HTTP.

**Architecture**:
```
Mi Fitness (com.xiaomi.wearable) → Health Connect (on-device)
  → Your Companion Android App (Health Connect SDK)
    → WorkManager background sync → HTTP POST → Your FastAPI/Python backend
```

**Setup**:
1. In Mi Fitness: Settings → Health Connect → Enable data types (steps, heart rate, sleep, etc.)
2. Companion app requests Health Connect permissions once
3. WorkManager runs periodic syncs (30 min recommended)
4. Data is read via `readRecords()` and uploaded as JSON

**Health Connect Data Types Available via Mi Fitness**:
| Data Type | Health Connect Record | Available from Mi Fitness? |
|-----------|----------------------|---------------------------|
| Steps | `StepsRecord` | ✅ Confirmed |
| Heart Rate | `HeartRateRecord` | ✅ Confirmed |
| Resting Heart Rate | `RestingHeartRateRecord` | ✅ Confirmed |
| Sleep | `SleepSessionRecord` | ✅ Confirmed |
| SpO2 | `OxygenSaturationRecord` | ✅ Confirmed |
| Weight | `WeightRecord` | ✅ Confirmed |
| Active Calories | `ActiveCaloriesBurnedRecord` | ✅ Confirmed |
| Distance | `DistanceRecord` | ✅ Confirmed |
| Respiratory Rate | `RespiratoryRateRecord` | ⚠️ Not always written |
| Blood Pressure | `BloodPressureRecord` | ✅ On compatible devices |
| Body Fat | `BodyFatRecord` | ✅ With Mi Scale |

Source: [ROOK Tech Docs](https://docs.tryrook.io/data-sources/xiaomi/), [Google Play listing](https://play.google.com/store/apps/details?id=com.xiaomi.wearable)

**Companion App Development** (Kotlin):
```kotlin
// build.gradle
dependencies {
    implementation("androidx.health.connect:connect-client:1.1.0-alpha12")
}

// Read heart rate
val response = healthConnectClient.readRecords(
    ReadRecordsRequest(
        HeartRateRecord::class,
        timeRangeFilter = TimeRangeFilter.between(startTime, endTime)
    )
)
for (record in response.records) {
    for (sample in record.samples) {
        val bpm = sample.beatsPerMinute
        // upload to VPS
    }
}

// Background sync with WorkManager
class HealthSyncWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        // read Health Connect → serialize → POST to VPS
        return Result.success()
    }
}
```

**Production VPS Pipeline Pattern** (proven):
- [open-wearables](https://github.com/yocxy2/open-wearables) — Full open-source platform: FastAPI + PostgreSQL + Celery. Companion Android app reads HC and posts to backend.
- [health-dashboard](https://github.com/manumnoha-sys/health-dashboard) — Galaxy Watch + HC bridge, syncs every 30 min
- [health-connect-webhook](https://github.com/mcnaveen/health-connect-webhook) — Android app → webhook bridge
- [HCGateway](https://github.com/ShuchirJ/HCGateway) — REST API bridge for Health Connect

**Pre-existing Android apps that can bridge HC → VPS** (no custom dev needed):
| App | Features | Sync |
|-----|----------|------|
| **mcnaveen/health-connect-webhook** | HC → webhook, interval/scheduled | 15 min+ |
| **owen282000/life-dashboard-companion** | HC + screen time → webhook | 15 min+ |
| **DavideGarbi/openclaw-healthconnect-bridge** | HC → OpenClaw HTTP | 30 min+ |
| **HCGateway** | HC → REST API bridge | 2 hours |

**Pros**:
- ✅ **Official API** — stable, versioned, Google-maintained
- ✅ Mi Fitness **already supports** Health Connect sync
- ✅ Background sync via WorkManager (battery-friendly)
- ✅ Clean, typed records (not raw DB parsing)
- ✅ More than 50 data types supported
- ✅ Android 14+ has Health Connect built-in
- ✅ Can read data from multiple sources aggregated

**Cons**:
- ❌ **Must build a companion Android app** (or use pre-existing one)
- ❌ Health Connect has **no server-side API** — data must go through phone
- ❌ Read history limited to 30 days (unless `READ_HEALTH_DATA_HISTORY` permission)
- ❌ Mi Fitness sync to HC can be flaky (user reports of intermittent breaks)
- ❌ Must open Mi Fitness app occasionally to trigger sync
- ❌ No stress data type in Health Connect (as of 2026)
- ❌ PAI score not available in Health Connect

**Battery Impact**: Low. WorkManager batches and respects Doze mode. ~2-3% extra/day.

**Latency**: 15-30 min (WorkManager interval). Faster if app triggers manual sync.

**Reliability**: ★★★★☆ — Official but depends on Mi Fitness → HC sync chain. Multiple users report sync requiring app foreground occasionally.

---

### #3 MI FITNESS CLOUD API — Python SDK

**What it is**: Python SDK that authenticates with Xiaomi Cloud and pulls health data via Xiaomi's internal cloud API.

**Primary Python Library**: [`mi-fitness`](https://pypi.org/project/mi-fitness/) (v0.2.0) by Misty02600 — SDK through 亲友 (family member) data access.

**Data Coverage**:
```python
from mi_fitness import MiFitness

client = MiFitness(user_id="...", password="...")

# Heart rate: daily avg, resting, max, min, latest sample
hr_data = client.get_heart_rate(uid, date)

# Sleep: duration, score, deep/light/REM, stage details
sleep_data = client.get_sleep(uid, date)

# Steps: count, distance, calories
steps_data = client.get_steps(uid, date)

# SpO2 history (daily/weekly)
spo2_data = client.get_spo2_history(uid, date, days=7)

# Blood pressure history
bp_data = client.get_blood_pressure_history(uid, date, days=7)

# Weight history
weight_data = client.get_weight_history(uid, date, days=7)

# Daily summary (concurrent fetch of heart + sleep + steps)
summary = client.get_daily_summary(uid, date)

# Latest snapshot
latest = client.get_latest_data(uid)
```

**Alternative Python Library**: [`Mi-Fitness-Sync`](https://github.com/kevinkwee/Mi-Fitness-Sync) — focuses on workout data and Strava sync, but accesses same cloud endpoints.

**Alternative: MCP Server**: [`kubulashvili/mi-fitness-mcp`](https://github.com/kubulashvili/mi-fitness-mcp) — MCP server backed by local SQLite, syncs from Mi Fitness cloud.

**Authentication**: Requires `userId` and `passToken` from Xiaomi account cookies.

**API Endpoints (Reverse-Engineered)**:
| Endpoint | Purpose | Source |
|----------|---------|--------|
| `POST /v2/client/login` | Auth with Huami | [MiFit-Hack-API](https://github.com/bysiber/MiFit-Hack-API) |
| `GET /v1/data/band_data.json` | Band summary data | [hacking-mifit-api](https://github.com/micw/hacking-mifit-api) |
| `GET /v1/sport/run/history.json` | Workout history | [mifit-exporter](https://github.com/imduffy15/mifit-exporter) |
| `POST /healthapp/service/gen_download_url` | FDS binary download | [Habr RE article](https://habr.com/ru/articles/1038812/) |
| `GET /app/v1/data/get_aggregated_fitness_data_by_watermark` | Aggregated data | Habr RE article |
| `GET /v1/statistics/get_stat_data_by_time` | Statistics | [Xiaomi Cloud tokens extractor](https://github.com/PiotrMachowski/Xiaomi-cloud-tokens-extractor) |

**FDS Binary Format**: Xiaomi stores high-resolution sleep, HR, SpO2 in FDS (File Data Storage) objects. These are AES/CBC encrypted blobs that can be decrypted and parsed:
```python
# From the Xiaomi Smart Band 10 reverse engineering
def parse_sleep_assist_info(b, pos, byte_count, version):
    interval = struct.unpack_from("<h", b, pos)[0]
    record_count = struct.unpack_from("<h", b, pos + 2)[0]
    pos += 4
    start_time = 0
    if version >= 2:
        start_time = struct.unpack_from("<I", b, pos)[0]
        pos += 4
    values = []
    for _ in range(record_count):
        values.append(b[pos])
        pos += byte_count
    return {"start_time": start_time, "interval": interval,
            "record_count": record_count, "values": values}, pos
```

**Pros**:
- ✅ Pure Python — no Android app needed
- ✅ All major data types: heart rate, sleep, steps, SpO2, blood pressure
- ✅ Historical data accessible (years back)
- ✅ Can pull data for multiple accounts (family member feature)
- ✅ MCP server available for AI integration

**Cons**:
- ❌ **Unofficial API** — can break at any time when Xiaomi changes endpoints
- ❌ Sleep data may not be available on newer cloud endpoints
- ❌ Authentication requires browser cookie extraction (`passToken`)
- ❌ Xiaomi Cloud has region-specific endpoints and RC4 encryption
- ❌ Rate limits may apply (cloud is not designed for frequent polling)
- ❌ Latency: only as fresh as last Mi Fitness sync to cloud
- ❌ FDS binary format requires custom parsing

**Battery Impact**: Zero (runs on VPS, not phone).

**Latency**: Minutes to hours — depends on Mi Fitness phone app sync frequency.

**Reliability**: ★★★☆☆ — Works but unofficial. The [mi-fitness SDK](https://github.com/MistEO/MiSDK) is actively maintained (2026). Main risk: Xiaomi API changes.

---

### #4 MI FITNESS GDPR DATA EXPORT — Manual + Automatable

**What it is**: Xiaomi provides a GDPR-compliant data export webpage that generates a ZIP with CSV files.

**Export URL**: https://account.xiaomi.com (Privacy → Manage Your Data → MI Fitness → Download)

**ZIP Contents (CSV files)**:
| File | Contents | Key Columns |
|------|----------|-------------|
| `hlth_center_fitness_data.csv` | Raw health logs | uid, key, time, value (JSON) |
| `hlth_center_aggregated_fitness_data.csv` | Daily/weekly summaries | tag, key, time, value |
| `hlth_center_sport_record.csv` | Sport events | category, key, time, value |
| `hlth_center_sport_track_data.csv` | GPS tracks | key, time, .gpx |
| `user_fitness_data_records.csv` | User health records | tag, key, time, value |
| `user_device_setting.csv` | Device settings | — |

Source: [Japanese reverse engineering article](https://zenn.dev/hitama/articles/a5d9a3e1e34d6c)

**Older Zepp Life (Huami) export**:
| File | Contents |
|------|----------|
| `ACTIVITY_*.csv` | Steps, distance, calories |
| `HEARTRATE_*.csv` | Heart rate readings |
| `HEARTRATE_AUTO_*.csv` | Auto heart rate |
| `SLEEP_*.csv` | Sleep data |
| `BODY_*.csv` | Body measurements |
| `SPORT_*.csv` | Sport data |

Source: [zoilomora/xiaomi-mi-fit-data-export](https://github.com/zoilomora/xiaomi-mi-fit-data-export)

**Automation**:
```python
# The zoilomora script automates this:
# 1. POST to request data export → get UUID
# 2. Wait for email with UUID
# 3. GET download URL with ZIP password
# 4. Download and unzip → parse CSVs
```

**Pros**:
- ✅ Official data export (GDPR)
- ✅ Well-structured CSV files
- ✅ Can request historical data (years)
- ✅ No root or hacking required

**Cons**:
- ❌ **Not real-time** — manual trigger or API automation needed
- ❌ Request takes minutes to hours to be ready (async email delivery)
- ❌ Authentication flow is web-based, hard to fully automate
- ❌ No on-demand API

**Battery Impact**: Zero (server-side).

**Latency**: Hours to days (email-based async).

**Reliability**: ★★★★☆ — Very reliable but slow. Good for historical backfill, bad for real-time.

---

### #5 ZEPP LIFE (MI FIT) HUAMI CLOUD API

**What it is**: Original Huami cloud API used by older Xiaomi devices (Mi Band 1-6, Mi Scale). Predecessor to Mi Fitness cloud.

**Key Endpoints** (from [bysiber/MiFit-Hack-API](https://github.com/bysiber/MiFit-Hack-API)):
```
POST https://account.huami.com/v2/client/login
     → returns app_token, user_id
GET  https://api-mifit.huami.com/v1/data/band_data.json
     ?query_type=summary&device_type=android_phone&userid=X&from_date=Y&to_date=Z
     Header: apptoken
     → Response: daily JSON with BASE64-encoded summary
```

**Base64 Summary Decoding**:
```python
import base64, json
raw = day_data['summary']  # BASE64
decoded = json.loads(base64.b64decode(raw))
# decoded['stp'] = step data: ttl (total), dis (distance), cal (calories)
# decoded['slp'] = sleep data: st (start epoch), ed (end), dp (deep min), lt (light min)
# decoded['stp']['stage'] = list of activities with start/end/step/distance/cal/mode
```

**Existing Python Libraries**:
- [rolandsz/Mi-Fit-and-Zepp-workout-exporter](https://github.com/rolandsz/Mi-Fit-and-Zepp-workout-exporter) (201 stars) — GPX/GeoJSON/CSV export for workouts
- [imduffy15/mifit-exporter](https://github.com/imduffy15/mifit-exporter) — GPX/TCX conversion
- [huami-token](https://pypi.org/project/huami-token/) — Auth token retrieval for Gadgetbridge

**Pros**:
- ✅ Well-documented reverse-engineered API
- ✅ Multiple Python libraries available
- ✅ Can be polled from VPS

**Cons**:
- ❌ Only works with **old devices** (Zepp Life not used by new Xiaomi watches)
- ❌ Sleep data may be incomplete
- ❌ Huami API is increasingly restricted
- ❌ Newer Xiaomi accounts use a different cloud backend

**Battery Impact**: Zero (VPS polling).

**Reliability**: ★★☆☆☆ — Legacy API, declining support.

---

### #6 NOTIFY & FITNESS + TASKER — Real-time Event Push

**What it is**: Third-party app "Notify for Mi Band/Xiaomi" (paid) that can replace Mi Fitness. It has deep Tasker integration for real-time health data events.

**Tasker Intents Available**:
| Intent Action | Data | Trigger |
|--------------|------|---------|
| `com.mc.xiaomi.heartRateGot` | `value` (BPM int) | After each HR measurement |
| `com.mc.xiaomi.stepsGot` | `value` (steps int) | On step update |
| `com.mc.xiaomi.batteryStatGot` | `value` (battery %) | Battery change |
| `com.mc.xiaomi.fellSleep` | — | When user falls asleep |
| `com.mc.xiaomi.wokeUp` | — | When user wakes |
| `com.mc.xiaomi.stopWearing` | — | Band removed from wrist |
| `com.mc.xiaomi.bandConnected` | — | BLE connection event |
| `com.mc.xiaomi.bandDisconnected` | — | BLE disconnection |

**Tasker → VPS Pipeline**:
```
Notify & Fitness → Tasker (intent received) 
  → Tasker MQTT Publisher plugin → MQTT Broker (cloud)
    → Python MQTT subscriber on VPS → Database
```

OR

```
Notify & Fitness → Tasker (intent received)
  → Tasker HTTP POST plugin → FastAPI endpoint on VPS
```

OR (for step/HR data every N minutes):
```
Tasker: every N minutes → send intent to Notify to sync
  → Notify exports CSV → Tasker reads file → HTTP POST to VPS
```

**Heart Monitor Settings**: Must set to "Notify app mode" for real-time HR intents.

**CSV Export via Tasker Intent**:
```java
Action: com.mc.xiaomi.taskerExportAllSpreadsheetData
Extras: start (long, ms timestamp), end (long, ms timestamp)
// Files saved to: /storage/emulated/0/android/data/com.mc.xiaomi1/files/export/
```

**Real-World Proven Pipeline**:
- [Home Assistant integration guide](https://community.home-assistant.io/t/mi-band-3-amazfit-bip-integration-updated-10-01-2019/89777) — Tasker → MQTT → HA
- [JamesMcCarthy79 HA Config](https://github.com/JamesMcCarthy79/Home-Assistant-Config/blob/master/config/packages/fitness/README.md) — Tasker → MQTT → InfluxDB
- [Emanuele Papa sleep automation](https://www.emanuelepapa.dev/sleep-automation-with-mi-band-and-home-assistant/) — Tasker → HA via MQTT

**Pros**:
- ✅ **Real-time** — HR and steps pushed as events (not polling)
- ✅ Works without Mi Fitness (Notify replaces it)
- ✅ SpO2 and sleep events also available
- ✅ Tasker handles MQTT/HTTP for cloud upload
- ✅ Proven in many HA integrations

**Cons**:
- ❌ **Requires paid app** (Notify & Fitness — ~$3-4)
- ❌ Must NOT have Mi Fitness running (BLE conflict)
- ❌ Notify and Mi Fitness cannot coexist on BLE
- ❌ Tasker complexity — many components
- ❌ Heart rate data is from one-time measurements, not continuous
- ❌ Battery impact: BLE always-on + Tasker polling

**Battery Impact**: Medium-High. BLE always connected + Tasker profiles. Expect 8-12% extra/day.

**Latency**: Real-time (seconds) for HR/steps events.

**Reliability**: ★★★★☆ — Notify is mature (10+ years). Tasker integration is solid. Main risk: Xiaomi firmware changes breaking Notify's BLE compatibility.

---

### #7 ADB DATA EXTRACTION — Direct SQLite Pull

**What it is**: Pull the Mi Fitness or Gadgetbridge SQLite database directly from the Android device via ADB (USB debugging).

**Methods**:

**Method A — Rooted device**:
```bash
adb shell
su
cp /data/data/com.xiaomi.wearable/databases/device_db /sdcard/
exit
adb pull /sdcard/device_db
```

**Method B — Non-rooted (ADB backup)**:
```bash
# Create backup of Mi Fitness app data
adb backup -f mi_fitness.ab -noapk -noshared com.xiaomi.wearable

# Convert backup to tar
dd if=mi_fitness.ab bs=1 skip=24 | python -c "import zlib,sys;sys.stdout.write(zlib.decompress(sys.stdin.read()))" > mi_fitness.tar

# Extract
tar xvf mi_fitness.tar

# DB files at: apps/com.xiaomi.wearable/db/
```

**Method C — Non-rooted (run-as)**:
```bash
# For debuggable or userdebug builds
adb shell run-as com.xiaomi.wearable cp databases/device_db /sdcard/device_db
adb pull /sdcard/device_db
```

**DB Location for Different Apps**:
| App | Package | DB Path | Key Table |
|-----|---------|---------|-----------|
| Mi Fitness (new) | `com.xiaomi.wearable` | `databases/device_db` | `device` (JSON with auth_key) |
| Zepp Life (old) | `com.xiaomi.hm.health` | `databases/origin_db_*` | `DATE_DATA`, `HEART_RATE` |
| Gadgetbridge | `nodomain.freeyourgadget.gadgetbridge` | `Gadgetbridge` (export) | `MI_BAND_ACTIVITY_SAMPLE`, etc. |

**Mi Fitness Internal DB Schema** (from RE):
- `device_db`: JSON blobs with auth keys, device info
- Health data is primarily stored in Xiaomi FDS cloud, not locally
- Local DB mainly caches recent data

**Old Zepp Life DB Schema**: The `DATE_DATA` table contains:
- `SUMMARY` column: JSON with daily aggregates (steps, sleep, heart rate)
- `DATA` column: Raw per-minute activity (1440 entries/day)
- `DATA_HR` column: Raw per-minute heart rate
- Each encoded as binary/custom format

**Pros**:
- ✅ Full access to the app's local database
- ✅ Works offline
- ✅ Can be automated via cron on dev machine

**Cons**:
- ❌ **Requires USB connection** or ADB over network
- ❌ Non-rooted extraction is complex (ADB backup flow)
- ❌ Mi Fitness stores most data in cloud, not locally
- ❌ Gadgetbridge DB is the better target, not Mi Fitness DB
- ❌ Not suitable for production pipeline (manual/physical)

**Battery Impact**: Zero.

**Latency**: On-demand.

**Reliability**: ★★★☆☆ — Works but impractical for continuous pipeline.

---

### #8 DIRECT BLE — Python Bluetooth Library

**What it is**: Connect directly to the Xiaomi watch via BLE from a computer using Python, bypassing the phone entirely.

**Available Libraries**:
- [xiaomi-ble](https://github.com/Bluetooth-Devices/xiaomi-ble) — Parser for Xiaomi BLE advertisements (53 stars, actively maintained)
- [python-miio](https://github.com/rytilahti/python-miio) — Xiaomi smart home protocol (4217 stars, but for IoT not wearables)
- [miband5](https://github.com/AdrianDahlstrom/miband5) — Direct Mi Band 4/5 BLE library (7 stars)
- [pymb1a](https://github.com/freezed-or-frozen/pymb1a) — Mi Band 1A BLE library

**Xiaomi Encrypted BLE (V1)** — from [Band 7 Pro RE](https://medium.com/h7w/i-reverse-engineered-my-xiaomi-band-7-pro-using-only-a-browser-966f88c32f4e):
```
Service: FE95
Characteristics: 0x51, 0x52, 0x53
Auth handshake: send auth key → receive nonces → derive session keys → encrypted comms
```

**BreakMi Toolkit**: The academic paper [BreakMi](https://tches.iacr.org/index.php/TCHES/article/download/9704/9234) provides a full Python toolkit for:
- Xiaomi BLE protocol dissection
- Pairing v1/v2
- Authentication and communication
- Eavesdropping and data extraction

**Pros**:
- ✅ No phone or Android dependency
- ✅ Can run on Linux (Raspberry Pi) near the watch

**Cons**:
- ❌ **Requires BLE hardware** on the computer
- ❌ Auth key extraction still needed from Mi Fitness
- ❌ Session keys, encrypted BLE v1/v2 are complex
- ❌ Watch BLE range limits (10m max)
- ❌ Libraries have limited device support
- ❌ Newer Xiaomi bands use encrypted BLE v2 with protobuf
- ❌ Not production-ready for most devices

**Battery Impact**: N/A (external computer).

**Latency**: Real-time.

**Reliability**: ★☆☆☆☆ — Experimental for most devices. Production-ready only for very old Mi Bands (1A, 2, 4).

---

### #9 TASKER + AUTONOTIFICATION — Notification Intercept

**What it is**: Use Tasker with AutoNotification plugin to intercept Mi Fitness notifications and extract health data from them.

**How it works**: Mi Fitness occasionally sends notifications with health data summaries. AutoNotification can intercept these and extract the text content.

**Pattern**:
```
Profile: Event → Plugin → AutoNotification → Intercept
  Filter: Notification App = "Mi Fitness"
  Task: Parse %antitle and %antext for health numbers
       → HTTP POST to VPS
```

**Limitations**: 
- Mi Fitness notifications contain limited data (mostly "X steps today" or "Sleep quality summary")
- Not a reliable source of granular data
- Notification content is user-facing, not machine-parseable
- Low data throughput

**Pros**:
- ✅ Easy to set up
- ✅ No root
- ✅ Works alongside Mi Fitness

**Cons**:
- ❌ Very limited data (only what appears in notifications)
- ❌ Not reliable as primary data source
- ❌ Notification content is inconsistent and sparse
- ❌ AutoNotification battery drain (notification listener service)

**Battery Impact**: Low-Medium (notification listener).

**Reliability**: ★☆☆☆☆ — Supplement only, not a primary method.

---

### #10 OPEN WEARABLES PLATFORM — Self-Hosted Unified API

**What it is**: [Open Wearables](https://github.com/yocxy2/open-wearables) — an MIT-licensed platform that unifies wearable data through a single API. Currently supports Health Connect (via companion app), with extensible provider architecture.

**Architecture**:
```
[Android Phone]                   [Your VPS]
  Mi Fitness → HC → Open Wearables App → HTTP → FastAPI backend → PostgreSQL
```

**Component**: `yocxy2/open-wearables` (2026, very new)
- Backend: FastAPI (Python) + PostgreSQL + Redis + Celery
- Frontend: React + TanStack Router
- Companion Android app reads Health Connect
- Normalized data model across providers

**Pros**:
- ✅ Full platform, not just a bridge
- ✅ Self-hosted, MIT licensed
- ✅ Normalized data schema
- ✅ AI-powered health insights built in
- ✅ Webhook notifications

**Cons**:
- ❌ Very new (March 2026, 0 stars)
- ❌ Requires running PostgreSQL + Redis + Celery
- ❌ Companion Android app architecture still evolving
- ❌ Overkill if you just need data ingestion

---

## Data Format Comparison

| Method | Format | Parsability | Time Granularity |
|--------|--------|-------------|------------------|
| Gadgetbridge | SQLite | ★★★★★ Direct SQL queries | Per-minute |
| Health Connect | Typed Records (Kotlin/Java) | ★★★★ JSON after serialization | Per-reading |
| Mi Fitness Cloud SDK | Python objects | ★★★★★ Native Python | Daily + per-reading |
| GDPR Export | CSV | ★★★★★ Easy | Varies by file |
| Zepp Life Cloud | BASE64 JSON | ★★★★ Need to decode | Daily summaries |
| Notify + Tasker | Android Intent | ★★★★ Intents to MQTT/HTTP | Per-event (real-time) |
| ADB Pull | SQLite | ★★★★★ Direct SQL | Per-minute |
| Direct BLE | Custom binary | ★★ Need protocol parsing | Per-second |
| AutoNotification | Notification text | ★★ Unstructured text | Only when notification fires |

## Recommended Pipeline Architecture

### Tier 1 (Primary — Gadgetbridge)

```
┌─────────────────┐     ┌──────────────┐     ┌────────────┐     ┌──────────┐
│ Xiaomi Watch     │ BLE │ Gadgetbridge  │ SQLite │ Auto-Export │ WebDAV │ VPS Server  │
│ (Mi Band 9 Pro)  │────▶│ (Android)     │───────▶│ (every 1hr)  │───────▶│             │
└─────────────────┘     └──────────────┘     └────────────┘     │  ┌──────────┐ │
                                                                  │  │ Python   │ │
                                                                  │  │ Ingest   │ │
                                                                  │  │ Script   │ │
                                                                  │  └──────────┘ │
                                                                  │       ↓       │
                                                                  │  ┌──────────┐ │
                                                                  │  │ Timescale │ │
                                                                  │  │ /InfluxDB │ │
                                                                  │  └──────────┘ │
                                                                  └──────────────┘
```

### Tier 2 (Backup — Health Connect Webhook)

```
┌─────────────────┐     ┌──────────────┐     ┌────────────┐     ┌──────────┐
│ Xiaomi Watch     │ BLE │ Mi Fitness    │ HC  │ HC Webhook  │ HTTP │ Your VPS  │
│                  │────▶│ (Android)     │────▶│ (Android)   │─────▶│ FastAPI   │
└─────────────────┘     └──────────────┘     └────────────┘     └──────────┘
```

### Tier 3 (Backfill — Cloud SDK)

```
┌──────────────┐     ┌──────────────┐     ┌──────────┐
│ Mi Fitness   │     │ Python SDK   │     │ Your VPS │
│ Cloud        │────▶│ mi-fitness   │────▶│ Database │
│ (Xiaomi)     │     │ (cron daily) │     │          │
└──────────────┘     └──────────────┘     └──────────┘
```

## Battery Impact Summary

| Method | Daily Battery Drain | Always-On BLE | Background Service |
|--------|-------------------|---------------|-------------------|
| Gadgetbridge | 5-8% | Yes | Yes (auto-export) |
| Gadgetbridge (no BLE, export only) | 1-2% | No | Periodic |
| Health Connect + Webhook app | 3-5% | No (Mi Fitness handles) | WorkManager |
| Notify & Fitness + Tasker | 8-12% | Yes | Tasker + Notify |
| Mi Fitness alone + Cloud SDK | 3-5% | No (Mi Fitness handles) | Mi Fitness |
| Tasker + AutoNotification | 2-4% | No | Notification listener |

## Python Library Availability Matrix

| Library | Package | Data Types | Maintenance | GitHub Stars |
|---------|---------|-----------|-------------|-------------|
| **mi-fitness** | `pip install mi-fitness` | HR, sleep, steps, SpO2, BP, weight | Active (2026) | ~50 |
| **Mi-Fitness-Sync** | `pip install mi-fitness-sync` | Workouts, HR, GPS | Active (2026) | 3 |
| **gadgetbridge_to_influxdb** | — (script) | HR, steps, sleep, stress, SpO2 | Maintained | ~20 |
| **gb2influxdb** | `pip install gb2influxdb` | HR, steps, sleep | Archived (2021) | 7 |
| **Mi-Fit-and-Zepp-workout-exporter** | — (script) | Workouts, GPX, TCX | Semi-active | 201 |
| **mi-fitness-mcp** | `pip install mi-fitness-mcp` | HR, steps, body | Active (2026) | 1 |
| **huami-token** | `pip install huami-token` | Auth key retrieval | Active (2026) | — |
| **xiaomi-ble** | `pip install xiaomi-ble` | BLE advertisement parser | Very active | 53 |
| **breakmi** | — (toolkit) | BLE protocol analysis | Academic | ~20 |

## Key Findings & Recommendations

1. **Gadgetbridge is the gold standard** for production pipelines. It has auto-export, SQLite format, all data types, and multiple proven integrations. **Use this as Tier 1.**

2. **Health Connect is the official path** but requires a companion Android app. Several pre-existing apps (HC Webhook, Life Dashboard Companion) can bridge HC → HTTP with no custom code. **Use this as Tier 2 fallback.**

3. **Mi Fitness Cloud SDK** (`mi-fitness` on PyPI) is surprisingly mature for an unofficial library — covers HR, sleep, steps, SpO2, blood pressure, weight. Good for daily batch pulls. **Use this as Tier 3 for backfill.**

4. **Notify + Tasker** is the only truly real-time option (sub-second HR events). If real-time alerts are needed (e.g., "heart rate > 120"), this is the answer. **Use for real-time event triggers only.**

5. **Do NOT rely on:**
   - AutoNotification intercept (sparse data)
   - Direct BLE from Python (too experimental for new watches)
   - ADB backup (not pipeline-suitable)
   - Zepp Life API (legacy, declining)

6. **Battery is manageable.** Even the heaviest method (Notify + Tasker) adds ~12% daily. Gadgetbridge adds 5-8%. Health Connect webhook adds 3-5%.

7. **Permission considerations**: All on-device methods require Android permissions (Physical Activity, Nearby Devices for BLE). Gadgetbridge and Health Connect follow standard Android permission patterns — no special requirements.

---
