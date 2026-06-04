# ADR-022 Follow-Up Fixes — Verification Report

> **Date:** 2026-06-03
> **Task:** Fix 2 high-priority follow-up items from ADR-022 revision
> **Status:** ✅ COMPLETE

---

## 1. What Was Done

Two documentation fixes addressing stale references left after ADR-022 was revised from Baileys (Node.js) to Neonize (pure Python):

| # | Fix | File | Scope |
|---|-----|------|-------|
| FIX 1 | Redis → PostgreSQL session storage | `research-reports/p11-expansion/requirements-p11-whatsapp.md` | 10 edits (8 changes + 2 intentional keeps) |
| FIX 2 | Node.js/Baileys §3.7 → Neonize/Python | `docs/40-operations/44-DeploymentGuide_v1.0.md` | 9 edits across 7 sections |

---

## 2. Files Changed

### FIX 1 — requirements-p11-whatsapp.md

| Line (approx) | Section | Change |
|---------------|---------|--------|
| 32 | §2.1 Decision #6 | `Redis + SOPS encryption` → `PostgreSQL (Neonize native backend) + SOPS encryption for DB credentials` |
| 68 | §2.4 Decision #28 | Safe word — **kept Redis** (correct: runtime flag, not session) |
| 172 | §4.1 Diagram | `PostgreSQL ◄── Memory, Session, Conversation` → `Memory, WA Session, Conversation` |
| 173 | §4.1 Diagram | `Redis ◄── HARD STOP flag, Session, Rate limits` → `HARD STOP flag, Rate limits, Consent` |
| 174 | §4.1 Diagram | `SOPS ◄── Session encryption` → `DB credentials encryption` |
| 315-324 | §5.2 Code | `NewClient(store_path=..., # Redis-backed)` → `NewSession(postgresql://...)` |
| 366-382 | §6.1 Block | Entire session encryption flow: Redis blob → PostgreSQL native backend + SOPS for DB creds |
| 394 | §6.2 Table | `SOPS-encrypted Redis only` → `PostgreSQL (Neonize native backend, SOPS-encrypted DB credentials)` |
| 407 | §6.3 Flow | Consent flow — **kept Redis** (correct: runtime flag) |
| 508 | §12 Caveats | `SOPS backup in Redis` → `PostgreSQL backup in daily dump` |

### FIX 2 — 44-DeploymentGuide_v1.0.md

| Line (approx) | Section | Change |
|---------------|---------|--------|
| 84 | TOC | `Full Baileys WhatsApp setup` → `WhatsApp service via Neonize (pure Python)` |
| 109 | §1.1 Mermaid | `guinevere-whatsapp Baileys Bridge` → `guinevere-whatsapp Neonize Service` |
| 836-849 | §2.3 Node.js | Entire nvm install block → Removal note citing ADR-022 rev 2026-06-03 |
| 868 | §2.3 Verify | `node --version` check → Comment noting removal |
| 1449-1503 | §3.7 | **Full section replacement:** Node.js systemd unit → Python systemd unit (`python -m src.whatsapp.main`), npm setup → `pip install neonize`, `auth_info_baileys` dir → PostgreSQL sessions, `requestPairingCode()` → `!wa-pair` Discord command |
| 3019 | Troubleshooting | `Session expired` → `Session expired or Neonize connection drop`, `use pairing code` → `use !wa-pair Discord command` |
| 3128 | §10 Audit | `npm audit` → Comment: `Neonize (pure Python) — audited via uv pip audit` |
| 3246 | §10 CVE | `npm audit` → `uv pip audit` |
| 3395 | Summary | `Baileys bridge` → `Neonize WhatsApp service` |

---

## 3. Validation Results

### FIX 1 — requirements-p11-whatsapp.md

| Check | Command | Result |
|-------|---------|--------|
| No Redis session refs | `grep "Redis.*session\|session.*Redis" file` | **0 matches** ✅ |
| No store_path | `grep "store_path" file` | **0 matches** ✅ |
| No Redis-backed | `grep "Redis-backed" file` | **0 matches** ✅ |
| PostgreSQL present | `grep "PostgreSQL" file` | **9 matches** ✅ |
| Redis refs correct | `grep "Redis" file` | **12 matches** (all: safe word, HARD STOP, rate limits, consent, whitelist) ✅ |

### FIX 2 — 44-DeploymentGuide_v1.0.md

| Check | Command | Result |
|-------|---------|--------|
| No active Baileys | `grep "Baileys" file` | **3 matches** (all in historical removal notes) ✅ |
| No active Node.js for WA | `grep "node\|Node\|npm\|baileys" file` | **29 matches** — all: Prometheus `node_exporter` (10), mount options (4), Tailscale (1), Linode (1), historical notes (3), removed comments (2), Prometheus queries (6), other (2). **Zero active Node.js-for-WhatsApp refs** ✅ |
| Neonize present | `grep "Neonize" file` | **12 matches** ✅ |
| node_exporter intact | `grep "node_exporter" file` | **10 matches** (all untouched) ✅ |
| §3.7 visual | Read lines 1449-1503 | **Correct:** Neonize service, `python -m src.whatsapp.main`, `Slice=guinevere.slice`, `postgresql.service` dep, `!wa-pair` command, QR pairing procedure ✅ |

---

## 4. Evidence Artifacts

| Artifact | Path |
|----------|------|
| This report | `docs/setup-evidence/adr-022-revision/follow-up-fixes-verification.md` |
| ADR-022 revision evidence | `docs/setup-evidence/adr-022-revision/evidence-adr-022-revision.md` |
| Requirements file | `research-reports/p11-expansion/requirements-p11-whatsapp.md` |
| Deployment guide | `docs/40-operations/44-DeploymentGuide_v1.0.md` |

---

## 5. Boundary Compliance

- No secrets, tokens, or credentials modified
- No surveillance data exposed
- No consent boundary changes
- No persona drift
- Documentation-only fix, no runtime code affected

---

## 6. Remaining Follow-Up (Out of Scope)

| # | Item | Priority | Notes |
|---|------|----------|-------|
| 1 | ADR-021 wording inconsistency | LOW | Pre-existing, not blocking |
| 2 | 13 other docs still have Baileys refs | LOW | SRS, FSD, Feasibility, Security Policy, Secrets Runbook, Data Governance, Ops Manual, TDD, RTM — all need Baileys→Neonize sweep in future batch |

---

## Footer

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-03 | Guinevere | Initial verification report for ADR-022 follow-up fixes |
