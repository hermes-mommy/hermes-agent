# Research: python3.12-distutils & ensurepip vs get-pip.py

| Field | Value |
|-------|-------|
| **Research Agent** | Librarian |
| **Date** | 2026-05-31 |
| **Sources** | Ubuntu Packages, PEP 632, pip docs, StackOverflow |
| **Verdict** | distutils removed in 3.12; ensurepip is preferred over get-pip.py |

---

## 1. python3.12-distutils — Tidak Ada

- `python3.12-distutils` does NOT exist as an APT package
- `python3-distutils` only available for Ubuntu 22.04 (Jammy, Python 3.10)
- On Ubuntu 24.04: `apt-get install python3-distutils` → "Package 'python3-distutils' has no installation candidate"
- **Root cause**: distutils removed from Python 3.12 per PEP 632

## 2. Pengganti distutils — setuptools

- PEP 632: "Code that imports distutils will no longer work from Python 3.12"
- setuptools ≥ 60.0.0 includes vendored distutils, active by default
- Python 3.12 no longer installs setuptools in venvs by default
- Command: `python3.12 -m pip install setuptools`

## 3. ensurepip vs get-pip.py

| Aspect | ensurepip | get-pip.py |
|--------|-----------|------------|
| Built-in | Yes (Python ≥ 3.4) | No (download needed) |
| Official recommendation | **First choice** | Fallback |
| System package coordination | Safer | May leave inconsistent state |
| Network required | No (bundled) | Yes |

From pip official docs: *"If pip isn't already installed, first try to bootstrap it from the standard library: python -m ensurepip --default-pip"*

From Python Packaging User Guide: *"get-pip.py does not coordinate with system package managers, and may leave your system in an inconsistent state"*

## 4. Recommended Commands

```bash
# Bootstrap pip
python3.12 -m ensurepip --upgrade

# Install setuptools for distutils compatibility
python3.12 -m pip install setuptools

# Optional: upgrade pip
python3.12 -m pip install --upgrade pip
```

## 5. Ubuntu 24.04 Alternative

APT install is also valid: `sudo apt install -y python3-pip`
This installs pip via the system package manager and handles dependencies correctly.

| Field | Value |
|-------|-------|
| **Source** | bg_8ea6bd89 — python3.12-distutils |
| **File** | research-reports/P1/distutils-ensurepip.md |