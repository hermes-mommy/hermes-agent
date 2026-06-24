# P14 Gadgetbridge Schema & Export Reality Check

**Scope:** Gadgetbridge export/WebDAV/SQLite behavior relevant to Xiaomi wearables, with emphasis on what P14-005 assumes versus what the real database/export paths actually look like.

**Primary sources used:**
- Gadgetbridge Auto Export docs: <https://gadgetbridge.org/internals/automations/auto-export/>
- Gadgetbridge Data Management docs: <https://gadgetbridge.org/internals/development/data-management/>
- Gadgetbridge Xiaomi device pages: <https://gadgetbridge.org/gadgets/wearables/xiaomi/> and <https://gadgetbridge.org/basics/topics/xiaomi-protobuf/>
- Gadgetbridge activity analysis / wiki excerpts and downstream parsers:
  - <https://codeberg.org/Freeyourgadget/Gadgetbridge/wiki/Data-Export-Import-Merging-Processing>
  - <https://codeberg.org/Freeyourgadget/Gadgetbridge/wiki/Activity-Analysis>
  - <https://projects.bentasker.co.uk/gils_projects/wiki/utilities/gadgetbridge_to_influxdb/page/Fields.html>
  - <https://projects.bentasker.co.uk/gils_projects/issue/utilities/gadgetbridge_to_influxdb/13.html>
  - <https://projects.bentasker.co.uk/gils_projects/issue/utilities/gadgetbridge_to_influxdb/10.html>
  - <https://projects.bentasker.co.uk/gils_projects/issue/utilities/gadgetbridge_to_influxdb/34.html>
  - <https://www.bacaliu.de/analyzing_gadgetbridge_data_in_python.html>
  - <https://methodmatters.github.io/mi-band-5-data-gadgetbridge-r/>
- P14-005 assumptions file: `research-reports/p14-expansion/P14-005.md`

---

## 1) Executive summary

P14-005 assumes a much smaller, simpler schema than the real Gadgetbridge export database used for Xiaomi devices.

The real situation is:

1. **Gadgetbridge exports a single SQLite database named `Gadgetbridge` (no extension)**, or a zip backup that includes that DB plus preferences and GPX tracks. The auto-export feature can export either a **database-only backup** or a **full zip backup**.
2. **WebDAV is a transport target, not the database format.** Gadgetbridge can auto-export its database to a path on the phone, and users commonly sync that folder to WebDAV/Nextcloud/Syncthing externally.
3. **The schema is not a single fixed Xiaomi table with one row type.** For Xiaomi/Huami devices, the database commonly contains tables such as `MI_BAND_ACTIVITY_SAMPLE`, `HUAMI_HEART_RATE_MANUAL_SAMPLE`, `HUAMI_HEART_RATE_MAX_SAMPLE`, `HUAMI_HEART_RATE_RESTING_SAMPLE`, `HUAMI_SPO2_SAMPLE`, `HUAMI_STRESS_SAMPLE`, `HUAMI_EXTENDED_ACTIVITY_SAMPLE`, `HUAMI_PAI_SAMPLE`, and `HUAMI_SLEEP_RESPIRATORY_RATE_SAMPLE` depending on device/firmware/support.
4. **Many fields are stored in raw device units and timestamps are usually Unix timestamps, often in seconds for older tables and milliseconds for newer Huami tables.** This matters because P14-005 currently normalizes everything to UTC ISO by assuming millisecond-like inputs everywhere.
5. **For Xiaomi devices, sleep-stage fidelity is a caveat.** Gadgetbridge documents that deep-sleep detection is not reliable for many older Xiaomi/Huami devices and that some sleep hints are just stored raw without full post-processing.
6. **P14-005’s table list (`HEART_RATE_SAMPLE`, `SLEEP_SAMPLE`, `SPO2_SAMPLE`, `STRESS_SAMPLE`, `HRV_SAMPLE`, `BODY_ENERGY_SAMPLE`) does not match the real Xiaomi Gadgetbridge tables.** It looks closer to a synthetic or abstracted schema than the exported Gadgetbridge DB.

Net: P14-005 parser assumptions are **not grounded enough** for real Xiaomi Gadgetbridge exports. The parser must either target the actual Gadgetbridge schema or first define a transformation layer from raw Gadgetbridge tables to a normalized intermediate format.

