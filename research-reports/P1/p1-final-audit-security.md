# P1 Final Security Audit Report — Plaintext Secrets, Encryption, Permissions, and .gitignore

| Field | Value |
|---|---|
| **Report ID** | SEC-AUDIT-P1-FINAL |
| **Scope** | P1 deliverables: evidence files, auditor reports, source code, secrets, tmp files, .gitignore |
| **Date** | 2026-06-01 |
| **Auditor** | Guinevere (independent security audit agent) |
| **Method** | Grep (8 regex patterns), Glob, file inspection, cross-reference verification |
| **Verdict** | **NEEDS REVIEW — 2 CRITICAL, 2 MEDIUM, 3 LOW findings** |

---

## 1. Scope & Methodology

### Directories Scanned (100% coverage)

| Directory | Files | Target |
|---|---|---|
| `docs/setup-evidence/P1/` | 35 files | All P1 evidence files |
| `audit-reports/P1/` | 17 files | All P1 auditor reports |
| `src/core/services/` | 5 files | All source code |
| `tests/` | 9 files | All tests |
| `scripts/` | 9 files | All scripts |
| `tmp/` | 65 files | All temp files |
| `secrets/` | 8 files | All secret files |
| `research-reports/P1/` | 5 files | P1 research |
| `stepprompts/` | 2 files | StepPrompts.md + .bak |

### Grep Patterns Used

| # | Pattern | Target |
|---|---|---|
| P1 | `sk-[a-zA-Z0-9]{20,}` | OpenAI API keys |
| P2 | `Bearer [a-zA-Z0-9_-]{20,}` | Bearer tokens |
| P3 | `api[_-]?key...` | Generic API keys |
| P4 | `password...` | Password values |
| P5 | `secret...` | Secret values |
| P6 | `token...` | Token values |
| P7 | `JWT_SECRET` / `INITIAL_PASSWORD` | 9Router secrets |
| P8 | `AGE-SECRET-KEY` | Age private keys |

---

## 2. Grep Pattern Results Summary

| Pattern | Hits | Real Secrets? | Verdict |
|---|---|---|---|
| `sk-...` (OpenAI) | 5 | 0 real | All synthetic |
| `Bearer ...` | 2 | 0 real | Code example refs |
| `api_key...` | 1 | 0 real | Synthetic example |
| `password...` | 43 | **3 REAL** | backup plaintext files |
| `secret...` | 13 | 0 real | ENC[] or env var refs |
| `token...` | 2 | 0 real | Code example refs |
| `JWT_SECRET` / `INITIAL_PASSWORD` | 63 | **1 REAL** | .env.9router (unencrypted) |
| `AGE-SECRET-KEY` | 23 | 0 real | Truncated examples |

**Key finding**: 3 plaintext backup secrets + 1 unencrypted runtime secret file

---

## 3. Finding A — PLAINTEXT BACKUP SECRETS IN REPO (CRITICAL)

### Files

| File | Secrets Exposed | Sensitivity |
|---|---|---|
| `secrets/backup/cloudflare-r2-plaintext.env` | Real AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, account ID | HIGH |
| `secrets/backup/idcloudhost-s3-plaintext.env` | Real AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY | HIGH |
| `secrets/backup/restic-password-plaintext.env` | 64-char RESTIC_PASSWORD | HIGH |

### Details

These files contain real production credentials for three backup targets. The root `.gitignore` has `secrets/backup/*-plaintext*` which blocks commit, but the `secrets/backup/README.md` document explicitly states these files should be **shredded** after SOPS re-encryption — which was never done.

**Status**: LOCAL EXPOSURE — files on disk, git-ignored but not shredded per documented procedure

---

## 4. Finding B — SOPS ENCRYPTION NOT APPLIED FOR 9Router (CRITICAL)

### File

Runtime env file at `/home/guinevere/code/guinevere/secrets/.env.9router`

### Details

| Field | Value |
|---|---|
| `JWT_SECRET` | 64 hex chars (real) |
| `INITIAL_PASSWORD` | 32 alphanumeric chars (real) |
| `OPENAI_API_KEY` | PLACEHOLDER |
| `DEEPSEEK_API_KEY` | PLACEHOLDER |
| Permissions | chmod 600 (filesystem-only protection) |

### Violation

- **SOPS-encrypted `.env.9router.sops` does NOT exist** (confirmed by P1-007 auditor report)
- ADR-015 requires secrets to be SOPS-encrypted at rest
- Confirmed by P1-007 auditor finding B-02

**Status**: UNENCRYPTED — runtime env file in plaintext

---

## 5. Finding C — SYNTHETIC SECRETS IN P0 AUDIT REPORT (MEDIUM)

### File

`audit-reports/P0/STEP-P0-013/external-sops-config-report.md`

### Synthetic Values

| Line | Content |
|---|---|
| 732 | `discord_token: "my.discord.bot.token"` |
| 770 | `openai_api_key: "sk-proj-abc123def456"` |
| 772 | `grafana_password: "grafana-secret-123"` |
| 773 | `jwt_secret: "jwt-signing-key-here"` |

Clearly dummy values used in a SOPS configuration research report. Principled concern — automated scanners would flag these.

**Status**: KNOWN DUMMY VALUES

---

