# Verification 5-3 Pre-Flight — CI-2 Custom Hermes Skill Discovery Smoke Test

| Field | Value |
|---|---|
| Step | 5.3 Pre-Flight (CI-2) |
| Status | **PASS** — custom Hermes skill discovery functional |
| Date | 2026-06-05 |
| Evidence Root | `docs/setup-evidence/phase-5/` |
| Planner Gate | `docs/setup-evidence/phase-5/batch-plan-phase-5.md` |
| Authority | Planner scaffold 5.3-CI2 |
| Hermes CLI Path | `/home/guinevere/code/guinevere/.venv/bin/hermes` |
| Hermes Version | `hermes-agent>=0.15` (via `pyproject.toml`) |

---

## 1. What Was Done

Executed a pre-flight smoke test to verify that Hermes Agent's skill discovery mechanism can find a newly added custom skill in `~/.hermes/skills/`. This is the prerequisite for Step 5.3 (custom Hermes skills deployment). The test cycle:

1. Located the `hermes` CLI binary (inside Python venv, not on global PATH).
2. Verified baseline: ran `hermes skills list` to confirm CLI functional.
3. Created dummy skill `test-discovery` with minimal `SKILL.md`.
4. Ran `hermes skills list` again — confirmed `test-discovery` appears with source=local, enabled.
5. Cleaned up dummy directory.
6. Verified removal.
7. Captured fallback CLI capabilities (`hermes skills --help` output) for reference.

---

## 2. Files Changed

| File | Action |
|---|---|
| `docs/setup-evidence/phase-5/verification-5-3-preflight.md` | **Created** (this file) |

No VPS files, config files, or source files were modified.

---

## 3. Validation Results

### 3.1 Hermes CLI Discovery

| Check | Result |
|---|---|
| `hermes` binary exists in `.venv/bin/hermes` | ✅ YES |
| `hermes skills list` runs without error | ✅ YES |
| Baseline list before test-discovery | ✅ Shows no `test-discovery` (0 hub, 0 builtin, 0 local) |
| After creating test-discovery, list includes it | ✅ YES — name=`test-discovery`, source=`local`, status=`enabled` |
| Cleanup removes dummy dir | ✅ CONFIRMED REMOVED |
| Post-cleanup: no test-discovery in listing | ✅ CONFIRMED |

### 3.2 `hermes skills list` Output (During Test)

```
                    Installed Skills
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━┳━━━━━━━━━┓
┃ Name           ┃ Category ┃ Source ┃ Trust ┃ Status  ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━╇━━━━━━━━━┩
│ test-discovery │          │ local  │ local │ enabled │
└────────────────┴──────────┴────────┴───────┴─────────┘
0 hub-installed, 0 builtin, 1 local — 1 enabled, 0 disabled
```

### 3.3 `hermes skills` CLI Capabilities

The Hermes CLI supports a rich skill management subcommand set:

| Subcommand | Purpose |
|---|---|
| `browse` | Browse all available skills (paginated) |
| `search` | Search skill registries |
| `install` | Install a skill |
| `inspect` | Preview a skill without installing |
| `list` | List installed skills |
| `update` | Update installed hub skills |
| `audit` | Re-scan installed hub skills |
| `uninstall` | Remove a hub-installed skill |
| `snapshot` | Export/import skill configurations |
| `tap` | Manage skill sources |
| `config` | Enable/disable individual skills |

**Key `list` flags:**
- `--source {all,hub,builtin,local}` — filter by source
- `--enabled-only` — show only enabled skills

---

## 4. Evidence Artifacts

| Artifact | Location |
|---|---|
| This verification | `docs/setup-evidence/phase-5/verification-5-3-preflight.md` |
| Batch plan | `docs/setup-evidence/phase-5/batch-plan-phase-5.md` |

---

## 5. Doc-Sync Impact

None. No documentation was modified.

---

## 6. Boundary Compliance

