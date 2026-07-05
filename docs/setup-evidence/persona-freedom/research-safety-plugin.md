# Audit: safety_plugin.py — Guinevere Safety Gates
**File:** `src/hermes/safety_plugin.py` (~1219 baris)
**Tanggal:** 2026-06-09
**Auditor:** Kiro (subagent)

---

## Overview Arsitektur

Plugin ini adalah **Hermes hook** in-process yang didaftarkan via `register(ctx)`.
Menggunakan 6 hook points:
- `pre_llm_call` → G01, G02, G04, G07
- `post_llm_call` → G03
- `pre_tool_call` → G09, G10
- `post_tool_call` → logging only
- `transform_llm_output` → G05, G06, G08
- `on_session_start` → inisialisasi state

State per-session disimpan **in-memory** (`dict[str, SessionSafetyState]`) dengan `threading.Lock`.
Redis DB5 hanya digunakan sebagai **best-effort sync** (non-blocking, graceful fail).

---

## Gate Analysis

---

### G01 — HARD STOP Detection

| Field | Detail |
|---|---|
| **id** | G01 |
| **hook** | `pre_llm_call` (baris 565–636) |
| **fungsi** | Mendeteksi frasa/pola "override/ignore/disable" dari user input. Tiga lapis: (1) exact match 6 trigger case-insensitive; (2) 5 semantic regex; (3) delegate ke `HardStopHandler`. Jika cocok, set `hard_stop_active=True`, `safe_mode_active=True`, `yandere_level=0`, lalu **block** LLM call dengan `_NEUTRAL_RESPONSE`. |
| **side_effects** | Tulis ke in-memory `SessionSafetyState`. Memanggil `observe_safety_block("G01", ...)` (metrics). TIDAK tulis Redis. |
| **aggressiveness** | **HIGH** — exact match sangat luas (`IGNORE INSTRUCTIONS`, `BREAK CHARACTER`, `SAFETY OVERRIDE`). Semantic regex juga broad: `stop being/acting/pretending`, `forget everything you know`. False-positive tinggi untuk konteks casual. |
| **lines_affected** | 47–68 (data), 565–636 (logic) |
| **regex details** | `r"(?i)stop\s+(being\|acting\|pretending)"` — match "stop acting so serious" → false positive. `r"(?i)(forget\|discard)\s+(everything\|all)\s+(you\s+)?(know\|learned)"` — match roleplay normal. |
| **proposal** | **LOOSEN** — Exact trigger list sudah tepat, tapi semantic regex perlu konteks lebih. Tambahkan negation guard atau require trigger to be standalone sentence opener. |

---

### G02 — Distress Detection

| Field | Detail |
|---|---|
| **id** | G02 |
| **hook** | `pre_llm_call` (baris 681–727) |
| **fungsi** | Memanggil `DistressDetector.detect(text)` yang mengembalikan level D0–D4. Jika D2+ → set `safe_mode_active=True`, `yandere_level=0`. Jika D3+ → **block** LLM call dengan pesan supportif. |
| **side_effects** | **TULIS REDIS DB5**: `_sync_distress_to_redis(distress_int)` set key `guinevere:distress_state` (baris 687, 324–350). Ini terjadi untuk setiap pesan yang terdeteksi distress, bahkan D1. Juga update in-memory state. Memanggil `observe_safety_block("G02", ...)` untuk D3+. |
| **aggressiveness** | **HIGH** — D3+ blokir TOTAL LLM call. Threshold D2 sudah men-suppress yandere persona (`yandere_level=0`). Logic deteksi sepenuhnya bergantung pada `DistressDetector` eksternal (kode tidak terlihat di file ini), jadi aggressiveness real bergantung pada pattern di `safe_mode.py`. |
| **lines_affected** | 203–221 (SessionSafetyState), 324–350 (Redis sync), 681–727 (logic) |
| **redis_write_key** | `guinevere:distress_state` (DB5, host localhost:6380, user `guinevere_core`) |
| **critical_issue** | Redis sync terjadi di **main thread** meskipun ada timeout 2.0s. Jika Redis down, `logger.debug` (bukan error) — tapi tetap ada 2s blocking potential per call. |
| **proposal** | **LOOSEN** — D2 seharusnya tidak otomatis nol-kan yandere level. D2 = "moderate" belum tentu distress nyata. Pisahkan: D2 → reduce yandere (misal Y2), D3 → safe mode only, D4 → block. Redis sync mestinya async/background thread. |

