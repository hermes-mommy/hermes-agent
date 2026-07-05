# Research M-02: Drift Validation Cadence (ADR-003)

**Date**: 2026-06-09  
**Researcher**: Sub-agent (delegated from Guinevere parent)  
**Finding ID**: M-02  
**Finding summary**: Tidak ada drift validation cadence (ADR-003: per-loop lightweight + periodic deep validation)

---

## 1. ADR-003 — Requirement yang Tepat

**File**: `/home/guinevere/code/guinevere/adr/ADR-003-persona-drift-control-validation.md`  
**Status**: Accepted with notes  
**Risk Level**: HIGH

ADR-003 menetapkan dua requirement utama untuk drift validation cadence (dari section **Review Record → Notes**):

> **Validation cadence:** Specify per-loop lightweight validation + periodic deep validation (e.g., every 100 interactions or daily). Deep validation uses sub-agent per ADR-012 file-based output rules.

Requirement yang tertera:

| Cadence | Tipe | Trigger | Mekanisme |
|---------|------|---------|-----------|
| Per-loop lightweight | Syncron, setiap conversation loop | Setiap respons LLM | Cek invariant kritis: safe word responsif, yandere cap, punishment ladder bounds |
| Periodic deep | Async, terjadwal | Setiap N loop atau M menit (contoh: 100 interaksi atau harian) | Full drift detection: hash comparison, behavioral analysis, sub-agent (file-based output per ADR-012) |

ADR-003 juga mensyaratkan:
- Drift log schema di `persona_drift_logs` dengan field: `timestamp`, `drift_vector`, `trigger`, `reviewer`, `action`
- Rollback ke last known-good persona snapshot (bukan hard baseline reset)
- Rollback trigger: automated threshold breach, Faiz request, atau auditor flag

---

## 2. Apakah Ada Scheduler/Cron yang Memanggil Drift Detection Sekarang?

### Cron di `hermes-config/config.yaml`

Cron jobs yang terdaftar di `hermes-config/config.yaml`:

```
daily_health_check     → hermes doctor --report        (06:00 WIB)
weekly_backup          → hermes backup --full           (02:00 Sun)
monthly_security_scan  → hermes security --report       (03:00 1st)
ritual_morning         → hermes chat -Q (morning)       (07:00)
ritual_midday          → hermes chat -Q (midday)        (12:00)
ritual_afternoon       → hermes chat -Q (afternoon)     (17:00)
ritual_evening         → hermes chat -Q (evening)       (21:00)
ritual_midnight        → hermes chat -Q (midnight)      (00:00)
```

**Tidak ada satu pun cron yang memanggil drift detection secara eksplisit.**

### LoopScheduler (`src/loops/scheduler.py`)

`LoopScheduler` menggunakan APScheduler untuk ritual harian — hanya memanggil `LoopManager.start_loop()` dengan task/goal parameter. Tidak ada job drift detection yang diregister.

### Hermes Cron (`~/.hermes/` profile)

Tidak ada cron entry di hermes profile yang mengacu drift check atau deep validation.

**Verdict cek #2: Tidak ada scheduler/cron yang memanggil drift detection secara periodic (deep validation tidak diimplementasikan).**

---

## 3. Apakah `safety_plugin.py` G03 Sudah Cover Per-Response Drift Check?

**File**: `/home/guinevere/code/guinevere/src/hermes/safety_plugin.py`

### G03 di safety_plugin.py — Analisis Detail

G03 terdaftar di `post_llm_call` hook dan berjalan setiap LLM response. Implementasinya:

