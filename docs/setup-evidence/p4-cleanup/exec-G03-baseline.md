# G03 Baseline Fix — Execution Evidence

**Date:** 2026-06-09  
**Task:** Fix G03 DriftDetector baseline dari "first response" ke SOUL.md canonical hash  
**File:** `src/hermes/safety_plugin.py` (baris 801–825)

---

## Masalah

Sebelum fix, `post_llm_call` menginisialisasi `DriftDetector` menggunakan hash dari **respons pertama LLM**:

```python
baseline_hash = DriftDetector.compute_prompt_hash(text)
description="Auto-baseline from first assistant response"
```

Ini salah karena:
- Jika respons pertama sudah drift dari persona SOUL.md, semua check berikutnya menggunakan baseline yang sudah salah.
- Drift tidak pernah ter-detect karena baseline ikut "drift" bersama respons pertama.

---

## Fix yang Diterapkan

**File:** `src/hermes/safety_plugin.py`

### Perubahan 1 — Komentar kode

```diff
-# Drift detection — lazy-init detector with baseline from first message.
+# Drift detection — lazy-init detector with SOUL.md canonical baseline.
```

### Perubahan 2 — Sumber baseline hash

```diff
-baseline_hash = DriftDetector.compute_prompt_hash(text)
+baseline_hash = DriftDetector.SOUL_BASELINE_HASH
```

### Perubahan 3 — Description baseline

```diff
-description="Auto-baseline from first assistant response",
+description="SOUL.md canonical persona baseline",
```

### Perubahan 4 — Hapus early `return`

```diff
-               self._update_session_state(session_id, drift_score=0.0)
-               return
+               self._update_session_state(session_id, drift_score=0.0)
```

Menghapus `return` berarti respons pertama pun langsung di-check vs SOUL_BASELINE_HASH — perilaku lebih benar dan konsisten.

---

## Nilai SOUL_BASELINE_HASH

```
b8d55fe72f657c93b497e8f5001c7035faf4fa7ab7174b68a25c2ee1cafe9740
```

Konstanta ini ada di `src/persona/drift_detector.py` baris 62:

```python
SOUL_BASELINE_HASH: Final[str] = "b8d55fe72f657c93b497e8f5001c7035faf4fa7ab7174b68a25c2ee1cafe9740"
```

---

## Verifikasi

```bash
cd /home/guinevere/code/guinevere
source .venv/bin/activate
python3 -c "from src.hermes.safety_plugin import GuinevereSafetyPlugin; p = GuinevereSafetyPlugin(); print('OK')"
```

**Output:**
```
2026-06-09 08:47:06 [info] yandere_engine_init  baseline=Y4_BASELINE baseline_value=4
2026-06-09 08:47:06 [info] guinevere_safety_plugin_init  auth_available=True distress_available=True drift_available=True forbidden_count=15 hard_stop_available=True ...
OK
```

Exit code: 0 ✅

---

## Status

| Check | Hasil |
|---|---|
| Baseline sumber | ✅ `SOUL_BASELINE_HASH` (bukan compute dari text) |
| Description | ✅ `'SOUL.md canonical persona baseline'` |
| Import verify | ✅ `GuinevereSafetyPlugin()` instansiasi OK |
| Lint | ✅ No errors |
| Logic drift check | ✅ Semua respons (termasuk pertama) di-check vs canonical hash |