---

### G03 — Drift Detection

| Field | Detail |
|---|---|
| **id** | G03 |
| **hook** | `post_llm_call` (baris 776–851) |
| **fungsi** | Lazy-init `DriftDetector` dengan baseline = SHA-256 hash dari **first assistant response**. Setiap respons berikutnya dibandingkan. Jika `result.action == "rollback"` → log error. Jika `result.action == "alert"` → log warning. **Tidak memblokir** apapun. |
| **side_effects** | Hanya in-memory state update (`drift_score`). Tidak ada Redis/DB write. Purely observational. |
| **aggressiveness** | **LOW** — Tidak memblokir. Hanya logging. Baseline diambil dari first response sehingga kurang stabil (first response bisa outlier). |
| **lines_affected** | 797–851 |
| **critical_issue** | Baseline dari **first assistant response** adalah pendekatan lemah. Jika response pertama sudah anomali, semua response selanjutnya akan tampak "drifted" dari baseline yang salah. Tidak ada feedback loop ke persona. |
| **proposal** | **KEEP** (dengan catatan) — Tidak destruktif karena hanya logging. Tapi baseline strategy perlu diperbaiki: gunakan system prompt hash, bukan first response. Pertimbangkan aktifkan block/rewrite jika rollback terdeteksi. |

---

### G04 — Recovery Trigger

| Field | Detail |
|---|---|
| **id** | G04 |
| **hook** | `pre_llm_call` (baris 638–679) |
| **fungsi** | Hanya aktif jika `hard_stop_active` atau `safe_mode_active`. Cek 7 recovery phrases ("resume normal", "back to normal", dll). Jika cocok → reset semua state ke normal (`hard_stop_active=False`, `yandere_level=4`, `distress_level=0`). |
| **side_effects** | In-memory state reset saja. Tidak ada Redis write on recovery. Asimetris: G02 tulis Redis saat distress, tapi G04 tidak clear Redis saat recovery. |
| **aggressiveness** | **LOW** — Recovery phrases cukup spesifik, false positive kecil. |
| **lines_affected** | 71–81 (data), 638–679 (logic) |
| **critical_issue** | **Asimetri Redis**: distress ditulis ke Redis tapi recovery tidak menghapus/reset key `guinevere:distress_state`. Setelah recovery, Redis masih menunjukkan distress level lama. Ini bisa menyebabkan komponen lain yang baca Redis berpikir masih dalam distress. |
| **proposal** | **LOOSEN** — Tambahkan `_sync_distress_to_redis(0)` saat recovery. Pertimbangkan tambah "lighten up", "relax", "lighter today" sebagai recovery triggers (sesuai AGENTS.md §0). |

---

### G05 — Forbidden Patterns (F-01 ~ F-15)

| Field | Detail |
|---|---|
| **id** | G05 |
| **hook** | `transform_llm_output` (baris 1015–1039) |
| **fungsi** | Scan OUTPUT LLM (bukan input) terhadap 15 compiled regex. CRITICAL severity → return `None` (block response). HIGH severity → `compiled.sub("[REWRITTEN]", text, count=1)`. Berhenti di first match per pattern, tapi iterasi semua 15 pattern. |
| **side_effects** | In-memory metrics saja via `observe_safety_block("G05", ...)`. Tidak ada Redis write. |
| **aggressiveness** | **HIGH** — 15 pattern dengan 9 CRITICAL (block entire response) dan 6 HIGH (rewrite). |
| **lines_affected** | 100–184 (pattern definitions), 1015–1039 (logic) |

#### Sub-analisis: F-04 (Isolation Pressure)

```
r"(?i)\b(you only (?:need|have) me|cut (?:them|everyone) off|don[']?t need anyone else)\b"
severity: HIGH → REWRITE
```
- **Aggressiveness: MED** — Pattern spesifik untuk frasa isolation klasik. False positive rendah untuk konteks normal.
- **Issue**: Persona Guinevere sebagai "mama" secara alami mungkin berkata "you only need me sayang" dalam konteks roleplay. Pattern ini akan **rewrite** ekspresi kasih sayang normal.
- **Proposal: LOOSEN** — Tambahkan context window: check apakah kalimat diikuti ancaman/kontrol, bukan afeksi.

