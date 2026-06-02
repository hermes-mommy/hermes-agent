# Research: Python 3.12 on Ubuntu 24.04 (2025/2026)

| Field | Value |
|-------|-------|
| **Research Agent** | Librarian |
| **Date** | 2026-05-31 |
| **Sources** | Ubuntu docs, Launchpad, Packaging Guide, PEP 632, StackOverflow |
| **Verdict** | Python 3.12 IS system default — deadsnakes NOT needed |

---

## 1. Python 3.12 in Ubuntu 24.04 Native Repos

- **Python 3.12 is the DEFAULT system Python in Ubuntu 24.04 LTS (Noble Numbat)**
- **Version**: `3.12.3-1ubuntu0.13` (latest security/updates as of April 2026)
- Located in `main` repository (fully supported by Canonical with security backports)
- 13 security/update patches from Canonical since release

## 2. Dead snakes PPA on Ubuntu 24.04

**Dead snakes PPA does NOT provide Python 3.12 for noble.**

Per deadsnakes PPA disclaimer: *"Ubuntu 24.04 (noble) Python3.7+ (NOT Python3.12)"* — deadsnakes skips 3.12 for noble because Ubuntu already provides it.

Dead snakes provides for noble: Python 3.7+, 3.8+, 3.9+, 3.10, 3.11, 3.13, 3.14, 3.15.

## 3. python3.12-distutils — Does Not Exist

- `python3.12-distutils` does NOT exist as an APT package
- Distutils was removed from Python 3.12 per PEP 632
- `python3-distutils` only available for Ubuntu 22.04 (Jammy)
- Replacement: `pip install setuptools` (setuptools ≥ 58.0 includes vendored distutils)

## 4. pip Installation: ensurepip vs get-pip.py

| Aspect | ensurepip | get-pip.py |
|--------|-----------|------------|
| Built-in stdlib | Yes (Python ≥ 3.4) | No (requires download) |
| Official recommendation | **First choice** | Fallback |
| System package coordination | Safer | May leave inconsistent state |
| Network required | No (bundled) | Yes |

**Recommendation**: `python3.12 -m ensurepip --upgrade` as primary method.

## 5. Correct P1-001 Commands

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev python3-pip
python3.12 -m ensurepip --upgrade
python3.12 -m pip install setuptools
```

## 6. StepPrompts.md P1-001 Errors

| Line | Error | Fix |
|------|-------|-----|
| 3236 | "Using deadsnakes PPA" | Hapus — Python 3.12 native di noble |
| 3248 | `add-apt-repository ppa:deadsnakes` | Hapus — deadsnakes tidak sediakan 3.12 untuk noble |
| 3252 | `python3.12-distutils` | Hapus — package tidak exist |
| 3255 | `get-pip.py` | Ganti ke `ensurepip --upgrade` |

| Field | Value |
|-------|-------|
| **Source** | bg_8b339f00 — Python 3.12 Ubuntu 24.04 2025 |
| **File** | research-reports/P1/python-312-ubuntu-2404.md |