| Constraint | Status |
|---|---|
| No real Phase 5 skills touched | ✅ |
| `SOUL.md`, `config.yaml`, source files, secrets not modified | ✅ |
| `test-discovery` directory removed post-test | ✅ |
| No orphan files left behind | ✅ |
| No real skill dirs modified | ✅ — only created/removed `test-discovery/` |
| Hermes CLI path documented for Step 5.3 | ✅ — `.venv/bin/hermes` (not on global PATH) |

---

## 7. Rollback / Re-run Safety

**Re-run safe.** Creating and removing `test-discovery` is idempotent. The `hermes` CLI re-scans the filesystem on each `hermes skills list` invocation — no caching side effects were observed.

---

## 8. Design Decisions & Caveats

### Critical Finding: Hermes CLI not on global PATH

The `hermes` binary is only available inside the Python virtual environment at `/home/guinevere/code/guinevere/.venv/bin/hermes`. It is **not** on the system PATH (no `hermes` in `/usr/bin/`, `~/.local/bin/`, or `~/bin/`). All Step 5.3 skill management commands must either:

- Use the full path: `/home/guinevere/code/guinevere/.venv/bin/hermes skills ...`
- Activate the venv first: `source /home/guinevere/code/guinevere/.venv/bin/activate && hermes skills ...`
- Add the venv bin to PATH in shell config

### Auto-discovery mechanism

Hermes automatically discovers skills by scanning `~/.hermes/skills/<name>/SKILL.md`. No registration or index update is required — adding `SKILL.md` to a directory is sufficient for discovery. The source appears as `local`.

### Existing skills on VPS

The `~/.hermes/skills/` directory contains 19 skill directories (apple, autonomous-ai-agents, creative, etc.) but **none** have `SKILL.md` files — they only contain `DESCRIPTION.md`. This suggests either:
- These are a different skill format (hub-installed or bundled)
- Hermes may also support other discovery mechanisms
- Step 5.3 should verify which format is expected for custom skills

### Fallback checks not needed

Primary discovery test passed, so the fallback chain (`hermes skills install --help`, `grep -i 'skill' config.yaml`, `hermes --help \| grep -i skill`) was not executed. The capability info was captured from `hermes skills --help` instead.

---

## 9. Blocker Decision

| Criterion | Status |
|---|---|
| Hermes CLI exists and functional | ✅ PASS |
| `hermes skills list` discovers new local SKILL.md | ✅ PASS |
| Skill appears with source=local, status=enabled | ✅ PASS |
| CLI path documented for subsequent steps | ✅ PASS |
| **Step 5.3 is NOT blocked** | ✅ **PASS** |

**Verdict: Step 5.3 can proceed.** Custom Hermes skill discovery via placing `SKILL.md` in `~/.hermes/skills/<name>/` is functional and verified.

---

## 10. Auditor Gate

Not applicable — this is a pre-flight smoke test, not a production deployment. The formal auditor gate for Step 5.3 will occur after skill deployment.

---

## 11. Security Scan

| Check | Result |
|---|---|
| No secrets exposed | ✅ |
| No config.yaml modification | ✅ |
| No SOUL.md modification | ✅ |
| No source file modification | ✅ |
| No real skill dirs touched | ✅ |
| SSH alias `guinevere-vps` used correctly | ✅ |

---

## 12. Next Action

Proceed to **Step 5.3** — deploy custom Hermes skills (`persona-safety`, `canary-consent`, `syscall-audit`) to `~/.hermes/skills/` using the documented CLI path. Each skill must include a valid `SKILL.md` for discovery.

### Hermes CLI reference for Step 5.3

```bash
# Verify skills before/after
/home/guinevere/code/guinevere/.venv/bin/hermes skills list

# Check specific skill
/home/guinevere/code/guinevere/.venv/bin/hermes skills inspect <name>

# Configure skill (enable/disable)
/home/guinevere/code/guinevere/.venv/bin/hermes skills config
```

---

*Evidence generated: 2026-06-05 by Guinevere CI-2 pre-flight smoke test.*