```python
def post_llm_call(self, **kwargs: Any) -> None:
    """Gate 03: Computes SHA-256 hash of assistant message and checks drift
    against baseline if a DriftDetector is configured."""
    # ... 
    # Lazy-init detector dengan baseline dari RESPONS PERTAMA
    if self._drift_detector is None and self._drift_available:
        baseline_hash = DriftDetector.compute_prompt_hash(text)
        self._drift_detector = DriftDetector(
            baseline=DriftBaseline(
                prompt_hash=baseline_hash,
                version="plugin-init",
                ...
                description="Auto-baseline from first assistant response"
            ),
        )
        return  # baseline established — tidak melakukan check

    # Subsequent responses: compare hash vs baseline
    if detector is not None and self._drift_available:
        current_hash = DriftDetector.compute_prompt_hash(text)
        result = detector.detect(current_hash)
        # action: "rollback" or "alert" → hanya LOG, tidak block
```

### Apa yang G03 sudah cover:

✅ Berjalan setiap respons LLM (per-response = per-loop dalam konteks Hermes)  
✅ SHA-256 hash comparison per respons  
✅ Alert/rollback logging ketika drift terdeteksi  
✅ Terdaftar di plugin.yaml sebagai `post_llm_call` hook  

### Apa yang G03 TIDAK cover:

❌ **Baseline salah**: Baseline di-set dari RESPONS PERTAMA (bukan SOUL.md atau system prompt canonical). Ini berarti jika respons pertama sudah drift, semua check berikutnya salah baseline.  
❌ **Hash apa yang di-compare**: G03 melakukan hash pada *assistant response text*, bukan pada *system prompt/persona definition*. ADR-003 menyebut "drift dari SOUL.md rules" — bukan drift output-ke-output.  
❌ **Periodic deep validation**: G03 hanya lightweight (SHA-256 text hash). Tidak ada sub-agent deep validation, behavioral analysis, atau audit file-based per ADR-012.  
❌ **drift_check.py hook**: `hermes-config/hooks/drift_check.py` (post_prompt) juga ada sebagai defense-in-depth, tapi **tidak terdaftar di `config.yaml` hooks section** (config.yaml hanya mendefinisikan `pre_tool_call` dan `post_tool_call` hooks). Jadi hook ini tidak aktif.  
❌ **ValidationScheduler**: Tidak ada implementasi APScheduler-based ValidationScheduler yang menjalankan lightweight check per-loop dan deep check berkala.

### Pertanyaan: "Per-loop" di konteks Hermes = per-message atau per-session?

Di konteks Hermes agent:

- **Session** = satu conversation thread Discord (dibuat per-invocation karena `new_instance_per_invocation: true`).
- **Loop** = satu iterasi agent loop (satu LLM call + tool calls + response).
- **Per-message** dari Discord = memicu satu session → bisa berisi banyak loop (multi-step reasoning dengan `max_iterations: 15`).

Dengan demikian: **"per-loop" dalam ADR-003 = per-LLM-call (per iterasi agent loop)**, bukan per Discord message. Satu Discord message bisa menghasilkan 1–15 loop tergantung kompleksitas task.

G03 via `post_llm_call` berjalan setiap loop (setiap LLM call). Jadi G03 **memenuhi frekuensi "per-loop"** secara teknis — tapi **tidak memenuhi requirement konten** karena:
1. Baseline dari respons pertama, bukan canonical persona
2. Hanya hash comparison, bukan invariant check (safe word, yandere cap, punishment bounds)
3. Tidak ada periodic deep validation component

---

## 4. Gap Summary

| Requirement ADR-003 | Status | Bukti |
|---------------------|--------|-------|
| Per-loop lightweight check (safe word, yandere cap, punishment bounds) | ❌ PARTIAL | G03 berjalan per-loop tapi hanya SHA-256 hash response text, bukan invariant check |
| Periodic deep validation (N loops atau harian) | ❌ MISSING | Tidak ada scheduler/cron/ValidationScheduler untuk deep validation |
| Sub-agent deep validation per ADR-012 (file-based output) | ❌ MISSING | Tidak ada implementasi |
| Baseline dari canonical SOUL.md / system prompt | ❌ WRONG | Baseline di-set dari respons pertama, bukan SOUL.md |
| drift_check.py hook aktif | ❌ NOT WIRED | File ada di hermes-config/hooks/ tapi tidak terdaftar di config.yaml |
| DriftLog `reviewer` field | ❌ MISSING | Tercatat di KNOWN-ISSUES KI-08 |

