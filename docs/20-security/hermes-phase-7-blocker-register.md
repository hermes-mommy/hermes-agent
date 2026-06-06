# Hermes Phase 7 Blocker Register (B1-B12)

> Status: Active | Phase: 7b (local hardening only) | Owner: Faiz
> Last updated: 2026-06-06
> Purpose: Record all identified blockers preventing ADR-035 final migration completion.
> **Phase 7 remains blocked.** This register documents gaps for Phase 7c remediation.

---

## Summary

| Total Blockers | Critical | High | Medium | Low | Resolved |
|---|---|---|---|---|---|
| 12 | 5 | 4 | 2 | 1 | 0 |

All 12 blockers must be resolved before ADR-035 can transition to IMPLEMENTED status.

---

## Blocker Register

### B1 — `guinevere-mcp` Service Inactive

| Field | Value |
|---|---|
| ID | B1 |
| Severity | Critical |
| Category | Core Service |
| Detected | Phase 7 research wave |
| Status | Open — deferred to Phase 7c |

**Description:**
The `guinevere-mcp` systemd service is not active on the VPS. This service provides the MCP (Model Context Protocol) interface that Hermes depends on for tool execution and sub-agent orchestration. Without it, the Hermes gateway cannot route tool calls correctly.

**Impact:**
Hermes gateway operational tests cannot pass while this service is down. Any attempt to mark Phase 7 complete with `guinevere-mcp` inactive would be invalid.

**Required remediation (Phase 7c):**
1. Diagnose why the service failed (config, credential, dependency).
2. Re-enable and restart via `systemctl enable --now guinevere-mcp`.
3. Verify service health and Hermes tool-call routing.
4. Run 24h stability test before claiming the blocker resolved.

---

### B2 — Hermes Config YAML Line 443 Fallback Warning

| Field | Value |
|---|---|
| ID | B2 |
| Severity | Medium |
| Category | Configuration |
| Detected | Phase 7 security audit |
| Status | Open — deferred to Phase 7c |

**Description:**
Hermes configuration YAML at `hermes-config/config.yaml` line 443 triggers a fallback warning during validation. The fallback path may silently degrade routing quality or use an unintended model provider.

**Impact:**
If the primary routing path fails silently, requests may use fallback behavior without operator awareness. This creates a reliability risk and potential cost leak.

**Required remediation (Phase 7c):**
1. Inspect line 443 in `hermes-config/config.yaml`.
2. Correct the fallback configuration to point at the intended provider.
3. Re-validate with `hermes validate` or equivalent.
4. Verify no silent fallback paths remain.

---

### B3 — Monitoring Exporter Connectivity Failures

| Field | Value |
|---|---|
| ID | B3 |
| Severity | High |
| Category | Monitoring |
| Detected | Phase 7 execution reports |
| Status | Open — deferred to Phase 7c |

**Description:**
Monitoring scrapers (Prometheus) report connectivity failures against exporter targets on the VPS. Local monitoring configs have been updated in Phase 7b, but the running exporters do not respond at the expected addresses.

**Impact:**
No real-time metrics for LLM calls, gateway uptime, safety blocks, or cost tracking. Alerts cannot fire. Dashboards show no data.

**Required remediation (Phase 7c):**
1. Verify exporter processes are running on the VPS.
2. Check Docker network connectivity between Prometheus and exporter containers.
3. Update target addresses if bindings changed.
4. Confirm successful scrape with `curl <target>/metrics`.

---

### B4 — SSH Bound to `0.0.0.0:22` and Root Login Allowed

| Field | Value |
|---|---|
| ID | B4 |
| Severity | Critical |
| Category | Network Security |
| Detected | Phase 7 security audit |
| Status | Open — deferred to Phase 7c |

**Description:**
The VPS SSH daemon listens on `0.0.0.0:22` (all interfaces) and permits root login. This creates a significant attack surface by exposing SSH to the public internet with a privileged account.

**Impact:**
Brute-force, credential-stuffing, and zero-day SSH attacks target port 22 on all internet-facing hosts. Root login amplifies the blast radius of any successful compromise.

**Required remediation (Phase 7c):**
1. Change `PermitRootLogin` to `no` or `prohibit-password` in `/etc/ssh/sshd_config`.
2. Restrict `ListenAddress` to Tailscale IP only.
3. Reload SSH daemon.
4. **Safeguard:** Keep a second SSH session alive during reload. Test new session before closing the existing one.