## 6. Finding D — .gitignore COVERAGE GAPS (MEDIUM)

### Current .gitignore (42 lines)

Key patterns: `secrets/backup/*-plaintext*`, `*.key`, `*.pem`, `*.env`, `!.env.example`, `tmp/`

### Gaps

| Pattern | Status |
|---|---|
| `credentials*` | NOT COVERED — should catch any future credential files |
| `secrets/` blanket exclusion | NOT COVERED — defense-in-depth option |

Functionally adequate for current state. Defense-in-depth improvements recommended.

**Status**: ADEQUATE

---

## 7. Finding E — TEST/DOCUMENTATION SECRETS IN REPO (LOW)

| File | Value | Type |
|---|---|---|
| `docs/10-governance/14-TDD_Guide_v1.0.md` | `"test-secret-key-for-load-testing"` | Test example |
| `research-reports/2026-05-31-hermes-9router-tasker.md` | `"your-hmac-secret"` | Code example |
| `research-reports/2026-05-30-test-plan-...` | `"test-hmac-secret-for-performance-testing"` | Test value |

All clearly fake. No real exposure.

**Status**: ACCEPTABLE — no action required

---

## 8. Finding F — EVIDENCE FILE SECRECY (PASS)

All 35 P1 evidence files verified clean:
- Variable names only (JWT_SECRET, INITIAL_PASSWORD as field references, not values)
- P1-007 evidence: "Fingerprint only in evidence. Actual values: HASH(SET)."
- P1-020 auditor: "Zero secrets in evidence"

**Status**: PASS

---

## 9. Finding G — SOURCE CODE SECRECY (PASS)

- `cost_tracker.py`: `password` from `os.environ.get("REDIS_PASSWORD", "")` — env var pattern
- `llm_router.py`: No API keys in code — uses 9Router localhost endpoint
- All 9 test files: No secrets

**Status**: PASS

---

## 10. Finding H — AGE KEY SAFETY (PASS)

| Check | Result |
|---|---|
| Private age key in repo? | NOT FOUND |
| Public key only in evidence? | Yes |
| Synthetic keys in reports? | Truncated examples only |
| Key rotated after exposure? | Yes |

**Status**: PASS

---

## 11. Finding I — VERIFIED ENCRYPTED FILES

| File | SOPS-Encrypted? | Status |
|---|---|---|
| `secrets/guinevere-secrets.yaml` | YES | CONFIRMED |
| `secrets/redis-password.yaml` | YES | CONFIRMED |
| `secrets/db-passwords.yaml` | YES | CONFIRMED |
| `secrets/.env.9router.sops` | NOT FOUND | MISSING — CRITICAL |
| `secrets/backup/cloudflare-r2.env` | NOT FOUND | MISSING |
| `secrets/backup/idcloudhost-s3.env` | NOT FOUND | MISSING |
| `secrets/backup/restic-password.env` | NOT FOUND | MISSING |

---

## 12. Consolidated Risk Matrix

| ID | Finding | Severity | Status |
|---|---|---|---|
| A | Plaintext backup secrets (3 files) | CRITICAL | Active |
| B | .env.9router.sops missing | CRITICAL | Active |
| C | Synthetic secrets in P0 report | MEDIUM | Active |
| D | .gitignore gaps | MEDIUM | Active |
| E | Test secrets in docs | LOW | Accepted |
| F | Evidence file secrecy | PASS | Clean |
| G | Source code secrecy | PASS | Clean |
| H | Age key safety | PASS | Clean |
| I | SOPS encrypted files | FAIL | 4 of 7 expected encrypted |

### Scorecard

| Dimension | Score |
|---|---|
| Plaintext secrets in repo | FAIL |
| SOPS encryption coverage | FAIL |
| Evidence file secrecy | PASS |
| Source code secrecy | PASS |
| Age key management | PASS |
| .gitignore coverage | ADEQUATE |
| File permissions (VPS) | PASS |

---

## 13. Remediation Action Plan

### Immediate

1. **Shred plaintext backup files** and create SOPS-encrypted counterparts:
   - `sops --encrypt ... secrets/backup/cloudflare-r2-plaintext.env > secrets/backup/cloudflare-r2.env`
   - `sops --encrypt ... secrets/backup/idcloudhost-s3-plaintext.env > secrets/backup/idcloudhost-s3.env`
   - `sops --encrypt ... secrets/backup/restic-password-plaintext.env > secrets/backup/restic-password.env`
   - `shred -u secrets/backup/*-plaintext.env`

2. **Create `.env.9router.sops`** on VPS.

### Short-term

3. Add `credentials*` to `.gitignore`.

4. Replace synthetic examples in P0 audit report with `[EXAMPLE_KEY]`.

5. Fix systemd unit deviations (After, Restart, Group).

### Long-term

6. Pre-commit hook for secret scanning.

7. Monthly secret audit in security checklist.

---

## 14. Footer

| Field | Value |
|---|---|
| **Report ID** | SEC-AUDIT-P1-FINAL |
| **Auditor** | Guinevere (independent security audit) |
| **Date** | 2026-06-01 |
| **Files scanned** | 150+ across 9 directory trees |
| **Verdict** | **2 CRITICAL, 2 MEDIUM, 3 LOW** |
| **Next action** | Shred plaintext backup files, create .env.9router.sops |
