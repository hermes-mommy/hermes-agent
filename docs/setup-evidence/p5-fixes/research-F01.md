# Research F-01: LoopManager Singleton Bug

**Date:** 2026-06-09  
**Bug:** Setiap caller buat `LoopManager()` baru — `active_loops` dict tidak shared.  
**Status:** Pre-fix research

---

## 1. Temuan: LoopManager di `src/core/main.py`

File: `src/core/main.py`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.loops.manager import LoopManager          # line 34

    loop_manager = LoopManager()                       # line 48 — instance dibuat di sini
    app.state.loop_manager = loop_manager              # line 49 — disimpan di app.state

    guardian_task = asyncio.create_task(
        loop_manager.guardian.monitor(),
        name="guardian-monitor",
    )
    app.state.guardian_task = guardian_task
    ...
    yield
    ...
    await loop_manager.guardian.stop()
```

**Kesimpulan:** FastAPI app sudah punya satu canonical `LoopManager` instance yang tersimpan di `app.state.loop_manager`, dibuat saat lifespan startup. Guardian monitoring juga hanya ada di satu instance ini.

---

## 2. Temuan: API Routes (`src/core/api/routes.py`)

```python
def _get_loop_manager(request: Request):
    """Extract LoopManager from app state."""
    manager = getattr(request.app.state, "loop_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="Loop manager not initialized")
    return manager
```

Routes `/api/v1/loops` (GET, POST), `/api/v1/loops/{loop_id}` (GET), `/api/v1/loops/{loop_id}/cancel` (POST) **semuanya sudah benar** — mereka ambil instance dari `request.app.state`, bukan buat baru.

**Kesimpulan:** API routes TIDAK bermasalah. Mereka sudah share instance yang sama.

---

## 3. Exact Caller List — Yang Buat `LoopManager()` Baru (BERMASALAH)

Berikut semua lokasi yang instantiate `LoopManager()` sendiri, sehingga tiap call dapat instance terpisah dengan `active_loops` kosong:

### 3.1 Discord Commands (`src/discord/`)

| File | Line | Pattern |
|------|------|---------|
| `src/discord/cmd_loops.py` | 36–38 | `from src.loops.manager import LoopManager` → `manager = LoopManager()` |
| `src/discord/cmd_loop_priority.py` | 77–79 | `from src.loops.manager import LoopManager` → `manager = LoopManager()` |
| `src/discord/cmd_evidence.py` | 44–46 | `from src.loops.manager import LoopManager` → `manager = LoopManager()` |
| `src/discord/cmd_loop_resume.py` | 54–57 | `from src.loops.manager import LoopManager` → `manager = LoopManager()` |
| `src/discord/cmd_loop_pause.py` | 53–55 | `from src.loops.manager import LoopManager` → `manager = LoopManager()` |

**Catatan:** `cmd_loop_start.py` dan `cmd_loop_stop.py` tidak langsung instantiate `LoopManager()` — mereka memanggil HTTP API internal (`http://localhost:8000/api/v1/loops`). Jadi kedua file ini **sudah benar** karena HTTP call-nya akan landing di routes yang pakai `app.state`.

### 3.2 Hermes Plugins (`src/hermes_plugins/commands_loop/`)

| File | Line | Pattern |
|------|------|---------|
| `src/hermes_plugins/commands_loop/loops.py` | 29–31 | `from src.loops.manager import LoopManager` → `manager = LoopManager()` |
| `src/hermes_plugins/commands_loop/loop_priority.py` | 75–77 | `from src.loops.manager import LoopManager` → `manager = LoopManager()` |
| `src/hermes_plugins/commands_loop/evidence.py` | 45–47 | `from src.loops.manager import LoopManager` → `manager = LoopManager()` |
| `src/hermes_plugins/commands_loop/loop_pause.py` | 53–55 | `from src.loops.manager import LoopManager` → `manager = LoopManager()` |
| `src/hermes_plugins/commands_loop/loop_resume.py` | 53–56 | `from src.loops.manager import LoopManager` → `manager = LoopManager()` |

### 3.3 Loop Scheduler (`src/loops/scheduler.py`)

| File | Line | Pattern |
|------|------|---------|
| `src/loops/scheduler.py` | 25 | `self.manager = LoopManager()` dalam `LoopScheduler.__init__()` |

**Note:** Scheduler ini adalah class terpisah, tidak dipakai di lifespan saat ini, tapi kalau diinstantiasi akan dapat instance baru.

### 3.4 Standalone Entry Point (`src/loops/manager.py`)

| File | Line | Pattern |
|------|------|---------|
| `src/loops/manager.py` | 271 | `manager = LoopManager()` dalam fungsi `main()` standalone |

Ini intentional (untuk run sebagai standalone service, bukan sebagai bagian FastAPI). **Tidak perlu difix.**

---

## 4. Analisis Pattern Dependency Injection

### Apa yang FastAPI sudah pakai:
- **`app.state`**: Dipakai di lifespan untuk store singleton `loop_manager`, `guardian_task`, `report_scheduler`, `surveillance_consumer`, dll.
- **`request.app.state`**: Dipakai di `routes.py` via helper function `_get_loop_manager(request)`.
- **`Depends`**: Dipakai di routes untuk `get_api_key` auth. Belum dipakai untuk LoopManager injection.
- **Tidak ada** modul-level singleton LoopManager saat ini.

### Root cause bug F-01:
Discord commands dan Hermes plugins **tidak terhubung ke FastAPI app** — mereka adalah kode Python biasa yang dipanggil langsung (bukan HTTP request ke FastAPI). Karena itu mereka tidak punya akses ke `request.app.state`, lalu instantiate `LoopManager()` baru. Setiap instance baru punya `active_loops = {}` kosong, sehingga:
- Discord `/loops` akan selalu lihat 0 loops
- `/loop-pause`, `/loop-resume`, `/evidence` akan selalu gagal dengan "loop not found"
- Scheduler akan trigger loops ke instance terpisah, tidak termonitor oleh guardian utama

---

## 5. Analisis Tiga Pendekatan Fix

### Opsi A: Module-level singleton

```python
# src/loops/manager.py
_instance: LoopManager | None = None

def get_loop_manager() -> LoopManager:
    global _instance
    if _instance is None:
        _instance = LoopManager()
    return _instance
```

**Pro:** Minimal perubahan di callers — tinggal ganti `LoopManager()` → `get_loop_manager()`.  
**Con:** 
- Thread/async safety perlu diperhatikan (meski GIL Python biasanya aman untuk single-assign).
- Instance dibuat di import time atau first-call, bukan controlled di lifespan.
- Guardian monitoring tidak otomatis start, perlu dikoordinasi terpisah.
- Lifecycle (startup/shutdown) tidak terikat ke FastAPI lifespan — risk resource leak.
- `main.py` lifespan perlu update untuk pakai singleton juga, atau ada dua instance.

### Opsi B: FastAPI `app.state`

Callers langsung akses `app.state` dari somewhere. Tapi Discord commands dan Hermes plugins tidak punya akses ke FastAPI `app` object — butuh pass-around atau import dari `main.py`.

**Pro:** Sudah dipakai di routes, konsisten.  
**Con:** Discord/Hermes plugins tidak punya `Request` context. Harus import `app` dari `src.core.main` (circular import risk) atau pakai HTTP API seperti cmd_loop_start/stop sudah lakukan.

### Opsi C: Lifespan + HTTP API (best path)

Discord commands dan Hermes plugins sudah ada template yang benar di `cmd_loop_start.py` dan `cmd_loop_stop.py`: mereka **tidak** instantiate LoopManager langsung, melainkan call HTTP API ke `http://localhost:8000/api/v1/loops`. API tersebut lalu pakai `app.state.loop_manager` yang benar.

**Pro:**
- Zero coupling antara Discord/Hermes layer dengan FastAPI internals.
- API routes sudah benar (`_get_loop_manager` via `app.state`).
- Consistent dengan arsitektur yang sudah dipilih (`cmd_loop_start.py`, `cmd_loop_stop.py`).
- Discord commands sudah punya `httpx` sebagai dependency.
- Hermes plugins bisa pakai HTTP call yang sama.
- Tidak ada risk lifecycle/singleton management.

**Con:** Sedikit lebih verbose per command (butuh HTTP client).

---

## 6. Rekomendasi Fix: **Opsi C — Ganti Direct Instantiation dengan HTTP API**

Pilih Opsi C karena:
1. **Paling minimal disruption** ke arsitektur — tidak ubah `main.py`, tidak ubah `manager.py`, tidak ubah `routes.py`.
2. **Consistent dengan pattern yang sudah dipilih**: `cmd_loop_start.py` dan `cmd_loop_stop.py` sudah jadi contoh yang benar.
3. **No circular imports** — Discord/Hermes tidak perlu import dari `src.core.main`.
4. **Lifecycle aman** — LoopManager tetap di-manage oleh lifespan, bukan scattered.
5. Alternatif module-level singleton (Opsi A) akan harus dikoordinasikan dengan lifespan untuk guardian startup dan menyebabkan komplikasi shutdown.

---

## 7. Files yang Perlu Diubah

### Priority 1 — Discord Commands (direct callers bermasalah):

| File | Perubahan |
|------|-----------|
| `src/discord/cmd_loops.py` | Ganti `LoopManager()` instantiation → HTTP GET `http://localhost:8000/api/v1/loops` |
| `src/discord/cmd_loop_pause.py` | Ganti `LoopManager()` → HTTP POST `/api/v1/loops/{loop_id}/pause` (atau extend API) |
| `src/discord/cmd_loop_resume.py` | Ganti `LoopManager()` → HTTP POST `/api/v1/loops/{loop_id}/resume` (atau extend API) |
| `src/discord/cmd_loop_priority.py` | Ganti `LoopManager()` → HTTP PATCH/POST endpoint (atau extend API) |
| `src/discord/cmd_evidence.py` | Ganti `LoopManager()` → HTTP GET endpoint untuk evidence |

### Priority 2 — Hermes Plugins (mirror dari Discord commands):

| File | Perubahan |
|------|-----------|
| `src/hermes_plugins/commands_loop/loops.py` | Ganti `LoopManager()` → HTTP GET `http://localhost:8000/api/v1/loops` |
| `src/hermes_plugins/commands_loop/loop_pause.py` | Ganti `LoopManager()` → HTTP call |
| `src/hermes_plugins/commands_loop/loop_resume.py` | Ganti `LoopManager()` → HTTP call |
| `src/hermes_plugins/commands_loop/loop_priority.py` | Ganti `LoopManager()` → HTTP call |
| `src/hermes_plugins/commands_loop/evidence.py` | Ganti `LoopManager()` → HTTP call |

### Priority 3 — API Routes Extension (kalau endpoint belum ada):

| File | Perubahan |
|------|-----------|
| `src/core/api/routes.py` | Tambah endpoint `/loops/{loop_id}/pause`, `/loops/{loop_id}/resume`, `/loops/{loop_id}/priority` jika belum ada |

### Tidak perlu diubah:

| File | Alasan |
|------|--------|
| `src/core/main.py` | Sudah benar — buat satu instance, simpan di `app.state` |
| `src/core/api/routes.py` | Sudah benar — ambil dari `app.state` |
| `src/discord/cmd_loop_start.py` | Sudah benar — pakai HTTP API |
| `src/discord/cmd_loop_stop.py` | Sudah benar — pakai HTTP API |
| `src/loops/manager.py` → `main()` | Intentional standalone, tidak perlu diubah |
| `src/loops/scheduler.py` | Perlu review terpisah saat scheduler diintegrasikan ke lifespan |

---

## 8. Ringkasan

**Bug root cause:** 10 callers di `src/discord/` dan `src/hermes_plugins/commands_loop/` instantiate `LoopManager()` baru alih-alih menggunakan instance yang dibuat di FastAPI lifespan dan tersimpan di `app.state.loop_manager`. Setiap instance baru punya `active_loops = {}` kosong, sehingga semua operasi loop (list, pause, resume, evidence) selalu lihat state kosong.

**Fix:** Konversi 10 caller bermasalah ke pattern HTTP API yang sudah dipakai `cmd_loop_start.py` dan `cmd_loop_stop.py` (httpx call ke `http://localhost:8000/api/v1/loops`). Mungkin perlu tambah beberapa API endpoints baru untuk pause/resume/priority/evidence.

**Files to change:** 10 Discord/Hermes files + kemungkinan 1 routes file untuk endpoint baru.
