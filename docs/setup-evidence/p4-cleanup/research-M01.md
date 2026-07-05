# Research M-01: DriftLog — Missing `reviewer` Field (ADR-003)

**Tanggal research:** 2026-06-09
**Researcher:** Guinevere sub-agent (research wave)
**Finding asal:** P4 Enterprise Audit 2026-06-08 — M-01 (MEDIUM)

---

## 1. Field DriftLog Saat Ini (`src/memory/models.py` baris 373–392)

```python
class DriftLog(Base, ClassificationMetaMixin):
    __tablename__ = "drift_log"
    __table_args__ = {"schema": "persona"}

    id                : UUID        (PK)
    drift_type        : Text        NOT NULL
    before_state      : JSONB       NOT NULL
    after_state       : JSONB       NOT NULL
    delta             : JSONB       NOT NULL
    trigger_context   : Text        nullable
    safety_score      : Integer     nullable
    rollback_available: Boolean     default true
    occurred_at       : TIMESTAMP   NOT NULL
```

Plus field dari `ClassificationMetaMixin` (classification, purpose, source,
retention_class, retention_until, access_policy, encryption_profile,
deletion_state, key_id, key_version, created_at, updated_at).

**Field `reviewer` TIDAK ADA.** ✗

---

## 2. Apakah DriftLog Di-write dari Tempat Lain di `src/`?

Search `DriftLog` dan `drift_log` di seluruh `src/`:

```
src/memory/models.py:373  class DriftLog(Base, ClassificationMetaMixin):
```

**Hanya 1 hit — definisi model itu sendiri.**

Tidak ada kode di `src/` yang melakukan insert/write ke tabel `drift_log`.

---

## 3. Apakah DriftDetector / drift_corrector Masih Menulis DriftLog ke DB?

### `src/persona/drift_corrector.py`
**File sudah DIHAPUS** (2026-06-09). Tidak ada di filesystem.

### `src/persona/drift_detector.py`
File ada dan masih dipakai oleh `safety_plugin.py`.
Namun `DriftDetector.detect()` hanya mengembalikan `DriftResult` dataclass (in-memory).
**Tidak ada import DriftLog, tidak ada SQLAlchemy session, tidak ada DB write.**

```python
# drift_detector.py — TIDAK ada:
#   from src.memory.models import DriftLog
#   session.add(...)
#   session.commit()
```

`DriftResult` adalah pure dataclass frozen, bukan ORM model.

**Kesimpulan: Tidak ada code path aktif yang menulis ke tabel `persona.drift_log`.**

---

## 4. Alembic Migration untuk DriftLog

File migration yang relevan:
- `alembic/versions/e401bb5fd274_initial_schema_47_tables.py` — dibuat 2026-06-02

Tabel `drift_log` **ADA** di migration ini (baris 565–589), dengan kolom:

```
id, drift_type, before_state, after_state, delta,
trigger_context, safety_score, rollback_available, occurred_at,
+ ClassificationMetaMixin columns (classification, purpose, source, ...)
```

**Kolom `reviewer` TIDAK ADA di migration.** ✗

Tidak ada migration lain yang menyentuh `drift_log` (search exhaustif di semua
file `alembic/versions/`).

---

## 5. Status Tabel di Production

Query langsung ke PostgreSQL (port 5433, user `guinevere_core`, DB `guinevere`):

```sql
SELECT count(*) FROM persona.drift_log;
```

**Hasil:**
```
 count
-------
     0
(1 row)
```

Tabel ada (migration dijalankan) tapi **belum pernah diisi satu row pun.**

---

## 6. Analisis ADR-003 Requirement

ADR-003 (`adr/ADR-003-persona-drift-control-validation.md`) baris 131:

> **Drift log schema:** Reference specific table/schema in
> Guinevere_MemorySchema_v2.0.md (e.g., `persona_drift_logs` with
> **timestamp, drift_vector, trigger, reviewer, action**).
> Align with ADR-024 data classification.

