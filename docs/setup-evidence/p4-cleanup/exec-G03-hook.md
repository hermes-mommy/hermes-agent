# exec-G03-hook: Register drift_check.py sebagai Active Hook

**Date**: 2026-06-09  
**Task**: G03 — Register drift_check.py di hermes-config/config.yaml sebagai transform_llm_output hook  
**Status**: ✅ COMPLETE

---

## Langkah yang Dilakukan

### 1. Baca hooks section config.yaml (baris 135–174)

Struktur hooks sebelum perubahan:

```yaml
hooks:
  pre_tool_call:
    - event: pre_tool_call
      command: "python3 ~/.hermes/hooks/budget_check.py"
      timeout_ms: 500
      on_failure: block
      priority: 100
    - event: pre_tool_call
      command: "python3 ~/.hermes/hooks/consent_gate.py"
      timeout_ms: 200
      on_failure: block
      priority: 90

  post_tool_call:
    - event: post_tool_call
      command: "python3 ~/.hermes/hooks/dnr_filter.py"
      timeout_ms: 50
      on_failure: block
      priority: 70
```

Tidak ada `transform_llm_output` section — perlu ditambahkan.

### 2. Tambah section transform_llm_output

Section berikut ditambahkan setelah `post_tool_call` (setelah baris 173):

```yaml
  # Persona drift check — monitors LLM output for identity/persona drift.
  # Runs on every LLM response before delivery to user. warn-only (non-blocking)
  # so drift signals are logged without interrupting normal operation.
  transform_llm_output:
    - event: transform_llm_output
      command: "python3 ~/.hermes/hooks/drift_check.py"
      timeout_ms: 100
      on_failure: warn
      priority: 50
```

File yang dimodifikasi: `hermes-config/config.yaml` (baris 175–183)

### 3. Cek keberadaan drift_check.py di ~/.hermes/hooks/

```
/home/guinevere/.hermes/hooks/drift_check.py  → EXISTS ✅
```

File sudah ada — tidak perlu copy. Source tersedia di:
- `hermes-config/hooks/drift_check.py` (repo)
- `~/.hermes/hooks/drift_check.py` (deployed, sudah ada)

### 4. Verifikasi YAML syntax

```bash
python3 -c "import yaml; yaml.safe_load(open('hermes-config/config.yaml')); print('YAML valid - no syntax errors')"
```

Output:
```
YAML valid - no syntax errors
```

Exit code: 0 ✅

---

## Hasil Akhir

| Item | Status |
|------|--------|
| `transform_llm_output` section ditambahkan | ✅ |
| Entry menggunakan event `transform_llm_output` | ✅ |
| Command: `python3 ~/.hermes/hooks/drift_check.py` | ✅ |
| `timeout_ms: 100` | ✅ |
| `on_failure: warn` | ✅ |
| `priority: 50` | ✅ |
| `drift_check.py` ada di `~/.hermes/hooks/` | ✅ (pre-existing) |
| YAML syntax valid | ✅ |

---

## State Akhir hooks Section (baris 142–184)

```yaml
hooks:
  pre_tool_call:
    - event: pre_tool_call
      command: "python3 ~/.hermes/hooks/budget_check.py"
      timeout_ms: 500
      on_failure: block
      priority: 100
    - event: pre_tool_call
      command: "python3 ~/.hermes/hooks/consent_gate.py"
      timeout_ms: 200
      on_failure: block
      priority: 90

  post_tool_call:
    - event: post_tool_call
      command: "python3 ~/.hermes/hooks/dnr_filter.py"
      timeout_ms: 50
      on_failure: block
      priority: 70

  transform_llm_output:
    - event: transform_llm_output
      command: "python3 ~/.hermes/hooks/drift_check.py"
      timeout_ms: 100
      on_failure: warn
      priority: 50
```

---

## Files Modified / Created

- **Modified**: `/home/guinevere/code/guinevere/hermes-config/config.yaml`
- **Created**: `/home/guinevere/code/guinevere/docs/setup-evidence/p4-cleanup/exec-G03-hook.md` (this file)
