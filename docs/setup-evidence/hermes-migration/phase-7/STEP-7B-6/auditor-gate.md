# Step 7b.6 — Hermes Gateway Systemd Template — Auditor Gate

**Status:** PENDING AUDITOR REVIEW

**Auditor scope:** A3 — Docs and Evidence Completeness (per Phase 7b plan §9)

**Scoped steps:** 7b.6, 7b.7, 7b.8

**Checklist for auditor:**

- [ ] `systemd/hermes-gateway.service` exists and contains all required hardening flags:
  - `Type=exec`, `User=guinevere`, `Group=guinevere`
  - `Slice=guinevere.slice`, `MemoryHigh=512M`, `MemoryMax=1G`
  - `NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=read-only`
  - `PrivateTmp=true`, `ProtectKernelTunables=true`, `ProtectKernelModules=true`
  - `ProtectControlGroups=true`, `RestrictSUIDSGID=true`
  - Explicit limited `ReadWritePaths` (no broad `/`)
- [ ] No `User=root`
- [ ] No `ReadWritePaths=/`
- [ ] VPS sync comment present in the unit file
- [ ] Verification file exists with all 12 evidence sections
- [ ] Verification file does not claim live deployment or `systemd-analyze security`
- [ ] No ADR-035 IMPLEMENTED claim
- [ ] No Phase 7 complete claim
- [ ] Boundary compliance: no persona/surveillance/consent/HARD STOP/secrets exposure

**Verdict:** __________ (PASS / NEEDS REVIEW / FAIL)

**Findings:**

1. 
2. 
3. 

**Auditor:** __________
**Date:** __________