Field yang disyaratkan ADR-003 vs yang ada sekarang:

| Field ADR-003    | Ada di model? | Catatan                                          |
|------------------|:-------------:|--------------------------------------------------|
| timestamp        | ✅ `occurred_at` | Sudah ada                                     |
| drift_vector     | ⚠️ partial    | `delta` (JSONB) bisa menampung ini, tapi belum eksplisit |
| trigger          | ✅ `trigger_context` | Sudah ada                                |
| **reviewer**     | ❌            | **MISSING — inilah finding M-01**                |
| action           | ❌            | Juga missing — tidak ada kolom `action`          |

Catatan: ADR-003 juga menyebut field `action` — ini juga tidak ada di model.
Audit P4 hanya melaporkan `reviewer` secara eksplisit, tapi `action` juga gap.

---

## 7. Ringkasan Temuan

| Aspek                         | Status |
|-------------------------------|--------|
| `reviewer` field di model     | ❌ MISSING |
| `reviewer` field di migration | ❌ MISSING |
| Ada writer ke DriftLog di src | ❌ TIDAK ADA (dead table) |
| drift_corrector menulis DB    | ❌ FILE DIHAPUS |
| drift_detector menulis DB     | ❌ TIDAK (in-memory only) |
| Row di production             | **0 rows** |
| Tabel ada di DB               | ✅ Ya (migration ran) |

---

## 8. Verdict: **FIX**

### Alasan

**Mengapa HAPUS tidak tepat:**
1. `DriftDetector` masih aktif dipakai `safety_plugin.py` — komponen ini hidup,
   hanya persistensinya yang belum diwire.
2. ADR-003 status adalah **"Accepted"** — ini keputusan arsitektur yang binding.
   Menghapus tabel berarti melanggar ADR-003 tanpa superseding ADR, yang
   dilarang oleh ADR-003 §Implementation Notes.
3. Tabel `drift_log` adalah bagian dari audit trail persona (HIGH risk domain).
   Menghapusnya memperlemah safety observability.
4. M-02 (finding terpisah) juga menyatakan drift validation cadence belum ada —
   artinya infrastruktur DriftLog *memang belum digunakan*, tapi ini karena M-02
   belum di-fix, bukan karena DriftLog tidak dibutuhkan.

**Mengapa FIX adalah tindakan benar:**
1. Tambahkan kolom `reviewer` (Text, nullable) ke model `DriftLog`.
2. Tambahkan kolom `action` (Text, nullable) sekaligus — juga gap ADR-003.
3. Buat Alembic migration baru untuk kedua kolom.
4. Wire persistence di `DriftDetector.detect()` atau di `safety_plugin.py` setelah
   detect() dipanggil (sebagai bagian fix M-02/P5 integration).

### Prioritas Fix

Fix model + migration: **P4 / segera** (non-breaking, additive).
Wire persistence: **P5** (butuh architectural decision kapan reviewer diisi —
human reviewer vs automated tag).

### Catatan untuk Implementasi

- Kolom `reviewer` sebaiknya `nullable=True` karena drift yang dideteksi otomatis
  (tanpa human review) tetap harus bisa di-log.
- Isi default untuk automated drift: `'system:drift_detector'`.
- Field `action` (nilai: `'none'|'alert'|'rollback'`) sudah dihitung di
  `DriftResult.action` — tinggal dipersist.
- Saat wire persistence, pastikan tidak expose Faiz personal data ke drift_log
  (AGENTS.md §2.1 Consent-Safety Mandate).

---

*Evidence: models.py dibaca langsung, drift_detector.py dibaca langsung,
alembic/versions/e401bb5fd274_initial_schema_47_tables.py dicek exhaustif,
ADR-003 dibaca penuh, query `SELECT count(*) FROM persona.drift_log` dijalankan
live (hasil: 0 rows), search `DriftLog` di seluruh src/ (1 hit = definisi saja).*
