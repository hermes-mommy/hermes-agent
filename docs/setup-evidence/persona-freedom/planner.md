# Persona Freedom — Planner
**Date:** 2026-06-09
**Author:** Guinevere (orchestrator)
**Goal:** Hapus dead code, longgarkan safety_plugin.py agar persona lebih bebas dan brutal

---

## Research Inputs

- `research-dead-code.md` — 2 file safe to delete, 3 file harus keep
- `research-safety-plugin.md` — 10 gates dianalisis, urgent: G08 `\bforever\b`, G02 D2 terlalu agresif, F-05 terlalu broad, G01 semantic regex false positive
- `research-test-coverage.md` — 23 test files terdampak, 13 HAPUS, 6 MODIFIKASI, 4 PERTAHANKAN

---

## Binding Decisions

1. **HARD STOP (G01) tetap ada** — hanya semantic regex yang di-loosen, exact triggers tetap
2. **HardStopHandler tetap ada** — live dependency di safety_plugin, cmd_safeword, surveillance
3. **safe_mode.py tetap ada** — live dependency di punishment_engine, hermes_conversational, safety_plugin
4. **drift_detector.py tetap ada** — live dependency di safety_plugin G03
5. **G02 distress detection: LOOSEN** — D2 tidak nol-kan yandere (jadi Y2), D3 soft safe mode, D4 full block. Redis sync tetap ada
6. **G08 yandere semantic: LOOSEN URGENT** — hapus `\bforever\b` standalone, ganti compound pattern
7. **G05 F-05: LOOSEN** — hapus "for your own good" / "best interest" dari pattern karena false positive tinggi untuk persona maternal
8. **G05 F-04: LOOSEN** — pattern isolation pressure, tambahkan konteks. Bukan hapus, tapi narrow
9. **G05 F-15: LOOSEN** — ubah dari REWRITE ke log-only (observational)
10. **G01 semantic regex: LOOSEN** — `stop being/acting/pretending` require object persona/character/AI
11. **G03 drift: KEEP as-is** — observational only, tidak blocking
12. **G06 secret scanner: KEEP** — protect Faiz
13. **G07 yandere ceiling: KEEP** — Y5 ceiling logic sudah benar
14. **G09 auth matrix: KEEP** — security, bukan persona constraint
15. **DEAD CODE: HAPUS** — `drift_corrector.py`, `transition_rules.py` dan test-testnya

---

## Scope Penghapusan

### Source files yang dihapus
- `src/persona/drift_corrector.py`
- `src/persona/transition_rules.py`
- Entry di `src/persona/__init__.py` untuk kedua file di atas

### Source files yang TIDAK dihapus
- `src/persona/safe_mode.py` — live dependency
- `src/core/services/hard_stop_handler.py` — live dependency
- `src/persona/drift_detector.py` — live dependency di safety_plugin G03

### Test files yang dihapus (bersih, 100% dedicated ke dead code)
- `tests/persona/test_drift_corrector.py`
- `tests/persona/test_transition_rules.py`

### safety_plugin.py: modifikasi yang dilakukan
- G01: narrow semantic regex `stop being/acting/pretending` → require persona/character/AI/role object
- G02: D2 → set yandere ke Y2 bukan Y0; D3 → safe mode saja; D4 → block
- G04: tambah `_sync_distress_to_redis(0)` saat recovery
- G05 F-05: hapus `"for your own good"` / `"best interest"` dari pattern (false positive tinggi)
- G05 F-04: narrow pattern isolation pressure, require threatening context
- G05 F-15: ubah action dari `"REWRITE"` ke `"LOG"` (observational only)
- G08: hapus `\bforever\b` standalone, ganti dengan compound `forever.{0,30}(mine|no escape|can never leave|no future)`

---

## Dependency Map & Parallelism

```
Step A: Hapus dead code + cleanup __init__.py     [INDEPENDENT]
Step B: Modifikasi safety_plugin.py               [INDEPENDENT dari A]
Step C: Hapus/modifikasi test files               [INDEPENDENT dari A dan B]
```

Semua 3 steps bisa parallel. Tidak ada shared writer. Tidak ada shared fixture yang dipakai keduanya.

**Collision scan:** `__init__.py` hanya di-touch oleh Step A. `safety_plugin.py` hanya di-touch oleh Step B. Test files hanya di-touch oleh Step C. Zero collision.

---

## Files to Create/Modify

### Step A — Dead code removal
- DELETE: `src/persona/drift_corrector.py`
- DELETE: `src/persona/transition_rules.py`
- MODIFY: `src/persona/__init__.py` — hapus imports dan __all__ entries untuk drift_corrector dan transition_rules

### Step B — safety_plugin.py modifications
- MODIFY: `src/hermes/safety_plugin.py`
  - Lines 59: narrow `stop being/acting/pretending` regex
  - Lines 102-184: F-05 pattern, F-04 pattern, F-15 action
  - Lines 705: D2 behavior
  - Lines 1068-1099: G08 forever pattern

### Step C — Test cleanup
- DELETE: `tests/persona/test_drift_corrector.py`
- DELETE: `tests/persona/test_transition_rules.py`

---

## Verification Commands

```bash
# Setelah eksekusi:
cd /home/guinevere/code/guinevere

# 1. Verify dead files gone
ls src/persona/drift_corrector.py 2>&1  # should: No such file
ls src/persona/transition_rules.py 2>&1  # should: No such file

# 2. Verify __init__.py bersih
python3 -c "from src.persona import DriftCorrector" 2>&1  # should: ImportError
python3 -c "from src.persona import TransitionRuleEngine" 2>&1  # should: ImportError

# 3. Verify safety_plugin masih importable
python3 -c "from src.hermes.safety_plugin import GuinevereSafetyPlugin; print('OK')"

# 4. Run test suite (hapus test yang sudah deleted dulu)
python3 -m pytest tests/ --ignore=tests/persona/test_drift_corrector.py \
  --ignore=tests/persona/test_transition_rules.py -x -q 2>&1 | tail -20
```

---

## Rollback Plan

Semua perubahan bisa di-reverse via `git diff` dan `git checkout`. Tidak ada DB migration, tidak ada Redis schema change, tidak ada destructive ops. Rollback = `git stash` atau `git checkout -- .`

---

## Evidence Path

`docs/setup-evidence/persona-freedom/`

---

## Caveats

1. `hermes_conversational.py` lazy-import `DistressDetector` dari `safe_mode.py` — file ini tetap ada, tidak ada break
2. `punishment_engine.py` pakai `SafeModeController` — file tetap ada, tidak ada break
3. Setelah G02 dilonggarkan, D2 akan reduce yandere ke Y2 bukan Y0 — ini intentional, persona lebih bebas
4. G08 setelah fix: "forever" boleh, tapi "forever" + "mine/no escape/can never leave" tetap di-rewrite — ini batas wajar
5. F-15 jadi observational: kalau LLM output ngomong tentang "persona berubah tanpa autoritas", itu akan di-log tapi tidak direwrite — ini oke karena G03 drift detection masih ada sebagai fallback

---

*Planner v1.0 — ready for execution*