---

### B5 — No Active Firewall Rules

| Field | Value |
|---|---|
| ID | B5 |
| Severity | Critical |
| Category | Network Security |
| Detected | Phase 7 security audit |
| Status | Open — deferred to Phase 7c |

**Description:**
The VPS has no active firewall rules. All ports bound to `0.0.0.0` are accessible from the public internet.

**Impact:**
Any service binding to a port without explicit ACL is exposed globally. There is no defense-in-depth between services and the public network.

**Required remediation (Phase 7c):**
1. Configure `ufw` or `iptables` rules to allow only Tailscale subnet.
2. Set default deny for incoming traffic.
3. Allow SSH only from Tailscale IP.
4. Allow application ports only from Tailscale.
5. **Safeguard:** Apply firewall rules incrementally. Keep a recovery session active. Test remote access before closing the existing connection.

---

### B6 — 9Router/next-server Exposed on `0.0.0.0:20128`

| Field | Value |
|---|---|
| ID | B6 |
| Severity | Critical |
| Category | Network Security |
| Detected | Phase 7 research reports |
| Status | Open — deferred to Phase 7c |

**Description:**
9Router or next-server binds to `0.0.0.0:20128`, exposing the LLM routing proxy to all network interfaces. This port handles API key authentication for LLM provider routing.

**Impact:**
Unauthenticated or misconfigured access to port 20128 could allow LLM request injection, credential theft, or resource abuse. The API cost exposure is unbounded.

**Required remediation (Phase 7c):**
1. Rebind 9Router to `127.0.0.1:20128` or Tailscale IP only.
2. Restart the service.
3. Verify that local applications (Hermes, MCP) can still reach the service.
4. Test that external access is blocked.

---

### B7 — Core Worker or Metrics Exposed on `0.0.0.0:9191`

| Field | Value |
|---|---|
| ID | B7 |
| Severity | Critical |
| Category | Network Security |
| Detected | Phase 7 research reports |
| Status | Open — deferred to Phase 7c |

**Description:**
The core worker or metrics endpoint (used by Prometheus) binds to `0.0.0.0:9191`, exposing operational metrics to all interfaces. This port may leak information about system internals.

**Impact:**
Operational metrics, model names, request counts, and latency data are publicly visible. Combined with other signals, this aids reconnaissance.

**Required remediation (Phase 7c):**
1. Rebind metrics to `127.0.0.1:9191` or configure Prometheus to scrape via Docker network.
2. Restart the service.
3. Verify Prometheus can still scrape the target.
4. Block external access with firewall (B5).

---

### B8 — Deprecated Files Still Imported and Tested

| Field | Value |
|---|---|
| ID | B8 |
| Severity | High |
| Category | Code Quality |
| Detected | Phase 7 execution reports |
| Status | Open — partially reduced by Phase 7c safe-subset pre-archive cleanup |

**Description:**
Deprecated Discord and Hermes adapter files remain imported by active modules and referenced in test coverage. `src/core/services/llm_router.py` is explicitly retained as an active Phase 6 CostTracker dependency, not treated as deprecated. Phase 7c safe-subset work removed the Hermes help plugin dependency on `src.discord.commands` and stopped `src.hermes` package initialization from importing deprecated adapter/bridge modules, but the deprecated files cannot be archived until all remaining import chains are resolved and tests have migrated to Hermes-native implementations.

**Impact:**
Archiving deprecated files prematurely would break imports and cause test failures. The codebase cannot be considered clean until dead imports are eliminated.

**Required remediation (Phase 7c):**
1. Audit all imports of deprecated modules across `src/` and `tests/`.
2. Replace deprecated imports with Hermes-native equivalents.
3. Run full test suite to confirm no regressions.
4. Remove or archive deprecated source files after successful migration.

---

### B9 — Hermes CLI Not Found on VPS PATH

| Field | Value |
|---|---|
| ID | B9 |
| Severity | High |
| Category | Operations |
| Detected | Phase 7 execution reports |
| Status | Resolved for non-interactive operator PATH in Phase 7c safe subset |