---

## 2) What Gadgetbridge actually exports

### 2.1 Export artifacts

Gadgetbridge supports two export modes:

- **Database export**: exports the activities database only.
- **Zip export**: exports the full Gadgetbridge data set, including the database, preferences, and other files such as GPX tracks.

The docs explicitly state that the **activity database is exported as an SQLite file called `Gadgetbridge` without an extension**. The export/import folder is typically under Android app storage, often:

```text
/storage/emulated/0/Android/data/nodomain.freeyourgadget.gadgetbridge/files/
```

The exact package path can vary by flavor/build.

### 2.2 Auto-export and WebDAV

Gadgetbridge’s auto-export can periodically write the DB/zip to a user-chosen export path. Common production patterns then sync that folder to:

- WebDAV / Nextcloud
- Syncthing
- local shared storage

Important clarification: **Gadgetbridge itself is not “uploading raw SQLite DBs to WebDAV” as a dedicated protocol feature in the schema sense**; instead it exports a DB file locally, and a sync layer (or a WebDAV-mounted path / external sync pipeline) moves that file elsewhere. In practice, downstream pipelines fetch the exported `Gadgetbridge` SQLite file from WebDAV and parse it.

Evidence: bentasker’s `gadgetbridge_to_influxdb` explicitly describes fetching the exported Gadgetbridge DB from a WebDAV server and parsing it afterwards.

### 2.3 File naming convention

Real-world convention from docs and examples:

- database file: `Gadgetbridge`
- zip export: a full backup archive
- GPX files: `gadgetbridge-track-YYYY-MM-DD...gpx`
- preferences: `Export_preference*` XML files

P14-005’s assumption of “`.db` SQLite files” is therefore too specific and may miss the default export name.

---

## 3) Real Xiaomi/Gadgetbridge schema: tables and shapes

### 3.1 Core table families seen in the wild

From Gadgetbridge docs and downstream SQL examples, the most relevant Xiaomi/Huami tables include:

- `MI_BAND_ACTIVITY_SAMPLE`
- `HUAMI_HEART_RATE_MANUAL_SAMPLE`
- `HUAMI_HEART_RATE_MAX_SAMPLE`
- `HUAMI_HEART_RATE_RESTING_SAMPLE`
- `HUAMI_EXTENDED_ACTIVITY_SAMPLE`
- `HUAMI_SPO2_SAMPLE`
- `HUAMI_STRESS_SAMPLE`
- `HUAMI_PAI_SAMPLE`
- `HUAMI_SLEEP_RESPIRATORY_RATE_SAMPLE`
- `BASE_ACTIVITY_SUMMARY` (workouts / summaries)
- `DEVICE` / `USER` / `DEVICE_ATTRIBUTES` / `USER_ATTRIBUTES`

The exact table set depends on device model, firmware, and which data the firmware/Gadgetbridge actually supports.

### 3.2 `MI_BAND_ACTIVITY_SAMPLE`

This is the classic Mi Band activity table and is the most documented by older guides.

A schema excerpt from community docs shows:

```sql
CREATE TABLE IF NOT EXISTS "MI_BAND_ACTIVITY_SAMPLE"
("TIMESTAMP" INTEGER NOT NULL,
 "DEVICE_ID" INTEGER NOT NULL,
 "USER_ID" INTEGER NOT NULL,
 "RAW_INTENSITY" INTEGER NOT NULL,
 "STEPS" INTEGER NOT NULL,
 "RAW_KIND" INTEGER NOT NULL,
 "HEART_RATE" INTEGER NOT NULL,
 PRIMARY KEY ("TIMESTAMP", "DEVICE_ID") ON CONFLICT REPLACE
) WITHOUT ROWID;
```

Observed meaning in the docs/examples:

- `TIMESTAMP`: Unix timestamp, generally **seconds** in older Mi Band tables
- `RAW_INTENSITY`: non-normalized intensity score
- `STEPS`: steps for that minute/sample, not cumulative
- `RAW_KIND`: raw activity/sleep type code
- `HEART_RATE`: bpm, often `255` when missing in older exports