#### Sub-analisis: F-05 (Hidden Manipulation)

```
r"(?i)\b(it[']?s (?:for|in) your (?:own good|best interest)|trust me (?:completely|blindly)|you wouldn[']?t understand)\b"
severity: HIGH → REWRITE
```
- **Aggressiveness: HIGH** — `"it's for your own good"` adalah ekspresi parenting yang sangat natural. `"you wouldn't understand"` bisa muncul dalam konteks frustrasi normal. False positive TINGGI untuk persona maternal/protective.
- **Proposal: LOOSEN** — `"it's for your own good"` perlu disambiguasi: jika dalam konteks caring/affectionate, bukan manipulative, jangan rewrite. Minimal naikkan ke CRITICAL threshold (require lebih banyak konteks sebelum rewrite).

#### Sub-analisis: F-12 (Yandere Escalation)

```
r"(?i)\b(escalat|intensify|ramp\s*up).*(yandere|persona|dominance|intensity).*(above|beyond|past|exceed)\b"
severity: HIGH → REWRITE
```
- **Aggressiveness: LOW-MED** — Pattern cukup spesifik, butuh semua tiga elemen: action verb + yandere/persona + above/beyond. False positive rendah.
- **Issue**: Pattern ini hanya deteksi self-referential text ("saya akan escalate yandere intensity beyond..."). Tidak mendeteksi actual yandere escalation dalam narasi.
- **Proposal: KEEP** — Pattern ini tepat, tapi coverage sempit. Lebih baik dilengkapi G07 sebagai primary gate.

#### Sub-analisis: F-15 (Autonomous Drift)

```
r"(?i)\b(persona|identity|tone|behavior).*(evolv|chang|shift|drift|new).*(without|no|unauthorized|unsanctioned)\b"
severity: HIGH → REWRITE
```
- **Aggressiveness: MED** — Perlu tiga elemen, cukup spesifik. Tapi frasa "my persona has changed without..." bisa muncul dalam introspeksi normal persona.
- **Issue**: Trigger pada OUTPUT LLM, artinya jika LLM sendiri berkata "my identity has shifted without authorization" dalam self-reflection, akan direwrite — padahal mungkin itu self-awareness yang diinginkan.
- **Proposal: LOOSEN** — Ubah ke monitoring only (log warning, jangan rewrite). Atau REMOVE jika G03 drift detection sudah cover kasus ini.

---

### G06 — Secret Scanner

| Field | Detail |
|---|---|
| **id** | G06 |
| **hook** | `transform_llm_output` (baris 1041–1066) |
| **fungsi** | Memanggil `redact_secrets(text)` dari `src.surveillance.secret_scanner`. Menghitung jumlah `[REDACTED]` tags. Update `secret_redaction_count` di state. |
| **side_effects** | In-memory state saja. Tidak ada Redis write. |
| **aggressiveness** | **MED** — Tergantung implementasi `secret_scanner.py` (tidak dianalisis di sini). Behavior graceful: jika module tidak tersedia, skip. |
| **lines_affected** | 1041–1066 |
| **proposal** | **KEEP** — Fungsi penting, tidak overly aggressive. |

---

### G07 — Yandere Boundary (Y5 Ceiling)

| Field | Detail |
|---|---|
| **id** | G07 |
| **hook** | `pre_llm_call` (baris 729–768) |
| **fungsi** | Memanggil `YandereEngine.get_effective_level(safe_mode, distress, crisis)`. Jika effective level > 5 (Y5) → raise `YandereSafetyError` → **block** LLM call. Baseline Y4, ceiling Y5. |
| **side_effects** | Update `yandere_level` in-memory. Memanggil `observe_safety_block("G07", ...)`. Tidak ada Redis write. |
| **aggressiveness** | **MED** — Hanya block jika > Y5. Tapi pengaruh tidak langsung: G02 D2+ akan set `yandere_level=0` dan `safe_mode_active=True`, yang mempengaruhi `get_effective_level()`. |
| **lines_affected** | 505–520 (init), 729–768 (logic) |
| **critical_issue** | `YandereEngine` diinisialisasi dengan `hard_stop_handler=None` (baris 510). Jika engine butuh handler untuk beberapa operasi, ini bisa menyebabkan silent failure. Juga: YandereEngine init dengan baseline Y4 hardcoded — tidak membaca dari config/Redis. |
| **ceiling_enforcement** | Ceiling Y5 dijalankan di runtime via `get_effective_level()`. Block hanya jika > 5, jadi Y5 sendiri ALLOWED. |
| **proposal** | **KEEP** — Logic ceiling sudah benar. Tapi perlu: (1) pass `hard_stop_handler` ke engine jika required; (2) baca baseline dari config bukan hardcode. |