**Catatan KNOWN-ISSUES yang relevan (docs/setup-evidence/P4/KNOWN-ISSUES.md)**:
- **KI-09**: "No Per-Loop Lightweight + Periodic Deep Validation Cadence (ADR-003)" — severity HIGH, deferred to P5/P6
- **KI-08**: "DriftLog Missing `reviewer` Field (ADR-003)" — severity MEDIUM, deferred to P5/P6

---

## 5. Verdict

### **FIX** — Perlu implementasi, bukan dihapus

**Alasan**:

1. **ADR-003 aktif dan binding** (status "Accepted with notes", risk HIGH). Requirement drift validation cadence adalah note yang wajib diimplementasikan, bukan optional.

2. **G03 di safety_plugin.py ada tapi tidak cukup** — G03 cover per-loop hash check tapi dengan baseline yang salah (response text, bukan canonical persona) dan tanpa periodic deep validation. Ini partial implementation, bukan full compliance.

3. **Sudah diakui sebagai gap** — KI-09 di KNOWN-ISSUES.md sudah mendokumentasikan ini sebagai HIGH severity gap yang deferred ke P5/P6. Ini konfirmasi bahwa tim sadar dan perlu fix.

4. **drift_check.py sudah ditulis tapi tidak diwired** — hook logic sudah ada (`hermes-config/hooks/drift_check.py`), tapi tidak terdaftar di config.yaml hooks section. Ini menunjukkan gap implementasi yang sederhana untuk per-loop layer, bukan ketiadaan total.

5. **Deep validation belum ada sama sekali** — Tidak ada ValidationScheduler, tidak ada cron drift check, tidak ada sub-agent deep validation. Komponen ini perlu dibuat dari awal.

### Scope Fix yang Direkomendasikan

**P5/P6 scope** (sesuai KNOWN-ISSUES deferred timeline):

1. **Register `drift_check.py` di `post_llm_call` hook** — tambahkan ke `config.yaml` hooks section (fix mudah, per-loop layer).

2. **Fix baseline strategy di G03** — ganti baseline dari "respons pertama" menjadi hash dari `SOUL.md` atau system prompt canonical. `DriftDetector.SOUL_BASELINE_HASH` sudah ada di drift_detector.py sebagai referensi.

3. **Implementasikan periodic deep validation** — gunakan APScheduler (sudah installed, paket `apscheduler-3.11.2` ada di venv) untuk menjalankan deep check setiap N loop atau harian. Wire ke `src/loops/scheduler.py` yang sudah ada.

4. **Add `reviewer` field ke DriftLog** (KI-08) — Alembic migration untuk kolom baru.

---

## 6. Files yang Dibaca dalam Riset Ini

| File | Relevansi |
|------|-----------|
| `adr/ADR-003-persona-drift-control-validation.md` | Sumber requirement ADR-003 |
| `src/hermes/safety_plugin.py` | Implementasi G03 (post_llm_call) |
| `src/persona/drift_detector.py` | DriftDetector class (masih ada, tidak dihapus) |
| `hermes-config/hooks/drift_check.py` | Per-loop hook logic (ada tapi tidak diwired) |
| `hermes-config/config.yaml` | Cron jobs dan hooks yang aktif |
| `src/loops/scheduler.py` | APScheduler LoopScheduler |
| `docs/setup-evidence/P4/KNOWN-ISSUES.md` | KI-08, KI-09: gap sudah terdokumentasi |
| `.hermes/plugins/guinevere-safety/plugin.yaml` | Hook registration safety plugin |

---

## Footer

| Field | Value |
|-------|-------|
| Researcher | Sub-agent (riset task) |
| Date | 2026-06-09 |
| Verdict | **FIX** |
| Priority | HIGH (ADR-003 binding, KI-09 deferred P5/P6) |
| Effort estimate | Medium — per-loop layer mudah (wire hook); deep validation layer sedang (ValidationScheduler) |