The database is **minute-aggregated**, and gadget timestamps may be any second within the minute. The same minute can be duplicated if transfers repeat.

### 3.3 Xiaomi/Huami newer tables

For newer Xiaomi/Huami devices, `MI_BAND_ACTIVITY_SAMPLE` is not the only relevant source. Documentation and downstream parsers show separate tables for different sensor types:

#### Heart rate tables
- `HUAMI_HEART_RATE_MANUAL_SAMPLE`
- `HUAMI_HEART_RATE_MAX_SAMPLE`
- `HUAMI_HEART_RATE_RESTING_SAMPLE`

Typical payload shape (from downstream code/docs):

- timestamp
- device id
- user id
- utc offset or type fields depending on table
- heart rate value

Important: these are **not** the same as the old `HEART_RATE_SAMPLE` table name assumed in P14-005.

#### SpO2
- `HUAMI_SPO2_SAMPLE`

Downstream examples show rows like:

- `TIMESTAMP`
- `DEVICE_ID`
- `USER_ID`
- `TYPE_NUM`
- `SPO2`

The source commentary indicates timestamps are **milliseconds** in this table.

#### Stress
- `HUAMI_STRESS_SAMPLE`

Downstream query patterns show columns such as:

- `TIMESTAMP`
- `DEVICE_ID`
- `USER_ID`
- `TYPE_NUM`
- `STRESS`

The `TYPE_NUM` value distinguishes periodic samples; downstream tooling filters on `type_num = 1` for periodic readings.

#### Extended activity
- `HUAMI_EXTENDED_ACTIVITY_SAMPLE`

This table is the real source for a richer activity record on newer devices. Downstream field docs indicate it can include:

- `intensity`
- `steps`
- `heart_rate`
- `sleep`
- `deep_sleep`
- `rem_sleep`

Downstream issue discussion shows timestamps in this table may be **seconds**, while newer Huami sensor tables may use **milliseconds**; do not assume all Huami tables share one timestamp unit.

#### PAI, sleep respiratory rate, other extras
- `HUAMI_PAI_SAMPLE`
- `HUAMI_SLEEP_RESPIRATORY_RATE_SAMPLE`
- likely other device-specific tables depending on firmware and model

### 3.4 `DEVICE` table matters for merging and device identity

Gadgetbridge database entries are device-scoped. The `DEVICE` table holds the device identity mapping (`_id`, MAC/identifier, alias/name). When parsing or merging histories, `DEVICE_ID` should be interpreted as a foreign key to `DEVICE._id` rather than invented by the parser.

This directly conflicts with P14-005’s hardcoded `DEFAULT_DEVICE_ID = "watch_s3_01"` approach if the goal is faithful parsing of exported records.

---

## 4) Timestamp conventions and normalization risk

### 4.1 Real timestamp patterns

The evidence shows multiple timestamp conventions in Gadgetbridge data:

- **Older Mi Band activity tables**: seconds-based Unix timestamps
- **Some Huami tables**: milliseconds-based timestamps
- Some downstream scripts convert to nanoseconds for TSDB ingestion after reading seconds/ms from SQLite

### 4.2 Why this matters

P14-005 currently describes a parser that:

- treats timestamps as UTC ISO strings directly
- assumes a blanket `_ensure_utc()` conversion from integer timestamps
- mixes record-level semantics with normalization semantics

That is risky because real Gadgetbridge exports can contain a mixed timestamp ecosystem. A robust parser must:

1. Detect table-specific timestamp units.
2. Preserve raw timestamp fields or unit metadata.
3. Convert to a normalized canonical format only after the unit is understood.

### 4.3 Timezone caveat for Xiaomi device data

Gadgetbridge data analysis docs indicate timestamps are often interpreted with `unixepoch` and localtime transformations in SQL examples. That means the DB stores raw time values and display/analysis layers choose local timezone at read time. P14-005 should not assume the stored timestamp is already UTC just because the Python object is a naive integer.

---

## 5) Data shape by metric type

Below is the most defensible shape summary from the available sources.

### 5.1 Sleep

Real Gadgetbridge sleep data is often not a standalone `SLEEP_SAMPLE` table for Xiaomi. On classic Mi Band data, sleep is encoded in activity rows, with raw kinds representing sleep states.