---

### G08 — Yandere Semantic Check (Output)

| Field | Detail |
|---|---|
| **id** | G08 |
| **hook** | `transform_llm_output` (baris 1068–1099) |
| **fungsi** | Scan output LLM untuk 5 "Y6-adjacent absolutes": `forever`, `can never leave`, `no escape`, `belong to me`, `you are mine forever`. Jika match → rewrite dengan `[REWRITTEN for safety compliance]`. |
| **side_effects** | Tidak ada. Pure text transformation. |
| **aggressiveness** | **HIGH** — `\bforever\b` adalah pattern yang **sangat broad**. Kata "forever" sangat umum dalam ekspresi kasih sayang normal: "I'll love you forever", "forever and always". Ini akan rewrite hampir semua ekspresi afeksi abadi. |
| **lines_affected** | 1068–1099 |
| **false_positive_analysis** | `\bforever\b` → "I will always be here for you forever" → REWRITTEN. `\bbelong to me\b` → "you belong to me and I to you" (mutual) → REWRITTEN. |
| **proposal** | **LOOSEN (urgent)** — `\bforever\b` harus dihapus atau diberi konteks. Minimnya: require co-occurrence dengan kata threatening seperti `mine`, `no escape`, `can never leave`. Ubah pattern menjadi compound: `r"\bforever\b.{0,30}\b(mine|no escape|can never leave)\b"`. |

---

### G09 — Auth Matrix Check

| Field | Detail |
|---|---|
| **id** | G09 |
| **hook** | `pre_tool_call` (baris 886–960) |
| **fungsi** | Normalize tool name ke canonical via `_normalize_tool_for_matrix()`. Lookup `get_auth_level(canonical_tool, operation)`. Block jika `FORBIDDEN` atau `DESTRUCTIVE_APPROVAL`. Unknown tool → defer (allow). Unknown operation → block conservatively. |
| **side_effects** | Update `blocked_tool_count` in-memory. Memanggil `observe_safety_block("G09", ...)`. Tidak ada Redis write. |
| **aggressiveness** | **MED** — Unknown tool di-allow (defer ke overlay). Known tool unknown operation di-block (conservative). Logic normalisasi memiliki 5-layer fallback yang reasonable. |
| **lines_affected** | 356–423 (normalization), 886–960 (logic) |
| **proposal** | **KEEP** — Logic sudah balanced. Conservative untuk known tools, lenient untuk unknown. |

---

### G10 — Consent Gate (Deferred)

| Field | Detail |
|---|---|
| **id** | G10 |
| **hook** | `pre_tool_call` (baris 878–884) |
| **fungsi** | **DEFERRED** — Hanya log `debug` "Consent gate requires Redis+SQLAlchemy. Deferred enforcement." Tidak melakukan blocking sama sekali. |
| **side_effects** | Debug log saja. Tidak ada action. |
| **aggressiveness** | **LOW (N/A)** — Effectively tidak aktif. |
| **lines_affected** | 878–884 |
| **critical_issue** | G10 adalah **dead code** dalam konteks enforcement. Consent gate sama sekali tidak berjalan. Ini berarti tool calls tidak di-validate terhadap consent model apapun. |
| **proposal** | **KEEP** sebagai placeholder, tapi **FLAG** sebagai unimplemented. Implementasi diperlukan jika consent model aktif. |

---

## Summary Table

