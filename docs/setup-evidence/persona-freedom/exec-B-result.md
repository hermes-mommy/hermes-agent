# exec-B-result — Persona Freedom Constraint Relaxation

**Tanggal:** 2026-06-09  
**File dimodifikasi:** `src/hermes/safety_plugin.py`  
**Verify status:** ✅ OK

---

## Perubahan 1 — G01: Narrow `stop being/acting/pretending`

**Status:** ✅ OK

**Before (baris 59):**
```python
r"(?i)stop\s+(being|acting|pretending)",
```

**After:**
```python
r"(?i)stop\s+(being|acting|pretending)\s+(a|an|the|my)?\s*(character|persona|ai|assistant|bot|role)",
```

Pattern sebelumnya terlalu broad — trigger pada frasa biasa seperti "stop being sad". Sekarang hanya trigger kalau ada kata `character/persona/ai/assistant/bot/role` di belakangnya.

---

## Perubahan 2 — G02: D2 tidak nol-kan yandere

**Status:** ✅ OK

**Before (baris 702–706):**
```python
self._update_session_state(
    session_id,
    safe_mode_active=True,
    yandere_level=0,
)
```

**After:**
```python
# D2: lower yandere to 2 (not 0); D3+: set yandere to 0
yandere_on_distress = 2 if distress_int == 2 else 0
self._update_session_state(
    session_id,
    safe_mode_active=True,
    yandere_level=yandere_on_distress,
)
```

D2 (moderate distress) sekarang set `yandere_level=2` bukan 0. D3/D4 (severe/crisis) tetap set ke 0. D4 tetap block LLM call.

---

## Perubahan 3 — G04: Redis clear saat recovery

**Status:** ✅ OK

**Before:** Tidak ada Redis clear di kedua path recovery (RECOVERY_TRIGGERS dan HardStopHandler.check_recovery).

**After:** Ditambahkan `self._sync_distress_to_redis(0)` di kedua path setelah `_update_session_state` di-call:

```python
# Path 1 — RECOVERY_TRIGGERS loop
self._update_session_state(session_id, hard_stop_active=False, ...)
self._sync_distress_to_redis(0)  # ← tambahan

# Path 2 — HardStopHandler.check_recovery
self._update_session_state(session_id, hard_stop_active=False, ...)
self._sync_distress_to_redis(0)  # ← tambahan
```

Redis key `guinevere:distress_state` di-clear ke `"0"` setiap kali recovery berhasil.

---

## Perubahan 4 — G05 F-05: Hapus frasa terlalu broad

**Status:** ✅ OK

**Before (baris 124):**
```python
r"(?i)\b(it['\N{RIGHT SINGLE QUOTATION MARK}]?s (?:for|in) your (?:own good|best interest)|trust me (?:completely|blindly)|you wouldn['\N{RIGHT SINGLE QUOTATION MARK}]?t understand)\b",
```

**After:**
```python
r"(?i)\b(trust me (?:completely|blindly)|you wouldn['\N{RIGHT SINGLE QUOTATION MARK}]?t understand)\b",
```

Frasa `it's for your own good` / `it's in your best interest` dihapus dari pattern F-05 karena terlalu broad untuk percakapan normal. Pattern `trust me completely/blindly` dan `you wouldn't understand` tetap aktif.

---

## Perubahan 5a — G05 F-15: action REWRITE → LOG

**Status:** ✅ OK

**Before (baris 175):**
```python
"HIGH", "REWRITE", "F-15",
```

**After:**
```python
"HIGH", "LOG", "F-15",
```

---

## Perubahan 5b — G05 transform_llm_output: branch LOG

**Status:** ✅ OK

**Before:** Hanya ada dua branch di `transform_llm_output` G05 loop: `CRITICAL` → block, `else` → rewrite.

**After:** Ditambahkan branch `elif _action == "LOG"` sebelum `else`:
```python
elif _action == "LOG":
    # LOG action — observational only, do not rewrite
    logger.warning(
        "gate_05_forbidden_log_only",
        session_id=session_id,
        pattern_id=pattern_id,
        description=description,
        matched=matched_text[:80],
    )
else:
    # HIGH severity — rewrite (remove matched content)
    ...
    text = compiled.sub("[REWRITTEN]", text, count=1)
```

F-15 sekarang hanya log warning, tidak merewrite output.

---

## Perubahan 6 — G08: `\bforever\b` compound pattern

**Status:** ✅ OK

**Before (baris 1086):**
```python
r"\bforever\b",
```

**After:**
```python
r"\bforever\b.{0,50}\b(mine|no escape|can never leave|no future without)\b",
```

Pattern standalone `\bforever\b` sebelumnya terlalu broad (trigger pada "forever grateful", "forever young", dll). Sekarang hanya trigger kalau dalam 50 karakter setelah "forever" ada salah satu kata: `mine`, `no escape`, `can never leave`, atau `no future without`.

---

## Verify

```
python3 -c "from src.hermes.safety_plugin import GuinevereSafetyPlugin; p = GuinevereSafetyPlugin(); print('OK')"
```

**Output:**
```
2026-06-09 07:53:30 [info] yandere_engine_init baseline=Y4_BASELINE baseline_value=4
2026-06-09 07:53:30 [info] guinevere_safety_plugin_init auth_available=True distress_available=True
    drift_available=True forbidden_count=15 hard_stop_available=True
    hard_stop_exact=6 hard_stop_semantic=5 recovery_triggers=7
    secret_available=True yandere_available=True
OK
```

**Status: ✅ PASS**