Observed/mentioned raw kinds:
- `112` = waking in one downstream parser
- `120` = light sleep
- `121` = deep sleep
- `122` = REM
- `249` = very light
- older docs also reference raw sleep kinds like `1`, `2`, `3`, `4` for legacy/other devices

Key caveat from Gadgetbridge docs: **old Huami devices have weak deep-sleep detection** and some hints are stored raw without being fully interpreted by Gadgetbridge.

### 5.2 Heart rate

Heart rate appears in multiple tables and may be either:
- periodic samples embedded in activity rows
- separate heart rate sample tables

Fields commonly seen:
- `HEART_RATE`
- sometimes `UTC_OFFSET` or `TYPE_NUM`

Older guides note `255` can mean missing/invalid HR.

### 5.3 SpO2

`HUAMI_SPO2_SAMPLE` typically exposes:
- `TIMESTAMP`
- `DEVICE_ID`
- `USER_ID`
- `TYPE_NUM`
- `SPO2`

Some devices expose manual samples and maybe periodic samples; the shape is simple but table name is not.

### 5.4 Stress

`HUAMI_STRESS_SAMPLE` typically exposes:
- `TIMESTAMP`
- `DEVICE_ID`
- `USER_ID`
- `TYPE_NUM`
- `STRESS`

Downstream tooling reconstructs duration by taking `LEAD(TIMESTAMP)` to create point-in-time intervals. That means raw DB rows are point samples, not duration ranges.

### 5.5 HRV

A dedicated `HRV_SAMPLE` table is **not established as the canonical Xiaomi Gadgetbridge table name** in the sources reviewed. HRV exists in some downstream models and device data ecosystems, but P14-005’s `HRV_SAMPLE` assumption is not source-grounded for Gadgetbridge Xiaomi exports. This is a high-risk assumption.

### 5.6 Body battery

Likewise, `BODY_ENERGY_SAMPLE` is **not confirmed as a real Gadgetbridge Xiaomi table** in the sources reviewed. “Body battery” is a conceptual normalization target, not a verified Gadgetbridge export table. If P14 needs a body-battery analog, it likely needs derived computation or a device-specific source mapping, not a direct table scan.

### 5.7 Activity / steps

`MI_BAND_ACTIVITY_SAMPLE` and `HUAMI_EXTENDED_ACTIVITY_SAMPLE` are the practical sources for:
- steps
- activity intensity
- sleep states
- often heart rate

The data is minute-granular and frequently “raw as sent by device,” not cleaned summaries.

---

## 6) WebDAV behavior: what is actually happening

Source-backed conclusion:

- Gadgetbridge auto-export writes the DB/zip locally to the export/import folder.
- External sync or a WebDAV-mounted/exported path can move that file to a server.
- Downstream tools commonly **download the exported SQLite file from WebDAV** and parse it.

Therefore, if P14-005 expects “WebDAV uploads raw SQLite DBs,” that is operationally plausible, but the more accurate statement is:

> Gadgetbridge auto-exports a local SQLite database file; a WebDAV sync layer may then transport that file without transformation.

That distinction matters because parser design should target the SQLite file, not the transport mechanism.

---

## 7) Comparison against P14-005 assumptions

### 7.1 P14-005 assumption: tables

P14-005 assumes these tables:
- `HEART_RATE_SAMPLE`
- `SLEEP_SAMPLE`
- `ACTIVITY_SAMPLE`
- `SPO2_SAMPLE`
- `STRESS_SAMPLE`
- `HRV_SAMPLE`
- `BODY_ENERGY_SAMPLE`
- `DEVICE`

**Reality:** For Xiaomi Gadgetbridge exports, the common real names are more like:
- `MI_BAND_ACTIVITY_SAMPLE`
- `HUAMI_HEART_RATE_MANUAL_SAMPLE`
- `HUAMI_HEART_RATE_MAX_SAMPLE`
- `HUAMI_HEART_RATE_RESTING_SAMPLE`
- `HUAMI_SPO2_SAMPLE`
- `HUAMI_STRESS_SAMPLE`
- `HUAMI_EXTENDED_ACTIVITY_SAMPLE`
- `HUAMI_PAI_SAMPLE`
- `HUAMI_SLEEP_RESPIRATORY_RATE_SAMPLE`
- `DEVICE`

