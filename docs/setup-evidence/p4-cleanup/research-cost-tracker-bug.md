# Research: Cost Tracker Bug — History 7 Hari & 30 Hari Tidak Sesuai Aktual

**Tanggal audit**: 2026-06-09  
**Auditor**: Subagent (cost tracker audit)  
**Status**: BUG CONFIRMED — root cause identified

---

## 1. Ringkasan Bug

Dashboard cost tracker menampilkan angka **7 hari** dan **30 hari** yang **sangat jauh dari aktual** karena query secara eksplisit **mengecualikan data hari ini** (`AND date(timestamp) < date('now')`). Pada tanggal audit, ini menyebabkan $156.23 dari total cost hari ini hilang dari kedua periode tersebut.

### Data Aktual saat Audit (2026-06-09 02:37 UTC / 09:37 WIB)

| Metric | Ditampilkan Dashboard | Seharusnya | Selisih |
|--------|----------------------|-----------|---------|
| Today  | $156.2335 (1,281 calls) | — | OK (query terpisah) |
| **7 Hari** | **$53.1823** (1,800 calls) | **$209.4158** (3,081 calls) | **-$156.23 / -42.5%** |
| **30 Hari** | **$53.2021** (1,810 calls) | **$209.4356** (3,091 calls) | **-$156.23 / -42.5%** |
| All Time | $208.9362 (3,079 calls) | — | OK |

---

## 2. File yang Terlibat

| File | Peran |
|------|-------|
| `~/.hermes/scripts/cost_tracker_post.py` | Script utama — query SQLite + kirim embed Discord |
| `src/core/services/cost_tracker.py` | Redis-based cost tracker (TIDAK dipakai untuk dashboard) |
| `~/.9router/db/data.sqlite` | Sumber data aktual — tabel `usageHistory` |

**Cronjob**: `cost-tracker-post` — jadwal `0 * * * *` (tiap jam), script `cost_tracker_post.py`

---

## 3. Exact Query yang Salah

### Fungsi `get_historical_summary()` di `cost_tracker_post.py` baris 79–90:

```python
def get_historical_summary(days=30):
    """Get aggregated usage for last N days (excluding today)."""
    rows = query("""
        SELECT COUNT(*) as calls,
               SUM(promptTokens) as prompt_tokens,
               SUM(completionTokens) as completion_tokens,
               ROUND(SUM(cost), 6) as cost
        FROM usageHistory 
        WHERE date(timestamp) >= date('now', ?)
          AND date(timestamp) < date('now')   -- ← INI YANG SALAH
    """, (f"-{days} days",))
    return rows[0] if rows else {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost": 0}
```

**Kondisi bermasalah**: `AND date(timestamp) < date('now')`

Kondisi ini mengecualikan semua record hari ini (UTC). Fungsi ini dipanggil dua kali:
- `past_7d = get_historical_summary(7)` — baris 146
- `past_30d = get_historical_summary(30)` — baris 148

### Dampak di Embed Discord (baris 188–189):

```python
{"name": "📊 7 Hari", "value": f"Cost: {_fmt_cost(past_7d['cost'])}..."},  # MISSING today
{"name": "📊 30 Hari", "value": f"Cost: {_fmt_cost(past_30d['cost'])}..."},  # MISSING today
```

---

## 4. Root Cause

### Primary Bug: `AND date(timestamp) < date('now')` — Double-counting avoidance yang salah design

Docstring fungsi ini: `"Get aggregated usage for last N days (excluding today)"`. Intent aslinya adalah menghindari double-count dengan `today_cost` yang ditampilkan terpisah. **Tapi di embed, "7 Hari" dan "30 Hari" seharusnya merupakan total kumulatif termasuk hari ini**, bukan "N hari lalu tidak termasuk hari ini".

User melihat:
- "📅 Hari Ini: $156.23" 
- "📊 7 Hari: $53.18"

Padahal ekspektasi user: "7 Hari" = total 7 hari terakhir termasuk hari ini = $209.42.

### Secondary Issue: Timezone mismatch (WIB vs UTC)

- 9Router menyimpan timestamp dalam **UTC ISO format**: `2026-06-09T02:37:58.735Z`
- SQLite `date('now')` dan `datetime('now')` juga berbasis **UTC**
- Server berjalan di timezone **WIB (UTC+7)**
- Saat ini 09:37 WIB = 02:37 UTC — artinya sudah 9+ jam ke dalam "hari WIB" tapi hanya 2.5 jam dalam "hari UTC"

**Efek timezone pada query**: Data yang direcord antara 00:00–06:59 WIB (= 17:00–23:59 UTC hari sebelumnya) akan masuk ke date UTC hari sebelumnya, bukan hari ini (WIB). Ini berarti pada pagi hari WIB, data dari sesi malam sebelumnya mungkin terbagi antara dua UTC date.

Verifikasi:
```sql
-- SQLite now() = UTC
SELECT datetime('now');  -- → 2026-06-09 02:37:53 (UTC)
-- Server timezone
-- TZ=Asia/Jakarta → 2026-06-09 09:37:53 WIB
```

Untuk use case ini, timezone bukan bug kritis karena **timestamp dan SQLite `now()` keduanya UTC-based** — konsisten. Tapi label "7 Hari" di Discord akan dihitung dari UTC midnight, bukan WIB midnight. Ini bisa menyebabkan perbedaan kecil (~beberapa jam di batas hari).