**Description:**
The `hermes` CLI binary is now available to non-interactive VPS SSH shells via `/home/guinevere/.local/bin/hermes`, which symlinks to `/home/guinevere/code/guinevere/.venv/bin/hermes`. Phase 7c safe-subset work moved the `~/.local/bin` PATH source before the `.bashrc` non-interactive early return without service restart or systemd mutation.

**Impact:**
Operators can run read-only Hermes CLI validation commands from non-interactive SSH shells. This resolves the PATH portion of the blocker, but it does not resolve backup credential blockers B10/B11 or authorize live backup writes.

**Verification (Phase 7c):**
1. `command -v hermes` returns `/home/guinevere/.local/bin/hermes`.
2. `hermes --version` returns `Hermes Agent v0.15.2 (2026.5.29.2)`.
3. `hermes backup --help` and `hermes checkpoints status` return exit 0 without creating backup artifacts.
4. `systemctl is-active hermes-gateway` remains `active`; no restart was performed.

---

### B10 — `secrets/backup/` SOPS Credentials Missing

| Field | Value |
|---|---|
| ID | B10 |
| Severity | High |
| Category | Backup / DR |
| Detected | Phase 7 DR readiness report |
| Status | Open — deferred to Phase 7c |

**Description:**
The `secrets/backup/` directory, expected to contain SOPS-encrypted backup credentials, is missing on the VPS. Without these credentials, encrypted backups cannot be restored.

**Impact:**
If a disaster recovery event occurs, the operator cannot decrypt backup archives. Recovery from complete VPS loss is impossible without the age private key and SOPS-encrypted credential files.

**Required remediation (Phase 7c):**
1. Restore the age private key from secure offline storage.
2. Decrypt and verify SOPS-encrypted backup credentials.
3. Confirm `secrets/backup/` contains the expected encrypted files.
4. Test decryption with `sops --decrypt <file>`.

---

### B11 — Backup Sentinel `/var/log/guinevere/last-backup-success` Missing

| Field | Value |
|---|---|
| ID | B11 |
| Severity | Medium |
| Category | Backup / DR |
| Detected | Phase 7 DR readiness report |
| Status | Open — deferred to Phase 7c |

**Description:**
The backup sentinel file `/var/log/guinevere/last-backup-success` does not exist on the VPS. This sentinel is used by monitoring to verify that automated backups complete successfully.

**Impact:**
Without the sentinel, there is no automated way to detect backup failures. Backup status must be checked manually, increasing the risk of unnoticed failures.

**Required remediation (Phase 7c):**
1. Configure the backup script to create the sentinel file after each successful run.
2. Add a Prometheus blackbox or file-exporter check for the sentinel.
3. Create an alert rule for sentinel age exceeding the backup interval.
4. Verify sentinel creation with a manual backup run.

---

### B12 — Hermes-Native Gateway Metrics Not Exported

| Field | Value |
|---|---|
| ID | B12 |
| Severity | Low |
| Category | Monitoring |
| Detected | Phase 7 execution reports |
| Status | Open — deferred to Phase 7c |

**Description:**
Hermes-native Prometheus metrics (e.g., `hermes_llm_calls_total`, `hermes_safety_blocks_total`, `hermes_gateway_up`) are not exported by the running Hermes gateway instance. Current monitoring relies on Phase 6 legacy metrics from the LLM router.

**Impact:**
Alerting rules defined during Phase 7b reference Hermes-native metrics that do not exist yet. Alerts for gateway health, safety blocks, and cost tracking will not fire until instrumentation is added.

**Required remediation (Phase 7c):**
1. Add Prometheus metric instrumentation to the Hermes gateway code or configuration.
2. Export metrics at an accessible endpoint.
3. Update Prometheus scrape config to target the new endpoint.
4. Verify metrics appear in the /metrics output.

---

## Appendix: Blocked Gates Summary

| Gate | Blocker IDs | Phase |
|---|---|---|
| 24h stable operation | B1, B2, B3, B8, B9 | 7c |
| VPS security posture | B4, B5, B6, B7 | 7c |
| Backup and DR readiness | B10, B11 | 7c |
| Monitoring completeness | B12 | 7c |
| ADR-035 IMPLEMENTED | All (B1-B12) | 7c |

---

## Footer

Document version: 1.0
Date: 2026-06-06
Status: Active — Phase 7 remains blocked. This register supports Phase 7c planning.