**Assessment:** P14-005 is **not aligned** with the real schema names.

### 7.2 P14-005 assumption: one row per metric type with stable columns

P14-005 assumes direct reads such as:
- `SELECT TIMESTAMP, HEART_RATE FROM HEART_RATE_SAMPLE`
- `SELECT TIMESTAMP, SLEEP_STATE, DURATION FROM SLEEP_SAMPLE`
- `SELECT TIMESTAMP, SPO2 FROM SPO2_SAMPLE`

**Reality:**
- sleep is often embedded in activity rows
- stress and SpO2 have `TYPE_NUM` and may require filtering
- HR can be split across separate tables by semantic subtype
- timestamps can vary by table and unit

**Assessment:** P14-005 over-simplifies the source model.

### 7.3 P14-005 assumption: all timestamps are easy UTC-normalizable integers

**Reality:** timestamps may be seconds or milliseconds depending on table/device; localtime is often applied at analysis time.

**Assessment:** P14-005 needs per-table timestamp handling.

### 7.4 P14-005 assumption: unknown tables/columns can be ignored with warnings

This is a reasonable fallback behavior, but **it must not be used to paper over a wrong schema**. If the parser queries non-existent tables, it should degrade gracefully — but the default schema target must still reflect the real export.

### 7.5 P14-005 assumption: `BODY_ENERGY_SAMPLE` = body battery

**Reality:** Not confirmed from Gadgetbridge Xiaomi schema sources.

**Assessment:** High risk / likely incorrect without a specific source or device table proof.

---

## 8) Xiaomi-specific caveats

1. **Device support varies heavily.** Not every Xiaomi watch writes every table.
2. **Older Huami/Xiaomi devices have unreliable sleep staging.** Deep sleep on old devices is explicitly called out as weak or partially post-processed.
3. **Some features exist in the watch/app UX but not in Gadgetbridge export.** Example: stress, SpO2, and heart rate support are device/model dependent.
4. **Pairing requires vendor app auth token/key first.** This is not directly about schema, but it is a practical prerequisite for getting the export in the first place.
5. **Timestamp units are not uniform across tables.** This is the biggest parser-risk area.
6. **Raw samples often need higher-level interpretation.** For example, stress intervalization and sleep state derivation are downstream analytics tasks, not necessarily direct DB exports.

---

## 9) Practical parser guidance for P14

If P14-005 is implemented against reality, it should:

- Target the real Xiaomi tables first:
  - `MI_BAND_ACTIVITY_SAMPLE`
  - `HUAMI_*` tables as available
- Inspect `sqlite_master` to detect available tables before parsing.
- Read `DEVICE` for device metadata instead of hardcoding a fake device id.
- Handle seconds vs milliseconds by table-specific heuristics.
- Preserve raw sample rows and create normalized output in a second step.
- Treat sleep as possibly encoded in activity rows, not a standalone sleep table.
- Treat HRV/body-battery as derived or unsupported until a concrete table is confirmed.

---

## 10) Conclusion

The real Gadgetbridge export for Xiaomi wearables is a **SQLite database named `Gadgetbridge`** that may be auto-exported locally and then synchronized via WebDAV or another transport. The relevant schema is **table-rich and device-specific**, not the simplified table set assumed by P14-005.

### Bottom line

- **Confirmed:** Gadgetbridge exports SQLite; WebDAV sync pipelines are common; Xiaomi data often lives in `MI_BAND_ACTIVITY_SAMPLE` plus `HUAMI_*` tables.
- **Not confirmed / risky:** `HEART_RATE_SAMPLE`, `SLEEP_SAMPLE`, `SPO2_SAMPLE`, `STRESS_SAMPLE`, `HRV_SAMPLE`, `BODY_ENERGY_SAMPLE` as direct Gadgetbridge Xiaomi table names.
- **Major parser risk:** timestamp-unit mismatch and sleep/HR data not being in the assumed table layout.

**Recommendation:** Treat P14-005 as a normalized-target design, not a direct Gadgetbridge parser, unless it is reworked to match the real schema discovered here.