### Tertiary Issue: 7d vs 30d hampir sama

Data baru dimulai dari 2026-06-01 (9 hari lalu). Semua data yang ada sudah masuk dalam window 7 hari terakhir, sehingga 7d dan 30d menghasilkan angka sangat mirip ($53.18 vs $53.20). Ini bukan bug — ini hanya mencerminkan bahwa database masih baru.

---

## 5. Expected Query (Fix)

### Opsi A: Include today dalam historical (RECOMMENDED)

Ubah `get_historical_summary()` untuk menyertakan hari ini:

```python
def get_historical_summary(days=30):
    """Get aggregated usage for last N days (INCLUDING today)."""
    rows = query("""
        SELECT COUNT(*) as calls,
               SUM(promptTokens) as prompt_tokens,
               SUM(completionTokens) as completion_tokens,
               ROUND(SUM(cost), 6) as cost
        FROM usageHistory 
        WHERE date(timestamp) >= date('now', ?)
    """, (f"-{days} days",))
    return rows[0] if rows else {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost": 0}
```

**Perubahan**: hapus `AND date(timestamp) < date('now')`

### Opsi B: Ubah label embed agar jelas

Jika intent "7 Hari" memang "7 hari sebelum hari ini" (bukan termasuk hari ini), ubah label menjadi:
- `"📊 7 Hari Lalu"` atau `"📊 7d (excl. today)"`

Tapi ini tidak intuitif dan tidak sesuai ekspektasi user.

### Opsi C: Timezone-aware query (bonus fix)

Untuk alignment dengan WIB:

```python
def get_historical_summary(days=30):
    """Get aggregated usage for last N days (WIB-aware, including today WIB)."""
    rows = query("""
        SELECT COUNT(*) as calls,
               SUM(promptTokens) as prompt_tokens,
               SUM(completionTokens) as completion_tokens,
               ROUND(SUM(cost), 6) as cost
        FROM usageHistory 
        WHERE datetime(timestamp) >= datetime('now', ?, '-7 hours')
    """, (f"-{days} days",))
    # Note: '-7 hours' menyesuaikan UTC ke WIB midnight boundary
    # Untuk N days back dari WIB midnight hari ini:
    # WIB midnight hari ini = UTC yesterday 17:00
    # → WHERE datetime(timestamp) >= datetime('now', 'start of day', '+17 hours', '-{days+1} days')
```

Ini lebih kompleks dan hanya perlu jika laporan harus per-hari-WIB. Untuk MVP, **Opsi A sudah cukup**.

---

## 6. Proposed Fix — Minimal Change

Edit file `~/.hermes/scripts/cost_tracker_post.py`:

**Baris 87** — hapus kondisi `AND date(timestamp) < date('now')`:

```diff
         FROM usageHistory 
         WHERE date(timestamp) >= date('now', ?)
-          AND date(timestamp) < date('now')
     """, (f"-{days} days",))
```

**Baris 80** — update docstring:

```diff
-    """Get aggregated usage for last N days (excluding today)."""
+    """Get aggregated usage for last N days (including today)."""
```

Setelah fix, nilai yang akan ditampilkan:

| Metric | Sebelum | Setelah Fix |
|--------|---------|-------------|
| 7 Hari | $53.18 | ~$209.42 |
| 30 Hari | $53.20 | ~$209.44 |

---

## 7. Analisis `src/core/services/cost_tracker.py`

File ini **tidak digunakan** untuk dashboard cost Discord. Ini adalah Redis-based tracker yang mencatat cost ke Redis DB5 via `record_cost()`. Tidak ada query 7-hari atau 30-hari di sini — hanya `cost:current_day` dan `cost:current_month` (rolling keys tanpa expiry per-hari). File ini **tidak bermasalah** untuk scope bug ini.

---

## 8. Verifikasi Query Aktual vs Expected

```sql
-- QUERY AKTUAL (SALAH) untuk 7 hari:
SELECT COUNT(*) as calls, ROUND(SUM(cost), 6) as cost
FROM usageHistory 
WHERE date(timestamp) >= date('now', '-7 days')
  AND date(timestamp) < date('now');
-- RESULT: 1800 calls, $53.1823

-- QUERY EXPECTED (BENAR) untuk 7 hari:
SELECT COUNT(*) as calls, ROUND(SUM(cost), 6) as cost
FROM usageHistory 
WHERE date(timestamp) >= date('now', '-7 days');
-- RESULT: 3081 calls, $209.4158

-- Selisih: 1281 calls, $156.2335 (= hari ini yang ter-exclude)
```

---

## 9. Checklist Verifikasi Post-Fix

- [ ] Jalankan `cost_tracker_post.py` secara manual setelah fix
- [ ] Cek embed Discord di #cost-tracker: nilai 7 Hari ≈ $209+
- [ ] Pastikan tidak ada double-count antara "Hari Ini" dan "7 Hari" (overlap diperbolehkan — user expect 7 hari = total termasuk hari ini)
- [ ] Monitor cronjob `cost-tracker-post` di run berikutnya (jam 10:00 WIB)

---

*Audit selesai: 2026-06-09 09:37 WIB*