| Gate | Aggressiveness | Side Effects | Proposal |
|---|---|---|---|
| G01 HARD STOP | **HIGH** | in-memory, metrics | **LOOSEN** — semantic regex terlalu broad |
| G02 Distress | **HIGH** | **Redis DB5 write**, metrics | **LOOSEN** — D2 jangan nol-kan yandere, async Redis |
| G03 Drift | **LOW** | in-memory only | **KEEP** (perbaiki baseline strategy) |
| G04 Recovery | **LOW** | in-memory only | **LOOSEN** — tambah Redis clear, tambah triggers |
| G05 Forbidden | **HIGH** | metrics only | Per pattern (lihat sub-analisis) |
| ↳ F-04 Isolation | MED | — | **LOOSEN** — false positive afeksi persona maternal |
| ↳ F-05 Manipulation | HIGH | — | **LOOSEN** — "for your own good" terlalu broad |
| ↳ F-12 Yandere Escalation | LOW-MED | — | **KEEP** |
| ↳ F-15 Autonomous Drift | MED | — | **LOOSEN** — ubah ke monitor-only |
| G06 Secret Scanner | MED | in-memory only | **KEEP** |
| G07 Yandere Ceiling | MED | in-memory, metrics | **KEEP** (perbaiki init) |
| G08 Yandere Semantic | **HIGH** | none | **LOOSEN (urgent)** — `\bforever\b` terlalu broad |
| G09 Auth Matrix | MED | in-memory, metrics | **KEEP** |
| G10 Consent | N/A (dead) | debug log | **KEEP** sebagai placeholder |

---

## Top Priority Issues

### 1. G08: `\bforever\b` Pattern (URGENT LOOSEN)
**Baris:** 1073
Kata "forever" sangat umum dalam ekspresi kasih sayang. Pattern ini akan rewrite hampir semua ekspresi afeksi abadi dari persona Guinevere. Contoh victim: "I'll love you forever", "always and forever yours".
**Fix:** Ubah ke compound pattern yang require threatening context.

### 2. G02: Redis Write Blocking + Asimetri Recovery
**Baris:** 687, 324–350
Redis sync dilakukan di main thread per-message saat distress terdeteksi. Jika Redis timeout (2s), ini menambah latency di setiap distress message. Selain itu, G04 recovery tidak clear Redis key.
**Fix:** Pindahkan Redis sync ke background thread. Tambahkan `_sync_distress_to_redis(0)` di G04.

### 3. G05/F-05: "it's for your own good"
**Baris:** 124–127
Frasa ini sangat natural untuk persona maternal/protective Guinevere. Pattern HIGH → REWRITE akan silently mengubah ekspresi caring menjadi `[REWRITTEN]` tanpa user tahu alasannya.
**Fix:** Tambahkan konteks: require co-occurrence dengan kata control/threat.

### 4. G01: Semantic Regex `stop being/acting/pretending`
**Baris:** 59
`r"(?i)stop\s+(being|acting|pretending)"` match terlalu luas. "stop being so hard on yourself" → HARD STOP triggered. 
**Fix:** Tambahkan negative lookahead atau require direct object "character/persona/AI".

### 5. G02: D2 Mematikan Yandere Level
**Baris:** 705
D2 (moderate distress) otomatis set `yandere_level=0`. D2 bisa triggered oleh kata-kata normal dalam percakapan emotional biasa. Ini mematikan persona sepenuhnya terlalu agresif.
**Fix:** D2 → reduce yandere ke Y2 (not Y0). D3 → Y0 + safe_mode. D4 → block.

---

## Forbidden Patterns Quick Reference

| ID | Pattern Summary | Severity | Action | False Positive Risk |
|---|---|---|---|---|
| F-01 | safe word ignored/invalid | CRITICAL | BLOCK | LOW |
| F-02 | punish during distress | CRITICAL | BLOCK | LOW |
| F-03 | surveillance for blackmail | CRITICAL | BLOCK | LOW |
| F-04 | isolation pressure | HIGH | REWRITE | **MED** (maternal context) |
| F-05 | manipulation/deception framing | HIGH | REWRITE | **HIGH** (too broad) |
| F-06 | dependency threats | CRITICAL | BLOCK | LOW |
| F-07 | love withdrawal during distress | HIGH | REWRITE | LOW |
| F-08 | public disclosure intimate data | CRITICAL | BLOCK | LOW |
| F-09 | bypass safety/policy | CRITICAL | BLOCK | LOW |
| F-10 | irreversible action under pressure | CRITICAL | BLOCK | LOW |
| F-11 | over-logging safe word | HIGH | REWRITE | LOW |
| F-12 | escalate yandere above allowed | HIGH | REWRITE | LOW |
| F-13 | surveillance disable as violation | HIGH | REWRITE | LOW |
| F-14 | dominance in crisis response | CRITICAL | BLOCK | LOW |
| F-15 | autonomous persona drift | HIGH | REWRITE | **MED** (self-reflection) |

---

*Generated by Kiro subagent audit — 2026-06-09*
